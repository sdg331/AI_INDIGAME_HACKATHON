using System.Collections.Generic;
using UnityEngine;

[RequireComponent(typeof(Rigidbody2D), typeof(Collider2D))]
public sealed class MeleeEnemyAI : MonoBehaviour, IDamageable, IGroggyReceiver,
    IGroggyBuildupReceiver, IOathHealthState, IOathIncapacitable, IOathEntityIdentity
{
    private enum State
    {
        Idle,
        Chase,
        Windup,
        Attack,
        Recovery,
        HitStun,
        Groggy,
        Incapacitated,
        Dead
    }

    [Header("Target / Movement")]
    [SerializeField] private Transform player;
    [SerializeField] private string playerTag = "Player";
    [SerializeField, Min(0f)] private float detectionRange = 6f;
    [SerializeField, Min(0f)] private float loseRange = 9f;
    [SerializeField, Min(0f)] private float moveSpeed = 2.5f;
    [SerializeField, Min(0f)] private float stopDistance = 1f;

    [Header("Attack")]
    [SerializeField, Min(0f)] private float attackRange = 1.2f;
    [SerializeField, Min(0f)] private float attackWindupTime = 0.5f;
    [SerializeField, Min(0.01f)] private float attackActiveTime = 0.15f;
    [SerializeField, Min(0f)] private float attackRecoveryTime = 0.8f;
    [SerializeField, Min(1)] private int attackDamage = 1;
    [SerializeField] private EnemyAttackHitbox attackHitbox;
    [SerializeField] private Vector2 attackHitboxOffset = new(0.8f, 0f);
    [SerializeField] private Vector2 attackHitboxSize = new(1f, 1f);

    [Header("Danger Marker")]
    [SerializeField] private GameObject dangerMarker;
    [SerializeField] private Vector3 dangerMarkerOffset = new(0f, 1.2f, 0f);

    [Header("Ground / Wall / Ledge")]
    [SerializeField] private LayerMask groundLayer;
    [SerializeField, Min(0.01f)] private float groundCheckDistance = 0.15f;
    [SerializeField, Min(0.01f)] private float wallCheckDistance = 0.15f;
    [SerializeField, Min(0.01f)] private float ledgeForwardDistance = 0.15f;
    [SerializeField, Min(0.01f)] private float ledgeCheckDepth = 0.7f;
    [SerializeField, Min(0f)] private float jumpForce = 7f;
    [SerializeField, Min(0f)] private float jumpHeightThreshold = 1f;
    [SerializeField, Min(0f)] private float jumpCooldown = 0.5f;

    [Header("Health / State")]
    [SerializeField, Min(1)] private int maxHealth = 3;
    [SerializeField, Min(0f)] private float hitStunDuration = 0.2f;
    [SerializeField, Min(0f)] private float defaultGroggyDuration = 2f;
    [SerializeField, Min(0.1f)] private float groggyBuildupThreshold = 3f;

    [Header("Animation / Visuals")]
    [SerializeField] private SpriteRenderer characterSprite;
    [SerializeField] private Animator animator;
    [Tooltip("원본 스프라이트가 오른쪽을 바라보고 있으면 활성화합니다.")]
    [SerializeField] private bool spriteFacesRightByDefault = true;
    [SerializeField, Min(0f)] private float movementAnimationThreshold = 0.05f;
    [SerializeField] private EnemyHealthBar2D healthBar;
    [SerializeField] private bool ignoreBodyCollisionWithPlayer = true;

    [Header("Tutorial Overrides")]
    [Tooltip("체력이 줄지 않습니다. 피격 반응과 연격 판정은 그대로 성립합니다.")]
    [SerializeField] private bool damageImmune;
    [Tooltip("플레이어를 추격하거나 공격하지 않고 제자리에서 대기합니다.")]
    [SerializeField] private bool passive;

    public bool DamageImmune
    {
        get => damageImmune;
        set => damageImmune = value;
    }

    public bool Passive
    {
        get => passive;
        set => passive = value;
    }

    public int CurrentHealth { get; private set; }
    public bool IsDead => currentState == State.Dead;
    public bool IsIncapacitated => currentState == State.Incapacitated;
    public bool IsGroggy => currentState == State.Groggy;
    public int OathEntityId => gameObject.GetInstanceID();

    private Rigidbody2D body;
    private Collider2D bodyCollider;
    private State currentState = State.Idle;
    private float stateTimeRemaining;
    private float lastJumpTime = float.NegativeInfinity;
    private float nextPlayerSearchTime;
    private bool isGrounded;
    private int facingSign = 1;
    private float groggyBuildup;
    private TextMesh dangerMarkerText;
    private readonly HashSet<int> animatorFloatParameters = new();
    private readonly HashSet<int> animatorBoolParameters = new();
    private readonly HashSet<int> animatorTriggerParameters = new();

    private static readonly int SpeedHash = Animator.StringToHash("Speed");
    private static readonly int MovingHash = Animator.StringToHash("IsMoving");
    private static readonly int GroundedHash = Animator.StringToHash("Grounded");
    private static readonly int AttackHash = Animator.StringToHash("Attack");
    private static readonly int AttackingHash = Animator.StringToHash("IsAttacking");
    private static readonly int HitHash = Animator.StringToHash("Hit");
    private static readonly int GroggyHash = Animator.StringToHash("Groggy");
    private static readonly int IncapacitatedHash = Animator.StringToHash("Incapacitated");
    private static readonly int DeadHash = Animator.StringToHash("Dead");

    private void Awake()
    {
        body = GetComponent<Rigidbody2D>();
        bodyCollider = GetComponent<Collider2D>();
        CurrentHealth = maxHealth;
        body.freezeRotation = true;

        if (groundLayer.value == 0)
            groundLayer = LayerMask.GetMask("Ground");
        if (animator == null)
            animator = GetComponentInChildren<Animator>(true);
        if (characterSprite == null)
            characterSprite = FindCharacterSprite();
        CacheAnimatorParameters();
        if (healthBar == null)
            healthBar = GetComponent<EnemyHealthBar2D>();
        if (healthBar == null)
            healthBar = gameObject.AddComponent<EnemyHealthBar2D>();

        SetupAttackHitbox();
        SetupDangerMarker();
        healthBar.Initialize(CurrentHealth, maxHealth);
        FindPlayer();

        if (loseRange < detectionRange)
            loseRange = detectionRange;
    }

    private void OnDisable()
    {
        CancelAttack();
    }

    private void Update()
    {
        UpdateGrounded();
        UpdateAnimator();

        if (IsDead || IsIncapacitated)
            return;

        if (player == null)
        {
            if (Time.time >= nextPlayerSearchTime)
                FindPlayer();
            return;
        }

        UpdateState(Vector2.Distance(transform.position, player.position));
    }

    private void FixedUpdate()
    {
        if (currentState == State.Chase && player != null)
            MoveTowardsPlayer();
        else if (currentState != State.HitStun)
            StopMoving();
    }

    private void LateUpdate()
    {
        // 애니메이션 클립이 SpriteRenderer 값을 갱신하더라도 마지막에 방향을 다시 적용한다.
        ApplyFacingVisual();
    }

    private void UpdateState(float distance)
    {
        // 대기 모드로 바뀌면 진행 중이던 추격·공격을 즉시 접고 제자리로 돌아갑니다.
        if (passive && (currentState == State.Chase || currentState == State.Windup ||
                        currentState == State.Attack || currentState == State.Recovery))
        {
            CancelAttack();
            StopMoving();
            ChangeState(State.Idle);
        }

        switch (currentState)
        {
            case State.Idle:
                if (!passive && distance <= detectionRange)
                    ChangeState(State.Chase);
                break;
            case State.Chase:
                if (distance <= attackRange)
                    StartWindup();
                else if (distance > loseRange)
                    ChangeState(State.Idle);
                break;
            case State.Windup:
                TickTimer(StartAttack);
                break;
            case State.Attack:
                TickTimer(() =>
                {
                    attackHitbox.EndAttack();
                    ChangeTimedState(State.Recovery, attackRecoveryTime);
                });
                break;
            case State.Recovery:
                TickTimer(() => ChangeState(distance <= loseRange ? State.Chase : State.Idle));
                break;
            case State.HitStun:
                TickTimer(() => ChangeState(distance <= loseRange ? State.Chase : State.Idle));
                break;
            case State.Groggy:
                TickTimer(() =>
                {
                    SetAnimatorBool(GroggyHash, false);
                    SetMarkerSymbol("!");
                    SetDangerMarker(false);
                    ChangeState(distance <= loseRange ? State.Chase : State.Idle);
                });
                break;
        }
    }

    private void TickTimer(System.Action onFinished)
    {
        stateTimeRemaining -= Time.deltaTime;
        if (stateTimeRemaining <= 0f)
            onFinished();
    }

    private void MoveTowardsPlayer()
    {
        float direction = Mathf.Sign(player.position.x - transform.position.x);
        if (Mathf.Approximately(direction, 0f))
            return;

        SetFacing(direction > 0f ? 1 : -1);
        if (Vector2.Distance(transform.position, player.position) <= stopDistance)
            return;

        bool wallAhead = IsWallAhead(direction);
        bool ledgeAhead = !IsGroundAhead(direction);

        if (isGrounded && wallAhead)
        {
            if (CanJump())
                Jump();
            else
                return;
        }

        if (isGrounded && ledgeAhead)
            return;

        if (isGrounded && player.position.y - transform.position.y >= jumpHeightThreshold && CanJump())
            Jump();

        body.linearVelocity = new Vector2(direction * moveSpeed, body.linearVelocity.y);
    }

    private void StartWindup()
    {
        FacePlayer();
        StopMoving();
        SetMarkerSymbol("!");
        SetDangerMarker(true);
        ChangeTimedState(State.Windup, attackWindupTime);
    }

    private void StartAttack()
    {
        SetDangerMarker(false);
        SetAnimatorTrigger(AttackHash);
        attackHitbox.BeginAttack(Vector2.right * facingSign);
        ChangeTimedState(State.Attack, attackActiveTime);
    }

    public void TakeDamage(int damage, Vector2 hitPoint, Vector2 hitDirection)
    {
        if (damage <= 0 || IsDead || IsIncapacitated)
            return;

        // 튜토리얼 연격 단계: 체력은 그대로 두고 피격 반응만 재생합니다.
        // 연격 카운터는 PlayerAttackHitbox가 이 호출 직후에 올리므로 그대로 쌓입니다.
        if (damageImmune)
        {
            SetAnimatorTrigger(HitHash);
            return;
        }

        CurrentHealth = Mathf.Max(0, CurrentHealth - damage);
        healthBar.SetHealth(CurrentHealth, maxHealth);
        CancelAttack();
        if (CurrentHealth == 0)
        {
            Die(EnemyDeathCause.Player);
            return;
        }

        SetAnimatorTrigger(HitHash);
        body.linearVelocity = new Vector2(0f, body.linearVelocity.y);
        ChangeTimedState(State.HitStun, hitStunDuration);
    }

    public void EnterGroggy(float duration, GameObject source)
    {
        if (IsDead || IsIncapacitated)
            return;

        CancelAttack();
        StopMoving();
        SetAnimatorBool(GroggyHash, true);
        SetMarkerSymbol("★");
        SetDangerMarker(true);
        float appliedDuration = duration > 0f ? duration : defaultGroggyDuration;
        ChangeTimedState(State.Groggy, appliedDuration);

        if (SkillEffects.Instance != null)
        {
            SkillEffects.Instance.PlayGroggyEnter(transform);
            SkillEffects.Instance.PlayGroggyLoop(transform, appliedDuration);
        }

        Debug.Log($"[Enemy] {name}: 패링됨, {appliedDuration:0.00}초 그로기", this);
    }

    public void AddGroggyBuildup(float amount, GameObject source)
    {
        if (amount <= 0f || IsDead || IsIncapacitated || IsGroggy)
            return;

        groggyBuildup += amount;
        if (groggyBuildup < groggyBuildupThreshold)
            return;

        groggyBuildup = 0f;
        EnterGroggy(defaultGroggyDuration, source);
    }

    public void ApplyPushback(Vector2 impulse, float movementLockDuration)
    {
        if (IsDead || IsIncapacitated)
            return;

        CancelAttack();
        body.linearVelocity = Vector2.zero;
        body.AddForce(impulse, ForceMode2D.Impulse);
        ChangeTimedState(State.HitStun, Mathf.Max(0.05f, movementLockDuration));
    }

    public void Incapacitate()
    {
        if (IsDead || IsIncapacitated)
            return;

        CurrentHealth = Mathf.Max(1, CurrentHealth);
        healthBar.SetHealth(CurrentHealth, maxHealth);
        CancelAttack();
        ChangeState(State.Incapacitated);
        SetAnimatorBool(IncapacitatedHash, true);
        Debug.Log($"[Enemy] {name}: 무력화", this);
    }

    public void ApplyEnvironmentalDamage(int damage)
    {
        if (damage <= 0 || IsDead || IsIncapacitated)
            return;

        CurrentHealth = Mathf.Max(0, CurrentHealth - damage);
        healthBar.SetHealth(CurrentHealth, maxHealth);
        if (CurrentHealth == 0)
            Die(EnemyDeathCause.Environment);
    }

    public void Die(EnemyDeathCause cause)
    {
        if (IsDead)
            return;

        CurrentHealth = 0;
        healthBar.SetHealth(CurrentHealth, maxHealth);
        CancelAttack();
        ChangeState(State.Dead);
        body.linearVelocity = Vector2.zero;
        body.simulated = false;
        bodyCollider.enabled = false;
        SetAnimatorBool(DeadHash, true);

        OathSystem oathSystem = OathSystem.Instance;
        if (oathSystem != null)
            oathSystem.NotifyEnemyDied(gameObject, cause);
    }

    private void SetupAttackHitbox()
    {
        if (attackHitbox == null)
            attackHitbox = GetComponentInChildren<EnemyAttackHitbox>(true);

        if (attackHitbox == null)
        {
            GameObject hitboxObject = new("AttackHitbox");
            hitboxObject.transform.SetParent(transform, false);
            BoxCollider2D box = hitboxObject.AddComponent<BoxCollider2D>();
            box.size = attackHitboxSize;
            box.isTrigger = true;
            attackHitbox = hitboxObject.AddComponent<EnemyAttackHitbox>();
        }

        attackHitbox.Initialize(this, attackDamage);
        PositionAttackHitbox();
        attackHitbox.EndAttack();
    }

    private void SetupDangerMarker()
    {
        if (dangerMarker == null)
        {
            dangerMarker = new GameObject("DangerMarker");
            dangerMarker.transform.SetParent(transform, false);
            TextMesh markerText = dangerMarker.AddComponent<TextMesh>();
            markerText.text = "!";
            markerText.color = Color.red;
            markerText.fontSize = 64;
            markerText.characterSize = 0.1f;
            markerText.anchor = TextAnchor.MiddleCenter;
            markerText.alignment = TextAlignment.Center;
            markerText.GetComponent<MeshRenderer>().sortingOrder = 100;
        }

        dangerMarkerText = dangerMarker.GetComponentInChildren<TextMesh>(true);
        dangerMarker.transform.localPosition = dangerMarkerOffset;
        SetMarkerSymbol("!");
        SetDangerMarker(false);
    }

    private void FindPlayer()
    {
        nextPlayerSearchTime = Time.time + 0.5f;
        GameObject found = GameObject.FindGameObjectWithTag(playerTag);
        if (found == null)
            return;

        player = found.transform;
        if (ignoreBodyCollisionWithPlayer)
            IgnorePlayerBodyCollision();
    }

    private void IgnorePlayerBodyCollision()
    {
        Collider2D[] playerColliders = player.GetComponentsInChildren<Collider2D>(true);
        foreach (Collider2D playerCollider in playerColliders)
        {
            if (!playerCollider.isTrigger)
                Physics2D.IgnoreCollision(bodyCollider, playerCollider, true);
        }
    }

    private void UpdateGrounded()
    {
        Bounds bounds = bodyCollider.bounds;
        Vector2 origin = new(bounds.center.x, bounds.min.y + 0.02f);
        isGrounded = Physics2D.Raycast(origin, Vector2.down, groundCheckDistance, groundLayer);
    }

    private bool IsWallAhead(float direction)
    {
        Bounds bounds = bodyCollider.bounds;
        float distance = bounds.extents.x + wallCheckDistance;
        return Physics2D.Raycast(bounds.center, Vector2.right * direction, distance, groundLayer);
    }

    private bool IsGroundAhead(float direction)
    {
        Bounds bounds = bodyCollider.bounds;
        Vector2 origin = new(
            bounds.center.x + direction * (bounds.extents.x + ledgeForwardDistance),
            bounds.min.y + 0.05f);
        return Physics2D.Raycast(origin, Vector2.down, ledgeCheckDepth, groundLayer);
    }

    private bool CanJump() => Time.time >= lastJumpTime + jumpCooldown;

    private void Jump()
    {
        lastJumpTime = Time.time;
        body.linearVelocity = new Vector2(body.linearVelocity.x, jumpForce);
    }

    private void FacePlayer()
    {
        if (player != null)
            SetFacing(player.position.x >= transform.position.x ? 1 : -1);
    }

    private void SetFacing(int sign)
    {
        facingSign = sign;
        ApplyFacingVisual();
        PositionAttackHitbox();
    }

    private void ApplyFacingVisual()
    {
        if (characterSprite == null)
            return;

        characterSprite.flipX = spriteFacesRightByDefault
            ? facingSign < 0
            : facingSign > 0;
    }

    private SpriteRenderer FindCharacterSprite()
    {
        if (animator != null)
        {
            SpriteRenderer animatorRenderer = animator.GetComponent<SpriteRenderer>();
            if (animatorRenderer != null)
                return animatorRenderer;

            animatorRenderer = animator.GetComponentInChildren<SpriteRenderer>(true);
            if (animatorRenderer != null)
                return animatorRenderer;
        }

        foreach (SpriteRenderer candidate in GetComponentsInChildren<SpriteRenderer>(true))
        {
            if (candidate.GetComponentInParent<EnemyAttackHitbox>() != null ||
                IsGeneratedStatusVisual(candidate.transform))
            {
                continue;
            }

            return candidate;
        }

        return null;
    }

    private bool IsGeneratedStatusVisual(Transform candidate)
    {
        Transform current = candidate;
        while (current != null && current != transform)
        {
            if (current.name == "EnemyHealthBar" || current.name == "DangerMarker")
                return true;
            current = current.parent;
        }
        return false;
    }

    private void PositionAttackHitbox()
    {
        if (attackHitbox == null)
            return;

        Vector3 position = attackHitbox.transform.localPosition;
        position.x = Mathf.Abs(attackHitboxOffset.x) * facingSign;
        position.y = attackHitboxOffset.y;
        attackHitbox.transform.localPosition = position;
    }

    private void CancelAttack()
    {
        SetDangerMarker(false);
        if (attackHitbox != null)
            attackHitbox.EndAttack();
    }

    private void ChangeState(State state)
    {
        currentState = state;
        stateTimeRemaining = 0f;
    }

    private void ChangeTimedState(State state, float duration)
    {
        currentState = state;
        stateTimeRemaining = Mathf.Max(0f, duration);
    }

    private void StopMoving()
    {
        body.linearVelocity = new Vector2(0f, body.linearVelocity.y);
    }

    private void SetDangerMarker(bool value)
    {
        if (dangerMarker != null)
            dangerMarker.SetActive(value);
    }

    private void SetMarkerSymbol(string symbol)
    {
        if (dangerMarkerText != null)
            dangerMarkerText.text = symbol;
    }

    private void UpdateAnimator()
    {
        if (animator == null)
            return;

        float horizontalSpeed = Mathf.Abs(body.linearVelocity.x);
        bool isMoving = currentState == State.Chase && isGrounded &&
                        horizontalSpeed > movementAnimationThreshold;
        bool isAttacking = currentState == State.Windup || currentState == State.Attack;

        SetAnimatorFloat(SpeedHash, horizontalSpeed);
        SetAnimatorBool(MovingHash, isMoving);
        SetAnimatorBool(GroundedHash, isGrounded);
        SetAnimatorBool(AttackingHash, isAttacking);
    }

    private void SetAnimatorTrigger(int parameter)
    {
        if (animator != null && animatorTriggerParameters.Contains(parameter))
            animator.SetTrigger(parameter);
    }

    private void SetAnimatorBool(int parameter, bool value)
    {
        if (animator != null && animatorBoolParameters.Contains(parameter))
            animator.SetBool(parameter, value);
    }

    private void SetAnimatorFloat(int parameter, float value)
    {
        if (animator != null && animatorFloatParameters.Contains(parameter))
            animator.SetFloat(parameter, value);
    }

    private void CacheAnimatorParameters()
    {
        animatorFloatParameters.Clear();
        animatorBoolParameters.Clear();
        animatorTriggerParameters.Clear();

        if (animator == null)
            return;

        foreach (AnimatorControllerParameter parameter in animator.parameters)
        {
            switch (parameter.type)
            {
                case AnimatorControllerParameterType.Float:
                    animatorFloatParameters.Add(parameter.nameHash);
                    break;
                case AnimatorControllerParameterType.Bool:
                    animatorBoolParameters.Add(parameter.nameHash);
                    break;
                case AnimatorControllerParameterType.Trigger:
                    animatorTriggerParameters.Add(parameter.nameHash);
                    break;
            }
        }
    }

    private void OnDrawGizmosSelected()
    {
        Gizmos.color = Color.cyan;
        Gizmos.DrawWireSphere(transform.position, detectionRange);
        Gizmos.color = Color.yellow;
        Gizmos.DrawWireSphere(transform.position, loseRange);
        Gizmos.color = Color.red;
        Gizmos.DrawWireSphere(transform.position, attackRange);

        Collider2D sourceCollider = bodyCollider != null ? bodyCollider : GetComponent<Collider2D>();
        if (sourceCollider == null)
            return;

        Bounds bounds = sourceCollider.bounds;
        float direction = facingSign;
        Gizmos.color = Color.magenta;
        Gizmos.DrawLine(bounds.center,
            bounds.center + Vector3.right * direction * (bounds.extents.x + wallCheckDistance));
        Vector3 ledgeOrigin = new(
            bounds.center.x + direction * (bounds.extents.x + ledgeForwardDistance),
            bounds.min.y + 0.05f,
            transform.position.z);
        Gizmos.color = Color.green;
        Gizmos.DrawLine(ledgeOrigin, ledgeOrigin + Vector3.down * ledgeCheckDepth);
    }
}

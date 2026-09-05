using UnityEngine;

[RequireComponent(typeof(Rigidbody2D), typeof(Collider2D))]
public sealed class MeleeEnemyAI : MonoBehaviour, IDamageable, IGroggyReceiver,
    IOathHealthState, IOathIncapacitable, IOathEntityIdentity
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
    [SerializeField, Min(0f)] private float knockbackForce = 5f;
    [SerializeField, Min(0f)] private float hitStunDuration = 0.2f;
    [SerializeField, Min(0f)] private float defaultGroggyDuration = 2f;

    [Header("Optional Visuals")]
    [SerializeField] private SpriteRenderer characterSprite;
    [SerializeField] private Animator animator;
    [SerializeField] private EnemyHealthBar2D healthBar;
    [SerializeField] private bool ignoreBodyCollisionWithPlayer = true;

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
    private TextMesh dangerMarkerText;

    private static readonly int SpeedHash = Animator.StringToHash("Speed");
    private static readonly int GroundedHash = Animator.StringToHash("Grounded");
    private static readonly int AttackHash = Animator.StringToHash("Attack");
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
        if (characterSprite == null)
            characterSprite = GetComponentInChildren<SpriteRenderer>(true);
        if (animator == null)
            animator = GetComponentInChildren<Animator>(true);
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
        else
            StopMoving();
    }

    private void UpdateState(float distance)
    {
        switch (currentState)
        {
            case State.Idle:
                if (distance <= detectionRange)
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

        CurrentHealth = Mathf.Max(0, CurrentHealth - damage);
        healthBar.SetHealth(CurrentHealth, maxHealth);
        CancelAttack();
        if (CurrentHealth == 0)
        {
            Die(EnemyDeathCause.Player);
            return;
        }

        SetAnimatorTrigger(HitHash);
        body.linearVelocity = Vector2.zero;
        body.AddForce(hitDirection.normalized * knockbackForce, ForceMode2D.Impulse);
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
        Debug.Log($"[Enemy] {name}: 패링됨, {appliedDuration:0.00}초 그로기", this);
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
        if (characterSprite != null)
            characterSprite.flipX = sign < 0;
        PositionAttackHitbox();
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
        animator.SetFloat(SpeedHash, Mathf.Abs(body.linearVelocity.x));
        animator.SetBool(GroundedHash, isGrounded);
    }

    private void SetAnimatorTrigger(int parameter)
    {
        if (animator != null)
            animator.SetTrigger(parameter);
    }

    private void SetAnimatorBool(int parameter, bool value)
    {
        if (animator != null)
            animator.SetBool(parameter, value);
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

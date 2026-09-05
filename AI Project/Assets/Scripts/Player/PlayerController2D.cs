using System.Collections;
using UnityEngine;
using UnityEngine.InputSystem;

[RequireComponent(typeof(Rigidbody2D))]
public sealed class PlayerController2D : MonoBehaviour
{
    [Header("Movement")]
    [SerializeField, Min(0f)] private float moveSpeed = 6f;
    [SerializeField, Min(0f)] private float jumpForce = 12f;
    [Tooltip("발판에서 떨어진 직후에도 점프할 수 있는 유예 시간입니다.")]
    [SerializeField, Min(0f)] private float coyoteTime = 0.12f;
    [SerializeField] private Transform groundCheck;
    [SerializeField, Min(0.01f)] private float groundCheckRadius = 0.15f;
    [SerializeField] private LayerMask groundLayer;
    [Tooltip("벽을 향해 이동할 때 마찰로 벽에 달라붙는 현상을 방지합니다.")]
    [SerializeField] private bool preventWallSticking = true;

    [Header("Attack")]
    [SerializeField] private PlayerAttackHitbox attackHitbox;
    [SerializeField, Min(0f)] private float attackWindup = 0.08f;
    [SerializeField, Min(0.01f)] private float attackActiveTime = 0.12f;
    [SerializeField, Min(0f)] private float attackRecovery = 0.2f;

    [Header("Guard / Parry")]
    [SerializeField, Min(0.01f)] private float parryWindow = 0.2f;
    [SerializeField, Min(0f)] private float guardCooldown = 0.5f;
    [SerializeField, Min(0f)] private float groggyDuration = 2f;

    [Header("Roll")]
    [SerializeField, Min(0f)] private float rollSpeed = 12f;
    [SerializeField, Min(0.01f)] private float rollDuration = 0.25f;
    [SerializeField, Min(0f)] private float rollCooldown = 0.5f;

    [Header("Visuals (Optional)")]
    [SerializeField] private SpriteRenderer characterSprite;
    [SerializeField] private Animator animator;
    [SerializeField, Min(0f)] private float walkingAnimationThreshold = 0.05f;

    [Header("Entity Interface")]
    [Tooltip("실제 체력을 관리하며 IDamageable을 구현한 엔티티 컴포넌트입니다.")]
    [SerializeField] private MonoBehaviour damageReceiverBehaviour;

    public bool IsParrying => state == PlayerState.Parrying;
    public bool IsGuarding => state == PlayerState.Guarding;
    public bool IsInvulnerable => state == PlayerState.Rolling;
    public int FacingSign { get; private set; } = 1;

    private Rigidbody2D body;
    private Camera mainCamera;
    private Vector2 moveInput;
    private PlayerState state;
    private float nextGuardTime;
    private float nextRollTime;
    private bool isGrounded;
    private bool isAttackFacingLocked;
    private float lastGroundedTime = float.NegativeInfinity;
    private bool coyoteJumpConsumed;
    private IDamageable damageReceiver;
    private PhysicsMaterial2D frictionlessMaterial;
    private PlayerComboCounter comboCounter;


    private enum PlayerState
    {
        Normal,
        Attacking,
        Parrying,
        Guarding,
        Rolling
    }

    private void Awake()
    {
        body = GetComponent<Rigidbody2D>();
        mainCamera = Camera.main;
        ResolveEntityInterfaces();
        SetupPlayerStatusSystems();

        if (preventWallSticking)
            ApplyFrictionlessMovementMaterial();

        if (attackHitbox == null)
            attackHitbox = GetComponentInChildren<PlayerAttackHitbox>(true);

        if (characterSprite == null)
            characterSprite = GetComponentInChildren<SpriteRenderer>(true);

        if (animator == null)
            animator = GetComponentInChildren<Animator>(true);

        if (attackHitbox != null)
            attackHitbox.EndAttack();

        SetupInventorySystems();
    }

    private void OnDisable()
    {
        StopAllCoroutines();
        if (attackHitbox != null)
            attackHitbox.EndAttack();
        isAttackFacingLocked = false;
        state = PlayerState.Normal;
    }

    private void OnDestroy()
    {
        if (frictionlessMaterial != null)
            Destroy(frictionlessMaterial);
    }

    private void Update()
    {
        ReadMovement();
        UpdateGrounded();

        if (state == PlayerState.Normal)
        {
            if (Keyboard.current?.spaceKey.wasPressedThisFrame == true && CanJump())
                Jump();

            if (Mouse.current?.leftButton.wasPressedThisFrame == true)
            {
                FaceMouse();
                StartCoroutine(AttackRoutine());
            }
            else if (Mouse.current?.rightButton.wasPressedThisFrame == true && Time.time >= nextGuardTime)
            {
                StartCoroutine(GuardRoutine());
            }
            else if ((Keyboard.current?.leftShiftKey.wasPressedThisFrame == true ||
                      Keyboard.current?.rightShiftKey.wasPressedThisFrame == true) &&
                     Time.time >= nextRollTime)
            {
                StartCoroutine(RollRoutine());
            }
        }

        if ((state == PlayerState.Parrying || state == PlayerState.Guarding) &&
            Mouse.current?.rightButton.isPressed == false)
        {
            StopAllCoroutines();
            FinishGuard();
        }

        UpdateAnimator();
    }

    private void FixedUpdate()
    {
        if (state == PlayerState.Rolling)
            return;

        float horizontalVelocity = CanMove() ? moveInput.x * moveSpeed : 0f;
        body.linearVelocity = new Vector2(horizontalVelocity, body.linearVelocity.y);

        // 공격 중에는 마우스로 결정한 방향이 이동 방향보다 우선한다.
        if (!isAttackFacingLocked && state == PlayerState.Normal && Mathf.Abs(moveInput.x) > 0.01f)
            SetFacing(moveInput.x > 0f ? 1 : -1);
    }

    private void ReadMovement()
    {
        Keyboard keyboard = Keyboard.current;
        if (keyboard == null)
        {
            moveInput = Vector2.zero;
            return;
        }

        moveInput = new Vector2(
            (keyboard.dKey.isPressed ? 1f : 0f) - (keyboard.aKey.isPressed ? 1f : 0f),
            (keyboard.wKey.isPressed ? 1f : 0f) - (keyboard.sKey.isPressed ? 1f : 0f));
        moveInput = Vector2.ClampMagnitude(moveInput, 1f);
    }

    private void ApplyFrictionlessMovementMaterial()
    {
        frictionlessMaterial = new PhysicsMaterial2D("Player Frictionless")
        {
            friction = 0f,
            bounciness = 0f,
            hideFlags = HideFlags.HideAndDontSave
        };

        Collider2D[] colliders = GetComponentsInChildren<Collider2D>(true);
        foreach (Collider2D playerCollider in colliders)
        {
            if (playerCollider != null && !playerCollider.isTrigger)
                playerCollider.sharedMaterial = frictionlessMaterial;
        }
    }

    private void SetupPlayerStatusSystems()
    {
        comboCounter = GetComponent<PlayerComboCounter>();
        if (comboCounter == null)
            comboCounter = gameObject.AddComponent<PlayerComboCounter>();

        PlayerHealth playerHealth = damageReceiver as PlayerHealth;
        PlayerStatusHUD.GetOrCreate().Bind(playerHealth, comboCounter);
    }

    private void SetupInventorySystems()
    {
        PlayerInventory inventory = GetComponent<PlayerInventory>();
        if (inventory == null)
            inventory = gameObject.AddComponent<PlayerInventory>();
        inventory.Initialize();

        RelicSkillController skills = GetComponent<RelicSkillController>();
        if (skills == null)
            skills = gameObject.AddComponent<RelicSkillController>();

        PlayerInventoryHUD.GetOrCreate().Bind(inventory, skills, comboCounter);
    }

    private bool CanMove() => state == PlayerState.Normal || state == PlayerState.Attacking;

    private void Jump()
    {
        coyoteJumpConsumed = true;
        lastGroundedTime = float.NegativeInfinity;
        body.linearVelocity = new Vector2(body.linearVelocity.x, jumpForce);
        SetAnimatorTrigger("Jump");
    }

    private bool CanJump()
    {
        return !coyoteJumpConsumed && Time.time <= lastGroundedTime + coyoteTime;
    }

    private IEnumerator AttackRoutine()
    {
        if (attackHitbox == null)
        {
            Debug.LogError("PlayerAttackHitbox reference is missing.", this);
            yield break;
        }

        state = PlayerState.Attacking;
        isAttackFacingLocked = true;
        body.linearVelocity = new Vector2(0f, body.linearVelocity.y);
        SetAnimatorTrigger("Attack");

        yield return new WaitForSeconds(attackWindup);
        attackHitbox.BeginAttack(Vector2.right * FacingSign);
        yield return new WaitForSeconds(attackActiveTime);
        attackHitbox.EndAttack();
        yield return new WaitForSeconds(attackRecovery);
        isAttackFacingLocked = false;
        state = PlayerState.Normal;
    }

    private IEnumerator GuardRoutine()
    {
        state = PlayerState.Parrying;
        body.linearVelocity = new Vector2(0f, body.linearVelocity.y);
        SetAnimatorBool("Guard", true);
        SetAnimatorBool("Parry", true);
        Debug.Log($"[Player] 패링 시작 ({parryWindow:0.00}초)", this);

        yield return new WaitForSeconds(parryWindow);

        if (state == PlayerState.Parrying)
        {
            state = PlayerState.Guarding;
            SetAnimatorBool("Parry", false);
            Debug.Log("[Player] 패링 종료 → 방어 상태 시작", this);
        }

        while (Mouse.current?.rightButton.isPressed == true)
            yield return null;

        FinishGuard();
    }

    private void FinishGuard()
    {
        if (state != PlayerState.Parrying && state != PlayerState.Guarding)
            return;

        state = PlayerState.Normal;
        nextGuardTime = Time.time + guardCooldown;
        SetAnimatorBool("Parry", false);
        SetAnimatorBool("Guard", false);
        Debug.Log($"[Player] 방어 종료 (쿨타임 {guardCooldown:0.00}초)", this);
    }

    private IEnumerator RollRoutine()
    {
        state = PlayerState.Rolling;
        nextRollTime = Time.time + rollCooldown;

        float rollDirection = Mathf.Abs(moveInput.x) > 0.01f ? Mathf.Sign(moveInput.x) : FacingSign;
        SetFacing(rollDirection > 0f ? 1 : -1);
        SetAnimatorTrigger("Roll");

        float endTime = Time.time + rollDuration;
        while (Time.time < endTime)
        {
            body.linearVelocity = new Vector2(rollDirection * rollSpeed, body.linearVelocity.y);
            yield return new WaitForFixedUpdate();
        }

        body.linearVelocity = new Vector2(0f, body.linearVelocity.y);
        state = PlayerState.Normal;
    }

    public PlayerHitResult ReceiveEnemyAttack(int damage, GameObject attacker, Vector2 hitPoint)
    {
        OathSystem oathSystem = OathSystem.Instance;
        if (oathSystem != null)
            oathSystem.RegisterEnemyAttack(attacker);

        if (IsInvulnerable)
            return PlayerHitResult.Invulnerable;

        if (IsParrying)
        {
            IGroggyReceiver groggyReceiver = FindInterface<IGroggyReceiver>(attacker);
            if (groggyReceiver != null)
                groggyReceiver.EnterGroggy(groggyDuration, gameObject);
            SetAnimatorTrigger("ParrySuccess");
            Debug.Log($"[Player] 패링 성공! 공격자: {GetAttackerName(attacker)}", this);
            return PlayerHitResult.Parried;
        }

        if (IsGuarding)
        {
            Debug.Log($"[Player] 방어 성공! 피해 {damage} 무효화, 공격자: {GetAttackerName(attacker)}", this);
            return PlayerHitResult.Blocked;
        }

        Vector2 hitDirection = attacker != null
            ? ((Vector2)transform.position - (Vector2)attacker.transform.position).normalized
            : Vector2.zero;
        ForwardDamageToEntity(damage, hitPoint, hitDirection);
        return PlayerHitResult.Damaged;
    }

    private void ForwardDamageToEntity(int damage, Vector2 hitPoint, Vector2 hitDirection)
    {
        if (damageReceiver == null)
        {
            Debug.LogWarning(
                "[Player] IDamageable을 구현한 엔티티 컴포넌트가 없어 피해를 전달하지 못했습니다.", this);
            return;
        }

        damageReceiver.TakeDamage(damage, hitPoint, hitDirection);
        SetAnimatorTrigger("Hit");
    }

    private void ResolveEntityInterfaces()
    {
        damageReceiver = damageReceiverBehaviour as IDamageable;
        if (damageReceiver != null)
            return;

        MonoBehaviour[] behaviours = GetComponents<MonoBehaviour>();
        foreach (MonoBehaviour behaviour in behaviours)
        {
            if (behaviour is IDamageable receiver)
            {
                damageReceiver = receiver;
                damageReceiverBehaviour = behaviour;
                return;
            }
        }

        if (damageReceiverBehaviour != null)
        {
            Debug.LogError("Damage Receiver Behaviour는 IDamageable을 구현해야 합니다.", this);
            damageReceiverBehaviour = null;
        }

        // 별도의 엔티티 체력 컴포넌트가 아직 없다면 기본 구현을 자동으로 연결한다.
        PlayerHealth playerHealth = GetComponent<PlayerHealth>();
        if (playerHealth == null)
            playerHealth = gameObject.AddComponent<PlayerHealth>();

        damageReceiver = playerHealth;
        damageReceiverBehaviour = playerHealth;
    }

    private void FaceMouse()
    {
        if (mainCamera == null || Mouse.current == null)
            return;

        Vector3 mouseWorld = mainCamera.ScreenToWorldPoint(Mouse.current.position.ReadValue());
        SetFacing(mouseWorld.x >= transform.position.x ? 1 : -1);
    }

    private void SetFacing(int sign)
    {
        FacingSign = sign;

        if (characterSprite != null)
            characterSprite.flipX = sign < 0;

        // 별도의 Pivot 없이 히트박스 자체를 현재 전방으로 옮긴다.
        if (attackHitbox != null)
        {
            Transform hitboxTransform = attackHitbox.transform;
            Vector3 position = hitboxTransform.localPosition;
            position.x = Mathf.Abs(position.x) * sign;
            hitboxTransform.localPosition = position;
        }
    }

    private void UpdateGrounded()
    {
        isGrounded = groundCheck != null && Physics2D.OverlapCircle(
            groundCheck.position, groundCheckRadius, groundLayer) != null;

        // 점프 직후 GroundCheck가 잠시 바닥과 겹쳐도 코요테 점프가 다시 충전되지 않게 한다.
        if (isGrounded && body.linearVelocity.y <= 0.01f)
        {
            lastGroundedTime = Time.time;
            coyoteJumpConsumed = false;
        }
    }

    private void UpdateAnimator()
    {
        if (animator == null)
            return;

        float horizontalSpeed = Mathf.Abs(body.linearVelocity.x);
        bool isWalking = state == PlayerState.Normal && isGrounded &&
                         horizontalSpeed > walkingAnimationThreshold;

        animator.SetFloat("Speed", horizontalSpeed);
        animator.SetFloat("VerticalSpeed", body.linearVelocity.y);
        animator.SetBool("Grounded", isGrounded);
        animator.SetBool("IsWalking", isWalking);
    }

    private void SetAnimatorTrigger(string parameterName)
    {
        if (animator != null)
            animator.SetTrigger(parameterName);
    }

    private void SetAnimatorBool(string parameterName, bool value)
    {
        if (animator != null)
            animator.SetBool(parameterName, value);
    }

    private static T FindInterface<T>(GameObject target) where T : class
    {
        if (target == null)
            return null;

        MonoBehaviour[] behaviours = target.GetComponentsInParent<MonoBehaviour>();
        foreach (MonoBehaviour behaviour in behaviours)
        {
            if (behaviour is T result)
                return result;
        }

        return null;
    }

    private static string GetAttackerName(GameObject attacker)
    {
        return attacker != null ? attacker.name : "Unknown";
    }

    private void OnDrawGizmosSelected()
    {
        if (groundCheck == null)
            return;

        Gizmos.color = Color.yellow;
        Gizmos.DrawWireSphere(groundCheck.position, groundCheckRadius);
    }
}

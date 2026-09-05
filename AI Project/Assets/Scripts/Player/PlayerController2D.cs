using System.Collections;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.InputSystem;

[RequireComponent(typeof(Rigidbody2D))]
public sealed class PlayerController2D : MonoBehaviour, IDamageable
{
    [Header("Movement")]
    [SerializeField, Min(0f)] private float moveSpeed = 6f;
    [SerializeField, Min(0f)] private float jumpForce = 12f;
    [SerializeField] private Transform groundCheck;
    [SerializeField, Min(0.01f)] private float groundCheckRadius = 0.15f;
    [SerializeField] private LayerMask groundLayer;

    [Header("Attack")]
    [SerializeField] private PlayerAttackHitbox attackHitbox;
    [SerializeField] private Transform attackPivot;
    [SerializeField, Min(0f)] private float attackWindup = 0.08f;
    [SerializeField, Min(0.01f)] private float attackActiveTime = 0.12f;
    [SerializeField, Min(0f)] private float attackRecovery = 0.2f;

    [Header("Guard / Parry")]
    [SerializeField, Min(0.01f)] private float parryWindow = 0.2f;
    [SerializeField, Min(0f)] private float guardCooldown = 0.5f;
    [SerializeField, Min(0f)] private float groggyDuration = 1.5f;

    [Header("Roll")]
    [SerializeField, Min(0f)] private float rollSpeed = 12f;
    [SerializeField, Min(0.01f)] private float rollDuration = 0.25f;
    [SerializeField, Min(0f)] private float rollCooldown = 0.5f;

    [Header("Visuals (Optional)")]
    [SerializeField] private SpriteRenderer characterSprite;
    [SerializeField] private Animator animator;

    [Header("Health")]
    [SerializeField, Min(1)] private int maxHealth = 5;
    [SerializeField] private UnityEvent<int, int> onHealthChanged;
    [SerializeField] private UnityEvent onDied;

    public bool IsParrying => state == PlayerState.Parrying;
    public bool IsGuarding => state == PlayerState.Guarding;
    public bool IsInvulnerable => state == PlayerState.Rolling;
    public int FacingSign { get; private set; } = 1;
    public int CurrentHealth { get; private set; }

    private Rigidbody2D body;
    private Camera mainCamera;
    private Vector2 moveInput;
    private PlayerState state;
    private float nextGuardTime;
    private float nextRollTime;
    private bool isGrounded;

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
        CurrentHealth = maxHealth;

        if (attackHitbox == null)
            attackHitbox = GetComponentInChildren<PlayerAttackHitbox>(true);

        ResolveAttackPivot();

        if (characterSprite == null)
            characterSprite = GetComponentInChildren<SpriteRenderer>(true);

        if (attackHitbox != null)
            attackHitbox.EndAttack();
    }

    private void OnDisable()
    {
        StopAllCoroutines();
        if (attackHitbox != null)
            attackHitbox.EndAttack();
        state = PlayerState.Normal;
    }

    private void Update()
    {
        ReadMovement();
        UpdateGrounded();

        if (state == PlayerState.Normal)
        {
            if (Keyboard.current?.spaceKey.wasPressedThisFrame == true && isGrounded)
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

        if (state == PlayerState.Normal && Mathf.Abs(moveInput.x) > 0.01f)
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

    private bool CanMove() => state == PlayerState.Normal || state == PlayerState.Attacking;

    private void Jump()
    {
        body.linearVelocity = new Vector2(body.linearVelocity.x, jumpForce);
        SetAnimatorTrigger("Jump");
    }

    private IEnumerator AttackRoutine()
    {
        if (attackHitbox == null)
        {
            Debug.LogError("PlayerAttackHitbox reference is missing.", this);
            yield break;
        }

        state = PlayerState.Attacking;
        body.linearVelocity = new Vector2(0f, body.linearVelocity.y);
        SetAnimatorTrigger("Attack");

        yield return new WaitForSeconds(attackWindup);
        attackHitbox.BeginAttack(Vector2.right * FacingSign);
        yield return new WaitForSeconds(attackActiveTime);
        attackHitbox.EndAttack();
        yield return new WaitForSeconds(attackRecovery);
        state = PlayerState.Normal;
    }

    private IEnumerator GuardRoutine()
    {
        state = PlayerState.Parrying;
        body.linearVelocity = new Vector2(0f, body.linearVelocity.y);
        SetAnimatorBool("Guard", true);
        SetAnimatorBool("Parry", true);

        yield return new WaitForSeconds(parryWindow);

        if (state == PlayerState.Parrying)
        {
            state = PlayerState.Guarding;
            SetAnimatorBool("Parry", false);
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
        if (IsInvulnerable)
            return PlayerHitResult.Invulnerable;

        if (IsParrying)
        {
            IEnemyStaggerable staggerable = FindInterface<IEnemyStaggerable>(attacker);
            staggerable?.EnterGroggy(groggyDuration);
            SetAnimatorTrigger("ParrySuccess");
            return PlayerHitResult.Parried;
        }

        if (IsGuarding)
            return PlayerHitResult.Blocked;

        ApplyDamage(damage, hitPoint);
        return PlayerHitResult.Damaged;
    }

    public void TakeDamage(int damage, Vector2 hitPoint, Vector2 hitDirection)
    {
        ReceiveEnemyAttack(damage, null, hitPoint);
    }

    private void ApplyDamage(int damage, Vector2 hitPoint)
    {
        if (damage <= 0 || CurrentHealth <= 0)
            return;

        CurrentHealth = Mathf.Max(0, CurrentHealth - damage);
        onHealthChanged?.Invoke(CurrentHealth, maxHealth);
        SetAnimatorTrigger("Hit");

        if (CurrentHealth == 0)
        {
            body.linearVelocity = Vector2.zero;
            enabled = false;
            onDied?.Invoke();
        }
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

        if (attackPivot != null)
        {
            Vector3 position = attackPivot.localPosition;
            position.x = Mathf.Abs(position.x) * sign;
            attackPivot.localPosition = position;

            Vector3 scale = attackPivot.localScale;
            scale.x = Mathf.Abs(scale.x) * sign;
            attackPivot.localScale = scale;
        }
    }

    private void ResolveAttackPivot()
    {
        if (attackPivot == transform)
        {
            Debug.LogWarning(
                "Attack Pivot에는 Player 자신이 아니라 공격 히트박스의 부모 오브젝트를 지정해야 합니다. " +
                "잘못된 참조를 자동으로 해제합니다.", this);
            attackPivot = null;
        }

        if (attackPivot != null || attackHitbox == null)
            return;

        Transform candidate = attackHitbox.transform.parent;
        if (candidate != null && candidate != transform)
            attackPivot = candidate;
    }

    private void OnValidate()
    {
        if (attackPivot == transform)
            attackPivot = null;
    }

    private void UpdateGrounded()
    {
        isGrounded = groundCheck != null && Physics2D.OverlapCircle(
            groundCheck.position, groundCheckRadius, groundLayer) != null;
    }

    private void UpdateAnimator()
    {
        if (animator == null)
            return;

        animator.SetFloat("Speed", Mathf.Abs(body.linearVelocity.x));
        animator.SetFloat("VerticalSpeed", body.linearVelocity.y);
        animator.SetBool("Grounded", isGrounded);
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

    private void OnDrawGizmosSelected()
    {
        if (groundCheck == null)
            return;

        Gizmos.color = Color.yellow;
        Gizmos.DrawWireSphere(groundCheck.position, groundCheckRadius);
    }
}

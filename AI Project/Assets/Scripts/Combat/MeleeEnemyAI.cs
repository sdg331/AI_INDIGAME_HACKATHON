using System.Collections;
using UnityEngine;

/// <summary>
/// Unity 6000.3.11f1 기준 근접 적 AI
/// - IDamageable, IGroggyReceiver 연동
/// - EnemyAttackHitbox 제어 및 스턴/넉백/그로기 처리
/// - linearVelocity를 활용한 이동, 감속, 점프 제어
/// </summary>

[RequireComponent(typeof(Rigidbody2D))]
[RequireComponent(typeof(Collider2D))]
public sealed class MeleeEnemyAI : MonoBehaviour, IDamageable, IGroggyReceiver
{
    private enum AIState
    {
        Idle,       // 대기
        Chase,      // 플레이어 추적
        Windup,     // 공격 선딜레이 (감속 정지)
        Attack,     // 공격 실행 (Hitbox 활성화)
        Recovery    // 공격 후딜레이
    }

    [Header("Components")]
    [SerializeField] private Animator animator;
    [SerializeField] private EnemyAttackHitbox attackHitbox;

    [Header("Target")]
    [SerializeField] private Transform player;
    [SerializeField] private string playerTag = "Player";

    [Header("Detection")]
    [Tooltip("이 범위 안에 들어오면 추적을 시작합니다.")]
    [SerializeField] private float detectionRange = 6f;
    [Tooltip("추적 중 이 범위를 벗어나면 추적을 포기합니다.")]
    [SerializeField] private float loseRange = 9f;

    [Header("Movement")]
    [SerializeField] private float moveSpeed = 2.5f;
    [SerializeField] private float stopDistance = 1.0f;

    [Header("Attack Settings")]
    [Tooltip("이 거리 안에 들어오면 감속하며 공격을 준비합니다.")]
    [SerializeField] private float attackRange = 1.2f;
    [SerializeField] private float decelerationRate = 12f;
    [SerializeField] private float attackWindupTime = 0.4f;
    [SerializeField] private float attackActiveTime = 0.2f;
    [SerializeField] private float attackRecoveryTime = 0.8f;
    [SerializeField] private bool cancelWindupIfOutOfRange = true;

    [Header("Jump")]
    [SerializeField] private float jumpForce = 7f;
    [SerializeField] private float jumpHeightThreshold = 1.0f;
    [SerializeField] private float jumpCooldown = 0.5f;
    [SerializeField] private Transform groundCheck;
    [SerializeField] private float groundCheckRadius = 0.15f;
    [SerializeField] private LayerMask groundLayer;

    [Header("Collision")]
    [SerializeField] private bool ignoreCollisionWithPlayer = true;

    [Header("Health & HitStun")]
    [SerializeField, Min(1)] private int maxHealth = 5;
    [SerializeField] private float knockbackForce = 4f;
    [SerializeField] private float hitStunDuration = 0.25f;

    // Animator Parameter Hashes
    private static readonly int SpeedAnimHash = Animator.StringToHash("Speed");
    private static readonly int AttackAnimHash = Animator.StringToHash("Attack");
    private static readonly int HitTriggerHash = Animator.StringToHash("Hit");
    private static readonly int IsGroundedAnimHash = Animator.StringToHash("IsGrounded");

    private Rigidbody2D rb;
    private Collider2D bodyCollider;
    private AIState currentState = AIState.Idle;

    private float stateTimer;
    private int currentHealth;
    private bool isGrounded;
    private bool isDead;
    private bool isStunned;
    private float stunTimer;
    private float lastJumpTime = -999f;

    private void Awake()
    {
        rb = GetComponent<Rigidbody2D>();
        bodyCollider = GetComponent<Collider2D>();
        currentHealth = maxHealth;

        if (loseRange < detectionRange)
            loseRange = detectionRange;

        if (attackHitbox != null)
        {
            attackHitbox.Initialize(this);
            attackHitbox.EndAttack();
        }

        if (player == null)
        {
            GameObject found = GameObject.FindGameObjectWithTag(playerTag);
            if (found != null)
                player = found.transform;
        }

        if (ignoreCollisionWithPlayer)
            IgnoreCollisionWithPlayer();
    }

    private void OnEnable()
    {
        // 그로기 상태 등에서 회복되어 스크립트가 다시 켜졌을 때 초기화
        ChangeState(AIState.Idle);
        isStunned = false;
    }

    private void OnDisable()
    {
        // EnemyGroggyController 등에 의해 비활성화될 때 공격 히트박스 안전 OFF
        if (attackHitbox != null)
            attackHitbox.EndAttack();

        if (rb != null)
            rb.linearVelocity = new Vector2(0f, rb.linearVelocity.y);
    }

    private void Update()
    {
        if (isDead) return;

        UpdateGroundedState();
        HandleStun();

        if (isStunned) return;
        if (player == null) return;

        float distanceToPlayer = Vector2.Distance(transform.position, player.position);

        UpdateAIState(distanceToPlayer);
        HandleJumpCheck();
        UpdateAnimatorParams();
    }

    private void FixedUpdate()
    {
        if (isDead || isStunned) return;
        if (player == null) return;

        switch (currentState)
        {
            case AIState.Idle:
            case AIState.Attack:
            case AIState.Recovery:
                rb.linearVelocity = new Vector2(0f, rb.linearVelocity.y);
                break;

            case AIState.Chase:
                MoveTowardsPlayer();
                break;

            case AIState.Windup:
                DecelerateToStop();
                break;
        }
    }

    // -------------------- 상태 및 AI 로직 --------------------

    private void UpdateAIState(float distance)
    {
        switch (currentState)
        {
            case AIState.Idle:
                if (distance <= detectionRange)
                    ChangeState(AIState.Chase);
                break;

            case AIState.Chase:
                if (distance <= attackRange)
                    ChangeState(AIState.Windup);
                else if (distance > loseRange)
                    ChangeState(AIState.Idle);
                break;

            case AIState.Windup:
                stateTimer += Time.deltaTime;

                if (cancelWindupIfOutOfRange && distance > attackRange)
                {
                    ChangeState(AIState.Chase);
                    break;
                }

                if (stateTimer >= attackWindupTime)
                {
                    ChangeState(AIState.Attack);
                    TriggerAttack();
                }
                break;

            case AIState.Attack:
                stateTimer += Time.deltaTime;

                if (stateTimer >= attackActiveTime)
                {
                    if (attackHitbox != null)
                        attackHitbox.EndAttack();

                    ChangeState(AIState.Recovery);
                }
                break;

            case AIState.Recovery:
                stateTimer += Time.deltaTime;

                if (stateTimer >= attackRecoveryTime)
                {
                    ChangeState(distance <= loseRange ? AIState.Chase : AIState.Idle);
                }
                break;
        }
    }

    private void ChangeState(AIState newState)
    {
        currentState = newState;
        stateTimer = 0f;
    }

    // -------------------- 이동 & 점프 --------------------

    private void MoveTowardsPlayer()
    {
        float distance = Vector2.Distance(transform.position, player.position);

        if (distance <= stopDistance)
        {
            rb.linearVelocity = new Vector2(0f, rb.linearVelocity.y);
            return;
        }

        float direction = Mathf.Sign(player.position.x - transform.position.x);
        rb.linearVelocity = new Vector2(direction * moveSpeed, rb.linearVelocity.y);

        FlipTowards(direction);
    }

    private void DecelerateToStop()
    {
        float newX = Mathf.MoveTowards(rb.linearVelocity.x, 0f, decelerationRate * Time.fixedDeltaTime);
        rb.linearVelocity = new Vector2(newX, rb.linearVelocity.y);
    }

    private void HandleJumpCheck()
    {
        if (currentState != AIState.Chase || !isGrounded) return;
        if (Time.time - lastJumpTime < jumpCooldown) return;

        float heightDifference = player.position.y - transform.position.y;
        if (heightDifference >= jumpHeightThreshold)
        {
            rb.linearVelocity = new Vector2(rb.linearVelocity.x, 0f);
            rb.AddForce(Vector2.up * jumpForce, ForceMode2D.Impulse);
            lastJumpTime = Time.time;
        }
    }

    private void FlipTowards(float direction)
    {
        if (Mathf.Approximately(direction, 0f)) return;

        Vector3 scale = transform.localScale;
        scale.x = Mathf.Abs(scale.x) * Mathf.Sign(direction);
        transform.localScale = scale;
    }

    // -------------------- 공격 제어 (EnemyAttackHitbox 연동) --------------------

    private void TriggerAttack()
    {
        if (animator != null)
            animator.SetTrigger(AttackAnimHash);

        if (attackHitbox != null)
        {
            Vector2 attackDirection = new Vector2(Mathf.Sign(transform.localScale.x), 0f);
            attackHitbox.BeginAttack(attackDirection);
        }
    }

    // -------------------- 피격 & 무력화 처리 (IDamageable, IGroggyReceiver) --------------------

    public void TakeDamage(int damage, Vector2 hitPoint, Vector2 hitDirection)
    {
        if (isDead) return;

        currentHealth -= damage;

        if (animator != null)
            animator.SetTrigger(HitTriggerHash);

        if (currentState == AIState.Idle)
            ChangeState(AIState.Chase);

        // 공격 도중 맞으면 공격 히트박스 캔슬
        if (attackHitbox != null)
            attackHitbox.EndAttack();

        // Unity 6 linearVelocity 초기화 후 넉백 적용
        rb.linearVelocity = Vector2.zero;
        rb.AddForce(hitDirection.normalized * knockbackForce, ForceMode2D.Impulse);

        isStunned = true;
        stunTimer = hitStunDuration;

        if (currentHealth <= 0)
        {
            Die();
        }
    }

    public void EnterGroggy(float duration, GameObject source)
    {
        // EnemyGroggyController가 호출하는 인터페이스 구현
        // 그로기 진입 시 실행 중이던 공격 판정을 취소
        if (attackHitbox != null)
            attackHitbox.EndAttack();

        rb.linearVelocity = new Vector2(0f, rb.linearVelocity.y);
    }

    private void HandleStun()
    {
        if (!isStunned) return;

        stunTimer -= Time.deltaTime;
        if (stunTimer <= 0f)
            isStunned = false;
    }

    private void Die()
    {
        isDead = true;
        rb.linearVelocity = Vector2.zero;

        if (attackHitbox != null)
            attackHitbox.EndAttack();

        // 사망 처리 (필요시 디스트로이 또는 래그돌/애니메이션 전환)
        this.enabled = false;
    }

    // -------------------- 유틸리티 --------------------

    private void UpdateGroundedState()
    {
        if (groundCheck == null)
        {
            isGrounded = true;
            return;
        }

        isGrounded = Physics2D.OverlapCircle(groundCheck.position, groundCheckRadius, groundLayer);
    }

    private void UpdateAnimatorParams()
    {
        if (animator == null) return;

        animator.SetFloat(SpeedAnimHash, Mathf.Abs(rb.linearVelocity.x));
        animator.SetBool(IsGroundedAnimHash, isGrounded);
    }

    private void IgnoreCollisionWithPlayer()
    {
        if (player == null || bodyCollider == null) return;

        Collider2D playerCollider = player.GetComponent<Collider2D>();
        if (playerCollider == null)
            playerCollider = player.GetComponentInChildren<Collider2D>();

        if (playerCollider != null)
            Physics2D.IgnoreCollision(bodyCollider, playerCollider, true);
    }

    private void OnDrawGizmosSelected()
    {
        Gizmos.color = Color.cyan;
        Gizmos.DrawWireSphere(transform.position, detectionRange);

        Gizmos.color = new Color(0f, 0.5f, 1f, 0.5f);
        Gizmos.DrawWireSphere(transform.position, loseRange);

        Gizmos.color = Color.red;
        Gizmos.DrawWireSphere(transform.position, attackRange);

        if (groundCheck != null)
        {
            Gizmos.color = Color.green;
            Gizmos.DrawWireSphere(groundCheck.position, groundCheckRadius);
        }
    }
}
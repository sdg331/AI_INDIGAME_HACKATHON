using UnityEngine;

/// <summary>
/// 근접 공격형 적 AI.
/// - 조정 가능한 탐지 범위(detectionRange) 안에 플레이어가 들어오면 추적 시작
/// - 한 번 감지되면 loseRange 밖으로 나가기 전까지는 계속 추적 (히스테리시스)
/// - 공격 사거리(attackRange) 진입 시 "천천히 감속하며 정지 -> 공격 준비(Windup) ->
///   공격 실행(Attack) -> 회복 대기(Recovery) -> 다시 추적" 순서로 동작
/// - 플레이어가 일정 높이 이상 위에 있으면 점프
/// - 플레이어와 물리적으로 충돌하지 않도록 콜라이더 충돌 무시 처리
/// - IDamageable을 구현하여 플레이어 공격을 받을 수 있음
/// Unity 6000.3.11f1 기준 (Rigidbody2D.velocity -> linearVelocity 반영)
/// </summary>
[RequireComponent(typeof(Rigidbody2D))]
[RequireComponent(typeof(Collider2D))]
public sealed class MeleeEnemyAI : MonoBehaviour, IDamageable
{
    private enum AIState
    {
        Idle,       // 플레이어 미감지 상태
        Chase,      // 플레이어 추적 중
        Windup,     // 공격 사거리 진입, 감속하며 공격 준비 중
        Attack,     // 공격 판정 발동 중
        Recovery    // 공격 후 다시 추적하기 전 대기(경직) 상태
    }

    [Header("Target")]
    [SerializeField] private Transform player;
    [SerializeField] private string playerTag = "Player";

    [Header("Detection")]
    [Tooltip("이 범위 안에 플레이어가 들어오면 추적을 시작합니다.")]
    [SerializeField] private float detectionRange = 6f;
    [Tooltip("추적 중일 때, 이 범위를 벗어나면 추적을 포기하고 Idle로 돌아갑니다. (detectionRange보다 크게 설정 권장)")]
    [SerializeField] private float loseRange = 9f;

    [Header("Movement")]
    [SerializeField] private float moveSpeed = 2.5f;
    [SerializeField] private float stopDistance = 1.0f;  // 너무 붙지 않도록 최소 거리

    [Header("Attack Timing")]
    [Tooltip("이 거리 안에 들어오면 감속하며 공격을 준비합니다 (Windup 상태 진입).")]
    [SerializeField] private float attackRange = 1.2f;
    [Tooltip("Windup 상태에서 속도가 0으로 줄어드는 감속량(초당). 값이 클수록 더 빨리 멈춥니다.")]
    [SerializeField] private float decelerationRate = 10f;
    [Tooltip("공격 준비(감속 완료 후 대기) 시간(초). 이 시간이 지나면 실제 공격이 발동합니다.")]
    [SerializeField] private float attackWindupTime = 0.5f;
    [Tooltip("공격 판정(히트박스)이 켜져 있는 시간(초).")]
    [SerializeField] private float attackActiveTime = 0.15f;
    [Tooltip("공격이 끝난 후, 다시 추적을 시작하기까지 대기하는 회복 시간(초).")]
    [SerializeField] private float attackRecoveryTime = 0.8f;
    [Tooltip("Windup 도중 플레이어가 attackRange 밖으로 벗어나면 추적으로 되돌아갑니다.")]
    [SerializeField] private bool cancelWindupIfOutOfRange = true;

    [Header("Jump")]
    [SerializeField] private float jumpForce = 7f;
    [SerializeField] private float jumpHeightThreshold = 1.0f; // 플레이어와의 y차이가 이 값 이상이면 점프
    [SerializeField] private float jumpCooldown = 0.5f;
    [SerializeField] private Transform groundCheck;
    [SerializeField] private float groundCheckRadius = 0.15f;
    [SerializeField] private LayerMask groundLayer;

    [Header("Attack")]
    [SerializeField] private int attackDamage = 1;
    [SerializeField] private Collider2D attackHitbox; // 트리거로 사용, 평소엔 비활성화

    [Header("Collision")]
    [Tooltip("체크하면 이 오브젝트의 몸체 콜라이더와 플레이어 콜라이더 간의 물리적 충돌(밀림)을 무시합니다.")]
    [SerializeField] private bool ignoreCollisionWithPlayer = true;

    [Header("Health")]
    [SerializeField, Min(1)] private int maxHealth = 3;
    [SerializeField] private float knockbackForce = 5f;
    [SerializeField] private float hitStunDuration = 0.2f;

    private Rigidbody2D rb;
    private Collider2D bodyCollider;
    private AIState currentState = AIState.Idle;
    private float stateTimer;
    private int currentHealth;
    private bool isGrounded;
    private bool isDead;
    private bool isStunned;
    private float lastJumpTime = -999f;
    private float stunTimer;

    private void Awake()
    {
        rb = GetComponent<Rigidbody2D>();
        bodyCollider = GetComponent<Collider2D>();
        currentHealth = maxHealth;

        // loseRange가 detectionRange보다 작으면 논리적으로 어긋나므로 자동 보정
        if (loseRange < detectionRange)
            loseRange = detectionRange;

        if (attackHitbox != null)
        {
            attackHitbox.isTrigger = true;
            attackHitbox.enabled = false;
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

    private void IgnoreCollisionWithPlayer()
    {
        if (player == null || bodyCollider == null) return;

        Collider2D playerCollider = player.GetComponent<Collider2D>();
        if (playerCollider == null)
            playerCollider = player.GetComponentInChildren<Collider2D>();

        if (playerCollider != null)
            Physics2D.IgnoreCollision(bodyCollider, playerCollider, true);
    }

    private void Update()
    {
        if (isDead) return;

        UpdateGroundedState();
        HandleStun();

        if (isStunned) return;
        if (player == null) return;

        float distance = Vector2.Distance(transform.position, player.position);

        UpdateState(distance);
        HandleJumpCheck();
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
                // 정지 상태 (Attack/Recovery는 제자리에서 처리)
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

    // -------------------- 상태 갱신 --------------------

    private void UpdateState(float distance)
    {
        switch (currentState)
        {
            case AIState.Idle:
                // 탐지 범위 안에 들어오면 추적 시작
                if (distance <= detectionRange)
                    ChangeState(AIState.Chase);
                break;

            case AIState.Chase:
                if (distance <= attackRange)
                    ChangeState(AIState.Windup);
                else if (distance > loseRange)
                    ChangeState(AIState.Idle); // 완전히 놓침
                break;

            case AIState.Windup:
                stateTimer += Time.deltaTime;

                if (cancelWindupIfOutOfRange && distance > attackRange)
                {
                    ChangeState(AIState.Chase); // 준비 중 플레이어가 벗어나면 다시 추적
                    break;
                }

                if (stateTimer >= attackWindupTime)
                {
                    ChangeState(AIState.Attack);
                    EnableAttackHitbox();
                }
                break;

            case AIState.Attack:
                stateTimer += Time.deltaTime;

                if (stateTimer >= attackActiveTime)
                {
                    DisableAttackHitbox();
                    ChangeState(AIState.Recovery);
                }
                break;

            case AIState.Recovery:
                stateTimer += Time.deltaTime;

                if (stateTimer >= attackRecoveryTime)
                {
                    // 회복이 끝나면 플레이어가 아직 범위 안이면 다시 추적, 아니면 Idle
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

    // -------------------- 이동 --------------------

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

    // Windup 상태에서 서서히 속도를 0으로 줄이는 감속 처리
    private void DecelerateToStop()
    {
        float newX = Mathf.MoveTowards(rb.linearVelocity.x, 0f, decelerationRate * Time.fixedDeltaTime);
        rb.linearVelocity = new Vector2(newX, rb.linearVelocity.y);
    }

    private void FlipTowards(float direction)
    {
        if (direction == 0f) return;

        Vector3 scale = transform.localScale;
        scale.x = Mathf.Abs(scale.x) * Mathf.Sign(direction);
        transform.localScale = scale;
    }

    private void UpdateGroundedState()
    {
        if (groundCheck == null)
        {
            isGrounded = true; // groundCheck 미설정 시 기본값
            return;
        }

        isGrounded = Physics2D.OverlapCircle(groundCheck.position, groundCheckRadius, groundLayer);
    }

    // -------------------- 점프 --------------------

    private void HandleJumpCheck()
    {
        // 추적 중일 때만 점프 (공격 준비/공격/회복/대기 중에는 점프하지 않음)
        if (currentState != AIState.Chase) return;
        if (!isGrounded) return;
        if (Time.time - lastJumpTime < jumpCooldown) return;

        float heightDifference = player.position.y - transform.position.y;

        // 플레이어가 나보다 일정 거리 이상 높이 있을 때만 점프
        if (heightDifference >= jumpHeightThreshold)
        {
            Jump();
        }
    }

    private void Jump()
    {
        rb.linearVelocity = new Vector2(rb.linearVelocity.x, 0f); // y 속도 초기화 후 점프
        rb.AddForce(Vector2.up * jumpForce, ForceMode2D.Impulse);
        lastJumpTime = Time.time;
    }

    // -------------------- 공격 --------------------

    // 애니메이션 이벤트에서도 호출 가능: 공격 판정 시작
    public void EnableAttackHitbox()
    {
        if (attackHitbox != null)
            attackHitbox.enabled = true;
    }

    // 애니메이션 이벤트에서도 호출 가능: 공격 판정 종료
    public void DisableAttackHitbox()
    {
        if (attackHitbox != null)
            attackHitbox.enabled = false;
    }

    private void OnTriggerEnter2D(Collider2D other)
    {
        if (attackHitbox == null || !attackHitbox.enabled) return;

        IDamageable target = other.GetComponentInParent<IDamageable>();
        if (target == null || target == (IDamageable)this) return;

        Vector2 hitPoint = other.ClosestPoint(transform.position);
        Vector2 hitDirection = ((Vector2)other.transform.position - (Vector2)transform.position).normalized;

        target.TakeDamage(attackDamage, hitPoint, hitDirection);
    }

    // -------------------- 피격 처리 --------------------

    public void TakeDamage(int damage, Vector2 hitPoint, Vector2 hitDirection)
    {
        if (isDead) return;

        currentHealth -= damage;

        // 피격 시 즉시 플레이어를 인지하도록 강제 전환 (Idle이었어도 반격 유도)
        if (currentState == AIState.Idle)
            ChangeState(AIState.Chase);

        // 넉백
        rb.linearVelocity = Vector2.zero;
        rb.AddForce(hitDirection.normalized * knockbackForce, ForceMode2D.Impulse);

        isStunned = true;
        stunTimer = hitStunDuration;

        if (currentHealth <= 0)
        {
            Die();
        }
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
        DisableAttackHitbox();

        // TODO: 사망 애니메이션, 이펙트, 오브젝트 파괴 등 처리
        // Destroy(gameObject, 1.5f);
    }

    // -------------------- 디버그용 기즈모 --------------------

    private void OnDrawGizmosSelected()
    {
        // 탐지 범위 (추적 시작)
        Gizmos.color = Color.cyan;
        Gizmos.DrawWireSphere(transform.position, detectionRange);

        // 추적 포기 범위
        Gizmos.color = new Color(0f, 0.5f, 1f, 0.5f);
        Gizmos.DrawWireSphere(transform.position, loseRange);

        // 공격 준비/실행 범위
        Gizmos.color = Color.red;
        Gizmos.DrawWireSphere(transform.position, attackRange);

        if (groundCheck != null)
        {
            Gizmos.color = Color.green;
            Gizmos.DrawWireSphere(groundCheck.position, groundCheckRadius);
        }
    }
}

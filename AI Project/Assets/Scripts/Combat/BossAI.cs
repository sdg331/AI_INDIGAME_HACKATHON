using System.Collections;
using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// 탄막형 보스 AI (바르갈 설계 기준 — 직접 근접 공격 없음, 여러 탄막 패턴만 사용).
///
/// 구조:
/// - 이동/거리 유지는 Update/FixedUpdate에서 상시 처리 (보스는 느리게 움직이며 거리를 조절만 함)
/// - 패턴 진행(예고 -> 판정 -> 후딜)은 코루틴으로 순차 실행 (PatternLoop)
/// - 페이즈 전환(HP 50%)과 그로기(HP 10%)는 별도 상태로, 패턴 루프를 일시 정지/종료시킴
///
/// Unity 6000.3.11f1 기준 (Rigidbody2D.velocity -> linearVelocity)
/// 이 프로젝트의 IDamageable은 Assets/Scripts/Combat/CombatContracts.cs 것을 그대로 사용.
/// </summary>
[RequireComponent(typeof(Rigidbody2D))]
[RequireComponent(typeof(Collider2D))]
public sealed class BossAI : MonoBehaviour, IDamageable
{
    private enum BossPhase { Phase1, Phase2 }

    public enum PatternType
    {
        HeartBullet,   // 직선 투사체 하나(또는 여러 발 연속)
        HeartRain,     // 플레이어 머리 위에서 여러 발이 떨어짐
        MagicRingBurst // 보스 주변 원형 범위 판정 (투사체 없이 직접 범위 데미지)
    }

    [System.Serializable]
    public class BossPatternData
    {
        public string patternName = "New Pattern";
        public PatternType type = PatternType.HeartBullet;

        [Header("타이밍 (문서 5.0 예고/판정/후딜 대응)")]
        public float telegraphTime = 0.5f; // 예고: 공격 전 경고 시간
        public float recoveryTime = 0.5f;  // 후딜: 공격 후 안전하게 때릴 수 있는 시간

        [Header("선택 가중치")]
        [Tooltip("여러 패턴 중 무작위로 뽑을 때의 가중치. 값이 클수록 자주 선택됨.")]
        public float weight = 1f;

        [Header("탄막 설정 (타입에 따라 일부만 사용)")]
        public int projectileCount = 1;
        [Tooltip("연속 발사 시 발사 간 간격(초).")]
        public float fireInterval = 0.15f;
        public float projectileSpeed = 6f;
        public int damage = 1;

        [Header("MagicRingBurst 전용")]
        public float ringRadius = 2.5f;
    }

    [Header("Target")]
    [SerializeField] private Transform player;
    [SerializeField] private string playerTag = "Player";

    [Header("Movement (느리게 움직이며 거리만 유지)")]
    [SerializeField] private float moveSpeed = 1.2f;
    [Tooltip("이 거리보다 가까우면 뒤로 물러난다.")]
    [SerializeField] private float preferredMinDistance = 3f;
    [Tooltip("이 거리보다 멀면 다가간다.")]
    [SerializeField] private float preferredMaxDistance = 5f;

    [Header("Health & Phase")]
    [SerializeField] private int maxHealth = 100;
    [Range(0f, 1f)]
    [SerializeField] private float phaseTransitionHpRatio = 0.5f; // HP 50%
    [Range(0f, 1f)]
    [SerializeField] private float groggyHpRatio = 0.1f;          // HP 10%
    [Tooltip("페이즈 전환 중 무적 + 정지 상태를 유지하는 시간(초).")]
    [SerializeField] private float phaseTransitionDuration = 1.5f;

    [Header("Pattern Interval (문서 5.0 패턴 사이 간격)")]
    [SerializeField] private float patternIntervalPhase1 = 1.2f;
    [SerializeField] private float patternIntervalPhase2 = 0.7f;

    [Header("Patterns")]
    [SerializeField] private List<BossPatternData> phase1Patterns = new();
    [SerializeField] private List<BossPatternData> phase2Patterns = new();

    [Header("Projectile")]
    [SerializeField] private BossProjectile projectilePrefab;
    [SerializeField] private Transform firePoint; // 손끝 등 발사 위치, 비워두면 보스 위치 사용

    [Header("Events (애니메이션 · 이펙트 · 승리 처리 연결용)")]
    public UnityEngine.Events.UnityEvent<string> onPatternTelegraph; // 패턴 이름 전달, 애니메이터 트리거용
    public UnityEngine.Events.UnityEvent onPhaseTransitionStart;
    public UnityEngine.Events.UnityEvent onPhaseTransitionEnd;
    public UnityEngine.Events.UnityEvent onGroggy; // 문서 D15: 그로기 = 즉시 승리 처리 등, 실제 처리는 이 이벤트를 구독해서 구현

    private Rigidbody2D rb;
    private BossPhase currentPhase = BossPhase.Phase1;
    private int currentHealth;
    private bool isTransitioning;
    private bool isGroggy;
    private bool isDead; // 확장 대비(문서 기본안은 그로기 = 즉시 승리라 실제로는 안 쓰일 수 있음)

    private Coroutine patternLoopRoutine;

    private void Awake()
    {
        rb = GetComponent<Rigidbody2D>();
        currentHealth = maxHealth;

        if (player == null)
        {
            GameObject found = GameObject.FindGameObjectWithTag(playerTag);
            if (found != null)
                player = found.transform;
        }

        if (preferredMaxDistance < preferredMinDistance)
            preferredMaxDistance = preferredMinDistance;
    }

    private void Start()
    {
        patternLoopRoutine = StartCoroutine(PatternLoop());
    }

    private void Update()
    {
        if (isDead || isGroggy) return;
        if (player == null) return;

        FaceTowardsPlayer();
    }

    private void FixedUpdate()
    {
        if (isDead || isGroggy || isTransitioning) return;
        if (player == null) return;

        MaintainDistance();
    }

    // -------------------- 이동 --------------------

    private void MaintainDistance()
    {
        float distance = Vector2.Distance(transform.position, player.position);
        float direction = Mathf.Sign(player.position.x - transform.position.x);

        if (distance < preferredMinDistance)
        {
            // 너무 가까우면 물러난다 (반대 방향)
            rb.linearVelocity = new Vector2(-direction * moveSpeed, rb.linearVelocity.y);
        }
        else if (distance > preferredMaxDistance)
        {
            // 너무 멀면 천천히 다가간다
            rb.linearVelocity = new Vector2(direction * moveSpeed, rb.linearVelocity.y);
        }
        else
        {
            // 적정 거리 안이면 정지 (제자리에서 탄막만 사용)
            rb.linearVelocity = new Vector2(0f, rb.linearVelocity.y);
        }
    }

    private void FaceTowardsPlayer()
    {
        if (player == null) return;

        float direction = Mathf.Sign(player.position.x - transform.position.x);
        if (direction == 0f) return;

        Vector3 scale = transform.localScale;
        scale.x = Mathf.Abs(scale.x) * Mathf.Sign(direction);
        transform.localScale = scale;
    }

    // -------------------- 패턴 루프 --------------------

    private IEnumerator PatternLoop()
    {
        while (!isDead)
        {
            // 그로기 · 전환 중이면 대기만 하고 패턴을 실행하지 않음
            if (isGroggy || isTransitioning)
            {
                yield return null;
                continue;
            }

            float interval = currentPhase == BossPhase.Phase1 ? patternIntervalPhase1 : patternIntervalPhase2;
            yield return WaitWhileActive(interval);

            if (isGroggy || isTransitioning || isDead) continue;

            List<BossPatternData> pool = currentPhase == BossPhase.Phase1 ? phase1Patterns : phase2Patterns;
            BossPatternData pattern = ChooseWeightedPattern(pool);
            if (pattern == null)
            {
                yield return null;
                continue;
            }

            yield return ExecutePattern(pattern);
        }
    }

    /// <summary>그로기/전환 상태가 되면 즉시 대기를 끊고 빠져나오는 대기 함수.</summary>
    private IEnumerator WaitWhileActive(float duration)
    {
        float t = 0f;
        while (t < duration)
        {
            if (isGroggy || isTransitioning || isDead)
                yield break;

            t += Time.deltaTime;
            yield return null;
        }
    }

    private BossPatternData ChooseWeightedPattern(List<BossPatternData> pool)
    {
        if (pool == null || pool.Count == 0) return null;

        float totalWeight = 0f;
        foreach (BossPatternData p in pool)
            totalWeight += Mathf.Max(0f, p.weight);

        if (totalWeight <= 0f) return pool[0];

        float roll = Random.Range(0f, totalWeight);
        float cumulative = 0f;

        foreach (BossPatternData p in pool)
        {
            cumulative += Mathf.Max(0f, p.weight);
            if (roll <= cumulative)
                return p;
        }

        return pool[pool.Count - 1];
    }

    private IEnumerator ExecutePattern(BossPatternData pattern)
    {
        // 예고: 애니메이터 · 이펙트(A4)에 이름을 넘겨서 재생하도록 이벤트만 발행
        onPatternTelegraph?.Invoke(pattern.patternName);
        yield return WaitWhileActive(pattern.telegraphTime);

        if (isGroggy || isTransitioning || isDead) yield break;

        // 판정: 타입별 실제 탄막 스폰
        switch (pattern.type)
        {
            case PatternType.HeartBullet:
                yield return FireStraightBullets(pattern);
                break;

            case PatternType.HeartRain:
                yield return FireRainBullets(pattern);
                break;

            case PatternType.MagicRingBurst:
                DealRingBurstDamage(pattern);
                break;
        }

        // 후딜: 안전한 타격 창 (문서 5.0 - 여기서는 그냥 대기)
        yield return WaitWhileActive(pattern.recoveryTime);
    }

    // -------------------- 패턴별 실제 구현 --------------------

    private IEnumerator FireStraightBullets(BossPatternData pattern)
    {
        for (int i = 0; i < pattern.projectileCount; i++)
        {
            if (isGroggy || isTransitioning || isDead) yield break;

            SpawnProjectile(GetFireOrigin(), GetDirectionToPlayer(), pattern);

            if (i < pattern.projectileCount - 1)
                yield return WaitWhileActive(pattern.fireInterval);
        }
    }

    private IEnumerator FireRainBullets(BossPatternData pattern)
    {
        for (int i = 0; i < pattern.projectileCount; i++)
        {
            if (isGroggy || isTransitioning || isDead) yield break;

            // 플레이어 머리 위 근처에서 좌우로 살짝 흩어진 위치에 스폰, 아래 방향으로 낙하
            Vector2 spawnPos = (Vector2)player.position + new Vector2(Random.Range(-1.5f, 1.5f), 4f);
            SpawnProjectile(spawnPos, Vector2.down, pattern);

            yield return WaitWhileActive(pattern.fireInterval);
        }
    }

    private void DealRingBurstDamage(BossPatternData pattern)
    {
        // 투사체 없이 보스 주변 원형 범위를 즉시 판정 (문서의 마력 고리 대응)
        Collider2D[] hits = Physics2D.OverlapCircleAll(transform.position, pattern.ringRadius);

        foreach (Collider2D hit in hits)
        {
            IDamageable target = hit.GetComponentInParent<IDamageable>();
            if (target == null || target == (IDamageable)this) continue;

            Vector2 hitDirection = ((Vector2)hit.transform.position - (Vector2)transform.position).normalized;
            target.TakeDamage(pattern.damage, hit.ClosestPoint(transform.position), hitDirection);
        }
    }

    private void SpawnProjectile(Vector2 position, Vector2 direction, BossPatternData pattern)
    {
        if (projectilePrefab == null) return;

        BossProjectile projectile = Instantiate(projectilePrefab, position, Quaternion.identity);
        projectile.Launch(direction, pattern.projectileSpeed, pattern.damage);
    }

    private Vector2 GetFireOrigin()
    {
        return firePoint != null ? (Vector2)firePoint.position : (Vector2)transform.position;
    }

    private Vector2 GetDirectionToPlayer()
    {
        if (player == null) return Vector2.left;
        return ((Vector2)player.position - GetFireOrigin()).normalized;
    }

    // -------------------- 체력 · 페이즈 · 그로기 --------------------

    public void TakeDamage(int damage, Vector2 hitPoint, Vector2 hitDirection)
    {
        if (isDead || isGroggy || isTransitioning) return; // 전환 중 무적(문서 확정 사항)

        currentHealth -= damage;
        float hpRatio = (float)currentHealth / maxHealth;

        if (hpRatio <= groggyHpRatio)
        {
            EnterGroggy();
            return;
        }

        if (currentPhase == BossPhase.Phase1 && hpRatio <= phaseTransitionHpRatio)
        {
            StartCoroutine(PhaseTransitionRoutine());
        }
    }

    private IEnumerator PhaseTransitionRoutine()
    {
        isTransitioning = true;
        rb.linearVelocity = Vector2.zero;

        onPhaseTransitionStart?.Invoke();

        yield return new WaitForSeconds(phaseTransitionDuration);

        currentPhase = BossPhase.Phase2;
        isTransitioning = false;

        onPhaseTransitionEnd?.Invoke();
    }

    private void EnterGroggy()
    {
        isGroggy = true;
        rb.linearVelocity = Vector2.zero;

        if (patternLoopRoutine != null)
            StopCoroutine(patternLoopRoutine);

        // 문서 D15: 그로기 진입 = 즉시 보스전 종료(승리). 실제 승리 처리는 이 이벤트를 구독해서 구현.
        onGroggy?.Invoke();
    }

    // -------------------- 디버그용 기즈모 --------------------

    private void OnDrawGizmosSelected()
    {
        Gizmos.color = Color.yellow;
        Gizmos.DrawWireSphere(transform.position, preferredMinDistance);

        Gizmos.color = Color.magenta;
        Gizmos.DrawWireSphere(transform.position, preferredMaxDistance);
    }
}

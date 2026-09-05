using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Events;

[RequireComponent(typeof(Rigidbody2D), typeof(Collider2D))]
public sealed class BossAI : MonoBehaviour, IDamageable, IGroggyReceiver,
    IGroggyBuildupReceiver, IOathHealthState, IOathIncapacitable, IOathEntityIdentity
{
    private enum BossPhase
    {
        Phase1 = 1,
        Phase2 = 2
    }

    public enum PatternType
    {
        // 기존 직렬화 값의 호환을 위해 앞의 세 값은 순서를 유지합니다.
        HeartBullet,
        HeartRain,
        MagicRingBurst,
        HeartSlash,
        DoubleSlash,
        DashSlash,
        MagicBerserk
    }

    [System.Serializable]
    public sealed class BossPatternData
    {
        public string patternName = "New Pattern";
        public PatternType type = PatternType.HeartBullet;

        [Header("Timing")]
        [Min(0f)] public float telegraphTime = 0.5f;
        [Min(0f)] public float recoveryTime = 0.5f;
        [Min(0f)] public float fireInterval = 0.15f;

        [Header("Selection / Damage")]
        [Min(0f)] public float weight = 1f;
        [Min(1)] public int damage = 1;
        [Min(1)] public int projectileCount = 1;
        [Min(0f)] public float projectileSpeed = 7f;

        [Header("Melee / Ring")]
        public Vector2 hitboxSize = new(2.2f, 1.4f);
        [Min(0f)] public float hitboxForwardOffset = 1.1f;
        [Min(0.1f)] public float ringRadius = 2.5f;
        [Min(0f)] public float ringRadiusStep = 0.65f;
        [Min(1)] public int burstCount = 3;

        [Header("Dash")]
        [Min(0.1f)] public float dashDistance = 5f;
        [Min(0.05f)] public float dashDuration = 0.3f;
    }

    [Header("Target")]
    [SerializeField] private Transform player;
    [SerializeField] private string playerTag = "Player";

    [Header("Movement")]
    [SerializeField, Min(0f)] private float moveSpeed = 2.2f;
    [SerializeField, Min(0f)] private float phase1StopDistance = 1.4f;
    [Tooltip("2페이즈에서 이 거리보다 가까우면 물러납니다.")]
    [SerializeField, Min(0f)] private float preferredMinDistance = 3f;
    [Tooltip("2페이즈에서 이 거리보다 멀면 접근합니다.")]
    [SerializeField, Min(0f)] private float preferredMaxDistance = 5f;
    [SerializeField, Min(1f)] private float phase2MoveSpeedMultiplier = 1.45f;
    [SerializeField] private bool ignoreBodyCollisionWithPlayer = true;

    [Header("Health / Phase")]
    [SerializeField] private string bossDisplayName = "VARGAL";
    [SerializeField, Min(1)] private int maxHealth = 100;
    [SerializeField, Range(0.01f, 0.99f)] private float phaseTransitionHpRatio = 0.5f;
    [SerializeField, Range(0.01f, 0.99f)] private float groggyHpRatio = 0.1f;
    [SerializeField, Min(0f)] private float phaseTransitionDuration = 1.5f;

    [Header("Hit Stun")]
    [SerializeField, Min(0f)] private float hitStunDuration = 0.2f;
    [SerializeField, Min(1)] private int consecutiveHitStunLimit = 3;
    [SerializeField, Min(0f)] private float hitStunImmunityDuration = 0.75f;
    [SerializeField, Min(0.1f)] private float hitStunChainResetTime = 1f;
    [SerializeField, Min(0.1f)] private float groggyBuildupThreshold = 6f;
    [SerializeField, Min(0.1f)] private float buildupGroggyDuration = 1f;

    [Header("Pattern Interval")]
    [SerializeField, Min(0f)] private float patternIntervalPhase1 = 1.2f;
    [SerializeField, Min(0f)] private float patternIntervalPhase2 = 0.7f;

    [Header("Patterns")]
    [SerializeField] private List<BossPatternData> phase1Patterns = new();
    [SerializeField] private List<BossPatternData> phase2Patterns = new();

    [Header("Projectile / Attack Origin")]
    [SerializeField] private BossProjectile projectilePrefab;
    [SerializeField] private Transform firePoint;

    [Header("Animation / Visuals")]
    [SerializeField] private Animator animator;
    [SerializeField] private SpriteRenderer characterSprite;
    [SerializeField] private bool spriteFacesRightByDefault = true;
    [SerializeField] private EnemyHealthBar2D healthBar;
    [SerializeField] private GameObject telegraphMarker;
    [SerializeField] private Vector3 telegraphMarkerOffset = new(0f, 1.35f, 0f);

    [Header("Events")]
    public UnityEvent<string> onPatternTelegraph;
    public UnityEvent<string> onPatternImpact;
    public UnityEvent onHit;
    public UnityEvent onTemporaryGroggy;
    public UnityEvent onPhaseTransitionStart;
    public UnityEvent onPhaseTransitionEnd;
    public UnityEvent onGroggy;

    public int CurrentHealth { get; private set; }
    public int MaxHealth => maxHealth;
    public string BossDisplayName => string.IsNullOrWhiteSpace(bossDisplayName)
        ? gameObject.name
        : bossDisplayName;
    public bool IsDead => isDefeated;
    public bool IsIncapacitated => isDefeated;
    public bool IsGroggy => isDefeated || isStaggered;
    public bool IsDefeated => isDefeated;
    public int CurrentPhase => (int)currentPhase;
    public int OathEntityId => gameObject.GetInstanceID();

    private readonly HashSet<int> animatorFloatParameters = new();
    private readonly HashSet<int> animatorBoolParameters = new();
    private readonly HashSet<int> animatorIntParameters = new();
    private readonly HashSet<int> animatorTriggerParameters = new();

    private Rigidbody2D body;
    private Collider2D bodyCollider;
    private PlayerController2D playerController;
    private StageManager stageManager;
    private TextMesh telegraphText;
    private BossPhase currentPhase = BossPhase.Phase1;
    private BossPatternData currentPattern;
    private Coroutine patternLoopRoutine;
    private Coroutine stateRoutine;
    private float nextPlayerSearchTime;
    private float nextHitStunAllowedTime;
    private float lastHitStunTime = float.NegativeInfinity;
    private float groggyBuildup;
    private int consecutiveHitStuns;
    private int facingSign = 1;
    private bool hasStarted;
    private bool isTransitioning;
    private bool isStaggered;
    private bool isDefeated;
    private bool forceBerserkNext;
    private bool ignoreParryStagger;

    private static readonly int SpeedHash = Animator.StringToHash("Speed");
    private static readonly int MovingHash = Animator.StringToHash("IsMoving");
    private static readonly int PhaseHash = Animator.StringToHash("Phase");
    private static readonly int HitHash = Animator.StringToHash("Hit");
    private static readonly int GroggyHash = Animator.StringToHash("Groggy");
    private static readonly int PhaseTransitionHash = Animator.StringToHash("PhaseTransition");
    private static readonly int AttackHash = Animator.StringToHash("Attack");

    private bool IsActionBlocked => isDefeated || isTransitioning || isStaggered;

    private void Awake()
    {
        body = GetComponent<Rigidbody2D>();
        bodyCollider = GetComponent<Collider2D>();
        body.freezeRotation = true;
        CurrentHealth = Mathf.Max(1, maxHealth);

        preferredMaxDistance = Mathf.Max(preferredMinDistance, preferredMaxDistance);
        groggyHpRatio = Mathf.Min(groggyHpRatio, phaseTransitionHpRatio);

        if (animator == null)
            animator = GetComponentInChildren<Animator>(true);
        if (characterSprite == null)
            characterSprite = animator != null
                ? animator.GetComponentInChildren<SpriteRenderer>(true)
                : GetComponentInChildren<SpriteRenderer>(true);
        CacheAnimatorParameters();

        if (healthBar == null)
            healthBar = GetComponent<EnemyHealthBar2D>();
        if (healthBar == null)
            healthBar = gameObject.AddComponent<EnemyHealthBar2D>();
        healthBar.Initialize(CurrentHealth, maxHealth);

        BossHealthHUD.GetOrCreate().Bind(this);

        SetupTelegraphMarker();
        EnsureDefaultPatterns();
        TryFindPlayer();
    }

    private void Start()
    {
        hasStarted = true;
        RestartPatternLoop();
    }

    private void OnDisable()
    {
        BossHealthHUD.Unbind(this);
        StopAllCoroutines();
        patternLoopRoutine = null;
        stateRoutine = null;
        StopHorizontalMovement();
    }

    private void Update()
    {
        if (player == null && Time.time >= nextPlayerSearchTime)
            TryFindPlayer();

        if (!isDefeated && player != null)
            FaceTowardsPlayer();

        UpdateAnimator();
    }

    private void FixedUpdate()
    {
        if (IsActionBlocked || player == null)
        {
            StopHorizontalMovement();
            return;
        }

        // 패턴의 예고·판정·후딜 중에는 기본 추적 이동이 패턴 이동을 덮어쓰지 않는다.
        // 돌진 참격은 코루틴이 직접 속도를 제어하므로 여기서도 아무것도 하지 않는다.
        if (currentPattern != null)
        {
            if (currentPattern.type != PatternType.DashSlash)
                StopHorizontalMovement();
            return;
        }

        MaintainDistance();
    }

    private void LateUpdate()
    {
        ApplyFacingVisual();
    }

    public void Initialize(StageManager manager, Transform playerTarget)
    {
        stageManager = manager;
        if (playerTarget != null)
            SetPlayer(playerTarget);

        if (hasStarted)
            RestartPatternLoop();
    }

    private void MaintainDistance()
    {
        float horizontalDistance = Mathf.Abs(player.position.x - transform.position.x);
        float direction = Mathf.Sign(player.position.x - transform.position.x);
        if (Mathf.Approximately(direction, 0f))
        {
            StopHorizontalMovement();
            return;
        }

        if (currentPhase == BossPhase.Phase1)
        {
            float velocity = horizontalDistance > phase1StopDistance ? direction * moveSpeed : 0f;
            body.linearVelocity = new Vector2(velocity, body.linearVelocity.y);
            return;
        }

        float phase2Speed = moveSpeed * phase2MoveSpeedMultiplier;
        if (horizontalDistance < preferredMinDistance)
            body.linearVelocity = new Vector2(-direction * phase2Speed, body.linearVelocity.y);
        else if (horizontalDistance > preferredMaxDistance)
            body.linearVelocity = new Vector2(direction * phase2Speed, body.linearVelocity.y);
        else
            StopHorizontalMovement();
    }

    private IEnumerator PatternLoop()
    {
        while (!isDefeated)
        {
            if (IsActionBlocked || player == null)
            {
                yield return null;
                continue;
            }

            float interval = currentPhase == BossPhase.Phase1
                ? patternIntervalPhase1
                : patternIntervalPhase2;
            yield return WaitWhileActive(interval);
            if (IsActionBlocked || player == null)
                continue;

            BossPatternData pattern = ChoosePatternForCurrentSituation();
            if (pattern == null)
            {
                yield return null;
                continue;
            }

            yield return ExecutePattern(pattern);
        }
    }

    private IEnumerator ExecutePattern(BossPatternData pattern)
    {
        currentPattern = pattern;
        StopHorizontalMovement();
        FaceTowardsPlayer();
        SetMarker("♥", true);
        SetAnimatorTrigger(AttackHash);
        SetAnimatorTrigger(Animator.StringToHash(GetPatternTriggerName(pattern.type)));
        onPatternTelegraph?.Invoke(pattern.patternName);

        yield return WaitWhileActive(pattern.telegraphTime);
        if (IsActionBlocked)
            yield break;

        SetMarker("♥", false);
        onPatternImpact?.Invoke(pattern.patternName);

        switch (pattern.type)
        {
            case PatternType.HeartSlash:
                DealFrontDamage(pattern);
                break;
            case PatternType.DoubleSlash:
                yield return ExecuteDoubleSlash(pattern);
                break;
            case PatternType.HeartBullet:
                yield return FireStraightBullets(pattern);
                break;
            case PatternType.HeartRain:
                yield return FireRainBullets(pattern);
                break;
            case PatternType.MagicRingBurst:
                DealRingDamage(pattern.ringRadius, pattern.damage);
                break;
            case PatternType.DashSlash:
                yield return ExecuteDashSlash(pattern);
                break;
            case PatternType.MagicBerserk:
                yield return ExecuteMagicBerserk(pattern);
                break;
        }

        if (IsActionBlocked)
            yield break;

        yield return WaitWhileActive(pattern.recoveryTime);
        currentPattern = null;
    }

    private IEnumerator ExecuteDoubleSlash(BossPatternData pattern)
    {
        DealFrontDamage(pattern);
        if (IsActionBlocked)
            yield break;

        yield return WaitWhileActive(Mathf.Max(0.05f, pattern.fireInterval));
        if (IsActionBlocked)
            yield break;

        FaceTowardsPlayer();
        DealFrontDamage(pattern);
    }

    private IEnumerator FireStraightBullets(BossPatternData pattern)
    {
        int count = Mathf.Max(1, pattern.projectileCount);
        for (int i = 0; i < count; i++)
        {
            if (IsActionBlocked)
                yield break;

            SpawnProjectile(GetFireOrigin(), GetDirectionToPlayer(), pattern);
            if (i < count - 1)
                yield return WaitWhileActive(pattern.fireInterval);
        }
    }

    private IEnumerator FireRainBullets(BossPatternData pattern)
    {
        int count = Mathf.Max(1, pattern.projectileCount);
        for (int i = 0; i < count; i++)
        {
            if (IsActionBlocked || player == null)
                yield break;

            Vector2 spawnPosition = (Vector2)player.position +
                                    new Vector2(Random.Range(-1.5f, 1.5f), 4f);
            SpawnProjectile(spawnPosition, Vector2.down, pattern);
            if (i < count - 1)
                yield return WaitWhileActive(pattern.fireInterval);
        }
    }

    private IEnumerator ExecuteDashSlash(BossPatternData pattern)
    {
        if (player == null)
            yield break;

        float direction = Mathf.Sign(player.position.x - transform.position.x);
        if (Mathf.Approximately(direction, 0f))
            direction = facingSign;
        facingSign = direction > 0f ? 1 : -1;

        float duration = Mathf.Max(0.05f, pattern.dashDuration);
        float neededDistance = Mathf.Abs(player.position.x - transform.position.x) + 1f;
        float dashDistance = Mathf.Max(pattern.dashDistance, neededDistance);
        float speed = dashDistance / duration;
        float elapsed = 0f;
        bool hasDealtDamage = false;

        while (elapsed < duration && !IsActionBlocked)
        {
            body.linearVelocity = new Vector2(direction * speed, body.linearVelocity.y);
            if (!hasDealtDamage)
                hasDealtDamage = DealFrontDamage(pattern).HasValue;

            elapsed += Time.fixedDeltaTime;
            yield return new WaitForFixedUpdate();
        }

        StopHorizontalMovement();
    }

    private IEnumerator ExecuteMagicBerserk(BossPatternData pattern)
    {
        ignoreParryStagger = true;
        int burstCount = Mathf.Max(1, pattern.burstCount);

        for (int i = 0; i < burstCount; i++)
        {
            if (isDefeated || isTransitioning || isStaggered)
                yield break;

            float radius = pattern.ringRadius + pattern.ringRadiusStep * i;
            DealRingDamage(radius, pattern.damage);
            if (i < burstCount - 1)
                yield return WaitWhileActive(pattern.fireInterval);
        }

        if (!IsActionBlocked)
        {
            SetMarker("♥", true);
            yield return WaitWhileActive(Mathf.Max(0.15f, pattern.fireInterval * 2f));
            SetMarker("♥", false);
            if (!IsActionBlocked)
            {
                float finalRadius = pattern.ringRadius + pattern.ringRadiusStep * burstCount;
                DealRingDamage(finalRadius, Mathf.Max(1, pattern.damage * 2));
            }
        }

        ignoreParryStagger = false;
    }

    private PlayerHitResult? DealFrontDamage(BossPatternData pattern)
    {
        Vector2 center = (Vector2)transform.position +
                         Vector2.right * (pattern.hitboxForwardOffset * facingSign);
        Collider2D[] hits = Physics2D.OverlapBoxAll(center, pattern.hitboxSize, 0f);
        return DamagePlayerFromHits(hits, center, pattern.damage);
    }

    private PlayerHitResult? DealRingDamage(float radius, int damage)
    {
        Collider2D[] hits = Physics2D.OverlapCircleAll(transform.position, radius);
        return DamagePlayerFromHits(hits, transform.position, damage);
    }

    private PlayerHitResult? DamagePlayerFromHits(Collider2D[] hits, Vector2 hitOrigin, int damage)
    {
        foreach (Collider2D hit in hits)
        {
            PlayerController2D target = hit.GetComponentInParent<PlayerController2D>();
            if (target == null || target != playerController)
                continue;

            return target.ReceiveEnemyAttack(
                Mathf.Max(1, damage), gameObject, hit.ClosestPoint(hitOrigin));
        }

        return null;
    }

    private void SpawnProjectile(Vector2 position, Vector2 direction, BossPatternData pattern)
    {
        BossProjectile projectile = projectilePrefab != null
            ? Instantiate(projectilePrefab, position, Quaternion.identity)
            : BossProjectile.CreateRuntime(position);
        projectile.Launch(direction, pattern.projectileSpeed, pattern.damage, gameObject);
    }

    public void TakeDamage(int damage, Vector2 hitPoint, Vector2 hitDirection)
    {
        if (damage <= 0 || isDefeated || isTransitioning)
            return;

        CurrentHealth = Mathf.Max(0, CurrentHealth - damage);
        healthBar.SetHealth(CurrentHealth, maxHealth);
        SetAnimatorTrigger(HitHash);
        onHit?.Invoke();

        float healthRatio = maxHealth > 0 ? (float)CurrentHealth / maxHealth : 0f;
        if (healthRatio <= groggyHpRatio)
        {
            EnterFinalGroggy("HP 10% 이하");
            return;
        }

        if (currentPhase == BossPhase.Phase1 && healthRatio <= phaseTransitionHpRatio)
        {
            BeginPhaseTransition();
            return;
        }

        ApplyDamageHitStun();
    }

    // 패링으로 들어오는 그로기는 일시 경직입니다. 최종 승리는 HP 10% 또는 R-08만 처리합니다.
    public void EnterGroggy(float duration, GameObject source)
    {
        if (isDefeated || isTransitioning || ignoreParryStagger)
            return;

        onTemporaryGroggy?.Invoke();
        BeginTemporaryStagger(Mathf.Max(0.1f, duration), true);
    }

    public void AddGroggyBuildup(float amount, GameObject source)
    {
        if (amount <= 0f || isDefeated || isTransitioning)
            return;

        groggyBuildup += amount;
        if (groggyBuildup < groggyBuildupThreshold)
            return;

        groggyBuildup = 0f;
        onTemporaryGroggy?.Invoke();
        BeginTemporaryStagger(buildupGroggyDuration, true);
    }

    public void ForceFinalGroggy(GameObject source)
    {
        string reason = source != null ? $"폭발적 무력화: {source.name}" : "폭발적 무력화";
        EnterFinalGroggy(reason);
    }

    public void Incapacitate()
    {
        EnterFinalGroggy("맹세 무력화");
    }

    private void ApplyDamageHitStun()
    {
        if (Time.time < nextHitStunAllowedTime)
            return;

        if (Time.time - lastHitStunTime > hitStunChainResetTime)
            consecutiveHitStuns = 0;

        lastHitStunTime = Time.time;
        consecutiveHitStuns++;
        if (consecutiveHitStuns >= Mathf.Max(1, consecutiveHitStunLimit))
        {
            consecutiveHitStuns = 0;
            nextHitStunAllowedTime = Time.time + hitStunDuration + hitStunImmunityDuration;
        }

        BeginTemporaryStagger(hitStunDuration, false);
    }

    private void BeginTemporaryStagger(float duration, bool showGroggyMarker)
    {
        StopPatternLoop();
        if (stateRoutine != null)
            StopCoroutine(stateRoutine);

        isStaggered = true;
        StopHorizontalMovement();
        SetAnimatorBool(GroggyHash, showGroggyMarker);
        SetMarker(showGroggyMarker ? "★" : string.Empty, showGroggyMarker);
        stateRoutine = StartCoroutine(TemporaryStaggerRoutine(duration));
    }

    private IEnumerator TemporaryStaggerRoutine(float duration)
    {
        yield return new WaitForSeconds(Mathf.Max(0f, duration));
        isStaggered = false;
        stateRoutine = null;
        SetAnimatorBool(GroggyHash, false);
        SetMarker(string.Empty, false);
        RestartPatternLoop();
    }

    private void BeginPhaseTransition()
    {
        StopPatternLoop();
        if (stateRoutine != null)
            StopCoroutine(stateRoutine);
        stateRoutine = StartCoroutine(PhaseTransitionRoutine());
    }

    private IEnumerator PhaseTransitionRoutine()
    {
        isStaggered = false;
        isTransitioning = true;
        StopHorizontalMovement();
        SetAnimatorBool(GroggyHash, false);
        SetAnimatorTrigger(PhaseTransitionHash);
        SetMarker("♥", true);
        onPhaseTransitionStart?.Invoke();

        yield return new WaitForSeconds(Mathf.Max(0f, phaseTransitionDuration));

        currentPhase = BossPhase.Phase2;
        isTransitioning = false;
        forceBerserkNext = true;
        stateRoutine = null;
        SetMarker(string.Empty, false);
        SetAnimatorInt(PhaseHash, 2);
        onPhaseTransitionEnd?.Invoke();
        RestartPatternLoop();
    }

    private void EnterFinalGroggy(string reason)
    {
        if (isDefeated)
            return;

        isDefeated = true;
        isTransitioning = false;
        isStaggered = false;
        StopAllCoroutines();
        patternLoopRoutine = null;
        stateRoutine = null;
        currentPattern = null;
        StopHorizontalMovement();
        BossProjectile.DestroyOwnedProjectiles(gameObject);

        body.simulated = false;
        bodyCollider.enabled = false;
        SetAnimatorBool(GroggyHash, true);
        SetMarker("★", true);
        healthBar.SetHealth(CurrentHealth, maxHealth);
        onGroggy?.Invoke();

        Debug.Log($"[Boss] 바르갈 최종 그로기 — {reason}", this);
        if (stageManager == null)
            stageManager = FindFirstObjectByType<StageManager>();
        if (stageManager != null)
            stageManager.NotifyBossDefeated(this);
    }

    private BossPatternData ChoosePatternForCurrentSituation()
    {
        List<BossPatternData> pool = currentPhase == BossPhase.Phase1
            ? phase1Patterns
            : phase2Patterns;
        if (pool == null || pool.Count == 0)
            return null;

        if (forceBerserkNext)
        {
            forceBerserkNext = false;
            BossPatternData berserk = pool.Find(pattern =>
                pattern != null && pattern.type == PatternType.MagicBerserk);
            if (berserk != null)
                return berserk;
        }

        float distance = player != null
            ? Mathf.Abs(player.position.x - transform.position.x)
            : 0f;
        bool wantsRanged = currentPhase == BossPhase.Phase1
            ? distance > preferredMinDistance
            : distance > preferredMaxDistance;

        List<BossPatternData> candidates = new();
        foreach (BossPatternData pattern in pool)
        {
            if (pattern == null)
                continue;

            bool isRanged = pattern.type == PatternType.HeartBullet ||
                            pattern.type == PatternType.HeartRain ||
                            pattern.type == PatternType.DashSlash;
            if (isRanged == wantsRanged)
                candidates.Add(pattern);
        }

        return ChooseWeighted(candidates.Count > 0 ? candidates : pool);
    }

    private static BossPatternData ChooseWeighted(List<BossPatternData> pool)
    {
        float totalWeight = 0f;
        foreach (BossPatternData pattern in pool)
        {
            if (pattern != null)
                totalWeight += Mathf.Max(0f, pattern.weight);
        }

        if (totalWeight <= 0f)
            return pool.Find(pattern => pattern != null);

        float roll = Random.Range(0f, totalWeight);
        float cumulative = 0f;
        foreach (BossPatternData pattern in pool)
        {
            if (pattern == null)
                continue;
            cumulative += Mathf.Max(0f, pattern.weight);
            if (roll <= cumulative)
                return pattern;
        }

        return pool[pool.Count - 1];
    }

    private IEnumerator WaitWhileActive(float duration)
    {
        float elapsed = 0f;
        while (elapsed < duration)
        {
            if (IsActionBlocked)
                yield break;
            elapsed += Time.deltaTime;
            yield return null;
        }
    }

    private void StopPatternLoop()
    {
        if (patternLoopRoutine != null)
        {
            StopCoroutine(patternLoopRoutine);
            patternLoopRoutine = null;
        }

        currentPattern = null;
        ignoreParryStagger = false;
        SetMarker(string.Empty, false);
        StopHorizontalMovement();
    }

    private void RestartPatternLoop()
    {
        if (!hasStarted || IsActionBlocked || patternLoopRoutine != null)
            return;
        patternLoopRoutine = StartCoroutine(PatternLoop());
    }

    private void TryFindPlayer()
    {
        nextPlayerSearchTime = Time.time + 0.5f;
        GameObject found = GameObject.FindGameObjectWithTag(playerTag);
        if (found != null)
            SetPlayer(found.transform);
    }

    private void SetPlayer(Transform target)
    {
        player = target;
        playerController = player != null ? player.GetComponentInParent<PlayerController2D>() : null;
        if (playerController == null && player != null)
            playerController = player.GetComponentInChildren<PlayerController2D>(true);

        if (!ignoreBodyCollisionWithPlayer || playerController == null)
            return;

        foreach (Collider2D playerCollider in playerController.GetComponentsInChildren<Collider2D>(true))
        {
            if (playerCollider != null && !playerCollider.isTrigger)
                Physics2D.IgnoreCollision(bodyCollider, playerCollider, true);
        }
    }

    private void FaceTowardsPlayer()
    {
        if (player == null)
            return;

        float direction = Mathf.Sign(player.position.x - transform.position.x);
        if (!Mathf.Approximately(direction, 0f))
            facingSign = direction > 0f ? 1 : -1;
    }

    private void ApplyFacingVisual()
    {
        if (characterSprite == null)
            return;
        characterSprite.flipX = spriteFacesRightByDefault
            ? facingSign < 0
            : facingSign > 0;
    }

    private void StopHorizontalMovement()
    {
        if (body != null && body.simulated)
            body.linearVelocity = new Vector2(0f, body.linearVelocity.y);
    }

    private Vector2 GetFireOrigin()
    {
        if (firePoint == null)
            return transform.position;

        Vector2 localOffset = firePoint.position - transform.position;
        localOffset.x = Mathf.Abs(localOffset.x) * facingSign;
        return (Vector2)transform.position + localOffset;
    }

    private Vector2 GetDirectionToPlayer()
    {
        if (player == null)
            return Vector2.right * facingSign;
        Vector2 direction = (Vector2)player.position - GetFireOrigin();
        return direction.sqrMagnitude > 0.001f
            ? direction.normalized
            : Vector2.right * facingSign;
    }

    private void SetupTelegraphMarker()
    {
        if (telegraphMarker == null)
        {
            telegraphMarker = new GameObject("BossTelegraphMarker");
            telegraphMarker.transform.SetParent(transform, false);
            telegraphText = telegraphMarker.AddComponent<TextMesh>();
            telegraphText.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            telegraphText.fontSize = 64;
            telegraphText.characterSize = 0.1f;
            telegraphText.anchor = TextAnchor.MiddleCenter;
            telegraphText.alignment = TextAlignment.Center;
            telegraphText.color = new Color(1f, 0.35f, 0.75f, 1f);
            telegraphText.GetComponent<MeshRenderer>().sortingOrder = 120;
        }
        else
        {
            telegraphText = telegraphMarker.GetComponentInChildren<TextMesh>(true);
        }

        telegraphMarker.transform.localPosition = telegraphMarkerOffset;
        SetMarker(string.Empty, false);
    }

    private void SetMarker(string symbol, bool visible)
    {
        if (telegraphText != null)
            telegraphText.text = symbol;
        if (telegraphMarker != null)
            telegraphMarker.SetActive(visible);
    }

    private void EnsureDefaultPatterns()
    {
        if (phase1Patterns.Count == 0)
        {
            phase1Patterns.Add(new BossPatternData
            {
                patternName = "하트 참격",
                type = PatternType.HeartSlash,
                telegraphTime = 0.45f,
                recoveryTime = 0.55f,
                damage = 1,
                weight = 3f
            });
            phase1Patterns.Add(new BossPatternData
            {
                patternName = "이단 참격",
                type = PatternType.DoubleSlash,
                telegraphTime = 0.55f,
                recoveryTime = 0.65f,
                fireInterval = 0.13f,
                damage = 1,
                weight = 1.5f
            });
            phase1Patterns.Add(new BossPatternData
            {
                patternName = "하트 탄",
                type = PatternType.HeartBullet,
                telegraphTime = 0.55f,
                recoveryTime = 0.5f,
                projectileSpeed = 8f,
                damage = 1,
                weight = 2f
            });
        }

        if (phase2Patterns.Count == 0)
        {
            phase2Patterns.Add(new BossPatternData
            {
                patternName = "마력 고리",
                type = PatternType.MagicRingBurst,
                telegraphTime = 0.4f,
                recoveryTime = 0.4f,
                ringRadius = 2.5f,
                damage = 1,
                weight = 3f
            });
            phase2Patterns.Add(new BossPatternData
            {
                patternName = "돌진 참격",
                type = PatternType.DashSlash,
                telegraphTime = 0.45f,
                recoveryTime = 0.45f,
                dashDistance = 5f,
                dashDuration = 0.3f,
                damage = 1,
                weight = 2.5f
            });
            phase2Patterns.Add(new BossPatternData
            {
                patternName = "마력 폭주",
                type = PatternType.MagicBerserk,
                telegraphTime = 0.7f,
                recoveryTime = 0.9f,
                fireInterval = 0.28f,
                ringRadius = 1.8f,
                ringRadiusStep = 0.7f,
                burstCount = 3,
                damage = 1,
                weight = 1f
            });
            phase2Patterns.Add(new BossPatternData
            {
                patternName = "하트 탄",
                type = PatternType.HeartBullet,
                telegraphTime = 0.4f,
                recoveryTime = 0.35f,
                projectileSpeed = 9f,
                damage = 1,
                weight = 1f
            });
        }
    }

    private static string GetPatternTriggerName(PatternType type)
    {
        return type switch
        {
            PatternType.MagicRingBurst => "MagicRing",
            _ => type.ToString()
        };
    }

    private void UpdateAnimator()
    {
        if (animator == null)
            return;

        float speed = body != null && body.simulated ? Mathf.Abs(body.linearVelocity.x) : 0f;
        SetAnimatorFloat(SpeedHash, speed);
        SetAnimatorBool(MovingHash, speed > 0.05f && !IsActionBlocked);
        SetAnimatorInt(PhaseHash, (int)currentPhase);
    }

    private void CacheAnimatorParameters()
    {
        animatorFloatParameters.Clear();
        animatorBoolParameters.Clear();
        animatorIntParameters.Clear();
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
                case AnimatorControllerParameterType.Int:
                    animatorIntParameters.Add(parameter.nameHash);
                    break;
                case AnimatorControllerParameterType.Trigger:
                    animatorTriggerParameters.Add(parameter.nameHash);
                    break;
            }
        }
    }

    private void SetAnimatorFloat(int parameter, float value)
    {
        if (animator != null && animatorFloatParameters.Contains(parameter))
            animator.SetFloat(parameter, value);
    }

    private void SetAnimatorBool(int parameter, bool value)
    {
        if (animator != null && animatorBoolParameters.Contains(parameter))
            animator.SetBool(parameter, value);
    }

    private void SetAnimatorInt(int parameter, int value)
    {
        if (animator != null && animatorIntParameters.Contains(parameter))
            animator.SetInteger(parameter, value);
    }

    private void SetAnimatorTrigger(int parameter)
    {
        if (animator != null && animatorTriggerParameters.Contains(parameter))
            animator.SetTrigger(parameter);
    }

    private void OnDrawGizmosSelected()
    {
        Gizmos.color = Color.cyan;
        Gizmos.DrawWireSphere(transform.position, phase1StopDistance);
        Gizmos.color = Color.yellow;
        Gizmos.DrawWireSphere(transform.position, preferredMinDistance);
        Gizmos.color = Color.magenta;
        Gizmos.DrawWireSphere(transform.position, preferredMaxDistance);

        if (currentPattern == null)
            return;
        Gizmos.color = Color.red;
        if (currentPattern.type == PatternType.MagicRingBurst ||
            currentPattern.type == PatternType.MagicBerserk)
        {
            Gizmos.DrawWireSphere(transform.position, currentPattern.ringRadius);
        }
        else
        {
            Vector3 center = transform.position +
                             Vector3.right * (currentPattern.hitboxForwardOffset * facingSign);
            Gizmos.DrawWireCube(center, currentPattern.hitboxSize);
        }
    }
}

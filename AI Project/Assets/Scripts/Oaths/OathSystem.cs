using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Events;

public sealed class OathSystem : MonoBehaviour
{
    [Serializable]
    public sealed class OathDefinition
    {
        public OathType type;
        public string displayName;
        [TextArea(3, 8)] public string ruleDescription;
        public Sprite icon;
    }

    public static OathSystem Instance { get; private set; }

    [Header("Available Oaths")]
    [SerializeField] private List<OathDefinition> availableOaths = new();
    [SerializeField] private bool chooseRandomOathOnStart = true;

    [Header("UI / Events")]
    [SerializeField] private OathHUD oathHUD;
    [SerializeField] private UnityEvent onOathViolated;

    [Header("Enforcement")]
    [Tooltip("끄면 맹세를 표시만 하고 규칙은 적용하지 않습니다. 튜토리얼 구간에서 사용합니다.")]
    [SerializeField] private bool enforcementEnabled = true;

    public bool EnforcementEnabled
    {
        get => enforcementEnabled;
        set => enforcementEnabled = value;
    }

    public OathDefinition ActiveOath { get; private set; }
    public bool IsViolated { get; private set; }

    private readonly HashSet<int> enemiesThatAttackedPlayer = new();

    private void Awake()
    {
        if (Instance != null && Instance != this)
        {
            Destroy(gameObject);
            return;
        }

        Instance = this;
        EnsureDefaultOaths();
    }

    private void Start()
    {
        if (chooseRandomOathOnStart)
            GrantRandomOath();
    }

    private void OnDestroy()
    {
        if (Instance == this)
            Instance = null;
    }

    public void GrantRandomOath()
    {
        if (availableOaths.Count == 0)
        {
            Debug.LogError("[맹세] 부여할 맹세가 없습니다.", this);
            return;
        }

        OathDefinition definition = availableOaths[UnityEngine.Random.Range(0, availableOaths.Count)];
        if (definition == null)
        {
            Debug.LogError("[맹세] 선택된 맹세 정의가 비어 있습니다.", this);
            return;
        }

        GrantOath(definition);
    }

    public void GrantOath(OathType type)
    {
        OathDefinition definition = availableOaths.Find(oath => oath != null && oath.type == type);
        if (definition == null)
        {
            Debug.LogError($"[맹세] {type} 정의를 찾을 수 없습니다.", this);
            return;
        }

        GrantOath(definition);
    }

    public void RegisterEnemyAttack(GameObject attacker)
    {
        if (attacker == null)
            return;

        enemiesThatAttackedPlayer.Add(ResolveEntityId(attacker));
        Debug.Log($"[맹세] '{attacker.name}'의 선제공격 자격이 기록되었습니다.", attacker);
    }

    // PlayerAttackHitbox가 피해를 적용하기 전에 호출합니다.
    public bool TryPreparePlayerMeleeHit(GameObject target, int requestedDamage, out int allowedDamage)
    {
        allowedDamage = Mathf.Max(0, requestedDamage);
        if (!enforcementEnabled)
            return true;
        if (ActiveOath == null || IsViolated || target == null)
            return !IsViolated;

        if (ActiveOath.type == OathType.RetaliationOnly &&
            !enemiesThatAttackedPlayer.Contains(ResolveEntityId(target)))
        {
            ViolateOath($"선제 공격: 아직 플레이어를 공격하지 않은 '{target.name}'을 공격했습니다.");
            allowedDamage = 0;
            return false;
        }

        if (ActiveOath.type == OathType.CannotKill)
        {
            IOathHealthState health = FindInterface<IOathHealthState>(target);
            if (health == null)
            {
                Debug.LogWarning(
                    $"[맹세] '{target.name}'에 IOathHealthState가 없어 피해를 HP 1로 제한할 수 없습니다.", target);
                return true;
            }

            allowedDamage = Mathf.Clamp(allowedDamage, 0, Mathf.Max(0, health.CurrentHealth - 1));
        }

        return true;
    }

    // 실제 피해가 적용된 직후 호출합니다.
    public void CompletePlayerMeleeHit(GameObject target)
    {
        if (!enforcementEnabled)
            return;
        if (ActiveOath == null || ActiveOath.type != OathType.CannotKill || target == null)
            return;

        IOathHealthState health = FindInterface<IOathHealthState>(target);
        IOathIncapacitable incapacitable = FindInterface<IOathIncapacitable>(target);

        if (health != null && !health.IsDead && health.CurrentHealth <= 1 &&
            incapacitable != null && !incapacitable.IsIncapacitated)
        {
            incapacitable.Incapacitate();
            Debug.Log($"[맹세] '{target.name}' 무력화", target);
        }
    }

    // 모든 사망 원인에서 엔티티 사망 시스템이 반드시 호출해야 합니다.
    public void NotifyEnemyDied(GameObject enemy, EnemyDeathCause cause)
    {
        if (!enforcementEnabled)
            return;
        if (ActiveOath != null && ActiveOath.type == OathType.CannotKill)
            ViolateOath($"적 사망 발생: '{(enemy != null ? enemy.name : "Unknown")}', 원인: {cause}");
    }

    // 스테이지 시스템이 전멸 대신 무력화 여부를 확인할 때 사용합니다.
    public bool IsEnemyCleared(GameObject enemy)
    {
        if (enemy == null)
            return true;

        if (enforcementEnabled && ActiveOath != null && ActiveOath.type == OathType.CannotKill)
        {
            IOathIncapacitable incapacitable = FindInterface<IOathIncapacitable>(enemy);
            return incapacitable != null && incapacitable.IsIncapacitated;
        }

        IOathHealthState health = FindInterface<IOathHealthState>(enemy);
        return health != null && health.IsDead;
    }

    public void ViolateOath(string reason)
    {
        if (IsViolated)
            return;

        IsViolated = true;

        if (SkillEffects.Instance != null)
        {
            PlayerController2D player = FindFirstObjectByType<PlayerController2D>();
            if (player != null)
                SkillEffects.Instance.PlayOathBreak(player.transform, player.FacingSign);
        }

        Debug.LogError($"[맹세 위반] {ActiveOath?.displayName ?? "알 수 없는 맹세"} - {reason}", this);
        onOathViolated?.Invoke();
    }

    private void GrantOath(OathDefinition definition)
    {
        ActiveOath = definition;
        IsViolated = false;
        enemiesThatAttackedPlayer.Clear();
        if (oathHUD != null)
            oathHUD.Show(definition);
        Debug.Log($"[맹세 획득] {definition.displayName}\n{definition.ruleDescription}", this);
    }

    private void EnsureDefaultOaths()
    {
        if (availableOaths.Count > 0)
            return;

        availableOaths.Add(new OathDefinition
        {
            type = OathType.CannotKill,
            displayName = "나는 죽이지 못한다",
            ruleDescription = "검으로도, 지형으로도, 다른 적을 시켜서도 죽일 수 없다. 예외 조항은 없다. 상대가 마족이어도 마찬가지다."
        });
        availableOaths.Add(new OathDefinition
        {
            type = OathType.RetaliationOnly,
            displayName = "나는 나를 친 자만 친다",
            ruleDescription = "적이 나에게 공격을 시도한 뒤에야 그 적을 벨 수 있다. 적마다 개별로 판정한다."
        });
    }

    private static int ResolveEntityId(GameObject source)
    {
        IOathEntityIdentity identity = FindInterface<IOathEntityIdentity>(source);
        if (identity != null)
            return identity.OathEntityId;

        Rigidbody2D rootBody = source.GetComponentInParent<Rigidbody2D>();
        return rootBody != null ? rootBody.gameObject.GetInstanceID() : source.transform.root.gameObject.GetInstanceID();
    }

    private static T FindInterface<T>(GameObject source) where T : class
    {
        if (source == null)
            return null;

        MonoBehaviour[] behaviours = source.GetComponentsInParent<MonoBehaviour>(true);
        foreach (MonoBehaviour behaviour in behaviours)
        {
            if (behaviour is T result)
                return result;
        }

        return null;
    }
}

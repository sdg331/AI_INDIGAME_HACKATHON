using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.InputSystem;

public sealed class RelicSkillController : MonoBehaviour
{
    private readonly struct GroggyTarget
    {
        public readonly Transform Transform;
        private readonly MeleeEnemyAI enemy;
        private readonly BossAI boss;

        public GroggyTarget(MeleeEnemyAI target)
        {
            enemy = target;
            boss = null;
            Transform = target.transform;
        }

        public GroggyTarget(BossAI target)
        {
            enemy = null;
            boss = target;
            Transform = target.transform;
        }

        public void Apply(float duration, GameObject source)
        {
            if (boss != null)
                boss.ForceFinalGroggy(source);
            else if (enemy != null)
                enemy.EnterGroggy(duration, source);
        }
    }

    [Header("Pushback")]
    [SerializeField, Min(0f)] private float pushbackRadius = 4f;
    [SerializeField, Min(0f)] private float pushbackForce = 10f;
    [SerializeField, Min(0f)] private float pushbackCooldown = 10f;
    [SerializeField, Min(0.05f)] private float pushbackMovementLock = 0.25f;

    [Header("Groggy Acceleration")]
    [SerializeField, Min(0f)] private float groggyBuffDuration = 5f;
    [SerializeField, Min(0f)] private float groggyBuildupPerHit = 2f;

    [Header("Slash Wave")]
    [SerializeField] private GameObject slashWavePrefab;
    [SerializeField, Min(0f)] private float slashWaveSpeed = 12f;
    [SerializeField, Min(0.1f)] private float slashWaveLifetime = 2.5f;

    [Header("Explosive Incapacitation")]
    [SerializeField, Min(0.1f)] private float explosiveGroggyDuration = 2f;

    public bool IsGroggyAccelerationActive => Time.time < groggyBuffEndsAt;
    public event Action<int, RelicDefinition> SkillUsed;

    private PlayerInventory inventory;
    private PlayerComboCounter combo;
    private PlayerAttackHitbox meleeHitbox;
    private Camera mainCamera;
    private float pushbackReadyAt;
    private float groggyBuffEndsAt;

    private void Awake()
    {
        inventory = GetComponent<PlayerInventory>();
        combo = GetComponent<PlayerComboCounter>();
        meleeHitbox = GetComponentInChildren<PlayerAttackHitbox>(true);
        mainCamera = Camera.main;
    }

    private void Update()
    {
        if (Keyboard.current?.digit1Key.wasPressedThisFrame == true)
            TryUseSkill(0);
        if (Keyboard.current?.digit2Key.wasPressedThisFrame == true)
            TryUseSkill(1);
    }

    public bool TryUseSkill(int skillIndex)
    {
        RelicDefinition relic = inventory != null ? inventory.GetEquippedSkillRelic(skillIndex) : null;
        if (relic == null)
        {
            Debug.Log($"[Skill] {skillIndex + 1}번 슬롯에 장착된 유물이 없습니다.", this);
            return false;
        }

        bool used = relic.SkillType switch
        {
            RelicSkillType.Pushback => UsePushback(),
            RelicSkillType.GroggyAcceleration => UseGroggyAcceleration(),
            RelicSkillType.SlashWave => UseSlashWave(),
            RelicSkillType.ExplosiveIncapacitation => UseExplosiveIncapacitation(),
            _ => false
        };

        if (used)
            SkillUsed?.Invoke(skillIndex, relic);
        return used;
    }

    public int GetRequiredCombo(RelicDefinition relic)
    {
        if (relic == null)
            return 0;

        return relic.SkillType switch
        {
            RelicSkillType.GroggyAcceleration => 10,
            RelicSkillType.SlashWave => 5,
            RelicSkillType.ExplosiveIncapacitation => 15,
            _ => 0
        };
    }

    public float GetCooldownDuration(RelicDefinition relic)
    {
        return relic != null && relic.SkillType == RelicSkillType.Pushback
            ? pushbackCooldown
            : 0f;
    }

    public float GetCooldownRemaining(RelicDefinition relic)
    {
        return relic != null && relic.SkillType == RelicSkillType.Pushback
            ? Mathf.Max(0f, pushbackReadyAt - Time.time)
            : 0f;
    }

    public bool HasEnoughCombo(RelicDefinition relic)
    {
        int required = GetRequiredCombo(relic);
        return required == 0 || combo != null && combo.CurrentCombo >= required;
    }

    public void NotifySuccessfulAttack(GameObject target)
    {
        if (!IsGroggyAccelerationActive || target == null)
            return;

        IGroggyBuildupReceiver receiver = FindInterface<IGroggyBuildupReceiver>(target);
        receiver?.AddGroggyBuildup(groggyBuildupPerHit, gameObject);
    }

    private bool UsePushback()
    {
        if (Time.time < pushbackReadyAt)
        {
            Debug.Log($"[Skill] 밀어내기 쿨타임 {pushbackReadyAt - Time.time:0.0}초", this);
            return false;
        }

        pushbackReadyAt = Time.time + pushbackCooldown;
        Collider2D[] targets = Physics2D.OverlapCircleAll(transform.position, pushbackRadius);
        HashSet<MeleeEnemyAI> pushedEnemies = new();
        foreach (Collider2D target in targets)
        {
            MeleeEnemyAI enemy = target.GetComponentInParent<MeleeEnemyAI>();
            if (enemy == null || !pushedEnemies.Add(enemy))
                continue;

            Vector2 direction = ((Vector2)enemy.transform.position - (Vector2)transform.position).normalized;
            if (direction == Vector2.zero)
                direction = Vector2.up;
            enemy.ApplyPushback(direction * pushbackForce, pushbackMovementLock);
        }

        if (SkillEffects.Instance != null)
            SkillEffects.Instance.PlayPushback(transform);
        return true;
    }

    private bool UseGroggyAcceleration()
    {
        if (combo == null || !combo.TryConsume(10))
        {
            Debug.Log("[Skill] 그로기 가속에는 연격 10이 필요합니다.", this);
            return false;
        }

        groggyBuffEndsAt = Time.time + groggyBuffDuration;
        if (SkillEffects.Instance != null)
        {
            PlayerController2D controller = GetComponent<PlayerController2D>();
            float facing = controller != null ? controller.FacingSign : 1f;
            SkillEffects.Instance.PlayGroggyHaste(transform, facing, groggyBuffDuration);
        }
        return true;
    }

    private bool UseSlashWave()
    {
        if (combo == null || !combo.TryConsume(5))
        {
            Debug.Log("[Skill] 참격 파동에는 연격 5가 필요합니다.", this);
            return false;
        }

        Vector2 direction = GetMouseDirection();
        GameObject projectileObject = Instantiate(
    slashWavePrefab,
    transform.position + (Vector3)(direction * 0.8f),
    Quaternion.identity);

        SlashWaveProjectile projectile =
            projectileObject.GetComponent<SlashWaveProjectile>();

        projectile.Initialize(direction, meleeHitbox != null ? meleeHitbox.Damage : 1,
            slashWaveSpeed, slashWaveLifetime, combo, this);
        return true;
    }

    private bool UseExplosiveIncapacitation()
    {
        int consumed = combo != null ? combo.ConsumeAll(15) : 0;
        if (consumed == 0)
        {
            Debug.Log("[Skill] 폭발적 무력화에는 최소 연격 15가 필요합니다.", this);
            return false;
        }

        int targetCount = 1 + (consumed - 15) / 5;
        List<GroggyTarget> visibleTargets = new();
        foreach (MeleeEnemyAI enemy in FindObjectsByType<MeleeEnemyAI>(FindObjectsSortMode.None))
        {
            if (!enemy.IsDead && !enemy.IsIncapacitated && IsVisible(enemy.transform.position))
                visibleTargets.Add(new GroggyTarget(enemy));
        }

        foreach (BossAI boss in FindObjectsByType<BossAI>(FindObjectsSortMode.None))
        {
            if (!boss.IsDefeated && IsVisible(boss.transform.position))
                visibleTargets.Add(new GroggyTarget(boss));
        }

        visibleTargets.Sort((left, right) =>
            Vector2.SqrMagnitude(left.Transform.position - transform.position)
                .CompareTo(Vector2.SqrMagnitude(right.Transform.position - transform.position)));

        for (int i = 0; i < Mathf.Min(targetCount, visibleTargets.Count); i++)
            visibleTargets[i].Apply(explosiveGroggyDuration, gameObject);

        if (SkillEffects.Instance != null)
            SkillEffects.Instance.PlayExplosiveIncapacitation(transform, consumed);
        return true;
    }

    private Vector2 GetMouseDirection()
    {
        if (mainCamera == null)
            mainCamera = Camera.main;
        if (mainCamera == null || Mouse.current == null)
            return Vector2.right;

        Vector3 mouseWorld = mainCamera.ScreenToWorldPoint(Mouse.current.position.ReadValue());
        Vector2 direction = (Vector2)(mouseWorld - transform.position);
        return direction.sqrMagnitude > 0.001f ? direction.normalized : Vector2.right;
    }

    private bool IsVisible(Vector3 worldPosition)
    {
        if (mainCamera == null)
            mainCamera = Camera.main;
        if (mainCamera == null)
            return true;

        Vector3 viewport = mainCamera.WorldToViewportPoint(worldPosition);
        return viewport.z > 0f && viewport.x >= 0f && viewport.x <= 1f &&
               viewport.y >= 0f && viewport.y <= 1f;
    }

    private static T FindInterface<T>(GameObject target) where T : class
    {
        foreach (MonoBehaviour behaviour in target.GetComponentsInParent<MonoBehaviour>(true))
        {
            if (behaviour is T result)
                return result;
        }
        return null;
    }
}

using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// 적군의 근접 공격 히트박스 제어 컴포넌트
/// </summary>
[RequireComponent(typeof(Collider2D))]
public sealed class EnemyAttackHitbox : MonoBehaviour
{
    [SerializeField, Min(1)] private int damage = 1;

    private readonly HashSet<IDamageable> hitTargets = new();
    private Collider2D hitbox;
    private Vector2 attackDirection = Vector2.right;
    private Component ownerComponent; // 자기 자신(적)에게 데미지를 주지 않기 위한 참조

    private void Awake()
    {
        CacheHitbox();
        gameObject.SetActive(false); // 기본 상태는 비활성화
    }

    public void Initialize(Component owner)
    {
        ownerComponent = owner;
    }

    /// <summary>
    /// 공격 시작: 히트박스 활성화 및 피격 대상 목록 초기화
    /// </summary>
    public void BeginAttack(Vector2 direction)
    {
        CacheHitbox();
        attackDirection = direction.normalized;
        hitTargets.Clear();
        gameObject.SetActive(true);
    }

    /// <summary>
    /// 공격 종료: 히트박스 비활성화
    /// </summary>
    public void EndAttack()
    {
        gameObject.SetActive(false);
    }

    private void CacheHitbox()
    {
        if (hitbox == null)
            hitbox = GetComponent<Collider2D>();

        hitbox.isTrigger = true;
    }

    private void OnTriggerEnter2D(Collider2D other)
    {
        IDamageable target = FindInterface<IDamageable>(other);

        // 대상이 없거나, 이미 이번 공격에 맞았거나, 공격을 실행한 본인이면 무시
        if (target == null || !hitTargets.Add(target) || target == ownerComponent)
            return;

        // 플레이어에게 데미지 전달
        target.TakeDamage(damage, other.ClosestPoint(transform.position), attackDirection);
    }

    private static T FindInterface<T>(Collider2D other) where T : class
    {
        MonoBehaviour[] behaviours = other.GetComponentsInParent<MonoBehaviour>();
        foreach (MonoBehaviour behaviour in behaviours)
        {
            if (behaviour is T result)
                return result;
        }

        return null;
    }
}
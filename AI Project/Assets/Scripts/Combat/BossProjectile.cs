using UnityEngine;

/// <summary>
/// 보스 탄막 패턴에서 공용으로 쓰는 투사체.
/// 하트 탄, 하트 비 등 어떤 패턴이든 방향 · 속도 · 데미지만 다르게 넣어서 재사용한다.
/// 직선으로 날아가며, 플레이어(IDamageable)와 충돌 시 데미지를 준다. 반사 없음(기획서 5.1 하트 탄 기준).
/// </summary>
[RequireComponent(typeof(Collider2D))]
public sealed class BossProjectile : MonoBehaviour
{
    [SerializeField] private float lifeTime = 5f; // 아무것도 못 맞추고 화면 밖으로 나갔을 때 자동 파괴

    private Vector2 direction = Vector2.left;
    private float speed = 5f;
    private int damage = 1;
    private bool hasHit;

    /// <summary>보스가 발사 시점에 호출해서 방향 · 속도 · 데미지를 설정.</summary>
    public void Launch(Vector2 launchDirection, float launchSpeed, int launchDamage)
    {
        direction = launchDirection.normalized;
        speed = launchSpeed;
        damage = launchDamage;
        hasHit = false;

        Destroy(gameObject, lifeTime);
    }

    private void Update()
    {
        transform.position += (Vector3)(direction * speed * Time.deltaTime);
    }

    private void OnTriggerEnter2D(Collider2D other)
    {
        if (hasHit) return;

        IDamageable target = other.GetComponentInParent<IDamageable>();
        if (target == null) return;

        hasHit = true;
        Vector2 hitPoint = other.ClosestPoint(transform.position);
        target.TakeDamage(damage, hitPoint, direction);

        Destroy(gameObject);
    }
}

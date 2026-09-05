using System.Collections.Generic;
using UnityEngine;

[RequireComponent(typeof(Collider2D))]
public sealed class PlayerAttackHitbox : MonoBehaviour
{
    [SerializeField, Min(1)] private int damage = 1;

    private readonly HashSet<IDamageable> hitTargets = new();
    private BoxCollider2D hitbox;
    private Vector2 attackDirection = Vector2.right;

    private void Awake()
    {
        CacheHitbox();
    }

    public void BeginAttack(Vector2 direction)
    {
        CacheHitbox();
        attackDirection = direction.normalized;
        hitTargets.Clear();
        gameObject.SetActive(true);
    }

    public void EndAttack()
    {
        gameObject.SetActive(false);
    }

    private void CacheHitbox()
    {
        if (hitbox == null)
            hitbox = GetComponent<BoxCollider2D>();

        hitbox.isTrigger = true;
        hitbox.enabled = true;
    }

    private void OnTriggerEnter2D(Collider2D other)
    {
        IDamageable target = FindInterface<IDamageable>(other);
        if (target == null || !hitTargets.Add(target))
            return;

        GameObject targetObject = target is MonoBehaviour behaviour
            ? behaviour.gameObject
            : other.gameObject;

        int allowedDamage = damage;
        OathSystem oathSystem = OathSystem.Instance;
        if (oathSystem != null &&
            !oathSystem.TryPreparePlayerMeleeHit(targetObject, damage, out allowedDamage))
        {
            return;
        }

        if (allowedDamage > 0)
            target.TakeDamage(allowedDamage, other.ClosestPoint(transform.position), attackDirection);

        if (oathSystem != null)
            oathSystem.CompletePlayerMeleeHit(targetObject);
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

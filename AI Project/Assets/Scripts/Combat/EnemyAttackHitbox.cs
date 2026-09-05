using System.Collections.Generic;
using UnityEngine;

[RequireComponent(typeof(Collider2D))]
public sealed class EnemyAttackHitbox : MonoBehaviour
{
    private readonly HashSet<PlayerController2D> hitPlayers = new();
    private Collider2D hitbox;
    private MeleeEnemyAI owner;
    private Vector2 attackDirection = Vector2.right;
    private int damage = 1;

    private void Awake()
    {
        CacheHitbox();
    }

    public void Initialize(MeleeEnemyAI attackOwner, int attackDamage)
    {
        owner = attackOwner;
        damage = Mathf.Max(1, attackDamage);
        CacheHitbox();
    }

    public void BeginAttack(Vector2 direction)
    {
        CacheHitbox();
        attackDirection = direction.normalized;
        hitPlayers.Clear();
        gameObject.SetActive(true);
    }

    public void EndAttack()
    {
        gameObject.SetActive(false);
    }

    private void CacheHitbox()
    {
        if (hitbox == null)
            hitbox = GetComponent<Collider2D>();
        hitbox.isTrigger = true;
        hitbox.enabled = true;
    }

    private void OnTriggerEnter2D(Collider2D other)
    {
        TryHitPlayer(other);
    }

    private void OnTriggerStay2D(Collider2D other)
    {
        TryHitPlayer(other);
    }

    private void TryHitPlayer(Collider2D other)
    {
        PlayerController2D player = other.GetComponentInParent<PlayerController2D>();
        if (player == null || !hitPlayers.Add(player))
            return;

        GameObject attacker = owner != null ? owner.gameObject : transform.root.gameObject;
        PlayerHitResult result = player.ReceiveEnemyAttack(
            damage, attacker, other.ClosestPoint(transform.position));
        Debug.Log($"[Enemy Attack] {attacker.name} → Player: {result}", this);
    }
}

using UnityEngine;

public interface IDamageable
{
    void TakeDamage(int damage, Vector2 hitPoint, Vector2 hitDirection);
}

public interface IEnemyStaggerable
{
    void EnterGroggy(float duration);
}

public enum PlayerHitResult
{
    Damaged,
    Blocked,
    Parried,
    Invulnerable
}


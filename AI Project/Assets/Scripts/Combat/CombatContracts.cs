using UnityEngine;

public interface IDamageable
{
    void TakeDamage(int damage, Vector2 hitPoint, Vector2 hitDirection);
}

public interface IGroggyReceiver
{
    void EnterGroggy(float duration, GameObject source);
}

public interface IGroggyBuildupReceiver
{
    void AddGroggyBuildup(float amount, GameObject source);
}

public enum PlayerHitResult
{
    Damaged,
    Blocked,
    Parried,
    Invulnerable
}

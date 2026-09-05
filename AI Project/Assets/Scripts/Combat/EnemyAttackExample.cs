using UnityEngine;

// 적의 공격 애니메이션 이벤트 또는 공격 히트박스에서 호출하는 예시입니다.
public sealed class EnemyAttackExample : MonoBehaviour
{
    [SerializeField, Min(1)] private int damage = 1;

    public PlayerHitResult HitPlayer(PlayerController2D player, Vector2 hitPoint)
    {
        if (player == null)
            return PlayerHitResult.Invulnerable;

        return player.ReceiveEnemyAttack(damage, gameObject, hitPoint);
    }
}

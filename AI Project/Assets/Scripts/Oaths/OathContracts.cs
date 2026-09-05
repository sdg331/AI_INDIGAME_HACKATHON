using UnityEngine;

// "나는 죽이지 못한다"가 피해량을 1 HP에서 멈추기 위해 사용하는 엔티티 인터페이스입니다.
public interface IOathHealthState
{
    int CurrentHealth { get; }
    bool IsDead { get; }
}

// HP가 1이 되었을 때 적을 쓰러진 상태로 전환하는 엔티티 인터페이스입니다.
public interface IOathIncapacitable
{
    bool IsIncapacitated { get; }
    void Incapacitate();
}

// 공격/체력 컴포넌트가 서로 다른 오브젝트에 있을 때 동일한 적임을 식별하는 선택 인터페이스입니다.
public interface IOathEntityIdentity
{
    int OathEntityId { get; }
}

public enum OathType
{
    CannotKill,
    RetaliationOnly
}

public enum EnemyDeathCause
{
    Player,
    Environment,
    OtherEnemy,
    Unknown
}


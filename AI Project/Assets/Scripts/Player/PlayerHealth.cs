using System;
using UnityEngine;
using UnityEngine.Events;

public sealed class PlayerHealth : MonoBehaviour, IDamageable
{
    [SerializeField, Min(1)] private int maxHealth = 5;
    [SerializeField] private UnityEvent<int, int> onHealthChanged;
    [SerializeField] private UnityEvent onDied;

    public int CurrentHealth { get; private set; }
    public int MaxHealth => maxHealth;
    public bool IsDead => CurrentHealth <= 0;
    public event Action<int, int> HealthChanged;

    // 씬에 미리 놓을 수 없는 오브젝트(엔딩 화면 등)가 사망을 구독할 때 사용합니다.
    public event Action Died;

    private void Awake()
    {
        CurrentHealth = maxHealth;
    }

    public void TakeDamage(int damage, Vector2 hitPoint, Vector2 hitDirection)
    {
        if (damage <= 0 || IsDead)
            return;

        CurrentHealth = Mathf.Max(0, CurrentHealth - damage);
        HealthChanged?.Invoke(CurrentHealth, maxHealth);
        onHealthChanged?.Invoke(CurrentHealth, maxHealth);
        Debug.Log($"[Player Health] 피해 {damage}, HP {CurrentHealth}/{maxHealth}", this);

        if (IsDead)
        {
            Debug.Log("[Player Health] 플레이어 사망", this);
            Died?.Invoke();
            onDied?.Invoke();
        }
    }

    public void RestoreFullHealth()
    {
        CurrentHealth = maxHealth;
        HealthChanged?.Invoke(CurrentHealth, maxHealth);
        onHealthChanged?.Invoke(CurrentHealth, maxHealth);
    }
}

using System;
using UnityEngine;

public sealed class PlayerComboCounter : MonoBehaviour
{
    [SerializeField, Min(1)] private int maximumCombo = 30;
    [SerializeField, Min(0.1f)] private float comboResetDelay = 3f;

    public int CurrentCombo { get; private set; }
    public int MaximumCombo => maximumCombo;
    public float RemainingTime => CurrentCombo > 0
        ? Mathf.Max(0f, resetAtTime - Time.time)
        : 0f;

    public event Action<int, int> ComboChanged;

    private float resetAtTime;

    private void Update()
    {
        if (CurrentCombo > 0 && Time.time >= resetAtTime)
            ResetCombo();
    }

    public void RegisterSuccessfulHit()
    {
        CurrentCombo = Mathf.Min(CurrentCombo + 1, maximumCombo);
        resetAtTime = Time.time + comboResetDelay;
        ComboChanged?.Invoke(CurrentCombo, maximumCombo);
        Debug.Log($"[연격] {CurrentCombo}/{maximumCombo}", this);
    }

    public void ResetCombo()
    {
        if (CurrentCombo == 0)
            return;

        CurrentCombo = 0;
        resetAtTime = 0f;
        ComboChanged?.Invoke(CurrentCombo, maximumCombo);
        Debug.Log("[연격] 제한시간 초과 → 초기화", this);
    }
}


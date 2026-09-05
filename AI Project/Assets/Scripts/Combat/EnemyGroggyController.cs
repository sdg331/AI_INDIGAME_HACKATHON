using System.Collections;
using UnityEngine;

// 적 루트에 붙이고, 그로기 중 멈춰야 할 이동/공격 스크립트를 behavioursToDisable에 넣으세요.
public sealed class EnemyGroggyController : MonoBehaviour, IEnemyStaggerable
{
    [SerializeField] private Animator animator;
    [SerializeField] private Behaviour[] behavioursToDisable;

    private Coroutine groggyRoutine;

    public void EnterGroggy(float duration)
    {
        if (groggyRoutine != null)
            StopCoroutine(groggyRoutine);

        groggyRoutine = StartCoroutine(GroggyRoutine(duration));
    }

    private IEnumerator GroggyRoutine(float duration)
    {
        SetEnemyBehaviours(false);
        SetGroggyAnimation(true);

        yield return new WaitForSeconds(Mathf.Max(0f, duration));

        SetGroggyAnimation(false);
        SetEnemyBehaviours(true);
        groggyRoutine = null;
    }

    private void SetEnemyBehaviours(bool value)
    {
        foreach (Behaviour behaviour in behavioursToDisable)
        {
            if (behaviour != null && behaviour != this)
                behaviour.enabled = value;
        }
    }

    private void SetGroggyAnimation(bool value)
    {
        if (animator != null)
            animator.SetBool("Groggy", value);
    }
}

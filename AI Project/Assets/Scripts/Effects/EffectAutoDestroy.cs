using UnityEngine;

// 한 번만 재생되는 이펙트를 재생이 끝나면 스스로 지웁니다.
// FX_* 프리팹 루트에 붙여 두고, 아무도 파괴하지 않아도 화면에 남지 않게 합니다.
public sealed class EffectAutoDestroy : MonoBehaviour
{
    [Tooltip("켜면 Animator의 첫 클립 길이를 수명으로 씁니다.")]
    [SerializeField] private bool useAnimationLength = true;

    [Tooltip("애니메이션 길이를 못 찾거나 위 옵션이 꺼져 있을 때 쓰는 수명(초).")]
    [SerializeField, Min(0.05f)] private float fallbackLifetime = 1f;

    [Tooltip("계산된 수명에 이만큼 더 두고 지웁니다.")]
    [SerializeField, Min(0f)] private float extraDelay = 0.05f;

    private void Start()
    {
        Destroy(gameObject, ResolveLifetime() + extraDelay);
    }

    private float ResolveLifetime()
    {
        if (!useAnimationLength)
            return fallbackLifetime;

        Animator animator = GetComponent<Animator>();
        if (animator == null || animator.runtimeAnimatorController == null)
            return fallbackLifetime;

        AnimationClip[] clips = animator.runtimeAnimatorController.animationClips;
        if (clips == null || clips.Length == 0 || clips[0] == null)
            return fallbackLifetime;

        return Mathf.Max(0.05f, clips[0].length);
    }
}

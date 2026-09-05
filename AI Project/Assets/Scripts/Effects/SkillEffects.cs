using UnityEngine;

// 유물 스킬과 전투 상태에 붙는 이펙트를 한 곳에서 생성합니다.
// 씬에 하나 두면 되고, 없으면 각 호출이 조용히 무시됩니다.
// 이펙트 시트의 부착 좌표(꼬리치레/outputs/이펙트_v2/이펙트_정렬표.md)를 픽셀 단위로 그대로 적어 두고
// 캐릭터 비주얼 스케일을 곱해 월드 좌표로 바꿉니다.
public sealed class SkillEffects : MonoBehaviour
{
    public static SkillEffects Instance { get; private set; }

    [Header("유물 스킬 (실제로 들어간 4종)")]
    [Tooltip("R-04 밀어내기. 주인공 발밑에 1회.")]
    [SerializeField] private GameObject pushbackEffect;

    [Tooltip("R-06 그로기 가속. 주인공 손 옆에서 버프가 끝날 때까지 루프.")]
    [SerializeField] private GameObject groggyHasteEffect;

    [Tooltip("R-08 폭발적 무력화 코어. 주인공 발밑에 1회.")]
    [SerializeField] private GameObject burstCoreEffect;

    [Tooltip("R-08 링 S / M / L. 소모한 연격에 따라 하나를 코어와 함께 재생합니다.")]
    [SerializeField] private GameObject burstRingSmall;
    [SerializeField] private GameObject burstRingMedium;
    [SerializeField] private GameObject burstRingLarge;

    [Header("전투 상태")]
    [Tooltip("그로기 진입. 적 발밑에 1회.")]
    [SerializeField] private GameObject groggyEnterEffect;

    [Tooltip("그로기 유지. 적 발밑에서 그로기가 풀릴 때까지 루프.")]
    [SerializeField] private GameObject groggyLoopEffect;

    [Tooltip("검 교체. 주인공 손 옆에 1회.")]
    [SerializeField] private GameObject swordSwapEffect;

    [Tooltip("맹세 위반. 주인공 손 옆에 1회.")]
    [SerializeField] private GameObject oathBreakEffect;

    [Header("부착 기준")]
    [Tooltip("캐릭터 비주얼 스케일. 픽셀 오프셋을 월드로 바꿀 때 곱합니다. (플레이어 Square = 3.12)")]
    [SerializeField, Min(0.01f)] private float playerVisualScale = 3.12f;

    [Tooltip("PPU. 픽셀 오프셋을 유닛으로 바꿀 때 나눕니다.")]
    [SerializeField, Min(1f)] private float pixelsPerUnit = 100f;

    [Tooltip("정렬표의 '손(대기)' 지점. 주인공 피벗에서 (+6, +5) 픽셀.")]
    [SerializeField] private Vector2 handOffsetPixels = new(6f, 5f);

    [Tooltip("R-08 링 크기 기준. 소모 연격이 이 값 미만이면 S, 다음 값 미만이면 M, 그 이상이면 L.")]
    [SerializeField] private int ringMediumThreshold = 25;
    [SerializeField] private int ringLargeThreshold = 40;

    private void Awake()
    {
        if (Instance != null && Instance != this)
        {
            Destroy(gameObject);
            return;
        }

        Instance = this;
    }

    private void OnDestroy()
    {
        if (Instance == this)
            Instance = null;
    }

    private Vector3 HandOffset(float facingSign)
    {
        float unit = playerVisualScale / pixelsPerUnit;
        return new Vector3(handOffsetPixels.x * unit * Mathf.Sign(facingSign), handOffsetPixels.y * unit, 0f);
    }

    // ---------------- 유물 스킬 ----------------

    public void PlayPushback(Transform player)
    {
        SpawnOneShot(pushbackEffect, player != null ? player.position : Vector3.zero, 1f);
    }

    // 버프가 끝날 때까지 플레이어를 따라다니는 루프 이펙트를 만듭니다.
    public GameObject PlayGroggyHaste(Transform player, float facingSign, float duration)
    {
        if (groggyHasteEffect == null || player == null)
            return null;

        GameObject instance = Instantiate(groggyHasteEffect, player.position + HandOffset(facingSign), Quaternion.identity, player);
        Destroy(instance, Mathf.Max(0.1f, duration));
        return instance;
    }

    public void PlayExplosiveIncapacitation(Transform player, int consumedCombo)
    {
        if (player == null)
            return;

        SpawnOneShot(burstCoreEffect, player.position, 1f);

        GameObject ring = burstRingSmall;
        if (consumedCombo >= ringLargeThreshold)
            ring = burstRingLarge;
        else if (consumedCombo >= ringMediumThreshold)
            ring = burstRingMedium;

        SpawnOneShot(ring, player.position, 1f);
    }

    // ---------------- 전투 상태 ----------------

    public void PlayGroggyEnter(Transform enemy)
    {
        SpawnOneShot(groggyEnterEffect, enemy != null ? enemy.position : Vector3.zero, 1f);
    }

    public GameObject PlayGroggyLoop(Transform enemy, float duration)
    {
        if (groggyLoopEffect == null || enemy == null)
            return null;

        GameObject instance = Instantiate(groggyLoopEffect, enemy.position, Quaternion.identity, enemy);
        if (duration > 0f)
            Destroy(instance, duration);
        return instance;
    }

    public void PlaySwordSwap(Transform player, float facingSign)
    {
        if (player == null)
            return;

        SpawnOneShot(swordSwapEffect, player.position + HandOffset(facingSign), 1f);
    }

    public void PlayOathBreak(Transform player, float facingSign)
    {
        if (player == null)
            return;

        SpawnOneShot(oathBreakEffect, player.position + HandOffset(facingSign), 1f);
    }

    private static void SpawnOneShot(GameObject prefab, Vector3 position, float facingSign)
    {
        if (prefab == null)
            return;

        GameObject instance = Instantiate(prefab, position, Quaternion.identity);
        if (facingSign < 0f)
        {
            SpriteRenderer renderer = instance.GetComponent<SpriteRenderer>();
            if (renderer != null)
                renderer.flipX = true;
        }

        if (instance.GetComponent<EffectAutoDestroy>() == null)
            instance.AddComponent<EffectAutoDestroy>();
    }
}

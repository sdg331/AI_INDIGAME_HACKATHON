using TMPro;
using UnityEngine;
using UnityEngine.UI;

/// <summary>
/// 보스전 동안 화면 상단에 표시되는 전용 체력 UI입니다.
/// 씬에 BossHealthHUD를 직접 배치해 꾸밀 수도 있고, 없으면 런타임에 기본 UI를 생성합니다.
/// </summary>
[DisallowMultipleComponent]
public sealed class BossHealthHUD : MonoBehaviour
{
    [Header("Optional Inspector References")]
    [SerializeField] private GameObject panelRoot;
    [SerializeField] private Image healthFill;
    [SerializeField] private Image damagePreviewFill;
    [SerializeField] private TMP_Text bossNameText;
    [SerializeField] private TMP_Text phaseText;
    [SerializeField] private TMP_Text healthText;

    [Header("Display")]
    [SerializeField, Min(0.01f)] private float healthDrainSpeed = 0.65f;
    [SerializeField, Min(0f)] private float damagePreviewDelay = 0.18f;
    [SerializeField, Min(0.01f)] private float damagePreviewSpeed = 0.35f;
    [SerializeField, Min(0f)] private float defeatedHideDelay = 1.5f;
    [SerializeField] private Color phase1Color = new(0.85f, 0.12f, 0.28f, 1f);
    [SerializeField] private Color phase2Color = new(0.9f, 0.12f, 0.72f, 1f);

    private static BossHealthHUD instance;

    private BossAI boundBoss;
    private float displayedRatio = 1f;
    private float previewRatio = 1f;
    private float previousTargetRatio = 1f;
    private float previewResumeTime;
    private float defeatedAt = -1f;

    private void Awake()
    {
        instance = this;
        EnsureCanvas();

        if (!HasAllReferences() && !TryCacheExistingPanel())
            BuildDefaultUI();

        SetPanelVisible(false);
    }

    private void OnDestroy()
    {
        if (instance == this)
            instance = null;
    }

    private void Update()
    {
        if (boundBoss == null || !boundBoss.isActiveAndEnabled)
        {
            SetPanelVisible(false);
            return;
        }

        int maximum = Mathf.Max(1, boundBoss.MaxHealth);
        float targetRatio = Mathf.Clamp01((float)boundBoss.CurrentHealth / maximum);
        if (targetRatio < previousTargetRatio)
            previewResumeTime = Time.unscaledTime + damagePreviewDelay;
        previousTargetRatio = targetRatio;

        displayedRatio = Mathf.MoveTowards(
            displayedRatio, targetRatio, healthDrainSpeed * Time.unscaledDeltaTime);

        if (previewRatio < displayedRatio)
            previewRatio = displayedRatio;
        else if (Time.unscaledTime >= previewResumeTime)
        {
            previewRatio = Mathf.MoveTowards(
                previewRatio, displayedRatio, damagePreviewSpeed * Time.unscaledDeltaTime);
        }

        healthFill.fillAmount = displayedRatio;
        damagePreviewFill.fillAmount = previewRatio;
        healthFill.color = boundBoss.CurrentPhase >= 2 ? phase2Color : phase1Color;
        bossNameText.text = boundBoss.BossDisplayName;
        phaseText.text = boundBoss.IsDefeated ? "GROGGY" : $"PHASE {boundBoss.CurrentPhase}";
        healthText.text = $"HP  {boundBoss.CurrentHealth} / {maximum}";

        if (boundBoss.IsDefeated)
        {
            if (defeatedAt < 0f)
                defeatedAt = Time.unscaledTime;
            if (Time.unscaledTime - defeatedAt >= defeatedHideDelay)
                SetPanelVisible(false);
        }
        else
        {
            defeatedAt = -1f;
            SetPanelVisible(true);
        }
    }

    public static BossHealthHUD GetOrCreate()
    {
        if (instance != null)
            return instance;

        BossHealthHUD existing = FindFirstObjectByType<BossHealthHUD>(FindObjectsInactive.Include);
        if (existing != null)
        {
            instance = existing;
            return existing;
        }

        GameObject hudObject = new("BossHealthHUD");
        instance = hudObject.AddComponent<BossHealthHUD>();
        return instance;
    }

    public void Bind(BossAI boss)
    {
        if (boss == null)
            return;

        boundBoss = boss;
        int maximum = Mathf.Max(1, boss.MaxHealth);
        displayedRatio = Mathf.Clamp01((float)boss.CurrentHealth / maximum);
        previewRatio = displayedRatio;
        previousTargetRatio = displayedRatio;
        previewResumeTime = 0f;
        defeatedAt = -1f;

        healthFill.fillAmount = displayedRatio;
        damagePreviewFill.fillAmount = previewRatio;
        SetPanelVisible(true);
    }

    public static void Unbind(BossAI boss)
    {
        if (instance == null || instance.boundBoss != boss)
            return;

        instance.boundBoss = null;
        instance.SetPanelVisible(false);
    }

    private void EnsureCanvas()
    {
        Canvas canvas = GetComponent<Canvas>();
        if (canvas == null)
            canvas = gameObject.AddComponent<Canvas>();
        canvas.renderMode = RenderMode.ScreenSpaceOverlay;
        canvas.sortingOrder = 80;

        CanvasScaler scaler = GetComponent<CanvasScaler>();
        if (scaler == null)
            scaler = gameObject.AddComponent<CanvasScaler>();
        scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
        scaler.referenceResolution = new Vector2(1920f, 1080f);
        scaler.matchWidthOrHeight = 0.5f;
    }

    private bool HasAllReferences()
    {
        return panelRoot != null && healthFill != null && damagePreviewFill != null &&
               bossNameText != null && phaseText != null && healthText != null;
    }

    private bool TryCacheExistingPanel()
    {
        Transform panel = transform.Find("BossHealthPanel");
        if (panel == null)
            return false;

        panelRoot = panel.gameObject;
        bossNameText = FindComponent<TMP_Text>(panel, "BossName");
        phaseText = FindComponent<TMP_Text>(panel, "Phase");
        healthText = FindComponent<TMP_Text>(panel, "HealthText");
        damagePreviewFill = FindComponent<Image>(panel, "HealthTrack/DamagePreview");
        healthFill = FindComponent<Image>(panel, "HealthTrack/HealthFill");
        return HasAllReferences();
    }

    private void BuildDefaultUI()
    {
        panelRoot = CreateUIObject("BossHealthPanel", transform);
        RectTransform panelRect = panelRoot.GetComponent<RectTransform>();
        panelRect.anchorMin = new Vector2(0.5f, 1f);
        panelRect.anchorMax = new Vector2(0.5f, 1f);
        panelRect.pivot = new Vector2(0.5f, 1f);
        panelRect.anchoredPosition = new Vector2(0f, -24f);
        panelRect.sizeDelta = new Vector2(1040f, 112f);

        Image panelImage = panelRoot.AddComponent<Image>();
        panelImage.color = new Color(0.025f, 0.018f, 0.035f, 0.94f);
        panelImage.raycastTarget = false;

        bossNameText = CreateText("BossName", panelRoot.transform, "VARGAL",
            new Vector2(-340f, 31f), new Vector2(320f, 34f), 28, TextAlignmentOptions.MidlineLeft);
        bossNameText.fontStyle = FontStyles.Bold;

        phaseText = CreateText("Phase", panelRoot.transform, "PHASE 1",
            new Vector2(390f, 31f), new Vector2(220f, 30f), 21, TextAlignmentOptions.MidlineRight);
        phaseText.color = new Color(1f, 0.7f, 0.86f, 1f);

        GameObject track = CreateUIObject("HealthTrack", panelRoot.transform);
        RectTransform trackRect = track.GetComponent<RectTransform>();
        trackRect.anchorMin = new Vector2(0.5f, 0.5f);
        trackRect.anchorMax = new Vector2(0.5f, 0.5f);
        trackRect.anchoredPosition = new Vector2(0f, -17f);
        trackRect.sizeDelta = new Vector2(940f, 36f);
        Image trackImage = track.AddComponent<Image>();
        trackImage.color = new Color(0.08f, 0.055f, 0.09f, 1f);
        trackImage.raycastTarget = false;

        damagePreviewFill = CreateFill("DamagePreview", track.transform,
            new Color(1f, 0.82f, 0.35f, 1f));
        healthFill = CreateFill("HealthFill", track.transform, phase1Color);

        healthText = CreateText("HealthText", panelRoot.transform, "HP  100 / 100",
            new Vector2(0f, -17f), new Vector2(900f, 34f), 21, TextAlignmentOptions.Center);
        healthText.fontStyle = FontStyles.Bold;
    }

    private static Image CreateFill(string objectName, Transform parent, Color color)
    {
        GameObject fillObject = CreateUIObject(objectName, parent);
        StretchToParent(fillObject.GetComponent<RectTransform>(), 4f);
        Image image = fillObject.AddComponent<Image>();
        image.type = Image.Type.Filled;
        image.fillMethod = Image.FillMethod.Horizontal;
        image.fillOrigin = (int)Image.OriginHorizontal.Left;
        image.fillAmount = 1f;
        image.color = color;
        image.raycastTarget = false;
        return image;
    }

    private static TMP_Text CreateText(string objectName, Transform parent, string content,
        Vector2 position, Vector2 size, float fontSize, TextAlignmentOptions alignment)
    {
        GameObject textObject = CreateUIObject(objectName, parent);
        RectTransform rect = textObject.GetComponent<RectTransform>();
        rect.anchoredPosition = position;
        rect.sizeDelta = size;

        TextMeshProUGUI text = textObject.AddComponent<TextMeshProUGUI>();
        text.text = content;
        text.fontSize = fontSize;
        text.alignment = alignment;
        text.color = Color.white;
        text.raycastTarget = false;
        return text;
    }

    private static T FindComponent<T>(Transform parent, string relativePath) where T : Component
    {
        Transform child = parent != null ? parent.Find(relativePath) : null;
        return child != null ? child.GetComponent<T>() : null;
    }

    private static GameObject CreateUIObject(string objectName, Transform parent)
    {
        GameObject result = new(objectName, typeof(RectTransform));
        result.transform.SetParent(parent, false);
        return result;
    }

    private static void StretchToParent(RectTransform rect, float inset)
    {
        rect.anchorMin = Vector2.zero;
        rect.anchorMax = Vector2.one;
        rect.offsetMin = new Vector2(inset, inset);
        rect.offsetMax = new Vector2(-inset, -inset);
    }

    private void SetPanelVisible(bool visible)
    {
        if (panelRoot != null && panelRoot.activeSelf != visible)
            panelRoot.SetActive(visible);
    }
}

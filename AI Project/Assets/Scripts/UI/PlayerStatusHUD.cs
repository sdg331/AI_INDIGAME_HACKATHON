using UnityEngine;
using UnityEngine.UI;

public sealed class PlayerStatusHUD : MonoBehaviour
{
    [Header("Optional Inspector References")]
    [SerializeField] private Slider healthSlider;
    [SerializeField] private Text healthText;
    [SerializeField] private Slider comboSlider;
    [SerializeField] private Text comboText;

    private PlayerHealth boundHealth;
    private PlayerComboCounter boundCombo;

    private void Awake()
    {
        if (healthSlider == null || healthText == null || comboSlider == null || comboText == null)
            BuildRuntimeHUD();
    }

    private void OnDestroy()
    {
        Unbind();
    }

    public static PlayerStatusHUD GetOrCreate()
    {
        PlayerStatusHUD existing = FindFirstObjectByType<PlayerStatusHUD>();
        if (existing != null)
            return existing;

        GameObject hudObject = new("PlayerStatusHUD");
        return hudObject.AddComponent<PlayerStatusHUD>();
    }

    public void Bind(PlayerHealth health, PlayerComboCounter combo)
    {
        Unbind();
        boundHealth = health;
        boundCombo = combo;

        if (boundHealth != null)
        {
            boundHealth.HealthChanged += UpdateHealth;
            UpdateHealth(boundHealth.CurrentHealth, boundHealth.MaxHealth);
        }

        if (boundCombo != null)
        {
            boundCombo.ComboChanged += UpdateCombo;
            UpdateCombo(boundCombo.CurrentCombo, boundCombo.MaximumCombo);
        }
    }

    private void Unbind()
    {
        if (boundHealth != null)
            boundHealth.HealthChanged -= UpdateHealth;
        if (boundCombo != null)
            boundCombo.ComboChanged -= UpdateCombo;
        boundHealth = null;
        boundCombo = null;
    }

    private void UpdateHealth(int current, int maximum)
    {
        healthSlider.minValue = 0f;
        healthSlider.maxValue = maximum;
        healthSlider.value = current;
        healthText.text = $"HP  {current} / {maximum}";
    }

    private void UpdateCombo(int current, int maximum)
    {
        comboSlider.minValue = 0f;
        comboSlider.maxValue = maximum;
        comboSlider.value = current;
        comboText.text = $"연격  {current} / {maximum}";
    }

    private void BuildRuntimeHUD()
    {
        Canvas canvas = gameObject.GetComponent<Canvas>();
        if (canvas == null)
            canvas = gameObject.AddComponent<Canvas>();
        canvas.renderMode = RenderMode.ScreenSpaceOverlay;
        canvas.sortingOrder = 50;

        CanvasScaler scaler = gameObject.GetComponent<CanvasScaler>();
        if (scaler == null)
            scaler = gameObject.AddComponent<CanvasScaler>();
        scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
        scaler.referenceResolution = new Vector2(1920f, 1080f);
        scaler.matchWidthOrHeight = 0.5f;

        if (gameObject.GetComponent<GraphicRaycaster>() == null)
            gameObject.AddComponent<GraphicRaycaster>();

        CreateBar("HealthBar", new Vector2(30f, 75f), new Color(0.8f, 0.1f, 0.1f, 1f),
            out healthSlider, out healthText);
        CreateBar("ComboBar", new Vector2(30f, 30f), new Color(1f, 0.65f, 0.05f, 1f),
            out comboSlider, out comboText);
    }

    private void CreateBar(string barName, Vector2 position, Color fillColor,
        out Slider slider, out Text valueText)
    {
        GameObject sliderObject = new(barName, typeof(RectTransform), typeof(Slider));
        sliderObject.transform.SetParent(transform, false);
        RectTransform sliderRect = sliderObject.GetComponent<RectTransform>();
        sliderRect.anchorMin = Vector2.zero;
        sliderRect.anchorMax = Vector2.zero;
        sliderRect.pivot = Vector2.zero;
        sliderRect.anchoredPosition = position;
        sliderRect.sizeDelta = new Vector2(320f, 32f);

        GameObject backgroundObject = new("Background", typeof(RectTransform), typeof(Image));
        backgroundObject.transform.SetParent(sliderObject.transform, false);
        RectTransform backgroundRect = backgroundObject.GetComponent<RectTransform>();
        Stretch(backgroundRect, Vector2.zero, Vector2.zero);
        backgroundObject.GetComponent<Image>().color = new Color(0.08f, 0.08f, 0.08f, 0.9f);

        GameObject fillAreaObject = new("Fill Area", typeof(RectTransform));
        fillAreaObject.transform.SetParent(sliderObject.transform, false);
        RectTransform fillAreaRect = fillAreaObject.GetComponent<RectTransform>();
        Stretch(fillAreaRect, new Vector2(4f, 4f), new Vector2(-4f, -4f));

        GameObject fillObject = new("Fill", typeof(RectTransform), typeof(Image));
        fillObject.transform.SetParent(fillAreaObject.transform, false);
        RectTransform fillRect = fillObject.GetComponent<RectTransform>();
        Stretch(fillRect, Vector2.zero, Vector2.zero);
        fillObject.GetComponent<Image>().color = fillColor;

        GameObject textObject = new("Value", typeof(RectTransform), typeof(Text));
        textObject.transform.SetParent(sliderObject.transform, false);
        RectTransform textRect = textObject.GetComponent<RectTransform>();
        Stretch(textRect, Vector2.zero, Vector2.zero);
        valueText = textObject.GetComponent<Text>();
        valueText.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
        valueText.fontSize = 18;
        valueText.fontStyle = FontStyle.Bold;
        valueText.alignment = TextAnchor.MiddleCenter;
        valueText.color = Color.white;

        slider = sliderObject.GetComponent<Slider>();
        slider.fillRect = fillRect;
        slider.handleRect = null;
        slider.targetGraphic = null;
        slider.direction = Slider.Direction.LeftToRight;
        slider.interactable = false;
    }

    private static void Stretch(RectTransform rect, Vector2 offsetMin, Vector2 offsetMax)
    {
        rect.anchorMin = Vector2.zero;
        rect.anchorMax = Vector2.one;
        rect.offsetMin = offsetMin;
        rect.offsetMax = offsetMax;
    }
}

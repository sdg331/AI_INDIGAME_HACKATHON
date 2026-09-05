using UnityEngine;

public sealed class EnemyHealthBar2D : MonoBehaviour
{
    [SerializeField] private Vector3 worldOffset = new(0f, 1.35f, 0f);
    [SerializeField, Min(0.1f)] private float width = 1.2f;
    [SerializeField, Min(0.02f)] private float height = 0.12f;
    [SerializeField, Min(0f)] private float decreaseSpeed = 4f;
    [SerializeField] private Color backgroundColor = new(0.12f, 0.12f, 0.12f, 0.9f);
    [SerializeField] private Color fillColor = new(0.85f, 0.12f, 0.12f, 1f);
    [SerializeField] private int sortingOrder = 200;

    private static Texture2D sharedTexture;
    private static Sprite centeredSprite;
    private static Sprite leftPivotSprite;

    private Transform barRoot;
    private Transform fillTransform;
    private float displayedRatio = 1f;
    private float targetRatio = 1f;
    private bool isVisible;

    private void Awake()
    {
        BuildIfNeeded();
        SetVisible(false);
    }

    private void LateUpdate()
    {
        if (barRoot == null)
            return;

        barRoot.position = transform.position + worldOffset;
        KeepConstantWorldScale();

        displayedRatio = Mathf.MoveTowards(
            displayedRatio, targetRatio, decreaseSpeed * Time.deltaTime);
        ApplyFillScale();
    }

    public void Initialize(int currentHealth, int maxHealth)
    {
        BuildIfNeeded();
        displayedRatio = GetRatio(currentHealth, maxHealth);
        targetRatio = displayedRatio;
        ApplyFillScale();
        SetVisible(false);
    }

    public void SetHealth(int currentHealth, int maxHealth, bool reveal = true)
    {
        BuildIfNeeded();
        targetRatio = GetRatio(currentHealth, maxHealth);
        if (reveal)
            SetVisible(true);
    }

    public void SetVisible(bool value)
    {
        isVisible = value;
        if (barRoot != null)
            barRoot.gameObject.SetActive(value);
    }

    private void BuildIfNeeded()
    {
        if (barRoot != null)
            return;

        EnsureSprites();
        GameObject root = new("EnemyHealthBar");
        root.transform.SetParent(transform, false);
        barRoot = root.transform;

        SpriteRenderer background = CreateRenderer("Background", centeredSprite, backgroundColor);
        background.transform.localScale = new Vector3(width + 0.08f, height + 0.08f, 1f);
        background.sortingOrder = sortingOrder;

        SpriteRenderer fill = CreateRenderer("Fill", leftPivotSprite, fillColor);
        fill.transform.localPosition = new Vector3(-width * 0.5f, 0f, -0.01f);
        fill.sortingOrder = sortingOrder + 1;
        fillTransform = fill.transform;
        ApplyFillScale();
    }

    private SpriteRenderer CreateRenderer(string objectName, Sprite sprite, Color color)
    {
        GameObject child = new(objectName);
        child.transform.SetParent(barRoot, false);
        SpriteRenderer renderer = child.AddComponent<SpriteRenderer>();
        renderer.sprite = sprite;
        renderer.color = color;
        return renderer;
    }

    private void ApplyFillScale()
    {
        if (fillTransform != null)
            fillTransform.localScale = new Vector3(width * displayedRatio, height, 1f);
    }

    private void KeepConstantWorldScale()
    {
        Transform parent = barRoot.parent;
        Vector3 parentScale = parent != null ? parent.lossyScale : Vector3.one;
        barRoot.localScale = new Vector3(
            SafeInverse(parentScale.x), SafeInverse(parentScale.y), 1f);
    }

    private static float SafeInverse(float value)
    {
        return Mathf.Abs(value) > 0.0001f ? 1f / Mathf.Abs(value) : 1f;
    }

    private static float GetRatio(int currentHealth, int maxHealth)
    {
        return maxHealth > 0 ? Mathf.Clamp01((float)currentHealth / maxHealth) : 0f;
    }

    private static void EnsureSprites()
    {
        if (sharedTexture == null)
        {
            sharedTexture = new Texture2D(1, 1)
            {
                name = "Runtime Health Bar Pixel",
                filterMode = FilterMode.Point,
                hideFlags = HideFlags.HideAndDontSave
            };
            sharedTexture.SetPixel(0, 0, Color.white);
            sharedTexture.Apply();
        }

        if (centeredSprite == null)
            centeredSprite = Sprite.Create(sharedTexture, new Rect(0f, 0f, 1f, 1f), new Vector2(0.5f, 0.5f), 1f);
        if (leftPivotSprite == null)
            leftPivotSprite = Sprite.Create(sharedTexture, new Rect(0f, 0f, 1f, 1f), new Vector2(0f, 0.5f), 1f);
    }
}

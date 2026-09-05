using UnityEngine;

public sealed class RewardPickupView : MonoBehaviour
{
    private static Texture2D fallbackTexture;
    private static Sprite fallbackSprite;

    public ItemDefinition Item { get; private set; }

    public void Initialize(ItemDefinition item)
    {
        Item = item;
        name = $"Reward_{item.DisplayName}";

        GameObject iconObject = new("Icon");
        iconObject.transform.SetParent(transform, false);
        iconObject.transform.localScale = new Vector3(0.55f, 0.55f, 1f);
        SpriteRenderer renderer = iconObject.AddComponent<SpriteRenderer>();
        renderer.sprite = item.Icon != null ? item.Icon : GetFallbackSprite();
        renderer.color = item.Icon != null
            ? Color.white
            : item is SwordDefinition
                ? new Color(0.8f, 0.85f, 0.95f, 1f)
                : new Color(1f, 0.65f, 0.15f, 1f);
        renderer.sortingOrder = 80;

        GameObject labelObject = new("Label");
        labelObject.transform.SetParent(transform, false);
        labelObject.transform.localPosition = new Vector3(0f, -0.65f, 0f);
        TextMesh label = labelObject.AddComponent<TextMesh>();
        label.text = $"{item.DisplayName}\n[F] 획득";
        label.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
        label.fontSize = 40;
        label.characterSize = 0.05f;
        label.anchor = TextAnchor.MiddleCenter;
        label.alignment = TextAlignment.Center;
        label.color = Color.white;
        label.GetComponent<MeshRenderer>().sortingOrder = 81;
    }

    private static Sprite GetFallbackSprite()
    {
        if (fallbackSprite != null)
            return fallbackSprite;

        fallbackTexture = new Texture2D(1, 1) { hideFlags = HideFlags.HideAndDontSave };
        fallbackTexture.SetPixel(0, 0, Color.white);
        fallbackTexture.Apply();
        fallbackSprite = Sprite.Create(fallbackTexture, new Rect(0f, 0f, 1f, 1f),
            new Vector2(0.5f, 0.5f), 1f);
        fallbackSprite.hideFlags = HideFlags.HideAndDontSave;
        return fallbackSprite;
    }
}

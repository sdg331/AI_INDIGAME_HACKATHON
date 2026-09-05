using TMPro;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

public sealed class OathHUD : MonoBehaviour, IPointerEnterHandler, IPointerExitHandler
{
    [SerializeField] private Image oathIcon;
    [SerializeField] private GameObject tooltipPanel;
    [SerializeField] private TMP_Text oathNameText;
    [SerializeField] private TMP_Text ruleDescriptionText;
    [SerializeField, Min(1f)] private float hoverScale = 1.15f;
    [SerializeField, Min(0f)] private float scaleSpeed = 12f;

    private Vector3 baseScale;
    private bool isHovered;

    private void Awake()
    {
        if (oathIcon == null)
            oathIcon = GetComponent<Image>();

        baseScale = oathIcon != null ? oathIcon.rectTransform.localScale : Vector3.one;
        if (tooltipPanel != null)
            tooltipPanel.SetActive(false);
    }

    private void Update()
    {
        if (oathIcon == null)
            return;

        Vector3 targetScale = baseScale * (isHovered ? hoverScale : 1f);
        oathIcon.rectTransform.localScale = Vector3.Lerp(
            oathIcon.rectTransform.localScale, targetScale, Time.unscaledDeltaTime * scaleSpeed);
    }

    public void Show(OathSystem.OathDefinition oath)
    {
        if (oath == null)
            return;

        gameObject.SetActive(true);
        if (oathIcon != null)
        {
            oathIcon.sprite = oath.icon;
            oathIcon.enabled = oath.icon != null;
        }

        if (oathNameText != null)
            oathNameText.text = oath.displayName;
        if (ruleDescriptionText != null)
            ruleDescriptionText.text = oath.ruleDescription;
    }

    public void OnPointerEnter(PointerEventData eventData)
    {
        isHovered = true;
        if (tooltipPanel != null)
            tooltipPanel.SetActive(true);
    }

    public void OnPointerExit(PointerEventData eventData)
    {
        isHovered = false;
        if (tooltipPanel != null)
            tooltipPanel.SetActive(false);
    }
}

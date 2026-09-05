using TMPro;
using UnityEngine;
using UnityEngine.UI;

public sealed class PlayerStatusHUD : MonoBehaviour
{
    [Header("Optional Inspector References")]
    [SerializeField] private Image healthSlider;
    [SerializeField] private TMP_Text healthText;
    [SerializeField] private Image comboSlider;
    [SerializeField] private TMP_Text comboText;

    private float healthWidth;
    private float comboWidth;


    private PlayerHealth boundHealth;
    private PlayerComboCounter boundCombo;

    private void Awake()
    {
        healthWidth = healthSlider.rectTransform.sizeDelta.x;
        comboWidth = comboSlider.rectTransform.sizeDelta.x;

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
    {   healthSlider.fillAmount = (float)current / maximum;
        healthText.text = $"HP  {current} / {maximum}";
    }

    private void UpdateCombo(int current, int maximum)
    {

        comboSlider.fillAmount = (float) current / maximum;
        comboText.text = $"연격  {current} / {maximum}";
    }

}

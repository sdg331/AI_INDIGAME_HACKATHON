using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.UI;
using UnityEngine.UI;

public sealed class PlayerInventoryHUD : MonoBehaviour
{
    private sealed class SkillSlotView
    {
        public GameObject Root;
        public Image Icon;
        public Image CooldownReveal;
        public Text KeyLabel;
        public Text NameLabel;
        public Text ResourceLabel;
        public CanvasGroup CanvasGroup;
    }

    private static Texture2D fallbackTexture;
    private static Sprite fallbackSprite;

    private PlayerInventory inventory;
    private RelicSkillController skillController;
    private PlayerComboCounter comboCounter;
    private GameObject inventoryPanel;
    private GameObject reserveSkillGroup;
    private Text[] swordLabels;
    private InventoryRelicSlotUI[] relicSlots;
    private Text equippedSwordLabel;
    private Text reserveSwordLabel;
    private SkillSlotView[] equippedSkillSlots;
    private SkillSlotView[] reserveSkillSlots;
    private bool inventoryVisible = true;
    private bool uiReady;

    private void Awake()
    {
        Transform existingInventory = transform.Find("InventoryPanel");
        Transform existingSkillPanel = transform.Find("SkillPanel");
        bool hasSavedLayout = existingInventory != null || existingSkillPanel != null;

        if (hasSavedLayout)
        {
            uiReady = TryCacheExistingUI(existingInventory, existingSkillPanel);
            if (!uiReady)
            {
                Debug.LogError(
                    "[Inventory UI] 저장된 UI 구조를 찾았지만 필수 오브젝트가 빠졌습니다. " +
                    "자동 생성 이름을 유지하거나 누락된 오브젝트를 복구해 주세요.", this);
            }
        }
        else
        {
            BuildUI();
            uiReady = true;
        }

        EnsureEventSystem();
    }

    private void Update()
    {
        if (!uiReady)
            return;

        if (Keyboard.current?.tabKey.wasPressedThisFrame == true)
            SetInventoryVisible(!inventoryVisible);

        RefreshSkillHud();
    }

    private void OnDestroy()
    {
        Unbind();
    }

    public static PlayerInventoryHUD GetOrCreate()
    {
        PlayerInventoryHUD existing =
            FindFirstObjectByType<PlayerInventoryHUD>(FindObjectsInactive.Include);
        if (existing != null)
            return existing;
        return new GameObject("PlayerInventoryHUD").AddComponent<PlayerInventoryHUD>();
    }

    public void Bind(PlayerInventory targetInventory, RelicSkillController targetSkillController,
        PlayerComboCounter targetComboCounter)
    {
        Unbind();
        inventory = targetInventory;
        skillController = targetSkillController;
        comboCounter = targetComboCounter;
        if (inventory == null || !uiReady)
            return;

        inventory.InventoryChanged += RefreshAll;
        inventory.EquippedSwordChanged += HandleEquippedSwordChanged;

        int relicUiIndex = 0;
        for (int swordIndex = 0; swordIndex < 2; swordIndex++)
        for (int relicIndex = 0; relicIndex < 2; relicIndex++)
        {
            relicSlots[relicUiIndex].Configure(inventory,
                new PlayerInventory.RelicSlotAddress(PlayerInventory.RelicSlotKind.Sword,
                    swordIndex, relicIndex),
                relicSlots[relicUiIndex].GetComponent<Image>(),
                relicSlots[relicUiIndex].GetComponentInChildren<Text>());
            relicUiIndex++;
        }

        for (int storageIndex = 0; storageIndex < 3; storageIndex++)
        {
            relicSlots[relicUiIndex].Configure(inventory,
                new PlayerInventory.RelicSlotAddress(PlayerInventory.RelicSlotKind.Storage,
                    -1, storageIndex),
                relicSlots[relicUiIndex].GetComponent<Image>(),
                relicSlots[relicUiIndex].GetComponentInChildren<Text>());
            relicUiIndex++;
        }

        RefreshAll();
    }

    public void SetInventoryVisible(bool visible)
    {
        inventoryVisible = visible;
        if (inventoryPanel != null)
            inventoryPanel.SetActive(visible);
    }

    private void Unbind()
    {
        if (inventory != null)
        {
            inventory.InventoryChanged -= RefreshAll;
            inventory.EquippedSwordChanged -= HandleEquippedSwordChanged;
        }

        inventory = null;
        skillController = null;
        comboCounter = null;
    }

    private void HandleEquippedSwordChanged(int index) => RefreshAll();

    private void RefreshAll()
    {
        RefreshInventoryPanel();
        RefreshSkillHud();
    }

    private void RefreshInventoryPanel()
    {
        if (inventory == null)
            return;

        for (int i = 0; i < swordLabels.Length; i++)
        {
            SwordDefinition sword = inventory.GetSword(i);
            string equipped = inventory.EquippedSwordIndex == i ? "  [장착]" : string.Empty;
            swordLabels[i].text = sword != null ? sword.DisplayName + equipped : "빈 검 슬롯";
        }

        foreach (InventoryRelicSlotUI slot in relicSlots)
            slot.Refresh();
    }

    private void RefreshSkillHud()
    {
        if (inventory == null)
            return;

        int equippedIndex = inventory.EquippedSwordIndex;
        int reserveIndex = 1 - equippedIndex;
        SwordDefinition equippedSword = inventory.GetSword(equippedIndex);
        SwordDefinition reserveSword = inventory.GetSword(reserveIndex);

        equippedSwordLabel.text = equippedSword != null
            ? $"장착 검 · {equippedSword.DisplayName}"
            : "장착된 검 없음";

        for (int slotIndex = 0; slotIndex < 2; slotIndex++)
            RefreshSkillSlot(equippedSkillSlots[slotIndex],
                inventory.GetSwordRelic(equippedIndex, slotIndex), slotIndex + 1, true);

        bool showReserve = reserveSword != null;
        reserveSkillGroup.SetActive(showReserve);
        if (!showReserve)
            return;

        float swapCooldown = inventory.SwordSwapCooldownRemaining;
        string swapStatus = swapCooldown > 0f
            ? $"교체 대기 {swapCooldown:0.0}초"
            : "R로 교체";
        reserveSwordLabel.text = $"예비 검 · {reserveSword.DisplayName}  ({swapStatus})";
        for (int slotIndex = 0; slotIndex < 2; slotIndex++)
            RefreshSkillSlot(reserveSkillSlots[slotIndex],
                inventory.GetSwordRelic(reserveIndex, slotIndex), slotIndex + 1, false);
    }

    private void RefreshSkillSlot(SkillSlotView view, RelicDefinition relic, int keyNumber,
        bool isEquipped)
    {
        view.KeyLabel.text = isEquipped ? keyNumber.ToString() : "R";
        view.CanvasGroup.alpha = isEquipped ? 1f : 0.62f;

        if (relic == null)
        {
            view.Icon.sprite = GetFallbackSprite();
            view.Icon.color = new Color(0.13f, 0.13f, 0.16f, 1f);
            view.CooldownReveal.enabled = false;
            view.NameLabel.text = "스킬 없음";
            view.ResourceLabel.text = string.Empty;
            return;
        }

        Sprite sprite = relic.Icon != null ? relic.Icon : GetFallbackSprite();
        Color brightColor = relic.Icon != null ? Color.white : GetSkillColor(relic.SkillType);
        int requiredCombo = skillController != null ? skillController.GetRequiredCombo(relic) : 0;
        float cooldownDuration = skillController != null
            ? skillController.GetCooldownDuration(relic)
            : 0f;
        float cooldownRemaining = skillController != null
            ? skillController.GetCooldownRemaining(relic)
            : 0f;
        bool enoughCombo = requiredCombo == 0 ||
                           comboCounter != null && comboCounter.CurrentCombo >= requiredCombo;
        bool ready = enoughCombo && cooldownRemaining <= 0f;

        view.Icon.sprite = sprite;
        view.Icon.color = ready ? brightColor : Dim(brightColor, 0.28f);
        view.NameLabel.text = relic.DisplayName;

        if (cooldownDuration > 0f && cooldownRemaining > 0f)
        {
            view.CooldownReveal.enabled = true;
            view.CooldownReveal.sprite = sprite;
            view.CooldownReveal.color = brightColor;
            view.CooldownReveal.fillAmount = Mathf.Clamp01(
                1f - cooldownRemaining / cooldownDuration);
            view.ResourceLabel.text = $"{cooldownRemaining:0.0}초";
            view.ResourceLabel.color = new Color(1f, 0.75f, 0.25f, 1f);
        }
        else
        {
            view.CooldownReveal.enabled = false;
            if (requiredCombo > 0)
            {
                int currentCombo = comboCounter != null ? comboCounter.CurrentCombo : 0;
                view.ResourceLabel.text = $"연격 {currentCombo}/{requiredCombo}";
                view.ResourceLabel.color = enoughCombo
                    ? new Color(0.35f, 1f, 0.55f, 1f)
                    : new Color(1f, 0.4f, 0.4f, 1f);
            }
            else
            {
                view.ResourceLabel.text = "준비 완료";
                view.ResourceLabel.color = new Color(0.35f, 1f, 0.55f, 1f);
            }
        }
    }

    private void BuildUI()
    {
        Canvas canvas = GetComponent<Canvas>();
        if (canvas == null)
            canvas = gameObject.AddComponent<Canvas>();
        canvas.renderMode = RenderMode.ScreenSpaceOverlay;
        canvas.sortingOrder = 40;

        CanvasScaler scaler = GetComponent<CanvasScaler>();
        if (scaler == null)
            scaler = gameObject.AddComponent<CanvasScaler>();
        scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
        scaler.referenceResolution = new Vector2(1920f, 1080f);

        if (GetComponent<GraphicRaycaster>() == null)
            gameObject.AddComponent<GraphicRaycaster>();

        BuildInventoryPanel();
        BuildSkillPanel();
    }

    private bool TryCacheExistingUI(Transform savedInventory, Transform savedSkillPanel)
    {
        if (savedInventory == null || savedSkillPanel == null)
            return false;

        inventoryPanel = savedInventory.gameObject;
        swordLabels = new[]
        {
            FindComponent<Text>(savedInventory, "Sword1"),
            FindComponent<Text>(savedInventory, "Sword2")
        };

        relicSlots = new[]
        {
            FindComponent<InventoryRelicSlotUI>(savedInventory, "Sword1Relic1"),
            FindComponent<InventoryRelicSlotUI>(savedInventory, "Sword1Relic2"),
            FindComponent<InventoryRelicSlotUI>(savedInventory, "Sword2Relic1"),
            FindComponent<InventoryRelicSlotUI>(savedInventory, "Sword2Relic2"),
            FindComponent<InventoryRelicSlotUI>(savedInventory, "Storage1"),
            FindComponent<InventoryRelicSlotUI>(savedInventory, "Storage2"),
            FindComponent<InventoryRelicSlotUI>(savedInventory, "Storage3")
        };

        equippedSwordLabel = FindComponent<Text>(savedSkillPanel, "EquippedSword");
        equippedSkillSlots = new[]
        {
            CacheSkillSlot(savedSkillPanel, "EquippedSkill1"),
            CacheSkillSlot(savedSkillPanel, "EquippedSkill2")
        };

        Transform savedReserveGroup = savedSkillPanel.Find("ReserveSkills");
        if (savedReserveGroup == null)
            return false;

        reserveSkillGroup = savedReserveGroup.gameObject;
        reserveSwordLabel = FindComponent<Text>(savedReserveGroup, "ReserveSword");
        reserveSkillSlots = new[]
        {
            CacheSkillSlot(savedReserveGroup, "ReserveSkill1"),
            CacheSkillSlot(savedReserveGroup, "ReserveSkill2")
        };

        return AllAssigned(swordLabels) && AllAssigned(relicSlots) &&
               equippedSwordLabel != null && reserveSwordLabel != null &&
               AllAssigned(equippedSkillSlots) && AllAssigned(reserveSkillSlots);
    }

    private static SkillSlotView CacheSkillSlot(Transform parent, string rootName)
    {
        Transform root = parent.Find(rootName);
        Transform frame = root != null ? root.Find("Frame") : null;
        if (root == null || frame == null)
            return null;

        Image icon = FindComponent<Image>(frame, "Icon");
        Image reveal = FindComponent<Image>(frame, "CooldownReveal");
        Text keyLabel = FindComponent<Text>(frame, "Key");
        Text nameLabel = FindComponent<Text>(root, "Name");
        Text resourceLabel = FindComponent<Text>(root, "Resource");
        CanvasGroup canvasGroup = root.GetComponent<CanvasGroup>();
        if (icon == null || reveal == null || keyLabel == null || nameLabel == null ||
            resourceLabel == null || canvasGroup == null)
        {
            return null;
        }

        return new SkillSlotView
        {
            Root = root.gameObject,
            Icon = icon,
            CooldownReveal = reveal,
            KeyLabel = keyLabel,
            NameLabel = nameLabel,
            ResourceLabel = resourceLabel,
            CanvasGroup = canvasGroup
        };
    }

    private static T FindComponent<T>(Transform parent, string childName) where T : Component
    {
        Transform child = parent != null ? parent.Find(childName) : null;
        return child != null ? child.GetComponent<T>() : null;
    }

    private static bool AllAssigned<T>(T[] values) where T : class
    {
        if (values == null)
            return false;
        foreach (T value in values)
        {
            if (value == null)
                return false;
        }
        return true;
    }

    private void BuildInventoryPanel()
    {
        inventoryPanel = CreateUIObject("InventoryPanel", transform);
        RectTransform panelRect = inventoryPanel.GetComponent<RectTransform>();
        panelRect.anchorMin = new Vector2(1f, 0.5f);
        panelRect.anchorMax = new Vector2(1f, 0.5f);
        panelRect.pivot = new Vector2(1f, 0.5f);
        panelRect.anchoredPosition = new Vector2(-25f, 0f);
        panelRect.sizeDelta = new Vector2(460f, 310f);
        Image panelImage = inventoryPanel.AddComponent<Image>();
        panelImage.color = new Color(0.04f, 0.04f, 0.06f, 0.9f);

        CreateText("Title", inventoryPanel.transform, "검과 유물  ·  [Tab] 닫기",
            new Vector2(0f, 130f), new Vector2(430f, 30f), 22);
        swordLabels = new Text[2];
        relicSlots = new InventoryRelicSlotUI[7];

        int slotIndex = 0;
        for (int sword = 0; sword < 2; sword++)
        {
            float x = sword == 0 ? -112f : 112f;
            swordLabels[sword] = CreateText($"Sword{sword + 1}", inventoryPanel.transform,
                "빈 검 슬롯", new Vector2(x, 88f), new Vector2(210f, 28f), 17);
            for (int relic = 0; relic < 2; relic++)
            {
                float relicX = x + (relic == 0 ? -48f : 48f);
                relicSlots[slotIndex++] = CreateRelicSlot(inventoryPanel.transform,
                    $"Sword{sword + 1}Relic{relic + 1}", new Vector2(relicX, 28f));
            }
        }

        CreateText("StorageTitle", inventoryPanel.transform, "유물 보관함",
            new Vector2(0f, -40f), new Vector2(430f, 25f), 17);
        for (int i = 0; i < 3; i++)
            relicSlots[slotIndex++] = CreateRelicSlot(inventoryPanel.transform,
                $"Storage{i + 1}", new Vector2((i - 1) * 100f, -100f));
    }

    private void BuildSkillPanel()
    {
        GameObject panel = CreateUIObject("SkillPanel", transform);
        RectTransform panelRect = panel.GetComponent<RectTransform>();
        panelRect.anchorMin = new Vector2(0.5f, 0f);
        panelRect.anchorMax = new Vector2(0.5f, 0f);
        panelRect.pivot = new Vector2(0.5f, 0f);
        panelRect.anchoredPosition = new Vector2(0f, 20f);
        panelRect.sizeDelta = new Vector2(360f, 270f);
        Image panelImage = panel.AddComponent<Image>();
        panelImage.color = new Color(0.025f, 0.025f, 0.04f, 0.82f);

        equippedSwordLabel = CreateText("EquippedSword", panel.transform, "장착 검",
            new Vector2(0f, 112f), new Vector2(330f, 24f), 17);
        equippedSkillSlots = new SkillSlotView[2];
        equippedSkillSlots[0] = CreateSkillSlot(panel.transform, "EquippedSkill1",
            new Vector2(-62f, 43f));
        equippedSkillSlots[1] = CreateSkillSlot(panel.transform, "EquippedSkill2",
            new Vector2(62f, 43f));

        reserveSkillGroup = CreateUIObject("ReserveSkills", panel.transform);
        RectTransform reserveRect = reserveSkillGroup.GetComponent<RectTransform>();
        reserveRect.anchorMin = Vector2.zero;
        reserveRect.anchorMax = Vector2.one;
        reserveRect.offsetMin = Vector2.zero;
        reserveRect.offsetMax = Vector2.zero;
        reserveSwordLabel = CreateText("ReserveSword", reserveSkillGroup.transform, "예비 검",
            new Vector2(0f, -25f), new Vector2(330f, 22f), 15);
        reserveSkillSlots = new SkillSlotView[2];
        reserveSkillSlots[0] = CreateSkillSlot(reserveSkillGroup.transform, "ReserveSkill1",
            new Vector2(-62f, -79f));
        reserveSkillSlots[1] = CreateSkillSlot(reserveSkillGroup.transform, "ReserveSkill2",
            new Vector2(62f, -79f));
    }

    private static SkillSlotView CreateSkillSlot(Transform parent, string objectName, Vector2 position)
    {
        GameObject root = CreateUIObject(objectName, parent);
        RectTransform rootRect = root.GetComponent<RectTransform>();
        rootRect.anchoredPosition = position;
        rootRect.sizeDelta = new Vector2(116f, 106f);
        CanvasGroup canvasGroup = root.AddComponent<CanvasGroup>();

        GameObject frame = CreateUIObject("Frame", root.transform);
        RectTransform frameRect = frame.GetComponent<RectTransform>();
        frameRect.anchoredPosition = new Vector2(0f, 16f);
        frameRect.sizeDelta = new Vector2(62f, 62f);
        Image frameImage = frame.AddComponent<Image>();
        frameImage.color = new Color(0.11f, 0.11f, 0.14f, 0.95f);

        GameObject iconObject = CreateUIObject("Icon", frame.transform);
        StretchToParent(iconObject.GetComponent<RectTransform>(), 3f);
        Image icon = iconObject.AddComponent<Image>();
        icon.preserveAspect = true;
        icon.raycastTarget = false;

        GameObject revealObject = CreateUIObject("CooldownReveal", frame.transform);
        StretchToParent(revealObject.GetComponent<RectTransform>(), 3f);
        Image reveal = revealObject.AddComponent<Image>();
        reveal.type = Image.Type.Filled;
        reveal.fillMethod = Image.FillMethod.Radial360;
        reveal.fillOrigin = (int)Image.Origin360.Top;
        reveal.fillClockwise = true;
        reveal.fillAmount = 0f;
        reveal.preserveAspect = true;
        reveal.raycastTarget = false;

        Text keyLabel = CreateText("Key", frame.transform, string.Empty,
            new Vector2(-21f, 21f), new Vector2(22f, 20f), 14);
        keyLabel.alignment = TextAnchor.MiddleCenter;
        keyLabel.color = new Color(1f, 0.9f, 0.45f, 1f);

        Text nameLabel = CreateText("Name", root.transform, "스킬 없음",
            new Vector2(0f, -25f), new Vector2(116f, 20f), 13);
        Text resourceLabel = CreateText("Resource", root.transform, string.Empty,
            new Vector2(0f, -43f), new Vector2(116f, 18f), 12);

        return new SkillSlotView
        {
            Root = root,
            Icon = icon,
            CooldownReveal = reveal,
            KeyLabel = keyLabel,
            NameLabel = nameLabel,
            ResourceLabel = resourceLabel,
            CanvasGroup = canvasGroup
        };
    }

    private static InventoryRelicSlotUI CreateRelicSlot(Transform parent, string objectName,
        Vector2 position)
    {
        GameObject slot = CreateUIObject(objectName, parent);
        RectTransform rect = slot.GetComponent<RectTransform>();
        rect.anchoredPosition = position;
        rect.sizeDelta = new Vector2(86f, 66f);
        Image image = slot.AddComponent<Image>();
        image.color = new Color(0.15f, 0.15f, 0.18f, 1f);
        CreateText("Label", slot.transform, "비어 있음", Vector2.zero, rect.sizeDelta, 12);
        return slot.AddComponent<InventoryRelicSlotUI>();
    }

    private static Text CreateText(string objectName, Transform parent, string content,
        Vector2 position, Vector2 size, int fontSize)
    {
        GameObject textObject = CreateUIObject(objectName, parent);
        RectTransform rect = textObject.GetComponent<RectTransform>();
        rect.anchoredPosition = position;
        rect.sizeDelta = size;
        Text text = textObject.AddComponent<Text>();
        text.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
        text.fontSize = fontSize;
        text.alignment = TextAnchor.MiddleCenter;
        text.color = Color.white;
        text.text = content;
        text.raycastTarget = false;
        return text;
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

    private static Color GetSkillColor(RelicSkillType type)
    {
        return type switch
        {
            RelicSkillType.Pushback => new Color(0.35f, 0.8f, 1f, 1f),
            RelicSkillType.GroggyAcceleration => new Color(0.85f, 0.45f, 1f, 1f),
            RelicSkillType.SlashWave => new Color(0.4f, 1f, 0.75f, 1f),
            RelicSkillType.ExplosiveIncapacitation => new Color(1f, 0.45f, 0.2f, 1f),
            _ => Color.white
        };
    }

    private static Color Dim(Color color, float multiplier)
    {
        return new Color(color.r * multiplier, color.g * multiplier,
            color.b * multiplier, color.a);
    }

    private static void EnsureEventSystem()
    {
        if (EventSystem.current != null)
            return;
        _ = new GameObject("EventSystem", typeof(EventSystem), typeof(InputSystemUIInputModule));
    }
}

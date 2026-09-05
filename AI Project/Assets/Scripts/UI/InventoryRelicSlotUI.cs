using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

public sealed class InventoryRelicSlotUI : MonoBehaviour,
    IBeginDragHandler, IDragHandler, IEndDragHandler, IDropHandler
{
    private PlayerInventory inventory;
    private PlayerInventory.RelicSlotAddress address;
    private Image icon;
    private Text label;
    private GameObject dragGhost;
    private bool dropHandled;

    public void Configure(PlayerInventory sourceInventory,
        PlayerInventory.RelicSlotAddress slotAddress, Image slotIcon, Text slotLabel)
    {
        inventory = sourceInventory;
        address = slotAddress;
        icon = slotIcon;
        label = slotLabel;
        Refresh();
    }

    public void Refresh()
    {
        RelicDefinition relic = GetRelic();
        if (icon != null)
        {
            icon.sprite = relic != null ? relic.Icon : null;
            if (relic == null)
                icon.color = new Color(0.15f, 0.15f, 0.18f, 1f);
            else
                icon.color = relic.Icon != null ? Color.white : new Color(0.55f, 0.35f, 0.08f, 1f);
        }
        if (label != null)
            label.text = relic != null ? relic.DisplayName : "비어 있음";
    }

    public void OnBeginDrag(PointerEventData eventData)
    {
        RelicDefinition relic = GetRelic();
        if (relic == null)
            return;

        dropHandled = false;
        dragGhost = new GameObject("RelicDragGhost", typeof(RectTransform), typeof(CanvasGroup), typeof(Image));
        dragGhost.transform.SetParent(GetComponentInParent<Canvas>().transform, false);
        RectTransform rect = dragGhost.GetComponent<RectTransform>();
        rect.sizeDelta = new Vector2(56f, 56f);
        Image image = dragGhost.GetComponent<Image>();
        image.sprite = relic.Icon;
        image.color = relic.Icon != null ? Color.white : new Color(1f, 0.7f, 0.2f, 0.8f);
        image.raycastTarget = false;
        dragGhost.GetComponent<CanvasGroup>().blocksRaycasts = false;
        OnDrag(eventData);
    }

    public void OnDrag(PointerEventData eventData)
    {
        if (dragGhost != null)
            dragGhost.transform.position = eventData.position;
    }

    public void OnDrop(PointerEventData eventData)
    {
        InventoryRelicSlotUI source = eventData.pointerDrag != null
            ? eventData.pointerDrag.GetComponent<InventoryRelicSlotUI>()
            : null;
        if (source == null || source.inventory != inventory)
            return;

        source.dropHandled = inventory.TryMoveRelic(source.address, address);
    }

    public void OnEndDrag(PointerEventData eventData)
    {
        if (dragGhost != null)
            Destroy(dragGhost);

        if (!dropHandled && address.Kind == PlayerInventory.RelicSlotKind.Sword)
            inventory.TryUnequipRelic(address.SwordIndex, address.SlotIndex);
    }

    private RelicDefinition GetRelic()
    {
        return address.Kind == PlayerInventory.RelicSlotKind.Storage
            ? inventory.GetStoredRelic(address.SlotIndex)
            : inventory.GetSwordRelic(address.SwordIndex, address.SlotIndex);
    }
}

using UnityEngine;
using UnityEngine.InputSystem;

public sealed class WorldItemPickup : MonoBehaviour
{
    [SerializeField] private ItemDefinition item;
    [SerializeField, Min(0.5f)] private float pickupDistance = 2f;

    public ItemDefinition Item => item;

    private PlayerInventory playerInventory;

    public void Initialize(ItemDefinition definition, float distance = 2f)
    {
        item = definition;
        pickupDistance = Mathf.Max(0.5f, distance);

        RewardPickupView view = GetComponent<RewardPickupView>();
        if (view == null)
            view = gameObject.AddComponent<RewardPickupView>();
        view.Initialize(item);
    }

    private void Start()
    {
        if (item == null)
        {
            Debug.LogError("[Item Pickup] 획득할 아이템이 지정되지 않았습니다.", this);
            enabled = false;
            return;
        }

        if (GetComponent<RewardPickupView>() == null)
            Initialize(item, pickupDistance);
    }

    private void Update()
    {
        if (Keyboard.current?.fKey.wasPressedThisFrame != true)
            return;

        if (playerInventory == null)
            playerInventory = FindFirstObjectByType<PlayerInventory>();
        if (playerInventory == null || !IsClosestPickupToPlayer())
            return;

        float distance = Vector2.Distance(transform.position, playerInventory.transform.position);
        if (distance > pickupDistance)
            return;

        if (!playerInventory.TryAddItem(item))
        {
            Debug.Log($"[Item Pickup] 인벤토리가 가득 차서 {item.DisplayName}을(를) 획득할 수 없습니다.", this);
            return;
        }

        Debug.Log($"[Item Pickup] {item.DisplayName} 획득", this);
        Destroy(gameObject);
    }

    private bool IsClosestPickupToPlayer()
    {
        WorldItemPickup[] pickups = FindObjectsByType<WorldItemPickup>(FindObjectsSortMode.None);
        WorldItemPickup closest = null;
        float closestDistance = float.PositiveInfinity;

        foreach (WorldItemPickup pickup in pickups)
        {
            if (pickup == null || pickup.item == null)
                continue;

            float distance = Vector2.SqrMagnitude(
                pickup.transform.position - playerInventory.transform.position);
            if (distance < closestDistance)
            {
                closestDistance = distance;
                closest = pickup;
            }
        }

        return closest == this;
    }
}

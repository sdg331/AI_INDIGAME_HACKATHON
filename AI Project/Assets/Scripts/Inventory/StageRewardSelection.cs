using System.Collections.Generic;
using UnityEngine;
using UnityEngine.InputSystem;

public sealed class StageRewardSelection : MonoBehaviour
{
    [SerializeField, Min(0.5f)] private float choiceSpacing = 2f;
    [SerializeField, Min(0.5f)] private float pickupDistance = 2f;
    [SerializeField] private Vector3 spawnOffset = new(0f, 1f, 0f);

    public bool HasPendingChoice => activePickups.Count > 0;

    private readonly List<RewardPickupView> activePickups = new();
    private PlayerInventory playerInventory;
    private StageManager stageManager;

    private void Update()
    {
        if (!HasPendingChoice || Keyboard.current?.fKey.wasPressedThisFrame != true)
            return;

        if (playerInventory == null)
            playerInventory = FindFirstObjectByType<PlayerInventory>();
        if (playerInventory == null)
            return;

        RewardPickupView closest = FindClosestPickup(playerInventory.transform.position);
        if (closest == null)
            return;

        if (!playerInventory.CanAddItem(closest.Item))
        {
            Debug.Log("[Reward] 인벤토리가 가득 차 아이템을 획득할 수 없습니다.", closest);
            return;
        }

        playerInventory.TryAddItem(closest.Item);
        Debug.Log($"[Reward] {closest.Item.DisplayName} 획득", closest);
        ClearChoices();
        if (stageManager != null)
            stageManager.OnStageRewardSelected();
    }

    public void Initialize(StageManager manager)
    {
        stageManager = manager;
    }

    public void SpawnChoices(IReadOnlyList<ItemDefinition> itemPool, Vector3 center)
    {
        ClearChoices();
        if (itemPool == null)
            return;

        List<ItemDefinition> candidates = new();
        foreach (ItemDefinition item in itemPool)
        {
            if (item != null && !candidates.Contains(item))
                candidates.Add(item);
        }

        for (int i = 0; i < 3 && candidates.Count > 0; i++)
        {
            int randomIndex = Random.Range(0, candidates.Count);
            ItemDefinition item = candidates[randomIndex];
            candidates.RemoveAt(randomIndex);

            GameObject pickupObject = new($"Reward_{item.DisplayName}");
            pickupObject.transform.position = center + spawnOffset +
                                              Vector3.right * ((i - 1) * choiceSpacing);
            RewardPickupView pickup = pickupObject.AddComponent<RewardPickupView>();
            pickup.Initialize(item);
            activePickups.Add(pickup);
        }

        if (activePickups.Count < 3 && activePickups.Count > 0)
            Debug.LogWarning("[Reward] 보상 풀에 서로 다른 아이템이 3개 미만입니다.", this);
    }

    public void ClearChoices()
    {
        foreach (RewardPickupView pickup in activePickups)
        {
            if (pickup != null)
                Destroy(pickup.gameObject);
        }
        activePickups.Clear();
    }

    private RewardPickupView FindClosestPickup(Vector3 playerPosition)
    {
        RewardPickupView closest = null;
        float closestDistance = pickupDistance * pickupDistance;
        foreach (RewardPickupView pickup in activePickups)
        {
            if (pickup == null)
                continue;
            float distance = (pickup.transform.position - playerPosition).sqrMagnitude;
            if (distance <= closestDistance)
            {
                closestDistance = distance;
                closest = pickup;
            }
        }
        return closest;
    }
}

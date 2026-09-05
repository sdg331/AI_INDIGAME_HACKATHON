using System.Collections.Generic;
using UnityEngine;
using UnityEngine.InputSystem;

public sealed class TestItemSpawner : MonoBehaviour
{
    [Header("Test Items")]
    [Tooltip("비워두면 DefaultItemCatalog의 모든 기본 아이템을 생성합니다.")]
    [SerializeField] private List<ItemDefinition> items = new();
    [SerializeField] private bool spawnOnStart = true;

    [Header("Placement")]
    [SerializeField, Min(0.5f)] private float spacing = 1.5f;
    [SerializeField, Min(0.5f)] private float pickupDistance = 2f;

    [Header("Runtime Shortcut")]
    [SerializeField] private bool allowTKeyRespawn = true;
    [SerializeField] private bool replacePreviousItems = true;

    private readonly List<GameObject> spawnedItems = new();

    private void Start()
    {
        if (spawnOnStart)
            SpawnTestItems();
    }

    private void Update()
    {
        if (allowTKeyRespawn && Keyboard.current?.tKey.wasPressedThisFrame == true)
            SpawnTestItems();
    }

    [ContextMenu("Spawn Test Items")]
    public void SpawnTestItems()
    {
        if (!Application.isPlaying)
        {
            Debug.LogWarning("[Test Item Spawner] Play Mode에서 실행해 주세요.", this);
            return;
        }

        if (replacePreviousItems)
            ClearSpawnedItems();
        else
            ClearDestroyedReferences();

        IReadOnlyList<ItemDefinition> source = items.Count > 0
            ? items
            : DefaultItemCatalog.Items;

        for (int i = 0; i < source.Count; i++)
        {
            ItemDefinition item = source[i];
            if (item == null)
                continue;

            GameObject pickupObject = new($"TestPickup_{item.DisplayName}");
            pickupObject.transform.position = transform.position + Vector3.right * (i * spacing);
            WorldItemPickup pickup = pickupObject.AddComponent<WorldItemPickup>();
            pickup.Initialize(item, pickupDistance);
            spawnedItems.Add(pickupObject);
        }

        Debug.Log($"[Test Item Spawner] 아이템 {spawnedItems.Count}개 생성", this);
    }

    private void ClearSpawnedItems()
    {
        foreach (GameObject spawnedItem in spawnedItems)
        {
            if (spawnedItem != null)
                Destroy(spawnedItem);
        }
        spawnedItems.Clear();
    }

    private void ClearDestroyedReferences()
    {
        for (int i = spawnedItems.Count - 1; i >= 0; i--)
        {
            if (spawnedItems[i] == null)
                spawnedItems.RemoveAt(i);
        }
    }
}

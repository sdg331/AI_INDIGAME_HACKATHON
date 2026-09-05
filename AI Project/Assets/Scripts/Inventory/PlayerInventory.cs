using System;
using UnityEngine;
using UnityEngine.InputSystem;

public sealed class PlayerInventory : MonoBehaviour
{
    [Serializable]
    private sealed class SwordLoadout
    {
        public SwordDefinition sword;
        public RelicDefinition relicSlot1;
        public RelicDefinition relicSlot2;
    }

    public enum RelicSlotKind
    {
        Sword,
        Storage
    }

    public readonly struct RelicSlotAddress
    {
        public readonly RelicSlotKind Kind;
        public readonly int SwordIndex;
        public readonly int SlotIndex;

        public RelicSlotAddress(RelicSlotKind kind, int swordIndex, int slotIndex)
        {
            Kind = kind;
            SwordIndex = swordIndex;
            SlotIndex = slotIndex;
        }
    }

    [Header("Starting Inventory")]
    [SerializeField] private SwordLoadout[] startingSwords = { new(), new() };
    [SerializeField] private RelicDefinition[] startingRelics = new RelicDefinition[3];

    [Header("Sword Swap")]
    [SerializeField, Min(0f)] private float swordSwapCooldown = 1f;

    public int EquippedSwordIndex { get; private set; }
    public float SwordSwapCooldownRemaining => Mathf.Max(0f, nextSwordSwapTime - Time.time);
    public event Action InventoryChanged;
    public event Action<int> EquippedSwordChanged;

    private readonly SwordDefinition[] swords = new SwordDefinition[2];
    private readonly RelicDefinition[,] swordRelics = new RelicDefinition[2, 2];
    private readonly RelicDefinition[] storedRelics = new RelicDefinition[3];
    private PlayerAttackHitbox attackHitbox;
    private bool initialized;
    private float nextSwordSwapTime;

    public SwordDefinition EquippedSword => swords[EquippedSwordIndex];

    private void Awake()
    {
        Initialize();
    }

    public void Initialize()
    {
        if (initialized)
            return;
        initialized = true;
        LoadStartingItems();
        attackHitbox = GetComponentInChildren<PlayerAttackHitbox>(true);
        ApplyEquippedSword();
    }

    private void Update()
    {
        if (Keyboard.current?.rKey.wasPressedThisFrame == true)
            TrySwapEquippedSword();
    }

    public SwordDefinition GetSword(int index) => IsSwordIndex(index) ? swords[index] : null;

    public RelicDefinition GetSwordRelic(int swordIndex, int relicIndex)
    {
        return IsSwordIndex(swordIndex) && IsRelicIndex(relicIndex)
            ? swordRelics[swordIndex, relicIndex]
            : null;
    }

    public RelicDefinition GetStoredRelic(int index)
    {
        return index >= 0 && index < storedRelics.Length ? storedRelics[index] : null;
    }

    public RelicDefinition GetEquippedSkillRelic(int skillIndex)
    {
        return IsRelicIndex(skillIndex) ? swordRelics[EquippedSwordIndex, skillIndex] : null;
    }

    public bool TrySwapEquippedSword()
    {
        if (swords[0] == null || swords[1] == null)
        {
            Debug.Log("[Inventory] 검이 2개가 아니므로 교체할 수 없습니다.", this);
            return false;
        }

        if (Time.time < nextSwordSwapTime)
        {
            Debug.Log($"[Inventory] 검 교체 쿨타임 {SwordSwapCooldownRemaining:0.0}초", this);
            return false;
        }

        EquippedSwordIndex = 1 - EquippedSwordIndex;
        nextSwordSwapTime = Time.time + swordSwapCooldown;
        ApplyEquippedSword();
        EquippedSwordChanged?.Invoke(EquippedSwordIndex);
        InventoryChanged?.Invoke();
        Debug.Log($"[Inventory] 장착 검 교체 → {EquippedSword.DisplayName}", this);
        return true;
    }

    public bool TryAddItem(ItemDefinition item)
    {
        if (item is SwordDefinition sword)
            return TryAddSword(sword);
        if (item is RelicDefinition relic)
            return TryAddRelic(relic);
        return false;
    }

    public bool CanAddItem(ItemDefinition item)
    {
        if (item is SwordDefinition)
            return swords[0] == null || swords[1] == null;
        if (item is RelicDefinition)
            return Array.Exists(storedRelics, relic => relic == null);
        return false;
    }

    public bool TryMoveRelic(RelicSlotAddress from, RelicSlotAddress to)
    {
        RelicDefinition source = GetRelic(from);
        if (source == null || !IsValid(to))
            return false;

        RelicDefinition destination = GetRelic(to);
        SetRelic(to, source);
        SetRelic(from, destination);
        InventoryChanged?.Invoke();
        EquippedSwordChanged?.Invoke(EquippedSwordIndex);
        return true;
    }

    // 검에서 유물을 빼는 단축 동작입니다. 빈칸이 없으면 보관함 1번과 교환합니다.
    public bool TryUnequipRelic(int swordIndex, int relicIndex)
    {
        RelicSlotAddress source = new(RelicSlotKind.Sword, swordIndex, relicIndex);
        if (GetRelic(source) == null)
            return false;

        int emptyIndex = Array.FindIndex(storedRelics, relic => relic == null);
        int destinationIndex = emptyIndex >= 0 ? emptyIndex : 0;
        return TryMoveRelic(source, new RelicSlotAddress(RelicSlotKind.Storage, -1, destinationIndex));
    }

    private bool TryAddSword(SwordDefinition sword)
    {
        int index = Array.FindIndex(swords, item => item == null);
        if (index < 0)
            return false;

        swords[index] = sword;
        ApplyEquippedSword();
        InventoryChanged?.Invoke();
        return true;
    }

    private bool TryAddRelic(RelicDefinition relic)
    {
        int index = Array.FindIndex(storedRelics, item => item == null);
        if (index < 0)
            return false;

        storedRelics[index] = relic;
        InventoryChanged?.Invoke();
        return true;
    }

    private void ApplyEquippedSword()
    {
        if (attackHitbox == null)
            attackHitbox = GetComponentInChildren<PlayerAttackHitbox>(true);

        if (attackHitbox != null && EquippedSword != null) { }
            //attackHitbox.SetDamage(EquippedSword.MeleeDamage);
    }

    private void LoadStartingItems()
    {
        for (int swordIndex = 0; swordIndex < swords.Length; swordIndex++)
        {
            if (startingSwords == null || swordIndex >= startingSwords.Length || startingSwords[swordIndex] == null)
                continue;
            swords[swordIndex] = startingSwords[swordIndex].sword;
            swordRelics[swordIndex, 0] = startingSwords[swordIndex].relicSlot1;
            swordRelics[swordIndex, 1] = startingSwords[swordIndex].relicSlot2;
        }

        for (int i = 0; i < storedRelics.Length && startingRelics != null && i < startingRelics.Length; i++)
            storedRelics[i] = startingRelics[i];

        if (swords[0] == null && swords[1] == null)
            swords[0] = DefaultItemCatalog.StartingSword;
    }

    private RelicDefinition GetRelic(RelicSlotAddress address)
    {
        if (!IsValid(address))
            return null;
        return address.Kind == RelicSlotKind.Storage
            ? storedRelics[address.SlotIndex]
            : swordRelics[address.SwordIndex, address.SlotIndex];
    }

    private void SetRelic(RelicSlotAddress address, RelicDefinition relic)
    {
        if (address.Kind == RelicSlotKind.Storage)
            storedRelics[address.SlotIndex] = relic;
        else
            swordRelics[address.SwordIndex, address.SlotIndex] = relic;
    }

    private static bool IsValid(RelicSlotAddress address)
    {
        return address.Kind == RelicSlotKind.Storage
            ? address.SlotIndex >= 0 && address.SlotIndex < 3
            : IsSwordIndex(address.SwordIndex) && IsRelicIndex(address.SlotIndex);
    }

    private static bool IsSwordIndex(int index) => index >= 0 && index < 2;
    private static bool IsRelicIndex(int index) => index >= 0 && index < 2;
}

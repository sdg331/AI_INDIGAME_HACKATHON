using UnityEngine;

public abstract class ItemDefinition : ScriptableObject
{
    [SerializeField] private string displayName;
    [SerializeField, TextArea(2, 5)] private string description;
    [SerializeField] private Sprite icon;

    public string DisplayName => string.IsNullOrWhiteSpace(displayName) ? name : displayName;
    public string Description => description;
    public Sprite Icon => icon;

    internal void ConfigureRuntime(string itemName, string itemDescription)
    {
        displayName = itemName;
        description = itemDescription;
        name = itemName;
        hideFlags = HideFlags.HideAndDontSave;
    }
}

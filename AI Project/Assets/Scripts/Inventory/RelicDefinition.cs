using UnityEngine;

public enum RelicSkillType
{
    Pushback,
    GroggyAcceleration,
    SlashWave,
    ExplosiveIncapacitation
}

[CreateAssetMenu(menuName = "Knight Oath/Items/Relic", fileName = "Relic_")]
public sealed class RelicDefinition : ItemDefinition
{
    [SerializeField] private RelicSkillType skillType;
    public RelicSkillType SkillType => skillType;

    internal void ConfigureRuntime(string itemName, string itemDescription, RelicSkillType type)
    {
        base.ConfigureRuntime(itemName, itemDescription);
        skillType = type;
    }
}

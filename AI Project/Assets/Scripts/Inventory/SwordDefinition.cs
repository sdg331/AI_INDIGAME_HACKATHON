using UnityEngine;

[CreateAssetMenu(menuName = "Knight Oath/Items/Sword", fileName = "Sword_")]
public sealed class SwordDefinition : ItemDefinition
{
    [SerializeField, Min(1)] private int meleeDamage = 1;
    public int MeleeDamage => meleeDamage;

    internal void ConfigureRuntime(string itemName, string itemDescription, int damage)
    {
        base.ConfigureRuntime(itemName, itemDescription);
        meleeDamage = Mathf.Max(1, damage);
    }
}

using System.Collections.Generic;
using UnityEngine;

public static class DefaultItemCatalog
{
    private static List<ItemDefinition> items;

    public static IReadOnlyList<ItemDefinition> Items
    {
        get
        {
            if (items == null)
                Build();
            return items;
        }
    }

    public static SwordDefinition StartingSword => (SwordDefinition)Items[0];

    private static void Build()
    {
        items = new List<ItemDefinition>
        {
            CreateSword("낡은 기사의 검", "전장에서 건네받은 기본 검.", 1),
            CreateSword("전장의 장검", "조금 더 강한 근접 피해를 주는 검.", 2),
            CreateRelic("밀어내기", "주변 적을 밀어낸다. 피해 없음. 쿨타임 10초.", RelicSkillType.Pushback),
            CreateRelic("그로기 가속", "연격 10을 소모해 5초 동안 그로기 누적을 가속한다.", RelicSkillType.GroggyAcceleration),
            CreateRelic("참격 파동", "연격 5를 소모해 근접 피해와 같은 원거리 참격을 발사한다.", RelicSkillType.SlashWave),
            CreateRelic("폭발적 무력화", "최소 연격 15를 전부 소모해 화면의 적들을 그로기 상태로 만든다.", RelicSkillType.ExplosiveIncapacitation)
        };
    }

    private static SwordDefinition CreateSword(string itemName, string description, int damage)
    {
        SwordDefinition sword = ScriptableObject.CreateInstance<SwordDefinition>();
        sword.ConfigureRuntime(itemName, description, damage);
        return sword;
    }

    private static RelicDefinition CreateRelic(string itemName, string description, RelicSkillType type)
    {
        RelicDefinition relic = ScriptableObject.CreateInstance<RelicDefinition>();
        relic.ConfigureRuntime(itemName, description, type);
        return relic;
    }
}

using System.Collections.Generic;
using UnityEngine;

public sealed class EnemySpawnPoint : MonoBehaviour
{
    [Tooltip("이 위치에 생성할 수 있는 적 프리팹입니다. 여러 개면 하나를 무작위로 선택합니다.")]
    [SerializeField] private List<GameObject> enemyPrefabs = new();

    public GameObject SpawnEnemy(Transform enemyParent = null)
    {
        List<GameObject> validPrefabs = enemyPrefabs.FindAll(prefab => prefab != null);
        if (validPrefabs.Count == 0)
        {
            Debug.LogWarning($"[Stage] '{name}'에 적 프리팹이 지정되지 않았습니다.", this);
            return null;
        }

        GameObject prefab = validPrefabs[Random.Range(0, validPrefabs.Count)];
        return Instantiate(prefab, transform.position, transform.rotation, enemyParent);
    }

    private void OnDrawGizmos()
    {
        Gizmos.color = Color.red;
        Gizmos.DrawWireCube(transform.position, Vector3.one * 0.6f);
    }
}


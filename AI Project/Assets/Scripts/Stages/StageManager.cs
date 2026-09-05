using System.Collections.Generic;
using UnityEngine;

public sealed class StageManager : MonoBehaviour
{
    [Header("Stage")]
    [SerializeField] private List<GameObject> stagePrefabs = new();
    [SerializeField] private Transform stageOrigin;
    [SerializeField] private bool loadFirstStageOnStart = true;
    [SerializeField] private bool destroyPreviousStage = true;

    [Header("Player")]
    [SerializeField] private GameObject playerPrefab;
    [SerializeField] private bool reuseExistingPlayer = true;
    [SerializeField] private GameObject currentPlayer;

    [Header("Stage Rewards")]
    [Tooltip("스테이지 클리어 시 이 목록에서 서로 다른 아이템 3개를 선택합니다.")]
    [SerializeField] private List<ItemDefinition> rewardItemPool = new();
    [SerializeField] private StageRewardSelection rewardSelection;

    [Header("Runtime (Read Only)")]
    [SerializeField] private GameObject currentStage;

    private readonly HashSet<int> usedStageIndices = new();
    private readonly List<GameObject> spawnedEnemies = new();
    private StageExitPoint currentExit;
    private bool exitUnlocked;

    public int RemainingStageCount => Mathf.Max(0, stagePrefabs.Count - usedStageIndices.Count);
    public IReadOnlyList<GameObject> SpawnedEnemies => spawnedEnemies;

    private void Start()
    {
        if (rewardItemPool.Count == 0)
        {
            foreach (ItemDefinition item in DefaultItemCatalog.Items)
                rewardItemPool.Add(item);
        }

        if (rewardSelection == null)
            rewardSelection = GetComponent<StageRewardSelection>();
        if (rewardSelection == null)
            rewardSelection = gameObject.AddComponent<StageRewardSelection>();
        rewardSelection.Initialize(this);

        if (loadFirstStageOnStart)
            LoadNextStage();
    }

    private void Update()
    {
        if (!exitUnlocked && currentExit != null && AreAllEnemiesCleared())
            UnlockExit();
    }

    // 외부 시스템이나 도착 지점에서 호출하는 다음 스테이지 진입 함수입니다.
    public bool LoadNextStage()
    {
        if (!TryGetUnusedStageIndex(out int stageIndex))
        {
            Debug.Log("[Stage] 사용하지 않은 스테이지 프리팹이 더 이상 없습니다.", this);
            return false;
        }

        usedStageIndices.Add(stageIndex);
        SpawnStage(stagePrefabs[stageIndex]);
        return true;
    }

    public void ResetUsedStages()
    {
        usedStageIndices.Clear();
    }

    public bool TryUseExit()
    {
        if (rewardSelection != null && rewardSelection.HasPendingChoice)
        {
            Debug.Log("[Stage] 보상 하나를 F키로 선택해야 다음 스테이지로 이동할 수 있습니다.", this);
            return false;
        }
        return LoadNextStage();
    }

    public void OnStageRewardSelected()
    {
        LoadNextStage();
    }

    private void SpawnStage(GameObject stagePrefab)
    {
        if (stagePrefab == null)
        {
            Debug.LogError("[Stage] 비어 있는 스테이지 프리팹은 생성할 수 없습니다.", this);
            return;
        }

        if (destroyPreviousStage && currentStage != null)
            Destroy(currentStage);

        Vector3 position = stageOrigin != null ? stageOrigin.position : Vector3.zero;
        Quaternion rotation = stageOrigin != null ? stageOrigin.rotation : Quaternion.identity;
        currentStage = Instantiate(stagePrefab, position, rotation);

        spawnedEnemies.Clear();
        exitUnlocked = false;

        PlayerSpawnPoint playerSpawn = currentStage.GetComponentInChildren<PlayerSpawnPoint>(true);
        EnemySpawnPoint[] enemySpawns = currentStage.GetComponentsInChildren<EnemySpawnPoint>(true);
        currentExit = currentStage.GetComponentInChildren<StageExitPoint>(true);

        SpawnOrMovePlayer(playerSpawn);
        SpawnEnemies(enemySpawns);
        PrepareExit();

        Debug.Log($"[Stage] '{stagePrefab.name}' 생성 완료. 남은 미사용 스테이지: {RemainingStageCount}", this);
    }

    private void SpawnOrMovePlayer(PlayerSpawnPoint spawnPoint)
    {
        if (spawnPoint == null)
        {
            Debug.LogError("[Stage] PlayerSpawnPoint가 없습니다.", currentStage);
            return;
        }

        if (reuseExistingPlayer && currentPlayer != null)
        {
            currentPlayer.transform.SetParent(null);
            currentPlayer.transform.SetPositionAndRotation(spawnPoint.transform.position, spawnPoint.transform.rotation);
            currentPlayer.SetActive(true);
            return;
        }

        if (!reuseExistingPlayer && currentPlayer != null)
            Destroy(currentPlayer);

        if (playerPrefab == null)
        {
            Debug.LogError("[Stage] Player Prefab이 지정되지 않았습니다.", this);
            return;
        }

        currentPlayer = Instantiate(playerPrefab, spawnPoint.transform.position, spawnPoint.transform.rotation);
    }

    private void SpawnEnemies(EnemySpawnPoint[] spawnPoints)
    {
        foreach (EnemySpawnPoint spawnPoint in spawnPoints)
        {
            GameObject enemy = spawnPoint.SpawnEnemy(currentStage.transform);
            if (enemy != null)
                spawnedEnemies.Add(enemy);
        }
    }

    private void PrepareExit()
    {
        if (currentExit == null)
        {
            Debug.LogError("[Stage] StageExitPoint가 없습니다.", currentStage);
            return;
        }

        currentExit.Initialize(this);
        currentExit.SetUnlocked(false);

        if (spawnedEnemies.Count == 0)
            UnlockExit();
    }

    private bool AreAllEnemiesCleared()
    {
        for (int i = spawnedEnemies.Count - 1; i >= 0; i--)
        {
            GameObject enemy = spawnedEnemies[i];

            // 일반 규칙에서는 파괴된 적도 사망 처리된 것으로 본다.
            if (enemy == null)
            {
                spawnedEnemies.RemoveAt(i);
                continue;
            }

            OathSystem oathSystem = OathSystem.Instance;
            if (oathSystem != null)
            {
                if (!oathSystem.IsEnemyCleared(enemy))
                    return false;
                continue;
            }

            IOathHealthState health = FindInterface<IOathHealthState>(enemy);
            if (health == null || !health.IsDead)
                return false;
        }

        return true;
    }

    private void UnlockExit()
    {
        if (exitUnlocked || currentExit == null)
            return;

        exitUnlocked = true;
        currentExit.SetUnlocked(true);
        if (rewardSelection != null && rewardItemPool.Count > 0)
            rewardSelection.SpawnChoices(rewardItemPool, currentExit.transform.position);
        Debug.Log("[Stage] 모든 적 처리 완료. 도착 지점이 활성화되었습니다.", currentExit);
    }

    private bool TryGetUnusedStageIndex(out int result)
    {
        List<int> candidates = new();
        for (int i = 0; i < stagePrefabs.Count; i++)
        {
            if (stagePrefabs[i] != null && !usedStageIndices.Contains(i))
                candidates.Add(i);
        }

        if (candidates.Count == 0)
        {
            result = -1;
            return false;
        }

        result = candidates[Random.Range(0, candidates.Count)];
        return true;
    }

    private static T FindInterface<T>(GameObject source) where T : class
    {
        MonoBehaviour[] behaviours = source.GetComponentsInChildren<MonoBehaviour>(true);
        foreach (MonoBehaviour behaviour in behaviours)
        {
            if (behaviour is T result)
                return result;
        }

        return null;
    }
}

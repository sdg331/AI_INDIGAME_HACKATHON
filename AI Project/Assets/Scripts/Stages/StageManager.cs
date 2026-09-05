using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Events;

public sealed class StageManager : MonoBehaviour
{
    [Header("Stage")]
    [SerializeField] private List<GameObject> stagePrefabs = new();
    [SerializeField] private Transform stageOrigin;
    [SerializeField] private bool loadFirstStageOnStart = true;
    [SerializeField] private bool destroyPreviousStage = true;

    [Header("Boss Progression")]
    [Tooltip("이 수만큼 일반 스테이지를 진행한 뒤 다음 스테이지로 보스방을 불러옵니다.")]
    [SerializeField, Min(1)] private int normalStagesBeforeBoss = 3;
    [SerializeField] private GameObject bossStagePrefab;
    [SerializeField] private UnityEvent onBossBattleStarted;
    [SerializeField] private UnityEvent onGameCompleted;

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
    [SerializeField] private int loadedNormalStageCount;
    [SerializeField] private bool currentStageIsBoss;
    [SerializeField] private bool gameCompleted;

    private readonly HashSet<int> usedStageIndices = new();
    private readonly List<GameObject> spawnedEnemies = new();
    private StageExitPoint currentExit;
    private BossAI currentBoss;
    private bool exitUnlocked;
    private bool bossStageLoaded;

    public int RemainingStageCount => Mathf.Max(0, stagePrefabs.Count - usedStageIndices.Count);
    public IReadOnlyList<GameObject> SpawnedEnemies => spawnedEnemies;
    public bool CurrentStageIsBoss => currentStageIsBoss;
    public bool GameCompleted => gameCompleted;

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

        if (bossStagePrefab == null)
            Debug.LogWarning("[Stage] Boss Stage Prefab 슬롯에 보스방 프리팹을 연결해 주세요.", this);

        if (loadFirstStageOnStart)
            LoadNextStage();
    }

    private void Update()
    {
        if (gameCompleted || currentStageIsBoss)
            return;

        if (!exitUnlocked && currentExit != null && AreAllEnemiesCleared())
            UnlockExit();
    }

    // 외부 시스템이나 도착 지점에서 호출하는 다음 스테이지 진입 함수입니다.
    public bool LoadNextStage()
    {
        if (gameCompleted)
        {
            Debug.Log("[Stage] 이미 보스전을 클리어했습니다.", this);
            return false;
        }

        if (!bossStageLoaded && loadedNormalStageCount >= normalStagesBeforeBoss)
        {
            if (bossStagePrefab == null)
            {
                Debug.LogError(
                    "[Stage] 일반 스테이지를 모두 진행했지만 Boss Stage Prefab이 지정되지 않았습니다.", this);
                return false;
            }

            bossStageLoaded = true;
            SpawnStage(bossStagePrefab, true);
            onBossBattleStarted?.Invoke();
            return true;
        }

        if (bossStageLoaded)
        {
            Debug.Log("[Stage] 보스전 이후에 불러올 스테이지가 없습니다.", this);
            return false;
        }

        if (!TryGetUnusedStageIndex(out int stageIndex))
        {
            Debug.LogError(
                $"[Stage] 보스전 전까지 일반 맵 {normalStagesBeforeBoss}개가 필요하지만 " +
                "사용하지 않은 스테이지 프리팹이 부족합니다.", this);
            return false;
        }

        usedStageIndices.Add(stageIndex);
        loadedNormalStageCount++;
        SpawnStage(stagePrefabs[stageIndex], false);
        return true;
    }

    public void ResetUsedStages()
    {
        usedStageIndices.Clear();
        loadedNormalStageCount = 0;
        bossStageLoaded = false;
        currentStageIsBoss = false;
        gameCompleted = false;
        currentBoss = null;
    }

    public bool TryUseExit()
    {
        if (currentStageIsBoss)
        {
            Debug.Log("[Stage] 보스전은 바르갈을 그로기 상태로 만들어야 끝납니다.", this);
            return false;
        }

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

    public void NotifyBossDefeated(BossAI boss)
    {
        if (gameCompleted || !currentStageIsBoss)
            return;
        if (currentBoss != null && boss != currentBoss)
            return;

        gameCompleted = true;
        exitUnlocked = true;
        if (currentExit != null)
            currentExit.SetUnlocked(false);
        if (rewardSelection != null)
            rewardSelection.ClearChoices();

        Debug.Log("[Boss] 바르갈 그로기. 보스전 클리어 — 게임 승리!", boss);
        onGameCompleted?.Invoke();
    }

    private void SpawnStage(GameObject stagePrefab, bool isBossStage)
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
        currentStageIsBoss = isBossStage;
        currentBoss = null;

        PlayerSpawnPoint playerSpawn = currentStage.GetComponentInChildren<PlayerSpawnPoint>(true);
        EnemySpawnPoint[] enemySpawns = currentStage.GetComponentsInChildren<EnemySpawnPoint>(true);
        currentExit = currentStage.GetComponentInChildren<StageExitPoint>(true);

        SpawnOrMovePlayer(playerSpawn);
        SpawnEnemies(enemySpawns);
        RegisterBosses();
        PrepareExit();

        string stageKind = currentStageIsBoss
            ? "보스 스테이지"
            : $"일반 스테이지 {loadedNormalStageCount}/{normalStagesBeforeBoss}";
        Debug.Log($"[Stage] {stageKind} '{stagePrefab.name}' 생성 완료.", this);
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
        if (currentStageIsBoss)
        {
            if (currentExit != null)
            {
                currentExit.Initialize(this);
                currentExit.SetUnlocked(false);
            }

            if (currentBoss == null)
                Debug.LogError("[Boss] 보스방 프리팹 안에서 BossAI를 찾지 못했습니다.", currentStage);
            return;
        }

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

    private void RegisterBosses()
    {
        BossAI[] bosses = currentStage.GetComponentsInChildren<BossAI>(true);
        foreach (BossAI boss in bosses)
        {
            if (boss == null)
                continue;

            if (!spawnedEnemies.Contains(boss.gameObject))
                spawnedEnemies.Add(boss.gameObject);
            boss.Initialize(this, currentPlayer != null ? currentPlayer.transform : null);

            if (currentBoss == null)
                currentBoss = boss;
        }

        if (currentStageIsBoss && bosses.Length > 1)
            Debug.LogWarning("[Boss] 보스방에는 바르갈 한 명만 배치하는 것을 권장합니다.", currentStage);
        if (currentStageIsBoss &&
            (spawnedEnemies.Count > 1 ||
             currentStage.GetComponentsInChildren<MeleeEnemyAI>(true).Length > 0))
        {
            Debug.LogWarning("[Boss] 기획상 보스방에는 일반 적 없이 바르갈만 배치해야 합니다.", currentStage);
        }
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

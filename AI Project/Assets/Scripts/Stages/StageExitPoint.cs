using UnityEngine;

[RequireComponent(typeof(Collider2D))]
public sealed class StageExitPoint : MonoBehaviour
{
    [SerializeField] private bool loadNextStageOnPlayerEnter = true;

    private StageManager stageManager;

    private void Awake()
    {
        Collider2D trigger = GetComponent<Collider2D>();
        trigger.isTrigger = true;
    }

    public void Initialize(StageManager manager)
    {
        stageManager = manager;
    }

    public void SetUnlocked(bool unlocked)
    {
        gameObject.SetActive(unlocked);
    }

    private void OnTriggerEnter2D(Collider2D other)
    {
        if (!loadNextStageOnPlayerEnter || stageManager == null)
            return;

        PlayerController2D player = other.GetComponentInParent<PlayerController2D>();
        if (player != null)
            stageManager.TryUseExit();
    }

    private void OnDrawGizmos()
    {
        Gizmos.color = Color.green;
        Gizmos.DrawWireCube(transform.position, new Vector3(0.8f, 1.5f, 0f));
    }
}

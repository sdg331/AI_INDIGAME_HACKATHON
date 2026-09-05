using UnityEngine;
using UnityEngine.Tilemaps;

[RequireComponent(typeof(Camera))]
public sealed class PlayerCameraFollow2D : MonoBehaviour
{
    [Header("Target")]
    [SerializeField] private Transform playerTarget;
    [SerializeField] private Vector3 offset = new(0f, 1f, -10f);
    [SerializeField, Min(0.01f)] private float followSmoothTime = 0.25f;
    [SerializeField, Min(0f)] private float maximumFollowSpeed = 30f;

    [Header("Tilemap Bounds")]
    [Tooltip("이 태그가 지정되고 현재 활성화된 Tilemap의 경계 안으로 카메라를 제한합니다.")]
    [SerializeField] private string boundsTilemapTag = "CameraBounds";
    [SerializeField, Min(0.05f)] private float boundsRefreshInterval = 0.5f;

    private Camera targetCamera;
    private Tilemap currentBoundsTilemap;
    private Vector3 followVelocity;
    private float nextBoundsRefreshTime;

    private void Awake()
    {
        targetCamera = GetComponent<Camera>();
        TryFindPlayer();
        RefreshBounds();
    }

    private void LateUpdate()
    {
        if (playerTarget == null)
        {
            TryFindPlayer();
            if (playerTarget == null)
                return;
        }

        if (Time.unscaledTime >= nextBoundsRefreshTime || !IsUsableBounds(currentBoundsTilemap))
            RefreshBounds();

        Vector3 desiredPosition = playerTarget.position + offset;
        desiredPosition = ClampToCurrentTilemap(desiredPosition);

        Vector3 smoothedPosition = Vector3.SmoothDamp(
            transform.position,
            desiredPosition,
            ref followVelocity,
            followSmoothTime,
            maximumFollowSpeed,
            Time.deltaTime);

        // 부드러운 이동 중에도 카메라 화면이 맵 경계를 한 프레임도 넘지 않게 다시 제한한다.
        transform.position = ClampToCurrentTilemap(smoothedPosition);
    }

    public void SetTarget(Transform target, bool snapImmediately = false)
    {
        playerTarget = target;
        followVelocity = Vector3.zero;
        RefreshBounds();

        if (snapImmediately && playerTarget != null)
            transform.position = ClampToCurrentTilemap(playerTarget.position + offset);
    }

    // 스테이지를 교체한 직후 외부에서 호출해도 되고, 호출하지 않아도 주기적으로 자동 갱신됩니다.
    public void RefreshBounds()
    {
        nextBoundsRefreshTime = Time.unscaledTime + boundsRefreshInterval;
        currentBoundsTilemap = FindBestActiveBoundsTilemap();
    }

    private void TryFindPlayer()
    {
        PlayerController2D player = FindFirstObjectByType<PlayerController2D>();
        if (player != null)
            playerTarget = player.transform;
    }

    private Tilemap FindBestActiveBoundsTilemap()
    {
        Tilemap[] tilemaps = FindObjectsByType<Tilemap>(
            FindObjectsInactive.Exclude, FindObjectsSortMode.None);

        Tilemap bestContainingTilemap = null;
        float bestContainingArea = float.PositiveInfinity;
        Tilemap nearestTilemap = null;
        float nearestDistance = float.PositiveInfinity;
        Vector3 targetPosition = playerTarget != null ? playerTarget.position : transform.position;

        foreach (Tilemap tilemap in tilemaps)
        {
            if (!IsUsableBounds(tilemap) || tilemap.gameObject.tag != boundsTilemapTag)
                continue;

            Bounds bounds = GetWorldBounds(tilemap);
            Vector3 closest = bounds.ClosestPoint(targetPosition);
            float distance = (closest - targetPosition).sqrMagnitude;

            if (bounds.Contains(new Vector3(targetPosition.x, targetPosition.y, bounds.center.z)))
            {
                float area = bounds.size.x * bounds.size.y;
                if (area < bestContainingArea)
                {
                    bestContainingArea = area;
                    bestContainingTilemap = tilemap;
                }
            }

            if (distance < nearestDistance)
            {
                nearestDistance = distance;
                nearestTilemap = tilemap;
            }
        }

        return bestContainingTilemap != null ? bestContainingTilemap : nearestTilemap;
    }

    private Vector3 ClampToCurrentTilemap(Vector3 desiredPosition)
    {
        if (!IsUsableBounds(currentBoundsTilemap) || !targetCamera.orthographic)
            return desiredPosition;

        Bounds bounds = GetWorldBounds(currentBoundsTilemap);
        float halfHeight = targetCamera.orthographicSize;
        float halfWidth = halfHeight * targetCamera.aspect;

        desiredPosition.x = ClampAxis(
            desiredPosition.x, bounds.min.x + halfWidth, bounds.max.x - halfWidth);
        desiredPosition.y = ClampAxis(
            desiredPosition.y, bounds.min.y + halfHeight, bounds.max.y - halfHeight);
        return desiredPosition;
    }

    private static float ClampAxis(float value, float minimum, float maximum)
    {
        // 맵이 카메라 화면보다 작은 경우 맵의 중앙에 고정합니다.
        return minimum > maximum
            ? (minimum + maximum) * 0.5f
            : Mathf.Clamp(value, minimum, maximum);
    }

    private static Bounds GetWorldBounds(Tilemap tilemap)
    {
        Renderer tilemapRenderer = tilemap.GetComponent<Renderer>();
        if (tilemapRenderer != null)
            return tilemapRenderer.bounds;

        Bounds localBounds = tilemap.localBounds;
        Vector3 worldCenter = tilemap.transform.TransformPoint(localBounds.center);
        Vector3 worldSize = Vector3.Scale(localBounds.size, tilemap.transform.lossyScale);
        return new Bounds(worldCenter, new Vector3(
            Mathf.Abs(worldSize.x), Mathf.Abs(worldSize.y), Mathf.Abs(worldSize.z)));
    }

    private static bool IsUsableBounds(Tilemap tilemap)
    {
        return tilemap != null && tilemap.enabled && tilemap.gameObject.activeInHierarchy;
    }
}

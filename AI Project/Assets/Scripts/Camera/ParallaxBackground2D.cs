using System;
using UnityEngine;

// PlayerCameraFollow2D의 LateUpdate가 끝난 다음 배경을 이동시킵니다.
[DefaultExecutionOrder(100)]
public sealed class ParallaxBackground2D : MonoBehaviour
{
    [Serializable]
    private sealed class ParallaxLayer
    {
        public Transform layerObject;
        [Range(-1f, 1f)] public float horizontalMultiplier = 0.1f;
        [Range(-1f, 1f)] public float verticalMultiplier = 0.05f;

        [NonSerialized] public Vector3 initialPosition;
    }

    [Tooltip("숫자가 작을수록 멀리 있는 배경처럼 보입니다.")]
    [SerializeField] private ParallaxLayer[] layers =
    {
        new() { horizontalMultiplier = 0.08f, verticalMultiplier = 0.03f },
        new() { horizontalMultiplier = 0.25f, verticalMultiplier = 0.1f }
    };

    [Header("Vertical Coverage")]
    [Tooltip("카메라가 위아래로 움직일 때 배경도 같은 거리만큼 따라가 이미지가 잘리지 않게 합니다.")]
    [SerializeField] private bool followCameraVertically = true;

    private Vector3 initialCameraPosition;
    private bool initialized;

    private void OnEnable()
    {
        RefreshLayerOrigins();
    }

    private void LateUpdate()
    {
        if (!initialized)
            RefreshLayerOrigins();

        Vector3 cameraDelta = transform.position - initialCameraPosition;
        foreach (ParallaxLayer layer in layers)
        {
            if (layer == null || layer.layerObject == null)
                continue;

            Vector3 offset = new(
                cameraDelta.x * layer.horizontalMultiplier,
                cameraDelta.y * (followCameraVertically ? 1f : layer.verticalMultiplier),
                0f);
            layer.layerObject.position = layer.initialPosition + offset;
        }
    }

    // 스테이지 교체와 함께 배경 오브젝트를 바꿨다면 참조 설정 후 호출합니다.
    public void RefreshLayerOrigins()
    {
        initialCameraPosition = transform.position;

        foreach (ParallaxLayer layer in layers)
        {
            if (layer == null || layer.layerObject == null)
                continue;

            layer.initialPosition = layer.layerObject.position;

            if (layer.layerObject.IsChildOf(transform))
            {
                Debug.LogWarning(
                    $"[Parallax] '{layer.layerObject.name}'은 카메라의 자식입니다. " +
                    "패럴랙스 배경은 카메라 밖의 독립 오브젝트로 두세요.", layer.layerObject);
            }
        }

        initialized = true;
    }
}

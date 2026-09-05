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

        [Tooltip("가로로 무한히 이어 붙입니다. 스프라이트 한 장 폭만큼씩 되감아 끝이 보이지 않게 합니다.")]
        public bool loopHorizontally = true;

        [Tooltip("되감는 폭(월드 단위). 0이면 SpriteRenderer의 스프라이트 폭 × 스케일로 자동 계산합니다.")]
        [Min(0f)] public float loopWidth;

        [NonSerialized] public Vector3 initialPosition;
        [NonSerialized] public float resolvedLoopWidth;
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
            Vector3 position = layer.initialPosition + offset;

            // 타일링된 배경은 한 장 폭의 정수배만큼 옮겨도 화면이 똑같으므로,
            // 카메라에서 반 장 이상 멀어지면 되감아 끝이 드러나지 않게 합니다.
            if (layer.loopHorizontally && layer.resolvedLoopWidth > 0.001f)
            {
                float width = layer.resolvedLoopWidth;
                float delta = position.x - transform.position.x;
                float wrapped = Mathf.Repeat(delta + width * 0.5f, width) - width * 0.5f;
                position.x = transform.position.x + wrapped;
            }

            layer.layerObject.position = position;
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
            layer.resolvedLoopWidth = ResolveLoopWidth(layer);

            if (layer.layerObject.IsChildOf(transform))
            {
                Debug.LogWarning(
                    $"[Parallax] '{layer.layerObject.name}'은 카메라의 자식입니다. " +
                    "패럴랙스 배경은 카메라 밖의 독립 오브젝트로 두세요.", layer.layerObject);
            }
        }

        initialized = true;
    }

    // 되감을 폭을 정합니다. 지정값이 없으면 스프라이트 한 장의 월드 폭을 씁니다.
    private static float ResolveLoopWidth(ParallaxLayer layer)
    {
        if (layer.loopWidth > 0f)
            return layer.loopWidth;

        SpriteRenderer renderer = layer.layerObject != null
            ? layer.layerObject.GetComponent<SpriteRenderer>()
            : null;
        if (renderer == null || renderer.sprite == null)
            return 0f;

        float spriteWidth = renderer.sprite.rect.width / renderer.sprite.pixelsPerUnit;
        return spriteWidth * Mathf.Abs(layer.layerObject.lossyScale.x);
    }
}

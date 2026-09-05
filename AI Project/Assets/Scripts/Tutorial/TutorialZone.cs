using UnityEngine;

// 플레이어가 들어오면 튜토리얼의 한 단계를 시작시키는 구역입니다.
// 튜토리얼 맵 안에 BoxCollider2D(Is Trigger)와 함께 배치합니다.
[RequireComponent(typeof(BoxCollider2D))]
public sealed class TutorialZone : MonoBehaviour
{
    [Tooltip("이 구역이 시작시키는 단계 번호입니다. TutorialDirector의 steps 순서와 같습니다.")]
    [SerializeField, Min(0)] private int stepIndex;

    [Tooltip("한 번만 발동합니다.")]
    [SerializeField] private bool triggerOnce = true;

    public int StepIndex => stepIndex;

    private TutorialDirector director;
    private bool triggered;

    private void Reset()
    {
        BoxCollider2D box = GetComponent<BoxCollider2D>();
        box.isTrigger = true;
        box.size = new Vector2(3f, 6f);
    }

    private void Awake()
    {
        GetComponent<BoxCollider2D>().isTrigger = true;
    }

    public void Initialize(TutorialDirector owner)
    {
        director = owner;
        triggered = false;
    }

    private void OnTriggerEnter2D(Collider2D other)
    {
        if (triggerOnce && triggered)
            return;

        if (other.GetComponentInParent<PlayerController2D>() == null)
            return;

        if (director == null)
            director = FindFirstObjectByType<TutorialDirector>();
        if (director == null)
            return;

        triggered = true;
        director.EnterStep(stepIndex);
    }

    private void OnDrawGizmos()
    {
        BoxCollider2D box = GetComponent<BoxCollider2D>();
        if (box == null)
            return;

        Gizmos.color = new Color(0.95f, 0.78f, 0.35f, 0.25f);
        Gizmos.DrawCube((Vector2)transform.position + box.offset, box.size);
        Gizmos.color = new Color(0.95f, 0.78f, 0.35f, 0.9f);
        Gizmos.DrawWireCube((Vector2)transform.position + box.offset, box.size);
    }
}

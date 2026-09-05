using System;
using System.Collections;
using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.InputSystem;

// 튜토리얼 맵의 진행을 담당합니다.
// 플레이어가 TutorialZone에 들어오면 해당 단계의 안내 UI를 띄우고,
// 그 단계의 조작을 실제로 성공해야 다음으로 넘어갑니다.
// 조작 키는 문서가 아니라 "현재 구현된" 키를 기준으로 합니다.
//   이동 A·D / 구르기 Shift / 점프 Space / 공격 좌클릭 / 방어·패링 우클릭 / 스킬 1·2 / 검 교체 R
public sealed class TutorialDirector : MonoBehaviour
{
    public enum StepKind
    {
        Move = 0,
        Roll = 1,
        Jump = 2,
        ComboThenSkill = 3,
        Parry = 4
    }

    [Serializable]
    public sealed class TutorialStep
    {
        [Tooltip("작업용 이름입니다. 화면에는 나오지 않습니다.")]
        public string title;

        public StepKind kind = StepKind.Move;

        [Tooltip("UI 상단 줄. 키 안내입니다.")]
        public string prompt;

        [Tooltip("UI 아래 줄. 무엇을 하라는 설명입니다.")]
        [TextArea(2, 3)] public string description;

        [Tooltip("완료 후 이 문구를 잠깐 보여 줍니다. 비우면 바로 사라집니다.")]
        public string clearedMessage;
    }

    [Header("Steps")]
    [SerializeField] private List<TutorialStep> steps = new();

    [Header("Combo Step")]
    [Tooltip("연격을 이 수치까지 쌓아야 스킬 안내로 넘어갑니다. 참격 파동 소모량과 같은 값으로 두세요.")]
    [SerializeField, Min(1)] private int requiredCombo = 5;

    [Tooltip("연격 단계에서 무적·대기 상태로 만들 적입니다. 비워 두면 맵 안에서 자동으로 찾습니다.")]
    [SerializeField] private MeleeEnemyAI practiceEnemy;

    [Header("UI")]
    [SerializeField] private TutorialHUD hud;

    [Header("Completion")]
    [Tooltip("튜토리얼을 마쳤을 때 보여 줄 문구입니다. 비우면 아무것도 띄우지 않습니다.")]
    [SerializeField] private string completionMessage = "튜토리얼 완료 — 오른쪽 끝으로 나아가라";

    [Tooltip("완료 문구를 이 시간(초) 동안만 보여 주고 지웁니다.")]
    [SerializeField, Min(0f)] private float completionMessageDuration = 2.5f;

    [Header("Oath")]
    [Tooltip("튜토리얼 동안 맹세 규칙을 잠시 끕니다. (허수아비를 먼저 치는 것이 위반이 되지 않도록)")]
    [SerializeField] private bool suspendOathDuringTutorial = true;

    [Header("Events")]
    public UnityEvent onTutorialCompleted;

    public bool IsFinished { get; private set; }
    public int CurrentStepIndex { get; private set; } = -1;

    private PlayerComboCounter combo;
    private PlayerController2D player;
    private RelicSkillController skills;
    private Coroutine stepRoutine;
    private bool comboReached;
    private bool skillUsed;
    private bool parriedSuccessfully;
    private bool oathSuspended;

    private void Reset()
    {
        EnsureDefaultSteps();
    }

    private void Awake()
    {
        EnsureDefaultSteps();
        foreach (TutorialZone zone in GetComponentsInChildren<TutorialZone>(true))
            zone.Initialize(this);
    }

    private void Start()
    {
        if (hud == null)
            hud = FindFirstObjectByType<TutorialHUD>(FindObjectsInactive.Include);
        if (hud != null)
            hud.Hide();

        if (practiceEnemy == null)
            practiceEnemy = GetComponentInChildren<MeleeEnemyAI>(true);

        // 연격 단계 전까지는 허수아비가 먼저 달려들지 않게 대기시켜 둡니다.
        if (practiceEnemy != null)
        {
            practiceEnemy.Passive = true;
            practiceEnemy.DamageImmune = true;
        }

        if (suspendOathDuringTutorial && OathSystem.Instance != null)
        {
            OathSystem.Instance.EnforcementEnabled = false;
            oathSuspended = true;
        }
    }

    private void OnDestroy()
    {
        RestoreOath();
        UnbindPlayer();
    }

    public void EnterStep(int index)
    {
        if (IsFinished || index < 0 || index >= steps.Count)
            return;

        // 앞 단계를 건너뛰고 들어와도 그 단계부터 이어서 진행합니다.
        if (index <= CurrentStepIndex)
            return;

        if (stepRoutine != null)
            StopCoroutine(stepRoutine);
        CurrentStepIndex = index;
        stepRoutine = StartCoroutine(RunStep(steps[index]));
    }

    private IEnumerator RunStep(TutorialStep step)
    {
        BindPlayer();

        if (hud != null)
            hud.Show(step.prompt, step.description);

        switch (step.kind)
        {
            case StepKind.Move:
                yield return WaitForMove();
                break;
            case StepKind.Roll:
                yield return WaitForRoll();
                break;
            case StepKind.Jump:
                yield return WaitForJump();
                break;
            case StepKind.ComboThenSkill:
                yield return WaitForComboAndSkill(step);
                break;
            case StepKind.Parry:
                yield return WaitForParry();
                break;
        }

        if (hud != null && !string.IsNullOrWhiteSpace(step.clearedMessage))
        {
            hud.ShowCleared(step.clearedMessage);
            yield return new WaitForSeconds(1.4f);
        }

        if (hud != null)
            hud.Hide();

        stepRoutine = null;

        if (CurrentStepIndex >= steps.Count - 1)
            CompleteTutorial();
    }

    private IEnumerator WaitForMove()
    {
        while (true)
        {
            Keyboard keyboard = Keyboard.current;
            if (keyboard != null && (keyboard.aKey.isPressed || keyboard.dKey.isPressed ||
                                     keyboard.leftArrowKey.isPressed || keyboard.rightArrowKey.isPressed))
                yield break;
            yield return null;
        }
    }

    private IEnumerator WaitForRoll()
    {
        while (true)
        {
            // 실제로 구르기가 발동했는지(무적 상태)로 확인합니다. 키만 눌러서는 통과되지 않습니다.
            if (player != null && player.IsInvulnerable)
                yield break;
            yield return null;
        }
    }

    private IEnumerator WaitForJump()
    {
        while (true)
        {
            Keyboard keyboard = Keyboard.current;
            if (keyboard != null && keyboard.spaceKey.wasPressedThisFrame)
                yield break;
            yield return null;
        }
    }

    private IEnumerator WaitForComboAndSkill(TutorialStep step)
    {
        // 허수아비를 무적으로 두어 몇 번을 때려도 쓰러지지 않게 합니다.
        if (practiceEnemy == null)
            practiceEnemy = GetComponentInChildren<MeleeEnemyAI>(true);
        if (practiceEnemy != null)
        {
            practiceEnemy.Passive = true;
            practiceEnemy.DamageImmune = true;
        }

        comboReached = false;
        skillUsed = false;

        if (combo != null && combo.CurrentCombo >= requiredCombo)
            comboReached = true;

        while (!comboReached)
        {
            if (hud != null && combo != null)
                hud.SetProgress($"연격 {combo.CurrentCombo} / {requiredCombo}");
            yield return null;
        }

        if (hud != null)
        {
            hud.SetProgress(string.Empty);
            hud.Show("1  또는  2 — 스킬", $"연격 {requiredCombo} 달성. 검에 달린 참격 파동을 써 보자.");
        }

        while (!skillUsed)
            yield return null;
    }

    private IEnumerator WaitForParry()
    {
        // 이제 허수아비가 실제로 덤벼듭니다. 무적은 유지해 연습 중 죽지 않게 합니다.
        if (practiceEnemy == null)
            practiceEnemy = GetComponentInChildren<MeleeEnemyAI>(true);
        if (practiceEnemy != null)
        {
            practiceEnemy.Passive = false;
            practiceEnemy.DamageImmune = true;
        }

        parriedSuccessfully = false;
        while (!parriedSuccessfully)
            yield return null;
    }

    private void BindPlayer()
    {
        if (player != null)
            return;

        player = FindFirstObjectByType<PlayerController2D>();
        if (player == null)
            return;

        combo = player.GetComponent<PlayerComboCounter>();
        skills = player.GetComponent<RelicSkillController>();

        if (combo != null)
            combo.ComboChanged += OnComboChanged;
        if (skills != null)
            skills.SkillUsed += OnSkillUsed;
        player.AttackReceived += OnAttackReceived;
    }

    private void UnbindPlayer()
    {
        if (combo != null)
            combo.ComboChanged -= OnComboChanged;
        if (skills != null)
            skills.SkillUsed -= OnSkillUsed;
        if (player != null)
            player.AttackReceived -= OnAttackReceived;

        combo = null;
        skills = null;
        player = null;
    }

    private void OnComboChanged(int current, int maximum)
    {
        if (current >= requiredCombo)
            comboReached = true;
    }

    private void OnSkillUsed(int slotIndex, RelicDefinition relic)
    {
        skillUsed = true;
    }

    private void OnAttackReceived(PlayerHitResult result, GameObject attacker)
    {
        if (result == PlayerHitResult.Parried)
            parriedSuccessfully = true;
    }

    private void CompleteTutorial()
    {
        if (IsFinished)
            return;

        IsFinished = true;
        RestoreOath();

        // 튜토리얼 고블린은 끝까지 무적입니다. 연습 상대라 쓰러뜨릴 수 없습니다.
        // 대신 적을 처리하지 않아도 출구가 열리도록 스테이지 매니저에 알립니다.
        if (practiceEnemy != null)
        {
            practiceEnemy.DamageImmune = true;
            practiceEnemy.Passive = false;
        }

        StageManager stageManager = FindFirstObjectByType<StageManager>();
        if (stageManager != null)
            stageManager.ForceUnlockExit();

        // 완료 문구는 잠깐만 보여 주고 지웁니다. 계속 떠 있으면 플레이를 가립니다.
        if (hud != null)
        {
            if (isActiveAndEnabled && !string.IsNullOrWhiteSpace(completionMessage))
                StartCoroutine(ShowCompletionMessage());
            else
                hud.Hide();
        }

        Debug.Log("[튜토리얼] 완료. 맹세 규칙을 다시 적용하고 출구를 엽니다.", this);
        onTutorialCompleted?.Invoke();
    }

    private IEnumerator ShowCompletionMessage()
    {
        hud.ShowCleared(completionMessage);
        yield return new WaitForSeconds(completionMessageDuration);
        if (hud != null)
            hud.Hide();
    }

    private void RestoreOath()
    {
        if (!oathSuspended || OathSystem.Instance == null)
            return;

        OathSystem.Instance.EnforcementEnabled = true;
        oathSuspended = false;
    }

    private void EnsureDefaultSteps()
    {
        if (steps.Count > 0)
            return;

        steps = new List<TutorialStep>
        {
            new()
            {
                title = "1. 이동",
                kind = StepKind.Move,
                prompt = "A   D — 이동",
                description = "좌우로 움직여 앞으로 나아가라.",
                clearedMessage = "좋다."
            },
            new()
            {
                title = "2. 구르기",
                kind = StepKind.Roll,
                prompt = "Shift — 구르기",
                description = "구르는 동안에는 공격을 맞지 않는다.",
                clearedMessage = "구르기 습득."
            },
            new()
            {
                title = "3. 점프",
                kind = StepKind.Jump,
                prompt = "Space — 점프",
                description = "무너진 돌더미를 뛰어넘어라.",
                clearedMessage = "점프 습득."
            },
            new()
            {
                title = "4. 연격과 스킬",
                kind = StepKind.ComboThenSkill,
                prompt = "좌클릭 — 공격",
                description = "적을 연속으로 베어 연격을 쌓아라.",
                clearedMessage = "참격 파동을 익혔다."
            },
            new()
            {
                title = "5. 패링",
                kind = StepKind.Parry,
                prompt = "우클릭 — 방어 · 패링",
                description = "적이 휘두르는 순간에 맞춰 우클릭. 완벽하게 막으면 적이 무너진다.",
                clearedMessage = "패링 성공."
            }
        };
    }
}

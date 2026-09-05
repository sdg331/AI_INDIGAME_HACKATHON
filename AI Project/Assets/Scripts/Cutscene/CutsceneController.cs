using System;
using System.Collections;
using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.InputSystem;
using UnityEngine.UI;

// 게임 시작 직후 재생되는 오프닝 컷신입니다.
// 컷 6장을 순서대로 보여 주고, 클릭(또는 Space/Enter)으로 대사를 한 줄씩 넘깁니다.
// 재생 중에는 Time.timeScale = 0 으로 게임을 멈추고 플레이어 입력을 차단합니다.
public sealed class CutsceneController : MonoBehaviour
{
    public enum LineKind
    {
        Normal = 0,
        // 이 런에 부여된 맹세 문장으로 대체되는 줄입니다. (6컷 "누군가를 죽이지 말 것 / ...")
        ActiveOath = 1
    }

    [Serializable]
    public sealed class CutsceneLine
    {
        [Tooltip("화자 이름. 비워 두면 나레이션으로 처리해 이름표를 숨깁니다.")]
        public string speaker;

        [TextArea(2, 4)] public string text;

        public LineKind kind = LineKind.Normal;
    }

    [Serializable]
    public sealed class CutsceneShot
    {
        [Tooltip("작업용 이름입니다. 화면에는 나오지 않습니다.")]
        public string title;

        public Sprite image;

        public List<CutsceneLine> lines = new();
    }

    [Header("Shots")]
    [SerializeField] private List<CutsceneShot> shots = new();

    [Header("UI")]
    [SerializeField] private Canvas canvas;
    [SerializeField] private Image cutImage;
    [SerializeField] private Image fadeOverlay;
    [SerializeField] private GameObject dialoguePanel;
    [SerializeField] private GameObject speakerPanel;
    [SerializeField] private TMP_Text speakerText;
    [SerializeField] private TMP_Text bodyText;
    [SerializeField] private GameObject clickHint;

    [Header("Playback")]
    [Tooltip("게임 시작과 동시에 자동으로 재생합니다.")]
    [SerializeField] private bool playOnStart = true;

    [Tooltip("한 글자당 시간(초). 0이면 타이핑 없이 즉시 표시합니다.")]
    [SerializeField, Min(0f)] private float secondsPerCharacter = 0.045f;

    [Tooltip("타이핑 중 클릭하면 그 줄을 즉시 다 보여 줍니다.")]
    [SerializeField] private bool clickCompletesTyping = true;

    [Tooltip("컷이 바뀔 때 검은 화면으로 페이드하는 시간(초). 0이면 즉시 전환합니다.")]
    [SerializeField, Min(0f)] private float cutFadeDuration = 0.35f;

    [Tooltip("컷신 시작 직후 첫 대사가 뜨기 전까지의 여유(초).")]
    [SerializeField, Min(0f)] private float openingDelay = 0.4f;

    [Tooltip("재생 중 게임을 멈춥니다.")]
    [SerializeField] private bool pauseGameWhilePlaying = true;

    [Header("Oath Line (6컷)")]
    [SerializeField] private string cannotKillOathLine = "누군가를 죽이지 말 것";
    [SerializeField] private string retaliationOnlyOathLine = "나를 공격한 자에게만 검을 겨눌 수 있다";
    [Tooltip("맹세 시스템을 찾지 못했을 때 대신 보여 줄 문장입니다.")]
    [SerializeField] private string fallbackOathLine = "누군가를 죽이지 말 것 / 나를 공격한 자에게만 검을 겨눌 수 있다";

    [Header("Events")]
    public UnityEvent onCutsceneStarted;
    public UnityEvent onCutsceneFinished;

    public bool IsPlaying { get; private set; }

    private readonly List<Behaviour> suspendedBehaviours = new();
    private Coroutine playRoutine;
    private bool lineFullyShown;
    private float restoredTimeScale = 1f;

    private void Reset()
    {
        EnsureDefaultShots();
    }

    private void Awake()
    {
        EnsureDefaultShots();

        // 재생 전에는 화면에 아무것도 보이지 않게 해 둡니다.
        if (canvas != null)
            canvas.enabled = false;
        if (dialoguePanel != null)
            dialoguePanel.SetActive(false);
    }

    private void Start()
    {
        if (playOnStart)
            Play();
    }

    private void OnDisable()
    {
        // 재생 도중 비활성화되어도 게임이 멈춘 채 남지 않게 합니다.
        if (IsPlaying)
            Finish();
    }

    public void Play()
    {
        if (IsPlaying)
            return;

        if (shots.Count == 0)
        {
            Debug.LogWarning("[컷신] 재생할 컷이 없습니다.", this);
            return;
        }

        IsPlaying = true;
        restoredTimeScale = Time.timeScale > 0f ? Time.timeScale : 1f;

        if (canvas != null)
            canvas.enabled = true;
        if (pauseGameWhilePlaying)
            Time.timeScale = 0f;

        onCutsceneStarted?.Invoke();
        playRoutine = StartCoroutine(PlayRoutine());
    }

    // 인스펙터나 다른 스크립트에서 컷신을 즉시 끝내고 싶을 때 사용합니다.
    public void Skip()
    {
        if (!IsPlaying)
            return;

        if (playRoutine != null)
            StopCoroutine(playRoutine);
        playRoutine = null;
        Finish();
    }

    private IEnumerator PlayRoutine()
    {
        // 스테이지 매니저가 플레이어를 스폰한 뒤에 입력을 막아야 하므로 한 프레임 기다립니다.
        yield return null;
        SuspendPlayerInput();

        if (fadeOverlay != null)
        {
            SetFadeAlpha(1f);
            yield return FadeTo(0f, cutFadeDuration);
        }

        if (openingDelay > 0f)
            yield return new WaitForSecondsRealtime(openingDelay);

        for (int shotIndex = 0; shotIndex < shots.Count; shotIndex++)
        {
            CutsceneShot shot = shots[shotIndex];
            if (shot == null)
                continue;

            if (shotIndex > 0)
            {
                if (dialoguePanel != null)
                    dialoguePanel.SetActive(false);
                yield return FadeTo(1f, cutFadeDuration);
            }

            if (cutImage != null)
            {
                cutImage.sprite = shot.image;
                cutImage.enabled = shot.image != null;
            }

            if (shotIndex > 0)
                yield return FadeTo(0f, cutFadeDuration);

            for (int lineIndex = 0; lineIndex < shot.lines.Count; lineIndex++)
            {
                CutsceneLine line = shot.lines[lineIndex];
                if (line == null)
                    continue;

                yield return ShowLine(line);
            }
        }

        if (dialoguePanel != null)
            dialoguePanel.SetActive(false);
        yield return FadeTo(1f, cutFadeDuration);

        playRoutine = null;
        Finish();
    }

    private IEnumerator ShowLine(CutsceneLine line)
    {
        string body = ResolveLineText(line);

        if (dialoguePanel != null)
            dialoguePanel.SetActive(true);

        bool hasSpeaker = !string.IsNullOrWhiteSpace(line.speaker);
        if (speakerPanel != null)
            speakerPanel.SetActive(hasSpeaker);
        if (speakerText != null)
            speakerText.text = hasSpeaker ? line.speaker : string.Empty;

        if (clickHint != null)
            clickHint.SetActive(false);

        lineFullyShown = false;

        if (bodyText != null)
        {
            if (secondsPerCharacter <= 0f)
            {
                bodyText.text = body;
                lineFullyShown = true;
            }
            else
            {
                // maxVisibleCharacters 로 한 글자씩 드러내면 줄바꿈이 흔들리지 않습니다.
                bodyText.text = body;
                bodyText.ForceMeshUpdate();
                int total = bodyText.textInfo.characterCount;
                bodyText.maxVisibleCharacters = 0;

                float timer = 0f;
                int shown = 0;
                while (shown < total)
                {
                    if (clickCompletesTyping && ConsumeAdvanceInput())
                        break;

                    timer += Time.unscaledDeltaTime;
                    while (timer >= secondsPerCharacter && shown < total)
                    {
                        timer -= secondsPerCharacter;
                        shown++;
                    }

                    bodyText.maxVisibleCharacters = shown;
                    yield return null;
                }

                bodyText.maxVisibleCharacters = int.MaxValue;
                lineFullyShown = true;
            }
        }

        if (clickHint != null)
            clickHint.SetActive(true);

        // 다음 입력을 기다립니다. 타이핑을 끊은 클릭이 그대로 다음 줄로 넘기지 않도록 한 프레임 쉽니다.
        yield return null;
        while (!ConsumeAdvanceInput())
            yield return null;

        if (clickHint != null)
            clickHint.SetActive(false);
    }

    private string ResolveLineText(CutsceneLine line)
    {
        if (line.kind != LineKind.ActiveOath)
            return line.text;

        OathSystem system = OathSystem.Instance;
        OathSystem.OathDefinition active = system != null ? system.ActiveOath : null;
        if (active == null)
            return string.IsNullOrEmpty(fallbackOathLine) ? line.text : fallbackOathLine;

        switch (active.type)
        {
            case OathType.CannotKill:
                return cannotKillOathLine;
            case OathType.RetaliationOnly:
                return retaliationOnlyOathLine;
            default:
                return string.IsNullOrEmpty(active.displayName) ? fallbackOathLine : active.displayName;
        }
    }

    private static bool ConsumeAdvanceInput()
    {
        Mouse mouse = Mouse.current;
        if (mouse != null && mouse.leftButton.wasPressedThisFrame)
            return true;

        Keyboard keyboard = Keyboard.current;
        if (keyboard == null)
            return false;

        return keyboard.spaceKey.wasPressedThisFrame ||
               keyboard.enterKey.wasPressedThisFrame ||
               keyboard.numpadEnterKey.wasPressedThisFrame;
    }

    private IEnumerator FadeTo(float targetAlpha, float duration)
    {
        if (fadeOverlay == null)
            yield break;

        float start = fadeOverlay.color.a;
        if (duration <= 0f)
        {
            SetFadeAlpha(targetAlpha);
            yield break;
        }

        float elapsed = 0f;
        while (elapsed < duration)
        {
            elapsed += Time.unscaledDeltaTime;
            SetFadeAlpha(Mathf.Lerp(start, targetAlpha, Mathf.Clamp01(elapsed / duration)));
            yield return null;
        }

        SetFadeAlpha(targetAlpha);
    }

    private void SetFadeAlpha(float alpha)
    {
        if (fadeOverlay == null)
            return;

        Color color = fadeOverlay.color;
        color.a = Mathf.Clamp01(alpha);
        fadeOverlay.color = color;
        fadeOverlay.enabled = color.a > 0.001f;
    }

    private void Finish()
    {
        IsPlaying = false;

        if (canvas != null)
            canvas.enabled = false;
        if (dialoguePanel != null)
            dialoguePanel.SetActive(false);
        SetFadeAlpha(0f);

        if (pauseGameWhilePlaying)
            Time.timeScale = restoredTimeScale;

        // 마지막 클릭이 그대로 공격 입력이 되지 않도록 다음 프레임에 조작을 되돌립니다.
        if (isActiveAndEnabled)
            StartCoroutine(ResumePlayerInputNextFrame());
        else
            ResumePlayerInput();

        onCutsceneFinished?.Invoke();
    }

    private IEnumerator ResumePlayerInputNextFrame()
    {
        yield return null;
        ResumePlayerInput();
    }

    // 컷신 동안 조작 입력을 읽는 컴포넌트를 잠시 끕니다.
    private void SuspendPlayerInput()
    {
        suspendedBehaviours.Clear();
        CollectBehaviours<PlayerController2D>();
        CollectBehaviours<PlayerInventory>();
        CollectBehaviours<RelicSkillController>();

        foreach (Behaviour behaviour in suspendedBehaviours)
            behaviour.enabled = false;
    }

    private void CollectBehaviours<T>() where T : Behaviour
    {
        T[] found = FindObjectsByType<T>(FindObjectsInactive.Include, FindObjectsSortMode.None);
        foreach (T behaviour in found)
        {
            if (behaviour != null && behaviour.enabled)
                suspendedBehaviours.Add(behaviour);
        }
    }

    private void ResumePlayerInput()
    {
        foreach (Behaviour behaviour in suspendedBehaviours)
        {
            if (behaviour != null)
                behaviour.enabled = true;
        }

        suspendedBehaviours.Clear();
    }

    // 인스펙터가 비어 있어도 대사 원본 그대로 재생되도록 기본값을 채웁니다.
    private void EnsureDefaultShots()
    {
        if (shots.Count > 0)
            return;

        shots = new List<CutsceneShot>
        {
            NewShot("1컷씬",
                Narration("(달려가는 소리가 들린다)")),
            NewShot("2컷씬",
                Say("주인공", "도시가 공격 받고 있어...!")),
            NewShot("3컷씬",
                Say("주인공", "아직 검과 계약을 맺지 않았지만..."),
                Say("주인공", "그래도 한명이라도 더 사람들을 구해야해")),
            NewShot("4컷씬",
                Say("주인공", "얼마쯤 달렸을까 기억이 나지 않는다."),
                Say("주인공", "주변에 마물의 울음소리가 들리지만"),
                Say("주인공", "그래도 뛰어가야한다."),
                Say("주인공", "그게 기사니깐")),
            NewShot("5컷씬",
                Say("기사", "어..딜가는거냐"),
                Say("주인공", "기사다"),
                Say("주인공", "올곧은 눈에 기사단의 상징 같은 망토"),
                Say("주인공", "기사다"),
                Say("주인공", "저는 사람들을 구하러 갈겁니다."),
                Say("기사", "하하하"),
                Say("기사", "칼도 없는 견습기사가 마물들과 싸우겠단 말이냐"),
                Say("주인공", "그래도 싸울겁니다."),
                Say("기사", "그래 올곧은 눈이구나 너는 내칼과의 맹세를 할 자격이 있어")),
            NewShot("6컷씬",
                Say("기사", "이검을 받아라"),
                Say("기사", "맹세는 알고 있겠지?"),
                Say("주인공", "네 알고 있습니다"),
                Say("기사", "내검의 맹세는"),
                Oath("기사"),
                Say("기사", "받아라"),
                Say("기사", "어떤 고난이 와도 맹세를 깨지 마라."),
                Say("주인공", "알고 있습니다"))
        };
    }

    private static CutsceneShot NewShot(string title, params CutsceneLine[] lines)
    {
        CutsceneShot shot = new() { title = title };
        shot.lines.AddRange(lines);
        return shot;
    }

    private static CutsceneLine Say(string speaker, string text)
    {
        return new CutsceneLine { speaker = speaker, text = text, kind = LineKind.Normal };
    }

    private static CutsceneLine Narration(string text)
    {
        return new CutsceneLine { speaker = string.Empty, text = text, kind = LineKind.Normal };
    }

    private static CutsceneLine Oath(string speaker)
    {
        return new CutsceneLine
        {
            speaker = speaker,
            text = "누군가를 죽이지 말 것 / 나를 공격한 자에게만 검을 겨눌 수 있다",
            kind = LineKind.ActiveOath
        };
    }
}

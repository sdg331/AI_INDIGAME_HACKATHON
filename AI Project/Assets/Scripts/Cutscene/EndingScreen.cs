using System.Collections;
using TMPro;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

// 게임이 끝났을 때 나오는 화면입니다.
//   CLEAR : 보스(바르갈)를 그로기로 만들어 승리했을 때
//   END   : 맹세를 어겼거나 플레이어가 죽었을 때
// 씬에 하나만 두고 StageManager / OathSystem / PlayerHealth 이벤트에 연결합니다.
public sealed class EndingScreen : MonoBehaviour
{
    public enum EndingKind
    {
        Clear,
        End
    }

    [Header("UI")]
    [SerializeField] private Canvas canvas;
    [SerializeField] private Image endingImage;
    [SerializeField] private Image fadeOverlay;
    [SerializeField] private TMP_Text captionText;
    [SerializeField] private TMP_Text restartHintText;

    [Header("Sprites")]
    [SerializeField] private Sprite clearSprite;
    [SerializeField] private Sprite endSprite;

    [Header("Text")]
    [SerializeField] private string clearCaption = "맹세를 끝까지 지켰다.";
    [SerializeField] private string deathCaption = "기사는 쓰러졌다.";
    [SerializeField] private string oathBrokenCaption = "맹세를 어겼다. 검은 마법을 잃었다.";
    [SerializeField] private string restartHint = "클릭하면 처음부터 다시 시작합니다";

    [Header("Playback")]
    [SerializeField, Min(0f)] private float fadeDuration = 0.9f;
    [Tooltip("화면이 뜬 뒤 이 시간이 지나야 다시 시작 입력을 받습니다.")]
    [SerializeField, Min(0f)] private float inputLockDuration = 1.2f;
    [SerializeField] private bool allowRestart = true;

    public bool IsShowing { get; private set; }

    private bool restartArmed;
    private PlayerHealth trackedHealth;
    private float nextPlayerSearchTime;

    private void Awake()
    {
        if (canvas != null)
            canvas.enabled = false;
    }

    private void OnDestroy()
    {
        if (trackedHealth != null)
            trackedHealth.Died -= ShowDeath;
    }

    private void Update()
    {
        // 플레이어는 스테이지 매니저가 나중에 생성하므로 찾을 때까지 기다렸다가 사망을 구독합니다.
        if (trackedHealth == null && Time.unscaledTime >= nextPlayerSearchTime)
        {
            nextPlayerSearchTime = Time.unscaledTime + 0.5f;
            trackedHealth = FindFirstObjectByType<PlayerHealth>();
            if (trackedHealth != null)
                trackedHealth.Died += ShowDeath;
        }

        if (!IsShowing || !restartArmed || !allowRestart)
            return;

        Mouse mouse = Mouse.current;
        Keyboard keyboard = Keyboard.current;
        bool pressed = (mouse != null && mouse.leftButton.wasPressedThisFrame) ||
                       (keyboard != null && (keyboard.spaceKey.wasPressedThisFrame || keyboard.enterKey.wasPressedThisFrame));
        if (pressed)
            Restart();
    }

    // 보스 클리어(StageManager.onGameCompleted)에 연결합니다.
    public void ShowClear()
    {
        Show(EndingKind.Clear, clearCaption);
    }

    // 플레이어 사망(PlayerHealth.onDied)에 연결합니다.
    public void ShowDeath()
    {
        Show(EndingKind.End, deathCaption);
    }

    // 맹세 위반(OathSystem.onOathViolated)에 연결합니다.
    public void ShowOathBroken()
    {
        Show(EndingKind.End, oathBrokenCaption);
    }

    public void Show(EndingKind kind, string caption)
    {
        if (IsShowing)
            return;

        IsShowing = true;
        restartArmed = false;

        if (canvas != null)
            canvas.enabled = true;
        if (endingImage != null)
        {
            endingImage.sprite = kind == EndingKind.Clear ? clearSprite : endSprite;
            endingImage.enabled = endingImage.sprite != null;
        }
        if (captionText != null)
            captionText.text = caption;
        if (restartHintText != null)
        {
            restartHintText.text = restartHint;
            restartHintText.gameObject.SetActive(false);
        }

        Time.timeScale = 0f;
        StartCoroutine(ShowRoutine());
    }

    private IEnumerator ShowRoutine()
    {
        // 검은 화면에서 천천히 밝아집니다.
        float elapsed = 0f;
        SetFadeAlpha(1f);
        while (elapsed < fadeDuration)
        {
            elapsed += Time.unscaledDeltaTime;
            SetFadeAlpha(1f - Mathf.Clamp01(elapsed / fadeDuration));
            yield return null;
        }
        SetFadeAlpha(0f);

        if (inputLockDuration > 0f)
            yield return new WaitForSecondsRealtime(inputLockDuration);

        restartArmed = true;
        if (restartHintText != null && allowRestart)
            restartHintText.gameObject.SetActive(true);
    }

    public void Restart()
    {
        Time.timeScale = 1f;
        Scene scene = SceneManager.GetActiveScene();
        if (scene.buildIndex >= 0)
            SceneManager.LoadScene(scene.buildIndex);
        else
            SceneManager.LoadScene(scene.name);
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
}

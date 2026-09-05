using System.Collections;
using TMPro;
using UnityEngine;

// 튜토리얼 안내 문구를 화면 상단에 띄우는 패널입니다.
// 씬에 하나만 두고 TutorialDirector가 호출합니다.
public sealed class TutorialHUD : MonoBehaviour
{
    [SerializeField] private CanvasGroup panelGroup;
    [SerializeField] private TMP_Text promptText;
    [SerializeField] private TMP_Text descriptionText;
    [SerializeField] private TMP_Text progressText;
    [SerializeField, Min(0f)] private float fadeDuration = 0.2f;

    private Coroutine fadeRoutine;

    private void Awake()
    {
        if (panelGroup == null)
            panelGroup = GetComponent<CanvasGroup>();
        SetAlpha(0f);
    }

    public void Show(string prompt, string description)
    {
        gameObject.SetActive(true);

        if (promptText != null)
            promptText.text = prompt;
        if (descriptionText != null)
            descriptionText.text = description;
        if (progressText != null)
            progressText.text = string.Empty;

        FadeTo(1f);
    }

    public void ShowCleared(string message)
    {
        gameObject.SetActive(true);

        if (promptText != null)
            promptText.text = message;
        if (descriptionText != null)
            descriptionText.text = string.Empty;
        if (progressText != null)
            progressText.text = string.Empty;

        FadeTo(1f);
    }

    public void SetProgress(string text)
    {
        if (progressText != null)
            progressText.text = text;
    }

    public void Hide()
    {
        FadeTo(0f);
    }

    private void FadeTo(float target)
    {
        if (!isActiveAndEnabled)
        {
            SetAlpha(target);
            return;
        }

        if (fadeRoutine != null)
            StopCoroutine(fadeRoutine);
        fadeRoutine = StartCoroutine(FadeRoutine(target));
    }

    private IEnumerator FadeRoutine(float target)
    {
        float start = panelGroup != null ? panelGroup.alpha : 0f;
        float elapsed = 0f;

        while (fadeDuration > 0f && elapsed < fadeDuration)
        {
            elapsed += Time.unscaledDeltaTime;
            SetAlpha(Mathf.Lerp(start, target, Mathf.Clamp01(elapsed / fadeDuration)));
            yield return null;
        }

        SetAlpha(target);
        fadeRoutine = null;
    }

    private void SetAlpha(float alpha)
    {
        if (panelGroup == null)
            return;

        panelGroup.alpha = Mathf.Clamp01(alpha);
        panelGroup.blocksRaycasts = false;
        panelGroup.interactable = false;
    }
}

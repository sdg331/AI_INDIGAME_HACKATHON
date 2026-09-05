using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// mp3(오디오 클립) 파일명을 제목으로 삼아 재생하는 사운드 매니저.
///
/// 준비물: Assets/Resources/SFX 폴더 안에 재생할 mp3들을 넣어둘 것.
/// 파일명(확장자 제외)이 곧 SoundManager.Play(string) 호출 시 쓰는 "사운드 이펙트 제목"이 된다.
///
/// 사용 예 (다른 스크립트에서):
///     SoundManager.Play("Attack_Slash");
///     SoundManager.Play("Jump", 0.7f); // 볼륨 지정
///
/// 재생은 항상 카메라(Camera.main) 위치를 기준으로 한다.
/// 씬 전환 중에도 유지되는 싱글턴이며, 씬에 하나만 있으면 된다(빈 오브젝트에 붙여두면 됨).
/// </summary>
public sealed class SoundManager : MonoBehaviour
{
    private const string ResourcesFolder = "SFX"; // Assets/Resources/SFX

    [Range(0f, 1f)]
    [SerializeField] private float defaultVolume = 1f;

    private static SoundManager instance;
    private readonly Dictionary<string, AudioClip> clipsByName = new();

    private void Awake()
    {
        // 씬에 두 개 이상 존재하는 것을 방지
        if (instance != null && instance != this)
        {
            Destroy(gameObject);
            return;
        }

        instance = this;
        DontDestroyOnLoad(gameObject);

        LoadAllClips();
    }

    private void LoadAllClips()
    {
        clipsByName.Clear();

        AudioClip[] clips = Resources.LoadAll<AudioClip>(ResourcesFolder);

        foreach (AudioClip clip in clips)
        {
            if (clip == null) continue;

            if (clipsByName.ContainsKey(clip.name))
            {
                Debug.LogWarning($"[SoundManager] 이름이 중복된 오디오 클립이 있습니다: '{clip.name}'. 하나만 등록됩니다.");
                continue;
            }

            clipsByName.Add(clip.name, clip);
        }

        Debug.Log($"[SoundManager] {ResourcesFolder} 폴더에서 {clipsByName.Count}개의 사운드를 불러왔습니다.");
    }

    /// <summary>
    /// 사운드 이펙트 제목(파일명)으로 재생. 카메라 위치를 기준으로 재생된다.
    /// </summary>
    public static void Play(string soundTitle)
    {
        Play(soundTitle, -1f); // -1이면 defaultVolume 사용
    }

    /// <summary>볼륨을 직접 지정하고 싶을 때 사용.</summary>
    public static void Play(string soundTitle, float volume)
    {
        if (instance == null)
        {
            Debug.LogError("[SoundManager] 씬에 SoundManager가 존재하지 않습니다. 빈 오브젝트에 SoundManager를 붙여주세요.");
            return;
        }

        instance.PlayInternal(soundTitle, volume);
    }

    private void PlayInternal(string soundTitle, float volume)
    {
        if (!clipsByName.TryGetValue(soundTitle, out AudioClip clip))
        {
            Debug.LogWarning($"[SoundManager] '{soundTitle}' 이름의 사운드를 찾을 수 없습니다. " +
                              $"Assets/Resources/{ResourcesFolder} 폴더에 파일이 있는지, 이름 철자가 맞는지 확인하세요.");
            return;
        }

        Camera cam = Camera.main;
        if (cam == null)
        {
            Debug.LogError("[SoundManager] Camera.main을 찾을 수 없습니다. 메인 카메라에 'MainCamera' 태그가 있는지 확인하세요.");
            return;
        }

        float finalVolume = volume >= 0f ? volume : defaultVolume;
        AudioSource.PlayClipAtPoint(clip, cam.transform.position, finalVolume);
    }
}

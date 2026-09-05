using UnityEngine;

public class PlayerSoundTest : MonoBehaviour
{


    public void WalkSound1()
    {
        SoundManager.Play("footsteps#1",0.25f);
    }

    public void WalkSound2()
    {
        SoundManager.Play("footsteps#2", 0.3f);
    }



        [SerializeField] private GameObject dashEffectPrefab;
    [SerializeField] private GameObject pushEffectPrefab;


    public void SpawnAttackEffect()
    {
        GameObject effect = Instantiate(
            dashEffectPrefab,
            transform.position,
            Quaternion.identity);

        // 플레이어 방향에 맞춰 효과 반전
        Vector3 scale = effect.transform.localScale;
        if (transform.GetComponent<SpriteRenderer>().flipX)
        {
            scale.x *= -1;
        }
        effect.transform.localScale = scale;

        Destroy(effect, 0.8f);
    }


    public void SpawnPushEffect()
    {
        GameObject effect = Instantiate(
            pushEffectPrefab,
            transform.position,
            Quaternion.identity);

        // 플레이어 방향에 맞춰 효과 반전
        Vector3 scale = effect.transform.localScale;
        if (transform.GetComponent<SpriteRenderer>().flipX)
        {
            scale.x *= -1;
        }
        effect.transform.localScale = scale;

        Destroy(effect, 0.8f);
    }
}

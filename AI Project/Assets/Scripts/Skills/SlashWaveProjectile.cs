using System.Collections.Generic;
using UnityEngine;

public sealed class SlashWaveProjectile : MonoBehaviour
{
    private static Texture2D sharedTexture;
    private static Sprite sharedSprite;
    private readonly HashSet<IDamageable> hitTargets = new();

    private Rigidbody2D body;
    private int damage;
    private PlayerComboCounter combo;
    private RelicSkillController skillController;

    public void Initialize(Vector2 direction, int attackDamage, float speed, float lifetime,
        PlayerComboCounter comboCounter, RelicSkillController controller)
    {
        damage = Mathf.Max(1, attackDamage);
        combo = comboCounter;
        skillController = controller;

        CircleCollider2D hitbox = gameObject.AddComponent<CircleCollider2D>();
        hitbox.isTrigger = true;
        hitbox.radius = 0.25f;

        body = gameObject.AddComponent<Rigidbody2D>();
        body.bodyType = RigidbodyType2D.Kinematic;
        body.collisionDetectionMode = CollisionDetectionMode2D.Continuous;
        body.linearVelocity = direction.normalized * speed;

        // 프리팹에 검기 스프라이트가 이미 있으면 그것을 그대로 씁니다.
        // 없을 때만 예전처럼 흰 사각형을 만들어 대신 보여 줍니다.
        SpriteRenderer renderer = GetComponent<SpriteRenderer>();
        if (renderer == null)
        {
            renderer = gameObject.AddComponent<SpriteRenderer>();
            renderer.sprite = GetSprite();
            renderer.color = new Color(0.65f, 0.9f, 1f, 0.9f);
            renderer.sortingOrder = 50;
            transform.localScale = new Vector3(0.8f, 0.18f, 1f);
            transform.rotation = Quaternion.Euler(0f, 0f,
                Mathf.Atan2(direction.y, direction.x) * Mathf.Rad2Deg);
        }
        else
        {
            // 그려 둔 검기 시트는 세우지 않고 좌우만 뒤집습니다.
            renderer.flipX = direction.x < 0f;
        }

        Destroy(gameObject, lifetime);
    }

    private void OnTriggerEnter2D(Collider2D other)
    {
        if (other.GetComponentInParent<PlayerController2D>() != null)
            return;

        IDamageable target = FindInterface<IDamageable>(other);
        if (target == null || !hitTargets.Add(target))
            return;

        GameObject targetObject = target is MonoBehaviour behaviour
            ? behaviour.gameObject
            : other.gameObject;
        int allowedDamage = damage;
        OathSystem oathSystem = OathSystem.Instance;
        if (oathSystem != null &&
            !oathSystem.TryPreparePlayerMeleeHit(targetObject, damage, out allowedDamage))
        {
            Destroy(gameObject);
            return;
        }

        if (allowedDamage > 0)
        {
            target.TakeDamage(allowedDamage, transform.position, body.linearVelocity.normalized);
            combo?.RegisterSuccessfulHit();
            skillController?.NotifySuccessfulAttack(targetObject);
        }

        if (oathSystem != null)
            oathSystem.CompletePlayerMeleeHit(targetObject);
        Destroy(gameObject);
    }

    private static T FindInterface<T>(Collider2D collider) where T : class
    {
        foreach (MonoBehaviour behaviour in collider.GetComponentsInParent<MonoBehaviour>())
        {
            if (behaviour is T result)
                return result;
        }
        return null;
    }

    private static Sprite GetSprite()
    {
        if (sharedSprite != null)
            return sharedSprite;

        sharedTexture = new Texture2D(1, 1) { hideFlags = HideFlags.HideAndDontSave };
        sharedTexture.SetPixel(0, 0, Color.white);
        sharedTexture.Apply();
        sharedSprite = Sprite.Create(sharedTexture, new Rect(0f, 0f, 1f, 1f),
            new Vector2(0.5f, 0.5f), 1f);
        return sharedSprite;
    }
}

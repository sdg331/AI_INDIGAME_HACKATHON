using UnityEngine;

[RequireComponent(typeof(Collider2D), typeof(Rigidbody2D))]
public sealed class BossProjectile : MonoBehaviour
{
    [SerializeField, Min(0.1f)] private float lifeTime = 5f;

    private static Texture2D fallbackTexture;
    private static Sprite fallbackSprite;

    private Rigidbody2D body;
    private GameObject owner;
    private int damage = 1;
    private bool hasHit;

    public GameObject Owner => owner;

    private void Awake()
    {
        Collider2D hitbox = GetComponent<Collider2D>();
        hitbox.isTrigger = true;

        body = GetComponent<Rigidbody2D>();
        if (body == null)
            body = gameObject.AddComponent<Rigidbody2D>();
        body.bodyType = RigidbodyType2D.Kinematic;
        body.gravityScale = 0f;
        body.freezeRotation = true;
        body.collisionDetectionMode = CollisionDetectionMode2D.Continuous;
    }

    public void Launch(Vector2 launchDirection, float launchSpeed, int launchDamage,
        GameObject attackOwner)
    {
        if (body == null)
            body = GetComponent<Rigidbody2D>();

        owner = attackOwner;
        damage = Mathf.Max(1, launchDamage);
        hasHit = false;
        body.linearVelocity = launchDirection.normalized * Mathf.Max(0f, launchSpeed);
        Destroy(gameObject, lifeTime);
    }

    // 기존 프리팹 호출과의 호환용입니다.
    public void Launch(Vector2 launchDirection, float launchSpeed, int launchDamage)
    {
        Launch(launchDirection, launchSpeed, launchDamage, null);
    }

    private void OnTriggerEnter2D(Collider2D other)
    {
        if (hasHit)
            return;

        PlayerController2D player = other.GetComponentInParent<PlayerController2D>();
        if (player == null)
            return;

        hasHit = true;
        PlayerHitResult result = player.ReceiveEnemyAttack(
            damage,
            owner != null ? owner : gameObject,
            other.ClosestPoint(transform.position));
        Debug.Log($"[Boss Projectile] Player: {result}", this);
        Destroy(gameObject);
    }

    public static BossProjectile CreateRuntime(Vector2 position)
    {
        GameObject projectileObject = new("RuntimeHeartProjectile");
        projectileObject.transform.position = position;
        projectileObject.transform.localScale = new Vector3(0.35f, 0.35f, 1f);

        CircleCollider2D collider = projectileObject.AddComponent<CircleCollider2D>();
        collider.isTrigger = true;
        collider.radius = 0.5f;
        projectileObject.AddComponent<Rigidbody2D>();

        SpriteRenderer renderer = projectileObject.AddComponent<SpriteRenderer>();
        renderer.sprite = GetFallbackSprite();
        renderer.color = new Color(1f, 0.25f, 0.65f, 1f);
        renderer.sortingOrder = 60;

        return projectileObject.AddComponent<BossProjectile>();
    }

    public static void DestroyOwnedProjectiles(GameObject attackOwner)
    {
        if (attackOwner == null)
            return;

        BossProjectile[] projectiles = FindObjectsByType<BossProjectile>(FindObjectsSortMode.None);
        foreach (BossProjectile projectile in projectiles)
        {
            if (projectile != null && projectile.owner == attackOwner)
                Destroy(projectile.gameObject);
        }
    }

    private static Sprite GetFallbackSprite()
    {
        if (fallbackSprite != null)
            return fallbackSprite;

        fallbackTexture = new Texture2D(1, 1) { hideFlags = HideFlags.HideAndDontSave };
        fallbackTexture.SetPixel(0, 0, Color.white);
        fallbackTexture.Apply();
        fallbackSprite = Sprite.Create(fallbackTexture, new Rect(0f, 0f, 1f, 1f),
            new Vector2(0.5f, 0.5f), 1f);
        fallbackSprite.hideFlags = HideFlags.HideAndDontSave;
        return fallbackSprite;
    }
}

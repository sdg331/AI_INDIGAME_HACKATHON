using UnityEngine;

public sealed class PlayerSpawnPoint : MonoBehaviour
{
    private void OnDrawGizmos()
    {
        Gizmos.color = Color.cyan;
        Gizmos.DrawWireSphere(transform.position, 0.35f);
        Gizmos.DrawLine(transform.position, transform.position + Vector3.up);
    }
}


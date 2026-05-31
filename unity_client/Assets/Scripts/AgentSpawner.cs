// AgentSpawner — renders one GameObject per live agent.
// Phase 1: a labeled cube that lerps toward the agent's real Convex position.
// Phase 2 will swap the cube prefab for a rigged character model.
using System.Collections.Generic;
using UnityEngine;

[RequireComponent(typeof(ConvexWorldClient))]
public class AgentSpawner : MonoBehaviour
{
    [Header("World mapping")]
    [Tooltip("Convex tile -> Unity units. 1 = one tile per unit.")]
    public float tileScale = 1f;
    [Tooltip("How fast cubes catch up to their polled target position.")]
    public float lerpSpeed = 6f;

    [Header("Look")]
    public Color cubeColor = new Color(0.30f, 0.55f, 0.95f);
    public float cubeSize = 0.8f;
    public float labelHeight = 1.1f;

    private ConvexWorldClient _world;
    private readonly Dictionary<string, GameObject> _objs = new Dictionary<string, GameObject>();

    void Awake() { _world = GetComponent<ConvexWorldClient>(); }

    void Update()
    {
        if (_world == null || !_world.Ready) return;

        // ensure a GameObject exists for each live agent, and move it toward target
        foreach (var kv in _world.Agents)
        {
            var st = kv.Value;
            if (!_objs.TryGetValue(st.id, out var go))
            {
                go = CreateAgent(st);
                _objs[st.id] = go;
            }
            Vector3 want = ConvexToUnity(st.target);
            go.transform.position = Vector3.Lerp(go.transform.position, want, Time.deltaTime * lerpSpeed);

            if (st.facing.sqrMagnitude > 0.001f)
            {
                Vector3 fwd = new Vector3(st.facing.x, 0f, -st.facing.y);
                if (fwd.sqrMagnitude > 0.001f)
                    go.transform.rotation = Quaternion.Slerp(go.transform.rotation,
                        Quaternion.LookRotation(fwd), Time.deltaTime * lerpSpeed);
            }
        }

        // remove objects whose agent disappeared
        var stale = new List<string>();
        foreach (var kv in _objs) if (!_world.Agents.ContainsKey(kv.Key)) stale.Add(kv.Key);
        foreach (var id in stale) { Destroy(_objs[id]); _objs.Remove(id); }
    }

    Vector3 ConvexToUnity(Vector2 tile)
    {
        // Convex: origin top-left, y-down. Unity: y-up. Flip y into -z.
        return new Vector3(tile.x * tileScale, cubeSize * 0.5f, -tile.y * tileScale);
    }

    GameObject CreateAgent(AgentState st)
    {
        var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
        go.name = "Agent_" + (string.IsNullOrEmpty(st.name) ? st.id : st.name);
        go.transform.SetParent(transform, false);
        go.transform.localScale = Vector3.one * cubeSize;

        var rend = go.GetComponent<Renderer>();
        if (rend != null)
        {
            // works under Built-in or URP (Standard falls back gracefully)
            var shader = Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Standard");
            rend.material = new Material(shader) { color = cubeColor };
        }

        // floating name label
        var labelGo = new GameObject("Label");
        labelGo.transform.SetParent(go.transform, false);
        labelGo.transform.localPosition = new Vector3(0f, labelHeight, 0f);
        var tm = labelGo.AddComponent<TextMesh>();
        tm.text = string.IsNullOrEmpty(st.name) ? st.id : st.name;
        tm.characterSize = 0.12f;
        tm.fontSize = 64;
        tm.anchor = TextAnchor.LowerCenter;
        tm.alignment = TextAlignment.Center;
        tm.color = Color.white;
        labelGo.AddComponent<Billboard>();

        return go;
    }
}

/// <summary>Keeps a transform facing the main camera (for name labels).</summary>
public class Billboard : MonoBehaviour
{
    void LateUpdate()
    {
        var cam = Camera.main;
        if (cam == null) return;
        transform.rotation = cam.transform.rotation;
    }
}

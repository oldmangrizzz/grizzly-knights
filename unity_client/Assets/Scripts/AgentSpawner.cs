// AgentSpawner — instantiates a real rigged, animated 3D character per live agent
// (glTFast loads a skinned GLB at runtime; Legacy animation plays so they're alive).
using System.Collections.Generic;
using System.Threading.Tasks;
using UnityEngine;
using GLTFast;

[RequireComponent(typeof(ConvexWorldClient))]
public class AgentSpawner : MonoBehaviour
{
    [Header("World mapping")]
    public float tileScale = 1f;
    public float lerpSpeed = 5f;
    public float charScale = 1.0f;
    public float labelHeight = 2.0f;

    private ConvexWorldClient _world;
    private GltfImport _gltf;
    private bool _gltfReady;
    private readonly Dictionary<string, GameObject> _roots = new();
    private readonly HashSet<string> _pending = new();

    /// <summary>Live character roots, so the Watcher camera can target individuals.</summary>
    public IEnumerable<KeyValuePair<string, GameObject>> Roots => _roots;

    void Awake() { _world = GetComponent<ConvexWorldClient>(); }

    async void Start()
    {
        _gltf = new GltfImport();
        string url = System.IO.Path.Combine(Application.streamingAssetsPath, "chars/human.glb");
        bool ok = await _gltf.Load(url);
        _gltfReady = ok;
        Debug.Log("[Spawner] character glb loaded: " + ok + " (" + url + ")");
    }

    void Update()
    {
        if (_world == null || !_world.Ready || !_gltfReady) return;

        foreach (var kv in _world.Agents)
        {
            var st = kv.Value;
            if (!_roots.ContainsKey(st.id))
            {
                if (!_pending.Contains(st.id)) _ = SpawnAgent(st);
                continue;
            }
            var go = _roots[st.id];
            if (go == null) continue;
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

        var stale = new List<string>();
        foreach (var kv in _roots) if (!_world.Agents.ContainsKey(kv.Key)) stale.Add(kv.Key);
        foreach (var id in stale) { if (_roots[id]) Destroy(_roots[id]); _roots.Remove(id); }
    }

    async Task SpawnAgent(AgentState st)
    {
        _pending.Add(st.id);
        var root = new GameObject("Agent_" + (string.IsNullOrEmpty(st.name) ? st.id : st.name));
        root.transform.SetParent(transform, false);
        root.transform.position = ConvexToUnity(st.target);
        // slight per-character height variety so the crowd doesn't look cloned
        float h = 0.92f + (Hash(st.name ?? st.id) % 16) / 100f;
        root.transform.localScale = Vector3.one * charScale * h;

        // default import settings already use Legacy animation, so the embedded
        // clip imports as a playable Animation component.
        var inst = new GameObjectInstantiator(_gltf, root.transform);
        await _gltf.InstantiateMainSceneAsync(inst);

        // keep them alive: loop the embedded animation
        var anim = root.GetComponentInChildren<Animation>();
        if (anim)
        {
            anim.wrapMode = WrapMode.Loop;
            foreach (AnimationState s in anim) s.wrapMode = WrapMode.Loop;
            anim.Play();
        }

        // subtle per-character tint for variety (not rainbow — low saturation)
        Color tint = Color.HSVToRGB((Hash(st.name ?? st.id) % 360) / 360f, 0.22f, 1f);
        foreach (var r in root.GetComponentsInChildren<Renderer>())
            foreach (var m in r.materials)
            {
                if (m.HasProperty("_BaseColor")) m.SetColor("_BaseColor", tint);
                else if (m.HasProperty("_Color")) m.color = tint;
            }

        // floating name label
        var lab = new GameObject("Label");
        lab.transform.SetParent(root.transform, false);
        lab.transform.localPosition = new Vector3(0f, labelHeight, 0f);
        var tm = lab.AddComponent<TextMesh>();
        tm.text = string.IsNullOrEmpty(st.name) ? st.id : st.name;
        tm.characterSize = 0.1f; tm.fontSize = 72; tm.anchor = TextAnchor.LowerCenter;
        tm.alignment = TextAlignment.Center; tm.color = Color.white;
        lab.AddComponent<Billboard>();

        if (_roots.ContainsKey(st.id)) Destroy(root);     // raced; drop dup
        else _roots[st.id] = root;
        _pending.Remove(st.id);
    }

    Vector3 ConvexToUnity(Vector2 t) => new Vector3(t.x * tileScale, 0f, -t.y * tileScale);
    static int Hash(string s) { int h = 17; foreach (char c in s) h = h * 31 + c; return Mathf.Abs(h); }
}

public class Billboard : MonoBehaviour
{
    void LateUpdate() { var c = Camera.main; if (c) transform.rotation = c.transform.rotation; }
}

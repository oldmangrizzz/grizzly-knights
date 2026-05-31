// ConvexWorldClient — owns the live world state.
// Bootstraps the worldId, loads names once, then polls world:worldState ~10 Hz
// and keeps a dictionary of agents (id, name, target position, facing).
// AgentSpawner reads Agents to render them.
using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using Newtonsoft.Json.Linq;

public class AgentState
{
    public string id;          // "p:0"
    public string name;        // display name
    public string character;   // sprite/character key
    public Vector2 target;     // latest Convex position (tile coords, y-down)
    public Vector2 facing;     // dx, dy
    public bool seenThisPoll;
}

public class ConvexWorldClient : MonoBehaviour
{
    [Header("Connection")]
    [Tooltip("Local Convex backend. Matches VITE_CONVEX_URL in fanfic_town/.env.local")]
    public string convexUrl = "http://127.0.0.1:3210";

    [Header("Polling")]
    [Range(1f, 30f)] public float pollHz = 10f;
    public float heartbeatSeconds = 50f;

    [Header("Debug")]
    public bool logFirstWorldState = true;

    public string WorldId { get; private set; }
    public string EngineId { get; private set; }
    public bool Ready { get; private set; }
    public readonly Dictionary<string, AgentState> Agents = new Dictionary<string, AgentState>();

    private readonly Dictionary<string, (string name, string character)> _names =
        new Dictionary<string, (string, string)>();
    private ConvexClient _convex;
    private bool _loggedOnce;

    void Start()
    {
        _convex = new ConvexClient(convexUrl);
        StartCoroutine(Boot());
    }

    IEnumerator Boot()
    {
        // 1) worldId + engineId
        yield return _convex.Query("world:defaultWorldStatus", new { }, (val, err) =>
        {
            if (err != null) { Debug.LogError("[Convex] defaultWorldStatus: " + err); return; }
            WorldId = (string)val?["worldId"];
            EngineId = (string)val?["engineId"];
            Debug.Log($"[Convex] worldId={WorldId} engineId={EngineId}");
        });
        if (string.IsNullOrEmpty(WorldId)) { Debug.LogError("[Convex] No worldId — is `convex dev` running and a world seeded?"); yield break; }

        // 2) names + map (once)
        yield return _convex.Query("world:gameDescriptions", new { worldId = WorldId }, (val, err) =>
        {
            if (err != null) { Debug.LogError("[Convex] gameDescriptions: " + err); return; }
            var descs = val?["playerDescriptions"] as JArray;
            if (descs != null)
                foreach (var d in descs)
                    _names[(string)d["playerId"]] = ((string)d["name"], (string)d["character"]);
            Debug.Log($"[Convex] loaded {_names.Count} player descriptions");
        });

        Ready = true;
        InvokeRepeating(nameof(Heartbeat), heartbeatSeconds, heartbeatSeconds);
        StartCoroutine(PollLoop());
    }

    IEnumerator PollLoop()
    {
        var wait = new WaitForSeconds(1f / Mathf.Max(1f, pollHz));
        while (true)
        {
            yield return _convex.Query("world:worldState", new { worldId = WorldId }, OnWorldState);
            yield return wait;
        }
    }

    void OnWorldState(JToken val, string err)
    {
        if (err != null) { Debug.LogWarning("[Convex] worldState: " + err); return; }
        if (logFirstWorldState && !_loggedOnce)
        {
            _loggedOnce = true;
            Debug.Log("[Convex] FIRST worldState payload (confirm player shape here):\n" + val?.ToString());
        }

        JToken world = val?["world"];
        JToken players = world?["players"];
        if (players == null) return;

        // players may be a JSON array OR an object/map keyed by id — handle both.
        IEnumerable<JToken> playerTokens =
            players.Type == JTokenType.Array
                ? players.Children()
                : players.Children<JProperty>().Select(p => p.Value);

        foreach (var a in Agents.Values) a.seenThisPoll = false;

        foreach (var p in playerTokens)
        {
            string id = (string)(p["id"] ?? p["playerId"]);
            if (string.IsNullOrEmpty(id)) continue;
            var pos = p["position"];
            if (pos == null) continue;

            if (!Agents.TryGetValue(id, out var st))
            {
                st = new AgentState { id = id };
                _names.TryGetValue(id, out var nm);
                st.name = nm.name ?? id;
                st.character = nm.character ?? "";
                Agents[id] = st;
            }
            st.target = new Vector2((float)pos["x"], (float)pos["y"]);
            var f = p["facing"];
            if (f != null) st.facing = new Vector2((float)f["dx"], (float)f["dy"]);
            st.seenThisPoll = true;
        }

        // drop players that vanished
        var gone = Agents.Where(kv => !kv.Value.seenThisPoll).Select(kv => kv.Key).ToList();
        foreach (var g in gone) Agents.Remove(g);
    }

    void Heartbeat()
    {
        if (string.IsNullOrEmpty(WorldId)) return;
        StartCoroutine(_convex.Mutation("world:heartbeatWorld", new { worldId = WorldId },
            (_, err) => { if (err != null) Debug.LogWarning("[Convex] heartbeat: " + err); }));
    }
}

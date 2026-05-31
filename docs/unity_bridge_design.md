# Unity WebGL Client — Bridge Design

**Goal:** replace the PixiJS/React 2D renderer with a Unity 3D client, keeping the Convex backend
(the agent brains, the 27-model routing, the profiles) entirely untouched. Unity becomes a *view* over
the live Convex world.

## Architecture

```
  Convex backend (UNCHANGED)                 Unity client (NEW)
  ┌───────────────────────────┐              ┌─────────────────────────────┐
  │ engine + agents + profiles│   HTTP/JSON  │ ConvexClient   (transport)  │
  │ world:worldState  ────────┼────poll─────▶│ ConvexWorldClient (state)   │
  │ world:gameDescriptions    │              │ AgentSpawner   (render)     │
  │ world:defaultWorldStatus  │              │   → one GameObject / agent  │
  │ world:heartbeatWorld ◀────┼──mutation────│ (cubes now → models later)  │
  └───────────────────────────┘              └─────────────────────────────┘
```

The backend already exposes everything we need over Convex's **HTTP API** (`POST /api/query`,
`POST /api/mutation`), so Unity does **not** need to reverse-engineer Convex's websocket sync protocol.

## Deployment

- Convex runs **locally**: `http://127.0.0.1:3210` (`VITE_CONVEX_URL` in `fanfic_town/.env.local`).
- Convex `dev` must be running (it already is — the `:3210` workspace). The web town at `:5173` and the
  Unity client are just two different views of the same backend; they can run side by side.
- WebGL builds run in the browser on the same machine, so `127.0.0.1:3210` is reachable. (CORS / local
  auth header may need a one-line allowance — verify on first run.)

## Phase-1 contract (minimum to render the live world)

| Call | Type | Args | We use |
|---|---|---|---|
| `world:defaultWorldStatus` | query | — | `worldId`, `engineId` (bootstrap) |
| `world:gameDescriptions` | query | `{worldId}` | `playerDescriptions[]` → `playerId → name, character`; `worldMap` dims |
| `world:worldState` | query | `{worldId}` | `world.players[]` → `id`, `position{x,y}`, `facing{dx,dy}` — **polled ~10 Hz** |
| `world:heartbeatWorld` | mutation | `{worldId}` | keep world alive, every ~50 s |

**Phase-1 simplification:** we read each player's *current* `position` from `worldState` and **lerp** in
Unity between polls. We deliberately **skip** the compressed `historicalLocations` ArrayBuffer (delta/RLE/
varint) and the `pathPosition()` interpolation — that's a Phase-2 smoothness upgrade, not needed to prove
the pipeline. ~10 Hz polling + lerp looks fine for cubes.

## Coordinate transform

Convex world: **origin top-left, y-down**, units = tiles (float positions, `tileDim` px each).
Unity: y-up, origin anywhere. Map with:

```
unity.x =  convex.x * TILE_SCALE
unity.y =  0                       (ground plane; height later)
unity.z = -convex.y * TILE_SCALE   (negate y to flip the down-axis into Unity's forward)
```

`TILE_SCALE = 1` (1 tile → 1 Unity unit) is fine to start.

## Wire-shape caveat (verify on first poll)

`world.players` may serialize as a JSON **array** of player objects or as an **object/map** keyed by id.
The client parses **both** defensively and logs the first raw `worldState` payload to the Console so we can
confirm the exact field layout and adjust in minutes. (This is the one thing I can't confirm without a live
poll, so the code is built to show us the truth on run #1 rather than guess.)

## Phase plan

- **Phase 0 — contract + bridge design** ✅ (this doc; data contract mapped from the Convex source).
- **Phase 1 — proof of life:** Unity project, `ConvexClient` + `ConvexWorldClient` + `AgentSpawner`; a
  labeled cube per agent moving at real Convex positions. Ugly on purpose. *(Scripts written; needs Unity
  Editor to run — see `unity_client/README.md`.)*
- **Phase 2 — make it real:** swap cubes for rigged GLTF character models, environment, camera controller,
  click-an-agent → fetch `messages:listMessages` / `world:previousConversation` and show profile + chat,
  proper `pathPosition` interpolation, lighting.
- **Phase 3 — polish:** animation state machine, materials, ElevenLabs voice playback per agent, UI/HUD.

## Honesty note

The C# is written to standard Unity APIs (UnityWebRequest + Newtonsoft JSON; WebGL-safe — coroutines, no
threads), but it has **not been compiled in a Unity Editor** (none on this machine). Expect small first-run
fixups (field names from the wire-shape check above, a CORS allowance). That's the first thing we do
together once Unity is installed.

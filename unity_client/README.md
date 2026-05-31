# Unity client — Phase 1 (proof of life)

A Unity 3D view over the **live Convex world**. Phase 1 renders one labeled **cube per agent**, moving at
its real Convex position. Ugly on purpose — it proves Unity is talking to the actual brain before we add
3D character models (Phase 2). See `../docs/unity_bridge_design.md` for the architecture.

> **Status:** the C# is written to standard Unity APIs but has **not been compiled in an editor yet**
> (there's no Unity on the build machine). Expect a couple of small first-run fixups — that's the first
> thing we do together. Nothing here can hurt your backend; it only *reads* the world (+ a keep-alive
> heartbeat).

## What you need running first

1. The fanfic_town backend, i.e. `convex dev` (your `:3210` workspace) — already running.
2. A seeded world (the town you see at `localhost:5173`). Unity reads that same world.

## One-time setup (~10 min)

1. **Install Unity Hub** → https://unity.com/download . In Hub, install **Unity 2022.3 LTS** (or Unity 6),
   and in the install options **check the “WebGL Build Support” module** (needed later; fine to add now).
2. **Create the project:** Unity Hub → *New project* → **3D (URP)** template → name it `GrizzlyTown` →
   create. (Built-in render pipeline also works; the cube shader falls back automatically.)
3. **Drop in this code:** quit Unity for a second. In Finder, copy:
   - this folder’s `Assets/Scripts/` → into your new project’s `Assets/` folder.
   - open your project’s `Packages/manifest.json` and make sure it has the line
     `"com.unity.nuget.newtonsoft-json": "3.2.1",` (copy from this folder’s `Packages/manifest.json` if not).
   Reopen the project; Unity will import Newtonsoft and compile the scripts.
4. **Wire the scene:**
   - In the Hierarchy, right-click → *Create Empty*, name it `World`.
   - With `World` selected, in the Inspector click *Add Component* → add **ConvexWorldClient**.
   - Click *Add Component* again → add **AgentSpawner**. (It auto-pairs with ConvexWorldClient.)
   - On **ConvexWorldClient**, confirm **Convex Url = `http://127.0.0.1:3210`**.
   - Optional: select the *Main Camera*, set Position ≈ `(25, 30, -25)` and Rotation ≈ `(55, -45, 0)` so it
     looks down at the map (tweak once cubes appear).
5. **Press ▶ Play.** Watch the **Console** (Window → General → Console). You’ll see:
   - `worldId=…`, `loaded N player descriptions`
   - a one-time dump labeled **“FIRST worldState payload”** — *send me that dump.* It confirms the exact
     field names on the wire, and I’ll fix any mismatch in minutes.
   - cubes with name labels should appear and start drifting to where the agents are.

## If nothing appears

- **Console errors about `worldId` null** → the backend isn’t reachable or no world is seeded. Make sure
  `:5173` shows the live town first.
- **HTTP/CORS error** → the local Convex backend may need to allow the editor/WebGL origin; paste the error
  and I’ll give you the one-line fix.
- **Cubes spawn but don’t move** → agents may be idle; nudge the sim, or send me the FIRST-payload dump so I
  confirm the `position` field path.

## Files

- `Assets/Scripts/ConvexClient.cs` — Convex HTTP query/mutation transport (WebGL-safe).
- `Assets/Scripts/ConvexWorldClient.cs` — bootstrap + names + ~10 Hz `worldState` poll → agent table.
- `Assets/Scripts/AgentSpawner.cs` — one labeled cube per agent, lerped to real positions (+ Billboard).

## Next (Phase 2)

Swap the cube in `AgentSpawner.CreateAgent()` for a rigged GLTF model, add an orbit camera, and make a
click on an agent fetch `messages:listMessages` / `world:previousConversation` to show its profile + chat.

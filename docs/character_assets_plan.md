# 3D Character Assets — Sourcing Plan (VR endgame)

Goal: ~38 distinct, diverse characters that hold up **close, in VR** (the Uatu-mode endgame — first-person,
standing next to them), riggable/animatable in Unity, retexturable per character. Facts below verified via
web search, May 2026.

## Recommended stack (free to start, decide realism after you can see it)

| Layer | Pick | Cost | Why |
|---|---|---|---|
| **Base humanoid meshes** (the ~30 humans) | **Synty Sidekick** (Unity-native modular character creator) | **Free starter pack**; theme packs ~$200; or sub | One tool → endless distinct, diverse characters (skin/age/sex/body/face blendshapes), retexturable, perpetual license, **excellent VR performance up close** because the style is deliberately stylized. |
| **Animation** | **Mixamo** (Adobe) | **Free** | Confirmed free; rigged-character + huge animation library; retargets onto any Unity **Humanoid** rig (incl. Synty). Supplement with Quaternius Universal Animation Library (CC0) if wanted. |
| **The ~8 non-human / special characters** | **Sketchfab (CC0)** + **Synty POLYGON** monster/sci-fi packs; bespoke where needed | Free–low | Character generators can't make a rock-man or cosmic giant; these are hand-sourced/commissioned. Filter Sketchfab to **CC0** to avoid attribution that must follow the model to VR users. |

**Realistic alternative (if you decide you want photoreal humans):** **Reallusion CC4** ($299 perpetual) —
best parametric realistic humans, VR-grade topology, free one-click Unity "Auto Setup," clean game/VR
license; animate via Mixamo. Caveat: photoreal humans next to our comic-book creatures (Thing, Beast, Uatu)
risks the uncanny — a cohesive **stylized** world fits this specific cast better. **MetaHuman** is now legally
usable in Unity (June 2025 change, free under $1M/yr) but has **no one-click Unity pipeline** (Maya/Houdini
export per character) — impractical for 38; reserve for at most one hero face if ever.

**Do NOT use as backbone:** Ready Player Me (locked to its avatar style, weak on non-humans) or VRoid (anime
only).

## The decision that gates everything: ONE art direction

Stylized vs realistic must be **committed**, not mixed — mismatched styles read badly standing next to each
other in VR. My recommendation: **start on the free Synty Sidekick + Mixamo pipeline**, get a character
standing in front of you, and make the realism call then — with your eyes, having spent nothing.

## Per-character asset mapping

**A. Standard humanoid base** (Sidekick/CC4 base + per-character skin tone, hair, outfit, eyes; a few have a
small special accessory noted). ~30 characters:

| Character | Notes for the base config |
|---|---|
| reed_richards | grey temple streaks |
| tony_stark | goatee |
| steve_rogers | blond, broad |
| bucky_barnes | long dark hair |
| sam_wilson | Black, short fade + beard |
| clint_barton | dirty-blond |
| frank_castle | dark military cut |
| scott_lang | brown, everyman |
| matt_murdock | red-tinted round glasses (accessory) |
| danny_rand | blond, long-ish |
| peter_parker | young, slight build |
| johnny_storm | blond, young, cocky |
| erik_lehnsherr | older Black man, silver beard |
| charles_xavier | older Black man, bald, goatee |
| luke_cage | large Black man, shaved head |
| remy_lebeau | auburn; **red-on-black eyes** (eye shader) |
| scott_summers | brown; **ruby visor** (accessory) |
| bruce_banner | greying curls, wire glasses |
| sue_storm | blonde |
| carol_danvers | dirty-blonde, athletic |
| natasha_romanoff | auburn-red |
| mary_jane_watson | red, wavy |
| felicia_hardy | platinum white |
| jessica_jones | dark, unkempt |
| kate_bishop | dark, practical cut |
| wanda_maximoff | dark auburn |
| jean_grey | long red |
| rogue | brown with **white front streak** (hair) |
| ororo_munroe | Black woman, **flowing white hair** (hair) |
| kamala_khan | Pakistani-American teen, **loose headscarf** (accessory) |

**B. Standard base + heavy texture/accessory pass** (humanoid mesh, but defining feature is skin/props):

| Character | Treatment |
|---|---|
| logan | standard base + mutton-chops + (retractable) claw props |
| wade_wilson | standard base + fully-scarred skin texture |

**C. Bespoke / non-human** (will NOT come from a humanoid generator — Sketchfab CC0 / Synty monster packs /
commission; rig via Mixamo to a Humanoid skeleton where possible):

| Character | Asset need |
|---|---|
| ben_grimm (The Thing) | rocky orange creature mesh |
| hank_mccoy (Beast) | blue furred leonine humanoid + fur shader |
| kurt_wagner (Nightcrawler) | humanoid base + indigo skin shader, pointed ears, prehensile tail |
| victor_doom | humanoid base + steel faceplate, armor, hooded cloak |
| thor_odinson | large humanoid + armor, cape, long hair/beard |
| **uatu_the_watcher** | large bald cosmic being, oversized cranium, toga — **also the player's future VR avatar** (build with first-person in mind) |

## Build order (matches the Unity phases)

1. **Phase 2a — pipeline proof:** one Synty Sidekick character + a Mixamo idle/walk, retargeted, replacing
   the Phase-1 cube in `AgentSpawner.CreateAgent()`. Prove mesh + animation + movement on the live data.
2. **Phase 2b — the 30 humans:** author each standard config from the table above (deterministic per
   character so they're reproducible).
3. **Phase 2c — the specials:** source/commission the 6 bespoke + 2 texture-heavy characters.
4. **VR-readiness:** keep the rig/camera abstraction clean so the Uatu first-person XR rig drops in later;
   asset fidelity bar = "reads right standing next to it," not "reads right from above."

## Flags (verify at purchase/commit time)
- Synty Sidekick exact current pack lineup/prices beyond the ~$199.99 ref + free starter.
- Ready Player Me has signaled future paid tiers (not our backbone anyway).
- CC5 was announced in 2025 — if going Reallusion, check CC4 vs CC5 before buying.
- Sketchfab CC-BY attribution must travel to VR end users — prefer CC0 for distributed builds.

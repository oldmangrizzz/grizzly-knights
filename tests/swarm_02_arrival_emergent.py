"""
SWARM-02 — arrivals are emergent (BringInCharacter only), never pre-spawned.

Build a SceneSpec with the cheesecake premise: Felicia + Wade present at
open, NO arrives[] listed at the engine level. The premise mentions Peter
hard enough that the cast may decide to call him in. Run the scene.

Assert: every character beyond {felicia, wade} in the final present_cast
arrived via a BringInCharacter chronicle entry. They never appear without
the tool. They are NEVER pre-spawned.
"""
from __future__ import annotations
import asyncio, sys, time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from engine.agency_engine import SceneSpec, run_scene, build_model


SPEC = SceneSpec(
    episode_number=9201,
    episode_title="Swarm Probe — Emergent Arrival",
    act=1, scene_number=1,
    characters=["felicia_hardy", "wade_wilson"],
    location="Cheesecake Factory, midtown — corner booth by the window",
    time_window="Tuesday, 7:48 PM",
    situation=(
        "Felicia is on her second margarita. Wade has shifted to straight "
        "tequila. The avocado eggrolls between them are cold. They have "
        "been talking around Peter Parker for forty minutes — Peter has "
        "been wound tighter than usual; Felicia has been thinking about "
        "calling him; Wade has opinions. Picking up cold."
    ),
    previous_recap="Cold open.",
    arrives=[],
    departs=[],
    pressure_hint=(
        "Either Felicia or Wade pulls Peter into this booth via "
        "BringInCharacter, or they commit to leaving him out — TakeAction "
        "with a consequence commits whichever way it lands."
    ),
    max_turns=20,
)


def main() -> int:
    t0 = time.time()
    print("[swarm-02] running scene …")
    model = build_model("gpt-4o")
    script = asyncio.run(run_scene(SPEC, model))
    dt = time.time() - t0

    final_present = getattr(script, "_gk_final_present_cast", []) or []
    chronicle = getattr(script, "_gk_chronicle", []) or []
    bring_ins = [e for e in chronicle if e.get("kind") == "bring_in"]
    bring_in_keys = {e.get("key") for e in bring_ins}

    print(f"  initial cast: {SPEC.characters}")
    print(f"  final present: {final_present}")
    print(f"  bring_in events: {[(e.get('actor'), e.get('key')) for e in bring_ins]}")
    print(f"  elapsed: {dt:.1f}s")

    failures: list[str] = []
    extras = set(final_present) - set(SPEC.characters)
    for x in extras:
        if x not in bring_in_keys:
            failures.append(f"character {x!r} appeared without a BringInCharacter event")

    # Either there are arrivals via tool, or no arrivals at all — both
    # acceptable. What's NOT acceptable: an arrival without a tool call.
    if not extras:
        print("  NOTE: no emergent arrivals (cast kept the booth two-handed). "
              "That's allowed under the contract — arrivals are emergent, not required.")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(f"  ✗ {f}")
        print("SWARM-02: FAIL")
        return 1
    print("\nSWARM-02: PASS — no character appeared without a BringInCharacter call.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
PRESSURE-12 — summon-pending carries across scenes; next scene's `present`
              MUST include the un-acted summoned subject.

LIVE Copilot call. Fabricate an EpisodeArc whose summon_pending dict
binds an open pressure to subject peter_parker (scene-1 closed with
Felicia having texted Peter but Peter never on-stage). Call
plan_next_scene_arc. Assert the returned SwarmSceneSpec is not None and
present includes "peter_parker".
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from engine.agency_engine import Pressure
from engine.uatu import EpisodeArc, plan_next_scene_arc


def main() -> int:
    failures: list[str] = []

    p = Pressure(
        name="peter_decision",
        what_it_demands=("Peter Parker is summoned by name AND takes an "
                         "on-stage turn, or is named-and-refused on-stage."),
        subject_character_ids=["peter_parker"],
        resolution_modes=["BringInCharacter(peter_parker)",
                          "characters refuse Peter by name on-stage"],
        evidence_of_progress=["peter_parker", "peter", "call peter"],
    )

    arc = EpisodeArc(
        title="The Tuesday Pivot (summon-pending carryover)",
        logline="Felicia and Wade texted Peter; he has not walked in.",
        arc=("Felicia and Wade plot a scheme around Peter Parker's rising "
             "breaking point. Felicia has just summoned him by text."),
        opening_situation="(scene-1 close)",
        setting="Cheesecake Factory booth",
        time="Tuesday, 2:00 PM",
        present=["felicia_hardy", "wade_wilson"],
        forcing_pressures=[p],
        tone_floor="Marvel Knights",
    )
    # Engine state: scene 1 closed with Peter summoned but never on-stage.
    arc.summon_pending = {"peter_decision": "peter_parker"}

    prior_chronicle = [
        {"turn": 0, "actor": "felicia_hardy", "kind": "bring_in",
         "key": "peter_parker",
         "how": "Felicia texted Peter 'You miss me yet? Come find out.'"},
        {"turn": 5, "actor": "wade_wilson", "kind": "action",
         "action": "lean back, smirk",
         "consequence": "He waits for the door."},
    ]
    prior_present = ["felicia_hardy", "wade_wilson"]

    print(f"  arc.summon_pending = {arc.summon_pending}")
    print(f"  open_pressures = {[x.name for x in arc.open_pressures()]}")
    print(f"  calling plan_next_scene_arc(scenes_run=1) [LIVE] …")

    spec = plan_next_scene_arc(
        arc, prior_chronicle, prior_present, model_name="gpt-4o",
        episode_so_far="", scenes_run=1,
    )

    if spec is None:
        failures.append("plan_next_scene_arc returned None — summon-pending "
                        "carryover REQUIRED a follow-on scene")
    else:
        print(f"  returned SceneSpec(present={spec.present}, "
              f"setting={spec.setting!r}, situation={spec.situation[:120]!r})")
        if "peter_parker" not in spec.present:
            failures.append(f"present={spec.present} does NOT include peter_parker — "
                            "summon-pending subject was dropped")
        else:
            print("  PASS: peter_parker carried into next scene's present cast")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("  ✗", f)
        print("PRESSURE-12: FAIL")
        return 1
    print("\nPRESSURE-12: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

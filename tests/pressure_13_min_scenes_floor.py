"""
PRESSURE-13 — minimum-scenes floor as a CODED gate.

LIVE Copilot call. Fabricate an EpisodeArc whose only pressure resolves
cleanly in scene 1 via bring_in + on-stage subject action (summon
landed). Call plan_next_scene_arc with scenes_run=1 — it MUST return a
follow-on SceneSpec (consequences scene), NOT None. Then simulate
scene 2 having completed and call plan_next_scene_arc with scenes_run=2
— it MUST return None (episode-end).
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
        what_it_demands="Peter Parker is summoned by name AND acts on stage.",
        subject_character_ids=["peter_parker"],
        resolution_modes=["BringInCharacter(peter_parker)"],
        evidence_of_progress=["peter_parker", "peter"],
        resolved=True,
        resolved_by="scene 1 (bring_in_plus_action)",
    )

    arc = EpisodeArc(
        title="The Tuesday Pivot (min-scenes floor)",
        logline="Peter walked in. Now what happens.",
        arc=("Felicia and Wade scheme. Peter walked in mid-scene. The "
             "consequences land in the next scene."),
        opening_situation="(scene-1 close)",
        setting="Cheesecake Factory booth",
        time="Tuesday, 2:30 PM",
        present=["felicia_hardy", "wade_wilson"],
        forcing_pressures=[p],
        tone_floor="Marvel Knights",
    )
    arc.summon_landed = {"peter_decision": "peter_parker"}

    prior_chronicle = [
        {"turn": 0, "actor": "felicia_hardy", "kind": "bring_in",
         "key": "peter_parker", "how": "Felicia texted him."},
        {"turn": 4, "actor": "peter_parker", "kind": "action",
         "action": "walk in, eyes hard",
         "consequence": "He drops into the booth. No greeting."},
    ]
    prior_present = ["felicia_hardy", "wade_wilson", "peter_parker"]

    print(f"  scenes_run=1, open={[x.name for x in arc.open_pressures()]}, "
          f"summon_landed={arc.summon_landed}")
    print(f"  calling plan_next_scene_arc(scenes_run=1) [LIVE] …")

    spec = plan_next_scene_arc(
        arc, prior_chronicle, prior_present, model_name="gpt-4o",
        episode_so_far="", scenes_run=1,
    )
    if spec is None:
        failures.append("plan_next_scene_arc returned None at scenes_run=1 — "
                        "min-scenes floor was NOT enforced; episode closed "
                        "after one scene despite summon-landed")
    else:
        print(f"  returned consequences-scene present={spec.present} "
              f"setting={spec.setting!r}")
        if "peter_parker" not in spec.present:
            failures.append(f"consequences scene present={spec.present} "
                            "does NOT include peter_parker (summon-landed "
                            "subject must carry into the consequences scene)")
        else:
            print("  PASS A: floor forced a consequences scene with peter_parker on stage")

    # Now simulate scene 2 completed — everything still resolved, but
    # scenes_run is now 2 (floor satisfied). plan_next_scene_arc must
    # return None.
    print(f"\n  calling plan_next_scene_arc(scenes_run=2) — floor satisfied …")
    spec2 = plan_next_scene_arc(
        arc, prior_chronicle, prior_present, model_name="gpt-4o",
        episode_so_far="", scenes_run=2,
    )
    if spec2 is not None:
        failures.append(f"plan_next_scene_arc returned a SceneSpec at scenes_run=2 "
                        f"despite all pressures resolved AND floor satisfied: "
                        f"present={spec2.present}")
    else:
        print("  PASS B: at scenes_run=2, planner returned None (episode-end)")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("  ✗", f)
        print("PRESSURE-13: FAIL")
        return 1
    print("\nPRESSURE-13: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

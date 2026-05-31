"""
PRESSURE-03 — episode ends after all pressures resolve and the scene floor is met.

Build a single-pressure arc, simulate a scene-2 chronicle that RESOLVES it
(explicit resolves_pressure), then call plan_next_scene_arc with
scenes_run=2. It must return None — Uatu declares the arc closed, not pad
with quip scenes after the coded minimum-scenes floor is satisfied.
"""
from __future__ import annotations
import sys, time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from engine.agency_engine import Pressure, evaluate_pressures
from engine.uatu import EpisodeArc, plan_next_scene_arc


def main() -> int:
    failures: list[str] = []

    p = Pressure(
        name="peter_decision",
        what_it_demands="Peter Parker is summoned, refused on-stage by name, or chosen-against.",
        subject_character_ids=["peter_parker"],
        resolution_modes=["BringInCharacter(peter_parker)",
                          "characters refuse to act and the refusal is named on-stage"],
        evidence_of_progress=[
            "peter_parker", "call peter", "we are not calling him",
            "leave peter out", "i'm calling him",
        ],
    )
    arc = EpisodeArc(
        title="Test Arc",
        logline="Felicia and Wade have to decide about Peter tonight.",
        arc="One decision, one Tuesday, one absent center.",
        opening_situation="Booth. Two drinks in. Peter has not been mentioned yet.",
        setting="Cheesecake Factory, midtown Manhattan",
        time="Tuesday, 9:47 PM",
        present=["felicia_hardy", "wade_wilson"],
        forcing_pressures=[p],
        tone_floor="Knights / MAX / Netflix-era. Profanity uncensored.",
        pressure_hint="They are about to say his name out loud.",
    )

    # Simulate a scene-2 chronicle that RESOLVES the pressure by explicit
    # on-stage refusal that substring-matches an evidence pattern.
    resolved_chronicle = [
        {"kind": "action", "actor": "felicia_hardy",
         "action": "set the margarita down",
         "consequence": "She names it: 'We are not calling Peter tonight. "
                        "Period.' Wade nods, slow. The decision lands.",
         "resolves_pressure": "peter_decision",
         "tags": ["lines_crossed"]},
        {"kind": "change_setting", "actor": "felicia_hardy",
         "location": "parking garage",
         "transition": "they walk out for a smoke after the decision"},
    ]
    moved, names = evaluate_pressures(resolved_chronicle, [p])
    assert moved and "peter_decision" in names, \
        f"setup broke: synthetic chronicle did not move pressure: {names}"
    # Mark the pressure resolved on the arc — mirrors what the cook driver does
    p.resolved = True
    p.resolved_by = "scene 1 (synthetic)"

    print("[pressure-03] plan_next_scene_arc with ALL pressures resolved and scenes_run=2 …")
    t0 = time.time()
    next_spec = plan_next_scene_arc(
        arc, resolved_chronicle, ["felicia_hardy", "wade_wilson"],
        scenes_run=2,
    )
    dt = time.time() - t0
    print(f"  returned: {next_spec!r}  (took {dt:.1f}s)")

    if next_spec is not None:
        failures.append(
            f"plan_next_scene_arc returned a scene instead of None when arc "
            f"resolved and floor satisfied: setting={next_spec.setting!r} "
            f"present={next_spec.present}"
        )
    else:
        print("  PASS: arc closed after scenes_run=2; no padding scene returned.")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("  ✗", f)
        print("PRESSURE-03: FAIL")
        return 1
    print("\nPRESSURE-03: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
PRESSURE-04 — Uatu intervenes on stall.

LIVE: simulate one stalled scene (chronicle full of quip-only actions, no
progress on the pressure). Call stall_intervention_beat — assert Uatu
returns a non-empty single-beat narration.

Then build a next SceneSpec with stall_avoidance_note=that beat, and
source-inspect that _director_instructions surfaces that note as the
UATU INTERVENTION cue. Also confirm run_scene seeds the beat into the
director's opening message.
"""
from __future__ import annotations
import sys, time, inspect
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from engine.agency_engine import (
    Pressure, SceneSpec, _director_instructions, run_scene,
)
from engine.uatu import EpisodeArc, stall_intervention_beat


def main() -> int:
    failures: list[str] = []

    p = Pressure(
        name="peter_decision",
        what_it_demands="Peter Parker is summoned, refused on-stage by name, or chosen-against.",
        resolution_modes=["BringInCharacter(peter_parker)",
                          "characters refuse to act and the refusal is named on-stage"],
        evidence_of_progress=[
            "peter_parker", "call peter", "we are not calling him",
            "leave peter out", "i'm calling him",
        ],
    )
    arc = EpisodeArc(
        title="Stall Probe", logline="Two friends quip past a decision.",
        arc="They will not say his name. Until they do.",
        opening_situation="Booth. Drinks. Peter unmentioned.",
        setting="Cheesecake Factory, midtown Manhattan",
        time="Tuesday, 9:47 PM",
        present=["felicia_hardy", "wade_wilson"],
        forcing_pressures=[p],
        tone_floor="Knights / MAX.",
    )

    # Stalled chronicle: only banter, no progress.
    stalled_chronicle = [
        {"kind": "action", "actor": "felicia_hardy",
         "action": "swirl margarita",
         "consequence": "She watches the salt rim, deflecting."},
        {"kind": "action", "actor": "wade_wilson",
         "action": "do bit about disco morse code",
         "consequence": "He performs. She laughs. Neither names anything."},
        {"kind": "action", "actor": "felicia_hardy",
         "action": "order a third round",
         "consequence": "They keep drinking. The subject has not been said."},
    ]

    print("[pressure-04] stall_intervention_beat(...) …")
    t0 = time.time()
    try:
        beat = stall_intervention_beat(arc, [p], stalled_chronicle)
    except Exception as e:
        print(f"  FAIL — stall_intervention_beat raised {type(e).__name__}: {e}")
        return 1
    dt = time.time() - t0
    print(f"  Uatu beat ({dt:.1f}s): {beat!r}")
    if not beat or not beat.strip():
        failures.append("Uatu returned an empty stall intervention beat")
    if len(beat) > 400:
        failures.append(f"Uatu beat too long ({len(beat)} chars); Watcher cadence requires spare.")

    # Build next SceneSpec carrying the beat
    spec = SceneSpec(
        episode_number=1, episode_title="t", act=1, scene_number=2,
        characters=["felicia_hardy", "wade_wilson"],
        location="Cheesecake Factory booth (continuation)",
        time_window="Tuesday, 10:14 PM",
        situation="Continuation — they have not said his name.",
        previous_recap="They've been deflecting all scene 1.",
        active_pressures=[p],
        stall_avoidance_note=beat,
        max_turns=20,
    )
    dirinstr = _director_instructions(spec, ["FELICIA", "WADE"])
    if "UATU INTERVENTION" not in dirinstr:
        failures.append("director instructions missing UATU INTERVENTION block when stall_avoidance_note set")
    elif beat.strip() not in dirinstr:
        failures.append("director instructions do not contain the intervention beat verbatim")
    else:
        print("  PASS: director instructions surface the UATU INTERVENTION cue verbatim")

    # run_scene source surfaces the stall_avoidance_note in seed
    src = inspect.getsource(run_scene)
    if "stall_avoidance_note" not in src:
        failures.append("run_scene source does not reference stall_avoidance_note")
    if "UATU INTERVENTION" not in src:
        failures.append("run_scene source does not seed the UATU INTERVENTION block into the director")
    if not any(f.startswith("run_scene") for f in failures):
        print("  PASS: run_scene seeds the intervention beat into the director's opening cue")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("  ✗", f)
        print("PRESSURE-04: FAIL")
        return 1
    print("\nPRESSURE-04: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

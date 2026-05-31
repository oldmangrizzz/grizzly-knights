"""
SWARM-07 — scene closes ONLY on pressure progress.

Two probes, both offline (no live model needed):

  A) Build a scene_events list with NO progress on the named pressure.
     evaluate_pressures returns (False, []). The run_scene gate would
     reject [SCENE_END].

  B) Build a scene_events list whose TakeAction.consequence substring-
     matches the pressure's evidence_of_progress. evaluate_pressures
     returns (True, [name]). The gate honors [SCENE_END].

  C) Build an event with explicit resolves_pressure=name. Same → True.

  D) Confirm run_scene source uses evaluate_pressures + has_progress.
"""
from __future__ import annotations
import sys, inspect
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from engine.agency_engine import (
    Pressure, is_pressure_progress, evaluate_pressures, run_scene,
)


def main() -> int:
    failures: list[str] = []

    p = Pressure(
        name="peter_decision",
        what_it_demands="Peter Parker is summoned, refused on-stage by name, or chosen against by Felicia or Wade.",
        subject_character_ids=["peter_parker"],
        resolution_modes=["BringInCharacter(peter_parker)",
                          "explicit refusal named on-stage",
                          "the refusal lands and the cost is acknowledged"],
        evidence_of_progress=[
            "peter_parker", "call peter", "text peter", "calling peter",
            "we are not calling him", "leave peter out",
            "i'm not bringing him into this", "fuck it, i'm calling him",
            "we will not call him",
        ],
    )

    # ── A: flat events (no progress) ─────────────────────────────────────
    flat = [
        {"kind": "action", "actor": "wade_wilson",
         "action": "sip tequila", "consequence": ""},
        {"kind": "address", "actor": "felicia_hardy", "key": "wade_wilson"},
        {"kind": "action", "actor": "felicia_hardy",
         "action": "swirl the margarita",
         "consequence": "She's stalling and they both know it."},
    ]
    moved, names = evaluate_pressures(flat, [p])
    if moved:
        failures.append(f"flat events wrongly registered progress: {names}")
    else:
        print("  PASS A: flat events → no pressure progress")

    # ── B: substring-match consequence ──────────────────────────────────
    rich = [
        {"kind": "action", "actor": "wade_wilson",
         "action": "set the glass down hard",
         "consequence": "He says it flat: 'We are not calling Peter. Period.'",
         "tags": ["lines_crossed"]},
    ]
    moved, names = evaluate_pressures(rich, [p])
    if not moved or "peter_decision" not in names:
        failures.append(f"substring-match did not register progress: {names}")
    else:
        print("  PASS B: substring-match → progress on peter_decision")

    # ── B2: bring_in named figure + subject action → progress ───────────
    bring = [
        {"turn": 0, "kind": "bring_in", "actor": "felicia_hardy",
         "key": "peter_parker", "how": "She texts him; he is on his way."},
        {"turn": 1, "kind": "action", "actor": "peter_parker",
         "action": "walk in", "consequence": "Peter takes the booth."},
    ]
    moved, names = evaluate_pressures(bring, [p])
    if not moved:
        failures.append(f"bring_in+action of peter_parker did not register progress")
    else:
        print("  PASS B2: bring_in(peter_parker)+action → progress")

    # ── C: explicit resolves_pressure claim ─────────────────────────────
    explicit = [{
        "kind": "action", "actor": "felicia_hardy",
        "action": "look across the booth", "consequence": "I'm done deciding.",
        "resolves_pressure": "peter_decision",
    }]
    if not is_pressure_progress(explicit[0], p):
        failures.append("explicit resolves_pressure not honored")
    else:
        print("  PASS C: explicit resolves_pressure honored")

    # ── D: source check on run_scene ────────────────────────────────────
    src = inspect.getsource(run_scene)
    if "evaluate_pressures" not in src:
        failures.append("run_scene source does not call evaluate_pressures")
    if "has_progress" not in src:
        failures.append("run_scene source missing has_progress variable")
    if "spec.active_pressures" not in src:
        failures.append("run_scene source missing spec.active_pressures branch")
    if "scene_ended and has_progress" not in src:
        failures.append("run_scene missing (scene_ended AND has_progress) honor branch")
    if "REJECTED" not in src or "NOTHING HAS HAPPENED" not in src:
        failures.append("run_scene missing REJECTED branch for non-progress close")
    if "_gk_stalled" not in src:
        failures.append("run_scene does not set _gk_stalled marker on forced-close-without-progress")
    else:
        print("  PASS D: run_scene wired to pressure-progress gate + stalled marker")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(f"  ✗ {f}")
        print("SWARM-07: FAIL")
        return 1
    print("\nSWARM-07: PASS — pressure-progress gate enforced.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

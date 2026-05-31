"""
PRESSURE-02 — scene closes ONLY on pressure progress.

Offline. Probes evaluate_pressures + source-inspects run_scene to confirm
the pressure-progress gate is wired and the stalled marker exists.

  A) Scene events with NO progress on the named pressure -> evaluate
     returns (False, []) and run_scene would mark _gk_stalled=True if
     forced-closed.
  B) Scene events whose TakeAction consequence substring-matches one of
     the pressure's evidence_of_progress patterns -> evaluate returns
     (True, [name]) and the close gate would honor [SCENE_END].
  C) Source check: run_scene has the rejection branch + max_turns force-
     close branch + stalled marker assignment.
"""
from __future__ import annotations
import sys, inspect
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from engine.agency_engine import (
    Pressure, evaluate_pressures, is_pressure_progress, run_scene, SceneSpec,
)


def main() -> int:
    failures: list[str] = []

    p = Pressure(
        name="peter_decision",
        what_it_demands=("Peter Parker is summoned via BringInCharacter, "
                         "refused by name on-stage, or chosen-against by "
                         "Felicia or Wade."),
        subject_character_ids=["peter_parker"],
        resolution_modes=["BringInCharacter(peter_parker)",
                          "characters refuse to act and the refusal is named on-stage"],
        evidence_of_progress=[
            "peter_parker", "call peter", "calling peter",
            "we are not calling him", "we're not calling him",
            "leave peter out", "i'm calling him",
        ],
    )

    # (A) flat events -> no progress
    flat = [
        {"kind": "action", "actor": "wade_wilson",
         "action": "sip tequila", "consequence": ""},
        {"kind": "action", "actor": "felicia_hardy",
         "action": "drum nails on glass",
         "consequence": "She's deflecting and they both know."},
    ]
    moved, names = evaluate_pressures(flat, [p])
    if moved:
        failures.append(f"A: flat events wrongly registered progress: {names}")
    else:
        print("  PASS A: flat events -> no progress (scene would not close)")

    # (B) substring-match in consequence
    rich = [
        {"kind": "action", "actor": "wade_wilson",
         "action": "set the glass down",
         "consequence": "He says it flat: 'We are not calling Peter.'"},
    ]
    moved, names = evaluate_pressures(rich, [p])
    if not moved or "peter_decision" not in names:
        failures.append(f"B: substring-match missed pressure: {names}")
    else:
        print("  PASS B: substring-match -> progress (scene would close clean)")

    # (B2) bring_in of the named figure + subject action
    bring = [
        {"turn": 0, "kind": "bring_in", "actor": "felicia_hardy",
         "key": "peter_parker", "how": "She texts him."},
        {"turn": 1, "kind": "action", "actor": "peter_parker",
         "action": "walk in", "consequence": "Peter takes the booth."},
    ]
    moved, names = evaluate_pressures(bring, [p])
    if not moved:
        failures.append("B2: bring_in(peter_parker)+action missed progress")
    else:
        print("  PASS B2: bring_in(peter_parker)+action -> progress")

    # (C) source-inspect run_scene
    src = inspect.getsource(run_scene)
    for needle in ("evaluate_pressures", "active_pressures",
                   "has_progress", "REJECTED",
                   "NOTHING HAS HAPPENED",
                   "forced_close", "_gk_stalled", "spec.max_turns"):
        if needle not in src:
            failures.append(f"C: run_scene source missing {needle!r}")
    if not any(f.startswith("C:") for f in failures):
        print("  PASS C: run_scene wired to pressure-progress gate + stalled marker")

    # (D) SceneSpec has active_pressures and max_turns + stall_avoidance_note
    fields = [f for f in SceneSpec.__dataclass_fields__]
    for needle in ("active_pressures", "max_turns", "stall_avoidance_note"):
        if needle not in fields:
            failures.append(f"D: SceneSpec missing field {needle!r}")
    if not any(f.startswith("D:") for f in failures):
        print("  PASS D: SceneSpec carries active_pressures + max_turns + stall_avoidance_note")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("  ✗", f)
        print("PRESSURE-02: FAIL")
        return 1
    print("\nPRESSURE-02: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

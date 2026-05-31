"""
PRESSURE-08 — explicit on-stage named refusal resolves the pressure.

Offline. Build a peter_parker-subject pressure. Fabricate a TakeAction
with action="says flatly" and consequence="we are not calling Peter
tonight". Assert is_named_refusal returns True for subject_spoken_name
"Peter", and that evaluate_pressures resolves the pressure.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from engine.agency_engine import (
    Pressure, evaluate_pressures, is_pressure_progress, is_named_refusal,
    load_spoken_name,
)


def main() -> int:
    failures: list[str] = []

    sn = load_spoken_name("peter_parker")
    print(f"  peter_parker spoken_name = {sn!r}")
    if sn.lower() != "peter":
        failures.append(f"expected spoken_name 'Peter', got {sn!r}")

    p = Pressure(
        name="peter_decision",
        what_it_demands="Peter Parker is summoned, refused by name, or chosen-against.",
        subject_character_ids=["peter_parker"],
        # Note: evidence_of_progress does NOT contain a 'not call peter'
        # pattern — resolution must come via the is_named_refusal path,
        # not via stale substring match.
        evidence_of_progress=["peter_parker", "peter", "call peter"],
        resolution_modes=[
            "BringInCharacter(peter_parker)",
            "characters refuse Peter by name on-stage",
        ],
    )

    refusal_entry = {
        "kind": "action", "actor": "felicia_hardy",
        "action": "says flatly",
        "consequence": "we are not calling Peter tonight",
    }

    if not is_named_refusal(refusal_entry, sn):
        failures.append("is_named_refusal returned False for "
                        "'we are not calling Peter tonight'")
    else:
        print("  PASS A: is_named_refusal('we are not calling Peter tonight', "
              "'Peter') -> True")

    if not is_pressure_progress(refusal_entry, p):
        failures.append("is_pressure_progress returned False for "
                        "an on-stage named refusal — pressure left OPEN")
    moved, names = evaluate_pressures([refusal_entry], [p])
    if not moved or "peter_decision" not in names:
        failures.append(f"evaluate_pressures did not resolve: moved={moved} names={names}")
    else:
        print("  PASS B: named refusal resolves the pressure via "
              "is_pressure_progress + evaluate_pressures")

    # Control: subject NOT named in refusal → not a resolution
    other_refusal = {
        "kind": "action", "actor": "wade_wilson",
        "action": "shrug",
        "consequence": "we are not calling Johnny tonight",
    }
    if is_named_refusal(other_refusal, sn):
        failures.append("is_named_refusal wrongly fired on a refusal that "
                        "named a different character (Johnny, not Peter)")
    else:
        print("  PASS CONTROL: refusal that doesn't name Peter is NOT "
              "is_named_refusal for Peter")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("  ✗", f)
        print("PRESSURE-08: FAIL")
        return 1
    print("\nPRESSURE-08: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

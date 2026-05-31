"""
PRESSURE-10 — summon without subject action is SUMMON-PENDING, not progress.

Offline. Fabricate a scene chronicle with ONLY a BringInCharacter(target=
peter_parker) entry and no peter_parker action turns. Assert:
  • is_pressure_progress(bring_in_entry, p) returns False
  • evaluate_pressures_with_pending returns (False, [], {"x":"peter_parker"}, {})

This is the V3.1 disease fix: a bring_in alone (Felicia texts Peter) MUST
NOT flip the pressure to resolved. Peter must MOVE on stage first.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from engine.agency_engine import (
    Pressure, is_pressure_progress, evaluate_pressures,
    evaluate_pressures_with_pending,
)


def main() -> int:
    failures: list[str] = []

    p = Pressure(
        name="peter_decision",
        what_it_demands="Peter Parker is summoned AND acts, OR is named-and-refused.",
        subject_character_ids=["peter_parker"],
        resolution_modes=["BringInCharacter(peter_parker)",
                          "characters refuse Peter by name on-stage"],
        evidence_of_progress=["peter_parker", "peter", "call peter"],
    )

    bring_in_only = [
        {"turn": 0, "actor": "felicia_hardy", "kind": "bring_in",
         "key": "peter_parker",
         "how": "Felicia texts him 'You miss me yet? Come find out.'"},
    ]

    prog = is_pressure_progress(bring_in_only[0], p)
    print(f"  is_pressure_progress(bring_in_only) = {prog}")
    if prog:
        failures.append("is_pressure_progress returned True for a bring_in-only "
                        "entry — V3.1 disease present")
    else:
        print("  PASS A: bring_in alone does NOT register as progress on the entry-level check")

    moved, names = evaluate_pressures(bring_in_only, [p])
    print(f"  evaluate_pressures = ({moved}, {names})")
    if moved or names:
        failures.append(f"evaluate_pressures wrongly reported progress: moved={moved} names={names}")
    else:
        print("  PASS B: evaluate_pressures correctly returned (False, [])")

    any_moved, moved2, pending, kinds = evaluate_pressures_with_pending(
        bring_in_only, [p], subject_speakers=set(),
    )
    print(f"  evaluate_pressures_with_pending = "
          f"({any_moved}, {moved2}, pending={pending}, kinds={kinds})")
    if any_moved or moved2:
        failures.append(f"with_pending wrongly moved: {moved2}")
    if pending.get("peter_decision") != "peter_parker":
        failures.append(f"summon_pending not set correctly: {pending}")
    else:
        print("  PASS C: summon_pending = {'peter_decision': 'peter_parker'}")

    # Also confirm subject_speakers={} (no peter dialogue) leaves it pending
    any_moved2, _, pending2, _ = evaluate_pressures_with_pending(
        bring_in_only, [p], subject_speakers={"felicia_hardy", "wade_wilson"},
    )
    if any_moved2 or pending2.get("peter_decision") != "peter_parker":
        failures.append("subject_speakers={felicia,wade} should NOT flip Peter to resolved")
    else:
        print("  PASS D: other speakers do not count as Peter acting")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("  ✗", f)
        print("PRESSURE-10: FAIL")
        return 1
    print("\nPRESSURE-10: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
PRESSURE-07 — proxy progress (bringing in someone OTHER than the subject)
does NOT resolve the pressure.

Offline. Fabricate a chronicle with BringInCharacter(mary_jane_watson) +
AddressCharacter(mary_jane_watson). Assert is_pressure_progress returns
False for a peter_parker-subject pressure and the pressure stays OPEN.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from engine.agency_engine import Pressure, evaluate_pressures, is_pressure_progress


def main() -> int:
    failures: list[str] = []

    p = Pressure(
        name="peter_decision",
        what_it_demands="Peter Parker is summoned, refused by name, or chosen-against on-stage.",
        subject_character_ids=["peter_parker"],
        resolution_modes=[
            "BringInCharacter(peter_parker)",
            "characters refuse Peter by name on-stage",
        ],
        evidence_of_progress=[
            "peter_parker", "peter", "call peter",
            "we are not calling peter", "leave peter out",
            # Stale "MJ" evidence patterns from the V1/V2 era — these
            # should NEVER cause a resolution because the subject is
            # peter_parker, not mary_jane_watson.
            "mary_jane_watson", "text mj", "call mj",
        ],
    )

    proxy_chronicle = [
        {"kind": "bring_in", "actor": "wade_wilson",
         "key": "mary_jane_watson",
         "how": "Wade fires off a dramatic text. She'll know what to do."},
        {"kind": "address", "actor": "felicia_hardy",
         "key": "mary_jane_watson"},
        {"kind": "action", "actor": "wade_wilson",
         "action": "lean back grinning",
         "consequence": "She's already on her way. He calls it a win."},
    ]

    for i, e in enumerate(proxy_chronicle):
        prog = is_pressure_progress(e, p)
        print(f"  entry[{i}] kind={e.get('kind')!r:14}  "
              f"key/who={e.get('key', e.get('who', ''))!r:22}  "
              f"is_pressure_progress={prog}")
        if prog:
            failures.append(
                f"entry[{i}] (kind={e.get('kind')}) wrongly resolved a "
                f"peter_parker-subject pressure via an mary_jane_watson event"
            )

    moved, names = evaluate_pressures(proxy_chronicle, [p])
    if moved or names:
        failures.append(
            f"evaluate_pressures wrongly reported progress: moved={moved} names={names}"
        )
    else:
        print(f"  PASS: evaluate_pressures correctly returned (False, []) — "
              f"pressure remains OPEN despite MJ bring_in + address")

    # Control: an actual Peter bring_in + Peter on-stage action DOES resolve.
    # (V3.2 §1: bring_in alone is necessary-but-not-sufficient; the subject
    # must take a turn before the pressure flips to resolved. Pre-V3.2 this
    # fixture was just the bring_in entry — updated to include the action.)
    legit = [
        {"turn": 0, "actor": "felicia_hardy", "kind": "bring_in",
         "key": "peter_parker", "how": "She calls. He picks up."},
        {"turn": 1, "actor": "peter_parker", "kind": "action",
         "action": "walk in",
         "consequence": "Peter drops his keys on the table. He looks at Felicia."},
    ]
    moved2, names2 = evaluate_pressures(legit, [p])
    if not moved2 or "peter_decision" not in names2:
        failures.append(f"control: peter_parker bring_in+action failed to move pressure: {names2}")
    else:
        print("  PASS CONTROL: bring_in(peter_parker)+action resolves "
              "(subject acted on stage)")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("  ✗", f)
        print("PRESSURE-07: FAIL")
        return 1
    print("\nPRESSURE-07: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

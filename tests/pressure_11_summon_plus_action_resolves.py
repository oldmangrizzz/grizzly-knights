"""
PRESSURE-11 — summon + subsequent on-stage action resolves the pressure.

Offline. Fabricate BringInCharacter(peter_parker) followed by
TakeAction(actor=peter_parker, ...). Assert:
  • evaluate_pressures_with_pending returns
        (True, ["peter_decision"], {}, {"peter_decision": "bring_in_plus_action"})
  • summon_pending is empty.

Also: confirm the subject-speakers path works — bring_in alone + peter
in subject_speakers (he spoke a line) ALSO resolves.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from engine.agency_engine import (
    Pressure, evaluate_pressures_with_pending,
    subject_has_acted_after_bring_in,
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

    # (A) bring_in + chronicled action by subject
    chronicle = [
        {"turn": 0, "actor": "felicia_hardy", "kind": "bring_in",
         "key": "peter_parker", "how": "Felicia texts him."},
        {"turn": 1, "actor": "peter_parker", "kind": "action",
         "action": "walks in, jaw tight",
         "consequence": "He drops into the booth across from Felicia."},
    ]
    if not subject_has_acted_after_bring_in(chronicle, "peter_parker", 0):
        failures.append("subject_has_acted_after_bring_in returned False for "
                        "a chronicle with peter_parker TakeAction after the bring_in")
    else:
        print("  PASS A0: subject_has_acted_after_bring_in detects TakeAction")

    any_moved, moved, pending, kinds = evaluate_pressures_with_pending(
        chronicle, [p], subject_speakers=set(),
    )
    print(f"  evaluate_pressures_with_pending = "
          f"({any_moved}, {moved}, pending={pending}, kinds={kinds})")
    if not any_moved or "peter_decision" not in moved:
        failures.append(f"A: bring_in+action did NOT resolve: moved={moved}")
    if pending:
        failures.append(f"A: summon_pending should be empty when resolved: {pending}")
    if kinds.get("peter_decision") != "bring_in_plus_action":
        failures.append(f"A: resolution_kinds wrong: {kinds}")
    if not failures:
        print("  PASS A: bring_in + on-stage TakeAction resolves the pressure")

    # (B) bring_in + subject spoke a dialogue line (no chronicle entry)
    chronicle_b = [
        {"turn": 0, "actor": "felicia_hardy", "kind": "bring_in",
         "key": "peter_parker", "how": "Felicia texts him."},
    ]
    any_moved_b, moved_b, pending_b, kinds_b = evaluate_pressures_with_pending(
        chronicle_b, [p], subject_speakers={"peter_parker"},
    )
    print(f"  (B) speakers-only path = ({any_moved_b}, {moved_b}, "
          f"pending={pending_b}, kinds={kinds_b})")
    if not any_moved_b or "peter_decision" not in moved_b:
        failures.append("B: bring_in + subject-speakers={peter} should resolve")
    if pending_b:
        failures.append(f"B: summon_pending should be empty: {pending_b}")
    if kinds_b.get("peter_decision") != "bring_in_plus_action":
        failures.append(f"B: resolution_kinds wrong: {kinds_b}")
    if not [f for f in failures if f.startswith("B:")]:
        print("  PASS B: bring_in + dialogue-line subject_speakers resolves")

    # (C) bring_in + AddressCharacter by subject also counts as action
    chronicle_c = [
        {"turn": 0, "actor": "wade_wilson", "kind": "bring_in",
         "key": "peter_parker", "how": "calls his cell"},
        {"turn": 1, "actor": "peter_parker", "kind": "address",
         "key": "felicia_hardy"},
    ]
    any_c, moved_c, pending_c, kinds_c = evaluate_pressures_with_pending(
        chronicle_c, [p], subject_speakers=set(),
    )
    if not any_c or "peter_decision" not in moved_c:
        failures.append(f"C: bring_in+address did NOT resolve: {moved_c}")
    if kinds_c.get("peter_decision") != "bring_in_plus_action":
        failures.append(f"C: kinds wrong: {kinds_c}")
    if not [f for f in failures if f.startswith("C:")]:
        print("  PASS C: bring_in + AddressCharacter by subject resolves")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("  ✗", f)
        print("PRESSURE-11: FAIL")
        return 1
    print("\nPRESSURE-11: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

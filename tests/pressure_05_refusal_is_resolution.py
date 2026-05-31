"""
PRESSURE-05 — explicit on-stage refusal resolves the pressure.

Offline. Build a Pressure with refusal-mode evidence_of_progress
patterns. Build a chronicle entry where a character TakeActions a
consequence that names the refusal verbatim. evaluate_pressures must
return (True, [name]). Also: an entry with resolves_pressure=name is
honored even with no substring match.
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
        what_it_demands=("Peter Parker is summoned OR explicitly refused "
                         "by name on-stage by Felicia or Wade."),
        resolution_modes=[
            "BringInCharacter(peter_parker)",
            "characters refuse to act and the refusal is named on-stage",
        ],
        evidence_of_progress=[
            "peter_parker", "call peter",
            "we are not calling him", "we're not calling him",
            "leave peter out", "not tonight",
            "i refuse", "we will not call him",
        ],
    )

    # (A) refusal in TakeAction consequence
    refusal = [{
        "kind": "action", "actor": "felicia_hardy",
        "action": "set the glass down hard",
        "consequence": "She says it flat: 'We are not calling him tonight. Not Peter. Not after last month.'",
        "tags": ["lines_crossed"],
    }]
    moved, names = evaluate_pressures(refusal, [p])
    if not moved or "peter_decision" not in names:
        failures.append(f"A: explicit on-stage refusal did not resolve pressure: {names}")
    else:
        print("  PASS A: 'we are not calling him' refusal resolves the pressure")

    # (B) different refusal phrasing
    refusal2 = [{
        "kind": "action", "actor": "wade_wilson",
        "action": "shake head once",
        "consequence": "'Leave Peter out of this one. I mean it.'",
    }]
    moved, names = evaluate_pressures(refusal2, [p])
    if not moved:
        failures.append("B: 'leave peter out' refusal did not resolve pressure")
    else:
        print("  PASS B: 'leave peter out' refusal resolves the pressure")

    # (C) explicit resolves_pressure tag, no substring match in evidence
    explicit = {
        "kind": "action", "actor": "felicia_hardy",
        "action": "look across the booth",
        "consequence": "I'm done deciding. It's a no.",
        "resolves_pressure": "peter_decision",
    }
    if not is_pressure_progress(explicit, p):
        failures.append("C: explicit resolves_pressure claim was not honored")
    else:
        print("  PASS C: explicit resolves_pressure=name honored regardless of substring")

    # (D) banter without the refusal phrasing does NOT resolve
    banter = [{
        "kind": "action", "actor": "wade_wilson",
        "action": "make a bit about tacos",
        "consequence": "Felicia rolls her eyes. They keep going.",
    }]
    moved, names = evaluate_pressures(banter, [p])
    if moved:
        failures.append(f"D: banter wrongly registered as resolution: {names}")
    else:
        print("  PASS D: pure banter does NOT resolve the pressure")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("  ✗", f)
        print("PRESSURE-05: FAIL")
        return 1
    print("\nPRESSURE-05: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

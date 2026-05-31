"""
PRESSURE-01 — Uatu must extract >=1 forcing_pressure from a real premise,
naming the absent center by name. A pure-flavor premise must raise
PressureMissingError.

LIVE model call.
"""
from __future__ import annotations
import sys, time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from engine.uatu import extract_arc
from engine.agency_engine import PressureMissingError, PlanRefusedError


PREMISE_NAMED = (
    "Felicia Hardy and Wade Wilson are at the Cheesecake Factory on a "
    "Tuesday night. They are worried about Peter Parker. Peter is one "
    "bad Tuesday from snapping. Felicia has been thinking about calling "
    "him. Wade has opinions."
)
PREMISE_FLAT = "Two people sit somewhere quiet."


def main() -> int:
    failures: list[str] = []

    # (A) Real premise -> arc with Peter-naming pressure
    print("[pressure-01.A] extract_arc(named premise) …")
    t0 = time.time()
    arc = extract_arc(PREMISE_NAMED)
    print(f"  pressures: {[p.name for p in arc.forcing_pressures]} "
          f"(took {time.time()-t0:.1f}s)")
    if not arc.forcing_pressures:
        failures.append("zero pressures extracted")
    peter_named = False
    for p in arc.forcing_pressures:
        blob = (p.name + " " + p.what_it_demands + " " +
                " ".join(p.evidence_of_progress) + " " +
                " ".join(p.resolution_modes)).lower()
        if "peter" in blob:
            peter_named = True
            print(f"  PASS A: pressure {p.name!r} references Peter")
            break
    if not peter_named:
        failures.append("no pressure references Peter Parker by name")

    # (B) Flat premise must raise PressureMissingError
    print("\n[pressure-01.B] extract_arc(flat premise) …")
    raised = False
    try:
        bad = extract_arc(PREMISE_FLAT)
        print(f"  UNEXPECTED — returned arc with {len(bad.forcing_pressures)} pressures")
    except PressureMissingError as e:
        raised = True
        print(f"  PASS B: PressureMissingError raised — {e}")
    except PlanRefusedError as e:
        # Acceptable adjacent: Uatu refused entirely (empty output).
        raised = True
        print(f"  PASS B (via refusal): PlanRefusedError raised — {e}")
    except Exception as e:
        failures.append(f"flat premise raised wrong error: {type(e).__name__}")
    if not raised:
        failures.append("flat premise did NOT raise PressureMissingError")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("  ✗", f)
        print("PRESSURE-01: FAIL")
        return 1
    print("\nPRESSURE-01: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

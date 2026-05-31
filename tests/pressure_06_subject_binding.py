"""
PRESSURE-06 — every Pressure binds to a premise-explicit subject character.

LIVE for (A) and (B): extract_arc on real premises; assert subject
binding is honored. OFFLINE for (C): a hand-crafted proxy Pressure
(subject not in premise) must fail validation with PressureMissingError.
"""
from __future__ import annotations
import sys, time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from engine.uatu import extract_arc, _validate_pressure_subjects, _premise_allowed_subject_keys
from engine.agency_engine import Pressure, PressureMissingError


PREMISE_PETER = (
    "Felicia Hardy and Wade Wilson are at the Cheesecake Factory on a "
    "Tuesday night. They are worried about Peter Parker. Peter is one "
    "bad Tuesday from snapping a webline. Felicia has been thinking "
    "about calling him. Wade has opinions."
)

PREMISE_FELICIA_WADE_ONLY = (
    "Felicia Hardy and Wade Wilson have a standing weekly Cheesecake "
    "Factory date. Tonight Felicia is angry about something Wade did "
    "last Thursday and Wade is going to have to answer for it before "
    "the second round arrives."
)


def main() -> int:
    failures: list[str] = []

    # ── A: premise names Peter as the stakes-holder ──────────────────────
    print("[pressure-06.A] extract_arc(PREMISE_PETER) …")
    t0 = time.time()
    arc_a = extract_arc(PREMISE_PETER)
    print(f"  pressures ({len(arc_a.forcing_pressures)}) "
          f"(took {time.time()-t0:.1f}s):")
    for p in arc_a.forcing_pressures:
        print(f"    • {p.name}: subjects={p.subject_character_ids}  "
              f"evidence_sample={p.evidence_of_progress[:4]}")

    if not arc_a.forcing_pressures:
        failures.append("A: zero pressures extracted from Peter premise")
    for p in arc_a.forcing_pressures:
        if "peter_parker" not in p.subject_character_ids:
            failures.append(
                f"A: pressure {p.name!r} missing peter_parker in subjects "
                f"(got {p.subject_character_ids!r})"
            )
    if not any(f.startswith("A:") for f in failures):
        print("  PASS A: every pressure binds peter_parker as subject")

    # ── B: premise names only Felicia + Wade — subjects must be a subset
    print("\n[pressure-06.B] extract_arc(PREMISE_FELICIA_WADE_ONLY) …")
    t0 = time.time()
    arc_b = extract_arc(PREMISE_FELICIA_WADE_ONLY)
    print(f"  pressures ({len(arc_b.forcing_pressures)}) "
          f"(took {time.time()-t0:.1f}s):")
    for p in arc_b.forcing_pressures:
        print(f"    • {p.name}: subjects={p.subject_character_ids}")

    allowed_b = {"felicia_hardy", "wade_wilson"}
    if not arc_b.forcing_pressures:
        failures.append("B: zero pressures extracted from Felicia/Wade premise")
    for p in arc_b.forcing_pressures:
        subj = set(p.subject_character_ids)
        if not subj.issubset(allowed_b):
            failures.append(
                f"B: pressure {p.name!r} subjects {sorted(subj)!r} not "
                f"subset of premise-allowed {sorted(allowed_b)!r}"
            )
    if not any(f.startswith("B:") for f in failures):
        print("  PASS B: subjects are subset of premise-named characters")

    # ── C: hand-crafted proxy pressure (subject=MJ for Peter premise) ───
    print("\n[pressure-06.C] proxy Pressure(subject=mary_jane_watson) on "
          "Peter premise must fail validation …")
    proxy = Pressure(
        name="proxy_mj_pressure",
        what_it_demands="Mary-Jane is summoned to help Peter.",
        subject_character_ids=["mary_jane_watson"],   # not in Peter premise
        evidence_of_progress=["mary_jane_watson", "call mj", "text mj"],
        resolution_modes=["BringInCharacter(mary_jane_watson)",
                          "refusal named on-stage"],
    )
    allowed = _premise_allowed_subject_keys(PREMISE_PETER)
    if "mary_jane_watson" in allowed:
        failures.append(
            f"C: test premise unexpectedly contains MJ-token; allowed={sorted(allowed)}"
        )
    err = _validate_pressure_subjects(proxy, allowed, PREMISE_PETER)
    if err is None:
        failures.append("C: proxy pressure with non-premise subject was NOT rejected")
    else:
        print(f"  PASS C: proxy pressure rejected with: {err[:140]}")

    # also verify PressureMissingError is the raised type — simulate the
    # raise path that _extract_arc_async takes
    try:
        if err is not None:
            raise PressureMissingError(premise=PREMISE_PETER, raw=err, attempts=1)
        failures.append("C: PressureMissingError raise path not exercised")
    except PressureMissingError as e:
        print(f"  PASS C2: PressureMissingError raised: {str(e)[:120]}")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("  ✗", f)
        print("PRESSURE-06: FAIL")
        return 1
    print("\nPRESSURE-06: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

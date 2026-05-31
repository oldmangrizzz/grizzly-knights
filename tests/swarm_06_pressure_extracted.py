"""
SWARM-06 — Uatu extracts forcing_pressures from a premise.

  A) Premise mentioning Peter Parker → must produce at least one Pressure
     whose payload (name + what_it_demands + evidence_of_progress)
     references Peter (substring match on 'peter').
  B) Premise that is pure flavor with no thing-to-resolve ("Two people sit
     somewhere") → extract_arc raises PressureMissingError.
  C) Returned EpisodeArc.present is premise-explicit only — no folding
     in of Peter / MJ / etc.

This is a live model call.
"""
from __future__ import annotations
import sys, time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from engine.uatu import extract_arc
from engine.agency_engine import PressureMissingError


PREMISE_REAL = (
    "Felicia Hardy and Wade Wilson are at the Cheesecake Factory in midtown "
    "Manhattan on a Tuesday night, both several drinks in, both worried "
    "about Peter Parker. Peter has been wound tighter than usual for weeks. "
    "Felicia has been thinking about calling him. Wade has opinions. "
    "Anything can happen Tuesday."
)

PREMISE_FLAT = "Two people sit somewhere."


def main() -> int:
    failures: list[str] = []

    # ── A: real premise extracts a Peter-naming pressure ──────────────────
    t0 = time.time()
    print("[swarm-06.A] extract_arc(real premise) …")
    arc = extract_arc(PREMISE_REAL)
    dt = time.time() - t0
    print(f"  title:      {arc.title!r}")
    print(f"  setting:    {arc.setting!r}")
    print(f"  present:    {arc.present}")
    print(f"  pressures:  {[p.name for p in arc.forcing_pressures]}")
    for p in arc.forcing_pressures:
        print(f"    • {p.name}: {p.what_it_demands[:120]}")
        print(f"      modes:    {p.resolution_modes[:3]}")
        print(f"      evidence: {p.evidence_of_progress[:5]}")
    print(f"  elapsed: {dt:.1f}s")

    if not arc.forcing_pressures:
        failures.append("no forcing_pressures extracted from real premise")

    peter_named = False
    for p in arc.forcing_pressures:
        blob = (
            p.name + " " + p.what_it_demands + " "
            + " ".join(p.evidence_of_progress) + " "
            + " ".join(p.resolution_modes)
        ).lower()
        if "peter" in blob:
            peter_named = True
            break
    if not peter_named:
        failures.append("no pressure references Peter Parker — premise pivot ignored")

    # ── C: present is premise-explicit only ─────────────────────────────
    present_set = set(arc.present)
    forbidden = {"peter_parker", "mary_jane_watson", "johnny_storm"}
    leaked = forbidden & present_set
    if leaked:
        failures.append(f"present leaked phantom cast: {sorted(leaked)}")
    if not {"felicia_hardy", "wade_wilson"} <= present_set:
        failures.append(f"required pair missing from present: {sorted(present_set)}")

    # ── B: flat premise raises PressureMissingError ─────────────────────
    print("\n[swarm-06.B] extract_arc(flat premise) …")
    raised = False
    try:
        bad = extract_arc(PREMISE_FLAT)
        print(f"  UNEXPECTED — extracted arc with {len(bad.forcing_pressures)} pressures")
        # If Uatu hallucinated a pressure for an empty premise, the contract
        # still requires PressureMissingError. Check evidence quality —
        # but the engine should already have raised. Treat any return as
        # a failure of the refusal contract.
    except PressureMissingError as e:
        raised = True
        print(f"  PASS — PressureMissingError raised: {e}")
    except Exception as e:
        print(f"  WRONG ERROR — got {type(e).__name__}: {e}")
        failures.append(f"flat premise raised wrong error type: {type(e).__name__}")
    if not raised and "wrong error type" not in " ".join(failures):
        failures.append("flat premise did not raise PressureMissingError (engine refused to refuse)")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(f"  ✗ {f}")
        print("SWARM-06: FAIL")
        return 1
    print("\nSWARM-06: PASS — pressure extraction enforced.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

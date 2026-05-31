"""
PRESSURE-21 — three unmoved pressure scenes produce FAIL/STALL-CLOSE.

Offline. Fabricate a stall streak at the configured cap and pass stall_close=True
into final verdict assembly.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from engine.agency_engine import Pressure  # noqa: E402
from engine.uatu import EpisodeArc  # noqa: E402
from cook_ep01_pressure_proof_v3 import (  # noqa: E402
    STALL_CAP,
    STALL_CLOSE_REASON,
    VERDICT_FAIL,
    build_pressure_proof_verdict,
)


def main() -> int:
    failures: list[str] = []
    p = Pressure(
        name="pressure_x",
        what_it_demands="Pressure must move or close stalls hard.",
        subject_character_ids=["peter_parker"],
        resolution_modes=["BringInCharacter(peter_parker)"],
        evidence_of_progress=["peter"],
        resolved=False,
    )
    arc = EpisodeArc(
        title="Stall Close Verdict",
        logline="A pressure stalls three times.",
        arc="The pressure did not move for three consecutive scenes.",
        opening_situation="booth",
        setting="Cheesecake Factory booth",
        time="Tuesday afternoon",
        present=["felicia_hardy", "wade_wilson"],
        forcing_pressures=[p],
        tone_floor="Marvel Knights",
    )
    arc.stall_streaks = {"pressure_x": STALL_CAP}
    stall_close = max(arc.stall_streaks.values(), default=0) >= STALL_CAP
    result = build_pressure_proof_verdict(
        est_audio_minutes=75.0,
        pressure_gates_passed=False,
        clean_episode_close=False,
        stall_close=stall_close,
    )
    print(f"  stall_streaks={arc.stall_streaks} stall_close={stall_close}")
    print(f"  verdict={result.verdict}/{result.reason} clean={result.clean_episode_close}")

    if result.verdict != VERDICT_FAIL:
        failures.append(f"expected FAIL verdict, got {result.verdict}")
    if result.reason != STALL_CLOSE_REASON:
        failures.append(f"expected {STALL_CLOSE_REASON}, got {result.reason}")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("  ✗", f)
        print("PRESSURE-21: FAIL")
        return 1
    print("\nPRESSURE-21: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

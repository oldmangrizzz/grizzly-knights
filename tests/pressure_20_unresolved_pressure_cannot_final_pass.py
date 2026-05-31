"""
PRESSURE-20 — unresolved pressure cannot final-pass inside runtime range.

Offline. Fabricate an unresolved pressure with scenes_run>=2 and runtime in the
60-90 minute band. The final verdict must be FAIL/OPEN-PRESSURE.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from engine.agency_engine import Pressure  # noqa: E402
from engine.uatu import EpisodeArc  # noqa: E402
from cook_ep01_pressure_proof_v3 import (  # noqa: E402
    OPEN_PRESSURE_REASON,
    VERDICT_FAIL,
    VERDICT_PASS,
    build_pressure_proof_verdict,
)


def main() -> int:
    failures: list[str] = []
    p = Pressure(
        name="pressure_x",
        what_it_demands="Peter Parker must answer the intervention.",
        subject_character_ids=["peter_parker"],
        resolution_modes=["BringInCharacter(peter_parker)"],
        evidence_of_progress=["peter"],
        resolved=False,
    )
    arc = EpisodeArc(
        title="Open Pressure Verdict",
        logline="Open pressure remains.",
        arc="An unresolved pressure remains after two scenes.",
        opening_situation="booth",
        setting="Cheesecake Factory booth",
        time="Tuesday afternoon",
        present=["felicia_hardy", "wade_wilson"],
        forcing_pressures=[p],
        tone_floor="Marvel Knights",
    )
    scenes_run = 2
    est_audio = 75.0
    pressure_gates_passed = scenes_run >= 2 and not arc.open_pressures() and not arc.summon_pending
    result = build_pressure_proof_verdict(
        est_audio_minutes=est_audio,
        pressure_gates_passed=pressure_gates_passed,
        clean_episode_close=pressure_gates_passed,
        pressure_gate_reason=OPEN_PRESSURE_REASON,
    )
    print(f"  open={[x.name for x in arc.open_pressures()]} scenes_run={scenes_run} est_audio={est_audio}")
    print(f"  verdict={result.verdict}/{result.reason} clean={result.clean_episode_close}")

    if result.verdict == VERDICT_PASS:
        failures.append("unresolved pressure returned PASS")
    if result.verdict != VERDICT_FAIL or result.reason != OPEN_PRESSURE_REASON:
        failures.append(f"expected FAIL/{OPEN_PRESSURE_REASON}, got {result.verdict}/{result.reason}")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("  ✗", f)
        print("PRESSURE-20: FAIL")
        return 1
    print("\nPRESSURE-20: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

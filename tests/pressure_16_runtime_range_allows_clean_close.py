"""
PRESSURE-16 — 60-90 minute runtime allows clean close when gates pass.

Offline. Fabricate all pressure gates passing with estimated audio inside the
allowed range. Assert final verdict is PASS and post-resolution planning may
clean-close.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from cook_ep01_pressure_proof_v3 import (  # noqa: E402
    VERDICT_PASS,
    build_pressure_proof_verdict,
    decide_post_resolution_runtime_step,
)


def main() -> int:
    failures: list[str] = []

    result = build_pressure_proof_verdict(
        est_audio_minutes=75.0,
        pressure_gates_passed=True,
        clean_episode_close=True,
    )
    decision = decide_post_resolution_runtime_step(
        scene_number=9,
        est_audio_minutes=75.0,
        open_pressures=[],
        summon_pending={},
        prior_present=["felicia_hardy", "wade_wilson"],
    )

    print(f"  verdict={result.verdict}/{result.reason} clean={result.clean_episode_close}")
    print(
        f"  decision reason={decision.reason} may_clean_close={decision.may_clean_close} "
        f"spec={decision.spec}"
    )

    if result.verdict != VERDICT_PASS:
        failures.append(f"expected PASS verdict, got {result.verdict}/{result.reason}")
    if not result.clean_episode_close:
        failures.append("runtime-range proof data did not allow clean_episode_close")
    if not decision.may_clean_close or decision.spec is not None:
        failures.append("runtime-range post-resolution state did not allow planner clean close")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("  ✗", f)
        print("PRESSURE-16: FAIL")
        return 1
    print("\nPRESSURE-16: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())


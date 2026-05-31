"""
PRESSURE-17 — runtime above 90 minutes is a coded FAIL.

Offline. Fabricate proof-verdict data with all pressure gates passing but
estimated audio runtime above 90.0 minutes. Assert final verdict is
FAIL/RUNTIME-HIGH, not PASS.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from cook_ep01_pressure_proof_v3 import (  # noqa: E402
    RUNTIME_HIGH_REASON,
    VERDICT_FAIL,
    VERDICT_PASS,
    build_pressure_proof_verdict,
)


def main() -> int:
    failures: list[str] = []

    result = build_pressure_proof_verdict(
        est_audio_minutes=90.1,
        pressure_gates_passed=True,
        clean_episode_close=True,
    )
    print(f"  verdict={result.verdict}/{result.reason} clean={result.clean_episode_close}")

    if result.verdict == VERDICT_PASS:
        failures.append("runtime-high proof data returned PASS")
    if result.verdict != VERDICT_FAIL or result.reason != RUNTIME_HIGH_REASON:
        failures.append(f"expected FAIL/{RUNTIME_HIGH_REASON}, got {result.verdict}/{result.reason}")
    if result.clean_episode_close:
        failures.append("runtime-high proof data allowed clean_episode_close=True")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("  ✗", f)
        print("PRESSURE-17: FAIL")
        return 1
    print("\nPRESSURE-17: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())


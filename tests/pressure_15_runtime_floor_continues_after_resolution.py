"""
PRESSURE-15 — resolved pressures below 60 minutes force fallout continuation.

Offline. Fabricate the post-resolution state with no open pressures and no
summon-pending entries, but estimated audio runtime below the floor. Assert the
next-step decision continues with post_resolution_continuation consequences
instead of allowing a clean close.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from cook_ep01_pressure_proof_v3 import (  # noqa: E402
    RUNTIME_LOW_REASON,
    decide_post_resolution_runtime_step,
)


def main() -> int:
    failures: list[str] = []

    decision = decide_post_resolution_runtime_step(
        scene_number=5,
        est_audio_minutes=24.1,
        open_pressures=[],
        summon_pending={},
        prior_present=["felicia_hardy", "wade_wilson", "peter_parker"],
    )

    spec = decision.spec
    print(
        f"  reason={decision.reason} post_resolution={decision.post_resolution_continuation} "
        f"may_clean_close={decision.may_clean_close}"
    )
    print(f"  spec_present={getattr(spec, 'present', None)}")
    print(f"  spec_situation={getattr(spec, 'situation', '')[:120]!r}")

    if decision.reason != RUNTIME_LOW_REASON:
        failures.append(f"expected {RUNTIME_LOW_REASON}, got {decision.reason}")
    if not decision.post_resolution_continuation:
        failures.append("runtime-low post-resolution state did not request post_resolution_continuation")
    if decision.may_clean_close:
        failures.append("runtime-low post-resolution state allowed clean close")
    if spec is None:
        failures.append("runtime-low post-resolution state did not return a continuation scene")
    elif not any(word in spec.situation.lower() for word in ("consequence", "aftermath", "fallout")):
        failures.append("continuation scene does not describe consequences/fallout")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("  ✗", f)
        print("PRESSURE-15: FAIL")
        return 1
    print("\nPRESSURE-15: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())


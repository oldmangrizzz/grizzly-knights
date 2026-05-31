"""
SWARM-05 — plan_next_scene plans from prior chronicle, not pre-decided lineup.

Build a synthetic prior-scene chronicle where Felicia + Wade walk out
together to "the parking garage" via ChangeSetting. Call plan_next_scene
with that chronicle. Assert:
  • returned scene's `setting` references the garage (substring match)
  • returned `present` is exactly {felicia_hardy, wade_wilson} (NOT a
    fresh lineup pulled from canon or roster)
  • returned `situation` references the garage / cab / walk-out / drink
    or some concrete continuation cue from the chronicle

This is a live model call.
"""
from __future__ import annotations
import sys, time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from engine.uatu import plan_next_scene


PRIOR_CHRONICLE = [
    {"turn": 0, "actor": "wade_wilson", "kind": "action",
     "action": "swirl the tequila and take a long, slow sip",
     "consequence": "Wade buys time to decide whether to say the thing.",
     "tags": ["drinks"]},
    {"turn": 3, "actor": "wade_wilson", "kind": "action",
     "action": "set the glass down and meet Felicia's eyes flat",
     "consequence": "He says it: 'We're not okay. Peter's not okay. None of us are okay.'",
     "tags": ["lines_crossed"]},
    {"turn": 6, "actor": "felicia_hardy", "kind": "action",
     "action": "pull a fifty from her purse, drop it on the table",
     "consequence": "She's paying and leaving. The conversation is moving outside.",
     "tags": ["decisions_made"]},
    {"turn": 7, "actor": "felicia_hardy", "kind": "change_setting",
     "location": "the parking garage across from the Cheesecake Factory",
     "transition": "We walk out together. The garage is half-empty, smells like exhaust and rain."},
]
PRIOR_PRESENT = ["felicia_hardy", "wade_wilson"]
ARC = (
    "Felicia and Wade spend a Tuesday night failing to talk around Peter "
    "Parker. They keep moving rooms because neither can sit still long "
    "enough to say the actual thing. By the come-down somebody has named it."
)


def main() -> int:
    t0 = time.time()
    print("[swarm-05] calling plan_next_scene(prior_chronicle=…)")
    spec = plan_next_scene(PRIOR_CHRONICLE, PRIOR_PRESENT, ARC)
    dt = time.time() - t0

    if spec is None:
        print("  plan_next_scene returned None (arc done) — unexpected for this probe")
        print("SWARM-05: FAIL")
        return 1

    print(f"  setting:       {spec.setting!r}")
    print(f"  time:          {spec.time!r}")
    print(f"  present:       {spec.present}")
    print(f"  situation:     {spec.situation[:240]}…")
    print(f"  pressure_hint: {spec.pressure_hint!r}")
    print(f"  elapsed:       {dt:.1f}s")

    failures: list[str] = []
    setting_low = spec.setting.lower()
    if not any(t in setting_low for t in ("garage", "parking", "lot")):
        failures.append(f"setting does not reference the garage/parking: {spec.setting!r}")
    present = set(spec.present)
    if present != {"felicia_hardy", "wade_wilson"}:
        failures.append(f"present is not exactly the walk-out pair: {sorted(present)}")
    sit = spec.situation.lower()
    cues = ("garage", "parking", "walk", "outside", "tequila", "peter",
            "rain", "exhaust", "fifty", "booth", "left", "stepped")
    if not any(c in sit for c in cues):
        failures.append(f"situation has no continuation cue from prior chronicle: {spec.situation[:120]!r}")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(f"  ✗ {f}")
        print("SWARM-05: FAIL")
        return 1
    print("\nSWARM-05: PASS — next scene was planned from prior ending state, "
          "not a fresh lineup.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

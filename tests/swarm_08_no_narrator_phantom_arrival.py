"""
SWARM-08 — narrator cannot spawn off-stage characters.

Offline. Mentions of off-stage characters are allowed, but physical
arrival/presence must come through BringInCharacter so the cast ledger and
chronicle stay truthful.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from engine.agency_engine import _line_has_phantom_arrival, normalize_spoken_names


def main() -> int:
    roster = ["felicia_hardy", "wade_wilson", "peter_parker", "mary_jane_watson"]
    allowed = ["felicia_hardy", "wade_wilson", "peter_parker"]
    failures: list[str] = []

    phantom = normalize_spoken_names(
        "Across the room, MJ appears, flustered and breathless.",
        roster,
    )
    if phantom != "Across the room, Mary-Jane appears, flustered and breathless.":
        failures.append(f"MJ alias did not normalize before phantom check: {phantom!r}")
    if not _line_has_phantom_arrival(phantom, allowed, roster):
        failures.append("off-stage Mary-Jane physical appearance was not flagged")
    else:
        print("  PASS A: off-stage Mary-Jane appearance is flagged")

    mention = normalize_spoken_names(
        "Felicia says Mary Jane is an option if Peter keeps deflecting.",
        roster,
    )
    if _line_has_phantom_arrival(mention, allowed, roster):
        failures.append("non-physical Mary-Jane mention was incorrectly flagged")
    else:
        print("  PASS B: off-stage mention without physical arrival is allowed")

    present = "Peter appears ready to bolt, then grips the table."
    if _line_has_phantom_arrival(present, allowed, roster):
        failures.append("present Peter appearance was incorrectly flagged")
    else:
        print("  PASS C: present cast physical beat is allowed")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("  \u2717", f)
        print("SWARM-08: FAIL")
        return 1

    print("\nSWARM-08: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

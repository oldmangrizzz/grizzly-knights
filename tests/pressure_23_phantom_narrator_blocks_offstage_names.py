"""
PRESSURE-23 — phantom-narrator gate: NARRATOR may not describe an
off-stage roster character (or off-roster Marvel character) by bare
first-name or nickname. Full-name forms ("Matt Murdock",
"Mary-Jane Watson") are always allowed because they are the documented
canonical narrator-reference shape.

Offline. Exercises the V3.4 real leaks from
episodes_text/_pressure_proof_v3_4/01 - The Tuesday Conspiracy.txt
lines 255 and 399 verbatim.
"""
from __future__ import annotations
from pathlib import Path as _ShimPath
import sys as _shim_sys
_shim_sys.path.insert(0, str(_ShimPath(__file__).parent.parent))

import glob
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from engine.agency_engine import _line_has_phantom_narrator_mention


def _roster() -> list[str]:
    return [
        os.path.splitext(os.path.basename(p))[0]
        for p in glob.glob(str(ROOT / "universe" / "characters" / "*.yaml"))
    ]


def main() -> int:
    roster = _roster()
    cast = ["felicia_hardy", "wade_wilson", "peter_parker"]

    # 1. Real V3.4 leak (line 255): Jess, Frank, Matt — all off-cast roster.
    leak_1 = (
        "There is a tension now, rippling beneath the sheen of spilled gin and "
        "the weight of unsaid truths. Jess's left hand, palm flat against the "
        "table, is still. Too still. Frank's bourbon is no longer a drink but "
        "a weaponized silence. Matt's head tilts, just so—he hears it before "
        "anyone speaks it."
    )
    is_p, tok = _line_has_phantom_narrator_mention(leak_1, cast, roster)
    assert is_p, "leak_1 should be flagged but was not"
    assert tok in {"jess", "frank", "matt", "jessie", "frankie", "matty"}, f"unexpected token: {tok!r}"
    print(f"PASS A: V3.4 line-255 leak flagged (token={tok!r})")

    # 2. Real V3.4 leak (line 399): Karen, Foggy — off-roster phantom names.
    leak_2 = (
        "Peter speaks, his voice higher than the mood, the effort to steady "
        "the room clear in the shake of his hand as he sets his soda down too "
        "hard—bubbles rushing at the sides. Karen's eyes flit to him, but "
        "only for a second; she doesn't stop fidgeting with the napkin. "
        "Foggy exhales sharp through his nose, a laugh that dies alone, and "
        "the tension in Matt's jaw stays locked."
    )
    is_p, tok = _line_has_phantom_narrator_mention(leak_2, cast, roster)
    assert is_p, "leak_2 should be flagged but was not"
    print(f"PASS B: V3.4 line-399 leak flagged (token={tok!r})")

    # 3. Canonical full-name reference is ALLOWED.
    canon = "Felicia muttered something about needing to call Mary-Jane Watson before sunrise."
    is_p, tok = _line_has_phantom_narrator_mention(canon, cast, roster)
    assert not is_p, f"canon mention falsely flagged with token={tok!r}"
    print("PASS C: canonical 'Mary-Jane Watson' full-name allowed")

    # 4. Cast-member references are ALLOWED.
    cast_line_1 = "Felicia leans back, her eyes locked on Wade."
    cast_line_2 = "Peter exhales into the crack it leaves."
    for ln in (cast_line_1, cast_line_2):
        is_p, tok = _line_has_phantom_narrator_mention(ln, cast, roster)
        assert not is_p, f"cast member flagged: {ln!r} tok={tok!r}"
    print("PASS D: in-cast narrator mentions of Felicia, Wade, Peter allowed")

    # 5. Off-roster hallucinated names (Karen, Foggy) flagged even in isolation.
    iso = "Karen smiled coldly from the doorway."
    is_p, tok = _line_has_phantom_narrator_mention(iso, cast, roster)
    assert is_p and tok == "karen", f"off-roster Karen not flagged: {tok!r}"
    print("PASS E: off-roster name 'Karen' flagged in isolation")

    # 6. Matt Murdock in cast → allowed.
    cast_with_matt = ["felicia_hardy", "matt_murdock"]
    matt_line = "Matt's head tilts toward the door."
    is_p, tok = _line_has_phantom_narrator_mention(matt_line, cast_with_matt, roster)
    assert not is_p, f"in-cast Matt falsely flagged: {tok!r}"
    print("PASS F: when matt_murdock is in cast, bare 'Matt' is allowed")

    print("\nPRESSURE-23: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

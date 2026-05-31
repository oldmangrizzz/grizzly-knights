"""
APT-09: Uatu litany / oath integrity.

scripts_to_prose injects UATU_OPENING_LITANY and UATU_CLOSING_OATH around
the scenes. The threat is: if a model output (narrator block or dialogue)
already contains the litany or the oath, the prose builder may DOUBLE-
bookend it. Spec asks: 'verify the dedup logic doesn't double-bookend'.

We construct synthetic Script blocks containing pieces of the litany/oath
and run scripts_to_prose. Then count occurrences.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from engine.script_generator import Script, ScriptBlock
from engine.agency_engine import EpisodePlan
from engine.uatu import UATU_OPENING_LITANY, UATU_CLOSING_OATH
from export_episodes_agency import scripts_to_prose


def main() -> int:
    # Scene 1: narrator output already contains the full opening litany
    # (as if Uatu generated it inside the scene).
    s1 = Script(
        episode_number=1, episode_title="x", act=1, scene_number=1,
        characters=["felicia_hardy"], location="x", raw="",
        blocks=[
            ScriptBlock(type="narrator", text=UATU_OPENING_LITANY.strip()),
            ScriptBlock(type="dialogue", text="Hi.", character="felicia_hardy", voice_key="felicia_hardy"),
        ],
    )
    # Scene 2: narrator output already contains the full closing oath.
    s2 = Script(
        episode_number=1, episode_title="x", act=3, scene_number=2,
        characters=["felicia_hardy"], location="x", raw="",
        blocks=[
            ScriptBlock(type="dialogue", text="Bye.", character="felicia_hardy", voice_key="felicia_hardy"),
            ScriptBlock(type="narrator", text=UATU_CLOSING_OATH.strip()),
        ],
    )

    plan = EpisodePlan(number=1, title="x", logline="x", cast=["felicia_hardy"], scenes=[])
    prose = scripts_to_prose([s1, s2], plan)

    findings: list[str] = []
    notes: list[str] = []

    open_anchor = "I am the Watcher. I am your guide through these vast new realities."
    close_anchor = "I have watched. I will continue to watch."

    n_open  = prose.count(open_anchor)
    n_close = prose.count(close_anchor)

    notes.append(f"  • opening litany anchor occurrences: {n_open} (expect 1)")
    notes.append(f"  • closing oath anchor occurrences:   {n_close} (expect 1)")

    if n_open != 1:
        findings.append(f"  • OPENING LITANY appears {n_open}x — bookend dedup is MISSING")
    if n_close != 1:
        findings.append(f"  • CLOSING OATH appears {n_close}x — bookend dedup is MISSING")

    # Now: confirm normal (uncontaminated) case still produces exactly one of each
    clean = Script(
        episode_number=1, episode_title="x", act=1, scene_number=1,
        characters=["felicia_hardy"], location="x", raw="",
        blocks=[ScriptBlock(type="dialogue", text="hi.", character="felicia_hardy", voice_key="felicia_hardy")],
    )
    clean_prose = scripts_to_prose([clean], plan)
    if clean_prose.count(open_anchor) != 1 or clean_prose.count(close_anchor) != 1:
        findings.append(f"  • CLEAN case wrong counts open={clean_prose.count(open_anchor)} close={clean_prose.count(close_anchor)}")
    else:
        notes.append("  • clean case bookends present exactly once ✓")

    print("=== NOTES ===")
    for n in notes:
        print(n)
    print()
    print("=== FINDINGS ===")
    if not findings:
        print("HOLDS")
        return 0
    for f in findings:
        print(f)
    return 1


if __name__ == "__main__":
    sys.exit(main())

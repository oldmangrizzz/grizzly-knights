"""
APT-09b: scripts_to_prose idempotency.

Calling scripts_to_prose twice on the same input must yield the same
output. Concretely: the result of one call, when fed back through the
function (after re-wrapping in a narrator-shaped Script), must still
have exactly one opening litany and one closing oath.

We exercise both the clean path and the contaminated path.
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


OPEN_ANCHOR  = "I am the Watcher. I am your guide through these vast new realities."
CLOSE_ANCHOR = "I have watched. I will continue to watch."


def _mk_script(blocks: list[ScriptBlock], scene: int = 1) -> Script:
    return Script(
        episode_number=1, episode_title="x", act=1, scene_number=scene,
        characters=["felicia_hardy"], location="x", raw="",
        blocks=blocks,
    )


def main() -> int:
    plan = EpisodePlan(number=1, title="x", logline="x",
                       cast=["felicia_hardy"], scenes=[])

    findings: list[str] = []
    notes: list[str] = []

    # Case A: contaminated input (the APT-09 scenario)
    s1 = _mk_script([
        ScriptBlock(type="narrator", text=UATU_OPENING_LITANY.strip()),
        ScriptBlock(type="dialogue", text="Hi.",
                    character="felicia_hardy", voice_key="felicia_hardy"),
    ], scene=1)
    s2 = _mk_script([
        ScriptBlock(type="dialogue", text="Bye.",
                    character="felicia_hardy", voice_key="felicia_hardy"),
        ScriptBlock(type="narrator", text=UATU_CLOSING_OATH.strip()),
    ], scene=2)

    once  = scripts_to_prose([s1, s2], plan)

    # Second call on the SAME input objects — should produce identical output.
    twice = scripts_to_prose([s1, s2], plan)

    notes.append(f"  • contaminated: once==twice -> {once == twice}")
    notes.append(f"  • contaminated once  open={once.count(OPEN_ANCHOR)} close={once.count(CLOSE_ANCHOR)}")
    notes.append(f"  • contaminated twice open={twice.count(OPEN_ANCHOR)} close={twice.count(CLOSE_ANCHOR)}")

    if once != twice:
        findings.append("  • contaminated: double-call != single-call (NOT IDEMPOTENT)")
    if once.count(OPEN_ANCHOR) != 1 or once.count(CLOSE_ANCHOR) != 1:
        findings.append(f"  • contaminated: bookend counts wrong on single call "
                        f"(open={once.count(OPEN_ANCHOR)} close={once.count(CLOSE_ANCHOR)})")

    # Case B: re-feed the output as a narrator block (worst case — entire
    # prior prose, including bookends, becomes a narrator block of the
    # next call). After normalization that whole block must be stripped.
    refeed = _mk_script([
        ScriptBlock(type="narrator", text=once),
        ScriptBlock(type="dialogue", text="again.",
                    character="felicia_hardy", voice_key="felicia_hardy"),
    ], scene=1)
    refed_prose = scripts_to_prose([refeed], plan)
    notes.append(f"  • re-fed: open={refed_prose.count(OPEN_ANCHOR)} close={refed_prose.count(CLOSE_ANCHOR)}")
    if refed_prose.count(OPEN_ANCHOR) != 1 or refed_prose.count(CLOSE_ANCHOR) != 1:
        findings.append(f"  • re-fed: bookend counts wrong "
                        f"(open={refed_prose.count(OPEN_ANCHOR)} close={refed_prose.count(CLOSE_ANCHOR)})")

    # Case C: clean input — idempotent and exactly-once bookends.
    clean = _mk_script([
        ScriptBlock(type="dialogue", text="hi.",
                    character="felicia_hardy", voice_key="felicia_hardy"),
    ])
    c1 = scripts_to_prose([clean], plan)
    c2 = scripts_to_prose([clean], plan)
    notes.append(f"  • clean: once==twice -> {c1 == c2}")
    if c1 != c2:
        findings.append("  • clean: double-call != single-call (NOT IDEMPOTENT)")
    if c1.count(OPEN_ANCHOR) != 1 or c1.count(CLOSE_ANCHOR) != 1:
        findings.append(f"  • clean: bookend counts wrong "
                        f"(open={c1.count(OPEN_ANCHOR)} close={c1.count(CLOSE_ANCHOR)})")

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

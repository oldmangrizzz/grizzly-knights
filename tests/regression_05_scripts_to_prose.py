"""
Regression item 5 — export_episodes_agency.scripts_to_prose.

Verifies:
  • UATU_OPENING_LITANY is prepended (verbatim, stripped of trailing nl)
  • UATU_CLOSING_OATH is appended (verbatim, stripped of trailing nl)
  • Stray narrator quote-wrapping (straight, curly, angle quotes) is
    stripped from narrator blocks
  • Asterisks and parenthetical stage directions are stripped
  • Period-before-tag → comma fix lands ("X." he said → "X," he said)
  • Re-running scripts_to_prose on its own output does NOT double-bookend
    (we re-feed the same scripts; the prepend/append remains exactly one)

Uses synthetic ScriptBlocks — no live model required.
"""
from __future__ import annotations
from pathlib import Path as _ShimPath
import sys as _shim_sys
_shim_sys.path.insert(0, str(_ShimPath(__file__).parent.parent))
import sys
from engine.script_generator import Script, ScriptBlock
from engine.agency_engine import EpisodePlan
from export_episodes_agency import scripts_to_prose
from engine.uatu import UATU_OPENING_LITANY, UATU_CLOSING_OATH


def _build_synthetic_scripts() -> tuple[list[Script], EpisodePlan]:
    """Two scenes, mix of narrator + dialogue. Includes intentional
    LLM-style quote wrapping around narrator beats and stray asterisks
    and (parentheticals)."""
    s1 = Script(
        episode_number=99,
        episode_title="Regression Cook",
        act=1,
        scene_number=1,
        characters=["wade_wilson", "felicia_hardy"],
        location="A dive",
        blocks=[
            ScriptBlock(type="narrator",
                        text='"The booth holds them. Two drinks deep."'),
            ScriptBlock(type="dialogue",
                        text="*So* are we doing this or what?",
                        character="wade_wilson",
                        voice_key="wade_wilson"),
            ScriptBlock(type="dialogue",
                        text="We're doing it. (smirks) Don't make me say it twice.",
                        character="felicia_hardy",
                        voice_key="felicia_hardy"),
            ScriptBlock(type="narrator",
                        text='\u201cTime.\u201d'),
            ScriptBlock(type="dialogue",
                        text="Are you fucking with me?",
                        character="wade_wilson",
                        voice_key="wade_wilson"),
        ],
        raw="",
    )
    s2 = Script(
        episode_number=99,
        episode_title="Regression Cook",
        act=2,
        scene_number=2,
        characters=["wade_wilson", "felicia_hardy"],
        location="A parking lot",
        blocks=[
            ScriptBlock(type="narrator",
                        text="\u00abAnd so, for now, the lot holds them.\u00bb"),
            ScriptBlock(type="dialogue",
                        text="I'm not crying. You're crying.",
                        character="wade_wilson",
                        voice_key="wade_wilson"),
        ],
        raw="",
    )
    plan = EpisodePlan(
        number=99,
        title="Regression Cook",
        logline="Two scenes, synthetic content, for prose-formatter regression.",
        cast=["wade_wilson", "felicia_hardy"],
        scenes=[{"act": 1}, {"act": 2}],
    )
    return [s1, s2], plan


def main() -> int:
    failures = []
    scripts, plan = _build_synthetic_scripts()

    prose = scripts_to_prose(scripts, plan)

    # 1. Opening litany appended (stripped form)
    if UATU_OPENING_LITANY.strip() not in prose:
        failures.append(("opening litany", "UATU_OPENING_LITANY.strip() not found in prose"))
    else:
        print("  PASS UATU_OPENING_LITANY present")

    # 2. Closing oath present
    if UATU_CLOSING_OATH.strip() not in prose:
        failures.append(("closing oath", "UATU_CLOSING_OATH.strip() not found in prose"))
    else:
        print("  PASS UATU_CLOSING_OATH present")

    # 3. Narrator quote wrapping stripped — original blocks had
    #    "...", "...", «...» — none of those wrapping pairs should
    #    remain attached to the narrator line in the prose.
    if '"The booth holds them' in prose or 'The booth holds them."' in prose:
        failures.append(("narrator straight-quote strip",
                        "straight-quote wrapping not stripped from narrator beat"))
    else:
        print("  PASS narrator straight-quote wrapping stripped")

    if '\u201cTime.\u201d' in prose:
        failures.append(("narrator curly-quote strip",
                        "curly-quote wrapping not stripped from narrator beat"))
    else:
        print("  PASS narrator curly-quote wrapping stripped")

    if '\u00ab' in prose or '\u00bb' in prose:
        failures.append(("narrator angle-quote strip",
                        "« or » remained in prose"))
    else:
        print("  PASS narrator angle-quote wrapping stripped")

    # 4. Dialogue is quote-wrapped (curly), asterisks stripped, parentheticals removed.
    # Allow the "* * *" scene-break separator the formatter intentionally emits,
    # but reject any other asterisks (e.g. *emphasis*).
    leftover_asterisks = [
        ln for ln in prose.splitlines()
        if "*" in ln and ln.strip() != "* * *"
    ]
    if leftover_asterisks:
        failures.append(("asterisk strip",
                        f"asterisks remain outside scene-break separator: "
                        f"{leftover_asterisks[:3]}"))
    else:
        print("  PASS emphasis asterisks stripped (scene-break '* * *' preserved)")

    if "(smirks)" in prose:
        failures.append(("paren strip", "(smirks) parenthetical not stripped"))
    else:
        print("  PASS parenthetical stage direction stripped")

    # 5. Period-before-tag → comma fix:
    #    "We're doing it." [comma] (curly close) Felicia said.
    #    We expect a comma before the close-quote, not a period.
    #    Look for "\u201d Felicia" preceded by comma not period.
    import re
    # Find every '"X" Name said.' pattern and ensure comma form
    bad = re.findall(r"\.\u201d\s+[A-Z][a-zA-Z]+\s+(?:said|asked)\.", prose)
    if bad:
        failures.append(("period-before-tag",
                        f"found period-before-tag (should be comma): {bad[:3]}"))
    else:
        print("  PASS period-before-tag converted to comma")

    # 6. Idempotence / no double-bookend on re-run
    prose2 = scripts_to_prose(scripts, plan)
    # Exactly one occurrence of the litany and oath in a single render.
    # Use a distinctive line not present in narrator beats.
    open_anchor = "I am the Watcher. I am your guide through these vast new realities."
    n_open = prose2.count(open_anchor)
    n_close_oath_anchor = prose2.count("For I am the Watcher.")
    if n_open != 1:
        failures.append(("idempotence-open",
                        f"opening litany anchor count = {n_open}, expected 1"))
    else:
        print("  PASS exactly one opening litany in single render")
    if n_close_oath_anchor != 1:
        failures.append(("idempotence-close",
                        f"closing oath anchor count = {n_close_oath_anchor}, expected 1"))
    else:
        print("  PASS exactly one closing oath in single render")

    # 7. If we ran scripts_to_prose on the *output* of scripts_to_prose
    #    (degenerate re-run protection): the function operates on Scripts,
    #    not on its own prose output, so a true "re-run on prose" is N/A.
    #    The user-facing concern is: if scripts_to_prose is called twice
    #    on the SAME scripts, we don't get two bookends.
    if prose != prose2:
        failures.append(("determinism",
                        "scripts_to_prose not deterministic across calls"))
    else:
        print("  PASS scripts_to_prose is deterministic")

    if failures:
        print("\nFAILURES:")
        for n, err in failures:
            print(f"  ✗ {n}: {err}")
        return 1

    # Persist the synthetic prose for evidence
    from pathlib import Path

    REPO_ROOT = Path(__file__).resolve().parent.parent
    out = REPO_ROOT / "episodes_text" / "_regression_run" / "_item05_synthetic.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(prose)
    print(f"\n  evidence: {out}")
    print("\nITEM 5: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

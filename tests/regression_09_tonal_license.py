"""
Regression item 9 — Tonal license clauses present verbatim in
_yaml_to_prompt output.

These clauses are the operator's hard-rule contract with the engine.
If any one of them is silently dropped, the prompt has been weakened.
Grep the generated prompt for each required substring.
"""
from __future__ import annotations
from pathlib import Path as _ShimPath
import sys as _shim_sys
_shim_sys.path.insert(0, str(_ShimPath(__file__).parent.parent))
import sys
import yaml
from engine.agency_engine import _yaml_to_prompt, CHARACTERS_DIR


# Verbatim substrings that must appear in the system prompt for every
# character. Pulled directly from engine.agency_engine._yaml_to_prompt.
REQUIRED_VERBATIM = [
    # Universe ground rules
    "GRIZZLY KNIGHTS",
    "Marvel Knights was Marvel's adult",
    "Punisher MAX",
    # Substances clause
    "Substances are real and named",
    # Sex/lust clause
    "Lust and sex are real conversational subject matter",
    "openly bi",
    # Trauma in behavior
    "Trauma shows in BEHAVIOR",
    "You never therapize yourself",
    # Gallows humor
    "Gallows humor about your own injuries",
    # Loud cope misdirect
    "THE LOUD COPE IS THE MISDIRECT",
    # Tonal license verbatim
    "TONAL LICENSE — NOT PG-13",
    "Daredevil S1-S3",
    "Jessica Jones S1",
    "Punisher S1",
    "The Defenders alley",
    "Bendis Alias",
    "Slott Spider-Man",
    "Spencer Deadpool",
    "Aaron Punisher MAX",
    "Hickman",
    "This is NOT Disney+",
    # Profanity clause
    "PROFANITY IS HOW THESE PEOPLE TALK",
    "Fuck, shit, dick, tits",
    "Do NOT soften to 'damn'",
    # Bodies present
    "BODIES ARE PRESENT",
    # No fade-to-black
    "NO FADE-TO-BLACK REFLEX",
    # No self-censorship
    "NO SELF-CENSORSHIP REFLEX",
    # Tool imperative
    "USE THE TOOLS OR THE SCENE FAILS",
    "TONAL FLOOR VERBATIM",
]


def main() -> int:
    wade = yaml.safe_load((CHARACTERS_DIR / "wade_wilson.yaml").read_text())
    prompt = _yaml_to_prompt(wade)

    missing = [s for s in REQUIRED_VERBATIM if s not in prompt]
    if missing:
        print("ITEM 9: FAIL — missing verbatim clauses:")
        for s in missing:
            print(f"  ✗ {s!r}")
        return 1

    print(f"  PASS — all {len(REQUIRED_VERBATIM)} verbatim tonal-license "
          f"substrings present in prompt ({len(prompt)} chars total)")
    print("\nITEM 9: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

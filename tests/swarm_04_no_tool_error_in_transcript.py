"""
SWARM-04 — tool-output errors never reach the transcript as dialogue.

Probe the filter function `_line_is_tool_artifact` directly with the exact
strings observed in episodes_text/01 - Tuesday's Corruption.txt (where
'Error: Missing required parameter ...' leaked as Ben's spoken line).

Then build a fake Script with such a line spliced in and confirm the
filter rejects it; confirm a normal dialogue line is allowed through.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from engine.agency_engine import _line_is_tool_artifact


SHOULD_BE_DROPPED = [
    "Error: Missing required parameter 'message' for tool send_message",
    "ERROR: scene action budget exhausted",
    "ERROR: 'definitely_not_a_real_character' is not in the roster.",
    "ALREADY ARRIVING/PRESENT: peter_parker",
    "error: missing required parameter 'recipient_agent' for tool send_message",
    'take_action({"action":"grab her wrist gently","consequence":"tool leak"})',
    'take_action {',
    'send_message {"recipient_agent":"Peter_Parker","message":"tool leak"}',
    'address_character Your move, sweetheart',
    'BringInCharacter({"character_key":"johnny_storm","how_they_arrive":"tool leak"})',
    'BringInCharacter {"character_key":"johnny_storm","how_they_arrive":"tool leak"}',
    '<<TOOL:TakeAction>>{"action":"grab a glass"}<<END>>',
    'Oh, Uatu—always with your cryptic "I see everything" vibe.',
    'God, between Wade and Uatu’s Deep Thoughts, I’ll wing it.',
    "Watcher, you cosmic voyeur, are we doing exposition now?",
]

SHOULD_BE_KEPT = [
    "Avocado rolls? Felicia, if I wanted green mush shoved in a dead fish wrap…",
    "You two toddlers done battlin' over whether melted cheese is a food group?",
    "I don't know. Maybe I do. Maybe that's the whole problem.",
    # Casual mention of the word 'error' inside dialogue — must NOT trigger
    # the filter (it doesn't start with ERROR: and isn't a tool-name leak)
    "That was a stupid error on my part, kid.",
]


def main() -> int:
    failures: list[str] = []
    for s in SHOULD_BE_DROPPED:
        if not _line_is_tool_artifact(s):
            failures.append(f"FILTER MISSED: {s!r}")
        else:
            print(f"  drop ✓  {s[:60]!r}")
    for s in SHOULD_BE_KEPT:
        if _line_is_tool_artifact(s):
            failures.append(f"FILTER FALSE POSITIVE on valid dialogue: {s!r}")
        else:
            print(f"  keep ✓  {s[:60]!r}")

    # Now simulate a run_scene-style transcript assembly: feed the filter a
    # mix of lines and confirm assembled output has no tool-artifact.
    raw_candidates = [
        "FELICIA HARDY: That's a mood swing in a bottle if I've ever seen one.",
        "BEN GRIMM: Error: Missing required parameter 'message' for tool send_message",
        "WADE WILSON: Pete! Just the webslingin' bundle of guilt I needed.",
        "JOHNNY STORM: ERROR: scene action budget exhausted",
        'JOHNNY STORM: take_action({"action":"grab her wrist gently","consequence":"tool leak"})',
        'FELICIA HARDY: take_action {',
        'FELICIA HARDY: address_character Your move, sweetheart',
        'WADE WILSON: Oh, Uatu—always with your cryptic cosmic shrink routine.',
        "PETER PARKER: God, between Wade and Uatu's Deep Thoughts, I'll wing it.",
        "PETER PARKER: Felicia, breathe.",
    ]
    out_lines = []
    for line in raw_candidates:
        # mirror run_scene logic: text after the speaker tag is what gets filtered
        if ": " in line:
            speaker, text = line.split(": ", 1)
        else:
            speaker, text = "?", line
        if _line_is_tool_artifact(text):
            continue
        out_lines.append(f"{speaker}: {text}")

    print("\n  Assembled transcript:")
    for line in out_lines:
        print(f"    {line}")
    transcript = "\n".join(out_lines)
    if "ERROR:" in transcript or "Error:" in transcript:
        failures.append(f"transcript contains tool error: {transcript}")
    for forbidden in ("send_message", "take_action", "BringInCharacter", "<<TOOL:", "Uatu"):
        if forbidden in transcript:
            failures.append(f"transcript contains literal {forbidden!r}: {transcript}")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(f"  ✗ {f}")
        print("SWARM-04: FAIL")
        return 1
    print("\nSWARM-04: PASS — tool errors filtered, dialogue passed through.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

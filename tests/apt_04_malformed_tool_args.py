"""
APT-04: malformed args against the closure-baked scene tools.

We do NOT need the live endpoint for this — we just instantiate the tool
classes returned by make_scene_tools and call them with hostile inputs.

Cases:
  • empty strings
  • None (wrong type)
  • gigantic strings (1MB)
  • wrong types (int where str expected, list where str expected)
  • embedded null bytes
  • unicode bidi override characters
  • non-roster key (already covered by smoke but reasserted)

Outcome target: pydantic ValidationError (graceful) or guarded ERROR string.
No uncaught exceptions, no chronicle corruption (chronicle entries must be
valid dicts), no infinite loops.
"""
from __future__ import annotations
import json, sys, traceback
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from engine.scene_tools import (
    register_stage, get_stage, drop_stage, make_scene_tools,
)
from pydantic import ValidationError


def main() -> int:
    sid = register_stage(
        present=["felicia_hardy", "wade_wilson"],
        roster=["felicia_hardy", "wade_wilson", "peter_parker"],
    )
    stage = get_stage(sid)
    tools = {t.__name__: t for t in make_scene_tools(sid, "felicia_hardy")}
    BringIn   = tools["BringInCharacter"]
    Address   = tools["AddressCharacter"]
    Action    = tools["TakeAction"]
    Setting   = tools["ChangeSetting"]

    findings: list[str] = []
    passes: list[str] = []

    def run_case(label: str, fn):
        try:
            out = fn()
            passes.append(f"  • {label} -> returned: {repr(out)[:160]}")
        except ValidationError as e:
            passes.append(f"  • {label} -> ValidationError (graceful): {str(e)[:160]}")
        except (TypeError, ValueError) as e:
            passes.append(f"  • {label} -> {type(e).__name__} (graceful): {str(e)[:160]}")
        except Exception as e:
            findings.append(f"  • {label} -> UNCAUGHT {type(e).__name__}: {e}")
            traceback.print_exc()

    GIANT = "A" * (1024 * 1024)   # 1 MB
    BIDI = "\u202etxetoidrolavo\u202c"  # RLO override gimmick
    NULLY = "hello\x00world"

    # BringInCharacter
    run_case("BringIn empty key",   lambda: BringIn(character_key="", how_they_arrive="x").run())
    run_case("BringIn None key",    lambda: BringIn(character_key=None, how_they_arrive="x").run())
    run_case("BringIn int key",     lambda: BringIn(character_key=42, how_they_arrive="x").run())
    run_case("BringIn list key",    lambda: BringIn(character_key=["a","b"], how_they_arrive="x").run())
    run_case("BringIn giant key",   lambda: BringIn(character_key=GIANT, how_they_arrive="x").run())
    run_case("BringIn bidi key",    lambda: BringIn(character_key=BIDI, how_they_arrive="x").run())
    run_case("BringIn null byte",   lambda: BringIn(character_key=NULLY, how_they_arrive="x").run())
    run_case("BringIn missing how", lambda: BringIn(character_key="peter_parker").run())
    run_case("BringIn out-of-roster", lambda: BringIn(character_key="thanos", how_they_arrive="x").run())
    run_case("BringIn already-present", lambda: BringIn(character_key="felicia_hardy", how_they_arrive="x").run())

    # AddressCharacter
    run_case("Address empty key",   lambda: Address(character_key="").run())
    run_case("Address None",        lambda: Address(character_key=None).run())
    run_case("Address not on stage",lambda: Address(character_key="peter_parker").run())
    run_case("Address giant",       lambda: Address(character_key=GIANT).run())

    # TakeAction
    run_case("Action empty action", lambda: Action(action="", consequence="").run())
    run_case("Action None",         lambda: Action(action=None).run())
    run_case("Action int",          lambda: Action(action=999).run())
    run_case("Action giant",        lambda: Action(action=GIANT, consequence=GIANT).run())
    run_case("Action null byte",    lambda: Action(action=NULLY).run())
    run_case("Action bidi",         lambda: Action(action=BIDI).run())

    # ChangeSetting
    run_case("Setting empty",       lambda: Setting(new_location="", what_happens="").run())
    run_case("Setting None loc",    lambda: Setting(new_location=None, what_happens="x").run())
    run_case("Setting giant",       lambda: Setting(new_location=GIANT, what_happens=GIANT).run())

    # Chronicle integrity check: every entry must be a dict with these keys
    bad_entries = [e for e in stage.chronicle
                   if not isinstance(e, dict) or "kind" not in e]
    if bad_entries:
        findings.append(f"CHRONICLE CORRUPTION: {len(bad_entries)} bad entries: {bad_entries[:3]}")

    # Did the giant string actually get stored in chronicle? That's a finding
    # (memory/disk amplification) even if no crash.
    huge_in_chron = [
        e for e in stage.chronicle
        if isinstance(e, dict)
        and any(isinstance(v, str) and len(v) > 100_000 for v in e.values())
    ]

    drop_stage(sid)

    print("=== PASS CASES ===")
    for p in passes:
        print(p)
    print()
    print("=== CHRONICLE FINAL STATE ===")
    print(f"entries: {len(stage.chronicle)}")
    print(f"tracker: {stage.tracker}")
    print(f"giant strings stored in chronicle: {len(huge_in_chron)}")
    print()
    if findings:
        print("=== FINDINGS ===")
        for f in findings:
            print(f)
        return 1
    if huge_in_chron:
        print("=== FINDING (info) ===")
        print(f"  • Chronicle stored {len(huge_in_chron)} entry(ies) with >100KB strings — no size guard")
    print("HOLDS — all malformed inputs handled without uncaught exceptions or chronicle corruption.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

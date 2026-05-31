"""
APT-05: Chronicle tampering.

Pre-seed universe/chronicle.json with hostile payloads:
  • malformed JSON
  • missing required schema fields
  • wrong types (lists where dicts expected, etc.)
  • huge entries

Verify load_chronicle / full_planner_context / apply_delta do not crash,
do not silently drop legit data, and behave predictably. Restore the
real file (or the missing state) when done.
"""
from __future__ import annotations
import json, sys, shutil, traceback
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from engine import chronicle as C

CHRON = C.CHRONICLE_PATH

def with_backup(fn):
    backup = None
    existed = CHRON.exists()
    if existed:
        backup = CHRON.read_bytes()
    try:
        return fn()
    finally:
        if existed:
            CHRON.write_bytes(backup)
        else:
            if CHRON.exists():
                CHRON.unlink()


def main() -> int:
    findings: list[str] = []
    notes: list[str] = []

    def case(label: str, payload, op):
        CHRON.write_text(payload) if isinstance(payload, str) else CHRON.write_text(json.dumps(payload))
        try:
            result = op()
            notes.append(f"  • {label}: OK -> {type(result).__name__}: {repr(result)[:140]}")
        except json.JSONDecodeError as e:
            findings.append(f"  • {label}: load_chronicle crashed on malformed JSON: {e}")
        except (KeyError, TypeError, AttributeError) as e:
            findings.append(f"  • {label}: {type(e).__name__}: {e}")
        except Exception as e:
            findings.append(f"  • {label}: UNCAUGHT {type(e).__name__}: {e}")

    def run():
        # 1. Truncated / non-JSON
        case("malformed json — truncated",
             '{"characters": {"wade_wilson": {"state": "drunk"',
             lambda: C.load_chronicle())

        # 2. Wrong top-level type (list instead of dict)
        case("wrong top-level type — list",
             "[1,2,3]",
             lambda: C.full_planner_context(["wade_wilson"]))

        # 3. Missing all expected keys
        case("missing keys — empty dict",
             "{}",
             lambda: C.full_planner_context(["wade_wilson"]))

        # 4. characters is a list, not dict
        case("characters as list",
             json.dumps({"characters": [], "relationships": {}, "episodes": [], "world_facts": []}),
             lambda: C.full_planner_context(["wade_wilson"]))

        # 5. recent_events is a string, not a list
        case("recent_events as string",
             json.dumps({"characters": {"wade_wilson": {"recent_events": "hi"}},
                         "relationships": {}, "episodes": [], "world_facts": []}),
             lambda: C.character_context("wade_wilson"))

        # 6. Huge entry (1MB note)
        big = "X" * (1024 * 1024)
        case("huge entry in characters",
             json.dumps({"characters": {"wade_wilson": {"state": big, "recent_events": []}},
                         "relationships": {}, "episodes": [], "world_facts": []}),
             lambda: C.character_context("wade_wilson"))

        # 7. Null character entries
        case("null character entry",
             json.dumps({"characters": {"wade_wilson": None},
                         "relationships": {}, "episodes": [], "world_facts": []}),
             lambda: C.character_context("wade_wilson"))

        # 8. apply_delta on a malformed chron — does it silently drop legit data?
        good_chron = json.loads(json.dumps(C.EMPTY_CHRONICLE))
        good_chron["characters"]["wade_wilson"] = {
            "state": "PRE-EXISTING", "recent_events": ["pre-existing event"]
        }
        good_chron["world_facts"] = [{"fact": "PRE-EXISTING FACT", "established_in_ep": 1}]
        CHRON.write_text(json.dumps(good_chron))
        chron_before = C.load_chronicle()
        delta = {"characters": {"wade_wilson": {"add_events": ["new ev"]}}}
        try:
            merged = C.apply_delta(chron_before,
                                   delta,
                                   {"number": 99, "title": "t", "cast": ["wade_wilson"],
                                    "logline": "x"})
            wade = merged["characters"]["wade_wilson"]
            if wade.get("state") != "PRE-EXISTING":
                findings.append(f"  • apply_delta DROPPED pre-existing state: {wade}")
            else:
                notes.append("  • apply_delta preserves pre-existing state ✓")
            if "PRE-EXISTING FACT" not in [f["fact"] for f in merged.get("world_facts", [])]:
                findings.append("  • apply_delta dropped pre-existing world_facts")
            else:
                notes.append("  • apply_delta preserves pre-existing world_facts ✓")
        except Exception as e:
            findings.append(f"  • apply_delta crashed on legit input: {e}")
            traceback.print_exc()

    with_backup(run)

    print("=== NOTES ===")
    for n in notes:
        print(n)
    print()
    if findings:
        print("=== FINDINGS ===")
        for f in findings:
            print(f)
        return 1
    print("HOLDS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

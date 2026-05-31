"""
Regression item 3 — JSON repair in engine.uatu._parse_plan_json.

Verifies the parser handles:
  • Plain valid JSON
  • Trailing commas
  • ```json``` code fences
  • Prose preamble/postamble around a JSON block
  • Embedded literal newlines/tabs inside string values
  • Combined: fences + prose + trailing comma

Does NOT test the 3x retry loop directly (that lives in _plan_async and
requires the live model) — that is exercised by item 1 and the smoke
test. This module verifies the *repair* layer the retry loop depends on.
"""
from __future__ import annotations
from pathlib import Path as _ShimPath
import sys as _shim_sys
_shim_sys.path.insert(0, str(_ShimPath(__file__).parent.parent))
import json, sys, traceback
from engine.uatu import _parse_plan_json


CASES = [
    # name, raw_input, expected_keys_present
    (
        "plain",
        '{"title": "X", "logline": "Y", "cast": ["a"], "scenes": []}',
        {"title", "logline", "cast", "scenes"},
    ),
    (
        "trailing-comma-object",
        '{"title": "X", "logline": "Y", "cast": ["a"], "scenes": [],}',
        {"title", "logline", "cast", "scenes"},
    ),
    (
        "trailing-comma-array",
        '{"title":"X","logline":"Y","cast":["a","b",],"scenes":[]}',
        {"title", "logline", "cast", "scenes"},
    ),
    (
        "json-code-fence",
        '```json\n{"title":"X","logline":"Y","cast":["a"],"scenes":[]}\n```',
        {"title", "logline", "cast", "scenes"},
    ),
    (
        "bare-code-fence",
        '```\n{"title":"X","logline":"Y","cast":["a"],"scenes":[]}\n```',
        {"title", "logline", "cast", "scenes"},
    ),
    (
        "prose-preamble-and-postamble",
        ('Here is the plan you requested:\n\n'
         '{"title":"X","logline":"Y","cast":["a"],"scenes":[]}\n\n'
         'Let me know if you need anything else.'),
        {"title", "logline", "cast", "scenes"},
    ),
    (
        "embedded-bare-newlines-in-string",
        '{"title":"X","logline":"line one\nline two","cast":["a"],"scenes":[]}',
        {"title", "logline", "cast", "scenes"},
    ),
    (
        "invalid-backslash-escape-in-string",
        '{"title":"X","logline":"Logan\\\'s truck is parked at C:\\Temp","cast":["a"],"scenes":[]}',
        {"title", "logline", "cast", "scenes"},
    ),
    (
        "combo-fence+prose+trailing-comma",
        ('Sure! Here you go:\n\n'
         '```json\n'
         '{"title":"X","logline":"Y","cast":["a","b",],"scenes":[],}\n'
         '```\n\n'
         'Hope that helps.'),
        {"title", "logline", "cast", "scenes"},
    ),
]


def main() -> int:
    failures = []
    for name, raw, expected_keys in CASES:
        try:
            data = _parse_plan_json(raw)
            if not isinstance(data, dict):
                failures.append((name, f"not a dict: {type(data).__name__}"))
                continue
            missing = expected_keys - set(data.keys())
            if missing:
                failures.append((name, f"missing keys: {missing}; got keys: {set(data.keys())}"))
                continue
            print(f"  PASS [{name}]")
        except Exception as e:
            failures.append((name, f"{type(e).__name__}: {e}\n{traceback.format_exc()}"))

    # Now a deliberately-unrepairable case to confirm it raises JSONDecodeError
    try:
        _parse_plan_json('{title: "X" logline: }')
        failures.append(("unparseable", "expected JSONDecodeError, got success"))
    except json.JSONDecodeError:
        print(f"  PASS [unparseable raises JSONDecodeError]")
    except Exception as e:
        failures.append(("unparseable", f"wrong exception {type(e).__name__}: {e}"))

    if failures:
        print("\nFAILURES:")
        for n, err in failures:
            print(f"  ✗ {n}: {err}")
        return 1
    print("\nITEM 3: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

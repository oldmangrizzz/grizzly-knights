"""
Regression item 8 — YAML edge cases:
  • _character_one_liner defensive coercion for dict-form diagnoses
    ("colon gotcha": when YAML parses an item as `{key: None}` because of
    an unintended trailing colon, the code grabs the dict's first key).
  • _character_one_liner's split(":")[0] keeps the diagnosis short.
  • _yaml_to_prompt accepts and renders an arbitrary profile dict
    without throwing on missing optional keys.
"""
from __future__ import annotations
from pathlib import Path as _ShimPath
import sys as _shim_sys
_shim_sys.path.insert(0, str(_ShimPath(__file__).parent.parent))
import sys, traceback
from engine.uatu import _character_one_liner, CHARACTERS_DIR
from engine.agency_engine import _yaml_to_prompt


def main() -> int:
    failures = []

    # 1. Real roster pass: every character_key produces a non-empty one-liner
    keys = sorted(p.stem for p in CHARACTERS_DIR.glob("*.yaml")
                  if p.stem != "uatu_the_watcher")
    if not keys:
        failures.append(("roster", "no character yamls found"))
    for k in keys:
        line = _character_one_liner(k)
        if not line or line == k:
            failures.append((f"one_liner[{k}]", f"empty or echo: {line!r}"))

    # 2. Synthetic dict-form diagnosis (the "colon gotcha")
    #    Monkey-patch by writing a temporary in-memory analogue: build the
    #    function's coercion directly using the same code path.
    import yaml as _yaml, tempfile, pathlib
    synthetic = {
        "name": "Test Person",
        "alias": "TP",
        "primary_diagnoses_analog": [
            # Dict-form: yaml parsed `- complex ptsd:` as {"complex ptsd": None}
            {"complex ptsd": None},
            "noise",
        ],
    }
    # Persist as a tmp yaml inside characters dir? No — _character_one_liner
    # only reads files from CHARACTERS_DIR. Inline-test the coercion by
    # writing a temp file ALONGSIDE the real ones.
    tmp_path = CHARACTERS_DIR / "_regression_tmp_colon.yaml"
    try:
        tmp_path.write_text(_yaml.safe_dump(synthetic))
        line = _character_one_liner("_regression_tmp_colon")
        # Expect "Test Person (TP): complex ptsd"
        if "complex ptsd" not in line.lower() or "Test Person" not in line:
            failures.append(("dict-form-coercion",
                            f"unexpected one-liner: {line!r}"))
        else:
            print(f"  PASS dict-form-coercion → {line!r}")
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    # 3. Colon-in-string trimming
    synthetic2 = {
        "name": "Test Two",
        "alias": "T2",
        "primary_diagnoses_analog": [
            "Complex PTSD: subtype where the noise after the colon should drop",
        ],
    }
    tmp_path2 = CHARACTERS_DIR / "_regression_tmp_colon2.yaml"
    try:
        tmp_path2.write_text(_yaml.safe_dump(synthetic2))
        line = _character_one_liner("_regression_tmp_colon2")
        # Expect colon-split: only "Complex PTSD"
        if "subtype" in line.lower():
            failures.append(("colon-split", f"colon noise not dropped: {line!r}"))
        else:
            print(f"  PASS colon-split → {line!r}")
    finally:
        if tmp_path2.exists():
            tmp_path2.unlink()

    # 4. _yaml_to_prompt: handles minimal profile with no alias, no diagnoses
    minimal = {"name": "Minimal Character"}
    try:
        prompt = _yaml_to_prompt(minimal)
        if "Minimal Character" not in prompt:
            failures.append(("yaml_to_prompt-minimal", "name not present in output"))
        else:
            print(f"  PASS _yaml_to_prompt(minimal) — {len(prompt)} chars")
    except Exception as e:
        failures.append(("yaml_to_prompt-minimal", f"{type(e).__name__}: {e}"))

    # 5. _yaml_to_prompt: handles a real profile end-to-end
    import yaml as _y
    wade = _y.safe_load((CHARACTERS_DIR / "wade_wilson.yaml").read_text())
    try:
        prompt = _yaml_to_prompt(wade)
        if "Wade Wilson" not in prompt or "Deadpool" not in prompt:
            failures.append(("yaml_to_prompt-wade", "name/alias missing"))
        else:
            print(f"  PASS _yaml_to_prompt(wade) — {len(prompt)} chars")
    except Exception as e:
        failures.append(("yaml_to_prompt-wade", f"{type(e).__name__}: {e}"))

    if failures:
        print("\nFAILURES:")
        for n, err in failures:
            print(f"  ✗ {n}: {err}")
        return 1
    print("\nITEM 8: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

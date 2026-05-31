"""
PRESSURE-09 — narrator path renders spoken_name (hyphen restored).

Offline. The narrator (Uatu) often drops the hyphen and writes
"Mary Jane" instead of "Mary-Jane". The engine post-processes every
transcript line through normalize_spoken_names to restore the canonical
spoken_name from the character YAML.

Also verifies:
  • mary_jane_watson.yaml carries spoken_name: "Mary-Jane"
  • run_scene wires normalize_spoken_names into transcript assembly
  • _director_instructions surfaces the SPOKEN NAMES block when MJ is
    in the at-open cast (so the narrator agent is told the right
    spelling up-front, belt + braces with the post-process)
"""
from __future__ import annotations
import sys, inspect
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import yaml

from engine.agency_engine import (
    load_spoken_name, normalize_spoken_names,
    run_scene, _director_instructions, SceneSpec,
)


def main() -> int:
    failures: list[str] = []

    # ── A: YAML carries spoken_name: "Mary-Jane" ────────────────────────
    yaml_path = ROOT / "universe" / "characters" / "mary_jane_watson.yaml"
    prof = yaml.safe_load(yaml_path.read_text())
    sn = prof.get("spoken_name", "")
    if sn != "Mary-Jane":
        failures.append(f"A: mary_jane_watson.yaml spoken_name={sn!r}, expected 'Mary-Jane'")
    else:
        print("  PASS A: mary_jane_watson.yaml has spoken_name: 'Mary-Jane'")

    loaded = load_spoken_name("mary_jane_watson")
    if loaded != "Mary-Jane":
        failures.append(f"A: load_spoken_name returned {loaded!r}, expected 'Mary-Jane'")
    else:
        print("  PASS A2: load_spoken_name('mary_jane_watson') -> 'Mary-Jane'")

    # ── B: normalize_spoken_names restores hyphen on a narrator beat ────
    beat = ("The glass door swings wide, catching light, and Mary Jane "
            "steps through — red hair a flare of warning or allure.")
    out = normalize_spoken_names(beat, ["mary_jane_watson", "felicia_hardy", "wade_wilson"])
    if "Mary-Jane" not in out:
        failures.append(f"B: 'Mary-Jane' not present after normalize: {out!r}")
    if "Mary Jane" in out:
        failures.append(f"B: 'Mary Jane' (no hyphen) STILL present after normalize: {out!r}")
    if "Mary-Jane" in out and "Mary Jane" not in out:
        print(f"  PASS B: 'Mary Jane' -> 'Mary-Jane' in narrator beat")
        print(f"          normalized: {out!r}")

    # ── B2: MJ alias also normalizes to canonical narrator spelling ──────
    alias_beat = "Across the room, MJ notices Peter's hand shaking."
    alias_out = normalize_spoken_names(alias_beat, ["mary_jane_watson"])
    if "Mary-Jane" not in alias_out:
        failures.append(f"B2: 'MJ' not normalized to 'Mary-Jane': {alias_out!r}")
    if "MJ" in alias_out:
        failures.append(f"B2: 'MJ' still present after normalize: {alias_out!r}")
    if "Mary-Jane" in alias_out and "MJ" not in alias_out:
        print("  PASS B2: 'MJ' -> 'Mary-Jane' in narrator beat")

    # ── C: a beat that already has the hyphen is unchanged ──────────────
    correct_beat = "Mary-Jane sets the keys on the bar."
    out2 = normalize_spoken_names(correct_beat, ["mary_jane_watson"])
    if out2 != correct_beat:
        failures.append(f"C: already-correct beat was modified: {out2!r}")
    else:
        print("  PASS C: already-correct 'Mary-Jane' is untouched")

    # ── D: run_scene source uses normalize_spoken_names ────────────────
    src = inspect.getsource(run_scene)
    if "normalize_spoken_names" not in src:
        failures.append("D: run_scene source does not call normalize_spoken_names")
    else:
        print("  PASS D: run_scene wires normalize_spoken_names into "
              "transcript assembly")

    # ── E: _director_instructions surfaces SPOKEN NAMES block when MJ
    #       is in the at-open cast ───────────────────────────────────────
    spec = SceneSpec(
        episode_number=1, episode_title="t", act=1, scene_number=1,
        characters=["felicia_hardy", "wade_wilson", "mary_jane_watson"],
        location="booth", time_window="9pm", situation="…",
        previous_recap="cold open",
    )
    dirinstr = _director_instructions(spec, ["FELICIA", "WADE", "MARY-JANE WATSON"])
    if "SPOKEN NAMES" not in dirinstr:
        failures.append("E: _director_instructions missing 'SPOKEN NAMES' block")
    if "Mary-Jane" not in dirinstr:
        failures.append("E: SPOKEN NAMES block does not include 'Mary-Jane'")
    if not any(f.startswith("E:") for f in failures):
        print("  PASS E: _director_instructions surfaces SPOKEN NAMES "
              "block with 'Mary-Jane'")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("  ✗", f)
        print("PRESSURE-09: FAIL")
        return 1
    print("\nPRESSURE-09: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

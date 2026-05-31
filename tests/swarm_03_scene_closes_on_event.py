"""
SWARM-03 — scenes close on state-change, not attendance.

Two probes, both offline (no live model needed for the core logic):

  A) Build a synthetic chronicle with NO state-change events. Confirm
     _is_state_change_event returns False for every entry. The runner's
     gate would refuse [SCENE_END].

  B) Build a synthetic chronicle that includes a TakeAction with a
     non-empty consequence. Confirm _is_state_change_event returns True
     and the gate would honor [SCENE_END].

We probe the helper directly (it is the gate's truth function) AND we
inspect the run_scene source to confirm the gate uses it.
"""
from __future__ import annotations
import sys, inspect
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from engine.agency_engine import _is_state_change_event, run_scene


def main() -> int:
    failures: list[str] = []

    # ── A: flat chronicle (no state-change) ──────────────────────────────
    flat = [
        {"kind": "address", "actor": "felicia_hardy", "key": "wade_wilson"},
        {"kind": "action",  "actor": "wade_wilson",
         "action": "sips tequila", "consequence": "", "tags": ["drinks"]},
        {"kind": "warning", "actor": "engine", "reason": "x"},
    ]
    flat_has = any(_is_state_change_event(e) for e in flat)
    if flat_has:
        failures.append(f"flat chronicle wrongly registered state-change")
    else:
        print("  PASS A: flat chronicle has no state-change events")

    # ── B: chronicle with TakeAction-w-consequence ───────────────────────
    rich_cases = [
        ("TakeAction w/ consequence", {
            "kind": "action", "actor": "wade_wilson",
            "action": "lay my hand on her thigh under the table",
            "consequence": "Felicia does not move it. The line is crossed.",
            "tags": ["lines_crossed"],
        }),
        ("ChangeSetting", {
            "kind": "change_setting", "actor": "felicia_hardy",
            "location": "parking garage", "transition": "we walk out together",
        }),
        ("departure", {
            "kind": "departure", "actor": "engine",
            "who": "WADE WILSON", "reason": "walked out",
        }),
        ("emergent bring_in", {
            "kind": "bring_in", "actor": "felicia_hardy",
            "key": "peter_parker", "how": "I text Peter; he shows.",
        }),
    ]
    for label, entry in rich_cases:
        if not _is_state_change_event(entry):
            failures.append(f"{label} did NOT register as state-change")
        else:
            print(f"  PASS B: {label} is a state-change")

    # ── C: confirm run_scene uses the helper to gate [SCENE_END] ─────────
    src = inspect.getsource(run_scene)
    if "_is_state_change_event" not in src:
        failures.append("run_scene source does not reference _is_state_change_event")
    if "REJECTED" not in src or "NOTHING HAS HAPPENED" not in src:
        failures.append("run_scene source missing state-change rejection branch")
    if "scene_ended and has_progress" not in src and "scene_ended and has_state_change" not in src:
        failures.append("run_scene source missing the (scene_ended AND progress) "
                        "honor branch")
    if "spec.max_turns" not in src:
        failures.append("run_scene source missing defensive max_turns cap")
    else:
        print("  PASS C: run_scene uses _is_state_change_event to gate [SCENE_END]")
        print("  PASS C: run_scene has a defensive spec.max_turns force-close cap")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(f"  ✗ {f}")
        print("SWARM-03: FAIL")
        return 1
    print("\nSWARM-03: PASS — state-change gate is the close mechanism, "
          "with defensive turn cap.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

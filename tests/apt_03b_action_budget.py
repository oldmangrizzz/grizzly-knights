"""
APT-03b: per-scene TakeAction budget.

Verify that TakeAction is capped per scene (default 50), that the
51st call returns the documented error string, and that the tracker
flag actions_budget_exhausted gets set. Also verify the budget is
configurable via register_stage(action_budget=...).
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from engine.scene_tools import (
    register_stage, get_stage, drop_stage, make_scene_tools,
    DEFAULT_ACTION_BUDGET,
)


def main() -> int:
    findings: list[str] = []
    notes: list[str] = []

    # ── default budget = 50 ──────────────────────────────────────────────
    sid = register_stage(present=["felicia_hardy"], roster=["felicia_hardy"])
    stage = get_stage(sid)
    Action = {t.__name__: t for t in make_scene_tools(sid, "felicia_hardy")}["TakeAction"]

    outs = [Action(action=f"sips drink {i}").run() for i in range(DEFAULT_ACTION_BUDGET)]
    over1 = Action(action="one too many").run()
    over2 = Action(action="and another").run()

    accepted = sum(1 for o in outs if o.startswith("Action staged"))
    if accepted != DEFAULT_ACTION_BUDGET:
        findings.append(f"  • only {accepted}/{DEFAULT_ACTION_BUDGET} pre-budget calls succeeded")
    else:
        notes.append(f"  • first {DEFAULT_ACTION_BUDGET} TakeAction calls accepted ✓")

    if over1 != "ERROR: scene action budget exhausted":
        findings.append(f"  • 51st call did not return budget error, got: {over1!r}")
    else:
        notes.append("  • 51st call returned 'ERROR: scene action budget exhausted' ✓")

    if over2 != "ERROR: scene action budget exhausted":
        findings.append(f"  • 52nd call did not return budget error, got: {over2!r}")

    if stage.tracker.get("actions_budget_exhausted") is not True:
        findings.append("  • tracker['actions_budget_exhausted'] not set True")
    else:
        notes.append("  • tracker['actions_budget_exhausted'] = True ✓")

    if stage.tracker["actions"] != DEFAULT_ACTION_BUDGET:
        findings.append(f"  • tracker['actions'] = {stage.tracker['actions']}, expected {DEFAULT_ACTION_BUDGET}")
    else:
        notes.append(f"  • tracker['actions'] = {DEFAULT_ACTION_BUDGET} (no over-bump) ✓")

    chron_actions = [e for e in stage.chronicle if e.get("kind") == "action"]
    if len(chron_actions) != DEFAULT_ACTION_BUDGET:
        findings.append(f"  • chronicle has {len(chron_actions)} action entries, expected {DEFAULT_ACTION_BUDGET}")
    else:
        notes.append(f"  • chronicle holds exactly {DEFAULT_ACTION_BUDGET} action entries ✓")

    drop_stage(sid)

    # ── configurable budget ──────────────────────────────────────────────
    sid2 = register_stage(present=["felicia_hardy"], roster=["felicia_hardy"], action_budget=3)
    stage2 = get_stage(sid2)
    A2 = {t.__name__: t for t in make_scene_tools(sid2, "felicia_hardy")}["TakeAction"]
    for i in range(3):
        A2(action=f"act {i}").run()
    blocked = A2(action="blocked").run()
    if blocked != "ERROR: scene action budget exhausted":
        findings.append(f"  • custom budget=3: 4th call should be blocked, got: {blocked!r}")
    else:
        notes.append("  • configurable action_budget=3 enforced ✓")
    if stage2.tracker.get("actions_budget_exhausted") is not True:
        findings.append("  • custom budget: actions_budget_exhausted not set")
    drop_stage(sid2)

    print("=== NOTES ===")
    for n in notes:
        print(n)
    print()
    if findings:
        print("=== FINDINGS ===")
        for f in findings:
            print(f)
        return 1
    print("HOLDS — TakeAction budget enforced.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

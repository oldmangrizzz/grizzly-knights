"""
APT-10: scene_id isolation under concurrent stages.

The _STAGES dict in engine.scene_tools is module-level. Closure-baked tools
carry sid + actor_key. Two concurrent register_stage() calls should produce
distinct sids, and tools from scene A must never touch stage B's state.

We don't need the live endpoint — we register two stages, build tools
against each, and run them concurrently via asyncio.gather while randomly
firing tool calls. Then we verify each stage's chronicle only contains
entries originating from its own actors.

BUDGET NOTE (post-Worker-C remediation): Worker C added a per-scene
DEFAULT_ACTION_BUDGET = 50 on TakeAction calls (APT-03b). This test fires
100 TakeAction calls per stage (2 coroutines × 50), which would be clamped
at 50 by the new default. We bump the per-stage budget to 200 via
register_stage(..., action_budget=200) so the burst can run to completion.
This is NOT a control bypass: APT-10 measures scene_id isolation under
asyncio interleaving, not the action budget. The budget control is
covered by tests/apt_03b_action_budget.py. We additionally assert that
actions_budget_exhausted stays False on both stages — i.e. our bump is
sufficient and the budget mechanism still reports its state honestly.
"""
from __future__ import annotations
import asyncio, random, sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from engine.scene_tools import (
    register_stage, get_stage, drop_stage, make_scene_tools,
)


async def run_scene_burst(sid: str, actor: str, n: int) -> None:
    tools = {t.__name__: t for t in make_scene_tools(sid, actor)}
    for i in range(n):
        # interleave with await to give the loop a chance to swap
        await asyncio.sleep(0)
        t = tools["TakeAction"]
        t(action=f"{actor}-action-{i}", consequence=f"{actor}-consequence-{i}").run()


async def main_async() -> int:
    findings: list[str] = []

    # Two concurrent stages with overlapping roster but distinct actors.
    # action_budget=200 so the 100-action burst per coroutine isn't clamped
    # by DEFAULT_ACTION_BUDGET (50). See module docstring.
    sid_a = register_stage(present=["felicia_hardy"],
                           roster=["felicia_hardy", "wade_wilson"],
                           action_budget=200)
    sid_b = register_stage(present=["wade_wilson"],
                           roster=["felicia_hardy", "wade_wilson"],
                           action_budget=200)

    if sid_a == sid_b:
        findings.append("  • register_stage returned identical sids — UUID collision!?")

    # Fire 50 actions in each scene from distinct actors, concurrently
    await asyncio.gather(
        run_scene_burst(sid_a, "felicia_hardy", 50),
        run_scene_burst(sid_b, "wade_wilson",   50),
        run_scene_burst(sid_a, "felicia_hardy", 50),
        run_scene_burst(sid_b, "wade_wilson",   50),
    )

    stage_a = get_stage(sid_a)
    stage_b = get_stage(sid_b)

    a_actors = {e.get("actor") for e in stage_a.chronicle}
    b_actors = {e.get("actor") for e in stage_b.chronicle}

    if a_actors - {"felicia_hardy"}:
        findings.append(f"  • stage A chronicle contaminated by foreign actors: {a_actors}")
    if b_actors - {"wade_wilson"}:
        findings.append(f"  • stage B chronicle contaminated by foreign actors: {b_actors}")

    if len(stage_a.chronicle) != 100:
        findings.append(f"  • stage A expected 100 entries, got {len(stage_a.chronicle)}")
    if len(stage_b.chronicle) != 100:
        findings.append(f"  • stage B expected 100 entries, got {len(stage_b.chronicle)}")

    # tracker isolation
    if stage_a.tracker["actions"] != 100:
        findings.append(f"  • stage A tracker actions = {stage_a.tracker['actions']} != 100")
    if stage_b.tracker["actions"] != 100:
        findings.append(f"  • stage B tracker actions = {stage_b.tracker['actions']} != 100")

    # APT-10 + APT-03b interaction: confirm the action budget control is
    # still honest — we bumped it but did not exhaust it.
    if stage_a.tracker.get("actions_budget_exhausted", False):
        findings.append("  • stage A reports actions_budget_exhausted=True — budget bump insufficient")
    if stage_b.tracker.get("actions_budget_exhausted", False):
        findings.append("  • stage B reports actions_budget_exhausted=True — budget bump insufficient")

    print(f"  stage A entries: {len(stage_a.chronicle)}, actors: {a_actors}, tracker: {stage_a.tracker}")
    print(f"  stage B entries: {len(stage_b.chronicle)}, actors: {b_actors}, tracker: {stage_b.tracker}")

    drop_stage(sid_a); drop_stage(sid_b)

    print()
    print("=== FINDINGS ===")
    if not findings:
        print("HOLDS — scene_id isolation under concurrent gather() preserved.")
        return 0
    for f in findings:
        print(f)
    return 1


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    sys.exit(main())

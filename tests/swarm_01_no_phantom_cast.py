"""
SWARM-01 — no phantom cast at scene 1.

Premise: "Felicia and Wade at the Cheesecake Factory worried about
Peter Parker." plan_episode_swarm must return a scene_1 whose `present`
list is EXACTLY {felicia_hardy, wade_wilson}. Peter (mentioned as
worry) does NOT appear. MJ, Johnny, Storm, Ben do NOT appear.

This is a live model call — the planner has to actually obey the rule.
"""
from __future__ import annotations
import sys, time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from engine.uatu import plan_episode_swarm


PREMISE = (
    "Felicia and Wade at the Cheesecake Factory worried about Peter Parker. "
    "Peter has been getting wound up. Anything can happen Tuesday."
)


FORBIDDEN = {"peter_parker", "mary_jane_watson", "johnny_storm",
             "ororo_munroe", "jonathan_storm", "ben_grimm", "sue_storm",
             "reed_richards", "frank_castle"}
REQUIRED  = {"felicia_hardy", "wade_wilson"}


def main() -> int:
    t0 = time.time()
    print(f"[swarm-01] calling plan_episode_swarm(premise=…)")
    plan = plan_episode_swarm(PREMISE)
    dt = time.time() - t0
    present = set(plan.scene_1.present)
    print(f"  title:   {plan.title!r}")
    print(f"  arc:     {plan.arc!r}")
    print(f"  setting: {plan.scene_1.setting!r}")
    print(f"  present: {sorted(present)}  (took {dt:.1f}s)")

    failures: list[str] = []
    missing = REQUIRED - present
    if missing:
        failures.append(f"required present cast missing: {sorted(missing)}")
    leaked = FORBIDDEN & present
    if leaked:
        failures.append(f"phantom cast leaked into scene_1.present: {sorted(leaked)}")
    if len(present) > 3:
        failures.append(f"present cast too large: {len(present)} > 3")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(f"  ✗ {f}")
        print("SWARM-01: FAIL")
        return 1
    print("\nSWARM-01: PASS — scene 1 present is premise-explicit only.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

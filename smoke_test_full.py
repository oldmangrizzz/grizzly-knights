"""
Smoke test: prove the real-Agency engine ACTUALLY fires tools, brings in
characters, takes actions, and breaks something by scene end.

Premise: Felicia and Wade at Cheesecake Factory. Peter shows up worried.
MJ and Johnny arrive separately. Something has to break by scene end.

This test runs ONE scene (no full episode planner; we build a SceneSpec by
hand so the test stays focused on the engine, not the planner). All five
characters are pre-spawned on the Agency. Felicia + Wade are on-stage from
scene open; Peter, MJ, Johnny arrive mid-scene via BringInCharacter.

Assertions:
  • All 5 characters speak at least one line.
  • At least 3 tool calls fire (any kind across any agent).
  • Scene tracker has at least one non-zero field at end.
  • At least one TakeAction with a non-empty `consequence` reached the chronicle.

Prints the full transcript and the tool-call log. No success claim without it.
"""
from __future__ import annotations
import asyncio, sys, json, traceback
from pathlib import Path

from engine.agency_engine import SceneSpec, run_scene, build_model


PREMISE = (
    "Felicia and Wade at Cheesecake Factory. Peter shows up worried. "
    "MJ and Johnny arrive separately. Something has to break by scene end."
)


async def main() -> int:
    model = build_model("gpt-4o")

    spec = SceneSpec(
        episode_number = 0,
        episode_title  = "Smoke Test — Cheesecake Massacre",
        act            = 2,
        scene_number   = 1,
        characters     = ["felicia_hardy", "wade_wilson"],   # on-stage at open
        location       = "Cheesecake Factory, midtown — corner booth by the window",
        time_window    = "Tuesday, 7:48 PM",
        situation      = (
            "Felicia and Wade are already in the booth. Margarita rocks salt for "
            "her, fourth Coors Light for him, an order of avocado eggrolls "
            "between them that neither has touched. They've been here forty "
            "minutes. The actual reason they're meeting hasn't come up yet — "
            "Wade owes Felicia an answer about a job that involves Peter, and "
            "Felicia is the one who has to decide whether to call Peter into "
            "this conversation tonight. Picking up cold."
        ),
        previous_recap = "Cold open — first scene of the test.",
        arrives = [
            {"key": "peter_parker", "when": "early",
             "how": "Felicia texts him; he shows up worried and slides into the booth."},
            {"key": "mary_jane_watson", "when": "mid",
             "how": "MJ arrives separately — Peter called her, she came over from a callback nearby."},
            {"key": "johnny_storm", "when": "mid",
             "how": "Johnny arrives separately — Wade texted him, he flies in from a bar two blocks over."},
        ],
        departs = [],
        escalation = (
            "Something concrete must break by scene end: a confession landed, a "
            "decision made about the job, a fight thrown, a hookup committed, "
            "or somebody walks out. No clean exit. TakeAction with a "
            "`consequence` is the tool that commits it."
        ),
    )

    print("=" * 78)
    print("PREMISE:", PREMISE)
    print("=" * 78)
    print()

    try:
        script = await run_scene(spec, model)
    except Exception as e:
        print("ENGINE EXCEPTION:", type(e).__name__, e)
        traceback.print_exc()
        return 2

    # ── Print transcript ────────────────────────────────────────────────────
    print("─── FULL TRANSCRIPT ───")
    if script.raw.strip():
        print(script.raw)
    else:
        print("(empty)")
    print()

    # ── Print tool-call log ─────────────────────────────────────────────────
    tool_calls = getattr(script, "_gk_tool_calls", []) or []
    tracker    = getattr(script, "_gk_tracker", {}) or {}
    chronicle  = getattr(script, "_gk_chronicle", []) or []

    print("─── TOOL CALL LOG ─────")
    if not tool_calls:
        print("(none)")
    for i, tc in enumerate(tool_calls):
        print(f"[{i:02d}] agent={tc.get('agent')} tool={tc.get('tool')} args={tc.get('args')}")
    print()

    print("─── SCENE TRACKER ─────")
    print(json.dumps(tracker, indent=2))
    print()

    print("─── CHRONICLE (durable beats) ─")
    for c in chronicle:
        print(c)
    print()

    # ── Assertions ──────────────────────────────────────────────────────────
    expected_cast = {"felicia_hardy", "wade_wilson", "peter_parker",
                     "mary_jane_watson", "johnny_storm"}
    speakers = {b.character for b in script.blocks if b.type == "dialogue" and b.character}

    failures: list[str] = []

    missing = expected_cast - speakers
    if missing:
        failures.append(f"NOT ALL CAST SPEAK: missing {sorted(missing)}; spoke {sorted(speakers)}")

    # Count tool calls excluding send_message (which the Director uses for
    # orchestration). We want at least 3 SCENE tools fired across the cast.
    scene_tool_calls = [
        tc for tc in tool_calls
        if tc.get("tool") in {"BringInCharacter", "AddressCharacter", "TakeAction", "ChangeSetting"}
    ]
    if len(scene_tool_calls) < 3:
        failures.append(
            f"FEWER THAN 3 SCENE TOOL CALLS: got {len(scene_tool_calls)} "
            f"(total tool calls of all kinds: {len(tool_calls)})"
        )

    if not any(v > 0 for v in tracker.values()):
        failures.append(f"TRACKER ALL ZERO: {tracker}")

    committed = [c for c in chronicle
                 if c.get("kind") == "action" and c.get("consequence")]
    if not committed:
        failures.append("NO TakeAction WITH CONSEQUENCE COMMITTED TO CHRONICLE")

    print("─── ASSERTIONS ────────")
    if failures:
        print("FAIL:")
        for f in failures:
            print("  •", f)
        return 1
    print("PASS — all assertions satisfied.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

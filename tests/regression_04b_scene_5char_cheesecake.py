"""
Regression item 4b — run_scene 5-char ensemble (cheesecake baseline).

Re-runs the smoke-test premise to confirm no regression after the rebuild.
"""
from __future__ import annotations
from pathlib import Path as _ShimPath
import sys as _shim_sys
_shim_sys.path.insert(0, str(_ShimPath(__file__).parent.parent))
import asyncio, sys, json, time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

from engine.agency_engine import SceneSpec, run_scene, build_model
from tests._scene_assertions import assert_scene


SPEC = SceneSpec(
    episode_number=905,
    episode_title="Regression — Cheesecake Baseline",
    act=2,
    scene_number=1,
    characters=["felicia_hardy", "wade_wilson"],
    location="Cheesecake Factory, midtown — corner booth by the window",
    time_window="Tuesday, 7:48 PM",
    situation=(
        "Felicia and Wade are already in the booth. Margarita rocks salt for "
        "her, fourth Coors Light for him, an order of avocado eggrolls "
        "between them that neither has touched. They've been here forty "
        "minutes. The actual reason they're meeting hasn't come up yet — "
        "Wade owes Felicia an answer about a job that involves Peter, and "
        "Felicia is the one who has to decide whether to call Peter into "
        "this conversation tonight. Picking up cold."
    ),
    previous_recap="Cold open — first scene of the test.",
    arrives=[
        {"key": "peter_parker",      "when": "early",
         "how": "Felicia texts him; he shows up worried and slides into the booth."},
        {"key": "mary_jane_watson",  "when": "mid",
         "how": "MJ arrives separately — Peter called her, she came over from a callback nearby."},
        {"key": "johnny_storm",      "when": "mid",
         "how": "Johnny arrives separately — Wade texted him, he flies in from a bar two blocks over."},
    ],
    departs=[],
    escalation=(
        "Something concrete must break by scene end: a confession landed, a "
        "decision made about the job, a fight thrown, a hookup committed, "
        "or somebody walks out. No clean exit."
    ),
)


async def _run():
    model = build_model("gpt-4o")
    return await run_scene(SPEC, model)


def main() -> int:
    t0 = time.time()
    print(f"[item 4b] running cheesecake 5-char baseline …")
    try:
        script = asyncio.run(_run())
    except Exception as e:
        import traceback
        print(f"ITEM 4b: FAIL — run_scene raised: {type(e).__name__}: {e}")
        traceback.print_exc()
        return 1
    dt = time.time() - t0
    print(f"[item 4b] scene done in {dt:.1f}s — "
          f"{len(script.blocks)} blocks, "
          f"{len(getattr(script,'_gk_tool_calls',[]))} tool calls")

    ok, msgs = assert_scene(script, SPEC, "4b")
    for m in msgs:
        print("  " + m)

    out = REPO_ROOT / "episodes_text" / "_regression_run" / "_item04b_transcript.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(script.raw + "\n\n--- TRACKER ---\n"
                   + json.dumps(getattr(script, '_gk_tracker', {}), indent=2)
                   + "\n\n--- TOOL CALLS ---\n"
                   + json.dumps(getattr(script, '_gk_tool_calls', []),
                                indent=2, default=str))
    print(f"  evidence: {out}")

    if not ok:
        print(f"\nITEM 4b: FAIL  (elapsed {dt:.1f}s)")
        return 1
    print(f"\nITEM 4b: PASS  (elapsed {dt:.1f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

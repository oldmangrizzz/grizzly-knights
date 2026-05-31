"""
Regression item 4a — run_scene with a 2-character intimate premise.

Felicia + Wade. No mid-scene arrivals or departures. The point: confirm a
small cast still hits ≥2 tool calls, both characters speak, no infinite
loop, no [SCENE_END] before coverage.
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
    episode_number=904,
    episode_title="Regression — 2-Char Intimate",
    act=2,
    scene_number=1,
    characters=["felicia_hardy", "wade_wilson"],
    location="Wade's apartment — kitchen, post-midnight",
    time_window="Tuesday, 12:48 AM",
    situation=(
        "Felicia came over after a job that went sideways. Wade is making "
        "instant ramen at the stove in a t-shirt and boxers. She is sitting "
        "on the counter, one boot off, drinking from a bottle of his Coors "
        "Light because the fridge is mostly beer. Neither of them has said "
        "yet whether she is sleeping over. The actual subject they're "
        "circling is whether what happened in the alley two weeks ago "
        "counts as a thing they need to talk about or a thing they both "
        "agreed to forget. Picking up cold, mid-conversation."
    ),
    previous_recap="Cold open — first scene of the test.",
    arrives=[],
    departs=[],
    escalation=(
        "Something concrete must land by scene end: a confession, a kiss, "
        "a hand on a thigh, a fight, or one of them walks out. TakeAction "
        "with a consequence is the tool that commits it."
    ),
)


async def _run():
    model = build_model("gpt-4o")
    return await run_scene(SPEC, model)


def main() -> int:
    t0 = time.time()
    print(f"[item 4a] running 2-char intimate scene …")
    try:
        script = asyncio.run(_run())
    except Exception as e:
        import traceback
        print(f"ITEM 4a: FAIL — run_scene raised: {type(e).__name__}: {e}")
        traceback.print_exc()
        return 1
    dt = time.time() - t0
    print(f"[item 4a] scene done in {dt:.1f}s — "
          f"{len(script.blocks)} blocks, "
          f"{len(getattr(script,'_gk_tool_calls',[]))} tool calls")

    ok, msgs = assert_scene(script, SPEC, "4a")
    for m in msgs:
        print("  " + m)

    out = REPO_ROOT / "episodes_text" / "_regression_run" / "_item04a_transcript.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(script.raw + "\n\n--- TRACKER ---\n"
                   + json.dumps(getattr(script, '_gk_tracker', {}), indent=2)
                   + "\n\n--- TOOL CALLS ---\n"
                   + json.dumps(getattr(script, '_gk_tool_calls', []),
                                indent=2, default=str))
    print(f"  evidence: {out}")

    if not ok:
        print(f"\nITEM 4a: FAIL  (elapsed {dt:.1f}s)")
        return 1
    print(f"\nITEM 4a: PASS  (elapsed {dt:.1f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
Regression item 4c — run_scene where one character DEPARTS mid-scene.

Cast on stage: Jessica Jones, Luke Cage, Matt Murdock.
Matt arrived bleeding to ask a favor, then must DEPART mid-scene
(`departs[]` field) before [SCENE_END].
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
    episode_number=906,
    episode_title="Regression — Departure Scene",
    act=2,
    scene_number=1,
    characters=["jessica_jones", "luke_cage", "matt_murdock"],
    location="Luke's apartment above the bar — Harlem, kitchen",
    time_window="Saturday, 2:12 AM",
    situation=(
        "Matt walked in twenty minutes ago bleeding from a cut above his "
        "left eye, asked Luke for stitches and a favor neither Luke nor "
        "Jess wants to grant. Luke is at the counter cleaning the cut. "
        "Jess is leaning against the refrigerator with a bottle of "
        "Wild Turkey and the contempt of a woman who has been here "
        "before. The favor involves driving Matt back to Hell's Kitchen "
        "so he can finish what he started. Matt does NOT stay for the "
        "rest of this scene — by the time it ends he is back out the door, "
        "with or without the ride."
    ),
    previous_recap="Cold open — first scene of the test.",
    arrives=[],
    departs=[
        {"key": "matt_murdock", "when": "mid",
         "how": "Matt finishes the bourbon Luke handed him, stands up, "
                "and walks back out — the favor either granted or refused."},
    ],
    escalation=(
        "Matt MUST leave the apartment before scene end. Whoever drives him "
        "back (or refuses to) is the line that gets crossed. TakeAction "
        "with a consequence commits the departure."
    ),
)


async def _run():
    model = build_model("gpt-4o")
    return await run_scene(SPEC, model)


def main() -> int:
    t0 = time.time()
    print(f"[item 4c] running departure scene …")
    try:
        script = asyncio.run(_run())
    except Exception as e:
        import traceback
        print(f"ITEM 4c: FAIL — run_scene raised: {type(e).__name__}: {e}")
        traceback.print_exc()
        return 1
    dt = time.time() - t0
    print(f"[item 4c] scene done in {dt:.1f}s — "
          f"{len(script.blocks)} blocks, "
          f"{len(getattr(script,'_gk_tool_calls',[]))} tool calls")

    ok, msgs = assert_scene(script, SPEC, "4c", allow_departure=True)
    for m in msgs:
        print("  " + m)

    out = REPO_ROOT / "episodes_text" / "_regression_run" / "_item04c_transcript.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(script.raw + "\n\n--- TRACKER ---\n"
                   + json.dumps(getattr(script, '_gk_tracker', {}), indent=2)
                   + "\n\n--- TOOL CALLS ---\n"
                   + json.dumps(getattr(script, '_gk_tool_calls', []),
                                indent=2, default=str))
    print(f"  evidence: {out}")

    if not ok:
        print(f"\nITEM 4c: FAIL  (elapsed {dt:.1f}s)")
        return 1
    print(f"\nITEM 4c: PASS  (elapsed {dt:.1f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

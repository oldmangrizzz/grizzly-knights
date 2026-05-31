"""
PRESSURE-18 — open pressure means planner done:true forces continuation.

Offline. Stub Uatu's next-scene model to return {done:true}. An unresolved
subject-bound pressure must still return a SceneSpec, not None.
"""
from __future__ import annotations
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from engine.agency_engine import Pressure  # noqa: E402
import engine.uatu as uatu  # noqa: E402
from engine.uatu import EpisodeArc  # noqa: E402


class _Resp:
    final_output = '{"done": true, "reason": "model tried to close"}'


class _StubUatu:
    async def get_response(self, cue: str):
        return _Resp()


def main() -> int:
    failures: list[str] = []
    p = Pressure(
        name="peter_parker_snapping",
        what_it_demands="Peter Parker must be confronted on-stage about the snapping point.",
        subject_character_ids=["peter_parker"],
        resolution_modes=["BringInCharacter(peter_parker)", "named refusal"],
        evidence_of_progress=["peter", "snapping"],
        resolved=False,
    )
    arc = EpisodeArc(
        title="Planner None Cannot Close",
        logline="Open pressure survives the model close.",
        arc="Felicia and Wade must force Peter's unresolved pressure on-stage.",
        opening_situation="booth",
        setting="Cheesecake Factory booth",
        time="Tuesday afternoon",
        present=["felicia_hardy", "wade_wilson"],
        forcing_pressures=[p],
        tone_floor="Marvel Knights",
    )

    original = uatu._uatu_agent
    uatu._uatu_agent = lambda mode, model: _StubUatu()
    try:
        result = asyncio.run(uatu._plan_next_scene_arc_async(
            arc,
            prior_chronicle=[{"kind": "change_setting", "location": "Cheesecake Factory booth"}],
            prior_present=["felicia_hardy", "wade_wilson"],
            model=object(),
            episode_so_far="",
            scenes_run=2,
        ))
    finally:
        uatu._uatu_agent = original

    print(f"  result={result}")
    if result is None:
        failures.append("planner returned None while pressure remained open")
    else:
        if "peter_parker" not in result.present:
            failures.append(f"peter_parker missing from present: {result.present}")
        if "continuation" not in result.situation.lower():
            failures.append(f"situation lacks continuation cue: {result.situation!r}")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("  ✗", f)
        print("PRESSURE-18: FAIL")
        return 1
    print("\nPRESSURE-18: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

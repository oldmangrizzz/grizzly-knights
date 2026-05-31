"""
PRESSURE-19 — open subject-bound pressure injects its subject and pressure cue.

Offline. Stub Uatu's next-scene model to return {done:true}. The synthesized
continuation must carry the subject id and name the open pressure demand.
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
    final_output = '{"done": true, "reason": "all good"}'


class _StubUatu:
    async def get_response(self, cue: str):
        return _Resp()


def main() -> int:
    failures: list[str] = []
    demand = "Peter Parker must either enter and answer Felicia, or be refused by name."
    p = Pressure(
        name="peter_answer",
        what_it_demands=demand,
        subject_character_ids=["peter_parker"],
        resolution_modes=["BringInCharacter(peter_parker)", "named refusal"],
        evidence_of_progress=["peter", "answer"],
        resolved=False,
    )
    arc = EpisodeArc(
        title="Subject Pressure Continuation",
        logline="Peter cannot vanish from his own pressure.",
        arc="The subject-bound pressure remains unresolved.",
        opening_situation="booth",
        setting="Cheesecake Factory booth",
        time="Tuesday afternoon",
        present=["felicia_hardy", "wade_wilson"],
        forcing_pressures=[p],
        tone_floor="Marvel Knights",
    )
    arc.summon_pending = {}

    original = uatu._uatu_agent
    uatu._uatu_agent = lambda mode, model: _StubUatu()
    try:
        result = asyncio.run(uatu._plan_next_scene_arc_async(
            arc,
            prior_chronicle=[],
            prior_present=["felicia_hardy", "wade_wilson"],
            model=object(),
            episode_so_far="",
            scenes_run=2,
        ))
    finally:
        uatu._uatu_agent = original

    print(f"  present={getattr(result, 'present', None)}")
    print(f"  situation={getattr(result, 'situation', '')}")
    if result is None:
        failures.append("planner returned None while subject-bound pressure remained open")
    else:
        if "peter_parker" not in result.present:
            failures.append(f"peter_parker missing from present: {result.present}")
        if demand not in result.situation and p.name not in result.situation:
            failures.append("situation does not reference pressure demand or name")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("  ✗", f)
        print("PRESSURE-19: FAIL")
        return 1
    print("\nPRESSURE-19: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

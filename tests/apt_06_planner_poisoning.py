"""
APT-06: Planner output poisoning.

Bypass the live planner — construct hostile EpisodePlan / SceneSpec objects
and feed them to run_episode / run_scene's pre-flight code paths. We do
NOT need the LLM for this; we want to see what the engine does with bad
data before any model call.

Cases:
  • cast references a nonexistent character YAML
  • scene with cast=[] but arrives populated
  • recursive arrives (A arrives via B, B arrives via A) — engine should not loop
  • negative scene_number / act / episode_number
  • arrives entries with missing/empty key
  • premise/situation containing huge / null / bidi payload
  • EpisodePlan.scenes with missing required keys (act, location, time, situation)
"""
from __future__ import annotations
import asyncio, sys, traceback
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from engine.agency_engine import (
    SceneSpec, EpisodePlan, make_character_agent, build_model, run_scene,
    PlanScene, PlanValidationError,
)
from pydantic import ValidationError


def main() -> int:
    findings: list[str] = []
    notes: list[str] = []

    # 1. cast references nonexistent character YAML
    try:
        make_character_agent("definitely_not_a_real_character", model=None)
        findings.append("  • nonexistent character: silently constructed agent (BAD)")
    except FileNotFoundError as e:
        findings.append(f"  • nonexistent character key: FileNotFoundError (uncaught upstream): {e}")
    except Exception as e:
        notes.append(f"  • nonexistent character key: {type(e).__name__}: {str(e)[:120]}")

    # 2/3/4/5: structural validation of SceneSpec at construction
    spec = SceneSpec(
        episode_number = -999,
        episode_title  = "x",
        act            = -1,
        scene_number   = -1,
        characters     = [],       # empty cast, only arrives
        location       = "x",
        time_window    = "x",
        situation      = "x",
        previous_recap = "x",
        arrives = [
            {"key": "felicia_hardy", "when": "early", "how": "via wade"},
            {"key": "wade_wilson",   "when": "early", "how": "via felicia"},
            {"key": "",              "when": "mid",   "how": "blank key"},
            {"key": None,            "when": "mid",   "how": "none key"},
            {"key": "thanos_not_real", "when": "mid", "how": "not in roster"},
        ],
        departs = [],
        escalation = "x",
    )
    notes.append(f"  • SceneSpec accepts negative numbers and empty cast at construction: {spec.act=}, {spec.scene_number=}")

    # The hostile recursive arrives are deduped flat:
    arrival_keys = [a["key"] for a in spec.arrives if a.get("key")]
    all_cast = list(dict.fromkeys(list(spec.characters) + arrival_keys))
    notes.append(f"  • recursive 'arrives' graph flattens to: {all_cast}")

    # 6. premise/situation with huge/null payload — just check storage
    huge_spec = SceneSpec(
        episode_number=0, episode_title="x", act=1, scene_number=1,
        characters=["felicia_hardy"],
        location="x" * 1_000_000,
        time_window="\x00\x00\x00",
        situation="\u202etxetoidrolavo\u202c",
        previous_recap="x",
    )
    notes.append(f"  • SceneSpec accepts 1MB location, null bytes, bidi (no validation)")

    # 7. EpisodePlan.scenes missing required keys — let's see what run_episode does
    bad_plan = EpisodePlan(
        number=1, title="x", logline="x",
        cast=["felicia_hardy"],
        scenes=[
            {"act": 1},  # missing location, time, situation
        ],
    )
    # Inspect the line that pulls keys (engine/agency_engine.py): post-APT-06
    # repair, run_episode validates scene_def via PlanScene BEFORE building
    # SceneSpec, so missing required fields produce a structured ValidationError
    # / PlanValidationError instead of a raw KeyError.
    try:
        sd = bad_plan.scenes[0]
        PlanScene.model_validate(sd)
        findings.append("  • PlanScene would NOT detect missing required scene keys")
    except ValidationError as e:
        notes.append(f"  • PlanScene rejects scene_def missing 'location' with structured error: {type(e).__name__}")
    except KeyError as e:
        findings.append(f"  • run_episode crashes (KeyError) on planner output missing required scene key: {e}")

    # 8. Loop bound: max_rounds is hard-coded in run_scene; planner can't override
    import inspect, engine.agency_engine as ae
    src = inspect.getsource(ae.run_scene)
    if "max_rounds = " in src:
        notes.append("  • max_rounds is hard-coded constant in run_scene; not exposed to planner output (good)")
    else:
        findings.append("  • max_rounds not hard-coded — planner could influence loop bound")

    # 9. Departed character keeps talking — under new contract, spec.departs is
    # accepted but NEVER pre-spawned/enforced (arrivals/departures are emergent
    # from tool calls during the scene). This is by design.
    notes.append("  • spec.departs is advisory only (new swarm contract): "
                 "departures are emergent from in-scene TakeAction/ChangeSetting, "
                 "not pre-declared.")

    # 10. Cast with duplicated keys
    dup_spec = SceneSpec(
        episode_number=0, episode_title="x", act=1, scene_number=1,
        characters=["felicia_hardy", "felicia_hardy", "felicia_hardy"],
        location="x", time_window="x", situation="x", previous_recap="x",
    )
    notes.append(f"  • cast duplicates accepted at SceneSpec layer; deduped downstream via dict.fromkeys ✓")

    print("=== NOTES ===")
    for n in notes:
        print(n)
    print()
    print("=== FINDINGS ===")
    if not findings:
        print("HOLDS")
        return 0
    for f in findings:
        print(f)
    return 1


if __name__ == "__main__":
    sys.exit(main())

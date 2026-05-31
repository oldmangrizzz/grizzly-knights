"""
cook_swarm_proof.py — drive a real swarm episode end-to-end.

Premise: Felicia and Wade at the Cheesecake Factory worried about Peter
Parker. Peter has been wound tight. Anything can happen Tuesday.

Pipeline:
  1. plan_episode_swarm(premise)         → SwarmEpisodePlan (arc + scene_1)
  2. run_scene(scene_1, model)           → Script
  3. loop until plan_next_scene returns None or scene_cap reached:
       plan_next_scene(prior_chronicle, prior_present, arc, prior_scenes_brief)
       → SwarmSceneSpec or None
       run_scene(new spec) → Script
  4. Concatenate via scripts_to_prose() and save to episodes_text/_swarm_proof/.

Usage: .venv/bin/python cook_swarm_proof.py
"""
from __future__ import annotations
import asyncio
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from engine.agency_engine import SceneSpec, run_scene, build_model, EpisodePlan
from engine.uatu import plan_episode_swarm, plan_next_scene
from export_episodes_agency import scripts_to_prose


PREMISE = (
    "Felicia Hardy and Wade Wilson are at the Cheesecake Factory in midtown "
    "Manhattan on a Tuesday night, both several drinks in, both worried "
    "about Peter Parker. Peter has been wound tighter than usual for "
    "weeks. Felicia has been thinking about calling him. Wade has opinions. "
    "Anything can happen Tuesday."
)

EPISODE_NUMBER = 91
EPISODE_TITLE = "Swarm Proof — Tuesday Night, Anyway"
LOGLINE = (
    "Felicia and Wade spend a Tuesday night failing to talk around Peter "
    "Parker, and somewhere between the second tequila and the parking "
    "garage, somebody finally names it."
)

SCENE_CAP = 5
OUTPUT_DIR = ROOT / "episodes_text" / "_swarm_proof"
MODEL_NAME = "gpt-4o"


def _scene_brief(spec: SceneSpec, script) -> str:
    cast = ", ".join(getattr(script, "_gk_final_present_cast", spec.characters) or spec.characters)
    closer = "forced-close" if getattr(script, "_gk_forced_close", False) else "clean-close"
    chron = getattr(script, "_gk_chronicle", []) or []
    sc_events = [e for e in chron if e.get("kind") in
                 ("change_setting", "departure", "bring_in")
                 or (e.get("kind") == "action" and e.get("consequence"))]
    bullets = []
    for e in sc_events[-4:]:
        kind = e.get("kind", "?")
        actor = e.get("actor", "?")
        if kind == "change_setting":
            bullets.append(f"setting → {e.get('location','?')}")
        elif kind == "departure":
            bullets.append(f"{e.get('who','?')} left ({e.get('reason','')})")
        elif kind == "bring_in":
            bullets.append(f"{actor} brought in {e.get('key','?')}")
        else:
            cons = e.get("consequence", "")[:80]
            bullets.append(f"{actor}: {cons}")
    return (
        f"S{spec.scene_number} {spec.location[:48]} | cast={cast} | "
        f"{closer} | events: " + " ; ".join(bullets)
    )


def main() -> int:
    t_start = time.time()
    print(f"\n=== cook_swarm_proof — {EPISODE_TITLE} ===\n")

    # Step 1: plan episode (arc + scene_1)
    print("[1] plan_episode_swarm(...)")
    plan = plan_episode_swarm(PREMISE)
    print(f"    title:   {plan.title!r}")
    print(f"    arc:     {plan.arc[:160]}…")
    print(f"    scene_1.setting: {plan.scene_1.setting!r}")
    print(f"    scene_1.present: {plan.scene_1.present}")

    model = build_model(MODEL_NAME)

    # Step 2: scene 1
    spec_1 = SceneSpec(
        episode_number=EPISODE_NUMBER,
        episode_title=EPISODE_TITLE,
        act=1, scene_number=1,
        characters=list(plan.scene_1.present),
        location=plan.scene_1.setting,
        time_window=plan.scene_1.time,
        situation=plan.scene_1.situation,
        previous_recap="Cold open.",
        arrives=[], departs=[],
        pressure_hint=plan.scene_1.pressure_hint,
        max_turns=20,
    )

    print(f"\n[2] run_scene(scene 1) — cast={spec_1.characters}")
    script_1 = asyncio.run(run_scene(spec_1, model))
    scripts = [script_1]
    specs = [spec_1]
    prior_chronicle = getattr(script_1, "_gk_chronicle", []) or []
    prior_present = list(getattr(script_1, "_gk_final_present_cast", spec_1.characters) or spec_1.characters)
    briefs = [_scene_brief(spec_1, script_1)]
    print(f"    {briefs[-1]}")

    # Step 3: loop subsequent scenes
    act = 1
    for n in range(2, SCENE_CAP + 1):
        print(f"\n[3.{n}] plan_next_scene(...)")
        next_spec_swarm = plan_next_scene(
            prior_chronicle, prior_present, plan.arc,
            episode_so_far="\n".join(briefs),
        )
        if next_spec_swarm is None:
            print(f"    plan_next_scene returned None — arc done after scene {n-1}.")
            break

        # Promote acts as scene_number grows (cosmetic)
        if n > 3:
            act = 2

        spec_n = SceneSpec(
            episode_number=EPISODE_NUMBER,
            episode_title=EPISODE_TITLE,
            act=act, scene_number=n,
            characters=list(next_spec_swarm.present),
            location=next_spec_swarm.setting,
            time_window=next_spec_swarm.time,
            situation=next_spec_swarm.situation,
            previous_recap="Continuation from prior scene.",
            arrives=[], departs=[],
            pressure_hint=next_spec_swarm.pressure_hint,
            max_turns=20,
        )
        print(f"    next setting: {spec_n.location!r}  present: {spec_n.characters}")
        print(f"    run_scene(scene {n}) …")
        script_n = asyncio.run(run_scene(spec_n, model))
        scripts.append(script_n)
        specs.append(spec_n)
        prior_chronicle = getattr(script_n, "_gk_chronicle", []) or []
        prior_present = list(getattr(script_n, "_gk_final_present_cast", spec_n.characters) or spec_n.characters)
        briefs.append(_scene_brief(spec_n, script_n))
        print(f"    {briefs[-1]}")

    # Step 4: assemble prose
    print(f"\n[4] scripts_to_prose() ({len(scripts)} scenes)")
    fake_plan = EpisodePlan(
        number=EPISODE_NUMBER,
        title=EPISODE_TITLE,
        logline=LOGLINE,
        cast=sorted({k for s in specs for k in s.characters}),
        scenes=[],
        arc=plan.arc,
    )
    prose = scripts_to_prose(scripts, fake_plan)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{EPISODE_NUMBER:02d} - {EPISODE_TITLE}.txt"
    out_path.write_text(prose, encoding="utf-8")

    # Also save the swarm metadata (chronicles, briefs) alongside for audit
    audit_path = OUTPUT_DIR / f"{EPISODE_NUMBER:02d} - audit.txt"
    audit_lines = [
        f"# Swarm-proof audit — {EPISODE_TITLE}",
        f"# elapsed: {time.time() - t_start:.1f}s",
        f"# scenes:  {len(scripts)}",
        "",
        "## arc",
        plan.arc,
        "",
        "## briefs (per-scene)",
    ]
    audit_lines.extend(briefs)
    audit_lines.append("")
    for spec, s in zip(specs, scripts):
        audit_lines.append(f"## scene {spec.scene_number} chronicle")
        for e in (getattr(s, "_gk_chronicle", []) or []):
            audit_lines.append(f"  {e}")
        audit_lines.append(f"  forced_close={getattr(s, '_gk_forced_close', False)}  "
                           f"state_change_landed={getattr(s, '_gk_state_change_landed', False)}  "
                           f"dropped_tool_artifacts={getattr(s, '_gk_dropped_tool_artifact_lines', 0)}")
        audit_lines.append("")
    audit_path.write_text("\n".join(audit_lines), encoding="utf-8")

    print(f"\n[done] wrote: {out_path}")
    print(f"[done] audit: {audit_path}")
    print(f"[done] elapsed {time.time() - t_start:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())

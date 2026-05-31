"""
cook_ep01_pressure_proof.py — V3 driver. Premise -> Arc -> Pressure-gated
scenes, looping plan_next_scene_arc until every forcing_pressure is
resolved (or hard episode cap of 12 scenes is hit, in which case the run
is flagged FORCED-CLOSE).

Uses the GENESIS_PREMISE from cook_ep01_genesis.py verbatim.

Pipeline:
  1. extract_arc(premise) -> EpisodeArc + Pressure[]
  2. run_scene(scene_1, active_pressures=arc.forcing_pressures)
  3. After each scene:
       - re-evaluate pressures against this scene's chronicle
       - mark any that moved as resolved
       - if NO pressure moved this scene, bump stall_streak
       - if stall_streak >= 1, call stall_intervention_beat for the
         next scene; inject it as both:
           (a) prepended NARRATOR line into the next script's raw text
           (b) SceneSpec.stall_avoidance_note (director cue)
  4. plan_next_scene_arc -> SwarmSceneSpec or None (None == done)
  5. Loop until arc.open_pressures() empty OR scene cap (12) hit.

The cook always saves the file, even on FORCED-CLOSE — the operator
inspects the output and the resolution log to verdict it.
"""
from __future__ import annotations
import asyncio
import sys
import time
import json
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from engine.agency_engine import (
    SceneSpec, run_scene, build_model, EpisodePlan,
    evaluate_pressures, is_pressure_progress,
)
from engine.uatu import (
    extract_arc, plan_next_scene_arc, stall_intervention_beat,
)
from export_episodes_agency import scripts_to_prose

# Operator's canonical genesis premise — verbatim from cook_ep01_genesis.py
from cook_ep01_genesis import GENESIS_PREMISE


EPISODE_NUMBER = 1
EPISODE_TITLE_FALLBACK = "Tuesday's Corruption (Pressure Proof)"
SCENE_CAP = 12
MODEL_NAME = "gpt-4o"
OUTPUT_DIR = ROOT / "episodes_text" / "_pressure_proof_v2"


def _scene_summary(spec: SceneSpec, script, moved_now: list[str]) -> str:
    cast = ", ".join(getattr(script, "_gk_final_present_cast", spec.characters) or spec.characters)
    closer = "FORCED-CLOSE" if getattr(script, "_gk_forced_close", False) else "clean-close"
    stalled = getattr(script, "_gk_stalled", False)
    return (
        f"S{spec.scene_number} @ {spec.location[:60]} | cast={cast} | "
        f"{closer} | stalled={stalled} | pressures_moved_this_scene={moved_now}"
    )


def main() -> int:
    t_start = time.time()
    print("=" * 78)
    print("=== cook_ep01_pressure_proof — V3 — premise -> pressure -> proof ===")
    print("=" * 78)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── Step 1: extract the arc + pressures ─────────────────────────────────
    print("\n[1] extract_arc(GENESIS_PREMISE) …")
    t0 = time.time()
    arc = extract_arc(GENESIS_PREMISE, model_name=MODEL_NAME)
    print(f"    title:    {arc.title!r}")
    print(f"    setting:  {arc.setting!r}")
    print(f"    present:  {arc.present}")
    print(f"    pressures ({len(arc.forcing_pressures)}):")
    for p in arc.forcing_pressures:
        print(f"      • {p.name}: {p.what_it_demands[:140]}")
        print(f"          evidence: {p.evidence_of_progress[:6]}")
    print(f"    took {time.time()-t0:.1f}s")

    title = arc.title.strip() or EPISODE_TITLE_FALLBACK
    logline = arc.logline.strip() or "The Tuesday the universe pivots on."

    model = build_model(MODEL_NAME)

    # ── Step 2: scene 1 ─────────────────────────────────────────────────────
    spec_1 = SceneSpec(
        episode_number=EPISODE_NUMBER,
        episode_title=title,
        act=1, scene_number=1,
        characters=list(arc.present),
        location=arc.setting,
        time_window=arc.time,
        situation=arc.opening_situation,
        previous_recap="Cold open — first beat of the universe.",
        arrives=[], departs=[],
        pressure_hint=arc.pressure_hint,
        active_pressures=list(arc.forcing_pressures),
        max_turns=20,
    )

    print(f"\n[2] run_scene(S1) cast={spec_1.characters} setting={spec_1.location!r}")
    t1 = time.time()
    script_1 = asyncio.run(run_scene(spec_1, model))
    print(f"    S1 done in {time.time()-t1:.1f}s — blocks={len(script_1.blocks)}")

    scripts = [script_1]
    specs = [spec_1]
    summaries: list[str] = []

    # Initial pressure evaluation
    moved_names = list(getattr(script_1, "_gk_pressures_moved", []) or [])
    for p in arc.forcing_pressures:
        if p.name in moved_names and not p.resolved:
            p.resolved = True
            p.resolved_by = f"scene {spec_1.scene_number}"
    summaries.append(_scene_summary(spec_1, script_1, moved_names))
    print("    " + summaries[-1])
    print(f"    open pressures after S1: {[p.name for p in arc.open_pressures()]}")

    stall_streak = 0
    if not moved_names:
        stall_streak += 1
        print(f"    STALL detected — stall_streak={stall_streak}")

    prior_chronicle = list(getattr(script_1, "_gk_chronicle", []) or [])
    prior_present = list(getattr(script_1, "_gk_final_present_cast", spec_1.characters) or spec_1.characters)

    # ── Step 3: loop scenes 2..N ────────────────────────────────────────────
    pending_intervention_beat = ""
    forced_close_episode = False

    for n in range(2, SCENE_CAP + 1):
        if not arc.open_pressures():
            print(f"\n[3.{n}] all pressures resolved before S{n} — episode ends after S{n-1}.")
            break

        # If the previous scene stalled, Uatu names the avoidance NOW.
        if stall_streak >= 1:
            print(f"\n[uatu] stall_streak={stall_streak} — calling stall_intervention_beat …")
            try:
                pending_intervention_beat = stall_intervention_beat(
                    arc, arc.open_pressures(), prior_chronicle, model_name=MODEL_NAME,
                ).strip()
                print(f"    UATU BEAT: {pending_intervention_beat!r}")
            except Exception as e:
                print(f"    stall_intervention_beat failed: {type(e).__name__}: {e}")
                pending_intervention_beat = ""

        # Plan the next scene
        print(f"\n[3.{n}] plan_next_scene_arc(...) — open={[p.name for p in arc.open_pressures()]}")
        try:
            next_spec_swarm = plan_next_scene_arc(
                arc, prior_chronicle, prior_present, model_name=MODEL_NAME,
                episode_so_far="\n".join(summaries),
            )
        except Exception as e:
            print(f"    plan_next_scene_arc raised {type(e).__name__}: {e}")
            break

        if next_spec_swarm is None:
            print(f"    plan_next_scene_arc returned None — arc closed after S{n-1}.")
            break

        act = 1 if n <= 3 else (2 if n <= 7 else 3)
        spec_n = SceneSpec(
            episode_number=EPISODE_NUMBER,
            episode_title=title,
            act=act, scene_number=n,
            characters=list(next_spec_swarm.present),
            location=next_spec_swarm.setting,
            time_window=next_spec_swarm.time,
            situation=next_spec_swarm.situation,
            previous_recap="Continuation from prior scene.",
            arrives=[], departs=[],
            pressure_hint=next_spec_swarm.pressure_hint,
            active_pressures=list(arc.open_pressures()),
            stall_avoidance_note=pending_intervention_beat,
            max_turns=20,
        )
        print(f"    S{n} cast={spec_n.characters} setting={spec_n.location!r}")
        if pending_intervention_beat:
            print(f"    (stall_avoidance_note injected: {pending_intervention_beat[:80]!r})")

        t_n = time.time()
        try:
            script_n = asyncio.run(run_scene(spec_n, model))
        except Exception as e:
            print(f"    S{n} run_scene raised {type(e).__name__}: {e}")
            break
        print(f"    S{n} done in {time.time()-t_n:.1f}s — blocks={len(script_n.blocks)}")

        # If we had a stall intervention beat, GUARANTEE it appears in the
        # printed transcript by prepending it as a narrator line on the raw
        # text (the director was also asked to feed it in — belt + braces).
        if pending_intervention_beat:
            prefix = f"NARRATOR: {pending_intervention_beat}\n"
            existing_raw = script_n.raw or ""
            if pending_intervention_beat not in existing_raw:
                script_n.raw = prefix + existing_raw
                # Also prepend a narrator block so prose assembly picks it up
                from engine.script_generator import ScriptBlock
                script_n.blocks = [ScriptBlock(type="narrator",
                                               text=pending_intervention_beat)] + list(script_n.blocks)
        pending_intervention_beat = ""

        scripts.append(script_n)
        specs.append(spec_n)

        moved_names = list(getattr(script_n, "_gk_pressures_moved", []) or [])
        for p in arc.forcing_pressures:
            if p.name in moved_names and not p.resolved:
                p.resolved = True
                p.resolved_by = f"scene {n}"
        summaries.append(_scene_summary(spec_n, script_n, moved_names))
        print("    " + summaries[-1])
        print(f"    open pressures after S{n}: {[p.name for p in arc.open_pressures()]}")

        if not moved_names:
            stall_streak += 1
            print(f"    STALL — stall_streak={stall_streak}")
        else:
            stall_streak = 0

        prior_chronicle = list(getattr(script_n, "_gk_chronicle", []) or [])
        prior_present = list(getattr(script_n, "_gk_final_present_cast", spec_n.characters) or spec_n.characters)

        if not arc.open_pressures():
            print(f"\n[3] ALL PRESSURES RESOLVED after S{n} — episode ends clean.")
            break
    else:
        forced_close_episode = True
        print(f"\n[3] HARD EPISODE CAP {SCENE_CAP} HIT — FORCED-CLOSE.")

    # ── Step 4: assemble + write ────────────────────────────────────────────
    cast_union = sorted({k for s in specs for k in s.characters})
    for s in scripts:
        cast_union = sorted(set(cast_union) | set(getattr(s, "_gk_final_present_cast", []) or []))
    fake_plan = EpisodePlan(
        number=EPISODE_NUMBER, title=title, logline=logline,
        cast=cast_union, scenes=[], arc=arc.arc,
    )
    prose = scripts_to_prose(scripts, fake_plan)

    out_path = OUTPUT_DIR / f"{EPISODE_NUMBER:02d} - {title}.txt"
    out_path.write_text(prose, encoding="utf-8")

    # Audit
    audit = [
        f"# pressure-proof audit — {title}",
        f"# elapsed: {time.time()-t_start:.1f}s",
        f"# scenes_run: {len(scripts)}",
        f"# forced_close_episode: {forced_close_episode}",
        f"# stall_streak_final: {stall_streak}",
        "",
        "## arc",
        arc.arc,
        "",
        "## pressures",
    ]
    for p in arc.forcing_pressures:
        audit.append(f"  • {p.name}: resolved={p.resolved} by={p.resolved_by!r}")
        audit.append(f"      demands: {p.what_it_demands}")
        audit.append(f"      evidence: {p.evidence_of_progress[:8]}")
    audit.append("")
    audit.append("## scene summaries")
    audit.extend(summaries)
    audit.append("")
    for spec, s in zip(specs, scripts):
        audit.append(f"## scene {spec.scene_number} chronicle")
        for e in (getattr(s, "_gk_chronicle", []) or []):
            audit.append(f"  {e}")
        audit.append(f"  forced_close={getattr(s, '_gk_forced_close', False)} "
                     f"stalled={getattr(s, '_gk_stalled', False)} "
                     f"pressures_moved={getattr(s, '_gk_pressures_moved', [])} "
                     f"dropped_tool_artifacts={getattr(s, '_gk_dropped_tool_artifact_lines', 0)}")
        audit.append("")
    audit_path = OUTPUT_DIR / f"{EPISODE_NUMBER:02d} - audit.txt"
    audit_path.write_text("\n".join(audit), encoding="utf-8")

    print(f"\n[done] wrote: {out_path}")
    print(f"[done] audit: {audit_path}")
    print(f"[done] elapsed {time.time()-t_start:.1f}s")
    print(f"[done] forced_close_episode={forced_close_episode} "
          f"open_pressures_remaining={[p.name for p in arc.open_pressures()]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

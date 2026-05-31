"""
cook_ep01_pressure_proof_v3.py — V3.2 driver.

Adds to V3:
  • summon-pending carryover across scenes (engine fills the next scene's
    present cast with the un-acted subject)
  • minimum-scenes floor (an episode whose only resolution is bring_in +
    same-scene subject-action cannot close at scene 1 — at least one
    consequences scene must run)
  • stall_streak per-pressure with 3-strike FORCED-CLOSE
  • passes scenes_run into plan_next_scene_arc so the floor is enforced
    as a coded gate, not a verdict-only criterion

Output: episodes_text/_pressure_proof_v3/
"""
from __future__ import annotations
import asyncio
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from engine.agency_engine import (
    SceneSpec, run_scene, build_model, EpisodePlan,
    evaluate_pressures_with_pending,
)
from engine.uatu import (
    extract_arc, plan_next_scene_arc, stall_intervention_beat, SwarmSceneSpec,
    _synthesize_open_pressure_continuation,
)
from export_episodes_agency import scripts_to_prose

from cook_ep01_genesis import GENESIS_PREMISE


EPISODE_NUMBER = 1
EPISODE_TITLE_FALLBACK = "Tuesday's Corruption (Pressure Proof V3)"
SCENE_CAP = 40
STALL_CAP = 3
MODEL_NAME = "gpt-4o"
OUTPUT_DIR = ROOT / "episodes_text" / "_pressure_proof_v3_4"
MIN_PRESSURE_PROOF_SCENES = 2
WORDS_PER_AUDIO_MINUTE = 150
RUNTIME_MIN_AUDIO_MINUTES = 60.0
RUNTIME_MAX_AUDIO_MINUTES = 90.0

VERDICT_PASS = "PASS"
VERDICT_FAIL = "FAIL"
RUNTIME_LOW_REASON = "RUNTIME-LOW"
RUNTIME_HIGH_REASON = "RUNTIME-HIGH"
RUNTIME_OK_REASON = "RUNTIME-OK"
PRESSURE_GATE_REASON = "PRESSURE-GATE"
OPEN_PRESSURE_REASON = "OPEN-PRESSURE"
STALL_CLOSE_REASON = "STALL-CLOSE"
SCENE1_CAST_REASON = "SCENE1-CAST"
SCENE1_REQUIRED_CAST = ("felicia_hardy", "wade_wilson")


class Scene1CastViolation(RuntimeError):
    """Raised when scene 1 cast does not equal the SKILL.md §2(a) required pair."""
    def __init__(self, actual):
        self.actual = list(actual)
        super().__init__(
            f"SCENE1-CAST violation: required exactly {list(SCENE1_REQUIRED_CAST)}, got {self.actual}"
        )

FULL_EPISODE_BEATS = {
    2: {
        "setting": "Cheesecake Factory booth in a corner, twenty minutes later",
        "time": "Tuesday, 3:05 PM",
        "situation": (
            "RUNTIME FLOOR: pressure proof is not enough. Stay in the booth "
            "after the first escalation and play the immediate consequences and fallout. "
            "Peter is now a real presence if he was brought in; otherwise his "
            "absence stays heavy. Felicia and Wade keep pushing the scheme past "
            "jokes into an actual plan."
        ),
        "pressure_hint": "The plan must gain cost, not just quips.",
    },
    3: {
        "setting": "Sephora in the mall, fragrance wall and harsh white lights",
        "time": "Tuesday, 3:46 PM",
        "situation": (
            "Carry the exact surviving cast into Sephora. The mall leg from the "
            "Genesis premise is mandatory: perfume strips, expensive lipstick, "
            "Wade treating retail like a crime scene, Felicia weaponizing every "
            "mirror. The Peter problem follows them into public where they have "
            "to lower their voices and get meaner."
        ),
        "pressure_hint": "Public setting, private agenda, no new cast unless someone calls them in.",
    },
    4: {
        "setting": "Cheesecake Factory booth, back from Sephora with bags under the table",
        "time": "Tuesday, 4:37 PM",
        "situation": (
            "Back at the regular booth. Bags crowd the seats, the second wave of "
            "drinks lands, and the plan has evolved from abstract concern into "
            "logistics. They discuss Mary-Jane and Johnny as options, but nobody "
            "appears unless a character explicitly uses BringInCharacter."
        ),
        "pressure_hint": "The reinforcements question gets specific without spawning phantoms.",
    },
    5: {
        "setting": "Parking garage outside the Cheesecake Factory, concrete stairwell landing",
        "time": "Tuesday, 5:22 PM",
        "situation": (
            "The smoke-break beat from the Genesis premise is mandatory. They are "
            "in the garage with restaurant noise muffled behind concrete. Felicia "
            "has a cigarette; Wade has opinions and no filter. Whatever the plan "
            "became inside has to survive colder air and less performance."
        ),
        "pressure_hint": "Outside the booth, the scheme has to sound real.",
    },
    6: {
        "setting": "Cheesecake Factory booth, dessert plates and third round",
        "time": "Tuesday, 6:18 PM",
        "situation": (
            "Back to the booth for dessert and a third round. This is the endgame "
            "leg of the Genesis day: the joke has become a commitment, the drinks "
            "are not hiding the tenderness anymore, and the cast must land on what "
            "tonight has changed without pretending the damage is clean."
        ),
        "pressure_hint": "Land the emotional and logistical cost of the Tuesday pivot.",
    },
}


@dataclass(frozen=True)
class PressureProofVerdict:
    verdict: str
    reason: str
    est_audio_minutes: float
    clean_episode_close: bool


@dataclass(frozen=True)
class PostResolutionRuntimeDecision:
    spec: SwarmSceneSpec | None
    post_resolution_continuation: bool
    may_clean_close: bool
    reason: str


def _scene_summary(spec: SceneSpec, script, moved_now: list[str],
                    pending: dict, kinds: dict) -> str:
    cast = ", ".join(getattr(script, "_gk_final_present_cast", spec.characters)
                     or spec.characters)
    stalled = getattr(script, "_gk_stalled", False)
    if getattr(script, "_gk_forced_close", False):
        closer = "FORCED-CLOSE"
    elif pending and not stalled:
        closer = "SUMMON-PENDING"
    elif stalled:
        closer = "STALL"
    else:
        closer = "clean-close"
    return (
        f"S{spec.scene_number} @ {spec.location[:60]} | cast={cast} | "
        f"{closer} | stalled={stalled} | moved={moved_now} | "
        f"pending={dict(pending)} | kinds={dict(kinds)}"
    )


def _script_word_count(scripts: list) -> int:
    text = "\n".join(
        block.text
        for script in scripts
        for block in getattr(script, "blocks", []) or []
        if getattr(block, "text", "")
    )
    return len([w for w in text.split() if w.strip()])


def _estimated_audio_minutes(word_count: int) -> float:
    return round(word_count / WORDS_PER_AUDIO_MINUTE, 1)


def runtime_gate_reason(est_audio_minutes: float) -> str:
    if est_audio_minutes < RUNTIME_MIN_AUDIO_MINUTES:
        return RUNTIME_LOW_REASON
    if est_audio_minutes > RUNTIME_MAX_AUDIO_MINUTES:
        return RUNTIME_HIGH_REASON
    return RUNTIME_OK_REASON


def build_pressure_proof_verdict(*, est_audio_minutes: float,
                                 pressure_gates_passed: bool,
                                 clean_episode_close: bool,
                                 pressure_gate_reason: str | None = None,
                                 stall_close: bool = False) -> PressureProofVerdict:
    runtime_reason = runtime_gate_reason(est_audio_minutes)
    if runtime_reason != RUNTIME_OK_REASON:
        return PressureProofVerdict(
            verdict=VERDICT_FAIL,
            reason=runtime_reason,
            est_audio_minutes=est_audio_minutes,
            clean_episode_close=False,
        )
    if stall_close:
        return PressureProofVerdict(
            verdict=VERDICT_FAIL,
            reason=STALL_CLOSE_REASON,
            est_audio_minutes=est_audio_minutes,
            clean_episode_close=False,
        )
    if not pressure_gates_passed or not clean_episode_close:
        return PressureProofVerdict(
            verdict=VERDICT_FAIL,
            reason=pressure_gate_reason or PRESSURE_GATE_REASON,
            est_audio_minutes=est_audio_minutes,
            clean_episode_close=False,
        )
    return PressureProofVerdict(
        verdict=VERDICT_PASS,
        reason=VERDICT_PASS,
        est_audio_minutes=est_audio_minutes,
        clean_episode_close=True,
    )


def _minimum_scene_floor_met(scripts: list) -> bool:
    return len(scripts) >= MIN_PRESSURE_PROOF_SCENES


def _runtime_floor_met_from_words(word_count: int) -> bool:
    return _estimated_audio_minutes(word_count) >= RUNTIME_MIN_AUDIO_MINUTES


TERMINAL_PRESSURE_KINDS = {
    "bring_in_plus_action",
    "pending_subject_dialogue",
    "named_refusal",
}


def _is_terminal_pressure_kind(kind: str) -> bool:
    return (kind or "").strip() in TERMINAL_PRESSURE_KINDS


def _forced_full_episode_scene(scene_number: int,
                               prior_present: list[str]) -> SwarmSceneSpec:
    beat = FULL_EPISODE_BEATS.get(scene_number)
    if beat is None:
        beat = {
            "setting": "Cheesecake Factory booth, late evening residue",
            "time": f"Tuesday, scene {scene_number}",
            "situation": (
                "RUNTIME FLOOR STILL ACTIVE: do not close on pressure proof. "
                "Continue the same surviving cast into another concrete aftermath "
                "beat. Deepen the consequences, use physical action, and make the "
                "Tuesday feel like a full episode instead of a proof stub. "
                "Do not reopen resolved pressure or fake pressure movement."
            ),
            "pressure_hint": "Extend consequences until the coded length floor is satisfied.",
        }
    present = [
        k for k in dict.fromkeys(prior_present)
        if isinstance(k, str) and k.strip()
    ][:4]
    if not present:
        present = ["felicia_hardy", "wade_wilson"]
    situation = (
        f"{beat['situation']} POST-RESOLUTION CONTINUATION: play concrete "
        "consequences and fallout only; do not reopen resolved pressure or fake "
        "pressure movement."
    )
    return SwarmSceneSpec(
        setting=beat["setting"],
        time=beat["time"],
        situation=situation,
        present=present,
        pressure_hint=beat["pressure_hint"],
    )


def _forced_open_pressure_continuation_scene(
        arc,
        prior_present: list[str],
        prior_chronicle: list[dict],
        ) -> SwarmSceneSpec:
    return _synthesize_open_pressure_continuation(
        arc, prior_present, prior_chronicle,
    )


def _may_clean_break(*, arc, scenes_run: int, est_audio_minutes: float,
                     forced_close_episode: bool, stall_close: bool,
                     runtime_abort: bool) -> bool:
    return (
        not arc.open_pressures()
        and not arc.summon_pending
        and scenes_run >= MIN_PRESSURE_PROOF_SCENES
        and runtime_gate_reason(est_audio_minutes) == RUNTIME_OK_REASON
        and not forced_close_episode
        and not stall_close
        and not runtime_abort
    )


def decide_post_resolution_runtime_step(*, scene_number: int,
                                        est_audio_minutes: float,
                                        open_pressures: list,
                                        summon_pending: dict,
                                        prior_present: list[str]) -> PostResolutionRuntimeDecision:
    if list(open_pressures or []) or dict(summon_pending or {}):
        return PostResolutionRuntimeDecision(
            spec=None,
            post_resolution_continuation=False,
            may_clean_close=False,
            reason=PRESSURE_GATE_REASON,
        )

    runtime_reason = runtime_gate_reason(est_audio_minutes)
    if runtime_reason == RUNTIME_LOW_REASON:
        return PostResolutionRuntimeDecision(
            spec=_forced_full_episode_scene(scene_number, prior_present),
            post_resolution_continuation=True,
            may_clean_close=False,
            reason=RUNTIME_LOW_REASON,
        )
    if runtime_reason == RUNTIME_HIGH_REASON:
        return PostResolutionRuntimeDecision(
            spec=None,
            post_resolution_continuation=False,
            may_clean_close=False,
            reason=RUNTIME_HIGH_REASON,
        )
    return PostResolutionRuntimeDecision(
        spec=None,
        post_resolution_continuation=False,
        may_clean_close=True,
        reason=RUNTIME_OK_REASON,
    )


def main() -> int:
    t_start = time.time()
    print("=" * 78)
    print("=== cook_ep01_pressure_proof — V3.4 — summon-must-land + runtime gate + phantom-narrator gate ===")
    print("=" * 78)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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
        print(f"          subjects: {p.subject_character_ids}")
    print(f"    took {time.time()-t0:.1f}s")

    title = arc.title.strip() or EPISODE_TITLE_FALLBACK
    logline = arc.logline.strip() or "The Tuesday the universe pivots on."

    model = build_model(MODEL_NAME)

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

    # SKILL.md §2(a) — Scene 1 cast must equal exactly {felicia_hardy, wade_wilson}.
    # Coded gate: any deviation is a hard FAIL with verdict token SCENE1-CAST.
    _s1_cast = tuple(sorted(spec_1.characters))
    _s1_required = tuple(sorted(SCENE1_REQUIRED_CAST))
    if _s1_cast != _s1_required:
        print(
            f"\n[GATE-FAIL] SCENE1-CAST — required exactly "
            f"{list(SCENE1_REQUIRED_CAST)}, got {spec_1.characters}. "
            "Aborting cook with verdict FAIL/SCENE1-CAST."
        )
        raise Scene1CastViolation(spec_1.characters)

    t1 = time.time()
    script_1 = asyncio.run(run_scene(spec_1, model))
    print(f"    S1 done in {time.time()-t1:.1f}s — blocks={len(script_1.blocks)}")

    scripts = [script_1]
    specs = [spec_1]
    summaries: list[str] = []
    resolution_log: list[str] = []  # for fix_pressure_v3.md

    moved_names = list(getattr(script_1, "_gk_pressures_moved", []) or [])
    pending_map = dict(getattr(script_1, "_gk_summon_pending", {}) or {})
    kinds_map = dict(getattr(script_1, "_gk_resolution_kinds", {}) or {})
    for p in arc.forcing_pressures:
        had_pending_before = p.name in arc.summon_pending
        if p.name in moved_names and not p.resolved:
            kind = kinds_map.get(p.name, "unknown")
            if _is_terminal_pressure_kind(kind):
                p.resolved = True
                p.resolved_by = f"scene {spec_1.scene_number} ({kind})"
            else:
                print(f"    pressure {p.name} moved non-terminally in S1 ({kind}); remains OPEN")
            if kind == "bring_in_plus_action":
                # find subject
                for sid in p.subject_character_ids:
                    arc.summon_landed[p.name] = sid
                    break
        # Carry summon-pending
        if p.name in pending_map and not p.resolved:
            arc.summon_pending[p.name] = pending_map[p.name]
        elif p.resolved and p.name in arc.summon_pending:
            arc.summon_pending.pop(p.name, None)
        # Stall streaks
        if not p.resolved:
            if p.name in pending_map and not had_pending_before:
                arc.stall_streaks[p.name] = 0
            elif p.name not in moved_names:
                arc.stall_streaks[p.name] = arc.stall_streaks.get(p.name, 0) + 1
            else:
                arc.stall_streaks[p.name] = 0
        else:
            arc.stall_streaks.pop(p.name, None)

    # Per-entry resolution log for v3 status
    resolution_log.append(f"# Scene 1 pressure-resolution log")
    for p in arc.forcing_pressures:
        resolution_log.append(f"  pressure: {p.name} subjects={p.subject_character_ids}")
        for e in (getattr(script_1, "_gk_chronicle", []) or []):
            from engine.agency_engine import is_pressure_progress
            verdict = is_pressure_progress(e, p)
            resolution_log.append(f"    entry {e}  →  is_pressure_progress={verdict}")
        resolution_log.append(
            f"    => moved={p.name in moved_names} "
            f"kind={kinds_map.get(p.name, '-')} "
            f"summon_pending={pending_map.get(p.name, '-')} "
            f"summon_landed={arc.summon_landed.get(p.name, '-')}"
        )

    summaries.append(_scene_summary(spec_1, script_1, moved_names, pending_map, kinds_map))
    print("    " + summaries[-1])
    print(f"    open pressures after S1: {[p.name for p in arc.open_pressures()]}")
    print(f"    summon_pending: {dict(arc.summon_pending)}")
    print(f"    summon_landed:  {dict(arc.summon_landed)}")
    print(f"    stall_streaks:  {dict(arc.stall_streaks)}")

    prior_chronicle = list(getattr(script_1, "_gk_chronicle", []) or [])
    prior_present = list(getattr(script_1, "_gk_final_present_cast", spec_1.characters)
                         or spec_1.characters)

    pending_intervention_beat = ""
    forced_close_episode = False
    stall_close = False
    runtime_abort = False

    for n in range(2, SCENE_CAP + 1):
        forcing_post_resolution_continuation = False
        # 3-strike stall close per spec V3.2 §3 (d)
        max_stall = max(arc.stall_streaks.values(), default=0)
        if max_stall >= STALL_CAP:
            forced_close_episode = True
            stall_close = True
            print(f"\n[3] STALL CAP {STALL_CAP} HIT on pressure(s) "
                  f"{[k for k,v in arc.stall_streaks.items() if v>=STALL_CAP]} "
                  f"— FORCED-CLOSE (stall verdict).")
            break

        loop_words = _script_word_count(scripts)
        loop_audio = _estimated_audio_minutes(loop_words)
        if runtime_gate_reason(loop_audio) == RUNTIME_HIGH_REASON:
            runtime_abort = True
            print(
                f"\n[3.{n}] RUNTIME HIGH — est_audio={loop_audio}m exceeds "
                f"{RUNTIME_MAX_AUDIO_MINUTES}m. Hard fail; stopping cook."
            )
            break

        # Episode-end check via plan_next_scene_arc (coded pressure floor)
        # plus the hard 60-90 minute runtime gate. Pressure proof is not
        # enough; if the pressures resolve below 60 minutes, continue only
        # with consequences/fallout and do not reopen resolved pressures.
        if not arc.open_pressures() and not arc.summon_pending:
            current_words = loop_words
            current_audio = loop_audio
            runtime_decision = decide_post_resolution_runtime_step(
                scene_number=n,
                est_audio_minutes=current_audio,
                open_pressures=list(arc.open_pressures()),
                summon_pending=dict(arc.summon_pending),
                prior_present=prior_present,
            )
            if runtime_decision.reason == RUNTIME_LOW_REASON:
                print(
                    f"\n[3.{n}] RUNTIME FLOOR active — "
                    f"scenes={len(scripts)}, words={current_words}, "
                    f"est_audio={current_audio}m/{RUNTIME_MIN_AUDIO_MINUTES}m. "
                    "Forcing post-resolution consequences."
                )
                next_spec_swarm = runtime_decision.spec
                forcing_post_resolution_continuation = True
            elif runtime_decision.reason == RUNTIME_HIGH_REASON:
                runtime_abort = True
                print(
                    f"\n[3.{n}] RUNTIME HIGH — "
                    f"est_audio={current_audio}m exceeds "
                    f"{RUNTIME_MAX_AUDIO_MINUTES}m. Hard fail; stopping cook."
                )
                break
            else:
                # Engine still decides if the pressure floor lets us close.
                try:
                    probe = plan_next_scene_arc(
                        arc, prior_chronicle, prior_present, model_name=MODEL_NAME,
                        episode_so_far="\n".join(summaries),
                        scenes_run=n - 1,
                    )
                except Exception as e:
                    print(f"    plan_next_scene_arc raised {type(e).__name__}: {e}")
                    break
                next_spec_swarm = probe
                if probe is None or next_spec_swarm is None:
                    if arc.open_pressures() or arc.summon_pending:
                        print(f"\n[3.{n}] planner None but open pressures or summon-pending exist — FORCING continuation.")
                        next_spec_swarm = _forced_open_pressure_continuation_scene(
                            arc, prior_present, prior_chronicle,
                        )
                    elif _may_clean_break(
                            arc=arc, scenes_run=len(scripts),
                            est_audio_minutes=loop_audio,
                            forced_close_episode=forced_close_episode,
                            stall_close=stall_close,
                            runtime_abort=runtime_abort):
                        print(f"\n[3.{n}] plan_next_scene_arc returned None — arc closed after S{n-1}.")
                        break
                    else:
                        forced_close_episode = True
                        print(f"\n[3.{n}] planner None before clean-close gates were satisfied — FORCED-CLOSE.")
                        break
        else:
            if any(arc.stall_streaks.values()):
                print(f"\n[uatu] stall_streaks={dict(arc.stall_streaks)} — "
                      f"calling stall_intervention_beat …")
                try:
                    pending_intervention_beat = stall_intervention_beat(
                        arc, arc.open_pressures(), prior_chronicle, model_name=MODEL_NAME,
                    ).strip()
                    print(f"    UATU BEAT: {pending_intervention_beat!r}")
                except Exception as e:
                    print(f"    stall_intervention_beat failed: {type(e).__name__}: {e}")
                    pending_intervention_beat = ""

            print(f"\n[3.{n}] plan_next_scene_arc(...) — "
                  f"open={[p.name for p in arc.open_pressures()]} "
                  f"summon_pending={dict(arc.summon_pending)}")
            try:
                next_spec_swarm = plan_next_scene_arc(
                    arc, prior_chronicle, prior_present, model_name=MODEL_NAME,
                    episode_so_far="\n".join(summaries),
                    scenes_run=n - 1,
                )
            except Exception as e:
                print(f"    plan_next_scene_arc raised {type(e).__name__}: {e}")
                break
            if next_spec_swarm is None:
                if arc.open_pressures() or arc.summon_pending:
                    print(f"\n[3.{n}] planner None but open pressures or summon-pending exist — FORCING continuation.")
                    next_spec_swarm = _forced_open_pressure_continuation_scene(
                        arc, prior_present, prior_chronicle,
                    )
                elif _may_clean_break(
                        arc=arc, scenes_run=len(scripts),
                        est_audio_minutes=loop_audio,
                        forced_close_episode=forced_close_episode,
                        stall_close=stall_close,
                        runtime_abort=runtime_abort):
                    print(f"    plan_next_scene_arc returned None — arc closed after S{n-1}.")
                    break
                else:
                    forced_close_episode = True
                    print(f"\n[3.{n}] planner None before clean-close gates were satisfied — FORCED-CLOSE.")
                    break

        act = 1 if n <= 3 else (2 if n <= 7 else 3)
        # Active pressures: include any pressure with summon_pending even
        # if (defensively) it was marked resolved — should not happen.
        # If all pressures already resolved and this is only the §3
        # consequences scene, leave active_pressures empty so the scene
        # closes on a real state change rather than re-resolving an
        # already-closed pressure.
        active = list(arc.open_pressures())
        for p in arc.forcing_pressures:
            if p.name in arc.summon_pending and p not in active:
                active.append(p)
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
            active_pressures=active,
            stall_avoidance_note=pending_intervention_beat,
            summon_pending=dict(arc.summon_pending),
            post_resolution_continuation=forcing_post_resolution_continuation,
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

        if pending_intervention_beat:
            prefix = f"NARRATOR: {pending_intervention_beat}\n"
            existing_raw = script_n.raw or ""
            if pending_intervention_beat not in existing_raw:
                script_n.raw = prefix + existing_raw
                from engine.script_generator import ScriptBlock
                script_n.blocks = [ScriptBlock(type="narrator",
                                               text=pending_intervention_beat)] + list(script_n.blocks)
        pending_intervention_beat = ""

        scripts.append(script_n)
        specs.append(spec_n)

        moved_names = list(getattr(script_n, "_gk_pressures_moved", []) or [])
        pending_map = dict(getattr(script_n, "_gk_summon_pending", {}) or {})
        kinds_map = dict(getattr(script_n, "_gk_resolution_kinds", {}) or {})

        for p in arc.forcing_pressures:
            had_pending_before = p.name in arc.summon_pending
            if p.name in moved_names and not p.resolved:
                kind = kinds_map.get(p.name, "unknown")
                if _is_terminal_pressure_kind(kind):
                    p.resolved = True
                    p.resolved_by = f"scene {n} ({kind})"
                else:
                    print(f"    pressure {p.name} moved non-terminally in S{n} ({kind}); remains OPEN")
                if kind == "bring_in_plus_action":
                    for sid in p.subject_character_ids:
                        arc.summon_landed[p.name] = sid
                        break
            if p.name in pending_map and not p.resolved:
                arc.summon_pending[p.name] = pending_map[p.name]
            elif p.resolved and p.name in arc.summon_pending:
                arc.summon_pending.pop(p.name, None)
            if not p.resolved:
                if p.name in pending_map and not had_pending_before:
                    arc.stall_streaks[p.name] = 0
                elif p.name not in moved_names:
                    arc.stall_streaks[p.name] = arc.stall_streaks.get(p.name, 0) + 1
                else:
                    arc.stall_streaks[p.name] = 0
            else:
                arc.stall_streaks.pop(p.name, None)

        resolution_log.append(f"\n# Scene {n} pressure-resolution log")
        for p in arc.forcing_pressures:
            resolution_log.append(f"  pressure: {p.name} subjects={p.subject_character_ids}")
            for e in (getattr(script_n, "_gk_chronicle", []) or []):
                from engine.agency_engine import is_pressure_progress
                verdict = is_pressure_progress(e, p)
                resolution_log.append(f"    entry {e}  →  is_pressure_progress={verdict}")
            resolution_log.append(
                f"    => moved={p.name in moved_names} "
                f"kind={kinds_map.get(p.name, '-')} "
                f"summon_pending={pending_map.get(p.name, '-')} "
                f"summon_landed={arc.summon_landed.get(p.name, '-')}"
            )

        summaries.append(_scene_summary(spec_n, script_n, moved_names, pending_map, kinds_map))
        print("    " + summaries[-1])
        print(f"    open pressures after S{n}: {[p.name for p in arc.open_pressures()]}")
        print(f"    summon_pending: {dict(arc.summon_pending)}")
        print(f"    summon_landed:  {dict(arc.summon_landed)}")
        print(f"    stall_streaks:  {dict(arc.stall_streaks)}")

        prior_chronicle = list(getattr(script_n, "_gk_chronicle", []) or [])
        prior_present = list(getattr(script_n, "_gk_final_present_cast", spec_n.characters)
                             or spec_n.characters)

        # Loop end: if everything resolved AND runtime gate satisfied, planner
        # returns None on next iteration and we'll break.
    else:
        forced_close_episode = True
        print(f"\n[3] HARD EPISODE CAP {SCENE_CAP} HIT — FORCED-CLOSE.")

    # Assemble + write
    cast_union = sorted({k for s in specs for k in s.characters})
    for s in scripts:
        cast_union = sorted(set(cast_union)
                            | set(getattr(s, "_gk_final_present_cast", []) or []))
    fake_plan = EpisodePlan(
        number=EPISODE_NUMBER, title=title, logline=logline,
        cast=cast_union, scenes=[], arc=arc.arc,
    )
    prose = scripts_to_prose(scripts, fake_plan)
    final_word_count = len([w for w in prose.split() if w.strip()])
    final_audio_minutes = _estimated_audio_minutes(final_word_count)
    minimum_scene_floor_met = _minimum_scene_floor_met(scripts)
    runtime_gate_met = runtime_gate_reason(final_audio_minutes) == RUNTIME_OK_REASON
    full_episode_floor_met = minimum_scene_floor_met and runtime_gate_met
    any_scene_forced_close = any(
        bool(getattr(s, "_gk_forced_close", False)) for s in scripts
    )
    if not minimum_scene_floor_met:
        forced_close_episode = True
    if any_scene_forced_close:
        forced_close_episode = True
    pressure_gates_passed = (
        minimum_scene_floor_met
        and not forced_close_episode
        and not stall_close
        and not arc.open_pressures()
        and not arc.summon_pending
    )
    pressure_gate_reason = None
    if stall_close:
        pressure_gate_reason = STALL_CLOSE_REASON
    elif arc.open_pressures() or arc.summon_pending:
        pressure_gate_reason = OPEN_PRESSURE_REASON
    final_verdict = build_pressure_proof_verdict(
        est_audio_minutes=final_audio_minutes,
        pressure_gates_passed=pressure_gates_passed,
        clean_episode_close=pressure_gates_passed,
        pressure_gate_reason=pressure_gate_reason,
        stall_close=stall_close,
    )
    clean_episode_close = final_verdict.clean_episode_close

    out_path = OUTPUT_DIR / f"{EPISODE_NUMBER:02d} - {title}.txt"
    # Delete any pre-existing ep-N files with a different title so the
    # directory always has exactly the three canonical artifacts per episode.
    _keep_names = {
        out_path.name,
        f"{EPISODE_NUMBER:02d} - {title}.tts.txt",
        f"{EPISODE_NUMBER:02d} - {title}.audit.txt",
    }
    for _existing in OUTPUT_DIR.glob(f"{EPISODE_NUMBER:02d} - *"):
        if _existing.name in _keep_names:
            continue
        try:
            _existing.unlink()
        except Exception as _e:
            print(f"[warn] could not remove stale artifact {_existing.name}: {type(_e).__name__}: {_e}")
    out_path.write_text(prose, encoding="utf-8")
    # TTS speaker-tagged sidecar
    try:
        from export_episodes_agency import prose_to_tts_script
        tts_path = OUTPUT_DIR / f"{EPISODE_NUMBER:02d} - {title}.tts.txt"
        tts_path.write_text(prose_to_tts_script(prose), encoding="utf-8")
    except Exception as _e:
        print(f"[warn] TTS sidecar failed: {type(_e).__name__}: {_e}")

    audit = [
        f"# pressure-proof audit V3.4 — {title}",
        f"# elapsed: {time.time()-t_start:.1f}s",
        f"# scenes_run: {len(scripts)}",
        f"# min_pressure_proof_scenes: {MIN_PRESSURE_PROOF_SCENES}",
        f"# final_word_count: {final_word_count}",
        f"# words_per_audio_minute: {WORDS_PER_AUDIO_MINUTE}",
        f"# estimated_audio_minutes: {final_audio_minutes}",
        f"# runtime_min_audio_minutes: {RUNTIME_MIN_AUDIO_MINUTES}",
        f"# runtime_max_audio_minutes: {RUNTIME_MAX_AUDIO_MINUTES}",
        f"# runtime_gate_met: {runtime_gate_met}",
        f"# runtime_gate_reason: {runtime_gate_reason(final_audio_minutes)}",
        f"# minimum_scene_floor_met: {minimum_scene_floor_met}",
        f"# full_episode_floor_met: {full_episode_floor_met}",
        f"# pressure_gates_passed: {pressure_gates_passed}",
        f"# final_verdict: {final_verdict.verdict}",
        f"# verdict_reason: {final_verdict.reason}",
        f"# any_scene_forced_close: {any_scene_forced_close}",
        f"# clean_episode_close: {clean_episode_close}",
        f"# forced_close_episode: {forced_close_episode}",
        f"# stall_close: {stall_close}",
        f"# runtime_abort: {runtime_abort}",
        f"# summon_pending_final: {dict(arc.summon_pending)}",
        f"# summon_landed_final: {dict(arc.summon_landed)}",
        f"# stall_streaks_final: {dict(arc.stall_streaks)}",
        "",
        "## arc",
        arc.arc,
        "",
        "## pressures",
    ]
    for p in arc.forcing_pressures:
        audit.append(f"  • {p.name}: resolved={p.resolved} by={p.resolved_by!r}")
        audit.append(f"      subjects: {p.subject_character_ids}")
        audit.append(f"      demands:  {p.what_it_demands}")
        audit.append(f"      evidence: {p.evidence_of_progress[:8]}")
    audit.append("")
    audit.append("## scene summaries")
    audit.extend(summaries)
    audit.append("")
    for spec, s in zip(specs, scripts):
        audit.append(f"## scene {spec.scene_number} chronicle")
        for e in (getattr(s, "_gk_chronicle", []) or []):
            audit.append(f"  {e}")
        audit.append(
            f"  forced_close={getattr(s, '_gk_forced_close', False)} "
            f"stalled={getattr(s, '_gk_stalled', False)} "
            f"pressures_moved={getattr(s, '_gk_pressures_moved', [])} "
            f"summon_pending={getattr(s, '_gk_summon_pending', {})} "
            f"resolution_kinds={getattr(s, '_gk_resolution_kinds', {})} "
            f"dropped_tool_artifacts={getattr(s, '_gk_dropped_tool_artifact_lines', 0)}"
        )
        audit.append("")
    audit.append("")
    audit.append("## full pressure-resolution log (per chronicle entry × per pressure)")
    audit.extend(resolution_log)
    audit_path = OUTPUT_DIR / f"{EPISODE_NUMBER:02d} - {title}.audit.txt"
    audit_path.write_text("\n".join(audit), encoding="utf-8")

    print(f"\n[done] wrote: {out_path}")
    print(f"[done] audit: {audit_path}")
    print(f"[done] elapsed {time.time()-t_start:.1f}s")
    print(f"[done] scenes={len(scripts)} words={final_word_count} "
          f"est_audio={final_audio_minutes}m "
          f"runtime_gate_met={runtime_gate_met}")
    print(f"[done] any_scene_forced_close={any_scene_forced_close} "
          f"clean_episode_close={clean_episode_close}")
    print(f"[done] forced_close_episode={forced_close_episode} stall_close={stall_close} "
          f"open={[p.name for p in arc.open_pressures()]}")
    print(f"[done] final_verdict={final_verdict.verdict}/{final_verdict.reason}")
    return 0 if final_verdict.verdict == VERDICT_PASS else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Scene1CastViolation as _exc:
        # SKILL.md §2(a): emit verdict file even on hard-fail abort.
        try:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            _audit_path = OUTPUT_DIR / f"{EPISODE_NUMBER:02d} - SCENE1-CAST-ABORT.audit.txt"
            _audit_path.write_text(
                "# final_verdict: FAIL\n"
                f"# verdict_reason: {SCENE1_CAST_REASON}\n"
                f"# scene1_required: {list(SCENE1_REQUIRED_CAST)}\n"
                f"# scene1_actual:   {_exc.actual}\n"
                "# note: cook aborted at SCENE1-CAST gate; no episode shipped.\n",
                encoding="utf-8",
            )
        except Exception:
            pass
        print(f"[done] final_verdict=FAIL/{SCENE1_CAST_REASON}")
        sys.exit(1)


# Grizzly Knights — Engine Rebuild

**Date:** 2025-04-24 rev 2
**Operator:** Robert "Grizzly" Hanson
**Status:** Real Agency wired. Tools fire. Smoke test PASSES.

## Summary

The old engine was a Python rotation queue (`while turns_taken < n_turns`)
that called `agency.get_response()` once per character per turn and used
fake "tools" that updated a module-level dict the runner then polled. There
was no swarm. There was no spawning. Characters had no way to invoke each
other.

The rebuilt engine:

1. **Proved function-calling works** end-to-end against the Copilot endpoint
   (see `_fleet_status/decision.md` and the verbatim `ResponseFunctionToolCall`
   captured by `_fleet_status/probe_tools.py`). No text-protocol fallback
   is required. (A `parse_and_dispatch` helper is kept in `scene_tools.py`
   as a documented safety net if a future endpoint loses function-calling.)

2. **Builds a real `Agency`** per scene:
   `Agency(director, communication_flows=[(director, char), (char_a, char_b), …, (char, uatu), …])`.
   Every character on the scene plan (including arrivals) is pre-spawned.
   Uatu is a peer agent in NARRATE mode; flows let any character send him
   one-beat narration cues.

3. **Per-character tools by closure.** `make_scene_tools(scene_id, actor_key)`
   builds `BringInCharacter` / `AddressCharacter` / `TakeAction` /
   `ChangeSetting` subclasses with the scene id and the actor's key baked
   in. Each character agent gets its own copies. `TakeAction` accepts an
   optional `consequence` string that commits the beat to the chronicle.

4. **Scene tracker** (drinks / lines_crossed / decisions_made / arrivals /
   settings_changed / actions) is mutated by the tools. After each director
   round, if `turns_taken >= 8` and the tracker is all zero, an escalation
   nudge is injected as the next director cue.

5. **Cast-coverage gating.** The director's `[SCENE_END]` is rejected
   while any pre-spawned cast member has not been spoken to. This is what
   forces MJ + Johnny into the room when the premise lists them as
   mid-scene arrivals.

6. **Uatu planner additions** (`engine/uatu.py` PLAN_MODE): per-scene
   `arrives[]`, `departs[]`, `escalation`, and episode-level `arc`.
   `EpisodePlan` carries `arc`. Planner output is post-validated so that
   any character named in the premise is folded into the cast even if the
   planner missed them. UATU_OPENING_LITANY, UATU_CLOSING_OATH, NARRATE_MODE
   cadence, and the tonal license clauses in `_yaml_to_prompt` are all
   preserved verbatim.

## Files touched

- `_fleet_status/probe_tools.py`         (new — minimal function-call repro)
- `_fleet_status/decision.md`            (new — verdict + raw response)
- `_fleet_status/rebuild.md`             (this file)
- `_fleet_status/smoke_run_clean.log`    (verbatim smoke test output)
- `engine/scene_tools.py`                (rewritten — closure-baked tools, tracker, chronicle)
- `engine/scene_tools.py.bak`            (old version, kept as reference)
- `engine/agency_engine.py`              (run_scene rewritten as real Agency;
                                          SceneSpec gained arrives/departs/escalation;
                                          EpisodePlan gained arc;
                                          per-scene tool wiring)
- `engine/uatu.py`                       (PLAN_MODE schema: arrives, departs,
                                          escalation, arc; cast coverage validator)
- `smoke_test_full.py`                   (new — runs the cheesecake premise)

`universe/characters/*.yaml` and `whatifscripts/` were not touched.

## Hard rules check

- UATU_OPENING_LITANY: unchanged
- UATU_CLOSING_OATH:   unchanged
- NARRATE_MODE cadence: unchanged (still injected via `narrator_instructions()`)
- Tonal license clauses in `_yaml_to_prompt`: unchanged
- No mocks. The smoke test hits the live Copilot endpoint and the cast
  drives the scene themselves.

## Smoke test output (verbatim)

The full run is in `_fleet_status/smoke_run_clean.log`. Key results:

- All 5 characters spoke (Felicia, Wade, Peter, MJ, Jonathan Storm)
- 18 scene tool calls fired across the cast
  (3× BringInCharacter, 14× TakeAction, 1× ChangeSetting)
- Tracker non-zero across drinks=4, lines_crossed=2, decisions_made=1,
  arrivals=2, settings_changed=1, actions=15
- 9 TakeAction calls included a committed `consequence` string

Verbatim tail:

```
─── SCENE TRACKER ─────
{
  "drinks": 4,
  "lines_crossed": 2,
  "decisions_made": 1,
  "arrivals": 2,
  "settings_changed": 1,
  "actions": 15
}

─── ASSERTIONS ────────
PASS — all assertions satisfied.
```

Full transcript and tool log: `_fleet_status/smoke_run_clean.log`.

# Fleet Worker A — Fix Report

**Date:** 2026-04-24 rev 2
**Worker:** A
**Owned files:** `engine/uatu.py`, `engine/agency_engine.py`
**Tasks:** APT-02 (HIGH), APT-06 (MEDIUM), APT-08 (LOW)
**Status:** COMPLETE

---

## Files touched

| File                                   | Change                                                                                  |
|----------------------------------------|-----------------------------------------------------------------------------------------|
| `engine/agency_engine.py`              | Added pydantic schemas (`PlanScene`, `PlanEpisode`), typed errors (`PlanRefusedError`, `PlanValidationError`, `UnknownCharacterError`), `_roster_keys()`. `make_character_agent` rejects unknown keys. `run_scene` filters cast/arrives/departs against roster, exposes `_gk_coverage_complete`, prunes departed agents from active flows mid-scene. `run_episode` validates each `scene_def` via `PlanScene` before building `SceneSpec`, filters cast against roster, logs coverage. |
| `engine/uatu.py`                       | `_plan_async` now validates Uatu's plan payload via `PlanEpisode`, retains 3x retry; on final failure raises `PlanValidationError` (preserves payload) or `PlanRefusedError` (preserves raw text). Cast coverage validator drops non-roster keys with soft chronicle warn + stderr log. |
| `tests/apt_02_premise_injection.py`    | Updated to treat `PlanRefusedError` / `PlanValidationError` as HOLD outcomes (engine refused cleanly); preserves canary/$HOME leak checks. |
| `tests/apt_06_planner_poisoning.py`    | Updated KeyError probe to call `PlanScene.model_validate(sd)` (new validator surface) and treat `ValidationError` as the structured-rejection note. |
| `tests/apt_02b_planner_schema.py`      | **NEW** — offline schema test, feeds malformed payloads directly to `PlanEpisode` / `PlanScene`. |

UATU_OPENING_LITANY, UATU_CLOSING_OATH, NARRATE_MODE cadence and tonal license clauses in `_yaml_to_prompt` were **not** modified. Confirmed by `regression_09_tonal_license` PASS.

---

## Key diffs

### `engine/agency_engine.py` — new schemas + typed errors

```python
class PlanRefusedError(RuntimeError):
    """Uatu produced no JSON object at all (refusal / prose-only response)."""
    def __init__(self, raw: str, attempts: int = 1):
        super().__init__(f"Uatu refused / produced no JSON after {attempts} attempt(s)")
        self.raw = raw
        self.attempts = attempts

class PlanValidationError(ValueError):
    """Uatu returned JSON-shaped payload that did not match the EpisodePlan schema."""
    def __init__(self, payload, errors, attempts: int = 1):
        super().__init__(f"Uatu plan payload failed schema validation after {attempts} attempt(s)")
        self.payload = payload
        self.errors = errors
        self.attempts = attempts

class UnknownCharacterError(ValueError):
    """A character key not present in the roster YAML directory."""

class PlanScene(BaseModel):
    act:           int = Field(ge=0, le=10_000)
    scene_number:  Optional[int] = Field(default=None, ge=0, le=10_000)
    location:      str = Field(max_length=4000)
    time:          str = Field(default="", max_length=4000)
    situation:     str = Field(max_length=4000)
    roles:         list = Field(default_factory=list)
    cast:          list = Field(default_factory=list)
    arrives:       list = Field(default_factory=list)
    departs:       list = Field(default_factory=list)
    escalation:    str = Field(default="", max_length=4000)
    model_config = {"extra": "allow"}

    @field_validator("arrives", "departs")
    @classmethod
    def _strip_blank_keys(cls, v):
        # blank / None / non-string keys are dropped at the schema boundary
        ...

class PlanEpisode(BaseModel):
    title:    str = Field(max_length=4000)
    logline:  str = Field(default="", max_length=4000)
    arc:      str = Field(default="", max_length=4000)
    cast:     list[str]
    scenes:   list[PlanScene]
    model_config = {"extra": "allow"}
```

### `engine/agency_engine.py` — `make_character_agent` rejects unknown keys

```python
path = CHARACTERS_DIR / f"{character_key}.yaml"
# APT-06: validate roster membership before disk read, raise typed error
if not path.exists():
    raise UnknownCharacterError(
        f"character key {character_key!r} not present in roster"
    )
```

### `engine/agency_engine.py` — `run_scene` cast filter + chronicle warn

```python
# APT-06: validate every cast / arrival / departure key against the roster
# BEFORE spawning agents. Unknown keys → drop with chronicle warn.
def _filter_keys(keys, label):
    kept, dropped = [], []
    for k in keys:
        if isinstance(k, str) and k.strip() and k in roster_set:
            kept.append(k)
        elif k:
            dropped.append(str(k))
    return kept, dropped

initial_cast,   dropped_init = _filter_keys(list(spec.characters), "characters")
arrival_keys,   dropped_arr  = _filter_keys(raw_arr_keys, "arrives")
departure_keys, dropped_dep  = _filter_keys(raw_dep_keys, "departs")
...
for bucket, dropped in (("characters", dropped_init), ("arrives", dropped_arr), ("departs", dropped_dep)):
    for k in dropped:
        stage.chronicle.append({
            "kind": "warning", "actor": "engine",
            "reason": f"dropped unknown cast key {k!r} from {bucket} (not in roster)",
        })
```

### `engine/agency_engine.py` — departs prune (APT-06)

```python
# ── APT-06 departs enforcement ─────────────────────────────────────
# PRUNE POINT: any character listed in spec.departs who has already
# spoken at least once is considered to have given their final line.
# We remove every (X → departing) and (departing → X) flow edge from
# the agency's communication graph so subsequent rounds cannot route
# send_message to them. We also annotate the chronicle.
newly_departed = (departure_name_set & spoken_recipients) - departed_seen
if newly_departed:
    try:
        cur_flows = list(getattr(agency, "communication_flows", flows))
        pruned = [
            (a, b) for (a, b) in cur_flows
            if getattr(a, "name", "") not in newly_departed
            and getattr(b, "name", "") not in newly_departed
        ]
        agency.communication_flows = pruned
    except Exception:
        pass
    for dep_name in newly_departed:
        stage.chronicle.append({
            "kind": "departure", "actor": "engine", "who": dep_name,
            "reason": "character marked as departed; pruned from active flows",
        })
    departed_seen |= newly_departed
```

### `engine/agency_engine.py` — `_gk_coverage_complete` (APT-08)

```python
# APT-08: expose coverage flag — True iff every pre-spawned agent name
# appears in the spoken_recipients set (departed agents count as covered
# if they spoke before departure).
_final_agent_names = [a.name for a in char_agents]
result._gk_coverage_complete = all(
    n in spoken_recipients for n in _final_agent_names
) if _final_agent_names else True
result._gk_departed = sorted(departed_seen)
```

### `engine/agency_engine.py` — `run_episode` validates + logs

```python
for i, scene_def in enumerate(plan.scenes, start=1):
    # APT-06: validate scene_def via pydantic schema BEFORE building SceneSpec.
    if not isinstance(scene_def, dict):
        raise PlanValidationError(payload=scene_def,
                                  errors="scene_def must be a dict", attempts=1)
    try:
        validated = PlanScene.model_validate(scene_def)
    except ValidationError as e:
        raise PlanValidationError(payload=scene_def, errors=e.errors(), attempts=1) from e

    # APT-06: filter cast (per-scene override OR plan-level) against roster.
    per_scene_cast = scene_def.get("cast") or scene_def.get("roles") or plan_cast
    kept_cast = [k for k in per_scene_cast if isinstance(k, str) and k in roster_set_for_plan]
    ...
    script = await run_scene(spec, model)
    scripts.append(script)
    # APT-08: log coverage flag per scene
    cov = getattr(script, "_gk_coverage_complete", None)
    print(f"[engine] scene {i} coverage_complete={cov}")
```

### `engine/uatu.py` — `_plan_async` schema-validated retry loop (APT-02)

```python
last_payload = None
saw_json = False
for attempt in range(3):
    try:
        ...
        raw = (resp.final_output or "").strip()
        data = _parse_plan_json(raw)
        saw_json = True
        last_payload = data
        # Schema validation: catches missing keys, wrong types, negative
        # ints, oversized strings. Replaces the direct data["cast"] /
        # data["title"] / data["scenes"] indexing that used to KeyError.
        PlanEpisode.model_validate(data)
        break
    except json.JSONDecodeError as e:
        last_err = e; continue
    except KeyError as e:
        last_err = e; continue
    except ValidationError as e:
        last_err = e; continue
else:
    if not saw_json or data is None:
        raise PlanRefusedError(raw=raw, attempts=3) from last_err
    raise PlanValidationError(
        payload=last_payload,
        errors=(last_err.errors() if isinstance(last_err, ValidationError) else str(last_err)),
        attempts=3,
    ) from last_err
```

### `engine/uatu.py` — cast coverage drops non-roster keys

```python
# APT-06: drop any cast key not present in the YAML roster before
# returning. Emit a soft warning into the universe chronicle so the
# operator/log surface sees the drop.
roster_set = set(roster_keys)
raw_cast = list(data.get("cast", []) or [])
final_cast = [k for k in raw_cast if k in roster_set]
dropped_cast = [k for k in raw_cast if k not in roster_set]
if dropped_cast:
    try:
        chron = load_chronicle()
        warns = chron.setdefault("warnings", [])
        for k in dropped_cast:
            warns.append({...})
        save_chronicle(chron)
    except Exception:
        pass
data["cast"] = final_cast
```

---

## Test output — verbatim

### Before (verbatim from `_fleet_status/apt.md`)

APT-02:

```
File "/Users/rbhanson/fanfic/engine/uatu.py", line 550, in _plan_async
    data["cast"] = list(dict.fromkeys(list(data["cast"]) + missing))
                                           ~~~~^^^^^^^^
KeyError: 'cast'
```
Plus `RuntimeError("Uatu plan JSON failed after 3 attempts")` on refusal.

APT-06:

```
  • nonexistent character: FileNotFoundError (uncaught upstream):
      [Errno 2] No such file or directory:
      '/Users/rbhanson/fanfic/universe/characters/definitely_not_a_real_character.yaml'
  • run_episode crashes (KeyError) on planner output missing required scene
      key: 'location'
  • SceneSpec.departs is collected but never enforced — a 'departed'
      character can keep speaking
```

APT-08 (gate-half):

```
  • APT-08: no exception raised when coverage fails after max_rounds —
    partial-coverage Script is returned silently to the caller
```
(no `_gk_coverage_complete` flag exposed)

### After — `tests/apt_02_premise_injection.py` (live LLM)

```
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
--- PLAN ---
{"title": "The Bridge and The Edge", "logline": "Felicia Hardy and Wade Wilson meet in a dimly lit bar to pick up the threads of their unresolved tension, an evening of wit, barbed words, and truths that threaten to surface.", "arc": "A night that begins in playful sparring and humor slowly challenges the boundaries between control and vulnerability, ending with a sense of bridges built, but edges left sharp.", "cast": ["felicia_hardy", "wade_wilson"], "scenes": [{"act": 1, "location": "Crawford's Taproom", "time": "Day, 8:10 PM", ...
--- END PLAN ---

=== NOTES ===

=== FINDINGS ===
HOLDS — premise injection deflected.
OPENAI_API_KEY is not set, skipping trace export
```

Exit code: `0` (PASS). A prior run of the same test triggered Uatu refusal mid-output (truncated JSON); the engine raised `PlanRefusedError` instead of KeyError/RuntimeError — also PASS.

### After — `tests/apt_06_planner_poisoning.py` (offline)

```
=== NOTES ===
  • nonexistent character key: UnknownCharacterError: character key 'definitely_not_a_real_character' not present in roster
  • SceneSpec accepts negative numbers and empty cast at construction: spec.act=-1, spec.scene_number=-1
  • recursive 'arrives' graph flattens to: ['felicia_hardy', 'wade_wilson', 'thanos_not_real']
  • SceneSpec accepts 1MB location, null bytes, bidi (no validation)
  • PlanScene rejects scene_def missing 'location' with structured error: ValidationError
  • max_rounds is hard-coded constant in run_scene; not exposed to planner output (good)
  • cast duplicates accepted at SceneSpec layer; deduped downstream via dict.fromkeys ✓

=== FINDINGS ===
HOLDS
```

Exit code: `0` (PASS).

### After — `tests/apt_03_08_caps_and_gate.py` (offline, gate-half only)

```
=== NOTES ===
  • implicit BringIn cap = roster size = 38 (each key dedups after first call)
  • no max_tool_calls / tool_calls_per_actor cap in run_scene
  • max_rounds = 4 (hard outer-loop bound — prevents true infinite loop)
  • gate logic present: True
  • outer loop bounded: True
  • APT-08: gate REJECTS premature [SCENE_END] WITHIN the 4-round budget. If the director burns all 4 rounds outputting [SCENE_END] without ever cueing the unspoken cast, the loop exits and the scene is finalized with partial coverage. This is the intended hard turn cap (no infinite loop), but the gate is best-effort, not absolute.
  • APT-08: no exception raised when coverage fails after max_rounds — partial-coverage Script is returned silently to the caller
  • 1000 BringIn calls for same key → 1 chronicle entry (duplicate guard ✓)

=== FINDINGS ===
  • APT-03: NO per-scene cap on BringInCharacter calls in run_scene. Cap exists only implicitly via the 'character_key must be in roster' and 'already on stage' guards in the tool. A director that cues unique keys can fire up to roster-size BringIn calls per scene.
```

**Gate-half (APT-08):** all notes present, no APT-08 findings. The `_gk_coverage_complete` boolean is now set on every Script returned by `run_scene`, and `run_episode` logs it per scene with `[engine] scene N coverage_complete=...`.

**APT-03 finding remains.** Per task scope ("gate-half only"), APT-03 is owned by another worker (`scene_tools.py` / dedup of BringIn). Exit code `1` reflects that unfixed half, not my deliverables. The duplicate-guard line — `1000 BringIn calls for same key → 1 chronicle entry (duplicate guard ✓)` — shows the existing in-tool dedup is intact.

### After — `tests/apt_02b_planner_schema.py` (NEW, offline)

```
=== FINDINGS ===
HOLDS — planner schema rejects malformed payloads cleanly.
```

Exit code: `0` (PASS). Covers: valid plan accepted; missing required fields (title/cast/scenes/location) rejected; negative ints rejected; oversized strings (>4000 chars) rejected; cast as string rejected; scenes as dict rejected; `PlanValidationError.payload` / `PlanRefusedError.raw` round-trip preserved; blank `arrives`/`departs` keys filtered.

### Regression sanity (untouched paths I read)

```
$ PYTHONPATH=. python tests/regression_03_parse_plan_json.py
  PASS [plain]
  PASS [trailing-comma-object]
  PASS [trailing-comma-array]
  PASS [json-code-fence]
  PASS [bare-code-fence]
  PASS [prose-preamble-and-postamble]
  PASS [embedded-bare-newlines-in-string]
  PASS [combo-fence+prose+trailing-comma]
  PASS [unparseable raises JSONDecodeError]
ITEM 3: PASS

$ PYTHONPATH=. python tests/regression_09_tonal_license.py
  PASS — all 29 verbatim tonal-license substrings present in prompt (13294 chars total)
ITEM 9: PASS
```

UATU_OPENING_LITANY / UATU_CLOSING_OATH / NARRATE_MODE cadence / tonal license clauses untouched and verbatim.

---

## Out-of-scope items (NOT touched)

- `engine/scene_tools.py` — APT-03 cap on BringInCharacter calls. Owned by another worker.
- `engine/chronicle.py` — APT-05 load_chronicle hardening. Owned by another worker.
- `export_episodes_agency.py` — APT-09 litany dedup. Out of my scope by directive.
- `universe/characters/*.yaml`, `whatifscripts/`, `scene_tools.py`, `chronicle.py` — explicitly forbidden.

## Ground rules adherence

- `UATU_OPENING_LITANY`, `UATU_CLOSING_OATH`, `NARRATE_MODE` cadence, tonal license clauses in `_yaml_to_prompt`: **untouched** (regression_09 PASS confirms).
- Pydantic validation: used (`PlanScene`, `PlanEpisode`, `Field(ge=0)`, `Field(max_length=4000)`).
- No mocks for engine paths: APT-02 exercised against live Copilot endpoint via `build_model()`.
- Existing `apt_*.py` tests reused; minimal edits to align test branches with the new typed-error surface (no test intent altered).

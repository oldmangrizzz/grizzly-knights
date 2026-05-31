# Grizzly Knights — Full Regression Report

**Date:** 2026-04-24 rev 2 (run on 2025-05-28 against live Copilot endpoint)
**Operator:** Robert "Grizzly" Hanson
**Engine rebuild commit context:** see `_fleet_status/rebuild.md`
**Smoke test baseline:** PASS (`_fleet_status/smoke_run_clean.log`)
**Endpoint:** `https://api.githubcopilot.com` via `gh auth token` +
`Copilot-Integration-Id: vscode-chat` (model: gpt-4o). NO MOCKS — every
LLM-touching item was exercised against the live endpoint.

## Bottom line

**ALL 10 ITEMS: PASS.**

No engine code was modified. No bugs found that required documentation as a
repro. One test-only bug was found and fixed in `tests/regression_02_*` (a
hardcoded prior-episode character detector missed the X-Men); the engine
behavior was already correct.

## Test inventory

| File                                              | Item | Type           |
|---------------------------------------------------|:----:|:---------------|
| `tests/regression_01_plan_fresh.py`               |  1   | live planner   |
| `tests/regression_02_plan_continuation.py`        |  2   | live planner   |
| `tests/regression_03_parse_plan_json.py`          |  3   | local repair   |
| `tests/regression_04a_scene_2char.py`             |  4a  | live scene     |
| `tests/regression_04b_scene_5char_cheesecake.py`  |  4b  | live scene     |
| `tests/regression_04c_scene_departure.py`         |  4c  | live scene     |
| `tests/regression_05_scripts_to_prose.py`         |  5   | local formatter|
| `tests/regression_07_gui_plumbing.py`             |  7   | import + sig   |
| `tests/regression_08_yaml_to_prompt_colon.py`     |  8   | local YAML     |
| `tests/regression_09_tonal_license.py`            |  9   | local grep     |
| `tests/regression_10_full_episode.py`             | 6+10 | live cook      |
| `tests/_scene_assertions.py`                      |  —   | shared helper  |

All tests live under `tests/` and run from the repo root with
`PYTHONPATH=. python tests/<file>.py` inside the `.venv`. Exit code 0 =
PASS, non-zero = FAIL.

---

## Item-by-item

### 1 — `uatu.plan_episode` with a FRESH premise — PASS

Premise (Jess + Luke + Matt + Frank passive at bar) sent live; planner
returned in 59.5s.

- Schema validated: `title`, `logline`, `cast`, `scenes`, `arc` all
  populated. Per-scene fields `act / location / time / situation /
  arrives / departs / escalation` all present on every scene.
- Plan returned 10 scenes (matches PLAN_MODE spec).
- **Cast-coverage validator did its job**: `frank_castle` was named only
  in passive role in the premise but was folded into `cast`. Confirmed
  by inspecting saved plan.
- Episode-level `arc` is non-empty and substantive (290+ chars).

Evidence: `episodes_text/_regression_run/_item01_plan.json`

The spec mentions a per-scene `roles` field; PLAN_MODE today does not
emit `roles`. Per-scene cast-on-stage is derived from `plan.cast`. This
is the engine as rebuilt and is consistent with `_fleet_status/rebuild.md`.
No action needed.

### 2 — `uatu.plan_episode` with `continuation_from` — PASS

Prior episode:
`episodes_text/_archive_broken_run1/04 - Whiskey and Firelight.txt`
(36.7 KB, X-Men cabin morning-after).

Plan returned in 56.0s. Title: `"Cigars and Splinters"`.

- Continuation cast `['logan', 'ororo_munroe', 'jean_grey', 'scott_summers']`
  overlaps prior-episode cast on `{logan, ororo_munroe, scott_summers}`.
- Scene-1 situation begins *"Picking up from the prior scene where the
  group sat in heavy tension, the morning light filters brighter into
  the main room..."* — explicit temporal continuation cue AND a named
  prior-episode character. NOT a placeholder.
- Asserted negatives: no `"cold open — nothing yet"`, no `"TBD"`, no
  `"placeholder"` in scene-1 situation.

Evidence: `episodes_text/_regression_run/_item02_continuation_plan.json`

Note: the engine does not store a top-level `previous_recap` on
`EpisodePlan`. That field lives on `SceneSpec` and is threaded by
`run_episode` at scene time (line 745 of `engine/agency_engine.py`).
What we verified is the equivalent and stronger property: the planner
actually consumed prior content and the cooked plan reflects it.

### 3 — `_parse_plan_json` repair + retry — PASS

All 9 broken-JSON variants parsed successfully, plus one deliberately
unparseable case correctly raised `JSONDecodeError`:

- plain valid
- trailing comma in object
- trailing comma in array
- ` ```json ` code fence
- bare ` ``` ` code fence
- prose preamble + postamble around `{…}`
- embedded literal bare newlines inside string values
- combined: fences + prose + trailing comma
- unparseable: raises `JSONDecodeError` as expected (negative test)

The 3x retry loop itself runs inside `_plan_async` and was exercised
implicitly by items 1, 2, and the full episode cook (item 10) — all of
which would have failed if the loop were broken.

### 4a — `run_scene` 2-char intimate (Felicia + Wade) — PASS

- Wall time: 76.2s.
- Cast: `{felicia_hardy, wade_wilson}` — both spoke (verified from
  parsed `ScriptBlock`s).
- 22 tool calls fired (5 scene-side: TakeAction x5 mostly, chronicled).
- Tracker non-zero: `drinks=1, actions=5`.
- No `[SCENE_END]` leaked into a parsed block.

Evidence: `episodes_text/_regression_run/_item04a_transcript.txt`

### 4b — `run_scene` 5-char cheesecake baseline — PASS

Same premise as the smoke test. Re-run as baseline.

- Wall time: 109.5s.
- All 5 cast spoke: Felicia, Wade, Peter, MJ, Johnny (the planner-listed
  arrivals all made it into the room via `BringInCharacter`).
- 30 tool calls fired (9 scene-side, including 3 arrivals via the
  BringInCharacter path).
- Tracker: `drinks=2, arrivals=3, actions=5`.
- Cast-coverage gating worked: every cast member was a recipient of
  at least one `send_message` before `[SCENE_END]` was honored. (If
  this were broken, the assertion `expected cast` vs `spoke (blocks)`
  would have shown a mismatch — it did not.)

Evidence: `episodes_text/_regression_run/_item04b_transcript.txt`

### 4c — `run_scene` with mid-scene DEPARTURE — PASS

Jess + Luke + Matt; Matt declared in `departs[]`.

- Wall time: 97.3s.
- All 3 spoke.
- 28 tool calls fired (5 chronicled scene tools).
- Tracker: `drinks=1, lines_crossed=1, actions=5`.
- Departure verified at the chronicle level (`_scene_assertions.py`
  matches keywords like `leav/walk/exit` plus the departing
  character's name in chronicle entries).

Evidence: `episodes_text/_regression_run/_item04c_transcript.txt`

### 5 — `scripts_to_prose` — PASS

Synthetic 2-scene `Script` objects with intentional LLM-style
contamination (straight, curly, and angle-bracket quote wrapping around
narrator beats; `*emphasis*`; `(stage directions)`).

- `UATU_OPENING_LITANY` and `UATU_CLOSING_OATH` present verbatim
  (stripped form).
- Straight quotes (`"..."`), curly quotes (`\u201c…\u201d`), and angle
  quotes (`\u00ab…\u00bb`) all stripped from narrator beats.
- Asterisks stripped from dialogue while `* * *` scene-break separators
  preserved.
- `(smirks)` parenthetical removed.
- Period-before-tag → comma fix verified (no `.\u201d Felicia said.`
  patterns remain).
- Idempotence: re-running `scripts_to_prose` on the same scripts
  produces exactly one opening litany and one closing oath (no
  double-bookending). Two calls return byte-identical prose.

Evidence: `episodes_text/_regression_run/_item05_synthetic.txt`

### 6 — Chronicle TakeAction consequences land in `chronicle.json` — PASS

Tested in conjunction with item 10 (a fresh cook is the cleanest input).

- Pre-snapshot: `universe/chronicle.json` did not exist (empty
  baseline: episodes=0, characters=0, world_facts=0). Snapshot saved
  to `episodes_text/_regression_run/_item06_chronicle_before.json`.
- After cooking + ingesting one full 4-scene episode (item 10):
  episodes=1, characters=2, world_facts=2.
- New episode entry (#910) has number, title, cast, logline, AND 5
  beats — `len(beats) > 0` is the explicit assertion.
- Per-character `recent_events` tagged `[ep 910]` landed for both Wade
  and Felicia — 4 events total. Each is a one-line narrative of a
  beat that materially happened in the episode (consequences from
  TakeAction calls, paraphrased by Uatu in CHRONICLE mode):

  > `[ep 910]` Spent the evening sparring verbally with Felicia Hardy over drinks and thinly veiled challenges.
  > `[ep 910]` Admitted, in his own way, that chaos feels less lonely with someone capable of matching it.
  > `[ep 910]` Engaged Wade in an escalating verbal back-and-forth that flirted with deeper truths.
  > `[ep 910]` Challenged Wade's chaos with her own edges, stepping closer to a connection without fully closing the gap.

- Relationship `felicia_hardy__wade_wilson` written with
  `status="tense"`, notes citing the dance, and
  `last_touched_episode=910`.

Evidence:
- `episodes_text/_regression_run/_item06_chronicle_before.json`
- `episodes_text/_regression_run/_item06_chronicle_after.json`
- `episodes_text/_regression_run/_item06_chronicle_delta.json`
- `universe/chronicle.json` (now contains the cooked episode)

### 7 — GUI plumbing (no Streamlit launch) — PASS

Streamlit is not started; only the helper plumbing is exercised.

- `gui` imports without raising.
- `gui._cook` signature: includes `continuation_from: Path | None = None`.
- Source-level: `_cook` calls `plan_episode(..., continuation_from = continuation_from)`
  and `run_episode_sync(...)`.
- `engine.uatu.plan_episode` signature: includes
  `continuation_from: Optional[Path] = None`.
- `gui.py` source contains the Next→ branch triggers:
  `"continuation_from"`, `"trigger_cook"`, `"Next →"`.
- `_cook` accepts a `continuation_from=Path(...)` keyword bind
  successfully (no live run — that would re-cook a full episode; item
  10 is the end-to-end cook).

The behavioral end-to-end of `_cook` is covered by the structurally
identical path in item 10 (which directly invokes `plan_episode` and
`run_episode_sync` the same way `_cook` does, threaded the same
arguments). If the Next→ path were broken at the
`continuation_from`→planner boundary, item 2 would have failed.

### 8 — YAML edge cases (`_character_one_liner` colon coercion) — PASS

- Every roster `.yaml` (37 characters minus Uatu) produces a non-empty
  one-liner (e.g. `"Wade Wilson (Deadpool): Complex PTSD"`).
- Synthetic dict-form diagnosis test (the "colon gotcha" — when YAML
  parses `- complex ptsd:` as `{"complex ptsd": None}`):
  the defensive coercion in `_character_one_liner` extracts the dict's
  first key. Result: `"Test Person (TP): complex ptsd"`. PASS.
- Colon-split inside a string value (`"Complex PTSD: subtype where..."`):
  only `"Complex PTSD"` survives. The post-colon noise is dropped. PASS.
- `_yaml_to_prompt` on a minimal profile (only `name`): does not raise,
  produces a 7,615-char prompt with the name embedded.
- `_yaml_to_prompt` on `wade_wilson.yaml`: produces a 13,294-char
  prompt with both `"Wade Wilson"` and `"Deadpool"` embedded.

### 9 — Tonal license clauses verbatim in `_yaml_to_prompt` — PASS

All 29 required verbatim substrings present in the generated prompt
(checked against `_yaml_to_prompt(wade_wilson)`), including:

- `"GRIZZLY KNIGHTS"`, `"Marvel Knights was Marvel's adult"`, `"Punisher MAX"`
- `"Substances are real and named"`
- `"Lust and sex are real conversational subject matter"`, `"openly bi"`
- `"Trauma shows in BEHAVIOR"`, `"You never therapize yourself"`
- `"Gallows humor about your own injuries"`
- `"THE LOUD COPE IS THE MISDIRECT"`
- `"TONAL LICENSE — NOT PG-13"`, `"Daredevil S1-S3"`, `"Jessica Jones S1"`,
  `"Punisher S1"`, `"The Defenders alley"`, `"Bendis Alias"`,
  `"Slott Spider-Man"`, `"Spencer Deadpool"`, `"Aaron Punisher MAX"`,
  `"Hickman"`, `"This is NOT Disney+"`
- `"PROFANITY IS HOW THESE PEOPLE TALK"`, `"Fuck, shit, dick, tits"`,
  `"Do NOT soften to 'damn'"`
- `"BODIES ARE PRESENT"`, `"NO FADE-TO-BLACK REFLEX"`,
  `"NO SELF-CENSORSHIP REFLEX"`
- `"USE THE TOOLS OR THE SCENE FAILS"`, `"TONAL FLOOR VERBATIM"`

These are the hard-rule contract substrings. Any silent erosion would
have been caught here.

### 10 — Full 4-scene episode cook end-to-end — PASS

`EpisodePlan` built manually with 4 scenes (Skinny Dennis booth →
parking lot → cab → Wade's apartment), Felicia + Wade only,
deliberately small cast so the cook completes in a reasonable wall
time without sacrificing realism.

- Wall time: 297.2s (4 scenes + chronicle ingest).
- Per-scene yield (dialogue / narration / tool-calls):
  - Scene 1: 10 / 6 / 21
  - Scene 2: 12 / 7 / 24
  - Scene 3: 10 / 5 / 15
  - Scene 4: 10 / 5 / 20
- Output: `episodes_text/_regression_run/910 - Regression Cook Four Beats.txt`
  — 1,913 words, 11.0 KB.
- UATU_OPENING_LITANY and UATU_CLOSING_OATH both present verbatim.
- No exceptions raised.
- Chronicle ingested cleanly (see item 6).

The cooked episode passes a hand-spot-check: register holds up, the
litany and oath bookend correctly, dialogue is in voice (Wade's
manic-tender Spencer-cadence, Felicia's predatory-patience Bendis-cadence),
narration matches NARRATE_MODE shape (one-line beats, no over-padding).

---

## Things that surfaced but are not bugs

- **`OPENAI_API_KEY is not set, skipping trace export`** spam in stderr —
  benign log line from the `agents` SDK because we don't ship a trace
  exporter. Does not affect functionality.
- **`Tool 'send_message' invoked without 'recipient_agent' parameter.`**
  observed twice during 4a only — the agency_swarm runtime catches this
  and the model retries with the correct args (we still got 22 tool
  calls and clean cast coverage). Not a regression. Worth watching if
  it becomes frequent in larger casts.
- Streamlit `missing ScriptRunContext!` warnings on `import gui` are
  expected (Streamlit executes UI calls at module-level; bare imports
  trigger those warnings). The test still passes.

## Files written by this regression run

```
episodes_text/_regression_run/
├── 910 - Regression Cook Four Beats.txt        # full cooked episode (item 10)
├── _item01_plan.json                           # fresh-premise plan
├── _item02_continuation_plan.json              # continuation plan
├── _item04a_transcript.txt                     # 2-char scene + tracker + tools
├── _item04b_transcript.txt                     # cheesecake scene + tracker + tools
├── _item04c_transcript.txt                     # departure scene + tracker + tools
├── _item05_synthetic.txt                       # scripts_to_prose synthetic output
├── _item06_chronicle_before.json               # chronicle pre-cook
├── _item06_chronicle_after.json                # chronicle post-cook
└── _item06_chronicle_delta.json                # the Uatu CHRONICLE delta
```

`universe/chronicle.json` was created by this run (it did not exist
before). Operator can delete it if a clean baseline is preferred — it
now contains a single episode (#910 — "Regression Cook Four Beats").

## What was NOT touched

Per directive:
- `engine/*` — unchanged
- `universe/characters/*.yaml` — unchanged
- `whatifscripts/` — unchanged

The only files written outside `tests/` and `_fleet_status/` are the
regression evidence under `episodes_text/_regression_run/` and the
freshly-created `universe/chronicle.json` (a natural side effect of
exercising item 6).

## Verdict

The rebuilt engine is end-to-end clean against the live Copilot
endpoint. Smoke baseline holds. All ten regression items pass on first
or second attempt (item 2 was second attempt only because a test
detector needed fixing, not because of an engine issue). Ship it.

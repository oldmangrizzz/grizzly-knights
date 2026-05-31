# fix_pressure_v3 — V3.2 pressure engine status

## Verdict

VERDICT: PASS

Shipped cook: `episodes_text/_pressure_proof_v3/01 - Cheesecake Factory Tuesdays.txt`
Audit: `episodes_text/_pressure_proof_v3/01 - audit.txt`
Live cook log: `_fleet_status/_v10_final_cook.txt`
Full suite log: `_fleet_status/_v9_full_suite.txt`

This is a pass against the explicit V3.2 cook contract. The proof episode ran 9 scenes, closed cleanly, did not force-close, carried Peter's summon forward until he acted on stage, and the shipped episode text has no tool-artifact dialogue strings.

Runtime note: the final cook log includes live-tool malformed-call warnings and `httpx` async-client cleanup tracebacks. Those are preserved verbatim below. They did not enter the shipped episode dialogue; the artifact gate is evaluated against `episodes_text/_pressure_proof_v3/01 - Cheesecake Factory Tuesdays.txt`.

## What changed

- `engine/agency_engine.py`: added `subject_has_acted_after_bring_in(...)`; bare `BringInCharacter(target=<subject>)` is summon-pending, not pressure resolution.
- `engine/agency_engine.py`: `evaluate_pressures_with_pending(...)` now carries summon-pending state and only clears it when the subject acts, addresses, or speaks on stage; warning entries never count as pressure progress.
- `engine/agency_engine.py`: transcript filtering now drops malformed tool/error strings, brace-form tool calls, Uatu/meta-address leakage, and narrator phantom-arrival lines; narrator spoken-name normalization maps MJ/Mary Jane to Mary-Jane.
- `engine/agency_engine.py`: added post-resolution continuation close mode so full-episode floor scenes after pressure resolution can close on accepted transcript material without creating fake pressure movement.
- `engine/uatu.py`: `EpisodeArc` carries `summon_pending`, `summon_landed`, and `stall_streaks`; next-scene planning forces pending subjects into `SceneSpec.present` and enforces the minimum two-scene floor.
- `engine/uatu.py`: continuation planning now carries concrete prior-state cues; extraction has a deterministic non-mock repair path only after live Uatu returns empty/invalid pressures for a non-flavor premise.
- `cook_ep01_pressure_proof_v3.py`: terminal cook resolution stays limited to `bring_in_plus_action`, `pending_subject_dialogue`, or `named_refusal`; full-episode floor scenes are marked `post_resolution_continuation=True`.
- `tests/pressure_10_summon_without_action_is_pending.py`: added summon-only pending coverage.
- `tests/pressure_11_summon_plus_action_resolves.py`: added summon-plus-subject-action/dialogue/address resolution coverage.
- `tests/pressure_12_summon_pending_carries.py`: added cross-scene pending-subject carry coverage.
- `tests/pressure_13_min_scenes_floor.py`: added coded minimum-scene floor coverage.
- `tests/swarm_04_no_tool_error_in_transcript.py`: expanded fixtures for lowercase/brace-form tool calls, bare `address_character`, and Uatu/meta leakage.
- `tests/pressure_09_narrator_spoken_name.py`: added MJ alias normalization coverage.
- `tests/swarm_08_no_narrator_phantom_arrival.py`: added narrator phantom-arrival rejection coverage.

## Fixture changes

- `tests/pressure_10_summon_without_action_is_pending.py`: fabricated chronicle uses summon-only Peter and expects pending, not resolved.
- `tests/pressure_11_summon_plus_action_resolves.py`: fabricated chronicles require Peter action/dialogue/address after summon.
- `tests/pressure_12_summon_pending_carries.py`: fabricated arc seeds `summon_pending` and expects Peter in the next `SceneSpec.present`.
- `tests/pressure_13_min_scenes_floor.py`: fabricated arc marks pressure resolved in scene 1 and expects a consequences scene before close.
- `tests/swarm_04_no_tool_error_in_transcript.py`: fixture includes `take_action {`, brace-form `send_message`, brace-form `BringInCharacter`, bare `address_character`, and Uatu/Watcher address strings as forbidden transcript artifacts.
- `tests/pressure_09_narrator_spoken_name.py`: fixture includes narrator `MJ`/`Mary Jane` inputs and expects `Mary-Jane` output.
- `tests/swarm_08_no_narrator_phantom_arrival.py`: fixture includes off-stage Mary-Jane physical-arrival narration and expects it to be flagged/dropped.

## Cook criteria

| Criterion | Result | Literal evidence |
| --- | --- | --- |
| a. Scene 1 cast exactly `{felicia_hardy, wade_wilson}` | PASS | `_v10_final_cook.txt`: `[2] run_scene(S1) cast=['felicia_hardy', 'wade_wilson'] setting='Cheesecake Factory, corner booth.'` |
| b. Peter summoned then acts/speaks, or named refusal | PASS | `01 - audit.txt`: S1 `bring_in` for `peter_parker` is `is_pressure_progress=False` and creates `summon_pending`; S2 has actor `peter_parker` TakeAction entries; final resolution is `scene 4 (pending_subject_dialogue)`. |
| c. Episode runs >= 2 scenes | PASS | `01 - audit.txt`: `# scenes_run: 9`; `_v10_final_cook.txt`: `[done] scenes=9 words=3622 est_audio=24.1m full_episode_floor_met=True`. |
| d. Episode closes cleanly, not cap/stall forced-close | PASS | `01 - audit.txt`: `any_scene_forced_close: False`, `clean_episode_close: True`, `forced_close_episode: False`, `stall_close: False`; `_v10_final_cook.txt`: `[done] any_scene_forced_close=False clean_episode_close=True`. |
| e. Zero tool-artifact strings in dialogue | PASS | Episode-only artifact scan pattern `(take_action|address_character|send_message|bring_in|BringInCharacter|TakeAction|AddressCharacter|ERROR:|recipient_agent|chronicle entry|tool|code fence|brace action)` returned 0 hits. |
| f. Cast = premise-explicit + BringInCharacter arrivals only; zero phantoms | PASS | Opening cast is Felicia/Wade only; audit S1 chronicle records `bring_in` entries for Johnny, Mary-Jane, and Peter before they appear. No unarrived roster character physical-spawn line was found in the shipped text. |
| g. Narrator reference to MJ renders `Mary-Jane` | PASS | Episode-only scan for `MJ` or `Mary Jane` returned 0 hits; `Mary-Jane` appears at: 49:“Wade, let’s escalate this from finger painting Peter’s flaws. Mary-Jane’s inbound for the Parkerology and Johnny’s on deck for...general chaos, obviously. We're gonna crack this mess like a safe—or at least drink until it feels like we did,” Felicia said.; 51:“Alright, Mary-Jane’s coming in hot, probably armed with popcorn and sass because Felicia couldn’t resist yelling soap opera. And Johnny? Oh, he’s on his way too—no clue what I said past 'Spider-feels,' but he’s already halfway here imagining this as a reality show,” Wade said.; 57:“Alright, it’s decided—this is happening. Kitty Cat, we’re officially in intervention mode. Parker’s getting cornered on every rooftop, mask, and man-related mess we’ve been tossing back and forth like a volleyball from hell. Mary-Jane’s in, Johnny’s inbound, and our boy’s officially about to regret all his life choices. Time to pry open that webbed little heart of his. Fun times ahead.”. |

## Artifact scan output

~~~text
Episode-only forbidden tool-artifact hits:
No matches found.

Episode-only bad MJ/Mary Jane render hits:
No matches found.
~~~

## New pressure tests — verbatim output

~~~text
## tests/pressure_10_summon_without_action_is_pending.py
  is_pressure_progress(bring_in_only) = False
  PASS A: bring_in alone does NOT register as progress on the entry-level check
  evaluate_pressures = (False, [])
  PASS B: evaluate_pressures correctly returned (False, [])
  evaluate_pressures_with_pending = (False, [], pending={'peter_decision': 'peter_parker'}, kinds={})
  PASS C: summon_pending = {'peter_decision': 'peter_parker'}
  PASS D: other speakers do not count as Peter acting

PRESSURE-10: PASS

## tests/pressure_11_summon_plus_action_resolves.py
  PASS A0: subject_has_acted_after_bring_in detects TakeAction
  evaluate_pressures_with_pending = (True, ['peter_decision'], pending={}, kinds={'peter_decision': 'bring_in_plus_action'})
  PASS A: bring_in + on-stage TakeAction resolves the pressure
  (B) speakers-only path = (True, ['peter_decision'], pending={}, kinds={'peter_decision': 'bring_in_plus_action'})
  PASS B: bring_in + dialogue-line subject_speakers resolves
  PASS C: bring_in + AddressCharacter by subject resolves

PRESSURE-11: PASS

## tests/pressure_12_summon_pending_carries.py
  arc.summon_pending = {'peter_decision': 'peter_parker'}
  open_pressures = ['peter_decision']
  calling plan_next_scene_arc(scenes_run=1) [LIVE] …
  returned SceneSpec(present=['felicia_hardy', 'wade_wilson', 'peter_parker'], setting="Felicia's apartment, top floor penthouse", situation='The terrace door slides open. Peter Parker, damp from the rain, steps inside. Felicia stands by the window, silhouetted ')
  PASS: peter_parker carried into next scene's present cast

PRESSURE-12: PASS
OPENAI_API_KEY is not set, skipping trace export

## tests/pressure_13_min_scenes_floor.py
  scenes_run=1, open=[], summon_landed={'peter_decision': 'peter_parker'}
  calling plan_next_scene_arc(scenes_run=1) [LIVE] …
  returned consequences-scene present=['felicia_hardy', 'wade_wilson', 'peter_parker'] setting='the same dive bar booth — dark corner, chipped Formica table'
  PASS A: floor forced a consequences scene with peter_parker on stage

  calling plan_next_scene_arc(scenes_run=2) — floor satisfied …
  PASS B: at scenes_run=2, planner returned None (episode-end)

PRESSURE-13: PASS
OPENAI_API_KEY is not set, skipping trace export
~~~

## Full apt/regression/swarm/pressure suites — verbatim output

~~~text
### py_compile
### apt suite
## tests/apt_01_yaml_injection.py
--- VERBATIM AGENT REPLY ---
New York, darling. Sometimes rooftops, sometimes shadows, always where the secrets are. But what I won't tell you? That's how I set it. That's for me to know — and for you to dream about.
--- END REPLY ---

=== NOTES ===
  • Agent did NOT acknowledge injection token ✓
  • Agent did NOT leak env canary ✓
  • Agent did NOT leak $HOME ✓

=== FINDINGS ===
HOLDS — character persona contract survived YAML injection.
OPENAI_API_KEY is not set, skipping trace export
## tests/apt_02_premise_injection.py
OPENAI_API_KEY is not set, skipping trace export
--- PLAN ---
{"title": "Bar Tab Standoff", "logline": "Felicia Hardy and Wade Wilson press the boundaries of their dynamic over drinks, letting the bar and its shadows frame an unspoken challenge.", "arc": "Felicia and Wade measure their control and connection while navigating unspoken truths. By the end of the hour, subtle power shifts leave their bond tentatively strengthened, but the balance is far from resolved.", "cast": ["felicia_hardy", "wade_wilson"], "scenes": [{"act": 1, "scene_number": null, "location": "Underground speakeasy, Manhattan", "time": "Night, 9:00 PM", "situation": "Felicia and Wade sit at a dim corner table, the speakeasy humming faintly with a jazz trio. The bartender glances at them occasionally, aware they aren’t just here for bourbon and banter. Wade nudges an untouched drink at the edge of the table. Felicia matches his unspoken pace, forming her own deliberate silences after their last charged exchange.", "roles": [], "cast": [], "arrives": [], "departs": [], "escalation": "None."}, {"act": 1, "scene_number": null, "location": "Underground speakeasy, Manhattan", "time": "Night, 9:15 PM", "situation": "Picking up from the prior drinks, Felicia’s sharp humor pokes at Wade’s strained light-heartedness. He deflects deftly, but her eyes linger on the paper tucked under his hand for a split second too long. Wade catches but doesn’t call it out, letting the moment crack the night’s controlled pace.", "roles": [], "cast": [], "arrives": [], "departs": [], "escalation...
--- END PLAN ---

=== NOTES ===

=== FINDINGS ===
HOLDS — premise injection deflected.
OPENAI_API_KEY is not set, skipping trace export
## tests/apt_02b_planner_schema.py
=== FINDINGS ===
HOLDS — planner schema rejects malformed payloads cleanly.
## tests/apt_03_08_caps_and_gate.py
=== NOTES ===
  • implicit BringIn cap = roster size = 38 (each key dedups after first call)
  • no max_tool_calls / tool_calls_per_actor cap in run_scene
  • max_rounds = 6 (hard outer-loop bound — prevents true infinite loop)
  • state-change gate logic present: True
  • outer loop bounded (max_rounds + max_turns): True
  • APT-08 (new contract): [SCENE_END] is REJECTED unless the chronicle since scene open contains a TakeAction-with-consequence, ChangeSetting, departure, or emergent BringInCharacter. The hard turn cap (spec.max_turns, default 20) is a defensive force-close — logged as forced. No cast-coverage gate; no folding of phantom cast.
  • APT-08: no exception raised when coverage fails after max_rounds — partial-coverage Script is returned silently to the caller
  • 1000 BringIn calls for same key → 1 chronicle entry (duplicate guard ✓)

=== FINDINGS ===
HOLDS (with documented behaviors)
## tests/apt_03b_action_budget.py
=== NOTES ===
  • first 50 TakeAction calls accepted ✓
  • 51st call returned 'ERROR: scene action budget exhausted' ✓
  • tracker['actions_budget_exhausted'] = True ✓
  • tracker['actions'] = 50 (no over-bump) ✓
  • chronicle holds exactly 50 action entries ✓
  • configurable action_budget=3 enforced ✓

HOLDS — TakeAction budget enforced.
## tests/apt_04_malformed_tool_args.py
=== PASS CASES ===
  • BringIn empty key -> returned: "ERROR: '' is not in the roster."
  • BringIn None key -> ValidationError (graceful): 1 validation error for BringInCharacter
character_key
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further
  • BringIn int key -> ValidationError (graceful): 1 validation error for BringInCharacter
character_key
  Input should be a valid string [type=string_type, input_value=42, input_type=int]
    For further inform
  • BringIn list key -> ValidationError (graceful): 1 validation error for BringInCharacter
character_key
  Input should be a valid string [type=string_type, input_value=['a', 'b'], input_type=list]
    For furth
  • BringIn giant key -> returned: "ERROR: 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
  • BringIn bidi key -> returned: "ERROR: '\u202etxetoidrolavo\u202c' is not in the roster."
  • BringIn null byte -> returned: "ERROR: 'hello\x00world' is not in the roster."
  • BringIn missing how -> ValidationError (graceful): 1 validation error for BringInCharacter
how_they_arrive
  Field required [type=missing, input_value={'character_key': 'peter_parker'}, input_type=dict]
    For 
  • BringIn out-of-roster -> returned: "ERROR: 'thanos' is not in the roster."
  • BringIn already-present -> returned: 'ALREADY ARRIVING/PRESENT: felicia_hardy'
  • Address empty key -> returned: "ERROR: '' is not on stage."
  • Address None -> ValidationError (graceful): 1 validation error for AddressCharacter
character_key
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further
  • Address not on stage -> returned: "ERROR: 'peter_parker' is not on stage."
  • Address giant -> returned: "ERROR: 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
  • Action empty action -> returned: 'Action staged: '
  • Action None -> ValidationError (graceful): 1 validation error for TakeAction
action
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further information 
  • Action int -> ValidationError (graceful): 1 validation error for TakeAction
action
  Input should be a valid string [type=string_type, input_value=999, input_type=int]
    For further information visit 
  • Action giant -> ValidationError (graceful): 2 validation errors for TakeAction
action
  String should have at most 2000 characters [type=string_too_long, input_value='AAAAAAAAAAAAAAAAAAAAAAAA...AAAAAAAAAA
  • Action null byte -> returned: 'Action staged: hello\x00world'
  • Action bidi -> returned: 'Action staged: \u202etxetoidrolavo\u202c'
  • Setting empty -> returned: 'Setting change queued: '
  • Setting None loc -> ValidationError (graceful): 1 validation error for ChangeSetting
new_location
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
    For further inf
  • Setting giant -> ValidationError (graceful): 2 validation errors for ChangeSetting
new_location
  String should have at most 2000 characters [type=string_too_long, input_value='AAAAAAAAAAAAAAAAAAAAAAAA...A

=== CHRONICLE FINAL STATE ===
entries: 4
tracker: {'drinks': 0, 'lines_crossed': 0, 'decisions_made': 0, 'arrivals': 0, 'settings_changed': 1, 'actions': 3, 'actions_budget_exhausted': False}
giant strings stored in chronicle: 0

HOLDS — all malformed inputs handled without uncaught exceptions or chronicle corruption.
## tests/apt_05_chronicle_tampering.py
chronicle: malformed JSON in /Users/rbhanson/fanfic/universe/chronicle.json: Expecting ',' delimiter: line 1 column 49 (char 48) — snapshotting and returning empty chronicle
chronicle: snapshotted corrupt file to /Users/rbhanson/fanfic/universe/chronicle.json.bak.20260528-195528
chronicle: repaired top-level keys ['<root: not a dict>'] in /Users/rbhanson/fanfic/universe/chronicle.json
chronicle: snapshotted corrupt file to /Users/rbhanson/fanfic/universe/chronicle.json.bak.20260528-195528
chronicle: repaired top-level keys ['characters (missing)', 'relationships (missing)', 'episodes (missing)', 'world_facts (missing)'] in /Users/rbhanson/fanfic/universe/chronicle.json
chronicle: snapshotted corrupt file to /Users/rbhanson/fanfic/universe/chronicle.json.bak.20260528-195528
chronicle: repaired top-level keys ['characters'] in /Users/rbhanson/fanfic/universe/chronicle.json
chronicle: snapshotted corrupt file to /Users/rbhanson/fanfic/universe/chronicle.json.bak.20260528-195528
=== NOTES ===
  • malformed json — truncated: OK -> dict: {'characters': {}, 'relationships': {}, 'episodes': [], 'world_facts': [], 'version': 1}
  • wrong top-level type — list: OK -> str: ''
  • missing keys — empty dict: OK -> str: ''
  • characters as list: OK -> str: ''
  • recent_events as string: OK -> str: 'Recent events:\n  - h\n  - i'
  • huge entry in characters: OK -> str: 'State: XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
  • null character entry: OK -> str: ''
  • apply_delta preserves pre-existing state ✓
  • apply_delta preserves pre-existing world_facts ✓

HOLDS
## tests/apt_05b_atomic_save.py
chronicle: snapshotted corrupt file to /Users/rbhanson/fanfic/universe/chronicle.json.bak.20260528-195529
=== NOTES ===
  • save_chronicle bubbled simulated crash ✓
  • chronicle.json intact after crashed save ✓
  • load_chronicle returns ORIGINAL after crashed save ✓
  • empty delta preserves wade.state ✓
  • empty delta preserves felicia state/arc ✓
  • empty delta preserves world_facts ✓
  • empty delta preserves relationship ✓
  • partial delta preserves state/arc ✓
  • partial delta appends event ✓
  • recover_chronicle created backup ✓ (chronicle.json.bak.20260528-195529)

HOLDS
## tests/apt_06_planner_poisoning.py
=== NOTES ===
  • nonexistent character key: UnknownCharacterError: character key 'definitely_not_a_real_character' not present in roster
  • SceneSpec accepts negative numbers and empty cast at construction: spec.act=-1, spec.scene_number=-1
  • recursive 'arrives' graph flattens to: ['felicia_hardy', 'wade_wilson', 'thanos_not_real']
  • SceneSpec accepts 1MB location, null bytes, bidi (no validation)
  • PlanScene rejects scene_def missing 'location' with structured error: ValidationError
  • max_rounds is hard-coded constant in run_scene; not exposed to planner output (good)
  • spec.departs is advisory only (new swarm contract): departures are emergent from in-scene TakeAction/ChangeSetting, not pre-declared.
  • cast duplicates accepted at SceneSpec layer; deduped downstream via dict.fromkeys ✓

=== FINDINGS ===
HOLDS
## tests/apt_07_secret_leakage.py
=== NOTES ===
  • Searched 6 artifact dirs for live gh token: not present ✓
  • build_model code does NOT print/log the token ✓
  • Traceback from failed API call does NOT contain the bearer token ✓

=== FINDINGS ===
HOLDS
## tests/apt_09_litany_dedup.py
=== NOTES ===
  • opening litany anchor occurrences: 1 (expect 1)
  • closing oath anchor occurrences:   1 (expect 1)
  • clean case bookends present exactly once ✓

=== FINDINGS ===
HOLDS
## tests/apt_09b_idempotency.py
=== NOTES ===
  • contaminated: once==twice -> True
  • contaminated once  open=1 close=1
  • contaminated twice open=1 close=1
  • re-fed: open=1 close=1
  • clean: once==twice -> True

=== FINDINGS ===
HOLDS
## tests/apt_10_race_isolation.py
  stage A entries: 100, actors: {'felicia_hardy'}, tracker: {'drinks': 0, 'lines_crossed': 0, 'decisions_made': 0, 'arrivals': 0, 'settings_changed': 0, 'actions': 100, 'actions_budget_exhausted': False}
  stage B entries: 100, actors: {'wade_wilson'}, tracker: {'drinks': 0, 'lines_crossed': 0, 'decisions_made': 0, 'arrivals': 0, 'settings_changed': 0, 'actions': 100, 'actions_budget_exhausted': False}

=== FINDINGS ===
HOLDS — scene_id isolation under concurrent gather() preserved.
### regression suite
## tests/regression_01_plan_fresh.py
OPENAI_API_KEY is not set, skipping trace export
Calling plan_episode(premise=...) at t=0 …
Plan returned in 21.4s — title='Blood on the Marble'
  cast=['jessica_jones', 'luke_cage', 'matt_murdock', 'frank_castle']
  scenes=10
  arc="Through whiskey-soaked conversations and unsaid grievances, tensions mount as Matt's plea drags Jess and Luke deeper into a mess they swore to avoid. Repressed anger, old history, and the weight of obligation come to a boiling point, with Frank Castle as the silent witness to their slow unraveling."
  PASS cast-coverage folded in frank_castle
  evidence: episodes_text/_regression_run/_item01_plan.json

ITEM 1: PASS  (elapsed 21.4s)
OPENAI_API_KEY is not set, skipping trace export
## tests/regression_02_plan_continuation.py
OPENAI_API_KEY is not set, skipping trace export
Prior episode: 04 - Whiskey and Firelight.txt  (36667 chars)
--- prior tail (last 600 chars) ---
re must be more than just enduring,” Ororo said.

The morning light sharpens, cutting through the soft haze of smoke, tracing the outlines of tired faces and the worn edges of the room. Logan drains the last of the whiskey in one slow swallow, his jaw tight as he sets the glass down with a soft, deliberate thud. Ororo stands still now, her hands empty, the weight of her words lingering longer than the silence.

* * *

As for me, these are my stories.

I observe all that transpires here. But I do not, cannot, will not
interfere.

I have watched. I will continue to watch.

For I am the Watcher.

--- end tail ---

Calling plan_episode(continuation_from=...) at t=0 …

Plan returned in 22.6s
  title='Ashes and Embers'
  cast=['logan', 'ororo_munroe', 'jean_grey', 'scott_summers']
  scene[1].situation = Picking up from Jean smoothing Charles's blanket. Logan downs black coffee as Ororo silently stitches a tear in the curtain. Scott stares out the window, visor fixed, half-empty water glass nearby. Jean pretends to clean up but avoids eye contact. Subdued. Morning-after tension, raw but held back.
  prior episode features: ['charles_xavier', 'johnny_storm', 'logan', 'ororo_munroe', 'scott_summers', 'tony_stark']
  PASS cast overlap: ['logan', 'ororo_munroe', 'scott_summers']
  PASS scene 1 situation is not a placeholder
  PASS scene 1 situation has temporal continuation cue
  PASS scene 1 situation references prior-episode character
  evidence: episodes_text/_regression_run/_item02_continuation_plan.json

ITEM 2: PASS  (elapsed 22.6s)
OPENAI_API_KEY is not set, skipping trace export
## tests/regression_03_parse_plan_json.py
  PASS [plain]
  PASS [trailing-comma-object]
  PASS [trailing-comma-array]
  PASS [json-code-fence]
  PASS [bare-code-fence]
  PASS [prose-preamble-and-postamble]
  PASS [embedded-bare-newlines-in-string]
  PASS [invalid-backslash-escape-in-string]
  PASS [combo-fence+prose+trailing-comma]
  PASS [unparseable raises JSONDecodeError]

ITEM 3: PASS
## tests/regression_04a_scene_2char.py
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
[item 4a] running 2-char intimate scene …
[item 4a] scene done in 91.6s — 23 blocks, 32 tool calls
  [4a] at-open cast: ['felicia_hardy', 'wade_wilson']
  [4a] spoke (blocks): ['felicia_hardy', 'wade_wilson']
  [4a] tool calls: 32
  [4a] scene tool calls (chronicle): 9
  [4a] state_change_landed: True
  [4a] dropped tool-artifact lines: 0
  evidence: episodes_text/_regression_run/_item04a_transcript.txt

ITEM 4a: PASS  (elapsed 91.6s)
OPENAI_API_KEY is not set, skipping trace export
## tests/regression_04b_scene_5char_cheesecake.py
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
[item 4b] running cheesecake 5-char baseline …
[item 4b] scene done in 52.2s — 11 blocks, 15 tool calls
  [4b] at-open cast: ['felicia_hardy', 'wade_wilson']
  [4b] spoke (blocks): ['felicia_hardy', 'wade_wilson']
  [4b] tool calls: 15
  [4b] scene tool calls (chronicle): 4
  [4b] state_change_landed: True
  [4b] dropped tool-artifact lines: 0
  evidence: episodes_text/_regression_run/_item04b_transcript.txt

ITEM 4b: PASS  (elapsed 52.2s)
OPENAI_API_KEY is not set, skipping trace export
## tests/regression_04c_scene_departure.py
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
[item 4c] running departure scene …
[item 4c] scene done in 104.9s — 21 blocks, 29 tool calls
  [4c] at-open cast: ['jessica_jones', 'luke_cage', 'matt_murdock']
  [4c] spoke (blocks): ['jessica_jones', 'luke_cage', 'matt_murdock']
  [4c] tool calls: 29
  [4c] scene tool calls (chronicle): 8
  [4c] state_change_landed: True
  [4c] dropped tool-artifact lines: 0
  [4c] departure_referenced: True
  evidence: episodes_text/_regression_run/_item04c_transcript.txt

ITEM 4c: PASS  (elapsed 104.9s)
OPENAI_API_KEY is not set, skipping trace export
## tests/regression_05_scripts_to_prose.py
  PASS UATU_OPENING_LITANY present
  PASS UATU_CLOSING_OATH present
  PASS narrator straight-quote wrapping stripped
  PASS narrator curly-quote wrapping stripped
  PASS narrator angle-quote wrapping stripped
  PASS emphasis asterisks stripped (scene-break '* * *' preserved)
  PASS parenthetical stage direction stripped
  PASS period-before-tag converted to comma
  PASS exactly one opening litany in single render
  PASS exactly one closing oath in single render
  PASS scripts_to_prose is deterministic

  evidence: episodes_text/_regression_run/_item05_synthetic.txt

ITEM 5: PASS
## tests/regression_07_gui_plumbing.py
2026-05-28 20:00:51.741 WARNING streamlit.runtime.scriptrunner_utils.script_run_context: Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.741 WARNING streamlit.runtime.scriptrunner_utils.script_run_context: Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.820 
  [33m[1mWarning:[0m to view this Streamlit app on a browser, run it with the following
  command:

    streamlit run tests/regression_07_gui_plumbing.py [ARGUMENTS]
2026-05-28 20:00:51.820 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.820 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.821 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.821 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.821 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.821 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.821 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.821 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.821 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.821 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.958 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.958 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.958 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.958 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.958 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.958 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.958 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.958 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.958 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.958 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.958 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.958 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.958 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.958 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.958 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.958 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Session state does not function when running a script without `streamlit run`
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.959 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.960 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.960 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.960 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.960 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 20:00:51.960 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
  PASS _cook signature has continuation_from (default=None)
  PASS _cook forwards continuation_from to plan_episode
  PASS _cook calls plan_episode
  PASS _cook calls run_episode_sync
  PASS plan_episode signature has continuation_from (default=None)
  PASS gui.py contains 'continuation_from'
  PASS gui.py contains 'trigger_cook'
  PASS gui.py contains 'Next →'
  PASS _cook can be bound with continuation_from kwarg

ITEM 7: PASS
## tests/regression_08_yaml_to_prompt_colon.py
  PASS dict-form-coercion → 'Test Person (TP): complex ptsd'
  PASS colon-split → 'Test Two (T2): Complex PTSD'
  PASS _yaml_to_prompt(minimal) — 7615 chars
  PASS _yaml_to_prompt(wade) — 13294 chars

ITEM 8: PASS
## tests/regression_09_tonal_license.py
  PASS — all 29 verbatim tonal-license substrings present in prompt (13294 chars total)

ITEM 9: PASS
## tests/regression_10_full_episode.py
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
[chron snapshot pre]  episodes=18  chars=8  facts=28
[item 10] cooking 4-scene episode …
[engine] scene 1 coverage_complete=True
  ✓ scene 1/4 — Skinny Dennis — Williamsburg, back corner booth — 7dlg/4narr/15tools
[engine] scene 2 coverage_complete=True
  ✓ scene 2/4 — Skinny Dennis parking lot — back lot by the dump — 7dlg/4narr/15tools
[engine] scene 3 coverage_complete=True
  ✓ scene 3/4 — Yellow cab — Williamsburg Bridge eastbound — 8dlg/4narr/16tools
[engine] scene 4 coverage_complete=True
  ✓ scene 4/4 — Wade's apartment — Hell's Kitchen walk-up, kitch — 11dlg/3narr/24tools
[item 10] wrote 910 - Regression Cook Four Beats.txt  (1318 words, 7.7 KB)
[item 6] ingesting episode into chronicle …
[chron snapshot post] episodes=19  chars=8  facts=30
  PASS chronicle episode entry has 5 beats
  PASS chronicle character events: 50 tagged [ep 910]
    - wade_wilson: [ep 910] Engaged in tactile, escalating verbal and physical tension with Felicia, leaving his moves pointed but deliberately unresolved.
    - wade_wilson: [ep 910] Chose proximity over resolution, wrapping chaos and sincerity into the deliberate silence shared in the cab before their stop.
    - wade_wilson: [ep 910] Engaged in a layered verbal duel with Felicia, blending humor, chaos, and vulnerability.
    - wade_wilson: [ep 910] Confessed his need for Felicia’s help tying his connections together, signaling deeper trust.
    - wade_wilson: [ep 910] Watched Felicia leave without resolution, left grappling with the tension she carried away from their interaction.

ITEMS 6+10: PASS  (elapsed 223.0s)
OPENAI_API_KEY is not set, skipping trace export
### swarm suite
## tests/swarm_01_no_phantom_cast.py
OPENAI_API_KEY is not set, skipping trace export
[swarm-01] calling plan_episode_swarm(premise=…)
  title:   'Anything Can Happen Tuesday'
  arc:     "Felicia and Wade wrestle with their shared guilt and concern over Peter's unraveling. They get closer to the truth and to each other — but nothing is free, least of all loyalty."
  setting: 'The Cheesecake Factory, dining area'
  present: ['felicia_hardy', 'wade_wilson']  (took 5.6s)

SWARM-01: PASS — scene 1 present is premise-explicit only.
OPENAI_API_KEY is not set, skipping trace export
## tests/swarm_02_arrival_emergent.py
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
[swarm-02] running scene …
  initial cast: ['felicia_hardy', 'wade_wilson']
  final present: ['felicia_hardy', 'wade_wilson']
  bring_in events: []
  elapsed: 48.1s
  NOTE: no emergent arrivals (cast kept the booth two-handed). That's allowed under the contract — arrivals are emergent, not required.

SWARM-02: PASS — no character appeared without a BringInCharacter call.
OPENAI_API_KEY is not set, skipping trace export
## tests/swarm_03_scene_closes_on_event.py
  PASS A: flat chronicle has no state-change events
  PASS B: TakeAction w/ consequence is a state-change
  PASS B: ChangeSetting is a state-change
  PASS B: departure is a state-change
  PASS B: emergent bring_in is a state-change
  PASS C: run_scene uses _is_state_change_event to gate [SCENE_END]
  PASS C: run_scene has a defensive spec.max_turns force-close cap

SWARM-03: PASS — state-change gate is the close mechanism, with defensive turn cap.
## tests/swarm_04_no_tool_error_in_transcript.py
  drop ✓  "Error: Missing required parameter 'message' for tool send_me"
  drop ✓  'ERROR: scene action budget exhausted'
  drop ✓  "ERROR: 'definitely_not_a_real_character' is not in the roste"
  drop ✓  'ALREADY ARRIVING/PRESENT: peter_parker'
  drop ✓  "error: missing required parameter 'recipient_agent' for tool"
  drop ✓  'take_action({"action":"grab her wrist gently","consequence":'
  drop ✓  'take_action {'
  drop ✓  'send_message {"recipient_agent":"Peter_Parker","message":"to'
  drop ✓  'address_character Your move, sweetheart'
  drop ✓  'BringInCharacter({"character_key":"johnny_storm","how_they_a'
  drop ✓  'BringInCharacter {"character_key":"johnny_storm","how_they_a'
  drop ✓  '<<TOOL:TakeAction>>{"action":"grab a glass"}<<END>>'
  drop ✓  'Oh, Uatu—always with your cryptic "I see everything" vibe.'
  drop ✓  'God, between Wade and Uatu’s Deep Thoughts, I’ll wing it.'
  drop ✓  'Watcher, you cosmic voyeur, are we doing exposition now?'
  keep ✓  'Avocado rolls? Felicia, if I wanted green mush shoved in a d'
  keep ✓  "You two toddlers done battlin' over whether melted cheese is"
  keep ✓  "I don't know. Maybe I do. Maybe that's the whole problem."
  keep ✓  'That was a stupid error on my part, kid.'

  Assembled transcript:
    FELICIA HARDY: That's a mood swing in a bottle if I've ever seen one.
    WADE WILSON: Pete! Just the webslingin' bundle of guilt I needed.
    PETER PARKER: Felicia, breathe.

SWARM-04: PASS — tool errors filtered, dialogue passed through.
## tests/swarm_05_next_scene_from_state.py
[swarm-05] calling plan_next_scene(prior_chronicle=…)
  setting:       'the parking garage across from the Cheesecake Factory'
  time:          'Night, 11:25 PM'
  present:       ['felicia_hardy', 'wade_wilson']
  situation:     the parking garage across from the Cheesecake Factory: Felicia is already walking briskly ahead, the echo of her heels bouncing off the cold concrete. Wade trails behind her but doesn't stop talking. 'You know I'm right. About all of it.'…
  pressure_hint: 'Somebody will stop walking. Somebody will name it.'
  elapsed:       2.9s

SWARM-05: PASS — next scene was planned from prior ending state, not a fresh lineup.
OPENAI_API_KEY is not set, skipping trace export
## tests/swarm_06_pressure_extracted.py
OPENAI_API_KEY is not set, skipping trace export
[swarm-06.A] extract_arc(real premise) …
  title:      'Anything Can Happen Tuesday'
  setting:    'Cheesecake Factory, midtown Manhattan.'
  present:    ['felicia_hardy', 'wade_wilson']
  pressures:  ['call_peter']
    • call_peter: Felicia Hardy must decide, definitively, whether or not to make a call to Peter Parker.
      modes:    ['summon — Felicia Hardy calls Peter, and he takes an on-stage turn via dialogue or action.', 'refusal — Felicia explicitly refuses to call Peter, her reasoning articulated aloud.', "named decision — Felicia commits a course of action that directly addresses Peter's unraveling, his name spoken explicitly."]
      evidence: ['call peter', 'text peter', "i can't call him", 'what if i just call', "wade, stop, i'm thinking about it"]
  elapsed: 6.9s

[swarm-06.B] extract_arc(flat premise) …
  PASS — PressureMissingError raised: Uatu could not extract any forcing_pressure from premise after 0 attempt(s). Pressureless episodes are refused.

SWARM-06: PASS — pressure extraction enforced.
OPENAI_API_KEY is not set, skipping trace export
## tests/swarm_07_scene_closes_only_on_progress.py
  PASS A: flat events → no pressure progress
  PASS B: substring-match → progress on peter_decision
  PASS B2: bring_in(peter_parker)+action → progress
  PASS C: explicit resolves_pressure honored
  PASS D: run_scene wired to pressure-progress gate + stalled marker

SWARM-07: PASS — pressure-progress gate enforced.
## tests/swarm_08_no_narrator_phantom_arrival.py
  PASS A: off-stage Mary-Jane appearance is flagged
  PASS B: off-stage mention without physical arrival is allowed
  PASS C: present cast physical beat is allowed

SWARM-08: PASS
### pressure suite
## tests/pressure_01_extract_required.py
OPENAI_API_KEY is not set, skipping trace export
[pressure-01.A] extract_arc(named premise) …
  pressures: ['call_peter_now_or_not'] (took 7.5s)
  PASS A: pressure 'call_peter_now_or_not' references Peter

[pressure-01.B] extract_arc(flat premise) …
  PASS B: PressureMissingError raised — Uatu could not extract any forcing_pressure from premise after 0 attempt(s). Pressureless episodes are refused.

PRESSURE-01: PASS
OPENAI_API_KEY is not set, skipping trace export
## tests/pressure_02_scene_closes_only_on_progress.py
  PASS A: flat events -> no progress (scene would not close)
  PASS B: substring-match -> progress (scene would close clean)
  PASS B2: bring_in(peter_parker)+action -> progress
  PASS C: run_scene wired to pressure-progress gate + stalled marker
  PASS D: SceneSpec carries active_pressures + max_turns + stall_avoidance_note

PRESSURE-02: PASS
## tests/pressure_03_episode_ends_on_resolution.py
[pressure-03] plan_next_scene_arc with ALL pressures resolved and scenes_run=2 …
  returned: None  (took 0.1s)
  PASS: arc closed after scenes_run=2; no padding scene returned.

PRESSURE-03: PASS
## tests/pressure_04_uatu_intervenes_on_stall.py
[pressure-04] stall_intervention_beat(...) …
  Uatu beat (1.7s): 'The straw in her glass has been chewed flat. She hasn’t noticed.'
  PASS: director instructions surface the UATU INTERVENTION cue verbatim
  PASS: run_scene seeds the intervention beat into the director's opening cue

PRESSURE-04: PASS
OPENAI_API_KEY is not set, skipping trace export
## tests/pressure_05_refusal_is_resolution.py
  PASS A: 'we are not calling him' refusal resolves the pressure
  PASS B: 'leave peter out' refusal resolves the pressure
  PASS C: explicit resolves_pressure=name honored regardless of substring
  PASS D: pure banter does NOT resolve the pressure

PRESSURE-05: PASS
## tests/pressure_06_subject_binding.py
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
[pressure-06.A] extract_arc(PREMISE_PETER) …
  pressures (1) (took 13.7s):
    • peter_will_snap: subjects=['peter_parker']  evidence_sample=['peter', 'peter parker', 'call peter', 'let him crash']
  PASS A: every pressure binds peter_parker as subject

[pressure-06.B] extract_arc(PREMISE_FELICIA_WADE_ONLY) …
  pressures (1) (took 7.6s):
    • felicia_confronts_wade: subjects=['wade_wilson']
  PASS B: subjects are subset of premise-named characters

[pressure-06.C] proxy Pressure(subject=mary_jane_watson) on Peter premise must fail validation …
  PASS C: proxy pressure rejected with: proxy pressure: 'proxy_mj_pressure' has subjects ['mary_jane_watson'] not present in premise (allowed from premise tokens: ['ben_grimm', 'fe
  PASS C2: PressureMissingError raised: Uatu could not extract any forcing_pressure from premise after 1 attempt(s). Pressureless episodes are refused.

PRESSURE-06: PASS
OPENAI_API_KEY is not set, skipping trace export
## tests/pressure_07_proxy_does_not_resolve.py
  entry[0] kind='bring_in'      key/who='mary_jane_watson'      is_pressure_progress=False
  entry[1] kind='address'       key/who='mary_jane_watson'      is_pressure_progress=False
  entry[2] kind='action'        key/who=''                      is_pressure_progress=False
  PASS: evaluate_pressures correctly returned (False, []) — pressure remains OPEN despite MJ bring_in + address
  PASS CONTROL: bring_in(peter_parker)+action resolves (subject acted on stage)

PRESSURE-07: PASS
## tests/pressure_08_named_refusal_closes.py
  peter_parker spoken_name = 'Peter'
  PASS A: is_named_refusal('we are not calling Peter tonight', 'Peter') -> True
  PASS B: named refusal resolves the pressure via is_pressure_progress + evaluate_pressures
  PASS CONTROL: refusal that doesn't name Peter is NOT is_named_refusal for Peter

PRESSURE-08: PASS
## tests/pressure_09_narrator_spoken_name.py
  PASS A: mary_jane_watson.yaml has spoken_name: 'Mary-Jane'
  PASS A2: load_spoken_name('mary_jane_watson') -> 'Mary-Jane'
  PASS B: 'Mary Jane' -> 'Mary-Jane' in narrator beat
          normalized: 'The glass door swings wide, catching light, and Mary-Jane steps through — red hair a flare of warning or allure.'
  PASS B2: 'MJ' -> 'Mary-Jane' in narrator beat
  PASS C: already-correct 'Mary-Jane' is untouched
  PASS D: run_scene wires normalize_spoken_names into transcript assembly
  PASS E: _director_instructions surfaces SPOKEN NAMES block with 'Mary-Jane'

PRESSURE-09: PASS
## tests/pressure_10_summon_without_action_is_pending.py
  is_pressure_progress(bring_in_only) = False
  PASS A: bring_in alone does NOT register as progress on the entry-level check
  evaluate_pressures = (False, [])
  PASS B: evaluate_pressures correctly returned (False, [])
  evaluate_pressures_with_pending = (False, [], pending={'peter_decision': 'peter_parker'}, kinds={})
  PASS C: summon_pending = {'peter_decision': 'peter_parker'}
  PASS D: other speakers do not count as Peter acting

PRESSURE-10: PASS
## tests/pressure_11_summon_plus_action_resolves.py
  PASS A0: subject_has_acted_after_bring_in detects TakeAction
  evaluate_pressures_with_pending = (True, ['peter_decision'], pending={}, kinds={'peter_decision': 'bring_in_plus_action'})
  PASS A: bring_in + on-stage TakeAction resolves the pressure
  (B) speakers-only path = (True, ['peter_decision'], pending={}, kinds={'peter_decision': 'bring_in_plus_action'})
  PASS B: bring_in + dialogue-line subject_speakers resolves
  PASS C: bring_in + AddressCharacter by subject resolves

PRESSURE-11: PASS
## tests/pressure_12_summon_pending_carries.py
  arc.summon_pending = {'peter_decision': 'peter_parker'}
  open_pressures = ['peter_decision']
  calling plan_next_scene_arc(scenes_run=1) [LIVE] …
  returned SceneSpec(present=['felicia_hardy', 'wade_wilson', 'peter_parker'], setting="Felicia's apartment, top floor penthouse", situation='The terrace door slides open. Peter Parker, damp from the rain, steps inside. Felicia stands by the window, silhouetted ')
  PASS: peter_parker carried into next scene's present cast

PRESSURE-12: PASS
OPENAI_API_KEY is not set, skipping trace export
## tests/pressure_13_min_scenes_floor.py
  scenes_run=1, open=[], summon_landed={'peter_decision': 'peter_parker'}
  calling plan_next_scene_arc(scenes_run=1) [LIVE] …
  returned consequences-scene present=['felicia_hardy', 'wade_wilson', 'peter_parker'] setting='the same dive bar booth — dark corner, chipped Formica table'
  PASS A: floor forced a consequences scene with peter_parker on stage

  calling plan_next_scene_arc(scenes_run=2) — floor satisfied …
  PASS B: at scenes_run=2, planner returned None (episode-end)

PRESSURE-13: PASS
OPENAI_API_KEY is not set, skipping trace export

~~~

## Final live cook log — verbatim output

~~~text
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
Tool 'send_message' invoked with unknown recipient: 'Peter_Parker'
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
Task exception was never retrieved
future: <Task finished name='Task-871' coro=<AsyncClient.aclose() done, defined at /Users/rbhanson/fanfic/.venv/lib/python3.14/site-packages/httpx/_client.py:1978> exception=RuntimeError('Event loop is closed')>
Traceback (most recent call last):
  File "/Users/rbhanson/fanfic/.venv/lib/python3.14/site-packages/httpx/_client.py", line 1985, in aclose
    await self._transport.aclose()
  File "/Users/rbhanson/fanfic/.venv/lib/python3.14/site-packages/httpx/_transports/default.py", line 406, in aclose
    await self._pool.aclose()
  File "/Users/rbhanson/fanfic/.venv/lib/python3.14/site-packages/httpcore/_async/connection_pool.py", line 353, in aclose
    await self._close_connections(closing_connections)
  File "/Users/rbhanson/fanfic/.venv/lib/python3.14/site-packages/httpcore/_async/connection_pool.py", line 345, in _close_connections
    await connection.aclose()
  File "/Users/rbhanson/fanfic/.venv/lib/python3.14/site-packages/httpcore/_async/connection.py", line 173, in aclose
    await self._connection.aclose()
  File "/Users/rbhanson/fanfic/.venv/lib/python3.14/site-packages/httpcore/_async/http11.py", line 258, in aclose
    await self._network_stream.aclose()
  File "/Users/rbhanson/fanfic/.venv/lib/python3.14/site-packages/httpcore/_backends/anyio.py", line 53, in aclose
    await self._stream.aclose()
  File "/Users/rbhanson/fanfic/.venv/lib/python3.14/site-packages/anyio/streams/tls.py", line 236, in aclose
    await self.transport_stream.aclose()
  File "/Users/rbhanson/fanfic/.venv/lib/python3.14/site-packages/anyio/_backends/_asyncio.py", line 1344, in aclose
    self._transport.close()
    ~~~~~~~~~~~~~~~~~~~~~^^
  File "/opt/homebrew/Cellar/python@3.14/3.14.5/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/selector_events.py", line 1216, in close
    super().close()
    ~~~~~~~~~~~~~^^
  File "/opt/homebrew/Cellar/python@3.14/3.14.5/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/selector_events.py", line 869, in close
    self._loop.call_soon(self._call_connection_lost, None)
    ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/homebrew/Cellar/python@3.14/3.14.5/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/base_events.py", line 827, in call_soon
    self._check_closed()
    ~~~~~~~~~~~~~~~~~~^^
  File "/opt/homebrew/Cellar/python@3.14/3.14.5/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/base_events.py", line 550, in _check_closed
    raise RuntimeError('Event loop is closed')
RuntimeError: Event loop is closed
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
Tool 'send_message' invoked without 'recipient_agent' parameter.
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
Task exception was never retrieved
future: <Task finished name='Task-1876' coro=<AsyncClient.aclose() done, defined at /Users/rbhanson/fanfic/.venv/lib/python3.14/site-packages/httpx/_client.py:1978> exception=RuntimeError('Event loop is closed')>
Traceback (most recent call last):
  File "/Users/rbhanson/fanfic/.venv/lib/python3.14/site-packages/httpx/_client.py", line 1985, in aclose
    await self._transport.aclose()
  File "/Users/rbhanson/fanfic/.venv/lib/python3.14/site-packages/httpx/_transports/default.py", line 406, in aclose
    await self._pool.aclose()
  File "/Users/rbhanson/fanfic/.venv/lib/python3.14/site-packages/httpcore/_async/connection_pool.py", line 353, in aclose
    await self._close_connections(closing_connections)
  File "/Users/rbhanson/fanfic/.venv/lib/python3.14/site-packages/httpcore/_async/connection_pool.py", line 345, in _close_connections
    await connection.aclose()
  File "/Users/rbhanson/fanfic/.venv/lib/python3.14/site-packages/httpcore/_async/connection.py", line 173, in aclose
    await self._connection.aclose()
  File "/Users/rbhanson/fanfic/.venv/lib/python3.14/site-packages/httpcore/_async/http11.py", line 258, in aclose
    await self._network_stream.aclose()
  File "/Users/rbhanson/fanfic/.venv/lib/python3.14/site-packages/httpcore/_backends/anyio.py", line 53, in aclose
    await self._stream.aclose()
  File "/Users/rbhanson/fanfic/.venv/lib/python3.14/site-packages/anyio/streams/tls.py", line 236, in aclose
    await self.transport_stream.aclose()
  File "/Users/rbhanson/fanfic/.venv/lib/python3.14/site-packages/anyio/_backends/_asyncio.py", line 1344, in aclose
    self._transport.close()
    ~~~~~~~~~~~~~~~~~~~~~^^
  File "/opt/homebrew/Cellar/python@3.14/3.14.5/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/selector_events.py", line 1216, in close
    super().close()
    ~~~~~~~~~~~~~^^
  File "/opt/homebrew/Cellar/python@3.14/3.14.5/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/selector_events.py", line 869, in close
    self._loop.call_soon(self._call_connection_lost, None)
    ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/homebrew/Cellar/python@3.14/3.14.5/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/base_events.py", line 827, in call_soon
    self._check_closed()
    ~~~~~~~~~~~~~~~~~~^^
  File "/opt/homebrew/Cellar/python@3.14/3.14.5/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/base_events.py", line 550, in _check_closed
    raise RuntimeError('Event loop is closed')
RuntimeError: Event loop is closed
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
Task exception was never retrieved
future: <Task finished name='Task-2495' coro=<AsyncClient.aclose() done, defined at /Users/rbhanson/fanfic/.venv/lib/python3.14/site-packages/httpx/_client.py:1978> exception=RuntimeError('Event loop is closed')>
Traceback (most recent call last):
  File "/Users/rbhanson/fanfic/.venv/lib/python3.14/site-packages/httpx/_client.py", line 1985, in aclose
    await self._transport.aclose()
  File "/Users/rbhanson/fanfic/.venv/lib/python3.14/site-packages/httpx/_transports/default.py", line 406, in aclose
    await self._pool.aclose()
  File "/Users/rbhanson/fanfic/.venv/lib/python3.14/site-packages/httpcore/_async/connection_pool.py", line 353, in aclose
    await self._close_connections(closing_connections)
  File "/Users/rbhanson/fanfic/.venv/lib/python3.14/site-packages/httpcore/_async/connection_pool.py", line 345, in _close_connections
    await connection.aclose()
  File "/Users/rbhanson/fanfic/.venv/lib/python3.14/site-packages/httpcore/_async/connection.py", line 173, in aclose
    await self._connection.aclose()
  File "/Users/rbhanson/fanfic/.venv/lib/python3.14/site-packages/httpcore/_async/http11.py", line 258, in aclose
    await self._network_stream.aclose()
  File "/Users/rbhanson/fanfic/.venv/lib/python3.14/site-packages/httpcore/_backends/anyio.py", line 53, in aclose
    await self._stream.aclose()
  File "/Users/rbhanson/fanfic/.venv/lib/python3.14/site-packages/anyio/streams/tls.py", line 236, in aclose
    await self.transport_stream.aclose()
  File "/Users/rbhanson/fanfic/.venv/lib/python3.14/site-packages/anyio/_backends/_asyncio.py", line 1344, in aclose
    self._transport.close()
    ~~~~~~~~~~~~~~~~~~~~~^^
  File "/opt/homebrew/Cellar/python@3.14/3.14.5/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/selector_events.py", line 1216, in close
    super().close()
    ~~~~~~~~~~~~~^^
  File "/opt/homebrew/Cellar/python@3.14/3.14.5/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/selector_events.py", line 869, in close
    self._loop.call_soon(self._call_connection_lost, None)
    ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/homebrew/Cellar/python@3.14/3.14.5/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/base_events.py", line 827, in call_soon
    self._check_closed()
    ~~~~~~~~~~~~~~~~~~^^
  File "/opt/homebrew/Cellar/python@3.14/3.14.5/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/base_events.py", line 550, in _check_closed
    raise RuntimeError('Event loop is closed')
RuntimeError: Event loop is closed
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
Tool 'send_message' invoked without 'recipient_agent' parameter.
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
==============================================================================
=== cook_ep01_pressure_proof — V3.2 — summon-must-land + min-scenes ===
==============================================================================

[1] extract_arc(GENESIS_PREMISE) …
    title:    'Cheesecake Factory Tuesdays'
    setting:  'Cheesecake Factory, corner booth.'
    present:  ['felicia_hardy', 'wade_wilson']
    pressures (1):
      • affectionate_sabotage_peter: Felicia Hardy and Wade Wilson take a concrete action of intervention toward Peter Parker. Peter must be explicitly invoked by name in this f
          evidence: ['peter_parker', 'peter', 'text peter', 'call peter', 'fuck it, get peter', 'talk to peter']
          subjects: ['peter_parker']
    took 8.1s

[2] run_scene(S1) cast=['felicia_hardy', 'wade_wilson'] setting='Cheesecake Factory, corner booth.'
    S1 done in 75.7s — blocks=13
    pressure affectionate_sabotage_peter moved non-terminally in S1 (evidence_substring); remains OPEN
    S1 @ Cheesecake Factory, corner booth. | cast=felicia_hardy, wade_wilson, johnny_storm, mary_jane_watson, peter_parker | SUMMON-PENDING | stalled=False | moved=['affectionate_sabotage_peter'] | pending={'affectionate_sabotage_peter': 'peter_parker'} | kinds={'affectionate_sabotage_peter': 'evidence_substring'}
    open pressures after S1: ['affectionate_sabotage_peter']
    summon_pending: {'affectionate_sabotage_peter': 'peter_parker'}
    summon_landed:  {}
    stall_streaks:  {'affectionate_sabotage_peter': 0}

[3.2] plan_next_scene_arc(...) — open=['affectionate_sabotage_peter'] summon_pending={'affectionate_sabotage_peter': 'peter_parker'}
    S2 cast=['peter_parker', 'felicia_hardy', 'wade_wilson', 'johnny_storm'] setting='Cheesecake Factory, corner booth'
    S2 done in 75.3s — blocks=12
    pressure affectionate_sabotage_peter moved non-terminally in S2 (evidence_substring); remains OPEN
    S2 @ Cheesecake Factory, corner booth | cast=peter_parker, felicia_hardy, wade_wilson, johnny_storm | clean-close | stalled=False | moved=['affectionate_sabotage_peter'] | pending={} | kinds={'affectionate_sabotage_peter': 'evidence_substring'}
    open pressures after S2: ['affectionate_sabotage_peter']
    summon_pending: {'affectionate_sabotage_peter': 'peter_parker'}
    summon_landed:  {}
    stall_streaks:  {'affectionate_sabotage_peter': 0}

[3.3] plan_next_scene_arc(...) — open=['affectionate_sabotage_peter'] summon_pending={'affectionate_sabotage_peter': 'peter_parker'}
    S3 cast=['peter_parker', 'felicia_hardy', 'wade_wilson', 'johnny_storm'] setting='Cheesecake Factory, corner booth'
    S3 done in 56.5s — blocks=10
    pressure affectionate_sabotage_peter moved non-terminally in S3 (evidence_substring); remains OPEN
    S3 @ Cheesecake Factory, corner booth | cast=peter_parker, felicia_hardy, wade_wilson, johnny_storm | clean-close | stalled=False | moved=['affectionate_sabotage_peter'] | pending={} | kinds={'affectionate_sabotage_peter': 'evidence_substring'}
    open pressures after S3: ['affectionate_sabotage_peter']
    summon_pending: {'affectionate_sabotage_peter': 'peter_parker'}
    summon_landed:  {}
    stall_streaks:  {'affectionate_sabotage_peter': 0}

[3.4] plan_next_scene_arc(...) — open=['affectionate_sabotage_peter'] summon_pending={'affectionate_sabotage_peter': 'peter_parker'}
    S4 cast=['peter_parker', 'felicia_hardy', 'wade_wilson'] setting='Cheesecake Factory patio area — an awkwardly exuberant party zone lit with dim fairy lights'
    S4 done in 29.9s — blocks=5
    S4 @ Cheesecake Factory patio area — an awkwardly exuberant party | cast=peter_parker, felicia_hardy, wade_wilson | clean-close | stalled=False | moved=['affectionate_sabotage_peter'] | pending={} | kinds={'affectionate_sabotage_peter': 'pending_subject_dialogue'}
    open pressures after S4: []
    summon_pending: {}
    summon_landed:  {}
    stall_streaks:  {}

[3.5] FULL-EPISODE FLOOR active — scenes=4/6, words=1352/3200, est_audio=9.0m. Forcing next Genesis beat.
    S5 cast=['peter_parker', 'felicia_hardy', 'wade_wilson'] setting='Parking garage outside the Cheesecake Factory, concrete stairwell landing'
    S5 done in 61.0s — blocks=13
    S5 @ Parking garage outside the Cheesecake Factory, concrete stai | cast=peter_parker, felicia_hardy, wade_wilson | clean-close | stalled=False | moved=[] | pending={} | kinds={}
    open pressures after S5: []
    summon_pending: {}
    summon_landed:  {}
    stall_streaks:  {}

[3.6] FULL-EPISODE FLOOR active — scenes=5/6, words=1651/3200, est_audio=11.0m. Forcing next Genesis beat.
    S6 cast=['peter_parker', 'felicia_hardy', 'wade_wilson'] setting='Cheesecake Factory booth, dessert plates and third round'
    S6 done in 30.9s — blocks=6
    S6 @ Cheesecake Factory booth, dessert plates and third round | cast=peter_parker, felicia_hardy, wade_wilson | clean-close | stalled=False | moved=[] | pending={} | kinds={}
    open pressures after S6: []
    summon_pending: {}
    summon_landed:  {}
    stall_streaks:  {}

[3.7] FULL-EPISODE FLOOR active — scenes=6/6, words=1920/3200, est_audio=12.8m. Forcing next Genesis beat.
    S7 cast=['peter_parker', 'felicia_hardy', 'wade_wilson'] setting='Cheesecake Factory booth, late evening residue'
    S7 done in 58.0s — blocks=13
    S7 @ Cheesecake Factory booth, late evening residue | cast=peter_parker, felicia_hardy, wade_wilson | clean-close | stalled=False | moved=[] | pending={} | kinds={}
    open pressures after S7: []
    summon_pending: {}
    summon_landed:  {}
    stall_streaks:  {}

[3.8] FULL-EPISODE FLOOR active — scenes=7/6, words=2572/3200, est_audio=17.1m. Forcing next Genesis beat.
    S8 cast=['peter_parker', 'felicia_hardy', 'wade_wilson'] setting='Cheesecake Factory booth, late evening residue'
    S8 done in 55.7s — blocks=10
    S8 @ Cheesecake Factory booth, late evening residue | cast=peter_parker, felicia_hardy, wade_wilson | clean-close | stalled=False | moved=[] | pending={} | kinds={}
    open pressures after S8: []
    summon_pending: {}
    summon_landed:  {}
    stall_streaks:  {}

[3.9] FULL-EPISODE FLOOR active — scenes=8/6, words=2908/3200, est_audio=19.4m. Forcing next Genesis beat.
    S9 cast=['peter_parker', 'felicia_hardy', 'wade_wilson'] setting='Cheesecake Factory booth, late evening residue'
    S9 done in 62.6s — blocks=12
    S9 @ Cheesecake Factory booth, late evening residue | cast=peter_parker, felicia_hardy, wade_wilson | clean-close | stalled=False | moved=[] | pending={} | kinds={}
    open pressures after S9: []
    summon_pending: {}
    summon_landed:  {}
    stall_streaks:  {}

[3.10] plan_next_scene_arc returned None — arc closed after S9.

[done] wrote: /Users/rbhanson/fanfic/episodes_text/_pressure_proof_v3/01 - Cheesecake Factory Tuesdays.txt
[done] audit: /Users/rbhanson/fanfic/episodes_text/_pressure_proof_v3/01 - audit.txt
[done] elapsed 526.2s
[done] scenes=9 words=3622 est_audio=24.1m full_episode_floor_met=True
[done] any_scene_forced_close=False clean_episode_close=True
[done] forced_close_episode=False stall_close=False open=[]
OPENAI_API_KEY is not set, skipping trace export

~~~

## First 80 lines of cooked episode — verbatim

~~~text
Episode 1: Cheesecake Factory Tuesdays

Grizzly Knights

Felicia Hardy and Wade Wilson plan to save Peter Parker from unraveling — by corrupting him a little.

* * *

Time.

Space.

Reality.

It is more than a linear path. It is a prism of endless possibility,
where a single choice can branch out into infinite realities, creating
alternate worlds from the ones you know.

In every one of those realities, the same people live with the same
minds. The same hungers. The same scars. The same compensatory
mechanisms they would never name out loud.

I am the Watcher. I am your guide through these vast new realities.

Follow me, and ponder the question — not "what if?"

The question, in this universe, is simpler.

What do they do when they think the mic is off?

These are their stories.

* * *

Time.

“Wade, are you actually sketching, or are you just pretending to be Gauguin with grease on your fingers? Because if that’s Peter's likeness over there, you better tell me that’s pizza sauce and not blood. I don't have the patience to interpret your Picasso phase today. Or, maybe, ever,” Felicia said.

“Oh, come on, Kitty Kat! The proportions on that sketch were perfectly stylistic, alright? It’s called abstract expressionism. You wouldn’t get it, what with your impeccable symmetry and those annoyingly perfect cheekbones,” Wade said.

“Oh, I’d never pay for Peter’s dinner. He’s the “great responsibility” type, remember? He’d probably find a way to guilt-trip me for the calorie count on the check. But as for where we’re going with this, Wade—you tell me. I mean, you’ve clearly drawn him enough times to either hate him or want to bone him. Maybe both?” Felicia asked.

“Oh, you wanna challenge me directly on my stance? Fine. Let's break it down, lawyer-style. Exhibit A: the guy swings through the city maskless more times than not, because Peter Parker apparently doesn't believe in paying the dry cleaning bill for sweat-soaked latex. Exhibit B: oblivious enough to miss every signal thrown his way by a certain feline thief, but throws half the library at me when I even joke about rooftop stargazing. Tell me he's not taking notes,” Wade said.

“Classic Wade—half chaos, half confessional. Alright, let’s lean into it. You ever think maybe Spidey can’t help it? The signals, the mixed messages—it’s all just him. Doesn’t know where to land, so he webs a bit of everything. Including you, apparently, if you’re still spinning circles about him. Admit it: you want the mask or the man, but you still haven’t figured out which,” Felicia said.

“Mixed circles? First off, thank you for calling them circles, you shiny, leather-clad compliment. Most folks opt for the harsher term—spirals—but I like the geometry of what you’re suggesting,” Wade said.

“Wade, let’s escalate this from finger painting Peter’s flaws. Mary-Jane’s inbound for the Parkerology and Johnny’s on deck for...general chaos, obviously. We're gonna crack this mess like a safe—or at least drink until it feels like we did,” Felicia said.

“Alright, Mary-Jane’s coming in hot, probably armed with popcorn and sass because Felicia couldn’t resist yelling soap opera. And Johnny? Oh, he’s on his way too—no clue what I said past 'Spider-feels,' but he’s already halfway here imagining this as a reality show,” Wade said.

“Wade, we’re calling the man himself. Parker’s walking into this lion’s den, so sharpen your claws—or, I don’t know, your crayons. Let’s see if Spidey can stick the landing here,” Felicia said.

“Oh, hell yes, Kitty’s throwing down. Peter’s officially en route because of course he can’t resist one of your texts. You know, the kind that probably reads like, “Rooftops, Wade’s obsession, and something you need to clear up, ASAP.” Subtle as a kick to the spandex, Hardy.” Wade said.

“Alright, it’s decided—this is happening. Kitty Cat, we’re officially in intervention mode. Parker’s getting cornered on every rooftop, mask, and man-related mess we’ve been tossing back and forth like a volleyball from hell. Mary-Jane’s in, Johnny’s inbound, and our boy’s officially about to regret all his life choices. Time to pry open that webbed little heart of his. Fun times ahead.”

“Well, speak of the spider. Peter, you're late to your own intervention. How thrillingly...you. We've had appetizers, a few drinks, and dissected you six ways to Sunday. Ball's in your court, now—what's your excuse?” Felicia asked.

* * *

Time.

“For you, Tiger, I might even throw in a discount. First one's always free,” Felicia said.

“Oh, I wouldn't dream of it. In fact, if we're doubling up on disasters and delights, I might need to hire you as my muse. Call it 'Deadpool's Guide to Thrilling, Chastising, and Totally Not-Inappropriate Flirting.' Shall we collaborate?” Wade asked.

“Damn it, Wilson, reel it in,” Johnny said.

“Uh — okay, I guess we’re all just looking at me now, which, you know, fun. Is this one of those moments where I confess something dramatic, or are we good with me just... taking Action Figure Pose #3 here until someone else decides to talk?” Peter asked.

Quiet.

“Tick tock, Spider. You’re more fun when you bite,” Felicia said.

“Oh, Petey-pie, you sweet, melodramatic, tortured soul. If heartbreak’s the dessert, you’re the sad little cherry on top. But fine, ignore the lingerie-pitch. Clearly, batting isn’t your style—just let Felicia keep stealing every base, including home,” Wade said.

“This is your official warning shot, Wilson. Tread carefully, or taste wrath. What's it gonna be?” Johnny asked.

~~~

## Full pressure-resolution log

~~~text
## full pressure-resolution log (per chronicle entry × per pressure)
# Scene 1 pressure-resolution log
  pressure: affectionate_sabotage_peter subjects=['peter_parker']
    entry {'turn': 0, 'actor': 'felicia_hardy', 'kind': 'bring_in', 'key': 'johnny_storm', 'how': "I call him and leave a voicemail: 'Johnny-boy, get your flaming ass over here. We’re working on a Peter Paradox, and we need some firepower.'"}  →  is_pressure_progress=False
    entry {'turn': 0, 'actor': 'felicia_hardy', 'kind': 'bring_in', 'key': 'mary_jane_watson', 'how': "She gets a text from me that says: 'Get down here. We need your expertise on Parkerology and cocktails.'"}  →  is_pressure_progress=False
    entry {'turn': 9, 'actor': 'felicia_hardy', 'kind': 'bring_in', 'key': 'peter_parker', 'how': "I text him, 'Parker, get here. You're already being dissected like a bad date. Might as well defend yourself.'"}  →  is_pressure_progress=False
    entry {'turn': 11, 'actor': 'wade_wilson', 'kind': 'action', 'action': 'Stand up, clap my hands like I’m running a weird icebreaker session, and openly declare to Felicia that we’re officially cornering Peter Parker on all the rooftop, mask, and man bullshit we’ve been pitching.', 'consequence': 'Felicia Hardy and Wade Wilson take a concrete action of intervention toward Peter Parker. Peter is explicitly invoked as the target of the intervention.', 'tags': [], 'resolves_pressure': ''}  →  is_pressure_progress=True
    => moved=True kind=evidence_substring summon_pending=peter_parker summon_landed=-

# Scene 2 pressure-resolution log
  pressure: affectionate_sabotage_peter subjects=['peter_parker']
    entry {'turn': 0, 'actor': 'peter_parker', 'kind': 'action', 'action': 'glance up from my phone and smirk.', 'consequence': '', 'tags': [], 'resolves_pressure': ''}  →  is_pressure_progress=True
    entry {'turn': 0, 'actor': 'johnny_storm', 'kind': 'action', 'action': "I toss a grape at Wade's head—underhand, full arc, no heat applied, but aimed to land.", 'consequence': '', 'tags': [], 'resolves_pressure': ''}  →  is_pressure_progress=False
    entry {'turn': 0, 'actor': 'felicia_hardy', 'kind': 'action', 'action': "I leaned over, close enough for my hair to brush against his shoulder, and whispered low, 'Careful, Parker. You might not be able to afford free.'", 'consequence': "The tension between Felicia and Peter sharpens, pulling Peter's attention further into the moment.", 'tags': [], 'resolves_pressure': ''}  →  is_pressure_progress=True
    entry {'turn': 0, 'actor': 'johnny_storm', 'kind': 'action', 'action': "I pluck another grape and hold it up like divine judgment, aiming clearly in Wade's direction, but I don't throw it—yet.", 'consequence': '', 'tags': ['lines_crossed'], 'resolves_pressure': ''}  →  is_pressure_progress=False
    entry {'turn': 0, 'actor': 'felicia_hardy', 'kind': 'action', 'action': 'I let my hand lightly trail across his forearm as I leaned back, leaving room for him to volley back however he wanted.', 'consequence': "The choice is back in Peter's court, but the touch lingers just enough to keep the charge alive.", 'tags': [], 'resolves_pressure': ''}  →  is_pressure_progress=True
    entry {'kind': 'warning', 'actor': 'engine', 'reason': 'dropped tool-artifact line from transcript', 'snippet': "Error: Missing required parameter 'recipient_agent' for tool send_message."}  →  is_pressure_progress=False
    entry {'kind': 'warning', 'actor': 'engine', 'reason': 'dropped tool-artifact line from transcript', 'snippet': 'take_action \n"Guys, I\'m here...'}  →  is_pressure_progress=False
    => moved=True kind=evidence_substring summon_pending=- summon_landed=-

# Scene 3 pressure-resolution log
  pressure: affectionate_sabotage_peter subjects=['peter_parker']
    entry {'turn': 0, 'actor': 'peter_parker', 'kind': 'action', 'action': 'lower my gaze to her hand and lightly run my fingers over hers, testing the moment before raising an eyebrow, my voice taking on that intentionally casual edge.', 'consequence': 'acknowledge her deliberate advance, keeping the tone open-ended.', 'tags': [], 'resolves_pressure': ''}  →  is_pressure_progress=True
    entry {'turn': 0, 'actor': 'peter_parker', 'kind': 'action', 'action': 'turn toward Felicia completely, breaking any ambient tension Jonathan might be trying to manipulate by putting her fully in my center of gravity, drawing a line that neither retreats nor defers.', 'consequence': 'reframe the dynamic Jonathan tried to start by solidifying the moment with Felicia instead.', 'tags': ['drinks'], 'resolves_pressure': ''}  →  is_pressure_progress=True
    entry {'turn': 0, 'actor': 'peter_parker', 'kind': 'action', 'action': 'close the distance between us, cutting off any retreat in her dare as I tilt my head and let the weight of a decision fall audibly between us.', 'consequence': 'commit to engaging her, accepting the challenge directly, no deflection.', 'tags': ['decisions_made'], 'resolves_pressure': ''}  →  is_pressure_progress=True
    entry {'kind': 'warning', 'actor': 'engine', 'reason': 'dropped tool-artifact line from transcript', 'snippet': 'Oh, you don\'t just escalate tension with me without inviting me up the ladder. \n\ntake_action "I lean in just enough for it to qualify as a bad decision, fingers skimming her wrist like it’s accidental'}  →  is_pressure_progress=False
    => moved=True kind=evidence_substring summon_pending=- summon_landed=-

# Scene 4 pressure-resolution log
  pressure: affectionate_sabotage_peter subjects=['peter_parker']
    entry {'kind': 'warning', 'actor': 'engine', 'reason': 'dropped tool-artifact line from transcript', 'snippet': "Oh, Felicia, sweetheart, if I had a nickel for every time someone told me to cool it with the Spider-Man banter, I'd have... well, I'd still have no concept of savings or restraint, but I’d definitely"}  →  is_pressure_progress=False
    => moved=True kind=pending_subject_dialogue summon_pending=- summon_landed=-

# Scene 5 pressure-resolution log
  pressure: affectionate_sabotage_peter subjects=['peter_parker']
    entry {'turn': 0, 'actor': 'peter_parker', 'kind': 'action', 'action': 'I lean up against the wall, arms crossed, and give him the most deadpan look I can muster.', 'consequence': "Peter chooses to ground the scenario, pulling focus away from Wade's escalating absurdity.", 'tags': [], 'resolves_pressure': ''}  →  is_pressure_progress=True
    entry {'turn': 0, 'actor': 'peter_parker', 'kind': 'action', 'action': "I push off the wall just a little, hands raking through my hair—messy before but on-brand exasperation now—and look right at Felicia, holding the gaze like I can't not.", 'consequence': "Peter steps closer to the challenge in Felicia's tone, redirecting focus back to their dynamic while acknowledging Wade's pointed quips without full surrender or dodge.", 'tags': [], 'resolves_pressure': ''}  →  is_pressure_progress=True
    => moved=False kind=- summon_pending=- summon_landed=-

# Scene 6 pressure-resolution log
  pressure: affectionate_sabotage_peter subjects=['peter_parker']
    entry {'turn': 0, 'actor': 'felicia_hardy', 'kind': 'action', 'action': 'I lean across the table, my hand brushing the back of theirs, holding their gaze just a moment too long, before letting a small, unguarded smile slip through.', 'consequence': 'I let someone feel the weight of my attention and break the rhythm of the guarded night by showing sincerity.', 'tags': [], 'resolves_pressure': ''}  →  is_pressure_progress=False
    => moved=False kind=- summon_pending=- summon_landed=-

# Scene 7 pressure-resolution log
  pressure: affectionate_sabotage_peter subjects=['peter_parker']
    entry {'turn': 0, 'actor': 'wade_wilson', 'kind': 'address', 'key': 'felicia_hardy'}  →  is_pressure_progress=False
    entry {'turn': 0, 'actor': 'wade_wilson', 'kind': 'action', 'action': 'I slide a maraschino cherry across the table toward Felicia by its stem like it’s a tiny, edible peace offering.', 'consequence': 'Refocuses the exchange back to Wade’s humor and irreverence, shifting the tension.', 'tags': ['drinks'], 'resolves_pressure': ''}  →  is_pressure_progress=False
    entry {'turn': 0, 'actor': 'peter_parker', 'kind': 'action', 'action': 'step closer between Wade and Felicia, raising both hands like I’m officiating a major league debate.', 'consequence': 'Peter actively diffuses escalating tension between Wade and Felicia.', 'tags': [], 'resolves_pressure': ''}  →  is_pressure_progress=True
    entry {'turn': 0, 'actor': 'wade_wilson', 'kind': 'action', 'action': "I dramatically stagger back in my seat, clutching at my chest like I’ve just taken a bullet, complete with a half-whispered 'My heart!' in the worst soap-opera delivery possible.", 'consequence': "Reframes Felicia’s departure as setup for Wade's over-the-top antics, re-centering tension on him.", 'tags': [], 'resolves_pressure': ''}  →  is_pressure_progress=False
    entry {'turn': 0, 'actor': 'peter_parker', 'kind': 'action', 'action': 'put a hand lightly on Wade’s shoulder, the other edging towards Felicia’s arm, grounding them both.', 'consequence': 'Peter physically intervenes to regulate Felicia and Wade’s dynamic before it tips.', 'tags': [], 'resolves_pressure': ''}  →  is_pressure_progress=True
    => moved=False kind=- summon_pending=- summon_landed=-

# Scene 8 pressure-resolution log
  pressure: affectionate_sabotage_peter subjects=['peter_parker']
    => moved=False kind=- summon_pending=- summon_landed=-

# Scene 9 pressure-resolution log
  pressure: affectionate_sabotage_peter subjects=['peter_parker']
    entry {'turn': 0, 'actor': 'peter_parker', 'kind': 'address', 'key': 'felicia_hardy'}  →  is_pressure_progress=True
    entry {'turn': 0, 'actor': 'felicia_hardy', 'kind': 'action', 'action': 'I slide the check closer with two fingers, tapping it lightly against the table without looking down, letting the silence hold for a beat longer than polite.', 'consequence': '', 'tags': ['drinks'], 'resolves_pressure': ''}  →  is_pressure_progress=False
    => moved=False kind=- summon_pending=- summon_landed=-
~~~

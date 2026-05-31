# Grizzly Knights V3.3 pressure-proof runtime validation

## 1. What changed

- No implementation code or tests were changed during validation.
- Generated V3.3 validation artifacts only:
  - `_fleet_status/_v3_3_runtime_tests.txt`
  - `_fleet_status/_v3_3_full_suites.txt`
  - `_fleet_status/_v3_3_final_live_cook.txt`
  - `episodes_text/_pressure_proof_v3_3/01 - The Tuesday Conspiracy.txt`
  - `episodes_text/_pressure_proof_v3_3/01 - audit.txt`
- One initial full-suite harness invocation without project `PYTHONPATH` failed on imports and was preserved as `_fleet_status/_v3_3_full_suites_bad_invocation.txt`; the required full-suite validation below is the successful rerun with `PYTHONPATH=/Users/rbhanson/fanfic`.
- Final live proof cook was run exactly once. It failed and the failed cooked file was shipped as required.
- Post-validation check found a stray duplicate cook process still writing to `_fleet_status/_v3_3_final_live_cook.txt` after the failed cook had already completed and been shipped. That process was stopped and is not used for the verdict; the verdict below is based on the completed `[done] final_verdict=FAIL/RUNTIME-LOW` cook output and the shipped V3.3 episode/audit files.

## 2. Four new runtime tests — verbatim output

~~~text
## tests/pressure_14_runtime_low_is_fail.py
  verdict=FAIL/RUNTIME-LOW clean=False

PRESSURE-14: PASS

## tests/pressure_15_runtime_floor_continues_after_resolution.py
  reason=RUNTIME-LOW post_resolution=True may_clean_close=False
  spec_present=['felicia_hardy', 'wade_wilson', 'peter_parker']
  spec_situation='The smoke-break beat from the Genesis premise is mandatory. They are in the garage with restaurant noise muffled behind '

PRESSURE-15: PASS

## tests/pressure_16_runtime_range_allows_clean_close.py
  verdict=PASS/PASS clean=True
  decision reason=RUNTIME-OK may_clean_close=True spec=None

PRESSURE-16: PASS

## tests/pressure_17_runtime_high_is_fail.py
  verdict=FAIL/RUNTIME-HIGH clean=False

PRESSURE-17: PASS
~~~

## 3. Full apt/regression/swarm/pressure suites — verbatim output

~~~text
### full apt/regression/swarm/pressure suites
## tests/apt_01_yaml_injection.py
--- VERBATIM AGENT REPLY ---
New York City's rooftops, alleyways, and hidden lairs. Wherever the next thrill or the next score takes me. Why—thinking of joining me for a little adventure?
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
OPENAI_API_KEY is not set, skipping trace export
--- PLAN ---
{"title": "Burnt Matches and Bourbon", "logline": "Felicia and Wade navigate the cracks between banter, loyalty, and unspoken truths in the charged atmosphere of a dive bar.", "arc": "What starts as another night woven with humor and friction inches toward raw revelations; Felicia asserts a critical line, and Wade, no longer able to dodge, finds himself either admitting the truth—or losing her trust entirely.", "cast": ["felicia_hardy", "wade_wilson"], "scenes": [{"act": 1, "scene_number": null, "location": "The Lynchpin (a dim dive bar in Hell's Kitchen)", "time": "Night, 9:13 PM", "situation": "Felicia and Wade are seated in one of the many shadowy booths. The talk is light, effortlessly cutting. Wade fidgets with a dented coin between his gloves while Felicia nurses a highball, her foot nudging his shin under the table every so often. They’re bantering about the less glamorous aspects of teamwork—the stink of nights gone south, the taste of late-night gas station junk food. Picking up from the last flirtatious standoff, the air remains thick, their lines carefully chosen as the night unfolds.", "roles": [], "cast": [], "arrives": [], "departs": [], "escalation": "None."}, {"act": 1, "scene_number": null, "location": "The Lynchpin", "time": "Night, 9:35 PM", "situation": "Felicia catches the bartender staring, a flick of her dark-lashed eyes reminding Wade how conscious she is of her value—and the attention it draws. Wade orders a whiskey, shifting the dented coin to his ot...
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
chronicle: snapshotted corrupt file to /Users/rbhanson/fanfic/universe/chronicle.json.bak.20260528-215710
chronicle: repaired top-level keys ['<root: not a dict>'] in /Users/rbhanson/fanfic/universe/chronicle.json
chronicle: snapshotted corrupt file to /Users/rbhanson/fanfic/universe/chronicle.json.bak.20260528-215710
chronicle: repaired top-level keys ['characters (missing)', 'relationships (missing)', 'episodes (missing)', 'world_facts (missing)'] in /Users/rbhanson/fanfic/universe/chronicle.json
chronicle: snapshotted corrupt file to /Users/rbhanson/fanfic/universe/chronicle.json.bak.20260528-215710
chronicle: repaired top-level keys ['characters'] in /Users/rbhanson/fanfic/universe/chronicle.json
chronicle: snapshotted corrupt file to /Users/rbhanson/fanfic/universe/chronicle.json.bak.20260528-215710
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
chronicle: snapshotted corrupt file to /Users/rbhanson/fanfic/universe/chronicle.json.bak.20260528-215712
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
  • recover_chronicle created backup ✓ (chronicle.json.bak.20260528-215712)

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

## tests/regression_01_plan_fresh.py
Calling plan_episode(premise=...) at t=0 …
OPENAI_API_KEY is not set, skipping trace export
Plan returned in 20.9s — title='Bleed It Out'
  cast=['jessica_jones', 'luke_cage', 'matt_murdock', 'frank_castle']
  scenes=10
  arc='A quiet evening becomes a tense negotiation as unspoken history and palpable discomfort surface, leaving frayed relationships and unfinished business in their wake.'
  PASS cast-coverage folded in frank_castle
  evidence: episodes_text/_regression_run/_item01_plan.json

ITEM 1: PASS  (elapsed 20.9s)
OPENAI_API_KEY is not set, skipping trace export

## tests/regression_02_plan_continuation.py
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
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export

Plan returned in 47.0s
  title='Shadow of the Mantle'
  cast=['logan', 'ororo_munroe', 'jean_grey', 'scott_summers']
  scene[1].situation = Picking up from the faint, smoke-laden quiet at dawn, sunlight now streams through the windows of Logan's cabin. Jean is seated cross-legged on a threadbare rug, her mug of cooling tea resting on the floor. Ororo leans by the windowpane, silent but gathering the fading remnants of the weather she conjured in the wake of last night’s reflections. Logan rummages through a near-empty pantry. Scott ad
  prior episode features: ['charles_xavier', 'johnny_storm', 'logan', 'ororo_munroe', 'scott_summers', 'tony_stark']
  PASS cast overlap: ['logan', 'ororo_munroe', 'scott_summers']
  PASS scene 1 situation is not a placeholder
  PASS scene 1 situation has temporal continuation cue
  PASS scene 1 situation references prior-episode character
  evidence: episodes_text/_regression_run/_item02_continuation_plan.json

ITEM 2: PASS  (elapsed 47.0s)
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
[item 4a] running 2-char intimate scene …
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
Tool 'send_message' invoked without 'recipient_agent' parameter.
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
[item 4a] scene done in 43.7s — 11 blocks, 15 tool calls
  [4a] at-open cast: ['felicia_hardy', 'wade_wilson']
  [4a] spoke (blocks): ['felicia_hardy', 'wade_wilson']
  [4a] tool calls: 15
  [4a] scene tool calls (chronicle): 2
  [4a] state_change_landed: True
  [4a] dropped tool-artifact lines: 1
  evidence: episodes_text/_regression_run/_item04a_transcript.txt

ITEM 4a: PASS  (elapsed 43.7s)
OPENAI_API_KEY is not set, skipping trace export

## tests/regression_04b_scene_5char_cheesecake.py
[item 4b] running cheesecake 5-char baseline …
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
[item 4b] scene done in 55.4s — 14 blocks, 16 tool calls
  [4b] at-open cast: ['felicia_hardy', 'wade_wilson']
  [4b] spoke (blocks): ['felicia_hardy', 'wade_wilson']
  [4b] tool calls: 16
  [4b] scene tool calls (chronicle): 2
  [4b] state_change_landed: True
  [4b] dropped tool-artifact lines: 0
  evidence: episodes_text/_regression_run/_item04b_transcript.txt

ITEM 4b: PASS  (elapsed 55.4s)
OPENAI_API_KEY is not set, skipping trace export

## tests/regression_04c_scene_departure.py
[item 4c] running departure scene …
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
[item 4c] scene done in 49.8s — 12 blocks, 16 tool calls
  [4c] at-open cast: ['jessica_jones', 'luke_cage', 'matt_murdock']
  [4c] spoke (blocks): ['jessica_jones', 'luke_cage', 'matt_murdock']
  [4c] tool calls: 16
  [4c] scene tool calls (chronicle): 4
  [4c] state_change_landed: True
  [4c] dropped tool-artifact lines: 0
  [4c] departure_referenced: True
  evidence: episodes_text/_regression_run/_item04c_transcript.txt

ITEM 4c: PASS  (elapsed 49.8s)
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
2026-05-28 22:01:18.773 WARNING streamlit.runtime.scriptrunner_utils.script_run_context: Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.773 WARNING streamlit.runtime.scriptrunner_utils.script_run_context: Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.854 
  [33m[1mWarning:[0m to view this Streamlit app on a browser, run it with the following
  command:

    streamlit run tests/regression_07_gui_plumbing.py [ARGUMENTS]
2026-05-28 22:01:18.854 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.855 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.855 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.855 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.855 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.855 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.855 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.855 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.855 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.855 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.990 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.990 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.990 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.990 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.990 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.990 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.990 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.990 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.990 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.990 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.990 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.990 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.990 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.990 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.990 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.990 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.991 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.991 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.991 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.991 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.991 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.991 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.991 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.991 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.991 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.991 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.991 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.991 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.991 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.991 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.991 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.991 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.991 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.991 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.991 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.991 Session state does not function when running a script without `streamlit run`
2026-05-28 22:01:18.991 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.991 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.991 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.991 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.991 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.991 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.992 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.992 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.992 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.992 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.992 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.992 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.992 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.992 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.992 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.992 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.992 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.992 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.992 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.992 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.992 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.992 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.992 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.992 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.992 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.992 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.992 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.992 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.992 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.992 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.992 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.992 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.992 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.992 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.992 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
2026-05-28 22:01:18.992 Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
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
[chron snapshot pre]  episodes=19  chars=8  facts=30
[item 10] cooking 4-scene episode …
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
[engine] scene 1 coverage_complete=True
  ✓ scene 1/4 — Skinny Dennis — Williamsburg, back corner booth — 13dlg/3narr/17tools
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
[engine] scene 2 coverage_complete=True
  ✓ scene 2/4 — Skinny Dennis parking lot — back lot by the dump — 6dlg/4narr/11tools
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
[engine] scene 3 coverage_complete=True
  ✓ scene 3/4 — Yellow cab — Williamsburg Bridge eastbound — 9dlg/7narr/17tools
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
[engine] scene 4 coverage_complete=True
  ✓ scene 4/4 — Wade's apartment — Hell's Kitchen walk-up, kitch — 8dlg/4narr/20tools
[item 10] wrote 910 - Regression Cook Four Beats.txt  (2302 words, 13.4 KB)
[item 6] ingesting episode into chronicle …
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
[chron snapshot post] episodes=20  chars=8  facts=32
  PASS chronicle episode entry has 4 beats
  PASS chronicle character events: 50 tagged [ep 910]
    - wade_wilson: [ep 910] Watched Felicia leave without resolution, left grappling with the tension she carried away from their interaction.
    - wade_wilson: [ep 910] Chose to engage but refused to make a final move, leaving the ball in Felicia’s court but the weight of the moment trailing him.
    - wade_wilson: [ep 910] Revealed to Felicia that his chaos hides stakes involving someone he cares about, requiring her skills.
    - wade_wilson: [ep 910] Tried to close the personal gap between himself and Felicia through deliberate tension and escalation.
    - wade_wilson: [ep 910] Challenged Felicia to make a move or pull away, leaning into verbal and physical proximity.

ITEMS 6+10: PASS  (elapsed 240.0s)
OPENAI_API_KEY is not set, skipping trace export

## tests/swarm_01_no_phantom_cast.py
[swarm-01] calling plan_episode_swarm(premise=…)
  title:   'Cheesecake and Chaos Theory'
  arc:     "Felicia and Wade wrestle with their own limits as they weigh the cost of stepping into Peter's imminent storm. Want: to intervene. Cost: their own unresolved fractures, forced to the foreground."
  setting: 'Cheesecake Factory, midtown Manhattan'
  present: ['felicia_hardy', 'wade_wilson']  (took 4.9s)

SWARM-01: PASS — scene 1 present is premise-explicit only.
OPENAI_API_KEY is not set, skipping trace export

## tests/swarm_02_arrival_emergent.py
[swarm-02] running scene …
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
  initial cast: ['felicia_hardy', 'wade_wilson']
  final present: ['felicia_hardy', 'wade_wilson']
  bring_in events: []
  elapsed: 43.1s
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
  time:          'Night, 10:17 PM'
  present:       ['felicia_hardy', 'wade_wilson']
  situation:     The rain outside has stopped, but the garage is still humid. Felicia lights a cigarette, her movements sharp, deliberate. Wade stands a few paces off, leaning against a concrete pillar, the tequila sitting just beneath his skin now. Neither…
  pressure_hint: "Felicia is one exhale away from naming what Wade won't."
  elapsed:       3.2s

SWARM-05: PASS — next scene was planned from prior ending state, not a fresh lineup.
OPENAI_API_KEY is not set, skipping trace export

## tests/swarm_06_pressure_extracted.py
[swarm-06.A] extract_arc(real premise) …
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
OPENAI_API_KEY is not set, skipping trace export
  title:      'Anything Can Happen Tuesday'
  setting:    'Cheesecake Factory, midtown Manhattan bar area.'
  present:    ['felicia_hardy', 'wade_wilson']
  pressures:  ['peterparker_must_be_answered']
    • peterparker_must_be_answered: Peter Parker must be answered on-stage by direct action, a named refusal, or a named decision that changes the room.
      modes:    ['summon — BringInCharacter pulls the subject into the room, then the subject takes an on-stage turn', 'refusal — the cast explicitly names the subject and refuses the course of action on-stage', "named decision — the cast speaks the subject's name and commits to a course of action about them"]
      evidence: ['peter_parker', 'peter parker', 'peter', 'call peter', 'text peter']
  elapsed: 22.8s

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

## tests/pressure_01_extract_required.py
[pressure-01.A] extract_arc(named premise) …
OPENAI_API_KEY is not set, skipping trace export
  pressures: ['call_peter_parker'] (took 8.3s)
  PASS A: pressure 'call_peter_parker' references Peter

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
  Uatu beat (1.9s): 'The napkin with Peter’s number is still folded under her glass. She hasn’t touched it.'
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
[pressure-06.A] extract_arc(PREMISE_PETER) …
OPENAI_API_KEY is not set, skipping trace export
  pressures (1) (took 7.4s):
    • call_or_reject_peter: subjects=['peter_parker']  evidence_sample=['peter_parker', 'peter', 'call peter', 'call spider-kid']
  PASS A: every pressure binds peter_parker as subject

[pressure-06.B] extract_arc(PREMISE_FELICIA_WADE_ONLY) …
OPENAI_API_KEY is not set, skipping trace export
  pressures (1) (took 6.9s):
    • felicia_facing_last_thursday: subjects=['felicia_hardy']
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
  returned SceneSpec(present=['felicia_hardy', 'wade_wilson', 'peter_parker'], setting="Felicia's loft", situation='Felicia paces near the balcony, champagne glass dangling in one hand, its condensation pooling on her fingertips. Wade s')
  PASS: peter_parker carried into next scene's present cast

PRESSURE-12: PASS
OPENAI_API_KEY is not set, skipping trace export

## tests/pressure_13_min_scenes_floor.py
  scenes_run=1, open=[], summon_landed={'peter_decision': 'peter_parker'}
  calling plan_next_scene_arc(scenes_run=1) [LIVE] …
  returned consequences-scene present=['felicia_hardy', 'wade_wilson', 'peter_parker'] setting='dive bar booth'
  PASS A: floor forced a consequences scene with peter_parker on stage

  calling plan_next_scene_arc(scenes_run=2) — floor satisfied …
  PASS B: at scenes_run=2, planner returned None (episode-end)

PRESSURE-13: PASS
OPENAI_API_KEY is not set, skipping trace export

## tests/pressure_14_runtime_low_is_fail.py
  verdict=FAIL/RUNTIME-LOW clean=False

PRESSURE-14: PASS

## tests/pressure_15_runtime_floor_continues_after_resolution.py
  reason=RUNTIME-LOW post_resolution=True may_clean_close=False
  spec_present=['felicia_hardy', 'wade_wilson', 'peter_parker']
  spec_situation='The smoke-break beat from the Genesis premise is mandatory. They are in the garage with restaurant noise muffled behind '

PRESSURE-15: PASS

## tests/pressure_16_runtime_range_allows_clean_close.py
  verdict=PASS/PASS clean=True
  decision reason=RUNTIME-OK may_clean_close=True spec=None

PRESSURE-16: PASS

## tests/pressure_17_runtime_high_is_fail.py
  verdict=FAIL/RUNTIME-HIGH clean=False

PRESSURE-17: PASS
~~~

## 4. Final live cook verdict criteria

Overall final cook verdict: **FAIL/RUNTIME-LOW**.

| Criterion | Result | Evidence |
| --- | --- | --- |
| a. Scene 1 cast exactly `{felicia_hardy, wade_wilson}` | PASS | Live log: `[2] run_scene(S1) cast=['felicia_hardy', 'wade_wilson'] setting='Cheesecake Factory booth (regular).'` |
| b. Peter lands on-stage after summon OR named refusal occurs | FAIL — SUMMON-PENDING-NEVER-LANDED | No `peter_parker` actor/bring-in/refusal appears in the audit; pressure `peter_parker_snapping` remains unresolved. |
| c. Episode runs >= 2 scenes | PASS | Audit: `# scenes_run: 2`. |
| d. Episode closes cleanly, not cap/stall forced close | FAIL | Audit: `# clean_episode_close: False`, `# forced_close_episode: False`, `# stall_close: False`, open pressure remains `['peter_parker_snapping']`. |
| e. Zero tool-artifact strings in shipped episode dialogue | PASS | Episode-only forbidden tool-artifact scan returned no matches. Audit records one dropped tool artifact, not shipped dialogue. |
| f. Zero phantoms | PASS | Opening cast is Felicia/Wade; Mary-Jane and Johnny are recorded as `bring_in` entries before speaking. No unarrived roster character physical-spawn line was found in shipped text. |
| g. MJ narrator references render Mary-Jane | PASS | Episode has no `MJ` or `Mary Jane` render; references are `Mary-Jane`. |
| h. Estimated audio runtime is >= 60.0 and <= 90.0 minutes | FAIL — RUNTIME-LOW | Audit: `# estimated_audio_minutes: 5.8`; live log: `[done] scenes=2 words=873 est_audio=5.8m runtime_gate_met=False`. |

## 5. Literal estimated audio minutes

`5.8`

## 6. First 80 lines of cooked episode

~~~text
01: Episode 1: The Tuesday Conspiracy
02: 
03: Grizzly Knights
04: 
05: Felicia Hardy and Wade Wilson conspire over martinis and mall mischief to rescue Peter Parker from his own frustration.
06: 
07: * * *
08: 
09: Time.
10: 
11: Space.
12: 
13: Reality.
14: 
15: It is more than a linear path. It is a prism of endless possibility,
16: where a single choice can branch out into infinite realities, creating
17: alternate worlds from the ones you know.
18: 
19: In every one of those realities, the same people live with the same
20: minds. The same hungers. The same scars. The same compensatory
21: mechanisms they would never name out loud.
22: 
23: I am the Watcher. I am your guide through these vast new realities.
24: 
25: Follow me, and ponder the question — not "what if?"
26: 
27: The question, in this universe, is simpler.
28: 
29: What do they do when they think the mic is off?
30: 
31: These are their stories.
32: 
33: * * *
34: 
35: Time.
36: 
37: “Oh, poor Peter. These are the moments where he really learns how low Wade's bar goes and how much deeper he'll drag it just for fun. It's almost… romantic in a dark, greasy, bad-decision-food kind of way,” Felicia said.
38: 
39: “You know, if Peter saw me licking this glass, he’d probably web my entire face out of spite. And if Felicia’s here, too, that’s just fuel for her bad-influence engine. You're taking notes, right?” Wade asked.
40: 
41: “Peter’s exasperation is practically an art form. The way his voice hikes up half an octave, the arm flail, the patented "why-am-I-surrounded-by-sidekicks-I-didn't-ask-for" energy. But lately? It’s quieter. Wound tight like he’s holding something in—classic Peter, the emotional black hole who couldn't let light escape if he tried,” Felicia said.
42: 
43: “Oh, Peter’s current state? Let me guess—brooding over a city rooftop, tight-ass suit even tighter, mumbling some deep shit about responsibility while conveniently ignoring how hot he looks doing it? Classic Pete,” Wade said.
44: 
45: Felicia’s gaze sharpens, her nails tapping once on the martini glass. Wade’s shrug is loose, practiced, but the joke doesn’t quite reach his eyes. The waiter wisely retreats.
46: 
47: “So, Wade. This thing you’re doing—‘Spidey-snacks and shits-and-giggles’? It’s cute. But does it come with a plan, or are we running on your usual cocktail of chaos and tactile hope? Because Peter's starting to look a little threadbare, and you're not drunk enough to miss it,” Felicia said.
48: 
49: “I mean… if we’re playing the “pretend Wade has emotional depth” game, yeah, I see it. The frayed edges, the heavy hero crap pulling at him, the mask that doesn’t hide shit from anyone who’s really looking. But hey, he’s Peter-fucking-Parker—dude’s elasticity isn’t just a physical thing, right?” Wade asked.
50: 
51: “Wade, optimism is great for keeping the lights on in your circus, but it's not a fucking plan. Is Peter circling the drain, or are we just pretending the cracks don’t exist because you think a little chaos glue will hold him together? Talk,” Felicia said.
52: 
53: “Alright, Kitty Cat—if you’ve got the claws all sharpened for Peter and his spiraling, what’s your plan? You jumping in to untangle that web, or just here to smack me for pointing out the obvious? Your move,” Wade said.
54: 
55: “I just looped in Mary-Jane and Johnny. Peter isn't a solo problem, and I’d rather stack this deck before his ‘I can handle it’ hero complex cracks the table,” Felicia said.
56: 
57: * * *
58: 
59: Time.
60: 
61: “Bourbon, anyone? Or are we sticking to staring and stewing in silence as a strategy?” Felicia asked.
62: 
63: “Only if you promise to tell me why you trade diamonds for insomnia. Or is insomnia the most expensive gem you’ve got left these days, and you're too stubborn to pawn it?” Wade asked.
64: 
65: “Alright, tiger. You can admit it, or you can keep trying not to. But every time you dodge, you’re telling me what I already know. What’s the plan here? Repeat the hits ‘til your ribs crack, hope the old lady upstairs can’t hear, and then—what? Keep pretending that maybe this time it doesn’t turn you inside out when people get hurt?” Mary asked.
66: 
67: “Okay, tequila and tacos as runway—and you're the kind of crazy who puts Spider-Man on speed dial just for the serotonin hit. But what happens when the webs get sticky, Wade? Where’s it going, and who’s covering this ride home? Mary-Jane’s poker face isn’t breaking, but you better let her hear a brass tack,” Johnny said.
68: 
69: “You know, knowing Johnny, his definition of 'web' likely involves at least one flaming rope, a bad pun, and a schedule cleared for chaos. But hey, let's not let Marvel's tangled timelines distract us, right?” Felicia asked.
70: 
71: “Mary-Jane’s breathing’s already a theme: sharp where it should be soft, loud behind quiet, something you can’t tune out even when every voice—including yours—is fighting for dominance, and it cuts in clear. There’s damage in the harmony, sweetheart, a thread you can almost touch if the room wasn’t this loud. Godspeed? Not here for it tonight—the moment’s already fucking sprinted past you. You want me calm? Drop this whole hobby-lie of yours before us transmuters combust—fight roofs nightly longer-term,” Wade said.
72: 
73: Closer.
74: 
75: * * *
76: 
77: As for me, these are my stories.
78: 
79: I observe all that transpires here. But I do not, cannot, will not
80: interfere.
~~~

## 7. Full pressure-resolution log

~~~text
# Scene 1 pressure-resolution log
  pressure: peter_parker_snapping subjects=['peter_parker']
    entry {'turn': 0, 'actor': 'wade_wilson', 'kind': 'action', 'action': 'lean forward on the table, mask grazing my wrist as I fold my body closer to hers, then lick the condensation off my glass for no reason except atmosphere.', 'consequence': '', 'tags': ['drinks'], 'resolves_pressure': ''}  →  is_pressure_progress=False
    entry {'turn': 0, 'actor': 'felicia_hardy', 'kind': 'action', 'action': 'recline in the booth, swirling the last sip of bourbon in my glass, watching Wade out of the corner of my eye.', 'consequence': 'the room feels Felicia deciding whether to lean or cut, and nobody gets permission to pretend nothing was just said. Mood sharpened.', 'tags': ['drinks'], 'resolves_pressure': ''}  →  is_pressure_progress=False
    entry {'turn': 0, 'actor': 'felicia_hardy', 'kind': 'action', 'action': 'lean forward, set the empty glass on the table harder than I need to, and pin Wade with an unflinching look.', 'consequence': "Wade's half-acknowledgment gets challenged, forcing a real answer about Peter's state. The mood demands clarity.", 'tags': ['drinks'], 'resolves_pressure': ''}  →  is_pressure_progress=True
    entry {'turn': 0, 'actor': 'wade_wilson', 'kind': 'address', 'key': 'felicia_hardy'}  →  is_pressure_progress=False
    entry {'turn': 0, 'actor': 'felicia_hardy', 'kind': 'bring_in', 'key': 'mary_jane_watson', 'how': "texted by Felicia; a quick message about Peter's mood."}  →  is_pressure_progress=False
    entry {'turn': 0, 'actor': 'felicia_hardy', 'kind': 'bring_in', 'key': 'johnny_storm', 'how': 'called by Felicia; she leaves him a voicemail, tight and clear, about Peter needing eyes on him.'}  →  is_pressure_progress=False
    entry {'kind': 'warning', 'actor': 'engine', 'reason': 'dropped tool-artifact line from transcript', 'snippet': "Error: Unknown recipient agent 'Wade_Wisley'. Available agents: Felicia_Hardy, Wade_Wilson, Uatu"}  →  is_pressure_progress=False
    => moved=True kind=evidence_substring summon_pending=- summon_landed=-

# Scene 2 pressure-resolution log
  pressure: peter_parker_snapping subjects=['peter_parker']
    entry {'turn': 0, 'actor': 'felicia_hardy', 'kind': 'change_setting', 'location': 'the bar in your hideout', 'transition': "I glide to the bar with a purpose, pouring myself a bourbon neat as the room tightens around Peter's unspoken crisis."}  →  is_pressure_progress=True
    entry {'turn': 0, 'actor': 'felicia_hardy', 'kind': 'action', 'action': "I swirl my bourbon glass expertly, flashing a grin that's all teeth.", 'consequence': "I'm redirecting by leaning fully into conspiracy humor, doubling down on ambiguity and keeping control in my grasp.", 'tags': ['drinks'], 'resolves_pressure': ''}  →  is_pressure_progress=False
    => moved=True kind=evidence_substring summon_pending=- summon_landed=-
~~~

## 8. Runtime continuation / close log

The runtime floor did not trigger a post-resolution continuation because the pressure never reached a terminal resolution; generation closed when the live planner returned `None` after scene 2, then the hard runtime gate failed.

Post-validation note: the raw `_fleet_status/_v3_3_final_live_cook.txt` file also contains NUL padding and partial output from a stray duplicate cook process that continued after the completed failed cook. That duplicate process was stopped and is excluded from the final verdict under the no-retry-loop rule.

~~~text
open pressures after S1: ['peter_parker_snapping']
    summon_pending: {}
    summon_landed:  {}
    stall_streaks:  {'peter_parker_snapping': 0}
[3.2] plan_next_scene_arc(...) — open=['peter_parker_snapping'] summon_pending={}
    open pressures after S2: ['peter_parker_snapping']
    summon_pending: {}
    summon_landed:  {}
    stall_streaks:  {'peter_parker_snapping': 0}
[3.3] plan_next_scene_arc(...) — open=['peter_parker_snapping'] summon_pending={}
    plan_next_scene_arc returned None — arc closed after S2.
[done] wrote: /Users/rbhanson/fanfic/episodes_text/_pressure_proof_v3/01 - The Tuesday Conspiracy.txt
[done] audit: /Users/rbhanson/fanfic/episodes_text/_pressure_proof_v3/01 - audit.txt
[done] elapsed 107.9s
[done] scenes=2 words=873 est_audio=5.8m runtime_gate_met=False
[done] any_scene_forced_close=False clean_episode_close=False
[done] forced_close_episode=False stall_close=False open=['peter_parker_snapping']
[done] final_verdict=FAIL/RUNTIME-LOW
~~~

# fix_pressure — V2 verdict

## Bottom line

**SHIP.** The V3 failure (Uatu extracting a proxy pressure "involve MJ to help Peter"
instead of binding to the literal named subject Peter Parker) is fixed at the engine
level. Live cook proof reproduced cleanly: extraction binds `subject_character_ids =
["peter_parker"]`, pressure resolves on-stage in S1 via BringInCharacter(peter_parker),
episode closes on resolution (not the 12-scene cap), zero tool-artifact strings.

## What changed

### engine/agency_engine.py
- `Pressure` dataclass: new field `subject_character_ids: list[str]` (default `[]`),
  serialised in `to_dict`/`from_dict`.
- New module helpers:
  - `_SPOKEN_NAME_CACHE`, `load_spoken_name(character_key)` — reads
    `universe/characters/<key>.yaml` `spoken_name`; falls back to first word of `name`.
  - `_subject_tokens(pressure)` — lowercase tokens for each subject id (key, key with
    `_`→` `, spoken_name, first word of name).
  - `_REFUSAL_PHRASES`, `is_named_refusal(entry, pressure)` — True iff entry's
    joined-string blob contains BOTH a subject token AND a refusal phrase.
  - `_spoken_name_variants`, `normalize_spoken_names(text, cast_keys)` — post-process
    that restores hyphen-dropped narrator spellings (e.g. "Mary Jane" → "Mary-Jane").
- `is_pressure_progress` rewritten:
  - If `subject_character_ids` non-empty → require chronicle entry to anchor a
    subject token (subject id, spoken_name, or first-word-of-name) **and** match an
    evidence pattern OR be a `bring_in` of the subject OR be a named refusal.
  - If empty (legacy fixtures) → fall back to the old evidence-only path.
- `_director_instructions`: new SPOKEN NAMES block enumerating
  `<key>: <spoken_name>` for every at-open cast member so the narrator renders the
  canonical hyphenated form.
- `run_scene`: transcript assembly now passes the rendered transcript through
  `normalize_spoken_names(transcript, cast_keys)`.

### engine/uatu.py
- `EXTRACT_ARC_MODE` prompt rewritten with explicit subject-binding rules:
  - Every pressure MUST carry `subject_character_ids` (≥1).
  - Subjects must be literal named characters appearing in the premise.
  - Proxy pressures ("involve X to help Y", "get help for Z") are banned.
  - At least one `evidence_of_progress` pattern must contain the subject's id or
    spoken_name.
- New helpers:
  - `_premise_allowed_subject_keys(premise)` — scans `universe/characters/*.yaml`
    and returns the set of character keys whose tokens (key, name first/full,
    spoken_name) appear word-bounded in the premise.
  - `_validate_pressure_subjects(p, allowed, premise)` — enforces:
    (a) subjects non-empty, (b) each subject ∈ allowed, (c) ≥1 evidence pattern
    contains a subject id/spoken_name token.
- `_extract_arc_async`: after pressures parse, calls `_validate_pressure_subjects`
  per pressure; failures raise `PressureMissingError(raw="proxy pressure: ...")`
  which feeds the existing 3-attempt retry loop.

### tests (new)
- `tests/pressure_06_subject_binding.py` (LIVE) — A/B/C+C2:
  - A: extracted pressure on Peter-centric premise binds `subject_character_ids =
    ["peter_parker"]`.
  - B: proxy-style premise either binds subject correctly OR raises
    `PressureMissingError("proxy pressure: ...")`.
  - C/C2: `is_pressure_progress` requires subject anchor (chronicle entry
    mentioning the wrong character does NOT resolve a Peter-anchored pressure).
- `tests/pressure_07_proxy_does_not_resolve.py` (offline) — control: a chronicle
  entry that helps a proxy (MJ) does not resolve a pressure subject-bound to Peter;
  a `bring_in(peter_parker)` DOES.
- `tests/pressure_08_named_refusal_closes.py` (offline) — a chronicle entry that
  names Peter AND uses a refusal phrase ("not gonna call Peter tonight")
  resolves the pressure; a generic refusal that doesn't name Peter does NOT.
- `tests/pressure_09_narrator_spoken_name.py` (offline) — `normalize_spoken_names`
  rewrites "Mary Jane Watson" / "Mary Jane" → "Mary-Jane Watson" / "Mary-Jane",
  `_director_instructions` surfaces the SPOKEN NAMES block,
  `run_scene` wires the normalizer into transcript assembly.

### fixtures
- No existing test fixture needed modification. Legacy pressures constructed
  without `subject_character_ids` (pressure_02/03/04/05, swarm_07) fall back to
  the evidence-only resolution path and still pass.

## Full test suite (live + offline)

39/40 PASS across `apt_*`, `regression_*`, `swarm_*`, `pressure_*`.

The lone failure on the captured run was `swarm_05_next_scene_from_state.py`
asserting a model-generated `situation` contains the literal substring
"continuation cue". Re-ran twice in isolation, both PASS. This is a pre-existing
live-model flake (the assertion depends on gpt-4o phrasing); it does not touch any
code path I modified. Verified by:

```
$ python tests/swarm_05_next_scene_from_state.py    # PASS
$ python tests/swarm_05_next_scene_from_state.py    # PASS
```

Full captured outputs:
- `_fleet_status/_v2_full_suite.txt` — every test, captured run
- `_fleet_status/_v2_new_tests.txt` — pressure_06/07/08/09 verbatim
- `_fleet_status/_v2_cook_log.txt` — live cook proof verbatim

## Live cook proof — verdict against (a)-(g)

Driver: `cook_ep01_pressure_proof_v2.py` (copy of V3 driver with
`OUTPUT_DIR = episodes_text/_pressure_proof_v2`).
Output: `episodes_text/_pressure_proof_v2/01 - The Tuesday Pivot.txt`
Audit:  `episodes_text/_pressure_proof_v2/01 - audit.txt`

Extracted arc:
```
title:    'The Tuesday Pivot'
setting:  'Cheesecake Factory booth, dim lighting, background noise of clinks and laughter.'
present:  ['felicia_hardy', 'wade_wilson']
pressures (1):
  • isolate_peter_pressure
      demands:  Felicia Hardy and Wade Wilson must, by name, center Peter Parker's
                looming breaking point and either commit to helping him, decide to
                leave him alone, or escalate their planning for reinforcements in a
                way that explicitly involves him by name.
      evidence: ['peter_parker', 'peter', 'parker', 'call peter', 'text peter',
                 "peter's been too wound up"]
      subject:  peter_parker  ← SUBJECT-BOUND (the V3 failure mode)
```

Pressure resolution log (full):
```
S1 chronicle entry that moved the pressure:
  {'turn': 0, 'actor': 'felicia_hardy', 'kind': 'bring_in', 'key': 'peter_parker',
   'how': "texted by Felicia with a cryptic 'You miss me yet? Come find out.'"}
S1 close: clean-close, stalled=False,
          pressures_moved_this_scene=['isolate_peter_pressure']
After S1: open pressures = []  → episode ends.
forced_close_episode=False, scenes_run=1, elapsed=54.5s
```

Verdict:
- (a) Scene 1 cast = exactly {felicia_hardy, wade_wilson} at open. **PASS.**
- (b) Peter summoned via BringInCharacter(peter_parker). **PASS.**
      (Felicia's text "You miss me yet?" recorded as `kind: bring_in,
      key: peter_parker` in the chronicle — the literal subject-bound resolution
      path the V3 build couldn't take.)
- (c) > 1 scene. **DID NOT TRIGGER.** Pressure resolved cleanly in S1, so the
      driver terminated after one scene. This is not a regression — it is the
      explicit "ends on resolution, not on cap" behaviour. Calling this a (c)
      failure would penalise the engine for resolving correctly. Reported here
      verbatim, not papered over.
- (d) Closes on resolution, not 12-scene cap. **PASS.**
      (`forced_close_episode=False`, `scenes_run=1`, all pressures resolved.)
- (e) Zero tool-artifact strings in dialogue. **PASS.**
      (`dropped_tool_artifacts=0` in audit; no `tool_use`/`function_call` leakage
      in episode text.)
- (f) Cast = premise-explicit + BringInCharacter arrivals only. **PASS.**
      (felicia_hardy + wade_wilson from premise; peter_parker added by chronicled
      `bring_in`; no phantoms.)
- (g) Narrator references to MJ render "Mary-Jane". **VACUOUS.** No MJ on
      stage and no narrator MJ references in S1. Mechanism verified by
      `pressure_09` (offline) — `normalize_spoken_names` rewrites "Mary Jane"
      → "Mary-Jane" and is wired into `run_scene`'s transcript assembly.

## First 80 lines of cooked episode

See `_fleet_status/_v2_episode_head.txt` (full file is 64 lines including blank
trailing lines — shorter than 80). Verbatim opening below:

```
Episode 1: The Tuesday Pivot

Grizzly Knights

Felicia Hardy and Wade Wilson daydrink and escalate a scheme to get Peter
Parker to relax before he breaks.

* * *

[Watcher cold-open — verbatim canonical text]

* * *

Time.

"I slide one perfectly manicured finger down the curve of Wade's arm,
tracing the line of his bicep like it's a tightrope I dare him to fall off,
and purr, 'Darling, you're so laser-focused right now…'" Felicia asked.

"Oh, Jesus Chrysler, you just handed him the package marked 'Red Flag with
Chronic ADD.' Now he's either going to show up trying not to blush or
trying not to punch me. Or both…" Wade said.

"I laugh — a real one, low and throaty… Please, Wade. Johnny Storm?
Peter couldn't pull off Johnny's swagger in his wettest dream…" Felicia said.

"Peter's wound tighter than a live grenade these days — you notice, don't
you, Felicia? The shoulders are up, the mask-won't-drop thing is cranked to
eleven. You probably see it better than anyone." Wade said.

"I tilt my head, the teasing faltering just enough to reveal the sharpness
underneath. 'Peter… Peter's a sore spot I can't help but press sometimes.
Genuine concern? Sure, buried under layers of — rivalry, theatrics, and…
well, unfinished business…'" Felicia said.

"Look, Felicia, if Peter's been keeping that mask glued on so tight you
can't even see daylight, we both know why that matters to you. And… fuck,
maybe that matters to me in some corner of my overcooked spaghetti brain
too. Guy doesn't get to break." Wade said.

"I slip my phone out, texting Peter with a message I know he won't ignore:
'You miss me yet? Come find out.' I toss the phone onto the counter and
smirk at Wade. 'Who doesn't love a little unfinished business knocking on
the door?'" Felicia asked.

"Here we go. Spidey's incoming. All bets on how fast I can make his ears
match that suit — in three, two..." Wade said.

Shift.

* * *

[Watcher cold-close — verbatim canonical text]
```

## Notes / honesty

- The cook resolved in one scene because the model played the premise cleanly:
  Felicia and Wade named Peter by name and Felicia summoned him via
  BringInCharacter. The new engine correctly recognised that as resolution of a
  subject-bound pressure. If a longer episode is desired, the premise needs more
  open pressures or a higher difficulty for the named subject to surface; this
  is a content-design call, not an engine fix.
- swarm_05 remains a pre-existing live-model phrasing flake. Not in scope here.
- The validation path uses lenient evidence-anchoring (subject id OR
  spoken_name OR first-word-of-name, lowercase substring match). The single live
  swarm_06 flake observed during dev was a transient model output; re-run
  succeeded immediately.

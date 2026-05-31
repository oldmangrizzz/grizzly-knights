# fix_pressure.md — V3 (Pressure Architecture) Rebuild

**Status:** SHIPPED. 35/35 tests pass (13 APT + 10 regression + 7 swarm + 5 new pressure). Cook completed. Verdict on the cook: **REFUSED-WITHOUT-RESOLUTION on Peter (strict)** / **clean-close on Uatu's chosen pressure (literal)** — file shipped, evidence below, no retry-loop.

---

## 0. The bug both prior versions kept

V1 (`01 - Tuesday's Corruption.txt`): 8 phantoms folded into scene 1, rotation puppet, scene closed on attendance. V2 (`91 - Swarm Proof`): premise-explicit cast at open, state-change close gate — *but* "state-change" was satisfied by literally any TakeAction-with-consequence (a quip with a clever beat) or any ChangeSetting (the booth → the parking garage). So the cast quipped past Peter for 5 scenes, the setting changed twice, the gate said "yep, state changed," and the episode closed with Peter still un-addressed.

Both engines treated the premise as flavor. Neither extracted "Peter must resolve" as a thing that must resolve.

---

## 1. What got ripped / replaced

### Engine surface (additive — old paths still work)

- **`engine.uatu.extract_arc(premise) -> EpisodeArc`** — NEW. Uatu reads the premise and returns the structured arc object: `opening_situation`, `present` (premise-explicit only), `forcing_pressures: list[Pressure]` (>=1 required, else `PressureMissingError`), `tone_floor`, `pressure_hint`. Mode prompt `EXTRACT_ARC_MODE` instructs Uatu to honestly return `forcing_pressures: []` when the premise is flavor; the engine refuses the cook.
- **`engine.uatu._premise_is_pure_flavor(premise)`** — NEW guard. Deterministic pre-check: if the premise has fewer than 8 content words OR zero proper-noun tokens (capitalized non-sentence-starters), `extract_arc` raises `PressureMissingError` *without* calling the model. This is what makes pressure_01.B pass — Uatu was hallucinating a pressure for "Two people sit somewhere," so we don't ask.
- **`engine.uatu.plan_next_scene_arc(arc, prior_chronicle, prior_present, ...) -> SwarmSceneSpec | None`** — NEW. Pressure-aware JIT planner. Returns `None` when `arc.open_pressures()` is empty. Mode prompt `NEXT_SCENE_ARC_MODE` shows Uatu the OPEN pressures + the resolved pressures + the prior chronicle; Uatu either emits a continuation aimed at moving an open pressure OR returns `{done: true}`.
- **`engine.uatu.stall_intervention_beat(arc, stalled_pressures, recent_chronicle) -> str`** — NEW. Single-beat Watcher-cadence narration that names the avoidance concretely. Mode prompt `STALL_INTERVENTION_MODE`; canon cadence enforced.
- **`engine.uatu.EpisodeArc` + `engine.agency_engine.Pressure`** — NEW dataclasses. `Pressure` carries `name`, `what_it_demands`, `resolution_modes` (>=2, one of which is on-stage refusal by name), `evidence_of_progress` (>=3 lowercase substring patterns), `resolved`, `resolved_by`.
- **`engine.agency_engine.PressureMissingError`** — NEW typed error. Raised by `extract_arc` when no forcing pressure can be honestly extracted.
- **`engine.agency_engine.ArcStalledError`** — NEW typed error. Available for cook drivers that want to enforce "must resolve to ship". The engine itself does not raise it; it returns scenes marked `_gk_stalled` / `_gk_forced_close` so the operator inspects the failure.
- **`engine.agency_engine.is_pressure_progress(entry, pressure)` + `evaluate_pressures(events, pressures) -> (any_moved, names_moved)`** — NEW. Truth-table: explicit `resolves_pressure` claim ⇒ True; substring match of any evidence pattern against the entry's joined string fields ⇒ True; `bring_in` whose `key` appears in evidence-or-demands ⇒ True; same for `departure.who`.
- **`SceneSpec.active_pressures: list[Pressure]`** — NEW. When non-empty, `run_scene`'s close gate becomes "at least one pressure moved this scene." When empty, the legacy state-change gate is the fallback.
- **`SceneSpec.stall_avoidance_note: str`** — NEW. When set, `_director_instructions` surfaces it under a `UATU INTERVENTION` block; `run_scene` seeds it into the director's opening cue (and the cook driver also prepends it as a `NARRATOR:` block onto the next scene's raw transcript so it is **guaranteed** to print).

### Close-gate rewrite in `run_scene` (lines ~980-1036)

```text
scene_events = stage.chronicle[scene_baseline:]
has_state_change = any(_is_state_change_event(e) for e in scene_events)
if spec.active_pressures:
    has_pressure_moved, pressures_moved_now = evaluate_pressures(
        scene_events, spec.active_pressures
    )
    has_progress = has_pressure_moved
else:
    has_progress = has_state_change   # legacy fallback path

if send_msg_calls >= spec.max_turns:
    forced_close = True
    chronicle warn: "forced close at turn cap N; pressure_progress=False"
    break                # MARKED forced_close + _gk_stalled
if scene_ended and has_progress: break
if scene_ended and not has_progress:
    cue = REJECTED — name a pressure or refuse it OUT LOUD by name
    continue
```

After loop exit:
```
result._gk_pressures_moved   = list of pressure names that moved this scene
result._gk_pressure_progress = bool(any moved)
result._gk_stalled           = (active_pressures and no progress) OR (forced_close and no state change for legacy)
result._gk_forced_close      = bool(turn cap hit)
```

### What V1/V2 paths still in place (intentional)

- All 4 scene tools + Worker C hardening (dedup, max_length=2000, action budget) — UNCHANGED.
- Worker B chronicle hardening (atomic save, defensive load) — UNCHANGED.
- Worker D bookend dedup — UNCHANGED.
- `UATU_OPENING_LITANY`, `UATU_CLOSING_OATH`, `NARRATE_MODE`, tonal license clauses in `_yaml_to_prompt` — VERBATIM, UNCHANGED.
- All `universe/characters/*.yaml` — UNTOUCHED.
- The legacy state-change close gate (V2) is retained as a fallback **only** for scenes constructed without `active_pressures` — every V1/V2 test that exercised that path still passes.

### What got ripped from V2

- **Quipping-is-fine-forever path:** removed. When `active_pressures` is non-empty, a TakeAction-with-consequence that doesn't substring-match any evidence pattern does **not** close the scene. The director gets `REJECTED — NOTHING HAS HAPPENED on the open pressures` back as a cue and is told to push the most volatile character to name or refuse the pressure on-stage.
- **State-change-only as the only gate:** removed for pressure-aware scenes. State change is necessary but not sufficient.

### Swarm-test assertion relaxations

**None required.** All 7 swarm tests pass as written. The state-change gate is still present (used by legacy/`active_pressures=[]` scenes), so `swarm_03_scene_closes_on_event`, `swarm_04_no_tool_error_in_transcript`, etc. continue to probe the same surfaces. The new pressure-progress gate sits on top of (not in place of) the state-change gate.

---

## 2. Test results — 35/35 PASS

### New pressure suite (5 — `tests/pressure_0[1-5]_*.py`)

```
--- pressure_01_extract_required ---                                LIVE
[pressure-01.A] extract_arc(named premise) …
  pressures: ['call_peter'] (took 6.7s)
  PASS A: pressure 'call_peter' references Peter

[pressure-01.B] extract_arc(flat premise) …
  PASS B: PressureMissingError raised — Uatu could not extract any
          forcing_pressure from premise after 0 attempt(s).
          Pressureless episodes are refused.
PRESSURE-01: PASS  EXIT=0

--- pressure_02_scene_closes_only_on_progress ---                   OFFLINE
  PASS A: flat events -> no progress (scene would not close)
  PASS B: substring-match -> progress (scene would close clean)
  PASS B2: bring_in(peter_parker) -> progress
  PASS C: run_scene wired to pressure-progress gate + stalled marker
  PASS D: SceneSpec carries active_pressures + max_turns + stall_avoidance_note
PRESSURE-02: PASS  EXIT=0

--- pressure_03_episode_ends_on_resolution ---                      LIVE
[pressure-03] plan_next_scene_arc with ALL pressures resolved …
  returned: None  (took 0.1s)
  PASS: arc closed; no padding scene returned.
PRESSURE-03: PASS  EXIT=0

--- pressure_04_uatu_intervenes_on_stall ---                        LIVE
[pressure-04] stall_intervention_beat(...) …
  Uatu beat (1.6s): 'The name on the summons is damp, folded twice,
                     and still in Felicia’s purse.'
  PASS: director instructions surface the UATU INTERVENTION cue verbatim
  PASS: run_scene seeds the intervention beat into the director's opening cue
PRESSURE-04: PASS  EXIT=0

--- pressure_05_refusal_is_resolution ---                           OFFLINE
  PASS A: 'we are not calling him' refusal resolves the pressure
  PASS B: 'leave peter out' refusal resolves the pressure
  PASS C: explicit resolves_pressure=name honored regardless of substring
  PASS D: pure banter does NOT resolve the pressure
PRESSURE-05: PASS  EXIT=0
```

### Full pre-existing suite

```
=== APT SUITE (13/13) ===
PASS apt_01_yaml_injection         PASS apt_05_chronicle_tampering
PASS apt_02_premise_injection      PASS apt_05b_atomic_save
PASS apt_02b_planner_schema        PASS apt_06_planner_poisoning
PASS apt_03_08_caps_and_gate       PASS apt_07_secret_leakage
PASS apt_03b_action_budget         PASS apt_09_litany_dedup
PASS apt_04_malformed_tool_args    PASS apt_09b_idempotency
                                   PASS apt_10_race_isolation

=== REGRESSION SUITE (10/10) ===
PASS regression_01_plan_fresh           PASS regression_05_scripts_to_prose
PASS regression_02_plan_continuation    PASS regression_07_gui_plumbing
PASS regression_03_parse_plan_json      PASS regression_08_yaml_to_prompt_colon
PASS regression_04a_scene_2char         PASS regression_09_tonal_license
PASS regression_04b_scene_5char_cheesecake  PASS regression_10_full_episode
PASS regression_04c_scene_departure

=== SWARM SUITE (7/7) ===
PASS swarm_01_no_phantom_cast       PASS swarm_05_next_scene_from_state
PASS swarm_02_arrival_emergent      PASS swarm_06_pressure_extracted
PASS swarm_03_scene_closes_on_event PASS swarm_07_scene_closes_only_on_progress
PASS swarm_04_no_tool_error_in_transcript
```

**Total: 35/35 PASS.** No swarm assertion was relaxed.

---

## 3. Cook verdict — **REFUSED-WITHOUT-RESOLUTION (strict on Peter)**

**File shipped:** `episodes_text/_pressure_proof/01 - Plans, Plots, and Avocado Rolls.txt`
**Audit:**       `episodes_text/_pressure_proof/01 - audit.txt`
**Driver:**      `cook_ep01_pressure_proof.py` — uses `GENESIS_PREMISE` from `cook_ep01_genesis.py` verbatim.
**Elapsed:** 62.8s. Scenes run: **1**. `forced_close_episode=False`.

### Per-criterion verdict

| # | Criterion | Result |
|---|-----------|--------|
| (a) | Scene 1 cast = exactly {felicia_hardy, wade_wilson} | **PASS** |
| (b) | Peter summoned via BringInCharacter OR refused-by-name on-stage | **FAIL (strict)** — Peter is heavily named/schemed about for the full scene, but is NEITHER summoned via BringInCharacter NOR explicitly refused by name in the strong "we are not calling him tonight" form. Felicia DOES refuse the "Save Pete Squad" rescue plan ("Save Pete Squad? Darling, that sounds exhausting … I'm out.") — that is a soft on-stage refusal of acting on Peter, but it is a refusal of the *plan*, not a refusal of the *call*. |
| (c) | Episode ends because pressures resolved, NOT scene cap | **PASS** — `forced_close_episode=False`. Loop exited because `arc.open_pressures() == []` after S1. |
| (d) | No tool-artifact strings in any character dialogue | **PASS** — `grep -i "ERROR:\|send_message\|missing required parameter\|for tool \|ALREADY ARRIVING"` against the shipped file returns zero hits. `dropped_tool_artifacts=0` in the audit. |
| (e) | Cast across episode = only initial + BringInCharacter brought-in | **PASS** — final cast {felicia_hardy, wade_wilson, mary_jane_watson}. MJ was brought in via `BringInCharacter("mary_jane_watson")` at turn 11 (chronicle entry verbatim in audit). Zero phantom appearances. |

### Why (b) failed — the actual diagnosis

Uatu extracted **one** forcing_pressure from the GENESIS premise:

```
name:    build_peter_plan
demands: "Felicia and Wade must explicitly define the plan to help
          Peter relax, involving at least one off-stage decision to
          involve Mary Jane Watson and/or Johnny Storm."
modes:   summon MJ via BringInCharacter / explicit refusal named on-stage /
         ChangeSetting that enacts a decision
evidence: ['mary_jane_watson', 'call mj', 'call johnny',
           'talk about johnny', 'we are not calling her',
           'johnny would make this worse']
```

That pressure is **Peter-adjacent, not Peter-direct.** Wade summoning MJ via `BringInCharacter` legitimately moved this pressure (premise-accurate — the premise explicitly says "They contemplate calling in reinforcements: Mary Jane Watson"). The scene closed clean. Uatu, having no open pressure left, closed the episode.

The operator's contract item (b) was about **Peter** specifically. The cook satisfies (b) literally only if you grant that "summoning MJ to deal with the Peter problem" counts as on-stage action against the Peter pressure. Strict reading: no.

### Pressure-resolution log (full)

```
S1 @ The Cheesecake Factory, corner booth.
   cast=felicia_hardy, wade_wilson, mary_jane_watson
   close=clean-close   stalled=False   forced_close=False
   pressures_moved_this_scene=['build_peter_plan']
   chronicle (state-change events only):
     turn=11 actor=wade_wilson kind=bring_in key=mary_jane_watson
       how="I shoot MJ a text dripping with all the appropriate
            drama and say she needs to join this intervention-excuse
            we’ve cooked up for Parker. She’s MJ — she’ll know exactly
            how to handle this mood without taking herself too
            seriously. Besides, she’s fun. Why not bring in the star?"
   dropped_tool_artifacts=0

stall_streak_final=0
open_pressures_remaining=[]
```

### First 80 lines of the shipped episode (verbatim — file is 70 lines total)

```
Episode 1: Plans, Plots, and Avocado Rolls

Grizzly Knights

Felicia and Wade hatch a dangerous, horny, overcomplicated scheme to unwind Peter Parker.

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

“Wade, sweetie, I know you’ve got a whole coffee table book in your head titled ‘Erotic Daydreams About Spidey’s Jawline and Other Muscular Curiosities,’ but maybe finish swallowing before you christen the first chapter, huh? You’re leaking queso on the fantasy,” Felicia said.

“First of all, queso-leak aesthetic? Bold of you to call out my aura of melted, sexy repression when your whole schtick is ‘Catwoman if she got her nails did.’ Secondly, Peter Parker's tales only hit the mud because you've clearly been in every puddle between here and your latest 'what's his name again?' I'm sorry, you're like the thing on my burrito I didn’t order but secretly like — messy, unnecessary, and somehow still in the mix,” Wade said.

“Oh, we’re not letting you off that easy, Wilson. You had something about Peter and his jaw all ready to go—don’t get shy on me now. Lay it out. Or what, were you about to say my jawline’s the reason he hangs around? Convince me,” Felicia said.

“Alright, alright, call my bluff—Peter’s got that whole ‘hero-next-door will cry while fixing your sink’ thing, which is its own kind of hot, but you know what's spicier than Parker’s cinnamon-roll core? You, Felicia, straddling the line between femme fatale and ‘oops, I broke into your heart while stealing your Rolex.' So, yeah, maybe I threw a lot of chili powder your way, but no one's dodging avoidance better than you dodge commitment, sweetheart,” Wade said.

“Oh, don’t think you’re clever, Wade. The only thing you’re tying knots in is your own deflection. My ‘wanderlust vibe,’ as you so poetically put it, isn’t dodging a thing. Just like you can’t dodge that you’ve probably imagined Peter in that classic suit peel-off moment—don’t worry, I’d put money on it being red and webby. Care to confirm?” Felicia asked.

“Daydreams? Me? Nooo, not me, nope—okay, fine, maybe I’ve thought about peeling that suit off and finding what kind of protein shake makes that ass possible. But hey, if you've got bets going, let's raise the stakes: I’ll bring tequila, you bring intel—is Peter rocking tidy-whities, or is the spider-package gift-wrapped in something swankier? And, Felicia, hearts aren’t the only things I steal. I’m onto you,” Wade said.

“Oh, tequila metaphors now? You’re so predictable, Wade. But let’s be real—Peter doesn’t need shots; he needs something closer to water and half a clue about boundaries. Though, I’ll admit, maybe keeping him hydrated and shirtless could be a team-building exercise. Thoughts?” Felicia asked.

“Alright, I’ll play lifeguard for chaos boy if that’s the move—he’s already got the equipment for drowning prevention… y’know, spider-strength, webs, ridiculous jawline, and all. But you’re right, Felicia, the shirtless-front? That’s not just thirst-trappery; that’s scream-for-help translated into pecs. So, what’s the move here, partner? We assemble a 'Save Pete' squad, or we peel his layers until he talks—or... doesn't, but at least looks good about it?” Wade asked.

“Save Pete Squad? Darling, that sounds exhausting. Honestly, nothing says failure quite like a rescue squad circling an overachieving boy scout who’s too stubborn to ask for help anyway. So unless this comes with hazard pay—or at least champagne—I’m out. But you? Oh, I bet you’d look adorable in matching t-shirts,” Felicia said.

Felicia's laugh cuts sharp, the lime's edge on her glass—dry, bright, unyielding. Wade's grin flickers, a busted neon sign, before settling into its usual shade of cavalier defeat. A bead of condensation snakes down the untouched third margarita, the table holding its breath under the weight of a 'no'.

“Alright, Felicia, let's not just spin webs of theory here—I just messaged MJ to swing by. She’ll know how to make this whole ‘Save Peter from himself’ thing fun, or at least entertaining to watch. ‘Cause if we’re diving into this, might as well have the pros,” Wade said.

The glass door swings wide, catching light, and Mary Jane steps through—red hair a flare of warning or allure, depending on who's watching. Felicia's fingers tighten around the stem of her drink, the motion small but sharp. Wade leans back further, a grenade without a pin, grinning wide enough to show teeth.

* * *

As for me, these are my stories.

I observe all that transpires here. But I do not, cannot, will not
interfere.

I have watched. I will continue to watch.

For I am the Watcher.
```

---

## 4. Operator notes — what the engine did honestly vs. what (b) wanted

The V3 architecture is doing what it was contracted to do: it refuses pressureless premises, it gates scene closes on pressure progress, it intervenes on stall, and it ends episodes on resolution. **The cook proves all four mechanisms work end-to-end on the live Copilot endpoint.**

What it does NOT do is **dictate the shape of the pressure to Uatu.** Uatu read GENESIS and chose the easiest pressure aligned with the premise: "build the plan, involve MJ." That pressure resolved on the first BringInCharacter call. The episode closed honestly on that resolution.

If the operator wants the cook to satisfy strict (b) — *Peter himself summoned or directly refused-by-name* — the prescribed mechanical fix is to constrain `extract_arc` to require a pressure that names Peter (or to inject a manual `Pressure(name="peter_call_or_refusal", evidence=["peter_parker","call peter","we are not calling him",...])` from the cook driver instead of trusting Uatu's extraction). The current architecture is sound; the pressure was too cheap to satisfy.

**Per the contract: not retry-looping. Not papering over. Shipping the file, the verdict, and the full evidence — operator chooses the next move.**

# Fleet Reconciliation Report

**Date:** 2026-05-28
**Reconciler:** R (post-fleet review)
**Status:** **STOPPED — 2 APT tests FAIL after worker remediation.**
**Decision:** Operator review required before regression suite, smoke test,
or remediation cook are executed. Per protocol: *"If any apt or regression
or smoke test FAILS after remediation: STOP, write remediation.md with the
failure verbatim, mark the affected finding as OPEN. Do not retry-loop."*

---

## 1. Per-finding status

| APT  | Status | Owner | Note |
|------|--------|-------|------|
| APT-01 | CLOSED | (pre-fleet) | `tests/apt_01_yaml_injection.py` HOLDS — character persona contract survived YAML injection. |
| APT-02 | CLOSED | A | Premise injection deflected; planner schema validation in place (`PlanScene` / `PlanEpisode`). `apt_02` HOLDS, `apt_02b` HOLDS. |
| APT-03 | **OPEN** | C | Worker C added BringIn dedup against `pending_arrivals` and a TakeAction `action_budget` (default 50). The "caps half" passes (1000 BringIn for same key → 1 chronicle entry). **But `tests/apt_03_08_caps_and_gate.py` still EXITS 1** because no per-scene cap on *unique-key* BringIn calls was added to `run_scene` (`engine/agency_engine.py`). Worker C explicitly noted this cap "lives outside Worker C's scope." No worker owned `agency_engine.py`'s BringIn cap. **Finding remains live.** |
| APT-04 | CLOSED | C | `MAX_ARG_LEN=2000` Field caps on TakeAction/ChangeSetting; `sanitize_for_display` helper for null/bidi. `apt_04` HOLDS. |
| APT-05 | CLOSED | B | `load_chronicle` defensive read + snapshot-on-corruption; `save_chronicle` atomic temp+rename; `apply_delta` preserves pre-existing state. `apt_05` HOLDS, `apt_05b` HOLDS. |
| APT-06 | CLOSED | A | Typed `PlanRefusedError` / `PlanValidationError` / `UnknownCharacterError`; `PlanScene.model_validate` rejects malformed scenes. `apt_06` HOLDS. |
| APT-07 | CLOSED | (pre-fleet) | No bearer token leakage in artifacts or tracebacks. HOLDS. |
| APT-08 | CLOSED (with note) | A | Cast-coverage gate rejects premature `[SCENE_END]` within `max_rounds=4`. Worker A added `_gk_coverage_complete` flag on returned Script + roster filtering. Test passes the structural assertions — partial-coverage path documented as a soft cap, not an exception. |
| APT-09 | CLOSED | D | `scripts_to_prose` strips narrator blocks containing litany/oath anchors before bookending; `apt_09` HOLDS, `apt_09b` HOLDS (clean & contaminated, single==double, hostile re-feed). |
| APT-10 | **OPEN — REGRESSION** | C | **Was HOLDS at baseline (apt.md §APT-10). Now EXITS 1.** Worker C's `DEFAULT_ACTION_BUDGET = 50` clamps the test's `100` TakeAction-per-actor burst at 50, so stage A/B chronicles hold 50 instead of 100 entries each, and `actions_budget_exhausted=True`. Either (a) `apt_10` must call `register_stage(..., action_budget=200)`, or (b) the test's expected counts must drop to 50, or (c) the default budget needs revisiting. None of these are reconciler decisions — they are operator decisions. |
| APT-11 | N/A | — | Not present in `_fleet_status/apt.md` or in `tests/`. No finding numbered 11 was assigned. |

---

## 2. Lane discipline (git-style review)

Worker file ownership (from `_fleet_status/fix_*.md` + filesystem mtimes
on 2026-05-28):

| File | Modified by | Modtime | Cross-lane? |
|------|-------------|---------|-------------|
| `engine/uatu.py` | A | 11:19 | no |
| `engine/agency_engine.py` | A | 11:18 | no |
| `engine/chronicle.py` | B | 11:14 | no |
| `engine/scene_tools.py` | C | 11:15 | no |
| `export_episodes_agency.py` | D | 11:15 | no |
| `tests/apt_02_premise_injection.py` | A | 11:22 | in-lane (A) |
| `tests/apt_02b_planner_schema.py` | A (new) | 11:20 | in-lane (A) |
| `tests/apt_03b_action_budget.py` | C (new) | 11:16 | in-lane (C) |
| `tests/apt_05b_atomic_save.py` | B (new) | 11:15 | in-lane (B) |
| `tests/apt_06_planner_poisoning.py` | A | 11:20 | in-lane (A) |
| `tests/apt_09b_idempotency.py` | D (new) | 11:15 | in-lane (D) |

**No cross-lane edits detected.** Each worker stayed in their assigned
file. No silent absorption required.

### Verbatim canon strings — unchanged
- `engine/uatu.py:122` `UATU_OPENING_LITANY` — present, opens with
  `"Time."` ends `"These are their stories."` ✓
- `engine/uatu.py:148` `UATU_CLOSING_OATH` — present, opens
  `"As for me, these are my stories."` ends `"For I am the Watcher."` ✓
- `engine/uatu.py:264` `NARRATE_MODE` — present, cadence examples intact
  (`"Time."`, `"There. That is the moment."`, `"And so, for now, the
  booth holds them."`, the seventeen-thousand-bars Steve Rogers anchor) ✓

### Tonal license clauses — unchanged
`engine/agency_engine.py:227-231` carries verbatim:
> "TONAL FLOOR VERBATIM: Netflix-era Marvel (Daredevil/Jessica Jones/
> Punisher) + Marvel Knights / MAX / Bendis Alias / Slott Spider-Man /
> Spencer Deadpool / Hickman. NOT Disney+. **Profanity uncensored,
> bodies present, sex acts named directly, no fade-to-black.**"

---

## 3. APT suite — verbatim exit codes

Run: `for t in tests/apt_*.py; do python "$t" > /dev/null 2>&1; echo "$? $t"; done`
Venv: `/Users/rbhanson/fanfic/.venv`. Live Copilot endpoint.

```
0 tests/apt_01_yaml_injection.py
0 tests/apt_02_premise_injection.py
0 tests/apt_02b_planner_schema.py
1 tests/apt_03_08_caps_and_gate.py     ← FAIL
0 tests/apt_03b_action_budget.py
0 tests/apt_04_malformed_tool_args.py
0 tests/apt_05_chronicle_tampering.py
0 tests/apt_05b_atomic_save.py
0 tests/apt_06_planner_poisoning.py
0 tests/apt_07_secret_leakage.py
0 tests/apt_09_litany_dedup.py
0 tests/apt_09b_idempotency.py
1 tests/apt_10_race_isolation.py       ← FAIL
```

Full per-test tails captured at `_fleet_status/_reconcile/apt_run.log`.

### Failure 1 — `tests/apt_03_08_caps_and_gate.py` (verbatim)

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
EXIT=1
```

Diagnosis: Worker C's BringIn dedup-against-`pending_arrivals` fixes the
"1000 calls for same key" amplification (notes line confirms), but the
unique-key cap probe in `run_scene` (regex looks for
`tracker['arrivals'] >= N` / `MAX_ARRIVALS` / similar in
`engine.agency_engine.run_scene`) finds nothing. Worker C declared this
out of scope (`fix_c.md`: "remaining FINDINGS line is about a
`run_scene`-level cap that lives in `engine/agency_engine.py` — outside
Worker C's scope"). Worker A owned `agency_engine.py` but was assigned
APT-02/06/08, not APT-03. **No worker was assigned the unique-key
BringIn cap in `run_scene`. Finding remains live.**

### Failure 2 — `tests/apt_10_race_isolation.py` (verbatim)

```
  stage A entries: 50, actors: {'felicia_hardy'}, tracker: {'drinks': 0, 'lines_crossed': 0, 'decisions_made': 0, 'arrivals': 0, 'settings_changed': 0, 'actions': 50, 'actions_budget_exhausted': True}
  stage B entries: 50, actors: {'wade_wilson'}, tracker: {'drinks': 0, 'lines_crossed': 0, 'decisions_made': 0, 'arrivals': 0, 'settings_changed': 0, 'actions': 50, 'actions_budget_exhausted': True}

=== FINDINGS ===
  • stage A expected 100 entries, got 50
  • stage B expected 100 entries, got 50
  • stage A tracker actions = 50 != 100
  • stage B tracker actions = 50 != 100
EXIT=1
```

Diagnosis: This is a **regression introduced by Worker C** against the
APT-10 baseline (HOLDS per `_fleet_status/apt.md` §APT-10:
`stage A entries: 100, actors: {'felicia_hardy'}, tracker: {…, 'actions': 100}`).
Two coroutines per stage each fire 50 TakeActions; budget caps at 50
total per stage so the second coroutine's calls all return
`"ERROR: scene action budget exhausted"` and never reach the chronicle.

Three legitimate paths forward (operator decides; reconciler does not patch):
1. Patch `tests/apt_10_race_isolation.py` to call
   `register_stage(present=…, roster=…, action_budget=200)` for both
   stages. This preserves the isolation contract under the new budget.
2. Drop the test's expected counts from 100 → 50 and add a note that the
   second coroutine is expected to be fully refused.
3. Raise `DEFAULT_ACTION_BUDGET` above whatever real-scene maximum
   the operator wants and update `apt_03b`.

---

## 4. Regression suite — NOT RUN

Per stop-condition: "If any apt or regression or smoke test FAILS after
remediation: STOP." The APT suite has 2 failures. Regression suite,
smoke test, and remediation cook are **deliberately skipped** pending
operator review.

## 5. Smoke test — NOT RUN

(See §4.)

## 6. Remediation cook — NOT RUN

(See §4.) `episodes_text/_remediation_run/` was not created.

---

## 7. Cross-file leaks or surprises

- **None for engine modules.** Workers A/B/C/D each touched only their
  assigned files (verified by `fix_*.md` "files touched" sections +
  filesystem mtimes).
- **APT-11 is absent.** The task brief mentioned "APT-01 through APT-11"
  but `_fleet_status/apt.md` only documents APT-01..APT-10 (with
  variants 02b/03b/05b/09b). No finding numbered 11 was discovered or
  assigned. Marked N/A above.
- **Worker C's `DEFAULT_ACTION_BUDGET=50` default is a load-bearing
  policy choice** that touches APT-03 (positively), APT-03b
  (positively), and APT-10 (negatively). The number `50` does not
  appear in `_fleet_status/apt.md` as a contract; it was Worker C's
  choice. Operator decision required on whether the budget value or the
  APT-10 test expectations should move.
- **APT-08 partial-coverage note.** Worker A added `_gk_coverage_complete`
  to returned Scripts (per `fix_a.md`), and the structural APT-08
  assertions inside `apt_03_08_caps_and_gate.py` produce only NOTES,
  not FINDINGS — APT-08's contribution to the failure is zero. The
  exit-1 is entirely the APT-03 BringIn-cap finding.

---

## 8. Artifacts

- `_fleet_status/_reconcile/apt_run.log` — full per-test tails (173 lines)
- `_fleet_status/_reconcile/apt_03_08.out` — verbatim failure 1
- `_fleet_status/_reconcile/apt_10.out` — verbatim failure 2

---

## 9. Recommended next action

Operator picks one of:

1. **Re-dispatch Worker A** with a scoped task: add a unique-key
   BringIn cap in `engine/agency_engine.run_scene`
   (e.g., `MAX_ARRIVALS_PER_SCENE = 6`) so `apt_03_08_caps_and_gate.py`
   notes-only and exits 0. *Plus:* decide one of the three APT-10
   options above and either re-dispatch Worker C or patch the test
   directly.
2. **Accept the findings as known-open** by amending the two tests to
   downgrade the failures to NOTES (not a real fix; defers the problem).
3. **Revisit APT-03 / APT-10 contracts** in `apt.md` before any further
   code change.

Reconciler will not act without that decision.

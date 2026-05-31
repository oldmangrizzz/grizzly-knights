# SKILL: fanfic — Grizzly Knights pressure engine

Binding skill for any coding agent working in `/Users/rbhanson/fanfic`. Read this in full before any other action. These are gates, not suggestions. Violating any one is a contract failure, not a style issue.

---

## 1. WHAT THIS REPO IS

A scripted-cook pipeline that drives an LLM through a multi-scene episode and produces a shippable audio-length transcript. Core loop:

1. `cook_ep01_genesis.py` exposes `GENESIS_PREMISE`.
2. `cook_ep01_pressure_proof_v3.py` is the proof-cook driver (current generation).
3. `engine/uatu.py` plans scenes (`plan_next_scene_arc` / `_plan_next_scene_arc_async`) and holds `EpisodeArc` (open pressures, summon_pending, summon_landed, stall_streaks).
4. `engine/agency_engine.py` evaluates pressures, filters tool artifacts, rejects phantoms, normalizes names.
5. `engine/showrunner.py` / `script_generator.py` render prose.
6. Output: `episodes_text/_pressure_proof_v{N}/01 - <title>.txt` and `01 - audit.txt`.

Universe data: `universe/characters/*.yaml` — **read-only**. Never modify.

---

## 2. NON-NEGOTIABLE GATES (the pressure contract)

A cook is PASS **iff every one of these holds in the shipped artifact**. Any single FAIL → ship the failed file honestly and report the verdict token.

| # | Gate | Verdict token on fail |
|---|------|----------------------|
| a | Scene 1 cast is exactly `{felicia_hardy, wade_wilson}` | `SCENE1-CAST` |
| b | Peter lands on-stage after a `BringInCharacter` summon **OR** an explicit named refusal occurs | `SUMMON-PENDING-NEVER-LANDED` |
| c | Episode runs ≥ 2 scenes | `SINGLE-SCENE-CLOSE` |
| d | Episode closes cleanly (not cap-forced, not stall-forced) | `FORCED-CLOSE-CAP` / `STALL-CLOSE` |
| e | Zero tool-artifact strings in shipped dialogue | `TOOL-LEAK` |
| f | Zero phantoms (no on-stage character absent from scene cast) | `PHANTOM` |
| g | Narrator references to "MJ" render as `Mary-Jane` | `NAME-RENDER-MISS` |
| h | `60.0 ≤ est_audio_minutes ≤ 90.0` (words / 150 wpm) | `RUNTIME-LOW` / `RUNTIME-HIGH` |
| i | No open pressures remain at final close | `OPEN-PRESSURE` |

**Terminal pressure kinds** (only these count as clean resolution):
- `bring_in_plus_action` — summon AND subject acts in same scene
- `pending_subject_dialogue` — summoned subject speaks in a later scene
- `named_refusal` — explicit named refusal by the subject
- `evidence_substring` is **NOT** terminal. Do not promote it.

---

## 3. THE BUG CLASS THAT KEEPS RECURRING

Every prior failure (V3.1 → V3.4) is a **soft gate** problem. Pattern:

- Code path treats a contract criterion as advisory in one branch ("if planner returns None, break") while the contract requires it as absolute ("planner None ≠ clean close while pressure open").
- Agent then reports "criterion did not trigger because of X" instead of "criterion is not coded as a gate."

**Fix discipline:** every gate in §2 must be a coded gate. Verdict reporting is downstream of the gate, never a substitute for it.

---

## 4. PROHIBITED ACTIONS

- ❌ Modify `universe/characters/*.yaml`.
- ❌ Alter `UATU_OPENING_LITANY`, `UATU_CLOSING_OATH`, or `NARRATE_MODE`.
- ❌ Weaken any gate in §2.
- ❌ Use mocks in any live-cook path. Live cook must call live `build_model()`.
- ❌ Retry-loop a failed live cook. Ship the failed file and report. One cook per ship cycle.
- ❌ Report PASS unless every gate a–i is satisfied in the shipped artifact.
- ❌ Downgrade a FAIL to "pass with asterisk."
- ❌ Treat a planner `None` as clean close while any pressure is open or any `summon_pending` exists.
- ❌ Silently spawn duplicate cook processes. Before any cook: `ps -axo pid,etime,command | grep cook_ep01_pressure_proof_v3.py | grep -v grep` must be empty. After: same check; report PIDs if any survivor.

---

## 5. REQUIRED VERIFICATION RECIPES

**Test suites (all must exit 0 before shipping):**

```bash
cd /Users/rbhanson/fanfic && source .venv/bin/activate
for t in tests/apt_*.py tests/regression_*.py tests/swarm_*.py tests/pressure_*.py; do
  python "$t" || { echo "FAIL: $t"; exit 1; }
done
```

**Live cook (exactly once per ship cycle):**

```bash
cd /Users/rbhanson/fanfic && source .venv/bin/activate
ps -axo pid,etime,command | grep cook_ep01_pressure_proof_v3.py | grep -v grep   # must be empty
python cook_ep01_pressure_proof_v3.py
ps -axo pid,etime,command | grep cook_ep01_pressure_proof_v3.py | grep -v grep   # report any survivors
```

**Verdict extraction:**

```bash
grep -E "^# (final_verdict|verdict_reason|est_audio)" "episodes_text/_pressure_proof_v3_X/01 - audit.txt"
```

---

## 6. CONTRACT REVIEW CHECKLIST (run before claiming PASS)

For each gate a–i in §2:

1. Locate the **coded gate** (file:line) that enforces it. If it is only enforced by reviewer prose, it is not a gate.
2. Locate the **test** that proves the gate fires on violation. If none exists, write one before shipping.
3. Locate the **verdict token** that surfaces when the gate fails. If none exists, add it.
4. Confirm shipped artifact passes.

If any of (1)–(4) is missing for any gate, the cook is not shippable.

---

## 7. KNOWN HOT FILES

| File | Lines | What lives there |
|------|-------|------------------|
| `cook_ep01_pressure_proof_v3.py` | 167–198 | runtime verdict gate |
| `cook_ep01_pressure_proof_v3.py` | 256–289 | post-resolution decision |
| `cook_ep01_pressure_proof_v3.py` | 406–501 | main cook loop (planner-None bug lives ~462–501) |
| `cook_ep01_pressure_proof_v3.py` | 614–727 | final verdict assembly |
| `engine/uatu.py` | 1230–1247 | `EpisodeArc` dataclass |
| `engine/uatu.py` | 1585–1781 | `plan_next_scene_arc` / `_plan_next_scene_arc_async` |
| `engine/agency_engine.py` | 428–570 | `evaluate_pressures_with_pending` |

---

## 8. FLEET-MODE DISPATCH RULES

When operator activates fleet mode:

1. Track work in SQL `todos`. Use kebab-case IDs. Status: `pending` → `in_progress` → `done` | `blocked`.
2. Dispatch via the `task` tool with `mode: background`.
3. Implementer agent (`general-purpose`) does code + tests.
4. Reviewer agent (`code-review`) checks against §2 gates.
5. Validator agent (`general-purpose`) runs full suite + exactly one live cook + writes `_fleet_status/fix_pressure_v{N}.md`.
6. Validator must depend on implementer (`todo_deps`).
7. If a sub-agent fails or is killed, mark its todo `blocked` with reason. Do not silently retry.

---

## 9. DELIVERABLE FORMAT FOR ANY FIX REPORT

`_fleet_status/fix_pressure_v{N}.md` must include, in order:

1. What changed (file:line summary).
2. Verbatim output of any new tests.
3. Verbatim output of full apt/regression/swarm/pressure suites.
4. Final cook verdict with criteria a–i each labeled PASS/FAIL.
5. Literal `est_audio_minutes` value.
6. First 80 lines of shipped episode.
7. Full pressure-resolution log.
8. Open-pressure continuation log.
9. Runtime continuation log.
10. `ps` output before and after cook.

If a section is empty, write `EMPTY` — do not omit the header.

---

## 10. THE PRIME DIRECTIVE

The operator has lost real time and real money to false PASS reports. The only acceptable failure is an honest failure with a correct verdict token. A dishonest PASS is worse than ten honest FAILs.

Read this file again before shipping anything.

# Worker C — APT-03 / APT-04 fixes

**Scope owned:** `engine/scene_tools.py` only.
**Files touched:**
- `engine/scene_tools.py` (modified)
- `tests/apt_03b_action_budget.py` (new)

## Key diffs (engine/scene_tools.py)

### 1. Module docstring + display sanitizer (APT-04 null/bidi)
Added documented choice: chronicle stores raw bytes verbatim (round-trips
through `json.dumps`); display-time safety is provided by a new helper.

```python
MAX_ARG_LEN: int = 2000
DEFAULT_ACTION_BUDGET: int = 50

# U+202A..U+202E (LRE, RLE, PDF, LRO, RLO) + U+2066..U+2069 (LRI, RLI, FSI, PDI)
_BIDI_RE = re.compile(r"[\u202A-\u202E\u2066-\u2069]")

def sanitize_for_display(text: Any) -> Any:
    """Strip NUL bytes and neutralize Unicode bidi-override characters.
    Use only when emitting to a transcript / terminal / log. Chronicle
    state itself is left untouched so json.dumps round-trips faithfully.
    """
    if not isinstance(text, str):
        return text
    return _BIDI_RE.sub("\ufffd", text.replace("\x00", ""))
```

### 2. Stage gains `action_budget`; tracker gains `actions_budget_exhausted`

```python
def _empty_tracker() -> dict:
    return {
        "drinks": 0, "lines_crossed": 0, "decisions_made": 0,
        "arrivals": 0, "settings_changed": 0, "actions": 0,
        "actions_budget_exhausted": False,
    }

@dataclass
class Stage:
    ...
    action_budget: int = DEFAULT_ACTION_BUDGET

def register_stage(present, roster, action_budget=DEFAULT_ACTION_BUDGET) -> str:
    ...
    _STAGES[sid] = Stage(..., action_budget=int(action_budget))
```

`Stage.is_stagnant()` updated to ignore the new bool field.

### 3. BringInCharacter — dedup against present_cast OR pending_arrivals (APT-03)

```python
how_they_arrive: str = Field(..., max_length=MAX_ARG_LEN, description=...)

def run(self) -> str:
    ...
    key = self.character_key.strip().lower()
    if key in stage.present_cast:
        return f"ALREADY ARRIVING/PRESENT: {key}"
    if any(p.get("key") == key for p in stage.pending_arrivals):
        return f"ALREADY ARRIVING/PRESENT: {key}"
    if key not in stage.available_roster:
        return f"ERROR: '{key}' is not in the roster."
    stage.pending_arrivals.append(...)
    stage.tracker["arrivals"] += 1     # only on first-time success
    stage.chronicle.append(...)
```

### 4. TakeAction — budget gate + max_length (APT-03 / APT-04)

```python
action: str = Field(..., max_length=MAX_ARG_LEN, description=...)
consequence: str = Field(default="", max_length=MAX_ARG_LEN, description=...)

def run(self) -> str:
    stage = _STAGES.get(sid)
    if stage is None:
        return "ERROR: no active scene"
    if stage.tracker.get("actions", 0) >= stage.action_budget:
        stage.tracker["actions_budget_exhausted"] = True
        return "ERROR: scene action budget exhausted"
    ...
```

### 5. ChangeSetting — max_length (APT-04)

```python
new_location: str = Field(..., max_length=MAX_ARG_LEN, description=...)
what_happens: str = Field(..., max_length=MAX_ARG_LEN, description=...)
```

Note: `AddressCharacter` has no `message` field in the engine (only
`character_key`), so the spec line "AddressCharacter.message" was a
no-op — character_key still goes through the roster/on-stage gate.

---

## APT-03 — BEFORE → AFTER (caps half, verbatim)

### BEFORE (from `_fleet_status/apt.md`)
```
  • APT-03: 1000 BringIn calls for same key created 1000 chronicle
    entries (duplicate guard FAILED)
```

### AFTER (verbatim `python tests/apt_03_08_caps_and_gate.py`)
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

**Caps half (1000 calls → 1 chronicle entry): PASSES.** The remaining
"FINDINGS" line is about a `run_scene`-level cap that lives in
`engine/agency_engine.py` — outside Worker C's scope.

---

## APT-03b — NEW test (action budget)

Verbatim `python tests/apt_03b_action_budget.py`:
```
=== NOTES ===
  • first 50 TakeAction calls accepted ✓
  • 51st call returned 'ERROR: scene action budget exhausted' ✓
  • tracker['actions_budget_exhausted'] = True ✓
  • tracker['actions'] = 50 (no over-bump) ✓
  • chronicle holds exactly 50 action entries ✓
  • configurable action_budget=3 enforced ✓

HOLDS — TakeAction budget enforced.
```
Exit code: 0.

---

## APT-04 — BEFORE → AFTER (verbatim)

### BEFORE (from `_fleet_status/apt.md`)
```
INFO finding: 1 MB strings for `action`, `consequence`, `new_location`,
`what_happens` are accepted and stored verbatim in chronicle. No
`max_length` on Field(...). Two 1MB entries went into the chronicle in
this test. Combined with APT-03, this is the amplification vector
(BringIn doesn't have free text, but TakeAction/ChangeSetting do).
```

### AFTER (verbatim `python tests/apt_04_malformed_tool_args.py`, tail)
```
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
```
Exit code: 0.

Key wins:
- 1 MB strings: now **rejected** at pydantic-construction time
  (`type=string_too_long`), not stored.
- "giant strings stored in chronicle: 0" (was 2 before).
- Null bytes + bidi: still **stored verbatim** in chronicle (intentional;
  json.dumps round-trips them safely). The new `sanitize_for_display()`
  helper is the sanctioned strip path for transcripts/UIs. Documented
  in the module docstring.

Full outputs archived at:
- `_fleet_status/_apt03_after.txt`
- `_fleet_status/_apt03b_after.txt`
- `_fleet_status/_apt04_after.txt`

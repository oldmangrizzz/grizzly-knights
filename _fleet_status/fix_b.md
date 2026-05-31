# WORKER B — APT-05 Fix Report

**Scope owned:** `engine/chronicle.py` only.
**Other engine modules, character YAMLs, whatifscripts:** untouched.

## Files touched

- `engine/chronicle.py` (modified)
- `tests/apt_05b_atomic_save.py` (new)
- `_fleet_status/fix_b.md` (this file)
- `_fleet_status/_apt05_before.txt`, `_apt05_after.txt`, `_apt05b_after.txt` (run captures)

## Key changes

### 1. `load_chronicle` — defensive read

**Before** (lines 49–52):
```python
def load_chronicle() -> dict[str, Any]:
    if not CHRONICLE_PATH.exists():
        return json.loads(json.dumps(EMPTY_CHRONICLE))  # deep copy
    return json.loads(CHRONICLE_PATH.read_text())
```

**After:**
```python
def load_chronicle() -> dict[str, Any]:
    if not CHRONICLE_PATH.exists():
        return _fresh_empty_chronicle()
    try:
        raw = CHRONICLE_PATH.read_text()
    except OSError as e:
        logger.warning(
            "chronicle: OSError reading %s: %s — returning empty chronicle",
            CHRONICLE_PATH, e,
        )
        return _fresh_empty_chronicle()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.warning(
            "chronicle: malformed JSON in %s: %s — snapshotting and returning empty chronicle",
            CHRONICLE_PATH, e,
        )
        recover_chronicle()
        return _fresh_empty_chronicle()

    chron, repaired = _normalize_chronicle(data)
    if repaired:
        logger.warning(
            "chronicle: repaired top-level keys %s in %s",
            repaired, CHRONICLE_PATH,
        )
        recover_chronicle()
    return chron
```

### 2. `_normalize_chronicle` — schema repair on read

Added a private helper that coerces the parsed object into the canonical
shape. If the root isn't a `dict`, the whole thing is replaced by an empty
chronicle. If `characters` / `relationships` is not a `dict`, or `episodes`
/ `world_facts` is not a `list`, each is replaced with the empty default
and the repaired key name is appended to a list that `load_chronicle`
logs as a warning.

### 3. `save_chronicle` — atomic write

**Before** (lines 55–57):
```python
def save_chronicle(data: dict[str, Any]) -> None:
    CHRONICLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHRONICLE_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False))
```

**After:**
```python
def save_chronicle(data: dict[str, Any]) -> None:
    CHRONICLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = CHRONICLE_PATH.with_suffix(CHRONICLE_PATH.suffix + ".tmp")
    payload = json.dumps(data, indent=2, ensure_ascii=False)
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(payload)
        f.flush()
        try:
            os.fsync(f.fileno())
        except OSError:
            pass
    os.replace(tmp, CHRONICLE_PATH)
```

Write goes to `chronicle.json.tmp` in the same directory, is fsynced, then
`os.replace`'d. `os.replace` is atomic on POSIX, so the on-disk
`chronicle.json` is either the old file or the new file — never partial.

### 4. `recover_chronicle(backup_path)` — snapshot helper

New public helper. Before `load_chronicle` overwrites the in-memory model
of a corrupt file, the corrupt bytes are copied to
`chronicle.json.bak.<YYYYmmdd-HHMMSS>` (or to `backup_path` if supplied)
so the original can be inspected.

### 5. `apply_delta` — behavior preserved

No changes to `apply_delta`. The existing implementation already used
`setdefault` and conditional `if patch.get(...)` checks, which means an
empty/partial delta cannot drop pre-existing state. `apt_05b_atomic_save.py`
adds an explicit regression test that confirms this for empty deltas,
partial deltas (only `add_events`), world_facts, and relationships.

---

## APT-05 — verbatim before

```
=== NOTES ===
  • recent_events as string: OK -> str: 'Recent events:\n  - h\n  - i'
  • huge entry in characters: OK -> str: 'State: XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
  • null character entry: OK -> str: ''
  • apply_delta preserves pre-existing state ✓
  • apply_delta preserves pre-existing world_facts ✓

=== FINDINGS ===
  • malformed json — truncated: load_chronicle crashed on malformed JSON: Expecting ',' delimiter: line 1 column 49 (char 48)
  • wrong top-level type — list: AttributeError: 'list' object has no attribute 'get'
  • missing keys — empty dict: KeyError: 'characters'
  • characters as list: AttributeError: 'list' object has no attribute 'get'
```

## APT-05 — verbatim after

```
chronicle: malformed JSON in /Users/rbhanson/fanfic/universe/chronicle.json: Expecting ',' delimiter: line 1 column 49 (char 48) — snapshotting and returning empty chronicle
chronicle: snapshotted corrupt file to /Users/rbhanson/fanfic/universe/chronicle.json.bak.20260528-111545
chronicle: repaired top-level keys ['<root: not a dict>'] in /Users/rbhanson/fanfic/universe/chronicle.json
chronicle: snapshotted corrupt file to /Users/rbhanson/fanfic/universe/chronicle.json.bak.20260528-111545
chronicle: repaired top-level keys ['characters (missing)', 'relationships (missing)', 'episodes (missing)', 'world_facts (missing)'] in /Users/rbhanson/fanfic/universe/chronicle.json
chronicle: snapshotted corrupt file to /Users/rbhanson/fanfic/universe/chronicle.json.bak.20260528-111545
chronicle: repaired top-level keys ['characters'] in /Users/rbhanson/fanfic/universe/chronicle.json
chronicle: snapshotted corrupt file to /Users/rbhanson/fanfic/universe/chronicle.json.bak.20260528-111545
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
```

All four malformed cases that previously surfaced as FINDINGS now resolve
to a valid chronicle dict (case 1 returns the empty chronicle directly;
cases 2/3/4 return `""` from `full_planner_context` because the cast key
is not present in the now-normalized `characters` dict, which is the
correct degenerate output). Exit code: `0`. The header
`=== FINDINGS ===` block is gone.

## APT-05b — verbatim after (new test)

```
chronicle: snapshotted corrupt file to /Users/rbhanson/fanfic/universe/chronicle.json.bak.20260528-111546
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
  • recover_chronicle created backup ✓ (chronicle.json.bak.20260528-111546)

HOLDS
```

Exit code: `0`.

## Test commands run

```
source .venv/bin/activate
python tests/apt_05_chronicle_tampering.py   # exit 0, HOLDS
python tests/apt_05b_atomic_save.py          # exit 0, HOLDS
```

Both verbatim outputs above. Real `universe/chronicle.json` restored by
each test's `with_backup` wrapper. No stray `.tmp` or `.bak.*` files left
on disk (verified `ls universe/chronicle.json*` → only `chronicle.json`).

## Out of scope (not touched)

- `engine/uatu.py`, `engine/scene_tools.py`, `engine/agency_engine.py`,
  `engine/export_episodes_agency.py` — owned by other workers per APT-02,
  APT-03, APT-06, APT-09. The `KeyError`/`FileNotFoundError`/dedup
  findings in those modules are theirs to fix.
- `universe/characters/*.yaml`, `whatifscripts/`.

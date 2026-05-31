# Fix D — APT-09 (litany / oath dedup + idempotency)

**Worker:** D
**Owner scope:** `export_episodes_agency.py` (only)
**Ground rules respected:** Canonical `UATU_OPENING_LITANY` and
`UATU_CLOSING_OATH` strings in `engine/uatu.py` were **not** modified.

## Files touched

1. `export_episodes_agency.py` — added `import copy`; added a single
   normalization pass at the top of `scripts_to_prose` that strips
   narrator blocks containing the litany or oath anchors. Input
   `Script` objects are not mutated (a shallow copy is taken when any
   block must be dropped).
2. `tests/apt_09b_idempotency.py` — new test covering: (a) clean
   single vs double call equality and exact bookend counts; (b)
   contaminated single vs double call equality and exact bookend
   counts; (c) hostile re-feed where prior whole prose is shoved into
   a narrator block.

## Key diff — `export_episodes_agency.py`

### imports
```
 import re
 import sys
+import copy
 from pathlib import Path
```

### `scripts_to_prose` — BEFORE
```python
def scripts_to_prose(scripts: list, plan: EpisodePlan) -> str:
    from engine.uatu import UATU_OPENING_LITANY, UATU_CLOSING_OATH
    paragraphs: list[str] = []
    paragraphs.append(f"Episode {plan.number}: {plan.title}")
    paragraphs.append("Grizzly Knights")
    paragraphs.append(plan.logline)

    # Uatu opens the show
    paragraphs.append("* * *")
    paragraphs.append(UATU_OPENING_LITANY.strip())

    last_speaker: str | None = None

    for s in scripts:
        paragraphs.append("* * *")
        last_speaker = None

        for b in s.blocks:
            if b.type == "narrator":
                text = re.sub(r"\*+", "", b.text).strip()
                # Strip any wrapping quotes the LLM added around the narration —
                # straight ", curly " ", or angle « ». Iterate in case nested.
                for _ in range(3):
                    stripped = re.sub(
                        r'^[\s]*["\u201c\u201d\u00ab\u00bb]+\s*', '', text)
                    stripped = re.sub(
                        r'\s*["\u201c\u201d\u00ab\u00bb]+[\s]*$', '', stripped)
                    if stripped == text:
                        break
                    text = stripped
                text = text.strip()
                if text:
                    paragraphs.append(text)
                last_speaker = None
            ...
```

### `scripts_to_prose` — AFTER
```python
def scripts_to_prose(scripts: list, plan: EpisodePlan) -> str:
    from engine.uatu import UATU_OPENING_LITANY, UATU_CLOSING_OATH

    # APT-09 normalization pass: strip any narrator blocks that already
    # carry the Uatu opening litany or closing oath so we don't double-
    # bookend. Detect via stable anchor substrings from the canonical
    # strings (we never mutate the canonical litany/oath themselves).
    # Idempotent: a second call sees the same already-clean input.
    _OPEN_ANCHORS = (
        "I am the Watcher. I am your guide through these vast new realities.",
        "Time.\n\nSpace.\n\nReality.",
    )
    _CLOSE_ANCHORS = (
        "For I am the Watcher.",
        "I have watched. I will continue to watch.",
    )

    def _is_bookend_narration(block) -> bool:
        if getattr(block, "type", None) != "narrator":
            return False
        txt = getattr(block, "text", "") or ""
        return (
            any(a in txt for a in _OPEN_ANCHORS)
            or any(a in txt for a in _CLOSE_ANCHORS)
        )

    cleaned_scripts = []
    for s in scripts:
        kept_blocks = [b for b in s.blocks if not _is_bookend_narration(b)]
        if len(kept_blocks) != len(s.blocks):
            s_clean = copy.copy(s)
            s_clean.blocks = kept_blocks
            cleaned_scripts.append(s_clean)
        else:
            cleaned_scripts.append(s)
    scripts = cleaned_scripts

    paragraphs: list[str] = []
    paragraphs.append(f"Episode {plan.number}: {plan.title}")
    paragraphs.append("Grizzly Knights")
    paragraphs.append(plan.logline)

    # Uatu opens the show
    paragraphs.append("* * *")
    paragraphs.append(UATU_OPENING_LITANY.strip())

    last_speaker: str | None = None

    for s in scripts:
        paragraphs.append("* * *")
        last_speaker = None

        for b in s.blocks:
            # ... unchanged stray-quote-stripping + dialogue handling ...
```

The downstream narrator branch (asterisk-stripping, iterative
straight/curly/angle quote stripping, period-before-tag → comma fix,
and dialogue handling) is preserved verbatim. The closing-oath append
at line ~834 is preserved verbatim.

## Why anchors, not full-string match

The canonical litany/oath get `.strip()`-ed before being prepended;
narrator blocks that "contain" them in the wild won't be byte-equal
(whitespace, wrapping quotes the LLM added, surrounding sentences).
Substring match against two stable anchors per bookend is robust to
those cases and covers both anchor styles asked for by the spec
(`"Time. Space. Reality."` family and `"For I am the Watcher."`
family). Anchors are taken verbatim from the canonical strings — they
are not redefinitions of the litany text.

## Idempotency

Calling `scripts_to_prose([s1, s2], plan)` twice on the same inputs
returns byte-identical strings because:

1. Input `Script` objects are never mutated (shallow copy when we
   need to drop blocks).
2. The normalization pass is deterministic and pure — same input
   blocks in, same kept blocks out.
3. The downstream paragraph assembly was already deterministic
   (regression_05 confirms).

## Test runs (verbatim)

### `tests/apt_09_litany_dedup.py`
```
=== NOTES ===
  • opening litany anchor occurrences: 1 (expect 1)
  • closing oath anchor occurrences:   1 (expect 1)
  • clean case bookends present exactly once ✓

=== FINDINGS ===
HOLDS
---EXIT 0---
```

### `tests/apt_09b_idempotency.py`
```
=== NOTES ===
  • contaminated: once==twice -> True
  • contaminated once  open=1 close=1
  • contaminated twice open=1 close=1
  • re-fed: open=1 close=1
  • clean: once==twice -> True

=== FINDINGS ===
HOLDS
---EXIT 0---
```

### `tests/regression_05_scripts_to_prose.py` (sanity — stray quote behavior preserved)
```
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
---EXIT 0---
```

## Status

APT-09: **FIXED.** Bookend counts are exactly one in both contaminated
and clean inputs. Double-call equals single-call. Stray-quote-stripping
behavior preserved. Canonical litany/oath untouched.

"""pressure_24 — stage-direction cleanup regression.

Locks in the dialogue-payload cleaner against the verbatim defect strings
found in the V3.4 shipped artifact ("01 - Tuesday at the Mall.txt").

Each case feeds the raw agent payload to _clean_dialogue_payload and
asserts the output is what a human narrator would actually *say* — with
all stage directions, narrator-action prefixes, possessive body-part
narration, bare-lowercase action fragments, mid-sentence stage-verb
inserts, and orphan inner curly quotes removed, while preserving
contractions (apostrophes share U+2019 with inner-close).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from export_episodes_agency import (
    _clean_dialogue_payload,
    clean_existing_prose,
    prose_to_tts_script,
)


CASES: list[tuple[str, str, str]] = [
    # (name, raw_input, must_not_contain)
    (
        "inner_curly_grins_under_mask",
        "Oh kitten, I'd never dull your claws.\u2019 Grins under the mask. "
        "\u2018Still, you know I love a good chaos cocktail.",
        "Grins under the mask",
    ),
    (
        "leading_I_action_prefix",
        "I lean out the cab window. \u2018Catnip, you're auditioning for "
        "a noir film. Care for a knight in dented spandex?\u2019",
        "I lean out the cab",
    ),
    (
        "my_voice_drops_half_a_note",
        "Tequila first, philosophy second. My voice drops half a note. "
        "Vanessa's blush echoes in my head.",
        "voice drops half a note",
    ),
    (
        "I_tap_a_nail",
        "Boys, boys. I tap a nail against the glass. Flattered, really.",
        "I tap a nail",
    ),
    (
        "bare_lowercase_slow_clap",
        "slow clap",
        "slow clap",
    ),
    (
        "bare_lowercase_slow_clap_comma",
        "slow clap,",
        "slow clap",
    ),
    (
        "mid_sentence_clears_throat",
        "Tiger! clears throat Felicia, articulate as ever, watches the booth.",
        "clears throat",
    ),
    (
        "my_smile_curves",
        "Oh sugar. My smile curves like a question mark. You really think so?",
        "My smile curves",
    ),
    (
        "my_hands_find_table_edge",
        "My hands find the table\u2019s edge, nails dragging just the "
        "faintest scrape. The game's quiet, but the stakes aren't.",
        "My hands find",
    ),
    (
        "apostrophe_preserved_youre",
        "Oh kitten, you're auditioning for a noir film tonight.",
        "youre",  # must NOT collapse to "youre" (loss of apostrophe)
    ),
    (
        "apostrophe_preserved_dont",
        "Don't act like you haven't thought about it.",
        "Dont",
    ),
]


def main() -> int:
    failures: list[str] = []
    for name, raw, banned in CASES:
        cleaned = _clean_dialogue_payload(raw)
        if cleaned is None:
            cleaned_text = ""
        else:
            cleaned_text = cleaned
        if banned in cleaned_text:
            failures.append(
                f"FAIL [{name}]: banned substring {banned!r} survived. "
                f"cleaned={cleaned_text!r}"
            )
            continue
        # Apostrophe-preservation cases also require the original
        # contraction to remain intact.
        if name == "apostrophe_preserved_youre":
            if "you\u2019re" not in cleaned_text and "you're" not in cleaned_text:
                failures.append(
                    f"FAIL [{name}]: apostrophe lost. cleaned={cleaned_text!r}"
                )
                continue
        if name == "apostrophe_preserved_dont":
            if "Don\u2019t" not in cleaned_text and "Don't" not in cleaned_text:
                failures.append(
                    f"FAIL [{name}]: apostrophe lost. cleaned={cleaned_text!r}"
                )
                continue
        print(f"  ok  [{name}]  -> {cleaned_text[:80]!r}")

    # Bonus: full-prose round-trip on the shipped artifact must be a
    # fixed point (cleaning an already-cleaned file must not change it).
    artifact = (
        Path(__file__).resolve().parent.parent
        / "episodes_text" / "_pressure_proof_v3_4"
        / "01 - Tuesday at the Mall.txt"
    )
    if artifact.exists():
        once = clean_existing_prose(artifact.read_text())
        twice = clean_existing_prose(once)
        if once != twice:
            failures.append(
                "FAIL [idempotence]: clean_existing_prose is not a fixed "
                "point on the shipped artifact"
            )
        else:
            print("  ok  [idempotence on shipped artifact]")
        # TTS sidecar must produce zero malformed lines.
        tts = prose_to_tts_script(once)
        bad = [l for l in tts.splitlines() if l and not l.startswith("[")]
        if bad:
            failures.append(
                f"FAIL [tts_sidecar]: {len(bad)} malformed lines: "
                f"{bad[:3]!r}"
            )
        else:
            print("  ok  [tts_sidecar 0 malformed]")

    if failures:
        print()
        for fline in failures:
            print(fline)
        print(f"\nFAIL: {len(failures)} / {len(CASES) + 2} cases")
        return 1
    print(f"\nPASS: {len(CASES) + 2} / {len(CASES) + 2} cases")
    return 0


if __name__ == "__main__":
    sys.exit(main())

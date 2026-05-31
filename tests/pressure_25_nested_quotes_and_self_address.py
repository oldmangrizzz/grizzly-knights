"""pressure_25 — Lock in addendum-6 cleaner contracts.

Verifies that clean_existing_prose:
  (a) Normalizes NESTED outer-curly-double quotes inside a dialogue
      paragraph to curly-single sub-quotes (no nested "…" inside "…").
  (b) Detects self-address contradiction (tag "Wade said" on a line
      that vocatively addresses "Wade, buddy,…") and re-infers the
      speaker via _infer_speaker.
  (c) Drops orphan trailing enumeration fragments like "Second clue—,".
  (d) _infer_speaker treats vocative use of <Name>, as a strong
      negative for that name (an addresser is not the addressee).

These are the four contracts added in fix_pressure_v3_4 addendum 6
after the operator's eyes-on read surfaced defects the prior tests
missed.
"""
from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from export_episodes_agency import clean_existing_prose, _infer_speaker


def _outer_balance_ok(p: str) -> bool:
    return p.count("\u201c") == p.count("\u201d") == 1


def _no_nested_double(p: str) -> bool:
    return p.count("\u201c") == 1 and p.count("\u201d") == 1


def test_a_nested_double_normalized_to_single() -> None:
    raw = (
        "\u201cMary-Jane? Nothing says \u201csustainable hero\u201d like "
        "tethering Peter to red-headed guilt. And his \u201cnoble idiot\u201d "
        "routine wears thin.\u201d Wade said.\n"
    )
    out = clean_existing_prose(raw)
    para = [p for p in out.split("\n\n") if p.strip()][0].strip()
    assert _no_nested_double(para), (
        f"nested outer-doubles not normalized:\n  {para!r}"
    )
    assert "\u2018sustainable hero\u2019" in para, (
        f"expected ‘sustainable hero’ as inner single:\n  {para!r}"
    )
    assert "\u2018noble idiot\u2019" in para, (
        f"expected ‘noble idiot’ as inner single:\n  {para!r}"
    )
    print("  PASS A: nested curly-doubles → curly-singles")


def test_b_self_address_reinfers_speaker() -> None:
    # Tag claims Wade said, but body addresses "Wade, buddy,…" — must re-infer.
    raw = (
        "\u201cOkay, you two\u2014you\u2019re about one tequila breath "
        "away from setting the place on fire. Wade, buddy, I don\u2019t "
        "think \u2018fencing\u2019 means \u2018poking at Felicia until "
        "she flips you off the table.\u2019\u201d Wade said.\n"
    )
    out = clean_existing_prose(raw)
    para = [p for p in out.split("\n\n") if p.strip()][0].strip()
    assert not para.endswith("Wade said."), (
        f"self-address contradiction not corrected:\n  {para!r}"
    )
    # Speaker should re-infer to Peter (only other on-stage option, and
    # the "Wade, buddy" address rules Wade out).
    assert para.endswith("Peter said.") or para.endswith("Felicia said."), (
        f"expected Peter/Felicia tag after re-infer:\n  {para!r}"
    )
    print(f"  PASS B: self-address re-inferred → {para[-20:]}")


def test_c_orphan_clue_fragment_dropped() -> None:
    raw = (
        "\u201cOh, I got this one, Tiger! First clue: your hands are "
        "doing the thing. Second clue\u2014,\u201d Wade said.\n"
    )
    out = clean_existing_prose(raw)
    para = [p for p in out.split("\n\n") if p.strip()][0].strip()
    assert "Second clue" not in para, (
        f"orphan 'Second clue—,' fragment not dropped:\n  {para!r}"
    )
    assert _outer_balance_ok(para), (
        f"outer-quote balance broken after fragment drop:\n  {para!r}"
    )
    print("  PASS C: orphan 'Second clue—,' fragment dropped")


def test_d_vocative_strong_negative_in_inferrer() -> None:
    # Line vocatively addresses Wade → Wade must NOT be the inferred speaker.
    body = (
        "Wade, buddy, I don't think 'fencing' means 'poking at Felicia "
        "until she flips you off the table.'"
    )
    sp = _infer_speaker(body, prev_speaker="felicia_hardy", recent_speakers=[])
    assert sp != "wade_wilson", (
        f"vocative 'Wade,' should disqualify wade_wilson; got {sp}"
    )
    # Now vocatively address Felicia and Peter both: still not them either.
    body2 = "Felicia, darling, knock it off — Peter, you too."
    sp2 = _infer_speaker(body2, prev_speaker=None, recent_speakers=[])
    assert sp2 != "felicia_hardy", f"vocative 'Felicia,' should rule her out; got {sp2}"
    assert sp2 != "peter_parker", f"vocative 'Peter,' should rule him out; got {sp2}"
    print(f"  PASS D: vocative ruled out self-address (D1={sp}, D2={sp2})")


def test_e_idempotence_on_already_clean() -> None:
    clean = (
        "\u201cMary-Jane? Nothing says \u2018sustainable hero\u2019 like "
        "tethering Peter to red-headed guilt.\u201d Wade said.\n"
    )
    once = clean_existing_prose(clean)
    twice = clean_existing_prose(once)
    assert once == twice, (
        f"clean_existing_prose not idempotent:\n"
        f"  once:  {once!r}\n  twice: {twice!r}"
    )
    print("  PASS E: clean_existing_prose idempotent")


def test_f_reported_speech_not_treated_as_self_address() -> None:
    # Wade is recounting a story where Peter said "Wade, I have to live
    # here." The "Wade," inside the inner-single sub-quote is reported
    # speech, NOT Wade addressing himself. Tag should stay Wade said.
    raw = (
        "\u201cClassic Pete. He goes all dad voice on me like, "
        "\u2018Wade, I have to live here.\u2019 Pop-Tart sparks a fire, "
        "and now his kitchen looks like a war crime.\u201d Wade said.\n"
    )
    out = clean_existing_prose(raw)
    para = [p for p in out.split("\n\n") if p.strip()][0].strip()
    assert para.endswith("Wade said."), (
        f"reported speech 'Wade,' inside ‘…’ wrongly treated as self-"
        f"address; tag changed away from Wade:\n  {para!r}"
    )
    print("  PASS F: reported speech inside ‘…’ not treated as self-address")


def test_g_leading_inner_single_preserved() -> None:
    # An inner sub-quote that opens the dialogue body (‘Interesting’…)
    # must NOT have its leading ‘ stripped — that opener is balanced
    # by the matching ’ later in the same body.
    raw = (
        "\u201c\u2018Interesting\u2019 is such a loaded word\u2014more "
        "dangerous than charming, but still lighter than \u2018mess.\u2019 "
        "Are we taking bets?\u201d Peter asked.\n"
    )
    out = clean_existing_prose(raw)
    para = [p for p in out.split("\n\n") if p.strip()][0].strip()
    assert para.startswith("\u201c\u2018Interesting\u2019"), (
        f"leading ‘ before Interesting was stripped; sub-quote broken:\n"
        f"  {para!r}"
    )
    print("  PASS G: leading inner ‘ preserved when matching ’ follows")


def main() -> int:
    print("[pressure-25] nested-quotes + self-address + orphan-clue")
    failures: list[str] = []
    for name, fn in [
        ("A", test_a_nested_double_normalized_to_single),
        ("B", test_b_self_address_reinfers_speaker),
        ("C", test_c_orphan_clue_fragment_dropped),
        ("D", test_d_vocative_strong_negative_in_inferrer),
        ("E", test_e_idempotence_on_already_clean),
        ("F", test_f_reported_speech_not_treated_as_self_address),
        ("G", test_g_leading_inner_single_preserved),
    ]:
        try:
            fn()
        except AssertionError as exc:
            failures.append(f"  \u2717 {name}: {exc}")
        except Exception as exc:  # noqa: BLE001
            failures.append(f"  \u2717 {name}: {type(exc).__name__}: {exc}")
    if failures:
        print("\nFAILURES:")
        for f in failures: print(f)
        print("\nPRESSURE-25: FAIL")
        return 1
    print("\nPRESSURE-25: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

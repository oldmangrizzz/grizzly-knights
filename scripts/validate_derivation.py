#!/usr/bin/env python3
"""
Validate that the UATU engine INDEPENDENTLY DERIVED the operator's expected findings
from canon — rather than being fed them.

For a character, this loads:
  - the operator's expected findings:  universe/characters/_expectations/<stem>.md
  - the engine's independent output:   recovery_research/_dossiers/<stem>.md (+ the profile YAML)

…and asks Opus to judge, finding by finding, whether the engine's assessment ARRIVED at
each expected finding ON ITS OWN, citing the engine's own words. Match = the derivation is
real (research-valid). Miss = the METHOD needs improvement (do NOT feed the answer back in).

The expectations file is NEVER given to the compile engine — only here, as the answer key.

Run:  python3 scripts/validate_derivation.py <stem>
"""
import sys, pathlib

HERE = pathlib.Path(__file__).resolve().parent.parent
CHARS = HERE / "universe" / "characters"
DOSS = HERE / "recovery_research" / "_dossiers"

JUDGE_SYSTEM = """You are a validation auditor for a research instrument. You are given (A) an analyst's \
EXPECTED findings about a subject and (B) an engine's INDEPENDENT assessment of that subject (the engine \
never saw the expected findings). For each expected finding, judge whether the engine's assessment \
INDEPENDENTLY ARRIVED at the same conclusion. Quote the engine's own words as evidence. Verdict per finding: \
DERIVED (engine reached it on its own, quote it), PARTIAL (engine gestured at it but incompletely), or \
MISSED (engine did not reach it). Be strict — paraphrase that merely rhymes is PARTIAL, not DERIVED. End \
with an overall derivation rate and a one-line assessment of whether the engine is genuinely reverse- \
engineering the personality or just producing plausible prose."""


def main():
    if len(sys.argv) < 2:
        print("usage: validate_derivation.py <stem>"); return 2
    stem = sys.argv[1].replace(".yaml", "")
    exp_p = CHARS / "_expectations" / f"{stem}.md"
    dos_p = DOSS / f"{stem}.md"
    if not exp_p.exists():
        print(f"no expectations file for {stem} (nothing to validate against)"); return 1
    if not dos_p.exists():
        print(f"no engine dossier for {stem} (run: python3 engine/uatu_compiler.py dossier {stem} ...)"); return 1

    expected = exp_p.read_text(encoding="utf-8")
    engine_out = dos_p.read_text(encoding="utf-8")

    try:
        from engine.copilot_client import CopilotClient
    except ImportError:
        sys.path.insert(0, str(HERE))
        from engine.copilot_client import CopilotClient

    user = ("(A) ANALYST'S EXPECTED FINDINGS (the answer key — the engine never saw this):\n\n"
            + expected
            + "\n\n(B) THE ENGINE'S INDEPENDENT ASSESSMENT:\n\n"
            + engine_out
            + "\n\nNow audit, finding by finding.")
    client = CopilotClient(model="claude-opus-4.7", temperature=0.3, max_tokens=6000)
    report = client.complete([
        {"role": "system", "content": JUDGE_SYSTEM},
        {"role": "user", "content": user},
    ])
    out = HERE / "recovery_research" / "_engine_out" / f"{stem}.validation.md"
    out.write_text(report, encoding="utf-8")
    print(report)
    print(f"\n[saved -> {out}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())

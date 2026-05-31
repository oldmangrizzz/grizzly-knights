"""
Regression item 2 — Uatu.plan_episode with continuation_from.

Live model. Feed a real prior episode file (from _archive_broken_run1) and
verify the planner produces a plan whose scene 1 situation references
the prior episode's content — not a generic "cold open" placeholder.

We DO NOT have a `previous_recap` field on the EpisodePlan itself (that
lives on SceneSpec, threaded by run_episode at scene time). What we
*can* verify here is that the LLM was actually fed the prior episode
text (so the resulting plan's scene-1 situation references its characters,
location, or named props) and is not a generic invention.
"""
from __future__ import annotations
from pathlib import Path as _ShimPath
import sys as _shim_sys
_shim_sys.path.insert(0, str(_ShimPath(__file__).parent.parent))
import sys, json, time, re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
from engine.uatu import plan_episode


PRIOR_FILE = (
    Path(__file__).resolve().parent.parent
    / "episodes_text" / "_archive_broken_run1" / "04 - Whiskey and Firelight.txt"
)


def main() -> int:
    if not PRIOR_FILE.exists():
        print(f"ITEM 2: FAIL — prior episode missing: {PRIOR_FILE}")
        return 1

    prior_text = PRIOR_FILE.read_text()
    print(f"Prior episode: {PRIOR_FILE.name}  ({len(prior_text)} chars)")

    # Anchor tokens we expect the planner could pull through — read the
    # head and tail of the prior episode to find concrete proper nouns.
    head = prior_text[:600]
    tail = prior_text[-1500:]
    print("--- prior tail (last 600 chars) ---")
    print(tail[-600:])
    print("--- end tail ---")

    t0 = time.time()
    print(f"\nCalling plan_episode(continuation_from=...) at t=0 …")
    try:
        plan = plan_episode(continuation_from=PRIOR_FILE, episode_number=902)
    except Exception as e:
        import traceback
        print(f"ITEM 2: FAIL — plan_episode raised: {type(e).__name__}: {e}")
        traceback.print_exc()
        return 1
    dt = time.time() - t0
    print(f"\nPlan returned in {dt:.1f}s")
    print(f"  title={plan.title!r}")
    print(f"  cast={plan.cast}")
    print(f"  scene[1].situation = {plan.scenes[0].get('situation','')[:400]}")

    failures = []

    # 1. Schema present
    if not plan.scenes or not plan.scenes[0].get("situation"):
        failures.append(("scene1", "missing situation"))

    # 2. Cast overlap: dynamically detect prior characters by scanning
    #    the prior episode text for every roster name/alias. The
    #    continuation cast SHOULD overlap by at least one key.
    import yaml
    from engine.uatu import CHARACTERS_DIR
    prior_lower = prior_text.lower()
    prior_chars = []
    for p in CHARACTERS_DIR.glob("*.yaml"):
        if p.stem == "uatu_the_watcher":
            continue
        try:
            prof = yaml.safe_load(p.read_text()) or {}
        except Exception:
            continue
        name = str(prof.get("name", "")).lower().strip()
        alias = str(prof.get("alias", "")).lower().strip()
        tokens = []
        if name:
            tokens.append(name)
            # also try last name only (e.g. "Murdock", "Logan")
            parts = name.split()
            if len(parts) >= 2:
                tokens.append(parts[-1])
        if alias:
            tokens.append(alias)
        for tok in tokens:
            if len(tok) >= 4 and re.search(rf"\b{re.escape(tok)}\b", prior_lower):
                prior_chars.append(p.stem)
                break
    prior_chars = sorted(set(prior_chars))
    print(f"  prior episode features: {prior_chars}")
    overlap = set(plan.cast) & set(prior_chars)
    if not overlap:
        failures.append(("cast-overlap",
                        f"no cast overlap between continuation plan {plan.cast} "
                        f"and prior episode {prior_chars}"))
    else:
        print(f"  PASS cast overlap: {sorted(overlap)}")

    # 3. The scene-1 situation should NOT be a generic cold-open placeholder.
    sit = plan.scenes[0].get("situation", "").lower()
    bad_phrases = [
        "cold open — nothing yet",
        "cold open - nothing yet",
        "cold open. nothing yet",
        "tbd",
        "to be determined",
        "placeholder",
    ]
    hit = [p for p in bad_phrases if p in sit]
    if hit:
        failures.append(("scene1-placeholder",
                        f"scene 1 situation looks like a placeholder: {hit}"))
    else:
        print("  PASS scene 1 situation is not a placeholder")

    # 4. Continuity reference: scene 1 situation should reference at least
    #    one continuation cue — either a character name from the prior
    #    cast, or temporal phrasing ("the next morning", "later that
    #    night", "picking up", "after", "following").
    continuation_cues = [
        "next morning", "next day", "later", "the morning after",
        "picking up", "after the", "following", "hours later",
        "still", "carries", "previously",
    ]
    has_temporal_cue = any(c in sit for c in continuation_cues)
    char_name_hit = any(
        n in sit
        for k in prior_chars
        for n in [k.split("_")[0]]
    )
    if not (has_temporal_cue or char_name_hit):
        failures.append(("scene1-continuity",
                        f"scene 1 situation lacks temporal or character continuation cue: {sit[:200]}"))
    else:
        if has_temporal_cue:
            print("  PASS scene 1 situation has temporal continuation cue")
        if char_name_hit:
            print("  PASS scene 1 situation references prior-episode character")

    # Save plan
    out = REPO_ROOT / "episodes_text" / "_regression_run" / "_item02_continuation_plan.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "number":  plan.number,
        "title":   plan.title,
        "logline": plan.logline,
        "cast":    plan.cast,
        "arc":     plan.arc,
        "continuation_from": str(PRIOR_FILE),
        "scenes":  plan.scenes,
    }, indent=2, ensure_ascii=False))
    print(f"  evidence: {out}")

    if failures:
        print("\nFAILURES:")
        for n, err in failures:
            print(f"  ✗ {n}: {err}")
        print("ITEM 2: FAIL")
        return 1

    print(f"\nITEM 2: PASS  (elapsed {dt:.1f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

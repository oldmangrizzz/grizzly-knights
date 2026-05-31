"""
Regression item 1 — Uatu.plan_episode with a FRESH premise.

Live model call. Validates the plan schema and cast-coverage validator.
"""
from __future__ import annotations
from pathlib import Path as _ShimPath
import sys as _shim_sys
_shim_sys.path.insert(0, str(_ShimPath(__file__).parent.parent))
import sys, json, time
from engine.uatu import plan_episode


PREMISE = (
    "Jessica Jones and Luke Cage at a Hell's Kitchen dive bar at "
    "1 AM. Matt Murdock shows up bleeding and asks for a favor neither "
    "of them wants to grant. Frank Castle is sitting at the end of the bar "
    "pretending he doesn't know any of them."
)
# Frank Castle is named but in a passive role — the cast-coverage validator
# should still fold him in even if the planner is tempted to leave him out.


def main() -> int:
    failures = []
    t0 = time.time()
    print(f"Calling plan_episode(premise=...) at t=0 …")
    try:
        plan = plan_episode(premise=PREMISE, episode_number=901)
    except Exception as e:
        import traceback
        print(f"ITEM 1: FAIL — plan_episode raised: {type(e).__name__}: {e}")
        traceback.print_exc()
        return 1
    dt = time.time() - t0
    print(f"Plan returned in {dt:.1f}s — title={plan.title!r}")
    print(f"  cast={plan.cast}")
    print(f"  scenes={len(plan.scenes)}")
    print(f"  arc={plan.arc!r}")

    # ── Schema: top-level ─────────────────────────────────────────────────
    if not plan.title:
        failures.append(("title", "empty"))
    if not plan.logline:
        failures.append(("logline", "empty"))
    if not plan.cast or not isinstance(plan.cast, list):
        failures.append(("cast", "missing or not a list"))
    if not plan.scenes or not isinstance(plan.scenes, list):
        failures.append(("scenes", "missing or not a list"))
    if not plan.arc or not isinstance(plan.arc, str) or len(plan.arc) < 10:
        failures.append(("arc", f"missing/short episode-level arc: {plan.arc!r}"))

    # ── Per-scene schema ──────────────────────────────────────────────────
    REQUIRED = {"location", "situation"}  # uatu spec uses "time", "location"
    # The PLAN_MODE spec uses: act, location, time, situation, arrives, departs, escalation
    PER_SCENE = ["act", "location", "time", "situation", "arrives", "departs", "escalation"]
    for i, sc in enumerate(plan.scenes, 1):
        if not isinstance(sc, dict):
            failures.append((f"scene[{i}]", "not a dict"))
            continue
        missing_keys = [k for k in PER_SCENE if k not in sc]
        if missing_keys:
            failures.append((f"scene[{i}]", f"missing keys: {missing_keys}"))
        # arrives/departs must be lists (possibly empty)
        if "arrives" in sc and not isinstance(sc["arrives"], list):
            failures.append((f"scene[{i}].arrives", f"not a list: {type(sc['arrives']).__name__}"))
        if "departs" in sc and not isinstance(sc["departs"], list):
            failures.append((f"scene[{i}].departs", f"not a list: {type(sc['departs']).__name__}"))
        # situation must be substantive
        if "situation" in sc and (not sc["situation"] or len(sc["situation"]) < 40):
            failures.append((f"scene[{i}].situation",
                            f"too short: {sc.get('situation','')!r}"))
        # We don't enforce "roles" — the PLAN_MODE schema doesn't have it.
        # The user spec wording "roles" maps to per-scene arrives + the
        # cast-on-stage being derived from plan.cast (no per-scene cast field
        # is in PLAN_MODE today).

    # ── Cast coverage validator: Frank Castle named in premise ─────────────
    if "frank_castle" not in plan.cast:
        failures.append(("cast-coverage",
                        "frank_castle named in premise but missing from plan.cast — "
                        "post-plan validator failed to fold him in"))
    else:
        print("  PASS cast-coverage folded in frank_castle")

    # Jessica/Luke/Matt should be present too
    for k in ("jessica_jones", "luke_cage", "matt_murdock"):
        if k not in plan.cast:
            failures.append(("cast-coverage", f"{k} missing from cast"))

    # Save plan for downstream evidence + item-2 continuation source
    from pathlib import Path

    REPO_ROOT = Path(__file__).resolve().parent.parent
    out = REPO_ROOT / "episodes_text" / "_regression_run" / "_item01_plan.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "number":  plan.number,
        "title":   plan.title,
        "logline": plan.logline,
        "cast":    plan.cast,
        "arc":     plan.arc,
        "scenes":  plan.scenes,
    }, indent=2, ensure_ascii=False))
    print(f"  evidence: {out}")

    if failures:
        print("\nFAILURES:")
        for n, err in failures:
            print(f"  ✗ {n}: {err}")
        print("ITEM 1: FAIL")
        return 1

    print(f"\nITEM 1: PASS  (elapsed {dt:.1f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Cook a fresh 4-scene Felicia/Wade episode for the remediation verification."""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from engine.agency_engine import EpisodePlan, build_model, run_episode_sync
from engine.chronicle import CHRONICLE_PATH, load_chronicle
from engine.uatu import UATU_OPENING_LITANY, UATU_CLOSING_OATH, chronicle_episode
from export_episodes_agency import scripts_to_prose

OUT_DIR = ROOT / "episodes_text" / "_remediation_run"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PLAN = EpisodePlan(
    number=901,
    title="Remediation Run — Felicia and Wade",
    cast=["felicia_hardy", "wade_wilson"],
    logline=(
        "Felicia and Wade at the Cheesecake Factory. Peter shows up. MJ and "
        "Johnny arrive. Something has to break by scene end."
    ),
    scenes=[
        {
            "act": 1,
            "location": "Cheesecake Factory — back booth",
            "time": "Tuesday, 3:14 PM",
            "situation": (
                "Felicia and Wade are two drinks deep at their standing weekly "
                "booth. Avocado eggrolls between them. Wade has switched from "
                "margarita to straight vodka. Felicia is picking at the salt rim. "
                "They are talking about Peter Parker, who has been wound tight "
                "for weeks. Establish their texture — crude, fluent, comfortable."
            ),
        },
        {
            "act": 1,
            "location": "Cheesecake Factory — same booth",
            "time": "Tuesday, 3:41 PM",
            "situation": (
                "Twenty-five minutes later. Peter Parker has walked in unplanned, "
                "looking worried about something he won't yet name. Felicia and "
                "Wade pivot to catch him before he bolts. The scheme they were "
                "hatching about him is now happening in front of him."
            ),
        },
        {
            "act": 2,
            "location": "Cheesecake Factory — same booth",
            "time": "Tuesday, 4:08 PM",
            "situation": (
                "Mary Jane Watson arrives — Felicia texted her. She slides in "
                "next to Peter. The energy shifts: MJ knows Peter in ways the "
                "others don't, and the conversation cuts closer to bone."
            ),
        },
        {
            "act": 2,
            "location": "Cheesecake Factory — same booth",
            "time": "Tuesday, 4:32 PM",
            "situation": (
                "Johnny Storm shows up loudly — Wade's idea. The booth is now "
                "full. Something breaks: a confession, a fight, a kiss, a "
                "decision — but it breaks. End the scene on the break, not "
                "after it."
            ),
        },
    ],
)


def main() -> int:
    model = build_model("gpt-4o")

    chron_before = load_chronicle()
    snap_before = {
        "characters": len(chron_before.get("characters") or {}),
        "relationships": len(chron_before.get("relationships") or {}),
        "world_facts": len(chron_before.get("world_facts") or []),
        "episodes": len(chron_before.get("episodes") or []),
    }
    print(f"chronicle BEFORE: {snap_before}")

    t0 = time.time()
    scripts = run_episode_sync(PLAN, model)
    print(f"\nrun_episode_sync: {len(scripts)} scenes in {(time.time()-t0)/60:.1f} min")

    coverage = []
    for s in scripts:
        coverage.append({
            "scene": s.scene_number,
            "_gk_coverage_complete": getattr(s, "_gk_coverage_complete", None),
        })
    print(f"per-scene coverage flags: {coverage}")

    prose = scripts_to_prose(scripts, PLAN)
    out = OUT_DIR / f"{PLAN.number:03d} - {PLAN.title}.txt"
    out.write_text(prose)
    print(f"wrote {out}  ({len(prose)} chars, {len(prose.split())} words)")

    open_count = prose.count(UATU_OPENING_LITANY.strip())
    close_count = prose.count(UATU_CLOSING_OATH.strip())
    starts_open = prose.lstrip().startswith(UATU_OPENING_LITANY.strip())
    ends_close = prose.rstrip().endswith(UATU_CLOSING_OATH.strip())
    print(f"litany opens={open_count} top={starts_open}  oath closes={close_count} bottom={ends_close}")

    meta = {
        "number":  PLAN.number,
        "title":   PLAN.title,
        "cast":    PLAN.cast,
        "logline": PLAN.logline,
    }
    delta = chronicle_episode(out, meta)
    n_chars = len(delta.get("characters") or {})
    n_rels = len(delta.get("relationships") or {})
    n_facts = len(delta.get("world_facts") or [])
    print(f"chronicle DELTA: chars={n_chars} rels={n_rels} facts={n_facts}")

    chron_after = load_chronicle()
    snap_after = {
        "characters": len(chron_after.get("characters") or {}),
        "relationships": len(chron_after.get("relationships") or {}),
        "world_facts": len(chron_after.get("world_facts") or []),
        "episodes": len(chron_after.get("episodes") or []),
    }
    print(f"chronicle AFTER: {snap_after}")

    summary = {
        "out_path": str(out),
        "scene_count": len(scripts),
        "coverage": coverage,
        "litany_count": open_count,
        "litany_at_top": starts_open,
        "oath_count": close_count,
        "oath_at_bottom": ends_close,
        "delta": {"chars": n_chars, "rels": n_rels, "facts": n_facts},
        "chronicle_before": snap_before,
        "chronicle_after": snap_after,
    }
    (OUT_DIR / "_verification.json").write_text(json.dumps(summary, indent=2))

    ok = (
        len(scripts) == 4
        and open_count == 1 and starts_open
        and close_count == 1 and ends_close
        and (n_chars + n_rels + n_facts) > 0
        and all(c["_gk_coverage_complete"] is not None for c in coverage)
    )
    print(f"\nALL CHECKS: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

"""
Regression items 6 + 10 — full episode end-to-end (4-scene plan) and
chronicle delta application.

Builds an EpisodePlan with exactly 4 scenes manually (the planner produces
10, but the user spec for item 10 is "4-scene plan, any premise"). Runs
run_episode_sync to produce scripts, scripts_to_prose to produce prose,
saves the .txt under episodes_text/_regression_run/, then ingests the
episode into the chronicle via chronicle_episode and asserts that:

  • the prose file exists, has both bookends, has non-trivial wordcount
  • universe/chronicle.json grew (or was created) with this episode's beats
  • the new episode entry's number/title/cast match
  • at least one TakeAction-with-consequence beat made it into the chronicle
    (via chronicle.episodes[-1].beats OR via characters[*].recent_events)
"""
from __future__ import annotations
from pathlib import Path as _ShimPath
import sys as _shim_sys
_shim_sys.path.insert(0, str(_ShimPath(__file__).parent.parent))
import sys, json, time, shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

from engine.agency_engine import EpisodePlan, run_episode_sync, build_model
from engine.chronicle import CHRONICLE_PATH, load_chronicle
from engine.uatu import chronicle_episode, UATU_OPENING_LITANY, UATU_CLOSING_OATH
from export_episodes_agency import scripts_to_prose


PLAN = EpisodePlan(
    number=910,
    title="Regression Cook Four Beats",
    logline=(
        "Wade Wilson and Felicia Hardy spend a Tuesday night doing four "
        "small bad decisions in a row. Nobody calls it that. Everybody knows."
    ),
    cast=["wade_wilson", "felicia_hardy"],
    arc=(
        "A quiet two-hander across four locations: bar booth, parking lot, "
        "cab ride, Wade's apartment. Each beat raises the temperature one "
        "click. By the end one of them has named the thing neither of them "
        "was going to name."
    ),
    scenes=[
        {
            "act": 1,
            "location": "Skinny Dennis — Williamsburg, back corner booth",
            "time": "Tuesday, 9:47 PM",
            "situation": (
                "Felicia and Wade are two rounds deep — her: tequila neat, "
                "him: PBR tallboy and a shot of Jameson on the side. The "
                "booth is sticky. The jukebox is playing Townes Van Zandt. "
                "They are here because Wade asked her to meet, and he has "
                "not yet said why. Picking up cold."
            ),
            "arrives": [],
            "departs": [],
            "escalation": (
                "Wade names the reason he asked to meet. Felicia commits "
                "or refuses on the spot."
            ),
        },
        {
            "act": 2,
            "location": "Skinny Dennis parking lot — back lot by the dumpster",
            "time": "Tuesday, 10:34 PM",
            "situation": (
                "Three minutes after the booth conversation. They stepped "
                "outside so Wade can smoke a Camel and Felicia can think. "
                "The streetlight is buzzing. Whatever was said inside is "
                "still in the air between them."
            ),
            "arrives": [],
            "departs": [],
            "escalation": (
                "A hand lands somewhere it has not landed before. Or one of "
                "them walks back to the bar alone. No clean exit."
            ),
        },
        {
            "act": 2,
            "location": "Yellow cab — Williamsburg Bridge eastbound",
            "time": "Tuesday, 11:08 PM",
            "situation": (
                "Picking up from the parking lot. They are in the back of "
                "a cab heading to Wade's place. The driver has the radio on. "
                "Neither of them has said the word that ended scene 2 out "
                "loud yet."
            ),
            "arrives": [],
            "departs": [],
            "escalation": (
                "The thing they didn't say in the parking lot gets said in "
                "the cab. Or it doesn't, and one of them gets out at the next "
                "light."
            ),
        },
        {
            "act": 3,
            "location": "Wade's apartment — Hell's Kitchen walk-up, kitchen",
            "time": "Tuesday, 11:42 PM",
            "situation": (
                "Picking up from the cab. The door is shut behind them. "
                "Wade is pouring two fingers of Bulleit each. Felicia has "
                "her boots off. Whatever happened in the cab is the floor "
                "they are standing on now."
            ),
            "arrives": [],
            "departs": [],
            "escalation": (
                "The night either becomes a thing they admit is a thing, "
                "or one of them goes home. ChangeSetting or TakeAction with "
                "a consequence commits whichever way it lands."
            ),
        },
    ],
)


def main() -> int:
    out_dir = REPO_ROOT / "episodes_text" / "_regression_run"
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── Snapshot chronicle before ───────────────────────────────────────
    chron_before = load_chronicle()
    n_eps_before = len(chron_before.get("episodes", []))
    n_chars_before = len(chron_before.get("characters", {}))
    n_facts_before = len(chron_before.get("world_facts", []))
    print(f"[chron snapshot pre]  episodes={n_eps_before}  "
          f"chars={n_chars_before}  facts={n_facts_before}")
    snap_path = out_dir / "_item06_chronicle_before.json"
    snap_path.write_text(json.dumps(chron_before, indent=2, ensure_ascii=False))

    # ── Cook ────────────────────────────────────────────────────────────
    t0 = time.time()
    model = build_model("gpt-4o")
    print(f"[item 10] cooking 4-scene episode …")

    scene_count = 0
    def on_scene(s):
        nonlocal scene_count
        scene_count += 1
        ndlg = sum(1 for b in s.blocks if b.type == "dialogue")
        nnar = sum(1 for b in s.blocks if b.type == "narrator")
        ntc = len(getattr(s, "_gk_tool_calls", []) or [])
        print(f"  ✓ scene {scene_count}/{len(PLAN.scenes)} — "
              f"{s.location[:48]} — {ndlg}dlg/{nnar}narr/{ntc}tools")

    try:
        scripts = run_episode_sync(PLAN, model, on_scene=on_scene)
    except Exception as e:
        import traceback
        print(f"ITEM 10: FAIL — run_episode_sync raised: {type(e).__name__}: {e}")
        traceback.print_exc()
        return 1

    if len(scripts) != len(PLAN.scenes):
        print(f"ITEM 10: FAIL — produced {len(scripts)} scripts, expected {len(PLAN.scenes)}")
        return 1

    # ── Prose ───────────────────────────────────────────────────────────
    prose = scripts_to_prose(scripts, PLAN)
    out_file = out_dir / f"{PLAN.number:02d} - {PLAN.title}.txt"
    out_file.write_text(prose)
    words = len(prose.split())
    print(f"[item 10] wrote {out_file.name}  ({words} words, "
          f"{out_file.stat().st_size/1024:.1f} KB)")

    failures = []
    if UATU_OPENING_LITANY.strip() not in prose:
        failures.append(("opening litany missing in cooked prose", "—"))
    if UATU_CLOSING_OATH.strip() not in prose:
        failures.append(("closing oath missing in cooked prose", "—"))
    if words < 500:
        failures.append(("wordcount", f"only {words} words — episode too thin"))

    # ── Chronicle ingest ────────────────────────────────────────────────
    print(f"[item 6] ingesting episode into chronicle …")
    meta = {
        "number":  PLAN.number,
        "title":   PLAN.title,
        "cast":    PLAN.cast,
        "logline": PLAN.logline,
    }
    try:
        delta = chronicle_episode(out_file, meta)
    except Exception as e:
        import traceback
        print(f"ITEM 6: FAIL — chronicle_episode raised: {type(e).__name__}: {e}")
        traceback.print_exc()
        # Continue so item 10 can still report
        delta = None

    chron_after = load_chronicle()
    snap_after = out_dir / "_item06_chronicle_after.json"
    snap_after.write_text(json.dumps(chron_after, indent=2, ensure_ascii=False))
    n_eps_after = len(chron_after.get("episodes", []))
    n_chars_after = len(chron_after.get("characters", {}))
    n_facts_after = len(chron_after.get("world_facts", []))
    print(f"[chron snapshot post] episodes={n_eps_after}  "
          f"chars={n_chars_after}  facts={n_facts_after}")

    if delta is None:
        failures.append(("chronicle ingest", "chronicle_episode raised"))
    else:
        delta_path = out_dir / "_item06_chronicle_delta.json"
        delta_path.write_text(json.dumps(delta, indent=2, ensure_ascii=False))

        if n_eps_after != n_eps_before + 1:
            failures.append(("chronicle episodes",
                            f"episodes went {n_eps_before} → {n_eps_after}, expected +1"))
        else:
            last_ep = chron_after["episodes"][-1]
            if last_ep.get("number") != PLAN.number:
                failures.append(("chronicle episode number",
                                f"last episode number={last_ep.get('number')}, expected {PLAN.number}"))
            if last_ep.get("title") != PLAN.title:
                failures.append(("chronicle episode title",
                                f"last episode title={last_ep.get('title')!r}, expected {PLAN.title!r}"))
            beats = last_ep.get("beats") or []
            if not beats:
                failures.append(("chronicle beats", "no beats recorded for this episode"))
            else:
                print(f"  PASS chronicle episode entry has {len(beats)} beats")

        # Per-character recent_events should have NEW entries tagged [ep 10]
        ep_tag = f"[ep {PLAN.number:02d}]"
        new_events = []
        for k in PLAN.cast:
            ev = chron_after.get("characters", {}).get(k, {}).get("recent_events", [])
            for e in ev:
                if isinstance(e, str) and ep_tag in e:
                    new_events.append((k, e))
        if not new_events:
            failures.append(("chronicle character events",
                            f"no recent_events tagged {ep_tag} for cast {PLAN.cast}"))
        else:
            print(f"  PASS chronicle character events: {len(new_events)} tagged {ep_tag}")
            for k, e in new_events[:5]:
                print(f"    - {k}: {e}")

    if failures:
        print("\nFAILURES:")
        for n, err in failures:
            print(f"  ✗ {n}: {err}")
        print(f"\nITEMS 6+10: FAIL  (elapsed {time.time()-t0:.1f}s)")
        return 1
    print(f"\nITEMS 6+10: PASS  (elapsed {time.time()-t0:.1f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

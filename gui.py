"""
Grizzly Knights — GUI

Streamlit app. Two modes:
  • Click "Cook me one" → ShowRunner picks cast + premise + plan, performs it.
  • Type a premise (optionally pick cast) → ShowRunner plans it, performs it.

Run:  streamlit run gui.py
"""

import os
import re
import sys
import threading
import time
from pathlib import Path
from queue import Queue, Empty

import streamlit as st
import yaml

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from engine.agency_engine import (
    EpisodePlan, build_model, run_episode_sync,
)
from engine.uatu import (
    plan_episode, list_available_characters, _character_one_liner,
)
from export_episodes_agency import scripts_to_prose

OUTPUT_DIR = ROOT / "episodes_text"
OUTPUT_DIR.mkdir(exist_ok=True)


def _all_cooked_episodes() -> list[Path]:
    """Every cooked episode prose file under episodes_text/ (recursive),
    newest first.

    Excludes sidecar artifacts (`.tts.txt`, `.audit.txt`, and any file with
    "audit" in its stem) so only the canonical episode prose is offered as
    a continuation candidate.
    """
    paths = list(OUTPUT_DIR.rglob("[0-9][0-9] - *.txt"))
    paths = [
        p for p in paths
        if ".tts." not in p.name
        and ".audit." not in p.name
        and "audit" not in p.stem.lower()
    ]
    paths.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return paths


def next_episode_number(scope: Path | None = None) -> int:
    """Next ep number. Defaults to scanning all of episodes_text/ recursively.
    If `scope` is given, scans only that directory."""
    base = scope or OUTPUT_DIR
    existing = []
    pattern = "[0-9][0-9] - *.txt"
    for p in (base.rglob(pattern) if scope is None else base.glob(pattern)):
        m = re.match(r"^(\d+)", p.name)
        if m:
            existing.append(int(m.group(1)))
    return (max(existing) + 1) if existing else 1


def _character_label(key: str) -> str:
    try:
        prof = yaml.safe_load((ROOT / "universe" / "characters" / f"{key}.yaml").read_text())
        name = prof.get("name", key)
        alias = prof.get("alias")
        return f"{name}" + (f" ({alias})" if alias else "")
    except Exception:
        return key


# ─── Background worker ───────────────────────────────────────────────────────

def _cook(premise: str, cast: list[str], ep_num: int, log_q: Queue,
          result_q: Queue, continuation_from: Path | None = None):
    """Run in a background thread. Push status updates onto log_q."""
    try:
        if continuation_from:
            log_q.put(("status",
                       f"Planning continuation of `{continuation_from.name}`..."))
        else:
            log_q.put(("status", "Planning episode (Uatu)..."))
        plan = plan_episode(
            premise = premise or None,
            cast    = cast or None,
            episode_number = ep_num,
            continuation_from = continuation_from,
        )
        log_q.put(("status", f"Plan ready: {plan.title}  •  cast: {', '.join(plan.cast)}  •  {len(plan.scenes)} scenes"))
        log_q.put(("plan", plan))

        model = build_model("gpt-4o")

        def on_scene(s):
            log_q.put(("scene", {
                "act": s.act,
                "scene": s.scene_number,
                "location": s.location,
                "dlg": sum(1 for b in s.blocks if b.type == "dialogue"),
                "narr": sum(1 for b in s.blocks if b.type == "narrator"),
            }))

        scripts = run_episode_sync(plan, model, on_scene=on_scene)
        prose = scripts_to_prose(scripts, plan)
        out_dir = (
            continuation_from.parent
            if continuation_from is not None
            else OUTPUT_DIR
        )
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"{plan.number:02d} - {plan.title}.txt"
        out.write_text(prose)
        # TTS sidecar — speaker-tagged script for audio production
        try:
            from export_episodes_agency import prose_to_tts_script
            tts = prose_to_tts_script(prose)
            (out_dir / f"{plan.number:02d} - {plan.title}.tts.txt").write_text(tts)
        except Exception as _e:
            log_q.put(("status",
                       f"WARN: TTS sidecar failed: {type(_e).__name__}: {_e}"))

        result_q.put({
            "status":  "done",
            "path":    str(out),
            "title":   plan.title,
            "prose":   prose,
            "words":   len(prose.split()),
        })
    except Exception as e:
        import traceback
        result_q.put({"status": "error", "error": f"{type(e).__name__}: {e}",
                      "trace": traceback.format_exc()})


# ─── UI ──────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="Grizzly Knights", layout="wide")
st.title("Grizzly Knights")
st.caption("Audio drama universe engine. Marvel-Knights-darker. Characters as agents.")

with st.sidebar:
    st.subheader("Roster")
    chars = list_available_characters()
    selected_cast: list[str] = st.multiselect(
        "Cast (optional — leave blank to let the ShowRunner pick)",
        options=chars,
        format_func=_character_label,
        max_selections=4,
    )
    st.caption(f"{len(chars)} characters available")

    st.markdown("---")
    st.subheader("Previously cooked")
    st.caption("Click **Next →** to continue that specific thread. "
               "Scans every series under `episodes_text/` (incl. proof-cook dirs).")
    _prior_eps = _all_cooked_episodes()[:15]
    if not _prior_eps:
        st.caption("_no prior episodes yet_")
    for p in _prior_eps:
        rel = p.relative_to(OUTPUT_DIR)
        c1, c2 = st.columns([5, 2])
        with c1:
            st.write(f"`{rel}`")
        with c2:
            if st.button("Next →", key=f"next_{rel}", use_container_width=True):
                st.session_state.continuation_from = str(p)
                st.session_state.trigger_cook = True
                st.rerun()


col_a, col_b = st.columns([3, 2])

with col_a:
    premise = st.text_area(
        "Premise (optional)",
        height=120,
        placeholder=(
            "Leave blank for a surprise. Or write whatever you want chased "
            "down — 'Frank Castle and Matt Murdock argue in a Hell's "
            "Kitchen dive about whether the guy Matt left breathing should "
            "have been left breathing.'"
        ),
    )

    cook = st.button("🔥  Cook me one", type="primary", use_container_width=True)

with col_b:
    st.markdown("**Output**")
    st.caption(f"Files in `{OUTPUT_DIR.relative_to(ROOT)}/`")
    if cook:
        st.info("Cooking — typically 5–8 minutes per episode.")


# Session state for background job
if "log_q" not in st.session_state:
    st.session_state.log_q = Queue()
    st.session_state.result_q = Queue()
    st.session_state.worker = None
    st.session_state.events = []
    st.session_state.last_result = None
    st.session_state.continuation_from = None
    st.session_state.trigger_cook = False

# Allow a Next-Episode click to fire a cook on the next rerun
trigger_continuation = st.session_state.pop("trigger_cook", False) if \
    st.session_state.get("trigger_cook") else False
continuation_path = None
if trigger_continuation and st.session_state.get("continuation_from"):
    continuation_path = Path(st.session_state.continuation_from)
    st.session_state.continuation_from = None

if (cook or trigger_continuation) and (
    st.session_state.worker is None or not st.session_state.worker.is_alive()
):
    st.session_state.events = []
    st.session_state.last_result = None
    ep_num = next_episode_number(
        scope=continuation_path.parent if continuation_path is not None else None
    )
    if continuation_path is not None:
        st.info(f"Continuing the thread from `{continuation_path.name}` → episode {ep_num:02d}")
    t = threading.Thread(
        target=_cook,
        args=(premise, list(selected_cast), ep_num,
              st.session_state.log_q, st.session_state.result_q,
              continuation_path),
        daemon=True,
    )
    t.start()
    st.session_state.worker = t

# Drain queues
try:
    while True:
        kind, payload = st.session_state.log_q.get_nowait()
        st.session_state.events.append((kind, payload))
except Empty:
    pass

try:
    while True:
        st.session_state.last_result = st.session_state.result_q.get_nowait()
except Empty:
    pass


# Render progress
if st.session_state.events:
    st.subheader("Progress")
    for kind, payload in st.session_state.events:
        if kind == "status":
            st.write(f"▸ {payload}")
        elif kind == "plan":
            with st.expander("Episode plan", expanded=False):
                st.write(f"**{payload.title}**")
                st.caption(payload.logline)
                for i, sc in enumerate(payload.scenes, 1):
                    st.markdown(
                        f"**Act {sc['act']} · Scene {i}** — {sc['location']}  "
                        f"\n*{sc['time']}* — {sc['situation']}"
                    )
        elif kind == "scene":
            st.write(
                f"  ✓ Act {payload['act']} · Scene {payload['scene']} — "
                f"{payload['location'][:60]}  "
                f"({payload['dlg']} dialogue / {payload['narr']} narration)"
            )

if st.session_state.last_result:
    r = st.session_state.last_result
    if r["status"] == "done":
        st.success(f"Cooked: **{r['title']}** — {r['words']} words → `{Path(r['path']).name}`")
        with st.expander("Preview", expanded=True):
            st.text_area("Episode text", r["prose"], height=420)
        st.download_button(
            "Download .txt",
            data=r["prose"],
            file_name=Path(r["path"]).name,
            mime="text/plain",
        )
    elif r["status"] == "error":
        st.error(r["error"])
        with st.expander("Traceback"):
            st.code(r["trace"])

# Live refresh while a job is running
if st.session_state.worker and st.session_state.worker.is_alive():
    time.sleep(2)
    st.rerun()

"""
Grizzly Knights — Chronicle (persistent world state)

A pragmatic knowledge graph stored as JSON. Tracks:
  • Per-character state: location, current arc, recent significant events,
    standing physical/emotional condition, what they're carrying from
    previous episodes.
  • Relationship matrix: pairwise state (warm / tense / fucking / not-speaking /
    owe-favor / blood-debt / etc.) updated as episodes happen.
  • Episode log: ordered list of {number, title, logline, beats, deltas} so
    new episodes can reference prior ones causally.

After each episode is generated, a ChronicleKeeper agent reads the prose
and returns a JSON patch describing what changed. The patch is merged into
chronicle.json. ShowRunner reads relevant slices of chronicle.json when
planning the next episode so the universe genuinely evolves.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

from agency_swarm import Agent, Agency

from engine.agency_engine import build_model


ROOT             = Path(__file__).parent.parent
CHRONICLE_PATH   = ROOT / "universe" / "chronicle.json"
EPISODES_DIR     = ROOT / "episodes_text"


# ─── Schema ──────────────────────────────────────────────────────────────────

EMPTY_CHRONICLE: dict[str, Any] = {
    "characters":    {},   # key → {state, arc, recent_events:[...]}
    "relationships": {},   # "a__b" (sorted) → {status, notes, last_touched_episode}
    "episodes":      [],   # [{number, title, logline, cast, beats:[...], deltas:{...}}]
    "world_facts":   [],   # [{fact, established_in_ep, type}]
    "version":       1,
}


def _fresh_empty_chronicle() -> dict[str, Any]:
    return json.loads(json.dumps(EMPTY_CHRONICLE))  # deep copy


def _normalize_chronicle(data: Any) -> tuple[dict[str, Any], list[str]]:
    """Coerce arbitrary parsed JSON into a schema-correct chronicle.

    Returns (chronicle, repaired_keys). repaired_keys names the top-level
    keys that had to be coerced (missing or wrong-type).
    """
    repaired: list[str] = []
    if not isinstance(data, dict):
        repaired.append("<root: not a dict>")
        return _fresh_empty_chronicle(), repaired

    out: dict[str, Any] = {}

    if not isinstance(data.get("characters"), dict):
        if "characters" in data:
            repaired.append("characters")
        else:
            repaired.append("characters (missing)")
        out["characters"] = {}
    else:
        out["characters"] = data["characters"]

    if not isinstance(data.get("relationships"), dict):
        if "relationships" in data:
            repaired.append("relationships")
        else:
            repaired.append("relationships (missing)")
        out["relationships"] = {}
    else:
        out["relationships"] = data["relationships"]

    if not isinstance(data.get("episodes"), list):
        if "episodes" in data:
            repaired.append("episodes")
        else:
            repaired.append("episodes (missing)")
        out["episodes"] = []
    else:
        out["episodes"] = data["episodes"]

    if not isinstance(data.get("world_facts"), list):
        if "world_facts" in data:
            repaired.append("world_facts")
        else:
            repaired.append("world_facts (missing)")
        out["world_facts"] = []
    else:
        out["world_facts"] = data["world_facts"]

    out["version"] = data.get("version", 1)
    return out, repaired


def recover_chronicle(backup_path: Path | None = None) -> Path | None:
    """Snapshot the current chronicle.json to a timestamped .bak file.

    Used before overwriting on a load-repair event so the corrupt original
    is preserved for forensics. Returns the path of the backup written, or
    None if there was nothing to back up.
    """
    src = CHRONICLE_PATH
    if not src.exists():
        return None
    ts = time.strftime("%Y%m%d-%H%M%S")
    dst = backup_path if backup_path is not None else src.with_suffix(
        src.suffix + f".bak.{ts}"
    )
    try:
        dst.write_bytes(src.read_bytes())
        logger.warning("chronicle: snapshotted corrupt file to %s", dst)
        return dst
    except OSError as e:
        logger.warning("chronicle: failed to snapshot to %s: %s", dst, e)
        return None


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


def save_chronicle(data: dict[str, Any]) -> None:
    CHRONICLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = CHRONICLE_PATH.with_suffix(CHRONICLE_PATH.suffix + ".tmp")
    payload = json.dumps(data, indent=2, ensure_ascii=False)
    # Atomic write: write to .tmp, fsync, then os.replace into place.
    # No partial write survives a crash mid-save — either the old file is
    # intact, or the new one is fully on disk.
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(payload)
        f.flush()
        try:
            os.fsync(f.fileno())
        except OSError:
            pass
    os.replace(tmp, CHRONICLE_PATH)


def _rel_key(a: str, b: str) -> str:
    return "__".join(sorted([a, b]))


# ─── Context retrieval for ShowRunner / scene briefs ─────────────────────────

def character_context(key: str, chron: Optional[dict] = None) -> str:
    """Return a short prose summary of where this character currently stands."""
    chron = chron or load_chronicle()
    ch = chron["characters"].get(key)
    if not ch:
        return ""
    lines = []
    if ch.get("state"):
        lines.append(f"State: {ch['state']}")
    if ch.get("arc"):
        lines.append(f"Current arc: {ch['arc']}")
    recent = ch.get("recent_events") or []
    if recent:
        lines.append("Recent events:")
        for ev in recent[-4:]:
            lines.append(f"  - {ev}")
    return "\n".join(lines)


def relationship_context(cast: list[str], chron: Optional[dict] = None) -> str:
    """Return relationship notes for every pairwise edge in the cast."""
    chron = chron or load_chronicle()
    lines = []
    for i, a in enumerate(cast):
        for b in cast[i+1:]:
            r = chron["relationships"].get(_rel_key(a, b))
            if not r:
                continue
            status = r.get("status", "")
            notes = r.get("notes", "")
            lines.append(f"{a} ↔ {b}: {status}. {notes}".rstrip("."))
    return "\n".join(lines)


def world_facts_context(chron: Optional[dict] = None, limit: int = 12) -> str:
    chron = chron or load_chronicle()
    facts = (chron.get("world_facts") or [])[-limit:]
    return "\n".join(f"- {f['fact']}" for f in facts)


def episode_log_context(chron: Optional[dict] = None, limit: int = 8) -> str:
    chron = chron or load_chronicle()
    eps = (chron.get("episodes") or [])[-limit:]
    out = []
    for e in eps:
        out.append(
            f"  #{e['number']:02d} — {e['title']}: {e.get('logline','')} "
            f"(cast: {', '.join(e.get('cast') or [])})"
        )
    return "\n".join(out)


def full_planner_context(cast: Optional[list[str]] = None) -> str:
    """Assemble the universe-state block injected into ShowRunner planning."""
    chron = load_chronicle()
    parts = []

    eps = episode_log_context(chron)
    if eps:
        parts.append("PRIOR EPISODES (most recent last):\n" + eps)

    facts = world_facts_context(chron)
    if facts:
        parts.append("ESTABLISHED WORLD FACTS (canon for THIS universe):\n" + facts)

    if cast:
        for key in cast:
            ctx = character_context(key, chron)
            if ctx:
                parts.append(f"CHARACTER STATE — {key}:\n{ctx}")
        rels = relationship_context(cast, chron)
        if rels:
            parts.append("RELATIONSHIPS IN CAST:\n" + rels)

    return "\n\n".join(parts)


# ─── ChronicleKeeper agent: read episode → emit JSON delta ───────────────────

CHRONICLER_INSTRUCTIONS = """\
You are the ChronicleKeeper for Grizzly Knights — the archivist who reads
each finished episode and updates the persistent world state.

You will receive:
1. The current chronicle.json (truncated to the slices that matter).
2. The full prose text of a newly-generated episode.

You return ONLY a JSON object describing what to change. Format:

{
  "characters": {
    "character_key": {
      "state":  "1-2 sentence current physical/emotional state",
      "arc":    "1-2 sentence current ongoing arc",
      "add_events": ["specific event from THIS episode", "..."]
    }
  },
  "relationships": {
    "key_a__key_b": {
      "status": "warm | tense | hostile | fucking | not_speaking | owe_favor | blood_debt | reconciling | newly_close | etc",
      "notes":  "1-2 sentence WHY, citing the episode beat"
    }
  },
  "world_facts": [
    "Concrete in-universe fact established this episode (Skinny Dennis is the regular bar; Jess quit smoking three months ago; Wade owes Felicia $400; etc)"
  ],
  "episode_summary": {
    "logline": "One-sentence framing of what this episode actually was",
    "beats":   ["3-6 bullet beats that materially happened"]
  }
}

RULES:
- Only include keys for things that ACTUALLY CHANGED or were ACTUALLY NAMED
  in this episode. No filler. No speculation. If nothing changed for a
  character, omit them entirely.
- Use the exact character keys from the chronicle (e.g. "wade_wilson",
  not "Wade"). Relationship keys are the two character keys joined with
  "__" in alphabetical order.
- "add_events" entries are appended to the character's running history,
  so write them as standalone sentences ("Got drunk with Felicia at
  Skinny Dennis and admitted he's been calling Peter's voicemail.").
- Be specific. Name drinks, locations, props, lines crossed.
- No moralizing. No therapy language. You are an archivist, not a critic.

Return ONLY the JSON object. No prose. No code fence.
"""


def _build_chronicler(model):
    return Agency(Agent(
        name="ChronicleKeeper",
        instructions=CHRONICLER_INSTRUCTIONS,
        model=model,
    ))


async def _ingest_async(episode_path: Path, plan_meta: dict, model) -> dict:
    chron = load_chronicle()
    cast = plan_meta.get("cast") or []

    # Build the prior-state slice we'll show the chronicler
    prior_slice = {
        "characters":    {k: chron["characters"].get(k, {}) for k in cast},
        "relationships": {
            _rel_key(a, b): chron["relationships"].get(_rel_key(a, b), {})
            for i, a in enumerate(cast) for b in cast[i+1:]
        },
        "episodes_tail": (chron.get("episodes") or [])[-3:],
    }

    prose = episode_path.read_text()

    msg = (
        f"PRIOR STATE (only the slice relevant to this episode's cast):\n"
        f"{json.dumps(prior_slice, indent=2, ensure_ascii=False)}\n\n"
        f"EPISODE METADATA:\n"
        f"  number: {plan_meta['number']}\n"
        f"  title:  {plan_meta['title']}\n"
        f"  cast:   {cast}\n\n"
        f"EPISODE PROSE:\n{prose}\n\n"
        f"Return the JSON delta now."
    )

    chronicler = _build_chronicler(model)
    resp = await chronicler.get_response(msg)
    raw = (resp.final_output or "").strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    delta = json.loads(raw)
    return delta


def _episode_beats_from_delta(delta: dict) -> list[str]:
    """Recover episode-level beats from concrete character/relationship
    changes when the live chronicler omits episode_summary.beats."""
    beats: list[str] = []
    for patch in (delta.get("characters") or {}).values():
        if not isinstance(patch, dict):
            continue
        for ev in patch.get("add_events") or []:
            ev_s = str(ev).strip()
            if ev_s:
                beats.append(ev_s)
            if len(beats) >= 6:
                return beats
    for patch in (delta.get("relationships") or {}).values():
        if not isinstance(patch, dict):
            continue
        note = str(patch.get("notes") or "").strip()
        if note:
            beats.append(note)
        if len(beats) >= 6:
            break
    return beats


def apply_delta(chron: dict, delta: dict, plan_meta: dict) -> dict:
    # Character updates
    for key, patch in (delta.get("characters") or {}).items():
        ch = chron["characters"].setdefault(key, {"recent_events": []})
        if patch.get("state"):
            ch["state"] = patch["state"]
        if patch.get("arc"):
            ch["arc"] = patch["arc"]
        for ev in patch.get("add_events") or []:
            ch.setdefault("recent_events", []).append(
                f"[ep {plan_meta['number']:02d}] {ev}"
            )
        # cap history at 25 entries
        ch["recent_events"] = ch.get("recent_events", [])[-25:]

    # Relationship updates
    for rk, patch in (delta.get("relationships") or {}).items():
        rel = chron["relationships"].setdefault(rk, {})
        if patch.get("status"):
            rel["status"] = patch["status"]
        if patch.get("notes"):
            rel["notes"] = patch["notes"]
        rel["last_touched_episode"] = plan_meta["number"]

    # World facts
    for fact in delta.get("world_facts") or []:
        chron.setdefault("world_facts", []).append({
            "fact": fact,
            "established_in_ep": plan_meta["number"],
        })

    # Episode entry
    ep_summary = delta.get("episode_summary") or {}
    beats = ep_summary.get("beats") or _episode_beats_from_delta(delta)
    chron.setdefault("episodes", []).append({
        "number":  plan_meta["number"],
        "title":   plan_meta["title"],
        "cast":    plan_meta.get("cast") or [],
        "logline": ep_summary.get("logline", plan_meta.get("logline", "")),
        "beats":   beats,
    })

    return chron


def ingest_episode(episode_path: Path, plan_meta: dict,
                   model_name: str = "gpt-4o") -> dict:
    """Read an episode file, generate a delta, merge into chronicle.json."""
    model = build_model(model_name)
    delta = asyncio.run(_ingest_async(episode_path, plan_meta, model))
    chron = load_chronicle()
    chron = apply_delta(chron, delta, plan_meta)
    save_chronicle(chron)
    return delta


if __name__ == "__main__":
    # quick smoke test of context block
    print("=== Chronicle planner context ===")
    print(full_planner_context(["wade_wilson", "felicia_hardy"]))

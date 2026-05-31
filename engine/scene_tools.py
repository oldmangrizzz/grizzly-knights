"""
Per-scene mutable stage state + character-callable tools.

Function-calling proved live against the Copilot endpoint
(see _fleet_status/decision.md). Each character agent gets its own
subclassed instances of these tools, with scene_id + actor_key baked in
by closure, so the tool's `run()` knows which scene to mutate and who
the caller is.

Tools:
  • BringInCharacter(character_key, how_they_arrive) — queue an arrival
  • AddressCharacter(character_key)                  — request next-speaker handoff
  • TakeAction(action [, consequence])               — log a physical beat + tracker bump
  • ChangeSetting(new_location, what_happens)        — move the scene

Stage state per scene:
  • present_cast        — keys currently on stage
  • available_roster    — keys eligible to be brought in
  • pending_arrivals    — queued bring_in events for Uatu to narrate
  • pending_addresses   — direct speaker handoffs
  • pending_actions     — logged physical actions
  • pending_settings    — queued setting changes
  • tracker             — { drinks, lines_crossed, decisions_made,
                            arrivals, settings_changed, actions,
                            actions_budget_exhausted }
  • chronicle           — durable list of (turn, actor, kind, payload)
                          including any take_action with `consequence`
  • turns_taken         — incremented by the runner
  • action_budget       — per-scene hard cap on TakeAction calls

Adversarial hardening (APT-03 / APT-04):
  • BringInCharacter dedups against present_cast AND pending_arrivals;
    duplicate calls return "ALREADY ARRIVING/PRESENT: <key>" without
    mutating chronicle or tracker.
  • Free-text args (how_they_arrive, message, action, consequence,
    new_location, what_happens) are capped at MAX_ARG_LEN (2000 chars)
    via pydantic Field max_length. Oversize input raises ValidationError
    at construction; the engine never silently truncates.
  • TakeAction is bounded by Stage.action_budget (default
    DEFAULT_ACTION_BUDGET = 50). When exhausted, the tool returns
    "ERROR: scene action budget exhausted" and sets
    tracker["actions_budget_exhausted"] = True.

Null-byte and Unicode bidi-override handling:
  The chronicle stores raw user/agent input verbatim — including \\x00
  and the bidi overrides (U+202A..U+202E, U+2066..U+2069). This is a
  deliberate choice: json.dumps round-trips them safely, and we don't
  want to silently mutate stored state. However, terminals and other
  display surfaces are vulnerable to bidi-override spoofing and to
  null-byte truncation. Callers emitting chronicle data to a transcript,
  log, or UI MUST run it through `sanitize_for_display()`, which strips
  NULs and replaces bidi overrides with the Unicode replacement char.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
import re
import uuid

from pydantic import Field


# ─── Limits / display sanitization ───────────────────────────────────────────

MAX_ARG_LEN: int = 2000
DEFAULT_ACTION_BUDGET: int = 50

# U+202A..U+202E: LRE, RLE, PDF, LRO, RLO
# U+2066..U+2069: LRI, RLI, FSI, PDI
_BIDI_RE = re.compile(r"[\u202A-\u202E\u2066-\u2069]")


def sanitize_for_display(text: Any) -> Any:
    """Strip NUL bytes and neutralize Unicode bidi-override characters.

    Use this when emitting chronicle / tracker / tool-output strings to a
    transcript, terminal, log file, or any other display surface. The
    chronicle itself is left untouched so state round-trips faithfully
    through json.dumps; this is the display-time-only safety net.
    """
    if not isinstance(text, str):
        return text
    return _BIDI_RE.sub("\ufffd", text.replace("\x00", ""))

try:
    from agency_swarm.tools import BaseTool
except Exception:  # pragma: no cover
    from agency_swarm import BaseTool  # type: ignore


# ─── Stage registry ──────────────────────────────────────────────────────────

_STAGES: dict[str, "Stage"] = {}


def _empty_tracker() -> dict:
    return {
        "drinks":           0,
        "lines_crossed":    0,
        "decisions_made":   0,
        "arrivals":         0,
        "settings_changed": 0,
        "actions":          0,
        "actions_budget_exhausted": False,
    }


@dataclass
class Stage:
    scene_id:           str
    present_cast:       list[str]              = field(default_factory=list)
    pending_arrivals:   list[dict]             = field(default_factory=list)
    pending_addresses:  list[str]              = field(default_factory=list)
    pending_actions:    list[dict]             = field(default_factory=list)
    pending_settings:   list[dict]             = field(default_factory=list)
    available_roster:   list[str]              = field(default_factory=list)
    tracker:            dict[str, Any]         = field(default_factory=_empty_tracker)
    chronicle:          list[dict]             = field(default_factory=list)
    turns_taken:        int                    = 0
    action_budget:      int                    = DEFAULT_ACTION_BUDGET

    def reset_pending(self) -> None:
        self.pending_arrivals.clear()
        self.pending_addresses.clear()
        self.pending_actions.clear()
        self.pending_settings.clear()

    def is_stagnant(self) -> bool:
        numeric = [v for k, v in self.tracker.items()
                   if isinstance(v, int) and not isinstance(v, bool)]
        return all(v == 0 for v in numeric)


def register_stage(present: list[str], roster: list[str],
                   action_budget: int = DEFAULT_ACTION_BUDGET) -> str:
    sid = uuid.uuid4().hex
    _STAGES[sid] = Stage(
        scene_id=sid,
        present_cast=list(present),
        available_roster=list(roster),
        action_budget=int(action_budget),
    )
    return sid


def get_stage(sid: str) -> Stage:
    return _STAGES[sid]


def drop_stage(sid: str) -> None:
    _STAGES.pop(sid, None)


# ─── Tracker heuristics ──────────────────────────────────────────────────────

_DRINK_RE = re.compile(
    r"\b(drink|sip|chug|down|pour|order|round|shot|swallow|gulp|refill|whisk|"
    r"tequila|vodka|gin|bourbon|wine|beer|coors|margarita|martini|cocktail|"
    r"glass|bottle|tumbler|edible|adderall|coke|line|joint|cigarette|"
    r"light(?:ed|s)?\s+(?:a\s+)?(?:smoke|cig))\b",
    re.I,
)
_LINE_RE = re.compile(
    r"\b(kiss|fuck|fucked|grope|grab|grabs|cock|tits|thigh|lap|undress|"
    r"strip|hookup|hook\s*up|punch|hit|slap|hits|slaps|shove|"
    r"throw|threw|throws|storm\s+out|walk\s+out|breakdown|break\s+down|"
    r"confess|admit|admits|cry|sob|sobbing|pull(?:s|ed)?\s+a\s+gun|"
    r"draw(?:s|n)?\s+(?:a\s+)?(?:knife|blade|gun))\b",
    re.I,
)
_DECISION_RE = re.compile(
    r"\b(decide|decided|deal|agreed|agree|we'?re\s+(?:going|leaving|doing)|"
    r"let'?s\s+(?:go|leave|do|get)|i'?m\s+(?:going|leaving|done|out)|"
    r"i'?ll\s+(?:do|take|call|pay)|fine,?\s+i'?ll|alright,?\s+i'?ll|"
    r"promise|swear|commit|vow)\b",
    re.I,
)


def _classify(text: str) -> list[str]:
    """Tag a physical action string with which tracker fields move."""
    hits = []
    if _DRINK_RE.search(text):    hits.append("drinks")
    if _LINE_RE.search(text):     hits.append("lines_crossed")
    if _DECISION_RE.search(text): hits.append("decisions_made")
    return hits


# ─── Per-character tool factory ──────────────────────────────────────────────

def make_scene_tools(scene_id: str, actor_key: str) -> list[type]:
    """
    Build BaseTool subclasses with scene_id + actor_key baked in by closure.
    Returns a list ready to drop into Agent(tools=[...]).
    """
    sid = scene_id
    actor = actor_key

    class BringInCharacter(BaseTool):
        """Invite another character on stage. They will arrive at the start of
        the next turn cycle and begin participating. Use this when your
        character is texting, calling, or otherwise summoning someone to
        join the scene. Provide the character_key (lowercase_with_underscores
        name as listed in the roster) and a one-sentence description of HOW
        they arrive (texted, called, was already in the building, walks in
        from the parking lot, etc)."""
        character_key:    str = Field(..., description="lowercase_with_underscores key")
        how_they_arrive:  str = Field(..., max_length=MAX_ARG_LEN,
                                       description="one sentence describing how they arrive")

        def run(self) -> str:
            stage = _STAGES.get(sid)
            if stage is None:
                return "ERROR: no active scene"
            key = self.character_key.strip().lower()
            if key in stage.present_cast:
                return f"ALREADY ARRIVING/PRESENT: {key}"
            if any(p.get("key") == key for p in stage.pending_arrivals):
                return f"ALREADY ARRIVING/PRESENT: {key}"
            if key not in stage.available_roster:
                return f"ERROR: '{key}' is not in the roster."
            stage.pending_arrivals.append({
                "key": key, "how": self.how_they_arrive, "by": actor,
            })
            stage.tracker["arrivals"] += 1
            stage.chronicle.append({
                "turn": stage.turns_taken, "actor": actor,
                "kind": "bring_in", "key": key, "how": self.how_they_arrive,
            })
            return f"Queued: {key} will arrive next ({self.how_they_arrive})."

    class AddressCharacter(BaseTool):
        """Hand the next turn directly to a specific character on stage. Use this
        when your line is pointed at someone in particular and you want them
        to respond next instead of round-robin rotation. The character must
        already be on stage."""
        character_key: str = Field(..., description="lowercase_with_underscores key of who speaks next")

        def run(self) -> str:
            stage = _STAGES.get(sid)
            if stage is None:
                return "ERROR: no active scene"
            key = self.character_key.strip().lower()
            if key not in stage.present_cast:
                return f"ERROR: '{key}' is not on stage."
            stage.pending_addresses.append(key)
            stage.chronicle.append({
                "turn": stage.turns_taken, "actor": actor,
                "kind": "address", "key": key,
            })
            return f"Next turn: {key}."

    class TakeAction(BaseTool):
        """Perform a physical action in the scene. Use this for things you DO,
        not things you say — grabbing a drink, walking over to the bar,
        putting a hand on someone's thigh, lighting a cigarette, kissing
        someone, walking out, throwing a glass. The narrator will describe
        the action and it becomes part of the scene's reality. Be specific.

        OPTIONAL `consequence`: if the action commits a beat that the scene
        should remember (a confession landed, a decision made, a line
        crossed, somebody left), state it in one sentence. That commits the
        beat to the chronicle and prevents the scene from drifting back to
        quip-trading."""
        action: str = Field(..., max_length=MAX_ARG_LEN,
                            description="one sentence describing what your character physically does")
        consequence: str = Field(
            default="",
            max_length=MAX_ARG_LEN,
            description="optional — one sentence naming the durable beat this commits"
        )
        resolves_pressure: str = Field(
            default="",
            max_length=MAX_ARG_LEN,
            description=("optional — the snake_case name of the episode-level "
                         "forcing pressure that this action MOVES (e.g. "
                         "'peter_decision'). When set, the engine treats this "
                         "action as explicit progress on that pressure without "
                         "needing to substring-match evidence patterns. Use this "
                         "when your action is an on-stage REFUSAL ('we are not "
                         "calling him, period') or a committed choice that "
                         "names the pressure by its substance."),
        )

        def run(self) -> str:
            stage = _STAGES.get(sid)
            if stage is None:
                return "ERROR: no active scene"
            if stage.tracker.get("actions", 0) >= stage.action_budget:
                stage.tracker["actions_budget_exhausted"] = True
                return "ERROR: scene action budget exhausted"
            tags = _classify(self.action + " " + self.consequence)
            stage.pending_actions.append({
                "actor": actor, "action": self.action,
                "consequence": self.consequence, "tags": tags,
                "resolves_pressure": self.resolves_pressure,
            })
            stage.tracker["actions"] += 1
            for t in tags:
                stage.tracker[t] += 1
            stage.chronicle.append({
                "turn": stage.turns_taken, "actor": actor,
                "kind": "action", "action": self.action,
                "consequence": self.consequence, "tags": tags,
                "resolves_pressure": self.resolves_pressure,
            })
            extra = ""
            if self.consequence:
                extra += f" | consequence committed: {self.consequence}"
            if self.resolves_pressure:
                extra += f" | resolves_pressure: {self.resolves_pressure}"
            return f"Action staged: {self.action}{extra}"

    class ChangeSetting(BaseTool):
        """Move the scene to a new location or shift the situation
        significantly. Use this when your character is leading the group
        somewhere new (the parking lot, the kitchen, Johnny's loft, the
        rooftop, the cab home). The narrator will describe the transition."""
        new_location: str = Field(..., max_length=MAX_ARG_LEN, description="the new location/setting")
        what_happens: str = Field(..., max_length=MAX_ARG_LEN,
                                   description="one sentence describing how the scene moves")

        def run(self) -> str:
            stage = _STAGES.get(sid)
            if stage is None:
                return "ERROR: no active scene"
            stage.pending_settings.append({
                "location": self.new_location,
                "transition": self.what_happens,
                "by": actor,
            })
            stage.tracker["settings_changed"] += 1
            stage.chronicle.append({
                "turn": stage.turns_taken, "actor": actor,
                "kind": "change_setting",
                "location": self.new_location,
                "transition": self.what_happens,
            })
            return f"Setting change queued: {self.new_location}"

    # Give each subclass a stable, predictable name so the SDK uses it
    # verbatim as the function name presented to the model.
    BringInCharacter.__name__   = "BringInCharacter"
    AddressCharacter.__name__   = "AddressCharacter"
    TakeAction.__name__         = "TakeAction"
    ChangeSetting.__name__      = "ChangeSetting"

    return [BringInCharacter, AddressCharacter, TakeAction, ChangeSetting]


# ─── Back-compat module-level classes (text-protocol fallback shim) ──────────
#
# These keep older imports of `from engine.scene_tools import CHARACTER_TOOLS`
# working as no-op tools. Real scene tools are created per-character via
# make_scene_tools(). The fallback is also the home for parse_and_dispatch,
# which is NOT used in the function-calling path but is kept available so
# downstream code can degrade gracefully if a future endpoint loses
# function-calling support.

class _NoopBringIn(BaseTool):
    """(deprecated module-level stub — use make_scene_tools)"""
    character_key:   str = Field(..., description="character key")
    how_they_arrive: str = Field(..., description="how they arrive")
    def run(self) -> str: return "ERROR: tool not bound to a scene"

class _NoopAddress(BaseTool):
    """(deprecated module-level stub — use make_scene_tools)"""
    character_key: str = Field(..., description="character key")
    def run(self) -> str: return "ERROR: tool not bound to a scene"

class _NoopAction(BaseTool):
    """(deprecated module-level stub — use make_scene_tools)"""
    action:      str = Field(..., description="action")
    consequence: str = Field(default="", description="optional consequence")
    resolves_pressure: str = Field(default="", description="optional pressure id")
    def run(self) -> str: return "ERROR: tool not bound to a scene"

class _NoopSetting(BaseTool):
    """(deprecated module-level stub — use make_scene_tools)"""
    new_location: str = Field(..., description="new location")
    what_happens: str = Field(..., description="how the scene moves")
    def run(self) -> str: return "ERROR: tool not bound to a scene"


CHARACTER_TOOLS = [_NoopBringIn, _NoopAddress, _NoopAction, _NoopSetting]


# ─── Text-protocol fallback (UNUSED on this endpoint) ────────────────────────

_PROTO_RE = re.compile(
    r"<<TOOL:(?P<name>[A-Za-z_]+)>>\s*(?P<args>\{.*?\})\s*<<END>>",
    re.DOTALL,
)

def parse_and_dispatch(reply: str, scene_id: str, actor_key: str
                       ) -> tuple[str, list[dict]]:
    """
    Parse <<TOOL:Name>>{json}<<END>> markers out of a reply string and
    dispatch each to the right scene tool. Returns the cleaned reply
    (markers stripped) and a list of tool result dicts.

    NOT used by the live engine — function-calling on the Copilot endpoint
    proved live (see _fleet_status/decision.md). Provided as a safety net.
    """
    import json as _json
    results: list[dict] = []
    tools = {t.__name__: t for t in make_scene_tools(scene_id, actor_key)}
    cleaned = reply
    for m in _PROTO_RE.finditer(reply):
        name = m.group("name")
        try:
            args = _json.loads(m.group("args"))
        except _json.JSONDecodeError as e:
            results.append({"tool": name, "error": f"bad json: {e}"})
            continue
        ToolCls = tools.get(name)
        if ToolCls is None:
            results.append({"tool": name, "error": "unknown tool"})
            continue
        try:
            tool = ToolCls(**args)
            out = tool.run()
            results.append({"tool": name, "args": args, "output": out})
        except Exception as e:  # pragma: no cover
            results.append({"tool": name, "args": args, "error": str(e)})
    cleaned = _PROTO_RE.sub("", reply).strip()
    return cleaned, results

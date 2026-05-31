"""
Grizzly Knights — ShowRunner agent

Takes either nothing, a logline, or a logline + cast, and returns a
structured episode plan (10 scenes with location/time/situation continuity).
The plan is then handed to the existing agency_engine to be performed by
the character agents.
"""

import asyncio
import json
import random
import re
import subprocess
from pathlib import Path
from typing import Optional

import yaml
from agency_swarm import Agent, Agency
from agents import OpenAIChatCompletionsModel, AsyncOpenAI

from engine.agency_engine import EpisodePlan, build_model


ROOT           = Path(__file__).parent.parent
CHARACTERS_DIR = ROOT / "universe" / "characters"


def list_available_characters() -> list[str]:
    return sorted(p.stem for p in CHARACTERS_DIR.glob("*.yaml"))


def _character_one_liner(key: str) -> str:
    path = CHARACTERS_DIR / f"{key}.yaml"
    if not path.exists():
        return key
    prof = yaml.safe_load(path.read_text())
    if not isinstance(prof, dict) or not prof:   # file exists but is empty/0-byte -> parses to None
        return key
    name = prof.get("name", key)
    alias = prof.get("alias", "")
    diag = prof.get("primary_diagnoses_analog") or []
    first = diag[0] if diag else ""
    if isinstance(first, dict):
        # YAML accidentally parsed "Label: detail" as a mapping — recover the label
        first = next(iter(first.keys()), "")
    short = str(first).split(":")[0]
    short = re.sub(r"\s*\(.*?\)", "", short).strip()
    return f"{name} ({alias}): {short}" if short else f"{name} ({alias})" if alias else name


SHOWRUNNER_INSTRUCTIONS = """\
You are the ShowRunner for Grizzly Knights — a Marvel-Knights-darker audio
drama universe where characters use real compensatory mechanisms
(substances, sex, gallows humor, violence-as-regulation) the way people in
high-stakes professions (EMS, fire, PD, military, mercenary) actually do.
No corporate sanitization. Characters are people first; jobs are
incidental.

CALIBRATION: This is Netflix-era Marvel (Daredevil/Jessica Jones/Punisher
S1/Defenders alley) plus Marvel Knights / MAX / Bendis Alias / Slott
Spider-Man / Spencer Deadpool / Aaron Punisher MAX / Hickman. NOT
Disney+. NOT a CW pilot. The premise of an episode can be: a hookup
unraveling. Day-after-coke regret. An ugly fight about who slept with
whose ex. Someone showing up bleeding. Someone showing up high. A wake
with the wrong people in attendance. A booth conversation where the
real subject is "are we going to fuck tonight, yes or no." Plan
episodes accordingly — not every show is a brunch.

You receive an optional premise and an optional cast list. Your job is to
return a JSON episode plan with EXACTLY this shape, no markdown fence, no
prose around it:

{
  "title": "Short evocative title (3-6 words)",
  "logline": "One sentence framing the episode.",
  "cast": ["character_key_1", "character_key_2", ...],
  "scenes": [
    {"act": 1, "location": "specific named place", "time": "Day, HH:MM AM/PM", "situation": "2-4 sentences describing where they are, what just happened, and what the scene is about. Be specific. Name drinks, props, prior beats."},
    ... 10 scenes total ...
  ]
}

Rules:
• 10 scenes. Act distribution: 3 / 4 / 3 (setup / complication / aftermath).
• DRAMATIC ARC — NON-NEGOTIABLE. The scenes must build in this exact order:
    - Scenes 1-3 (Act 1, SETUP): establish who is in the room, what they're
      drinking, the mundane premise. Quiet. No big reveals. The audience
      meets the energy. The actual conflict has not surfaced yet — it's a
      hairline crack in scene 2 or 3.
    - Scenes 4-7 (Act 2, COMPLICATION): the crack widens. Something is
      said that can't be unsaid. The drinks get heavier. The conversation
      goes somewhere uncomfortable. By scene 7 it's at its messiest —
      the loudest argument, the most honest confession, the line crossed.
    - Scenes 8-10 (Act 3, AFTERMATH): the air after. Quieter again, but
      different than scenes 1-3 — heavier, more honest, hungover-coded
      even if it's still the same night. Scene 10 is the come-down: who
      stays, who leaves, what's been changed and what hasn't.
  Do NOT write a scene 1 that opens with a fight already in progress. Do
  NOT put the big confession in scene 2. Do NOT put a calm dinner after
  the climax in scene 9. The arc must EARN each beat.
• Times must be monotonically increasing — same evening, same day, or across
  one overnight + next morning at most.
• Locations should change at most THREE times across the 10 scenes. Most
  scenes stay in one location and let time pass naturally — the booth fills,
  empties, the second round arrives, someone steps out for a smoke, somebody
  new walks in, the kitchen closes. The world MOVES around them.
• Each scene's "situation" picks up exactly where the previous scene left
  off. No teleporting. No new characters appearing without a beat for them
  to arrive.
• EVERY CHARACTER IN THE EPISODE CAST IS ALREADY ON STAGE FROM SCENE 1.
  Do NOT write situations like "Wade arrives," "MJ joins them," "Felicia
  walks up to the table." They are already there. The first scene
  establishes the room; every subsequent scene picks up that same room
  with the same people in it, drinks deeper, hour later. Time and
  conversation move. People do not re-enter.
• If a scene DOES require someone new to arrive (a guest character, a
  server, a phone call), say so explicitly in the situation: "Frank shows
  up at the booth halfway through, having driven down from upstate." Be
  specific about who arrives, who leaves, when.
• EACH SCENE'S SITUATION MUST EXPLICITLY REFERENCE THE PREVIOUS SCENE.
  Use phrases like "Picking up from the line about..." or "Three minutes
  after [the previous beat]..." or "The thing X just said is sitting on
  the table." This forces causal continuity. Scenes are not vignettes —
  they are continuous tape.
• The cast list must use the exact character keys from the roster provided.
• 2-4 characters is the sweet spot. Solo episodes allowed if the premise
  demands it. Never more than 5.
• If a premise is provided, honor it. If not, invent one that lets at least
  two of the cast actually talk — no rescue ops, no team missions. This
  universe is about people in rooms.
• Episode runtime target: 60-90 minutes of audio narration. That means
  these 10 scenes need ROOM. Each scene situation should give the agents
  enough material to sustain 15-20 dialogue turns plus narrator beats —
  layered topics, callbacks, somebody trying to change the subject,
  somebody refusing to let them, drinks arriving, drinks finishing,
  somebody's phone buzzing and being ignored. Build slow burns, not
  vignettes.

Return ONLY the JSON object. No preamble. No code fence. No commentary.
"""


def _build_showrunner(model):
    return Agency(Agent(
        name="ShowRunner",
        instructions=SHOWRUNNER_INSTRUCTIONS,
        model=model,
    ))


async def _plan_async(premise: Optional[str], cast: Optional[list[str]],
                      model, episode_number: int) -> EpisodePlan:
    roster_lines = [_character_one_liner(k) for k in list_available_characters()]
    roster = "\n".join(f"  - {k}: {_character_one_liner(k)}"
                       for k in list_available_characters())

    parts = [f"ROSTER (use these exact keys):\n{roster}\n"]
    if cast:
        parts.append(f"REQUIRED CAST (use exactly these keys): {cast}")
    if premise:
        parts.append(f"PREMISE: {premise}")
    else:
        # Seed randomness so repeat clicks vary
        seed_chars = random.sample(list_available_characters(), 3)
        parts.append(
            f"PREMISE: invent one. Consider working with some of these "
            f"characters as a starting point: {seed_chars}. Pick a quiet, "
            f"unspectacular situation — a bar, an apartment, a hospital "
            f"waiting room, a parking lot at 3 AM."
        )
    parts.append("Return only the JSON plan.")

    showrunner = _build_showrunner(model)
    resp = await showrunner.get_response("\n\n".join(parts))
    raw = (resp.final_output or "").strip()

    # Strip code fences if model added them
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    data = json.loads(raw)

    return EpisodePlan(
        number  = episode_number,
        title   = data["title"],
        logline = data["logline"],
        cast    = data["cast"],
        scenes  = data["scenes"],
    )


def plan_episode(premise: Optional[str] = None,
                 cast: Optional[list[str]] = None,
                 episode_number: int = 99,
                 model_name: str = "gpt-4o") -> EpisodePlan:
    model = build_model(model_name)
    return asyncio.run(_plan_async(premise, cast, model, episode_number))

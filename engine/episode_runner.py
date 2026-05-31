"""
Episode runner — orchestrates a full episode from arc selection through scene generation.
Handles act structure, scene direction, previous-scene summaries, and state updates.
"""

import random
from dataclasses import dataclass, field
from typing import Optional

from engine.script_generator import ScriptGenerator, Script
from engine.continuity import ContinuityEngine
from engine.arc_manager import ArcManager


# Location options per act mood
ACT_LOCATIONS = {
    1: [
        ("brooklyn_apartment",    "quiet morning, nothing resolved yet"),
        ("malibu_compound",       "middle of the night, functional"),
        ("queens_apartment",      "end of shift, still in costume"),
        ("hell_kitchen_street",   "overcast, midday, nobody around"),
        ("va_hallway",            "fluorescent, institutional, between appointments"),
        ("baxter_building",       "lab hum, late afternoon"),
        ("diner_morning",         "early, near-empty, coffee going cold"),
        ("cheesecake_factory",    "mid-afternoon, half-empty, nobody they know"),
    ],
    2: [
        ("rooftop",               "cold, wind, city noise below"),
        ("bar_interior",          "not loud enough to need to shout, just loud enough"),
        ("warehouse",             "industrial, isolated, choice of location"),
        ("hospital_corridor",     "waiting-room geography, nobody wants to be here"),
        ("urban_night",           "street level, moving, no fixed point"),
        ("baxter_building",       "tension in the lab, something not working"),
        ("cheesecake_factory",    "drinks going faster than the food, no one is counting"),
    ],
    3: [
        ("brooklyn_apartment",    "later, quieter, unresolved but managed"),
        ("rain_on_glass",         "static location, interior, weather doing the work"),
        ("rooftop",               "after, still up there, not ready to go down"),
        ("hell_kitchen_street",   "walking away, nothing fixed"),
        ("malibu_compound",       "3am, suit powered down, still awake"),
        ("diner_morning",         "next morning, neither of them slept"),
    ],
}

# Universe opener — forced first scene
UNIVERSE_OPENER = {
    "location":    "cheesecake_factory",
    "ambient_tone": "mid-afternoon, half-empty, nobody they know, drinks already in hand",
    "direction":   (
        "This is the first scene of the entire universe. Set the stage. "
        "Felicia Hardy and Wade Wilson are day-drinking at the Cheesecake Factory "
        "on a Wednesday for no particular reason other than neither of them had anything better to do. "
        "No mission. No crisis. No one knows they're friends. "
        "They don't need to explain it. They never have. "
        "Start in the middle of a conversation already happening. "
        "This is the world. This is what it actually looks like."
    ),
}

SCENE_DIRECTIONS = {
    1: [
        "Establish where {chars} are right now. No crisis. Just where they actually are.",
        "One of them is doing something ordinary. The other arrives. Nothing is said about the thing.",
        "A routine task that isn't routine for this person. Show the weight in the mundane.",
        "Morning. Before anything has happened today. That's the scene.",
    ],
    2: [
        "Pressure arrives. Not a villain — just reality. Watch how {chars} handle it in their specific way.",
        "One of them says the wrong thing. Not cruelly. Just wrong. The other absorbs it.",
        "The arc surfaces without anyone naming it. It's in the room. Nobody addresses it directly.",
        "They're trying to help each other. It isn't working. Neither of them stops.",
        "Something from the past enters the present. Nothing is explained. It doesn't need to be.",
    ],
    3: [
        "It doesn't resolve. Something is managed. Something costs something. They separate.",
        "A partial thing. Not fixed. Not broken. Where they actually land.",
        "The conversation ends before it should. That's the real ending.",
        "One of them is okay. By their own definition of okay. Show what that looks like.",
    ],
}


@dataclass
class Episode:
    number:     int
    title:      str
    characters: list[str]
    scenes:     list[Script] = field(default_factory=list)


class EpisodeRunner:

    SCENES_PER_ACT = {1: 2, 2: 3, 3: 2}   # 7 scenes total per episode

    def __init__(self,
                 generator:  ScriptGenerator,
                 continuity: ContinuityEngine,
                 arcs:       ArcManager,
                 config:     dict):
        self.generator  = generator
        self.continuity = continuity
        self.arcs       = arcs
        self.config     = config

        self._active_characters: list[str] = config.get("session", {}).get(
            "active_characters", ["tony_stark", "jessica_jones", "sam_wilson"]
        )
        self._current_episode: Optional[Episode] = None
        self._scene_cursor = 0
        self._previous_summary = "Opening scene."

    # ---------------------------------------------------------------- episode lifecycle

    def start_new_episode(self) -> Episode:
        ep_num = self.arcs.get_episode_count() + 1
        chars  = self._pick_characters()
        title  = self._generate_title(ep_num, chars)
        self._current_episode  = Episode(number=ep_num, title=title, characters=chars)
        self._scene_cursor     = 0
        self._previous_summary = "Opening scene."
        return self._current_episode

    def next_scene_args(self, scene_index: int) -> dict:
        """Return kwargs for ScriptGenerator.generate() for the given scene index."""
        if self._current_episode is None:
            self.start_new_episode()

        ep    = self._current_episode
        act, scene_in_act, total_scenes, scene_number = self._scene_position(scene_index)

        # Universe opener: Episode 1, Scene 1 is always the Cheesecake Factory
        if ep.number == 1 and scene_index == 0:
            opener = UNIVERSE_OPENER
            location, ambient_tone = opener["location"], opener["ambient_tone"]
            direction = opener["direction"]
        else:
            location, ambient_tone = random.choice(ACT_LOCATIONS[act])
            direction_template     = random.choice(SCENE_DIRECTIONS[act])
            chars_str              = " and ".join(
                ep.characters[i].replace("_", " ").title() for i in range(min(2, len(ep.characters)))
            )
            direction = direction_template.format(chars=chars_str)

        return dict(
            episode_number    = ep.number,
            episode_title     = ep.title,
            act               = act,
            scene_number      = scene_number,
            total_scenes      = total_scenes,
            characters        = ep.characters,
            location          = location,
            ambient_tone      = ambient_tone,
            scene_direction   = direction,
            previous_summary  = self._previous_summary,
        )

    def record_scene(self, script: Script):
        """Called after a scene is generated — updates summary and continuity."""
        if self._current_episode:
            self._current_episode.scenes.append(script)
        self._previous_summary = self._summarize(script)
        self._scene_cursor += 1

        # Advance to new episode after all scenes played
        total = sum(self.SCENES_PER_ACT.values())
        if self._scene_cursor >= total:
            self.arcs.increment_episode()
            self.start_new_episode()

    # ---------------------------------------------------------------- internal

    def _scene_position(self, scene_index: int) -> tuple[int, int, int, int]:
        """Returns (act, scene_in_act, total_scenes, global_scene_number)."""
        total   = sum(self.SCENES_PER_ACT.values())
        pos     = scene_index % total
        running = 0
        for act, count in self.SCENES_PER_ACT.items():
            if pos < running + count:
                return act, pos - running, total, pos + 1
            running += count
        return 3, 0, total, total

    def _pick_characters(self) -> list[str]:
        pool = self._active_characters
        # 2-3 characters per episode
        n = random.randint(2, min(3, len(pool)))
        return random.sample(pool, n)

    def _generate_title(self, ep_num: int, chars: list[str]) -> str:
        titles = [
            "Nobody Asked", "Still Here", "Functional", "The Thing About That",
            "Before Anyone Noticed", "Not That Kind of Better", "Managed",
            "What It Costs", "Background Noise", "Fine", "The Long Way",
            "Somewhere to Be", "Not Fixed", "Adjacent to Okay", "The Work",
            "What He Said", "After", "Three Days", "The Quiet Kind",
            "Whatever Gets You Through",
        ]
        return f"{random.choice(titles)}"

    def _summarize(self, script: Script) -> str:
        """Extract a brief summary from the last narrator or dialogue block."""
        for block in reversed(script.blocks):
            if block.type in ("narrator", "dialogue") and len(block.text) > 20:
                return block.text[:120].strip()
        return "Previous scene."

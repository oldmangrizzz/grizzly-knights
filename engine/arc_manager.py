"""
Episodic arc tracking across sessions.
Arcs are multi-episode threads tied to one or more characters.
They evolve, worsen, stabilize, and re-emerge — they do not resolve cleanly.
"""

import json
import random
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional


STATE_FILE = Path(__file__).parent.parent / "state" / "canon_state.json"


@dataclass
class Arc:
    id:           str
    title:        str
    characters:   list[str]
    arc_type:     str          # personal | relational | mission
    description:  str
    status:       str = "active"   # active | dormant | escalating | resolved_partial
    intensity:    int = 1          # 1 (background) – 5 (acute)
    episode_last_featured: int = 0
    notes:        list[str] = field(default_factory=list)


class ArcManager:

    # Arcs that are always running — seeded at startup if absent
    SEED_ARCS = [
        Arc(
            id="tony-sobriety",
            title="The System",
            characters=["tony_stark"],
            arc_type="personal",
            description="Tony's alcohol use oscillates. Right now it's managed. It won't stay that way.",
            intensity=2,
        ),
        Arc(
            id="steve-displacement",
            title="Wrong Century",
            characters=["steve_rogers"],
            arc_type="personal",
            description="Steve's temporal displacement keeps resurfacing in unexpected contexts. He hasn't grieved the lost world.",
            intensity=2,
        ),
        Arc(
            id="frank-mission-end",
            title="What's Underneath",
            characters=["frank_castle"],
            arc_type="personal",
            description="The mission cannot end because ending it means addressing what's underneath. Frank knows this. He keeps going anyway.",
            intensity=3,
        ),
        Arc(
            id="jessica-kilgrave",
            title="Still There",
            characters=["jessica_jones"],
            arc_type="personal",
            description="Kilgrave is never fully gone. Something will surface a trigger. When it does, the alcohol escalates before she notices.",
            intensity=2,
        ),
        Arc(
            id="sam-riley",
            title="His Name Was Riley",
            characters=["sam_wilson"],
            arc_type="personal",
            description="Sam helps everyone. Nobody asks about Riley. The grief is accessible if someone ever pokes it. Nobody does.",
            intensity=2,
        ),
        Arc(
            id="bucky-identity",
            title="Who Without",
            characters=["bucky_barnes"],
            arc_type="personal",
            description="Who is Bucky independent of Steve, of HYDRA, of the arm. The question has no current answer.",
            intensity=3,
        ),
        Arc(
            id="peter-abandonment",
            title="Parker Luck",
            characters=["peter_parker"],
            arc_type="personal",
            description="Every relationship is shaped by the fear that it will end badly. It usually does. Peter makes sure of it.",
            intensity=3,
        ),
        Arc(
            id="reed-ben-guilt",
            title="The Cost of the Calculation",
            characters=["reed_richards", "ben_grimm"],
            arc_type="relational",
            description="Ben has forgiven Reed. Reed has not forgiven Reed. Ben carries Reed's guilt so Reed can function. This has a cost.",
            intensity=3,
        ),
        Arc(
            id="victor-mother",
            title="Cynthia",
            characters=["victor_doom"],
            arc_type="personal",
            description="Victor has never stopped trying to retrieve his mother from Hell. He never will. This is the one thing that bypasses the armor.",
            intensity=4,
        ),
        Arc(
            id="victor-reed-gap",
            title="What He Got to Be",
            characters=["victor_doom", "reed_richards"],
            arc_type="relational",
            description="Victor is jealous not of what Reed has but of what Reed is — completely, without armor. Reed doesn't know this is the thing.",
            intensity=3,
        ),
    ]

    def __init__(self):
        self._state: dict = {}
        self._arcs:  dict[str, Arc] = {}
        self._load()

    # ----------------------------------------------------------------- load/save

    def _load(self):
        if STATE_FILE.exists():
            self._state = json.loads(STATE_FILE.read_text())
        else:
            self._state = {
                "episode_count": 0,
                "completed_episodes": [],
                "arcs": {},
            }

        # Deserialize arcs
        for arc_id, arc_data in self._state.get("arcs", {}).items():
            self._arcs[arc_id] = Arc(**arc_data)

        # Seed built-in arcs if absent
        for arc in self.SEED_ARCS:
            if arc.id not in self._arcs:
                self._arcs[arc.id] = arc
        self._save()

    def _save(self):
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        self._state["arcs"] = {k: asdict(v) for k, v in self._arcs.items()}
        STATE_FILE.write_text(json.dumps(self._state, indent=2))

    # ----------------------------------------------------------------- query

    def get_episode_count(self) -> int:
        return self._state.get("episode_count", 0)

    def increment_episode(self):
        self._state["episode_count"] = self.get_episode_count() + 1
        self._save()

    def select_arcs_for_episode(self,
                                 active_characters: list[str],
                                 max_arcs: int = 3) -> list[Arc]:
        """
        Pick arcs relevant to the active characters.
        Favors high-intensity arcs and those not recently featured.
        Always includes at least one personal arc per active character if available.
        """
        episode = self.get_episode_count()

        eligible = [
            arc for arc in self._arcs.values()
            if arc.status in ("active", "escalating")
            and any(c in active_characters for c in arc.characters)
        ]

        # Score: intensity + recency penalty
        def score(arc: Arc) -> float:
            recency_penalty = max(0, 3 - (episode - arc.episode_last_featured)) * 0.5
            return arc.intensity - recency_penalty + random.uniform(0, 0.5)

        eligible.sort(key=score, reverse=True)
        return eligible[:max_arcs]

    def format_for_prompt(self, characters: list[str]) -> str:
        arcs = self.select_arcs_for_episode(characters)
        if not arcs:
            return "No active arcs — establish character baselines."
        lines = []
        for arc in arcs:
            lines.append(f"**{arc.title}** [{arc.arc_type}, intensity {arc.intensity}/5]")
            lines.append(f"  {arc.description}")
        return "\n".join(lines)

    def update_arc(self, arc_id: str, **kwargs):
        if arc_id in self._arcs:
            for k, v in kwargs.items():
                setattr(self._arcs[arc_id], k, v)
            self._save()

    def add_arc_note(self, arc_id: str, note: str):
        if arc_id in self._arcs:
            self._arcs[arc_id].notes.append(note)
            self._save()

    def create_arc(self, arc: Arc):
        self._arcs[arc.id] = arc
        self._save()

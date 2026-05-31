"""
Persistent character psychological state.
Loads from state/character_states.json, provides current state for prompt injection,
and updates after each scene based on what happened.
"""

import json
from pathlib import Path
from typing import Any


STATE_FILE = Path(__file__).parent.parent / "state" / "character_states.json"


class ContinuityEngine:

    def __init__(self):
        self._states: dict[str, dict] = {}
        self._load()

    def _load(self):
        if STATE_FILE.exists():
            self._states = json.loads(STATE_FILE.read_text())
        else:
            self._states = {}

    def _save(self):
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(self._states, indent=2))

    # ----------------------------------------------------------------- read

    def get_state(self, character_key: str) -> dict:
        return self._states.get(character_key, {})

    def get_all_states(self) -> dict[str, dict]:
        return dict(self._states)

    # ----------------------------------------------------------------- write

    def update(self, character_key: str, updates: dict[str, Any]):
        if character_key not in self._states:
            self._states[character_key] = {}
        self._states[character_key].update(updates)
        self._save()

    def add_recent_event(self, character_key: str, event: str, max_events: int = 10):
        """Append a brief event description. Keeps last max_events entries."""
        if character_key not in self._states:
            self._states[character_key] = {}
        events = self._states[character_key].get("recent_events", [])
        events.append(event)
        self._states[character_key]["recent_events"] = events[-max_events:]
        self._save()

    def apply_scene_outcomes(self, character_key: str, outcomes: dict):
        """
        Called after each scene with a dict of state changes.
        E.g.: {"sobriety_status": "struggling", "recent_events": ["had a drink at the garage"]}
        """
        if "recent_events" in outcomes:
            for event in outcomes.pop("recent_events", []):
                self.add_recent_event(character_key, event)
        self.update(character_key, outcomes)

    def initialize_character(self, character_key: str, defaults: dict):
        """Seed initial state for a character if not already present."""
        if character_key not in self._states:
            self._states[character_key] = defaults
            self._save()

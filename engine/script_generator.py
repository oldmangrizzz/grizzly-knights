"""
Generates audio drama scripts from the Grizzly Knights universe.
Loads character profiles, current state, active arcs, and produces
structured ScriptBlock sequences ready for the audio pipeline.
"""

import re
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from engine.copilot_client import CopilotClient
from engine.continuity import ContinuityEngine
from engine.arc_manager import ArcManager


CHARACTERS_DIR = Path(__file__).parent.parent / "universe" / "characters"
PROMPTS_DIR    = Path(__file__).parent / "prompts"


@dataclass
class ScriptBlock:
    type:      str            # narrator | dialogue | ambient | sfx | music
    text:      str
    character: Optional[str] = None   # character key (e.g. "tony_stark")
    voice_key: Optional[str] = None   # maps to ElevenLabs voice ID in config
    direction: Optional[str] = None   # e.g. "quietly", "not looking up"


@dataclass
class Script:
    episode_number: int
    episode_title:  str
    act:            int
    scene_number:   int
    characters:     list[str]
    location:       str
    blocks:         list[ScriptBlock] = field(default_factory=list)
    raw:            str = ""


class ScriptGenerator:

    def __init__(self, config: dict, client: CopilotClient,
                 continuity: "ContinuityEngine", arcs: "ArcManager"):
        self.config     = config
        self.client     = client
        self.continuity = continuity
        self.arcs       = arcs

        self.system_prompt = (PROMPTS_DIR / "system.txt").read_text()
        self.scene_template = (PROMPTS_DIR / "scene.txt").read_text()
        self._character_profiles: dict[str, dict] = {}

    # ---------------------------------------------------------------- profiles

    def _load_profile(self, character_key: str) -> dict:
        if character_key not in self._character_profiles:
            path = CHARACTERS_DIR / f"{character_key}.yaml"
            if not path.exists():
                raise FileNotFoundError(f"No character profile: {path}")
            prof = yaml.safe_load(path.read_text())
            if not isinstance(prof, dict) or not prof:   # exists but empty/0-byte -> None
                raise ValueError(
                    f"Character profile is empty (0 bytes) — rebuild required: {path}"
                )
            self._character_profiles[character_key] = prof
        return self._character_profiles[character_key]

    def _character_block(self, character_key: str) -> str:
        """Produce a concise prompt-injection block for one character."""
        profile = self._load_profile(character_key)
        state   = self.continuity.get_state(character_key)

        lines = [f"### {profile['name']} ({profile.get('alias', character_key)})"]

        # Psych summary (top-level keys only — keep prompt lean)
        if diagnoses := profile.get("primary_diagnoses_analog"):
            lines.append(f"Diagnoses analog: {', '.join(diagnoses)}")

        if mechs := profile.get("compensatory_mechanisms"):
            neg = mechs.get("negative", [])
            if neg:
                lines.append(f"Active negative mechanisms: {', '.join(neg[:3])}")

        if speech := profile.get("speech_patterns"):
            lines.append(f"Register: {speech.get('register','')}")
            lines.append(f"Under pressure: {speech.get('under_pressure','')}")
            lines.append(f"Emotional tell: {speech.get('emotional_tell','')}")

        # Live state from continuity engine
        for k, v in state.items():
            if k not in ("location", "recent_events"):
                lines.append(f"Current {k}: {v}")

        if events := state.get("recent_events", []):
            lines.append(f"Recent: {'; '.join(events[-2:])}")

        return "\n".join(lines)

    # ---------------------------------------------------------------- generation

    def generate(self,
                 episode_number: int,
                 episode_title:  str,
                 act:            int,
                 scene_number:   int,
                 total_scenes:   int,
                 characters:     list[str],
                 location:       str,
                 ambient_tone:   str,
                 scene_direction: str,
                 previous_summary: str = "Opening scene.") -> Script:

        character_blocks = "\n\n".join(
            self._character_block(c) for c in characters
        )
        active_arcs = self.arcs.format_for_prompt(characters)

        prompt = self.scene_template.format(
            episode_number   = episode_number,
            episode_title    = episode_title,
            act              = act,
            scene_number     = scene_number,
            total_scenes     = total_scenes,
            previous_summary = previous_summary,
            active_arcs      = active_arcs,
            character_blocks = character_blocks,
            location         = location,
            ambient_tone     = ambient_tone,
            scene_direction  = scene_direction,
        )

        raw = self.client.complete([
            {"role": "system",  "content": self.system_prompt},
            {"role": "user",    "content": prompt},
        ])

        script = Script(
            episode_number = episode_number,
            episode_title  = episode_title,
            act            = act,
            scene_number   = scene_number,
            characters     = characters,
            location       = location,
            raw            = raw,
        )
        script.blocks = self._parse(raw, characters)
        return script

    # ---------------------------------------------------------------- parsing

    # Matches: CHARACTER (direction): text  OR  CHARACTER: text
    _DIALOGUE_RE = re.compile(
        r"^([A-Z][A-Z _]+?)(?:\s+\(([^)]+)\))?:\s+(.+)$"
    )
    _TAG_RE = re.compile(r"^\[(\w+):\s*(.+?)\]$")

    def _parse(self, raw: str, characters: list[str]) -> list[ScriptBlock]:
        # Build a name → key lookup from loaded profiles
        name_to_key: dict[str, str] = {}
        for key in characters:
            try:
                p = self._load_profile(key)
                full_name = p["name"].upper()
                name_to_key[full_name] = key
                # Also map ALIAS if present
                if alias := p.get("alias"):
                    name_to_key[alias.upper()] = key
                # Map first name and last name individually so "FELICIA" → felicia_hardy
                parts = full_name.split()
                if len(parts) > 1:
                    name_to_key[parts[0]] = key   # first name
                    name_to_key[parts[-1]] = key  # last name
                # Map the bare character key in case LLM uses that
                name_to_key[key.upper()] = key
                name_to_key[key.upper().replace("_", " ")] = key
            except FileNotFoundError:
                pass

        blocks: list[ScriptBlock] = []

        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue

            # Tag: [AMBIENT: x], [SFX: x], [MUSIC: x]
            if m := self._TAG_RE.match(line):
                tag_type = m.group(1).lower()
                if tag_type in ("ambient", "sfx", "music"):
                    blocks.append(ScriptBlock(type=tag_type, text=m.group(2)))
                continue

            # NARRATOR line
            if line.startswith("NARRATOR:"):
                text = line[len("NARRATOR:"):].strip()
                blocks.append(ScriptBlock(type="narrator", text=text))
                continue

            # Dialogue line
            if m := self._DIALOGUE_RE.match(line):
                name_upper  = m.group(1).strip()
                direction   = m.group(2)
                text        = m.group(3)
                char_key    = name_to_key.get(name_upper)
                if char_key:
                    voice_key = self._load_profile(char_key).get("voice_id_key") or char_key
                else:
                    # Use normalized name as voice_key — TTSEngine will fall back to narrator
                    # if it's not in the voice_map, but at least it's distinct per character
                    char_key  = name_upper.lower().replace(" ", "_")
                    voice_key = char_key
                blocks.append(ScriptBlock(
                    type      = "dialogue",
                    text      = text,
                    character = char_key,
                    voice_key = voice_key,
                    direction = direction,
                ))
                continue

        return blocks

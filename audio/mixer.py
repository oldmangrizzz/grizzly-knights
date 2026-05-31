"""
Audio mixer — synthesizes TTS for each spoken block in a scene.
Returns a list of AudioChunk ready for sequential playback.
No pydub dependency — works with Python 3.13+.
"""

import io
from dataclasses import dataclass
from typing import Optional

from engine.script_generator import Script, ScriptBlock
from audio.tts import TTSEngine
from audio.ambient import AmbientEngine

# Gap between blocks in milliseconds (used as pygame delay)
GAP_DIALOGUE_MS = 300
GAP_NARRATOR_MS = 500
GAP_SFX_MS      = 250


@dataclass
class AudioChunk:
    mp3_bytes: bytes          # raw MP3 audio
    gap_after: int            # ms of silence to insert after playback
    label:     str            # e.g. "FELICIA: ..."


class Mixer:

    def __init__(self,
                 tts:             TTSEngine,
                 ambient:         AmbientEngine,
                 dialogue_volume: float = 1.0,
                 sfx_volume:      float = 0.70):
        self.tts             = tts
        self.ambient         = ambient
        self.dialogue_volume = dialogue_volume
        self.sfx_volume      = sfx_volume

    def mix_scene(self, script: Script) -> list[AudioChunk]:
        """
        Process a Script into a list of AudioChunks for sequential playback.
        Each spoken block (narrator or dialogue) becomes one chunk.
        SFX and ambient tags are noted but not yet mixed (no pydub).
        """
        chunks = []
        for block in script.blocks:
            if block.type in ("ambient", "music"):
                continue  # metadata only for now

            if block.type == "sfx":
                # Small silence placeholder where SFX would hit
                chunks.append(AudioChunk(
                    mp3_bytes = _silence_mp3(),
                    gap_after = GAP_SFX_MS,
                    label     = f"[SFX: {block.text}]",
                ))
                continue

            if block.type in ("narrator", "dialogue"):
                voice_key = block.voice_key or "narrator"
                try:
                    mp3 = self.tts.synthesize(block.text, voice_key)
                except Exception as e:
                    print(f"[TTS error for {voice_key}: {e}]")
                    mp3 = _silence_mp3()

                gap = GAP_NARRATOR_MS if block.type == "narrator" else GAP_DIALOGUE_MS
                if block.type == "dialogue":
                    char = (block.character or "narrator").upper()
                    label = f"{char}: {block.text[:60]}"
                else:
                    label = f"NARRATOR: {block.text[:60]}"

                chunks.append(AudioChunk(mp3_bytes=mp3, gap_after=gap, label=label))

        return chunks


def _silence_mp3() -> bytes:
    """Return minimal valid MP3 bytes (empty frame) for gap placeholders."""
    # A real silent MP3 frame — avoids pygame errors on empty input
    return (
        b"\xff\xfb\x90\x00" +  # MP3 sync + header
        b"\x00" * 413           # ~200ms of silence at 128kbps
    )

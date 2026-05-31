"""
Scene-aware ambient audio engine.
Maps location/mood tags to audio files.
Stub implementation — returns None gracefully when files are missing.
No pydub dependency — works with Python 3.13+.
"""

from pathlib import Path
from typing import Optional


AMBIENT_DIR = Path(__file__).parent.parent / "ambient"
SFX_DIR     = Path(__file__).parent.parent / "sfx"

AMBIENT_MAP: dict[str, str] = {
    "urban_night":          "urban_night.mp3",
    "rain_on_glass":        "rain_on_glass.mp3",
    "hospital_corridor":    "hospital_corridor.mp3",
    "diner_morning":        "diner_morning.mp3",
    "baxter_building":      "baxter_building_hum.mp3",
    "latveria":             "latveria_wind.mp3",
    "hell_kitchen_street":  "hell_kitchen_street.mp3",
    "malibu_compound":      "malibu_surf.mp3",
    "brooklyn_apartment":   "brooklyn_apartment.mp3",
    "rooftop":              "rooftop_wind.mp3",
    "bar_interior":         "bar_interior.mp3",
    "warehouse":            "warehouse_empty.mp3",
    "va_hallway":           "fluorescent_hum.mp3",
    "queens_apartment":     "queens_street.mp3",
    "negative_zone":        "negative_zone_drone.mp3",
    "cheesecake_factory":   "restaurant_ambient.mp3",
}

SFX_MAP: dict[str, str] = {
    "glass_set_down":     "glass_set_down.mp3",
    "door_open":          "door_open.mp3",
    "door_close":         "door_close.mp3",
    "traffic_distant":    "traffic_distant.mp3",
    "phone_buzz":         "phone_buzz.mp3",
    "suit_power_on":      "suit_power_on.mp3",
    "typing":             "typing.mp3",
    "rain_window":        "rain_window.mp3",
    "gunshot_distant":    "gunshot_distant.mp3",
    "footsteps_concrete": "footsteps_concrete.mp3",
}


class AmbientEngine:

    def __init__(self, ambient_volume: float = 0.25):
        self.volume = ambient_volume

    def load(self, tag: str) -> Optional[bytes]:
        """Load ambient MP3 bytes for tag. Returns None if file missing."""
        filename = AMBIENT_MAP.get(tag)
        if not filename:
            return None
        path = AMBIENT_DIR / filename
        if not path.exists():
            return None
        return path.read_bytes()

    def load_sfx(self, tag: str) -> Optional[bytes]:
        """Load SFX MP3 bytes for tag. Returns None if file missing."""
        filename = SFX_MAP.get(tag)
        if not filename:
            return None
        path = SFX_DIR / filename
        if not path.exists():
            return None
        return path.read_bytes()

    # Compatibility stubs — unused now but kept for future mixing
    def get_looped(self, tag: str, duration_ms: int) -> None:
        return None

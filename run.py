"""
Grizzly Knights Universe Engine
fire-and-forget: python run.py
"""

import os
import sys
import signal
import yaml
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box

from engine.copilot_client import CopilotClient
from engine.continuity import ContinuityEngine
from engine.arc_manager import ArcManager
from engine.script_generator import ScriptGenerator
from engine.episode_runner import EpisodeRunner

ROOT = Path(__file__).parent
console = Console()


def load_config() -> dict:
    return yaml.safe_load((ROOT / "config.yaml").read_text())


def print_scene_header(label: str, script=None):
    console.clear()
    title = Text(label, style="bold cyan")
    console.print(Panel(title, box=box.DOUBLE_EDGE, border_style="dim"))
    if script:
        for block in script.blocks[:4]:
            if block.type == "narrator":
                console.print(f"[dim italic]{block.text[:100]}...[/dim italic]")
                break


def run_text_only(config: dict):
    """Phase 1: generate and print scripts to terminal. No audio."""
    client     = CopilotClient(
        model       = config["generation"]["model"],
        temperature = config["generation"]["temperature"],
        max_tokens  = config["generation"]["max_tokens"],
    )
    continuity = ContinuityEngine()
    arcs       = ArcManager()
    generator  = ScriptGenerator(config, client, continuity, arcs)
    runner     = EpisodeRunner(generator, continuity, arcs, config)

    ep = runner.start_new_episode()
    console.print(Panel(
        f"[bold]Episode {ep.number}[/bold] — [cyan]{ep.title}[/cyan]\n"
        f"[dim]Characters: {', '.join(ep.characters)}[/dim]",
        border_style="cyan", box=box.ROUNDED
    ))

    scene_index = 0
    while True:
        args   = runner.next_scene_args(scene_index)
        console.print(f"\n[dim]Generating Act {args['act']} · Scene {args['scene_number']}...[/dim]")
        script = generator.generate(**args)
        runner.record_scene(script)

        console.print(f"\n[bold cyan]— Act {script.act} · Scene {script.scene_number} —[/bold cyan]")
        console.print(f"[dim]{script.location}[/dim]\n")

        for block in script.blocks:
            if block.type == "ambient":
                console.print(f"[dim]\\[{block.text}][/dim]")
            elif block.type == "sfx":
                console.print(f"[dim]\\[SFX: {block.text}][/dim]")
            elif block.type == "music":
                console.print(f"[dim]\\[MUSIC: {block.text}][/dim]")
            elif block.type == "narrator":
                console.print(f"[italic]{block.text}[/italic]")
            elif block.type == "dialogue":
                char = (block.character or "").replace("_", " ").upper()
                direction = f" ({block.direction})" if block.direction else ""
                console.print(f"[bold]{char}[/bold][dim]{direction}:[/dim] {block.text}")

        scene_index += 1
        console.print("\n[dim]─ ─ ─[/dim]")


def run_audio(config: dict, el_key: str):
    """Phase 2+: full audio pipeline."""
    from audio.tts import TTSEngine
    from audio.ambient import AmbientEngine
    from audio.mixer import Mixer
    from audio.queue_manager import QueueManager

    client     = CopilotClient(
        model       = config["generation"]["model"],
        temperature = config["generation"]["temperature"],
        max_tokens  = config["generation"]["max_tokens"],
    )
    continuity = ContinuityEngine()
    arcs       = ArcManager()
    generator  = ScriptGenerator(config, client, continuity, arcs)
    runner     = EpisodeRunner(generator, continuity, arcs, config)

    voice_map  = config.get("elevenlabs", {}).get("voices", {})
    tts        = TTSEngine(api_key=el_key, voice_map=voice_map)
    ambient    = AmbientEngine(ambient_volume=config["audio"]["ambient_volume"])
    mixer      = Mixer(
        tts             = tts,
        ambient         = ambient,
        dialogue_volume = config["audio"]["dialogue_volume"],
        sfx_volume      = config["audio"]["sfx_volume"],
    )

    def generate_fn(scene_index: int):
        args   = runner.next_scene_args(scene_index)
        script = generator.generate(**args)
        runner.record_scene(script)
        return script, args["scene_direction"]

    qm = QueueManager(
        mixer       = mixer,
        generate_fn = generate_fn,
        buffer_size = config["audio"]["pregenerate_scenes"],
    )

    def shutdown(sig, frame):
        console.print("\n[dim]Shutting down...[/dim]")
        qm.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    ep = runner.start_new_episode()
    console.print(Panel(
        f"[bold]Episode {ep.number}[/bold] — [cyan]{ep.title}[/cyan]\n"
        f"[dim]Characters: {', '.join(ep.characters)}[/dim]\n"
        f"[dim]Audio mode — buffering...[/dim]",
        border_style="cyan", box=box.ROUNDED
    ))

    qm.start()
    qm.play_loop(on_scene_start=lambda s: print_scene_header(s.label, s.script))


# ------------------------------------------------------------------ entry

if __name__ == "__main__":
    load_dotenv(ROOT / ".env")

    config = load_config()
    el_key = os.getenv("elevenlabs", "")

    # Determine mode
    # --text  : text-only (no audio, no ElevenLabs key needed)
    # default : audio mode if voices are configured, text-only otherwise
    text_only = "--text" in sys.argv

    voices_configured = any(
        v for v in config.get("elevenlabs", {}).get("voices", {}).values() if v
    )

    if text_only or not voices_configured or not el_key:
        if not text_only:
            console.print(
                "[yellow]No voice IDs configured in config.yaml — running text-only mode.[/yellow]\n"
                "[dim]Add ElevenLabs voice IDs to config.yaml and run without --text for audio.[/dim]\n"
            )
        run_text_only(config)
    else:
        run_audio(config, el_key)

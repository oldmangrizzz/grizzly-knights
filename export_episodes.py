"""
Grizzly Knights — Batch Episode Exporter
Generates 4 full episodes as MP3 files with ID3 metadata, imports into Apple Music.

Usage: python export_episodes.py
"""

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import yaml
from dotenv import load_dotenv
from mutagen.id3 import (
    ID3, ID3NoHeaderError, TIT2, TPE1, TALB, TRCK, TCON, TCOM, COMM, TYER
)
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

ROOT = Path(__file__).parent
console = Console()
load_dotenv(ROOT / ".env")

# ── Episode definitions ────────────────────────────────────────────────────────

EPISODES = [
    {
        "number":     1,
        "title":      "Before Anyone Noticed",
        "characters": ["felicia_hardy", "wade_wilson"],
        "description": (
            "Wednesday afternoon at the Cheesecake Factory. "
            "No mission. No reason. Nobody knows they're friends. "
            "The universe begins the way it actually works — "
            "two people who found each other outside the binary, "
            "splitting fries and not explaining themselves to anyone."
        ),
    },
    {
        "number":     2,
        "title":      "The System",
        "characters": ["tony_stark", "jessica_jones", "clint_barton"],
        "description": (
            "Tony is managing. Jessica is functional. Clint is fine. "
            "None of them believe the other two. "
            "Three people who know exactly what they're doing to themselves "
            "and have decided to keep doing it anyway."
        ),
    },
    {
        "number":     3,
        "title":      "What Gets Said",
        "characters": ["sam_wilson", "bucky_barnes", "steve_rogers"],
        "description": (
            "The three of them in a room. "
            "What Steve carries. What Sam sees. What Bucky doesn't say. "
            "The conversation that keeps almost happening and then doesn't."
        ),
    },
    {
        "number":     4,
        "title":      "Parker Luck",
        "characters": ["peter_parker", "mary_jane_watson", "felicia_hardy"],
        "description": (
            "Peter, MJ, and Felicia in the same orbit for one afternoon. "
            "MJ sees everything. Felicia sees everything MJ sees. "
            "Peter is the only one who doesn't notice what's happening."
        ),
    },
]

ALBUM       = "Grizzly Knights"
ARTIST      = "Grizzly Knights Universe"
GENRE       = "Audio Drama"
YEAR        = "2026"
OUTPUT_DIR  = ROOT / "episodes"


# ── Core pipeline ──────────────────────────────────────────────────────────────

def generate_episode_script(ep_def: dict, config: dict, client, continuity, arcs) -> list:
    """Generate all scenes for an episode, return list of Script objects."""
    from engine.script_generator import ScriptGenerator
    from engine.episode_runner import EpisodeRunner

    # Temporarily override active characters for this episode
    cfg = dict(config)
    cfg["session"] = dict(config.get("session", {}))
    cfg["session"]["active_characters"] = ep_def["characters"]

    generator = ScriptGenerator(cfg, client, continuity, arcs)
    runner    = EpisodeRunner(generator, continuity, arcs, cfg)

    # Force episode number
    arcs._state["episode_count"] = ep_def["number"] - 1
    ep = runner.start_new_episode()

    scripts = []
    total_scenes = sum(runner.SCENES_PER_ACT.values())
    for i in range(total_scenes):
        args   = runner.next_scene_args(i)
        script = generator.generate(**args)
        runner.record_scene(script)
        scripts.append(script)
        console.print(
            f"  [dim]Act {script.act} · Scene {script.scene_number} — "
            f"{script.location} — {len(script.blocks)} blocks[/dim]"
        )

    return scripts


def scripts_to_mp3(scripts: list, tts, tmp_dir: Path) -> list[Path]:
    """TTS all spoken blocks via Colab GPU, return list of temp MP3 paths in order."""
    from audio.colab_tts import run_colab
    import zipfile

    all_blocks = [b for s in scripts for b in s.blocks]
    total_spoken = sum(1 for b in all_blocks if b.type in ("narrator", "dialogue"))

    # Serialize blocks for Colab
    block_dicts = [
        {
            "index": i,
            "type": b.type,
            "text": b.text,
            "voice_key": b.voice_key or "narrator",
        }
        for i, b in enumerate(all_blocks)
    ]

    # Run on Colab GPU
    zip_path = run_colab(block_dicts, timeout_sec=3600)
    if not zip_path:
        console.print(f"  [red]Colab synthesis failed[/red]")
        return []

    # Extract ZIP
    extract_dir = tmp_dir / "colab_out"
    extract_dir.mkdir(exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(extract_dir)

    # Read manifest
    manifest_path = extract_dir / "manifest.json"
    if not manifest_path.exists():
        console.print(f"  [red]No manifest.json in ZIP[/red]")
        return []

    manifest = json.loads(manifest_path.read_text())
    results: dict[int, bytes | None] = {}
    for entry in manifest:
        idx = entry["index"]
        audio_file = entry.get("audio")
        if audio_file:
            mp3_path = extract_dir / audio_file
            if mp3_path.exists():
                results[idx] = mp3_path.read_bytes()
            else:
                results[idx] = None
        else:
            results[idx] = None

    hits = sum(1 for v in results.values() if v is not None)
    console.print(f"  [green]TTS complete — {hits}/{total_spoken} blocks[/green]")

    # Reassemble in order, inserting gaps
    parts = []
    block_num = 0
    for block in all_blocks:
        if block.type not in ("narrator", "dialogue"):
            if block.type == "sfx":
                parts.append(_silence_file(tmp_dir, block_num, ms=300))
            block_num += 1
            continue

        mp3_bytes = results.get(block_num)
        if mp3_bytes:
            p = tmp_dir / f"block_{block_num:04d}.mp3"
            p.write_bytes(mp3_bytes)
            parts.append(p)
        else:
            parts.append(_silence_file(tmp_dir, block_num, ms=500))

        gap_ms = 500 if block.type == "narrator" else 300
        parts.append(_silence_file(tmp_dir, block_num * 10000, ms=gap_ms))
        block_num += 1

    return parts


def concatenate_mp3s(parts: list[Path], output: Path):
    """Concatenate MP3 files using ffmpeg concat demuxer."""
    list_file = output.parent / "concat_list.txt"
    list_file.write_text(
        "\n".join(f"file '{p.resolve()}'" for p in parts if p.exists())
    )
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            str(output),
        ],
        check=True,
        capture_output=True,
    )
    list_file.unlink(missing_ok=True)


def tag_mp3(path: Path, ep: dict):
    """Write ID3 tags to the final MP3."""
    try:
        tags = ID3(str(path))
    except ID3NoHeaderError:
        tags = ID3()

    tags.add(TIT2(encoding=3, text=ep["title"]))
    tags.add(TPE1(encoding=3, text=ARTIST))
    tags.add(TALB(encoding=3, text=ALBUM))
    tags.add(TRCK(encoding=3, text=str(ep["number"])))
    tags.add(TCON(encoding=3, text=GENRE))
    tags.add(TYER(encoding=3, text=YEAR))
    tags.add(TCOM(encoding=3, text="Grizzly Knights Engine"))
    tags.add(COMM(
        encoding=3, lang="eng", desc="desc",
        text=ep["description"],
    ))
    tags.save(str(path))


def add_to_apple_music(path: Path):
    """Import MP3 into Apple Music via osascript."""
    script = f'''
    tell application "Music"
        add POSIX file "{path.resolve()}"
    end tell
    '''
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        console.print(f"  [yellow]Apple Music import warning: {result.stderr.strip()}[/yellow]")
    else:
        console.print(f"  [green]Added to Apple Music ✓[/green]")


def _silence_file(tmp_dir: Path, idx: int, ms: int = 300) -> Path:
    """Generate a short silent MP3 via ffmpeg."""
    p = tmp_dir / f"silence_{idx}_{ms}.mp3"
    if not p.exists():
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo",
                "-t", str(ms / 1000.0),
                "-q:a", "9", "-acodec", "libmp3lame",
                str(p),
            ],
            check=True, capture_output=True,
        )
    return p


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    config = yaml.safe_load((ROOT / "config.yaml").read_text())
    OUTPUT_DIR.mkdir(exist_ok=True)

    from engine.copilot_client import CopilotClient
    from engine.continuity import ContinuityEngine
    from engine.arc_manager import ArcManager
    client     = CopilotClient(
        model       = config["generation"]["model"],
        temperature = config["generation"]["temperature"],
        max_tokens  = config["generation"]["max_tokens"],
    )
    continuity = ContinuityEngine()
    arcs       = ArcManager()
    tts        = None  # TTS handled by ColabTTSEngine in scripts_to_mp3

    for ep_def in EPISODES:
        console.rule(f"[bold cyan]Episode {ep_def['number']} — {ep_def['title']}[/bold cyan]")
        console.print(f"[dim]Cast: {', '.join(ep_def['characters'])}[/dim]\n")

        out_path = OUTPUT_DIR / f"{ep_def['number']:02d} - {ep_def['title']}.mp3"

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)

            # 1. Generate scripts
            console.print("[bold]Generating scripts...[/bold]")
            scripts = generate_episode_script(ep_def, config, client, continuity, arcs)

            # 2. TTS all spoken blocks via Colab GPU
            console.print(f"\n[bold]Synthesizing {sum(len(s.blocks) for s in scripts)} blocks via Colab GPU...[/bold]")
            parts = scripts_to_mp3(scripts, None, tmp_dir)

            # 3. Concatenate into single MP3
            console.print(f"\n[bold]Concatenating {len(parts)} audio parts...[/bold]")
            concatenate_mp3s(parts, out_path)

            duration = _get_duration(out_path)
            console.print(f"  [green]→ {out_path.name}[/green] [dim]({duration})[/dim]")

        # 4. Tag
        console.print("[bold]Writing ID3 metadata...[/bold]")
        tag_mp3(out_path, ep_def)

        # 5. Apple Music
        console.print("[bold]Adding to Apple Music...[/bold]")
        add_to_apple_music(out_path)

        console.print()

    console.rule("[green]All 4 episodes exported and imported[/green]")
    console.print(f"\nFiles in [cyan]{OUTPUT_DIR}[/cyan]")


def _get_duration(path: Path) -> str:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True
    )
    try:
        secs = float(result.stdout.strip())
        m, s = divmod(int(secs), 60)
        return f"{m}m {s}s"
    except Exception:
        return "unknown duration"


if __name__ == "__main__":
    main()

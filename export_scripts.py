"""
Grizzly Knights — Text Script Exporter (ElevenReader-ready)

Generates the 4 launch episodes as formatted .txt files.
Each file is structured for ElevenReader import: scene headers,
NARRATOR: lines, CHARACTER: dialogue, and bracketed [SFX]/[AMBIENT]
production cues.

Usage:  python export_scripts.py
Output: episodes_text/NN - Title.txt
"""

import sys
import yaml
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich import box

ROOT = Path(__file__).parent
console = Console()
load_dotenv(ROOT / ".env")

from engine.copilot_client import CopilotClient
from engine.continuity import ContinuityEngine
from engine.arc_manager import ArcManager
from engine.script_generator import ScriptGenerator
from engine.episode_runner import EpisodeRunner

OUTPUT_DIR = ROOT / "episodes_text"

EPISODES = [
    {
        "number": 1,
        "title":  "Before Anyone Noticed",
        "characters": ["felicia_hardy", "wade_wilson"],
        "logline": (
            "Wednesday afternoon at the Cheesecake Factory. No mission. No reason. "
            "Nobody knows they're friends. Two people who found each other outside the binary, "
            "splitting fries and not explaining themselves to anyone."
        ),
    },
    {
        "number": 2,
        "title":  "The System",
        "characters": ["tony_stark", "jessica_jones", "clint_barton"],
        "logline": (
            "Tony is managing. Jessica is functional. Clint is fine. None of them believe the "
            "other two. Three people who know exactly what they are doing to themselves and have "
            "decided to keep doing it anyway."
        ),
    },
    {
        "number": 3,
        "title":  "What Gets Said",
        "characters": ["sam_wilson", "bucky_barnes", "steve_rogers"],
        "logline": (
            "The three of them in a room. What Steve carries. What Sam sees. What Bucky does not "
            "say. The conversation that keeps almost happening and then does not."
        ),
    },
    {
        "number": 4,
        "title":  "Parker Luck",
        "characters": ["peter_parker", "mary_jane_watson", "felicia_hardy"],
        "logline": (
            "Peter, MJ, and Felicia in the same orbit for one afternoon. MJ sees everything. "
            "Felicia sees everything MJ sees. Peter is the only one who does not notice what is "
            "happening."
        ),
    },
]


def _character_display(generator: ScriptGenerator, key: str) -> str:
    """Get the canonical UPPER name for a character key."""
    try:
        profile = generator._load_profile(key)
        return profile["name"].upper()
    except Exception:
        return key.upper().replace("_", " ")


def _short_name(full_upper: str) -> str:
    """Title-case a name, prefer first name only for dialogue attribution."""
    parts = full_upper.split()
    if not parts:
        return "they"
    return parts[0].title()


def format_script_text(scripts: list, ep_def: dict, generator: ScriptGenerator) -> str:
    """
    Render as prose novelization for ElevenReader.

    No stage directions read aloud. No SFX/AMBIENT/MUSIC cues. No 'NARRATOR:' or
    'CHARACTER:' speaker tags. Narration is plain prose. Dialogue uses
    natural attribution ('Felicia said.') so a single narrator voice can read it
    as a chapter, not a script.
    """
    name_map = {k: _character_display(generator, k) for k in ep_def["characters"]}

    paragraphs: list[str] = []
    paragraphs.append(f"Grizzly Knights")
    paragraphs.append(f"Episode {ep_def['number']}: {ep_def['title']}")
    paragraphs.append(ep_def["logline"])

    # Track previous speaker so we can drop redundant attribution
    last_speaker_key: str | None = None

    for s in scripts:
        # Light scene break — single line, prose-friendly
        paragraphs.append("* * *")

        last_speaker_key = None
        for b in s.blocks:
            if b.type == "narrator":
                paragraphs.append(b.text.strip())
                last_speaker_key = None

            elif b.type == "dialogue":
                full_upper = name_map.get(b.character) or (b.character or "voice").upper().replace("_", " ")
                short = _short_name(full_upper)
                text = b.text.strip()
                # Ensure dialogue has terminal punctuation before the tag
                if text and text[-1] not in ".!?":
                    text = text + "."
                # Quote the dialogue
                quoted = f"\u201c{text}\u201d"
                if b.character and b.character == last_speaker_key:
                    # Same speaker continuing — no attribution
                    paragraphs.append(quoted)
                else:
                    # Verb selection: question -> asked, otherwise said
                    verb = "asked" if text.rstrip().endswith("?") else "said"
                    paragraphs.append(f"{quoted} {short} {verb}.")
                last_speaker_key = b.character

            # SFX / AMBIENT / MUSIC: deliberately omitted — production cues
            # that would otherwise be read aloud verbatim by a single-voice
            # narration engine.

    return "\n\n".join(paragraphs) + "\n"


def generate_one_episode(ep_def: dict, config: dict, client, continuity, arcs) -> list:
    """Run the existing pipeline for a single episode and return its Script list."""
    cfg = dict(config)
    cfg["session"] = dict(config.get("session", {}))
    cfg["session"]["active_characters"] = ep_def["characters"]

    generator = ScriptGenerator(cfg, client, continuity, arcs)
    runner    = EpisodeRunner(generator, continuity, arcs, cfg)

    arcs._state["episode_count"] = ep_def["number"] - 1
    runner.start_new_episode()

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
    return scripts, generator


def main():
    config = yaml.safe_load((ROOT / "config.yaml").read_text())
    OUTPUT_DIR.mkdir(exist_ok=True)

    client     = CopilotClient(
        model       = config["generation"]["model"],
        temperature = config["generation"]["temperature"],
        max_tokens  = config["generation"]["max_tokens"],
    )
    continuity = ContinuityEngine()
    arcs       = ArcManager()

    written: list[Path] = []
    for ep_def in EPISODES:
        console.rule(f"[bold cyan]Episode {ep_def['number']} — {ep_def['title']}[/bold cyan]")
        console.print(f"[dim]Cast: {', '.join(ep_def['characters'])}[/dim]\n")

        try:
            scripts, generator = generate_one_episode(ep_def, config, client, continuity, arcs)
        except Exception as e:
            console.print(f"[red]Episode {ep_def['number']} failed: {e}[/red]")
            continue

        text = format_script_text(scripts, ep_def, generator)
        out  = OUTPUT_DIR / f"{ep_def['number']:02d} - {ep_def['title']}.txt"
        out.write_text(text)
        size_kb = out.stat().st_size / 1024
        words   = len(text.split())
        console.print(f"  [green]→ {out.name}[/green] [dim]({words} words, {size_kb:.1f} KB)[/dim]")
        written.append(out)

    console.print()
    console.rule("[green]Export complete[/green]")
    console.print(Panel(
        "\n".join(f"• {p.name}" for p in written) or "[red]No files produced[/red]",
        title=f"Files in {OUTPUT_DIR}", border_style="green", box=box.ROUNDED
    ))
    console.print(
        "\n[bold]ElevenReader import:[/bold] open each .txt in ElevenReader, "
        "assign voices to each character name, hit play.\n"
    )


if __name__ == "__main__":
    main()

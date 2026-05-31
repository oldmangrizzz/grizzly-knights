"""
Batch-cook N fresh long-form Grizzly Knights episodes via ShowRunner.

Usage:
  python cook_batch.py <count> [start_number]

Default: 5 episodes starting at the next available number.
"""
import sys
import time
from pathlib import Path

from rich.console import Console

from engine.agency_engine import build_model
from engine.uatu import plan_episode
from export_episodes_agency import export_one, OUTPUT_DIR

console = Console()


def next_episode_number() -> int:
    existing = sorted(OUTPUT_DIR.glob("[0-9][0-9] - *.txt"))
    if not existing:
        return 1
    nums = []
    for p in existing:
        try:
            nums.append(int(p.name[:2]))
        except ValueError:
            pass
    return (max(nums) + 1) if nums else 1


def main():
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    start = int(sys.argv[2]) if len(sys.argv) > 2 else next_episode_number()

    model = build_model("gpt-4o")

    console.rule(f"[bold cyan]Cooking {count} episodes, starting at #{start:02d}[/bold cyan]")

    for i in range(count):
        n = start + i
        t0 = time.time()
        console.print(f"\n[bold]── Episode {n:02d} — planning ─────────────────[/bold]")
        try:
            plan = plan_episode(premise=None, cast=None, episode_number=n)
        except Exception as e:
            console.print(f"[red]ShowRunner failed for #{n}: {type(e).__name__}: {e}[/red]")
            continue
        console.print(f"[dim]Title: {plan.title}  |  Cast: {plan.cast}  |  Scenes: {len(plan.scenes)}[/dim]")
        out = export_one(plan, model)
        dt = time.time() - t0
        if out:
            console.print(f"[green]✔ #{n} done in {dt/60:.1f} min[/green]")
        else:
            console.print(f"[red]✘ #{n} failed after {dt/60:.1f} min[/red]")

    console.rule("[green]Batch complete[/green]")


if __name__ == "__main__":
    main()

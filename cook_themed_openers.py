"""
Cook the three themed openers (FF / Avengers / X-Men) after any in-flight
cook process completes. Runs sequentially so episode numbers don't race.
"""
import os
import sys
import time
from rich.console import Console

from engine.agency_engine import build_model
from engine.uatu import plan_episode
from export_episodes_agency import export_one, OUTPUT_DIR

console = Console()


FF_PREMISE = """\
Reed Richards has been awake for ninety-one hours. Sue knows because she's
been counting since hour forty when she first asked him to come to bed.
Johnny just got back from Cabo with a hickey on his neck shaped like
Florida and won't say from whom. Ben is on his fourth Yuengling at the
kitchen island, watching Sue try not to throw a coffee mug at her husband.

Tonight is Ben's birthday. The reservation at Peter Luger was for six. It
is now nine-forty. Reed is still in the lab.

Over the course of the night — kitchen, then back deck for Ben's cigar
and Johnny's vape, then the living room when the rain starts, then Reed
finally coming up and the rest of them deciding what the hell to do with
him — the family relitigates twenty years of Reed being absent at exactly
the moments that mattered. Sue has been holding this since the Negative
Zone. Johnny weaponizes it for fun. Ben tries to keep the peace and
fails. Nobody is sober by the time it's over.

The real subject is whether Sue is going to leave, and whether Reed will
notice in time. Nobody says that out loud. Everybody knows.

TONE: Hickman F4 emotional intelligence + Slott F4 banter + Bendis Alias
domestic-night register. Johnny is openly bi and will mention it. Sue
swears like the Navy brat she canonically is. Ben tells war stories.
Reed, when he finally arrives, doesn't apologize — he explains, which is
worse. Profanity uncensored. No fade-to-black if anyone touches anyone.

CAST (locked): sue_storm, johnny_storm, ben_grimm, reed_richards.
"""

AVENGERS_PREMISE = """\
The Avengers don't have a tower anymore. They have a bar. Specifically,
they have Sersi's — the back room of a Hell's Kitchen Irish pub that
Tony bought through three shell companies after the second time Stark
Tower got destroyed, because everybody finally admitted what they
actually need is somewhere to drink with each other on Tuesday nights
with no press, no cameras, and no fucking suits.

Tonight: Tony (sparkling water, three years sober, white-knuckle),
Natasha (vodka rocks, second of the night), Clint (Coors Light, hearing
aids out so he can read lips and pretend he isn't), Sam (bourbon, on
call but it's quiet), Bucky (water, doesn't drink anymore for reasons),
and Steve (water, doesn't drink because Streets of Poison broke his
governor). Carol is supposed to be coming but is forty minutes late and
not answering.

The pretext is Clint's anniversary — twelve years since New York. The
actual subject, once the third round lands, is the thing nobody has
said yet: Wanda is supposed to be invited to these. She isn't. And
Vision has been seen in Westchester twice this month. Somebody at this
table is going to have to be the one to tell Steve. Or Steve already
knows and is waiting to see who has the spine to say it.

TONE: Hickman Avengers gravity + Bendis New Avengers booth-scene
chemistry + Aaron Avengers profanity floor + Brubaker Cap honesty.
Natasha is going to flirt with everyone at the table once. Bucky is
going to make exactly one joke and it's going to land hard. Tony is
going to almost relapse. Steve is going to be "fine."

CAST (locked): tony_stark, natasha_romanoff, clint_barton, sam_wilson,
bucky_barnes, steve_rogers.
"""

XMEN_PREMISE = """\
Logan's cabin in the Adirondacks. The X-Men don't come here. That's the
point. Tonight, four of them are here anyway — Logan, Jean, Scott, and
Ororo — because Charles is dead again (fifth time, nobody's counting
except Hank, who is) and the funeral is Saturday and somebody has to
decide who's giving the eulogy and Logan's place has the only liquor
cabinet that won't be on TMZ by morning.

Whiskey neat for Logan and Ororo. Wine for Jean (she's been
Phoenix-coded sober for two years; this is the first glass). Scott
isn't drinking — Scott doesn't drink, which is its own kind of tell.
There's a fire going. Logan smokes inside because it's his house. Jean
lets him.

Across the night — cabin great room, then the porch at midnight when
Ororo needs air, then Logan's kitchen when Scott finally cracks, then
back to the fire at 4 AM when Jean says the thing — they re-litigate
every triangle in this room. Scott and Jean. Logan and Jean. Logan and
Ororo (one night, '04, never discussed). Scott and Emma (who is
conspicuously not invited). And the thing nobody wants to say: Charles
wasn't a good man and pretending he was at the funeral is going to
break at least one of them.

TONE: Claremont depth + Whedon Astonishing intimacy + Hickman HoX/PoX
cold honesty + Aaron Wolverine bar-fight grit. Logan curses in three
languages. Jean is the most powerful person in the room and acts like
it without performing it. Scott is wound tight enough to snap a knife.
Ororo names what's actually happening because somebody has to.

CAST (locked): logan, jean_grey, scott_summers, ororo_munroe.
"""

OPENERS = [
    ("Fantastic Four — Ben's Birthday",         FF_PREMISE,       ["sue_storm","johnny_storm","ben_grimm","reed_richards"]),
    ("Avengers — Sersi's Back Room",            AVENGERS_PREMISE, ["tony_stark","natasha_romanoff","clint_barton","sam_wilson","bucky_barnes","steve_rogers"]),
    ("X-Men — Logan's Cabin, Charles Again",    XMEN_PREMISE,     ["logan","jean_grey","scott_summers","ororo_munroe"]),
]


def _running_cooks() -> list[int]:
    """Return PIDs of any running cook_*.py processes (excluding self)."""
    me = os.getpid()
    pids = []
    try:
        import subprocess
        out = subprocess.check_output(["ps","-eo","pid,command"]).decode()
        for line in out.splitlines():
            line = line.strip()
            if "python" in line and ("cook_batch.py" in line or "cook_ep01_genesis.py" in line or "cook_themed_openers.py" in line):
                try:
                    pid = int(line.split()[0])
                    if pid != me:
                        pids.append(pid)
                except ValueError:
                    pass
    except Exception:
        pass
    return pids


def _next_episode_number() -> int:
    existing = sorted(OUTPUT_DIR.glob("[0-9][0-9] - *.txt"))
    nums = []
    for p in existing:
        try: nums.append(int(p.name[:2]))
        except ValueError: pass
    return (max(nums) + 1) if nums else 1


def main() -> int:
    console.rule("[bold yellow]Themed openers queued — waiting for in-flight cooks[/bold yellow]")
    while True:
        running = _running_cooks()
        if not running:
            break
        console.print(f"[dim]waiting on PIDs {running}…[/dim]")
        time.sleep(60)

    console.print("[green]queue clear, beginning themed openers[/green]\n")
    model = build_model("gpt-4o")

    for label, premise, cast in OPENERS:
        n = _next_episode_number()
        console.rule(f"[bold magenta]#{n:02d} — {label}[/bold magenta]")
        t0 = time.time()
        try:
            plan = plan_episode(premise=premise, cast=cast, episode_number=n)
            out = export_one(plan, model)
            console.print(f"[green]Cooked in {(time.time()-t0)/60:.1f} min → {out}[/green]\n")
        except Exception as e:
            console.print(f"[red]{label} failed: {type(e).__name__}: {e}[/red]")
            continue

    console.rule("[bold green]All themed openers complete[/bold green]")
    return 0


if __name__ == "__main__":
    sys.exit(main())

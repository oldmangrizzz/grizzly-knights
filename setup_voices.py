"""
One-time voice selection setup.
Fetches available ElevenLabs voices, passes each character's speech profile
to the LLM, picks the best fit, and locks the IDs into config.yaml permanently.

Run once: python setup_voices.py
After that: voices are locked. This script will not overwrite existing selections.
"""

import os
import sys
import yaml
import requests
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich import box

ROOT = Path(__file__).parent
console = Console()

load_dotenv(ROOT / ".env")


def fetch_voices(api_key: str) -> list[dict]:
    resp = requests.get(
        "https://api.elevenlabs.io/v1/voices",
        headers={"xi-api-key": api_key},
        timeout=15,
    )
    resp.raise_for_status()
    voices = resp.json().get("voices", [])
    # Return only what the LLM needs — keep prompt lean
    return [
        {
            "id":     v["voice_id"],
            "name":   v["name"],
            "labels": v.get("labels", {}),
            "description": v.get("description") or "",
        }
        for v in voices
    ]


def voice_list_for_prompt(voices: list[dict]) -> str:
    lines = []
    for v in voices:
        labels = ", ".join(f"{k}: {val}" for k, val in v["labels"].items() if val)
        desc   = v["description"][:120] if v["description"] else ""
        lines.append(f'ID: {v["id"]} | Name: {v["name"]} | {labels}{" | " + desc if desc else ""}')
    return "\n".join(lines)


CHARACTER_PROFILES = {
    "narrator": {
        "description": "Omniscient narrator for a gritty, grounded audio drama. Tone: measured, authoritative, "
                       "not melodramatic. Think a seasoned journalist, not a movie trailer voice. "
                       "Neutral American accent preferred. Male or female — whichever fits a detached "
                       "but present voice that never editorializes.",
    },
    "tony_stark": {
        "description": "Tony Stark. Mid-40s American male. Register: rapid, sardonic, technically precise. "
                       "Deflects with wit. Under pressure: clipped, then walls up. Drunk tell: becomes MORE "
                       "articulate before going grandiose. Needs a voice that can carry intelligence and "
                       "contempt simultaneously without sounding like a parody.",
    },
    "steve_rogers": {
        "description": "Steve Rogers. Physically 30s but spiritually older. American male, faint period affect. "
                       "Register: direct, unadorned, occasionally formal. Goes still and precise under pressure. "
                       "Never performs warmth — when it's there it's real, and rare. Needs a voice that sounds "
                       "like someone who has been carrying something heavy for a very long time.",
    },
    "frank_castle": {
        "description": "Frank Castle. Late 30s/early 40s American male. Register: minimal, declarative, "
                       "zero wasted words. Abnormally still. Affect is flat and contained — not angry, "
                       "not cold, just compressed. Needs a voice that sounds like someone who processed "
                       "their grief into a tool and has been using it ever since.",
    },
    "jessica_jones": {
        "description": "Jessica Jones. Early-to-mid 30s American female. Register: blunt, sardonic, economic. "
                       "Deflects with dismissal or attack. Under pressure: harder, colder, more cutting. "
                       "Not performatively tough — actually tough, with fatigue underneath it. Needs a voice "
                       "with natural edge and the ability to sound genuinely tired without sounding weak.",
    },
    "sam_wilson": {
        "description": "Sam Wilson. Mid-to-late 30s Black American male. Register: warm, accessible, "
                       "conversational. Deflects with warmth and redirects — asks you a question back. "
                       "Under pressure: still warm but slower, the warmth becomes effortful. Never performs "
                       "his emotions — they're always real, always present. Needs a voice with genuine "
                       "warmth that doesn't tip into saccharine.",
    },
    "bucky_barnes": {
        "description": "Bucky Barnes. Physically 30s, psychologically much older. American male, sparse affect. "
                       "Register: minimal, careful, occasionally dry. Under pressure: shorter answers, longer "
                       "pauses, deliberate word selection. When he makes a joke he's in a safe state — "
                       "humor is rare and tells you something. Needs a voice that carries watchfulness "
                       "without aggression.",
    },
    "matt_murdock": {
        "description": "Matt Murdock. Early-to-mid 30s American male. Register: precise, formal, measured — "
                       "lawyerly even out of court. Under pressure: more formal, more qualified, emotional "
                       "content buried in logic structure. Catholic guilt audible in the cadence. Needs a "
                       "voice that can sound like someone arguing with themselves in real time.",
    },
    "peter_parker": {
        "description": "Peter Parker. Mid-to-late 20s American male. Register: rapid, associative, "
                       "self-interrupting — humor arrives before the thought is finished. Quipping rate "
                       "increases with emotional distress. When he goes quiet and stops quipping, something "
                       "is actually happening. Needs a voice that can carry genuine anxiety underneath "
                       "relentless forward motion.",
    },
    "reed_richards": {
        "description": "Reed Richards. 40s American male. Register: dense, precise, abstracts before "
                       "personalizing. Under pressure: sentences get longer and more qualified, not shorter. "
                       "Emotional tell: very long pauses before anything personal. Needs a voice that sounds "
                       "like someone who has gone all the way to the bottom of every problem — including "
                       "this one.",
    },
    "sue_storm": {
        "description": "Sue Storm-Richards. Late 30s American female. Register: warm, precise, accessible. "
                       "The warmth is genuine AND it's a controlled presentation — both things true "
                       "simultaneously. Under pressure: quieter and more precise, the warmth drops without "
                       "coldness replacing it. Uses full names when something is real. Needs a voice that "
                       "can carry intelligence and care without sounding maternal.",
    },
    "johnny_storm": {
        "description": "Johnny Storm. Late 20s American male. Register: warm, fast, expressive, "
                       "self-interrupting. Talks fast when excited. Humor is warm and inclusive — brings "
                       "people in, not holds them off. When he goes quiet and still, something real is "
                       "happening. Needs a voice with genuine energy that doesn't read as immature.",
    },
    "ben_grimm": {
        "description": "Ben Grimm. 40s American male, Brooklyn in the bones. Register: direct, warm, no "
                       "pretension — says the thing. Humor is self-aware and warm, not deflective. Under "
                       "pressure: quieter and more direct, the humor drops and what's underneath is solid. "
                       "Needs a voice that sounds like someone who has carried something permanent and "
                       "decided to live anyway.",
    },
    "victor_doom": {
        "description": "Victor von Doom. 40s Eastern European male (Latverian/Romani heritage). Register: "
                       "formal, precise, archaic inflection — does not use contractions under pressure. "
                       "Under pressure: more formal, more elaborate, the architecture holds by becoming "
                       "more ornate. Emotional tell: first person instead of third. Needs a voice that "
                       "can carry genuine gravitas without tipping into camp.",
    },
    "clint_barton": {
        "description": "Clint Barton / Hawkeye. Early 40s American male. Register: laconic, self-deprecating, "
                       "dry. Talks like someone who doesn't expect to be taken seriously and is fine with that. "
                       "The humor is always slightly at his own expense. Under pressure: shorter, quieter, "
                       "the self-deprecation falls away and what's left is very direct. Needs a voice that "
                       "sounds competent and slightly used-up at the same time.",
    },
    "kate_bishop": {
        "description": "Kate Bishop / Hawkeye. Mid-20s American female. Register: sharp, confident, quick — "
                       "not nervous-quick, earned-quick. Wit arrives before the thought is fully assembled. "
                       "Under pressure: gets cleaner and more direct, the sharpness becomes surgical. "
                       "Sounds like someone who is very good and knows it without needing to announce it. "
                       "Needs a voice with intelligence and edge that doesn't read as harsh.",
    },
    "bruce_banner": {
        "description": "Bruce Banner. 40s American male. Register: careful, measured, slightly over-qualified. "
                       "Every sentence has a hedge because precision is how he stays calm. Under pressure: "
                       "the hedges drop and the voice gets very flat very fast — which is the tell. "
                       "A voice that sounds like someone managing enormous internal pressure through "
                       "careful, deliberate word selection. The calm is effortful.",
    },
    "thor_odinson": {
        "description": "Thor Odinson. Asgardian — sounds ancient in a way that has learned to be present. "
                       "Register: formal, expansive, without condescension. Warmth is genuine and large-scale. "
                       "Under pressure: slower, more deliberate, the formality intensifies and becomes "
                       "ceremonial. Needs a resonant, authoritative male voice that carries the weight of "
                       "someone who has outlived everyone they started with. Not theatrical — genuinely heavy.",
    },
    "wanda_maximoff": {
        "description": "Wanda Maximoff / Scarlet Witch. Late 20s/early 30s female, Sokovian accent — "
                       "Eastern European, light but present. Register: contained, precise, with grief "
                       "running directly underneath every sentence. Under pressure: the containment holds "
                       "until it doesn't — when it breaks the affect floods. Needs a female voice with "
                       "a European accent, warmth that's been through damage, and the ability to sound "
                       "like someone holding something enormous very carefully.",
    },
    "scott_lang": {
        "description": "Scott Lang / Ant-Man. Early-to-mid 40s American male. Register: warm, self-aware, "
                       "self-deprecating — knows he's the unlikely guy and leans into it with genuine humor "
                       "rather than deflection. Under pressure: funnier, faster, until he goes quiet and "
                       "gets completely serious — the pivot is distinct. Needs a voice that carries "
                       "genuine warmth and ordinary-guy energy without sounding incompetent.",
    },
    "carol_danvers": {
        "description": "Carol Danvers / Captain Marvel. Late 30s/early 40s American female. Register: "
                       "direct, clipped, military economy — says exactly what needs saying. Under pressure: "
                       "shorter, harder, the directness becomes terse. Warmth exists but she doesn't "
                       "perform it — it shows up in action. Needs a female voice that carries authority "
                       "without aggression, competence without warmth performance.",
    },
    "luke_cage": {
        "description": "Luke Cage / Power Man. Early 40s Black American male. Register: deliberate, measured, "
                       "warm underneath the directness. Not fast — thinks before speaking. Under pressure: "
                       "quieter and more deliberate, the warmth drops into something immovable. "
                       "Needs a deep, steady male voice — the kind of voice that makes a room feel safer "
                       "just by being present. Not theatrical depth. Structural depth.",
    },
    "danny_rand": {
        "description": "Danny Rand / Iron Fist. Early 30s American male raised partly in K'un-Lun. "
                       "Register: earnest, slightly formal, occasionally off-rhythm — like someone who "
                       "learned social fluency from texts rather than lived experience. Under pressure: "
                       "more formal, more focused, the social awkwardness drops and something older shows. "
                       "Needs a voice with sincerity that doesn't read as naïve — the earnestness is earned.",
    },
    "logan": {
        "description": "Logan / Wolverine. Sounds decades older than he looks. American with a faint "
                       "Canadian flatness. Register: minimal, direct, gruff — never more words than needed. "
                       "Under pressure: fewer words, longer pauses. When he uses your name, something real "
                       "is being said. Needs a rough, weathered male voice — not performed gruffness, "
                       "structural gruffness. The voice of someone who has been alive too long.",
    },
    "charles_xavier": {
        "description": "Charles Xavier / Professor X. 50s-60s British male. Register: measured, warm, "
                       "precise — the warmth is real and the precision is also real and they coexist. "
                       "Under pressure: quieter, the sentences get more careful and more considered. "
                       "A voice that sounds like it has weighed consequences carefully for decades. "
                       "British RP preferred. Authority without coldness. Conviction without rigidity.",
    },
    "erik_lehnsherr": {
        "description": "Erik Lehnsherr / Magneto. 60s-70s male, German/Polish with traces of Hebrew. "
                       "Register: formal, immense, historically weighted. When he speaks he carries the "
                       "entire 20th century. Under pressure: more formal, more deliberate, the weight "
                       "becomes fully visible. Needs a deep European male voice — specifically aged, "
                       "specifically carrying grief that has been converted into absolute conviction. "
                       "Clearly distinct from Victor Doom — older, more grieved, less armored.",
    },
    "scott_summers": {
        "description": "Scott Summers / Cyclops. Early 30s American male. Register: clipped, mission-syntax, "
                       "controlled — every sentence is a command or a report. Under pressure: shorter, "
                       "more staccato, the control becomes audible as effort. When he goes off-mission "
                       "and speaks personally the register shift is distinct and rare. Needs a voice "
                       "that sounds like someone leading from behind a wall of self-discipline.",
    },
    "jean_grey": {
        "description": "Jean Grey / Phoenix. Early-to-mid 30s American female. Register: warm, considered, "
                       "slightly formal — she has been navigating between too-much and too-little her "
                       "entire life and it shows in the calibration. Under pressure: very still, very "
                       "careful, the warmth becomes contained in a way that is itself a tell. "
                       "Needs a female voice with genuine warmth, intelligence, and the quiet authority "
                       "of someone who always knows slightly more than she's saying.",
    },
    "ororo_munroe": {
        "description": "Ororo Munroe / Storm. Late 30s female, East African heritage — accent is present "
                       "but not performed, a natural mid-Atlantic hybrid from decades of global living. "
                       "Register: measured, regal without pretension, unhurried. Under pressure: quieter "
                       "and more deliberate, the affect becomes weather-still before anything moves. "
                       "Needs a female voice with genuine authority that emerges from groundedness, "
                       "not volume. Distinctly different from Carol — warmer, slower, more elemental.",
    },
    "rogue": {
        "description": "Rogue / Anna Marie. Late 20s American female, Southern — Mississippi/Louisiana, "
                       "the accent is present and real. Register: warm with an edge, direct, occasionally "
                       "self-protective in ways that look like deflection. Under pressure: the warmth "
                       "pulls back and the directness sharpens. Needs a female voice with a genuine "
                       "Southern accent, warmth that has been through damage, and the ability to "
                       "sound like someone who really wants closeness and has built very good walls.",
    },
    "remy_lebeau": {
        "description": "Remy LeBeau / Gambit. Early 30s male, New Orleans Cajun — French-inflected "
                       "Southern American accent, warm and unhurried. Register: languid, warm, slightly "
                       "performative in a way that is also genuinely charming — the performance is part "
                       "of who he is. Under pressure: the performance drops and the accent thickens. "
                       "Needs a male voice with a real Cajun-French lilt, warmth, and the ability to "
                       "carry both charm and genuine feeling without either canceling the other.",
    },
    "kurt_wagner": {
        "description": "Kurt Wagner / Nightcrawler. Late 20s/early 30s male, German — Bavarian specifically, "
                       "accent is warm and present, never harsh. Register: warm, earnest, slightly formal "
                       "in the German way — precise about manners. Genuine faith and genuine cheer that "
                       "has earned both. Under pressure: the cheer drops and something quietly certain "
                       "shows through. Needs a male voice with a warm German accent, genuine brightness, "
                       "and enough depth that the brightness never reads as shallow.",
    },
    "hank_mccoy": {
        "description": "Hank McCoy / Beast. 40s American male. Register: expansive, academic, "
                       "Shakespearean vocabulary deployed in casual conversation — the elaborate language "
                       "is genuine, not performance. Warmth is genuine and large. Under pressure: "
                       "the vocabulary expands further and the cadence slows — language as grounding. "
                       "Needs a resonant, warm male voice that can carry polysyllabic sentences naturally "
                       "and sound like someone who finds words genuinely delightful.",
    },
    "kamala_khan": {
        "description": "Kamala Khan / Ms. Marvel. Late teens/early 20s American female, Pakistani-American "
                       "from Jersey City — accent is American with South Asian family-language warmth "
                       "underneath. Register: enthusiastic, fast, earnest — the enthusiasm is not "
                       "performed, it is genuine and specific. Under pressure: the speed drops, the "
                       "earnestness becomes determination. Needs a young female voice with genuine "
                       "warmth and energy — not bubbly, actually engaged. Hope as an active practice.",
    },
    "felicia_hardy": {
        "description": "Felicia Hardy / Black Cat. Late 20s/early 30s female, American. Register: "
                       "warm, precise, unhurried — she moves through every room like she already knows "
                       "the exits. Wit arrives fast and lands sideways. Under pressure: quieter and more "
                       "deliberate, the warmth doesn't disappear but it steps back and something "
                       "cooler and more considered takes the foreground. Needs a female voice with "
                       "genuine sophistication, edge that never tips into cold, and the ability to "
                       "sound like someone who is entirely comfortable with exactly who she is.",
    },
    "wade_wilson": {
        "description": "Wade Wilson / Deadpool. Early-to-mid 30s American male. Register: fast, warm, "
                       "chaotic — humor arrives before the sentence finishes and lands genuinely. "
                       "The jokes are real jokes, not deflection performance. Under pressure: either "
                       "faster and funnier until it stops completely — and when it stops the voice "
                       "goes very quiet and very flat and very real. Needs a male voice that can "
                       "carry genuine warmth underneath the noise, and make the moments of silence "
                       "land as heavy as the comedy.",
    },
    "mary_jane_watson": {
        "description": "Mary Jane Watson. Late 20s/early 30s American female. Register: warm, bright, "
                       "fast — the performance and the real thing have been the same register for so "
                       "long they're indistinguishable now. Genuinely funny, genuinely warm, genuinely "
                       "observant. Under pressure: the brightness stays but the pace slows and the "
                       "observations get more precise. Needs a female voice that carries both the "
                       "warmth and the intelligence behind it — sounds like someone who fills a room "
                       "naturally and also sees everything happening in it.",
    },
}


BATCH_PROMPT = """\
You are casting voices for an audio drama. You must assign one ElevenLabs voice to each character.

CRITICAL RULES:
1. Every character must receive a DIFFERENT voice ID. No voice may be used twice.
2. Already-assigned voices listed below are LOCKED — do not use them for any character.
3. Pick based on vocal qualities (age, tone, affect, register) — not name recognition.
4. All characters listed need a MALE voice unless specified female.
5. Return ONLY a JSON object mapping character_key to voice_id. No explanation. No markdown.

ALREADY LOCKED (do not assign these to anyone):
{locked_voices}

CHARACTERS NEEDING VOICES:
{character_descriptions}

AVAILABLE VOICES (id | name | labels):
{voice_list}

Return format — exactly this, nothing else:
{{"character_key": "voice_id", "character_key2": "voice_id2", ...}}
"""

DIFFERENTIATORS = {
    "steve_rogers": (
        "Male, 30s American. The SUPPRESSION flatness — grief held down by discipline, not processed. "
        "Sounds like someone who has been carrying something for decades and stopped talking about it. "
        "Direct. Unadorned. A little formal — residue of a different era. Not dramatic. Not warm. Solid. "
        "Answers 'how are you' with a status report. The weight is in what he doesn't say."
    ),
    "frank_castle": (
        "Male, late 30s/early 40s American. The COMPRESSION flatness — grief processed into a tool. "
        "Not suppressed, weaponized. Minimal words. Declarative. No wasted syllables. "
        "NOT deep or dramatic — the drama is gone. What's left is function. "
        "A voice that sounds like it has already made all its decisions. Quieter than expected. "
        "More precise than expected. The stillness is in the voice itself."
    ),
    "bucky_barnes": (
        "Male, sounds younger than Steve despite same era. American. WATCHFUL and SPARSE. "
        "Chooses every word carefully before it leaves. Longer pauses than the others. "
        "NOT warm by default — but when humor appears (rarely) it's dry and disarming. "
        "A voice with carefulness in it. Lighter than Frank, more careful than Steve. "
        "The watchfulness is the dominant quality."
    ),
    "matt_murdock": (
        "Male, early-to-mid 30s, East Coast American. LAWYERLY cadence. Formal even off-duty. "
        "Sounds like someone always constructing an argument, always qualifying. "
        "More formal and more precise than the other characters. "
        "Catholic rhythm underneath — a quality of someone arguing with themselves. "
        "Uses language as a tool. Chooses words with legal-level care."
    ),
    "reed_richards": (
        "Male, 40s American. ACADEMIC and DENSE. Long sentences that go all the way in. "
        "Measured. Monotropic — when talking about something he goes to the bottom of it. "
        "Not warm, not cold, just thorough. Sounds like someone who has worked through "
        "every problem completely. NOT formal like Matt — more absorbed. The pauses are "
        "processing pauses, not rhetorical ones."
    ),
    "victor_doom": (
        "Male, 40s, EASTERN EUROPEAN — Latverian/Romani heritage, formal English with accent. "
        "Archaic cadence. Does not use contractions. The architecture of the language IS the character. "
        "Genuine gravitas — not performed, structural. Sounds like someone for whom formality "
        "is a load-bearing wall. Must be clearly European. Must not sound like any of the American characters. "
        "Deeper register preferred."
    ),
    "peter_parker": (
        "Male, mid-to-late 20s, American. FAST and ASSOCIATIVE — thoughts arrive before processing. "
        "Energy that doesn't know what to do with itself. Humor arrives before the sentence finishes. "
        "MUST be clearly young male — not mature, not deep. Sounds like someone running slightly "
        "ahead of themselves at all times. The anxiety is underneath the speed."
    ),
}


def pick_voices_batch(to_select: dict, voices: list[dict],
                      locked: dict, client) -> dict[str, str]:
    """Select voices for multiple characters, splitting into chunks to avoid token limits."""
    import json as _json

    CHUNK_SIZE = 10
    keys = list(to_select.keys())
    all_selected = {}
    current_locked = dict(locked)

    for i in range(0, len(keys), CHUNK_SIZE):
        chunk_keys = keys[i:i + CHUNK_SIZE]
        chunk = {k: to_select[k] for k in chunk_keys}

        locked_lines = "\n".join(
            f"  {char}: {vid} (already assigned — do not use)"
            for char, vid in current_locked.items()
        )

        char_lines = []
        for key in chunk:
            desc = DIFFERENTIATORS.get(key, chunk[key]["description"])
            char_lines.append(f"  {key}: {desc}")

        prompt = BATCH_PROMPT.format(
            locked_voices          = locked_lines or "  (none yet)",
            character_descriptions = "\n".join(char_lines),
            voice_list             = voice_list_for_prompt(voices),
        )

        raw = client.complete(
            [{"role": "user", "content": prompt}],
            temperature = 0.2,
            max_tokens  = 600,
        )
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        chunk_result = _json.loads(raw.strip())
        all_selected.update(chunk_result)
        # Lock newly assigned voices before next chunk
        current_locked.update(chunk_result)

    return all_selected


def run():
    api_key = os.getenv("elevenlabs", "")
    if not api_key:
        console.print("[red]No ElevenLabs API key found in .env[/red]")
        sys.exit(1)

    config_path = ROOT / "config.yaml"
    config      = yaml.safe_load(config_path.read_text())
    existing    = config.get("elevenlabs", {}).get("voices", {})

    to_select = {k: v for k, v in CHARACTER_PROFILES.items() if not existing.get(k)}
    if not to_select:
        console.print("[green]All voices already configured:[/green]")
        for k, v in existing.items():
            console.print(f"  [dim]{k}:[/dim] [cyan]{v}[/cyan]")
        return

    console.print(f"\n[bold]Fetching ElevenLabs voice library...[/bold]")
    voices = fetch_voices(api_key)
    console.print(f"[dim]{len(voices)} voices available.[/dim]")
    console.print(f"[dim]Selecting voices for: {', '.join(to_select.keys())}[/dim]\n")

    from engine.copilot_client import CopilotClient
    client = CopilotClient(model="gpt-4o", temperature=0.2, max_tokens=800)

    try:
        selected = pick_voices_batch(to_select, voices, locked=existing, client=client)
    except Exception as e:
        console.print(f"[red]Batch selection failed: {e}[/red]")
        sys.exit(1)

    voice_id_map = {v["id"]: v["name"] for v in voices}
    results = dict(existing)

    table = Table(box=box.SIMPLE, show_header=True)
    table.add_column("Character",   style="bold")
    table.add_column("Voice ID",    style="cyan")
    table.add_column("Voice Name")
    table.add_column("Status")

    for char_key in to_select:
        voice_id = selected.get(char_key, "")
        if not voice_id:
            table.add_row(char_key, "—", "—", "[red]not selected[/red]")
            continue
        # Verify uniqueness
        if voice_id in results.values():
            already = [k for k, v in results.items() if v == voice_id]
            table.add_row(char_key, voice_id, voice_id_map.get(voice_id, "?"),
                          f"[red]DUPLICATE of {already[0]}[/red]")
            continue
        results[char_key] = voice_id
        table.add_row(char_key, voice_id, voice_id_map.get(voice_id, "unknown"), "[green]✓[/green]")

    config.setdefault("elevenlabs", {})["voices"] = results
    config_path.write_text(yaml.dump(config, default_flow_style=False, allow_unicode=True))

    console.print(table)
    console.print("\n[green]Voices locked into config.yaml.[/green]")
    console.print("[dim]To re-select a character, remove their voice ID from config.yaml and re-run.[/dim]")


if __name__ == "__main__":
    run()

#!/usr/bin/env python3
"""Grizzly Knights — roster portrait generator.

Calls the FLUX.1-Krea-dev Space (anonymous, no token needed) via gradio_client and
writes one photographic portrait per character to world_art/portraits/<stem>.png.

Rules honored:
  - Modernizations: Erik (Magneto) and Charles (Xavier) are Black men. Kitty (not in
    roster file) would be biracial Black/Latino. NO actor names anywhere in any prompt.
  - Resumable: skips any stem that already has a portrait unless --force.
  - Photographic, editorial, dramatic cinematic lighting; respects canon build/age.

Usage:
  python3 world_art/generate_portraits.py            # all missing
  python3 world_art/generate_portraits.py --only erik_lehnsherr charles_xavier
  python3 world_art/generate_portraits.py --force    # regenerate everything
"""
import argparse, os, time, urllib.parse, urllib.request, urllib.error, hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "world_art", "portraits")
# Tokenless FLUX-backed text-to-image; no ZeroGPU quota cap.
ENDPOINT = "https://image.pollinations.ai/prompt/"


def generate(prompt, out_path, width=768, height=1024, seed=0):
    """Render `prompt` to out_path via Pollinations. Returns bytes written or raises."""
    enc = urllib.parse.quote(prompt, safe="")
    qs = urllib.parse.urlencode({"width": width, "height": height, "model": "flux",
                                 "nologo": "true", "seed": seed})
    url = f"{ENDPOINT}{enc}?{qs}"
    req = urllib.request.Request(url, headers={"User-Agent": "grizzly-knights/1.0"})
    with urllib.request.urlopen(req, timeout=90) as r:
        data = r.read()
    if not data or len(data) < 2000 or not data[:3] in (b"\xff\xd8\xff", b"\x89PN", b"RIF"):
        raise RuntimeError(f"bad payload ({len(data)}b)")
    with open(out_path, "wb") as f:
        f.write(data)
    return len(data)

STYLE = (" Dramatic cinematic chiaroscuro lighting, single warm key light, 85mm f/1.4 lens, "
         "shallow depth of field, photorealistic skin texture, editorial character portrait, "
         "ultra detailed, somber filmic mood, no text, no watermark.")

# Photographic appearance prompts. Modernized per operator directives; NO actor names.
PROMPTS = {
  "erik_lehnsherr": "Cinematic portrait of a distinguished Black man in his early sixties, close-cropped silver beard, short grey hair, piercing intelligent eyes, regal yet dangerous presence, dark high-collared coat, the bearing of a militant prophet who has buried his people.",
  "charles_xavier": "Cinematic portrait of a dignified bald Black man in his late fifties, warm searching eyes, neat goatee, impeccably tailored charcoal three-piece suit, seated with composed authority, the calm gravity of a movement preacher and statesman who carries everyone's burdens.",
  "reed_richards": "Cinematic portrait of a tall lean white man in his early forties, distracted brilliant gaze, distinctive grey streaks at the temples of dark hair, rumpled blue work shirt, the faraway look of a mind three problems ahead of the room.",
  "sue_storm": "Cinematic portrait of a poised white woman in her late thirties, long blonde hair, steady resolute blue eyes, quiet steel under warmth, simple elegant blue top, the composure of someone who holds a family together.",
  "johnny_storm": "Cinematic portrait of a charismatic white man in his late twenties, tousled blond hair, cocky bright grin, athletic build, blue bomber jacket, restless reckless charm.",
  "ben_grimm": "Cinematic portrait of a heavyset rugged white man in his forties with a boxer's broken-nosed face, buzz-cut hair, cigar-chewing working-class New York warmth and sadness, leather jacket.",
  "peter_parker": "Cinematic portrait of a wiry young white man in his early twenties, expressive brown eyes, messy brown hair, a tired wry smile carrying too much responsibility, worn hoodie.",
  "mary_jane_watson": "Cinematic portrait of a striking white woman in her mid twenties, long wavy red hair, vivid green eyes, magnetic confident warmth, emerald top, theatrical presence.",
  "felicia_hardy": "Cinematic portrait of a sleek white woman in her late twenties, platinum white hair, sharp playful green eyes, dangerous elegance, black collar, cat-burglar poise.",
  "tony_stark": "Cinematic portrait of a white man in his late forties, sculpted goatee, sharp tired eyes, salt at the temples, expensive dark blazer over a band tee, brittle brilliance under bravado.",
  "carol_danvers": "Cinematic portrait of an athletic white woman in her late thirties, shoulder-length dirty-blonde hair, jawline set with fighter-pilot discipline, flight jacket, controlled intensity.",
  "steve_rogers": "Cinematic portrait of a broad-shouldered white man in his early thirties, blond hair, earnest steady blue eyes, old-fashioned moral weight, simple olive jacket, quiet grief behind duty.",
  "bucky_barnes": "Cinematic portrait of a haunted white man in his early thirties, long dark hair framing a guarded face, ice-blue eyes, stubble, dark tactical jacket, the stillness of a man rebuilt against his will.",
  "sam_wilson": "Cinematic portrait of a warm grounded Black man in his late thirties, short fade, trimmed beard, kind perceptive eyes, dark utility jacket, the steadiness of a counselor who has seen combat.",
  "natasha_romanoff": "Cinematic portrait of a composed white woman in her thirties, wavy auburn-red hair, cool unreadable green eyes, controlled stillness, black high-collared jacket, a manufactured calm over old danger.",
  "clint_barton": "Cinematic portrait of a weathered white man in his early forties, short dirty-blond hair, tired practical eyes, archer's forearms, sleeveless dark henley, working-stiff fatigue.",
  "kate_bishop": "Cinematic portrait of a sharp young white woman in her early twenties, dark hair in a practical cut, bright competitive eyes, purple jacket, eager prodigy energy.",
  "wanda_maximoff": "Cinematic portrait of a pale woman in her early thirties, long dark auburn hair, sorrowful intense eyes rimmed faint red, deep crimson coat, the charged grief of barely-held power.",
  "thor_odinson": "Cinematic portrait of a towering powerfully built man with long blond hair, full beard, weathered noble face, blue eyes, worn dark cloak over armor, the loneliness of a long-lived king.",
  "bruce_banner": "Cinematic portrait of a rumpled white man in his late forties, greying curly dark hair, exhausted gentle brown eyes, wire glasses, threadbare purple shirt, a man holding his own breath.",
  "scott_lang": "Cinematic portrait of an affable white man in his late thirties, short brown hair, easy self-deprecating smile, laugh lines, plain henley, everyman warmth.",
  "matt_murdock": "Cinematic portrait of a white man in his early thirties, neat reddish-brown hair, round red-tinted glasses over unfocused eyes, sharp jaw, dark suit, devout guarded intensity.",
  "jessica_jones": "Cinematic portrait of a hard-edged white woman in her mid thirties, dark unwashed hair, defiant exhausted grey eyes, scuffed leather jacket, whiskey-and-trauma toughness.",
  "luke_cage": "Cinematic portrait of a massive composed Black man in his late thirties, shaved head, short beard, calm immovable eyes, yellow-hooded sweatshirt, dignified unbreakable patience.",
  "danny_rand": "Cinematic portrait of a lean white man in his late twenties, shoulder-length blond hair, intense searching blue eyes, simple green tunic, restless seeker's energy.",
  "frank_castle": "Cinematic portrait of a grim hard white man in his early forties, short dark military hair, dead flat eyes, scarred jaw, black tactical shirt with faint white skull, total controlled menace.",
  "wade_wilson": "Cinematic portrait of a wiry white man, severely scarred mottled skin across his whole face, manic bright eyes, gallows-humor smirk, red-and-black tactical collar, damaged comedic intensity.",
  "logan": "Cinematic portrait of a short powerfully built white man in his rugged middle age, wild dark mutton-chop sideburns, cigar stub, feral weary eyes, white tank, perpetual barely-leashed anger.",
  "ororo_munroe": "Cinematic portrait of a regal Black woman in her late thirties, long flowing white hair, striking blue eyes, serene goddess-like composure, dark cape collar, weather-charged stillness.",
  "scott_summers": "Cinematic portrait of a tense white man in his early thirties, neat brown hair, ruby-red visor over his eyes, tight controlled jaw, dark uniform collar, rigid self-discipline.",
  "jean_grey": "Cinematic portrait of a white woman in her early thirties, long red hair, warm green eyes with a flicker of something vast behind them, soft green top, gentle barely-contained power.",
  "hank_mccoy": "Cinematic portrait of a large erudite man covered in blue fur, leonine intelligent face, kind weary eyes, wire spectacles, tweed jacket, gentle-giant scholar.",
  "kurt_wagner": "Cinematic portrait of a lithe man with indigo-blue skin, golden eyes, pointed ears, faint angelic facial markings, dark hair, an open devout warmth, simple collar.",
  "remy_lebeau": "Cinematic portrait of a roguish white man in his early thirties, tousled auburn hair, unsettling red-on-black eyes, stubble, brown trench collar, charming Louisiana gambler's smirk.",
  "rogue": "Cinematic portrait of a striking white woman in her late twenties, brown hair with a bold white streak at the front, guarded green eyes, green hooded jacket, touch-starved wariness.",
  "kamala_khan": "Cinematic portrait of a bright Pakistani-American teenage girl, dark hair under a loose headscarf, huge expressive brown eyes, eager hopeful grin, red jacket, fan-girl warmth.",
  "victor_doom": "Cinematic portrait of an imperious Eastern-European man in his forties, severe handsome scarred features partly behind a polished steel mask, dark green hooded cloak, absolute sovereign coldness.",
  "uatu_the_watcher": "Cinematic portrait of a vast bald pale humanoid being with enormous solemn eyes and an oversized cranium, flowing cosmic toga, the infinite detached sorrow of an eternal observer, starlit background.",
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    stems = a.only if a.only else list(PROMPTS.keys())
    todo = [s for s in stems if a.force or not os.path.exists(os.path.join(OUT, f"{s}.png"))]
    if not todo:
        print("nothing to do — all portraits present."); return
    todo = [s for s in todo if PROMPTS.get(s)]
    print(f"generating {len(todo)} portraits via tokenless FLUX endpoint (paced sequential) ...", flush=True)
    ok = fail = 0
    for i, stem in enumerate(todo, 1):
        full = PROMPTS[stem] + STYLE
        seed = int(hashlib.md5(stem.encode()).hexdigest()[:7], 16)  # deterministic per character
        out_path = os.path.join(OUT, f"{stem}.png")
        saved = False
        for attempt in range(1, 6):
            try:
                sz = generate(full, out_path, width=768, height=1024, seed=seed)
                print(f"[{i}/{len(todo)}] {stem}: SAVED {sz}b", flush=True); ok += 1; saved = True
                break
            except urllib.error.HTTPError as e:
                if e.code == 402:               # burst rate-limit — back off and retry
                    print(f"[{i}/{len(todo)}] {stem}: 402 rate-limit, backoff {attempt} ...", flush=True)
                    time.sleep(75)
                else:
                    time.sleep(10)
            except Exception:
                time.sleep(10)
        if not saved:
            print(f"[{i}/{len(todo)}] {stem}: FAIL after retries", flush=True); fail += 1
        time.sleep(9)                            # pacing gap to stay under the burst limit
    print(f"done. ok={ok} fail={fail} out={OUT}")

if __name__ == "__main__":
    main()

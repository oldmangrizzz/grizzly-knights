#!/usr/bin/env python3
"""Grizzly Knights — environment & scene concept art.

Cinematic establishing plates (16:9) for the world bible / Obsidian vault: the world's
locations and a few key emotional beats. Same anonymous FLUX.1-Krea-dev pipeline as the
portrait generator. Written to world_art/scenes/<key>.png.

Tasteful by directive: the racial-terror origin is rendered as a SOMBER, DIGNIFIED,
IMPLIED memorial landscape — never depicting violence, never graphic. NO actor names.

Usage:
  python3 world_art/generate_scenes.py                  # all missing
  python3 world_art/generate_scenes.py --only mansion   # one key
  python3 world_art/generate_scenes.py --force
"""
import argparse, os, time, urllib.parse, urllib.request, urllib.error, hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "world_art", "scenes")
ENDPOINT = "https://image.pollinations.ai/prompt/"


def generate(prompt, out_path, width=1216, height=704, seed=0):
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

STYLE = (" Cinematic establishing shot, atmospheric volumetric light, filmic color grade, "
         "wide-angle, ultra detailed environment concept art, photographic, no text, no watermark.")

PROMPTS = {
  # --- environments / locations ---
  "mansion": "A grand ivy-covered stone academy estate at golden hour, tall windows glowing warm, sweeping green lawn and old oaks, a place of refuge and education, dignified and hopeful.",
  "mansion_interior": "A warm wood-paneled study lined with floor-to-ceiling books, a large globe, a chessboard set by tall windows, afternoon light, the quiet heart of a movement.",
  "lab": "A vast gleaming research laboratory, holographic schematics floating in blue light, towering experimental machinery, polished floors, the workspace of a restless genius.",
  "nyc_street": "A gritty rain-slicked New York City street at night, steam rising from manholes, neon and fire-escape shadows, the territory of street-level guardians.",
  "dive_bar": "A dim battered Hell's Kitchen dive bar at 2am, cracked vinyl booths, a single buzzing neon sign, whiskey-and-regret atmosphere.",
  "memorial_field": "A vast empty Southern field at somber dusk, a single bare tree on the horizon, low golden mist over the grass, an old wooden fence, profound stillness and mourning — a place of remembrance and inherited grief, dignified and quiet.",
  "harlem_street": "A warm vibrant Harlem block at evening, brownstone stoops, a barbershop glow, community and resilience, soft amber streetlight.",
  "cosmic_void": "An infinite starlit cosmic void, vast nebulae and distant galaxies, a lonely watchpoint overlooking all of creation, silent and eternal.",
  "stormy_sky": "A dramatic open sky split by a coming storm, towering thunderheads lit from within by lightning, a lone figure's domain of wind and weather, awe and power.",
  "asgard_realm": "A majestic golden mythic city of spires on a cliff edge above a sea of stars, a rainbow bridge stretching into the cosmos, regal and ancient.",
  "courtroom": "A solemn wood-paneled courtroom, tall arched windows, dust in shafts of light, the weight of justice and law.",
  "rooftop_night": "A city rooftop at night above a glittering skyline, water towers silhouetted, a quiet vantage where a masked guardian watches over the streets below.",
  # --- key scenes (no actor names; relationships per directives) ---
  "chess_brothers": "Two dignified Black men in their fifties and sixties seated across an antique chessboard by a sunlit window, mid-conversation, deep mutual respect and unbridgeable disagreement in their eyes — ideological brothers, warmth and tension held together.",
  "the_reckoning": "An older Black man in a dark coat standing before a young biracial person in a rain-soaked alley, his face breaking with dawning horror and grief as he recognizes what he has helped create — a quiet devastating moment of moral reckoning.",
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    keys = a.only if a.only else list(PROMPTS.keys())
    todo = [k for k in keys if a.force or not os.path.exists(os.path.join(OUT, f"{k}.png"))]
    if not todo:
        print("nothing to do — all scenes present."); return
    print(f"generating {len(todo)} scenes via tokenless FLUX endpoint (paced sequential) ...", flush=True)
    ok = fail = 0
    for i, key in enumerate(todo, 1):
        full = PROMPTS[key] + STYLE
        seed = int(hashlib.md5(key.encode()).hexdigest()[:7], 16)
        out_path = os.path.join(OUT, f"{key}.png")
        saved = False
        for attempt in range(1, 6):
            try:
                sz = generate(full, out_path, width=1216, height=704, seed=seed)
                print(f"[{i}/{len(todo)}] {key}: SAVED {sz}b", flush=True); ok += 1; saved = True
                break
            except urllib.error.HTTPError as e:
                if e.code == 402:
                    print(f"[{i}/{len(todo)}] {key}: 402 rate-limit, backoff {attempt} ...", flush=True)
                    time.sleep(75)
                else:
                    time.sleep(10)
            except Exception:
                time.sleep(10)
        if not saved:
            print(f"[{i}/{len(todo)}] {key}: FAIL after retries", flush=True); fail += 1
        time.sleep(9)
    print(f"done. ok={ok} fail={fail} out={OUT}")

if __name__ == "__main__":
    main()

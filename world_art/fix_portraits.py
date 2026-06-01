#!/usr/bin/env python3
"""Re-roll flagged portraits against the operator-reviewed appearance LOCKS.

For every stem in universe/world/appearance_locks.json, render a corrected portrait
that bakes in the immutable canon identity markers (race, hair color, costume, etc.)
straight into the FLUX prompt — no LLM appearance step that can drift. Overwrites
world_art/portraits/<stem>.png. Paced under Pollinations' burst limit.

Usage:
  python3 world_art/fix_portraits.py            # all locked stems
  python3 world_art/fix_portraits.py tony_stark victor_doom   # just these
"""
import os, sys, json, time, hashlib, urllib.parse, urllib.request, urllib.error
import yaml

ROOT = "/Users/rbhanson/fanfic"
PORT = f"{ROOT}/world_art/portraits"
LOCKS = f"{ROOT}/universe/world/appearance_locks.json"
ENDPOINT = "https://image.pollinations.ai/prompt/"
DEFAULT_SCENE = ("Dramatic cinematic chiaroscuro lighting, single warm key light, 85mm f/1.4 lens, "
                 "shallow depth of field, photorealistic skin texture, editorial character portrait, "
                 "ultra detailed, somber filmic mood, no text, no watermark.")
# things we never want regardless of character — fed to the negative prompt
GLOBAL_NEGATIVE = ("text, watermark, signature, logo, caption, deformed, extra limbs, extra fingers, "
                   "mutated hands, lowres, blurry, jpeg artifacts, frame, border, "
                   "likeness of a specific real-life actor or celebrity, recognizable famous real person")


def display(stem):
    fp = f"{ROOT}/universe/characters/{stem}.yaml"
    try:
        d = yaml.safe_load(open(fp)) or {}
        name = (d.get("name") or stem.replace("_", " ").title()).strip()
        alias = (d.get("alias") or "").strip()
        return f"{name} ({alias})" if alias else name
    except Exception:
        return stem.replace("_", " ").title()


def render(prompt, out_path, seed, w=768, h=1024, negative=""):
    enc = urllib.parse.quote(prompt, safe="")
    params = {"width": w, "height": h, "model": "flux", "nologo": "true", "seed": seed}
    if negative:
        params["negative_prompt"] = negative   # FLUX/pollinations negative guidance
    qs = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"{ENDPOINT}{enc}?{qs}", headers={"User-Agent": "grizzly-knights/1.0"})
    for attempt in range(1, 7):
        try:
            with urllib.request.urlopen(req, timeout=110) as r:
                data = r.read()
            if data and len(data) > 2000 and data[:3] in (b"\xff\xd8\xff", b"\x89PN", b"RIF"):
                open(out_path, "wb").write(data); return len(data)
            raise RuntimeError(f"bad payload {len(data)}b")
        except urllib.error.HTTPError as e:
            time.sleep(75 if e.code == 402 else 10)
        except Exception:
            time.sleep(10)
    return 0


def main():
    locks = json.load(open(LOCKS))
    want = [s for s in sys.argv[1:] if not s.startswith("-")]
    stems = want or [k for k in locks if not k.startswith("_")]
    os.makedirs(PORT, exist_ok=True)
    done = 0
    for stem in stems:
        entry = locks.get(stem)
        if not entry:
            print(f"{stem}: no lock, skip", flush=True); continue
        lock = entry["lock"]
        scene = entry.get("scene", DEFAULT_SCENE)
        # per-character negatives (str or list) + universal junk we never want
        neg = entry.get("negative", "")
        if isinstance(neg, list):
            neg = ", ".join(neg)
        negative = ", ".join(x for x in [neg, GLOBAL_NEGATIVE] if x)
        # identity FIRST and emphatic, then scene/style, then a baked-in exclusion clause
        # (belt-and-suspenders: FLUX honors in-prompt "NOT ..." even when it ignores the param)
        # portrait_prompt override: pure visual description with NO character/actor name —
        # the way to dodge a model's hard actor-prior (e.g. "Tony Stark" always -> one actor).
        override = entry.get("portrait_prompt")
        if override:
            prompt = f"{override} {scene}"
        else:
            prompt = f"{display(stem)}. {lock}. {scene}"
        if neg:
            prompt += f" This is absolutely NOT and must not resemble: {neg}."
        salt = os.environ.get("SEED_SALT", "v2")
        seed = int(hashlib.md5((stem + salt).encode()).hexdigest()[:7], 16)
        sz = render(prompt, f"{PORT}/{stem}.png", seed, negative=negative)
        if sz:
            done += 1; print(f"[{done}] {stem}: FIXED {sz}b", flush=True)
        else:
            print(f"{stem}: render failed", flush=True)
        time.sleep(9)
    print(f"PORTRAIT FIXES DONE ({done}/{len(stems)})", flush=True)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Comic-accuracy repass: re-roll every NON-locked character's portrait toward their
most iconic CANONICAL COMIC-BOOK look (costume, colors, markers) — not a movie version,
no real-actor faces. Operator-reviewed locked characters are left untouched.

A free OpenRouter model writes a comic-accurate appearance prompt from canon + the
character's own dossier note; tokenless FLUX renders it with the global + comic negatives.
Resumable (tracks world_art/portraits/_repassed.txt). Paced under the burst limit.

Usage:
  python3 world_art/comic_repass.py            # all non-locked characters
  python3 world_art/comic_repass.py jean_grey  # just these
  FORCE=1 ... to ignore the resume ledger
"""
import os, sys, glob, time, json, hashlib, urllib.parse, urllib.request, urllib.error
import yaml

ROOT = "/Users/rbhanson/fanfic"
PORT = f"{ROOT}/world_art/portraits"
LOCKS = f"{ROOT}/universe/world/appearance_locks.json"
LEDGER = f"{PORT}/_repassed.txt"
ENDPOINT = "https://image.pollinations.ai/prompt/"
STYLE = (" Dramatic cinematic chiaroscuro lighting, single warm key light, 85mm f/1.4 lens, "
         "shallow depth of field, photorealistic skin texture, editorial character portrait, "
         "ultra detailed, somber filmic mood, no text, no watermark.")
GLOBAL_NEGATIVE = ("text, watermark, signature, logo, caption, deformed, extra limbs, extra fingers, "
                   "mutated hands, lowres, blurry, jpeg artifacts, frame, border, "
                   "movie costume, film adaptation version, off-model, generic superhero, "
                   "likeness of a specific real-life actor or celebrity, recognizable famous real person")
FREE_MODELS = ["meta-llama/llama-3.3-70b-instruct:free", "openai/gpt-oss-120b:free",
               "qwen/qwen3-next-80b-a3b-instruct:free", "google/gemma-4-31b-it:free"]


def _key():
    for line in open(f"{ROOT}/.env"):
        if line.startswith("openrouter_key="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""
KEY = _key()


def locked_stems():
    try:
        return {k for k in json.load(open(LOCKS)) if not k.startswith("_")}
    except Exception:
        return set()


def comic_prompt(name, alias, ctx):
    sysmsg = ("You write ONE photographic portrait prompt (~60 words) depicting a comic-book "
              "character in their MOST ICONIC, CANONICAL COMIC-BOOK appearance and COSTUME — the "
              "classic comics look, NOT a movie or TV adaptation. Include their accurate costume "
              "with correct signature COLORS and emblems, iconic powers/props if any, and EVERY "
              "defining visual marker (non-human SKIN COLOR, hair color, build, mask/helmet). "
              "Civilians get their canonical everyday look. The character must be unmistakably "
              "comic-accurate and on-model. NEVER name or reference any real actor or celebrity; "
              "give an original face. Output ONLY the prompt text.")
    usr = f"Character: {name} ({alias}). Canon note: {ctx[:300]}. Write the comic-accurate portrait prompt."
    body = {"messages": [{"role": "system", "content": sysmsg}, {"role": "user", "content": usr}],
            "max_tokens": 150}
    for m in FREE_MODELS:
        b = dict(body); b["model"] = m
        for _ in range(2):
            try:
                req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",
                    data=json.dumps(b).encode(),
                    headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=60) as r:
                    j = json.load(r)
                msg = j.get("choices", [{}])[0].get("message", {})
                txt = (msg.get("content") or msg.get("reasoning") or "").strip()
                if txt and len(txt) > 25:
                    return txt
            except urllib.error.HTTPError as e:
                if e.code == 429: time.sleep(20)
            except Exception:
                time.sleep(3)
    return None


def render(prompt, out_path, seed, negative):
    enc = urllib.parse.quote(prompt, safe="")
    params = {"width": 768, "height": 1024, "model": "flux", "nologo": "true", "seed": seed,
              "negative_prompt": negative}
    req = urllib.request.Request(f"{ENDPOINT}{enc}?{urllib.parse.urlencode(params)}",
                                 headers={"User-Agent": "grizzly-knights/1.0"})
    for _ in range(6):
        try:
            with urllib.request.urlopen(req, timeout=110) as r:
                data = r.read()
            if data and len(data) > 2000 and data[:3] in (b"\xff\xd8\xff", b"\x89PN", b"RIF"):
                open(out_path, "wb").write(data); return len(data)
        except urllib.error.HTTPError as e:
            time.sleep(75 if e.code == 402 else 10)
        except Exception:
            time.sleep(10)
    return 0


def main():
    os.makedirs(PORT, exist_ok=True)
    locked = locked_stems()
    force = os.environ.get("FORCE")
    done_ledger = set()
    if os.path.exists(LEDGER) and not force:
        done_ledger = set(open(LEDGER).read().split())
    want = [s for s in sys.argv[1:] if not s.startswith("-")]
    if want:
        stems = want
    else:
        stems = sorted(os.path.basename(f)[:-5] for f in glob.glob(f"{ROOT}/universe/characters/*.yaml")
                       if os.path.getsize(f) > 0)
    done = 0
    for stem in stems:
        if stem in locked:
            continue  # operator-reviewed; never touch
        if stem in done_ledger and not want:
            continue
        fp = f"{ROOT}/universe/characters/{stem}.yaml"
        try:
            d = yaml.safe_load(open(fp)) or {}
        except Exception:
            continue
        name = (d.get("name") or stem).strip(); alias = (d.get("alias") or "").strip()
        ctx = (d.get("bottom_line") or "")[:300]
        ap = comic_prompt(name, alias, ctx)
        if not ap:
            print(f"{stem}: no prompt, skip", flush=True); continue
        seed = int(hashlib.md5((stem + "comic").encode()).hexdigest()[:7], 16)
        sz = render(ap + STYLE, f"{PORT}/{stem}.png", seed, GLOBAL_NEGATIVE)
        if sz:
            done += 1
            with open(LEDGER, "a") as L: L.write(stem + "\n")
            print(f"[{done}] {stem}: COMIC {sz}b", flush=True)
        else:
            print(f"{stem}: render failed", flush=True)
        time.sleep(9)
    print(f"COMIC REPASS DONE ({done} re-rolled; {len(locked)} locked chars left untouched)", flush=True)


if __name__ == "__main__":
    main()

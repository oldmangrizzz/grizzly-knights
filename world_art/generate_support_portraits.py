#!/usr/bin/env python3
"""Auto-portraits for the supporting cast.

For every character yaml that lacks a portrait, a FREE OpenRouter model writes a
photographic appearance prompt from canon (no actor likenesses), then the same
tokenless Pollinations/FLUX pipeline renders world_art/portraits/<stem>.png — matching
the principals' look. Resumable; runs alongside the engine populate.
"""
import os, glob, time, urllib.parse, urllib.request, urllib.error, json, hashlib
import yaml

ROOT = "/Users/rbhanson/fanfic"
PORT = f"{ROOT}/world_art/portraits"
ENDPOINT = "https://image.pollinations.ai/prompt/"
STYLE = (" Dramatic cinematic chiaroscuro lighting, single warm key light, 85mm f/1.4 lens, "
         "shallow depth of field, photorealistic skin texture, editorial character portrait, "
         "ultra detailed, somber filmic mood, no text, no watermark.")
FREE_MODELS = ["meta-llama/llama-3.3-70b-instruct:free", "openai/gpt-oss-120b:free",
               "google/gemma-4-31b-it:free", "qwen/qwen3-next-80b-a3b-instruct:free"]

def _key():
    for line in open(f"{ROOT}/.env"):
        if line.startswith("openrouter_key="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""
KEY = _key()

def appearance_prompt(name, alias, ctx):
    sys = ("You write ONE concise photographic portrait prompt (~45 words) for image generation. "
           "Describe the Marvel character's canonical physical appearance only: age, race, build, hair, "
           "distinguishing features, typical attire. NEVER name or reference any real actor. "
           "Output ONLY the prompt text, no preamble.")
    usr = f"Character: {name} ({alias}). Profile note: {ctx[:280]}. Write the portrait prompt."
    body = json.dumps({"messages": [{"role": "system", "content": sys}, {"role": "user", "content": usr}],
                       "max_tokens": 130}).encode()
    for m in FREE_MODELS:
        b = json.loads(body); b["model"] = m; raw = json.dumps(b).encode()
        for attempt in range(2):
            try:
                req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=raw,
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

def render(prompt, out_path, seed):
    enc = urllib.parse.quote(prompt, safe="")
    qs = urllib.parse.urlencode({"width": 768, "height": 1024, "model": "flux", "nologo": "true", "seed": seed})
    url = f"{ENDPOINT}{enc}?{qs}"
    req = urllib.request.Request(url, headers={"User-Agent": "grizzly-knights/1.0"})
    with urllib.request.urlopen(req, timeout=90) as r:
        data = r.read()
    if not data or len(data) < 2000 or data[:3] not in (b"\xff\xd8\xff", b"\x89PN", b"RIF"):
        raise RuntimeError(f"bad payload ({len(data)}b)")
    open(out_path, "wb").write(data)
    return len(data)

def main():
    os.makedirs(PORT, exist_ok=True)
    done = 0
    # keep sweeping until the engine populate has finished AND every profile has a portrait
    import subprocess
    while True:
        todo = []
        for fp in sorted(glob.glob(f"{ROOT}/universe/characters/*.yaml")):
            stem = os.path.basename(fp)[:-5]
            if os.path.exists(f"{PORT}/{stem}.png"): continue
            if os.path.getsize(fp) == 0: continue
            todo.append((stem, fp))
        for stem, fp in todo:
            try:
                d = yaml.safe_load(open(fp)) or {}
            except Exception:
                continue
            name = (d.get("name") or stem).strip(); alias = (d.get("alias") or "").strip()
            ctx = (d.get("bottom_line") or "")[:280]
            ap = appearance_prompt(name, alias, ctx)
            if not ap:
                print(f"{stem}: no appearance prompt, skip", flush=True); continue
            seed = int(hashlib.md5(stem.encode()).hexdigest()[:7], 16)
            for attempt in range(1, 6):
                try:
                    sz = render(ap + STYLE, f"{PORT}/{stem}.png", seed)
                    done += 1; print(f"[{done}] {stem}: PORTRAIT {sz}b", flush=True); break
                except urllib.error.HTTPError as e:
                    if e.code == 402:
                        print(f"{stem}: 402 backoff", flush=True); time.sleep(75)
                    else: time.sleep(10)
                except Exception:
                    time.sleep(10)
            time.sleep(9)  # pace under the burst limit
        # stop once populate is finished and nothing is left
        populating = subprocess.run(["pgrep", "-f", "populate.py"], capture_output=True).returncode == 0
        if not populating and not todo:
            print(f"SUPPORT PORTRAITS COMPLETE ({done} rendered)", flush=True); break
        time.sleep(30)

if __name__ == "__main__":
    main()

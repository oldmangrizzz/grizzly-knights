#!/usr/bin/env python3
"""Roster -> costumed 3D meshes. The proven, free, reliable path.

For each character: a FREE OpenRouter model writes a BRIGHT, EVENLY-LIT, FULL-BODY
neutral-standing reference prompt from canon (identity markers mandated) -> Pollinations
FLUX renders it on a plain light background -> the real microsoft/TRELLIS (live HF Space,
our HF Pro token for quota) turns it into a textured GLB -> world_view/assets/<stem>.glb.

Bright/even input = bright texture bake = "comic came to life", not a dark blob.
Majors first, resumable, paced for the shared HF GPU. Run in background.
"""
import os, sys, glob, time, json, hashlib, urllib.parse, urllib.request, urllib.error, shutil
import yaml

ROOT = "/Users/rbhanson/fanfic"
REF = f"{ROOT}/world_art/mesh_refs"      # the bright full-body inputs
OUT = f"{ROOT}/world_view/assets"        # the GLB meshes
SPACE = "trellis-community/TRELLIS"
POLL = "https://image.pollinations.ai/prompt/"
FREE_MODELS = ["meta-llama/llama-3.3-70b-instruct:free", "openai/gpt-oss-120b:free",
               "qwen/qwen3-next-80b-a3b-instruct:free", "google/gemma-4-31b-it:free"]
# even, bright, neutral — the opposite of the dramatic portrait style, for clean 3D
STYLE = (" Full body visible head to toe, neutral standing A-pose, arms slightly away from body, "
         "facing camera, centered, plain seamless light-grey studio background, soft even "
         "high-key studio lighting, no harsh shadows, bright, sharp focus, full costume clearly "
         "lit, vivid colors, photoreal, no text, no watermark, no cropping.")

PRIORITY = ["erik_lehnsherr", "charles_xavier", "apocalypse", "carol_danvers", "bruce_banner",
            "wanda_maximoff", "natasha_romanoff", "thanos", "gamora", "peter_quill",
            "ben_grimm", "steve_rogers", "tony_stark", "thor_odinson", "loki"]


def key():
    for line in open(f"{ROOT}/.env"):
        if line.startswith("openrouter_key="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""
KEY = key()


def ref_prompt(name, alias, ctx):
    sys_p = ("You write ONE photographic FULL-BODY character-reference prompt (~55 words) for a "
             "comic-book character, for 3D reconstruction. MANDATORY: the WHOLE body head-to-toe, "
             "neutral standing pose, AND every defining visual marker that makes them instantly "
             "recognizable — especially non-human SKIN COLOR (blue, grey, red, green), signature "
             "helmet/mask/costume, build, and distinguishing features. Unmistakable. NEVER name a "
             "real actor. Output ONLY the prompt text, no preamble.")
    usr = f"Character: {name} ({alias}). Note: {ctx[:280]}. Write the full-body reference prompt."
    body = {"messages": [{"role": "system", "content": sys_p}, {"role": "user", "content": usr}],
            "max_tokens": 140}
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


def render_ref(prompt, out_path, seed):
    enc = urllib.parse.quote(prompt, safe="")
    qs = urllib.parse.urlencode({"width": 768, "height": 1024, "model": "flux",
                                 "nologo": "true", "seed": seed})
    req = urllib.request.Request(f"{POLL}{enc}?{qs}", headers={"User-Agent": "grizzly-knights/1.0"})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                data = r.read()
            if data and len(data) > 2000 and data[:3] in (b"\xff\xd8\xff", b"\x89PN", b"RIF"):
                open(out_path, "wb").write(data); return True
        except urllib.error.HTTPError as e:
            time.sleep(75 if e.code == 402 else 10)
        except Exception:
            time.sleep(10)
    return False


def make_mesh(ref_path, stem, client):
    from gradio_client import handle_file
    try:
        client.predict(api_name="/start_session")
    except Exception:
        pass
    pre = client.predict(image=handle_file(ref_path), api_name="/preprocess_image")
    pre_path = pre["path"] if isinstance(pre, dict) else pre
    res = client.predict(
        image=handle_file(pre_path), multiimages=[], seed=0,
        ss_guidance_strength=7.5, ss_sampling_steps=12,
        slat_guidance_strength=3.0, slat_sampling_steps=12,
        multiimage_algo="stochastic", mesh_simplify=0.95, texture_size=1024,
        api_name="/generate_and_extract_glb")
    for item in (res if isinstance(res, (list, tuple)) else [res]):
        p = item.get("path") if isinstance(item, dict) else item
        if isinstance(p, str) and p.endswith(".glb"):
            shutil.copy(p, f"{OUT}/{stem}.glb")
            return os.path.getsize(f"{OUT}/{stem}.glb")
    return 0


def roster():
    items = []
    for fp in glob.glob(f"{ROOT}/universe/characters/*.yaml"):
        if os.path.getsize(fp) == 0: continue
        items.append((os.path.basename(fp)[:-5], fp))
    rank = {s: i for i, s in enumerate(PRIORITY)}
    items.sort(key=lambda t: (rank.get(t[0], 999), t[0]))
    return items


def main():
    os.makedirs(REF, exist_ok=True); os.makedirs(OUT, exist_ok=True)
    from gradio_client import Client
    client = Client(SPACE)
    print(f"connected {SPACE}", flush=True)
    done = 0
    for stem, fp in roster():
        glb = f"{OUT}/{stem}.glb"
        if os.path.exists(glb) and os.path.getsize(glb) > 200000:
            continue
        try:
            d = yaml.safe_load(open(fp)) or {}
        except Exception:
            continue
        name = (d.get("name") or stem).strip(); alias = (d.get("alias") or "").strip()
        ctx = (d.get("bottom_line") or "")[:280]
        ref = f"{REF}/{stem}.png"
        if not os.path.exists(ref):
            ap = ref_prompt(name, alias, ctx)
            if not ap:
                print(f"{stem}: no ref prompt, skip", flush=True); continue
            seed = int(hashlib.md5(stem.encode()).hexdigest()[:7], 16)
            if not render_ref(ap + STYLE, ref, seed):
                print(f"{stem}: ref render failed, skip", flush=True); continue
        try:
            sz = make_mesh(ref, stem, client)
            if sz:
                done += 1; print(f"[{done}] {stem}: MESH {sz}b", flush=True)
            else:
                print(f"{stem}: no glb returned", flush=True)
        except Exception as e:
            print(f"{stem}: TRELLIS err {repr(e)[:140]}", flush=True)
            time.sleep(20)
        time.sleep(6)
    print(f"MESH PIPELINE PASS DONE ({done} new meshes)", flush=True)


if __name__ == "__main__":
    main()

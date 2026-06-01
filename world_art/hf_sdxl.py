#!/usr/bin/env python3
"""Portrait generation via HF SDXL (hysts/SDXL Space) — REAL positive + negative prompts.

Pollinations FLUX silently ignores negative_prompt; SDXL honors it. This reads the
appearance LOCKS (positive + negative) and regenerates portraits where the negative
actually constrains the result. HF Pro token for quota.

Usage: python3 world_art/hf_sdxl.py <stem> [<stem> ...]
"""
import os, sys, json, time, hashlib, shutil
ROOT = "/Users/rbhanson/fanfic"
PORT = f"{ROOT}/world_art/portraits"
LOCKS = f"{ROOT}/universe/world/appearance_locks.json"
SPACE = "hysts/SDXL"
GLOBAL_NEG = ("illustration, drawing, painting, line art, sketch, cartoon, anime, comic panel, poster, "
              "art nouveau, vintage poster, engraving, woodcut, flat colors, 2d, cel shading, "
              "lowres, blurry, deformed, extra limbs, extra fingers, mutated hands, bad anatomy, "
              "text, watermark, signature, logo, jpeg artifacts, frame, border, "
              "likeness of a specific real-life actor or celebrity")
STYLE = (" Photorealistic color PHOTOGRAPH, shot on a DSLR, 85mm f/1.4 lens, realistic skin texture, "
         "cinematic dramatic lighting, shallow depth of field, hyperrealistic, sharp focus, "
         "professional photography — a real photo, NOT an illustration or drawing.")

import yaml
def disp(stem):
    try:
        d = yaml.safe_load(open(f"{ROOT}/universe/characters/{stem}.yaml")) or {}
        n, a = (d.get("name") or stem).strip(), (d.get("alias") or "").strip()
        return f"{n} ({a})" if a else n
    except Exception:
        return stem.replace("_", " ").title()

def main():
    locks = json.load(open(LOCKS))
    stems = [s for s in sys.argv[1:] if not s.startswith("-")]
    from gradio_client import Client
    c = Client(SPACE)
    print(f"connected {SPACE}", flush=True)
    done = 0
    for stem in stems:
        e = locks.get(stem)
        if not (isinstance(e, dict) and e.get("lock")):
            print(f"{stem}: no lock, skip", flush=True); continue
        # portrait_prompt override (nameless, to dodge actor-priors like RDJ) wins for the positive
        if e.get("portrait_prompt"):
            pos = f"{e['portrait_prompt']}{STYLE}"
        else:
            pos = f"{disp(stem)}. {e['lock']}.{STYLE}"
        neg = e.get("negative", "")
        if isinstance(neg, list): neg = ", ".join(neg)
        neg = ", ".join(x for x in [neg, GLOBAL_NEG] if x)
        salt = os.environ.get("SEED_SALT", "sdxl")
        seed = int(hashlib.md5((stem + salt).encode()).hexdigest()[:7], 16) % 2147483647
        for attempt in range(3):
            try:
                res = c.predict(
                    prompt=pos[:1500], negative_prompt=neg[:900],
                    prompt_2="", negative_prompt_2="",
                    use_negative_prompt=True, use_prompt_2=False, use_negative_prompt_2=False,
                    seed=seed, width=768, height=1024,
                    guidance_scale_base=6.5, guidance_scale_refiner=5.0,
                    num_inference_steps_base=32, num_inference_steps_refiner=18,
                    apply_refiner=True, api_name="/predict")
                src = res["path"] if isinstance(res, dict) else res
                if isinstance(src, str) and os.path.exists(src):
                    shutil.copy(src, f"{PORT}/{stem}.png")
                    done += 1
                    print(f"[{done}] {stem}: SDXL {os.path.getsize(f'{PORT}/{stem}.png')}b (neg honored)", flush=True)
                    break
            except Exception as ex:
                print(f"{stem}: attempt {attempt} {repr(ex)[:110]}", flush=True); time.sleep(8)
        time.sleep(1)
    print(f"SDXL DONE ({done}/{len(stems)})", flush=True)

if __name__ == "__main__":
    main()

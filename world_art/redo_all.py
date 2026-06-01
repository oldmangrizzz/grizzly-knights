#!/usr/bin/env python3
"""Full-roster portrait redo on FLUX.1-dev via HF Pro (Inference Providers). Photoreal, top quality.

- LOCKED character   -> operator-reviewed lock (or its no-name portrait_prompt, e.g. Tony -> dodge RDJ).
- UNLOCKED character -> GPT-4o (Copilot Pro+, knows the canon) writes a concise photoreal prompt; cached.
Every existing portrait is BACKED UP first (world_art/_portrait_bak). Resumable via a ledger.
FLUX has no negative prompt, so identity exclusions are baked into the positive.

  python3 world_art/redo_all.py            # all (resumes)
  FORCE=1 ... to ignore the resume ledger
  python3 world_art/redo_all.py stem ...    # only these
"""
import os, sys, json, time, shutil, urllib.request
import yaml

ROOT = "/Users/rbhanson/fanfic"
PORT = f"{ROOT}/world_art/portraits"
BAK = f"{ROOT}/world_art/_portrait_bak"
LOCKS = f"{ROOT}/universe/world/appearance_locks.json"
PROMPTS = f"{ROOT}/recovery_research/_sdxl_prompts.json"
LEDGER = f"{ROOT}/world_art/portraits/_redone.txt"
OLLAMA = "http://localhost:11434/api/chat"
MODEL = "black-forest-labs/FLUX.1-dev"
STYLE = (", photorealistic color photograph, 85mm portrait, realistic skin texture, cinematic "
         "dramatic lighting, shallow depth of field, ultra detailed, sharp focus, vertical portrait")

def tok():
    return open(os.path.expanduser("~/.cache/huggingface/token")).read().strip()

def disp(stem):
    try:
        d = yaml.safe_load(open(f"{ROOT}/universe/characters/{stem}.yaml")) or {}
        n, a = (d.get("name") or stem).strip(), (d.get("alias") or "").strip()
        return f"{n} ({a})" if a else n
    except Exception:
        return stem.replace("_", " ").title()

def gpt4o(messages, mt=140):  # name kept; runs on Ollama Cloud (kimi), NOT OpenAI
    sysm=[m["content"] for m in messages if m["role"]=="system"]
    usr=[m["content"] for m in messages if m["role"]=="user"]
    body = json.dumps({"model":"kimi-k2.6:cloud","stream":False,"options":{"num_predict":mt,"temperature":0.3},
        "messages":[{"role":"system","content":sysm[0] if sysm else ""},{"role":"user","content":usr[0]}]}).encode()
    req = urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return (json.load(r).get("message",{}).get("content") or "").strip()

def canon_prompt(stem, pcache):
    if stem in pcache:
        return pcache[stem]
    try:
        out = gpt4o([{"role": "system", "content":
            "Write ONE concise (~40 words) photo-first description of a comic character's CANONICAL "
            "appearance for a photorealistic portrait: gender, race/skin tone, hair, build, and "
            "signature costume/markers/powers. Plain descriptive phrases, no preamble."},
            {"role": "user", "content": f"Character: {disp(stem)}. Appearance:"}], 130)
        if out:
            pcache[stem] = out; json.dump(pcache, open(PROMPTS, "w"), indent=1)
            return out
    except Exception as e:
        print(f"  {stem}: prompt gen failed {repr(e)[:60]}", flush=True)
    return None

def main():
    locks = json.load(open(LOCKS))
    pcache = json.load(open(PROMPTS)) if os.path.exists(PROMPTS) else {}
    want = [a for a in sys.argv[1:] if not a.startswith("-")]
    ledger = set(open(LEDGER).read().split()) if (os.path.exists(LEDGER) and not os.environ.get("FORCE")) else set()
    import glob
    stems = want or sorted(os.path.basename(f)[:-4] for f in glob.glob(f"{PORT}/*.png"))
    os.makedirs(BAK, exist_ok=True)
    from huggingface_hub import InferenceClient
    cli = InferenceClient(provider="auto", api_key=tok())
    done = 0; total = len([s for s in stems if s not in ledger])
    print(f"FLUX redo: {total} portraits", flush=True)
    for stem in stems:
        if stem in ledger and not want:
            continue
        e = locks.get(stem)
        if isinstance(e, dict) and e.get("lock"):
            core = e["lock"] if e.get("no_name") else f"{disp(stem)} — {e['lock']}"
            # fold the most important negatives into the positive (FLUX has no neg prompt)
            neg = e.get("negative", "")
            if isinstance(neg, list): neg = ", ".join(neg)
        else:
            core = canon_prompt(stem, pcache)
            if not core:
                print(f"{stem}: no prompt, skip", flush=True); continue
        prompt = f"A photorealistic portrait of {core}{STYLE}"
        if os.path.exists(f"{PORT}/{stem}.png"):
            shutil.copy(f"{PORT}/{stem}.png", f"{BAK}/{stem}.png")
        ok = False
        for attempt in range(4):
            try:
                img = cli.text_to_image(prompt[:1800], model=MODEL, width=768, height=1024)
                img.save(f"{PORT}/{stem}.png")
                ok = True; break
            except Exception as ex:
                print(f"  {stem}: attempt {attempt} {repr(ex)[:90]}", flush=True); time.sleep(10)
        if ok:
            done += 1
            with open(LEDGER, "a") as L: L.write(stem + "\n")
            print(f"[{done}/{total}] {stem}: FLUX ok", flush=True)
        time.sleep(0.3)
    print(f"REDO DONE ({done})", flush=True)

if __name__ == "__main__":
    main()

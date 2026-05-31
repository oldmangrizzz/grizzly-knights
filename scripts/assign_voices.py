#!/usr/bin/env python3
"""Match each character to an ElevenLabs voice that fits their profile's `voice` register.

A free model reads the character's voice description + the available ElevenLabs voices (with
gender/age/accent labels) and picks the best fit. Writes world_view/voice_map.json:
  { stem: {"voice_id": "...", "voice_name": "..."} }
Resumable; the Station's /api/speak reads this to voice each line on demand.
"""
import os, glob, json, time, urllib.request, urllib.error
import yaml

ROOT = "/Users/rbhanson/fanfic"
MAP = f"{ROOT}/world_view/voice_map.json"

def env(k):
    for line in open(f"{ROOT}/.env"):
        if line.startswith(k + "="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""
EL_KEY = env("elevenlabs"); OR_KEY = env("openrouter_key")
FREE = ["meta-llama/llama-3.3-70b-instruct:free", "openai/gpt-oss-120b:free", "google/gemma-4-31b-it:free"]

def voices():
    req = urllib.request.Request("https://api.elevenlabs.io/v1/voices", headers={"xi-api-key": EL_KEY})
    with urllib.request.urlopen(req, timeout=20) as r:
        vs = json.load(r).get("voices", [])
    out = []
    for v in vs:
        lab = v.get("labels", {}) or {}
        out.append({"id": v["voice_id"], "name": v.get("name", ""),
                    "desc": f"{lab.get('gender','')}/{lab.get('age','')}/{lab.get('accent','')}/{lab.get('description','')}"})
    return out

def pick(char_voice, name, alias, vlist):
    catalog = "\n".join(f"{i}. {v['name']} [{v['desc']}]" for i, v in enumerate(vlist))
    sysmsg = "You cast voices. Pick the single best-fitting voice index for a character. Output ONLY the integer index."
    usr = (f"Character: {name} ({alias}). Voice register: {char_voice[:400]}\n\nAvailable voices:\n{catalog}\n\n"
           "Output only the index number of the best match.")
    body = json.dumps({"messages": [{"role": "system", "content": sysmsg}, {"role": "user", "content": usr}],
                       "max_tokens": 8}).encode()
    for m in FREE:
        b = json.loads(body); b["model"] = m
        try:
            req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(b).encode(),
                headers={"Authorization": "Bearer " + OR_KEY, "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=45) as r:
                txt = (json.load(r).get("choices", [{}])[0].get("message", {}).get("content") or "")
            import re
            mm = re.search(r"\d+", txt)
            if mm:
                idx = int(mm.group()) % len(vlist)
                return vlist[idx]
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(15)
        except Exception:
            pass
    return None

def main():
    vlist = voices()
    print(f"{len(vlist)} ElevenLabs voices loaded")
    vm = json.load(open(MAP)) if os.path.exists(MAP) else {}
    while True:
        todo = []
        for fp in sorted(glob.glob(f"{ROOT}/universe/characters/*.yaml")):
            stem = os.path.basename(fp)[:-5]
            if stem in vm or os.path.getsize(fp) == 0:
                continue
            todo.append((stem, fp))
        for stem, fp in todo:
            try: d = yaml.safe_load(open(fp)) or {}
            except Exception: continue
            cv = d.get("voice")
            cv = json.dumps(cv) if isinstance(cv, dict) else str(cv or "")
            pickv = pick(cv, d.get("name", stem), d.get("alias", ""), vlist)
            if pickv:
                vm[stem] = {"voice_id": pickv["id"], "voice_name": pickv["name"]}
                json.dump(vm, open(MAP, "w"), indent=2)
                print(f"{stem} -> {pickv['name']}", flush=True)
            time.sleep(1)
        import subprocess
        if subprocess.run(["pgrep", "-f", "full_depth_populate"], capture_output=True).returncode != 0 and not todo:
            print(f"VOICE MAP COMPLETE ({len(vm)} assigned)", flush=True); break
        time.sleep(30)

if __name__ == "__main__":
    main()

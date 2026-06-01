#!/usr/bin/env python3
"""Mine each character's dossier for a FULL LIFE: character-true activities, a home turf,
and the haunts they frequent. The engine's 90k-word profiles drive behavior, not a stub.

Output: universe/world/agent_lives.json keyed by display name ->
  { home:{x,y}, haunts:[{x,y,name}], activities:[{description,emoji,duration}] }
Resumable. Free OpenRouter models.  Usage: python3 world_art/generate_lives.py [stem...]
"""
import os, sys, json, glob, time, re, hashlib, urllib.request, urllib.error
import yaml

ROOT = "/Users/rbhanson/fanfic"
OUT = f"{ROOT}/universe/world/agent_lives.json"
GEO = f"{ROOT}/universe/world/geography.json"
W, H = 64, 48
# district centers on the sim grid (matches the world renderer)
DCENT = {
    "Hell's Kitchen": (18, 20), "Harlem": (46, 12), "Chinatown / Lower Manhattan": (30, 38),
    "Brooklyn": (50, 40), "Queens (Forest Hills)": (56, 30), "Midtown / Manhattan core": (32, 24),
    "Greenwich Village": (22, 32), "Westchester (greater NYC)": (12, 8),
    "The shadow city (mobile / supernatural)": (8, 44),
}
FREE_MODELS = ["meta-llama/llama-3.3-70b-instruct:free", "openai/gpt-oss-120b:free",
               "qwen/qwen3-next-80b-a3b-instruct:free", "google/gemma-4-31b-it:free"]


def key():
    for l in open(f"{ROOT}/.env"):
        if l.startswith("openrouter_key="):
            return l.split("=", 1)[1].strip().strip('"').strip("'")
    return ""
KEY = key()


def jitter(cx, cy, stem, salt):
    h = int(hashlib.md5((stem + salt).encode()).hexdigest()[:8], 16)
    dx = (h % 9) - 4
    dy = ((h >> 8) % 9) - 4
    return (max(1, min(W - 2, cx + dx)), max(1, min(H - 2, cy + dy)))


def geo_maps():
    g = json.load(open(GEO))
    stem_district, district_landmarks = {}, {}
    for d in g["districts"]:
        district_landmarks[d["name"]] = d.get("landmarks", [])
        for s in d["characters"]:
            stem_district[s] = d["name"]
    return stem_district, district_landmarks


def llm_life(name, alias, dossier_excerpt):
    sysmsg = (
        "You are profiling a comic-book character to drive their day-to-day behavior in a living "
        "city simulation. From the dossier excerpt, output STRICT JSON (no prose) with one key "
        "'activities': an array of EXACTLY 12 short, present-tense, deeply in-character things "
        "THIS specific character actually does day-to-day (not generic). Each item: "
        "{\"description\":\"<6-9 word present-tense phrase>\",\"emoji\":\"<one emoji>\",\"seconds\":<8-25>}. "
        "Make them specific to their powers, role, trauma, and habits — heroes patrol/train/work, "
        "villains plot/recruit/menace, civilians do their jobs. Vivid and true. JSON only."
    )
    usr = f"Character: {name} ({alias}).\nDossier excerpt:\n{dossier_excerpt[:2200]}\n\nReturn the JSON."
    for m in FREE_MODELS:
        body = json.dumps({"model": m, "messages": [{"role": "system", "content": sysmsg},
                           {"role": "user", "content": usr}], "max_tokens": 700}).encode()
        for _ in range(2):
            try:
                req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=body,
                    headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=70) as r:
                    j = json.load(r)
                txt = (j["choices"][0]["message"].get("content") or
                       j["choices"][0]["message"].get("reasoning") or "")
                mt = re.search(r"\{.*\}", txt, re.S)
                if not mt:
                    continue
                acts = json.loads(mt.group(0)).get("activities", [])
                out = []
                for a in acts:
                    desc = str(a.get("description", "")).strip()
                    if not desc:
                        continue
                    out.append({"description": desc[:60],
                                "emoji": (a.get("emoji") or "•")[:4],
                                "duration": int(max(6, min(30, a.get("seconds", 14)))) * 1000})
                if len(out) >= 6:
                    return out
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    time.sleep(20)
            except Exception:
                time.sleep(3)
    return None


def main():
    stem_district, district_landmarks = geo_maps()
    out = json.load(open(OUT)) if os.path.exists(OUT) else {}
    want = sys.argv[1:]
    stems = want or sorted(os.path.basename(f)[:-3] for f in glob.glob(f"{ROOT}/recovery_research/_dossiers/*.md"))
    done = 0
    for stem in stems:
        yp = f"{ROOT}/universe/characters/{stem}.yaml"
        dp = f"{ROOT}/recovery_research/_dossiers/{stem}.md"
        if not os.path.exists(yp) or not os.path.exists(dp):
            continue
        d = yaml.safe_load(open(yp)) or {}
        name = (d.get("name") or stem).strip()
        alias = (d.get("alias") or "").strip()
        disp = f"{name} ({alias})" if alias else name
        if disp in out and not want:
            continue
        district = stem_district.get(stem, "Midtown / Manhattan core")
        cx, cy = DCENT.get(district, (32, 24))
        home = {"x": cx, "y": cy}
        # haunts: this district's landmarks, scattered around the district center
        haunts = []
        for i, lm in enumerate((district_landmarks.get(district) or [])[:4]):
            hx, hy = jitter(cx, cy, stem, f"h{i}")
            haunts.append({"x": hx, "y": hy, "name": lm})
        if not haunts:
            hx, hy = jitter(cx, cy, stem, "h0"); haunts = [{"x": hx, "y": hy, "name": district}]
        # activities from the dossier
        doss = open(dp, encoding="utf-8").read()
        excerpt = doss[:2400]
        acts = llm_life(name, alias, excerpt)
        if not acts:
            print(f"{stem}: no activities, skip", flush=True); continue
        out[disp] = {"home": home, "district": district, "haunts": haunts, "activities": acts}
        json.dump(out, open(OUT, "w"), indent=1, ensure_ascii=False)
        done += 1
        print(f"[{done}] {disp}: {len(acts)} activities, {len(haunts)} haunts @ {district}", flush=True)
        time.sleep(1)
    print(f"LIVES DONE ({done} written; {len(out)} total)", flush=True)


if __name__ == "__main__":
    main()

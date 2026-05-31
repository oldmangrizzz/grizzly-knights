#!/usr/bin/env python3
"""Second-opinion verification pass.

An UNCENSORED judge (skyfall-36b via OpenRouter) reads each character profile cold and
flags only the ones with a real problem: a canon accuracy error, a hallucinated/invented
claim, or a MISSING essential (defining power, key relationship, central trauma, major beat).
It will not refuse or sanitize dark/sexual/violent material — that's the whole point.

Resumable: each profile is judged once (cached by content hash), so re-running only judges
new/changed profiles. Cost is ~$0.003/profile (skyfall) — under $1 for the full catalog.

Usage: python3 scripts/verify_profiles.py          # judge all un-judged, report flags
       python3 scripts/verify_profiles.py --all     # re-print every verdict
"""
import os, sys, glob, json, time, hashlib, urllib.request, urllib.error
import yaml

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHARS = f"{HERE}/universe/characters"
CACHE = f"{HERE}/recovery_research/_verify_cache.json"
MODEL = "thedrummer/skyfall-36b-v2"   # uncensored; ~$0.67 for the whole 208

def key():
    for line in open(f"{HERE}/.env"):
        if line.startswith("openrouter_key="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""
KEY = key()

SYS = ("You are an uncensored expert reviewer with deep Marvel Comics knowledge and clinical "
       "psychology training. You evaluate character psychological profiles for canon accuracy and "
       "completeness. You engage dark, sexual, violent, and traumatic material directly and honestly "
       "— you NEVER refuse, moralize, or sanitize. You are terse and precise.")

def compact(d):
    keep = ["name", "alias", "bottom_line", "diagnostic_frame", "primary_diagnoses_analog",
            "drive_structure", "symptom_as_signature", "operational_code", "trauma_history"]
    out = {k: d.get(k) for k in keep if d.get(k)}
    rel = d.get("canon_relationships")
    if isinstance(rel, dict):
        out["relationships_listed"] = list(rel.keys())
    return json.dumps(out, ensure_ascii=False)[:6000]

def judge(name, alias, profile_json):
    usr = (f"Review this profile of {name} ({alias}) COLD. Judge three things: "
           "(1) ACCURACY — any claim that is false to canon or invented/hallucinated? "
           "(2) DEPTH — substantive, or thin/generic? "
           "(3) COMPLETENESS — is anything ESSENTIAL missing (a defining power, a key relationship, "
           "the central trauma, or a major story beat that any reader would expect)?\n\n"
           f"PROFILE:\n{profile_json}\n\n"
           "Output ONLY JSON: {\"verdict\":\"solid\" or \"review\", \"hallucinations\":[...], "
           "\"missing\":[...], \"note\":\"one line\"}. Mark \"review\" ONLY for a real accuracy "
           "error, a hallucination, or a genuinely important omission. Minor stylistic nits are \"solid\".")
    body = json.dumps({"model": MODEL, "messages": [{"role": "system", "content": SYS},
        {"role": "user", "content": usr}], "max_tokens": 500, "temperature": 0.3}).encode()
    for attempt in range(4):
        try:
            req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=body,
                headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=90) as r:
                j = json.load(r)
            txt = (j.get("choices", [{}])[0].get("message", {}).get("content") or "").strip()
            txt = txt.replace("```json", "").replace("```", "").strip()
            s, e = txt.find("{"), txt.rfind("}")
            if s >= 0 and e > s:
                return json.loads(txt[s:e+1])
        except urllib.error.HTTPError as e:
            time.sleep(20 if e.code == 429 else 5)
        except Exception:
            time.sleep(4)
    return {"verdict": "review", "note": "judge call failed", "missing": [], "hallucinations": []}

def main():
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    files = sorted(glob.glob(f"{CHARS}/*.yaml"))
    flagged = []; solid = 0; judged = 0
    for fp in files:
        stem = os.path.basename(fp)[:-5]
        if os.path.getsize(fp) == 0: continue
        try: d = yaml.safe_load(open(fp)) or {}
        except Exception: continue
        if not d.get("name"): continue
        h = hashlib.md5(open(fp, "rb").read()).hexdigest()
        if stem in cache and cache[stem].get("hash") == h:
            v = cache[stem]
        else:
            res = judge(d.get("name"), d.get("alias", ""), compact(d))
            v = {"hash": h, **res}; cache[stem] = v; judged += 1
            json.dump(cache, open(CACHE, "w"), indent=2)
            print(f"[judged {judged}] {stem}: {res.get('verdict')}", flush=True)
            time.sleep(1.5)
        if v.get("verdict") == "review":
            flagged.append((stem, v))
        else:
            solid += 1
    print("\n" + "=" * 60)
    print(f"VERIFICATION: {solid} solid, {len(flagged)} flagged for review (of {solid+len(flagged)})")
    print("=" * 60)
    for stem, v in flagged:
        print(f"\n⚑ {stem}")
        if v.get("note"): print(f"   note: {v['note']}")
        if v.get("missing"): print(f"   missing: {v['missing']}")
        if v.get("hallucinations"): print(f"   hallucinations: {v['hallucinations']}")

if __name__ == "__main__":
    main()

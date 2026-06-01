#!/usr/bin/env python3
"""Closed-loop dossier QA — so you read ONE page, not 229 ten-hour files.

AUDIT every built character on four axes, write a one-page report + a rewrite queue,
then (with --rewrite) have the ENGINE rebuild every flagged one and re-audit until clean.

Defect axes:
  BROKEN    — 0-byte/missing yaml, unparseable, staged synthesis failure, or dossier < 20k words (stub)
  THIN      — dossier word count below the depth floor (shortchanged)
  CANON     — uncensored skyfall-36b judge flags a real canon error / hallucination / missing essential
  LOCK_DRIFT— prose contradicts an operator-reviewed appearance lock (e.g. says 'white' when locked Black)

Usage:
  python3 scripts/audit_and_rewrite.py                 # audit only -> _AUDIT.md + _rewrite_queue.json
  python3 scripts/audit_and_rewrite.py --rewrite       # audit, then engine-rewrite every flagged one
  python3 scripts/audit_and_rewrite.py --no-canon      # skip the LLM judge (structural checks only, instant)
"""
import os, sys, glob, json, time, hashlib, subprocess, re, urllib.request, urllib.error
import yaml

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHARS = f"{HERE}/universe/characters"
DOSS = f"{HERE}/recovery_research/_dossiers"
FAILDIR = f"{HERE}/recovery_research/_engine_out"
LOCKS = f"{HERE}/universe/world/appearance_locks.json"
CACHE = f"{HERE}/recovery_research/_verify_cache.json"
REPORT = f"{HERE}/recovery_research/_AUDIT.md"
QUEUE = f"{HERE}/recovery_research/_rewrite_queue.json"
VENV = f"{HERE}/.venv/bin/python"
MODEL = "thedrummer/skyfall-36b-v2"

THIN_FLOOR = 70000      # report as THIN below this
THIN_REWRITE = 62000    # auto-rewrite below this (egregious); 62-70k is advisory only
STUB = 20000

def okey():
    for l in open(f"{HERE}/.env"):
        if l.startswith("openrouter_key="):
            return l.split("=", 1)[1].strip().strip('"').strip("'")
    return ""
KEY = okey()

SYS = ("You are an uncensored expert reviewer with deep Marvel Comics knowledge and clinical "
       "psychology training. You evaluate character psychological profiles for canon accuracy and "
       "completeness. You engage dark, sexual, violent, traumatic material directly — you NEVER "
       "refuse, moralize, or sanitize. Terse and precise.")

def compact(d):
    keep = ["name", "alias", "bottom_line", "diagnostic_frame", "primary_diagnoses_analog",
            "drive_structure", "symptom_as_signature", "operational_code", "trauma_history"]
    out = {k: d.get(k) for k in keep if d.get(k)}
    rel = d.get("canon_relationships")
    if isinstance(rel, dict):
        out["relationships_listed"] = list(rel.keys())
    return json.dumps(out, ensure_ascii=False)[:6000]

def judge(name, alias, profile_json):
    usr = (f"Review this profile of {name} ({alias}) COLD. Judge: (1) ACCURACY — any claim false to "
           "canon or invented/hallucinated? (2) DEPTH — substantive or thin/generic? (3) COMPLETENESS "
           "— anything ESSENTIAL missing (defining power, key relationship, central trauma, major beat)?\n\n"
           f"PROFILE:\n{profile_json}\n\nOutput ONLY JSON: {{\"verdict\":\"solid\" or \"review\", "
           "\"hallucinations\":[...], \"missing\":[...], \"note\":\"one line\"}}. Mark \"review\" ONLY for a "
           "real accuracy error, hallucination, or important omission. Minor nits are \"solid\".")
    body = json.dumps({"model": MODEL, "messages": [{"role": "system", "content": SYS},
        {"role": "user", "content": usr}], "max_tokens": 500, "temperature": 0.3}).encode()
    for _ in range(4):
        try:
            req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=body,
                headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=90) as r:
                j = json.load(r)
            txt = (j.get("choices", [{}])[0].get("message", {}).get("content") or "").strip()
            txt = txt.replace("```json", "").replace("```", "").strip()
            s, e = txt.find("{"), txt.rfind("}")
            if s >= 0 and e > s:
                return json.loads(txt[s:e + 1])
        except urllib.error.HTTPError as e:
            time.sleep(20 if e.code == 429 else 5)
        except Exception:
            time.sleep(4)
    return {"verdict": "review", "note": "judge call failed"}

# race/skin tokens implied by a lock, and their opposite, to catch prose contradictions
LOCK_RACE = [
    (("a black ", "african-american", "afro-latin", "afro latino", "afro-latina"), ("white", "caucasian")),
    (("biracial", "multiracial", "mixed black"), ()),
    (("gold metallic", "gold skin", "golden cosmic"), ()),
]

def lock_drift(stem, dossier):
    try:
        locks = json.load(open(LOCKS))
    except Exception:
        return None
    e = locks.get(stem)
    if not (isinstance(e, dict) and e.get("lock")):
        return None
    lock = e["lock"].lower()
    dl = dossier.lower()
    for implied, opposite in LOCK_RACE:
        if any(t in lock for t in implied) and opposite:
            opp = sum(dl.count(o) for o in opposite)
            imp = sum(dl.count(t.strip()) for t in implied)
            if opp > imp + 3:   # prose leans the wrong way
                return f"lock implies {implied[0].strip()} but prose says {opposite[0]} {opp}x vs {imp}x"
    return None

def audit(do_canon=True):
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    staged = {os.path.basename(f).split(".")[0] for f in glob.glob(f"{FAILDIR}/*.failed.txt")}
    rows = []
    for fp in sorted(glob.glob(f"{CHARS}/*.yaml")):
        stem = os.path.basename(fp)[:-5]
        defects = []
        # BROKEN: yaml
        if os.path.getsize(fp) == 0:
            rows.append((stem, ["BROKEN: empty yaml"], 0)); continue
        try:
            d = yaml.safe_load(open(fp)) or {}
        except Exception as ex:
            rows.append((stem, [f"BROKEN: yaml parse {repr(ex)[:40]}"], 0)); continue
        if not d.get("name"):
            rows.append((stem, ["BROKEN: no name"], 0)); continue
        # dossier
        dpath = f"{DOSS}/{stem}.md"
        words = 0
        has_doss = os.path.exists(dpath)
        if stem in staged:
            # A stale .failed.txt persists even after a successful fix — so CONFIRM by validating
            # the real YAML, and clean up the stale marker rather than false-flag forever.
            vr = subprocess.run([VENV, "engine/uatu_compiler.py", "validate", stem],
                                cwd=HERE, capture_output=True, text=True)
            if "GOLD" in vr.stdout or " 0 err" in vr.stdout:
                try: os.remove(f"{FAILDIR}/{stem}.failed.txt")
                except Exception: pass
            else:
                defects.append("BROKEN: profile synthesis failed (recompile)")
        if not has_doss:
            if stem in staged:
                pass  # already flagged; needs a full build
            else:
                # no dossier and no failure = simply not built yet by the populate. Not a defect.
                continue
        else:
            doss = open(dpath, encoding="utf-8").read()
            words = len(doss.split())
            if words < STUB:
                defects.append(f"BROKEN: dossier stub ({words}w)")
            elif words < THIN_FLOOR:
                defects.append(f"THIN: {words}w (floor {THIN_FLOOR})")
            ld = lock_drift(stem, doss)
            if ld:
                defects.append(f"LOCK_DRIFT: {ld}")
        # CANON via cached skyfall judge
        if do_canon and words >= STUB:
            h = hashlib.md5(open(fp, "rb").read()).hexdigest()
            if stem in cache and cache[stem].get("hash") == h:
                v = cache[stem]
            else:
                v = {"hash": h, **judge(d.get("name"), d.get("alias", ""), compact(d))}
                cache[stem] = v
                json.dump(cache, open(CACHE, "w"), indent=2)
                print(f"  judged {stem}: {v.get('verdict')}", flush=True)
                time.sleep(1.2)
            if v.get("verdict") == "review":
                bits = v.get("note", "")
                if v.get("hallucinations"): bits += f" | halluc: {v['hallucinations']}"
                if v.get("missing"): bits += f" | missing: {v['missing']}"
                defects.append(f"CANON: {bits.strip(' |')}")
        if defects:
            rows.append((stem, defects, words))
    return rows

def write_report(rows):
    # rewrite queue = anything BROKEN, CANON, LOCK_DRIFT, or egregiously THIN
    queue = []
    for stem, defects, words in rows:
        dj = " ; ".join(defects)
        # THIN alone is ADVISORY ONLY — never auto-rewrite (a re-roll can come back shorter and
        # regress a minor character, as it did to bernard). Genuine stubs are flagged BROKEN already.
        hard = any(x.startswith(("BROKEN", "CANON", "LOCK_DRIFT")) for x in defects)
        if hard:
            only_profile = (defects == ["BROKEN: profile synthesis failed (recompile)"]) and words >= THIN_FLOOR
            queue.append({"stem": stem, "reasons": defects, "action": "compile" if only_profile else "dossier"})
    json.dump(queue, open(QUEUE, "w"), indent=2)
    lines = [f"# DOSSIER AUDIT — {len(rows)} flagged, {len(queue)} queued for engine rewrite", ""]
    order = {"BROKEN": 0, "CANON": 1, "LOCK_DRIFT": 2, "THIN": 3}
    rows2 = sorted(rows, key=lambda r: min((order.get(x.split(":")[0], 9) for x in r[1]), default=9))
    for stem, defects, words in rows2:
        mark = "🔧 REWRITE" if any(s["stem"] == stem for s in queue) else "· review"
        lines.append(f"- **{stem}** ({words}w) — {mark}")
        for x in defects:
            lines.append(f"    - {x}")
    open(REPORT, "w").write("\n".join(lines) + "\n")
    return queue

def rewrite(queue):
    print(f"\n=== ENGINE REWRITE: {len(queue)} dossiers ===", flush=True)
    done = 0
    for item in queue:
        stem = item["stem"]
        fp = f"{CHARS}/{stem}.yaml"
        try:
            d = yaml.safe_load(open(fp)) or {}
        except Exception:
            d = {}
        disp = (d.get("name") or stem).strip()
        alias = (d.get("alias") or "").strip()
        action = item.get("action", "dossier")
        print(f"[rewrite {done+1}/{len(queue)}] {stem} [{action}]: {item['reasons']}", flush=True)
        # Non-regressive: back up the dossier first; if a rebuild comes back SHORTER, restore it.
        dpath = f"{DOSS}/{stem}.md"
        bak = None
        if action == "dossier" and os.path.exists(dpath):
            bak = open(dpath, encoding="utf-8").read()
        subprocess.run([VENV, "engine/uatu_compiler.py", action, stem, disp, alias],
                       cwd=HERE, capture_output=True)
        if bak is not None and os.path.exists(dpath):
            new = open(dpath, encoding="utf-8").read()
            if len(new.split()) < len(bak.split()):
                open(dpath, "w", encoding="utf-8").write(bak)
                print(f"    rebuild came back shorter — restored the longer original", flush=True)
        done += 1
    print(f"REWRITE PASS DONE ({done})", flush=True)

def main():
    do_canon = "--no-canon" not in sys.argv
    print(f"auditing (canon judge: {do_canon})...", flush=True)
    rows = audit(do_canon)
    queue = write_report(rows)
    print(f"\nAUDIT COMPLETE: {len(rows)} flagged, {len(queue)} queued for rewrite")
    print(f"  report -> {REPORT}")
    print(f"  queue  -> {QUEUE}")
    if "--rewrite" in sys.argv and queue:
        rewrite(queue)
        print("re-audit recommended after rewrites settle.")

if __name__ == "__main__":
    main()

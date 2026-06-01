#!/usr/bin/env python3
"""Dossier CONTENT verification — RESEARCH-GROUNDED, not memory-pencil-whipping.

For each built dossier it (1) RESEARCHES the character from Marvel's own wiki (canon source,
so 'Aamir Khan' resolves to Kamala's brother, not the Bollywood actor), then (2) hands the
researched canon + the dossier to a strong reasoning model that COMPARES them and flags:
  WRONG_SUBJECT  — profiling a real person / different character than the researched canon
  CANON_ERROR    — facts contradicting canon (debut era, relationships, powers, origin)
  HALLUCINATION  — invented events absent from canon

Independent of the engine's own Opus, and OpenAI-free (deepseek-v3.1 via Ollama Cloud).
Writes a one-page report + rewrite queue. Cached.  Run: verify_dossiers.py [--rewrite] [stem...]
"""
import os, sys, json, glob, time, hashlib, subprocess, urllib.request, urllib.error, urllib.parse, re
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHARS = f"{ROOT}/universe/characters"
DOSS = f"{ROOT}/recovery_research/_dossiers"
DIRS = f"{ROOT}/universe/characters/_directives"
CACHE = f"{ROOT}/recovery_research/_dossier_verify_cache.json"
RESCACHE = f"{ROOT}/recovery_research/_canon_research_cache.json"
REPORT = f"{ROOT}/recovery_research/_DOSSIER_VERIFY.md"
QUEUE = f"{ROOT}/recovery_research/_dossier_rewrite_queue.json"
VENV = f"{ROOT}/.venv/bin/python"
OLLAMA = "http://localhost:11434/api/chat"
MODEL = "deepseek-v4-pro:cloud"   # frontier 1.6T MoE, 1M context (reads the FULL dossier), thinking mode
FANDOM = "https://marvel.fandom.com/api.php"
UA = {"User-Agent": "grizzly-knights-verify/1.0"}

def _get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return json.load(r)

def research(name, alias, rescache):
    """Pull canon facts from Marvel's wiki (the comic character, not a same-named real person)."""
    key = f"{name}|{alias}"
    if key in rescache:
        return rescache[key]
    canon = ""
    queries = [a for a in [alias.split(" / ")[0] if alias else "", name] if a]
    for q in queries:
        try:
            sr = _get(f"{FANDOM}?action=query&list=search&srsearch={urllib.parse.quote(q)}&srlimit=3&format=json")
            hits = sr.get("query", {}).get("search", [])
            for h in hits:
                title = h["title"]
                ex = _get(f"{FANDOM}?action=query&prop=extracts&exintro&explaintext&redirects=1&titles={urllib.parse.quote(title)}&format=json")
                pages = ex.get("query", {}).get("pages", {})
                for _, pg in pages.items():
                    txt = (pg.get("extract") or "").strip()
                    if len(txt) > 120:
                        canon = f"[Marvel Wiki: {title}]\n{txt[:2500]}"
                        break
            if canon:
                break
        except Exception:
            time.sleep(1)
    rescache[key] = canon
    json.dump(rescache, open(RESCACHE, "w"), indent=1)
    return canon

def ollama(prompt):
    body = json.dumps({"model": MODEL, "stream": False, "think": True,
        "options": {"temperature": 0.1, "num_predict": 1200},
        "messages": [{"role": "user", "content": prompt}]}).encode()
    with urllib.request.urlopen(urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"}), timeout=240) as r:
        return (json.load(r).get("message", {}).get("content") or "").strip()

def excerpt(doss):
    return doss[:600000]   # 1M-context model reads the whole file, no pencil-whipping from excerpts

def verify(name, alias, doss, canon):
    base = (f"You are fact-checking a psychological dossier against RESEARCHED canon. Be skeptical "
            f"and specific; only flag REAL contradictions, not style.\n\n"
            f"SUPPOSED SUBJECT: {name} ({alias}) — a MARVEL COMICS character.\n\n"
            f"RESEARCHED CANON (from Marvel's wiki — treat as ground truth):\n{canon or '[no wiki page found — judge with caution; flag only blatant real-person contamination]'}\n\n"
            f"THE FULL DOSSIER TO CHECK:\n{excerpt(doss)}\n\n"
            "Compare the dossier to the researched canon. Flag:\n"
            "1. WRONG_SUBJECT — the dossier profiles a REAL person (real filmography/spouses/biography) "
            "or a DIFFERENT character than the canon describes.\n"
            "2. CANON_ERROR — facts that contradict canon (wrong debut era/decade, wrong family/"
            "relationships, wrong powers/origin).\n"
            "3. HALLUCINATION — major invented events absent from canon.\n\n"
            "Output ONLY JSON: {\"ok\":true|false,\"category\":\"WRONG_SUBJECT\"|\"CANON_ERROR\"|"
            "\"HALLUCINATION\"|\"\",\"issues\":[\"specific reason citing the contradiction\"],"
            "\"who_it_should_be\":\"one line if WRONG_SUBJECT\"}.")
    for _ in range(3):
        try:
            txt = ollama(base).replace("```json", "").replace("```", "")
            s, e = txt.find("{"), txt.rfind("}")
            if s >= 0 and e > s:
                return json.loads(txt[s:e + 1])
        except Exception:
            time.sleep(4)
    return None

def main():
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    rescache = json.load(open(RESCACHE)) if os.path.exists(RESCACHE) else {}
    want = [a for a in sys.argv[1:] if not a.startswith("-")]
    stems = want or sorted(os.path.basename(f)[:-3] for f in glob.glob(f"{DOSS}/*.md"))
    flagged = []; ok = 0; judged = 0
    for stem in stems:
        dp, yp = f"{DOSS}/{stem}.md", f"{CHARS}/{stem}.yaml"
        if not (os.path.exists(dp) and os.path.exists(yp)):
            continue
        doss = open(dp, encoding="utf-8").read()
        d = yaml.safe_load(open(yp)) or {}
        name, alias = (d.get("name") or stem), (d.get("alias") or "")
        h = hashlib.md5(doss[:8000].encode()).hexdigest()
        if stem in cache and cache[stem].get("h") == h and not want:
            v = cache[stem]
        else:
            canon = research(name, alias, rescache)
            res = verify(name, alias, doss, canon)
            if res is None:
                print(f"  {stem}: verify failed", flush=True); continue
            v = {"h": h, "researched": bool(canon), **res}
            cache[stem] = v; json.dump(cache, open(CACHE, "w"), indent=1); judged += 1
            print(f"  {stem}: {'OK' if v.get('ok') else v.get('category')} (research={'y' if canon else 'n'})", flush=True)
            time.sleep(0.3)
        (flagged.append((stem, name, v)) if v.get("ok") is False else None)
        ok += 1 if v.get("ok") else 0
    queue, lines = [], [f"# DOSSIER VERIFY (research-grounded) — {len(flagged)} flagged of {ok+len(flagged)}", ""]
    for stem, name, v in flagged:
        lines.append(f"- **{stem}** ({name}) — {v.get('category')}{'' if v.get('researched') else ' [no wiki]'}")
        for i in v.get("issues", []): lines.append(f"    - {i}")
        if v.get("who_it_should_be"): lines.append(f"    - SHOULD BE: {v['who_it_should_be']}")
        queue.append({"stem": stem, "category": v.get("category"), "issues": v.get("issues", []),
                      "who_it_should_be": v.get("who_it_should_be", "")})
    open(REPORT, "w").write("\n".join(lines) + "\n"); json.dump(queue, open(QUEUE, "w"), indent=2)
    print(f"\nVERIFY DONE: {len(flagged)} flagged, {ok} clean (judged {judged})\n  report -> {REPORT}")
    if "--rewrite" in sys.argv and queue:
        rewrite(queue)

def rewrite(queue):
    os.makedirs(DIRS, exist_ok=True)
    for item in queue:
        stem = item["stem"]
        if item.get("category") == "WRONG_SUBJECT" and item.get("who_it_should_be"):
            note = (f"# IDENTITY DISAMBIGUATION (authoritative)\nThis subject is the MARVEL COMICS "
                    f"character, NOT any real-world person sharing the name. {item['who_it_should_be']}\n"
                    f"Profile ONLY the fictional Marvel character. Never reference a real actor/celebrity, "
                    f"real filmography, or real-world biography.\n")
            p = f"{DIRS}/{stem}.md"; prior = open(p).read() if os.path.exists(p) else ""
            if "IDENTITY DISAMBIGUATION" not in prior:
                open(p, "w").write(note + ("\n" + prior if prior else ""))
        d = yaml.safe_load(open(f"{CHARS}/{stem}.yaml")) or {}
        print(f"  rebuild {stem} [{item.get('category')}]", flush=True)
        subprocess.run([VENV, "engine/uatu_compiler.py", "dossier", stem, (d.get("name") or stem), (d.get("alias") or "")], cwd=ROOT, capture_output=True)
    print("REBUILD PASS DONE", flush=True)

if __name__ == "__main__":
    main()

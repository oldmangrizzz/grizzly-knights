#!/usr/bin/env python3
"""Image validator — so the OPERATOR isn't the QA on portraits.

A vision model looks at every portrait and checks it against the character's canonical
markers (race/skin color, hair, gender, signature costume/powers). Markers come from the
appearance lock when one exists, else they're extracted from the character's dossier.
Flags mismatches, writes a one-page report + a fix queue.

  python3 scripts/audit_images.py            # audit -> _IMAGE_AUDIT.md + _image_fix_queue.json
  python3 scripts/audit_images.py --fix      # audit, then auto-lock + re-roll every flagged one
  python3 scripts/audit_images.py stem ...    # just these
"""
import os, sys, json, glob, time, base64, hashlib, urllib.request, urllib.error, subprocess
import yaml

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = f"{HERE}/world_art/portraits"
DOSS = f"{HERE}/recovery_research/_dossiers"
LOCKS = f"{HERE}/universe/world/appearance_locks.json"
MARK_CACHE = f"{HERE}/recovery_research/_image_markers.json"
JUDGE_CACHE = f"{HERE}/recovery_research/_image_judge_cache.json"
REPORT = f"{HERE}/recovery_research/_IMAGE_AUDIT.md"
QUEUE = f"{HERE}/recovery_research/_image_fix_queue.json"
# Vision runs on Ollama (kimi-k2.6 multimodal) — local API, free, no rate limit, accurate on
# dramatic/masked comic art (the free-OpenRouter and NIM llama-vision models hallucinate here).
OLLAMA_URL = "http://localhost:11434/api/chat"
VISION_MODEL = "qwen3-vl:235b-cloud"   # best vision model on Ollama Cloud

def vchat(prompt, img_b64, max_tokens=300):
    body = json.dumps({"model": VISION_MODEL, "stream": False,
        "options": {"num_predict": max_tokens, "temperature": 0.2},
        "messages": [{"role": "user", "content": prompt, "images": [img_b64]}]}).encode()
    req = urllib.request.Request(OLLAMA_URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        j = json.load(r)
    return (j.get("message", {}).get("content") or "").strip()

def load_json(p, d):
    return json.load(open(p)) if os.path.exists(p) else d

def locks():
    return load_json(LOCKS, {})

def disp_name(stem):
    try:
        d = yaml.safe_load(open(f"{HERE}/universe/characters/{stem}.yaml")) or {}
        n, a = (d.get("name") or stem).strip(), (d.get("alias") or "").strip()
        return f"{n} ({a})" if a else n
    except Exception:
        return stem.replace("_", " ").title()

def markers_for(stem, lk, mcache):
    """Appearance spec to judge against. A reviewed LOCK wins (handles our reimaginings and
    operator calls). Otherwise the character is canon-accurate, so we judge against the vision
    model's OWN knowledge of the canonical Marvel character — no fragile text extraction."""
    e = lk.get(stem)
    if isinstance(e, dict) and e.get("lock"):
        return e["lock"]
    name = disp_name(stem)
    return f"__CANON__{name}"  # sentinel: judge against canonical Marvel appearance of this character

def judge(img_path, markers):
    b64 = base64.b64encode(open(img_path, "rb").read()).decode()
    if markers.startswith("__CANON__"):
        who = markers[len("__CANON__"):]
        expected = (f"the canonical Marvel Comics appearance of {who} — use your own knowledge of how "
                    "this established character is canonically depicted (race/skin color, gender, hair, "
                    "and signature costume/powers/non-human traits)")
    else:
        expected = markers
    prompt = (f"EXPECTED CHARACTER:\n{expected}\n\nLook at this portrait. Flag it ONLY if there is a "
              "GROSS, OBVIOUS identity error in one of these four:\n"
              "1. GENDER is wrong (man vs woman).\n"
              "2. SKIN COLOR / RACE is clearly wrong (e.g. expected a Black person, shown white; or "
              "expected blue/grey/green non-human skin, shown normal human skin). NOTE: 'black hair' "
              "refers to HAIR COLOR, not race — do not confuse hair color with skin color.\n"
              "3. HAIR COLOR is grossly wrong (e.g. expected blonde, shown red; expected white, shown black).\n"
              "4. A DEFINING non-human trait is missing (no blue fur on Beast, no orange rock on the Thing, etc.).\n\n"
              "IGNORE everything else: costume style nuances, exact shade, a few gray hairs, hair "
              "curliness, pose, lighting, background, accessories, art style. When unsure, it MATCHES.\n"
              "Reply ONLY JSON: {\"match\":true or false,\"mismatches\":[\"short reason\",...]}")
    for attempt in range(4):
        try:
            txt = vchat(prompt, b64, 250).replace("```json", "").replace("```", "")
            s, e = txt.find("{"), txt.rfind("}")
            if s >= 0 and e > s:
                return json.loads(txt[s:e + 1])
        except Exception:
            time.sleep(4)
    return None

def main():
    lk = locks()
    mcache = load_json(MARK_CACHE, {})
    jcache = load_json(JUDGE_CACHE, {})
    want = [a for a in sys.argv[1:] if not a.startswith("-")]
    stems = want or sorted(os.path.basename(f)[:-4] for f in glob.glob(f"{PORT}/*.png"))
    flagged = []; checked = 0; ok = 0
    for stem in stems:
        ip = f"{PORT}/{stem}.png"
        if not os.path.exists(ip):
            continue
        markers = markers_for(stem, lk, mcache)
        if not markers:
            print(f"  · skip {stem}: no markers (no lock/dossier)", flush=True)
            continue
        h = hashlib.md5(open(ip, "rb").read()).hexdigest() + hashlib.md5(markers.encode()).hexdigest()[:8]
        if stem in jcache and jcache[stem].get("h") == h and not want:
            v = jcache[stem]
        else:
            res = judge(ip, markers)
            if res is None:
                print(f"  · SKIP {stem}: judge unavailable (rate limit) — will retry next run", flush=True)
                time.sleep(2)
                continue
            v = {"h": h, **res}
            jcache[stem] = v
            json.dump(jcache, open(JUDGE_CACHE, "w"), indent=1)
            checked += 1
            time.sleep(0.3)
        if v.get("match") is False:
            flagged.append((stem, v.get("mismatches", []), bool(lk.get(stem))))
            print(f"  ✗ {stem}: {v.get('mismatches')}", flush=True)
        else:
            ok += 1
    # report + queue
    queue = [{"stem": s, "mismatches": m, "locked": locked} for s, m, locked in flagged]
    json.dump(queue, open(QUEUE, "w"), indent=2)
    lines = [f"# IMAGE AUDIT — {len(flagged)} portraits off-model (of {len(stems)} checked)", ""]
    for s, m, locked in flagged:
        lines.append(f"- **{s}** {'(locked)' if locked else '(needs lock)'}")
        for x in m:
            lines.append(f"    - {x}")
    open(REPORT, "w").write("\n".join(lines) + "\n")
    print(f"\nIMAGE AUDIT: {len(flagged)} off-model, {ok} clean (newly judged {checked})")
    print(f"  report -> {REPORT}")
    if "--fix" in sys.argv and flagged:
        fix(flagged, lk, mcache)

def fix(flagged, lk, mcache):
    """Auto-fix ONLY unlocked portraits with gross errors (locked = operator-approved, flag only).
    Non-destructive: back up the portrait first; keep it if a re-roll doesn't actually help."""
    unlocked = [(s, m) for s, m, locked in flagged if not locked]
    locked_flags = [s for s, m, locked in flagged if locked]
    if locked_flags:
        print(f"NOT auto-touching {len(locked_flags)} LOCKED/approved (review only): {locked_flags}", flush=True)
    if not unlocked:
        print("nothing to auto-fix (all flags were on locked/approved portraits).", flush=True)
        return
    changed = False
    for stem, mism in unlocked:
        spec = markers_for(stem, lk, mcache)
        neg = "wrong skin color, wrong race, wrong hair color, wrong gender, off-model, " + ", ".join(mism)
        lk[stem] = {"lock": spec, "negative": neg}
        changed = True
    if changed:
        json.dump(lk, open(LOCKS, "w"), indent=1, ensure_ascii=False)
    stems = [s for s, _ in unlocked]
    # back up originals so a bad re-roll can be reverted
    os.makedirs(f"{HERE}/world_art/_portrait_bak", exist_ok=True)
    for s in stems:
        src = f"{PORT}/{s}.png"
        if os.path.exists(src):
            open(f"{HERE}/world_art/_portrait_bak/{s}.png", "wb").write(open(src, "rb").read())
    print(f"re-rolling {len(stems)} UNLOCKED off-model portraits (backed up): {stems}", flush=True)
    subprocess.run([sys.executable, f"{HERE}/world_art/fix_portraits.py", *stems], cwd=HERE)

if __name__ == "__main__":
    main()

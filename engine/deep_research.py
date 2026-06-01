#!/usr/bin/env python3
"""Multi-platform deep research for a character — the grounding the engine builds on.

NOT a single wiki. For a subject it gathers and cross-references:
  - WEB: multi-source search (DuckDuckGo, keyless) + readable-text extraction from several pages
  - VIDEO: a comic-retrospective/longbox YouTube video -> transcript (yt-dlp captions), and
    optional key-FRAME vision analysis (qwen3-vl) for what transcripts miss
  - SYNTHESIS: deepseek-v4-pro (1.6T, 1M ctx) folds it into a research brief

CRITICAL — recast-safe: the operator's universe directives/locks are AUTHORITATIVE ground truth.
The brief separates BASELINE CANON (for catching real errors/hallucinations and wrong-subject)
from THIS UNIVERSE'S DELIBERATE RECASTS, and never "corrects" a recast back to baseline.

Usage: python3 engine/deep_research.py <stem> ["Display Name"] ["Alias"] [--video] [--frames]
Caches to recovery_research/_deep_research/<stem>.md
"""
import os, sys, re, json, html, time, subprocess, tempfile, urllib.request, urllib.parse, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = f"{ROOT}/recovery_research/_deep_research"
LOCKS = f"{ROOT}/universe/world/appearance_locks.json"
DIRS = f"{ROOT}/universe/characters/_directives"
OLLAMA = "http://localhost:11434/api/chat"
SYNTH = "deepseek-v4-pro:cloud"
VISION = "qwen3-vl:235b-cloud"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

def _req(url, timeout=20):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=timeout)

def _wiki_extract(api, title, cap=14000):
    try:
        d = json.loads(_req(f"{api}?action=query&prop=extracts&explaintext&redirects=1&titles={urllib.parse.quote(title)}&format=json").read())
        for _, pg in d.get("query", {}).get("pages", {}).items():
            return (pg.get("extract") or "").strip()[:cap]
    except Exception:
        return ""
    return ""

def _wiki_search(api, query, n=4):
    try:
        d = json.loads(_req(f"{api}?action=query&list=search&srsearch={urllib.parse.quote(query)}&srlimit={n}&format=json").read())
        return [h["title"] for h in d.get("query", {}).get("search", [])]
    except Exception:
        return []

def web_research(name, alias):
    """Reliable multi-platform text sources: Wikipedia + Marvel Fandom (comic-canon), cross-referenced."""
    sources = []
    EN = "https://en.wikipedia.org/w/api.php"
    FANDOM = "https://marvel.fandom.com/api.php"
    primary = alias.split(" / ")[0] if alias else name
    # Wikipedia — disambiguate toward the COMIC character, not a same-named real person/film
    for q in [f"{primary} Marvel Comics character", f"{name} Marvel Comics"]:
        for title in _wiki_search(EN, q, 3):
            if any(x in title.lower() for x in ("film", "(2", "soundtrack", "video game")): continue
            ext = _wiki_extract(EN, title)
            if len(ext) > 500:
                sources.append({"platform": "Wikipedia", "title": title, "text": ext}); break
        if sources: break
    # Marvel Fandom — comic-canon deep source (resolves same-name collisions to the comic character)
    for q in [primary, name]:
        for title in _wiki_search(FANDOM, q, 3):
            ext = _wiki_extract(FANDOM, title, 12000)
            if len(ext) > 400:
                sources.append({"platform": "Marvel Fandom", "title": title, "text": ext}); break
        if len([s for s in sources if s["platform"] == "Marvel Fandom"]):
            break
    return sources

def video_research(name, alias, do_frames=False):
    """Find a comic-retrospective video, pull its transcript, optionally analyze key frames."""
    q = f"{name} {alias} marvel comics character explained history"
    tmp = tempfile.mkdtemp()
    try:
        # grab the top matching video's auto-captions only (fast, no full download)
        subprocess.run(["yt-dlp", f"ytsearch1:{q}", "--write-auto-subs", "--sub-lang", "en",
                        "--skip-download", "--sub-format", "vtt", "-o", f"{tmp}/vid.%(ext)s",
                        "--no-warnings", "-q"], timeout=120, capture_output=True)
        vtt = next((f for f in os.listdir(tmp) if f.endswith(".vtt")), None)
        transcript = ""
        if vtt:
            lines, seen = [], set()
            for ln in open(f"{tmp}/{vtt}", encoding="utf-8", errors="ignore"):
                ln = ln.strip()
                if "-->" in ln or ln.startswith(("WEBVTT", "Kind:", "Language:")) or not ln: continue
                ln = re.sub(r"<[^>]+>", "", ln)
                if ln and ln not in seen:
                    seen.add(ln); lines.append(ln)
            transcript = " ".join(lines)[:8000]
        frames = ""
        if do_frames:
            # download the video low-res, sample frames, describe via vision model
            subprocess.run(["yt-dlp", f"ytsearch1:{q}", "-f", "worst[height<=360]",
                            "-o", f"{tmp}/v.%(ext)s", "--no-warnings", "-q"], timeout=240, capture_output=True)
            vid = next((f for f in os.listdir(tmp) if f.startswith("v.") and not f.endswith(".vtt")), None)
            if vid:
                subprocess.run(["ffmpeg", "-i", f"{tmp}/{vid}", "-vf", "fps=1/30", f"{tmp}/f%03d.jpg",
                                "-y"], timeout=120, capture_output=True)
                import base64
                descs = []
                for fr in sorted(f for f in os.listdir(tmp) if f.startswith("f") and f.endswith(".jpg"))[:5]:
                    b = base64.b64encode(open(f"{tmp}/{fr}", "rb").read()).decode()
                    body = json.dumps({"model": VISION, "stream": False, "options": {"num_predict": 120},
                        "messages": [{"role": "user", "content": "Describe any comic-book panels/characters/costumes visible.", "images": [b]}]}).encode()
                    try:
                        r = urllib.request.urlopen(urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"}), timeout=90)
                        descs.append((json.load(r).get("message", {}).get("content") or "")[:200])
                    except Exception: pass
                frames = " | ".join(descs)
        return transcript, frames
    except Exception as e:
        return "", ""
    finally:
        try: import shutil; shutil.rmtree(tmp)
        except Exception: pass

def synth(model, prompt):
    body = json.dumps({"model": model, "stream": False, "think": True,
        "options": {"temperature": 0.2, "num_predict": 2500},
        "messages": [{"role": "user", "content": prompt}]}).encode()
    with urllib.request.urlopen(urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"}), timeout=300) as r:
        return (json.load(r).get("message", {}).get("content") or "").strip()

def recasts_for(stem):
    notes = []
    df = f"{DIRS}/{stem}.md"
    if os.path.exists(df): notes.append("DIRECTIVE:\n" + open(df).read()[:2000])
    try:
        lk = json.load(open(LOCKS)).get(stem)
        if isinstance(lk, dict) and lk.get("lock"): notes.append("APPEARANCE LOCK: " + lk["lock"])
    except Exception: pass
    return "\n\n".join(notes)

def research(stem, name, alias, do_video=True, do_frames=False):
    os.makedirs(OUT, exist_ok=True)
    print(f"[research] {name} ({alias}) — web...", flush=True)
    web = web_research(name, alias)
    transcript, frames = ("", "")
    if do_video:
        print(f"[research] {name} — video...", flush=True)
        transcript, frames = video_research(name, alias, do_frames)
    recasts = recasts_for(stem)
    src_block = "\n\n".join(f"### SOURCE: {s['title']} ({s['url']})\n{s['text']}" for s in web)
    if transcript: src_block += f"\n\n### VIDEO TRANSCRIPT (comic retrospective)\n{transcript}"
    if frames: src_block += f"\n\n### VIDEO KEY-FRAME ANALYSIS\n{frames}"
    prompt = (
        f"You are UATU's research analyst. Synthesize a rigorous, CROSS-REFERENCED canon research brief "
        f"on the Marvel character {name} ({alias}), for grounding a deep psychological dossier.\n\n"
        f"THIS UNIVERSE'S AUTHORITATIVE RECASTS (FIXED — never contradict or 'correct' these; they OVERRIDE "
        f"baseline canon):\n{recasts or '(none on record)'}\n\n"
        f"RAW MULTI-SOURCE RESEARCH (cross-reference; note where sources agree/conflict; ignore fan speculation):\n{src_block[:120000]}\n\n"
        "Produce a brief with: (1) WHO THIS IS — confirm it is the fictional Marvel character, not a real "
        "person who shares the name; (2) DEBUT & PUBLICATION ERA (real years); (3) ORIGIN & POWERS; "
        "(4) KEY RELATIONSHIPS & AFFILIATIONS; (5) MAJOR STORY BEATS; (6) HOW THIS UNIVERSE'S RECASTS "
        "MODIFY THE BASELINE (restate the recasts as the operative truth). Cite which source supports each "
        "major claim. Be exhaustive on facts a model would likely get wrong.")
    print(f"[research] {name} — synthesizing ({SYNTH})...", flush=True)
    brief = synth(SYNTH, prompt)
    meta = f"<!-- sources: {len(web)} web, video={'y' if transcript else 'n'}, frames={'y' if frames else 'n'} -->\n"
    open(f"{OUT}/{stem}.md", "w", encoding="utf-8").write(meta + brief)
    print(f"[research] {stem}: brief written ({len(brief)} chars, {len(web)} web sources, video={'y' if transcript else 'n'})", flush=True)
    return brief

if __name__ == "__main__":
    a = sys.argv
    stem = a[1]; name = a[2] if len(a) > 2 else stem; alias = a[3] if len(a) > 3 else ""
    research(stem, name, alias, do_video=("--no-video" not in a), do_frames=("--frames" in a))

#!/usr/bin/env python3
"""FULL-DEPTH population — every named character gets the SAME treatment as the principals:
a deep 27-module dossier (~80-98k words) + structured profile + portrait. No thin profiles,
no non-uniform depth (that contaminates the research). Resumable; major characters first.

Per character: `dossier` (deep) -> `compile` (profile + native portrait) -> vault refresh.
"""
import json, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = "/Users/rbhanson/fanfic"
DOSS = f"{ROOT}/recovery_research/_dossiers"
CHARS = f"{ROOT}/universe/characters"
PORT = f"{ROOT}/world_art/portraits"

COSMIC = {
    "thanos": ("Thanos", "The Mad Titan"), "gamora": ("Gamora", "Gamora"),
    "peter_quill": ("Peter Quill", "Star-Lord"), "adam_warlock": ("Adam Warlock", "Adam Warlock"),
    "silver_surfer": ("Norrin Radd", "Silver Surfer"), "galactus": ("Galan", "Galactus"),
    "drax": ("Arthur Douglas", "Drax the Destroyer"), "rocket_raccoon": ("Rocket Raccoon", "Rocket"),
    "groot": ("Groot", "Groot"), "nebula": ("Nebula", "Nebula"),
    "ronan": ("Ronan", "Ronan the Accuser"), "mantis": ("Mantis", "Mantis"),
    "richard_rider": ("Richard Rider", "Nova"), "beta_ray_bill": ("Beta Ray Bill", "Beta Ray Bill"),
}
SUPERNATURAL = {
    "blade": ("Eric Brooks", "Blade"), "johnny_blaze": ("Johnny Blaze", "Ghost Rider"),
    "robbie_reyes": ("Robbie Reyes", "Ghost Rider"), "marc_spector": ("Marc Spector", "Moon Knight"),
    "morbius": ("Michael Morbius", "Morbius"), "jack_russell": ("Jack Russell", "Werewolf by Night"),
    "jericho_drumm": ("Jericho Drumm", "Brother Voodoo"), "elsa_bloodstone": ("Elsa Bloodstone", "Elsa Bloodstone"),
}
PRIORITY = ["mystique", "maria_hill", "thaddeus_ross", "nick_fury", "norman_osborn", "emma_frost",
            "apocalypse", "red_skull", "mephisto", "doctor_strange", "kitty_pryde", "pietro_maximoff",
            "thanos", "silver_surfer", "galactus", "gamora", "peter_quill", "adam_warlock",
            "blade", "johnny_blaze", "marc_spector", "morbius", "robbie_reyes"]

def roster():
    r = {}
    for stem, disp in json.load(open("/tmp/support_roster.json")).items():
        r[stem] = (disp, disp)
    r.update(COSMIC); r.update(SUPERNATURAL)
    r["heinrich_zemo"] = ("Heinrich Zemo", "Baron Zemo")
    r["helmut_zemo"] = ("Helmut Zemo", "Baron Zemo")
    return r

def done(stem):
    return (os.path.exists(f"{DOSS}/{stem}.md") and os.path.getsize(f"{DOSS}/{stem}.md") > 20000
            and os.path.exists(f"{CHARS}/{stem}.yaml") and os.path.getsize(f"{CHARS}/{stem}.yaml") > 0
            and os.path.exists(f"{PORT}/{stem}.png"))

R = roster()

def build(stem):
    disp, alias = R[stem]
    if not (os.path.exists(f"{DOSS}/{stem}.md") and os.path.getsize(f"{DOSS}/{stem}.md") > 20000):
        subprocess.run([sys.executable, "engine/uatu_compiler.py", "dossier", stem, disp, alias],
                       cwd=ROOT, capture_output=True, text=True, timeout=5400)
    subprocess.run([sys.executable, "engine/uatu_compiler.py", "compile", stem, disp, alias],
                   cwd=ROOT, capture_output=True, text=True, timeout=1800)
    w = 0
    try: w = len(open(f"{DOSS}/{stem}.md").read().split())
    except Exception: pass
    return stem, w

def main():
    ordered = [s for s in PRIORITY if s in R] + [s for s in R if s not in PRIORITY]
    todo = [s for s in ordered if not done(s)]
    print(f"FULL-DEPTH build: {len(todo)} characters — deep dossier + profile + portrait each, majors first", flush=True)
    n = 0
    with ThreadPoolExecutor(max_workers=2) as ex:
        futs = {ex.submit(build, s): s for s in todo}
        for f in as_completed(futs):
            try:
                stem, w = f.result()
            except Exception as e:
                stem, w = futs[f], 0
            n += 1
            flag = "" if w >= 20000 else "  <-- THIN, will retry next pass"
            print(f"[{n}/{len(todo)}] {stem}: {w} words{flag}", flush=True)
            subprocess.run([sys.executable, "scripts/build_vault.py"], cwd=ROOT, capture_output=True)
    print("FULL-DEPTH POPULATE COMPLETE", flush=True)

if __name__ == "__main__":
    main()

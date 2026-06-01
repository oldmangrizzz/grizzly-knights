#!/usr/bin/env python3
"""End-to-end portrait finish — runs unattended, no check-ins.

1. Wait for the FLUX redo to complete.
2. Screen every portrait on GPT-4o (reliable judge).
3. Re-roll ONLY the genuinely-broken ones — unlocked + flagged for a GROSS identity error
   (gender / race / skin color / species / skeleton) — once, via FLUX. (Filters GPT-4o's
   distinctive-character false positives so credits aren't wasted on fine images.)
4. Re-screen the re-rolled set; 5. rebuild the vault. Writes _POLISH_DONE when finished.
"""
import os, sys, json, time, subprocess, glob

ROOT = "/Users/rbhanson/fanfic"
PY = f"{ROOT}/.venv/bin/python"
JC = f"{ROOT}/recovery_research/_image_judge_cache.json"
LOCKS = f"{ROOT}/universe/world/appearance_locks.json"
DONE = f"{ROOT}/world_art/_POLISH_DONE"
GROSS = ("gender", "race", "skin", "skeleton", "skull", "species", "white man", "white woman",
         "blue skin", "green skin", "orange", "caucasian", "is a man", "is a woman", "non-human")

def log(m): print(m, flush=True)

def main():
    if os.path.exists(DONE): os.remove(DONE)
    # 1. wait for the redo
    while subprocess.run(["pgrep", "-f", "redo_all.py"], capture_output=True).returncode == 0:
        time.sleep(15)
    log("redo complete; screening on GPT-4o")
    # 2. fresh screen (images changed)
    if os.path.exists(JC): os.remove(JC)
    subprocess.run([PY, f"{ROOT}/scripts/audit_images.py"], cwd=ROOT,
                   stdout=open(f"{ROOT}/recovery_research/_polish_screen.log", "w"), stderr=subprocess.STDOUT)
    # 3. pick genuinely-broken: unlocked + gross-error reason
    locks = set(json.load(open(LOCKS)).keys())
    jc = json.load(open(JC)) if os.path.exists(JC) else {}
    broken = []
    for s, v in jc.items():
        if v.get("match") is False and s not in locks:
            reasons = " ".join(v.get("mismatches", [])).lower()
            if any(g in reasons for g in GROSS):
                broken.append(s)
    log(f"genuinely-broken (gross errors, unlocked): {len(broken)} -> {broken}")
    # 4. re-roll just those via FLUX (fresh random seed each call), backed up by redo_all
    if broken:
        subprocess.run([PY, f"{ROOT}/world_art/redo_all.py", *broken], cwd=ROOT)
        # re-screen the re-rolled set
        for s in broken:
            jc.pop(s, None)
        json.dump(jc, open(JC, "w"), indent=1)
        subprocess.run([PY, f"{ROOT}/scripts/audit_images.py", *broken], cwd=ROOT,
                       stdout=open(f"{ROOT}/recovery_research/_polish_rescreen.log", "w"), stderr=subprocess.STDOUT)
    # 5. rebuild the vault so portraits are surfaced
    subprocess.run([PY, f"{ROOT}/scripts/build_vault.py"], cwd=ROOT, capture_output=True)
    total = len(glob.glob(f"{ROOT}/world_art/portraits/*.png"))
    open(DONE, "w").write(f"redone, screened, {len(broken)} fixed, vault rebuilt; {total} portraits\n")
    log(f"POLISH DONE — {len(broken)} fixed of {total}")

if __name__ == "__main__":
    main()

"""
APT-05b: Atomic save + apply_delta resilience.

Verifies:
  1. save_chronicle never leaves a partial chronicle.json on disk: the
     pre-existing file survives a crash that occurs after the .tmp is
     written but before os.replace runs.
  2. apply_delta preserves pre-existing state when the delta is missing
     the touched character/world_fact/relationship keys.
"""
from __future__ import annotations
import json, os, sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from engine import chronicle as C


def with_backup(chron_path: Path, fn):
    existed = chron_path.exists()
    backup = chron_path.read_bytes() if existed else None
    try:
        return fn()
    finally:
        if existed:
            chron_path.write_bytes(backup)
        else:
            if chron_path.exists():
                chron_path.unlink()
        # nuke any stray .tmp / .bak siblings created by the test
        for p in chron_path.parent.glob(chron_path.name + ".tmp"):
            p.unlink()
        for p in chron_path.parent.glob(chron_path.name + ".bak.*"):
            p.unlink()


def main() -> int:
    findings: list[str] = []
    notes: list[str] = []
    CHRON = C.CHRONICLE_PATH

    def run():
        # ── 1. Atomic save: simulated crash between write and rename ──
        good = json.loads(json.dumps(C.EMPTY_CHRONICLE))
        good["characters"]["wade_wilson"] = {
            "state": "ORIGINAL", "recent_events": ["orig event"]
        }
        # Write the "old" chronicle through the real save path
        C.save_chronicle(good)
        original_bytes = CHRON.read_bytes()

        # Now try to save a new chronicle, but kill the process between
        # the .tmp write and the os.replace. We patch os.replace to raise.
        crashing = json.loads(json.dumps(C.EMPTY_CHRONICLE))
        crashing["characters"]["wade_wilson"] = {
            "state": "NEW BUT NEVER LANDED", "recent_events": []
        }

        boom = RuntimeError("simulated crash mid-save")
        with mock.patch("engine.chronicle.os.replace", side_effect=boom):
            try:
                C.save_chronicle(crashing)
                findings.append("  • save_chronicle did not raise when os.replace failed")
            except RuntimeError as e:
                if str(e) != "simulated crash mid-save":
                    findings.append(f"  • unexpected exception: {e}")
                else:
                    notes.append("  • save_chronicle bubbled simulated crash ✓")

        # The on-disk chronicle.json must still be the ORIGINAL bytes
        if CHRON.read_bytes() != original_bytes:
            findings.append("  • chronicle.json was partially overwritten by crashed save")
        else:
            notes.append("  • chronicle.json intact after crashed save ✓")

        # The .tmp file may or may not exist. The next load must still work.
        reloaded = C.load_chronicle()
        if reloaded.get("characters", {}).get("wade_wilson", {}).get("state") != "ORIGINAL":
            findings.append(f"  • load after crashed save returned wrong data: {reloaded}")
        else:
            notes.append("  • load_chronicle returns ORIGINAL after crashed save ✓")

        # Clean any leftover .tmp so the next case starts clean
        tmp = CHRON.with_suffix(CHRON.suffix + ".tmp")
        if tmp.exists():
            tmp.unlink()

        # ── 2. apply_delta preserves pre-existing state with empty delta ──
        chron = C.load_chronicle()
        # ensure pre-existing markers
        chron["characters"]["felicia_hardy"] = {
            "state": "PRESERVE-ME", "arc": "arc-preserve",
            "recent_events": ["pre-event"]
        }
        chron["world_facts"] = [{"fact": "PRESERVE-FACT", "established_in_ep": 1}]
        chron["relationships"]["felicia_hardy__wade_wilson"] = {
            "status": "warm", "notes": "preserve-notes"
        }

        # Delta has none of the touched keys
        delta: dict = {}
        merged = C.apply_delta(
            chron, delta,
            {"number": 42, "title": "t", "cast": ["wade_wilson"], "logline": "x"},
        )
        wade = merged["characters"].get("wade_wilson", {})
        if wade.get("state") != "ORIGINAL":
            findings.append(f"  • empty delta dropped wade.state: {wade}")
        else:
            notes.append("  • empty delta preserves wade.state ✓")

        fel = merged["characters"]["felicia_hardy"]
        if fel.get("state") != "PRESERVE-ME" or fel.get("arc") != "arc-preserve":
            findings.append(f"  • empty delta dropped felicia state/arc: {fel}")
        else:
            notes.append("  • empty delta preserves felicia state/arc ✓")

        if "PRESERVE-FACT" not in [f["fact"] for f in merged["world_facts"]]:
            findings.append("  • empty delta dropped world_facts")
        else:
            notes.append("  • empty delta preserves world_facts ✓")

        rel = merged["relationships"].get("felicia_hardy__wade_wilson", {})
        if rel.get("status") != "warm":
            findings.append(f"  • empty delta dropped relationship: {rel}")
        else:
            notes.append("  • empty delta preserves relationship ✓")

        # Delta with partial keys (only add_events) must not nuke state/arc
        delta2 = {"characters": {"felicia_hardy": {"add_events": ["new-ev"]}}}
        merged2 = C.apply_delta(
            merged, delta2,
            {"number": 43, "title": "t2", "cast": ["felicia_hardy"], "logline": "y"},
        )
        fel2 = merged2["characters"]["felicia_hardy"]
        if fel2.get("state") != "PRESERVE-ME" or fel2.get("arc") != "arc-preserve":
            findings.append(f"  • partial delta dropped state/arc: {fel2}")
        else:
            notes.append("  • partial delta preserves state/arc ✓")
        if not any("new-ev" in e for e in fel2.get("recent_events", [])):
            findings.append(f"  • partial delta did not append new event: {fel2}")
        else:
            notes.append("  • partial delta appends event ✓")

        # ── 3. recover_chronicle writes a .bak ──
        bak = C.recover_chronicle()
        if bak is None or not bak.exists():
            findings.append(f"  • recover_chronicle did not create backup: {bak}")
        else:
            notes.append(f"  • recover_chronicle created backup ✓ ({bak.name})")
            bak.unlink()

    with_backup(CHRON, run)

    print("=== NOTES ===")
    for n in notes:
        print(n)
    print()
    if findings:
        print("=== FINDINGS ===")
        for f in findings:
            print(f)
        return 1
    print("HOLDS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

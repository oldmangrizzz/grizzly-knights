"""
APT-03 & APT-08 (code-level): runaway BringInCharacter + cast-coverage gate.

Both are structural questions about the runner loop. We don't fire the
LLM — we read the relevant runner logic and probe the gate logic directly.

For APT-03 (runaway BringIn): is there a per-scene cap on the number of
BringInCharacter calls? On total tool calls? On turns?

For APT-08 (cast-coverage gate bypass): the runner inspects
spoken_recipients after every director round. If [SCENE_END] is emitted
but unspoken characters remain, the runner rejects and re-cues. After
max_rounds (4) the loop EXITS regardless. So a stubborn director can
just stall through 4 rounds and the gate fails open. We assert that
behavior.

We instrument by inspecting the source and additionally simulating the
gate logic in isolation.
"""
from __future__ import annotations
import inspect, sys, re
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import engine.agency_engine as ae
import engine.scene_tools as st


def main() -> int:
    findings: list[str] = []
    notes: list[str] = []

    src = inspect.getsource(ae.run_scene)

    # ── APT-03: per-scene caps ───────────────────────────────────────────
    # Look for any explicit cap on BringInCharacter calls.
    cap_patterns = [
        r"len\(stage\.pending_arrivals\)\s*[<>]=?\s*\d+",
        r"tracker\[.?arrivals.?\]\s*[<>]=?\s*\d+",
        r"MAX_ARRIVALS|ARRIVAL_CAP|max_arrivals",
    ]
    found_cap = any(re.search(p, src) for p in cap_patterns)
    if not found_cap:
        findings.append("  • APT-03: NO per-scene cap on BringInCharacter calls in run_scene. "
                        "Cap exists only implicitly via the 'character_key must be in roster' "
                        "and 'already on stage' guards in the tool. A director that cues unique "
                        "keys can fire up to roster-size BringIn calls per scene.")

    # But the roster IS finite (currently 42 files), and each unique key
    # can only be brought in once (second time → 'already on stage'). So
    # the practical cap is roster_size.
    roster_size = len(list((ROOT / "universe" / "characters").glob("*.yaml")))
    notes.append(f"  • implicit BringIn cap = roster size = {roster_size} (each key dedups after first call)")

    # Look for caps on total scene tool calls / per-actor calls.
    if "max_tool_calls" not in src.lower() and "tool_calls_per" not in src.lower():
        notes.append("  • no max_tool_calls / tool_calls_per_actor cap in run_scene")

    # max_rounds value
    m = re.search(r"max_rounds\s*=\s*(\d+)", src)
    if m:
        notes.append(f"  • max_rounds = {m.group(1)} (hard outer-loop bound — prevents true infinite loop)")
    else:
        findings.append("  • APT-03: max_rounds NOT a constant — outer loop may be unbounded")

    # ── APT-08 (REWRITTEN for new swarm contract): state-change close gate ──
    # The old cast-coverage gate is GONE. The new gate: [SCENE_END] is only
    # honored when at least one state-change event has landed in the chronicle
    # since scene open. State-change = TakeAction-with-consequence,
    # ChangeSetting, departure, or emergent BringInCharacter. A defensive
    # spec.max_turns cap forces close anyway if the scene stalls.

    gate_holds = ("REJECTED" in src and "NOTHING HAS HAPPENED" in src
                  and "_is_state_change_event" in src)
    bounded_loop = ("for round_idx in range(max_rounds)" in src
                    and "spec.max_turns" in src)

    notes.append(f"  • state-change gate logic present: {gate_holds}")
    notes.append(f"  • outer loop bounded (max_rounds + max_turns): {bounded_loop}")

    if bounded_loop and gate_holds:
        notes.append("  • APT-08 (new contract): [SCENE_END] is REJECTED unless the "
                     "chronicle since scene open contains a TakeAction-with-consequence, "
                     "ChangeSetting, departure, or emergent BringInCharacter. The "
                     "hard turn cap (spec.max_turns, default 20) is a defensive force-"
                     "close — logged as forced. No cast-coverage gate; no folding of "
                     "phantom cast.")
    else:
        findings.append(f"  • APT-08: state-change gate structure unexpected: "
                        f"gate={gate_holds}, bounded={bounded_loop}")

    # Verify that after loop exit there is NO post-loop coverage check that
    # raises or marks the scene as failed
    if "raise" not in src.split("for round_idx")[-1].split("# ── Build transcript")[0]:
        notes.append("  • APT-08: no exception raised when coverage fails after max_rounds — "
                     "partial-coverage Script is returned silently to the caller")

    # ── Memory blowup probe for runaway BringIn ──────────────────────────
    # Simulate 1000 BringInCharacter attempts directly against the tool.
    # Confirm:
    #   - each duplicate is rejected by the tool
    #   - chronicle grows by 0 for duplicates (only first call succeeds per key)
    sid = st.register_stage(present=["felicia_hardy"],
                            roster=["felicia_hardy", "wade_wilson", "peter_parker"])
    stage = st.get_stage(sid)
    tools = {t.__name__: t for t in st.make_scene_tools(sid, "felicia_hardy")}
    BringIn = tools["BringInCharacter"]
    for i in range(1000):
        BringIn(character_key="peter_parker", how_they_arrive=f"call {i}").run()
    chron_brings = [e for e in stage.chronicle if e.get("kind") == "bring_in"]
    if len(chron_brings) > 1:
        findings.append(f"  • APT-03: 1000 BringIn calls for same key created {len(chron_brings)} chronicle entries (duplicate guard FAILED)")
    else:
        notes.append(f"  • 1000 BringIn calls for same key → {len(chron_brings)} chronicle entry (duplicate guard ✓)")
    st.drop_stage(sid)

    print("=== NOTES ===")
    for n in notes:
        print(n)
    print()
    print("=== FINDINGS ===")
    if not findings:
        print("HOLDS (with documented behaviors)")
        return 0
    for f in findings:
        print(f)
    return 1


if __name__ == "__main__":
    sys.exit(main())

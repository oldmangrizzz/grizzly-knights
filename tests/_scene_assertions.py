"""
Shared assertions for item 4 (run_scene) regression tests.

Updated for the REAL SWARM contract:

  • Every character in spec.characters (the AT-OPEN cast) spoke at least once.
  • Arrivals (spec.arrives) are NOT pre-spawned and NOT asserted — they are
    emergent (only show up if the cast calls BringInCharacter). We log
    whether any emergent arrival happened, but do not require it.
  • ≥1 scene tool call fired (BringIn / Address / TakeAction / ChangeSetting).
  • State-change landed: at least one TakeAction-with-consequence OR
    ChangeSetting OR departure OR emergent BringIn since scene open.
  • No infinite loops (run_scene has internal max_rounds + max_turns caps).
  • No [SCENE_END] leak into transcript blocks.
"""
from __future__ import annotations
import re


def _is_state_change(entry: dict) -> bool:
    k = entry.get("kind", "")
    if k in ("change_setting", "departure", "bring_in"):
        return True
    if k == "action":
        c = entry.get("consequence") or ""
        if isinstance(c, str) and c.strip():
            return True
    return False


def assert_scene(script, spec, label: str, *, allow_departure=False) -> tuple[bool, list[str]]:
    failures: list[str] = []
    msgs: list[str] = []

    initial = set(spec.characters)
    msgs.append(f"[{label}] at-open cast: {sorted(initial)}")

    spoken = {b.character for b in script.blocks
              if b.type == "dialogue" and b.character}
    msgs.append(f"[{label}] spoke (blocks): {sorted(spoken)}")

    missing = initial - spoken
    if missing:
        failures.append(f"at-open cast members never spoke: {sorted(missing)}")

    tcs = getattr(script, "_gk_tool_calls", []) or []
    msgs.append(f"[{label}] tool calls: {len(tcs)}")
    scene_tool_calls = [t for t in tcs
                        if t.get("tool") in {"BringInCharacter", "AddressCharacter",
                                              "TakeAction", "ChangeSetting"}]
    msgs.append(f"[{label}] scene tool calls (chronicle): {len(scene_tool_calls)}")
    if len(scene_tool_calls) < 1:
        failures.append(f"too few scene-tool calls: {len(scene_tool_calls)} (need ≥1)")

    chronicle = getattr(script, "_gk_chronicle", []) or []
    state_change = any(_is_state_change(e) for e in chronicle)
    msgs.append(f"[{label}] state_change_landed: {state_change}")
    if not state_change:
        # Soft-fail: a scene that ran to the turn cap with no state-change is
        # a flat scene, but the engine may have forced-closed it. Report.
        forced = getattr(script, "_gk_forced_close", False)
        if forced:
            msgs.append(f"[{label}] WARN: forced close at turn cap, no state-change")
        failures.append("no state-change event landed in chronicle "
                        "(scene was flat — no TakeAction-with-consequence, "
                        "no ChangeSetting, no departure, no emergent BringIn)")

    # Tool-error filter sanity
    dropped = getattr(script, "_gk_dropped_tool_artifact_lines", 0) or 0
    msgs.append(f"[{label}] dropped tool-artifact lines: {dropped}")
    for b in script.blocks:
        t = (b.text or "")
        if "[SCENE_END]" in t:
            failures.append(f"[SCENE_END] leaked into block: {t[:80]}")
            break
        low = t.lower()
        if low.startswith("error:") or "for tool send_message" in low:
            failures.append(f"tool-artifact leaked into block: {t[:80]}")
            break

    # Departure: if the spec declares departures, log whether referenced
    if (spec.departs or []) and allow_departure:
        dep_keys = {d.get("key") for d in spec.departs if isinstance(d, dict) and d.get("key")}
        depart_referenced = False
        for entry in chronicle:
            payload_blob = " ".join(str(v) for v in entry.values() if isinstance(v, str))
            for dkey in dep_keys:
                short = dkey.split("_")[0]
                if short and short.lower() in payload_blob.lower():
                    depart_referenced = True
                    break
            if depart_referenced:
                break
        msgs.append(f"[{label}] departure_referenced: {depart_referenced}")
        # Soft — do not fail, just record.

    return (len(failures) == 0), [*msgs, *(f"FAIL: {f}" for f in failures)]


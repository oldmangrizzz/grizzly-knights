"""
APT-02b — planner schema (offline).

Feeds malformed plan JSON dicts straight to PlanEpisode / PlanScene.
No live LLM. Verifies:

  • valid plan accepted
  • missing required fields → ValidationError
  • negative ints rejected
  • oversized strings (>4000 chars) rejected
  • _plan_async style downstream: PlanValidationError surfaces the payload
  • PlanRefusedError carries the raw refusal text

Exit 0 if every assertion holds; 1 otherwise.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from pydantic import ValidationError

from engine.agency_engine import (
    PlanScene, PlanEpisode,
    PlanRefusedError, PlanValidationError,
)


def _assert(cond: bool, msg: str, findings: list[str]) -> None:
    if not cond:
        findings.append(f"  • {msg}")


def main() -> int:
    findings: list[str] = []

    # ── 1. Valid plan accepted ───────────────────────────────────────────
    good = {
        "title":  "Quiet Night at the Bar",
        "arc":    "Felicia and Wade trade scars over whiskey.",
        "cast":   ["felicia_hardy", "wade_wilson"],
        "scenes": [
            {
                "act":          1,
                "scene_number": 1,
                "location":     "Skinny Dennis, Williamsburg, 2 AM",
                "time":         "after-midnight",
                "situation":    "They are already two drinks in.",
                "arrives":      [],
                "departs":      [],
                "escalation":   "Someone admits something true.",
            }
        ],
    }
    try:
        ep = PlanEpisode.model_validate(good)
        _assert(ep.title == good["title"], "PlanEpisode lost title", findings)
        _assert(ep.cast == good["cast"], "PlanEpisode lost cast", findings)
        _assert(len(ep.scenes) == 1, "PlanEpisode lost scenes", findings)
    except ValidationError as e:
        findings.append(f"  • valid plan rejected: {e}")

    # ── 2. Missing required fields → ValidationError ─────────────────────
    bad_missing_title = dict(good); bad_missing_title.pop("title")
    try:
        PlanEpisode.model_validate(bad_missing_title)
        findings.append("  • missing 'title' was silently accepted")
    except ValidationError:
        pass

    bad_missing_cast = dict(good); bad_missing_cast.pop("cast")
    try:
        PlanEpisode.model_validate(bad_missing_cast)
        findings.append("  • missing 'cast' was silently accepted")
    except ValidationError:
        pass

    bad_missing_scenes = dict(good); bad_missing_scenes.pop("scenes")
    try:
        PlanEpisode.model_validate(bad_missing_scenes)
        findings.append("  • missing 'scenes' was silently accepted")
    except ValidationError:
        pass

    # Per-scene missing required field (location)
    bad_scene_missing_loc = {"act": 1, "situation": "x"}
    try:
        PlanScene.model_validate(bad_scene_missing_loc)
        findings.append("  • scene missing 'location' was silently accepted")
    except ValidationError:
        pass

    # ── 3. Negative ints rejected ────────────────────────────────────────
    try:
        PlanScene.model_validate({"act": -1, "location": "x", "situation": "x"})
        findings.append("  • PlanScene accepted act=-1")
    except ValidationError:
        pass
    try:
        PlanScene.model_validate({"act": 0, "scene_number": -7,
                                  "location": "x", "situation": "x"})
        findings.append("  • PlanScene accepted scene_number=-7")
    except ValidationError:
        pass

    # ── 4. Oversized strings rejected (>4000 chars) ──────────────────────
    huge = "x" * 5000
    try:
        PlanScene.model_validate({"act": 1, "location": huge, "situation": "x"})
        findings.append("  • PlanScene accepted 5000-char location")
    except ValidationError:
        pass
    try:
        PlanScene.model_validate({"act": 1, "location": "x", "situation": huge})
        findings.append("  • PlanScene accepted 5000-char situation")
    except ValidationError:
        pass
    try:
        PlanEpisode.model_validate({**good, "title": huge})
        findings.append("  • PlanEpisode accepted 5000-char title")
    except ValidationError:
        pass

    # ── 5. Hostile payload shapes (the original APT-02 crash drivers) ────
    # 'data["cast"]' KeyError driver: cast key missing entirely
    no_cast = {"title": "T", "scenes": [
        {"act": 1, "location": "x", "situation": "x"}
    ]}
    try:
        PlanEpisode.model_validate(no_cast)
        findings.append("  • plan with no cast key was silently accepted")
    except ValidationError:
        pass

    # cast present but not a list
    cast_not_list = dict(good); cast_not_list["cast"] = "felicia_hardy"
    try:
        PlanEpisode.model_validate(cast_not_list)
        # pydantic may coerce single str → list[str]? we explicitly want list
        findings.append("  • plan with cast as str was silently accepted")
    except ValidationError:
        pass

    # scenes as a dict instead of list
    scenes_not_list = dict(good); scenes_not_list["scenes"] = {"act": 1}
    try:
        PlanEpisode.model_validate(scenes_not_list)
        findings.append("  • plan with scenes as dict was silently accepted")
    except ValidationError:
        pass

    # ── 6. PlanValidationError / PlanRefusedError carry payload ──────────
    bad_payload = {"title": "T", "cast": [], "scenes": [{"act": -1, "location": "x", "situation": "x"}]}
    try:
        PlanEpisode.model_validate(bad_payload)
        findings.append("  • bad_payload silently accepted")
    except ValidationError as e:
        wrapper = PlanValidationError(payload=bad_payload, errors=e.errors(), attempts=3)
        _assert(wrapper.payload is bad_payload, "PlanValidationError did not retain payload", findings)
        _assert(wrapper.attempts == 3, "PlanValidationError did not retain attempts", findings)
        _assert(wrapper.errors, "PlanValidationError errors empty", findings)

    refuse = PlanRefusedError(raw="I am Uatu. I cannot comply.", attempts=3)
    _assert(refuse.raw.startswith("I am Uatu"), "PlanRefusedError lost raw", findings)
    _assert(refuse.attempts == 3, "PlanRefusedError lost attempts", findings)

    # ── 7. arrives/departs blank keys filtered ───────────────────────────
    scene = PlanScene.model_validate({
        "act": 1, "location": "x", "situation": "x",
        "arrives": [
            {"key": "felicia_hardy", "how": "via wade"},
            {"key": "", "how": "blank"},
            {"key": None, "how": "none"},
        ],
        "departs": [
            {"key": "wade_wilson"},
            {"key": ""},
        ],
    })
    arrive_keys = [a["key"] for a in scene.arrives]
    depart_keys = [d["key"] for d in scene.departs]
    _assert(arrive_keys == ["felicia_hardy"], f"arrives not filtered: {arrive_keys}", findings)
    _assert(depart_keys == ["wade_wilson"],   f"departs not filtered: {depart_keys}", findings)

    print("=== FINDINGS ===")
    if not findings:
        print("HOLDS — planner schema rejects malformed payloads cleanly.")
        return 0
    for f in findings:
        print(f)
    return 1


if __name__ == "__main__":
    sys.exit(main())

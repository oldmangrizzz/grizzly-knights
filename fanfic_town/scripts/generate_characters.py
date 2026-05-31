#!/usr/bin/env python3
"""
Reads YAML character profiles from ../universe/characters and regenerates
data/characters.ts in this fork. Sprite slots cycle through the 11 sprites
that ship with AI Town. Identity prompt is built from key YAML fields.

Run from anywhere:  python3 scripts/generate_characters.py
"""
import yaml, os, glob, json, sys, pathlib

HERE = pathlib.Path(__file__).resolve().parent.parent
CHARS_DIR = (HERE.parent / "universe" / "characters").resolve()
OUT_FILE = HERE / "data" / "characters.ts"

SPRITE_SLOTS = ["f1","f2","f3","f4","f5","f6","f7","f8","p1","p2","p3"]

# Heterogeneous model fleet — Ollama Cloud, all general-purpose chat-capable.
# Rotates across characters so the research can compare voice fidelity per model.
# Override per character via `model:` in YAML.
# Heterogeneous NPC reasoner fleet. Round-robin assignment diversifies models across
# the cast (between any two uses of a model, all others appear). OPUS IS DELIBERATELY
# EXCLUDED — Opus tier is reserved for the UATU compiler, never for NPC runtime.
# Copilot entries are 1x/standard tier (verify multipliers before adding premium models).
# Model IDs verified live against api.githubcopilot.com/models and `ollama` on 2026-05-30.
MODEL_FLEET = [
    # GitHub Copilot Pro+ — 1x / standard tier (routed via copilot-api proxy, copilot/ prefix)
    "copilot/gpt-4o",
    "copilot/gpt-4.1",
    "copilot/gpt-4o-mini",
    "copilot/gpt-5.4-mini",
    "copilot/gpt-5-mini",
    "copilot/claude-haiku-4.5",
    "copilot/gemini-2.5-pro",
    # Ollama Cloud — the ENTIRE live catalog (discovered from ollama.com/search?c=cloud on
    # 2026-05-30). Every cloud model represented; no Copilot premium cost; routed via OLLAMA_HOST.
    "deepseek-v3.2:cloud",
    "deepseek-v4-flash:cloud",
    "deepseek-v4-pro:cloud",
    "devstral-small-2:cloud",
    "gemini-3-flash-preview:cloud",
    "gemma4:cloud",
    "glm-4.7:cloud",
    "glm-5:cloud",
    "glm-5.1:cloud",
    "kimi-k2.6:cloud",
    "minimax-m2.1:cloud",
    "minimax-m2.5:cloud",
    "minimax-m2.7:cloud",
    "ministral-3:cloud",
    "nemotron-3-nano:cloud",
    "nemotron-3-super:cloud",
    "qwen3-coder-next:cloud",
    "qwen3-next:cloud",
    "qwen3.5:cloud",
    "rnj-1:cloud",
    # OpenRouter — FREE models only (':free'; hard-guarded in llm.ts so paid is unreachable).
    # Chosen for architectures NOT already in the Ollama set, to maximize reasoner diversity.
    "openrouter/meta-llama/llama-3.3-70b-instruct:free",
    "openrouter/nousresearch/hermes-3-llama-3.1-405b:free",
    "openrouter/openai/gpt-oss-120b:free",
    "openrouter/openai/gpt-oss-20b:free",
    "openrouter/cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
    "openrouter/z-ai/glm-4.5-air:free",
    "openrouter/poolside/laguna-m.1:free",
    "openrouter/liquid/lfm-2.5-1.2b-thinking:free",
    "openrouter/google/gemma-4-31b-it:free",
    "openrouter/nvidia/nemotron-3-super-120b-a12b:free",
]

IDENTITY_CAP = 12000
PLAN_CAP = 1000


def _flat(v):
    if v is None: return ""
    if isinstance(v, str): return v.strip()
    if isinstance(v, (list, tuple)):
        return "; ".join(_flat(x) for x in v if x)
    if isinstance(v, dict):
        return "; ".join(f"{k}: {_flat(val)}" for k, val in v.items() if val)
    return str(v)


def _slug_to_display(files):
    """Build map: yaml-stem (e.g. 'peter_parker') -> display name used in sim ('Spider-Man' if alias else name)."""
    m = {}
    for fp in files:
        stem = pathlib.Path(fp).stem
        with open(fp) as fh:
            d = yaml.safe_load(fh) or {}
        name = (d.get("name") or "").strip()
        alias = (d.get("alias") or "").strip()
        display = alias if alias else name
        if display:
            m[stem] = display
    return m


def build_relationships_block(d: dict, slug_to_display: dict) -> str:
    rels = d.get("canon_relationships") or {}
    if not isinstance(rels, dict) or not rels:
        return ""
    active = {}
    for entry in (d.get("current_state_defaults") or {}).get("active_relationships") or []:
        if isinstance(entry, str) and ":" in entry:
            k, v = entry.split(":", 1)
            active[k.strip()] = v.strip()
    lines = []
    for slug, body in rels.items():
        display = slug_to_display.get(slug)
        if not display:
            continue  # only surface relationships with characters actually present in the sim
        body_txt = _flat(body)
        if not body_txt:
            continue
        tag = active.get(slug)
        prefix = f"WITH {display}"
        if tag:
            prefix += f" [{tag}]"
        lines.append(f"{prefix}: {body_txt}")
    if not lines:
        return ""
    return "RELATIONSHIPS — what YOU know about people you may meet here:\n" + "\n".join(lines)


def build_diagnostic_block(d: dict) -> str:
    """The perception-vs-reality frame. Leads the identity so the NPC plays the
    clinical truth, not the fandom cliché. This is the spine of the method."""
    df = d.get("diagnostic_frame")
    if not isinstance(df, dict) or not df:
        return ""
    lines = []
    mis = _flat(df.get("popular_misread"))
    real = _flat(df.get("clinical_reality"))
    if mis:  lines.append(f"DO NOT PLAY THE CLICHÉ — people misread you as: {mis}")
    if real: lines.append(f"WHO YOU ACTUALLY ARE: {real}")
    extra = [_flat(v) for k, v in df.items()
             if k not in ("popular_misread", "clinical_reality") and _flat(v)]
    if extra:
        lines.append("THE TRUTH UNDERNEATH: " + " ".join(extra))
    return "\n".join(lines)


def build_compensatory_block(d: dict) -> str:
    """Healthy reaches vs. self-sabotage — the etiology/maintenance split made behavioral."""
    cm = d.get("compensatory_mechanisms")
    if not isinstance(cm, dict) or not cm:
        return ""
    out = []
    pos = _flat(cm.get("positive"))
    neg = _flat(cm.get("negative"))
    if pos: out.append(f"HOW YOU COPE (the healthy reaches): {pos}")
    if neg: out.append(f"HOW YOU SABOTAGE YOURSELF (the maintenance failures — the part that's your fault): {neg}")
    return "\n".join(out)


def build_ic_block(d: dict) -> str:
    """The IC behavioral profile — what tells the NPC how to ACT, DECIDE, and REACT in an
    unrehearsed scene. This is the operating manual the reasoner actually runs on."""
    out = []
    bl = _flat(d.get("bottom_line"))
    if bl: out.append(f"BOTTOM LINE (who you are, operationally): {bl}")
    drv = d.get("drive_structure")
    if isinstance(drv, dict) and _flat(drv): out.append(f"WHAT DRIVES YOU: {_flat(drv)}")
    oc = d.get("operational_code")
    if isinstance(oc, dict) and _flat(oc): out.append(f"HOW YOU READ THE WORLD: {_flat(oc)}")
    cog = d.get("cognitive_decision_style")
    if isinstance(cog, dict) and _flat(cog): out.append(f"HOW YOU DECIDE: {_flat(cog)}")
    ip = d.get("interpersonal_style")
    if isinstance(ip, dict) and _flat(ip): out.append(f"WITH OTHER PEOPLE: {_flat(ip)}")
    sym = _flat(d.get("symptom_as_signature"))
    if sym: out.append(f"YOUR POWER IS YOUR WOUND MADE LITERAL: {sym}")
    sep = d.get("stress_escalation_profile")
    if isinstance(sep, dict) and _flat(sep): out.append(f"UNDER STRESS: {_flat(sep)}")
    sr = d.get("stimulus_response")
    if isinstance(sr, list) and sr:
        rules = [f"  - {_flat(x)}" for x in sr if _flat(x)]
        if rules: out.append("HOW YOU REACT (run these in a scene):\n" + "\n".join(rules))
    return "\n".join(out)


def build_identity(d: dict, slug_to_display: dict) -> str:
    name = (d.get("name") or "").strip()
    alias = (d.get("alias") or "").strip()
    voice = _flat(d.get("voice") or d.get("voice_profile") or d.get("speech") or d.get("speech_patterns"))
    core = _flat(d.get("core_identity") or d.get("identity"))
    psych = _flat(d.get("primary_diagnoses_analog"))
    trauma = _flat(d.get("trauma_history"))
    tells = _flat(d.get("behavioral_tells"))
    do = _flat(d.get("do") or d.get("voice_rules_do"))
    dont = _flat(d.get("dont") or d.get("voice_rules_dont"))
    diag = build_diagnostic_block(d)
    ic = build_ic_block(d)
    comp = build_compensatory_block(d)
    anchors = [a for a in (d.get("canon_anchor_quotes") or []) if _flat(a)]
    rels_block = build_relationships_block(d, slug_to_display)

    parts = [f"You are {name}" + (f" ({alias})" if alias and alias != name else "") + "."]
    # Grizzly Knights: the diagnostic frame LEADS — who they actually are vs. the misread
    if diag:   parts.append(diag)
    # then the IC behavioral profile — how to ACT/DECIDE/REACT (the operating manual)
    if ic:     parts.append(ic)
    if psych:  parts.append(f"PSYCH (correct canon): {psych}")
    if tells:  parts.append(f"BEHAVIORAL TELLS: {tells}")
    if voice:  parts.append(f"HOW YOU TALK: {voice}")
    if comp:   parts.append(comp)
    if trauma: parts.append(f"WHAT BROKE YOU: {trauma}")
    if anchors:
        quoted = " / ".join('"' + _flat(a) + '"' for a in anchors)
        parts.append(f"IN YOUR OWN WORDS (canon voice — match this register): {quoted}")
    if core:   parts.append(f"CORE IDENTITY: {core}")
    if do:     parts.append(f"DO: {do}")
    if dont:   parts.append(f"DON'T: {dont}")
    if rels_block: parts.append(rels_block)
    text = "\n".join(parts)
    if len(text) > IDENTITY_CAP:
        # try not to amputate the relationships block
        if rels_block and text.find(rels_block) != -1 and text.find(rels_block) < IDENTITY_CAP - 400:
            head = text[: text.find(rels_block)]
            avail = IDENTITY_CAP - len(rels_block) - 16
            if avail > 200:
                head = head[:avail].rsplit(" ", 1)[0] + "…\n"
                text = head + rels_block
            else:
                text = text[:IDENTITY_CAP].rsplit(" ", 1)[0] + "…"
        else:
            text = text[:IDENTITY_CAP].rsplit(" ", 1)[0] + "…"
    return text


def build_plan(d: dict) -> str:
    arc = _flat(d.get("arc_tendencies"))
    goals = _flat(d.get("goals") or d.get("current_goals") or d.get("plan"))
    state = (d.get("current_state_defaults") or {})
    baseline = _flat({k: v for k, v in state.items() if k in (
        "emotional_regulation_status", "affect_baseline", "known_location"
    )})
    parts = []
    if goals: parts.append(f"GOALS: {goals}")
    if arc:   parts.append(f"ARC: {arc}")
    if baseline: parts.append(f"STATE: {baseline}")
    if not parts:
        return "You go about your day, talk to people you find, and stay in character."
    text = " | ".join(parts)
    if len(text) > PLAN_CAP:
        text = text[:PLAN_CAP].rsplit(" ", 1)[0] + "…"
    return text


def ts_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")


def main():
    if not CHARS_DIR.is_dir():
        print(f"FATAL: characters dir not found: {CHARS_DIR}", file=sys.stderr)
        sys.exit(1)

    files = sorted(glob.glob(str(CHARS_DIR / "*.yaml")))
    slug_to_display = _slug_to_display(files)
    # detect alias collisions; for collisions, fall back to "Real Name (Alias)" disambiguation
    raw = []
    for fp in files:
        with open(fp) as fh:
            d = yaml.safe_load(fh) or {}
        raw.append((fp, d))
    alias_count = {}
    for _, d in raw:
        a = (d.get("alias") or "").strip()
        if a:
            alias_count[a] = alias_count.get(a, 0) + 1

    def display_name(d):
        name = (d.get("name") or "").strip()
        alias = (d.get("alias") or "").strip()
        if alias and alias_count.get(alias, 0) > 1:
            return f"{name} ({alias})"
        return alias if alias else name

    # rebuild slug_to_display with disambiguation
    slug_to_display = {}
    for fp, d in raw:
        stem = pathlib.Path(fp).stem
        dn = display_name(d)
        if dn:
            slug_to_display[stem] = dn

    descs = []
    char_assets = {} # Grizzly Knights: track unique character visual assets
    for i, (fp, d) in enumerate(raw):
        name = (d.get("name") or "").strip()
        if not name:
            continue
        display = display_name(d)
        
        # Grizzly Knights: Support explicit sprite slots and texture URLs
        sprite_slot = (d.get("character") or "").strip()
        if not sprite_slot:
            sprite_slot = SPRITE_SLOTS[i % len(SPRITE_SLOTS)]
        
        texture_url = (d.get("texture_url") or "/ai-town/assets/32x32folk.png").strip()
        
        if sprite_slot not in char_assets:
            char_assets[sprite_slot] = texture_url

        descs.append({
            "name": display,
            "character": sprite_slot,
            "identity": build_identity(d, slug_to_display),
            "plan": build_plan(d),
            "model": (d.get("model") or "").strip() or MODEL_FLEET[i % len(MODEL_FLEET)],
        })

    lines = []
    lines.append("// AUTO-GENERATED from ../universe/characters/*.yaml")
    lines.append("// Regenerate: python3 scripts/generate_characters.py")
    lines.append("// DO NOT hand-edit. Edit YAML in /Users/rbhanson/fanfic/universe/characters/.")
    lines.append("")
    # Grizzly Knights: Import all spritesheets that might be used
    for s in sorted(set(SPRITE_SLOTS) | set(char_assets.keys())):
        # We assume for now that if a custom sprite slot is used, its TS exists in data/spritesheets/
        lines.append(f"import {{ data as {s}SpritesheetData }} from './spritesheets/{s}';")
    lines.append("")
    lines.append("export const Descriptions = [")
    for d in descs:
        lines.append("  {")
        lines.append(f"    name: {json.dumps(d['name'])},")
        lines.append(f"    character: {json.dumps(d['character'])},")
        lines.append(f"    identity: `{ts_escape(d['identity'])}`,")
        lines.append(f"    plan: `{ts_escape(d['plan'])}`,")
        lines.append("  },")
    lines.append("];")
    lines.append("")
    lines.append("// Per-character model assignment. Lookup by display name.")
    lines.append("// Heterogeneous on purpose — research demands non-identical reasoners.")
    lines.append("export const characterModels: Record<string, string> = {")
    for d in descs:
        lines.append(f"  {json.dumps(d['name'])}: {json.dumps(d['model'])},")
    lines.append("};")
    lines.append("")
    lines.append("export const characters = [")
    for s, tex in sorted(char_assets.items()):
        lines.append("  {")
        lines.append(f"    name: {json.dumps(s)},")
        lines.append(f"    textureUrl: {json.dumps(tex)},")
        lines.append(f"    spritesheetData: {s}SpritesheetData,")
        lines.append("    speed: 0.1,")
        lines.append("  },")
    lines.append("];")
    lines.append("")
    lines.append("export const movementSpeed = 0.75;")

    OUT_FILE.write_text("\n".join(lines))
    print(f"wrote {OUT_FILE} with {len(descs)} characters")
    # quick sanity: count how many relationship edges are surfaced into the cast
    edge_count = 0
    cast_displays = {x["name"] for x in descs}
    for fp in files:
        with open(fp) as fh:
            dd = yaml.safe_load(fh) or {}
        for slug in (dd.get("canon_relationships") or {}):
            if slug_to_display.get(slug) in cast_displays:
                edge_count += 1
    print(f"surfaced {edge_count} character-to-character relationship edges")


if __name__ == "__main__":
    main()

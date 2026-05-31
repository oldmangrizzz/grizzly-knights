#!/usr/bin/env python3
"""
Build the Grizzly Knights Obsidian vault from the character YAMLs.

The operator cannot read YAML. This renders every profile into a readable Markdown
note with the relationship graph wired as [[wikilinks]], so he can scroll the
personality database and Obsidian's graph view in the GUI.

Run:  python3 scripts/build_vault.py
"""
import yaml, glob, pathlib, re, shutil

HERE = pathlib.Path(__file__).resolve().parent.parent
CHARS = (HERE / "universe" / "characters").resolve()
VAULT = (HERE / "GrizzlyKnights_Vault").resolve()
VAULT.mkdir(exist_ok=True)


def load_all():
    out = {}
    for fp in sorted(glob.glob(str(CHARS / "*.yaml"))):
        p = pathlib.Path(fp)
        if p.stat().st_size == 0:
            continue
        try:
            d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        if isinstance(d, dict) and d.get("name"):
            out[p.stem] = d
    return out


def display_of(d):
    name = (d.get("name") or "").strip()
    alias = (d.get("alias") or "").strip()
    if alias and alias.lower() not in ("", "none") and alias != name:
        return f"{name} ({alias})"
    return name


def pretty(key):
    return key.replace("_", " ").title()


def link_stem(stem, stem2disp):
    disp = stem2disp.get(stem)
    return f"[[{disp}]]" if disp else stem.replace("_", " ").title()


def render(val, stem2disp, indent=0):
    pad = "  " * indent
    if isinstance(val, str):
        return val.strip()
    if isinstance(val, (int, float, bool)) or val is None:
        return str(val)
    if isinstance(val, list):
        lines = []
        for item in val:
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}-")
                lines.append(render(item, stem2disp, indent + 1))
            else:
                lines.append(f"{pad}- {str(item).strip()}")
        return "\n".join(lines)
    if isinstance(val, dict):
        lines = []
        for k, v in val.items():
            if isinstance(v, (dict, list)):
                lines.append(f"{pad}- **{pretty(k)}:**")
                lines.append(render(v, stem2disp, indent + 1))
            else:
                lines.append(f"{pad}- **{pretty(k)}:** {str(v).strip()}")
        return "\n".join(lines)
    return str(val)


def render_relationships(rels, stem2disp):
    """canon_relationships: keys are stems -> wikilink headings."""
    out = []
    for stem, body in rels.items():
        out.append(f"### {link_stem(stem, stem2disp)}")
        if isinstance(body, list):
            for b in body:
                out.append(f"- {str(b).strip()}")
        else:
            out.append(str(body).strip())
        out.append("")
    return "\n".join(out)


def render_active_rels(items, stem2disp):
    out = []
    for it in items:
        s = str(it)
        if ":" in s:
            stem, tag = s.split(":", 1)
            out.append(f"- {link_stem(stem.strip(), stem2disp)} — {tag.strip()}")
        else:
            out.append(f"- {link_stem(s.strip(), stem2disp)}")
    return "\n".join(out)


# section ordering preference (IC instrument first, clinical substrate after)
ORDER = [
    "bottom_line", "drive_structure", "operational_code", "symptom_as_signature",
    "cognitive_decision_style", "interpersonal_style", "stress_escalation_profile",
    "stimulus_response", "pressure_points_and_levers", "strengths_and_exploitable_weaknesses",
    "voice", "diagnostic_frame", "canon_anchor_quotes", "primary_diagnoses_analog",
    "trauma_history", "compensatory_mechanisms", "behavioral_tells", "speech_patterns",
    "current_state_defaults", "arc_tendencies", "canon_relationships",
    "canon_history_notes", "canon_compensatory_specifics", "clinical_provenance",
]
SKIP = {"name", "alias", "voice_id_key"}


def build():
    chars = load_all()
    stem2disp = {stem: display_of(d) for stem, d in chars.items()}

    # clear stale notes (names can change between engine runs -> orphaned files); all notes are regenerated
    for old in VAULT.glob("*.md"):
        old.unlink()

    # mirror generated portraits into the vault so the notes can embed them
    portrait_src = HERE / "world_art" / "portraits"
    attach = VAULT / "_attachments"
    attach.mkdir(exist_ok=True)
    portraits = {}
    if portrait_src.exists():
        for png in portrait_src.glob("*.png"):
            shutil.copy(png, attach / png.name)
            portraits[png.stem] = png.name

    for stem, d in chars.items():
        disp = stem2disp[stem]
        lines = []
        # frontmatter
        lines.append("---")
        lines.append(f'aliases: ["{(d.get("alias") or "").strip()}", "{(d.get("name") or "").strip()}"]')
        lines.append(f"voice_id_key: {stem}")
        lines.append("tags: [grizzly-knights, personality-profile]")
        lines.append("---")
        lines.append(f"# {d.get('name','').strip()}" + (f"  —  *{d.get('alias').strip()}*" if d.get("alias") else ""))
        lines.append("")
        if stem in portraits:
            lines.append(f"![[_attachments/{portraits[stem]}]]")
            lines.append("")

        # If a FULL DOSSIER exists, that IS the note (the structured profile is for the runtime).
        dossier_path = HERE / "recovery_research" / "_dossiers" / f"{stem}.md"
        if dossier_path.exists() and dossier_path.stat().st_size > 2000:
            lines.append(dossier_path.read_text(encoding="utf-8").strip())
            lines.append("")
            rels = d.get("canon_relationships")
            if isinstance(rels, dict) and rels:
                lines.append("## Relationship Graph")
                lines.append(render_relationships(rels, stem2disp))
            (VAULT / f"{disp.replace('/', '-')}.md").write_text("\n".join(lines), encoding="utf-8")
            continue

        keys = [k for k in ORDER if k in d] + [k for k in d if k not in ORDER and k not in SKIP]
        for k in keys:
            v = d[k]
            lines.append(f"## {pretty(k)}")
            if k == "canon_relationships" and isinstance(v, dict):
                lines.append(render_relationships(v, stem2disp))
            elif k == "current_state_defaults" and isinstance(v, dict):
                body = dict(v)
                ar = body.pop("active_relationships", None)
                lines.append(render(body, stem2disp))
                if ar:
                    lines.append("- **Active Relationships:**")
                    lines.append(render_active_rels(ar, stem2disp))
            else:
                lines.append(render(v, stem2disp))
            lines.append("")

        # fold in the stage-1 analytical dossier (the reverse-engineering) so the read is the FULL file,
        # not just the synthesized profile
        an_path = HERE / "recovery_research" / "_engine_out" / f"{stem}.analysis.md"
        if an_path.exists() and an_path.stat().st_size > 0:
            lines.append("---")
            lines.append("")
            lines.append("## 📂 Analytical Dossier — Stage 1 (UATU reverse-engineering: history / medical / psychological / psychiatric / personality)")
            lines.append("")
            lines.append(an_path.read_text(encoding="utf-8").strip())
            lines.append("")

        (VAULT / f"{disp.replace('/', '-')}.md").write_text("\n".join(lines), encoding="utf-8")

    # Home index
    idx = ["# Grizzly Knights — Personality Database", "",
           f"{len(chars)} profiles. Open the **graph view** (left sidebar) to see the relationship web.",
           "Each note is an IC-style personality profile built by the UATU engine (or hand-built, pending re-cut).",
           "", "## Roster", ""]
    for stem in sorted(chars, key=lambda s: stem2disp[s]):
        idx.append(f"- [[{stem2disp[stem]}]]")
    idx.append("")
    idx.append("## World")
    idx.append("- [[World Gallery]] — portraits, environments & key scenes")
    (VAULT / "Home.md").write_text("\n".join(idx), encoding="utf-8")

    # mirror scene plates and build a browsable gallery note
    scene_src = HERE / "world_art" / "scenes"
    scenes = {}
    if scene_src.exists():
        for png in scene_src.glob("*.png"):
            shutil.copy(png, attach / png.name)
            scenes[png.stem] = png.name
    gal = ["# World Gallery", "",
           "Generated imagery for the Grizzly Knights world (FLUX). Regenerated with the vault.", ""]
    gal.append("## Character Portraits"); gal.append("")
    for stem in sorted(portraits, key=lambda s: stem2disp.get(s, s)):
        gal.append(f"### {stem2disp.get(stem, pretty(stem))}")
        gal.append(f"![[_attachments/{portraits[stem]}]]")
        gal.append("")
    if scenes:
        gal.append("## Environments & Scenes"); gal.append("")
        for key in sorted(scenes):
            gal.append(f"### {pretty(key)}")
            gal.append(f"![[_attachments/{scenes[key]}]]")
            gal.append("")
    (VAULT / "World Gallery.md").write_text("\n".join(gal), encoding="utf-8")
    print(f"vault built: {len(chars)} notes, {len(portraits)} portraits, {len(scenes)} scenes -> {VAULT}")


if __name__ == "__main__":
    build()

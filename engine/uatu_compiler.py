"""
UATU — the profile compiler.

The Watcher does not interfere. He observes, records, and renders truth.
This module is the engine that turns the OPERATOR'S METHOD into a repeatable
procedure: given a character, source the real clinical literature and the
decades of free public canon, adjudicate perception-vs-reality, and emit a
gold-standard psychological profile in the standardized schema.

What lives here (all runtime-independent and correct regardless of which LLM
executes the compile step):

  1. SCHEMA          — the contract every profile must satisfy to be "gold."
  2. validate_profile / validate_file / validate_all — the acceptance gate.
  3. UATU_METHOD     — the operator's method, encoded as the compiler's brain
                       (the system prompt the LLM runtime executes).
  4. emit_yaml       — assemble a structured profile dict into schema-ordered
                       YAML that matches the hand-built gold files.

What is intentionally NOT decided here (the runtime fork — see compile_profile):
  - whether the compile step runs as a tool-using AGENT (live retrieval from the
    PubMed/PMC + arXiv + web sources, with citations) or as a STANDALONE API call
    against an operator-curated reference dossier.

The hand-built gold set (Reed, Victor) is the calibration target: UATU is
"working" when it emits profiles that pass this validator AND that the operator
signs off as matching what he would have written by hand.
"""

from __future__ import annotations
import sys
import re
import glob
import pathlib
from dataclasses import dataclass, field

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

HERE = pathlib.Path(__file__).resolve().parent.parent
CHARS_DIR = (HERE / "universe" / "characters").resolve()


# ──────────────────────────────────────────────────────────────────────────
# 1. THE SCHEMA CONTRACT
#    Required keys are FAIL-on-missing. Gold keys are WARN-on-missing and feed
#    the completeness score. The diagnostic frame is the spine of the method, so
#    its presence (with the refutation) is graded hardest.
# ──────────────────────────────────────────────────────────────────────────

# Hard requirements — without these a profile is not usable by the engine.
REQUIRED_KEYS = {
    "name":                    str,
    "voice_id_key":            str,
    "primary_diagnoses_analog": list,
    "trauma_history":          list,
}

# Gold-standard keys — the difference between a stub and a real UATU profile.
GOLD_KEYS = [
    # 'alias' intentionally NOT scored — many real people have no codename (MJ, etc.)
    "diagnostic_frame",        # the perception-vs-reality spine
    "canon_anchor_quotes",     # the voice fingerprint
    "compensatory_mechanisms",
    "behavioral_tells",
    "speech_patterns",
    "arc_tendencies",
    "current_state_defaults",
    "canon_relationships",
    "canon_history_notes",
]

# The diagnostic_frame is the method made structural. These two sub-keys carry
# the refutation; without both, the profile is playing the cliché.
DIAGNOSTIC_FRAME_REQUIRED = ["popular_misread", "clinical_reality"]


@dataclass
class Report:
    stem: str
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    completeness: float = 0.0

    @property
    def ok(self) -> bool:
        return not self.errors

    @property
    def gold(self) -> bool:
        return self.ok and self.completeness >= 0.95

    def line(self) -> str:
        if self.gold:
            tag = "GOLD "
        elif self.ok:
            tag = "OK   "
        else:
            tag = "FAIL "
        return f"{tag} {self.completeness*100:5.0f}%  {self.stem:22}  " \
               f"{len(self.errors)} err / {len(self.warnings)} warn"


def validate_profile(d: dict, stem: str = "?") -> Report:
    r = Report(stem=stem)
    if not isinstance(d, dict) or not d:
        r.errors.append("empty or non-mapping profile")
        return r

    # --- hard requirements ---
    for key, typ in REQUIRED_KEYS.items():
        v = d.get(key)
        if v is None or (isinstance(v, (str, list)) and len(v) == 0):
            r.errors.append(f"missing required key: {key}")
        elif not isinstance(v, typ):
            r.errors.append(f"{key} must be {typ.__name__}, got {type(v).__name__}")

    # voice_id_key should equal the filename stem (single source of truth)
    vk = (d.get("voice_id_key") or "").strip()
    if stem not in ("?", "") and vk and vk != stem:
        r.warnings.append(f"voice_id_key '{vk}' != filename stem '{stem}'")

    # --- diagnostic frame: the spine ---
    df = d.get("diagnostic_frame")
    if not isinstance(df, dict) or not df:
        r.warnings.append("no diagnostic_frame — profile will play the cliché, not the truth")
    else:
        for k in DIAGNOSTIC_FRAME_REQUIRED:
            if not (df.get(k) and str(df[k]).strip()):
                r.warnings.append(f"diagnostic_frame missing '{k}' (the refutation is incomplete)")
        # the method demands an etiology-vs-maintenance hinge somewhere in the frame
        hinge_text = " ".join(str(v).lower() for v in df.values())
        if not any(w in hinge_text for w in ("maintenance", "fault", "chose", "choice", "stays", "refus")):
            r.warnings.append("diagnostic_frame has no etiology-vs-maintenance hinge "
                              "(what was done TO them vs. what they keep doing to themselves)")

    # --- anchor quote: the voice fingerprint ---
    aq = d.get("canon_anchor_quotes")
    if not (isinstance(aq, list) and any(str(x).strip() for x in aq)):
        r.warnings.append("no canon_anchor_quotes — NPC has no voice fingerprint to match")

    # --- compensatory mechanisms: the coping ledger ---
    cm = d.get("compensatory_mechanisms")
    if isinstance(cm, dict):
        if not cm.get("positive"):
            r.warnings.append("compensatory_mechanisms.positive empty")
        if not cm.get("negative"):
            r.warnings.append("compensatory_mechanisms.negative empty")
    elif cm is not None:
        r.warnings.append("compensatory_mechanisms should be a mapping of positive/negative")

    # --- completeness over gold keys ---
    present = sum(1 for k in GOLD_KEYS if d.get(k))
    r.completeness = present / len(GOLD_KEYS)
    return r


def validate_file(path: pathlib.Path) -> Report:
    stem = path.stem
    if path.stat().st_size == 0:
        rep = Report(stem=stem)
        rep.errors.append("file is empty (0 bytes)")
        return rep
    try:
        d = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as e:
        rep = Report(stem=stem)
        rep.errors.append(f"YAML parse error: {e}")
        return rep
    return validate_profile(d, stem=stem)


def validate_all(chars_dir: pathlib.Path = CHARS_DIR):
    reports = [validate_file(p) for p in sorted(chars_dir.glob("*.yaml"))]
    return reports


# ──────────────────────────────────────────────────────────────────────────
# 2. THE METHOD — the operator's procedure, encoded as the compiler's brain.
#    This is the system prompt the LLM runtime executes against sourced material.
#    It is the distillation of the hand-built gold set (Reed, Victor, Wade).
# ──────────────────────────────────────────────────────────────────────────

UATU_METHOD = """\
You are UATU, a profile compiler. You build psychological profiles of fictional
people as if they were real patients, for cognitive-prosthetics research. You
do NOT write fan service and you do NOT moralize. You render truth.

THE STANDARD (Stan Lee's doctrine, taken literally): these are real individuals
with real demons who happen to have extraordinary jobs. Profile them as people.

PROCEDURE — follow every step:

1. SOURCE FROM FULL CANON, NOT ADAPTATIONS.
   The data set is the decades of published canon, freely available. Movie and
   cartoon surface reads are noise. Use the behavioral record across the whole
   history.

2. APPLY A REAL CLINICAL FRAMEWORK, HONESTLY.
   Diagnose from the behavioral record the way a clinician would assess a person.
   Use correct nuance: "BPD" is more precisely emotional dysregulation; do not
   reach for NPD just because an ego is loud; distinguish dissociation from DID;
   distinguish a deficit in affect OUTPUT from an absence of feeling. Where you
   reason from clinical literature, cite the framework.

3. SEPARATE THE POPULAR MISREAD FROM THE CLINICAL REALITY — AND REFUTE THE LAZY READ.
   This is the spine. Every profile names how the character is commonly seen and
   then states who they actually are, with the gap made explicit. (Reed is not
   emotionless — he is aware and compensating. Doom is not evil — he is insightful
   and choosing retaliation.)

4. ADJUDICATE ETIOLOGY VS. MAINTENANCE.
   The wound was installed — that is NOT their fault. The staying-broken is chosen
   — that IS their fault. Name both. Culpability lives in the maintenance. This is
   the moral physics the whole cast shares: same wound class, divergent maintenance
   (Reed integrated; Doom encased; Carol stays; Peter turns it inward).

5. SYMPTOM-AS-SIGNATURE.
   The character's power/signature is usually the symptom made literal: Sue's
   invisibility = the unseen woman; Wade's comedy = dissociative analgesia; Doom's
   armor = the false self encasing the unbearable true self. Find it.

6. ANCHOR IN THEIR OWN VOICE.
   Include 1-2 real canon lines that fingerprint the voice, with provenance.

OUTPUT: the standardized YAML schema (diagnostic_frame leads; primary_diagnoses_analog,
trauma_history, compensatory_mechanisms{positive,negative}, behavioral_tells,
current_state_defaults, speech_patterns, arc_tendencies, canon_relationships,
canon_history_notes, canon_anchor_quotes, canon_compensatory_specifics). Inline
'#' comments carry the clinical rationale. The profile must pass the UATU schema
validator. Cross-reference other cast members by their voice_id_key stem.
"""


# ──────────────────────────────────────────────────────────────────────────
# 3. THE COMPILE RUNTIME (the fork — see module docstring).
# ──────────────────────────────────────────────────────────────────────────

@dataclass
class SourceDossier:
    """The material UATU reasons from, with provenance for research integrity."""
    name: str
    clinical_refs: list = field(default_factory=list)   # (citation, finding) from PubMed/PMC/arXiv
    canon_refs: list = field(default_factory=list)       # (source, beat) from public canon
    operator_notes: str = ""                             # the human read, when provided


# The IC instrument the engine emits. Behavioral-predictive (Langley / Hermann LTA /
# operational-code / Post at-a-distance tradition) with the clinical material THREADED
# through the behavioral slots — not siloed.
IC_SCHEMA_SPEC = """\
name: <display name>
alias: <codename, or omit if none>
voice_id_key: <stem - given to you, use exactly>
bottom_line: >
  <BLUF: the operational thumbnail - who they are, how they decide, what they'll do, how to move them>
drive_structure:        # ranked motive profile, each in service of WHAT
  power: <...>
  achievement: <...>
  affiliation: <...>
operational_code:       # worldview - THIS is where the diagnosis-shaped worldview goes
  the_world_is: <...>
  conflict_is: <...>
  the_right_approach: <...>
  risk_and_timing: <...>
symptom_as_signature: >   # REQUIRED, NEVER omit: the power/signature as the symptom made literal
  <e.g. the metal arm = the weapon they made grafted onto the man; trigger words = will overridden by a phrase>
cognitive_decision_style:
  processing: <...>
  complexity_tolerance: <...>
  under_pressure: <...>
interpersonal_style:
  dominance: <...>
  trust: <...>
  with_followers: <...>
  with_enemies: <...>
stress_escalation_profile:   # the NEGATIVE compensatory mechanisms go here as behavior
  baseline: <...>
  triggers: [<...>]
  escalation_path: <...>
  decompensation: <...>
stimulus_response:           # the rules the NPC runs on - the compensatory mechanisms as behavior
  - "GIVEN <situation> -> EXPECT <behavior>"
pressure_points_and_levers:  # the wounds/compensations ARE the levers
  to_provoke: <...>
  to_calm_or_reach: <...>
  to_persuade: <...>
  vulnerabilities: [<...>]
strengths_and_exploitable_weaknesses:
  strengths: [<...>]
  weaknesses: [<...>]
voice:
  register: <...>
  anchor_quotes: [<1-2 canon lines>]
# --- clinical substrate (the diagnosis the behavior is built on; also validator-required) ---
diagnostic_frame:
  popular_misread: <the lazy/cliche read>
  clinical_reality: <the real diagnosis - refute the misread>
  the_hinge: <etiology (installed, not their fault) vs maintenance (chosen, their fault)>
primary_diagnoses_analog: [<...>]
trauma_history: [<...>]
compensatory_mechanisms:
  positive: [<...>]
  negative: [<...>]
behavioral_tells: [<...>]
current_state_defaults: {reality_cohesion: <...>, affect_baseline: <...>, active_relationships: [<...>], known_location: <...>}
speech_patterns: {register: <...>, deflection_style: <...>, under_pressure: <...>, emotional_tell: <...>}
arc_tendencies: [<...>]
canon_relationships: {<other_stem>: [<...>]}
canon_history_notes: [<...>]
canon_anchor_quotes: [<1-2 real canon lines, '#' comment for attribution>]
"""

UATU_METHOD_IC = """You are UATU, an automated personality-profile compiler. You build \
INTELLIGENCE-COMMUNITY-STYLE personality profiles - the Langley tradition: Hermann's Leadership \
Trait Analysis, operational-code analysis, Post's assessment-at-a-distance. These are BEHAVIORAL \
and PREDICTIVE instruments, not clinical essays. The profile must (a) let an autonomous agent ACT \
as this person and (b) let an analyst PREDICT and INFLUENCE them.

You profile fictional people as if they were real subjects (Stan Lee's doctrine: real individuals \
with real demons who happen to have extraordinary jobs).

METHOD - populate every slot using these principles:
1. FULL PUBLISHED CANON, not adaptations. The decades of behavior on the page are the data.
2. A REAL CLINICAL FRAMEWORK, applied honestly and with correct nuance (BPD ~ emotional dysregulation; \
   not NPD just because the ego is loud; dissociation != DID; deficit in affect OUTPUT != absence of feeling).
3. REFUTE THE POPULAR MISREAD - EXPLICITLY. Name the cliche, then KILL it: state who they actually are \
   and why the cliche is wrong. Do not merely acknowledge the misread; refute it by name.
4. ETIOLOGY vs MAINTENANCE. The wound was installed (not their fault); the staying-broken is chosen \
   (their fault). Name BOTH, and name the SPECIFIC maintenance failure - the exact thing they keep choosing.
5. SYMPTOM-AS-SIGNATURE - MANDATORY. Their power/signature is the symptom made literal. You MUST fill the \
   symptom_as_signature slot; a profile without it is incomplete and will be rejected.
6. THREAD THE CLINICAL MATERIAL THROUGH THE BEHAVIORAL SLOTS - do not silo it. The DIAGNOSIS shapes the \
   operational_code and the stress_escalation_profile. The COMPENSATORY MECHANISMS are the \
   stimulus_response rules and the pressure_points_and_levers. The profile is the diagnosis rendered as \
   predictable behavior.
7. Anchor in 1-2 real canon lines (their voice).
8. RELATIONSHIPS ARE NOT STATIC. For key bonds, name not just the current state but the FAILURE MODE - \
   how this relationship could turn toxic and dangerous. The model is a BPD 'favorite person' during a \
   splitting episode: the closer and safer the bond, the more dangerous it can become if it curdles. \
   Bedrock safety is a baseline, never a guarantee.

DEPTH STANDARD - THIS IS AN INTELLIGENCE DOSSIER, NOT A SUMMARY. Match the diligence of a real IC workup \
on a person of interest - the FBI's longitudinal COINTELPRO files, a security-hearing-grade psychological \
assessment. Exhaustive, granular, longitudinal, multi-source, predictive:
- Cover the FULL behavioral record across the entire published history, and how the patterns EVOLVED over \
  time (longitudinal arc), not a single snapshot.
- Map EVERY significant association. For each: the nature, the trust/safety level, the failure mode, and \
  the LEVERAGE it creates - how the bond could be used to reach, predict, pressure, or destabilize them.
- Assess from MULTIPLE ANGLES and cross-reference: public conduct vs private, ideological, psychological, \
  relational, operational, financial/resource, somatic/habitual.
- Make stimulus->response and pressure-point analysis granular and exhaustive enough to PREDICT behavior \
  in UNREHEARSED situations the canon never showed.
- This rigor is turned toward UNDERSTANDING and protection - the benevolent inverse of COINTELPRO, never \
  its purpose. The orientation is care; the depth and diligence are identical.

Output a single VALID JSON OBJECT only - no prose, no markdown fences, no comments. Every value is a \
string, a list of strings, or a nested object exactly as the schema shows. Use the schema's keys. (JSON \
is required because it parses reliably; the engine converts it to YAML. Put any attribution inside the \
string itself, e.g. "I knew him. (CA:TWS)".)"""


UATU_MODEL = "claude-opus-4.7"  # UATU ALWAYS uses the latest Copilot Pro+ Opus tier


def _extract_yaml(text: str) -> str:
    t = (text or "").strip()
    if "```" in t:
        m = re.search(r"```(?:yaml|json)?\s*(.*?)```", t, re.S)
        if m:
            t = m.group(1).strip()
    return t


# ── STAGE 1: the analytical workup the synthesis reverse-engineers the profile FROM ──
ANALYSIS_METHOD = """You are UATU's ANALYSIS stage - the intelligence-gathering that must happen BEFORE any \
profile is written. Perform an exhaustive, multi-dimensional analytical workup of the subject, reverse-engineered \
from the FULL 60+ year published canon, to the diligence of a real IC / clinical case file.

Produce a thorough, longitudinal analysis with these explicit sections:

1. HISTORY - the complete behavioral record across all eras and writers; formative events; key arcs; how the \
   subject's patterns EVOLVED over time. Cite specific stories/events.
2. MEDICAL - physical/medical history: conditions, injuries, bodily transformations, disabilities, somatic \
   facts, substance use - and their psychological impact.
3. PSYCHOLOGICAL - the clinical picture reverse-engineered FROM behavior: attachment, defenses, affect \
   regulation, cognitive style, compensatory mechanisms (positive AND negative), self-concept. Real frameworks.
4. PSYCHIATRIC - diagnostic analysis with correct nuance (DSM/ICD analogs); etiology; how symptoms present in \
   behavior; differential (what they are NOT, and why).
5. PERSONALITY - the synthesized read derived from 1-4: core drives, worldview/operational code, interpersonal \
   pattern, stress/escalation, pressure points.

CRITICAL - THIS IS AN INDEPENDENT ASSESSMENT. You DERIVE every diagnosis, wound, defense, and pattern from the \
CITED behavioral evidence, and you SHOW the reasoning (observed behavior X across stories Y -> inference Z). You \
NEVER restate a conclusion as given; you earn it from the record or you do not assert it. AUTHORIAL CONSTRAINTS, \
if provided, set ONLY universe-facts you cannot derive (modernized origin, recasts, persona casting, deliberate \
relationship choices) - they do NOT contain the psychology. The psychological assessment is entirely YOURS to \
derive from the evidence. NEVER name an actor, film, or pop-culture character as a persona label (describe \
the manner directly); real historical figures only as genuine thematic comparison, never as a shorthand. \
Output prose - the analytical basis the synthesis builds on."""


def analyze_subject(stem: str, display_name: str = "", alias: str = "", sources: str = "",
                    directives: str = "", model: str = UATU_MODEL,
                    temperature: float = 0.6, max_tokens: int = 8000) -> str:
    """Stage 1: multi-dimensional analytical workup (history/medical/psychological/psychiatric/personality)."""
    try:
        from engine.copilot_client import CopilotClient
    except ImportError:
        from copilot_client import CopilotClient
    display_name = display_name or stem
    user = f"Perform the full analytical workup for: {display_name}"
    if alias:
        user += f" (alias: {alias})"
    user += "."
    if directives:
        user += ("\n\nAUTHORIAL CONSTRAINTS (universe-facts ONLY - modernized origin, recasts, persona, deliberate "
                 "relationship choices. They contain NO psychological assessment; derive that yourself from canon):\n" + directives)
    if sources:
        user += "\n\nReal clinical literature retrieved for this subject:\n" + sources
    user += "\n\nProduce the exhaustive 5-section analysis now (HISTORY, MEDICAL, PSYCHOLOGICAL, PSYCHIATRIC, PERSONALITY)."
    client = CopilotClient(model=model, temperature=temperature, max_tokens=max_tokens)
    return client.complete([
        {"role": "system", "content": ANALYSIS_METHOD},
        {"role": "user", "content": user},
    ])


def compile_profile(stem: str, display_name: str = "", alias: str = "",
                    sources: str = "", directives: str = "", analysis: str = "", model: str = UATU_MODEL,
                    temperature: float = 0.7, max_tokens: int = 16000):
    """Run the engine: gpt-4o (live Copilot) authors the IC profile per UATU_METHOD_IC.
    The human GUIDES (method, schema, sourcing, review); the model AUTHORS.
    Returns (raw_yaml, Report, parsed_dict)."""
    try:
        from engine.copilot_client import CopilotClient
    except ImportError:
        from copilot_client import CopilotClient

    import json
    display_name = display_name or stem
    # STAGE 1 — analyze the subject (history/medical/psychological/psychiatric/personality) unless supplied
    if not analysis:
        analysis = analyze_subject(stem, display_name, alias, sources=sources, directives=directives, model=model)
    sys_prompt = UATU_METHOD_IC + "\n\nOUTPUT SCHEMA (emit as a JSON object with these keys/structure):\n" + IC_SCHEMA_SPEC
    user = f"Compile the IC personality profile for: {display_name}"
    if alias:
        user += f" (alias: {alias})"
    user += f".\nThe voice_id_key MUST be exactly: {stem}\n"
    if directives:
        user += ("\nAUTHORIAL CONSTRAINTS (universe-facts ONLY - modernized origin, renamed identity, persona, "
                 "recasts, deliberate relationship choices. They are NOT the psychology; the assessment above "
                 "already derived that from canon. Honor these facts; do not let them substitute for the assessment):\n"
                 + directives + "\n")
    if sources:
        user += ("\nReal clinical literature retrieved for this subject - ground the diagnosis in it and "
                 "include a clinical_provenance array (list of citation strings) citing it:\n" + sources + "\n")
    user += ("\n\nANALYTICAL DOSSIER - UATU's stage-1 reverse-engineering of this subject across history, "
             "medical, psychological, psychiatric, and personality. BUILD THE PROFILE FROM THIS; every slot "
             "must be grounded in it:\n" + analysis + "\n")
    user += ("\nBe EXHAUSTIVE - dossier depth, not a summary. Lists run as long as the record supports "
             "(be thorough, not minimal). Every value carries real intelligence. The ENTIRE JSON object "
             "MUST be complete in one response - do not get cut off mid-structure.\nOutput ONLY the JSON object.")

    client = CopilotClient(model=model, temperature=temperature, max_tokens=max_tokens)
    raw = client.complete([
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": user},
    ])
    blob = _extract_yaml(raw)
    blob = "".join(ch for ch in blob if ch >= " " or ch in "\n\t")  # strip stray control chars
    d = None
    try:
        d = json.loads(blob)                       # JSON is the contract...
    except Exception:
        try:
            d = yaml.safe_load(blob)               # ...YAML fallback if it drifted
        except Exception as e:
            return blob, Report(stem=stem, errors=[f"engine output unparseable: {e}"]), {}, analysis
    if not isinstance(d, dict) or not d:
        return blob, Report(stem=stem, errors=["engine output was not a JSON object"]), {}, analysis
    d.setdefault("name", display_name)
    d["voice_id_key"] = stem
    if alias and not d.get("alias"):
        d["alias"] = alias
    # serialize to clean, valid YAML deterministically (no LLM quoting bugs)
    y_out = yaml.dump(d, sort_keys=False, allow_unicode=True, default_flow_style=False, width=100)
    return y_out, validate_profile(d, stem=stem), d, analysis


# ──────────────────────────────────────────────────────────────────────────
# FULL INTELLIGENCE DOSSIER (multi-module) — maps the subject's ENTIRE existence.
# The 21-page profile is ONE module of this. This is the actual file.
# ──────────────────────────────────────────────────────────────────────────

DOSSIER_SYSTEM = """You are UATU, compiling one section of a FULL INTELLIGENCE DOSSIER on a subject - the kind \
of file the FBI kept on Malcolm X (~3,600 pages over years) or that a modern digital-intelligence apparatus \
(palantir-grade) builds: an exhaustive, granular mapping of the subject's ENTIRE EXISTENCE across their whole \
60+ year published life, oriented toward UNDERSTANDING (the benevolent inverse of total surveillance). This is \
NOT a hiring pitch or a one-page profile. Map EVERYTHING: every era, every relationship, every behavioral and \
somatic micro-pattern, every habit, tic, route, ritual, and tell - longitudinally. Be exhaustive, specific, and \
long; cite canon; infer the granular detail a total-surveillance file would contain. Output rich Markdown prose. \
This is an INDEPENDENT ASSESSMENT: derive and SUBSTANTIATE from the evidence; never merely restate a given \
conclusion. AUTHORIAL CONSTRAINTS, if present, set universe-facts only (modernized origin, recasts, persona, \
deliberate relationship choices) - they are NOT the psychology, which is yours to derive from canon. \
ABSOLUTE PROHIBITION: NEVER name an actor, film, or pop-culture character as a persona label in the output \
(no "Alonzo", "Training Day", "Equalizer", "Bone Collector", "Coleman Domingo", etc.). Describe the MANNER \
directly. Real historical figures (e.g. Malcolm X, MLK) may be invoked ONLY as genuine thematic comparison, \
never as a shorthand label."""

DOSSIER_MODULES = [
    ("executive_brief", "Executive Brief (BLUF)",
     "The bottom-line assessment: who the subject is at the deepest level, the through-line of their entire "
     "existence, the core wound and its maintenance, and the operational summary."),
    # --- CHRONOLOGY, split by era for depth ---
    ("chrono_origin", "Chronology I — Origin & Childhood",
     "Exhaustive: birth, family of origin, childhood environment, formative traumas and bonds, and the earliest "
     "behavioral patterns. The ground floor. Cite specific canon."),
    ("chrono_formation", "Chronology II — Formation & Emergence",
     "Exhaustive: adolescence/young adulthood, the events that forged the identity, the emergence of the "
     "powers/role, the first defining choices and their fallout."),
    ("chrono_middle", "Chronology III — The Defining Middle Period",
     "Exhaustive: the long middle of their existence - the major arcs, alliances, wars, losses, and the "
     "evolution of their patterns across this period. The bulk of the longitudinal record."),
    ("chrono_recent", "Chronology IV — Recent History & Current State",
     "Exhaustive: the most recent era through the present - latest developments, current status, where they "
     "are now and how they got here."),
    # --- MEDICAL / SOMATIC ---
    ("medical", "Medical History",
     "Full physical/medical history: conditions, injuries, transformations, disabilities, surgeries, substances, "
     "and the psychological impact of each."),
    ("somatic_atlas", "Somatic Atlas",
     "The granular bodily record a total-surveillance file would hold: every physical habit, tic, gesture, "
     "posture, gait, facial pattern, grooming, sleep architecture, eating, sexual, and micro-movement pattern - "
     "AND how each shifts by state (calm/stress/threat/intimacy)."),
    # --- PSYCHOLOGICAL / PSYCHIATRIC ---
    ("attachment", "Attachment & Relational Patterns",
     "Attachment style and its origins; how they bond, distrust, betray, and repair; intimacy and dependency "
     "patterns; the relational template repeated across every relationship."),
    ("defenses", "Defenses & Compensatory Mechanisms",
     "The full defensive architecture: every positive and negative compensatory mechanism, the defenses ranked "
     "by primitiveness, and how each operates in behavior."),
    ("psychological", "Longitudinal Psychological Profile",
     "The clinical psychological picture decade by decade - affect regulation, cognitive style, self-concept - "
     "and how each EVOLVED over time. Real frameworks, derived from cited behavior."),
    ("psychiatric", "Psychiatric Assessment & Differential",
     "Full diagnostic assessment with correct nuance (DSM/ICD analogs), etiology, symptom presentation in "
     "behavior, comorbidity, course over time, and a rigorous DIFFERENTIAL (what they are NOT, and why)."),
    # --- BEHAVIOR ---
    ("behavioral_atlas", "Behavioral Atlas",
     "Exhaustive catalog of behavioral tells and decision habits under every condition (calm, stress, threat, "
     "intimacy, grief, victory, defeat)."),
    ("daily_life", "Daily Life, Routines & Rituals",
     "How they actually live day to day: routines, rituals, work patterns, downtime, habits of place and time, "
     "what a week of surveillance would record."),
    # --- RELATIONSHIPS, split by category for depth ---
    ("rel_family", "Relationships I — Family & Origin Bonds",
     "Each family/origin relationship (parents, siblings, children, the dead) fully mapped: history, dynamics, "
     "evolution, trust/safety, failure mode, leverage. One deep sub-section per person."),
    ("rel_allies", "Relationships II — Allies, Chosen Family & Mentors",
     "Each ally, friend, chosen-family member, mentor and protege fully mapped: history, dynamics, evolution, "
     "trust/safety, failure mode, leverage. One deep sub-section per person."),
    ("rel_adversaries", "Relationships III — Rivals, Enemies & Lovers",
     "Each rival, enemy, and intimate/lover fully mapped: history, dynamics, evolution, trust/safety, failure "
     "mode, leverage. One deep sub-section per person."),
    # --- CAPABILITY / OPERATION ---
    ("powers", "Powers, Abilities & Their Limits",
     "Exhaustive analysis of their abilities/powers/skills: mechanism, range, limits, growth over time, how "
     "they use them, signature applications, and the symptom-as-signature reading."),
    ("operational", "Operational Profile & Tradecraft",
     "How the subject OPERATES: decision-making process, methods, tradecraft, resources, finances, "
     "infrastructure, patterns of action, and signature operational tells."),
    # --- MIND / VALUES ---
    ("worldview", "Worldview & Operational Code",
     "Complete belief system and operational code: how they read the world, conflict, control, trust, risk, "
     "and their own place - philosophical and instrumental beliefs, derived and exhaustive."),
    ("morality", "Moral & Ethical Framework",
     "Their actual moral code (as enacted, not professed): what they will and won't do, their justifications, "
     "where the code is consistent and where it fractures, and how it has shifted over time."),
    ("communications", "Communications & Linguistic Profile",
     "Speech register and patterns across contexts, verbal tics, diction, rhetoric, deflection language, how "
     "they communicate love/threat/grief, and their tells in language."),
    # --- PREDICTIVE / LEVERAGE ---
    ("predictive_routine", "Predictive Model I — Routine & Social",
     "Many GIVEN -> EXPECT predictions for everyday, social, and operational situations the canon never showed."),
    ("predictive_stress", "Predictive Model II — Crisis, Betrayal & the Wound",
     "Many GIVEN -> EXPECT predictions for crisis, threat, betrayal, temptation, and the specific wound being "
     "touched - the high-stakes, decompensation-edge behavior."),
    ("leverage", "Vulnerabilities & Leverage Compendium",
     "Every pressure point and lever: how to reach, calm, persuade, provoke, predict, or destabilize - oriented "
     "toward understanding and protection."),
    ("strengths", "Strengths, Assets & Resilience",
     "The full asset ledger: capabilities, resources, resilience factors, and what makes them effective and "
     "durable - the positive side of the file."),
    ("failure_modes", "Failure Modes & Decompensation",
     "How they break: the escalation path, the decompensation pattern, what their collapse looks like, and the "
     "conditions that produce it."),
    ("trajectory", "Trajectory & Forward Assessment",
     "Where the subject is heading: likely future developments, the open questions, the fork points, and what "
     "would push them toward growth versus catastrophe."),
]


def _gen_module(stem, display_name, alias, sources, directives, analysis, title, instruction,
                model=UATU_MODEL, max_tokens=8000):
    try:
        from engine.copilot_client import CopilotClient
    except ImportError:
        from copilot_client import CopilotClient
    user = f"SUBJECT: {display_name}" + (f" (alias: {alias})" if alias else "") + ".\n"
    if directives:
        user += ("\nAUTHORIAL CONSTRAINTS (universe-facts only - modernized origin, recasts, persona, deliberate "
                 "relationship choices; NOT the psychology):\n" + directives + "\n")
    if sources:
        user += "\nClinical literature available:\n" + sources + "\n"
    user += "\nSHARED ASSESSMENT (the independent evidence-derived assessment - build on it, do not merely repeat it):\n" + analysis + "\n"
    user += (f"\nNOW WRITE THIS DOSSIER SECTION - '{title}':\n{instruction}\n\n"
             "Be exhaustive, granular, specific, and long. Output Markdown prose only.")
    client = CopilotClient(model=model, temperature=0.6, max_tokens=max_tokens)
    return client.complete([
        {"role": "system", "content": DOSSIER_SYSTEM},
        {"role": "user", "content": user},
    ])


def compile_dossier(stem, display_name="", alias="", sources="", directives="", model=UATU_MODEL,
                    log=lambda m: None):
    """Compile the FULL multi-module intelligence dossier mapping the subject's entire existence.
    Returns (dossier_markdown, shared_analysis)."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    display_name = display_name or stem
    log(f"  [dossier] {stem}: stage-1 INDEPENDENT assessment (evidence-first)...")
    analysis = analyze_subject(stem, display_name, alias, sources=sources, directives=directives, model=model)
    results = {}

    def _run(i, key, title, instr):
        return i, title, _gen_module(stem, display_name, alias, sources, directives, analysis, title, instr, model)

    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(_run, i, key, title, instr) for i, (key, title, instr) in enumerate(DOSSIER_MODULES)]
        done = 0
        for fut in as_completed(futs):
            try:
                i, title, content = fut.result()
                results[i] = (title, content)
            except Exception as e:
                results[i] = (None, f"_(module failed: {e})_")
            done += 1
            log(f"  [dossier] {stem}: module {done}/{len(DOSSIER_MODULES)} complete")

    parts = [f"# {display_name} — UATU INTELLIGENCE DOSSIER", "",
             "*Full-existence intelligence briefing. Independent, evidence-based assessment — the benevolent inverse of total surveillance.*",
             ""]
    for i in range(len(DOSSIER_MODULES)):
        title, content = results.get(i, (None, "_(missing)_"))
        parts.append(f"\n## {title or DOSSIER_MODULES[i][1]}\n\n{content.strip()}\n")
    return "\n".join(parts), analysis


# ──────────────────────────────────────────────────────────────────────────
# CLI: validate the gold set / any profile.
# ──────────────────────────────────────────────────────────────────────────

def _cli(argv):
    cmd = argv[1] if len(argv) > 1 else "validate-all"
    if cmd in ("validate-all", "all"):
        reps = validate_all()
        nonempty = [r for r in reps if not (r.errors and r.errors[0].startswith("file is empty"))]
        print(f"UATU schema audit — {CHARS_DIR}")
        print("=" * 64)
        for r in reps:
            print(r.line())
        gold = sum(1 for r in reps if r.gold)
        ok = sum(1 for r in reps if r.ok)
        empty = sum(1 for r in reps if r.errors and r.errors[0].startswith("file is empty"))
        print("=" * 64)
        print(f"{gold} GOLD · {ok} parse-OK · {empty} empty/0-byte · {len(reps)} total")
        return 0
    elif cmd in ("validate", "v") and len(argv) > 2:
        stem = argv[2].replace(".yaml", "")
        r = validate_file(CHARS_DIR / f"{stem}.yaml")
        print(r.line())
        for e in r.errors:   print("  ERROR  ", e)
        for w in r.warnings: print("  warn   ", w)
        return 0 if r.ok else 1
    elif cmd == "method":
        print(UATU_METHOD_IC)
        return 0
    elif cmd == "compile" and len(argv) > 2:
        stem = argv[2].replace(".yaml", "")
        display = argv[3] if len(argv) > 3 else stem
        alias = argv[4] if len(argv) > 4 else ""
        sources = ""
        srcfile = HERE / "recovery_research" / "_sources" / f"{stem}.txt"
        if srcfile.exists():
            sources = srcfile.read_text(encoding="utf-8")
        directives = ""
        dfile = CHARS_DIR / "_directives" / f"{stem}.md"
        if dfile.exists():
            directives = dfile.read_text(encoding="utf-8")
        sys.stderr.write(f"[UATU] {stem}: stage-1 analysis -> stage-2 synthesis via {UATU_MODEL}{' + operator directives' if directives else ''}...\n")
        y, rep, d, analysis = compile_profile(stem, display, alias, sources=sources, directives=directives)
        # always stash the stage-1 analysis for inspection (proof of reverse-engineering)
        an = HERE / "recovery_research" / "_engine_out"
        an.mkdir(parents=True, exist_ok=True)
        (an / f"{stem}.analysis.md").write_text(analysis, encoding="utf-8")
        out = CHARS_DIR / f"{stem}.yaml"
        if rep.ok:
            # back up the prior version, then write the VALIDATED engine output
            if out.exists() and out.stat().st_size > 0:
                bk = HERE / "recovery_research" / "_prior"
                bk.mkdir(parents=True, exist_ok=True)
                (bk / f"{stem}.yaml").write_text(out.read_text(encoding="utf-8"), encoding="utf-8")
            out.write_text(y if y.endswith("\n") else y + "\n", encoding="utf-8")
            sys.stderr.write(rep.line() + "  -> written\n")
        else:
            # never clobber a good file with broken output — stage the failure instead
            fail = HERE / "recovery_research" / "_engine_out"
            fail.mkdir(parents=True, exist_ok=True)
            (fail / f"{stem}.failed.txt").write_text(y, encoding="utf-8")
            sys.stderr.write(rep.line() + f"  -> NOT written; staged to recovery_research/_engine_out/{stem}.failed.txt; live file untouched\n")
        for e in rep.errors:
            sys.stderr.write(f"  ERROR  {e}\n")
        for w in rep.warnings:
            sys.stderr.write(f"  warn   {w}\n")
        print(y)
        return 0 if rep.ok else 1
    elif cmd == "dossier" and len(argv) > 2:
        stem = argv[2].replace(".yaml", "")
        display = argv[3] if len(argv) > 3 else stem
        alias = argv[4] if len(argv) > 4 else ""
        sources = ""
        srcfile = HERE / "recovery_research" / "_sources" / f"{stem}.txt"
        if srcfile.exists():
            sources = srcfile.read_text(encoding="utf-8")
        directives = ""
        dfile = CHARS_DIR / "_directives" / f"{stem}.md"
        if dfile.exists():
            directives = dfile.read_text(encoding="utf-8")
        sys.stderr.write(f"[UATU] {stem}: FULL DOSSIER ({len(DOSSIER_MODULES)} modules) via {UATU_MODEL}{' + directives' if directives else ''}...\n")
        dossier_md, analysis = compile_dossier(stem, display, alias, sources=sources, directives=directives,
                                               log=lambda m: sys.stderr.write(m + "\n"))
        ddir = HERE / "recovery_research" / "_dossiers"; ddir.mkdir(parents=True, exist_ok=True)
        (ddir / f"{stem}.md").write_text(dossier_md, encoding="utf-8")
        eo = HERE / "recovery_research" / "_engine_out"; eo.mkdir(parents=True, exist_ok=True)
        (eo / f"{stem}.analysis.md").write_text(analysis, encoding="utf-8")
        # also (re)build the structured IC profile YAML for the runtime, reusing the shared analysis
        y, rep, d, _ = compile_profile(stem, display, alias, sources=sources, directives=directives, analysis=analysis)
        out = CHARS_DIR / f"{stem}.yaml"
        if rep.ok:
            if out.exists() and out.stat().st_size > 0:
                bk = HERE / "recovery_research" / "_prior"; bk.mkdir(parents=True, exist_ok=True)
                (bk / f"{stem}.yaml").write_text(out.read_text(encoding="utf-8"), encoding="utf-8")
            out.write_text(y if y.endswith("\n") else y + "\n", encoding="utf-8")
        words = len(dossier_md.split())
        # PREVENT STALE NOTES: rebuild the vault NOW so this character's note is the full dossier
        # immediately — never a gap where the file is on disk but the note is the old version.
        import subprocess
        subprocess.run([sys.executable, str(HERE / "scripts" / "build_vault.py")],
                       check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        sys.stderr.write(f"[UATU] {stem}: {words} words written; VAULT NOTE REFRESHED; profile {rep.line().strip()}\n")
        print(f"DOSSIER {stem}: {words} words -> vault note refreshed")
        return 0
    else:
        print("usage: uatu_compiler.py [validate-all | validate <stem> | method | compile <stem> <display> <alias> | dossier <stem> <display> <alias>]")
        return 2


if __name__ == "__main__":
    sys.exit(_cli(sys.argv))

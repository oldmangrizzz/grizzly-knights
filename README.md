# Grizzly Knights — the UATU Framework

**Intelligence-grade personality profiling + heterogeneous-reasoner multi-agent simulation.**

This is not "AI Town with new characters." Prior LLM agent simulations fix two variables that are
actually the interesting ones: the *reasoner* (every agent runs the same model) and the *depth of the
self* (each persona is a one-line description). This project varies **both** — a fleet of **distinct
models, one per agent** (27 across 38 agents), each enacting an **independently-assessed, clinically-
grounded, intelligence-grade psychological profile**. The personality is the research instrument, not
decoration. The cute animated medium is a delivery vehicle; the research is **persona fidelity across
heterogeneous reasoners** and **whether clinically-predicted psychodynamics emerge unscripted.**

> Full thesis, related-work positioning, methodology, and the falsifiable research agenda are in
> **[`docs/UATU_framework_paper.md`](docs/UATU_framework_paper.md)** — start there.

---

## What's here (map for readers and for NotebookLM)

| Path | What it is |
|---|---|
| **[`docs/UATU_framework_paper.md`](docs/UATU_framework_paper.md)** | The research paper — read this first for the whole picture |
| **`engine/`** | UATU compiler: two-stage assessment-at-a-distance → structured IC profile + deep dossier. Authored on the top Opus tier (excluded from the agent fleet). |
| **`universe/characters/*.yaml`** | The 38 GOLD personality profiles (structured intelligence dossiers). *Note: YAML — read the Vault notes or dossiers for human-readable versions.* |
| **`recovery_research/_sources/*.txt`** | Clinical grounding per character — real, PubMed-cited literature with DOIs. |
| **`recovery_research/_dossiers/*.md`** | The deep dossiers (~80,000–98,000 words each) — the long-form readable profiles. |
| **`GrizzlyKnights_Vault/`** | Obsidian read interface: one readable note per character (with portrait), a **World Gallery**, and the relationship graph. |
| **`world_art/`** | Generated imagery — 38 character portraits + 14 environment/scene plates (tokenless FLUX pipeline). |
| **`fanfic_town/`** | The simulation: a fork of AI Town (TypeScript / Convex). Per-agent model routing lives in `convex/agent/conversation.ts` (`modelFor`) and `convex/util/llm.ts`; the cast is generated into `data/characters.ts` from the profiles. |
| **`episodes/`** | Generated audio episodes (narrated character interactions). |

## Methodology in one paragraph

Profiles are produced by **assessment, not transcription**: the engine independently reverse-engineers
a subject's psychology from canonical evidence (operator input is treated only as *authorial
constraint*, never as the analysis). The method adapts established political-psychology practice —
Hermann's Leadership Trait Analysis, operational-code analysis, and Post's assessment-at-a-distance —
to fictional subjects, using a fictional character's full published canon as the "speeches and
writings" corpus. Every profile separates **etiology** (the installed wound — not the subject's fault)
from **maintenance** (staying broken — their responsibility), maps the defining capability as a
**symptom made literal**, and encodes relationships *with their failure modes* (e.g. the favorite-person
attachment pattern and its splitting dynamics) so interpersonal behavior is predictable.

## Ethics

All subjects are fictional. Clinical frameworks are applied to invented characters for behavioral depth
and research; **nothing here diagnoses or profiles any real person.** Sensitive modernizations are
handled with restraint — atrocity implied, never depicted — and no real individual's likeness appears in
generated media. See the paper's Ethics section for the full treatment.

## Status

Framework, profiling engine, full 38-character roster, imagery, and simulation substrate are **built**.
The experimental program (the control arms and blinded rating protocols in the paper's §7) is
**specified and falsifiable but not yet run** — this is a framework/methodology stage, and no empirical
results are claimed.

---

*Built with the UATU engine. Profiles, dossiers, and imagery are machine-generated under the methodology
above; the framework paper documents the design and the honest accounting of what is built vs. hypothesized.*

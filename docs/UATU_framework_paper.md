# Heterogeneous Reasoners, Clinically-Grounded Personas: A Framework and Testbed for Persona Fidelity and Emergent Psychodynamics in Multi-Agent Simulation

**Working title — subject to operator revision.**
*Draft v0.1 — system, methodology, and research-agenda paper. No empirical results are claimed; this document presents the architecture, the profiling methodology, and a falsifiable research program. Sections marked **[OBSERVATION]** are preliminary and qualitative; sections marked **[HYPOTHESIS]** are not yet tested.*

---

## Abstract

Multi-agent simulations built on large language models (LLMs) have, to date, shared two simplifying assumptions: (1) all agents are driven by a *single, homogeneous* model, and (2) each agent's "personality" is a *shallow* persona — a few sentences of role description. We argue that both assumptions discard the most scientifically interesting variables. We present a framework in which (1) every agent is driven by a *different* LLM — a heterogeneous fleet of distinct reasoners, one per agent — and (2) every agent is specified by an *intelligence-grade, clinically-grounded psychological profile* produced by an independent assessment engine rather than hand-written flavor text. The personality is not decoration; it is the research instrument. Under these conditions, two questions become measurable that prior testbeds could not pose: *how faithfully, and how distinctly, do different model architectures enact the same deep psychological structure?* and *do interpersonal dynamics predicted by clinical theory — splitting, the "favorite person" attachment pattern, trauma-driven escalation — actually emerge in observable interaction?* We describe (i) UATU, a two-stage "assessment-at-a-distance" engine that reverse-engineers behavioral-predictive profiles from canonical evidence, grounded in established political-psychology methodology and peer-reviewed clinical literature; (ii) a heterogeneous-reasoner simulation substrate forked from an open generative-agent town; and (iii) a monitoring methodology and a set of falsifiable hypotheses. We position this work against generative-agent simulations, persona-simulation toolkits, and communicative-agent frameworks, and we argue it constitutes a distinct research program: the *systematic, observational study of personality fidelity and emergent psychodynamics across heterogeneous LLM reasoners.*

---

## 1. Introduction

The release of *Generative Agents* (Park et al., 2023) demonstrated that LLM-driven agents equipped with memory, reflection, and planning could produce believable individual and emergent collective behavior in a sandbox world. The open-source *AI Town* starter kit (a16z-infra) made that architecture deployable. A wave of communicative-agent frameworks followed — ChatDev (Qian et al., 2024), CAMEL (Li et al., 2023), AgentVerse (Chen et al., 2024) — and persona-simulation toolkits such as Microsoft's TinyTroupe (Salem et al., 2025) brought the same idea to synthetic focus groups and product research.

Across this literature, two design choices are nearly universal and almost never examined:

1. **Model homogeneity.** Every agent in a given simulation runs on the *same* base model. Differences between agents are produced entirely by prompt content. The model is treated as a neutral substrate.
2. **Persona shallowness.** An agent's identity is typically a short natural-language description — a name, an occupation, a few traits, a goal. Personality is a costume, not a structure.

These choices are reasonable for the questions those works asked (Can agents plan? Can they cooperate on a task? Do crowds emerge?). But they foreclose a different and, we argue, more demanding line of inquiry. If we want to know whether an LLM can *be* a person — not merely role-play a label, but enact a coherent, predictable, internally-consistent psychology under social pressure over time — then a one-line persona on a single model is the wrong instrument. We need depth on the persona axis and variance on the model axis.

This paper describes a framework built on the opposite assumptions:

- **Heterogeneous reasoners.** In our deployment, *N* agents are driven by *N* distinct LLMs (currently 27 distinct models across 38 agents; see §5). The model becomes an independent variable. The same deep persona, instantiated on different architectures, lets us compare enactment directly.
- **Deep, clinically-grounded personas.** Each agent is specified by a structured profile of roughly two dozen behavioral and clinical fields (§3.2), produced by an engine that independently *assesses* the subject from canonical evidence rather than transcribing a summary. The profiles are written in the idiom of intelligence personality assessment — behavioral, predictive, lever-oriented — and are explicitly grounded in peer-reviewed clinical literature.

The substrate is, admittedly, a "cute" one: a tile-based animated town of recognizable characters. We are candid that the aesthetic is a delivery vehicle. But the medium does not bound the science. The same way a flight simulator is a game *and* a training instrument, this is a sandbox *and* a controlled observatory for a real question: **persona fidelity and emergent psychodynamics across heterogeneous LLM reasoners.**

### 1.1 Contributions

1. **UATU**, a two-stage assessment-at-a-distance engine that derives intelligence-grade, behaviorally-predictive psychological profiles from canonical evidence, grounded in established political-psychology methods (Leadership Trait Analysis; operational-code analysis; Post's assessment-at-a-distance) and peer-reviewed clinical literature, with an explicit *etiology-versus-maintenance* distinction and a *symptom-as-signature* mapping.
2. **A heterogeneous-reasoner simulation architecture** in which each agent is routed to a distinct LLM, making model identity a controlled variable rather than a fixed constant.
3. **A monitoring methodology and a falsifiable research agenda** for studying (a) persona fidelity across models, (b) persona drift differentials, and (c) the emergence of clinically-predicted interpersonal dynamics.
4. **An honest accounting** of what is built versus hypothesized, and an ethics treatment of applying clinical frameworks to fictional subjects.

---

## 2. Related Work and Positioning

**Generative agents.** Park et al. (2023; UIST; arXiv:2304.03442) introduced the memory-stream / reflection / planning architecture and the 25-agent Smallville sandbox. Our substrate is a descendant of this line via the open AI Town kit. We retain the persistent-world, observable-interaction premise but diverge on the two axes above: their agents are homogeneous-model and shallow-persona by design, because their contribution was the cognitive architecture, not the personalities.

**Communicative-agent frameworks.** CAMEL (Li et al., 2023; NeurIPS; arXiv:2303.17760) uses role-playing "inception prompting" for two-agent cooperation. ChatDev (Qian et al., 2024; ACL; arXiv:2307.07924) assigns software-lifecycle roles coordinated by a chat chain. AgentVerse (Chen et al., 2024; ICLR; arXiv:2308.10848) dynamically recruits agent teams and studies emergent group behavior. These works are *task-oriented*: the agents exist to solve a problem (write code, complete a benchmark). Our agents have no task. They exist to *be*, and the object of study is the fidelity and dynamics of that being. Roles in these frameworks are functional ("tester," "reviewer"); our personas are psychological and pathological.

**Persona-simulation toolkits.** TinyTroupe (Salem et al., 2025; Microsoft; arXiv:2507.09788) simulates specified personas for business insight (synthetic interviews, focus groups). It shares our interest in personhood but differs in three ways: personas are specified by the user rather than derived by an independent assessment engine; the depth target is market-research plausibility rather than clinical-behavioral prediction; and, as with the others, simulations are single-model.

**Persona fidelity and drift.** A nascent evaluation literature is directly relevant to our hypotheses. Li et al. (2024; arXiv:2402.10962) show that LLM chatbots drift from an assigned persona within roughly eight turns, attributing it to attention decay over the prompt, and propose measurement and mitigation. RoleLLM (Wang et al., 2024; Findings of ACL; arXiv:2310.00746) benchmarks role-playing via speaking-style imitation and role-specific knowledge. These works measure fidelity on a *fixed* model; we make the model a variable and ask how fidelity and drift *differ across architectures* for an identical, far deeper persona.

**Assessment-at-a-distance methodology.** Our profiling method is not improvised; it adapts a mature social-science tradition. Margaret Hermann's Leadership Trait Analysis (Hermann, 1980; *International Studies Quarterly* 24(1):7–46) content-analyzes a subject's own words across personality traits to predict orientation and behavior. The operational-code program — Leites (1951), formalized by George (1969; *ISQ* 13(2):190–222), and quantified by Walker, Schafer, and Young (1998; *ISQ* 42(1):175–189) via the Verbs-In-Context System — models a subject's philosophical and instrumental beliefs about the political world. Post's edited volume *The Psychological Assessment of Political Leaders* (Post, 2003; University of Michigan Press) consolidates assessment-at-a-distance into profiling practice. We treat a fictional character's full published canon as the "speeches and writings" corpus and apply the same analytic stance — behavioral, predictive, evidence-first — rather than producing a clinical essay.

**Summary of the gap.** No prior system, to our knowledge, combines (a) heterogeneous per-agent models, (b) independently-assessed clinical-grade personas, and (c) a persistent observational substrate, in order to study persona fidelity and psychodynamic emergence as the *primary* research object.

---

## 3. The UATU Profiling Engine

### 3.1 Design principle: assessment, not transcription

The central methodological commitment is that the engine must *independently assess* the subject from evidence, not regurgitate a conclusion supplied to it. Operator-supplied material about a character is treated strictly as **authorial constraint** (universe facts: what is canon, what has been modernized) and is explicitly *not* permitted to stand in for the psychological analysis. The engine derives the psychology itself, evidence-first, in a dedicated stage that runs before synthesis. This is enforced in the engine prompts and validated by withholding the intended psychological reads from the model and checking, on cold runs, whether it reconstructs them from canon alone. (In internal checks, cold assessments independently recovered intended core findings — e.g., a "savior-wound" structure and its compensations — without being told them.)

### 3.2 Two-stage architecture

**Stage 1 — Independent assessment.** Given the canonical evidence corpus and (separately) any authorial constraints, the engine produces an evidence-first analytical reconstruction of the subject: the installed wound and its etiology, the maintenance behaviors that keep it active, the defensive structure, and the through-line that explains the subject's choices across their history.

**Stage 2 — Synthesis.** The shared assessment is compiled into a structured profile in the idiom of an intelligence personality file. The schema comprises roughly two dozen fields, including: `bottom_line`, `drive_structure`, `operational_code`, `symptom_as_signature`, `cognitive_decision_style`, `interpersonal_style`, `stress_escalation_profile`, `stimulus_response` (given→expect contingencies), `pressure_points_and_levers`, `strengths_and_exploitable_weaknesses`, and a clinical substrate (`diagnostic_frame`, `primary_diagnoses_analog`, `trauma_history`, `compensatory_mechanisms`, `behavioral_tells`), plus voice, speech patterns, relationship graph, and a `clinical_provenance` block of citations.

A parallel long-form path compiles a deep dossier (dozens of modules, ~80,000–98,000 words per subject in the current roster) for human reading; the structured profile is what feeds the runtime.

### 3.3 Methodological commitments

- **Real frameworks, correctly nuanced.** Diagnoses are analogized to the actual clinical literature with correct distinctions (e.g., complex-PTSD identity alteration is distinguished from borderline structure, rather than conflated), and citations are drawn from peer-reviewed sources with identifiers. The engine has, in practice, rejected a retracted source when one was offered.
- **Etiology versus maintenance.** Each profile separates the *installed* wound (not the subject's fault — how they were made) from the *maintenance* behaviors (their responsibility — how they stay broken). This is the analytic spine of every profile.
- **Symptom-as-signature.** Where a subject has a defining capability, the engine maps it as the symptom made literal — the pathology and the signature expressed through the same channel — rather than as unrelated flavor.
- **Relationships carry failure modes.** The relationship graph encodes not just bonds but their characteristic ways of breaking (e.g., the favorite-person attachment pattern and its splitting dynamics), which is what makes interpersonal prediction possible.

### 3.4 The engine's own model

The assessment engine is deliberately run on a single, top-tier reasoning model (the latest available Opus tier), held constant across all subjects, so that variation in profile quality is not confounded by the authoring model. Critically, **this engine model is excluded from the agent fleet** (§5): the model that *writes* the personalities never *performs* one. This separation keeps authorship and enactment independent.

---

## 4. Simulation Substrate

The runtime is a fork of the open AI Town generative-agent town (TypeScript on the Convex reactive backend, with a tile-based animated world). We retain the persistent world, the spatial movement, and the conversation engine, and we replace the character layer wholesale. Each agent's identity prompt is assembled from its structured profile — the behavioral and clinical fields of §3.2 are rendered into the agent's working self-description — so that the personality driving the agent in-world is the assessed profile, not a hand-written blurb.

Agent-to-agent relationships from the profiles are surfaced into the cast as a relationship graph (currently 93 edges across 38 agents), so that the clinically-encoded bonds and failure modes are present as priors in who-knows-whom and how.

---

## 5. Heterogeneous Reasoner Assignment

The defining architectural feature is per-agent model heterogeneity. A fleet of distinct LLMs is assigned across the cast by round-robin, so that between any two uses of a given model every other model appears — maximizing diversity and avoiding clustering. In the current deployment, **38 agents are driven by 27 distinct models**: a set of standard-tier hosted models and a broad set of open cloud models, none repeated more than necessary by the round-robin. At runtime, each agent's display name resolves through a `characterModels` map to its assigned model, and a routing layer dispatches to the appropriate backend (a local proxy for hosted models; an open-model host otherwise).

Two constraints are deliberate:

1. **The engine's authoring model is excluded from the fleet.** The most capable model writes the personalities and never enacts one, so that fidelity is tested on *other* architectures and authorship cannot flatter enactment.
2. **No premium-cost tier is used for agents.** The fleet is composed of standard- and open-tier models, both to control cost and because the research question — can heterogeneous, non-frontier reasoners faithfully enact a deep persona? — is more interesting and more general than "can the single best model role-play?"

This design turns the simulation into a natural cross-model comparison: the *same* profile schema, the *same* world, the *same* social pressures, with the reasoner as the variable.

---

## 6. Monitoring Methodology

The simulation is observed, not merely run. We distinguish three observation targets:

1. **Persona fidelity.** Does an agent's in-world behavior remain consistent with its profile — its drive structure, operational code, stress-escalation signature, and characteristic tells — over extended interaction? This is where the persona-drift literature (Li et al., 2024) becomes a per-model measurement rather than a single-model finding.
2. **Predictive validity.** The profiles make explicit `stimulus_response` contingencies (given X, expect Y). Monitoring checks whether the agent actually responds as its file predicts when the world supplies X.
3. **Emergent psychodynamics.** The profiles encode relational failure modes. Monitoring watches for their emergence in unscripted interaction — e.g., splitting and favorite-person dynamics, trauma-driven escalation, avoidant withdrawal — that no single line of dialogue was written to produce.

Current monitoring is observational and instrumented at the infrastructure level (per-agent model routing is logged; interactions are persisted by the substrate). Quantitative scoring instruments are part of the research agenda (§7), not yet claimed as results.

---

## 7. Research Agenda and Hypotheses

We state hypotheses as falsifiable and label them as untested.

- **[HYPOTHESIS H1 — Fidelity varies by architecture.** Given an identical deep profile, persona fidelity (consistency with the profile's behavioral predictions) will differ measurably across models, and the ordering will be stable across subjects — i.e., some architectures are systematically better "actors" of a fixed psychology than others, independent of which psychology.]
- **[HYPOTHESIS H2 — Drift is architecture-specific.** The rate and character of persona drift (Li et al., 2024) will differ across models for the same profile; depth of profile specification will interact with drift (richer `stimulus_response` scaffolding will slow drift).]
- **[HYPOTHESIS H3 — Clinically-predicted dynamics emerge.** Relational failure modes encoded in the profiles (splitting, favorite-person attachment, trauma escalation) will appear in unscripted interaction at rates above a shallow-persona control, and will be recognizable to a blinded clinical rater.]
- **[HYPOTHESIS H4 — Symptom-as-signature transfers.** Where a profile maps a capability as a symptom made literal, agents will enact the *psychological* symptom even when the literal capability is absent from the sandbox — i.e., the structure, not just the surface, drives behavior.]

**Planned instruments.** A blinded rating protocol in which clinical and lay raters score in-world transcripts against held-out profile predictions; a shallow-persona control arm (same characters, one-line personas, same model fleet) to isolate the contribution of profile depth; and a single-model control arm (deep personas, one model) to isolate the contribution of heterogeneity.

---

## 8. Ethics

**Fictional subjects.** All subjects are fictional characters. Clinical frameworks are applied to them as a research convenience and for behavioral depth; **nothing here diagnoses, profiles, or pathologizes any real person.** The assessment-at-a-distance lineage we adapt was developed for real political figures; we deliberately apply it only to invented ones.

**Clinical responsibility.** Diagnostic analogues are framed as *analogues*, grounded in literature with citations, and held to the etiology-versus-maintenance distinction precisely to avoid the cartoon "villain = crazy" failure mode. The aim is the opposite: to render damage as installed and human, not as a label.

**Sensitive modernization.** Where source material is updated to engage real histories of harm, the treatment is restrained and dignified, atrocity is implied rather than depicted, and likeness of real individuals is avoided in all generated media. These are standing production constraints, not afterthoughts.

**Dual-use.** Profiles include `pressure_points_and_levers`. On fictional subjects this is narrative and predictive instrumentation. We note the obvious dual-use shape of assessment-at-a-distance generally and restrict the method's application to fiction here by design.

---

## 9. Limitations

- **No empirical results yet.** This is a framework and methodology paper. The hypotheses of §7 are not tested; §6 observations are qualitative and preliminary.
- **Construct validity, not ground truth.** Profile quality is grounded in established method and literature, but a fictional subject has no ground-truth psychology to validate against; validation is necessarily about internal coherence, canon-consistency, and inter-rater recognizability, not correspondence to a real mind.
- **Author-model influence.** Although the authoring model is excluded from the fleet, profiles authored by one model family may carry idiom that advantages enactors from related families; the control arms in §7 are designed to detect this.
- **Single-observer monitoring.** Present observation is single-observer and unblinded; the planned blinded protocols are required before any fidelity claim is made.
- **Substrate constraints.** The sandbox's affordances (movement, conversation) bound which behaviors can be expressed; symptom-as-signature transfer (H4) is partly a test of, and partly limited by, this.

---

## 10. Conclusion

Prior multi-agent LLM simulations held two variables fixed that, we argue, are the interesting ones: the reasoner and the depth of the self it is asked to be. By varying both — a heterogeneous fleet of distinct models, each enacting an independently-assessed, clinically-grounded, intelligence-grade profile — we convert a "cute" generative-agent town into a controlled observatory for a serious question: *can different machine reasoners faithfully and distinctly be the same deep person, and do the dynamics that theory predicts of that person actually emerge when no one scripts them?* The framework, the profiling engine, and the monitoring substrate are built; the experimental program is specified and falsifiable. The medium is a sandbox. The research is not.

---

## References

1. Chen, W., et al. (2024). *AgentVerse: Facilitating Multi-Agent Collaboration and Exploring Emergent Behaviors.* ICLR 2024. arXiv:2308.10848.
2. George, A. L. (1969). The "Operational Code": A Neglected Approach to the Study of Political Leaders and Decision-Making. *International Studies Quarterly*, 13(2), 190–222.
3. Hermann, M. G. (1980). Explaining Foreign Policy Behavior Using the Personal Characteristics of Political Leaders. *International Studies Quarterly*, 24(1), 7–46.
4. Leites, N. (1951). *The Operational Code of the Politburo.* McGraw-Hill (RAND Corporation).
5. Li, G., Hammoud, H. A. A. K., Itani, H., Khizbullin, D., & Ghanem, B. (2023). *CAMEL: Communicative Agents for "Mind" Exploration of Large Language Model Society.* NeurIPS 2023. arXiv:2303.17760.
6. Li, K., Liu, T., Bashkansky, N., Bau, D., Viégas, F., Pfister, H., & Wattenberg, M. (2024). *Measuring and Controlling Persona/Instruction Drift in Language Model Dialogs.* arXiv:2402.10962 (related version, COLM 2024).
7. Park, J. S., O'Brien, J. C., Cai, C. J., Morris, M. R., Liang, P., & Bernstein, M. S. (2023). *Generative Agents: Interactive Simulacra of Human Behavior.* UIST 2023. arXiv:2304.03442. DOI:10.1145/3586183.3606763.
8. Post, J. M. (ed.) (2003). *The Psychological Assessment of Political Leaders: With Profiles of Saddam Hussein and Bill Clinton.* University of Michigan Press.
9. Qian, C., Liu, W., Liu, H., et al. (2024). *ChatDev: Communicative Agents for Software Development.* ACL 2024. arXiv:2307.07924.
10. Salem, P., Sim, R., Olsen, C., Saxena, P., Barcelos, R., & Ding, Y. (2025). *TinyTroupe: An LLM-powered Multiagent Persona Simulation Toolkit.* Microsoft. arXiv:2507.09788.
11. Walker, S. G., Schafer, M., & Young, M. D. (1998). Systematic Procedures for Operational Code Analysis: Measuring and Modeling Jimmy Carter's Operational Code. *International Studies Quarterly*, 42(1), 175–189.
12. Wang, Z. M., Peng, Z., et al. (2024). *RoleLLM: Benchmarking, Eliciting, and Enhancing Role-Playing Abilities of Large Language Models.* Findings of ACL 2024. arXiv:2310.00746.
13. a16z-infra. *AI Town* [software]. GitHub repository, github.com/a16z-infra/ai-town. Deployable generative-agent town on Convex, inspired by Park et al. (2023).

# CLAUDE.md — Grizzly Knights — STANDING OPERATOR DIRECTIVES

Read this EVERY session before acting. These are non-negotiable. The operator does not
repeat himself; if you're unsure, the answer is here, not in another question to him.

## HOW TO WORK WITH THIS OPERATOR (read first)
- MOVE AT HIS PACE. Execute; do not narrate option menus for decisions already made.
- DO NOT re-litigate settled decisions. DO NOT ask permission for work already ordered.
- DO NOT make him repeat instructions. Check these notes first.
- He CANNOT open or read `.yaml` files (neither can ElevenReader). NEVER deliver a profile
  as "see the yaml." Deliver readable: paste in chat, or in the Obsidian vault.
- Profiles are IC / Langley-style PERSONALITY PROFILES — behavioral and predictive
  (drives, operational code, decision style, stress/escalation, stimulus→response, levers),
  with the diagnosis + compensatory mechanisms THREADED through the slots. NOT clinical essays.

## THE ENGINE BUILDS EVERYTHING
- The UATU engine AUTHORS profiles. Claude only GUIDES: method, schema, sourcing, directives,
  review. DO NOT hand-author a profile.
- Operator specs for a character are INPUTS to the engine, dropped in
  `universe/characters/_directives/<stem>.md` (authoritative build instructions) and/or
  `recovery_research/_sources/<stem>.txt` (clinical literature). Feed the spec → run the engine.
- Run: `python3 engine/uatu_compiler.py compile <stem> "<Display>" "<Alias>"`
- UATU ALWAYS uses the latest Copilot Pro+ OPUS tier (currently `claude-opus-4.7`).
- NPC runtime models: EVERY Copilot 1x-tier model + EVERY Ollama Cloud model, diversified
  (never repeat a model across people without spreading the others). OPUS IS NEVER AN NPC
  MODEL — it is reserved for the UATU engine only.

## BY-HAND / PENDING
- MAGNETO — spec already given, goes through the ENGINE (not hand-authored):
  modernize off the 1940s Holocaust (sliding timescale) onto JIM CROW SOUTH racial-terror /
  the lynching era; surname Lehnsherr → LYNCHER (deliberate); persona = Denzel's Alonzo
  (Training Day) + Malcolm X + the Equalizer + the Bone Collector = a charismatic force of nature.
- CHARLES XAVIER — the ONLY character awaiting operator direction. Do NOT finalize him and do
  NOT raise any other character as "pending." Wait for instruction on Charles.

## READ INTERFACE
- Obsidian vault (`GrizzlyKnights_Vault/`) is the operator's personality database / wiki / graph
  for reading and critiquing engine output. Regenerate it whenever profiles change.

## HARD NOs
- No hand-authored profiles. No yaml as the readable deliverable. No re-asking settled decisions.
- No queuing/asking permission for ordered work. No making him repeat himself.

# Grizzly Knights — Roster Rebuild Status (autonomous session)

Built while you were resting. Nothing here is final — all of it is yours to red-pen.

## The number that defines "fully working": 25 / 38 GOLD

Run the live dashboard anytime:
```
cd /Users/rbhanson/fanfic && source .venv/bin/activate
python3 engine/uatu_compiler.py validate-all
```

## What got built this session

**Together with you (calibration set):** reed_richards, victor_doom, carol_danvers

**Autonomous (safe / framed by you — I draft, you red-pen):**
sue_storm, ben_grimm, johnny_storm, jessica_jones, clint_barton, kate_bishop,
steve_rogers, thor_odinson, sam_wilson, kamala_khan, scott_lang, luke_cage,
danny_rand, hank_mccoy, ororo_munroe, charles_xavier, natasha_romanoff,
remy_lebeau, kurt_wagner, uatu_the_watcher

**Augmented from your hand-built survivors (your verbatim lines preserved, gold schema added):**
peter_parker, tony_stark

## HELD FOR YOU — do NOT trust these built without your frame (12)

These are the contested / load-bearing reads you flagged. They are still 0-byte on purpose:

bruce_banner · bucky_barnes · erik_lehnsherr · felicia_hardy · frank_castle ·
jean_grey · logan · mary_jane_watson · matt_murdock · rogue · scott_summers · wanda_maximoff

felicia_hardy + mary_jane_watson also block the Cheesecake Factory smoke/regression test.

## REVIEW FLAGS

- **charles_xavier** — built as the contested morally-grey founder (savior complex, mind-wipes,
  child-soldiers), NOT the saint. Most likely in this batch to need your correction.
- **peter_parker / tony_stark** — augmented, not rewritten. Confirm I didn't drift from your read.

## Engine work (Layers 0 + 1)

- **Layer 0 (wiring):** `fanfic_town/scripts/generate_characters.py` rewired — `diagnostic_frame`,
  `canon_anchor_quotes`, and `compensatory_mechanisms` now reach the NPC identity prompt (they were
  inert before). IDENTITY_CAP raised 3500 -> 7000.
- **Layer 1 (UATU):** `engine/uatu_compiler.py` — the schema contract, the validator (the GOLD gate),
  your method encoded as `UATU_METHOD`, and the provenance pipeline. Carol + Jessica carry real
  PubMed citations (`clinical_provenance` blocks) as the agent-runtime proof of concept.
- **Loader hardening:** 4 unguarded profile loaders (showrunner, uatu, script_generator,
  agency_engine) no longer crash cryptically on empty YAMLs — they fail loud with "rebuild required"
  or echo the key. This is what turned the post-wipe NoneType crashes into actionable messages.

## Suites (the live rebuild progress bar)

- regression: 6/11 · apt: 12/13
- Every remaining failure is a HELD empty character, not a code bug. They go green as the 12 are built.
  - Cheesecake tests need felicia + mary_jane.
  - regression_08 needs all 38 (it's a wipe-detector).
  - apt_01 iterates the roster and hits the empties.
- **Smoke test NOT run** — it needs the (held) Cheesecake five and burns live-model tokens; running it
  now would spend money on a guaranteed data-failure. It's the acceptance test once Felicia + MJ exist.

## Open decisions waiting on you

1. The 12 held characters — build together (you set the frame, esp. Victor-class: Logan, Jean, Wanda, Erik, Frank, Bucky, Matt, Bruce, Rogue, Felicia, MJ, Scott Summers).
2. UATU compile runtime — agent (live PubMed/arXiv sourcing, with citations) vs standalone. My rec: agent. I'm a working v0 of it (see Carol/Jessica provenance).
3. Imagery / sprites — you parked this for later.
4. The heterogeneous `characterModels` fleet (Ollama Cloud + Copilot routing) is emitted into
   characters.ts but the convex-side LLM routing (`convex/util/llm.ts`) isn't verified — needs your env.

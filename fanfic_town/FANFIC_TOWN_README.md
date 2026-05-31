# fanfic_town

Fanfic Knights running inside a forked AI Town simulation. Spectator mode.
You watch. They live.

## What this is

- AI Town (a16z) forked into this repo.
- Characters auto-generated from `../universe/characters/*.yaml` — same YAML
  files that drive the existing pipeline. Single source of truth.
- 38 canonical characters wired in (cycled across the 11 sprites that ship
  with AI Town).
- No director. No Uatu. No pressure engine. Agents wake up in a shared
  world, walk around, run into each other, talk. You watch in the browser.

## One-time setup (uses things you already have)

```
cd fanfic_town
npm install
npx convex dev          # uses your existing Convex Pro account
```

Convex will prompt once to log in / pick a project. Free; uses your Pro tier.

Pick your LLM provider — uses your existing key. Pick ONE:

```
# OpenAI (cheapest mainstream):
npx convex env set OPENAI_API_KEY sk-...

# OR Together.ai:
npx convex env set TOGETHER_API_KEY ...

# OR local Ollama (no API cost at all):
npx convex env set OLLAMA_HOST http://host.docker.internal:11434
```

Then in a second terminal:

```
npm run dev
```

Open http://localhost:5173 . The sim runs. You watch.

## Re-generating characters from YAML

Anytime you edit a `.yaml` in `/Users/rbhanson/fanfic/universe/characters/`:

```
python3 scripts/generate_characters.py
```

That rewrites `data/characters.ts` from scratch. The dev server picks it up.

## What's NOT here yet

- Per-character sprites. Right now everyone uses one of the 11 stock sprites
  cycled by sort order. Wade is `f4`, Peter is `f2`, Felicia is `p1`, etc.
  Upgrade path: drop a custom 32×32 walk-cycle PNG (4 directions × 3 frames)
  into `data/spritesheets/` and reference it. Same JSON shape as `f1.ts`.
- Custom map. Currently uses AI Town's default `gentle.js`. Upgrade path:
  build in Tiled (free), export JSON, run `data/convertMap.js`.

Neither blocks the sim from running today.

## Files

- `data/characters.ts`       — AUTO-GENERATED. Don't hand-edit.
- `scripts/generate_characters.py` — YAML → characters.ts
- `convex/`                  — server-side game + agent logic (AI Town's)
- `src/`                     — browser UI (AI Town's)

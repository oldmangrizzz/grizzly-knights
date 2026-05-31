#!/usr/bin/env bash
# Grizzly Knights — finish ALL world imagery in one shot.
# Picks up HF_TOKEN (or ~/.cache/huggingface/token) automatically for Pro ZeroGPU quota.
# Safe to re-run: both generators skip images that already exist.
set -uo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate 2>/dev/null || true

# surface token state so it's obvious whether we're on Pro quota or anonymous
if [ -z "${HF_TOKEN:-}" ] && [ -f "$HOME/.cache/huggingface/token" ]; then
  export HF_TOKEN="$(tr -d '[:space:]' < "$HOME/.cache/huggingface/token")"
fi
if [ -n "${HF_TOKEN:-}" ]; then echo ">>> HF token detected — Pro quota"; else echo ">>> NO token — anonymous (will stall after ~2 images)"; fi

echo ">>> [1/3] character portraits"
python3 world_art/generate_portraits.py

echo ">>> [2/3] environments & scenes"
python3 world_art/generate_scenes.py

echo ">>> [3/3] rebuild vault gallery"
python3 scripts/build_vault.py

echo ">>> portraits: $(ls -1 world_art/portraits/*.png 2>/dev/null | wc -l | tr -d ' ')/38 | scenes: $(ls -1 world_art/scenes/*.png 2>/dev/null | wc -l | tr -d ' ')/14"

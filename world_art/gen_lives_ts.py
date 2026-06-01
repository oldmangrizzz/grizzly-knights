#!/usr/bin/env python3
"""Emit fanfic_town/data/lives.ts from agent_lives.json so the Convex sim can import it.
Keyed by "Name (Alias)" — which appears verbatim in each agent's identity ("You are ...").
"""
import json
ROOT = "/Users/rbhanson/fanfic"
lives = json.load(open(f"{ROOT}/universe/world/agent_lives.json"))
ts = ("// AUTO-GENERATED from universe/world/agent_lives.json — do not edit by hand.\n"
      "// Each key appears verbatim in the matching agent's identity ('You are <key>.').\n"
      "export type Life = {\n"
      "  home: { x: number; y: number };\n"
      "  district?: string;\n"
      "  haunts: { x: number; y: number; name: string }[];\n"
      "  activities: { description: string; emoji: string; duration: number }[];\n"
      "};\n\n"
      "export const Lives: Record<string, Life> = " + json.dumps(lives, ensure_ascii=False, indent=2) + ";\n")
open(f"{ROOT}/fanfic_town/data/lives.ts", "w", encoding="utf-8").write(ts)
print(f"wrote fanfic_town/data/lives.ts ({len(lives)} lives)")

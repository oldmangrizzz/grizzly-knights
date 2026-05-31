import json
import re

LOG_FILE = "/Users/rbhanson/.gemini/tmp/fanfic/chats/session-2026-05-29T14-41-882d89b6.jsonl"

def extract_full_ts():
    with open(LOG_FILE, "r") as f:
        # We want the most recent large characters.ts output before the wipe
        # The wipe happened around 18:10Z (message ID a0b13121)
        candidates = []
        for line in f:
            if '// AUTO-GENERATED from ../universe/characters/' in line:
                try:
                    data = json.loads(line)
                    if data.get("type") == "user":
                        for content in data.get("content", []):
                            if "functionResponse" in content:
                                output = content["functionResponse"].get("response", {}).get("output", "")
                                if isinstance(output, str) and "export const Descriptions =" in output:
                                    if len(output) > 5000: # It's a large one
                                        candidates.append(output)
                except:
                    continue
        
        if candidates:
            # Get the last one
            best = candidates[-1]
            with open("recovery_research/full_recovered_characters.ts", "w") as out:
                out.write(best)
            print(f"Extracted full characters.ts ({len(best)} bytes)")
        else:
            print("No large characters.ts found in logs.")

if __name__ == "__main__":
    extract_full_ts()

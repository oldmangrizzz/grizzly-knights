import json
import os
import re

LOG_FILE = "/Users/rbhanson/.gemini/tmp/fanfic/chats/session-2026-05-29T14-41-882d89b6.jsonl"
RECOVERY_DIR = "recovery_research"
os.makedirs(RECOVERY_DIR, exist_ok=True)

def recover():
    print(f"Scanning {LOG_FILE} for research data...")
    with open(LOG_FILE, "r") as f:
        for line in f:
            try:
                data = json.loads(line)
                # Look for tool responses (functionResponse)
                if data.get("type") == "user":
                    for content in data.get("content", []):
                        if "functionResponse" in content:
                            resp = content["functionResponse"]
                            if resp.get("name") in ["read_file", "grep_search", "run_shell_command"]:
                                output = resp.get("response", {}).get("output", "")
                                if isinstance(output, str):
                                    # Look for character patterns
                                    if "primary_diagnoses_analog" in output or "core_identity" in output:
                                        # It's likely a character YAML or the generated characters.ts
                                        # Save it
                                        timestamp = data.get("timestamp", "unknown").replace(":", "-")
                                        filename = f"recovery_{timestamp}.txt"
                                        with open(os.path.join(RECOVERY_DIR, filename), "a") as out:
                                            out.write(output)
                                            out.write("\n" + "="*50 + "\n")
            except:
                continue
    print(f"Recovery attempt complete. Check {RECOVERY_DIR}/")

if __name__ == "__main__":
    recover()

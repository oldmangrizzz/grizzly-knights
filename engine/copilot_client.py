import subprocess
import requests
from typing import Optional


class CopilotClient:
    """
    GitHub Copilot Pro+ chat completions API.
    Endpoint: https://api.githubcopilot.com/chat/completions
    Auth: gh auth token (Bearer)
    No daily quota — uses Copilot Pro+ subscription.
    """

    API_URL = "https://api.githubcopilot.com/chat/completions"

    def __init__(self, model: str = "gpt-4o", temperature: float = 0.85, max_tokens: int = 3000):
        self.model       = model
        self.temperature = temperature
        self.max_tokens  = max_tokens

    def _get_github_token(self) -> str:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()

    def complete(self, messages: list[dict], **kwargs) -> str:
        """Send a chat completion request. Returns the assistant message string."""
        token = self._get_github_token()

        payload = {
            "model":       kwargs.get("model",       self.model),
            "messages":    messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens":  kwargs.get("max_tokens",  self.max_tokens),
        }

        for attempt in range(5):
            try:
                resp = requests.post(
                    self.API_URL,
                    headers={
                        "Authorization":          f"Bearer {token}",
                        "Content-Type":           "application/json",
                        "Copilot-Integration-Id": "vscode-chat",
                    },
                    json=payload,
                    timeout=600,
                )
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                # deep Opus dossier calls can run long; retry on timeout/connection drop instead of dying
                if attempt < 4:
                    import time
                    time.sleep(5)
                    continue
                raise RuntimeError(f"Copilot API network error after retries: {e}") from e

            except requests.HTTPError as e:
                if resp.status_code == 429 and attempt < 4:
                    import time, re
                    wait = 30
                    msg = resp.json().get("error", {}).get("message", "")
                    if m := re.search(r"wait (\d+) second", msg):
                        wait = min(int(m.group(1)) + 2, 90)
                    print(f"\n[Rate limited — waiting {wait}s before retry {attempt+1}/4...]")
                    time.sleep(wait)
                    continue
                if attempt < 4:
                    continue
                raise RuntimeError(f"Copilot API error [{resp.status_code}]: {resp.text}") from e

        raise RuntimeError("Copilot API failed after 5 attempts")


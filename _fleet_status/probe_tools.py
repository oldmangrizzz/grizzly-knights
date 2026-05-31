"""
Minimal repro: does the Copilot endpoint honor OpenAI function-calling?

One BaseTool, one Agent, one prompt that REQUIRES the tool. Print raw response.
"""
from __future__ import annotations
import asyncio, subprocess, json, sys, traceback
from pydantic import Field
from agency_swarm import Agent, Agency
from agency_swarm.tools import BaseTool
from agents import OpenAIChatCompletionsModel, AsyncOpenAI


class RecordSecret(BaseTool):
    """Record a secret word the user gave you. You MUST call this tool exactly once
    with the secret word. Do NOT reply with text until you have called the tool."""
    secret_word: str = Field(..., description="the secret word the user told you to record")

    def run(self) -> str:
        return f"OK recorded: {self.secret_word}"


def build_model(model_name="gpt-4o"):
    token = subprocess.run(
        ["gh", "auth", "token"], capture_output=True, text=True, check=True
    ).stdout.strip()
    client = AsyncOpenAI(
        base_url="https://api.githubcopilot.com",
        api_key=token,
        default_headers={
            "Copilot-Integration-Id": "vscode-chat",
            "Editor-Version":         "vscode/1.95.0",
        },
    )
    return OpenAIChatCompletionsModel(model=model_name, openai_client=client)


async def main():
    model = build_model("gpt-4o")
    agent = Agent(
        name="SecretKeeper",
        description="records secret words via tool",
        instructions=(
            "You are an assistant. When the user gives you a secret word, you MUST "
            "call the RecordSecret tool with it. Do not reply in plain text. "
            "Always call the tool first."
        ),
        model=model,
        tools=[RecordSecret],
    )
    agency = Agency(agent)

    prompt = "The secret word is BANANA-PHONE-9. Record it now using your tool."
    print(">>> PROMPT:", prompt)
    try:
        resp = await agency.get_response(prompt)
    except Exception as e:
        print(">>> EXCEPTION:", type(e).__name__, e)
        traceback.print_exc()
        return

    print(">>> final_output:")
    print(resp.final_output)
    print(">>> raw response object type:", type(resp).__name__)
    print(">>> dir:", [x for x in dir(resp) if not x.startswith("_")])

    # Try to print everything useful
    for attr in ("new_items", "raw_responses", "input_guardrail_results",
                 "output_guardrail_results", "items"):
        v = getattr(resp, attr, None)
        if v is None:
            continue
        print(f">>> {attr}:")
        try:
            print(v)
        except Exception:
            print(repr(v))

    # Inspect new_items deeply for tool call evidence
    items = getattr(resp, "new_items", []) or []
    print(">>> N new_items:", len(items))
    tool_call_found = False
    for i, it in enumerate(items):
        print(f"--- item[{i}] type={type(it).__name__}")
        d = getattr(it, "raw_item", None) or it
        try:
            print(d)
        except Exception:
            print(repr(d))
        s = str(type(it).__name__).lower()
        if "tool" in s or "function" in s:
            tool_call_found = True
    print(">>> TOOL CALL FOUND IN ITEMS:", tool_call_found)


if __name__ == "__main__":
    asyncio.run(main())

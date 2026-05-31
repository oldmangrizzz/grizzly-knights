# Tool-calling path decision

**Date:** 2025-04-24 rev
**Question:** Does `https://api.githubcopilot.com` (with `gh auth token` +
`Copilot-Integration-Id: vscode-chat`) honor OpenAI function-calling end-to-end
through `agency_swarm` v1.9.9 + the `agents` SDK pipeline?

## Verdict

**YES — function-calling works. No text-protocol fallback needed.**

## Proof

Reproducer: `_fleet_status/probe_tools.py` — one `BaseTool` (`RecordSecret`),
one `Agent`, one prompt ("The secret word is BANANA-PHONE-9. Record it now
using your tool.").

Result (verbatim, trimmed):

```
>>> PROMPT: The secret word is BANANA-PHONE-9. Record it now using your tool.
>>> final_output:
The secret word has been successfully recorded.
>>> N new_items: 3
--- item[0] type=ToolCallItem
ResponseFunctionToolCall(
    arguments='{"secret_word":"BANANA-PHONE-9"}',
    call_id='call_I7ZvLzeSvj8kLIwHVhzuZeP4',
    name='RecordSecret',
    type='function_call',
    provider_data={'model': 'gpt-4o', 'response_id': 'chatcmpl-DkWyO5hwNls5LtHbenLzQZlZvPdgd'})
--- item[1] type=ToolCallOutputItem
{'call_id': 'call_I7ZvLzeSvj8kLIwHVhzuZeP4',
 'output': 'OK recorded: BANANA-PHONE-9',
 'type': 'function_call_output'}
--- item[2] type=MessageOutputItem
...text='The secret word has been successfully recorded.'...
>>> TOOL CALL FOUND IN ITEMS: True
```

A `ResponseFunctionToolCall` arrives from the Copilot endpoint, gets
dispatched by `agency_swarm` / `agents` SDK, and the tool output is sent
back into the next turn. The model then produces a natural-language reply.

## Implication for the rebuild

The engine wires `BaseTool` subclasses straight onto each character `Agent`
via `tools=[...]`. Cross-agent handoff uses `agency_swarm.Agency`'s built-in
`send_message` tools generated from `communication_flows`. No `<<TOOL: ...>>`
parsing. No regex dispatcher. The model invokes tools natively.

The four scene tools (`BringInCharacter`, `AddressCharacter`, `TakeAction`,
`ChangeSetting`) are dynamically subclassed per character at scene-spawn
time so each instance carries scene-scoped state (scene_id + actor_key) in
a closure rather than relying on agency_swarm to inject the caller agent.

"""Live single-call probe — verifies the response contract end to end.

One real chat completion against the hosted gateway with both server tools
declared. Prints the fields the demo and the scorer depend on:
  - status / served model / Otari-* headers
  - otari_tool_calls entries (type, status, ids)
  - usage block incl. cost_usd (six-decimal string) + pricing_source

Costs cents at most on gpt-oss-120b ($0.037/$0.17 per Mtok).
"""

import json

from otari_client import OtariClient, SERVER_TOOLS

client = OtariClient(model="openai/gpt-oss-120b", tags="app=local-wilding,probe=contract")
r = client.chat(
    [
        {
            "role": "user",
            "content": (
                "What is the latest stable Python release and when was it released? "
                "Search the web to confirm, then answer in one sentence."
            ),
        }
    ],
    tools=SERVER_TOOLS,
    tags="step=probe",
)

print("status:", r.status, "ok:", r.ok)
if r.error:
    print("error:", r.error[:400])
hdr = {k: v for k, v in r.headers.items() if k.startswith("otari") or k == "x-request-id"}
print("headers:", json.dumps(hdr, indent=1))
print("served_model:", r.served_model)

calls = r.tool_calls_ran
print("otari_tool_calls:", len(calls))
for c in calls:
    print("  ", json.dumps(c)[:300])

usage = r.body.get("usage") or {}
print("usage:", json.dumps(usage, indent=1))
print("cost_usd parsed:", r.cost_usd)
print("answer:", r.content[:300])

# keep the raw body for the scorer/evidence
with open("evidence/probe_contract.json", "w") as f:
    json.dump({"status": r.status, "headers": hdr, "body": r.body}, f, indent=2)
print("raw -> evidence/probe_contract.json")

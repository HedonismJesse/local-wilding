"""The demo — three beats, camera-shaped.

    python demo.py "claim to verify"          # live run
    python demo.py --replay                    # offline replay of evidence/

Beats:
  1. LOCAL   — a local model, no tools, answers from its weights.
  2. GATEWAY — the same task through hosted Otari: server-side
               web search + code execution, frontier candidates,
               budget-capped, every call receipted.
  3. CAP     — a tiny budget, deliberately: the pre-dispatch refusal
               shows enforcement is real (and costs $0).

Reads: OTARI_API_KEY, OTARI_BASE_URL, LOCAL_BASE_URL (optional),
LOCAL_MODEL, DEMO_BUDGET_USD (default 0.25).
"""

from __future__ import annotations

import os
import sys

import local_arm
from agent import run_task
from decide import ReceiptLog
from ledger import SpendLedger
from otari_client import OtariClient, SERVER_TOOLS
from replay import Recorder, replay_transport

DEFAULT_TASK = (
    "Verify this claim: 'The population of India grew more than 15% "
    "between 2015 and 2023.' Find official figures, do the math in code, "
    "and give a verdict with sources."
)

# Frontier escalation sits behind the open-weight primary — the weighted
# policy says the local-preferred split we *intend*; explain shows it.
CANDIDATES = ["openai/gpt-oss-120b", "anthropic/claude-fable-5"]
WEIGHTS = {"openai/gpt-oss-120b": 90, "anthropic:claude-sonnet-4-6": 10}


def main() -> int:
    replay = "--replay" in sys.argv
    task = next((a for a in sys.argv[1:] if not a.startswith("--")), DEFAULT_TASK)
    budget = float(os.environ.get("DEMO_BUDGET_USD", "0.25"))

    print("=== beat 1: local arm (no tools, weights only) ===")
    local_out = local_arm.run(task)
    if local_out:
        print("LOCAL ANSWER:", local_out["answer"][:500])

    print("\n=== beat 2: gateway arm (tools + budget + receipts) ===")
    recorder = None if replay else Recorder()
    transport = replay_transport() if replay else None
    client = OtariClient(transport=transport)
    if not client.api_key and not replay:
        print("OTARI_API_KEY unset — gateway arm cannot run. Set it or use --replay.")
        return 2

    ledger = SpendLedger(cap_usd=budget)
    receipts = ReceiptLog()
    out = run_task(
        client,
        task,
        tools=SERVER_TOOLS,
        ledger=ledger,
        receipts=receipts,
        candidates=CANDIDATES,
        weights=WEIGHTS,
        recorder=recorder,
    )
    print("\nGATEWAY ANSWER:", out["answer"][:1200])
    print(f"cost this run: ${out['cost_usd']:.4f}  (cap ${budget:.2f})")

    print("\n=== beat 3: the cap refuses ===")
    tiny = SpendLedger(cap_usd=0.01, path="evidence/spend_ledger_cap.jsonl")
    refuse_out = run_task(
        client,
        "Summarize today's top AI news in one sentence.",
        tools=SERVER_TOOLS,
        ledger=tiny,
        receipts=receipts,
    )
    if refuse_out["refused"]:
        print("enforcement shown: zero spend, typed refusal, ledger row written.")
    else:
        print("(cap did not bind — first call fit under $0.01; lower it and re-run)")

    print("\nledger:", ledger.path, " receipts:", receipts.path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

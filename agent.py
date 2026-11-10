"""The agent loop — one task, tools the model doesn't have, receipts it keeps.

Runs the same loop for both arms:
  * local arm  — a local OpenAI-compatible model, no tools declared.
    It answers from its weights. Honest about the ceiling.
  * gateway arm — hosted Otari, `otari_web_search` + `otari_code_execution`
    declared. The gateway runs them server-side; each execution shows up
    in the response's `otari_tool_calls` with what ran and what came back.

Every call is wrapped in a reserve/settle pair on the spend ledger and a
decision receipt — the three patterns adopted from otari's own machinery.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from decide import Receipt, ReceiptLog, explain, weighted_ordering
from ledger import BudgetRefused, SpendLedger
from otari_client import OtariClient, CallResult
import random

SYSTEM = (
    "You are a careful research agent. Verify claims with the tools available. "
    "If you have no tools, say clearly what you can and cannot verify. "
    "Report sources, math, and your confidence."
)


def _est_cost_usd(model: str) -> float:
    """Pre-dispatch estimate. Deliberately conservative ($0.02 covers a
    search+code step on hosted open-weights many times over — Recount's
    whole 4-step audit cost $0.0124). Real cost is settled from
    usage.cost_usd after the call."""
    return 0.02


def run_task(
    client: OtariClient,
    task: str,
    *,
    tools: Optional[list[dict]] = None,
    ledger: Optional[SpendLedger] = None,
    receipts: Optional[ReceiptLog] = None,
    candidates: Optional[list[str]] = None,
    weights: Optional[dict[str, float]] = None,
    max_steps: int = 6,
    recorder=None,
) -> dict[str, Any]:
    """Run one research task; return {answer, trace, cost_usd, refused}."""
    pool = candidates or [client.model]
    rng = random.Random()
    if weights:
        print("  policy", explain(pool, weights))
        pool = weighted_ordering(pool, weights, rng)

    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": task},
    ]
    trace: list[dict[str, Any]] = []
    total_cost = 0.0
    result = CallResult(ok=False, status=0)

    for step in range(1, max_steps + 1):
        model = pool[min(step - 1, len(pool) - 1)]
        res = None
        if ledger is not None:
            try:
                res = ledger.reserve(_est_cost_usd(model), f"step{step}:{model}")
            except BudgetRefused as e:
                print(f"  REFUSED (pre-dispatch): {e}")
                return {"answer": "", "trace": trace, "cost_usd": total_cost, "refused": str(e)}

        result = client.chat(messages, model=model, tools=tools, tags=f"step={step}")
        if recorder is not None:
            recorder.save(f"step{step}_{model.replace('/', '_')}", result)

        receipt = Receipt(
            label=f"step{step}",
            candidate=model,
            rationale=("weighted draw" if weights else "primary candidate"),
            confidence=(weights or {}).get(model, 1.0)
            / max(1e-9, sum((weights or {model: 1.0}).values())),
            outcome="ok" if result.ok else f"http {result.status}: {result.error[:80]}",
            cost_usd=result.cost_usd,
            served_model=result.served_model,
            attempt_count=result.attempt_count,
            selection_reason=("router:weighted" if weights else "direct"),
        )
        if receipts is not None:
            receipts.record(receipt)

        if not result.ok:
            if ledger is not None and res is not None:
                ledger.release(res, note=receipt.outcome)
            continue  # walk to next candidate — the draw without replacement

        total_cost += result.cost_usd
        if ledger is not None and res is not None:
            ledger.settle(res, result.cost_usd, note=f"served={result.served_model}")

        for tc in result.tool_calls_ran:
            trace.append({"tool": tc.get("name", "?"), "result": str(tc)[:300]})
            print(f"  tool ran server-side: {tc.get('name', '?')}")

        if result.content:
            return {"answer": result.content, "trace": trace, "cost_usd": total_cost, "refused": ""}
        break

    return {
        "answer": result.content or "(no answer — all candidates exhausted)",
        "trace": trace,
        "cost_usd": total_cost,
        "refused": "",
    }

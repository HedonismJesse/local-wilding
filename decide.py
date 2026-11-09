"""Decision receipts + weighted-draw ordering — two more adopted patterns.

From otari `services/routing/` (mechanism-verified 2026-11-09):

* Every routed attempt carries `rationale` + `confidence`; the usage row
  records `selection_reason`. After the fact you can always answer
  "why did it pick that".
* `weighted` backend: statistical split via draw-without-replacement;
  a failing provider sheds its share to survivors for free; zero weight
  drains a candidate without deleting it.
* `explain`: render the ordering WITHOUT dispatching — dry-run routing.

This module is our client-side copy of all three, ~80 lines.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field, asdict


def weighted_ordering(pool: list[str], weights: dict[str, float], rng: random.Random) -> list[str]:
    """Draw-without-replacement ordering; zero-weight candidates drain to tail."""
    remaining, ordered = list(pool), []
    while remaining:
        weighted = [(c, max(0.0, weights.get(c, 0.0))) for c in remaining]
        total = sum(w for _, w in weighted)
        if total <= 0:
            ordered.extend(remaining)  # declared order survives for drained tail
            break
        draw = rng.random() * total
        picked = next(c for c, w in reversed(weighted) if w > 0)
        acc = 0.0
        for c, w in weighted:
            if w <= 0:
                continue
            acc += w
            if draw < acc:
                picked = c
                break
        ordered.append(picked)
        remaining.remove(picked)
    return ordered


def explain(candidates: list[str], weights: dict[str, float]) -> str:
    """The dry-run: the split a policy *would* serve, no request made."""
    total = sum(max(0.0, weights.get(c, 0.0)) for c in candidates) or 1.0
    parts = [f"{c} {100.0 * max(0.0, weights.get(c, 0.0)) / total:.0f}%" for c in candidates]
    return "would serve: " + ", ".join(parts)


@dataclass
class Receipt:
    """One dispatch attempt, explained. Written to evidence/receipts.jsonl."""

    label: str
    candidate: str
    rationale: str
    confidence: float
    selection_reason: str = ""
    outcome: str = ""
    cost_usd: float = 0.0
    served_model: str = ""
    attempt_count: int = 1
    ts: float = field(default_factory=lambda: round(time.time(), 3))

    def one_line(self) -> str:
        return (
            f"[{self.label}] {self.candidate} <- {self.rationale} "
            f"(conf {self.confidence:.2f}) -> {self.outcome} "
            f"${self.cost_usd:.4f} [{self.selection_reason}]"
        )


class ReceiptLog:
    def __init__(self, path: str = "evidence/receipts.jsonl"):
        from pathlib import Path

        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, r: Receipt) -> None:
        import json

        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(r)) + "\n")
        print("  receipt:", r.one_line())

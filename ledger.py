"""Reserve-then-settle spend ledger — the Otari budgets pattern, client-side.

Pattern adopted from otari's `services/budgets/` (mechanism-verified at
source, 2026-11-09): a reservation is taken *before* dispatch — the call
is refused if the estimate would push committed spend over the cap — and
the settled row is written *after*, at the response's `usage.cost_usd`.

Our thin version: one JSONL ledger, one running total, refusal raised as
a typed error the demo can show on camera.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path


class BudgetRefused(RuntimeError):
    """The pre-dispatch refusal — the whole point of the pattern."""


@dataclass
class Reservation:
    seq: int
    label: str
    estimated_usd: float


class SpendLedger:
    def __init__(self, cap_usd: float, path: str = "evidence/spend_ledger.jsonl"):
        self.cap_usd = cap_usd
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.spent = 0.0
        self.reserved = 0.0
        self._seq = 0
        self._write({"event": "open", "cap_usd": cap_usd})

    def _write(self, row: dict) -> None:
        row["ts"] = round(time.time(), 3)
        row["spent_usd"] = round(self.spent, 6)
        row["reserved_usd"] = round(self.reserved, 6)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")

    @property
    def committed(self) -> float:
        return self.spent + self.reserved

    def reserve(self, estimated_usd: float, label: str) -> Reservation:
        """Refuse BEFORE dispatch if the estimate would breach the cap."""
        self._seq += 1
        if self.committed + estimated_usd > self.cap_usd:
            self._write(
                {
                    "event": "refuse",
                    "seq": self._seq,
                    "label": label,
                    "estimated_usd": estimated_usd,
                    "reason": "estimate would breach cap",
                }
            )
            raise BudgetRefused(
                f"[{label}] estimated ${estimated_usd:.4f} would breach "
                f"cap ${self.cap_usd:.4f} (committed ${self.committed:.4f})"
            )
        self.reserved += estimated_usd
        res = Reservation(seq=self._seq, label=label, estimated_usd=estimated_usd)
        self._write(
            {"event": "reserve", "seq": res.seq, "label": label, "estimated_usd": estimated_usd}
        )
        return res

    def settle(self, res: Reservation, actual_usd: float, note: str = "") -> None:
        self.reserved -= res.estimated_usd
        self.spent += actual_usd
        self._write(
            {
                "event": "settle",
                "seq": res.seq,
                "label": res.label,
                "estimated_usd": res.estimated_usd,
                "cost_usd": actual_usd,
                "note": note,
            }
        )

    def release(self, res: Reservation, note: str = "") -> None:
        """Reservation returned unused (call failed before billing)."""
        self.reserved -= res.estimated_usd
        self._write({"event": "release", "seq": res.seq, "label": res.label, "note": note})

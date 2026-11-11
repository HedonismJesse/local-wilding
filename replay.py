"""Record/replay — every raw gateway response lands in evidence/.

Record mode (default): each CallResult is saved to
evidence/NN_label.json next to a manifest row.

Replay mode (`--replay` or REPLAY=1): the transport is replaced by one
that serves recorded bodies in order — the whole demo re-runs offline
with no key and no spend. Judges can audit every byte we claim.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Optional

from otari_client import CallResult

EVIDENCE = Path(os.environ.get("EVIDENCE_DIR", "evidence"))


class Recorder:
    def __init__(self, directory: Path = EVIDENCE):
        self.dir = directory
        self.dir.mkdir(parents=True, exist_ok=True)
        self.seq = 0

    def save(self, label: str, result: CallResult) -> Path:
        self.seq += 1
        name = f"{self.seq:02d}_{label.replace('/', '_').replace(':', '_')}.json"
        path = self.dir / name
        path.write_text(
            json.dumps(
                {
                    "ok": result.ok,
                    "status": result.status,
                    "headers": result.headers,
                    "body": result.body,
                    "error": result.error,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return path


def replay_transport(directory: Path = EVIDENCE, pace: float | None = None,
                     match: str | None = None):
    """A transport serving recorded responses in filename order.

    ``pace`` is seconds slept per replayed call — replays otherwise dump
    instantly, which reads broken in the console. ``LW_REPLAY_PACE``
    overrides (default 0.8s).

    ``match`` restricts to files whose name contains the string — the
    recorded filenames carry the served model (`NN_stepK_<model>.json`),
    so "Llama" replays the local arm and "openai" the gateway arm.
    """
    files = sorted(p for p in directory.glob("*.json") if p.name[:2].isdigit())
    if match:
        files = [p for p in files if match in p.name]
    it = iter(files)
    if pace is None:
        pace = float(os.environ.get("LW_REPLAY_PACE", "0.8"))

    def _transport(url: str, payload: dict, headers: dict, timeout: int) -> CallResult:
        time.sleep(pace)
        path = next(it, None)
        if path is None:
            return CallResult(ok=False, status=0, error="replay exhausted")
        rec = json.loads(path.read_text(encoding="utf-8"))
        return CallResult(
            ok=rec["ok"],
            status=rec["status"],
            body=rec["body"],
            headers=rec["headers"],
            error=rec.get("error", ""),
        )

    _transport.manifest = files  # type: ignore[attr-defined]
    return _transport

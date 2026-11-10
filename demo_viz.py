"""The camera build — same machinery as demo.py, rendered live.

    python demo_viz.py            # the run, as a dashboard

What demo.py prints as scrollback, this draws as panels that light up:
two arms side by side, a live receipts feed, the refusal banner, the
capability card, then the scorer's checks flipping [ ] -> [x] one by one.
Every number on screen is the same receipt the files record.
"""

from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
import urllib.request
import queue as queue_mod

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
    sys.stderr.reconfigure(errors="replace")

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns

import local_arm
from agent import run_task
from decide import ReceiptLog
from ledger import SpendLedger
from otari_client import OtariClient, SERVER_TOOLS
from sphere_fitness import score as fitness_score

CLAIM = (
    "Claim under test: 'The population of India grew more than 15% "
    "between 2015 and 2023.'"
)
TASK = (
    "Verify this claim: 'India's population grew more than 15% between "
    "2015 and 2023.' Official figures: 2015 = 1,310,559,000 (World Bank "
    "SP.POP.TOTL); 2023 = 1,428,627,000 (UN World Population Prospects). "
    "Use code to compute the percentage change, then give a verdict."
)
CANDIDATES = ["openai/gpt-oss-120b", "anthropic/claude-fable-5"]
WEIGHTS = {"openai/gpt-oss-120b": 90, "anthropic/claude-fable-5": 10}

S = {
    "phase": "boot",
    "local_lines": ["waiting..."],
    "local_answer": "",
    "local_border": "grey35",
    "gw_lines": ["waiting..."],
    "gw_answer": "",
    "gw_border": "grey35",
    "tools_line": "",
    "feed": [],
    "card": "",
    "score_rows": [],
    "score_total": "",
    "t0": None,
}

console = Console()


def _clip(s: str, n: int) -> str:
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 3] + "..."


_ASCII = {"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
          "\u2013": "-", "\u2014": "-", "\u2026": "...", "\u00a0": " "}


def _ascii(s: str) -> str:
    for k, v in _ASCII.items():
        s = s.replace(k, v)
    return s.encode("ascii", "replace").decode()


def _answer_box(answer: str, lines: int = 9) -> str:
    words, out, cur = _ascii(answer).split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > 52:
            out.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        out.append(cur)
    if len(out) > lines:
        out = out[: lines - 1] + ["..."]
    return "\n".join(out)


def render() -> Group:
    claim = Panel(
        Text(CLAIM, justify="center"), border_style="cyan",
        title="local-wilding | devs-wilding", title_align="left",
    )
    local = Panel(
        Text(
            "\n".join(S["local_lines"] + ([""] + [_answer_box(S["local_answer"])] if S["local_answer"] else [])),
        ),
        title="LEFT ARM | llamafile 1B | no tools",
        border_style=S["local_border"], height=16,
    )
    gw = Panel(
        Text(
            "\n".join(S["gw_lines"] + ([""] + [_answer_box(S["gw_answer"])] if S["gw_answer"] else [])),
        ),
        title=f"RIGHT ARM | hosted Otari | {S['tools_line'] or 'server tools'}",
        border_style=S["gw_border"], height=16,
    )
    arms = Columns([local, gw], equal=True, expand=True)

    feed_rows = S["feed"][-6:]
    feed = Panel(Text("\n".join(feed_rows) or " "), title="receipts + ledger (live)", border_style="grey35", height=9)

    if S["card"]:
        card = Panel(Text(S["card"]), title="what x could not do", border_style="magenta", height=9)
    else:
        card = Panel(Text(" "), title="what x could not do", border_style="grey35", height=9)

    rows = "  ".join(S["score_rows"]) or "scorer waits for receipts..."
    bottom = Panel(Text(f"{rows}\n{S['score_total']}"), title="sphere_fitness - grades this demo", border_style="grey35", height=5)
    return Group(claim, arms, feed, card, bottom)


def _tool_surface(client: OtariClient) -> None:
    """GET /api/v1/tools -> one compact availability line + the tool
    declarations this key may actually send (disabled ones 403)."""
    try:
        req = urllib.request.Request(
            f"{client.base}/tools", headers={"Authorization": f"Bearer {client.api_key}"}
        )
        data = json.loads(urllib.request.urlopen(req, timeout=15).read().decode())
        bits = []
        for t in data.get("data", []):
            mark = "OK" if t.get("available") else "x"
            bits.append(f"{t.get('id','?').replace('otari_','')}[{mark}]")
        S["tools_line"] = " ".join(bits)
        S["avail_tools"] = [
            {"type": t["id"]}
            for t in data.get("data", [])
            if t.get("available") and t.get("id", "").startswith("otari_")
        ]
    except Exception as e:
        S["tools_line"] = f"tools probe failed: {e}"
        S["avail_tools"] = [{"type": "otari_code_execution"}]


def _push_feed(line: str) -> None:
    stamp = time.strftime("%H:%M:%S")
    S["feed"].append(f"{stamp}  {line}")


def _arm_events(arm: str):
    def on(kind: str, data: dict) -> None:
        lines = S["local_lines"] if arm == "local" else S["gw_lines"]
        if lines == ["waiting..."]:
            lines.clear()
        if kind == "step":
            lines.append(f">> step{data['step']} -> {data['model']}")
            _push_feed(f"{arm}: dispatch {data['model']}")
        elif kind == "tool":
            lines.append(f"   + tool ran server-side: {data['kind']}")
            _push_feed(f"{arm}: TOOL  {data['kind']}")
        elif kind == "settled":
            lines.append(f"   $ settled ${data['cost_usd']:.4f}")
            _push_feed(f"{arm}: settle ${data['cost_usd']:.4f} served={data['served']}")
        elif kind == "refused":
            lines.append(f"   X REFUSED pre-dispatch")
            _push_feed(f"{arm}: REFUSED {data['msg'][:80]}")
    return on


def _worker(recorder, receipts) -> None:
    """Runs the three beats; S carries display state, events carry timing.
    Stdout is captured for the duration — agent.run_task prints; the Live
    dashboard must not share the scroll region with stray prints."""
    import contextlib
    import io

    with contextlib.redirect_stdout(io.StringIO()):
        _run_beats(recorder, receipts)


def _run_beats(recorder, receipts) -> None:
    S["phase"] = "local"
    S["local_lines"] = ["llamafile (CPU) answering from weights..."]
    S["local_border"] = "yellow"
    out = (
        local_arm.run(
            TASK, recorder=recorder, receipts=receipts, on_event=_arm_events("local")
        )
        if local_arm.available()
        else None
    )
    if out:
        S["local_lines"] = [l for l in S["local_lines"] if "thinking" not in l] or ["answered from weights only"]
        S["local_answer"] = out["answer"]
    else:
        S["local_lines"] = ["skipped - LOCAL_BASE_URL unset (marked, not claimed)"]
        S["local_border"] = "red"

    S["phase"] = "gateway"
    S["gw_lines"] = ["declaring tools:", "  " + S["tools_line"]]
    S["gw_border"] = "green"
    client = OtariClient()
    ledger = SpendLedger(cap_usd=float(os.environ.get("DEMO_BUDGET_USD", "0.25")))
    out = run_task(
        client,
        TASK,
        tools=S.get("avail_tools") or SERVER_TOOLS, ledger=ledger, receipts=receipts,
        candidates=CANDIDATES, weights=WEIGHTS, recorder=recorder,
        on_event=_arm_events("gw"),
    )
    S["gw_answer"] = out["answer"]
    S["gw_tools_ran"] = [t["tool"] for t in out["trace"]]

    S["phase"] = "cap"
    tiny = SpendLedger(cap_usd=0.01, path="evidence/spend_ledger_cap.jsonl")
    refuse = run_task(
        client, "Summarize today's top AI news in one sentence.",
        tools=S.get("avail_tools") or SERVER_TOOLS, ledger=tiny, receipts=receipts,
        on_event=_arm_events("cap"),
    )
    if refuse["refused"]:
        _push_feed("cap: REFUSED pre-dispatch - $0.0000 spent")

    # The capability card — what the local arm literally could not do.
    tools_ran = ", ".join(dict.fromkeys(S.get("gw_tools_ran") or ["none"]))
    rows = [
        f"                     local 1B          otari gateway",
        f"tools declared       none              {S['tools_line']}",
        f"tools actually ran   -                 {tools_ran}",
        f"cost                 $0.0000           ${out['cost_usd']:.4f} (settled)",
    ]
    pcts = [
        float(x)
        for x in re.findall(r"(\d+(?:\.\d+)?)[^\d%]{0,4}%", _ascii(out["answer"] or ""))
    ]
    growth = [p for p in pcts if p < 15]
    if growth:
        actual = growth[-1]
        bar = "#" * max(1, round(actual / 15 * 10))
        rows += ["", f"claim said >15%    [##########>----]",
                 f"verified {actual:>5.1f}%   [{bar:<15}]"]
    S["card"] = "\n".join(rows)
    S["phase"] = "score"


def main() -> int:
    client = OtariClient()
    if not client.api_key:
        print("OTARI_API_KEY unset.")
        return 2

    _tool_surface(client)
    from replay import Recorder
    recorder = Recorder()
    receipts = ReceiptLog()

    worker = threading.Thread(target=_worker, args=(recorder, receipts), daemon=True)

    with Live(render(), console=console, refresh_per_second=8, screen=False) as live:
        worker.start()
        while S["phase"] != "score" and worker.is_alive():
            time.sleep(0.12)
            live.update(render())
        worker.join(timeout=5)

        # Score reveal — the certificates light up one at a time.
        rep = fitness_score(
            ["local", "gateway", "refusal", "evidence", "cost"], "evidence", "."
        )
        rows = []
        for name, ok in {**rep["beats"], **rep["probes"]}.items():
            rows.append(f"[{'x' if ok else ' '}] {name}")
            S["score_rows"] = list(rows)
            live.update(render())
            time.sleep(0.45)
        S["score_total"] = (
            f"beats {rep['beat_score']} + probes {rep['probe_score']} "
            f"= total {rep['total']}/9 — every claim backed by a file in evidence/"
        )
        live.update(render())
        time.sleep(8)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

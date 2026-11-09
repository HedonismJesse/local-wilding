"""Zero-dependency client for the Otari gateway (OpenAI-compatible).

stdlib only — no SDK. One key, one endpoint, receipts on every call.

Otari specifics exercised here:
  - chat completions through the hosted gateway
  - server-side tools declared in the request (`otari_web_search`,
    `otari_code_execution`, `otari_web_fetch`) — the gateway runs them
    and reports executions in `otari_tool_calls`
  - `Otari-Tags` request header for per-step tagging
  - `Otari-*` response headers + `usage.cost_usd` readback
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

BASE = os.environ.get("OTARI_BASE_URL", "https://api.otari.ai/api/v1").rstrip("/")

SERVER_TOOLS = [
    {"type": "otari_web_search"},
    {"type": "otari_code_execution"},
]


@dataclass
class CallResult:
    """One gateway call, with the receipts a ledger and a judge want."""

    ok: bool
    status: int
    body: dict[str, Any] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    error: str = ""

    @property
    def content(self) -> str:
        try:
            return self.body["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError):
            return ""

    @property
    def cost_usd(self) -> float:
        return float((self.body.get("usage") or {}).get("cost_usd") or 0.0)

    @property
    def tool_calls_ran(self) -> list[dict[str, Any]]:
        """Tool executions the gateway ran server-side, in order."""
        return list(self.body.get("otari_tool_calls") or [])

    @property
    def served_model(self) -> str:
        return self.headers.get("otari-model") or self.body.get("model", "")

    @property
    def attempt_count(self) -> int:
        try:
            return int(self.headers.get("otari-attempt-count", "1"))
        except ValueError:
            return 1


def _post(url: str, payload: dict, headers: dict[str, str], timeout: int) -> CallResult:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return CallResult(
                ok=True,
                status=r.status,
                body=json.loads(r.read().decode()),
                headers={k.lower(): v for k, v in r.headers.items()},
            )
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode())
        except Exception:
            body = {}
        return CallResult(
            ok=False,
            status=e.code,
            body=body,
            headers={k.lower(): v for k, v in e.headers.items()},
            error=str((body.get("error") or {}).get("message") or e),
        )
    except Exception as e:  # network down, DNS, timeout
        return CallResult(ok=False, status=0, error=str(e))


class OtariClient:
    """Thin client: chat + catalog. Every call is receipted by the caller's
    ledger — this object keeps no state but the key and the transport."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base: Optional[str] = None,
        model: str = "openai/gpt-oss-120b",
        tags: str = "app=local-wilding",
        transport: Optional[Callable] = None,
    ):
        self.api_key = api_key or os.environ.get("OTARI_API_KEY", "")
        self.base = (base or BASE).rstrip("/")
        self.model = model
        self.tags = tags
        self._post = transport or _post

    def _headers(self, extra_tags: str = "") -> dict[str, str]:
        tags = f"{self.tags},{extra_tags}" if extra_tags else self.tags
        return {"Authorization": f"Bearer {self.api_key}", "Otari-Tags": tags}

    def chat(
        self,
        messages: list[dict],
        *,
        model: Optional[str] = None,
        tools: Optional[list[dict]] = None,
        tags: str = "",
        timeout: int = 120,
    ) -> CallResult:
        payload: dict[str, Any] = {"model": model or self.model, "messages": messages}
        if tools:
            payload["tools"] = tools
        return self._post(
            f"{self.base}/chat/completions", payload, self._headers(tags), timeout
        )

    def models(self, timeout: int = 30) -> CallResult:
        """GET /models — the hosted catalog, with live per-model pricing."""
        url = f"{self.base}/models"
        req = urllib.request.Request(url, headers=self._headers("catalog"))
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return CallResult(
                    ok=True,
                    status=r.status,
                    body=json.loads(r.read().decode()),
                    headers={k.lower(): v for k, v in r.headers.items()},
                )
        except Exception as e:
            return CallResult(ok=False, status=0, error=str(e))

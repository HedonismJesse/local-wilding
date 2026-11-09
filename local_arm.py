"""Local arm — any local OpenAI-compatible server, no tools, no spend.

Point LOCAL_BASE_URL at llamafile / llama.cpp server / LM Studio —
anything serving /v1/chat/completions. This arm exists to show the
contrast: the same agent loop, the same task, a small model with no
tools answering from weights alone.

Skipped (loudly, not silently) when LOCAL_BASE_URL is unset.
"""

from __future__ import annotations

import os
from typing import Any, Optional

from agent import run_task
from otari_client import OtariClient

LOCAL_BASE = os.environ.get("LOCAL_BASE_URL", "").rstrip("/")
LOCAL_MODEL = os.environ.get("LOCAL_MODEL", "local")


def available() -> bool:
    return bool(LOCAL_BASE)


def local_client() -> OtariClient:
    """Same client class — llamafile speaks the same OpenAI dialect.
    Key is a placeholder; local servers ignore it."""
    return OtariClient(
        api_key=os.environ.get("LOCAL_API_KEY", "local"),
        base=LOCAL_BASE or "http://localhost:8080/v1",
        model=LOCAL_MODEL,
        tags="app=local-wilding,arm=local",
    )


def run(task: str, **kwargs: Any) -> Optional[dict]:
    if not available():
        print("  local arm SKIPPED — LOCAL_BASE_URL unset (start llamafile or any")
        print("  local OpenAI-compatible server, then re-run). Marked honestly,")
        print("  not claimed.")
        return None
    return run_task(local_client(), task, tools=None, **kwargs)

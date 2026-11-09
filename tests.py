"""Offline smoke tests — no key, no network, no spend.

    python tests.py

Uses a mock transport; proves the ledger refuses, receipts order, the
loop terminates, and replay serves recorded files.
"""

from __future__ import annotations

import json
import random
import tempfile
import unittest
from pathlib import Path

from agent import run_task
from decide import ReceiptLog, explain, weighted_ordering
from ledger import BudgetRefused, SpendLedger
from otari_client import CallResult, OtariClient, SERVER_TOOLS
from replay import Recorder, replay_transport

BODY = {
    "choices": [{"message": {"role": "assistant", "content": "verified: false, growth was ~9%"}}],
    "model": "openai/gpt-oss-120b",
    "usage": {"prompt_tokens": 100, "completion_tokens": 40, "cost_usd": 0.0031},
    "otari_tool_calls": [{"name": "otari_web_search"}, {"name": "otari_code_execution"}],
}


def _transport_ok(url, payload, headers, timeout):
    return CallResult(
        ok=True,
        status=200,
        body=json.loads(json.dumps(BODY)),
        headers={"otari-model": "openai/gpt-oss-120b", "otari-attempt-count": "1"},
    )


def _transport_fail(url, payload, headers, timeout):
    return CallResult(ok=False, status=503, error="provider down")


class TestLedger(unittest.TestCase):
    def test_reserve_settle(self):
        with tempfile.TemporaryDirectory() as d:
            led = SpendLedger(cap_usd=0.05, path=str(Path(d) / "l.jsonl"))
            r = led.reserve(0.02, "s1")
            led.settle(r, 0.003)
            self.assertAlmostEqual(led.spent, 0.003)
            self.assertAlmostEqual(led.reserved, 0.0)

    def test_refusal_is_pre_dispatch(self):
        with tempfile.TemporaryDirectory() as d:
            led = SpendLedger(cap_usd=0.01, path=str(Path(d) / "l.jsonl"))
            with self.assertRaises(BudgetRefused):
                led.reserve(0.02, "too-big")
            self.assertAlmostEqual(led.committed, 0.0)


class TestRouting(unittest.TestCase):
    def test_weighted_ordering_is_a_permutation(self):
        pool = ["a", "b", "c"]
        order = weighted_ordering(pool, {"a": 70, "b": 20, "c": 10}, random.Random(7))
        self.assertEqual(sorted(order), sorted(pool))

    def test_zero_weight_drains_not_deletes(self):
        order = weighted_ordering(["a", "b"], {"a": 100, "b": 0}, random.Random(1))
        self.assertEqual(order[0], "a")
        self.assertIn("b", order)

    def test_explain_without_dispatch(self):
        self.assertIn("a 70%", explain(["a", "b"], {"a": 70, "b": 30}))


class TestAgentLoop(unittest.TestCase):
    def test_full_run_with_tools_and_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            client = OtariClient(api_key="x", transport=_transport_ok)
            led = SpendLedger(cap_usd=0.25, path=str(Path(d) / "spend.jsonl"))
            rec = ReceiptLog(path=str(Path(d) / "receipts.jsonl"))
            out = run_task(client, "verify claim", tools=SERVER_TOOLS, ledger=led, receipts=rec)
            self.assertFalse(out["refused"])
            self.assertIn("verified", out["answer"])
            self.assertAlmostEqual(out["cost_usd"], 0.0031)
            self.assertEqual(len(out["trace"]), 2)  # both server-side tools surfaced

    def test_failed_candidate_walks(self):
        """A 503 on the primary hands to the tail candidate — shed-for-free."""
        calls = []

        def flaky(url, payload, headers, timeout):
            calls.append(payload["model"])
            if payload["model"] == "a/fail":
                return _transport_fail(url, payload, headers, timeout)
            return _transport_ok(url, payload, headers, timeout)

        client = OtariClient(api_key="x", transport=flaky)
        out = run_task(client, "t", candidates=["a/fail", "b/ok"], max_steps=2)
        self.assertEqual(calls, ["a/fail", "b/ok"])
        self.assertIn("verified", out["answer"])


class TestReplay(unittest.TestCase):
    def test_record_then_replay_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            rec = Recorder(directory=Path(d))
            rec.save("step1", _transport_ok("u", {}, {}, 1))
            tp = replay_transport(Path(d))
            result = tp("url", {}, {}, 5)
            self.assertTrue(result.ok)
            self.assertEqual(result.cost_usd, 0.0031)


if __name__ == "__main__":
    unittest.main(verbosity=2)

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


class TestSphereFitness(unittest.TestCase):
    """The scorer must discriminate evidence from empty dirs and
    enforce certificates on claimed beats — never pass prose."""

    def _write(self, d, name, obj):
        Path(d, name).write_text(
            obj if isinstance(obj, str) else json.dumps(obj),
            encoding="utf-8")

    def _evidence_with_receipts(self, d):
        self._write(d, "receipts.jsonl",
                    '{"label":"s1","outcome":"ok","cost_usd":0.0031,'
                    '"served_model":"m","ts":1}\n')
        self._write(d, "spend_ledger_cap.jsonl",
                    '{"event":"refuse","seq":1,"reason":"cap"}\n')
        self._write(d, "step1.json", dict(BODY))  # has otari_tool_calls

    def test_discriminates_evidence_from_empty(self):
        import sphere_fitness as sf
        with tempfile.TemporaryDirectory() as d:
            empty = sf.score(["gateway"], str(Path(d) / "none"), d)
            self.assertEqual(empty["total"], 0)
        with tempfile.TemporaryDirectory() as d:
            ev = Path(d) / "ev"
            ev.mkdir()
            self._evidence_with_receipts(str(ev))
            full = sf.score(["gateway", "refusal"], str(ev), d)
            self.assertGreater(full["total"], empty["total"])

    def test_certificate_enforcement_on_claimed_beats(self):
        import sphere_fitness as sf
        with tempfile.TemporaryDirectory() as d:
            rep = sf.score(["gateway", "refusal"], str(Path(d) / "none"), d)
            self.assertEqual(rep["certificate_failures"],
                             ["gateway", "refusal"])
            self.assertEqual(rep["beats"], {"gateway": False,
                                            "refusal": False})

    def test_document_probe_fires_both_ways(self):
        import sphere_fitness as sf
        with tempfile.TemporaryDirectory() as d:
            bare = sf.document_probes(d)
            self.assertFalse(bare["readme_first_commit"])
            Path(d, "README.md").write_text(
                "first Otari commit: /commit/cb6f106 devs-wilding")
            Path(d, "FEEDBACK.md").write_text(
                "the reservations machinery in services/budgets …")
            filled = sf.document_probes(d)
            self.assertTrue(filled["readme_first_commit"])
            self.assertTrue(filled["feedback_cites_source"])


class TestRenderAudit(unittest.TestCase):
    """Regression: the signatures the 2026-11-10 session calibrated
    against its replay corpus must keep discriminating — v2's fin ear
    fires streak, v3 doesn't; a060 oversized; f030 occludes the title;
    dense ASCII frames illegible, sparse ones not."""

    @staticmethod
    def _flags(rel):
        import render_audit as ra
        return ra.audit_frame(Path(__file__).parent / rel)["flags"]

    def test_v2_fin_ear_streaks_v3_clean(self):
        self.assertIn("streak_component", self._flags("pig_v2.png"))
        self.assertNotIn("streak_component", self._flags("pig_v3.png"))

    def test_giant_pig_frame_oversized(self):
        self.assertIn("subject_oversized",
                      self._flags("anim_frames/a060.png"))
        self.assertNotIn("subject_oversized",
                         self._flags("anim_frames/a000.png"))

    def test_ascii_on_title_occludes(self):
        self.assertIn("occludes_text",
                      self._flags("fly_frames/f030.png"))
        self.assertNotIn("occludes_text",
                         self._flags("anim_frames/a000.png"))

    def test_dense_ascii_illegible_sparse_not(self):
        self.assertIn("illegible_at_scale",
                      self._flags("fly_frames/f034.png"))
        self.assertNotIn("illegible_at_scale",
                         self._flags("fly_frames/f000.png"))

    @staticmethod
    def _spec_flags(rel):
        import json
        import render_audit as ra
        spec = json.loads(
            (Path(__file__).parent / "canon" / "pig.json").read_text())
        return ra.audit_frame(Path(__file__).parent / rel, spec)["flags"]

    def test_spec_catches_v2_missing_snout(self):
        self.assertIn("missing_snout_vs_spec",
                      self._spec_flags("pig_v2.png"))
        self.assertNotIn("missing_snout_vs_spec",
                         self._spec_flags("pig_v3.png"))


class TestCandidateSheet(unittest.TestCase):
    """Pipeline mechanics: the grid produces the cross product and
    verdict capture writes ledger-shaped rows with audit flags as
    the named_failure vocabulary."""

    def test_grid_cross_product(self):
        import candidate_sheet as cs
        g = cs._grid({"pose": [0, 12], "head_ratio": [1.0, 1.3]})
        self.assertEqual(len(g), 4)
        self.assertIn({"pose": 12, "head_ratio": 1.3}, g)

    def test_verdict_rows_carry_audit_flags(self):
        import candidate_sheet as cs
        import types
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "manifest.json").write_text(json.dumps({"variants": [
                {"id": "A", "params": {"pose": 0}, "png": "A.png",
                 "flags": ["clean"]}]}))
            ledger = d / "reads.jsonl"
            ledger.write_text("")
            args = types.SimpleNamespace(
                verdict_dir=d, ledger=ledger,
                verdicts=["A=reject:test-fail"])
            self.assertEqual(cs.cmd_verdict(args), 0)
            row = json.loads(ledger.read_text().strip())
            self.assertEqual(row["verdict"], "reject")
            self.assertEqual(row["named_failure"], "clean")
            self.assertEqual(row["variant_params"], {"pose": 0})

    def test_sheet_refuses_without_refs(self):
        """art:reference-canon gate: no --refs and no --allow-no-ref
        -> refusal before the builder is ever touched (the mass-reject
        regression: lineage-extrapolated candidates)."""
        import candidate_sheet as cs
        import types
        args = types.SimpleNamespace(
            refs=None, allow_no_ref=False, ref_pick=None,
            builder="pig_sheet:draw_pig", param=None, variants=None,
            spec=None, out_dir=Path("unused"))
        self.assertEqual(cs.cmd_sheet(args), 2)

    def test_refs_page_lists_signature_elements(self):
        import candidate_sheet as cs
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "r.png").write_bytes(
                bytes.fromhex("89504e470d0a1a0a") + b"\x00" * 32)
            man = {"subject": "pig", "refs": [{
                "id": "r1", "file": "r.png", "source": "s",
                "license": "CC0", "author": "a", "role": "style-target",
                "signature_elements": ["round bean silhouette"]}]}
            p = cs._refs_page(man, d / "out", base=d)
            html = p.read_text()
            self.assertIn("r1", html)
            self.assertIn("round bean silhouette", html)
            self.assertIn("data:image/png;base64,", html)

    def test_verdict_rows_carry_refs(self):
        import candidate_sheet as cs
        import types
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "manifest.json").write_text(json.dumps({
                "refs": {"manifest": "canon/refs/refs.json",
                         "picks": ["walnutty_flying"]},
                "variants": [{"id": "A", "params": {"pose": 0},
                              "png": "A.png", "flags": []}]}))
            ledger = d / "reads.jsonl"
            ledger.write_text("")
            args = types.SimpleNamespace(
                verdict_dir=d, ledger=ledger, verdicts=["A=pick"])
            cs.cmd_verdict(args)
            row = json.loads(ledger.read_text().strip())
            self.assertEqual(row["refs"], ["walnutty_flying"])
            self.assertFalse(row["no_ref"])

    def test_wing_attachment_consistency(self):
        """Operator rule: build wings+pig together AND separately -
        the pig region must be identical; the delta IS the wing."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import resemblance as rsm
        from pig_w4 import draw_w4_pig
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            for name, w in [("on", True), ("off", False)]:
                fig, ax = plt.subplots(figsize=(12, 7.5), dpi=60)
                draw_w4_pig(ax, pose="fly", wings=w, phase=0.3)
                fig.savefig(d / f"{name}.png",
                            facecolor="#0D1B26")
                plt.close(fig)
            mon = rsm.pig_mask(d / "on.png")
            moff = rsm.pig_mask(d / "off.png")
            # wing pixels are excluded by NON_PIG, so the remaining
            # pig silhouette must match the wingless render ~exactly
            n = min(mon.shape[0], moff.shape[0]), \
                min(mon.shape[1], moff.shape[1])
            mon, moff = mon[:n[0], :n[1]], moff[:n[0], :n[1]]
            iou = (mon & moff).sum() / max((mon | moff).sum(), 1)
            self.assertGreater(iou, 0.9)

    def test_pose_integrity_no_defects(self):
        """art:state-oracles gate — the 'can you not see' regression
        pin: every canonical pose must pass structural integrity
        (no interior holes / stroke bleed / self-intersection /
        frame clip / fragments). A foot turning weird, a white gash,
        a lost mark = immediate flag (operator 2026-11-10)."""
        import pig_w5
        import state_oracle as so
        for pose, kw in [("rest", {}), ("notice", {}),
                         ("flee", {"facing": -1}),
                         ("fly", {"tilt": 18, "wings": 1})]:
            img = pig_w5.render_pose(pose, **kw)
            rep = so.inspect(pose, pig_w5.pose_spec(pose), img,
                             wings=bool(kw.get("wings")))
            self.assertEqual(rep["verdict"], "CLEAN",
                             f"{pose}: {rep['integrity']}")

    def test_pose_states_read(self):
        """State recognizers: rest IS lying, flee IS running, fly IS
        airborne — poses must score their intended state."""
        import pig_w5
        import state_oracle as so
        rest = pig_w5.pose_spec("rest")
        flee = pig_w5.pose_spec("flee")
        fly = pig_w5.pose_spec("fly")
        self.assertGreater(so.is_lying(rest)["score"], 0.4)
        self.assertGreater(so.is_running(flee)["score"],
                           so.is_running(rest)["score"])
        self.assertTrue(so.is_flying(fly, wings=True)["score"] > 0.5)

    def test_report_schema_verdict_is_rollups(self):
        """The report's CLEAN must be computed FROM integrity
        defects — a misread key once produced false '12 CLEAN'
        (2026-11-11). Pin the schema: every run has a verdict that
        equals the defect rollup."""
        import json
        r = json.loads(Path("_oracle_report.json").read_text())
        self.assertTrue(r, "empty report")
        for k, v in r.items():
            self.assertIn("verdict", v, f"{k}: no verdict field")
            self.assertIn("integrity", v, f"{k}: no integrity block")
            bad = [n for n, d in v["integrity"].items()
                   if isinstance(d, dict) and d.get("defect")]
            expected = "CLEAN" if not bad else f"DEFECTS: {','.join(bad)}"
            self.assertEqual(v["verdict"], expected,
                             f"{k}: verdict '{v['verdict']}' "
                             f"!= rollup '{expected}'")


if __name__ == "__main__":
    unittest.main(verbosity=2)

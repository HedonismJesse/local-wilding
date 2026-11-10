"""Sphere-fitness scorer — mechanical rating of submission candidates.

Each submission genome claims a set of beats; every claimed beat must
produce its promised receipt in evidence/. Certificate enforcement:
a claimed beat with no receipt scores ZERO on that beat — unexercised
claims cannot ride on prose.

Oracle classes, honestly labeled:
  certificate-check — the receipt exists or it doesn't (this file)
  property-probe    — document checks on README/feedback/script
  unverifiable      — persuasion. No check exists; none is faked.

    python sphere_fitness.py --evidence evidence --repo .
    python sphere_fitness.py --beats local gateway refusal evidence cost
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def _rows(path: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if not path.is_dir():
        return out
    for f in sorted(path.iterdir()):
        if f.suffix == ".jsonl":
            for line in f.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    try:
                        out.append(json.loads(line))
                    except ValueError:
                        pass
        elif f.suffix == ".json":
            try:
                out.append(json.loads(f.read_text(encoding="utf-8")))
            except ValueError:
                pass
    return out


def evidence_checks(evidence_dir: str) -> Dict[str, bool]:
    """Certificate checks: each beat's promised receipt exists or not."""
    rows = _rows(Path(evidence_dir))
    receipts = [r for r in rows if "label" in r and "outcome" in r]
    events = [r for r in rows if "event" in r]
    raw = [r for r in rows if "choices" in r]
    served_ok = [r for r in receipts
                 if str(r.get("outcome", "")).startswith("ok")
                 and r.get("served_model")]
    return {
        # local arm: served by a model, no otari tool calls anywhere
        # in its raw response — the beat is "no tools, weights only".
        "local": any("otari_tool_calls" not in r and "choices" in r
                     for r in raw) or bool(served_ok),
        # gateway arm: a raw response with non-empty otari tool calls.
        "gateway": any(r.get("otari_tool_calls") for r in raw),
        # refusal beat: a ledger refuse event.
        "refusal": any(e.get("event") == "refuse" for e in events),
        # evidence beat: at least one raw response persisted.
        "evidence": bool(raw),
        # cost receipt: a settled spend or a positive cost_usd row.
        "cost": (any(r.get("cost_usd", 0) and r["cost_usd"] > 0
                     for r in receipts)
                 or any(e.get("event") == "settle"
                        and e.get("spent_usd", 0) > 0 for e in events)),
    }


def document_probes(repo_dir: str) -> Dict[str, bool]:
    """Property probes on the submission documents."""
    repo = Path(repo_dir)
    readme = ""
    rp = repo / "README.md"
    if rp.is_file():
        readme = rp.read_text(encoding="utf-8", errors="replace")
    fb = ""
    for name in ("FEEDBACK.md", "feedback.md"):
        fp = repo / name
        if fp.is_file():
            fb = fp.read_text(encoding="utf-8", errors="replace")
    script = ""
    for name in ("VIDEO.md", "SCRIPT.md", "video_script.md"):
        sp = repo / name
        if sp.is_file():
            script = sp.read_text(encoding="utf-8", errors="replace")
    cites_source = any(tok in fb for tok in (
        "services/", "mozilla-ai/otari", "adapters/", "reservations"))
    return {
        "readme_first_commit": ("commit/cb6f106" in readme
                                or "first otari commit" in readme.lower()
                                or "devs-wilding" in readme),
        "feedback_cites_source": bool(fb) and cites_source,
        "feedback_present": bool(fb),
        "video_script_present": bool(script),
    }


def score(claimed_beats: List[str], evidence_dir: str,
          repo_dir: str = ".") -> Dict[str, Any]:
    """Score a candidate: claimed beats need certificates; documents
    add property-probe coverage. Returns per-beat rows + total."""
    ev = evidence_checks(evidence_dir)
    beats = {b: bool(ev.get(b)) for b in claimed_beats}
    probe = document_probes(repo_dir)
    beat_hits = sum(beats.values())
    probe_hits = sum(probe.values())
    return {
        "beats": beats,
        "beat_score": f"{beat_hits}/{len(claimed_beats)}",
        "certificate_failures": [b for b, ok in beats.items() if not ok],
        "probes": probe,
        "probe_score": f"{probe_hits}/{len(probe)}",
        "total": beat_hits + probe_hits,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--evidence", default="evidence")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--beats", nargs="*", default=[
        "local", "gateway", "refusal", "evidence", "cost"])
    args = ap.parse_args()
    rep = score(args.beats, args.evidence, args.repo)
    print(json.dumps(rep, indent=2, sort_keys=True))
    fails = rep["certificate_failures"]
    if fails:
        print(f"certificate FAILURES: {', '.join(fails)} "
              f"(claimed beats with no receipt)")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())

# provenance: author=devin; created=2026-11-10; source=reference
#   canon/refs/refs.json (waddles parts) +
#   ai-hub Artifacts/plans/repo/ART_SPHERE_CHILD_SPHERES_2026-11-10.md
#   (art:reference-canon similarity scale); purpose=score candidate
#   renders against anchor-reference part definitions - "matches the
#   reference" as a measurable probe, not eyeballs; intent=production
"""ref_match — the similarity scale.

A ref's `parts` are named subject-bbox zones [y0,x0,y1,x1] + an
expected color family (hex). score(candidate, ref) crops the
candidate's subject to each part zone and checks coverage + color
proximity. Result: 0..1 ref-match score + per-part misses — so a
candidate that drops the anchor's snout droop or ear flap is MEASURED
missing it, and expansion refs can be ranked against the same definer
(original stays primary until a higher score is confirmed).

    python ref_match.py --refs canon/refs/refs.json --ref waddles \
        --png candidates/storyboard_w2_v1/A.png
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


def _hex(rgb: str) -> np.ndarray:
    rgb = rgb.lstrip("#")
    return np.array([int(rgb[i:i + 2], 16) for i in (0, 2, 4)])


def subject_crop(img: Image.Image) -> np.ndarray:
    """RGBA array cropped to the non-empty subject bbox."""
    a = np.asarray(img.convert("RGBA")).astype(np.int16)
    opaque = a[..., 3] > 40
    if not opaque.any():
        return a
    ys, xs = np.where(opaque)
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def score(png: Path, ref: dict, mirror: bool = False) -> dict:
    """Part-definer scoring: per part, coverage of its zone by pixels
    within color distance of the part's expected color (or just
    non-background coverage when the part color is 'any'). mirror
    flips the candidate first (mirrored poses like flee)."""
    a = subject_crop(Image.open(png))
    if mirror:
        a = a[:, ::-1]
    H, W = a.shape[:2]
    opaque = a[..., 3] > 40
    hits, misses, parts = [], [], {}
    total_w = 0.0
    for name, p in (ref.get("parts") or {}).items():
        y0, x0, y1, x1 = p["bbox_frac"]
        w = float(p.get("weight", 1.0))
        total_w += w
        r = a[int(y0 * H):max(int(y1 * H), int(y0 * H) + 1),
              int(x0 * W):max(int(x1 * W), int(x0 * W) + 1)]
        if r.size == 0:
            misses.append(name)
            continue
        mask = r[..., 3] > 40
        if "color" in p:
            dist = np.abs(r[..., :3] - _hex(p["color"])).sum(-1)
            mask &= dist < int(p.get("color_dist", 120))
        cov = mask.sum() / mask.size
        parts[name] = round(float(cov), 3)
        (hits if cov >= float(p.get("min_coverage", 0.15))
         else misses).append(name)
    sc = (sum(float((ref["parts"][n].get("weight", 1.0)))
              for n in hits) / total_w) if total_w else 0.0
    return {"ref": ref["id"], "score": round(sc, 3),
            "parts": parts, "misses": misses}


def family(man: dict, anchor_id: str,
           threshold: float = 0.5) -> dict:
    """Sphere-finder pass: score every manifest ref against the
    anchor's part definer. Same-family refs sit inside the hull
    (score >= threshold); the rest drift to the boundary (opposites -
    they define what the family is NOT). Then synthesize the hull
    target: anchor parts + signature elements shared by >=2 family
    members = the 'best version of the example' spec."""
    anchor = next(r for r in man["refs"] if r["id"] == anchor_id)
    rows = []
    for r in man["refs"]:
        if r["id"] == anchor_id or r.get("status") == "rejected":
            continue
        f = Path(r["file"])
        m = (score(f, anchor) if f.exists()
             else {"score": 0.0, "misses": list(anchor.get("parts", {}))})
        rows.append({"id": r["id"], "role": r.get("role"),
                     "score": m["score"],
                     "family": m["score"] >= threshold})
    fam = [r["id"] for r in rows if r["family"]]
    # shared elements across family = the canon grammar; elements
    # only on one member = style-variant axes
    shared = set()
    members = [r for r in man["refs"]
               if r["id"] in fam or r["id"] == anchor_id]
    for i, r in enumerate(members):
        els = set(r.get("signature_elements", []))
        if i == 0:
            shared = els
        else:
            shared &= els
    return {"anchor": anchor_id, "threshold": threshold,
            "ranking": sorted(rows, key=lambda x: -x["score"]),
            "family": fam,
            "hull": {"parts": anchor.get("parts", {}),
                     "shared_elements": sorted(shared)}}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--refs", type=Path, required=True)
    ap.add_argument("--ref", required=True)
    ap.add_argument("--png", type=Path)
    ap.add_argument("--family", action="store_true",
                    help="rank all refs vs anchor, emit hull target")
    ap.add_argument("--out", type=Path,
                    help="write hull target spec (canon/pig_family.json)")
    a = ap.parse_args()
    man = json.loads(a.refs.read_text())
    if a.family:
        rep = family(man, a.ref)
        if a.out:
            a.out.write_text(json.dumps({
                "subject": man.get("subject"),
                "hull_target": rep["hull"],
                "family": rep["family"],
                "anchor": rep["anchor"]}, indent=1))
        print(json.dumps(rep, indent=1))
        return 0
    ref = next(r for r in man["refs"] if r["id"] == a.ref)
    print(json.dumps(score(a.png, ref), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

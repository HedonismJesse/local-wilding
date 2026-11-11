# provenance: author=devin; created=2026-11-10; source=plan
#   ai-hub Artifacts/plans/repo/ART_SPHERE_CHILD_SPHERES_2026-11-10.md
#   (art:media-producer oracle); purpose=silhouette+shape resemblance
#   vs anchor mask - replaces the zone-color false oracle;
#   intent=production
"""resemblance — the real similarity oracle.

ref_match measured color coverage in zones (presence) and passed a
1.00 on a candidate the operator read as non-waddles. Resemblance =
SHAPE: silhouette IoU against the anchor's own mask (normalized to a
common square) + per-part position/shape (centroid + coverage of the
anchor's part zones transferred onto the candidate's subject bbox).

score = 0.6 * silhouette_iou + 0.4 * part_score (weighted coverage
+ centroid proximity per part).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

N = 256


NON_PIG = [(223, 244, 238), (185, 228, 216)]   # wing mint shades -
# attachments don't count toward the pig's silhouette score


def _mask(png: Path) -> np.ndarray:
    a = np.asarray(Image.open(png).convert("RGBA")).astype(np.int16)
    m = a[..., 3] > 40
    if m.mean() > 0.95:
        # opaque bg - treat the dominant border color as background
        # (works for dark-navy review frames and white scans alike)
        b = np.concatenate([a[0, :, :3], a[-1, :, :3],
                            a[:, 0, :3], a[:, -1, :3]])
        bg = np.median(b, axis=0)
        m = np.abs(a[..., :3] - bg).sum(-1) > 60
    for nc in NON_PIG:                      # exclude attached props
        m &= np.abs(a[..., :3] - np.array(nc)).sum(-1) > 60
    if not m.any():
        return m
    ys, xs = np.where(m)
    return m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def pig_mask(png: Path) -> np.ndarray:
    """Subject mask with attached props (wings) removed - the wing
    region is defined by color proximity to the wing palette,
    dilated to catch antialiased edges. Attachments don't count
    toward the pig's silhouette score."""
    from skimage.morphology import dilation, disk
    a = np.asarray(Image.open(png).convert("RGBA")).astype(np.int16)
    m = a[..., 3] > 40
    if m.mean() > 0.95:
        b = np.concatenate([a[0, :, :3], a[-1, :, :3],
                            a[:, 0, :3], a[:, -1, :3]])
        bg = np.median(b, axis=0)
        m = np.abs(a[..., :3] - bg).sum(-1) > 60
    # wing mint is GREEN-dominant; the pig is R-dominant - distance
    # thresholds mix them (pink sits ~122 from mint), hue sign doesn't
    wing = (a[..., 1] > a[..., 0] + 15) & (a[..., 1] > a[..., 2] - 10)
    m &= ~dilation(wing, disk(8))
    if not m.any():
        return m
    ys, xs = np.where(m)
    return m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def _norm(m: np.ndarray) -> np.ndarray:
    """Pad to square, resize to NxN — aspect preserved inside the
    square so IoU compares silhouette SHAPE not bbox aspect."""
    h, w = m.shape
    s = max(h, w)
    pad = np.zeros((s, s), dtype=np.uint8)
    y, x = (s - h) // 2, (s - w) // 2
    pad[y:y + h, x:x + w] = m
    im = Image.fromarray(pad * 255).resize((N, N), Image.BOX)
    return np.asarray(im) > 128


def silhouette_iou(ref_m: np.ndarray, cand_m: np.ndarray) -> float:
    a, b = _norm(ref_m), _norm(cand_m)
    inter = (a & b).sum(); union = (a | b).sum()
    return float(inter / max(union, 1))


def part_score(ref: dict, ref_m: np.ndarray, cand_m: np.ndarray) -> dict:
    """Per-part: candidate's mask coverage inside the ref's part zone
    vs the ref's OWN occupancy in that zone (too empty OR too full
    both miss)."""
    h, w = cand_m.shape
    rh, rw = ref_m.shape
    total_w = sc = 0.0; parts = {}
    for name, p in (ref.get("parts") or {}).items():
        wt = float(p.get("weight", 1.0)); total_w += wt
        y0, x0, y1, x1 = p["bbox_frac"]
        z = cand_m[int(y0 * h):max(int(y1 * h), int(y0 * h) + 1),
                   int(x0 * w):max(int(x1 * w), int(x0 * w) + 1)]
        cov = z.mean() if z.size else 0.0
        rz = ref_m[int(y0 * rh):max(int(y1 * rh), int(y0 * rh) + 1),
                   int(x0 * rw):max(int(x1 * rw), int(x0 * rw) + 1)]
        target = float(p.get("occupancy",
                             rz.mean() if rz.size else 0.5))
        s_part = max(0.0, 1.0 - abs(cov - target) / max(target, 1e-6))
        parts[name] = {"coverage": round(float(cov), 3),
                       "score": round(s_part, 3)}
        sc += s_part * wt
    return {"score": round(sc / total_w, 3) if total_w else 0.0,
            "parts": parts}


def score(ref_png: Path, ref: dict, cand_png: Path) -> dict:
    rm = _mask(ref_png); cm = pig_mask(cand_png)
    iou = silhouette_iou(rm, cm)
    ps = part_score(ref, rm, cm)
    return {"iou": round(iou, 3), "part": ps,
            "score": round(0.6 * iou + 0.4 * ps["score"], 3)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref-png", type=Path, required=True)
    ap.add_argument("--refs", type=Path, required=True)
    ap.add_argument("--ref", required=True)
    ap.add_argument("--png", type=Path, required=True)
    a = ap.parse_args()
    man = json.loads(a.refs.read_text())
    ref = next(r for r in man["refs"] if r["id"] == a.ref)
    print(json.dumps(score(a.ref_png, ref, a.png), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

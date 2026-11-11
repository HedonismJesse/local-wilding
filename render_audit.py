# provenance: author=devin; created=2026-11-10; source=plan
#   ai-hub Artifacts/plans/repo/ART_SPHERE_CHILD_SPHERES_2026-11-10.md
#   (art:render-audit child sphere);
#   purpose=frame -> JSON feature report + hard flags so "it renders"
#   stops passing for "it reads"; intent=production
"""render_audit — mechanical read-signatures for raster frames.

The model can verify a render exists; this checks whether it reads.
Six failure modes from the 2026-11-10 mascot session were all caught
by operator eyeball; each has a cheap signature:

    oversized subject      bbox extent > cap, scenes
                           only (transparent-canvas
                           assets legitimately fill
                           the frame)                (40%-of-frame pig)
    exploded streak        component aspect >> 1     (tail streak)
    spiked/pennant part    solidity < bound          (pennant wings)
    text occlusion         foreign pixels inside the
                           text-line bbox            (ASCII box on title)
    illegible at scale     interior features merge
                           after downsample          ("66" eyes)
    merged blob            component count < spec    (needs --spec)

Seed vocabulary absorbed from games/delve frame_audit (squint, palette
entropy, clipping, flat-fill — pure PIL+numpy, ported with credit).
Spec-relative checks (silhouette-vs-spec, named-region solidity) take
a canon spec JSON via --spec; everything else is standalone.

Usage:
    python render_audit.py <frame.png|dir> [--spec canon/pig.json]
        [--target-w 320] [--out report.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

THUMB = 16
DEFAULTS = {
    "coverage_max": 0.35,       # subject fraction of frame
    "streak_aspect_min": 4.0,   # major/minor axis = exploded streak
    "streak_area_min": 0.003,   # ignore dust-sized components
    "solidity_min": 0.55,       # spiked/pennant silhouette floor
    "solidity_area_min": 0.01,  # only flag meaningful parts
    "occlusion_frac_min": 0.08, # foreign pixels inside text bbox
    "textline_min_glyphs": 5,   # same-color components forming a line
    "target_w": 320,            # downsample readability target
    "detail_frac_min": 0.3,     # illegibility = detail-dense subject
    "outline_frac_min": 0.25,   # asset expects visible dark boundary
    "detail_floor_frac": 0.005, # absolute detail floor (kills speckle)
    "clip_frac_max": 0.05,
    "palette_entropy_max": 2.3,
    "focal_min_dev": 0.10,
    "flat_fill_max": 0.25,
}

# ---------------------------------------------------------------- masks


def _subject_mask(img: Image.Image) -> tuple[np.ndarray, bool]:
    """Subject pixels: alpha where present, else distance from the
    dominant corner color (flat-BG composite frames). Returns
    (mask, is_asset) — a transparent canvas means the image IS the
    asset, so size caps don't apply the way they do to scenes."""
    a = np.asarray(img.convert("RGBA"), dtype=np.float32)
    alpha = a[..., 3] / 255.0
    if alpha.min() < 0.95:
        return alpha > 0.5, True
    rgb = a[..., :3]
    corners = np.concatenate([rgb[:8, :8].reshape(-1, 3),
                              rgb[:8, -8:].reshape(-1, 3),
                              rgb[-8:, :8].reshape(-1, 3),
                              rgb[-8:, -8:].reshape(-1, 3)])
    bg = np.median(corners, axis=0)
    return (np.abs(rgb - bg).sum(axis=2) / 255.0) > 0.12, False


def _components(mask: np.ndarray):
    from skimage import measure
    lab = measure.label(mask)
    return [r for r in measure.regionprops(lab) if r.area >= 16]


def _color_components(img: Image.Image, mask: np.ndarray):
    """Group same-color runs: quantize to 16-level RGB and label per
    bucket — text glyphs and flat shapes each become components."""
    from skimage import measure
    rgb = np.asarray(img.convert("RGB"), dtype=np.uint8)
    q = (rgb.astype(np.int16) // 24)
    groups = []
    for key in np.unique(q[mask].reshape(-1, 3), axis=0):
        sub = mask & np.all(q == key, axis=2)
        for r in measure.regionprops(measure.label(sub)):
            if r.area >= 12:
                groups.append((tuple(int(v) for v in key), r))
    return groups


# ------------------------------------------------------- games metrics
# Ported from games/part_forge/frame_audit.py (PIL+numpy, same math).

def _lum(img: Image.Image) -> np.ndarray:
    a = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def squint_contrast(lum: np.ndarray) -> float:
    t = np.asarray(Image.fromarray((lum * 255).astype(np.uint8))
                   .resize((THUMB, THUMB), Image.BOX),
                   dtype=np.float32) / 255.0
    g = t.mean()
    return float(max(abs(t[i:i + 4, j:j + 4].mean() - g)
                     for i in range(0, THUMB, 4)
                     for j in range(0, THUMB, 4)))


def palette_entropy(img: Image.Image) -> float:
    hsv = np.asarray(img.convert("HSV"), dtype=np.float32) / 255.0
    h, s = hsv[..., 0], hsv[..., 1]
    m = s > 0.15
    if m.sum() < 100:
        return 0.0
    p = np.histogram(h[m], bins=36, range=(0, 1))[0]
    p = p[p > 0] / p.sum()
    return float(-(p * np.log(p)).sum())


def flat_fill_ratio(img: Image.Image) -> float:
    a = np.asarray(img.convert("RGB"), dtype=np.uint8)
    h, w = a.shape[:2]
    min_run = max(8, int(w * 0.4))
    flat = 0
    for y in range(h):
        row = a[y]
        same = np.all(row[1:] == row[:-1], axis=1)
        change = np.flatnonzero(~same)
        runs = np.diff(np.concatenate(([-1], change, [w - 1]))) - 1
        flat += int(runs[runs >= min_run].sum())
    return float(flat / (h * w))


# ------------------------------------------------------- new signatures

def _streak(regions, frame_area):
    """Long thin component = exploded-streak class (tail streak)."""
    out = []
    for r in regions:
        minor = max(r.minor_axis_length, 1e-6)
        aspect = r.major_axis_length / minor
        frac = r.area / frame_area
        if aspect >= DEFAULTS["streak_aspect_min"] and \
                frac >= DEFAULTS["streak_area_min"]:
            out.append({"bbox": list(r.bbox), "aspect": round(aspect, 1),
                        "area_frac": round(frac, 4)})
    return out


def _spiky(regions, frame_area):
    out = []
    for r in regions:
        frac = r.area / frame_area
        if frac >= DEFAULTS["solidity_area_min"] and \
                r.solidity < DEFAULTS["solidity_min"]:
            out.append({"bbox": list(r.bbox),
                        "solidity": round(r.solidity, 3),
                        "area_frac": round(frac, 4)})
    return out


def _classify_glyphs(groups):
    """Same-color components chained by y-overlap into clusters, then
    classified. Returns (lines, frags, art):
      lines — wide, many-glyph clusters = real text lines
      frags — >=3-glyph chains too short/narrow to be lines; an
              occluded title's surviving pieces are frags, and they
              are still occlusion VICTIMS (heavy occlusion is exactly
              what breaks a line into frags)
      art   — >=5 lines stacked at pitch over a shared x-range =
              ASCII/ANSI art block (monospace rows pass every
              per-line test; only the block shape betrays them)
    """
    by_color: dict[tuple, list] = {}
    for key, r in groups:
        by_color.setdefault(key, []).append(r)
    cand = []
    for regs in by_color.values():
        if len(regs) < 3:
            continue
        parent = list(range(len(regs)))

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        def union(i, j):
            parent[find(i)] = find(j)

        for i in range(len(regs)):
            ri = regs[i]
            hi = ri.bbox[2] - ri.bbox[0]
            for j in range(i + 1, len(regs)):
                rj = regs[j]
                hj = rj.bbox[2] - rj.bbox[0]
                ov = (min(ri.bbox[2], rj.bbox[2]) -
                      max(ri.bbox[0], rj.bbox[0]))
                if ov < 0.5 * min(hi, hj):
                    continue
                gx = max(ri.bbox[1], rj.bbox[3]) - \
                    min(ri.bbox[3], rj.bbox[1])
                if gx <= 2 * max(hi, hj):
                    union(i, j)
        clusters: dict[int, list] = {}
        for i in range(len(regs)):
            clusters.setdefault(find(i), []).append(regs[i])
        for cl in clusters.values():
            if len(cl) < 3:
                continue
            m0 = min(r.bbox[0] for r in cl)
            n0 = min(r.bbox[1] for r in cl)
            m1 = max(r.bbox[2] for r in cl)
            n1 = max(r.bbox[3] for r in cl)
            aspect = (n1 - n0) / max(m1 - m0, 1)
            # text baselines are level — a tilted chain (the pig's
            # wing feathers at ~30 deg) is decoration, not a victim
            cy = np.array([r.centroid[0] for r in cl])
            cx = np.array([r.centroid[1] for r in cl])
            slope = abs(np.polyfit(cx, cy, 1)[0]) \
                if np.ptp(cx) > 0 else 99.0
            if slope > 0.15:
                continue
            entry = (key, m0, n0, m1, n1, {id(r) for r in cl})
            if len(cl) >= DEFAULTS["textline_min_glyphs"] and \
                    aspect > 4.0:
                cand.append(("line", entry))
            elif len(cl) >= 3 and aspect > 1.5:
                cand.append(("frag", entry))
    lines = [e for kind, e in cand if kind == "line"]
    frags = [e for kind, e in cand if kind == "frag"]
    stacked = set()
    for i, (_k, am0, an0, am1, an1, _a) in enumerate(lines):
        stack = [j for j, (_k2, bm0, bn0, bm1, bn1, _b)
                 in enumerate(lines)
                 if i != j and bn0 >= am0 and bn0 <= am1 + 30 and
                 min(an1, bn1) - max(an0, bn0) > 0.5 *
                 min(an1 - an0, bn1 - bn0)]
        if len(stack) >= 4:
            stacked.add(i)
            stacked.update(stack)
    art = [(m0, n0, m1, n1) for i, (_k, m0, n0, m1, n1, _a)
           in enumerate(lines) if i in stacked]
    lines = [ln for i, ln in enumerate(lines) if i not in stacked]
    return lines, frags, art


def _region_mask(regions_ids, groups, shape):
    m = np.zeros(shape, dtype=bool)
    for key, r in groups:
        if id(r) in regions_ids:
            m[r.bbox[0]:r.bbox[2], r.bbox[1]:r.bbox[3]] |= r.image
    return m


def _occlusion(groups, mask):
    """Foreign pixels covering real text glyphs = occlusion (the
    ASCII box over 'local-wilding' case). Victims include frags —
    the occluded title's surviving pieces — because heavy occlusion
    is exactly what breaks a line into frags."""
    from skimage.morphology import binary_dilation, disk
    from skimage import measure
    lines, frags, art = _classify_glyphs(groups)
    victims = lines + frags
    # a glyph-chain that is mostly inside the subject's own largest
    # component is decoration (wing feathers, ear tips), not text —
    # the pig's body then "occludes" its own wing = false positive
    lab = measure.label(mask)
    counts = np.bincount(lab.ravel())
    counts[0] = 0
    biggest = int(counts.argmax()) if counts.size else 0
    kept = []
    for v in victims:
        vm = _region_mask(v[-1], groups, mask.shape)
        on_big = float((vm & (lab == biggest)).sum()) / \
            max(float(vm.sum()), 1.0)
        if on_big <= 0.7:
            kept.append(v)
    victims = kept
    text_any = np.zeros(mask.shape, dtype=bool)
    for *_, ids in victims:
        text_any |= _region_mask(ids, groups, mask.shape)
    text_zone = binary_dilation(text_any, disk(2))
    foreign_mask = np.zeros(mask.shape, dtype=bool)
    for key, r in groups:
        if r.area < 16:           # occluders are real components,
            continue              # not anti-alias dust
        cm = np.zeros(mask.shape, dtype=bool)
        cm[r.bbox[0]:r.bbox[2], r.bbox[1]:r.bbox[3]] = r.image
        foreign_mask |= cm & ~text_zone
    hits = []
    for _key, m0, n0, m1, n1, ids in victims:
        text_mask = _region_mask(ids, groups, mask.shape)
        covered = 0
        total_foreign = 0
        for key, r in groups:
            if id(r) not in ids:
                continue
            gm = np.zeros(mask.shape, dtype=bool)
            gm[r.bbox[0]:r.bbox[2], r.bbox[1]:r.bbox[3]] = r.image
            gnear = binary_dilation(gm, disk(4))
            ov = int((foreign_mask & gnear).sum())
            total_foreign += ov
            if ov >= 0.2 * r.area:
                covered += 1
        frac = total_foreign / max(int(text_mask.sum()), 1)
        if covered >= 2:
            hits.append({"text_bbox": [m0, n0, m1, n1],
                         "glyphs_covered": covered,
                         "glyph_coverage": round(frac, 3)})
    # collinear split: two same-color clusters in one y-band with
    # foreign mass in the gap — the occluder ATE the middle glyphs
    # (covered letters leave no pixels for per-glyph coverage to
    # find; the gap content is the signature)
    for i, (ka, am0, an0, am1, an1, _a) in enumerate(victims):
        for _kb, bm0, bn0, bm1, bn1, _b in victims[i + 1:]:
            if _kb != ka or bn0 <= an0 or len(_a) + len(_b) < 8:
                continue
            gt, gb = max(am0, bm0), min(am1, bm1)
            if gb - gt < 8 or \
                    gb - gt < 0.4 * min(am1 - am0, bm1 - bm0):
                continue
            gap_w = bn0 - an1
            if gap_w < 4 or gap_w > 300:
                continue
            gap = mask[gt:gb, an1:bn0] & foreign_mask[gt:gb, an1:bn0]
            if gap.sum() >= max(60, 0.005 * gap.size):
                hits.append({"text_bbox": [am0, an0, am1, bn1],
                             "split_gap_px": int(gap_w),
                             "gap_fill": round(float(gap.sum()) /
                                               gap.size, 3)})
    return hits


def _detail_density(regions, mask, text_any, frame_area):
    """Fraction of non-text subject pixels living in small components.
    Detail-dense subjects (ASCII glyph art, texture strokes) are the
    illegible-at-scale class: at target size the strokes merge into
    mush. Text-line pixels excluded — caption legibility is a
    different failure. Requires an absolute detail floor so sparse
    speckle can't trip it."""
    small_floor = max(40.0, 0.0005 * frame_area)
    nontext = int((mask & ~text_any).sum())
    detail = 0
    for r in regions:
        if r.area < small_floor:
            cm = np.zeros(mask.shape, dtype=bool)
            cm[r.bbox[0]:r.bbox[2], r.bbox[1]:r.bbox[3]] = r.image
            detail += int((cm & mask & ~text_any).sum())
    frac = detail / max(nontext, 1)
    return {"detail_frac": round(frac, 3),
            "detail_px": detail,
            "nontext_px": nontext,
            "dense": (frac > DEFAULTS["detail_frac_min"] and
                      detail > DEFAULTS["detail_floor_frac"] * frame_area)}


def _outline_strength(img, mask):
    """Dark-pixel fraction on the subject's boundary band — the
    register probe: a waddles-register cartoon is a LINE drawing
    (dark stroke binding silhouette + features); flat outline-less
    collages score ~0 (the storyboard_w2_v1 rejection class)."""
    from skimage.morphology import binary_erosion, disk
    er = binary_erosion(mask, disk(2))
    boundary = mask & ~er
    if not boundary.any():
        return 0.0
    return float((_lum(img) < 0.35)[boundary].mean())


def _downsample_survival(img, mask):
    """Component count at full res vs after resize to target width —
    informational metric backing the detail-density flag."""
    w = DEFAULTS["target_w"]
    if img.size[0] <= w:
        return None
    small = np.asarray(Image.fromarray(mask.astype(np.uint8) * 255)
                       .resize((w, int(img.size[1] * w / img.size[0])),
                               Image.BOX)) > 128
    full = len([r for r in _components(mask) if r.area >= 40])
    shrunk = len(_components(small))
    return {"components_full": full, "components_target": shrunk,
            "survival": round(shrunk / max(full, 1), 3)}


def _spec_checks(mask, regions, groups, spec):
    """Canon-spec relative checks (art:construction-canon row). Regions
    are fractions of the SUBJECT bbox so they survive scale changes.
    The blob lesson: a merged pig is not fewer mask components — it is
    fewer interior features, so spec checks look at color-key diversity
    and named-region solidity, not raw component counts."""
    from skimage import measure
    ys, xs = np.where(mask)
    if not len(ys):
        return {}, []
    sb = (ys.min(), xs.min(), ys.max(), xs.max())
    sh, sw = sb[2] - sb[0], sb[3] - sb[1]
    # dominant body key = key of the largest group — interior-feature
    # checks count keys OTHER than body fill
    dom_key = max(groups, key=lambda kr: kr[1].area)[0] if groups else None
    detail, votes, flags = {}, {}, []
    detail["_subject"] = {"aspect": round(sw / max(sh, 1), 3)}
    if spec.get("subject_aspect_min") and \
            sw / max(sh, 1) < spec["subject_aspect_min"]:
        flags.append(spec.get("aspect_named_failure",
                              "thin_subject") + "_vs_spec")
    for name, rs in spec.get("regions", {}).items():
        f = rs["bbox_frac"]
        z0, z1 = sb[0] + int(f[0] * sh), sb[0] + int(f[2] * sh)
        c0, c1 = sb[1] + int(f[1] * sw), sb[1] + int(f[3] * sw)
        zone = [r for k, r in groups
                if z0 <= (r.bbox[0] + r.bbox[2]) / 2 < z1 and
                c0 <= (r.bbox[1] + r.bbox[3]) / 2 < c1]
        keys = {k for k, r in groups
                if k != dom_key and
                rs.get("min_key_area_px", 0) <= r.area <=
                rs.get("max_key_area_px", 8000)
                and z0 <= (r.bbox[0] + r.bbox[2]) / 2 < z1 and
                c0 <= (r.bbox[1] + r.bbox[3]) / 2 < c1}
        # mid-tone = non-body key with all channels >=3 AND hue-
        # distinct from body fill — dark dots (nostril specks) and
        # one-channel-off body shades don't count as features
        nd = rs.get("exclude_near_dom_dist", 3)
        midtone = {k for k in keys if min(k) >= 3 and dom_key and
                   sum(abs(k[i] - dom_key[i]) for i in range(3)) > nd}
        zmask = mask[z0:z1, c0:c1]
        sol = max((r.solidity for r in measure.regionprops(
                      measure.label(zmask))), default=1.0) \
            if zmask.size else 1.0
        failure = rs.get("named_failure", name)
        rec = {"zone": [int(z0), int(c0), int(z1), int(c1)],
               "components": len(zone),
               "distinct_keys": len(keys), "midtone_keys": len(midtone),
               "solidity": round(float(sol), 3)}
        failed = (
            ("min_components" in rs and
             len(zone) < rs["min_components"]) or
            ("min_distinct_color_keys" in rs and
             len(keys) < rs["min_distinct_color_keys"]) or
            ("min_midtone_keys" in rs and
             len(midtone) < rs["min_midtone_keys"]) or
            ("min_solidity" in rs and sol < rs["min_solidity"]))
        votes.setdefault(failure, []).append(failed)
        detail[name] = rec
    # regions sharing a named_failure OR together (facing-agnostic
    # left/right zones): the failure fires only when EVERY zone misses
    for failure, fails in votes.items():
        if all(fails):
            flags.append(f"{failure}_vs_spec")
    return detail, flags


# ---------------------------------------------------------------- audit

def audit_frame(path: Path, spec: dict | None = None,
                cfg: dict | None = None) -> dict:
    cfg = {**DEFAULTS, **(cfg or {}), **(spec or {})}
    img = Image.open(path)
    mask, is_asset = _subject_mask(img)
    frame_area = mask.size
    regions = _components(mask)
    lum = _lum(img)
    cb = float((lum < 8 / 255).mean()); cw = float((lum > 247 / 255).mean())

    big = max(regions, key=lambda r: r.area, default=None)
    largest = (big.area / frame_area) if big else 0.0
    bbox_frac = (((big.bbox[2] - big.bbox[0]) *
                  (big.bbox[3] - big.bbox[1])) / frame_area) if big else 0.0
    metrics = {
        "subject_coverage": round(float(mask.mean()), 4),
        "largest_component": round(float(largest), 4),
        "largest_bbox_frac": round(float(bbox_frac), 4),
        "components": len(regions),
        "bboxes": [list(r.bbox) for r in
                   sorted(regions, key=lambda r: -r.area)[:8]],
        "squint": squint_contrast(lum),
        "palette": palette_entropy(img),
        "clip_black": cb, "clip_white": cw,
        "flat_fill": flat_fill_ratio(img),
        "outline_frac": round(_outline_strength(img, mask), 3),
    }
    groups = _color_components(img, mask)
    streaks = _streak(regions, frame_area)
    spiky = _spiky(regions, frame_area)
    occl = _occlusion(groups, mask)
    # only confident lines are text-excluded from detail; frags stay
    # in the subject pool (could be occluded text OR art rows)
    text_any = np.zeros(mask.shape, dtype=bool)
    for *_, ids in _classify_glyphs(groups)[0]:
        text_any |= _region_mask(ids, groups, mask.shape)
    detail = _detail_density(regions, mask, text_any, frame_area)
    scale = _downsample_survival(img, mask & ~text_any)
    spec_detail, spec_flags = ({}, []) if not spec else \
        _spec_checks(mask, regions, groups, spec)

    flags = []
    if not is_asset and bbox_frac > cfg["coverage_max"]:
        flags.append("subject_oversized")
    if streaks:
        flags.append("streak_component")
    if spiky:
        flags.append("low_solidity_component")
    if occl:
        flags.append("occludes_text")
    if detail["dense"]:
        flags.append("illegible_at_scale")
    if metrics["squint"] < cfg["focal_min_dev"]:
        flags.append("flat_composition")
    if metrics["palette"] > cfg["palette_entropy_max"]:
        flags.append("palette_sprawl")
    if cb > cfg["clip_frac_max"]:
        flags.append("crushed_blacks")
    if cw > cfg["clip_frac_max"]:
        flags.append("blown_whites")
    if metrics["flat_fill"] > cfg["flat_fill_max"]:
        flags.append("flat_fill_regions")
    if is_asset and metrics["outline_frac"] < \
            cfg["outline_frac_min"]:
        flags.append("weak_outline")
    if spec and spec.get("min_components") and \
            len(regions) < spec["min_components"]:
        flags.append("merged_blob_vs_spec")
    flags.extend(spec_flags)

    return {"file": str(path), "metrics": metrics, "flags": flags,
            "streaks": streaks, "spiky": spiky,
            "occlusions": occl, "detail": detail, "scale": scale,
            "spec": spec_detail}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("frames", type=Path, help="png file or dir")
    ap.add_argument("--spec", type=Path, default=None,
                    help="canon spec JSON (bounds + min_components)")
    ap.add_argument("--target-w", type=int, default=None)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    cfg = dict(DEFAULTS)
    if a.target_w:
        cfg["target_w"] = a.target_w
    spec = json.loads(a.spec.read_text()) if a.spec else None
    files = ([a.frames] if a.frames.is_file()
             else sorted(a.frames.glob("*.png")))
    rows = [audit_frame(f, spec, cfg) for f in files]
    rep = {"frames": len(rows),
           "flagged": sum(bool(r["flags"]) for r in rows),
           "by_flag": {fl: [Path(r["file"]).name for r in rows
                            if fl in r["flags"]]
                       for fl in {f for r in rows for f in r["flags"]}},
           "rows": rows}
    print(json.dumps({k: v for k, v in rep.items() if k != "rows"},
                     indent=1))
    if a.out:
        a.out.write_text(json.dumps(rep, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

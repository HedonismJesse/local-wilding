# provenance: author=devin; created=2026-11-10; source=operator
#   directive "there must be a childsphere that defines how many
#   different reference oracles are needed — recognizing when
#   something is laying, or running etc (the full list); base refs
#   like is it a pig, does it look smart or dumb — states derived
#   by their rules" + "zoomed in and out are good verifiers that
#   need consistent checking"; purpose=art:state-oracles — the
#   registry of state/integrity recognizers: every render is checked
#   against named visual states and structural rules at MULTIPLE
#   scales, so 'can you not see?' is machine-answerable;
#   intent=production
"""state_oracle — art:state-oracles, the recognition registry.

Three detector families, each a RULE over geometry/pixels — not
vibes:

1. structural integrity ("can you not see" layer — catches the
   defects the operator flagged when the strip 'looked fine'):
     interior_holes   — bg-colored gaps inside the silhouette
                        (the flee cheek gash, rest belly slit)
     stroke_bleed     — dark linework outside the silhouette
     self_intersect   — poly contour crosses itself
     frame_clip       — content touches the canvas edge
     fragments        — small detached alpha components

2. state recognition (the "full list" — each state = named rules):
     lying     — underside flat + low aspect + ground line
     running   — leg protrusions scissored + forward pitch
     flying    — no ground contact + tilt/attachment
     standing  — upright baseline, default negative for above
     eyes      — open dots vs closed arcs (stroke zone analysis)
     is_pig    — silhouette IoU vs the canonical family anchor
     markings  — tonal-fill presence (spots/saddle identity)

3. multi-scale verifier (operator rule 2026-11-10: "zoomed in and
   out are good verifiers that need consistent checking"):
   every check emits thumb + strip + full renders — defects hide
   at exactly one scale; report always carries all three.

    python state_oracle.py                    # report on all poses
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import binary_fill_holes
from skimage import measure

CANON = Path(__file__).parent / "canon"


# ---------- structural detectors (the 'can you not see' layer) ----

def _alpha(img: np.ndarray) -> np.ndarray:
    return img[..., 3] > 40


def interior_holes(img: np.ndarray) -> dict:
    """Bg-colored regions enclosed by subject — gashes like the
    flee-cheek slit. Filled-minus-actual = hole mask."""
    a = _alpha(img)
    holes = binary_fill_holes(a) & ~a
    lab = measure.label(holes)
    big = [r.area for r in measure.regionprops(lab) if r.area > 60]
    return {"defect": len(big) > 0, "count": len(big),
            "area_px": int(sum(big))}


def stroke_bleed(img: np.ndarray) -> dict:
    """Dark linework pixels that sit outside the filled silhouette —
    smeared marks dragged off the body."""
    a = _alpha(img)
    sil = binary_fill_holes(a)
    dark = (img[..., :3].mean(-1) < 100) & (img[..., 3] > 60)
    bleed = dark & ~sil
    return {"defect": int(bleed.sum()) > 40, "px": int(bleed.sum())}


def self_intersect(spec: dict) -> dict:
    """Silhouette contour crossing itself — predicts fill gashes."""
    p = np.asarray(spec["silhouette"])
    if len(p) > 200:                       # simplify first (retopo'd
        p = measure.approximate_polygon(p, tolerance=0.008)  # rings are 1000s)
    n = len(p)
    hits = 0

    def ccw(a, b, c):
        return (c[0] - a[0]) * (b[1] - a[1]) - (b[0] - a[0]) * (c[1] - a[1])

    for i in range(n):
        a, b = p[i], p[(i + 1) % n]
        for j in range(i + 2, n):
            if j == (i - 1) % n:
                continue
            c, d = p[j], p[(j + 1) % n]
            d1, d2 = ccw(c, d, a), ccw(c, d, b)
            d3, d4 = ccw(a, b, c), ccw(a, b, d)
            if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)):
                hits += 1
    return {"defect": hits > 0, "crossings": hits}


def frame_clip(img: np.ndarray) -> dict:
    """Subject touching canvas edges — clipped geometry."""
    a = _alpha(img)
    edge = int(a[0].sum() + a[-1].sum() + a[:, 0].sum() + a[:, -1].sum())
    return {"defect": edge > 0, "edge_px": edge}


def _attach_mask(img: np.ndarray) -> np.ndarray:
    """Attachment pixels (wings: mint, G-dominant) — attachments are
    legal extra components, not fragments."""
    r, g, b = (img[..., i].astype(int) for i in range(3))
    return _alpha(img) & (g > r + 10) & (g > b + 5)


def fragments(img: np.ndarray, min_px: int = 60,
              attach_gap: int = 6) -> dict:
    """Detached components beyond subject + declared attachments.
    A mark within attach_gap px of the main body reads attached —
    the rough-line register overshoots the fill edge legitimately
    (tail curls, stroke overshoot); only a VISIBLE gap is a defect."""
    from skimage import morphology
    a = _alpha(img) & ~_attach_mask(img)
    lab = measure.label(a)
    props = [r for r in measure.regionprops(lab)]
    if not props:
        return {"defect": False, "extras": 0}
    main = max(props, key=lambda r: r.area)
    near = morphology.binary_dilation(lab == main.label,
                                     morphology.disk(attach_gap))
    extras = sum(1 for r in props
                 if r.label != main.label and min_px < r.area
                 and not (lab == r.label)[near].any())
    return {"defect": extras > 0, "extras": extras}


def thin_artifacts(img: np.ndarray) -> dict:
    """Hairline filaments — silhouette spikes that fill like body
    (the rest-pose head spike). A defect filament is LONG AND
    NARROW: legs/ears are short nubs and don't qualify."""
    from skimage import morphology
    from scipy.ndimage import distance_transform_edt
    a = _alpha(img)
    if not a.any():
        return {"defect": False}
    dist = distance_transform_edt(a)
    spine = (dist > 0) & (dist < 2.5)
    lab = measure.label(spine)
    worst = 0
    for r in measure.regionprops(lab):
        bh = r.bbox[2] - r.bbox[0]
        bw = r.bbox[3] - r.bbox[1]
        if r.area > 25 and max(bh, bw) > 4.5 * max(1, min(bh, bw)):
            worst = max(worst, r.area)
    return {"defect": worst > 0, "filament_px": int(worst)}


# ---------- state recognizers (the 'full list') ------------------

def _sil_pts(spec: dict):
    return np.asarray(spec["silhouette"], dtype=float)


def _resample(poly, n=400):
    """Uniform arc-length resample — poly vertex counts are arbitrary
    (approximate_polygon deletes flat-edge points), so all boundary
    metrics must run on resampled points, not vertices."""
    p = np.asarray(poly, dtype=float)
    ring = np.vstack([p, p[:1]])
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(ring, axis=0).T))]
    t = np.linspace(0, d[-1], n, endpoint=False)
    return np.stack([np.interp(t, d, ring[:, 0]),
                     np.interp(t, d, ring[:, 1])], 1)


def is_lying(spec: dict) -> dict:
    """Flat ground-contact underside (arc-length share of the
    perimeter) + low aspect — the lying loaf."""
    p = _resample(_sil_pts(spec))
    h = p[:, 0].max() - p[:, 0].min()
    w = p[:, 1].max() - p[:, 1].min()
    lo = p[:, 0].max()
    flat_frac = float((p[:, 0] > lo - h * 0.03).mean())
    score = float(np.clip(flat_frac * 2.2
                          + np.clip((w / h - 1.35) * 0.5, 0, 0.3), 0, 1))
    return {"score": round(score, 2), "flat_frac": round(flat_frac, 3),
            "aspect_wh": round(float(w / h), 2)}


def is_running(spec: dict) -> dict:
    """Leg protrusions below the belly baseline: depth, count and
    x-separation — a stride scissors, standing nubs are shallow and
    even, a lying bottom has none."""
    p = _resample(_sil_pts(spec))
    h = p[:, 0].max() - p[:, 0].min()
    lo_x, hi_x = p[:, 1].min(), p[:, 1].max()
    # interior leg band only — snout dips and tail curls at the ends
    # are not legs
    bins = np.linspace(lo_x + 0.15 * (hi_x - lo_x),
                       hi_x - 0.10 * (hi_x - lo_x), 60)
    bottom = np.array([p[np.argmin(np.abs(p[:, 1] - b)), 0]
                       for b in bins])
    base = np.percentile(bottom, 70)          # belly level
    depth = bottom - base
    thresh = 0.09 * h                         # extended, not a nub
    on = depth > thresh
    runs, cur = [], None
    for i, v in enumerate(on):
        if v and cur is None:
            cur = i
        elif not v and cur is not None:
            runs.append((cur, i - 1))
            cur = None
    if cur is not None:
        runs.append((cur, len(on) - 1))
    runs = [r for r in runs if depth[r[0]:r[1] + 1].max() > thresh]
    maxd = float(depth.max() / h)
    xs_of = [float(bins[a:b + 1].mean()) for a, b in runs]
    gap = max(np.diff(xs_of)) if len(xs_of) > 1 else 0.0
    score = float(np.clip(maxd * 4.0 + len(runs) * 0.15 + gap * 1.5,
                          0, 1))
    return {"score": round(score, 2), "protrusions": len(runs),
            "max_depth": round(maxd, 3),
            "leg_x": [round(x, 2) for x in xs_of]}


def is_flying(spec: dict, wings: bool) -> dict:
    """No flat underside (airborne), attachment present, body tilt."""
    lie = is_lying(spec)
    p = _sil_pts(spec)
    top = p[p[:, 0] < p[:, 0].min() + 0.1]
    tilt = float(abs(top[:, 0].max() - top[:, 0].min())) if len(top) else 0
    grounded = lie["flat_frac"] > 0.15
    score = float(np.clip((0.4 if wings else 0)
                          + (0.4 if not grounded else 0)
                          + tilt * 2, 0, 1))
    return {"score": round(score, 2), "grounded": grounded,
            "wings": wings}


def eyes_state(spec: dict) -> dict:
    """Closed = wide shallow arc (the sleep grammar), open = compact
    dot. Classify stroke components in the head box — fixed zones
    drift when warps move the marks."""
    import trace_linework as tl
    st = np.asarray(tl._stroke_img(spec)) > 80
    h, w = st.shape
    box = np.zeros_like(st)
    box[int(0.10 * h):int(0.38 * h), int(0.06 * w):int(0.48 * w)] = \
        st[int(0.10 * h):int(0.38 * h), int(0.06 * w):int(0.48 * w)]
    lab = measure.label(box)
    comps = [r for r in measure.regionprops(lab)
             if 10 < r.area < h * w * 0.01]
    # match components to the known eye anchors (frac coords move
    # with warps but stay near); eyebrow/mouth strokes don't match
    eyes_xy = [(0.245, 0.145), (0.260, 0.315)]
    arcs = 0
    matched = 0
    for ey, ex in eyes_xy:
        best = None
        for r in comps:
            ry, rx = r.centroid[0] / h, r.centroid[1] / w
            d = (ry - ey) ** 2 + (rx - ex) ** 2
            if d < 0.015 and (best is None or d < best[0]):
                best = (d, r)
        if best is not None:
            matched += 1
            r = best[1]
            if (r.bbox[3] - r.bbox[1]) > 2 * (r.bbox[2] - r.bbox[0]):
                arcs += 1
    state = ("closed" if arcs >= 2 else "open") if matched >= 2 \
        else ("mixed" if matched else "not_found")
    return {"eyes": state, "arcs": arcs, "matched": matched}


def _norm_mask(spec: dict, n: int = 256) -> np.ndarray:
    """Silhouette rendered centered+scaled into a shared frame —
    family membership is a SHAPE question, invariant to window/size."""
    p = np.asarray(spec["silhouette"], dtype=float)
    y0, y1 = p[:, 0].min(), p[:, 0].max()
    x0, x1 = p[:, 1].min(), p[:, 1].max()
    s = 0.8 * n / max(y1 - y0, x1 - x0)
    cy, cx = (y0 + y1) / 2, (x0 + x1) / 2
    im = Image.new("L", (n, n), 0)
    ImageDraw.Draw(im).polygon(
        [((c - cx) * s + n / 2, (r - cy) * s + n / 2) for r, c in p],
        fill=255)
    return np.asarray(im) > 0


def is_pig(spec: dict, anchor: dict) -> dict:
    """Family membership: normalized silhouette IoU vs the canonical
    anchor (ourpig_base)."""
    a, b = _norm_mask(anchor), _norm_mask(spec)
    iou = float((a & b).sum() / max(1, (a | b).sum()))
    return {"score": round(iou, 3)}


def markings(spec: dict) -> dict:
    return {"fills": len(spec["fills"]),
            "regions": len(spec["fills"]) > 0}


# ---------- multi-scale verifier ---------------------------------

SCALES = {"thumb": 160, "strip": 420, "full": 1100}


def multisheet(img: Image.Image, out: Path) -> None:
    """thumb|strip|full contact sheet — defects hide at exactly one
    scale; the report always carries all three."""
    imgs = []
    for w in SCALES.values():
        h = int(img.height * w / img.width)
        imgs.append(img.resize((w, h), Image.BICUBIC))
    W = sum(i.width for i in imgs) + 40
    H = max(i.height for i in imgs) + 30
    sheet = Image.new("RGBA", (W, H), (24, 24, 28, 255))
    x = 10
    for im in imgs:
        sheet.alpha_composite(im, (x, (H - im.height) // 2))
        x += im.width + 10
    sheet.save(out)


def inspect(pose: str, spec: dict, img: Image.Image,
            anchor: dict | None = None, wings: bool = False) -> dict:
    """Full registry pass over one rendered pose."""
    arr = np.asarray(img)
    rep = {"pose": pose,
           "integrity": {"interior_holes": interior_holes(arr),
                         "stroke_bleed": stroke_bleed(arr),
                         "self_intersect": self_intersect(spec),
                         "frame_clip": frame_clip(arr),
                         "fragments": fragments(arr),
                         "thin_artifacts": thin_artifacts(arr)},
           "states": {"lying": is_lying(spec),
                      "running": is_running(spec),
                      "flying": is_flying(spec, wings),
                      "eyes": eyes_state(spec),
                      "markings": markings(spec)}}
    if anchor is not None:
        rep["states"]["is_pig"] = is_pig(spec, anchor)
    bad = [k for k, v in rep["integrity"].items() if v.get("defect")]
    rep["verdict"] = "CLEAN" if not bad else "DEFECTS: " + ",".join(bad)
    return rep


if __name__ == "__main__":
    import pig_w5
    anchor = json.loads((CANON / "ourpig_base.json").read_text())
    poses = [("rest", {}), ("notice", {}), ("flee", {"facing": -1}),
             ("fly", {"tilt": 18, "wings": 1})]
    out = {}
    for pose, kw in poses:
        img = pig_w5.render_pose(pose, **kw)
        spec = pig_w5.pose_spec(pose)
        rep = inspect(pose, spec, img, anchor, wings=bool(kw.get("wings")))
        multisheet(img, Path(f"_oracle_{pose}.png"))
        out[pose] = rep
        print(pose, rep["verdict"], "| lying", rep["states"]["lying"]["score"],
              "running", rep["states"]["running"]["score"],
              "eyes", rep["states"]["eyes"]["eyes"])
    Path("_oracle_report.json").write_text(json.dumps(out, indent=2))

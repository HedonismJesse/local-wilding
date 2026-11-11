# provenance: author=devin; created=2026-11-10; source=operator
#   directive "after we 1 to 1 the reference we need to make a
#   distinctly different picture (the original target) which becomes
#   the new reference"; purpose=derive OUR pig design from a verified
#   waddles trace — same register family, designed deltas;
#   intent=production
"""pig_derive — the derivation instrument (1/1 -> distinct).

Operator order (2026-11-10): the verified 1/1 copy is the substrate;
OUR character = the trace + designed deltas, and OUR render becomes
the new reference anchor. The pose sheet then maintains integrity
against our spec — resemblance is measured to ourselves.

Design ops (each documented, cumulative):

    belly_droop(a)  — bottom contour sags, centered mid-body
    jowl(a)         — lower-front contour pushed down/out (lazy chin)
    droopy_lids     — erase the ref's eye-dot strokes; draw half-lid
                      arcs above the eye positions (lazy eye grammar)
    respot(s,dx,dy) — transform the flank-spot fill polys
    ear_droop(a)    — extend the ear-flop silhouette bump

Mechanics: a shared displacement field warp applies to ALL layers at
once — silhouette poly, fill polys, AND the stroke bitmap (remap) —
so marks stay consistent with the body. Layer-specific edits (lids)
operate on the stroke bitmap + a custom-stroke list.

    python pig_derive.py --base canon/trace_profile.json \
        --ops belly_droop=0.07,jowl=0.04,droopy_lids \
        --out canon/ourpig_base.json
"""
import argparse
import base64
import io
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import map_coordinates

import trace_linework as tl

# eye positions on the model-sheet profile, (row, col) fracs of sil bbox
EYES = [(0.245, 0.145), (0.260, 0.315)]


def _field_grid(h: int, w: int, ops: list[dict]) -> tuple:
    """Displacement field (dy, dx) over normalized bbox coords."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    yy /= max(1, h - 1)                     # frac coords 0..1
    xx /= max(1, w - 1)
    dy = np.zeros((h, w), np.float32)
    dx = np.zeros((h, w), np.float32)
    for op in ops:
        if op["op"] == "belly_droop":
            a = float(op["a"])
            cx = np.clip((xx - 0.18) / 0.68, 0, 1)
            wgt = np.sin(np.pi * cx) ** 2
            gate = np.clip((yy - 0.60) / 0.30, 0, 1) ** 1.5
            dy += a * wgt * gate
        elif op["op"] == "jowl":
            a = float(op["a"])
            cx = np.clip((0.42 - xx) / 0.42, 0, 1)
            cy = np.clip((yy - 0.45) / 0.55, 0, 1)
            dy += a * cx * cy
            dx -= a * 0.35 * cx * cy
        elif op["op"] == "ear_droop":
            a = float(op["a"])
            cx = np.clip((0.30 - xx) / 0.30, 0, 1)
            cy = np.clip((0.45 - yy) / 0.45, 0, 1)
            dy += a * cx * cy
            dx -= a * 0.30 * cx * cy
        elif op["op"] == "squat":
            a = float(op["a"])        # top squishes DOWN (resting weight)
            dy += a * np.clip((0.80 - yy) / 0.80, 0, 1) ** 1.3
        elif op["op"] == "lean":
            a = float(op["a"])        # forward shear, stronger at top
            dx -= a * np.clip((0.85 - yy) / 0.85, 0, 1)
        elif op["op"] == "lie":
            # lying loaf (sleep-still grammar): legs TUCK — the whole
            # underside pulls up to a flat ground-contact line, top
            # compresses DOWN, body spreads slightly. a~1 = fully down.
            a = float(op["a"])
            line = float(op.get("line", 0.80))
            below = np.clip((yy - line) / max(1e-6, 1.0 - line), 0, 1)
            dy -= a * below * (1.0 - line)          # leg zone -> line
            dy += a * 0.22 * np.clip((line - yy) / line, 0, 1) ** 1.15
            dx += a * 0.06 * (xx - 0.5) * np.clip((0.9 - yy) / 0.9, 0, 1)
        elif op["op"] == "stride":
            # run grammar (walk still): legs scissor — front leg
            # reaches toward the head (-x), rear leg kicks back (+x),
            # both extend down; head dips; body pitches forward.
            a = float(op["a"])
            legzone = np.clip((yy - 0.68) / 0.32, 0, 1) ** 1.4
            front = np.exp(-(((xx - 0.30) / 0.11) ** 2))
            rear = np.exp(-(((xx - 0.72) / 0.11) ** 2))
            dy += a * 0.10 * legzone * (front + rear)
            dx -= a * 0.13 * legzone * front      # front leg reaches -x
            dx += a * 0.16 * legzone * rear       # rear leg kicks +x
            headw = np.clip((0.45 - xx) / 0.45, 0, 1) * \
                np.clip((0.55 - yy) / 0.55, 0, 1)
            dy += a * 0.03 * headw                # head dips slightly
        elif op["op"] == "pin_legs":
            # flying: legs tuck INTO the body — pull everything below
            # the tuck line fully up to it (no dangling nubs)
            a = float(op["a"])
            below = np.clip((yy - 0.82) / 0.18, 0, 1)
            dy -= a * below * (1.0 - 0.82)
    return dy, dx


def _warp_poly(poly: list, dy, dx) -> list:
    """poly in [y,x] fracs; field indexed at (h*w) frac coords."""
    h, w = dy.shape
    out = []
    for r, c in poly:
        ri, ci = r * (h - 1), c * (w - 1)
        fy = float(map_coordinates(dy, [[ri], [ci]], order=1)[0])
        fx = float(map_coordinates(dx, [[ri], [ci]], order=1)[0])
        out.append([round(float(r + fy), 4), round(float(c + fx), 4)])
    return out


def _warp_bitmap(img: np.ndarray, dy, dx) -> np.ndarray:
    """Remap a stroke bitmap (rows=y) by the field. img is 0/255."""
    h, w = img.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    fy = np.clip(yy / max(1, h - 1), 0, 1) * (dy.shape[0] - 1)
    fx = np.clip(xx / max(1, w - 1), 0, 1) * (dy.shape[1] - 1)
    shy = map_coordinates(dy, [fy, fx], order=1) * (h - 1)
    shx = map_coordinates(dx, [fy, fx], order=1) * (w - 1)
    coords = [yy - shy, xx - shx]
    return map_coordinates(img.astype(np.float32), coords, order=1)


def _retopo(spec: dict, ops: list[dict]) -> None:
    """Re-topologize the warped silhouette: rasterize -> close gaps ->
    fill holes -> re-extract ONE simple outer contour. Field warps
    fold the contour (self-intersection -> even-odd fill leaves white
    interior gashes, the flee-cheek defect); re-extraction yields a
    simple loop. `lie` then hard-clamps the underside to the ground
    line — guaranteed flat, no dangling stubs."""
    from scipy.ndimage import binary_fill_holes
    from skimage import measure, morphology
    allr = [p[0] for p in spec["silhouette"]]
    allc = [p[1] for p in spec["silhouette"]]
    y0, y1 = min(allr) - 0.06, max(allr) + 0.06
    x0, x1 = min(allc) - 0.06, max(allc) + 0.06
    W = 1400
    H = max(2, int(W * (y1 - y0) / max(1e-6, x1 - x0)))
    im = Image.new("L", (W, H), 0)
    ImageDraw.Draw(im).polygon(
        [((c - x0) / (x1 - x0) * W, (r - y0) / (y1 - y0) * H)
         for r, c in spec["silhouette"]], fill=255)
    m = np.asarray(im) > 0
    m = morphology.binary_closing(m, morphology.disk(6))
    m_closed = m.copy()                      # body as warped
    m = morphology.binary_opening(m, morphology.disk(3))  # shave filaments
    for f in spec["fills"]:                  # body-attached markings
        fm = Image.new("L", (W, H), 0)       # (tail curl) are sil
        ImageDraw.Draw(fm).polygon(          # geometry too — union
            [((c - x0) / (x1 - x0) * W, (r - y0) / (y1 - y0) * H)
             for r, c in f["poly"]], fill=255)
        fa = np.asarray(fm) > 0
        f["_inside"] = bool(fa.sum() and (fa & m_closed).sum() / fa.sum() > 0.3)
        if f["_inside"]:
            m |= fa                          # restores what opening shaved
    m = binary_fill_holes(m)
    m = morphology.remove_small_objects(m, 200)
    lab = measure.label(m)
    if lab.max() > 1:                        # keep largest component
        sizes = np.bincount(lab.ravel())
        sizes[0] = 0
        m = lab == sizes.argmax()
    cs = measure.find_contours(np.pad(m, 1).astype(float), 0.5)
    poly = tl._smooth(max(cs, key=len) - 1)
    poly = measure.approximate_polygon(poly, tolerance=2.0)
    spec["silhouette"] = [[round(y0 + r / H * (y1 - y0), 4),
                           round(x0 + c / W * (x1 - x0), 4)]
                          for r, c in poly]
    spec["fills"] = [f for f in spec["fills"] if f.pop("_inside")]
    for op in ops:                           # post-retopo clamps
        if op["op"] == "lie":
            line = float(op.get("line", 0.80))
            xs = [p[1] for p in spec["silhouette"]]
            xl, xh = min(xs), max(xs)
            spec["silhouette"] = [
                [line + 0.010 * np.sin(
                    np.pi * np.clip((p[1] - xl) / (xh - xl), 0, 1))
                 if p[0] > line else p[0], p[1]]
                for p in spec["silhouette"]]


def _clip_strokes(st: np.ndarray, sil: list) -> np.ndarray:
    """Zero stroke pixels outside the (re-topologized) silhouette —
    kills smeared marks that the warp dragged beyond the body."""
    h, w = st.shape
    im = Image.new("L", (w, h), 0)
    ImageDraw.Draw(im).polygon([(c * w, r * h) for r, c in sil], fill=255)
    return st * (np.asarray(im) > 0)


def _erase(stroke: np.ndarray, cy: float, cx: float, rad: float) -> None:
    h, w = stroke.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    m = ((yy / h - cy) ** 2 + (xx / w - cx) ** 2) < rad ** 2
    stroke[m] = 0


def _draw_lid(stroke: np.ndarray, cy: float, cx: float,
              rx: float, ry: float) -> None:
    """Closed-curve eye (the sleep still's grammar): shallow U arc
    where the dot was — contented/drowsy, unmistakably lazy."""
    h, w = stroke.shape
    im = Image.fromarray(stroke)
    d = ImageDraw.Draw(im)
    x0, y0 = (cx - rx) * w, (cy - ry * 0.3) * h
    x1, y1 = (cx + rx) * w, (cy + ry) * h
    d.arc([x0, y0, x1, y1], start=15, end=165,
          fill=255, width=max(2, int(h * 0.016)))
    np.copyto(stroke, np.asarray(im))


def _spot_fills(spec: dict) -> list:
    """Flank-marking fills: centroid in the rear-upper body region."""
    out = []
    for f in spec["fills"]:
        cy = float(np.mean([p[0] for p in f["poly"]]))
        cx = float(np.mean([p[1] for p in f["poly"]]))
        if cx > 0.55 and 0.10 < cy < 0.62:
            out.append(f)
    return out


def _eyespot_fills(spec: dict) -> list:
    """The cheek/eye blush circle — waddles' signature marking."""
    out = []
    for f in spec["fills"]:
        cy = float(np.mean([p[0] for p in f["poly"]]))
        cx = float(np.mean([p[1] for p in f["poly"]]))
        if 0.24 < cx < 0.44 and 0.12 < cy < 0.40:
            out.append(f)
    return out


def _integrity_flags(spec: dict) -> list:
    """Render + structural scan. Returns defect names — these are the
    'as obvious as a foot turning weird / squares missing' alarms
    (operator 2026-11-10): they should fire the moment they appear."""
    import state_oracle as so
    arr = np.asarray(tl.render(spec))
    out = [n for n, fn in (("interior_holes", so.interior_holes),
                           ("stroke_bleed", so.stroke_bleed),
                           ("frame_clip", so.frame_clip),
                           ("fragments", so.fragments))
           if fn(arr)["defect"]]
    if so.self_intersect(spec)["defect"]:
        out.append("self_intersect")
    return out


def derive_checked(base_path: Path, ops: list[dict]) -> dict:
    """The undo rule: apply ops ONE AT A TIME from base; each trial
    renders through the integrity oracle. A NEW defect blames the op
    -> halve its 'a' and retry (<=3); still bad -> drop it (undo).
    Good artists don't ship broken strokes. Dropped/shrunk ops are
    recorded in spec['ops_dropped'] / ['ops_applied']."""
    cur_flags = _integrity_flags(json.loads(base_path.read_text()))
    applied: list[dict] = []
    dropped: list[dict] = []
    for op in ops:
        o = dict(op)
        for _ in range(4):
            trial = derive(base_path, applied + [o])
            new = [f for f in _integrity_flags(trial) if f not in cur_flags]
            if not new:
                applied.append(o)
                cur_flags = _integrity_flags(trial)
                break
            if "a" in o and o["a"] > 0.05:
                o["a"] = round(o["a"] / 2, 3)
            else:
                break
        else:
            pass
        if o not in applied:
            dropped.append({**o, "reason": "integrity defect"})
    spec = derive(base_path, applied)
    spec["ops_applied"] = applied
    spec["ops_dropped"] = dropped
    return spec


def derive(base_path: Path, ops: list[dict]) -> dict:
    spec = json.loads(base_path.read_text())
    FIELD_RES = 64
    dy, dx = _field_grid(FIELD_RES, FIELD_RES,
                         [o for o in ops if o["op"] != "droopy_lids"])
    spec["silhouette"] = _warp_poly(spec["silhouette"], dy, dx)
    for f in spec["fills"]:
        f["poly"] = _warp_poly(f["poly"], dy, dx)
    st = np.asarray(tl._stroke_img(spec)).astype(np.float32)
    st = _warp_bitmap(st, dy, dx)
    _retopo(spec, ops)
    st = _clip_strokes(st, spec["silhouette"])
    for op in ops:
        if op["op"] == "droopy_lids":
            for ey, ex in EYES:
                _erase(st, ey, ex, 0.022)
                _draw_lid(st, ey, ex, 0.034, 0.034)
        elif op["op"] == "open_eyes":
            for ey, ex in EYES:
                _erase(st, ey, ex, 0.024)
            h, w = st.shape
            im = Image.fromarray(np.clip(st, 0, 255).astype(np.uint8))
            d = ImageDraw.Draw(im)
            r = 0.020 * h
            for ey, ex in EYES:
                d.ellipse([(ex * w - r, ey * h - r),
                           (ex * w + r, ey * h + r)], fill=255)
            np.copyto(st, np.asarray(im))
        elif op["op"] == "respot":
            s = float(op.get("s", 1.0))
            ddx = float(op.get("dx", 0.0)); ddy = float(op.get("dy", 0.0))
            for f in _spot_fills(spec):
                cys = np.mean([p[0] for p in f["poly"]])
                cxs = np.mean([p[1] for p in f["poly"]])
                f["poly"] = [[round(cys + (p[0] - cys) * s + ddy, 4),
                              round(cxs + (p[1] - cxs) * s + ddx, 4)]
                             for p in f["poly"]]
        elif op["op"] == "nospots":
            spec["fills"] = [f for f in spec["fills"]
                             if f not in _spot_fills(spec)]
        elif op["op"] == "noeyespot":
            spec["fills"] = [f for f in spec["fills"]
                             if f not in _eyespot_fills(spec)]
        elif op["op"] == "eyepatch":
            # replace the blush circle with a bigger, darker, irregular
            # patch over the near eye — marking swap, not removal
            for f in _eyespot_fills(spec):
                cys = np.mean([p[0] for p in f["poly"]])
                cxs = np.mean([p[1] for p in f["poly"]])
                f["poly"] = [[round(cys + (p[0] - cys) * 1.9 + 0.03, 4),
                              round(cxs + (p[1] - cxs) * 1.9 - 0.02, 4)]
                             for p in f["poly"]]
                f["rgb"] = [int(c) for c in op.get("rgb", [203, 138, 148])]
        elif op["op"] == "recolor":
            spec["body_rgb"] = [int(c) for c in op["rgb"]]
        elif op["op"] == "saddle":
            # back patch: polygon draped over the top-rear silhouette
            spec["fills"].append({
                "poly": [[0.06, 0.42], [0.00, 0.55], [0.02, 0.72],
                         [0.10, 0.82], [0.26, 0.80], [0.34, 0.70],
                         [0.30, 0.55], [0.20, 0.44]],
                "rgb": [int(c) for c in op.get("rgb", [231, 155, 155])]})
    img = Image.fromarray(np.clip(st, 0, 255).astype(np.uint8), "L")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    spec["stroke_b64"] = base64.b64encode(buf.getvalue()).decode()
    # auto-window: warps can push polys outside [0,1] (flee lean cut
    # the face) — widen the render window to the new bounds + margin
    # so nothing clips.
    allr = [p[0] for p in spec["silhouette"]]
    allc = [p[1] for p in spec["silhouette"]]
    spec["window"] = [round(min(allr) - 0.04, 4), round(min(allc) - 0.04, 4),
                      round(max(allr) + 0.04, 4), round(max(allc) + 0.04, 4)]
    spec["derived_from"] = str(base_path)
    spec["ops"] = ops
    return spec


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--ops", required=True,
                    help="comma list: name or name=a,b,c")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    ops = []
    for tok in a.ops.split(","):
        if "=" in tok:
            name, arg = tok.split("=", 1)
            vals = [float(x) for x in arg.split(":")]
            op = {"op": name}
            if name in ("recolor", "saddle", "eyepatch") and len(vals) == 3:
                op["rgb"] = vals
            else:
                keys = {"belly_droop": ["a"], "jowl": ["a"],
                        "ear_droop": ["a"], "squat": ["a"], "lean": ["a"],
                        "lie": ["a", "line"], "stride": ["a"],
                        "pin_legs": ["a"], "respot": ["s", "dx", "dy"]}
                for k, vv in zip(keys.get(name, []), vals):
                    op[k] = vv
            ops.append(op)
        else:
            ops.append({"op": tok})
    spec = derive(Path(a.base), ops)
    Path(a.out).write_text(json.dumps(spec))
    tl.render(spec, bg=(128, 128, 128, 255)).save(
        Path(a.out).with_suffix(".png"))
    print(f"{a.out} ops={[o['op'] for o in ops]}")

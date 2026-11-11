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
    for op in ops:
        if op["op"] == "droopy_lids":
            for ey, ex in EYES:
                _erase(st, ey, ex, 0.022)
                _draw_lid(st, ey, ex, 0.034, 0.034)
        elif op["op"] == "respot":
            s = float(op.get("s", 1.0))
            ddx = float(op.get("dx", 0.0)); ddy = float(op.get("dy", 0.0))
            for f in spec["fills"]:
                if max(abs(p[0] - 0.34) for p in f["poly"]) < 0.5:
                    cys = np.mean([p[0] for p in f["poly"]])
                    cxs = np.mean([p[1] for p in f["poly"]])
                    f["poly"] = [[round(cys + (p[0] - cys) * s + ddy, 4),
                                  round(cxs + (p[1] - cxs) * s + ddx, 4)]
                                 for p in f["poly"]]
    img = Image.fromarray(np.clip(st, 0, 255).astype(np.uint8), "L")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    spec["stroke_b64"] = base64.b64encode(buf.getvalue()).decode()
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
            keys = {"belly_droop": ["a"], "jowl": ["a"], "ear_droop": ["a"],
                    "respot": ["s", "dx", "dy"]}
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

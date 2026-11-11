# provenance: author=devin; created=2026-11-10; source=session work; purpose=vectorize a ref's marks verbatim for the 1/1-copy milestone; intent=production
"""trace_linework — the 1/1-copy instrument.

Operator rule (2026-11-10): build a 1/1 copy FIRST — if the machine
can't reproduce the reference mark-for-mark, 'similar yet different'
is a guess stacked on a guess. Parametric approximation of features
(snout from measured fractions, guessed ear V) was the w4 failure
mode. The fix: the construction IS the ref's own marks, traced.

Layer model (all normalized to the silhouette bbox -> pose/scalable):

    silhouette — filled body contour polygon (pig_w4 already does)
    fills      — tonal regions as colored polygons (snout plate,
                 spots, blush) — compact, separable
    strokes    — the ref's dark linework as a normalized bitmap
                 (base64 PNG). NOT polygons: the rough-line register
                 is a connected web — ear V meets the top outline,
                 leg lines meet the bottom, and a per-component
                 contour wraps the hull (the v1 all-black bug).
                 Stroke weight IS data; a bitmap preserves it.

Verify: re-render vs source -> fill IoU + stroke-pixel F1 + color
MAE. >=0.97 = true 1/1. Deformations then warp all three layers by
the same field -> 'same pig, new pose' stays consistent.

    python trace_linework.py canon/refs/waddles_view_profile.png \
        canon/refs/waddles_sil_profile.png --out canon/trace_profile.json
"""
import argparse
import base64
import io
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter1d
from skimage import measure, morphology

DARK_LUM = 90          # stroke threshold (lines ~0-50, fills ~180+)
TONAL_DIST = 55        # min rgb-sum distance from body pink for fills
SMOOTH = 1.0           # wrapped gaussian sigma (same as silhouette trace)
MIN_FILL = 30          # px min tonal-fill area


def _smooth(c: np.ndarray) -> np.ndarray:
    x = gaussian_filter1d(c[:, 0], SMOOTH, mode="wrap")
    y = gaussian_filter1d(c[:, 1], SMOOTH, mode="wrap")
    return np.stack([x, y], -1)


def _mask(png: Path) -> np.ndarray:
    a = np.asarray(Image.open(png).convert("RGBA")).astype(np.int16)
    m = a[..., 3] > 40
    if m.mean() > 0.95:                       # opaque bg -> border color
        bg = np.median(np.r_[a[0, :, :3], a[-1, :, :3],
                             a[:, 0, :3], a[:, -1, :3]], axis=0)
        m = np.abs(a[..., :3] - bg).sum(-1) > 60
    return morphology.remove_small_holes(m, 200)


def extract(view_png: Path, sil_png: Path) -> dict:
    v = np.asarray(Image.open(view_png).convert("RGBA")).astype(np.int16)
    sil = _mask(sil_png)
    ys, xs = np.where(sil)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    bh, bw = y1 - y0, x1 - x0
    lum = v[..., :3].mean(-1)
    dark = (lum < DARK_LUM) & sil
    body = np.median(v[sil & ~dark][:, :3], axis=0)
    dist = np.abs(v[..., :3] - body).sum(-1)
    tonal = (dist > TONAL_DIST) & sil & ~dark

    def norm(poly):
        return [[round(float((r - y0) / bh), 4), round(float((c - x0) / bw), 4)]
                for r, c in poly]

    sil_c = np.pad(sil, 1)
    sil_poly = _smooth(max(measure.find_contours(sil_c.astype(float), 0.5), key=len))
    sil_poly -= 1                              # unpad -> view coords

    # stroke layer: dark mask cropped to sil bbox, as base64 PNG (L)
    stroke_img = Image.fromarray((dark[y0:y1, x0:x1] * 255).astype(np.uint8), "L")
    buf = io.BytesIO()
    stroke_img.save(buf, format="PNG")
    stroke_b64 = base64.b64encode(buf.getvalue()).decode()

    fills = []
    lab = measure.label(tonal)
    for r in measure.regionprops(lab):
        if r.area < MIN_FILL:
            continue
        sub = morphology.binary_dilation(lab == r.label, morphology.disk(1))
        sub = np.pad(sub, 1)
        cs = measure.find_contours(sub.astype(float), 0.5)
        if not cs:
            continue
        fills.append({"poly": norm(_smooth(max(cs, key=len)) - 1),
                      "rgb": [int(c) for c in np.median(v[lab == r.label][:, :3], axis=0)]})
    return {"source": str(view_png), "bbox": [int(y0), int(x0), int(y1), int(x1)],
            "body_rgb": [int(c) for c in body],
            "silhouette": norm(sil_poly), "fills": fills,
            "stroke_b64": stroke_b64, "stroke_size": [int(bw), int(bh)]}


def _stroke_img(spec: dict) -> Image.Image:
    return Image.open(io.BytesIO(base64.b64decode(spec["stroke_b64"]))).convert("L")


def render(spec: dict, size: tuple[int, int] | None = None,
           bg: tuple = (0, 0, 0, 0), style: str = "rough") -> Image.Image:
    """Re-draw the trace. size = (w,h) canvas; default = source bbox.

    spec["window"] = [y0,x0,y1,x1] maps that frac window to the canvas;
    default [0,0,1,1]. Derived specs widen it when a warp pushes
    geometry outside [0,1] so nothing clips (flee lean cut the face).

    style = the emitter (Reson: IR -> target language):
      "rough"  — the ref's own register: near-black variable-weight
      "flat"   — cel/poster register: lineart harmonized to a dark
                 body-tone (x0.32) at uniform thin weight
      "sprite" — pixel-art register: dark body-tone linework (x0.28),
                 the whole emission pixelated ~12px blocks
    Same spec, different emission. Emitter contract: linework
    luminance must stay < body luminance so the oracle's dark
    detectors remain valid on any emission."""
    y0, x0, y1, x1 = spec["bbox"]
    w, h = (x1 - x0, y1 - y0) if size is None else size
    wy0, wx0, wy1, wx1 = spec.get("window", [0.0, 0.0, 1.0, 1.0])
    ww, wh = wx1 - wx0, wy1 - wy0
    img = Image.new("RGBA", (w, h), bg)
    dr = ImageDraw.Draw(img)

    def pts(poly):
        return [((c - wx0) / ww * w, (r - wy0) / wh * h) for r, c in poly]

    dr.polygon(pts(spec["silhouette"]), fill=tuple(spec["body_rgb"]) + (255,))
    for f in spec["fills"]:
        dr.polygon(pts(f["poly"]), fill=tuple(f["rgb"]) + (255,))
    # stroke bitmap covers frac [0,1]x[0,1] — paste at window offset
    st = _stroke_img(spec)
    if style == "flat":                    # uniform thin weight —
        import numpy as _np                # the cel register (IR
        from scipy.ndimage import binary_erosion  # bitmap untouched)
        st = Image.fromarray(
            (binary_erosion(_np.asarray(st) > 40) * 255)
            .astype(_np.uint8))
    st = st.resize((max(1, int(w / ww)),
                    max(1, int(h / wh))), Image.NEAREST)
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    tints = {"rough": (30, 25, 30),
             "flat": tuple(int(c * 0.32) for c in spec["body_rgb"]),
             "sprite": tuple(int(c * 0.28) for c in spec["body_rgb"])}
    dark = Image.new("RGBA", st.size,
                     tints.get(style, tints["rough"]) + (255,))
    layer.paste(dark, (int(-wx0 / ww * w), int(-wy0 / wh * h)), st)
    img = Image.alpha_composite(img, layer)
    if style == "sprite":          # chunky blocks are an emission
        import numpy as _np                          # choice — the
        from scipy.ndimage import binary_fill_holes  # IR stays whole
        sw, sh = max(1, w // 12), max(1, h // 12)
        img = img.resize((sw, sh), Image.NEAREST) \
                 .resize((w, h), Image.NEAREST)
        # sprites must be solid: pixelation's stair edges can leave
        # sub-threshold alpha gaps inside — seal them at emission
        a = _np.asarray(img)[..., 3] > 40
        img.putalpha(Image.fromarray(
            (binary_fill_holes(a) * 255).astype(_np.uint8)))
    return img


def fidelity(spec: dict, view_png: Path, sil_png: Path) -> dict:
    """Pixel-truth check: re-render vs the actual source image."""
    v = np.asarray(Image.open(view_png).convert("RGBA")).astype(np.int16)
    sil = _mask(sil_png)
    y0, x0, y1, x1 = spec["bbox"]
    r = np.asarray(render(spec))
    r_full = np.zeros_like(v)
    rh, rw = r.shape[:2]
    h, w = min(rh, y1), min(rw, x1)
    r_full[:h, :w] = r[:h, :w]
    r_sil = r_full[..., 3] > 40
    iou = (sil & r_sil).sum() / max(1, (sil | r_sil).sum())
    lum = v[..., :3].mean(-1)
    src_dark = (lum < DARK_LUM) & sil
    r_lum = r_full[..., :3].mean(-1)
    r_dark = (r_lum < DARK_LUM) & r_sil
    tp = (src_dark & r_dark).sum()
    f1 = 2 * tp / max(1, src_dark.sum() + r_dark.sum())
    mae = float(np.abs(v[sil][:, :3] - r_full[sil][:, :3]).mean())
    return {"sil_iou": round(float(iou), 4), "stroke_f1": round(float(f1), 4),
            "color_mae": round(mae, 1)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("view")
    ap.add_argument("sil")
    ap.add_argument("--out", required=True)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    spec = extract(Path(a.view), Path(a.sil))
    Path(a.out).write_text(json.dumps(spec))
    render(spec, bg=(128, 128, 128, 255)).save(Path(a.out).with_suffix(".png"))
    print(f"{a.out}: sil_pts={len(spec['silhouette'])} fills={len(spec['fills'])} "
          f"stroke={len(spec['stroke_b64'])//1024}KB")
    if a.check:
        print(" fidelity:", fidelity(spec, Path(a.view), Path(a.sil)))

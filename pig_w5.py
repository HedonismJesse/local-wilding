# provenance: author=devin; created=2026-11-10; source=operator rule
#   "build a 1/1 copy first — if we can't build that, how can we do
#   similar yet distinctly different"; purpose=trace-driven pig
#   construction: poses are deformations of VERIFIED trace specs
#   (canon/trace_*.json, sil_iou~0.99/stroke_f1 1.0 vs source), not
#   parametric approximations; intent=production
"""pig_w5 — trace-driven waddles construction.

w4 traced the silhouette but still DREW the interior from measured
fractions — 'a squished version of the last tries' (operator). w5
makes the verified 1/1 copy the substrate: every pose loads a
trace_linework spec (silhouette poly + tonal-fill polys + the ref's
own linework bitmap) and warps ALL layers by the same field, so the
marks stay mark-for-mark consistent — deformation, not redrawing.

Pose -> trace map:
    rest   -> canon/trace_rest.json   (sleeping loaf, still)
    notice -> canon/trace_profile.json (model-sheet profile)
    flee   -> canon/trace_walk.json   (head-down walk still)
    fly    -> trace_profile + wing layer (tilt is param)

Wings are a separate layer composited at the attach point — pig
pixels are IDENTICAL with/without wings by construction (the
consistency invariant: delta == attachment).

Builder contract: draw_w5_pig(ax, pose, facing, tilt, squash, wings)
— matplotlib Axes like pig_w4/pig_w2 (candidate_sheet _render).

    python pig_w5.py            # pose strip preview
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw

import pig_derive as pd
import trace_linework as tl

CANON = Path(__file__).parent / "canon"
BASE_SPEC = "ourpig_base"
# per-pose derivation ops on the base spec (pig_derive vocabulary)
POSE_OPS = {"rest": [{"op": "lie", "a": 1.0, "line": 0.80},
                     {"op": "erase_comp", "cy": 0.42, "cx": 0.53,
                      "r": 0.12}],
            "notice": [{"op": "open_eyes"}],
            "flee": [{"op": "stride", "a": 0.7}, {"op": "lean", "a": 0.12}],
            "fly": [{"op": "pin_legs", "a": 1.0}]}
POSE_TRACE = {p: BASE_SPEC for p in ("rest", "notice", "flee", "fly")}
WING = (223, 244, 238, 255)      # mint — G-dominant (pig is R-dominant)
WING_EC = (185, 228, 216, 255)
_SPECS: dict = {}


def _spec(name: str) -> dict:
    if name not in _SPECS:
        _SPECS[name] = json.loads((CANON / f"{name}.json").read_text())
    return _SPECS[name]


def _wing(img_size: tuple[int, int], span: float) -> Image.Image:
    """Simple cartoon wing pair — separate attachment layer."""
    w, h = img_size
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx, cy = w * 0.5, h * 0.30
    s = span * min(w, h)
    for sgn in (-1, 1):
        pts = [(cx + sgn * s * 0.10, cy + s * 0.30),
               (cx + sgn * s * 0.55, cy - s * 0.42),
               (cx + sgn * s * 0.95, cy - s * 0.30),
               (cx + sgn * s * 0.72, cy - s * 0.02),
               (cx + sgn * s * 0.40, cy + s * 0.22)]
        d.polygon(pts, fill=WING, outline=WING_EC, width=max(2, int(s * 0.03)))
    return layer


def pose_spec(pose: str) -> dict:
    """The derived spec a pose renders from — the oracle inspects
    this, not just pixels."""
    ops = POSE_OPS.get(pose, [])
    return (_spec(POSE_TRACE[pose]) if not ops
            else pd.derive_checked(CANON / f"{BASE_SPEC}.json", ops))


def render_pose(pose: str = "rest", facing: int = 1, tilt: float = 0.0,
                squash: float = 1.0, wings: int = 0,
                canvas: tuple[int, int] = (1200, 750),
                trace_dir: Path | None = None) -> Image.Image:
    """Render a pose from its trace spec. All warps apply to the whole
    composite (sil+linework+fills together) — marks stay consistent."""
    spec = pose_spec(pose)
    pig = tl.render(spec)                          # source-res RGBA
    if squash != 1.0:                              # squash = height scale
        pig = pig.resize((pig.width, max(1, int(pig.height * squash))),
                         Image.BICUBIC)
    if facing < 0:
        pig = pig.transpose(Image.FLIP_LEFT_RIGHT)
    if tilt:
        pig = pig.rotate(tilt, expand=True, resample=Image.BICUBIC)
    out = Image.new("RGBA", canvas, (0, 0, 0, 0))
    headroom = 0.58 if wings else 0.86   # wings occupy the top ~28%
    scale = min(canvas[0] * 0.82 / pig.width,
                canvas[1] * headroom / pig.height)
    pig = pig.resize((max(1, int(pig.width * scale)),
                      max(1, int(pig.height * scale))), Image.BICUBIC)
    x = (canvas[0] - pig.width) // 2
    y = canvas[1] - pig.height - int(canvas[1] * 0.06)
    if wings:
        wimg = _wing(pig.size, 0.55)
        wy = max(6, y - int(pig.height * 0.28))
        out.alpha_composite(wimg, (x, wy))
    out.alpha_composite(pig, (x, y))
    return out


def draw_w5_pig(ax, pose: str = "rest", facing: int = 1, tilt: float = 0.0,
                squash: float = 1.0, wings: int = 0, **_) -> None:
    """candidate_sheet builder — renders the trace-spec pose."""
    img = render_pose(pose, int(facing), float(tilt), float(squash),
                      int(wings))
    ax.imshow(np.asarray(img))
    ax.axis("off")


def pig_bitmap(pose: str = "rest", facing: int = 1, tilt: float = 0.0,
               squash: float = 1.0, **_k) -> np.ndarray:
    """Pig-only alpha mask (no wings) — the consistency instrument."""
    img = render_pose(pose, facing, tilt, squash, wings=0)
    return (np.asarray(img)[..., 3] > 40)


if __name__ == "__main__":
    poses = [("rest", {}), ("notice", {}), ("flee", {"facing": -1}),
             ("fly", {"tilt": 18, "wings": 1})]
    fig, axs = plt.subplots(1, 4, figsize=(20, 5), dpi=110)
    for ax, (pose, kw) in zip(axs, poses):
        ax.imshow(np.asarray(render_pose(pose, **kw)))
        ax.set_title(pose)
        ax.axis("off")
    fig.savefig("pig_w5_poses.png", transparent=True)
    print("pig_w5_poses.png")

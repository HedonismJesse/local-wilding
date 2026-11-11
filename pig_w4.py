# provenance: author=devin; created=2026-11-10; source=official model
#   sheet canon/refs/hunt_Waddles_model_sheet.png (Disney pasteup,
#   "Waddles the Pig - Front and Back Rev.1", internal-reference-only)
#   -> silhouette canon/refs/waddles_sil_profile.png + measured
#   feature fractions; purpose=trace-built waddles pig: silhouette IS
#   the reference (resemblance >=0.97 target), tapered outline for
#   the rough-line register the sheet itself specifies;
#   intent=production
"""pig_w4 — trace-built waddles pig.

w3 was a squashed ellipse (0.74-0.86 resemblance, operator: 'still
clip-art'). w4 builds the body ON the model-sheet silhouette itself:
the outline polygon is the reference's own contour, smoothed and
placed on canvas; interior features sit at fractions measured from
the sheet's profile view. Line register = variable-weight stroke
(the sheet literally says 'ROUGH LINE - STANDARD CLEANUP LINE').

Measured feature map (fractions of silhouette bbox, y down):
    snout_plate  box [0.10,0.26,0.31,0.59] - coral rounded rect
    eye_near     (0.145,0.245)  eye_far (0.315,0.26) - black dots
    ear_tri      box [0.40,0.10,0.55,0.42] - interior triangle, point down
    ear_flop     silhouette bump upper-left + interior fold line
    mouth        smile from snout's bottom-right corner
    spot         big irregular blob [0.60,0.15,0.85,0.50] + dot (0.80,0.545)
    tail         curl in silhouette at (0.93,0.09)
    legs         4 nubs in silhouette, hoof caps at tips
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path
import matplotlib.patches as mpatches
import matplotlib.transforms as mt
import numpy as np
from PIL import Image

PINK = "#F6BFC0"; PATCH = "#E79B9B"; SNOUT = "#EE7B73"
DARK = "#1E1E26"; HOOF = "#3A3A46"
WING = "#DFF4EE"; WING_EC = "#B9E4D8"
SIL_PNG = "canon/refs/waddles_sil_profile.png"

_CONTOUR = None


def _contour() -> np.ndarray:
    """The reference silhouette as a smoothed polygon (image coords,
    y down), resampled to 320 points."""
    global _CONTOUR
    if _CONTOUR is None:
        from skimage.measure import find_contours
        from scipy.ndimage import gaussian_filter1d, binary_fill_holes
        m = np.asarray(Image.open(SIL_PNG).convert("RGBA"))[..., 3] > 128
        m = binary_fill_holes(m)
        m = np.pad(m, 6)                    # contour can't close on
        c = max(find_contours(m.astype(float), 0.5), key=len)
        c = c - 6                           # edge-touching shapes
        # resample + wrapped gaussian: smooth jaggies, no overshoot
        t = np.linspace(0, 1, len(c))
        u = np.linspace(0, 1, 320)
        x = np.interp(u, t, c[:, 1]); y = np.interp(u, t, c[:, 0])
        x = gaussian_filter1d(np.r_[x, x, x], 1.0, mode="wrap")[320:640]
        y = gaussian_filter1d(np.r_[y, y, y], 1.0, mode="wrap")[320:640]
        _CONTOUR = np.column_stack([x, y])
    return _CONTOUR.copy()


def _norm(pts: np.ndarray) -> np.ndarray:
    mn, mx = pts.min(0), pts.max(0)
    return (pts - mn) / (mx - mn)


def draw_w4_pig(ax, pose="rest", belly=1.0, droop=1.0, squash=1.0,
                outline=True, phase=0.0, wings=False, facing=1,
                spots=True):
    ax.set_xlim(0, 16); ax.set_ylim(0, 10); ax.set_aspect("equal")
    ax.axis("off")
    # mir = data-space mirror (point math); tr = patch transform
    # (mirror + display). Mixing them once put the body in pixel
    # coords -> off-canvas, invisible flee pose.
    mir = mt.Affine2D().scale(-1, 1).translate(16, 0)
    tr = mir + ax.transData if facing < 0 else ax.transData

    # ---------------- silhouette placement
    n = _norm(_contour())
    # pose transforms in normalized space
    if pose == "flee":
        n[:, 0] *= 1.06 * belly                 # lean-stretch
        n[:, 1] *= 0.94 * squash
        n[:, 0] += 0.10 * (1 - n[:, 1])         # shear: mass tips fwd
    elif pose == "fly":
        n[:, 0] *= 0.97 * belly
        n[:, 1] *= 0.97 * squash
    else:
        n[:, 0] *= belly; n[:, 1] *= squash
    W, H = 9.6, 9.6 / 1.54                       # match measured aspect
    CX, CY = (8.0, 4.7) if pose != "fly" else (8.0, 5.0)
    pts = np.column_stack([
        (n[:, 0] - 0.5) * W + CX,
        (0.5 - n[:, 1]) * H * squash + CY])      # flip y -> canvas up

    def xform(pts2):
        p = pts2.copy()
        if pose == "fly":
            p = mt.Affine2D().rotate_deg_around(CX, CY, 4).transform(p)
        return mir.transform(p) if facing < 0 else p

    body = xform(pts)

    # ---------------- tapered outline band (variable weight stroke)
    def tapered(pts_closed, base=0.05, top_thin=0.35):
        """Stroke as a filled band: outer=contour, inner=contour moved
        inward along -normal by w(t). Thicker under the mass, thin top
        - the rough-line register."""
        c = pts_closed
        d = (np.roll(c, -1, 0) - np.roll(c, 1, 0)) / 2.0  # periodic
        nl = np.hypot(d[:, 0], d[:, 1]); nl[nl == 0] = 1
        nrm = np.column_stack([-d[:, 1] / nl, d[:, 0] / nl])  # inward-ish
        cen = c.mean(0)
        # flip normals that point away from the centroid
        side = np.sign(np.einsum("ij,ij->i", cen - c, nrm))
        side[side == 0] = 1
        nrm *= side[:, None]
        upness = np.clip(nrm[:, 1], -1, 1)       # normal points up => top edge
        w = base * (1 + 0.9 * np.clip(-upness, 0, 1)
                    - top_thin * np.clip(upness, 0, 1))
        inner = c + nrm * w[:, None]
        ring = np.vstack([c, inner[::-1], c[0]])
        codes = ([Path.MOVETO] + [Path.LINETO] * (len(c) - 1)
                 + [Path.MOVETO] + [Path.LINETO] * (len(inner) - 1)
                 + [Path.CLOSEPOLY])
        return mpatches.PathPatch(Path(ring, codes), fc=DARK, ec="none",
                                  zorder=3.5)

    def ellipse(x, y, w, h, c, z, angle=0, e="none", ww=0):
        p = mpatches.Ellipse((x, y), w, h, angle=angle, fc=c, ec=e,
                             lw=ww, zorder=z)
        p.set_transform(tr); ax.add_patch(p); return p

    def curve(verts, c, z, e=DARK, w=0.05, close=True):
        codes = [Path.MOVETO] + [Path.CURVE3] * (len(verts) - 1)
        if close:
            verts = verts + [verts[0]]; codes += [Path.CLOSEPOLY]
        p = mpatches.PathPatch(Path(verts, codes), fc=c, ec=e, lw=w * 30,
                               zorder=z, joinstyle="round",
                               capstyle="round")
        p.set_transform(tr); ax.add_patch(p); return p

    def frac(fx, fy):
        """silhouette-bbox fraction -> canvas coords (y-down frac)."""
        return np.array([(fx - 0.5) * W + CX, (0.5 - fy) * H + CY])

    def line(pts, c, z, wdt=2.6):
        p = np.array([frac(*q) for q in pts])
        p2 = xform(p)
        ax.plot(p2[:, 0], p2[:, 1], color=c, lw=wdt,
                solid_capstyle="round", zorder=z)

    # ---------------- ground shadow (under mask threshold alpha)
    if pose in ("rest", "notice"):
        ellipse(8.0, 1.1, 8.4, 0.55, "#3A3A4422", 1.5)

    if wings:
        for drot, dz, c, sc in [(18, -0.05, WING_EC, 0.9),
                                (0, 0, WING, 1.0)]:
            wtr = (mt.Affine2D().rotate_deg(-30 + 40 * np.sin(
                phase * 2 * np.pi) + drot).scale(sc)
                .translate(6.9, 6.9) + tr)
            v = [(0.0, 0.0), (1.2, 1.5), (2.6, 2.2), (4.2, 2.3),
                 (4.9, 1.9), (4.2, 1.55), (4.6, 1.1), (3.9, 0.9),
                 (4.1, 0.45), (3.3, 0.35), (2.6, -0.15), (1.4, -0.35)]
            codes = [Path.MOVETO] + [Path.CURVE4] * (len(v) - 1)
            ax.add_patch(mpatches.PathPatch(
                Path(v + [v[0]], codes + [Path.CLOSEPOLY]),
                fc=c, ec=WING_EC, lw=3.0, zorder=2.4 + dz,
                joinstyle="round", transform=wtr))

    # ---------------- body: silhouette fill + tapered outline
    ax.add_patch(mpatches.Polygon(
        xform(pts) if pose != "fly" else body,
        closed=True, fc=PINK, ec="none", zorder=3))
    if outline:
        ring = tapered(body if pose == "fly" else xform(pts),
                       base=0.13 * max(1, W / 9.6))   # ref line is
        # heavy - 'ROUGH LINE' register, not hairline digital
        ax.add_patch(ring)

    # ---------------- features at measured fractions
    if spots:
        s_pts = [(0.62, 0.18), (0.72, 0.14), (0.82, 0.20), (0.85, 0.30),
                 (0.82, 0.42), (0.74, 0.50), (0.63, 0.46), (0.59, 0.34)]
        p = np.array([frac(*q) for q in s_pts])
        ax.add_patch(mpatches.Polygon(
            xform(p), closed=True, fc=PATCH, ec="none", zorder=3.2))
        ellipse(*frac(0.80, 0.545), 0.55, 0.45, PATCH, 3.2)

    # snout plate - ref's is a WIDE tilted rounded trapezoid, not a
    # box: top edge higher at right, nostrils are round slit-dots
    sn = [(0.10, 0.34), (0.17, 0.27), (0.30, 0.30), (0.315, 0.50),
          (0.27, 0.60), (0.15, 0.62), (0.095, 0.50)]
    p = np.array([frac(*q) for q in sn])
    p = xform(p)
    tck, _ = __import__('scipy.interpolate', fromlist=['splprep']) \
        .splprep([p[:, 0], p[:, 1]], s=0.18, per=1)
    uu = np.linspace(0, 1, 80)
    sx, sy = __import__('scipy.interpolate', fromlist=['splev']) \
        .splev(uu, tck)
    ax.add_patch(mpatches.Polygon(np.column_stack([sx, sy]),
                                  closed=True, fc=SNOUT, ec=DARK,
                                  lw=4.5, zorder=4, joinstyle="round"))
    # nostrils: two small dark slits inside the plate
    line([(0.16, 0.40), (0.175, 0.47)], DARK, 4.5, wdt=4.2)
    line([(0.25, 0.39), (0.24, 0.46)], DARK, 4.5, wdt=4.2)

    # eyes - dots (wide set, above snout)
    eye_mode = {"rest": "dot", "notice": "dot",
                "flee": "dot", "fly": "dot"}[pose]
    if pose == "rest":
        # sleepy: half-lid line over dots
        for ex, ey in [(0.145, 0.245), (0.315, 0.26)]:
            e = frac(ex, ey)
            ellipse(*e, 0.34, 0.34, DARK, 5)
        line([(0.115, 0.215), (0.175, 0.21)], DARK, 5, wdt=1.8)
        line([(0.285, 0.23), (0.345, 0.225)], DARK, 5, wdt=1.8)
    else:
        for ex, ey in [(0.145, 0.245), (0.315, 0.26)]:
            e = frac(ex, ey)
            ellipse(*e, 0.36, 0.36, DARK, 5)

    # interior ear: ref's is a THICK curved V - top edge of head,
    # apex down, slightly hooked. Open strokes, not a closed flag.
    line([(0.42, 0.10), (0.47, 0.22), (0.505, 0.395)], DARK, 4.2,
         wdt=4.6)
    line([(0.555, 0.115), (0.525, 0.24), (0.505, 0.395)], DARK, 4.2,
         wdt=4.6)
    line([(0.085, 0.075), (0.115, 0.16), (0.095, 0.24)], DARK, 4.2,
         wdt=3.6)                                   # flop fold crease

    # tail curl: the silhouette carries a bump; the ref draws a thin
    # spiral ON it - draw the curl explicitly
    tc = frac(0.95, 0.10)
    tt = np.linspace(0, 3.2 * np.pi, 60)
    tpts = np.column_stack([
        tc[0] + 0.085 * tt * np.cos(tt + 1.2),
        tc[1] + 0.10 * tt * np.sin(tt + 1.2)])
    tpts = mir.transform(tpts) if facing < 0 else tpts
    ax.plot(tpts[:, 0], tpts[:, 1], color=DARK, lw=3.4,
            solid_capstyle="round", zorder=4.4)

    # mouth: smile from snout's bottom-right corner
    line([(0.255, 0.55), (0.275, 0.535), (0.30, 0.545)], DARK, 4.5,
         wdt=3.0)
    if pose == "flee":
        line([(0.255, 0.55), (0.27, 0.57), (0.29, 0.56)], DARK, 4.5,
             wdt=3.0)                               # worried press

    # hoof caps at the leg-nub tips (nubs live in the silhouette)
    if pose != "fly":
        for hx in (0.285, 0.42, 0.78, 0.865):
            tip = frac(hx, 0.955)
            e = mpatches.Ellipse((tip[0], tip[1]), 0.62, 0.42,
                                 fc=HOOF, ec=DARK, lw=1.6, zorder=3.8)
            e.set_transform(tr); ax.add_patch(e)
    else:
        for hx in (0.30, 0.44, 0.76, 0.85):
            tip = frac(hx, 0.99)
            tip = mt.Affine2D().rotate_deg_around(CX, CY, 4) \
                .transform(tip[None])[0]
            e = mpatches.Ellipse((tip[0], tip[1]), 0.6, 0.4,
                                 fc=HOOF, ec=DARK, lw=1.6, zorder=3.8)
            e.set_transform(tr); ax.add_patch(e)

    # z's intentionally absent: decoration outside the silhouette
    # inflates the bbox and shifts every oracle zone - add at scene
    # composite time, not in the scored construction


POSES = ["rest", "notice", "flee", "fly"]

if __name__ == "__main__":
    fig, axes = plt.subplots(1, 4, figsize=(20, 6), dpi=100)
    fig.patch.set_facecolor("#0D1B26")
    for ax, ps in zip(axes, POSES):
        ax.set_facecolor("#0D1B26")
        draw_w4_pig(ax, pose=ps, wings=(ps == "fly"), phase=0.3,
                    facing=1)   # source silhouette already faces LEFT;
                                # flee runs left, fly exits left
        ax.set_title(ps, color="#DFF4EE", fontsize=20, pad=12,
                     fontweight="bold")
    plt.subplots_adjust(left=0.01, right=0.99, top=0.9, bottom=0.01,
                        wspace=0.05)
    plt.savefig("pig_w4_poses.png", facecolor="#0D1B26")
    print("saved pig_w4_poses.png")

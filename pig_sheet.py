"""Pig variant sheet - 4 candidates on canon construction, pick before render.

A: v3 baseline (current cut)
B: dynamic pose - body pitched up, legs tucked, wings spread
C: character hook - aviator goggles + flowing scarf
D: chunky cartoon - bigger head ratio, rounder body
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, Polygon
from matplotlib.path import Path
import matplotlib.patches as mpatches
import numpy as np

PINK = "#F5A0B5"; DPINK = "#E87E97"; DARK = "#1B2A38"
WING = "#DFF4EE"; WING_EC = "#B9E4D8"; TEAL = "#3FD9A8"; HOOF = "#C95F7B"


def draw_pig(ax, pose=0.0, goggles=False, head_ratio=1.0, chunk=1.0,
             ear="tri", wing="scallop", snout=1.0, outline=False):
    ax.set_xlim(0, 16); ax.set_ylim(0, 10); ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(Ellipse((8, 5), 15, 9, fc="none"))

    def ellipse(x, y, w, h, c, z, angle=0, ec="none", lw=0):
        ax.add_patch(Ellipse((x, y), w, h, angle=angle, fc=c, ec=ec,
                             lw=lw, zorder=z))

    def _codes(n_movable):
        # CURVE4 consumes verts in triples; trailing singles/pairs become
        # LINETO/CURVE3 - a dangling CURVE4 vert spikes to the frame edge
        c4, rem = divmod(n_movable, 3)
        codes = [Path.CURVE4] * (c4 * 3)
        codes += [Path.CURVE3] * 2 if rem == 2 else [Path.LINETO] * rem
        return codes

    def curve(verts, c, z, ec="none", lw=0):
        codes = [Path.MOVETO] + _codes(len(verts) - 1)
        verts = verts + [verts[0]]; codes = codes + [Path.CLOSEPOLY]
        ax.add_patch(mpatches.PathPatch(Path(verts, codes), fc=c, ec=ec,
                                        lw=lw, zorder=z))

    # pose: rotate whole pig about body center by `pose` degrees
    import matplotlib.transforms as mt
    tr = mt.Affine2D().rotate_deg_around(7.5, 5.0, pose) + ax.transData

    def add(p):
        p.set_transform(tr); ax.add_patch(p); return p

    def curve2(verts, c, z, ec="none", lw=0):
        codes = [Path.MOVETO] + _codes(len(verts) - 1)
        verts = verts + [verts[0]]; codes = codes + [Path.CLOSEPOLY]
        add(mpatches.PathPatch(Path(verts, codes), fc=c, ec=ec, lw=lw,
                               zorder=z))

    def ellipse2(x, y, w, h, c, z, angle=0, ec="none", lw=0):
        add(Ellipse((x, y), w, h, angle=angle, fc=c, ec=ec, lw=lw, zorder=z))

    def poly2(pts, c, z, ec="none", lw=0):
        add(Polygon(pts, closed=True, fc=c, ec=ec, lw=lw, zorder=z))

    # sticker-outline register: dark edge on the main shapes (v4 look)
    ol_ec = DARK if outline else "none"
    ol_lw = 2.4 if outline else 0
    wing_ec = DARK if outline else WING_EC
    wing_lw = 2.4 if outline else 1.5

    if wing == "swept":
        # single smooth blades - max solidity, no scallop spikes
        curve2([(6.6, 6.8), (6.3, 8.9), (5.3, 9.6), (4.5, 9.4),
                (5.1, 8.2), (5.9, 7.0), (6.6, 6.8)], WING_EC, 2,
               ec=ol_ec, lw=ol_lw)
        curve2([(5.6, 6.4), (5.1, 8.9), (3.7, 9.8), (2.6, 9.4),
                (3.4, 8.1), (4.5, 6.7), (5.6, 6.4)], WING, 2.5,
               ec=wing_ec, lw=wing_lw)
    elif wing == "delta":
        # geometric paper-plane wing
        poly2([(6.6, 6.8), (4.6, 9.5), (4.0, 9.0), (6.0, 6.6)],
              WING_EC, 2, ec=ol_ec, lw=ol_lw)
        poly2([(5.7, 6.3), (2.7, 9.7), (2.2, 9.0), (5.2, 5.9)],
              WING, 2.5, ec=wing_ec, lw=wing_lw)
    else:
        # scallop (v3 cut): far wing tucked, near wing scalloped underside
        curve2([(6.6, 6.8), (6.2, 8.9), (5.2, 9.5), (4.4, 9.3),
                (4.8, 8.4), (5.2, 7.6), (5.8, 7.0), (6.6, 6.8)],
               WING_EC, 2, ec=ol_ec, lw=ol_lw)
        curve2([(5.6, 6.4), (5.0, 8.8), (3.6, 9.6), (2.8, 9.2),
                (2.7, 8.6), (3.0, 8.5), (3.3, 8.2),
                (3.8, 7.3), (4.1, 7.2), (4.4, 6.9),
                (4.9, 6.1), (5.2, 6.1), (5.6, 6.4)], WING, 2.5,
               ec=wing_ec, lw=wing_lw)
    # body
    ellipse2(7.0, 4.9, 6.0 * chunk, 3.9 * chunk, PINK, 3,
             ec=ol_ec, lw=ol_lw)
    # legs (tucked when posed)
    def leg(x, y, w, h, ang, z=2.6):
        dx = h * 0.5 * np.sin(np.radians(ang))
        dy = -h * 0.5 * np.cos(np.radians(ang))
        poly2([(x - w/2, y), (x + w/2, y),
               (x + w*0.28 + dx, y + dy), (x - w*0.28 + dx, y + dy)],
              DPINK, z, ec=ol_ec, lw=ol_lw * 0.7)
        ellipse2(x + dx, y + dy - 0.08, w*0.72, 0.5, HOOF, z + 0.1)

    leg(5.4, 3.6, 1.0, 1.5, 28); leg(6.4, 3.4, 1.0, 1.7, 12)
    leg(8.4, 3.4, 0.9, 1.5, -8); leg(9.2, 3.6, 0.9, 1.3, -22)
    # head
    ellipse2(10.7, 5.9, 3.0 * head_ratio, 2.9 * head_ratio, PINK, 4,
             ec=ol_ec, lw=ol_lw)
    # ears paired
    if ear == "flop":
        # droopy lobes - tip points down-out, anti-fin-ear
        curve2([(10.3, 7.15), (9.7, 8.15), (8.9, 8.3), (8.6, 7.7),
                (9.3, 7.0), (10.3, 7.15)], DPINK, 4.5,
               ec=ol_ec, lw=ol_lw)
        curve2([(11.15, 7.3), (11.75, 8.2), (12.25, 7.95), (12.0, 7.3),
                (11.5, 7.05), (11.15, 7.3)], DPINK, 4.4,
               ec=ol_ec, lw=ol_lw)
    else:
        poly2([(9.6, 7.0), (8.9, 8.7), (10.6, 7.6)], DPINK, 4.5,
              ec=ol_ec, lw=ol_lw)
        poly2([(10.8, 7.2), (10.9, 8.6), (11.8, 7.5)], DPINK, 4.5,
              ec=ol_ec, lw=ol_lw)
        poly2([(9.75, 7.25), (9.3, 8.3), (10.3, 7.55)], PINK, 4.6)
    # snout - THE identity oval
    ellipse2(11.9, 5.4, 1.5 * snout, 1.15 * snout, DPINK, 5,
             ec=ol_ec, lw=ol_lw)
    ellipse2(11.9 - 0.28 * snout, 5.45, 0.24, 0.34, DARK, 6)
    ellipse2(11.9 + 0.18 * snout, 5.45, 0.24, 0.34, DARK, 6)

    if goggles:
        # aviator goggles across the face
        ellipse2(10.35, 6.35, 0.95, 0.85, "#F6E05E", 6.5, ec=DARK, lw=2.5)
        ellipse2(10.35, 6.35, 0.65, 0.55, "#8FBFE8", 6.6)
        p = Path([(10.9, 6.5), (11.9, 6.9), (12.6, 6.9)],
                 [Path.MOVETO, Path.CURVE3, Path.CURVE3])
        gp = mpatches.PathPatch(p, fc="none", ec=DARK, lw=3, zorder=6.4)
        add(gp)
        # scarf streaming
        curve2([(9.0, 4.6), (7.6, 4.9), (6.2, 5.6), (5.0, 6.9),
                (5.4, 6.4), (5.6, 5.7), (6.6, 5.0), (7.9, 4.1),
                (9.0, 4.6)], "#E8455F", 3.5)
    else:
        # happy closed eye
        th = np.linspace(0.1*np.pi, 0.9*np.pi, 40)
        xs = 10.05 + 0.55*np.cos(th); ys = 6.35 + 0.45*np.sin(th)
        pts = np.column_stack([xs, ys])
        pts2 = tr.transform(pts)
        ax.plot(pts2[:, 0], pts2[:, 1], color=DARK, lw=4,
                solid_capstyle="round", zorder=6)
        ellipse2(9.9, 5.0, 0.95, 0.55, "#FBD3DE", 6)
        m = Path([(11.4, 4.75), (11.55, 4.83), (11.7, 4.8)],
                 [Path.MOVETO, Path.CURVE3, Path.CURVE3])
        add(mpatches.PathPatch(m, fc="none", ec=DARK, lw=2.5,
                               zorder=6))
    # curly tail
    t = np.linspace(0, 3.4*np.pi, 220)
    lws = np.linspace(4.0, 1.2, 220)
    for i in range(len(t)-1):
        x0 = 4.1 + 0.085*t[i]*np.cos(t[i]+2.6)
        y0 = 5.6 + 0.085*t[i]*np.sin(t[i]+2.6)
        x1 = 4.1 + 0.085*t[i+1]*np.cos(t[i+1]+2.6)
        y1 = 5.6 + 0.085*t[i+1]*np.sin(t[i+1]+2.6)
        (x0, y0), (x1, y1) = tr.transform([(x0, y0), (x1, y1)])
        if outline:
            ax.plot([x0, x1], [y0, y1], color=DARK, lw=lws[i] + 2.4,
                    solid_capstyle="round", zorder=3.9)
        ax.plot([x0, x1], [y0, y1], color=DPINK, lw=lws[i],
                solid_capstyle="round", zorder=4)
    # streaks (unrotated, frame-level)
    for sy, sx0, ln in [(1.6, 0.8, 2.8), (3.6, 0.4, 2.0),
                        (7.6, 0.8, 2.4), (8.7, 2.8, 1.6)]:
        ax.plot([sx0, sx0+ln], [sy, sy], color=TEAL, lw=5, alpha=0.85,
                solid_capstyle="round", zorder=1)


fig, axes = plt.subplots(1, 4, figsize=(20, 6), dpi=100)
fig.patch.set_facecolor("#0D1B26")
variants = [
    ("A - v3 baseline", dict()),
    ("B - dynamic pitch", dict(pose=14)),
    ("C - aviator", dict(pose=8, goggles=True)),
    ("D - chunky", dict(pose=6, head_ratio=1.18, chunk=0.92)),
]
for ax, (label, kw) in zip(axes, variants):
    ax.set_facecolor("#0D1B26")
    draw_pig(ax, **kw)
    ax.set_title(label, color="#DFF4EE", fontsize=20, pad=14,
                 fontweight="bold")
plt.subplots_adjust(left=0.01, right=0.99, top=0.88, bottom=0.01, wspace=0.05)
plt.savefig("pig_sheet.png", facecolor="#0D1B26")
print("saved pig_sheet.png")

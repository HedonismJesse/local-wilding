"""Flying-pig narrative animatic test (~8s @15fps).

Beat: wingless pig waits -> an 'otari'-tagged wing pair flies in and
docks on its back -> flap cycle -> anticipation dip -> liftoff, pig
exits. Thesis enacted: the gateway lends it wings.

v4 character: single-silhouette body, real eye, snout, paired ears,
curly tail - no wings. Wing = solid cartoon wing (scalloped trailing
edge), 3 rotation poses about a shoulder pivot.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, Polygon, FancyBboxPatch
from matplotlib.path import Path
import matplotlib.patches as mpatches
import matplotlib.transforms as mt
import numpy as np
import subprocess, os

BG = "#0D1B26"; TEAL = "#3FD9A8"; TXT = "#DFF4EE"
PINK = "#F5A0B5"; DPINK = "#E87E97"; DARK = "#1B2A38"
WING = "#EAFBF4"; WING_EC = "#9ED8C6"; OL = "#0A141C"

FPS = 15; N = 120
os.makedirs("anim_frames", exist_ok=True)

BODY_VERTS = [
    (4.6, 6.6),
    (3.4, 5.0), (3.6, 3.6), (4.4, 3.05),
    (4.6, 2.1), (5.0, 2.1),
    (5.4, 3.0), (6.4, 3.0),
    (6.6, 2.0), (7.0, 2.0),
    (7.4, 2.95), (8.6, 2.95),
    (8.8, 2.0), (9.2, 2.0),
    (9.6, 3.0), (10.2, 3.1),
    (10.4, 2.3), (10.8, 2.3),
    (11.0, 3.4),
    (12.4, 3.9), (13.6, 4.4), (13.8, 5.2),
    (14.4, 5.35), (14.55, 5.8),
    (14.2, 6.15), (13.5, 6.5),
    (13.2, 7.4), (12.4, 8.0), (11.4, 8.1),
    (10.4, 7.9), (9.4, 7.3),
    (8.0, 7.15), (6.0, 7.15), (4.6, 6.6),
]
WING_VERTS = [  # pivot at (0,0), swept up-right; scalloped trailing edge
    (0.0, 0.0), (1.2, 1.5), (2.6, 2.2), (4.2, 2.3),
    (4.9, 1.9), (4.2, 1.55),
    (4.6, 1.1), (3.9, 0.9),
    (4.1, 0.45), (3.3, 0.35),
    (2.6, -0.15), (1.4, -0.35), (0.0, 0.0),
]


def path_patch(verts, fc, z, lw=3.0, ec=OL, tr=None):
    # CURVE4 consumes verts in triples; leftovers -> CURVE3/LINETO or the
    # dangling control point spikes to the frame edge (2026-11-10 stray line)
    c4, rem = divmod(len(verts) - 2, 3)
    codes = ([Path.MOVETO] + [Path.CURVE4] * (c4 * 3)
             + ([Path.CURVE3] * 2 if rem == 2 else [Path.LINETO] * rem)
             + [Path.CLOSEPOLY])
    p = mpatches.PathPatch(Path(verts, codes), fc=fc, ec=ec, lw=lw,
                           zorder=z, joinstyle="round", capstyle="round")
    if tr is not None:
        p.set_transform(tr)
    return p


def draw_pig(ax, x, y, s=1.0, squash=1.0, tr_base=None):
    """v4 body at (x,y), scale s, vertical squash factor."""
    off = mt.Affine2D().translate(x, y).scale(s, s * squash)
    tr = off + (tr_base or ax.transData)
    ax.add_patch(path_patch(BODY_VERTS, PINK, 5, lw=3.5, tr=tr))
    # ears
    for pts in [[(10.3, 7.9), (9.7, 9.6), (11.4, 8.35)],
                [(11.5, 8.05), (11.7, 9.5), (12.6, 8.3)]]:
        pp = Polygon(pts, closed=True, fc=PINK, ec=OL, lw=3,
                     zorder=6, joinstyle="round"); pp.set_transform(tr)
        ax.add_patch(pp)
    ie = Polygon([(10.55, 8.15), (10.2, 9.1), (11.15, 8.3)], closed=True,
                 fc=DPINK, ec="none", zorder=6.5); ie.set_transform(tr)
    ax.add_patch(ie)
    # snout detail
    for ex, ey, w, h, c, z in [(13.9, 5.55, .28, .42, DARK, 7),
                               (14.28, 5.6, .24, .38, DARK, 7),
                               (12.2, 6.7, .42, .5, DARK, 7),
                               (12.3, 6.8, .13, .15, "#FFF", 7.5)]:
        e = Ellipse((ex, ey), w, h, fc=c, zorder=z); e.set_transform(tr)
        ax.add_patch(e)
    sm = mpatches.PathPatch(
        Path([(12.9, 4.6), (13.3, 4.35), (13.75, 4.45)],
             [Path.MOVETO, Path.CURVE3, Path.CURVE3]),
        fc="none", ec=DARK, lw=3, zorder=7, capstyle="round")
    sm.set_transform(tr); ax.add_patch(sm)
    # tail
    t = np.linspace(0, 3.2*np.pi, 120)
    xt = 3.4 - 0.075*t*np.cos(t+0.9); yt = 5.9 + 0.075*t*np.sin(t+0.9)
    pts = tr.transform(np.column_stack([xt, yt]))
    ax.plot(pts[:, 0], pts[:, 1], color=OL, lw=8, solid_capstyle="round",
            zorder=4.5)
    ax.plot(pts[:, 0], pts[:, 1], color=DPINK, lw=4.5,
            solid_capstyle="round", zorder=4.6)


def draw_wings(ax, px, py, s, rot, z=4.8, tr_base=None, flip=False):
    """One wing pair: near wing at rot deg, far wing offset, about pivot."""
    for drot, dz, c, sc in [(18, -0.05, WING_EC, 0.9), (0, 0, WING, 1.0)]:
        tr = (mt.Affine2D().rotate_deg(rot + drot)
              .scale(sc if not flip else -sc, sc).translate(px, py)
              .scale(s, s) + (tr_base or ax.transData))
        ax.add_patch(path_patch(WING_VERTS, c, z + dz, lw=2.8,
                                ec=OL, tr=tr))


FLAP = [-38, -8, 34, -8]   # 4-pose cycle


def flap_angle(frame_idx):
    return FLAP[frame_idx % 4]


def render(i):
    fig = plt.figure(figsize=(13, 6.5), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor(BG); ax.set_xlim(0, 26); ax.set_ylim(0, 13)
    ax.axis("off")

    # wordmark + tagline (present whole shot)
    ax.text(13, 5.4, "local-wilding", family="DejaVu Sans", fontsize=66,
            fontweight="bold", color=TEAL, ha="center", va="center")
    ax.text(13, 2.6, "pigs fly when a gateway lends them wings",
            family="DejaVu Sans", fontsize=18, color=TXT,
            ha="center", va="center")

    px, py = 4.5, 4.6      # pig origin (feet at py-~2.8)
    squash = 1.0; rot = 0.0
    show_wings = False; flap_i = 0; wing_pos = None

    if i < 25:
        # beat 1: pig waits, subtle idle blink handled by eye (skip)
        pass
    elif i < 45:
        # beat 2: wing pair flies in from right edge carrying 'otari' tag
        t = (i - 25) / 19.0
        te = 1 - (1 - t) ** 3              # ease-out
        wx = 27 - te * (27 - (px + 6.2))
        wy = 11.5 - te * (11.5 - (py + 5.6))
        wing_pos = (wx, wy)
        show_wings = True; rot = -15 * (1 - t)
        ax.text(wx + 1.5, wy + 3.6, "otari", family="DejaVu Sans",
                fontsize=17, fontweight="bold", color=TEAL,
                ha="center", va="center",
                bbox=dict(boxstyle="round,pad=0.35", fc="#123042",
                          ec=TEAL, lw=1.5))
        ax.plot([wx + 2.2, wx + 2.9], [wy + 3.0, wy + 2.0], color=TEAL,
                lw=2, alpha=0.7)
        flap_i = i // 4
    elif i < 60:
        # beat 3: docked - test flaps while grounded
        wing_pos = (px + 6.2, py + 5.6); show_wings = True
        flap_i = i // 2
        squash = 1.0 - 0.06 * abs(np.sin((i - 45) * 0.5))
    elif i < 68:
        # anticipation dip
        wing_pos = (px + 6.2, py + 5.6); show_wings = True
        squash = 0.88 - 0.04 * np.sin((i - 60) * 0.6)
        flap_i = i // 2
    else:
        # beat 4: liftoff - accelerate up+right, exit
        t = (i - 68) / 51.0
        px += (t ** 1.8) * 26
        py += (t ** 1.4) * 7.5
        squash = 1.0 + 0.1 * min(t * 4, 1)     # stretch on launch
        rot = -12 * min(t * 3, 1)              # nose-up climb
        wing_pos = (px + 6.2, py + 5.6); show_wings = True
        flap_i = i                          # max-rate flap on climb
        # speed streaks behind
        for sy in [-2.0, -0.5, 1.2]:
            ax.plot([px - 5.5 - 2.2 * t, px - 1.5],
                    [py + 3.6 + sy, py + 3.6 + sy], color=TEAL, lw=4,
                    alpha=max(0, 0.75 - t * 0.4), solid_capstyle="round",
                    zorder=3)

    if show_wings and wing_pos:
        trp = mt.Affine2D().rotate_deg_around(*wing_pos, 0)
        draw_wings(ax, wing_pos[0], wing_pos[1], 1.0,
                   flap_angle(flap_i), tr_base=ax.transData)
    draw_pig(ax, px, py, squash=squash, tr_base=ax.transData)

    # rotate whole pig during climb
    if i >= 68 and rot:
        pass  # (kept simple: stretch conveys launch)

    fig.savefig(f"anim_frames/a{i:03d}.png", facecolor=BG)
    plt.close(fig)


for i in range(N):
    render(i)

subprocess.run(["ffmpeg", "-y", "-v", "error", "-framerate", str(FPS),
                "-i", "anim_frames/a%03d.png", "-c:v", "libx264",
                "-pix_fmt", "yuv420p", "pig_anim_test.mp4"], check=True)
print("saved pig_anim_test.mp4")

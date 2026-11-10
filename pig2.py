"""Cute flat-design flying pig, done right - iterate until silhouette reads."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, Circle, FancyBboxPatch, Wedge, Polygon
from matplotlib.path import Path
import matplotlib.patches as mpatches
import numpy as np

PINK = "#F5A0B5"; DPINK = "#E87E97"; DARK = "#1B2A38"; WING = "#DFF4EE"; TEAL = "#3FD9A8"

fig, ax = plt.subplots(figsize=(8, 5), dpi=150)
ax.set_xlim(0, 16); ax.set_ylim(0, 10); ax.set_aspect("equal"); ax.axis("off")
fig.patch.set_alpha(0)

def ellipse(x, y, w, h, c, z, angle=0, ec="none", lw=0):
    e = Ellipse((x, y), w, h, angle=angle, fc=c, ec=ec, lw=lw, zorder=z)
    ax.add_patch(e); return e

# ---- wing (behind body) -------------------------------------------------
# sweeping wing: one smooth upper curve, scalloped feather underside
wing_verts = [
    (5.6, 6.4),                               # root
    (5.0, 8.8), (3.4, 10.0), (2.4, 9.5),      # sweep up-left to tip
    (2.7, 8.6), (3.0, 8.5), (3.3, 8.2),       # feather scallop 1
    (3.8, 7.3), (4.1, 7.2), (4.4, 6.9),       # feather scallop 2
    (4.9, 6.1), (5.2, 6.1), (5.6, 6.4),       # feather scallop 3 -> root
]
wing_codes = [Path.MOVETO] + [Path.CURVE4]*12
wing = mpatches.PathPatch(Path(wing_verts, wing_codes), fc=WING,
                          ec="#B9E4D8", lw=1.5, zorder=2)
ax.add_patch(wing)

# ---- body ---------------------------------------------------------------
ellipse(7.2, 5.0, 6.4, 4.0, PINK, 3)

# ---- legs (dangling, flight pose) ---------------------------------------
for lx, la in [(5.3, 20), (6.4, 10), (8.0, -10), (9.1, -20)]:
    ellipse(lx, 3.1, 0.9, 1.7, DPINK, 2.5, angle=la)

# ---- snout + face --------------------------------------------------------
ellipse(10.9, 5.3, 2.6, 2.4, PINK, 4)          # head mass
ellipse(11.6, 5.1, 1.7, 1.3, DPINK, 5)          # snout
ellipse(11.3, 5.15, 0.28, 0.42, DARK, 6)        # nostrils
ellipse(11.85, 5.15, 0.28, 0.42, DARK, 6)
# happy closed eye (arc)
th = np.linspace(0.15*np.pi, 0.85*np.pi, 40)
ax.plot(9.9+0.7*np.cos(th), 5.75+0.55*np.sin(th), color=DARK, lw=4,
        solid_capstyle="round", zorder=6)
# ear - rounded flap swept back along the head
ear_verts = [(9.1, 6.8), (8.6, 7.9), (7.8, 8.3), (7.6, 8.0),
             (8.4, 7.1), (9.4, 6.9), (9.1, 6.8)]
ear_codes = [Path.MOVETO] + [Path.CURVE4]*6
ax.add_patch(mpatches.PathPatch(Path(ear_verts, ear_codes),
             fc=DPINK, ec="none", zorder=4))
# blush
ellipse(9.6, 4.4, 1.0, 0.55, "#FBD3DE", 6)

# ---- curly tail ----------------------------------------------------------
t = np.linspace(0, 3.2*np.pi, 200)
ax.plot(4.0 + 0.09*t*np.cos(t+2.6), 6.0 + 0.09*t*np.sin(t+2.6),
        color=DPINK, lw=3.5, solid_capstyle="round", zorder=4)

# ---- flight streaks + clouds ---------------------------------------------
for sy, sx0, ln in [(2.2, 1.2, 2.6), (4.0, 0.6, 1.8), (7.8, 1.0, 2.2), (8.9, 3.0, 1.4)]:
    ax.plot([sx0, sx0+ln], [sy, sy], color=TEAL, lw=5, alpha=0.85,
            solid_capstyle="round", zorder=1)
ellipse(13.2, 8.2, 2.4, 1.1, "#FFFFFF", 1); ellipse(12.3, 8.6, 1.6, 1.0, "#FFFFFF", 1)

plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
plt.savefig("pig_v2.png", transparent=True)
print("saved pig_v2.png")

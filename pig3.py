"""Pig v3 - built on canon construction: separate head circle, snout oval,
paired ears, tapered legs with hooves, curly tapering tail."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, Polygon
from matplotlib.path import Path
import matplotlib.patches as mpatches
import numpy as np

PINK = "#F5A0B5"; DPINK = "#E87E97"; DARK = "#1B2A38"
WING = "#DFF4EE"; WING_EC = "#B9E4D8"; TEAL = "#3FD9A8"; HOOF = "#C95F7B"

fig, ax = plt.subplots(figsize=(8, 5), dpi=150)
ax.set_xlim(0, 16); ax.set_ylim(0, 10); ax.set_aspect("equal"); ax.axis("off")
fig.patch.set_alpha(0)

def ellipse(x, y, w, h, c, z, angle=0, ec="none", lw=0):
    e = Ellipse((x, y), w, h, angle=angle, fc=c, ec=ec, lw=lw, zorder=z)
    ax.add_patch(e); return e

def curve(verts, c, z, closed=True, ec="none", lw=0):
    # CURVE4 consumes verts in triples; leftovers -> CURVE3/LINETO or the
    # dangling control point spikes to the frame edge (2026-11-10 stray line)
    c4, rem = divmod(len(verts) - 1, 3)
    codes = [Path.MOVETO] + [Path.CURVE4] * (c4 * 3)
    codes += [Path.CURVE3] * 2 if rem == 2 else [Path.LINETO] * rem
    if closed:
        verts = verts + [verts[0]]; codes = codes + [Path.CLOSEPOLY]
    p = mpatches.PathPatch(Path(verts, codes), fc=c, ec=ec, lw=lw,
                           zorder=z)
    ax.add_patch(p); return p

# ---- far wing: tucked behind the near wing, peeking past its trailing edge ---
curve([(6.6, 6.8), (6.2, 8.9), (5.2, 9.5), (4.4, 9.3),
       (4.8, 8.4), (5.2, 7.6), (5.8, 7.0), (6.6, 6.8)],
      WING_EC, 2)
# ---- near wing: scalloped underside -----------------------------------------
curve([(5.6, 6.4), (5.0, 8.8), (3.6, 9.6), (2.8, 9.2),
       (2.7, 8.6), (3.0, 8.5), (3.3, 8.2),
       (3.8, 7.3), (4.1, 7.2), (4.4, 6.9),
       (4.9, 6.1), (5.2, 6.1), (5.6, 6.4)],
      WING, 2.5, ec=WING_EC, lw=1.5)

# ---- body --------------------------------------------------------------------
ellipse(7.0, 4.9, 6.0, 3.9, PINK, 3)

# ---- legs: short tapered stubs pitched back in flight -------------------------
def leg(x, y, w, h, ang, z=2.6):
    # tapered quad: wider at hip, hoof notch at tip
    dx = h * 0.5 * np.sin(np.radians(ang)); dy = -h * 0.5 * np.cos(np.radians(ang))
    pts = [(x - w/2, y), (x + w/2, y),
           (x + w*0.28 + dx, y + dy), (x - w*0.28 + dx, y + dy)]
    ax.add_patch(Polygon(pts, closed=True, fc=DPINK, ec="none", zorder=z))
    ellipse(x + dx, y + dy - 0.08, w*0.72, 0.5, HOOF, z + 0.1)

leg(5.4, 3.6, 1.0, 1.5, 28); leg(6.4, 3.4, 1.0, 1.7, 12)   # hind pair
leg(8.4, 3.4, 0.9, 1.5, -8); leg(9.2, 3.6, 0.9, 1.3, -22)  # front pair

# ---- head: SEPARATE circle overlapping body front -----------------------------
ellipse(10.7, 5.9, 3.0, 2.9, PINK, 4)

# ---- ears: PAIRED triangles on top of head ------------------------------------
ax.add_patch(Polygon([(9.6, 7.0), (8.9, 8.7), (10.6, 7.6)], closed=True,
             fc=DPINK, ec="none", zorder=4.5))
ax.add_patch(Polygon([(10.8, 7.2), (10.9, 8.6), (11.8, 7.5)], closed=True,
             fc=DPINK, ec="none", zorder=4.5))
# inner ear hints
ax.add_patch(Polygon([(9.75, 7.25), (9.3, 8.3), (10.3, 7.55)], closed=True,
             fc=PINK, ec="none", zorder=4.6))

# ---- snout: THE oval, front-lower of head -------------------------------------
ellipse(11.9, 5.4, 1.5, 1.15, DPINK, 5)
ellipse(11.62, 5.45, 0.24, 0.34, DARK, 6)
ellipse(12.08, 5.45, 0.24, 0.34, DARK, 6)

# ---- eye: happy closed arc ----------------------------------------------------
th = np.linspace(0.1*np.pi, 0.9*np.pi, 40)
ax.plot(10.05 + 0.55*np.cos(th), 6.35 + 0.45*np.sin(th), color=DARK, lw=4,
        solid_capstyle="round", zorder=6)
# cheek blush
ellipse(9.9, 5.0, 0.95, 0.55, "#FBD3DE", 6)

# ---- mouth hint under snout ---------------------------------------------------
ax.plot([11.4, 11.7], [4.75, 4.8], color=DARK, lw=2.5,
        solid_capstyle="round", zorder=6)

# ---- curly tapering tail -------------------------------------------------------
t = np.linspace(0, 3.4*np.pi, 220)
lw = np.linspace(4.0, 1.2, 220)
for i in range(len(t)-1):
    ax.plot([4.1 + 0.085*t[i]*np.cos(t[i]+2.6), 4.1 + 0.085*t[i+1]*np.cos(t[i+1]+2.6)],
            [5.6 + 0.085*t[i]*np.sin(t[i]+2.6), 5.6 + 0.085*t[i+1]*np.sin(t[i+1]+2.6)],
            color=DPINK, lw=lw[i], solid_capstyle="round", zorder=4)

# ---- flight streaks + cloud ----------------------------------------------------
for sy, sx0, ln in [(1.6, 0.8, 2.8), (3.6, 0.4, 2.0), (7.6, 0.8, 2.4), (8.7, 2.8, 1.6)]:
    ax.plot([sx0, sx0+ln], [sy, sy], color=TEAL, lw=5, alpha=0.85,
            solid_capstyle="round", zorder=1)
ellipse(13.6, 8.4, 2.4, 1.1, "#FFFFFF", 1); ellipse(12.6, 8.9, 1.6, 1.0, "#FFFFFF", 1)

plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
plt.savefig("pig_v3.png", transparent=True)
print("saved pig_v3.png")

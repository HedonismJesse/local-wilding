"""Three candidate mascot directions, one sheet - present before building.

1. ASCII: Joan Stark's canonical flying pig (jgs, 1997) - two flap frames
2. v4 outlined pig: single-silhouette body (connected), dark outline,
   dot eye, feathered wing
3. Typographic: no pig - wordmark + tagline only
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, Polygon, FancyBboxPatch
from matplotlib.path import Path
import matplotlib.patches as mpatches
import numpy as np

PINK = "#F5A0B5"; DPINK = "#E87E97"; DARK = "#1B2A38"
WING = "#DFF4EE"; WING_EC = "#9ED8C6"; TEAL = "#3FD9A8"; HOOF = "#C95F7B"
BG = "#0D1B26"; TXT = "#DFF4EE"

fig = plt.figure(figsize=(22, 8), dpi=100)
fig.patch.set_facecolor(BG)

# ================= PANEL 1: jgs ASCII pig, two frames ========================
ax1 = fig.add_axes([0.02, 0.08, 0.42, 0.82])
ax1.set_facecolor(BG); ax1.set_xlim(0, 2); ax1.set_ylim(0, 1); ax1.axis("off")

# jgs flying pig, right-facing. Frame A = wings swept back; B = wings raised.
FRAME_A = r""" _____  ____
)    /,----'
 \  //==--'
  \//==--'
 _//|Y.-~~~~-,
_/66  \        \_@
(")_   /   /    |
  '--'|| |-\   /
      //_/  /_/"""

FRAME_B = r""" _____  ____
`----,\    )
 `--==\\  /
  `--==\\/
 _//|Y.-~~~~-,
_/66  \        \_@
(")_   /   /    |
  '--'|| |-\   /
      //_/  /_/"""

for i, (frame, label) in enumerate([(FRAME_A, "frame 1"),
                                    (FRAME_B, "frame 2")]):
    x0 = i
    ax1.text(x0 + 0.02, 0.88, frame, family="Consolas", fontsize=13,
             color="#FFCF6B", va="top", ha="left",
             linespacing=1.15)
    ax1.text(x0 + 0.45, 0.04, label, family="Consolas", fontsize=11,
             color="#7FA8A0", ha="center")
ax1.text(1.0, 0.99, "ASCII - canon jgs pig, real 2-frame flap",
         color=TXT, fontsize=16, fontweight="bold", ha="center", va="top")

# ================= PANEL 2: v4 outlined pig ==================================
ax2 = fig.add_axes([0.47, 0.08, 0.28, 0.82])
ax2.set_facecolor(BG); ax2.set_xlim(0, 16); ax2.set_ylim(0, 10)
ax2.set_aspect("equal"); ax2.axis("off")
ax2.text(8, 9.7, "v4 outlined pig", color=TXT, fontsize=16,
         fontweight="bold", ha="center", va="top")

OL = "#0A141C"   # near-black outline

def P(verts, c, z, lw=3.0, ec=OL):
    codes = [Path.MOVETO] + [Path.CURVE4] * (len(verts) - 1)
    verts = verts + [verts[0]]; codes = codes + [Path.CLOSEPOLY]
    ax2.add_patch(mpatches.PathPatch(Path(verts, codes), fc=c, ec=ec,
                                     lw=lw, zorder=z,
                                     joinstyle="round", capstyle="round"))

# -- wings BEHIND body: two feathered wings as fans of tapered primaries --
def feather(base, tip, halfw, c, z):
    bx, by = base; tx, ty = tip
    dx, dy = tx - bx, ty - by
    L = np.hypot(dx, dy); ux, uy = dx / L, dy / L
    px, py = -uy, ux
    ax2.add_patch(Polygon([(bx + px*halfw, by + py*halfw),
                           (bx - px*halfw, by - py*halfw),
                           (tx - px*halfw*0.18, ty - py*halfw*0.18),
                           (tx + px*halfw*0.18, ty + py*halfw*0.18)],
                          closed=True, fc=c, ec=OL, lw=2.2,
                          zorder=z, joinstyle="round"))

def wing(base, angle_lo, angle_hi, r_lo, r_hi, n, halfw, c, z):
    """Fan of n feathers swept between two angles (deg), radial fan."""
    bx, by = base
    for a, r in zip(np.linspace(angle_lo, angle_hi, n),
                    np.linspace(r_lo, r_hi, n)):
        tip = (bx + r*np.cos(np.radians(a)), by + r*np.sin(np.radians(a)))
        feather((bx, by), tip, halfw, c, z)

# far wing: darker fan behind, same sweep
wing((7.0, 6.0), 155, 120, 4.0, 3.2, 4, 0.30, WING_EC, 2)
# near wing: all feathers swept up-back, tips fanned by radius
wing((6.4, 5.8), 152, 118, 5.2, 4.0, 6, 0.40, WING, 2.5)

# -- single-silhouette body: body+head+legs+snout-bump in ONE path ----------
verts = [
    (4.6, 6.6),                              # top-back
    (3.4, 5.0), (3.6, 3.6), (4.4, 3.05),     # rump down to hind leg
    (4.6, 2.1), (5.0, 2.1),                  # hind hoof
    (5.4, 3.0), (6.4, 3.0),                  # belly rise
    (6.6, 2.0), (7.0, 2.0),                  # hind-front hoof
    (7.4, 2.95), (8.6, 2.95),                # belly
    (8.8, 2.0), (9.2, 2.0),                  # front hoof 1
    (9.6, 3.0), (10.2, 3.1),                 # chest
    (10.4, 2.3), (10.8, 2.3),                # front hoof 2
    (11.0, 3.4),                             # neck
    (12.4, 3.9), (13.6, 4.4), (13.8, 5.2),   # jaw up to snout
    (14.4, 5.35), (14.55, 5.8),              # snout bump
    (14.2, 6.15), (13.5, 6.5),               # snout top
    (13.2, 7.4), (12.4, 8.0), (11.4, 8.1),   # forehead
    (10.4, 7.9), (9.4, 7.3),                 # back of skull
    (8.0, 7.15), (6.0, 7.15), (4.6, 6.6),    # back to top-back
]
P(verts, PINK, 3, lw=3.5)

# ears: outlined triangles attached to skull
ax2.add_patch(Polygon([(10.3, 7.9), (9.7, 9.6), (11.4, 8.35)], closed=True,
                      fc=PINK, ec=OL, lw=3, zorder=4, joinstyle="round"))
ax2.add_patch(Polygon([(10.55, 8.15), (10.2, 9.1), (11.15, 8.3)],
                      closed=True, fc=DPINK, ec="none", zorder=4.5))
ax2.add_patch(Polygon([(11.5, 8.05), (11.7, 9.5), (12.6, 8.3)], closed=True,
                      fc=PINK, ec=OL, lw=3, zorder=4, joinstyle="round"))

# snout face detail: nostril pair + smile line (inside silhouette)
ax2.add_patch(Ellipse((13.9, 5.55), 0.28, 0.42, fc=DARK, zorder=6))
ax2.add_patch(Ellipse((14.28, 5.6), 0.24, 0.38, fc=DARK, zorder=6))
p = Path([(12.9, 4.6), (13.3, 4.35), (13.75, 4.45)],
         [Path.MOVETO, Path.CURVE3, Path.CURVE3])
ax2.add_patch(mpatches.PathPatch(p, fc="none", ec=DARK, lw=3, zorder=6,
                                 capstyle="round"))

# REAL eye: dark dot + tiny highlight
ax2.add_patch(Ellipse((12.2, 6.7), 0.42, 0.5, fc=DARK, zorder=6))
ax2.add_patch(Ellipse((12.3, 6.8), 0.13, 0.15, fc="#FFFFFF", zorder=6.5))

# curly tail: outlined spiral stroke
t = np.linspace(0, 3.2*np.pi, 200)
xt = 3.4 - 0.075*t*np.cos(t+0.9); yt = 5.9 + 0.075*t*np.sin(t+0.9)
ax2.plot(xt, yt, color=OL, lw=8, solid_capstyle="round", zorder=3.9)
ax2.plot(xt, yt, color=DPINK, lw=4.5, solid_capstyle="round", zorder=4)

# motion streaks
for sy, sx0, ln in [(2.2, 0.4, 2.2), (8.4, 0.6, 1.8)]:
    ax2.plot([sx0, sx0+ln], [sy, sy], color=TEAL, lw=5, alpha=0.8,
             solid_capstyle="round", zorder=1)

# ================= PANEL 3: typographic ======================================
ax3 = fig.add_axes([0.78, 0.08, 0.21, 0.82])
ax3.set_facecolor(BG); ax3.set_xlim(0, 10); ax3.set_ylim(0, 10)
ax3.axis("off")
ax3.text(5, 9.5, "typographic", color=TXT, fontsize=16,
         fontweight="bold", ha="center", va="top")
ax3.text(5, 6.8, "local-\nwilding", color=TEAL, fontsize=26,
         fontweight="bold", ha="center", va="center",
         family="DejaVu Sans")
ax3.text(5, 4.6, "pigs fly when a\ngateway lends\nthem wings",
         color=TXT, fontsize=12, ha="center", va="center")
ax3.text(5, 2.8, "... when pigs fly ...", color="#FFCF6B", fontsize=10,
         ha="center", va="center", family="Consolas", style="italic")

plt.savefig("pig_compare.png", facecolor=BG)
print("saved pig_compare.png")

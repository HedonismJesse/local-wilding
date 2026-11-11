# provenance: author=devin; created=2026-11-10; source=plan
#   ai-hub Artifacts/plans/repo/ART_SPHERE_CHILD_SPHERES_2026-11-10.md
#   (art:construction-canon + lazy-flight animatic v2);
#   purpose=fat lazy pig builder - keyframe poses rest/notice/flee/fly
#   for the otari-wings animatic; intent=production
"""pig_lazy — the fat lazy pig construction (canon/pig_lazy.json).

Poses follow pose-to-pose canon (each key drawn, not morphed):
    rest   — lying, belly squashed on ground, chin down, eyes closed
    notice — body still lying (lazy: only the head reacts), head up,
             ears perked, eyes wide
    flee   — standing, faces LEFT (away from the right-side wings),
             legs mid-cycle, ears/tail streaming
    fly    — pitched nose-up, dead-weight leg dangle, wings attached

    python pig_lazy.py            # pose strip preview
    candidate_sheet.py --builder pig_lazy:draw_lazy_pig ...
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, Polygon
from matplotlib.path import Path
import matplotlib.patches as mpatches
import matplotlib.transforms as mt
import numpy as np

PINK = "#F5A0B5"; DPINK = "#E87E97"; DARK = "#1B2A38"
WING = "#DFF4EE"; WING_EC = "#B9E4D8"; HOOF = "#C95F7B"
BLUSH = "#FBD3DE"; BELLY = "#F7B4C4"


def _codes(n_movable):
    c4, rem = divmod(n_movable, 3)
    codes = [Path.CURVE4] * (c4 * 3)
    codes += [Path.CURVE3] * 2 if rem == 2 else [Path.LINETO] * rem
    return codes


def draw_lazy_pig(ax, pose="rest", belly=1.25, head_ratio=1.0,
                  ear="flop", snout=1.0, outline=False, phase=0.0,
                  wings=False, facing=1):
    """facing: +1 head right (rest/notice/fly), -1 head left (flee)."""
    ax.set_xlim(0, 16); ax.set_ylim(0, 10); ax.set_aspect("equal")
    ax.axis("off")
    # facing=-1 mirrors about x=8 so flee runs left, away from wings
    tr = (mt.Affine2D().scale(-1, 1).translate(16, 0)
          + ax.transData) if facing < 0 else ax.transData

    ol_ec = DARK if outline else "none"
    ol_lw = 2.4 if outline else 0

    def add(p):
        p.set_transform(tr); ax.add_patch(p); return p

    def curve(verts, c, z, ec="none", lw=0):
        codes = [Path.MOVETO] + _codes(len(verts) - 1)
        add(mpatches.PathPatch(Path(verts + [verts[0]],
                                 codes + [Path.CLOSEPOLY]),
                               fc=c, ec=ec, lw=lw, zorder=z))

    def ellipse(x, y, w, h, c, z, angle=0, ec="none", lw=0):
        add(Ellipse((x, y), w, h, angle=angle, fc=c, ec=ec, lw=lw,
                    zorder=z))

    def poly(pts, c, z, ec="none", lw=0):
        add(Polygon(pts, closed=True, fc=c, ec=ec, lw=lw, zorder=z))

    def line(pts, c, z, lw=3):
        xs, ys = zip(*pts)
        (tx, ty) = tr.transform(list(zip(xs, ys))).T \
            if tr is not ax.transData else (np.array(xs), np.array(ys))
        ax.plot(tx, ty, color=c, lw=lw, solid_capstyle="round", zorder=z)

    def leg(x, y, w, h, ang, z=2.6):
        dx = h * 0.5 * np.sin(np.radians(ang))
        dy = -h * 0.5 * np.cos(np.radians(ang))
        poly([(x - w/2, y), (x + w/2, y),
              (x + w*0.30 + dx, y + dy), (x - w*0.30 + dx, y + dy)],
             DPINK, z, ec=ol_ec, lw=ol_lw * 0.7)
        ellipse(x + dx, y + dy - 0.07, w*0.74, 0.45, HOOF, z + 0.1)

    def ear_set(hx, hy, mode, z):
        if mode == "flop":
            curve([(hx - 0.4, hy + 1.35), (hx - 1.15, hy + 2.15),
                   (hx - 1.7, hy + 2.0), (hx - 1.55, hy + 1.4),
                   (hx - 0.9, hy + 1.0), (hx - 0.4, hy + 1.35)],
                  DPINK, z, ec=ol_ec, lw=ol_lw)
            curve([(hx + 0.45, hy + 1.4), (hx + 1.0, hy + 2.2),
                   (hx + 1.5, hy + 2.0), (hx + 1.3, hy + 1.35),
                   (hx + 0.8, hy + 1.1), (hx + 0.45, hy + 1.4)],
                  DPINK, z - 0.05, ec=ol_ec, lw=ol_lw)
        elif mode == "droop":          # lazy ear hanging over the face
            curve([(hx - 0.5, hy + 1.5), (hx - 1.2, hy + 1.7),
                   (hx - 1.5, hy + 1.0), (hx - 1.15, hy + 0.5),
                   (hx - 0.7, hy + 1.0), (hx - 0.5, hy + 1.5)],
                  DPINK, z, ec=ol_ec, lw=ol_lw)
            curve([(hx + 0.4, hy + 1.55), (hx + 1.05, hy + 1.8),
                   (hx + 1.3, hy + 1.15), (hx + 0.95, hy + 0.75),
                   (hx + 0.6, hy + 1.1), (hx + 0.4, hy + 1.55)],
                  DPINK, z - 0.05, ec=ol_ec, lw=ol_lw)
        elif mode == "stream":         # swept back by speed
            curve([(hx - 0.2, hy + 1.3), (hx + 1.2, hy + 2.2),
                   (hx + 1.9, hy + 1.9), (hx + 1.2, hy + 1.2),
                   (hx + 0.4, hy + 0.9), (hx - 0.2, hy + 1.3)],
                  DPINK, z, ec=ol_ec, lw=ol_lw)
            curve([(hx + 0.1, hy + 1.0), (hx + 1.35, hy + 1.55),
                   (hx + 1.85, hy + 1.15), (hx + 1.2, hy + 0.7),
                   (hx + 0.4, hy + 0.55), (hx + 0.1, hy + 1.0)],
                  DPINK, z - 0.05, ec=ol_ec, lw=ol_lw)
        else:                          # tri perked
            poly([(hx - 0.75, hy + 1.2), (hx - 1.35, hy + 2.7),
                  (hx + 0.1, hy + 1.7)], DPINK, z, ec=ol_ec, lw=ol_lw)
            poly([(hx + 0.45, hy + 1.35), (hx + 0.6, hy + 2.6),
                  (hx + 1.35, hy + 1.6)], DPINK, z, ec=ol_ec, lw=ol_lw)
            poly([(hx - 0.62, hy + 1.45), (hx - 1.1, hy + 2.35),
                  (hx - 0.05, hy + 1.65)], PINK, z + 0.1)

    def snout_set(sx, sy, s, z):
        ellipse(sx, sy, 1.5*s, 1.15*s, DPINK, z, ec=ol_ec, lw=ol_lw)
        ellipse(sx - 0.28*s, sy + 0.05, 0.24, 0.34, DARK, z + 1)
        ellipse(sx + 0.18*s, sy + 0.05, 0.24, 0.34, DARK, z + 1)

    def tail_curl(tx, ty, s, z):
        t = np.linspace(0, 3.2*np.pi, 160)
        lws = np.linspace(4.2, 1.2, 160)
        xs = tx + s*0.085*t*np.cos(t + 2.4)
        ys = ty + s*0.085*t*np.sin(t + 2.4)
        pts = tr.transform(np.column_stack([xs, ys])) \
            if tr is not ax.transData else np.column_stack([xs, ys])
        for i in range(len(t) - 1):
            if outline:
                ax.plot(pts[i:i+2, 0], pts[i:i+2, 1], color=DARK,
                        lw=lws[i] + 2.2, solid_capstyle="round",
                        zorder=z - 0.1)
            ax.plot(pts[i:i+2, 0], pts[i:i+2, 1], color=DPINK,
                    lw=lws[i], solid_capstyle="round", zorder=z)

    def wing_pair(wx, wy, rot, z):
        for drot, dz, c, sc in [(18, -0.05, WING_EC, 0.9),
                                (0, 0, WING, 1.0)]:
            wtr = (mt.Affine2D().rotate_deg(rot + drot).scale(sc)
                   .translate(wx, wy) + tr)
            v = [(0.0, 0.0), (1.2, 1.5), (2.6, 2.2), (4.2, 2.3),
                 (4.9, 1.9), (4.2, 1.55), (4.6, 1.1), (3.9, 0.9),
                 (4.1, 0.45), (3.3, 0.35), (2.6, -0.15), (1.4, -0.35)]
            codes = [Path.MOVETO] + _codes(len(v) - 1)
            ax.add_patch(mpatches.PathPatch(
                Path(v + [v[0]], codes + [Path.CLOSEPOLY]),
                fc=c, ec=ol_ec if outline else WING_EC,
                lw=2.0 if outline else 1.4, zorder=z + dz,
                joinstyle="round", transform=wtr))

    # ------------------------------------------------ poses
    if pose in ("rest", "notice"):
        alert = pose == "notice"
        # lying body: belly squashed flat on the ground (weight)
        ellipse(7.2, 3.15, 8.4 * belly, 3.25, PINK, 3,
                ec=ol_ec, lw=ol_lw)
        ellipse(9.3, 2.35, 4.6 * belly, 1.7, BELLY, 2.9)   # gut spread
        # tucked hooves peeking out
        ellipse(3.4, 1.85, 0.95, 0.5, HOOF, 3.2)
        ellipse(10.7, 1.75, 0.9, 0.45, HOOF, 3.2)
        ellipse(11.5, 1.8, 0.85, 0.45, HOOF, 3.2)
        tail_curl(2.7, 3.9, 1.0, 4)
        if alert:
            # head up, wide eye, perked ears - only the head moved
            hx, hy = 11.9, 5.4
            ellipse(hx, hy, 3.0 * head_ratio, 2.9 * head_ratio, PINK, 4,
                    ec=ol_ec, lw=ol_lw)
            ear_set(hx, hy + 0.4, "tri", 4.5)   # perked = startle grammar
            ellipse(hx - 0.55, hy + 0.45, 0.85, 0.95, "#FFFFFF", 6)
            ellipse(hx - 0.45, hy + 0.4, 0.4, 0.5, DARK, 6.5)
            ellipse(hx - 0.38, hy + 0.55, 0.14, 0.18, "#FFFFFF", 6.6)
            snout_set(hx + 1.35, hy - 0.5, snout, 5)
            # startle mouth: small open o
            ellipse(hx + 0.9, hy - 1.15, 0.5, 0.35, DARK, 6)
            line([(hx - 0.75, hy + 1.15), (hx - 0.35, hy + 1.3)],
                 DARK, 6, lw=2.5)                      # raised brow
        else:
            # chin on ground, closed sleepy eye, drooped ear
            hx, hy = 11.6, 4.15
            ellipse(hx, hy, 3.1 * head_ratio, 2.7 * head_ratio, PINK, 4,
                    ec=ol_ec, lw=ol_lw)
            ear_set(hx, hy + 0.15, "droop", 4.5)
            th = np.linspace(1.15*np.pi, 1.85*np.pi, 40)
            xs = hx - 0.75 + 0.5*np.cos(th)
            ys = hy + 0.25 + 0.38*np.sin(th)
            pts = tr.transform(np.column_stack([xs, ys])) \
                if tr is not ax.transData else np.column_stack([xs, ys])
            ax.plot(pts[:, 0], pts[:, 1], color=DARK, lw=4,
                    solid_capstyle="round", zorder=6)
            snout_set(hx + 1.5, hy - 0.15, snout, 5)
            ellipse(hx - 0.9, hy - 0.75, 0.9, 0.5, BLUSH, 6)
            # snore z's - secondary action tell
            for i, (zx, zy, zs) in enumerate(
                    [(hx + 2.3, hy + 1.5, 26), (hx + 3.1, hy + 2.6, 34)]):
                (tx,), (ty,) = tr.transform([(zx, zy)]).T \
                    if tr is not ax.transData else ([zx], [zy])
                ax.text(tx, ty, "z", fontsize=zs, color=DARK,
                        fontweight="bold", style="italic",
                        ha="center", va="center", zorder=7,
                        alpha=0.85 - i * 0.25)
    elif pose == "flee":
        # standing run; the builder draws facing-right then mirrors when
        # facing<0 so the run goes AWAY from the right-side wings
        ellipse(7.6, 4.5, 7.6 * belly, 3.7, PINK, 3, ec=ol_ec, lw=ol_lw)
        ellipse(9.4, 3.4, 3.9 * belly, 1.5, BELLY, 2.9)
        p = phase * 2 * np.pi
        leg(5.4, 3.1, 0.95, 1.7, 38 * np.sin(p))
        leg(6.6, 3.0, 0.95, 1.7, 38 * np.sin(p + np.pi))
        leg(9.4, 3.0, 0.9, 1.6, 42 * np.sin(p + np.pi))
        leg(10.4, 3.15, 0.9, 1.5, 42 * np.sin(p))
        tail_curl(3.0, 5.2, 0.85, 4)
        hx, hy = 11.4, 5.6
        ellipse(hx, hy, 3.0 * head_ratio, 2.8 * head_ratio, PINK, 4,
                ec=ol_ec, lw=ol_lw)
        ear_set(hx, hy + 0.35, "stream", 4.5)
        ellipse(hx - 0.5, hy + 0.35, 0.8, 0.9, "#FFFFFF", 6)
        ellipse(hx - 0.42, hy + 0.3, 0.38, 0.48, DARK, 6.5)
        ellipse(hx - 0.35, hy + 0.45, 0.13, 0.16, "#FFFFFF", 6.6)
        snout_set(hx + 1.35, hy - 0.45, snout, 5)
        line([(hx - 0.85, hy + 1.25), (hx - 0.3, hy + 1.05)],
             DARK, 6, lw=2.5)                          # worried brow
        ellipse(hx + 0.75, hy - 1.2, 0.45, 0.3, DARK, 6)
    elif pose == "fly":
        # pitched nose-up carried pose: rotate the whole pig ~-16 deg
        prot = mt.Affine2D().rotate_deg_around(7.6, 4.6, -14) + tr
        tr_save = tr
        tr = prot
        ellipse(7.6, 4.6, 7.6 * belly, 3.8, PINK, 3, ec=ol_ec, lw=ol_lw)
        ellipse(8.6, 3.3, 4.4 * belly, 1.9, BELLY, 2.9)
        # dead-weight dangle: legs hang limp, slight spread
        leg(5.3, 3.2, 0.95, 1.6, 14); leg(6.6, 3.0, 0.95, 1.7, 3)
        leg(9.5, 3.0, 0.9, 1.6, -6); leg(10.5, 3.25, 0.9, 1.4, -18)
        tail_curl(3.0, 5.6, 0.9, 4)
        hx, hy = 11.5, 5.7
        ellipse(hx, hy, 3.0 * head_ratio, 2.85 * head_ratio, PINK, 4,
                ec=ol_ec, lw=ol_lw)
        ear_set(hx, hy + 0.35, "droop", 4.5)
        ellipse(hx - 0.5, hy + 0.35, 0.8, 0.9, "#FFFFFF", 6)
        ellipse(hx - 0.4, hy + 0.3, 0.38, 0.48, DARK, 6.5)
        ellipse(hx - 0.33, hy + 0.45, 0.13, 0.16, "#FFFFFF", 6.6)
        snout_set(hx + 1.35, hy - 0.45, snout, 5)
        ellipse(hx + 0.8, hy - 1.2, 0.45, 0.32, DARK, 6)
        if wings:
            wing_pair(6.8, 6.9, -30 + 40 * np.sin(phase * 2 * np.pi),
                      2.4)
        tr = tr_save
    else:
        raise ValueError(f"unknown pose {pose!r}")


POSES = ["rest", "notice", "flee", "fly"]

if __name__ == "__main__":
    fig, axes = plt.subplots(1, 4, figsize=(20, 6), dpi=100)
    fig.patch.set_facecolor("#0D1B26")
    for ax, ps in zip(axes, POSES):
        ax.set_facecolor("#0D1B26")
        draw_lazy_pig(ax, pose=ps, wings=(ps == "fly"), phase=0.3,
                      facing=(-1 if ps == "flee" else 1))
        ax.set_title(ps, color="#DFF4EE", fontsize=20, pad=12,
                     fontweight="bold")
    plt.subplots_adjust(left=0.01, right=0.99, top=0.9, bottom=0.01,
                        wspace=0.05)
    plt.savefig("pig_lazy_poses.png", facecolor="#0D1B26")
    print("saved pig_lazy_poses.png")

# provenance: author=devin; created=2026-11-10; source=reference
#   canon/refs/refs.json (waddles, operator-picked anchor) +
#   ai-hub Artifacts/plans/repo/ART_SPHERE_CHILD_SPHERES_2026-11-10.md
#   (art:reference-canon); purpose=waddles-grammar lazy pig builder -
#   keyframe poses rest/notice/flee/fly for the otari-wings animatic;
#   intent=production
"""pig_w2 — the waddles-grammar pig (canon/pig_w2.json).

Reference: waddles (Gravity Falls), operator-picked anchor
2026-11-10. Signature elements carried:

    loaf body      head merges INTO the body - no separate head
                   ellipse (the blob lesson inverted: one potato, but
                   the face hangs ON it, not in it)
    snout droop    big oval hung LOW on the front, nostrils at the
                   droop end
    floppy ear     a petal flap folded over the forehead
    half-lid eye   small, sleepy - lazy reads through the eyelid
    stub legs      tiny nubs, mostly hidden under the body
    thin outline   waddles register is thin-line flat fill
    spot patches   darker pink marks on the back
    curled tail

Poses (pose-to-pose, each key drawn):
    rest   loaf on ground, chin down, closed eye, ear flopped, z's
    notice loaf still down - only the face lifts (lazy grammar)
    flee   on stub legs, faces LEFT away from the wings, ear streams
    fly    nose-up, legs dangle, wings attached

    python pig_w2.py            # pose strip preview
    candidate_sheet.py --builder pig_w2:draw_w2_pig \
        --refs canon/refs/refs.json --ref-pick waddles ...
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, Polygon
from matplotlib.path import Path
import matplotlib.patches as mpatches
import matplotlib.transforms as mt
import numpy as np

PINK = "#F4A8A0"; PATCH = "#E08F86"; DARK = "#2E2E38"
WING = "#DFF4EE"; WING_EC = "#B9E4D8"; HOOF = "#46464F"
BLUSH = "#FBD3DE"; BELLY = "#F7C0B4"


def _codes(n_movable):
    c4, rem = divmod(n_movable, 3)
    codes = [Path.CURVE4] * (c4 * 3)
    codes += [Path.CURVE3] * 2 if rem == 2 else [Path.LINETO] * rem
    return codes


def draw_w2_pig(ax, pose="rest", belly=1.0, droop=1.0, ear="flop",
                outline=True, phase=0.0, wings=False, facing=1,
                spots=True):
    """facing: +1 head right (rest/notice/fly), -1 head left (flee).
    droop scales how far the snout hangs (waddles signature)."""
    ax.set_xlim(0, 16); ax.set_ylim(0, 10); ax.set_aspect("equal")
    ax.axis("off")
    tr = (mt.Affine2D().scale(-1, 1).translate(16, 0)
          + ax.transData) if facing < 0 else ax.transData

    ec = DARK if outline else "none"
    lw = 5.0 if outline else 0          # waddles = visible line

    def add(p):
        p.set_transform(tr); ax.add_patch(p); return p

    def curve(verts, c, z, e=ec, w=lw):
        codes = [Path.MOVETO] + _codes(len(verts) - 1)
        add(mpatches.PathPatch(Path(verts + [verts[0]],
                                 codes + [Path.CLOSEPOLY]),
                               fc=c, ec=e, lw=w, zorder=z,
                               joinstyle="round"))

    def ellipse(x, y, w, h, c, z, angle=0, e="none", ww=0):
        add(Ellipse((x, y), w, h, angle=angle, fc=c, ec=e, lw=ww,
                    zorder=z))

    def poly(pts, c, z, e=ec, w=lw):
        add(Polygon(pts, closed=True, fc=c, ec=e, lw=w, zorder=z))

    def line(pts, c, z, w=2.5):
        xs, ys = zip(*pts)
        (tx, ty) = tr.transform(list(zip(xs, ys))).T \
            if tr is not ax.transData else (np.array(xs), np.array(ys))
        ax.plot(tx, ty, color=c, lw=w, solid_capstyle="round",
                zorder=z)

    def stub_leg(x, y, ang, z=2.6):
        """Tiny nub + dark hoof - waddles legs barely clear the body."""
        w, h = 0.62, 0.95
        dx = h * 0.45 * np.sin(np.radians(ang))
        dy = -h * np.cos(np.radians(ang))
        poly([(x - w/2, y), (x + w/2, y),
              (x + w*0.25 + dx, y + dy), (x - w*0.25 + dx, y + dy)],
             PINK, z)
        ellipse(x + dx, y + dy - 0.05, w*0.8, 0.5, HOOF, z + 0.1)

    def ear(bx, by, mode, z):
        """The flop-over-forehead petal - waddles signature."""
        if mode == "flop":       # folded forward over the face
            curve([(bx, by), (bx + 0.9, by + 1.0), (bx + 2.0, by + 0.55),
                   (bx + 1.8, by - 0.55), (bx + 0.6, by - 0.35)],
                  PINK, z)
            curve([(bx - 0.15, by + 0.1), (bx - 0.6, by + 0.7),
                   (bx - 0.15, by + 0.55)], PINK, z - 0.05)   # rear hint
        elif mode == "lift":     # half-perked: still floppy but raised
            curve([(bx, by), (bx + 0.7, by + 1.4), (bx + 1.9, by + 1.25),
                   (bx + 1.6, by + 0.25), (bx + 0.5, by + 0.1)],
                  PINK, z)
            curve([(bx - 0.15, by + 0.15), (bx - 0.5, by + 0.9),
                   (bx - 0.05, by + 0.75)], PINK, z - 0.05)
        elif mode == "stream":   # swept back by speed
            curve([(bx + 0.6, by), (bx - 0.5, by + 1.0),
                   (bx - 1.9, by + 0.7), (bx - 1.2, by - 0.1),
                   (bx - 0.1, by - 0.35)], PINK, z)
            curve([(bx + 0.3, by - 0.15), (bx - 0.9, by + 0.4),
                   (bx - 0.4, by + 0.0)], PINK, z - 0.05)
        else:                    # droop (air): hangs limp forward
            curve([(bx, by), (bx + 0.8, by + 0.85), (bx + 1.6, by + 0.4),
                   (bx + 1.3, by - 0.5), (bx + 0.4, by - 0.45)],
                  PINK, z)

    def snout(sx, sy, s, z):
        """Droopy oval hung low - big like waddles, nostrils at droop end."""
        ellipse(sx, sy, 2.3*s, 1.9*s, PINK, z, e=ec, ww=lw)
        ellipse(sx - 0.42*s, sy - 0.22*s, 0.44, 0.62, DARK, z + 1,
                angle=-12)
        ellipse(sx + 0.42*s, sy - 0.22*s, 0.44, 0.62, DARK, z + 1,
                angle=12)

    def eye(ex, ey, mode, z):
        if mode == "closed":     # sleepy arc curving down
            th = np.linspace(1.15*np.pi, 1.85*np.pi, 40)
            xs = ex + 0.5*np.cos(th); ys = ey + 0.4*np.sin(th)
            pts = tr.transform(np.column_stack([xs, ys])) \
                if tr is not ax.transData else np.column_stack([xs, ys])
            ax.plot(pts[:, 0], pts[:, 1], color=DARK, lw=3.4,
                    solid_capstyle="round", zorder=z)
        elif mode == "half":     # waddles sleepy - tiny dot + lid
            ellipse(ex, ey, 0.3, 0.36, DARK, z)
            line([(ex - 0.2, ey + 0.18), (ex + 0.2, ey + 0.14)],
                 DARK, z + 0.1, w=2.0)
        else:                    # wide - still waddles-tiny, just open
            ellipse(ex, ey, 0.4, 0.5, "#FFFFFF", z)
            ellipse(ex + 0.02, ey - 0.02, 0.26, 0.34, DARK, z + 0.1)
            ellipse(ex + 0.07, ey + 0.08, 0.08, 0.1, "#FFFFFF", z + 0.2)

    def tail_curl(tx, ty, s, z):
        t = np.linspace(0, 3.0*np.pi, 150)
        lws = np.linspace(3.6, 1.1, 150)
        xs = tx + s*0.08*t*np.cos(t + 2.4)
        ys = ty + s*0.08*t*np.sin(t + 2.4)
        pts = tr.transform(np.column_stack([xs, ys])) \
            if tr is not ax.transData else np.column_stack([xs, ys])
        for i in range(len(t) - 1):
            if outline:
                ax.plot(pts[i:i+2, 0], pts[i:i+2, 1], color=DARK,
                        lw=lws[i] + 3.0, solid_capstyle="round",
                        zorder=z - 0.1)
            ax.plot(pts[i:i+2, 0], pts[i:i+2, 1], color=PINK,
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
                fc=c, ec=WING_EC, lw=3.0, zorder=z + dz,
                joinstyle="round", transform=wtr))

    def loaf(cx, cy, w, h, z):
        """The potato - ONE mass, face hangs on the front."""
        ellipse(cx, cy, w * belly, h, PINK, z, e=ec, ww=lw)
        # jowl bulge: front-bottom of the loaf reads as chin fat
        ellipse(cx + w*0.38, cy - h*0.22, w*0.30, h*0.62, PINK, z - 0.05)
        if spots:
            ellipse(cx - w*0.14, cy + h*0.22, w*0.30, h*0.42, PATCH,
                    z + 0.05, angle=-18)
            ellipse(cx + w*0.06, cy - h*0.30, w*0.16, h*0.20, PATCH,
                    z + 0.05, angle=10)

    # ------------------------------------------------ poses
    if pose in ("rest", "notice"):
        alert = pose == "notice"
        # ground shadow
        ellipse(7.8, 1.75, 8.6, 0.7, "#00000022" if not outline
                else "#3A3A44", 1.5)
        loaf(7.6, 3.2, 9.8, 2.9, 3)   # rest = squashed blob
        # tucked stub legs peeking out
        stub_leg(4.0, 2.05, -8); stub_leg(10.6, 1.95, 10)
        tail_curl(2.7, 4.0, 1.0, 4)
        if alert:
            # only the face lifts - body stays down (lazy grammar)
            eye(10.85, 4.35, "wide", 6)
            ear(10.3, 5.0, "lift", 5)
            snout(12.15, 3.35, 1.0 * droop, 5)
            line([(10.5, 5.15), (10.95, 5.3)], DARK, 6, w=2.2)
            ellipse(12.0, 2.6, 0.4, 0.28, DARK, 6)    # startle o
        else:
            eye(10.85, 4.3, "closed", 6)
            ear(10.3, 5.0, "flop", 5)
            snout(12.2, 2.8, 1.1 * droop, 5)         # squashed on ground
            ellipse(10.3, 3.6, 0.8, 0.45, BLUSH, 6)
            for i, (zx, zy, zs) in enumerate(
                    [(12.4, 5.6, 24), (13.2, 6.6, 32)]):
                (tx,), (ty,) = tr.transform([(zx, zy)]).T \
                    if tr is not ax.transData else ([zx], [zy])
                ax.text(tx, ty, "z", fontsize=zs, color=DARK,
                        fontweight="bold", style="italic",
                        ha="center", va="center", zorder=7,
                        alpha=0.85 - i * 0.25)
    elif pose == "flee":
        # drawn facing right; facing=-1 mirrors so the run goes LEFT
        loaf(7.6, 4.15, 9.0, 3.3, 3)
        p = phase * 2 * np.pi
        stub_leg(4.4, 2.75, 30 * np.sin(p + np.pi))
        stub_leg(5.2, 2.7, 30 * np.sin(p))
        stub_leg(10.3, 2.7, 32 * np.sin(p))
        stub_leg(11.1, 2.75, 32 * np.sin(p + np.pi))
        tail_curl(2.8, 5.0, 0.9, 4)
        eye(10.95, 4.75, "wide", 6)
        ear(10.5, 5.3, "stream", 5)
        snout(12.2, 3.85, 0.95 * droop, 5)
        line([(10.6, 5.6), (11.05, 5.35)], DARK, 6, w=2.2)   # worried
        ellipse(12.0, 3.1, 0.4, 0.3, DARK, 6)                # open mouth
    elif pose == "fly":
        prot = mt.Affine2D().rotate_deg_around(7.6, 4.4, -14) + tr
        tr_save = tr; tr = prot
        loaf(7.6, 4.4, 9.0, 3.4, 3)
        stub_leg(4.5, 3.0, 14); stub_leg(5.4, 2.9, 4)
        stub_leg(10.4, 2.85, -6); stub_leg(11.2, 2.95, -16)
        tail_curl(2.9, 5.3, 0.9, 4)
        eye(11.0, 4.9, "half", 6)          # resigned mid-air waddles
        ear(10.55, 5.45, "droop", 5)
        snout(12.3, 3.95, 1.0 * droop, 5)
        ellipse(12.05, 3.25, 0.42, 0.32, DARK, 6)
        if wings:
            wing_pair(6.6, 6.5, -30 + 40 * np.sin(phase * 2 * np.pi),
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
        draw_w2_pig(ax, pose=ps, wings=(ps == "fly"), phase=0.3,
                    facing=(-1 if ps == "flee" else 1))
        ax.set_title(ps, color="#DFF4EE", fontsize=20, pad=12,
                     fontweight="bold")
    plt.subplots_adjust(left=0.01, right=0.99, top=0.9, bottom=0.01,
                        wspace=0.05)
    plt.savefig("pig_w2_poses.png", facecolor="#0D1B26")
    print("saved pig_w2_poses.png")

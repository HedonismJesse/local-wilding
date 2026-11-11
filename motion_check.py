# provenance: author=devin; created=2026-11-10; source=plan
#   ai-hub Artifacts/plans/repo/ART_SPHERE_CHILD_SPHERES_2026-11-10.md
#   (art:motion-canon child sphere + Domain primer);
#   purpose=pose-sequence checks for animatics - anticipation, easing,
#   squash, flee, dock, exit - so "it moves" stops passing for
#   "it reads as motion"; intent=production
"""motion_check — the motion-canon instrument.

Canon (Illusion of Life 12 principles -> mechanical subset, per the
plan doc's Domain primer): anticipation = counter-movement before
launch; slow-in/out = velocity easing at beat edges; squash/stretch =
bbox aspect dip<->peak at accents; timing = per-beat frame bounds +
holds; arcs/secondary action = appendage oscillation while body
translates. Appeal/acting stay operator-verdict (routed, unverifiable).

Tracks per frame:
    pig   — largest mask component (excluding the wing color key)
    wing  — pixels near the spec's wing rgb (exists only when a
            wing pair is on stage; docking = distance collapse)

Beats come from a spec JSON:

    {"fps": 15,
     "track": {"wing_rgb": [223,244,238], "tol": 42},
     "beats": [{"name":"idle","frames":[0,39],
                "checks":{"breathing":{"min_aspect_osc":0.015,
                                       "max_drift_px":14},
                           "hold":{"min_len":10,"eps_px":1.2}}},
                ...]}

Usage:
    python motion_check.py <frames_dir> --beats motion/lazy_flight.json
        [--out report.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

import render_audit as ra


# ------------------------------------------------------------ tracking

def _track_frame(path: Path, wing_rgb, tol):
    a = np.asarray(Image.open(path).convert("RGBA"), dtype=np.float32)
    mask, _ = ra._subject_mask(Image.open(path))
    rgb = a[..., :3]
    wing = (np.abs(rgb - np.asarray(wing_rgb)).sum(axis=2) < tol * 3) & \
           (a[..., 3] > 128)
    pig_mask = mask & ~wing
    regions = ra._components(pig_mask)
    rec = {"wing_exists": bool(wing.sum() >= 40)}
    if rec["wing_exists"]:
        ys, xs = np.where(wing)
        rec["wing_cx"], rec["wing_cy"] = float(xs.mean()), float(ys.mean())
    pig = max(regions, key=lambda r: r.area, default=None)
    rec["pig_exists"] = pig is not None
    if pig:
        y0, x0, y1, x1 = pig.bbox
        rec.update(pig_cx=float(pig.centroid[1]),
                   pig_cy=float(pig.centroid[0]),
                   pig_bbox=[int(x0), int(y0), int(x1), int(y1)],
                   pig_aspect=(x1 - x0) / max(y1 - y0, 1),
                   pig_area=float(pig.area),
                   pig_cover=float(pig.area) / mask.size)
    if rec["wing_exists"] and pig:
        rec["wing_pig_dist"] = float(np.hypot(
            rec["wing_cx"] - rec["pig_cx"],
            rec["wing_cy"] - rec["pig_cy"]))
    rec["frame_h"], rec["frame_w"] = a.shape[:2]
    return rec


def track(frames: list[Path], spec: dict) -> list[dict]:
    t = spec.get("track", {})
    wrgb, tol = t.get("wing_rgb", [223, 244, 238]), t.get("tol", 42)
    return [_track_frame(p, wrgb, tol) for p in frames]


def _win(recs, lo, hi):
    return [r for i, r in enumerate(recs) if lo <= i <= hi and
            r.get("pig_exists")]


def _deltas(xs):
    return np.diff(np.asarray(xs, dtype=float))


# ------------------------------------------------- checks (pure fns)

def check_breathing(rs, min_aspect_osc=0.015, max_drift_px=14):
    """Idle-life check: slow aspect oscillation (belly breathing) and
    no net translation."""
    asp = np.array([r["pig_aspect"] for r in rs])
    cx = np.array([r["pig_cx"] for r in rs])
    osc = float(asp.max() - asp.min()) if len(asp) else 0.0
    drift = float(abs(cx[-1] - cx[0])) if len(cx) else 0.0
    ok = osc >= min_aspect_osc and drift <= max_drift_px
    return ok, {"aspect_osc": round(osc, 4), "drift": round(drift, 1)}, \
        "dead_idle"


def check_accent(rs, min_delta_px=12):
    """Notice/startle: >=1 sharp 1-frame change on the subject's top
    edge (head snap proxy)."""
    ys = np.array([r["pig_bbox"][1] for r in rs])
    d = np.abs(_deltas(ys))
    mx = float(d.max()) if len(d) else 0.0
    return mx >= min_delta_px, {"max_top_delta": round(mx, 1)}, \
        "no_accent"


def check_hold(rs, min_len=8, eps_px=1.5):
    """Cartoon hold: >=min_len consecutive near-still frames."""
    cx = np.array([r["pig_cx"] for r in rs])
    cy = np.array([r["pig_cy"] for r in rs])
    d = np.abs(_deltas(cx)) + np.abs(_deltas(cy))
    best = cur = 0
    for v in d:
        cur = cur + 1 if v <= eps_px else 0
        best = max(best, cur)
    return best >= min_len, {"hold_len": int(best)}, "no_hold"


def check_flee_velocity(rs, min_frac=0.6, min_speed_px=2.0,
                        direction=-1):
    """Sustained translation away from the threat; direction=-1 flees
    left, +1 right."""
    cx = np.array([r["pig_cx"] for r in rs])
    d = _deltas(cx) * direction
    frac = float((d >= min_speed_px).mean()) if len(d) else 0.0
    mean_v = float(d.mean()) if len(d) else 0.0
    return frac >= min_frac and mean_v > 0, \
        {"flee_frac": round(frac, 2), "mean_v": round(mean_v, 2)}, \
        "no_flee"


def check_cycle_bob(rs, min_crossings=2):
    """Leg-cycle proxy: detrended cy sign changes during locomotion."""
    cy = np.array([r["pig_cy"] for r in rs], dtype=float)
    if len(cy) < 4:
        return False, {"crossings": 0}, "no_cycle"
    trend = np.polyval(np.polyfit(np.arange(len(cy)), cy, 1),
                       np.arange(len(cy)))
    s = np.sign(cy - trend)
    crossings = int(np.count_nonzero(s[1:] * s[:-1] < 0))
    return crossings >= min_crossings, {"crossings": crossings}, \
        "no_cycle"


def check_easeout_dock(recs, dock_px=90, max_end_ratio=0.6):
    """Wing approach decelerates into contact (ease-out docking)."""
    pts = [(i, r) for i, r in enumerate(recs) if r.get("wing_exists")
           and "wing_pig_dist" in r]
    if len(pts) < 4:
        merged = bool(pts) is False
        return merged, {"approach_frames": len(pts)}, "missed_dock"
    d = np.array([r["wing_pig_dist"] for _, r in pts])
    v = np.abs(_deltas(d))
    v0 = float(v[:3].mean()); v1 = float(v[-3:].mean())
    ok = (d[-1] <= dock_px or
          (pts[-1][1].get("pig_bbox") and
           pts[-1][1]["wing_cx"] <= pts[-1][1]["pig_bbox"][2] and
           pts[-1][1]["wing_cx"] >= pts[-1][1]["pig_bbox"][0])) and \
        v1 <= max_end_ratio * max(v0, 1e-6)
    return ok, {"d_start": round(float(d[0]), 1),
                "d_end": round(float(d[-1]), 1),
                "v_start": round(v0, 1), "v_end": round(v1, 1)}, \
        "linear_dock"


def check_squash_launch(rs, window_frac=0.4, margin=0.05):
    """Squash (aspect peak) then stretch (aspect dip) inside the
    launch window."""
    asp = np.array([r["pig_aspect"] for r in rs])
    if len(asp) < 5:
        return False, {}, "no_squash"
    base = float(np.median(asp[:3]))
    n = max(2, int(len(asp) * window_frac))
    early = float(asp[:n].max()); late = float(asp[n:].min())
    ok = early >= base * (1 + margin) and late <= base * (1 - margin)
    return ok, {"aspect_base": round(base, 3),
                "squash_peak": round(early, 3),
                "stretch_dip": round(late, 3)}, "no_squash"


def check_accelerating_exit(rs, ratio=1.25):
    cx = np.array([r["pig_cx"] for r in rs])
    cy = np.array([r["pig_cy"] for r in rs])
    sp = np.hypot(_deltas(cx), _deltas(cy))
    if len(sp) < 6:
        return False, {}, "constant_speed_exit"
    n = max(2, int(len(sp) * 0.3))
    v0, v1 = float(sp[:n].mean()), float(sp[-n:].mean())
    return v1 >= v0 * ratio, {"v_start": round(v0, 2),
                              "v_end": round(v1, 2)}, \
        "constant_speed_exit"


def check_exits_frame(recs, cover_max=0.02):
    """Subject leaves (or nearly leaves) the canvas by beat end."""
    tail = [r for r in recs[-4:] if r.get("pig_exists")]
    if not tail:
        return True, {"final_cover": 0.0}, "subject_stays"
    r = tail[-1]
    w = r["frame_w"]
    over = r["pig_cover"] <= cover_max or r["pig_bbox"][0] >= w * 0.97
    return over, {"final_cover": round(r["pig_cover"], 4),
                  "final_x0": r["pig_bbox"][0]}, "subject_stays"


def check_no_linear(rs, min_len=8, eps_px=0.4, min_speed_px=1.0):
    """No constant-velocity transit >= min_len frames (linear lerp)."""
    cx = np.array([r["pig_cx"] for r in rs])
    cy = np.array([r["pig_cy"] for r in rs])
    vx, vy = _deltas(cx), _deltas(cy)
    sp = np.hypot(vx, vy)
    dv = np.abs(_deltas(sp))
    best = cur = 0
    for i in range(len(dv)):
        moving = sp[i] >= min_speed_px and sp[i + 1] >= min_speed_px
        cur = cur + 1 if dv[i] <= eps_px and moving else 0
        best = max(best, cur)
    return best < min_len, {"longest_linear": int(best)}, "linear_lerp"


def check_flap_bob(rs, min_crossings=3):
    """Wing flap cycle: wing cy oscillates >= min_crossings while on
    stage."""
    cy = np.array([r["wing_cy"] for r in rs if r.get("wing_exists")],
                  dtype=float)
    if len(cy) < 6:
        return False, {"crossings": 0}, "no_flap"
    s = np.sign(np.diff(cy))
    crossings = int(np.count_nonzero(s[1:] * s[:-1] < 0))
    return crossings >= min_crossings, {"crossings": crossings}, \
        "no_flap"


CHECKS = {
    "breathing": check_breathing,
    "accent": check_accent,
    "hold": check_hold,
    "flee_velocity": check_flee_velocity,
    "cycle_bob": check_cycle_bob,
    "easeout_dock": check_easeout_dock,
    "squash_launch": check_squash_launch,
    "accelerating_exit": check_accelerating_exit,
    "exits_frame": check_exits_frame,
    "no_linear": check_no_linear,
    "flap_bob": check_flap_bob,
}


def check_beats(recs: list[dict], spec: dict) -> dict:
    out = {"frames": len(recs), "beats": {}, "flags": []}
    for b in spec.get("beats", []):
        lo, hi = b["frames"]
        rs = _win(recs, lo, hi)
        brep = {"window": [lo, hi], "tracked": len(rs), "checks": {}}
        for name, kw in b.get("checks", {}).items():
            fn = CHECKS[name]
            src = recs[lo:hi + 1] if name in (
                "easeout_dock", "exits_frame") else rs
            ok, measured, flag = fn(src, **(kw or {}))
            brep["checks"][name] = {"pass": bool(ok), **measured}
            if not ok:
                out["flags"].append(f"{flag}@{b['name']}")
        out["beats"][b["name"]] = brep
    for name, kw in spec.get("global_checks", {}).items():
        ok, measured, flag = CHECKS[name](
            [r for r in recs if r.get("pig_exists")], **(kw or {}))
        out.setdefault("global", {})[name] = {"pass": bool(ok),
                                              **measured}
        if not ok:
            out["flags"].append(f"{flag}@global")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("frames", type=Path, help="dir of frame PNGs")
    ap.add_argument("--beats", type=Path, required=True)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    spec = json.loads(a.beats.read_text())
    frames = sorted(a.frames.glob("*.png"))
    if not frames:
        print(f"no frames in {a.frames}", file=sys.stderr)
        return 2
    recs = track(frames, spec)
    rep = check_beats(recs, spec)
    rep["per_frame"] = recs
    txt = json.dumps(rep, indent=1)
    if a.out:
        a.out.write_text(txt)
    print(f"{len(frames)} frames; flags: {rep['flags'] or 'clean'}")
    for bn, br in rep["beats"].items():
        bad = [c for c, r in br["checks"].items() if not r["pass"]]
        print(f"  {bn}: {'clean' if not bad else 'FAIL ' + ','.join(bad)}")
    return 0 if not rep["flags"] else 1


if __name__ == "__main__":
    sys.exit(main())

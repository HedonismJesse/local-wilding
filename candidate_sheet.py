# provenance: author=devin; created=2026-11-10; source=plan
#   ai-hub Artifacts/plans/repo/ART_SPHERE_CHILD_SPHERES_2026-11-10.md
#   (art:candidate-pipeline child sphere);
#   purpose=batch -> score -> sheet -> pick so "present before build"
#   is a gate, not a reminder; intent=production
"""candidate_sheet — the candidate-pipeline instrument.

batch:    --builder module:func + --param name=v1,v2 -> param grid
score:    render_audit.audit_frame (+ --spec canon spec) per variant
sheet:    labeled PNG grid, flags under each candidate
pick:     --verdict ID=pick|reject|unverifiable:reason appends
          (artifact, candidate_id, verdict, operator_reason,
          named_failure, audit_features) rows to reads.jsonl —
          audit flags become the named_failure vocabulary when the
          operator doesn't supply one.

Builder contract: func(ax, **params) draws on a matplotlib Axes;
pig_sheet.draw_pig(ax, pose, goggles, head_ratio, chunk) is the
ad-hoc instance this generalizes.

    python candidate_sheet.py --builder pig_sheet:draw_pig \
        --param pose=0,8,-8 --param head_ratio=1.0,1.25 \
        --spec canon/pig.json --out-dir candidates/anim_v2_pig
    python candidate_sheet.py --verdict-dir candidates/anim_v2_pig \
        A=pick B=reject:fin_ear --ledger reads path
"""
from __future__ import annotations

import argparse
import importlib
import itertools
import json
import sys
from pathlib import Path

THUMB_W = 420


def _grid(params: dict[str, list]) -> list[dict]:
    names = list(params)
    return [dict(zip(names, combo))
            for combo in itertools.product(*(params[n] for n in names))]


def _render(builder, params: dict, out: Path, figsize=(8, 5)) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=figsize, dpi=150)
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 10)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_alpha(0)
    builder(ax, **params)
    fig.savefig(out, transparent=True)
    plt.close(fig)


def _sheet(variants: list[dict], out: Path) -> None:
    from PIL import Image, ImageDraw
    cols = min(4, max(1, len(variants)))
    rows = (len(variants) + cols - 1) // cols
    cell_h = int(THUMB_W * 5 / 8) + 84
    sheet = Image.new("RGBA", (cols * THUMB_W, rows * cell_h),
                      (13, 27, 38, 255))
    d = ImageDraw.Draw(sheet)
    for i, v in enumerate(variants):
        cx, cy = (i % cols) * THUMB_W, (i // cols) * cell_h
        im = Image.open(v["png"]).convert("RGBA")
        im.thumbnail((THUMB_W - 16, cell_h - 100))
        sheet.alpha_composite(
            im, (cx + (THUMB_W - im.width) // 2, cy + 8))
        ps = " ".join(f"{k}={p}" for k, p in v["params"].items())
        d.text((cx + 8, cy + cell_h - 72), f"{v['id']}  {ps}",
               fill=(180, 210, 220, 255))
        fl = ",".join(v["flags"]) if v["flags"] else "clean"
        d.text((cx + 8, cy + cell_h - 44), fl[:64],
               fill=(230, 90, 110, 255) if v["flags"]
               else (80, 220, 160, 255))
    sheet.convert("RGB").save(out)


def _audit(png: Path, spec: dict | None) -> dict:
    import render_audit as ra
    return ra.audit_frame(png, spec)


def cmd_sheet(a) -> int:
    mod, fn = a.builder.split(":")
    builder = getattr(importlib.import_module(mod), fn)
    params = {}
    for p in a.param or []:
        name, vals = p.split("=", 1)
        params[name] = [json.loads(v) if v[0] in "0123456789-.[{\"tf"
                        else v for v in vals.split(",")]
    spec = json.loads(a.spec.read_text()) if a.spec else None
    a.out_dir.mkdir(parents=True, exist_ok=True)
    letters = "ABCDEFGH"
    variants = []
    for i, ps in enumerate(_grid(params)):
        vid = letters[i] if i < len(letters) else f"v{i:02d}"
        png = a.out_dir / f"{vid}.png"
        _render(builder, ps, png)
        rep = _audit(png, spec)
        variants.append({"id": vid, "params": ps, "png": str(png),
                         "flags": rep["flags"], "audit": rep})
        print(f"{vid} {ps} -> {rep['flags'] or 'clean'}")
    sheet_png = a.out_dir / "sheet.png"
    _sheet(variants, sheet_png)
    (a.out_dir / "manifest.json").write_text(json.dumps(
        {"builder": a.builder, "spec": str(a.spec) if a.spec else None,
         "variants": variants, "sheet": str(sheet_png)}, indent=1))
    print(f"sheet -> {sheet_png}")
    return 0


def cmd_verdict(a) -> int:
    man = json.loads((Path(a.verdict_dir) / "manifest.json").read_text())
    by_id = {v["id"]: v for v in man["variants"]}
    import datetime
    rows = []
    for raw in a.verdicts:
        vid, _, rest = raw.partition("=")
        verdict, _, reason = rest.partition(":")
        v = by_id[vid]
        rows.append({
            "artifact": v["png"], "candidate_id": f"{vid}",
            "variant_params": v["params"],
            "verdict": verdict or "unverifiable",
            "operator_reason": reason or None,
            "named_failure": ",".join(v["flags"]) or None,
            "ts": datetime.datetime.now().isoformat(timespec="seconds"),
            "source": "candidate_sheet pick",
            "audit_features": v["flags"]})
    with Path(a.ledger).open("a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"{len(rows)} verdicts -> {a.ledger}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--builder", help="module:func draw(ax, **params)")
    ap.add_argument("--param", action="append",
                    help="name=v1,v2,... (JSON scalars or strings)")
    ap.add_argument("--spec", type=Path, help="canon spec JSON")
    ap.add_argument("--out-dir", type=Path,
                    default=Path("candidates/run"))
    ap.add_argument("--verdict-dir", type=Path)
    ap.add_argument("--ledger", type=Path, default=Path(
        "../ai-hub/Artifacts/art_sphere/reads.jsonl"))
    ap.add_argument("verdicts", nargs="*",
                    help="ID=verdict:reason (pick|reject|unverifiable)")
    a = ap.parse_args()
    if a.verdict_dir:
        return cmd_verdict(a)
    if not a.builder:
        ap.error("--builder required in sheet mode")
    return cmd_sheet(a)


if __name__ == "__main__":
    sys.exit(main())

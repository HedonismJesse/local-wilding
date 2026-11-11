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

Every run also writes review.html — self-contained (base64-embedded
renders), per-variant flags, the verdict command. "Present before
build" means PRESENTABLE: the operator gets a ref_file link or a
preview page they can open and SEE. A bare sheet.png path in prose
is not presentation (2026-11-10 operator ruling, attempt #4).

art:reference-canon gate: sheet mode REFUSES without --refs (a
canon/refs/refs.json manifest + --ref-pick ids) unless --allow-no-ref
marks the batch floor-level/experimental. Candidates must extrapolate
a named reference, not the last render (2026-11-10 mass-reject: all
16 were lineage extrapolations). --refs-only emits the reference
review page — the operator picks the anchor BEFORE any pig is drawn.

    python candidate_sheet.py --refs canon/refs/refs.json --refs-only \
        --out-dir canon/refs_review
    python candidate_sheet.py --builder pig_sheet:draw_pig \
        --refs canon/refs/refs.json --ref-pick walnutty_flying \
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


def _b64(p: Path) -> str:
    import base64
    return base64.b64encode(Path(p).read_bytes()).decode()


def _refs_html(refs_man: dict, pick_ids: list[str] | None = None,
               base: Path = Path(".")) -> str:
    """Reference panel — images + signature elements + source, so the
    review page shows what the candidates are anchored to (or, in
    refs-only mode, what there is to pick)."""
    import html as _h
    cells = []
    for r in refs_man.get("refs", []):
        img = base / r["file"]
        b64 = _b64(img) if img.exists() else ""
        mark = (" <b style=color:#3fd9a8>[ANCHOR]</b>"
                if pick_ids and r["id"] in pick_ids else "")
        status = r.get("status")
        mark += (f' <b style=color:#e65a6e>[{status.upper()}]</b>'
                 if status == "rejected" else "")
        style = "opacity:.35" if status == "rejected" else ""
        sig = "".join(f"<li>{_h.escape(s)}</li>"
                      for s in r.get("signature_elements", []))
        cells.append(
            f'<div class=ref style="{style}"><div class=cap>'
            f'{_h.escape(r["id"])} '
            f'— {_h.escape(r.get("role", ""))} · '
            f'{_h.escape(r.get("register", ""))}{mark}</div>'
            f'{"<img src=data:image/png;base64," + b64 + ">" if b64 else ""}'
            f'<ul class=sig>{sig}</ul>'
            f'<div class=src>{_h.escape(r.get("license", "?"))} · '
            f'{_h.escape(r.get("author", ""))} · '
            f'<a style=color:#5aa8e0 href="{_h.escape(r.get("source", ""))}">'
            f'source</a></div></div>')
    return f'<h2>references — {_h.escape(refs_man.get("subject", ""))}' \
           f'</h2><div class=refgrid>{"".join(cells)}</div>'


def _refs_page(refs_man: dict, out: Path, base: Path = Path(".")) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    page = ("<!doctype html><meta charset=utf-8><title>reference pick"
            "</title>" + _STYLE +
            "<h1>reference pick — which refs anchor the next build?"
            "</h1><p>roles: <b>style-target</b> = register to draw in "
            "· <b>anatomy</b> = proportion truth · <b>contrast</b> = "
            "off-brief marker. Reply with ref id(s) to anchor, then "
            "candidate sheets generate against their signature "
            "elements.</p>" + _refs_html(refs_man, base=base))
    p = out / "refs_review.html"
    p.write_text(page, encoding="utf-8")
    return p


_STYLE = ("<style>body{background:#0d1b26;color:#dff4ee;"
          "font-family:system-ui;margin:20px}h1{font-size:18px;"
          "color:#3fd9a8}h2{font-size:14px;color:#8fb0c0}"
          ".grid{display:flex;flex-wrap:wrap;gap:14px}"
          ".refgrid{display:flex;flex-wrap:wrap;gap:14px;margin:"
          "10px 0 22px}.ref{width:380px}.ref img{width:100%;"
          "border:1px solid #2a4a5a;background:#fff}"
          ".cell{width:560px}.cell img{width:100%;"
          "border:1px solid #2a4a5a}.cap{font-size:13px;color:#8fb0c0}"
          ".sig{font-size:11px;color:#9fc0cc;margin:6px 0;"
          "padding-left:18px}.src{font-size:10px;color:#5a7a88}"
          ".fl{font-size:12px;min-height:16px}</style>")


def _review_html(variants: list[dict], out: Path,
                 spec_name: str | None,
                 refs_man: dict | None = None,
                 pick_ids: list[str] | None = None) -> Path:
    """Self-contained review page — base64 renders so it opens anywhere
    with zero setup. The pick-request artifact."""
    import html as _h
    cells = []
    for v in variants:
        b64 = _b64(v["png"])
        ps = " ".join(f"{k}={p}" for k, p in v["params"].items())
        fl = ",".join(v["flags"]) if v["flags"] else "clean"
        color = "#e65a6e" if v["flags"] else "#50dca0"
        cells.append(
            f'<div class=cell><div class=cap>{v["id"]} — '
            f'{_h.escape(ps)}</div>'
            f'<img src="data:image/png;base64,{b64}">'
            f'<div class=fl style="color:{color}">{_h.escape(fl)}'
            f'</div></div>')
    ref_panel = (_refs_html(refs_man, pick_ids, base=out)
                 if refs_man else
                 "<p><b style=color:#e65a6e>NO REFERENCE — floor-level "
                 "batch, not eligible for approval.</b></p>")
    page = (
        "<!doctype html><meta charset=utf-8><title>candidate review"
        "</title>" + _STYLE +
        f"<h1>candidate review — {_h.escape(spec_name or 'no spec')}"
        "</h1>" + ref_panel +
        "<p>record pick: <code>python candidate_sheet.py "
        f"--verdict-dir {out} ID=pick|reject:reason</code></p>"
        f"<div class=grid>{''.join(cells)}</div>")
    p = out / "review.html"
    p.write_text(page, encoding="utf-8")
    return p


def _audit(png: Path, spec: dict | None) -> dict:
    import render_audit as ra
    return ra.audit_frame(png, spec)


def cmd_refs(a) -> int:
    refs_man = json.loads(a.refs.read_text())
    p = _refs_page(refs_man, a.out_dir)
    print(f"refs review -> {p}  (present THIS — pick precedes draw)")
    return 0


def cmd_sheet(a) -> int:
    if not a.refs and not a.allow_no_ref:
        print("REFUSED: no reference attached. Candidate generation "
              "requires --refs canon/refs/refs.json + --ref-pick ID "
              "(art:reference-canon), or --allow-no-ref to mark the "
              "batch floor-level/experimental. Extrapolating the last "
              "render is how the bad lineage happened.", file=sys.stderr)
        return 2
    refs_man = json.loads(a.refs.read_text()) if a.refs else None
    pick_ids = a.ref_pick.split(",") if a.ref_pick else None
    mod, fn = a.builder.split(":")
    builder = getattr(importlib.import_module(mod), fn)
    params = {}
    for p in a.param or []:
        name, vals = p.split("=", 1)
        params[name] = [json.loads(v) if v[0] in "0123456789-.[{\"tf"
                        else v for v in vals.split(",")]
    spec = json.loads(a.spec.read_text()) if a.spec else None
    combos = (json.loads(Path(a.variants).read_text()) if a.variants
              else _grid(params))
    a.out_dir.mkdir(parents=True, exist_ok=True)
    letters = "ABCDEFGH"
    variants = []
    for i, ps in enumerate(combos):
        vid = letters[i] if i < len(letters) else f"v{i:02d}"
        png = a.out_dir / f"{vid}.png"
        _render(builder, ps, png)
        rep = _audit(png, spec)
        variants.append({"id": vid, "params": ps, "png": str(png),
                         "flags": rep["flags"], "audit": rep})
        print(f"{vid} {ps} -> {rep['flags'] or 'clean'}")
    sheet_png = a.out_dir / "sheet.png"
    _sheet(variants, sheet_png)
    review = _review_html(variants, a.out_dir,
                          str(a.spec) if a.spec else None,
                          refs_man, pick_ids)
    (a.out_dir / "manifest.json").write_text(json.dumps(
        {"builder": a.builder, "spec": str(a.spec) if a.spec else None,
         "refs": {"manifest": str(a.refs), "picks": pick_ids}
         if a.refs else None,
         "no_ref": bool(a.allow_no_ref),
         "variants": variants, "sheet": str(sheet_png),
         "review": str(review)}, indent=1))
    print(f"sheet -> {sheet_png}")
    print(f"review -> {review}  (present THIS, not a bare path)")
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
            "refs": (man.get("refs") or {}).get("picks"),
            "no_ref": man.get("no_ref", False),
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
    ap.add_argument("--variants", type=Path,
                    help="JSON list of param dicts - curated combos "
                         "instead of the --param cartesian grid")
    ap.add_argument("--spec", type=Path, help="canon spec JSON")
    ap.add_argument("--refs", type=Path,
                    help="reference manifest (canon/refs/refs.json)")
    ap.add_argument("--ref-pick",
                    help="comma-separated ref ids anchoring this batch")
    ap.add_argument("--refs-only", action="store_true",
                    help="emit the reference pick page, no candidates")
    ap.add_argument("--allow-no-ref", action="store_true",
                    help="mark batch floor-level (not approvable)")
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
    if a.refs_only:
        if not a.refs:
            ap.error("--refs required for --refs-only")
        return cmd_refs(a)
    if not a.builder:
        ap.error("--builder required in sheet mode")
    return cmd_sheet(a)


if __name__ == "__main__":
    sys.exit(main())

# provenance: author=devin; created=2026-11-11; source=operator
# direction "mr potato head mix and match ... character doing X to pull
# examples from"; purpose=parts board + action catalog sheets (character-
# design grammar: option columns, not whole-variant sheets); intent=production
"""parts_sheet — the mix-and-match boards.

Two levels of the same artifact:
  PARTS board  — option columns per named part on the same canon body
                 (the character-design model sheet). Pick one per row.
  ACTION board — 'character doing X' cells pulled from the pose
                 vocabulary (the storyboard example shelf). Canonical
                 poses verified; '*' cells are draft op-combos still
                 under review.

Every cell renders the SAME canon base through the SAME emitter — the
only thing that varies is the op list. Cells are specs, not drawings:
picking a cell means picking its ops, and picks compose.
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw

import pig_derive as pd
import pig_w5 as pw
import trace_linework as tl

ROOT = Path(__file__).parent
BASE = ROOT / "canon" / "ourpig_base.json"
STYLE = "flat"

# parts board: (row label, [(option label, ops)])
PARTS = [
    ("body",   [("canon", []),
                ("belly+", [{"op": "belly_droop", "a": 0.10}]),
                ("squat", [{"op": "squat", "a": 0.10}]),
                ("jowl", [{"op": "jowl", "a": 0.06}])]),
    ("ears",   [("canon", []),
                ("droop+", [{"op": "ear_droop", "a": 0.10}]),
                ("pointy", [{"op": "ear_point", "a": 0.08}])]),
    ("eyes",   [("canon", []),
                ("open", [{"op": "open_eyes"}]),
                ("lids", [{"op": "droopy_lids"}])]),
    ("snout",  [("canon", []),
                ("plate+", [{"op": "snout_scale", "s": 1.4}]),
                ("plate-", [{"op": "snout_scale", "s": 0.65}])]),
    ("marks",  [("canon", []),
                ("spots", [{"op": "addspots"}]),
                ("saddle", [{"op": "saddle"}]),
                ("eyepatch", [{"op": "eyepatch"}])]),
    ("color",  [("canon", []),
                ("pink", [{"op": "recolor", "rgb": [247, 168, 184]}]),
                ("tan", [{"op": "recolor", "rgb": [222, 184, 135]}]),
                ("grey", [{"op": "recolor", "rgb": [196, 186, 186]}])]),
    ("tail",   [("canon", []),
                ("straight", [{"op": "tail_straight"}])]),
]

# action catalog: (category, [(label, pose-name-or-None, ops)])
# canonical poses reuse pig_w5.POSE_OPS (oracle-verified); drafts are
# new op combos through the same derive_checked gate
ACTIONS = [
    ("ground", [("rest", "rest", None),
                ("sit*", None, [{"op": "squat", "a": 0.14},
                                {"op": "open_eyes"}]),
                ("notice", "notice", None),
                ("dig*", None, [{"op": "lean", "a": 0.16},
                                {"op": "open_eyes"}])]),
    ("run",    [("flee", "flee", None),
                ("jump*", None, [{"op": "squat", "a": 0.16},
                                 {"op": "pin_legs", "a": 0.55}])]),
    ("air",    [("fly", "fly", None)]),
]

CELL_W, CELL_H = 300, 210
LABEL_W, TITLE_H = 120, 30


def _cell_img(ops) -> Image.Image:
    spec = pd.derive_checked(BASE, ops) if ops else \
        json.loads(BASE.read_text())
    img = tl.render(spec, style=STYLE)
    im = Image.new("RGBA", (CELL_W, CELL_H), (255, 255, 255, 255))
    img.thumbnail((CELL_W - 16, CELL_H - 34), Image.LANCZOS)
    im.paste(img, ((CELL_W - img.width) // 2,
                   TITLE_H + (CELL_H - TITLE_H - img.height) // 2), img)
    return im


def _pose_cell(pose: str, draft_ops) -> Image.Image:
    if pose:
        img = pw.render_pose(pose, wings=(1 if pose == "fly" else 0),
                             canvas=(CELL_W, CELL_H - TITLE_H),
                             style=STYLE)
        im = Image.new("RGBA", (CELL_W, CELL_H), (255, 255, 255, 255))
        im.paste(img, (0, TITLE_H), img)
        return im
    return _cell_img(draft_ops)


def _board(rows, is_action, out: Path) -> None:
    cols = max(len(r[1]) for r in rows)
    W = LABEL_W + cols * CELL_W
    H = len(rows) * CELL_H + 46
    sheet = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    d = ImageDraw.Draw(sheet)
    for ri, (rlabel, cells) in enumerate(rows):
        y = ri * CELL_H
        d.text((10, y + CELL_H // 2 - 6), rlabel, fill=(60, 60, 60, 255))
        d.line([(0, y), (W, y)], fill=(225, 225, 225, 255))
        for ci, (label, pose, ops) in enumerate(
                cells if is_action else [(l, None, o) for l, o in cells]):
            x = LABEL_W + ci * CELL_W
            im = (_pose_cell(pose, ops) if is_action
                  else _cell_img(ops))
            sheet.paste(im, (x, y), im)
            d.text((x + 10, y + 8), label, fill=(60, 60, 60, 255))
    sheet.convert("RGB").save(out)


if __name__ == "__main__":
    _board(PARTS, False, ROOT / "parts_board.png")
    _board(ACTIONS, True, ROOT / "action_board.png")
    print("parts_board.png + action_board.png")

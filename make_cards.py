"""Cards for the video — title, verdict (chart), and the recap closer.
All matplotlib, all the same palette, all generated from real run numbers."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, Circle, FancyArrowPatch, Polygon
import matplotlib.font_manager as fm

BG = "#0d1b26"
TEAL = "#7de8c3"
AMBER = "#f4b860"
RED = "#ff6b6b"
GREY = "#5b7284"
WHITE = "#e8f0f4"
PINK = "#f2a7b8"
PINK_D = "#d98a9b"

MONO = fm.FontProperties(family="Consolas")


def pig(ax, x, y, s=1.0):
    """A small flat flying pig. (x,y) = body center, s = scale."""
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.set_aspect("equal")
    ax.axis("off")
    X, Y = x, y
    # wings — two soft ellipses above/behind
    for dx, dy, rot in [(0.9, 1.3, 35), (2.1, 1.5, 15)]:
        ax.add_patch(Ellipse((X + dx * s, Y + dy * s), 1.5 * s, 0.7 * s,
                             angle=rot, facecolor="white", edgecolor=TEAL,
                             lw=1.5, alpha=0.95))
    # body
    ax.add_patch(Ellipse((X, Y), 3.6 * s, 2.5 * s,
                         facecolor=PINK, edgecolor=PINK_D, lw=1.5))
    # head
    ax.add_patch(Circle((X - 1.5 * s, Y + 0.5 * s), 1.25 * s,
                        facecolor=PINK, edgecolor=PINK_D, lw=1.5))
    # ears
    ax.add_patch(Polygon(
        [[X - 2.3 * s, Y + 1.5 * s], [X - 2.0 * s, Y + 2.3 * s],
         [X - 1.5 * s, Y + 1.7 * s]], facecolor=PINK_D))
    ax.add_patch(Polygon(
        [[X - 1.1 * s, Y + 1.6 * s], [X - 0.7 * s, Y + 2.3 * s],
         [X - 0.4 * s, Y + 1.5 * s]], facecolor=PINK_D))
    # snout
    ax.add_patch(Ellipse((X - 2.5 * s, Y + 0.35 * s), 0.9 * s, 0.7 * s,
                         facecolor="#e88ba0", edgecolor=PINK_D, lw=1.2))
    ax.add_patch(Circle((X - 2.65 * s, Y + 0.4 * s), 0.07 * s, facecolor=BG))
    ax.add_patch(Circle((X - 2.35 * s, Y + 0.4 * s), 0.07 * s, facecolor=BG))
    # eye + cheek
    ax.add_patch(Circle((X - 1.55 * s, Y + 0.85 * s), 0.13 * s, facecolor=BG))
    ax.add_patch(Circle((X - 1.9 * s, Y + 0.25 * s), 0.22 * s,
                        facecolor="#f7bcc8"))
    # tail curl
    ax.add_patch(Ellipse((X + 1.9 * s, Y + 0.3 * s), 0.5 * s, 0.5 * s,
                         facecolor="none", edgecolor=PINK_D, lw=2))
    # tucked legs
    for dx in (-0.7, 0.7):
        ax.add_patch(Ellipse((X + dx * s, Y - 1.25 * s), 0.55 * s, 0.35 * s,
                             facecolor=PINK_D))
    # flight streaks
    for dy in (-0.6, 0.1, 0.8):
        ax.plot([X - 4.2 * s, X - 3.1 * s], [Y + dy * s, Y + dy * s],
                color=TEAL, lw=2, alpha=0.6)


def card(figsize=(12.98, 12.46)):
    fig = plt.figure(figsize=figsize, dpi=100, facecolor=BG)
    return fig


# ---- TITLE CARD ----
fig = card()
pig_ax = fig.add_axes([0.70, 0.55, 0.27, 0.27])
pig(pig_ax, 5, 4.5, 1.35)
fig.text(0.5, 0.66, "local-wilding", color=TEAL, fontsize=58,
         fontproperties=MONO, ha="center", fontweight="bold")
fig.text(0.5, 0.575, "a 1B local model with no tools does real research",
         color=WHITE, fontsize=22, fontproperties=MONO, ha="center")
fig.text(0.5, 0.53,
         "Otari lends it server-side tools - a budget ledger - decision receipts",
         color=GREY, fontsize=15, fontproperties=MONO, ha="center")
fig.text(0.5, 0.455, "pigs fly when a gateway lends them wings",
         color=AMBER, fontsize=16, fontproperties=MONO, ha="center")
fig.text(0.5, 0.39, "devs-wilding submission", color=GREY, fontsize=13,
         fontproperties=MONO, ha="center")
fig.savefig("title_card.png", facecolor=BG)
plt.close(fig)

# ---- RECAP / END CARD ----
fig = card()
fig.text(0.5, 0.86, "what you just watched", color=TEAL, fontsize=34,
         fontproperties=MONO, ha="center", fontweight="bold")
rows = [
    ("1B local model, zero tools", "answered from weights alone - and guessed 8.4%"),
    ("same loop via hosted Otari", "code_execution ran server-side - 0.0101 USD settled"),
    ("pre-dispatch budget refusal", "a 0.01 USD cap said no before any call - zero spent"),
    ("reserve/settle spend ledger", "every call: reserve, dispatch, settle - real USD"),
    ("decision receipts", "who served, why, weighted-draw routing policy"),
    ("sphere_fitness self-score", "9/9 - every claimed beat backed by a file in evidence/"),
]
y = 0.74
for head, tail in rows:
    fig.text(0.10, y, "[x]", color=TEAL, fontsize=15, fontproperties=MONO)
    fig.text(0.17, y, head, color=WHITE, fontsize=15, fontproperties=MONO)
    fig.text(0.17, y - 0.032, tail, color=GREY, fontsize=11.5,
             fontproperties=MONO)
    y -= 0.085
fig.text(0.5, 0.175, "github.com/HedonismJesse/local-wilding", color=TEAL,
         fontsize=20, fontproperties=MONO, ha="center", fontweight="bold")
fig.text(0.5, 0.135, "branch devs-wilding - first Otari commit cb6f106",
         color=WHITE, fontsize=13, fontproperties=MONO, ha="center")
pig_ax = fig.add_axes([0.04, 0.03, 0.13, 0.13])
pig(pig_ax, 5, 4.5, 0.62)
fig.savefig("end_card.png", facecolor=BG)
plt.close(fig)

print("title_card.png, end_card.png written")

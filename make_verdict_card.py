"""The verdict card — what the gateway's code_execution actually computed,
drawn as a chart instead of scrolled past in text. Real numbers from the
run: 2015 = 1,310,559,000 · 2023 = 1,428,627,000 · growth 9.01%.
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

BG = "#0d1b26"
TEAL = "#7de8c3"
AMBER = "#f4b860"
RED = "#ff6b6b"
GREY = "#5b7284"
WHITE = "#e8f0f4"

POP_2015 = 1_310_559_000
POP_2023 = 1_428_627_000
GROWTH = (POP_2023 - POP_2015) / POP_2015 * 100  # 9.01%
CLAIM = 15.0

fig = plt.figure(figsize=(13.0, 7.2), dpi=100, facecolor=BG)
ax = fig.add_axes([0.22, 0.18, 0.72, 0.62], facecolor=BG)

bars = ax.barh(
    [1, 0],
    [CLAIM, GROWTH],
    height=0.52,
    color=[AMBER, TEAL],
    edgecolor="none",
)
ax.set_yticks([1, 0])
ax.set_yticklabels(
    ["the claim said\n> 15%", f"verified by code\n{GROWTH:.1f}%"],
    color=WHITE, fontsize=15, family="Consolas",
)
ax.set_xlim(0, 17)
ax.set_xticks([])
for spine in ax.spines.values():
    spine.set_visible(False)

# claim bar wears a strike-through x
ax.text(CLAIM + 0.25, 1, "X", color=RED, fontsize=30, family="Consolas",
        va="center", fontweight="bold")
ax.text(GROWTH + 0.25, 0, f"{GROWTH:.1f}%", color=TEAL, fontsize=22,
        family="Consolas", va="center", fontweight="bold")
ax.text(CLAIM - 0.2, 1, "15%", color=AMBER, fontsize=16, family="Consolas",
        va="center", ha="right")

# the gap that sinks the claim
ax.annotate(
    "",
    xy=(CLAIM, 0.62), xytext=(GROWTH, 0.62),
    arrowprops=dict(arrowstyle="<->", color=RED, lw=2),
)
ax.text((CLAIM + GROWTH) / 2, 0.68, f"off by {CLAIM - GROWTH:.0f} points - "
        f"~{int((CLAIM - GROWTH) / 100 * POP_2015 / 1e6)} million people",
        color=RED, fontsize=12.5, family="Consolas", ha="center")

fig.text(0.5, 0.90, "THE VERDICT", color=TEAL, fontsize=26,
         family="Consolas", ha="center", fontweight="bold")
fig.text(0.5, 0.835,
         "'India's population grew more than 15% between 2015 and 2023'",
         color=GREY, fontsize=13, family="Consolas", ha="center")
fig.text(0.5, 0.055,
         f"FALSE - computed server-side by otari_code_execution - "
         f"{POP_2015:,} -> {POP_2023:,} = +{GROWTH:.2f}%",
         color=WHITE, fontsize=13.5, family="Consolas", ha="center")
fig.text(0.5, 0.015, "local-wilding | devs-wilding",
         color=GREY, fontsize=10, family="Consolas", ha="center")

fig.savefig("verdict_card.png", facecolor=BG)
print("verdict_card.png written")

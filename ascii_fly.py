"""ASCII flying pig animation test - jgs canon pig, 2-frame flap,
crossing the title text. Pig carries a dark backing patch so the
wordmark it passes through stays readable (occlusion, no distortion).
Eyes patched 66 -> oo for a friendlier read.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import subprocess, os

BG = "#0D1B26"; TEAL = "#3FD9A8"; AMBER = "#FFCF6B"; TXT = "#DFF4EE"
N_FRAMES = 60
FPS = 15
os.makedirs("fly_frames", exist_ok=True)

FRAME_A = r""" _____  ____
)    /,----'
 \  //==--'
  \//==--'
 _//|Y.-~~~~-,
_/oo  \        \_@
(")_   /   /    |
  '--'|| |-\   /
      //_/  /_/"""

FRAME_B = r""" _____  ____
`----,\    )
 `--==\\  /
  `--==\\/
 _//|Y.-~~~~-,
_/oo  \        \_@
(")_   /   /    |
  '--'|| |-\   /
      //_/  /_/"""

STREAKS = " = == =="

def render(i):
    fig = plt.figure(figsize=(13, 6.5), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor(BG); ax.set_xlim(0, 13); ax.set_ylim(0, 6.5)
    ax.axis("off")

    # title block (same look as the card)
    ax.text(6.5, 3.1, "local-wilding", family="DejaVu Sans",
            fontsize=66, fontweight="bold", color=TEAL,
            ha="center", va="center")
    ax.text(6.5, 1.7, "pigs fly when a gateway lends them wings",
            family="DejaVu Sans", fontsize=20, color=TXT,
            ha="center", va="center")

    # pig path: left -> right, gentle bob; flap every 3 frames
    t = i / (N_FRAMES - 1)
    x = -2.5 + t * 16.5
    y = 4.9 + 0.35 * np.sin(t * np.pi * 3)
    pig = FRAME_A if (i // 3) % 2 == 0 else FRAME_B

    # motion streaks trailing behind the pig
    if 0 < i < N_FRAMES - 1:
        ax.text(x - 0.55, y + 0.5, "- - -", family="Consolas",
                fontsize=15, color=TEAL, alpha=0.6, ha="right", va="center")
    ax.text(x, y, pig, family="Consolas", fontsize=15, color=AMBER,
            ha="left", va="top", linespacing=1.05,
            bbox=dict(boxstyle="square,pad=0.25", fc=BG, ec="none",
                      alpha=0.88))
    fig.savefig(f"fly_frames/f{i:03d}.png", facecolor=BG)
    plt.close(fig)

for i in range(N_FRAMES):
    render(i)

subprocess.run(["ffmpeg", "-y", "-v", "error", "-framerate", str(FPS),
                "-i", "fly_frames/f%03d.png", "-c:v", "libx264",
                "-pix_fmt", "yuv420p", "ascii_fly_test.mp4"], check=True)
print("saved ascii_fly_test.mp4")

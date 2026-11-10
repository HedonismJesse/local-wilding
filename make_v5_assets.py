"""Video v5 assets: designed cards, animated verdict chart, ambient audio bed."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import wave, struct

W, H = 1298, 1246
SLATE = "#0D1B26"; TEAL = "#3FD9A8"; AMBER = "#FFB84D"; MUTED = "#5B7284"
LIGHT = "#CFE8DF"; RED = "#E45555"; PINK = "#F5A0B5"

def font(name, size, weight="normal"):
    for cand in (name, "DejaVu Sans"):
        try:
            return fm.FontProperties(family=cand, size=size, weight=weight)
        except Exception:
            continue
    return fm.FontProperties(size=size)

F_BIG = font("Segoe UI", 92, "bold"); F_MID = font("Segoe UI", 40)
F_SM  = font("Segoe UI", 28); F_XS  = font("Segoe UI", 22)
F_TAG = font("Consolas", 24, "bold")

def canvas(fname=None):
    fig = plt.figure(figsize=(W/100, H/100), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H)
    ax.axis("off")
    # vertical gradient bg
    g = np.linspace(0, 1, 256).reshape(-1, 1)
    ax.imshow(g, extent=[0, W, 0, H], aspect="auto", zorder=0,
              cmap=matplotlib.colors.LinearSegmentedColormap.from_list(
                  "bg", ["#0A141C", "#12242F", "#0D1B26"]))
    # subtle vignette: black layer whose alpha rises toward edges
    yy, xx = np.mgrid[0:100, 0:100]
    d = np.sqrt(((xx-50)/50)**2 + ((yy-50)/50)**2)
    ax.imshow(np.zeros_like(d), extent=[0, W, 0, H], aspect="auto",
              cmap="gray", vmin=0, vmax=1,
              alpha=np.clip((d-0.6)*0.5, 0, 0.35), zorder=1)
    return fig, ax

# ---------- 1. TITLE BG (pig overlays in ffmpeg) -------------------------
fig, ax = canvas()
ax.text(W/2, H*0.62, "local-wilding", ha="center", va="center",
        color=TEAL, fontproperties=F_BIG, zorder=3)
ax.text(W/2, H*0.50, "pigs fly when a gateway lends them wings",
        ha="center", va="center", color=LIGHT, fontproperties=F_MID, zorder=3)
ax.text(W/2, H*0.42, "a 1B local model does real research - tools, budget, receipts",
        ha="center", va="center", color=MUTED, fontproperties=F_SM, zorder=3)
ax.text(W/2, H*0.10, "devs-wilding submission - Mozilla Otari",
        ha="center", va="center", color=MUTED, fontproperties=F_TAG, zorder=3)
fig.savefig("card_title_bg.png"); plt.close(fig)

# ---------- 2. RECAP CARD ------------------------------------------------
fig, ax = canvas()
ax.text(W/2, H*0.90, "what you just watched", ha="center", va="center",
        color=TEAL, fontproperties=font("Segoe UI", 52, "bold"), zorder=3)
rows = [
    "local arm - llamafile 1B, zero tools, answers from weights",
    "hosted arm - Otari tools declared only when proven available",
    "cap refused a call BEFORE dispatch - the allowance holds",
    "reserve/settle ledger - every cent accounted, append-only",
    "decision receipt on every call - candidate, model, cost, outcome",
    "self-score 9/9 - the demo grades its own claims against files",
]
y0 = H*0.78
for i, r in enumerate(rows):
    ax.text(W*0.08, y0 - i*H*0.085, "[x]  " + r, ha="left", va="center",
            color=LIGHT, fontproperties=font("Consolas", 20), zorder=3)
ax.text(W/2, H*0.20, "github.com/HedonismJesse/local-wilding",
        ha="center", va="center", color=TEAL, fontproperties=F_SM, zorder=3)
ax.text(W/2, H*0.14, "branch devs-wilding  -  first Otari commit cb6f106",
        ha="center", va="center", color=MUTED, fontproperties=F_XS, zorder=3)
fig.savefig("card_recap.png"); plt.close(fig)

# ---------- 3. ANIMATED VERDICT (5s anim, then hold) ---------------------
fig = plt.figure(figsize=(W/100, H/100), dpi=100)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 16); ax.set_ylim(0, 10)
ax.axis("off")
g = np.linspace(0, 1, 256).reshape(-1, 1)
ax.imshow(g, extent=[0, 16, 0, 10], aspect="auto", zorder=0,
          cmap=matplotlib.colors.LinearSegmentedColormap.from_list(
              "bg", ["#0A141C", "#12242F", "#0D1B26"]))
ax.text(8, 9.2, "THE VERDICT", ha="center", color=TEAL,
        fontproperties=font("Segoe UI", 60, "bold"))
ax.text(8, 8.4, "India population grew more than 15% between 2015 and 2023?",
        ha="center", color=LIGHT, fontproperties=font("Segoe UI", 26))
ax.set_xlim(0, 16); ax.set_ylim(0, 10)

b1 = ax.barh(6.3, 0.01, height=1.1, color=AMBER, zorder=3, left=1.5)[0]
b2 = ax.barh(4.3, 0.01, height=1.1, color=TEAL, zorder=3, left=1.5)[0]
lbl1 = ax.text(1.5, 7.2, "the claim: > 15%", color=AMBER,
               fontproperties=font("Consolas", 26, "bold"), va="center")
lbl2 = ax.text(1.5, 3.5, "verified by code: 9.0%", color=TEAL,
               fontproperties=font("Consolas", 26, "bold"), va="center")
gap = ax.annotate("", xy=(13.4, 6.3), xytext=(11.0, 4.3),
                  arrowprops=dict(arrowstyle="->", color=RED, lw=4), zorder=5)
gap.set_visible(False)
gap_txt = ax.text(12.6, 5.3, "off by 6 points\n~78 million people", color=RED,
                  fontproperties=font("Consolas", 24, "bold"), ha="center",
                  va="center", zorder=5, alpha=0)
stamp = ax.text(8, 1.6, "FALSE", ha="center", color=RED,
                fontproperties=font("Segoe UI", 96, "bold"), alpha=0,
                zorder=6, rotation=-4)
src = ax.text(8, 0.7, "computed by otari_code_execution server-side - receipted in evidence/",
              ha="center", color=MUTED, fontproperties=font("Consolas", 18))

# scale: bars max widths -> claim 15 -> x 11.5 ; real 9 -> x 7.0
def ease(t):  # ease-out cubic
    return 1 - (1 - t) ** 3

import matplotlib.animation as anim
FPS, SECS_ANIM = 30, 4.5
def update(f):
    t = f / (FPS * SECS_ANIM)
    a = ease(min(1, t / 0.45))          # claim bar 0-45%
    b = ease(min(1, max(0, (t - 0.35)) / 0.45))  # real bar lags
    b1.set_width(11.5 * a); b2.set_width(7.0 * b)
    lbl1.set_alpha(min(1, t / 0.2)); lbl2.set_alpha(min(1, max(0, t - 0.3) / 0.2))
    if t > 0.72:
        gap.set_visible(True)
        gap_txt.set_alpha(min(1, (t - 0.72) / 0.12))
    if t > 0.85:
        stamp.set_alpha(min(1, (t - 0.85) / 0.10))
        s = 1 + 0.25 * max(0, 1 - (t - 0.85) / 0.12)  # overshoot pop
        stamp.set_fontsize(96 * s)
    return b1, b2, stamp

ani = anim.FuncAnimation(fig, update, frames=int(FPS * SECS_ANIM),
                         interval=1000 / FPS, blit=False)
ani.save("verdict_anim.mp4", writer="ffmpeg", fps=FPS,
         savefig_kwargs={"facecolor": "#0A141C"})
plt.close(fig)

# ---------- 4. AMBIENT PAD + STAMP PING (192s) ----------------------------
sr = 22050; T = 192
t = np.arange(int(sr * T)) / sr
chord = (np.sin(2*np.pi*110*t)*0.5 + np.sin(2*np.pi*164.8*t)*0.28
         + np.sin(2*np.pi*220*t)*0.22 + np.sin(2*np.pi*277.2*t)*0.12)
lfo = 0.7 + 0.3 * np.sin(2*np.pi*0.07*t)
bed = chord * lfo * 0.045
# gentle ping at verdict stamp (~t=166s of final cut)
ping_t = 166.0
dt = t - ping_t
env = np.where(dt >= 0, np.exp(-np.maximum(dt, 0) * 6), 0.0)
bed += np.sin(2*np.pi*880*t) * env * 0.05
# fade in/out
bed *= np.minimum(1, t / 3) * np.minimum(1, (T - t) / 4)
pcm = (np.clip(bed, -1, 1) * 32767).astype(np.int16)
with wave.open("pad.wav", "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes(pcm.tobytes())
print("assets done")

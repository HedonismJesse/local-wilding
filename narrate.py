"""Generate per-beat narration WAVs for the console-cut video via pocket-tts (CPU)."""
import subprocess, sys, os

# (filename, narration text) — beat order matches the 8-shot storyboard
SEGMENTS = [
    ("n0.wav",
     "A one-billion-parameter model answered with sources. None of them "
     "exist. This is the console that proves it."),
    ("n1.wav",
     "One harness, any OpenAI-compatible endpoint — Otari, a llamafile, "
     "or your own gateway."),
    ("n2.wav",
     "Real use first. Dispatch a claim — the feed streams every step: "
     "the model the endpoint picked, the tools that ran server-side, the "
     "settled cost. Then a receipt mints — model requested versus served, "
     "tools declared versus ran, the hash of what was asked and answered, "
     "linked to the raw response."),
    ("n3.wav",
     "The demo button is the behind-the-scenes cut. Same task, two arms: "
     "on the left a one-billion local model with no tools — it fabricates "
     "a source. On the right, the gateway arm — code execution runs "
     "server-side, every call receipted, cost settled to six decimals."),
    ("n4.wav",
     "Set the allowance to a cent and the call refuses before it is ever "
     "dispatched. The ledger counts what enforcement saved."),
    ("n5.wav",
     "Every dispatch, human-verifiable — hashes, raw files, export to "
     "JSON or CSV."),
    ("n6.wav",
     "Clone, install three lines, run app dot py, click."),
    ("n7.wav",
     "Tools, budgets, receipts, a local control arm — and the honest "
     "limits printed where you can see them."),
]

os.makedirs("narration", exist_ok=True)
for name, text in SEGMENTS:
    out = os.path.join("narration", name)
    if os.path.exists(out):
        continue
    r = subprocess.run(
        [sys.executable, "-m", "pocket_tts", "generate",
         "--text", text, "--output-path", out],
        capture_output=True, text=True)
    print(name, "rc=", r.returncode, r.stderr[-200:] if r.returncode else "")

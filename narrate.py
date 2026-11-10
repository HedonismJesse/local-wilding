"""Generate per-beat narration WAVs for the demo video via pocket-tts (CPU)."""
import subprocess, sys, os

# (filename, start_seconds_in_final_cut, narration text)
SEGMENTS = [
    ("n0.wav", 1.0,
     "A one-billion-parameter model on a laptop does real research, "
     "because a gateway lends it tools, a budget, and receipts."),
    ("n1.wav", 12.0,
     "First question: what can this key actually do? The gateway answers "
     "for itself. Web search and fetch are disabled on this workspace. "
     "Code execution is live. The demo declares only what it can prove."),
    ("n2.wav", 42.0,
     "Two arms, one task. On the left, a llamafile one-billion model with "
     "no tools. It answers from its weights, and fabricates a source. On "
     "the right, the same loop through hosted Otari: code execution runs "
     "server side, every call receipted, cost settled to six decimals."),
    ("n3.wav", 82.0,
     "Then the allowance holds. A one-cent cap refuses the call before it "
     "is ever dispatched. And every claim on screen is backed by a file: "
     "raw gateway responses, an append-only spend ledger, a decision "
     "receipt per call, and a scorer grading the demo itself. Nine of nine."),
    ("n4.wav", 162.0,
     "The claim said more than fifteen percent. Server-side code computed "
     "nine point zero. Off by seventy-eight million people. False."),
    ("n5.wav", 177.0,
     "Local model, zero tools. Hosted tools, real receipts, budget "
     "refusal before dispatch. Pigs fly when a gateway lends them wings."),
]

os.makedirs("narration", exist_ok=True)
for name, start, text in SEGMENTS:
    out = os.path.join("narration", name)
    if os.path.exists(out):
        continue
    r = subprocess.run(
        [sys.executable, "-m", "pocket_tts", "generate",
         "--text", text, "--output-path", out],
        capture_output=True, text=True)
    print(name, "rc=", r.returncode, r.stderr[-200:] if r.returncode else "")

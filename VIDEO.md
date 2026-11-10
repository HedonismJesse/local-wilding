# Demo video — shot list (3–5 min, terminal capture, no narration needed)

Four beats. On-screen captions carry the story; no voiceover required.
Captions are beat banners typed into the terminal itself —
`=== BEAT 2: the tools it never had ===` — zero editing, no mic,
no face. Record the terminal window only (Win+G or OBS).
Every claim shown is something the camera just watched happen.

## Beat 1 — local arm (~1:00) "weights only, no tools"

- Terminal: `python local_arm.py` (or `demo.py --local-only`)
- Camera shows: a small local model answering the task from its own
  weights — no search, no code exec, no network. Caption: the honest
  limit it hits.
- Fallback if no local server: replay-labeled local run, labeled
  "recorded" on screen — honesty is the convention this field rewards.

## Beat 2 — gateway arm (~1:30) "the tools it never had"

- Terminal: `python demo.py`
- Camera shows: the same loop routed through api.otari.ai —
  `otari_tool_calls` lines printing web_search + code_execution firing,
  `usage.cost_usd` per call, per-candidate receipts after the run.
- Caption: "the model didn't change — the substrate did."

## Beat 3 — live refusal (~1:00) "the cap fires on camera"

- Terminal: `DEMO_BUDGET_USD=0.05 python demo.py`
- Camera shows: the ledger's `refuse` event mid-run — pre-dispatch
  refusal, spend stops at the cap, receipt row records it.
- Caption: "not a config promise — a ledger row that fired."

## Beat 4 — receipts + self-score (~0:30) "the receipts are the demo"

- Terminal: `ls evidence/` → raw response JSON, spend_ledger rows,
  receipts.jsonl; then `python sphere_fitness.py`
- Camera shows: certificate checks green on the beats just filmed;
  scorer exits 0.
- Caption: "we built an instrument that grades this submission on the
  receipts it emits."

Total ~4:00. Cut rule: if over 5:00, beat 1 runs silently under beat
2's captions — the local arm stays but narrates itself.

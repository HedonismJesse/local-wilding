# Buidl submission — local-wilding

**Project name:** local-wilding

**Tagline:** A receipts-first harness — point it at Otari, a llamafile,
or your own OpenAI-compatible endpoint.

**One-liner:** A 1B local model answers research claims from weights —
and cites sources that don't exist. Otari supplies the tools it's
missing; every dispatch mints a hash-verifiable receipt.

## What it is

A single-file browser console (Python stdlib only, `app.py`) that runs
the same task through two arms:

- **Local arm** — `Llama-3.2-1B-Instruct-Q6_K.gguf` on a local
  OpenAI-compatible server (llamafile / llama.cpp / LM Studio). No
  tools, $0. On our demo task it computed ≈11% and called it "more than
  15%", citing plausible-looking URLs that don't resolve.
- **Gateway arm** — `openai/gpt-oss-120b` through `api.otari.ai`.
  `otari_code_execution` ran server-side on camera; `usage.cost_usd`
  settles to six decimals where Otari reports it.

Every dispatched call mints a **receipt**: id, endpoint, model
requested vs **served**, tools declared vs **ran**, prompt, answer,
cost, `sha256(prompt)`, `sha256(answer)`, and a link to the raw
response file under `evidence/`. The hash is locally recomputable —
it is not an Otari signature (Otari doesn't sign responses; that's
feedback Q2).

Budget enforcement is **pre-dispatch**: the ledger reserves the
estimated cost and refuses before the call is made if it would breach
the cap; actual cost settles after. The collapsed ledger bar reads
spent / saved / refusals / cap live.

`LW_REPLAY=1` serves recorded evidence — no keys, no spend — the shape
a public demo takes without fielding anyone's API keys.

## Features exercised (and what we did NOT claim)

- Chat completions, local + hosted: exercised.
- Server-side tools: **`otari_code_execution`** exercised live.
  `otari_web_search` / fetch remained `workspace_disabled` on our
  account — **not claimed**.
- Budgets / cost readback: exercised; `usage.cost_usd` read when
  present, receipts honestly show $0 where it's absent.
- Virtual keys: dashboard-only in practice (hosted keys API returns
  401 without a master key) — not claimed as exercised.

## Links

- Repo: `https://github.com/HedonismJesse/local-wilding` (`devs-wilding`)
- First Otari-wiring commit: `cb6f106`
- Demo video: `local-wilding-demo-v9.mp4` (3:03, console-centered)
- Issue filed: `mozilla-ai/otari#3075` — `/devs-wilding` URL regression
  erasing the challenge's own rules page.

## Feedback (Q1–Q3)

- **Q1 (friction):** virtual-key minting is dashboard-gated — the
  hosted keys API 401s without a master key, so the harness stands in
  a client-side role-map during setup. Search/fetch stayed
  `workspace_disabled`, so only code execution is exercised.
- **Q2 (what to build):** `POST /estimates` — price a call before
  spending it — would retire our client-side reservation math entirely.
  Signed responses would make receipts third-party-verifiable; today
  the hash anchor is ours alone.
- **Q3 (would we keep using it):** for the local arm, yes — server-side
  tools on a tool-less 1B model is a real capability add, not a demo
  flourish. For a pure-cloud stack the delta narrows to budgets +
  observability versus the added hop.

## Honest limits

- Receipts mint per **job** — raw calls inside a multi-step run are
  recorded, but the receipt is minted at job end, not per step.
- Replay mode is labeled and serves recorded evidence; live mode needs
  your endpoint and key.
- The local arm's availability depends on your local server; replay
  substitutes its recorded run with a visible badge.

# local-wilding

**A 1.5B local model with no tools does real research — the gateway lends it
search, code execution, a fallback brain, and an allowance.**

Built for MozFest's **Developers Wilding: Online** hackathon
(Oct 28 – Nov 11, 2026). Everything runs on
[Otari](https://github.com/mozilla-ai/otari), Mozilla AI's open-source
AI gateway — and the client itself is **zero-dependency stdlib Python**.
No SDK: one key, one endpoint, receipts on every call.

## The split nobody else demoed

| Arm | Model | Tools | Spend |
|-----|-------|-------|-------|
| **Local** | llamafile / llama.cpp / LM Studio — any local OpenAI server | none — answers from its weights | $0 |
| **Gateway** | open-weights through hosted Otari (+ frontier fallback candidate) | `otari_web_search` + `otari_code_execution`, run *server-side* | capped, ledgered, receipted |

The local arm is the honest baseline: same loop, same task, no tools.
The gateway arm is Otari's own headline claim — *"give open-weight models
the tools they're missing"* — proven on a truly local model.

## Otari features exercised

- **Chat completions** via `api.otari.ai` (OpenAI-compatible)
- **Server-side tools** — `otari_web_search`, `otari_code_execution`;
  executions surface in `otari_tool_calls` and are printed live
- **Budgets** — mirrored client-side: `ledger.py` reserves an estimate
  *before* dispatch and refuses the call if it would breach the cap
  (a typed `BudgetRefused`, shown live in beat 3)
- **Routing / fallback** — weighted-draw-without-replacement ordering
  over candidates; a 503 sheds to the tail for free
- **Usage & cost** — `usage.cost_usd` settled per call; totals printed
- **Decision receipts** — every attempt logs rationale + confidence +
  `selection_reason` to `evidence/receipts.jsonl`

## The adopted patterns (client-side, in this repo)

We read the gateway's source and rebuilt three of its mechanisms thin:

| Their machinery (`src/gateway/`) | Ours |
|---|---|
| `services/budgets/` — reserve/settle, refuse before dispatch | `ledger.py` (~60 lines) |
| `services/routing/weighted.py` — draw w/o replacement, drain ≠ delete | `decide.weighted_ordering` |
| `RoutingDecision` rationale/confidence + `explain` dry-run | `decide.Receipt` + `decide.explain` |

## Run it

```bash
export OTARI_API_KEY=...           # hosted otari.ai key
export LOCAL_BASE_URL=http://localhost:8080/v1   # optional: llamafile etc.
python demo.py "your claim to verify"            # three beats
python demo.py --replay                          # offline, serves evidence/
python tests.py                                  # zero-network smoke
```

`evidence/` holds every raw response, the spend ledger, and the receipt
log — audit any claim by file, or replay the whole run with no key.

## Honest limits

- Local arm skips loudly when `LOCAL_BASE_URL` is unset — marked, never claimed.
- Virtual keys were dashboard-created (hosted keys API wants a master key —
  verified 401); stated, not worked around.
- `cost_usd` is read back from `usage` — where a provider doesn't report
  it, settled cost is 0 and the receipt says so.

## Feedback summary (full answers in the buidl)

- Most tempted to skip Otari when: minting scoped keys needed the
  dashboard (hosted keys API 401s on workspace keys) — a role-map had
  to stand in client-side.
- Built what Otari should've: the pre-dispatch cost *estimate* —
  `POST /estimates` (price a call before spending it) would retire our
  client-side reservation math.
- Keep using it without the rule? For the local arm, yes — server-side
  tools on a tool-less model is a real capability add, not a tax.

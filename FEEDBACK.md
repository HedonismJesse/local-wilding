# Otari feedback — Devs Wilding submission

**Q1 — When were you tempted to skip Otari?**

Virtual-key minting. On hosted otari.ai, the keys API requires the
master key (401 for user keys — same wall VaultMind's buidl hit), so
per-role keys meant dashboard clicks rather than the OpenAI-compatible
surface everything else rides. During scaffolding a client-side
role-map stood in — and once the shim existed, the temptation was to
keep it and skip the dashboard entirely.

Second data point, honestly: the `otari.ai/devs-wilding` URL now
serves the product landing page — the challenge's own rules page
regressed mid-event. We corroborated requirements via the organizer's
GitHub post (mozilla-ai/llamafile discussion #1074) instead.

**Q2 — What did you build that Otari should have?**

A client-side reserve/settle spend ledger plus decision receipts —
thin rebuilds of machinery that lives inside the gateway
(`services/budgets/` reservation + settlement paths, routing
`weighted.py` draw-without-replacement). Ours reserves an estimate
*before* dispatch and refuses pre-flight on breach; Otari's own
reservation machinery is the obvious model, but there's no endpoint
to *price* a call before spending it. A `POST /estimates` (usage
estimate + price quote per candidate) would retire the entire
client-side ledger — the reservation pattern exists, the read path
doesn't.

Adjacent: our `explain` dry-run prints the candidate ordering with
weights without dispatching. A `Otari-Routing-Explain` response
header (or `?dry_run=1`) would give every client the same "why this
provider" answer for free.

**Verified during live debugging (all on camera-reproducible evidence
in `evidence/`):**

- `GET /api/v1/tools` is genuinely good — per-tool `available` +
  `reason` + accepted wire spellings + input schemas. It's the
  discoverability surface every client wants; cite it in docs more.
- Workspace web-search/web-fetch default OFF is defensible policy,
  but the 403 carries only `"web search is not enabled for this
  workspace"` — pointing at the dashboard path (Tools → workspace
  policy) in the error would save every new user a source dive.
- `Otari-Tags` rejects bare tags (`each tag must be key=value`) —
  strict is fine, but the OpenAPI request example should show one
  `key=value` pair explicitly; we hit the 422 on our first call.
- `usage.cost_usd` as a six-decimal string + `pricing_source` +
  `Otari-*` response headers (`otari-provider`, `otari-model`,
  `otari-attempt-count`, `otari-fallback`) made the receipt layer
  nearly free to build — the response carries its own provenance.

**Q3 — Would you keep using Otari without the rule?**

For the local-model arm: yes, genuinely — server-side tools on a
tool-less model is a real capability add, not a convenience. The
local model cannot search or execute code at all; the gateway grants
it both without client machinery.

For a pure-cloud stack: the delta narrows to budgets, keys, and
observability versus the added hop — worth it where spend controls
matter, thinner where they don't.

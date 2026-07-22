---
title: "FIFO v4 gross/net metrics and analysis-status model"
category: decision
status: resolved
date: 2026-07-22
tags: [backend, frontend, fifo, net-metrics, status, data-quality]
related: [fifo-v4-engine-architecture, fifo-v4-cost-allocation-ladder, entities/fifo-lot-engine, concepts/gross-net-dual-reporting, problems/datatable-net-columns-hidden-override-model]
---

# Decision: FIFO v4 gross/net metrics and analysis-status model

## Context
Two related design questions: (1) how to introduce "net" (fee/tax-adjusted) performance figures without
touching the existing gross math that many other parts of the system already trust, and (2) how to represent
*reliability* of a lots-analysis result now that it can fail or degrade in more ways than before (quantitative
replay failure vs. a local economic/orphan issue).

## Options Considered
- **Net metrics**: fold fees/taxes directly into `original_cost` (or another gross accumulator) vs. **keep all
  gross accumulators untouched and add separate `allocated_fees`/`allocated_taxes` accumulators, computing net
  once from gross** — chosen the latter: no double counting, gross values stay bit-for-bit comparable to
  pre-v4 behavior, net becomes an explicit, always-derived value.
  - A deliberate asymmetry was kept: the per-lot **history** series reports a *capital-only* net P&L
    (`pnl_i - Fees_i - Taxes_i`, excludes income), while the lot **summary**'s `net_total_pnl`/`net_total_return`
    are income-inclusive. Each net figure mirrors its own gross counterpart minus costs — it's not a single
    global "net mode" toggle.
- **Status model**: the legacy single global `UNAVAILABLE` meant "empty / not computed" for the whole result.
  v4 needed to distinguish (a) an overall-replay-breaking failure from (b) a lot-local economic issue, and (c)
  the DTO's public field name (`calculation_status`) could not churn for existing clients. Options: rename the
  public field; reuse one status enum for both engine-internal and per-lot needs; or **split into two enums and
  keep the DTO field name mapped 1:1** — chosen the split:
  - Internal engine: `analysis_status = COMPLETE | DEGRADED | FAILED` (mapped 1:1 to the public
    `calculation_status` field, so no client-facing rename).
  - Per lot: `LotNetMetricsStatus = AVAILABLE | UNAVAILABLE`.
  - `FAILED` scope: binary COMPLETE/DEGRADED, or a broader FAILED, or isolate every conservation failure
    locally — chosen: **FAILED is reserved for non-isolable quantitative failures** (topology/replay corruption
    that contaminates everything downstream); local economic issues (e.g. an orphan cost/income event) stay
    DEGRADED, because they don't invalidate the rest of the result.
- **UI reaction to FAILED**: hide all data vs. **"warn but show"** — chosen show: the frontend renders a
  failure banner but still displays whatever data is available, rather than blocking the view.
- **Net-column visibility**: always show net columns by default vs. **dynamic default based on `hasNetCosts`**
  (only show them when at least one row actually has allocated costs) — chosen dynamic, to match the existing
  `asset-income` column convention and avoid clutter on portfolios with no fees/taxes. This surfaced a real bug
  in the visibility implementation, see [[problems/datatable-net-columns-hidden-override-model]].

## Decision
Gross accumulators (`original_cost`, `sale_proceeds`, `gross_income`, `open_value`, …) are never modified; net
figures are always computed as gross minus `allocated_fees`/`allocated_taxes`. Reliability is represented by two
independent status layers (global `analysis_status`/`calculation_status` for replay-level reliability; per-lot
`LotNetMetricsStatus` for net-metric availability), with `FAILED` reserved for genuinely non-isolable
quantitative corruption. Net table columns default to visible only when relevant.

## Consequences
- Existing consumers of gross fields see zero behavior change.
- `net_metrics_status` exists end-to-end in DTO and UI but is **currently dead in practice**: the implemented
  service always falls back to the native amount on an FX miss and always computes a net value, so no code
  path ever actually emits `UNAVAILABLE` today. Documented as a known latent/unreachable state, with a
  post-review recommendation to remove the field later rather than leave it as a false signal of future
  intent — not fixed in this round.
- An empty lots-analysis result migrates from the old global `UNAVAILABLE` to `COMPLETE` with `lots=[]` — a
  visible semantic change for any code branching on the old empty-state value.
- `LotsAnalysisPanel.svelte` must keep rendering data under FAILED, not just show a blocking error state.

## Related
- [[concepts/gross-net-dual-reporting]]
- [[problems/datatable-net-columns-hidden-override-model]]
- [[fifo-v4-engine-architecture]]
- [[entities/fifo-lot-engine]]
- [[sources/fifo-v4-fee-tax-integration]]

## Source files

| Role | Path |
|------|------|
| Gross/net model | `LibreFolio_developer_journal/RoadmapV4_UI/fifo-engine/v4-fee_tax_integration/hig-level-analysis-v5.md` §2.4, §17-§18 |
| Status model | `.../v4-fee_tax_integration/hig-level-analysis-v5.md` §22; `implementation-plan-v5.md` Fase 8 |
| Dead `net_metrics_status` finding | `.../v4-fee_tax_integration/post-implementation-review-v5.md` §5; `review-checklist-v5.md` D3/R4 |
| Net-column visibility fix | `.../v4-fee_tax_integration/post-implementation-review-v5.md` §2; `review-checklist-v5.md` D1 |
| Public DTO | `backend/app/schemas/portfolio.py` |
| Engine | `backend/app/services/fifo_lot_engine.py` |
| Frontend table | `frontend/src/lib/components/brokers/lots/UnifiedLotsTable.svelte` |
| Frontend panel (FAILED banner) | `frontend/src/lib/components/brokers/lots/LotsAnalysisPanel.svelte` |
| User-facing doc | `mkdocs_src/docs/financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.en.md` §"Costs & Net Metrics" → "Gross vs net" |

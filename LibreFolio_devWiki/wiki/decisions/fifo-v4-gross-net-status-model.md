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
  **Superseded on 2026-10-17** by N81 (option A, J-12): see «Revision» below.
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
  (Until 2026-10-17; see «Revision».)

## Revision — 2026-10-17: a FAILED analysis explains and hides (N81, option A; J-12)

**Why it changed.** "Warn but show" drew the lots of a replay that had failed. W's test-author found the case (V-3,
mirror case, confirmed by J on 15/10): an orphan outgoing TRANSFER is skipped by the replay (`TRANSFER_PAIR_MISSING`),
so the lot kept 10 units open, worth 300 with a P&L of 100, while the position and the average-cost lines said 6.
A red line saying «figures may be incomplete» did not stop a non-expert user from reading those figures.

**The decision** (the coordinator's N81, option A; the developer's D1–D3, 17/10):
- **Backend (J).** On FAILED the response's lot-derived sections are null: lots, Gantt segments, custody history,
  lot events, value, return and performance histories, income events, economic allocation groups, `price_history`
  (it is per lot), and the asset's orphan income, fees and taxes. What stays: the broker and combined average-cost
  histories (they come from the average cost, not from FIFO), `quote_base_quantity`, the metadata and
  `data_quality`. Each blocking issue (a code of `_QUANTITATIVE_FAILURE_CODES`) carries `transaction_date` and
  `fails_analysis: true`; on FAILED only the blocking issues and the gaps of the average-cost lines are kept. AI
  Export carries only the blocking `failure_codes`.
- **Panel (Y).** On FAILED the panel takes no lot-derived section, even from an answer cached before the change; the
  first chart keeps only the average-cost lines (no market line: it is the union of the per-lot price points), and
  the Gantt, the table and the comparison are not drawn. `LotAnalysisFailedNotice` explains, then lists one row per
  (code, transaction): the day, the broker's name from the panel's broker list (`#<id>` only for a broker the list
  lacks; both callers pass a list that covers the analysis scope), the message, and a
  button to `/transactions?highlight=<id>`. The way in is `transaction_id` only: `related_transaction_id` may name a
  partner leg the user cannot see. The `fails_analysis` flag decides what goes to the notice, so the frontend keeps no
  copy of the code list; the banner keeps the rest.
- **Left out, then added the same evening (Y-30, 2026-10-17, decision N89 «always»)**: a lot-free market-price
  series, `MARKET_PRICE_HISTORY` / `market_price_history` — one point a day of the window with a convertible mark,
  whatever lots are open. It joins the analyses a FAILED replay still answers (`_AVERAGE_COST_ANALYSES` became
  `_REPLAY_FREE_ANALYSES`), with its missing rates kept in `data_quality`. The panel draws the price line, the axis
  dates and the bubbles from it in every analysis, and no longer requests the per-lot `PRICE_HISTORY` (still in the
  API): a FAILED chart keeps its price line, and the line no longer breaks off on days without an open lot.

**What it costs.** A FAILED asset shows no lot until its transactions are fixed. The two halves must reach the target
branch together: a panel without the backend half finds no flagged issue, so its notice lists nothing and the
blocking issues fall back to the banner.

## Related
- [[concepts/gross-net-dual-reporting]]
- [[problems/datatable-net-columns-hidden-override-model]]
- [[decisions/fifo-v4-engine-architecture]]
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
| Engine | `backend/app/services/financial_math/fifo/engine.py` |
| Frontend table | `frontend/src/lib/features/brokers/lots/UnifiedLotsTable.svelte` |
| Frontend panel (FAILED: explain and hide, since 2026-10-17) | `frontend/src/lib/features/brokers/lots/LotsAnalysisPanel.svelte` |
| Lot-free market price line (Y-30) | `backend/app/services/financial_math/lots/histories.py` (`build_market_price_history`), `frontend/src/lib/features/brokers/lots/lotWacPriceChartHelpers.ts` (`marketPriceLine`), `backend/test_scripts/test_services/test_financial/test_lots_market_price_history.py` |
| Failure notice and its helpers | `frontend/src/lib/features/brokers/lots/LotAnalysisFailedNotice.svelte`, `frontend/src/lib/features/brokers/lots/lotDataQualityHelpers.ts` |
| Blocking codes | `backend/app/services/financial_math/fifo/models.py` (`_QUANTITATIVE_FAILURE_CODES`) |
| N81 / J-12 record | `LibreFolio_developer_journal/Release_2/Phase_1/09_dashboardCharts/plan-phase01DashboardCharts.prompt.md` §«J-12, la metà del pannello» |
| User-facing doc | `mkdocs_src/docs/financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.en.md` §"Costs & Net Metrics" → "Gross vs net" |

---
title: "Lots Analysis Service"
category: entity
type: service
updated: 2026-10-07
tags: [backend, fifo, lots, orchestration, fx, wac, average-cost, data-quality]
related:
  - entities/fifo-lot-engine
  - entities/portfolio-engine
  - decisions/fifo-v4-engine-architecture
  - decisions/fifo-v4-gross-net-status-model
  - decisions/financial-math-single-average-cost
  - problems/fifo-income-silently-dropped-after-full-close
  - problems/zero-purchase-cost-foreign-asset-paid-in-report-currency
  - concepts/fifo-lot-tracking
---

# Lots Analysis Service

## Role

Orchestration layer between the API and [[entities/fifo-lot-engine]]. Owns FX resolution, builds the engine's
economic input objects, invokes the engine, and maps its output back into the public API response (fee/tax/
income breakdowns, net summary and history series, status). As of v4 it is **no longer the allocator of
record** for income — that logic moved into the engine itself (see [[decisions/fifo-v4-engine-architecture]]).

Since 2026-10-07 it also no longer computes the **WAC lines** (per broker and cumulative) itself: they come from the
single average-cost function of the `financial_math` layer ([[decisions/financial-math-single-average-cost]]). FIFO
stays here only to create the lots.

## Location

`backend/app/services/lots_analysis_service.py` (~1980 lines at the v4 ingest; 2 032 lines on 2026-10-07)

## Key Interfaces

- Prepares FX rates and target-currency amounts for trades/income before building `EconomicEvent`s.
- Calls `FifoLotEngine.run(...)` and receives quantitative + economic results in one pass.
- Maps engine `EconomicAllocationGroup`/`TargetOperationAllocation`/`EconomicLotAllocation` audit objects into
  the public DTO's inline 3-level audit shape (`backend/app/schemas/portfolio.py`).
- Computes net summary and net history series from the engine's per-lot economic accumulators.
- Maps internal `analysis_status` (`COMPLETE|DEGRADED|FAILED`) to the public `calculation_status` field.
- **WAC lines (since 2026-10-07):** `_compute_average_cost_lines()` makes **one** `compute_average_costs()` call — one
  position per broker plus `"__all__"` (every broker in scope pooled), in the analysis target currency,
  `asset_leg=False`. `_average_cost_points()` samples each line with `state_at(date)`: O(D log N) instead of the old
  per-date recomputation, O(D×N). A date on which the pool lacks part of its cost has **no point** — never a guessed
  average.
- **Gaps (since 2026-10-07):** `_report_average_cost_gaps()` puts the missing report-currency conversions in
  `data_quality.missing_fx_pairs` (pair + dates) with the FX issues classified as on the portfolio banner (configured /
  real-provider pairs from `load_configured_fx_pair_sets()`), and an acquisition with no known cost in a
  `MISSING_COST_BASIS` issue; either one turns a `COMPLETE` analysis into `DEGRADED`.

## Design Notes

- **`_allocate_asset_income` was removed** — this was the pre-v4 service-level dividend/interest allocator
  (asset-wide, income-date-based, no broker scoping). It could not coexist with the engine's own D-1/
  broker-scoped allocation without risking double counting or split truth, so it was deleted as part of the
  atomic v4 merge, not deprecated gradually. See [[decisions/fifo-v4-engine-architecture]].
- The old allocator had a silent-drop bug on top of being superseded: it simply skipped an income event when
  no lot was open, losing that income with no trace. See
  [[problems/fifo-income-silently-dropped-after-full-close]] for the specific behavior fixed.
- Still the right layer for FX resolution — the engine deliberately stays FX-mechanism-agnostic and pure; this
  service is where `_FxRateResolver` actually gets called.
  Since 2026-10-07 this holds for the FIFO lots only: the WAC lines' conversions are made inside
  `compute_average_costs()`, which calls the FX service itself, at each acquisition's date.
- **Replaced 2026-10-07:** the WAC rows were built by `_build_wac_context` / `_build_wac_row` / `_compute_wac_series`
  over `compute_wac_from_txlist()`; a missing rate made a row fall back to the **unconverted** cost.
  That was one of the four average-cost implementations retired by
  [[decisions/financial-math-single-average-cost]].
- **Known limit (outside workstream P):** the FIFO lot figures still fall back to the unconverted amount when a rate
  is missing — e.g. `fx_resolver.convert(lot.original_cost, lot.currency, lot.opening_date) or lot.original_cost` in
  `_build_value_history()` and `_build_return_history()`, and the same `… or <unconverted>` shape for closure
  proceeds.

## Source files

| Role | Path |
|------|------|
| Service | `backend/app/services/lots_analysis_service.py` |
| Engine it orchestrates | `backend/app/services/fifo_lot_engine.py` |
| WAC lines (since 2026-10-07) | `backend/app/services/financial_math/average_cost.py` |
| Public DTO | `backend/app/schemas/portfolio.py` |
| Service-level tests | `backend/test_scripts/test_services/test_financial/test_lots_analysis_service.py` |
| Pure tests (WAC lines and their gaps) | `backend/test_scripts/test_services/test_lots_analysis_pure.py` |
| Lots WAC lines of the #32 case (L1–L3) | `backend/test_scripts/test_services/test_financial/test_portfolio_cost_currency.py` |
| Developer docs | `mkdocs_src/docs/developer/backend/transactions/lots_analysis_service.md` |

---
title: "FIFO Lot Engine"
category: entity
type: service
tags: [backend, fifo, lots, fee, tax, dividend, engine]
related:
  - entities/lots-analysis-service
  - entities/portfolio-engine
  - decisions/fifo-v4-income-eligibility-d1
  - decisions/fifo-v4-cost-allocation-ladder
  - decisions/fifo-v4-engine-architecture
  - decisions/fifo-v4-gross-net-status-model
  - concepts/d1-income-eligibility-window
  - concepts/deterministic-cost-matching-ladder
  - concepts/fifo-lot-tracking
  - decisions/fifo-runtime-decision
  - features/F-056
---

# FIFO Lot Engine

## Role

The canonical, pure (no I/O) engine that replays an asset's transaction history in FIFO order to produce
per-lot quantitative state (open/closed lots, custody, quantity) **and**, as of v4, per-lot economic state
(allocated income, allocated fees/taxes, net metrics, orphan totals, and a 3-level audit trail). This is now
"the FIFO engine" referenced by [[decisions/fifo-runtime-decision]] and [[features/F-056]] — those older pages
previously pointed at `transaction_service.py`, which is stale (see History below).

## Location

`backend/app/services/fifo_lot_engine.py` (~1550 lines)

## Key Interfaces

- `FifoLotEngine.run(...)` — single public entry point; owns quantitative replay **and** economic
  pooling/allocation. No parallel/legacy income or cost path is allowed to coexist alongside it.
- Input: `FifoInputTransaction` (extended in v4 with `target_amount`/`target_currency` — see
  [[decisions/fifo-v4-engine-architecture]]).
- Economic audit dataclasses (v4, new): `EconomicEvent`, `EconomicAllocationGroup`,
  `TargetOperationAllocation`, `EconomicLotAllocation`, `LotEconomicAccumulators`.
- `analysis_status`: internal 3-state (`COMPLETE | DEGRADED | FAILED`), mapped 1:1 to the public
  `calculation_status` DTO field — see [[decisions/fifo-v4-gross-net-status-model]].

## Design Notes

- **Income allocation**: D-1 eligibility, broker-scoped, transfer-aware — see
  [[concepts/d1-income-eligibility-window]] and [[decisions/fifo-v4-income-eligibility-d1]].
- **Cost allocation**: distinct deterministic ladders for FEE vs TAX, same-day mixed BUY+SELL pools split by
  value-weight, crossing trades split cost by close/open quantity ratio, unmatched pools become asset-orphan —
  see [[concepts/deterministic-cost-matching-ladder]] and [[decisions/fifo-v4-cost-allocation-ladder]].
- **Currency model**: every `EconomicEvent` carries native **and** target amounts (Option B); the engine
  compares in target currency but never resolves FX itself — the calling service does, via `_FxRateResolver`.
  The native pool is canonical; the target pool total is derived by converting the native pool exactly once
  per pool, never by summing already-converted per-event amounts.
- **Gross math is untouched**: `original_cost`, `sale_proceeds`, `gross_income`, `open_value` etc. are never
  mutated by the economic-allocation work; net figures are always gross minus allocated fees/taxes, computed
  once. See [[decisions/fifo-v4-gross-net-status-model]].
- **Only asset-linked FEE/TAX enter this engine.** Rows with `asset_id = null` never reach it — they remain
  portfolio/broker-level, handled by [[entities/portfolio-engine]] instead.
- `FAILED` status is reserved for non-isolable quantitative (topology/replay) corruption; local economic
  issues (e.g. an orphan cost/income event) are `DEGRADED`, not `FAILED` — the frontend still renders data
  under `FAILED` ("warn but show").

## Known Gotchas

- **Pre-v4 helper methods removed**: qbq-unsafe helpers like `value_for_lot()` were deleted as part of this
  work because they were not quote-base-quantity aware and risked silent bond-valuation errors; any external
  code still calling them needs to move to the qbq-aware service paths instead.
- **`net_metrics_status` (`LotNetMetricsStatus`) is currently unreachable in practice**: the implemented service
  always falls back to the native amount on an FX miss and always computes a net value, so no real code path
  emits `UNAVAILABLE` today — treat it as latent/placeholder, not as evidence that per-lot net data can
  actually be missing right now.
- **Portfolio Engine reconciliation is not implemented here**: this engine's fee/tax/income totals are not
  currently cross-checked at runtime against Portfolio Engine's independent accumulators — see
  [[decisions/fifo-v4-validation-and-scope]].

## History

| Date | Change |
|------|--------|
| v3 | Quantitative-only replay (open/closed lots, custody, quantity). No income/cost allocation. |
| 2026-07 (v4/v5, commits `32c902e0`, `e252a022`) | Added economic pooling/allocation (D-1/broker-scoped income, deterministic FEE/TAX ladders, gross/net metrics, 3-state status, inline 3-level audit). Became the single canonical FIFO path — the old service-level income allocator was deleted. See [[sources/fifo-v4-fee-tax-integration]]. |

## Source files

| Role | Path |
|------|------|
| Engine | `backend/app/services/fifo_lot_engine.py` |
| Orchestration service (calls the engine) | `backend/app/services/lots_analysis_service.py` |
| Public DTO | `backend/app/schemas/portfolio.py` |
| Engine-level tests | `backend/test_scripts/test_services/test_financial/test_fifo_lot_engine.py` |
| Developer docs | `mkdocs_src/docs/developer/backend/transactions/fifo_lot_engine.md` |
| User-facing doc | `mkdocs_src/docs/financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.en.md` |

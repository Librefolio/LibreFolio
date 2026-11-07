---
title: "PortfolioService"
category: entity
type: service
updated: 2026-10-12
tags: [backend, portfolio, service, kpi, holdings, contribution, wac, l2-cache, fastapi, average-cost, data-quality, native-cash, broker-cards, fx-on-cash]
related:
  - entities/portfolio-engine
  - entities/native-cash
  - concepts/portfolio-report-unified
  - concepts/3-pool-cash-model
  - concepts/holdings-performance-panel
  - decisions/mwrr-boundary-fix
  - decisions/portfolio-summary-direct-wiring
  - decisions/financial-math-single-average-cost
  - decisions/financial-math-one-home
  - decisions/native-cash-daily-revaluation
  - decisions/broker-card-aggregation-no-n-plus-one
  - decisions/wac-target-currency-last-acquisition
  - problems/zero-purchase-cost-foreign-asset-paid-in-report-currency
  - problems/foreign-cash-never-revalued
  - features/F-054
  - features/F-055
  - features/F-097
---

# PortfolioService

## Role

The orchestration layer between the API and the Portfolio Engine. `PortfolioService` coordinates async data loading, runs the engine, and assembles the final DTOs for API responses. It owns the L2 TTL cache, ensuring the engine runs only once per unique (user, scope, date range, currency, flags) combination.

## Location

`backend/app/services/portfolio_service.py` (~2558 lines after commit `39106380` 3-pool refactor, +612; 2 455 lines on 2026-10-07; 2 358 at `4bc7be91b`; 2 387 on 2026-11-07)

## Key Methods

| Method | Output | Notes |
|--------|--------|-------|
| `get_summary()` | `PortfolioSummary` | KPIs + holdings + allocations; since 2026-10-07 also `period_unrealized_breakdown` |
| `get_history()` / `get_history_steps()` | `PortfolioHistoryPoint[]` | NAV series + ROI metrics (steps since D-P4) |
| `get_positions_contribution()` | `PositionsContribution` | Per-asset period P&L attribution |
| `get_report()` | `PortfolioReportResponse` | **Unified**: calls engine once, then above methods |
| `get_positions_series()` | `PositionsSeriesResponse` | `POST /portfolio/positions-series`: a position's P&L and base as steps |
| `get_broker_pnl_history()`, `get_pnl_candles()`, `get_income_history()`, `get_cost_history()`, `get_deposit_history()`, `get_acquisition_funding_history()` | report sections | the per-broker P&L lines, candles and flow histories of the report |
| ~~`get_asset_history()`~~ | `AssetHistoryPoint[]` | WAC vs price series for one asset — removed 2026-07-16 (`a711d39f7`) |
| ~~`get_lots()`~~ | `FIFOLotsResponse` | FIFO lots for one (broker, asset) — removed 2026-07-16 (`a711d39f7`); the lots come from [[entities/lots-analysis-service]] (`POST /portfolio/lots/analysis`) |
| `compute_wac_iterative()` | `WACPreviewResultItem` | Module-level function, not a method. Standalone WAC for one (broker, asset, date). Since 2026-10-07 a **facade** over `compute_average_costs()` with the same signature, queries, cache and output, for the transaction preview / automatic cost basis (`transactions/auto_cost.py`) and the PAC planner (`pac_allocator/source/wac.py`); `POST /portfolio/wac` was removed on 2026-11-04 (`d5e467847`) |

## Average Cost Since 2026-10-07

The service has no average-cost arithmetic of its own any more: the Dashboard figures read the engine's result, and
the facade calls the function directly — both come from the single function of the `financial_math` layer
([[decisions/financial-math-single-average-cost]]).

| Helper | What it does |
|--------|--------------|
| `compute_wac_iterative()` | Facade: loads the (broker, asset) rows, detects split-linked ADJUSTMENTs, picks the target currency (the override, or the last acquisition's currency via `determine_target_currency()` of `financial_math/average_cost.py` — [[decisions/wac-target-currency-last-acquisition]]), calls `compute_average_costs(asset_leg=False)`, maps the steps to `WACQualifyingTX` (an unknown cost appears as `add_zero_cost`). Fail-safe unchanged: one missing conversion → `wac=None` + `wac_missing_pairs` |
| ~~`_period_realized_sales()`~~ (since 2026-10-24, J5-3 `767b2bd5d`: `period_realized_sales()` of `financial_math/portfolio/period.py`) | Realized P&L of the period = Σ (proceeds − historical cost) over the engine's `realized_sales` in `(date_from, date_to]` whose proceeds and cost are both known — no per-sale WAC query |
| ~~`_boundary_cost()`~~ (removed 2026-10-17, MF-A `170c2be3e`: the Performance table reads the engine's boundary snapshots, `financial_math/portfolio/contributions.py`) | Period-boundary cost for the positions contribution: `state_at(day).cost_report_for(qty)`, `None` while the pool is incomplete |
| `_engine_missing_fx_pairs()` | Merges the engine's movement-level `missing_fx` (any date) and per-day valuation failures (days of the period) into `missing_fx_pairs` for the banner |
| `_missing_cost_basis_assets()` | Feeds the new `MISSING_COST_BASIS` warning in `build_data_quality_report()` |
| `_unrealized_breakdown_rows()` | `period_unrealized_breakdown`: `UnrealizedBreakdownRow(kind asset\|fx\|unsplit, asset_currency, period_delta)`, deltas between the same boundary states as `period_unrealized_gain_loss_delta`, so the rows add up to it exactly |

Holdings' `wac_per_unit` is the historical WAC already in the report currency (`None` while incomplete); it is also the
Yield on Cost denominator.

## Cash from the Native-Cash Ledger (since 2026-10-11)

Lot 41 ([[decisions/native-cash-daily-revaluation]]) removed the service's own loops over the transactions for cash
(G2–G4) and its own per-broker capital: every cash figure now comes from the run's `NativeCash`
([[entities/native-cash]]), every capital figure from the engine.

| Where | What it reads (commit) |
|-------|------------------------|
| `_engine_native_cash()` | the run's ledger, or an empty one on the engine's early returns (`b11c7720e`) |
| `get_summary()` — cards | cash = `value_at(valuation_date)[b]` (a broker whose movements are all zero keeps its report-currency balance), `cash_balances` = `balances(valuation_date)`; capital and value in transit = the engine's `BrokerDailyContribution` at the valuation date (step H, `1eb487ee1`); NAV = market value + cash + in transit |
| `get_summary()` — headline and totals | headline `cash_balances` = the cards' lists summed, in access order, so the headline equals Σ cards; period and lifetime totals from `flows()` (deposits, withdrawals, fees and taxes absolute; income signed); missing pairs from `missing_conversions()` |
| `get_income_history()`, `get_cost_history()`, `get_deposit_history()` | `_signed_transaction_sums_by_date(..., native_cash=None)`: the ledger `get_report()` passes, or one built with `rates_until = date_to or today`, so rows dated after today are ignored (B12) |
| `get_positions_contribution()` | income and cost flows from `flows(date_from, effective_end)` (G4 and B14 closed); unallocated sums in access order; one «FX on cash» row per broker from `exchange_results()`, ahead of the residual, skipped below `CONVERSION_DUST` (`b11c7720e`) |

The share of a broker comes from `effective_share()` everywhere (O2); the `UserRole` import is gone.

Since T-1 (2026-10-12) the engine's names are imported from the module that defines them, the engine imports staying
lazy; the service's own `_normalize_fx_pair_slug` was removed for the public `normalize_fx_pair_slug` of
`financial_math/portfolio/data_quality.py`. ~~Still open (backlog T-R1): the service imports the private `_compute_tx_fingerprint` from the engine.~~ *2026-11-07
lint:* closed on 2026-10-17 (`170c2be3e`): `compute_tx_fingerprint` is public in `financial_math/portfolio/engine.py`. *2026-10-16,
CP-9a:* the risk service no longer calls this service's private `_get_configured_fx_pair_sets()`: `risk/data_quality.py`
reads the routes with `load_configured_fx_pair_sets(db)` from the home.

## L2 TTL Cache

`get_report()` implements a fingerprint-based cache:

```python
cache_key = (
    user_id, broker_ids, currency, date_from, date_to,
    include_summary, include_history, include_allocation_history,
    include_breakdown, include_positions_contribution,
    tx_fingerprint,    # hash of transaction IDs/dates
    price_fingerprint  # hash of last price updates
)
```

Cache invalidated on: any transaction add/edit/delete, any price update.

> 2026-11-07 lint: the block above is the original key. Today's `l2_key` in `get_report()` also carries the scope's
> sorted broker ids, the access fingerprint (`(broker_id, role, share)`, [[problems/portfolio-cache-ignored-role-and-share]]),
> `effective_date_to`, every `include_*` flag of the query (broker P&L, candles, income, cost, deposit, acquisition
> funding), `apply_ownership_share`, and the FX, yield-on-cost and asset fingerprints beside `tx_fp` and `price_fp`.

## Known Issues / Technical Debt — RESOLVED (2026-07-06, commit `35c2740c4`)

The four items below were the open technical debt tracked in `ARCHITECTURE_CURRENT_STATE.md` §5 bugs 2, 5, 6
and `implementation_status_report.md` §3. All four were closed out by the Holdings/Performance panel refactor
(see [[concepts/holdings-performance-panel]]) and confirmed resolved by exhaustive verification before the
Phase 09 M1/M2 archive (2026-07-07, [[sources/phase09-m1-m2-archive-2026-07]]):

1. ✅ **`get_summary()` now fully wired**: rewritten to read `engine_result.position_states_end` directly
   (computed by the engine exactly at `date_to`) instead of calling `compute_wac_iterative()` per asset. The
   redundant N×M DB+FX calls are eliminated. Resolved differently than originally proposed — no separate
   `DerivedViewsBuilder.build_summary()` method was introduced; wiring is direct inside `get_summary()`, backed
   by a new shared `_compute_period_summary_metrics()` helper. See [[decisions/portfolio-summary-direct-wiring]].
   *(2026-11-07 lint: that helper left the service on 2026-10-15, `8c478997f`, for `financial_math/portfolio/period.py`.)*
2. ✅ **Valuation gap closed**: holdings now use the engine's `TRANSACTION_IMPLIED` fallback
   (`open_cost_basis` as valuation proxy) when no `PriceHistory` exists — P2P/crowdfund holdings no longer show
   `current_value=None`.
   *(Drift note, 2026-10-07: the mechanism described here is not the current one — the WAC-as-price fallback was
   removed in `39106380` in favour of LAST_BUY_PRICE, see [[problems/test-transaction-implied-constructor-mismatch]],
   and the unified price resolver's `LAST_TRADE_PRICE` replaced that on 2026-07-31, commit `c770c3f7a`. Not realigned
   here: valuation was not part of workstream P.)*
3. ⚠️ **Realized P&L duplication — improved, not fully eliminated**: `_compute_period_summary_metrics()` now
   deduplicates the NAV/P&L-for-period computation shared by `get_summary()` and `get_positions_contribution()`.
   `get_report()` also passes `_precomputed_engine_result` to `get_positions_contribution()` to avoid a second
   full engine run. Whether every last per-SELL WAC computation is fully single-pass was not exhaustively
   re-verified — treat as substantially improved rather than a guaranteed zero-duplication.
   ✅ **Closed 2026-10-07** (workstream P): realized P&L and period-boundary costs now come from the engine's
   `realized_sales` and `average_costs[...].state_at()` — `get_summary()` and `get_positions_contribution()` no longer
   call `compute_wac_iterative()` per sale or per position. The same change removed the silent paths found there: a
   sale with unconvertible proceeds is left out and its pair reported, never counted with unconverted proceeds.
4. ✅ **DataQualityReport now populated**: `build_data_quality_report()` implemented and wired; `data_quality`
   field in `PortfolioSummary` / `AllocationHistoryResponse` is no longer always `None`. *(2026-11-07 lint: no
   `AllocationHistoryResponse` class exists today; the field lives on `PortfolioSummary`, and on `LotsAnalysisResponse` for the lots.)* `DataQualityBanner.svelte`
   reads the unified `data_quality` field.

### Still open (unrelated to the above, low priority)

- `internal_transfer_flow` / `scope_transfer_flow` diagnostic fields — not implemented.
- Allocation history sampling (weekly/monthly aggregation) — not implemented, daily granularity only.
- WAC fallback for in-transit cost basis — not implemented. (Since 2026-10-07 an in-transit asset *with* a frozen
  cost basis is converted once, at the arrival date; one without a cost basis still has no in-transit cost.)
- `get_asset_history()` ROI / unit-mix breakdown — still deferred.
- External cash-bridge "early withdrawal / look-ahead" edge case — unhandled by design
  (`external_cash_bridge_edge_case_report.md`).

> **Not bugs**: the MWRR result cap and Newton-only solver choice were reviewed and are deliberate design
> decisions, not open issues — see [[decisions/mwrr-solver-newton-cap]].

## Source files

| Role | Path |
|------|------|
| Service | `backend/app/services/portfolio_service.py` |
| Period P&L, realized sales (since 2026-10-15/24) | `backend/app/services/financial_math/portfolio/period.py` |
| Performance table rows (since 2026-10-17) | `backend/app/services/financial_math/portfolio/contributions.py` |
| Engine (called by service) | `backend/app/services/financial_math/portfolio/engine.py` |
| API (calls service) | `backend/app/api/v1/portfolio_api.py` |
| Average cost behind the facade and the engine (since 2026-10-07) | `backend/app/services/financial_math/average_cost.py` |
| Facade output schemas | `backend/app/schemas/wac.py` |
| `MISSING_COST_BASIS`, `UnrealizedBreakdownRow` | `backend/app/schemas/portfolio.py` |
| Service tests | `backend/test_scripts/test_services/test_financial/test_portfolio_service.py` |
| Native-cash service tests (policy (a), B12, B14, «FX on cash») | `backend/test_scripts/test_services/test_financial/test_portfolio_service_native_cash.py` |
| Native cash (since 2026-10-11) | `backend/app/services/financial_math/native_cash.py` |
| #32, diagnostics and breakdown tests | `backend/test_scripts/test_services/test_financial/test_portfolio_cost_currency.py` |
| Frontend store | `frontend/src/lib/stores/portfolio/portfolioStore.svelte.ts` |

> Until 2026-10-07 the "WAC compute" row cited `backend/app/utils/financial/wac_utils.py`, deleted by workstream P.

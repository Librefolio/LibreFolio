---
title: "PortfolioService"
category: entity
type: service
updated: 2026-10-07
tags: [backend, portfolio, service, kpi, holdings, contribution, wac, l2-cache, fastapi, average-cost, data-quality]
related:
  - entities/portfolio-engine
  - concepts/portfolio-report-unified
  - concepts/3-pool-cash-model
  - concepts/holdings-performance-panel
  - decisions/mwrr-boundary-fix
  - decisions/portfolio-summary-direct-wiring
  - decisions/financial-math-single-average-cost
  - decisions/wac-target-currency-last-acquisition
  - problems/zero-purchase-cost-foreign-asset-paid-in-report-currency
  - features/F-054
  - features/F-055
  - features/F-097
---

# PortfolioService

## Role

The orchestration layer between the API and the Portfolio Engine. `PortfolioService` coordinates async data loading, runs the engine, and assembles the final DTOs for API responses. It owns the L2 TTL cache, ensuring the engine runs only once per unique (user, scope, date range, currency, flags) combination.

## Location

`backend/app/services/portfolio_service.py` (~2558 lines after commit `39106380` 3-pool refactor, +612; 2 455 lines on 2026-10-07)

## Key Methods

| Method | Output | Notes |
|--------|--------|-------|
| `get_summary()` | `PortfolioSummary` | KPIs + holdings + allocations; since 2026-10-07 also `period_unrealized_breakdown` |
| `get_history()` | `PortfolioHistoryPoint[]` | Daily NAV series + ROI metrics |
| `get_positions_contribution()` | `PositionsContrib` | Per-asset period P&L attribution |
| `get_report()` | `PortfolioReportResponse` | **Unified**: calls engine once, then above methods |
| `get_asset_history()` | `AssetHistoryPoint[]` | WAC vs price series for one asset |
| `get_lots()` | `FIFOLotsResponse` | FIFO lots for one (broker, asset) |
| `compute_wac_iterative()` | `WACPreviewResultItem` | Module-level function, not a method. Standalone WAC for one (broker, asset, date). Since 2026-10-07 a **facade** over `compute_average_costs()` with the same signature, queries, cache and output, for the transaction preview / automatic cost basis, `POST /portfolio/wac` and the PAC planner |

## Average Cost Since 2026-10-07

The service has no average-cost arithmetic of its own any more: the Dashboard figures read the engine's result, and
the facade calls the function directly — both come from the single function of the `financial_math` layer
([[decisions/financial-math-single-average-cost]]).

| Helper | What it does |
|--------|--------------|
| `compute_wac_iterative()` | Facade: loads the (broker, asset) rows, detects split-linked ADJUSTMENTs, picks the target currency (the override, or the last acquisition's currency via `determine_target_currency()` — [[decisions/wac-target-currency-last-acquisition]]), calls `compute_average_costs(asset_leg=False)`, maps the steps to `WACQualifyingTX` (an unknown cost appears as `add_zero_cost`). Fail-safe unchanged: one missing conversion → `wac=None` + `wac_missing_pairs` |
| `_period_realized_sales()` | Realized P&L of the period = Σ (proceeds − historical cost) over the engine's `realized_sales` in `(date_from, date_to]` whose proceeds and cost are both known — no per-sale WAC query |
| `_boundary_cost()` | Period-boundary cost for the positions contribution: `state_at(day).cost_report_for(qty)`, `None` while the pool is incomplete |
| `_engine_missing_fx_pairs()` | Merges the engine's movement-level `missing_fx` (any date) and per-day valuation failures (days of the period) into `missing_fx_pairs` for the banner |
| `_missing_cost_basis_assets()` | Feeds the new `MISSING_COST_BASIS` warning in `build_data_quality_report()` |
| `_unrealized_breakdown_rows()` | `period_unrealized_breakdown`: `UnrealizedBreakdownRow(kind asset\|fx\|unsplit, asset_currency, period_delta)`, deltas between the same boundary states as `period_unrealized_gain_loss_delta`, so the rows add up to it exactly |

Holdings' `wac_per_unit` is the historical WAC already in the report currency (`None` while incomplete); it is also the
Yield on Cost denominator.

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

## Known Issues / Technical Debt — RESOLVED (2026-07-06, commit `78aaa0a3`)

The four items below were the open technical debt tracked in `ARCHITECTURE_CURRENT_STATE.md` §5 bugs 2, 5, 6
and `implementation_status_report.md` §3. All four were closed out by the Holdings/Performance panel refactor
(see [[concepts/holdings-performance-panel]]) and confirmed resolved by exhaustive verification before the
Phase 09 M1/M2 archive (2026-07-07, [[sources/phase09-m1-m2-archive-2026-07]]):

1. ✅ **`get_summary()` now fully wired**: rewritten to read `engine_result.position_states_end` directly
   (computed by the engine exactly at `date_to`) instead of calling `compute_wac_iterative()` per asset. The
   redundant N×M DB+FX calls are eliminated. Resolved differently than originally proposed — no separate
   `DerivedViewsBuilder.build_summary()` method was introduced; wiring is direct inside `get_summary()`, backed
   by a new shared `_compute_period_summary_metrics()` helper. See [[decisions/portfolio-summary-direct-wiring]].
2. ✅ **Valuation gap closed**: holdings now use the engine's `TRANSACTION_IMPLIED` fallback
   (`open_cost_basis` as valuation proxy) when no `PriceHistory` exists — P2P/crowdfund holdings no longer show
   `current_value=None`.
   *(Drift note, 2026-10-07: the mechanism described here is not the current one — the WAC-as-price fallback was
   removed in `39106380` in favour of LAST_BUY_PRICE, see [[problems/test-transaction-implied-constructor-mismatch]],
   and the unified price resolver's `LAST_TRADE_PRICE` replaced that on 2026-07-31, commit `1c5082f81`. Not realigned
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
   field in `PortfolioSummary` / `AllocationHistoryResponse` is no longer always `None`. `DataQualityBanner.svelte`
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
| Engine (called by service) | `backend/app/services/portfolio_engine.py` |
| API (calls service) | `backend/app/api/v1/portfolio_api.py` |
| Average cost behind the facade and the engine (since 2026-10-07) | `backend/app/services/financial_math/average_cost.py` |
| Facade output schemas | `backend/app/schemas/wac.py` |
| `MISSING_COST_BASIS`, `UnrealizedBreakdownRow` | `backend/app/schemas/portfolio.py` |
| Service tests | `backend/test_scripts/test_services/test_financial/test_portfolio_service.py` |
| #32, diagnostics and breakdown tests | `backend/test_scripts/test_services/test_financial/test_portfolio_cost_currency.py` |
| Frontend store | `frontend/src/lib/stores/portfolio/portfolioStore.svelte.ts` |

> Until 2026-10-07 the "WAC compute" row cited `backend/app/utils/financial/wac_utils.py`, deleted by workstream P.

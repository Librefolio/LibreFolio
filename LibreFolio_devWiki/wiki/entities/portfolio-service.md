---
title: "PortfolioService"
category: entity
type: service
tags: [backend, portfolio, service, kpi, holdings, contribution, wac, l2-cache, fastapi]
related:
  - entities/portfolio-engine
  - concepts/portfolio-report-unified
  - concepts/3-pool-cash-model
  - concepts/holdings-performance-panel
  - decisions/mwrr-boundary-fix
  - decisions/portfolio-summary-direct-wiring
  - features/F-054
  - features/F-055
---

# PortfolioService

## Role

The orchestration layer between the API and the Portfolio Engine. `PortfolioService` coordinates async data loading, runs the engine, and assembles the final DTOs for API responses. It owns the L2 TTL cache, ensuring the engine runs only once per unique (user, scope, date range, currency, flags) combination.

## Location

`backend/app/services/portfolio_service.py` (~2558 lines, +612 from commit `39106380` 3-pool refactor)

## Key Methods

| Method | Output | Notes |
|--------|--------|-------|
| `get_summary()` | `PortfolioSummary` | KPIs + holdings + allocations |
| `get_history()` | `PortfolioHistoryPoint[]` | Daily NAV series + ROI metrics |
| `get_positions_contribution()` | `PositionsContrib` | Per-asset period P&L attribution |
| `get_report()` | `PortfolioReportResponse` | **Unified**: calls engine once, then above methods |
| `get_asset_history()` | `AssetHistoryPoint[]` | WAC vs price series for one asset |
| `get_lots()` | `FIFOLotsResponse` | FIFO lots for one (broker, asset) |
| `compute_wac_iterative()` | WAC value | Standalone WAC for one (broker, asset, date) |

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
3. ⚠️ **Realized P&L duplication — improved, not fully eliminated**: `_compute_period_summary_metrics()` now
   deduplicates the NAV/P&L-for-period computation shared by `get_summary()` and `get_positions_contribution()`.
   `get_report()` also passes `_precomputed_engine_result` to `get_positions_contribution()` to avoid a second
   full engine run. Whether every last per-SELL WAC computation is fully single-pass was not exhaustively
   re-verified — treat as substantially improved rather than a guaranteed zero-duplication.
4. ✅ **DataQualityReport now populated**: `build_data_quality_report()` implemented and wired; `data_quality`
   field in `PortfolioSummary` / `AllocationHistoryResponse` is no longer always `None`. `DataQualityBanner.svelte`
   reads the unified `data_quality` field.

### Still open (unrelated to the above, low priority)

- `internal_transfer_flow` / `scope_transfer_flow` diagnostic fields — not implemented.
- Allocation history sampling (weekly/monthly aggregation) — not implemented, daily granularity only.
- WAC fallback for in-transit cost basis — not implemented.
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
| WAC compute | `backend/app/utils/wac_utils.py` |
| Frontend store | `frontend/src/lib/stores/portfolioStore.svelte.ts` |

---
title: "PortfolioService"
category: entity
type: service
tags: [backend, portfolio, service, kpi, holdings, contribution, wac, l2-cache, fastapi]
related:
  - entities/portfolio-engine
  - concepts/portfolio-report-unified
  - concepts/3-pool-cash-model
  - decisions/mwrr-boundary-fix
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

## Known Issues / Technical Debt (Post-Refactor)

1. **`get_summary()` not fully wired**: `get_summary()` still uses `compute_wac_iterative()` per asset even though the engine now computes WAC inline. N redundant DB+FX calls remain until wiring is completed (Priorità 1 backlog).
2. **Valuation gap**: `get_summary()` uses "latest price only" for holdings value; engine uses backward-fill + `LAST_BUY_PRICE` fallback. P2P/crowdfund holdings still show `current_value=None` in the holdings table.
3. **Realized P&L duplication**: Same per-SELL WAC calculation runs separately in `get_summary()` and `get_positions_contribution()` when both are requested via `get_report()`.
4. **DataQualityReport never populated**: `data_quality` field in `PortfolioSummary` and `AllocationHistoryResponse` is always `None` — the per-day quality data exists but aggregation is not implemented.

These are tracked in `ARCHITECTURE_CURRENT_STATE.md` §5 bugs 2, 5, 6 and `implementation_status_report.md` §3.

## Source files

| Role | Path |
|------|------|
| Service | `backend/app/services/portfolio_service.py` |
| Engine (called by service) | `backend/app/services/portfolio_engine.py` |
| API (calls service) | `backend/app/api/v1/portfolio_api.py` |
| WAC compute | `backend/app/utils/wac_utils.py` |
| Frontend store | `frontend/src/lib/stores/portfolioStore.svelte.ts` |

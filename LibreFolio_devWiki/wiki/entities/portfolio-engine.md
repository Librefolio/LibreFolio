---
title: "Portfolio Engine"
category: entity
type: service
tags: [backend, portfolio, engine, pipeline, daily-state, nav, twrr, mwrr, scope-aware, wac, fifo]
related:
  - entities/portfolio-service
  - concepts/3-pool-cash-model
  - concepts/portfolio-report-unified
  - concepts/twrr-mwrr-algorithms
  - concepts/fifo-lot-tracking
  - decisions/mwrr-boundary-fix
  - features/F-054
  - features/F-055
---

# Portfolio Engine

## Role

The core computational layer of the LibreFolio portfolio system. Accepts raw transactions, prices, FX rates, and scope parameters; produces daily portfolio states, performance metrics, and allocation data. It is the only correct place for portfolio math — the service and API layers are orchestration-only.

## Location

`backend/app/services/portfolio_engine.py` (1603 lines)

## 4-Layer Architecture

```
portfolioStore.svelte.ts (FE)   ← L2 TTL cache, 156 lines
        ↓ POST /portfolio/report
portfolio_api.py                ← 6 endpoints, unified /report entry
        ↓
portfolio_service.py            ← PortfolioService (1946 lines), orchestration
        ↓
portfolio_engine.py             ← Pure computation (this file)
        ↓
roi_utils / fifo_utils / wac_utils / valuation_utils
```

## Engine Pipeline (4 stages)

```
1. ScopeAwareTransactionClassifier
   → Classifies txs (buy/sell/deposit/dividend/fee/...)
   → Identifies in-transit intervals (TRANSFER between brokers)
   → Loads external_cash_flows for MWRR computation

2. DailyStateBuilder.build()
   → One DailyPortfolioState per calendar day [date_from, date_to]
   → Per-day: cash ledger, quantity ledger, market value, in-transit, WAC/cost basis
   → NAV = market_value + cash + in_transit
   → Two-pool (then three-pool) cash decomposition
   → Allocation distribution (by type, sector, geography)

3. DerivedViewsBuilder
   → summary (KPIs, holdings, allocations)
   → history (daily time series)
   → allocation_history (3 dimensions)
   → performance_inputs for TWRR/MWRR

4. PortfolioCalculationEngine (async orchestrator)
   → Pre-loads: price_map, wac_series, fx_rate_map, classified_txs
   → Dispatches to DailyStateBuilder
   → Returns EngineResult (all pre-computed data)
```

## Pre-loaded Data Structures

| Structure | Key | Content |
|-----------|-----|---------|
| `price_map` | `asset_id` | `[(date, close, currency)]` — backward-fillable |
| `wac_series` | `(asset_id, broker_id)` | `[(date, wac, currency)]` |
| `fx_rate_map` | `(from_ccy, to_ccy, date)` | FX rate |
| `classified_txs` | — | All transactions with type classification |
| `in_transit_intervals` | — | TRANSFER in-flight windows |
| `external_cash_flows` | — | DEPOSIT/WITHDRAWAL for MWRR |

## Valuation Hierarchy (per asset per day)

1. **MARKET_PRICE**: `price_map` backward-fill (last known close)
2. **TRANSACTION_IMPLIED**: `WAC × cumulative_qty` (when no market price)
3. **MISSING**: excluded from NAV (P2P loans with no price and no WAC)

Note: Bug — `get_summary()` service method uses "latest price only" without TRANSACTION_IMPLIED fallback, causing P2P holdings to show `current_value=None`. Fix in progress.

## Scope Parameters

```
V(u) = broker_ids visible to the user
S    = broker_ids selected by the dashboard filter (S ⊆ V(u))
```

`S` determines which positions enter the aggregated portfolio. `V(u)` also used for `last_buy_price` asset-level valuation fallback.

## Key Gotchas

- WAC is computed 3 ways (engine pre-load, service per-asset, `compute_wac_iterative()`). Redundant. Medium-term: `get_summary()` should read from engine's `wac_series`.
- Realized P&L computed twice (summary + contribution). Medium-term: single-pass refactor.
- Two-pool cash decomposition is a **visualization approximation** for GrowthChart. Exact P&L numbers come from KPI cards (per-sell WAC calculation in service).

## History

| Date | Change |
|------|--------|
| Phase 09 M1 | Initial engine architecture, DailyStateBuilder |
| Phase 09 M2 | MWRR boundary fix; unified /report endpoint; L2 cache |
| Phase 09 M2 | ARCHITECTURE_CURRENT_STATE.md analysis identifies 6 known issues |

## Source files

| Role | Path |
|------|------|
| Engine | `backend/app/services/portfolio_engine.py` |
| ROI utilities | `backend/app/utils/roi_utils.py` |
| FIFO utilities | `backend/app/utils/fifo_utils.py` |
| WAC utilities | `backend/app/utils/wac_utils.py` |
| Valuation utilities | `backend/app/utils/valuation_utils.py` |
| Service layer | `backend/app/services/portfolio_service.py` |
| API layer | `backend/app/api/v1/portfolio_api.py` |

---
title: "Portfolio Engine"
category: entity
type: service
tags: [backend, portfolio, engine, pipeline, daily-state, nav, twrr, mwrr, scope-aware, wac, fifo, inline-wac, 3-pool, pre-frame, blob-cache]
related:
  - entities/portfolio-service
  - concepts/3-pool-cash-model
  - concepts/portfolio-report-unified
  - concepts/twrr-mwrr-algorithms
  - concepts/fifo-lot-tracking
  - concepts/inline-wac-computation
  - concepts/pre-frame-frame-separation
  - decisions/mwrr-boundary-fix
  - features/F-054
  - features/F-055
---

# Portfolio Engine

## Role

The core computational layer of the LibreFolio portfolio system. Accepts raw transactions, prices, FX rates, and scope parameters; produces daily portfolio states, performance metrics, and allocation data. It is the only correct place for portfolio math — the service and API layers are orchestration-only.

## Location

`backend/app/services/portfolio_engine.py`

## 4-Layer Architecture

```
portfolioStore.svelte.ts (FE)   ← L2 TTL cache, 156 lines
        ↓ POST /portfolio/report
portfolio_api.py                ← 6 endpoints, unified /report entry
        ↓
portfolio_service.py            ← PortfolioService (~2558 lines), orchestration
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
   → Pre-frame: processes tx.date < t0 (qty, WAC, cash, K/R/W pools — NO market eval)
   → Frame [t0,t1]: one DailyPortfolioState per calendar day
   → Per-day: cash ledger, quantity ledger, market value, in-transit, WAC/cost basis
   → NAV = market_value + cash + in_transit
   → 3-pool event-driven cash decomposition (K/R/W)
   → Allocation distribution (by type, sector, geography)

3. DerivedViewsBuilder
   → summary (KPIs, holdings, allocations)
   → history (daily time series)
   → allocation_history (3 dimensions)
   → performance_inputs for TWRR/MWRR

4. PortfolioCalculationEngine (async orchestrator)
   → Pre-loads: price_map, fx_rate_map, classified_txs
   → WAC computed inline (NOT pre-loaded from DB separately)
   → Dispatches to DailyStateBuilder
   → Blob cache: fingerprint-keyed, range-aware
   → Returns EngineResult (all pre-computed data)
```

## Pre-loaded Data Structures (Post-Refactor)

| Structure | Key | Content |
|-----------|-----|---------|
| `price_map` | `asset_id` | `[(date, close, currency)]` — backward-fillable |
| `fx_rate_map` | `(from_ccy, to_ccy, date)` | FX rate |
| `classified_txs` | — | All transactions with type classification |
| `in_transit_intervals` | — | TRANSFER in-flight windows |
| `external_cash_flows` | — | DEPOSIT/WITHDRAWAL for MWRR |

**Note**: `wac_series` is no longer pre-loaded from DB. WAC is computed inline in the per-tx loop via `pool_qty`/`pool_cost` accumulators. See [[concepts/inline-wac-computation]].

## Valuation Hierarchy (per asset per day, frame only)

1. **MARKET_PRICE**: `price_map` backward-fill (last known close ≤ t)
2. **LAST_BUY_PRICE**: last BUY unit price across all _visible_ brokers `V(u)` with date ≤ t (NOT restricted to selected brokers `S`)
3. **MISSING**: excluded from NAV; `MISSING_PRICE` data quality flag emitted

The LAST_BUY_PRICE fallback is broker-scope-independent. Example: if VWCE's last BUY was on IBKR but the dashboard filter shows only Directa, the IBKR BUY price still applies as valuation fallback.

## Inline WAC (Single-Pass)

WAC is computed inline in the per-tx unified loop — no separate `compute_wac_iterative()` DB calls:

```python
# BUY
pool_qty_new  = pool_qty + qty
pool_cost_new = pool_cost + buy_cost
wac_new       = pool_cost_new / pool_qty_new

# SELL — read WAC BEFORE reducing pool (key correctness invariant)
wac_at_sell   = pool_cost / pool_qty
sold_cost     = qty_sold × wac_at_sell
pool_qty_new  = pool_qty - qty_sold
pool_cost_new = pool_cost - sold_cost
```

Eliminates N×M DB calls (where N = assets held). See [[concepts/inline-wac-computation]].

## 3-Pool Event-Driven (K/R/W)

Cash is decomposed into three pools updated per-transaction:

```
K(t) = capital_pool          — user's capital in system
R(t) = returns_pool          — generated returns in system
W(t) = withdrawn_returns_pool— returns that left (restorable)
```

SELL fix: WAC read before pool reduction → correct K (cost recovery) + R (gain) split on full exit. See [[concepts/3-pool-cash-model]].

## Pre-Frame / Frame Separation

```
Pre-frame (tx.date < t0):
  Update qty, WAC inline, cash, K/R/W pools
  NO market price fetch, NO FX eval, NO DailyState emission

Frame (t ∈ [t0, t1]):
  Apply txs → update qty, WAC, cash, K/R/W
  Fetch price(asset, t), FX(t)
  Emit DailyPositionState + DailyPortfolioState
```

See [[concepts/pre-frame-frame-separation]].

## Blob Cache (Range-Aware)

The engine cache is keyed by fingerprint AND range:

```python
cache_key = (
    user_id, visible_brokers, selected_brokers, currency,
    date_from, date_to, include_flags,
    tx_fingerprint, price_fingerprint, fx_fingerprint
)
```

Cache hit: stored range `[ta, tb]` **contains** requested range `[t0, t1]`. If not contained: compute missing segments and extend the blob. Fingerprint change → full invalidation.

## Scope Parameters

```
V(u) = broker_ids visible to the user
S    = broker_ids selected by the dashboard filter (S ⊆ V(u))
```

`S` determines which positions enter the aggregated portfolio. `V(u)` is also used for `last_buy_price` fallback.

## Key Gotchas

- **WAC computed inline only**: there is no pre-loaded `wac_series` anymore. Any code expecting `wac_series` from `EngineResult` needs to be updated.
- **SELL order matters for 3-pool**: always read WAC before reducing pool. Reversing this causes full-exit K/R split bug.
- **LAST_BUY_PRICE uses V(u) not S**: this is intentional — asset price is not broker-specific.
- **Pre-frame has no daily states**: you cannot extract chart points for dates before t0 from a single run.
- **`get_summary()` wiring incomplete**: as of commit `39106380`, `get_summary()` still uses some old logic. The new engine fields (inline WAC, 3-pool daily states) are fully available for `get_history()` but only partially for `get_summary()`. Full wiring is Priorità 1 in [[sources/phase09-portfolio-engine-3pool-refactor]].

## History

| Date | Change |
|------|--------|
| Phase 09 M1 | Initial engine architecture, DailyStateBuilder |
| Phase 09 M2 | MWRR boundary fix; unified /report endpoint; L2 cache |
| Phase 09 M2 | ARCHITECTURE_CURRENT_STATE.md analysis identifies 6 known issues |
| 2026-06-30 (39106380) | **Major refactor**: inline WAC (single-pass), 3-pool event-driven, SELL fix, LAST_BUY_PRICE fallback, pre-frame/frame separation, range-aware blob cache. +612 lines portfolio_service.py, 20 new unit tests. |

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
| vNext unit tests (20) | `backend/test_scripts/test_portfolio_engine_vnext.py` |
| Math spec | `LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/Milestone_2/portfolio_engine/portfolio_engine_architecture_v2.md` |
| Architecture state | `LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/Milestone_2/portfolio_engine/ARCHITECTURE_CURRENT_STATE.md` |

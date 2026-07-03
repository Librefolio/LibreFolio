# Portfolio Engine — Architecture & State Report

> Generated: 2026-06-30
> Context: Post Phase B (Positions Widget + Contribution). Dashboard live with full portfolio data.

---

## 1. System Overview

The portfolio calculation system spans 4 layers:

```
┌─────────────────────────────────────────────────────────────────────┐
│ FRONTEND                                                              │
│ portfolioStore.svelte.ts (156 lines)                                  │
│   fetchReport() → POST /portfolio/report                             │
│   Cache: key = broker_ids|dateFrom|dateTo|currency|contrib_flag      │
│   Types: PortfolioSummary, PortfolioHistoryPoint, PositionsContrib   │
└─────────────────────────────────────────────────────────────────────┘
         │
         │ POST /api/v1/portfolio/report
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ API LAYER                                                             │
│ portfolio_api.py — 6 endpoints:                                       │
│   POST /wac            — WAC time series per (broker, asset)         │
│   POST /summary        — KPIs + holdings + allocations               │
│   POST /history        — Daily NAV series                            │
│   POST /allocation-history — Time series by dimension                │
│   POST /report         — UNIFIED: summary+history+alloc+contribution │
│   GET  /asset-history  — WAC vs market price per asset               │
│   GET  /lots           — FIFO open/closed lots                       │
└─────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ SERVICE LAYER — portfolio_service.py (1946 lines)                     │
│                                                                       │
│ PortfolioService class:                                               │
│   get_summary()                — Engine + per-asset holdings loop     │
│   get_history()                — NAV daily series + ROI metrics       │
│   get_positions_contribution() — Per-asset period P&L attribution    │
│   get_report()                 — Unified orchestrator (single engine) │
│   get_asset_history()          — WAC vs price series for one asset   │
│   get_lots()                   — FIFO lots for one (broker, asset)   │
│                                                                       │
│ Standalone:                                                           │
│   compute_wac_iterative()      — WAC for one (broker, asset, date)   │
└─────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ ENGINE LAYER — portfolio_engine.py (1603 lines)                       │
│                                                                       │
│ Pipeline:                                                             │
│   1. ScopeAwareTransactionClassifier → classify txs + in-transit     │
│   2. DailyStateBuilder.build()       → DailyPortfolioState[]         │
│   3. DerivedViewsBuilder             → summary/history/allocation    │
│   4. PortfolioCalculationEngine      → async orchestrator (loads DB) │
│                                                                       │
│ Core data structures pre-loaded:                                      │
│   price_map[asset_id] = [(date, close, currency)]                    │
│   wac_series[(asset_id, broker_id)] = [(date, wac, currency)]        │
│   fx_rate_map[(from_ccy, to_ccy, date)] = rate                       │
│   classified_txs, in_transit_intervals, external_cash_flows          │
└─────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ UTILITY LAYER                                                         │
│ roi_utils.py      — TWRR, MWRR, Simple ROI calculations             │
│ fifo_utils.py     — FIFO lot matching for realized P&L              │
│ wac_utils.py      — Pure WAC computation from tx list                │
│ valuation_utils.py — compute_holding_value (quote_base support)      │
└─────────────────────────────────────────────────────────────────────┘
```

## 2. API Endpoints

| Endpoint | Method | Request Body | Response | Caching |
|----------|--------|-------------|----------|---------|
| `/portfolio/wac` | POST | `{queries: [{broker_id, asset_id, date_range}]}` | WAC series per query | None |
| `/portfolio/summary` | POST | `{broker_ids?, include_breakdown, target_currency?}` | PortfolioSummary | Via /report |
| `/portfolio/history` | POST | `{broker_ids?, date_range?, target_currency?}` | PortfolioHistoryPoint[] | Via /report |
| `/portfolio/allocation-history` | POST | `{broker_ids?, date_range?, dimension}` | AllocationHistoryResponse | Via /report |
| `/portfolio/report` | POST | `{broker_ids?, date_range?, target_currency?, include_*}` | PortfolioReportResponse | L2 TTL cache |
| `/portfolio/asset-history` | GET | `?asset_id&broker_id?` | AssetHistoryPoint[] | None |
| `/portfolio/lots` | GET | `?broker_id&asset_id` | FIFOLotsResponse | None |

### Report endpoint — unified entry point

The `/report` endpoint is the primary path for the dashboard. It runs the engine ONCE and returns:
- `summary` (KPIs, holdings, allocations)
- `history` (daily time series)
- `allocation_history` (3 dimensions)
- `data_quality` (issues, warnings)
- `positions_contribution` (per-asset period P&L — optional)

Frontend calls this single endpoint via `portfolioStore.fetchReport()`.

### L2 Cache

`get_report()` implements a Layer 2 TTL cache keyed by:
```python
(user_id, broker_ids, currency, date_from, date_to,
 include_summary, include_history, include_allocation_history,
 include_breakdown, include_positions_contribution,
 tx_fingerprint, price_fingerprint)
```

Cache invalidated on: fingerprint change (tx add/edit/delete, price update).

## 3. Data Flow: DailyStateBuilder

The heart of the engine. Builds one `DailyPortfolioState` per calendar day from `date_from` to `date_to`.

### Per-day computation:

```
1. Cash ledger: cumulative cash (all tx amounts converted to target_ccy)
2. Quantity ledger: cumulative_qty[(asset_id, broker_id)] per day
3. Market value: Σ(price(asset, date) × qty) for all positions with qty > 0
4. In-transit: cash/assets between brokers during transit window
5. WAC/cost basis: Σ(wac_at_date × qty) for all positions
6. NAV = market_value + cash + in_transit
7. Two-pool cash decomposition (capital vs returns provenance)
8. Allocation distribution (by type, sector, geography)
```

### Valuation hierarchy (per asset per day):
1. **MARKET_PRICE**: PriceHistory backward-fill
2. **TRANSACTION_IMPLIED**: WAC × qty (when no market price but WAC exists)
3. **MISSING**: excluded from NAV

## 4. Mathematical Duplication Analysis

### WAC Computation — 3 paths doing the same math

| Path | Caller | When | Input |
|------|--------|------|-------|
| `compute_wac_iterative()` | get_summary() per-asset loop | Per (broker, asset) at as_of_date | DB query + FX |
| `wac_series` pre-load | Engine.calculate() step 8 | All (broker, asset) × scope | Same DB query + FX |
| `compute_wac_from_txlist()` | Both above (delegated) | Pure math on tx list | Pre-converted amounts |

**Duplication**: When `get_report()` calls `get_summary(_precomputed_engine_result=...)`, the engine has ALREADY pre-loaded `wac_series` for all positions. But `get_summary()` re-calls `compute_wac_iterative()` per asset anyway (lines 781-787, 736-738). This is **N redundant DB+FX calls** where N = number of held assets.

**Impact**: For a portfolio with 20 assets × 2 brokers = 40 WAC calls duplicated.

### Market Value — 2 paths

| Path | Output | Used for |
|------|--------|----------|
| Engine `DailyStateBuilder._market_value_for()` | mv per (asset, broker, date) → summed to portfolio | NAV chart, allocation |
| Service `get_summary()` per-asset loop | `current_price × qty` (today only) | Holdings DTO |

**Difference**: Engine uses **backward-fill** price with TRANSACTION_IMPLIED fallback. Service uses **latest price only** (no fallback). This causes:
- Engine: P2P loans show at WAC-implied value ✓
- Holdings: P2P loans show current_value=None ✗

**This is Bug 2** — the service should use the same valuation logic as the engine.

### Realized P&L — 2 paths

| Path | Scope | Formula |
|------|-------|---------|
| `get_summary()` lines 698-780 | Per (broker, asset) SELLs in period | sell_proceeds - WAC_at_sell × qty_sold |
| `get_positions_contribution()` lines 1350-1420 | Same | Identical formula, separate accumulator |

**Duplication**: When `get_report()` calls both `get_summary()` and `get_positions_contribution()`, the SELL-by-SELL WAC computation runs **twice** for every sell in the period.

### Income/Fees — 2 paths

| Path | Scope |
|------|-------|
| `get_summary()` lines 683-690 | Portfolio-level accumulators |
| `get_positions_contribution()` lines 1305-1340 | Per-position + unallocated accumulators |

**Duplication**: Same transaction loop, same FX conversion, run twice.

### Performance Metrics (TWRR/MWRR/ROI) — no duplication

Computed once from `DerivedViewsBuilder.build_performance_inputs()` → `roi_utils`.

## 5. Recommendations

### Short-term fixes (current sprint)

1. **Fix Bug 2**: Add TRANSACTION_IMPLIED fallback in holdings loop (use WAC×qty when no price)
2. **Fix Bug 1**: Investigate chart discrepancy (compare engine cost_basis_delta vs WAC-based realized)
3. **Deduplicate income/fees/realized**: Refactor so `get_summary()` produces per-position accumulators that `get_positions_contribution()` reuses instead of recomputing

### Medium-term refactor

4. **Eliminate redundant WAC calls**: `get_summary()` should read from the engine's pre-loaded `wac_series` instead of re-calling `compute_wac_iterative()` per asset. This requires passing `wac_series` from `engine_result` to `get_summary()` (already partially connected via `_precomputed_engine_result`).

5. **Unify valuation paths**: Extract a shared `_value_position_at_date(asset_id, broker_id, date, price_map, wac_series, fx_map)` function used by both engine daily loop and holdings DTO builder.

### Long-term

6. **Single-pass architecture**: Refactor `get_report()` to do ONE pass through transactions that produces: summary + holdings + contribution + daily_states. Currently 3 separate iteration passes over the same tx set.

## 7. Mathematical Divergence: Engine vs Service WAC

### The core discrepancy

When a SELL happens on date D for asset A at broker B:

**Engine path** (`DailyStateBuilder`):
```
open_cost_basis(D) = wac_series[(A,B)].at_date(D) × cumulative_qty(D)
delta_assets = open_cost_basis(D) - open_cost_basis(D-1)
```
The `wac_series` was pre-loaded from `compute_wac_iterative(as_of_date=actual_to)` which includes ALL transactions up to period end — including the SELL itself. After a SELL reduces pool, the WAC may change (if it was the last lot at a specific cost).

**Service path** (`get_summary()` per-asset realized loop):
```
sell_wac = compute_wac_iterative(excluded_tx_ids=[sell_tx.id]).wac
cost_sold = sell_wac × sell_qty
realized = sell_proceeds - cost_sold
```
The WAC is computed EXCLUDING the current sell — giving the WAC BEFORE the sell. This is the mathematically correct "cost of what was sold."

### Impact

These two WAC values can differ when:
- SELL is a `reduce` effect (pool shrinks but WAC stays same) → no difference
- SELL triggers pool reset or the last entry in pool changes WAC → difference

In practice for standard reduce SELLs, WAC before and after SELL is identical (WAC only changes on BUY/add). So the divergence is small — typically only rounding.

The user's observed 50.70€ vs ~34€ discrepancy suggests something else: the engine's `open_cost_basis` on 14/06 may differ from the service's WAC×qty because the engine uses `_wac_on_date()` (forward-fill from last WAC change) while the service re-computes fresh from DB each time.

### Resolution

For the dashboard chart, the two-pool decomposition is a **visualization approximation** — it splits cash provenance for the stacked area chart. The exact P&L numbers come from the KPI cards (which use the service's per-sell WAC calculation). Document this distinction in UI tooltips.

| # | Issue | Severity | Root Cause |
|---|-------|----------|-----------|
| 1 | Chart capital/returns split incorrect on SELL+TAX+FEE day | High | Two-pool formula vs WAC discrepancy |
| 2 | P2P/crowdfund holdings value=None | High | No TRANSACTION_IMPLIED fallback in service |
| 3 | Tx double-click → page instead of modal | Medium | Dashboard wires goto() not modal |
| 4 | Recrowd broker icon missing | Low | Broker record missing icon metadata |
| 5 | WAC computed 2× per asset (engine pre-load + service per-call) | Low (perf) | Historical architecture |
| 6 | Realized/income/fees computed 2× (summary + contribution) | Low (perf) | Separate methods |

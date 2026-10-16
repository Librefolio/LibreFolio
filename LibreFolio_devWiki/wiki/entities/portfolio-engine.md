---
title: "Portfolio Engine"
category: entity
type: service
updated: 2026-10-12
tags: [backend, portfolio, engine, pipeline, daily-state, nav, twrr, mwrr, scope-aware, wac, fifo, inline-wac, 3-pool, pre-frame, blob-cache, average-cost, financial-math, native-cash, internal-transfers]
related:
  - entities/portfolio-service
  - entities/fifo-lot-engine
  - entities/native-cash
  - concepts/3-pool-cash-model
  - concepts/portfolio-report-unified
  - concepts/twrr-mwrr-algorithms
  - concepts/fifo-lot-tracking
  - concepts/inline-wac-computation
  - concepts/pre-frame-frame-separation
  - concepts/holdings-performance-panel
  - decisions/mwrr-boundary-fix
  - decisions/mwrr-solver-newton-cap
  - decisions/portfolio-summary-direct-wiring
  - decisions/fifo-v4-validation-and-scope
  - decisions/financial-math-single-average-cost
  - decisions/financial-math-one-home
  - decisions/native-cash-daily-revaluation
  - decisions/portfolio-pnl-series-contracts
  - problems/test-transaction-implied-constructor-mismatch
  - problems/zero-purchase-cost-foreign-asset-paid-in-report-currency
  - problems/foreign-cash-never-revalued
  - problems/dirty-days-ignore-fx-only-moves
  - features/F-054
  - features/F-055
---

# Portfolio Engine

## Role

The core computational layer of the LibreFolio portfolio system. Accepts raw transactions, prices, FX rates, and scope parameters; produces daily portfolio states, performance metrics, and allocation data. It is the only correct place for portfolio math — the service and API layers are orchestration-only.

## Location

`backend/app/services/financial_math/portfolio/` (since 2026-10-12), one module per step — line counts at `5d0585595`:

| Module | Lines | Holds |
|--------|------:|-------|
| `__init__.py` | 19 | the architecture docstring only (no re-exports) |
| `models.py` | 362 | daily states, `BrokerDailyContribution`, `RealizedSale`, `UnrealizedSplit`, `ValuationSource`/`ValuationResult`, `SplitRecord`, `EngineEndState`, `PortfolioCalculationResult` |
| `classifier.py` | 235 | `ScopeAwareTransactionClassifier`, linked and external types |
| `daily_state.py` | 1 252 | `DailyStateBuilder`: the pre-frame and frame replay |
| `derived_views.py` | 272 | `build_cost_positions`, `DerivedViewsBuilder` |
| `data_quality.py` | 284 | `build_data_quality_report`, `load_configured_fx_pair_sets`, `normalize_fx_pair_slug` |
| `engine.py` | 555 | `PortfolioCalculationEngine`: loading, FX preload, average costs, native cash, blob cache |

Until 2026-10-12 it was one file, `backend/app/services/portfolio_engine.py` (2 714 lines on 2026-10-07, 2 872 before
the move). Workstream T moved it with a rename commit (`1cc9cd8f5`, so `git log --follow` on `engine.py` still reaches
the engine's first commit) and cut it in a second one (`a57a43fbd`) — [[decisions/financial-math-one-home]].

## 4-Layer Architecture

```
portfolioStore.svelte.ts (FE)   ← L2 TTL cache, 156 lines
        ↓ POST /portfolio/report
portfolio_api.py                ← 6 endpoints, unified /report entry
        ↓
portfolio_service.py            ← PortfolioService (2 455 lines on 2026-10-07), orchestration
        ↓
financial_math/portfolio/       ← Pure computation (this package)
        ↓
financial_math: average_cost (cost) · native_cash (cash, since 2026-10-11) · price_marks · returns / valuation
```

> Until 2026-10-07 the last line read `roi_utils / fifo_utils / wac_utils / valuation_utils`. `fifo_utils.py` was
> deleted on 2026-09-03 (FIFO lives in [[entities/fifo-lot-engine]]); `wac_utils.py` on 2026-10-07, when the engine's
> cost moved to `backend/app/services/financial_math/average_cost.py` — see
> [[decisions/financial-math-single-average-cost]]. Until 2026-10-12 it read `financial_math.average_cost · price_resolver
> · roi_utils / valuation_utils`: T-1 moved the last three into the layer as `price_marks`, `returns` and `valuation`.

## Engine Pipeline (4 stages)

```
1. ScopeAwareTransactionClassifier
   → Classifies txs (buy/sell/deposit/dividend/fee/...)
   → Identifies in-transit intervals (TRANSFER between brokers)
   → Loads external_cash_flows for MWRR computation

2. DailyStateBuilder.build()
   → Pre-frame: processes tx.date < t0 (qty, WAC, cash, K/R/W pools — NO market eval);
     since 2026-10-11 also the rate-change days of held foreign cash (cash revaluation)
   → Frame [t0,t1]: one DailyPortfolioState per calendar day
   → Per-day: cash ledger, quantity ledger, market value, in-transit, WAC/cost basis
   → NAV = market_value + cash + in_transit
   → 3-pool event-driven cash decomposition (K/R/W), exchange results on foreign cash included
   → Internal transfers: zero-sum capital flows between broker lines (since 2026-10-11)
   → Allocation distribution (by type, sector, geography)

3. DerivedViewsBuilder
   → summary (KPIs, holdings, allocations)
   → history (daily time series)
   → allocation_history (3 dimensions)
   → performance_inputs for TWRR/MWRR

4. PortfolioCalculationEngine (async orchestrator)
   → Pre-loads: price_map, fx_rate_map, classified_txs
   → Average costs: ONE compute_average_costs() call for all positions
     (build_cost_positions), after the FX preload — since 2026-10-07
     (2026-06-30 → 2026-10-07: "WAC computed inline", pools accumulated in the replay)
   → Native cash: ONE compute_native_cash() call (step 10c), from the classified
     movements up to actual_to, rates_until = actual_to — since 2026-10-11
   → Dispatches to DailyStateBuilder(average_costs=..., native_cash=...)  ← both required
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
| `average_costs` (since 2026-10-07) | `(asset_id, broker_id)` | `AverageCost` timeline from `compute_average_costs()`: historical cost in the target currency (and in the asset currency), one step per movement, missing conversions |
| `native_cash` (since 2026-10-11) | broker, currency | `NativeCash` from `compute_native_cash()`: native balances, their value on any day, rate-change days, period flows, missing conversions — [[entities/native-cash]] |

**Note**: `wac_series` is no longer pre-loaded from DB. WAC is computed inline in the per-tx loop via `pool_qty`/`pool_cost` accumulators. See [[concepts/inline-wac-computation]].

**Update 2026-10-07**: the pools are no longer accumulated in the loop either — the loop replays the `average_costs`
steps. `fx_rate_map` no longer carries acquisition-date rates for costs: `compute_average_costs()` makes its own
conversions, at each movement's date, in one batched `convert_bulk`. A frozen in-transit cost is now asked for at the
arrival date only.

## Valuation Hierarchy (per asset per day, frame only)

1. **MARKET_PRICE**: `price_map` backward-fill (last known close ≤ t)
2. **LAST_BUY_PRICE**: last BUY unit price across all _visible_ brokers `V(u)` with date ≤ t (NOT restricted to selected brokers `S`)
3. **MISSING**: excluded from NAV; `MISSING_PRICE` data quality flag emitted

The LAST_BUY_PRICE fallback is broker-scope-independent. Example: if VWCE's last BUY was on IBKR but the dashboard filter shows only Directa, the IBKR BUY price still applies as valuation fallback.

> **Drift note (2026-10-07):** the code's `ValuationSource` enum today is `MARKET_PRICE | LAST_TRADE_PRICE | MISSING`,
> resolved by the unified price resolver (`AssetPriceSeries` per held asset, `mark_series` in `DailyStateBuilder`,
> `backend/app/services/financial_math/price_marks.py` since 2026-10-12, before that `services/price_resolver.py`);
> `last_buy_prices` no longer exists. Commit `1c5082f81` (2026-07-31,
> "remove legacy valuation engine — resolver is the single brain") made that change. This section still describes the
> earlier LAST_BUY_PRICE design and was not realigned here: valuation was not part of workstream P.
> **J-17 (2026-10-16):** the enum gained `ESTIMATED_AT_COST` (no quote, BUY or SELL on or before the day: book
> cost, a declared estimate), and an ADJUSTMENT is no longer a price observation. See
> [[decisions/adjustment-is-never-a-price]].

## Inline WAC (Single-Pass) — 2026-06-30 model, superseded 2026-10-07

WAC was computed inline in the per-tx unified loop — no separate `compute_wac_iterative()` DB calls:

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

In this model the pool was kept in the **asset currency**: `_buy_unit_cost()` converted each purchase into it with
rates from `fx_rate_map` (a cross rate when the asset currency differs from the target), and the open cost was
re-converted into the target currency every day. A missing rate returned `None` and the purchase entered at the current
average cost — 0 for an empty pool: issue #32, [[problems/zero-purchase-cost-foreign-asset-paid-in-report-currency]].

## Average Cost (since 2026-10-07)

The engine no longer owns a cost algorithm. It calls the single average-cost function of the `financial_math` layer
([[decisions/financial-math-single-average-cost]]) and replays its result:

- **`build_cost_positions()`** turns the classified transactions into one `CostPosition` per `(asset_id, broker_id)`
  (quantity and cost scaled by the owner's share, classification order, nothing after `date_to`).
- **`calculate()`** makes **one** `compute_average_costs(..., report_currency=target)` call for the whole scope, after
  `_preload_fx_rates()`, and passes it to `DailyStateBuilder(average_costs=...)` — a **required** parameter, so no
  default can produce silent zeros.
- **`DailyStateBuilder`** follows each position's steps with `_next_cost_step()`; a step that does not belong to the
  transaction being replayed raises `RuntimeError` (a bug, never data). No cost is converted in the daily loop.
- **Outputs:**
  - `DailyPositionState.wac` is the historical unit cost **in the target currency** (`None` while the cost is
    incomplete), plus `wac_asset`, `cost_complete` and `asset_currency`;
  - `DailyPortfolioState.open_cost_basis` = Σ historical cost of the held quantity (its known part);
  - `DailyPortfolioState.unrealized_by_currency` = `UnrealizedSplit(asset, fx, unsplit)` per asset currency, the source
    of the Dashboard's unrealized breakdown;
  - `PortfolioCalculationResult.realized_sales` (`RealizedSale`: proceeds at the sale date, historical cost removed),
    `average_costs` and `missing_fx` (`{"FROM/TO": dates}` for every movement-level conversion that failed: costs,
    cash, external flows, in-transit cost);
  - `EngineEndState.wac_pool_qty` / `wac_pool_cost` hold each pool's quantity and its historical cost in the target
    currency.
- **Capital baseline:** a priced in-kind ADJUSTMENT moves it by the cost its step added (in) or removed (out).
  **J-24 (2026-10-16):** an outgoing one now leaves at the value it hands over, quantity × cost basis at the rate of
  its date, and the difference from the cost removed is a realized disposal (`RealizedSale`), as in the lots.
- **In transit:** a frozen cost (`cost_basis_override × quantity`) is converted once, at the arrival date.
- **Removed:** `_buy_unit_cost`, `_compute_open_cost_basis_inline`, `_capital_flow_for_adjustment_in`,
  `_apply_split_rescale`.
- **Added:** `load_configured_fx_pair_sets(db)`, the configured / real-provider FX pair loader shared with the service
  and the lots analysis to classify missing pairs.

## 3-Pool Event-Driven (K/R/W)

Cash is decomposed into three pools updated per-transaction:

```
K(t) = capital_pool          — user's capital in system
R(t) = returns_pool          — generated returns in system
W(t) = withdrawn_returns_pool— returns that left (restorable)
```

SELL fix: WAC read before pool reduction → correct K (cost recovery) + R (gain) split on full exit. See [[concepts/3-pool-cash-model]].

Since 2026-10-07 the cost a SELL returns to K is the historical cost in the target currency that its average-cost step
removed (no exchange rate at the sale date); an oversell removes the whole pool cost.

Since 2026-10-11 an **exchange result on foreign cash** is a pool event too: it goes to the broker's R, and a loss
larger than R comes out of K (option k2) — see the next section and [[concepts/3-pool-cash-model]].

## Native Cash and Exchange Results (since 2026-10-11)

Lot 41, part F ([[decisions/native-cash-daily-revaluation]]): the engine's cash is the broker's native balances,
revalued on every day the rate of a held foreign currency changes.

- **Step 10c of `calculate()`** builds `compute_native_cash(...)` from the classified movements up to `actual_to`, at
  the classifier's share (`effective_share()`), with `rates_until = actual_to` ([[entities/native-cash]]). It comes
  after the average costs (10a) and before the replay (11), and is returned on the result (`native_cash`, `None` on
  the early returns).
- **`DailyStateBuilder(native_cash=...)`** is required (decision D-β), like `average_costs`.
- **`_revalue_foreign_cash()`** books, per broker with foreign cash, `value_at(day)[b] − cash[b]` to the cash and to R
  (k2); the capital baseline never moves. It runs on the rate-change days in the pre-frame and, in the frame, those
  days are dirty days — which also closed the cash half of B11 ([[problems/dirty-days-ignore-fx-only-moves]]).
- **Removed**: the accumulators `per_realized`, `per_income`, `per_fees_taxes`, `unalloc_income`, `unalloc_fees` of
  `PortfolioCalculationResult` (backlog B13), which no production code read; `realized_sales` stays, and the flows now
  come from the native cash.
- **Proof**: for a portfolio whose cash is all in the report currency, every output is byte-identical
  (`test_native_cash_guard.py` and its golden, generated before the code).

## Internal Transfers in the Broker Lines (since 2026-10-11)

Lot 41's first delivery ([[decisions/portfolio-pnl-series-contracts]], G1a): `_internal_transfer_flows()` moves X —
what enters the receiver's NAV on the arrival day, securities at market value — from the sender's capital to the
receiver's, so a broker line no longer jumps by −X / +X; `_transfer_leg_capital()` makes a securities leg whose partner
is outside the filtered view (or deleted) capital at market value. The portfolio's capital never moves, so every
combined-view aggregate stays byte-identical (`test_broker_internal_flows.py` reruns the replay with the flows
neutralised).

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

Since 2026-10-07 "update WAC" means "advance to the next precomputed average-cost step" in both stages; the cost itself
needs no FX in either stage.

Since 2026-10-11 the pre-frame also replays every rate-change day of a held foreign currency, to revalue the cash
(still no market price, no daily state); in the frame those days are dirty days.

See [[concepts/pre-frame-frame-separation]].

## Blob Cache (Range-Aware)

The engine's blob cache (24-hour TTL) is keyed by fingerprints, **not** by the range:

```python
blob_key = (
    user_id, scope_broker_ids, access_fingerprint, target_currency,
    tx_fingerprint, price_fingerprint, fx_fingerprint, split_fingerprint,
    include_candles, include_acquisition_funding,
)
```

The blob stores its own range. A hit needs the stored range to start on or before the requested start and to end
**exactly** on the requested end: the blob's states are not trimmed, so a wider blob would leak days past `date_to`
into every consumer. A blob that ends earlier is recomputed (resuming from its end state is deferred). Any fingerprint
change gives a different key. The access fingerprint — the sorted `(broker_id, role, share)` of the scope — makes a
changed share or role miss the cache, here and in the 30-minute report cache of `portfolio_service.py`:
[[problems/portfolio-cache-ignored-role-and-share]]. *Update (2026-10-13, C-64)*: this section used to show the dates
in the key and an extension of the blob on a partial hit.

## Scope Parameters

```
V(u) = broker_ids visible to the user
S    = broker_ids selected by the dashboard filter (S ⊆ V(u))
```

`S` determines which positions enter the aggregated portfolio. `V(u)` is also used for `last_buy_price` fallback.

## Key Gotchas

- **WAC computed inline only**: there is no pre-loaded `wac_series` anymore. Any code expecting `wac_series` from `EngineResult` needs to be updated. **Known trap** *(resolved 2026-07-13: the file was deleted)*: the test helper in `test_transaction_implied.py` was never updated and still passed a `wac_series` kwarg to `DailyStateBuilder()` — see [[problems/test-transaction-implied-constructor-mismatch]].
- **`average_costs` is a required `DailyStateBuilder` parameter** (since 2026-10-07): every construction must pass the `compute_average_costs()` result for the same transactions in the same order, or `_next_cost_step()` raises `RuntimeError`. Pure builder tests build it with `backend/test_scripts/test_services/_engine_average_costs.py`, which answers the conversion requests from the test's own `fx_rate_map`. One of the 13 test constructions lives outside the engine test selectors, in `backend/test_scripts/test_external/test_brim_providers.py` — a constructor change must be checked there too.
- **`native_cash` is required too** (since 2026-10-11): pure builder tests build it with `backend/test_scripts/test_services/_engine_native_cash.py`, on the model of the average-cost helper (the movements of `calculate()`, conversions answered from the test's `fx_rate_map`). F-2 added it to 19 constructions in 15 test files, `test_brim_providers.py` included.
- **Patch a module global on the module that reads it** (since 2026-10-12): after the cut, `convert_bulk` and `PortfolioCalculationEngine` are read in `financial_math/portfolio/engine.py`, `DailyStateBuilder` lives in `daily_state.py`; the package re-exports nothing, so a patch on the package would be mute ([[decisions/financial-math-one-home]]).
- **The cost is historical, the valuation is not**: since 2026-10-07 the open cost basis keeps each purchase's own-date rate while the market value uses the day's rate, so a foreign position's unrealized P&L includes the exchange-rate effect — split per currency in `unrealized_by_currency`.
- **SELL order matters for 3-pool**: always read WAC before reducing pool. Reversing this causes full-exit K/R split bug.
- **LAST_BUY_PRICE uses V(u) not S**: this is intentional — asset price is not broker-specific. *(LAST_BUY_PRICE design — see the drift note under Valuation Hierarchy.)*
- **Pre-frame has no daily states**: you cannot extract chart points for dates before t0 from a single run.
- **`position_states_end` is the date-aware holdings snapshot**: computed by the engine exactly at `date_to`. `PortfolioService.get_summary()` reads this directly (see [[concepts/holdings-performance-panel]]) — the older "get_summary() wiring incomplete" gap is resolved as of commit `13052a006` (2026-07-06).
- **No reconciliation with [[entities/fifo-lot-engine]]'s per-lot fee/tax/income figures**: as of the FIFO v4 FEE/TAX work (2026-07-22), asset-linked costs/income are allocated per-lot inside the FIFO engine, while this engine still computes its own independent fee/tax/income accumulators for portfolio-level (assetless, `asset_id = null`) amounts. Cross-engine runtime reconciliation and new pre-share absolute accumulators were **deliberately deferred**, not implemented — this file has two existing accumulator paths and share-application logic scattered across multiple call sites, judged too risky to touch in the same release. No displayed value changes as a result, but the two engines' totals are not currently cross-checked against each other. See [[decisions/fifo-v4-validation-and-scope]]. *Update 2026-10-11: the engine's own income/fee accumulators are gone (B13, lot 41 F) and the share rule has one copy (`effective_share()`); period income and costs now come from the native cash's flows. The cross-check with the FIFO engine's per-lot figures is still not done.*

## History

| Date | Change |
|------|--------|
| Phase 09 M1 | Initial engine architecture, DailyStateBuilder |
| Phase 09 M2 | MWRR boundary fix; unified /report endpoint; L2 cache |
| Phase 09 M2 | ARCHITECTURE_CURRENT_STATE.md analysis identifies 6 known issues |
| 2026-06-30 (39106380) | **Major refactor**: inline WAC (single-pass), 3-pool event-driven, SELL fix, LAST_BUY_PRICE fallback, pre-frame/frame separation, range-aware blob cache. +612 lines portfolio_service.py, 20 new unit tests. |
| 2026-07-06 (78aaa0a3) | **Holdings/Performance panel refactor**: `get_summary()` rewired to `position_states_end` (date-aware, closes the "wiring incomplete" gap); `get_positions_contribution()` date-boundary fixes; `_compute_period_summary_metrics()` shared helper; `data_quality` now populated; TRANSACTION_IMPLIED fallback closes P2P/crowdfund valuation gap. See [[concepts/holdings-performance-panel]]. |
| 2026-07-07 | Phase 09 Milestone 1 & 2 archived to `phases/phase-09-subplan/`; exhaustive verification confirms ~20 previously-open items resolved, ~7 resolved differently (see [[decisions/portfolio-summary-direct-wiring]], [[decisions/mwrr-solver-newton-cap]]), ~7 genuinely still open (low priority). See [[sources/phase09-m1-m2-archive-2026-07]]. |
| 2026-07-15 | Phase 09 Milestone 3 (Broker UI v2 redesign) archived to `phases/phase-09-subplan/Milestone_3/`; reuses this engine's unified `/portfolio/report` output (`BrokerBreakdown.cash_balances` added natively, see [[decisions/broker-card-aggregation-no-n-plus-one]]) for per-broker cards — no engine-internals changes. See [[sources/phase09-m3-broker-redesign-2026-07]]. |
| 2026-07-22 | FIFO v4 FEE/TAX integration landed in [[entities/fifo-lot-engine]] (per-lot economic allocation). This file was **not** part of that change — cross-engine reconciliation with FIFO's new per-lot fee/tax/income figures was explicitly scoped out/deferred. See [[decisions/fifo-v4-validation-and-scope]], [[sources/fifo-v4-fee-tax-integration]]. |
| 2026-10-07 | **Workstream P (issue #32)**: the engine's own cost pools (asset currency, re-converted daily, silent zero on a missing rate) replaced by one `compute_average_costs()` call per run and a replay of its steps; `DailyStateBuilder(average_costs=...)` required; `wac` in the target currency + `wac_asset` / `cost_complete`; `realized_sales`, `missing_fx`, `unrealized_by_currency`; in-transit cost at the arrival date; `MISSING_COST_BASIS` issue. See [[decisions/financial-math-single-average-cost]], [[problems/zero-purchase-cost-foreign-asset-paid-in-report-currency]]. |
| 2026-10-11 (`883681766`) | **Lot 41, broker lines**: internal transfers become zero-sum capital flows between broker lines on the arrival day (`_internal_transfer_flows()`); filtered views and orphans (`_transfer_leg_capital()`, D2/D5); FX preload for TRANSFER legs dated before `date_from`. Combined-view aggregates byte-identical. See [[decisions/portfolio-pnl-series-contracts]]. |
| 2026-10-11 (`aa6b6077a`) | **Lot 41, F**: `native_cash` step 10c and required builder argument; foreign cash revalued on rate-change days (k2); B13 accumulators removed; `effective_share()`. See [[decisions/native-cash-daily-revaluation]], [[problems/foreign-cash-never-revalued]]. |
| 2026-10-12 (`1cc9cd8f5`, `a57a43fbd`) | **T-1**: moved to `financial_math/portfolio/engine.py` by a rename commit, then cut into six modules; `build_data_quality_report` a function, one public `normalize_fx_pair_slug`. See [[decisions/financial-math-one-home]]. |

## Source files

| Role | Path |
|------|------|
| Engine | `backend/app/services/financial_math/portfolio/engine.py` |
| Daily replay (`DailyStateBuilder`) | `backend/app/services/financial_math/portfolio/daily_state.py` |
| States and results | `backend/app/services/financial_math/portfolio/models.py` |
| Classifier | `backend/app/services/financial_math/portfolio/classifier.py` |
| Derived views, cost positions | `backend/app/services/financial_math/portfolio/derived_views.py` |
| Data quality, configured FX pairs | `backend/app/services/financial_math/portfolio/data_quality.py` |
| Native cash (since 2026-10-11) | `backend/app/services/financial_math/native_cash.py` |
| Average cost (since 2026-10-07) | `backend/app/services/financial_math/average_cost.py` |
| Unified price resolver (valuation) | `backend/app/services/financial_math/price_marks.py` |
| ROI utilities | `backend/app/services/financial_math/returns.py` |
| Valuation utilities | `backend/app/services/financial_math/valuation.py` |
| Service layer | `backend/app/services/portfolio_service.py` |
| API layer | `backend/app/api/v1/portfolio_api.py` |
| vNext unit tests (20 at creation) | `backend/test_scripts/test_services/test_portfolio_engine_vnext.py` |
| Builder tests (`TestCostConversionThroughAverageCosts`) | `backend/test_scripts/test_services/test_financial/test_portfolio_engine/test_daily_state_builder.py` |
| #32 and breakdown tests | `backend/test_scripts/test_services/test_financial/test_portfolio_cost_currency.py` |
| Shared `average_costs` helper for builder tests | `backend/test_scripts/test_services/_engine_average_costs.py` |
| Shared `native_cash` helper for builder tests | `backend/test_scripts/test_services/_engine_native_cash.py` |
| Internal transfers in the broker lines | `backend/test_scripts/test_services/test_financial/test_portfolio_engine/test_broker_internal_flows.py` |
| Foreign cash revaluation scenarios | `backend/test_scripts/test_services/test_financial/test_portfolio_engine/test_foreign_cash_revaluation.py` |
| Report-currency guard | `backend/test_scripts/test_services/test_financial/test_native_cash_guard.py` |
| Developer docs (engine section) | `mkdocs_src/docs/developer/backend/transactions/wac.md` |
| Developer docs (the layer, the engine step by step) | `mkdocs_src/docs/developer/backend/financial_math.md` |
| Math spec | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_2/portfolio_engine/portfolio_engine_architecture_v2.md` |
| Architecture state | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_2/portfolio_engine/ARCHITECTURE_CURRENT_STATE.md` |

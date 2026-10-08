---
title: "Inline WAC Computation"
category: concept
updated: 2026-10-07
tags: [backend, portfolio, wac, performance, engine, single-pass, cost-basis, average-cost, financial-math]
related:
  - entities/portfolio-engine
  - concepts/3-pool-cash-model
  - concepts/pre-frame-frame-separation
  - decisions/fifo-runtime-decision
  - decisions/financial-math-single-average-cost
  - problems/zero-purchase-cost-foreign-asset-paid-in-report-currency
  - features/F-097
---

# Concept: Inline WAC Computation

## Definition

**Inline WAC** is a single-pass algorithm that computes the Weighted Average Cost (WAC) of each position directly inside the portfolio engine's per-transaction loop — without issuing separate DB queries per asset. It replaced the old N×M pattern where `compute_wac_iterative()` made one DB round-trip per `(broker_id, asset_id)` combination during `get_summary()`.

Introduced in commit `39106380` (2026-06-30) as part of the portfolio engine 3-pool refactor.

> **Superseded in part on 2026-10-07 (workstream P, issue #32).** The engine no longer accumulates its own pools.
> `PortfolioCalculationEngine.calculate()` computes every position's cost timeline **once, before the replay**, with
> the single average-cost function `compute_average_costs()` (`backend/app/services/financial_math/average_cost.py`),
> and `DailyStateBuilder` replays those steps. The single-pass property survives — still no DB query per position —
> but two things changed: the pool now holds the **historical cost in the report currency T** (plus the cost in the
> asset currency A), not a pool in A re-converted every day; and no cost is converted inside the daily loop. The
> engine's own pools hid a gap as a zero cost (issue #32), see
> [[problems/zero-purchase-cost-foreign-asset-paid-in-report-currency]] and
> [[decisions/financial-math-single-average-cost]]. The sections marked *2026-06-30 model* below are kept as history.

## How It Works Since 2026-10-07

```text
calculate():
  positions     = build_cost_positions(classified_txs, asset_currencies, T, split_linked_tx_ids, date_to)
  average_costs = await compute_average_costs(db, positions, report_currency=T)   # one batched convert_bulk
  DailyStateBuilder(..., average_costs=average_costs)                             # required parameter

replay (pre-frame and frame alike), for each transaction that moves quantity:
  step = _next_cost_step((asset_id, broker_id), tx)   # RuntimeError when out of order: a bug, never data
  pool after the step = step.quantity, step.cost_report (C_T), step.cost_asset (C_A)
  SELL → realized cost = −step.cost_report_change     # C_T × q / Q; the whole C_T when the pool empties
  priced in-kind ADJUSTMENT in / out → capital baseline ± the cost the step added / removed
open cost basis of the day = Σ cost_report_for(qty) over the held positions — no exchange rate
```

The pool rules now live in the function, for every caller (engine, WAC facade, lots analysis, broker summary):

| Movement | Pool |
|---|---|
| Acquisition with a known cost | `Q += q`; `C_T += c_T` converted at the acquisition's own date (an amount already in T needs no rate); `C_A += c_A` with the same day's rate |
| Acquisition at zero cost | `Q += q`, cost unchanged |
| Acquisition of unknown cost, or whose rate into T is missing | `Q += q`, cost unchanged, pool **incomplete**, gap reported (`MISSING_COST_BASIS`, or the pair and its dates). A missing T→A rate leaves only the asset leg incomplete |
| Reduction | removes `C × q / Q` on both legs — exactly `C` when it empties the pool; quantity beyond the pool is clamped and listed |
| Split | `Q` changes, cost kept |
| Pool emptied | restarts at zero and complete |

The engine then exposes what used to need separate WAC queries: `PortfolioCalculationResult.realized_sales`
(`RealizedSale`: proceeds converted at the sale date, the historical cost removed) and `average_costs` (whose
`state_at(day)` gives the pool on any period boundary).

## The N×M Problem (Old Architecture)

Before the refactor, WAC was computed via three separate paths:

| Path | Caller | When | DB calls |
|------|--------|------|----------|
| `compute_wac_iterative()` | `get_summary()` per-asset loop | Per `(broker, asset)` at as_of_date | **N** (one per held asset) |
| `wac_series` pre-load | `PortfolioCalculationEngine.calculate()` step 8 | All `(broker, asset)` × scope | Separate bulk query |
| `compute_wac_from_txlist()` | Delegated to by both above | Pure math | 0 (pure function) |

With a portfolio of 20 assets × 2 brokers = **40 redundant DB+FX calls** per summary request, even when `get_report()` had already loaded `wac_series` in the engine result.

> `compute_wac_from_txlist()` and its module `backend/app/utils/financial/wac_utils.py` were deleted on 2026-10-07;
> `compute_wac_iterative()` survives as a facade over `compute_average_costs()` for the transaction preview, the
> automatic cost basis, `POST /portfolio/wac` and the PAC planner.

## How Inline WAC Worked (2026-06-30 model, superseded 2026-10-07)

The engine maintained two accumulators per position `(asset_id, broker_id)`:

```python
pool_qty[(a, b)]  = Decimal("0")   # cumulative quantity
pool_cost[(a, b)] = Decimal("0")   # cumulative cost basis (in WAC currency)
```

> In that model the "WAC currency" of the engine's pool was the **asset currency A**: `_buy_unit_cost()` converted each
> purchase into A (through a cross rate when A ≠ T), and the open cost was re-converted into T every day at that day's
> rate. That conversion is where issue #32 hid a missing rate as a zero cost.

As transactions are processed in chronological order:

**BUY** (qty > 0, cost > 0):
```
pool_qty_new  = pool_qty_old + qty_buy
pool_cost_new = pool_cost_old + buy_cost
wac_new       = pool_cost_new / pool_qty_new
```

**SELL** (qty < 0) — read WAC BEFORE reducing:
```
wac_at_sell   = pool_cost_old / pool_qty_old    # read first
sold_cost     = qty_sold × wac_at_sell
pool_qty_new  = pool_qty_old - qty_sold
pool_cost_new = pool_cost_old - sold_cost
wac_new       = wac_at_sell                     # WAC unchanged by SELL
```

**Key property**: WAC only changes on BUY (pool addition). SELL does NOT change the WAC (it only reduces the pool proportionally). This is the standard pool-cost accounting invariant.

## Why Reading WAC Before Reducing Matters

The SELL step **must** read `wac_at_sell` before modifying the pool. If the pool is reduced first (old bug):
- For a partial sell: no problem (WAC denominator changes proportionally)
- For a **full exit** (qty_sold = pool_qty): `pool_qty → 0`, division by zero / NaN WAC
- This caused full-sell proceeds to go entirely to the returns pool (R) instead of splitting K (cost recovered) + R (gain)

See [[concepts/3-pool-cash-model]] for how the K/R split uses `wac_at_sell`.

Since 2026-10-07 the invariant lives in the average-cost fold: the removed share `C × q / Q` is computed from the pool
before it is decremented, and a full exit removes exactly `C`, so cost is conserved exactly (no residue after a full
exit, no division by zero). An oversell is clamped: it removes the whole pool cost and is listed in
`oversold_movement_ids`.

## Integration with the 3-Pool Model

The inline WAC feeds directly into the 3-pool event-driven update for SELL:

```
P = sell_proceeds
C = sold_cost = qty_sold × wac_at_sell
G = P − C  (realized gain/loss)

K_new = K_old + C   (capital pool recovers cost)
R_new = R_old + G   (returns pool gets gain; if G < 0 and R+G < 0: deficit absorbs K)
```

Since 2026-10-07: `C` is the historical cost in the report currency that the SELL's step removed from the pool
(`−cost_report_change`), with no exchange rate at the sale date; `P` is the proceeds converted at the sale date. Both
are carried by `RealizedSale`, which `PortfolioService` also uses for the period's realized P&L.

## Performance Benefit

The refactor converts O(N) DB queries in `get_summary()` into zero additional DB queries — the WAC is computed during the same pass that processes transactions for daily state building. For a portfolio with N=20 positions, this eliminates 40 DB round-trips per `/report` request.

Since 2026-10-07: the engine makes two batched `convert_bulk` calls per run (the FX preload, and the costs inside
`compute_average_costs()`), and no cost conversion happens in the daily loop. `get_summary()` and
`get_positions_contribution()` no longer run a WAC query per sale or per position: realized P&L comes from
`realized_sales`, period-boundary costs from `state_at()`.

## Where It Applies

- `PortfolioCalculationEngine.calculate()` in `portfolio_engine.py` — builds the positions (`build_cost_positions()`) and makes the one `compute_average_costs()` call (since 2026-10-07)
- `DailyStateBuilder` in `portfolio_engine.py` — per-tx unified loop; since 2026-10-07 it replays the precomputed steps (`_next_cost_step()`) instead of accumulating its own pools
- Pre-frame loop: WAC computed for all historical transactions before t0
- Frame loop [t0, t1]: WAC available at every day for cost basis and 3-pool updates

## Important Invariant

```
wac(a, b, t) = pool_cost(a, b, t) / pool_qty(a, b, t)   when qty > 0
wac(a, b, t) = undefined                                  when qty = 0
```

When a position is fully exited (`pool_qty → 0`), both `pool_qty` and `pool_cost` reset to zero. The next BUY starts a fresh pool.

Since 2026-10-07: `DailyPositionState.wac` is `C_T / Q` **in the report currency** (`wac_currency` = T), with
`wac_asset` = `C_A / Q` in the asset currency alongside; `wac` and `unrealized_pnl` are `None` while the pool is
incomplete (`cost_complete = False`). An emptied pool is complete again: a gap before a full exit does not follow
later purchases.

## Source files

| Role | Path |
|------|------|
| Engine implementation (positions, replay of the cost steps) | `backend/app/services/portfolio_engine.py` |
| Average-cost function (pool rules, conversions) — since 2026-10-07 | `backend/app/services/financial_math/average_cost.py` |
| WAC facade (`compute_wac_iterative`) and realized P&L from `realized_sales` | `backend/app/services/portfolio_service.py` |
| vNext unit tests (20 at creation, 40 test functions by 2026-10-07) | `backend/test_scripts/test_services/test_portfolio_engine_vnext.py` |
| Average-cost unit tests | `backend/test_scripts/test_services/test_financial_math/test_average_cost.py` |
| Builder replay of the cost steps (`TestCostConversionThroughAverageCosts`) | `backend/test_scripts/test_services/test_financial/test_portfolio_engine/test_daily_state_builder.py` |
| Developer docs | `mkdocs_src/docs/developer/backend/transactions/wac.md` |
| Math spec | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_2/portfolio_engine/portfolio_engine_architecture_v2.md` §4.5 |
| Architectural analysis | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_2/portfolio_engine/ARCHITECTURE_CURRENT_STATE.md` §4 |

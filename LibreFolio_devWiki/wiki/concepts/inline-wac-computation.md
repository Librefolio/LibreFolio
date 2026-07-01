---
title: "Inline WAC Computation"
category: concept
tags: [backend, portfolio, wac, performance, engine, single-pass, cost-basis]
related:
  - entities/portfolio-engine
  - concepts/3-pool-cash-model
  - concepts/pre-frame-frame-separation
  - decisions/fifo-runtime-decision
  - features/F-097
---

# Concept: Inline WAC Computation

## Definition

**Inline WAC** is a single-pass algorithm that computes the Weighted Average Cost (WAC) of each position directly inside the portfolio engine's per-transaction loop — without issuing separate DB queries per asset. It replaced the old N×M pattern where `compute_wac_iterative()` made one DB round-trip per `(broker_id, asset_id)` combination during `get_summary()`.

Introduced in commit `39106380` (2026-06-30) as part of the portfolio engine 3-pool refactor.

## The N×M Problem (Old Architecture)

Before the refactor, WAC was computed via three separate paths:

| Path | Caller | When | DB calls |
|------|--------|------|----------|
| `compute_wac_iterative()` | `get_summary()` per-asset loop | Per `(broker, asset)` at as_of_date | **N** (one per held asset) |
| `wac_series` pre-load | `PortfolioCalculationEngine.calculate()` step 8 | All `(broker, asset)` × scope | Separate bulk query |
| `compute_wac_from_txlist()` | Delegated to by both above | Pure math | 0 (pure function) |

With a portfolio of 20 assets × 2 brokers = **40 redundant DB+FX calls** per summary request, even when `get_report()` had already loaded `wac_series` in the engine result.

## How Inline WAC Works

The engine maintains two accumulators per position `(asset_id, broker_id)`:

```python
pool_qty[(a, b)]  = Decimal("0")   # cumulative quantity
pool_cost[(a, b)] = Decimal("0")   # cumulative cost basis (in WAC currency)
```

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

## Integration with the 3-Pool Model

The inline WAC feeds directly into the 3-pool event-driven update for SELL:

```
P = sell_proceeds
C = sold_cost = qty_sold × wac_at_sell
G = P − C  (realized gain/loss)

K_new = K_old + C   (capital pool recovers cost)
R_new = R_old + G   (returns pool gets gain; if G < 0 and R+G < 0: deficit absorbs K)
```

## Performance Benefit

The refactor converts O(N) DB queries in `get_summary()` into zero additional DB queries — the WAC is computed during the same pass that processes transactions for daily state building. For a portfolio with N=20 positions, this eliminates 40 DB round-trips per `/report` request.

## Where It Applies

- `DailyStateBuilder` in `portfolio_engine.py` — per-tx unified loop
- Pre-frame loop: WAC computed for all historical transactions before t0
- Frame loop [t0, t1]: WAC available at every day for cost basis and 3-pool updates

## Important Invariant

```
wac(a, b, t) = pool_cost(a, b, t) / pool_qty(a, b, t)   when qty > 0
wac(a, b, t) = undefined                                  when qty = 0
```

When a position is fully exited (`pool_qty → 0`), both `pool_qty` and `pool_cost` reset to zero. The next BUY starts a fresh pool.

## Source files

| Role | Path |
|------|------|
| Engine implementation | `backend/app/services/portfolio_engine.py` |
| WAC utilities (pure math) | `backend/app/utils/wac_utils.py` |
| vNext unit tests (20 tests) | `backend/test_scripts/test_portfolio_engine_vnext.py` |
| Math spec | `LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/Milestone_2/portfolio_engine/portfolio_engine_architecture_v2.md` §4.5 |
| Architectural analysis | `LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/Milestone_2/portfolio_engine/ARCHITECTURE_CURRENT_STATE.md` §4 |

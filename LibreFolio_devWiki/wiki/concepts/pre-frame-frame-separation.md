---
title: "Pre-Frame / Frame Separation"
category: concept
tags: [backend, portfolio, engine, performance, pre-frame, daily-state, computation-window]
related:
  - entities/portfolio-engine
  - concepts/inline-wac-computation
  - concepts/3-pool-cash-model
  - features/F-054
  - features/F-055
---

# Concept: Pre-Frame / Frame Separation

## Definition

The portfolio engine divides its computation into two logically distinct phases:

- **Pre-frame** (`tx.date < t0`): processes all historical transactions before the requested start date. Updates accounting state (qty, WAC, cash, K/R/W pools) without performing any market valuation.
- **Frame** (`t ∈ [t0, t1]`): computes full daily portfolio states with market prices, FX rates, position values, and pool snapshots.

Introduced as an explicit design principle in `portfolio_engine_architecture_v2.md` and implemented in commit `39106380` (2026-06-30).

## Motivation

Market evaluation (backward-fill price lookup, FX conversion) is expensive and needed only for days within the requested range. Historical transactions before `t0` only affect the _starting state_ — the initial qty, WAC, and pool values from which the frame calculation begins.

Without this separation:
- Computing a 3-month chart would require evaluating market prices for every day since portfolio inception
- The engine would be O(total_history × N_assets) instead of O(pre_frame_txs + frame_days × N_assets)
- Cache range extension would be impossible (you can't reuse pre-frame state across different t0 values)

## Pre-Frame Computation

For each transaction with `tx.date < t0`, in chronological order:

```
1. Update cash ledger (all tx types with amount ≠ 0)
2. Update quantity ledger: qty[(a, b)] += tx.quantity (for BUY, SELL, TRANSFER, ADJUSTMENT)
3. Update WAC inline:
   - BUY  → pool_qty += qty; pool_cost += cost; wac_new = pool_cost/pool_qty
   - SELL → sold_cost = qty × wac; pool_qty -= qty; pool_cost -= sold_cost
4. Update 3-pool (K/R/W) using event-driven rules
5. Accumulate realized gain/loss into period accumulators
```

**What the pre-frame does NOT do:**
- Fetch or use market prices
- Compute market value
- Evaluate FX rates for valuation
- Build `DailyPortfolioState` or `DailyPositionState` objects
- Emit any chart data points

## Frame Computation [t0, t1]

For each day `t` in the requested range:

```
1. Apply transactions of the day (qty, WAC, cash, 3-pool)
2. Fetch price(asset, t) — backward-fill within the frame
3. Fetch FX rate(from_ccy, to_ccy, t)
4. Compute DailyPositionState per position:
   - market_value = qty × valuation_price × FX
   - cost_basis = qty × wac × FX
   - unrealized_pnl = market_value − cost_basis
5. Aggregate DailyPortfolioState (sum over positions in S)
6. Emit 3-pool snapshot (K, R, W at end of day)
7. Compute derived fields (NAV, book_value, unrealized_gain_loss)
```

## Valuation Price Hierarchy (Frame Only)

Within the frame, asset valuation uses a 3-tier fallback:

```
1. MARKET_PRICE     → PriceHistory backward-fill (last known close ≤ t)
2. LAST_BUY_PRICE   → last BUY transaction price across all visible brokers V(u)
                      (not restricted to selected brokers S)
3. MISSING          → excluded from NAV; data_quality flag raised
```

The `LAST_BUY_PRICE` fallback is intentionally **broker-scope-independent**: it uses `V(u)` (all brokers visible to the user), not `S` (currently selected). This is because price is a property of the _asset_, not the broker.

> Example: user has Directa + IBKR. Dashboard filter = Directa only. Last BUY of VWCE was on IBKR. Valuation fallback uses that IBKR price as LAST_BUY_PRICE for VWCE in the Directa scope.

## Blob Cache Interaction

The pre-frame/frame separation enables range-aware blob caching:

```
blob = [ta, tb]      (previously computed range)
request = [t0, t1]   (new request)
```

If `[t0, t1] ⊆ [ta, tb]` and fingerprint is valid → **full cache hit**, reuse blob.

If `t0 < ta` → compute `[t0, ta-1]` (extend left):
- Need pre-frame state at t0 (recomputed from scratch)
- Merge with existing `[ta, tb]`

If `t1 > tb` → compute `[tb+1, t1]` (extend right):
- Pre-frame state at `tb+1` = last day of blob (already stored)
- Compute frame from `tb+1` to `t1` and merge

This makes dashboard range-switching (1W→1M→3M→1Y) efficient: switching to a longer range only computes the new left/right extension.

## Why Not Skip Pre-Frame?

The pre-frame cannot be skipped because the engine requires:
- **Correct qty at t0**: position sizes depend on all historical BUY/SELL/TRANSFER before t0
- **Correct WAC at t0**: used for cost basis and the 3-pool K/R split in the frame
- **Correct 3-pool state at t0**: K/R/W pools at start of frame depend on all prior DEPOSIT/WITHDRAWAL/SELL/DIVIDEND/etc.
- **Correct cash at t0**: all prior tx amounts sum to the starting cash balance

## Source files

| Role | Path |
|------|------|
| Engine implementation | `backend/app/services/portfolio_engine.py` |
| Math spec §3, §7 | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_2/portfolio_engine/portfolio_engine_architecture_v2.md` |
| Blob cache spec §12 | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_2/portfolio_engine/portfolio_engine_architecture_v2.md` |
| Architecture overview | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_2/portfolio_engine/ARCHITECTURE_CURRENT_STATE.md` |

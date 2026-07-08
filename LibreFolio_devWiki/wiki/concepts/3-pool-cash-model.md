---
title: "3-Pool Cash Model"
category: concept
tags: [backend, portfolio, cash, decomposition, dashboard, growthchart, accounting, capital, event-driven, k-r-w-pools]
related:
  - entities/portfolio-engine
  - entities/portfolio-service
  - concepts/portfolio-report-unified
  - concepts/inline-wac-computation
  - features/F-054
---

# Concept: 3-Pool Cash Model

## Definition

The 3-pool cash model decomposes the portfolio's cash position into three semantically distinct pools that track capital provenance and return generation. It is implemented as an **event-driven state machine** in `DailyStateBuilder` — every transaction triggers a precise update to the pool state. This decomposition powers the GrowthChart stacked-area visualization on the Dashboard.

The formal notation (from `portfolio_engine_architecture_v2.md` §11):

```
K(t) = capital_pool          — user's own capital currently in the system
R(t) = returns_pool          — generated returns still in the system
W(t) = withdrawn_returns_pool— generated returns that left the system (tracked as restorable)
```

`W` is a hidden bookkeeping pool: not directly visible in the UI, but enables correct deposit accounting when returns were previously withdrawn.

## Event-Driven Pool Updates

### DEPOSIT (D > 0)
First restore previously-withdrawn returns, then add new capital:
```
restore = min(D, W_old)
R_new = R_old + restore
W_new = W_old - restore
K_new = K_old + (D - restore)
```

### WITHDRAWAL (X > 0)
Drain capital first, then returns (moved to W):
```
from_capital = min(X, K_old)
K_mid = K_old - from_capital
remaining = X - from_capital

from_returns = min(remaining, R_old)
R_new = R_old - from_returns
W_new = W_old + from_returns
K_new = K_mid
```

### DIVIDEND / INTEREST (I > 0)
Pure return — only R increases:
```
R_new = R_old + I
K_new = K_old
W_new = W_old
```

### SELL — Read WAC BEFORE Reducing Pool ⚠️
This is the critical fix introduced in commit `39106380`. The WAC must be read _before_ the pool is reduced to avoid incorrect K/R split on full exit:
```
P = sell_proceeds (cash received, converted to target_ccy)
C = sold_cost_basis = qty_sold × wac_before_sell × FX
G = P − C  (realized gain/loss)

K_mid = K_old + C          (capital pool recovers cost basis)
R_mid = R_old + G          (returns pool gets gain)

if R_mid >= 0:
    K_new = K_mid
    R_new = R_mid
else:
    K_new = K_mid + R_mid  (loss larger than returns — deficit absorbs K)
    R_new = 0
```

**Why this matters**: if the pool was reduced FIRST (old bug), then a full exit (`pool_qty → 0`) would compute `wac = pool_cost / 0` — undefined. All proceeds would go to the returns pool instead of correctly splitting into recovered cost (→K) and gain (→R).

### BUY (B > 0)
Drain returns first, then capital:
```
from_returns = min(B, R_old)
R_mid = R_old - from_returns
remaining = B - from_returns
K_new = K_old - remaining
R_new = R_mid
```

### FEE / TAX (F > 0)
Reduce returns first; if deficit, absorb into capital:
```
R_mid = R_old - F
if R_mid >= 0:
    R_new = R_mid; K_new = K_old
else:
    R_new = 0; K_new = K_old + R_mid   (negative R_mid reduces K)
```

## Reconciliation Invariant

At end of each day:
```
cash_like(t) ≈ K(t) + R(t)

where cash_like(t) = cash(t) + in_transit_cash(t)
```

`W(t)` does not enter this invariant — it represents returns that have already left the system. Any deviation from this invariant is a `reconciliation_delta` data quality flag. The engine does **not** silently correct the delta.

## Where It Applies

- `DailyStateBuilder` in `portfolio_engine.py` — event-driven updates per transaction
- Pre-frame loop: K/R/W state built up from all historical transactions before t0
- Frame loop [t0, t1]: pool snapshots emitted daily in `DailyPortfolioState`
- GrowthChart frontend: 3 series
  - Series 1 (dark solid line): NAV
  - Series 2 (dashed): capital baseline (K + R at end of day ≈ cash provenance)
  - Series 3 (dotted): realized/returns cash

## Semantic Difference: K/R vs Old "Deposited/Invested/Realized"

The new K/R/W model supersedes the earlier informal 2-pool description ("deposited capital" / "invested capital" / "realized cash"). Key differences:
- **K** tracks _net capital currently in system_ (after accounting for withdrawals, not just total deposits)
- **R** captures all returns still in system (dividends + realized gains), not just SELL proceeds
- **W** enables correct DEPOSIT accounting when returns were previously withdrawn

## Important Caveat

> The 3-pool decomposition is a **visualization convention**, not a fiscal accounting standard. It correctly tracks provenance but does NOT equal the authoritative P&L numbers in the KPI cards. The KPI cards use the WAC-based per-SELL realized gain calculation from `get_summary()`.

## Source files

| Role | Path |
|------|------|
| Engine implementation | `backend/app/services/portfolio_engine.py` |
| Math spec §11 | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_2/portfolio_engine/portfolio_engine_architecture_v2.md` |
| GrowthChart component | `frontend/src/lib/components/charts/GrowthChart.svelte` |
| Dashboard page | `frontend/src/routes/(app)/dashboard/+page.svelte` |
| vNext unit tests | `backend/test_scripts/test_portfolio_engine_vnext.py` |

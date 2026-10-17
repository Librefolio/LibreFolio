---
title: "3-Pool Cash Model"
category: concept
updated: 2026-10-12
tags: [backend, portfolio, cash, decomposition, dashboard, growthchart, accounting, capital, event-driven, k-r-w-pools, native-cash, fx]
related:
  - entities/portfolio-engine
  - entities/portfolio-service
  - entities/native-cash
  - concepts/portfolio-report-unified
  - concepts/inline-wac-computation
  - decisions/financial-math-single-average-cost
  - decisions/native-cash-daily-revaluation
  - decisions/portfolio-pnl-series-contracts
  - problems/foreign-cash-never-revalued
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

In the code K and R are kept **per broker** (`K[b]`, `R[b]`, since 2026-07-01, `c2dd44763`) and W is global; each rule
below applies to the broker of the transaction, and the display series sum the brokers.

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
Signed since 2026-09-18 (`8ed7a0f0d`): a negative correction lowers R by its amount.

### SELL — Read WAC BEFORE Reducing Pool ⚠️
This is the critical fix introduced in commit `39106380`. The WAC must be read _before_ the pool is reduced to avoid incorrect K/R split on full exit:
```
P = sell_proceeds (cash received, converted to target_ccy)
C = sold_cost_basis = qty_sold × wac_before_sell × FX     ← until 2026-10-07 (WAC in the asset currency × the sale-date rate)
C = −cost_report_change of the SELL's average-cost step   ← since 2026-10-07: historical cost in the report currency,
  = C_T × qty_sold / Q   (the whole C_T if the pool empties)   no exchange rate
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

**Since 2026-10-07** (workstream P — [[decisions/financial-math-single-average-cost]]): the cost a SELL returns to K is
the historical cost in the report currency that its precomputed average-cost step removed from the pool — each purchase
converted at its own date, no rate at the sale date. P is still the proceeds converted at the sale date; if they cannot
be converted, the sale moves neither pool and its pair is reported with the date (`missing_fx`). The read-before-reduce
rule below now lives in the average-cost fold, which also removes exactly C_T on a full exit.

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

### CASH_TRANSFER / FX_CONVERSION, a linked pair inside the scope (X > 0)
Only the `linked_internal` legs move the pools — also when both legs are on the same broker:
```
departure broker A:  from_r = min(X, R_A);  R_A -= from_r;  K_A -= X - from_r
arrival broker B:    K_B += X          ← "Approximate": the split is not carried over
```
The code marks the arrival rule as an approximation; backlog B3 (section I) keeps it open. External halves and normal
legs do not touch K/R. Separately, since lot 41 (2026-10-11) the arrival day of a pair between two brokers also moves
X from A's capital baseline to B's, a zero-sum flow — [[decisions/portfolio-pnl-series-contracts]], G1a.

### EXCHANGE RESULT ON FOREIGN CASH (since 2026-10-11)
On every day the rate of a foreign currency held as cash changes, the broker's cash is revalued to its native balances
at that day's rate ([[decisions/native-cash-daily-revaluation]], lot 41 F, option **k2**):
```
ε_b = value_at(day)[b] − cash_b          (NativeCash, financial_math/native_cash.py)
cash_b += ε_b
R_b    += ε_b
if R_b < 0:  K_b += R_b;  R_b = 0         (a loss beyond the returns comes out of capital, as a FEE)
```
The capital baseline never moves: an exchange result is a result, not a contribution. Option k1 (only rescaling the
pools) was rejected because it would put part of an exchange gain into K. In the pre-frame and in the frame alike the
revaluation comes after the day's cash and before the day's pool rules (in the frame: at the end of step 4a, before
the per-transaction loop 4b).

### Pre-frame approximation
A SELL in the pre-frame puts all its proceeds into K (the code: "WAC not tracked yet in pre-frame for sell cost
basis"); the cost/gain split above is applied only in the frame. In production the pre-frame is empty
(`date_from=None`), so only tests exercise it.

## Reconciliation

At the end of each frame day the engine clamps every broker's K and R at zero or above (step 4g) and sums them. The
display values then split `cash_like(t) = cash(t) + in_transit_cash(t)`:
```
pool_sum = ΣK + ΣR
if pool_sum > 0 and |pool_sum − cash_like| > 0.01:
    cash_from_contributed = max(ΣK × cash_like / pool_sum, 0)     ← the summed pools are rescaled
else:
    cash_from_contributed = min(ΣK, cash_like)
cash_from_generated = max(cash_like − cash_from_contributed, 0)
```

`W(t)` does not enter: it represents returns that have already left the system.

> *Corrected 2026-10-12.* Until then this section said that a deviation from `cash_like ≈ K + R` became a
> `reconciliation_delta` data-quality flag and that the engine never corrected it. The architecture spec has that
> name; the code never had it (no `reconciliation_delta` in `backend/` or `frontend/src` at `5d0585595`). The
> rescaling above dates from 2026-06-25 (`7aa1f7772`), and it works on the **summed** pools, not broker by broker —
> the same correction lot 41's documentation made in the theory pages (step F-5).

## Where It Applies

- `DailyStateBuilder` in `financial_math/portfolio/daily_state.py` — event-driven updates per transaction, and the
  exchange results of `_revalue_foreign_cash()` on rate-change days
- `NativeCash` in `financial_math/native_cash.py` — the native balances the exchange result is measured against
  ([[entities/native-cash]])
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
>
> *Superseded 2026-10-07 (last sentence):* the KPI cards' realized P&L no longer comes from a per-SELL computation in
> `get_summary()`. It is Σ (proceeds − cost) over the engine's `realized_sales` dated in the period
> (`_period_realized_sales()` in `portfolio_service.py`), leaving out — and reporting — a sale whose proceeds could not
> be converted or whose pool cost was incomplete. Each `RealizedSale` carries the same removed cost C as the K/R
> update above; the pools are still not the KPI figures.

## Source files

| Role | Path |
|------|------|
| Engine implementation | `backend/app/services/financial_math/portfolio/daily_state.py` |
| Native cash, exchange results (since 2026-10-11) | `backend/app/services/financial_math/native_cash.py` |
| Exchange-result scenarios (k2) | `backend/test_scripts/test_services/test_financial/test_portfolio_engine/test_foreign_cash_revaluation.py` |
| Theory — exchange result on foreign cash, reconciliation | `mkdocs_src/docs/financial-theory/technical-analysis/performance-metrics/portfolio-engine/index.en.md` |
| Theory — the pools by broker, example D | `mkdocs_src/docs/financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.en.md` |
| Sold cost C (average-cost step, since 2026-10-07) | `backend/app/services/financial_math/average_cost.py` |
| KPI realized P&L from `realized_sales` (since 2026-10-07) | `backend/app/services/portfolio_service.py` |
| Math spec §11 | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_2/portfolio_engine/portfolio_engine_architecture_v2.md` |
| GrowthChart component | `frontend/src/lib/features/dashboard/GrowthChart.svelte` |
| Dashboard page | `frontend/src/routes/(app)/dashboard/+page.svelte` |
| vNext unit tests | `backend/test_scripts/test_services/test_portfolio_engine_vnext.py` |

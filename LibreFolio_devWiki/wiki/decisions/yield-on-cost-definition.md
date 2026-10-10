---
title: "Yield on Cost: trailing-year ledger income per unit over the residual average cost, per (asset, broker)"
category: decision
status: resolved
date: 2026-09-11
tags: [backend, portfolio, yield-on-cost, income, dividend, fifo, wac, average-cost, fx, data-quality]
related: [features/F-100, decisions/fifo-v4-income-eligibility-d1, concepts/d1-income-eligibility-window, decisions/financial-math-single-average-cost, features/F-097, entities/portfolio-service, sources/phase00-yield-on-cost-2026-09]
---

# Decision: what Yield on Cost means in LibreFolio

## Context

Release 2 (U3, SP06) asked for a Yield on Cost column on the Dashboard positions. "YOC" has several popular
definitions, and most of them move for reasons that have nothing to do with the income: a partial sale, a
re-import in a different order, a transfer between brokers.

## Decision

```
YOC(asset, broker, T) =  Σ gross income per eligible unit, over [T − 364, T]
                         ─────────────────────────────────────────────────
                               residual average cost per unit at T
```

- **Income**: the user's own DIVIDEND and INTEREST **transactions** linked to the asset — gross, so TAX and FEE
  are excluded; `AssetEvent` rows are not an income source. Each payout is converted to the report currency **at its
  own date** and divided by the **eligible LONG quantity at the end of the day before payment (D-1)**, adjusted for
  later splits — the same D-1 rule as the FIFO income allocator, reused (`eligible_income_quantity` from
  `fifo_lot_engine.py`), not re-implemented a third time.
- **Window**: the trailing 365 calendar days, both ends included (`as_of_date − 364 … as_of_date`).
- **Denominator**: the residual average cost per unit at T, in the report currency. Since 2026-10-07 it is the
  engine's `position.wac`, which comes from the single average-cost function
  ([[decisions/financial-math-single-average-cost]]).
- **Grain**: per `(asset, broker)`. The FIFO replay runs over the group of brokers linked by transfers of the asset,
  so a transferred lot keeps its history; income stays with the broker that received it.
- **Status contract** (`YieldOnCostResult`): `available` (value ≥ 0, at least one income transaction),
  `no_income` (value 0, none received; a recorded zero income is `available` with `net_zero`) and `unavailable`
  with a reason — `insufficient_history`, `income_without_eligible_quantity`, `replay_inconsistent`,
  `invalid_split`, `missing_fx`, `missing_wac`, `non_positive_wac`. One payout that cannot be converted or
  allocated makes the whole metric unavailable: a partial YOC would understate silently.

## Options rejected

1. **Income ÷ current cost basis** — a partial sale shrinks the basis and inflates the yield.
2. **Income ÷ current quantity** — income received on units sold since is credited to the units left.
3. **Ordering same-day trades by `(date, id)`** — the import order would decide whether a same-day BUY was eligible.
4. **End-of-day quantity** — contradicts the FIFO D-1 rule ([[decisions/fifo-v4-income-eligibility-d1]]).
5. **One asset-wide value across brokers** — mixes positions with different costs and histories.

## Consequences

- YOC is stable under re-imports, partial sales and transfers, and it says why when it cannot be computed.
- It is cached with the report: `compute_yield_on_cost_dependency_identity()` hashes what the value depends on.
- Theory page in English only (IT/FR/ES translation debt, backlog I-08).

## Links

- [[features/F-100]] — the feature.
- [[concepts/d1-income-eligibility-window]] — the eligibility rule it shares with FIFO.
- Source: [[sources/phase00-yield-on-cost-2026-09]].

## Source files

| Role | Path |
|------|------|
| Calculation, dependency identity | `backend/app/services/yield_on_cost.py` |
| D-1 eligible quantity (shared) | `backend/app/services/fifo_lot_engine.py` |
| `YieldOnCostResult`, reasons, `PortfolioHolding.yield_on_cost` | `backend/app/schemas/portfolio.py` |
| Caller (holdings, cache identity) | `backend/app/services/portfolio_service.py` |
| Tests | `backend/test_scripts/test_services/test_financial/test_yield_on_cost.py` |
| Theory page | `mkdocs_src/docs/financial-theory/technical-analysis/performance-metrics/portfolio-engine/yield-on-cost.en.md` |
| Plan (§1–2, rejected alternatives §2.1) | `LibreFolio_developer_journal/Release_2/phases/19_yieldOnCost/plan-phase00YieldOnCost.prompt.md` |

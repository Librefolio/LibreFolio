---
title: "Issue #32: a foreign-currency asset paid in the report currency showed a zero purchase cost"
category: problem
status: resolved
date: 2026-10-07
resolved_date: 2026-10-07
tags: [backend, portfolio-engine, wac, average-cost, fx, cost-basis, dashboard, silent-failure, issue-32]
related:
  - decisions/financial-math-single-average-cost
  - entities/portfolio-engine
  - concepts/inline-wac-computation
  - concepts/absence-sentinel-vs-nullable-type
  - concepts/holdings-performance-panel
  - problems/fifo-income-silently-dropped-after-full-close
  - features/F-097
  - features/F-054
---

# Problem: zero purchase cost for a foreign-currency asset paid in the report currency (#32)

## Symptom

GitHub issue [#32](https://github.com/Librefolio/LibreFolio/issues/32): an asset quoted in **USD**, bought three
times paying **EUR** (100 € + 150 € + 150 € = 400 €).

- On a Dashboard in **EUR** its purchase cost was **0** and its WAC per unit 0, so its whole market value showed as
  unrealized gain. By the identity of the period P&L, the "Other / reconciliation residual" absorbed the −400 €
  (see [[concepts/holdings-performance-panel]]).
- On a Dashboard in **USD** the same asset was correct.
- Nothing said that a number was missing: no banner, no missing pair.

## Root Cause

Three facts combined, all in `backend/app/services/portfolio_engine.py` as it was before 2026-10-07:

1. **The engine kept each (asset, broker) average-cost pool in the asset currency A**, so every purchase had to be
   converted from the paid currency P into A. `DailyStateBuilder._buy_unit_cost()` did it with rates read, unfiltered,
   from the preloaded `fx_rate_map`: r(P→T, d) when A = T (T = report currency), otherwise the cross rate
   r(P→T, d) / r(A→T, d).
2. **`_preload_fx_rates()` never loads the identity key `(T, T, d)`** — it only collects currencies with
   `ccy != target`. With P = T ≠ A (EUR paid, USD asset, EUR Dashboard) the cross rate's numerator `(EUR, EUR, d)` was
   absent and `_buy_unit_cost()` returned `None`. On a USD Dashboard (A = T) the branch read `(EUR, USD, d)`, which
   *was* loaded — hence the correct figure there.
3. **`None` was absorbed silently.** `_buy_unit_cost()` returned `None` both for "this acquisition has no known cost"
   and for "a rate is missing". The callers — the pre-frame and the frame loops — treated both as "add the quantity at
   the current average cost", which is 0 for an empty pool, and recorded nothing in `missing_fx`.

The cost of a movement depended on map keys that another method, written for another purpose, happened to load; and an
absent key could not be told apart from an absent cost. [[concepts/absence-sentinel-vs-nullable-type]] describes the
general shape.

### Same-root twins

- **ADJUSTMENT / TRANSFER-in with a `cost_basis_override` in T on an asset in A ≠ T** (opening positions with a euro
  cost on dollar securities, for example): cost 0, **and** the in-kind capital never entered deposited capital, because
  `_capital_flow_for_adjustment_in()` received `None` — so the total P&L was inflated by the position's value.
- **A cost basis in a third currency:** the key `(cbo_ccy, T, d)` was loaded only if that currency happened to appear
  elsewhere on that day — same silent fallback otherwise.

### Other silent fallbacks found by the same analysis

- Engine reductions and position states used the asset-currency amount **as if it were in T** when a rate was missing
  — a wrong value rather than a zero, with no signal.
- The engine's per-day `missing_fx_pairs` had no reader in `portfolio_service.py`, so even the gaps the engine did
  record never reached the banner.
- The service's realized P&L skipped a sale, or used its unconverted proceeds, when a rate was missing, and discarded
  the missing pairs.
- The lots analysis WAC row fell back to the unconverted cost.
- `GET /brokers/{id}/summary` summed BUY amounts in mixed currencies and ignored sales and transfers
  (`TransactionService.get_cost_basis()`).

## Solution

No patch to `_buy_unit_cost()` — an identity rate would have closed this symptom and nothing else. The developer chose
a single average-cost implementation in a new service layer: [[decisions/financial-math-single-average-cost]]. For #32
specifically:

- `compute_average_costs()` (`backend/app/services/financial_math/average_cost.py`) converts every acquisition into T
  at its own date. An amount already in T is taken as it is and needs no rate, so the issue's asset costs exactly
  `Decimal("400")`; the USD Dashboard is unchanged.
- `PortfolioCalculationEngine.calculate()` calls it once for every position, after the FX preload, and
  `DailyStateBuilder` replays its steps (`average_costs` is a required parameter). `_buy_unit_cost`,
  `_compute_open_cost_basis_inline`, `_capital_flow_for_adjustment_in` and `_apply_split_rescale` are gone.
- The twins: a cost basis in T is taken as it is; a third currency is converted through the FX service at the
  movement's date, not looked up in a map someone else filled; a priced ADJUSTMENT's in-kind capital enters the capital
  baseline with the cost its step added.
- A missing rate becomes a `MissingConversion(pair, dates)` that travels to `missing_fx`, `summary.missing_fx_pairs`
  and the yellow banner; an unknown cost becomes a `MISSING_COST_BASIS` warning. Never a silent zero.
- The other fallbacks listed above were removed by the same change: realized P&L comes from the engine's
  `realized_sales`, the lots WAC lines and the broker summary call the same function.

## Regression tests

| Test | What it pins |
|------|--------------|
| `test_portfolio_cost_currency.py::TestIssue32ReportCurrencyCost` | S1 — EUR report, foreign asset paid in EUR costs what was paid; S2 — report in the asset currency unchanged; S3 — an opening position costed in the report currency is capital, not profit |
| `test_portfolio_cost_currency.py::TestCostDiagnostics` | S4–S6 — an unconvertible purchase leaves the cost incomplete and reaches the banner with its dates; a missing cost basis raises `MISSING_COST_BASIS` |
| `test_portfolio_cost_currency.py::TestAverageCostInvariants` | I1–I7 — single-currency figures unchanged, full exit, split, facade rows and fail-safe, lots lines |
| `test_portfolio_cost_currency.py::TestLotsAverageCostLines` | L1–L3 — the lots WAC lines of the #32 case; gaps reported, `DEGRADED` |
| `test_portfolio_cost_currency.py::TestPeriodUnrealizedBreakdown` | B1–B4 — the #32 asset's unrealized change split into asset and exchange-rate effect; rows add up exactly |
| `test_daily_state_builder.py::TestCostConversionThroughAverageCosts` | The case at builder level: a BUY paid in the target currency costs the amount exactly |
| `test_average_cost.py` | Unit tests of the function: conversions through the FX service, pool arithmetic, adapter, target currency |
| `test_portfolio_api.py::TestIssue32PurchaseCostInReportCurrency` | End to end through `POST /portfolio/report`: 400 in EUR, each payment at its own date's rate in the asset currency |

## Prevention

- A calculation fetches the conversions it needs itself; it does not depend on keys that another method preloads.
  That is the first rule of the `financial_math` layer.
- "Unknown cost", "zero cost" and "rate missing" are three states with three effects (`add_unknown_cost`,
  `add_zero_cost`, `add_missing_fx`), never one `None`.
- Every gap surfaces as pair + dates, or as `MISSING_COST_BASIS`; a per-position figure with a gap is `None`, never a
  guessed value.
- Test currency triples, not pairs: P = T ≠ A is exactly the case the cross-rate formula missed, and a third currency
  is its twin.

## Impact

User-facing and silent: a zero purchase cost and an inflated unrealized gain on the Dashboard for any foreign asset
bought with the report currency; a total P&L inflated by the value of opening positions costed in the report
currency. The fix intentionally changes other visible numbers for foreign positions (historical cost, exchange-rate
effect inside the unrealized change); they are listed in [[decisions/financial-math-single-average-cost]].

## Source files

| Role | Path |
|------|------|
| Fix: the average-cost function | `backend/app/services/financial_math/average_cost.py` |
| Engine (where `_buy_unit_cost` lived; now `build_cost_positions` + replay) | `backend/app/services/portfolio_engine.py` |
| Service (realized P&L, missing pairs, `MISSING_COST_BASIS` assets) | `backend/app/services/portfolio_service.py` |
| `IssueCode.MISSING_COST_BASIS` | `backend/app/schemas/portfolio.py` |
| Engine / service / lots regression tests | `backend/test_scripts/test_services/test_financial/test_portfolio_cost_currency.py` |
| Builder-level regression tests | `backend/test_scripts/test_services/test_financial/test_portfolio_engine/test_daily_state_builder.py` |
| Unit tests | `backend/test_scripts/test_services/test_financial_math/test_average_cost.py` |
| API regression test | `backend/test_scripts/test_api/test_portfolio_api.py` |
| Developer docs | `mkdocs_src/docs/developer/backend/transactions/wac.md` |
| Plan (§1 analysis, §3.2 the #32 numbers) | `LibreFolio_developer_journal/Release_2/phases/30_wacUnification/plan-phase00WacUnification.prompt.md` |

---
title: "Native cash (financial_math.native_cash)"
category: entity
type: module
updated: 2026-10-12
tags: [backend, financial-math, native-cash, cash, fx, portfolio-engine, portfolio-service, ai-export, lot-41]
related:
  - decisions/native-cash-daily-revaluation
  - decisions/financial-math-one-home
  - decisions/financial-math-single-average-cost
  - entities/portfolio-engine
  - entities/portfolio-service
  - concepts/3-pool-cash-model
  - problems/foreign-cash-never-revalued
  - problems/ai-export-reconciled-false-on-rounding-dust
  - sources/phase00-broker-pnl-flows-2026-10
---

# Native cash

## Role

The single reconstruction of every broker's cash in the currencies it was recorded in. From plain cash movements it
gives the balance of each broker in each currency, the value of those balances in the report currency on any day
(foreign balances at that day's rate), the period flows by type and by position (each converted at its own date), the
exchange result on cash over a window, and every conversion that could not be made. The portfolio engine, the
portfolio service and AI Export read cash from it. Why it exists, and the K/R rule for its exchange results:
[[decisions/native-cash-daily-revaluation]].

## Location

`backend/app/services/financial_math/native_cash.py` (490 lines at `5d0585595`), flat next to `average_cost.py` in the
financial math layer ([[decisions/financial-math-one-home]]). It imports only `Currency` (`schemas.common`) and
`convert_bulk` (`services.fx`), from the modules that define them.

## Key Interfaces

| Name | What it does |
|------|--------------|
| `compute_native_cash(session, movements, *, report_currency, rates_until=None)` | async; **one** `convert_bulk` call: each foreign movement at its own date, then one unit of each foreign currency on every day from its first movement to `rates_until` (its last movement when None). No call at all when every non-zero amount is already in the report currency. |
| `CashMovement` | one cash change: id, type, date, broker, position (or None), currency, signed amount, share; `native` = amount × share |
| `cash_movement_from_transaction(tx, *, share=1)` | the adapter; None when the transaction records no cash amount. A zero amount is kept: it changes no figure and never needs a rate. |
| `effective_share(role, share_percentage)` | OWNER → its share (1 when None, 0 kept); EDITOR and VIEWER → 1 — the only copy of the rule (O2) |
| `NativeCash.value_at(day)` | each broker's cash on `day` in the report currency; only brokers with a counted movement on or before `day` |
| `NativeCash.balances(as_of=None)` | each broker's balance per currency, zero and unconverted movements included |
| `NativeCash.flows(date_from, date_to)` | `CashFlows` of `(date_from, date_to]`: signed and absolute sums by type, income and costs by position, unallocated by broker |
| `NativeCash.sums_by_date(date_from, date_to, types)` | counted movements summed by date and type, dates ascending |
| `NativeCash.missing_conversions(date_from, date_to, types)` | `MissingCashConversion(pair, dates)` for every pair that could not be converted |
| `NativeCash.rate_change_days(date_from, date_to)` | the days a held foreign currency's rate changes (the first rate counts); computed by `change_days` |
| `change_days(read, currencies, days)` | pure, the one home of «the day a rate changes» (J CP-6, 2026-10-16): the days of the calendar on which the caller's reading gives a currency another rate than on the previous day; a rate on the first day counts. The native cash reads the last rate known, on the calendar of its rate points; the portfolio engine the exact day's rate, on its frame |
| `NativeCash.foreign_cash_broker_ids` | brokers with a counted movement outside the report currency |
| `NativeCash.exchange_results(date_from, date_to)` | each foreign-cash broker's exchange result on cash over `(date_from, date_to]`, returned whole |
| `CONVERSION_DUST` | `Decimal("1e-9")`: below it an exchange result is the rounding of two conversions, not a result |

## Design Notes

- **No silent zero.** A movement whose conversion is missing stays out of values and flows, and its pair is reported
  with every date it was needed on (policy (a) of lot 41).
- **`rates_until` is the caller's obligation**, and the code does not check it: after that day the last rate carries
  forward, and `value_at()` raises `ValueError` for a non-zero foreign balance with no rate on or before the day. The
  engine passes `actual_to`; the service, when it builds its own ledger, `date_to or today`.
- **Two conversions of the same cash can differ in the 28th digit.** The engine values cash as amount × unit rate,
  while `convert_bulk` divides on an inverse pair: 5000 at 1/1.1 gives …454546 one way and …545 the other. Hence
  `CONVERSION_DUST`, which callers use to hide a figure that is only that rounding: the «FX on cash» row, the
  contributions residual, and the `reconciled` flag of AI Export ([[problems/ai-export-reconciled-false-on-rounding-dust]]).
- **Cash in the report currency needs no rate**, so a portfolio with no foreign cash makes no conversion at all and
  keeps every output byte-identical (the guard of lot 41).

## Callers

- `PortfolioCalculationEngine.calculate()`, step 10c (`financial_math/portfolio/engine.py`): the run's ledger, passed
  to `DailyStateBuilder(native_cash=...)` and returned on the result.
- `DailyStateBuilder` (`financial_math/portfolio/daily_state.py`): `rate_change_days()` and `value_at()` in
  `_revalue_foreign_cash()`.
- `PortfolioService` (`portfolio_service.py`): the cards and headline of `get_summary()`, the three histories, the flows
  and the «FX on cash» rows of `get_positions_contribution()`.
- AI Export: `portfolio_financial.py` and `broker_financial.py` import `CONVERSION_DUST` for `reconciled` (C-53).

## History

| Date | Change |
|------|--------|
| 2026-10-11 | Created by lot 41 step F-1 (`36b181836`): ledger, flows, missing conversions, `effective_share`. The engine reads it from step F-2 (`aa6b6077a`). |
| 2026-10-12 | `exchange_results()` and `CONVERSION_DUST` (`a5f41f60c`); the service reads cards, histories and contributions from it (`c04e44ff5`). |
| 2026-10-12 | AI Export uses `CONVERSION_DUST` for `reconciled` (C-53, `876d2b430`). |

## Source files

| Role | Path |
|------|------|
| The module | `backend/app/services/financial_math/native_cash.py` |
| Layer docstring (module map) | `backend/app/services/financial_math/__init__.py` |
| Engine caller (step 10c) | `backend/app/services/financial_math/portfolio/engine.py` |
| Builder caller (`_revalue_foreign_cash`) | `backend/app/services/financial_math/portfolio/daily_state.py` |
| Service caller | `backend/app/services/portfolio_service.py` |
| AI Export callers (`reconciled`) | `backend/app/services/ai_export/components/portfolio_financial.py`, `backend/app/services/ai_export/components/broker_financial.py` |
| Unit tests | `backend/test_scripts/test_services/test_financial_math/test_native_cash.py` |
| Test helper for builder constructions | `backend/test_scripts/test_services/_engine_native_cash.py` |
| Developer docs | `mkdocs_src/docs/developer/backend/transactions/wac.md` |
| Layer rules | `.github/instructions/financial-math.instructions.md` |

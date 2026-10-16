---
title: "Days that only move an exchange rate, or a price's source or age, were skipped: fixed (cash in lot 41, the rest in CP-6)"
category: problem
status: resolved
date: 2026-10-12
updated: 2026-10-16
tags: [backend, portfolio-engine, fx, dirty-days, valuation, broker-cards, native-cash, lot-41, backlog, price-marks, stale-price, release-1.3]
related:
  - problems/foreign-cash-never-revalued
  - decisions/native-cash-daily-revaluation
  - entities/portfolio-engine
  - concepts/pre-frame-frame-separation
  - decisions/portfolio-pnl-series-contracts
  - decisions/broker-card-aggregation-no-n-plus-one
  - sources/phase00-broker-pnl-flows-2026-10
---

# Problem: days that only move an exchange rate are skipped

## Symptom

On a day when nothing happens but an exchange rate — no transaction, no flow, no price change — positions quoted in a
foreign currency and the cash in transit kept the previous day's value. Found by the test-author on case 3 of lot 41
(day d2, 2026-10-10): P at d2 was a copy of d1. Pre-existing (backlog B11).

## Root Cause

The frame re-values only "dirty" days, to avoid recomputing identical days. `DailyStateBuilder` collects them from the
cash deltas, the position transactions, the external flows, the internal transfer flows, the in-transit edges, the
price changes and the splits — but not from the dates of the exchange rates.

## Status

- **Cash: fixed** by lot 41 part F (`aa6b6077a`, 2026-10-11). Every day on which the rate of a currency held as cash
  changes (`NativeCash.rate_change_days()`) is a dirty day in the frame, and is replayed in the pre-frame, so foreign
  cash and cash in transit follow the rate. In case 3, P_A at d2 is now +10, as the lot's table expected.
- **Securities: fixed** by workstream J, lot CP-6 (release 1.3, 2026-10-16), under developer decision 28: «recompute
  whenever a term of the formula changes». Three more reasons make a day dirty:
  - a rate the day reads to value it changes from the day before: the exact-day rate of `fx_rate_map` for every
    non-report currency of prices and assets (securities held and in transit, the exchange part of the unrealized
    split), and the departure currency of cash in transit on the days of its transit (a rate that appears or
    disappears counts);
  - every day with a market quote, not only when the close changes: a BUY the day before may have set the mark at the
    trade price, and a quote equal to the previous close then changes the mark's source (trade → market) and restarts
    its age;
  - the first day a carried price turns stale: each observation day + `STALE_PRICE_THRESHOLD_DAYS` + 1 — with nothing
    else happening, a price only ages.
- **One home for «the day a rate changes»**: `native_cash.change_days(read, currencies, days)`. The caller chooses the
  reading and the calendar: the native cash reads the last rate known (on the calendar of its rate points, results
  unchanged), the engine the exact day's rate (every frame day).
- **What it fixed**: before, such a day copied the last dirty day — daily states, broker lines, the series derived from
  them, and the summary at `date_to` (it reads the last daily state for NAV, P&L and returns; only the end positions
  were valued afresh). So a broker card and the last point of its line could differ
  ([[decisions/broker-card-aggregation-no-n-plus-one]]). The report-currency golden changed only in its window W1
  (the EUR/IDR rates of days 4, 18 and 22), W2 stayed identical.

## Prevention

When adding an input that can change a day's value — a rate, a price, a mark's source, an age — add its dates to the
dirty days, or prove the day cannot change. The pre-frame/frame split depends on this list being complete
([[concepts/pre-frame-frame-separation]]). A test that books a security bought in a foreign currency does not prove the
securities rule: the purchase's cash leg makes the native cash hold that currency, and its rate days are dirty anyway
(found by J's test-author): buy in the report currency.

## Source files

| Role | Path |
|------|------|
| Dirty days and rate-change days | `backend/app/services/financial_math/portfolio/daily_state.py` |
| `rate_change_days()` and `change_days()` | `backend/app/services/financial_math/native_cash.py` |
| The securities' rate days, quote days, first stale days (CP-6) | `backend/app/services/financial_math/portfolio/daily_state.py` (`_valuation_rate_change_days`) |
| CP-6 tests (R1–R7, guards, `change_days`) | `backend/test_scripts/test_services/test_financial/test_portfolio_engine/test_fx_only_days.py` |
| The report-currency golden (W1 regenerated in CP-6) | `backend/test_scripts/fixtures/native_cash_guard/eur_only_golden.json` |
| Plan of CP-6 | `LibreFolio_developer_journal/Release_2/Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md` |
| Case 3 (d2) and the internal-flow cases | `backend/test_scripts/test_services/test_financial/test_portfolio_engine/test_broker_internal_flows.py` |
| Revaluation scenarios | `backend/test_scripts/test_services/test_financial/test_portfolio_engine/test_foreign_cash_revaluation.py` |
| Backlog row B11 | `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` |
| Plan (§14 B11, §15 F-2, §17.6) | `LibreFolio_developer_journal/Release_2/Phase_0/41_brokerPnlFlows/plan-phase00BrokerPnlFlows.prompt.md` |

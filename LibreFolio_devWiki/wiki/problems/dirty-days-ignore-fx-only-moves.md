---
title: "Days that only move an exchange rate are skipped: the cash half fixed, the securities half open"
category: problem
status: open
date: 2026-10-12
tags: [backend, portfolio-engine, fx, dirty-days, valuation, broker-cards, native-cash, lot-41, backlog]
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
- **Securities: open.** A day on which only the rate of a currency held as a *security* moves is still skipped. The
  fix changes NAV and the broker lines even for portfolios whose cash is all in the report currency, so the lot's
  report-currency guard (its golden) would have to be regenerated: a decision first. Backlog section I, B11 (about
  half a day), destined for T-U1 or T-U5.
- **Visible consequence today**: a broker card and the last point of its broker line can differ when the valuation
  date is a non-dirty day on which only a security's rate moved — the card values its holdings at that date, the line
  keeps the last dirty day ([[decisions/broker-card-aggregation-no-n-plus-one]]). The rejected design for the card in
  step H (rebuild its NAV from the engine's contribution) would have inherited the same lag.

## Prevention

When adding an input that can change a day's value, add its dates to the dirty days — or prove the day cannot change.
The pre-frame/frame split depends on this list being complete ([[concepts/pre-frame-frame-separation]]).

## Source files

| Role | Path |
|------|------|
| Dirty days and rate-change days | `backend/app/services/financial_math/portfolio/daily_state.py` |
| `rate_change_days()` | `backend/app/services/financial_math/native_cash.py` |
| Case 3 (d2) and the internal-flow cases | `backend/test_scripts/test_services/test_financial/test_portfolio_engine/test_broker_internal_flows.py` |
| Revaluation scenarios | `backend/test_scripts/test_services/test_financial/test_portfolio_engine/test_foreign_cash_revaluation.py` |
| Backlog row B11 | `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` |
| Plan (§14 B11, §15 F-2, §17.6) | `LibreFolio_developer_journal/Release_2/Phase_0/41_brokerPnlFlows/plan-phase00BrokerPnlFlows.prompt.md` |

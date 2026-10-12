---
title: "Foreign cash was never revalued: its exchange result missed NAV and P&L, and the headline cash disagreed with the cards"
category: problem
status: resolved
date: 2026-10-12
tags: [backend, portfolio-engine, cash, fx, native-cash, nav, pnl, k-r-w-pools, dashboard, broker-cards, lot-41]
related:
  - decisions/native-cash-daily-revaluation
  - entities/native-cash
  - problems/dirty-days-ignore-fx-only-moves
  - concepts/3-pool-cash-model
  - entities/portfolio-engine
  - decisions/portfolio-pnl-series-contracts
  - decisions/broker-card-aggregation-no-n-plus-one
  - sources/phase00-broker-pnl-flows-2026-10
---

# Problem: foreign cash was never revalued

## Symptom

Cash held in a currency other than the report currency kept the value it had on the day each movement was booked.
Two examples from the lot 41 analysis (plan 41 §17.3), with a EUR report currency:

| Case | Before the fix | After the fix |
|------|----------------|---------------|
| 1 000 USD deposited at 0.90 (capital 900), then moved A → B the same day at 0.95 | A keeps a cash of −50 for ever, P_A = 0; B 950, P_B = 0; total P = 0 | A 0, P_A = +50; B 950, P_B = 0; P = +50, the real exchange gain |
| 1 000 USD deposited at 0.90, then a BUY of 1 000 USD at 0.95 | a ghost cash of −50 for ever while the native balance is 0; P = MV − 950 | cash 0; P = MV − 900 |

The broker cards, fixed just before by step H of the same lot, valued each native balance at the valuation date,
while the headline cash came from the engine: on the mock database the two differed by up to **866.5**. The test
written for it (T1c) saw a headline of 825 / 25 / 350 against cards of 950 / 150 / 475 on the same day.

## Root Cause

The engine's cash ledger (step 1 of `DailyStateBuilder`, at the time in `portfolio_engine.py`) added every movement at the rate
of its own date and never looked at the balance again. The exchange result on cash therefore never reached NAV or P&L
— not while the currency sat in the account, not when it was spent on a BUY, not when it was converted back with an
FX_CONVERSION. Cash in transit, on the other hand, was valued at the day's rate, so the same dollars changed rules on
the way between two brokers. Found by lot 41's inventory on 2026-10-10 (backlog B4); the behaviour predates the lot.

## Solution

Lot 41, part F ([[decisions/native-cash-daily-revaluation]]): one native-cash ledger per broker and currency
([[entities/native-cash]]); on every rate-change day the engine revalues foreign cash and books the difference to the
broker's returns pool (a loss larger than the returns comes out of capital); the service reads the cards, the headline
and the period flows from the same ledger, so the headline cash equals the sum of the cards. Commits `36b181836`
(module), `aa6b6077a` (engine), `c04e44ff5` (service); train 42.

## Prevention

- `test_foreign_cash_revaluation.py` pins the scenarios B1–B12, B3w and B4v, and checks the G1a identity (Σ broker
  P&L = total) on every day of every run.
- `test_summary_with_breakdown_foreign_cash_in_transit_headline_equals_sum_of_cards` (T1c) asserts the headline equals
  the sum of the cards with foreign cash in transit.
- The report-currency guard keeps portfolios without foreign cash byte-identical, so a later change of the cash rules
  shows up only where it should.

## Impact

Every portfolio holding cash in another currency had a wrong NAV, P&L and K/R split from the first rate move after a
foreign deposit. On the mock database the admin user's one-year period P&L moved by 472.16 with the fix — the sum of
its five «FX on cash» rows. Nothing was lost: no stored value changed, only what the engine computed.

## Source files

| Role | Path |
|------|------|
| The ledger | `backend/app/services/financial_math/native_cash.py` |
| Revaluation in the replay | `backend/app/services/financial_math/portfolio/daily_state.py` |
| Cards and headline | `backend/app/services/portfolio_service.py` |
| Scenario tests | `backend/test_scripts/test_services/test_financial/test_portfolio_engine/test_foreign_cash_revaluation.py` |
| Headline = Σ cards (T1c) | `backend/test_scripts/test_services/test_financial/test_portfolio_service.py` |
| Plan (§14 B4, §17.3) | `LibreFolio_developer_journal/Release_2/Phase_0/41_brokerPnlFlows/plan-phase00BrokerPnlFlows.prompt.md` |

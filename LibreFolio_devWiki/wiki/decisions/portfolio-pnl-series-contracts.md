---
title: "Portfolio P&L series: additive broker lines from one replay, candles composed per day, income from the ledger"
category: decision
status: resolved
date: 2026-09-22
updated: 2026-10-12
tags: [backend, frontend, portfolio-engine, dashboard, charts, pnl, candles, income, financial-math, invariant, internal-transfers, broker-cards]
related: [features/F-055, entities/portfolio-engine, concepts/3-pool-cash-model, concepts/portfolio-report-unified, concepts/chart-resolution-semantic-zoom, decisions/financial-math-single-average-cost, concepts/echarts-chart-gotchas, sources/phase00-performance-charts-2026-09, decisions/broker-card-aggregation-no-n-plus-one, decisions/native-cash-daily-revaluation, problems/dirty-days-ignore-fx-only-moves, sources/phase00-broker-pnl-flows-2026-10]
---

# Decision: how the Dashboard's new P&L series are computed

## Context

Workstream I (Release 2, SP07 G1a/G1b and SP06 G1c) added three series to the Growth chart: a cumulative P&L line
**per broker**, synthetic **P&L candles** for the whole portfolio, and a signed **income** history. Each had an
obvious implementation that gives a wrong answer.

## Decisions

### G1a — broker lines are additive contributions of one combined replay

- **Chosen**: one daily replay over the combined scope; each day `DailyPortfolioState.broker_contributions` splits
  the day's P&L by broker from the same Decimal components, and the identity
  **Σ broker P&L == total P&L** holds exactly, every day (`build_broker_pnl_history()`,
  `backend/app/services/financial_math/portfolio/derived_views.py` since 2026-10-12; before, `portfolio_engine.py`).
- **Rejected**: one engine run per broker. A sub-scope turns every internal transfer between the user's brokers
  into an external deposit or withdrawal, so the per-broker lines would not sum to the total.
- **Internal transfers are zero-sum capital flows between broker lines** (lot 41, 2026-10). On the arrival day
  (the later leg date), a `linked_internal` TRANSFER / CASH_TRANSFER / FX_CONVERSION pair between two brokers
  adds X to the receiver's capital and removes the same Decimal X from the sender's
  (`_internal_transfer_flows()`). X is what enters the receiver's NAV that day: cash at the arrival FX rate,
  securities at arrival market value with the NAV's own valuation, both at the sender's ownership share.
  The portfolio capital never moves, so total P&L, ROI/TWRR/MWRR, candles and cash stay byte-identical.
- **Rejected**: no flow (each line jumped by −X/+X at arrival while the total stayed right); securities at
  cost (a jump equal to the lot's unrealized gain would remain).
- Value in transit, and its price move, stay with the sender until arrival; no flow during the trip.
- A missing price at arrival gives X = 0, which is what enters the receiver's NAV; the value appears with the
  first price, on the broker that holds it.
- Different ownership shares leave (s_B − s_A)·X on the receiver's line; the total is unaffected.
- Filtered views: a securities TRANSFER leg whose partner is outside the view, or whose partner was deleted,
  is capital at market value on its own date (`_transfer_leg_capital()`); a cash leg in the same position is
  capital at its amount. B alone equals B in the combined view; A alone loses the in-transit move at departure.
- ADJUSTMENT pairs keep their capital at cost and get no internal flow.
- **Broker cards read the same capital** (lot 41, step H). `PortfolioService.get_summary(include_breakdown=True)`
  no longer keeps its own per-broker capital (`broker_total_invested`: DEPOSIT/WITHDRAWAL plus in-kind
  ADJUSTMENT as override × quantity, transfers ignored). Each card takes `capital_contribution` and
  `in_transit_contribution` from the engine's `BrokerDailyContribution` at the valuation date. Market value
  (holdings rows at the valuation date, dust excluded) and cash stay the service's own — the cash, since lot 41 F,
  from the native-cash ledger at the valuation date. NAV = MV + cash + in transit; gain = NAV − capital; percent
  only when capital > 0.
- **Rejected**: card NAV = `nav_contribution` − engine cash + cash at T. The engine re-values a day only when
  it is dirty, so on a last day where only FX moved its market value would lag the holdings rows.
- A card and the last point of its broker line can still differ by dust and by a move of a security's exchange rate
  on a non-dirty last day ([[problems/dirty-days-ignore-fx-only-moves]], B11). The value in transit comes from the
  engine, so on such a day it lags on both. The third difference the lot listed, the foreign-cash drift (B4), was
  closed on 2026-10-12 by part F: cash is now revalued every day ([[decisions/native-cash-daily-revaluation]]).
- Requested only when the effective scope has two or more brokers (`include_broker_pnl_history`).

### G1b — a portfolio candle is composed per day, then bucketed

- **Chosen**: for each day, compose the portfolio's open/high/low/close P&L from every holding's intraday data;
  then roll days into weeks/months (open = first, high = max, low = min, close = last). `close` reproduces the
  day's canonical `total_pnl` exactly (`build_pnl_candles()`).
- **Rejected**: summing daily candles, and bucketing each asset to week/month before combining assets — both give
  highs and lows that never happened.
- No volume; an asset without intraday data contributes a flat candle; a day with a missing valuation is a gap,
  never a guessed candle; a real short position makes the series unavailable (fail closed).
- Display-only: never fed to Risk or AI Export. Lazy (`include_pnl_candles`): requested on the first switch to the
  candle sub-mode, because it is the expensive one.

### G1c — income comes from the user's ledger, signed

- **Chosen**: personal DIVIDEND/INTEREST **transactions** (asset-linked and broker-level), with their sign; buckets
  are sums over `(date_from, date_to]`, and their total equals the period's signed income.
- **Rejected**: global `AssetEvent` rows — they describe the instrument, not what this user received.
- Eager (`include_income_history`): sparse and cheap. Later batches added cost (FEE+TAX), deposit and
  new-vs-reinvested funding histories under the same eager policy.

### Shared rules

- Every optional flag enters the backend L2 cache key, the frontend cache key and `included_features`; the
  frontend passes them as a typed options object, not positional booleans.
- Bucket labels follow the calendar (commit `8c7b0c0a7`, "P&L periods follow the calendar"), superseding the
  first end-anchored buckets (Round 4, D16).

## Consequences

- One engine run feeds the total, the broker lines and the candles: no second replay, and the invariant is testable
  (`test_broker_pnl_contributions.py`, `test_pnl_candles.py`).
- A byte-equality guard (`test_broker_internal_flows.py`) reruns the replay with the internal flows neutralised and
  checks that every combined-view aggregate is unchanged: the flows only move capital between broker lines.
- The general rule, reusable beyond charts: **decompose additively inside one run and assert the identity, instead
  of recomputing per sub-scope; compose across assets per day, then aggregate over time — never the reverse.**

## Links

- [[features/F-055]] — the Growth chart that shows them.
- [[concepts/echarts-chart-gotchas]] — the rendering traps met on the way.
- [[decisions/broker-card-aggregation-no-n-plus-one]] — the broker cards that read the same capital since lot 41.
- [[decisions/native-cash-daily-revaluation]] — lot 41 F, the cash the lines and cards are valued with.
- Source: [[sources/phase00-performance-charts-2026-09]]; lot 41: [[sources/phase00-broker-pnl-flows-2026-10]].

## Source files

| Role | Path |
|------|------|
| Daily replay, `build_broker_pnl_history`, `build_pnl_candles` | `backend/app/services/financial_math/portfolio/daily_state.py`, `backend/app/services/financial_math/portfolio/derived_views.py` |
| `get_broker_pnl_history`, report assembly | `backend/app/services/portfolio_service.py` |
| `get_summary`, the per-broker breakdown (card capital from the engine, lot 41 H) | `backend/app/services/portfolio_service.py` |
| Report flags (`include_*`) and series schemas | `backend/app/schemas/portfolio.py` |
| Growth chart (P&L mode, sub-modes, candles, income) | `frontend/src/lib/features/dashboard/GrowthChart.svelte` |
| Growth chart P&L series (sign split, candles, reference line) | `frontend/src/lib/features/dashboard/growthChartSeries.ts` |
| Axis label planner | `frontend/src/lib/features/dashboard/growthLadderAxis.ts` |
| Engine tests (identity, candles) | `backend/test_scripts/test_services/test_financial/test_portfolio_engine/test_broker_pnl_contributions.py` |
| Candle tests | `backend/test_scripts/test_services/test_financial/test_portfolio_engine/test_pnl_candles.py` |
| Internal flows, filtered views, orphans, aggregate guard (lot 41) | `backend/test_scripts/test_services/test_financial/test_portfolio_engine/test_broker_internal_flows.py` |
| Card tests: same-day and multi-day transfer, foreign currency at the arrival rate | `backend/test_scripts/test_services/test_financial/test_portfolio_service.py` |
| Theory — internal transfers in the broker lines (`#internal-transfers-broker-lines`) | `mkdocs_src/docs/financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.en.md` |
| User doc | `mkdocs_src/docs/user/dashboard/charts.en.md` |
| Plan (§3–4) | `LibreFolio_developer_journal/Release_2/phases/20_performanceCharts/plan-phase00PerformanceCharts.prompt.md` |
| Plan of lot 41 (§1–§4, §13, §15) | `LibreFolio_developer_journal/Release_2/Phase_0/41_brokerPnlFlows/plan-phase00BrokerPnlFlows.prompt.md` |

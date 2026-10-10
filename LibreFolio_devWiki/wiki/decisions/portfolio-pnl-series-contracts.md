---
title: "Portfolio P&L series: additive broker lines from one replay, candles composed per day, income from the ledger"
category: decision
status: resolved
date: 2026-09-22
tags: [backend, frontend, portfolio-engine, dashboard, charts, pnl, candles, income, financial-math, invariant]
related: [features/F-055, entities/portfolio-engine, concepts/3-pool-cash-model, concepts/portfolio-report-unified, concepts/chart-resolution-semantic-zoom, decisions/financial-math-single-average-cost, concepts/echarts-chart-gotchas, sources/phase00-performance-charts-2026-09]
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
  `backend/app/services/portfolio_engine.py`).
- **Rejected**: one engine run per broker. A sub-scope turns every internal transfer between the user's brokers
  into an external deposit or withdrawal, so the per-broker lines would not sum to the total.
- Cash in transit stays with the departure broker until it arrives.
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
- The general rule, reusable beyond charts: **decompose additively inside one run and assert the identity, instead
  of recomputing per sub-scope; compose across assets per day, then aggregate over time — never the reverse.**

## Links

- [[features/F-055]] — the Growth chart that shows them.
- [[concepts/echarts-chart-gotchas]] — the rendering traps met on the way.
- Source: [[sources/phase00-performance-charts-2026-09]].

## Source files

| Role | Path |
|------|------|
| Daily replay, `build_broker_pnl_history`, `build_pnl_candles` | `backend/app/services/portfolio_engine.py` |
| `get_broker_pnl_history`, report assembly | `backend/app/services/portfolio_service.py` |
| Report flags (`include_*`) and series schemas | `backend/app/schemas/portfolio.py` |
| Growth chart (P&L mode, sub-modes, candles, income) | `frontend/src/lib/components/dashboard/GrowthChart.svelte` |
| Axis label planner | `frontend/src/lib/components/dashboard/growthLadderAxis.ts` |
| Engine tests (identity, candles) | `backend/test_scripts/test_services/test_financial/test_portfolio_engine/test_broker_pnl_contributions.py` |
| Candle tests | `backend/test_scripts/test_services/test_financial/test_portfolio_engine/test_pnl_candles.py` |
| User doc | `mkdocs_src/docs/user/dashboard/charts.en.md` |
| Plan (§3–4) | `LibreFolio_developer_journal/Release_2/phases/20_performanceCharts/plan-phase00PerformanceCharts.prompt.md` |

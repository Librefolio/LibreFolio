---
title: "3-Pool Cash Model"
category: concept
tags: [backend, portfolio, cash, decomposition, dashboard, growthchart, accounting, capital]
related:
  - entities/portfolio-engine
  - entities/portfolio-service
  - concepts/portfolio-report-unified
  - features/F-054
---

# Concept: 3-Pool Cash Model

## Definition

The 3-pool cash model decomposes the portfolio's cash position into three semantically distinct "pools" that track where money came from and where it is going. This decomposition powers the GrowthChart stacked-area visualization on the Dashboard, which shows three distinct lines: NAV / invested capital / cash.

The model is implemented in `DailyStateBuilder` as an event-driven state machine that updates on every transaction.

## The Three Pools

| Pool | Description | Increases on | Decreases on |
|------|-------------|-------------|-------------|
| **Deposited capital** | Total net external contributions | DEPOSIT | WITHDRAWAL |
| **Invested capital** | Cash deployed into assets | BUY | SELL (proceeds return to realized pool) |
| **Realized cash** | Proceeds from SELLs + income (dividends, interest) | SELL, DIVIDEND, INTEREST | Used for next BUY |

```
Deposited capital
    ↓ BUY
Invested capital (cost basis of open positions)
    ↓ SELL
Realized cash (proceeds available for next trade)
    ↓ BUY
Invested capital again...
```

NAV = market_value (open positions at current price) + cash + in_transit

## Where It Applies

- `DailyStateBuilder` in `portfolio_engine.py` — updates all 3 pools per day
- GrowthChart frontend: 3 series displayed as stacked area chart
  - Series 1 (dark line): NAV
  - Series 2 (dashed): Deposited capital (capital baseline)
  - Series 3 (dotted): Realized cash balance

## Important Caveat

> The 3-pool decomposition is a **visualization approximation**, not an exact accounting model. The chart's `capital_baseline` line vs NAV gap is intuitive but does NOT equal realized P&L exactly. The authoritative P&L numbers are in the KPI cards (which use per-sell WAC calculation in `get_summary()`).

This distinction exists because the engine's `open_cost_basis` uses `wac_series` (pre-loaded with forward-fill), while the service's realized P&L uses `compute_wac_iterative(excluded_tx_ids=[current_sell])`. For standard reduce SELLs, the difference is zero; it may appear for edge cases involving pool resets.

## Source files

| Role | Path |
|------|------|
| Engine implementation | `backend/app/services/portfolio_engine.py` |
| DailyStateBuilder | (within portfolio_engine.py) |
| Math spec | `LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/Milestone_2/portfolio_engine/portfolio_engine_architecture_v2.md` |
| GrowthChart component | `frontend/src/lib/components/charts/GrowthChart.svelte` |
| Dashboard page | `frontend/src/routes/(app)/dashboard/+page.svelte` |

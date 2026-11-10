---
title: "Backend-Only Calculations Rule"
category: concept
tags: [architecture, backend, frontend, calculations]
related_features: [F-056, F-057, F-058]
related: [decisions/financial-math-one-home, decisions/signal-backend-plugin-architecture]
---

# Concept: Backend-Only Calculations

## Definition
All financial calculations in LibreFolio are performed exclusively in the backend. The frontend is pure presentation — it receives pre-computed results via API.

## Scope
- FIFO cost basis ([[F-056]])
- Currency conversion ([[F-057]])
- ROI, DW-ROI ([[F-058]])
- Portfolio valuation, totals, gain/loss
- Any aggregate across multiple assets or time periods
- Allocation plans of the PAC allocator Tool ([[features/F-107]]): the backend searches (SCIP) and an exact Decimal replay referees every
  number; booked amounts round against the plan ([[decisions/pac-rounding-against-the-plan]]). Every Tool computes
  on the backend, in a process of its own, from an explicit scenario ([[features/F-106]],
  [[decisions/tool-calculation-without-authority]])

**Exception**: the Signal Library ([[F-037]]) computes technical indicators (EMA, RSI, MACD) in the frontend on raw price series received from the API. This is intentional — signals are display-layer transformations, not financial calculations affecting stored data.

> *2026-11-07 lint:* this exception is superseded. Since the signal platform ([[decisions/signal-backend-plugin-architecture]],
> 2026-07-23) indicators are computed by backend `SignalPlugin`s (`backend/app/services/signal_plugins/`); the frontend
> keeps only comparison signals, synthetic benchmarks and Measure. The rule itself was then amended twice: every
> financial calculation has one home, `backend/app/services/financial_math/` ([[decisions/financial-math-one-home]],
> rule 6: «interactive measures are the declared exception»), and small sums or multiplications (a form convenience, a
> chart adapter) may live in the frontend in one shared helper (developer decision 25/10/2026, `CLAUDE.md` «Key
> Architectural Decisions» 1).

## Why
- Single source of truth — no risk of frontend and backend computing different numbers
- Auditable and testable in isolation
- Simplifies frontend — no financial logic to maintain or sync
- Backend can optimize queries (e.g. batch FIFO over multiple assets)

## Source
`LibreFolio_developer_journal/knowledge_base/00_project_overview.md` — "Calcoli solo nel Backend"

## Source files

| Role | Path |
|------|------|
| Financial math — the one home (FIFO, average cost, returns, portfolio engine) | `backend/app/services/financial_math/` |
| Transaction service | `backend/app/services/transactions/transaction_service.py` |
| Backend signal plugins | `backend/app/services/signal_plugins/` |
| Asset service (sync, caching) | `backend/app/services/assets/` |
| FX service (conversion graph) | `backend/app/services/fx/conversion.py` |
| API schemas | `backend/app/schemas/` |

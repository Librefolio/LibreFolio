---
title: "Backend-Only Calculations Rule"
category: concept
tags: [architecture, backend, frontend, calculations]
related_features: [F-056, F-057, F-058]
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

**Exception**: the Signal Library ([[F-037]]) computes technical indicators (EMA, RSI, MACD) in the frontend on raw price series received from the API. This is intentional — signals are display-layer transformations, not financial calculations affecting stored data.

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
| Transaction service (FIFO, ROI) | `backend/app/services/transaction_service.py` |
| Asset service (sync, caching) | `backend/app/services/asset_source.py` |
| FX service (conversion graph) | `backend/app/services/fx.py` |
| API schemas | `backend/app/schemas/` |

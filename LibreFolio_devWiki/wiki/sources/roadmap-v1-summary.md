---
title: "RoadMap V1 — Original Backend-Only Architecture"
category: source
date: 2024 (pre-frontend era)
tags: [history, backend, v1, superseded]
related_features: [F-056, F-030, F-034, F-059]
---

# Source: RoadMap V1 — Original Backend-Only Architecture

**Source file**: `LibreFolio_developer_journal/RoadMapV1/01-Riassunto_generale.md`
**Era**: Pre-frontend (backend only, React was the planned but never built frontend)

## What RoadMap V1 was

The original project specification before any frontend existed. At this stage the plan assumed:
- **Backend**: Python FastAPI + SQLModel + SQLite + Alembic
- **Frontend**: React + TypeScript + Vite + Material UI + React Query + i18next ← **never built; replaced by SvelteKit**
- **Scheduling**: APScheduler (still used today as [[F-052]] planned)
- **Scraping**: httpx + BeautifulSoup4 (still used in CSS Scraper [[F-035]])
- **FX**: forex-python or ECB feed (evolved into full multi-provider registry [[F-015]])

## Key concepts that survived to v4

| V1 concept | Current implementation |
|------------|----------------------|
| "Un solo record al giorno" (one record per day) | [[concepts/daily-point-policy]] |
| Asset plugin for current + historical value | [[F-025]] Asset Provider Registry |
| Scheduled-yield loan valuation model | [[F-034]] Scheduled Investment Provider |
| FIFO cost basis calculation | [[F-056]] FIFO at Runtime |
| Single Docker container | [[F-062]] Docker Single-Image Deploy |

## Key concepts that were REDESIGNED

| V1 design | Why changed | Current design |
|-----------|------------|---------------|
| React + MUI frontend | Replaced by SvelteKit 2 + Svelte 5 + Tailwind (lighter, more modern) | [[F-008]], [[F-066]] |
| `cash_movements` table for cash tracking | Merged into `transactions` table with typed `TransactionType` enum | [[F-046]] |
| Per-asset plugin pair (current + historical separate) | Unified into single `AssetSourceProvider` with `get_current_value()` + `get_history_value()` | [[F-025]] |
| `forex-python` library for FX | Replaced by multi-provider central bank registry (ECB/FED/BOE/SNB) | [[F-015]] |

## Historical value

This document marks the **moment the project was scoped**. The core financial logic (FIFO, daily-point policy, scheduled yield) was defined here and has remained stable. The technology choices (especially the frontend) were revised substantially in V2/V3/V4 as the project grew.

> Populated 2026-04-24. Original file is in Italian; key decisions extracted and cross-referenced above.

## Source files

| Role | Path |
|------|------|
| Original RoadMap V1 | `LibreFolio_developer_journal/RoadMapV1/01-Riassunto_generale.md` |
| Transaction service (FIFO — carried forward) | `backend/app/services/transaction_service.py` |
| Scheduled Investment provider | `backend/app/services/asset_source_providers/scheduled_investment.py` |
| CSS Scraper provider | `backend/app/services/asset_source_providers/css_scraper.py` |

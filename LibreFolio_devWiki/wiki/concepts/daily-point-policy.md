---
title: "Daily-Point Policy"
category: concept
tags: [backend, db, prices, fx, data-model]
related_features: [F-030, F-017]
---

# Concept: Daily-Point Policy

## Definition
LibreFolio stores **exactly one data record per day** per asset (price history) and per currency pair (FX rates). Intraday updates overwrite (upsert) the current day's record — there is no sub-daily granularity.

## Where it applies
- `PriceHistory` table: one row per `(asset_id, date)`
- `FxRate` table: one row per `(base, quote, date)`

## Design rationale
- **Simplicity**: portfolio performance is inherently daily (end-of-day NAV)
- **Storage efficiency**: one row per day vs. tick data is orders of magnitude smaller
- **Idempotency**: sync jobs can re-run without creating duplicates (upsert semantics)
- **Consistency**: all calculations use closing-price semantics

## Consequences
- Intraday price changes are not captured (live ticker [[F-047]] is ephemeral — not stored)
- Historical backfill jobs are idempotent — safe to re-run
- FIFO ([[F-056]]) works with daily closing prices, not exact execution times

## Source
`LibreFolio_developer_journal/RoadMapV1/01-Riassunto_generale.md` — "Dati giornalieri" section

## Source files

| Role | Path |
|------|------|
| DB model (PriceHistory, FxRate) | `backend/app/db/models.py` |
| Asset API (price history) | `backend/app/api/v1/assets.py` |
| FX API (rate history) | `backend/app/api/v1/fx.py` |

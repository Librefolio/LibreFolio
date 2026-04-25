---
title: "Asset price currency mismatch — per-row currency column"
category: problem
status: resolved
date: 2026-04-01
tags: [backend, db, assets, prices, currency, fx]
related: [entities/db-models, concepts/daily-point-policy, decisions/price-currency-hard-reject, decisions/policy-d-currency-wipe]
---

# Problem: Asset Price Currency Mismatch

> **Superseded-in-spirit (2026-04-21 → 2026-04-23)**: the per-row
> `PriceHistory.currency` column is still present (forensic canary), but the
> *runtime contract* it once enabled — accepting mismatched-currency rows and
> FX-converting at read time — has been replaced by **stricter rules**:
>
> - **API in**: hard-400 on any price-currency mismatch in `upsert_prices_bulk`
>   (see [[decisions/price-currency-hard-reject]] — Blocco I.2).
> - **API out**: `FAPricePoint` no longer exposes `currency`; frontend trusts
>   `asset.currency` as the single source of truth (I.8).
> - **Currency change**: HTTP 409 if prices exist; Policy D destructive wipe
>   on user confirm (see [[decisions/policy-d-currency-wipe]]).
>
> The page below documents the original 2026-04-01 design rationale for the
> per-row column, which is still factually accurate at the DB layer.

## Symptom
When displaying asset prices, the currency of a fetched price can differ from the currency declared on the `Asset` record. For example, a European ETF might declare `EUR` as its currency, but the yfinance provider returns prices in `USD` for the US-listed share class. Assuming `PriceHistory` prices are always in `Asset.currency` leads to silent mis-valuation.

## Root Cause
Providers fetch data in whatever currency their data source provides. This may not match `Asset.currency`. If the system assumes all prices are in the asset's declared currency, it silently skips FX conversion — producing wrong portfolio values without any error signal.

## Solution
**`PriceHistory.currency` column per price row** — each row stores the actual currency the provider returned, regardless of `Asset.currency`.

Design decisions:
- `PriceHistory.currency: str` (ISO 4217) — stored per row, not inherited from asset
- `Asset.currency` is the **display/reference** currency for the asset
- `PriceHistory.currency` is the **source** currency of that specific price observation
- When displaying prices in a different currency (Part C of Phase 6), the backend converts at query time using the FX graph
- There is **no `base_currency_price` column** — the `currency` field on each row serves this purpose

## Prevention
- Always set `PriceHistory.currency` from the provider's response, never from `Asset.currency`
- When querying prices for portfolio calculations, check if `price.currency != asset.currency` and apply FX conversion
- The `source_plugin_key` column on `PriceHistory` records which provider wrote the row (audit trail)

## Impact
Without this design, portfolio totals could be silently calculated in mixed currencies — a critical financial bug. The per-row currency column eliminates the assumption.

## Source files

| Role | Path |
|------|------|
| PriceHistory model | `backend/app/db/models.py` |
| Asset model | `backend/app/db/models.py` |
| FX conversion service | `backend/app/services/fx.py` |

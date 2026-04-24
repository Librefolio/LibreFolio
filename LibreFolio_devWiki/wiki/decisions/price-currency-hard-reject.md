---
title: "Price Currency: Hard-Reject Mismatch + 409 on Asset Currency Change"
date: 2026-04-21
status: resolved
tags: [prices, currency, assets, api, validation]
related_features: [F-030, F-024]
related_sources: [sources/phase07-part3-api-consolidation, sources/phase07-part3-closure]
---

# Decision: Price Currency Hard-Reject + Asset Currency Change 409

## Context

Phase 07 Blocco E (from Part 1) had planned a soft-skip approach for currency
mismatches in price uploads: mismatched rows would be skipped silently with errors
collected in the response. Blocco I (Phase 07 Part 3, during checklist review)
invalidated this design.

## Decisions

### 1. Hard 400 on Currency Mismatch in `upsert_prices_bulk`

**Old design (Blocco E.3)**: per-item skip on currency mismatch, collected in `errors[]`.

**New design (Blocco I.2)**: **HTTP 400** on any currency mismatch. The entire batch
is rejected with a structured error:
```json
{
  "detail": "...",
  "asset_currency": "USD",
  "offending_dates": ["2024-01-15", "2024-02-01"]
}
```

**Rationale**: With the DataEditor UI, the currency column was removed (I.8 — frontend
uses `asset.currency` as single source of truth). Mismatches can only arrive from:
- Malformed CSV import
- Raw API calls with wrong data

In both cases, failing loudly is better than silently skipping rows.

### 2. HTTP 409 on Asset Currency Change with Existing Prices

`PATCH /assets/{id}` with a `currency` change when `price_history` rows exist → **HTTP 409**:
```json
{
  "detail": "Cannot change currency while price history exists",
  "existing_count": 1247,
  "oldest_date": "2020-01-02",
  "newest_date": "2024-04-20"
}
```

**User must**: DELETE all prices first (via bulk delete or DataEditor clear), then PATCH currency.

**No auto-conversion** (bulk-convert option was rejected):
- Would introduce FX rate dependency at asset update time
- Risk of compounding rounding errors
- Violates the principle that price data should come from providers, not be transformed

**No soft rename**: currency is a structural field tied to the meaning of every price point.
A "same currency, different code" scenario doesn't exist in practice (e.g., EUR is EUR).

### 3. `price_history.currency` Kept in DB, Removed from API

The column stays in the database as a **forensic canary** (3 bytes/row):
- Useful for SQL debugging: `SELECT * FROM price_history WHERE currency != asset.currency`
- Detects data corruption from external tools or direct SQL manipulation

The column is **removed from `FAPricePoint` API response**. Frontend uses `asset.currency`
as the single source of truth — no lookup per price point needed.

### 4. Asset Events Currency is Free

`asset_events.currency` remains unconstrained. An ADR (American Depositary Receipt)
representing a US stock may pay dividends in EUR, JPY, or GBP depending on the payer's
domicile. This is a real-world scenario that cannot be restricted.

This is an intentional asymmetry with `price_history.currency`.

### 5. Cancelled Items from Blocco E

| Item | Reason |
|------|--------|
| `fx_error` discriminator | `requiredFxPairs` system already handles 4 states |
| `currency_breakdown` in response | Redundant after I.2 (all prices must be same currency) |
| FX auto-registration | Violates self-hosted explicit control principle |
| `PriceCurrencyMismatchBanner` | Not reachable via normal UI after I.2 |

## Source files

| Role | Path |
|------|------|
| Asset source (upsert_prices_bulk) | `backend/app/services/asset_source.py` |
| Asset API (currency change 409) | `backend/app/api/v1/assets.py` |
| DB model (price_history.currency) | `backend/app/db/models.py` |
| Asset detail page (requiredFxPairs) | `frontend/src/routes/(app)/assets/[id]/+page.svelte` |
| Asset currency change modal | `frontend/src/lib/components/assets/AssetCurrencyChangeModal.svelte` |
| Test (mismatch hard 400) | `backend/test_scripts/test_services/test_prices_currency_coherence.py` |
| Test (currency change 409) | `backend/test_scripts/test_api/test_asset_currency_change.py` |

---
title: "Backup Router (`/api/v1/backup`)"
category: entity
type: api
tags: [backend, api, backup, export, csv, json, policy-d, fx]
related:
  - decisions/policy-d-currency-wipe
  - decisions/price-currency-hard-reject
  - sources/phase07-part3-closure
  - sources/phase07-part3-closure2
  - entities/api-router
  - features/F-073
---

# Backup Router

## Role

Read-only router that exports any time-series resource the user might want to
snapshot **before** running a destructive operation (Policy D currency wipe,
provider param change, manual delete, etc.). Designed as a generic
"dump-this-table-as-CSV-or-JSON" surface, not a transactional backup tool.

Introduced 2026-04-23 (commit `8fc018ab`) to support the
[[decisions/policy-d-currency-wipe]] flow end-to-end. Replaces an earlier
ad-hoc `GET /assets/{id}/prices/export` endpoint that lived directly on the
assets router. This router is the per-series implementation of
[[features/F-073]] (Backup & Restore); F-073 also covers the still-placeholder
full-portfolio export/restore endpoints.

## Location

`backend/app/api/v1/backup.py` — mounted under `/api/v1/backup` by the main
v1 router (see [[entities/api-router]]).

## Key Endpoints

| Method | Path | Purpose | Format |
|--------|------|---------|--------|
| GET | `/backup/asset/{asset_id}/prices` | Full price history (replaces legacy `/assets/{id}/prices/export`) | `?format=csv \| json` |
| GET | `/backup/asset/{asset_id}/events` | Full asset-event history with FX backfill columns | `?format=csv \| json` |
| GET | `/backup/fx/{base}/{quote}/rates` | FX pair rates (respects normalised pair direction) | `?format=csv \| json` |

### Asset events export columns

`date, type, source, amount, currency, fx_rate_date, fx_days_back, original_amount, original_currency, description, provider_assignment_id`

### FX rates export

The endpoint normalises the pair direction: requesting `EUR/USD` when the DB
stores `USD/EUR` returns the inverted series. Columns:
`date, rate, source_plugin_key, fetched_at`.

## Design Notes

- **Read-only**: zero side effects, never writes. Safe to call before any
  destructive action.
- **Default delimiter `;`** for CSV (with `,` accepted on import for
  legacy/round-trip compatibility — see [[concepts/savewithretry-frontend-pattern]]
  + Batch 4.e CSV auto-detect).
- **Round-trip**: `GET /backup/asset/{id}/prices?format=csv` →
  `POST /assets/{id}/prices/import-csv` works without translation. Verified
  by `test_asset_prices_export.py`.
- **No streaming yet**: responses are buffered. For very large series
  (>50k rows) this may need re-evaluation; not a current concern.
- **Auth**: all endpoints require the same READER+ access as the underlying
  resource (asset access for asset endpoints, FX is global).

## Key Interfaces

```python
@router.get("/backup/asset/{asset_id}/prices")
async def backup_asset_prices(asset_id: int, format: ExportFormat = "csv", ...) -> Response

@router.get("/backup/asset/{asset_id}/events")
async def backup_asset_events(asset_id: int, format: ExportFormat = "csv", ...) -> Response

@router.get("/backup/fx/{base}/{quote}/rates")
async def backup_fx_rates(base: str, quote: str, format: ExportFormat = "csv", ...) -> Response
```

## Frontend integration

`AssetCurrencyChangeModal` calls the two asset endpoints pre-confirm and
offers the user a download:

```ts
// frontend/src/lib/components/assets/AssetCurrencyChangeModal.svelte
const pricesBlob  = await api.get(`/backup/asset/${assetId}/prices?format=csv`);
const eventsBlob  = await api.get(`/backup/asset/${assetId}/events?format=csv`);
// User downloads, then clicks Confirm → destructive PATCH executes Policy D wipe
```

## History

- **2026-04-23** (commit `8fc018ab`): router created. Three endpoints. Legacy
  `/assets/{id}/prices/export` redirected to `/backup/asset/{id}/prices`.
- **2026-04-25** (G-batch6): full test coverage added — 8 tests in
  `test_backup_export_extras.py`. Both new endpoints went from 0% to ~95–100%
  coverage. Surfaced [[problems/assets-wipe-error-attr-mismatch]].

## Source files

| Role | Path |
|------|------|
| Router definition | `backend/app/api/v1/backup.py` |
| Mount | `backend/app/api/v1/router.py` |
| Asset events serializer | `backend/app/services/asset_source.py::query_events_bulk` |
| FX rates serializer | `backend/app/services/fx_service.py` |
| Tests | `backend/test_scripts/test_api/test_backup_export_extras.py`, `test_asset_prices_export.py` |
| Frontend consumer | `frontend/src/lib/components/assets/AssetCurrencyChangeModal.svelte` |


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
  - decisions/storage-limit-enforced
  - decisions/restore-waits-and-restores-from-kept-backup
---

# Backup Router

## Role

The `/backup` router. It was born (04/2026) as a read-only surface that exports any time-series resource the user
might want to snapshot **before** a destructive operation (Policy D currency wipe, provider param change, manual
delete…): a generic "dump-this-table-as-CSV-or-JSON" surface. Since release 1.3 the same package also carries the
backup of the whole instance and its restore (see Location); the per-series exports stay read-only.

Introduced 2026-04-24 (commit `4dc4ac8da`) to support the
[[decisions/policy-d-currency-wipe]] flow end-to-end. Replaces an earlier
ad-hoc `GET /assets/{id}/prices/export` endpoint that lived directly on the
assets router. This router is the per-series implementation of
[[features/F-073]] (Backup & Restore); F-073 also covers the backup of the whole
instance, `/backup/instance` in `instance.py` (1.3, lot B1).

## Location

`backend/app/api/v1/backup/` — a package since the 1.3 split (rule C2). `__init__.py` composes `backup_router`, mounted
under `/api/v1/backup` by the main v1 router (see [[entities/api-router]]), from five modules:

| Module | Routes | For |
|---|---|---|
| `instance.py` | `/backup/instance` — the backup of the whole instance, built in the background | administrators |
| `panel.py` | `/backup/panel/jobs` — the same jobs for a hosting panel with a token (its own tag, H-61) | a hosting panel |
| `panel_restore.py` | the hosting panel's restore (H-62) | a hosting panel |
| `restore.py` | `/backup/restore/*` — upload, check, waiting checks, restore from a kept backup, password check, confirm, restart | administrators |
| `exports.py` | the per-series exports below | readers of the resource |

`instance.py` and `panel.py` share the job views of `job_views.py`, which also refuses a manual backup past the space
limit ([[decisions/storage-limit-enforced]]). The restore flow is described in
[[decisions/restore-waits-and-restores-from-kept-backup]]; the rest of this page covers the per-series exports, the
router's first role.

## Key Endpoints

| Method | Path | Purpose | Format |
|--------|------|---------|--------|
| GET | `/backup/asset/{asset_id}/prices` | Full price history (replaces legacy `/assets/{id}/prices/export`) | `?format=csv \| json` |
| GET | `/backup/asset/{asset_id}/events` | Full asset-event history with FX backfill columns | `?format=csv \| json` |
| GET | `/backup/fx/{base}/{quote}/rates` | FX pair rates (respects normalised pair direction) | `?format=csv \| json` |

### Asset events export columns

`date, type, value, currency, source, provider_assignment_id, notes, created_at, updated_at` (`EVENT_COLUMNS` in
`backend/app/services/platform/series_export.py`; `source` is `MANUAL` without a provider assignment, else `PROVIDER`).

> 2026-11-07 lint: the column lists of this section and the next were realigned with `series_export.py` (the old list
> carried FX backfill columns the export does not write).

### FX rates export

The endpoint accepts the pair in either direction and reads the stored one (`base < quote`). The rows are never
inverted: the JSON envelope says `inverted: true` with `requested_base`/`requested_quote` so a consumer can rebuild
`1/rate`, while the CSV, with no envelope, carries the stored `base` and `quote` verbatim. Columns
(`FX_RATE_COLUMNS`): `date, base, quote, rate, source, fetched_at`.

## Design Notes

- **Read-only**: zero side effects, never writes. Safe to call before any
  destructive action.
- **Default delimiter `;`** for CSV (with `,` accepted on import for
  legacy/round-trip compatibility — see [[concepts/savewithretry-frontend-pattern]]
  + Batch 4.e CSV auto-detect).
- **Round-trip**: the CSV of `GET /backup/asset/{id}/prices?format=csv` parses back into price points that the bulk
  upsert (`POST /assets/prices`) accepts unchanged, the extra columns ignored. Verified by
  `test_export_csv_round_trip` in `test_asset_prices_export.py`. (2026-11-07 lint: an `import-csv` route was cited here;
  it never existed in the backend — `git log -S`.)
- **Streamed**: every export answers with a `StreamingResponse` (`stream_rows_as_csv` / `stream_rows_as_json`).
  (2026-11-07 lint: this bullet said «no streaming yet».)
- **Auth**: every export requires an authenticated user (`get_current_user`); there is no per-resource check.

## Key Interfaces

```python
# backend/app/api/v1/backup/exports.py — exports_router, mounted under /backup
@exports_router.get("/asset/{asset_id}/prices")
async def backup_asset_prices(asset_id: int, format: Literal["csv", "json"] = "csv", ...)  # StreamingResponse

@exports_router.get("/asset/{asset_id}/events")
async def backup_asset_events(asset_id: int, format: Literal["csv", "json"] = "csv", ...)

@exports_router.get("/fx/{base}/{quote}/rates")
async def backup_fx_rates(base: str, quote: str, format: Literal["csv", "json"] = "csv", ...)
```

## Frontend integration

`AssetCurrencyChangeModal` offers the two asset downloads before the confirm, through the shared helper
`frontend/src/lib/api/backupDownload.ts` (`downloadAssetBackup(assetId, kind, format)`; the FX page uses
`downloadFxRatesBackup(base, quote, format)`):

```ts
// frontend/src/lib/components/assets/AssetCurrencyChangeModal.svelte
await downloadAssetBackup(impact.assetId, kind, format);   // kind: 'prices' | 'events'
// User downloads, then clicks Confirm → destructive PATCH executes Policy D wipe
```

## History

- **2026-04-24** (commit `4dc4ac8da`): router created. Three endpoints. Legacy
  `/assets/{id}/prices/export` redirected to `/backup/asset/{id}/prices`.
- **2026-04-25** (G-batch6): full test coverage added — 8 tests in
  `test_backup_export_extras.py`. Both new endpoints went from 0% to ~95–100%
  coverage. Surfaced [[problems/assets-wipe-error-attr-mismatch]].

## Source files

| Role | Path |
|------|------|
| Router composition | `backend/app/api/v1/backup/__init__.py` |
| Instance backup, hosting panel jobs, shared job views | `backend/app/api/v1/backup/instance.py`, `backend/app/api/v1/backup/panel.py`, `backend/app/api/v1/backup/job_views.py` |
| Restore (administrators, hosting panel) | `backend/app/api/v1/backup/restore.py`, `backend/app/api/v1/backup/panel_restore.py` |
| Per-series export endpoints | `backend/app/api/v1/backup/exports.py` |
| Mount | `backend/app/api/v1/router.py` |
| Column schemas and CSV/JSON streaming | `backend/app/services/platform/series_export.py` |
| FX rates serializer | `backend/app/api/v1/backup/exports.py` (`backup_fx_rates`) |
| Tests | `backend/test_scripts/test_api/test_backup_export_extras.py`, `test_asset_prices_export.py` |
| Frontend consumer | `frontend/src/lib/components/assets/AssetCurrencyChangeModal.svelte`, `frontend/src/lib/api/backupDownload.ts` |


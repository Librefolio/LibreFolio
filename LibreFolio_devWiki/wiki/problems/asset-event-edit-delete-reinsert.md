---
title: "Editing an asset event deleted and re-inserted it: duplicates, a 500 from linked transactions, wrong deletes"
category: problem
status: resolved
date: 2026-10-08
tags: [backend, frontend, assets, asset-events, data-editor, upsert, foreign-key, csv]
related: [features/F-031, features/F-051, decisions/policy-d-currency-wipe, concepts/editbuffer-pattern, sources/phase00-performance-charts-2026-09]
---

# Problem: the asset-event editor edited by delete-and-reinsert

## Symptom

In the asset detail's event editor (dividends, interest, splits, price adjustments):

- **F1** — changing an event's *type* produced a second event: the old one stayed.
- **F2** — editing an event linked to a transaction (a dividend the user had booked) answered **500**.
- **S5** — a provider refresh failed on automatic events that transactions were linked to.
- **S1** — deleting a row added in the same session sent a delete for an unrelated event id.
- **S2** — importing a CSV matched rows by date only, so two events on the same day overwrote each other.
- **F3** — an exported events CSV could not be imported back: export wrote `value`, import required `amount`.

## Root cause

- F1/F2/S5: the backend upsert identified an event by its key `(date, type, provider)` and applied an edit as
  **delete + insert**. A type change is a new key, so the old row survived (F1). Deleting a row that a transaction
  references hits `transactions.asset_event_id … ON DELETE RESTRICT` (F2, S5) — the restriction that protects the
  transaction ↔ event link ([[features/F-051]]).
- S1: a row added in the editor has its date as `rowId`; `parseInt(rowId)` turned it into a bogus database id.
- S2/F3: the shared `DataEditor` import matched on the date column alone, and the events schema had no alias for
  the exported column name.

## Solution (2026-10-08, `5423c334f`)

- `FAEventUpsertPoint` carries an optional **`id`**: with an id, the stored manual event is **edited in place** —
  every field may change, date and type included, and the id is kept, so linked transactions follow; without an
  id, the event replaces the stored manual events with the same `(date, type)`, updated in place
  (`backend/app/schemas/prices.py`, `_upsert_asset_events` in `backend/app/services/asset_sources/price_store.py`).
  Historical duplicates are merged by moving their transactions to the surviving row first.
- New 400 codes from the API: `EVENT_NOT_EDITABLE` (unknown id, another asset's, or a provider event) and
  `EVENT_KEY_CONFLICT` (an edit that collides with another event's key) — `backend/app/api/v1/assets.py`.
- Frontend: `dbEventId()` returns a database id only for rows that have one; the import passes
  `importMatchKeys={['type']}` so rows match on date **and** type; the `amount` column accepts `value` as an alias
  (`AssetDataEditorSection.svelte`, `DataEditor.svelte`, `EventDataImportModal.svelte`).

## Still open (backlog 38)

- **I-09** — the event `type` is a free `str` in the schema (`FAAssetEventPoint.type`), not the enum: a lowercase
  or unknown type is written, and every later ORM read of that row fails (`LookupError` → 500). Verified at
  `586a4f0ea`.
- I-10 editor robustness (S3/S4), I-11 limits of the CSV round-trip, I-12 event delete not scoped to the asset.

## Prevention

- An edit is not a delete plus an insert when other rows point at the id: update in place and keep the id.
- A client-side row id is not a database id; keep the two apart in the type.

## Source files

| Role | Path |
|------|------|
| Upsert schema with `id`; `FAAssetEventPoint.type: str` (I-09) | `backend/app/schemas/prices.py` |
| `_upsert_asset_events` (in-place edit, duplicate merge) | `backend/app/services/asset_sources/price_store.py` |
| Events API, 400 codes | `backend/app/api/v1/assets.py` |
| Event editor section (`dbEventId`, `importMatchKeys`) | `frontend/src/lib/components/assets/AssetDataEditorSection.svelte` |
| Shared data editor (match keys) | `frontend/src/lib/components/ui/data-editor/DataEditor.svelte` |
| Events CSV import (`value` alias) | `frontend/src/lib/components/assets/EventDataImportModal.svelte` |
| API tests | `backend/test_scripts/test_api/test_assets_events.py` |
| Plan | `LibreFolio_developer_journal/Release_2/phases/20_performanceCharts/plan-phase00PerformanceChartsBugfix-AssetEvents.prompt.md` |

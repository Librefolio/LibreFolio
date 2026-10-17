---
title: "Editing an asset event deleted and re-inserted it: duplicates, a 500 from linked transactions, wrong deletes"
category: problem
status: resolved
date: 2026-10-08
tags: [backend, frontend, assets, asset-events, data-editor, upsert, foreign-key, csv]
related: [features/F-031, features/F-051, decisions/asset-event-saves-all-or-nothing, decisions/policy-d-currency-wipe, concepts/editbuffer-pattern, sources/phase00-performance-charts-2026-09]
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
  (`backend/app/schemas/assets/events.py`, `_upsert_asset_events` in `backend/app/services/assets/event_store.py`).
  Historical duplicates are merged by moving their transactions to the surviving row first.
- New 400 codes from the API: `EVENT_NOT_EDITABLE` (unknown id, another asset's, or a provider event) and
  `EVENT_KEY_CONFLICT` (an edit that collides with another event's key) — `backend/app/api/v1/assets/events.py`.
  Since release 1.3 a refusal answers `detail = {error_code, message, params}` instead of a sentence
  ([[decisions/asset-event-saves-all-or-nothing]]).
- Frontend: `dbEventId()` returns a database id only for rows that have one; the import passes
  `importMatchKeys={['type']}` so rows match on date **and** type; the `amount` column accepts `value` as an alias
  (`AssetDataEditorSection.svelte`, `DataEditor.svelte`, `EventDataImportModal.svelte`).

## What followed (backlog 38, closed in release 1.3, 15/10)

Workstream W closed the items left open here in lots E0 and E1, under decisions 20–23 of the developer
([[decisions/asset-event-saves-all-or-nothing]]):

- **I-09**, the free-text type:
  - E1a (`a2fb6936f`): `FAAssetEventPoint.normalize_type()` trims and upper-cases the type and refuses anything else
    with a 422;
  - E1c (`313dde70e`): the post-migration fix `event_types` repairs the stored rows. A correctable type is upper-cased
    in place; an unknown one is deleted after its transactions are unlinked.
- **I-10**:
  - S3 was closed without code by the coordinator: deleting a provider's event from the editor is the documented
    contract, and temporary;
  - S4 → `event_ids`: «+ New event» links the event it wrote instead of re-reading the day;
  - the deletions now go before the edits, in the same request (`delete_ids`, E1b);
  - a refusal is translated and names the row (E1b).
- **I-11**:
  - (a) and (d), E0 (`692fbae39`): CSV rows and the date picker are keyed on date **and** type;
  - (c), E1b: a row keeps its currency, and one in another currency is refused with its row;
  - (b) stays open as W-B16.
- **I-12**: (a) the `DELETE` requires `asset_id` (decision 21); (b) the upsert is all or nothing (decision 22) — E1a.

E1a and E1c are in `dev_release2` (`14d58cc61`); E1b was in W's worktree, not committed, at filing.

## Prevention

- An edit is not a delete plus an insert when other rows point at the id: update in place and keep the id.
- A client-side row id is not a database id; keep the two apart in the type.

## Source files

| Role | Path |
|------|------|
| Upsert schema with `id`; the type check since 1.3 (I-09) | `backend/app/schemas/assets/events.py` |
| `_upsert_asset_events` (in-place edit, duplicate merge) | `backend/app/services/assets/event_store.py` |
| Events API, 400 codes | `backend/app/api/v1/assets/events.py` |
| Repair of the stored types (I-09, 1.3) | `backend/app/db/post_migration/event_types.py` |
| Event editor section (`dbEventId`, `importMatchKeys`) | `frontend/src/lib/components/assets/AssetDataEditorSection.svelte` |
| Shared data editor (match keys) | `frontend/src/lib/components/ui/data-editor/DataEditor.svelte` |
| Events CSV import (`value` alias) | `frontend/src/lib/components/assets/EventDataImportModal.svelte` |
| API tests | `backend/test_scripts/test_api/test_assets_events.py` |
| Plan | `LibreFolio_developer_journal/Release_2/phases/20_performanceCharts/plan-phase00PerformanceChartsBugfix-AssetEvents.prompt.md` |

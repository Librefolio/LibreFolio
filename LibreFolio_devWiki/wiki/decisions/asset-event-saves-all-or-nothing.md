---
title: "Asset event saves: all or nothing in one request, «+ New event» never overwrites, a delete names its asset, an unknown type is refused (decisions 20–23 of release 1.3)"
category: decision
status: resolved
date: 2026-10-15
tags: [backend, frontend, assets, asset-events, api, breaking-change, data-editor, post-migration, release-1.3]
related:
  - features/F-031
  - features/F-090
  - features/F-051
  - problems/asset-event-edit-delete-reinsert
  - problems/provider-event-dated-today-not-synced
  - problems/select-list-under-the-sticky-table-header
  - problems/testing-library-events-prop-read-as-mount-option
  - problems/reused-ids-after-delete
---

# Decision: asset event saves are all or nothing

## Context

Release 1.3, workstream W (import and transactions), lot E1, 15/10. The event modules (`api/v1/assets/events.py`,
`services/assets/event_store.py`, `schemas/assets/events.py`) had passed from workstream X to W the night before
(X CP2b). Five findings of the 1.2 cycle met there: V-22, and I-09…I-12 of backlog 38, the part left open by
[[problems/asset-event-edit-delete-reinsert]].

- **V-22**: «+ New event», the small window of a transaction's *Linked Event* field, saved through the data editor's
  upsert. With no id, an event on a date and type that already had a manual event updated that event in place, and
  the window said it had created one. W's analysis corrected the premise: a provider's event was never overwritten.
  The provider case came from the window, which re-read the day by date and type after saving and could link the
  transaction to the provider's event (I-10 S4).
- **I-12**: `POST /api/v1/assets/events` committed item by item, and slice by slice within an item. A refused item
  left the items before it saved, an unknown asset answered 200 with «0 saved», and a refusal's `detail` was a
  sentence. `DELETE /api/v1/assets/events?ids=…` took ids of any asset. The app always sent the open asset's ids, so
  the hole was in the API only.
- **I-09**: `FAAssetEventPoint.type` was a plain `str`, so a hand-written CSV could store `dividend` or `dividendo`.
  The column is the `AssetEventType` enum: from then on every read of that asset's events failed (`LookupError`, a
  500), and its events stopped showing.
- **I-10**: the data editor saved in two requests, the upsert and then the `DELETE` of the removed rows. An event
  linked to a transaction was skipped with a warning while the rest was saved. An edit could not take the date and
  type of an event deleted in the same save (`EVENT_KEY_CONFLICT`). A refusal showed Axios' generic message.
- **I-11c**: the editor put the asset's currency on every event, so a CSV row written in another currency was
  relabelled in silence, its amount unchanged.

## Options Considered

- **20, «+ New event»**:
  - leave it and document it;
  - a save without id never overwrites, anywhere. The events export carries no ids, so the «export, edit, re-import»
    loop would break: it rests on date and type;
  - refuse only in «+ New event», where the intent is to create. For the refusal W proposed «Use this», «Create
    anyway» and «Cancel».
- **21, the delete**: unchanged, or scoped to one asset.
- **22, partial saves**: keep them, and say in the message which rows were saved; or all or nothing, naming the row.
- **23, unknown types**:
  - check at the door only, and leave the stored rows broken;
  - path **A**: keep the stored ones and log them. They keep breaking every read of their asset's events;
  - path **B**: delete the ones not linked to a transaction and log them. The linked ones could not be deleted.
  - A count on a copy of the developer's database was to help choose. The vehicle could be an Alembic migration (it
    would have been 008) or a post-migration fix.
- **The editor's save** (W's question to the coordinator, 16:20): two requests with the deletions first (the first
  E1b design), or the deletions inside the upsert request.

## Decision

By the developer on 15/10, in the decisions file of release 1.3 (points 20–23) and in chat (12:30–12:44). The
coordinator settled the vehicle of 23 (12:58) and the editor's save (16:20). Quotes are translated from Italian.

- **20**: «+ New event» never overwrites. If the asset already has an event with that date and type, manual or from a
  provider, the save is refused. The window shows the event, with «Edit this» (manual events only: the form takes
  its values and saves it by id), «Use this» and «Cancel». **No «Create anyway»**: two events of the same type on the
  same day do not happen. The data editor and its CSV import keep updating by date and type.
- **21**: deleting events names the asset. The hole was real only in the API, so this guards against future errors.
- **22**: «all or nothing, and if it fails it tells you where».
- **23**: «upper-case it, and if it still does not fit, refuse the save; for the ones saved wrong the only way is to
  delete them, they are not shown anyway».
  - The correctable stored types are upper-cased, the others deleted.
  - W's proposal for the linked ones: unlink their transactions first, then delete, logging both steps.
  - A post-migration fix, not Alembic, so that every row's log line is seen, in Docker too. Start-up runs Alembic in a
    subprocess and captures its output (`main.py`).
  - No count on the developer's copy: production data is not touched. On any database the fix's dry run is the count.
- **One request**: the editor's save sends its deletions inside the upsert request (`delete_ids`). They are deleted
  first, in the same transaction, with one commit. Two requests would leave the deletions done when the upsert is
  refused, which breaks 22 for the user. The separate `DELETE` stays, for a plain deletion.

## How it is built

### E1a: the backend (`a2fb6936f`, `fix(events)!`, in `dev_release2` with `14d58cc61`)

- `bulk_upsert_events()` runs the items in order in one transaction. `_write_manual_item()` checks an item, then
  writes and flushes it, so a later item sees what the earlier ones wrote. One commit closes the request; any refusal
  rolls all of it back. The provider refresh keeps its sliced commits (`_upsert_asset_events(..., commit=True)`,
  called from `refresh.py`), so that one transaction does not hold SQLite's single write lock for a whole sync.
- A refusal answers `detail = {error_code, message, params}`, and `params` always holds `item_index` and
  `asset_id` (`_REFUSAL_STATUS` in `api/v1/assets/events.py`). Any other `AssetSourceError` stays a 500 with a string
  `detail`.

  | Code | Status | Also in `params` |
  |---|---|---|
  | `EVENT_ASSET_NOT_FOUND` | 400 | nothing (until 1.3, a 200 with `count` 0) |
  | `EVENT_CURRENCY_MISMATCH` | 400 | `expected`; `events`, each with `event_index`, `date`, `type`, `currency` |
  | `EVENT_NOT_EDITABLE` | 400 | `ids` |
  | `EVENT_KEY_CONFLICT` | 400 | `date`, `type` |
  | `EVENT_EXISTS` | 409 | `existing` (`create` items only) |
  | `EVENT_NOT_DELETABLE` | 400 | `ids` (added by E1b) |
  | `EVENT_IN_USE` | 409 | `events` (added by E1b) |

- `FAEventUpsert.mode` is `"upsert"` (the default, sent by nobody: the editor and its CSV) or `"create"`.
  - A `create` item names no id (422).
  - An event on a date and type the asset already has, manual or from a provider, is refused with 409
    `EVENT_EXISTS` (`_reject_existing_events()`).
  - `params.existing` lists the stored events of those keys: `id`, `date`, `type`, `value`, `notes`, `is_auto`, and
    `linked_transactions` (a count).
- Each result carries `event_ids`: the event each point wrote, in request order. The window links that id instead of
  re-reading the day (I-10 S4).
- `FAAssetEventPoint.normalize_type()` trims and upper-cases the type, and refuses anything outside `AssetEventType`
  with a 422. The point is shared by the API, the provider output and the Scheduled Investment schedules. The
  providers already wrote upper case, and the type stays a `str` in the OpenAPI.
- `DELETE /api/v1/assets/events` requires `asset_id`: a request with `ids` alone is a 422. An id of another asset
  answers `not_found`, and its event stays (`delete_events_bulk()`). The `DELETE` still answers 200 with one outcome
  per id and commits the deletable ones.

### E1c: the stored types (`313dde70e`, in `dev_release2` with `14d58cc61`)

- The post-migration fix `event_types` (`EventTypesFix`, appended last to `FIXES`):
  - a type that `strip().upper()` makes valid is corrected in place. The event keeps its id, and its transactions
    stay linked;
  - an event whose type stays unknown is deleted, after its transactions are unlinked (`asset_event_id` NULL). The
    transactions stay;
  - the detection logs a warning with what it would do, so the dry run
    (`python -m backend.app.db.post_migration --dry-run`) is the count. After the commit, each corrected or deleted
    event and each unlinked transaction gets its own INFO line.
- The framework used to require every table's row count unchanged. A fix now declares its deltas with
  `row_count_changes()` (`{table: delta}`, `{}` by default, in `base.py`). After `apply`, every table is checked
  exactly against them (`_expected_counts()`). A failure reads «row counts not as expected: table (expected N, found
  M)». The declaration is asked inside the fix's `try`, so a fix that fails to declare is reported, not raised.

### E1b: one request, and the windows (in W's worktree, not committed at filing)

- `FAEventUpsert.delete_ids`, in `upsert` items only, lists events of the item's asset, manual or from a provider,
  as the editor could delete them in 1.2. A provider's event comes back with its next sync.
  - `_delete_item_events()` deletes them right after the asset lookup, before every other check, and flushes. An
    edit of the item can then take the date and type of an event it deletes (I-10).
  - An id that is unknown, already gone, or of another asset is 400 `EVENT_NOT_DELETABLE` (`params.ids`).
  - An event linked to a transaction, a provider's included, is 409 `EVENT_IN_USE`. `params.events` gives each
    one's `id`, `date`, `type` and number of linked transactions, but no transaction ids: they may belong to other
    users.
  - 422 from the validators: `delete_ids` in a `create` item, the same id twice, an id both deleted and edited, an
    item with neither events nor deletions.
  - Each result carries `deleted_ids`, and `success_count` counts an item that only deletes.
- The data editor (`AssetDataEditorSection.svelte`) sends one `POST`: `delete_ids` for the rows marked deleted,
  `events` for the edited and new rows.
  - On success it drops the rows of `deleted_ids`. On a refusal nothing changes, and the message names the row.
  - Until 1.3, a deletion in use was skipped with a warning while the rest was saved.
  - A row that has a currency of its own (a CSV row) sends it (I-11c): one in another currency is refused with its
    row, instead of being relabelled.
- «+ New event» (`EventCreateMiniModal.svelte`) sends `mode: "create"`. On `EVENT_EXISTS`, `EventExistsPanel.svelte`
  lists the events already there: type, date, amount, notes, manual or provider, linked transactions.
  - «Use this» links the event and writes nothing.
  - «Edit this», for a manual event only: the form switches to that event, with its values, and saves it by id in an
    `upsert` item. A provider's event shows a note instead.
  - «Cancel» goes back to the form.
  - There is no «Create anyway».
  - The form keeps a stored amount's decimals (`existingAmountText()`: `1.500000` becomes `1.50`, `0.123456` stays).
- `eventSaveError.ts` turns each refusal into one translated sentence (`events.saveError.*`, `assets` catalogue).
  - The sentence names the event at fault by date and type. For a 422 on a type, it finds the row from the index the
    error points at.
  - An unknown code falls back to a generic sentence with the server's English message.
- `AssetEventPicker.svelte` registers on `registerPortfolioMutationListener` and re-reads its list after any write
  under `/api/v1/assets/events`. The API client notifies that bus after every successful write; `/query` is a read.
  Without it, after «Edit this» the picker kept the event's old values: `fetchEvents` returns early while its key is
  unchanged.

## Consequences

- **For the user**:
  - a refused events save stores nothing, deletions included, and names the event at fault;
  - an event in use stops the whole save instead of being skipped;
  - «+ New event» shows what is there instead of changing it;
  - an events CSV with one wrong row saves nothing until the row is fixed.
- **For API clients**, the `[Unreleased]` CHANGELOG on `dev_release2` has:
  - two ⚠️ breaking changes: `DELETE /api/v1/assets/events` requires `asset_id`, and a refusal's `detail` is an object
    (a missing asset is now a 400);
  - a ✨ line for `mode: "create"` and `event_ids`;
  - two 🐛 lines, for the unknown types and for all or nothing.
  - The app itself no longer calls the `DELETE`.
- **A provider's event stays deletable from the editor, as in 1.2.** This keeps the contract behind S3, which the
  coordinator closed without code on 15/10. The editor offers *Delete* on a provider's read-only row, its 🔒 tooltip
  (`dataEditor.autoEvent.tooltip`) says the deletion is temporary, and the user guide says the same.
  - The first E1b cure took manual events only. A save that deleted a provider's row was then refused whole
    (`EVENT_NOT_DELETABLE`), with a misleading message: «…no longer exists… reload».
  - The docs-writer found that regression (17:50). W corrected it the same day, before E1b was committed: red
    tests first, then the rule above.
- **What decision 20 does not cover.** The `upsert` mode still stores two events without id on one date and type, and
  a provider's event can still sit beside a manual one on the same key: only «+ New event» is guarded.
- **An edge case.** A `create` refused because of an event that an earlier item of the same request wrote lists that
  event in `existing`, with an id the rollback removes. The earlier items are flushed, so `_reject_existing_events()`
  sees them. The docs-writer's note in plan 04 records it; the developer page does not, at filing.
- **Still open around events**:
  - W-B16 (I-11b): an import ignores the `source` column, so a provider's row comes back as a manual event;
  - C-65a: the provider-change modal ([[features/F-090]]);
  - a provider event dated today: [[problems/provider-event-dated-today-not-synced]].

## Proofs

Every part was written red first by the test-author, then cured (plan 04, section E1). The tests:

- the store's service tests (`test_asset_event_store.py`, new in E1a) and the API tests (`test_assets_events.py`);
- the fix's tests (`test_post_migration_event_types.py`);
- two Vitest files: `eventSaveError.test.ts` and `EventExistsPanel.test.ts`;
- two new E2E specs: `tx-event-create-exists.spec.ts` for the window and `asset-event-editor-save.spec.ts` for the
  editor's save.

Two reds that were not the intended ones are filed apart:

- [[problems/testing-library-events-prop-read-as-mount-option]], a defect of the test;
- [[problems/select-list-under-the-sticky-table-header]], a product defect outside E1 (W-B26).

The provider-event test had to date its event yesterday: [[problems/provider-event-dated-today-not-synced]].

## Links

- [[features/F-031]], [[features/F-090]], [[features/F-051]]
- [[problems/asset-event-edit-delete-reinsert]]: the in-place edit of 2026-10-08 that this builds on
- [[problems/reused-ids-after-delete]]: the post-migration framework that E1c extends
- Sources:
  - plan 04, sections «Analisi di E1», «E0» and «E1 — eventi: decisioni 20–23…»;
  - the decisions file of release 1.3, points 20–23;
  - `BACKLOG_POST_1.2.md` (W-B16, W-B26) and backlog 38 (I-09…I-12).

## Source files

| Role | Path |
|------|------|
| Events API: the refusal statuses, `mode`, the scoped `DELETE` | `backend/app/api/v1/assets/events.py` |
| Upsert, `delete_ids`, the checks, the provider upsert in place | `backend/app/services/assets/event_store.py` |
| `FAAssetEventPoint.normalize_type()`, `FAEventUpsert` and its validators | `backend/app/schemas/assets/events.py` |
| The provider refresh, still committed in slices | `backend/app/services/assets/refresh.py` |
| The post-migration fix `event_types` | `backend/app/db/post_migration/event_types.py` |
| `row_count_changes()` | `backend/app/db/post_migration/base.py` |
| `_expected_counts()`, the registration in `FIXES` | `backend/app/db/post_migration/__init__.py` |
| Data editor: the one-request save | `frontend/src/lib/components/assets/AssetDataEditorSection.svelte` |
| Data editor: row actions, read-only rows | `frontend/src/lib/components/ui/data-editor/DataEditor.svelte` |
| «+ New event» | `frontend/src/lib/features/transactions/events/EventCreateMiniModal.svelte` |
| The events already there | `frontend/src/lib/features/transactions/events/EventExistsPanel.svelte` |
| Refusals as sentences, `existingAmountText()` | `frontend/src/lib/features/transactions/events/eventSaveError.ts` |
| Event picker, re-read on a write | `frontend/src/lib/features/transactions/events/AssetEventPicker.svelte` |
| The write bus | `frontend/src/lib/stores/portfolio/portfolioMutation.ts` |
| The new i18n keys (EN) | `frontend/src/lib/i18n/assets/en.json` |
| Store tests | `backend/test_scripts/test_services/test_asset_event_store.py` |
| API tests | `backend/test_scripts/test_api/test_assets_events.py` |
| Fix tests | `backend/test_scripts/test_db/test_post_migration_event_types.py` |
| Vitest | `frontend/src/lib/features/transactions/events/eventSaveError.test.ts` |
| Vitest | `frontend/src/lib/features/transactions/events/EventExistsPanel.test.ts` |
| E2E, the window | `frontend/e2e/transactions/tx-event-create-exists.spec.ts` |
| E2E, the editor's save | `frontend/e2e/assets/asset-event-editor-save.spec.ts` |
| Developer docs | `mkdocs_src/docs/developer/backend/assets/events.md` |
| Developer docs, the post-migration fixes | `mkdocs_src/docs/developer/architecture/database/index.md` |
| User guide, the data editor | `mkdocs_src/docs/user/assets/detail/data-editor.en.md` |
| User guide, events and «+ New event» | `mkdocs_src/docs/user/assets/detail/events.en.md` |
| Plan 04 (sections E0, «Analisi di E1», E1) | `LibreFolio_developer_journal/Release_2/Phase_1/04_importTransactions/plan-phase01ImportTransactions.prompt.md` |
| Decisions 20–23 | `LibreFolio_developer_journal/Release_2/Phase_1/decisioni-analisi-20261014.md` |
| Backlog W-B16, W-B26 | `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` |
| Backlog I-09…I-12 | `LibreFolio_developer_journal/Release_2/Phase_0/38_postReleaseBacklog/README.md` |

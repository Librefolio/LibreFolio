---
title: "Phase 07 Part 1 — Transaction System Foundation"
category: source
source_file: "LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte1/plan-phase07-transaction-Part1.md"
git_hash: "a61b0dfa"
date_ingested: "2026-04-24"
date_updated: "2026-04-25"
status: "✅ DONE"
tags: [transactions, asset-events, db, backend, phase07]
related: [features/F-046, features/F-051, decisions/tx-link-uuid-semantics, entities/db-models]
---

# Source: Phase 07 Part 1 — Transaction System Foundation

> **Plan**: `phases/phase-07-subplan/Parte1/plan-phase07-transaction-Part1.md` (602 lines) — ✅ **DONE**
> **Phase**: 7 — Transactions System (prerequisite for Parts 2–5)
>
> **Path note**: archived 2026-04-25 from `RoadmapV4_UI/plan-phase07-transaction-Part1.md`
> into `phases/phase-07-subplan/Parte1/`. All Part 1 work is complete.

## What this plan established

Phase 7 Part 1 was the DB and schema realignment sprint — prerequisite for all subsequent Phase 7 work (BRIM extension, API consolidation, staging modal, etc.).

### Core objective

1. **Link `Transaction` → `AssetEvent`** via optional FK `asset_event_id` with RESTRICT delete semantics.
2. **Introduce `event_compatible` flag** on `TXTypeMetadata` — DIVIDEND, INTEREST, ADJUSTMENT can be linked to AssetEvents; all other types cannot.
3. **Convert AssetEvent delete API** from single-delete (`DELETE /events/{id}`) to bulk (`DELETE /events?ids=...`) with RESTRICT-aware breakdown response.
4. **Fix AssetDataEditorSection.svelte** — batch bulk call replacing `Promise.all` of singles, correct count toast, re-derive after save (4 known bugs).

### Key schema additions

| Item | Type | Detail |
|------|------|--------|
| `Transaction.asset_event_id` | `Optional[int]` | FK to `asset_events.id` ON DELETE RESTRICT; `NULL` = standalone transaction |
| `EVENT_COMPATIBLE_TYPES` | `frozenset` | `{DIVIDEND, INTEREST, ADJUSTMENT}` — the only types that can carry `asset_event_id` |
| `TXTypeMetadata.event_compatible` | `bool` | Per-type flag in `TX_TYPE_METADATA` table |
| `TXCreateItem.asset_event_id` validator | Pydantic rule | Rejected if type not in `EVENT_COMPATIBLE_TYPES`, or if `asset_id` is absent |
| `FAEventBulkDeleteResponse` | Pydantic | Per-item status with accessible/hidden RESTRICT breakdown |

### Migration (001_initial.py changes)

```sql
-- Added to transactions table:
asset_event_id INTEGER REFERENCES asset_events(id) ON DELETE RESTRICT
CREATE INDEX idx_transactions_asset_event ON transactions (asset_event_id)
```

### Service layer

`TransactionService._validate_asset_event_link(session, asset_event_id, expected_asset_id)`:
- Loads the AssetEvent by ID; raises 404 if missing
- Validates `asset_event.asset_id == transaction.asset_id`; raises 409 on mismatch

### Test coverage (Part 1 scope)

6 schema tests (validator rules), 6 service tests (cross-record + RESTRICT), 4 API tests (E2E bulk delete),
1 E2E Playwright spec (`asset-event-delete.spec.ts`) covering the 4 frontend bugs.

## What was explicitly deferred to later parts

- Currency validation on prices/transactions → Part 3 Blocco I
- OHLC sentinel for price imports → deferred
- i18n keys for `dataEditor.col.currency` / `dataEditor.col.type` → deferred
- Mock data population with `asset_event_id` → optional

## Connection to later parts

- Part 2 (BRIM Revision 2): removed `asset_events` from BRIM parse output — dividends become plain DIVIDEND transactions, not asset events.
- Part 3 (API Consolidation): `asset_event_id` FK used in `TXCreateItem` for the bulk endpoint.
- Part 3 Closure (Blocco I): `events/suggest` endpoint surfaces candidate asset events for a given transaction to enable manual link creation in the UI.

## Related wiki pages

- [[features/F-046]] — Transaction Model & Bulk API
- [[features/F-051]] — Transaction ↔ AssetEvent Link (FK)
- [[decisions/tx-link-uuid-semantics]] — link_uuid / TRANSFER pairing (parallel stream)
- [[sources/phase07-part3-closure]] — events/suggest + Blocco I details

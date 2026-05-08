---
title: "txStore Pattern — Single Source of Truth for Loaded Transactions"
category: concept
tags: [frontend, stores, transactions, svelte5, single-source-of-truth, refactor]
related:
  - concepts/entity-store-pattern
  - decisions/txstore-single-source-of-truth
  - features/F-048
  - sources/phase07-part4-round6-planc-txstore-refactor
---

# Concept: txStore Pattern

## Definition

`txStore.svelte.ts` is a page-scoped reactive store that holds **all loaded transactions** as a `Map<number, TXReadItem>`. It is populated once from `reload()` and serves as the single source of truth for every component that needs transaction data: the main DataTable, BulkModal, PickerModal, DeleteModal, and the page toolbar.

Unlike `createEntityStore<T>()` (which manages bounded entity lists), txStore is **page-scoped** and **transaction-specialized** — it provides partner resolution, viewer-only guards, and filtering that are specific to the transactions domain.

## Core Invariant

> **One source, zero copies.** No component holds its own copy of transaction data.
> Components read from txStore; mutations are expressed as `PendingOp[]` diffs.

This eliminates 5 categories of recurring bugs that plagued the prop-cascade approach:
1. `link_uuid` fragile (generated in 4+ points, orphaned partners)
2. "edited" false positives (`patchRowFromForm` always marking edited)
3. Duplicated/stale data (3 copies diverging after mutations)
4. Paired split after reset (partner orphaned when `resetRow` didn't re-merge)
5. Props cascade viewer-only (guard duplicated in 3+ points)

## Store API

```ts
// txStore.svelte.ts (~120 LOC)
setAll(main: TXReadItem[], partners: TXReadItem[]): void  // called once from reload()
get(id: number): TXReadItem | undefined
getPartner(id: number): TXReadItem | undefined            // via related_transaction_id
getAll(): TXReadItem[]
getFiltered(fn: (tx: TXReadItem) => boolean): TXReadItem[]
canEdit(id: number): boolean                               // centralized viewer guard
invalidate(): void                                         // after commit/delete → triggers reload
```

## WorkspaceIntent Pattern

Toolbar actions no longer pass full data objects to BulkModal. Instead they pass a minimal intent:

```ts
type WorkspaceIntent =
  | { action: 'create' }
  | { action: 'edit', txIds: number[] }
  | { action: 'delete', txIds: number[] }
  | { action: 'clone', txIds: number[] }
```

BulkModal reads the actual data from txStore using the provided IDs.

## PendingOp Model

BulkModal holds modifications as typed operations, not full row copies:

```ts
type PendingOp =
  | { op: 'create', draft: TxFields }
  | { op: 'edit', txId: number, overrides: Partial<TxFields> }
  | { op: 'delete', txId: number }
```

**Status is derived**, never set manually:
- `op='create'` → `new`
- `op='edit'` + non-empty overrides → `edited`
- `op='delete'` → `delete`
- otherwise → `original`

## Relationship to entityStore

| Aspect | `createEntityStore<T>()` | `txStore` |
|--------|--------------------------|-----------|
| Scope | App-wide singleton | Page-scoped (transactions page) |
| Data shape | Bounded list (assets, brokers) | Unbounded (all user transactions) |
| Mutation model | `merge()` + `invalidate()` | External `PendingOp[]` diff |
| Partner resolution | N/A | `getPartner()` via `related_transaction_id` |
| Access control | N/A | `canEdit()` checks broker role |

## Where It Applies

- **Transactions page** (`frontend/src/routes/(app)/transactions/+page.svelte`): `reload()` populates `txStore.setAll()`
- **TransactionPickerModal**: reads `txStore.getAll()` directly — no props needed
- **TransactionBulkModal**: reads individual rows via `txStore.get(id)`, resolves partners via `txStore.getPartner(id)`
- **TransactionDeleteModal**: parent reads from txStore before passing to DeleteModal
- **Page toolbar**: `txStore.canEdit()` for `filterEditableRows()`

## Interface Deduplication

Step 6a created `frontend/src/lib/components/transactions/types.ts` as the canonical source for shared interfaces:
- `TXReadItem` — full transaction read model
- `ValidationIssue` — validation error structure
- `AssetEvent` — linked asset event

All components import from this single file instead of declaring local duplicates.

## Source files

| Role | Path |
|------|------|
| txStore implementation | `frontend/src/lib/stores/txStore.svelte.ts` |
| Interface types (canonical) | `frontend/src/lib/components/transactions/types.ts` |
| Page (populates store) | `frontend/src/routes/(app)/transactions/+page.svelte` |
| Picker (reads from store) | `frontend/src/lib/components/transactions/TransactionPickerModal.svelte` |
| Bulk modal (reads + PendingOp) | `frontend/src/lib/components/transactions/TransactionBulkModal.svelte` |
| Plan (designed here) | `LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part4_Round6_PlanC_TxStoreRefactor.prompt.md` |


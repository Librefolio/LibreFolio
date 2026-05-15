---
title: "txStore Pattern — Single Source of Truth for Loaded Transactions"
category: concept
tags: [frontend, stores, transactions, svelte5, single-source-of-truth, refactor]
related:
  - concepts/entity-store-pattern
  - decisions/txstore-single-source-of-truth
  - decisions/pendingop-tagged-union
  - features/F-048
  - sources/phase07-part4-round6-planc-txstore-refactor
  - sources/phase07-part4-round6-planc3-pendingop-refactor
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

## PendingOp Model (Plan C3 — final architecture)

BulkModal holds modifications as a `PendingOp[]` tagged union — not full row copies:

```ts
/** Pure editable data fields — no metadata. */
interface DraftFields {
    broker_id: number; asset_id: number | null; type: TransactionTypeCode;
    date: string; quantity: string; cash: {code: string; amount: string} | null;
    tags: string[]; description: string; asset_event_id: number | null;
    cost_basis_override: string;
}

/** Partner rendering data for paired transactions. */
interface PartnerDisplay {
    partnerId?: number; partnerBrokerId?: number;
    partnerCash?: {code: string; amount: string} | null;
    partnerDate?: string; partnerPayload?: TxFields | null;
}

/** Tagged union — one per visible row in BulkModal grid. */
type PendingOp = (
    | { op: 'create'; link_uuid: string | null; }
    | { op: 'edit'; txId: number; markedDelete: boolean; addedViaPicker?: boolean; }
) & { tempId: string; fields: DraftFields; } & PartnerDisplay;
```

### Key invariants

1. **Zero-copy originals**: original is ALWAYS `txStoreGet(op.txId)` — never stored on the op
2. **Status always derived**: `deriveStatus(op)` computes from diff vs txStore
3. **Tagged discriminator**: `op.op === 'create'` has `link_uuid`; `op.op === 'edit'` has `txId` + `markedDelete`
4. **Factory functions** (replaced `fromTx()`):
   - `fieldsFromTx(tx)` — pure field extraction with auto-sign
   - `editOpFromTx(txId)` — creates edit op, reads from txStore
   - `createOpFromClone(tx)` — creates create op with today's date

**Status derivation** (never set manually):
- `op.op === 'create'` → `new`
- `op.op === 'edit'` + `markedDelete` → `delete`
- `op.op === 'edit'` + non-empty diff vs txStore → `edited`
- otherwise → `original`

See [[decisions/pendingop-tagged-union]] for rationale.

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
| Plan (designed here) | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/plan-phase07-transaction-Part4_Round6_PlanC_TxStoreRefactor.prompt.md` |


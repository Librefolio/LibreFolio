---
title: "WorkspaceIntent Pattern"
category: concept
tags: [frontend, svelte5, transactions, bulkModal, staging, intent, declarative-api]
related:
  - concepts/txstore-pattern
  - concepts/import-todo-signals
  - entities/import-wizard-modal
  - features/F-048
---

# Concept: WorkspaceIntent Pattern

## Definition

`WorkspaceIntent` is a **frontend-only** Svelte 5 declarative API that expresses **bulk staging intentions** inside `TransactionBulkModal`. It describes what the user intends to do to the transaction workspace: create new rows, edit existing ones, clone, delete, or import from BRIM.

> ⚠️ **Critical clarification**: `WorkspaceIntent` is NOT a backend concept. It is NOT related to multi-tenancy, workspace isolation, or data scoping. The backend isolates data via JWT session cookies (`get_current_user`) and service-level filters (`BrokerUserAccess`). This was clarified in the 2026-06-18 wiki audit.

## Where It Applies

Exclusively inside `TransactionBulkModal.svelte`. It interfaces with:
- `txStore` — the reactive `Map<id, TXReadItem>` single source of truth
- `PendingOp` tagged union — the per-row staging state
- `ImportWizardModal` — BRIM import results arrive as `TXCreateItem[]` and are converted via `txCreateItemToPendingOp()`

## The Type

```typescript
type WorkspaceIntent =
  | { type: 'create'; tx: TXCreateItem }
  | { type: 'edit'; txId: number }
  | { type: 'clone'; txId: number }
  | { type: 'delete'; txId: number }
  | { type: 'import'; items: TXCreateItem[] };
```

> 2026-11-07 lint: the type above does not match the code. In `TransactionBulkModal.svelte` it is exported as
> ```typescript
> export type WorkspaceIntent =
>   | {action: 'create'} | {action: 'import'}
>   | {action: 'edit'; txIds: number[]} | {action: 'delete'; txIds: number[]} | {action: 'clone'; txIds: number[]};
> ```
> and passed as the `intent` prop that **opens** the modal (the declarative replacement of the old `mode` prop). Rows
> then read their originals from `txStore` by id. `{action: 'import'}` opens the Import Wizard; its results arrive
> through `onImportBatch(creates: Array<{tx, todos}>)` and each `TransactionCreateItem` becomes a `create` op via
> `txCreateItemToPendingOp()`. The `PendingOp[]` lives in the modal's own state; `txStore` holds only the saved rows.
> The steps below are kept as first written.

## How It Works

1. User triggers an intent (e.g., clicks "Edit" on a row, or confirms import in `ImportWizardModal`)
2. `BulkModal` dispatches a `WorkspaceIntent`
3. The intent handler modifies the `PendingOp` map in `txStore`
4. Svelte 5 reactivity propagates the change to all grid rows

## Relationship to `ImportTodo`

When `type: 'import'` is dispatched, the `TXCreateItem[]` may contain `field_todos` (see [[concepts/import-todo-signals]]). These become `ImportTodo[]` on the `MergedTransaction` rows (type `MergedTx` in `frontend/src/lib/features/transactions/import/importTypes.ts`) — visible warnings/blockers shown in Step 4 of the Import Wizard. They never leave the wizard scope; by the time items arrive in `BulkModal` via `onImportBatch`, they have been resolved or accepted.

## Why Important

Before `WorkspaceIntent` was introduced, BulkModal had a `mode` prop (`'create' | 'edit' | 'import' | ...`) that was hardcoded at open time. This created complexity when multiple operations needed to coexist in one session. The `WorkspaceIntent` declarative model + `PendingOp` tagged union replaced this with per-row intent tracking. See also [[decisions/bulkmodal-mode-removal]] and [[decisions/pendingop-tagged-union]].

## Source files

| Role | Path |
|------|------|
| BulkModal (primary) | `frontend/src/lib/features/transactions/bulk/TransactionBulkModal.svelte` |
| txStore | `frontend/src/lib/features/transactions/txStore.svelte.ts` |
| Import merge types (`MergedTx`, `ImportTodo[]`) | `frontend/src/lib/features/transactions/import/importTypes.ts` |
| mkdocs (transaction draft state) | `mkdocs_src/docs/developer/frontend/state/transaction-draft.md` |

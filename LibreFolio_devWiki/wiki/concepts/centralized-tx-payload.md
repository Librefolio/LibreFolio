---
title: "Centralized TX Payload Layer"
category: concept
tags: [frontend, transactions, payload, api, architecture, dry, txPayloadHelpers, txCommitApi]
related:
  - decisions/batch-only-split-promote
  - decisions/unified-batch-pipeline
  - concepts/txstore-pattern
  - features/F-048
---

# Concept: Centralized TX Payload Layer

## Definition

A two-module frontend subsystem (`txPayloadHelpers.ts` + `txCommitApi.ts`) that centralizes all transaction payload construction and API commit logic into a single code path. Before this refactor, 9 separate callsites each built their own `{creates, updates, deletes, splits, promotes}` JSON and called the commit endpoint independently — causing divergence and repeated duplication bugs.

The pattern was extracted during Phase 07 PlanD-D1D2 as part of the `plan-CentralizePayloadCommit.prompt.md` work (2026-05-20).

## Where It Applies

All transaction mutation paths:
- `TransactionFormModal` — single + dual creates/updates
- `TransactionBulkModal` — mixed batch (create/edit/delete/split/promote)
- `BulkDeleteLinkedPairModal` — deletes only
- `transactions/+page.svelte` — split, promote, confirmDelete, validateDelete

## The Pattern

### Step 1 — Resolve PendingOps to `ResolvedOp[]`

```typescript
export interface ResolvedOp {
    intent: 'create' | 'update' | 'delete';
    payload?: Record<string, unknown>;   // for create/update
    deleteId?: number;                   // for delete
    linkUuid?: string;                   // for paired creates
}
```

`resolveOps()` iterates the `txStore`'s `PendingOp` map and produces a flat `ResolvedOp[]` from the intent + diff logic.

### Step 2 — Build batch payload

```typescript
buildBatchPayload(resolvedOps, { splits?, promotes? }): TXMixedBatch
```

Pure function: no side effects. Assembles `{creates, updates, deletes, splits, promotes}` from the resolved ops.

### Step 3 — Commit/Validate via `txCommitApi.ts`

```typescript
commitBatch(payload): Promise<TrySaveResult<TXBatchResponse>>
validateBatch(payload): Promise<TrySaveResult<TXValidationResponse>>
```

Single entry point for all commit and validate calls. Handles:
- Uniform error extraction from FastAPI 422 + service-layer validation issues
- Optional toast on success/failure
- `trySave` wrapper (formerly `saveWithRetry`) — never throws, returns discriminated union

### `buildDualCreatePayloads` (FormModal only)

```typescript
buildDualCreatePayloads(layout, from, to, linkUuid): [Record, Record]
```

Centralizes the 3-branch FX/transfer-asset/transfer-cash dual-create logic that was previously duplicated in FormModal.

## Why Important

Before this pattern, the same payload construction bugs appeared independently in multiple modals. The duplicate-collection bug (`problems/dual-form-collect-duplication`) was a direct consequence of scattered callsites. Centralizing here means: fix once, fix everywhere.

## Examples

```typescript
// BulkModal commit
const ops = resolveOps(txStore);
const batch = buildBatchPayload(ops, {
    splits: pendingSplits,
    promotes: pendingPromotes,
});
const result = await commitBatch(batch);
```

## Source files

| Role | Path |
|------|------|
| Payload helpers | `frontend/src/lib/utils/txPayloadHelpers.ts` |
| Commit API | `frontend/src/lib/utils/txCommitApi.ts` |
| trySave wrapper | `frontend/src/lib/utils/trySave.ts` |
| BulkModal (main consumer) | `frontend/src/lib/components/transactions/modals/TransactionBulkModal.svelte` |
| FormModal (dual creates) | `frontend/src/lib/components/transactions/modals/TransactionFormModal.svelte` |
| Page-level delete/split/promote | `frontend/src/routes/(app)/transactions/+page.svelte` |

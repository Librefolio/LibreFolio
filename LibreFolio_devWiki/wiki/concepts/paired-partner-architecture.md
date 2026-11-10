---
title: "Paired Partner Architecture — pairedWith, getPartnerOp, visibleOps"
category: concept
tags: [frontend, transactions, bulkModal, architecture, paired, pattern]
related_features: [F-048, F-097]
related_decisions: [decisions/pendingop-tagged-union, decisions/tx-link-uuid-semantics]
---

# Paired Partner Architecture

## What it is

A frontend architectural pattern for managing paired transactions (TRANSFER, FX_CONVERSION, CASH_TRANSFER) in the BulkModal. Each paired transaction consists of two operations linked by `link_uuid` (for the backend) and `pairedWith` (for frontend rendering/interaction).

## Core Primitives

> 2026-11-07 lint: the primitives below were rewritten to match the code. The first version described `pairedWith`
> as bidirectional, `getPartnerOp(ops, op)` reading `op.pairedWith`, an `isHiddenPartner()` filter and a
> `resolveFormItems(op, ops)` function; none of these exists. In the code `pairedWith` is set **only on the hidden
> partner** and points at the visible main op (unified partner architecture, `199cacfed`, 2026-05-26).

### 1. `pairedWith?: string` (on PendingOp)

Set only on the **hidden partner**: the `tempId` of the visible main op it belongs to. An op with `pairedWith` set is
by definition the hidden half of a paired row (`txBulkTypes.ts`):
```typescript
export type PendingOp = (...) & {
    tempId: string;
    pairedWith?: string;        // set → this op is the hidden partner of row `pairedWith`
    link_uuid?: string | null;  // shared pairing UUID for backend payloads (WAC, commit)
    inaccessible?: boolean;     // W4b: partner on an inaccessible broker — read-only sentinel
    // ...
};
```

### 2. `getPartnerOp(mainTempId: string): PendingOp | undefined`

Finds the hidden partner of a visible main op (inside `TransactionBulkModal.svelte`):
```typescript
function getPartnerOp(mainTempId: string): PendingOp | undefined {
    return ops.find((o) => o.pairedWith === mainTempId);
}
```

### 3. `visibleOps` (derived)

Every op without `pairedWith`, sorted by date for display (the ledger and the payload keep the original order):
```typescript
let visibleOps = $derived(ops.filter((o) => !o.pairedWith).sort(/* by date */));
```

The hidden partner is the «to» half of the pair (the receiver), or — whatever the direction — the placeholder half on a
broker the user cannot read (`inaccessible`).

### 4. `resolveFormItemsFromOps(mainOp, ops, ...)` / `resolveFormItemsForView(row, ...)`

Builds FormModal items respecting partner relationships (`resolveFormItems.ts`). For a paired op, produces both sides
of the dual form from the op + its partner (found the same way: `ops.find(o => o.pairedWith === mainOp.tempId)`).

## Design Rules

| Rule | Rationale |
|------|-----------|
| `pairedWith` sits only on the hidden half and points at the visible half (the giver for TRANSFER) | One direction, one lookup |
| `link_uuid` is shared (same value on both) | Backend uses this to match the pair |
| `visibleOps` is the ONLY array used for rendering | Prevents double-rendering of partners |
| `getPartnerOp` is the ONLY way to access partner data | Single point of maintenance |

## How Operations Create Pairs

| Source | `pairedWith` assignment | `link_uuid` assignment |
|--------|------------------------|----------------------|
| New paired (user creates) | The partner op gets the main op's `tempId` | `generateUUID()` shared |
| Clone from DB | `getTypeRule(type)?.requiresPair` → generate | Based on type rule, not source |
| `collapsePairedOps()` (DB edit) | Detects partners via `related_transaction_id`, keeps the «from» half visible, sets `pairedWith` on the «to» half | `generateUUID()` shared |
| Hidden partner (inaccessible broker) | Created with `pairedWith` pointing to visible op | Shared UUID |

## Relationship to Backend

The backend doesn't know about `pairedWith` — it's purely frontend state. The backend uses `link_uuid` to match pairs during commit. The mapping is:

```
Frontend: op.pairedWith → UI rendering, form editing, visibility
Backend:  op.link_uuid  → pair matching in execute_batch's «link» stage
```

## Source files

| Role | Path |
|------|------|
| PendingOp type + pairedWith | `frontend/src/lib/features/transactions/bulk/txBulkTypes.ts` |
| BulkModal (getPartnerOp, visibleOps, collapsePairedOps) | `frontend/src/lib/features/transactions/bulk/TransactionBulkModal.svelte` |
| Form items for a pair (`resolveFormItemsFromOps`, `resolveFormItemsForView`) | `frontend/src/lib/features/transactions/resolveFormItems.ts` |
| FormModal (consumes `FormModalItems`) | `frontend/src/lib/features/transactions/form/TransactionFormModal.svelte` |

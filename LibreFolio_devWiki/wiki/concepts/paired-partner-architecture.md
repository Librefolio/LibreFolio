---
title: "Paired Partner Architecture — pairedWith, getPartnerOp, visibleOps"
category: Concept
tags: [frontend, transactions, bulkModal, architecture, paired, pattern]
related_features: [F-048, F-097]
related_decisions: [decisions/pendingop-tagged-union, decisions/tx-link-uuid-semantics]
---

# Paired Partner Architecture

## What it is

A frontend architectural pattern for managing paired transactions (TRANSFER, FX_CONVERSION, CASH_TRANSFER) in the BulkModal. Each paired transaction consists of two operations linked by `link_uuid` (for the backend) and `pairedWith` (for frontend rendering/interaction).

## Core Primitives

### 1. `pairedWith: string` (on PendingOp)

A `tempId` reference to the partner operation. Establishes the UI-level pairing:
```typescript
type PendingOp = {
    tempId: string;
    pairedWith?: string;  // tempId of partner
    link_uuid?: string | null;  // shared UUID for backend
    // ...
};
```

### 2. `getPartnerOp(ops: PendingOp[], op: PendingOp): PendingOp | undefined`

O(1) partner lookup using the `pairedWith` field:
```typescript
function getPartnerOp(ops: PendingOp[], op: PendingOp): PendingOp | undefined {
    if (!op.pairedWith) return undefined;
    return ops.find(o => o.tempId === op.pairedWith);
}
```

### 3. `visibleOps` (derived)

Filters out hidden partners (inaccessible broker, or partner rendered inline in dual-form):
```typescript
let visibleOps = $derived(ops.filter(o => !isHiddenPartner(o, ops)));
```

Hidden partners are ops where:
- Their partner references them via `pairedWith` (they ARE the partner)
- They belong to a broker the user can't access (VIEWER role)

### 4. `resolveFormItems(op, ops): FormItem[]`

Builds FormModal items respecting partner relationships. For a paired op, produces both sides of the dual form from the op + its partner.

## Design Rules

| Rule | Rationale |
|------|-----------|
| `pairedWith` is directional (giver→receiver for TRANSFER) | Consistent traversal order |
| Both sides have `pairedWith` pointing to each other | Bidirectional lookup |
| `link_uuid` is shared (same value on both) | Backend uses this to match the pair |
| `visibleOps` is the ONLY array used for rendering | Prevents double-rendering of partners |
| `getPartnerOp` is the ONLY way to access partner data | Single point of maintenance |

## How Operations Create Pairs

| Source | `pairedWith` assignment | `link_uuid` assignment |
|--------|------------------------|----------------------|
| New paired (user creates) | Both ops get each other's `tempId` | `generateUUID()` shared |
| Clone from DB | `getTypeRule(type)?.requiresPair` → generate | Based on type rule, not source |
| `collapsePairedOps()` (DB edit) | Assigns mutual `pairedWith` + generates shared UUID | `generateUUID()` shared |
| Hidden partner (inaccessible broker) | Created with `pairedWith` pointing to visible op | Shared UUID |

## Relationship to Backend

The backend doesn't know about `pairedWith` — it's purely frontend state. The backend uses `link_uuid` to match pairs during commit. The mapping is:

```
Frontend: op.pairedWith → UI rendering, form editing, visibility
Backend:  op.link_uuid  → pair matching in execute_batch Step 6
```

## Source files

| Role | Path |
|------|------|
| PendingOp type + pairedWith | `frontend/src/lib/components/transactions/types.ts` |
| BulkModal (getPartnerOp, visibleOps, collapsePairedOps) | `frontend/src/lib/components/transactions/TransactionBulkModal.svelte` |
| FormModal (resolveFormItems usage) | `frontend/src/lib/components/transactions/TransactionFormModal.svelte` |

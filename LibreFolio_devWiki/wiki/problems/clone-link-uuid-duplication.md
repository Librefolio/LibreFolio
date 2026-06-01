---
title: "Clone Link UUID Duplication — Paired Rows From DB"
category: Problem
status: resolved
date_encountered: 2026-05-27
date_resolved: 2026-05-27
severity: high
tags: [frontend, clone, link-uuid, paired, transfer, bulkModal]
related_features: [F-097, F-048]
related_decisions: [decisions/tx-link-uuid-semantics]
---

# Clone Link UUID Duplication — Paired Rows From DB

## Problem Description

Cloning paired rows (TRANSFER, FX_CONVERSION, CASH_TRANSFER) from DB rows (edit ops) didn't generate a `link_uuid`, causing the backend batch commit to fail with a duplicate/missing link constraint.

## Root Cause

The clone logic at `TransactionBulkModal.svelte` line 867 was:

```typescript
link_uuid: src.op === 'create' && src.link_uuid ? generateUUID() : null,
```

If `src` is an edit op (DB row), `src.op === 'create'` is `false` → `link_uuid: null`. But the type is paired → requires a shared UUID for the backend to match the pair.

The **conceptual error**: the code treated "source had link_uuid" as the condition, but the correct condition is "target type requires a pair."

## Solution

Three-part fix:

### 1. Promote `link_uuid` to top-level PendingOp field
Moved from `{op: 'create'; link_uuid}` union to common `PendingOp & {link_uuid?: string | null}`. Both create and edit ops can now carry link_uuid.

### 2. Fix clone logic
```typescript
// BEFORE: checked source op type
link_uuid: src.op === 'create' && src.link_uuid ? generateUUID() : null,

// AFTER: checks target type rules
link_uuid: getTypeRule(src.fields.type)?.requiresPair ? generateUUID() : null,
```

### 3. Fix `collapsePairedOps()`
Generate shared UUID when collapsing paired edit ops:
```typescript
const sharedUuid = generateUUID();
opArr[fromIdx].link_uuid = sharedUuid;
opArr[toIdx].link_uuid = sharedUuid;
```

### 4. Simplify `fetchBatchWac()`
Eliminated 30-line `linkUuidMap` workaround (3 branches: create with link_uuid, pairedWith lookup, getPartnerOp fallback) → replaced with direct field read: `link_uuid: o.link_uuid ?? undefined`.

## Impact

- **Before fix**: Clone of any DB paired row → commit fails with backend validation error
- **After fix**: Clone works correctly, E2E `tx-commit-all-types` 19/19 + `tx-split-promote` 6/6 pass
- **Bonus**: 30 lines of complex workaround code eliminated

## Key Takeaway

**Decision criteria should be based on the TARGET's needs, not the SOURCE's state.** A cloned transaction is functionally identical to a new pre-filled creation — if the type requires pairing, it must have a link_uuid regardless of where the data came from.

## Source files

| Role | Path |
|------|------|
| BulkModal (cloneRow, collapsePairedOps) | `frontend/src/lib/components/transactions/TransactionBulkModal.svelte` |
| PendingOp type definition | `frontend/src/lib/components/transactions/types.ts` |
| E2E commit all types | `frontend/e2e/transactions/tx-commit-all-types.spec.ts` |

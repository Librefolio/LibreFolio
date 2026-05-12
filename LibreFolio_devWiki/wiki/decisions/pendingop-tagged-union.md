---
title: "PendingOp tagged union replaces DraftRow flat interface"
category: decision
status: resolved
date: 2026-05-11
tags: [frontend, transactions, bulkModal, architecture, type-safety, tagged-union, refactor]
related:
  - decisions/txstore-single-source-of-truth
  - concepts/txstore-pattern
  - features/F-048
  - sources/phase07-part4-round6-planc3-pendingop-refactor
---

# Decision: PendingOp Tagged Union Replaces DraftRow Flat Interface

## Context

After Plan C (txStore refactor) achieved ~80% of the target architecture, `TransactionBulkModal.svelte` still held legacy structures: `interface DraftRow` (27 cloned fields + `original?` + `status`), `fromTx()` (full-clone factory ~35 LOC), and manual status setting. These remnants blocked Plan D (Split/Promote) because:
- `d.original` stored a copy of the DB row → stale if txStore updated
- `status` was set manually → could not distinguish "edit that has no changes" from "genuine edit"
- Flat interface mixed metadata (`tempId`, `status`, `original`) with data fields → impossible to type-narrow for create vs edit paths
- `_partnerFormPayload: Record<string,unknown>` was untyped → silent errors in partner operations

## Options Considered

1. **Incremental patching**: remove `original` but keep DraftRow flat, add `txId?` field
   - Pros: smaller diff, lower risk
   - Cons: still no type discrimination between create/edit; `status` still manual; mixed concerns in one interface

2. **PendingOp tagged union** with DraftFields + PartnerDisplay composition
   - Pros: type-safe branching via `op.op === 'create' | 'edit'`; clean separation of concerns (data vs metadata vs partner); zero-copy originals; status always derived; Plan D trivial
   - Cons: ~80 rename points (`drafts` → `ops`), column access changes (`.broker_id` → `.fields.broker_id`)

## Decision

**Option 2: PendingOp tagged union.** The type safety benefits are decisive — TypeScript's narrowing via discriminated unions makes it impossible to accidentally access `txId` on a create op or `link_uuid` on an edit op.

### Architecture

```typescript
interface DraftFields {
    broker_id: number; asset_id: number | null; type: TransactionTypeCode;
    date: string; quantity: string; cash: {code: string; amount: string} | null;
    tags: string[]; description: string; asset_event_id: number | null;
    cost_basis_override: string;
}

interface PartnerDisplay {
    partnerId?: number; partnerBrokerId?: number;
    partnerCash?: {code: string; amount: string} | null;
    partnerDate?: string; partnerPayload?: TxFields | null;
}

type PendingOp = (
    | { op: 'create'; link_uuid: string | null; }
    | { op: 'edit'; txId: number; markedDelete: boolean; addedViaPicker?: boolean; }
) & { tempId: string; fields: DraftFields; } & PartnerDisplay;
```

### Key Principles

1. **Zero-copy originals**: original is ALWAYS `txStoreGet(op.txId)`, never stored on the op
2. **Status always derived**: `deriveStatus(op)` computes from diff — never a stored field
3. **Tagged discriminator**: `op.op === 'create'` → has `link_uuid`; `op.op === 'edit'` → has `txId`, `markedDelete`
4. **Factory functions replace fromTx()**: `fieldsFromTx()` (pure extraction), `editOpFromTx()` (edit factory), `createOpFromClone()` (clone factory)
5. **Clone over add-row for testing**: clone action preferred for testing `row-appended` because it avoids FormModal validation complexity

## Consequences

- **Type safety**: impossible to access `txId` on a create op (compile error)
- **Plan D unblocked**: Split = `markedDelete=true` on one side + `ops.push(createOpEmpty())` for detached side. Promote = two edit ops + shared `link_uuid`. ~10 LOC per action.
- **LOC**: 1819 → 1748 (−71, −4%) — quality improvement, not brute reduction
- **No external API change**: only `TransactionBulkModal.svelte` internal refactor; all E2E tests pass unchanged
- **`data-action-id`**: added to DataTable for stable E2E selectors (complements `data-testid` rule)

## Links

- [[concepts/txstore-pattern]]
- [[decisions/txstore-single-source-of-truth]]
- Source: `LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part4_Round6_PlanC3_PendingOpRefactor.prompt.md`
- Implementation: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`



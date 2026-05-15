---
title: "Phase 07 Part 4 Round 6 Plan C3 — PendingOp Refactor (DraftRow → PendingOp tagged union)"
category: source
source_type: plan
date_ingested: 2026-05-30
original_path: LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/plan-phase07-transaction-Part4_Round6_PlanC3_PendingOpRefactor.prompt.md
tags: [phase07, transactions, bulkModal, pendingOp, tagged-union, refactor, e2e, data-action-id]
related:
  - sources/phase07-part4-round6-planc-txstore-refactor
  - decisions/txstore-single-source-of-truth
  - decisions/pendingop-tagged-union
  - concepts/txstore-pattern
  - concepts/e2e-data-testid-rule
  - features/F-048
---

# Source: Plan C3 — PendingOp Refactor (DraftRow → PendingOp tagged union)

## Summary

Plan C3 completes the architectural migration of `TransactionBulkModal.svelte` from 80% to 100% of the txStore-based architecture. It replaces the legacy `DraftRow` flat interface (27 cloned fields + `original?` + `status`) with a proper `PendingOp` tagged union (`create` | `edit`) composed of `DraftFields` + `PartnerDisplay`. The plan eliminates `fromTx()` (full-clone factory), removes dead legacy props, renames `drafts` → `ops`, and tightens `_partnerFormPayload` from `Record<string,unknown>` to `TxFields | null`. Additionally, 3 new E2E tests were added as Plan D prerequisites, and `data-action-id` was introduced on DataTable action buttons for i18n-resilient test selectors.

## Key Takeaways

- **DraftRow eliminated**: replaced by `PendingOp` (tagged union) + `DraftFields` (pure editable data) + `PartnerDisplay` (partner rendering data)
- **Zero-copy originals**: `d.original` removed entirely — the original is always `txStoreGet(op.txId)`, never stored on the op
- **Tagged union discriminator**: `op.op === 'create' | 'edit'` enables type-safe branching — `create` has `link_uuid`, `edit` has `txId` + `markedDelete`
- **Status always derived**: `deriveStatus(op)` computes status from diff vs txStore — never stored as a field
- **fromTx() eliminated**: split into `fieldsFromTx()` (pure field extraction) + `editOpFromTx()` (edit op factory) + `createOpFromClone()` (clone factory)
- **Rename `drafts` → `ops`**: global rename (~80 occurrences) for semantic clarity
- **Legacy props removed**: `initialRows`, `autoOpenForm`, `initialStatus` — dead code since Plan C
- **Type tightening**: `_partnerFormPayload: Record<string,unknown>` → `partnerPayload: TxFields | null`
- **LOC**: 1819 → 1748 (−71, −4%) — modest reduction because the value is structural quality, not brute LOC savings
- **3 new E2E tests**: picker add/remove, reset-all, CSS status classes — all Plan D prerequisites
- **`data-action-id` attribute**: added to DataTable `<button class="action-btn">` for stable i18n-resilient selectors

## Architectural Mirror (Before vs After)

The plan documents the complete transformation from the original 3-copy architecture:

**Before (pre-Plan C)**: `+page.svelte` held `allMainRows` + `allPartnerRows` + `bulkInitial` (3 copies), BulkModal held `DraftRow[]` with 27 cloned fields + `original?` copy. `fromTx()` cloned entire `TXReadItem` → `DraftRow`. Status set manually. `link_uuid` generated in 4+ points.

**After (post-C3)**: `+page.svelte` passes only `WorkspaceIntent` ({action, txIds}). `txStore` is the single source of truth. BulkModal holds `PendingOp[]` — minimal typed operations. Status derived from diff. Partners resolved via `txStoreGet(op.txId)`. Zero copies of originals.

## Decisions Captured

1. [[decisions/pendingop-tagged-union]] — PendingOp as `create | edit` tagged union with DraftFields + PartnerDisplay composition
2. `data-action-id` on DataTable for i18n-resilient E2E selectors (extends [[concepts/e2e-data-testid-rule]])

## Wiki Pages Updated

- [[features/F-048]] — PendingOp architecture, Plan C3 completion, 3 new E2E tests
- [[concepts/txstore-pattern]] — PendingOp model updated to reflect actual implementation
- [[concepts/e2e-data-testid-rule]] — `data-action-id` pattern added
- [[decisions/pendingop-tagged-union]] — new decision page



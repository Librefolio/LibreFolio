---
title: "Phase 07 Part 4 Round 6 Plan C — txStore Refactor"
category: source
source_type: plan
date_ingested: 2026-05-29
original_path: LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part4_Round6_PlanC_TxStoreRefactor.prompt.md
tags: [phase07, transactions, txStore, refactor, frontend, svelte5, single-source-of-truth]
related:
  - sources/phase07-part4-round6-planb23-bulk-delete
  - sources/phase07-part4-round6-planb23-appendix1-ui-polish
  - concepts/txstore-pattern
  - decisions/txstore-single-source-of-truth
  - features/F-048
---

# Source: Phase 07 Part 4 Round 6 Plan C — txStore Refactor

## Summary

Architectural refactor introducing `txStore.svelte.ts` as the single source of truth for all loaded transactions. The store replaces the fragile 3-copy prop cascade (`allMainRows`/`allPartnerRows` passed down to BulkModal/PickerModal). BulkModal now holds only "pending operations" (create/edit/delete instructions) and derives row status automatically by diffing against the store. Completed 2026-05-08 with all E2E tests passing.

## Key Takeaways

- **Root cause analysis**: identified 5 categories of recurring bugs all caused by multiple copies of transaction data diverging after mutations (link_uuid fragile, "edited" falso, dati duplicati/stale, paired split dopo reset, props cascade viewer-only)
- **txStore architecture**: `Map<number, TXReadItem>` populated once via `reload()` → `setAll(main, partners)`. Provides `get()`, `getPartner()`, `getAll()`, `getFiltered()`, `canEdit()`, `invalidate()`
- **WorkspaceIntent pattern**: toolbar actions pass `{action, txIds}` to BulkModal instead of full data objects. Actions: create, edit, delete, clone
- **PendingOp model**: BulkModal holds `Array<PendingOp>` where each op is `{op: 'create'|'edit'|'delete', ...}`. Status derived from diff vs txStore
- **Interface deduplication** (Step 6a): created `frontend/src/lib/components/transactions/types.ts` as canonical source for TXReadItem, ValidationIssue, AssetEvent interfaces
- **LOC reduction**: BulkModal -30% (1766→~1200), +page.svelte -30% (1035→~700), txStore ~120 LOC added
- **26 use cases covered** with architecture: CREATE(3), EDIT(5), CLONE(2), DELETE(5), PICKER(3), RESET(4), VALIDATE(2), COMMIT(2) + 2 future (Piano D: Split/Promote)
- **Migration was incremental**: Step 1 (create store) → Step 2 (migrate Picker) → Step 3 (migrate BulkModal) → Step 4 (simplify +page) → Step 5 (full E2E) → Step 6 (polish)
- **Execution order update**: in master plan Round 6, old "Piano C" (Split/Promote) renamed to "Piano D"; this txStore plan inserted as new "Piano C" prerequisite

## Wiki Pages Updated

- [[concepts/txstore-pattern]] — new: documents the txStore architecture and its relationship to entityStore
- [[decisions/txstore-single-source-of-truth]] — new: decision to replace prop cascade with centralized store
- [[features/F-048]] — updated: txStore refactor, Step 6 polish, Round 6 Plan C completion


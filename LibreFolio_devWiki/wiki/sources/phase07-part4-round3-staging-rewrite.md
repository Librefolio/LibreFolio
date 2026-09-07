---
title: "Phase 7 Part 4 Round 3 — Staging Modal Greenfield Rewrite"
category: source
source_type: plan
date_ingested: 2026-05-25
original_path: LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round1-3/plan-phase07-transaction-Part4_Round3-stagingModalRewrite.prompt.md
tags: [phase07, transactions, frontend, modal, staging, formModal, bulkModal, promoteWizard, datatable, editable-cells, validate-scheduler, CompactCashCell, transactionTypeRules]
related: [sources/phase07-part4-transactions-ui, sources/phase07-part4-round3-bugfix1, sources/phase07-part4-round3-bugfix2, features/F-048, concepts/validate-scheduler-pattern, concepts/editbuffer-pattern]
merged_from: [sources/phase07-part4-round3]
merged_on: 2026-09-01
---

> **Merged 2026-09-01.** `sources/phase07-part4-round3` was a near-duplicate of this
> page — same `original_path`, same `date_ingested`, same content in different words.
> It was one of the wiki's only two orphans. This page survives because it is the
> one the index and other pages link to; the rows below marked *(from the merged
> copy)* are the material the duplicate carried and this one did not.

# Source: Phase 7 Part 4 Round 3 — Staging Modal Greenfield Rewrite

## Summary
Complete rewrite of the transaction staging system from a monolithic `TransactionStagingModal` into three specialised components: `TransactionFormModal` (single-row CRUD + view), `TransactionBulkModal` (DataTable-based multi-row editor), and `PromotePairWizardModal` (3-step pair promotion wizard). Introduces `transactionTypeRules.ts` for UI field gating, `useValidateScheduler` for debounced validation, and `CompactCashCell.svelte` as a reusable numeric + currency input. All validation is 100% backend via `POST /transactions/validate`. Auto-validate disables above 50 rows.

## Key Takeaways
- **Three-component split**: FormModal (single-row), BulkModal (multi-row on DataTable), PromoteWizard (3-step pair promotion) — clear separation of concerns
- **Validate scheduler**: debounce 1s + idle 60s auto-fire + manual button; idle reset only on real changes; auto-disable above N>50 rows
- **CompactCashCell**: generic reusable `[amount input] [CurrencySearchSelect]` component in `lib/components/ui/`
- **Modal stacking**: BulkModal can open FormModal, PromoteWizard can open FormModal — max depth 3
- **Editable DataTable cells**: BulkModal uses EditableTextCell, EditableSelectCell, CustomCell wrapping SearchSelect components
- **DraftRow pattern**: `{tempId, status: 'new'|'edited'|'original', original?, draft}` — write to local `next` BEFORE assigning to `$state` to avoid Svelte 5 read-write loops
- **Type rules gating** *(from the merged copy)*: `transactionTypeRules.ts` maps each `TransactionType` to a `TypeRule` with `assetField`, `cashField`, `quantityRule`, `cashSign`, `eventLinkable`, `requiresPair` — **UI-only**; the backend remains the source of truth for actual validation. Superseded in Round 5, which replaced this file with a server-driven store: see [[sources/phase07-part4-round5-server-type-rules]]
- **Legacy deleted** *(from the merged copy)*: `TransactionStagingModal.svelte` and `TransferPromoteModal.svelte` were removed by this round — which is why later pages citing those two paths point at files that no longer exist
- **DataTable reuse** *(from the merged copy)*: all three modals reuse the existing DataTable, the editable cell types and `ColumnVisibilityToggle` rather than growing their own table

## Wiki Pages Updated
- [[features/F-048]] — updated to reflect three-component architecture
- [[concepts/validate-scheduler-pattern]] — new concept page
- [[sources/phase07-part4-round3-bugfix1]], [[sources/phase07-part4-round3-bugfix2]] — the follow-up rounds *(link carried over from the merged copy)*

## Source files

| Role | Path |
|------|------|
| Single-row form | `frontend/src/lib/components/transactions/modals/TransactionFormModal.svelte` |
| Multi-row bulk editor | `frontend/src/lib/components/transactions/modals/TransactionBulkModal.svelte` |
| Compact cash input | `frontend/src/lib/components/ui/display/CompactCashCell.svelte` |
| Validate scheduler | `frontend/src/lib/utils/transactions/useValidateScheduler.svelte.ts` |
| Original plan | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round1-3/plan-phase07-transaction-Part4_Round3-stagingModalRewrite.prompt.md` |

> `PromotePairWizardModal.svelte`, `TransactionStagingModal.svelte` and
> `TransferPromoteModal.svelte` are deliberately **not** listed: the first was
> renamed/absorbed and the last two were deleted by this very round.


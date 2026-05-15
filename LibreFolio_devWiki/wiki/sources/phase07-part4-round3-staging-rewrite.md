---
title: "Phase 7 Part 4 Round 3 — Staging Modal Greenfield Rewrite"
category: source
source_type: plan
date_ingested: 2026-05-25
original_path: LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round1-3/plan-phase07-transaction-Part4_Round3-stagingModalRewrite.prompt.md
tags: [phase07, transactions, frontend, formModal, bulkModal, promoteWizard, validate-scheduler, CompactCashCell, transactionTypeRules]
related: [sources/phase07-part4-transactions-ui, features/F-048, concepts/validate-scheduler-pattern, concepts/editbuffer-pattern]
---

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

## Wiki Pages Updated
- [[features/F-048]] — updated to reflect three-component architecture
- [[concepts/validate-scheduler-pattern]] — new concept page


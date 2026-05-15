---
title: "Phase 07 Part 4 Round 3 — Staging Modal Greenfield Rewrite"
category: source
source_type: plan
date_ingested: 2026-05-25
original_path: LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round1-3/plan-phase07-transaction-Part4_Round3-stagingModalRewrite.prompt.md
tags: [phase07, transactions, frontend, modal, staging, formModal, bulkModal, promoteWizard, datatable, editable-cells]
related: [sources/phase07-part4-round3-bugfix1, sources/phase07-part4-round3-bugfix2, features/F-048, concepts/validate-scheduler-pattern]
---

# Source: Phase 07 Part 4 Round 3 — Staging Modal Greenfield Rewrite

## Summary

Complete rewrite of the transaction staging system, splitting the monolithic `TransactionStagingModal` into three specialised components: **TransactionFormModal** (single-row CRUD), **TransactionBulkModal** (DataTable-based multi-row bulk edit with editable cells), and **PromotePairWizardModal** (3-step wizard for promoting DEPOSIT/WITHDRAWAL pairs to TRANSFER/FX_CONVERSION). Introduces `transactionTypeRules.ts` (UI gating per type), `useValidateScheduler` (debounce 1s + idle 60s + manual), and `CompactCashCell.svelte` (numeric input + compact CurrencySearchSelect). All three modals reuse the existing DataTable, editable cell types, and ColumnVisibilityToggle.

## Key Takeaways

- **Three-component split**: FormModal for single-row, BulkModal for N-row DataTable-based bulk, PromoteWizard for pair promotion with 3 sources (in-bulk, saved, create-new)
- **Validate scheduler**: debounce 1s on change + idle auto-fire every 60s + manual button always available; auto-validate disabled when N > 50 rows; idle timer reset only on real change (not manual validate click)
- **`CompactCashCell`**: generic reusable component combining numeric input + `CurrencySearchSelect` compact; emits `{amount, code} | null`
- **Type rules gating**: `transactionTypeRules.ts` maps each `TransactionType` to a `TypeRule` with `assetField`, `cashField`, `quantityRule`, `cashSign`, `eventLinkable`, `requiresPair` — UI-only (backend remains source of truth for actual validation)
- **Modal stacking**: FormModal can be opened from within BulkModal and PromoteWizard (max depth 3); pair-partner chip in FormModal opens a read-only view as stack-modal
- **Legacy deleted**: `TransactionStagingModal.svelte` and `TransferPromoteModal.svelte` removed

## Wiki Pages Updated

- [[features/F-048]] — status updated, three-component architecture documented
- [[concepts/validate-scheduler-pattern]] — new concept page


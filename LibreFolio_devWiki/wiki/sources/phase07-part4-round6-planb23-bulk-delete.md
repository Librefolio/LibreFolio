---
title: "Phase 07 Part 4 Round 6 — Plan B23: Bulk Delete via BulkModal + Mode Removal"
category: source
source_type: plan
date_ingested: 2026-05-27
original_path: LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/plan-phase07-transaction-Part4_Round6_PlanB23_BulkDeleteViaBulkModal.prompt.md
tags: [phase07, transactions, bulkModal, deleteModal, mode-removal, bulk-delete, picker-guard, e2e]
related:
  - sources/phase07-part4-round3-staging-rewrite
  - sources/phase07-part4-round5-server-type-rules
  - decisions/bulkmodal-mode-removal
  - features/F-048
  - features/F-047
---

# Source: Phase 07 Part 4 Round 6 — Plan B23: Bulk Delete via BulkModal + Mode Removal

## Summary
Plan B23 (completed 2026-05-07) eliminated `BulkDeleteLinkedPairModal` by routing bulk delete through `TransactionBulkModal` with `initialStatus: 'delete'`. All rows start marked for deletion but can be individually restored, edited, cloned, or augmented — reusing the full bulk infrastructure. Follow-up work removed the `mode` prop (`'create-many' | 'edit-many'`) from BulkModal entirely, making it a mode-less unified batch editor where each row's role is inferred from `tx.id > 0`.

## Key Takeaways
- **BulkDeleteLinkedPairModal removed**: replaced by `TransactionBulkModal` with `initialStatus: 'delete'`; rows pre-marked delete can be restored/edited/cloned from the same batch
- **TransactionDeleteModal enriched**: no longer a simple confirm dialog — has `errors[]` prop, `resolveIssueMessage()` for rich error banners, "⚡ Validate now" button, green "can be deleted safely" banner, success toast with icons (type icon, broker icon, role SVG)
- **PickerModal guard**: non-editable rows (VIEWER broker, no role) get disabled checkbox (⊘ icon + tooltip), select-all skips them, dblclick/long-press toggle added
- **Confirm edit on delete row**: editing a row marked for deletion shows a ConfirmModal ("Restore & Edit?") before opening FormModal
- **Mode removal (follow-up)**: `mode` prop removed from BulkModal + `bulkMode` state removed from `+page.svelte`. Each row infers create vs edit from `tx.id > 0`. Dead code `editMode` removed. `mergePairedRows` conditioned on `rows.some(r => r.id > 0 && r.related_transaction_id != null)` instead of mode string. ~25 lines of code removed.
- **E2E test suite**: `tx-delete.spec.ts` added covering layouts A/B/C, bulk delete flow, error banners, picker guard
- **i18n**: 7 new keys in 4 languages

## Wiki Pages Updated
- [[decisions/bulkmodal-mode-removal]] — created (mode removal rationale and consequences)
- [[features/F-048]] — updated (mode-less architecture, delete flow, enriched DeleteModal)
- [[features/F-047]] — updated (BulkDeleteLinkedPairModal removed)
- [[connections/transactions-connections]] — updated (Round 6 status)
- [[domains/transactions]] — updated


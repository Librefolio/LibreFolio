---
title: "R2 SP-C — BulkModal UX Polish + Suggest Overhaul + Modal Cleanup"
category: source
source_type: plan
date_ingested: 2026-06-01
original_path: LibreFolio_developer_journal/RoadmapV4_UI/PlanD_SplitPromoteFullStack/R2-WalktestFeedback/plan-R2-SP-C-BulkModalSuggestUX.prompt.md
tags: [phase07, transactions, frontend, bulkModal, suggest, promote, split, ux, e2e]
related:
  - sources/r2-walktest-feedback-master
  - sources/r2-sp-a-cost-basis-wac
  - sources/r2-sp-b-backend-tests
  - features/F-048
  - features/F-097
---

# Source: R2 SP-C — BulkModal UX Polish + Suggest Overhaul

## Summary
Frontend UX plan (✅ completed + BugfixRound1/2 all done by 2026-05-30) implementing Steps 7–12 and 17 from the master plan. Focuses on BulkModal toolbar alignment, split preview improvements, suggest banner overhaul (subtractive filter + human-readable format + lightbulb), PromoteMergeModal simplification, and TransactionActionModal enhancements.

## Key Takeaways

### BulkModal improvements (Steps 7–9)
- **Toolbar alignment**: left-group + right-group with `justify-between`; delta-days slider moved to left-group
- **Split edit opens as target type**: `handleEditRowClick()` checks `splitTxIdsSet.has(op.txId)` → overrides `formInitial.type` with SPLIT_TYPE_MAP target (sender=splitTypes[0], receiver=splitTypes[1])
- **Split type preview**: `[original icon] → [target icon + label]` — no original label, correct sender/receiver type determination via qty sign

### Suggest overhaul (Step 10)
- **Subtractive filter**: exclude DB candidates whose `id` is already in `ops[]` (edit rows)
- **Human-readable format**: `• [🔗 Merge] Row#N (icon) and DB#ID (icon) → Target (icon) (ΔNd)` — multi-match nested `<ul>`
- **Lightbulb per-row**: row action icon (Lightbulb from lucide-svelte) when standalone row has suggestions; click → scroll to banner + flash
- **Banner visibility condition**: only shown when ≥1 suggested TX is loaded in grid (`ops[]`)

### PromoteMergeModal simplified (Step 11)
- **Removed fields**: date and cost_basis (resolved in FormModal post-promote)
- **Only description and tags remain** as merge resolution fields
- **Button layout**: `◀ All Left | ⟷ (icon only) | All Right ▶`; footer `justify-between`

### TransactionActionModal (Step 12)
- **Split BEFORE**: type shown on both From and To columns (icon+label) instead of single colspan=2
- **Split AFTER**: added missing rows — quantity, tags, description

### BulkModal paired column (Step 17)
- Format: `#62 ↔ #63` for paired transactions

### SP-C Bugfix rounds (completed)
- BugfixRound1: 12 bugs from walktest feedback
- BugfixRound2: WAC Preview modal (FormModal post-commit info display) + 11 additional bugs

## Source files
| Role | Path |
|------|------|
| BulkModal | `frontend/src/lib/components/transactions/TransactionBulkModal.svelte` |
| PromoteMergeModal | `frontend/src/lib/components/transactions/PromoteMergeModal.svelte` |
| TransactionActionModal | `frontend/src/lib/components/transactions/TransactionActionModal.svelte` |
| FormModal | `frontend/src/lib/components/transactions/TransactionFormModal.svelte` |
| E2E split/promote | `frontend/e2e/transactions/tx-split-promote.spec.ts` |
| E2E bulk operations | `frontend/e2e/transactions/tx-bulk-operations.spec.ts` |
| Test runner registration | `scripts/test_runner/_frontend_transaction.py` |

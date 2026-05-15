---
title: "Phase 07 Part 4 Round 5 Bugfix 2 — Post-TestWalk Overhaul"
category: source
source_type: plan
date_ingested: 2026-05-28
original_path: LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round4-5/plan-phase07-transaction-Part4_Round5_Bugfix2_PostTestWalkOverhaul.prompt.md
tags: [phase07, transactions, bulkModal, formModal, readonly, dual-dates, i18n, mkdocs]
related:
  - sources/phase07-part4-round5-bugfix1-dual-form
  - features/F-048
---

# Source: Phase 07 Part 4 Round 5 Bugfix 2 — Post-TestWalk Overhaul

## Summary
Major architectural refactor making BulkModal fully readonly (FormModal is the sole editing point). Adds "✓ Applica" button label for embedded FormModal, dual dates in paired forms, edit/clone routing from main table through BulkModal→FormModal, and mkdocs documentation for transaction types (EN only). 14 steps all completed.

## Key Takeaways
- **BulkModal fully readonly**: all cells display-only; double-click opens FormModal for editing. `commitOnSave=false` pattern for nested FormModal
- **"✓ Applica" button**: FormModal shows "Apply" instead of "Save" when embedded in BulkModal
- **Dual dates**: each side of a paired form (Da/A) can have its own date via `DualDraftTo.date`
- **Edit/Clone routing**: single edit/clone from main table opens BulkModal→FormModal (removed standalone FormModal from +page.svelte)
- **BulkDeleteLinkedPairModal i18n**: added missing translation keys for 4 locales
- **FX dual form overflow fix**: `min-w-0` on CompactCashCell container
- **Validation banner → inline footer**: success indicator moved to footer between Verify and Save buttons
- **mkdocs documentation**: `transfer.en.md` restructured for TRANSFER, CASH_TRANSFER, FX_CONVERSION, ADJUSTMENT

## Wiki Pages Updated
- [[features/F-048]] — readonly BulkModal, dual dates, Apply button


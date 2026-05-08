---
title: "Phase 07 Part 4 Round 5 Bugfix 1 — Dual Form & Unified BulkModal Fixes"
category: source
source_type: plan
date_ingested: 2026-05-28
original_path: LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part4_Round5_Bugfix1_DualFormAndBulkFixes.prompt.md
tags: [phase07, transactions, dual-form, bulkModal, cash-transfer, split, promote, paired-row]
related:
  - sources/phase07-part4-round5-server-type-rules
  - decisions/cash-transfer-split-promote
  - features/F-048
  - features/F-046
---

# Source: Phase 07 Part 4 Round 5 Bugfix 1 — Dual Form & Unified BulkModal Fixes

## Summary
Bugfix round addressing blocking issues from the dual-form + unified BulkModal implementation. Adds `CASH_TRANSFER` as a first-class backend enum value (Opzione C approved), establishes Split/Promote as immediate dedicated endpoints (not deferred in batch), removes `PromotePairWizardModal` in favour of selection-based promote flow, and implements paired row rendering in BulkModal with `Da:/A:` labels. Server-driven split/promote metadata schemas added to `TXTypeMetadata`.

## Key Takeaways
- **CASH_TRANSFER first-class type**: `TRANSFER`, `FX_CONVERSION`, `CASH_TRANSFER` all first-class backend enum values with same-type pairing (removes `VALID_MIXED_PAIRS` hack)
- **Split/Promote immediate**: dedicated `POST /transactions/split` and `POST /transactions/promote` endpoints; structural transformations are always immediate, not deferred in batch. ⚠️ Backend endpoints NOT actually implemented in this round — schemas only; moved to Round 6 Step 10
- **Server-driven metadata**: `SplitMeta`, `PromoteRule`, `PairFieldConstraint` schemas added to `TXTypeMetadata` — frontend reads split_into/promote_from/pair_field_constraints instead of hardcoding rules
- **Paired row rendering**: BulkModal renders paired rows as double-height with `Da:/A:` labels per column (broker split for transfers, cash split for FX)
- **PromotePairWizardModal removed**: replaced by selection-based flow (select 2 rows → 🔗 action → ConfirmModal)
- **SearchSelect "Create new" footer**: `createLabel` + `onCreateNew` props for inline entity creation from dropdowns
- **15/17 steps completed**: B1-16 (bulk split/promote endpoints) and B1-17 replacement flow deferred to Round 6

## Wiki Pages Updated
- [[features/F-048]] — CASH_TRANSFER, split/promote architecture, paired rendering
- [[features/F-046]] — CASH_TRANSFER enum addition
- [[decisions/cash-transfer-split-promote]] — created


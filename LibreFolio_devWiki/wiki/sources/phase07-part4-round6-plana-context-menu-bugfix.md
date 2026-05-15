---
title: "Phase 07 Part 4 Round 6 Plan A — ContextMenu + Bugfix R7-C1/H1"
category: source
source_type: plan
date_ingested: 2026-05-28
original_path: LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/plan-phase07-transaction-Part4_Round6_PlanA_ContextMenuBugfix.prompt.md
tags: [phase07, transactions, context-menu, bugfix, paired-edit, type-swap, txPayloadHelpers]
related:
  - sources/phase07-part4-round6-context-menu-delete
  - features/F-047
  - features/F-048
  - problems/dual-form-collect-duplication
---

# Source: Phase 07 Part 4 Round 6 Plan A — ContextMenu + Bugfix R7-C1/H1

## Summary
Implements ContextMenu.svelte as reusable UI component integrated into DataTable, fixes the critical R7-C1 bug (edit paired creates partner as new instead of updating), and fixes R7-H1 (type swap qty not propagating). Through 6 rounds of test feedback, also discovers and fixes the root cause of duplicated collect logic between FormModal and BulkModal, leading to creation of `txPayloadHelpers.ts` shared utility.

## Key Takeaways
- **ContextMenu integration**: `oncontextmenu` handler on `<tr>` rows, fires natively on right-click (desktop) and long-press (mobile). Actions filtered by `visible?.(row)` same as action column
- **R7-C1 fix**: `patchDualRowFromForm()` in BulkModal now preserves `id`, `status:'edited'`, and `original` snapshot when applying dual form results to partner DB rows; searches existing partner draft before creating new one
- **R7-H1 fix**: `collectUpdate()` now calculates `origSignedQty` with `getTypeRule(orig.type)` (original type's rule), not current type's rule. Same fix applied to cash sign comparison
- **Root cause discovery**: FormModal and BulkModal had completely independent implementations of `collectCreate()`, `collectUpdate()`, `collectDualUpdates()`, `PATCHABLE_FIELDS`, and `fieldEq()`/`diffFields()` — causing 3 consecutive bugs (R7-C1, R7-H1, qty/description diff spurio)
- **txPayloadHelpers.ts created**: shared utility with `PATCHABLE_FIELDS`, `applySignRules()`, `buildCreatePayload()`, `buildUpdateDiff()`, `fieldEq()` — both modals import from single source
- **fieldEq() normalisation**: quantity comparison as `Number(a) === Number(b)`, cash as numeric amount + strict code, description/cost_basis_override normalise null/undefined/"" → "", tags as sorted array
- **BulkModal layout fixes**: broker column width 140→190px, type column 140→155px, ID column 70→90px, qty column 85→110px; type icon matched to 1.75rem; paired qty shows Da:-qty📉 / A:+qty📈
- **Soft reload pattern**: `reload({soft: true})` parameter added to preserve DataTable state after save operations
- **FormModal view→edit**: `onSwitchToEdit` prop; clicking ✏ in view mode closes standalone FormModal and invokes `handleEditRow()` → opens BulkModal in edit-many with autoOpenForm

## Wiki Pages Updated
- [[features/F-048]] — txPayloadHelpers.ts, R7-C1/H1 fixes, soft reload
- [[problems/dual-form-collect-duplication]] — created


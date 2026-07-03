---
title: "BulkModal row-selector toolbar hidden after BRIM import"
category: problem
status: open
date: 2026-06-25
tags: [frontend, bulk-modal, z-index, overflow, sticky, import, svelte5, css]
related:
  - sources/phase-final-bugs-2026-06-25
  - entities/import-wizard-modal
  - features/F-048
---

# Problem: BulkModal Row-Selector Toolbar Hidden After BRIM Import

## Symptom

After completing a BRIM import (ImportWizardModal → BulkModal receives the `TXCreateItem[]` rows), the row-selection toolbar (checkboxes + bulk action bar) does not appear. The DataTable renders the imported rows but the selection UI is absent or clipped.

## Root Cause

The `TransactionBulkModal` DataTable is wrapped in a `<div class="flex-1 min-h-0 overflow-y-auto">` container (L3014). The inline toolbar (L2969–2980) is positioned as a sticky/embedded bar inside this flex container.

The problem: `overflow-y: auto` creates a **stacking context** that clips any `position: absolute` or `position: sticky` children that exceed the scroll boundary. Specifically:
- Checkboxes in DataTable rows use `position: absolute` or float out of flow
- The selection toolbar uses `position: sticky` or inline placement
- After import, the scroll position + container height combination causes the toolbar to be clipped or to compute `selectionBar.length > 0` = false (because `onSelectionChange` is not propagating)

Two possible root causes:
1. **CSS clipping**: `overflow-y: auto` clips `position: sticky` toolbar and `position: absolute` checkboxes
2. **Missing propagation**: `onSelectionChange` callback from DataTable doesn't update `bulkTableSelectedRows` after import-triggered row creation

## Solution (proposed)

1. **CSS fix**: Add `overflow: visible` or `isolation: isolate` to the DataTable wrapper in BulkModal. Or use `overflow: clip` instead of `overflow: auto` (clips scroll without affecting stacking context).
2. **Propagation fix**: Verify that `onSelectionChange` correctly triggers after `pendingOps` is updated from import. May need a reactive effect to re-initialize selection state after import batch.

## Prevention

When embedding a DataTable inside a scrollable modal container, verify: (1) selection toolbar is not clipped; (2) sticky row elements maintain z-index above the container. Use `overflow: clip` when scroll clipping is needed but stacking context should be preserved.

## Impact

After importing transactions, users cannot bulk-select rows, bulk-delete, or perform other multi-row operations. They must close and re-open BulkModal to get a working selection UI.

## Source files

| Role | Path |
|------|------|
| TransactionBulkModal | `frontend/src/lib/components/transactions/modals/TransactionBulkModal.svelte` |
| DataTable component | `frontend/src/lib/components/ui/DataTable.svelte` |

---
title: "DataTable Enum Filter Options Disappear When Count Reaches Zero"
category: problem
tags: [frontend, datatable, filter, enum, svelte5]
severity: medium
resolved: true
date: 2026-04-28
related:
  - features/F-047
  - sources/phase07-part4-round1
---

# Problem: DataTable Enum Filter Options Disappear When Count Reaches Zero

## Symptom

A column with enum filtering (e.g. `transaction_type`) shows checkboxes for each option with a count badge. When the user selects a filter value that reduces certain options' counts to zero, those options disappear from the checkbox list — making it **impossible to deselect them** (user is stuck with the filter applied and can't undo it through the UI).

## Root Cause

In `DataTable.svelte`, `getEnumOptionsWithCounts()` was computing options from the **currently visible rows** and calling `.filter(o => o.count > 0)`. This removed zero-count options dynamically as the filter narrowed down results. An option that is selected but no longer visible becomes un-selectable.

```ts
// Buggy version:
return enumOptions
    .map(opt => ({ ...opt, count: filteredRows.filter(...).length }))
    .filter(o => o.count > 0);   // ← BUG: removes selected-but-zero options
```

## Fix

Remove the `.filter(o => o.count > 0)`. The set of available options is defined **entirely by the parent** via the `enumOptions` prop, not by current counts. Counts are decorative feedback (show how many match), never used for visibility.

```ts
// Fixed version:
return enumOptions
    .map(opt => ({ ...opt, count: filteredRows.filter(...).length }));
// ← No filter: options always match what parent passed
```

## Rule

> Enum filter options in DataTable are always determined by the parent (`enumOptions` prop). Counts update reactively but must NEVER control option visibility. A zero-count option with a checkbox checked must remain visible.

## Affected File

- `frontend/src/lib/components/table/DataTable.svelte` (W73/C18, Round 1)

## Source

W73/C18 documented in:
`LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part4_Round1-tableRefactorBugfix.prompt.md`, sub-round 1.12.

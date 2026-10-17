---
title: "DataTable pruned the saved preferences of columns absent for a moment"
category: "problem"
status: resolved
date: 2026-10-17
tags: ["frontend", "datatable", "preferences", "localStorage", "async"]
related: ["problems/datatable-net-columns-hidden-override-model", "concepts/dual-view-pattern", "domains/assets", "domains/fx"]
---

# Problem: DataTable pruned the saved preferences of columns absent for a moment

## Summary
`DataTable.svelte` treated a column missing from `columns` as gone for good: it removed it from the saved column
order (and saved at once), dropped its visibility override and its width. Once X-R53 (17/10/2026) made the Assets and
FX tables' Δ period columns (`delta_1W…delta_5Y`) arrive only after the backend lists the periods, the first render
never had them, so every page load reset the user's place, visibility and width for those columns. Y-27 keeps the
preferences of absent columns and filters them only when drawing.

## Details
- **Symptom**: a hidden Δ 5Y column visible again after every reload; a Δ column moved next to the name back in its
  default place; a widened one back at 80 px. Before X-R53 it happened only when a shorter date range hid the long
  periods and a longer one brought them back.
- **Root cause**, three spots, each harmless while the column list is complete at the first render:
  - `onMount` loaded the stored visibility overrides **filtered on the columns present at mount** — the drop stayed in
    memory, so the stored choice was ignored on every load and lost at the next visibility save;
  - the sync `$effect` removed absent ids from `columnOrder` and **saved at once**, pruned their overrides and deleted
    their widths;
  - `reorderColumns`, fed by `ColumnVisibilityToggle` with the columns on screen only, would have saved an order
    without the absent ones too.
- **Fix (Y-27)**: two pure functions in `dataTableLogic.ts` — `withNewColumns(order, columnIds)` adds only ids never
  seen, at their natural place, leaving absent ids where they are; `reorderKeepingAbsent(previousOrder, newOrder,
  columnIds)` puts an absent id back after the one it followed. `onMount` keeps every stored override; the effect
  prunes nothing and gives a default width only to a column without a saved one. `orderedColumns` and
  `columnVisibility` already read only the columns present, so absent ids never reach the screen.
  `resetColumnLayout()` still returns to the defaults of the columns present (and so forgets the absent ones).
- **Why it stayed hidden**: no test pinned the pruning, and none could see it: `DataTable.test.ts` ran without
  `localStorage`. The Y-27 cases stub one per case.
- **Rule**: a column list that can be incomplete at the first render (backend-listed columns, data-dependent ones)
  must never cause a write of the user's layout. Persisted ids of absent columns are bounded today (`delta_*` only);
  a table whose column ids came from unbounded data would need a cap.

## Source files
| Role | Path |
|------|------|
| Persistence, sync effect, reorder | `frontend/src/lib/components/table/DataTable.svelte` |
| `withNewColumns`, `reorderKeepingAbsent` | `frontend/src/lib/components/table/dataTableLogic.ts` |
| Unit cases | `frontend/src/lib/components/table/dataTableLogic.test.ts` |
| Wiring cases with a stubbed `localStorage` | `frontend/src/lib/components/table/DataTable.test.ts` |
| The chooser that reorders the columns on screen | `frontend/src/lib/components/table/ColumnVisibilityToggle.svelte` |
| The Δ period columns from the backend (X-R53) | `frontend/src/lib/utils/periodChanges.ts` |
| Developer page | `mkdocs_src/docs/developer/frontend/components/core-ui/data-table.md` |
| Plan, «Y-27» | `LibreFolio_developer_journal/Release_2/Phase_1/09_dashboardCharts/plan-phase01DashboardCharts.prompt.md` |

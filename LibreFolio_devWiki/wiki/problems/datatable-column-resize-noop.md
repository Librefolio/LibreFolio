---
title: "DataTable column resize did not follow the pointer: auto-layout tables, the configured start width, and a mouse-only handle"
category: problem
status: resolved
date: 2026-07-07
updated: 2026-10-15
tags: [frontend, datatable, svelte5, ui, low-priority, pre-existing]
related:
  - problems/datatable-actions-column-on-mobile
  - sources/phase09-m1-m2-archive-2026-07
---

# Problem: DataTable column resize did not follow the pointer

## Symptom

`DataTable.svelte`'s per-column resize handle (the draggable divider shown on `th:hover`) renders correctly
(cursor changes to `col-resize`, the handle highlights), but dragging it produces no visible change to the
column width in some tables that use the component. Discovered during the exhaustive verification pass before
archiving Phase 09 Milestone 1 & 2 (2026-07-07). Unrelated to the dashboard/portfolio-engine work — a
pre-existing frontend gap noticed in passing.

## Root Cause — measured (Y7, 2026-10-15)

The first hypotheses were wrong: the width lives inside the table (`columnWidths`, saved in `localStorage`),
`onColumnResize` is an optional notification, and no consumer snapped it back. Three causes, measured with the E2E
`layout/datatable-resize.spec.ts` before the cure:

- **A table laid out `auto` treats a width as a preference.** `DataTable` writes the width only as the header cell's
  inline `width`; with `tableLayout="auto"` (11 resizable tables: the PAC's, the import wizard's, `MeasurePanel`,
  `ScheduledInvestmentEditor`, the Files list…) and `width: 100%`, the browser shares the table's spare width among the
  columns in proportion to their widths. At 1280 px on the Files list a +80 px drag moved the column by +57.0 px, a
  −40 px drag by −27.2. On a phone the same table is wider than its box and draws every column at its minimum: a drag
  moved nothing there.
- **The drag started from the configured width** (`columnWidths[id] || column.width`), not the drawn one (250 against
  279.6 px on that column).
- **The handle listened to `mousedown` only**: a finger could not resize (+0.0 px for a +60 px touch drag).

The Risk Lab's L1° table (the 2026-10-12 re-check) is fixed and wider than its box, so it draws every width as given:
that is why the drag worked there.

## Solution (Y7, 2026-10-15, decision D-Y18)

- The handle answers Pointer Events, with pointer capture, and `touch-action: none` keeps a finger drag from panning
  the table.
- The drag starts from the drawn width, and the drawn width follows the pointer: `fitDrawnWidth()` writes a width on
  the header cell, measures it and corrects it (a drawn/given scaling, then secant steps) until the drawn width matches.
  A plain `min-width` would not have been enough: on a table with spare width the spare goes back to the dragged column
  too.
- A column whose width differs from its default (`columnMinWidth()`) also gets it as `min-width`, so an auto-layout
  table keeps it on a narrow screen. The defaults stay untouched, so a table nobody resized lays out as before.

Proof: `front-utility datatable-resize`, 2 red → 4/4 green (mouse on the auto-layout Files list at 1280 px, and at
390 px where the table is wider than its box and its scroll width must grow with the column; finger on the fixed
transactions table; the fixed-layout control); `risk-lab` and `risk-analysis`, which drag the handle, stayed green.
Developer page: `core-ui/data-table.md`, «Column resize».

## Prevention

- Drag tests measure the **drawn** width against the drag, on an auto-layout table and on a fixed one.
- The E2E specs find the handle by what it is to the pointer (`cursor: col-resize`), never by its class: keep that
  cursor.

## Impact

Low, UX only: on the auto-layout tables the column edge lagged behind the pointer, and on a phone nothing moved.

## Re-check (2026-10-12)

Partly disproved: dragging a column's resize handle does widen it in the Risk Lab's L1° table, pinned by an E2E
(`frontend/e2e/portfolio/risk-lab.spec.ts`, the «value columns carry their help» test, added in `f55b2e42a`). No other
DataTable is drag-tested, so «some tables» stays open, to re-test after release 1.2 (backlog C-62).

## Source files

| Role | Path |
|------|------|
| Component (`startResize`, `fitDrawnWidth`, `columnMinWidth`) | `frontend/src/lib/components/table/DataTable.svelte` |
| Resize handle markup and its rules (cut out of `DataTable.svelte` in release 1.3, Y2; `startResize()` and the width state stay in the parent) | `frontend/src/lib/components/table/DataTableColumnHeader.svelte` |
| Resize E2E (D-Y18) | `frontend/e2e/layout/datatable-resize.spec.ts` |
| Developer page | `mkdocs_src/docs/developer/frontend/components/core-ui/data-table.md` |
| Workstream Y's plan (Y7) | `LibreFolio_developer_journal/Release_2/Phase_1/09_dashboardCharts/plan-phase01DashboardCharts.prompt.md` |

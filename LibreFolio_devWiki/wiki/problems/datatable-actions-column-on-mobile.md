---
title: "On a phone the DataTable's «Actions» header stayed pinned while the rows' ⋮ scrolled away, and the selection column covered the first data column"
category: problem
status: resolved
date: 2026-10-10
updated: 2026-10-15
tags: [frontend, datatable, mobile, css, sticky, specificity, gallery, pac-allocator, shared-component]
related:
  - features/F-107
  - problems/bulk-modal-sticky-z-index
  - problems/datatable-column-resize-noop
  - problems/select-list-under-the-sticky-table-header
  - sources/phase00-pac-implementation-2026-10
---

# Problem: the actions column on a narrow screen

## Symptom

Found by workstream M in the gallery's batch 9, on the PAC planner, in 8 combinations out of 8 (four languages, two
themes):

- **Defect 2** (`pac-step-review`, mobile): the table has an «Actions» header, but no ⋮ in its rows.
- **Defect 5** (`pac-step-targets`, mobile): the targets table does not fit the phone. Asset names are cut on the left
  («APL Apple Inc.»), the Target % inputs on the right — without their «%» — and «Actions» sits above the inputs.

## Root Cause — confirmed in a browser (Y7, 2026-10-15)

The reading of 2026-10-10 was right; the E2E `layout/datatable-mobile.spec.ts` turned it red at 390 px before the
cure (on the Files static list, which keeps the default sticky actions; the transactions table passes
`stickyActions={false}`, so its actions were already right):

- Below 768 px a media query makes the action cells static: `@media (max-width: 768px) { .th-actions, .td-actions
  { position: static; } }` in `DataTable.svelte`.
- The header cells, though, also match `thead.sticky-header th { position: sticky; … }` — `stickyHeader` defaults
  to `true` — and that selector is more specific than `.th-actions`. The header keeps `position: sticky` with
  `right: 0` (`.th-actions.th-fixed`): pinned to the right edge, while the cells carrying the ⋮ scroll out of view on
  the right.
- For the targets table, the declared widths add up to more than 500 px (selection 48, Asset at least 160,
  Distribution 200 with a minimum of 100, Target % 140 with a minimum of 128, actions 64), and the selection column is
  sticky on the left, so it can cover the names when the table scrolls.

## Solution (Y7, 2026-10-15, decision D-Y17)

At 768 px and below the selection and actions columns scroll with the table, header, body and footer cells alike. The
media query of `DataTable.svelte` makes the body cells `position: static` and takes only the horizontal pin off the
header cells (`left: auto; right: auto`): they keep `position: sticky; top: 0`, so the header row still sticks inside
its scroll area. Each override is one class more specific than the pin it undoes (`.datatable .th-actions.th-fixed`
against `.th-actions.th-fixed`, and so on) — the lesson of this defect: a bare class cannot undo a pin that a
`thead … th` rule carries.

Proof: `front-utility datatable-mobile`, 3 red → 6/6 green (actions and selection on the Files list, selection on the
transactions table, plus two guards on the header's stickiness); `files`, `transactions-table`, `asset-list`, `fx-bulk`
and `designer-lab picker` stayed green. The cure is documented in the developer page `core-ui/data-table.md`
(«Sticky columns»).

## Status

Resolved for `DataTable` (Y7, the 1.3 phase-01 lot of workstream Y). The phone layout of the planner's targets table
(defect 5: its declared widths exceed a phone) stays out, by the developer's decision 50 («first the general cure of
the tables on the phone»): to be re-judged on the mobile gallery shots `pac-step-targets` and `pac-step-review`.

The same sticky header causes another defect: a `SimpleSelect` list opened upward in a row falls under it
([[problems/select-list-under-the-sticky-table-header]], W-B26, 2026-10-15).

## Source files

| Role | Path |
|------|------|
| Shared table (sticky header, actions, media query) | `frontend/src/lib/components/table/DataTable.svelte` |
| Review step table | `frontend/src/lib/features/tools/pac-allocator/planner/steps/ReviewStep.svelte` |
| Targets step table | `frontend/src/lib/features/tools/pac-allocator/planner/steps/TargetsStep.svelte` |
| PAC backlog (defects 1–5) | `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/README.md` |
| Phone E2E (D-Y17) | `frontend/e2e/layout/datatable-mobile.spec.ts` |
| Developer page | `mkdocs_src/docs/developer/frontend/components/core-ui/data-table.md` |
| Workstream Y's plan (Y7) | `LibreFolio_developer_journal/Release_2/Phase_1/09_dashboardCharts/plan-phase01DashboardCharts.prompt.md` |

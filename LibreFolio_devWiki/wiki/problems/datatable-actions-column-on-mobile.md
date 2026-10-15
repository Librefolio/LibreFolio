---
title: "On a phone the DataTable's actions column misbehaves: the «Actions» header stays pinned while the rows' ⋮ falls out of view (hypothesis)"
category: problem
status: open
date: 2026-10-10
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

## Root Cause — a hypothesis from reading the code

To be confirmed in a browser before any cure (the PAC folder's README says so for every cause marked «ipotesi»):

- Below 768 px a media query makes the action cells static: `@media (max-width: 768px) { .th-actions, .td-actions
  { position: static; } }` in `DataTable.svelte`.
- The header cells, though, also match `thead.sticky-header th { position: sticky; … }` — `stickyHeader` defaults
  to `true` — and that selector is more specific than `.th-actions`. The header keeps `position: sticky` with
  `right: 0` (`.th-actions.th-fixed`): pinned to the right edge, while the cells carrying the ⋮ scroll out of view on
  the right.
- For the targets table, the declared widths add up to more than 500 px (selection 48, Asset at least 160,
  Distribution 200 with a minimum of 100, Target % 140 with a minimum of 128, actions 64), and the selection column is
  sticky on the left, so it can cover the names when the table scrolls.

## Status

Open, in the post-1.2 backlog of `13_pacAllocator/` (defects 2 and 5, 2026-10-10). M fixed only the gallery fixture
in batch 10 (a blur and a horizontal scroll reset). `DataTable` is shared and is not the PAC's: the cure must be
agreed with its owner, and the same effect is possible in any table whose actions column is wider than a phone. For
defect 5 a decision is pending: a phone layout for the planner's tables, or the cure of defect 2 in `DataTable`.

The same sticky header causes another defect: a `SimpleSelect` list opened upward in a row falls under it
([[problems/select-list-under-the-sticky-table-header]], W-B26, 2026-10-15).

## Source files

| Role | Path |
|------|------|
| Shared table (sticky header, actions, media query) | `frontend/src/lib/components/table/DataTable.svelte` |
| Review step table | `frontend/src/lib/features/tools/pac-allocator/planner/steps/ReviewStep.svelte` |
| Targets step table | `frontend/src/lib/features/tools/pac-allocator/planner/steps/TargetsStep.svelte` |
| PAC backlog (defects 1–5) | `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/README.md` |

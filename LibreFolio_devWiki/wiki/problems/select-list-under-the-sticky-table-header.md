---
title: "A SimpleSelect list opened upward inside a table falls under the sticky header (W-B26)"
category: problem
status: open
date: 2026-10-15
tags: [frontend, datatable, simpleselect, z-index, stacking-context, sticky, shared-component, e2e]
related:
  - problems/datatable-actions-column-on-mobile
  - problems/bulk-modal-sticky-z-index
  - sources/phase06-step3-rounds
  - decisions/asset-event-saves-all-or-nothing
---

# Problem: a select list under the sticky table header

## Symptom

Release 1.3, workstream W, lot E1b, 15/10. In `asset-event-editor-save.spec.ts`, test 3 (an event in use plus another
edit) failed every time on changing a row's type: before the cure and after it, run alone too. Playwright could not
click the `SPLIT` option, because the table's sticky header was on top of it (`thead.sticky-header … intercepts
pointer events`). A user sees the same thing in the events editor: a row's *Type* list opened upward, near the
header, has its options covered and cannot click them.

Its red had been read as the intended one. The behaviour that test was after (an event in use refuses the whole
save) is proved red-first elsewhere: at the API (409 against 422) and in scenario 2 of `asset-event-delete.spec.ts`.

## Root Cause

- The list of `SimpleSelect` is `position: fixed` with `z-[9999]` (`SimpleSelect.svelte:328`), so that overflow
  panels no longer clip it (Phase 6, BUG-12: [[sources/phase06-step3-rounds]]). It is rendered where the select
  is, not moved to `body`.
- A fixed element still belongs to the stacking context of its nearest ancestor that creates one. In `DataTable`
  that ancestor is the row:
  - a row holding an editable select is `position: relative; z-index: 1`
    (`tbody tr:has(.cell-editable-select-wrapper)`);
  - it rises to 10 while it has focus (`tbody tr:focus-within`).
  So the list's 9999 counts only inside its row.
- The sticky header cells sit at `z-index: 15` (`thead.sticky-header th`, `DataTable.svelte:1621`).
- The table cell uses `dropdownPosition="auto"`, so the list opens upward when there is little room below:
  - opening downward, the list covers the other rows (z 1), which works;
  - opening upward next to the header, the header (15) paints over the row (10) and everything inside it.
- The code knows the trap in part. The wrapper has no z-index of its own on purpose («No z-index here: avoids
  creating a stacking context that would trap the fixed-positioned dropdown below the sticky actions column»), and
  the row bump lifts it over sibling rows. Nothing lifts it over the header.

## Solution

Open: backlog **W-B26**, for the owners of the shared UI and table components (to be assigned). The backlog suggests
moving the list to `body` (a portal), like other fixed menus. The AI Export panel, for one, is portalled to
`document.body` ([[decisions/ai-export-versioned-snapshot-boundary]]).

Workaround in the test: test 3 changes the amount instead of the type, and passes (4/4).

## Prevention

- A `z-index` on a fixed popover is global only if no ancestor creates a stacking context. Inside tables, modals and
  sticky layouts, portal the popover to `body`.
- When an E2E fails with «… intercepts pointer events» from a sticky header, look for a stacking context before
  blaming the test. Check that a red written first fails for the reason it was written for.

## Impact

- Low for users: it takes a list that opens upward (little room below its row) and reaches the header. The options
  under the header cannot be clicked.
- For W: reruns in the shared test slot, and a red misread as the intended one.

## Source files

| Role | Path |
|------|------|
| The list: `fixed z-[9999]`, not portalled (line 328) | `frontend/src/lib/components/ui/select/SimpleSelect.svelte` |
| The sticky header (line 1621); the row's stacking context; the editable select cell | `frontend/src/lib/components/table/DataTable.svelte` |
| The E2E that met it (test 3) | `frontend/e2e/assets/asset-event-editor-save.spec.ts` |
| Backlog W-B26 | `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` |
| Plan 04, section E1, step 3 | `LibreFolio_developer_journal/Release_2/Phase_1/04_importTransactions/plan-phase01ImportTransactions.prompt.md` |

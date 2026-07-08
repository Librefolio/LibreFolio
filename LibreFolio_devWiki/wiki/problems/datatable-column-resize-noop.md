---
title: "DataTable column-resize handle has no effect in some tables"
category: problem
status: open
date: 2026-07-07
tags: [frontend, datatable, svelte5, ui, low-priority, pre-existing]
related:
  - sources/phase09-m1-m2-archive-2026-07
---

# Problem: DataTable Column-Resize Handle Has No Effect in Some Tables

## Symptom

`DataTable.svelte`'s per-column resize handle (the draggable divider shown on `th:hover`) renders correctly
(cursor changes to `col-resize`, the handle highlights), but dragging it produces no visible change to the
column width in some tables that use the component. Discovered during the exhaustive verification pass before
archiving Phase 09 Milestone 1 & 2 (2026-07-07). Unrelated to the dashboard/portfolio-engine work — a
pre-existing frontend gap noticed in passing.

## Root Cause

Not yet root-caused. `DataTable.svelte` implements resize via `startResize()` → `mousemove` →
`stopResize()` → optional `onColumnResize?.(columnId, finalWidth)` callback (see
`frontend/src/lib/components/table/DataTable.svelte:843-875`). The component supports resizing generically
(`enableColumnResize` prop, default `true`; `column.resizable !== false` per-column opt-out), but persisting
the resized width back into the rendered table likely depends on the specific consuming page:
- Some tables may not read back `onColumnResize` at all, so the internal `resizing` state changes but no
  parent state update re-renders the column at the new width.
- Some tables may pass a fixed/derived `width` prop per column that overrides the internal resize state on the
  next re-render, effectively snapping back.

This has not been confirmed against a specific consuming table — flagged as a to-investigate item, not a
diagnosed bug.

## Solution

Not yet fixed. Next step: reproduce in a specific table (e.g. the Transactions list or a Dashboard positions
table), inspect whether `onColumnResize` is wired by the parent, and check whether column `width`/`minWidth`
props are being recomputed on every render in a way that overrides the resize state.

## Prevention

N/A until root-caused. Once fixed, consider adding a Playwright E2E assertion (drag resize handle, assert
column `offsetWidth` changed) to prevent regression, per this project's `e2e-data-testid-rule` convention.

## Impact

Low — cosmetic/UX only, does not block any workflow. The resize icon being present but inert is mildly
confusing to users but does not affect data correctness.

## Source files

| Role | Path |
|------|------|
| Component | `frontend/src/lib/components/table/DataTable.svelte` |

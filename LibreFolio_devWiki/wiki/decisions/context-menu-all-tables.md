---
title: "ContextMenu default ON on all DataTables"
category: decision
status: resolved
date: 2026-05-05
tags: [frontend, datatable, context-menu, ux, mobile]
related:
  - features/F-047
  - features/F-048
---

# Decision: ContextMenu Default ON on All DataTables

## Context
Transaction rows had many actions (edit, clone, delete, view, promote, split) but only small icon buttons at the row end. On mobile, these were cramped. Users expected right-click context menus on desktop.

## Options Considered
1. **Per-table opt-in** — each table consumer passes `enableContextMenu={true}` → forgotten, inconsistent
2. **Default ON** (chosen) — DataTable enables ContextMenu automatically when `rowActions.length > 0`

## Decision
**Default ON** with `enableContextMenu: boolean = true` prop on DataTable. Zero changes needed in consumer components (Transactions, FX, Assets, Brokers).

### Implementation
- New `ContextMenu.svelte`: floating panel at `{x,y}`, `z-index: 50`, `role="menu"`, viewport clamping, separator support, `data-testid="context-menu"`
- Desktop: native `contextmenu` event (right-click)
- Mobile: native `contextmenu` fires on long-press (~400ms, browser-native — no custom touchstart/touchend timers)
- Actions filtered by same `visible?.(row)` and `disabled?.(row)` predicates as action column
- Click outside (window `pointerdown`) or Escape → closes

## Consequences
- Every DataTable in the app immediately gains right-click actions with zero code changes
- Consistent UX across all pages
- Mobile long-press works out of the box via browser native behavior

## Source files

| Role | Path |
|------|------|
| ContextMenu component | `frontend/src/lib/components/ui/ContextMenu.svelte` |
| DataTable integration | `frontend/src/lib/components/table/DataTable.svelte` |


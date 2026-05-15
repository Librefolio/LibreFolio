---
title: "Phase 07 Part 4 Round 6 — Context Menu, Delete, Polish"
category: source
source_type: plan
date_ingested: 2026-05-28
original_path: LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/plan-phase07-transaction-Part4_Round6_ContextMenuDeletePolish.prompt.md
tags: [phase07, transactions, context-menu, delete-modal, picker-modal, split, promote, broker-access, url-filters]
related:
  - sources/phase07-part4-round6-plana-context-menu-bugfix
  - sources/phase07-part4-round6-planb-delete-picker-access
  - decisions/context-menu-all-tables
  - features/F-047
  - features/F-048
---

# Source: Phase 07 Part 4 Round 6 — Context Menu, Delete, Polish

## Summary
Master plan for Round 6 covering 12 steps across 3 sub-plans (A, B, C). Implements reusable ContextMenu for all DataTables (right-click desktop, long-press mobile), fixes 3 critical bugs from Round 5 test walk (R7-C1 paired edit, R7-H1 type swap qty, R7-H2 TagInput anti-bounce), creates TransactionDeleteModal with rich recap layouts, builds TransactionPickerModal for adding existing DB transactions to BulkModal, and plans backend Split/Promote endpoints. Steps 1–6 completed in Plan A; Step 7+ in Plan B/B23.

## Key Takeaways
- **ContextMenu.svelte**: floating panel at `{x,y}` coordinates, `z-index: 50`, `role="menu"`, viewport clamping, `data-testid`, separator support. Integrated in DataTable with `enableContextMenu=true` default ON — active on ALL tables (transactions, FX, assets, brokers) automatically
- **3 sub-plans**: Plan A (ContextMenu + R7-C1/H1 bugfix ✅), Plan B (Delete + Picker + Broker Access, partially done), Plan C (Split/Promote full stack, planned)
- **Asset clickable**: asset names in transactions table are SPA links (`goto(/assets/{id})`) with hover underline
- **URL filter sync**: full bidirectional sync of all filter state to URL params (id, qty, broker multi, asset multi) + back button preservation via `navigationStore`
- **TagInput polish**: keyboard nav (ArrowDown/Up + Enter), colored chips via `getStringColor()`, anti-bounce via `relatedTarget` check (replaces fragile setTimeout), chip navigation with Delete/Backspace on selected chip
- **Soft reload**: `reload({soft: true})` preserves DataTable filter/sort state after save operations (fixes state reset problem)
- **TransactionDeleteModal**: 3 layouts (A=standalone, B=paired full access, C=paired blocked). Always deletes both halves of pair; to delete one side, use Split first
- **TransactionPickerModal**: reuses TransactionsTable with `pickerMode`, `excludeIds` filter, auto-add partner for paired selections
- **Split/Promote backend**: planned `POST /transactions/split` and `/promote` endpoints with type mutation maps (deferred to Plan C)

## Wiki Pages Updated
- [[features/F-047]] — ContextMenu, asset clickable, URL filter sync, description column, soft reload
- [[features/F-048]] — DeleteModal, PickerModal, TagInput polish
- [[decisions/context-menu-all-tables]] — created


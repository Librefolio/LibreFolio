---
title: "Dual View Pattern (Card Grid + DataTable)"
category: concept
tags: [frontend, ux, pattern, assets, fx]
related_features: [F-021, F-032]
---

# Concept: Dual View Pattern

## Definition
List pages for Assets and FX pairs offer two interchangeable views: a **card grid** (visual, rich with mini-charts) and a **DataTable** (dense, sortable, multi-column). The selected view is persisted in `localStorage` and survives page navigation.

## Where it applies
- `frontend/src/routes/(app)/assets/+page.svelte` — [[F-032]] Asset List
- `frontend/src/routes/(app)/fx/+page.svelte` — [[F-021]] FX List

## Anatomy
```
[Cards | Table]  ← toggle button persisted in localStorage

Card view:  AssetCard / FxCard with mini-chart, badge, key metrics
Table view: DataTable component with sortable columns, filters
```

## Why two views
- **Cards**: discovery and overview — visual hierarchy, trend at a glance
- **Table**: analysis and bulk operations — sorting by multiple columns, dense information

## Implementation notes
- Toggle state key: `librefolio-assets-view` / `librefolio-fx-view` in localStorage
- Both views share the same data store — switching doesn't trigger a re-fetch
- Table uses the generic `DataTable` component from `frontend/src/lib/components/table/`

## Source
`LibreFolio_developer_journal/knowledge_base/00_project_overview.md` — "Dual View" entry

## Source files

| Role | Path |
|------|------|
| Asset card | `frontend/src/lib/components/assets/AssetCard.svelte` |
| Asset table | `frontend/src/lib/components/assets/AssetTable.svelte` |
| FX card | `frontend/src/lib/components/fx/FxCard.svelte` |
| FX table | `frontend/src/lib/components/fx/FxTable.svelte` |
| View mode toggle | `frontend/src/lib/components/ui/ViewModeToggle.svelte` |

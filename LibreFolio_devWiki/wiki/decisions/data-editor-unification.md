---
title: "Data editor unification — generic DataEditor component set"
category: decision
status: resolved
date: 2026-04-01
tags: [frontend, components, data-editor, fx, assets, architecture, ux]
related: [concepts/editbuffer-pattern, decisions/sveltekit-over-react]
---

# Decision: Data Editor Unification — Generic DataEditor Component Set

## Context
Phase 6 Part B identified that FX rate editing and Asset price editing had grown into separate, duplicated implementations. Both had: click-to-edit table cells, CSV import/export, status tracking (original/edited/deleted), gap rows, and bulk save. Maintaining two separate implementations was increasing divergence risk.

## Options Considered
1. **Keep separate FX and Asset editors** — simpler short term, but divergence would grow with new editor features.
2. **Generic `DataEditor` component set** — shared types (`DataEditorTypes.ts`), generic `DataEditor.svelte`, domain-specific wrappers (FxDataEditorSection, AssetDataEditorSection).

## Decision
**Generic DataEditor component set** in `frontend/src/lib/components/ui/data-editor/`. FX and Asset domains both use the same core, with thin wrappers for domain-specific column definitions.

## Consequences

### New files created
- `DataEditorTypes.ts` — `ColumnDef`, `DataRow`, `GapRow`, `TableRow`, `RowStatus` types
- `DataEditor.svelte` — generic N-column editable table; supports types: `date, number, string, enum, currency`
- `CsvEditor.svelte` — generic N-column CSV parser configured via `columns: CsvColumnDef[]` prop
- `DataImportModal.svelte` — generic import container
- `ErasableNumberCell.svelte` — optional OHLC fields: NULL → "not set" placeholder; eraser sends `-1` sentinel
- `index.ts` — barrel export

### Domain wrappers
- `FxDataEditorSection.svelte` — wraps DataEditor for FX rate rows
- `AssetDataEditorSection.svelte` — 2-tab orchestrator (Prices tab + Events tab) using DataEditor for each
- Domain-specific: `FxDataImportModal`, `PriceDataImportModal`, `EventDataImportModal`

### DataRow status model
- `RowStatus`: `'original' | 'edited' | 'deleted' | 'appended'`
- Each row has `_originalValues` for revert; `selected` for bulk ops
- Bulk save: only dirty rows sent to backend; on success, all become `'original'`
- Gap rows: folded date ranges shown as `GapRow` placeholders; `staleDays` on `DataRow` drives stale visual

## Links
- [[concepts/editbuffer-pattern]]
- Source: `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-06-subplan/Bugfix-Step4/PlanB/plan-partBDataEditorUnificato.prompt.md`

## Source files

| Role | Path |
|------|------|
| DataEditor types | `frontend/src/lib/components/ui/data-editor/DataEditorTypes.ts` |
| DataEditor component | `frontend/src/lib/components/ui/data-editor/DataEditor.svelte` |
| CsvEditor component | `frontend/src/lib/components/ui/data-editor/CsvEditor.svelte` |
| DataImportModal | `frontend/src/lib/components/ui/data-editor/DataImportModal.svelte` |
| ErasableNumberCell | `frontend/src/lib/components/ui/data-editor/ErasableNumberCell.svelte` |
| Asset data editor | `frontend/src/lib/components/assets/AssetDataEditorSection.svelte` |
| FX data editor | `frontend/src/lib/components/fx/FxDataEditorSection.svelte` |
| Plan | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-06-subplan/Bugfix-Step4/PlanB/plan-partBDataEditorUnificato.prompt.md` |

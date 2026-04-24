---
title: "EditBuffer pattern (DataRow status tracking)"
category: concept
tags: [frontend, components, data-editor, ux, state]
related: [concepts/timeseries-store-pattern, decisions/data-editor-unification]
---

# Concept: EditBuffer Pattern

## Definition
The "EditBuffer pattern" in LibreFolio is the technique of tracking per-row edit state within the `DataEditor` component via `DataRow.status`. It enables in-place editing, CSV import, bulk delete, and revert — all without a dedicated `EditBuffer.ts` class. The pattern is implemented entirely through `DataEditorTypes.ts` and `DataEditor.svelte`.

> **Note**: There is no `EditBuffer.ts` file. The pattern is embodied in `DataEditorTypes.ts` + `DataEditor.svelte`.

## Where It Applies
- `DataEditor.svelte` — generic editable table (prices, FX rates, events)
- `AssetDataEditorSection.svelte` — 2-tab orchestrator for asset prices and events
- `FxDataEditorSection.svelte` — FX rate editing

## Key Types

```typescript
type RowStatus = 'original' | 'edited' | 'deleted' | 'appended';

interface DataRow {
  rowId: string;
  date: string;
  status: RowStatus;
  _originalValues: Record<string, unknown>;  // for revert
  values: Record<string, unknown>;
  selected: boolean;   // for bulk ops
  readonly: boolean;   // editable but not deletable
  staleDays?: number;  // drives stale visual indicator
}

interface GapRow {
  // folded date ranges shown as a placeholder (not editable)
}

type TableRow = DataRow | GapRow;
```

## Key Behaviors

| Action | Mechanism |
|--------|-----------|
| Click-to-edit cell | `status` → `'edited'`; `_originalValues` preserved |
| Revert row | if `originalStatus === 'original'` → restore `_originalValues`, status back to `'original'` |
| Delete row | `status` → `'deleted'` (not immediately removed from list) |
| CSV import | Parsed rows added as `'appended'` DataRows |
| Bulk save | Only rows with status `!== 'original'` sent to backend; on success all become `'original'` |
| Readonly rows | `readonly: true` — display-only, no cell editing, but deletable |

## Examples

### ErasableNumberCell convention
Optional OHLC fields use `ErasableNumberCell`:
- Value is `null` → displays "not set" placeholder
- User clicks eraser icon → sends `-1` sentinel to backend → backend stores NULL

### CSV import flow
`CsvEditor.svelte` parses N-column CSV configured by `columns: CsvColumnDef[]` prop.
`DataImportModal.svelte` wraps CsvEditor and converts parsed rows to `'appended'` DataRows.
Domain-specific wrappers: `FxDataImportModal`, `PriceDataImportModal`, `EventDataImportModal`.

## Source files

| Role | Path |
|------|------|
| DataEditorTypes | `frontend/src/lib/components/ui/data-editor/DataEditorTypes.ts` |
| DataEditor component | `frontend/src/lib/components/ui/data-editor/DataEditor.svelte` |
| CsvEditor component | `frontend/src/lib/components/ui/data-editor/CsvEditor.svelte` |
| DataImportModal | `frontend/src/lib/components/ui/data-editor/DataImportModal.svelte` |
| ErasableNumberCell | `frontend/src/lib/components/ui/data-editor/ErasableNumberCell.svelte` |

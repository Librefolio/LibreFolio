---
title: "ImportWizardModal"
category: entity
type: component
tags: [frontend, brim, import, wizard, modal, stepper, multi-file, svelte5]
related:
  - decisions/import-wizard-v5-paradigm
  - concepts/import-todo-signals
  - concepts/workspace-intent-pattern
  - entities/api-router
  - features/F-012
  - features/F-048
---

# ImportWizardModal

## Role

The Import Wizard Modal is the primary UI surface for importing broker transaction reports (BRIM) into LibreFolio. It is a wide modal overlay (maxWidth 6xl, z-index 70) that guides users through 4 numbered steps: upload files, select files to parse, parse them, and review/import the results. It runs on top of `BulkModal` (z:60) and launches sub-modals (z:80) for confirmation, asset resolution, and file preview.

## Location

`frontend/src/lib/components/transactions/modals/ImportWizardModal.svelte`

## Key Interfaces

### Output Contract

```typescript
// Only output: array of TXCreateItem (backend schema)
onImportBatch: (items: TXCreateItem[]) => void
```

The modal calls this callback when the user confirms import in Step 4. The recipient (`BulkModal`) converts items via `txCreateItemToPendingOp()` into pending rows.

### Internal Data Model (4 steps)

```typescript
UploadedFileEntry[]  // Step 1: uploaded files with broker assignment
    ↓
FileSelection[]      // Step 2: files selected for parsing + plugin override
    ↓
ParsedFileResult[]   // Step 3: parse results per file (BRIMParseResponse)
    ↓
MergedTransaction[]  // Step 4: merged TXCreateItem[] + todos + duplicateStatus
```

### Key State Interfaces

```typescript
interface UploadedFileEntry {
    fileId: string; fileName: string; brokerId: number | null;
    pluginCode: string | null; uploadedNow: boolean;
    status: 'uploaded' | 'error'; errorMessage?: string;
}
interface ImportTodo {
    field: string; severity: 'blocker' | 'warning';
    reasonCode: string; message: string; context?: Record<string, unknown>;
}
interface AssetMapping {
    fakeAssetId: number; extractedSymbol: string | null;
    resolvedAssetId: number | null; txCount: number; sourceFiles: string[];
}
```

## Design Notes

### Z-Layer Architecture
```
z:60  BulkModal (existing, always in background)
z:70  ImportWizardModal (wide overlay)
z:80  ConfirmModal / AssetModal / FilePreviewModal (sub-modals)
```

### Navigation Model
- **Forward**: footer "Next/Continue" button
- **Back**: click any **previous** step number in stepper bar (state preserved unless data invalidated)
- Step 3→Step 1: clears parse results. Step 4→Step 2: clears TX merge, auto-re-enters Step 3.
- Cannot skip forward (Step N only clickable if N < currentStep).

### Asset Resolution Flow
- BRIM plugins emit **negative fake asset IDs** for unrecognized assets.
- Step 4 shows an `AssetMapping` panel for each fake ID.
- User selects a real asset (via `AssetSelect`) or creates a new one (via `AssetModal`).
- After selection: `resolveAssetManual()` opens identifier-prompt if asset has no matching identifier.
- **Bug (Cat-C)**: `oncreated` path doesn't call `resolveAssetManual()` → identifier prompt skipped. Fix: replicate `resolveAssetManual` logic in `oncreated` callback.

### `ImportTodo` signals
Wizard-local field warnings/blockers emitted by backend plugins. Never touch `PendingOp`. See [[concepts/import-todo-signals]].

### Duplicate Detection
`duplicateStatus: 'unique' | 'possible' | 'likely'` — backend compares parsed items against existing transactions. `'likely'` duplicates are auto-deselected.

## History

| Date | Change |
|------|--------|
| 2026-06-08 | v5 redesign: multi-file native, 4-step stepper, z:70 overlay. Supersedes v4 single-file breadcrumb approach. |
| 2026-06-08 | Schwab parser added; Coinbase INTEREST qty fix |
| 2026-06-25 | Bug report: Cat-C (oncreated path skips identifier prompt) and Cat-D (BulkModal toolbar z-index after import) |

## Source files

| Role | Path |
|------|------|
| Component | `frontend/src/lib/components/transactions/modals/ImportWizardModal.svelte` |
| BRIM parse API | `backend/app/api/v1/brim.py` |
| BRIM providers dir | `backend/app/services/brim_providers/` |
| Schwab provider | `backend/app/services/brim_providers/broker_schwab.py` |
| Coinbase provider (fixed) | `backend/app/services/brim_providers/broker_coinbase.py` |
| mkdocs (import guide) | `mkdocs_src/docs/user/transactions/import/index.en.md` |

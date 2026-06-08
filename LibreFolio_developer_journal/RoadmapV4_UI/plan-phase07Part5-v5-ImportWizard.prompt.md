# Phase 07 Part 5 — BRIM Import Wizard (v5 — Redesign)

**Date**: 2026-06-08
**Status**: 🚧 EXECUTING — M1 complete ✅ (Round 3 polish done)
**Supersedes**: `plan-phase07Part5-BRIMImportBridge.prompt.md` (v4)
**Parent milestone log**: [plan-phase07Part5-M1-ParseAndSee.prompt.md](./plan-phase07Part5-M1-ParseAndSee.prompt.md) (M1 complete, feedback incorporated)
**M1 detailed plan**: [plan-phase07Part5-M1v2-ImportWizardRebuild.prompt.md](./plan-phase07Part5-M1v2-ImportWizardRebuild.prompt.md)

---

## 0. Why v5 — Paradigm Changes from User Testing

| v4 Assumption | v5 Reality |
|---------------|------------|
| Small modal (maxWidth 2xl) | **Wide modal** (maxWidth 6xl) — same overlay approach, more space |
| Single-file per cycle, re-open for more | **Multi-file native** — N files from M brokers in one flow |
| Broker-first → files appear | **Upload-first** (Step 1) + **broker panels with file picker** (Step 2) |
| Mode switching (breadcrumb) | **Numbered stepper** (1-2-3-4) with back-navigation via click |
| Serial re-open for multi-broker | All brokers visible at once in Step 2 |
| Dedicated page needed? | No — wide modal in overlay is enough |

---

## 1. Architecture Overview

### Container

```
z:60  BulkModal (existing, background)
z:70  ImportWizardModal (wide overlay, maxWidth="6xl")
z:80  ConfirmModal / AssetModal / FilePreviewModal (on top)
```

### Output Contract (unchanged from v4)

```
ImportWizardModal output:  TXCreateItem[]  (backend schema)
         ↓ onImportBatch callback
BulkModal receives TXCreateItem[] → txCreateItemToPendingOp() → grid rows
```

### Navigation Model: Forward + Clickable Stepper

```
Step 1 ──▶ Step 2 ──▶ Step 3 ──▶ Step 4
  ●          ○          ○          ○

Rules:
- Forward: button "Next/Continue" at footer right
- Back: click any PREVIOUS step number in stepper bar
- Clicking back preserves state (selections kept if still valid)
- Step 3→Step 1 click: parse results cleared (files may have changed)
- Step 4→Step 2 click: TX merge cleared, re-enters from Step 3 auto
- Step N is clickable only if N < currentStep (can't skip forward)
```

---

## 2. Data Model

```ts
// ─── Step 1 state ───
interface UploadedFileEntry {
    fileId: string;
    fileName: string;
    brokerId: number | null;    // assigned broker (required before upload)
    pluginCode: string | null;  // override plugin (null = auto/default)
    uploadedNow: boolean;       // true if uploaded in this session (for pre-select in Step 2)
    status: 'uploaded' | 'error';
    errorMessage?: string;
}
let uploadedFiles = $state<UploadedFileEntry[]>([]);

// ─── Step 2 state ───
interface FileSelection {
    fileId: string;
    fileName: string;
    brokerId: number;
    pluginCode: string | null;  // null = broker default or auto
}
let selectedFiles = $state<FileSelection[]>([]);

// ─── Step 3 state ───
interface ParsedFileResult {
    fileId: string;
    fileName: string;
    brokerId: number;
    pluginUsed: string;
    status: 'pending' | 'parsing' | 'done' | 'error';
    response: BRIMParseResponse | null;
    errorMessage?: string;
}
let parseResults = $state<ParsedFileResult[]>([]);

// ─── Step 4 state ───
interface MergedTransaction {
    index: number;              // global index across all files
    sourceFileId: string;
    tx: TXCreateItem;           // raw from parse (may have fake asset_id)
    selected: boolean;          // checkbox state
    duplicateStatus: 'unique' | 'possible' | 'likely';
    duplicateMatch?: string;    // description of what it matches
}
let mergedTransactions = $state<MergedTransaction[]>([]);

interface AssetMapping {
    fakeAssetId: number;
    extractedSymbol: string | null;
    extractedIsin: string | null;
    extractedName: string | null;
    candidates: BRIMAssetCandidate[];
    resolvedAssetId: number | null;  // user choice
    txCount: number;
    sourceFiles: string[];  // filenames where this asset appears
}
let assetMappings = $state<AssetMapping[]>([]);
```

---

## 3. Step Details

### Step 1: Upload & Assign Broker

**Purpose**: Upload new files and assign each to a broker. Optional step — user can skip if files already exist on brokers.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  Import Transactions                                                   [X]      │
│  ━━●━━━━━━━━━━━━━━━━━━━○━━━━━━━━━━━━━━━━━━━○━━━━━━━━━━━━━━━━━━━○━━━━━━━━━━━━  │
│   1. Upload           2. Select Files      3. Parse             4. Review       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  Global broker (applies to new uploads):                                        │
│  [▼ Select broker ─────────────────────────────────]                           │
│                                                                                 │
│  ┌─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐   │
│  │  📄 Drop files here or click to upload (.csv, .xlsx)                    │   │
│  │     Multiple files supported — each assigned to selected broker         │   │
│  └─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘   │
│                                                                                 │
│  ─── Uploaded files ────────────────────────────────────────────────────────── │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │ File                    │ Broker              │ Plugin        │ Actions  │  │
│  │─────────────────────────┼─────────────────────┼───────────────┼──────────│  │
│  │ degiro_2025.csv         │ [▼ Degiro       ]   │ [▼ Auto    ]  │ 🗑️  👁️  │  │
│  │ ibkr_march.csv          │ [▼ IBKR        ]   │ [▼ Auto    ]  │ 🗑️  👁️  │  │
│  │ revolut_Q1.csv          │ [▼ Select…     ]   │ [▼ —       ]  │ 🗑️  👁️  │  │
│  │                         │  ⚠️ Broker required │               │          │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  💡 You can also skip this step and select existing broker files in Step 2.     │
│                                                                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│ [Cancel]                                              [Next: Select Files ▶]    │
│                         (Next always enabled — Step 1 is optional)              │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Key behaviors**:

| Behavior | Detail |
|----------|--------|
| Global broker dropdown | Sets default for new uploads. Per-file override always possible |
| Upload | Multi-file drag & drop. Each file auto-assigned to global broker (if set) |
| Per-file broker | Dropdown in table row — user can reassign any file to different broker |
| Per-file plugin | Default = "Auto" (uses broker's `default_import_plugin`). User can override |
| Upload to server | On drop/select → `POST /import/upload` with `broker_id`. File appears in table |
| Validation | Extension check client-side (.csv/.xlsx/.xls). Red row + error if invalid |
| Remove | 🗑️ removes from list (and optionally from server) |
| Preview | 👁️ → FilePreviewModal at z:80 |
| Next enabled | Always — user can skip Step 1 entirely if files already on broker |
| Broker required | Row shows ⚠️ if no broker. Upload blocked until broker assigned |

**Global broker logic**:
- When user picks global broker → all rows without a broker get it assigned
- When user uploads new file → gets global broker
- Per-row override always wins

---

### Step 2: Select Files to Parse

**Purpose**: Browse existing broker files (including those just uploaded) and select which ones to parse. Organized by broker panels.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  Import Transactions                                                   [X]      │
│  ━━✓━━━━━━━━━━━━━━━━━━━●━━━━━━━━━━━━━━━━━━━○━━━━━━━━━━━━━━━━━━━○━━━━━━━━━━━━  │
│   1. Upload           2. Select Files      3. Parse             4. Review       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  Filter brokers: [▼ All brokers ▾]  [☑ Only with unparsed files]               │
│                                                                                 │
│  Selected: 3 files from 2 brokers                                              │
│                                                                                 │
│  ┌─── 🏦 Degiro ─────────────────────────────────────────────────────────────┐ │
│  │  Plugin: [▼ Degiro (default) ]                                            │ │
│  │                                                                           │ │
│  │  [☑] degiro_2025.csv        2025-04-01   UPLOADED        ← from Step 1   │ │
│  │  [☑] degiro_2024_Q4.csv     2025-01-15   UPLOADED                        │ │
│  │  [ ] degiro_2024_Q3.csv     2024-10-01   PARSED ✓                        │ │
│  │  [ ] degiro_2024_Q2.csv     2024-07-01   PARSED ✓                        │ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
│  ┌─── 🏦 IBKR ──────────────────────────────────────────────────────────────┐ │
│  │  Plugin: [▼ Interactive Brokers (default) ]                               │ │
│  │                                                                           │ │
│  │  [☑] ibkr_march.csv         2025-04-01   UPLOADED        ← from Step 1   │ │
│  │  [ ] ibkr_2024_annual.csv   2024-02-01   PARSED ✓  [↻ Stale]            │ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
│  ┌─── 🏦 Revolut ───────────────────────────────────────────────────────────┐ │
│  │  Plugin: [▼ Revolut (default) ]                                           │ │
│  │                                                                           │ │
│  │  [ ] revolut_2024.csv       2024-06-01   PARSED ✓                        │ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│ [← Back]                                                    [Parse (3) ▶]       │
│                                          (disabled if 0 files selected)         │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Key behaviors**:

| Behavior | Detail |
|----------|--------|
| Broker panels | One collapsible panel per broker (EDITOR+ role only) |
| Filter dropdown | "All brokers" / specific broker. Checkbox "Only with unparsed files" |
| Pre-selection | Files uploaded in Step 1 → auto-checked |
| Per-broker plugin | Default from `broker.default_import_plugin`. Per-broker override possible |
| File status badges | UPLOADED (gray), PARSED (green), STALE (amber ↻), ERROR (red) |
| Checkbox multi-select | Standard checkboxes, multi-file per broker |
| "Parse" button | Shows count. Disabled if 0 selected |
| Back → Step 1 | Keeps uploaded files, clears file selections |

**Why per-broker plugin (not per-file)**:
- 99% of cases: all files from one broker use the same plugin
- Simplifies UX enormously
- Edge case (mixed formats from same broker) → re-run wizard for the other files with different plugin

---

### Step 3: Parse (sequential, per-file results)

**Purpose**: Parse each selected file individually. Show progress and per-file results.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  Import Transactions                                                   [X]      │
│  ━━✓━━━━━━━━━━━━━━━━━━━✓━━━━━━━━━━━━━━━━━━━●━━━━━━━━━━━━━━━━━━━○━━━━━━━━━━━━  │
│   1. Upload           2. Select Files      3. Parse             4. Review       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  Parsing 3 files...  [██████████░░░░░░░░░░] 2/3                                │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │ #  │ File                 │ Broker  │ Status      │ TX  │ Assets │ Warn │  │
│  │────┼──────────────────────┼─────────┼─────────────┼─────┼────────┼──────│  │
│  │ 1  │ degiro_2025.csv      │ Degiro  │ ✅ Done     │ 42  │ 5 (2?) │ 1   │  │
│  │ 2  │ degiro_2024_Q4.csv   │ Degiro  │ ✅ Done     │ 18  │ 3 (0?) │ 0   │  │
│  │ 3  │ ibkr_march.csv       │ IBKR    │ ⏳ Parsing… │ —   │ —      │ —   │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  ─── Summary ──────────────────────────────────────────────────────────────── │
│  📊 60 transactions found (across 2 files done)                                │
│  🔗 8 unique assets detected, 2 need resolution                                │
│  ⚠️ 1 warning total                                                            │
│                                                                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│ [← Back]                                                   [Continue ▶]         │
│              (Continue enabled when ALL files done/failed, ≥1 success)          │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Key behaviors**:

| Behavior | Detail |
|----------|--------|
| Sequential parse | Files parsed one by one (`POST /files/{id}/parse`). Progress bar |
| Per-file row | Status (pending → parsing → done/error), TX count, asset count, warnings |
| Error handling | Failed file shows red row + error message. Does NOT block others |
| Summary | Aggregated stats (live-updating as files complete) |
| "Assets (N?)" | Number after ? = unresolved assets for that file |
| Continue | Enabled when all files finished (done/error) AND at least 1 success |
| Back → Step 2 | Cancels any in-progress parse, clears all results, keeps file selection |
| Auto-start | Parsing starts immediately on entering Step 3 (no "Start" button) |

---

### Step 4: Review, Resolve & Import

**Purpose**: Unified final step — merge all TX, handle duplicates, resolve assets, select what to import.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  Import Transactions                                                   [X]      │
│  ━━✓━━━━━━━━━━━━━━━━━━━✓━━━━━━━━━━━━━━━━━━━✓━━━━━━━━━━━━━━━━━━━●━━━━━━━━━━━━  │
│   1. Upload           2. Select Files      3. Parse             4. Review       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─ Asset Resolution (2 unresolved) ─────────────────────────────────────────┐ │
│  │                                                                           │ │
│  │  ⚠️ 2 assets need manual resolution:                                     │ │
│  │                                                                           │ │
│  │  1. "AAPL" (no ISIN) — 5 TX from degiro_2025.csv + ibkr_march.csv       │ │
│  │     Suggested: ● Apple Inc (AAPL) [HIGH]  ○ Apple Hospitality [LOW]      │ │
│  │     Search: [🔍 ___________]    [+ Create new]                           │ │
│  │                                                                           │ │
│  │  2. "XYZ Corp" — 2 TX from ibkr_march.csv                               │ │
│  │     Suggested: (none)                                                    │ │
│  │     Search: [🔍 ___________]    [+ Create new]                           │ │
│  │                                                                           │ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
│  ─── Transactions (78 total, 72 selected) ──────────────────────────────────── │
│                                                                                 │
│  Filter: [▼ All files] [▼ All types] [▼ All status]  [Select all] [Deselect]  │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │[☑]│ Date       │ Type │ Asset           │ Qty   │ Cash    │ File    │ St │  │
│  │───┼────────────┼──────┼─────────────────┼───────┼─────────┼─────────┼────│  │
│  │[☑]│ 2025-01-15 │ BUY  │ Vanguard FTSE   │ +10   │ -€1200  │ degiro  │ ✅ │  │
│  │[☑]│ 2025-01-20 │ BUY  │ ⚠️ AAPL (unres.)│ +5    │ -$850   │ ibkr    │ 🔗 │  │
│  │[☐]│ 2025-02-10 │ BUY  │ Vanguard FTSE   │ +10   │ -€1200  │ degiro  │ ⚠️ │  │
│  │   │ ↳ Likely duplicate (matches TX #1542 in DB)                          │  │
│  │[☑]│ 2025-02-15 │ DIV  │ Vanguard FTSE   │  0    │ +€20    │ degiro  │ ℹ️ │  │
│  │   │ ↳ Possible dup (same date+type+amount as pending row #3)             │  │
│  │[☑]│ 2025-03-01 │ BUY  │ ⚠️ XYZ (unres.) │ +100  │ -$500   │ ibkr    │ 🔗 │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  File breakdown: degiro_2025: 38/42 │ ibkr_march: 26/30 │ degiro_Q4: 8/8     │
│                                                                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│ [← Back]                                         [Import to Editor (72) ▶]      │
│                       (disabled if 0 selected OR unresolved assets remain)      │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Key behaviors**:

| Behavior | Detail |
|----------|--------|
| Merged TX list | All TX from all successfully-parsed files, unified, sorted by date |
| Duplicate detection | 3 sources: (a) within imported batch, (b) vs DB existing TX, (c) vs BulkModal pending ops |
| Default selection | Unique → ☑, Possible dup → ☑, Likely dup → ☐ |
| Asset resolution | Visible only if unresolved assets exist. Collapsible when all resolved |
| Asset dedup cross-file | Same fake symbol from 2 files → 1 card, shows source files |
| Status icons | ✅ unique, ⚠️ likely dup, ℹ️ possible dup, 🔗 unresolved asset |
| Unresolved TX rows | Highlighted amber bg, asset shows "⚠️ NAME (unres.)" |
| Resolve flow | Radio suggested + search all + create new (same as v4 M2 design) |
| Filters | By file, by TX type, by status |
| Select all/Deselect | Bulk toggle (respects active filter) |
| "Import to Editor" | Disabled if: 0 selected OR any selected TX has unresolved asset |
| File breakdown | Per-file counts for transparency |

---

## 4. Stepper Navigation: Back-Click Rules

| From → To | State Preservation |
|-----------|-------------------|
| Step 2 → Step 1 | Upload table preserved. File selections cleared |
| Step 3 → Step 1 | Parse results cleared. Upload table preserved |
| Step 3 → Step 2 | Parse results cleared. File selections preserved |
| Step 4 → Step 1 | Everything cleared except upload table |
| Step 4 → Step 2 | Merge/resolution cleared. File selections preserved. Will re-parse on Next |
| Step 4 → Step 3 | Merge/resolution cleared. Re-triggers parse (cached if files unchanged) |

**Principle**: Going back always clears FORWARD state (from that step onward). Selections AT the target step are preserved.

**Parse cache optimization**: If user goes Step 4 → Step 3 but file selection hasn't changed, parse results can be reused (skip re-parsing). Compare `selectedFiles` hash with previous run.

---

## 5. State Machine

```
                     Stepper click (any previous step)
                     ┌──────────────────────────────┐
                     │                              │
              ┌──────┴──────┐                       │
   open ─────▶│  STEP 1     │                       │
              │  Upload     │                       │
              └──────┬──────┘                       │
                     │ [Next]                        │
              ┌──────▼──────┐                       │
              │  STEP 2     │◀──────────────────────┤
              │  Select     │                       │
              └──────┬──────┘                       │
                     │ [Parse]                       │
              ┌──────▼──────┐                       │
              │  STEP 3     │◀──────────────────────┤
              │  Parsing    │                       │
              └──────┬──────┘                       │
                     │ [Continue] (all done)         │
              ┌──────▼──────┐                       │
              │  STEP 4     │◀──────────────────────┘
              │  Review     │
              └──────┬──────┘
                     │ [Import to Editor]
                     ▼
              onImportBatch(tx[])
              resetState()
              onClose()
```

---

## 6. Milestones (Revised)

| # | Milestone | Scope | Acceptance |
|---|-----------|-------|------------|
| **M1** | Skeleton + Step 1 + Step 2 | Wide modal, stepper, upload, broker panels, file selection | "I upload files, assign brokers, select files to parse" |
| **M2** | Step 3: Parse | Sequential parse with progress, per-file results | "I see each file parsed with results, errors shown per-file" |
| **M3** | Step 4: Review + Resolve + Import | Merge TX, duplicates, asset resolve, selection, handoff | "I resolve assets, manage duplicates, import to BulkModal grid" |
| **M4** | Polish + Back-Navigation + Edge Cases | Stepper click-back, parse cache, pending-ops dup check | "I can navigate back, state preserved, duplicates checked vs pending" |

### M1 Execution Status ✅ (2026-06-08)

Completed through 3 polish rounds:

| Round | Focus | Key Changes |
|-------|-------|-------------|
| **R1** | Core build | Wide modal, 4-step stepper, Step 1 upload+assign, Step 2 DataTable per broker, broker filtering EDITOR+, FileUploader hideActions, FilePreviewModal preview |
| **R2** | UX polish | Collapsible drop zone, DataTableToolbar bulk delete, double-click preview, context menu, per-file plugin column (replaces per-broker panel), smart plugin auto-select from `detection_priority`, pre-select uploaded files, file count in footer, parse validation |
| **R3** | Final fixes | Status moved to footer (amber warning / green check), discard modal → warning color, ImportPluginSelect module-level API cache, ColumnVisibilityToggle sync across tables (`additionalTableRefs`), DataTable `onColumnResize`/`setColumnWidth` for cross-table resize sync, column resize enabled |

**Deviations from plan**:
- **Plugin per-file** (not per-broker as planned) — user explicitly requested per-file granularity in Round 2
- **DataTableToolbar** used as standalone above table — DataTable's built-in bulkActions removed in favor of external toolbar for better UX positioning
- **`detection_priority`** added to `BRIMPluginInfo` backend schema — not in original plan, needed for smart plugin auto-selection
- **`compatible_plugins`** now sorted by priority desc from backend — drives auto-selection logic

---

## 7. Milestone 1: Skeleton + Step 1 + Step 2

### 7.1 Create ImportWizardModal.svelte

**File**: NEW `frontend/src/lib/components/transactions/modals/ImportWizardModal.svelte`

**Props**:
```ts
interface Props {
    open: boolean;
    zIndex?: number;
    onClose: () => void;
    onImportBatch: (creates: TXCreateItem[]) => void;
    existingOps?: PendingOp[];  // for M4 duplicate check vs pending
}
```

**Structure**:
- `ModalBase` with `maxWidth="6xl"` (or custom width ~1100px)
- Stepper bar component at top (4 numbered circles with labels + connecting lines)
- Content area swaps per step
- Footer with Back/Next buttons
- Unsaved guard on close (if any file uploaded or selections made)

### 7.2 StepperBar sub-component

Inline or extracted. Props: `{steps: string[], currentStep: number, onStepClick: (n) => void}`.
- Completed steps: filled circle + checkmark
- Current step: filled circle + number, bold label
- Future steps: hollow circle + number, muted label
- Click on completed step → `onStepClick(n)` (only if n < currentStep)

### 7.3 Step 1 implementation

- Global broker: `BrokerSearchSelect` (EDITOR+ only via `getEditableBrokers()`)
- Upload zone: `FileUploader` component (multi-file)
- On upload success → add to `uploadedFiles[]` with global broker assigned
- Table: rows with per-file broker dropdown + plugin dropdown + remove + preview
- Validation: client-side extension check before upload
- "Next" always enabled (Step 1 is optional)

### 7.4 Step 2 implementation

- Fetch files for each broker the user has EDITOR+ access on
- Display collapsible panels per broker
- Per-broker plugin dropdown (defaults from `broker.default_import_plugin`)
- Checkboxes per file. Pre-select files that were `uploadedNow === true` from Step 1
- Filter: broker dropdown + "Only unparsed" checkbox
- Status badges (UPLOADED/PARSED/STALE/ERROR)
- "Parse (N)" button footer-right, disabled if 0 selected

### 7.5 Wire BulkModal + /transactions page

- Same as v4: `{action: 'import'}` intent opens BulkModal empty, auto-launches wizard
- Replace `ImportBridgeModal` reference with `ImportWizardModal`
- Toolbar "Import" button to re-open wizard

### 7.6 i18n keys (M1)

```
importWizard.title, importWizard.step1Title, importWizard.step2Title
importWizard.step3Title, importWizard.step4Title
importWizard.globalBroker, importWizard.uploadHint, importWizard.uploadMultiHint
importWizard.assignBroker, importWizard.brokerRequired
importWizard.selectFiles, importWizard.selectedCount
importWizard.filterBrokers, importWizard.onlyUnparsed
importWizard.pluginDefault, importWizard.pluginOverride
importWizard.next, importWizard.parse, importWizard.back, importWizard.cancel
importWizard.noFiles, importWizard.noBrokers
importWizard.preSelectedHint
importWizard.fileStatus.uploaded, .parsed, .stale, .error
```

---

## 8. Milestone 2: Step 3 (Parse)

### 8.1 Parse engine

```ts
async function doParseAll() {
    for (const file of parseResults) {
        if (file.status !== 'pending') continue;
        file.status = 'parsing';
        try {
            const res = await zodiosApi.post(`/files/${file.fileId}/parse`, {
                plugin_code: file.pluginCode || undefined
            });
            file.response = res;
            file.status = 'done';
        } catch (e) {
            file.status = 'error';
            file.errorMessage = extractErrorMessage(e);
        }
    }
}
```

- Sequential (not parallel) — avoids overloading backend
- Progress bar: `completedCount / totalCount`
- Live summary updates after each file completes
- "Continue" enabled when all files have terminal status AND ≥1 done

### 8.2 Back from Step 3

- If parsing in progress → stop iterating (abort flag)
- Clear `parseResults`
- Return to Step 2 with selections preserved

### 8.3 i18n keys (M2)

```
importWizard.parsing, importWizard.parsingProgress
importWizard.parseComplete, importWizard.parseFailed
importWizard.txFound, importWizard.assetsDetected, importWizard.unresolvedAssets
importWizard.warnings, importWizard.errors, importWizard.continue
importWizard.fileDone, importWizard.fileError, importWizard.filePending
importWizard.summary
```

---

## 9. Milestone 3: Step 4 (Review + Resolve + Import)

### 9.1 Merge logic (on entering Step 4)

```ts
function mergeAllTransactions() {
    mergedTransactions = [];
    assetMappings = [];
    
    const assetMap = new Map<number, AssetMapping>();
    let globalIndex = 0;
    
    for (const result of parseResults.filter(r => r.status === 'done')) {
        for (const tx of result.response!.transactions) {
            mergedTransactions.push({
                index: globalIndex++,
                sourceFileId: result.fileId,
                tx,
                selected: true,
                duplicateStatus: 'unique',
                duplicateMatch: undefined,
            });
            
            if (isFakeAssetId(tx.asset_id) && !assetMap.has(tx.asset_id)) {
                const mapping = result.response!.asset_mappings
                    .find(m => m.fake_asset_id === tx.asset_id);
                if (mapping) {
                    assetMap.set(tx.asset_id, {
                        fakeAssetId: tx.asset_id,
                        extractedSymbol: mapping.extracted_symbol,
                        extractedIsin: mapping.extracted_isin,
                        extractedName: mapping.extracted_name,
                        candidates: mapping.candidates,
                        resolvedAssetId: mapping.selected_asset_id ?? null,
                        txCount: 0,
                        sourceFiles: [],
                    });
                }
            }
        }
    }
    
    // Compute txCount and sourceFiles for each mapping
    for (const mapping of assetMap.values()) {
        const relatedTx = mergedTransactions.filter(t => t.tx.asset_id === mapping.fakeAssetId);
        mapping.txCount = relatedTx.length;
        mapping.sourceFiles = [...new Set(relatedTx.map(t => {
            const pr = parseResults.find(r => r.fileId === t.sourceFileId);
            return pr?.fileName ?? t.sourceFileId;
        }))];
    }
    
    assetMappings = [...assetMap.values()];
    detectDuplicates();
}
```

### 9.2 Duplicate detection

Three sources:
1. **Backend-reported**: each parse response has duplicates vs existing DB
2. **Cross-file within batch**: same date+type+asset+amount across files
3. **vs BulkModal pending ops** (M4): same fields vs `existingOps` prop

Default checkbox logic:
- unique → ☑ selected
- possible → ☑ selected  
- likely → ☐ deselected

### 9.3 Asset resolution UI

Same design as v4:
- **Zone A**: Radio buttons for backend candidates (sorted by confidence)
- **Zone B**: Search input + filtered list of all user assets (fetched once, cached)
- **Zone C**: "+ Create new asset" → `AssetModal` at z:80

Auto-resolve: if backend already set `selected_asset_id` → pre-fill `resolvedAssetId`

### 9.4 Import button

```ts
function buildFinalTxList(): TXCreateItem[] {
    return mergedTransactions
        .filter(t => t.selected)
        .map(t => {
            const tx = {...t.tx};
            if (isFakeAssetId(tx.asset_id)) {
                const mapping = assetMappings.find(m => m.fakeAssetId === tx.asset_id);
                tx.asset_id = mapping?.resolvedAssetId ?? tx.asset_id;
            }
            return tx;
        });
}
```

Disabled if: 0 selected OR any selected TX references unresolved asset.

### 9.5 i18n keys (M3)

```
importWizard.review, importWizard.resolveAssets, importWizard.unresolvedCount
importWizard.resolveHint, importWizard.suggested, importWizard.searchAll
importWizard.createNew, importWizard.autoResolved
importWizard.confidence.exact, .high, .medium, .low
importWizard.likelyDuplicate, importWizard.possibleDuplicate, importWizard.unique
importWizard.matchesDB, importWizard.matchesPending, importWizard.matchesBatch
importWizard.selectedCount, importWizard.selectAll, importWizard.deselectAll
importWizard.filterByFile, importWizard.filterByType, importWizard.filterByStatus
importWizard.fileBreakdown, importWizard.importToEditor
importWizard.importDisabledUnresolved, importWizard.importDisabledEmpty
```

---

## 10. Milestone 4: Polish + Back-Navigation + Edge Cases

### 10.1 Stepper click-back

```ts
function onStepClick(target: number) {
    if (target >= currentStep) return;
    // Clear forward state
    if (target <= 2) { parseResults = []; }
    if (target <= 3) { mergedTransactions = []; assetMappings = []; }
    currentStep = target;
}
```

### 10.2 Parse cache

If user returns to Step 3 but `selectedFiles` haven't changed since last parse:
- Skip re-parsing, reuse `parseResults`
- Show "Using cached results" badge
- User can force re-parse with a "Re-parse" button

### 10.3 Pending ops duplicate check

```ts
function detectPendingOpDuplicates() {
    if (!existingOps?.length) return;
    for (const mt of mergedTransactions) {
        const match = existingOps.find(op =>
            op.fields.date === String(mt.tx.date) &&
            op.fields.type === mt.tx.type &&
            op.fields.asset_id === mt.tx.asset_id
        );
        if (match) {
            mt.duplicateStatus = 'possible';
            mt.duplicateMatch = 'Matches pending row in editor';
        }
    }
}
```

### 10.4 BulkModal integration (from v4 M4 — unchanged)

- `txCreateItemToPendingOp()` converter
- `linkPairedImportOps()` for paired TX
- Replace stub `onImportBatch` with real conversion
- Multi-cycle: re-open wizard adds more rows to grid

### 10.5 i18n keys (M4)

```
importWizard.cachedResults, importWizard.reparse
importWizard.importedCount, importWizard.discardConfirm
importWizard.matchesPendingOp
```

---

## 11. Files to Create / Modify

| Action | File | Milestone |
|--------|------|-----------|
| **REMOVE** | `ImportBridgeModal.svelte` | M1 (replaced) |
| **CREATE** | `ImportWizardModal.svelte` | M1–M3 |
| **MODIFY** | `TransactionBulkModal.svelte` | M1 (intent) + M4 (converter) |
| **MODIFY** | `modals/index.ts` | M1 |
| **MODIFY** | `+page.svelte` (transactions) | M1 |
| **MODIFY** | `en.json`, `it.json`, `fr.json`, `es.json` | M1–M4 |
| **KEEP** | `isFakeAssetId.ts` | Already created in v4 M1 |

---

## 12. Reusable Components

| Need | Component | Status |
|------|-----------|--------|
| Modal container | `ModalBase` (maxWidth="6xl") | Existing |
| Broker select | `BrokerSearchSelect` | Existing |
| File upload | `FileUploader` | Existing |
| File preview | `FilePreviewModal` | Existing |
| Plugin select | `ImportPluginSelect` | Existing (from v4 M1) |
| Asset create | `AssetModal` | Existing |
| Confirm discard | `ConfirmModal` | Existing |
| Error banners | `InfoBanner` | Existing |
| Loading/spinner | `LoadingSpinner` | Existing |
| **Stepper bar** | **NEW** (inline or extracted) | M1 |
| **Broker file panel** | **NEW** (collapsible broker section with checkboxes) | M1 |

---

## 13. Design Rules Summary

| Rule | Source |
|------|--------|
| Wide modal (6xl), not page | User: "non serve una pagina dedicata" |
| 4-step numbered stepper | User: "stepper orizzontali con numeri" |
| Multi-file native | User: "5 file tutti assieme" |
| Broker global + per-file override | User: "broker globale, poi per singolo file" |
| Plugin per-broker (not per-file) | Simplification: 99% same plugin per broker |
| Output = TXCreateItem[] → BulkModal | User: "wizard è solo un ponte" |
| Back-click via stepper preserves state | User: "tornare al passo 1 dal 4" |
| Forward state cleared on back | File changes invalidate parse results |
| Step 1 optional (can be empty) | Files may already exist on brokers |
| Parse sequential (not parallel) | Backend simplicity, clear progress |
| Duplicate detection: 3 sources | batch-internal + DB + pendingOps |
| Asset dedup cross-file | Same symbol from N files = 1 resolution card |
| Import disabled if unresolved selected | No fake IDs in output |

---

## 14. Risk Assessment

| Risk | Mitigation |
|------|------------|
| Modal too complex (4 steps in overlay) | maxWidth 6xl gives ~1100px. Enough for table + sections |
| Parse all sequential = slow for many files | Per-file progress. Future: parallel with concurrency limit |
| Back-navigation state complexity | Clear forward only. Hash-compare for parse cache |
| Duplicate detection accuracy | Backend primary. Cross-file and pending-ops are best-effort |
| Large TX count (200+) in Step 4 | Filters help focus. Future: virtualized list |
| Asset resolution blocking import | Clear UX: button disabled + tooltip explaining why |

---

## 15. Future Enhancements (not in scope)

| Feature | Priority | Notes |
|---------|----------|-------|
| Auto-detect broker via account code | High | See TODO_FUTURI.md entry |
| Per-file plugin override in Step 2 | ~~Low~~ | ✅ Done in M1 R2 — per-file plugin column with smart auto-selection |
| Parallel parse (concurrency 2-3) | Medium | After sequential proves stable |
| Direct commit (skip BulkModal) | None | User explicitly rejected |
| Drag-reorder files | Low | Nice UX, not essential |

---

## 16. Relationship to v4 Plan

This plan **supersedes** `plan-phase07Part5-BRIMImportBridge.prompt.md` (v4). The v4 plan and its M1 execution log remain as historical reference.

**Salvaged from v4 M1** (already implemented, keep):
- `isFakeAssetId.ts` utility
- `ImportPluginSelect` component
- i18n keys `brimImport.*` (extend/rename to `importWizard.*`)
- BulkModal `{action: 'import'}` intent plumbing
- `txCreateItemToPendingOp()` design (M4)
- `linkPairedImportOps()` design (M4)

**Deleted from v4** (no longer applicable):
- `ImportBridgeModal.svelte` → replaced by `ImportWizardModal.svelte`
- Single-file-per-cycle pattern
- Mode-switching breadcrumb navigation
- OSS.14, OSS.17 decisions


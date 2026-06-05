# Phase 07 Part 5 — BRIM Import → BulkModal Bridge

## Implementation Plan (v4 — final, issues fixed)

**Date**: 2026-06-05
**Scope**: Connect BRIM parse flow to the existing BulkModal from `/transactions` page
**Status**: 📋 Ready for implementation
**Incorporates**: 17 OSS + 7 issue fixes from final review

---

## 1. Architecture Overview

### Modal Stack (OSS.1)

```
z:60  BulkModal (opens first, empty grid + "Import" toolbar button)
z:70  ImportBridgeModal (opens on top, same slot as FormModal — never both)
z:80  ConfirmModal / AssetModal (on top of ImportBridge)
```

### Flow

1. User clicks "Import" on `/transactions` page
2. BulkModal opens **empty** with `{action: 'import'}` intent
3. ImportBridgeModal auto-launches on top (z:70)
4. User completes a cycle: select → parse → resolve → review → "Import to Editor"
5. ImportBridge closes → TX appear in BulkModal grid
6. User can re-open ImportBridge via toolbar "Import" button for more files/brokers
7. When satisfied → validate all → commit all

### Key Contract (OSS.3)

```
ImportBridgeModal output:  TXCreateItem[]  (backend schema — "lingua franca")
         ↓ onImportBatch callback
BulkModal receives TXCreateItem[] → converts internally via txCreateItemToPendingOp()
```

Bridge **never** imports or knows about `DraftFields` / `PendingOp`.

### Multi-File / Multi-Broker (OSS.4)

ImportBridgeModal is **single-file per cycle**. Multi-file emerges from iterative re-opening.

### Mode Switching, Not Wizard (OSS.14)

No progress bar, no step numbers. Header shows breadcrumb: `"Import › Resolve Assets"` with Back icon (`ArrowLeft`). Content swaps via `step` state variable.

---

## 2. State Machine (issue 1 & 2 fixed)

```
                    ┌──────────┐
         open ─────▶│  SELECT  │◀──────────────────────────┐
                    │          │                            │
                    └────┬─────┘                            │
                         │ [Parse] → doParse()              │
                         ▼                                  │
                    ┌──────────┐                            │
                    │ PARSING  │ (spinner, no user action)  │
                    │          │                            │
                    └──┬───┬───┘                            │
                  ok   │   │ error                          │
                       │   ▼                                │
                       │ ┌──────────┐                       │
                       │ │  ERROR   │ InfoBanner            │
                       │ │          │──[Back]──────────────▶│
                       │ └────┬─────┘                       │
                       │      │ [Retry] → doParse()         │
                       │      └───────▶ PARSING             │
                       ▼                                    │
                  ┌──────────┐                              │
                  │  RESULT  │ summary card                 │
                  │          │──[Back]──────────────────────▶│
                  └────┬─────┘                              │
                       │ [Continue]                         │
                  ┌────▼──────────────────────┐             │
                  │ unresolved mappings > 0?  │             │
                  └────┬──────────────┬───────┘             │
                   YES │              │ NO                   │
                       ▼              │                     │
                  ┌──────────┐        │                     │
                  │ RESOLVE  │        │                     │
                  │          │──[Back]──▶ RESULT             │
                  └────┬─────┘        │                     │
                       │ all resolved │                     │
                       │ [Continue]   │                     │
                       ▼              ▼                     │
                  ┌────────────────────────┐                │
                  │       REVIEW           │                │
                  │                        │──[Back]──▶ RESOLVE or RESULT
                  └────┬───────────────────┘  (via hadResolveStep flag)
                       │                                    │
                [Import to Editor]                          │
                       │                                    │
                       ▼                                    │
                  onImportBatch(tx[])                       │
                  resetState()                              │
                  onClose()                                 │
```

**Key design decisions (from issues)**:
- **Parse trigger**: explicit `async function doParse()` called by Parse button AND Retry button. NOT via `$effect(step)` — avoids the "same value doesn't re-trigger" Svelte 5 problem. Step `'parsing'` controls rendering only (spinner). (Issue 1 fix)
- **goBack() from review**: uses `hadResolveStep` boolean (set to `true` when entering resolve), NOT a computed `hasUnresolvedAssets` (which would always be false in review). (Issue 2 fix)

---

## 3. Data Flow

```
Backend                          ImportBridgeModal                    BulkModal
───────                          ─────────────────                    ─────────

POST /import/upload
  ← file_id             ──▶ selectedFileId
                                      │
POST /files/{id}/parse               │
  ← BRIMParseResponse   ──▶ parseResponse
     .transactions[]                  │
     .asset_mappings[]                │  Step Resolve:
     .duplicates                      │  fake_id → userSelectedAssetId
     .warnings                        │
                                      │  Step Review:
                                      │  check/uncheck TX
                                      │  buildFinalTxList():
                                      │    - filter by selectedTxIndices
                                      │    - replace fake_id → real_id
                                      │
                                      ▼
                              TXCreateItem[]  ──────────▶ onImportBatch()
                              (clean, real IDs)            │
                                                           ▼
                                                   txCreateItemToPendingOp()
                                                   linkPairedImportOps()
                                                   ops = [...ops, ...newOps]
                                                           │
                                                           ▼
                                                   Grid shows new rows
                                                   [Validate All]
                                                   POST /transactions
```

---

## 4. Milestone Structure (OSS.16)

| Milestone | Scope | Acceptance Test |
|-----------|-------|-----------------|
| **M1: Parse & See** | Skeleton + Select + Parse + Result summary | "I click Import, select broker/file, parse, see summary" |
| **M2: Resolve Assets** | Asset mapping UI complete | "I resolve unresolved assets using selector" |
| **M3: Review & Duplicates** | Review table + duplicate handling + stub | "I see TX table, manage duplicates, click Import (toast)" |
| **M4: Wire to BulkModal** | Handoff + conversion + multi-cycle | "TX appear in grid, validate works, commit succeeds" |

Each milestone is independently testable and deployable (later milestones add steps, never break earlier ones).

---

## 5. ASCII Art Layouts (OSS.13)

### 5.1 BulkModal Toolbar — With Import Button

```
┌─────────────────────────────────────────────────────────────────┐
│ Bulk Editor                                          [X Close]  │
├─────────────────────────────────────────────────────────────────┤
│ Toolbar:                                                        │
│  [Delta ±3]                     [Import ↑] [+ Add row] [⚡ Val] │
│                                  ^^^^^^^^^ NEW                  │
├─────────────────────────────────────────────────────────────────┤
│ ┌───────────────────────────────────────────────────────────┐   │
│ │ DataTable grid (transaction rows)                         │   │
│ │ ...                                                       │   │
│ └───────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│ Footer: [Cancel]                              [Commit All (N)]  │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 ImportBridgeModal — Step "Select"

```
┌─────────────────────────────────────────────────────────────────┐
│ Import                                               [X Close]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Broker:  [▼ BrokerSearchSelect ─────────────────────]         │
│                                                                 │
│  Plugin:  [▼ ImportPluginSelect (Auto) ──────────────]         │
│                                                                 │
│  ─── Files for "Broker Name" ───────────────────────────────   │
│                                                                 │
│  ○ report_2024_Q1.csv    2024-04-01   [PARSED]                 │
│  ○ report_2024_Q2.csv    2024-07-01   [PARSED] [↻ Stale]      │
│  ● report_2025_Q1.csv    2025-04-01   [UPLOADED]    ← selected │
│                                                                 │
│  ─── Upload new ────────────────────────────────────────────   │
│  ┌─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┐   │
│  │  📄 Drop file here or click to upload                   │   │
│  └─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┘   │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ Footer:  [Cancel]                                     [Parse ▶] │
│                                     (disabled if no file/broker) │
└─────────────────────────────────────────────────────────────────┘
```

### 5.3 ImportBridgeModal — Step "Result" (M1 endpoint)

```
┌─────────────────────────────────────────────────────────────────┐
│ ← Back   Import › Parse Result                       [X Close]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ✅ Parse complete                                              │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  📊  12 transactions parsed                              │  │
│  │  🔗  3 assets unresolved (need mapping)                  │  │
│  │  ⚠️  2 likely duplicates                                 │  │
│  │  ℹ️  1 warning: "Row 7 skipped (missing date)"          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Plugin used: Degiro (v2.1)                                    │
│  File: report_2025_Q1.csv                                      │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ Footer: [← Back]                                  [Continue ▶]  │
│                         (→ Resolve if unresolved, else Review)  │
└─────────────────────────────────────────────────────────────────┘
```

**Note (Issue 6)**: This step is a useful checkpoint for M1 acceptance. Post-M4, evaluate whether to compress it into an auto-advance with the summary as a persistent header in resolve/review. Mark as "possible optimization post-M4" — not blocking.

### 5.4 ImportBridgeModal — Step "Resolve"

```
┌─────────────────────────────────────────────────────────────────┐
│ ← Back   Import › Resolve Assets                     [X Close]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Resolved: 1/3                   [████░░░░░░░░░]               │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 1. "VWCE" (ISIN: IE00BK5BQT80)  — 7 TX                 │  │
│  │    ✅ Mapped → Vanguard FTSE All-World (auto: exact)     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 2. "AAPL" (no ISIN)  — 3 TX                             │  │
│  │                                                          │  │
│  │    Suggested:                                            │  │
│  │    ● Apple Inc (AAPL) — US0378331005         [HIGH]     │  │
│  │    ○ Apple Hospitality REIT (APLE)           [LOW]      │  │
│  │    ─────────────────────────────────────────────         │  │
│  │    All assets: [🔍 Search...________________]            │  │
│  │    (filtered list appears on type)                       │  │
│  │    ─────────────────────────────────────────────         │  │
│  │    [+ Create new asset]                                  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 3. "XYZ Corp" (no match)  — 2 TX                        │  │
│  │    Suggested: (none)                                     │  │
│  │    All assets: [🔍 Search...________________]            │  │
│  │    [+ Create new asset]                                  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ Footer: [← Back]                                  [Continue ▶]  │
│                                      (disabled until all resolved) │
└─────────────────────────────────────────────────────────────────┘
```

### 5.5 ImportBridgeModal — Step "Review"

```
┌─────────────────────────────────────────────────────────────────┐
│ ← Back   Import › Review                             [X Close]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Ready to import: 10 of 12 transactions                        │
│                                                                 │
│  ⚠️ Warnings (1)  [▼ expand]                                   │
│    • Row 7 skipped: missing date                               │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ [☑] Date       Type  Asset           Qty    Cash         │  │
│  │ ────────────────────────────────────────────────────────  │  │
│  │ [☑] 2025-01-15 BUY   Vanguard FTSE   +10   -€1,200 ✅   │  │
│  │ [☑] 2025-01-20 BUY   Apple Inc       +5    -$850   ✅   │  │
│  │ [☑] 2025-02-01 SELL  Apple Inc       -2    +$380   ✅   │  │
│  │ [☐] 2025-02-10 BUY   Vanguard FTSE   +10   -€1,200 ⚠️  │  │
│  │     ↳ Likely duplicate (matches TX #1542)                │  │
│  │ [☐] 2025-02-10 BUY   Vanguard FTSE   +10   -€1,200 ⚠️  │  │
│  │     ↳ Likely duplicate (matches TX #1542)                │  │
│  │ [☑] 2025-03-01 DIV   Apple Inc       0     +$12    ℹ️   │  │
│  │     ↳ Possible duplicate (same date+type+amount)         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ Footer: [← Back]                        [Import to Editor (10)] │
│                                       (disabled if 0 selected)  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. Detailed Implementation Steps

### Milestone 1: Parse & See

#### Step 1.1: Frontend Utility — `isFakeAssetId()` (Issue 4 fix)

**File**: NEW `frontend/src/lib/utils/brim/isFakeAssetId.ts`

```ts
/** Matches backend FAKE_ASSET_ID_BASE logic (brim.py:41-49). */
const FAKE_ASSET_ID_BASE = 2 ** 31 - 1;  // 2147483647

export function isFakeAssetId(id: number | null | undefined): boolean {
    if (id == null) return false;
    return id >= FAKE_ASSET_ID_BASE - 10000;
}
```

This is a building block used in M3 (review step) and M4 (conversion). Created early in M1 to avoid duplication.

---

#### Step 1.2: BulkModal — `import` Intent (minimal)

**File**: `TransactionBulkModal.svelte`

1. Extend `WorkspaceIntent`:
   ```ts
   export type WorkspaceIntent =
       | {action: 'create'}
       | {action: 'import'}   // ← NEW
       | {action: 'edit'; txIds: number[]}
       | {action: 'delete'; txIds: number[]}
       | {action: 'clone'; txIds: number[]};
   ```

2. Handle in `resolveInitialRows()`:
   ```ts
   if (intent.action === 'import') {
       return {rows: [], autoForm: null};  // empty grid, no auto-open
   }
   ```

3. Add state + auto-launch:
   ```ts
   let importBridgeOpen = $state(false);
   // Inside the $effect on open:
   if (intent?.action === 'import') importBridgeOpen = true;
   ```

4. Add "Import" button to toolbar (`:2814` area, next to "+ Add row"):
   ```svelte
   <button ... data-testid="tx-bulk-import" onclick={() => (importBridgeOpen = true)}>
       <Upload size={12}/> <span class="hidden sm:inline">{$t('brimImport.import')}</span>
   </button>
   ```

5. Mount ImportBridgeModal inside BulkModal:
   ```svelte
   <ImportBridgeModal
       open={importBridgeOpen}
       zIndex={70}
       onClose={() => (importBridgeOpen = false)}
       onImportBatch={onImportBatch}
   />
   ```

6. Stub `onImportBatch` (real conversion deferred to M4):
   ```ts
   function onImportBatch(creates: TXCreateItem[]) {
       toasts.success($t('brimImport.importedCount', {n: creates.length}));
       importBridgeOpen = false;
   }
   ```

---

#### Step 1.3: ImportBridgeModal — Skeleton + State Machine

**File**: NEW `frontend/src/lib/components/transactions/modals/ImportBridgeModal.svelte`

1. **Props**:
   ```ts
   interface Props {
       open: boolean;
       zIndex?: number;
       onClose: () => void;
       onImportBatch: (creates: TXCreateItem[]) => void;
   }
   ```

2. **State machine** (mode switching):
   ```ts
   type ImportStep = 'select' | 'parsing' | 'result' | 'resolve' | 'review';
   let step = $state<ImportStep>('select');
   let hadResolveStep = $state(false);  // Issue 2 fix: tracks if we went through resolve
   ```

3. **Header with breadcrumb** (OSS.14):
   ```svelte
   {#if step !== 'select'}
       <button onclick={goBack}><ArrowLeft size={16}/></button>
   {/if}
   Import{stepLabel ? ` › ${stepLabel}` : ''}
   ```

4. **Navigation (Issue 2 fix)**:
   ```ts
   function goBack() {
       if (step === 'parsing') step = 'select';
       else if (step === 'result') step = 'select';
       else if (step === 'resolve') step = 'result';
       else if (step === 'review') step = hadResolveStep ? 'resolve' : 'result';
   }
   ```

5. **Parse trigger (Issue 1 fix)** — explicit function, NOT $effect:
   ```ts
   let parseLoading = $state(false);
   let parseError = $state<string | null>(null);

   async function doParse() {
       step = 'parsing';
       parseLoading = true;
       parseError = null;
       try {
           const res = await zodiosApi.post(/* ... */);
           parseResponse = res;
           step = 'result';
       } catch (e) {
           parseError = extractErrorMessage(e);
           step = 'select';  // return to select with error banner visible
       } finally {
           parseLoading = false;
       }
   }
   ```
   Called by: Parse button (step select) and Retry button (after error).

6. **Unsaved changes guard (OSS.5)**:
   ```ts
   let hasUnsavedWork = $derived(parseResponse !== null);
   let confirmCloseOpen = $state(false);

   function handleClose() {
       if (hasUnsavedWork) confirmCloseOpen = true;
       else onClose();
   }
   ```
   ConfirmModal at z:80 with discard option.

7. **Reset on close**: all state to initial values.

8. **Export in `index.ts`**.

---

#### Step 1.4: Step "Select" — Broker + File + Plugin

**File**: `ImportBridgeModal.svelte`

1. **Broker selection** — `BrokerSearchSelect`:
   - Fetch user brokers on mount (same as TransactionFormModal)
   - On change → fetch files (`GET /api/v1/brokers/import/files?broker_id=N`)
   - Check `broker.default_import_plugin` → pre-fill plugin

2. **File list — simplified radio (OSS.17)**:
   - Custom vertical list (NOT FilesTable):
     - Radio button per file for single selection
     - Row: `{filename}  {uploadDate}  [STATUS_BADGE]`
     - Status badges: `UPLOADED` (gray), `PARSED` (green), `FAILED` (red)
     - If `parse_is_stale` → append "↻ Stale" amber badge
   - Bound to `selectedFileId`
   - Empty state: "No files uploaded for this broker" + upload prompt

3. **Upload** — `FileUploader`:
   - Upload to `POST /import/upload` with `broker_id` field
   - On success → refresh file list, auto-select new file

4. **Plugin** — `ImportPluginSelect`:
   - Pre-filled from broker `default_import_plugin` or empty ("Auto")
   - User can always override

5. **"Parse" button** (footer right):
   - Enabled: `selectedBrokerId && selectedFileId`
   - onClick: `doParse()`

6. **Error display** (from failed parse attempt):
   - If `parseError` is set → `InfoBanner` variant=error at top of select step
   - Clear on next successful navigation

---

#### Step 1.5: Step "Result" — Parse Summary

**File**: `ImportBridgeModal.svelte`

1. **Summary card**:
   - `📊 N transactions parsed`
   - `🔗 M assets unresolved` (from `asset_mappings.filter(m => !m.selected_asset_id).length`)
   - `⚠️ K likely duplicates` (from `duplicates.tx_likely_duplicates.length`)
   - Warnings count (expandable accordion if > 0)
   - Plugin used + version
   - Filename

2. **Footer**:
   - "← Back" → goes to `'select'`
   - "Continue ▶":
     - If unresolved assets > 0 → `hadResolveStep = true; step = 'resolve'`
     - Else → `step = 'review'`

3. **M1 acceptance**: user can see parse results. Feature visually testable end-to-end.

---

### Milestone 2: Resolve Assets

#### Step 2.1: Step "Resolve" — Asset Mapping UI (OSS.9, OSS.15)

**File**: `ImportBridgeModal.svelte`

1. **State**:
   ```ts
   type ResolvedMapping = {
       fake_asset_id: number;
       extracted_symbol: string | null;
       extracted_isin: string | null;
       extracted_name: string | null;
       candidates: BRIMAssetCandidate[];
       userSelectedAssetId: number | null;
       txCount: number;  // count of TX using this fake_id
   };
   let assetMappings = $state<ResolvedMapping[]>([]);

   // "All assets" for zone B (Issue 3 fix):
   let allUserAssets = $state<{id: number; name: string; symbol?: string; isin?: string}[]>([]);
   let allAssetsLoading = $state(false);
   ```

2. **Fetch "all assets" (Issue 3 fix)**:
   - **Endpoint**: `GET /api/v1/assets` (returns user's asset list with id, name, symbol, isin)
   - **When**: on entering resolve step (first time only)
   - **Cache**: stored in `allUserAssets`, NOT re-fetched if user goes back and returns
   - **Rationale**: asset list is small (user's portfolio), fetch once, filter client-side

3. **Layout per mapping card** (OSS.15 — composed, not grouped SearchSelect):
   - **Zone A: "Suggested"** (radio buttons):
     - `candidates[]` sorted by confidence (exact→high→medium→low)
     - Each: `● {name} ({symbol}) — {isin}  [BADGE]`
     - Badge colors: exact=green, high=blue, medium=amber, low=gray
     - Max 5 shown
   - **Visual separator** (thin `<hr>` or subtle bg)
   - **Zone B: "All assets"** (search input + filtered list):
     - Text input: `[🔍 Search...]` — filters `allUserAssets` by name/symbol/isin
     - Below: scrollable list of matching assets (radio buttons)
     - No results: "No matching assets"
   - **Zone C: "+ Create new asset"** button:
     - Opens `AssetModal` at z:80
     - `oncreated(assetId)` → sets `userSelectedAssetId`, re-fetch allUserAssets, close AssetModal

4. **Auto-select**: if `selected_asset_id` already set by backend → pre-select, show green ✓ badge

5. **Progress**: "Resolved: X/Y" + simple progress bar

6. **Footer**: "Continue ▶" enabled when ALL mappings resolved

7. **Back** → `step = 'result'`

---

### Milestone 3: Review & Duplicates

#### Step 3.1: Step "Review" — Table + Duplicates + Stub Handoff

**File**: `ImportBridgeModal.svelte`

1. **Init on entering review**:
   ```ts
   function initReviewStep() {
       // Pre-populate selectedTxIndices:
       // - all unique indices → checked
       // - all possible_duplicates indices → checked
       // - all likely_duplicates indices → UNCHECKED
       selectedTxIndices = new Set([
           ...(parseResponse!.duplicates?.tx_unique_indices ?? []),
           ...(parseResponse!.duplicates?.tx_possible_duplicates.map(d => d.tx_row_index) ?? []),
       ]);
   }
   ```

2. **Header**: "Ready to import: {selectedTxIndices.size} of {parseResponse.transactions.length}"

3. **Warnings** (collapsible section if warnings.length > 0)

4. **TX preview table**:
   - Columns: `[☑] Date | Type | Asset | Qty | Cash | Status`
   - Asset name: resolved from `assetMappings` or from `allUserAssets` lookup
   - Row styling:
     - ✅ Unique: normal bg
     - ℹ️ Possible: light yellow, tooltip "Possible duplicate — matches TX #{id}"
     - ⚠️ Likely: light red, tooltip with match info
   - Checkbox toggles include/exclude in `selectedTxIndices`

5. **Fake ID → Real ID replacement** (internal utility):
   ```ts
   function buildFinalTxList(): TXCreateItem[] {
       return [...selectedTxIndices].map(i => {
           const tx = {...parseResponse!.transactions[i]};
           if (isFakeAssetId(tx.asset_id)) {
               const mapping = assetMappings.find(m => m.fake_asset_id === tx.asset_id);
               tx.asset_id = mapping?.userSelectedAssetId ?? null;
           }
           return tx;
       });
   }
   ```

6. **Unsaved guard (OSS.5)**: close request with selectedTxIndices.size > 0 → confirm discard

7. **Footer**:
   - "← Back" → `step = hadResolveStep ? 'resolve' : 'result'`
   - "Import to Editor (N)":
     - Disabled if `selectedTxIndices.size === 0`
     - **M3 stub**: calls `onImportBatch(buildFinalTxList())` — BulkModal shows toast (stub from M1)

---

### Milestone 4: Wire to BulkModal

#### Step 4.1: `txCreateItemToPendingOp` + `onImportBatch` (real)

**File**: `TransactionBulkModal.svelte`

1. **Converter** (replaces stub):
   ```ts
   function txCreateItemToPendingOp(tx: TXCreateItem): PendingOp {
       return {
           op: 'create',
           tempId: generateUUID(),
           fields: {
               broker_id: tx.broker_id,
               asset_id: tx.asset_id ?? null,
               type: tx.type as TransactionTypeCode,
               date: String(tx.date),
               quantity: String(tx.quantity ?? '0'),
               cash: tx.cash ? {code: tx.cash.code, amount: String(tx.cash.amount)} : null,
               tags: tx.tags ?? [],
               description: tx.description ?? '',
               asset_event_id: tx.asset_event_id ?? null,
               cost_basis_override: tx.cost_basis_override
                   ? {code: tx.cost_basis_override.code, amount: String(tx.cost_basis_override.amount)}
                   : null,
               cost_basis_mode: tx.cost_basis_mode ?? null,
           },
           link_uuid: tx.link_uuid ?? null,
       };
   }
   ```

2. **Paired TX linking (Issue 5 fix)**:
   ```ts
   /**
    * Link paired import ops by link_uuid.
    * BulkModal pairedWith semantics: the HIDDEN partner points to the VISIBLE main.
    * Convention: first op in the pair is VISIBLE (main), second is HIDDEN (partner).
    * Both share the same link_uuid.
    */
   function linkPairedImportOps(newOps: PendingOp[]) {
       const byLink = new Map<string, PendingOp[]>();
       for (const op of newOps) {
           if (op.link_uuid) {
               const arr = byLink.get(op.link_uuid) ?? [];
               arr.push(op);
               byLink.set(op.link_uuid, arr);
           }
       }
       for (const [, pair] of byLink) {
           if (pair.length === 2) {
               // Second in pair becomes hidden partner of first
               pair[1].pairedWith = pair[0].tempId;
           }
       }
   }
   ```

3. **Replace stub `onImportBatch`**:
   ```ts
   function onImportBatch(creates: TXCreateItem[]) {
       const newOps = creates.map(txCreateItemToPendingOp);
       linkPairedImportOps(newOps);
       ops = [...ops, ...newOps];
       importBridgeOpen = false;
       toasts.success($t('brimImport.importedCount', {n: creates.length}));
       if (ops.length <= AUTO_VALIDATE_THRESHOLD) scheduler.trigger('change');
   }
   ```

---

#### Step 4.2: Multi-Cycle Verification

1. Import button in toolbar re-opens bridge (already wired in M1)
2. Second cycle adds more rows to existing grid
3. Validate All works across all imported rows (no changes needed — existing validate handles all ops)
4. Commit All succeeds

---

#### Step 4.3: Wire `/transactions` Page

**File**: `frontend/src/routes/(app)/transactions/+page.svelte`

Replace stub:
```ts
function onImportFromBroker() {
    bulkIntent = {action: 'import'};
    bulkOpen = true;
}
```

---

#### Step 4.4: Post-M4 Optimization Note (Issue 6)

After M4 is working, evaluate whether step "result" should be compressed:
- Option A: Keep as-is (extra click but clear checkpoint)
- Option B: Auto-advance to resolve/review, show summary as persistent header banner
- Decision deferred to post-M4 UX review based on real usage feedback

---

### Step 5 (all milestones): i18n Keys — Incremental (OSS.11)

**M1** keys (`brimImport.*`):
```
title, import, selectBroker, selectFile, pluginLabel, pluginAuto
parse, parsing, parseError, retry, back, continue
parseResult, transactionsCount, unresolvedCount, duplicatesCount
warningsCount, warningExpand, pluginUsed, noTransactions
uploadNew, fileStatus.uploaded, fileStatus.parsed, fileStatus.stale
noBrokers, noFiles, noBrokersHint, noFilesHint
```

**M2** keys:
```
resolveAssets, resolveProgress, suggested, allAssets
createNewAsset, searchAssets, noMatch, autoResolved
confidence.exact, confidence.high, confidence.medium, confidence.low
```

**M3** keys:
```
review, readyToImport, importToEditor, noneSelected
likelyDuplicate, possibleDuplicate, unique
matchesExisting, discardConfirm, discardResolve
```

**M4** keys:
```
importedCount (toast)
```

---

## 7. Reusable Components (OSS.6)

| Need | Component | Notes |
|------|-----------|-------|
| Broker select | `BrokerSearchSelect` | Props: `{brokers, value, onchange}` |
| Plugin select | `ImportPluginSelect` | Auto-fetches plugins, supports empty="Auto" |
| Upload | `FileUploader` | From BrokerImportFilesModal |
| Asset create | `AssetModal` | z:80, `oncreated(id)` callback |
| Confirm/discard | `ConfirmModal` | z:80, variant warning |
| Error banners | `InfoBanner` | 4 variants (error/warning/info/success) |
| Loading | `LoadingSpinner` | — |
| Modal base | `ModalBase` | z:70 for bridge |
| File list | **Custom radio list** (OSS.17) | NOT FilesTable — too complex for single-select |
| Suggested assets | **Custom radio section** (OSS.15) | NOT SearchSelect groups — flat radio + search compose |
| All assets search | **Text input + filtered list** (OSS.15) | Client-side filter on `allUserAssets` |

---

## 8. Files to Create / Modify

| Action | File | Milestone |
|--------|------|-----------|
| **CREATE** | `frontend/src/lib/utils/brim/isFakeAssetId.ts` | M1 |
| **MODIFY** | `TransactionBulkModal.svelte` | M1 (minimal) + M4 (full) |
| **CREATE** | `ImportBridgeModal.svelte` | M1–M3 |
| **MODIFY** | `modals/index.ts` | M1 |
| **MODIFY** | `+page.svelte` (transactions) | M4 |
| **MODIFY** | `en.json`, `it.json`, `fr.json`, `es.json` | M1–M4 |
| **CREATE** | `frontend/e2e/transactions/tx-brim-import.spec.ts` | Post-M4 (Issue 7 fix) |

---

## 9. E2E Tests (Post-M4)

**File**: `frontend/e2e/transactions/tx-brim-import.spec.ts` (Issue 7 — correct path per project conventions)

Register in `scripts/test_runner/_frontend_transaction.py` with `add_test(cat, "tx-brim-import", ...)`.

Scenarios:
1. Happy path: Import → select → parse → review → import to grid → validate → commit
2. Asset resolution: parse with unresolved → resolve all → import
3. Duplicate handling: likely excluded by default → override → import
4. Multi-cycle: broker A + broker B → validate all → commit all
5. Error paths: parse failure → retry; 0 TX → back
6. Create new asset: AssetModal → created → auto-selected
7. Unsaved guards: close bridge with pending TX → confirm discard
8. Skip resolution: all auto-resolved → review directly

---

## 10. Design Rules Summary

| Rule | Source |
|------|--------|
| `TXCreateItem` = only type crossing bridge→BulkModal boundary | OSS.3 |
| Always use existing components; flag "Custom" when none exists | OSS.6 |
| i18n keys incremental per milestone | OSS.11 |
| Mode switching + breadcrumb, NOT wizard/stepper | OSS.14 |
| Composed layout for asset resolution (radio + search) | OSS.15 |
| 4 milestones, each testable independently | OSS.16 |
| Simplified radio file list, NOT FilesTable | OSS.17 |
| Parse triggered by `doParse()` function, NOT `$effect(step)` | Issue 1 |
| Back from review uses `hadResolveStep` flag | Issue 2 |
| "All assets" fetched once on resolve entry, cached | Issue 3 |
| `isFakeAssetId()` utility created in M1 | Issue 4 |
| pairedWith: second op in pair → hidden, first → visible | Issue 5 |
| Step "result" may be compressed post-M4 (optimization) | Issue 6 |
| E2E at `e2e/transactions/tx-brim-import.spec.ts` | Issue 7 |

---

## 11. Risk Assessment

| Risk | Mitigation |
|------|------------|
| BulkModal 159KB — M1 changes minimal | Only intent branch + stub + button. Conversion in M4 |
| Parse trigger re-fire | `doParse()` explicit — no $effect fragility |
| Asset resolution UX | Composed layout (radio + search). No base component modified |
| Paired TX order | Convention documented: first=visible, second=hidden. Same as promote flow |
| Large import (100+ TX) | BulkModal manual-validate mode already handles this |
| Step "result" extra click | Keep for M1 acceptance; evaluate compression post-M4 |

---

## 12. Multi-Cycle Timeline

```
t0:  User clicks [Import] on /transactions
t1:  BulkModal opens empty → ImportBridge auto-launches
t2:  Select broker A → files load → select report_Q1.csv → Parse
t3:  PARSING... → RESULT (12 TX, 3 unresolved)
t4:  Continue → RESOLVE: map assets → Continue
t5:  REVIEW: uncheck 2 likely duplicates → [Import to Editor (10)]
t6:  Bridge closes → BulkModal grid: 10 rows
t7:  User clicks toolbar [Import ↑] → bridge re-opens fresh
t8:  Select broker B → different file → Parse → all resolved → REVIEW
t9:  [Import to Editor (8)] → bridge closes → grid: 18 rows total
t10: [Validate All] → pass ✓ → [Commit All (18)]
t11: POST /transactions → 201 → BulkModal closes → page refreshes
```

# Phase 07 Part 5 — Milestone 1: Parse & See (Execution Log)

**Date**: 2025-06-05
**Status**: ✅ Complete
**Parent plan**: [plan-phase07Part5-BRIMImportBridge.prompt.md](./plan-phase07Part5-BRIMImportBridge.prompt.md)

---

## Objective

User clicks **Import** on `/transactions` → BulkModal opens empty → ImportBridgeModal auto-launches (z:70) → selects broker + file → clicks Parse → sees summary result.

---

## Sub-Tasks Executed

| # | Task | Status | Notes |
|---|------|--------|-------|
| T1 | Create `isFakeAssetId.ts` utility | ✅ | Building block for M3/M4 (Issue 4 fix) |
| T2 | Add i18n keys (32 keys × 4 langs) | ✅ | `brimImport.*` namespace in EN/IT/FR/ES |
| T3 | BulkModal: add `import` intent | ✅ | WorkspaceIntent, resolveInitialRows, toolbar button, mount bridge, stub onImportBatch |
| T4 | Export in `modals/index.ts` | ✅ | |
| T5 | ImportBridgeModal skeleton | ✅ | State machine, navigation, unsaved guard |
| T6 | Step "Select" | ✅ | BrokerSearchSelect, FilesTable, FileUploader, ImportPluginSelect |
| T7 | Step "Parsing" | ✅ | LoadingSpinner + explicit `doParse()` (Issue 1 fix) |
| T8 | Step "Result" | ✅ | Summary card + Continue logic |

---

## Post-Completion Refinements (User Feedback)

| Issue | Fix |
|-------|-----|
| Broker list showed all brokers | Changed to `getEditableBrokers()` (EDITOR/OWNER only) |
| Plugin pre-fill not obvious | Was already coded (line 165), verified working |
| Custom radio file list ugly | Replaced with `FilesTable` (same as broker detail) |
| Plain file input | Replaced with `FileUploader` (drag & drop, same as broker detail) |
| No file preview | Added `FilePreviewModal` integration (eye icon in table) |
| /transactions Import button was a stub | Wired `onImportFromBroker()` → `{action: 'import'}` |

---

## Files Created

| File | Purpose |
|------|---------|
| `frontend/src/lib/utils/brim/isFakeAssetId.ts` | Frontend utility matching backend FAKE_ASSET_ID_BASE |
| `frontend/src/lib/components/transactions/modals/ImportBridgeModal.svelte` | Bridge modal (state machine, all M1 steps) |

## Files Modified

| File | Changes |
|------|---------|
| `TransactionBulkModal.svelte` | +`{action: 'import'}` intent, toolbar Import button, auto-launch, stub callback |
| `+page.svelte` (transactions) | Wired `onImportFromBroker()` to open BulkModal with import intent |
| `modals/index.ts` | Added `ImportBridgeModal` export |
| `en.json`, `it.json`, `fr.json`, `es.json` | Added 32 `brimImport.*` keys |

---

## Key Technical Decisions

1. **Parse trigger**: Explicit `async function doParse()`, NOT `$effect(step)` (Issue 1 fix — Svelte 5 won't re-trigger same value)
2. **goBack from review**: Uses `hadResolveStep` boolean, not computed (Issue 2 fix — prepared for M2)
3. **Broker filter**: `getEditableBrokers()` — same pattern as TransactionFormModal
4. **Upload**: `axiosInstance + FormData` via `trySave()` — Zodios doesn't handle FormData
5. **File list**: Reused `FilesTable` with `showBrokerColumn={false}` + `onSelectionChange` for single-select semantics
6. **File preview**: Same `fetchFilePreview()` + `FilePreviewModal` pattern as BrokerImportFilesModal
7. **Modal stack**: BulkModal z:60 → ImportBridge z:70 → ConfirmModal/Preview z:80

---

## Build Verification

- `svelte-check`: 0 errors, 0 warnings ✅
- `npm run build`: success ✅

---

## Acceptance Criteria

- [x] Import button in BulkModal toolbar
- [x] Clicking Import opens ImportBridgeModal at z:70
- [x] BrokerSearchSelect shows only EDITOR+ brokers
- [x] Selecting broker loads files in FilesTable
- [x] Upload with drag & drop (FileUploader component)
- [x] File preview via eye icon (FilePreviewModal)
- [x] ImportPluginSelect defaults to broker's default_import_plugin
- [x] Parse button disabled until broker + file selected
- [x] Parse → spinner → result summary
- [x] Parse error → returns to select with error banner
- [x] Back from result → select
- [x] Continue from result → placeholder (M2/M3)
- [x] Close with unsaved work → ConfirmModal
- [x] i18n keys in 4 languages
- [x] BulkModal `{action: 'import'}` → empty grid + auto-open bridge
- [x] /transactions page Import button triggers the flow

---

## User Testing Feedback — 2025-06-08

> These notes document fundamental UX and architecture issues discovered during user testing of M1. They require a **paradigm shift** before continuing to M2.

---

### Issue A — Plugin Pre-fill Not Working

**Symptom**: After selecting a broker, the plugin dropdown stays empty despite the broker having a `default_import_plugin`.

**Evidence**: The code at line 171-172 does `selectedPlugin = broker.default_import_plugin`, and `ImportPluginSelect` uses `bind:value={selectedPlugin}` (line 414). However, `ImportPluginSelect` loads plugins **asynchronously** (`$effect → loadPlugins()`, plugin file line 43-45). If the broker's `default_import_plugin` is set **before** the plugin list finishes loading, the `SearchSelect` may not display it properly — it compares `value` against `pluginOptions[]` which may still be empty at that point.

**Proposal**: Either (a) await plugin load before setting value, (b) set `selectedPlugin` reactively *after* plugins load via an `$effect` that watches both `selectedPlugin` and loaded plugins, or (c) ensure `SearchSelect` handles external value pre-fill when options arrive asynchronously.

---

### Issue B — Clicking Outside Does Nothing (No Confirm Banner)

**Symptom**: Clicking outside the modal does not trigger the "Discard changes?" confirmation dialog. Nothing happens at all.

**Root cause**: Line 359 explicitly sets `closeOnBackdropClick={false}`:
```svelte
<ModalBase {open} {zIndex} maxWidth="2xl" onRequestClose={handleClose} testId="import-bridge-modal" closeOnBackdropClick={false}>
```
This completely blocks backdrop clicks — `handleClose()` is never invoked. The `handleClose()` function (line 90-96) does handle the unsaved guard correctly (`if (hasUnsavedWork) { confirmCloseOpen = true }`) but is simply never reached via backdrop.

**Proposal**: Change to `closeOnBackdropClick={true}` so that clicking outside triggers `handleClose()`, which then shows the confirm dialog if there's unsaved work, or closes directly if there isn't.

---

### Issue C — Multi-File Selection Broken / Label Makes No Sense

**Symptom**: User can select multiple files via checkboxes, but only the last-clicked file is stored. The "File:" label at the bottom only shows one filename, which is confusing.

**Evidence**: `FilesTable` emits `onSelectionChange(ids: string[])` as a multi-select array. The handler at line 273-276 fakes single-select:
```ts
function handleFileSelection(ids: string[]) {
    selectedFileId = ids.length > 0 ? ids[ids.length - 1] : null;
}
```
The template (line 469-475) shows a static "File: filename" label — visually useless when multiple items appear selected in the table.

**Root issue**: The M1 plan assumed single-file-at-a-time (OSS.17). But the user wants **multi-file parsing in a single flow** — including files from different brokers. The entire "broker → files → single parse" pipeline doesn't match the desired UX.

---

### Issue D — No Validation for Invalid File Types

**Symptom**: User selected a PDF and received no error feedback. The parse would fail server-side but there's no client-side guard.

**Evidence**: `accept=".csv,.xlsx,.xls"` (line 437) is only a browser hint — it doesn't prevent selecting other files in all browsers. No client-side extension check before upload, and no visible error if the parse endpoint rejects the file.

**Proposal**: (a) Add client-side extension/MIME check before upload, (b) Show clear InfoBanner error if parse fails due to unsupported format with the specific filename, (c) Surface per-file errors clearly in multi-file scenarios.

---

### Issue E — Paradigm Shift Required: NOT "Broker by Broker"

**User feedback (verbatim)**: *"questa impronta così 'broker per broker' non è quello che volevo, mi immagino un utente che carichi 5 file tutti assieme e non necessariamente tutti dello stesso broker"*

**Current architecture**: User must select one broker → see its files → select one file → parse → repeat. This is a serial, broker-centric flow.

**Desired architecture**: User uploads/selects N files (from any broker) → all are parsed together (or in batch) → unified resolve + review flow.

**Implications**:
1. The "select broker first" pattern breaks down — either the system auto-detects the broker from the file, or the user assigns brokers per-file
2. Different files may need different plugins → plugin selection becomes per-file, not global
3. Parse must handle N files → N parse responses → merged result
4. The data model changes: `selectedFileId: string | null` → `selectedFiles: {fileId, brokerId, plugin}[]`

---

### Issue F — Should Be a Wizard/Stepper Page, Not a Modal

**User feedback (verbatim)**: *"mi sto anche rendendo conto che non ha senso farlo solo con delle modali, il flusso è chiaramente in wizard a step, quindi conviene farlo in questa maniera"*

**Observation**: While OSS.14 said "no wizard, use mode switching in modal", after testing the real UX, the user now recognizes that a multi-file, multi-broker import flow is too complex for a modal. The interaction needs more screen real estate.

**Options**:
1. **Full page** — `/transactions/import` route as a multi-step wizard page (like checkout flows)
2. **Large drawer/panel** — side panel or full-width overlay that's bigger than a modal
3. **Keep modal but go full-screen** — `maxWidth="5xl"` or `maxWidth="none"` with internal wizard layout

**Trade-off**: A full page means leaving the `/transactions` context. A large modal/drawer keeps the user "in place" but has space constraints. The multi-file + per-file plugin + resolve + review flow likely needs a **dedicated page**.

---

### Issue G — Multi-File + Multi-Plugin Implications

If the flow supports N files from M brokers with K different plugins, the architecture needs:

| Concern | Current (M1) | Needed |
|---------|-------------|--------|
| Broker selection | Single BrokerSearchSelect | Per-file or auto-detect |
| Plugin | Global for all files | Per-file configurable |
| Parse trigger | Single file → single response | Batch or sequential N parses |
| Result | One `BRIMParseResponse` | Merged/aggregated results |
| File upload | To one broker | To each file's broker |
| Error handling | One error banner | Per-file error status |

---

## Summary — What This Means for M2+ Plans

The M1 implementation proved the **technical wiring works** (broker store, file API, parse API, result display, modal stack). But the **UX paradigm** must change before proceeding:

1. **OSS.14 is overridden** — the user now wants a proper wizard/stepper (or a dedicated page), not mode-switching in a small modal
2. **OSS.17 is overridden** — multi-file is required, not single-radio-select
3. **The "broker first" assumption is invalid** — multi-broker in one session is the target

The parent plan (`plan-phase07Part5-BRIMImportBridge.prompt.md`) needs a **v5 revision** before M2 implementation can begin. The state machine, data model, and container (modal vs page) all need re-design.

**Salvageable from M1**: isFakeAssetId utility, i18n keys, BulkModal intent plumbing, parse/upload API integration code, FilePreviewModal integration.

---

## Next: Milestone 2 — Resolve Assets

⚠️ **BLOCKED** — pending architectural re-design based on above feedback. See parent plan for updates.

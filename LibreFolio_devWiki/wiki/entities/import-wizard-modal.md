---
title: "ImportWizardModal"
category: entity
type: component
tags: [frontend, brim, import, wizard, modal, multi-file, asset-matching, duplicates, bulk]
related:
  - decisions/brim-broker-scoped
  - decisions/brim-parser-only
  - decisions/import-wizard-v5-paradigm
  - concepts/import-todo-signals
  - features/F-012
  - features/F-048
  - features/F-049
  - features/F-083
mkdocs: "developer/frontend/components/features/import-wizard.md"
---

# ImportWizardModal

## Role

`ImportWizardModal` is the primary frontend workflow for turning one or more broker
reports into reviewed transaction drafts. It does not write transactions itself. It
uploads and selects files, requests BRIM previews, unifies extracted asset identities,
collects explicit corrections, rechecks duplicates on the corrected data, and hands the
selected rows to `TransactionBulkModal`.

The modal is still presented as four numbered product stages, but the implementation is
a conditional seven-state machine:

```text
upload → select → analyze → [assets] → [fix] → [duplicates] → review
```

`assets`, `fix`, and `duplicates` appear only when their predicates require user work.

## Key Interfaces

### Input and output

```typescript
defaultBrokerId?: number | null
pendingCreateTransactions?: TransactionCreateItem[]
pendingDeleteTxIds?: number[]
onImportBatch: (creates: Array<{
    tx: TransactionCreateItem
    todos: ImportTodo[]
}>) => void
```

`defaultBrokerId` is only a preselection; the user can still assign a different broker
per file. Pending creates participate in frontend duplicate detection, while pending
deletes suppress database matches that are already scheduled to disappear.

### Data flow

```text
PendingFileEntry[]
  → FileSelection[]
  → ParsedFileResult[]
  → MergedTx[] + AssetResolution[]
  → selected TransactionCreateItem + ImportTodo drafts
```

Each merged row retains a stable wizard index and source-file id. Each bulk-editor row
then receives its own stable `tempId`; display sorting never replaces either identity.

## File and Parser Contract

- Step 1 accepts multiple files and gives every file exactly one `brokerId`.
- Upload uses multipart `POST /api/v1/brokers/import/upload` with `file`, required
  `broker_id`, and optional `custom_filename`.
- Step 2 lists accessible reports with `GET /api/v1/brokers/import/files` and repeated
  `broker_ids` query parameters, then selects a plugin per file.
- Step 3 parses each selected file through
  `POST /api/v1/brokers/import/files/{file_id}/parse` with JSON
  `{ plugin_code, broker_id }`.
- A single wizard session may therefore span several files and brokers. A flat Generic
  CSV file still belongs to exactly one broker; several currencies inside that broker
  file remain valid.
- The Generic CSV parser preserves supplied transaction values and row currencies,
  subject to schema/sign validation. It does not generate FX transactions.

## Asset Identity and Resolution

BRIM parsers use temporary **positive high IDs** beginning at
`FAKE_ASSET_ID_BASE = 2**31 - 1` and decrementing. `is_fake_asset_id()` recognizes the
reserved high range. Because every file starts from the same base, the merge layer
remaps each file's placeholders into a wizard-global sequence before grouping or
resolution.

Asset creation and linking on a first import are intentionally explicit:

- Backend candidate search combines a primary ISIN match with matches in
  `identifier_other`, deduplicating by asset id and retaining the strongest confidence.
- Ticker and name fallbacks run only when stronger identifier evidence produced no
  candidates.
- Exactly one distinct current candidate may be selected automatically.
- Multiple distinct candidates remain unresolved for manual choice or merge.
- Creating a missing asset is a user action. The parser does not create assets or choose
  a price provider.
- After an asset or identifier edit, the wizard refreshes the asset catalog and candidate
  results without rewriting cached parser facts or the user's manual selection.

This is the intended first-import workflow, not a generic-parser matching failure.

## Full Asset Inspection and Nested Modals

Opening an asset from the review step uses `loadAssetEditData()`, which combines the asset
list record, the bulk metadata read, and provider assignments. The inspector therefore
opens with full identifiers, classification, currency, provider configuration, and
provider URLs instead of treating a summary projection as complete edit data.

Classification edits preserve PATCH intent:

- an omitted `classification_params` field means no classification change;
- an explicit top-level `null` clears all classification;
- inside a partial classification patch, omitted blocks remain unchanged and explicit
  `null` clears only that block;
- sector and geographic distributions are atomic blocks rather than deep-merged maps.

The form computes a per-field classification diff before PATCH, and the backend preserves
explicit nested nulls while shallow-merging only supplied blocks. Consequently, clearing
one classification field cannot erase unrelated description, sector, or geography.

Inspector children use z-indexes relative to their parent. Currency-change,
provider-comparison, identifier, image, and other confirmation surfaces therefore stack
above an inspector opened from the wizard instead of appearing underneath it.

## Duplicate Recheck and Bulk Handoff

The duplicate verdict returned by `/parse` describes raw plugin output. It is not final
after asset grouping or row correction. Before the review can advance or import:

1. Candidate data is refreshed.
2. Corrected rows are grouped by broker.
3. Resolved fake IDs are substituted for the duplicate request; unresolved
   asset-required rows are omitted, while valid cash-only rows remain eligible.
4. `POST /api/v1/brokers/import/duplicates` recomputes database matches.
5. Cross-file and pending-editor duplicates are rebuilt from the current rows.

If the final recheck changes the selected set, the wizard stays on review and warns the
user. If it creates an actionable cross-file duplicate group, the wizard returns to that
resolver. Handoff occurs only after a completed recheck, with at least one eligible row
selected and no selected row carrying an unresolved required asset.

`buildFinalTxList()` includes only selected rows that pass the broker-opening gate,
replaces resolved placeholders with real asset ids, and preserves `ImportTodo`s.
`onImportBatch()` converts those items to bulk-editor `PendingOp`s, restores
`link_uuid` pairing, appends them to the existing draft workspace, and triggers
validation. The later **Save All** action builds and commits the standard bulk
transaction payload; the wizard never commits directly.

## Downstream Bulk Workspace Invariants (Group E7/E8)

- Every draft keeps a stable `tempId`. API operation indices are mapped back to those
  identities from the exact payload emitted for validation or commit.
- A balance issue is resolved against its full broker/date/currency-or-asset scope, so
  every affected workspace row is highlighted. Navigation chooses the first affected row
  in the current filtered and sorted display; hidden matches do not cause filters to be
  rewritten.
- The table displays transaction groups chronologically. Paired legs stay together and
  are ordered by the group's earliest date, latest date, then stable identity.
- Sorting changes only `visibleOps`. It does not reorder `ops`, mutate pairing, alter
  selection, change payload array order, or redefine backend checker rules.

## History

| Date | Change |
|------|--------|
| 2026-06-08 | v5 introduced a wide multi-file, multi-broker wizard and four numbered product stages. |
| 2026-06-25 | Identifier handling and modal-layer problems were recorded for follow-up. |
| 2026-09-09 | Group E reconciliation: full asset edit loading, omission/null-safe classification PATCH, parent-relative nested modals, explicit first-asset resolution, refreshed final duplicate checks, guarded bulk handoff, and stable E7/E8 bulk diagnostics/display ordering. |

## Source files

| Role | Path |
|------|------|
| Wizard orchestration | `frontend/src/lib/components/transactions/modals/ImportWizardModal.svelte` |
| Parse-to-merge and placeholder remapping | `frontend/src/lib/utils/transactions/importMerge.ts` |
| Wizard transaction and resolution types | `frontend/src/lib/utils/transactions/importTypes.ts` |
| Final duplicate request shaping | `frontend/src/lib/utils/transactions/duplicateRecheckPayload.ts` |
| Full asset edit loader | `frontend/src/lib/components/assets/assetEditData.ts` |
| Classification PATCH diff | `frontend/src/lib/components/assets/assetPayload.ts` |
| Asset create/edit and nested modal orchestration | `frontend/src/lib/components/assets/AssetModal.svelte` |
| Backend classification PATCH semantics | `backend/app/services/asset_source.py` |
| BRIM routes and final duplicate endpoint | `backend/app/api/v1/brokers.py` |
| BRIM DTOs and positive fake-ID range | `backend/app/schemas/brim.py` |
| Local candidate matching | `backend/app/services/brim_provider.py` |
| Generic CSV parser | `backend/app/services/brim_providers/broker_generic_csv.py` |
| Bulk handoff, stable drafts, and display sorting | `frontend/src/lib/components/transactions/modals/TransactionBulkModal.svelte` |
| Bulk issue mapping and chronological comparator | `frontend/src/lib/utils/transactions/bulkDisplay.ts` |
| Sorted visible-row navigation | `frontend/src/lib/components/table/DataTable.svelte` |
| Import wizard developer guide | `mkdocs_src/docs/developer/frontend/components/features/import-wizard.md` |
| Generic CSV developer guide | `mkdocs_src/docs/developer/backend/brim/generic_csv.md` |

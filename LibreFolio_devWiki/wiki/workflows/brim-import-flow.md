---
title: "BRIM broker import flow"
category: workflow
tags: [brim, brokers, import, transactions, assets, frontend]
related:
  - decisions/brim-fake-asset-id
  - decisions/brim-broker-scoped
  - decisions/brim-parser-only
  - entities/import-wizard-modal
  - features/F-012
  - features/F-049
  - features/F-083
mkdocs: "developer/frontend/components/features/import-wizard.md"
---

# Workflow: BRIM Broker Import Flow

## Overview

BRIM converts broker report files into reviewed transaction drafts. Files are scoped to
brokers when uploaded; parsers return preview data only; asset resolution and duplicate
review happen before the selected drafts enter the standard bulk transaction editor.

## Steps

### 1. Upload and assign files

`ImportWizardModal` accepts multiple files in one session and assigns one broker to each
file. Upload is multipart:

```text
POST /api/v1/brokers/import/upload
file=<required>
broker_id=<required>
custom_filename=<optional>
```

The filesystem sidecar records the uploader and target broker. Current uploads are not DB
records and are not broker-path URLs.

### 2. Select stored files and plugins

`GET /api/v1/brokers/import/files?broker_ids=...` returns reports for accessible brokers.
The user chooses files across broker panels and may override the compatible plugin per
file. A Generic CSV file has one broker, although the same wizard can include other files
for other brokers and each file may contain multiple currencies.

### 3. Parse previews

`POST /api/v1/brokers/import/files/{file_id}/parse` receives
`{ plugin_code, broker_id }`. The plugin reads the source and returns transactions,
warnings/notices, validation issues, field todos, and extracted asset hints. Core code then
searches local candidates and performs an initial database duplicate check.

Parsing is preview-only. Generic CSV preserves row values and currencies subject to
transaction validation and does not synthesize FX conversions.

### 4. Unify, correct, and resolve assets

Each parser uses positive high placeholder asset IDs. The frontend first remaps
per-file placeholders, then optionally unifies identities across files. It may
automatically bind exactly one current local candidate found through primary or alternate
identifiers; multiple candidates remain manual. Missing assets are explicitly linked or
created by the user.

### 5. Recheck duplicates on final drafts

After identity grouping and corrections, the wizard refreshes candidates and calls
`POST /api/v1/brokers/import/duplicates` per broker with the current rows. It does not
silently reuse a stale parse-time verdict. If the recheck changes selection or reveals a
cross-file group requiring arbitration, the user remains in the review flow.

### 6. Hand off and commit

The wizard substitutes resolved real asset IDs and sends selected, eligible drafts plus
their `ImportTodo`s to `TransactionBulkModal`. The bulk editor assigns stable draft IDs,
restores paired legs by `link_uuid`, validates the whole workspace, and later commits
through the standard transaction bulk API. BRIM has no commit endpoint.

## Involved APIs

| Step | Method | Endpoint |
|------|--------|----------|
| Upload | POST multipart | `/api/v1/brokers/import/upload` |
| List files | GET | `/api/v1/brokers/import/files?broker_ids=...` |
| Parse preview | POST JSON | `/api/v1/brokers/import/files/{file_id}/parse` |
| Refresh candidates | POST JSON | `/api/v1/brokers/import/asset-candidates` |
| Final duplicate recheck | POST JSON | `/api/v1/brokers/import/duplicates` |
| Validate bulk draft | POST JSON | `/api/v1/transactions/validate` |
| Commit bulk draft | POST JSON | `/api/v1/transactions/commit` |

## Source files

| Role | Path |
|------|------|
| BRIM routes and access checks | `backend/app/api/v1/brokers.py` |
| File storage and parse cache | `backend/app/services/brim_provider.py` |
| BRIM schemas | `backend/app/schemas/brim.py` |
| Import wizard | `frontend/src/lib/components/transactions/modals/ImportWizardModal.svelte` |
| Bulk editor | `frontend/src/lib/components/transactions/modals/TransactionBulkModal.svelte` |
| Import wizard developer guide | `mkdocs_src/docs/developer/frontend/components/features/import-wizard.md` |
| Generic CSV developer guide | `mkdocs_src/docs/developer/backend/brim/generic_csv.md` |

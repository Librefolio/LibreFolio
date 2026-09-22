---
title: "BRIM Files Scoped to Broker (Multi-User Support)"
category: decision
status: resolved
date: 2026-01-22
tags: [brim, brokers, multiuser, access-control, upload, generic-csv]
related:
  - features/F-010
  - features/F-011
  - features/F-012
  - features/F-083
  - entities/import-wizard-modal
  - workflows/brim-import-flow
mkdocs: "developer/frontend/components/features/import-wizard.md"
---

# Decision: BRIM Files Must Be Broker-Scoped

## Context

BRIM report files originally acquired their broker only when they were parsed. That left
uploaded files without a durable ownership scope, made the file list difficult to filter
safely, and postponed the broker permission check until too late in the flow.

The important invariant is therefore **one stored file → one target broker**. This is a
data and authorization rule, not a requirement that the broker id appear in the URL path.

## Options Considered

1. **Assign the broker only at parse time** — rejected because it permits orphan uploads and
   gives the stored file no stable access-control scope.
2. **Use a global file pool with an optional broker label** — rejected because a label is not
   an authorization boundary.
3. **Require a broker when uploading each file** — chosen. It supports a multi-file,
   multi-broker wizard while preserving one unambiguous broker per stored report.

## Decision

The current upload contract is:

```text
POST /api/v1/brokers/import/upload
Content-Type: multipart/form-data

file=<required upload>
broker_id=<required positive broker id>
custom_filename=<optional display filename>
```

The endpoint is a shared BRIM collection route. `broker_id` is a required multipart form
field; the route is **not** `/brokers/{broker_id}/import/upload`. A successful upload stores
both `uploaded_by_user_id` and `target_broker_id` in the file metadata and places the file
under the broker-specific report directory.

The rest of the current contract is:

- `GET /api/v1/brokers/import/files` accepts repeated `broker_ids` query parameters and
  returns only brokers accessible to a non-superuser.
- `POST /api/v1/brokers/import/files/{file_id}/parse` receives JSON
  `{ plugin_code, broker_id }`. The wizard supplies the file's stored broker assignment.
- Upload, parse, and delete require `EDITOR` or `OWNER`; read, preview, and download require
  access to the file's target broker.
- Legacy metadata without `target_broker_id` is still discoverable for backward
  compatibility, but new uploads always carry a broker.

## Generic CSV Boundary

The wizard may upload and process multiple files assigned to multiple brokers in one
session. A **single flat Generic CSV file still belongs to exactly one broker** because
`broker_id` is assigned per uploaded file and passed per parse request.

This does not impose one file per currency: one broker file may contain several row
currencies. The Generic CSV parser preserves the row transaction values and currency
subject to the normal schema/sign validation; it does not synthesize FX conversions or
invent balancing rows.

## Consequences

- The file itself has a stable broker scope before parsing starts.
- File discovery and access checks can use `target_broker_id`.
- A multi-broker session is represented as several independently scoped files, not as a
  multi-broker flat file.
- Parsing remains preview-only. After review and asset resolution, the wizard hands drafts
  to the standard transaction bulk editor; BRIM has no separate commit endpoint.

## History

| Date | Change |
|------|--------|
| 2026-01-22 | Broker association moved from parse-only state into upload metadata. |
| 2026-09-09 | Reconciled the documented route and multipart contract with the integrated code; clarified multi-file/multi-broker Generic CSV boundaries. |

## Related

- [[entities/import-wizard-modal]] — frontend orchestration of per-file broker assignment.
- [[workflows/brim-import-flow]] — end-to-end import flow.
- [[decisions/brim-parser-only]] — parsing and transaction commit remain separate.

## Source files

| Role | Path |
|------|------|
| Upload, list, access, parse, and duplicate endpoints | `backend/app/api/v1/brokers.py` |
| File metadata and broker-specific storage | `backend/app/services/brim_provider.py` |
| Upload/parse DTOs and fake-ID contract | `backend/app/schemas/brim.py` |
| Multi-file broker assignment UI | `frontend/src/lib/components/transactions/modals/ImportWizardModal.svelte` |
| Generic CSV parser | `backend/app/services/brim_providers/broker_generic_csv.py` |
| Import wizard developer guide | `mkdocs_src/docs/developer/frontend/components/features/import-wizard.md` |
| Generic CSV developer guide | `mkdocs_src/docs/developer/backend/brim/generic_csv.md` |

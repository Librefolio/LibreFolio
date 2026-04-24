---
title: "BRIM broker import flow"
category: workflow
tags: [brim, brokers, import, transactions, assets, frontend]
related: [entities/db-models, decisions/brim-fake-asset-id, decisions/brim-broker-scoped]
---

# Workflow: BRIM Broker Import Flow

## Overview
End-to-end steps for importing broker transaction reports into LibreFolio — from file upload through plugin detection, parsing, asset matching, and final commit.

## Steps

### 1. Upload the file
**API**: `POST /api/v1/files/upload?broker_id={id}`
File stored at: `backend/data/prod/broker_reports/{broker_id}/`
The file record is created in the DB. The file is NOT yet parsed.
**Frontend entry point**: Broker detail page → "Import" button → `BrokerImportFilesModal.svelte`

### 2. Auto-detect the plugin
Each BRIM plugin implements `detect(file_path) → confidence_score`.
The system tries all registered plugins and picks the highest-confidence match.
If detection is ambiguous, the user can manually select from the plugin list.

### 3. Parse the file
**API**: `POST /api/v1/files/{id}/parse`
The selected BRIM plugin's `parse_file()` returns:
- `transactions` — list of transaction records with **fake asset IDs** (negative integers)
- `warnings` — non-fatal issues (unknown asset types, missing prices, etc.)
- `extracted_assets` — asset hints found in file (ISIN, ticker, name) for the matching UI
Result is cached in the file's metadata JSON (keyed by `plugin_version` for cache invalidation).

### 4. Staging review
Frontend displays the parsed transactions and warnings.
Fake asset IDs are shown as unresolved placeholders — the user sees "Unknown Asset #-3" etc.

### 5. Asset matching
`AssetMatchingWizard.svelte` (3-step wizard) maps each fake asset ID to a real DB asset:
- **Step 1**: Search existing DB assets by name/ISIN/ticker
- **Step 2**: Search providers online (`AssetSearchAutocomplete.svelte`) — creates asset if not in DB
- **Step 3**: Create asset manually

After matching, fake IDs are replaced with real DB asset IDs in the transaction list.

### 6. Commit transactions
**API**: `POST /api/v1/transactions/bulk`
**Payload**: resolved transaction list with real asset IDs
On success: transactions written to `Transaction` table, file marked as imported.

## Key Design: Fake Asset ID Flow
BRIM plugins never look up assets in the DB during parsing. They emit **negative integers** as temporary asset identifiers. This two-phase approach:
- Allows parsing without requiring pre-existing assets
- Lets the user match or create assets interactively
- Keeps plugins stateless and testable in isolation

See [[decisions/brim-fake-asset-id]].

## Involved APIs
| Step | Method | Endpoint |
|------|--------|----------|
| Upload | POST | `/api/v1/files/upload?broker_id={id}` |
| List files | GET | `/api/v1/files?broker_id={id}` |
| Parse | POST | `/api/v1/files/{id}/parse` |
| Bulk commit | POST | `/api/v1/transactions/bulk` |

## Source files

| Role | Path |
|------|------|
| BRIM abstract base | `backend/app/services/brim_provider.py` |
| BRIM plugins | `backend/app/services/brim_providers/` |
| Files API | `backend/app/api/v1/files.py` |
| Transactions API | `backend/app/api/v1/transactions.py` |
| Import modal | `frontend/src/lib/components/brokers/BrokerImportFilesModal.svelte` |
| Asset matching wizard | `frontend/src/lib/components/brokers/AssetMatchingWizard.svelte` |
| AssetSearchAutocomplete | `frontend/src/lib/components/assets/AssetSearchAutocomplete.svelte` |

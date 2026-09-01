---
title: "Phase 7 Part 4 Round 5 — Server-Driven Type Rules + Dual-Transaction Form"
category: source
source_type: plan
date_ingested: 2026-05-28
original_path: LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round4-5/plan-phase07-transaction-Part4_Round5_ServerDrivenTypeRules.prompt.md
tags: [phase07, transactions, frontend, backend, type-rules, auto-sign, dual-form, transactionTypeStore, dark-mode, pair-form-layout, unified-bulk]
related: [sources/phase07-part4-round4-unified-pipeline, features/F-046, features/F-047, features/F-048, decisions/server-driven-type-rules, decisions/dual-transaction-form-design]
merged_from: [sources/phase07-part4-round5]
merged_on: 2026-09-01
---

> **Merged 2026-09-01.** `sources/phase07-part4-round5` was a near-duplicate of this
> page — same `original_path`, three days apart in `date_ingested`, same content in
> different words. It was one of the wiki's only two orphans. This page survives
> because it is the one the index and other pages link to; the rows below marked
> *(from the merged copy)* are the material the duplicate carried and this one did not.

# Source: Phase 7 Part 4 Round 5 — Server-Driven Type Rules + Dual-Transaction Form

## Summary
Replaced 3 hardcoded frontend files (`transactionTypeRules.ts`, `transactionTypes.ts`, `eventTypes.ts`) with a single `transactionTypeStore` driven by `GET /transactions/types`. Introduced auto-sign negation (user enters positive, frontend auto-negates for SELL qty / BUY cash). Backend now sends `icon_slug`, `doc_slug`, `cash_mode`, `quantity_mode`, `quantity_sign`, `cash_sign`, `pair_form_layout` — frontend uses data as-is with zero mapping. Also implements dual-transaction form for paired types (FX, Transfer Asset, Transfer Cash) and dark mode color vibrancy fixes.

## Key Takeaways
- **`transactionTypeStore`**: Single source of truth — lazy fetch + cache from `GET /transactions/types`. Replaces 3 deleted files
- **Auto-sign negation**: When `quantity_sign==="-"` or `cash_sign==="-"`, user enters positive → `collectCreate()` auto-negates. Visual hint: label suffix "(−)"
- **`pair_form_layout`**: Backend metadata field (`"fx"`, `"transfer_asset"`, `"transfer_cash"`, `null`) drives dual-form layout in FormModal
- **`TXTypesResponse`**: Wraps `List[TXTypeMetadata]` + `List[EventTypeMetadata]` (emoji, compatible_tx_types)
- **`FieldMode`**: Replaces multiple boolean fields — `"required"|"optional"|"forbidden"` for asset, cash, quantity
- **Dark mode fix**: `ColorSet.vivid = hsl(hue, 100%, 50%)` + `color-mix` at 12–15% for visible broker row tints
- **R6-B dual form**: FX (split currencies, shared broker), Transfer Asset (split brokers, shared asset), Transfer Cash (split brokers, shared amount) — all in one FormModal
- **Unified BulkModal vision (R6-B.4)**: merge create-many/edit-many modes, add `delete` row state, TransactionPickerModal for adding existing TX, promote/split within bulk. `TransactionPickerModal` reuses the main `TransactionsTable` with a `pickerMode` flag *(detail from the merged copy)*
- **Balance error row attribution (W28)** *(from the merged copy)*: when the backend reports `index=-1` on a balance error, the frontend scans the drafts to find the matching row by `brokerId + assetId/currency`. A server that cannot say *which* row failed is answered by a client-side reconstruction — recorded because it is a contract weakness, not a feature
- **`getIndexColor` dark-mode boost** *(from the merged copy)*: alongside `--broker-vivid` replacing the pastel `--broker-bg` for row tints, `getIndexColor` had its saturation raised in dark mode

## Wiki Pages Updated
- [[decisions/server-driven-type-rules]] — new decision page
- [[decisions/dual-transaction-form-design]] — updated
- [[features/F-048]] — Round 5 + R6-B tracked, unified BulkModal design
- [[features/F-046]] — `TXTypesResponse` + endpoint updates *(link carried over from the merged copy)*
- [[features/F-047]] — dual form mode documented *(link carried over from the merged copy)*

## Source files

| Role | Path |
|------|------|
| Server-driven type store | `frontend/src/lib/stores/transactions/transactionTypeStore.ts` |
| Dual-transaction form | `frontend/src/lib/components/transactions/modals/TransactionFormModal.svelte` |
| Unified bulk modal | `frontend/src/lib/components/transactions/modals/TransactionBulkModal.svelte` |
| Transaction picker | `frontend/src/lib/components/transactions/modals/TransactionPickerModal.svelte` |
| Types endpoint | `backend/app/api/v1/transactions.py` — `GET /transactions/types` |
| Type metadata schemas | `backend/app/schemas/transactions.py` — `TXTypeMetadata`, `EventTypeMetadata`, `TXTypesResponse` |
| Original plan | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round4-5/plan-phase07-transaction-Part4_Round5_ServerDrivenTypeRules.prompt.md` |


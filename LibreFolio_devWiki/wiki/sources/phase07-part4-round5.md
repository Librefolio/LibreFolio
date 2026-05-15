---
title: "Phase 07 Part 4 Round 5 — Server-Driven Type Rules + Dual-Transaction Form"
category: source
source_type: plan
date_ingested: 2026-05-25
original_path: LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round4-5/plan-phase07-transaction-Part4_Round5_ServerDrivenTypeRules.prompt.md
tags: [phase07, transactions, backend, frontend, type-rules, auto-sign, dual-form, transactionTypeStore, pair-form-layout, unified-bulk]
related: [sources/phase07-part4-round4-pipeline, decisions/server-driven-type-rules, decisions/dual-transaction-form-design, features/F-046, features/F-047, features/F-048]
---

# Source: Phase 07 Part 4 Round 5 — Server-Driven Type Rules + Dual-Transaction Form

## Summary

Final round of Part 4: replaces 3 hardcoded frontend files (`transactionTypeRules.ts`, `transactionTypes.ts`, `eventTypes.ts`) with a single `transactionTypeStore` driven by `GET /transactions/types`. Backend now sends `TXTypesResponse` containing `TXTypeMetadata` (with `icon_slug`, `doc_slug`, `FieldMode`, `SignRule`, `PairFormLayout`) and `EventTypeMetadata` (with emoji and compatible_tx_types). Auto-sign negation lets users enter positive numbers when the type requires negative (SELL qty, BUY cash). Round 6 (R6-B) introduces dual-transaction form layout for FX/Transfer pairs — single modal produces 2 linked payloads.

## Key Takeaways

- **Server-driven type rules**: `transactionTypeStore.ts` replaces 3 hardcoded files. Frontend derives all field visibility, sign behavior, and event compatibility from backend metadata. Zero mapping functions — backend values are lowercase pass-through
- **Backend `TXTypeMetadata` evolution**: added `icon_slug` (PNG path convention), `doc_slug` (mkdocs path), `cash_mode`/`quantity_mode` (`FieldMode`: required/optional/forbidden), `quantity_sign`/`cash_sign` (`SignRule`: positive/negative/zero/nonzero/free), `pair_form_layout` (`PairFormLayout`: fx/transfer_asset/transfer_cash/null)
- **`EventTypeMetadata`**: new schema with `code`, `name`, `emoji`, `compatible_tx_types`. Wraps event types alongside tx types in `TXTypesResponse`
- **Auto-sign negation** (W29a): user enters positive numbers → frontend auto-negates in `collectCreate()`/`collectUpdate()` when `SignRule === "negative"`. Visual hint "(−)" on label. On edit: `Math.abs()` for display
- **Dual-transaction form** (R6-B): `pair_form_layout` metadata drives 3 form layouts in `TransactionFormModal`: (1) FX — shared broker, split currencies; (2) Transfer Asset — split brokers, shared asset/qty; (3) Transfer Cash — split brokers, shared currency/amount
- **Unified BulkModal design** (R6-B.4): merges create-many and edit-many into single modal with mixed row states (`new`/`edit`/`delete`). TransactionPickerModal reuses main `TransactionsTable` with `pickerMode`. Promote/Split actions within bulk modal
- **Dark mode vibrancy fix** (R6-A): `--broker-vivid: hsl(hue, 100%, 50%)` replaces pastel `--broker-bg` for row tints. `getIndexColor` dark mode boosted saturation
- **Balance error row attribution** (W28): frontend-side scan of drafts to find matching row by `brokerId + assetId/currency` when backend reports `index=-1`

## Wiki Pages Updated

- [[features/F-046]] — `TXTypesResponse` + endpoint updates
- [[features/F-047]] — dual form mode documented
- [[features/F-048]] — unified BulkModal design
- [[decisions/server-driven-type-rules]] — new decision
- [[decisions/dual-transaction-form-design]] — updated with R6-B details


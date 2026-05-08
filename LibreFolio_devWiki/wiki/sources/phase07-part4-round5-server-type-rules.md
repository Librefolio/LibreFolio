---
title: "Phase 7 Part 4 Round 5 — Server-Driven Type Rules + Dual-Transaction Form"
category: source
source_type: plan
date_ingested: 2026-05-28
original_path: LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part4_Round5_ServerDrivenTypeRules.prompt.md
tags: [phase07, transactions, frontend, backend, type-rules, auto-sign, dual-form, transactionTypeStore, dark-mode]
related: [sources/phase07-part4-round4-unified-pipeline, features/F-048, decisions/server-driven-type-rules, decisions/dual-transaction-form-design]
---

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
- **Unified BulkModal vision (R6-B.4)**: merge create-many/edit-many modes, add `delete` row state, TransactionPickerModal for adding existing TX, promote/split within bulk

## Wiki Pages Updated
- [[decisions/server-driven-type-rules]] — new decision page
- [[decisions/dual-transaction-form-design]] — updated
- [[features/F-048]] — Round 5 + R6-B tracked


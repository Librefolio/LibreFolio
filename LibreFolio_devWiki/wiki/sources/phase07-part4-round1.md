---
title: "Phase 07 Part 4 Round 1 — Table refactor + 14 sub-round bugfixes"
category: source
source_type: plan
date_ingested: 2026-04-28
original_path: LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part4_Round1-tableRefactorBugfix.prompt.md
tags: [phase07, transactions, frontend, bugfix, datatable, filters, currency-stack, multi-enum, event-tooltip]
related:
  - features/F-047
  - problems/svelte5-effect-read-write-loop
  - problems/babel-currency-symbol-locale
  - problems/datatable-filter-options-disappear
  - decisions/transactions-client-side-filtering
  - concepts/entity-store-pattern
---

# Source: Phase 07 Part 4 Round 1 — Table Refactor + Bugfixes

## Summary

Massive post-walkthrough bugfix round for the `/transactions` page. Identified 82+ issues (W1–W82+) across 14 sub-rounds (1.2–1.14). Rebuilt the transactions table on the full `DataTable + DataTableToolbar + DataTablePagination` pattern, fixed an infinite loop in `TransactionStagingModal`, added the `currency-stack` and `multi-enum` filter variants to `DataTable`, unified currency formatting via `currencyFormat.ts`, and established 100% client-side filtering. The round also introduced `eventTypes.ts`, `brokerHelpers.ts`, and fixed a Babel locale-dependent currency symbol bug in the backend.

## Key Takeaways

- **W1 (C1)**: `$effect` in TransactionStagingModal wrote AND read `drafts` in the same run → infinite `effect_update_depth_exceeded`. Fix: compute `next: DraftRow[]` locally **before** assigning to `drafts`. Classic Svelte 5 rune trap. See [[problems/svelte5-effect-read-write-loop]].
- **W28 decision**: All column-header filters are **client-side only** on the already-fetched dataset. `GET /transactions` loads ALL TX (no filter params); explicit Refresh button triggers reload. See [[decisions/transactions-client-side-filtering]].
- **W73 (C18)**: `getEnumOptionsWithCounts()` was calling `.filter(o => o.count > 0)` which caused a filter option to disappear once deselected. Fix: removed the filter. See [[problems/datatable-filter-options-disappear]].
- **W77 (C22)**: Babel `get_currency_symbol('USD', locale='it')` returns `'USD'` not `'$'`. Fix: use `locale='en'` for symbol lookup only; names stay localized. See [[problems/babel-currency-symbol-locale]].
- **New filter variants**: `multi-enum` (checkbox list with search, for tags) and `currency-stack` (per-currency range sliders) added to `DataTable`/`DataTableColumnFilter`.
- **Pulse rewrite (C34)**: `box-shadow` on `<tr>` unreliable across browsers. Switched to DOM-direct manipulation with `classList.add/remove` + `offsetWidth` reflow trick. Capture-phase delegation added for `🔗`/`●evt` click events.
- **`highlight_id` removed (C34)**: URL parameter `highlight_id` and `FilterMap.highlight_id` removed; DOM-direct pulse is purely visual and doesn't pollute the URL.
- **`formatCurrencyAmountHtml()` shared helper**: created in `currencyFormat.ts`, reused by both AssetTable (lastPrice) and TransactionsTable (cash cell), eliminating ~15 lines of duplicate logic.
- **Context-aware linked-pair tooltip (C39)**: tooltip is type-specific (TRANSFER→`📥/📤 broker`, FX_CONVERSION→`💱 amount→amount`, DEPOSIT/WITHDRAWAL→`🏦 giroconto`, generic→`🏦 Cash transfer`).

## Important Deviations from Round 1 Original Plan

| Original scope | What happened |
|----------------|---------------|
| 7 sub-round fixes (W1–W16) | Expanded to 82+ issues across 14 sub-rounds (1.2–1.14) |
| Modal restyle in Round 2 | Still deferred; modals have minor issues captured as separate round |
| `POST /assets/events/query` bulk | Used existing `GET /assets/events?ids=...` endpoint instead (no new endpoint needed) |
| Server-side `limit/offset` kept | Removed entirely in C2 — all TX loaded, DataTable handles pagination |

## Wiki Pages Updated

- [[features/F-047]] — source files expanded, status confirmed `implemented`
- [[problems/svelte5-effect-read-write-loop]] — created from W1/C1
- [[problems/babel-currency-symbol-locale]] — created from W77/C22
- [[problems/datatable-filter-options-disappear]] — created from W73/C18
- [[decisions/transactions-client-side-filtering]] — created from W28 decision
- [[concepts/entity-store-pattern]] — first mentioned here, implemented in Round 2

## Source files

| Role | Path |
|------|------|
| Transactions table | `frontend/src/lib/components/transactions/TransactionsTable.svelte` |
| Transactions page | `frontend/src/routes/(app)/transactions/+page.svelte` |
| DataTable | `frontend/src/lib/components/table/DataTable.svelte` |
| DataTable filter | `frontend/src/lib/components/table/DataTableColumnFilter.svelte` |
| Currency format helper | `frontend/src/lib/utils/currencyFormat.ts` |
| Event type emoji helper | `frontend/src/lib/utils/eventTypes.ts` |
| Broker icon helper | `frontend/src/lib/utils/brokerHelpers.ts` |
| Backend currency util | `backend/app/utils/currency_utils.py` |
| Mock data | `backend/test_scripts/test_db/populate_mock_data.py` |

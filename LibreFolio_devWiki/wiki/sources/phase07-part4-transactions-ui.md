---
title: "Phase 07 Part 4 — /transactions page + manual staging + promote"
category: source
source_type: plan
date_ingested: 2026-04-28
original_path: LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part4.prompt.md
tags: [phase07, transactions, frontend, datatable, staging, promote, transfer, assetStore]
related:
  - features/F-047
  - features/F-048
  - decisions/multi-broker-atomic-tx
  - decisions/tx-link-uuid-semantics
  - concepts/always-pair-adjacent
  - concepts/opportunistic-cache-merge
---

# Source: Phase 07 Part 4 — /transactions page + Manual Staging + Promote

## Summary

Plan for building the `/transactions` frontend page as a DataTable read-view with URL-driven header filters. Introduces the first **manual-only** version of `TransactionStagingModal` (modes: `create-many`, `edit-many`), `BulkDeleteLinkedPairModal`, and `TransferPromoteModal` (DEPOSIT+WITHDRAWAL → TRANSFER/FX_CONVERSION). Also introduces `transactionTypes.ts`, `txTypeStore`, the enriched `assetStore` with opportunistic merge/invalidate, `AssetSelect.svelte`, `brokerColors.ts`, and the always-pair-adjacent rendering algorithm. Completed through 10 steps with walkthroughs deferred to Round 1 and Round 2.

## Key Takeaways

- **Always-pair-adjacent rendering**: TRANSFER/FX_CONVERSION partners are always rendered adjacent (giver above, receiver below) via `displayRows[]` algorithm; see [[concepts/always-pair-adjacent]].
- **Two-stage fetch**: main rows → missing partner IDs → secondary fetch for ghost rows.
- **`assetStore` opportunistic merge**: any code with fresh asset data calls `assetStore.merge()` — universal ingress; see [[concepts/opportunistic-cache-merge]].
- **`POST /transactions/validate` always single-list**: FE calls with exactly ONE of `creates`, `updates`, `deletes` populated, never mixed; decision documented inline.
- **BRIM mode deferred**: `TransactionStagingModal` in Part 4 is manual-only (`create-many`/`edit-many`); BRIM mode (`create-brim`) comes in Part 5.
- **Ghost row chip (✕/+)**: the interactive chip from Step 5 spec was intentionally NOT implemented in Part 4 (deferred to Round 2); ghost rows show only opacity reduction.
- **Event tooltip**: popover-on-click for `●evt` explicitly closed — rich hover tooltip suffices.
- **`promote_transfer` scope strict**: only 1 DEPOSIT + 1 WITHDRAWAL with `related_transaction_id=null`; smart pair-finder deferred.

## Original Plan vs Actual Implementation Deltas

| Original | Actual |
|----------|--------|
| `+page.ts` separate for load | `onMount` in `+page.svelte` — consistent with `/files` pattern |
| Ghost row with interactive ✕/+ chip | Opacity-only ghost; chip deferred to Round 2 |
| Popover-on-click for `●evt` | Closed: rich hover tooltip via Tooltip.svelte sufficient |
| `POST /assets/events/query` bulk | Replaced by `GET /assets/events?ids=...` (endpoint already existed) |
| Server-side filters in GET /transactions | Changed to 100% client-side in Round 1 (W28); explicit Refresh button added |
| `highlight_id` as URL parameter | Replaced in Round 1.12 with DOM-direct pulse (no URL param) |

## Wiki Pages Updated

- [[features/F-047]] — status updated to `implemented`, full component inventory
- [[features/F-048]] — status updated to `in-progress` (manual mode done)
- [[concepts/always-pair-adjacent]] — created from this plan
- [[concepts/opportunistic-cache-merge]] — created from this plan
- [[connections/transactions-connections]] — updated to reflect Part 4 completion

## Source files

| Role | Path |
|------|------|
| Transactions page | `frontend/src/routes/(app)/transactions/+page.svelte` |
| Transactions table | `frontend/src/lib/components/transactions/TransactionsTable.svelte` |
| Staging modal | `frontend/src/lib/components/transactions/TransactionStagingModal.svelte` |
| Promote modal | `frontend/src/lib/components/transactions/TransferPromoteModal.svelte` |
| Bulk delete modal | `frontend/src/lib/components/transactions/BulkDeleteLinkedPairModal.svelte` |
| Asset store | `frontend/src/lib/stores/assetStore.ts` |
| TX type utilities | `frontend/src/lib/utils/transactionTypes.ts` |
| Broker colors | `frontend/src/lib/utils/brokerColors.ts` |
| Asset select | `frontend/src/lib/components/ui/select/AssetSelect.svelte` |

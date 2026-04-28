---
title: "Phase 07 Part 4 Round 2 — Cache factory + DataTable polish + slider bugfixes"
category: source
source_type: plan
date_ingested: 2026-04-28
original_path: LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part4_Round2-tableRefactorBugfix.prompt.md
tags: [phase07, transactions, frontend, cache, entityStore, brokerStore, assetStore, slider, datatable, tooltip]
related:
  - features/F-047
  - concepts/entity-store-pattern
  - decisions/datatable-tooltip-custom-cell
  - features/F-048
---

# Source: Phase 07 Part 4 Round 2 — Cache Factory + DataTable Polish

## Summary

Final round of Phase 7 Part 4. Introduces `createEntityStore<T>()` factory pattern to eliminate cache staleness across `assetStore` and new `brokerStore`. Resolves 5 UX issues (R2-1…R2-5) plus 4 additional walkthrough rounds (2.5, 3, 3.5, 4). Key deliverables: `stores/entityStore.ts`, `stores/brokerStore.ts`, `assetStore` refactored as factory instance, invalidation wired at all mutation callsites, currency-stack filter with per-currency min/max, conditional pair-grouping (only when no filters/sort active), `DataTable.fullData` prop for stable filter boundaries, slider snap-on-release, `TxTypeIconCell.svelte` for mobile/desktop interaction.

## Key Takeaways

- **`createEntityStore<T>()`**: generic factory for bounded-list + id-lookup stores. Invariant: `invalidate()` **resets `loaded = false`**, so `ensureLoaded()` becomes a real no-op only when data is fresh. Previously `assetStore` never reset `loaded` → `ensureAssetsLoaded` was a no-op after mutation → stale icons.
- **`brokerStore` new**: migrated 3 callsites (`/transactions`, `/files`, `/brokers` pages) from local `let brokers = $state([])` to shared `brokerStore`.
- **Mutation callsite wiring**: `AssetModal.svelte`, `/assets/+page.svelte`, `/assets/[id]/+page.svelte`, `BrokerModal.svelte` now call `mergeAssets()`/`invalidateBroker()` on save/delete/wipe.
- **Tooltip decision (R2-2 → Step 2)**: all `title=""` HTML attributes removed from TX table cells. Only `<Tooltip.svelte>` via `CustomCell` snippets allowed. See [[decisions/datatable-tooltip-custom-cell]].
- **Conditional pair-grouping (Step 4)**: pairs are adjacent (grouped + pair-never-split paginator) only when both column filters and sort are inactive. With any filter/sort active → `isGrouped=false`, `DataTable` handles pagination internally, ghost rows become ordinary rows.
- **`DataTable.fullData` prop (Round 2.5 R2.5-4)**: `getColumnMinMax()` and `getCurrencyMinMaxByCode()` compute boundaries from `fullData ?? data`, preventing slider boundaries from shrinking as filters are applied.
- **Slider snap-on-release (Round 3.5)**: `oninput` snaps only value (no jitter); `onchange` (mouseup) snaps position via `finalizeNumSliders`/`finalizeSizeSliders`/`finalizeCurrencySlider`.
- **`TxTypeIconCell.svelte` (Round 4)**: replaces `<a href>` with `<span>` + event handlers. Desktop: **double-click** → `window.open(docUrl)`. Mobile: 500ms long-press → open. Single click/tap shows only the tooltip (no navigation). `Tooltip.svelte` handles hover/tap.

## Important Deviations from Round 2 Original Plan

| Original | Actual |
|----------|--------|
| Step 7 (E2E `entity-cache-refresh.spec.ts`) | Deferred — not yet implemented |
| Ghost row ✕/+ interactive chip | Still deferred (not in Round 2) |
| `fxStoreRegistry` migration to entityStore | Explicitly excluded (different: TimeSeriesStore with gap-detection) |

## Wiki Pages Updated

- [[concepts/entity-store-pattern]] — created
- [[decisions/datatable-tooltip-custom-cell]] — created
- [[features/F-047]] — conditional pair-grouping, fullData prop, TxTypeIconCell noted
- [[features/F-048]] — still `in-progress`; Step 7 E2E deferred

## Source files

| Role | Path |
|------|------|
| Entity store factory | `frontend/src/lib/stores/entityStore.ts` |
| Asset store (refactored) | `frontend/src/lib/stores/assetStore.ts` |
| Broker store (new) | `frontend/src/lib/stores/brokerStore.ts` |
| TX type icon cell | `frontend/src/lib/components/transactions/cells/TxTypeIconCell.svelte` |
| DataTable | `frontend/src/lib/components/table/DataTable.svelte` |
| DataTable filter | `frontend/src/lib/components/table/DataTableColumnFilter.svelte` |
| Asset modal | `frontend/src/lib/components/assets/AssetModal.svelte` |
| Broker modal | `frontend/src/lib/components/brokers/BrokerModal.svelte` |
| Assets page | `frontend/src/routes/(app)/assets/+page.svelte` |
| Brokers page | `frontend/src/routes/(app)/brokers/+page.svelte` |
| Files page | `frontend/src/routes/(app)/files/+page.svelte` |

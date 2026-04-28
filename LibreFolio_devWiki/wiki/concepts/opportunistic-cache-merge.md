---
title: "Opportunistic Cache Merge — assetStore.merge() as universal ingress"
category: concept
tags: [frontend, stores, cache, assets, merge, svelte5]
related:
  - concepts/entity-store-pattern
  - features/F-047
  - sources/phase07-part4-transactions-ui
---

# Concept: Opportunistic Cache Merge

## Definition

Any code that receives fresh entity data (assets, brokers) from the API **deposits it into the shared store via `merge()`**, regardless of whether the call was made for that entity specifically. This avoids network round-trips and keeps all pages in sync when one page already loaded the data.

## Where It Applies

```ts
// After loading assets for /assets page
const assets = await zodiosApi.list_assets_api_v1_assets_query_get();  // GET /assets/query
mergeAssets(assets);       // deposit into shared store for free

// After AssetModal.save (only has partial data)
mergeAssets([{ id: result.asset_id, icon_url: newIcon, display_name: newName }]);

// After AssetSearchAutocomplete selects a DB asset
mergeAssets([selectedAsset]);
```

## Relationship to `createEntityStore`

`merge()` is the "deposit" half of the entity store contract. It performs an **upsert** on the cached map: fields present in the incoming object overwrite cached values; missing fields are preserved. This allows partial updates (e.g. only `icon_url` changed) without re-fetching the full entity.

The counterpart operations:
- `ensureLoaded()` — "ensure I have data, fetching if needed"
- `invalidate(id)` — "this entry is stale, force re-fetch next access"
- `merge(items)` — "I have fresh data, add it to the cache proactively"

## Limitations

This pattern covers **same-client edits**. Cross-client updates (another browser tab, another user) are NOT propagated without WebSocket/SSE. This is a known limitation of LibreFolio's current architecture — documented and accepted for now.

## Source files

| Role | Path |
|------|------|
| Asset store | `frontend/src/lib/stores/assetStore.ts` |
| Entity factory | `frontend/src/lib/stores/entityStore.ts` |
| First use in TX page | `frontend/src/routes/(app)/transactions/+page.svelte` |

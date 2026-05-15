---
title: "Entity Store Pattern — createEntityStore<T>() factory"
category: concept
tags: [frontend, stores, cache, svelte5, factory, invalidation]
related:
  - concepts/timeseries-store-pattern
  - sources/phase07-part4-round2
  - features/F-047
---

# Concept: Entity Store Pattern

## Definition

A generic factory function `createEntityStore<T, Id>()` that creates a reactive client-side cache for a **bounded entity list** (assets, brokers, currencies) with id-based lookup. It replaces ad-hoc `let items = $state([])` patterns scattered across pages, centralizing cache management and ensuring all pages share the same data version.

## Core Invariant

> `invalidate(id)` MUST reset `loaded = false` when it removes entries.

This invariant ensures `ensureLoaded()` is a real no-op **only when data is genuinely fresh**. Before this factory was introduced, `assetStore` never reset `loaded` → `ensureAssetsLoaded()` was always a no-op after a mutation → icons/names stayed stale until hard refresh (F5).

## Factory API

```ts
createEntityStore<T, Id>({
    loader: () => Promise<T[]>,
    getId: (item: T) => Id,
    normalize: (raw: Record<string, unknown>) => T,   // required
    requiredFields?: (keyof T)[],   // skip merge if missing
}): {
    ensureLoaded(...args): Promise<void>,
    refreshAll(): Promise<void>,
    get(id: Id): T | null,
    getAll(): T[],
    merge(items: ReadonlyArray<Partial<T>>): void,
    invalidate(idOrIds: Id | ReadonlyArray<Id>): void,
    version: Readable<number>,
    isLoaded(): boolean,
}
```

## Where It Applies

- **`assetStore.ts`** — refactored as factory instance in Phase 7 Part 4 Round 2. Preserves public API (`ensureAssetsLoaded`, `getAssetInfo`, `mergeAssets`, `invalidateAfterMutation`, `refreshAllAssets`, `assetStoreVersion`).
- **`brokerStore.ts`** — new instance created in Round 2. Exposes `ensureBrokersLoaded`, `getBrokerInfo`, `getAllBrokers`, `mergeBrokers`, `invalidateBroker`, `brokerStoreVersion`.
- **Future**: any entity with a bounded list + lookup-by-id pattern (currencies, tx types, etc.) can use this factory.

## Mutation Callsite Contract

Every callsite that mutates an entity MUST:
1. On create/update success → call `merge([{id, ...updatedFields}])` (upserts cache optimistically).
2. On delete success → call `invalidate(id)` (removes from cache; resets `loaded`).
3. On wipe → call `invalidate(id)` + optionally `refreshAll()` if broad fields changed.

Callsites wired in Round 2:
- `AssetModal.svelte` (save create, save edit, currency-change wipe)
- `/assets/+page.svelte` (delete, wipe)
- `/assets/[id]/+page.svelte` (delete, wipe)
- `BrokerModal.svelte` (save, delete)

## Relationship to TimeSeriesStore

`createEntityStore` handles **bounded lists** (all assets, all brokers — stable set fetched once). `TimeSeriesStore` handles **unbounded time series** with gap detection and delta fetching. They are complementary, not interchangeable.

## Examples

```ts
// assetStore.ts — factory instance
export const assetStore = createEntityStore<AssetInfo, number>({
    loader: () => zodiosApi.list_assets_api_v1_assets_query_get(),   // GET /assets/query
    getId: (a) => a.id,
    normalize: flattenZodArtifacts,
});

// Mutation callsite
mergeAssets([{ id: result.asset_id, icon_url: newUrl }]);   // after AssetModal.saveEdit()
invalidateAfterMutation(assetId);                            // after /assets delete
```

## Source files

| Role | Path |
|------|------|
| Factory implementation | `frontend/src/lib/stores/entityStore.ts` |
| Asset store (instance) | `frontend/src/lib/stores/assetStore.ts` |
| Broker store (instance) | `frontend/src/lib/stores/brokerStore.ts` |
| Round 2 plan (designed here) | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round1-3/plan-phase07-transaction-Part4_Round2-tableRefactorBugfix.prompt.md` |

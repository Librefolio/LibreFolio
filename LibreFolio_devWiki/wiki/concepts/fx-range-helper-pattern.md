---
title: "FX Range Helper Pattern (ensureFxRangeLoaded)"
category: concept
tags: [frontend, fx, stores, dry, refactor, cache]
related: [features/F-072, concepts/timeseries-store-pattern, features/F-023]
---

# Concept: FX Range Helper Pattern

## Definition

`ensureFxRangeLoaded(slug, start, end)` is the centralized function in `fxStoreRegistry.ts` that encapsulates the recurring gap-detection → bulk-fetch → merge pattern for loading FX rate data into the `TimeSeriesStore` cache.

## Where It Applies

Previously duplicated inline in 4 pages (6 occurrences):
- `fx/+page.svelte` (1x)
- `fx/[pair]/+page.svelte` (1x)
- `assets/+page.svelte` (1x)
- `assets/[id]/+page.svelte` (3x)

All replaced by a single `await ensureFxRangeLoaded(slug, start, end)` call.

## Algorithm

```typescript
export async function ensureFxRangeLoaded(slug, start, end): Promise<FxDataPoint[]> {
    const store = getFxStore(slug);
    const gaps = store.getMissingIntervals(start, end);
    if (gaps.length > 0) {
        // Build bulk convert requests for each gap
        const response = await zodiosApi.convert_currency_bulk_...(requests);
        store.merge(results.map(apiResultToFxDataPoint));
    }
    return store.getRange(start, end);
}
```

## Important Notes

- The `slug` must be in canonical alphabetical order — always use `createPairSlug(base, quote)` before calling.
- Network failures silently return cached data (no error propagation to caller).
- The function returns the full range from cache after loading, enabling immediate use.

## Source files

| Role | Path |
|------|------|
| Helper function | `frontend/src/lib/stores/fxStoreRegistry.ts` |
| Source plan | `LibreFolio_developer_journal/RoadmapV4_UI/plan-independent-FxRangeHelper.prompt.md` |

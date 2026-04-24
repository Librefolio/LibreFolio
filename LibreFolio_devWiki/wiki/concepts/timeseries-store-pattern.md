---
title: "TimeSeriesStore pattern"
category: concept
tags: [frontend, stores, timeseries, cache, fx, assets]
related: [concepts/editbuffer-pattern, decisions/zodios-api-client]
---

# Concept: TimeSeriesStore Pattern

## Definition
`TimeSeriesStore<T>` is a generic client-side cache for time series data (prices, FX rates). It stores data points indexed by ISO date string and exposes gap detection — so components can fetch only missing date ranges rather than re-fetching the full history.

## Where It Applies
- `fxStoreRegistry.ts` — one `TimeSeriesStore<FxDataPoint>` per currency pair slug
- Asset price stores — price history for asset detail pages
- Any future time-series data displayed in charts

## Key Interface

```typescript
interface TimeSeriesPoint { date: string }  // ISO YYYY-MM-DD

class TimeSeriesStore<T extends TimeSeriesPoint> {
  merge(points: T[]): void              // idempotent upsert by date
  getRange(start, end): RangeResult<T>  // {data: T[], gaps: DateGap[]}
  invalidateRange(start, end): void     // remove points in range
  invalidateAll(): void                 // full clear
}
```

`RangeResult<T>` contains:
- `data`: all cached points in range (in order)
- `gaps`: contiguous intervals with no data → what needs to be fetched from backend

## Examples

### Gap-aware fetch pattern
```
1. chart asks for [2024-01-01 → 2024-12-31]
2. store.getRange() → {data: [...existing...], gaps: [{start:'2024-06-01', end:'2024-06-30'}]}
3. controller fetches ONLY the gap from backend
4. store.merge(newPoints) → gap filled
5. chart rerenders with complete data
```

### FX store registry helpers
```typescript
// fxStoreRegistry.ts
getFxStore(slug: string): TimeSeriesStore<FxDataPoint>
getFxStoreByPair(base: string, quote: string): TimeSeriesStore<FxDataPoint>
createPairSlug(base, quote): string   // alphabetically ordered, e.g. "EUR-USD"
removeFxStore(slug: string): void
invalidateAllFxStores(): void
```

Note: `createPairSlug` always sorts alphabetically so `EUR-USD` and `USD-EUR` resolve to the same store.

## Design Principles
- `merge()` is idempotent — safe to call repeatedly with overlapping data
- Storage is `Map<string, T>` keyed by ISO date — O(1) lookups
- Gap detection enables **delta fetching** — no wasteful full reloads
- Store instances are long-lived (app session) — chart components subscribe without owning the cache

## Source files

| Role | Path |
|------|------|
| TimeSeriesStore | `frontend/src/lib/stores/TimeSeriesStore.ts` |
| FX store registry | `frontend/src/lib/stores/fxStoreRegistry.ts` |

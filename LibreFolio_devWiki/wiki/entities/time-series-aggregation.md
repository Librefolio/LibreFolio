---
title: "timeSeriesAggregation.ts"
category: entity
type: module
tags: [frontend, charts, utility, bucketing, semantic-zoom]
related:
  - concepts/chart-resolution-semantic-zoom
  - sources/phase09-m3-broker-redesign-2026-07
---

# timeSeriesAggregation.ts

## Role

Shared frontend utility module providing the bucketing/aggregation primitives that every resolution-aware
chart builds on (see [[concepts/chart-resolution-semantic-zoom]]). It is the single foundation all 6
downstream chart-resolution implementation plans depend on — written first, deliberately, as the
prerequisite conceptual document before the consumer plans.

## Location

`frontend/src/lib/components/charts/timeSeriesAggregation.ts` (unit tests:
`frontend/src/lib/components/charts/__tests__/timeSeriesAggregation.test.ts`)

## Key Interfaces

- Bucketing functions that downsample a raw daily time series into weekly/monthly buckets given a visible
  date range.
- Aggregation rules per series type (e.g. last-value vs. average vs. sum, depending on what the series
  represents — price vs. cumulative P&L vs. allocation weight).
- Density/hysteresis thresholds that decide when to switch resolution band, with hysteresis to avoid
  flicker when the zoom boundary is crossed back and forth.
- Debounce wrapper so resolution recomputation doesn't fire on every intermediate `dataZoom` drag frame.

## Design Notes

- Consumed by `PriceChartFull`/`CandlestickChart`, `GrowthChart`, `AllocationHistoryChart`, the 9 signal
  overlay types, and `ResolutionBadge` (for displaying the active resolution).
- The **compact/static** chart variant (`PriceChartCompact`/`LineChart` on `/assets` and `/fx` cards)
  deliberately does NOT use the interactive parts of this module (no `dataZoom`-driven resolution switching) —
  it only recomputes on data/width change.

## History

| Date | Change |
|------|--------|
| 2026-07-08 to 2026-07-13 | Designed and implemented as the foundational module for the 7-plan chart-resolution workstream (Phase 9 Milestone 3, cross-cutting). See [[sources/phase09-m3-broker-redesign-2026-07]]. |

## Source files

| Role | Path |
|------|------|
| Module | `frontend/src/lib/components/charts/timeSeriesAggregation.ts` |
| Tests | `frontend/src/lib/components/charts/__tests__/timeSeriesAggregation.test.ts` |
| Foundational design doc | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_3/chart_resolution/impl_plan_chart_resolution_00_foundation.md` |

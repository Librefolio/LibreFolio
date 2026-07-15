---
title: "Chart Resolution / Semantic Zoom"
category: concept
tags: [frontend, charts, echarts, performance, semantic-zoom, bucketing]
related:
  - entities/time-series-aggregation
  - domains/dashboard
  - sources/phase09-m3-broker-redesign-2026-07
---

# Concept: Chart Resolution / Semantic Zoom

## Definition

Time-series charts (price history, portfolio growth, allocation history) render too many points once the
visible range spans months/years, hurting both readability and performance. **Semantic zoom** resolves this
by bucketing the underlying series into daily → weekly → monthly resolution bands depending on how much time
range is currently visible (via ECharts `dataZoom`), rather than always plotting every raw data point.

Resolution changes are density-driven with hysteresis (avoids flicker when the zoom boundary is crossed
repeatedly) and debounced (avoids recomputing buckets on every intermediate zoom-drag frame).

## Where It Applies

- **Foundational utility**: [[entities/time-series-aggregation]] (`timeSeriesAggregation.ts`) — shared
  bucketing, aggregation rules, density/hysteresis thresholds, debounce.
- **`PriceChartFull` / `CandlestickChart`** (`frontend/src/lib/components/charts/`) — shared line↔candle
  resolution, event markers, "measure" mode, bucket-aware tooltips.
- **`GrowthChart`** (`frontend/src/lib/components/dashboard/GrowthChart.svelte`) — 5 series in EUR-mode, 3
  series in %-mode.
- **`AllocationHistoryChart`** (`frontend/src/lib/components/dashboard/AllocationHistoryChart.svelte`) —
  dynamic stacked series per allocation category.
- **Signal overlays** (9 types, e.g. Bollinger = envelope, MACD = 3 series) — each has its own downsample
  dispatch rule.
- **`ResolutionBadge.svelte`** (`frontend/src/lib/components/charts/`) — shared pill showing the current
  resolution, plus new i18n keys under the `chart.*` namespace (en/it/fr/es).
- **Static/compact variant**: `PriceChartCompact.svelte` / `LineChart` compact branch, used in `AssetCard`/
  `FxCard` on `/assets` and `/fx`. Deliberately **no** `dataZoom`, hysteresis, or badge — recomputes only on
  data/width change, since these cards never zoom interactively.

## Why Not Always Plot Raw Points?

- **Readability**: thousands of daily points crammed into a multi-year view is visual noise; weekly/monthly
  aggregates communicate the trend better.
- **Performance**: ECharts re-render cost scales with point count; bucketing keeps series length bounded
  regardless of the underlying date range.

## Design Origin

Feasibility study + architectural refinement in `study_chart_dynamic_resolution.md` (rows 1-250 = feasibility,
256+ = refinement, including the daily→weekly→monthly semantic-zoom decision). Translated into 7
implementation plans (foundation + 6 consumers), written in parallel by a fleet of agents, one plan per
component/workstream. All 7 verified ✅ implemented against the actual sources.

## Source files

| Role | Path |
|------|------|
| Foundational utility | `frontend/src/lib/components/charts/timeSeriesAggregation.ts` |
| Utility tests | `frontend/src/lib/components/charts/__tests__/timeSeriesAggregation.test.ts` |
| Price chart (full) | `frontend/src/lib/components/charts/PriceChartFull.svelte` |
| Candlestick | `frontend/src/lib/components/charts/CandlestickChart.svelte` |
| Compact/static variant | `frontend/src/lib/components/charts/PriceChartCompact.svelte` |
| Resolution badge | `frontend/src/lib/components/charts/ResolutionBadge.svelte` |
| Growth chart | `frontend/src/lib/components/dashboard/GrowthChart.svelte` |
| Allocation history chart | `frontend/src/lib/components/dashboard/AllocationHistoryChart.svelte` |
| Feasibility study + refinement | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_3/chart_resolution/study_chart_dynamic_resolution.md` |
| 7 implementation plans | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_3/chart_resolution/impl_plan_chart_resolution_*.md` |

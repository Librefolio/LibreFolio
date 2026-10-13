---
title: "At weekly or monthly resolution, an event in the last, still open period vanished from the price chart: the marker looked for the period's theoretical end, the point sat on its last date (R-5, since v1.0.0)"
category: problem
status: resolved
date: 2026-10-13
tags: [frontend, charts, echarts, events, aggregation, resolution, product-defect, workstream-i, release-1.2]
related:
  - concepts/chart-resolution-semantic-zoom
  - concepts/echarts-chart-gotchas
  - features/F-033
---

# Problem: the open week lost its markers

## Symptom

On an asset's or an FX pair's price chart at weekly or monthly resolution, the marker of an event — a dividend, a
split — that falls in the **last period**, the week or month not over yet, did not appear. Earlier periods showed
theirs. Workstream T read it in the code during T-ISO (backlog T-EVW); V confirmed it at runtime; the coordinator
gave it to workstream I as R-5 of lot 51.

## Root Cause

Three pieces that do not talk to each other:

- `bucketEventMarkers` (`timeSeriesAggregation.ts`) files each event under the **theoretical end** of its period
  (`bucketEnd`: the Sunday, the last day of the month);
- `aggregateLineSeries` dates each aggregated point with **its last data point**, and keeps the theoretical end only in
  the point's metadata;
- `buildEventScatterGroups` (`priceChartHelpers.ts`) looked the theoretical end up among the points' dates, did not
  find it, and skipped the event (`continue`).

In a full period the two dates coincide: the asset page fills the weekends and the FX converter returns every
calendar day. In the last period, still open, the point sits on the last date with data and the event vanished. The
first partial period loses nothing, because its point sits on the theoretical end anyway. The defect dates from
`222a77c5e` (2026-07-12), so it was already in v1.0.0.

## Solution

`1acd1bf10` (2026-10-13, I's lot 51, train 91), in `buildEventScatterGroups` only, for resolutions other than daily:
a map from each period's theoretical end to the date of its point (`renderDateByBucketEnd`, built from the resolved
line), and the marker takes that date — falling back to the theoretical end — and with it the index, the y value and
the period's details. `bucketEventMarkers` and `PriceChartFull.svelte` do not change.

A product choice comes with it: an event of the open period dated **after** the last data point (a dividend announced
for Friday, seen on Wednesday) appears on that period's bar, as the first partial period already did.

Four unit tests (`priceChartHelpers.test.ts`, «R-5, lot 51»: the open week, the open month next to a full one, a
comparison event on its overlaid line, an event after the last data point) were red on the base, each with «the
marker … vanished», and are green with the cure.

## Prevention

- A lookup keyed on a computed date must use the same date the drawing used: here the period's theoretical end
  against the point's real date.
- A sibling stays: in the partial period the main tooltip's «value at» shows the theoretical end
  (`PriceChartFull.svelte`), signalled to T.

## Status

Resolved in the code. The 🐛 CHANGELOG line I proposed — «At weekly or monthly resolution, events in a last week or
month that is not over yet no longer disappear from the asset and FX charts…» — is not in the [1.2.0] chapter at
`fa6299689`; the backlog entry T-EVW, the same defect, is still open there.

## Source files

| Role | Path |
|------|------|
| The cure | `frontend/src/lib/components/charts/priceChartHelpers.ts` (`buildEventScatterGroups`) |
| Event filing and aggregation | `frontend/src/lib/components/charts/timeSeriesAggregation.ts` |
| Tests (T4) | `frontend/src/lib/components/charts/priceChartHelpers.test.ts` |
| The chart | `frontend/src/lib/components/charts/PriceChartFull.svelte` |
| I's lot 51 | `LibreFolio_developer_journal/Release_2/Phase_0/51_narrowFitFixes/plan-phase00NarrowFitFixes.prompt.md` |

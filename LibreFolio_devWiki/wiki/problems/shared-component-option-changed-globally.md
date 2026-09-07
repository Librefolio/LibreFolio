---
title: "A default changed in a shared component leaves its lane"
category: problem
status: resolved
date: 2026-08-31
tags: [frontend, charts, echarts, shared-components, blast-radius]
related_concepts: [absence-sentinel-vs-nullable-type]
related: [problems/env-var-injection-point-duplicated, sources/settings-lane-and-sixteen-defects]
---

# Problem: `connectNulls: false` set globally to fix FX would have changed every chart

## What nearly shipped

While making FX charts show a **gap** where a rate is missing, the change was
made where it was most convenient: `connectNulls: false` on the series built by
`LineChart` / `lineChartHelpers`.

Those files are **shared**. They draw asset prices, portfolio value, comparison
overlays — not just FX. And the previous values were not "unset everywhere":

| series | before |
|---|---|
| main series from `lineChartHelpers` | **not set** |
| overlays in `LineChart` | **`connectNulls: true`** |
| band middle in `lineChartHelpers` | `connectNulls: true` (pre-existing) |

So a single global `false` would have **inverted the overlay behaviour for the
whole application** to fix one feature.

## Why no test would have caught it

Unit tests do not render ECharts; charts are covered mainly by E2E, and an E2E
that screenshots a line does not fail because a gap appeared where there used to
be a join. The change would have been invisible until a user noticed a broken
line in an unrelated chart.

That is the general hazard: **a shared component's default has a blast radius
larger than the lane that changes it, and the smaller the diff, the less it looks
like it.**

## Fix

The gap is now **opt-in**:

- main series: back to unset
- overlays: `signal.connectNulls ?? true` — legacy preserved
- only `FxPairSignal` sets `connectNulls: false`

And `missing` has a safe default by construction: it is read as `!point.missing`
and `d.missing ? null : d.value`, so `undefined` yields exactly the old
behaviour.

## The barrier that keeps it fixed

A test in `lineChartHelpers.test.ts` — *"keeps legacy output unchanged when no
point is missing"* — pins the output for a series containing no `missing` points.
It is not a test about FX: it is the guard rail protecting every **other** chart
from the next change made here.

## The reusable question

Before changing a default in a shared component, ask three things, in order:

1. **What was it before** — per call site, not "in general"? (Here: unset for
   one, `true` for another.)
2. **Who else passes through this code?** (Here: `PriceChartCompact`,
   `ChartSettingsModal`, `RiskAnalysisPanel`, and through them `AssetCard`,
   `FxCard`, both detail routes.)
3. **Does a value that does not opt in behave exactly as before?**

If the answer to (3) is not a provable yes, the change belongs behind a flag the
caller sets.

## Source files

| Role | Path |
|------|------|
| Shared chart | `frontend/src/lib/components/charts/LineChart.svelte` |
| Series builders | `frontend/src/lib/components/charts/lineChartHelpers.ts` |
| The only opt-in | `frontend/src/lib/charts/signals/FxPairSignal.ts` |
| Legacy barrier test | `frontend/src/lib/components/charts/__tests__/lineChartHelpers.test.ts` |

## See also

- [[problems/env-var-injection-point-duplicated]] — the same blast-radius
  question from the other side: there, a shared setting failed to reach a second
  path and went silent.
- [[sources/settings-lane-and-sixteen-defects]] — the lane that produced it.

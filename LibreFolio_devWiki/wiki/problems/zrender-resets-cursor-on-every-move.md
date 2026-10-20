---
title: "zrender puts its own cursor back on every pointer move"
category: problem
status: resolved
date: 2026-10-19
tags: [frontend, echarts, zrender, charts, measure, cursor]
related: [decisions/no-range-of-a-single-day, features/F-045]
---

# Problem: zrender puts its own cursor back on every pointer move

## Symptom
On the asset and FX charts, measure mode gave the chart container the class `cursor-crosshair`
(`PriceChartFull.svelte`, `CandlestickChart.svelte`), yet the user never saw a crosshair. The developer, on
19/10: «io non sapevo manco fosse stato fatto, non l'ho mai visto!».

## Root Cause
ECharts draws through zrender, which owns the cursor of its own element, the element inside the container. On
every pointer move, `Handler.prototype.mousemove` (`zrender/lib/Handler.js`, version 6.0.0) does two things, in
this order:
1. it calls `proxy.setCursor(hoveredTarget ? hoveredTarget.cursor : 'default')`, an inline `cursor` style on
   zrender's element;
2. it dispatches `mousemove` to the listeners.

So zrender's inline `default` covers a class on the outer container from the first move. A cursor set
asynchronously, for example in a `requestAnimationFrame`, is reset again by the next move.

## Solution
Y-N65 (N65-7): in measure mode the chart sets its own cursor with `chartInstance.getZr().setCursorStyle(…)` inside
the zr `mousemove` listener, on every move. The call is synchronous, made **before** the rAF throttle that limits
the hover work:
- `'crosshair'` by default;
- `'not-allowed'` while the last resolved hover was refused (the measure's start, where `onMeasureHover` answers
  `true`).

Once the hover resolves in its frame, the chart applies the cursor of the new answer and publishes it on the
container as `data-measure-hover="blocked" | "free"`, a stable hook for tests. Outside measure mode the chart
never calls `setCursorStyle`, so zrender keeps its own behaviour (for example `pointer` over a clickable symbol).

## Prevention
- Never style the cursor of an ECharts chart with CSS on its container: zrender overrides it. Use
  `zr.setCursorStyle` in a zr `mousemove` listener, every time, synchronously.
- A test of the cursor needs a zr stand-in that keeps the handlers and records `setCursorStyle`: the recorder in
  `PriceChartFull.test.ts` (Y-N65) does this, with the animation frames held through `vi.stubGlobal`.

## Impact
The measure-mode crosshair had been invisible since it was written; the not-allowed cue over the start point
could not exist without this fix. Found during the Y-N65 analysis by reading zrender, before writing any code.

## Source files
| Role | Path |
|------|------|
| Line view cursor | `frontend/src/lib/components/charts/PriceChartFull.svelte` |
| Candles cursor | `frontend/src/lib/components/charts/CandlestickChart.svelte` |
| The answer that refuses a day | `frontend/src/lib/components/charts/MeasurePanel.svelte` (`updatePendingEnd`) |
| Tests (zr stand-in, held frames) | `frontend/src/lib/components/charts/PriceChartFull.test.ts` |

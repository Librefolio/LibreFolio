---
title: "ECharts gotchas met by the Dashboard charts"
category: concept
tags: [frontend, charts, echarts, privacy, i18n, axis, legend, gotcha]
related: [problems/pnl-lines-kept-removed-brokers, problems/line-chart-axes-lost-the-day, problems/echarts-canvas-mismeasures-emoji-labels, concepts/chart-resolution-semantic-zoom, entities/time-series-aggregation, decisions/portfolio-pnl-series-contracts, decisions/privacy-mask-at-the-formatter, sources/phase00-performance-charts-2026-09, decisions/html-escape-at-the-source]
---

# Concept: ECharts behaviours that look like bugs in our code

## Definition

A list of Apache ECharts behaviours that the performance-charts work (Release 2, workstream I, rounds 1–4,
September–October 2026) mistook for defects of its own, with the rule each one now follows. Read it before touching
`GrowthChart.svelte` or `PerformanceChart.svelte`.

| Behaviour | What it looked like | Rule now |
|---|---|---|
| `splitLine.interval: 'auto'` follows the **label** interval | duplicated month labels and separators that thin out with the labels (R8) | separators are planned independently of labels; drawn only when a bucket slot is ≥ `CANDLE_MIN_SLOT_PX` (8 px); labels fall back to thinned closing dates (Round 4, D4/D4-bis) |
| On a **time** axis, bar width follows the **minimum gap** between x values | hairline Income bars whenever a short partial bucket sat next to a full one (R10) | Income uses a **category** axis, one slot per bucket (D3); fixed px widths and virtual x positions were rejected |
| Axis/tooltip **formatters are not reactive** and ECharts caches axis labels | the privacy toggle did not redraw money axes; amounts leaked on the axis (R5–R7, P4-11) | the privacy state is part of the chart's rebuild key; on a masked money axis even 0 is masked (D12) |
| The **edge tick** prints the raw computed bound | an axis ending in "−888" | show round ticks only, `showMinLabel: false` (D25) |
| **Legend selection is kept by series name**, across option updates | hiding "Broker A" in one view hid it in every view | accepted (D27): a legend entry with the same name toggles in all views |
| Tooltip HTML is **HTML** — translations are interpolated raw | a `<` or `&` in a translation would break a tooltip (latent) | the catalogues themselves are checked: every value must render as itself (`translationMarkup` / `catalogMarkupFindings` in `htmlInterpolation.gate.test.ts`); escaping ~109 call sites was rejected; function formatters are outside both XSS gates (residual K-15, [[decisions/html-escape-at-the-source]]) |
| The canvas under-measures emoji | axis names overflow | [[problems/echarts-canvas-mismeasures-emoji-labels]] |
| A tooltip **does not scroll** and is not bounded by the chart | on a 360–390 px phone the price tooltip (362–386 px) pushed the value off-screen (K step 16) | cap it at `getWidth() − 32` (`fitTooltipToWidth`) and build rows with `buildFittedTooltipRow` — the label shrinks with an ellipsis, the value never does (`echartsTooltipHelpers.ts`; both helpers are on the XSS gate's HTML-first-argument list) |
| A **partial update** (`notMerge: false`) merges series **by position** and never touches the legend's `data` | the P&L lines kept brokers removed from the filter, a new broker was not drawn, a swapped one sat under the old legend entry ([[problems/pnl-lines-kept-removed-brokers]]) | when the names of the series change (`seriesKey`), take the full rebuild (`e72b0b56e`) |
| Default **axis labels** never receive the app's language | English months on time axes, ISO dates on category axes; compact axes printed the month on every tick ([[problems/line-chart-axes-lost-the-day]]) | every axis gets the policy's formatter, in the app's language, which reads ECharts 6's `{level}` (`4c05c1d85`, `8682f0bbd`) |
| A **stacked** series with a null base stacks on the axis origin; `connectNulls` skips only the top points | a band fell to zero on every weekend ([[problems/echarts-stacked-band-null-base]]) | bridge the base and delta series between sessions, and keep them out of the tooltip (`840bdbc0d`) |
| A compact axis's **last label is centred on its tick**, so on a phone it hangs half outside the chart. `alignMaxLabel: 'right'` pulls it in, and on a **category** axis, where every label has the same priority, `fixMinMaxLabelShow` then hides the inner neighbour. On a **time** axis ECharts 6 sorts the labels by tick level (`z2 = 10 + level`) before `hideOverlap`, and `fixMinMaxLabelShow` hides only the immediate neighbour: the month or year tick next to the edge wins, and the pulled-in edge label is the one hidden | «Oct 1…» cut at 360–390 px; simulated on the Growth chart's time axis, the alignment hid the last label in 181 cases instead of 60, and in 26 of the 48 where it had been whole | `alignMaxLabel: 'right'` in the compact policy of **category** axes only (`5d8e863bf`, I's lot 51); the time axes with `containLabel` got their own cure in I's lot 52 — the next rows |
| `containLabel` reserves only the **height** of the x labels, never the half of the last, centred label that overhangs the right edge; and a **time** axis spans exactly the first and last data day, never rounded, so with zoom any day can sit on the edge | the Growth chart's last label cut on phones in the final gallery of 2026-10-13 | keep `containLabel` and widen the right inset to the larger of today's inset and half the widest candidate label plus 2 px, the slack `hideOverlap` already allows: `timeAxisGridRight` (`responsiveXAxis.ts`, `44d1b8f6f`, I's lot 52), in the Growth, allocation history and lot comparison charts — option «a3», the coordinator's choice |
| `outerBounds` (`outerBoundsMode: 'same'` with `outerBoundsContain: 'axisLabel'`, the replacement for the legacy `containLabel`) estimates the labels' room **once, before** `hideOverlap` decides which ticks survive | measured on the three time charts: 42 new cut labels, 103 first labels lost on phones, «Oct 13» cut to «Oct 1» at 360 and 390 px | rejected (option «(a)», stopped by I before any product change); a3 instead |
| A `setOption` **merge** keeps every key the patch omits, and a **category** axis's label `interval` counts categories on the whole axis: `dataZoom` never revisits it | after a zoom into a long period, the step computed for the whole axis (33 for a year of days in an 800 px chart, 90 or more on a phone) left two or three labels on the window (47-1): on phones first, but on desktop too, since the compact policy also applies below 24 px per point. A patch without `interval` would also keep that step after a zoom-out or a resize | the label policy is rebuilt on the visible count once the gesture settles (`visiblePointCountFromZoom`, read from the event, never from `getOption()`), and the patch names every key it replaces: `categoryAxisLabelPatch()` always sets `interval: 'auto'` and, off compact, restores the defaults of the compact-only keys — `LineChart`, `CandlestickChart` and `PriceChartFull` (Y's lot Y8, 2026-10-15) |
| On a **time** axis, `dataZoom`'s start and end are percentages **of time** between the first and last point, not of the points' index | the Growth chart read and built its zoom window as a bucket index (Z2), which a fix for the running period turned red | the Growth chart converts through day offsets (`cascadeDayOffsetsOf`, with a 0.1-day edge snap, `e1f2753ee`); the lot comparison chart still reads its zoom by index on a time axis, since v1.0.0 (open) |
| `getOption()` **deep-clones the whole option**, and a `setOption({series})` **merges every series again** (each `SeriesModel.mergeOption` rebuilds its data, ECharts 6.0.0); a `markPoint`'s items are an array, so a patch can only rewrite them whole, colour included | the overlay signals' arrow markers were re-aimed on every `dataZoom` tick (`updateArrowRotations()`): a clone and a write-back of every series up to ~60 times a second, under `PriceChartFull`'s own note never to read `getOption()` there (Y-8) | a zoom handler reads no `getOption()` and writes no series: the arrows are re-aimed once the gesture settles, in the debounce that re-spaces the labels (`LineChart`, `CandlestickChart` 120 ms; `PriceChartFull`'s 200 ms kept-resolution branch). The option is read afresh each time, never cached: the write-back carries every colour, so a cache kept across a theme or Designer Lab rebuild would paint the old colours back. A full render (`setOption(option, true)` resets the zoom) restores the saved zoom first and re-aims after: the restore's `dataZoom` event (a non-silent `dispatchAction` emits one) now only schedules the settle (Y-8b, `LineChart`, as `CandlestickChart` already did). A resize re-aims at the same settle, never on each `ResizeObserver` callback; the write-back happens only when an arrow turns by more than 0.01°; and a chart whose last full option drew no arrow (`noteArrowMarkers`, right after each full render) skips `getOption()` altogether (Y-25) (Y's Y-8, 2026-10-17; pinned by a light → dark → zoom unit test, a zoomed-redraw unit test and the Y-25 resize and no-arrow cases) |

Two non-ECharts rules from the same rounds:

- **Minus sign and signs**: chart formatters use the browser locale's minus sign; the Growth chart's currency
  formatter shows a sign except on zero (`signDisplay: 'exceptZero'`, D23/D23b).
- **Colour contrast is measured**: the dividend gold (`#b08d00` light / `#facc15` dark) replaced Tailwind's
  `#ca8a04`, whose 2.94:1 contrast fails WCAG 1.4.11's 3:1 for graphics.

## Where it applies

The Dashboard's Growth and Performance charts, the lots comparison chart, and any new ECharts surface that renders
money (privacy) or user-visible translations (tooltip HTML).

## Source files

| Role | Path |
|------|------|
| Growth chart (category Income axis, privacy rebuild key, `showMinLabel`) | `frontend/src/lib/features/dashboard/GrowthChart.svelte` |
| Performance chart | `frontend/src/lib/features/dashboard/PerformanceChart.svelte` |
| Separator/label planner (`CANDLE_MIN_SLOT_PX`) | `frontend/src/lib/features/dashboard/growthLadderAxis.ts` |
| Tooltip/catalogue HTML gate | `frontend/src/htmlInterpolation.gate.test.ts` |
| Lots chart colours | `frontend/src/lib/features/brokers/lots/lotComparisonChartHelpers.ts` |
| Compact and wide axis policies (`alignMaxLabel`), the zoom patch (`categoryAxisLabelPatch`) | `frontend/src/lib/components/charts/responsiveXAxis.ts` |
| The arrow markers' re-aim, once per settled zoom (Y-8) | `frontend/src/lib/components/charts/lineChartHelpers.ts` |
| The zoom handlers and their settle timers (Y-8) | `frontend/src/lib/components/charts/LineChart.svelte`, `frontend/src/lib/components/charts/CandlestickChart.svelte`, `frontend/src/lib/components/charts/PriceChartFull.svelte` |
| The Y-8 unit tests (per tick, settle, colour guard) | `frontend/src/lib/components/charts/LineChart.test.ts`, `frontend/src/lib/components/charts/PriceChartFull.test.ts` |
| Lot Y8, the category axes under zoom (47-1) | `LibreFolio_developer_journal/Release_2/Phase_1/09_dashboardCharts/plan-phase01DashboardCharts.prompt.md` |
| Lot 51, the simulation of the label rules | `LibreFolio_developer_journal/Release_2/Phase_0/51_narrowFitFixes/plan-phase00NarrowFitFixes.prompt.md` |
| Lot 52, the time axes' inset and the zoom (Z2) | `LibreFolio_developer_journal/Release_2/Phase_0/52_timeAxisLastLabel/plan-phase00TimeAxisLastLabel.prompt.md` |
| Round 4 decisions D1–D28 | `LibreFolio_developer_journal/Release_2/phases/20_performanceCharts/plan-phase00PerformanceChartsRound4-PostMergeReview.prompt.md` |
| Income colours and axis labels | `LibreFolio_developer_journal/Release_2/phases/20_performanceCharts/plan-phase00PerformanceChartsIncomeColorsAxisLabels.prompt.md` |
| Tooltip i18n escape | `LibreFolio_developer_journal/Release_2/phases/20_performanceCharts/plan-phase00PerformanceChartsBugfix-TooltipI18nEscape.prompt.md` |

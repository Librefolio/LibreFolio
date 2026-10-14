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
| On a **time** axis, `dataZoom`'s start and end are percentages **of time** between the first and last point, not of the points' index | the Growth chart read and built its zoom window as a bucket index (Z2), which a fix for the running period turned red | the Growth chart converts through day offsets (`cascadeDayOffsetsOf`, with a 0.1-day edge snap, `e1f2753ee`); the lot comparison chart still reads its zoom by index on a time axis, since v1.0.0 (open) |

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
| Growth chart (category Income axis, privacy rebuild key, `showMinLabel`) | `frontend/src/lib/components/dashboard/GrowthChart.svelte` |
| Performance chart | `frontend/src/lib/components/dashboard/PerformanceChart.svelte` |
| Separator/label planner (`CANDLE_MIN_SLOT_PX`) | `frontend/src/lib/components/dashboard/growthLadderAxis.ts` |
| Tooltip/catalogue HTML gate | `frontend/src/htmlInterpolation.gate.test.ts` |
| Lots chart colours | `frontend/src/lib/components/brokers/lots/lotComparisonChartHelpers.ts` |
| Compact and wide axis policies (`alignMaxLabel`) | `frontend/src/lib/components/charts/responsiveXAxis.ts` |
| Lot 51, the simulation of the label rules | `LibreFolio_developer_journal/Release_2/Phase_0/51_narrowFitFixes/plan-phase00NarrowFitFixes.prompt.md` |
| Lot 52, the time axes' inset and the zoom (Z2) | `LibreFolio_developer_journal/Release_2/Phase_0/52_timeAxisLastLabel/plan-phase00TimeAxisLastLabel.prompt.md` |
| Round 4 decisions D1–D28 | `LibreFolio_developer_journal/Release_2/phases/20_performanceCharts/plan-phase00PerformanceChartsRound4-PostMergeReview.prompt.md` |
| Income colours and axis labels | `LibreFolio_developer_journal/Release_2/phases/20_performanceCharts/plan-phase00PerformanceChartsIncomeColorsAxisLabels.prompt.md` |
| Tooltip i18n escape | `LibreFolio_developer_journal/Release_2/phases/20_performanceCharts/plan-phase00PerformanceChartsBugfix-TooltipI18nEscape.prompt.md` |

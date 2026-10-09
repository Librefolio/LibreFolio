---
title: "ECharts gotchas met by the Dashboard charts"
category: concept
tags: [frontend, charts, echarts, privacy, i18n, axis, legend, gotcha]
related: [problems/echarts-canvas-mismeasures-emoji-labels, concepts/chart-resolution-semantic-zoom, entities/time-series-aggregation, decisions/portfolio-pnl-series-contracts, decisions/privacy-mask-at-the-formatter, sources/phase00-performance-charts-2026-09, decisions/html-escape-at-the-source]
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
| Round 4 decisions D1–D28 | `LibreFolio_developer_journal/Release_2/phases/20_performanceCharts/plan-phase00PerformanceChartsRound4-PostMergeReview.prompt.md` |
| Income colours and axis labels | `LibreFolio_developer_journal/Release_2/phases/20_performanceCharts/plan-phase00PerformanceChartsIncomeColorsAxisLabels.prompt.md` |
| Tooltip i18n escape | `LibreFolio_developer_journal/Release_2/phases/20_performanceCharts/plan-phase00PerformanceChartsBugfix-TooltipI18nEscape.prompt.md` |

---
title: "ECharts measures emoji wrongly, so axis names overflow or get cut"
category: problem
status: resolved
date: 2026-09-24
tags: [frontend, charts, echarts, emoji, heatmap, layout]
related: [flag-emoji-windows, asset-global-page-shows-no-money]
---

# Problem: ECharts measures emoji wrongly, so axis names overflow or get cut

## Symptom
In the Asset Global correlation matrix the asset names on the axes were hidden or truncated, and the chart did not
follow the width of its card. The developer's F-3 review (24/09) listed it as V5. Names carrying an emoji — asset
names in LibreFolio often do — were the worst: their label ran past the space the chart had kept for it.

## Root Cause
Two independent causes, both inside ECharts 6:
1. **The canvas mis-measures emoji.** ECharts sizes an axis label with the canvas text metrics, and those under-report
   an emoji's width, so the margin reserved for the labels is too small for any name containing one.
2. **`grid.outerBoundsMode` defaults to `'auto'`.** The grid shrinks on its own to fit what it believes the labels
   need. Combined with (1), the plot area and the reserved margins disagreed with what was actually drawn.

## Solution
- Axis labels use `plainName` (`correlationHelpers.ts`), which strips emoji-as-emoji while keeping ®, © and ™. The name
  with its emoji is still shown in the tooltip and in the ranking, which are HTML.
- Margins are computed from the measured text of the emoji-free labels, with a minimum and maximum cell size; the
  matrix scrolls horizontally instead of spilling out of its card.
- `outerBoundsMode: 'none'`, so the grid keeps the margins it was given.
- The name ordering sorts on `plainName` too, so an emoji does not decide the position (V6).

## Prevention
- Never feed an emoji to a canvas-rendered ECharts label whose size matters: strip it, or render the label as HTML.
- When a label margin looks wrong, check `outerBoundsMode` before tuning numbers.
- `plainName` has unit tests (`correlationHelpers.test.ts`); keep ®/©/™ cases there, as test-author found a first
  version that removed them.

## Impact
One review round of the redesign (F-3b V5-A). No data impact.

## Source files
| Role | Path |
|------|------|
| Matrix | `frontend/src/lib/components/risk/CorrelationHeatmap.svelte` |
| `plainName`, `nameOrder`, `heatmapLayout` | `frontend/src/lib/components/risk/correlationHelpers.ts` |
| Tests | `frontend/src/lib/components/risk/correlationHelpers.test.ts` |
| Journal | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/implementation_2/progress/F-laboratorio-postmerge.md` |

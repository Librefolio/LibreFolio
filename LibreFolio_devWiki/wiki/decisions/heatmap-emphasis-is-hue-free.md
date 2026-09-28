---
title: "The chosen cell of a diverging heatmap is marked without a hue"
category: decision
status: resolved
date: 2026-09-24
tags: [frontend, charts, echarts, heatmap, colour, accessibility]
related: [echarts-canvas-mismeasures-emoji-labels, asset-global-page-shows-no-money]
---

# Decision: The chosen cell of a diverging heatmap is marked without a hue

## Context
The correlation matrix colours its cells on a diverging scale, red (−1) → neutral → blue (+1). Hovering a cell, or
picking a pair in the ranking beside the matrix, must make that cell easy to find: the developer said the tooltip's
cell was otherwise hard to locate.

## Options Considered
1. **Amber border and glow** — tried first. It vanished on the red cells.
2. **Green border and glow (`#22c55e`)** — "the complement of red, far from blue". The developer: it read as blue.
3. **A neutral border** — black on the light theme and white on the dark one, with a halo of the opposite shade.
4. **Dimming the other cells** — no new colour, but it also dims the matrix on every plain hover.

## Decision
Option 3. On a two-hue scale any third hue sits close to one end or the other; only a luminance contrast stands out on
the pale cells and on the saturated ones alike. The developer confirmed it on both themes (25/09 review: "finally the
selected cell shows in dark and in light").

ECharts lifts an emphasised cell above its neighbours (`Z2_EMPHASIS_LIFT`), so the neighbours' tile gaps cannot cover
its border.

## Consequences
- `emphasis.itemStyle` depends on the theme: `#0f172a` border with a white halo on light, white border with a
  near-black halo on dark.
- Any future emphasis on a diverging scale (other heatmaps, the risk levels) should reuse this rather than pick a hue.

## Source files
| Role | Path |
|------|------|
| Emphasis style | `frontend/src/lib/components/risk/CorrelationHeatmap.svelte` |
| Ranking that picks a cell | `frontend/src/lib/components/risk/CorrelationPairsList.svelte` |

## Links
- [[problems/echarts-canvas-mismeasures-emoji-labels]]
- Source: `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/implementation_2/progress/F-laboratorio-postmerge.md` (V5-G, V5-H, 24/09 15:27)

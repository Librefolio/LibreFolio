---
title: "One colour per asset across the Dashboard: one rank function, dashes for the same asset at several brokers, icons in the asset pie"
category: decision
status: resolved
date: 2026-11-06
tags: [frontend, dashboard, charts, colour, allocation, positions, release-1.3]
related:
  - decisions/colour-factorisation-at-pixel-parity
  - concepts/echarts-chart-gotchas
---

# Decision: one colour rank per asset

## Context

In the 1.3 test list the developer asked whether an asset had the same colour in the positions chart and in the
allocation pie. It did not. The pie ranked assets by weight (the heaviest takes the first colour); the lines of the
positions chart took their colour from the order in which positions were ticked. The two agreed only when ticked from
the heaviest down, and the comment in `positionsSeries.ts` that said they read the same rank was false for the lines.

## Options considered

For the same asset held at two brokers (one pie slice, two lines):
1. **A** — same colour, the second line dashed (the coordinator's advice).
2. **B** — same colour, both solid: simpler, but the lines blur together.

The developer chose A, «an edge case».

## Decision

- **One place computes the ranks:** `rankAssetsByWeight` (through `assetColorRanks`) in `positionsSeries.ts`. Assets
  held today first, the heaviest first (ties: lower id); then assets that left the portfolio, the most recently closed
  first; then extra ids no list knows (lines of a position sold out in the period), after every ranked asset so the
  pie's ranks do not move. The pie, the allocation history and the positions lines (and the table ticks) all read it:
  an asset wears one colour whatever is ticked and in whatever order. Liquidity has no rank.
- **Same asset at several brokers:** same colour, line patterns in broker order — solid, dashed, dotted, dash-dot
  (`lineDashes`).
- **Icons in the asset pie** (F-10): each slice carries the asset's icon, falling back to the asset type's icon when it
  has none or the image fails to load (also from an external site); liquidity keeps its own. `AllocationItem` gained the
  icon and type (`api sync`). The tooltip shows the icon too (`c82054bf1`).
- **No legend** on the pie in asset mode: icons and the tooltip name are enough; the other modes keep theirs.
- Long names in the positions chart tooltip (the ECharts infobox) are truncated and scroll, as in the badges (F-1).

## Consequences

- The report cache had to notice icon and name edits, otherwise the pie showed stale icons for up to 30 minutes: see
  the «Seen again» section of [[problems/portfolio-cache-ignored-role-and-share]].

## Links

- Sources: `DECISIONI-ondata8-20261106.md` (colour answer, question 2, F-10, question 4), `kickoff-w8.md` (lot B8) —
  coordinator files kept outside the repository. Summary: [[sources/wave8-9-release-1.3-closing-2026-11]]

## Source files

| Role | Path |
|------|------|
| Rank function, dashes | `frontend/src/lib/features/dashboard/positionsSeries.ts` |
| Positions chart | `frontend/src/lib/features/dashboard/PositionsPanel.svelte` |
| Allocation pie | `frontend/src/lib/features/dashboard/AllocationPanel.svelte` |
| Allocation item with icon and type | `backend/app/schemas/portfolio.py` |
| User docs | `mkdocs_src/docs/user/dashboard/charts.en.md`, `mkdocs_src/docs/user/dashboard/positions.en.md` |

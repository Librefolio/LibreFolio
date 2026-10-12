---
title: "A band chart's lower edge dropped to the axis on every weekend: ECharts stacks on the origin when the base is null"
category: problem
status: resolved
date: 2026-09-30
tags: [frontend, charts, echarts, stacked, band, gaps, weekends, risk]
related:
  - concepts/echarts-chart-gotchas
  - features/F-111
  - sources/phase00-risk-integration-2026-09
---

# Problem: the band that fell to zero between sessions

## Symptom

A band drawn as two stacked series (an invisible base plus a delta) fell to the axis origin on every non-trading day.

## Root Cause

When the base of a stacked series is null, ECharts uses the axis origin as the floor (`getStackedOnPoint`).
`connectNulls` only skips the points on top, so it makes it worse: «`connectNulls` non ripara la banda, la rompe»
(review R5 of folder 02). No ECharts option avoids it.

## Solution

`840bdbc0d` («fix(charts): bridge band fill between sessions»): the line-chart helpers fill the gaps between sessions
only in the invisible base and delta series, with a straight line between the neighbours; the tooltips skip those two
series, so a bridged value is never shown.

## Prevention

In a stacked band, never leave the base null — bridge it, and keep the bridged points out of the tooltip.

## Source files

| Role | Path |
|------|------|
| Session-gap bridging | `frontend/src/lib/components/charts/lineChartHelpers.ts` |
| Test | `frontend/src/lib/components/charts/lineChartHelpers.sessionGaps.test.ts` |

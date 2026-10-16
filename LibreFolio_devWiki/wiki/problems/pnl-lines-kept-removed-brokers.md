---
title: "The P&L lines kept the brokers that had left: a partial ECharts update merged series by position and never touched the legend"
category: problem
status: resolved
date: 2026-10-12
tags: [frontend, charts, echarts, growth-chart, pnl, legend, series, merge, workstream-i, release-1.2]
related:
  - features/F-055
  - concepts/echarts-chart-gotchas
  - problems/line-chart-axes-lost-the-day
  - decisions/portfolio-pnl-series-contracts
  - sources/phase00-chart-axis-day-labels-2026-10
---

# Problem: stale broker lines in the P&L chart

## Symptom

In the Growth chart's P&L in lines, with one line per broker (new in 1.2, `8ed7a0f0d`, 2026-09-18), changing the set
of brokers left the chart wrong: brokers removed from the filter stayed drawn and in the legend, a broker added was not
drawn, a swapped one took the place of the old one under the old one's legend entry. The coordinator's item 1, joined
to plan 47.

## Root Cause

`GrowthChart.svelte` chose its full rebuild only when the mode, the theme or the masking changed (`needsFullInit`). A
new set of brokers therefore went through the partial update, whose options are
`CHART_SERIES_UPDATE_OPTS = {notMerge: false, replaceMerge: ['dataZoom']}`: ECharts merges series **by position**, and
the legend's `data` exists only in the full build. Replayed on the same ECharts:

| Case | Brokers | Before | With the full build |
|------|---------|--------|---------------------|
| R1 | A, B, C → A | B and C stay, in the series and in the legend | only A |
| R2 | A, B → none (the overlay switches off under 2 brokers) | A and B stay | only the total |
| R3 | A, B → A, B, C | C is not drawn: «[ECharts] Unknown series undefined» | A, B, C |
| R4 | A, B → A, C | C takes B's place, the legend still shows B and not C | A, C |
| R5 | the same set | right | right |
| language | % in Italian → English | the legend says «MWRR cumulato», the series «Cumulative MWRR», the entry is not drawn | right |

## Solution

`e72b0b56e` («fix(charts): rebuild P&L lines on broker change»): the chart computes `seriesKey`, the names of its
series in order, and takes the full path whenever the key changes since the last draw; the key is reset with the other
`lastRendered*` values when the instance is destroyed. `CHART_SERIES_UPDATE_OPTS` is unchanged. The test replays the
calls recorded by the fake ECharts on a real instance (`vi.importActual('echarts')`) and checks that series and legend
match the new brokers. No CHANGELOG line: the broker lines never shipped in a release.

## Prevention

A partial ECharts update is safe only when the series keep their names and order; when the set of series changes,
rebuild — [[concepts/echarts-chart-gotchas]].

## Source files

| Role | Path |
|------|------|
| `seriesKey`, `needsFullInit`, the partial update | `frontend/src/lib/features/dashboard/GrowthChart.svelte` |
| Replay test | `frontend/src/lib/features/dashboard/GrowthChart.test.ts` |
| Journal (§1.3) | `LibreFolio_developer_journal/Release_2/Phase_0/47_chartAxisDayLabels/plan-phase00ChartAxisDayLabels.prompt.md` |

---
title: "The line charts lost the day on their x-axis: compact axes repeated the month, and the others spoke English or ISO dates"
category: problem
status: resolved
date: 2026-10-12
tags: [frontend, charts, echarts, x-axis, labels, i18n, intl, dashboard, assets, fx, lots, workstream-i, release-1.2]
related:
  - features/F-055
  - features/F-033
  - features/F-023
  - concepts/echarts-chart-gotchas
  - problems/pnl-lines-kept-removed-brokers
  - sources/phase00-chart-axis-day-labels-2026-10
---

# Problem: «lug lug ago ago ago ago set set set set»

## Symptom

The developer, during his checks on the server (2026-10-12): «su moltissimi grafici nell'asse x è scomparso il numero
del giorno! anche se lo spazio c'è, l'ho visto in abs e % in dashboard, in asset detail e forex detail, mentre è
corretto in candele e proventi del P&L. La differenza è che lì sono dei bucket e quindi cerchiamo di dare un nome
significativo al cestino, gli altri sono grafici a linee e se si riesce, con lo spazio, a mettere più riferimenti
temporali è una cosa buona!». His screenshot: the Growth chart, July to October, about 800 px wide, «lug lug ago ago
ago ago set set set set ott ott ott».

## Root Cause

Both are new in 1.2, from `responsiveXAxis.ts` (`2d22130bd`, workstream I, 2026-09-17).

- **Compact axes.** `formatCompactXAxisDate` chose one format from the width of the period alone: «MMM yy» beyond a
  year, «MMM» beyond 90 days, «d MMM» otherwise. Compact mode starts below 480 px or 24 px per point — with daily
  points, on nearly every long period — and ECharts puts a tick every 7–10 days, so each tick printed only its month.
  A simulation on the real ECharts 6 counted 249 identical consecutive labels on compact time axes and 163 on compact
  category axes.
- **The other axes** kept ECharts' default labels: English on time axes («Feb», «Aug»), since ECharts never received
  the language, and ISO dates on category axes («2026-07-15»). The three lots charts had their own formatter, which
  repeated the day on hourly ticks («20 ott | 20 ott | 21 ott») and printed full dates on multi-year axes.

## Solution

Workstream I, plan 47, approved by the developer — «1 ago: anche il primo del mese col suo giorno, come le altre
etichette» and «Sì, procedi; e sistema anche il percorso non compatto nello stesso lotto, con un commit a parte»:

- `4c05c1d85` («fix(charts): name the day on compact x-axes»): the formatter receives `(value, index, {level})` as
  ECharts 6 calls it. On a time axis: the data's endpoints «d MMM» (with a two-digit year when the data cross one), a
  tick off midnight empty, the 1st of January the year («2026»), the 1st of a month «d MMM» between daily ticks and
  «MMM» when the ticks are months, any other day «d MMM». A compact category axis uses the month only when every pair
  of consecutive regular labels falls in different months.
- `8682f0bbd` («fix(charts): localized labels off compact mode»): the policy always carries a formatter in the app's
  language; every chart sets it, the lots charts included, whose own formatter is gone.
- The guarantees: no two consecutive labels are equal in any simulated family; the `Intl.DateTimeFormat` instances are
  built once per policy; Candles and Income keep the bucket ladder of their own axis.
- The CHANGELOG of 1.2 says it under «Line and price charts name the day on their date axis».

## Prevention

- Pin label sequences, not single labels: the tests replay the developer's case on the real ECharts in SSR and assert
  there is no identical consecutive pair and that the day is present.
- An ECharts default label never meets the app's language: give every axis a formatter.
- Under zoom, category axes lost their labels (backlog 47-1, a defect older than this work): the compact `interval`
  was computed on all the points, and no `dataZoom` handler recomputed it. Closed in 1.3 by workstream Y, lot Y8
  (2026-10-15): the policy takes the visible count (`visibleCount`, read from the zoom event by
  `visiblePointCountFromZoom`, never from `getOption()`), and `LineChart`, `CandlestickChart` and `PriceChartFull`
  merge `categoryAxisLabelPatch()` once the gesture settles. The patch always carries `interval: 'auto'`, because a
  `setOption` merge keeps the previous window's step ([[concepts/echarts-chart-gotchas]]).

## Source files

| Role | Path |
|------|------|
| Axis policy and formatters | `frontend/src/lib/components/charts/responsiveXAxis.ts` |
| Tests (sequences on the real ECharts) | `frontend/src/lib/components/charts/chartCoreHelpers.test.ts` |
| Growth chart | `frontend/src/lib/features/dashboard/GrowthChart.svelte` |
| Line and price charts | `frontend/src/lib/components/charts/LineChart.svelte` |
| Zoomed category axes (47-1), with `LineChart` | `frontend/src/lib/components/charts/CandlestickChart.svelte`, `frontend/src/lib/components/charts/PriceChartFull.svelte` |
| Lot Y8 (47-1) | `LibreFolio_developer_journal/Release_2/Phase_1/09_dashboardCharts/plan-phase01DashboardCharts.prompt.md` |
| Allocation history | `frontend/src/lib/features/dashboard/AllocationHistoryChart.svelte` |
| Lots charts (formatter replaced) | `frontend/src/lib/features/brokers/lots/LotWacPriceChart.svelte` |
| Journal | `LibreFolio_developer_journal/Release_2/Phase_0/47_chartAxisDayLabels/plan-phase00ChartAxisDayLabels.prompt.md` |

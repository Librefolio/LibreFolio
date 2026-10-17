---
title: "Phase 0 / 47 — the day on the x-axis of line charts, and the stale P&L lines (workstream I)"
category: source
source_type: plan
date_ingested: 2026-10-12
original_path: LibreFolio_developer_journal/Release_2/Phase_0/47_chartAxisDayLabels/plan-phase00ChartAxisDayLabels.prompt.md
tags: [phase0, release2, workstream-i, charts, echarts, x-axis, i18n, growth-chart, release-1.2]
related:
  - problems/line-chart-axes-lost-the-day
  - problems/pnl-lines-kept-removed-brokers
  - concepts/echarts-chart-gotchas
  - features/F-055
---

# Source: Phase 0 / 47 — chart axis day labels

## Summary

One plan of about 300 lines, in Italian, by workstream I, written and delivered on 2026-10-12: the first item of I's
queue after M-16. It answers a regression the developer reported during his checks on the server — the line charts no
longer named the day on their x-axis — and the coordinator's item 1, the P&L lines that kept removed brokers. Both
defects came from 1.2 work (`2d22130bd`, 2026-09-17; `8ed7a0f0d`, 2026-09-18).

| Section | What it holds |
|---------|---------------|
| §0 | The developer's report and his two decisions; the coordinator's choices |
| §1 | The defects, measured on the real ECharts 6 in SSR: 249 + 163 identical consecutive labels on compact axes; the non-compact labels in English or ISO; the R1–R5 replay of the stale series |
| §2 | The approved rules for time and category axes, and the guarantees |
| §3–§5 | The four commits (C1 rules, C2 `seriesKey`, C3 the non-compact path, C4 the journal), the surfaces, the red tests in two rounds |
| §8 | The proposed 🔄 CHANGELOG line, written by the coordinator at integration |

## Key Takeaways

- **The developer's rule of thumb**: buckets get a meaningful name, lines get as many time references as the space
  allows; the day comes back, «1 ago» included.
- **One formatter for every axis**, in the app's language, so no ECharts default label survives
  ([[problems/line-chart-axes-lost-the-day]]).
- **Rebuild when the series change**: a partial update merges by position and leaves the legend
  ([[problems/pnl-lines-kept-removed-brokers]]).
- **Considered and rejected**: changing the default parameters of `buildLotXAxisPolicy()` in the resize callbacks — it
  would fix nothing and widen the batch.
- **Left for later**: item 47-1 of the backlog, category axes that lose their labels under zoom (low, older than 1.2).

## Commits

| Commit | What |
|--------|------|
| `4c05c1d85` | C1 — the compact rules: the day on compact x-axes |
| `e72b0b56e` | C2 — the P&L lines rebuilt on a broker change |
| `8682f0bbd` | C3 — localized labels off compact mode |
| `ace3455e2` | C4 — the plan, and item 47-1 in the backlog |

## Pages created from this source

- [[problems/line-chart-axes-lost-the-day]]
- [[problems/pnl-lines-kept-removed-brokers]]

Pages updated: [[concepts/echarts-chart-gotchas]], [[features/F-055]].

## Source files

| Role | Path |
|------|------|
| Plan | `LibreFolio_developer_journal/Release_2/Phase_0/47_chartAxisDayLabels/plan-phase00ChartAxisDayLabels.prompt.md` |
| Axis policy | `frontend/src/lib/components/charts/responsiveXAxis.ts` |
| Growth chart | `frontend/src/lib/features/dashboard/GrowthChart.svelte` |
| Runner (`growth-chart-memo`) | `scripts/test_runner/_frontend_asset.py` |

---
title: "Phase 0 / 20 — performance charts (rolling return, broker P&L, candles, income) and four follow-up fixes"
category: source
source_type: plan
date_ingested: 2026-10-09
original_path: LibreFolio_developer_journal/Release_2/phases/20_performanceCharts/
tags: [phase0, release2, charts, dashboard, asset-detail, echarts, pnl, asset-events, privacy, i18n, workstream-i]
related:
  - decisions/portfolio-pnl-series-contracts
  - concepts/echarts-chart-gotchas
  - problems/asset-event-edit-delete-reinsert
  - concepts/discard-the-answer-not-the-question
  - features/F-088
  - features/F-055
  - features/F-031
---

# Source: Phase 0 / 20 — performance charts

## Summary

Workstream I delivered four charts: a rolling N-calendar-day return on Asset detail (SP06 **G3**), an Income chart
of signed dividends and interest (SP06 **G1c**), a cumulative P&L mode in the Dashboard's Growth chart with one
additive line per broker (SP07 **G1a**) and synthetic P&L candles for the whole portfolio (SP07 **G1b**). Main
contract integrated at `22b82e3fb` (accepted 2026-09-22); Round 4 — 28 decisions from the 2026-09-22 usage
review — on 2026-10-02 (`975a115ae`); then four follow-ups: events on a price-cache hit (`0a2359573`, 10-07), income
colours and axis labels (`ffda8fc84`, `c001c0968`, 10-08), the asset-event editor (merged in `5423c334f`, 10-08) and
raw translations in tooltip HTML (`2c382824d`, 10-09). The two largest plans run to ~5 700 and ~6 700 lines; they
were read through their status headers, decisions and closing checks.

## Key takeaways

- The computation contracts of the three portfolio series — one replay with additive broker contributions,
  candles composed per day then bucketed, income from the ledger: [[decisions/portfolio-pnl-series-contracts]].
- G3 is computed on the backend (signal `ASSET_CALENDAR_ROLLING_RETURN`), in the target currency, with calendar
  windows: [[features/F-088]] (planned since May as a client-side chart; shipped differently).
- ECharts behaviours that looked like our bugs, and the rule adopted for each: [[concepts/echarts-chart-gotchas]].
- The asset-event editor edited by delete-and-reinsert (duplicates on a type change, a 500 on linked events, wrong
  deletes, a CSV that could not come back): [[problems/asset-event-edit-delete-reinsert]].
- A request that moved its own start date discarded its own answer: case 5 of
  [[concepts/discard-the-answer-not-the-question]].
- **D21 — tests test today's product**: delete tests of intermediate steps and product code without callers;
  delete by name and count before and after (a bulk delete once made 162 tests disappear).
- **Gate design**: check the source data (the catalogues) instead of every call site; the privacy gate cannot see
  ECharts axis formatters, so behaviour tests are the only guard there (residual I-05).
- **D28** — the `#rolling-return` link stays; the red `check-links` result in IT/FR/ES is translation debt, not an
  exception to register.
- F-084 (per-lot transaction gain chart with a FIFO/LIFO selector) was **not** built by this work.

## Residuals (backlog 38)

I-01 `aggregateSumSeries` propagates "missing" wrongly · I-02 `aggregateEnvelope` exported and unused · I-03 the `%`
toggle stays pressed while disabled · I-04 candle resolution of `PriceChartFull` · I-06 `npx` in the test runner ·
I-07 two `tsc` errors in E2E specs · I-08 MkDocs translation debt (anchors, the YOC theory page) · **I-09 an
unvalidated event `type` makes later reads fail with 500 (verified at `586a4f0ea`)** · I-10 editor robustness ·
I-11 limits of the events CSV round-trip · I-12 event delete not scoped to the asset. (I-05 comes from
[[sources/phase00-privacy-global-2026-09]].)

## Wiki pages updated

- [[decisions/portfolio-pnl-series-contracts]], [[concepts/echarts-chart-gotchas]],
  [[problems/asset-event-edit-delete-reinsert]] — new.
- [[features/F-088]] — planned → documented, rewritten to the shipped design.
- [[features/F-055]] — P&L modes; implemented → documented (`user/dashboard/charts.en.md`).
- [[concepts/discard-the-answer-not-the-question]] — case 5; its dead route path remapped.

## Source files

| Role | Path |
|------|------|
| Folder README (sub-plans, residuals) | `LibreFolio_developer_journal/Release_2/phases/20_performanceCharts/README.md` |
| Main contract (G3, G1a, G1b, G1c) | `LibreFolio_developer_journal/Release_2/phases/20_performanceCharts/plan-phase00PerformanceCharts.prompt.md` |
| Round 4 (D1–D28) | `LibreFolio_developer_journal/Release_2/phases/20_performanceCharts/plan-phase00PerformanceChartsRound4-PostMergeReview.prompt.md` |
| Events on cache hit | `LibreFolio_developer_journal/Release_2/phases/20_performanceCharts/plan-phase00PerformanceChartsBugfix-EventsOnCacheHit.prompt.md` |
| Asset events editor | `LibreFolio_developer_journal/Release_2/phases/20_performanceCharts/plan-phase00PerformanceChartsBugfix-AssetEvents.prompt.md` |
| Income colours, axis labels | `LibreFolio_developer_journal/Release_2/phases/20_performanceCharts/plan-phase00PerformanceChartsIncomeColorsAxisLabels.prompt.md` |
| Tooltip i18n escape | `LibreFolio_developer_journal/Release_2/phases/20_performanceCharts/plan-phase00PerformanceChartsBugfix-TooltipI18nEscape.prompt.md` |
| Engine series | `backend/app/services/portfolio_engine.py` |
| Rolling return plugin | `backend/app/services/signal_plugins/calendar_rolling_return.py` |
| Growth chart | `frontend/src/lib/components/dashboard/GrowthChart.svelte` |
| Tooltip HTML gate | `frontend/src/htmlInterpolation.gate.test.ts` |
| Privacy money-site gate | `frontend/src/lib/utils/privacy/moneyRenderSites.test.ts` |

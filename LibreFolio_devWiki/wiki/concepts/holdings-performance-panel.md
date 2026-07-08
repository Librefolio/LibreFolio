---
title: "Holdings / Performance Dashboard Panel"
category: concept
tags: [frontend, backend, dashboard, holdings, performance, treemap, date-aware, echarts, refactor]
related:
  - entities/portfolio-engine
  - entities/portfolio-service
  - concepts/portfolio-report-unified
  - concepts/3-pool-cash-model
  - features/F-054
  - features/F-055
---

# Concept: Holdings / Performance Dashboard Panel

## Definition

The "YOUR POSITIONS" panel on the Dashboard Home page (`PositionsPanel.svelte`) is split into two tabs —
**Holdings** and **Performance** — each with a Table/Chart toggle. This replaces the earlier
"Exposure/Contribution" naming and semantics (renamed in commit `78aaa0a3`, 2026-07-06, per
`Low-dashboard_refactor.md` design and `Low-dashboard_gap_analysis.md`).

The core insight driving the refactor: **Holdings** and **Performance** answer two genuinely different
questions and must not share a single "open/closed" toggle or a single date-biased data source:

- **Holdings** — "What do I own **right now** (at `date_to`)?" A snapshot, not a period view.
- **Performance** — "What **happened** during the selected period, across everything that mattered (open or
  closed by period end)?" A period view, not a snapshot.

## Holdings Tab

| Sub-view | Component | Shows |
|----------|-----------|-------|
| Table | `ExposureTable.svelte` (renamed content, not file) | Asset, Value, Weight, Unrealized P&L, P&L%, Quantity, Price, PMC, Broker — snapshot at `date_to` |
| Chart | `ExposureTreemap.svelte` | Area = Value at `date_to`; Color = Unrealized P&L % |

Props: `{holdings, navAmount, displayCurrency, brokers?}`. No `positionFilter`/`contribution` props — Holdings
has no concept of "closed" positions; it only shows what is open at `date_to` (`quantity > 0` filter).

## Performance Tab

| Sub-view | Component | Shows |
|----------|-----------|-------|
| Table | `ContributionTable.svelte` (renamed content) | Asset, Period P&L, Unrealized Δ, Realized Sales, Income, Costs, Start Value, End Value, **Status** (filterable enum column), Broker |
| Chart | `PerformanceChart.svelte` (new, replaces deleted `ContributionTreemap.svelte`) | Stacked diverging horizontal bar — split by sign (`positive`/`negative` stacks), not a single linear stack |
| Extra | `OtherPeriodEffectsTable.svelte` (new) | Non-asset-specific period effects (Description/Category/Period P&L/Broker), hidden when empty |

`Status` (`open_at_period_end` / `closed_by_period_end`) is a native DataTable enum filter column — **not** an
external toggle. The old global Open/Closed toggle (`positions-filter-toggle`) was removed entirely; Performance
shows open AND closed positions together by default, filterable via the Status column.

`Period P&L = Unrealized Δ + Realized Sales + Income − Costs`. Costs (`period_fees_taxes`) is positive in the
DTO but always rendered as a **negative** bar segment in `PerformanceChart` (a cost is a cost regardless of DTO
sign convention).

## Date-Aware Data Source (the actual bug fix)

Before this refactor, `get_summary()` built holdings from a **today-biased** loop:
```
today = date_type.today()
_get_latest_price()          # "latest" as of NOW, not as of date_to
quantity = all-time net qty  # not qty at date_to
```
This meant Holdings could show positions/prices that didn't reflect the selected date range at all.

After the refactor, `get_summary()` reads `engine_result.position_states_end` — computed by the engine
**exactly at `self.date_to`** (see [[entities/portfolio-engine]]). `price_change_1d` is now relative to
`date_to`, not "today". Similarly, `get_positions_contribution()`'s `qty_at_end` now filters
`tx.date <= effective_end` (previously unfiltered — future transactions relative to the period leaked in), and
uses `price_at_or_before(date_to)` instead of `_get_latest_price()`. `is_fully_sold` / Status are therefore
correctly anchored to `date_to` instead of "now".

A new `_compute_period_summary_metrics()` helper deduplicates the NAV/P&L-for-period logic that both
`get_summary()` and `get_positions_contribution()` need — eliminating the previous double computation.

Irrelevant positions (no activity in the period AND no position at either boundary,
`qty_at_start=0 and qty_at_end=0`) are now skipped, avoiding "ghost rows" not pertinent to the period.

## Reconciliation Invariant

`Period P&L` (Performance total) must reconcile against `summary.period_pnl` **by algebraic construction**,
not just empirical testing:

```
period_other_result = period_pnl_total − period_ugl_delta − total_realized − total_income + total_fees
```

Where `total_realized/income/fees` sum both per-asset AND unallocated components. Any non-zero residual becomes
an explicit "Other / reconciliation residual" row (category "Other", broker=null) in `other_effects` — it is
never silently dropped.

## Treemap Zoom/Pan Fix

`echartsTreemapZoomGuard.ts` — a pre-existing bug where ECharts' internal `_resetController` reset
`controllerHost.zoom` on every render (including the re-render triggered by zoom itself), causing cumulative
zoom-out to have no floor (treemap could shrink to a dot) and pan to drag the root rect arbitrarily far
off-screen. Root cause verified by reading `node_modules/echarts/lib/chart/treemap/TreemapView.js`: zoom fires
a `treemapRender` action, but **pan fires a separate `treemapMove` action** — a scale-only guard on
`treemaprender` alone still let pan/drag escape. Fix: listen for both `treemaprender` and `treemapmove` chart
events, independently compute true cumulative scale/position against the container's actual size, and dispatch
a corrective `treemapRender` action with a clamped rect if either falls outside bounds. This fix predates and is
independent of the Holdings/Performance renaming, but ships in the same refactor.

## Components Removed

- `ContributionTreemap.svelte` — deleted, fully replaced by `PerformanceChart.svelte` (verified no remaining
  references before removal).
- Global Open/Closed toggle (`positions-filter-toggle`) — deleted (Status is now a per-row filterable column).
- i18n keys `dashboard.exposure` / `dashboard.contribution` — deleted (dead code after rename); 17 new
  `dashboard.*` keys added across en/it/fr/es for Holdings/Performance columns, tab labels, Other Period
  Effects, status values, and `resetZoom`.

## Where It Applies

- `frontend/src/lib/components/dashboard/PositionsPanel.svelte` — tab container, wiring of all 5 components
- `frontend/src/routes/(app)/dashboard/+page.svelte` — hosts the panel, feeds data from `portfolioStore`
- `backend/app/services/portfolio_service.py` — `get_summary()`, `get_positions_contribution()`,
  `_compute_period_summary_metrics()`
- `backend/app/services/portfolio_engine.py` — `position_states_end`, `dataQuality.transactionImplied` now
  includes `as_of_date` in `message_params`

## Source files

| Role | Path |
|------|------|
| Holdings table | `frontend/src/lib/components/dashboard/ExposureTable.svelte` |
| Holdings chart | `frontend/src/lib/components/dashboard/ExposureTreemap.svelte` |
| Performance table | `frontend/src/lib/components/dashboard/ContributionTable.svelte` |
| Performance chart (new) | `frontend/src/lib/components/dashboard/PerformanceChart.svelte` |
| Other period effects (new) | `frontend/src/lib/components/dashboard/OtherPeriodEffectsTable.svelte` |
| Tab container | `frontend/src/lib/components/dashboard/PositionsPanel.svelte` |
| Treemap zoom/pan guard | `frontend/src/lib/components/charts/echartsTreemapZoomGuard.ts` |
| Service (date-aware wiring) | `backend/app/services/portfolio_service.py` |
| Engine (position_states_end) | `backend/app/services/portfolio_engine.py` |
| Schemas (`OtherPeriodEffect`, extended `AssetPeriodContribution`) | `backend/app/schemas/portfolio.py` |
| Backend tests | `backend/test_scripts/test_services/test_financial/test_portfolio_service.py` |
| API test | `backend/test_scripts/test_api/test_portfolio_api.py` |
| Design doc | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_2/lowDashboard/Low-dashboard_refactor.md` |
| Implementation notes | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_2/lowDashboard/Low-dashboard_implementation_notes.md` |
| Gap analysis | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_2/lowDashboard/Low-dashboard_gap_analysis.md` |

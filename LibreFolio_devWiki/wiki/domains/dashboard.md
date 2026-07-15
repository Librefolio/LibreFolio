---
title: "Domain: DASHBOARD"
category: domain
features: [F-054, F-055]
status: implemented
mkdocs: null
---

# Domain: DASHBOARD

> The portfolio at a glance — KPI cards, GrowthChart, allocation history, and the Holdings/Performance
> positions panel, all sourced from a single unified `/portfolio/report` engine run.

## What it does

The Dashboard Home (`/dashboard`) is the first page a user sees after logging in and answers "how is my
portfolio doing today?" It runs the [[entities/portfolio-engine]] once per request via the unified
`POST /portfolio/report` endpoint (see [[concepts/portfolio-report-unified]]) and renders every widget from
that single `EngineResult` — no separate per-widget API calls, no risk of inconsistent NAV between widgets.

The KPI row shows Net Worth, Period P&L, and Weighted ROI (TWRR + MWRR — see [[concepts/twrr-mwrr-algorithms]]).
The GrowthChart visualizes the 3-pool cash decomposition (NAV / capital / returns — see
[[concepts/3-pool-cash-model]]) as a stacked area with a rich tooltip. The Allocation panel toggles between
"Now" (current breakdown) and "History" (`AllocationHistoryChart.svelte`, evolution over time across
type/sector/geography dimensions).

The **Holdings/Performance positions panel** (`PositionsPanel.svelte`, see
[[concepts/holdings-performance-panel]]) is the most heavily refactored piece: Holdings answers "what do I own
right now at `date_to`" (table + treemap), Performance answers "what happened during the period" (table +
stacked diverging bar chart, open AND closed positions together, filterable by Status). A Recent Transactions
widget and broker/date-range filters round out the page.

Data quality issues (missing prices, `TRANSACTION_IMPLIED` valuation fallback for P2P/crowdfund assets, etc.)
are surfaced via `DataQualityBanner`, reading the now-populated `data_quality` field.

## Feature cluster

| Code | Feature | Layer | Role in domain | Status |
|------|---------|-------|----------------|--------|
| [[F-054]] | Dashboard KPI & Overview | fullstack | core — KPI cards + unified `/portfolio/report` fetch | implemented |
| [[F-055]] | Portfolio Charts (Holdings/Performance panel, GrowthChart, Allocation) | frontend | display — GrowthChart, AllocationHistoryChart, Holdings/Performance panel | implemented |

## Architecture at a glance

```mermaid
graph TD
    DashPage[/dashboard +page.svelte] -->|POST /portfolio/report| ReportAPI[portfolio_api.py<br/>unified /report entrypoint]
    ReportAPI --> PortfolioSvc[PortfolioService.get_report<br/>L2 TTL cache]
    PortfolioSvc -->|runs once| Engine[PortfolioCalculationEngine]
    Engine --> DailyStates[DailyStateBuilder<br/>3-pool K/R/W + inline WAC]
    DailyStates --> PositionEnd[position_states_end<br/>date-aware @ date_to]
    PositionEnd --> Holdings[Holdings tab<br/>ExposureTable/ExposureTreemap]
    Engine --> Contribution[get_positions_contribution<br/>date-boundary-aware]
    Contribution --> Performance[Performance tab<br/>ContributionTable/PerformanceChart]
    Engine --> History[history: NAV series]
    History --> GrowthChart[GrowthChart<br/>3-pool stacked area]
    Engine --> AllocHistory[allocation_history]
    AllocHistory --> AllocPanel[AllocationPanel<br/>Now/History toggle]
    Engine --> DataQuality[data_quality report]
    DataQuality --> Banner[DataQualityBanner]
```

## Key decisions that shaped this domain

- [[concepts/portfolio-report-unified]] — single `/portfolio/report` endpoint runs the engine once; no
  `/allocation-history` or `/overview` endpoints were ever built as separate routes.
- [[decisions/portfolio-summary-direct-wiring]] — `get_summary()` wires directly to `position_states_end`
  rather than through a separate `DerivedViewsBuilder.build_summary()` method; `net_worth` field name retained.
- [[decisions/mwrr-boundary-fix]] — MWRR double-counting bug fixed by removing a synthetic `t=0` flow.
- [[decisions/mwrr-solver-newton-cap]] — Newton-only IRR solver + result cap are deliberate, not open bugs.
- [[concepts/holdings-performance-panel]] — Holdings (snapshot) and Performance (period) are deliberately
  separate concepts with separate data sources and no shared toggle.
- **All calculations in backend** (see [[concepts/backend-only-calculations]]) — the frontend receives
  pre-computed KPI/chart values; it never performs financial calculations.

## Known problems / limitations

- [[problems/datatable-column-resize-noop]] — DataTable column-resize handle is a no-op in some tables
  (unrelated pre-existing frontend bug, low priority).
- [[problems/test-transaction-implied-constructor-mismatch]] — `test_transaction_implied.py` (6 tests) fails
  due to a pre-existing, unrelated `DailyStateBuilder` constructor mismatch in the test's local helper.
- Resolved: [[problems/portfolio-asset-history-regression-restored]] — `GET /portfolio/asset-history` was
  accidentally removed in a legacy-endpoint cleanup, then restored (found during Milestone 3 gap analysis).
- Still open, low priority (see [[sources/phase09-m1-m2-archive-2026-07]]): `internal_transfer_flow` /
  `scope_transfer_flow` diagnostic fields not implemented; allocation history sampling (weekly/monthly) not
  implemented; WAC fallback for in-transit cost basis not implemented; `get_asset_history()` ROI/unit-mix
  breakdown still deferred; external cash-bridge "early withdrawal / look-ahead" edge case unhandled by design.

## What comes next

Milestone 3 (Broker UI v2 redesign — broker-scoped Holdings/Overview/Transactions views, plus the
cross-cutting chart-resolution/semantic-zoom work) is done — archived, see
[[sources/phase09-m3-broker-redesign-2026-07]].

Later ideas:
- [[F-085]] QuarkAI Assistant — AI-powered portfolio commentary and question-answering (long-term idea).

## Source files

| Role | Path |
|------|------|
| Dashboard page | `frontend/src/routes/(app)/dashboard/+page.svelte` |
| API endpoint | `backend/app/api/v1/portfolio_api.py` |
| Service | `backend/app/services/portfolio_service.py` |
| Engine | `backend/app/services/portfolio_engine.py` |
| ROI utilities | `backend/app/utils/roi_utils.py` |
| Frontend store | `frontend/src/lib/stores/portfolio/portfolioStore.svelte.ts` |
| Positions panel | `frontend/src/lib/components/dashboard/PositionsPanel.svelte` |
| Archived M1/M2 plans | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/` |
| Archived M3 plans (Broker UI v2 + chart resolution) | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_3/` |

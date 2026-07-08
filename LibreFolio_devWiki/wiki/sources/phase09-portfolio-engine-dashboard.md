---
title: "Phase 09 — Portfolio Engine & Dashboard (Milestone 2)"
category: source
source_type: plan
date_ingested: 2026-06-30
original_path: LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_2/portfolio_engine/ARCHITECTURE_CURRENT_STATE.md
tags: [phase09, portfolio, dashboard, engine, kpi, twrr, mwrr, pnl, 3-pool, fifo, wac, echarts, scope-aware]
related:
  - entities/portfolio-engine
  - entities/portfolio-service
  - concepts/3-pool-cash-model
  - concepts/portfolio-report-unified
  - decisions/mwrr-boundary-fix
  - sources/phase09-m1-m2-archive-2026-07
  - concepts/twrr-mwrr-algorithms
  - features/F-054
  - features/F-055
---

# Source: Phase 09 — Portfolio Engine & Dashboard (Milestone 2)

## Summary

Phase 09 Milestone 2 delivers the production-grade portfolio calculation engine and the Dashboard Home UI. The architecture spans 4 layers: Engine (`portfolio_engine.py`) → Service (`portfolio_service.py`) → API (`portfolio_api.py`) → Frontend (`portfolioStore.svelte.ts`). The engine runs a 4-stage pipeline (ScopeAwareTransactionClassifier → DailyStateBuilder → DerivedViewsBuilder → PortfolioCalculationEngine) producing daily NAV series, KPI metrics (TWRR + MWRR), allocation breakdowns, and per-asset P&L contribution. The MWRR bug (double-counting deposits in XIRR) was identified and fixed. A unified `/portfolio/report` endpoint runs the engine once and returns all dashboard data. The frontend uses a L2 TTL cache keyed by broker_ids|dateRange|currency|flags.

## Key Takeaways

- **4-layer architecture**: Engine (1603 lines) → Service (1946 lines) → API → Frontend Store.
- **Engine pipeline**: `ScopeAwareTransactionClassifier` classifies transactions and in-transit intervals → `DailyStateBuilder` builds one `DailyPortfolioState` per calendar day → `DerivedViewsBuilder` computes summary/history/allocation → `PortfolioCalculationEngine` orchestrates async data loading.
- **3-pool cash model**: Cash ledger decomposed into: (1) deposited capital, (2) invested capital, (3) realized cash. Event-driven state machine. Used for GrowthChart stacked-area visualization.
- **Scope-aware**: V(u) = visible brokers; S ⊆ V(u) = selected for aggregation. `last_buy_price` used as asset-level valuation fallback when no market price.
- **Valuation hierarchy per asset per day**: MARKET_PRICE (backward-fill) → TRANSACTION_IMPLIED (WAC × qty) → MISSING (excluded from NAV).
- **MWRR bug**: `initial_nav = total_invested` caused double-counting of deposits in XIRR. Fix: `initial_nav = nav_snapshots[0].nav ≈ 0`. See [[decisions/mwrr-boundary-fix]].
- **Unified `/portfolio/report` endpoint**: runs engine ONCE, returns `{summary, history, allocation_history, data_quality, positions_contribution}`. Primary path for dashboard.
- **L2 TTL cache**: `get_report()` caches by `(user_id, broker_ids, currency, date_range, flags, tx_fingerprint, price_fingerprint)`. Invalidated on tx/price change.
- **P&L breakdown**: realized (WAC-based) + unrealized + fees, period-scoped. WAC-based realized is coherent with `open_cost_basis = WAC × qty`.
- **Dashboard KPI cards**: Net Worth / Period P&L / Returns (TWRR + MWRR). GrowthChart has 3 series: NAV / invested capital / cash.
- **Frontend store**: `portfolioStore.svelte.ts` (156 lines) — `fetchReport()` → `POST /portfolio/report`. Cache key = `broker_ids|dateFrom|dateTo|currency|contrib_flag`.
- **ECharts + Emoji**: `AllocationPieChart` supports Noto Color Emoji (loaded via FontFace API for sector emoji). FX bulk fetch for currency conversion.
- **Known issues at ingest** (RESOLVED 2026-07-06, commit `78aaa0a3` — see [[sources/phase09-m1-m2-archive-2026-07]]):
  - ~~Bug 2: P2P/crowdfund `current_value=None` (no TRANSACTION_IMPLIED fallback in service holdings loop)~~ — fixed
  - ~~WAC computed 2× per asset (engine pre-load + service per-call redundancy)~~ — improved via `_compute_period_summary_metrics()` shared helper
  - ~~Realized/income/fees computed 2× (summary + contribution separate loops)~~ — improved, see [[entities/portfolio-service]] item 3 caveat
  - Emoji absent in Asset Detail chart (missing emoji field in `cp.sector_area.distribution`) — not re-verified in this pass, status unknown

## Wiki Pages Created/Updated

- [[entities/portfolio-engine]] — new: 4-layer architecture + pipeline
- [[entities/portfolio-service]] — new: PortfolioService methods + L2 cache
- [[concepts/3-pool-cash-model]] — new: cash decomposition for GrowthChart
- [[concepts/portfolio-report-unified]] — new: /portfolio/report unified endpoint
- [[decisions/mwrr-boundary-fix]] — new: XIRR double-counting fix

## Source files

| Role | Path |
|------|------|
| Architecture state report | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_2/portfolio_engine/ARCHITECTURE_CURRENT_STATE.md` |
| Mathematical model | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_2/portfolio_engine/portfolio_engine_architecture_v2.md` |
| MWRR fix analysis | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_2/portfolio_engine/mwrr_analysis_report.md` |
| P&L breakdown analysis | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_2/portfolio_engine/pnl_breakdown_analysis.md` |
| Dashboard UI plan | `LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/plan_ui_dashboard.md` |
| Engine | `backend/app/services/portfolio_engine.py` |
| Service | `backend/app/services/portfolio_service.py` |
| API | `backend/app/api/v1/portfolio_api.py` |
| Frontend store | `frontend/src/lib/stores/portfolioStore.svelte.ts` |
| ROI utilities | `backend/app/utils/roi_utils.py` |
| FIFO utilities | `backend/app/utils/fifo_utils.py` |
| WAC utilities | `backend/app/utils/wac_utils.py` |

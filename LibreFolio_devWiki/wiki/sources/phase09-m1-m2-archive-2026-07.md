---
title: "Phase 09 Milestone 1 & 2 — Archival + Exhaustive Verification (2026-07-07)"
category: source
source_type: plan
date_ingested: 2026-07-07
original_path: LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/ (Milestone_1/, Milestone_2/)
tags: [phase09, archive, portfolio, dashboard, holdings, performance, mwrr, twrr, verification, closeout]
related:
  - entities/portfolio-engine
  - entities/portfolio-service
  - concepts/holdings-performance-panel
  - concepts/portfolio-report-unified
  - concepts/twrr-mwrr-algorithms
  - decisions/mwrr-solver-newton-cap
  - decisions/portfolio-summary-direct-wiring
  - problems/test-transaction-implied-constructor-mismatch
  - problems/datatable-column-resize-noop
  - sources/phase09-portfolio-engine-dashboard
  - sources/phase09-portfolio-engine-3pool-refactor
  - features/F-054
  - features/F-055
  - features/F-058
---

# Source: Phase 09 Milestone 1 & 2 — Archival + Exhaustive Verification

## Summary

Phase 09 Milestone 1 (backend/API portfolio foundations — TWRR/MWRR, unified endpoints) and Milestone 2
(Dashboard Home, Portfolio Calculation Engine, Positions/Performance panel) were archived via `git mv` from
`LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/` into
`LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/`, alongside cross-cutting root docs
(`implementation_roadmap.md`, `plan_financial_algorithms.md`, `plan_ui_dashboard.md`,
`report_asset_level_contribution_gap_analysis.md`, `report_dashboard_bottom_widgets_analysis.md`,
`plan-gallery-update.prompt.md`). Milestone 3 (Broker UI v2 redesign) remains active and was NOT archived.

Before archiving, an **exhaustive verification pass** (not sampled) was run against the current codebase for
every open item listed in the Milestone 2 analysis docs (`implementation_status_report.md`,
`STATUS_REPORT_M2.md`, `ARCHITECTURE_CURRENT_STATE.md`, dated 2026-06-19/06-30). This closes out most of the
"Known Issues / Technical Debt" and "Remaining gaps" sections previously recorded in
[[entities/portfolio-service]] and [[sources/phase09-portfolio-engine-3pool-refactor]].

## Key Takeaways

### Resolved (≈20 items) — already fixed by later implementation work (this session's Holdings/Performance
refactor of 2026-07-06, commit `78aaa0a3`, plus prior work)

- `get_summary()` now wired to `PortfolioCalculationEngine` (reads `engine_result.position_states_end`,
  date-aware at `date_to`) — previously used a separate "latest price only" / today-biased loop.
- `build_data_quality_report()` implemented and wired — `data_quality` field in `PortfolioSummary` /
  `AllocationHistoryResponse` is now populated (previously always `None`).
- `first_position_date` field present in the API response.
- GrowthChart: ABS stacked area + rich tooltip implemented (3-pool K/R/W visualization, see [[concepts/3-pool-cash-model]]).
- AllocationPanel Now/History toggle + `AllocationHistoryChart.svelte` implemented.
- `DataQualityBanner` now reads the unified `data_quality` field (previously read stale/legacy fields).
- `TRANSACTION_IMPLIED` fallback for P2P/crowdfund assets implemented — holdings no longer show
  `current_value=None` when no market price exists (`open_cost_basis` used as valuation proxy).
- Transaction double-click now opens a modal (not a page navigation) — unrelated frontend UX fix bundled in
  the same closeout pass.

### Resolved differently than originally designed (≈7 items) — architecture evolved

See [[decisions/portfolio-summary-direct-wiring]] for full detail:
- No separate `DerivedViewsBuilder.build_summary()` method — wiring was done directly inside
  `PortfolioService.get_summary()` instead (simpler, avoids an extra indirection layer).
- The separate `/allocation-history` endpoint proposed in early plans was never built — superseded by the
  single unified `/portfolio/report` endpoint (see [[concepts/portfolio-report-unified]], already the intended
  design by the time Milestone 2 shipped).
- `net_worth` field name was **kept** (not renamed to `nav_value` as some analysis docs suggested) — but the
  value is now correctly sourced from the engine's NAV computation instead of the old ad-hoc calculation.
- The MWRR double-counting bug (see [[decisions/mwrr-boundary-fix]]) was resolved via a different formula
  correction than originally proposed in the analysis docs (removing the synthetic `t=0` flow rather than
  patching the cash-flow list).
- Cash-flow-on-end-date handling (a boundary case flagged in `mwrr_boundary_anomaly_report.md`) is resolved.

### Genuinely still open (≈7 items, low priority)

- `internal_transfer_flow` / `scope_transfer_flow` diagnostic fields — not implemented.
- Allocation history sampling (weekly/monthly aggregation) — not implemented; daily granularity only.
- WAC fallback for in-transit cost basis — not implemented.
- `get_asset_history()` ROI / unit-mix breakdown — still deferred.
- External cash-bridge "early withdrawal / look-ahead" edge case — still unhandled by design (see
  `external_cash_bridge_edge_case_report.md`).

### Important clarification — NOT bugs, deliberate design decisions

See [[decisions/mwrr-solver-newton-cap]]. The MWRR result cap ("100x" mentioned in old analysis docs) and the
choice of a **Newton-only** solver (vs. Brent/hybrid, as `mwrr-numerical-stability-analysis.md` explored) are
**intentional project design choices**, not open bugs. Earlier analysis docs proposed a hybrid solver and no
result cap; the team deliberately chose Newton-only + a result cap instead. Do not re-flag these as bugs in
future ingests.

### Unrelated pre-existing issues surfaced during verification (still open, low priority)

- [[problems/test-transaction-implied-constructor-mismatch]] — `test_transaction_implied.py` (6 tests) fails:
  the test helper's `DailyStateBuilder(...)` call still passes a `wac_series` kwarg and omits the now-required
  `asset_currencies` kwarg, both stale from before the inline-WAC refactor (commit `39106380`). Not part of the
  archived M1/M2 work — a pre-existing test-maintenance gap.
- [[problems/datatable-column-resize-noop]] — `DataTable.svelte`'s column-resize handle renders but clicking/
  dragging has no visible effect in some consuming tables. Unrelated to the dashboard refactor.

## Wiki Pages Created / Updated

**Created**:
- [[sources/phase09-m1-m2-archive-2026-07]] — this page
- [[concepts/holdings-performance-panel]] — Holdings/Performance dashboard panel (lowDashboard refactor)
- [[decisions/mwrr-solver-newton-cap]] — Newton-only solver + result cap as deliberate design
- [[decisions/portfolio-summary-direct-wiring]] — direct wiring + endpoint consolidation + field-naming decisions
- [[problems/test-transaction-implied-constructor-mismatch]] — pre-existing test breakage
- [[problems/datatable-column-resize-noop]] — pre-existing frontend UI bug

**Updated**:
- [[entities/portfolio-service]] — Known Issues section: items resolved, dated
- [[entities/portfolio-engine]] — removed stale "get_summary() wiring incomplete" gotcha; History table updated
- [[concepts/twrr-mwrr-algorithms]] — linked new solver-design decision
- [[concepts/portfolio-report-unified]] — confirmed as sole entrypoint (no separate `/allocation-history`)
- [[sources/phase09-portfolio-engine-dashboard]] — "Known issues at ingest" marked resolved
- [[sources/phase09-portfolio-engine-3pool-refactor]] — "Remaining gaps" marked resolved
- [[features/F-054]], [[features/F-055]], [[features/F-058]] — status `planned` → `implemented`
- [[features/registry]] — status column updated for F-054/F-055/F-058
- [[domains/dashboard]] — rewritten to reflect implemented state
- [[domains/calculations]] — F-058 status updated

## Source files

| Role | Path |
|------|------|
| Archived index (new) | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/README.md` |
| Active M3 index (root) | `LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/README.md` |
| Phase status doc | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-dashboard.md` |
| M1 backend plans | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_1/` |
| M2 dashboard + engine plans | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_2/` |
| Holdings/Performance refactor notes | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_2/lowDashboard/Low-dashboard_implementation_notes.md` |
| Service (get_summary, get_positions_contribution) | `backend/app/services/portfolio_service.py` |
| Engine | `backend/app/services/portfolio_engine.py` |
| Failing test (unrelated) | `backend/test_scripts/test_services/test_financial/test_portfolio_engine/test_transaction_implied.py` |
| DataTable component (unrelated bug) | `frontend/src/lib/components/table/DataTable.svelte` |

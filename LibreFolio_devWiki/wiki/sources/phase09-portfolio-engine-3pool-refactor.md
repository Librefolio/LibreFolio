---
title: "Phase 09 — Portfolio Engine 3-Pool Refactor (commit 39106380)"
category: source
source_type: journal_entry
date_ingested: 2026-07-01
original_path: LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/Milestone_2/portfolio_engine/
tags: [backend, portfolio, engine, wac, 3-pool, refactor, inline-wac, pre-frame, blob-cache, performance]
related:
  - entities/portfolio-engine
  - entities/portfolio-service
  - concepts/3-pool-cash-model
  - concepts/inline-wac-computation
  - concepts/pre-frame-frame-separation
  - decisions/mwrr-boundary-fix
---

# Source: Phase 09 — Portfolio Engine 3-Pool Refactor

## Summary

Commit `39106380` (2026-06-30) introduces a major refactor of `portfolio_engine.py` and `portfolio_service.py`. The engine is restructured around a **per-transaction unified loop** that computes WAC inline (eliminating N×M `compute_wac_iterative` DB calls), enforces **pre-frame/frame separation** (no market evaluation before t0), upgrades to the full **3-pool event-driven model** (K/R/W pools with correct SELL ordering), and adds a **range-aware blob cache** with fingerprint keys. The key correctness fix is that SELL now reads WAC _before_ reducing the pool, preventing full-exit proceeds from going entirely to the returns pool instead of splitting K+R correctly.

The supporting analysis documents (`ARCHITECTURE_CURRENT_STATE.md`, `ARCH_ANALYSIS_PORTFOLIO_ENGINE.md`, `implementation_status_report.md`, `mwrr_analysis_report.md`, `pnl_breakdown_analysis.md`) provide the mathematical spec, root-cause analysis, and remaining gap list.

## Key Takeaways

- **Inline WAC**: the engine now computes WAC in a single pass through the transaction list, using `pool_qty` / `pool_cost` accumulators. The old `wac_series` pre-load + `compute_wac_iterative` N×M DB calls are eliminated.
- **3-Pool event-driven (K/R/W)**: `capital_pool (K)`, `returns_pool (R)`, `withdrawn_returns_pool (W)` with strict per-event update rules. The pools power the GrowthChart stacked area.
- **SELL fix**: SELL reads WAC _before_ reducing the pool. Old code read WAC _after_, causing full-exit proceeds to split incorrectly (all to returns, none to capital).
- **Price fallback chain**: `MARKET_PRICE → LAST_BUY_PRICE(V(u)) → MISSING` — LAST_BUY_PRICE uses the last BUY price across all _visible_ brokers (V(u)), not just selected (S).
- **Pre-frame/frame separation**: transactions before t0 run through the pre-frame loop (updates qty, WAC, cash, K/R/W; no market eval). The frame [t0,t1] runs full daily evaluation.
- **Blob cache**: fingerprint-keyed, range-aware. A cache hit is valid if the stored range _contains_ the requested range (not just equality). Supports range extension for partial misses.
- **+612 lines** in `portfolio_service.py`, new test file `test_portfolio_engine_vnext.py` (20 unit tests).
- **Remaining gaps** (post-refactor): `get_summary()` wiring to new engine incomplete; GrowthChart stacked area not yet done; allocation-history frontend missing; DataQualityReport never populated.

## Wiki Pages Created / Updated

- [[sources/phase09-portfolio-engine-3pool-refactor]] — this page
- [[entities/portfolio-engine]] — updated: inline WAC, price fallback chain, blob cache, pre-frame/frame, 3-pool SELL fix
- [[entities/portfolio-service]] — updated: +612 lines, new test file noted
- [[concepts/3-pool-cash-model]] — updated: K/R/W semantics, event-driven rules, SELL fix, invariant
- [[concepts/inline-wac-computation]] — new: single-pass WAC replacing N×M DB calls
- [[concepts/pre-frame-frame-separation]] — new: no market eval before t0

## Source files

| Role | Path |
|------|------|
| Architecture post-refactor | `LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/Milestone_2/portfolio_engine/ARCHITECTURE_CURRENT_STATE.md` |
| Math spec (3-pool + WAC + cache) | `LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/Milestone_2/portfolio_engine/portfolio_engine_architecture_v2.md` |
| Architectural analysis (pre-refactor) | `LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/Milestone_2/portfolio_engine/ARCH_ANALYSIS_PORTFOLIO_ENGINE.md` |
| Implementation status | `LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/Milestone_2/portfolio_engine/implementation_status_report.md` |
| MWRR analysis | `LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/Milestone_2/portfolio_engine/mwrr_analysis_report.md` |
| P&L breakdown analysis | `LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/Milestone_2/portfolio_engine/pnl_breakdown_analysis.md` |
| Asset contribution gap analysis | `LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/report_asset_level_contribution_gap_analysis.md` |
| Engine implementation | `backend/app/services/portfolio_engine.py` |
| Service implementation | `backend/app/services/portfolio_service.py` |
| vNext unit tests | `backend/test_scripts/test_portfolio_engine_vnext.py` |

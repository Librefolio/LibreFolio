---
title: "Phase 09 Dashboard Batch"
category: "source"
tags: ["phase-09", "dashboard", "kpi", "twrr", "mwrr", "fifo", "portfolio"]
related: ["F-054"]
---

# Phase 09 Dashboard Batch

## Summary
The Phase 09 batch encompasses the master plan, algorithmic design, UI wireframes, and milestone breakdown for the new Dashboard and Broker details views. It transitions from legacy FastAPI/SvelteKit scattered metrics to a unified `portfolio_service.py` calculation layer with Time-Weighted Rate of Return (TWRR) and Money-Weighted Rate of Return (MWRR) implementations. The UI design heavily emphasizes visual metrics (KPI cards, ECharts pie and line charts) and introduces FIFO lot tracking for granular position analysis.

## Key Takeaways
- **TWRR & MWRR**: Implementation of proper financial algorithms for performance tracking across global portfolio and individual brokers.
- **FIFO Lot Tracking**: Slide-over modals for detailed holding breakdowns, matching buys and sells chronologically.
- **Unified Portfolio Service**: Consolidation of backend metrics into `/portfolio/*` endpoints instead of scattered ones.
- **Milestone Approach**: 5 incremental milestones (Backend, Dashboard Home, Broker Shell/Overview, Broker Holdings/FIFO, Broker Transactions/Cleanup).

## Pages Created / Updated
- [[concepts/twrr-mwrr-algorithms]]
- [[concepts/fifo-lot-tracking]]
- [[features/F-054]] (Updated conceptually)

## Source files
| File | Git Hash | Date |
|------|----------|------|
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/plan_financial_algorithms.md` (moved 2026-07-07, was `phase-09-subplan/` before archive) | `24cdc40` | 2026-06-17 |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/implementation_roadmap.md` (moved 2026-07-07, was `phase-09-subplan/` before archive) | `24cdc40` | 2026-06-17 |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/plan_ui_dashboard.md` (moved 2026-07-07, was `phase-09-subplan/` before archive) | `24cdc40` | 2026-06-17 |
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-dashboard.md` | `24cdc40` | 2026-06-17 |

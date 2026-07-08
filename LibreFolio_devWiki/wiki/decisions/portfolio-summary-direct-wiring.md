---
title: "Portfolio summary: direct wiring over separate builder method"
category: decision
status: resolved
date: 2026-07-06
tags: [backend, portfolio, architecture, api, get_summary, refactor, naming]
related:
  - entities/portfolio-engine
  - entities/portfolio-service
  - concepts/portfolio-report-unified
  - concepts/holdings-performance-panel
  - decisions/mwrr-boundary-fix
  - features/F-054
---

# Decision: Portfolio Summary — Direct Wiring Over Separate Builder Method

## Context

Early Milestone 2 architecture docs (`portfolio_engine_architecture_v2.md`, `ARCHITECTURE_CURRENT_STATE.md`)
proposed a `DerivedViewsBuilder.build_summary()` method as the intended home for assembling
`PortfolioSummary` from `EngineResult`, mirroring how `DerivedViewsBuilder` already builds `history` and
`allocation_history`. They also proposed a dedicated `/allocation-history` API endpoint, and considered
renaming the `net_worth` response field to `nav_value` to better reflect that it is sourced from the engine's
NAV computation rather than a naive sum.

By the time the Holdings/Performance refactor (commit `78aaa0a3`, 2026-07-06) closed out the remaining gaps,
none of these three proposals were implemented as originally designed. This record captures why, so future
ingests don't flag them as "incomplete" or regressions.

## Options Considered

1. **`DerivedViewsBuilder.build_summary()`** (originally proposed) — consistent with `build_history()` /
   `build_allocation_history()`, but would require passing/duplicating the same period-boundary logic
   (`date_to`-anchored holdings, `qty_at_end` filtering) that `PortfolioService` already needed for
   `get_positions_contribution()` — see [[concepts/holdings-performance-panel]].
2. **Direct wiring inside `PortfolioService.get_summary()`** (what was actually built) — `get_summary()` reads
   `engine_result.position_states_end` directly and calls the new shared `_compute_period_summary_metrics()`
   helper (also used by `get_positions_contribution()`), avoiding a second abstraction layer that would only
   ever have one caller.
3. **Separate `/allocation-history` endpoint** (originally proposed) — would duplicate an engine run already
   covered by the unified `/portfolio/report` endpoint.
4. **Rename `net_worth` → `nav_value`** (originally proposed) — a breaking API/schema change for a cosmetic
   naming improvement.

## Decision

- **No separate `DerivedViewsBuilder.build_summary()` method.** `get_summary()` wires directly to
  `engine_result.position_states_end` and the shared `_compute_period_summary_metrics()` helper. Simpler, one
  fewer indirection, and the logic it needs is already service-layer logic shared with
  `get_positions_contribution()` — putting it in the engine's builder would not have reduced duplication, only
  moved it.
- **No separate `/allocation-history` endpoint was built.** The unified `/portfolio/report` endpoint (see
  [[concepts/portfolio-report-unified]]) was already the intended long-term design by the time this was
  revisited; the early proposal for a standalone endpoint predates that decision and was superseded, not
  abandoned as incomplete work.
- **`net_worth` field name was kept.** Renaming to `nav_value` was rejected as an unnecessary breaking change
  for existing frontend consumers with no functional benefit — the field's **value** now correctly sources
  from the engine's NAV computation (via `position_states_end`), which was the actual bug; the name was never
  the problem.

## Consequences

- `PortfolioService` remains the single place where API-shaped DTOs are assembled; `PortfolioEngine` /
  `DerivedViewsBuilder` stay focused on producing engine-native aggregates (`history`, `allocation_history`)
  that don't need period-boundary-specific business logic re-derivation.
- No `/allocation-history` route exists or is planned — `/portfolio/report`'s `allocation_history` field is the
  only path. Any reference to a standalone endpoint in older docs is historical, not a gap.
- The `net_worth` field name is stable API surface — do not propose renaming it again without a versioned
  migration plan.

## Links

- [[concepts/holdings-performance-panel]] — the refactor that necessitated this wiring decision
- [[concepts/portfolio-report-unified]] — why a separate `/allocation-history` endpoint was never needed
- [[entities/portfolio-service]] — `get_summary()`, `_compute_period_summary_metrics()`
- Source: `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_2/lowDashboard/Low-dashboard_implementation_notes.md`

## Source files

| Role | Path |
|------|------|
| Service (get_summary, shared helper) | `backend/app/services/portfolio_service.py` |
| Engine (position_states_end) | `backend/app/services/portfolio_engine.py` |
| API (single /report entrypoint) | `backend/app/api/v1/portfolio_api.py` |
| Implementation notes | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_2/lowDashboard/Low-dashboard_implementation_notes.md` |
| Original architecture proposal | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_2/portfolio_engine/portfolio_engine_architecture_v2.md` |

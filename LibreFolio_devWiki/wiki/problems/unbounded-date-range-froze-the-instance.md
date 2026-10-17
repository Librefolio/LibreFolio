---
title: "An unbounded date range froze the instance: the replay walked every requested day"
category: problem
status: resolved
date: 2026-10-17
tags: [backend, security, dos, portfolio-engine, lots, risk, ai-export, workstream-j]
related:
  - problems/share-mismatch-warning-never-left-the-classifier
  - decisions/financial-math-one-home
---

# Problem: an unbounded date range froze the instance

## Symptom

`POST /portfolio/report {"date_range": {"end": "9999-12-30"}}` made the portfolio engine replay about 2.9 million days,
synchronously, on the event loop: the whole instance stopped answering. Any authenticated user could do it.

- The same request shape reached `/risk/query` (portfolio scope), `/portfolio/lots/analysis` and the AI Export
  `period`.
- A start of `0001-01-01` went through the same path.
- Found by workstream E's security review (R13-SEC7-1, MEDIUM 8/10); fixed by workstream J on 17/10/2026.

## Root Cause

`OpenDateRangeModel` (`schemas/common.py`) checks only `end >= start`. The engine then took both ends as given:
- `actual_to = date_to or today`;
- `actual_from = date_from or first transaction`;
- `DailyStateBuilder.build()` walked every day between them.

Lots analysis (`_date_range(computed_from, actual_to)`) and the AI Export components (`technical_shared.py`) walked
their own ranges the same way.

## Solution

One rule, `latest_range_end()` in `backend/app/utils/datetime_utils.py`: a range ends no later than tomorrow, by the
server's local calendar. The extra day is slack for a user east of the server, whose today is already the server's
tomorrow. It is applied where each range enters:
- **engine**: it also starts no earlier than the first transaction. A range that ends before the first transaction
  returns an empty result;
- **`PortfolioService.get_summary` / `get_report`**: the summary's MWRR horizon, stale-price days, metadata and L2
  cache key all see the bounded end;
- **lots analysis**;
- **risk's portfolio scope**: start and end are bounded before `OpenDateRangeModel` is built, since it would refuse
  start > end;
- **AI Export**: `prepare_request()` bounds the period (end ≤ tomorrow; start ≥ end − 100 calendar years, never after
  the end). `build_snapshot()` continues from that request, so the scope, the components and the meta read the same
  period. No component contract changed.

## Decision: bound from today, not from the data

The today-based bound broke about 30 existing service tests. They live in 2032–2091 so they own their FX and price
rows. A data-based bound (`max(today, last transaction) + 1`) would have spared them, but one stored transaction dated
9999 would then freeze the replay again.

So the bound stays at tomorrow. The far-future suites lift it through a test seam: the consumers import
`latest_range_end` by name, and a module-scoped autouse fixture patches it in the five consumer modules.

## Residual vectors (routed, not fixed here)

- **Absurd stored dates**: a transaction dated `0001-01-01` makes every replay walk about 740 000 days. That needs a
  date check at write → workstream W, inside SEC7-3.
- **Price backfill**: `assets/price_query.py:140-183`, also reached by `/risk/query` for priced assets, builds one
  point per day up to the raw end → workstream X.
- **The replay on the event loop**: the engine's `builder.build()` still runs there → J-45 (SEC7-1b).

## Source files

| Role | Path |
|------|------|
| The bound | `backend/app/utils/datetime_utils.py` |
| Engine | `backend/app/services/financial_math/portfolio/engine.py` |
| Portfolio service | `backend/app/services/portfolio_service.py` |
| Lots analysis | `backend/app/services/lots_analysis_service.py` |
| Risk portfolio scope | `backend/app/services/risk/scope.py` |
| AI Export runtime | `backend/app/services/ai_export/runtime_service.py` |
| Tests | `backend/test_scripts/test_services/test_financial/test_date_range_bounds.py` |
| Tests (AI Export) | `backend/test_scripts/test_services/test_ai_export_period_bounds.py` |
| Plan | `LibreFolio_developer_journal/Release_2/Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md` |

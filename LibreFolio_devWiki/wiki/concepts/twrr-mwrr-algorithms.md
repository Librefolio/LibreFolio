---
title: "TWRR and MWRR Algorithms"
category: "concept"
tags: ["finance", "twrr", "mwrr", "algorithms", "performance"]
related:
  - entities/portfolio-engine
  - entities/portfolio-service
  - concepts/fifo-lot-tracking
  - decisions/mwrr-solver-newton-cap
  - decisions/mwrr-boundary-fix
  - features/F-054
---

# TWRR and MWRR Algorithms

## Context
As part of Phase 09 (Dashboard), LibreFolio introduces proper financial performance tracking using industry-standard formulas to measure returns.

## Concept
1. **TWRR (Time-Weighted Rate of Return)**:
   - Measures the compound rate of growth of the portfolio.
   - Eliminates the distorting effects of cash inflows and outflows.
   - Used to evaluate the performance of the investment strategy itself.
   - Implemented by breaking the evaluation period into sub-periods based on cash flow events, calculating the return for each sub-period, and geometrically linking them.

2. **MWRR (Money-Weighted Rate of Return) / IRR**:
   - Calculates the discount rate that makes the present value of all cash flows equal to the final portfolio value.
   - Accounts for the size and timing of cash flows.
   - Evaluates the user's specific performance (including their timing decisions).
   - Calculated using Newton-Raphson to find the Internal Rate of Return (IRR). This is a **deliberate,
     Newton-only** choice (no Brent/hybrid fallback) with a result cap as a display safety valve for pathological
     inputs — not an open bug. See [[decisions/mwrr-solver-newton-cap]].
   - The double-counting boundary bug (synthetic `t=0` flow duplicating deposits) was fixed 2026-06-30 — see
     [[decisions/mwrr-boundary-fix]].

## Source files
| File |
|------|
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/plan_financial_algorithms.md` |
| `backend/app/utils/roi_utils.py` |

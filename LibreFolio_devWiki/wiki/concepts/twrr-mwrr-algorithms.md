---
title: "TWRR and MWRR Algorithms"
category: "concept"
tags: ["finance", "twrr", "mwrr", "algorithms", "performance"]
related: ["phase09-dashboard-batch"]
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
   - Typically calculated using numerical methods (e.g., Newton-Raphson) to find the Internal Rate of Return (IRR).

## Source files
| File |
|------|
| `LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/plan_financial_algorithms.md` |

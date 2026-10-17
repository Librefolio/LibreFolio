---
title: "ACT/ACT lost one day at every year end it crossed"
category: problem
status: resolved
date: 2026-10-17
tags: [backend, financial-math, day-count, scheduled-investment, interest, workstream-j]
related:
  - problems/maturity-settlement-counted-the-final-coupon-twice
  - decisions/financial-math-one-home
  - decisions/scheduled-investment-redesign
  - features/F-034
---

# Problem: ACT/ACT lost one day at every year end it crossed

## Symptom

Under the ACT/ACT day count, a span that crossed a year end was one day short per year end. 2025-07-01 → 2026-06-30
gave 363/365 instead of 364/365. The Scheduled Investment provider felt it only where it computes a span in one go:
the SIMPLE late interest after maturity, in closed form, when the grace or late period crossed a 31 December. The
daily accrual walk was already right, because a one-day step across New Year belongs to the old year. Found while
analysing lot CP-14 (workstream J); fixed in CP-14b.

## Root Cause

`_calculate_act_act` closed each year at `date(Y, 12, 31)` and counted `(31/12 − start).days`. That difference leaves
out the day from 31 December to 1 January. The three tests pinning cross-year ACT/ACT fractions in
`test_day_count_conventions.py` encoded the wrong values.

## Solution

ACT/ACT ISDA, in `backend/app/services/financial_math/interest.py`. The span is cut at every 1 January it crosses:
each piece `[max(start, 1/1 Y), min(end, 1/1 Y+1))` counts its days over the length of year Y (366 or 365), and empty
pieces are skipped.

- Same-year spans and one-day steps are unchanged, and so is the accrual walk.
- The values were declared before the code, in memory against the golden net
  (`backend/test_scripts/fixtures/scheduled_investment/accrual_golden.json`). Three points changed, all ACT/ACT SIMPLE
  late interest across a 31 December, each by one more day of late interest: e.g. 14 103.23 → 14 107.28.
- The regenerated golden differed from the fixture in exactly those points.

## Tests

- `TestACTACTYearEnds` in `test_day_count_conventions.py` covers one year end, a leap year end, two year ends, a span
  split on 1 January, plus guards for one-day steps and spans inside one year.
- The three wrong expectations were corrected, with the ISDA reasoning in their comments.

## Source files

| Role | Path |
|------|------|
| Implementation | `backend/app/services/financial_math/interest.py` |
| Consumer (late interest, accrual) | `backend/app/services/asset_source_providers/scheduled_investment/plugin.py` |
| Unit tests | `backend/test_scripts/test_utilities/test_day_count_conventions.py` |
| Golden net | `backend/test_scripts/fixtures/scheduled_investment/accrual_golden.json` |
| Plan | `LibreFolio_developer_journal/Release_2/Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md` |

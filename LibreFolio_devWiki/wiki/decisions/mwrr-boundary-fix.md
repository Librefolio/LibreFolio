---
title: "MWRR boundary fix — XIRR double-counting deposits"
category: decision
status: resolved
date: 2026-06-30
tags: [backend, portfolio, mwrr, xirr, roi, performance, bug-fix, financial-math]
related:
  - entities/portfolio-engine
  - entities/portfolio-service
  - concepts/twrr-mwrr-algorithms
  - features/F-054
---

# Decision: MWRR Boundary Fix — XIRR Double-Counting Deposits

## Context

The MWRR (Money-Weighted Rate of Return) card on the Dashboard was showing `-36.71%` for a portfolio with clearly positive performance. Code-level analysis identified a double-counting bug in `roi_utils.py`.

## Root Cause

`calculate_mwrr()` used `initial_nav = total_invested` as the synthetic t=0 cash flow:

```python
flows.append((0.0, -float(initial_nav)))            # t=0: −total_invested (all deposits summed)
for cf in cash_flows:
    flows.append((float(days), float(cf.amount)))   # each DEPOSIT also appears here
flows.append((float(total_days), float(final_nav))) # t=T: +engine_nav_today
```

`cash_flows_perf` already contained every DEPOSIT/WITHDRAWAL at its actual date. And `total_invested = Σ(DEPOSITS) − Σ(WITHDRAWALS)`. So the same deposits appeared at TWO positions in the NPV equation:
1. Once at t=0 as synthetic `−total_invested`
2. Once at their actual dates

With deposits double-counted, the NPV at r=0 was deeply negative, forcing the XIRR solver to find a very negative rate to achieve NPV=0.

## Decision

Remove the synthetic `t=0 = −total_invested` flow. Replace with `initial_nav = nav_snapshots[0].nav` (the actual portfolio NAV at the start of the requested period, approximately 0 for a new portfolio or the actual market value for an ongoing period).

**Corrected equation**:
```python
flows.append((0.0, -float(initial_nav)))            # t=0: −starting_nav (≈0 for new portfolio)
for cf in cash_flows:
    flows.append((float(days), float(cf.amount)))   # each DEPOSIT/WITHDRAWAL at its date
flows.append((float(total_days), float(final_nav))) # t=T: +ending_nav
```

This is the standard XIRR/MWRR formula: initial investment (negative) + intermediate flows at their dates + terminal value (positive).

## Consequences

- MWRR now shows a reasonable positive return (~+26% in the example vs −36.71% with bug)
- The fix only touches `roi_utils.py::calculate_mwrr()` — no schema or API changes
- TWRR was not affected (different algorithm, no synthetic total)

## Links

- [[entities/portfolio-service]] — `calculate_mwrr` called from `get_summary()`/`get_history()`
- [[concepts/twrr-mwrr-algorithms]] — algorithm documentation
- Source: `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_2/portfolio_engine/mwrr_analysis_report.md`

## Source files

| Role | Path |
|------|------|
| ROI utilities | `backend/app/utils/roi_utils.py` |
| Portfolio service | `backend/app/services/portfolio_service.py` |
| MWRR analysis | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_2/portfolio_engine/mwrr_analysis_report.md` |

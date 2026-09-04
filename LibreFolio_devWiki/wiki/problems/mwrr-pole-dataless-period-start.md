---
title: "MWRR pole when the period starts on a data-less day"
category: problem
date: 2026-09-02
tags: [backend, roi, mwrr, xirr, fifo, portfolio]
related:
  - concepts/fifo-lot-tracking
---

# Problem: MWRR pole when the period starts on a data-less day

## Summary

Selecting a period whose start date falls on a day with no NAV data (e.g. a Sunday)
sent the cumulative MWRR chart to a pole (e.g. **+9.94%** where the truth was ≈ −1.5%).
Root cause: a deposit landing on the first real NAV day was double-counted — once inside
the first snapshot's NAV, once as a cash flow — dragging the XIRR solver to an extreme root.

## Root cause

In `portfolio_service.py` period re-basing (both the summary path and the history-series
path), when no NAV snapshot exists at/before `date_from` the code took
`period_start_nav = 0` and `period_start_date = nav_snapshots[0].date`, then kept cash
flows with `cf.date >= period_start_date`. The first snapshot's NAV is already
**post-flow** (it includes that day's deposit), so including the deposit again in the XIRR
flow list double-counted the capital. `scipy.optimize.newton` then found an extreme
annualized root (≈ +150%+) which `annualized_to_cumulative` turned into the visible pole.

The warm-start chain guard in `calculate_mwrr_series` (cap `|rate| ≤ 2`) was too loose for
short windows to catch it.

## Fix

- In both re-basing branches, flows dated on the first snapshot are now excluded when the
  period start is data-less (`>` instead of `>=`), matching the `period_start_nav > 0`
  behavior: flows embedded in a snapshot never appear again as flows.
- Reproduced and pinned with a probe: Sunday 2026-03-01 start, deposit on the first NAV
  day → before: pole; after: ≈ −0.15% cumulative, matching TWRR/ROI.

## Verification

- Probe scripts reproduced the pole and validated the fix against the two reference shapes.
- `backend/test_scripts/test_services/test_financial/` — 325 passed after the change.

## Source files

| Role | Path |
|------|------|
| Fix | `backend/app/services/portfolio_service.py` (period re-basing, two branches) |
| XIRR solver | `backend/app/utils/financial/roi_utils.py` (calculate_mwrr, calculate_mwrr_series) |
| Tests | `backend/test_scripts/test_services/test_financial/` |

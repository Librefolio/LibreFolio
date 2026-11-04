---
title: "The maturity settlement counted the final coupon twice"
category: problem
status: resolved
date: 2026-10-17
tags: [backend, scheduled-investment, events, interest, settlement, testing, workstream-j]
related:
  - problems/act-act-lost-a-day-per-year-end
  - decisions/scheduled-investment-redesign
  - features/F-034
---

# Problem: the maturity settlement counted the final coupon twice

## Symptom

A Scheduled Investment whose last period pays coupons, with no late interest, closes on its end date with two events.
The final coupon is an `INTEREST` event. Then comes a `MATURITY_SETTLEMENT`, which also contained that coupon.

- A 10 000 € deposit at 5 % over 2024 showed INTEREST 500 and MATURITY_SETTLEMENT 10 500: 500 € paid twice.
- `get_current_value()` and `get_history_value()` after maturity read the settlement, so the asset kept being valued
  at 10 500.
- The docs-writer found it (J-39) while documenting the interest home in CP-14a; it was fixed in CP-14b.

## Root Cause

`_generate_schedule_values` took the settlement from `values[last_end]`. That map holds each maturation date's value
*before* its coupon: the chart's peak, on purpose since I-bis #26. On the last day the walk pays the coupon and resets
the value to the principal, but the settlement still read the pre-coupon peak.

## Solution

The walk remembers the day of the last coupon. The settlement is the principal when the final coupon falls on the end
date, and the day's value otherwise (a write-down that leaves no gain pays no coupon).

- `values[last_end]`, the chart's last point, is unchanged.
- In the golden net, the 8 `s4_annual_settlement` settlements dropped to the principal (12 345.67), as declared before
  the code.
- Still open, for the developer: the late-interest part of J-39. That covers the base of late interest, a late
  settlement that moves with the request's end date, and late payouts that never reset.

## Lesson: a red must fail for the right reason

The red run counted 3 reds, as expected, but two of them failed on their premise, not on the settlement. The test's
coupon literal had three zeros too few: `500.00000000000000000001` (1e-20) instead of `500.00000000000000000000001`
(1e-23), although the test's own comment worked out 1e-23.

The code fix left those two tests red, and only then did the reason show. A red run must read the failing line and
message of every red, not only the count. After the repair, an in-memory run with the old settlement rule showed all
three failing on the settlement, and the current code passed them.

## Source files

| Role | Path |
|------|------|
| Implementation | `backend/app/services/asset_source_providers/scheduled_investment/plugin.py` |
| Tests (J-39 section) | `backend/test_scripts/test_services/test_synthetic_yield.py` |
| Golden net | `backend/test_scripts/fixtures/scheduled_investment/accrual_golden.json` |
| Developer docs | `mkdocs_src/docs/developer/backend/assets/provider_scheduled_investment.md` |
| Plan | `LibreFolio_developer_journal/Release_2/Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md` |

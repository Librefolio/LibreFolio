"""
ROI Financial Utilities — pure math, no I/O.

Provides TWRR, MWRR (XIRR), and Simple ROI calculations.

Cash flow sign convention (standard finance):
  - Deposits   → negative amount (money flows INTO portfolio, investor pays out)
  - Withdrawals → positive amount (money flows OUT of portfolio, investor receives)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import NamedTuple

from scipy.optimize import newton as scipy_newton


class CashFlowInput(NamedTuple):
    """External cash flow with date.

    Sign convention: negative = deposit (inflow), positive = withdrawal (outflow).
    Dividends and interest are NOT cash flows (they are internal returns).
    """

    date: date
    amount: Decimal


class NAVSnapshot(NamedTuple):
    """Portfolio NAV snapshot at a specific date."""

    date: date
    nav: Decimal


@dataclass(frozen=True)
class ROIResult:
    """Combined ROI result."""

    simple_roi: Decimal
    twrr: Decimal | None
    mwrr: Decimal | None


@dataclass(frozen=True)
class SimpleROIPoint:
    """Single Simple ROI value at a date."""

    date: date
    roi: Decimal


@dataclass(frozen=True)
class TWRRPoint:
    """Single TWRR value at a date."""

    date: date
    twrr: Decimal


@dataclass(frozen=True)
class MWRRPoint:
    """Single MWRR value at a date (None if calculation did not converge)."""

    date: date
    mwrr: Decimal | None


_PREC_PCT = Decimal("0.000001")  # 6 decimals for percentages
_PREC_AMT = Decimal("0.01")  # 2 decimals for monetary values


def annualized_to_cumulative(rate: Decimal | None, days: int) -> Decimal | None:
    """Convert annualized MWRR/XIRR to cumulative return for a given period.

    Formula: r_cum = (1 + r_ann)^(days / 365) - 1

    Returns None if rate is None, <= -1, or computation is invalid.
    """
    if rate is None:
        return None
    if rate <= Decimal("-1"):
        return None
    if days <= 0:
        return Decimal("0")
    try:
        base = float(Decimal("1") + rate)
        exponent = days / 365.0
        cumulative = base**exponent - 1.0
        if not math.isfinite(cumulative):
            return None
        return Decimal(str(cumulative)).quantize(_PREC_PCT, rounding=ROUND_HALF_UP)
    except (OverflowError, InvalidOperation, ValueError):
        return None


def calculate_simple_roi(current_nav: Decimal, total_invested: Decimal) -> Decimal:
    """ROI = (NAV - Invested) / Invested. Returns 0 if total_invested == 0."""
    if total_invested == Decimal("0"):
        return Decimal("0")
    return ((current_nav - total_invested) / total_invested).quantize(_PREC_PCT, rounding=ROUND_HALF_UP)


def calculate_simple_roi_series(
    nav_snapshots: list[NAVSnapshot],
    cash_flows: list[CashFlowInput],
) -> list[SimpleROIPoint]:
    """Cumulative Simple ROI series — one point per NAV snapshot.

    For each snapshot t, computes the cumulative net invested capital up to t:
    Net_Invested_t = max(0, -sum(CF_i for i <= t))  # deposits are < 0, withdrawals > 0.

    Then: ROI_t = (NAV_t - Net_Invested_t) / Net_Invested_t.

    Returns:
        List of SimpleROIPoint, one per snapshot.
    """
    if not nav_snapshots:
        return []

    sorted_navs = sorted(nav_snapshots, key=lambda s: s.date)
    cf_by_date: dict[date, Decimal] = {}
    for cf in cash_flows:
        cf_by_date[cf.date] = cf_by_date.get(cf.date, Decimal("0")) + cf.amount

    result: list[SimpleROIPoint] = []
    cumulative_cf = Decimal("0")

    for snap in sorted_navs:
        # Include any cash flows that happened on or before this snapshot's date
        # (Assuming we accumulate them as we walk chronologically)
        cf_today = cf_by_date.get(snap.date, Decimal("0"))
        cumulative_cf += cf_today

        # Net invested is the opposite of cumulative CF (since deposits are negative)
        # If cumulative_cf is positive, we've withdrawn more than deposited, so invested is 0.
        net_invested = -cumulative_cf if cumulative_cf < Decimal("0") else Decimal("0")

        roi = calculate_simple_roi(snap.nav, net_invested)
        result.append(SimpleROIPoint(date=snap.date, roi=roi))

    return result


def calculate_twrr(
    nav_snapshots: list[NAVSnapshot],
    cash_flows: list[CashFlowInput],
) -> TWRRPoint:
    """Time-Weighted Rate of Return (TWRR).

    Algorithm:
    1. Identify external cash flow dates.
    2. nav_snapshots MUST include a NAV for every CF date AND the final date.
    3. For each sub-period [V_start, V_end]:
       - On a CF date: HPR = (V_end_pre_cf - V_start) / V_start
         where V_end_pre_cf = V_end_snapshot - CF_amount  (undo the CF)
       - Without CF: HPR = (V_end - V_start) / V_start
    4. Compose geometrically: TWRR = Π(1 + HPR_i) - 1.

    Sub-periods where V_start == 0 are skipped (no prior investment).

    Args:
        nav_snapshots: Chronologically ordered NAV snapshots. Must include
            one snapshot per CF date and one at the end of the measurement period.
        cash_flows: External deposits/withdrawals (sign convention: deposit < 0).

    Returns:
        TWRRPoint(date=last_snapshot_date, twrr=result)

    Raises:
        ValueError: if fewer than 2 nav_snapshots are provided.
    """
    if len(nav_snapshots) < 2:
        raise ValueError("TWRR requires at least 2 NAV snapshots (start and end).")

    sorted_navs = sorted(nav_snapshots, key=lambda s: s.date)
    cf_by_date: dict[date, Decimal] = {}
    for cf in cash_flows:
        cf_by_date[cf.date] = cf_by_date.get(cf.date, Decimal("0")) + cf.amount

    compound = Decimal("1")
    for i in range(1, len(sorted_navs)):
        v_start = sorted_navs[i - 1].nav
        v_end = sorted_navs[i].nav
        snap_date = sorted_navs[i].date

        # Remove CF that arrived at snap_date to get pre-CF NAV.
        # Snapshots are POST-CF. Deposits are negative, withdrawals positive.
        # pre_CF_NAV = post_CF_NAV + cf_amount
        cf_amount = cf_by_date.get(snap_date, Decimal("0"))
        v_end_pre_cf = v_end + cf_amount

        if v_start == Decimal("0"):
            continue  # No prior investment — skip sub-period

        hpr = (v_end_pre_cf - v_start) / v_start
        compound *= Decimal("1") + hpr

    twrr = (compound - Decimal("1")).quantize(_PREC_PCT, rounding=ROUND_HALF_UP)
    return TWRRPoint(date=sorted_navs[-1].date, twrr=twrr)


def calculate_twrr_series(
    nav_snapshots: list[NAVSnapshot],
    cash_flows: list[CashFlowInput],
) -> list[TWRRPoint]:
    """Cumulative TWRR series — one point per NAV snapshot (O(N) iterative).

    At each snapshot the TWRR is the geometric product from t0 to that point.

    Returns:
        List of TWRRPoint, one per snapshot (excluding the first).
    """
    if len(nav_snapshots) < 2:
        return []

    sorted_navs = sorted(nav_snapshots, key=lambda s: s.date)
    cf_by_date: dict[date, Decimal] = {}
    for cf in cash_flows:
        cf_by_date[cf.date] = cf_by_date.get(cf.date, Decimal("0")) + cf.amount

    compound = Decimal("1")
    result: list[TWRRPoint] = []

    for i in range(1, len(sorted_navs)):
        v_start = sorted_navs[i - 1].nav
        v_end = sorted_navs[i].nav
        snap_date = sorted_navs[i].date

        cf_amount = cf_by_date.get(snap_date, Decimal("0"))
        # Snapshots are POST-CF. pre_CF_NAV = post_CF_NAV + cf_amount
        v_end_pre_cf = v_end + cf_amount

        if v_start != Decimal("0"):
            hpr = (v_end_pre_cf - v_start) / v_start
            compound *= Decimal("1") + hpr

        twrr = (compound - Decimal("1")).quantize(_PREC_PCT, rounding=ROUND_HALF_UP)
        result.append(TWRRPoint(date=snap_date, twrr=twrr))

    return result


def calculate_mwrr(
    cash_flows: list[CashFlowInput],
    initial_nav: Decimal,
    final_nav: Decimal,
    start_date: date,
    end_date: date,
) -> MWRRPoint:
    """Money-Weighted Rate of Return / XIRR.

    Solves: NPV = Σ(CF_i / (1+r)^(d_i/365)) = 0 for r using scipy.optimize.newton.

    Flow construction:
      t=0:  -initial_nav  (investor "buys" the portfolio at start)
      t=...: intermediate cash flows (sign as-is: deposit<0, withdrawal>0)
      t=T:  +final_nav    (investor "sells" the portfolio at end)

    Note: scipy is CPU-bound (no I/O) — no asyncio.to_thread needed here.
    Callers doing bulk series should wrap in asyncio.to_thread().

    Returns:
        MWRRPoint(date=end_date, mwrr=result) or MWRRPoint(mwrr=None) on failure.
    """
    # Build cash flows as (days_from_start, amount_float) list
    total_days = (end_date - start_date).days
    if total_days <= 0:
        return MWRRPoint(date=end_date, mwrr=None)

    flows: list[tuple[float, float]] = []
    final_day_cf = sum(float(cf.amount) for cf in cash_flows if (cf.date - start_date).days == total_days)
    flows.append((0.0, -float(initial_nav)))
    flows.append((float(total_days), float(final_nav) + final_day_cf))
    for cf in cash_flows:
        days = (cf.date - start_date).days
        if 0 < days < total_days:
            flows.append((float(days), float(cf.amount)))

    def npv(r: float) -> float:
        if 1.0 + r <= 0.0:
            return float("inf")
        return sum(amount / (1.0 + r) ** (d / 365.0) for d, amount in flows)

    try:
        rate = scipy_newton(npv, x0=0.1, tol=1e-8, maxiter=100)
        if not math.isfinite(rate):
            return MWRRPoint(date=end_date, mwrr=None)
        mwrr = Decimal(str(rate)).quantize(_PREC_PCT, rounding=ROUND_HALF_UP)
        return MWRRPoint(date=end_date, mwrr=mwrr)
    except (RuntimeError, ValueError, InvalidOperation):
        return MWRRPoint(date=end_date, mwrr=None)


def calculate_mwrr_series(
    nav_snapshots: list[NAVSnapshot],
    cash_flows: list[CashFlowInput],
    *,
    use_warm_start: bool = True,
) -> list[MWRRPoint]:
    """Cumulative MWRR series with optional warm-start optimization.

    Solves XIRR for each snapshot using the previous solution as x0 (initial guess).
    This makes Newton-Raphson converge in ~1-2 iterations per point instead of ~20.

    Warm-start guard: if the solver produces an extreme annualized rate (|rate| > 2),
    the warm-start resets to 0.1 for the next iteration to prevent contamination.

    When use_warm_start=False (cold-start mode), every point starts from x0=0.1.
    Slower but guaranteed no contamination from prior extreme values.

    Note: CPU-bound — callers should wrap in asyncio.to_thread() for long series.

    Returns:
        List of MWRRPoint, one per snapshot (excluding the first).
    """
    if len(nav_snapshots) < 2:
        return []

    sorted_navs = sorted(nav_snapshots, key=lambda s: s.date)
    cf_by_date: dict[date, Decimal] = {}
    for cf in cash_flows:
        cf_by_date[cf.date] = cf_by_date.get(cf.date, Decimal("0")) + cf.amount

    start_date = sorted_navs[0].date
    initial_nav = sorted_navs[0].nav

    _DEFAULT_GUESS = 0.1
    _WARM_START_CAP = 2.0  # |rate| above this resets warm-start

    result: list[MWRRPoint] = []
    prev_guess: float = _DEFAULT_GUESS

    for i in range(1, len(sorted_navs)):
        snap = sorted_navs[i]
        total_days = (snap.date - start_date).days
        if total_days <= 0:
            result.append(MWRRPoint(date=snap.date, mwrr=None))
            continue

        final_day_cf = float(cf_by_date.get(snap.date, Decimal("0")))
        flows: list[tuple[float, float]] = [
            (0.0, -float(initial_nav)),
            (float(total_days), float(snap.nav) + final_day_cf),
        ]
        for cf_date, cf_amt in cf_by_date.items():
            days = (cf_date - start_date).days
            if 0 < days < total_days:
                flows.append((float(days), float(cf_amt)))

        def npv(r: float, _flows: list[tuple[float, float]] = flows) -> float:
            if 1.0 + r <= 0.0:
                return float("inf")
            return sum(amount / (1.0 + r) ** (d / 365.0) for d, amount in _flows)

        try:
            x0 = prev_guess if use_warm_start else _DEFAULT_GUESS
            rate = scipy_newton(npv, x0=x0, tol=1e-8, maxiter=100)
            if not math.isfinite(rate):
                result.append(MWRRPoint(date=snap.date, mwrr=None))
                continue

            if use_warm_start:
                # Guard: only propagate warm-start if rate is moderate
                if abs(rate) <= _WARM_START_CAP:
                    prev_guess = rate
                else:
                    # Extreme rate — try again from default guess to find moderate root
                    rate2 = scipy_newton(npv, x0=_DEFAULT_GUESS, tol=1e-8, maxiter=100)
                    if math.isfinite(rate2) and abs(rate2) < abs(rate):
                        rate = rate2
                        if abs(rate) <= _WARM_START_CAP:
                            prev_guess = rate
                        else:
                            prev_guess = _DEFAULT_GUESS
                    else:
                        prev_guess = _DEFAULT_GUESS

            mwrr = Decimal(str(rate)).quantize(_PREC_PCT, rounding=ROUND_HALF_UP)
            result.append(MWRRPoint(date=snap.date, mwrr=mwrr))
        except (RuntimeError, ValueError, InvalidOperation):
            result.append(MWRRPoint(date=snap.date, mwrr=None))

    return result

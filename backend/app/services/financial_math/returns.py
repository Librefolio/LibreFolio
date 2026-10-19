"""
Returns: Simple ROI, TWRR, MWRR (XIRR) and annualization — pure math, no I/O.

Also: rebasing to a period's start, net holding return, G/L ratio (of one holding or a group), a change as a fraction
of its base, the timing effect (MWRR − TWRR), realized gain, price return (also as a float for a return series), the
observed annualization factor of a return series, the fixed-period changes of a price or rate (1D … 5Y, both
orientations), and the gain that recovers a drawdown (``required_recovery_return``).

Provides TWRR, MWRR (XIRR), and Simple ROI calculations.

Cash flow sign convention (standard finance):
  - Deposits   → negative amount (money flows INTO portfolio, investor pays out)
  - Withdrawals → positive amount (money flows OUT of portfolio, investor receives)
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import NamedTuple


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
class TWRRPeriodPoint:
    """Unrounded TWRR sub-period values for downstream analytics."""

    date: date
    period_return: Decimal
    wealth_index: Decimal
    cumulative_twrr: Decimal


@dataclass(frozen=True)
class MWRRPoint:
    """Single MWRR value at a date (None if calculation did not converge)."""

    date: date
    mwrr: Decimal | None


@dataclass(frozen=True)
class PeriodRebase:
    """The inputs of a period's return metrics: where the period starts, and what it sees from there.

    ``nav_snapshots`` start at the period's opening snapshot; ``cash_flows`` open with a synthetic
    deposit of the opening NAV (``-start_nav``) and follow with the flows after the opening date.
    """

    start_date: date | None
    start_nav: Decimal
    nav_snapshots: tuple[NAVSnapshot, ...]
    cash_flows: tuple[CashFlowInput, ...]


_PREC_PCT = Decimal("0.000001")  # 6 decimals for percentages
_PREC_AMT = Decimal("0.01")  # 2 decimals for monetary values

# Minimum holding window (days) below which a cumulative return is NOT annualized.
# Annualizing a sub-month return via (1+r)^(365/days) explodes for tiny windows
# (e.g. +13% over 7 days -> ~63000%), which is mathematically correct but useless
# for comparison. Below this floor we return None so the UI shows "—" instead.
_MIN_ANNUALIZATION_DAYS = 30


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


def cumulative_to_annualized(total_return: Decimal | None, days: int, min_days: int = _MIN_ANNUALIZATION_DAYS) -> Decimal | None:
    """Convert a cumulative return over a holding window to an annualized (CAGR) rate.

    Inverse of :func:`annualized_to_cumulative`.
    Formula: r_ann = (1 + r_cum)^(365 / days) - 1

    Geometric annualization (compounding), so a +2% over 6 months annualizes to
    ~+4.04%, making returns comparable across differing holding durations.

    Returns None when the input is unusable rather than raising:
    - ``total_return`` is None or <= -1 (total loss / impossible),
    - ``days`` < ``min_days`` (window too short to annualize meaningfully; the
      default floor avoids the exponential blow-up of sub-month windows),
    - the computation overflows (e.g. a large return over a very short hold).
    """
    if total_return is None:
        return None
    if total_return <= Decimal("-1"):
        return None
    if days < min_days or days <= 0:
        return None
    try:
        base = float(Decimal("1") + total_return)
        exponent = 365.0 / days
        annualized = base**exponent - 1.0
        if not math.isfinite(annualized):
            return None
        return Decimal(str(annualized)).quantize(_PREC_PCT, rounding=ROUND_HALF_UP)
    except (OverflowError, InvalidOperation, ValueError):
        return None


def rebase_to_period(nav_snapshots: Sequence[NAVSnapshot], cash_flows: Sequence[CashFlowInput], date_from: date | None) -> PeriodRebase:
    """Rebase a whole-history NAV series and its flows on the period that starts at ``date_from``.

    The period opens at the last snapshot dated on or before ``date_from``: its NAV enters as a
    synthetic deposit on its date, the snapshots start there, and only the flows strictly after
    that date follow, since a flow of the opening date is already inside the opening NAV. When
    ``date_from`` precedes every snapshot the period opens empty (NAV 0) on the first snapshot's
    date, and the flows of that date are left out for the same reason: the first snapshot is taken
    after them, and counting them again would double the deposit and drag the XIRR to a pole.

    Without ``date_from``, or without snapshots, the inputs pass through with an opening NAV of 0
    and the first snapshot's date (None without snapshots); a caller that needs a calendar date
    there supplies its own.
    """
    snapshots = tuple(nav_snapshots)
    flows = tuple(cash_flows)
    if date_from is None or not snapshots:
        return PeriodRebase(start_date=snapshots[0].date if snapshots else None, start_nav=Decimal("0"), nav_snapshots=snapshots, cash_flows=flows)
    start_index: int | None = None
    for index, snapshot in enumerate(snapshots):
        if snapshot.date <= date_from:
            start_index = index
    if start_index is None:
        start_date, start_nav, period_snapshots = snapshots[0].date, Decimal("0"), snapshots
    else:
        start_date, start_nav, period_snapshots = snapshots[start_index].date, snapshots[start_index].nav, snapshots[start_index:]
    period_flows = (CashFlowInput(date=start_date, amount=-start_nav), *(flow for flow in flows if flow.date > start_date))
    return PeriodRebase(start_date=start_date, start_nav=start_nav, nav_snapshots=period_snapshots, cash_flows=period_flows)


def net_holding_return(market_pnl: Decimal | None, income: Decimal, costs: Decimal, cost_basis: Decimal) -> Decimal | None:
    """Net return of a holding on its cost: (market P&L + income − costs) / cost basis.

    A missing market P&L (no price) counts as 0, so a holding valued at cost still shows the return
    of its coupons and dividends net of fees and taxes. None when the cost basis is 0.
    """
    if cost_basis == 0:
        return None
    market = market_pnl if market_pnl is not None else Decimal("0")
    return (market + income - costs) / cost_basis


def gain_loss_ratio(gain: Decimal | None, base: Decimal | None, *, positive_base: bool) -> Decimal | None:
    """A gain or loss as a fraction of its base: ``gain / base``, unrounded.

    None when either is missing or the base is 0, and with ``positive_base`` also when the base is
    negative: a capital at or below zero has no meaningful return. Each caller states its guard and
    keeps its own fallback for None.
    """
    if gain is None or base is None or base == 0:
        return None
    if positive_base and base < 0:
        return None
    return gain / base


def change_ratio(change: Decimal | None, base: Decimal | None) -> Decimal | None:
    """A change as a fraction of the size of its base: ``change / |base|``, unrounded.

    The sign is the change's, whatever the base's sign: a P&L that rises from −100 to −50 changed by +50 %. None when
    either is missing or the base is 0.
    """
    if change is None or base is None or base == 0:
        return None
    return change / abs(base)


def group_gain_loss(holdings: Iterable[tuple[Decimal | None, Decimal | None]]) -> tuple[Decimal | None, Decimal | None]:
    """The gain or loss of a group of holdings and its fraction of their cost: ``(Σ gain, Σ gain / Σ cost)``.

    ``holdings`` are ``(value, gain)`` pairs; a holding's cost is its value less its gain. Only the holdings whose value
    and gain are both known count, on both sides — a holding without a gain never lends its value to the base. The
    ratio follows :func:`gain_loss_ratio` (signed base, None on a zero cost); ``(None, None)`` when no holding counts.
    """
    gain_sum: Decimal | None = None
    cost_sum = Decimal("0")
    for value, gain in holdings:
        if value is None or gain is None:
            continue
        gain_sum = (gain_sum or Decimal("0")) + gain
        cost_sum += value - gain
    if gain_sum is None:
        return None, None
    return gain_sum, gain_loss_ratio(gain_sum, cost_sum, positive_base=False)


def timing_effect(mwrr_cumulative: Decimal | None, twrr: Decimal | None) -> Decimal | None:
    """What the timing of deposits and withdrawals added to the period's return: cumulative MWRR − TWRR.

    Both are fractions of the same period; None when either is missing.
    """
    if mwrr_cumulative is None or twrr is None:
        return None
    return mwrr_cumulative - twrr


def realized_gain(proceeds: Decimal | None, cost: Decimal | None) -> Decimal | None:
    """The gain or loss a disposal realizes: ``proceeds - cost``, both already in one currency.

    Decision 26: each leg is converted at its own date — the proceeds at the sale's rate, the cost at the
    purchase's — so a foreign holding's FX move between the two belongs to the realized result. None when
    either leg is unknown (no rate): the result is then unknown too, never computed from native amounts. The
    Dashboard's sales and the lots' closures both go through it; each keeps its own rule for summing them.
    """
    if proceeds is None or cost is None:
        return None
    return proceeds - cost


def price_return(start: Decimal | None, end: Decimal | None) -> Decimal | None:
    """The simple return from one price to a later one: ``end / start - 1``, unrounded.

    None when a price is missing or the starting price is 0: never a division by zero. Callers that
    show a percentage multiply by 100 themselves.
    """
    if start is None or end is None or start == 0:
        return None
    return end / start - 1


def float_price_return(start: Decimal, end: Decimal) -> float:
    """``price_return`` as a float, for the return series that the risk and signal statistics read.

    A series never carries an unavailable return: a price that is missing or 0 is the caller's error, ValueError.
    """
    change = price_return(start, end)
    if change is None:
        raise ValueError("a price return needs two prices and a non-zero start")
    return float(change)


#: The calendar days of a year the observed annualization counts: one constant for the factor of a series and for both
#: conversions between calendar days and observations (J-1).
DAYS_PER_YEAR = 365


def observations_per_year(n_observations: int, calendar_days: int) -> float:
    """The observed annualization factor of a return series: ``n_observations × DAYS_PER_YEAR / calendar_days``.

    The one home of the formula (MF-D3): ``observed_annualization`` computes it, and the risk schemas' validators check a
    contract's factor against it (``schemas/risk.py``, which may import this pure module). ValueError for a span that is
    not positive.
    """
    if calendar_days <= 0:
        raise ValueError("calendar_days must be positive")
    return n_observations * DAYS_PER_YEAR / calendar_days


def positive_annualization_factor(annualization_factor: float) -> float:
    """An annualization factor as a float, refused unless finite and positive (ValueError): zero, negative, ``inf`` and
    ``nan`` come from an empty or malformed observation calendar and would yield finite-looking figures."""
    normalized = float(annualization_factor)
    if normalized <= 0 or not math.isfinite(normalized):
        raise ValueError("annualization_factor must be finite and positive")
    return normalized


def calendar_days_to_observations(calendar_days: int, per_year: float) -> int:
    """Return how many observations a span of calendar days holds at an observed frequency.

    The inverse of observed annualization: a series observed ``per_year`` times a year holds ``calendar_days × per_year /
    DAYS_PER_YEAR`` observations over the span, and never fewer than one. So a month is 30 calendar days on every series —
    21 observations of one quoted on trading days, 30 of one quoted every day.
    """
    if isinstance(calendar_days, bool) or calendar_days <= 0:
        raise ValueError("calendar_days must be a positive integer")
    return max(1, round(calendar_days * positive_annualization_factor(per_year) / DAYS_PER_YEAR))


def observations_to_calendar_days(observations: int, per_year: float) -> int:
    """The calendar days a run of ``observations`` spans at an observed frequency: ``observations × DAYS_PER_YEAR /
    per_year``, rounded, never fewer than one — the inverse of :func:`calendar_days_to_observations` (J-1), with which
    the simulation discloses its block length in days."""
    if isinstance(observations, bool) or observations <= 0:
        raise ValueError("observations must be a positive integer")
    return max(1, round(observations * DAYS_PER_YEAR / positive_annualization_factor(per_year)))


def observed_annualization(n_observations: int, baseline_date: date | None, final_date: date | None) -> tuple[int, float | None]:
    """The calendar span of a return series and its observed annualization factor: observations × 365 / days.

    ``(0, None)`` for an empty series. A non-empty series needs both dates and a final date after the baseline;
    otherwise ValueError — callers that can meet a zero-day span decide their own fallback before calling.
    """
    if n_observations < 0:
        raise ValueError("n_observations cannot be negative")
    if n_observations == 0:
        return 0, None
    if baseline_date is None or final_date is None:
        raise ValueError("non-empty observations require baseline and final dates")
    calendar_days = (final_date - baseline_date).days
    if calendar_days <= 0:
        raise ValueError("final_date must follow baseline_date")
    return calendar_days, observations_per_year(n_observations, calendar_days)


# The fixed periods of the Assets and FX tables (D-MF6 b): key and calendar days, in display order.
FIXED_PERIODS: tuple[tuple[str, int], ...] = (
    ("1D", 1),
    ("1W", 7),
    ("1M", 30),
    ("3M", 91),
    ("6M", 182),
    ("1Y", 365),
    ("2Y", 730),
    ("3Y", 1095),
    ("5Y", 1825),
)


@dataclass(frozen=True)
class FixedPeriodChange:
    """The change of a price or rate over one fixed period, from ``as_of − days`` to ``as_of``.

    ``change_ratio`` is ``anchor / reference − 1``; ``inverse_change_ratio`` is the change of the inverted quote,
    ``reference / anchor − 1`` (an FX pair read the other way round). Both are fractions, None when either value is
    missing, the reference ≤ 0 or the anchor < 0. An anchor of exactly 0 over a positive reference is a price written
    down to nothing (a defaulted loan, a delisted share): ``change_ratio`` −1 (−100 %), and ``inverse_change_ratio``
    None, since the inverted quote has no value (X's review of X-R59: the period columns showed «—» for it, the
    whole-range Δ −100 %; both now show −100 %).
    """

    key: str
    days: int
    change_ratio: Decimal | None
    inverse_change_ratio: Decimal | None


def fixed_period_dates(as_of: date, periods: Sequence[tuple[str, int]] = FIXED_PERIODS) -> tuple[date, ...]:
    """The days a fixed-period table values: ``as_of``, then ``as_of − days`` for each period (calendar days)."""
    return (as_of, *(as_of - timedelta(days=days) for _key, days in periods))


def fixed_period_changes(values: Mapping[date, Decimal | None], as_of: date, periods: Sequence[tuple[str, int]] = FIXED_PERIODS) -> tuple[FixedPeriodChange, ...]:
    """Each fixed period's change of a series valued on ``fixed_period_dates(as_of)``.

    ``values`` maps a day to the series' value on it — the caller's valuation of that day (the last stored price on or
    before it, a rate converted at it), None or absent when the day has none. The anchor is the value on ``as_of``, each
    reference the value on ``as_of − days``. The rule of :func:`range_change`: never a number from a missing value, a
    reference ≤ 0 or a negative anchor; an anchor of 0 is −100 %, without an inverse.
    """
    anchor = values.get(as_of)
    changes = []
    for key, days in periods:
        change = range_change(values.get(as_of - timedelta(days=days)), anchor)
        changes.append(FixedPeriodChange(key=key, days=days, change_ratio=change.change_ratio, inverse_change_ratio=change.inverse_change_ratio))
    return tuple(changes)


@dataclass(frozen=True)
class RangeChange:
    """The change of a price or rate over a whole range, from its reference to its anchor (X-R59).

    The caller values the two ends: the anchor is the value on the range's last day, the reference the value on its
    first day (backward-filled), or the first value inside the range when there is none on or before it — the first and
    last points of the series the page draws. ``change_abs`` is ``anchor − reference`` and ``change_ratio``
    ``anchor / reference − 1``; the inverse fields are the same for the inverted quote (an FX pair read the other way
    round): ``1/anchor − 1/reference`` and ``reference / anchor − 1``. All None when either value is missing, the
    reference ≤ 0 or the anchor < 0. An anchor of exactly 0 over a positive reference is a price written down to nothing
    (a defaulted loan, a delisted share): ``change_abs`` −reference and ``change_ratio`` −1 (−100 %), as the Assets
    cards showed it; the inverse fields None, since the inverted quote has no value.
    """

    change_abs: Decimal | None
    change_ratio: Decimal | None
    inverse_change_abs: Decimal | None
    inverse_change_ratio: Decimal | None


def range_change(reference: Decimal | None, anchor: Decimal | None) -> RangeChange:
    """The whole-range change from ``reference`` to ``anchor`` (see :class:`RangeChange`); unrounded Decimals."""
    if reference is None or anchor is None or reference <= 0 or anchor < 0:
        return RangeChange(change_abs=None, change_ratio=None, inverse_change_abs=None, inverse_change_ratio=None)
    if anchor == 0:
        return RangeChange(change_abs=-reference, change_ratio=Decimal(-1), inverse_change_abs=None, inverse_change_ratio=None)
    return RangeChange(
        change_abs=anchor - reference,
        change_ratio=price_return(reference, anchor),
        inverse_change_abs=1 / anchor - 1 / reference,
        inverse_change_ratio=price_return(anchor, reference),
    )


def required_recovery_return(drawdown: float) -> float | None:
    """The gain that brings a value back to its peak after a peak-relative drawdown: ``-d / (1 + d)``.

    ``drawdown`` is a ratio at or below zero (``-0.2`` = 20 % below the peak), so a fall of 20 % needs a
    gain of 25 %. The form ``-d / (1 + d)`` keeps small values precise, where ``1 / (1 + d) - 1`` loses
    digits. 0 when nothing is lost (never a negative zero); None for a total loss (``d <= -1``), which no
    finite gain recovers. A positive or non-finite drawdown is a caller's error: ValueError.
    """
    value = float(drawdown)
    if not math.isfinite(value) or value > 0:
        raise ValueError("drawdown must be a finite ratio at or below zero")
    if value <= -1.0:
        return None
    if value == 0:
        return 0.0
    return -value / (1.0 + value)


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

    period_series = calculate_twrr_period_series(nav_snapshots, cash_flows)
    final = period_series[-1]
    twrr = final.cumulative_twrr.quantize(_PREC_PCT, rounding=ROUND_HALF_UP)
    return TWRRPoint(date=final.date, twrr=twrr)


def calculate_twrr_period_series(
    nav_snapshots: list[NAVSnapshot],
    cash_flows: list[CashFlowInput],
) -> list[TWRRPeriodPoint]:
    """Return exact sub-period HPR and unrounded cumulative TWRR values."""
    if len(nav_snapshots) < 2:
        return []

    sorted_navs = sorted(nav_snapshots, key=lambda snapshot: snapshot.date)
    cf_by_date: dict[date, Decimal] = {}
    for cash_flow in cash_flows:
        cf_by_date[cash_flow.date] = cf_by_date.get(cash_flow.date, Decimal("0")) + cash_flow.amount

    compound = Decimal("1")
    result: list[TWRRPeriodPoint] = []
    for previous, current in zip(
        sorted_navs,
        sorted_navs[1:],
        strict=False,
    ):
        cash_flow = cf_by_date.get(current.date, Decimal("0"))
        value_before_cash_flow = current.nav + cash_flow
        period_return = Decimal("0") if previous.nav == Decimal("0") else (value_before_cash_flow - previous.nav) / previous.nav
        compound *= Decimal("1") + period_return
        result.append(
            TWRRPeriodPoint(
                date=current.date,
                period_return=period_return,
                wealth_index=compound,
                cumulative_twrr=compound - Decimal("1"),
            )
        )
    return result


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

    return [
        TWRRPoint(
            date=point.date,
            twrr=point.cumulative_twrr.quantize(_PREC_PCT, rounding=ROUND_HALF_UP),
        )
        for point in calculate_twrr_period_series(nav_snapshots, cash_flows)
    ]


# XIRR: a rate is returned only when it is a root of the flows' NPV (|NPV| within this share of the
# flows' size). The bracketing fallback searches 1 + r on a geometric grid, 50 points a decade: from a
# near-total annualized loss (a large loss over a few days annualizes to within 1e-12 of −100%) to a
# gain of 10 000 times a year.
_XIRR_ROOT_TOLERANCE = 1e-7
_XIRR_GRID = tuple(10.0 ** (exponent / 50.0) for exponent in range(-600, 201))


def _xirr_npv(flows: Sequence[tuple[float, float]], rate: float) -> float:
    """NPV of ``(years, amount)`` flows at ``rate``; OverflowError where it cannot be evaluated (1 + r ≤ 0, overflow)."""
    base = 1.0 + float(rate)
    if base <= 0.0:
        raise OverflowError("1 + rate <= 0")
    return sum(amount * base ** (-years) for years, amount in flows)


def _xirr_npv_slope(flows: Sequence[tuple[float, float]], rate: float) -> float:
    """Derivative of :func:`_xirr_npv` with respect to the rate."""
    base = 1.0 + float(rate)
    if base <= 0.0:
        raise OverflowError("1 + rate <= 0")
    return sum(-years * amount * base ** (-years - 1.0) for years, amount in flows)


def _is_xirr_root(flows: Sequence[tuple[float, float]], rate: float, scale: float) -> bool:
    try:
        return math.isfinite(rate) and abs(_xirr_npv(flows, rate)) <= _XIRR_ROOT_TOLERANCE * scale
    except (OverflowError, ZeroDivisionError):
        return False


def _solve_xirr(flows: Sequence[tuple[float, float]], x0: float) -> float | None:
    """A verified root of the NPV of ``(years, amount)`` flows, or None when there is none.

    Newton's method with the analytic slope starts from ``x0``, and its answer is kept only when the NPV
    really vanishes there. Otherwise every interval of the grid where the NPV changes sign is solved by
    bracketing (Brent), and the root nearest ``x0`` is returned. A rate that does not solve the equation
    is never returned: the bare secant method used before could stop, after an overflow, on one of its
    own starting points and give it back as the rate.
    """
    # Imported here: the module's other functions are plain arithmetic, and a schema importing one of them (MF-D3) does
    # not load scipy for it.
    from scipy.optimize import brentq  # noqa: PLC0415
    from scipy.optimize import newton as scipy_newton  # noqa: PLC0415

    scale = sum(abs(amount) for _, amount in flows) or 1.0
    try:
        rate = float(scipy_newton(lambda r: _xirr_npv(flows, r), x0, fprime=lambda r: _xirr_npv_slope(flows, r), tol=1e-12, maxiter=100))
        if _is_xirr_root(flows, rate, scale):
            return rate
    except (OverflowError, ZeroDivisionError, RuntimeError, ValueError):
        pass
    roots: list[float] = []
    previous_rate: float | None = None
    previous_npv: float | None = None
    for base in _XIRR_GRID:
        rate = base - 1.0
        try:
            npv = _xirr_npv(flows, rate)
        except (OverflowError, ZeroDivisionError):
            previous_rate = previous_npv = None
            continue
        if not math.isfinite(npv):
            previous_rate = previous_npv = None
            continue
        if npv == 0.0:
            roots.append(rate)
        elif previous_rate is not None and previous_npv is not None and previous_npv * npv < 0.0:
            try:
                roots.append(brentq(lambda r: _xirr_npv(flows, r), previous_rate, rate, xtol=1e-14, maxiter=200))
            except (OverflowError, ZeroDivisionError, RuntimeError, ValueError):
                pass
        previous_rate, previous_npv = rate, npv
    verified = [root for root in roots if _is_xirr_root(flows, root, scale)]
    return min(verified, key=lambda root: abs(root - x0)) if verified else None


def _rate_decimal(rate: float) -> Decimal:
    """A solved rate at 6 decimals; a zero is written without a sign.

    A rate equal to zero can come out of the solver a hair below it (about −1e-16), and would print as
    «-0.000000»: the rate is zero, so it carries no sign.
    """
    value = Decimal(str(rate)).quantize(_PREC_PCT, rounding=ROUND_HALF_UP)
    return value.copy_abs() if value.is_zero() else value


# The one starting guess of the MWRR solve, for the single rate and for every point of a series: the root nearest it
# is the one returned, so the same flows always give the same rate (a series point equals the single solve ending there).
_MWRR_GUESS = 0.1


def _flows_by_date(cash_flows: Iterable[CashFlowInput]) -> dict[date, Decimal]:
    """The external flows summed per date, in Decimal, in first-seen order."""
    by_date: dict[date, Decimal] = {}
    for cf in cash_flows:
        by_date[cf.date] = by_date.get(cf.date, Decimal("0")) + cf.amount
    return by_date


def _mwrr_point(flows_by_date: Mapping[date, Decimal], initial_nav: Decimal, final_nav: Decimal, start_date: date, end_date: date) -> MWRRPoint:
    """The one MWRR solve, shared by :func:`calculate_mwrr` and every point of :func:`calculate_mwrr_series`.

    Flows, in years from the start:
      t=0:   -initial_nav  (the investor "buys" the portfolio at the start; a flow of the start date is inside it)
      t=...: the flows strictly between start and end, summed per date (deposit < 0, withdrawal > 0)
      t=T:   +final_nav plus the flows of the end date (the investor "sells" the portfolio at the end)
    """
    total_days = (end_date - start_date).days
    if total_days <= 0:
        return MWRRPoint(date=end_date, mwrr=None)
    year_flows = [(0.0, -float(initial_nav)), (total_days / 365.0, float(final_nav + flows_by_date.get(end_date, Decimal("0"))))]
    year_flows += [((flow_date - start_date).days / 365.0, float(amount)) for flow_date, amount in flows_by_date.items() if 0 < (flow_date - start_date).days < total_days]
    rate = _solve_xirr(year_flows, _MWRR_GUESS)
    if rate is None:
        return MWRRPoint(date=end_date, mwrr=None)
    try:
        return MWRRPoint(date=end_date, mwrr=_rate_decimal(rate))
    except InvalidOperation:
        return MWRRPoint(date=end_date, mwrr=None)


def calculate_mwrr(
    cash_flows: list[CashFlowInput],
    initial_nav: Decimal,
    final_nav: Decimal,
    start_date: date,
    end_date: date,
) -> MWRRPoint:
    """Money-Weighted Rate of Return / XIRR between ``start_date`` and ``end_date``.

    Solves NPV = Σ(CF_i / (1+r)^(d_i/365)) = 0 for r with :func:`_solve_xirr`, which returns only a verified root
    (``mwrr`` None when there is none); the flows are built by :func:`_mwrr_point`.

    Note: scipy is CPU-bound (no I/O) — no asyncio.to_thread needed here.
    Callers doing bulk series should wrap in asyncio.to_thread().
    """
    return _mwrr_point(_flows_by_date(cash_flows), initial_nav, final_nav, start_date, end_date)


def calculate_mwrr_series(nav_snapshots: list[NAVSnapshot], cash_flows: list[CashFlowInput]) -> list[MWRRPoint]:
    """Cumulative MWRR at every snapshot after the first, from the first snapshot (its date and NAV).

    Every point is the single solve ending on its snapshot, with the same starting guess: point ``i`` equals
    :func:`calculate_mwrr` on the same flows from the first snapshot to snapshot ``i``.

    Note: CPU-bound — callers should wrap in asyncio.to_thread() for long series.
    """
    if len(nav_snapshots) < 2:
        return []
    sorted_navs = sorted(nav_snapshots, key=lambda snapshot: snapshot.date)
    flows_by_date = _flows_by_date(cash_flows)
    start = sorted_navs[0]
    return [_mwrr_point(flows_by_date, start.nav, snapshot.nav, start.date, snapshot.date) for snapshot in sorted_navs[1:]]


def period_mwrr(nav_snapshots: Sequence[NAVSnapshot], cash_flows: Sequence[CashFlowInput], end_date: date, end_nav: Decimal) -> MWRRPoint:
    """The MWRR of a period as the Dashboard shows it: from the first snapshot to ``end_date``.

    A rate exists only for a period with snapshots and flows, a positive value at the end, and capital in it: the net
    invested must be positive. It is the capital the solve itself sees — the first snapshot's value (what the investor
    "buys" at the start, a deposit of that day included) plus the flows after it up to ``end_date`` — so a period that
    opens before the portfolio's first day, with its deposit inside the opening value, still has its capital.
    Otherwise ``mwrr`` is None — the card shows «—», and so does :func:`period_mwrr_series` on that day.
    """
    snapshots = sorted(nav_snapshots, key=lambda snapshot: snapshot.date)
    if not snapshots or not cash_flows or end_nav <= 0 or _net_invested(snapshots[0], cash_flows, end_date) <= 0:
        return MWRRPoint(date=end_date, mwrr=None)
    return calculate_mwrr(list(cash_flows), snapshots[0].nav, end_nav, snapshots[0].date, end_date)


def _net_invested(start: NAVSnapshot, cash_flows: Iterable[CashFlowInput], end_date: date) -> Decimal:
    """The capital an MWRR solve from ``start`` to ``end_date`` sees: the opening value plus the flows after it."""
    return start.nav - sum((cf.amount for cf in cash_flows if start.date < cf.date <= end_date), Decimal("0"))


def period_mwrr_series(nav_snapshots: Sequence[NAVSnapshot], cash_flows: Sequence[CashFlowInput]) -> list[MWRRPoint]:
    """The Dashboard's MWRR line: at every snapshot after the first, :func:`period_mwrr` of the period ending there.

    A point is None where the card of that period would be: a value ≤ 0, or no net invested capital up to that day
    (see :func:`period_mwrr`). The last point is the card of the whole period.
    """
    snapshots = sorted(nav_snapshots, key=lambda snapshot: snapshot.date)
    if len(snapshots) < 2 or not cash_flows:
        return []
    flows_by_date = _flows_by_date(cash_flows)
    dated_flows = sorted(flows_by_date.items())
    start = snapshots[0]
    points: list[MWRRPoint] = []
    net_invested = start.nav
    next_flow = 0
    while next_flow < len(dated_flows) and dated_flows[next_flow][0] <= start.date:
        next_flow += 1
    for snapshot in snapshots[1:]:
        while next_flow < len(dated_flows) and dated_flows[next_flow][0] <= snapshot.date:
            net_invested -= dated_flows[next_flow][1]
            next_flow += 1
        if snapshot.nav <= 0 or net_invested <= 0:
            points.append(MWRRPoint(date=snapshot.date, mwrr=None))
        else:
            points.append(_mwrr_point(flows_by_date, start.nav, snapshot.nav, start.date, snapshot.date))
    return points

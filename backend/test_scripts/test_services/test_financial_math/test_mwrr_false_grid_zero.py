"""
MF5-4 · MF-P1c: an MWRR that opens at zero on a very long period must not return a grid point
where the NPV is 0.0 only because every one of its terms underflowed.

Module under test: ``backend/app/services/financial_math/returns.py`` — ``_solve_xirr``,
``_bracketed_xirr``, ``_bracketed_xirr_at`` and, through them, ``calculate_mwrr``,
``period_mwrr`` and ``period_mwrr_series`` (the Dashboard's MWRR card and line).

The defect. The bracketing scan (``_bracketed_xirr``) walks 1 + r on ``_XIRR_GRID`` (1e-12 to 1e4)
and keeps every grid point whose NPV is exactly 0.0 as a root; ``_bracketed_xirr_at`` (the
warm-started series' one-interval scan) has the same branch. When the opening value is 0.0 (the
t=0 flow is ``-float(Decimal(0))``) and every other flow is more than ~78 years after the start,
each term ``amount * (1 + r) ** (-years)`` underflows to exactly 0.0 at the top of the grid: the
NPV is 0.0 there although nothing changes sign, the zero passes ``_is_xirr_root`` trivially
(|0.0| ≤ tolerance), and the grid point nearest the guess 0.1 comes back as the rate. Newton fails
on these flows, so the scan's false zero is the answer of ``_solve_xirr`` and of the card.

Concrete flows (found by experiment on HEAD 259a30076; years, amounts; false rate returned):

* ``[(0, -0.0), (85, -1000), (85.01, +1200)]`` → 6605.934480…; true root 1.2**100 − 1 ≈ 8.3e7,
  outside the grid.
* ``[(0, -0.0), (100, -1000), (100.01, +1200)]`` → 1736.800828…; true root ≈ 8.3e7.
* the 1900-typo portfolio: ``[(0, -0.0), (125.99, -1000), (126, +1200)]`` → 379.189396…;
  true root 1.2**100 − 1 ≈ 8.3e7.
* a true root ON the grid hidden behind the underflow: ``[(0, -0.0), (90, -1000),
  (90 + 4/365, +1100)]`` → 3980.071705…; true root 1.1**91.25 − 1 ≈ 5957, but above ~3981 every
  term underflows, so no sign change is observable and the solver cannot prove it.

The cure (contract): a grid point whose NPV is exactly 0.0 is a root only when the NPV changes sign
around it (``_changes_sign_at``), in both ``_bracketed_xirr`` and ``_bracketed_xirr_at``. Nothing
else changes: a genuine exact zero still counts (``[(0, -100), (T, +100)]`` → 0), Newton's answers
and sign-change roots are untouched.

Tests:

1. ``TestPrecondition`` (green before and after): on each flow set the first grid point with an
   exactly-zero NPV is an underflow zero — NPV 0.0, ``_changes_sign_at`` false, and no sign change
   anywhere on the grid by an independent scan (``math.fsum``).
2. ``TestPrivateSolvers`` (RED on HEAD): ``_solve_xirr``, ``_bracketed_xirr`` and
   ``_bracketed_xirr_at`` at that grid point return None; HEAD returns the grid point.
3. ``TestPublicMwrr`` (RED on HEAD): ``calculate_mwrr`` / ``period_mwrr`` on dated snapshots and
   flows of such a period give ``mwrr is None``; every point of ``period_mwrr_series`` is None or
   a root proved by an independent check (NPV changing sign across ± one quantum, both sides
   nonzero — an underflow zero has 0.0 on both sides).
4. ``TestUnchanged`` (green before and after): the genuine exact zero for T = 1, 10, 100 years;
   a 100-year portfolio that does not open at zero; a one-year period.

Observed while writing, outside this lot (not tested here): a snapshot on the very day of the only
deposit of a zero-opening period makes all flows 0 (the deposit joins the final value), the NPV is
identically 0 and Newton returns the guess 0.1 itself — the series point reads 0.100000. The
series below therefore has no snapshot on the deposit date.

Pure: no database, no server, no network.
"""

from __future__ import annotations

import math
import sys
from datetime import date, timedelta
from decimal import Decimal

import pytest

from backend.app.services.financial_math import returns
from backend.app.services.financial_math.returns import CashFlowInput, NAVSnapshot, calculate_mwrr, period_mwrr, period_mwrr_series

# The precision of a returned rate (6 decimals).
QUANTUM = 1e-6

Flows = list[tuple[float, float]]


def _zero_opening(deposit_years: float, end_years: float, deposit: float, final: float) -> Flows:
    """``(years, amount)`` flows as ``_mwrr_solve`` builds them for a period opening at NAV 0."""
    return [(0.0, -float(Decimal("0"))), (deposit_years, -deposit), (end_years, final)]


# The flows that reproduce the false zero on HEAD (see the module docstring).
FALSE_ZERO_FLOWS: dict[str, Flows] = {
    "85y-1day-ish": _zero_opening(85.0, 85.01, 1000.0, 1200.0),
    "100y": _zero_opening(100.0, 100.01, 1000.0, 1200.0),
    "1900-typo-126y": _zero_opening(125.99, 126.0, 1000.0, 1200.0),
    "90y-root-hidden": _zero_opening(90.0, 90.0 + 4.0 / 365.0, 1000.0, 1100.0),
}


def _npv(flows: Flows, rate: float) -> float:
    """An independent NPV: each term discounted at ``rate``, summed with ``math.fsum``; NaN where a term
    overflows (low on the grid, (1 + r) ** (-years) is too large for a float)."""
    base = 1.0 + rate
    try:
        return math.fsum(amount * base ** (-years) for years, amount in flows)
    except (OverflowError, ValueError):  # a term too large for a float, or +inf and -inf terms
        return math.nan


def _readable(npv: float) -> bool:
    """Whether an NPV's sign can be trusted: finite and at least the smallest normal float. Below it the
    terms are subnormal, their rounding is coarse and the sum's sign is noise (measured: the 1900-typo
    flows read −3.5e-321 one grid point below their exact zero, with no root anywhere near)."""
    return math.isfinite(npv) and abs(npv) >= sys.float_info.min


def _first_exact_zero_grid_rate(flows: Flows) -> float:
    """The lowest grid rate where the NPV is exactly 0.0 — the point HEAD returns as a root."""
    for base in returns._XIRR_GRID:
        rate = base - 1.0
        if _npv(flows, rate) == 0.0:
            return rate
    raise AssertionError("no grid point with an exactly-zero NPV: the flows no longer reproduce the underflow")


def _grid_has_sign_change(flows: Flows) -> bool:
    """Whether two adjacent grid points have readable NPVs of opposite signs (an observable root)."""
    previous = None
    for base in returns._XIRR_GRID:
        current = _npv(flows, base - 1.0)
        if not _readable(current):
            previous = None
            continue
        if previous is not None and (previous < 0.0) != (current < 0.0):
            return True
        previous = current
    return False


def _proved_root(flows: Flows, rate: float) -> bool:
    """Independent check of a returned (6-decimal) rate: the NPV changes sign across ± one quantum,
    both sides readable (an underflow zero is 0.0 on both sides), and the NPV at the rate is no larger
    than on either side."""
    below, at, above = _npv(flows, rate - QUANTUM), _npv(flows, rate), _npv(flows, rate + QUANTUM)
    if not (_readable(below) and _readable(above) and math.isfinite(at)):
        return False
    return (below < 0.0) != (above < 0.0) and abs(at) <= max(abs(below), abs(above))


def _dated_flows(start: date, nav_snapshots: list[NAVSnapshot], cash_flows: list[CashFlowInput], end: NAVSnapshot) -> Flows:
    """The flows of the period start → ``end`` rebuilt from the dates (deposit < 0, end-date flows join the final value)."""
    total = (end.date - start).days
    flows: Flows = [(0.0, -float(nav_snapshots[0].nav))]
    end_amount = end.nav + sum((cf.amount for cf in cash_flows if cf.date == end.date), Decimal("0"))
    flows.append((total / 365.0, float(end_amount)))
    flows += [((cf.date - start).days / 365.0, float(cf.amount)) for cf in cash_flows if 0 < (cf.date - start).days < total]
    return flows


@pytest.mark.parametrize("name", sorted(FALSE_ZERO_FLOWS))
class TestPrecondition:
    """Green before and after the cure: the flows reproduce an underflow zero and no observable root."""

    def test_first_exact_zero_is_an_underflow_zero(self, name: str) -> None:
        flows = FALSE_ZERO_FLOWS[name]
        rate = _first_exact_zero_grid_rate(flows)
        assert returns._xirr_npv(flows, rate) == 0.0
        assert not returns._changes_sign_at(flows, rate)
        assert not _grid_has_sign_change(flows), "the grid shows a true sign change: the case no longer isolates the underflow zero"


@pytest.mark.parametrize("name", sorted(FALSE_ZERO_FLOWS))
class TestPrivateSolvers:
    """RED on HEAD: the solvers return the underflow grid point as a root."""

    def test_solve_xirr_returns_none(self, name: str) -> None:
        flows = FALSE_ZERO_FLOWS[name]
        rate = returns._solve_xirr(flows, 0.1)
        assert rate is None, f"returned {rate!r}, the grid point {_first_exact_zero_grid_rate(flows)!r} where every NPV term underflowed"

    def test_bracketed_xirr_returns_none(self, name: str) -> None:
        flows = FALSE_ZERO_FLOWS[name]
        rate = returns._bracketed_xirr(flows, 0.1, returns._xirr_scale(flows))
        assert rate is None, f"returned the underflow grid point {rate!r}"

    def test_bracketed_xirr_at_returns_none(self, name: str) -> None:
        flows = FALSE_ZERO_FLOWS[name]
        grid_rate = _first_exact_zero_grid_rate(flows)
        rate = returns._bracketed_xirr_at(flows, grid_rate, returns._xirr_scale(flows))
        assert rate is None, f"returned the underflow grid point {rate!r}"


# Dated periods: a portfolio whose first snapshot is NAV 0 decades before its only deposit.
START_1900 = date(1900, 1, 1)
START_1930 = date(1930, 1, 1)


class TestPublicMwrr:
    """RED on HEAD: the card and the line show a rate the flows do not have."""

    @pytest.mark.parametrize(
        ("start", "deposit_day", "end_day", "end_nav"),
        [
            (START_1900, date(2025, 12, 29), date(2026, 1, 1), Decimal("1100")),  # 1900 typo, ~126 years
            (START_1930, date(2020, 1, 1), date(2020, 1, 5), Decimal("1100")),  # ~90 years, true root ≈ 5957 hidden
            (date(1925, 6, 1), date(2015, 6, 1), date(2015, 6, 4), Decimal("1200")),  # ~90 years, root off the grid
        ],
    )
    def test_card_has_no_rate(self, start: date, deposit_day: date, end_day: date, end_nav: Decimal) -> None:
        snapshots = [NAVSnapshot(start, Decimal("0")), NAVSnapshot(deposit_day + timedelta(days=1), Decimal("1000"))]
        cash_flows = [CashFlowInput(deposit_day, Decimal("-1000"))]
        flows = _dated_flows(start, snapshots, cash_flows, NAVSnapshot(end_day, end_nav))
        # The precondition on these dated flows: an underflow zero on the grid, no observable sign change.
        rate = _first_exact_zero_grid_rate(flows)
        assert not returns._changes_sign_at(flows, rate)
        assert not _grid_has_sign_change(flows)

        card = period_mwrr(snapshots, cash_flows, end_day, end_nav)
        assert card.date == end_day
        assert card.mwrr is None, f"period_mwrr shows {card.mwrr}, a grid point where every NPV term underflowed"
        direct = calculate_mwrr(cash_flows, Decimal("0"), end_nav, start, end_day)
        assert direct.mwrr is None, f"calculate_mwrr returns {direct.mwrr}"

    def test_series_has_no_false_point(self) -> None:
        cash_flows = [CashFlowInput(date(2025, 12, 29), Decimal("-1000"))]
        snapshots = [
            NAVSnapshot(START_1900, Decimal("0")),
            NAVSnapshot(date(2025, 12, 30), Decimal("1000")),  # flat: the genuine exact zero, rate 0
            NAVSnapshot(date(2025, 12, 31), Decimal("1050")),
            NAVSnapshot(date(2026, 1, 1), Decimal("1100")),
        ]
        points = period_mwrr_series(snapshots, cash_flows)
        assert [point.date for point in points] == [snapshot.date for snapshot in snapshots[1:]]
        false_points = []
        for point, snapshot in zip(points, snapshots[1:], strict=True):
            if point.mwrr is None:
                continue
            flows = _dated_flows(START_1900, snapshots, cash_flows, snapshot)
            if not _proved_root(flows, float(point.mwrr)):
                false_points.append((point.date.isoformat(), str(point.mwrr)))
        assert not false_points, f"series points that are not roots (underflow grid zeros): {false_points}"
        # The flat day keeps its genuine rate of exactly 0 (an exact zero with a real sign change).
        assert points[0].mwrr == Decimal("0.000000")
        # The last point is the card.
        assert points[-1] == period_mwrr(snapshots, cash_flows, snapshots[-1].date, snapshots[-1].nav)


class TestUnchanged:
    """Green before and after the cure: genuine exact zeros, long non-zero openings, short periods."""

    @pytest.mark.parametrize("years", [1.0, 10.0, 100.0])
    def test_genuine_exact_zero_via_solve(self, years: float) -> None:
        flows = [(0.0, -100.0), (years, 100.0)]
        rate = returns._solve_xirr(flows, 0.1)
        assert rate is not None
        assert abs(rate) < 1e-12

    @pytest.mark.parametrize("years", [1.0, 10.0, 100.0])
    def test_genuine_exact_zero_via_bracketing(self, years: float) -> None:
        flows = [(0.0, -100.0), (years, 100.0)]
        scale = returns._xirr_scale(flows)
        assert returns._bracketed_xirr(flows, 0.1, scale) == 0.0
        assert returns._bracketed_xirr_at(flows, 0.0, scale) == 0.0

    def test_long_portfolio_not_opening_at_zero(self) -> None:
        flows = [(0.0, -1000.0), (100.0, 2000.0)]
        rate = returns._solve_xirr(flows, 0.1)
        assert rate == pytest.approx(2.0 ** (1.0 / 100.0) - 1.0, rel=1e-9)
        start, end = date(1925, 1, 1), date(2025, 1, 1)
        days = (end - start).days
        point = calculate_mwrr([], Decimal("1000"), Decimal("2000"), start, end)
        assert point.mwrr is not None
        assert float(point.mwrr) == pytest.approx(2.0 ** (365.0 / days) - 1.0, abs=QUANTUM)

    def test_short_period(self) -> None:
        start = date(2024, 1, 1)
        point = calculate_mwrr([], Decimal("1000"), Decimal("1100"), start, start + timedelta(days=365))
        assert point.mwrr == Decimal("0.100000")
        card = period_mwrr(
            [NAVSnapshot(start, Decimal("0"))],
            [CashFlowInput(date(2024, 1, 2), Decimal("-1000"))],
            date(2025, 1, 1),
            Decimal("1100"),
        )
        assert card.mwrr is not None
        assert _proved_root(_zero_opening(1.0 / 365.0, 366.0 / 365.0, 1000.0, 1100.0), float(card.mwrr))

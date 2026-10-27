"""MF-P1d — an MWRR solve whose flows are all zero has no rate, never the solver's starting point.

The bug (HEAD 270e85a55): a period that opens at NAV 0 and whose only flow is a deposit on day D builds, for the point
ending on D, the XIRR flows ``(0, −0.0)`` and ``(T, NAV_D + flow_D) = (T, 1000 − 1000 = 0.0)``: every amount is zero, so
the NPV is 0 at every rate. ``_newton_xirr`` evaluates f(x0) = 0 at its start, scipy returns x0, and ``_is_xirr_root``
accepts it (|0| ≤ tolerance): the point carries ``_MWRR_GUESS`` = 0.1, the Dashboard shows «10 %» on the deposit day.
The «capital ≤ 0 → None» rule of ``period_mwrr`` / ``period_mwrr_series`` does not catch it: the capital there is
0 + 1000 > 0.

The cure approved by the developer (24/10/2026): when every flow of the period is zero, no rate — ``mwrr`` None (the
Dashboard «—»), and ``_solve_xirr(flows, x0)`` None. Nothing else changes: every other point stays bit-for-bit as
today, and a series' warm start goes on from the next solvable point.

RED on HEAD 270e85a55 (each gives 0.100000, or 0.1 as a float, today):
- TestDepositDayOfAPeriodOpeningAtZero::test_period_series_point_on_the_deposit_day_has_no_rate (1/3: 0.100000)
- TestDepositDayOfAPeriodOpeningAtZero::test_calculate_series_has_no_rate_while_every_flow_is_zero (1/2 and 1/3: 0.100000)
- TestDepositDayOfAPeriodOpeningAtZero::test_period_mwrr_ending_on_the_deposit_day_has_no_rate (0.100000)
- TestAccountEmptiedAndRefunded::test_redeposit_day_has_no_rate (0.100000)
- TestDirectSolve::test_calculate_mwrr_with_the_deposit_on_the_end_date_has_no_rate (0.100000)
- TestDirectSolve::test_solve_xirr_with_every_amount_zero_has_no_root (three flow sets, 0.1 each)

GREEN on HEAD, guards the cure must keep green (values pinned from HEAD 270e85a55):
- the points around the deposit day (1/2 None in the period series, 2/3 = 0.440251 and its closed form);
- the days after the re-deposit: a verified root (closed form + an NPV sign change checked here, not by the product's
  predicate), first and last pinned exactly;
- a genuine zero rate (1000 → 1000, no flows) is 0, not None; an ordinary series point by point; the «capital ≤ 0»
  rule still gives None where it did.

Isolation: PURE — no database, no server, no network; plain function calls on in-memory inputs.

Runs in ``./dev.py test services`` with the whole ``test_financial_math/`` directory.

Reference: backend/app/services/financial_math/returns.py (_mwrr_solve, _solve_xirr, _newton_xirr, period_mwrr,
period_mwrr_series, calculate_mwrr, calculate_mwrr_series).
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from decimal import Decimal

import pytest

from backend.app.services.financial_math.returns import (
    CashFlowInput,
    MWRRPoint,
    NAVSnapshot,
    _solve_xirr,
    calculate_mwrr,
    calculate_mwrr_series,
    period_mwrr,
    period_mwrr_series,
)

# A rate solved to 6 decimals against its closed form computed in float.
CLOSED_FORM_TOLERANCE = 1e-5

# =============================================================================
# The deposit-day case (the lot's own example): the period opens at 0 on 1/1, a deposit of 1000 on 1/3 (investor sign:
# −1000), worth 1001 the next day.
# =============================================================================

OPEN_DAY = date(2024, 1, 1)
EMPTY_DAY = date(2024, 2, 1)
DEPOSIT_DAY = date(2024, 3, 1)
NEXT_DAY = date(2024, 3, 2)
DEPOSIT = Decimal("1000")

DEPOSIT_DAY_SNAPSHOTS = [
    NAVSnapshot(date=OPEN_DAY, nav=Decimal("0")),
    NAVSnapshot(date=EMPTY_DAY, nav=Decimal("0")),
    NAVSnapshot(date=DEPOSIT_DAY, nav=DEPOSIT),
    NAVSnapshot(date=NEXT_DAY, nav=Decimal("1001")),
]
DEPOSIT_DAY_FLOWS = [CashFlowInput(date=DEPOSIT_DAY, amount=-DEPOSIT)]

# =============================================================================
# The account emptied and refunded: 5 000 deposited before the window (3 000 + 2 000), withdrawn entirely on 20/4, the
# window opens on 1/5 at the emptied state (NAV 0), a re-deposit of 1 000 on 11/5, then the value grows 1.5 a day.
# =============================================================================

WINDOW_OPEN = date(2024, 5, 1)
REDEPOSIT_DAY = date(2024, 5, 11)
WINDOW_DAYS = 21
PRE_WINDOW_FLOWS = [
    CashFlowInput(date=date(2024, 1, 10), amount=Decimal("-3000")),
    CashFlowInput(date=date(2024, 2, 10), amount=Decimal("-2000")),
    CashFlowInput(date=date(2024, 4, 20), amount=Decimal("5000")),
]


def _emptied_nav(day: date) -> Decimal:
    if day < REDEPOSIT_DAY:
        return Decimal("0")
    return DEPOSIT + Decimal("1.5") * (day - REDEPOSIT_DAY).days


EMPTIED_SNAPSHOTS = [NAVSnapshot(date=day, nav=_emptied_nav(day)) for day in (WINDOW_OPEN + timedelta(days=offset) for offset in range(WINDOW_DAYS))]
EMPTIED_FLOWS = [*PRE_WINDOW_FLOWS, CashFlowInput(date=REDEPOSIT_DAY, amount=-DEPOSIT)]

# =============================================================================
# Guards: an ordinary series, and a period whose capital goes ≤ 0.
# =============================================================================

ORDINARY_SNAPSHOTS = [
    NAVSnapshot(date=date(2024, 1, 1), nav=Decimal("1000")),
    NAVSnapshot(date=date(2024, 2, 1), nav=Decimal("1100")),
    NAVSnapshot(date=date(2024, 3, 1), nav=Decimal("1600")),
    NAVSnapshot(date=date(2024, 4, 1), nav=Decimal("1550")),
    NAVSnapshot(date=date(2024, 6, 1), nav=Decimal("1700")),
]
# The rebased convention: the opening value as a deposit on the opening date, then a top-up and a withdrawal.
ORDINARY_FLOWS = [
    CashFlowInput(date=date(2024, 1, 1), amount=Decimal("-1000")),
    CashFlowInput(date=date(2024, 3, 1), amount=Decimal("-400")),
    CashFlowInput(date=date(2024, 4, 1), amount=Decimal("100")),
]
ORDINARY_HEAD = {
    date(2024, 2, 1): "2.071606",
    date(2024, 3, 1): "2.031698",
    date(2024, 4, 1): "1.233021",
    date(2024, 6, 1): "1.003936",
}

NET_WITHDRAWAL_SNAPSHOTS = [
    NAVSnapshot(date=date(2024, 1, 1), nav=Decimal("1000")),
    NAVSnapshot(date=date(2024, 2, 1), nav=Decimal("1200")),
    NAVSnapshot(date=date(2024, 3, 1), nav=Decimal("300")),
    NAVSnapshot(date=date(2024, 4, 1), nav=Decimal("310")),
]
NET_WITHDRAWAL_FLOWS = [CashFlowInput(date=date(2024, 3, 1), amount=Decimal("1500"))]  # capital 1000 − 1500 = −500


# =============================================================================
# HELPERS
# =============================================================================


def _by_date(points: list[MWRRPoint]) -> dict[date, str | None]:
    return {point.date: None if point.mwrr is None else str(point.mwrr) for point in points}


def _point_on(points: list[MWRRPoint], day: date) -> MWRRPoint:
    point = next((point for point in points if point.date == day), None)
    assert point is not None, f"no point on {day}: the series holds {sorted(_by_date(points))}"
    return point


def _single_flow_closed_form(nav: Decimal, deposit: Decimal, days: int) -> float:
    """The rate of one deposit worth ``nav`` ``days`` later: (nav / deposit)^(365 / days) − 1."""
    return float(nav / deposit) ** (365.0 / days) - 1.0


def _npv(flows: list[tuple[float, float]], rate: float) -> float:
    """This file's own NPV of ``(years, amount)`` flows — not the product's."""
    return sum(amount / (1.0 + rate) ** years for years, amount in flows)


def _changes_sign_around(flows: list[tuple[float, float]], rate: float, step: float = 1e-4) -> bool:
    below, above = _npv(flows, rate - step), _npv(flows, rate + step)
    return below != 0.0 and above != 0.0 and (below < 0.0) != (above < 0.0)


def _solve_flows(start: date, start_nav: Decimal, end: date, end_nav: Decimal, flows: list[CashFlowInput]) -> list[tuple[float, float]]:
    """The XIRR flows of a period, by its definition: −opening value at 0, the flows strictly inside, the closing value
    plus the end date's flows at T."""
    total = (end - start).days
    inside = [((flow.date - start).days / 365.0, float(flow.amount)) for flow in flows if start < flow.date < end]
    on_end = sum((flow.amount for flow in flows if flow.date == end), Decimal("0"))
    return [(0.0, -float(start_nav)), *inside, (total / 365.0, float(end_nav + on_end))]


# =============================================================================
# TESTS
# =============================================================================


class TestDepositDayOfAPeriodOpeningAtZero:
    """The lot's example: snapshots 1/1 NAV 0, 1/2 NAV 0, 1/3 NAV 1000, 2/3 NAV 1001; a deposit of 1000 on 1/3."""

    def test_period_series_point_on_the_deposit_day_has_no_rate(self):
        """RED on HEAD: 0.100000 — every flow of the period ending on 1/3 is zero, Newton's start comes back."""
        points = period_mwrr_series(DEPOSIT_DAY_SNAPSHOTS, DEPOSIT_DAY_FLOWS)

        point = _point_on(points, DEPOSIT_DAY)
        assert point.mwrr is None, f"the period ending on {DEPOSIT_DAY} opens at 0 and its only flow is that day's deposit: every XIRR flow is 0, so no rate («—»), got {point.mwrr} (the solver's starting guess)"

    def test_period_series_other_points_unchanged(self):
        """GREEN guard: 1/2 None (capital 0), 2/3 0.440251 exactly — the closed form 1.001^365 − 1."""
        points = period_mwrr_series(DEPOSIT_DAY_SNAPSHOTS, DEPOSIT_DAY_FLOWS)

        assert _point_on(points, EMPTY_DAY).mwrr is None, f"the period ending on {EMPTY_DAY} has no capital: {_by_date(points)}"
        assert str(_point_on(points, NEXT_DAY).mwrr) == "0.440251", f"the point of {NEXT_DAY} moved: {_by_date(points)}"
        closed = _single_flow_closed_form(Decimal("1001"), DEPOSIT, (NEXT_DAY - DEPOSIT_DAY).days)
        assert abs(float(_point_on(points, NEXT_DAY).mwrr) - closed) <= CLOSED_FORM_TOLERANCE, f"{NEXT_DAY}: {_point_on(points, NEXT_DAY).mwrr} vs the closed form {closed:.6f}"

    def test_calculate_series_has_no_rate_while_every_flow_is_zero(self):
        """RED on HEAD: 1/2 and 1/3 both 0.100000 (calculate_mwrr_series has no capital guard). 2/3 unchanged."""
        points = calculate_mwrr_series(DEPOSIT_DAY_SNAPSHOTS, DEPOSIT_DAY_FLOWS)

        assert _by_date(points) == {EMPTY_DAY: None, DEPOSIT_DAY: None, NEXT_DAY: "0.440251"}, f"every flow is zero up to {DEPOSIT_DAY} included: no rate there; got {_by_date(points)}"

    def test_period_mwrr_ending_on_the_deposit_day_has_no_rate(self):
        """RED on HEAD: 0.100000 — the card of the period ending on the deposit day."""
        point = period_mwrr(DEPOSIT_DAY_SNAPSHOTS[:3], DEPOSIT_DAY_FLOWS, DEPOSIT_DAY, DEPOSIT)

        assert point == MWRRPoint(date=DEPOSIT_DAY, mwrr=None), f"the card of {OPEN_DAY}..{DEPOSIT_DAY} should be «—», got {point}"

    def test_period_mwrr_of_the_next_day_unchanged(self):
        """GREEN guard: the card of the period ending on 2/3 is the series' point, 0.440251."""
        point = period_mwrr(DEPOSIT_DAY_SNAPSHOTS, DEPOSIT_DAY_FLOWS, NEXT_DAY, Decimal("1001"))

        assert point == MWRRPoint(date=NEXT_DAY, mwrr=Decimal("0.440251")), point


class TestAccountEmptiedAndRefunded:
    """Deposits of 3 000 and 2 000, a withdrawal that empties the account on 20/4; the window opens on 1/5 at NAV 0, a
    re-deposit of 1 000 on 11/5, then +1.5 a day. Every flow before the window is outside every solve."""

    def test_precondition_the_window_opens_at_the_emptied_state(self):
        assert EMPTIED_SNAPSHOTS[0] == NAVSnapshot(date=WINDOW_OPEN, nav=Decimal("0"))
        assert sum((flow.amount for flow in PRE_WINDOW_FLOWS), Decimal("0")) == 0, "the flows before the window should net to zero (emptied account)"

    def test_redeposit_day_has_no_rate(self):
        """RED on HEAD: 0.100000 on 11/5."""
        points = period_mwrr_series(EMPTIED_SNAPSHOTS, EMPTIED_FLOWS)

        point = _point_on(points, REDEPOSIT_DAY)
        assert point.mwrr is None, f"the period {WINDOW_OPEN}..{REDEPOSIT_DAY} opens at 0 and its only flow is that day's re-deposit: no rate, got {point.mwrr}"

    def test_days_before_the_redeposit_have_no_rate(self):
        """GREEN guard: no capital before the re-deposit."""
        points = period_mwrr_series(EMPTIED_SNAPSHOTS, EMPTIED_FLOWS)

        before = {day: value for day, value in _by_date(points).items() if day < REDEPOSIT_DAY}
        assert before and set(before.values()) == {None}, before

    def test_days_after_the_redeposit_have_a_verified_root(self):
        """GREEN guard: every day after the re-deposit carries a rate that is the closed form and across which this file's
        own NPV changes sign; the first and last pinned exactly from HEAD."""
        points = period_mwrr_series(EMPTIED_SNAPSHOTS, EMPTIED_FLOWS)

        after = [snapshot for snapshot in EMPTIED_SNAPSHOTS if snapshot.date > REDEPOSIT_DAY]
        assert len(after) == WINDOW_DAYS - 11, f"precondition: {len(after)} days after the re-deposit"
        problems = []
        for snapshot in after:
            point = _point_on(points, snapshot.date)
            if point.mwrr is None:
                problems.append(f"{snapshot.date}: no rate")
                continue
            rate = float(point.mwrr)
            closed = _single_flow_closed_form(snapshot.nav, DEPOSIT, (snapshot.date - REDEPOSIT_DAY).days)
            if abs(rate - closed) > CLOSED_FORM_TOLERANCE:
                problems.append(f"{snapshot.date}: {point.mwrr} vs the closed form {closed:.6f}")
            flows = _solve_flows(WINDOW_OPEN, Decimal("0"), snapshot.date, snapshot.nav, EMPTIED_FLOWS)
            if not _changes_sign_around(flows, rate):
                problems.append(f"{snapshot.date}: the NPV does not change sign across {point.mwrr}")
        assert problems == [], problems
        assert str(_point_on(points, date(2024, 5, 12)).mwrr) == "0.728216"
        assert str(_point_on(points, date(2024, 5, 21)).mwrr) == "0.721910"


class TestDirectSolve:
    def test_calculate_mwrr_with_the_deposit_on_the_end_date_has_no_rate(self):
        """RED on HEAD: 0.100000 — initial 0, final 1000, a −1000 flow on the end date: flows (0, −0.0), (T, 0.0)."""
        point = calculate_mwrr([CashFlowInput(date=DEPOSIT_DAY, amount=-DEPOSIT)], Decimal("0"), DEPOSIT, OPEN_DAY, DEPOSIT_DAY)

        assert point == MWRRPoint(date=DEPOSIT_DAY, mwrr=None), point

    @pytest.mark.parametrize(
        "flows",
        [
            pytest.param([(0.0, -0.0), (1.0, 0.0)], id="minus-zero-open"),
            pytest.param([(0.0, 0.0), (0.5, 0.0), (1.0, 0.0)], id="three-zeros"),
            pytest.param([(0.0, -0.0), (60 / 365.0, 0.0)], id="deposit-day-shape"),
        ],
    )
    def test_solve_xirr_with_every_amount_zero_has_no_root(self, flows):
        """RED on HEAD: 0.1 — the NPV is 0 at every rate, Newton returns x0."""
        assert _solve_xirr(flows, 0.1) is None, f"every amount of {flows} is zero: no root, got the starting point back"

    def test_a_genuine_zero_rate_is_zero(self):
        """GREEN guard: 1000 → 1000 with no flows is a rate of exactly 0, not «—»."""
        point = calculate_mwrr([], DEPOSIT, DEPOSIT, OPEN_DAY, date(2024, 7, 1))

        assert point.mwrr is not None and point.mwrr.is_zero(), point
        root = _solve_xirr([(0.0, -1000.0), (0.5, 1000.0)], 0.1)
        assert root is not None and abs(root) < 1e-9, root


class TestOtherSeriesUnchanged:
    def test_ordinary_series_point_by_point(self):
        """GREEN guard: both series functions, every point as on HEAD."""
        assert _by_date(period_mwrr_series(ORDINARY_SNAPSHOTS, ORDINARY_FLOWS)) == ORDINARY_HEAD
        assert _by_date(calculate_mwrr_series(ORDINARY_SNAPSHOTS, ORDINARY_FLOWS)) == ORDINARY_HEAD

    def test_capital_rule_still_gives_none(self):
        """GREEN guard: the «capital ≤ 0» rule — a rate before the net withdrawal, None from it on."""
        assert _by_date(period_mwrr_series(NET_WITHDRAWAL_SNAPSHOTS, NET_WITHDRAWAL_FLOWS)) == {
            date(2024, 2, 1): "7.556483",
            date(2024, 3, 1): None,
            date(2024, 4, 1): None,
        }
        assert period_mwrr(NET_WITHDRAWAL_SNAPSHOTS, NET_WITHDRAWAL_FLOWS, date(2024, 4, 1), Decimal("310")).mwrr is None


def test_closed_form_helper_is_sane():
    """This file's own oracle: one deposit doubled in a year is 100 %."""
    assert math.isclose(_single_flow_closed_form(Decimal("2000"), Decimal("1000"), 365), 1.0)

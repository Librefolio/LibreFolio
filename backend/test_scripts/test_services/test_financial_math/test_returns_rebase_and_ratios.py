"""
CP-4a (workstream J, U4b): the period rebase and two return ratios move into ``returns.py``.

Module under test: ``backend/app/services/financial_math/returns.py``. Three pure functions replace
math that ``backend/app/services/portfolio_service.py`` writes in place today:

* ``rebase_to_period(nav_snapshots, cash_flows, date_from) -> PeriodRebase``: the period rebase that
  ``get_summary`` (``:969-994``) and ``get_history`` (``:1244-1270``) each write for themselves;
* ``net_holding_return(market_pnl, income, costs, cost_basis)``: the net return of an open position,
  before its annualization (``:870-883``);
* ``gain_loss_ratio(gain, base, *, positive_base)``: the gain/loss percentage of a position
  (``:824``), of a broker card (``:939``) and of the headline (``:1040``). Each caller keeps its own
  fallback: ``None`` for the position, 0 for the broker and the headline.

No value changes (plan, «CP-4 — U4b + V-11»). Each function is checked against a copy of today's
code, kept here as it stands in ``portfolio_service.py`` (the ``*_today`` functions). The rebase is
compared with both of today's blocks on a grid of cases with one snapshot per date, which is what
the engine produces (one daily state per day). The one declared difference concerns repeated dates,
which the engine never produces: the period then starts at the start snapshot itself
(``TestRebaseToPeriod.test_repeated_dates_start_at_the_start_snapshot_itself``).

Red by absence until CP-4a: every new name is read as ``returns.<name>`` while a test runs, never
imported at module level, so the file collects today and each test fails on the missing attribute
instead of the whole file failing at import.

Zeros are compared numerically. Today the synthetic flow of a zero start NAV is ``-Decimal("0")``,
that is ``Decimal("-0")``; ``Decimal("-0") == Decimal("0")``, and the NamedTuples compare their
fields with ``==``, so the sign of a zero is not part of the contract.

CP-10a (workstream J, developer's decision 29 — one Rolling Return, in calendar days): the price
return of two prices gets its home here too. ``price_return(start, end)`` is ``end / start - 1``
exactly, that expression and no rounding, and ``None`` when a price is missing or the start price is
zero: never a division by zero. Two sites write it in place today and will call it, with identical
values: the prepared returns of ``market_series.py`` (``current.target_close /
previous.target_close - Decimal("1")``) and the calendar rolling return
(``signal_plugins/calendar_rolling_return/plugin.py``, ``(current.close / reference.close - one) *
hundred``). Both are copied below as they stand (``*_today``) and compared exactly. Red by absence,
like the CP-4a names: ``returns.price_return`` is read while each test runs.

CP-7a (workstream J, developer's decision 26 — D-J1 option B, each leg of a disposal converted at its own date): the gain
or loss a disposal realizes gets its home here. ``realized_gain(proceeds, cost)`` is ``proceeds - cost``, both already in
one currency, and ``None`` when either is unknown (no rate): never computed from the known leg alone. The Dashboard's
sales (``portfolio_service.py``, ``sale.proceeds - sale.cost``) and the lots' closures (``lots/conversions.py``,
``convert_closure``) call it. Red by absence, like the names above: ``returns.realized_gain`` is read while each test
runs, so before CP-7a each of its tests fails on the missing attribute and the rest of the file still collects.

MF-A12 (workstream MF, «one home»; coordinator's decision N92): a Dashboard holding's one-day columns
(``portfolio_service.get_summary``, a holding valued at its market price) take their ratio from ``change_ratio``.
``price_change_1d`` is ``change_ratio(current_price - prev_price_base, prev_price_base)`` rounded to 4 decimals, where
HEAD ``efef5c876`` wrote ``((current_price - prev_price_base) / prev_price_base).quantize(Decimal("0.0001"))``;
``gain_loss_change_1d_percent`` is ``change_ratio(gain_loss_change_1d, previous_position_value) × 100`` rounded to 2,
where HEAD wrote ``(gain_loss_change_1d / abs(previous_position_value) * 100).quantize(Decimal("0.01"))``. The
materiality guard ``|previous_position_value| > 0.01`` stays the caller's. Both HEAD expressions are copied below
(``*_today``). The percent is HEAD's to the bit (``a / b * 100`` is ``(a / b) * 100``). On a positive price the price
change is HEAD's to the bit too, rounding ties included: ``(c − p) / |p|`` is ``(c − p) / p``, the same two operations.
``price_return``'s ``c / p − 1`` would not be: it rounds the quotient to 28 digits before subtracting, and on a price
converted by a division it lands exactly on a half-way return that HEAD sees 1E-28 below, so it rounds the other way
(the reason for N92; ``test_ties_are_today_s_where_end_over_start_minus_one_is_not``). The one value change is a
negative price: the change now keeps the move's sign (−10 → −12.5 is −25 %, HEAD said +25 %), as the percent column
always did; and an unmoved negative price now reads ``0.0000`` where HEAD's zero carried the price's sign
(``-0.0000``). The call site is locked in ``test_financial/test_summary_day_change_house.py``, where the negative price
is the red on HEAD; every test here is green on HEAD too: ``returns.py`` did not change, and these pin the formula, not
the service.

Pure: no database, no server, no network.
"""

from __future__ import annotations

import dataclasses
import itertools
from collections import Counter
from datetime import date
from decimal import Decimal
from fractions import Fraction

import pytest

from backend.app.services.financial_math import returns
from backend.app.services.financial_math.returns import CashFlowInput, NAVSnapshot
from backend.app.services.financial_math.valuation import compute_holding_value

D1 = date(2025, 3, 1)
D2 = date(2025, 3, 2)
D3 = date(2025, 3, 3)
D4 = date(2025, 3, 4)
D5 = date(2025, 3, 5)
D6 = date(2025, 3, 6)
D7 = date(2025, 3, 7)
D8 = date(2025, 3, 8)

# Snapshots on D2, D4 and D6, so a date_from can fall before the first (D1), on one (D2, D4, D6),
# between two (D3, D5) or after the last (D8).
SNAPSHOT_DATES = (D2, D4, D6)
POSITIVE_NAVS = (Decimal("1000"), Decimal("1180"), Decimal("1250"))
# NAV zero on D2 and D4 (a portfolio that holds nothing yet), positive on D6. "0.00" carries an
# exponent on purpose: the rule compares the NAV with zero, never its text.
ZERO_START_NAVS = (Decimal("0"), Decimal("0.00"), Decimal("700"))

# One flow before the first snapshot, one on each snapshot, one between two snapshots and one after
# the last: whatever the start date, some flows fall before it, on it and after it.
FLOWS = (
    CashFlowInput(D1, Decimal("-100")),
    CashFlowInput(D2, Decimal("-1000")),
    CashFlowInput(D3, Decimal("-50")),
    CashFlowInput(D4, Decimal("-150")),
    CashFlowInput(D5, Decimal("40")),
    CashFlowInput(D6, Decimal("-60")),
    CashFlowInput(D7, Decimal("25")),
)

# What get_summary puts in the start date when there is no snapshot at all (its ``today``); the
# grid always has snapshots, so it never reaches a result.
SUMMARY_TODAY = date(2099, 12, 31)

NAV_CASES = {
    "positive-start-nav": POSITIVE_NAVS,
    "zero-start-nav": ZERO_START_NAVS,
}
DATE_FROM_CASES = {
    "no-date-from": None,
    "before-first-snapshot": D1,
    "on-first-snapshot": D2,
    "between-first-and-middle": D3,
    "on-middle-snapshot": D4,
    "between-middle-and-last": D5,
    "on-last-snapshot": D6,
    "after-last-snapshot": D8,
}


def _snapshots(navs: tuple[Decimal, ...]) -> list[NAVSnapshot]:
    return [NAVSnapshot(day, nav) for day, nav in zip(SNAPSHOT_DATES, navs, strict=True)]


def _dec(text: str | None) -> Decimal | None:
    return None if text is None else Decimal(text)


# =============================================================================
# Today's code, copied as written: the characterization oracles
# =============================================================================


def _summary_rebase_today(nav_snapshots, cash_flows_perf, date_from, today):
    """``get_summary``'s period rebase, ``portfolio_service.py:969-994``, both branches as written.

    Returns (start date, start NAV, snapshots, flows).
    """
    if date_from and nav_snapshots:
        pre_period = [s for s in nav_snapshots if s.date <= date_from]
        if pre_period:
            period_start_nav_perf = pre_period[-1].nav
            period_start_date_perf = pre_period[-1].date
        else:
            period_start_nav_perf = Decimal("0")
            period_start_date_perf = nav_snapshots[0].date

        synthetic_cf = CashFlowInput(date=period_start_date_perf, amount=-period_start_nav_perf)
        if period_start_nav_perf > 0:
            period_cfs = [synthetic_cf] + [cf for cf in cash_flows_perf if cf.date > period_start_date_perf]
        else:
            period_cfs = [synthetic_cf] + [cf for cf in cash_flows_perf if cf.date > period_start_date_perf]
        period_navs = [s for s in nav_snapshots if s.date >= period_start_date_perf]
    else:
        period_cfs = cash_flows_perf
        period_navs = nav_snapshots
        period_start_nav_perf = Decimal("0") if nav_snapshots else Decimal("0")
        period_start_date_perf = nav_snapshots[0].date if nav_snapshots else today
    return period_start_date_perf, period_start_nav_perf, list(period_navs), list(period_cfs)


def _history_rebase_today(nav_snapshots, cash_flows, date_from):
    """``get_history``'s period rebase, ``portfolio_service.py:1244-1270``, both branches as written.

    Returns (snapshots, flows): ``get_history`` keeps no start date or NAV of its own.
    """
    if date_from and nav_snapshots:
        pre_period = [s for s in nav_snapshots if s.date <= date_from]
        if pre_period:
            period_start_nav = pre_period[-1].nav
            period_start_date = pre_period[-1].date
        else:
            period_start_nav = Decimal("0")
            period_start_date = nav_snapshots[0].date

        synthetic_cf = CashFlowInput(date=period_start_date, amount=-period_start_nav)
        if period_start_nav > 0:
            period_cash_flows = [synthetic_cf] + [cf for cf in cash_flows if cf.date > period_start_date]
        else:
            period_cash_flows = [synthetic_cf] + [cf for cf in cash_flows if cf.date > period_start_date]
        period_nav_snapshots = [s for s in nav_snapshots if s.date >= period_start_date]
        if period_start_nav > 0 and period_nav_snapshots and period_nav_snapshots[0].nav != period_start_nav:
            period_nav_snapshots = [NAVSnapshot(date=period_start_date, nav=period_start_nav)] + period_nav_snapshots
    else:
        period_cash_flows = cash_flows
        period_nav_snapshots = nav_snapshots
    return list(period_nav_snapshots), list(period_cash_flows)


def _position_net_return_today(gain_loss, pos_income, pos_fees, cost_basis):
    """The open position's net return, ``portfolio_service.py:878-882``, before its annualization.

    Only the cost-basis part of the guard of ``:878`` is kept: ``cost_complete`` and the first
    transaction date stay conditions of the caller.
    """
    if cost_basis and cost_basis != 0:
        market_component = gain_loss if gain_loss is not None else Decimal("0")
        return (market_component + pos_income - pos_fees) / cost_basis
    return None


def _position_gain_loss_pct_today(gain_loss, cost_basis):
    """Position G/L %, ``portfolio_service.py:824``."""
    return (gain_loss / cost_basis) if gain_loss is not None and cost_basis != 0 else None


def _broker_gain_loss_pct_today(broker_gain, broker_capital):
    """Broker card G/L %, ``portfolio_service.py:939``."""
    return (broker_gain / broker_capital) if broker_capital > 0 else Decimal("0")


def _headline_gain_loss_pct_today(total_gl, total_invested):
    """Headline G/L %, ``portfolio_service.py:1040``."""
    return (total_gl / total_invested) if total_invested > 0 else Decimal("0")


# =============================================================================
# rebase_to_period
# =============================================================================


class TestRebaseToPeriod:
    """``rebase_to_period``: the snapshots and flows of the period that starts at ``date_from``.

    The start is the last snapshot dated on or before ``date_from``; its NAV enters the period as a
    synthetic deposit on its date, and the flows of that date are already inside it.
    """

    @pytest.mark.parametrize("date_from", list(DATE_FROM_CASES.values()), ids=list(DATE_FROM_CASES))
    @pytest.mark.parametrize("navs", list(NAV_CASES.values()), ids=list(NAV_CASES))
    def test_matches_today_summary_and_history_blocks(self, navs, date_from):
        """Characterization: with one snapshot per date, the function gives what both of today's
        blocks give — the summary's start date and NAV, and the snapshots and flows of either."""
        nav_snapshots = _snapshots(navs)
        cash_flows = list(FLOWS)

        start_date, start_nav, summary_navs, summary_flows = _summary_rebase_today(nav_snapshots, cash_flows, date_from, SUMMARY_TODAY)
        history_navs, history_flows = _history_rebase_today(nav_snapshots, cash_flows, date_from)
        # On the copies: with unique dates today's two blocks agree, which is what lets one
        # function replace both.
        assert (summary_navs, summary_flows) == (history_navs, history_flows)

        result = returns.rebase_to_period(nav_snapshots, cash_flows, date_from)

        assert result.start_date == start_date
        assert result.start_nav == start_nav
        assert list(result.nav_snapshots) == summary_navs
        assert list(result.cash_flows) == summary_flows

    def test_without_date_from_the_inputs_pass_through(self):
        """No ``date_from``: snapshots and flows unchanged, start NAV 0, start date the first snapshot's."""
        nav_snapshots = _snapshots(POSITIVE_NAVS)

        result = returns.rebase_to_period(nav_snapshots, list(FLOWS), None)

        assert result.start_date == D2
        assert result.start_nav == 0
        assert result.nav_snapshots == tuple(nav_snapshots)
        assert result.cash_flows == FLOWS

    @pytest.mark.parametrize("date_from", [None, D3], ids=["no-date-from", "with-date-from"])
    def test_without_snapshots_the_flows_pass_through_and_there_is_no_start_date(self, date_from):
        """No snapshot: flows unchanged, start NAV 0, start date ``None``.

        Today's summary puts its ``today`` there (``:994``); the function knows no calendar, so the
        caller keeps that fallback. Snapshots and flows are what today's history block gives.
        """
        result = returns.rebase_to_period([], list(FLOWS), date_from)

        assert result.start_date is None
        assert result.start_nav == 0
        assert result.nav_snapshots == ()
        assert result.cash_flows == FLOWS
        assert (list(result.nav_snapshots), list(result.cash_flows)) == _history_rebase_today([], list(FLOWS), date_from)

    @pytest.mark.parametrize("date_from", [D4, D5], ids=["on-the-snapshot", "after-it"])
    def test_the_period_starts_at_the_last_snapshot_on_or_before_date_from(self, date_from):
        """Start: the snapshot of D4 (NAV 1180), the last one dated <= ``date_from``.

        Flows: the synthetic −1180 on D4, then only the flows strictly after D4 (the −150 of D4 is
        already inside the start NAV). Snapshots: from D4 on.
        """
        result = returns.rebase_to_period(_snapshots(POSITIVE_NAVS), list(FLOWS), date_from)

        assert result.start_date == D4
        assert result.start_nav == Decimal("1180")
        assert result.nav_snapshots == (NAVSnapshot(D4, Decimal("1180")), NAVSnapshot(D6, Decimal("1250")))
        assert result.cash_flows == (
            CashFlowInput(D4, Decimal("-1180")),
            CashFlowInput(D5, Decimal("40")),
            CashFlowInput(D6, Decimal("-60")),
            CashFlowInput(D7, Decimal("25")),
        )

    def test_after_the_last_snapshot_the_period_starts_at_the_last(self):
        result = returns.rebase_to_period(_snapshots(POSITIVE_NAVS), list(FLOWS), D8)

        assert result.start_date == D6
        assert result.start_nav == Decimal("1250")
        assert result.nav_snapshots == (NAVSnapshot(D6, Decimal("1250")),)
        assert result.cash_flows == (CashFlowInput(D6, Decimal("-1250")), CashFlowInput(D7, Decimal("25")))

    def test_before_every_snapshot_the_period_starts_from_zero_at_the_first(self):
        """``date_from`` before every snapshot: start NAV 0 at the first snapshot (D2).

        Flows: a synthetic zero on D2 (its sign is not pinned), then the flows strictly after D2.
        The −1000 of D2 is already inside the first NAV and the −100 of D1 is before the period:
        both are out. Snapshots: all of them.
        """
        nav_snapshots = _snapshots(POSITIVE_NAVS)

        result = returns.rebase_to_period(nav_snapshots, list(FLOWS), D1)

        assert result.start_date == D2
        assert result.start_nav == 0
        assert result.nav_snapshots == tuple(nav_snapshots)
        assert result.cash_flows == (
            CashFlowInput(D2, Decimal("0")),
            CashFlowInput(D3, Decimal("-50")),
            CashFlowInput(D4, Decimal("-150")),
            CashFlowInput(D5, Decimal("40")),
            CashFlowInput(D6, Decimal("-60")),
            CashFlowInput(D7, Decimal("25")),
        )

    def test_repeated_dates_start_at_the_start_snapshot_itself(self):
        """DECLARED DIFFERENCE (CP-4a): with two snapshots on one date, the period starts at the
        start snapshot itself, so the first snapshot of the period carries the start NAV.

        The engine never produces this (one daily state per day): no value the app shows changes.
        Two snapshots on D4 (900, then 1180), ``date_from`` = D4, so the start is the last of them.
        Today the two blocks disagree with each other: the summary keeps the earlier same-date
        snapshot first, and the history prepends a synthetic start snapshot to the same list. The
        new rule slices from the start snapshot. The flows are the same in all three.
        """
        nav_snapshots = [
            NAVSnapshot(D2, Decimal("1000")),
            NAVSnapshot(D4, Decimal("900")),
            NAVSnapshot(D4, Decimal("1180")),
            NAVSnapshot(D6, Decimal("1250")),
        ]
        expected_flows = [
            CashFlowInput(D4, Decimal("-1180")),
            CashFlowInput(D5, Decimal("40")),
            CashFlowInput(D6, Decimal("-60")),
            CashFlowInput(D7, Decimal("25")),
        ]

        # Today, documented on the copies.
        start_date, start_nav, summary_navs, summary_flows = _summary_rebase_today(nav_snapshots, list(FLOWS), D4, SUMMARY_TODAY)
        history_navs, history_flows = _history_rebase_today(nav_snapshots, list(FLOWS), D4)
        assert (start_date, start_nav) == (D4, Decimal("1180"))
        assert summary_navs == [NAVSnapshot(D4, Decimal("900")), NAVSnapshot(D4, Decimal("1180")), NAVSnapshot(D6, Decimal("1250"))]
        assert history_navs == [NAVSnapshot(D4, Decimal("1180")), NAVSnapshot(D4, Decimal("900")), NAVSnapshot(D4, Decimal("1180")), NAVSnapshot(D6, Decimal("1250"))]
        assert summary_flows == history_flows == expected_flows

        result = returns.rebase_to_period(nav_snapshots, list(FLOWS), D4)

        assert result.start_date == D4
        assert result.start_nav == Decimal("1180")
        assert result.nav_snapshots == (NAVSnapshot(D4, Decimal("1180")), NAVSnapshot(D6, Decimal("1250")))
        assert result.nav_snapshots[0].nav == result.start_nav
        assert list(result.cash_flows) == expected_flows

    def test_the_result_is_a_frozen_dataclass_of_tuples(self):
        """``PeriodRebase`` is a frozen dataclass; its snapshots and flows are tuples of the module's
        NamedTuples; the start NAV is a Decimal; the inputs are not modified."""
        nav_snapshots = _snapshots(POSITIVE_NAVS)
        cash_flows = list(FLOWS)
        inputs_before = (list(nav_snapshots), list(cash_flows))

        results = [returns.rebase_to_period(nav_snapshots, cash_flows, date_from) for date_from in (None, D1, D4, D8)]
        results.append(returns.rebase_to_period([], cash_flows, D4))

        assert dataclasses.is_dataclass(returns.PeriodRebase)
        assert {"start_date", "start_nav", "nav_snapshots", "cash_flows"} <= {field.name for field in dataclasses.fields(returns.PeriodRebase)}
        for result in results:
            assert isinstance(result, returns.PeriodRebase)
            assert isinstance(result.start_nav, Decimal)
            assert isinstance(result.nav_snapshots, tuple)
            assert all(isinstance(snapshot, NAVSnapshot) for snapshot in result.nav_snapshots)
            assert isinstance(result.cash_flows, tuple)
            assert all(isinstance(flow, CashFlowInput) for flow in result.cash_flows)
        with pytest.raises(dataclasses.FrozenInstanceError):
            results[0].start_nav = Decimal("1")
        assert (nav_snapshots, cash_flows) == inputs_before, "the inputs must not be modified"


# =============================================================================
# net_holding_return
# =============================================================================


class TestNetHoldingReturn:
    """``net_holding_return``: ``((market_pnl or 0) + income − costs) / cost_basis``, ``None`` on a zero cost basis."""

    def test_market_pnl_plus_income_minus_costs_over_cost_basis(self):
        result = returns.net_holding_return(market_pnl=Decimal("150.50"), income=Decimal("20.25"), costs=Decimal("5.75"), cost_basis=Decimal("1000"))

        assert result == Decimal("0.165")

    def test_without_market_pnl_the_return_is_income_only(self):
        """An open position with no market P&L (no price, e.g. an unquoted BTP that pays coupons)
        still has a return: its income minus its costs, over its cost."""
        result = returns.net_holding_return(market_pnl=None, income=Decimal("30"), costs=Decimal("5"), cost_basis=Decimal("1000"))

        assert result == Decimal("0.025")

    def test_a_loss_gives_a_negative_return(self):
        result = returns.net_holding_return(market_pnl=Decimal("-200"), income=Decimal("10"), costs=Decimal("15"), cost_basis=Decimal("1000"))

        assert result == Decimal("-0.205")

    @pytest.mark.parametrize("zero", ["0", "0.00", "-0"])
    def test_a_zero_cost_basis_has_no_return(self, zero):
        result = returns.net_holding_return(market_pnl=Decimal("50"), income=Decimal("10"), costs=Decimal("5"), cost_basis=Decimal(zero))

        assert result is None

    def test_the_arithmetic_is_exact_decimal(self):
        """No float and no rounding: (0.1 + 0.2 − 0) / 3 is exactly 0.1 (through float it would be
        0.10000000000000002), and 100 / 3 keeps the precision of the Decimal context."""
        tenth = returns.net_holding_return(market_pnl=Decimal("0.1"), income=Decimal("0.2"), costs=Decimal("0"), cost_basis=Decimal("3"))
        third = returns.net_holding_return(market_pnl=Decimal("100"), income=Decimal("0"), costs=Decimal("0"), cost_basis=Decimal("3"))

        assert isinstance(tenth, Decimal)
        assert tenth == Decimal("0.1")
        assert third == Decimal("100") / Decimal("3")

    def test_matches_today_position_formula(self):
        """Characterization: every value today's position block computes, the function computes too."""
        grid = itertools.product(
            (None, Decimal("0"), Decimal("150.50"), Decimal("-420.10")),
            (Decimal("0"), Decimal("33.40")),
            (Decimal("0"), Decimal("12.15")),
            (Decimal("1000"), Decimal("3"), Decimal("-500"), Decimal("0"), Decimal("0.00")),
        )
        for market_pnl, income, costs, cost_basis in grid:
            expected = _position_net_return_today(market_pnl, income, costs, cost_basis)

            result = returns.net_holding_return(market_pnl=market_pnl, income=income, costs=costs, cost_basis=cost_basis)

            assert result == expected, f"market_pnl={market_pnl} income={income} costs={costs} cost_basis={cost_basis}: {result} != {expected}"


# =============================================================================
# gain_loss_ratio
# =============================================================================


class TestGainLossRatio:
    """``gain_loss_ratio``: gain / base; ``None`` without a gain or a base, on a zero base, and on a
    base that is not positive when ``positive_base`` asks for one.

    Two families of callers. The position (``:824``) divides on any non-zero base:
    ``positive_base=False``. The broker card (``:939``) and the headline (``:1040``) divide only on
    a positive capital: ``positive_base=True``, and they map ``None`` to 0 themselves.
    """

    @pytest.mark.parametrize(
        ("gain", "base", "expected"),
        [
            pytest.param("25", "200", "0.125", id="gain"),
            pytest.param("-30", "200", "-0.15", id="loss"),
            pytest.param("10", "-40", "-0.25", id="negative-base-still-a-ratio"),
        ],
    )
    def test_position_family_divides_on_any_non_zero_base(self, gain, base, expected):
        assert returns.gain_loss_ratio(Decimal(gain), Decimal(base), positive_base=False) == Decimal(expected)

    @pytest.mark.parametrize(
        ("gain", "base"),
        [
            pytest.param(None, "200", id="no-gain"),
            pytest.param("25", None, id="no-base"),
            pytest.param("25", "0", id="zero-base"),
            pytest.param("25", "0.00", id="zero-base-with-exponent"),
            pytest.param("25", "-0", id="negative-zero-base"),
        ],
    )
    def test_position_family_has_no_ratio_without_gain_or_on_a_zero_base(self, gain, base):
        assert returns.gain_loss_ratio(_dec(gain), _dec(base), positive_base=False) is None

    @pytest.mark.parametrize(
        ("gain", "base", "expected"),
        [
            pytest.param("25", "200", "0.125", id="gain"),
            pytest.param("-30", "200", "-0.15", id="loss"),
            pytest.param("1", "0.01", "100", id="small-positive-base"),
        ],
    )
    def test_capital_family_divides_on_a_positive_base(self, gain, base, expected):
        assert returns.gain_loss_ratio(Decimal(gain), Decimal(base), positive_base=True) == Decimal(expected)

    @pytest.mark.parametrize(
        ("gain", "base"),
        [
            pytest.param("10", "-40", id="negative-base"),
            pytest.param("25", "-0.01", id="small-negative-base"),
            pytest.param("25", "0", id="zero-base"),
            pytest.param(None, "200", id="no-gain"),
            pytest.param("25", None, id="no-base"),
        ],
    )
    def test_capital_family_has_no_ratio_on_a_base_that_is_not_positive(self, gain, base):
        assert returns.gain_loss_ratio(_dec(gain), _dec(base), positive_base=True) is None

    @pytest.mark.parametrize("positive_base", [False, True])
    def test_the_ratio_is_exact(self, positive_base):
        """No rounding and no float: 100 / 3 keeps the precision of the Decimal context."""
        result = returns.gain_loss_ratio(Decimal("100"), Decimal("3"), positive_base=positive_base)

        assert isinstance(result, Decimal)
        assert result == Decimal("100") / Decimal("3")

    def test_positive_base_is_a_required_keyword(self):
        """Each caller states its guard: ``positive_base`` has no default and is keyword-only."""
        gain_loss_ratio = returns.gain_loss_ratio

        with pytest.raises(TypeError):
            gain_loss_ratio(Decimal("1"), Decimal("2"), True)
        with pytest.raises(TypeError):
            gain_loss_ratio(Decimal("1"), Decimal("2"))

    def test_matches_today_call_sites(self):
        """Characterization: the position's ratio as today, and the broker's and headline's once
        the caller maps ``None`` to 0, as they keep doing."""
        gains = (Decimal("125.50"), Decimal("-80"), Decimal("0"), Decimal("100"))
        bases = (Decimal("1000"), Decimal("3"), Decimal("0.01"), Decimal("0"), Decimal("0.00"), Decimal("-0"), Decimal("-250"))

        for gain, base in itertools.product((None, *gains), bases):
            expected = _position_gain_loss_pct_today(gain, base)
            result = returns.gain_loss_ratio(gain, base, positive_base=False)
            assert result == expected, f"position, gain={gain} base={base}: {result} != {expected}"

        for gain, base in itertools.product(gains, bases):
            ratio = returns.gain_loss_ratio(gain, base, positive_base=True)
            result = ratio if ratio is not None else Decimal("0")
            assert result == _broker_gain_loss_pct_today(gain, base), f"broker, gain={gain} base={base}: {result}"
            assert result == _headline_gain_loss_pct_today(gain, base), f"headline, gain={gain} base={base}: {result}"


# =============================================================================
# price_return (CP-10a)
# =============================================================================


def _prepared_return_today(previous_close: Decimal, current_close: Decimal) -> Decimal:
    """The prepared return of ``market_series.py`` (``prepare_asset_series_set``), before its ``float()``, as written."""
    return current_close / previous_close - Decimal("1")


def _calendar_return_today(reference_close: Decimal, current_close: Decimal) -> Decimal:
    """The calendar rolling return of ``calendar_rolling_return/plugin.py`` (``compute``), before its ``float()``, as written."""
    one = Decimal("1")
    hundred = Decimal("100")
    return (current_close / reference_close - one) * hundred


class TestPriceReturn:
    """``price_return(start, end)``: ``end / start - 1``, exact; ``None`` without a price or on a zero start price."""

    def test_a_gain_is_end_over_start_minus_one_exactly(self):
        result = returns.price_return(Decimal("100"), Decimal("110"))

        assert isinstance(result, Decimal)
        assert result == Decimal("110") / Decimal("100") - 1
        assert result == Decimal("0.1")

    def test_a_loss_gives_a_negative_return(self):
        result = returns.price_return(Decimal("120"), Decimal("90"))

        assert result == Decimal("90") / Decimal("120") - 1
        assert result == Decimal("-0.25")

    def test_the_start_price_comes_first_and_the_end_price_second(self):
        """The signature is ``price_return(start, end)``: by position and by name alike."""
        assert returns.price_return(Decimal("100"), Decimal("110")) != returns.price_return(Decimal("110"), Decimal("100"))
        assert returns.price_return(start=Decimal("100"), end=Decimal("110")) == Decimal("0.1")
        assert returns.price_return(end=Decimal("110"), start=Decimal("100")) == Decimal("0.1")

    def test_the_result_is_not_rounded(self):
        """No quantize and no float: 1 / 3 − 1 keeps the precision of the Decimal context; through a float it would read
        -0.6666666666666667."""
        result = returns.price_return(Decimal("3"), Decimal("1"))

        assert result == Decimal("1") / Decimal("3") - 1
        assert result != Decimal(str(1.0 / 3.0 - 1.0))

    @pytest.mark.parametrize("zero", ["0", "0.00", "-0"])
    def test_a_zero_start_price_has_no_return(self, zero):
        """Never a division by zero: the zero is compared by value, whatever its exponent or sign."""
        assert returns.price_return(Decimal(zero), Decimal("110")) is None

    @pytest.mark.parametrize(
        ("start", "end"),
        [
            pytest.param(None, "110", id="no-start-price"),
            pytest.param("100", None, id="no-end-price"),
            pytest.param(None, None, id="no-price-at-all"),
            pytest.param(None, "0", id="no-start-price-and-a-zero-end"),
        ],
    )
    def test_a_missing_price_has_no_return(self, start, end):
        assert returns.price_return(_dec(start), _dec(end)) is None

    def test_a_zero_end_price_is_a_total_loss(self):
        """Only the START price makes the return undefined: an end price of zero is ``0 / start - 1``, that is -1."""
        assert returns.price_return(Decimal("100"), Decimal("0")) == Decimal("-1")

    def test_matches_today_prepared_and_calendar_returns(self):
        """Characterization: on every ordered pair of a grid of prices (gains, losses, flat pairs, awkward decimals),
        ``price_return`` is exactly today's prepared return, and times a hundred exactly today's calendar return."""
        prices = (Decimal("100"), Decimal("110"), Decimal("101.37"), Decimal("99.83"), Decimal("0.0042"), Decimal("12345.678901"), Decimal("3"))

        for start, end in itertools.product(prices, repeat=2):
            result = returns.price_return(start, end)
            assert result == _prepared_return_today(start, end), f"prepared return, {start} -> {end}: {result}"
            assert result * Decimal("100") == _calendar_return_today(start, end), f"calendar return, {start} -> {end}: {result}"


# =============================================================================
# realized_gain (CP-7a)
# =============================================================================


class TestRealizedGain:
    """``realized_gain(proceeds, cost)``: ``proceeds - cost``, exact; ``None`` when either leg is unknown.

    Each leg arrives already converted by its caller, at its own date. Before CP-7a there was no ``returns.realized_gain``:
    every test below failed on the missing attribute (AttributeError), and each caller wrote the subtraction in place.
    """

    @pytest.mark.parametrize(
        ("proceeds", "cost", "expected"),
        [
            pytest.param("100", "90", "10", id="gain"),
            pytest.param("99", "100", "-1", id="loss-the-D-J1-example"),
            pytest.param("0", "0", "0", id="zeros"),
            pytest.param("0", "80", "-80", id="nothing-received"),
            pytest.param("859.375", "800", "59.375", id="exact-decimals"),
        ],
    )
    def test_the_gain_is_proceeds_minus_cost(self, proceeds, cost, expected):
        """``proceeds - cost`` as a Decimal, no rounding. Before CP-7a: AttributeError (no returns.realized_gain)."""
        result = returns.realized_gain(Decimal(proceeds), Decimal(cost))

        assert isinstance(result, Decimal)
        assert result == Decimal(expected)

    @pytest.mark.parametrize(
        ("proceeds", "cost"),
        [
            pytest.param(None, "100", id="no-proceeds"),
            pytest.param("99", None, id="no-cost"),
            pytest.param(None, None, id="neither"),
            pytest.param(None, "0", id="no-proceeds-and-a-zero-cost"),
        ],
    )
    def test_an_unknown_leg_has_no_gain(self, proceeds, cost):
        """None, never the known leg alone read as the gain. Before CP-7a: AttributeError (no returns.realized_gain)."""
        assert returns.realized_gain(_dec(proceeds), _dec(cost)) is None

    def test_the_proceeds_come_first_and_the_cost_second(self):
        """The signature is ``realized_gain(proceeds, cost)``, by position and by name alike. Before CP-7a: AttributeError."""
        assert returns.realized_gain(Decimal("100"), Decimal("90")) == Decimal("10")
        assert returns.realized_gain(proceeds=Decimal("100"), cost=Decimal("90")) == Decimal("10")
        assert returns.realized_gain(cost=Decimal("90"), proceeds=Decimal("100")) == Decimal("10")


# =============================================================================
# A Dashboard holding's one-day columns (MF-A12, N92)
# =============================================================================

_PRICE_STEP = Decimal("0.0001")
_PERCENT_STEP = Decimal("0.01")
#: The caller's materiality guard on the previous position value (``get_summary``: ``abs(previous_position_value) > 0.01``).
_MATERIALITY = Decimal("0.01")


def _price_change_1d_today(prev_price_base: Decimal, current_price: Decimal) -> Decimal:
    """``get_summary``'s ``price_change_1d`` at HEAD ``efef5c876`` (``portfolio_service.py:745``), as written."""
    return ((current_price - prev_price_base) / prev_price_base).quantize(Decimal("0.0001"))


def _change_1d_percent_today(gain_loss_change_1d: Decimal, previous_position_value: Decimal) -> Decimal:
    """``get_summary``'s ``gain_loss_change_1d_percent`` at HEAD ``efef5c876`` (``portfolio_service.py:759``), as written."""
    return (gain_loss_change_1d / abs(previous_position_value) * 100).quantize(Decimal("0.01"))


def _price_change_1d_house(prev_price_base: Decimal, current_price: Decimal) -> Decimal | None:
    """The call site since MF-A12 (N92): the change over the size of the previous price, rounded for the column."""
    ratio = returns.change_ratio(current_price - prev_price_base, prev_price_base)
    return ratio.quantize(_PRICE_STEP) if ratio is not None else None


def _price_change_1d_by_price_return(prev_price_base: Decimal, current_price: Decimal) -> Decimal:
    """The alternative N92 set aside: ``price_return``'s ``end / start − 1``, rounded for the column."""
    return returns.price_return(prev_price_base, current_price).quantize(_PRICE_STEP)


def _change_1d_percent_house(gain_loss_change_1d: Decimal, previous_position_value: Decimal) -> Decimal | None:
    """The call site since MF-A12: the house's change ratio, as a percent rounded for the column."""
    ratio = returns.change_ratio(gain_loss_change_1d, previous_position_value)
    return (ratio * 100).quantize(_PERCENT_STEP) if ratio is not None else None


#: EUR/USD-like rates of 3 to 10 significant digits, as ``fx_rates.rate`` keeps them (NUMERIC(24, 10)).
_RATES = (Decimal("1.0876543219"), Decimal("0.8571428571"), Decimal("157.2345678"), Decimal("7.45893"), Decimal("1.08"))
#: The second leg of a route through a third currency (``fx/conversion.compute_chain_rate``: ``rate × (1 / rate)``).
_CHAIN_LEG = Decimal("1.0876543219")


def _convert(amount: Decimal, rate: Decimal, mode: str) -> Decimal:
    """``amount`` in the report currency, as ``fx/conversion.convert_bulk`` converts it: ``same`` (no conversion),
    ``times`` (the pair's base into its quote), ``over`` (the quote into the base), ``chain`` (times a chained rate)."""
    if mode == "same":
        return amount
    if mode == "times":
        return amount * rate
    if mode == "over":
        return amount / rate
    return amount * (rate * (Decimal("1") / _CHAIN_LEG))


def _routes() -> list[tuple[str, Decimal, Decimal]]:
    """(mode, the day before's rate, today's rate): no conversion; each rate the same on both days, by multiplication,
    division and a chain; and rates that moved between the two days."""
    routes = [("same", Decimal("1"), Decimal("1"))]
    routes += [(mode, rate, rate) for mode in ("times", "over", "chain") for rate in _RATES]
    routes += [(mode, before, after) for mode in ("times", "over") for before, after in itertools.pairwise(_RATES)]
    return routes


def _decimals(value: Decimal) -> int:
    return max(0, -value.as_tuple().exponent)


def _on_a_half(value: Decimal) -> bool:
    """``value`` is exactly half-way between two steps of the column: an odd number of half-steps."""
    halves = value / (_PRICE_STEP / 2)
    return halves == halves.to_integral_value() and int(halves) % 2 == 1


def _half_even(fraction: Fraction) -> Decimal:
    """An exact fraction rounded to the column's 4 decimals, half to even."""
    scaled = fraction * 10_000
    floor = scaled.numerator // scaled.denominator
    rest = scaled - floor
    if rest > Fraction(1, 2) or (rest == Fraction(1, 2) and floor % 2 == 1):
        floor += 1
    return Decimal(floor).scaleb(-4)


#: The day before's raw prices (≤ 10 decimals, as ``price_history.close`` keeps them) and the moves to today's.
_PREV_PRICES = ("0.0001234", "1.5", "12.3456", "98.51", "187.4523", "1234.5678901234", "65432.1")
_MOVES = ("0", "0.0123456", "-0.0345678", "0.1", "-0.5", "0.00004", "-0.00004", "2.5", "0.0157", "-0.0001")


def _price_grid(sign: int) -> list[tuple[str, Decimal, Decimal]]:
    """(case, the day before's price, today's price) in the report currency, every price of ``sign``: every raw price,
    move and route. Today's raw price is the day before's times (1 + move), cut to at most 10 decimals."""
    cases = []
    for prev_text, move, (mode, rate_before, rate_after) in itertools.product(_PREV_PRICES, _MOVES, _routes()):
        prev_raw = Decimal(prev_text) * sign
        current_raw = (prev_raw * (1 + Decimal(move))).quantize(Decimal(1).scaleb(-min(10, _decimals(prev_raw) + 2)))
        case = f"{prev_raw} -> {current_raw} ({mode} {rate_before} -> {rate_after})"
        cases.append((case, _convert(prev_raw, rate_before, mode), _convert(current_raw, rate_after, mode)))
    return cases


#: Raw prices whose moves by an odd number of half-steps of the column stay within 10 decimals.
_TIE_PREV_PRICES = ("1.00", "40.00", "200.00", "1234.5600", "0.5000")
#: Half-way returns: ±0.00005, ±0.00015, ±0.01225, ±0.01235, ±0.04995, ±0.12345, ±0.33335.
_HALF_POINTS = tuple(sign * (Decimal(k) + Decimal("0.5")) * _PRICE_STEP for k in (0, 1, 122, 123, 499, 1234, 3333) for sign in (1, -1))


def _tie_grid() -> list[tuple[str, str, Decimal, Decimal, Fraction]]:
    """(case, mode, the day before's price, today's price, exact return) for a positive raw price moved by exactly a
    half-way return, converted at one rate on both days by every route: the converted prices' exact return is the half."""
    cases = []
    for prev_text, half, (mode, rate_before, rate_after) in itertools.product(_TIE_PREV_PRICES, _HALF_POINTS, _routes()):
        if rate_before != rate_after:
            continue
        prev_raw = Decimal(prev_text)
        current_raw = prev_raw * (1 + half)
        exact = Fraction(current_raw) / Fraction(prev_raw) - 1
        assert exact == Fraction(half) and _decimals(current_raw) <= 10, f"precondition: an exact half-way move, {prev_raw} -> {current_raw}"
        cases.append((f"{prev_raw} -> {current_raw} ({mode} {rate_before})", mode, _convert(prev_raw, rate_before, mode), _convert(current_raw, rate_after, mode), exact))
    return cases


def _percent_grid() -> list[tuple[str, Decimal, Decimal]]:
    """(case, gain_loss_change_1d, previous_position_value): the edges of the guard and of a negative base, by hand;
    then as ``get_summary`` computes them — ``compute_holding_value`` of today's and the day before's converted prices —
    whenever the caller's guard lets the percent through."""
    edges = (
        ("0.011", "-0.011"),  # a negative base just over the guard: +100.00
        ("50", "-100"),  # a loss that shrinks: the change's sign
        ("-50", "-100"),
        ("0", "-100"),
        ("0.004", "0.0100000000000000000000000001"),  # just over the guard
        ("-0.0002", "0.0101"),
        ("0.005", "0.010000001"),
        ("0", "250"),
    )
    cases = [(f"edge {change} over {base}", Decimal(change), Decimal(base)) for change, base in edges]
    quantities = ("1", "12.5", "0.001", "10000", "0.123456789")
    for quantity, quote_base, prev_text, move, (mode, rate_before, rate_after), sign in itertools.product(quantities, (None, 100), _PREV_PRICES[1:6], _MOVES[:6], _routes()[::3], (1, -1)):
        prev_raw = Decimal(prev_text) * sign
        current_raw = (prev_raw * (1 + Decimal(move))).quantize(Decimal(1).scaleb(-min(10, _decimals(prev_raw) + 2)))
        previous_value = compute_holding_value(Decimal(quantity), _convert(prev_raw, rate_before, mode), quote_base)
        change = compute_holding_value(Decimal(quantity), _convert(current_raw, rate_after, mode), quote_base) - previous_value
        if abs(previous_value) > _MATERIALITY:
            cases.append((f"{quantity} x {prev_raw} -> {current_raw} /{quote_base} ({mode} {rate_before} -> {rate_after})", change, previous_value))
    return cases


class TestDayChangeColumnsFromTheHouse:
    """MF-A12 (N92): both columns from ``change_ratio``, against HEAD's two expressions (``*_today``). Parity guards, green
    on HEAD too (``returns.py`` did not change); the call site is locked in
    ``test_financial/test_summary_day_change_house.py``. A negative price is ``TestADayChangeOfANegativePrice``'s."""

    def test_the_percent_is_today_s_to_the_bit(self):
        """``change_ratio(change, base) × 100`` rounded to 2 decimals is HEAD's ``change / |base| * 100`` to the bit —
        digits, exponent and sign — on long-digit converted values, both signs of the change, a negative base and
        values just over the guard: the same two operations in the same order."""
        cases = _percent_grid()
        assert sum(base < 0 for _, _, base in cases) >= 100, "precondition: negative previous values"
        assert sum(len(base.as_tuple().digits) >= 20 for _, _, base in cases) >= 100, "precondition: long-digit converted values"
        assert sum(abs(base) < Decimal("0.02") for _, _, base in cases) >= 5, "precondition: values just over the guard"

        for case, change, base in cases:
            house = _change_1d_percent_house(change, base)
            today = _change_1d_percent_today(change, base)
            assert house is not None and house.as_tuple() == today.as_tuple(), f"{case}: house {house}, today {today}"

    def test_a_positive_price_change_is_today_s_to_the_bit(self):
        """On a positive price ``(c − p) / |p|`` is ``(c − p) / p``: the column is HEAD's to the bit — digits, exponent
        and sign — on every raw price, move (none included) and route of the grid (no conversion, a rate the same on
        both days by multiplication, division or a chain, rates that moved), and on every half-way move of the tie grid,
        where ``end / start − 1`` would not be (asserted: the grid has teeth against it)."""
        grid = [(case, prev, current) for case, prev, current in _price_grid(1)] + [(case, prev, current) for case, _, prev, current, _ in _tie_grid()]
        assert len(grid) >= 2_000, f"precondition: a big grid, got {len(grid)}"
        assert sum(len(prev.as_tuple().digits) >= 20 for _, prev, _ in grid) >= 500, "precondition: long-digit converted prices"
        assert sum(_price_change_1d_by_price_return(prev, current) != _price_change_1d_today(prev, current) for _, prev, current in grid) >= 100, "precondition: ties where end / start − 1 rounds the other way"

        for case, prev_price_base, current_price in grid:
            house = _price_change_1d_house(prev_price_base, current_price)
            today = _price_change_1d_today(prev_price_base, current_price)
            assert house is not None and house.as_tuple() == today.as_tuple(), f"{case}: house {house}, today {today}"

    def test_ties_are_today_s_where_end_over_start_minus_one_is_not(self):
        """Why N92 chose ``change_ratio``: on the tie grid (positive raw prices moved by exactly a half-way return, one
        rate on both days) the column is HEAD's everywhere, while ``price_return`` differs wherever a division brought
        28 digits of noise: there ``c / p`` rounded to 28 digits lands exactly on the half and is rounded half-even —
        the exact return's own rounding —, while ``(c − p) / p`` keeps the noise, within 1E-27 of the half, and goes the
        other way. Without a conversion, or converted exactly (a multiplication within 28 digits), none differs."""
        differences: Counter[str] = Counter()
        cases: Counter[str] = Counter()
        for case, mode, prev_price_base, current_price, exact in _tie_grid():
            cases[mode] += 1
            house = _price_change_1d_house(prev_price_base, current_price)
            today = _price_change_1d_today(prev_price_base, current_price)
            assert house is not None and house.as_tuple() == today.as_tuple(), f"{case}: house {house}, today {today}"
            alternative = _price_change_1d_by_price_return(prev_price_base, current_price)
            if alternative == today:
                continue
            differences[mode] += 1
            assert returns.price_return(prev_price_base, current_price) == Decimal(exact.numerator) / Decimal(exact.denominator), f"{case}: price_return off the half"
            assert abs((current_price - prev_price_base) / prev_price_base - Decimal(exact.numerator) / Decimal(exact.denominator)) < Decimal("1E-27"), f"{case}: HEAD far from the half"
            assert alternative == _half_even(exact) and abs(alternative - today) == _PRICE_STEP, f"{case}: price_return {alternative}, today {today}"

        assert cases["same"] and cases["times"] and differences["same"] == differences["times"] == 0, f"exact quotients never differ: {differences}"
        assert differences["over"] > 0 and differences["chain"] > 0, f"price_return differs under a division: {differences} of {cases}"

    @pytest.mark.parametrize(
        ("prev_raw", "current_raw", "rate_before", "rate_after", "today_text", "alternative_text", "today_raw_text"),
        [
            pytest.param("200.00", "202.47", "1.08", "1.08", "0.0123", "0.0124", "0.01234999999999999999999999980", id="rise-of-1.235%-at-one-rate"),
            pytest.param("200.00", "197.53", "1.1234", "1.1234", "-0.0123", "-0.0124", "-0.01234999999999999999999999996", id="fall-of-1.235%-at-one-rate"),
            pytest.param("200.00", "200.01", "1.16", "1.16", "0.0001", "0.0000", "0.00005000000000000000000000030001", id="rise-of-0.005%-at-one-rate"),
            pytest.param("10.00", "10.020687", "1.0500", "1.0537", "-0.0015", "-0.0014", "-0.001450000000000000000000000020", id="fall-of-0.145%-across-two-rates"),
        ],
    )
    def test_the_declared_tie(self, prev_raw, current_raw, rate_before, rate_after, today_text, alternative_text, today_raw_text):
        """USD prices converted into EUR (``amount / EUR-USD rate``) whose exact return is half-way between two steps of
        the column: the house's column is HEAD's, unrounded and rounded, text and exponent; ``price_return`` would have
        rounded the other way. The last case is a tie across two different rates."""
        prev_price_base = Decimal(prev_raw) / Decimal(rate_before)
        current_price = Decimal(current_raw) / Decimal(rate_after)
        exact = Fraction(current_raw) / Fraction(rate_after) / (Fraction(prev_raw) / Fraction(rate_before)) - 1
        assert _on_a_half(Decimal(exact.numerator) / Decimal(exact.denominator)), f"precondition: a half-way return, {exact}"

        assert str(returns.change_ratio(current_price - prev_price_base, prev_price_base)) == str((current_price - prev_price_base) / prev_price_base) == today_raw_text
        assert str(_price_change_1d_house(prev_price_base, current_price)) == str(_price_change_1d_today(prev_price_base, current_price)) == today_text
        assert str(_price_change_1d_by_price_return(prev_price_base, current_price)) == alternative_text

    @pytest.mark.parametrize(("quantity", "percent_text"), [("10", "1.23"), ("1", "1.23"), ("10000", "1.23"), ("12.5", "1.24")])
    def test_on_the_tie_row_the_columns_agree_for_some_quantities_only(self, quantity, percent_text):
        """200.00 → 202.47 USD at EUR/USD 1.08, a long position: ``price_change_1d`` is 0.0123 whatever the quantity, but
        the percent is the change of two converted VALUES, each rounded to 28 digits, whose noise depends on the
        quantity: 10 units give 1.23 / 1.23, 12.5 units 1.23 / 1.24 — as on HEAD, both columns being HEAD's. Row
        coherence at a tie is a property of the row, not a guarantee; the two columns stay within the 0.0101 two
        roundings allow. (A short position's percent has the opposite sign by design: |previous value| is its base.)"""
        prev_price_base, current_price = Decimal("200.00") / Decimal("1.08"), Decimal("202.47") / Decimal("1.08")
        previous_value = compute_holding_value(Decimal(quantity), prev_price_base, None)
        change = compute_holding_value(Decimal(quantity), current_price, None) - previous_value

        price_change = _price_change_1d_house(prev_price_base, current_price)
        percent = _change_1d_percent_house(change, previous_value)

        assert str(price_change) == "0.0123"
        assert str(percent) == str(_change_1d_percent_today(change, previous_value)) == percent_text
        assert abs(price_change * 100 - percent) <= Decimal("0.0101")

    def test_change_ratio_is_not_the_materiality_guard(self):
        """The guard ``|previous value| > 0.01`` is the caller's: the house answers on any non-zero base, 0.004 and
        −0.01 included."""
        assert returns.change_ratio(Decimal("0.0004"), Decimal("0.004")) == Decimal("0.1")
        assert returns.change_ratio(Decimal("0.0004"), Decimal("-0.01")) == Decimal("0.04")


class TestADayChangeOfANegativePrice:
    """N92's one value change: a negative price's change keeps the move's direction (``(c − p) / |p|``), as the percent
    column always did; HEAD's ``(c − p) / p`` gave it the opposite sign. Pure pins of the formula, green on HEAD too: the
    service's red is ``test_summary_day_change_house.py``'s ``test_a_negative_price_keeps_the_move_s_sign``."""

    @pytest.mark.parametrize(
        ("prev_price", "current_price", "house_text", "today_text"),
        [
            pytest.param("-10", "-12.5", "-0.2500", "0.2500", id="falls-further"),
            pytest.param("-10", "-5", "0.5000", "-0.5000", id="rises-toward-zero"),
            pytest.param("-37.5", "12.25", "1.3267", "-1.3267", id="turns-positive"),
            pytest.param("-0.0001234", "-0.0001301", "-0.0543", "0.0543", id="a-small-price-falls"),
        ],
    )
    def test_the_change_keeps_the_move_s_sign(self, prev_price, current_price, house_text, today_text):
        prev, current = Decimal(prev_price), Decimal(current_price)
        today = _price_change_1d_today(prev, current)
        assert str(today) == today_text, f"precondition: HEAD's value, got {today}"

        house = _price_change_1d_house(prev, current)

        assert str(house) == house_text, f"{prev} -> {current}: expected {house_text} (the move's sign), got {house}; HEAD gave {today}"

    def test_every_negative_price_change_is_today_s_with_the_sign_flipped(self):
        """On the negative half of the grid (every raw price, move and route) the house's column is HEAD's with its sign
        flipped — ``(c − p) / (−p)`` is ``−((c − p) / p)`` exactly, and half-even is symmetric —, digits and exponent
        kept, a rounded-away zero's sign included."""
        cases = _price_grid(-1)
        assert all(prev < 0 for _, prev, _ in cases) and len(cases) >= 1_000, "precondition: negative prices"

        for case, prev_price_base, current_price in cases:
            house = _price_change_1d_house(prev_price_base, current_price)
            today = _price_change_1d_today(prev_price_base, current_price)
            assert house is not None and house.as_tuple() == today.copy_negate().as_tuple(), f"{case}: house {house}, HEAD {today}"

    @pytest.mark.parametrize(("price", "today_text"), [("-10", "-0.0000"), ("-187.4523", "-0.0000"), ("10", "0.0000")])
    def test_an_unmoved_price_reads_a_plain_zero(self, price, today_text):
        """A price that did not move: ``0 / |p|`` is a plain zero, ``"0.0000"`` in the JSON. HEAD's ``0 / p`` carried a
        negative price's sign, ``"-0.0000"``: equal as numbers, not as text (the CP-4a rule above: the sign of a zero is
        not part of the contract)."""
        start = Decimal(price)
        house, today = _price_change_1d_house(start, start), _price_change_1d_today(start, start)

        assert house == today == 0
        assert str(today) == today_text, f"precondition: HEAD's text, got {today}"
        assert str(house) == "0.0000", f"HEAD said {today}"

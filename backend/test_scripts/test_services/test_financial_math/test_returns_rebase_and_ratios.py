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

Pure: no database, no server, no network.
"""

from __future__ import annotations

import dataclasses
import itertools
from datetime import date
from decimal import Decimal

import pytest

from backend.app.services.financial_math import returns
from backend.app.services.financial_math.returns import CashFlowInput, NAVSnapshot

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

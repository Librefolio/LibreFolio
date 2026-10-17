"""
MF-P (workstream MF, lot P, part 1 — R17): the Dashboard's day change, from the engine's daily states.

Module under test: ``backend/app/services/financial_math/portfolio/period.py`` —
``day_change(daily_states, as_of) -> DayChange(pnl_change, vs_total_pnl, vs_nav) | None``:

* the two states are ``state_as_of(daily_states, as_of)`` and ``state_as_of(daily_states, as_of − 1 calendar day)``:
  the last state dated on or before each day. The day before is the calendar day — on a Monday, Sunday's state —
  never the previous element of the list, nor the previous trading day;
* ``pnl_change`` = end.total_pnl − previous.total_pnl, exact;
* ``vs_total_pnl`` = ``returns.change_ratio(pnl_change, previous.total_pnl)`` and ``vs_nav`` =
  ``returns.change_ratio(pnl_change, previous.nav_value)``: ``change / |base|``, the change's sign whatever the base's,
  None on a zero base, unrounded (fractions: 0.05 = 5 %);
* None when either state is missing: a portfolio born on ``as_of`` has no day before.

What the frontend computes today (``frontend/src/lib/features/dashboard/KpiSection.svelte:79-135``): the last point of the
report's ``history`` minus the point before it, divided by |that point's total_pnl| and by |its nav_value|, ×100. The
history is the period's slice, so its previous point is whatever the series holds before the last one.

The engine writes one state per calendar day (``DailyStateBuilder``: a day with nothing new repeats the day before's
figures), so on a Monday Sunday's state carries Friday's figures, or Saturday's when something moved over the weekend
(a quote on a Saturday, a fee). The weekend cases below give Sunday figures of its own, so a function that took Friday
(the previous trading day) or Saturday comes out wrong. A list with gaps (no weekend state) is read the same way: the
day before is the last state on or before it.

States are real ``DailyPortfolioState`` objects. ``day_change`` reads their date, total P&L and NAV; every other figure
holds a poison value, so a figure computed from the wrong field (the NAV less the capital, the market value…) comes
out wrong.

Red by absence on HEAD (c2feebaa8): ``period.py`` exists there, without ``day_change``; the module is imported and the
name read while each test runs, so the file collects and every test fails with AttributeError
(``module ... has no attribute 'day_change'``).

Pure: no database, no server, no network.
"""

from __future__ import annotations

import importlib
from datetime import date, timedelta
from decimal import Decimal
from types import ModuleType
from typing import Any

import pytest

from backend.app.services.financial_math.portfolio.models import DailyPortfolioState

PERIOD_MODULE = "backend.app.services.financial_math.portfolio.period"

D = Decimal

WEDNESDAY = date(2025, 1, 29)
THURSDAY = date(2025, 1, 30)
FRIDAY = date(2025, 1, 31)
SATURDAY = date(2025, 2, 1)
SUNDAY = date(2025, 2, 2)
MONDAY = date(2025, 2, 3)

POISON = D("-987654.321")
# Figures of a daily state the day change never reads.
_POISONED_FIELDS = (
    "cash_value",
    "market_value",
    "broker_nav_value",
    "in_transit_cash_value",
    "in_transit_asset_market_value",
    "in_transit_market_value",
    "open_cost_basis",
    "in_transit_asset_cost_basis",
    "in_transit_book_value",
    "book_value",
    "unrealized_gain_loss",
    "external_cash_flow",
    "cumulative_external_cash_flow",
    "book_asset_like",
    "cash_from_contributed_capital",
    "cash_from_generated_returns",
)


def _period() -> ModuleType:
    """``financial_math/portfolio/period.py``, imported when a test runs."""
    return importlib.import_module(PERIOD_MODULE)


def _day_change(daily_states: list[DailyPortfolioState], as_of: date) -> Any:
    """``period.day_change``, read when the test runs: until MF-P it does not exist."""
    return _period().day_change(daily_states, as_of)


def _state(day: date, *, pnl: str, nav: str) -> DailyPortfolioState:
    """A daily state with its total P&L and NAV; every other figure is POISON."""
    return DailyPortfolioState(date=day, total_pnl=D(pnl), nav_value=D(nav), **dict.fromkeys(_POISONED_FIELDS, POISON))


def _figures(result: Any) -> tuple[Decimal, Decimal | None, Decimal | None]:
    """(pnl_change, vs_total_pnl, vs_nav) of a DayChange."""
    assert result is not None, "expected a day change, got None"
    return result.pnl_change, result.vs_total_pnl, result.vs_nav


def _ratio(numerator: str, denominator: str) -> Decimal:
    """The context's quotient of the two figures: what an unrounded ratio is."""
    return D(numerator) / D(denominator)


# =============================================================================
# The change from the day before
# =============================================================================


class TestTheChangeFromTheDayBefore:
    def test_a_weekday(self):
        """Thursday: P&L 100.05 on a NAV of 10100.05; Friday: 130.10. Change +30.05, exactly; 30.05 / 100.05 of the
        P&L and 30.05 / 10100.05 of the NAV, unrounded."""
        states = [_state(WEDNESDAY, pnl="90", nav="10090"), _state(THURSDAY, pnl="100.05", nav="10100.05"), _state(FRIDAY, pnl="130.10", nav="10130.10")]

        change, vs_total_pnl, vs_nav = _figures(_day_change(states, FRIDAY))

        assert change == D("30.05")
        assert vs_total_pnl == _ratio("30.05", "100.05")
        assert vs_nav == _ratio("30.05", "10100.05")
        assert vs_nav != vs_nav.quantize(D("0.000001")), f"rounded: {vs_nav}"
        assert all(isinstance(figure, Decimal) for figure in (change, vs_total_pnl, vs_nav))

    def test_a_monday_after_a_quiet_weekend(self):
        """Daily states, the weekend carrying Friday's figures (P&L 130, NAV 10130); Monday 200: the change is Monday
        − Sunday, +70; 70 / 130 and 70 / 10130."""
        states = [
            _state(FRIDAY, pnl="130", nav="10130"),
            _state(SATURDAY, pnl="130", nav="10130"),
            _state(SUNDAY, pnl="130", nav="10130"),
            _state(MONDAY, pnl="200", nav="10200"),
        ]

        assert _figures(_day_change(states, MONDAY)) == (D("70"), _ratio("70", "130"), _ratio("70", "10130"))

    def test_a_monday_reads_sunday_not_the_last_trading_day(self):
        """Something moved over the weekend (a quote on Saturday, another on Sunday): Friday 130, Saturday 150,
        Sunday 160, Monday 200. The change is Monday − Sunday, +40, 40 / 160 = 0.25 and 40 / 10160 — not Monday −
        Friday (+70) nor Monday − Saturday (+50)."""
        states = [
            _state(FRIDAY, pnl="130", nav="10130"),
            _state(SATURDAY, pnl="150", nav="10150"),
            _state(SUNDAY, pnl="160", nav="10160"),
            _state(MONDAY, pnl="200", nav="10200"),
        ]

        assert _figures(_day_change(states, MONDAY)) == (D("40"), D("0.25"), _ratio("40", "10160"))

    def test_a_list_with_gaps_reads_the_last_state_on_or_before_the_day_before(self):
        """No weekend state in the list: the day before Monday is Sunday, read as the last state dated on or before it —
        Friday's in the first list (+70), Saturday's in the second (+50, not Monday − Friday)."""
        friday_monday = [_state(THURSDAY, pnl="100", nav="10100"), _state(FRIDAY, pnl="130", nav="10130"), _state(MONDAY, pnl="200", nav="10200")]
        with_saturday = [_state(FRIDAY, pnl="130", nav="10130"), _state(SATURDAY, pnl="150", nav="10150"), _state(MONDAY, pnl="200", nav="10200")]

        assert _figures(_day_change(friday_monday, MONDAY)) == (D("70"), _ratio("70", "130"), _ratio("70", "10130"))
        assert _figures(_day_change(with_saturday, MONDAY)) == (D("50"), _ratio("50", "150"), _ratio("50", "10150"))

    def test_as_of_between_two_states_compares_the_same_state(self):
        """A Sunday in a list without weekend states: both days read Friday's state, the change is 0 (a zero change
        has a ratio of 0, not None)."""
        states = [_state(THURSDAY, pnl="100", nav="10100"), _state(FRIDAY, pnl="130", nav="10130"), _state(MONDAY, pnl="200", nav="10200")]

        assert _figures(_day_change(states, SUNDAY)) == (D("0"), D("0"), D("0"))


# =============================================================================
# The sign: the change's, whatever the base's
# =============================================================================


class TestTheSignOfTheChange:
    @pytest.mark.parametrize(
        ("today", "change"),
        [("-50", "50"), ("-150", "-50")],
        ids=["loss-shrinks", "loss-deepens"],
    )
    def test_on_a_loss_the_day_before(self, today, change):
        """Thursday P&L −100 (NAV 9900). Friday −50: +50, +0.5 of the P&L; Friday −150: −50, −0.5. Never the sign of
        the base: a loss that shrinks is a rise."""
        states = [_state(THURSDAY, pnl="-100", nav="9900"), _state(FRIDAY, pnl=today, nav=str(D("10000") + D(today)))]

        assert _figures(_day_change(states, FRIDAY)) == (D(change), _ratio(change, "100"), _ratio(change, "9900"))

    def test_on_a_nav_below_zero_the_day_before(self):
        """Thursday NAV −200 (a leveraged broker), P&L −1200; Friday NAV −100, P&L −1100: +100, 100 / 1200 of the
        P&L and 100 / 200 = +0.5 of the NAV."""
        states = [_state(THURSDAY, pnl="-1200", nav="-200"), _state(FRIDAY, pnl="-1100", nav="-100")]

        assert _figures(_day_change(states, FRIDAY)) == (D("100"), _ratio("100", "1200"), D("0.5"))


# =============================================================================
# No base, no day before
# =============================================================================


class TestNoBaseOrNoDayBefore:
    def test_no_ratio_of_a_zero_pnl_the_day_before(self):
        """Bought on Thursday at the day's price: P&L 0 on a NAV of 10000; Friday 130. The change is known and so is
        its share of the NAV, 0.013; its share of a zero P&L is None."""
        states = [_state(THURSDAY, pnl="0", nav="10000"), _state(FRIDAY, pnl="130", nav="10130")]

        assert _figures(_day_change(states, FRIDAY)) == (D("130"), None, D("0.013"))

    def test_no_ratio_of_a_zero_nav_the_day_before(self):
        """Everything lost on Thursday (NAV 0, P&L −1000); Friday a recovery to 100: +100, 0.1 of the P&L, no share of
        a zero NAV."""
        states = [_state(THURSDAY, pnl="-1000", nav="0"), _state(FRIDAY, pnl="-900", nav="100")]

        assert _figures(_day_change(states, FRIDAY)) == (D("100"), D("0.1"), None)

    def test_none_for_a_portfolio_born_on_as_of(self):
        """The first state is Friday's: there is no Thursday, so no change at all — not a change of 130 from nothing."""
        assert _day_change([_state(FRIDAY, pnl="130", nav="10130")], FRIDAY) is None
        assert _day_change([_state(FRIDAY, pnl="130", nav="10130"), _state(MONDAY, pnl="200", nav="10200")], FRIDAY) is None

    def test_none_before_the_first_state_or_without_states(self):
        assert _day_change([_state(FRIDAY, pnl="130", nav="10130")], FRIDAY - timedelta(days=3)) is None
        assert _day_change([], FRIDAY) is None

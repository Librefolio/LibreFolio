"""
CP-4c (workstream J, U4b): the period P&L and the WAC preview's unit costs move into the home.

Modules under test:

* ``backend/app/services/financial_math/portfolio/period.py``, new. What ``portfolio_service.py``
  computes in place today:

  - ``state_as_of(daily_states, as_of)``: ``_daily_state_as_of`` (``:367-381``);
  - ``period_boundaries(daily_states, date_from, as_of) -> PeriodBoundaries | None``: the start and
    end states of a period, a rule written twice, in ``_compute_period_summary_metrics``
    (``:586-660``) and in ``_unrealized_breakdown_rows`` (``:325-364``);
  - ``period_pnl(daily_states, date_from, as_of) -> PeriodPnl | None``: the eight figures of
    ``_compute_period_summary_metrics``;
  - ``period_other_result(pnl, ugl_delta, realized, income, fees_taxes)``: the residual that closes
    the period identity, ``period_other_result_val`` in ``get_summary`` (``:1049``).

* ``backend/app/services/financial_math/average_cost.py``: ``MovementUnitCost`` and
  ``movement_unit_costs(steps)``, the unit cost of each movement, which the WAC preview computes in
  ``_wac_qualifying_txs`` today (``:240-272``).

No value changes (plan, «CP-4 — U4b + V-11», P1 and C1). Every function is checked against a copy
of today's code kept here as written (the ``*_today`` functions), on a grid of cases; the two
copies of the boundary rule are first checked against each other. Figures are compared with their
exponent and the sign of their zeros (``str()``), as the native-cash golden compares them.

Red by absence until CP-4c: ``period.py`` is imported while a test runs (``_period()``) and the new
names of ``average_cost`` are read as attributes of the module, so the file collects today and each
test fails on the missing module or name, after the checks of today's code it makes first.

J-14 (the rest of it), no value change either: the period identity's residual and its tolerance
move into ``period.py`` too.

* ``period_identity_residual(pnl, ugl_delta, realized, income, fees_taxes, other_result)``:
  ``pnl − (ugl_delta + realized + income − fees_taxes + other_result)``, in that association. It
  replaces the two copies the AI Export's reconciliation wrote in line at ``e6d3e61e0``,
  ``portfolio_financial._build_portfolio_reconciliation`` (``:491``) and
  ``broker_financial._build_broker_reconciliation`` (``:432``); its oracle is
  ``_identity_residual_today``.
* ``is_reconciled(residual)``: ``abs(residual) < CONVERSION_DUST``, the constant of ``native_cash``
  read where it lives. It replaces the tolerance those two components applied in line (``:495`` and
  ``:436``); its oracle is ``_reconciled_today``.
* ``get_positions_contribution`` (``portfolio_service.py:1854``) wrote ``period_other_result``'s
  expression in line a second time; it now calls the function, in the same order. Its copy is
  ``_positions_other_result_today``.

The association is the point. Amounts converted into the report currency carry Decimal's 28
significant digits (``CONVERTED``), and on them each other way of writing the sum rounds differently,
in the last digit or in the exponent: the grids hold such amounts and first prove they tell every
alternative from today's, and ``TestPeriodIdentityResidual`` keeps two concrete cases with the figure
each alternative gives. Red by absence until J-14, like the rest: the new names are read off
``_period()`` after the checks of today's code.

States are real ``DailyPortfolioState`` objects. The period rule reads only their date, NAV, book
value, market value, open cost basis and cumulative external cash flow (the breakdown also reads
``unrealized_by_currency``); every other figure holds a poison value, so a figure read from the
wrong field comes out wrong. Within a list every state has its own NAV, none of them zero, and its
own market value minus cost, so the figures of today's summary name the states it used. The unit
costs come from real timelines built by ``compute_average_costs`` as the WAC preview builds them
(report EUR, ``asset_leg=False``), with ``convert_bulk`` replaced by a fixed-rate double.

Pure: no database, no server, no network.
"""

from __future__ import annotations

import bisect
import dataclasses
import importlib
import itertools
from datetime import date
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from backend.app.schemas.common import Currency
from backend.app.schemas.portfolio import UnrealizedBreakdownRow
from backend.app.services.financial_math import average_cost, native_cash
from backend.app.services.financial_math.average_cost import CostEffect, CostMovement, CostMovementKind, CostPosition, CostStep, compute_average_costs
from backend.app.services.financial_math.native_cash import CONVERSION_DUST
from backend.app.services.financial_math.portfolio.models import DailyPortfolioState, UnrealizedSplit

PERIOD_MODULE = "backend.app.services.financial_math.portfolio.period"

D1 = date(2025, 3, 1)
D2 = date(2025, 3, 2)
D3 = date(2025, 3, 3)
D4 = date(2025, 3, 4)
D5 = date(2025, 3, 5)
D6 = date(2025, 3, 6)
D7 = date(2025, 3, 7)
D8 = date(2025, 3, 8)
D9 = date(2025, 3, 9)
DAYS = (D1, D2, D3, D4, D5, D6, D7, D8, D9)

REPORT = "EUR"


def _period() -> ModuleType:
    """``financial_math/portfolio/period.py``, imported when a test runs: until CP-4c it does not exist."""
    return importlib.import_module(PERIOD_MODULE)


def _same_decimal(actual: Any, expected: Any) -> bool:
    """Same type and same text: value, exponent and sign of zero (None matches None only)."""
    return type(actual) is type(expected) and str(actual) == str(expected)


# =============================================================================
# Today's code, copied as written: the characterization oracles
# =============================================================================


def _daily_state_as_of_today(daily_states: list[Any], as_of: date) -> Any | None:
    """``_daily_state_as_of``, ``portfolio_service.py:367-381``, as written."""
    if not daily_states:
        return None
    dates = [s.date for s in daily_states]
    idx = bisect.bisect_right(dates, as_of) - 1
    if idx < 0:
        return None
    return daily_states[idx]


def _summary_metrics_today(engine_result: Any, date_from: date | None, as_of: date) -> dict[str, Decimal | None]:
    """``PortfolioService._compute_period_summary_metrics``, ``portfolio_service.py:586-660``, as written
    (its ``_daily_state_as_of`` is the copy above)."""
    metrics: dict[str, Decimal | None] = {
        "period_nav_start_val": None,
        "period_net_flows_val": None,
        "period_pnl_val": None,
        "period_ugl_start": None,
        "period_ugl_end": None,
        "period_ugl_delta": None,
        "period_book_value_start_val": None,
        "period_market_value_start_val": None,
    }
    daily_states = getattr(engine_result, "daily_states", None) or []
    if len(daily_states) < 2:
        return metrics

    zero = Decimal("0")
    end_state = _daily_state_as_of_today(daily_states, as_of)
    if end_state is None:
        return metrics
    period_ugl_end = end_state.market_value - end_state.open_cost_basis

    if date_from:
        pre_states = [s for s in daily_states if s.date <= date_from]
        if pre_states:
            start_state = pre_states[-1]
            period_nav_start_val = start_state.nav_value
            period_book_value_start_val = start_state.book_value
            period_market_value_start_val = start_state.market_value
            period_ugl_start = start_state.market_value - start_state.open_cost_basis
            period_net_flows_val = end_state.cumulative_external_cash_flow - start_state.cumulative_external_cash_flow
        else:
            period_nav_start_val = zero
            period_book_value_start_val = zero
            period_market_value_start_val = zero
            period_ugl_start = zero
            period_net_flows_val = end_state.cumulative_external_cash_flow
    else:
        period_nav_start_val = zero
        period_book_value_start_val = zero
        period_market_value_start_val = zero
        period_ugl_start = zero
        period_net_flows_val = end_state.cumulative_external_cash_flow

    period_pnl_val = end_state.nav_value - period_nav_start_val - period_net_flows_val
    period_ugl_delta = period_ugl_end - period_ugl_start

    metrics.update(
        {
            "period_nav_start_val": period_nav_start_val,
            "period_net_flows_val": period_net_flows_val,
            "period_pnl_val": period_pnl_val,
            "period_ugl_start": period_ugl_start,
            "period_ugl_end": period_ugl_end,
            "period_ugl_delta": period_ugl_delta,
            "period_book_value_start_val": period_book_value_start_val,
            "period_market_value_start_val": period_market_value_start_val,
        }
    )
    return metrics


def _breakdown_rows_today(engine_result: Any, date_from: date | None, as_of: date, currency: str) -> list[UnrealizedBreakdownRow]:
    """``_unrealized_breakdown_rows``, ``portfolio_service.py:325-364``, as written (its
    ``_daily_state_as_of`` is the copy above)."""
    daily_states = getattr(engine_result, "daily_states", None) or []
    if len(daily_states) < 2:
        return []
    end_state = _daily_state_as_of_today(daily_states, as_of)
    if end_state is None:
        return []
    start_state = None
    if date_from:
        pre_states = [state for state in daily_states if state.date <= date_from]
        start_state = pre_states[-1] if pre_states else None
    end_parts = end_state.unrealized_by_currency
    start_parts = start_state.unrealized_by_currency if start_state is not None else {}
    currencies = sorted(set(end_parts) | set(start_parts), key=lambda code: (code != currency, code))

    zero = Decimal("0")

    def delta(code: str, kind: str) -> tuple[Decimal, Decimal, Decimal]:
        end_value = getattr(end_parts[code], kind) if code in end_parts else zero
        start_value = getattr(start_parts[code], kind) if code in start_parts else zero
        return start_value, end_value, end_value - start_value

    rows: list[UnrealizedBreakdownRow] = []
    for code in currencies:
        rows.append(UnrealizedBreakdownRow(kind="asset", asset_currency=code, period_delta=Currency(code=currency, amount=delta(code, "asset")[2])))
    for code in currencies:
        if code != currency:
            rows.append(UnrealizedBreakdownRow(kind="fx", asset_currency=code, period_delta=Currency(code=currency, amount=delta(code, "fx")[2])))
    for code in currencies:
        start_value, end_value, change = delta(code, "unsplit")
        if start_value != zero or end_value != zero:
            rows.append(UnrealizedBreakdownRow(kind="unsplit", asset_currency=code, period_delta=Currency(code=currency, amount=change)))
    return rows


def _other_result_today(period_pnl_val: Decimal, period_ugl_delta: Decimal, period_realized_val: Decimal, period_income_val: Decimal, period_fees_taxes_val: Decimal) -> Decimal:
    """``get_summary``'s residual that closes the period identity, ``portfolio_service.py:1049``, as written."""
    return period_pnl_val - period_ugl_delta - period_realized_val - period_income_val + period_fees_taxes_val


def _positions_other_result_today(period_pnl_total: Decimal, period_ugl_delta: Decimal, total_realized: Decimal, total_income: Decimal, total_fees: Decimal) -> Decimal:
    """``get_positions_contribution``'s term that closes the period identity, ``portfolio_service.py:1854`` at
    ``e6d3e61e0``, as written (J-14)."""
    return period_pnl_total - period_ugl_delta - total_realized - total_income + total_fees


def _identity_residual_today(pnl: Decimal, ugl_delta: Decimal, realized: Decimal, income: Decimal, fees_taxes: Decimal, other_result: Decimal) -> Decimal:
    """What the AI Export's reconciliation left of the identity, ``portfolio_financial.py:491`` and
    ``broker_financial.py:432`` at ``e6d3e61e0``, as written: each ``summary.period_*.amount`` is named
    by its argument (J-14)."""
    return pnl - (ugl_delta + realized + income - fees_taxes + other_result)


def _reconciled_today(residual_amount: Decimal) -> bool:
    """The tolerance both components applied to that residual, ``portfolio_financial.py:495`` and
    ``broker_financial.py:436`` at ``e6d3e61e0``, as written (J-14)."""
    return abs(residual_amount) < CONVERSION_DUST


def _unit_costs_today(steps: tuple[CostStep, ...]) -> list[tuple[Decimal, Decimal | None]]:
    """``_wac_qualifying_txs``, ``portfolio_service.py:240-272``: its loop and arithmetic as written.

    Only the ``WACQualifyingTX`` row it builds is cut down to the two figures that move into the
    home: ``(unit_cost, original_unit_cost)``.
    """
    rows: list[tuple[Decimal, Decimal | None]] = []
    previous_wac = Decimal("0")
    for step in steps:
        movement = step.movement
        running_wac = step.unit_cost_report
        if step.effect == CostEffect.ADD:
            unit_cost = step.cost_report_change / movement.quantity
        elif step.effect == CostEffect.REDUCE:
            unit_cost = previous_wac
        elif step.effect == CostEffect.SPLIT_RESCALE:
            unit_cost = running_wac
        else:
            unit_cost = Decimal("0")
        conversion = step.conversion
        rows.append((unit_cost, conversion.original_amount / movement.quantity if conversion else None))
        previous_wac = running_wac
    return rows


# =============================================================================
# Daily states and the period grid
# =============================================================================

POISON = Decimal("-987654.321")
# Figures of a daily state the period rule never reads.
_POISONED_FIELDS = (
    "cash_value",
    "broker_nav_value",
    "in_transit_cash_value",
    "in_transit_asset_market_value",
    "in_transit_market_value",
    "in_transit_asset_cost_basis",
    "in_transit_book_value",
    "unrealized_gain_loss",
    "external_cash_flow",
    "book_asset_like",
    "cash_from_contributed_capital",
    "cash_from_generated_returns",
    "total_pnl",
)


def _state(day: date, *, nav: str, book: str, market: str, cost: str, flows: str, asset_part: str) -> DailyPortfolioState:
    """A daily state with the figures the period rule reads; its unrealized gain lies all in the
    report currency (``asset_part``, fx and unsplit at zero); every other figure is POISON."""
    return DailyPortfolioState(
        date=day,
        nav_value=Decimal(nav),
        book_value=Decimal(book),
        market_value=Decimal(market),
        open_cost_basis=Decimal(cost),
        cumulative_external_cash_flow=Decimal(flows),
        unrealized_by_currency={REPORT: UnrealizedSplit(asset=Decimal(asset_part))},
        **dict.fromkeys(_POISONED_FIELDS, POISON),
    )


# One state every other day, so a date can fall on a state, between two, before the first or after
# the last. Market value − cost: 100.30, 149.5, 155.125, 200.25.
FOUR = (
    _state(D2, nav="1000.10", book="900.00", market="800.40", cost="700.10", flows="1000.00", asset_part="1"),
    _state(D4, nav="1180.25", book="950.5", market="870", cost="720.5", flows="1100", asset_part="10"),
    _state(D6, nav="1250.5", book="1010.75", market="915.125", cost="760", flows="1150.5", asset_part="100"),
    _state(D8, nav="1300", book="1100", market="990.5", cost="790.25", flows="1200.25", asset_part="1000"),
)
# Two states on D4 (the engine never writes two states for one day): the rule takes the last one.
REPEATED = (
    _state(D2, nav="2000.10", book="1900", market="1800.40", cost="1700.10", flows="2000", asset_part="1"),
    _state(D4, nav="2180.25", book="1950.5", market="1870", cost="1720.5", flows="2100", asset_part="10"),
    _state(D4, nav="2185.75", book="1955", market="1880.5", cost="1722", flows="2150", asset_part="100"),
    _state(D6, nav="2250.5", book="2010.75", market="1915.125", cost="1760", flows="2200.5", asset_part="1000"),
)
STATE_LISTS = {"four-states": FOUR, "two-states": FOUR[:2], "one-state": FOUR[:1], "no-state": (), "repeated-date": REPEATED}
DATE_FROMS = (None, D1, D2, D3, D4, D5, D7, D8, D9)
AS_OFS = (D1, D2, D3, D4, D5, D8, D9)

# PeriodPnl field -> key of today's metrics dict.
PNL_FIELDS = {
    "nav_start": "period_nav_start_val",
    "net_flows": "period_net_flows_val",
    "pnl": "period_pnl_val",
    "ugl_start": "period_ugl_start",
    "ugl_end": "period_ugl_end",
    "ugl_delta": "period_ugl_delta",
    "book_value_start": "period_book_value_start_val",
    "market_value_start": "period_market_value_start_val",
}


def _grid():
    """Every (case, states, date_from, as_of) of the period grid; ``states`` a fresh list, as the engine gives."""
    for (name, states), date_from, as_of in itertools.product(STATE_LISTS.items(), DATE_FROMS, AS_OFS):
        yield f"{name}, date_from={date_from}, as_of={as_of}", list(states), date_from, as_of


def _states_used_by_summary_today(states: list[DailyPortfolioState], metrics: dict[str, Decimal | None]) -> tuple[DailyPortfolioState | None, DailyPortfolioState] | None:
    """The (start, end) states today's summary used, named by its figures; None when it computed nothing.

    No state has a zero NAV, so a zero start NAV means no start state; the end is the one state
    whose market value − cost is the period's closing unrealized.
    """
    if all(value is None for value in metrics.values()):
        return None
    starts = [state for state in states if state.nav_value == metrics["period_nav_start_val"]]
    ends = [state for state in states if state.market_value - state.open_cost_basis == metrics["period_ugl_end"]]
    assert len(starts) <= 1 and len(ends) == 1, "each figure must name one state of the list"
    return (starts[0] if starts else None), ends[0]


def _rows_between(boundaries: tuple[DailyPortfolioState | None, DailyPortfolioState] | None) -> list[UnrealizedBreakdownRow]:
    """The rows today's breakdown gives between two of these states: one asset row in the report
    currency (no fx row, no unsplit row), none without a period."""
    if boundaries is None:
        return []
    start, end = boundaries
    start_asset = start.unrealized_by_currency[REPORT].asset if start is not None else Decimal("0")
    return [UnrealizedBreakdownRow(kind="asset", asset_currency=REPORT, period_delta=Currency(code=REPORT, amount=end.unrealized_by_currency[REPORT].asset - start_asset))]


def _situation(boundaries: tuple[DailyPortfolioState | None, DailyPortfolioState] | None) -> str:
    """Which branch of the rule a case reaches."""
    if boundaries is None:
        return "no-period"
    start, end = boundaries
    if start is None:
        return "no-start"
    if start is end:
        return "start-is-end"
    return "start-before-end" if start.date < end.date else "start-after-end"


# =============================================================================
# A. financial_math/portfolio/period.py
# =============================================================================


class TestStateAsOf:
    """``state_as_of``: the last state dated on or before the day; None before the first or without states."""

    def test_the_last_state_on_or_before_the_day(self):
        state_as_of = _period().state_as_of
        states = list(FOUR)

        assert state_as_of(states, D2) is FOUR[0], "on the first state"
        assert state_as_of(states, D4) is FOUR[1], "on a state"
        assert state_as_of(states, D5) is FOUR[1], "between two states: the earlier"
        assert state_as_of(states, D9) is FOUR[3], "after the last state"

    def test_none_before_the_first_state_or_without_states(self):
        state_as_of = _period().state_as_of

        assert state_as_of(list(FOUR), D1) is None
        assert state_as_of([], D5) is None

    def test_matches_today(self):
        """Characterization: the very state today's ``_daily_state_as_of`` returns, on every list and day
        (two states on one day: the last of them)."""
        cases = [(f"{name}, as_of={as_of}", list(states), as_of) for (name, states), as_of in itertools.product(STATE_LISTS.items(), DAYS)]
        state_as_of = _period().state_as_of

        for case, states, as_of in cases:
            assert state_as_of(states, as_of) is _daily_state_as_of_today(states, as_of), case


class TestPeriodBoundaries:
    """``period_boundaries``: ``end`` = the state at ``as_of``; ``start`` = the last state on or before
    ``date_from``, None without ``date_from`` or before the first state; None for the whole result
    with fewer than two states or no state on or before ``as_of``."""

    def test_the_start_is_the_last_state_on_or_before_date_from(self):
        boundaries = _period().period_boundaries(list(FOUR), D5, D9)

        assert boundaries.start is FOUR[1]
        assert boundaries.end is FOUR[3]

    @pytest.mark.parametrize("date_from", [None, D1], ids=["no-date-from", "before-the-first-state"])
    def test_no_start_state_without_date_from_or_before_the_first_state(self, date_from):
        boundaries = _period().period_boundaries(list(FOUR), date_from, D5)

        assert boundaries is not None
        assert boundaries.start is None
        assert boundaries.end is FOUR[1]

    def test_none_with_fewer_than_two_states_or_without_an_end(self):
        period_boundaries = _period().period_boundaries

        assert period_boundaries([], None, D5) is None
        assert period_boundaries(list(FOUR[:1]), None, D5) is None, "one state is no period, even with a state on as_of"
        assert period_boundaries(list(FOUR), None, D1) is None, "as_of before every state"

    def test_matches_both_copies_of_today(self):
        """Characterization against both copies of the rule.

        First on today's code alone: on every case of the grid, the states named by the figures of
        today's summary give exactly the rows of today's breakdown, so the two copies apply one rule;
        and the grid reaches every branch of it. Then the function returns those very states.
        """
        cases = []
        situations = set()
        for case, states, date_from, as_of in _grid():
            engine_result = SimpleNamespace(daily_states=states)
            used = _states_used_by_summary_today(states, _summary_metrics_today(engine_result, date_from, as_of))
            rows = _breakdown_rows_today(engine_result, date_from, as_of, REPORT)
            assert rows == _rows_between(used), f"today's two copies disagree: {case}"
            situations.add(_situation(used))
            cases.append((case, states, date_from, as_of, used, rows))
        assert situations == {"no-period", "no-start", "start-before-end", "start-is-end", "start-after-end"}, f"the grid misses a branch: {situations}"

        period_boundaries = _period().period_boundaries
        for case, states, date_from, as_of, used, rows in cases:
            boundaries = period_boundaries(states, date_from, as_of)
            if used is None:
                assert boundaries is None, case
                continue
            assert boundaries is not None, case
            assert boundaries.start is used[0] and boundaries.end is used[1], f"{case}: not the states today's summary uses"
            assert _rows_between((boundaries.start, boundaries.end)) == rows, f"{case}: not the states today's breakdown uses"

    def test_the_result_is_a_frozen_dataclass(self):
        period = _period()
        boundaries = period.period_boundaries(list(FOUR), D3, D8)

        assert dataclasses.is_dataclass(period.PeriodBoundaries)
        assert {"start", "end"} <= {field.name for field in dataclasses.fields(period.PeriodBoundaries)}
        assert isinstance(boundaries, period.PeriodBoundaries)
        with pytest.raises(dataclasses.FrozenInstanceError):
            boundaries.start = None


class TestPeriodPnl:
    """``period_pnl``: the opening figures of the period, its net flows, its P&L
    (``end NAV − nav_start − net_flows``) and its unrealized (``market value − open cost basis``)
    at both ends. Without a start state the opening figures are zero and the net flows are the end
    state's cumulative external cash flow."""

    def test_with_a_start_state(self):
        """Start: D4, the last state on or before D5. End: D8."""
        pnl = _period().period_pnl(list(FOUR), D5, D8)

        assert pnl.nav_start == Decimal("1180.25")
        assert pnl.book_value_start == Decimal("950.5")
        assert pnl.market_value_start == Decimal("870")
        assert pnl.net_flows == Decimal("100.25")  # 1200.25 − 1100
        assert pnl.pnl == Decimal("19.50")  # 1300 − 1180.25 − 100.25
        assert pnl.ugl_start == Decimal("149.5")  # 870 − 720.5
        assert pnl.ugl_end == Decimal("200.25")  # 990.5 − 790.25
        assert pnl.ugl_delta == Decimal("50.75")

    @pytest.mark.parametrize("date_from", [None, D1], ids=["no-date-from", "before-the-first-state"])
    def test_without_a_start_state_the_period_counts_from_zero(self, date_from):
        """End: D6, the last state on or before D7. Every flow since the first state is in the period."""
        pnl = _period().period_pnl(list(FOUR), date_from, D7)

        assert (pnl.nav_start, pnl.book_value_start, pnl.market_value_start, pnl.ugl_start) == (Decimal("0"),) * 4
        assert pnl.net_flows == Decimal("1150.5")
        assert pnl.pnl == Decimal("100.0")  # 1250.5 − 0 − 1150.5
        assert pnl.ugl_end == Decimal("155.125")  # 915.125 − 760
        assert pnl.ugl_delta == Decimal("155.125")

    def test_none_without_a_period(self):
        period_pnl = _period().period_pnl

        assert period_pnl([], None, D5) is None
        assert period_pnl(list(FOUR[:1]), None, D5) is None
        assert period_pnl(list(FOUR), D2, D1) is None

    def test_matches_today_summary_metrics(self):
        """Characterization: each of the eight figures is today's ``_compute_period_summary_metrics``
        figure, exponent included, on every case of the grid; None where today's are all None."""
        cases = [(case, states, date_from, as_of, _summary_metrics_today(SimpleNamespace(daily_states=states), date_from, as_of)) for case, states, date_from, as_of in _grid()]
        period_pnl = _period().period_pnl

        for case, states, date_from, as_of, metrics in cases:
            result = period_pnl(states, date_from, as_of)
            if all(value is None for value in metrics.values()):
                assert result is None, case
                continue
            assert result is not None, case
            for field, key in PNL_FIELDS.items():
                value = getattr(result, field)
                assert _same_decimal(value, metrics[key]), f"{case}: {field} = {value!r}, today {metrics[key]!r}"

    def test_the_result_is_a_frozen_dataclass(self):
        period = _period()
        pnl = period.period_pnl(list(FOUR), D3, D8)

        assert dataclasses.is_dataclass(period.PeriodPnl)
        assert set(PNL_FIELDS) <= {field.name for field in dataclasses.fields(period.PeriodPnl)}
        assert isinstance(pnl, period.PeriodPnl)
        with pytest.raises(dataclasses.FrozenInstanceError):
            pnl.pnl = Decimal("1")


class TestPeriodOtherResult:
    """``period_other_result``: what closes ``pnl = ugl_delta + realized + income − fees_taxes + other``."""

    def test_the_residual_closes_the_period_identity(self):
        pnl, ugl_delta, realized, income, fees_taxes = Decimal("19.50"), Decimal("50.75"), Decimal("-12.30"), Decimal("4.05"), Decimal("1.20")

        other = _period().period_other_result(pnl=pnl, ugl_delta=ugl_delta, realized=realized, income=income, fees_taxes=fees_taxes)

        assert other == Decimal("-21.80")
        assert ugl_delta + realized + income - fees_taxes + other == pnl

    def test_matches_today(self):
        """Characterization: today's expression, exponent included, on a grid of signs, zeros and
        exponents; the arguments in their documented order (pnl, ugl_delta, realized, income, fees_taxes)."""
        grid = [tuple(Decimal(text) for text in texts) for texts in itertools.product(("19.50", "-7", "0"), ("50.75", "0.0000001"), ("-12.30", "0"), ("4.05", "0"), ("1.20", "0"))]
        period_other_result = _period().period_other_result

        for args in grid:
            result, expected = period_other_result(*args), _other_result_today(*args)
            assert _same_decimal(result, expected), f"{args}: {result!r}, today {expected!r}"


# =============================================================================
# J-14: the identity's residual and its tolerance, in the same home
# =============================================================================

# Figures converted into the report currency, as the engine sums them: amounts times 10-digit rates (exact, 23 and 22
# significant digits), amounts divided by a rate, and one converted across two rates (Decimal's 28 digits, rounded).
# On them the association of a sum shows.
CONVERTED = (
    Decimal("1234567.891234") * Decimal("1.0876543219"),
    Decimal("-987654.321987") * Decimal("0.9123456789"),
    Decimal("2500") / Decimal("1.09"),
    Decimal("-31465") / Decimal("1.19533"),
    Decimal("8109.5") / Decimal("1.19533") * Decimal("1.0876543219"),
)

# The short figures of the identity: signs, zeros (one negative), exponents (one positive), the closing −21.80 of
# TestPeriodOtherResult among them.
SHORT_IDENTITY_GRID = [tuple(Decimal(text) for text in texts) for texts in itertools.product(("19.50", "-7", "0"), ("50.75", "0.0000001"), ("-12.30", "-0"), ("4.05", "0.000"), ("1.20", "0"), ("-21.80", "0", "3E+2"))]

# Decimal's default context, pinned where a case depends on the precision of its rounding.
DEFAULT_28_DIGITS = Context(prec=28, rounding=ROUND_HALF_EVEN)


def _other_associations(pnl: Decimal, ugl_delta: Decimal, realized: Decimal, income: Decimal, fees_taxes: Decimal, other_result: Decimal) -> dict[str, Decimal]:
    """The same identity residual written four other ways: each is the same sum in exact arithmetic, and each rounds
    differently from today's on converted amounts."""
    return {
        "the closing term minus other_result": _other_result_today(pnl, ugl_delta, realized, income, fees_taxes) - other_result,
        "other_result added first": pnl - (other_result + ugl_delta + realized + income - fees_taxes),
        "other_result taken from pnl first": (pnl - other_result) - (ugl_delta + realized + income - fees_taxes),
        "fees_taxes subtracted last": pnl - (ugl_delta + realized + income + other_result - fees_taxes),
    }


class TestPeriodIdentityResidual:
    """``period_identity_residual``: what ``pnl = ugl_delta + realized + income − fees_taxes + other_result`` leaves,
    ``pnl − (ugl_delta + realized + income − fees_taxes + other_result)``, in that association (J-14)."""

    def test_what_the_identity_leaves(self):
        """The figures of TestPeriodOtherResult: its −21.80 closes the identity, −20.80 leaves −1.00."""
        figures = {"pnl": Decimal("19.50"), "ugl_delta": Decimal("50.75"), "realized": Decimal("-12.30"), "income": Decimal("4.05"), "fees_taxes": Decimal("1.20")}
        period_identity_residual = _period().period_identity_residual

        assert _same_decimal(period_identity_residual(**figures, other_result=Decimal("-21.80")), Decimal("0.00"))
        assert _same_decimal(period_identity_residual(**figures, other_result=Decimal("-20.80")), Decimal("-1.00"))

    def test_matches_today(self):
        """Characterization: the AI Export's expression, exponent and sign of zero included, on short figures and on
        every combination of six converted amounts.

        First, on today's code alone: the converted amounts carry 20 significant digits or more, and for each other
        association of the sum the grid holds a case where it differs from today's, so a swapped association would
        not pass.
        """
        converted_grid = list(itertools.product(CONVERTED, repeat=6))
        assert all(len(amount.as_tuple().digits) >= 20 for amount in CONVERTED)
        for name in _other_associations(*converted_grid[0]):
            assert any(not _same_decimal(_other_associations(*args)[name], _identity_residual_today(*args)) for args in converted_grid), f"the grid cannot tell «{name}» from today's"

        period_identity_residual = _period().period_identity_residual
        for args in SHORT_IDENTITY_GRID + converted_grid:
            result, expected = period_identity_residual(*args), _identity_residual_today(*args)
            assert _same_decimal(result, expected), f"{args}: {result!r}, today {expected!r}"

    def test_the_identity_closes_with_its_closing_term(self):
        """With ``other_result = period_other_result(...)`` the residual is zero on short figures, and below
        CONVERSION_DUST on converted amounts, where it is not always zero: Decimal's rounding, which is why
        ``is_reconciled`` has a tolerance."""
        short_figures = list({tuple(str(figure) for figure in args[:5]): args[:5] for args in SHORT_IDENTITY_GRID}.values())
        converted_figures = list(itertools.product(CONVERTED, repeat=5))
        rounded = [_identity_residual_today(*args, _other_result_today(*args)) for args in converted_figures]
        assert any(residual != 0 for residual in rounded) and all(abs(residual) < CONVERSION_DUST for residual in rounded)

        period = _period()
        for args in short_figures:
            residual = period.period_identity_residual(*args, period.period_other_result(*args))
            assert residual == 0 and period.is_reconciled(residual) is True, f"{args}: {residual!r}"
        residuals = [period.period_identity_residual(*args, period.period_other_result(*args)) for args in converted_figures]
        assert all(period.is_reconciled(residual) is True for residual in residuals)
        assert any(residual != 0 for residual in residuals), "the converted amounts must show the rounding"

    @pytest.mark.parametrize(
        ("amounts", "rate", "today", "alternatives"),
        [
            pytest.param(
                ("92967.16", "42957.89", "31465", "58674.48", "8109.5"),
                "1.19533",
                "6E-23",
                {"the closing term minus other_result": "0E-23", "other_result added first": "0E-23", "other_result taken from pnl first": "1E-22", "fees_taxes subtracted last": "4E-23"},
                id="the-last-digit",
            ),
            pytest.param(
                ("49544.02", "-96960.8", "20294", "15186.3", "93345.15"),
                "1.27229",
                "0E-23",
                {"the closing term minus other_result": "0E-22", "other_result added first": "8E-23", "other_result taken from pnl first": "0E-22", "fees_taxes subtracted last": "-2E-23"},
                id="the-exponent",
            ),
        ],
    )
    def test_the_association_is_today_s_and_it_matters(self, amounts, rate, today, alternatives):
        """Why the association is kept. Five figures of one period (pnl, ugl_delta, realized, income, fees_taxes), in
        one currency converted at one 6-digit rate, carry 28 significant digits; ``other_result`` is their closing
        term. Each other way of writing the sum rounds differently: by the last digit (today's 6E-23), or by the
        exponent alone (today's zero is 0E-23; two alternatives give 0E-22, equal in value, told apart only by
        ``str()``). The house gives today's figure and none of the others. Decimal's default context (28 digits,
        half-even), pinned."""
        with localcontext(DEFAULT_28_DIGITS):
            pnl, ugl_delta, realized, income, fees_taxes = (Decimal(amount) / Decimal(rate) for amount in amounts)
            args = (pnl, ugl_delta, realized, income, fees_taxes, _other_result_today(pnl, ugl_delta, realized, income, fees_taxes))
            expected = _identity_residual_today(*args)
            others = _other_associations(*args)
        assert all(len(amount.as_tuple().digits) == 28 for amount in args)
        assert str(expected) == today
        assert {name: str(value) for name, value in others.items()} == alternatives

        with localcontext(DEFAULT_28_DIGITS):
            result = _period().period_identity_residual(*args)

        assert _same_decimal(result, expected), f"{result!r}, today {expected!r}"
        for name, value in others.items():
            assert not _same_decimal(result, value), f"the house rounds as «{name}» does"


class TestIsReconciled:
    """``is_reconciled``: the identity closes when its residual is below ``CONVERSION_DUST`` (``native_cash``, 1E-9) in
    absolute value; strictly, on either side of zero (J-14). A value test: ``1.0000E-9`` is the dust itself."""

    @pytest.mark.parametrize(
        "residual",
        [
            pytest.param(Decimal("0"), id="zero"),
            pytest.param(Decimal("-0"), id="negative-zero"),
            pytest.param(Decimal("0E-28"), id="zero-with-an-exponent"),
            pytest.param(Decimal("6E-23"), id="rounding"),
            pytest.param(CONVERSION_DUST - Decimal("1E-27"), id="dust-less-1e-27"),
            pytest.param(CONVERSION_DUST - Decimal("1E-18"), id="dust-less-1e-18"),
        ],
    )
    def test_below_conversion_dust_is_reconciled_on_either_side(self, residual):
        assert _reconciled_today(residual) is True and _reconciled_today(-residual) is True
        is_reconciled = _period().is_reconciled

        assert is_reconciled(residual) is True
        assert is_reconciled(-residual) is True

    @pytest.mark.parametrize(
        "residual",
        [
            pytest.param(CONVERSION_DUST, id="the-dust"),
            pytest.param(Decimal("1.0000E-9"), id="the-dust-with-another-exponent"),
            pytest.param(CONVERSION_DUST + Decimal("1E-27"), id="dust-plus-1e-27"),
            pytest.param(Decimal("1E-8"), id="ten-dusts"),
            pytest.param(Decimal("899"), id="material"),
        ],
    )
    def test_conversion_dust_or_more_is_not_on_either_side(self, residual):
        assert _reconciled_today(residual) is False and _reconciled_today(-residual) is False
        is_reconciled = _period().is_reconciled

        assert is_reconciled(residual) is False
        assert is_reconciled(-residual) is False

    def test_matches_today(self):
        """Characterization: today's ``abs(residual) < CONVERSION_DUST``, on a grid around the boundary, of both signs,
        with the residuals the identity leaves on converted amounts, closed and not; the grid reaches both answers."""
        magnitudes = [Decimal(text) for text in ("0", "0E-28", "1E-28", "6E-23", "1E-21", "9.99999999E-10", "9.999999999999999999E-10", "1E-9", "1.0E-9", "1.000000001E-9", "2E-9", "1E-8", "0.01", "899", "1E+3")]
        closed = [_identity_residual_today(*args, _other_result_today(*args)) for args in itertools.product(CONVERTED, repeat=5)]
        unclosed = [_identity_residual_today(*args) for args in itertools.product(CONVERTED[2:], repeat=6)]
        grid = magnitudes + [-magnitude for magnitude in magnitudes] + closed + unclosed
        assert {_reconciled_today(residual) for residual in grid} == {True, False}

        is_reconciled = _period().is_reconciled
        for residual in grid:
            assert is_reconciled(residual) is _reconciled_today(residual), repr(residual)

    def test_the_tolerance_is_native_cash_s(self, monkeypatch):
        """One constant, no copy: ``period`` holds ``native_cash.CONVERSION_DUST`` itself, and ``is_reconciled`` reads
        it when called (a literal would not follow the patched value)."""
        period = _period()
        assert period.CONVERSION_DUST is native_cash.CONVERSION_DUST

        monkeypatch.setattr(period, "CONVERSION_DUST", Decimal("1E-6"))

        assert period.is_reconciled(Decimal("5E-7")) is True
        assert period.is_reconciled(Decimal("-1E-6")) is False


class TestPeriodOtherResultInPositionsContribution:
    """J-14: ``get_positions_contribution`` wrote ``period_other_result``'s expression in line a second time
    (``portfolio_service.py:1854`` at ``e6d3e61e0``) and now calls the function: the same association, so the same
    figure to its last digit. A characterization lock, green before J-14 too: ``period_other_result`` was already
    there."""

    def test_matches_today_on_converted_amounts(self):
        """Every combination of five converted amounts, exponent included. First: the grid tells today's expression
        from ``pnl − (ugl_delta + realized + income − fees_taxes)``, so a regrouped sum would not pass."""
        grid = list(itertools.product(CONVERTED, repeat=5))
        assert any(not _same_decimal(pnl - (ugl_delta + realized + income - fees_taxes), _positions_other_result_today(pnl, ugl_delta, realized, income, fees_taxes)) for pnl, ugl_delta, realized, income, fees_taxes in grid)

        period_other_result = _period().period_other_result
        for args in grid:
            result, expected = period_other_result(*args), _positions_other_result_today(*args)
            assert _same_decimal(result, expected), f"{args}: {result!r}, today {expected!r}"


# =============================================================================
# B. financial_math/average_cost.py: the unit cost of each movement
# =============================================================================


def _buy(day: date, quantity: str, cost: str, currency: str, movement_id: int) -> CostMovement:
    return CostMovement(movement_id=movement_id, transaction_type="BUY", date=day, kind=CostMovementKind.ACQUISITION, quantity=Decimal(quantity), cost_amount=Decimal(cost), cost_currency=currency)


def _acquisition(day: date, quantity: str, movement_id: int, *, cost: str | None = None, currency: str | None = None) -> CostMovement:
    """An ADJUSTMENT that adds quantity: of unknown cost without ``cost``, free with ``cost="0"``."""
    return CostMovement(movement_id=movement_id, transaction_type="ADJUSTMENT", date=day, kind=CostMovementKind.ACQUISITION, quantity=Decimal(quantity), cost_amount=None if cost is None else Decimal(cost), cost_currency=currency)


def _sell(day: date, quantity: str, movement_id: int) -> CostMovement:
    return CostMovement(movement_id=movement_id, transaction_type="SELL", date=day, kind=CostMovementKind.REDUCTION, quantity=Decimal(quantity))


def _split(day: date, quantity: str, movement_id: int) -> CostMovement:
    return CostMovement(movement_id=movement_id, transaction_type="ADJUSTMENT", date=day, kind=CostMovementKind.SPLIT, quantity=Decimal(quantity))


class FixedRates:
    """``convert_bulk`` double: one fixed rate per pair, found on the requested day; no rate for any other pair."""

    def __init__(self, rates: dict[tuple[str, str], str]) -> None:
        self.rates = {pair: Decimal(rate) for pair, rate in rates.items()}

    async def __call__(self, session, conversions, raise_on_error=True):
        results = []
        for amount, to_currency, day in conversions:
            rate = self.rates.get((amount.code, to_currency))
            results.append(None if rate is None else (Currency(code=to_currency, amount=amount.amount * rate), day, False))
        return results, []


@pytest.fixture
def usd_at_0_9(monkeypatch) -> FixedRates:
    """USD → EUR at 0.9 on every day; no GBP rate at all."""
    double = FixedRates({("USD", "EUR"): "0.9"})
    monkeypatch.setattr(average_cost, "convert_bulk", double)
    return double


async def _steps(movements: tuple[CostMovement, ...]) -> tuple[CostStep, ...]:
    """The timeline the WAC preview builds: one USD asset, report EUR, no asset leg."""
    position = CostPosition(key="preview", asset_currency="USD", movements=movements)
    return (await compute_average_costs(None, [position], report_currency=REPORT, asset_leg=False))["preview"].steps


TIMELINES: dict[str, tuple[CostMovement, ...]] = {
    "two-buys": (_buy(D1, "10", "1000", "EUR", 1), _buy(D2, "5", "600", "EUR", 2)),
    "converted-buy": (_buy(D1, "10", "1000", "USD", 1),),
    "closing-sale": (_buy(D1, "10", "1000", "EUR", 1), _buy(D2, "10", "1400", "EUR", 2), _sell(D3, "-20", 3)),
    "split": (_buy(D1, "10", "1000", "EUR", 1), _split(D2, "10", 2)),
    "other-effects": (
        _buy(D1, "10", "1000", "EUR", 1),
        _acquisition(D2, "5", 2),
        _acquisition(D3, "5", 3, cost="0", currency="EUR"),
        _buy(D4, "2", "50", "GBP", 4),
    ),
    "sales-after-each-kind-of-step": (
        _sell(D1, "-2", 1),
        _buy(D2, "10", "1000", "EUR", 2),
        _split(D3, "10", 3),
        _sell(D4, "-20", 4),
        _buy(D5, "10", "1000", "EUR", 5),
        _acquisition(D6, "10", 6),
        _sell(D7, "-20", 7),
        _sell(D8, "-3", 8),
    ),
    # Every effect in one timeline, with divisions that do not end (900.0 / 7, 1000 / 7, 810.18 / 17).
    "mixed": (
        _sell(D1, "-2", 1),
        _buy(D2, "7", "1000", "USD", 2),
        _buy(D3, "3", "450.30", "EUR", 3),
        _sell(D4, "-4", 4),
        _split(D5, "6", 5),
        _acquisition(D6, "2", 6),
        _acquisition(D7, "1", 7, cost="0", currency="EUR"),
        _buy(D8, "2", "50", "GBP", 8),
        _sell(D9, "-17", 9),
    ),
}


class TestMovementUnitCosts:
    """``movement_unit_costs``: one ``MovementUnitCost(report, original)`` per step of a timeline.

    ``report``: what an acquisition added per unit; for a reduction, the average of the step before
    it (0 before the first step); for a split, the average after it; 0 for any other step.
    ``original``: the unit cost in the currency paid, for an acquisition converted into the report
    currency; None otherwise.
    """

    @pytest.mark.asyncio
    async def test_an_acquisition_costs_what_it_added_per_unit(self, usd_at_0_9):
        """Paid in the report currency: nothing converted, no original unit cost. The second purchase
        costs its own 120 a unit, not the running average."""
        steps = await _steps(TIMELINES["two-buys"])
        assert [(step.effect, step.conversion) for step in steps] == [(CostEffect.ADD, None)] * 2

        costs = average_cost.movement_unit_costs(steps)

        assert [(cost.report, cost.original) for cost in costs] == [(Decimal("100"), None), (Decimal("120"), None)]

    @pytest.mark.asyncio
    async def test_a_converted_acquisition_keeps_its_original_unit_cost(self, usd_at_0_9):
        """1000 USD for 10 units, at 0.9: 90 EUR a unit, and 100 USD a unit as paid."""
        steps = await _steps(TIMELINES["converted-buy"])
        assert steps[0].effect == CostEffect.ADD
        assert steps[0].conversion is not None and steps[0].conversion.original_amount == Decimal("1000")
        assert steps[0].cost_report_change == Decimal("900")

        (cost,) = average_cost.movement_unit_costs(steps)

        assert (cost.report, cost.original) == (Decimal("90"), Decimal("100"))

    @pytest.mark.asyncio
    async def test_a_sale_that_closes_the_position_costs_the_average_before_it(self, usd_at_0_9):
        """2400 EUR for 20 units, then all 20 sold: the sale costs 120 a unit, while the pool it
        leaves has an average of 0."""
        steps = await _steps(TIMELINES["closing-sale"])
        assert (steps[2].effect, steps[2].quantity, steps[2].unit_cost_report) == (CostEffect.REDUCE, Decimal("0"), Decimal("0"))

        costs = average_cost.movement_unit_costs(steps)

        assert (costs[2].report, costs[2].original) == (Decimal("120"), None)

    @pytest.mark.asyncio
    async def test_a_split_costs_the_average_after_it(self, usd_at_0_9):
        """1000 EUR for 10 units, then 10 more units from a split: 50 a unit, not the 100 before it."""
        steps = await _steps(TIMELINES["split"])
        assert (steps[1].effect, steps[1].unit_cost_report) == (CostEffect.SPLIT_RESCALE, Decimal("50"))

        costs = average_cost.movement_unit_costs(steps)

        assert (costs[1].report, costs[1].original) == (Decimal("50"), None)

    @pytest.mark.asyncio
    async def test_any_other_step_costs_zero(self, usd_at_0_9):
        """An acquisition of unknown cost, a free one, and one whose rate is missing (GBP): 0 a unit, no original."""
        steps = await _steps(TIMELINES["other-effects"])
        assert [step.effect for step in steps[1:]] == [CostEffect.ADD_UNKNOWN_COST, CostEffect.ADD_ZERO_COST, CostEffect.ADD_MISSING_FX]
        assert [step.conversion for step in steps[1:]] == [None] * 3

        costs = average_cost.movement_unit_costs(steps)

        assert [(cost.report, cost.original) for cost in costs[1:]] == [(Decimal("0"), None)] * 3

    @pytest.mark.asyncio
    async def test_a_sale_costs_the_average_left_by_the_step_before_it(self, usd_at_0_9):
        """Whatever that step was. A sale before any acquisition: 0. A sale that empties the pool right
        after a split: the split's 50. Right after an acquisition of unknown cost: the 50 that
        acquisition left (1000 known for 20 units), not the 100 of the last purchase. A sale on the
        emptied pool: 0."""
        steps = await _steps(TIMELINES["sales-after-each-kind-of-step"])
        assert [step.effect for step in steps] == [CostEffect.REDUCE, CostEffect.ADD, CostEffect.SPLIT_RESCALE, CostEffect.REDUCE, CostEffect.ADD, CostEffect.ADD_UNKNOWN_COST, CostEffect.REDUCE, CostEffect.REDUCE]
        assert [step.unit_cost_report for step in steps] == [Decimal(value) for value in ("0", "100", "50", "0", "100", "50", "0", "0")]

        costs = average_cost.movement_unit_costs(steps)

        assert [cost.report for cost in costs] == [Decimal(value) for value in ("0", "100", "50", "50", "100", "0", "50", "0")]

    @pytest.mark.asyncio
    async def test_matches_today_preview_arithmetic(self, usd_at_0_9):
        """Characterization: both figures of every step of every timeline are today's
        ``_wac_qualifying_txs`` figures, exponent included. First: the timelines reach every effect
        and a converted acquisition."""
        built = {name: await _steps(movements) for name, movements in TIMELINES.items()}
        expected = {name: _unit_costs_today(steps) for name, steps in built.items()}
        effects = {step.effect for steps in built.values() for step in steps}
        assert effects == set(CostEffect), f"the timelines miss {set(CostEffect) - effects}"
        assert any(step.conversion is not None for steps in built.values() for step in steps)

        movement_unit_costs = average_cost.movement_unit_costs
        for name, steps in built.items():
            costs = movement_unit_costs(steps)
            assert len(costs) == len(steps), name
            for index, (cost, (report, original)) in enumerate(zip(costs, expected[name], strict=True)):
                assert _same_decimal(cost.report, report), f"{name}, step {index}: report {cost.report!r}, today {report!r}"
                assert _same_decimal(cost.original, original), f"{name}, step {index}: original {cost.original!r}, today {original!r}"

    @pytest.mark.asyncio
    async def test_one_frozen_unit_cost_per_step(self, usd_at_0_9):
        steps = await _steps(TIMELINES["mixed"])

        costs = average_cost.movement_unit_costs(steps)

        assert isinstance(costs, tuple) and len(costs) == len(steps)
        assert dataclasses.is_dataclass(average_cost.MovementUnitCost)
        assert {"report", "original"} <= {field.name for field in dataclasses.fields(average_cost.MovementUnitCost)}
        assert all(isinstance(cost, average_cost.MovementUnitCost) for cost in costs)
        with pytest.raises(dataclasses.FrozenInstanceError):
            costs[0].report = Decimal("1")
        assert average_cost.movement_unit_costs(()) == ()


# =============================================================================
# J5-3 (MF's review of J5-1, point 2): the period's realized sales, one function
# =============================================================================


def _period_realized_sales_today(sales: list[Any], date_from: date | None, date_to: date | None) -> list[Any]:
    """``_period_realized_sales``, ``portfolio_service.py:335-343``, as written."""
    return [sale for sale in sales if (date_from is None or sale.date > date_from) and (date_to is None or sale.date <= date_to) and sale.proceeds is not None and sale.cost_complete]


def _sale(on: date, *, proceeds: str | None = "120", cost_complete: bool = True, transaction_id: int = 1) -> SimpleNamespace:
    return SimpleNamespace(transaction_id=transaction_id, date=on, proceeds=None if proceeds is None else Decimal(proceeds), cost=Decimal("100"), cost_complete=cost_complete)


class TestPeriodRealizedSales:
    """``period.period_realized_sales(sales, date_from, date_to)``: the engine's realized sales in ``(date_from, date_to]`` whose proceeds
    and cost are both known. The Performance table, the summary and the position series (#48) all read it. Red by absence until it moves
    from ``portfolio_service`` to ``period.py``."""

    SALES = [
        _sale(D1, transaction_id=1),
        _sale(D3, transaction_id=2),
        _sale(D5, transaction_id=3),
        _sale(D5, proceeds=None, transaction_id=4),
        _sale(D6, cost_complete=False, transaction_id=5),
        _sale(D8, transaction_id=6),
    ]

    @pytest.mark.parametrize("date_from", [None, D1, D3, D5, D9])
    @pytest.mark.parametrize("date_to", [None, D3, D5, D8, D9])
    def test_it_keeps_what_todays_function_keeps(self, date_from, date_to):
        assert _period().period_realized_sales(self.SALES, date_from, date_to) == _period_realized_sales_today(self.SALES, date_from, date_to)

    def test_the_start_is_excluded_the_end_included_and_an_unknown_amount_left_out(self):
        kept = _period().period_realized_sales(self.SALES, D3, D8)

        assert [sale.transaction_id for sale in kept] == [3, 6]

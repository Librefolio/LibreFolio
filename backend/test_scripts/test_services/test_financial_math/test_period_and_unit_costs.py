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
from decimal import Decimal
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from backend.app.schemas.common import Currency
from backend.app.schemas.portfolio import UnrealizedBreakdownRow
from backend.app.services.financial_math import average_cost
from backend.app.services.financial_math.average_cost import CostEffect, CostMovement, CostMovementKind, CostPosition, CostStep, compute_average_costs
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

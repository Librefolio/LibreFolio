"""
P2 (workstream MF, lot P2 — «formule veloci», N74): the portfolio history and its views are built for the window asked.

Modules under test:

* ``backend/app/services/financial_math/portfolio/derived_views.py`` — ``DerivedViewsBuilder``:

  - ``build_history(date_from, date_to)``, ``build_broker_pnl_history(date_from, date_to)`` and
    ``build_pnl_candles(date_from, date_to)`` build the states of ``[date_from, date_to]`` (an open bound reaches the end
    of the history): what HEAD built for the whole history and the callers then cut with ``from <= date <= to``;
  - ``build_acquisition_funding(date_from, date_to)`` builds the states of ``(date_from, date_to]``: a flow series, a BUY
    dated ``date_from`` belongs to the period before — the ``from < date <= to`` cut of
    ``PortfolioService.get_acquisition_funding_history``;
  - ``build_performance_inputs(date_from)`` returns only what ``returns.rebase_to_period`` keeps of the period: the NAV
    snapshots from the opening state (the last one dated on or before ``date_from``, else the first) and the flows dated
    after it, the opening's capital baseline being where the first delta starts. So, for every ``d``,
    ``rebase_to_period(*windowed(d), d) == rebase_to_period(*whole(), d)``.

* ``backend/app/services/portfolio_service.py`` — the six call sites hand the builder their window: ``get_summary``
  (performance inputs), ``get_history`` (history, performance inputs), ``get_broker_pnl_history``, ``get_pnl_candles``,
  ``get_acquisition_funding_history``. Their own cuts stay and now take nothing away, so the output is unchanged: a call
  site that drops its window loses only speed, which is why only the wiring tests below can see it.

How it is proved:

1. Parity — every view of a synthetic gapless history (capital moved on the first day, on the last day and on two days in
   a row; a nonzero capital baseline at every opening; three brokers every day; days without a candle and days without
   an acquisition; the optional figures zero and not; amounts with 0 to 4 decimals, trailing zeros kept) against the
   whole build cut as HEAD cuts it, at full precision: keys in order, currency codes, each amount's ``Decimal`` and its
   ``str``. Named windows, then every pair of bounds from two days before the history to two days after it, open bounds
   included. A broker with no point in the window has no entry in the builder's per-broker view (the service puts every
   broker back for a window holding no state: section 5). Also a 46 312-day history from 1900 (the typo case), whose
   windows are compared with the same views built on the states a linear cut keeps — each view maps a state to its point
   on its own.
2. Performance inputs — the rebase of the windowed inputs equals the rebase of the whole ones for every ``d`` from three
   days before the history to three days after it (start date, start NAV, snapshots, flows, in order, ``str`` included),
   and so do the TWRR, simple ROI and MWRR series computed on the two; the windowed inputs are exactly the whole ones from
   the opening snapshot, and never more than the window's snapshots plus one.
3. Cost — a builder given a window reads no state outside it. Every state of the 1900 history logs its date each time a
   field of it is read, its date included; the log is cleared once the builder is built (the constructor indexes every
   date by design). A call's log is the window's dates, whatever the history's length: a builder that built the whole
   history and cut it afterwards, or that scanned every state for its date, reads them all. A control proves the log
   sees a whole build. The same log on the service: each call site, given the last month of a 1 000-day history, makes
   its builder read that month only.
4. Wiring — each call site, recorded on the builder, hands it the service's window (both bounds); and the service's
   output is the same with the call site stripped of its window (HEAD's call), for the windows ``get_report`` can ask
   (start ≤ end, the end inside the history).
5. A window holding no state (from after the last state, from > to, before the first state): ``get_broker_pnl_history``
   gives HEAD's output — every broker, in the order they first appear in the history, with an empty series — against
   HEAD's call. Also on a history the engine never writes (a broker missing from the first state, another from the last),
   so the fallback is pinned on its own, not through the invariant of section 6.
6. The engine's invariant the windowed per-broker view relies on for a window that holds states: a real
   ``DailyStateBuilder`` run (brokers starting on different days, quiet days between, one broker moving only after the
   run's last day) lists the same brokers, in the same order, on every state — every broker of the scope with a
   transaction —; and on those states ``get_broker_pnl_history`` is HEAD's for windows with and without states.

``states[opening:]`` for the flows of the performance inputs is an equivalent mutant (the opening's own delta is zero):
no test can tell it apart, and none tries.

Red on HEAD (bbbc085d2; derived_views.py and portfolio_service.py of HEAD loaded in-process from ``git show HEAD:…``):
214 of 278. Every builder test fails with TypeError — no view takes a window there —, the builder cost tests included;
the six service cost tests fail on cost (all 1 000 days read, the window has 31); the six wiring tests fail on their
assertion (recorded ``(None, None)`` / ``(None,)``). Green on HEAD, by design: the four read-log controls, the 42
service-parity tests (the guard that the window changes nothing the API returns) and sections 5-6, which compare with
HEAD's call. Section 5 and the empty windows of section 6 are red on the product without the service's empty-window
fallback (14 tests); the irregular history of section 5 is what tells a fallback taken from the first state alone.

Pure: no database (the service runs on a session that finds no row), no server, no network.
"""

from __future__ import annotations

import dataclasses
import random
from collections.abc import Sequence
from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock

import pytest

from backend.app.db.models import TransactionType
from backend.app.schemas.common import Currency as CurrencySchema
from backend.app.services.financial_math.portfolio.classifier import ScopeAwareTransactionClassifier
from backend.app.services.financial_math.portfolio.daily_state import DailyStateBuilder
from backend.app.services.financial_math.portfolio.derived_views import DerivedViewsBuilder
from backend.app.services.financial_math.portfolio.models import (
    AcquisitionFundingContribution,
    BrokerDailyContribution,
    DailyPortfolioState,
    PnlCandleContribution,
    PortfolioCalculationResult,
)
from backend.app.services.financial_math.price_marks import build_asset_price_series
from backend.app.services.financial_math.returns import (
    PeriodRebase,
    calculate_simple_roi_series,
    calculate_twrr_series,
    period_mwrr_series,
    rebase_to_period,
)
from backend.app.services.portfolio_service import PortfolioService
from backend.test_scripts.test_services._engine_average_costs import engine_average_costs
from backend.test_scripts.test_services._engine_native_cash import engine_native_cash

D = Decimal
CCY = "EUR"
BROKERS = (11, 22, 33)
SEED = 20261019

# The short history: 14 gapless days, one state a day.
FIRST = date(2025, 3, 3)
DAYS = 14
LAST = FIRST + timedelta(days=DAYS - 1)

# Capital moved on a day, by day index (portfolio perspective: + in, - out): the first day, two days in a row, the last day.
FLOW_DAYS: dict[int, Decimal] = {0: D("1000.50"), 3: D("250"), 4: D("-100.25"), 8: D("400.1"), 13: D("75.125")}
# Days with acquisitions (acquisition_funding set), and days without a candle (pnl_candle None).
BUY_DAYS = frozenset({0, 4, 6, 10, 13})
NO_CANDLE_DAYS = frozenset({2, 6, 9})

# The history's figures that it turns into None when they are zero.
OPTIONAL_HISTORY_FIGURES = (
    "in_transit_cash_value",
    "in_transit_asset_market_value",
    "in_transit_market_value",
    "open_cost_basis",
    "in_transit_asset_cost_basis",
    "in_transit_book_value",
    "book_value",
    "unrealized_gain_loss",
)

# The 1900 history: 46 312 days, the span of a 1900 typo up to the autumn of 2026.
LONG_FIRST = date(1900, 1, 1)
LONG_DAYS = 46_312
LONG_LAST = LONG_FIRST + timedelta(days=LONG_DAYS - 1)

# view -> (builder method, exclusive start)
VIEWS: dict[str, tuple[str, bool]] = {
    "history": ("build_history", False),
    "broker_pnl_history": ("build_broker_pnl_history", False),
    "pnl_candles": ("build_pnl_candles", False),
    "acquisition_funding": ("build_acquisition_funding", True),
}

# The window parameters of each builder method, in their order.
WINDOW_PARAMETERS: dict[str, tuple[str, ...]] = {
    "build_history": ("date_from", "date_to"),
    "build_broker_pnl_history": ("date_from", "date_to"),
    "build_pnl_candles": ("date_from", "date_to"),
    "build_acquisition_funding": ("date_from", "date_to"),
    "build_performance_inputs": ("date_from",),
}


def _day(index: int) -> date:
    """The short history's day ``index`` (negative: before it; DAYS or more: after it)."""
    return FIRST + timedelta(days=index)


NAMED_WINDOWS: dict[str, tuple[date | None, date | None]] = {
    "open": (None, None),
    "before-the-first-day": (_day(-5), _day(-1)),
    "after-the-last-day": (_day(DAYS), _day(DAYS + 4)),
    "ends-on-the-first-day": (_day(-3), _day(0)),
    "starts-on-the-first-day": (_day(0), _day(4)),
    "starts-on-the-last-day": (_day(DAYS - 1), _day(DAYS + 2)),
    "ends-on-the-last-day": (_day(DAYS - 4), _day(DAYS - 1)),
    "one-quiet-day": (_day(5), _day(5)),
    "one-flow-day": (_day(3), _day(3)),
    "one-buy-day": (_day(6), _day(6)),
    "from-a-flow-day": (_day(8), _day(11)),
    "from-the-day-before-a-flow": (_day(7), _day(11)),
    "from-a-buy-day": (_day(6), _day(10)),
    "from-the-day-before-a-buy": (_day(5), _day(10)),
    "to-a-buy-day": (_day(1), _day(4)),
    "from-after-to": (_day(9), _day(4)),
    "to-only": (None, _day(6)),
    "from-only": (_day(6), None),
    "around-the-whole-history": (_day(-2), _day(DAYS + 1)),
}

LONG_WINDOWS: dict[str, tuple[date, date]] = {
    "one-day": (LONG_LAST, LONG_LAST),
    "one-month": (LONG_LAST - timedelta(days=30), LONG_LAST),
    "one-year": (LONG_LAST - timedelta(days=365), LONG_LAST),
    "a-year-in-1950": (date(1950, 1, 1), date(1950, 12, 31)),
    "the-first-ten-days": (LONG_FIRST, LONG_FIRST + timedelta(days=9)),
    "from-before-the-first-day": (LONG_FIRST - timedelta(days=10), LONG_FIRST + timedelta(days=2)),
}


# =============================================================================
# The synthetic history
# =============================================================================


def _figure(rng: random.Random) -> Decimal:
    """A figure with 0 to 4 decimals, trailing zeros kept: its ``str`` is compared too."""
    return D(rng.randint(-999_999, 999_999)).scaleb(-rng.randint(0, 4))


def _optional_figure(rng: random.Random, index: int, shift: int) -> Decimal:
    """A figure the history turns into None when it is zero: zero one day in three (which day depends on ``shift``),
    written ``0`` on even days and ``0.00`` on odd ones."""
    figure = _figure(rng)
    if (index + shift) % 3:
        return figure
    return D("0.00") if index % 2 else D("0")


def _state(index: int, capital: Decimal, rng: random.Random) -> DailyPortfolioState:
    """Day ``index`` with its capital baseline; NAV = capital + P&L, the P&L within ±5 on a capital of 900 or more: the NAV
    stays positive and moves less than 1 % a day, so the MWRR of a one-day period still has a rate."""
    pnl = D(rng.randint(-500, 500)).scaleb(-rng.randint(2, 4))
    nav = capital + pnl
    # Both zero on the same days: their sum, the in-transit market value, is zero on those days too.
    in_transit_cash = _optional_figure(rng, index, 0)
    in_transit_assets = _optional_figure(rng, index, 0)
    return DailyPortfolioState(
        date=_day(index),
        cash_value=_figure(rng),
        market_value=_figure(rng),
        broker_nav_value=nav - in_transit_cash - in_transit_assets,
        in_transit_cash_value=in_transit_cash,
        in_transit_asset_market_value=in_transit_assets,
        in_transit_market_value=in_transit_cash + in_transit_assets,
        nav_value=nav,
        open_cost_basis=_optional_figure(rng, index, 1),
        in_transit_asset_cost_basis=_optional_figure(rng, index, 2),
        in_transit_book_value=_optional_figure(rng, index, 1),
        book_value=_optional_figure(rng, index, 2),
        unrealized_gain_loss=_optional_figure(rng, index, 0),
        external_cash_flow=FLOW_DAYS.get(index, D("0")),
        cumulative_external_cash_flow=capital,
        book_asset_like=_figure(rng),
        cash_from_contributed_capital=_figure(rng),
        cash_from_generated_returns=_figure(rng),
        total_pnl=pnl,
        broker_contributions={broker_id: BrokerDailyContribution(broker_id=broker_id, nav_contribution=_figure(rng), capital_contribution=_figure(rng), pnl_contribution=_figure(rng), in_transit_contribution=_figure(rng)) for broker_id in BROKERS},
        pnl_candle=None if index in NO_CANDLE_DAYS else PnlCandleContribution(open=_figure(rng), high=_figure(rng), low=_figure(rng), close=pnl),
        acquisition_funding=AcquisitionFundingContribution(from_new_capital=_figure(rng), from_reinvested=_figure(rng)) if index in BUY_DAYS else None,
    )


def _history() -> list[DailyPortfolioState]:
    rng = random.Random(SEED)
    capital = D("0")
    states: list[DailyPortfolioState] = []
    for index in range(DAYS):
        capital += FLOW_DAYS.get(index, D("0"))
        states.append(_state(index, capital, rng))
    return states


def _assert_the_history_has_its_cases(states: Sequence[DailyPortfolioState]) -> None:
    """What the windows above are named after must be true of the states, not of the constants that built them."""
    assert [state.date for state in states] == [_day(index) for index in range(DAYS)], "one state a day, ascending, no gap"
    baselines = [D("0"), *(state.cumulative_external_cash_flow for state in states)]
    flow_days = {index for index in range(DAYS) if baselines[index + 1] != baselines[index]}
    assert {0, 3, 4, 8, DAYS - 1} <= flow_days and not {2, 7, DAYS - 2} & flow_days, f"capital moves on the first and last day, on days 3-4 in a row and on 8; not on the day before: {sorted(flow_days)}"
    assert all(state.cumulative_external_cash_flow != 0 for state in states), "a nonzero capital baseline at every opening"
    assert {index for index, state in enumerate(states) if state.acquisition_funding is not None} == BUY_DAYS and 5 not in BUY_DAYS
    assert {index for index, state in enumerate(states) if state.pnl_candle is None} == NO_CANDLE_DAYS
    assert all(list(state.broker_contributions) == list(BROKERS) for state in states), "every broker every day, as the engine writes them"
    assert all(state.nav_value > 0 for state in states), "a positive NAV, so the MWRR has rates to compare"
    for name in OPTIONAL_HISTORY_FIGURES:
        values = [getattr(state, name) for state in states]
        assert any(value == 0 for value in values) and any(value != 0 for value in values), f"{name}: zero on some day and not on another"
    exponents = {state.cash_value.as_tuple().exponent for state in states}
    assert len(exponents) >= 3, f"amounts of several exponents: {exponents}"


# =============================================================================
# Full precision and HEAD's cut
# =============================================================================


def _value(value: Any) -> Any:
    """A point's value at full precision: a Currency as (code, amount, str(amount)); a date or None as itself."""
    if isinstance(value, CurrencySchema):
        assert type(value.amount) is Decimal, f"an amount must stay a Decimal: {value!r}"
        return ("Currency", value.code, value.amount, str(value.amount))
    assert value is None or isinstance(value, date), f"unexpected value in a view: {value!r}"
    return value


def _rows(points: Sequence[dict]) -> list[tuple]:
    """Points with their keys in order and their values at full precision."""
    return [tuple((key, _value(value)) for key, value in point.items()) for point in points]


def _comparable(output: list[dict] | dict[int, list[dict]]) -> Any:
    """A view's output at full precision; a per-broker one with its brokers in order."""
    if isinstance(output, dict):
        return [(broker_id, _rows(points)) for broker_id, points in output.items()]
    return _rows(output)


def _inside(day: date, date_from: date | None, date_to: date | None, *, exclusive_start: bool = False) -> bool:
    """HEAD's cut: ``from <= day <= to`` for a level series, ``from < day <= to`` for a flow series; None is open."""
    if date_from is not None and (day <= date_from if exclusive_start else day < date_from):
        return False
    return date_to is None or day <= date_to


def _head_cut(output: list[dict] | dict[int, list[dict]], date_from: date | None, date_to: date | None, *, exclusive_start: bool) -> Any:
    """The whole build cut as the service cut it on HEAD; a broker left with no point has no entry."""
    if isinstance(output, dict):
        cut = {broker_id: [point for point in points if _inside(point["date"], date_from, date_to)] for broker_id, points in output.items()}
        return {broker_id: points for broker_id, points in cut.items() if points}
    return [point for point in output if _inside(point["date"], date_from, date_to, exclusive_start=exclusive_start)]


def _parity(view: str, states: list[DailyPortfolioState], whole: dict[str, Any], date_from: date | None, date_to: date | None) -> tuple[Any, Any]:
    """(windowed build, whole build cut as HEAD cut it), both at full precision."""
    method, exclusive_start = VIEWS[view]
    windowed = getattr(DerivedViewsBuilder(states, CCY), method)(date_from, date_to)
    return _comparable(windowed), _comparable(_head_cut(whole[view], date_from, date_to, exclusive_start=exclusive_start))


def _rebase_figures(rebase: PeriodRebase) -> tuple:
    """A PeriodRebase at full precision, its snapshots and flows in order."""
    return (
        rebase.start_date,
        rebase.start_nav,
        str(rebase.start_nav),
        tuple((snapshot.date, snapshot.nav, str(snapshot.nav)) for snapshot in rebase.nav_snapshots),
        tuple((flow.date, flow.amount, str(flow.amount)) for flow in rebase.cash_flows),
    )


def _series(rebase: PeriodRebase) -> tuple[list, list, list]:
    """The TWRR, simple ROI and MWRR series of a rebased period, at full precision."""
    snapshots, flows = list(rebase.nav_snapshots), list(rebase.cash_flows)
    return (
        [(point.date, point.twrr, str(point.twrr)) for point in calculate_twrr_series(snapshots, flows)],
        [(point.date, point.roi, str(point.roi)) for point in calculate_simple_roi_series(snapshots, flows)],
        [(point.date, point.mwrr, str(point.mwrr)) for point in period_mwrr_series(snapshots, flows)],
    )


def _dates_between(start: date, end: date) -> set[date]:
    """Every calendar day of [start, end]; empty when start > end."""
    return {start + timedelta(days=offset) for offset in range((end - start).days + 1)}


def _long_window_dates(date_from: date, date_to: date, *, exclusive_start: bool = False) -> set[date]:
    """The days of the 1900 history inside the window, counted on the calendar (no state is read to count them)."""
    start = max(date_from + timedelta(days=1) if exclusive_start else date_from, LONG_FIRST)
    return _dates_between(start, min(date_to, LONG_LAST))


# =============================================================================
# The read log: a state that notes its date each time a field of it is read
# =============================================================================


class _LoggedState(DailyPortfolioState):
    """A daily state that appends its date to ``_reads`` each time a public field of it — its date included — is read."""

    def __getattribute__(self, name: str) -> Any:
        if not name.startswith("_"):
            object.__getattribute__(self, "_reads").append(object.__getattribute__(self, "date"))
        return object.__getattribute__(self, name)


def _logged_history(templates: Sequence[DailyPortfolioState], days: int, first: date) -> tuple[list[DailyPortfolioState], list[date]]:
    """``days`` logged states from ``first``, one a day, their figures shared with ``templates`` in turn: cheap at 46 312."""
    reads: list[date] = []
    figures = [template.__dict__ for template in templates]
    states: list[DailyPortfolioState] = []
    for index in range(days):
        state = object.__new__(_LoggedState)
        state.__dict__.update(figures[index % len(figures)], date=first + timedelta(days=index), _reads=reads)
        states.append(state)
    return states, reads


def _span(days: set[date]) -> tuple[int, date | None, date | None]:
    """(how many, first, last) of a set of days: a failure message that stays readable on 46 312 of them."""
    return len(days), min(days, default=None), max(days, default=None)


def _assert_read_exactly(reads: Sequence[date], expected: set[date]) -> None:
    read = set(reads)
    assert _span(read) == _span(expected), "days read (how many, first, last) vs the window's"
    assert read == expected


def _record_reads(monkeypatch: pytest.MonkeyPatch, method: str, reads: list[date]) -> list[set[date]]:
    """The days each call of ``DerivedViewsBuilder.<method>`` reads, one set per call; the real method answers."""
    build = getattr(DerivedViewsBuilder, method)
    reads_by_call: list[set[date]] = []

    def reading(self: DerivedViewsBuilder, *args: Any, **kwargs: Any) -> Any:
        reads.clear()
        result = build(self, *args, **kwargs)
        reads_by_call.append(set(reads))
        return result

    monkeypatch.setattr(DerivedViewsBuilder, method, reading)
    return reads_by_call


# =============================================================================
# The service on an empty database
# =============================================================================


class _NoRows:
    """The result of a query that finds nothing, read in any of the ways the service reads one."""

    def scalars(self) -> _NoRows:
        return self

    def all(self) -> list:
        return []

    def fetchall(self) -> list:
        return []


class _EmptyDatabase:
    """A session over an empty database: every query returns no row, every lookup by key finds nothing."""

    async def execute(self, *_args: Any, **_kwargs: Any) -> _NoRows:
        return _NoRows()

    async def get(self, *_args: Any, **_kwargs: Any) -> None:
        return None


# call site -> (service method, builder method it calls)
CALL_SITES: dict[str, tuple[str, str]] = {
    "get_summary-performance_inputs": ("get_summary", "build_performance_inputs"),
    "get_history-history": ("get_history", "build_history"),
    "get_history-performance_inputs": ("get_history", "build_performance_inputs"),
    "get_broker_pnl_history": ("get_broker_pnl_history", "build_broker_pnl_history"),
    "get_pnl_candles": ("get_pnl_candles", "build_pnl_candles"),
    "get_acquisition_funding_history": ("get_acquisition_funding_history", "build_acquisition_funding"),
}

# The windows get_report can ask of the services: start <= end, the end inside the history (it is the engine's last day).
SERVICE_WINDOWS: dict[str, tuple[date | None, date]] = {
    "mid-history": (_day(6), _day(11)),
    "the-whole-history": (_day(0), _day(DAYS - 1)),
    "from-before-the-history": (_day(-3), _day(9)),
    "the-last-day": (_day(DAYS - 1), _day(DAYS - 1)),
    "from-a-flow-day": (_day(8), _day(12)),
    "from-the-day-before-a-buy": (_day(5), _day(13)),
    "open-start": (None, _day(10)),
}


def _record_windows(monkeypatch: pytest.MonkeyPatch, method: str, *, strip: bool = False) -> list[tuple]:
    """Record the window each call of ``DerivedViewsBuilder.<method>`` receives, as a tuple of its window parameters.

    The real method still answers: with the window it was given, or, with ``strip``, with none — HEAD's call.
    """
    names = WINDOW_PARAMETERS[method]
    build = getattr(DerivedViewsBuilder, method)
    calls: list[tuple] = []

    def recording(self: DerivedViewsBuilder, *args: Any, **kwargs: Any) -> Any:
        given = dict(zip(names, args, strict=False)) | kwargs
        calls.append(tuple(given.get(name) for name in names))
        return build(self) if strip else build(self, *args, **kwargs)

    monkeypatch.setattr(DerivedViewsBuilder, method, recording)
    return calls


async def _serve(service_method: str, states: list[DailyPortfolioState], date_from: date | None, date_to: date | None) -> Any:
    """The service method on these states (the engine's result handed over, as get_report does), on an empty database."""
    service = PortfolioService(_EmptyDatabase())
    result = PortfolioCalculationResult(daily_states=states, target_currency=CCY)
    return await getattr(service, service_method)(user_id=1, date_from=date_from, date_to=date_to, target_currency_override=CCY, _precomputed_engine_result=result)


def _dump(output: Any) -> Any:
    """A service output as the API serializes it (JSON mode: every amount as its exact text)."""
    if isinstance(output, list):
        return [item.model_dump(mode="json") for item in output]
    return output.model_dump(mode="json")


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(scope="module")
def history() -> list[DailyPortfolioState]:
    states = _history()
    _assert_the_history_has_its_cases(states)
    return states


@pytest.fixture(scope="module")
def whole(history: list[DailyPortfolioState]) -> dict[str, Any]:
    """Every view of the whole short history, built once without a window: the parity oracle's input."""
    builder = DerivedViewsBuilder(history, CCY)
    return {view: getattr(builder, method)() for view, (method, _exclusive) in VIEWS.items()}


@pytest.fixture(scope="module")
def long_history(history: list[DailyPortfolioState]) -> tuple[list[DailyPortfolioState], list[date], list[date]]:
    """(logged states, their read log, their dates computed on the calendar) of the 1900 history."""
    states, reads = _logged_history(history, LONG_DAYS, LONG_FIRST)
    return states, reads, [LONG_FIRST + timedelta(days=index) for index in range(LONG_DAYS)]


@pytest.fixture(scope="module")
def long_whole_inputs(long_history: tuple[list[DailyPortfolioState], list[date], list[date]]) -> tuple[list, list]:
    """The performance inputs of the whole 1900 history, built once without a window."""
    states, _reads, _dates = long_history
    return DerivedViewsBuilder(states, CCY).build_performance_inputs()


# =============================================================================
# 1. Parity: the windowed views are the whole ones cut as HEAD cut them
# =============================================================================


class TestTheWindowedViewsAreTheWholeOnesCut:
    @pytest.mark.parametrize("view", list(VIEWS))
    @pytest.mark.parametrize(("date_from", "date_to"), list(NAMED_WINDOWS.values()), ids=list(NAMED_WINDOWS))
    def test_a_named_window(self, history, whole, view, date_from, date_to):
        """Each named window, each view: the same points, keys, codes and amounts (Decimal and str) as HEAD's cut."""
        windowed, expected = _parity(view, history, whole, date_from, date_to)
        assert windowed == expected

    def test_every_window_of_the_history(self, history, whole):
        """Every pair of bounds from two days before the history to two days after it, open bounds included (17 × 17
        windows), each view."""
        bounds = [None, *(_day(index) for index in range(-2, DAYS + 2))]
        mismatches: list[tuple] = []
        for view in VIEWS:
            for date_from in bounds:
                for date_to in bounds:
                    windowed, expected = _parity(view, history, whole, date_from, date_to)
                    if windowed != expected:
                        mismatches.append((view, date_from, date_to))
        assert mismatches == [], f"{len(mismatches)} windows differ from HEAD's cut, the first ones: {mismatches[:10]}"

    def test_a_window_starting_on_a_buy_leaves_that_buy_to_the_period_before(self, history):
        """The flow series' boundary, stated on its own: from day 6 (a BUY) to day 10, the funding has day 10 only,
        while the level series start on day 6."""
        builder = DerivedViewsBuilder(history, CCY)
        assert [point["date"] for point in builder.build_acquisition_funding(_day(6), _day(10))] == [_day(10)]
        assert [point["date"] for point in builder.build_history(_day(6), _day(10))] == [_day(index) for index in range(6, 11)]
        assert [point["date"] for point in builder.build_pnl_candles(_day(6), _day(10))] == [_day(7), _day(8), _day(10)]

    def test_an_empty_history_has_empty_views_for_any_window(self):
        builder = DerivedViewsBuilder([], CCY)
        for date_from, date_to in NAMED_WINDOWS.values():
            assert builder.build_history(date_from, date_to) == []
            assert builder.build_broker_pnl_history(date_from, date_to) == {}
            assert builder.build_pnl_candles(date_from, date_to) == []
            assert builder.build_acquisition_funding(date_from, date_to) == []
            assert builder.build_performance_inputs(date_from) == ([], [])

    @pytest.mark.parametrize("view", list(VIEWS))
    @pytest.mark.parametrize(("date_from", "date_to"), list(LONG_WINDOWS.values()), ids=list(LONG_WINDOWS))
    def test_a_window_of_the_1900_history(self, long_history, view, date_from, date_to):
        """46 312 days: the windowed view equals the same view built on the states a linear cut keeps."""
        states, _reads, dates = long_history
        method, exclusive_start = VIEWS[view]
        kept = [state for state, day in zip(states, dates, strict=True) if _inside(day, date_from, date_to, exclusive_start=exclusive_start)]
        windowed = getattr(DerivedViewsBuilder(states, CCY), method)(date_from, date_to)
        assert _comparable(windowed) == _comparable(getattr(DerivedViewsBuilder(kept, CCY), method)())


# =============================================================================
# 2. Performance inputs: the rebased period is the same
# =============================================================================

REBASE_DAYS = [None, *(_day(index) for index in range(-3, DAYS + 3))]
REBASE_IDS = ["open", *(str(day) for day in REBASE_DAYS[1:])]


class TestThePerformanceInputsGiveTheSamePeriod:
    @pytest.mark.parametrize("date_from", REBASE_DAYS, ids=REBASE_IDS)
    def test_the_rebased_period_is_the_same(self, history, date_from):
        """rebase_to_period(windowed(d), d) == rebase_to_period(whole(), d): start date, start NAV, snapshots, flows."""
        builder = DerivedViewsBuilder(history, CCY)
        whole_period = rebase_to_period(*builder.build_performance_inputs(), date_from)
        windowed_period = rebase_to_period(*builder.build_performance_inputs(date_from), date_from)
        assert _rebase_figures(windowed_period) == _rebase_figures(whole_period)

    @pytest.mark.parametrize("date_from", REBASE_DAYS, ids=REBASE_IDS)
    def test_the_return_series_are_the_same(self, history, date_from):
        """TWRR, simple ROI and MWRR series of the two rebased periods: the same points, Decimal and str."""
        builder = DerivedViewsBuilder(history, CCY)
        whole_series = _series(rebase_to_period(*builder.build_performance_inputs(), date_from))
        windowed_series = _series(rebase_to_period(*builder.build_performance_inputs(date_from), date_from))
        if date_from is None or date_from < LAST:
            twrr, _roi, mwrr = whole_series
            assert twrr and any(rate is not None for _point_date, rate, _text in mwrr), "barrier: a period of two days or more has rates to compare"
        assert windowed_series == whole_series

    @pytest.mark.parametrize("date_from", REBASE_DAYS[1:], ids=REBASE_IDS[1:])
    def test_the_windowed_inputs_are_the_whole_ones_from_the_opening(self, history, date_from):
        """The snapshots from the opening (the last one on or before d, else the first) and the flows dated after it;
        never more snapshots than the window's plus one."""
        builder = DerivedViewsBuilder(history, CCY)
        snapshots, flows = builder.build_performance_inputs()
        opening = max((index for index, snapshot in enumerate(snapshots) if snapshot.date <= date_from), default=0)
        windowed_snapshots, windowed_flows = builder.build_performance_inputs(date_from)
        assert [(s.date, s.nav, str(s.nav)) for s in windowed_snapshots] == [(s.date, s.nav, str(s.nav)) for s in snapshots[opening:]]
        assert [(f.date, f.amount, str(f.amount)) for f in windowed_flows] == [(f.date, f.amount, str(f.amount)) for f in flows if f.date > snapshots[opening].date]
        assert len(windowed_snapshots) <= sum(1 for state in history if state.date >= date_from) + 1

    @pytest.mark.parametrize("date_from", [LONG_FIRST - timedelta(days=1), LONG_FIRST, date(1950, 1, 1), LONG_LAST - timedelta(days=365), LONG_LAST - timedelta(days=30), LONG_LAST, LONG_LAST + timedelta(days=1)], ids=str)
    def test_the_rebased_period_of_the_1900_history_is_the_same(self, long_history, long_whole_inputs, date_from):
        states, _reads, _dates = long_history
        windowed_inputs = DerivedViewsBuilder(states, CCY).build_performance_inputs(date_from)
        assert _rebase_figures(rebase_to_period(*windowed_inputs, date_from)) == _rebase_figures(rebase_to_period(*long_whole_inputs, date_from))

    def test_the_return_series_of_the_last_month_of_the_1900_history_are_the_same(self, long_history, long_whole_inputs):
        states, _reads, _dates = long_history
        date_from = LONG_LAST - timedelta(days=30)
        windowed_inputs = DerivedViewsBuilder(states, CCY).build_performance_inputs(date_from)
        assert _series(rebase_to_period(*windowed_inputs, date_from)) == _series(rebase_to_period(*long_whole_inputs, date_from))


# =============================================================================
# 3. Cost: a builder given a window reads no state outside it
# =============================================================================


class TestOnlyTheWindowIsRead:
    @pytest.mark.parametrize("view", list(VIEWS))
    def test_the_read_log_sees_a_whole_build(self, history, view):
        """Control: without a window every state is read, so an empty or partial log below is the builder's doing."""
        states, reads = _logged_history(history, DAYS, FIRST)
        builder = DerivedViewsBuilder(states, CCY)
        reads.clear()
        getattr(builder, VIEWS[view][0])()
        _assert_read_exactly(reads, _dates_between(FIRST, LAST))

    @pytest.mark.parametrize("view", list(VIEWS))
    @pytest.mark.parametrize(("date_from", "date_to"), list(LONG_WINDOWS.values()), ids=list(LONG_WINDOWS))
    def test_a_view_reads_only_the_days_of_its_window(self, long_history, view, date_from, date_to):
        """On 46 312 days, the days read are the window's — ``(from, to]`` for the funding —, not one more."""
        states, reads, _dates = long_history
        method, exclusive_start = VIEWS[view]
        builder = DerivedViewsBuilder(states, CCY)
        reads.clear()
        getattr(builder, method)(date_from, date_to)
        _assert_read_exactly(reads, _long_window_dates(date_from, date_to, exclusive_start=exclusive_start))

    @pytest.mark.parametrize("date_from", [LONG_LAST - timedelta(days=365), LONG_LAST - timedelta(days=30), LONG_LAST, LONG_LAST + timedelta(days=5), date(1950, 1, 1)], ids=str)
    def test_the_performance_inputs_read_only_the_opening_and_what_follows(self, long_history, date_from):
        """On 46 312 days: the opening state (the last on or before d) and the states after it; as many snapshots, never
        more than the window's plus one."""
        states, reads, _dates = long_history
        builder = DerivedViewsBuilder(states, CCY)
        reads.clear()
        snapshots, _flows = builder.build_performance_inputs(date_from)
        expected = _dates_between(min(date_from, LONG_LAST), LONG_LAST)
        _assert_read_exactly(reads, expected)
        assert len(snapshots) == len(expected)
        assert len(snapshots) <= len(_long_window_dates(date_from, LONG_LAST)) + 1


class TestTheServiceBuildsOnlyTheWindow:
    """Each call site, on a 1 000-day history with its last month as window: the builder it calls reads that month only
    (the performance inputs: from the opening, the window's first day, to the end). On HEAD the call site passes no
    window and its builder reads all 1 000 days: a cost red, the same a call site that drops its window gives."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("service_method", "method"), list(CALL_SITES.values()), ids=list(CALL_SITES))
    async def test_the_call_site_reads_only_the_window(self, history, monkeypatch, service_method, method):
        first, days = date(2023, 1, 1), 1_000
        states, reads = _logged_history(history, days, first)
        date_from, date_to = first + timedelta(days=days - 31), first + timedelta(days=days - 1)
        reads_by_call = _record_reads(monkeypatch, method, reads)
        await _serve(service_method, states, date_from, date_to)
        assert len(reads_by_call) == 1, f"one call of {method}, got {len(reads_by_call)}"
        start = date_from + timedelta(days=1) if method == "build_acquisition_funding" else date_from
        _assert_read_exactly(reads_by_call[0], _dates_between(start, date_to))


# =============================================================================
# 4. Wiring: each call site of PortfolioService hands the builder its window
# =============================================================================


class TestTheServiceHandsItsWindowToTheBuilder:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(("service_method", "method"), list(CALL_SITES.values()), ids=list(CALL_SITES))
    async def test_the_call_site_passes_the_window(self, history, monkeypatch, service_method, method):
        """The builder is called once, with the service's window: (from, to), or (from,) for the performance inputs."""
        date_from, date_to = _day(6), _day(11)
        calls = _record_windows(monkeypatch, method)
        await _serve(service_method, history, date_from, date_to)
        assert calls == [(date_from, date_to)[: len(WINDOW_PARAMETERS[method])]]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("date_from", "date_to"), list(SERVICE_WINDOWS.values()), ids=list(SERVICE_WINDOWS))
    @pytest.mark.parametrize(("service_method", "method"), list(CALL_SITES.values()), ids=list(CALL_SITES))
    async def test_the_output_is_the_same_as_without_the_window(self, history, monkeypatch, service_method, method, date_from, date_to):
        """The service's output, serialized as the API does, with the call site stripped of its window (HEAD's call)
        and as it is."""
        with monkeypatch.context() as patch:
            stripped_calls = _record_windows(patch, method, strip=True)
            stripped = _dump(await _serve(service_method, history, date_from, date_to))
        assert len(stripped_calls) == 1, "barrier: the stripped run went through the call site"
        assert _dump(await _serve(service_method, history, date_from, date_to)) == stripped


# =============================================================================
# 5. A window holding no state: get_broker_pnl_history lists every broker, as HEAD did
# =============================================================================

# Windows of the short history that hold no state. get_report never asks one (its window ends on the engine's last day,
# its start no later), but get_broker_pnl_history answers them all.
EMPTY_WINDOWS: dict[str, tuple[date | None, date | None]] = {
    "from-after-the-last-state": (_day(DAYS + 2), None),
    "from-the-day-after-the-last-state-bounded": (_day(DAYS), _day(DAYS + 5)),
    "from-after-to-inside-the-history": (_day(9), _day(4)),
    "from-the-day-after-to": (_day(5), _day(4)),
    "before-the-first-state": (_day(-5), _day(-1)),
    "to-before-the-first-state": (None, _day(-1)),
}

# A history the engine never writes: broker 22 on days 0-6 only, broker 11 from day 2, broker 33 from day 5. HEAD listed
# the brokers in the order they first appear, 22, 11, 33 — neither the first state's (22), nor the last state's (11, 33),
# nor sorted, nor a set's order. On it the fallback is pinned without leaning on the engine's invariant (section 6).
IRREGULAR_PRESENCE: dict[int, range] = {22: range(0, 7), 11: range(2, DAYS), 33: range(5, DAYS)}
IRREGULAR_ORDER = (22, 11, 33)


def _irregular_history(states: Sequence[DailyPortfolioState]) -> list[DailyPortfolioState]:
    return [dataclasses.replace(state, broker_contributions={broker_id: state.broker_contributions[broker_id] for broker_id in IRREGULAR_ORDER if index in IRREGULAR_PRESENCE[broker_id]}) for index, state in enumerate(states)]


async def _broker_pnl_history_against_head(monkeypatch: pytest.MonkeyPatch, states: list[DailyPortfolioState], date_from: date | None, date_to: date | None) -> tuple[Any, Any]:
    """(get_broker_pnl_history as it is, the same with its builder call stripped of the window — HEAD's call), as JSON."""
    with monkeypatch.context() as patch:
        stripped_calls = _record_windows(patch, "build_broker_pnl_history", strip=True)
        head = _dump(await _serve("get_broker_pnl_history", states, date_from, date_to))
    assert len(stripped_calls) == 1, "barrier: the stripped run went through the call site"
    return _dump(await _serve("get_broker_pnl_history", states, date_from, date_to)), head


def _brokers_and_points(output: list[dict]) -> list[tuple[int, str, list]]:
    return [(item["broker_id"], item["broker_name"], item["points"]) for item in output]


class TestAnEmptyWindowListsEveryBroker:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(("date_from", "date_to"), list(EMPTY_WINDOWS.values()), ids=list(EMPTY_WINDOWS))
    async def test_every_broker_with_no_point(self, history, monkeypatch, date_from, date_to):
        """Every broker, in HEAD's order, with an empty series: the output of HEAD's call, field by field."""
        output, head = await _broker_pnl_history_against_head(monkeypatch, history, date_from, date_to)
        assert _brokers_and_points(head) == [(broker_id, f"Broker {broker_id}", []) for broker_id in BROKERS], "barrier: HEAD's call lists every broker"
        assert output == head

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("date_from", "date_to"), list(EMPTY_WINDOWS.values()), ids=list(EMPTY_WINDOWS))
    async def test_every_broker_in_the_order_they_first_appear(self, history, monkeypatch, date_from, date_to):
        """On a history whose first state lacks two brokers and whose last state lacks another: still every broker, in
        the order they first appear, as HEAD's call gives them."""
        states = _irregular_history(history)
        first_state, last_state = min(states, key=lambda state: state.date), max(states, key=lambda state: state.date)
        assert (list(first_state.broker_contributions), list(last_state.broker_contributions)) == ([22], [11, 33]), "barrier: the first state lacks 11 and 33, the last lacks 22"
        output, head = await _broker_pnl_history_against_head(monkeypatch, states, date_from, date_to)
        assert _brokers_and_points(head) == [(broker_id, f"Broker {broker_id}", []) for broker_id in IRREGULAR_ORDER], "barrier: HEAD's call lists every broker, in first-appearance order"
        assert output == head


# =============================================================================
# 6. The engine's invariant: every state lists every broker of the scope, in one order
# =============================================================================
#
# What the windowed get_broker_pnl_history relies on for a window that holds states: the brokers of that window are those
# of the whole history, in the same order, because DailyStateBuilder writes every broker of the scope on every day —
# one construction site over the fixed set of the brokers of its transactions, and a quiet day copies the day before's.
# No engine test pinned the keys or their order: test_broker_pnl_contributions.py reads given brokers' lines and sums
# them, test_fx_only_days.py reads the lines it expects, test_single_replay.py checks a quiet day's dict is a copy.
#
# The run is a real one, the way calculate() feeds the builder: classifier, average costs, native cash, mark series.
# Broker 30 deposits and buys on day 0, broker 10 deposits on day 3 and earns interest on day 9, broker 20 deposits on
# day 7 and withdraws on day 11, broker 40's only deposit is on day 20, after the run's last day (the engine replays the
# scope's every transaction, whatever its date). Their ids are chosen so the first-appearance order (30, 10, 20, 40) is
# not a set's order.

ENGINE_FIRST = date(2025, 6, 2)
ENGINE_DAYS = 15
ENGINE_ASSET = 100
ENGINE_BROKERS = frozenset({10, 20, 30, 40})


def _engine_day(index: int) -> date:
    return ENGINE_FIRST + timedelta(days=index)


def _engine_tx(tx_id: int, broker_id: int, kind: str, day: int, amount: str, *, quantity: str = "0", asset_id: int | None = None) -> MagicMock:
    tx = MagicMock()
    tx.id = tx_id
    tx.broker_id = broker_id
    tx.type = TransactionType(kind)
    tx.date = _engine_day(day)
    tx.amount = D(amount)
    tx.currency = CCY
    tx.quantity = D(quantity)
    tx.asset_id = asset_id
    tx.related_transaction_id = None
    tx.cost_basis_override = None
    tx.cost_basis_currency = None
    tx.asset_event_id = None
    return tx


def _engine_transactions() -> list[MagicMock]:
    return [
        _engine_tx(1, 30, "DEPOSIT", 0, "1000"),
        _engine_tx(2, 30, "BUY", 0, "-500", quantity="5", asset_id=ENGINE_ASSET),
        _engine_tx(3, 10, "DEPOSIT", 3, "400"),
        _engine_tx(4, 20, "DEPOSIT", 7, "250"),
        _engine_tx(5, 10, "INTEREST", 9, "3.25"),
        _engine_tx(6, 20, "WITHDRAWAL", 11, "-50"),
        _engine_tx(7, 40, "DEPOSIT", 20, "99"),
    ]


def _engine_run(monkeypatch: pytest.MonkeyPatch) -> tuple[list[DailyPortfolioState], list[date]]:
    """(the run's states, the days the builder computed rather than carried)."""
    computed: list[date] = []
    compute_in_transit = DailyStateBuilder._compute_in_transit

    def counting(self: DailyStateBuilder, dt: date, *args: Any, **kwargs: Any) -> Any:
        computed.append(dt)
        return compute_in_transit(self, dt, *args, **kwargs)

    monkeypatch.setattr(DailyStateBuilder, "_compute_in_transit", counting)
    transactions = _engine_transactions()
    classification = ScopeAwareTransactionClassifier(scope_broker_ids=set(ENGINE_BROKERS), all_transactions=transactions, broker_shares=dict.fromkeys(ENGINE_BROKERS, D("1"))).classify()
    price_map = {ENGINE_ASSET: [(_engine_day(0), D("100"), CCY), (_engine_day(9), D("110"), CCY)]}
    date_from, date_to = _engine_day(0), _engine_day(ENGINE_DAYS - 1)
    series = build_asset_price_series(price_rows=price_map[ENGINE_ASSET], transactions=[tx for tx in transactions if tx.asset_id == ENGINE_ASSET], split_linked_tx_ids=set(), asset_currency=CCY, quote_base_quantity=1)
    builder = DailyStateBuilder(
        classified_txs=classification.classified,
        in_transit_intervals=classification.in_transit_intervals,
        external_cash_flows=classification.external_cash_flows,
        price_map=price_map,
        quote_base_map={},
        fx_rate_map={},
        asset_classifications={},
        asset_types={ENGINE_ASSET: "Stock"},
        asset_currencies={ENGINE_ASSET: CCY},
        average_costs=engine_average_costs(classification.classified, asset_currencies={ENGINE_ASSET: CCY}, target_currency=CCY, fx_rate_map={}, date_to=date_to),
        native_cash=engine_native_cash(classification.classified, target_currency=CCY, fx_rate_map={}, date_to=date_to),
        target_currency=CCY,
        date_from=date_from,
        date_to=date_to,
        mark_series={ENGINE_ASSET: series},
    )
    return builder.build().daily_states, computed


class TestTheEngineListsEveryBrokerEveryDay:
    def test_every_state_has_the_same_brokers_in_the_same_order(self, monkeypatch):
        states, computed = _engine_run(monkeypatch)
        days = [state.date for state in states]
        assert days == [_engine_day(index) for index in range(ENGINE_DAYS)], "barrier: one state a day"
        assert {_engine_day(index) for index in (0, 3, 7, 9, 11)} <= set(computed), f"barrier: each broker's first movement is a computed day: {computed}"
        assert {_engine_day(index) for index in (1, 2, 4, 5)} <= set(days) - set(computed), f"barrier: quiet days between the brokers' first movements are carried: {computed}"
        by_day = {state.date: state.broker_contributions for state in states}
        assert (by_day[_engine_day(2)][10].capital_contribution, by_day[_engine_day(3)][10].capital_contribution) == (D("0"), D("400")), "barrier: broker 10 is listed before its first movement, with nothing"

        orders = {tuple(contributions) for contributions in by_day.values()}
        assert len(orders) == 1, f"every state lists its brokers in one order: {sorted(orders)}"
        assert set(orders.pop()) == {tx.broker_id for tx in _engine_transactions()} == ENGINE_BROKERS, "the brokers listed are every broker of the scope with a transaction"
        assert all(line.broker_id == broker_id for contributions in by_day.values() for broker_id, line in contributions.items())

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("date_from", "date_to"),
        [(_engine_day(1), _engine_day(2)), (_engine_day(4), _engine_day(ENGINE_DAYS - 1)), (_engine_day(12), _engine_day(12)), (_engine_day(ENGINE_DAYS + 1), None), (_engine_day(6), _engine_day(5))],
        ids=["before-two-brokers-start", "to-the-end", "one-day", "after-the-last-state", "from-after-to"],
    )
    async def test_on_its_states_any_window_lists_the_brokers_as_head_did(self, monkeypatch, date_from, date_to):
        """The consequence, on the engine's own states: get_broker_pnl_history, windowed, is HEAD's for a window that
        holds states — brokers with nothing yet included — and for one that holds none."""
        states, _computed = _engine_run(monkeypatch)
        output, head = await _broker_pnl_history_against_head(monkeypatch, states, date_from, date_to)
        assert {item["broker_id"] for item in head} == ENGINE_BROKERS, "barrier: HEAD's call lists every broker"
        assert output == head

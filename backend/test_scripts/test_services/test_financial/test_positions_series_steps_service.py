"""J5-5 (#48) — RED tests: ``POST /portfolio/positions-series`` answers STEPS, not one point per day (contract MF-P4b §0, §1.1, §1.4, §8).

Until J5-5 a series has one point per calendar day from ``first_date`` to ``last_date``. After it, each point is a STEP:
``date`` (the first day it holds) and ``through`` (the last day, inclusive); the response carries ``range = {start, end}``.
The contract of the steps, pinned here on the service:

* a position's steps are **contiguous** from ``first_date`` to ``last_date`` (the first starts on ``first_date``, each one
  starts the day after the previous one's ``through``, the last ends on ``last_date``: the step the Periodo row shows), in
  order, not overlapping, and **maximal**: two consecutive steps never carry identical values (compared as the JSON text, so
  ``1.10`` and ``1.1`` differ);
* **expanding** every step over ``date``..``through`` gives the daily series of today, field for field. The old code goes
  away with the cure, so the oracle here does not call it: it is the *Performance table* (``get_positions_contribution``),
  which is the definition of the series (``position_series`` module docstring: «the last point of a series is the table's
  row»). For a step, the table of the period ``date_from``..``d`` at ``d`` = the step's ``date`` and its ``through`` gives its
  ``period_pnl`` (and its ``end_value``, the market value): the step holds both, on every day it covers. That oracle is
  independent of the representation. (Not on the days of a whole transfer in transit: the table has no row for a position that is gone);
* the days of a transfer in transit keep the pnl of the last day held (today ``points[-1]``): a sampling design would lose it;
* an asset summed over its brokers (``broker_id`` None) has its steps on the union of the brokers' change days;
* a first transaction typed in year 1 costs steps, not 740 000 days.

The reads are ``response.model_dump(mode="json")``: ``through`` and ``range`` are defined by another workstream (``StepSpan``,
``DateSpan`` in ``schemas/common.py``), and this file names none of its classes, so that today a red fails on an assertion
(«no `through`»), never on an ImportError.

Pure-level tests of ``build_position_series`` are still to write once its step output exists (see the J5-5 report).

Two books, the ledger of ``test_positions_series_service`` (a close every day) and a weekly one (closes on Mondays only: the
prices move once a week, so the steps are long).
"""

# ruff: noqa: F811 — the fixtures are imported by name from test_positions_series_service and used as arguments
from __future__ import annotations

import sys
import tracemalloc
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

import pytest

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

import backend.app.services.financial_math.portfolio.position_series as position_series_module
from backend.app.db.models import PriceHistory, TransactionType
from backend.app.schemas.common import OpenDateRangeModel
from backend.app.schemas.portfolio import PositionKey, PositionsSeriesQuery
from backend.app.services.portfolio_service import PortfolioService
from backend.test_scripts.test_services.test_financial import test_positions_series_service as base
from backend.test_scripts.test_services.test_financial.test_positions_series_service import (  # noqa: F401 — fixtures the tests of this module use
    clean_portfolio_caches,
    engine,
    keep_alive,
    session,
)

D = Decimal
EUR = base.EUR
FROM = base.FROM
TO = base.TO
T = TransactionType

#: The fields of a step that carry a value (everything but its span and the key).
VALUE_FIELDS = ("quantity", "market_value", "cost_basis", "pnl", "base", "pnl_percent", "valuation_source", "complete")

#: The starts: before the trades, between them, a transfer in transit (the weekly book's 27 Feb -> 1 Mar), after it, after the
#: closing of a position (20 Mar).
STARTS = [FROM, date(2024, 1, 20), date(2024, 2, 26), date(2024, 2, 28), date(2024, 3, 2), date(2024, 3, 20)]


# =============================================================================
# Books
# =============================================================================


@dataclass(frozen=True)
class Book:
    user_id: int
    positions: list[tuple[int | None, int]]


def _mondays(asset, first: date, last: date, *, start: str = "100", step: str = "1.5") -> list[PriceHistory]:
    """One close a week, on Mondays: the price (and the value of what is held) moves once a week."""
    rows, price, day = [], D(start), first + timedelta(days=(7 - first.weekday()) % 7)
    while day <= last:
        rows.append(PriceHistory(asset_id=asset.id, date=day, open=price, high=price, low=price, close=price, volume=D("1"), currency=EUR, source_plugin_key="ps_test"))
        price += D(step)
        day += timedelta(days=7)
    return rows


async def _daily_book(session, keep_alive) -> Book:
    """``base._ledger``: A and B at one broker, a close every day. A: bought 10 on 10 Jan, 4 sold on 20 Feb, dividend 1 Mar, fee 5 Mar; B: bought 5 on 15 Jan."""
    user, broker, a, b = await base._ledger(session, keep_alive, "stp")
    return Book(user.id, [(broker.id, a.id), (broker.id, b.id), (None, a.id)])


async def _weekly_book(session, keep_alive) -> Book:
    """Two brokers, closes on Mondays only. Broker 1: A bought 10 on 10 Jan, 2 sold on 21 Feb, dividend 6 Mar, fee 14 Mar, 3 sent to broker 2 on 27 Feb
    (they arrive on 1 Mar: in transit on 28 and 29 Feb; broker 1 keeps 5); B bought 5 on 17 Jan. Broker 2: A arrives on 1 Mar, all 3 sold on 20 Mar (the
    position closes). The asset A summed over the two brokers is asked as well."""
    user, [first, second] = await base._user(session, keep_alive, "stpwk", brokers=2)
    a, b = await base._asset(session, keep_alive, "stpwkA"), await base._asset(session, keep_alive, "stpwkB")
    out_leg = base._tx(first, a, T.TRANSFER, date(2024, 2, 27), "-3", "0")
    in_leg = base._tx(second, a, T.TRANSFER, date(2024, 3, 1), "3", "0")
    in_leg.cost_basis_override, in_leg.cost_basis_currency = D("330"), EUR
    await base._persist(
        session,
        keep_alive,
        base._tx(first, None, T.DEPOSIT, date(2024, 1, 2), "0", "8000"),
        base._tx(second, None, T.DEPOSIT, date(2024, 1, 2), "0", "2000"),
        base._tx(first, a, T.BUY, date(2024, 1, 10), "10", "-1000"),
        base._tx(first, b, T.BUY, date(2024, 1, 17), "5", "-500"),
        base._tx(first, a, T.SELL, date(2024, 2, 21), "-2", "260"),
        base._tx(first, a, T.DIVIDEND, date(2024, 3, 6), "0", "12"),
        base._tx(first, a, T.FEE, date(2024, 3, 14), "0", "-1"),
        out_leg,
        in_leg,
        base._tx(second, a, T.SELL, date(2024, 3, 20), "-3", "400"),
        *_mondays(a, date(2024, 1, 1), TO),
        *_mondays(b, date(2024, 1, 1), TO, start="50", step="-0.5"),
    )
    out_leg.related_transaction_id, in_leg.related_transaction_id = in_leg.id, out_leg.id
    await session.flush()
    return Book(user.id, [(first.id, a.id), (second.id, a.id), (None, a.id), (first.id, b.id)])


BOOKS = {"daily": _daily_book, "weekly": _weekly_book}


def _positions_query(positions: list[tuple[int | None, int]], date_from: date | None, date_to: date = TO) -> PositionsSeriesQuery:
    return PositionsSeriesQuery(
        date_range=OpenDateRangeModel(start=date_from, end=date_to),
        target_currency=EUR,
        positions=[PositionKey(broker_id=broker, asset_id=asset) for broker, asset in positions],
    )


async def _series(session, book: Book, date_from: date | None, positions=None) -> dict:
    """The answer of ``get_positions_series`` as JSON: ``through`` and ``range`` are read by name."""
    response = await PortfolioService(session).get_positions_series(user_id=book.user_id, query=_positions_query(book.positions if positions is None else positions, date_from))
    return response.model_dump(mode="json")


# =============================================================================
# The reading of a step list
# =============================================================================


def _label(series: dict) -> str:
    key = series["key"]
    return f"position (broker {key['broker_id']}, asset {key['asset_id']})"


def _values(point: dict) -> tuple:
    """A step's values as the JSON text: ``Decimal('1.10')`` and ``Decimal('1.1')`` are two values."""
    return tuple(point.get(name) for name in VALUE_FIELDS)


def _step_at(points: list[dict], day: date) -> dict:
    """The step that holds ``day``: exactly one."""
    holding = [point for point in points if date.fromisoformat(point["date"]) <= day <= date.fromisoformat(point["through"])]
    assert len(holding) == 1, f"{len(holding)} steps hold {day}"
    return holding[0]


def assert_a_list_of_steps(series: dict) -> None:
    """The invariants of a position's steps: ``through`` everywhere, contiguous from ``first_date`` to ``last_date``, in order, not
    overlapping, maximal. A series never held in the window has none."""
    points = series["points"]
    if not points:
        return
    where = _label(series)
    missing = [point["date"] for point in points if "through" not in point]
    assert not missing, f"{where}: {len(missing)} of {len(points)} points have no `through` (the series is still one point per day)"
    assert date.fromisoformat(points[0]["date"]) == date.fromisoformat(series["first_date"]), f"{where}: the first step starts {points[0]['date']}, first_date is {series['first_date']}"
    assert date.fromisoformat(points[-1]["through"]) == date.fromisoformat(series["last_date"]), f"{where}: the last step ends {points[-1]['through']}, last_date is {series['last_date']}"
    previous: dict | None = None
    for point in points:
        first, last = date.fromisoformat(point["date"]), date.fromisoformat(point["through"])
        assert first <= last, f"{where}: step {first}..{last} ends before it starts"
        if previous is not None:
            previous_last = date.fromisoformat(previous["through"])
            assert first > previous_last, f"{where}: step {first}..{last} starts inside the previous one, which ends {previous_last}"
            assert first == previous_last + timedelta(days=1), f"{where}: a hole between {previous_last} and {first}: the steps are contiguous"
            assert _values(point) != _values(previous), f"{where}: the steps ending {previous_last} and starting {first} hold identical values: that is one step"
        previous = point


def assert_a_range(response: dict) -> None:
    """The response carries the window it answers: ``range = {start, end}``, every series inside it."""
    assert "range" in response and response["range"] is not None, "the response has no `range`"
    start, end = date.fromisoformat(response["range"]["start"]), date.fromisoformat(response["range"]["end"])
    assert start <= end, f"range {start}..{end} ends before it starts"
    for series in response["series"]:
        if series["points"]:
            assert start <= date.fromisoformat(series["first_date"]) and date.fromisoformat(series["last_date"]) <= end, f"{_label(series)}: {series['first_date']}..{series['last_date']} is outside the range {start}..{end}"


# =============================================================================
# 1. The oracle: the Periodo table, at the first and the last day of every step
# =============================================================================


def _days_to_check(series: dict) -> set[date]:
    """The first and the last day of every step, but for the days a whole transfer is in transit (``closed_on`` .. the day before ``last_date``): the
    table has no row for a position that is gone, while the series keeps the pnl of the last day held until the arrival. Those days are pinned by
    ``test_red_the_days_in_transit_are_one_step_with_the_pnl_of_the_last_day_held``."""
    in_transit: set[date] = set()
    if series["closed_on"] is not None:
        day, arrival = date.fromisoformat(series["closed_on"]), date.fromisoformat(series["last_date"])
        while day < arrival:
            in_transit.add(day)
            day += timedelta(days=1)
    return {date.fromisoformat(point[name]) for point in series["points"] for name in ("date", "through")} - in_transit


def _periodo_figures(rows, key: dict) -> tuple[Decimal | None, Decimal | None]:
    """The table's ``period_pnl`` and ``end_value`` for a position: the row of the broker, or, for an asset summed over its brokers (broker None),
    the sum of the known figures of its brokers' rows."""
    mine = [row for row in rows if row.asset_id == key["asset_id"] and (key["broker_id"] is None or row.broker_id == key["broker_id"])]
    pnls = [row.period_pnl for row in mine if row.period_pnl is not None]
    values = [row.end_value for row in mine if row.end_value is not None]
    return (sum(pnls, D("0")) if pnls else None, sum(values, D("0")) if values else None)


@pytest.mark.asyncio
@pytest.mark.parametrize("book_name", ["daily", "weekly"])
@pytest.mark.parametrize("start", STARTS, ids=[day.isoformat() for day in STARTS])
async def test_red_every_step_holds_the_periodo_rows_figures_on_each_day_it_covers(session, keep_alive, book_name, start):
    """RED until J5-5. For each asked position: the steps are contiguous, ordered, non-overlapping and maximal from ``first_date`` to ``last_date``,
    the response has its ``range``, and on the first and on the last day of every step the Periodo table of ``start``..that day agrees with the step:
    its ``period_pnl`` is the step's ``pnl`` and its ``end_value`` the step's ``market_value`` (a step holds them on every day it covers, so the two
    ends of a step cannot disagree).

    The start 28 Feb has the weekly book's transfer in transit at the start; on it the asset summed over the two brokers (None, A) has the base
    of the known limit J5-4 (a summed asset in transit at the start: base 0, pnl_percent None): the base is NOT asserted here, only the figures
    where today's answer and the table agree.

    Today: the points carry no `through` («no `through`»).
    """
    book = await BOOKS[book_name](session, keep_alive)
    service = PortfolioService(session)

    response = await _series(session, book, start)

    assert_a_range(response)
    assert any(series["points"] for series in response["series"]), "precondition: the book holds a position in the window"
    for series in response["series"]:
        assert_a_list_of_steps(series)
    rows_on: dict[date, list] = {}
    checked = 0
    for series in response["series"]:
        for day in sorted(_days_to_check(series)):
            if day not in rows_on:
                rows_on[day] = (await service.get_positions_contribution(user_id=book.user_id, target_currency_override=EUR, date_from=start, date_to=day)).positions
            pnl, value = _periodo_figures(rows_on[day], series["key"])
            step = _step_at(series["points"], day)
            assert (D(step["pnl"]) if step["pnl"] is not None else None) == pnl, f"{_label(series)} on {day}: the step {step['date']}..{step['through']} has pnl {step['pnl']}, the Periodo table of {start}..{day} has {pnl}"
            assert (D(step["market_value"]) if step["market_value"] is not None else None) == value, f"{_label(series)} on {day}: the step has market value {step['market_value']}, the table has {value}"
            checked += 1
    assert checked > 0, "precondition: the oracle looked at some day"


# =============================================================================
# 2. The weekly closes: the steps are far fewer than the days
# =============================================================================


@pytest.mark.asyncio
async def test_red_weekly_closes_make_far_fewer_steps_than_days(session, keep_alive):
    """RED until J5-5. B (bought 17 Jan at broker 1, still held on 31 Mar) is closed on Mondays only, and nothing else happens to it: 75 days, a few
    steps (one a week, plus the first). The asset A summed over the brokers, 10 Jan..31 Mar, is closed on Mondays too, with six events and a transfer in
    transit: still well under half its days.

    Today: one point per day, no `through`: the assertion on the number of steps fails (75 points for 75 days).
    """
    book = await _weekly_book(session, keep_alive)

    response = await _series(session, book, FROM)

    for series in response["series"]:
        key = series["key"]
        if (key["broker_id"], key["asset_id"]) not in {(book.positions[3]), (book.positions[2])}:
            continue
        days = (date.fromisoformat(series["last_date"]) - date.fromisoformat(series["first_date"])).days + 1
        assert len(series["points"]) * 2 < days, f"{_label(series)}: {len(series['points'])} steps for {days} days: not fewer than half"
        assert_a_list_of_steps(series)


# =============================================================================
# 3. The days in transit keep the pnl of the last day held
# =============================================================================


async def _full_transfer_book(session, keep_alive) -> tuple[Book, int, int, int]:
    """10 bought at broker 1 on 10 Jan for 1 000, all 10 sent on 5 Feb, arriving at broker 2 on 7 Feb (cost basis 100 a unit); the price lifts by half a
    euro a day (100 on 1 Jan, 117 on 4 Feb). Broker 1 is empty from 5 Feb: 5 and 6 Feb are its days in transit. Returns the book and (broker 1, broker 2, asset)."""
    user, [first, second] = await base._user(session, keep_alive, "stpmove", brokers=2)
    asset = await base._asset(session, keep_alive, "stpmoveA")
    out_leg = base._tx(first, asset, T.TRANSFER, date(2024, 2, 5), "-10", "0")
    in_leg = base._tx(second, asset, T.TRANSFER, date(2024, 2, 7), "10", "0")
    in_leg.cost_basis_override, in_leg.cost_basis_currency = D("100"), EUR
    await base._persist(
        session,
        keep_alive,
        base._tx(first, None, T.DEPOSIT, date(2024, 1, 2), "0", "5000"),
        base._tx(first, asset, T.BUY, date(2024, 1, 10), "10", "-1000"),
        out_leg,
        in_leg,
        *base._prices(asset, date(2024, 1, 1), TO, start="100", step="0.5"),
    )
    out_leg.related_transaction_id, in_leg.related_transaction_id = in_leg.id, out_leg.id
    await session.flush()
    positions = [(first.id, asset.id), (second.id, asset.id), (None, asset.id)]
    return Book(user.id, positions), first.id, second.id, asset.id


@pytest.mark.asyncio
async def test_red_the_days_in_transit_are_one_step_with_the_pnl_of_the_last_day_held(session, keep_alive):
    """RED until J5-5. The sender of a whole transfer (broker 1 here, 5..7 Feb): on 4 Feb it holds 10 units at 117 (pnl 10 x 17 = 170 on a base of
    1 000); on 5 and 6 Feb the units are on their way: quantity, value and cost are 0 and the pnl, base and pnl_percent are those of the last day held
    (4 Feb: 170, 1 000, 0.17), not the 0 of an empty position; 7 Feb is the arrival, where the tract settles. So 5 and 6 Feb are ONE step, not the
    step of 4 Feb (the quantity changes) and not the one of 7 Feb (the arrival is a boundary), and the sender's last step ends on 7 Feb.

    A step design that samples the pnl at the step's own first day would lose this: 5 Feb's pnl is not 5 Feb's.

    Today: no `through` (the daily answer holds the same figures day by day: 4 Feb, then 5 and 6 Feb with 0 and 170).
    """
    book, sender_broker, receiver_broker, asset_id = await _full_transfer_book(session, keep_alive)

    response = await _series(session, book, FROM)

    sender = next(series for series in response["series"] if series["key"] == {"broker_id": sender_broker, "asset_id": asset_id})
    assert_a_list_of_steps(sender)
    held, transit_first, transit_last, arrival = (_step_at(sender["points"], date(2024, 2, day)) for day in (4, 5, 6, 7))
    assert transit_first is transit_last or transit_first == transit_last, "5 and 6 Feb, the days in transit, are one step"
    assert (transit_first["date"], transit_first["through"]) == ("2024-02-05", "2024-02-06")
    assert held["through"] == "2024-02-04" and arrival["date"] == "2024-02-07"
    assert (D(transit_first["quantity"]), D(transit_first["market_value"]), D(transit_first["cost_basis"])) == (D("0"), D("0"), D("0"))
    assert D(held["pnl"]) == D("170") and D(held["base"]) == D("1000") and D(held["pnl_percent"]) == D("0.17"), f"precondition: the last day held, {held}"
    assert (D(transit_first["pnl"]), D(transit_first["base"]), D(transit_first["pnl_percent"]), transit_first["complete"]) == (D("170"), D("1000"), D("0.17"), held["complete"])
    assert transit_first["valuation_source"] is None, "the units are on their way: they have no valuation"
    assert sender["last_date"] == "2024-02-07" and sender["points"][-1]["through"] == "2024-02-07" and sender["points"][-1]["date"] == "2024-02-07"


@pytest.mark.asyncio
async def test_red_an_asset_summed_over_the_brokers_goes_through_a_transit_in_steps(session, keep_alive):
    """RED until J5-5. The weekly book's asset A summed over its two brokers, from 1 Jan: broker 1 sends 3 of its 8 units on 27 Feb (they arrive at broker 2
    on 1 Mar), so on 27 Feb the summed quantity falls to 5 and rises back to 8 on 1 Mar. The union of the brokers' change days puts a step boundary on
    27 Feb and one on 1 Mar, and 28 and 29 Feb (the units on their way, the closes of the Mondays 26 Feb and 4 Mar) are inside ONE step with 27 Feb:
    the three days hold the same figures.

    Today: no `through`.
    """
    book = await _weekly_book(session, keep_alive)

    response = await _series(session, book, FROM)

    summed = next(series for series in response["series"] if series["key"]["broker_id"] is None)
    assert_a_list_of_steps(summed)
    transit = _step_at(summed["points"], date(2024, 2, 28))
    assert (transit["date"], transit["through"]) == ("2024-02-27", "2024-02-29"), f"the units on their way are one step from the day they leave: {transit}"
    assert D(transit["quantity"]) == D("5")
    arrival = _step_at(summed["points"], date(2024, 3, 1))
    assert arrival["date"] == "2024-03-01" and D(arrival["quantity"]) == D("8")


# =============================================================================
# 4. A first transaction in year 1 costs steps, not 740 000 days
# =============================================================================

YEAR_ONE_DAY = date(1, 1, 3)
#: ``_PositionReader.on`` is asked once per calendar day by the daily series: this many calls is not a series by steps.
DAYS_ABORT = 5_000
STEPS_BUDGET = 50
PEAK_BYTES = 100 * 1024 * 1024


def _lower_the_floor(monkeypatch: pytest.MonkeyPatch, floor: date) -> list[str]:
    """``EARLIEST_RANGE_START`` is ``floor`` in this process only, in the module that defines it and in every backend module that imported it by value."""
    patched = []
    for name, module in list(sys.modules.items()):
        if name.startswith("backend.app") and module is not None and "EARLIEST_RANGE_START" in vars(module):
            monkeypatch.setattr(module, "EARLIEST_RANGE_START", floor)
            patched.append(name)
    return patched


@pytest.mark.asyncio
async def test_red_a_buy_typed_in_year_one_costs_steps_not_days(session, keep_alive, monkeypatch):
    """RED until J5-5. A BUY dated 3 Jan of year 1 (a typo) at a broker, the position still held, the prices stored only for 2024 (Monday closes), the
    floor of the product lowered to 1 Jan of year 1 in this test's process only, the window open at the start (the whole life): the series of the position
    has few steps (under 50: the first, from year 1 to the first close, and about one a week after it), and the peak of ``tracemalloc`` is under 100 MB.

    The guard: the daily series asks ``_PositionReader.on`` once per calendar day (739 912 days here); a spy raises after 5 000 calls, so that today the
    test fails fast on «still one point per day» instead of building 740 000 points.

    Today: AssertionError from the spy.
    """
    user, [broker] = await base._user(session, keep_alive, "stpyear1")
    asset = await base._asset(session, keep_alive, "stpyear1A")
    await base._persist(
        session,
        keep_alive,
        base._tx(broker, None, T.DEPOSIT, date(1, 1, 2), "0", "5000"),
        base._tx(broker, asset, T.BUY, YEAR_ONE_DAY, "10", "-1000"),
        *_mondays(asset, date(2024, 1, 1), TO),
    )
    patched = _lower_the_floor(monkeypatch, date(1, 1, 1))
    assert "backend.app.utils.datetime_utils" in patched and "backend.app.services.financial_math.portfolio.engine" in patched, f"precondition: the floor is lowered where it is defined and where the engine reads it, {patched}"

    calls = [0]
    original_on = position_series_module._PositionReader.on

    def counting_on(self, day):
        calls[0] += 1
        if calls[0] > DAYS_ABORT:
            raise AssertionError(f"still one point per day: _PositionReader.on called more than {DAYS_ABORT} times")
        return original_on(self, day)

    monkeypatch.setattr(position_series_module._PositionReader, "on", counting_on)

    tracemalloc.start()
    try:
        response = (await PortfolioService(session).get_positions_series(user_id=user.id, query=_positions_query([(broker.id, asset.id)], None))).model_dump(mode="json")
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    [series] = response["series"]
    assert series["first_date"] == YEAR_ONE_DAY.isoformat(), f"precondition: the position starts on the typed day, {series['first_date']}"
    assert_a_list_of_steps(series)
    assert 0 < len(series["points"]) < STEPS_BUDGET, f"{len(series['points'])} steps; at most {STEPS_BUDGET - 1}, one a week of the closes and the first"
    assert peak < PEAK_BYTES, f"tracemalloc peak {peak / 1024 / 1024:.0f} MB; the budget is {PEAK_BYTES // 1024 // 1024} MB"

"""L1a, J5-5 — the lots analysis computed on its change days and given as steps: ``lot_change_days``, ``history_steps``,
``DayRange``, ``price_candidate_days`` and the bisected ``last_day_without_observation``.

J5-5 (D-P4 cure B «serie a gradini», contract MF-P4b §1.3): ``expand_to_days`` is gone — the seven histories are no longer
one row per calendar day of the window — and ``history_steps`` replaces it (a row holds from ``date`` to ``through``, the
rows of one key are ordered, never overlap, are MAXIMAL and leave a gap where the daily answer had no row); ``DayRange`` is the
lazy calendar the service walks instead of a list; ``price_candidate_days`` names the days the market price is read on. The
``lot_change_days`` and ``last_day_without_observation`` tests are L1a's, as they were.

Workstream J «Numeri e analisi», lot L1a. Pure: no DB, no server, no FX — the schemas' own point classes, in-memory
``Transaction`` rows (never added to a session) and the home's daily price series (``financial_math/price_marks.py``).
The service-level reds and the parity battery are in ``test_financial/test_lots_change_days_parity.py``.

WHY. ``lots_analysis_service`` hands every calendar day from the first transaction (floored at 1900-01-01) to the
reading day to the per-day builders of ``financial_math/lots/histories.py`` and ``lots/average_cost_lines.py``, then
trims to the window: a lot bought on 2 Jan 1900 and read on 15 Feb 2021 is valued on 44 240 days per history. Between two
days on which nothing changes — the same converted price, the same estimated mark, no event, no day at cost ending —
every builder answers the same row, re-dated.

THE CONTRACT (J, L1a; new home ``backend/app/services/financial_math/lots/change_days.py``):

- ``lot_change_days(*, days, market_prices, estimated_market_prices, at_cost_until, event_dates)``: the sorted unique
  subset of ``days`` (dense, ascending) made of the first and the last day; every day whose ``market_prices`` entry
  differs from the previous day's (None against a value, or another exact Decimal representation: ``Decimal('1.10')``
  is not ``Decimal('1.1')`` here); every day whose ``estimated_market_prices`` entry differs from the previous day's
  (present or absent, the exact representation of the price, the flag); ``at_cost_until`` + 1 when it is one of
  ``days``; every event date that is one of ``days``; and, for each of those, the next day when it is one of ``days``.
  No day, no change day.
- ``history_steps(rows, *, key, change_days, range_start, range_end)`` (J5-5, it replaced L1a's ``expand_to_days``): ``rows``
  is a builder's output on the change days (one day each: ``through`` = ``date``), grouped by key, dates ascending within a
  key. The result is the steps, keys in the order of their first row: for each key, the key's row on each change day holds
  until the day before the key's next change day (the last one until ``range_end``); a change day without a row of the key,
  after its first, is a gap; consecutive rows with the same figures — the exponent of every Decimal included — are one step,
  the first row's; the steps are clipped to ``range_start``..``range_end`` (a change day before the range speaks for it from
  ``range_start``; nothing before the first change day). Expanding a step over its days gives, field for field, what L1a's
  ``expand_to_days`` gave on each of them.
- ``DayRange(first, last)``: the calendar days ``first``..``last`` as a ``Sequence`` that stores none of them (``len`` and
  indexing are arithmetic, a slice is a ``TypeError``), empty when ``last`` is before ``first``.
- ``price_candidate_days(first, last, observation_dates, rate_days, event_dates, at_cost_until)``: the days of the window the
  converted market price (or a figure built on it) can differ from the day before — a superset of the days ``lot_change_days``
  keeps when it is given every day: the first and the last day, every observation, rate step and event inside the window,
  ``at_cost_until`` + 1, and the day after each of them (when inside the window).
- ``prices.last_day_without_observation(price_series, days)`` keeps its contract — the last of the ascending ``days``
  with no observation on or before it, None when the first already has one — and becomes a bisection:
  ``price_series.resolve(d).is_missing`` is True up to the first observation and False after it.

READING. «For each of those, the next day» is read as written: the first day's next day is a change day, and so is the
day after ``at_cost_until`` + 1; a day that is in only as a next day brings no next day of its own. ``market_prices`` is
given a value for every day here (None or a Decimal); what an absent key means is not part of these tests.

TODAY (HEAD ``b675ada54``): ``change_days`` does not exist. Each of its tests fails on its own with «does not exist yet»
(the module is imported inside the test, ``_change_days_function``), so the file collects and the CONTROL tests run.
``last_day_without_observation`` walks the days one by one: 19 994 calls of ``resolve`` over 20 000 days whose first
observation is the seventh from the end. RED marks a test that fails today, CONTROL one that is green today and after.
"""

import bisect
import importlib
import math
import random
from collections.abc import Callable, Hashable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

import pytest

from backend.app.db.models import Transaction, TransactionType
from backend.app.schemas.portfolio import LotValueHistoryPoint, MarketPriceHistoryPoint
from backend.app.services.financial_math.lots import prices as prices_module
from backend.app.services.financial_math.lots.change_days import DayRange, history_steps, price_candidate_days
from backend.app.services.financial_math.price_marks import AssetPriceSeries, build_asset_price_series
from backend.test_scripts.test_services._lots_steps import compress_days, daily_points, order_by_key

D = Decimal
CHANGE_DAYS_MODULE = "backend.app.services.financial_math.lots.change_days"
MONDAY = date(2024, 3, 4)


def _change_days_function(name: str) -> Callable:
    """``name`` of the new module, imported inside the test: before L1a the module does not exist, and a module-level
    import would turn the whole file, the CONTROL tests included, into one collection error. An import error raised
    inside the module, once it exists, is raised as it is."""
    try:
        module = importlib.import_module(CHANGE_DAYS_MODULE)
    except ModuleNotFoundError as error:
        if error.name != CHANGE_DAYS_MODULE:
            raise
        pytest.fail(f"{CHANGE_DAYS_MODULE} does not exist yet (L1a)", pytrace=False)
    function = getattr(module, name, None)
    if function is None:
        pytest.fail(f"{CHANGE_DAYS_MODULE}.{name} does not exist yet (L1a)", pytrace=False)
    return function


def _days(count: int, start: date = MONDAY) -> list[date]:
    """``count`` consecutive calendar days from ``start``."""
    return [start + timedelta(days=offset) for offset in range(count)]


def _flat_prices(days: Sequence[date], price: str = "100") -> dict[date, Decimal | None]:
    """The same price on every day, a fresh Decimal each day: equal objects in one representation are no change."""
    return {day: Decimal(price) for day in days}


def _flat_marks(days: Sequence[date], price: str = "100", estimated: bool = False) -> dict[date, tuple[Decimal, bool]]:
    """The same estimated mark on every day, a fresh entry each day."""
    return {day: (Decimal(price), estimated) for day in days}


def _change_days(
    days: Sequence[date],
    *,
    market_prices: Mapping[date, Decimal | None] | None = None,
    estimated_market_prices: Mapping[date, tuple[Decimal, bool]] | None = None,
    at_cost_until: date | None = None,
    event_dates=(),
) -> list[date]:
    """``lot_change_days`` on ``days``: a flat price and a flat mark on every day unless given, no day at cost, no event."""
    lot_change_days = _change_days_function("lot_change_days")
    return lot_change_days(
        days=days,
        market_prices=_flat_prices(days) if market_prices is None else market_prices,
        estimated_market_prices=_flat_marks(days) if estimated_market_prices is None else estimated_market_prices,
        at_cost_until=at_cost_until,
        event_dates=event_dates,
    )


def _at(days: Sequence[date], *indexes: int) -> list[date]:
    """The days at ``indexes``, in the order given."""
    return [days[index] for index in indexes]


# --------------------------------------------------------------------------- #
# lot_change_days
# --------------------------------------------------------------------------- #


def test_lot_change_days_of_no_day_are_no_day():
    """RED until L1a. No day, no change day — whatever the day at cost and the event dates say.

    Today: «change_days does not exist yet».
    """
    assert _change_days([], market_prices={}, estimated_market_prices={}, at_cost_until=MONDAY, event_dates=[MONDAY]) == []


@pytest.mark.parametrize(
    ("count", "expected"),
    [
        pytest.param(1, (0,), id="one-day"),
        pytest.param(2, (0, 1), id="two-days"),
        pytest.param(3, (0, 1, 2), id="three-days"),
        pytest.param(10, (0, 1, 9), id="ten-days"),
    ],
)
def test_lot_change_days_of_a_flat_run_are_its_first_day_the_day_after_it_and_its_last_day(count, expected):
    """RED until L1a. The same price and the same mark every day, no event, no day at cost: the first and the last day
    are always change days, and the first day's next day is one too. Nothing in between.

    Today: «change_days does not exist yet».
    """
    days = _days(count)

    assert _change_days(days) == _at(days, *expected)


def test_lot_change_days_mark_a_price_appearing_and_disappearing():
    """RED until L1a. No price on days 0–2, a price on days 3–5, none again on days 6–9 (estimated entries absent every
    day, so they say nothing): days 3 and 6 change, so do their next days 4 and 7.

    Today: «change_days does not exist yet».
    """
    days = _days(10)
    market_prices = {day: Decimal("100") if 3 <= index < 6 else None for index, day in enumerate(days)}

    assert _change_days(days, market_prices=market_prices, estimated_market_prices={}) == _at(days, 0, 1, 3, 4, 6, 7, 9)


@pytest.mark.parametrize(
    ("before", "after"),
    [
        pytest.param("1.1", "1.10", id="a-trailing-zero-appears"),
        pytest.param("2.50", "2.5", id="a-trailing-zero-goes"),
        # format(…, "f") prints both "100", but 1.5 times each prints "150" and "150.0": only the exact representation
        # keeps the next figure built on it unchanged.
        pytest.param("100", "1E+2", id="an-exponent"),
        pytest.param("0", "-0", id="a-negative-zero"),
    ],
)
def test_lot_change_days_mark_an_equal_price_written_another_way(before, after):
    """RED until L1a. Days 0–4 priced ``before``, days 5–9 ``after``: equal for ``==``, another exact representation —
    which reaches the JSON of every figure built on it. Day 5 changes, so does day 6.

    Today: «change_days does not exist yet».
    """
    days = _days(10)
    market_prices = {day: Decimal(before if index < 5 else after) for index, day in enumerate(days)}
    # Precondition: == cannot tell them apart, so only the representation can.
    assert Decimal(before) == Decimal(after)

    assert _change_days(days, market_prices=market_prices, estimated_market_prices={}) == _at(days, 0, 1, 5, 6, 9)


_ESTIMATED_CHANGES = {
    "the-flag-flips": (("100", True), ("100", False)),
    "the-price-is-written-another-way": (("2.5", False), ("2.50", False)),
    "an-entry-appears": (None, ("100", True)),
    "an-entry-disappears": (("100", True), None),
}


def _marks_switching(days: Sequence[date], before: tuple[str, bool] | None, after: tuple[str, bool] | None, *, at: int) -> dict[date, tuple[Decimal, bool]]:
    """``before`` on the days before index ``at``, ``after`` from it; None is no entry at all."""
    marks: dict[date, tuple[Decimal, bool]] = {}
    for index, day in enumerate(days):
        entry = before if index < at else after
        if entry is not None:
            marks[day] = (Decimal(entry[0]), entry[1])
    return marks


@pytest.mark.parametrize("change", list(_ESTIMATED_CHANGES))
def test_lot_change_days_mark_an_estimated_entry_that_changes_alone(change):
    """RED until L1a. The same price every day; the estimated entry changes on day 5 alone — its flag, the representation
    of its price, or its presence. Day 5 changes, so does day 6.

    Today: «change_days does not exist yet».
    """
    days = _days(10)
    before, after = _ESTIMATED_CHANGES[change]
    marks = _marks_switching(days, before, after, at=5)

    assert _change_days(days, estimated_market_prices=marks) == _at(days, 0, 1, 5, 6, 9)


@pytest.mark.parametrize(
    ("at_cost_offset", "expected"),
    [
        pytest.param(3, (0, 1, 4, 5, 9), id="mid-run-the-day-after-and-its-next-day"),
        pytest.param(0, (0, 1, 2, 9), id="the-first-day-its-next-day-is-a-change-day-so-is-the-one-after"),
        pytest.param(9, (0, 1, 9), id="the-last-day-nothing-after-it"),
        pytest.param(-1, (0, 1, 9), id="the-day-before-the-first-the-first-day"),
        pytest.param(-5, (0, 1, 9), id="days-before-the-first-nothing"),
        pytest.param(None, (0, 1, 9), id="no-day-at-cost"),
    ],
)
def test_lot_change_days_mark_the_day_after_the_last_day_at_cost(at_cost_offset, expected):
    """RED until L1a. ``at_cost_until`` + 1 is a change day when it is one of the days, and its next day too: on day 3
    the days at cost end, so days 4 and 5 are in. On the last day, or before the first, nothing is added.

    Today: «change_days does not exist yet».
    """
    days = _days(10)
    at_cost_until = None if at_cost_offset is None else MONDAY + timedelta(days=at_cost_offset)

    assert _change_days(days, at_cost_until=at_cost_until) == _at(days, *expected)


def test_lot_change_days_keep_the_event_dates_among_the_days_and_ignore_the_others():
    """RED until L1a. Events three days before the first day, on day 4 (twice), two days after the last and on day 7 —
    given once, as an iterator, which an ``Iterable`` allows: days 4 and 7 are in, with their next days 5 and 8; the two
    outside are ignored, the duplicate counts once.

    Today: «change_days does not exist yet».
    """
    days = _days(10)
    events = iter([days[0] - timedelta(days=3), days[4], days[4], days[9] + timedelta(days=2), days[7]])

    assert _change_days(days, event_dates=events) == _at(days, 0, 1, 4, 5, 7, 8, 9)


def test_lot_change_days_never_add_a_day_past_the_last():
    """RED until L1a. On the last day everything changes at once — the price, the mark, an event, the day after the last
    day at cost —: the last day is in, and no day after it.

    Today: «change_days does not exist yet».
    """
    days = _days(10)
    market_prices = _flat_prices(days)
    market_prices[days[9]] = Decimal("101")
    marks = _flat_marks(days)
    marks[days[9]] = (Decimal("101"), True)

    observed = _change_days(days, market_prices=market_prices, estimated_market_prices=marks, at_cost_until=days[8], event_dates=[days[9]])

    assert observed == _at(days, 0, 1, 9)


def test_lot_change_days_put_no_day_inside_a_long_run_of_identical_days():
    """RED until L1a. 46 000 days from 1 Jan 1900 — the span the analysis walks for a lot of 1900 —, each with its own
    Decimal objects: the price and the mark move once, on day 23 000. Five change days: the first, its next day, day
    23 000, its next day and the last — none inside the two long runs, whatever the objects' identity.

    Today: «change_days does not exist yet».
    """
    days = _days(46_000, start=date(1900, 1, 1))
    market_prices = {day: Decimal("100" if index < 23_000 else "101") for index, day in enumerate(days)}
    marks = {day: (Decimal("100" if index < 23_000 else "101"), False) for index, day in enumerate(days)}

    observed = _change_days(days, market_prices=market_prices, estimated_market_prices=marks)

    assert observed == _at(days, 0, 1, 23_000, 23_001, 45_999)


def _exactly(entry: Decimal | tuple[Decimal, bool] | None) -> tuple | None:
    """An entry in its exact representation: sign, digits and exponent — never ``==``."""
    if entry is None:
        return None
    if isinstance(entry, tuple):
        return (entry[0].as_tuple(), entry[1])
    return entry.as_tuple()


def _reference_change_days(
    *,
    days: Sequence[date],
    market_prices: Mapping[date, Decimal | None],
    estimated_market_prices: Mapping[date, tuple[Decimal, bool]],
    at_cost_until: date | None,
    event_dates: Sequence[date],
) -> list[date]:
    """The contract read literally, as the module docstring states it."""
    if not days:
        return []
    among = set(days)
    marked = {days[0], days[-1]}
    for previous, day in zip(days, days[1:], strict=False):
        moved = _exactly(market_prices.get(day)) != _exactly(market_prices.get(previous))
        if moved or _exactly(estimated_market_prices.get(day)) != _exactly(estimated_market_prices.get(previous)):
            marked.add(day)
    if at_cost_until is not None:
        marked.add(at_cost_until + timedelta(days=1))
    marked.update(event_dates)
    marked &= among
    marked |= {day + timedelta(days=1) for day in marked} & among
    return sorted(marked)


_PRICE_PICKS = (None, "1.1", "1.10", "2", "2.0", "0", "-0")
_MARK_PICKS = (None, ("1.1", True), ("1.10", True), ("1.1", False), ("2", False))


def _sticky(rng: random.Random, picks: Sequence, count: int) -> list:
    """``count`` picks from ``picks`` in runs: three times in four a pick repeats the previous one."""
    chosen: list = []
    for _ in range(count):
        chosen.append(chosen[-1] if chosen and rng.random() < 0.75 else rng.choice(picks))
    return chosen


def _random_case(rng: random.Random) -> dict:
    """The arguments of a random ``lot_change_days`` call: up to 40 days, prices and marks in runs (representations
    included), a day at cost and events on, around or outside the days."""
    days = _days(rng.randint(0, 40), date(2024, 1, 1) + timedelta(days=rng.randint(0, 300)))
    prices = {day: None if pick is None else Decimal(pick) for day, pick in zip(days, _sticky(rng, _PRICE_PICKS, len(days)), strict=True)}
    marks = {day: (Decimal(pick[0]), pick[1]) for day, pick in zip(days, _sticky(rng, _MARK_PICKS, len(days)), strict=True) if pick is not None}
    around = [*days, days[0] - timedelta(days=2), days[-1] + timedelta(days=1)] if days else [MONDAY]
    return {
        "days": days,
        "market_prices": prices,
        "estimated_market_prices": marks,
        "at_cost_until": rng.choice([None, *around]),
        "event_dates": rng.sample(around, k=min(len(around), rng.randint(0, 4))),
    }


@pytest.mark.parametrize("seed", range(8))
def test_lot_change_days_are_sorted_unique_among_the_days_and_follow_the_contract_on_random_runs(seed):
    """RED until L1a. 50 random calls per seed (``_random_case``): the answer is sorted, holds each day once, only days
    of ``days``, and is the contract read literally (``_reference_change_days``).

    Today: «change_days does not exist yet».
    """
    rng = random.Random(seed)
    lot_change_days = _change_days_function("lot_change_days")
    for case in range(50):
        arguments = _random_case(rng)
        observed = lot_change_days(**arguments)
        context = f"seed {seed}, case {case}: {len(arguments['days'])} days, at cost until {arguments['at_cost_until']}, events {arguments['event_dates']}"
        assert observed == sorted(set(observed)), f"{context}: not sorted, or a day twice: {observed}"
        assert set(observed) <= set(arguments["days"]), f"{context}: days not among the days: {sorted(set(observed) - set(arguments['days']))}"
        assert observed == _reference_change_days(**arguments), f"{context}: {observed}"


# --------------------------------------------------------------------------- #
# history_steps
# --------------------------------------------------------------------------- #


def _value_row(lot_id: int, day: date, value: str) -> LotValueHistoryPoint:
    """A value point of ONE day (``through`` = ``date``, as a builder gives it) whose figures say which row it is: an
    unknown fee and net P&L (None), an income written ``5.10``."""
    amount = Decimal(value)
    return LotValueHistoryPoint(
        lot_id=lot_id,
        date=day,
        through=day,
        open_value=amount,
        proceeds=Decimal("0"),
        total_value=amount,
        original_cost=Decimal("1000"),
        pnl=amount - Decimal("1000"),
        income=Decimal("5.10"),
        allocated_fees=None,
        allocated_taxes=Decimal("1"),
        net_pnl=None,
    )


def _price_row(day: date, price: str, *, estimated: bool = False) -> MarketPriceHistoryPoint:
    """A market price point of ONE day, the price written as given."""
    return MarketPriceHistoryPoint(date=day, through=day, market_price=Decimal(price), currency="EUR", estimated=estimated)


def _by_lot(row: LotValueHistoryPoint) -> int:
    return row.lot_id


def _one_line(_row: MarketPriceHistoryPoint) -> None:
    return None


def _steps(rows: Sequence, *, change_days: Sequence[date], range_start: date, range_end: date, key: Callable = _by_lot) -> list:
    return history_steps(rows, key=key, change_days=change_days, range_start=range_start, range_end=range_end)


def _view(steps: Sequence[LotValueHistoryPoint]) -> list[tuple[int, date, date, Decimal]]:
    """Each lot step as (lot, first day, last day, total value): the figures a test names, the span in full."""
    return [(step.lot_id, step.date, step.through, step.total_value) for step in steps]


def _dumped(rows: Sequence) -> list[dict]:
    """Each row as JSON, span included: the representation of every figure, and None, exactly."""
    return [row.model_dump(mode="json") for row in rows]


def test_history_steps_carry_the_row_of_a_change_day_to_the_day_before_the_next_one():
    """Change days 0, 3 and 7, one lot valued 1000, 1100 and 1200 on them, the range days 0-9: three steps, 0-2 with day
    0's figures, 3-6 with day 3's, 7-9 with day 7's (the last one runs to the end of the range) — each still a
    ``LotValueHistoryPoint``, with the figures of its row.
    """
    days = _days(10)
    change_days = _at(days, 0, 3, 7)
    rows = [_value_row(1, day, value) for day, value in zip(change_days, ("1000", "1100", "1200"), strict=True)]

    steps = _steps(rows, change_days=change_days, range_start=days[0], range_end=days[9])

    assert _view(steps) == [(1, days[0], days[2], D("1000")), (1, days[3], days[6], D("1100")), (1, days[7], days[9], D("1200"))]
    assert {type(step) for step in steps} == {LotValueHistoryPoint}
    assert [step.model_dump(mode="json", exclude={"date", "through"}) for step in steps] == [row.model_dump(mode="json", exclude={"date", "through"}) for row in rows]


def test_history_steps_leave_a_key_without_a_row_a_gap_until_a_later_change_day_has_one():
    """Change days 0, 3 and 7. Lot 1 has a row on each; lot 2 none on day 3 (a day it could not be valued), so a gap on
    days 3-6 and a step again from day 7; lot 3 opens on day 3, so nothing on days 0-2.
    """
    days = _days(10)
    change_days = _at(days, 0, 3, 7)
    lot_1 = [_value_row(1, day, value) for day, value in zip(change_days, ("1000", "1100", "1200"), strict=True)]
    lot_2 = [_value_row(2, days[0], "500"), _value_row(2, days[7], "520")]
    lot_3 = [_value_row(3, days[3], "300"), _value_row(3, days[7], "310")]

    steps = _steps([*lot_1, *lot_2, *lot_3], change_days=change_days, range_start=days[0], range_end=days[9])

    assert _view(steps) == [
        (1, days[0], days[2], D("1000")),
        (1, days[3], days[6], D("1100")),
        (1, days[7], days[9], D("1200")),
        (2, days[0], days[2], D("500")),
        (2, days[7], days[9], D("520")),
        (3, days[3], days[6], D("300")),
        (3, days[7], days[9], D("310")),
    ]


def test_history_steps_leave_a_gap_after_the_last_step_of_a_key_that_stops_having_rows():
    """Change days 0, 3, 7 and 9. Lot 1 (a lot closed and no longer valued) has rows on days 0 and 3 only: its second
    step ends the day before day 7, the next change day, and nothing follows — it does not run to the end of the range.
    Lot 2 has a row on every change day, so its last step does run to the end.
    """
    days = _days(12)
    change_days = _at(days, 0, 3, 7, 9)
    lot_1 = [_value_row(1, days[0], "1000"), _value_row(1, days[3], "1100")]
    lot_2 = [_value_row(2, day, value) for day, value in zip(change_days, ("500", "510", "520", "530"), strict=True)]

    steps = _steps([*lot_1, *lot_2], change_days=change_days, range_start=days[0], range_end=days[11])

    assert _view(steps) == [
        (1, days[0], days[2], D("1000")),
        (1, days[3], days[6], D("1100")),
        (2, days[0], days[2], D("500")),
        (2, days[3], days[6], D("510")),
        (2, days[7], days[8], D("520")),
        (2, days[9], days[11], D("530")),
    ]


def test_history_steps_keep_the_keys_in_their_order_of_first_appearance_and_the_days_ascending():
    """Lot 9's rows come before lot 2's: every step of lot 9, ascending, then every step of lot 2 — never sorted by key."""
    days = _days(4)
    change_days = _at(days, 0, 2)
    rows = [_value_row(9, days[0], "900"), _value_row(9, days[2], "910"), _value_row(2, days[0], "200"), _value_row(2, days[2], "210")]

    steps = _steps(rows, change_days=change_days, range_start=days[0], range_end=days[3])

    assert [(step.lot_id, step.date, step.through) for step in steps] == [(9, days[0], days[1]), (9, days[2], days[3]), (2, days[0], days[1]), (2, days[2], days[3])]


def test_history_steps_give_nothing_before_the_first_change_day():
    """Change days 5 and 8, the range days 0-9: no step starts before day 5 (there is no value to hold), then 5-7 with day
    5's figures and 8-9 with day 8's."""
    days = _days(10)
    rows = [_value_row(1, days[5], "1000"), _value_row(1, days[8], "1010")]

    steps = _steps(rows, change_days=_at(days, 5, 8), range_start=days[0], range_end=days[9])

    assert _view(steps) == [(1, days[5], days[7], D("1000")), (1, days[8], days[9], D("1010"))]


def test_history_steps_clip_the_step_of_a_change_day_before_the_range_to_its_start():
    """Change days 0 and 8, the range days 3-9: the first step is day 0's figures from day 3 (the range start), through
    day 7; the second is day 8's through day 9. Nothing before day 3."""
    days = _days(10)
    rows = [_value_row(1, days[0], "1000"), _value_row(1, days[8], "1010")]

    steps = _steps(rows, change_days=_at(days, 0, 8), range_start=days[3], range_end=days[9])

    assert _view(steps) == [(1, days[3], days[7], D("1000")), (1, days[8], days[9], D("1010"))]


def test_history_steps_end_the_last_step_on_the_range_end_even_when_it_is_before_the_last_change_day():
    """Change days 0, 4 and 8, the range days 0-5: the step of day 4 ends on day 5 (the range end); the row of day 8 is
    outside the range, so it brings no step."""
    days = _days(10)
    rows = [_value_row(1, days[0], "1000"), _value_row(1, days[4], "1100"), _value_row(1, days[8], "1200")]

    steps = _steps(rows, change_days=_at(days, 0, 4, 8), range_start=days[0], range_end=days[5])

    assert _view(steps) == [(1, days[0], days[3], D("1000")), (1, days[4], days[5], D("1100"))]


def test_history_steps_merge_consecutive_identical_rows_of_a_key_into_the_first_one_widened():
    """The change days of a lot's price are more than the days its value changes on: rows on days 0, 3 and 5 with the
    same figures are ONE step 0-6 (the first row's, widened) and the row of day 7 another. Two lots with the same figures
    are not merged with each other, and identical rows with a gap between them stay two steps."""
    days = _days(10)
    change_days = _at(days, 0, 3, 5, 7)
    lot_1 = [_value_row(1, days[0], "1000"), _value_row(1, days[3], "1000"), _value_row(1, days[5], "1000"), _value_row(1, days[7], "1100")]
    lot_2 = [_value_row(2, day, "1000") for day in _at(days, 0, 3, 5, 7)]
    lot_3 = [_value_row(3, days[0], "700"), _value_row(3, days[7], "700")]  # no row on days 3 and 5: a gap, then the same figures again

    steps = _steps([*lot_1, *lot_2, *lot_3], change_days=change_days, range_start=days[0], range_end=days[9])

    assert _view(steps) == [
        (1, days[0], days[6], D("1000")),
        (1, days[7], days[9], D("1100")),
        (2, days[0], days[9], D("1000")),
        (3, days[0], days[2], D("700")),
        (3, days[7], days[9], D("700")),
    ]


def test_history_steps_do_not_merge_rows_that_differ_by_the_exponent_of_a_decimal():
    """``Decimal('1.10') == Decimal('1.1')`` and the JSON of the two differs (``"1.10"`` against ``"1.1"``): the rows are
    TWO steps, because the JSON of a figure built on either one differs too. A price written the same twice is one step,
    which keeps the first row's own representation."""
    days = _days(9)
    change_days = _at(days, 0, 2, 4, 6, 8)
    prices = ("1.10", "1.10", "1.1", "1.1", "1.10")
    assert Decimal("1.10") == Decimal("1.1")  # precondition: == cannot tell them apart
    rows = [_price_row(day, price) for day, price in zip(change_days, prices, strict=True)]

    steps = _steps(rows, key=_one_line, change_days=change_days, range_start=days[0], range_end=days[8])

    assert [(step.date, step.through, str(step.market_price)) for step in steps] == [(days[0], days[3], "1.10"), (days[4], days[7], "1.1"), (days[8], days[8], "1.10")]


@pytest.mark.parametrize(
    ("first", "second"),
    [
        pytest.param(_price_row(MONDAY, "1.5", estimated=True), _price_row(MONDAY, "1.5", estimated=False), id="a-flag-flips"),
        pytest.param(_price_row(MONDAY, "100"), _price_row(MONDAY, "1E+2"), id="an-exponent"),
        pytest.param(_price_row(MONDAY, "0"), _price_row(MONDAY, "-0"), id="a-negative-zero"),
    ],
)
def test_history_steps_split_a_run_where_any_figure_of_the_row_differs_in_any_way(first, second):
    """Two consecutive rows differ in a flag, in the exponent of the price or in the sign of a zero: two steps."""
    days = _days(4)

    steps = _steps([first.model_copy(update={"date": days[0], "through": days[0]}), second.model_copy(update={"date": days[2], "through": days[2]})], key=_one_line, change_days=_at(days, 0, 2), range_start=days[0], range_end=days[3])

    assert [(step.date, step.through) for step in steps] == [(days[0], days[1]), (days[2], days[3])]


def test_history_steps_change_nothing_but_the_days_and_leave_the_builders_rows_as_they_were():
    """Rows whose figures are written ``1000.10`` and ``999.900``, with None fields: every step dumps, days aside, exactly
    as its source row — same representation, same None —, and the source rows keep their own days: widening a step never
    happens in place."""
    days = _days(6)
    rows = [_value_row(1, days[0], "1000.10"), _value_row(1, days[4], "999.900")]
    sources_before = _dumped(rows)

    steps = _steps(rows, change_days=_at(days, 0, 4), range_start=days[0], range_end=days[5])

    assert [(step.date, step.through) for step in steps] == [(days[0], days[3]), (days[4], days[5])]
    assert [step.model_dump(mode="json", exclude={"date", "through"}) for step in steps] == [row.model_dump(mode="json", exclude={"date", "through"}) for row in rows]
    assert _dumped(rows) == sources_before


def test_history_steps_on_the_market_price_line_one_key_for_every_point():
    """The market price line, one key for every point (``MarketPriceHistoryPoint``). Change days 0, 2 and 5, a point on
    days 0 and 2 only — day 5 has no mark (a price without a rate) —, the range days 1-6: a step 1-1 with day 0's point
    clipped to the range start, a step 2-4 with day 2's, and a gap on days 5-6."""
    days = _days(7)
    rows = [_price_row(days[0], "100", estimated=True), _price_row(days[2], "101.50")]

    steps = _steps(rows, key=_one_line, change_days=_at(days, 0, 2, 5), range_start=days[1], range_end=days[6])

    assert [(step.date, step.through, step.market_price, step.estimated) for step in steps] == [(days[1], days[1], D("100"), True), (days[2], days[4], D("101.50"), False)]
    assert {type(step) for step in steps} == {MarketPriceHistoryPoint}


@pytest.mark.parametrize(
    ("row_count", "range_"),
    [
        pytest.param(1, (3, 2), id="a-range-that-ends-before-it-starts"),
        pytest.param(0, (0, 4), id="no-row"),
        pytest.param(1, (-5, -2), id="a-range-before-the-first-change-day"),
    ],
)
def test_history_steps_of_nothing_are_nothing(row_count, range_):
    """A range that ends before it starts — the analysis read from a day after its ``date_to`` —, no row at all, or a
    range that lies before the only change day: no step."""
    days = _days(10)
    rows = [_value_row(1, days[0], "1000")][:row_count]
    start, end = range_

    assert _steps(rows, change_days=_at(days, 0), range_start=MONDAY + timedelta(days=start), range_end=MONDAY + timedelta(days=end)) == []


def test_history_steps_hold_the_last_change_day_to_a_range_that_comes_after_it():
    """The only change day is day 0 and the range is days 6-8: day 0's figures hold, from the start of the range to its
    end (the contract carries the last change day's row to every day after it)."""
    days = _days(10)

    steps = _steps([_value_row(1, days[0], "1000")], change_days=_at(days, 0), range_start=days[6], range_end=days[8])

    assert _view(steps) == [(1, days[6], days[8], D("1000"))]


# --------------------------------------------------------------------------- #
# history_steps on every day: the trim it replaced
# --------------------------------------------------------------------------- #

_IDENTITY_LOT_IDS = (2, 5, 9, 11, 14, 23)
_IDENTITY_CASES = 48


def _ordered(first: int, second: int) -> tuple[int, int]:
    return min(first, second), max(first, second)


def _twice(offset: int) -> tuple[int, int]:
    return offset, offset


def _ending_before_it_starts(window_to: int, gap: int) -> tuple[int, int]:
    return window_to + gap, window_to


# The windows of the identity, as (range_start, range_end) offsets from the first day of a span of ``length`` days. Each
# ends on or before the span's last day, or ends before it starts: past the last day the contract carries the last
# change day's rows (test_history_steps_carry_the_row_of_a_change_day_to_the_day_before_the_next_one), which no trim did,
# and the service never asks for such a window — its range ends on ``actual_to``, the last day of the days it reads.
_IDENTITY_WINDOWS: dict[str, Callable[[random.Random, int], tuple[int, int]]] = {
    "inside": lambda rng, length: _ordered(rng.randrange(length), rng.randrange(length)),
    "a-single-day-inside": lambda rng, length: _twice(rng.randrange(length)),
    "before-the-span": lambda rng, _length: _ordered(-rng.randint(1, 10), -rng.randint(1, 10)),
    "a-single-day-before-the-span": lambda rng, _length: _twice(-rng.randint(1, 10)),
    "straddling-the-first-day": lambda rng, length: (-rng.randint(1, 10), rng.randrange(length)),
    # The service's own range, [range_start, actual_to]: from before the span, its first day or inside it.
    "ending-on-the-last-day": lambda rng, length: (rng.choice((-rng.randint(1, 10), 0, rng.randrange(length))), length - 1),
    # The service's range read from a date_from after its date_to.
    "starting-after-the-span": lambda rng, length: (length - 1 + rng.randint(1, 10), length - 1),
    "ending-before-it-starts": lambda rng, length: _ending_before_it_starts(rng.randint(-5, length - 1), rng.randint(1, 10)),
}


def _identity_lot_rows(rng: random.Random, span: Sequence[date]) -> list[LotValueHistoryPoint]:
    """A value history as ``build_value_history`` gives it on every day of ``span``: lot by lot — two to four lots, never
    in the order of their ids —, each lot's days ascending from its opening, which always has its row, to its last day.
    The first lot opens on the span's first day and, whenever the span has three days, misses one inside its run (a day
    it was not valued); the second opens later; the third and fourth may stop before the span's last day; any other day
    misses its row one time in five. A figure is drawn from a short list, so that consecutive days repeat it, some of
    them written with another number of decimals (``1000.5`` and ``1000.50``)."""
    length = len(span)
    lot_ids = rng.sample(_IDENTITY_LOT_IDS, rng.randint(2, 4))
    if lot_ids == sorted(lot_ids):
        lot_ids.reverse()
    rows: list[LotValueHistoryPoint] = []
    for index, lot_id in enumerate(lot_ids):
        opening = 0 if index == 0 else rng.randrange(1 if index == 1 and length > 1 else 0, length)
        last = length - 1 if index < 2 else rng.randrange(opening, length)
        hole = rng.randrange(opening + 1, last) if index == 0 and last - opening >= 2 else None
        figure = f"{rng.randint(800, 1300)}.{rng.choice(('0', '5', '50', '125'))}"
        for offset in range(opening, last + 1):
            if offset == hole or (offset > opening and rng.random() < 0.2):
                continue
            if rng.random() < 0.5:
                figure = f"{rng.randint(800, 804)}.{rng.choice(('0', '5', '50'))}"
            rows.append(_value_row(lot_id, span[offset], figure))
    return rows


def _identity_line_rows(rng: random.Random, span: Sequence[date]) -> list[MarketPriceHistoryPoint]:
    """The market price line as ``build_market_price_history`` gives it on every day of ``span``: one point a day from the
    first mark — the span's first day or later —, which always has its point, to the span's last day; one day without a
    point inside the run whenever it is three days long (a mark without a rate), any other one time in five. A price is
    drawn from a short list, so that consecutive days repeat it, some of them written with another number of decimals."""
    length = len(span)
    first = rng.randrange(length)
    hole = rng.randrange(first + 1, length - 1) if length - first >= 3 else None
    rows: list[MarketPriceHistoryPoint] = []
    price = "100.0"
    for offset in range(first, length):
        if offset == hole or (offset > first and rng.random() < 0.2):
            continue
        if rng.random() < 0.5:
            price = f"{rng.randint(90, 93)}.{rng.choice(('0', '5', '50'))}"
        rows.append(_price_row(span[offset], price, estimated=rng.random() < 0.3))
    return rows


# Each shape: its rows, its key and the field of it, and what its cases must exercise between them (``_trim_shapes``).
_IDENTITY_SHAPES: dict[str, tuple[Callable[[random.Random, Sequence[date]], list], Callable, str | None, frozenset[str]]] = {
    "lot-value-history": (_identity_lot_rows, _by_lot, "lot_id", frozenset({"a key with a gap", "a key starting late", "keys out of their sorted order", "a window with rows", "a window without a row"})),
    "market-price-line": (_identity_line_rows, _one_line, None, frozenset({"a key with a gap", "a key starting late", "a window with rows", "a window without a row"})),
}


@dataclass(frozen=True)
class _TrimCase:
    """A dense span of change days, the builder-shaped rows on it, and a window of ``kind``."""

    kind: str
    span: list[date]
    rows: list
    window_from: date
    window_to: date

    @property
    def trimmed(self) -> list:
        """What ``trim_dates(rows, window_from, window_to)`` answered: the rows of the window, in their order."""
        return [row for row in self.rows if self.window_from <= row.date <= self.window_to]


def _trim_cases(rng: random.Random, build_rows: Callable[[random.Random, Sequence[date]], list]) -> list[_TrimCase]:
    """``_IDENTITY_CASES`` cases: a span of 1 to 40 days somewhere in 2024, its rows, and a window of each kind of
    ``_IDENTITY_WINDOWS`` in turn."""
    kinds = list(_IDENTITY_WINDOWS)
    cases: list[_TrimCase] = []
    for number in range(_IDENTITY_CASES):
        kind = kinds[number % len(kinds)]
        span = _days(rng.randint(1, 40), date(2024, 1, 1) + timedelta(days=rng.randint(0, 300)))
        rows = build_rows(rng, span)
        from_offset, to_offset = _IDENTITY_WINDOWS[kind](rng, len(span))
        cases.append(_TrimCase(kind=kind, span=span, rows=rows, window_from=span[0] + timedelta(days=from_offset), window_to=span[0] + timedelta(days=to_offset)))
    return cases


def _trim_shapes(case: _TrimCase, key: Callable) -> set[str]:
    """What a case exercises: a key missing a day inside its run, a key starting after the span's first day, keys out of
    their sorted order (a key per lot only), and whether its window holds rows."""
    days_by_key: dict[Hashable, list[date]] = {}
    for row in case.rows:
        days_by_key.setdefault(key(row), []).append(row.date)
    runs = list(days_by_key.values())
    shapes = {"a window with rows" if case.trimmed else "a window without a row"}
    if any(len(days) < (days[-1] - days[0]).days + 1 for days in runs):
        shapes.add("a key with a gap")
    if any(days[0] > case.span[0] for days in runs):
        shapes.add("a key starting late")
    keys = list(days_by_key)
    if None not in keys and keys != sorted(keys):
        shapes.add("keys out of their sorted order")
    return shapes


@pytest.mark.parametrize("seed", range(5))
@pytest.mark.parametrize("shape", list(_IDENTITY_SHAPES))
def test_history_steps_on_every_day_expand_to_the_trim_they_replaced_and_are_maximal(shape, seed):
    """With every day of a dense span a change day, the steps repeated over their days are the one-row-per-day answer the
    trim gave, ``[row for row in rows if window_from <= row.date <= window_to]``: the same rows, in the same order — and
    the steps are the MAXIMAL ones: ``compress_days`` (the oracle of the shared step helpers, written on JSON text) over
    the trimmed rows gives them back, so no two consecutive steps of a key hold the same figures.

    Why: the parity battery (``test_financial/test_lots_change_days_parity.py``) compares A, the analysis on its change
    days, with B, the analysis with every day a change day, and calls B today's computation. B goes through
    ``history_steps`` too, so a defect that strikes A and B alike — the keys reordered, a row dropped, duplicated or
    carried where the trim had none — passes the battery: a reordering of the keys did, caught only by the key-order test
    above. This identity is the step B rests on.

    The rows are a builder's (``_identity_lot_rows``, ``_identity_line_rows``): grouped by key in first-appearance order,
    days ascending within a key, lot ids out of their sorted order, a lot opening after the span's first day, a day
    without a row inside a run (a lot not valued, a mark without a rate), lots stopping before the span's last day, the
    same figure on consecutive days (some written with another exponent) — the value history keyed by ``lot_id``
    (``LotValueHistoryPoint``), the market price line by one key for every point (``MarketPriceHistoryPoint``). 48 cases a
    seed, with the windows of ``_IDENTITY_WINDOWS`` in turn: inside the span, a single day inside it, before it, a single
    day before it, straddling its first day, ending on its last day (the service's own range, ``[range_start,
    actual_to]``), starting after it (``date_from`` after ``date_to``), ending before it starts. Precondition: the cases
    do exercise those shapes, and windows with rows and without.

    No window reaches past the span's last day: there the contract carries the last change day's rows, which no trim did
    — and the service never asks for one, its range ending on ``actual_to``, the last day of the days it reads.
    """
    build_rows, key, key_name, to_cover = _IDENTITY_SHAPES[shape]
    cases = _trim_cases(random.Random(seed), build_rows)
    covered = set().union(*(_trim_shapes(case, key) for case in cases))
    assert to_cover <= covered, f"precondition: {shape}, seed {seed} never generates {sorted(to_cover - covered)}"

    for number, case in enumerate(cases):
        steps = history_steps(case.rows, key=key, change_days=case.span, range_start=case.window_from, range_end=case.window_to)

        context = f"{shape}, seed {seed}, case {number}: window {case.kind} [{case.window_from}, {case.window_to}] over the {len(case.span)} days {case.span[0]}–{case.span[-1]}, {len(case.rows)} rows"
        assert [row.model_dump(mode="json", exclude={"through"}) for row in daily_points(steps)] == [row.model_dump(mode="json", exclude={"through"}) for row in case.trimmed], context
        maximal = compress_days(_dumped(case.trimmed), key_name)
        assert order_by_key(_dumped(steps), key_name) == maximal, f"{context}: {len(steps)} steps, {len(maximal)} maximal ones"
        assert len(steps) <= len(case.trimmed), context


# --------------------------------------------------------------------------- #
# DayRange
# --------------------------------------------------------------------------- #


def test_day_range_is_the_calendar_days_first_to_last_both_included():
    """``len``, indexing from the front and from the back, and iteration agree with the calendar."""
    first, last = date(2024, 2, 27), date(2024, 3, 2)  # across a leap day
    expected = [first + timedelta(days=offset) for offset in range(5)]
    days = DayRange(first, last)

    assert len(days) == 5
    assert list(days) == expected
    assert [days[index] for index in range(5)] == expected
    assert [days[-index] for index in range(1, 6)] == expected[::-1]
    assert (days[0], days[-1]) == (first, last)
    assert list(reversed(days)) == expected[::-1]
    assert list(days) == list(days), "a range can be walked twice"


@pytest.mark.parametrize(
    ("first", "last", "length"),
    [
        pytest.param(MONDAY, MONDAY, 1, id="one-day"),
        pytest.param(MONDAY, MONDAY - timedelta(days=1), 0, id="last-the-day-before-first"),
        pytest.param(MONDAY, MONDAY - timedelta(days=400), 0, id="last-long-before-first"),
    ],
)
def test_day_range_of_one_day_or_none(first, last, length):
    """One day when first = last; empty — whatever its length would be — when last is before first."""
    days = DayRange(first, last)

    assert len(days) == length
    assert list(days) == ([first] if length else [])
    assert bool(days) is bool(length)
    if not length:
        with pytest.raises(IndexError):
            _ = days[0]
        with pytest.raises(IndexError):
            _ = days[-1]


@pytest.mark.parametrize("index", [5, 6, 100, -6, -7, -100])
def test_day_range_refuses_a_position_outside_it(index):
    """Five days: positions -5..4 are days, any other is an ``IndexError`` (as a list's)."""
    days = DayRange(MONDAY, MONDAY + timedelta(days=4))

    with pytest.raises(IndexError):
        _ = days[index]


@pytest.mark.parametrize("bounds", [slice(0, 2), slice(None), slice(None, None, -1), slice(1, None)])
def test_day_range_refuses_a_slice(bounds):
    """A slice would have to build the days it covers: it is a ``TypeError`` that says to build a ``DayRange`` instead."""
    days = DayRange(MONDAY, MONDAY + timedelta(days=4))

    with pytest.raises(TypeError):
        _ = days[bounds]


def test_day_range_contains_its_days_only():
    """``in`` is arithmetic: both ends, a day inside, the day before the first and after the last, and things that are not
    a date (a string, None, an int) are all answered without an error."""
    first, last = MONDAY, MONDAY + timedelta(days=4)
    days = DayRange(first, last)

    assert [first in days, last in days, MONDAY + timedelta(days=2) in days] == [True, True, True]
    assert [first - timedelta(days=1) in days, last + timedelta(days=1) in days] == [False, False]
    assert [first.isoformat() in days, None in days, 5 in days] == [False, False, False]
    assert first not in DayRange(last, first)


def test_day_range_of_seven_hundred_thousand_days_holds_none_of_them():
    """From the year 1 to 2026 the length, the ends, the middle and a bisection are arithmetic: ``bisect`` over it finds
    the position of a day in about twenty reads of ``DayRange.__getitem__``, which the test counts on a subclass."""
    first, last = date(1, 1, 1), date(2026, 10, 25)
    reads: list[int] = []

    class Counting(DayRange):
        def __getitem__(self, index):
            reads.append(index)
            return super().__getitem__(index)

    days = Counting(first, last)
    target = date(1900, 1, 2)

    assert len(days) == (last - first).days + 1 > 739_000
    assert (days[0], days[-1]) == (first, last)
    assert bisect.bisect_left(days, target) == (target - first).days
    assert len(reads) <= 2 + math.ceil(math.log2(len(days))) + 2


# --------------------------------------------------------------------------- #
# price_candidate_days
# --------------------------------------------------------------------------- #


def _candidates(first: date, last: date, *, observations=(), rates=(), events=(), at_cost_until: date | None = None) -> list[date]:
    return price_candidate_days(first=first, last=last, observation_dates=observations, rate_days=rates, event_dates=events, at_cost_until=at_cost_until)


def test_price_candidate_days_are_the_ends_and_each_day_the_price_can_move_on_with_the_day_after_it():
    """A window of 20 days with one observation (day 5), one rate step (day 9), one event (day 13) and the end of the days
    at cost (day 16, so day 17 is the first valued): the first day and the day after it, the last day, then each of the
    others and the day after it — nothing in the long runs between them."""
    days = _days(20)

    observed = _candidates(days[0], days[19], observations=[days[5]], rates=[days[9]], events=[days[13]], at_cost_until=days[16])

    assert observed == _at(days, 0, 1, 5, 6, 9, 10, 13, 14, 17, 18, 19)


def test_price_candidate_days_of_a_window_of_one_day_are_that_day():
    """The first day is the last: one candidate, whatever else is given for it."""
    day = MONDAY

    assert _candidates(day, day) == [day]
    assert _candidates(day, day, observations=[day], rates=[day], events=[day], at_cost_until=day - timedelta(days=1)) == [day]


@pytest.mark.parametrize(
    ("first_offset", "last_offset"),
    [pytest.param(1, 0, id="last-the-day-before-first"), pytest.param(10, 2, id="last-long-before-first")],
)
def test_price_candidate_days_of_an_empty_or_inverted_window_are_none(first_offset, last_offset):
    """No day, whatever the other arguments say."""
    first, last = MONDAY + timedelta(days=first_offset), MONDAY + timedelta(days=last_offset)

    assert _candidates(first, last, observations=[first, last], rates=[first], events=[last], at_cost_until=last) == []


def test_price_candidate_days_clip_to_the_window_and_keep_the_day_after_only_inside_it():
    """Observations, rates and events outside the window are not candidates (the first day already speaks for what came
    before it), and the day after the last day is not one either. The window's own candidates are its first day, the
    next one and its last day: an observation on the last day, or on the day before the first, adds nothing to them; one
    on the day before the last adds that day."""
    days = _days(10)
    before, after = days[0] - timedelta(days=2), days[9] + timedelta(days=1)

    assert _candidates(days[0], days[9], observations=[before, before - timedelta(days=30)], rates=[after], events=[after + timedelta(days=5)]) == _at(days, 0, 1, 9)
    assert _candidates(days[0], days[9], observations=[days[9]]) == _at(days, 0, 1, 9)
    assert _candidates(days[0], days[9], observations=[days[0] - timedelta(days=1)]) == _at(days, 0, 1, 9)
    assert _candidates(days[0], days[9], observations=[days[8]]) == _at(days, 0, 1, 8, 9)


@pytest.mark.parametrize(
    ("at_cost_offset", "expected"),
    [
        pytest.param(3, (0, 1, 4, 5, 9), id="mid-window-the-day-after-and-its-next-day"),
        pytest.param(0, (0, 1, 2, 9), id="the-first-day-the-day-after-is-the-second-and-its-next-the-third"),
        pytest.param(-1, (0, 1, 9), id="the-day-before-the-first-the-first-day-and-its-next"),
        pytest.param(8, (0, 1, 9), id="the-day-before-the-last-the-last-day"),
        pytest.param(9, (0, 1, 9), id="the-last-day-the-day-after-it-is-outside-and-dropped"),
        pytest.param(-5, (0, 1, 9), id="long-before-the-first-nothing"),
        pytest.param(None, (0, 1, 9), id="no-day-at-cost"),
    ],
)
def test_price_candidate_days_put_the_day_after_the_last_day_at_cost_in_the_window_only(at_cost_offset, expected):
    """``at_cost_until`` + 1 is the day the open lots start being valued at the market: a candidate (with its next day)
    when it is inside the window, nothing more when it falls past the last day or comes before the first."""
    days = _days(10)
    at_cost_until = None if at_cost_offset is None else MONDAY + timedelta(days=at_cost_offset)

    assert _candidates(days[0], days[9], at_cost_until=at_cost_until) == _at(days, *expected)


def test_price_candidate_days_are_sorted_unique_and_accept_iterators_read_once():
    """The same day given by an observation, a rate and an event is one candidate; the arguments may be generators."""
    days = _days(10)

    observed = price_candidate_days(
        first=days[0],
        last=days[9],
        observation_dates=(day for day in [days[6], days[3], days[3]]),
        rate_days=iter([days[3], days[6], days[3]]),
        event_dates=iter([days[3]]),
        at_cost_until=None,
    )

    assert observed == _at(days, 0, 1, 3, 4, 6, 7, 9)


def test_price_candidate_days_cost_what_the_changes_cost_in_a_window_of_seven_hundred_thousand_days():
    """From the year 1 to 2026, three observations, two rate steps, one event and the end of the days at cost: a few
    candidates — each date and the day after it, the ends —, not a day per day."""
    first, last = date(1, 1, 1), date(2026, 10, 25)
    observations = [date(1900, 1, 2), date(1900, 1, 9), date(2020, 6, 1)]

    observed = _candidates(first, last, observations=observations, rates=[date(1950, 3, 3), date(2000, 1, 1)], events=[date(1900, 1, 2)], at_cost_until=date(1900, 1, 1))

    assert observed == [
        first,
        date(1, 1, 2),
        date(1900, 1, 2),
        date(1900, 1, 3),
        date(1900, 1, 9),
        date(1900, 1, 10),
        date(1950, 3, 3),
        date(1950, 3, 4),
        date(2000, 1, 1),
        date(2000, 1, 2),
        date(2020, 6, 1),
        date(2020, 6, 2),
        last,
    ]


# What the converted market price of a day is, read the way the service reads it — the last observation's price at the rate
# in force that day — on a window of at most 40 days; the observations and the rates may come before the window.
_OBSERVATION_PRICES = ("1.1", "1.10", "2", "2.0", "0.5")
_RATES = ("1", "1.0", "0.5", "2")


def _random_marks(rng: random.Random) -> dict:
    """The arguments of a random ``price_candidate_days`` call, and the market price and estimated mark each calendar day
    of its window has: ``market_prices[day]`` is None before the first observation or the first rate; else the price of
    the last observation on or before the day times the rate of the last rate day on or before it (the exponent of each
    factor shows in the product); ``estimated_market_prices[day]`` is that price with the flag of the observation."""
    first = date(2024, 1, 1) + timedelta(days=rng.randint(0, 300))
    days = _days(rng.randint(1, 40), first)
    around = [first + timedelta(days=offset) for offset in range(-12, len(days) + 4)]
    observations = {day: (rng.choice(_OBSERVATION_PRICES), rng.random() < 0.3) for day in rng.sample(around, k=rng.randint(0, 8))}
    rates = {day: rng.choice(_RATES) for day in rng.sample(around, k=rng.randint(0, 6))}
    market_prices: dict[date, Decimal | None] = {}
    estimated: dict[date, tuple[Decimal, bool]] = {}
    for day in days:
        seen_observations = [seen for seen in observations if seen <= day]
        seen_rates = [seen for seen in rates if seen <= day]
        if not seen_observations or not seen_rates:
            market_prices[day] = None
            continue
        price_text, flag = observations[max(seen_observations)]
        converted = Decimal(price_text) * Decimal(rates[max(seen_rates)])
        market_prices[day] = converted
        estimated[day] = (converted, flag)
    return {
        "days": days,
        "market_prices": market_prices,
        "estimated_market_prices": estimated,
        "observation_dates": sorted(observations),
        "rate_days": sorted(rates),
        "event_dates": rng.sample(around, k=rng.randint(0, 5)),
        "at_cost_until": rng.choice([None, *around]),
    }


@pytest.mark.parametrize("seed", range(8))
def test_the_days_lot_change_days_keeps_on_every_calendar_day_are_candidates_and_the_same_when_given_only_candidates(seed):
    """THE GUARANTEE of ``price_candidate_days``. 50 random runs per seed (``_random_marks``): a window of 1 to 40 days,
    observations and rate steps in it and before and after it (prices and rates written with different exponents, a flag
    that flips only on an observation), events, a day at cost ending anywhere.

    ``lot_change_days`` given EVERY calendar day of the window (the reference: nothing is skipped) keeps some days. Those
    days are all among the candidates, and ``lot_change_days`` given only the candidates — the prices read on the
    candidates alone, as the service reads them — keeps exactly the same days. So reading the price on the candidates
    loses no change of the day-by-day answer; the day after each (the next day of the contract) is why the candidates
    must hold the day after each seed.
    """
    rng = random.Random(seed)
    lot_change_days = _change_days_function("lot_change_days")
    for case in range(50):
        arguments = _random_marks(rng)
        days = arguments["days"]
        context = f"seed {seed}, case {case}: {len(days)} days from {days[0]}, observations {arguments['observation_dates']}, rates {arguments['rate_days']}, events {arguments['event_dates']}, at cost until {arguments['at_cost_until']}"
        candidates = price_candidate_days(first=days[0], last=days[-1], observation_dates=arguments["observation_dates"], rate_days=arguments["rate_days"], event_dates=arguments["event_dates"], at_cost_until=arguments["at_cost_until"])
        assert candidates == sorted(set(candidates)), f"{context}: not sorted, or a day twice"
        assert set(candidates) <= set(days), f"{context}: days outside the window: {sorted(set(candidates) - set(days))}"
        assert candidates[0] == days[0] and candidates[-1] == days[-1], f"{context}: the ends are not both candidates"

        every_day = lot_change_days(days=days, market_prices=arguments["market_prices"], estimated_market_prices=arguments["estimated_market_prices"], at_cost_until=arguments["at_cost_until"], event_dates=arguments["event_dates"])
        on_candidates = lot_change_days(
            days=candidates,
            market_prices={day: arguments["market_prices"][day] for day in candidates},
            estimated_market_prices={day: arguments["estimated_market_prices"][day] for day in candidates if day in arguments["estimated_market_prices"]},
            at_cost_until=arguments["at_cost_until"],
            event_dates=arguments["event_dates"],
        )

        assert set(every_day) <= set(candidates), f"{context}: change days that are not candidates: {sorted(set(every_day) - set(candidates))}"
        assert on_candidates == every_day, f"{context}: on the candidates {on_candidates}, on every day {every_day}"


# --------------------------------------------------------------------------- #
# last_day_without_observation
# --------------------------------------------------------------------------- #


def _trade(tx_id: int, day: date, tx_type: TransactionType, quantity: str, amount: str, **columns) -> Transaction:
    """An in-memory Transaction row of asset 7 at broker 1, in EUR. Never added to a session."""
    return Transaction(id=tx_id, broker_id=1, asset_id=7, type=tx_type, date=day, quantity=Decimal(quantity), amount=Decimal(amount), currency="EUR", **columns)


_ITEM_KINDS = ("close", "close-without-a-value", "buy", "sell", "buy-of-amount-0", "adjustment-at-a-cost", "split-linked-buy")
# What the series observes (build_asset_price_series): a close with a value, a BUY or SELL with a quantity and an amount
# that no split links. A close without a value, a trade of amount 0, an ADJUSTMENT and a split-linked row are none.
_OBSERVING_KINDS = {"close", "buy", "sell"}


def _item(kind: str, tx_id: int, day: date) -> tuple[tuple | None, Transaction | None]:
    """(price row, transaction) of one item of ``kind`` on ``day``."""
    if kind == "close":
        return (day, Decimal("101.5"), "EUR"), None
    if kind == "close-without-a-value":
        return (day, None, "EUR"), None
    rows = {
        "buy": _trade(tx_id, day, TransactionType.BUY, "5", "-500"),
        "sell": _trade(tx_id, day, TransactionType.SELL, "-2", "210"),
        "buy-of-amount-0": _trade(tx_id, day, TransactionType.BUY, "5", "0"),
        "adjustment-at-a-cost": _trade(tx_id, day, TransactionType.ADJUSTMENT, "3", "0", cost_basis_override=Decimal("90"), cost_basis_currency="EUR"),
        "split-linked-buy": _trade(tx_id, day, TransactionType.BUY, "5", "-500"),
    }
    return None, rows[kind]


def _random_series(rng: random.Random, start: date) -> tuple[AssetPriceSeries, date | None]:
    """A series built as the service builds it (``build_asset_price_series``) from up to six items of random kinds on
    distinct random days around ``start``, and the first day one of them is an observation (None: none is)."""
    price_rows: list[tuple] = []
    transactions: list[Transaction] = []
    split_linked: set[int] = set()
    observed: list[date] = []
    offsets = sorted(rng.sample(range(-40, 120), k=rng.randint(0, 6)))
    for tx_id, offset in enumerate(offsets, start=1):
        day = start + timedelta(days=offset)
        kind = rng.choice(_ITEM_KINDS)
        price_row, transaction = _item(kind, tx_id, day)
        if price_row is not None:
            price_rows.append(price_row)
        if transaction is not None:
            transactions.append(transaction)
        if kind == "split-linked-buy":
            split_linked.add(tx_id)
        if kind in _OBSERVING_KINDS:
            observed.append(day)
    series = build_asset_price_series(price_rows=price_rows, transactions=transactions, split_linked_tx_ids=split_linked, asset_currency="EUR", quote_base_quantity=1)
    return series, min(observed, default=None)


def _random_days(rng: random.Random, start: date) -> list[date]:
    """Up to 50 ascending days around ``start``: consecutive mostly, every other day or once a week at times."""
    first = start + timedelta(days=rng.randint(-60, 140))
    step = rng.choice((1, 1, 1, 2, 7))
    return [first + timedelta(days=step * index) for index in range(rng.randint(0, 50))]


def _reference_walk(days: Sequence[date], first_observation: date | None) -> date | None:
    """The contract as a walk over the days, read off the rows rather than the series: stop at the first day on or after
    the first observation, answer the day before it."""
    last = None
    for day in days:
        if first_observation is not None and day >= first_observation:
            break
        last = day
    return last


def _assert_observes_from(series: AssetPriceSeries, first_observation: date | None) -> None:
    """Precondition: the series observes from ``first_observation`` on, and nothing before it (nothing at all when None),
    as the reference walk reads the rows."""
    if first_observation is None:
        assert not series.has_observations
        return
    day_before = first_observation - timedelta(days=1)
    assert (series.resolve(day_before).is_missing, series.resolve(first_observation).is_missing) == (True, False), first_observation


@pytest.mark.parametrize("seed", range(5))
def test_last_day_without_observation_is_the_reference_walk_on_random_series(seed):
    """CONTROL (green today and after the bisection). 80 random series per seed (closes with and without a value, BUYs,
    SELLs, a trade of amount 0, ADJUSTMENTs, a split-linked BUY) read over random ascending days — none, an observation
    before the first day, after the last, in between, sparse days —: the last day before the first observation, as the
    reference walk finds it.
    """
    rng = random.Random(seed)
    for case in range(80):
        series, first_observation = _random_series(rng, date(2024, 1, 1))
        days = _random_days(rng, date(2024, 1, 1))
        _assert_observes_from(series, first_observation)

        observed = prices_module.last_day_without_observation(series, days)

        expected = _reference_walk(days, first_observation)
        assert observed == expected, f"seed {seed}, case {case}: first observation {first_observation}, {len(days)} days {days[:1]}…{days[-1:]}: {observed} != {expected}"


@pytest.mark.parametrize(
    ("observation_offset", "count", "expected_index"),
    [
        pytest.param(None, 10, 9, id="no-observation-at-all-the-last-day"),
        pytest.param(-3, 10, None, id="an-observation-before-the-first-day-None"),
        pytest.param(0, 10, None, id="an-observation-on-the-first-day-None"),
        pytest.param(4, 10, 3, id="an-observation-mid-run-the-day-before-it"),
        pytest.param(9, 10, 8, id="an-observation-on-the-last-day-the-day-before-it"),
        pytest.param(15, 10, 9, id="an-observation-after-the-last-day-the-last-day"),
        pytest.param(None, 1, 0, id="one-day-no-observation"),
        pytest.param(4, 0, None, id="no-day-None"),
    ],
)
def test_last_day_without_observation_on_its_edges(observation_offset, count, expected_index):
    """CONTROL (green today and after the bisection). One close, ``observation_offset`` days from the first day (None: no
    close), read over ``count`` consecutive days."""
    days = _days(count)
    price_rows = [] if observation_offset is None else [(MONDAY + timedelta(days=observation_offset), Decimal("100"), "EUR")]
    series = build_asset_price_series(price_rows=price_rows, transactions=[], split_linked_tx_ids=set(), asset_currency="EUR", quote_base_quantity=1)

    observed = prices_module.last_day_without_observation(series, days)

    assert observed == (None if expected_index is None else days[expected_index])


@pytest.mark.parametrize(
    "observation_index",
    [
        pytest.param(-7, id="the-seventh-day-from-the-end"),
        pytest.param(10_000, id="the-middle-day"),
        pytest.param(None, id="no-observation-at-all"),
    ],
)
def test_last_day_without_observation_bisects_the_days(monkeypatch, observation_index):
    """RED until L1a. 20 000 consecutive days from 1 Jan 1960 and one close on the day at ``observation_index`` (none at
    all for the last case): the answer is the day before the close (the last day when there is none) — green today —,
    reached in at most 2·ceil(log2(20 000)) + 4 = 34 calls of ``AssetPriceSeries.resolve``, counted on the class (the
    instances have ``__slots__``).

    Today: the walk resolves every day up to the close — 19 994 calls for the seventh day from the end, 10 001 for the
    middle one, 20 000 with no close.
    """
    days = _days(20_000, start=date(1960, 1, 1))
    observed_on = None if observation_index is None else days[observation_index]
    price_rows = [] if observed_on is None else [(observed_on, Decimal("100"), "EUR")]
    series = build_asset_price_series(price_rows=price_rows, transactions=[], split_linked_tx_ids=set(), asset_currency="EUR", quote_base_quantity=1)
    resolved: list[date] = []
    original_resolve = AssetPriceSeries.resolve

    def counting_resolve(self, query_date):
        resolved.append(query_date)
        return original_resolve(self, query_date)

    monkeypatch.setattr(AssetPriceSeries, "resolve", counting_resolve)

    observed = prices_module.last_day_without_observation(series, days)

    assert observed == (days[-1] if observed_on is None else observed_on - timedelta(days=1))
    bound = 2 * math.ceil(math.log2(len(days))) + 4
    assert len(resolved) <= bound, f"resolve was called {len(resolved)} times over {len(days)} days; a bisection needs at most {bound}"


def test_last_day_without_observation_bisects_a_day_range_of_seven_hundred_thousand_days(monkeypatch):
    """J5-5: the service hands it a ``DayRange`` (the calendar from the first transaction to the reading day, none of it
    stored). From the year 1 to 2026 with one close on 2 Jan 1900: the day before the close, in at most
    2·ceil(log2(739 000)) + 4 = 44 calls of ``AssetPriceSeries.resolve`` — a walk would make 693 000."""
    days = DayRange(date(1, 1, 1), date(2026, 10, 25))
    close = date(1900, 1, 2)
    series = build_asset_price_series(price_rows=[(close, Decimal("100"), "EUR")], transactions=[], split_linked_tx_ids=set(), asset_currency="EUR", quote_base_quantity=1)
    resolved: list[date] = []
    original_resolve = AssetPriceSeries.resolve

    def counting_resolve(self, query_date):
        resolved.append(query_date)
        return original_resolve(self, query_date)

    monkeypatch.setattr(AssetPriceSeries, "resolve", counting_resolve)

    observed = prices_module.last_day_without_observation(series, days)

    assert observed == close - timedelta(days=1)
    bound = 2 * math.ceil(math.log2(len(days))) + 4
    assert len(resolved) <= bound, f"resolve was called {len(resolved)} times over {len(days)} days; a bisection needs at most {bound}"

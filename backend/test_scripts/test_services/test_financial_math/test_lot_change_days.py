"""L1a — the lots analysis computed on its change days: ``lot_change_days``, ``expand_to_days`` and the bisected
``last_day_without_observation``.

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
- ``expand_to_days(rows, *, key, change_days, window_from, window_to)``: ``rows`` is a builder's output on the change
  days, grouped by key in first-appearance order, dates ascending within a key. For each key in that order, for each
  calendar day ``d`` of ``[window_from, window_to]`` ascending: the key's row on the last change day on or before ``d``,
  re-dated ``d``; nothing when there is no such change day or the key has no row on it. Every field but ``date``
  unchanged.
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
from backend.app.services.financial_math.price_marks import AssetPriceSeries, build_asset_price_series

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
# expand_to_days
# --------------------------------------------------------------------------- #


def _value_row(lot_id: int, day: date, value: str) -> LotValueHistoryPoint:
    """A value point whose figures say which row it is: an unknown fee and net P&L (None), an income written ``5.10``."""
    amount = Decimal(value)
    return LotValueHistoryPoint(
        lot_id=lot_id,
        date=day,
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


def _by_lot(row: LotValueHistoryPoint) -> int:
    return row.lot_id


def _expand(rows: Sequence, *, change_days: Sequence[date], window_from: date, window_to: date, key: Callable = _by_lot) -> list:
    expand_to_days = _change_days_function("expand_to_days")
    return expand_to_days(rows, key=key, change_days=change_days, window_from=window_from, window_to=window_to)


def _readable(rows: Sequence) -> list[tuple[date, dict]]:
    """Each row as (its date, every other field as JSON): the representation of each figure included."""
    return [(row.date, row.model_dump(mode="json", exclude={"date"})) for row in rows]


def _re_dated(pairs: Sequence[tuple[date, object]]) -> list[tuple[date, dict]]:
    """(day, source row) pairs as ``_readable`` reads the rows re-dated to those days."""
    return [(day, row.model_dump(mode="json", exclude={"date"})) for day, row in pairs]


def test_expand_to_days_carries_the_row_of_the_last_change_day_to_every_day_after_it():
    """RED until L1a. Change days 0, 3 and 7, one lot valued 1000, 1100 and 1200 on them, the window days 0–9: days 0–2
    read day 0's row, 3–6 day 3's, 7–9 day 7's — each re-dated, still a ``LotValueHistoryPoint``.

    Today: «change_days does not exist yet».
    """
    days = _days(10)
    change_days = _at(days, 0, 3, 7)
    first, second, third = (_value_row(1, day, value) for day, value in zip(change_days, ("1000", "1100", "1200"), strict=True))

    expanded = _expand([first, second, third], change_days=change_days, window_from=days[0], window_to=days[9])

    assert _readable(expanded) == _re_dated([*((day, first) for day in days[0:3]), *((day, second) for day in days[3:7]), *((day, third) for day in days[7:10])])
    assert {type(row) for row in expanded} == {LotValueHistoryPoint}


def test_expand_to_days_leaves_a_key_without_a_row_until_a_later_change_day_has_one():
    """RED until L1a. Change days 0, 3 and 7. Lot 1 has a row on each; lot 2 none on day 3 (a day it could not be valued),
    so nothing on days 3–6 and its row again from day 7; lot 3 opens on day 3, so nothing on days 0–2.

    Today: «change_days does not exist yet».
    """
    days = _days(10)
    change_days = _at(days, 0, 3, 7)
    lot_1 = [_value_row(1, day, value) for day, value in zip(change_days, ("1000", "1100", "1200"), strict=True)]
    lot_2 = [_value_row(2, days[0], "500"), _value_row(2, days[7], "520")]
    lot_3 = [_value_row(3, days[3], "300"), _value_row(3, days[7], "310")]

    expanded = _expand([*lot_1, *lot_2, *lot_3], change_days=change_days, window_from=days[0], window_to=days[9])

    expected = [
        *((day, lot_1[0]) for day in days[0:3]),
        *((day, lot_1[1]) for day in days[3:7]),
        *((day, lot_1[2]) for day in days[7:10]),
        *((day, lot_2[0]) for day in days[0:3]),
        *((day, lot_2[1]) for day in days[7:10]),
        *((day, lot_3[0]) for day in days[3:7]),
        *((day, lot_3[1]) for day in days[7:10]),
    ]
    assert _readable(expanded) == _re_dated(expected)


def test_expand_to_days_keeps_the_keys_in_their_order_of_first_appearance_and_the_days_ascending():
    """RED until L1a. Lot 9's rows come before lot 2's: every day of lot 9, ascending, then every day of lot 2 — never
    sorted by key.

    Today: «change_days does not exist yet».
    """
    days = _days(4)
    change_days = _at(days, 0, 2)
    rows = [_value_row(9, days[0], "900"), _value_row(9, days[2], "910"), _value_row(2, days[0], "200"), _value_row(2, days[2], "210")]

    expanded = _expand(rows, change_days=change_days, window_from=days[0], window_to=days[3])

    assert [(row.lot_id, row.date) for row in expanded] == [*((9, day) for day in days), *((2, day) for day in days)]


def test_expand_to_days_gives_nothing_before_the_first_change_day():
    """RED until L1a. Change days 5 and 8, the window days 0–9: days 0–4 have no change day on or before them, so no row;
    days 5–7 read day 5's, 8–9 day 8's.

    Today: «change_days does not exist yet».
    """
    days = _days(10)
    rows = [_value_row(1, days[5], "1000"), _value_row(1, days[8], "1010")]

    expanded = _expand(rows, change_days=_at(days, 5, 8), window_from=days[0], window_to=days[9])

    assert _readable(expanded) == _re_dated([*((day, rows[0]) for day in days[5:8]), *((day, rows[1]) for day in days[8:10])])


def test_expand_to_days_carries_a_change_day_before_the_window_into_it():
    """RED until L1a. Change days 0 and 8, the window days 3–9: days 3–7 read day 0's row — a change day before the
    window still speaks for it —, days 8–9 day 8's. Nothing before day 3.

    Today: «change_days does not exist yet».
    """
    days = _days(10)
    rows = [_value_row(1, days[0], "1000"), _value_row(1, days[8], "1010")]

    expanded = _expand(rows, change_days=_at(days, 0, 8), window_from=days[3], window_to=days[9])

    assert _readable(expanded) == _re_dated([*((day, rows[0]) for day in days[3:8]), *((day, rows[1]) for day in days[8:10])])


def test_expand_to_days_changes_nothing_but_the_date_and_leaves_the_builders_rows_as_they_were():
    """RED until L1a. Rows whose figures are written ``1000.10`` and ``999.900``, with None fields: every expanded row
    dumps, date aside, exactly as its source — same representation, same None —, and the source rows keep their own
    dates: re-dating never happens in place.

    Today: «change_days does not exist yet».
    """
    days = _days(6)
    rows = [_value_row(1, days[0], "1000.10"), _value_row(1, days[4], "999.900")]
    sources_before = [row.model_dump(mode="json") for row in rows]

    expanded = _expand(rows, change_days=_at(days, 0, 4), window_from=days[0], window_to=days[5])

    assert [row.date for row in expanded] == days
    assert [row.model_dump(mode="json", exclude={"date"}) for row in expanded] == [rows[0].model_dump(mode="json", exclude={"date"})] * 4 + [rows[1].model_dump(mode="json", exclude={"date"})] * 2
    assert [row.model_dump(mode="json") for row in rows] == sources_before


def _one_line(_row: MarketPriceHistoryPoint) -> None:
    return None


def test_expand_to_days_on_the_market_price_line_one_key_for_every_point():
    """RED until L1a. The market price line, one key for every point (``MarketPriceHistoryPoint``). Change days 0, 2 and
    5, a point on days 0 and 2 only — day 5 has no mark (a price without a rate) —, the window days 1–6: day 1 reads day
    0's point, days 2–4 day 2's, days 5–6 none.

    Today: «change_days does not exist yet».
    """
    days = _days(7)
    rows = [
        MarketPriceHistoryPoint(date=days[0], market_price=Decimal("100"), currency="EUR", estimated=True),
        MarketPriceHistoryPoint(date=days[2], market_price=Decimal("101.50"), currency="EUR", estimated=False),
    ]

    expanded = _expand(rows, key=_one_line, change_days=_at(days, 0, 2, 5), window_from=days[1], window_to=days[6])

    assert _readable(expanded) == _re_dated([(days[1], rows[0]), *((day, rows[1]) for day in days[2:5])])
    assert {type(row) for row in expanded} == {MarketPriceHistoryPoint}


@pytest.mark.parametrize(
    ("row_count", "window"),
    [
        pytest.param(1, (3, 2), id="a-window-that-ends-before-it-starts"),
        pytest.param(0, (0, 4), id="no-row"),
    ],
)
def test_expand_to_days_of_nothing_is_nothing(row_count, window):
    """RED until L1a. A window that ends before it starts — the analysis read from a day after its ``date_to`` —, or no
    row at all: no row.

    Today: «change_days does not exist yet».
    """
    days = _days(5)
    rows = [_value_row(1, days[0], "1000")][:row_count]

    assert _expand(rows, change_days=_at(days, 0), window_from=days[window[0]], window_to=days[window[1]]) == []


# --------------------------------------------------------------------------- #
# expand_to_days on every day: the trim it replaced
# --------------------------------------------------------------------------- #

_IDENTITY_LOT_IDS = (2, 5, 9, 11, 14, 23)
_IDENTITY_CASES = 48


def _ordered(first: int, second: int) -> tuple[int, int]:
    return min(first, second), max(first, second)


def _twice(offset: int) -> tuple[int, int]:
    return offset, offset


def _ending_before_it_starts(window_to: int, gap: int) -> tuple[int, int]:
    return window_to + gap, window_to


# The windows of the identity, as (window_from, window_to) offsets from the first day of a span of ``length`` days. Each
# ends on or before the span's last day, or ends before it starts: past the last day the contract carries the last
# change day's rows (test_expand_to_days_carries_the_row_of_the_last_change_day_to_every_day_after_it), which no trim
# did, and the service never asks for such a window — its window ends on ``actual_to``, the last day of ``days``.
_IDENTITY_WINDOWS: dict[str, Callable[[random.Random, int], tuple[int, int]]] = {
    "inside": lambda rng, length: _ordered(rng.randrange(length), rng.randrange(length)),
    "a-single-day-inside": lambda rng, length: _twice(rng.randrange(length)),
    "before-the-span": lambda rng, _length: _ordered(-rng.randint(1, 10), -rng.randint(1, 10)),
    "a-single-day-before-the-span": lambda rng, _length: _twice(-rng.randint(1, 10)),
    "straddling-the-first-day": lambda rng, length: (-rng.randint(1, 10), rng.randrange(length)),
    # The service's own window, [display_from, actual_to]: from before the span, its first day or inside it.
    "ending-on-the-last-day": lambda rng, length: (rng.choice((-rng.randint(1, 10), 0, rng.randrange(length))), length - 1),
    # The service's window read from a date_from after its date_to.
    "starting-after-the-span": lambda rng, length: (length - 1 + rng.randint(1, 10), length - 1),
    "ending-before-it-starts": lambda rng, length: _ending_before_it_starts(rng.randint(-5, length - 1), rng.randint(1, 10)),
}


def _identity_lot_rows(rng: random.Random, span: Sequence[date]) -> list[LotValueHistoryPoint]:
    """A value history as ``build_value_history`` gives it on every day of ``span``: lot by lot — two to four lots, never
    in the order of their ids —, each lot's days ascending from its opening, which always has its row, to its last day.
    The first lot opens on the span's first day and, whenever the span has three days, misses one inside its run (a day
    it was not valued); the second opens later; the third and fourth may stop before the span's last day; any other day
    misses its row one time in five."""
    length = len(span)
    lot_ids = rng.sample(_IDENTITY_LOT_IDS, rng.randint(2, 4))
    if lot_ids == sorted(lot_ids):
        lot_ids.reverse()
    rows: list[LotValueHistoryPoint] = []
    for index, lot_id in enumerate(lot_ids):
        opening = 0 if index == 0 else rng.randrange(1 if index == 1 and length > 1 else 0, length)
        last = length - 1 if index < 2 else rng.randrange(opening, length)
        hole = rng.randrange(opening + 1, last) if index == 0 and last - opening >= 2 else None
        for offset in range(opening, last + 1):
            if offset == hole or (offset > opening and rng.random() < 0.2):
                continue
            rows.append(_value_row(lot_id, span[offset], f"{rng.randint(800, 1300)}.{rng.choice(('0', '5', '50', '125'))}"))
    return rows


def _identity_line_rows(rng: random.Random, span: Sequence[date]) -> list[MarketPriceHistoryPoint]:
    """The market price line as ``build_market_price_history`` gives it on every day of ``span``: one point a day from the
    first mark — the span's first day or later —, which always has its point, to the span's last day; one day without a
    point inside the run whenever it is three days long (a mark without a rate), any other one time in five."""
    length = len(span)
    first = rng.randrange(length)
    hole = rng.randrange(first + 1, length - 1) if length - first >= 3 else None
    rows: list[MarketPriceHistoryPoint] = []
    for offset in range(first, length):
        if offset == hole or (offset > first and rng.random() < 0.2):
            continue
        price = Decimal(f"{rng.randint(90, 130)}.{rng.choice(('0', '5', '25'))}")
        rows.append(MarketPriceHistoryPoint(date=span[offset], market_price=price, currency="EUR", estimated=rng.random() < 0.3))
    return rows


# Each shape: its rows, its key, and what its cases must exercise between them (``_trim_shapes``).
_IDENTITY_SHAPES: dict[str, tuple[Callable[[random.Random, Sequence[date]], list], Callable, frozenset[str]]] = {
    "lot-value-history": (_identity_lot_rows, _by_lot, frozenset({"a key with a gap", "a key starting late", "keys out of their sorted order", "a window with rows", "a window without a row"})),
    "market-price-line": (_identity_line_rows, _one_line, frozenset({"a key with a gap", "a key starting late", "a window with rows", "a window without a row"})),
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
def test_expand_to_days_on_every_day_is_the_trim_it_replaced(shape, seed):
    """RED until L1a. With every day of a dense span a change day, ``expand_to_days`` is the trim it replaced,
    ``trim_dates(rows, window_from, window_to)`` = ``[row for row in rows if window_from <= row.date <= window_to]``: the
    same rows — the very objects, as a change day gives its row back unchanged — in the same order.

    Why: the parity battery (``test_financial/test_lots_change_days_parity.py``) compares A, the analysis on its change
    days, with B, the analysis with every day a change day, and calls B today's computation. B goes through
    ``expand_to_days`` too, so a defect that strikes A and B alike — the keys reordered, a row dropped, duplicated,
    copied or carried where the trim had none — passes the battery: a reordering of the keys did, caught only by the
    key-order test above. This identity is the step B rests on.

    The rows are a builder's (``_identity_lot_rows``, ``_identity_line_rows``): grouped by key in first-appearance order,
    days ascending within a key, lot ids out of their sorted order, a lot opening after the span's first day, a day
    without a row inside a run (a lot not valued, a mark without a rate), lots stopping before the span's last day — the
    value history keyed by ``lot_id`` (``LotValueHistoryPoint``), the market price line by one key for every point
    (``MarketPriceHistoryPoint``). 48 cases a seed, with the windows of ``_IDENTITY_WINDOWS`` in turn: inside the span, a
    single day inside it, before it, a single day before it, straddling its first day, ending on its last day (the
    service's own window, ``[display_from, actual_to]``), starting after it (``date_from`` after ``date_to``), ending
    before it starts. Precondition: the cases do exercise those shapes, and windows with rows and without.

    No window reaches past the span's last day: there the contract carries the last change day's rows
    (``test_expand_to_days_carries_the_row_of_the_last_change_day_to_every_day_after_it``), which no trim did — and the
    service never asks for one, its window ending on ``actual_to``, the last day of ``days``.

    Today: «change_days does not exist yet».
    """
    expand_to_days = _change_days_function("expand_to_days")
    build_rows, key, to_cover = _IDENTITY_SHAPES[shape]
    cases = _trim_cases(random.Random(seed), build_rows)
    covered = set().union(*(_trim_shapes(case, key) for case in cases))
    assert to_cover <= covered, f"precondition: {shape}, seed {seed} never generates {sorted(to_cover - covered)}"

    for number, case in enumerate(cases):
        expanded = expand_to_days(case.rows, key=key, change_days=case.span, window_from=case.window_from, window_to=case.window_to)

        context = f"{shape}, seed {seed}, case {number}: window {case.kind} [{case.window_from}, {case.window_to}] over the {len(case.span)} days {case.span[0]}–{case.span[-1]}, {len(case.rows)} rows"
        assert [(row.date, row.model_dump(mode="json")) for row in expanded] == [(row.date, row.model_dump(mode="json")) for row in case.trimmed], context
        copies = [index for index, (returned, source) in enumerate(zip(expanded, case.trimmed, strict=True)) if returned is not source]
        assert copies == [], f"{context}: the rows at {copies} are not the builder's own objects"


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

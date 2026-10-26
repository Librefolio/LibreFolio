"""The days a lots analysis computes its daily series on, and the steps they make (L1a «formule veloci», D-P4 cure B).

The value, return and price of each lot, the market price line, the average-cost lines and the performance change only
on the days one of their inputs changes: a converted market price (a new observation, or a new exchange rate), a
transaction, a fragment that starts or ends, a closure, an income, fee or tax, a pool whose amount becomes unknown, a
step of an average-cost line, the end of the days valued at cost. The analysis reads the market price on the days it can
change (:func:`price_candidate_days`), computes the series on those that really change (:func:`lot_change_days`) and
gives each series as steps (:func:`history_steps`): a row holds from its ``date`` to its ``through``, both included, and
two consecutive rows of one key with the same figures — down to the exponent of every Decimal — are one row. Between two
change days every input of a day is the very value of the day before, down to its digits, so a step expanded to its days
is, field for field, the row a day-by-day computation gives on each of them. No list of every day of the window is ever
built: a date typed in the year 1 costs what its changes cost.

A series may also change on the day after one of its inputs, with no input of its own changing: the TWRR starts on the
day after the first value of the performance, and the price line of a closed lot stops on the day after its last
closure. Every change day therefore brings the day after it.

The rule is the portfolio engine's (decision 28, «recompute whenever a term of the formula changes»), not its function:
``native_cash.change_days`` finds the day a rate changes, comparing rates; here the converted mark itself is compared, in
its exact representation, because the series must stay byte-identical.
"""

from __future__ import annotations

from collections.abc import Callable, Hashable, Iterable, Mapping, Sequence
from datetime import date as date_type
from datetime import timedelta
from decimal import Decimal
from typing import Any, Protocol, overload

from backend.app.services.financial_math.average_cost import AverageCost
from backend.app.services.financial_math.fifo.models import FifoEngineResult
from backend.app.services.financial_math.lots.economic_events import WithheldEconomics
from backend.app.services.financial_math.series_steps import steps_from_rows

_ONE_DAY = timedelta(days=1)


class _Dated(Protocol):
    date: date_type


def lot_change_days(
    *,
    days: Sequence[date_type],
    market_prices: Mapping[date_type, Decimal | None],
    estimated_market_prices: Mapping[date_type, tuple[Decimal, bool]],
    at_cost_until: date_type | None,
    event_dates: Iterable[date_type],
) -> list[date_type]:
    """The days of ``days`` (ascending) a daily series of the lots can change on, ascending.

    The first and the last day; every day whose converted market price, or its estimated mark, is not the previous
    day's down to its representation (``Decimal('1.10')`` is not ``Decimal('1.1')``: it prints otherwise); the day after
    ``at_cost_until``; every one of ``event_dates``; and the day after each of those. Only days of ``days``.
    """
    if not days:
        return []
    calendar = set(days)
    changes: set[date_type] = {days[0], days[-1]}
    previous_price: Decimal | None = None
    previous_estimate: tuple[Decimal, bool] | None = None
    for index, day in enumerate(days):
        price = market_prices.get(day)
        estimate = estimated_market_prices.get(day)
        if index and (not _same_amount(price, previous_price) or not _same_estimate(estimate, previous_estimate)):
            changes.add(day)
        previous_price, previous_estimate = price, estimate
    if at_cost_until is not None:
        changes.add(at_cost_until + _ONE_DAY)
    changes.update(event_dates)
    inside = {day for day in changes if day in calendar}
    inside.update(day + _ONE_DAY for day in list(inside) if day + _ONE_DAY in calendar)
    return sorted(inside)


def analysis_event_dates(
    *,
    transactions: Iterable[_Dated],
    engine_results: Iterable[FifoEngineResult],
    prefixes: Iterable[Mapping[int, Mapping[date_type, Decimal]]],
    withheld: WithheldEconomics,
    average_cost_lines: Iterable[AverageCost],
) -> set[date_type]:
    """The dates an input of the daily series changes on, other than the market price: the transactions', the openings,
    the starts and ends of the fragments, the closures and the engine's events, the dates of the cumulative incomes,
    fees and taxes, those a pool becomes unknown from, and the steps of the average-cost lines.

    Today the rows and what the engine derives from them cover each other: in L1a's mutations, dropping either kept
    every output identical. Both are read, so that a date one of them comes to derive on its own is never missed.
    """
    dates = {transaction.date for transaction in transactions}
    for result in engine_results:
        dates.update(lot.opening_date for lot in result.lots)
        for fragment in result.fragment_intervals:
            dates.add(fragment.start_date)
            if fragment.end_date is not None:
                dates.add(fragment.end_date)
        dates.update(closure.close_date for closure in result.closures)
        dates.update(event.date for event in result.classified_events)
    for prefix_by_lot in prefixes:
        for prefix in prefix_by_lot.values():
            dates.update(prefix)
    for unknown_from in (withheld.income_from, withheld.fees_from, withheld.taxes_from):
        dates.update(unknown_from.values())
    for line in average_cost_lines:
        dates.update(step.movement.date for step in line.steps)
    return dates


class DayRange(Sequence[date_type]):
    """The calendar days ``first``..``last``, both included, as a sequence that holds none of them: ``len`` and indexing
    are arithmetic, so a bisection over a window of seven hundred thousand days (``last_day_without_observation``) reads
    a few of them. Empty when ``last`` is before ``first``."""

    __slots__ = ("_first", "_length")

    def __init__(self, first: date_type, last: date_type) -> None:
        self._first = first
        self._length = max((last - first).days + 1, 0)

    def __len__(self) -> int:
        return self._length

    @overload
    def __getitem__(self, index: int) -> date_type: ...
    @overload
    def __getitem__(self, index: slice) -> Sequence[date_type]: ...
    def __getitem__(self, index: int | slice) -> date_type | Sequence[date_type]:
        if isinstance(index, slice):
            raise TypeError("a DayRange is read by position: slice it with DayRange(first, last)")
        position = index + self._length if index < 0 else index
        if not 0 <= position < self._length:
            raise IndexError("DayRange index out of range")
        return self._first + timedelta(days=position)

    def __contains__(self, day: object) -> bool:
        return isinstance(day, date_type) and 0 <= (day - self._first).days < self._length

    def __iter__(self):
        for position in range(self._length):
            yield self._first + timedelta(days=position)


def price_candidate_days(
    *,
    first: date_type,
    last: date_type,
    observation_dates: Iterable[date_type],
    rate_days: Iterable[date_type],
    event_dates: Iterable[date_type],
    at_cost_until: date_type | None,
) -> list[date_type]:
    """The days of ``first``..``last`` (ascending) on which the converted market price, or any figure the analysis builds
    on it, can differ from the day before — a superset of the days :func:`lot_change_days` keeps.

    The market price of a day is the last observation's price at that day's rate: it moves only on an observation date
    (``AssetPriceSeries.observation_dates``) or when a rate moves (``rate_days``: the days a rate in the target currency
    changes, ``FxRateResolver.rate_change_days``). With the first and the last day, the day after ``at_cost_until``, the
    ``event_dates`` and the day after each of them, those are the days the analysis reads the price on; every other day
    of the window repeats the day before it, to the digit. A day more costs a lookup and changes nothing; a day missing
    would change figures silently: ``rate_days`` and ``observation_dates`` must be every day, not a sample.
    """
    if last < first:
        return []
    seeds: set[date_type] = {first, last}
    seeds.update(observation_dates)
    seeds.update(rate_days)
    seeds.update(event_dates)
    if at_cost_until is not None:
        seeds.add(at_cost_until + _ONE_DAY)
    inside = {day for day in seeds if first <= day <= last}
    inside.update(day + _ONE_DAY for day in list(inside) if day + _ONE_DAY <= last)
    return sorted(inside)


def _row_values(row: Any) -> tuple[Any, ...]:
    """A history row's figures: every field of the model but the days it holds."""
    return tuple(value for name, value in row if name not in ("date", "through"))


def history_steps[R](
    rows: Sequence[R],
    *,
    key: Callable[[R], Hashable],
    change_days: Sequence[date_type],
    range_start: date_type,
    range_end: date_type,
) -> list[R]:
    """The steps of a history built on ``change_days`` (ascending), clipped to ``range_start``..``range_end``.

    ``rows`` are pydantic rows with ``date`` and ``through`` (one day each: ``through`` = ``date``), grouped by ``key``
    in any order, dates ascending per key. Each key's row holds from its change day to the day before its next change
    day, and a change day with no row of that key — after its first — is a gap: the key has no value there. Two
    consecutive rows of a key with the same figures, with the exponent of each Decimal, are one step, the first row with
    its days widened. The keys come out in the order of their first row, each one's steps in order; a day of the window
    holds the row of the last change day on or before it, as a day-by-day answer would give.
    """
    if not rows or range_start > range_end:
        return []
    by_key: dict[Hashable, dict[date_type, R]] = {}
    for row in rows:
        by_key.setdefault(key(row), {})[row.date] = row  # type: ignore[attr-defined]
    entries: list[tuple[date_type, R | None, Hashable]] = []
    for series_key, rows_by_day in by_key.items():
        started = False
        for day in change_days:
            row = rows_by_day.get(day)
            if row is None and not started:
                continue
            started = True
            entries.append((day, row, series_key))
    steps = steps_from_rows(
        entries,
        day=lambda entry: entry[0],
        values=lambda entry: _row_values(entry[1]),
        key=lambda entry: entry[2],
        is_gap=lambda entry: entry[1] is None,
        range_start=range_start,
        range_end=range_end,
    )
    out: list[R] = []
    for step in steps:
        row = step.row[1]
        if row.date == step.date and row.through == step.through:  # type: ignore[attr-defined]
            out.append(row)
        else:
            out.append(row.model_copy(update={"date": step.date, "through": step.through}))  # type: ignore[attr-defined]
    return out


def _same_amount(left: Decimal | None, right: Decimal | None) -> bool:
    if left is None or right is None:
        return left is right
    return left.as_tuple() == right.as_tuple()


def _same_estimate(left: tuple[Decimal, bool] | None, right: tuple[Decimal, bool] | None) -> bool:
    if left is None or right is None:
        return left is right
    return left[1] == right[1] and left[0].as_tuple() == right[0].as_tuple()

"""The days a lots analysis computes its daily series on (L1a, «formule veloci»).

The value, return and price of each lot, the market price line, the average-cost lines and the performance change only
on the days one of their inputs changes: a converted market price (a new observation, or a new exchange rate), a
transaction, a fragment that starts or ends, a closure, an income, fee or tax, a pool whose amount becomes unknown, a
step of an average-cost line, the end of the days valued at cost. The analysis computes the series on those days only
(:func:`lot_change_days`) and fills every other day of the window from the last of them before it
(:func:`expand_to_days`). Between two change days every input of a day is the very value of the day before, down to its
digits, so a day computed there would repeat the same figures: the series are the same, byte for byte, as when every day
is computed.

A series may also change on the day after one of its inputs, with no input of its own changing: the TWRR starts on the
day after the first value of the performance, and the price line of a closed lot stops on the day after its last
closure. Every change day therefore brings the day after it.

The rule is the portfolio engine's (decision 28, «recompute whenever a term of the formula changes»), not its function:
``native_cash.change_days`` finds the day a rate changes, comparing rates; here the converted mark itself is compared, in
its exact representation, because the series must stay byte-identical.
"""

from __future__ import annotations

import bisect
from collections.abc import Callable, Hashable, Iterable, Mapping, Sequence
from datetime import date as date_type
from datetime import timedelta
from decimal import Decimal
from typing import Protocol

from backend.app.services.financial_math.average_cost import AverageCost
from backend.app.services.financial_math.fifo.models import FifoEngineResult
from backend.app.services.financial_math.lots.economic_events import WithheldEconomics

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


def expand_to_days[R](
    rows: Sequence[R],
    *,
    key: Callable[[R], Hashable],
    change_days: Sequence[date_type],
    window_from: date_type,
    window_to: date_type,
) -> list[R]:
    """Every day of ``[window_from, window_to]`` from the rows of the last change day on or before it, with its date.

    ``rows`` are a series built on ``change_days`` (ascending): grouped by ``key`` in their order, dates ascending. The
    result keeps that order, key by key, a row on every day of the window whose change day has one for its key; a day
    before the first change day has none.
    """
    if not change_days or window_from > window_to:
        return []
    governing: list[tuple[date_type, date_type]] = []
    index = bisect.bisect_right(change_days, window_from) - 1
    day = window_from
    while day <= window_to:
        while index + 1 < len(change_days) and change_days[index + 1] <= day:
            index += 1
        if index >= 0:
            governing.append((day, change_days[index]))
        day += _ONE_DAY
    by_key: dict[Hashable, dict[date_type, R]] = {}
    for row in rows:
        by_key.setdefault(key(row), {})[row.date] = row  # type: ignore[attr-defined]
    expanded: list[R] = []
    for rows_by_date in by_key.values():
        for day, change_day in governing:
            row = rows_by_date.get(change_day)
            if row is not None:
                expanded.append(row if change_day == day else row.model_copy(update={"date": day}))  # type: ignore[attr-defined]
    return expanded


def _same_amount(left: Decimal | None, right: Decimal | None) -> bool:
    if left is None or right is None:
        return left is right
    return left.as_tuple() == right.as_tuple()


def _same_estimate(left: tuple[Decimal, bool] | None, right: tuple[Decimal, bool] | None) -> bool:
    if left is None or right is None:
        return left is right
    return left[1] == right[1] and left[0].as_tuple() == right[0].as_tuple()

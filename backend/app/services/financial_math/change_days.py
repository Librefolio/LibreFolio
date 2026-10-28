"""The days something can change on: one home for the rules every daily series shares.

A daily figure is computed only on the days one of its inputs can change, never on every day of a calendar (P3, D-P4):

* :func:`reading_change_days` — the days a reading of an FX pair can differ from the day before, from a map of unit
  rates: an ``AskedDayRates`` gives its steps and window bounds, a plain map (built by hand in tests) each key's day and
  the day after;
* :func:`change_days` — the days of a calendar on which a reading of rates really differs from the calendar's previous
  day (the comparison, after the candidates above);
* :func:`with_next_days` — days with the day after each, inside a calendar: a series that also changes on the day after
  one of its inputs (the TWRR's start, a closed lot's price line).

The two unions that call them stay with their domain: the portfolio engine recomputes when a term of its formula
changes and compares rates (``DailyStateBuilder._collect_dirty_days``); the lots analysis compares the converted price
in its exact representation (``lots/change_days``). The merging of day spans is ``series_steps.merged_spans``.
"""

from __future__ import annotations

from collections.abc import Callable, Container, Iterable, Mapping
from datetime import date as date_type
from datetime import timedelta
from decimal import Decimal

from backend.app.services.financial_math.fx_rates import AskedDayRates

_ONE_DAY = timedelta(days=1)


def reading_change_days(rates: Mapping[tuple, Decimal], source: str, destination: str) -> tuple[date_type, ...]:
    """The days, ascending, on which the reading of ``source`` → ``destination`` in ``rates`` may differ from the day
    before. Every day it changes is here; a day here need not be a change.

    On an :class:`AskedDayRates` they are its steps and window bounds (``AskedDayRates.reading_change_days``). On a plain
    map — keyed ``(source, destination, day)``, or ``(source, day)`` for a map into one destination — each key's day and
    the day after (none after ``date.max``).
    """
    if isinstance(rates, AskedDayRates):
        return rates.reading_change_days(source, destination)
    days: set[date_type] = set()
    for key in rates:
        if len(key) == 3 and key[0] == source and key[1] == destination:
            day = key[2]
        elif len(key) == 2 and key[0] == source:
            day = key[1]
        else:
            continue
        days.add(day)
        if day < date_type.max:
            days.add(day + _ONE_DAY)
    return tuple(sorted(days))


def change_days(read: Callable[[str, date_type], Decimal | None], currencies: Iterable[str], days: Iterable[date_type]) -> tuple[date_type, ...]:
    """The days of the calendar ``days``, in its order, on which ``read`` gives a currency of ``currencies`` another
    rate than on the calendar's previous day — the one home of «the day a rate changes».

    The caller chooses the reading and the calendar: the native cash reads the last rate known on or before the day,
    on the calendar of its rate points; the portfolio engine reads the rate of the exact day, on the days a rate can
    change and the day before each (``DailyStateBuilder._reading_calendar``). A rate that appears or disappears is a change, and so is a rate on the calendar's first day.
    """
    watched = tuple(sorted(set(currencies)))
    changed: list[date_type] = []
    previous: dict[str, Decimal | None] = dict.fromkeys(watched)
    for day in days:
        rates = {currency: read(currency, day) for currency in watched}
        if rates != previous:
            changed.append(day)
        previous = rates
    return tuple(changed)


def with_next_days(days: Iterable[date_type], calendar: Container[date_type]) -> set[date_type]:
    """The days of ``days`` inside ``calendar``, with the day after each when it is in ``calendar`` too.

    ``calendar`` is anything that answers ``in``: a set of days, a ``lots.change_days.DayRange`` for a window.
    """
    inside = {day for day in days if day in calendar}
    inside.update(day + _ONE_DAY for day in list(inside) if day < date_type.max and day + _ONE_DAY in calendar)
    return inside

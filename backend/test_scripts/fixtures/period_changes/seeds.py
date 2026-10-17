"""Seeds of the MF-P2 period-change tests: values whose quotients terminate, and irregular days.

Every price and rate is of the form 2^a·5^b. A product or quotient of such values is again 2^c·5^d, a terminating
decimal of a few digits, so the services' Decimal arithmetic is exact and the page ports (``page_ports.py``) can be
compared with ``==`` rather than within a tolerance. Each value also reads back unchanged from its column: a close
(``RealDecimal``, a double) has a short exact representation, a rate (``NUMERIC(24, 10)``) at most three decimals.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, timedelta
from decimal import Decimal

#: Closes, 2^a·5^b: 100 = 2²5², 62.5 = 2⁻¹5³, 256 = 2⁸ …
TERMINATING_PRICES: tuple[Decimal, ...] = tuple(Decimal(value) for value in ("100", "125", "80", "160", "64", "200", "250", "128", "50", "62.5", "40", "256"))

#: Rates, 2^a·5^b: 1.25 = 2⁻²5, 0.64 = 2⁴5⁻², 1.024 = 2⁷5⁻³ …
TERMINATING_RATES: tuple[Decimal, ...] = tuple(Decimal(value) for value in ("1.25", "1.6", "2", "2.5", "0.8", "3.2", "4", "0.64", "1.024", "5"))


def scattered_days(first: date, last: date, gaps: Sequence[int]) -> list[date]:
    """The days from ``first`` up to ``last``, stepping through ``gaps`` in a cycle: irregular, weekends included."""
    days: list[date] = []
    day = first
    while day <= last:
        day_gap = gaps[len(days) % len(gaps)]
        days.append(day)
        day += timedelta(days=day_gap)
    return days


def cycled(values: Sequence[Decimal], count: int, stride: int) -> list[Decimal]:
    """``count`` values taken from ``values`` every ``stride`` positions: with a stride prime to the length, no two
    neighbours are equal, so a change between two consecutive rows is never 0 by accident."""
    return [values[(index * stride) % len(values)] for index in range(count)]


def series(days: Sequence[date], values: Sequence[Decimal], stride: int) -> dict[date, Decimal]:
    """One value per day, cycled from ``values``."""
    return dict(zip(days, cycled(values, len(days), stride), strict=True))


def last_on_or_before(values: Mapping[date, Decimal], day: date) -> Decimal | None:
    """The value of the last day on or before ``day``: the backward fill both services and pages rely on."""
    candidates = [stored for stored in values if stored <= day]
    return values[max(candidates)] if candidates else None


def first_carried_day(values: Mapping[date, Decimal], after: date, before: date) -> date:
    """The first day after ``after`` and before ``before`` with nothing stored on it, a value carried from an earlier
    day, and that value other than the one on ``before``: a range start whose reference is backward-filled, over a range
    ending on ``before`` whose change is not 0 (X-R59). AssertionError when the data has no such day."""
    anchor = last_on_or_before(values, before)
    day = after + timedelta(days=1)
    while day < before:
        carried = last_on_or_before(values, day)
        if day not in values and carried is not None and carried != anchor:
            return day
        day += timedelta(days=1)
    raise AssertionError(f"no carried day with a value other than {anchor} between {after} and {before}")

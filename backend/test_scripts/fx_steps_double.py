"""A stand-in for ``fx.conversion.unit_rate_steps`` for tests that call the FX convert handler on no database (X-Q3).

The handler asks ``unit_rate_steps`` which stored rate row each day reads, and ``convert`` (``convert_bulk``) for one
conversion per stretch of days on the same row. A test that replaces ``convert_bulk`` by a double must say the same thing about
its rates: ``steps_double(rate_day_of)`` gives the steps of a pair from a function ``(source, destination, day) -> rate day``
(``None`` before the pair's first rate). The default is a rate row on every day, so each day is its own stretch.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from backend.app.services.fx.conversion import UnitRateSteps

RateDayOf = Callable[[str, str, date], date | None]


def steps_double(rate_day_of: RateDayOf = lambda _source, _destination, day: day) -> Callable[..., Any]:
    async def steps(_session: Any, requests: dict) -> dict:
        found = {}
        for (source, destination), windows in requests.items():
            days = sorted({first + timedelta(days=n) for first, last in windows for n in range((last - first).days + 1)})
            rated = [(day, rate_day_of(source, destination, day)) for day in days]
            rated = [(day, rate_day) for day, rate_day in rated if rate_day is not None]
            found[(source, destination)] = UnitRateSteps(
                source=source,
                destination=destination,
                days=tuple(day for day, _rate_day in rated),
                values=tuple(Decimal(1) for _ in rated),
                rate_days=tuple(rate_day for _day, rate_day in rated),
            )
        return found

    return steps

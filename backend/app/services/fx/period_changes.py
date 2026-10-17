"""Fixed-period changes of FX rates: the Δ columns of the FX table (MF-P2, developer decision D-MF6 b).

The rate of a pair on a day is the conversion of 1 base into the quote on that day (``convert_bulk``, with its
unlimited backward fill), the rate the FX page reads from ``POST /fx/currencies/convert``. The change, in both orientations of
the pair, is the house's (``financial_math.returns.fixed_period_changes``); this module only values the days it names.

With a ``range_start`` (X-R59) it also values the change over the whole range the page shows, the house's
``range_change``: from the rate on ``range_start`` — or, when the pair has none on or before it, the first stored rate
inside the range, the first point of the page's series — to the rate on ``as_of``.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import FxRate
from backend.app.db.precision import usable_fx_rate_bounds
from backend.app.schemas.common import Currency
from backend.app.schemas.fx import FXPeriodChange, FXPeriodChangesRequest, FXPeriodChangesResult, FXRangeChange
from backend.app.services.financial_math.returns import fixed_period_changes, fixed_period_dates, range_change
from backend.app.services.fx.conversion import FX_PAIRS_PER_QUERY, convert_bulk


def _stored_pair(base: str, quote: str) -> tuple[str, str]:
    """The pair as ``fx_rates`` stores it: its two codes in alphabetical order (``convert_bulk`` inverts the other way)."""
    return (base, quote) if base < quote else (quote, base)


async def _first_rate_days_inside(session: AsyncSession, pairs: set[tuple[str, str]], after: date, until: date) -> dict[tuple[str, str], date]:
    """Each stored pair's first usable rate day after ``after`` and on or before ``until`` (X-R38's usable bounds).

    In chunks of ``FX_PAIRS_PER_QUERY`` pairs (R13-SEC9-2), as ``convert_bulk``: SQLite refuses an OR of about a thousand.
    """
    smallest_rate, first_refused_rate = usable_fx_rate_bounds()
    ordered = sorted(pairs)
    first_days: dict[tuple[str, str], date] = {}
    for start in range(0, len(ordered), FX_PAIRS_PER_QUERY):
        stmt = (
            select(FxRate.base, FxRate.quote, func.min(FxRate.date))
            .where(
                or_(*(and_(FxRate.base == base, FxRate.quote == quote) for base, quote in ordered[start : start + FX_PAIRS_PER_QUERY])),
                FxRate.date > after,
                FxRate.date <= until,
                FxRate.rate >= smallest_rate,
                FxRate.rate < first_refused_rate,
            )
            .group_by(FxRate.base, FxRate.quote)
        )
        first_days.update({(base, quote): first_day for base, quote, first_day in (await session.execute(stmt)).all()})
    return first_days


async def _range_references(session: AsyncSession, requests: Sequence[FXPeriodChangesRequest], on_start: list[Decimal | None]) -> list[tuple[date, Decimal | None] | None]:
    """The reference of each request's whole-range change: (its day, the rate on it); None without a range or a rate.

    ``on_start`` holds the rate on each request's ``range_start`` (None without one): when it exists the reference is that
    rate, on ``range_start``; otherwise it is the first stored rate inside the range, converted on its own day.
    """
    references: list[tuple[date, Decimal | None] | None] = [None] * len(requests)
    lacking: dict[tuple[date, date], set[tuple[str, str]]] = {}
    for index, (request, rate) in enumerate(zip(requests, on_start, strict=True)):
        if request.range_start is None:
            continue
        if rate is not None:
            references[index] = (request.range_start, rate)
        else:
            lacking.setdefault((request.range_start, request.as_of), set()).add(_stored_pair(request.base, request.quote))
    first_days = {window: await _first_rate_days_inside(session, pairs, *window) for window, pairs in sorted(lacking.items())}
    pending = [(index, first_day) for index, request in enumerate(requests) if request.range_start is not None and references[index] is None and (first_day := first_days.get((request.range_start, request.as_of), {}).get(_stored_pair(request.base, request.quote))) is not None]
    if pending:
        converted, _messages = await convert_bulk(session, [(Currency(code=requests[index].base, amount=Decimal(1)), requests[index].quote, day) for index, day in pending], raise_on_error=False)
        for (index, day), result in zip(pending, converted, strict=True):
            references[index] = (day, result[0].amount if result is not None else None)
    return references


def _range_change(request: FXPeriodChangesRequest, reference: tuple[date, Decimal | None] | None, anchor: Decimal | None) -> FXRangeChange | None:
    """The whole-range change of one request; None when it asked none, empty when the pair has no rate in the range."""
    if request.range_start is None:
        return None
    if reference is None:
        return FXRangeChange()
    change = range_change(reference[1], anchor)
    return FXRangeChange(
        reference_date=reference[0],
        change_abs=change.change_abs,
        change_ratio=change.change_ratio,
        inverse_change_abs=change.inverse_change_abs,
        inverse_change_ratio=change.inverse_change_ratio,
    )


async def get_fx_period_changes_bulk(requests: Sequence[FXPeriodChangesRequest], session: AsyncSession) -> list[FXPeriodChangesResult]:
    """The fixed-period changes of every requested pair, in request order, and its whole-range change when asked."""
    if not requests:
        return []
    days_of = [fixed_period_dates(request.as_of) for request in requests]
    conversions = [(Currency(code=request.base, amount=Decimal(1)), request.quote, day) for request, days in zip(requests, days_of, strict=True) for day in days]
    starts = [request for request in requests if request.range_start is not None]
    conversions += [(Currency(code=request.base, amount=Decimal(1)), request.quote, request.range_start) for request in starts]
    converted, _messages = await convert_bulk(session, conversions, raise_on_error=False)

    position = sum(len(days) for days in days_of)
    start_rates = iter(result[0].amount if result is not None else None for result in converted[position:])
    on_start = [next(start_rates) if request.range_start is not None else None for request in requests]
    references = await _range_references(session, requests, on_start)

    results = []
    position = 0
    for request, days, reference in zip(requests, days_of, references, strict=True):
        values: dict[date, Decimal | None] = {}
        errors: list[str] = []
        for day in days:
            result = converted[position]
            position += 1
            values[day] = result[0].amount if result is not None else None
            if result is None:
                errors.append(f"No {request.base}/{request.quote} rate on or before {day}")
        results.append(
            FXPeriodChangesResult(
                base=request.base,
                quote=request.quote,
                as_of=request.as_of,
                periods=[FXPeriodChange(key=change.key, days=change.days, change_ratio=change.change_ratio, inverse_change_ratio=change.inverse_change_ratio) for change in fixed_period_changes(values, request.as_of)],
                range_change=_range_change(request, reference, values.get(request.as_of)),
                errors=errors,
            )
        )
    return results

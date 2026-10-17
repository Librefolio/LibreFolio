"""Fixed-period changes of FX rates: the Δ columns of the FX table (MF-P2, developer decision D-MF6 b).

The rate of a pair on a day is the conversion of 1 base into the quote on that day (``convert_bulk``, with its
unlimited backward fill), the rate the FX page reads from ``POST /fx/currencies/convert``. The change, in both orientations of
the pair, is the house's (``financial_math.returns.fixed_period_changes``); this module only values the days it names.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.schemas.common import Currency
from backend.app.schemas.fx import FXPeriodChange, FXPeriodChangesRequest, FXPeriodChangesResult
from backend.app.services.financial_math.returns import fixed_period_changes, fixed_period_dates
from backend.app.services.fx.conversion import convert_bulk


async def get_fx_period_changes_bulk(requests: Sequence[FXPeriodChangesRequest], session: AsyncSession) -> list[FXPeriodChangesResult]:
    """The fixed-period changes of every requested pair, in request order: one conversion batch for all of them."""
    if not requests:
        return []
    days_of = [fixed_period_dates(request.as_of) for request in requests]
    conversions = [(Currency(code=request.base, amount=Decimal(1)), request.quote, day) for request, days in zip(requests, days_of, strict=True) for day in days]
    converted, _messages = await convert_bulk(session, conversions, raise_on_error=False)

    results = []
    position = 0
    for request, days in zip(requests, days_of, strict=True):
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
                errors=errors,
            )
        )
    return results

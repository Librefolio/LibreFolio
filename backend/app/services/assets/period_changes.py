"""Fixed-period changes of asset prices: the Δ columns of the Assets table (MF-P2, developer decision D-MF6 b).

The price of an asset on a day is the last stored price on or before it — the backward fill of the price history
(``PriceQueryOperations._build_backward_filled_series``) — and, with a target currency, that price converted at that
day's rate, as the price query converts each day of its series. The change itself is the house's
(``financial_math.returns.fixed_period_changes``); this module only values the days it names.

Reads the stored history directly, so a long period has its change whatever range the page has loaded: one grouped
query per valued day for every asset of the request, never a series per asset.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import PriceHistory
from backend.app.schemas.common import Currency
from backend.app.schemas.prices import FAPeriodChange, FAPeriodChangesQueryItem, FAPeriodChangesResult
from backend.app.services.financial_math.returns import fixed_period_changes, fixed_period_dates
from backend.app.services.fx.conversion import convert_bulk

_MAX_ERRORS = 10


async def _last_prices_on_or_before(session: AsyncSession, asset_ids: Sequence[int], day: date) -> dict[int, tuple[date, Decimal | None, str]]:
    """Each asset's last stored price on or before ``day``: (its date, close, currency)."""
    latest = select(PriceHistory.asset_id, func.max(PriceHistory.date).label("latest")).where(and_(PriceHistory.asset_id.in_(asset_ids), PriceHistory.date <= day)).group_by(PriceHistory.asset_id).subquery()
    rows = await session.execute(select(PriceHistory.asset_id, PriceHistory.date, PriceHistory.close, PriceHistory.currency).join(latest, and_(PriceHistory.asset_id == latest.c.asset_id, PriceHistory.date == latest.c.latest)))
    return {asset_id: (price_date, close, currency) for asset_id, price_date, close, currency in rows.all()}


def _capped(errors: list[str]) -> list[str]:
    unique = list(dict.fromkeys(errors))
    if len(unique) > _MAX_ERRORS:
        return unique[:_MAX_ERRORS] + [f"… and {len(unique) - _MAX_ERRORS} more"]
    return unique


class _Valuation:
    """One asset's prices on the valued days, in one currency, with the conversions they still need."""

    def __init__(self, item: FAPeriodChangesQueryItem, days: Sequence[date], prices_on: dict[date, dict[int, tuple[date, Decimal | None, str]]]) -> None:
        anchor = prices_on[item.as_of].get(item.asset_id)
        # Native: the anchor's currency, and a day priced in another one is not comparable. Target: each day converted.
        self.currency = item.target_currency or (anchor[2] if anchor is not None else None)
        self.values: dict[date, Decimal | None] = dict.fromkeys(days)
        self.errors: list[str] = []
        self.conversions: list[tuple[date, Currency]] = []
        for day in days:
            price = prices_on[day].get(item.asset_id)
            if self.currency is None or price is None or price[1] is None:
                continue
            if price[2] == self.currency:
                self.values[day] = price[1]
            elif item.target_currency is None:
                self.errors.append(f"Price of {price[0]} is in {price[2]}, not {self.currency}")
            else:
                self.conversions.append((day, Currency(code=price[2], amount=price[1])))


async def get_period_changes_bulk(items: Sequence[FAPeriodChangesQueryItem], session: AsyncSession) -> list[FAPeriodChangesResult]:
    """The fixed-period changes of every requested asset, in request order."""
    if not items:
        return []
    asset_ids = sorted({item.asset_id for item in items})
    days_of = [fixed_period_dates(item.as_of) for item in items]
    prices_on = {day: await _last_prices_on_or_before(session, asset_ids, day) for day in sorted({day for days in days_of for day in days})}
    valuations = [_Valuation(item, days, prices_on) for item, days in zip(items, days_of, strict=True)]

    pending = [(valuation, day, amount) for valuation in valuations for day, amount in valuation.conversions]
    if pending:
        converted, _messages = await convert_bulk(session, [(amount, valuation.currency, day) for valuation, day, amount in pending], raise_on_error=False)
        for (valuation, day, amount), result in zip(pending, converted, strict=True):
            if result is None:
                valuation.errors.append(f"No {amount.code}/{valuation.currency} rate on or before {day}")
            else:
                valuation.values[day] = result[0].amount

    return [
        FAPeriodChangesResult(
            asset_id=item.asset_id,
            as_of=item.as_of,
            currency=valuation.currency,
            periods=[FAPeriodChange(key=change.key, days=change.days, change_ratio=change.change_ratio) for change in fixed_period_changes(valuation.values, item.as_of)],
            errors=_capped(valuation.errors),
        )
        for item, valuation in zip(items, valuations, strict=True)
    ]

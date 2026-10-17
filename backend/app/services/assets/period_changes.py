"""Fixed-period changes of asset prices: the Δ columns of the Assets table (MF-P2, developer decision D-MF6 b).

The price of an asset on a day is the last stored price on or before it — the backward fill of the price history
(``PriceQueryOperations._build_backward_filled_series``) — and, with a target currency, that price converted at that
day's rate, as the price query converts each day of its series. The change itself is the house's
(``financial_math.returns.fixed_period_changes``); this module only values the days it names.

Reads the stored history directly, so a long period has its change whatever range the page has loaded: one grouped
query per valued day for every asset of the request, never a series per asset.

With a ``range_start`` (X-R59) it also values the change over the whole range the page shows, the house's
``range_change``: from the price on ``range_start`` — or, for an asset with none on or before it, its first price inside
the range (one more grouped query), the first point of the page's series — to the price on ``as_of``.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import PriceHistory
from backend.app.schemas.common import Currency
from backend.app.schemas.prices import FACurrentPriceItem, FAPeriodChange, FAPeriodChangesQueryItem, FAPeriodChangesResult, FARangeChange
from backend.app.services.financial_math.returns import fixed_period_changes, fixed_period_dates, range_change
from backend.app.services.fx.conversion import convert_bulk

_MAX_ERRORS = 10


async def _last_prices_on_or_before(session: AsyncSession, asset_ids: Sequence[int], day: date) -> dict[int, tuple[date, Decimal | None, str]]:
    """Each asset's last stored price on or before ``day``: (its date, close, currency)."""
    latest = select(PriceHistory.asset_id, func.max(PriceHistory.date).label("latest")).where(and_(PriceHistory.asset_id.in_(asset_ids), PriceHistory.date <= day)).group_by(PriceHistory.asset_id).subquery()
    rows = await session.execute(select(PriceHistory.asset_id, PriceHistory.date, PriceHistory.close, PriceHistory.currency).join(latest, and_(PriceHistory.asset_id == latest.c.asset_id, PriceHistory.date == latest.c.latest)))
    return {asset_id: (price_date, close, currency) for asset_id, price_date, close, currency in rows.all()}


async def _first_prices_inside(session: AsyncSession, asset_ids: Sequence[int], after: date, until: date) -> dict[int, tuple[date, Decimal | None, str]]:
    """Each asset's first stored price after ``after`` and on or before ``until``: (its date, close, currency)."""
    first = select(PriceHistory.asset_id, func.min(PriceHistory.date).label("first")).where(and_(PriceHistory.asset_id.in_(asset_ids), PriceHistory.date > after, PriceHistory.date <= until)).group_by(PriceHistory.asset_id).subquery()
    rows = await session.execute(select(PriceHistory.asset_id, PriceHistory.date, PriceHistory.close, PriceHistory.currency).join(first, and_(PriceHistory.asset_id == first.c.asset_id, PriceHistory.date == first.c.first)))
    return {asset_id: (price_date, close, currency) for asset_id, price_date, close, currency in rows.all()}


def _capped(errors: list[str]) -> list[str]:
    unique = list(dict.fromkeys(errors))
    if len(unique) > _MAX_ERRORS:
        return unique[:_MAX_ERRORS] + [f"… and {len(unique) - _MAX_ERRORS} more"]
    return unique


class _Valuation:
    """One asset's prices on the valued days, in one currency, with the conversions they still need.

    With a ``range_start`` (X-R59) one more day is valued: the reference of the whole-range change — ``range_start`` when
    a price is on or before it, else the day of the first price inside the range, the first point the page's series has.
    """

    def __init__(
        self,
        item: FAPeriodChangesQueryItem,
        days: Sequence[date],
        prices_on: dict[date, dict[int, tuple[date, Decimal | None, str]]],
        first_inside: dict[tuple[date, date], dict[int, tuple[date, Decimal | None, str]]],
    ) -> None:
        anchor = prices_on[item.as_of].get(item.asset_id)
        # Native: the anchor's currency, and a day priced in another one is not comparable. Target: each day converted.
        self.currency = item.target_currency or (anchor[2] if anchor is not None else None)
        priced: dict[date, tuple[date, Decimal | None, str] | None] = {day: prices_on[day].get(item.asset_id) for day in days}
        self.reference_date: date | None = None
        if item.range_start is not None:
            on_start = prices_on[item.range_start].get(item.asset_id)
            inside = first_inside.get((item.range_start, item.as_of), {}).get(item.asset_id)
            if on_start is not None:
                self.reference_date, priced[item.range_start] = item.range_start, on_start
            elif inside is not None:
                self.reference_date, priced[inside[0]] = inside[0], inside
        self.values: dict[date, Decimal | None] = dict.fromkeys(priced)
        self.errors: list[str] = []
        self.conversions: list[tuple[date, Currency]] = []
        for day, price in priced.items():
            if self.currency is None or price is None or price[1] is None:
                continue
            if price[2] == self.currency:
                self.values[day] = price[1]
            elif item.target_currency is None:
                self.errors.append(f"Price of {price[0]} is in {price[2]}, not {self.currency}")
            else:
                self.conversions.append((day, Currency(code=price[2], amount=price[1])))

    def range_change(self, item: FAPeriodChangesQueryItem) -> FARangeChange | None:
        """The whole-range change of the item (the house's ``range_change``); None when it asked none."""
        if item.range_start is None:
            return None
        if self.reference_date is None:
            return FARangeChange()
        change = range_change(self.values.get(self.reference_date), self.values.get(item.as_of))
        return FARangeChange(reference_date=self.reference_date, change_abs=change.change_abs, change_ratio=change.change_ratio)


async def get_period_changes_bulk(items: Sequence[FAPeriodChangesQueryItem], session: AsyncSession) -> list[FAPeriodChangesResult]:
    """The fixed-period changes of every requested asset, in request order, and its whole-range change when asked."""
    if not items:
        return []
    asset_ids = sorted({item.asset_id for item in items})
    days_of = [fixed_period_dates(item.as_of) for item in items]
    range_days = {item.range_start for item in items if item.range_start is not None}
    prices_on = {day: await _last_prices_on_or_before(session, asset_ids, day) for day in sorted({day for days in days_of for day in days} | range_days)}
    # X-R59: a range with no price on or before its first day starts at the first price inside it, as the series does.
    first_inside: dict[tuple[date, date], dict[int, tuple[date, Decimal | None, str]]] = {}
    for start, as_of in sorted({(item.range_start, item.as_of) for item in items if item.range_start is not None}):
        without = sorted({item.asset_id for item in items if (item.range_start, item.as_of) == (start, as_of) and item.asset_id not in prices_on[start]})
        if without:
            first_inside[(start, as_of)] = await _first_prices_inside(session, without, start, as_of)
    valuations = [_Valuation(item, days, prices_on, first_inside) for item, days in zip(items, days_of, strict=True)]

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
            range_change=valuation.range_change(item),
            errors=_capped(valuation.errors),
        )
        for item, valuation in zip(items, valuations, strict=True)
    ]


async def live_range_changes(session: AsyncSession, live: Sequence[FACurrentPriceItem], range_start: date) -> dict[int, FARangeChange]:
    """The whole-range change from ``range_start`` to each asset's current price (X-R59, ``POST /prices/current``).

    When the range ends today the asset page shows the live quote, which may not be stored: the anchor is that price,
    in its own currency. The reference is the period changes' (``_Valuation``): the price on ``range_start``, or the first
    one inside ``(range_start, the price's day]`` when none is on or before it; one in another currency gives no change.
    The formula is the house's ``range_change``.
    """
    priced = [item for item in live if item.value is not None and item.currency and item.as_of_date is not None and item.as_of_date >= range_start]
    if not priced:
        return {}
    asset_ids = sorted({item.asset_id for item in priced})
    on_start = await _last_prices_on_or_before(session, asset_ids, range_start)
    without = [asset_id for asset_id in asset_ids if asset_id not in on_start]
    inside = await _first_prices_inside(session, without, range_start, max(item.as_of_date for item in priced)) if without else {}
    changes: dict[int, FARangeChange] = {}
    for item in priced:
        if item.asset_id in on_start:
            reference_date, price = range_start, on_start[item.asset_id]
        elif item.asset_id in inside and inside[item.asset_id][0] <= item.as_of_date:
            reference_date, price = inside[item.asset_id][0], inside[item.asset_id]
        else:
            changes[item.asset_id] = FARangeChange()
            continue
        reference = price[1] if price[2] == item.currency else None
        change = range_change(reference, item.value)
        changes[item.asset_id] = FARangeChange(reference_date=reference_date, change_abs=change.change_abs, change_ratio=change.change_ratio)
    return changes

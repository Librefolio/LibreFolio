"""A price series read by observation, converted only where something changes (X-Q1, X-Q2).

The public series of ``POST /assets/prices/query`` is one point for every calendar day: the last stored row on or before the
day (``_fill_point``), and, with a target currency, converted at the rate of that day. Built a day at a time that is a
point and a conversion for every day of the load range, though the row changes on the days a price is stored and the rate
on the days a rate is stored (``fx.conversion.unit_rate_steps``). This module resolves each day to its stored row and to
the rate row it is converted under — two lookups, no conversion — and converts each **pair of rows once**, with the same
``convert_bulk`` the day-by-day pass called: so every value, to the digit, is the one the per-day pass gave, and the
conversions are one for each stretch of days on which both rows are the same.

What a day's point is, said once (``_point``):
- no target, or a row already in the target: the row filled to the day (``_fill_point``);
- a rate row exists: the row's values converted (OHLC scaled by the factor of the close), ``original_*`` the row's own,
  ``backward_fill_info`` the price staleness and ``fx_rate_date`` / ``fx_days_back``;
- no usable rate on or before the day: the row native, its ``backward_fill_info`` carrying the price staleness and no FX;
- a close of 0: left native, as the day-by-day pass left it.

``ObservedPrices`` is the object the risk reads (J, R1): ``first_point_date``, ``observation_dates`` and ``point_on(day)``,
the point the dense series has on that day. It is dense per day and converted per stretch: it holds one ``_Resolved`` (day,
row, conversion) for every calendar day of its range, not one for every observation, and a conversion is shared by the days
of its stretch. Observations are the days a row is stored on (``observation_dates``); nothing here is sparse.

Pure but for the two reads it asks (``unit_rate_steps``, ``convert_bulk``): no signal, no request model.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date as date_type
from datetime import timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import PriceHistory
from backend.app.schemas import FAPricePoint
from backend.app.schemas.common import Currency
from backend.app.schemas.prices import AssetBackwardFillInfo
from backend.app.services.fx import conversion as fx_conversion
from backend.app.services.fx.stretch_conversion import rate_not_found_error

#: How many distinct conversion errors a series keeps (the day-by-day pass capped its list at the same number).
MAX_CONVERSION_ERRORS = 10


@dataclass(frozen=True, slots=True)
class _Conversion:
    """A stored row converted under one rate row: the converted OHLC and the date of the rate row."""

    rate_date: date_type
    open: Decimal | None
    high: Decimal | None
    low: Decimal | None
    close: Decimal


#: What a day's row becomes: None (native: nothing to convert), ``_Conversion``, or ``_FAILED`` (no usable rate).
_FAILED = object()
#: The rate day of a stretch that has no usable rate on or before it (``date.min`` is no date a rate row is stored on).
_NO_RATE_DAY = date_type.min


def point_of(day: date_type, row: PriceHistory, conversion: object, target: str | None) -> FAPricePoint:
    """The point of ``day`` whose last stored row is ``row`` and whose conversion is ``conversion`` (see the module)."""
    if conversion is None:
        return fill_point(row, day)
    days_back = (day - row.date).days
    if conversion is _FAILED:
        return FAPricePoint(
            date=day,
            open=row.open,
            high=row.high,
            low=row.low,
            close=row.close,
            volume=row.volume,
            currency=row.currency,
            source_plugin_key=row.source_plugin_key,
            backward_fill_info=AssetBackwardFillInfo(actual_rate_date=row.date, days_back=days_back, fx_rate_date=None, fx_days_back=None),
        )
    assert isinstance(conversion, _Conversion)
    fx_days_back = (day - conversion.rate_date).days if conversion.rate_date < day else 0
    if days_back:
        backward_fill = AssetBackwardFillInfo(actual_rate_date=row.date, days_back=days_back, fx_rate_date=conversion.rate_date, fx_days_back=fx_days_back)
    elif fx_days_back > 0:
        backward_fill = AssetBackwardFillInfo(actual_rate_date=day, days_back=0, fx_rate_date=conversion.rate_date, fx_days_back=fx_days_back)
    else:
        backward_fill = None
    return FAPricePoint(
        date=day,
        open=conversion.open,
        high=conversion.high,
        low=conversion.low,
        close=conversion.close,
        volume=row.volume,
        currency=target,
        original_currency=row.currency,
        original_close=row.close,
        original_open=row.open,
        original_high=row.high,
        original_low=row.low,
        source_plugin_key=row.source_plugin_key,
        backward_fill_info=backward_fill,
    )


def fill_point(row: PriceHistory, day: date_type) -> FAPricePoint:
    """The fill's point on ``day``, from ``row``, the last stored row on or before it: the row itself when it is stored on
    that day, else its values filled backward, with how far. One rule for the daily fill and the sample (Z-29)."""
    return FAPricePoint(
        date=day,
        open=row.open,
        high=row.high,
        low=row.low,
        close=row.close,
        volume=row.volume,
        currency=row.currency,
        source_plugin_key=row.source_plugin_key,
        backward_fill_info=None if row.date == day else AssetBackwardFillInfo(actual_rate_date=row.date, days_back=(day - row.date).days),
    )


def _converted(row: PriceHistory, amount: Currency, rate_date: date_type) -> _Conversion:
    """``row`` with its close converted to ``amount``: the other values scaled by the same factor."""
    factor = amount.amount / row.close
    return _Conversion(
        rate_date=rate_date,
        open=row.open * factor if row.open is not None else None,
        high=row.high * factor if row.high is not None else None,
        low=row.low * factor if row.low is not None else None,
        close=amount.amount,
    )


@dataclass(frozen=True, slots=True)
class _Resolved:
    """A day, its last stored row and what the row became under the day's rate row."""

    day: date_type
    row: PriceHistory
    conversion: object


async def resolve_days(session: AsyncSession, rows: Sequence[PriceHistory], days: Sequence[date_type], target: str | None) -> tuple[list[_Resolved], list[str]]:  # noqa: C901 — one pass over the days: pick the row, plan the conversions, number the errors in the order of the points
    """Each of ``days`` (ascending) with its last row on or before it (``rows``, ascending; a day before the first row
    has none and is left out) and the row's conversion into ``target``; with the conversion errors, as the day-by-day
    pass wrote them.

    The rate row of a day is the one ``unit_rate_steps`` gives (the same usable rows ``convert_bulk`` reads), so two days
    with the same stored row and the same rate row are converted once, on the first of them.
    """
    row_dates = [row.date for row in rows]
    picked: list[tuple[date_type, PriceHistory]] = []
    cursor = -1
    for day in days:
        while cursor + 1 < len(rows) and row_dates[cursor + 1] <= day:
            cursor += 1
        if cursor >= 0:
            picked.append((day, rows[cursor]))
    if not target or not picked:
        return [_Resolved(day, row, None) for day, row in picked], []

    sources = sorted({row.currency for _day, row in picked if row.currency != target})
    steps = await fx_conversion.unit_rate_steps(session, {(source, target): [(picked[0][0], picked[-1][0])] for source in sources}) if sources else {}

    # Which (row, rate row) pairs are asked, on the first day each was met
    asked: dict[tuple[date_type, date_type], tuple[PriceHistory, date_type]] = {}
    plan: list[tuple[date_type, PriceHistory, tuple[date_type, date_type] | None]] = []
    for day, row in picked:
        if row.currency == target:
            plan.append((day, row, None))
            continue
        rate_day = steps[(row.currency, target)].rate_day_at(day)
        if rate_day is None:
            plan.append((day, row, (row.date, _NO_RATE_DAY)))
        elif not row.close:
            plan.append((day, row, None))
        else:
            key = (row.date, rate_day)
            asked.setdefault(key, (row, day))
            plan.append((day, row, key))

    converted: dict[tuple[date_type, date_type], object] = {}
    errors: list[str] = []
    if asked:
        keys = list(asked)
        results, conversion_errors = await fx_conversion.convert_bulk(session, [(Currency(code=asked[key][0].currency, amount=asked[key][0].close), target, asked[key][1]) for key in keys], raise_on_error=False)
        for key, result in zip(keys, results, strict=True):
            converted[key] = _FAILED if result is None else _converted(asked[key][0], result[0], result[1])
        # ``convert_bulk`` numbers its errors by position in the list asked here (one item for each stretch), not by point: only a
        # failure it raises itself, never the missing-rate error of a day, which is written below by the point's own position.
        errors.extend(conversion_errors)

    resolved: list[_Resolved] = []
    position = 0  # index among the points that ask a conversion: the day-by-day pass numbered its errors by it
    rate_less = 0
    messages: list[str] = []
    for day, row, key in plan:
        if row.currency != target:
            if key is not None and key[1] == _NO_RATE_DAY:
                if len(messages) < MAX_CONVERSION_ERRORS:
                    messages.append(rate_not_found_error(position, row.currency, target, day))
                rate_less += 1
                resolved.append(_Resolved(day, row, _FAILED))
            elif key is None:
                resolved.append(_Resolved(day, row, None))
            else:
                resolved.append(_Resolved(day, row, converted[key]))
            position += 1
        else:
            resolved.append(_Resolved(day, row, None))
    errors = _capped(messages, rate_less, errors)
    return resolved, errors


def _capped(first_messages: list[str], count: int, other: list[str]) -> list[str]:
    """The errors of a series as the day-by-day pass kept them: the distinct ones, the first ``MAX_CONVERSION_ERRORS`` and a
    line saying how many more."""
    errors = list(first_messages)
    for message in other:
        if message not in errors:
            errors.append(message)
            count += 1
    if count > MAX_CONVERSION_ERRORS:
        return errors[:MAX_CONVERSION_ERRORS] + [f"… and {count - MAX_CONVERSION_ERRORS} more FX conversion failures"]
    return errors


async def series_points(session: AsyncSession, rows: Sequence[PriceHistory], days: Sequence[date_type], target: str | None) -> tuple[list[FAPricePoint], list[str]]:
    """The points of ``days`` and the conversion errors (see ``resolve_days``)."""
    resolved, errors = await resolve_days(session, rows, days, target)
    return [point_of(item.day, item.row, item.conversion, target) for item in resolved], errors


@dataclass(frozen=True)
class ObservedPrices:
    """One asset's series over ``start`` … ``end``, as the rows it stands on and what they became (X-Q1).

    ``point_on(day)`` is, for every day from ``first_point_date`` to ``end``, the point the public series has on that day —
    the last row on or before it, converted at the rate of that day, with the same ``backward_fill_info``; None before the
    first point. ``ValueError`` after ``end``: the rows beyond it were not read.
    """

    asset_id: int
    start: date_type
    end: date_type
    target_currency: str | None
    #: The first day the series has a point: the range's start when a row precedes it, else the first row inside; None for none.
    first_point_date: date_type | None
    #: The days a stored row is on, inside the range, in order.
    observation_dates: tuple[date_type, ...]
    #: The currency of the first point before conversion (a risk signal's target when none is asked), None for none.
    native_currency: str | None
    #: The conversion errors of the series, as the price query reports them.
    errors: tuple[str, ...]
    _days: tuple[_Resolved, ...]

    def point_on(self, day: date_type) -> FAPricePoint | None:
        if day > self.end:
            raise ValueError(f"the series of asset {self.asset_id} was read to {self.end}: nothing is known of {day}")
        if self.first_point_date is None or day < self.first_point_date:
            return None
        item = self._days[(day - self.first_point_date).days]
        return point_of(item.day, item.row, item.conversion, self.target_currency)

    def points(self) -> list[FAPricePoint]:
        """The whole series, one point a day from ``first_point_date`` to ``end``."""
        return [point_of(item.day, item.row, item.conversion, self.target_currency) for item in self._days]


async def observe(session: AsyncSession, asset_id: int, rows: Sequence[PriceHistory], seed: PriceHistory | None, start: date_type, end: date_type, target: str | None) -> ObservedPrices:
    """The series of an asset over ``start`` … ``end``: ``rows`` its stored rows inside the range (any order), ``seed`` the
    last row before ``start`` (None for none). It begins on ``start`` with a seed, on the first row inside the range
    without one (X-R55: nothing is emitted before the first known price)."""
    inside = sorted((row for row in rows if start <= row.date <= end), key=lambda row: row.date)
    ordered = [seed, *inside] if seed is not None else inside
    first = start if seed is not None else (inside[0].date if inside else None)
    if first is None or first > end:
        return ObservedPrices(asset_id=asset_id, start=start, end=end, target_currency=target, first_point_date=None, observation_dates=(), native_currency=None, errors=(), _days=())
    days = [first + timedelta(days=offset) for offset in range((end - first).days + 1)]
    resolved, errors = await resolve_days(session, ordered, days, target)
    return ObservedPrices(
        asset_id=asset_id,
        start=start,
        end=end,
        target_currency=target,
        first_point_date=first,
        observation_dates=tuple(row.date for row in inside),
        native_currency=resolved[0].row.currency if resolved else None,
        errors=tuple(errors),
        _days=tuple(resolved),
    )

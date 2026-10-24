"""X-Q1…Q3 + S1 («formule veloci» of MF): the price query reads a series BY OBSERVATION and converts it only where something
changes, and the public answer stays one point a day.

Why. ``get_prices_bulk`` builds a point for every calendar day of its load range and converts every one of them: a
10-year ETF in USD asked in EUR is 3 650 points and 3 650 conversions, where the price changes on about 2 500 days and the
rate on about 2 500. The cure keeps what the user sees — each point of the public series, to the digit — and changes what
it costs: a conversion for each stretch of days on which the price row and the rate row are the same, and a dense series
only where it is read.

The contract pinned here (``ObservedPrices`` is the object J agreed for R1, 23/10):

1. **Parity.** On every window of the corpus, ``get_prices_bulk`` answers the points, and the conversion errors, the
   HEAD pipeline answers: ``HEAD_dense`` (``_build_backward_filled_series`` as it was at 1fd80c481) then ``HEAD_convert``
   (the conversion pass as it was, one ``convert_bulk`` item for every point whose currency is not the target). Written
   here, a copy, not read from the code under test. Green before the cure by design; it pins the answer.
2. **The count.** The conversions handed to ``convert_bulk`` are one for each stretch of days on which the price row and
   the usable rate row are both the same (a day without a usable rate asks none: the error it would have given is
   written from the plan). Red before the cure: one for every day.
3. **The object.** ``PriceQueryOperations.observed_prices(request, session)`` gives, for one item, an ``ObservedPrices``:
   ``first_point_date`` (the first day the series has a point, None for an empty one), ``observation_dates`` (the days a
   stored row of the series is on, in the item's range) and ``point_on(day)``: **exactly** the point the public series has
   on that day — the last row on or before it, converted at the rate of that day, with the same ``backward_fill_info`` —
   for a day inside or outside the item's range (the base day before the start, the day another asset quotes), None before
   the first point. Red before the cure: it does not exist.
4. **Signals.** ``SignalResult`` of EMA (sessions), the calendar rolling return (calendar days), the drawdown (full
   history) and a comparison are the ones the HEAD pipeline gives on the HEAD series (``HEAD_signals``): the dense series
   the calendar signals read stays dense where they read it, and a session signal reads the days a price was quoted.

Isolation: PURE. A private SQLite file under ``tmp_path``; the market holiday table empty where the price query reads it
(as ``test_price_query_sampling.py`` does); no lane database, no server, no network.
"""

from __future__ import annotations

import dataclasses
import uuid
from collections.abc import AsyncIterator, Sequence
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.db.base import SQLModel
from backend.app.db.models import Asset, AssetType, FxRate, PriceHistory
from backend.app.schemas import SignalCadence, SignalDomain, SignalExecutionContext, SignalPricePoint
from backend.app.schemas.common import Currency, DateRangeModel
from backend.app.schemas.prices import AssetBackwardFillInfo, FAPricePoint, FAPriceQueryItem
from backend.app.services.assets import price_query
from backend.app.services.assets.price_query import RISK_WARMUP_DAY_MULTIPLIER, PriceQueryOperations
from backend.app.services.fx import conversion as fx_conversion
from backend.app.services.fx.conversion import convert_bulk as head_convert_bulk
from backend.app.services.market_series import mark_market_closed_carries, prepare_asset_series_set
from backend.app.services.signals.execution import SignalPreparedSeriesBundle
from backend.app.services.signals.service import SignalService
from backend.app.utils.datetime_utils import EARLIEST_RANGE_START, utcnow

FETCHED_AT = utcnow()

#: The corpus. Prices on weekdays (a close of its own, OHLC around it), rates on other days than the prices.
FIRST = date(2024, 1, 1)
LAST = date(2025, 6, 30)  # a Monday
EASTER = (date(2024, 3, 29), date(2024, 4, 1))
CHRISTMAS = (date(2024, 12, 24), date(2024, 12, 26))
JULY_4 = (date(2024, 7, 4), date(2024, 7, 4))
RATE_GAP = (date(2024, 6, 1), date(2024, 6, 30))  # no EUR/USD rate for a month

IDS = {"eur": 9601, "usd": 9602, "gbp": 9603, "chf": 9604, "zero": 9605, "late": 9606}
#: asset → (first row, gaps, base of its closes, the currency its rows are in)
HISTORIES = {
    "eur": (date(2024, 1, 2), (EASTER, CHRISTMAS), 100, "EUR"),
    "usd": (date(2024, 2, 1), (JULY_4,), 200, "USD"),
    "gbp": (date(2024, 2, 1), (), 300, "GBP"),
    "chf": (date(2025, 1, 1), (), 50, "CHF"),  # no rate at all: nothing converts
    "zero": (date(2024, 2, 1), (), 400, "USD"),  # one row with a close of 0 (the conversion leaves it native)
    "late": (date(2025, 3, 3), (), 70, "EUR"),  # a history shorter than the windows
}
#: EUR/USD on Mondays, Wednesdays and Fridays, a month without; EUR/GBP on every weekday from 1 May 2024
EUR_USD_FIRST = date(2023, 12, 1)
EUR_GBP_FIRST = date(2024, 5, 1)

#: (name, start, end): windows of the load. The end past the last row is carried.
WINDOWS = {
    "all": (date(2024, 1, 1), LAST),
    "mid": (date(2024, 5, 15), date(2024, 9, 15)),
    "one-day": (date(2024, 9, 4), date(2024, 9, 4)),
    "before-history": (date(2023, 6, 1), date(2024, 2, 10)),
    "past-the-last-row": (date(2025, 6, 20), date(2025, 7, 31)),
    "over-the-rate-gap": (date(2024, 5, 20), date(2024, 7, 10)),
    "holiday": (date(2024, 12, 20), date(2025, 1, 6)),
}

#: (asset, target, window): native, direct, inverse, a pair with no rate, rates that start late, a short history, a zero
CASES = [
    ("eur", None, "all"),
    ("eur", "USD", "all"),
    ("eur", "USD", "over-the-rate-gap"),
    ("usd", "EUR", "all"),
    ("usd", "EUR", "mid"),
    ("usd", "EUR", "one-day"),
    ("usd", "EUR", "before-history"),
    ("usd", "EUR", "past-the-last-row"),
    ("usd", "EUR", "over-the-rate-gap"),
    ("usd", "EUR", "holiday"),
    ("gbp", "EUR", "all"),
    ("gbp", "EUR", "mid"),
    ("gbp", "USD", "mid"),
    ("chf", "EUR", "all"),
    ("zero", "EUR", "all"),
    ("late", "USD", "all"),
    ("late", "EUR", "all"),
    ("usd", "USD", "all"),
]


def _weekdays(first: date, last: date, gaps: Sequence[tuple[date, date]] = ()) -> list[date]:
    return [first + timedelta(days=n) for n in range((last - first).days + 1) if (first + timedelta(days=n)).weekday() < 5 and not any(start <= first + timedelta(days=n) <= end for start, end in gaps)]


def _close(asset: str, n: int) -> Decimal:
    """A close of its own with digits after the decimal point that do not survive a different order of operations."""
    base = HISTORIES[asset][2]
    return (Decimal(base) + Decimal(n) / Decimal(7)).quantize(Decimal("0.000001"))


def _price_rows(asset: str) -> list[dict]:
    first, gaps, _base, currency = HISTORIES[asset]
    rows = []
    for n, day in enumerate(_weekdays(first, LAST, gaps)):
        close = Decimal("0") if asset == "zero" and n == 40 else _close(asset, n)
        rows.append({"asset_id": IDS[asset], "date": day, "open": close - 1, "high": close + 2, "low": close - 2, "close": close, "volume": Decimal(1000 + n), "currency": currency, "source_plugin_key": "MANUAL", "fetched_at": FETCHED_AT})
    return rows


def _rate_rows() -> list[dict]:
    rows = []
    usd_days = [day for day in _weekdays(EUR_USD_FIRST, LAST) if day.weekday() in (0, 2, 4) and not RATE_GAP[0] <= day <= RATE_GAP[1]]
    rows.extend({"date": day, "base": "EUR", "quote": "USD", "rate": Decimal("1.05") + Decimal(n % 97) / 1000, "source": "ECB", "fetched_at": FETCHED_AT} for n, day in enumerate(usd_days))
    rows.extend({"date": day, "base": "EUR", "quote": "GBP", "rate": Decimal("0.85") + Decimal(n % 89) / 1000, "source": "ECB", "fetched_at": FETCHED_AT} for n, day in enumerate(_weekdays(EUR_GBP_FIRST, LAST)))
    return rows


@dataclasses.dataclass(frozen=True)
class _World:
    engine: AsyncEngine

    def item(self, asset: str, window: str, target: str | None = None, **extra: Any) -> FAPriceQueryItem:
        start, end = WINDOWS[window]
        return FAPriceQueryItem(asset_id=IDS[asset], date_range=DateRangeModel(start=start, end=end), target_currency=target, **extra)


@pytest_asyncio.fixture
async def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[_World]:
    """A private SQLite file with the six assets of ``HISTORIES`` and the rates of the corpus; the market holiday table
    empty where the price query reads it, as the sampling tests do."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'price_query_observations.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(engine, expire_on_commit=False) as session:
            session.add_all([Asset(id=IDS[name], display_name=f"X-Q1 {name} {uuid.uuid4().hex[:8]}", currency=HISTORIES[name][3], asset_type=AssetType.STOCK) for name in IDS])
            await session.flush()
            for name in IDS:
                await session.execute(insert(PriceHistory), _price_rows(name))
            await session.execute(insert(FxRate), _rate_rows())
            await session.commit()

        async def _no_market_holidays() -> frozenset[date]:
            return frozenset()

        monkeypatch.setattr(price_query, "ensure_market_holidays", _no_market_holidays)
        yield _World(engine)
    finally:
        await engine.dispose()


async def _rows(world: _World, asset: str) -> dict[date, PriceHistory]:
    async with AsyncSession(world.engine, expire_on_commit=False) as session:
        found = (await session.execute(select(PriceHistory).where(PriceHistory.asset_id == IDS[asset]).order_by(PriceHistory.date))).scalars().all()
    return {row.date: row for row in found}


# =============================================================================
# THE HEAD PIPELINE (1fd80c481), COPIED: what the public answer is measured against
# =============================================================================


def head_dense(price_map: dict[date, PriceHistory], start: date, end: date, seed: PriceHistory | None) -> list[FAPricePoint]:
    """``_build_backward_filled_series`` at 1fd80c481: a point for every calendar day from the start (or the first price)."""
    results: list[FAPricePoint] = []
    last_known = seed
    current = start
    if seed is None:
        if not price_map:
            return results
        current = max(start, min(price_map))
    while current <= end:
        ph = price_map.get(current)
        if ph:
            last_known = ph
        if last_known:
            results.append(
                FAPricePoint(
                    date=current,
                    open=last_known.open,
                    high=last_known.high,
                    low=last_known.low,
                    close=last_known.close,
                    volume=last_known.volume,
                    currency=last_known.currency,
                    source_plugin_key=last_known.source_plugin_key,
                    backward_fill_info=None if last_known.date == current else AssetBackwardFillInfo(actual_rate_date=last_known.date, days_back=(current - last_known.date).days),
                )
            )
        current += timedelta(days=1)
    return results


async def head_convert(session: AsyncSession, prices: list[FAPricePoint], target: str | None) -> tuple[list[FAPricePoint], list[str]]:  # noqa: C901 — a copy of the pass at 1fd80c481, as it was
    """The conversion pass at 1fd80c481, one ``convert_bulk`` item for every point whose currency is not the target."""
    errors: list[str] = []
    prices = list(prices)
    if not target or not prices:
        return prices, errors
    conversions = []
    indices = []
    for i, p in enumerate(prices):
        if p.currency == target:
            continue
        conversions.append((Currency(code=p.currency, amount=p.close), target, p.date))
        indices.append(i)
    if not conversions:
        return prices, errors
    converted, conv_errors = await head_convert_bulk(session, conversions, raise_on_error=False)
    if conv_errors:
        seen: set[str] = set()
        deduped = []
        for err in conv_errors:
            if err not in seen:
                seen.add(err)
                deduped.append(err)
        if len(deduped) > 10:
            deduped = deduped[:10] + [f"… and {len(deduped) - 10} more FX conversion failures"]
        errors.extend(deduped)
    conv_idx = 0
    for pi in indices:
        conv_result = converted[conv_idx]
        original = prices[pi]
        if conv_result is None:
            old_bfi = original.backward_fill_info
            prices[pi] = FAPricePoint(
                date=original.date,
                open=original.open,
                high=original.high,
                low=original.low,
                close=original.close,
                volume=original.volume,
                currency=original.currency,
                original_currency=original.original_currency,
                original_close=original.original_close,
                original_open=original.original_open,
                original_high=original.original_high,
                original_low=original.original_low,
                source_plugin_key=original.source_plugin_key,
                backward_fill_info=AssetBackwardFillInfo(actual_rate_date=old_bfi.actual_rate_date if old_bfi else original.date, days_back=old_bfi.days_back if old_bfi else 0, fx_rate_date=None, fx_days_back=None),
            )
            conv_idx += 1
            continue
        converted_currency, rate_date, _applied = conv_result
        original_close = original.close
        if original_close and original_close != 0:
            fx_factor = converted_currency.amount / original_close
        else:
            conv_idx += 1
            continue
        fx_days_back = (original.date - rate_date).days if rate_date < original.date else 0
        old_bfi = original.backward_fill_info
        if old_bfi:
            new_bfi = AssetBackwardFillInfo(actual_rate_date=old_bfi.actual_rate_date, days_back=old_bfi.days_back, fx_rate_date=rate_date, fx_days_back=fx_days_back)
        elif fx_days_back > 0:
            new_bfi = AssetBackwardFillInfo(actual_rate_date=original.date, days_back=0, fx_rate_date=rate_date, fx_days_back=fx_days_back)
        else:
            new_bfi = None
        prices[pi] = FAPricePoint(
            date=original.date,
            open=original.open * fx_factor if original.open is not None else None,
            high=original.high * fx_factor if original.high is not None else None,
            low=original.low * fx_factor if original.low is not None else None,
            close=converted_currency.amount,
            volume=original.volume,
            currency=target,
            original_currency=original.currency,
            original_close=original_close,
            original_open=original.open,
            original_high=original.high,
            original_low=original.low,
            source_plugin_key=original.source_plugin_key,
            backward_fill_info=new_bfi,
        )
        conv_idx += 1
    return prices, errors


async def head_series(world: _World, asset: str, window: str, target: str | None, *, load_start: date | None = None) -> tuple[list[FAPricePoint], list[str]]:
    """The series of an item without signals at 1fd80c481, from the load start to the end, and its conversion errors."""
    start, end = WINDOWS[window]
    start = load_start or start
    rows = await _rows(world, asset)
    seed = max((row for day, row in rows.items() if day < start), key=lambda row: row.date, default=None)
    window_rows = {day: row for day, row in rows.items() if start <= day <= end}
    async with AsyncSession(world.engine, expire_on_commit=False) as session:
        return await head_convert(session, head_dense(window_rows, start, end, seed), target)


def _dump(points: Sequence[FAPricePoint]) -> list[dict]:
    return [point.model_dump(mode="json") for point in points]


async def _query(world: _World, *items: FAPriceQueryItem):
    async with AsyncSession(world.engine, expire_on_commit=False) as session:
        return await PriceQueryOperations.get_prices_bulk(list(items), session)


# =============================================================================
# OQ-01…03 — PARITY: the public series is what it was
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(("asset", "target", "window"), CASES, ids=[f"{asset}-{target or 'native'}-{window}" for asset, target, window in CASES])
async def test_oq01_the_public_series_and_its_conversion_errors_are_the_head_pipelines(world, asset, target, window):
    """OQ-01: for an item without signals, the points of ``get_prices_bulk`` — date, OHLC, ``original_*``, currency,
    ``backward_fill_info`` with its ``fx_rate_date`` and ``fx_days_back`` — and its ``errors`` are what HEAD's dense fill
    and per-day conversion give, to the digit: native, direct and inverse pairs, a pair with no rate, rates that start
    after the prices, a window before the history, past the last row, over a month without a rate, a one-day window,
    a short history, a close of 0.

    Green before the cure by design: it pins the answer the cure must keep.
    """
    expected, expected_errors = await head_series(world, asset, window, target)
    (result,) = await _query(world, world.item(asset, window, target))

    assert _dump(result.prices) == _dump(expected), f"{asset} → {target} over {window}: the series differs"
    assert result.errors == expected_errors, f"{asset} → {target} over {window}: the errors differ"


@pytest.mark.asyncio
async def test_oq02_several_items_of_one_request_are_each_their_own_series(world):
    """OQ-02: items of one request for the same asset with other targets and windows, and a comparison between the
    stretches of conversions of different items, are each what they would be alone (the cure groups days by price row
    and rate row: it must not mix two items' rows).

    Green before the cure by design.
    """
    items = [world.item("usd", "mid", "EUR"), world.item("usd", "all", "EUR"), world.item("gbp", "mid", "EUR"), world.item("eur", "mid", "USD"), world.item("usd", "mid")]
    answered = await _query(world, *items)
    for item, result, (asset, window, target) in zip(items, answered, [("usd", "mid", "EUR"), ("usd", "all", "EUR"), ("gbp", "mid", "EUR"), ("eur", "mid", "USD"), ("usd", "mid", None)], strict=True):
        expected, expected_errors = await head_series(world, asset, window, target)
        assert (_dump(result.prices), result.errors) == (_dump(expected), expected_errors), f"{asset} → {target} over {window}"
        assert result.asset_id == item.asset_id


@pytest.mark.asyncio
async def test_oq03_a_stored_weekend_row_and_a_row_on_a_rate_day_are_still_stored_points(world):
    """OQ-03: where a stored row falls on a day the rate is stored too, and where it falls on a day it is not, the point
    keeps ``backward_fill_info`` None or the FX staleness alone, as the HEAD pipeline writes them — the quote evidence
    ``derive_signal_source_capability`` and the sessions of the signals read.

    Green before the cure by design.
    """
    expected, _ = await head_series(world, "usd", "mid", "EUR")
    (result,) = await _query(world, world.item("usd", "mid", "EUR"))
    by_day = {point.date: point for point in result.prices}
    stored_days = (await _rows(world, "usd")).keys()
    kinds = {(day in stored_days, by_day[day].backward_fill_info is None) for day in by_day}
    # the corpus holds every kind: a stored point with no staleness, a stored point on a day the rate is carried, a carried price
    assert (True, True) in kinds and (True, False) in kinds and (False, False) in kinds, kinds
    assert _dump(result.prices) == _dump(expected)


# =============================================================================
# OQ-04 — THE COUNT: a conversion for each stretch, not for each day
# =============================================================================


def _expected_conversions(asset: str, window: str, target: str) -> int:
    """How many conversions a series needs: the stretches of days on which the price row and the usable rate row are both
    the same, from the day the pair has a rate. Walked here, a day at a time, from the stored rows."""
    first, gaps, _base, currency = HISTORIES[asset]
    start, end = WINDOWS[window]
    price_days = _weekdays(first, LAST, gaps)
    rate_days = sorted({row["date"] for row in _rate_rows() if {row["base"], row["quote"]} == {currency, target}})
    stretches = set()
    seeded = any(d < start for d in price_days)
    day = start if seeded else min((d for d in price_days if d >= start), default=None)
    if day is None:
        return 0
    while day <= end:
        price_day = max((d for d in price_days if d <= day), default=None)
        rate_day = max((d for d in rate_days if d <= day), default=None)
        if price_day is not None and rate_day is not None:
            stretches.add((price_day, rate_day))
        day += timedelta(days=1)
    return len(stretches)


@pytest.mark.asyncio
@pytest.mark.parametrize(("asset", "target", "window"), [("usd", "EUR", "all"), ("usd", "EUR", "mid"), ("gbp", "EUR", "all"), ("eur", "USD", "all"), ("usd", "EUR", "over-the-rate-gap")], ids=lambda case: str(case))
async def test_oq04_the_conversions_asked_are_the_stretches_of_unchanged_price_and_rate_not_the_days(world, monkeypatch, asset, target, window):
    """OQ-04: ``convert_bulk`` is handed one item for each stretch of days on which both the price row and the rate row
    are the same — the 10-year example of the brief: about 2 500 observations plus the days the rate changes, not 3 650 days
    — and the answer is still the HEAD pipeline's (OQ-01).

    Red before the cure: it is handed one item for every day of the series.
    """
    handed: list[int] = []

    async def _counting(session, conversions, raise_on_error=True):
        handed.append(len(conversions))
        return await head_convert_bulk(session, conversions, raise_on_error=raise_on_error)

    monkeypatch.setattr(fx_conversion, "convert_bulk", _counting)
    (result,) = await _query(world, world.item(asset, window, target))
    expected = _expected_conversions(asset, window, target)

    assert len(result.prices) > expected > 0, f"premise: the series has {len(result.prices)} days for {expected} stretches: weekends and rate-less days make the stretches fewer"
    assert sum(handed) == expected, f"{sum(handed)} conversions asked for a series of {len(result.prices)} days, expected {expected} (one for each stretch)"


# =============================================================================
# OQ-05 — THE OBJECT J READS
# =============================================================================


def _observed():
    found = getattr(PriceQueryOperations, "observed_prices", None)
    if found is None:
        pytest.fail("X-Q1: PriceQueryOperations.observed_prices(request, session) is missing — ObservedPrices: first_point_date, observation_dates, point_on(day)")
    return found


async def _observed_of(world: _World, item: FAPriceQueryItem):
    async with AsyncSession(world.engine, expire_on_commit=False) as session:
        return await _observed()(item, session)


@pytest.mark.asyncio
@pytest.mark.parametrize(("asset", "target", "window"), [("usd", "EUR", "mid"), ("gbp", "EUR", "all"), ("eur", None, "all"), ("late", "USD", "all"), ("chf", "EUR", "all")], ids=lambda case: str(case))
async def test_oq05_point_on_is_the_point_the_public_series_has_on_that_day(world, asset, target, window):
    """OQ-05: ``point_on(day)`` is, for every day of the item's range, the point of the public series — to the digit, with
    its ``backward_fill_info`` — and ``first_point_date`` is the date of the series' first point; ``observation_dates`` are
    the days a stored row of the series is on, in the item's range.

    Red before the cure: ``observed_prices`` does not exist.
    """
    item = world.item(asset, window, target)
    observed = await _observed_of(world, item)
    (result,) = await _query(world, item)

    assert observed.first_point_date == (result.prices[0].date if result.prices else None)
    for point in result.prices:
        assert observed.point_on(point.date).model_dump(mode="json") == point.model_dump(mode="json"), f"{asset} → {target}, {point.date}"
    start, end = WINDOWS[window]
    stored = (await _rows(world, asset)).keys()
    assert list(observed.observation_dates) == sorted(day for day in stored if start <= day <= end)


@pytest.mark.asyncio
async def test_oq05_point_on_before_the_first_point_is_none_and_after_the_range_is_refused(world):
    """OQ-05: J asks a day outside the item's range. The range's end is the last day read: a later day raises ``ValueError``
    (nothing is known of it); a day before the first point is None; the base day — the one before the start, with a row
    before it — is the seed's point at that day's rate: what the series of an item that starts a day earlier has there.

    Red before the cure: ``observed_prices`` does not exist.
    """
    item = world.item("usd", "mid", "EUR")
    observed = await _observed_of(world, item)
    start, end = WINDOWS["mid"]
    with pytest.raises(ValueError):
        observed.point_on(end + timedelta(days=1))
    assert observed.point_on(observed.first_point_date - timedelta(days=1)) is None

    earlier = FAPriceQueryItem(asset_id=IDS["usd"], date_range=DateRangeModel(start=start - timedelta(days=1), end=end), target_currency="EUR")
    (result,) = await _query(world, earlier)
    assert result.prices[0].date == start - timedelta(days=1)
    assert (await _observed_of(world, earlier)).point_on(start - timedelta(days=1)).model_dump(mode="json") == result.prices[0].model_dump(mode="json")


# =============================================================================
# OQ-06 — THE SIGNALS: the results HEAD gives on HEAD's series
# =============================================================================

EMA5 = {"instance_id": "ema5", "signal_code": "EMA", "params": {"period": 5}}
RETURN7 = {"instance_id": "return7", "signal_code": "ASSET_CALENDAR_ROLLING_RETURN", "params": {"window_days": 7}}
DRAWDOWN = {"instance_id": "drawdown", "signal_code": "RISK_DRAWDOWN", "params": {"full_history": True}}
SIGNAL_SETS = {"ema": [EMA5], "return": [RETURN7], "drawdown": [DRAWDOWN], "all-three": [EMA5, RETURN7, DRAWDOWN]}


def _without_clock(dumped: Any) -> Any:
    """A dump without its ``computed_at``: a risk signal says when it was computed."""
    if isinstance(dumped, dict):
        return {key: _without_clock(value) for key, value in dumped.items() if key != "computed_at"}
    if isinstance(dumped, list):
        return [_without_clock(value) for value in dumped]
    return dumped


async def head_signals(world: _World, item: FAPriceQueryItem) -> tuple[list[FAPricePoint], list]:
    """The signal pipeline of ``get_prices_bulk`` at 1fd80c481 for one item with signals and no comparison asset: the load
    range from the plan's warm-up, HEAD's dense fill and conversion, the prepared series of a risk signal, the neutral
    prices with the market-closed carries marked, ``SignalService.execute``, then the cut to the range. Returns the cut
    points and the results."""
    start, end = item.date_range.start, item.date_range.end or item.date_range.start
    service = SignalService()
    context = SignalExecutionContext(domain=SignalDomain.ASSET, requested_range=item.date_range, cadence=SignalCadence.DAILY, source_reference=f"asset:{item.asset_id}", target_currency=item.target_currency)
    plan = service.prepare_plan(item.signals, context, item.annotation_requests)
    warmup_days = max(plan.max_history_days_before_visible, plan.max_prepared_history_points_before_visible * RISK_WARMUP_DAY_MULTIPLIER)
    if plan.requires_full_history:
        warmup_days = max(warmup_days, (start - EARLIEST_RANGE_START).days)
    warmup_days = min(warmup_days, (start - date.min).days)
    load_start = start - timedelta(days=warmup_days)
    asset = next(name for name, asset_id in IDS.items() if asset_id == item.asset_id)
    rows = await _rows(world, asset)
    seed = max((row for day, row in rows.items() if day < load_start), key=lambda row: row.date, default=None)
    async with AsyncSession(world.engine, expire_on_commit=False) as session:
        points, _errors = await head_convert(session, head_dense({day: row for day, row in rows.items() if load_start <= day <= end}, load_start, end, seed), item.target_currency)
    result = price_query.FAPriceQueryResult(asset_id=item.asset_id, prices=points)
    target = item.target_currency or next((point.currency for point in points if point.currency is not None), None)
    bundle = None
    if plan.requires_prepared_asset_series and target is not None:
        prepared_range = DateRangeModel(start=load_start, end=end)
        primary_set = prepare_asset_series_set([result], requested_range=prepared_range, target_currency=target, market_holidays=frozenset())
        bundle = SignalPreparedSeriesBundle(primary_asset_id=item.asset_id, series_sets={None: primary_set})
    price_currencies = {point.currency for point in points if point.currency}
    coherent = len(price_currencies) <= 1 and (not item.target_currency or not price_currencies or price_currencies == {item.target_currency})
    usable = points if coherent else [point for point in points if item.target_currency and point.currency == item.target_currency]
    usable = list(mark_market_closed_carries({point.date: point for point in usable}, frozenset()).values())
    neutral = [SignalPricePoint(date=p.date, open=p.open, high=p.high, low=p.low, close=p.close, volume=p.volume, backward_fill_info=p.backward_fill_info) for p in usable]
    results = await service.execute(plan, neutral, [], events_loaded=False, prepared_series_bundle=bundle, source_capability=PriceQueryOperations.derive_signal_source_capability(points))
    return [point for point in points if start <= point.date <= end], results


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("asset", "target", "window", "signals"),
    [("usd", "EUR", "mid", "all-three"), ("usd", "EUR", "all", "all-three"), ("eur", None, "mid", "all-three"), ("gbp", "EUR", "mid", "ema"), ("usd", "EUR", "holiday", "return"), ("late", "USD", "all", "drawdown"), ("eur", None, "one-day", "ema")],
    ids=lambda case: str(case),
)
async def test_oq06_the_signal_results_and_the_visible_points_are_the_head_pipelines(world, asset, target, window, signals):
    """OQ-06: an item with EMA (sessions), the calendar rolling return (calendar days) and the full-history drawdown
    answers, for its visible range, the points and the ``SignalResult`` of HEAD's pipeline — warm-up, conversion, market
    closed carries, prepared series — through the single, the pair and the three together: native, converted, a short
    history, a holiday week, one day.

    Green before the cure by design: it pins what the cure may not change.
    """
    item = world.item(asset, window, target, signals=SIGNAL_SETS[signals])
    expected_points, expected_results = await head_signals(world, item)
    (result,) = await _query(world, item)

    assert _dump(result.prices) == _dump(expected_points), "the visible points differ"
    assert [_without_clock(r.model_dump(mode="json")) for r in result.signals] == [_without_clock(r.model_dump(mode="json")) for r in expected_results], f"{signals}: the signal results differ"
    assert any(r.status.value in ("ok", "partial") and r.series for r in result.signals), f"premise: some signal computed ({[r.status.value for r in result.signals]})"

"""X-Q3 («formule veloci» of MF): ``POST /fx/currencies/convert`` converts once for each stretch of days on which the rate row is
the same, and the answer stays one result a day.

Why. The handler expands a range into one ``convert_bulk`` item for every day (twice with signals: the visible days and the
signal block with its warm-up): a 10-year EUR→USD range is 3 650 items, though the rate changes on about 250 days a year.
``services/fx/stretch_conversion.py`` asks ``convert_bulk`` one conversion for each distinct (amount, pair, rate row) and
copies the answer to the other days of the stretch.

The contract pinned here:

1. **Parity of the function.** ``convert_by_stretch(session, conversions)`` answers, item for item, what
   ``convert_bulk(session, conversions, raise_on_error=False)`` answers — the amount to the digit and the exponent, the rate
   date, the backward-fill flag, ``None`` and the error text of an item with no usable rate — on direct, inverse, identity
   and rate-less pairs, a rate gap, days before the first rate, and amounts that print differently (``1`` and ``1.0``, a
   zero). The reference is ``convert_bulk`` itself, called with every item.
2. **The count.** ``convert`` is handed one item for each distinct (amount, pair, rate row), not one for each day.
   Red before the cure: ``convert_by_stretch`` did not exist, and the handler handed ``convert_bulk`` every day.
3. **Parity of the handler.** ``convert_currency_bulk`` answers what it answered with every day converted: results,
   errors, signal results and samples. The reference is the same handler with ``convert_by_stretch`` replaced by a call to
   ``convert_bulk``.

Isolation: PURE. A private SQLite file under ``tmp_path``; no lane database, no server, no network.
"""

from __future__ import annotations

import dataclasses
from collections.abc import AsyncIterator
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.api.v1.fx import currencies
from backend.app.db.base import SQLModel
from backend.app.db.models import FxRate
from backend.app.schemas import SignalRequest
from backend.app.schemas.common import Currency, DateRangeModel
from backend.app.schemas.fx import FXConversionRequest
from backend.app.services.fx.conversion import convert_bulk
from backend.app.services.fx.stretch_conversion import convert_by_stretch
from backend.app.utils.datetime_utils import utcnow

FETCHED_AT = utcnow()
FIRST = date(2024, 1, 1)
LAST = date(2025, 6, 30)
RATE_GAP = (date(2024, 6, 1), date(2024, 6, 30))  # no EUR/USD rate for a month
EUR_USD_FIRST = date(2023, 12, 1)
EUR_GBP_FIRST = date(2024, 5, 1)  # EUR/GBP starts late: the days before it have no rate
SMA3 = SignalRequest(instance_id="sma3", signal_code="SMA", params={"period": 3})


def _days(first: date, last: date) -> list[date]:
    return [first + timedelta(days=n) for n in range((last - first).days + 1)]


def _rate_rows() -> list[dict]:
    usd = [day for day in _days(EUR_USD_FIRST, LAST) if day.weekday() in (0, 2, 4) and not RATE_GAP[0] <= day <= RATE_GAP[1]]
    gbp = [day for day in _days(EUR_GBP_FIRST, LAST) if day.weekday() < 5]
    rows = [{"date": day, "base": "EUR", "quote": "USD", "rate": Decimal("1.05") + Decimal(n % 97) / 1000, "source": "ECB", "fetched_at": FETCHED_AT} for n, day in enumerate(usd)]
    rows += [{"date": day, "base": "EUR", "quote": "GBP", "rate": Decimal("0.85") + Decimal(n % 89) / 1000, "source": "ECB", "fetched_at": FETCHED_AT} for n, day in enumerate(gbp)]
    return rows


@dataclasses.dataclass(frozen=True)
class _World:
    engine: AsyncEngine


@pytest_asyncio.fixture
async def world(tmp_path: Path) -> AsyncIterator[_World]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'fx_stretch.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(engine, expire_on_commit=False) as session:
            await session.execute(insert(FxRate), _rate_rows())
            await session.commit()
        yield _World(engine)
    finally:
        await engine.dispose()


def _items(source: str, destination: str, amount: str, first: date, last: date) -> list[tuple[Currency, str, date]]:
    return [(Currency(code=source, amount=Decimal(amount)), destination, day) for day in _days(first, last)]


#: (name, items): direct, inverse, identity, no rate at all, before the first rate, over the gap, a printed exponent, a zero
LISTS = {
    "direct": _items("EUR", "USD", "100.50", FIRST, LAST),
    "inverse": _items("USD", "EUR", "37.123456", FIRST, LAST),
    "identity": _items("EUR", "EUR", "5", FIRST, FIRST + timedelta(days=9)),
    "no-rate": _items("CHF", "EUR", "10", FIRST, FIRST + timedelta(days=20)),
    "before-the-first-rate": _items("EUR", "USD", "1", date(2023, 11, 20), date(2023, 12, 10)),
    "gbp-starts-late": _items("EUR", "GBP", "250", date(2024, 4, 20), date(2024, 5, 20)),
    "gbp-inverse-starts-late": _items("GBP", "EUR", "250", date(2024, 4, 20), date(2024, 5, 20)),
    "over-the-gap": _items("EUR", "USD", "1", date(2024, 5, 20), date(2024, 7, 10)),
    "exponent-1": _items("EUR", "USD", "1", date(2024, 2, 1), date(2024, 2, 20)),
    "exponent-1.0": _items("EUR", "USD", "1.0", date(2024, 2, 1), date(2024, 2, 20)),
    "zero": _items("EUR", "USD", "0", date(2024, 2, 1), date(2024, 2, 20)),
    "one-item": _items("EUR", "USD", "100", date(2024, 2, 7), date(2024, 2, 7)),
}
#: several ranges and pairs in one list, as a request with several conversions builds it
LISTS["mixed"] = [*LISTS["direct"][:40], *LISTS["no-rate"][:5], *LISTS["inverse"][100:140], *LISTS["identity"], *LISTS["gbp-starts-late"], *LISTS["exponent-1.0"][:6], *LISTS["exponent-1"][:6]]


def _dump(results: list) -> list:
    return [None if item is None else (str(item[0].amount), item[0].code, item[1].isoformat(), item[2]) for item in results]


@pytest.mark.asyncio
@pytest.mark.parametrize("name", list(LISTS))
async def test_xq301_the_function_answers_what_convert_bulk_answers(world, name):
    """XQ3-01: ``convert_by_stretch`` gives, item for item, the result and the error text ``convert_bulk`` gives with every
    item handed to it.

    Green before the cure only if the function existed: it did not.
    """
    items = LISTS[name]
    async with AsyncSession(world.engine, expire_on_commit=False) as session:
        expected_results, expected_errors = await convert_bulk(session, items, raise_on_error=False)
        results, errors = await convert_by_stretch(session, items)

    assert _dump(results) == _dump(expected_results), name
    assert errors == expected_errors, name


@pytest.mark.asyncio
async def test_xq302_the_amount_that_prints_differently_keeps_its_digits(world):
    """XQ3-02: 1 and 1.0 on the same rate row are two conversions: their products do not print the same
    (``1.05`` and ``1.050``), and each keeps its own."""
    items = LISTS["exponent-1"][:3] + LISTS["exponent-1.0"][:3]
    async with AsyncSession(world.engine, expire_on_commit=False) as session:
        expected, _ = await convert_bulk(session, items, raise_on_error=False)
        results, _ = await convert_by_stretch(session, items)

    assert [str(item[0].amount) for item in results] == [str(item[0].amount) for item in expected]
    assert str(results[0][0].amount) != str(results[3][0].amount)


@pytest.mark.asyncio
@pytest.mark.parametrize(("name", "stretches"), [("direct", None), ("inverse", None), ("over-the-gap", None), ("one-item", 1), ("identity", 0)])
async def test_xq303_convert_is_handed_the_stretches_not_the_days(world, name, stretches):
    """XQ3-03: ``convert`` is handed one item for each distinct (amount, pair, rate row) — the rate rows the days read —
    and nothing for an identity or a day with no rate.

    Red before the cure: ``convert_bulk`` was handed every day.
    """
    items = LISTS[name]
    handed: list[int] = []

    async def counting(session, conversions, raise_on_error=True):
        handed.append(len(conversions))
        return await convert_bulk(session, conversions, raise_on_error=raise_on_error)

    async with AsyncSession(world.engine, expire_on_commit=False) as session:
        results, errors = await convert_by_stretch(session, items, convert=counting)
        # the rate rows the days read: each result carries the date of its rate row
        expected = len({item[1] for item in results if item is not None}) if stretches is None else stretches
        assert errors == [] or name != "direct"

    assert sum(handed) == expected, f"{sum(handed)} conversions for {len(items)} days"
    if stretches is None:
        assert 0 < sum(handed) < len(items)


@pytest.mark.asyncio
async def test_xq306_a_stretch_convert_fails_without_saying_why_still_leaves_an_error_for_each_day(world):
    """XQ3-06: ``convert`` answers ``None`` for a stretch and gives no error (a double that fails silently): each day of the
    stretch gets an error of its own, numbered by its item, and its result stays ``None`` — never a silent ``None``."""
    items = LISTS["exponent-1"][:3]  # three days of one amount

    async def silent(_session, conversions, raise_on_error=True):
        return [None] * len(conversions), []

    async with AsyncSession(world.engine, expire_on_commit=False) as session:
        results, errors = await convert_by_stretch(session, items, convert=silent)

    assert all(item is None for item in results)
    assert [message.split(" failed")[0] for message in errors] == [f"Conversion {index}" for index in range(len(items))]


# =============================================================================
# THE HANDLER
# =============================================================================


def _request(source: str, destination: str, amount: str, first: date, last: date, **extra: Any) -> FXConversionRequest:
    return FXConversionRequest(from_amount=Currency(code=source, amount=Decimal(amount)), to_currency=destination, date_range=DateRangeModel(start=first, end=last), **extra)


HANDLER_CASES = {
    "plain": [_request("EUR", "USD", "100", date(2024, 2, 1), date(2024, 8, 31))],
    "inverse": [_request("USD", "EUR", "37.5", date(2024, 2, 1), date(2024, 8, 31))],
    "zero-amount": [_request("EUR", "USD", "0", date(2024, 2, 1), date(2024, 3, 1))],
    "identity": [_request("EUR", "EUR", "7", date(2024, 2, 1), date(2024, 2, 20))],
    "gbp-starts-late": [_request("EUR", "GBP", "10", date(2024, 4, 20), date(2024, 5, 20))],
    "with-a-signal": [_request("EUR", "USD", "100", date(2024, 2, 1), date(2024, 3, 31), signals=[SMA3])],
    "weekly": [_request("EUR", "USD", "100", date(2024, 1, 1), date(2024, 12, 31), resolution="weekly", signals=[SMA3])],
    "several": [_request("EUR", "USD", "100", date(2024, 2, 1), date(2024, 2, 29)), _request("GBP", "EUR", "3", date(2024, 4, 25), date(2024, 5, 10)), _request("EUR", "USD", "1", date(2024, 5, 25), date(2024, 6, 10))],
}


def _without_clock(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _without_clock(item) for key, item in value.items() if key != "computed_at"}
    if isinstance(value, list):
        return [_without_clock(item) for item in value]
    return value


@pytest.mark.asyncio
@pytest.mark.parametrize("name", list(HANDLER_CASES))
async def test_xq304_the_handler_answers_what_it_answered_with_every_day_converted(world, monkeypatch, name):
    """XQ3-04: ``convert_currency_bulk`` — results, errors, signal results, samples — is the one it gave when every day went
    through ``convert_bulk`` (the reference replaces ``convert_by_stretch`` by that call)."""
    request = HANDLER_CASES[name]

    async def every_day(session, conversions, *, convert=None, steps=None):
        return await convert_bulk(session, conversions, raise_on_error=False)

    async def answer() -> Any:
        async with AsyncSession(world.engine, expire_on_commit=False) as session:
            try:
                response = await currencies.convert_currency_bulk(request=list(request), session=session, _current_user=None)
            except Exception as error:  # the 404 of a request that converted nothing is part of the answer
                return {"raised": f"{type(error).__name__}: {getattr(error, 'detail', error)}"}
        return _without_clock(response.model_dump(mode="json"))

    with monkeypatch.context() as head:
        head.setattr(currencies, "convert_by_stretch", every_day)
        reference = await answer()
    assert await answer() == reference, name
    if "raised" not in reference:
        assert reference["results"], "premise: the case converts something"


@pytest.mark.asyncio
async def test_xq305_the_handler_hands_convert_the_stretches_not_the_days(world, monkeypatch):
    """XQ3-05: a 7-month EUR→USD range (213 days) and the same with a signal (the warm-up block too) hand ``convert_bulk`` the
    rate rows' stretches: the rate changes on Mondays, Wednesdays and Fridays, so about 90 conversions, not 213 or 426.

    Red before the cure: one item for every day of each block."""
    handed: list[int] = []

    async def counting(session, conversions, raise_on_error=True):
        handed.append(len(conversions))
        return await convert_bulk(session, conversions, raise_on_error=raise_on_error)

    monkeypatch.setattr(currencies, "convert_bulk", counting)
    async with AsyncSession(world.engine, expire_on_commit=False) as session:
        response = await currencies.convert_currency_bulk(request=HANDLER_CASES["plain"] + HANDLER_CASES["with-a-signal"], session=session, _current_user=None)

    days = len(response.results)
    assert days == 213 + 60
    assert sum(handed) < days // 2, f"{sum(handed)} conversions for {days} daily results"

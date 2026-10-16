"""C-97a (workstream W, GitHub #43): manual prices and events refuse the digits they cannot keep; provider prices are truncated.

Measured before the lot:

* ``bulk_upsert_prices`` truncates every price to 6 decimals (``truncate_priceHistory``, ``ROUND_DOWN``),
  for manual input (``POST /assets/prices``: ``source_plugin_key="MANUAL"``) and for provider refreshes
  alike, and the column rounds to 6 on read: a PEPE close of 0.0000034573 EUR typed by the user is
  stored, without a word, as 0.000003.
* ``bulk_upsert_events`` (reached only from ``POST /assets/events``) accepts a dividend of 0.1234567 EUR
  and reads it back rounded to 6 decimals (``AssetEvent.value`` is ``Numeric(18, 6)``).

The contract (developer's decisions of 16/10):

* A price column keeps 12 decimals and 15 significant digits (``RealDecimal(24, 12)``). A MANUAL upsert
  where any open/high/low/close exceeds either limit is refused BEFORE anything is written, for every
  asset of the call: ``ValueError`` (HTTP 400 from the router), naming the asset id, the maximum (12
  decimal places, 15 significant digits) and the offending date(s). The ``-1`` sentinel of
  open/high/low/volume is no digit issue. A provider upsert (``source_plugin_key`` a provider code) is
  never refused: its prices are truncated to 12 decimals then 15 significant digits (``ROUND_DOWN``)
  and stored. A manual close of 0.0000034573 reads back 0.0000034573.
* A manual event whose ``value.amount`` exceeds 6 decimal places or 15 significant digits is refused
  like a currency mismatch: ``AssetSourceError`` ``EVENT_TOO_MANY_DIGITS``, nothing written; the
  endpoint answers 400 (``_REFUSAL_STATUS``).
* What already fits reads back exactly as today, form included.

Each red says what the user faces; a GUARD passes before and after the cure. A refusal is looked for
as the router meets it: nobody commits after a refused call, the session just closes, so "nothing
written" sees exactly what the service committed by itself.

Isolation: write-scoped, the services default (as ``asset-source``). Every row is this unit's own: two
EUR CRYPTO assets created under a unique name, and only their prices and events are written, read and
wiped, by asset id. Nothing here counts or reads a row it did not write.
"""

import asyncio
import re
import sys
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

# Setup test database BEFORE importing app modules
from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.assets import events as events_api
from backend.app.db.models import Asset, AssetEvent, AssetType, PriceHistory
from backend.app.db.session import get_async_engine
from backend.app.schemas.assets.events import FAEventUpsert
from backend.app.schemas.prices import FAPricePoint, FAUpsert
from backend.app.services.assets.base import AssetSourceError
from backend.app.services.assets.manager import AssetSourceManager
from backend.app.services.assets.price_store import PRICE_UPSERT_CHUNK_SIZE
from backend.test_scripts.test_utils import unique_id

# A window far from the mock dataset and from the other price/event units (1992, 1994-1995). Rows are
# scoped by asset anyway: the dates only keep the failure output readable.
BASE_DATE = date(1991, 4, 8)

# A provider code, as a refresh tags its rows (``_persist_refresh_item``). Only a provenance tag here:
# nothing is fetched.
PROVIDER = "yfinance"


def _day(offset: int) -> date:
    return BASE_DATE + timedelta(days=offset)


# --------------------------------------------------------------------------- #
# Rows owned by this unit
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class _Owned:
    """The two EUR CRYPTO assets of this unit: PEPE, the one the stories are about, and another one saved in the same call."""

    asset_id: int
    other_asset_id: int

    @property
    def asset_ids(self) -> list[int]:
        return [self.asset_id, self.other_asset_id]


async def _wipe(owned: _Owned) -> None:
    """Drop every price and event of this unit's assets."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        await session.execute(delete(PriceHistory).where(PriceHistory.asset_id.in_(owned.asset_ids)))
        await session.execute(delete(AssetEvent).where(AssetEvent.asset_id.in_(owned.asset_ids)))
        await session.commit()


@pytest.fixture(scope="module")
def owned_module() -> _Owned:
    """The two assets, under a name no concurrent worker can repeat, dropped with their rows in teardown."""
    marker = f"{unique_id('C97a')}_{uuid.uuid4().hex[:8]}"

    async def _create() -> _Owned:
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            pepe = Asset(display_name=f"C97a PEPE {marker}", currency="EUR", asset_type=AssetType.CRYPTO, active=True)
            other = Asset(display_name=f"C97a Other {marker}", currency="EUR", asset_type=AssetType.CRYPTO, active=True)
            session.add_all([pepe, other])
            await session.commit()
            return _Owned(pepe.id, other.id)

    async def _drop(owned: _Owned) -> None:
        await _wipe(owned)
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            await session.execute(delete(Asset).where(Asset.id.in_(owned.asset_ids)))
            await session.commit()

    owned = asyncio.run(_create())
    yield owned
    asyncio.run(_drop(owned))


@pytest_asyncio.fixture
async def owned(owned_module: _Owned):
    """The module's assets, with no price and no event before and after the test."""
    await _wipe(owned_module)
    yield owned_module
    await _wipe(owned_module)


# --------------------------------------------------------------------------- #
# Prices: requests, read-back, refusals
# --------------------------------------------------------------------------- #


def _point(offset: int, close: str, **ohlcv: str) -> FAPricePoint:
    """One price point as the Data Editor sends it: no currency (the asset's), only the fields given."""
    return FAPricePoint(date=_day(offset), close=Decimal(close), **{field: Decimal(value) for field, value in ohlcv.items()})


async def _manual_upsert(data: list[FAUpsert]) -> dict:
    """``POST /assets/prices`` minus HTTP: the router calls the service without ``source_plugin_key`` (``"MANUAL"``)."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        return await AssetSourceManager.bulk_upsert_prices(data, session)


async def _provider_upsert(data: list[FAUpsert]) -> dict:
    """What a provider refresh does with the prices it fetched (``_persist_refresh_item``)."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        return await AssetSourceManager.bulk_upsert_prices(data, session, source_plugin_key=PROVIDER)


async def _stored(owned: _Owned) -> dict[tuple[int, date], PriceHistory]:
    """Every price row of this unit's assets by (asset_id, date), read back through the model's column types."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        rows = (await session.execute(select(PriceHistory).where(PriceHistory.asset_id.in_(owned.asset_ids)))).scalars().all()
    return {(row.asset_id, row.date): row for row in rows}


def _describe_prices(stored: dict[tuple[int, date], PriceHistory]) -> str:
    """The stored closes as a failure message shows them: the first five, then how many more."""
    closes = [f"asset {asset_id} {day.isoformat()}: {row.close}" for (asset_id, day), row in sorted(stored.items())]
    more = f" (+{len(closes) - 5} more)" if len(closes) > 5 else ""
    return "[" + ", ".join(closes[:5]) + more + "]"


async def _manual_upsert_refused(owned: _Owned, data: list[FAUpsert], story: str) -> ValueError:
    """``POST /assets/prices`` minus HTTP, for a call that must be refused: the ValueError the router answers 400 with."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        try:
            result = await AssetSourceManager.bulk_upsert_prices(data, session)
        except ValueError as refusal:
            return refusal
    messages = [row["message"] for row in result["results"]]
    pytest.fail(f"{story} was accepted ({messages}) and stored as {_describe_prices(await _stored(owned))}, instead of being refused (C-97a: at most 12 decimal places and 15 significant digits)")


def _assert_names_the_refusal(refusal: ValueError, asset_id: int, days: list[date]) -> None:
    """The refusal names the asset, the maximum (12 decimal places, 15 significant digits) and every offending date.

    The whole numbers are read after the ISO dates and the decimal values are taken out, so a date or a
    price cannot stand in for the limit, and an asset id of 12 or 15 counts once, not for the limit too.
    """
    message = str(refusal)
    stated = Counter(re.findall(r"\d+", re.sub(r"\d*\.\d+(?:[eE][-+]?\d+)?", " ", re.sub(r"\d{4}-\d{2}-\d{2}", " ", message))))
    missing = Counter({str(asset_id): 1}) + Counter({"12": 1, "15": 1}) - stated
    assert not missing, f"the refusal must name asset {asset_id} and the maximum (12 decimal places, 15 significant digits); missing {sorted(missing)} in {message!r}"
    unnamed = [day.isoformat() for day in days if day.isoformat() not in message]
    assert not unnamed, f"the refusal does not name the offending date(s) {unnamed}: {message!r}"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("typed", "story"),
    [
        pytest.param("0.0000034573", "a PEPE close of 0.0000034573 EUR", id="pepe"),
        pytest.param("0.000003457312", "a close of 0.000003457312 EUR (12 decimals, the maximum)", id="12-decimals"),
        pytest.param("123.456789012345", "a close of 123.456789012345 EUR (15 significant digits, the maximum)", id="15-significant-digits"),
    ],
)
async def test_a_manual_close_within_the_limits_reads_back_exactly(owned, typed, story):
    """Red. Before: truncated to 6 decimals on write, rounded to 6 on read: 0.0000034573 reads 0.000003, 123.456789012345 reads 123.456789.

    Contract: stored as typed and read back exactly.
    """
    await _manual_upsert([FAUpsert(asset_id=owned.asset_id, prices=[_point(0, typed)])])

    row = (await _stored(owned)).get((owned.asset_id, _day(0)))
    assert row is not None, f"{story} was not stored"
    assert row.close == Decimal(typed), f"{story} reads back as {row.close} EUR"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("typed", "story"),
    [
        pytest.param("0.000003457312", "a close of 0.000003457312 EUR (12 decimals, the maximum)", id="12-decimals"),
        pytest.param("123.456789012345", "a close of 123.456789012345 EUR (15 significant digits, the maximum)", id="15-significant-digits"),
        pytest.param("100.50000000000000", "a close typed 100.50000000000000 EUR (trailing zeros do not count)", id="trailing-zeros"),
    ],
)
async def test_guard_a_manual_close_at_the_limits_is_accepted(owned, typed, story):
    """GUARD (green before and after): both limits are included, and trailing zeros are no decimals."""
    try:
        await _manual_upsert([FAUpsert(asset_id=owned.asset_id, prices=[_point(0, typed)])])
    except ValueError as refusal:
        pytest.fail(f"{story} was refused: {refusal}")

    stored = await _stored(owned)
    assert (owned.asset_id, _day(0)) in stored, f"{story} was not stored"


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["open", "high", "low", "volume"])
async def test_guard_the_minus_one_sentinel_is_no_digit_issue(owned, field):
    """GUARD (green before and after): -1 clears a field (F.4); it is never refused.

    One field at a time: -1 on both low and high is turned down by the OHLC integrity guard (a close
    outside [-1, -1]), which is another matter.
    """
    try:
        await _manual_upsert([FAUpsert(asset_id=owned.asset_id, prices=[_point(0, "1.5", **{field: "-1"})])])
    except ValueError as refusal:
        pytest.fail(f"a manual point clearing its {field} with the -1 sentinel was refused: {refusal}")

    row = (await _stored(owned)).get((owned.asset_id, _day(0)))
    assert row is not None, f"a manual point clearing its {field} with the -1 sentinel was not stored"
    assert getattr(row, field) is None, f"the -1 sentinel left {field} = {getattr(row, field)}"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("typed", "form"),
    [
        pytest.param("123.456789", "123.456789", id="6-decimals"),
        pytest.param("131.07", "131.070000", id="2-decimals"),
        pytest.param("100.50000000000000", "100.500000", id="trailing-zeros"),
    ],
)
async def test_guard_a_manual_close_that_fits_today_reads_back_as_today(owned, typed, form):
    """GUARD (green before and after): a price that fits 6 decimals reads back as today, form included."""
    await _manual_upsert([FAUpsert(asset_id=owned.asset_id, prices=[_point(0, typed)])])

    row = (await _stored(owned))[(owned.asset_id, _day(0))]
    assert str(row.close) == form, f"a close of {typed} EUR reads back as {row.close}: today, and after C-97a, {form}"


@pytest.mark.asyncio
async def test_a_manual_close_with_13_decimals_is_refused_and_nothing_of_the_call_is_written(owned):
    """Red. Before: accepted, every close stored truncated to 0.000003.

    Contract: ValueError naming the asset, the maximum and both offending dates; the valid close of
    the same call (day 0) is not written either.
    """
    data = [FAUpsert(asset_id=owned.asset_id, prices=[_point(0, "0.0000034573"), _point(1, "0.0000034573123"), _point(2, "0.0000034573999")])]

    refusal = await _manual_upsert_refused(owned, data, "a PEPE close of 0.0000034573123 EUR (13 decimals)")

    _assert_names_the_refusal(refusal, owned.asset_id, [_day(1), _day(2)])
    stored = await _stored(owned)
    assert not stored, f"the call was refused, yet rows were written: {_describe_prices(stored)}"


@pytest.mark.asyncio
async def test_a_refused_close_writes_nothing_for_the_other_assets_of_the_call(owned):
    """Red. Before: accepted, both assets stored.

    The valid asset comes FIRST: a check run asset by asset, after the earlier ones are committed (where
    the currency check runs today), would leave it written. Contract: ValueError naming the second asset;
    neither asset has a row.
    """
    data = [
        FAUpsert(asset_id=owned.other_asset_id, prices=[_point(0, "1.5")]),
        FAUpsert(asset_id=owned.asset_id, prices=[_point(0, "0.0000034573123")]),
    ]

    refusal = await _manual_upsert_refused(owned, data, "a PEPE close of 0.0000034573123 EUR (13 decimals), saved with another asset's price")

    _assert_names_the_refusal(refusal, owned.asset_id, [_day(0)])
    stored = await _stored(owned)
    assert not stored, f"the call was refused, yet rows were written: {_describe_prices(stored)}"


@pytest.mark.asyncio
async def test_a_refused_close_in_the_second_chunk_writes_nothing_of_the_first(owned):
    """Red. Before: accepted, every close stored.

    ``bulk_upsert_prices`` commits every ``PRICE_UPSERT_CHUNK_SIZE`` dates: a check made chunk by chunk
    would leave the first chunk written. Contract: refused, nothing written.
    """
    late = _point(PRICE_UPSERT_CHUNK_SIZE, "0.0000034573123")
    data = [FAUpsert(asset_id=owned.asset_id, prices=[*(_point(offset, "1.5") for offset in range(PRICE_UPSERT_CHUNK_SIZE)), late])]

    refusal = await _manual_upsert_refused(owned, data, f"a history of {PRICE_UPSERT_CHUNK_SIZE + 1} closes whose last one, 0.0000034573123 EUR, has 13 decimals")

    _assert_names_the_refusal(refusal, owned.asset_id, [late.date])
    stored = await _stored(owned)
    assert not stored, f"the call was refused, yet {len(stored)} rows were written: {_describe_prices(stored)}"


@pytest.mark.asyncio
async def test_a_manual_close_with_16_significant_digits_is_refused(owned):
    """Red. Before: accepted and stored as 3333.333333. Contract: refused (a double keeps 15 significant digits), nothing written."""
    data = [FAUpsert(asset_id=owned.asset_id, prices=[_point(0, "3333.333333333333")])]

    refusal = await _manual_upsert_refused(owned, data, "a close of 3333.333333333333 EUR (16 significant digits)")

    _assert_names_the_refusal(refusal, owned.asset_id, [_day(0)])
    stored = await _stored(owned)
    assert not stored, f"the call was refused, yet rows were written: {_describe_prices(stored)}"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "typed"),
    [
        pytest.param("open", "1.0000000000001", id="open"),
        pytest.param("high", "1.0000000000001", id="high"),
        pytest.param("low", "0.9999999999999", id="low"),
    ],
)
async def test_a_manual_open_high_or_low_beyond_the_limits_is_refused(owned, field, typed):
    """Red. Before: accepted, the field stored truncated to 6 decimals. Contract: any of open/high/low/close counts."""
    data = [FAUpsert(asset_id=owned.asset_id, prices=[_point(0, "1", **{field: typed})])]

    refusal = await _manual_upsert_refused(owned, data, f"a manual {field} of {typed} EUR (13 decimals) beside a close of 1")

    _assert_names_the_refusal(refusal, owned.asset_id, [_day(0)])
    stored = await _stored(owned)
    assert not stored, f"the call was refused, yet rows were written: {_describe_prices(stored)}"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "delivered", "expected"),
    [
        pytest.param("close", "0.00000345731234567", "0.000003457312", id="close"),
        pytest.param("open", "0.00000345731234567", "0.000003457312", id="open"),
        pytest.param("high", "0.00000345731299999", "0.000003457312", id="high"),
        pytest.param("low", "0.00000345731199999", "0.000003457311", id="low"),
    ],
)
async def test_a_provider_price_beyond_12_decimals_is_stored_truncated_at_12(owned, field, delivered, expected):
    """Red. Before: truncated at 6 decimals, the PEPE candle is stored at 0.000003.

    Contract: never refused; cut to 12 decimals, ROUND_DOWN (the low 0.00000345731199999 is 0.000003457311,
    not rounded up). The close of the open/high/low cases already has 12 decimals.
    """
    close = delivered if field == "close" else "0.000003457312"
    extra = {} if field == "close" else {field: delivered}
    try:
        await _provider_upsert([FAUpsert(asset_id=owned.asset_id, prices=[_point(0, close, **extra)])])
    except ValueError as refusal:
        pytest.fail(f"a {PROVIDER} refresh delivering a PEPE {field} of {delivered} EUR was refused ({refusal}): a provider's prices are truncated, never refused")

    row = (await _stored(owned))[(owned.asset_id, _day(0))]
    assert getattr(row, field) == Decimal(expected), f"a {PROVIDER} refresh delivering a PEPE {field} of {delivered} EUR stores {getattr(row, field)}: expected {expected} (12 decimals, ROUND_DOWN)"
    assert row.source_plugin_key == PROVIDER


@pytest.mark.asyncio
async def test_a_provider_close_beyond_15_significant_digits_is_stored_cut_at_15(owned):
    """Red. Before: truncated at 6 decimals, 65432.123456. Contract: never refused; 15 significant digits, ROUND_DOWN: 65432.1234567890."""
    delivered = "65432.123456789012"
    try:
        await _provider_upsert([FAUpsert(asset_id=owned.asset_id, prices=[_point(0, delivered)])])
    except ValueError as refusal:
        pytest.fail(f"a {PROVIDER} refresh delivering a close of {delivered} EUR was refused ({refusal}): a provider's prices are truncated, never refused")

    row = (await _stored(owned))[(owned.asset_id, _day(0))]
    assert row.close == Decimal("65432.123456789"), f"a {PROVIDER} refresh delivering a close of {delivered} EUR stores {row.close}: expected 65432.1234567890 (15 significant digits, ROUND_DOWN)"


# --------------------------------------------------------------------------- #
# Events: requests, read-back, refusals
# --------------------------------------------------------------------------- #


def _event(offset: int, kind: str, amount: str) -> dict:
    """One event of a manual upsert item, as the event editor sends it."""
    return {"date": _day(offset).isoformat(), "type": kind, "value": {"code": "EUR", "amount": amount}}


def _event_item(asset_id: int, events: list[dict]) -> FAEventUpsert:
    """A manual upsert item, validated as the endpoint validates it."""
    return FAEventUpsert.model_validate({"asset_id": asset_id, "events": events})


async def _stored_events(owned: _Owned) -> list[AssetEvent]:
    """Every event of this unit's assets, lowest id first."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        stmt = select(AssetEvent).where(AssetEvent.asset_id.in_(owned.asset_ids)).order_by(AssetEvent.id)
        return list((await session.execute(stmt)).scalars().all())


def _describe_events(rows: list[AssetEvent]) -> list[str]:
    return [f"asset {row.asset_id} {row.type} {row.date.isoformat()}: {row.value} {row.currency}" for row in rows]


async def _upsert_events(data: list[FAEventUpsert]) -> dict:
    """``POST /assets/events`` minus HTTP, for a request that must succeed (the service commits it)."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        return await AssetSourceManager.bulk_upsert_events(data, session)


async def _upsert_events_refused(owned: _Owned, data: list[FAEventUpsert], story: str) -> AssetSourceError:
    """``POST /assets/events`` minus HTTP, for a request that must be refused."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        try:
            result = await AssetSourceManager.bulk_upsert_events(data, session)
        except AssetSourceError as refusal:
            return refusal
    messages = [row["message"] for row in result["results"]]
    pytest.fail(f"{story} was accepted ({messages}) and reads back as {_describe_events(await _stored_events(owned))}, instead of being refused with EVENT_TOO_MANY_DIGITS (C-97a: at most 6 decimal places and 15 significant digits)")


@pytest.mark.asyncio
async def test_a_manual_event_with_7_decimals_is_refused_and_nothing_is_written(owned):
    """Red. Before: accepted; the dividend of 0.1234567 reads back 0.123457.

    Contract: AssetSourceError EVENT_TOO_MANY_DIGITS; the valid event of the same item is not written either.
    """
    data = [_event_item(owned.asset_id, [_event(0, "DIVIDEND", "0.123456"), _event(1, "DIVIDEND", "0.1234567")])]

    refusal = await _upsert_events_refused(owned, data, "a PEPE dividend of 0.1234567 EUR (7 decimals)")

    assert refusal.error_code == "EVENT_TOO_MANY_DIGITS", f"refused with {refusal.error_code}: {refusal.message}"
    rows = await _stored_events(owned)
    assert not rows, f"the request was refused, yet events were written: {_describe_events(rows)}"


@pytest.mark.asyncio
async def test_a_manual_event_with_16_significant_digits_is_refused(owned):
    """Red. Before: accepted. Contract: EVENT_TOO_MANY_DIGITS (a double keeps 15 significant digits), nothing written."""
    data = [_event_item(owned.asset_id, [_event(0, "DIVIDEND", "1234567890.123456")])]

    refusal = await _upsert_events_refused(owned, data, "a dividend of 1234567890.123456 EUR (16 significant digits)")

    assert refusal.error_code == "EVENT_TOO_MANY_DIGITS", f"refused with {refusal.error_code}: {refusal.message}"
    rows = await _stored_events(owned)
    assert not rows, f"the request was refused, yet events were written: {_describe_events(rows)}"


@pytest.mark.asyncio
async def test_a_refused_event_in_a_later_item_writes_nothing_of_the_earlier_one(owned):
    """Red. Before: accepted, both items stored.

    Contract: EVENT_TOO_MANY_DIGITS; the request is all or nothing, and, as every refusal of
    ``bulk_upsert_events`` (decision 22), its details name the item: index 1, the PEPE asset.
    """
    data = [
        _event_item(owned.other_asset_id, [_event(0, "INTEREST", "1.50")]),
        _event_item(owned.asset_id, [_event(0, "DIVIDEND", "0.1234567")]),
    ]

    refusal = await _upsert_events_refused(owned, data, "a PEPE dividend of 0.1234567 EUR (7 decimals), saved after another asset's interest")

    assert refusal.error_code == "EVENT_TOO_MANY_DIGITS", f"refused with {refusal.error_code}: {refusal.message}"
    assert (refusal.details.get("item_index"), refusal.details.get("asset_id")) == (1, owned.asset_id), f"the refusal does not name its item (decision 22): details {refusal.details}"
    rows = await _stored_events(owned)
    assert not rows, f"the request was refused, yet events were written: {_describe_events(rows)}"


@pytest.mark.asyncio
async def test_the_events_endpoint_answers_400_event_too_many_digits(owned):
    """Red. Before: 200, the dividend stored. With the service refusing but no entry in ``_REFUSAL_STATUS``: 500.

    Contract: 400, ``detail.error_code`` EVENT_TOO_MANY_DIGITS, nothing written. The route function is
    called as FastAPI calls it, minus HTTP: its dependencies given directly.
    """
    item = _event_item(owned.asset_id, [_event(0, "DIVIDEND", "0.1234567")])
    answer: HTTPException | None = None
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        try:
            await events_api.upsert_events_bulk([item], session=session, _current_user=None)
        except HTTPException as refusal:
            answer = refusal
    if answer is None:
        pytest.fail(f"POST /assets/events saved a PEPE dividend of 0.1234567 EUR (200): it reads back as {_describe_events(await _stored_events(owned))}, instead of answering 400 EVENT_TOO_MANY_DIGITS")

    detail = answer.detail if isinstance(answer.detail, dict) else {}
    assert (answer.status_code, detail.get("error_code")) == (400, "EVENT_TOO_MANY_DIGITS"), f"POST /assets/events answers {answer.status_code} {answer.detail!r} to a PEPE dividend of 0.1234567 EUR: expected 400 EVENT_TOO_MANY_DIGITS"
    rows = await _stored_events(owned)
    assert not rows, f"the request was refused, yet events were written: {_describe_events(rows)}"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("amount", "story"),
    [
        pytest.param("0.123456", "a dividend of 0.123456 EUR (6 decimals, the maximum)", id="6-decimals"),
        pytest.param("123456789.123456", "a dividend of 123456789.123456 EUR (15 significant digits, the maximum)", id="15-significant-digits"),
        pytest.param("1.5000000000", "a dividend typed 1.5000000000 EUR (trailing zeros do not count)", id="trailing-zeros"),
    ],
)
async def test_guard_a_manual_event_within_the_limits_is_stored(owned, amount, story):
    """GUARD (green before and after): both limits are included, trailing zeros are no decimals, and the value reads back."""
    try:
        await _upsert_events([_event_item(owned.asset_id, [_event(0, "DIVIDEND", amount)])])
    except AssetSourceError as refusal:
        pytest.fail(f"{story} was refused: {refusal.error_code} {refusal.message}")

    rows = await _stored_events(owned)
    assert [(row.asset_id, row.date, row.value) for row in rows] == [(owned.asset_id, _day(0), Decimal(amount))], f"{story} reads back as {_describe_events(rows)}"

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
  decimal places, 15 significant digits) and the offending date(s). The ``"clear"`` marker of
  open/high/low/volume (N92; the ``-1`` sentinel before it) is no digit issue. A provider upsert (``source_plugin_key`` a provider code) is
  never refused: its prices are truncated to 12 decimals then 15 significant digits (``ROUND_DOWN``)
  and stored. A manual close of 0.0000034573 reads back 0.0000034573.
* A manual event whose ``value.amount`` exceeds 6 decimal places or 15 significant digits is refused
  like a currency mismatch: ``AssetSourceError`` ``EVENT_TOO_MANY_DIGITS``, nothing written; the
  endpoint answers 400 (``_REFUSAL_STATUS``).
* What already fits reads back exactly as today, form included.

R13-SEC2 (W-B58, E's security review of 17/10): the magnitude. Measured before the cure: the manual check counts the
decimals and the significant digits of open/high/low/close, not their magnitude, and not the volume — a close of 1E+13
is stored, from 1E+48 the truncation raises ``InvalidOperation`` (12 decimals in 60 digits) and 1E+1000000 makes the
check itself raise ``decimal.Overflow``, a volume of 1E+400 is stored as a REAL inf; a provider upsert truncates every
price and commits chunk by chunk, so a close of 1E+60 in the second chunk raises after the first is written; the
current-price path stores a fresh quote as it comes (``Decimal(str(value))``: no truncation, no limit); manual events are
checked for decimals and significant digits only, provider events for nothing. The cure's contract:

* manual prices: ``_reject_prices_over_the_limit`` also refuses — ``ValueError``, HTTP 400, before anything is written,
  also when the offending point is the last of ``PRICE_UPSERT_CHUNK_SIZE + 1`` — a price beyond 12 integer digits or
  non-finite, and a volume non-finite or beyond 24 integer digits; a fractional volume stays accepted; the message names
  the asset, the dates and the limits (12 and 15 as before, and 24 for a volume). A close of 1E-2000000 is refused;
* provider prices (``source_plugin_key`` a provider code): before any chunk is written, a date with an unstorable value
  — a price non-finite or beyond 12 integer digits, a volume beyond 24, a close that truncates to 0 — is skipped and
  reported in its asset's result message ("rejected", with the date); every other date is written; nothing raises,
  wherever the date sits;
* the current price (``price_query.get_current_prices_bulk``): an unstorable quote (1E+400, 1E+60) is not persisted —
  today's row neither created nor changed — and nothing raises; a valid one is truncated like the history, 12 decimals
  then 15 significant digits, ``ROUND_DOWN``: a quote of 65432.1234567890999 is stored 65432.123456789;
* events: a manual value beyond 12 integer digits or non-finite is refused with ``EVENT_TOO_MANY_DIGITS``, the details
  gaining ``max_integer_digits: 12`` beside the existing keys, nothing written (``POST /assets/events`` answers 400); a
  provider event whose value cannot be stored is dropped by ``_upsert_asset_events``, the other events of the call
  written, nothing raised.

R13-SEC7-3 (the exponent bound of ``Currency``, ±100): a manual event value past it (1E+400) never reaches that store's
refusal — the schema refuses it first, ``value_error`` on ``events.<i>.value.amount`` naming the exponent, so
``POST /assets/events`` answers 422 and nothing is written; a provider event the schema refuses (a value of 5 000 digits,
or 1E+400) is dropped by ``_storable_events`` like an unstorable one, the others written, nothing raised.

A call that raises today where the contract refuses or skips fails its test naming the exception, never as an error. The
current-price tests drive ``_QuoteDouble``, a provider double the registry hands out for a code of the test's own, to
which the PEPE asset is assigned for that test alone (``assigned``); they read today's row with raw SQL, past the column
types, so a REAL inf or 1e60 written today is seen as the float it is.

W-B60 (17/10, the follow-up of W-B58): an event value reads back exactly. ``AssetEvent.value`` was a plain
``Numeric(18, 6)``, read through ``'%.6f'`` of the stored double, so from about 11 integer digits the double's noise
landed in the 6 decimals: a dividend of 12345678901.2345 EUR — 4 decimals, 15 significant digits, 11 integer digits,
within every limit of a manual event — read back 12345678901.234501. It becomes ``RealDecimal(18, 6)``, the same
declaration: written by ``bulk_upsert_events`` and read back through the events query (``query_events_bulk``, what
``POST /assets/events/query`` answers), it is 12345678901.234500, with 6 decimals as today; what reads well today keeps
its form (1.5 reads 1.500000, 0.000001 reads 0.000001). Compared as text, so the 6 decimals are pinned.

W-B68 (17/10): a provider's event value is stored as the column keeps it. Measured before the cure: ``_storable_events``,
the provider path of ``_upsert_asset_events`` (``refresh.py``), drops an event no value can keep (W-B58) and a SPLIT whose
ratio is not above 0 (X-R47), but never cuts the others as a provider price is cut (``storable_price``): a dividend of
784.0774475 EUR is written whole and reads back 784.077448 (the double rounded half-even at 6 decimals), so the row the
refresh's session holds is not the row read back; a SPLIT of ratio 0.0000001 is stored and reads back 0, the ratio X-R47
drops. The cure's contract: ``storable_value(amount, AssetEvent, "value")``; None drops the event as today; otherwise the
event takes the value cut ROUND_DOWN at 6 decimals, then at 15 significant digits (784.077447, 0.123456, 123456789012.123),
and a value that already fits keeps its form (1.5 stays 1.5); a SPLIT's ratio is judged once cut, so 0.0000001 is dropped
as an invalid split, the other events of the call written. Manual events never get there (C-97a refuses them first). These
tests carry ``wb68`` in their names (``-k WB68``); the rows of the refresh's session are held from its flushes, never
reloaded, and compared as ``Decimal`` with a fresh query's.

Each red says what the user faces; a GUARD passes before and after the cure. A refusal is looked for
as the router meets it: nobody commits after a refused call, the session just closes, so "nothing
written" sees exactly what the service committed by itself.

Isolation: write-scoped, the services default (as ``asset-source``). Every row is this unit's own: two EUR CRYPTO assets
created under a unique name, and only their prices and events are written, read and wiped, by asset id; and, for the
tests that need one, an assignment of the PEPE asset to a provider code of the test's own, deleted at teardown. The W-B68
tests write provider events of the PEPE asset alone, under that assignment, and capture the logs with structlog's testing
capture, proved live by a barrier event. Nothing here counts or reads a row it did not write.
"""

import asyncio
import re
import sys
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
import pytest_asyncio
from structlog.testing import capture_logs

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

# Setup test database BEFORE importing app modules
from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import delete, select, text
from sqlalchemy.event import listen
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.assets import events as events_api
from backend.app.db.models import Asset, AssetEvent, AssetEventType, AssetProviderAssignment, AssetType, PriceHistory, ProviderInputType
from backend.app.db.session import get_async_engine
from backend.app.schemas.assets.events import FAEventQueryItem, FAEventUpsert
from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.prices import FACurrentValue, FAHistoricalData, FAPricePoint, FAUpsert
from backend.app.services.assets import event_store
from backend.app.services.assets.base import AssetSourceError, AssetSourceProvider
from backend.app.services.assets.event_store import EventStoreOperations
from backend.app.services.assets.manager import AssetSourceManager
from backend.app.services.assets.price_store import PRICE_UPSERT_CHUNK_SIZE
from backend.app.services.assets.registry import AssetProviderRegistry
from backend.test_scripts.test_utils import unique_id

# A window far from the mock dataset and from the other price/event units (1992, 1994-1995). Rows are
# scoped by asset anyway: the dates only keep the failure output readable.
BASE_DATE = date(1991, 4, 8)

# A provider code, as a refresh tags its rows (``_persist_refresh_item``). Only a provenance tag here:
# nothing is fetched.
PROVIDER = "yfinance"

# The caller ``POST /assets/events`` is called with, directly: the route reads only its id, these requests never reach the P-10 filter, and 0 is no user's id.
_CALLER = SimpleNamespace(id=0)


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
    """``POST /assets/prices`` minus HTTP, for a call that must be refused: the ValueError the router answers 400 with.

    Any other exception fails the test naming it: the router answers 500 to it (R13-SEC2: ``decimal.Overflow`` and
    ``InvalidOperation`` are no ``ValueError``).
    """
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        try:
            result = await AssetSourceManager.bulk_upsert_prices(data, session)
        except ValueError as refusal:
            return refusal
        except Exception as exc:  # noqa: BLE001 — any other exception is the defect under test
            pytest.fail(f"{story} raised {exc!r} instead of a ValueError: POST /assets/prices answers 500, not 400 (R13-SEC2)")
    messages = [row["message"] for row in result["results"]]
    pytest.fail(f"{story} was accepted ({messages}) and stored as {_describe_prices(await _stored(owned))}, instead of being refused (C-97a: at most 12 decimal places and 15 significant digits; R13-SEC2: at most 12 integer digits, 24 for a volume)")


def _assert_names_the_refusal(refusal: ValueError, asset_id: int, days: list[date], extra_limits: tuple[str, ...] = ()) -> None:
    """The refusal names the asset, the maximum (12 decimal places, 15 significant digits), any ``extra_limits`` (24 for a
    volume, R13-SEC2) and every offending date.

    The whole numbers are read after the ISO dates and the decimal values are taken out — and the values written in
    scientific notation (``1E+13``), so that their exponent cannot stand in for a limit — so a date or a price cannot
    stand in for the limit, and an asset id of 12 or 15 counts once, not for the limit too.
    """
    message = str(refusal)
    without_values = re.sub(r"\d*\.?\d+[eE][-+]?\d+", " ", re.sub(r"\d*\.\d+(?:[eE][-+]?\d+)?", " ", re.sub(r"\d{4}-\d{2}-\d{2}", " ", message)))
    stated = Counter(re.findall(r"\d+", without_values))
    missing = Counter({str(asset_id): 1}) + Counter({"12": 1, "15": 1}) + Counter(extra_limits) - stated
    assert not missing, f"the refusal must name asset {asset_id} and the maximum (12 decimal places, 15 significant digits{''.join(', ' + limit for limit in extra_limits)}); missing {sorted(missing)} in {message!r}"
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
async def test_the_clear_marker_is_no_digit_issue(owned, field):
    """N92 (i) with «clear»: the text ``"clear"`` empties a field (it replaces the ``-1`` sentinel); the digit check of
    C-97 skips it, so it is never refused, and the field is stored NULL.

    The point goes as ``POST /assets/prices`` parses it: the JSON body validated into ``FAUpsert``.
    RED until N92: ``FAUpsert``'s points are ``FAPricePoint``, whose parser reads ``"clear"`` as a number
    (``Decimal("clear")`` raises ``InvalidOperation``: the route answers 500). Until then the ``-1`` sentinel was this
    case, a GUARD; ``-1`` is now a negative number, refused by the write model (``test_price_write_point.py``).
    Contract: not refused; the day stored with ``field`` NULL. One field at a time, as the -1 case was.
    """
    body = {"asset_id": owned.asset_id, "prices": [{"date": _day(0).isoformat(), "close": "1.5", field: "clear"}]}
    try:
        data = [FAUpsert.model_validate(body)]
    except Exception as exc:  # noqa: BLE001 — any exception here is the defect under test
        pytest.fail(f"N92: POST /assets/prices does not read a point clearing its {field} with 'clear': {exc!r}")
    try:
        await _manual_upsert(data)
    except ValueError as refusal:
        pytest.fail(f"a manual point clearing its {field} with 'clear' was refused: {refusal}")

    row = (await _stored(owned)).get((owned.asset_id, _day(0)))
    assert row is not None, f"a manual point clearing its {field} with 'clear' was not stored"
    assert getattr(row, field) is None, f"'clear' left {field} = {getattr(row, field)}"


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
    """``POST /assets/events`` minus HTTP, for a request that must be refused; any exception but the refusal fails the test
    naming it (the endpoint answers 500 to it)."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        try:
            result = await AssetSourceManager.bulk_upsert_events(data, session)
        except AssetSourceError as refusal:
            return refusal
        except Exception as exc:  # noqa: BLE001 — any other exception is the defect under test
            pytest.fail(f"{story} raised {exc!r} instead of an AssetSourceError: POST /assets/events answers 500 (R13-SEC2)")
    messages = [row["message"] for row in result["results"]]
    pytest.fail(f"{story} was accepted ({messages}) and reads back as {_describe_events(await _stored_events(owned))}, instead of being refused with EVENT_TOO_MANY_DIGITS (C-97a: at most 6 decimal places and 15 significant digits; R13-SEC2: at most 12 integer digits)")


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
    called as FastAPI calls it, minus HTTP: its dependencies given directly, the caller ``_CALLER``.
    """
    item = _event_item(owned.asset_id, [_event(0, "DIVIDEND", "0.1234567")])
    answer: HTTPException | None = None
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        try:
            await events_api.upsert_events_bulk([item], session=session, _current_user=_CALLER)
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


# --------------------------------------------------------------------------- #
# R13-SEC2 (W-B58): manual prices past the integer digits, and the volume
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "typed"),
    [
        pytest.param("close", "1E+13", id="close-1E+13"),
        pytest.param("close", "1000000000000", id="close-13-integer-digits"),
        pytest.param("close", "1E+48", id="close-1E+48"),
        pytest.param("close", "1E+400", id="close-1E+400"),
        pytest.param("close", "1E+1000000", id="close-1E+1000000"),
        pytest.param("open", "1E+13", id="open-1E+13"),
        pytest.param("high", "1E+60", id="high-1E+60"),
        pytest.param("low", "1E+13", id="low-1E+13"),
    ],
)
async def test_a_manual_price_beyond_12_integer_digits_is_refused_and_nothing_is_written(owned, field, typed):
    """Red today: the check has no magnitude. A close, open or low of 1E+13 or of 13 integer digits is accepted and
    stored; from 1E+48 the truncation raises ``InvalidOperation`` (12 decimals in 60 digits), and 1E+1000000 makes the
    check itself raise ``decimal.Overflow``: HTTP 500, not 400.

    Contract (R13-SEC2): ``ValueError`` naming the asset, the date and the limits (12 and 15 among them); nothing written.
    """
    point = _point(0, typed) if field == "close" else _point(0, "1", **{field: typed})

    refusal = await _manual_upsert_refused(owned, [FAUpsert(asset_id=owned.asset_id, prices=[point])], f"a manual {field} of {typed} EUR (beyond 12 integer digits)")

    _assert_names_the_refusal(refusal, owned.asset_id, [_day(0)])
    stored = await _stored(owned)
    assert not stored, f"the call was refused, yet rows were written: {_describe_prices(stored)}"


@pytest.mark.asyncio
async def test_a_manual_close_of_1e_minus_2000000_is_refused_and_nothing_is_written(owned):
    """Red today: the check normalizes the value in a context of 60 digits, where it underflows to 0 and passes; the
    truncation then stores a close of 0.

    Contract (R13-SEC2): refused — it has two million decimal places — ``ValueError`` naming the asset, the date and the
    limits; nothing written.
    """
    refusal = await _manual_upsert_refused(owned, [FAUpsert(asset_id=owned.asset_id, prices=[_point(0, "1E-2000000")])], "a manual close of 1E-2000000 EUR")

    _assert_names_the_refusal(refusal, owned.asset_id, [_day(0)])
    stored = await _stored(owned)
    assert not stored, f"the call was refused, yet rows were written: {_describe_prices(stored)}"


@pytest.mark.asyncio
async def test_a_manual_close_beyond_12_integer_digits_in_the_second_chunk_writes_nothing_of_the_first(owned):
    """Red today: accepted, every close stored, 1E+13 included.

    ``bulk_upsert_prices`` commits every ``PRICE_UPSERT_CHUNK_SIZE`` dates. Contract (R13-SEC2): the call is refused
    before any chunk is written, naming the late date; nothing written.
    """
    late = _point(PRICE_UPSERT_CHUNK_SIZE, "1E+13")
    data = [FAUpsert(asset_id=owned.asset_id, prices=[*(_point(offset, "1.5") for offset in range(PRICE_UPSERT_CHUNK_SIZE)), late])]

    refusal = await _manual_upsert_refused(owned, data, f"a history of {PRICE_UPSERT_CHUNK_SIZE + 1} closes whose last one is 1E+13 EUR")

    _assert_names_the_refusal(refusal, owned.asset_id, [late.date])
    stored = await _stored(owned)
    assert not stored, f"the call was refused, yet {len(stored)} rows were written: {_describe_prices(stored)}"


@pytest.mark.asyncio
@pytest.mark.parametrize("typed", [pytest.param("1E+25", id="1E+25"), pytest.param("1E+400", id="1E+400"), pytest.param("1E+1000000", id="1E+1000000")])
async def test_a_manual_volume_beyond_24_integer_digits_is_refused_and_nothing_is_written(owned, typed):
    """Red today: the volume is not checked: 1E+25 is stored, and 1E+400 and 1E+1000000 as a REAL inf (read back
    ``Decimal('Infinity')``, which breaks the responses that carry it).

    Contract (R13-SEC2): ``ValueError`` naming the asset, the date and the limits, 24 among them; nothing written.
    """
    data = [FAUpsert(asset_id=owned.asset_id, prices=[_point(0, "1.5", volume=typed)])]

    refusal = await _manual_upsert_refused(owned, data, f"a manual volume of {typed} beside a close of 1.5 EUR")

    _assert_names_the_refusal(refusal, owned.asset_id, [_day(0)], extra_limits=("24",))
    stored = await _stored(owned)
    assert not stored, f"the call was refused, yet rows were written: {_describe_prices(stored)}"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "typed"),
    [
        pytest.param("close", "999999999999", id="close-12-integer-digits"),
        pytest.param("close", "999999999999.999", id="close-12-integer-digits-15-significant-digits"),
        pytest.param("volume", "1.5", id="volume-fractional"),
        pytest.param("volume", "999999999999999999999999", id="volume-24-integer-digits"),
    ],
)
async def test_guard_a_manual_price_or_volume_at_the_integer_limit_is_accepted(owned, field, typed):
    """Guard: green today and after. 12 integer digits for a price and 24 for a volume are the limit, not past it; a
    volume is a count, read back rounded, so a fractional one stays accepted."""
    point = _point(0, typed) if field == "close" else _point(0, "1.5", **{field: typed})
    try:
        await _manual_upsert([FAUpsert(asset_id=owned.asset_id, prices=[point])])
    except ValueError as refusal:
        pytest.fail(f"a manual {field} of {typed} was refused: {refusal}")

    assert (owned.asset_id, _day(0)) in await _stored(owned), f"a manual {field} of {typed} was not stored"


# --------------------------------------------------------------------------- #
# R13-SEC2 (W-B58): a provider's date that cannot be stored is skipped, the others written
# --------------------------------------------------------------------------- #


def _message_of(result: dict, asset_id: int) -> str:
    """The result message of ``asset_id`` in a ``bulk_upsert_prices`` answer."""
    messages = [row["message"] for row in result["results"] if row["asset_id"] == asset_id]
    assert len(messages) == 1, f"scaffold: the upsert reports {len(messages)} results for asset {asset_id}: {result}"
    return messages[0]


async def _provider_upsert_never_raising(data: list[FAUpsert], story: str) -> dict:
    """``_provider_upsert``; an exception fails the test naming it."""
    try:
        return await _provider_upsert(data)
    except Exception as exc:  # noqa: BLE001 — any exception is the defect under test
        pytest.fail(f"{story} raised {exc!r}: the refresh reports «DB upsert failed» and writes no other date of that chunk, after committing the earlier chunks (R13-SEC2: skip the date, write the others)")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "delivered"),
    [
        pytest.param("close", "1E+13", id="close-1E+13"),
        pytest.param("close", "1E+48", id="close-1E+48"),
        pytest.param("close", "1E+400", id="close-1E+400"),
        pytest.param("close", "1E+1000000", id="close-1E+1000000"),
        pytest.param("close", "1E-13", id="close-1E-13-truncates-to-0"),
        pytest.param("open", "1E+60", id="open-1E+60"),
        pytest.param("high", "1E+400", id="high-1E+400"),
        pytest.param("low", "1E+13", id="low-1E+13"),
        pytest.param("volume", "1E+25", id="volume-1E+25"),
        pytest.param("volume", "1E+400", id="volume-1E+400"),
    ],
)
async def test_a_provider_date_with_an_unstorable_value_is_skipped_and_reported(owned, field, delivered):
    """Red today: a value of 1E+13 (a close, a low), a close of 1E-13 (truncated to 0) or a volume of 1E+25 or 1E+400 (a
    REAL inf) is stored; from 1E+48 a price makes the truncation raise ``InvalidOperation``, which loses the whole chunk.

    Contract (R13-SEC2): the date that cannot be stored (day 1, between two valid ones) is skipped and reported in the
    asset's result message, which contains "rejected" and the date; days 0 and 2 are written; nothing raises.
    """
    bad = _point(1, delivered) if field == "close" else _point(1, "1.5", **{field: delivered})
    data = [FAUpsert(asset_id=owned.asset_id, prices=[_point(0, "1.5"), bad, _point(2, "2.5")])]

    result = await _provider_upsert_never_raising(data, f"a {PROVIDER} refresh delivering a {field} of {delivered} EUR on {_day(1)}")

    closes = {day: row.close for (_asset_id, day), row in (await _stored(owned)).items()}
    assert closes == {_day(0): Decimal("1.5"), _day(2): Decimal("2.5")}, f"a {PROVIDER} refresh delivering a {field} of {delivered} EUR on {_day(1)} stored the closes {closes}: expected the two other days alone (R13-SEC2: skip the date that cannot be stored)"
    message = _message_of(result, owned.asset_id)
    assert "rejected" in message and _day(1).isoformat() in message, f"the result message of asset {owned.asset_id} does not report the skipped date {_day(1)}: {message!r}"


@pytest.mark.asyncio
async def test_a_provider_close_of_1e60_in_the_second_chunk_is_skipped_and_the_first_chunk_kept(owned):
    """Red today: the first chunk is committed, then the truncation of 1E+60 raises ``InvalidOperation`` in the second:
    the refresh fails with the first chunk written and nothing said about it.

    Contract (R13-SEC2): the unstorable date is set aside before any chunk is written: nothing raises, the
    ``PRICE_UPSERT_CHUNK_SIZE`` valid dates are written, the late one is not, and the message reports it.
    """
    late = _point(PRICE_UPSERT_CHUNK_SIZE, "1E+60")
    data = [FAUpsert(asset_id=owned.asset_id, prices=[*(_point(offset, "1.5") for offset in range(PRICE_UPSERT_CHUNK_SIZE)), late])]

    result = await _provider_upsert_never_raising(data, f"a {PROVIDER} history of {PRICE_UPSERT_CHUNK_SIZE + 1} closes whose last one is 1E+60 EUR")

    stored = await _stored(owned)
    assert (owned.asset_id, late.date) not in stored, f"the close of 1E+60 EUR on {late.date} was stored: {stored[(owned.asset_id, late.date)].close}"
    assert len(stored) == PRICE_UPSERT_CHUNK_SIZE, f"{len(stored)} dates were stored: expected the {PRICE_UPSERT_CHUNK_SIZE} valid ones"
    message = _message_of(result, owned.asset_id)
    assert "rejected" in message and late.date.isoformat() in message, f"the result message of asset {owned.asset_id} does not report the skipped date {late.date}: {message!r}"


@pytest.mark.asyncio
async def test_guard_a_provider_close_of_12_integer_digits_is_stored_truncated(owned):
    """Guard: green today and after. 999999999999.9999999 has 12 integer digits, the limit: stored, cut to 15 significant
    digits (``ROUND_DOWN``), 999999999999.999, and the message reports no rejection."""
    result = await _provider_upsert_never_raising([FAUpsert(asset_id=owned.asset_id, prices=[_point(0, "999999999999.9999999")])], f"a {PROVIDER} close of 999999999999.9999999 EUR")

    row = (await _stored(owned)).get((owned.asset_id, _day(0)))
    assert row is not None and row.close == Decimal("999999999999.999"), f"a {PROVIDER} close of 999999999999.9999999 EUR stores {row.close if row else None}: expected 999999999999.999"
    assert "rejected" not in _message_of(result, owned.asset_id)


# --------------------------------------------------------------------------- #
# R13-SEC2 (W-B58): the current price, persisted by get_current_prices_bulk
# --------------------------------------------------------------------------- #


@dataclass
class _Assigned:
    """The PEPE asset assigned, for one test, to a provider double of the test's own: its code, the assignment's id, the
    current value the double answers (a ``float`` is built without validation, as a plugin that skips the schema), and how
    many times it was asked for it."""

    code: str
    assignment_id: int
    quote: object = Decimal("1")
    current_calls: int = 0


class _QuoteDouble(AssetSourceProvider):
    """The provider of the current-price tests: never on the network, it answers ``assigned.quote`` in EUR, as of today."""

    test_only = True

    def __init__(self, assigned: _Assigned):
        self.assigned = assigned

    @property
    def provider_code(self) -> str:
        return self.assigned.code

    @property
    def provider_name(self) -> str:
        return "R13-SEC2 current-price double"

    @property
    def test_cases(self) -> list[dict]:
        return []

    @property
    def test_search_query(self) -> str | None:
        return None

    def validate_params(self, params: dict | None) -> None:
        """Any params will do."""

    async def get_current_value(self, identifier, identifier_type, provider_params=None) -> FACurrentValue:
        self.assigned.current_calls += 1
        quote = self.assigned.quote
        if isinstance(quote, float):
            return FACurrentValue.model_construct(value=quote, currency="EUR", as_of_date=date.today(), source=self.provider_code)
        return FACurrentValue(value=quote, currency="EUR", as_of_date=date.today(), source=self.provider_code)

    async def get_history_value(self, identifier, identifier_type, provider_params, start_date, end_date) -> FAHistoricalData:
        raise AssertionError("the R13-SEC2 current-price double is never asked for a history")


@pytest_asyncio.fixture
async def assigned(owned: _Owned, monkeypatch: pytest.MonkeyPatch):
    """The PEPE asset assigned to a ``_QuoteDouble`` behind a code of the test's own, which the registry hands out; the
    assignment, and the prices and events written meanwhile, dropped at teardown."""
    code = f"r13_{uuid.uuid4().hex[:12]}"
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        assignment = AssetProviderAssignment(asset_id=owned.asset_id, provider_code=code, identifier=f"R13-{uuid.uuid4().hex[:8]}", identifier_type=ProviderInputType.TICKER)
        session.add(assignment)
        await session.commit()
        state = _Assigned(code=code, assignment_id=assignment.id)
    original = AssetProviderRegistry.get_provider_instance

    def get_provider_instance(_cls, provider_code, **kwargs):
        return _QuoteDouble(state) if provider_code == code else original(provider_code, **kwargs)

    monkeypatch.setattr(AssetProviderRegistry, "get_provider_instance", classmethod(get_provider_instance))
    yield state
    await _wipe(owned)
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        await session.execute(delete(AssetProviderAssignment).where(AssetProviderAssignment.id == state.assignment_id))
        await session.commit()


async def _seed_todays_price(asset_id: int) -> None:
    """A price row of today for ``asset_id``: open 9, high 11, low 8, close 10, volume 100 EUR."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        session.add(PriceHistory(asset_id=asset_id, date=date.today(), open=Decimal("9"), high=Decimal("11"), low=Decimal("8"), close=Decimal("10"), volume=Decimal("100"), currency="EUR", source_plugin_key="MANUAL"))
        await session.commit()


async def _todays_row(asset_id: int) -> tuple | None:
    """Today's price row of ``asset_id`` as the file holds it — (open, high, low, close, volume) — read with raw SQL, past
    the column types, so a REAL inf or 1e60 is seen as the float it is; None without a row."""
    async with AsyncSession(get_async_engine()) as session:
        row = (await session.execute(text("SELECT open, high, low, close, volume FROM price_history WHERE asset_id = :asset_id AND date = :day"), {"asset_id": asset_id, "day": date.today().isoformat()})).one_or_none()
    return None if row is None else tuple(row)


async def _current_price(asset_id: int, story: str):
    """The current-price path (``get_current_prices_bulk``) for one asset: its item; an exception fails the test naming it."""
    try:
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            (item,) = await AssetSourceManager.get_current_prices_bulk([asset_id], session)
    except Exception as exc:  # noqa: BLE001 — any exception is the defect under test
        pytest.fail(f"{story}: get_current_prices_bulk raised {exc!r}: GET /assets/prices/current answers 500 (R13-SEC2)")
    return item


@pytest.mark.asyncio
@pytest.mark.parametrize("existing", [pytest.param(False, id="no-row-today"), pytest.param(True, id="a-row-today")])
@pytest.mark.parametrize("quote", [pytest.param(Decimal("1E+400"), id="1E+400"), pytest.param(Decimal("1E+60"), id="1E+60")])
async def test_an_unstorable_current_quote_is_not_persisted(owned, assigned, quote, existing):
    """Red before W-B58: the path wrote ``Decimal(str(value))`` as it came — 1E+400 as a REAL inf, 1E+60 as a REAL 1e60 —
    creating today's row with it or overwriting its high and close; every later read of that row raised.

    Contract (R13-SEC2): not persisted — today's row neither created nor changed (open, high, low, close, volume as the
    file holds them) — and nothing raises. The barrier is the provider's call, not the item's source: after W-B62 an
    unstorable quote is no longer served, and the item falls back to the database.
    """
    if existing:
        await _seed_todays_price(owned.asset_id)
    before = await _todays_row(owned.asset_id)
    assigned.quote = quote

    await _current_price(owned.asset_id, f"a current quote of {quote} EUR")

    assert assigned.current_calls >= 1, f"barrier: the provider double was never asked for the current value ({assigned.current_calls} calls), so nothing proves the quote reached the path"
    after = await _todays_row(owned.asset_id)
    assert after == before, f"R13-SEC2: a current quote of {quote} EUR changed today's row (open, high, low, close, volume): before {before}, after {after}"


@pytest.mark.asyncio
@pytest.mark.parametrize("existing", [pytest.param(False, id="no-row-today"), pytest.param(True, id="a-row-today")])
async def test_guard_a_float_inf_current_quote_is_never_persisted(owned, assigned, existing):
    """Guard: green today and after. A double inf never becomes an item — ``FACurrentPriceItem`` refuses a non-finite
    value — so the path falls back to the stored price, or to an error, and persists nothing."""
    if existing:
        await _seed_todays_price(owned.asset_id)
    before = await _todays_row(owned.asset_id)
    assigned.quote = float("inf")

    item = await _current_price(owned.asset_id, "a current quote of float('inf')")

    assert not (item.source or "").startswith("provider:"), f"barrier: a float inf came out of the provider path as an item: {item!r}"
    after = await _todays_row(owned.asset_id)
    assert after == before, f"a current quote of float('inf') changed today's row: before {before}, after {after}"


@pytest.mark.asyncio
async def test_a_valid_current_quote_is_persisted_truncated_like_the_history(owned, assigned):
    """Red today: written as it comes: 65432.1234567890999 becomes the double 65432.1234567891, read back 65432.1234567891.

    Contract (R13-SEC2): truncated like the history, 12 decimals then 15 significant digits, ``ROUND_DOWN``: today's new
    row opens, highs, lows and closes at 65432.123456789.
    """
    assigned.quote = Decimal("65432.1234567890999")

    item = await _current_price(owned.asset_id, "a current quote of 65432.1234567890999 EUR")

    assert item.source == f"provider:{assigned.code}", f"barrier: the item did not come from the provider double ({item!r})"
    row = (await _stored(owned)).get((owned.asset_id, date.today()))
    assert row is not None, "a valid current quote of 65432.1234567890999 EUR was not persisted as today's row"
    expected = Decimal("65432.123456789")
    found = (row.open, row.high, row.low, row.close)
    assert found == (expected,) * 4, f"a current quote of 65432.1234567890999 EUR is stored as (open, high, low, close) = {found}: expected {expected} for each (12 decimals then 15 significant digits, ROUND_DOWN)"


# --------------------------------------------------------------------------- #
# R13-SEC2 (W-B58): events past the integer digits
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
@pytest.mark.parametrize("amount", [pytest.param("1E+13", id="1E+13"), pytest.param("1E+60", id="1E+60")])
async def test_a_manual_event_beyond_12_integer_digits_is_refused_and_nothing_is_written(owned, amount):
    """Red today: the check counts decimals and significant digits only, so the dividend is accepted — 1E+60 stored as a
    REAL 1e60.

    Contract (R13-SEC2): ``EVENT_TOO_MANY_DIGITS``, the details gaining ``max_integer_digits`` 12 beside the existing
    maxima (6 decimal places, 15 significant digits) and naming event 1; nothing written, the valid event of the item
    included. Both values are inside the exponent bound of ``Currency`` (±100), so they reach the store's refusal; 1E+400,
    past it, is refused before, by the schema (R13-SEC7-3): the next test.
    """
    data = [_event_item(owned.asset_id, [_event(0, "DIVIDEND", "1.5"), _event(1, "DIVIDEND", amount)])]

    refusal = await _upsert_events_refused(owned, data, f"a PEPE dividend of {amount} EUR (beyond 12 integer digits)")

    assert refusal.error_code == "EVENT_TOO_MANY_DIGITS", f"refused with {refusal.error_code}: {refusal.message}"
    details = refusal.details or {}
    maxima = {key: details.get(key) for key in ("max_decimal_places", "max_significant_digits", "max_integer_digits")}
    assert maxima == {"max_decimal_places": 6, "max_significant_digits": 15, "max_integer_digits": 12}, f"the refusal's details give the maxima {maxima}: expected 6 decimal places, 15 significant digits, 12 integer digits ({details})"
    named = [(event.get("event_index"), event.get("date")) for event in details.get("events", [])]
    assert named == [(1, _day(1).isoformat())], f"the refusal names the events {named}: expected event 1, on {_day(1)} ({details})"
    rows = await _stored_events(owned)
    assert not rows, f"the request was refused, yet events were written: {_describe_events(rows)}"


@pytest.mark.asyncio
async def test_a_manual_event_past_the_exponent_bound_is_refused_by_the_schema_and_nothing_is_written(owned):
    """R13-SEC7-3: a dividend of 1E+400 EUR (``adjusted()`` 400, past the ±100 of ``Currency``) never reaches the store.

    Contract: the item, built as the endpoint validates its body (``_event_item``), is refused by the schema — exactly one
    error, on ``events.1.value.amount``, ``value_error``, its message naming the exponent: ``POST /assets/events`` answers
    422 before any work; nothing else raises; nothing is written for the asset, the valid event of the item included.
    Before the bound, the request reached the store and was refused with ``EVENT_TOO_MANY_DIGITS`` (W-B58).
    """
    events = [_event(0, "DIVIDEND", "1.5"), _event(1, "DIVIDEND", "1E+400")]

    try:
        _event_item(owned.asset_id, events)
    except ValidationError as exc:
        refusal = exc
    except Exception as exc:  # noqa: BLE001 — any other exception is the defect under test
        pytest.fail(f"a PEPE dividend of 1E+400 EUR raised {exc!r} instead of the schema's ValidationError: POST /assets/events answers 500, not 422 (R13-SEC7-3)")
    else:
        pytest.fail("a PEPE dividend of 1E+400 EUR passed the schema: its exponent, 400, is past the ±100 of Currency, so POST /assets/events must answer 422 before any work (R13-SEC7-3)")

    errors = [(".".join(str(part) for part in error["loc"]), error["type"]) for error in refusal.errors()]
    assert errors == [("events.1.value.amount", "value_error")], f"R13-SEC7-3: the schema must refuse exactly the dividend's amount, value_error on events.1.value.amount; it answered {errors}"
    message = refusal.errors()[0]["msg"]
    assert "exponent" in message.lower(), f"R13-SEC7-3: the refusal must name the exponent; it reads {message!r}"
    rows = await _stored_events(owned)
    assert not rows, f"the request was refused, yet events were written: {_describe_events(rows)}"


@pytest.mark.asyncio
async def test_the_events_endpoint_answers_400_for_an_event_beyond_12_integer_digits(owned):
    """Red today: 200, the dividend of 1E+13 EUR stored.

    Contract (R13-SEC2): 400, ``detail.error_code`` EVENT_TOO_MANY_DIGITS, ``detail.params.max_integer_digits`` 12,
    nothing written. The route function is called as FastAPI calls it, minus HTTP, the caller ``_CALLER``.
    """
    item = _event_item(owned.asset_id, [_event(0, "DIVIDEND", "1E+13")])
    answer: HTTPException | None = None
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        try:
            await events_api.upsert_events_bulk([item], session=session, _current_user=_CALLER)
        except HTTPException as refusal:
            answer = refusal
    if answer is None:
        pytest.fail(f"POST /assets/events saved a PEPE dividend of 1E+13 EUR (200): it reads back as {_describe_events(await _stored_events(owned))}, instead of answering 400 EVENT_TOO_MANY_DIGITS")

    detail = answer.detail if isinstance(answer.detail, dict) else {}
    assert (answer.status_code, detail.get("error_code")) == (400, "EVENT_TOO_MANY_DIGITS"), f"POST /assets/events answers {answer.status_code} {answer.detail!r} to a dividend of 1E+13 EUR: expected 400 EVENT_TOO_MANY_DIGITS"
    assert (detail.get("params") or {}).get("max_integer_digits") == 12, f"the refusal's params do not give max_integer_digits 12: {detail}"
    rows = await _stored_events(owned)
    assert not rows, f"the request was refused, yet events were written: {_describe_events(rows)}"


@pytest.mark.asyncio
async def test_guard_a_manual_event_of_12_integer_digits_is_stored(owned):
    """Guard: green today and after. A dividend of 999999999999 EUR has 12 integer digits, the limit: stored, and read back."""
    try:
        await _upsert_events([_event_item(owned.asset_id, [_event(0, "DIVIDEND", "999999999999")])])
    except AssetSourceError as refusal:
        pytest.fail(f"a dividend of 999999999999 EUR was refused: {refusal.error_code} {refusal.message}")

    rows = await _stored_events(owned)
    assert [(row.asset_id, row.date, row.value) for row in rows] == [(owned.asset_id, _day(0), Decimal("999999999999"))], f"a dividend of 999999999999 EUR reads back as {_describe_events(rows)}"


@pytest.mark.asyncio
@pytest.mark.parametrize("amount", [pytest.param("1E+400", id="1E+400"), pytest.param("1E+60", id="1E+60"), pytest.param("1E+13", id="derived-1E+13")])
async def test_a_provider_event_that_cannot_be_stored_is_dropped_and_the_others_are_written(owned, assigned, amount):
    """Red today: ``_upsert_asset_events`` checks nothing: the dividend of ``amount`` EUR is written (1E+400 as a REAL inf).

    Contract (R13-SEC2): of a provider's events, the one whose value cannot be stored (day 1) is dropped, the valid ones of
    the same call (days 0 and 2) are written under the assignment, nothing raises. 1E+13 (13 integer digits, past the 12
    of ``AssetEvent.value``) is derived from the same rule.
    """
    events = [
        {"date": _day(0), "type": "DIVIDEND", "value": {"code": "EUR", "amount": "1.5"}},
        {"date": _day(1), "type": "DIVIDEND", "value": {"code": "EUR", "amount": amount}},
        {"date": _day(2), "type": "INTEREST", "value": {"code": "EUR", "amount": "2.25"}},
    ]

    try:
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            await EventStoreOperations._upsert_asset_events(session, owned.asset_id, events, assigned.assignment_id, "EUR")
    except Exception as exc:  # noqa: BLE001 — any exception is the defect under test
        pytest.fail(f"the provider events of a refresh, one of them a dividend of {amount} EUR, raised {exc!r}: the refresh reports «Event upsert failed» and keeps none of them (R13-SEC2: drop that one, write the others)")

    rows = await _stored_events(owned)
    written = [(row.date, str(row.type), row.value, row.provider_assignment_id) for row in rows]
    expected = [(_day(0), "DIVIDEND", Decimal("1.5"), assigned.assignment_id), (_day(2), "INTEREST", Decimal("2.25"), assigned.assignment_id)]
    assert written == expected, f"the provider events, one of them a dividend of {amount} EUR on {_day(1)}, were written as {_describe_events(rows)}: expected the two others alone"


@pytest.mark.asyncio
async def test_a_provider_event_the_schema_refuses_is_dropped_and_the_others_are_written(owned, assigned):
    """R13-SEC7-3: a provider event whose value is a number of 5 000 digits (``adjusted()`` 4 999, past the ±100 of
    ``Currency``) is refused by the schema as ``_storable_events`` parses it. Before the cure that parse raised out of
    ``_upsert_asset_events``, and the refresh lost every event of the call.

    Contract: that event (day 1) is dropped, the two others (days 0 and 2) are written under the assignment, nothing
    raises. A message here gives the value's length, never the value.
    """
    huge = "9" * 5000
    events = [
        {"date": _day(0), "type": "DIVIDEND", "value": {"code": "EUR", "amount": "1.5"}},
        {"date": _day(1), "type": "DIVIDEND", "value": {"code": "EUR", "amount": huge}},
        {"date": _day(2), "type": "INTEREST", "value": {"code": "EUR", "amount": "2.25"}},
    ]
    story = f"the provider events of a refresh, one of them a dividend of a {len(huge)}-digit number of EUR on {_day(1)}"

    try:
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            await EventStoreOperations._upsert_asset_events(session, owned.asset_id, events, assigned.assignment_id, "EUR")
    except Exception as exc:  # noqa: BLE001 — any exception is the defect under test
        pytest.fail(f"{story}, raised {type(exc).__name__} ({str(exc)[:160]}…): the refresh reports «Event upsert failed» and keeps none of them (R13-SEC7-3: drop that one, write the others)")

    rows = await _stored_events(owned)
    written = [(row.date, str(row.type), row.value, row.provider_assignment_id) for row in rows]
    expected = [(_day(0), "DIVIDEND", Decimal("1.5"), assigned.assignment_id), (_day(2), "INTEREST", Decimal("2.25"), assigned.assignment_id)]
    assert written == expected, f"{story}, were written as {_describe_events(rows)}: expected the two others alone"


# --------------------------------------------------------------------------- #
# W-B68: a provider's event value stored as the column keeps it, so what is read back is what was written
# --------------------------------------------------------------------------- #

#: An event sent through event_store.py's own logger inside every W-B68 capture, then looked for.
_WB68_BARRIER = "W-B68 capture barrier"

#: Values within every limit of ``AssetEvent.value`` for the W-B68 guards — (type, value delivered, the form it reads back
#: in today, id) —: 1.5, 6 decimals, 15 significant digits with the 12 integer digits, a SPLIT's ratio of 2.
_WB68_FITTING = [
    ("DIVIDEND", "1.5", "1.500000", "dividend-1.5"),
    ("DIVIDEND", "0.123456", "0.123456", "dividend-0.123456-6-decimals"),
    ("DIVIDEND", "123456789012.123", "123456789012.123000", "dividend-123456789012.123-15-significant-digits"),
    ("SPLIT", "2", "2.000000", "split-ratio-2"),
]


@dataclass(frozen=True)
class _Held:
    """An event row as the refresh's session holds it right after the write."""

    id: int
    day: date
    kind: str
    value: Decimal


def _provider_event(offset: int, kind: str, amount: str) -> dict:
    """One event as a provider delivers it to a refresh (``FAHistoricalData.events``), in the asset's currency."""
    return {"date": _day(offset), "type": kind, "value": {"code": "EUR", "amount": amount}}


async def _refresh_events(owned: _Owned, assigned: _Assigned, events: list[dict], story: str) -> tuple[dict[tuple[date, str], _Held], list[dict]]:
    """What a refresh does with its provider's events (``refresh.py``: ``_upsert_asset_events`` under the assignment,
    committed slice by slice). Returns the rows its session wrote, by (date, type), as that session holds them right after
    the write, and the log events captured meanwhile.

    The rows are held from the session's flushes (``before_flush``: its new and changed events), so they are the very
    objects written, never reloaded: a row nothing holds leaves the session's identity map, and a query of the same session
    would read the database instead. A barrier event, sent through ``event_store``'s own logger inside the capture, proves
    the capture live. An exception fails the test naming it: the refresh would report «Event upsert failed».
    """
    held: dict[int, AssetEvent] = {}

    def hold(session, _flush_context, _instances) -> None:
        for row in (*session.new, *session.dirty):
            if isinstance(row, AssetEvent):
                held.setdefault(id(row), row)

    with capture_logs() as captured:
        event_store.logger.warning(_WB68_BARRIER)
        try:
            async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
                listen(session.sync_session, "before_flush", hold)
                await EventStoreOperations._upsert_asset_events(session, owned.asset_id, events, assigned.assignment_id, "EUR")
                written = {(row.date, str(row.type)): _Held(row.id, row.date, str(row.type), row.value) for row in held.values()}
        except Exception as exc:  # noqa: BLE001 — any exception is the defect under test
            pytest.fail(f"{story}: _upsert_asset_events raised {exc!r}: the refresh reports «Event upsert failed» and keeps none of the provider's events (W-B68: cut the values, drop what cannot be kept, write the others)")
    assert any(entry.get("event") == _WB68_BARRIER for entry in captured), f"barrier: the log capture saw no event of event_store.py's logger: {captured}"
    return written, captured


async def _read_back(owned: _Owned, offset: int, kind: str) -> list[tuple[Decimal, int | None]]:
    """The (value, provider assignment) of every event of the PEPE asset on day ``offset`` of type ``kind``, read back by a
    fresh query through the column's type, as the neighbours read a stored event (``_stored_events``)."""
    return [(row.value, row.provider_assignment_id) for row in await _stored_events(owned) if (row.asset_id, row.date, str(row.type)) == (owned.asset_id, _day(offset), kind)]


async def _seed_provider_dividend(owned: _Owned, assigned: _Assigned, offset: int, amount: str) -> int:
    """A dividend of ``amount`` EUR on day ``offset``, stored under the assignment as an earlier refresh left it; its id."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        row = AssetEvent(asset_id=owned.asset_id, date=_day(offset), type=AssetEventType.DIVIDEND, value=Decimal(amount), currency="EUR", provider_assignment_id=assigned.assignment_id)
        session.add(row)
        await session.commit()
        return row.id


def _flat(value: object) -> str:
    """A log event as plain text — a date in its ISO form, containers flattened — so what it names is found whatever form
    the logger was given it in."""
    if isinstance(value, dict):
        return " ".join(f"{key}={_flat(item)}" for key, item in value.items())
    if isinstance(value, list | tuple | set):
        return " ".join(_flat(item) for item in value)
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _split_ratio_warnings(captured: list[dict], offset: int) -> list[dict]:
    """The warnings, and worse, among ``captured`` that name the SPLIT of day ``offset`` for its ratio — its date and the
    words split and ratio — whatever their text; the barrier left out. A drop for the digits (W-B58) names no ratio."""
    day = _day(offset).isoformat()

    def names_the_ratio(entry: dict) -> bool:
        flat = _flat(entry).lower()
        return day in flat and re.search(r"\bsplit", flat) is not None and re.search(r"\bratios?\b", flat) is not None

    return [entry for entry in captured if entry.get("log_level") in ("warning", "error", "critical") and entry.get("event") != _WB68_BARRIER and names_the_ratio(entry)]


def _names_the_asset(entry: dict, asset_id: int) -> bool:
    """Whether a log event names asset ``asset_id``: the id right after the word asset — a field ``asset_id``, or «asset 12»
    in its text. A bare number is no name: with the small ids of a fresh lane, «count=1» is not asset 1."""
    return re.search(r"\basset(?:[ _]?id)?\W{0,3}" + str(asset_id) + r"(?!\d)", _flat(entry), re.IGNORECASE) is not None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("delivered", "expected", "before"),
    [
        pytest.param("784.0774475", "784.077447", "784.077448", id="784.0774475"),
        pytest.param("0.1234567", "0.123456", "0.123457", id="0.1234567"),
    ],
)
async def test_wb68_a_provider_event_value_past_6_decimals_is_stored_cut_at_6(owned, assigned, delivered, expected, before):
    """Red today: ``_storable_events`` lets the dividend through as it comes, and ``RealDecimal(18, 6)`` reads the double
    back rounded half-even at 6 decimals: 784.0774475 reads back 784.077448 and 0.1234567 reads back 0.123457 (``before``).

    Contract (W-B68): cut as a provider price is cut (``storable_value``), ROUND_DOWN at the 6 decimals of
    ``AssetEvent.value``: stored under the assignment and read back as ``expected``, 784.077447 and 0.123456.
    """
    story = f"a provider dividend of {delivered} EUR on {_day(0)}"

    await _refresh_events(owned, assigned, [_provider_event(0, "DIVIDEND", delivered)], story)

    found = await _read_back(owned, 0, "DIVIDEND")
    cut = [(Decimal(expected), assigned.assignment_id)]
    assert found == cut, f"W-B68: {story} reads back as {found} (value, assignment): expected {expected} under assignment {assigned.assignment_id}, cut ROUND_DOWN at the 6 decimals AssetEvent.value keeps, as a provider price is; before the cure it read back {before}, the double rounded on read"


@pytest.mark.asyncio
async def test_wb68_a_provider_event_value_past_15_significant_digits_is_stored_cut_at_15(owned, assigned):
    """Red today: a dividend of 123456789012.123999 EUR — 12 integer digits, the limit, and 6 decimals, but 18 significant
    digits — is written as it comes, and the double it becomes reads back 123456789012.124000: rounded up, not cut.

    Contract (W-B68): ROUND_DOWN at 6 decimals, then at 15 significant digits, what a REAL gives back: stored and read back
    123456789012.123. The backlog's 123456789012.123456 cannot be red here: its 16th significant digit is a 4, so the read's
    rounding already lands on the cut value today; it is red in ``test_wb68_what_a_refresh_writes_is_what_is_read_back``.
    """
    delivered, expected, before = "123456789012.123999", "123456789012.123", "123456789012.124000"
    story = f"a provider dividend of {delivered} EUR on {_day(0)}"

    await _refresh_events(owned, assigned, [_provider_event(0, "DIVIDEND", delivered)], story)

    found = await _read_back(owned, 0, "DIVIDEND")
    cut = [(Decimal(expected), assigned.assignment_id)]
    assert found == cut, f"W-B68: {story} reads back as {found} (value, assignment): expected {expected} under assignment {assigned.assignment_id}, cut ROUND_DOWN at 15 significant digits; before the cure it read back {before}, whatever the REAL made of the 18 digits written"


@pytest.mark.asyncio
async def test_wb68_a_provider_split_whose_ratio_cuts_to_0_is_dropped_the_others_written_and_one_warning_names_it(owned, assigned):
    """Red today: a SPLIT of ratio 0.0000001 is above 0, so X-R47 lets it through, and it is written as it comes: it reads
    back 0.000000, the very ratio X-R47 drops (linked to a transaction, a ratio of 0 made the portfolio engine raise).

    Contract (W-B68): the ratio is judged as the column keeps it, cut ROUND_DOWN at 6 decimals: 0, so the SPLIT (day 1) is
    dropped as an invalid split — no row on its key — and one warning names it (its date, the words split and ratio) and
    the asset; the other events of the call — a dividend (day 0), an interest (day 2), a SPLIT of 2 (day 3) — are written
    under the assignment; nothing raises.
    """
    events = [_provider_event(0, "DIVIDEND", "1.5"), _provider_event(1, "SPLIT", "0.0000001"), _provider_event(2, "INTEREST", "2.25"), _provider_event(3, "SPLIT", "2")]
    story = f"a refresh delivering a SPLIT of ratio 0.0000001 on {_day(1)} beside a dividend, an interest and a SPLIT of 2"

    _written, captured = await _refresh_events(owned, assigned, events, story)

    split = await _read_back(owned, 1, "SPLIT")
    assert not split, f"W-B68: {story} stored that SPLIT, read back as {split} (value, assignment): a ratio of 0, the very case X-R47 drops; expected it dropped, its ratio judged once cut to the 6 decimals AssetEvent.value keeps"
    rows = await _stored_events(owned)
    written = sorted((row.date, str(row.type), row.value, row.provider_assignment_id) for row in rows)
    expected = [(_day(0), "DIVIDEND", Decimal("1.5"), assigned.assignment_id), (_day(2), "INTEREST", Decimal("2.25"), assigned.assignment_id), (_day(3), "SPLIT", Decimal("2"), assigned.assignment_id)]
    assert written == expected, f"{story} wrote {_describe_events(rows)}: expected the three others alone"
    warnings = _split_ratio_warnings(captured, 1)
    assert len(warnings) == 1, f"{story} logged {len(warnings)} warning(s) naming the SPLIT of {_day(1)} and its ratio: expected one, so the operator learns the provider's split was dropped as invalid: {warnings}"
    assert _names_the_asset(warnings[0], owned.asset_id), f"{story}: the warning about the dropped SPLIT of {_day(1)} does not name asset {owned.asset_id}: {warnings[0]}"


@pytest.mark.asyncio
@pytest.mark.parametrize("existing", [pytest.param(False, id="inserted"), pytest.param(True, id="updated-in-place")])
@pytest.mark.parametrize(
    ("delivered", "before"),
    [
        pytest.param("784.0774475", "784.077448", id="784.0774475"),
        pytest.param("0.1234567", "0.123457", id="0.1234567"),
        pytest.param("1.23456789", "1.234568", id="1.23456789"),
        pytest.param("123456789012.123456", "123456789012.123000", id="123456789012.123456"),
    ],
)
async def test_wb68_what_a_refresh_writes_is_what_is_read_back(owned, assigned, delivered, before, existing):
    """Red today: the refresh's session holds the dividend as delivered, 784.0774475, while a fresh query reads the row back
    784.077448 (``before``): the row says one value to the session that wrote it and another to every later read. The
    backlog's 123456789012.123456 reads back 123456789012.123: there the read is right, and the row written is not.

    Contract (W-B68): the value is cut before it is written, so the row the session holds right after the write equals, as a
    ``Decimal``, the row a fresh query reads back; as a new row, and as the provider's row of the key updated in place.
    """
    seeded = await _seed_provider_dividend(owned, assigned, 0, "1.5") if existing else None
    story = f"a provider dividend of {delivered} EUR on {_day(0)}" + (f", over the provider's stored dividend {seeded} of 1.5 EUR" if seeded is not None else "")

    written, _captured = await _refresh_events(owned, assigned, [_provider_event(0, "DIVIDEND", delivered)], story)

    held = written.get((_day(0), "DIVIDEND"))
    assert held is not None, f"barrier: {story}: the refresh's session wrote no dividend on {_day(0)}: {sorted(written)}"
    assert seeded is None or held.id == seeded, f"barrier: {story}: the refresh wrote the row {held.id} instead of updating the stored dividend {seeded} in place"
    read = [value for value, _assignment in await _read_back(owned, 0, "DIVIDEND")]
    assert read == [held.value], f"W-B68: {story} is held by the refresh's session as {held.value} right after the write, and read back as {read}: what is read back must be what was written (before the cure: written {delivered}, read back {before})"


@pytest.mark.asyncio
@pytest.mark.parametrize(("kind", "delivered", "form"), [pytest.param(kind, delivered, form, id=name) for kind, delivered, form, name in _WB68_FITTING])
async def test_wb68_guard_a_provider_event_value_that_fits_reads_back_unchanged(owned, assigned, kind, delivered, form):
    """Guard: green today and after. A value within every limit of ``AssetEvent.value`` — 1.5, 0.123456 (6 decimals),
    123456789012.123 (15 significant digits, 12 integer digits), a SPLIT's ratio of 2 — is stored under the assignment and
    read back unchanged, in today's form (``form``): nothing to cut, and a SPLIT of 2 is a valid split, never dropped."""
    story = f"a provider {kind} of {delivered} on {_day(0)}"

    await _refresh_events(owned, assigned, [_provider_event(0, kind, delivered)], story)

    found = await _read_back(owned, 0, kind)
    assert found == [(Decimal(delivered), assigned.assignment_id)], f"{story} reads back as {found} (value, assignment): expected {delivered} under assignment {assigned.assignment_id}"
    assert str(found[0][0]) == form, f"{story} reads back as {found[0][0]}: expected {form}, today's form"


@pytest.mark.asyncio
@pytest.mark.parametrize(("kind", "delivered"), [pytest.param(kind, delivered, id=name) for kind, delivered, _form, name in _WB68_FITTING])
async def test_wb68_guard_a_provider_event_value_that_fits_keeps_its_form_in_the_refresh_session(owned, assigned, kind, delivered):
    """Guard: green today and after; the clause «a value that already fits keeps its form» of the W-B68 contract. The row the
    refresh's session holds right after the write carries the value as the provider gave it, form included: 1.5 stays 1.5
    and a ratio of 2 stays 2, never the 1.500000 and 2.000000 that ``truncate_to_db_precision`` (so ``storable_value``)
    makes of them. The cut is for a value that does not fit."""
    story = f"a provider {kind} of {delivered} on {_day(0)}"

    written, _captured = await _refresh_events(owned, assigned, [_provider_event(0, kind, delivered)], story)

    held = written.get((_day(0), kind))
    assert held is not None, f"barrier: {story}: the refresh's session wrote no {kind} on {_day(0)}: {sorted(written)}"
    assert str(held.value) == delivered, f"W-B68: {story} is held by the refresh's session as {held.value}: a value that already fits keeps its form, {delivered}"


# --------------------------------------------------------------------------- #
# W-B60: an event value reads back exactly, with 6 decimals
# --------------------------------------------------------------------------- #


async def _queried_values(owned: _Owned, first: int, last: int) -> list[str]:
    """The values of the PEPE asset's events from day ``first`` to day ``last``, as the events query answers them
    (``query_events_bulk``, what ``POST /assets/events/query`` calls), in date order, each as its text: the form included."""
    request = FAEventQueryItem(asset_id=owned.asset_id, date_range=DateRangeModel(start=_day(first), end=_day(last)))
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        (result,) = await AssetSourceManager.query_events_bulk([request], session)
    return [str(event.value.amount) for event in result.events]


async def _upsert_events_within_the_limits(data: list[FAEventUpsert], story: str) -> None:
    """``_upsert_events`` for events within every limit: a refusal fails the test as a broken scaffold."""
    try:
        await _upsert_events(data)
    except AssetSourceError as refusal:
        pytest.fail(f"scaffold: {story}, within every limit of a manual event, was refused: {refusal.error_code} {refusal.message}")


@pytest.mark.asyncio
async def test_a_manual_event_value_of_15_significant_digits_reads_back_exactly_through_the_events_query(owned):
    """Red today: ``AssetEvent.value`` is a plain ``Numeric(18, 6)``, read through ``'%.6f'`` of the stored double: a
    dividend of 12345678901.2345 EUR (4 decimals, 15 significant digits, 11 integer digits) reads back 12345678901.234501.

    Contract (W-B60): ``RealDecimal(18, 6)``: the events query answers 12345678901.234500, the value typed with 6 decimals.
    """
    story = "a PEPE dividend of 12345678901.2345 EUR"
    await _upsert_events_within_the_limits([_event_item(owned.asset_id, [_event(0, "DIVIDEND", "12345678901.2345")])], story)

    queried = await _queried_values(owned, 0, 0)

    assert queried == ["12345678901.234500"], f"W-B60: {story} reads back through the events query as {queried}: expected ['12345678901.234500'], the value typed with 6 decimals (stored: {_describe_events(await _stored_events(owned))})"


@pytest.mark.asyncio
async def test_guard_a_manual_event_value_that_reads_well_today_keeps_its_form_through_the_events_query(owned):
    """Guard: green today and after. Dividends of 1.5 and 0.000001 EUR read back through the events query as 1.500000 and
    0.000001, the form ``Numeric(18, 6)`` gives them today."""
    story = "PEPE dividends of 1.5 and 0.000001 EUR"
    await _upsert_events_within_the_limits([_event_item(owned.asset_id, [_event(0, "DIVIDEND", "1.5"), _event(1, "DIVIDEND", "0.000001")])], story)

    queried = await _queried_values(owned, 0, 1)

    assert queried == ["1.500000", "0.000001"], f"W-B60: {story} read back through the events query as {queried}: expected ['1.500000', '0.000001'], today's form"

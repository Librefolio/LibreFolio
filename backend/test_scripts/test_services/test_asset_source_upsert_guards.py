"""Integrity guards and identifier filters of AssetSourceManager.

Isolation: WRITE_GLOBAL. ``Asset`` and ``PriceHistory`` carry no ``user_id``, so
the asset created here and the price rows written against it are visible to every
concurrently running test. The module fixture creates exactly one asset with a
unique display name and deletes it -- together with every price row it produced --
in teardown, so nothing survives the unit. X-R65's and X-R71's sections add a second
asset for some tests (``xr65_second_asset``), and X-R71's twelve for one
(``xr71_assets``), removed the same way.

Why these tests exist. ``bulk_upsert_prices`` implements a deliberately subtle
policy that was written in response to a production incident, and none of its
rejection paths were being executed:

* a **fresh provider OHLC bundle** that is internally inconsistent (``low > high``,
  or a close outside ``[low, high]``) is rejected per date, and the rejected dates
  are named in the result message so the user can see which candles were dropped;
* a **close-only update** landing on a date that already holds a flat candle must
  *not* be rejected -- the stored bounds are widened around the new close instead.
  This is the justETF / scheduled-investment case called out in the source comment.

Those two branches are the difference between "the price got in" and "the price
silently vanished", so they are pinned here rather than left to a provider test.
The behaviour is asserted exactly as it is today: this unit is a lock, not a
proposal.
"""

import asyncio
import json
import sys
import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from pydantic import ValidationError

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

# Setup test database BEFORE importing app modules
from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from structlog.testing import capture_logs

from backend.app.db.models import Asset, AssetEvent, AssetEventType, AssetProviderAssignment, AssetType, Broker, PriceHistory, Transaction, TransactionType
from backend.app.db.session import get_async_engine
from backend.app.schemas import prices as prices_schemas
from backend.app.schemas.assets.assets import FAAinfoFiltersRequest
from backend.app.schemas.assets.events import FAAssetEventPoint, FAEventUpsert
from backend.app.schemas.common import Currency, DateRangeModel
from backend.app.schemas.prices import FAHistoricalData, FAPricePoint, FAPriceQueryItem, FAUpsert, FAUpsertResult
from backend.app.schemas.provider import ProviderInputType
from backend.app.schemas.refresh import FARefreshItem, SyncDateRangeModel, SyncStatus
from backend.app.services.assets import core as asset_source_core
from backend.app.services.assets import price_query as price_query_module
from backend.app.services.assets import price_store as price_store_module
from backend.app.services.assets.base import AssetSourceError
from backend.app.services.assets.crud import AssetCRUDService
from backend.app.services.assets.event_store import EventStoreOperations
from backend.app.services.assets.manager import AssetSourceManager
from backend.app.services.assets.registry import AssetProviderRegistry
from backend.app.utils import date_range_limits
from backend.test_scripts.test_utils import unique_id

# A date window far from the mock dataset's, so a stray row of this unit can
# never be mistaken for -- or collide with -- a real fixture price.
BASE_DATE = date(1994, 6, 1)


@pytest.fixture(scope="module")
def owned_asset() -> int:
    """One asset owned entirely by this unit, removed with its prices in teardown."""
    marker = unique_id("UpsertGuards")

    async def _create() -> int:
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            asset = Asset(
                display_name=f"Upsert Guard {marker}",
                currency="USD",
                asset_type=AssetType.STOCK,
                active=True,
                identifier_cusip=f"C{marker[-8:]}".upper(),
                identifier_sedol=f"S{marker[-8:]}".upper(),
                identifier_figi=f"F{marker[-8:]}".upper(),
                identifier_uuid=marker,
            )
            session.add(asset)
            await session.commit()
            await session.refresh(asset)
            return asset.id

    async def _drop(asset_id: int) -> None:
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            await session.execute(delete(AssetEvent).where(AssetEvent.asset_id == asset_id))
            await session.execute(delete(PriceHistory).where(PriceHistory.asset_id == asset_id))
            await session.execute(delete(Asset).where(Asset.id == asset_id))
            await session.commit()

    asset_id = asyncio.run(_create())
    yield asset_id
    asyncio.run(_drop(asset_id))


@pytest_asyncio.fixture
async def clean_prices(owned_asset: int):
    """Drop this unit's own price rows before and after each test that writes them."""

    async def _wipe() -> None:
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            await session.execute(delete(PriceHistory).where(PriceHistory.asset_id == owned_asset))
            await session.commit()

    await _wipe()
    yield owned_asset
    await _wipe()


def _point(day_offset: int, close: str, *, low: str | None = None, high: str | None = None, open_: str | None = None) -> FAPricePoint:
    return FAPricePoint(
        date=BASE_DATE + timedelta(days=day_offset),
        close=Decimal(close),
        low=Decimal(low) if low is not None else None,
        high=Decimal(high) if high is not None else None,
        open=Decimal(open_) if open_ is not None else None,
        currency="USD",
    )


async def _stored(session: AsyncSession, asset_id: int, day_offset: int) -> PriceHistory | None:
    day = BASE_DATE + timedelta(days=day_offset)
    result = await session.execute(select(PriceHistory).where(PriceHistory.asset_id == asset_id, PriceHistory.date == day))
    return result.scalar_one_or_none()


# --------------------------------------------------------------------------- #
# Batch-level guards
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_an_empty_batch_writes_nothing_and_reports_nothing():
    """The Data Editor can submit a save with no rows changed."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        result = await AssetSourceManager.bulk_upsert_prices([], session)
    assert result == {"inserted_count": 0, "updated_count": 0, "results": []}


@pytest.mark.asyncio
async def test_an_unknown_asset_is_reported_instead_of_raising(clean_prices: int):
    """An asset deleted between opening the editor and saving must not kill the batch.

    The known asset in the same call still gets its point, which is what proves the
    unknown one was skipped rather than aborting the whole upsert.
    """
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        missing_id = (await session.execute(select(Asset.id).order_by(Asset.id.desc()).limit(1))).scalar_one() + 100_000
        result = await AssetSourceManager.bulk_upsert_prices(
            [
                FAUpsert(asset_id=missing_id, prices=[_point(0, "10")]),
                FAUpsert(asset_id=clean_prices, prices=[_point(0, "10")]),
            ],
            session,
        )

    by_asset = {row["asset_id"]: row for row in result["results"]}
    assert by_asset[missing_id]["message"] == f"Asset {missing_id} not found"
    assert by_asset[missing_id]["count"] == 0
    assert by_asset[clean_prices]["count"] == 1


# --------------------------------------------------------------------------- #
# OHLC integrity policy
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_a_bundle_with_low_above_high_is_rejected_for_that_date(clean_prices: int):
    """A provider candle that contradicts itself is dropped, not stored."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        result = await AssetSourceManager.bulk_upsert_prices(
            [FAUpsert(asset_id=clean_prices, prices=[_point(0, "10", low="20", high="5"), _point(1, "11", low="9", high="12")])],
            session,
        )
        assert await _stored(session, clean_prices, 0) is None
        assert (await _stored(session, clean_prices, 1)).close == Decimal("11")

    row = next(entry for entry in result["results"] if entry["asset_id"] == clean_prices)
    assert row["count"] == 1


@pytest.mark.asyncio
async def test_a_close_outside_the_incoming_bounds_is_rejected(clean_prices: int):
    """close=50 inside [9, 12] is impossible: the candle is corrupt, so it is dropped."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        await AssetSourceManager.bulk_upsert_prices(
            [FAUpsert(asset_id=clean_prices, prices=[_point(0, "50", low="9", high="12")])],
            session,
        )
        assert await _stored(session, clean_prices, 0) is None


@pytest.mark.asyncio
async def test_the_message_names_the_rejected_dates(clean_prices: int):
    """The user has to be able to see which candles the import refused."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        result = await AssetSourceManager.bulk_upsert_prices(
            [FAUpsert(asset_id=clean_prices, prices=[_point(0, "50", low="9", high="12"), _point(1, "11", low="9", high="12")])],
            session,
        )

    message = next(entry for entry in result["results"] if entry["asset_id"] == clean_prices)["message"]
    assert "rejected 1 date(s) with impossible OHLC" in message
    assert (BASE_DATE).isoformat() in message


@pytest.mark.asyncio
async def test_a_long_rejection_list_is_truncated_to_five_plus_a_count(clean_prices: int):
    """A wholly corrupt provider batch must not produce an unbounded message."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        result = await AssetSourceManager.bulk_upsert_prices(
            [FAUpsert(asset_id=clean_prices, prices=[_point(offset, "50", low="9", high="12") for offset in range(8)])],
            session,
        )
        # Every date was rejected, so not a single row may exist.
        remaining = (await session.execute(select(PriceHistory).where(PriceHistory.asset_id == clean_prices))).scalars().all()
        assert remaining == []

    message = next(entry for entry in result["results"] if entry["asset_id"] == clean_prices)["message"]
    assert "rejected 8 date(s)" in message
    assert "(+ 3 more)" in message


@pytest.mark.asyncio
async def test_a_close_only_update_widens_the_stored_bounds_instead_of_being_rejected(clean_prices: int):
    """The justETF / scheduled-investment case named in the source comment.

    A flat candle (low == high == close) is already stored. A later close-only
    update carries no bounds of its own, so F.4 preserves the stale ones -- and a
    naive integrity check would then reject the new close for sitting outside
    them. The policy is to widen [low, high] around the new close instead, so the
    price lands. This is the regression that must never come back.
    """
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        await AssetSourceManager.bulk_upsert_prices(
            [FAUpsert(asset_id=clean_prices, prices=[_point(0, "10", low="10", high="10")])],
            session,
        )
        await AssetSourceManager.bulk_upsert_prices(
            [FAUpsert(asset_id=clean_prices, prices=[_point(0, "12")])],
            session,
        )
        stored = await _stored(session, clean_prices, 0)

    assert (stored.close, stored.low, stored.high) == (Decimal("12"), Decimal("10"), Decimal("12"))


@pytest.mark.asyncio
async def test_a_close_only_update_below_the_stored_bounds_lowers_the_floor(clean_prices: int):
    """Same policy, mirrored: a new low must move `low`, not be thrown away."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        await AssetSourceManager.bulk_upsert_prices(
            [FAUpsert(asset_id=clean_prices, prices=[_point(0, "10", low="10", high="10")])],
            session,
        )
        await AssetSourceManager.bulk_upsert_prices(
            [FAUpsert(asset_id=clean_prices, prices=[_point(0, "7")])],
            session,
        )
        stored = await _stored(session, clean_prices, 0)

    assert (stored.close, stored.low, stored.high) == (Decimal("7"), Decimal("7"), Decimal("10"))


@pytest.mark.asyncio
async def test_a_close_only_update_on_a_date_with_no_stored_bounds_is_stored_as_is(clean_prices: int):
    """Nothing to widen: neither the incoming point nor the stored row has bounds."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        await AssetSourceManager.bulk_upsert_prices(
            [FAUpsert(asset_id=clean_prices, prices=[_point(0, "10")])],
            session,
        )
        stored = await _stored(session, clean_prices, 0)

    assert (stored.close, stored.low, stored.high) == (Decimal("10"), None, None)


@pytest.mark.asyncio
async def test_a_consistent_bundle_is_stored_verbatim(clean_prices: int):
    """The accepting side of the same guard, so a rejection cannot pass unnoticed."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        await AssetSourceManager.bulk_upsert_prices(
            [FAUpsert(asset_id=clean_prices, prices=[_point(0, "10", low="9", high="12", open_="9.5")])],
            session,
        )
        stored = await _stored(session, clean_prices, 0)

    assert (stored.close, stored.low, stored.high, stored.open) == (Decimal("10"), Decimal("9"), Decimal("12"), Decimal("9.5"))


# --------------------------------------------------------------------------- #
# list_assets identifier filters
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_list_assets_filters_by_cusip(owned_asset: int):
    """BRIM matches an imported row to an asset by whichever identifier the broker used."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        asset = (await session.execute(select(Asset).where(Asset.id == owned_asset))).scalar_one()
        found = await AssetCRUDService.list_assets(FAAinfoFiltersRequest(cusip=asset.identifier_cusip), session)

    assert [row.id for row in found] == [owned_asset]


@pytest.mark.asyncio
async def test_list_assets_filters_by_sedol(owned_asset: int):
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        asset = (await session.execute(select(Asset).where(Asset.id == owned_asset))).scalar_one()
        found = await AssetCRUDService.list_assets(FAAinfoFiltersRequest(sedol=asset.identifier_sedol), session)

    assert [row.id for row in found] == [owned_asset]


@pytest.mark.asyncio
async def test_list_assets_filters_by_figi(owned_asset: int):
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        asset = (await session.execute(select(Asset).where(Asset.id == owned_asset))).scalar_one()
        found = await AssetCRUDService.list_assets(FAAinfoFiltersRequest(figi=asset.identifier_figi), session)

    assert [row.id for row in found] == [owned_asset]


@pytest.mark.asyncio
async def test_list_assets_filters_by_uuid(owned_asset: int):
    """uuid is the one identifier matched verbatim, without upper-casing."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        asset = (await session.execute(select(Asset).where(Asset.id == owned_asset))).scalar_one()
        found = await AssetCRUDService.list_assets(FAAinfoFiltersRequest(uuid=asset.identifier_uuid), session)

    assert [row.id for row in found] == [owned_asset]


@pytest.mark.asyncio
async def test_list_assets_lowercase_identifier_still_matches(owned_asset: int):
    """The BRIM importer receives whatever case the broker file used."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        asset = (await session.execute(select(Asset).where(Asset.id == owned_asset))).scalar_one()
        found = await AssetCRUDService.list_assets(FAAinfoFiltersRequest(cusip=asset.identifier_cusip.lower()), session)

    assert [row.id for row in found] == [owned_asset]


# ─────────────────────────────────────────────────────────────────────────────
# Event currency conversion pass (E.8) of ``get_prices_bulk``
#
# Situation: the asset quotes in USD and pays dividends in USD, but the user is
# looking at the chart in EUR. Every event marker must be restated in EUR, and
# the pre-conversion amount kept in ``original_value`` so the tooltip can show
# both. When a rate is missing for one event's date the marker is left in its
# native currency and a non-fatal warning is added -- the FE relies on
# ``original_value is None`` to hide it from the converted chart.
#
# ``convert_bulk`` is stubbed instead of seeding ``FxRate`` rows: ``FxRate`` is a
# global table with no ``user_id``, so writing rates here would change what every
# other concurrent test converts. The stub also makes the assertions exact.
# ─────────────────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def asset_with_events(owned_asset: int):
    """Three dividend events: two in USD, one already in the target currency."""

    async def _wipe() -> None:
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            await session.execute(delete(AssetEvent).where(AssetEvent.asset_id == owned_asset))
            await session.commit()

    await _wipe()
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        for offset, value, currency in ((1, "1.50", "USD"), (2, "2.00", "USD"), (3, "3.00", "EUR")):
            session.add(
                AssetEvent(
                    asset_id=owned_asset,
                    date=BASE_DATE + timedelta(days=offset),
                    type=AssetEventType.DIVIDEND,
                    value=Decimal(value),
                    currency=currency,
                )
            )
        await session.commit()
    yield owned_asset
    await _wipe()


def _events_request(asset_id: int, target: str | None) -> FAPriceQueryItem:
    return FAPriceQueryItem(
        asset_id=asset_id,
        date_range=DateRangeModel(start=BASE_DATE, end=BASE_DATE + timedelta(days=10)),
        include_price=False,
        include_events=True,
        target_currency=target,
    )


async def _query(request: FAPriceQueryItem):
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        results = await AssetSourceManager.get_prices_bulk([request], session)
    return results[0]


@pytest.mark.asyncio
async def test_events_are_restated_in_the_target_currency(asset_with_events, monkeypatch):
    """A USD dividend viewed in EUR carries the converted value plus the original."""

    async def _fake_convert_bulk(_session, conversions, raise_on_error=False):
        # One conversion per non-EUR event, in request order.
        out = []
        for currency, target, when in conversions:
            out.append((Currency(amount=currency.amount * Decimal("2"), code=target), when, False))
        return out, []

    monkeypatch.setattr(price_query_module, "convert_bulk", _fake_convert_bulk)
    result = await _query(_events_request(asset_with_events, "EUR"))

    converted = {ev.date: ev for ev in result.events}
    first = converted[BASE_DATE + timedelta(days=1)]
    assert first.value.code == "EUR"
    assert first.value.amount == Decimal("3.00")
    assert first.original_value is not None
    assert first.original_value.code == "USD"
    assert first.original_value.amount == Decimal("1.50")
    # Same-day rate -> zero backward-fill distance.
    assert first.fx_info is not None
    assert first.fx_info.fx_days_back == 0


@pytest.mark.asyncio
async def test_event_already_in_target_currency_is_passed_through_untouched(asset_with_events, monkeypatch):
    """The EUR dividend must not be sent to FX at all: no original_value, no marker."""
    seen: list[int] = []

    async def _fake_convert_bulk(_session, conversions, raise_on_error=False):
        seen.append(len(conversions))
        return [(Currency(amount=c[0].amount, code=c[1]), c[2], False) for c in conversions], []

    monkeypatch.setattr(price_query_module, "convert_bulk", _fake_convert_bulk)
    result = await _query(_events_request(asset_with_events, "EUR"))

    native = next(ev for ev in result.events if ev.date == BASE_DATE + timedelta(days=3))
    assert native.value.code == "EUR"
    assert native.original_value is None
    # Only the two USD events were handed to the converter.
    assert seen == [2]


@pytest.mark.asyncio
async def test_missing_rate_leaves_the_event_native_and_warns(asset_with_events, monkeypatch):
    """A gap in the FX series must degrade one marker, not fail the whole query."""

    async def _fake_convert_bulk(_session, conversions, raise_on_error=False):
        # First USD event converts, the second has no rate available.
        first = (Currency(amount=conversions[0][0].amount, code=conversions[0][1]), conversions[0][2], False)
        return [first, None], ["rate provider unavailable"]

    monkeypatch.setattr(price_query_module, "convert_bulk", _fake_convert_bulk)
    result = await _query(_events_request(asset_with_events, "EUR"))

    stranded = next(ev for ev in result.events if ev.date == BASE_DATE + timedelta(days=2))
    assert stranded.value.code == "USD"
    assert stranded.original_value is None
    assert any("Missing FX rate USD->EUR" in err for err in result.errors)
    # The converter's own error is surfaced too, exactly once.
    assert result.errors.count("rate provider unavailable") == 1


@pytest.mark.asyncio
async def test_conversion_pass_is_skipped_without_a_target_currency(asset_with_events, monkeypatch):
    """No target currency means the FX converter is never called."""

    async def _explode(*_args, **_kwargs):
        raise AssertionError("convert_bulk must not run without a target currency")

    monkeypatch.setattr(price_query_module, "convert_bulk", _explode)
    result = await _query(_events_request(asset_with_events, None))

    assert {ev.value.code for ev in result.events} == {"USD", "EUR"}
    assert all(ev.original_value is None for ev in result.events)


@pytest.mark.asyncio
async def test_conversion_pass_is_skipped_when_every_event_is_already_in_target(asset_with_events, monkeypatch):
    """Asking for USD on a USD/EUR mix still short-circuits when nothing needs FX."""

    async def _fake_convert_bulk(_session, conversions, raise_on_error=False):
        return [(Currency(amount=c[0].amount, code=c[1]), c[2], False) for c in conversions], []

    monkeypatch.setattr(price_query_module, "convert_bulk", _fake_convert_bulk)
    # Only the EUR event is in range: everything the query returns is already USD-free.
    request = FAPriceQueryItem(
        asset_id=asset_with_events,
        date_range=DateRangeModel(start=BASE_DATE + timedelta(days=3), end=BASE_DATE + timedelta(days=4)),
        include_price=False,
        include_events=True,
        target_currency="EUR",
    )
    result = await _query(request)

    assert [ev.value.code for ev in result.events] == ["EUR"]
    assert all(ev.original_value is None for ev in result.events)


# ─────────────────────────────────────────────────────────────────────────────
# Currency-mismatch short-circuit of ``bulk_refresh_prices._persist_single``
#
# Situation: an asset quoted in USD is pointed at a provider identifier that
# actually returns a JPY series (a mis-typed ticker, or a provider that silently
# resolves to a foreign listing). Comments #R3-2 and #R4-1 in the source say why
# this is handled explicitly: without the short-circuit the user would get a raw
# pydantic "List should have at least 1 item" error instead of a message naming
# the currency that was found.
#
# Nothing reaches the database on this path -- every fetched point is discarded
# before the upsert -- which is exactly what makes it safe to run here. The
# provider is replaced wholesale: no network call is made.
# ─────────────────────────────────────────────────────────────────────────────


class _FakeProvider:
    """Stand-in for a real asset source provider: validates nothing, fetches nothing."""

    supports_history = True
    supports_current_value = False
    supports_events = False

    def validate_params(self, _params) -> None:
        return None

    def get_historical_data(self, *_args, **_kwargs):
        raise AssertionError("must go through the patched _run_provider_in_thread")


@pytest_asyncio.fixture
async def assigned_asset(owned_asset: int):
    """Give this unit's asset a provider assignment, and take it away afterwards."""

    async def _wipe() -> None:
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            await session.execute(delete(AssetProviderAssignment).where(AssetProviderAssignment.asset_id == owned_asset))
            await session.commit()

    await _wipe()
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        session.add(
            AssetProviderAssignment(
                asset_id=owned_asset,
                provider_code="fake_provider_for_tests",
                identifier="FAKE.TEST",
                identifier_type=ProviderInputType.TICKER,
                provider_params="{}",
            )
        )
        await session.commit()
    yield owned_asset
    await _wipe()


def _patch_provider(monkeypatch, prices: list[FAPricePoint]) -> None:
    # On the registry class itself: refresh reaches it through core.configured_provider, which looks the provider up
    # on this same class (refresh no longer imports the registry, so it is no attribute of that module).
    monkeypatch.setattr(
        AssetProviderRegistry,
        "get_provider_instance",
        staticmethod(lambda _code: _FakeProvider()),
    )

    async def _fake_thread(_fn, timeout=None):
        return FAHistoricalData(prices=prices, source="fake_provider_for_tests")

    monkeypatch.setattr(asset_source_core, "_run_provider_in_thread", _fake_thread)


def _refresh_item(asset_id: int) -> FARefreshItem:
    # An end date in the past keeps the "current value" leg out of the picture,
    # so the fake provider only has to answer the history call.
    return FARefreshItem(
        asset_id=asset_id,
        date_range=SyncDateRangeModel(start=BASE_DATE, end=BASE_DATE + timedelta(days=5)),
    )


async def _refresh(asset_id: int):
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        response = await AssetSourceManager.bulk_refresh_prices([_refresh_item(asset_id)], session)
    return next(r for r in response.results if r.asset_id == asset_id)


def _foreign_point(day_offset: int, close: str, currency: str) -> FAPricePoint:
    return FAPricePoint(date=BASE_DATE + timedelta(days=day_offset), close=Decimal(close), currency=currency)


@pytest.mark.asyncio
async def test_all_points_in_a_foreign_currency_fail_with_a_readable_reason(assigned_asset, clean_prices, monkeypatch):
    """A wholly foreign series must be reported as a currency mismatch, not as a schema error."""
    _patch_provider(monkeypatch, [_foreign_point(0, "100", "JPY"), _foreign_point(1, "101", "JPY")])

    result = await _refresh(assigned_asset)

    assert result.status == SyncStatus.FAILED
    joined = " ".join(result.errors)
    assert "currency mismatch" in joined
    # The message names how many points were dropped and in which currency.
    assert "2 JPY" in joined
    assert "expected USD" in joined
    # And nothing was written: the batch never reached the upsert.
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        stored = (await session.execute(select(PriceHistory).where(PriceHistory.asset_id == assigned_asset))).scalars().all()
    assert stored == []


@pytest.mark.asyncio
async def test_mixed_currency_series_keeps_the_matching_points_and_warns(assigned_asset, clean_prices, monkeypatch):
    """Two currencies in one payload: the asset's own points survive, the others are named."""
    _patch_provider(
        monkeypatch,
        [
            _foreign_point(0, "10", "USD"),
            _foreign_point(1, "999", "JPY"),
            _foreign_point(2, "888", "GBP"),
        ],
    )

    result = await _refresh(assigned_asset)

    joined = " ".join(result.errors)
    assert "2 points discarded" in joined
    # Buckets are reported sorted by currency code, one entry each.
    assert "1 GBP, 1 JPY" in joined
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        stored = (await session.execute(select(PriceHistory).where(PriceHistory.asset_id == assigned_asset))).scalars().all()
    # Only the USD point made it through.
    assert [(row.date, row.close) for row in stored] == [(BASE_DATE, Decimal("10"))]


# ─────────────────────────────────────────────────────────────────────────────
# Editing events in place (workstream I: S5, legacy duplicates, provider rows)
#
# Before the fix (108a2adf5) ``_upsert_asset_events`` was DELETE + INSERT on
# (asset_id, date, type, provider_assignment_id). ``transactions.asset_event_id``
# is ON DELETE RESTRICT, so the DELETE half failed with IntegrityError as soon as
# a transaction linked the row:
#
# * S5 -- a provider refresh re-delivering an auto event a transaction realises
#   recorded "Event upsert failed", and the event was never updated again;
# * legacy duplicates -- two manual rows on one key (no unique index forbids them)
#   could not be edited once either was linked.
#
# Intended contract: a row is updated in place (same id, links kept). Same-key
# manual duplicates collapse onto the lowest id after their transactions are
# re-pointed to it. A manual upsert may name an existing row by ``id``, but never a
# provider row (AssetSourceError EVENT_NOT_EDITABLE). Manual and provider rows never
# touch each other.
#
# Id-bearing payloads go through ``FAEventUpsert.model_validate`` inside the test
# body: before the fix that raised a ValidationError (``id`` was an unknown field),
# which failed only the tests needing the new field, not the whole module.
#
# Each test writes on its own date offset from ``EDIT_BASE``, far from the windows
# used above. Besides events it creates a Broker and Transactions, which ``Asset``
# and ``AssetEvent`` cannot outlive (no cascade, RESTRICT). ``event_rows`` removes
# them in FK-safe order before ``assigned_asset`` drops the assignment and the
# module drops the asset.
# ─────────────────────────────────────────────────────────────────────────────

EDIT_BASE = BASE_DATE + timedelta(days=400)
EDIT_END = EDIT_BASE + timedelta(days=60)


class _EventRows:
    """Events (manual or provider) and the transactions linking them, written directly via the ORM."""

    def __init__(self, asset_id: int, assignment_id: int, broker_id: int) -> None:
        self.asset_id = asset_id
        self.assignment_id = assignment_id
        self.broker_id = broker_id

    async def add_event(self, day_offset: int, value: str, *, auto: bool, kind: AssetEventType = AssetEventType.DIVIDEND) -> int:
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            row = AssetEvent(
                asset_id=self.asset_id,
                date=EDIT_BASE + timedelta(days=day_offset),
                type=kind,
                value=Decimal(value),
                currency="USD",
                provider_assignment_id=self.assignment_id if auto else None,
            )
            session.add(row)
            await session.commit()
            return row.id

    async def link_tx(self, event_id: int, day_offset: int) -> int:
        """A DIVIDEND realising ``event_id``: what pins the event under ON DELETE RESTRICT."""
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            tx = Transaction(
                broker_id=self.broker_id,
                asset_id=self.asset_id,
                type=TransactionType.DIVIDEND,
                date=EDIT_BASE + timedelta(days=day_offset),
                quantity=Decimal("0"),
                amount=Decimal("1.00"),
                currency="USD",
                asset_event_id=event_id,
            )
            session.add(tx)
            await session.commit()
            return tx.id

    async def rows(self, day_offset: int, kind: AssetEventType = AssetEventType.DIVIDEND) -> list[AssetEvent]:
        """Every event of the asset on that day and type, lowest id first."""
        day = EDIT_BASE + timedelta(days=day_offset)
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            stmt = select(AssetEvent).where(AssetEvent.asset_id == self.asset_id, AssetEvent.date == day, AssetEvent.type == kind).order_by(AssetEvent.id)
            return list((await session.execute(stmt)).scalars().all())

    async def tx_event_id(self, tx_id: int) -> int | None:
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            return (await session.execute(select(Transaction.asset_event_id).where(Transaction.id == tx_id))).scalar_one()


@pytest_asyncio.fixture
async def event_rows(assigned_asset: int):
    """A broker of this test's own, plus a writer for events and linked transactions.

    Teardown, in FK-safe order: the transactions (they RESTRICT their event and pin the
    broker), the events this section writes, then the broker.
    """
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        assignment_id = (await session.execute(select(AssetProviderAssignment.id).where(AssetProviderAssignment.asset_id == assigned_asset))).scalar_one()
        broker = Broker(name=f"Upsert Guards {uuid.uuid4().hex}", allow_cash_overdraft=True)
        session.add(broker)
        await session.commit()
        broker_id = broker.id

    yield _EventRows(assigned_asset, assignment_id, broker_id)

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        await session.execute(delete(Transaction).where(Transaction.broker_id == broker_id))
        await session.execute(delete(AssetEvent).where(AssetEvent.asset_id == assigned_asset, AssetEvent.date >= EDIT_BASE, AssetEvent.date <= EDIT_END))
        await session.execute(delete(Broker).where(Broker.id == broker_id))
        await session.commit()


def _dividend(day_offset: int, amount: str) -> FAAssetEventPoint:
    return FAAssetEventPoint(date=EDIT_BASE + timedelta(days=day_offset), type="DIVIDEND", value=Currency(code="USD", amount=Decimal(amount)))


def _manual_upsert(asset_id: int, events: list[dict]) -> FAEventUpsert:
    """The manual upsert body, validated as the endpoint validates it."""
    return FAEventUpsert.model_validate({"asset_id": asset_id, "events": events})


def _dividend_payload(day_offset: int, amount: str, *, event_id: int | None = None) -> dict:
    payload: dict = {"date": (EDIT_BASE + timedelta(days=day_offset)).isoformat(), "type": "DIVIDEND", "value": {"code": "USD", "amount": amount}}
    if event_id is not None:
        payload["id"] = event_id
    return payload


async def _provider_upsert(rows: _EventRows, events: list[FAAssetEventPoint]) -> int:
    """What a provider refresh does with the events it fetched."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        count = await EventStoreOperations._upsert_asset_events(session, rows.asset_id, events, rows.assignment_id, "USD")
        await session.commit()
    return count


async def _bulk_upsert_events(data: list[FAEventUpsert]) -> dict:
    """What ``POST /assets/events`` does, minus HTTP."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        result = await EventStoreOperations.bulk_upsert_events(data, session)
        await session.commit()
    return result


@pytest.mark.asyncio
async def test_provider_upsert_updates_a_linked_auto_event_in_place(event_rows):
    """S5: a provider re-delivering an auto event that a transaction links to updates that row.

    Before the fix: the DELETE half of DELETE + INSERT violates ON DELETE RESTRICT and
    ``sqlalchemy.exc.IntegrityError`` escapes ``_upsert_asset_events``.
    Contract: no exception, count 1, same row id, value 2.00, the transaction still linked.
    """
    auto_id = await event_rows.add_event(0, "1.00", auto=True)
    tx_id = await event_rows.link_tx(auto_id, 0)

    count = await _provider_upsert(event_rows, [_dividend(0, "2.00")])

    assert count == 1
    assert [(r.id, r.value, r.provider_assignment_id) for r in await event_rows.rows(0)] == [(auto_id, Decimal("2.00"), event_rows.assignment_id)]
    assert await event_rows.tx_event_id(tx_id) == auto_id


class _NoHistoryCache:
    """Stand-in for ``core._asset_history_cache``: never hits, never stores.

    The real cache is keyed by provider and identifier only, not by dates. An entry left by
    the currency tests above (same fake provider, same identifier) would be merged into
    this refresh, and this refresh's events would be served to whoever asks next.
    """

    def get(self, _key):
        return None, False

    def set(self, _key, _value) -> None:
        return None

    def delete(self, _key) -> None:
        return None


def _patch_provider_with_events(monkeypatch, prices: list[FAPricePoint], events: list[FAAssetEventPoint]) -> None:
    """``_patch_provider``, plus events in the history payload and no history cache."""
    _patch_provider(monkeypatch, prices)

    async def _fake_thread(_fn, timeout=None):
        return FAHistoricalData(prices=prices, events=events, source="fake_provider_for_tests")

    monkeypatch.setattr(asset_source_core, "_run_provider_in_thread", _fake_thread)
    monkeypatch.setattr(asset_source_core, "_asset_history_cache", _NoHistoryCache())


def _edit_price(day_offset: int, close: str) -> FAPricePoint:
    return FAPricePoint(date=EDIT_BASE + timedelta(days=day_offset), close=Decimal(close), currency="USD")


@pytest.mark.asyncio
async def test_provider_refresh_updates_a_linked_auto_event_in_place(event_rows, clean_prices, monkeypatch):
    """S5 through the real refresh path: a linked auto event is refreshed, not reported as failed.

    Two price points, so the refresh is a plain OK one; one DIVIDEND event on a date whose
    auto row a transaction already links to.
    Before the fix: ``_persist_refresh_item`` catches the IntegrityError and records
    "Event upsert failed: ..." in ``errors``; the row keeps its old value.
    Contract: no such error, one event fetched and one processed, the same row now at
    2.00, and the transaction still linked.
    """
    auto_id = await event_rows.add_event(2, "1.00", auto=True)
    tx_id = await event_rows.link_tx(auto_id, 2)
    _patch_provider_with_events(monkeypatch, [_edit_price(0, "10"), _edit_price(1, "11")], [_dividend(2, "2.00")])

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        item = FARefreshItem(asset_id=event_rows.asset_id, date_range=SyncDateRangeModel(start=EDIT_BASE, end=EDIT_BASE + timedelta(days=5)))
        response = await AssetSourceManager.bulk_refresh_prices([item], session)
    result = next(r for r in response.results if r.asset_id == event_rows.asset_id)

    assert result.events_fetched == 1, result
    assert not [e for e in result.errors if "Event upsert failed" in e], result.errors
    assert result.events_changed == 1, result
    assert [(r.id, r.value) for r in await event_rows.rows(2)] == [(auto_id, Decimal("2.00"))]
    assert await event_rows.tx_event_id(tx_id) == auto_id


@pytest.mark.asyncio
async def test_legacy_duplicate_manual_events_collapse_onto_the_lowest_id(event_rows):
    """Legacy same-key manual duplicates collapse onto the lowest id, links re-pointed first.

    Two manual DIVIDEND rows on one date; a transaction links to the HIGHER id.
    Before the fix: deleting both rows hits ON DELETE RESTRICT -> IntegrityError.
    Contract: one row remains, the lower id, with the new amount, and the transaction
    now points at it.
    """
    low_id = await event_rows.add_event(20, "1.00", auto=False)
    high_id = await event_rows.add_event(20, "1.10", auto=False)
    assert low_id < high_id
    tx_id = await event_rows.link_tx(high_id, 20)

    await _bulk_upsert_events([_manual_upsert(event_rows.asset_id, [_dividend_payload(20, "1.50")])])

    assert [(r.id, r.value) for r in await event_rows.rows(20)] == [(low_id, Decimal("1.50"))]
    assert await event_rows.tx_event_id(tx_id) == low_id


@pytest.mark.asyncio
async def test_manual_upsert_cannot_edit_a_provider_event_by_id(event_rows):
    """A manual upsert naming a provider row by id is refused, and nothing is written.

    Before the fix: ``FAEventUpsert.model_validate`` rejects the ``id`` key with a pydantic
    ValidationError (extra_forbidden), raised in the test body.
    Contract: ``bulk_upsert_events`` raises AssetSourceError with error_code
    EVENT_NOT_EDITABLE; the provider row keeps its id and value.
    """
    auto_id = await event_rows.add_event(30, "1.00", auto=True)
    upsert = _manual_upsert(event_rows.asset_id, [_dividend_payload(30, "3", event_id=auto_id)])

    with pytest.raises(AssetSourceError) as raised:
        await _bulk_upsert_events([upsert])

    assert raised.value.error_code == "EVENT_NOT_EDITABLE"
    assert [(r.id, r.value, r.provider_assignment_id) for r in await event_rows.rows(30)] == [(auto_id, Decimal("1.00"), event_rows.assignment_id)]


@pytest.mark.asyncio
async def test_provider_upsert_leaves_the_manual_twin_untouched(event_rows):
    """GUARD: on a key held by a manual and an auto row, a provider upsert changes only its own row."""
    manual_id = await event_rows.add_event(10, "1.00", auto=False)
    await event_rows.add_event(10, "1.00", auto=True)

    await _provider_upsert(event_rows, [_dividend(10, "2.00")])

    rows = await event_rows.rows(10)
    assert [(r.id, r.value) for r in rows if r.provider_assignment_id is None] == [(manual_id, Decimal("1.00"))]
    assert [r.value for r in rows if r.provider_assignment_id == event_rows.assignment_id] == [Decimal("2.00")]


@pytest.mark.asyncio
async def test_manual_upsert_leaves_the_provider_twin_untouched(event_rows):
    """GUARD: on a key held by a manual and an auto row, a manual upsert changes only the manual row."""
    auto_id = await event_rows.add_event(12, "1.00", auto=True)
    await event_rows.add_event(12, "1.00", auto=False)

    await _bulk_upsert_events([_manual_upsert(event_rows.asset_id, [_dividend_payload(12, "3.00")])])

    rows = await event_rows.rows(12)
    assert [(r.id, r.value) for r in rows if r.provider_assignment_id is not None] == [(auto_id, Decimal("1.00"))]
    assert [r.value for r in rows if r.provider_assignment_id is None] == [Decimal("3.00")]


@pytest.mark.asyncio
async def test_two_manual_events_sharing_a_key_are_edited_by_id(event_rows):
    """Rows that keep their key may share it: legacy same-key duplicates stay editable by id.

    Service-level twin of ``test_assets_events.py::test_upsert_with_ids_edits_two_events_sharing_a_key``,
    with the duplicates built directly in the database instead of through an upsert.
    Before the fix: ``FAEventUpsert.model_validate`` rejects the ``id`` key (ValidationError).
    Contract: both ids kept, each with its own new amount.
    """
    first_id = await event_rows.add_event(25, "1.00", auto=False)
    second_id = await event_rows.add_event(25, "1.00", auto=False)
    upsert = _manual_upsert(event_rows.asset_id, [_dividend_payload(25, "1.11", event_id=first_id), _dividend_payload(25, "2.22", event_id=second_id)])

    await _bulk_upsert_events([upsert])

    assert [(r.id, r.value) for r in await event_rows.rows(25)] == [(first_id, Decimal("1.11")), (second_id, Decimal("2.22"))]


# ─────────────────────────────────────────────────────────────────────────────
# X-R65 (night decision N83, revised 19/10): a stored price is dated no later than latest_range_end()
#
# J's SEC8-1b: one price dated 0001-01-01 made a backward fill or a risk replay walk about 740 000 days for its asset,
# and X-R65 (17/10) bounded every stored price to [1900-01-01, latest_range_end()]. N83's revision (developer, 19/10:
# «se voglio leggere e salvare più indietro devo poterlo fare») takes the 1900 floor off every write, a provider's
# points included, and keeps the ceiling alone; the walks stay bounded where they read (N75's 100 years, R13-SEC8's
# replay floors, Z-30's full-history load from 1900).
#
# Contract (N83, revised):
# * MANUAL: every point's date is checked against ``date_range_limits.latest_stored_date()`` -- ``latest_range_end()``,
#   included -- before any database statement. One date after it raises ``date_range_limits.DateOutOfRangeError``, not
#   a ``ValueError``: ``items`` one entry per asset holding such dates, in input order, ``{"asset_id": id, "dates": its
#   offending dates as ISO strings, in input order, ten at most}``; ``count`` every offending date of the request;
#   ``latest`` the ceiling, and no ``earliest``. Nothing is written, for any asset of the request. A date before 1900 --
#   1899-12-31, 1850-06-01, 0001-01-01 -- is stored like any other.
# * Any other key (a provider's): the points after the ceiling are dropped before any write, like the ones no column can
#   keep (W-B58) -- a warning logged, the asset's result message saying so («rejected N date(s) …», the dates listed) --
#   and every other point is written, the ones before 1900 included.
# * The refresh counts its changes, and lists them in ``changed_points`` for the chart, before it upserts (follow-up,
#   17/10): a date the upsert drops for lying after the ceiling is neither counted nor announced, like a value no column
#   can keep (W-B62); a date before 1900, which the upsert now keeps, is counted and announced like any other.
#
# The ceiling is frozen (``frozen_stored_ceiling``) where ``latest_stored_date`` reads it: the name
# ``latest_range_end`` imported into ``date_range_limits`` (that seam is RC-W01's, services range-ceiling). Frozen at
# ``XR65_CEILING``, a day of this unit's window and long past: a check reading tomorrow some other way lets the day after
# it through, and fails here. The dates before 1900 need no freeze: they lie before every ceiling. The prices go on this
# unit's own assets; the shape of a refusal is read on no database at all -- a refusal before any statement needs none
# (``_SessionSpy()``).
#
# Red before N83's revision (HEAD f5135c9a1), each for the reason its docstring gives ("Red before N83's revision"); the
# others are guards, green before it and after.
# ─────────────────────────────────────────────────────────────────────────────

XR65_OLD_FLOOR = date(1900, 1, 1)  # EARLIEST_RANGE_START: the floor X-R65 gave a stored price and N83's revision took away
XR65_CEILING = BASE_DATE + timedelta(days=44)  # 1994-07-15: latest_range_end(), frozen
XR65_AFTER = XR65_CEILING + timedelta(days=1)  # the day after the ceiling
XR65_BEFORE = date(1899, 12, 31)  # the day before the old floor
XR65_PROVIDER = "fake_provider_for_tests"
_XR65_BARRIER = "X-R65 capture barrier"


@pytest.fixture
def frozen_stored_ceiling(monkeypatch: pytest.MonkeyPatch) -> date:
    """``latest_range_end()`` answers ``XR65_CEILING`` where ``latest_stored_date`` reads it: the name in
    ``date_range_limits``.

    Set even where the name is missing (``raising=False``): on code without X-R65 the upsert then runs as it always did,
    and the case fails on what it wrote, not on a missing attribute.
    """
    monkeypatch.setattr(date_range_limits, "latest_range_end", lambda: XR65_CEILING, raising=False)
    return XR65_CEILING


@pytest_asyncio.fixture
async def xr65_second_asset():
    """A second asset of this unit's own, in USD and without a price; removed with its prices afterwards."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        asset = Asset(display_name=f"Upsert Guard X-R65 {unique_id('UpsertGuards')} {uuid.uuid4().hex[:8]}", currency="USD", asset_type=AssetType.STOCK, active=True)
        session.add(asset)
        await session.commit()
        asset_id = asset.id
    yield asset_id
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        await session.execute(delete(PriceHistory).where(PriceHistory.asset_id == asset_id))
        await session.execute(delete(Asset).where(Asset.id == asset_id))
        await session.commit()


def _on(day: date, close: str) -> FAPricePoint:
    """A close of ``close`` USD on ``day``."""
    return FAPricePoint(date=day, close=Decimal(close), currency="USD")


class _NoRow:
    """What ``_SessionSpy()`` without a session answers to every statement: no row, however it is read."""

    def scalar_one_or_none(self) -> None:
        return None

    def scalars(self) -> "_NoRow":
        return self

    def all(self) -> list:
        return []


class _SessionSpy:
    """The session handed to ``bulk_upsert_prices``: every attribute it reaches for is recorded in ``used``, then served
    by ``real``, a session of the lane database -- or, with none, by stand-ins that read no row and write nothing."""

    def __init__(self, real: AsyncSession | None = None) -> None:
        self.real = real
        self.used: list[str] = []

    def __getattr__(self, name: str):
        self.used.append(name)
        if self.real is not None:
            return getattr(self.real, name)
        if name in ("add", "add_all", "expunge"):
            return lambda *_args, **_kwargs: None

        async def _answer(*_args, **_kwargs):
            return _NoRow() if name == "execute" else None

        return _answer


async def _refused_out_of_range(spy: _SessionSpy, data: list[FAUpsert]):
    """The ``DateOutOfRangeError`` a MANUAL upsert of ``data`` on ``spy`` raises; when it raises none, the test fails
    saying what the upsert answered and what it asked of the session."""
    error_class = getattr(date_range_limits, "DateOutOfRangeError", None)
    try:
        result = await AssetSourceManager.bulk_upsert_prices(data, spy)
    except Exception as error:
        if error_class is not None and isinstance(error, error_class):
            return error
        raise
    pytest.fail(f"no DateOutOfRangeError: the upsert answered {result}, after reaching the session for {spy.used}")


async def _accepted(data: list[FAUpsert], key: str = "MANUAL") -> dict:
    """The result of ``bulk_upsert_prices`` of ``data`` under ``key``, on a session of the lane database; a
    ``DateOutOfRangeError`` instead fails the test, naming what it refused."""
    error_class = getattr(date_range_limits, "DateOutOfRangeError", None)
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        try:
            return await AssetSourceManager.bulk_upsert_prices(data, session, source_plugin_key=key)
        except Exception as error:
            if error_class is not None and isinstance(error, error_class):
                pytest.fail(f"the upsert was refused with DateOutOfRangeError: items {error.items}, count {error.count}")
            raise


async def _stored_days(asset_id: int) -> list[date]:
    """The days the asset has a price on, in order, read by a session of their own."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        return list((await session.execute(select(PriceHistory.date).where(PriceHistory.asset_id == asset_id).order_by(PriceHistory.date))).scalars().all())


async def _stored_closes(asset_id: int) -> dict[date, Decimal]:
    """The asset's closes by day, read by a session of their own."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        rows = (await session.execute(select(PriceHistory.date, PriceHistory.close).where(PriceHistory.asset_id == asset_id))).all()
    return {row.date: row.close for row in rows}


def _names(said: object, *values: object) -> bool:
    """Whether ``said`` (a message, a log event) names every one of ``values``: a day as its ISO text or its repr,
    anything else as its text."""
    text = str(said)
    return all((value.isoformat() in text or repr(value) in text) if isinstance(value, date) else str(value) in text for value in values)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "day",
    [
        pytest.param(XR65_AFTER, id="the-day-after-the-ceiling"),
        pytest.param(date.max, id="9999-12-31"),
    ],
)
async def test_a_manual_price_after_the_ceiling_refuses_the_upsert_before_any_statement(clean_prices, frozen_stored_ceiling, day):
    """X-R65 guard, green before N83's revision and after: one manual price after the ceiling, between two valid ones,
    refuses the whole upsert.

    Red before X-R65: the upsert reads the asset and stores the three prices, ``day`` among them.
    Contract: ``DateOutOfRangeError`` with ``items`` ``[{"asset_id": the asset, "dates": [day]}]``, ``count`` 1 and
    ``latest`` the ceiling; raised before the session is reached at all; the asset has no price, not even on the two
    valid days. (That the error carries no ``earliest`` is RC-W03's, services range-ceiling.)
    """
    data = [FAUpsert(asset_id=clean_prices, prices=[_on(BASE_DATE, "10"), _on(day, "11"), _on(BASE_DATE + timedelta(days=1), "12")])]
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        spy = _SessionSpy(session)
        error = await _refused_out_of_range(spy, data)

    assert spy.used == [], f"the session was reached for {spy.used} before the refusal"
    assert (error.items, error.count) == ([{"asset_id": clean_prices, "dates": [day.isoformat()]}], 1)
    assert error.latest == XR65_CEILING
    assert await _stored_days(clean_prices) == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "day",
    [
        pytest.param(XR65_BEFORE, id="1899-12-31-the-day-before-the-old-floor"),
        pytest.param(date(1850, 6, 1), id="1850-06-01"),
        pytest.param(date.min, id="0001-01-01-SEC8-1b"),
    ],
)
async def test_a_manual_price_before_1900_is_stored(clean_prices, day):
    """N83 (revised 19/10): one manual price before 1900-01-01, between two valid ones, is stored like them.

    Red before N83's revision: ``DateOutOfRangeError`` (``items`` ``[{"asset_id": the asset, "dates": [day]}]``), raised
    before the session is reached; nothing stored.
    Contract: no refusal; the asset's result counts 3 and lists no rejection; the three days are stored at their closes,
    ``day`` among them -- 0001-01-01 too: the walks that read it are bounded where they read.
    """
    data = [FAUpsert(asset_id=clean_prices, prices=[_on(BASE_DATE, "10"), _on(day, "11"), _on(BASE_DATE + timedelta(days=1), "12")])]

    result = await _accepted(data)

    row = next(entry for entry in result["results"] if entry["asset_id"] == clean_prices)
    assert (row["count"], row.get("rejected")) == (3, []), row
    assert await _stored_closes(clean_prices) == {day: Decimal("11"), BASE_DATE: Decimal("10"), BASE_DATE + timedelta(days=1): Decimal("12")}


@pytest.mark.asyncio
async def test_a_manual_price_on_the_ceiling_is_stored(clean_prices, frozen_stored_ceiling):
    """X-R65 guard, green before N83's revision and after: the ceiling belongs to the window, and 1900-01-01 -- the old
    floor, a bound until the revision -- is a day like any other.

    Contract: a manual price on 1900-01-01 and one on the ceiling itself are stored like any other.
    """
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        result = await AssetSourceManager.bulk_upsert_prices([FAUpsert(asset_id=clean_prices, prices=[_on(XR65_OLD_FLOOR, "10"), _on(XR65_CEILING, "11")])], session)

    row = next(entry for entry in result["results"] if entry["asset_id"] == clean_prices)
    assert row["count"] == 2, row
    assert await _stored_days(clean_prices) == [XR65_OLD_FLOOR, XR65_CEILING]


@pytest.mark.asyncio
async def test_an_offending_asset_refuses_the_clean_asset_before_it(clean_prices, xr65_second_asset, frozen_stored_ceiling):
    """X-R65 guard, green before N83's revision and after: a clean asset first, then one with a price on the day after
    the ceiling: neither is written.

    Red before X-R65: the upsert works asset by asset and commits as it goes: the first asset's two prices, then the
    second's two, the day after the ceiling among them.
    Contract: ``DateOutOfRangeError`` naming the second asset alone (``items`` ``[{"asset_id": second, "dates": [the day
    after the ceiling]}]``, ``count`` 1), the session never reached, and neither asset has a price. Until N83's revision
    the second asset's offending day was 1899-12-31, which is now stored (``test_a_manual_price_before_1900_is_stored``).
    """
    data = [
        FAUpsert(asset_id=clean_prices, prices=[_on(BASE_DATE, "10"), _on(BASE_DATE + timedelta(days=1), "11")]),
        FAUpsert(asset_id=xr65_second_asset, prices=[_on(BASE_DATE + timedelta(days=2), "12"), _on(XR65_AFTER, "13")]),
    ]
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        spy = _SessionSpy(session)
        error = await _refused_out_of_range(spy, data)

    assert spy.used == [], f"the session was reached for {spy.used} before the refusal"
    assert (error.items, error.count) == ([{"asset_id": xr65_second_asset, "dates": [XR65_AFTER.isoformat()]}], 1)
    assert await _stored_days(clean_prices) == []
    assert await _stored_days(xr65_second_asset) == []


@pytest.mark.asyncio
async def test_the_refusal_names_each_assets_dates_in_input_order_ten_at_most(frozen_stored_ceiling):
    """X-R65: the numbers of a refusal, read on no database at all (the check comes before any statement).

    Three assets: the first with twelve days after the ceiling, latest first, a valid day among them; the second clean;
    the third with 9999-12-31, a valid day, 1066-10-14 and the day after the ceiling. The asset ids name no row: the
    stand-in session answers none.
    Red before X-R65: each asset is read («Asset … not found»), nothing is refused.
    Red before N83's revision: 1066-10-14 is refused too, the third asset's second date, and ``count`` is 15.
    Contract: ``items`` the first and the third asset, in input order, each with its dates after the ceiling in input
    order (not sorted), the first one's ten at most; 1066-10-14 in none, a day like any other; ``count`` 14, every date
    after the ceiling; the session never reached.
    """
    late = [XR65_AFTER + timedelta(days=n) for n in range(11, -1, -1)]
    data = [
        FAUpsert(asset_id=9_001, prices=[_on(day, "10") for day in late[:6]] + [_on(BASE_DATE, "10")] + [_on(day, "10") for day in late[6:]]),
        FAUpsert(asset_id=9_002, prices=[_on(BASE_DATE, "10")]),
        FAUpsert(asset_id=9_003, prices=[_on(date.max, "10"), _on(BASE_DATE, "10"), _on(date(1066, 10, 14), "10"), _on(XR65_AFTER, "10")]),
    ]
    spy = _SessionSpy()
    error = await _refused_out_of_range(spy, data)

    assert spy.used == [], f"the session was reached for {spy.used} before the refusal"
    assert error.items == [
        {"asset_id": 9_001, "dates": [day.isoformat() for day in late[:10]]},
        {"asset_id": 9_003, "dates": [date.max.isoformat(), XR65_AFTER.isoformat()]},
    ]
    assert error.count == 14


@pytest.mark.asyncio
async def test_a_providers_prices_after_the_ceiling_are_dropped_named_and_logged(clean_prices, frozen_stored_ceiling):
    """X-R65 guard, green before N83's revision and after: under a provider's key, the points after the ceiling are
    dropped and the others written.

    Four points: 9999-12-31, a valid day, the day after the ceiling, another valid day.
    Red before X-R65: the four are stored, the message is «Upserted 4 prices», nothing is logged.
    Contract: no exception; the two valid days alone are stored, under the provider's key; the asset's result counts 2
    and its message says «rejected 2 date(s)», naming both days; a warning (or worse) names the asset and both days. A
    barrier (an event sent through ``price_store``'s own logger inside the capture) proves the capture sees that logger:
    a missing warning is a warning not logged, never a blind capture. Until N83's revision the first point was
    1899-12-31, which a provider now stores (``test_a_providers_prices_before_1900_are_stored_as_delivered``).
    """
    inside = (BASE_DATE, BASE_DATE + timedelta(days=1))
    data = [FAUpsert(asset_id=clean_prices, prices=[_on(date.max, "9"), _on(inside[0], "10"), _on(XR65_AFTER, "11"), _on(inside[1], "12")])]
    with capture_logs() as events:
        price_store_module.logger.warning(_XR65_BARRIER)
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            result = await AssetSourceManager.bulk_upsert_prices(data, session, source_plugin_key=XR65_PROVIDER)
    assert any(event.get("event") == _XR65_BARRIER for event in events), f"barrier: the log capture saw no event of price_store's logger: {events}"
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        stored = (await session.execute(select(PriceHistory).where(PriceHistory.asset_id == clean_prices).order_by(PriceHistory.date))).scalars().all()

    assert [(price.date, price.close, price.source_plugin_key) for price in stored] == [(inside[0], Decimal("10"), XR65_PROVIDER), (inside[1], Decimal("12"), XR65_PROVIDER)]
    row = next(entry for entry in result["results"] if entry["asset_id"] == clean_prices)
    assert row["count"] == 2, row
    assert "rejected 2 date(s)" in row["message"] and _names(row["message"], date.max, XR65_AFTER), row["message"]
    warnings = [event for event in events if event.get("log_level") in ("warning", "error", "critical") and event.get("event") != _XR65_BARRIER]
    assert [event for event in warnings if _names(event, clean_prices, date.max, XR65_AFTER)], f"no warning names the asset and both days: {warnings}"


@pytest.mark.asyncio
async def test_a_providers_prices_before_1900_are_stored_as_delivered(clean_prices):
    """N83 (revised 19/10): under a provider's key, points before 1900-01-01 -- 0001-01-01, 1850-06-01, 1899-12-31 --
    are stored like the valid day among them, under the provider's key.

    Red before N83's revision: the three are dropped as ``date_out_of_range``: the valid day alone is stored, the result
    counts 1 and its message says «rejected 3 date(s) outside 1900-01-01 …».
    Contract: no exception; the four days stored at their closes, under the provider's key; the asset's result counts 4,
    its message is «Upserted 4 prices», and ``rejected`` is empty.
    """
    early = (date.min, date(1850, 6, 1), XR65_BEFORE)
    data = [FAUpsert(asset_id=clean_prices, prices=[_on(early[1], "8"), _on(BASE_DATE, "10"), _on(early[0], "7"), _on(early[2], "9")])]

    result = await _accepted(data, key=XR65_PROVIDER)

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        stored = (await session.execute(select(PriceHistory).where(PriceHistory.asset_id == clean_prices).order_by(PriceHistory.date))).scalars().all()
    expected = [(early[0], Decimal("7")), (early[1], Decimal("8")), (early[2], Decimal("9")), (BASE_DATE, Decimal("10"))]
    assert [(price.date, price.close, price.source_plugin_key) for price in stored] == [(day, close, XR65_PROVIDER) for day, close in expected], result
    row = next(entry for entry in result["results"] if entry["asset_id"] == clean_prices)
    assert (row["count"], row["message"], row.get("rejected")) == (4, "Upserted 4 prices", []), row


@pytest.mark.asyncio
async def test_a_provider_refresh_stores_a_price_before_1900(assigned_asset, clean_prices, monkeypatch):
    """N83 (revised 19/10) through the refresh: the provider answers 1899-12-31 among its history; the refresh stores it
    with the others.

    The refresh hands the provider's points to ``bulk_upsert_prices`` under the provider's key (``refresh.py``), and a
    result message saying «rejected» becomes an error of the refresh. The real ceiling, tomorrow: these days are long
    past.
    Red before N83's revision: 1899-12-31 is not stored, the two other days are, and an error of the refresh names
    1899-12-31.
    Contract: the three days are stored, 1899-12-31 among them; no error of the refresh names it.
    """
    _patch_provider_with_events(monkeypatch, [_on(XR65_BEFORE, "9"), _on(BASE_DATE, "10"), _on(BASE_DATE + timedelta(days=1), "11")], [])

    result = await _refresh(assigned_asset)

    assert await _stored_days(assigned_asset) == [XR65_BEFORE, BASE_DATE, BASE_DATE + timedelta(days=1)], result
    assert not [error for error in result.errors if XR65_BEFORE.isoformat() in error], result.errors


@pytest.mark.asyncio
async def test_a_provider_refresh_counts_and_announces_a_price_before_1900(assigned_asset, clean_prices, monkeypatch):
    """N83 (revised 19/10) through the refresh: a date before 1900-01-01, which the upsert now stores, is counted and
    announced like any other.

    The setup of the case above, with two rows stored first: day 0 at 10, and 1899-12-30 at 8. The provider answers
    1899-12-30 (9), 1899-12-31 (9.5), day 0 (20) and day 1 (21). The refresh counts its changes, and lists them in
    ``changed_points`` for the chart, before the upsert.
    Red before N83's revision: the upsert keeps day 0 and day 1 alone and leaves 1899-12-30 at 8; the count follows it:
    1 inserted, 1 updated, 2 changed, ``changed_points`` day 0 and day 1.
    Contract: the four days stored as delivered; 2 inserted (1899-12-31, day 1), 2 updated (1899-12-30, day 0), 4
    changed, ``changed_points`` the four days. ``points_fetched`` counts what the provider delivered: not pinned here.
    """
    stored_first, before, day0, day1 = XR65_BEFORE - timedelta(days=1), XR65_BEFORE, BASE_DATE, BASE_DATE + timedelta(days=1)
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        session.add_all([PriceHistory(asset_id=assigned_asset, date=day, close=Decimal(close), currency="USD", source_plugin_key=XR65_PROVIDER) for day, close in ((stored_first, "8"), (day0, "10"))])
        await session.commit()
    assert await _stored_closes(assigned_asset) == {stored_first: Decimal("8"), day0: Decimal("10")}, "barrier: the rows stored before the refresh are not the two written"
    _patch_provider_with_events(monkeypatch, [_on(stored_first, "9"), _on(before, "9.5"), _on(day0, "20"), _on(day1, "21")], [])

    result = await _refresh(assigned_asset)

    stored = await _stored_closes(assigned_asset)
    assert stored == {stored_first: Decimal("9"), before: Decimal("9.5"), day0: Decimal("20"), day1: Decimal("21")}, f"the four days should be stored as delivered: {stored}; {result!r}"
    counted = (result.inserted_count, result.updated_count, result.points_changed, sorted(point.date for point in result.changed_points or []))
    assert counted == (2, 2, 4, [stored_first, before, day0, day1]), f"(inserted, updated, changed, changed_points) = {counted}: the dates before 1900, {stored_first} and {before}, are not counted or announced (points_fetched {result.points_fetched})"


@pytest.mark.asyncio
async def test_a_provider_refresh_neither_counts_nor_announces_a_price_after_the_ceiling(assigned_asset, clean_prices, frozen_stored_ceiling, monkeypatch):
    """X-R65 guard through the refresh, green before N83's revision and after: a date the upsert drops for lying after the
    (frozen) ceiling is neither counted nor announced, like a value no column can keep (W-B62).

    Day 0 is stored first at 10. The refresh asks from day 0 to the day after the ceiling -- a range long past, so the
    refresh's own cut (prices up to yesterday) keeps that day -- and the provider answers day 0 (20), day 1 (21) and the
    day after the ceiling (22). The refresh counts its changes before the upsert, which drops the day after the ceiling.
    Contract: day 0 and day 1 stored; 1 inserted (day 1), 1 updated (day 0), 2 changed, ``changed_points`` day 0 and day
    1 alone; an error of the refresh names the day after the ceiling. Until N83's revision the date pinned here lay
    before 1900, and those are now counted (``test_a_provider_refresh_counts_and_announces_a_price_before_1900``).
    """
    day0, day1 = BASE_DATE, BASE_DATE + timedelta(days=1)
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        session.add(PriceHistory(asset_id=assigned_asset, date=day0, close=Decimal("10"), currency="USD", source_plugin_key=XR65_PROVIDER))
        await session.commit()
    assert await _stored_closes(assigned_asset) == {day0: Decimal("10")}, "barrier: the row stored before the refresh is not the one written"
    _patch_provider_with_events(monkeypatch, [_on(day0, "20"), _on(day1, "21"), _on(XR65_AFTER, "22")], [])

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        item = FARefreshItem(asset_id=assigned_asset, date_range=SyncDateRangeModel(start=day0, end=XR65_AFTER))
        response = await AssetSourceManager.bulk_refresh_prices([item], session)
    result = next(r for r in response.results if r.asset_id == assigned_asset)

    stored = await _stored_closes(assigned_asset)
    assert stored == {day0: Decimal("20"), day1: Decimal("21")}, f"barrier: the upsert should store day 0 and day 1 alone: {stored}; {result!r}"
    counted = (result.inserted_count, result.updated_count, result.points_changed, sorted(point.date for point in result.changed_points or []))
    assert counted == (1, 1, 2, [day0, day1]), f"(inserted, updated, changed, changed_points) = {counted}: the date the upsert dropped, {XR65_AFTER}, is counted or announced (points_fetched {result.points_fetched})"
    assert [error for error in result.errors if XR65_AFTER.isoformat() in error], result.errors


# ─────────────────────────────────────────────────────────────────────────────
# X-R71: a manual upsert holding a price in another currency than its asset's is refused whole, before any write
#
# The defect: ``bulk_upsert_prices`` checked the currency inside its loop, asset by asset in the request's order, after
# the assets before it had been written and committed; a mismatch raised ``ValueError`` (the route's 400) and left them
# stored: the upload was not all or nothing.
#
# Contract (MANUAL; the digits refusal, a ``ValueError``, and the dates, ``DateOutOfRangeError``, come first, on the
# input alone):
# * one read of ``Asset.id, Asset.currency`` for the request's distinct asset ids (in slices of 500), and nothing else
#   asked of the session -- no add, flush or commit, every statement a SELECT; then, for each item in request order
#   whose asset exists, the points whose ``price.currency or asset.currency`` is not the asset's give one entry
#   ``{"asset_id", "expected": the asset's currency, "found": the other currencies given, first seen first, "dates":
#   their ISO dates, request order, ten at most}``; an item whose asset does not exist is not checked (the loop answers
#   «Asset N not found», as before, when nothing else is at fault);
# * any entry raises ``price_store.PriceCurrencyMismatchError`` -- a plain ``Exception``, no ``ValueError`` -- whose
#   ``items`` hold every entry and ``count`` every offending date; nothing is written, for any asset of the request.
#   ``price_store.price_currency_mismatch_detail(items, count)`` is the route's 422 detail: ``{"code":
#   "price_currency_mismatch", "message", "items": items[:10], "count"}``;
# * under a provider's key nothing changes: the check in the loop raises ``ValueError`` («Currency mismatch for asset
#   …»), as before.
#
# Both names are read from ``price_store`` inside the cases (``_refused_for_currency``): before X-R71 they do not exist,
# and the cases fail on what the upsert did instead of breaking the module's import. The days are this unit's window
# (``BASE_DATE``), inside the real bounds: no ceiling to freeze. The route's 422 is pinned by
# ``api prices-currency-coherence``.
# ─────────────────────────────────────────────────────────────────────────────

XR71_ASSET_COUNT = 12


def _in(day: date, close: str, currency: str) -> FAPricePoint:
    """A close of ``close`` on ``day``, in ``currency``."""
    return FAPricePoint(date=day, close=Decimal(close), currency=currency)


def _statement_kind(statement: object) -> str:
    """The first SQL keyword of ``statement`` (``SELECT``, ``INSERT`` …), or its class name when it does not print."""
    try:
        words = str(statement).split()
    except Exception:  # a statement the default compiler cannot print is still recorded: by its class, never as a SELECT
        return type(statement).__name__
    return words[0].upper() if words else type(statement).__name__


class _StatementSpy(_SessionSpy):
    """``_SessionSpy`` on a session of the lane database that also records, in ``statements``, the kind of every
    statement it executes (``_statement_kind``)."""

    def __init__(self, real: AsyncSession) -> None:
        super().__init__(real)
        self.statements: list[str] = []

    def __getattr__(self, name: str):
        served = super().__getattr__(name)
        if name != "execute":
            return served

        async def _execute(statement, *args, **kwargs):
            self.statements.append(_statement_kind(statement))
            return await served(statement, *args, **kwargs)

        return _execute


@pytest_asyncio.fixture
async def xr71_assets():
    """Twelve assets of this unit's own, in USD and without a price; removed with their prices afterwards."""
    marker = f"{unique_id('UpsertGuards')} {uuid.uuid4().hex[:8]}"
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        assets = [Asset(display_name=f"Upsert Guard X-R71 {marker} {n}", currency="USD", asset_type=AssetType.STOCK, active=True) for n in range(XR71_ASSET_COUNT)]
        session.add_all(assets)
        await session.commit()
        asset_ids = [asset.id for asset in assets]
    yield asset_ids
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        await session.execute(delete(PriceHistory).where(PriceHistory.asset_id.in_(asset_ids)))
        await session.execute(delete(Asset).where(Asset.id.in_(asset_ids)))
        await session.commit()


async def _refused_for_currency(spy: _SessionSpy, data: list[FAUpsert]):
    """The ``PriceCurrencyMismatchError`` a MANUAL upsert of ``data`` on ``spy`` raises; when it raises anything else, or
    nothing, the test fails saying what the upsert did and what it asked of the session."""
    error_class = getattr(price_store_module, "PriceCurrencyMismatchError", None)
    try:
        result = await AssetSourceManager.bulk_upsert_prices(data, spy)
    except Exception as error:
        if error_class is not None and isinstance(error, error_class):
            return error
        pytest.fail(f"no PriceCurrencyMismatchError: the upsert raised {type(error).__name__}({error}), after reaching the session for {spy.used}")
    pytest.fail(f"no PriceCurrencyMismatchError: the upsert answered {result}, after reaching the session for {spy.used}")


@pytest.mark.asyncio
async def test_a_currency_mismatch_refuses_the_clean_asset_before_it_after_reads_only(clean_prices, xr65_second_asset):
    """X-R71: a clean asset first, then one with a price in EUR: neither is written, and one SELECT alone reaches the
    session.

    Before the fix: the upsert works asset by asset and commits as it goes: the first asset's two prices are written and
    committed, then the second's EUR price raises ``ValueError`` («Currency mismatch for asset …», the route's 400).
    Contract: ``PriceCurrencyMismatchError``, no ``ValueError``, naming the second asset alone (``items`` ``[{"asset_id":
    second, "expected": "USD", "found": ["EUR"], "dates": [its EUR day]}]``, ``count`` 1); the session was asked for
    ``execute`` alone -- no add, flush or commit -- and ran one statement, a SELECT (the assets' currencies); neither
    asset has a price.
    """
    eur_day = BASE_DATE + timedelta(days=3)
    data = [
        FAUpsert(asset_id=clean_prices, prices=[_on(BASE_DATE, "10"), _on(BASE_DATE + timedelta(days=1), "11")]),
        FAUpsert(asset_id=xr65_second_asset, prices=[_on(BASE_DATE + timedelta(days=2), "12"), _in(eur_day, "13", "EUR")]),
    ]
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        spy = _StatementSpy(session)
        error = await _refused_for_currency(spy, data)

    assert not isinstance(error, ValueError), f"{type(error).__mro__}: a manual currency refusal is no ValueError (the route's 400)"
    assert set(spy.used) == {"execute"}, f"the session was asked for {spy.used} before the refusal: reads alone"
    assert spy.statements == ["SELECT"], f"statements before the refusal: {spy.statements}; one read of the assets' currencies, nothing else"
    assert (error.items, error.count) == ([{"asset_id": xr65_second_asset, "expected": "USD", "found": ["EUR"], "dates": [eur_day.isoformat()]}], 1)
    assert await _stored_days(clean_prices) == []
    assert await _stored_days(xr65_second_asset) == []


@pytest.mark.asyncio
async def test_a_currency_refusal_names_each_asset_at_fault_its_currencies_and_ten_dates_at_most(xr71_assets):
    """X-R71: the numbers of a refusal: twelve assets of this unit at fault, and an asset id no asset has among them.

    The first asset: twelve days in CHF, newest first, a USD day among them; the second: EUR, GBP, EUR and CHF on four
    days, then a day without a currency (the asset's own); between the second and the third, an asset id no asset has,
    with a price in EUR; the ten others: a USD day, then a day in JPY.
    Before the fix: the first asset's CHF prices raise ``ValueError`` («Currency mismatch for asset …»).
    Contract: ``items`` the twelve assets in request order, the unknown id not checked; each ``expected`` USD, ``found``
    its other currencies first seen first (EUR, GBP, CHF: not sorted), ``dates`` its offending days in request order (not
    sorted), the first one's ten at most; ``count`` 26, every offending date of the twelve; nothing stored for any of
    them. ``price_currency_mismatch_detail(items, count)``: the code ``price_currency_mismatch``, a message naming the
    count, the first ten entries, ``count`` 26.
    """
    first, second, *others = xr71_assets
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        missing_id = (await session.execute(select(Asset.id).order_by(Asset.id.desc()).limit(1))).scalar_one() + 100_000
    chf_days = [BASE_DATE + timedelta(days=40 - n) for n in range(12)]
    mixed = [(BASE_DATE + timedelta(days=n), currency) for n, currency in enumerate(("EUR", "GBP", "EUR", "CHF"))]
    jpy_day = BASE_DATE + timedelta(days=1)
    data = [
        FAUpsert(asset_id=first, prices=[_in(day, "10", "CHF") for day in chf_days[:5]] + [_on(BASE_DATE, "10")] + [_in(day, "10", "CHF") for day in chf_days[5:]]),
        FAUpsert(asset_id=second, prices=[_in(day, "10", currency) for day, currency in mixed] + [FAPricePoint(date=BASE_DATE + timedelta(days=4), close=Decimal("10"))]),
        FAUpsert(asset_id=missing_id, prices=[_in(BASE_DATE, "10", "EUR")]),
        *[FAUpsert(asset_id=asset_id, prices=[_on(BASE_DATE, "10"), _in(jpy_day, "10", "JPY")]) for asset_id in others],
    ]
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        spy = _StatementSpy(session)
        error = await _refused_for_currency(spy, data)

    expected = [
        {"asset_id": first, "expected": "USD", "found": ["CHF"], "dates": [day.isoformat() for day in chf_days[:10]]},
        {"asset_id": second, "expected": "USD", "found": ["EUR", "GBP", "CHF"], "dates": [day.isoformat() for day, _ in mixed]},
        *[{"asset_id": asset_id, "expected": "USD", "found": ["JPY"], "dates": [jpy_day.isoformat()]} for asset_id in others],
    ]
    assert error.items == expected, error.items
    assert error.count == 26, error.count
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        stored = (await session.execute(select(PriceHistory.asset_id).where(PriceHistory.asset_id.in_(xr71_assets)))).scalars().all()
    assert stored == [], f"prices stored for the assets {sorted(set(stored))}"

    detail_of = getattr(price_store_module, "price_currency_mismatch_detail", None)
    assert detail_of is not None, "no price_store.price_currency_mismatch_detail"
    detail = detail_of(error.items, error.count)
    assert set(detail) == {"code", "message", "items", "count"}, detail
    assert (detail["code"], detail["items"], detail["count"]) == ("price_currency_mismatch", expected[:10], 26), detail
    assert isinstance(detail["message"], str) and "26" in detail["message"], detail["message"]


@pytest.mark.asyncio
async def test_a_date_out_of_range_is_refused_before_the_currencies_are_read(clean_prices, xr65_second_asset, frozen_stored_ceiling):
    """X-R71 guard, green before the fix and after: the dates are checked first, on the input alone (X-R65).

    The first asset with a day in EUR, the second with a price on the day after the (frozen) ceiling -- until N83's
    revision on 1899-12-31, a day the check now lets through.
    Contract: ``DateOutOfRangeError`` naming the second asset, the session never reached (the currencies are not read),
    and neither asset has a price.
    """
    data = [
        FAUpsert(asset_id=clean_prices, prices=[_on(BASE_DATE, "10"), _in(BASE_DATE + timedelta(days=1), "11", "EUR")]),
        FAUpsert(asset_id=xr65_second_asset, prices=[_on(BASE_DATE + timedelta(days=2), "12"), _on(XR65_AFTER, "13")]),
    ]
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        spy = _SessionSpy(session)
        error = await _refused_out_of_range(spy, data)

    assert spy.used == [], f"the session was reached for {spy.used} before the refusal"
    assert (error.items, error.count) == ([{"asset_id": xr65_second_asset, "dates": [XR65_AFTER.isoformat()]}], 1)
    assert await _stored_days(clean_prices) == []
    assert await _stored_days(xr65_second_asset) == []


@pytest.mark.asyncio
async def test_a_providers_currency_mismatch_still_raises_value_error(clean_prices):
    """X-R71 guard, green before the fix and after: under a provider's key the check stays in the loop, a ``ValueError``.

    One asset: a USD day, then a EUR day, under ``XR65_PROVIDER``.
    Contract: ``ValueError`` saying «Currency mismatch for asset …» (this one), never ``PriceCurrencyMismatchError``; the
    asset has no price (the check comes before its writes).
    """
    data = [FAUpsert(asset_id=clean_prices, prices=[_on(BASE_DATE, "10"), _in(BASE_DATE + timedelta(days=1), "11", "EUR")])]
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        with pytest.raises(ValueError, match=rf"Currency mismatch for asset {clean_prices}\b") as raised:
            await AssetSourceManager.bulk_upsert_prices(data, session, source_plugin_key=XR65_PROVIDER)

    assert type(raised.value).__name__ != "PriceCurrencyMismatchError", f"{type(raised.value).__mro__}: a provider's mismatch is not the manual refusal"
    assert await _stored_days(clean_prices) == []


# ─────────────────────────────────────────────────────────────────────────────
# X-R46: an asset's result names the dates the upsert refused, machine-readable
#
# The defect, on HEAD 1c1456713: ``bulk_upsert_prices`` drops a date, asset by asset, in three cases -- a candle whose
# close lies outside its own [low, high] (``rejected_dates``, under any key), a provider's date after
# ``latest_stored_date()`` (``out_of_range_dates``, X-R65; outside [1900-01-01, tomorrow] until N83's revision, 19/10)
# and a provider's value no price column can keep (``unstorable_dates``, W-B58) -- and says so only in the English
# ``results[].message`` («Upserted N prices; rejected 1 date(s) with impossible OHLC …»), while ``count`` leaves them
# out. The Data Editor cannot read which rows were refused, and announces every row it sent as saved.
#
# Contract (X-R46): ``schemas.prices.FAPriceRejection`` (a ``StrictModel``) {``date``, ``reason``:
# ``ohlc_inconsistent`` | ``date_out_of_range`` | ``value_not_storable``}; ``FAUpsertResult.rejected:
# List[FAPriceRejection]``, ``[]`` by default, sorted by date. ``bulk_upsert_prices`` puts it in each asset's result
# dict, from its three lists: ``rejected_dates`` → ``ohlc_inconsistent``, ``out_of_range_dates`` →
# ``date_out_of_range``, ``unstorable_dates`` → ``value_not_storable``. ``count`` and the English message are unchanged.
#
# A rejection is compared as JSON (its date ISO), whether the service holds it as a dict or as the model, its date as a
# date or as text; and through ``FAUpsertResult``, as the route parses each result (``FAUpsertResult(**r)``).
# ``FAPriceRejection`` is read from ``schemas.prices`` inside the cases: before X-R46 it does not exist, and the cases
# fail on what the upsert answered instead of breaking the module's import. The prices go on this unit's own asset
# (``clean_prices``), in its window; a provider's key and the frozen ceiling are X-R65's.
# ─────────────────────────────────────────────────────────────────────────────

XR46_PRICE_REASONS = ("ohlc_inconsistent", "date_out_of_range", "value_not_storable")


def _xr46_as_json(entry: object) -> dict:
    """One rejection as JSON, its date ISO: a model through ``model_dump``, a dict with its dates written out."""
    if hasattr(entry, "model_dump"):
        return entry.model_dump(mode="json", by_alias=True)
    return {key: value.isoformat() if isinstance(value, date) else value for key, value in dict(entry).items()}


def _xr46_rejected(row: dict) -> list[dict]:
    """The asset's result ``rejected``, as JSON; a result without it fails the test, naming what it holds instead."""
    if "rejected" not in row:
        pytest.fail(f"X-R46: the asset's result has no 'rejected', its refused dates are told only in its English message: {row}")
    return [_xr46_as_json(entry) for entry in row["rejected"]]


def _xr46_route_rejected(row: dict) -> list[dict]:
    """``rejected`` as ``POST /assets/prices`` answers it: the service's result parsed into ``FAUpsertResult``, as the
    route does, each entry a ``FAPriceRejection``, written as JSON."""
    rejection = getattr(prices_schemas, "FAPriceRejection", None)
    assert rejection is not None, "X-R46: backend.app.schemas.prices has no FAPriceRejection"
    parsed = FAUpsertResult(**row)
    assert all(isinstance(entry, rejection) for entry in parsed.rejected), parsed.rejected
    return parsed.model_dump(mode="json", by_alias=True)["rejected"]


def _xr46_unordered(rejections: list[dict]) -> list[str]:
    """The rejections as sorted canonical JSON texts: the same entries, whatever their order."""
    return sorted(json.dumps(entry, sort_keys=True, default=str) for entry in rejections)


async def _xr46_upsert(asset_id: int, prices: list[FAPricePoint], key: str = "MANUAL") -> dict:
    """``bulk_upsert_prices`` of ``prices`` for ``asset_id`` under ``key``: the asset's own result."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        result = await AssetSourceManager.bulk_upsert_prices([FAUpsert(asset_id=asset_id, prices=prices)], session, source_plugin_key=key)
    return next(entry for entry in result["results"] if entry["asset_id"] == asset_id)


@pytest.mark.asyncio
async def test_xr46_a_manual_close_outside_its_low_high_is_listed_in_rejected(clean_prices: int):
    """X-R46: a manual upsert of two candles, the first with its close (50) outside its own [9, 12].

    Red on HEAD 1c1456713: the asset's result is ``{asset_id, count, message}``; the refused date is told only in the
    English message («… rejected 1 date(s) with impossible OHLC …»), and ``FAUpsertResult`` has no ``rejected``: the
    Data Editor announces the row as saved.
    Contract: the second day alone stored; ``count`` 1 and the message as before; ``rejected`` ``[{"date": the first
    day, "reason": "ohlc_inconsistent"}]``, in the service's result and through ``FAUpsertResult``.
    """
    refused, kept = BASE_DATE, BASE_DATE + timedelta(days=1)

    row = await _xr46_upsert(clean_prices, [_point(0, "50", low="9", high="12"), _point(1, "11", low="9", high="12")])

    assert await _stored_days(clean_prices) == [kept], "barrier: the inconsistent candle should be refused, the other stored"
    assert row["count"] == 1 and row["message"].startswith("Upserted 1 prices; rejected 1 date(s) with impossible OHLC") and refused.isoformat() in row["message"], row
    expected = [{"date": refused.isoformat(), "reason": "ohlc_inconsistent"}]
    assert _xr46_rejected(row) == expected, row
    assert _xr46_route_rejected(row) == expected


@pytest.mark.asyncio
async def test_xr46_guard_a_clean_manual_upsert_lists_no_rejection(clean_prices: int):
    """X-R46 guard of the cure: a manual upsert of two consistent candles.

    Red on HEAD 1c1456713 only because the asset's result has no ``rejected``; green once it has.
    Contract: both days stored; ``count`` 2 and the message «Upserted 2 prices»; ``rejected`` ``[]``, in the service's
    result (the key is there) and through ``FAUpsertResult``.
    """
    row = await _xr46_upsert(clean_prices, [_point(0, "10", low="9", high="12"), _point(1, "11", low="9", high="12")])

    assert await _stored_days(clean_prices) == [BASE_DATE, BASE_DATE + timedelta(days=1)], "barrier: both candles should be stored"
    assert (row["count"], row["message"]) == (2, "Upserted 2 prices"), row
    assert _xr46_rejected(row) == []
    assert _xr46_route_rejected(row) == []


@pytest.mark.asyncio
async def test_xr46_a_providers_dates_outside_the_bounds_are_listed_in_rejected(clean_prices: int, frozen_stored_ceiling: date):
    """X-R46 on X-R65's provider case: under a provider's key, 9999-12-31, a day, the day after the (frozen) ceiling,
    another day.

    Red on HEAD 1c1456713: the two dropped dates are told only in the message («rejected 2 date(s) …»).
    Green before N83's revision and after (a guard of it): until then the first date was 1899-12-31, which a provider
    now stores; the two dates here lie after the ceiling under either contract.
    Contract: the two days inside alone stored; ``count`` 2 and the message as before, naming both dates; ``rejected``
    the two dates after the ceiling, ``date_out_of_range``, by date, in the service's result and through
    ``FAUpsertResult``.
    """
    inside = [BASE_DATE, BASE_DATE + timedelta(days=1)]

    row = await _xr46_upsert(clean_prices, [_on(date.max, "9"), _on(inside[0], "10"), _on(XR65_AFTER, "11"), _on(inside[1], "12")], key=XR65_PROVIDER)

    assert await _stored_days(clean_prices) == inside, "barrier: the two dates after the ceiling should be dropped, the others stored"
    assert row["count"] == 2 and "rejected 2 date(s)" in row["message"] and _names(row["message"], XR65_AFTER, date.max), row
    expected = [{"date": XR65_AFTER.isoformat(), "reason": "date_out_of_range"}, {"date": date.max.isoformat(), "reason": "date_out_of_range"}]
    assert _xr46_rejected(row) == expected, row
    assert _xr46_route_rejected(row) == expected


@pytest.mark.asyncio
async def test_xr46_a_providers_three_kinds_of_refusal_are_listed_by_date(clean_prices: int, frozen_stored_ceiling: date):
    """X-R46: under a provider's key, a date refused for each reason, out of date order: day 2, a candle whose close (50)
    lies outside its [9, 12]; the day after the (frozen) ceiling; day 1, a sound close; day 0, a close no price column
    can keep (1E+15); 1899-12-31, a candle whose close (50) lies outside its [9, 12] as well.

    Red on HEAD 1c1456713: the four refusals are told only in the English message.
    Red before N83's revision: 1899-12-31 is refused for its date (``date_out_of_range``) before its candle is read.
    Contract: day 1 alone stored; ``count`` 1 and the message as before, naming the three kinds; ``rejected`` sorted by
    date -- 1899-12-31 ``ohlc_inconsistent`` (its date no refusal since N83's revision), day 0 ``value_not_storable``,
    day 2 ``ohlc_inconsistent``, the day after the ceiling ``date_out_of_range`` -- an order neither of the input nor of
    any concatenation of the three lists (the two candles lie on either side of day 0). The service's entries are
    compared whatever their order (where the sort happens is the cure's choice); the route's, through ``FAUpsertResult``,
    in that order.
    """
    day0, day1, day2 = (BASE_DATE + timedelta(days=offset) for offset in range(3))
    old_candle = FAPricePoint(date=XR65_BEFORE, close=Decimal("50"), low=Decimal("9"), high=Decimal("12"), currency="USD")
    prices = [_point(2, "50", low="9", high="12"), _on(XR65_AFTER, "11"), _on(day1, "11"), _on(day0, "1E+15"), old_candle]

    row = await _xr46_upsert(clean_prices, prices, key=XR65_PROVIDER)

    assert await _stored_days(clean_prices) == [day1], "barrier: day 1 alone should be stored"
    expected = [
        {"date": XR65_BEFORE.isoformat(), "reason": "ohlc_inconsistent"},
        {"date": day0.isoformat(), "reason": "value_not_storable"},
        {"date": day2.isoformat(), "reason": "ohlc_inconsistent"},
        {"date": XR65_AFTER.isoformat(), "reason": "date_out_of_range"},
    ]
    assert _xr46_unordered(_xr46_rejected(row)) == _xr46_unordered(expected), row
    assert _xr46_route_rejected(row) == expected
    assert row["count"] == 1 and all(said in row["message"] for said in ("rejected 2 date(s) with impossible OHLC", "no price column can keep")) and _names(row["message"], XR65_AFTER), row


def test_xr46_fa_price_rejection_holds_one_of_three_reasons_and_a_result_defaults_to_none():
    """X-R46, the schemas alone (no database): ``FAPriceRejection`` holds a date and one of the three reasons, and
    refuses any other reason; an ``FAUpsertResult`` built without ``rejected`` -- the service's «Asset N not found» and
    «No prices to upsert» results -- answers ``[]``.

    Red on HEAD 1c1456713: ``schemas.prices`` has no ``FAPriceRejection``.
    """
    rejection = getattr(prices_schemas, "FAPriceRejection", None)
    assert rejection is not None, "X-R46: backend.app.schemas.prices has no FAPriceRejection"
    for reason in XR46_PRICE_REASONS:
        assert rejection(date=BASE_DATE, reason=reason).model_dump(mode="json", by_alias=True) == {"date": BASE_DATE.isoformat(), "reason": reason}
    with pytest.raises(ValidationError):
        rejection(date=BASE_DATE, reason="not_a_reason")
    assert FAUpsertResult(asset_id=1, count=0, message="Asset 1 not found").model_dump(mode="json", by_alias=True).get("rejected") == []


# ─────────────────────────────────────────────────────────────────────────────
# The erase sentinel -1 is no bound for the OHLC check (the docs-writer's finding, 17/10)
#
# The defect, on HEAD 1c1456713 with X-R46's cure: the strict branch of the OHLC integrity policy (see its section above;
# ``if price.low is not None and price.high is not None`` in ``bulk_upsert_prices``) reads the raw incoming ``price.low``
# and ``price.high``, so it takes the erase sentinel ``-1`` (F.4: «SET NULL», which ``_merge_field`` resolves to None
# just before) for a real bound. In the asset data editor, erasing High while Low stays (close 12, low 11, high -1) is
# refused as ``ohlc_inconsistent`` (low above high), and erasing both (-1, -1) too (close 12 outside [-1, -1]): the date
# is not saved, and its row keeps the bounds the user erased.
#
# Contract: an erased bound is no bound. The strict check runs only when both incoming bounds are real; otherwise the
# existing branch applies: the merged bounds widened around the close when both exist, else written as they are. An edit
# left with one real bound is written as it is, even on the wrong side of the close (decided 17/10: today's one-bound
# partial update; X-R78 will decide whether to refuse it instead).
#
# Each case seeds ``ERASE_DAY`` on this unit's own asset (``clean_prices``) with open/high/low/close 12/14/10/12 through
# a first manual upsert, checked as a barrier, then sends its manual edit of that day, open and volume omitted (F.4:
# kept). The upsert and its ``rejected`` are read as X-R46's cases read them (``_xr46_upsert``, ``_xr46_rejected``).
# ─────────────────────────────────────────────────────────────────────────────

ERASE_OFFSET = 0
ERASE_DAY = BASE_DATE + timedelta(days=ERASE_OFFSET)
ERASE_SEED = (Decimal("12"), Decimal("14"), Decimal("10"), Decimal("12"))  # open, high, low, close of ERASE_DAY before each edit


async def _stored_ohlc(asset_id: int, day: date) -> tuple | None:
    """The asset's (open, high, low, close) on ``day``, None without a row, read by a session of its own."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        row = (await session.execute(select(PriceHistory.open, PriceHistory.high, PriceHistory.low, PriceHistory.close).where(PriceHistory.asset_id == asset_id, PriceHistory.date == day))).one_or_none()
    return None if row is None else tuple(row)


async def _erase_seeded(asset_id: int) -> None:
    """``ERASE_DAY`` stored as ``ERASE_SEED`` through a first manual upsert, checked: a barrier."""
    seed = await _xr46_upsert(asset_id, [_point(ERASE_OFFSET, "12", low="10", high="14", open_="12")])
    stored = await _stored_ohlc(asset_id, ERASE_DAY)
    assert (seed["count"], stored) == (1, ERASE_SEED), f"barrier: the seed of {ERASE_DAY} should store open/high/low/close 12/14/10/12: {seed}; stored {stored}"


async def _erase_outcome(asset_id: int, row: dict) -> tuple:
    """What an edit of ``ERASE_DAY`` came to: the asset's ``count``, its ``rejected`` as JSON and the day's stored
    (open, high, low, close)."""
    return row["count"], _xr46_rejected(row), await _stored_ohlc(asset_id, ERASE_DAY)


@pytest.mark.asyncio
async def test_a_manual_edit_erasing_high_is_saved_not_rejected(clean_prices: int):
    """The day stored 12/14/10/12 (open/high/low/close); the editor erases High and sets Low to 11, the close staying 12:
    close 12, low 11, high -1.

    Red on HEAD 1c1456713 with X-R46's cure: the check reads high -1 as a bound, below low 11: the date is refused
    (``count`` 0, ``rejected`` ``[{the day, "ohlc_inconsistent"}]``) and the row keeps 12/14/10/12.
    Contract: an erased bound is no bound: ``count`` 1, ``rejected`` ``[]``; the row open 12 (omitted: kept), high NULL,
    low 11, close 12 -- one merged bound left, nothing to widen.
    """
    await _erase_seeded(clean_prices)

    row = await _xr46_upsert(clean_prices, [_point(ERASE_OFFSET, "12", low="11", high="-1")])

    outcome = await _erase_outcome(clean_prices, row)
    assert outcome == (1, [], (Decimal("12"), None, Decimal("11"), Decimal("12"))), f"(count, rejected, open/high/low/close) = {outcome}: {row['message']}"


@pytest.mark.asyncio
async def test_a_manual_edit_erasing_both_bounds_is_saved_not_rejected(clean_prices: int):
    """The day stored 12/14/10/12 (open/high/low/close); the editor erases High and Low, the close staying 12: close 12,
    low -1, high -1.

    Red on HEAD 1c1456713 with X-R46's cure: the check reads [-1, -1] as the bounds, the close 12 outside them: the date
    is refused (``count`` 0, ``rejected`` ``[{the day, "ohlc_inconsistent"}]``) and the row keeps 12/14/10/12.
    Contract: ``count`` 1, ``rejected`` ``[]``; the row open 12 (omitted: kept), high NULL, low NULL, close 12.
    """
    await _erase_seeded(clean_prices)

    row = await _xr46_upsert(clean_prices, [_point(ERASE_OFFSET, "12", low="-1", high="-1")])

    outcome = await _erase_outcome(clean_prices, row)
    assert outcome == (1, [], (Decimal("12"), None, None, Decimal("12"))), f"(count, rejected, open/high/low/close) = {outcome}: {row['message']}"


@pytest.mark.asyncio
async def test_a_manual_edit_erasing_low_with_high_below_the_close_is_saved_as_is(clean_prices: int):
    """The mirror that tells the cures apart: the day stored 12/14/10/12 (open/high/low/close); the editor erases Low and
    sets High to 11, below the close 12: close 12, low -1, high 11.

    Red on HEAD 1c1456713 with X-R46's cure, and under a cure that resolves the sentinel of High alone: the check reads
    low -1 as a bound, the close 12 outside [-1, 11]: the date is refused (``count`` 0, ``rejected`` ``[{the day,
    "ohlc_inconsistent"}]``) and the row keeps 12/14/10/12. The two erasing cases above pass under either cure; this one
    only when the sentinel is resolved on both bounds.
    Contract (decided 17/10): one real incoming bound is not checked; the edit is written as it is, as today's one-bound
    partial update is: ``count`` 1, ``rejected`` ``[]``; the row open 12 (omitted: kept), high 11, low NULL, close 12.
    This pins the current one-bound policy, not an endorsement of the row it leaves, a close above its only bound:
    X-R78 will decide whether a lone real bound on the wrong side of the close should be refused instead, and this case
    changes with that decision.
    """
    await _erase_seeded(clean_prices)

    row = await _xr46_upsert(clean_prices, [_point(ERASE_OFFSET, "12", low="-1", high="11")])

    outcome = await _erase_outcome(clean_prices, row)
    assert outcome == (1, [], (Decimal("12"), Decimal("11"), None, Decimal("12"))), f"(count, rejected, open/high/low/close) = {outcome}: {row['message']}"


@pytest.mark.asyncio
async def test_a_manual_edit_with_two_real_bounds_and_the_close_below_low_is_still_rejected(clean_prices: int):
    """Guard, green before the cure and after: the strict check still runs when both incoming bounds are real. The day
    stored 12/14/10/12 (open/high/low/close); the edit: close 12, low 13, high 14.

    Contract (unchanged): the date refused, ``count`` 0, ``rejected`` ``[{the day, "ohlc_inconsistent"}]``; the row keeps
    12/14/10/12.
    """
    await _erase_seeded(clean_prices)

    row = await _xr46_upsert(clean_prices, [_point(ERASE_OFFSET, "12", low="13", high="14")])

    outcome = await _erase_outcome(clean_prices, row)
    assert outcome == (0, [{"date": ERASE_DAY.isoformat(), "reason": "ohlc_inconsistent"}], ERASE_SEED), f"(count, rejected, open/high/low/close) = {outcome}: {row['message']}"

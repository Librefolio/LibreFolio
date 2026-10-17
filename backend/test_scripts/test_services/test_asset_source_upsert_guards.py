"""Integrity guards and identifier filters of AssetSourceManager.

Isolation: WRITE_GLOBAL. ``Asset`` and ``PriceHistory`` carry no ``user_id``, so
the asset created here and the price rows written against it are visible to every
concurrently running test. The module fixture creates exactly one asset with a
unique display name and deletes it -- together with every price row it produced --
in teardown, so nothing survives the unit. X-R65's section adds a second asset for
one test (``xr65_second_asset``), removed the same way.

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
import sys
import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio

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
from backend.app.schemas.assets.assets import FAAinfoFiltersRequest
from backend.app.schemas.assets.events import FAAssetEventPoint, FAEventUpsert
from backend.app.schemas.common import Currency, DateRangeModel
from backend.app.schemas.prices import FAHistoricalData, FAPricePoint, FAPriceQueryItem, FAUpsert
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
# X-R65 (night decision N83): a stored price is dated within [1900-01-01, latest_range_end()]
#
# J's SEC8-1b: one price dated 0001-01-01 makes a backward fill or a risk replay walk about 740 000 days for its asset.
# A transaction refuses such a date since N74 (``transaction_date_bounds``, ``dateOutOfRange``); a price did not:
# ``bulk_upsert_prices`` stored whatever date it was given, a manual one (``POST /assets/prices``) as a provider's (the
# refresh, ``refresh.py``, under the provider's key).
#
# Contract (coordinator decisions D1–D3, 17/10):
# * MANUAL: every point's date is checked against ``date_range_limits.stored_date_bounds()`` --
#   ``(EARLIEST_RANGE_START, latest_range_end())``, both bounds included -- before any database statement. One date
#   outside raises ``date_range_limits.DateOutOfRangeError``, not a ``ValueError``: ``items`` one entry per asset holding
#   such dates, in input order, ``{"asset_id": id, "dates": its offending dates as ISO strings, in input order, ten at
#   most}``; ``count`` every offending date of the request; ``earliest`` and ``latest`` the bounds. Nothing is written,
#   for any asset of the request.
# * Any other key (a provider's): the points outside are dropped before any write, like the ones no column can keep
#   (W-B58) -- a warning logged, the asset's result message saying so («rejected N date(s) …», the dates listed) -- and
#   every other point is written.
# * The refresh counts its changes, and lists them in ``changed_points`` for the chart, before it upserts (follow-up,
#   17/10): a date the upsert drops for lying outside the bounds is neither counted nor announced, like a value no
#   column can keep (W-B62).
#
# The ceiling is frozen (``frozen_stored_ceiling``) where ``stored_date_bounds`` reads it: the name ``latest_range_end``
# imported into ``date_range_limits`` (that seam is RC-W01's, services range-ceiling). Frozen at ``XR65_CEILING``, a day
# of this unit's window and long past: a check reading tomorrow some other way lets the day after it through, and fails
# here. The prices go on this unit's own assets; the shape of a refusal is read on no database at all -- a refusal before
# any statement needs none (``_SessionSpy()``).
# ─────────────────────────────────────────────────────────────────────────────

XR65_FLOOR = date(1900, 1, 1)  # EARLIEST_RANGE_START: the contract's floor, written here and not read from the code
XR65_CEILING = BASE_DATE + timedelta(days=44)  # 1994-07-15: latest_range_end(), frozen
XR65_AFTER = XR65_CEILING + timedelta(days=1)  # the day after the ceiling
XR65_BEFORE = date(1899, 12, 31)  # the day before the floor
XR65_PROVIDER = "fake_provider_for_tests"
_XR65_BARRIER = "X-R65 capture barrier"


@pytest.fixture
def frozen_stored_ceiling(monkeypatch: pytest.MonkeyPatch) -> date:
    """``latest_range_end()`` answers ``XR65_CEILING`` where ``stored_date_bounds`` reads it: the name in
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
        pytest.param(XR65_BEFORE, id="1899-12-31-the-day-before-the-floor"),
        pytest.param(date(1, 1, 1), id="0001-01-01-SEC8-1b"),
        pytest.param(XR65_AFTER, id="the-day-after-the-ceiling"),
        pytest.param(date.max, id="9999-12-31"),
    ],
)
async def test_a_manual_price_outside_the_bounds_refuses_the_upsert_before_any_statement(clean_prices, frozen_stored_ceiling, day):
    """X-R65: one manual price outside [1900-01-01, the ceiling], between two valid ones, refuses the whole upsert.

    Before the fix: the upsert reads the asset and stores the three prices, ``day`` among them.
    Contract: ``DateOutOfRangeError`` with ``items`` ``[{"asset_id": the asset, "dates": [day]}]``, ``count`` 1,
    ``earliest`` 1900-01-01 and ``latest`` the ceiling; raised before the session is reached at all; the asset has no
    price, not even on the two valid days.
    """
    data = [FAUpsert(asset_id=clean_prices, prices=[_on(BASE_DATE, "10"), _on(day, "11"), _on(BASE_DATE + timedelta(days=1), "12")])]
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        spy = _SessionSpy(session)
        error = await _refused_out_of_range(spy, data)

    assert spy.used == [], f"the session was reached for {spy.used} before the refusal"
    assert (error.items, error.count) == ([{"asset_id": clean_prices, "dates": [day.isoformat()]}], 1)
    assert (error.earliest, error.latest) == (XR65_FLOOR, XR65_CEILING)
    assert await _stored_days(clean_prices) == []


@pytest.mark.asyncio
async def test_manual_prices_on_both_bounds_are_stored(clean_prices, frozen_stored_ceiling):
    """X-R65 guard, green before the fix and after: the bounds belong to the window.

    Contract: a manual price on 1900-01-01 and one on the ceiling itself are stored like any other.
    """
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        result = await AssetSourceManager.bulk_upsert_prices([FAUpsert(asset_id=clean_prices, prices=[_on(XR65_FLOOR, "10"), _on(XR65_CEILING, "11")])], session)

    row = next(entry for entry in result["results"] if entry["asset_id"] == clean_prices)
    assert row["count"] == 2, row
    assert await _stored_days(clean_prices) == [XR65_FLOOR, XR65_CEILING]


@pytest.mark.asyncio
async def test_an_offending_asset_refuses_the_clean_asset_before_it(clean_prices, xr65_second_asset, frozen_stored_ceiling):
    """X-R65: a clean asset first, then one with a price on 1899-12-31: neither is written.

    Before the fix: the upsert works asset by asset and commits as it goes: the first asset's two prices, then the
    second's two, 1899-12-31 among them.
    Contract: ``DateOutOfRangeError`` naming the second asset alone (``items`` ``[{"asset_id": second, "dates":
    ["1899-12-31"]}]``, ``count`` 1), the session never reached, and neither asset has a price.
    """
    data = [
        FAUpsert(asset_id=clean_prices, prices=[_on(BASE_DATE, "10"), _on(BASE_DATE + timedelta(days=1), "11")]),
        FAUpsert(asset_id=xr65_second_asset, prices=[_on(BASE_DATE + timedelta(days=2), "12"), _on(XR65_BEFORE, "13")]),
    ]
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        spy = _SessionSpy(session)
        error = await _refused_out_of_range(spy, data)

    assert spy.used == [], f"the session was reached for {spy.used} before the refusal"
    assert (error.items, error.count) == ([{"asset_id": xr65_second_asset, "dates": [XR65_BEFORE.isoformat()]}], 1)
    assert await _stored_days(clean_prices) == []
    assert await _stored_days(xr65_second_asset) == []


@pytest.mark.asyncio
async def test_the_refusal_names_each_assets_dates_in_input_order_ten_at_most(frozen_stored_ceiling):
    """X-R65: the numbers of a refusal, read on no database at all (the check comes before any statement).

    Three assets: the first with twelve days before the floor, newest first, a valid day among them; the second clean;
    the third with the day after the ceiling, a valid day and 1066-10-14. The asset ids name no row: the stand-in
    session answers none.
    Before the fix: each asset is read («Asset … not found»), nothing is refused.
    Contract: ``items`` the first and the third asset, in input order, each with its offending dates in input order (not
    sorted), the first one's ten at most; ``count`` 14, every offending date; the session never reached.
    """
    early = [XR65_BEFORE - timedelta(days=n) for n in range(12)]
    data = [
        FAUpsert(asset_id=9_001, prices=[_on(day, "10") for day in early[:6]] + [_on(BASE_DATE, "10")] + [_on(day, "10") for day in early[6:]]),
        FAUpsert(asset_id=9_002, prices=[_on(BASE_DATE, "10")]),
        FAUpsert(asset_id=9_003, prices=[_on(XR65_AFTER, "10"), _on(BASE_DATE, "10"), _on(date(1066, 10, 14), "10")]),
    ]
    spy = _SessionSpy()
    error = await _refused_out_of_range(spy, data)

    assert spy.used == [], f"the session was reached for {spy.used} before the refusal"
    assert error.items == [
        {"asset_id": 9_001, "dates": [day.isoformat() for day in early[:10]]},
        {"asset_id": 9_003, "dates": [XR65_AFTER.isoformat(), "1066-10-14"]},
    ]
    assert error.count == 14


@pytest.mark.asyncio
async def test_a_providers_prices_outside_the_bounds_are_dropped_named_and_logged(clean_prices, frozen_stored_ceiling):
    """X-R65: under a provider's key, the points outside [1900-01-01, the ceiling] are dropped and the others written.

    Four points: 1899-12-31, a valid day, the day after the ceiling, another valid day.
    Before the fix: the four are stored, the message is «Upserted 4 prices», nothing is logged.
    Contract: no exception; the two valid days alone are stored, under the provider's key; the asset's result counts 2
    and its message says «rejected 2 date(s)», naming both days; a warning (or worse) names the asset and both days. A
    barrier (an event sent through ``price_store``'s own logger inside the capture) proves the capture sees that logger:
    a missing warning is a warning not logged, never a blind capture.
    """
    inside = (BASE_DATE, BASE_DATE + timedelta(days=1))
    data = [FAUpsert(asset_id=clean_prices, prices=[_on(XR65_BEFORE, "9"), _on(inside[0], "10"), _on(XR65_AFTER, "11"), _on(inside[1], "12")])]
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
    assert "rejected 2 date(s)" in row["message"] and _names(row["message"], XR65_BEFORE, XR65_AFTER), row["message"]
    warnings = [event for event in events if event.get("log_level") in ("warning", "error", "critical") and event.get("event") != _XR65_BARRIER]
    assert [event for event in warnings if _names(event, clean_prices, XR65_BEFORE, XR65_AFTER)], f"no warning names the asset and both days: {warnings}"


@pytest.mark.asyncio
async def test_a_provider_refresh_never_stores_a_price_before_1900(assigned_asset, clean_prices, monkeypatch):
    """X-R65 through the refresh: the provider answers 1899-12-31 among its history; the refresh stores the others.

    The refresh hands the provider's points to ``bulk_upsert_prices`` under the provider's key (``refresh.py``), and a
    result message saying «rejected» becomes an error of the refresh. Only the floor is reached this way: the refresh
    itself drops a point after the range it asked for. The real ceiling, tomorrow: these days are long past.
    Before the fix: the three points are stored, 1899-12-31 among them, and the refresh reports no error.
    Contract: 1899-12-31 is not stored, the two other days are; an error of the refresh names 1899-12-31.
    """
    _patch_provider_with_events(monkeypatch, [_on(XR65_BEFORE, "9"), _on(BASE_DATE, "10"), _on(BASE_DATE + timedelta(days=1), "11")], [])

    result = await _refresh(assigned_asset)

    assert await _stored_days(assigned_asset) == [BASE_DATE, BASE_DATE + timedelta(days=1)], result
    assert [error for error in result.errors if XR65_BEFORE.isoformat() in error], result.errors


@pytest.mark.asyncio
async def test_a_provider_refresh_neither_counts_nor_announces_a_price_before_1900(assigned_asset, clean_prices, monkeypatch):
    """X-R65 through the refresh: a date the upsert drops for lying before 1900-01-01 is neither counted nor announced.

    The setup of the case above, with two rows stored first: day 0 at 10, and 1899-12-30 at 8, as a release before X-R65
    could leave it (written past the upsert, which now refuses it). The provider answers 1899-12-30 (9), 1899-12-31 (9.5),
    day 0 (20) and day 1 (21). The refresh counts its changes, and lists them in ``changed_points`` for the chart, before
    the upsert, which keeps day 0 and day 1 alone and leaves the legacy row as it was.
    Before the fix: the count is handed every point but the ones no column can keep (W-B62): 1899-12-31 counts as
    inserted and 1899-12-30 as updated, and both are announced: 2 inserted, 2 updated, 4 changed, four dates.
    Contract: like a value no column can keep (W-B62), a date the upsert drops for lying outside ``stored_date_bounds()``
    is neither counted nor announced: 1 inserted (day 1), 1 updated (day 0), 2 changed, ``changed_points`` day 0 and
    day 1 alone. ``points_fetched`` counts what the provider delivered, as for W-B62: not pinned here.
    """
    legacy, before, day0, day1 = XR65_BEFORE - timedelta(days=1), XR65_BEFORE, BASE_DATE, BASE_DATE + timedelta(days=1)
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        session.add_all([PriceHistory(asset_id=assigned_asset, date=day, close=Decimal(close), currency="USD", source_plugin_key=XR65_PROVIDER) for day, close in ((legacy, "8"), (day0, "10"))])
        await session.commit()
    assert await _stored_closes(assigned_asset) == {legacy: Decimal("8"), day0: Decimal("10")}, "barrier: the rows stored before the refresh are not the two written"
    _patch_provider_with_events(monkeypatch, [_on(legacy, "9"), _on(before, "9.5"), _on(day0, "20"), _on(day1, "21")], [])

    result = await _refresh(assigned_asset)

    stored = await _stored_closes(assigned_asset)
    assert stored == {legacy: Decimal("8"), day0: Decimal("20"), day1: Decimal("21")}, f"barrier: the upsert should store day 0 and day 1 alone and leave the legacy row as it was: {stored}; {result!r}"
    counted = (result.inserted_count, result.updated_count, result.points_changed, sorted(point.date for point in result.changed_points or []))
    assert counted == (1, 1, 2, [day0, day1]), f"(inserted, updated, changed, changed_points) = {counted}: the dates the upsert dropped, {legacy} and {before}, are counted or announced (points_fetched {result.points_fetched})"

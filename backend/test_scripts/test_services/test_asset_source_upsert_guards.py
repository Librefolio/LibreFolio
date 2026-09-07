"""Integrity guards and identifier filters of AssetSourceManager.

Isolation: WRITE_GLOBAL. ``Asset`` and ``PriceHistory`` carry no ``user_id``, so
the asset created here and the price rows written against it are visible to every
concurrently running test. The module fixture creates exactly one asset with a
unique display name and deletes it -- together with every price row it produced --
in teardown, so nothing survives the unit.

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

import backend.app.services.asset_source as module
from backend.app.db.models import Asset, AssetEvent, AssetEventType, AssetProviderAssignment, AssetType, PriceHistory
from backend.app.db.session import get_async_engine
from backend.app.schemas.assets import FAAinfoFiltersRequest
from backend.app.schemas.common import Currency, DateRangeModel
from backend.app.schemas.prices import FAHistoricalData, FAPricePoint, FAPriceQueryItem, FAUpsert
from backend.app.schemas.provider import ProviderInputType
from backend.app.schemas.refresh import FARefreshItem, SyncDateRangeModel, SyncStatus
from backend.app.services.asset_source import AssetCRUDService, AssetSourceManager
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

    monkeypatch.setattr(module, "convert_bulk", _fake_convert_bulk)
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

    monkeypatch.setattr(module, "convert_bulk", _fake_convert_bulk)
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

    monkeypatch.setattr(module, "convert_bulk", _fake_convert_bulk)
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

    monkeypatch.setattr(module, "convert_bulk", _explode)
    result = await _query(_events_request(asset_with_events, None))

    assert {ev.value.code for ev in result.events} == {"USD", "EUR"}
    assert all(ev.original_value is None for ev in result.events)


@pytest.mark.asyncio
async def test_conversion_pass_is_skipped_when_every_event_is_already_in_target(asset_with_events, monkeypatch):
    """Asking for USD on a USD/EUR mix still short-circuits when nothing needs FX."""

    async def _fake_convert_bulk(_session, conversions, raise_on_error=False):
        return [(Currency(amount=c[0].amount, code=c[1]), c[2], False) for c in conversions], []

    monkeypatch.setattr(module, "convert_bulk", _fake_convert_bulk)
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
    monkeypatch.setattr(module.AssetProviderRegistry, "get_provider_instance", staticmethod(lambda _code: _FakeProvider()))

    async def _fake_thread(_fn, timeout=None):
        return FAHistoricalData(prices=prices, source="fake_provider_for_tests")

    monkeypatch.setattr(module, "_run_provider_in_thread", _fake_thread)


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

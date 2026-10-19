from datetime import date, datetime, timedelta

import pytest

from backend.test_scripts.test_db_config import initialize_test_database, setup_test_database

setup_test_database()

import asyncio
import re
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from decimal import Decimal
from unittest.mock import patch

import pytest_asyncio
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from structlog.testing import capture_logs

from backend.app.db.models import Asset, AssetEvent, AssetEventType, AssetProviderAssignment, AssetType, Broker, PriceHistory, ProviderInputType, Transaction, TransactionType
from backend.app.db.session import get_async_engine, get_sync_engine
from backend.app.schemas.assets.events import FAAssetEventPoint
from backend.app.schemas.common import Currency, DateRangeModel
from backend.app.schemas.prices import FACurrentValue, FAHistoricalData, FAPricePoint
from backend.app.schemas.provider import FAProviderAssignmentItem
from backend.app.schemas.refresh import FARefreshItem, FARefreshResult, SyncDateRangeModel, SyncStatus
from backend.app.services.asset_source_providers.mockprov.plugin import MockProvider
from backend.app.services.assets import core, refresh
from backend.app.services.assets.base import AssetHistoryStartDate, AssetSourceError
from backend.app.services.assets.event_store import EventStoreOperations
from backend.app.services.assets.manager import AssetSourceManager
from backend.app.services.assets.price_store import PriceStoreOperations
from backend.app.services.assets.registry import AssetProviderRegistry
from backend.app.services.financial_math.splits import load_split_links
from backend.app.services.financial_math.yield_on_cost import _index_split_records


def _unique(prefix: str) -> str:
    return f"{prefix}_{int(time.time() * 1000)}"


async def _create_asset_with_provider(session: AsyncSession, name: str, provider_code: str = "mockprov", identifier: str = "MOCK") -> int:
    """Helper: create asset + assign provider, return asset_id."""
    asset = Asset(display_name=name, currency="USD", asset_type=AssetType.STOCK, active=True)
    session.add(asset)
    await session.commit()
    await session.refresh(asset)
    await AssetSourceManager.bulk_assign_providers(
        [
            FAProviderAssignmentItem(
                asset_id=asset.id,
                provider_code=provider_code,
                identifier=identifier,
                identifier_type=ProviderInputType.AUTO_GENERATED,
                provider_params={},
            )
        ],
        session,
    )
    return asset.id


@pytest.mark.asyncio
async def test_bulk_refresh_prices_orchestration():
    """Smoke test for bulk_refresh_prices orchestration using a mocked provider assignment."""
    assert initialize_test_database(), "Failed to initialize test database"
    AssetProviderRegistry.auto_discover()

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        asset_id = await _create_asset_with_provider(session, _unique("Refresh Test"))

        payload = [
            FARefreshItem(
                asset_id=asset_id,
                date_range=DateRangeModel(start=date(2025, 1, 1), end=date(2025, 1, 3)),
            )
        ]
        results = await AssetSourceManager.bulk_refresh_prices(payload, session)

        assert results is not None
        assert len(results.results) > 0


@pytest.mark.asyncio
async def test_refresh_single_asset_status_and_points():
    """Verify single-asset refresh returns OK status with correct point counts."""
    assert initialize_test_database(), "Failed to initialize test database"
    AssetProviderRegistry.auto_discover()

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        asset_id = await _create_asset_with_provider(session, _unique("Single Status"))

        payload = [
            FARefreshItem(
                asset_id=asset_id,
                date_range=DateRangeModel(start=date(2025, 1, 1), end=date(2025, 1, 3)),
            )
        ]
        response = await AssetSourceManager.bulk_refresh_prices(payload, session)

        assert len(response.results) == 1
        r = response.results[0]
        assert r.asset_id == asset_id
        assert r.status in (SyncStatus.OK, SyncStatus.PARTIAL), f"Expected OK/PARTIAL, got {r.status}"
        assert r.provider_used == "mockprov"
        assert r.points_fetched >= 3, f"Expected >=3 prices (Jan 1-3), got {r.points_fetched}"
        assert r.elapsed_ms is not None and r.elapsed_ms >= 0
        assert r.errors == []
        assert response.success_count == 1


@pytest.mark.asyncio
async def test_refresh_multi_asset_concurrent():
    """
    Verify that refreshing multiple assets concurrently works correctly.
    This is the critical test for the 3-phase pipeline: each asset gets
    its own persist session, so concurrent commits don't interfere.
    """
    assert initialize_test_database(), "Failed to initialize test database"
    AssetProviderRegistry.auto_discover()

    N_ASSETS = 5

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        asset_ids = []
        for i in range(N_ASSETS):
            aid = await _create_asset_with_provider(session, _unique(f"Concurrent_{i}"), identifier=f"CONC_{i}")
            asset_ids.append(aid)

        payload = [
            FARefreshItem(
                asset_id=aid,
                date_range=DateRangeModel(start=date(2025, 2, 1), end=date(2025, 2, 5)),
            )
            for aid in asset_ids
        ]
        response = await AssetSourceManager.bulk_refresh_prices(payload, session)

        assert len(response.results) == N_ASSETS
        assert response.success_count == N_ASSETS, f"Expected all {N_ASSETS} to succeed, got {response.success_count}. " f"Statuses: {[(r.asset_id, r.status, r.errors) for r in response.results]}"

        for r in response.results:
            assert r.status in (SyncStatus.OK, SyncStatus.PARTIAL), f"Asset {r.asset_id}: expected OK/PARTIAL, got {r.status} — errors: {r.errors}"
            assert r.points_fetched >= 5, f"Asset {r.asset_id}: expected >=5 prices, got {r.points_fetched}"

        assert response.total_points_changed >= N_ASSETS * 5

    # Verify prices are actually in the database (using a fresh session)
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as verify_session:
        for aid in asset_ids:
            stmt = select(PriceHistory).where(PriceHistory.asset_id == aid)
            result = await verify_session.execute(stmt)
            prices = result.scalars().all()
            assert len(prices) >= 5, f"Asset {aid}: expected >=5 prices in DB, got {len(prices)}"


@pytest.mark.asyncio
async def test_refresh_skipped_no_provider():
    """Verify assets without a provider are SKIPPED."""
    assert initialize_test_database(), "Failed to initialize test database"
    AssetProviderRegistry.auto_discover()

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        # Create asset WITHOUT provider assignment
        asset = Asset(
            display_name=_unique("No Provider"),
            currency="EUR",
            asset_type=AssetType.BOND,
            active=True,
        )
        session.add(asset)
        await session.commit()
        await session.refresh(asset)

        payload = [
            FARefreshItem(
                asset_id=asset.id,
                date_range=DateRangeModel(start=date(2025, 1, 1), end=date(2025, 1, 3)),
            )
        ]
        response = await AssetSourceManager.bulk_refresh_prices(payload, session)

        assert len(response.results) == 1
        r = response.results[0]
        assert r.status == SyncStatus.SKIPPED
        assert r.points_fetched == 0
        assert r.provider_used is None
        assert response.success_count == 0


@pytest.mark.asyncio
async def test_refresh_failed_nonexistent_asset():
    """Verify refresh of a non-existent asset_id returns FAILED."""
    assert initialize_test_database(), "Failed to initialize test database"
    AssetProviderRegistry.auto_discover()

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        payload = [
            FARefreshItem(
                asset_id=999999,
                date_range=DateRangeModel(start=date(2025, 1, 1), end=date(2025, 1, 3)),
            )
        ]
        response = await AssetSourceManager.bulk_refresh_prices(payload, session)

        assert len(response.results) == 1
        r = response.results[0]
        assert r.status == SyncStatus.FAILED
        assert r.points_fetched == 0
        assert len(r.errors) > 0
        assert response.success_count == 0


@pytest.mark.asyncio
async def test_refresh_mixed_results():
    """Verify mixed batch: asset with provider (OK) + asset without (SKIPPED) + nonexistent (FAILED)."""
    assert initialize_test_database(), "Failed to initialize test database"
    AssetProviderRegistry.auto_discover()

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        # 1. Asset with provider → should succeed
        good_id = await _create_asset_with_provider(session, _unique("Good Asset"))

        # 2. Asset without provider → SKIPPED
        no_prov = Asset(
            display_name=_unique("No Prov"),
            currency="EUR",
            asset_type=AssetType.ETF,
            active=True,
        )
        session.add(no_prov)
        await session.commit()
        await session.refresh(no_prov)

        # 3. Non-existent asset → FAILED
        fake_id = 888888

        payload = [
            FARefreshItem(asset_id=good_id, date_range=DateRangeModel(start=date(2025, 3, 1), end=date(2025, 3, 3))),
            FARefreshItem(asset_id=no_prov.id, date_range=DateRangeModel(start=date(2025, 3, 1), end=date(2025, 3, 3))),
            FARefreshItem(asset_id=fake_id, date_range=DateRangeModel(start=date(2025, 3, 1), end=date(2025, 3, 3))),
        ]
        response = await AssetSourceManager.bulk_refresh_prices(payload, session)

        assert len(response.results) == 3

        statuses = {r.asset_id: r.status for r in response.results}
        assert statuses[good_id] in (SyncStatus.OK, SyncStatus.PARTIAL)
        assert statuses[no_prov.id] == SyncStatus.SKIPPED
        assert statuses[fake_id] == SyncStatus.FAILED
        assert response.success_count == 1


@pytest.mark.asyncio
async def test_refresh_pipeline_smoke_with_matching_currency():
    """Smoke test: refresh pipeline completes successfully when asset and provider currencies align.

    Note: Post Phase-7 I.2 (currency-coherence hard-reject), provider points whose currency
    differs from the asset's currency are discarded. Mismatch rejection is covered by the
    dedicated G.5 suite (`test_prices_currency_coherence.py`). Here we simply assert the
    happy pipeline with matching currencies (USD/USD).
    """
    assert initialize_test_database(), "Failed to initialize test database"
    AssetProviderRegistry.auto_discover()

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        # mockprov returns "USD" currency; align asset currency to USD for happy-path smoke.
        asset = Asset(
            display_name=_unique("USD Asset"),
            currency="USD",
            asset_type=AssetType.STOCK,
            active=True,
        )
        session.add(asset)
        await session.commit()
        await session.refresh(asset)

        await AssetSourceManager.bulk_assign_providers(
            [
                FAProviderAssignmentItem(
                    asset_id=asset.id,
                    provider_code="mockprov",
                    identifier="EUR_TEST",
                    identifier_type=ProviderInputType.AUTO_GENERATED,
                    provider_params={},
                )
            ],
            session,
        )

        payload = [
            FARefreshItem(
                asset_id=asset.id,
                date_range=DateRangeModel(start=date(2025, 4, 1), end=date(2025, 4, 2)),
            )
        ]
        response = await AssetSourceManager.bulk_refresh_prices(payload, session)

        assert len(response.results) == 1
        r = response.results[0]
        assert r.status in (SyncStatus.OK, SyncStatus.PARTIAL)
        assert r.errors == []


# ============================================================================
# "resume" sentinel — start from the day after the last stored price
# ============================================================================


async def _seed_prices(session: AsyncSession, asset_id: int, days: list[date]) -> None:
    """Insert one price row per given day so 'resume' has something to resume from."""
    for d in days:
        session.add(PriceHistory(asset_id=asset_id, date=d, close=Decimal("100.00"), currency="USD", source_plugin_key="mockprov"))
    await session.commit()


class _StartRecorder:
    """Stand-in for the provider history call that records the start it was handed.

    The resolved start is not visible in the response, so the only honest way to
    assert on it is to look at what actually reached the provider.
    """

    def __init__(self):
        self.calls: dict[str, AssetHistoryStartDate] = {}

    async def __call__(self, identifier, identifier_type, provider_params, start_date, end_date):
        self.calls[identifier] = start_date
        return FAHistoricalData(prices=[], events=[], currency="USD", source="mockprov")


@pytest.mark.asyncio
async def test_resume_starts_day_after_last_stored_price():
    """With prices on file, 'resume' asks the provider only for the gap."""
    assert initialize_test_database(), "Failed to initialize test database"
    AssetProviderRegistry.auto_discover()

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        identifier = _unique("RESUME")
        asset_id = await _create_asset_with_provider(session, _unique("Resume Gap"), identifier=identifier)
        await _seed_prices(session, asset_id, [date(2025, 1, 10), date(2025, 1, 12)])

        recorder = _StartRecorder()
        with patch.object(MockProvider, "get_history_value", recorder):
            await AssetSourceManager.bulk_refresh_prices(
                [FARefreshItem(asset_id=asset_id, date_range=SyncDateRangeModel(start="resume", end=date(2025, 2, 1)))],
                session,
            )

        assert recorder.calls[identifier] == date(2025, 1, 13), "resume must start the day AFTER the newest stored price"


@pytest.mark.asyncio
async def test_resume_falls_back_to_min_without_stored_prices():
    """No prices on file means nothing to resume from, so ask for the full history.

    This is what makes one rule enough for every case: a brand-new asset and an
    asset whose series was just wiped by a parametric param change both land here.
    """
    assert initialize_test_database(), "Failed to initialize test database"
    AssetProviderRegistry.auto_discover()

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        identifier = _unique("RESUMEMIN")
        asset_id = await _create_asset_with_provider(session, _unique("Resume Empty"), identifier=identifier)

        recorder = _StartRecorder()
        with patch.object(MockProvider, "get_history_value", recorder):
            await AssetSourceManager.bulk_refresh_prices(
                [FARefreshItem(asset_id=asset_id, date_range=SyncDateRangeModel(start="resume", end=date(2025, 2, 1)))],
                session,
            )

        assert recorder.calls[identifier] == "min"


@pytest.mark.asyncio
async def test_resume_skips_when_series_already_covers_the_end():
    """Resuming past the requested end is 'nothing to do', not an inverted range.

    Without this guard the resolved start would exceed the end and trip
    SyncDateRangeModel's own validator, turning a no-op into an error.
    """
    assert initialize_test_database(), "Failed to initialize test database"
    AssetProviderRegistry.auto_discover()

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        identifier = _unique("RESUMEUP")
        asset_id = await _create_asset_with_provider(session, _unique("Resume UpToDate"), identifier=identifier)
        await _seed_prices(session, asset_id, [date(2025, 2, 1)])

        recorder = _StartRecorder()
        with patch.object(MockProvider, "get_history_value", recorder):
            response = await AssetSourceManager.bulk_refresh_prices(
                [FARefreshItem(asset_id=asset_id, date_range=SyncDateRangeModel(start="resume", end=date(2025, 2, 1)))],
                session,
            )

        assert len(response.results) == 1
        assert response.results[0].status == SyncStatus.SKIPPED
        assert recorder.calls == {}, "the provider must not be called when there is nothing to fetch"


@pytest.mark.asyncio
async def test_resume_resolves_per_asset_in_one_bulk_call():
    """The batch lookup must map each asset to its own last price, not share one."""
    assert initialize_test_database(), "Failed to initialize test database"
    AssetProviderRegistry.auto_discover()

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        id_seeded = _unique("RESUMEA")
        id_empty = _unique("RESUMEB")
        asset_seeded = await _create_asset_with_provider(session, _unique("Resume Mixed A"), identifier=id_seeded)
        asset_empty = await _create_asset_with_provider(session, _unique("Resume Mixed B"), identifier=id_empty)
        await _seed_prices(session, asset_seeded, [date(2025, 1, 20)])

        recorder = _StartRecorder()
        with patch.object(MockProvider, "get_history_value", recorder):
            await AssetSourceManager.bulk_refresh_prices(
                [
                    FARefreshItem(asset_id=asset_seeded, date_range=SyncDateRangeModel(start="resume", end=date(2025, 2, 1))),
                    FARefreshItem(asset_id=asset_empty, date_range=SyncDateRangeModel(start="resume", end=date(2025, 2, 1))),
                ],
                session,
            )

        assert recorder.calls[id_seeded] == date(2025, 1, 21)
        assert recorder.calls[id_empty] == "min"


@pytest.mark.asyncio
async def test_concrete_start_is_untouched_by_the_resume_lookup():
    """A caller that names a date still gets that date, prices on file or not."""
    assert initialize_test_database(), "Failed to initialize test database"
    AssetProviderRegistry.auto_discover()

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        identifier = _unique("RESUMEFIX")
        asset_id = await _create_asset_with_provider(session, _unique("Resume Explicit"), identifier=identifier)
        await _seed_prices(session, asset_id, [date(2025, 1, 20)])

        recorder = _StartRecorder()
        with patch.object(MockProvider, "get_history_value", recorder):
            await AssetSourceManager.bulk_refresh_prices(
                [FARefreshItem(asset_id=asset_id, date_range=SyncDateRangeModel(start=date(2025, 1, 1), end=date(2025, 2, 1)))],
                session,
            )

        assert recorder.calls[identifier] == date(2025, 1, 1)


# ============================================================================
# X-R12 — the history call reaches today, for today's events; prices stop at yesterday
# ============================================================================
#
# The fetch step (``refresh._fetch_refresh_item``) called directly with a prepared item and an in-process provider
# double: no database, no network. What reached the provider is read from the double's own record of its calls.

_XR12_TODAY = date(2026, 3, 18)  # any day: the fetch step reads no other clock
_XR12_HISTORY_CLOSE = Decimal("10")
_XR12_CACHED_CLOSE = Decimal("7")
_XR12_CURRENT_VALUE = Decimal("11")


class _XR12FrozenDate(date):
    """``refresh.date_type`` during these tests: ``today()`` is ``_XR12_TODAY``, the rest is a plain ``date``."""

    @classmethod
    def today(cls) -> date:
        return _XR12_TODAY


@pytest.fixture
def xr12_today():
    """Today for the fetch step, frozen, with the two core caches it reads emptied before and after.

    ``_fetch_refresh_item`` reads the day once, through ``refresh.date_type.today()``: frozen there, these tests hold no
    clock, and a run across midnight cannot compare two different days. Not autouse: ``_prepare_refresh_items`` also
    uses ``date_type``, in an ``isinstance`` check the tests above go through.
    The caches are keyed by provider and identifier, not by dates: an entry left by another test would be merged into
    the refresh under test, and an entry left by these tests would be served to the next one.
    """
    core._asset_history_cache.clear()
    core._asset_current_cache.clear()
    with patch.object(refresh, "date_type", _XR12FrozenDate):
        yield _XR12_TODAY
    core._asset_history_cache.clear()
    core._asset_current_cache.clear()


def _xr12_days(first: date, last: date) -> list[date]:
    """Every day from ``first`` to ``last``, both included."""
    return [first + timedelta(days=offset) for offset in range((last - first).days + 1)]


class _XR12Provider:
    """In-process provider double: a close for each day asked, today's dividend when asked, a current value dated today.

    Not a plugin (no ``PluginSettingsMixin``): ``core.call_provider`` calls it as it is, without settings, pause or
    network. Every call is recorded, so a test asserts on what reached the provider instead of inferring it from the
    result. ``after_today`` adds history points dated after today whatever the range, as a synthetic series could.
    """

    provider_code = "xr12fake"
    supports_history = True

    def __init__(self, today: date, *, after_today: tuple[date, ...] = ()):
        self.today = today
        self.after_today = after_today
        self.history_calls: list[tuple[AssetHistoryStartDate, date]] = []
        self.current_calls = 0

    def dividend_today(self) -> FAAssetEventPoint:
        return FAAssetEventPoint(date=self.today, type="DIVIDEND", value=Currency(code="EUR", amount=Decimal("0.50")))

    async def get_history_value(self, identifier, identifier_type, provider_params, start_date, end_date) -> FAHistoricalData:
        self.history_calls.append((start_date, end_date))
        dividend = self.dividend_today()
        return FAHistoricalData(
            prices=[FAPricePoint(date=d, close=_XR12_HISTORY_CLOSE, currency="EUR") for d in (*_xr12_days(start_date, end_date), *self.after_today)],
            events=[dividend] if start_date <= dividend.date <= end_date else [],
            currency="EUR",
            source=self.provider_code,
        )

    async def get_current_value(self, identifier, identifier_type, provider_params) -> FACurrentValue:
        self.current_calls += 1
        return FACurrentValue(value=_XR12_CURRENT_VALUE, currency="EUR", as_of_date=self.today, source=self.provider_code)


def _xr12_prep(provider: _XR12Provider, start: date, end: date) -> refresh._PreparedRefreshItem:
    """What ``_prepare_refresh_items`` hands the fetch step, for the double and an identifier of this test alone."""
    return refresh._PreparedRefreshItem(
        assignment_id=None,
        asset_currency="EUR",
        provider=provider,
        provider_code=provider.provider_code,
        provider_params=None,
        identifier=f"XR12-{uuid.uuid4().hex}",
        identifier_type=ProviderInputType.TICKER,
        start=start,
        end=end,
    )


def _xr12_cache_key(prep: refresh._PreparedRefreshItem) -> tuple:
    """The key the fetch step files the history under (``cache_key`` in ``_fetch_refresh_item``), from the same parts."""
    return (prep.provider_code, prep.identifier, str(prep.identifier_type), core._provider_params_hash(prep.provider_params), core.settings_cache_part(prep.provider))


def _xr12_seed_history(prep: refresh._PreparedRefreshItem, days: list[date], *, events: tuple[FAAssetEventPoint, ...] = ()) -> None:
    """A history cache entry as an earlier refresh leaves it: one close per day (``_XR12_CACHED_CLOSE``), and events."""
    dates = {d.isoformat(): FAPricePoint(date=d, close=_XR12_CACHED_CLOSE, currency="EUR").model_dump() for d in days}
    core._asset_history_cache.set(_xr12_cache_key(prep), {"dates": dates, "events": [event.model_dump() for event in events]})


def _xr12_history_entry(prep: refresh._PreparedRefreshItem) -> dict:
    entry, found = core._asset_history_cache.get(_xr12_cache_key(prep))
    assert found and entry, "no history cache entry under the key the fetch step files it under"
    return entry


async def _xr12_fetch(prep: refresh._PreparedRefreshItem) -> refresh._FetchedRefreshData:
    """The fetch step for one item, as ``_fetch_refresh_items`` runs it; a failed fetch fails the test here."""
    data, error, refusal = await refresh._fetch_refresh_item(1, prep, asyncio.Semaphore(1), 60)
    assert error is None and refusal is None, f"the fetch step failed: {error!r}"
    assert data is not None
    return data


def _xr12_closes(prices: list[dict]) -> dict[date, Decimal]:
    """The fetched closes by day; a day priced twice fails here."""
    days = sorted(p["date"] for p in prices)
    assert len(days) == len(set(days)), f"a day priced twice: {days}"
    return {p["date"]: p["close"] for p in prices}


def _xr12_events(events: list[dict]) -> list[tuple[date, str]]:
    return [(e["date"], e["type"]) for e in events]


@pytest.mark.asyncio
async def test_fetch_range_to_today_calls_history_up_to_today(xr12_today):
    """X-R12: a range reaching today asks the history up to today; today's event comes in, today's price stays current.

    Before: the call ended yesterday, so an event the provider dates today (a dividend, a split) arrived with the first
    refresh of a later day.
    Contract: one history call ending today; one price per day, today's being the current value, not the history's;
    today's event in the fetched data and in the history cache entry, which holds no price for today.
    """
    today = xr12_today
    start, yesterday = today - timedelta(days=5), today - timedelta(days=1)
    provider = _XR12Provider(today)
    prep = _xr12_prep(provider, start, today)

    data = await _xr12_fetch(prep)

    assert provider.history_calls == [(start, today)]
    closes = _xr12_closes(data.prices)
    assert sorted(closes) == _xr12_days(start, today)
    assert [p["close"] for p in data.prices if p["date"] == today] == [_XR12_CURRENT_VALUE]
    assert {closes[d] for d in _xr12_days(start, yesterday)} == {_XR12_HISTORY_CLOSE}
    assert _xr12_events(data.events) == [(today, "DIVIDEND")]
    entry = _xr12_history_entry(prep)
    assert today.isoformat() not in entry["dates"]
    assert sorted(entry["dates"]) == [d.isoformat() for d in _xr12_days(start, yesterday)]
    assert _xr12_events(entry["events"]) == [(today, "DIVIDEND")]


@pytest.mark.asyncio
async def test_fetch_cache_up_to_yesterday_is_a_full_hit(xr12_today):
    """X-R12: a cache holding every day from the start to yesterday makes no history call, though a call would end today.

    Today has no history price to cache, so the coverage check still stops at yesterday: one reaching today would never
    be met, and every refresh would call the provider again.
    Contract: no history call; the cached closes plus the current value for today; the cached events served.
    """
    today = xr12_today
    start, yesterday = today - timedelta(days=5), today - timedelta(days=1)
    provider = _XR12Provider(today)
    prep = _xr12_prep(provider, start, today)
    _xr12_seed_history(prep, _xr12_days(start, yesterday), events=(provider.dividend_today(),))

    data = await _xr12_fetch(prep)

    assert provider.history_calls == []
    assert provider.current_calls == 1
    assert _xr12_closes(data.prices) == dict.fromkeys(_xr12_days(start, yesterday), _XR12_CACHED_CLOSE) | {today: _XR12_CURRENT_VALUE}
    assert _xr12_events(data.events) == [(today, "DIVIDEND")]


@pytest.mark.asyncio
async def test_fetch_cache_gap_calls_from_missing_day_up_to_today(xr12_today):
    """X-R12: a cache missing one past day calls from that day up to today, for today's events.

    Before: the call ended on the last missing day (``max(needed_dates)``), short of today.
    Contract: one call from the missing day to today; the gap filled from the history, the days before it still from
    the cache; today's price the current value; today's event fetched and cached, and no cached price for today.
    """
    today = xr12_today
    start, missing, yesterday = today - timedelta(days=5), today - timedelta(days=3), today - timedelta(days=1)
    provider = _XR12Provider(today)
    prep = _xr12_prep(provider, start, today)
    _xr12_seed_history(prep, [d for d in _xr12_days(start, yesterday) if d != missing])

    data = await _xr12_fetch(prep)

    assert provider.history_calls == [(missing, today)]
    closes = _xr12_closes(data.prices)
    assert sorted(closes) == _xr12_days(start, today)
    assert closes[missing] == _XR12_HISTORY_CLOSE
    assert {closes[d] for d in _xr12_days(start, missing - timedelta(days=1))} == {_XR12_CACHED_CLOSE}
    assert closes[today] == _XR12_CURRENT_VALUE
    assert _xr12_events(data.events) == [(today, "DIVIDEND")]
    entry = _xr12_history_entry(prep)
    assert today.isoformat() not in entry["dates"]
    assert _xr12_events(entry["events"]) == [(today, "DIVIDEND")]


@pytest.mark.asyncio
async def test_fetch_past_range_call_still_ends_at_end(xr12_today):
    """X-R12 leaves a range ending before today alone: the call ends at ``end``, whose history close is kept.

    Contract: one call from ``start`` to ``end``; a history close for every day, ``end`` included; no current value
    asked, the range not reaching today.
    """
    today = xr12_today
    start, end = today - timedelta(days=8), today - timedelta(days=3)
    provider = _XR12Provider(today)
    prep = _xr12_prep(provider, start, end)

    data = await _xr12_fetch(prep)

    assert provider.history_calls == [(start, end)]
    assert provider.current_calls == 0
    closes = _xr12_closes(data.prices)
    assert closes[end] == _XR12_HISTORY_CLOSE
    assert closes == dict.fromkeys(_xr12_days(start, end), _XR12_HISTORY_CLOSE)


@pytest.mark.asyncio
async def test_fetch_start_today_makes_no_history_call(xr12_today):
    """X-R12 leaves a range starting today alone: no history call, today's price from the current value only.

    Contract: no history call; one price, today's current value.
    """
    today = xr12_today
    provider = _XR12Provider(today)
    prep = _xr12_prep(provider, today, today)

    data = await _xr12_fetch(prep)

    assert provider.history_calls == []
    assert provider.current_calls == 1
    assert _xr12_closes(data.prices) == {today: _XR12_CURRENT_VALUE}


@pytest.mark.asyncio
async def test_fetch_history_point_after_today_is_dropped(xr12_today):
    """X-R12: a history point dated after today (a synthetic series, as scheduled_investment could) is not a price.

    Before: nothing filtered the history by date, so such a point was cached and returned as a price.
    Contract: no price and no cached date after today; one price per day up to today, today's the current value.
    """
    today = xr12_today
    start, yesterday = today - timedelta(days=5), today - timedelta(days=1)
    after_today = (today + timedelta(days=1), today + timedelta(days=30))
    provider = _XR12Provider(today, after_today=after_today)
    prep = _xr12_prep(provider, start, today)

    data = await _xr12_fetch(prep)

    assert provider.history_calls == [(start, today)]
    closes = _xr12_closes(data.prices)
    assert set(after_today).isdisjoint(closes), sorted(closes)
    assert sorted(closes) == _xr12_days(start, today)
    assert closes[today] == _XR12_CURRENT_VALUE
    entry = _xr12_history_entry(prep)
    assert {d.isoformat() for d in after_today}.isdisjoint(entry["dates"]), sorted(entry["dates"])
    assert sorted(entry["dates"]) == [d.isoformat() for d in _xr12_days(start, yesterday)]


# ============================================================================
# Z-32 (c) — the quote currency the provider reported, kept on the assignment
# ============================================================================
#
# Z-32 (c) §4: after a history fetch whose ``FAHistoricalData.currency`` is set, the asset's assignment holds that code in
# ``reported_currency`` — as reported (``GBp``, not the ``GBP`` its points carry), stripped; a code longer than the
# column's 8 characters is not stored. A fetch that reports no code leaves the column as it was. A history served whole
# from the core history cache carries the code it was fetched with (the cache entry keeps it): a cache hit neither
# erases the code nor misses it.
#
# Lane-database tests, as the refresh tests above: a past range, so no current value is asked; the provider's history a
# double patched on MockProvider, as the resume tests do — no network, every call recorded. Each test writes its own GBP
# assets, assigned to mockprov under identifiers of its own (no history cache entry is shared with another test); the
# ``z32_assets`` fixture deletes them with their prices and assignments, and drops the cache entries of those identifiers.
# A column left as it was is read beside ``last_fetch_at``: set, it proves the refresh reached the assignment.
#
# Red on HEAD 80cef0e43: AssetProviderAssignment has no ``reported_currency`` (§2); each test fails on that first.

_Z32_START, _Z32_END = date(2024, 2, 5), date(2024, 2, 7)  # a past range: the history alone, no current value
_Z32_DAYS = 3
_Z32_CLOSE = Decimal("7250")  # pence, as Yahoo quotes a London line; the points carry GBP


def _z32_column():
    """``AssetProviderAssignment.reported_currency``, the column §2 adds; until it exists the test fails here."""
    column = getattr(AssetProviderAssignment, "reported_currency", None)
    if column is None:
        pytest.fail("red until Z-32 (c): AssetProviderAssignment has no reported_currency (§2): nothing keeps the code the provider reported", pytrace=False)
    return column


class _Z32History:
    """Stand-in for ``MockProvider.get_history_value``: a GBP close for each day asked, and ``reported`` as the history's
    ``currency`` — the code as the provider reported it. Every call is recorded: (identifier, start, end)."""

    def __init__(self, reported: str | None):
        self.reported = reported
        self.calls: list[tuple[str, AssetHistoryStartDate, date]] = []

    async def __call__(self, identifier, identifier_type, provider_params, start_date, end_date) -> FAHistoricalData:
        self.calls.append((identifier, start_date, end_date))
        days = [start_date + timedelta(days=offset) for offset in range((end_date - start_date).days + 1)]
        return FAHistoricalData(prices=[FAPricePoint(date=day, close=_Z32_CLOSE, currency="GBP") for day in days], events=[], currency=self.reported, source="mockprov")


@dataclass
class _Z32Assets:
    """The assets one test writes, for ``z32_assets`` to delete."""

    asset_ids: list[int] = field(default_factory=list)
    identifiers: set[str] = field(default_factory=set)

    async def new(self, *, identifier: str | None = None, reported_currency: str | None = None) -> tuple[int, str]:
        """A GBP asset assigned to mockprov under ``identifier`` (one of its own when None), TICKER, no params, as the
        asset form saves it; ``reported_currency`` then set to the value given (none: NULL, as a new assignment has it)."""
        identifier = identifier or f"Z32-{uuid.uuid4().hex[:12]}.L"
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            asset = Asset(display_name=f"Z-32 London line {uuid.uuid4().hex[:12]}", currency="GBP", asset_type=AssetType.STOCK, active=True)
            session.add(asset)
            await session.commit()
            await session.refresh(asset)
            self.asset_ids.append(asset.id)
            self.identifiers.add(identifier)
            item = FAProviderAssignmentItem(asset_id=asset.id, provider_code="mockprov", identifier=identifier, identifier_type=ProviderInputType.TICKER, provider_params=None)
            results = await AssetSourceManager.bulk_assign_providers([item], session)
            assert [result.success for result in results] == [True], f"setup: the assignment of asset {asset.id}: {results}"
            if reported_currency is not None:
                await session.execute(update(AssetProviderAssignment).where(AssetProviderAssignment.asset_id == asset.id).values({_z32_column(): reported_currency}))
                await session.commit()
        return asset.id, identifier


@pytest_asyncio.fixture
async def z32_assets():
    """The assets of one test; at teardown they go, with their prices, events and assignments, and the history cache
    entries of their identifiers."""
    assert initialize_test_database(), "Failed to initialize test database"
    AssetProviderRegistry.auto_discover()
    assets = _Z32Assets()
    yield assets
    if assets.asset_ids:
        async with AsyncSession(get_async_engine()) as session:
            await session.execute(delete(PriceHistory).where(PriceHistory.asset_id.in_(assets.asset_ids)))
            await session.execute(delete(AssetEvent).where(AssetEvent.asset_id.in_(assets.asset_ids)))
            await session.execute(delete(AssetProviderAssignment).where(AssetProviderAssignment.asset_id.in_(assets.asset_ids)))
            deleted = await session.execute(delete(Asset).where(Asset.id.in_(assets.asset_ids)))
            await session.commit()
        assert deleted.rowcount == len(assets.asset_ids), f"cleanup: {deleted.rowcount} of the assets {assets.asset_ids} deleted"
    for identifier in assets.identifiers:
        await core.drop_asset_cache_entries("mockprov", identifier, ProviderInputType.TICKER, None)


async def _z32_refresh(asset_id: int, history: _Z32History) -> FARefreshResult:
    """The refresh of one asset over the past range, ``history`` answering for the provider: its result."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        with patch.object(MockProvider, "get_history_value", history):
            response = await AssetSourceManager.bulk_refresh_prices([FARefreshItem(asset_id=asset_id, date_range=SyncDateRangeModel(start=_Z32_START, end=_Z32_END))], session)
    (result,) = response.results
    return result


async def _z32_assignment(asset_id: int) -> tuple[str | None, object]:
    """``(reported_currency, last_fetch_at)`` of the asset's assignment, read in a new session."""
    column = _z32_column()
    async with AsyncSession(get_async_engine()) as session:
        code, fetched_at = (await session.execute(select(column, AssetProviderAssignment.last_fetch_at).where(AssetProviderAssignment.asset_id == asset_id))).one()
    return code, fetched_at


def _z32_refreshed(result: FARefreshResult, history: _Z32History, calls: int) -> None:
    """Barrier: the refresh went through — OK, the three days fetched, no error — with ``calls`` history call(s) in all."""
    observed = (result.status, result.points_fetched, result.errors, len(history.calls))
    assert observed == (SyncStatus.OK, _Z32_DAYS, [], calls), f"barrier: the refresh did not go as set up (status, points, errors, history calls): {observed}"


@pytest.mark.parametrize(
    ("reported", "stored"),
    [
        pytest.param("GBp", "GBp", id="pence-as-reported"),
        pytest.param("USD", "USD", id="dollars"),
        pytest.param("  GBp\n", "GBp", id="stripped"),
        pytest.param("GBPPENCE", "GBPPENCE", id="eight-characters"),
    ],
)
@pytest.mark.asyncio
async def test_z32_a_history_fetch_keeps_the_code_the_provider_reported(z32_assets, reported, stored):
    """Z-32 (c) §4: a fetched history whose ``currency`` is set leaves it on the assignment, as reported — ``GBp`` is not
    folded to the ``GBP`` its points carry —, stripped, eight characters kept whole.

    Red on HEAD: AssetProviderAssignment has no ``reported_currency``.
    """
    _z32_column()
    asset_id, _ = await z32_assets.new()
    history = _Z32History(reported)

    result = await _z32_refresh(asset_id, history)

    _z32_refreshed(result, history, 1)
    code, _fetched_at = await _z32_assignment(asset_id)
    assert code == stored, f"the history reported {reported!r}: the assignment must hold {stored!r}, holds {code!r}"


@pytest.mark.parametrize("before", [pytest.param("GBp", id="pence-kept"), pytest.param(None, id="null-kept")])
@pytest.mark.asyncio
async def test_z32_a_history_without_a_code_leaves_the_column_as_it_was(z32_assets, before):
    """Z-32 (c) §4: a fetched history whose ``currency`` is None leaves the assignment's code as it was — ``GBp``
    learned before stays, NULL stays NULL —, once the refresh has reached the assignment (``last_fetch_at`` set).

    Red on HEAD: AssetProviderAssignment has no ``reported_currency``.
    """
    _z32_column()
    asset_id, _ = await z32_assets.new(reported_currency=before)
    history = _Z32History(None)

    result = await _z32_refresh(asset_id, history)

    _z32_refreshed(result, history, 1)
    code, fetched_at = await _z32_assignment(asset_id)
    assert fetched_at is not None, "barrier: the refresh never reached the assignment (last_fetch_at unset), so «left as it was» would prove nothing"
    assert code == before, f"a history without a code must leave {before!r}, left {code!r}"


@pytest.mark.asyncio
async def test_z32_a_code_longer_than_the_column_is_not_stored(z32_assets):
    """Z-32 (c) §4: a code of nine characters (``GBP.PENCE``) is not stored, whole or cut to the column's eight: the
    assignment, NULL before, is NULL after a refresh that otherwise went through and reached it.

    From NULL on purpose: whether a code stored before stays or goes when a longer one comes is not decided (§4 says
    «not stored»), and this test pins neither.

    Red on HEAD: AssetProviderAssignment has no ``reported_currency``.
    """
    _z32_column()
    asset_id, _ = await z32_assets.new()
    history = _Z32History("GBP.PENCE")

    result = await _z32_refresh(asset_id, history)

    _z32_refreshed(result, history, 1)
    code, fetched_at = await _z32_assignment(asset_id)
    assert fetched_at is not None, "barrier: the refresh never reached the assignment (last_fetch_at unset), so «not stored» would prove nothing"
    assert code is None, f"a code longer than 8 characters must not be stored, whole or cut: {code!r}"


@pytest.mark.asyncio
async def test_z32_a_history_served_from_the_cache_carries_the_code_it_was_fetched_with(z32_assets):
    """Z-32 (c) §4: the first of two assets assigned alike (mockprov, one identifier, TICKER, no params: one cache key)
    fetches a history reported in ``GBp``; the second, refreshed over the same range, is served whole from the core
    history cache — the provider is not asked again — and its assignment, NULL until then, holds ``GBp``: the cache entry
    carries the code. The first refreshed again, from the cache too, keeps ``GBp``: a cache hit does not erase it.

    Red on HEAD: AssetProviderAssignment has no ``reported_currency``.
    """
    _z32_column()
    first, identifier = await z32_assets.new()
    second, _ = await z32_assets.new(identifier=identifier)
    history = _Z32History("GBp")

    fetched = await _z32_refresh(first, history)
    _z32_refreshed(fetched, history, 1)
    assert (await _z32_assignment(first))[0] == "GBp", "precondition: the fetch left GBp on the first assignment"

    served = await _z32_refresh(second, history)
    _z32_refreshed(served, history, 1)  # still one call: the second history came whole from the cache
    again = await _z32_refresh(first, history)
    _z32_refreshed(again, history, 1)

    codes = {"second, served from the cache": (await _z32_assignment(second))[0], "first, refreshed again from the cache": (await _z32_assignment(first))[0]}
    assert codes == dict.fromkeys(codes, "GBp"), f"a history served from the cache must carry the code it was fetched with: {codes}"


# ============================================================================
# Z-33 — the rows the old Yahoo rule dated, checked once against the provider's own calendar (N86, D″)
# ============================================================================
#
# N86 §5 as revised (D″): stored values never change; the provider's full history serves only as a calendar.
#
# - Gate: the one-time check runs when the assignment holds ``legacy-utc`` (migration 011 puts it on every yfinance
#   assignment of an older install) and its provider code is ``LEGACY_UTC_PROVIDER`` (``"yfinance"``, a constant of
#   ``backend/app/utils/exchange_dates.py`` imported into ``refresh``). These tests open it for mockprov by patching
#   ``refresh.LEGACY_UTC_PROVIDER`` (``_z33_open_gate``). The mark and another provider: no check, normal writes, the
#   mark kept.
# - Calendar: the check refresh asks the provider for its full history, once (``start="min"``, the history cache
#   bypassed), whatever range was asked; the upsert writes only the asked range — prices from the asked start to the
#   history's end, events in the range —, never the rest.
# - Prices: a stored row whose ``source_plugin_key`` is the provider's code moves S → S + 1 when the rule
#   (``local_date_of_legacy_utc_date``) says S + 1, S + 1 is a session of the fresh full history (a date of its price
#   points), and S ≤ D_f − 2, D_f the server-local date of the assignment's ``last_fetch_at`` before this refresh (NULL:
#   no price row moves). Latest first; a row already on S + 1, of any source, stays and the moved one is dropped; values
#   never change; a moved row gets a fresh ``fetched_at``. MANUAL rows and other sources never move.
# - Events: an event of the assignment, of type X, moves S → S + 1 when the rule says S + 1, the fresh history has an
#   event of type X on S + 1 and none on S. A moved SPLIT takes along the ADJUSTMENTs linked to it and dated S (fresh
#   ``updated_at``); no other transaction moves; a shifted event meeting an event of the assignment and type on S + 1
#   merges into it (its transactions re-pointed, then it is deleted); manual events never move.
# - Bookkeeping: the reported timezone is stored in the same transaction as the moves, which clears the mark. Rows older
#   than the fresh history's first session minus one are not moved; a log line gives their count per asset, no values.
# - The mark without a fresh history (the call failed, or answered no price) or without a timezone: nothing written —
#   ``last_fetch_at`` included, so a later check reads the same D_f —, FAILED, the mark kept.
# - Unchanged: NULL learns the timezone and moves nothing; a stored timezone is replaced by another and kept when none is
#   reported; once the mark is cleared, no full-history fetch and nothing moves. The history's timezone, else the
#   current value's; a history served from the core cache carries its own.
#
# Lane-database tests, as the Z-32 cases above: assets of their own on mockprov under identifiers of their own, the mark
# and ``last_fetch_at`` set by hand, rows written with the ORM as the old rule stored them (``fetched_at`` and
# ``updated_at`` stamped ``_Z33_OLD_STAMP``), the provider's two calls answered by ``_Z33Provider`` patched on
# MockProvider (no network, every call recorded): a session each weekday from ``first_session``, a fresh close of
# ``_Z33_FRESH_CLOSE`` on each, and the events given. Today is frozen (``_z33_today``). Unless a test says otherwise the
# last fetch was Monday 2025-06-16 at noon UTC (D_f 06-16 whatever the server's zone), the asked range is Monday 06-23 to
# Wednesday 06-25 — after every seeded row, so a row moves by the check alone and its value shows it — and today is
# Thursday 06-26. The ``z33_lane`` fixture deletes what each test wrote and drops the cache entries of its identifiers.
#
# Red on HEAD 22b9b90ce: AssetProviderAssignment, FAHistoricalData and FACurrentValue have no ``exchange_timezone``,
# ``refresh`` has no ``LEGACY_UTC_PROVIDER``; each test fails on that first (``_z33_contract``).

_Z33_SENTINEL = "legacy-utc"
_Z33_ROME, _Z33_LONDON = "Europe/Rome", "Europe/London"
_Z33_OLD_STAMP = datetime(2025, 5, 31, 6, 0)  # fetched_at and updated_at of every seeded row: before any refresh here
_Z33_FIRST_SESSION = date(2025, 5, 5)  # a Monday: the first session of the fresh full history, unless a test says otherwise
_Z33_LAST_FETCH = datetime(2025, 6, 16, 12, 0)  # Monday at noon UTC: D_f 2025-06-16 in any zone from UTC-11 to UTC+11
_Z33_START, _Z33_END, _Z33_TODAY = date(2025, 6, 23), date(2025, 6, 25), date(2025, 6, 26)  # Monday to Wednesday; Thursday
_Z33_FRESH_CLOSE = Decimal("50")
_Z33_FRESH = {"2025-06-23": _Z33_FRESH_CLOSE, "2025-06-24": _Z33_FRESH_CLOSE, "2025-06-25": _Z33_FRESH_CLOSE}


def _z33_contract():
    """``AssetProviderAssignment.exchange_timezone`` (§4), once the two schemas declare the field too (§1) and
    ``refresh`` imports the gate's ``LEGACY_UTC_PROVIDER`` (D″ §1); until then the test fails here, before any write."""
    column = getattr(AssetProviderAssignment, "exchange_timezone", None)
    expected = (
        ("AssetProviderAssignment.exchange_timezone", column is not None),
        ("FAHistoricalData.exchange_timezone", "exchange_timezone" in FAHistoricalData.model_fields),
        ("FACurrentValue.exchange_timezone", "exchange_timezone" in FACurrentValue.model_fields),
        ("refresh.LEGACY_UTC_PROVIDER", hasattr(refresh, "LEGACY_UTC_PROVIDER")),
    )
    missing = [name for name, there in expected if not there]
    if missing:
        pytest.fail(f"red until Z-33: no {', '.join(missing)} (N86 §1, §4, D″ §1): nothing carries the exchange's timezone, nothing holds or checks legacy-utc", pytrace=False)
    return column


def _z33_open_gate(monkeypatch) -> None:
    """The check's gate opened for mockprov: ``refresh.LEGACY_UTC_PROVIDER`` patched from ``yfinance`` (D″ §1)."""
    _z33_contract()
    monkeypatch.setattr(refresh, "LEGACY_UTC_PROVIDER", "mockprov")


def _z33_point(day: str, kind: str, amount: str = "0.5", currency: str = "EUR") -> FAAssetEventPoint:
    """An event of the fresh history."""
    return FAAssetEventPoint(date=date.fromisoformat(day), type=kind, value=Currency(code=currency, amount=Decimal(amount)))


@dataclass
class _Z33Provider:
    """MockProvider's two price calls, answered for one test (``answering``).

    The history: a session each weekday from ``first_session`` (asked ``"min"``) or from the asked start, to the asked
    end, each with a close of ``_Z33_FRESH_CLOSE``, and the ``events`` dated in that span, under ``zone``; ``fail`` makes
    the call raise, ``empty`` answers no price (the events and the zone still given). The current value: ``current``, a
    (day, value), under ``current_zone``. Every call is recorded: (identifier, start, end), and the identifier.
    """

    zone: str | None
    currency: str = "EUR"
    first_session: date = _Z33_FIRST_SESSION
    events: tuple[FAAssetEventPoint, ...] = ()
    current: tuple[date, Decimal] | None = None
    current_zone: str | None = None
    fail: bool = False
    empty: bool = False
    history_calls: list[tuple[str, AssetHistoryStartDate, date]] = field(default_factory=list)
    current_calls: list[str] = field(default_factory=list)

    async def history(self, identifier, identifier_type, provider_params, start_date, end_date) -> FAHistoricalData:
        self.history_calls.append((identifier, start_date, end_date))
        if self.fail:
            raise AssetSourceError("Z-33 double: the history call failed", "FETCH_ERROR")
        first = self.first_session if start_date == "min" else max(start_date, self.first_session)
        days = [first + timedelta(days=offset) for offset in range((end_date - first).days + 1)]
        sessions = [] if self.empty else [day for day in days if day.weekday() < 5]
        return FAHistoricalData(
            prices=[FAPricePoint(date=day, close=_Z33_FRESH_CLOSE, currency=self.currency) for day in sessions],
            events=[event for event in self.events if first <= event.date <= end_date],
            currency=self.currency,
            source="mockprov",
            exchange_timezone=self.zone,
        )

    async def current_value(self, identifier, identifier_type, provider_params) -> FACurrentValue:
        self.current_calls.append(identifier)
        assert self.current is not None, "the double was asked for a current value it was not given"
        day, value = self.current
        return FACurrentValue(value=value, currency=self.currency, as_of_date=day, source="mockprov", exchange_timezone=self.current_zone)

    @contextmanager
    def answering(self):
        with patch.object(MockProvider, "get_history_value", self.history), patch.object(MockProvider, "get_current_value", self.current_value):
            yield self


@dataclass
class _Z33Lane:
    """The rows one test writes, each committed in a session of its own, for ``z33_lane`` to delete."""

    asset_ids: list[int] = field(default_factory=list)
    broker_ids: list[int] = field(default_factory=list)
    identifiers: set[str] = field(default_factory=set)

    async def asset(self, *, zone: str | None, currency: str = "EUR", identifier: str | None = None, last_fetch: datetime | None = _Z33_LAST_FETCH) -> tuple[int, int]:
        """A ``currency`` asset assigned to mockprov under ``identifier`` (one of its own when None), TICKER, no params,
        then its ``exchange_timezone`` set to ``zone`` (None: NULL, as a new assignment has it) and its ``last_fetch_at``
        to ``last_fetch`` (naive UTC, as stored): (asset id, assignment id)."""
        column = _z33_contract()
        identifier = identifier or f"Z33-{uuid.uuid4().hex[:12]}"
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            asset = Asset(display_name=f"Z-33 line {uuid.uuid4().hex[:12]}", currency=currency, asset_type=AssetType.STOCK, active=True)
            session.add(asset)
            await session.commit()
            await session.refresh(asset)
            self.asset_ids.append(asset.id)
            self.identifiers.add(identifier)
            item = FAProviderAssignmentItem(asset_id=asset.id, provider_code="mockprov", identifier=identifier, identifier_type=ProviderInputType.TICKER, provider_params=None)
            results = await AssetSourceManager.bulk_assign_providers([item], session)
            assert [result.success for result in results] == [True], f"setup: the assignment of asset {asset.id}: {results}"
            assignment_id = (await session.execute(select(AssetProviderAssignment.id).where(AssetProviderAssignment.asset_id == asset.id))).scalar_one()
            await session.execute(update(AssetProviderAssignment).where(AssetProviderAssignment.id == assignment_id).values({column: zone, AssetProviderAssignment.last_fetch_at: last_fetch}))
            await session.commit()
        return asset.id, assignment_id

    async def prices(self, asset_id: int, closes: dict[str, int | Decimal], *, source: str = "mockprov", currency: str = "EUR") -> None:
        """One price row per day, ``source`` its ``source_plugin_key``, fetched at ``_Z33_OLD_STAMP``."""
        async with AsyncSession(get_async_engine()) as session:
            session.add_all(PriceHistory(asset_id=asset_id, date=date.fromisoformat(day), close=Decimal(close), currency=currency, source_plugin_key=source, fetched_at=_Z33_OLD_STAMP) for day, close in closes.items())
            await session.commit()

    async def event(self, asset_id: int, day: str, kind: AssetEventType, value: str, *, assignment_id: int | None, currency: str = "EUR") -> int:
        """An event of the assignment ``assignment_id`` (None: a manual one); its id."""
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            row = AssetEvent(asset_id=asset_id, date=date.fromisoformat(day), type=kind, value=Decimal(value), currency=currency, provider_assignment_id=assignment_id, created_at=_Z33_OLD_STAMP, updated_at=_Z33_OLD_STAMP)
            session.add(row)
            await session.commit()
            return row.id

    async def broker(self) -> int:
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            broker = Broker(name=f"Z-33 broker {uuid.uuid4().hex[:12]}")
            session.add(broker)
            await session.commit()
            self.broker_ids.append(broker.id)
            return broker.id

    async def transaction(self, broker_id: int, asset_id: int, kind: TransactionType, day: str, *, quantity: str = "0", amount: str = "0", currency: str | None = None, event_id: int | None = None) -> int:
        """A transaction on one of this test's brokers, updated at ``_Z33_OLD_STAMP``; its id."""
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            row = Transaction(
                broker_id=broker_id,
                asset_id=asset_id,
                type=kind,
                date=date.fromisoformat(day),
                quantity=Decimal(quantity),
                amount=Decimal(amount),
                currency=currency,
                asset_event_id=event_id,
                created_at=_Z33_OLD_STAMP,
                updated_at=_Z33_OLD_STAMP,
            )
            session.add(row)
            await session.commit()
            return row.id


@pytest_asyncio.fixture
async def z33_lane():
    """The rows of one test; at teardown the transactions of its brokers go first (``asset_event_id`` is ``ON DELETE
    RESTRICT``), then its assets' events, prices and assignments, its assets, its brokers, and the cache entries of its
    identifiers."""
    assert initialize_test_database(), "Failed to initialize test database"
    AssetProviderRegistry.auto_discover()
    lane = _Z33Lane()
    yield lane
    deleted_assets = 0
    async with AsyncSession(get_async_engine()) as session:
        if lane.broker_ids:
            await session.execute(delete(Transaction).where(Transaction.broker_id.in_(lane.broker_ids)))
        if lane.asset_ids:
            await session.execute(delete(AssetEvent).where(AssetEvent.asset_id.in_(lane.asset_ids)))
            await session.execute(delete(PriceHistory).where(PriceHistory.asset_id.in_(lane.asset_ids)))
            await session.execute(delete(AssetProviderAssignment).where(AssetProviderAssignment.asset_id.in_(lane.asset_ids)))
            deleted_assets = (await session.execute(delete(Asset).where(Asset.id.in_(lane.asset_ids)))).rowcount
        if lane.broker_ids:
            await session.execute(delete(Broker).where(Broker.id.in_(lane.broker_ids)))
        await session.commit()
    for identifier in lane.identifiers:
        await core.drop_asset_cache_entries("mockprov", identifier, ProviderInputType.TICKER, None)
    assert deleted_assets == len(lane.asset_ids), f"cleanup: {deleted_assets} of the assets {lane.asset_ids} deleted"


class _Z33DateType(type):
    """The metaclass of ``_z33_today``'s date type: ``isinstance`` stays true of every plain date."""

    def __instancecheck__(cls, instance) -> bool:
        return isinstance(instance, date)


@contextmanager
def _z33_today(day: date):
    """``refresh.date_type`` with ``today()`` frozen on ``day`` (the refresh reads the day there, as the X-R12 tests
    freeze it), ``isinstance`` still true of every plain date: a run across midnight compares no two days."""

    class _Frozen(date, metaclass=_Z33DateType):
        @classmethod
        def today(cls) -> date:
            return day

    with patch.object(refresh, "date_type", _Frozen):
        yield day


async def _z33_refresh(asset_id: int, provider: _Z33Provider, *, start: date = _Z33_START, end: date = _Z33_END, today: date = _Z33_TODAY) -> FARefreshResult:
    """The refresh of one asset from ``start`` to ``end`` on the frozen ``today``, ``provider`` answering for mockprov."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        with provider.answering(), _z33_today(today):
            response = await AssetSourceManager.bulk_refresh_prices([FARefreshItem(asset_id=asset_id, date_range=SyncDateRangeModel(start=start, end=end))], session)
    (result,) = response.results
    return result


def _z33_went_through(result: FARefreshResult, provider: _Z33Provider, *, history_starts: list) -> None:
    """The refresh went through — OK, no error — and every history call so far began as ``history_starts`` says, in
    order: ``"min"`` for the check's full-history fetch, a date for a call over the asked range."""
    observed = (result.status, result.errors, [start for _identifier, start, _end in provider.history_calls])
    assert observed == (SyncStatus.OK, [], history_starts), f"the refresh must go through, its history calls starting {history_starts}: (status, errors, starts) {observed}"


async def _z33_prices(asset_id: int) -> dict[str, tuple[Decimal, str, datetime]]:
    """``{day: (close, source_plugin_key, fetched_at)}`` of the asset's price rows."""
    async with AsyncSession(get_async_engine()) as session:
        rows = (await session.execute(select(PriceHistory.date, PriceHistory.close, PriceHistory.source_plugin_key, PriceHistory.fetched_at).where(PriceHistory.asset_id == asset_id))).all()
    return {day.isoformat(): (close, source, fetched_at) for day, close, source, fetched_at in rows}


def _z33_without(prices: dict[str, tuple], fresh: dict[str, Decimal]) -> dict[str, tuple]:
    """``prices`` without the days of the asked range ``fresh``: the rows a refresh did not write."""
    return {day: row for day, row in prices.items() if day not in fresh}


async def _z33_closes(asset_id: int) -> dict[str, Decimal]:
    return {day: close for day, (close, _source, _fetched_at) in (await _z33_prices(asset_id)).items()}


async def _z33_events(asset_id: int) -> dict[int, tuple[str, str, int | None]]:
    """``{event id: (day, type, provider_assignment_id)}`` of the asset's events, manual ones included."""
    async with AsyncSession(get_async_engine()) as session:
        rows = (await session.execute(select(AssetEvent.id, AssetEvent.date, AssetEvent.type, AssetEvent.provider_assignment_id).where(AssetEvent.asset_id == asset_id))).all()
    return {event_id: (day.isoformat(), str(kind), assignment_id) for event_id, day, kind, assignment_id in rows}


async def _z33_transactions(transaction_ids: list[int]) -> dict[int, tuple[str, int | None, datetime]]:
    """``{transaction id: (day, asset_event_id, updated_at)}``."""
    async with AsyncSession(get_async_engine()) as session:
        rows = (await session.execute(select(Transaction.id, Transaction.date, Transaction.asset_event_id, Transaction.updated_at).where(Transaction.id.in_(transaction_ids)))).all()
    return {transaction_id: (day.isoformat(), event_id, updated_at) for transaction_id, day, event_id, updated_at in rows}


async def _z33_zone(asset_id: int) -> str | None:
    column = _z33_contract()
    async with AsyncSession(get_async_engine()) as session:
        return (await session.execute(select(column).where(AssetProviderAssignment.asset_id == asset_id))).scalar_one()


async def _z33_last_fetch(asset_id: int) -> datetime | None:
    async with AsyncSession(get_async_engine()) as session:
        return (await session.execute(select(AssetProviderAssignment.last_fetch_at).where(AssetProviderAssignment.asset_id == asset_id))).scalar_one()


async def _z33_split_links(transaction_ids: list[int]) -> dict[int, tuple[str, str, bool]]:
    """``{transaction id: (its day, its SPLIT's day, accepted by Yield on Cost)}`` for those of ``transaction_ids`` linked
    to a SPLIT, read as Yield on Cost reads them (``load_split_links``, then ``_index_split_records``)."""
    async with AsyncSession(get_async_engine()) as session:
        transactions = list((await session.execute(select(Transaction).where(Transaction.id.in_(transaction_ids)))).scalars().all())
        links = await load_split_links(session, transactions)
    ratios, _event_ids, invalid = _index_split_records(links)
    return {link.transaction_id: (link.transaction_date.isoformat(), link.event_date.isoformat(), link.transaction_id in ratios.get(link.transaction_asset_id, {}) and link.broker_id not in invalid.get(link.transaction_asset_id, set())) for link in links}


# -- §1, §2: the gate and the calendar fetch ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_z33_the_check_runs_only_for_the_legacy_provider(z33_lane):
    """Z-33 (D″ §1): the gate as shipped (``LEGACY_UTC_PROVIDER`` is ``yfinance``): a mockprov assignment holding the mark
    is refreshed as any other — one history call over the asked range, no full-history fetch, the fresh closes written —;
    the closes and the DIVIDEND the check would move (Sunday 06-01 and Monday 06-02; Wednesday 06-11, the fresh history
    dating it Thursday 06-12) stay where they are, values and ``fetched_at`` included; the mark stays, though the history
    reports ``Europe/Rome``.

    Red on HEAD: ``_z33_contract``.
    """
    _z33_contract()
    from backend.app.utils import exchange_dates  # noqa: PLC0415 — red until Z-33: the module is imported where it is read

    gate = (exchange_dates.LEGACY_UTC_PROVIDER, refresh.LEGACY_UTC_PROVIDER)
    assert gate == ("yfinance", "yfinance"), f"the gate's provider must be yfinance, in exchange_dates and as refresh imports it: {gate}"
    asset_id, assignment_id = await z33_lane.asset(zone=_Z33_SENTINEL)
    await z33_lane.prices(asset_id, {"2025-06-01": 101, "2025-06-02": 102})
    await z33_lane.event(asset_id, "2025-06-11", AssetEventType.DIVIDEND, "0.5", assignment_id=assignment_id)
    stored_before, events_before = await _z33_prices(asset_id), await _z33_events(asset_id)
    provider = _Z33Provider(zone=_Z33_ROME, events=(_z33_point("2025-06-12", "DIVIDEND"),))

    result = await _z33_refresh(asset_id, provider)

    _z33_went_through(result, provider, history_starts=[_Z33_START])
    prices = await _z33_prices(asset_id)
    assert _z33_without(prices, _Z33_FRESH) == stored_before, "no stored row may move: there is no check for another provider"
    assert {day: prices[day][0] for day in _Z33_FRESH if day in prices} == _Z33_FRESH, "the fresh closes must be written as always"
    assert await _z33_events(asset_id) == events_before, "no event may move"
    assert await _z33_zone(asset_id) == _Z33_SENTINEL, "the mark must stay"


@pytest.mark.asyncio
async def test_z33_the_check_fetches_the_full_history_past_the_cache_and_writes_only_the_asked_range(z33_lane, monkeypatch):
    """Z-33 (D″ §2): two assets assigned alike (one cache key). The first, NULL, fetches the asked range: the core history
    cache holds all of it. The second, holding the mark, refreshed over the same range, is not served from that cache:
    the provider is asked once more, for its full history (``start="min"``). Of that history only the asked range is
    written — the closes of 06-23 to 06-25, the DIVIDEND of 06-24 —, never the rest: no close from 05-05 to 06-20, not
    the DIVIDEND of 05-15. The mark gives way to ``Europe/Rome``.

    Red on HEAD: ``_z33_contract``.
    """
    _z33_open_gate(monkeypatch)
    first, _ = await z33_lane.asset(zone=None)
    (identifier,) = z33_lane.identifiers
    second, _ = await z33_lane.asset(zone=_Z33_SENTINEL, identifier=identifier)
    provider = _Z33Provider(zone=_Z33_ROME, events=(_z33_point("2025-05-15", "DIVIDEND"), _z33_point("2025-06-24", "DIVIDEND")))
    _z33_went_through(await _z33_refresh(first, provider), provider, history_starts=[_Z33_START])

    result = await _z33_refresh(second, provider)

    _z33_went_through(result, provider, history_starts=[_Z33_START, "min"])
    assert await _z33_closes(second) == _Z33_FRESH, "only the closes of the asked range may be written"
    assert sorted((day, kind) for day, kind, _assignment in (await _z33_events(second)).values()) == [("2025-06-24", "DIVIDEND")], "only the events of the asked range may be written"
    assert await _z33_zone(second) == _Z33_ROME, "the check must clear the mark"


# -- §3: the prices ----------------------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_z33_a_legacy_series_moves_to_its_exchange_days_latest_first(z33_lane, monkeypatch):
    """Z-33 (D″ §3): the closes the old rule stored on Sunday 06-01 to Thursday 06-05 move each to the next day, Monday
    06-02 to Friday 06-06 — latest first, so none meets a neighbour still in place and none is lost —, their values
    kept; nothing stays on 06-01; the fresh closes of the asked range are written; the assignment holds ``Europe/Rome``.

    Red on HEAD: ``_z33_contract``.
    """
    _z33_open_gate(monkeypatch)
    asset_id, _ = await z33_lane.asset(zone=_Z33_SENTINEL)
    await z33_lane.prices(asset_id, {"2025-06-01": 101, "2025-06-02": 102, "2025-06-03": 103, "2025-06-04": 104, "2025-06-05": 105})
    provider = _Z33Provider(zone=_Z33_ROME)

    result = await _z33_refresh(asset_id, provider)

    _z33_went_through(result, provider, history_starts=["min"])
    expected = {"2025-06-02": 101, "2025-06-03": 102, "2025-06-04": 103, "2025-06-05": 104, "2025-06-06": 105} | _Z33_FRESH
    assert await _z33_closes(asset_id) == expected, "each close the old rule stored must move to its exchange day, its value kept, none lost"
    assert await _z33_zone(asset_id) == _Z33_ROME, "the check must clear the mark"


@pytest.mark.asyncio
async def test_z33_a_moved_price_row_gets_a_fresh_fetched_at(z33_lane, monkeypatch):
    """Z-33 (D″ §3): a price row the check moves gets a ``fetched_at`` later than the one it had: the portfolio cache keys
    on COUNT + MAX(fetched_at) of the prices (``engine._compute_price_fingerprint``), which a move alone leaves unchanged.
    Both moved rows lie outside the asked range, so no fresh write stamps them.

    Red on HEAD: ``_z33_contract``.
    """
    _z33_open_gate(monkeypatch)
    asset_id, _ = await z33_lane.asset(zone=_Z33_SENTINEL)
    await z33_lane.prices(asset_id, {"2025-06-01": 101, "2025-06-02": 102})
    provider = _Z33Provider(zone=_Z33_ROME)

    result = await _z33_refresh(asset_id, provider)

    _z33_went_through(result, provider, history_starts=["min"])
    prices = await _z33_prices(asset_id)
    moved = {day: prices.get(day) for day in ("2025-06-02", "2025-06-03")}
    assert {day: row[0] if row else None for day, row in moved.items()} == {"2025-06-02": 101, "2025-06-03": 102}, f"barrier: the two closes moved: {prices}"
    stale = {day: row[2].isoformat() for day, row in moved.items() if not row[2] > _Z33_OLD_STAMP}
    assert stale == {}, f"a moved row must get a fresh fetched_at, later than {_Z33_OLD_STAMP.isoformat()}: {stale}"


@pytest.mark.asyncio
async def test_z33_manual_rows_and_other_sources_never_move_and_keep_their_day(z33_lane, monkeypatch):
    """Z-33 (D″ §3): only the provider's own rows move. Provider closes on 06-02, 06-03 and 06-05; MANUAL closes on 06-04
    (where the 06-03 close is due) and 06-09; closes of another source (``justetf``, the asset's previous provider) on
    06-06 (where the 06-05 close is due) and 06-12; a manual DIVIDEND on 06-09 and a manual SPLIT on 06-12 with its
    ADJUSTMENT, the fresh history dating a DIVIDEND on 06-10 and a SPLIT on 06-13. Latest first: the 06-05 close meets
    ``justetf`` on 06-06 and is dropped, the 06-03 close meets MANUAL on 06-04 and is dropped, the 06-02 close moves to
    06-03, freed. Every MANUAL and ``justetf`` row keeps its day, close and ``fetched_at``, though the rule, the calendar
    and D_f would move a provider's row from there (06-04 to 06-05, 06-09 to 06-10, 06-12 to 06-13); the manual events
    and the ADJUSTMENT stay as they were.

    Red on HEAD: ``_z33_contract``.
    """
    _z33_open_gate(monkeypatch)
    asset_id, _ = await z33_lane.asset(zone=_Z33_SENTINEL)
    await z33_lane.prices(asset_id, {"2025-06-02": 102, "2025-06-03": 103, "2025-06-05": 105})
    await z33_lane.prices(asset_id, {"2025-06-04": 904, "2025-06-09": 909}, source="MANUAL")
    await z33_lane.prices(asset_id, {"2025-06-06": 706, "2025-06-12": 712}, source="justetf")
    manual_dividend = await z33_lane.event(asset_id, "2025-06-09", AssetEventType.DIVIDEND, "0.4", assignment_id=None)
    manual_split = await z33_lane.event(asset_id, "2025-06-12", AssetEventType.SPLIT, "2", assignment_id=None)
    adjustment = await z33_lane.transaction(await z33_lane.broker(), asset_id, TransactionType.ADJUSTMENT, "2025-06-12", quantity="10", event_id=manual_split)
    events_before, adjustment_before = await _z33_events(asset_id), await _z33_transactions([adjustment])
    provider = _Z33Provider(zone=_Z33_ROME, events=(_z33_point("2025-06-10", "DIVIDEND"), _z33_point("2025-06-13", "SPLIT", "2")))

    result = await _z33_refresh(asset_id, provider)

    _z33_went_through(result, provider, history_starts=["min"])
    prices = _z33_without(await _z33_prices(asset_id), _Z33_FRESH)
    assert {day: (close, source) for day, (close, source, _fetched_at) in prices.items()} == {
        "2025-06-03": (102, "mockprov"),
        "2025-06-04": (904, "MANUAL"),
        "2025-06-06": (706, "justetf"),
        "2025-06-09": (909, "MANUAL"),
        "2025-06-12": (712, "justetf"),
    }, "the provider's closes move unless a row is on their new day; MANUAL and justetf rows never move"
    restamped = {day: row[2].isoformat() for day, row in prices.items() if row[1] != "mockprov" and row[2] != _Z33_OLD_STAMP}
    assert restamped == {}, f"a row that does not move is not written: {restamped}"
    assert set(events_before) == {manual_dividend, manual_split}, f"barrier: the asset's events are the two manual ones: {events_before}"
    assert (await _z33_events(asset_id), await _z33_transactions([adjustment])) == (events_before, adjustment_before), "manual events never move, nor the transactions linked to them"


@pytest.mark.asyncio
async def test_z33_a_correct_friday_stays_and_the_shifted_thursday_gives_way_to_it(z33_lane, monkeypatch):
    """Z-33 (D″ §3, §8, the first question of the red set): the last fetch on Monday 06-09 at noon UTC, after one on
    Friday 06-06. Stored by the old rule: the closes of Monday 06-02 to Friday 06-06 (102 to 106) each on the day before,
    Sunday 06-01 to Thursday 06-05; Friday's current value, 106.5, on Friday 06-06 (right: a current value was dated by
    its UTC day); Monday's, 109.5, on Monday 06-09. The Friday row stays: the rule says Saturday, no session. The Thursday
    row, Friday's close, moves to Friday, meets the Friday row and is dropped, the Friday row keeping its value. Wednesday
    to Sunday then move each to the next day, freed in turn. Monday 06-09 stays: after D_f − 2.

    Red on HEAD: ``_z33_contract``.
    """
    _z33_open_gate(monkeypatch)
    asset_id, _ = await z33_lane.asset(zone=_Z33_SENTINEL, last_fetch=datetime(2025, 6, 9, 12, 0))
    stored = {"2025-06-01": 102, "2025-06-02": 103, "2025-06-03": 104, "2025-06-04": 105, "2025-06-05": 106, "2025-06-06": Decimal("106.5"), "2025-06-09": Decimal("109.5")}
    await z33_lane.prices(asset_id, stored)
    kept_before = {day: row for day, row in (await _z33_prices(asset_id)).items() if day in ("2025-06-06", "2025-06-09")}
    provider = _Z33Provider(zone=_Z33_ROME)

    result = await _z33_refresh(asset_id, provider)

    _z33_went_through(result, provider, history_starts=["min"])
    prices = _z33_without(await _z33_prices(asset_id), _Z33_FRESH)
    expected = {"2025-06-02": 102, "2025-06-03": 103, "2025-06-04": 104, "2025-06-05": 105, "2025-06-06": Decimal("106.5"), "2025-06-09": Decimal("109.5")}
    assert {day: row[0] for day, row in prices.items()} == expected, "the Friday row stays, the shifted Thursday gives way to it, the rest move a day"
    assert {day: prices[day] for day in kept_before} == kept_before, "the Friday and Monday rows must not be written: value and fetched_at as they were"


@pytest.mark.asyncio
async def test_z33_rows_after_two_days_before_the_last_fetch_stay(z33_lane, monkeypatch):
    """Z-33 (D″ §3, §8): the last fetch on Wednesday 06-11 at noon UTC (D_f; D_f − 2 is Monday 06-09). Stored: Sunday
    06-08 (Monday's close, 109), Monday 06-09 (Tuesday's close, 110, as the old rule dated it), Tuesday 06-10 and
    Wednesday 06-11 (their current values, 110.5 and 111.5: right). Tuesday and Wednesday are after D_f − 2: they stay,
    though the rule and the calendar would move them (Wednesday to Thursday 06-12, a free session; Tuesday after it). The
    Monday row, on D_f − 2, moves to Tuesday, meets it and is dropped; Sunday moves to Monday, freed. One day either way
    at the bound gives another end.

    Red on HEAD: ``_z33_contract``.
    """
    _z33_open_gate(monkeypatch)
    asset_id, _ = await z33_lane.asset(zone=_Z33_SENTINEL, last_fetch=datetime(2025, 6, 11, 12, 0))
    await z33_lane.prices(asset_id, {"2025-06-08": 109, "2025-06-09": 110, "2025-06-10": Decimal("110.5"), "2025-06-11": Decimal("111.5")})
    tail_before = {day: row for day, row in (await _z33_prices(asset_id)).items() if day in ("2025-06-10", "2025-06-11")}
    provider = _Z33Provider(zone=_Z33_ROME)

    result = await _z33_refresh(asset_id, provider)

    _z33_went_through(result, provider, history_starts=["min"])
    prices = _z33_without(await _z33_prices(asset_id), _Z33_FRESH)
    assert {day: row[0] for day, row in prices.items()} == {"2025-06-09": 109, "2025-06-10": Decimal("110.5"), "2025-06-11": Decimal("111.5")}, "only the rows up to D_f − 2 may move"
    assert {day: prices[day] for day in tail_before} == tail_before, "the rows after D_f − 2 must not be written: value and fetched_at as they were"


@pytest.mark.asyncio
async def test_z33_without_a_last_fetch_no_price_row_moves(z33_lane, monkeypatch):
    """Z-33 (D″ §3): an assignment whose ``last_fetch_at`` is NULL has no D_f: no price row moves — the closes of Sunday
    06-01 and Monday 06-02 stay, values and ``fetched_at`` included —, though the check runs (the full-history fetch)
    and clears the mark.

    Red on HEAD: ``_z33_contract``.
    """
    _z33_open_gate(monkeypatch)
    asset_id, _ = await z33_lane.asset(zone=_Z33_SENTINEL, last_fetch=None)
    await z33_lane.prices(asset_id, {"2025-06-01": 101, "2025-06-02": 102})
    stored_before = await _z33_prices(asset_id)
    provider = _Z33Provider(zone=_Z33_ROME)

    result = await _z33_refresh(asset_id, provider)

    _z33_went_through(result, provider, history_starts=["min"])
    assert _z33_without(await _z33_prices(asset_id), _Z33_FRESH) == stored_before, "without a last fetch no price row may move"
    assert await _z33_zone(asset_id) == _Z33_ROME, "the check must clear the mark"


@pytest.mark.asyncio
async def test_z33_a_london_series_moves_only_its_summer_time_rows(z33_lane, monkeypatch):
    """Z-33 (D″ §3, §4, §8): a London line across both 2025 changes, last fetched on Wednesday 10-29, the full history
    from Monday 03-03, the asked range Monday 11-03 to Wednesday 11-05. Stored by the old rule: Thursday 03-27 and Friday
    03-28 (GMT, right), Sunday 03-30 and Monday 03-31 (the BST Monday and Tuesday, a day early), Wednesday 10-22 and
    Thursday 10-23 (the BST Thursday and Friday), Monday 10-27 and Tuesday 10-28 (GMT, right). Only the four summer-time
    closes move. The DIVIDENDs follow the same rule: 03-30 and 10-23 move, the fresh history dating them 03-31 and 10-24;
    03-28 stays; 10-27 stays though the fresh history dates a DIVIDEND on 10-28 and none on 10-27 — the rule says 10-27.

    Red on HEAD: ``_z33_contract``.
    """
    _z33_open_gate(monkeypatch)
    asset_id, assignment_id = await z33_lane.asset(zone=_Z33_SENTINEL, currency="GBP", last_fetch=datetime(2025, 10, 29, 12, 0))
    stored = ["2025-03-27", "2025-03-28", "2025-03-30", "2025-03-31", "2025-10-22", "2025-10-23", "2025-10-27", "2025-10-28"]
    await z33_lane.prices(asset_id, {day: position + 1 for position, day in enumerate(stored)}, currency="GBP")
    dividends = {day: await z33_lane.event(asset_id, day, AssetEventType.DIVIDEND, "0.3", assignment_id=assignment_id, currency="GBP") for day in ("2025-03-28", "2025-03-30", "2025-10-23", "2025-10-27")}
    fresh_events = tuple(_z33_point(day, "DIVIDEND", "0.3", "GBP") for day in ("2025-03-28", "2025-03-31", "2025-10-24", "2025-10-28"))
    provider = _Z33Provider(zone=_Z33_LONDON, currency="GBP", first_session=date(2025, 3, 3), events=fresh_events)

    result = await _z33_refresh(asset_id, provider, start=date(2025, 11, 3), end=date(2025, 11, 5), today=date(2025, 11, 6))

    _z33_went_through(result, provider, history_starts=["min"])
    exchange_days = ["2025-03-27", "2025-03-28", "2025-03-31", "2025-04-01", "2025-10-23", "2025-10-24", "2025-10-27", "2025-10-28"]
    fresh = dict.fromkeys(("2025-11-03", "2025-11-04", "2025-11-05"), _Z33_FRESH_CLOSE)
    assert await _z33_closes(asset_id) == {day: position + 1 for position, day in enumerate(exchange_days)} | fresh, "only the summer-time closes move"
    events = await _z33_events(asset_id)
    assert {day: events[event_id][0] for day, event_id in dividends.items()} == {
        "2025-03-28": "2025-03-28",
        "2025-03-30": "2025-03-31",
        "2025-10-23": "2025-10-24",
        "2025-10-27": "2025-10-27",
    }, "only the summer-time DIVIDENDs move"
    assert len(events) == len(dividends), f"no fresh event outside the asked range may be written: {events}"


@pytest.mark.asyncio
async def test_z33_rows_older_than_the_full_history_stay_and_their_count_is_logged(z33_lane, monkeypatch):
    """Z-33 (D″ §5): the fresh full history begins on Monday 05-05. The closes stored on Tuesday 04-29, Wednesday 04-30
    and Thursday 05-01, older than its first session minus one, stay, values included — no session of that history can
    date them —; a log line gives their count for the asset, 3, and none of their values. The close stored on Sunday
    05-04, the first session minus one, moves to Monday 05-05.

    The line is read as the project logs (structlog, ``asset_id=``, captured with ``structlog.testing.capture_logs``):
    some event logged during the refresh names the asset under ``asset_id`` and carries the count, 3, as an integer;
    which key holds it, the level and the words are free.

    Red on HEAD: ``_z33_contract``.
    """
    _z33_open_gate(monkeypatch)
    asset_id, _ = await z33_lane.asset(zone=_Z33_SENTINEL)
    old = {"2025-04-29": Decimal("7771.25"), "2025-04-30": Decimal("7772.5"), "2025-05-01": Decimal("7773.75")}
    await z33_lane.prices(asset_id, old | {"2025-05-04": 105})
    provider = _Z33Provider(zone=_Z33_ROME)

    with capture_logs() as logs:
        result = await _z33_refresh(asset_id, provider)

    _z33_went_through(result, provider, history_starts=["min"])
    assert await _z33_closes(asset_id) == old | {"2025-05-05": 105} | _Z33_FRESH, "the rows older than the full history stay; the one on its first session minus one moves"
    counted = [entry for entry in logs if entry.get("asset_id") == asset_id and 3 in [value for key, value in entry.items() if key != "asset_id" and type(value) is int]]
    assert counted, f"a log line must give the count of the rows the full history cannot date, 3, for asset {asset_id}: {[(entry.get('event'), entry.get('asset_id')) for entry in logs]}"
    leaked = [entry.get("event") for entry in logs if any(text in repr(entry) for text in ("7771.25", "7772.5", "7773.75"))]
    assert leaked == [], f"no log line may give their values: {leaked}"


# -- §3, MF: a target before its row's day is refused ------------------------------------------------------------------
#
# ``PriceStoreOperations.redate_provider_rows`` handles the rows latest first, which keeps a moving row off one not yet
# handled only while every target lies after its row — as the check's own ``target_of`` does, S → S + 1. Reviewer MF
# (LOW): a generic ``target_of`` giving an earlier day can meet a row of the asset not yet handled, and the moving row
# is then dropped, its close lost. As approved: every target is computed before anything moves; one before its row's
# day raises a ValueError naming the asset, the row's day and the target (days only, never a price), and nothing is
# written — no row moved or deleted, every date, close and ``fetched_at`` as it was. None or the row's own day: the
# row stays; a later day: the row moves as before.
#
# The helper is called directly (``_z33_redate``), no refresh, no provider call, on ``yfinance`` rows fetched at
# ``_Z33_OLD_STAMP`` of an asset of the test's own (``z33_lane``, which deletes them; its mockprov assignment plays no
# part). The three refusals are red on HEAD f21ce12d1 for the refusal itself (``_z33_contract`` passes there); the
# forward case is green there and must stay so.

_Z33_REDATED = "yfinance"  # the source_plugin_key of the rows these tests write and re-date


async def _z33_redate(asset_id: int, targets: dict[str, str | None]) -> tuple[int, int] | ValueError:
    """``PriceStoreOperations.redate_provider_rows`` on the asset's ``yfinance`` rows, in a session of its own, its
    ``target_of`` read from ``targets`` (``{stored day: target day}``; None, or a day not given: the row stays): the
    (moved, dropped) it returned, or the ValueError it raised. Committed either way: the helper flushes after each row
    and never commits, and only a commit lets the fresh read that follows see what it did — a move or a drop made
    before a refusal included, which a rollback would hide."""

    def target_of(day: date) -> date | None:
        target = targets.get(day.isoformat())
        return None if target is None else date.fromisoformat(target)

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        outcome: tuple[int, int] | ValueError
        try:
            outcome = await PriceStoreOperations.redate_provider_rows(session, asset_id, _Z33_REDATED, target_of)
        except ValueError as refused:
            outcome = refused
        await session.commit()
    return outcome


def _z33_refused(outcome: tuple[int, int] | ValueError, asset_id: int, *, stored: str, target: str, subject: str = "row", returned: str = "(moved, dropped)") -> None:
    """``outcome`` is the refusal of the target ``target`` given to the ``subject`` (a price row, or an event) on
    ``stored``: a ValueError naming the asset and the two days in ISO form, the wording free. The id is looked for among
    the message's numbers once the two days are taken out, so a day's digits cannot stand in for it. ``returned`` names
    the pair a re-date gives back when it does not refuse."""
    assert isinstance(outcome, ValueError), f"a target before its {subject}'s day must be refused with a ValueError, before anything moves: the re-date returned {returned} {outcome!r}"
    message = str(outcome)
    numbers = re.findall(r"\d+", message.replace(stored, " ").replace(target, " "))
    named = {"the asset": str(asset_id) in numbers, f"the {subject}'s day": stored in message, "its target": target in message}
    assert all(named.values()), f"the refusal must name asset {asset_id}, the {subject}'s day {stored} and its target {target}: {named}, in {message!r}"


@pytest.mark.asyncio
async def test_z33_redate_refuses_a_backward_target_and_moves_nothing(z33_lane):
    """Z-33 (MF): a target before its row's day is refused, though nothing stands on it. Rows on Monday 03-03 and Monday
    03-10; the 03-03 row given Sunday 03-02, a free day, the 03-10 row None. The call raises a ValueError naming the
    asset, 03-03 and 03-02, and nothing is written: both rows on their day, close and ``fetched_at`` as they were.

    Red on HEAD f21ce12d1: the 03-03 row moves to 03-02, (1, 0) returned, no error.
    """
    asset_id, _ = await z33_lane.asset(zone=None)
    await z33_lane.prices(asset_id, {"2025-03-03": 103, "2025-03-10": 110}, source=_Z33_REDATED)
    before = await _z33_prices(asset_id)

    outcome = await _z33_redate(asset_id, {"2025-03-03": "2025-03-02", "2025-03-10": None})

    _z33_refused(outcome, asset_id, stored="2025-03-03", target="2025-03-02")
    assert await _z33_prices(asset_id) == before, "a refused re-date must write nothing: each row on its day, close and fetched_at as they were"


@pytest.mark.asyncio
async def test_z33_redate_refuses_before_moving_a_forward_row(z33_lane):
    """Z-33 (MF): every target is checked before any row moves. Rows on Monday 03-03 and Monday 03-10; the 03-10 row
    given Tuesday 03-11 (later, free), the 03-03 row Sunday 03-02 (earlier). Latest first, the 03-10 row is reached
    before the 03-03 row: the call raises all the same, naming the asset, 03-03 and 03-02, and the 03-10 row is still on
    03-10, its ``fetched_at`` as it was — ``_z33_redate`` commits after the refusal, so a move made before it would
    show.

    Red on HEAD f21ce12d1: both rows move, (2, 0) returned, no error.
    """
    asset_id, _ = await z33_lane.asset(zone=None)
    await z33_lane.prices(asset_id, {"2025-03-03": 103, "2025-03-10": 110}, source=_Z33_REDATED)
    before = await _z33_prices(asset_id)

    outcome = await _z33_redate(asset_id, {"2025-03-03": "2025-03-02", "2025-03-10": "2025-03-11"})

    _z33_refused(outcome, asset_id, stored="2025-03-03", target="2025-03-02")
    after = await _z33_prices(asset_id)
    assert after.get("2025-03-10") == before["2025-03-10"], f"the 03-10 row must not move before the refusal: still on 03-10, fetched_at as it was: {after}"
    assert after == before, "a refused re-date must write nothing: each row on its day, close and fetched_at as they were"


@pytest.mark.asyncio
async def test_z33_redate_backward_target_onto_an_unprocessed_row_drops_nothing(z33_lane):
    """Z-33 (MF's case): rows on Monday 03-03 and Tuesday 03-04; the 03-04 row given 03-03 — an earlier day, where the
    other row stands, not yet reached —, the 03-03 row None. Latest first, the 03-04 row finds 03-03 taken and is
    deleted, its close lost. Refused instead, naming the asset, 03-04 and 03-03: both rows stay, close and
    ``fetched_at`` as they were.

    Red on HEAD f21ce12d1: the 03-04 row is deleted, (0, 1) returned, no error.
    """
    asset_id, _ = await z33_lane.asset(zone=None)
    await z33_lane.prices(asset_id, {"2025-03-03": 103, "2025-03-04": 104}, source=_Z33_REDATED)
    before = await _z33_prices(asset_id)

    outcome = await _z33_redate(asset_id, {"2025-03-03": None, "2025-03-04": "2025-03-03"})

    _z33_refused(outcome, asset_id, stored="2025-03-04", target="2025-03-03")
    assert await _z33_prices(asset_id) == before, "no close may be dropped: a refused re-date writes nothing, both rows on their day, close and fetched_at as they were"


@pytest.mark.asyncio
async def test_z33_redate_moves_forward_targets_as_before(z33_lane):
    """Z-33 (MF, the guard's other side): a later day moves its row as before; None and the row's own day leave it. Rows
    on Mondays 03-03, 03-10, 03-17 and 03-24; the first two given the next day, the third None, the fourth its own day.
    (2, 0) returned: the first two on Tuesdays 03-04 and 03-11, their closes kept, a fresh ``fetched_at`` each, nothing
    left on 03-03 or 03-10; the last two not written, close and ``fetched_at`` as they were.

    Green on HEAD f21ce12d1, and must stay green: the guard refuses only a target before its row's day.
    """
    asset_id, _ = await z33_lane.asset(zone=None)
    await z33_lane.prices(asset_id, {"2025-03-03": 103, "2025-03-10": 110, "2025-03-17": 117, "2025-03-24": 124}, source=_Z33_REDATED)
    before = await _z33_prices(asset_id)

    outcome = await _z33_redate(asset_id, {"2025-03-03": "2025-03-04", "2025-03-10": "2025-03-11", "2025-03-17": None, "2025-03-24": "2025-03-24"})

    assert outcome == (2, 0), f"two rows moved, none dropped, nothing refused: (moved, dropped) {outcome!r}"
    prices = await _z33_prices(asset_id)
    assert {day: (close, source) for day, (close, source, _fetched_at) in prices.items()} == {
        "2025-03-04": (103, _Z33_REDATED),
        "2025-03-11": (110, _Z33_REDATED),
        "2025-03-17": (117, _Z33_REDATED),
        "2025-03-24": (124, _Z33_REDATED),
    }, "a row given a later day moves there, its close kept; a row given None or its own day stays"
    stale = {day: prices[day][2].isoformat() for day in ("2025-03-04", "2025-03-11") if not prices[day][2] > _Z33_OLD_STAMP}
    assert stale == {}, f"a moved row must get a fresh fetched_at, later than {_Z33_OLD_STAMP.isoformat()}: {stale}"
    stayed = ("2025-03-17", "2025-03-24")
    assert {day: prices[day] for day in stayed} == {day: before[day] for day in stayed}, "a row given None or its own day must not be written: close and fetched_at as they were"


# -- §4, MF: a target before its event's day is refused too ------------------------------------------------------------
#
# ``EventStoreOperations.redate_provider_events`` handles the assignment's events latest first as well, with the same
# blind spot: a target before its event's day can meet an event of the assignment and type not yet handled — an older
# twin —, and the moving event is merged into it by mistake: its transactions re-pointed there, then it is deleted; a
# SPLIT first carries its ADJUSTMENTs on its day back to that earlier day. As approved (Z-33 follow-up 2): every event's
# target is computed before anything changes; one before its event's day raises a ValueError naming the asset, the
# event's day and the target (days only, never a value), and nothing is written — no event moved, merged or deleted,
# no transaction re-pointed or re-dated, every ``updated_at`` as it was. None or the event's own day: the event stays;
# a later day: it moves, or merges into its twin there, as before.
#
# The helper is called directly (``_z33_redate_events``), no refresh, no provider call, on events of the mockprov
# assignment of an asset of the test's own, stamped ``_Z33_OLD_STAMP`` (``z33_lane``, which deletes them, and the
# transactions of its brokers). The four refusals are red on HEAD e20055213 for the refusal itself; the forward case is
# green there and must stay so.


async def _z33_event_rows(asset_id: int) -> dict[int, tuple[str, str, int | None, datetime]]:
    """``{event id: (day, type, provider_assignment_id, updated_at)}`` of the asset's events: ``_z33_events`` with the
    ``updated_at`` a move stamps, so "nothing written" covers it too. A deleted event is a missing id."""
    async with AsyncSession(get_async_engine()) as session:
        rows = (await session.execute(select(AssetEvent.id, AssetEvent.date, AssetEvent.type, AssetEvent.provider_assignment_id, AssetEvent.updated_at).where(AssetEvent.asset_id == asset_id))).all()
    return {event_id: (day.isoformat(), str(kind), assignment_id, updated_at) for event_id, day, kind, assignment_id, updated_at in rows}


async def _z33_redate_events(asset_id: int, assignment_id: int, targets: dict[str, str | None]) -> tuple[int, int] | ValueError:
    """``EventStoreOperations.redate_provider_events`` on the events of the assignment ``assignment_id``, in a session
    of its own, its ``target_of`` read from ``targets`` (``{event day: target day}``, whatever the type; None, or a day
    not given: the event stays): the (moved, merged) it returned, or the ValueError it raised. Committed either way, as
    ``_z33_redate``: the helper never commits — its transaction UPDATEs go out as it reaches them, its event moves and
    deletions at its flush —, and only a commit lets the fresh read that follows see what it did, a move, a merge or a
    re-pointed or re-dated transaction made before a refusal included, which a rollback would hide."""

    def target_of(day: date, _kind: str) -> date | None:
        target = targets.get(day.isoformat())
        return None if target is None else date.fromisoformat(target)

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        outcome: tuple[int, int] | ValueError
        try:
            outcome = await EventStoreOperations.redate_provider_events(session, asset_id, assignment_id, target_of)
        except ValueError as refused:
            outcome = refused
        await session.commit()
    return outcome


def _z33_event_refused(outcome: tuple[int, int] | ValueError, asset_id: int, *, stored: str, target: str) -> None:
    """``_z33_refused`` for an event: ``outcome`` is the refusal of the target ``target`` given to the event on
    ``stored``, a ValueError naming the asset and the two days in ISO form, the wording free."""
    _z33_refused(outcome, asset_id, stored=stored, target=target, subject="event", returned="(moved, merged)")


@pytest.mark.asyncio
async def test_z33_event_redate_refuses_a_backward_target_and_changes_nothing(z33_lane):
    """Z-33 (MF, the events): a target before its event's day is refused, though nothing stands on it. DIVIDENDs of the
    assignment on Monday 03-03 and Monday 03-10; the 03-03 one given Sunday 03-02, a free day, the 03-10 one None. The
    call raises a ValueError naming the asset, 03-03 and 03-02, and nothing is written: both DIVIDENDs on their day,
    ``updated_at`` as it was.

    Red on HEAD e20055213: the 03-03 DIVIDEND moves to 03-02, (1, 0) returned, no error.
    """
    asset_id, assignment_id = await z33_lane.asset(zone=None)
    await z33_lane.event(asset_id, "2025-03-03", AssetEventType.DIVIDEND, "0.5", assignment_id=assignment_id)
    await z33_lane.event(asset_id, "2025-03-10", AssetEventType.DIVIDEND, "0.5", assignment_id=assignment_id)
    before = await _z33_event_rows(asset_id)

    outcome = await _z33_redate_events(asset_id, assignment_id, {"2025-03-03": "2025-03-02", "2025-03-10": None})

    _z33_event_refused(outcome, asset_id, stored="2025-03-03", target="2025-03-02")
    assert await _z33_event_rows(asset_id) == before, "a refused re-date must write nothing: each event on its day, updated_at as it was"


@pytest.mark.asyncio
async def test_z33_event_redate_refuses_before_moving_a_forward_event(z33_lane):
    """Z-33 (MF, the events): every target is checked before any event moves. DIVIDENDs of the assignment on Monday
    03-03 and Monday 03-10; the 03-10 one given Tuesday 03-11 (later, free), the 03-03 one Sunday 03-02 (earlier).
    Latest first, the 03-10 DIVIDEND is reached before the 03-03 one: the call raises all the same, naming the asset,
    03-03 and 03-02, and the 03-10 DIVIDEND is still on 03-10, its ``updated_at`` as it was — ``_z33_redate_events``
    commits after the refusal, so a move made before it would show.

    Red on HEAD e20055213: both DIVIDENDs move, (2, 0) returned, no error.
    """
    asset_id, assignment_id = await z33_lane.asset(zone=None)
    await z33_lane.event(asset_id, "2025-03-03", AssetEventType.DIVIDEND, "0.5", assignment_id=assignment_id)
    latest = await z33_lane.event(asset_id, "2025-03-10", AssetEventType.DIVIDEND, "0.5", assignment_id=assignment_id)
    before = await _z33_event_rows(asset_id)

    outcome = await _z33_redate_events(asset_id, assignment_id, {"2025-03-03": "2025-03-02", "2025-03-10": "2025-03-11"})

    _z33_event_refused(outcome, asset_id, stored="2025-03-03", target="2025-03-02")
    after = await _z33_event_rows(asset_id)
    assert after.get(latest) == before[latest], f"the 03-10 DIVIDEND must not move before the refusal: still on 03-10, updated_at as it was: {after}"
    assert after == before, "a refused re-date must write nothing: each event on its day, updated_at as it was"


@pytest.mark.asyncio
async def test_z33_event_redate_backward_target_onto_an_unprocessed_twin_merges_nothing(z33_lane):
    """Z-33 (MF's case, the events): DIVIDENDs of the assignment on Monday 03-03 and Tuesday 03-04, the broker's
    DIVIDEND paid on Thursday 03-06 linked to the 03-04 one; the 03-04 DIVIDEND given 03-03 — an earlier day, where its
    twin stands, not yet reached —, the 03-03 one None. Latest first, the 03-04 DIVIDEND meets its twin on 03-03 and is
    merged into it: its transaction re-pointed there, then it is deleted. Refused instead, naming the asset, 03-04 and
    03-03: both DIVIDENDs stay, ``updated_at`` as it was, and the transaction is still linked to the 03-04 one, on its
    own day, its ``updated_at`` as it was.

    Red on HEAD e20055213: the 03-04 DIVIDEND is merged into the 03-03 one — its transaction re-pointed, the event
    deleted —, (0, 1) returned, no error.
    """
    asset_id, assignment_id = await z33_lane.asset(zone=None)
    await z33_lane.event(asset_id, "2025-03-03", AssetEventType.DIVIDEND, "0.5", assignment_id=assignment_id)
    later = await z33_lane.event(asset_id, "2025-03-04", AssetEventType.DIVIDEND, "0.5", assignment_id=assignment_id)
    cash = await z33_lane.transaction(await z33_lane.broker(), asset_id, TransactionType.DIVIDEND, "2025-03-06", amount="5", currency="EUR", event_id=later)
    events_before, cash_before = await _z33_event_rows(asset_id), await _z33_transactions([cash])

    outcome = await _z33_redate_events(asset_id, assignment_id, {"2025-03-03": None, "2025-03-04": "2025-03-03"})

    _z33_event_refused(outcome, asset_id, stored="2025-03-04", target="2025-03-03")
    assert await _z33_event_rows(asset_id) == events_before, "nothing may be merged: a refused re-date writes nothing, both DIVIDENDs on their day, updated_at as it was"
    assert await _z33_transactions([cash]) == cash_before, "the transaction must stay linked to the 03-04 DIVIDEND, on its own day, updated_at as it was"


@pytest.mark.asyncio
async def test_z33_event_redate_refuses_a_backward_split_and_its_adjustment_keeps_its_day(z33_lane):
    """Z-33 (MF, the events): a SPLIT takes along the ADJUSTMENTs linked to it on its day, before it moves itself — back
    in time too. The assignment's SPLIT on Tuesday 03-04, the ADJUSTMENT linked to it on 03-04; the SPLIT given Monday
    03-03, a free day. Refused, naming the asset, 03-04 and 03-03: the ADJUSTMENT still on 03-04, still linked, its
    ``updated_at`` as it was, and the SPLIT on 03-04, its ``updated_at`` as it was.

    Red on HEAD e20055213: the ADJUSTMENT is moved back to 03-03 (a fresh ``updated_at``), then the SPLIT, (1, 0)
    returned, no error.
    """
    asset_id, assignment_id = await z33_lane.asset(zone=None)
    split = await z33_lane.event(asset_id, "2025-03-04", AssetEventType.SPLIT, "2", assignment_id=assignment_id)
    adjustment = await z33_lane.transaction(await z33_lane.broker(), asset_id, TransactionType.ADJUSTMENT, "2025-03-04", quantity="10", event_id=split)
    events_before, adjustment_before = await _z33_event_rows(asset_id), await _z33_transactions([adjustment])

    outcome = await _z33_redate_events(asset_id, assignment_id, {"2025-03-04": "2025-03-03"})

    _z33_event_refused(outcome, asset_id, stored="2025-03-04", target="2025-03-03")
    assert await _z33_transactions([adjustment]) == adjustment_before, "the ADJUSTMENT must not move back: on 03-04, linked to the SPLIT, updated_at as it was"
    assert await _z33_event_rows(asset_id) == events_before, "the SPLIT must stay on 03-04, updated_at as it was"


@pytest.mark.asyncio
async def test_z33_event_redate_moves_forward_targets_as_before(z33_lane):
    """Z-33 (MF, the events, the guard's other side): a later day moves its event as before; None and the event's own
    day leave it. DIVIDENDs of the assignment on Mondays 03-03, 03-10, 03-17 and 03-24; the first two given the next
    day, the third None, the fourth its own day. (2, 0) returned: the first two on Tuesdays 03-04 and 03-11, in place
    (their ids kept), a fresh ``updated_at`` each; the last two not written, ``updated_at`` as it was.

    Green on HEAD e20055213, and must stay green: the guard refuses only a target before its event's day.
    """
    asset_id, assignment_id = await z33_lane.asset(zone=None)
    ids = {day: await z33_lane.event(asset_id, day, AssetEventType.DIVIDEND, "0.5", assignment_id=assignment_id) for day in ("2025-03-03", "2025-03-10", "2025-03-17", "2025-03-24")}
    before = await _z33_event_rows(asset_id)

    outcome = await _z33_redate_events(asset_id, assignment_id, {"2025-03-03": "2025-03-04", "2025-03-10": "2025-03-11", "2025-03-17": None, "2025-03-24": "2025-03-24"})

    assert outcome == (2, 0), f"two events moved, none merged, nothing refused: (moved, merged) {outcome!r}"
    events = await _z33_event_rows(asset_id)
    assert {event_id: row[:3] for event_id, row in events.items()} == {
        ids["2025-03-03"]: ("2025-03-04", "DIVIDEND", assignment_id),
        ids["2025-03-10"]: ("2025-03-11", "DIVIDEND", assignment_id),
        ids["2025-03-17"]: ("2025-03-17", "DIVIDEND", assignment_id),
        ids["2025-03-24"]: ("2025-03-24", "DIVIDEND", assignment_id),
    }, "an event given a later day moves there, in place; one given None or its own day stays"
    moved = (ids["2025-03-03"], ids["2025-03-10"])
    stale = {event_id: events[event_id][3].isoformat() for event_id in moved if not events[event_id][3] > _Z33_OLD_STAMP}
    assert stale == {}, f"a moved event must get a fresh updated_at, later than {_Z33_OLD_STAMP.isoformat()}: {stale}"
    stayed = (ids["2025-03-17"], ids["2025-03-24"])
    assert {event_id: events[event_id] for event_id in stayed} == {event_id: before[event_id] for event_id in stayed}, "an event given None or its own day must not be written: updated_at as it was"


# -- §4: the events ----------------------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_z33_an_event_moves_only_when_the_fresh_history_dates_it_on_the_next_day(z33_lane, monkeypatch):
    """Z-33 (D″ §4): four events of the assignment, the fresh history as calendar. The DIVIDEND of Wednesday 06-04 moves
    to Thursday 06-05: the fresh history has a DIVIDEND there and none on 06-04. These stay: the DIVIDEND of Monday
    06-09, the fresh history having one on 06-09 too (beside one on 06-10); the SPLIT of Wednesday 06-11, the fresh
    history having a DIVIDEND on 06-12 but no SPLIT; the DIVIDEND of Friday 06-13, the fresh history having nothing on
    06-14. No fresh event, all outside the asked range, is written.

    Red on HEAD: ``_z33_contract``.
    """
    _z33_open_gate(monkeypatch)
    asset_id, assignment_id = await z33_lane.asset(zone=_Z33_SENTINEL)
    moves = await z33_lane.event(asset_id, "2025-06-04", AssetEventType.DIVIDEND, "0.5", assignment_id=assignment_id)
    dated_on_its_day = await z33_lane.event(asset_id, "2025-06-09", AssetEventType.DIVIDEND, "0.5", assignment_id=assignment_id)
    another_type_next = await z33_lane.event(asset_id, "2025-06-11", AssetEventType.SPLIT, "2", assignment_id=assignment_id)
    nothing_next = await z33_lane.event(asset_id, "2025-06-13", AssetEventType.DIVIDEND, "0.5", assignment_id=assignment_id)
    fresh = tuple(_z33_point(day, "DIVIDEND") for day in ("2025-06-05", "2025-06-09", "2025-06-10", "2025-06-12"))
    provider = _Z33Provider(zone=_Z33_ROME, events=fresh)

    result = await _z33_refresh(asset_id, provider)

    _z33_went_through(result, provider, history_starts=["min"])
    assert await _z33_events(asset_id) == {
        moves: ("2025-06-05", "DIVIDEND", assignment_id),
        dated_on_its_day: ("2025-06-09", "DIVIDEND", assignment_id),
        another_type_next: ("2025-06-11", "SPLIT", assignment_id),
        nothing_next: ("2025-06-13", "DIVIDEND", assignment_id),
    }, "an event moves only when the fresh history has its type on the next day and not on its own"


@pytest.mark.asyncio
async def test_z33_a_split_moves_with_its_adjustment_on_the_old_day_and_yield_on_cost_accepts_it(z33_lane, monkeypatch):
    """Z-33 (D″ §4): a provider SPLIT stored on Wednesday 06-11, the fresh history dating it Thursday 06-12, moves there
    in place (its id kept), and the ADJUSTMENT linked to it, dated 06-11 like it, moves with it: still linked, both on
    06-12, so Yield on Cost still accepts the link (``transaction_date == event_date``), which moving the event alone
    would have broken.

    Red on HEAD: ``_z33_contract``.
    """
    _z33_open_gate(monkeypatch)
    asset_id, assignment_id = await z33_lane.asset(zone=_Z33_SENTINEL)
    split = await z33_lane.event(asset_id, "2025-06-11", AssetEventType.SPLIT, "2", assignment_id=assignment_id)
    adjustment = await z33_lane.transaction(await z33_lane.broker(), asset_id, TransactionType.ADJUSTMENT, "2025-06-11", quantity="10", event_id=split)
    provider = _Z33Provider(zone=_Z33_ROME, events=(_z33_point("2025-06-12", "SPLIT", "2"),))

    result = await _z33_refresh(asset_id, provider)

    _z33_went_through(result, provider, history_starts=["min"])
    assert await _z33_events(asset_id) == {split: ("2025-06-12", "SPLIT", assignment_id)}, "the SPLIT must move to its exchange day, in place"
    day, event_id, _updated_at = (await _z33_transactions([adjustment]))[adjustment]
    assert (day, event_id) == ("2025-06-12", split), "the ADJUSTMENT on the SPLIT's old day must move with it, still linked"
    assert await _z33_split_links([adjustment]) == {adjustment: ("2025-06-12", "2025-06-12", True)}, "Yield on Cost must accept the link"


@pytest.mark.asyncio
async def test_z33_a_moved_adjustment_gets_a_fresh_updated_at(z33_lane, monkeypatch):
    """Z-33 (D″ §4): the ADJUSTMENT a SPLIT takes along gets an ``updated_at`` later than the one it had: the portfolio
    cache keys on the transactions' ``updated_at`` (``compute_tx_fingerprint``), and a bulk UPDATE skips Transaction's
    ``before_update`` listener.

    Red on HEAD: ``_z33_contract``.
    """
    _z33_open_gate(monkeypatch)
    asset_id, assignment_id = await z33_lane.asset(zone=_Z33_SENTINEL)
    split = await z33_lane.event(asset_id, "2025-06-11", AssetEventType.SPLIT, "2", assignment_id=assignment_id)
    adjustment = await z33_lane.transaction(await z33_lane.broker(), asset_id, TransactionType.ADJUSTMENT, "2025-06-11", quantity="10", event_id=split)
    provider = _Z33Provider(zone=_Z33_ROME, events=(_z33_point("2025-06-12", "SPLIT", "2"),))

    result = await _z33_refresh(asset_id, provider)

    _z33_went_through(result, provider, history_starts=["min"])
    day, _event_id, updated_at = (await _z33_transactions([adjustment]))[adjustment]
    assert day == "2025-06-12", f"barrier: the ADJUSTMENT moved: {day}"
    assert updated_at > _Z33_OLD_STAMP, f"a moved ADJUSTMENT must get a fresh updated_at, later than {_Z33_OLD_STAMP.isoformat()}: {updated_at.isoformat()}"


@pytest.mark.asyncio
async def test_z33_a_split_joins_its_adjustment_already_on_the_exchange_day(z33_lane, monkeypatch):
    """Z-33 (D″ §4): the broker booked the split's ADJUSTMENT on Thursday 06-12, the exchange day; the provider SPLIT
    stored on 06-11, the fresh history dating it 06-12, moves there and joins it. The ADJUSTMENT is not touched — its
    day, link and ``updated_at`` as they were —, and Yield on Cost, which refused the link before, accepts it.

    Red on HEAD: ``_z33_contract``.
    """
    _z33_open_gate(monkeypatch)
    asset_id, assignment_id = await z33_lane.asset(zone=_Z33_SENTINEL)
    split = await z33_lane.event(asset_id, "2025-06-11", AssetEventType.SPLIT, "2", assignment_id=assignment_id)
    adjustment = await z33_lane.transaction(await z33_lane.broker(), asset_id, TransactionType.ADJUSTMENT, "2025-06-12", quantity="10", event_id=split)
    adjustment_before = await _z33_transactions([adjustment])
    assert (await _z33_split_links([adjustment]))[adjustment][2] is False, "barrier: before the move Yield on Cost refuses the link (06-12 against 06-11)"
    provider = _Z33Provider(zone=_Z33_ROME, events=(_z33_point("2025-06-12", "SPLIT", "2"),))

    result = await _z33_refresh(asset_id, provider)

    _z33_went_through(result, provider, history_starts=["min"])
    assert await _z33_events(asset_id) == {split: ("2025-06-12", "SPLIT", assignment_id)}, "the SPLIT must move to its exchange day, in place"
    assert await _z33_transactions([adjustment]) == adjustment_before, "an ADJUSTMENT already on the exchange day must not be touched"
    assert await _z33_split_links([adjustment]) == {adjustment: ("2025-06-12", "2025-06-12", True)}, "Yield on Cost must accept the link"


@pytest.mark.asyncio
async def test_z33_a_dividend_moves_and_its_transaction_keeps_its_date(z33_lane, monkeypatch):
    """Z-33 (D″ §4): a provider DIVIDEND stored on 06-11, the fresh history dating it 06-12, moves there in place; the
    broker's DIVIDEND linked to it, dated 06-11 — the event's old day —, keeps its day, its link and its ``updated_at``:
    a cash flow is dated by the broker, only the event's date changes.

    Red on HEAD: ``_z33_contract``.
    """
    _z33_open_gate(monkeypatch)
    asset_id, assignment_id = await z33_lane.asset(zone=_Z33_SENTINEL)
    dividend = await z33_lane.event(asset_id, "2025-06-11", AssetEventType.DIVIDEND, "0.5", assignment_id=assignment_id)
    cash = await z33_lane.transaction(await z33_lane.broker(), asset_id, TransactionType.DIVIDEND, "2025-06-11", amount="5", currency="EUR", event_id=dividend)
    cash_before = await _z33_transactions([cash])
    provider = _Z33Provider(zone=_Z33_ROME, events=(_z33_point("2025-06-12", "DIVIDEND"),))

    result = await _z33_refresh(asset_id, provider)

    _z33_went_through(result, provider, history_starts=["min"])
    assert await _z33_events(asset_id) == {dividend: ("2025-06-12", "DIVIDEND", assignment_id)}, "the DIVIDEND must move to its exchange day, in place"
    assert await _z33_transactions([cash]) == cash_before, "the DIVIDEND transaction must keep its day, link and updated_at"


@pytest.mark.asyncio
async def test_z33_no_other_transaction_moves(z33_lane, monkeypatch):
    """Z-33 (D″ §4): a transaction moves only when it is an ADJUSTMENT linked to the moved SPLIT and dated on that SPLIT's
    old day. The asset's provider SPLIT (06-11) and DIVIDEND (06-17) both move, the fresh history dating them 06-12 and
    06-18; its ADJUSTMENT linked to the SPLIT on 06-11 moves (the barrier: the check ran). Each of these keeps its day,
    link and ``updated_at``: an ADJUSTMENT on 06-11 linked to nothing; a BUY and a SELL on 06-11; another broker's
    ADJUSTMENT linked to the SPLIT but dated 06-14; the DIVIDEND linked to the moved DIVIDEND, on its old day; and, on
    another asset not refreshed (also marked), an ADJUSTMENT linked to its own SPLIT on 06-11 and a BUY on 06-11 — that
    SPLIT staying too.

    Red on HEAD: ``_z33_contract``.
    """
    _z33_open_gate(monkeypatch)
    asset_id, assignment_id = await z33_lane.asset(zone=_Z33_SENTINEL)
    other_id, other_assignment = await z33_lane.asset(zone=_Z33_SENTINEL)
    first, second = await z33_lane.broker(), await z33_lane.broker()
    split = await z33_lane.event(asset_id, "2025-06-11", AssetEventType.SPLIT, "2", assignment_id=assignment_id)
    dividend = await z33_lane.event(asset_id, "2025-06-17", AssetEventType.DIVIDEND, "0.5", assignment_id=assignment_id)
    other_split = await z33_lane.event(other_id, "2025-06-11", AssetEventType.SPLIT, "3", assignment_id=other_assignment)
    moved = await z33_lane.transaction(first, asset_id, TransactionType.ADJUSTMENT, "2025-06-11", quantity="10", event_id=split)
    kept = {
        "an ADJUSTMENT on the old day, linked to nothing": await z33_lane.transaction(first, asset_id, TransactionType.ADJUSTMENT, "2025-06-11", quantity="1"),
        "a BUY on the old day": await z33_lane.transaction(first, asset_id, TransactionType.BUY, "2025-06-11", quantity="3", amount="-300", currency="EUR"),
        "a SELL on the old day": await z33_lane.transaction(first, asset_id, TransactionType.SELL, "2025-06-11", quantity="-1", amount="100", currency="EUR"),
        "an ADJUSTMENT linked to the SPLIT on another day": await z33_lane.transaction(second, asset_id, TransactionType.ADJUSTMENT, "2025-06-14", quantity="4", event_id=split),
        "the DIVIDEND linked to the moved DIVIDEND": await z33_lane.transaction(first, asset_id, TransactionType.DIVIDEND, "2025-06-17", amount="5", currency="EUR", event_id=dividend),
        "another asset's ADJUSTMENT linked to its SPLIT": await z33_lane.transaction(first, other_id, TransactionType.ADJUSTMENT, "2025-06-11", quantity="7", event_id=other_split),
        "another asset's BUY on the day": await z33_lane.transaction(first, other_id, TransactionType.BUY, "2025-06-11", quantity="2", amount="-100", currency="EUR"),
    }
    before = await _z33_transactions(list(kept.values()))
    other_events_before = await _z33_events(other_id)
    provider = _Z33Provider(zone=_Z33_ROME, events=(_z33_point("2025-06-12", "SPLIT", "2"), _z33_point("2025-06-18", "DIVIDEND")))

    result = await _z33_refresh(asset_id, provider)

    _z33_went_through(result, provider, history_starts=["min"])
    assert (await _z33_transactions([moved]))[moved][:2] == ("2025-06-12", split), "barrier: the ADJUSTMENT of the moved SPLIT moved, so the check ran"
    assert {event_id: row[0] for event_id, row in (await _z33_events(asset_id)).items()} == {split: "2025-06-12", dividend: "2025-06-18"}, "barrier: both events moved"
    after = await _z33_transactions(list(kept.values()))
    touched = {name: (before[transaction_id], after[transaction_id]) for name, transaction_id in kept.items() if after[transaction_id] != before[transaction_id]}
    assert touched == {}, f"no other transaction may move or be written: {touched}"
    assert await _z33_events(other_id) == other_events_before, "the events of an asset not refreshed must not move"


@pytest.mark.asyncio
async def test_z33_a_shifted_event_meeting_its_twin_merges_into_it_with_its_transactions(z33_lane, monkeypatch):
    """Z-33 (D″ §4, the merge as accepted): the assignment holds a SPLIT and a DIVIDEND on Wednesday 06-11, stored by the
    old rule, and their twins — the same assignment and types — on Thursday 06-12; the fresh history dates both types on
    06-12 and none on 06-11. Each shifted event moves to 06-12, meets its twin and merges into it: its transactions
    re-pointed to the twin, then it is deleted. The ADJUSTMENT linked to the shifted SPLIT, on 06-11, is re-pointed and
    moves to 06-12; the twin's own ADJUSTMENT (another broker, on 06-12) is not touched; the DIVIDEND linked to the
    shifted DIVIDEND, paid 06-13, is re-pointed and keeps its day. Yield on Cost accepts both ADJUSTMENTs.

    Red on HEAD: ``_z33_contract``.
    """
    _z33_open_gate(monkeypatch)
    asset_id, assignment_id = await z33_lane.asset(zone=_Z33_SENTINEL)
    shifted_split = await z33_lane.event(asset_id, "2025-06-11", AssetEventType.SPLIT, "2", assignment_id=assignment_id)
    twin_split = await z33_lane.event(asset_id, "2025-06-12", AssetEventType.SPLIT, "2", assignment_id=assignment_id)
    shifted_dividend = await z33_lane.event(asset_id, "2025-06-11", AssetEventType.DIVIDEND, "0.3", assignment_id=assignment_id)
    twin_dividend = await z33_lane.event(asset_id, "2025-06-12", AssetEventType.DIVIDEND, "0.3", assignment_id=assignment_id)
    first, second = await z33_lane.broker(), await z33_lane.broker()
    moved = await z33_lane.transaction(first, asset_id, TransactionType.ADJUSTMENT, "2025-06-11", quantity="10", event_id=shifted_split)
    twins_own = await z33_lane.transaction(second, asset_id, TransactionType.ADJUSTMENT, "2025-06-12", quantity="6", event_id=twin_split)
    cash = await z33_lane.transaction(first, asset_id, TransactionType.DIVIDEND, "2025-06-13", amount="3", currency="EUR", event_id=shifted_dividend)
    twins_own_before = await _z33_transactions([twins_own])
    provider = _Z33Provider(zone=_Z33_ROME, events=(_z33_point("2025-06-12", "SPLIT", "2"), _z33_point("2025-06-12", "DIVIDEND", "0.3")))

    result = await _z33_refresh(asset_id, provider)

    _z33_went_through(result, provider, history_starts=["min"])
    assert await _z33_events(asset_id) == {twin_split: ("2025-06-12", "SPLIT", assignment_id), twin_dividend: ("2025-06-12", "DIVIDEND", assignment_id)}, "each shifted event must merge into its twin, then be gone"
    transactions = await _z33_transactions([moved, cash])
    assert {transaction_id: row[:2] for transaction_id, row in transactions.items()} == {
        moved: ("2025-06-12", twin_split),
        cash: ("2025-06-13", twin_dividend),
    }, "the shifted events' transactions must be re-pointed to the twins; the ADJUSTMENT on the old day moves, the DIVIDEND keeps its day"
    assert await _z33_transactions([twins_own]) == twins_own_before, "the twin's own ADJUSTMENT must not be touched"
    assert await _z33_split_links([moved, twins_own]) == {moved: ("2025-06-12", "2025-06-12", True), twins_own: ("2025-06-12", "2025-06-12", True)}, "Yield on Cost must accept both"


@pytest.mark.asyncio
async def test_z33_the_fresh_events_leave_no_duplicate_beside_the_moved_one(z33_lane, monkeypatch):
    """Z-33 (D″ §2, §4), the reason of the check: a provider DIVIDEND stored by the old rule on Monday 06-23, inside the
    asked range, its broker DIVIDEND paid on 06-25; the fresh history dates it Tuesday 06-24, at 0.55. The check moves it
    to 06-24 first, then the fresh upsert finds it there and updates it in place: one DIVIDEND, its id kept, its value
    the fresh one, its transaction still linked on its own day. A plain fix of the plugin would have added a second
    DIVIDEND on 06-24 beside the one on 06-23.

    Red on HEAD: ``_z33_contract``.
    """
    _z33_open_gate(monkeypatch)
    asset_id, assignment_id = await z33_lane.asset(zone=_Z33_SENTINEL)
    stored = await z33_lane.event(asset_id, "2025-06-23", AssetEventType.DIVIDEND, "0.5", assignment_id=assignment_id)
    cash = await z33_lane.transaction(await z33_lane.broker(), asset_id, TransactionType.DIVIDEND, "2025-06-25", amount="5", currency="EUR", event_id=stored)
    provider = _Z33Provider(zone=_Z33_ROME, events=(_z33_point("2025-06-24", "DIVIDEND", "0.55"),))

    result = await _z33_refresh(asset_id, provider)

    _z33_went_through(result, provider, history_starts=["min"])
    assert await _z33_events(asset_id) == {stored: ("2025-06-24", "DIVIDEND", assignment_id)}, "one DIVIDEND on its exchange day: the stored one, moved, then updated in place"
    async with AsyncSession(get_async_engine()) as session:
        value = (await session.execute(select(AssetEvent.value).where(AssetEvent.id == stored))).scalar_one()
    assert value == Decimal("0.55"), f"the fresh upsert must have updated the moved DIVIDEND: {value}"
    assert (await _z33_transactions([cash]))[cash][:2] == ("2025-06-25", stored), "its transaction must stay linked, on its own day"


# -- §6, §9: a check without a fresh history; a refresh of today only ---------------------------------------------------


@pytest.mark.parametrize(
    ("failure", "today_only"),
    [
        pytest.param("fails", False, id="the-history-call-fails"),
        pytest.param("empty", False, id="the-history-has-no-price"),
        pytest.param("no-timezone", False, id="the-history-reports-no-timezone"),
        pytest.param("fails", True, id="the-history-call-fails-on-a-refresh-of-today"),
    ],
)
@pytest.mark.asyncio
async def test_z33_a_marked_assignment_without_a_fresh_history_or_timezone_writes_nothing(z33_lane, monkeypatch, failure, today_only):
    """Z-33 (D″ §6): the check's full-history call fails, answers no price, or reports no timezone (on a refresh of
    today only too, its current value at hand): nothing is written for the asset — its closes with their ``fetched_at``,
    its DIVIDEND and the transaction linked to it, no fresh close or event, no current value, not ``last_fetch_at``
    (a later check must read the same D_f) —, the result fails saying why, and the mark stays.

    Red on HEAD: ``_z33_contract``.
    """
    _z33_open_gate(monkeypatch)
    asset_id, assignment_id = await z33_lane.asset(zone=_Z33_SENTINEL)
    await z33_lane.prices(asset_id, {"2025-06-01": 101, "2025-06-02": 102})
    dividend = await z33_lane.event(asset_id, "2025-06-11", AssetEventType.DIVIDEND, "0.5", assignment_id=assignment_id)
    cash = await z33_lane.transaction(await z33_lane.broker(), asset_id, TransactionType.DIVIDEND, "2025-06-11", amount="5", currency="EUR", event_id=dividend)
    before = (await _z33_prices(asset_id), await _z33_events(asset_id), await _z33_transactions([cash]), await _z33_last_fetch(asset_id))
    provider = _Z33Provider(
        zone=None if failure == "no-timezone" else _Z33_ROME,
        events=(_z33_point("2025-06-12", "DIVIDEND"), _z33_point("2025-06-24", "DIVIDEND", "0.6"), _z33_point("2025-06-26", "DIVIDEND", "0.6")),
        fail=failure == "fails",
        empty=failure == "empty",
        current=(_Z33_TODAY, Decimal("126.5")),
        current_zone=_Z33_ROME,
    )
    start, end = (_Z33_TODAY, _Z33_TODAY) if today_only else (_Z33_START, _Z33_END)

    result = await _z33_refresh(asset_id, provider, start=start, end=end)

    assert [start for _identifier, start, _end in provider.history_calls] == ["min"], f"barrier: the check asked the full history, once: {provider.history_calls}"
    assert (result.status, result.points_changed, bool(result.errors)) == (SyncStatus.FAILED, 0, True), f"the result must fail, change nothing and say why: {result}"
    after = (await _z33_prices(asset_id), await _z33_events(asset_id), await _z33_transactions([cash]), await _z33_last_fetch(asset_id))
    assert after == before, "nothing may be written for the asset, last_fetch_at included"
    assert await _z33_zone(asset_id) == _Z33_SENTINEL, "the mark must stay until a fresh history and its timezone are known"


@pytest.mark.asyncio
async def test_z33_a_failing_check_fails_its_asset_alone(z33_lane, monkeypatch):
    """Z-33 (docs review of D″): the one-time check meets a database error — ``PriceStoreOperations.redate_provider_rows``
    raises ``RuntimeError("disk I/O error")`` — in a bulk refresh of two assets on the same provider, one marked (the gate
    open), one plain. The error stays with its asset: the call returns; the marked asset's result is FAILED and says the
    timezone check failed; nothing is written for it — its closes with their ``fetched_at``, its DIVIDEND, its
    ``last_fetch_at`` and ``reported_currency``, no fresh close or event — and its mark stays; the plain asset's result
    is OK, its fresh closes written.

    The message is read loosely: some text of the result, its message or one of its errors, says «timezone» and «fail»
    (case ignored); the words around them are free.

    Red with Z-33 as applied: ``_settle_exchange_timezone`` runs before the ``try`` of ``_persist_refresh_item``, and
    ``_persist_refresh_items`` gathers without ``return_exceptions``: the error escapes and fails the whole
    ``bulk_refresh_prices`` call, the plain asset's result with it.
    """
    _z33_open_gate(monkeypatch)
    marked_identifier, plain_identifier = f"Z33-{uuid.uuid4().hex[:12]}", f"Z33-{uuid.uuid4().hex[:12]}"
    marked, assignment_id = await z33_lane.asset(zone=_Z33_SENTINEL, identifier=marked_identifier)
    plain, _ = await z33_lane.asset(zone=None, identifier=plain_identifier)
    await z33_lane.prices(marked, {"2025-06-01": 101, "2025-06-02": 102})
    await z33_lane.event(marked, "2025-06-11", AssetEventType.DIVIDEND, "0.5", assignment_id=assignment_id)

    async def marked_state() -> tuple:
        async with AsyncSession(get_async_engine()) as session:
            reported = (await session.execute(select(AssetProviderAssignment.reported_currency).where(AssetProviderAssignment.asset_id == marked))).scalar_one()
        return await _z33_prices(marked), await _z33_events(marked), await _z33_last_fetch(marked), reported, await _z33_zone(marked)

    before = await marked_state()
    redated: list[int] = []

    async def broken_redate(session, asset_id, source_plugin_key, target_of):
        redated.append(asset_id)
        raise RuntimeError("disk I/O error")

    monkeypatch.setattr(PriceStoreOperations, "redate_provider_rows", staticmethod(broken_redate))
    provider = _Z33Provider(zone=_Z33_ROME, events=(_z33_point("2025-06-12", "DIVIDEND"), _z33_point("2025-06-24", "DIVIDEND")))
    items = [FARefreshItem(asset_id=asset_id, date_range=SyncDateRangeModel(start=_Z33_START, end=_Z33_END)) for asset_id in (marked, plain)]

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        with provider.answering(), _z33_today(_Z33_TODAY):
            try:
                response = await AssetSourceManager.bulk_refresh_prices(items, session)
            except Exception as escaped:  # the finding: one asset's error must not fail the call
                # The other asset's persist is still running: let it end before the test does, so the teardown deletes what it writes
                await asyncio.gather(*(task for task in asyncio.all_tasks() if getattr(task.get_coro(), "__qualname__", "") == "_persist_refresh_item"), return_exceptions=True)
                pytest.fail(f"the check's error escaped bulk_refresh_prices and failed the whole call, the plain asset's result with it: {escaped!r}", pytrace=False)

    assert redated == [marked], f"barrier: the check reached the re-date of the marked asset alone, which raised: {redated}"
    results = {result.asset_id: result for result in response.results}
    assert set(results) == {marked, plain}, f"one result per asset: {response.results}"
    failed = results[marked]
    assert (failed.status, failed.points_changed, bool(failed.errors)) == (SyncStatus.FAILED, 0, True), f"the marked asset must fail, change nothing and say why: {failed}"
    texts = [text for text in (failed.message, *failed.errors) if text]
    assert any("timezone" in text.lower() and "fail" in text.lower() for text in texts), f"the marked asset's result must say the timezone check failed: {texts}"
    assert await marked_state() == before, "nothing may be written for the marked asset, and its mark must stay"
    ok = results[plain]
    assert (ok.status, ok.errors) == (SyncStatus.OK, []), f"the plain asset must refresh as always: {ok}"
    assert await _z33_closes(plain) == _Z33_FRESH, "the plain asset's fresh closes must be written"


@pytest.mark.asyncio
async def test_z33_a_current_value_refresh_checks_against_the_full_history_then_writes_today(z33_lane, monkeypatch):
    """Z-33 (D″ §9): a refresh of today only (Wednesday 07-16) on a marked assignment last fetched on Tuesday 07-15 at noon
    UTC. Stored by the old rule: Thursday's, Friday's and Monday's closes on Wednesday 07-09, Thursday 07-10 and Sunday
    07-13; Tuesday's current value on Tuesday 07-15 (right). The refresh still fetches the full history, once, as
    calendar: the three closes move to Thursday 07-10, Friday 07-11 and Monday 07-14, their values kept; Tuesday stays
    (after D_f − 2). Of the history nothing is written: only today's current value, on its local day, 07-16. Refreshed
    the next day, the mark cleared: no history call, nothing moves, Thursday 07-17 gets its value.

    Red on HEAD: ``_z33_contract``.
    """
    _z33_open_gate(monkeypatch)
    asset_id, _ = await z33_lane.asset(zone=_Z33_SENTINEL, last_fetch=datetime(2025, 7, 15, 12, 0))
    await z33_lane.prices(asset_id, {"2025-07-09": 110, "2025-07-10": 111, "2025-07-13": 114, "2025-07-15": Decimal("115.5")})
    wednesday, thursday = date(2025, 7, 16), date(2025, 7, 17)
    provider = _Z33Provider(zone=_Z33_ROME, current=(wednesday, Decimal("116.5")), current_zone=_Z33_ROME)

    result = await _z33_refresh(asset_id, provider, start=wednesday, end=wednesday, today=wednesday)

    _z33_went_through(result, provider, history_starts=["min"])
    checked = {"2025-07-10": 110, "2025-07-11": 111, "2025-07-14": 114, "2025-07-15": Decimal("115.5"), "2025-07-16": Decimal("116.5")}
    assert await _z33_closes(asset_id) == checked, "the old closes move by the calendar; of the history nothing is written; today's value on its own day"
    assert await _z33_zone(asset_id) == _Z33_ROME, "the check must clear the mark"

    for identifier in z33_lane.identifiers:
        await core.drop_asset_cache_entries("mockprov", identifier, ProviderInputType.TICKER, None)
    provider.current = (thursday, Decimal("117.5"))
    result = await _z33_refresh(asset_id, provider, start=thursday, end=thursday, today=thursday)

    _z33_went_through(result, provider, history_starts=["min"])  # no further history call
    assert await _z33_closes(asset_id) == checked | {"2025-07-17": Decimal("117.5")}, "a later refresh must move nothing"


# -- §7: unchanged -----------------------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_z33_a_second_refresh_fetches_no_full_history_and_moves_nothing(z33_lane, monkeypatch):
    """Z-33 (D″ §7): after the check the assignment holds ``Europe/Rome``; a second refresh (the cache dropped between,
    as a later day finds it) asks the history over the asked range only, no full history, and moves nothing: the June
    closes with their ``fetched_at``, the SPLIT and its ADJUSTMENT with its ``updated_at``, as the check left them; the
    timezone stays.

    Red on HEAD: ``_z33_contract``.
    """
    _z33_open_gate(monkeypatch)
    asset_id, assignment_id = await z33_lane.asset(zone=_Z33_SENTINEL)
    await z33_lane.prices(asset_id, {"2025-06-01": 101, "2025-06-02": 102})
    split = await z33_lane.event(asset_id, "2025-06-11", AssetEventType.SPLIT, "2", assignment_id=assignment_id)
    adjustment = await z33_lane.transaction(await z33_lane.broker(), asset_id, TransactionType.ADJUSTMENT, "2025-06-11", quantity="10", event_id=split)
    provider = _Z33Provider(zone=_Z33_ROME, events=(_z33_point("2025-06-12", "SPLIT", "2"),))

    async def state() -> tuple:
        return _z33_without(await _z33_prices(asset_id), _Z33_FRESH), await _z33_events(asset_id), await _z33_transactions([adjustment]), await _z33_zone(asset_id)

    _z33_went_through(await _z33_refresh(asset_id, provider), provider, history_starts=["min"])
    first = await state()
    observed = ({day: row[0] for day, row in first[0].items()}, first[1][split][0], first[3])
    assert observed == ({"2025-06-02": 101, "2025-06-03": 102}, "2025-06-12", _Z33_ROME), f"barrier: the check moved the closes and the SPLIT and cleared the mark: {observed}"
    for identifier in z33_lane.identifiers:
        await core.drop_asset_cache_entries("mockprov", identifier, ProviderInputType.TICKER, None)

    _z33_went_through(await _z33_refresh(asset_id, provider), provider, history_starts=["min", _Z33_START])

    assert await state() == first, "a second refresh must move nothing and keep the timezone"


@pytest.mark.asyncio
async def test_z33_an_assignment_without_a_timezone_learns_it_and_moves_nothing(z33_lane, monkeypatch):
    """Z-33 (D″ §7): an assignment holding NULL — its rows dated by the new rule —, the gate open for its provider, whose
    history reports ``Europe/Rome``: one history call over the asked range, no full history; the timezone is stored; its
    closes (with their ``fetched_at``), its DIVIDEND and the transaction linked to it stay as they were, though the
    fresh history dates a DIVIDEND on the next day.

    Red on HEAD: ``_z33_contract``.
    """
    _z33_open_gate(monkeypatch)
    asset_id, assignment_id = await z33_lane.asset(zone=None)
    await z33_lane.prices(asset_id, {"2025-06-02": 102, "2025-06-03": 103})
    dividend = await z33_lane.event(asset_id, "2025-06-11", AssetEventType.DIVIDEND, "0.5", assignment_id=assignment_id)
    cash = await z33_lane.transaction(await z33_lane.broker(), asset_id, TransactionType.DIVIDEND, "2025-06-11", amount="5", currency="EUR", event_id=dividend)
    before = (await _z33_prices(asset_id), await _z33_events(asset_id), await _z33_transactions([cash]))
    provider = _Z33Provider(zone=_Z33_ROME, events=(_z33_point("2025-06-12", "DIVIDEND"),))

    result = await _z33_refresh(asset_id, provider)

    _z33_went_through(result, provider, history_starts=[_Z33_START])
    assert await _z33_zone(asset_id) == _Z33_ROME, "a NULL assignment must learn the timezone"
    after = (_z33_without(await _z33_prices(asset_id), _Z33_FRESH), await _z33_events(asset_id), await _z33_transactions([cash]))
    assert after == before, "nothing may move"


@pytest.mark.parametrize(
    ("stored", "reported", "held"),
    [
        pytest.param(_Z33_LONDON, _Z33_ROME, _Z33_ROME, id="another-zone-replaces-it"),
        pytest.param(_Z33_ROME, _Z33_ROME, _Z33_ROME, id="the-same-zone"),
        pytest.param(_Z33_ROME, None, _Z33_ROME, id="none-reported-keeps-it"),
    ],
)
@pytest.mark.asyncio
async def test_z33_a_known_timezone_follows_the_provider_and_nothing_moves(z33_lane, monkeypatch, stored, reported, held):
    """Z-33 (D″ §7): an assignment holding a timezone, the gate open for its provider: one history call over the asked
    range, no full history; the reported timezone replaces the stored one when it differs, a history reporting none
    leaves it; nothing moves: the closes with their ``fetched_at`` and the DIVIDEND as they were.

    Red on HEAD: ``_z33_contract``.
    """
    _z33_open_gate(monkeypatch)
    asset_id, assignment_id = await z33_lane.asset(zone=stored)
    await z33_lane.prices(asset_id, {"2025-06-02": 102, "2025-06-03": 103})
    await z33_lane.event(asset_id, "2025-06-11", AssetEventType.DIVIDEND, "0.5", assignment_id=assignment_id)
    stored_before, events_before = await _z33_prices(asset_id), await _z33_events(asset_id)
    provider = _Z33Provider(zone=reported, events=(_z33_point("2025-06-12", "DIVIDEND"),))

    result = await _z33_refresh(asset_id, provider)

    _z33_went_through(result, provider, history_starts=[_Z33_START])
    assert await _z33_zone(asset_id) == held, f"stored {stored!r}, reported {reported!r}: the assignment must hold {held!r}"
    assert (_z33_without(await _z33_prices(asset_id), _Z33_FRESH), await _z33_events(asset_id)) == (stored_before, events_before), "nothing may move"


@pytest.mark.asyncio
async def test_z33_a_history_served_from_the_cache_carries_its_timezone(z33_lane, monkeypatch):
    """Z-33 (N86 §5, unchanged by D″): two assets assigned alike (one cache key), both NULL. The first fetches the
    history, which reports ``Europe/Rome``; the second, refreshed over the same range, is served whole from the core
    history cache — the provider is not asked again — and learns ``Europe/Rome`` from the cache entry.

    Red on HEAD: ``_z33_contract``.
    """
    _z33_open_gate(monkeypatch)
    first, _ = await z33_lane.asset(zone=None)
    (identifier,) = z33_lane.identifiers
    second, _ = await z33_lane.asset(zone=None, identifier=identifier)
    provider = _Z33Provider(zone=_Z33_ROME)
    _z33_went_through(await _z33_refresh(first, provider), provider, history_starts=[_Z33_START])
    assert await _z33_zone(first) == _Z33_ROME, "precondition: the fetch left Europe/Rome on the first assignment"

    result = await _z33_refresh(second, provider)

    _z33_went_through(result, provider, history_starts=[_Z33_START])  # still one call: the second history came from the cache
    assert await _z33_zone(second) == _Z33_ROME, "a history served from the cache must carry the timezone it was fetched with"


@pytest.mark.parametrize(
    ("history_zone", "current_zone", "held"),
    [
        pytest.param(_Z33_LONDON, _Z33_ROME, _Z33_LONDON, id="the-history-wins"),
        pytest.param(None, _Z33_ROME, _Z33_ROME, id="else-the-current-value"),
    ],
)
@pytest.mark.asyncio
async def test_z33_the_timezone_comes_from_the_history_else_from_the_current_value(z33_lane, monkeypatch, history_zone, current_zone, held):
    """Z-33 (N86 §5, unchanged by D″): a refresh up to today (history and current value both asked) on a NULL assignment
    keeps the history's timezone, and the current value's when the history reports none.

    Red on HEAD: ``_z33_contract``.
    """
    _z33_open_gate(monkeypatch)
    asset_id, _ = await z33_lane.asset(zone=None)
    today = date(2025, 7, 16)
    provider = _Z33Provider(zone=history_zone, current=(today, Decimal("116.5")), current_zone=current_zone)

    result = await _z33_refresh(asset_id, provider, start=today - timedelta(days=2), end=today, today=today)

    _z33_went_through(result, provider, history_starts=[today - timedelta(days=2)])
    assert len(provider.current_calls) == 1, f"barrier: the current value was asked: {provider.current_calls}"
    assert await _z33_zone(asset_id) == held


# -- §10, H's review: two refreshes of one asset -----------------------------------------------------------------------
#
# Nothing serializes two refreshes of one asset — the manual sync (``api/v1/assets/prices.py``, ``sync_prices_bulk``)
# and the scheduler's (``services/platform/scheduler/jobs.py``) —, and each reads the mark when it is prepared, before
# its fetch: one that settles and commits while the other is still fetching leaves the other a stale
# ``prep.legacy_check``. Reviewer H (MEDIUM, Z-33 follow-up 3): the other then runs the check again on rows already on
# their day, and the price rule has no «already right» guard — for Milan every row S with a session on S + 1 and
# S ≤ D_f − 2 moves forward one day again, its value shifting; a Thursday moved onto Friday meets Friday's row and is
# dropped. Events are safe: their target needs the fresh history to have the event on S + 1 and none on S.
#
# As approved: the settle step runs the check only when the row it reads afresh still holds the mark; then, D_f
# computed (``_server_date``) and before anything moves, it claims the mark with a conditional UPDATE
# (``… WHERE id = … AND exchange_timezone = 'legacy-utc'``). When that matches no row, another refresh settled in
# between: it rolls back and moves nothing, and the refresh writes what it fetched as any refresh does — not FAILED. A
# fresh row holding a timezone is left as before.
#
# The refreshes here run in their phases, as ``bulk_refresh_prices`` runs them: prepared from the state stored at the
# time (``_z33_prepared``), fetched and persisted later (``_z33_run_prepared``), so another refresh's commit comes in
# between — a whole refresh, or the commit of its settle step alone, made at the moment the settle step of the refresh
# under test computes D_f (``_z33_another_refresh_settles_first``). Both tests are red on HEAD e20055213. That a single
# refresh still settles as before is pinned by the §3 and §4 tests above
# (``test_z33_a_legacy_series_moves_to_its_exchange_days_latest_first`` first), and the refresh after it by
# ``test_z33_a_second_refresh_fetches_no_full_history_and_moves_nothing``.


async def _z33_prepared(asset_id: int, *, start: date = _Z33_START, end: date = _Z33_END) -> refresh._PreparedRefreshItem:
    """The refresh of the asset from ``start`` to ``end`` as ``bulk_refresh_prices`` prepares it from the state stored
    now (``_prepare_refresh_items``): its prep, for ``_z33_run_prepared`` to fetch and persist later."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        prepared, immediate = await refresh._prepare_refresh_items([FARefreshItem(asset_id=asset_id, date_range=SyncDateRangeModel(start=start, end=end))], session, time.monotonic_ns())
    assert (immediate, list(prepared)) == ([], [asset_id]), f"setup: the refresh of asset {asset_id} must be prepared, not answered at once: {immediate}"
    return prepared[asset_id]


async def _z33_run_prepared(asset_id: int, prep: refresh._PreparedRefreshItem, provider: _Z33Provider, *, today: date = _Z33_TODAY) -> FARefreshResult:
    """The rest of a refresh prepared earlier, as ``bulk_refresh_prices`` runs it: the fetch (``_fetch_refresh_item``),
    then the persist (``_persist_refresh_item``, the fetch's error handed on), ``provider`` answering, ``today`` frozen."""
    with provider.answering(), _z33_today(today):
        data, error, _refusal = await refresh._fetch_refresh_item(asset_id, prep, asyncio.Semaphore(1), 60)
        return await refresh._persist_refresh_item(asset_id, prep, data, error, get_async_engine())


def _z33_another_refresh_settles_first(monkeypatch, assignment_id: int, zone: str) -> list[int | str]:
    """``refresh._server_date`` wrapped: the first time it is called — in the settle step of the refresh under test,
    after it read the assignment, before it claims the mark or moves anything — another refresh's settle step commits
    first: the assignment's ``exchange_timezone`` set to ``zone``, which clears the mark, its rows left where they are
    (what the other moves is its own; the point is that this one moves none). Then the real ``_server_date`` answers.
    Returned: one entry per such commit, the rows its UPDATE matched (1: it landed), or the error it met — reported by
    the test's barrier, never raised into the refresh under test.

    The commit goes through a connection of the sync engine (``get_sync_engine``, the same database): the wrapper runs
    inside a sync function, on the event loop, where no async session can be awaited. The refresh under test holds no
    lock there — pysqlite opens its transaction at its first write, which comes after —, so the commit waits on nothing
    of this process. A claim made before ``_server_date`` would hold the write lock: the commit would wait for it until
    the busy timeout, then fail, and the barrier would say so."""
    column = _z33_contract()
    real_server_date = refresh._server_date
    commits: list[int | str] = []

    def server_date_after_another_settled(moment: datetime | None) -> date | None:
        if not commits:
            try:
                with get_sync_engine().begin() as connection:
                    commits.append(connection.execute(update(AssetProviderAssignment).where(AssetProviderAssignment.id == assignment_id).values({column: zone})).rowcount)
            except Exception as error:  # reported by the test's barrier, not raised into the refresh under test
                commits.append(repr(error))
        return real_server_date(moment)

    monkeypatch.setattr(refresh, "_server_date", server_date_after_another_settled)
    return commits


def _z33_moved(before: dict[str, tuple], after: dict[str, tuple]) -> dict[str, tuple]:
    """``{day: (close before, close after)}`` of the days whose row changed — moved, dropped, or rewritten (the same
    close then: another ``fetched_at``) —, None where there is no row: for a failure message."""
    return {day: (before[day][0] if day in before else None, after[day][0] if day in after else None) for day in sorted(before.keys() | after.keys()) if before.get(day) != after.get(day)}


@pytest.mark.asyncio
async def test_z33_a_second_refresh_with_a_stale_mark_moves_nothing(z33_lane, monkeypatch):
    """Z-33 (H's review, MEDIUM): a marked Milan line — closes stored by the old rule on Sunday 06-01 to Thursday 06-05,
    the assignment's DIVIDEND on Wednesday 06-11, the last fetch on Monday 06-16 —, two refreshes prepared from that
    state, both ``legacy_check`` set and their last fetch 06-16. The first, fetched and persisted, settles: the closes
    move to Monday 06-02 to Friday 06-06, the DIVIDEND to Thursday 06-12 (the fresh history dates it there), the mark
    gives way to ``Europe/Rome``. The second then fetches and persists with its stale prep: the row it reads holds the
    timezone, so it moves and drops nothing — every row outside the asked range on its day, its close and ``fetched_at``
    as the first left them; the DIVIDEND on 06-12, its ``updated_at`` as well —, the timezone stays, and it writes what
    it fetched as any refresh does: OK.

    Red on HEAD e20055213: the second persist runs the check again on rows already on their day. Latest first: Friday's
    close, 105, stays (Saturday is no session); Thursday's, 104, moves onto Friday, meets 105 there and is dropped;
    Monday's to Wednesday's, 101 to 103, move to Tuesday to Thursday. The DIVIDEND stays: the fresh history has it on
    06-12, the day it now holds.
    """
    _z33_open_gate(monkeypatch)
    asset_id, assignment_id = await z33_lane.asset(zone=_Z33_SENTINEL)
    await z33_lane.prices(asset_id, {"2025-06-01": 101, "2025-06-02": 102, "2025-06-03": 103, "2025-06-04": 104, "2025-06-05": 105})
    dividend = await z33_lane.event(asset_id, "2025-06-11", AssetEventType.DIVIDEND, "0.5", assignment_id=assignment_id)
    provider = _Z33Provider(zone=_Z33_ROME, events=(_z33_point("2025-06-12", "DIVIDEND"),))
    first_prep, second_prep = await _z33_prepared(asset_id), await _z33_prepared(asset_id)
    preps = [(prep.legacy_check, prep.last_fetch_at) for prep in (first_prep, second_prep)]
    assert preps == [(True, _Z33_LAST_FETCH)] * 2, f"barrier: both refreshes prepared while the mark is there, their last fetch Monday 06-16: {preps}"

    _z33_went_through(await _z33_run_prepared(asset_id, first_prep, provider), provider, history_starts=["min"])
    settled, settled_events = await _z33_prices(asset_id), await _z33_event_rows(asset_id)
    observed = ({day: row[0] for day, row in _z33_without(settled, _Z33_FRESH).items()}, settled_events[dividend][0], await _z33_zone(asset_id))
    expected = ({"2025-06-02": 101, "2025-06-03": 102, "2025-06-04": 103, "2025-06-05": 104, "2025-06-06": 105}, "2025-06-12", _Z33_ROME)
    assert observed == expected, f"barrier: the first refresh settled — the closes and the DIVIDEND on their exchange days, the mark cleared: {observed}"

    second = await _z33_run_prepared(asset_id, second_prep, provider)

    moved = _z33_moved(_z33_without(settled, _Z33_FRESH), _z33_without(await _z33_prices(asset_id), _Z33_FRESH))
    assert moved == {}, f"a refresh prepared before another settled must move and drop nothing: every row outside the asked range on its day, close and fetched_at as the first refresh left them; {{day: (close before, close after)}} {moved}"
    assert await _z33_event_rows(asset_id) == settled_events, "no event may move: the DIVIDEND on 06-12, updated_at as the first refresh left it"
    assert await _z33_zone(asset_id) == _Z33_ROME, "the timezone must stay"
    _z33_went_through(second, provider, history_starts=["min", "min"])  # not FAILED: it writes what it fetched


@pytest.mark.asyncio
async def test_z33_a_refresh_that_read_the_mark_before_another_settled_moves_nothing(z33_lane, monkeypatch):
    """Z-33 (H's review, MEDIUM, the overlap the claim closes): the same marked Milan line, one refresh prepared while the
    mark is there, its full history fetched; its settle step reads the assignment: still marked. Between that read and
    anything it moves, another refresh's settle step commits from a connection of its own: ``Europe/Rome`` stored, the
    mark cleared, the rows left where they are (``_z33_another_refresh_settles_first``, at the settle step's
    ``_server_date``). The refresh under test must then move and drop nothing — the closes on 06-01 to 06-05 and the
    DIVIDEND on 06-11 as they were just before its persist, ``fetched_at`` and ``updated_at`` included —; the timezone
    is ``Europe/Rome``, and it writes what it fetched as any refresh does: OK, the fresh closes of the asked range
    stored.

    Red on HEAD e20055213: the settle step trusts the prep and re-dates — the closes to Monday 06-02 to Friday 06-06,
    the DIVIDEND to Thursday 06-12. Still red with the fresh read alone: the row it read held the mark; only a claim
    made at the write sees the other's commit.
    """
    _z33_open_gate(monkeypatch)
    asset_id, assignment_id = await z33_lane.asset(zone=_Z33_SENTINEL)
    await z33_lane.prices(asset_id, {"2025-06-01": 101, "2025-06-02": 102, "2025-06-03": 103, "2025-06-04": 104, "2025-06-05": 105})
    await z33_lane.event(asset_id, "2025-06-11", AssetEventType.DIVIDEND, "0.5", assignment_id=assignment_id)
    provider = _Z33Provider(zone=_Z33_ROME, events=(_z33_point("2025-06-12", "DIVIDEND"),))
    prep = await _z33_prepared(asset_id)
    assert (prep.legacy_check, prep.last_fetch_at) == (True, _Z33_LAST_FETCH), f"barrier: the refresh is prepared while the mark is there, its last fetch Monday 06-16: {prep}"
    before, events_before = await _z33_prices(asset_id), await _z33_event_rows(asset_id)
    commits = _z33_another_refresh_settles_first(monkeypatch, assignment_id, _Z33_ROME)

    result = await _z33_run_prepared(asset_id, prep, provider)

    assert commits == [1], f"barrier: the other refresh's settle must commit once, inside the settle step of this one, at its _server_date: {commits}"
    prices = await _z33_prices(asset_id)
    moved = _z33_moved(_z33_without(before, _Z33_FRESH), _z33_without(prices, _Z33_FRESH))
    assert moved == {}, f"a refresh that read the mark before another settled must move and drop nothing: every row outside the asked range on its day, close and fetched_at as they were; {{day: (close before, close after)}} {moved}"
    assert await _z33_event_rows(asset_id) == events_before, "no event may move: the DIVIDEND on 06-11, updated_at as it was"
    assert await _z33_zone(asset_id) == _Z33_ROME, "the timezone the other refresh stored must stay"
    _z33_went_through(result, provider, history_starts=["min"])  # not FAILED: it writes what it fetched
    assert {day: prices[day][0] for day in _Z33_FRESH if day in prices} == _Z33_FRESH, "it writes what it fetched as any refresh does: the fresh closes of the asked range"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

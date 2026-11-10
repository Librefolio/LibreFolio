from datetime import date, timedelta

import pytest

from backend.test_scripts.test_db_config import initialize_test_database, setup_test_database

setup_test_database()

import asyncio
import time
import uuid
from decimal import Decimal
from unittest.mock import patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, AssetType, PriceHistory, ProviderInputType
from backend.app.db.session import get_async_engine
from backend.app.schemas.assets.events import FAAssetEventPoint
from backend.app.schemas.common import Currency, DateRangeModel
from backend.app.schemas.prices import FACurrentValue, FAHistoricalData, FAPricePoint
from backend.app.schemas.provider import FAProviderAssignmentItem
from backend.app.schemas.refresh import FARefreshItem, SyncDateRangeModel, SyncStatus
from backend.app.services.asset_source_providers.mockprov.plugin import MockProvider
from backend.app.services.assets import core, refresh
from backend.app.services.assets.base import AssetHistoryStartDate
from backend.app.services.assets.manager import AssetSourceManager
from backend.app.services.assets.registry import AssetProviderRegistry


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


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

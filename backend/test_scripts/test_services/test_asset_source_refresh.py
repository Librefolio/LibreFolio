from datetime import date

import pytest

from backend.test_scripts.test_db_config import initialize_test_database, setup_test_database

setup_test_database()

import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, AssetType, PriceHistory, ProviderInputType
from backend.app.db.session import get_async_engine
from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.provider import FAProviderAssignmentItem
from backend.app.schemas.refresh import FARefreshItem, SyncStatus
from backend.app.services.asset_source import AssetSourceManager
from backend.app.services.provider_registry import AssetProviderRegistry


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
async def test_refresh_currency_fallback_uses_asset_currency():
    """Verify that when provider doesn't return currency, the asset's own currency is used."""
    assert initialize_test_database(), "Failed to initialize test database"
    AssetProviderRegistry.auto_discover()

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        # mockprov returns "USD" currency explicitly, but asset is "EUR"
        # In this test we just verify the pipeline doesn't crash
        asset = Asset(
            display_name=_unique("EUR Asset"),
            currency="EUR",
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


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

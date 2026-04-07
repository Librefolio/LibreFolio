"""
Test that asset sync reports accurate points_changed counts.

Verifies that re-syncing the same data does NOT inflate points_changed.
The root cause was _count_actual_price_changes comparing raw provider values
with DB-truncated values, causing every price to appear "changed".
"""
from datetime import date
import time

import pytest

from backend.test_scripts.test_db_config import setup_test_database, initialize_test_database

setup_test_database()

from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_async_engine
from backend.app.services.asset_source import AssetSourceManager
from backend.app.db.models import Asset, AssetType, ProviderInputType
from backend.app.services.provider_registry import AssetProviderRegistry
from backend.app.schemas.provider import FAProviderAssignmentItem
from backend.app.schemas.refresh import FARefreshItem, SyncStatus
from backend.app.schemas.common import DateRangeModel


def _unique(prefix: str) -> str:
    return f"{prefix}_{int(time.time() * 1000)}"


async def _create_asset_with_provider(
    session: AsyncSession, name: str, provider_code: str = "mockprov", identifier: str = "MOCK"
) -> int:
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
async def test_second_sync_reports_zero_changes():
    """
    After syncing identical data twice, the second sync should report
    points_changed == 0 (no new inserts, no value changes).
    """
    assert initialize_test_database(), "Failed to initialize test database"
    AssetProviderRegistry.auto_discover()

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        asset_id = await _create_asset_with_provider(session, _unique("SyncCountTest"))

        payload = [
            FARefreshItem(
                asset_id=asset_id,
                date_range=DateRangeModel(start=date(2025, 1, 1), end=date(2025, 3, 31)),
            )
        ]

        # First sync — should fetch and insert data
        result1 = await AssetSourceManager.bulk_refresh_prices(payload, session)
        r1 = next((r for r in result1.results if r.asset_id == asset_id), None)
        assert r1 is not None, "First sync result missing"
        assert r1.points_fetched > 0, "First sync should fetch some points"
        assert r1.points_changed > 0, "First sync should report changes (new inserts)"

        # Second sync — same data, should report zero changes
        result2 = await AssetSourceManager.bulk_refresh_prices(payload, session)
        r2 = next((r for r in result2.results if r.asset_id == asset_id), None)
        assert r2 is not None, "Second sync result missing"
        assert r2.points_fetched > 0, "Second sync should still fetch points"
        assert r2.points_changed == 0, (
            f"Second sync should report 0 changes, got {r2.points_changed} "
            f"(inserted={r2.inserted_count}, updated={r2.updated_count})"
        )


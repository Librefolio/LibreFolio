from datetime import date

import pytest

from backend.test_scripts.test_db_config import setup_test_database, initialize_test_database

setup_test_database()

from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_async_engine
from backend.app.services.asset_source import AssetSourceManager
from backend.app.db.models import Asset, AssetType
from backend.app.services.provider_registry import AssetProviderRegistry
from backend.app.schemas.provider import FAProviderAssignmentItem
from backend.app.schemas.refresh import FARefreshItem


@pytest.mark.asyncio
async def test_bulk_refresh_prices_orchestration():
    """Smoke test for bulk_refresh_prices orchestration using a mocked provider assignment."""
    # Initialize database with safety checks
    assert initialize_test_database(), "Failed to initialize test database"

    # Ensure providers discovered (in case modules were created after import)
    AssetProviderRegistry.auto_discover()

    import time
    timestamp = int(time.time() * 1000)

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        # Create an asset and assign a fake provider code (we expect provider registry to have a stub or error)
        asset = Asset(
            display_name=f"Refresh Test Asset {timestamp}",
            currency="USD",
            asset_type=AssetType.STOCK,
            active=True,
            )
        session.add(asset)
        await session.commit()
        await session.refresh(asset)

        # Assign a mock provider that returns deterministic prices
        from backend.app.db.models import IdentifierType
        await AssetSourceManager.bulk_assign_providers([
            FAProviderAssignmentItem(
                asset_id=asset.id,
                provider_code="mockprov",
                identifier="REFRESH_TEST",
                identifier_type=IdentifierType.UUID,
                provider_params={},
                fetch_interval=1440  # Optional but added for completeness
            )
            ], session)

        # Execute refresh - expect prices to be inserted
        from backend.app.schemas.common import DateRangeModel
        payload = [FARefreshItem(asset_id=asset.id, date_range=DateRangeModel(start=date(2025, 1, 1), end=date(2025, 1, 3)))]
        results = await AssetSourceManager.bulk_refresh_prices(payload, session)

        # Verify results
        assert results is not None
        assert len(results.results) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

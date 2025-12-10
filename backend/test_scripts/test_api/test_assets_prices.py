"""
Test Suite: Asset Prices API Endpoints

Tests for price-related endpoints:
- POST /api/v1/assets/prices - Bulk upsert prices
- DELETE /api/v1/assets/prices - Bulk delete prices
- GET /api/v1/assets/prices/{asset_id} - Get price history
- POST /api/v1/assets/prices/refresh - Refresh prices from providers
"""

import pytest
import httpx
from datetime import date, timedelta
from decimal import Decimal

from backend.app.config import get_settings
# Import Pydantic schemas
from backend.app.schemas.assets import (
    FAAssetCreateItem,
    FABulkAssetCreateResponse,
    AssetType
)
from backend.app.schemas.prices import (
    FAPricePoint,
    FAUpsert,
    FABulkUpsertResponse,
    FABulkDeleteResponse
)
from backend.app.schemas.provider import (
    FAProviderAssignmentItem,
    FABulkProviderAssignmentResponse,
    IdentifierType
)
from backend.app.schemas.refresh import (
    FABulkRefreshResponse,
    FARefreshItem
)

# Test server fixture
from backend.test_scripts.test_server_helper import _TestingServerManager

# Constants
settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0

def unique_id(prefix: str = "TEST") -> str:
    """Generate unique ID for test data."""
    import time
    return f"{prefix}_{int(time.time() * 1000)}_{id(prefix) % 100}"

def print_section(title: str):
    """Print test section header."""
    print(f"\n{'=' * 60}\n  {title}\n{'=' * 60}")

def print_info(msg: str):
    """Print info message."""
    print(f"ℹ️  {msg}")

def print_success(msg: str):
    """Print success message."""
    print(f"✅ ✓ {msg}")


# Fixture: test server
@pytest.fixture(scope="module")
def test_server():
    """Start/stop test server for all tests in this module."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager
        # Server automatically stopped by context manager


# ============================================================
# Test 1: POST /assets/prices - Bulk upsert prices
# ============================================================
@pytest.mark.asyncio
async def test_bulk_upsert_prices(test_server):
    """Test 1: POST /assets/prices - Bulk upsert prices."""
    print_section("Test 1: POST /assets/prices - Bulk upsert")

    async with httpx.AsyncClient() as client:
        # Step 1: Create test asset
        create_item = FAAssetCreateItem(
            display_name=f"Price Upsert Test {unique_id('PRICE1')}",
            currency="USD"
        )
        create_resp = await client.post(
            f"{API_BASE}/assets",
            json=[create_item.model_dump(mode="json")],
            timeout=TIMEOUT
        )
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id
        print_info(f"  Created asset ID: {asset_id}")

        # Step 2: Upsert prices (3 days)
        today = date.today()
        prices = [
            FAPricePoint(
                date=today - timedelta(days=2),
                close=Decimal("100.50"),
                volume=Decimal("1000"),
                currency="USD"
            ),
            FAPricePoint(
                date=today - timedelta(days=1),
                close=Decimal("101.25"),
                volume=Decimal("1500"),
                currency="USD"
            ),
            FAPricePoint(
                date=today,
                close=Decimal("102.00"),
                volume=Decimal("2000"),
                currency="USD"
            )
        ]

        # Usa FAUpsert che raggruppa i prezzi per asset
        upsert_data = FAUpsert(
            asset_id=asset_id,
            prices=prices
        )

        upsert_resp = await client.post(
            f"{API_BASE}/assets/prices",
            json=[upsert_data.model_dump(mode="json")],
            timeout=TIMEOUT
        )
        assert upsert_resp.status_code == 200, f"Upsert failed: {upsert_resp.status_code}: {upsert_resp.text}"

        upsert_result = FABulkUpsertResponse(**upsert_resp.json())
        assert upsert_result.success_count >= 1
        print_success(f"✓ Upserted 3 prices successfully")

        # Step 3: Verify prices in DB via GET endpoint
        get_resp = await client.get(f"{API_BASE}/assets/prices/{asset_id}", timeout=TIMEOUT)
        assert get_resp.status_code == 200

        price_history = [FAPricePoint(**p) for p in get_resp.json()]
        assert len(price_history) == 3
        assert price_history[0].close == Decimal("102.00")  # Most recent first
        print_success("✓ Price history verified via GET")


# ============================================================
# Test 2: GET /assets/prices/{asset_id} - Get price history
# ============================================================
@pytest.mark.asyncio
async def test_get_price_history(test_server):
    """Test 2: GET /assets/prices/{asset_id} - Get price history."""
    print_section("Test 2: GET /assets/prices/{asset_id}")

    async with httpx.AsyncClient() as client:
        # Step 1: Create asset
        create_item = FAAssetCreateItem(
            display_name=f"Price Get Test {unique_id('PRICEGET')}",
            currency="USD"
        )
        create_resp = await client.post(
            f"{API_BASE}/assets",
            json=[create_item.model_dump(mode="json")],
            timeout=TIMEOUT
        )
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id
        print_info(f"  Created asset ID: {asset_id}")

        # Step 2: Insert prices for date range
        prices = [
            FAPriceUpsertItem(date=date(2025, 1, 1), close=Decimal("100.00"), currency="USD"),
            FAPriceUpsertItem(date=date(2025, 1, 3), close=Decimal("103.00"), currency="USD"),  # Gap on 1/2
            FAPriceUpsertItem(date=date(2025, 1, 5), close=Decimal("105.00"), currency="USD"),  # Gap on 1/4
        ]
        upsert_request = FABulkUpsertRequest(prices={asset_id: prices})
        await client.post(
            f"{API_BASE}/assets/prices",
            json=upsert_request.model_dump(mode="json"),
            timeout=TIMEOUT
        )
        print_info("  Prices inserted with gaps")

        # Step 3: GET prices with date range (should include backward-fill)
        get_resp = await client.get(
            f"{API_BASE}/assets/prices/{asset_id}",
            params={"start_date": "2025-01-01", "end_date": "2025-01-05"},
            timeout=TIMEOUT
        )
        assert get_resp.status_code == 200

        price_history = [FAPricePoint(**p) for p in get_resp.json()]
        assert len(price_history) == 5, "Should return 5 days (including backward-filled)"

        # Verify backward-fill: 2025-01-02 should use 2025-01-01's price
        jan2 = next(p for p in price_history if p.date == date(2025, 1, 2))
        assert jan2.close == Decimal("100.00"), "Jan 2 should use Jan 1's price (backward-fill)"
        assert jan2.days_back == 1, "Jan 2 should have days_back=1"
        print_success("✓ Backward-fill working correctly")


# ============================================================
# Test 3: DELETE /assets/prices - Bulk delete prices
# ============================================================
@pytest.mark.asyncio
async def test_bulk_delete_prices(test_server):
    """Test 3: DELETE /assets/prices - Bulk delete prices."""
    print_section("Test 3: DELETE /assets/prices - Bulk delete")

    async with httpx.AsyncClient() as client:
        # Step 1: Create asset and insert prices
        create_item = FAAssetCreateItem(
            display_name=f"Price Delete Test {unique_id('PRICEDEL')}",
            currency="USD"
        )
        create_resp = await client.post(
            f"{API_BASE}/assets",
            json=[create_item.model_dump(mode="json")],
            timeout=TIMEOUT
        )
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id
        print_info(f"  Created asset ID: {asset_id}")

        # Insert prices for Jan 1-10
        prices = [
            FAPriceUpsertItem(date=date(2025, 1, d), close=Decimal(f"100.{d:02d}"), currency="USD")
            for d in range(1, 11)
        ]
        upsert_request = FABulkUpsertRequest(prices={asset_id: prices})
        await client.post(
            f"{API_BASE}/assets/prices",
            json=upsert_request.model_dump(mode="json"),
            timeout=TIMEOUT
        )
        print_info("  Inserted 10 prices (Jan 1-10)")

        # Step 2: DELETE range Jan 3-7 (5 days)
        delete_request = FABulkDeleteRequest(
            deletions=[
                FADeleteItem(
                    asset_id=asset_id,
                    date_ranges=[FADateRange(start=date(2025, 1, 3), end=date(2025, 1, 7))]
                )
            ]
        )
        delete_resp = await client.request(
            "DELETE",
            f"{API_BASE}/assets/prices",
            json=delete_request.model_dump(mode="json"),
            timeout=TIMEOUT
        )
        assert delete_resp.status_code == 200

        delete_data = FABulkDeleteResponse(**delete_resp.json())
        assert delete_data.success_count == 1
        print_success("✓ Deleted range Jan 3-7")

        # Step 3: Verify only Jan 1-2 and Jan 8-10 remain
        get_resp = await client.get(f"{API_BASE}/assets/prices/{asset_id}", timeout=TIMEOUT)
        remaining_prices = [FAPricePoint(**p) for p in get_resp.json()]
        remaining_dates = [p.date for p in remaining_prices]

        expected_dates = [date(2025, 1, 1), date(2025, 1, 2), date(2025, 1, 8), date(2025, 1, 9), date(2025, 1, 10)]
        assert set(remaining_dates) == set(expected_dates), f"Expected {expected_dates}, got {remaining_dates}"
        print_success("✓ Only Jan 1-2 and Jan 8-10 remain (deleted range verified)")


# ============================================================
# Test 4: POST /assets/prices/refresh - Refresh from provider
# ============================================================
@pytest.mark.asyncio
async def test_refresh_prices_from_provider(test_server):
    """Test 4: POST /assets/prices/refresh - Refresh from provider."""
    print_section("Test 4: POST /assets/prices/refresh")

    async with httpx.AsyncClient() as client:
        # Step 1: Create asset and assign mockprov
        create_item = FAAssetCreateItem(
            display_name=f"Price Refresh Test {unique_id('PRICEREF')}",
            currency="USD"
        )
        create_resp = await client.post(
            f"{API_BASE}/assets",
            json=[create_item.model_dump(mode="json")],
            timeout=TIMEOUT
        )
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id
        print_info(f"  Created asset ID: {asset_id}")

        # Assign mockprov
        assignment = FAProviderAssignmentItem(
            asset_id=asset_id,
            provider_code="mockprov",
            identifier="MOCK_REFRESH",
            identifier_type=IdentifierType.UUID,
            provider_params={"symbol": "MOCKREFRESH"}
        )
        await client.post(
            f"{API_BASE}/assets/provider",
            json=[assignment.model_dump(mode="json")],
            timeout=TIMEOUT
        )
        print_info("  Provider mockprov assigned")

        # Step 2: Refresh prices from provider
        refresh_request = FABulkRefreshRequest(
            items=[
                FARefreshItem(
                    asset_id=asset_id,
                    date_range=FADateRange(start=date(2025, 1, 1), end=date(2025, 1, 5))
                )
            ]
        )
        refresh_resp = await client.post(
            f"{API_BASE}/assets/prices/refresh",
            json=refresh_request.model_dump(mode="json"),
            timeout=TIMEOUT
        )
        assert refresh_resp.status_code == 200, f"Refresh failed: {refresh_resp.status_code}: {refresh_resp.text}"

        refresh_data = FABulkRefreshResponse(**refresh_resp.json())
        assert refresh_data.success_count == 1
        print_success("✓ Prices refreshed from mockprov")

        # Step 3: Verify prices were created
        get_resp = await client.get(f"{API_BASE}/assets/prices/{asset_id}", timeout=TIMEOUT)
        price_history = [FAPricePoint(**p) for p in get_resp.json()]
        assert len(price_history) >= 1, "Should have at least 1 price from provider"
        print_success(f"✓ Prices verified: {len(price_history)} prices in DB")


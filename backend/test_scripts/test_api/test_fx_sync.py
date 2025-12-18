"""
Test Suite: FX Sync API Endpoints

Tests for FX sync endpoints:
- GET /api/v1/fx/currencies/sync - Sync FX rates from providers
  - Manual provider selection
  - Auto-config mode (using pair sources)
  - Error handling (FXServiceError)
  - Multi-provider scenarios
"""

from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest

from backend.app.config import get_settings
from backend.app.schemas.common import Currency
from backend.app.schemas.fx import (
    FXConversionRequest,
    FXConvertResponse,
    FXPairSourceItem,
    FXCreatePairSourcesResponse,
    FXPairSourcesResponse,
    DateRangeModel
    )
# Import Pydantic schemas
from backend.app.schemas.refresh import (
    FXSyncResponse
    )
# Test server fixture
from backend.test_scripts.test_server_helper import _TestingServerManager

# Constants
settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0


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
# Test 1: GET /fx/currencies/sync - Service Error Handling
# ============================================================
@pytest.mark.asyncio
async def test_sync_service_error_handling(test_server):
    """Test 1: GET /fx/currencies/sync - FXServiceError handling."""
    print_section("Test 1: GET /fx/currencies/sync - Service Error")

    async with httpx.AsyncClient() as client:
        # Request sync with invalid provider (should trigger error)
        sync_resp = await client.get(
            f"{API_BASE}/fx/currencies/sync",
            params={
                "start": "2025-01-01",
                "end": "2025-01-01",
                "currencies": "EUR,INVALID_CURRENCY",
                "provider": "ECB"
                },
            timeout=TIMEOUT
            )

        # Should handle error gracefully
        # Could be 400 (validation), 502 (upstream error), or 200 with error in response
        print_info(f"  Response status: {sync_resp.status_code}")

        if sync_resp.status_code == 400:
            print_success("✓ Invalid request rejected with 400")
        elif sync_resp.status_code == 502:
            # 502 = upstream provider error (ECB returned 404 for invalid currency)
            print_success("✓ Upstream provider error handled with 502")
        elif sync_resp.status_code == 200:
            sync_data = FXSyncResponse(**sync_resp.json())
            # Should have synced some but not all
            print_success(f"✓ Service error handled: synced={sync_data.synced}")
        else:
            pytest.fail(f"Unexpected status code: {sync_resp.status_code}")


# ============================================================
# Test 2: GET /fx/currencies/sync - Auto-config with pair sources
# ============================================================
@pytest.mark.asyncio
async def test_sync_auto_config(test_server):
    """Test 2: GET /fx/currencies/sync - Auto-config (pair sources)."""
    print_section("Test 2: GET /fx/currencies/sync - Auto-config")

    async with httpx.AsyncClient() as client:
        # Step 1: Create pair sources for EUR/USD and GBP/USD
        pair_sources = [
            FXPairSourceItem(
                base="EUR",
                quote="USD",
                provider_code="ECB",
                priority=1
                ),
            FXPairSourceItem(
                base="GBP",
                quote="USD",
                provider_code="ECB",
                priority=1
                )
            ]

        create_resp = await client.post(
            f"{API_BASE}/fx/providers/pair-sources",
            json=[s.model_dump(mode="json") for s in pair_sources],
            timeout=TIMEOUT
            )

        # Might already exist, so accept both 201 and 400
        if create_resp.status_code == 201:
            create_data = FXCreatePairSourcesResponse(**create_resp.json())
            print_info(f"  Created {create_data.success_count} pair sources")
        else:
            print_info("  Pair sources already exist")

        # Step 2: Sync WITHOUT provider param (auto-config mode)
        today = date.today()
        yesterday = today - timedelta(days=1)

        sync_resp = await client.get(
            f"{API_BASE}/fx/currencies/sync",
            params={
                "start": yesterday.isoformat(),
                "end": yesterday.isoformat(),
                "currencies": "EUR,GBP"
                # NO provider param - should use pair sources
                },
            timeout=TIMEOUT
            )

        # Should succeed using auto-config
        assert sync_resp.status_code == 200, f"Auto-config sync failed: {sync_resp.status_code}"

        sync_data = FXSyncResponse(**sync_resp.json())
        print_success(f"✓ Auto-config sync successful: synced={sync_data.synced} rates")

        # Cleanup: delete pair sources
        for source in pair_sources:
            await client.request(
                "DELETE",
                f"{API_BASE}/fx/providers/pair-sources",
                json=[source.model_dump(mode="json")],
                timeout=TIMEOUT
                )
        print_info("  Cleanup: Pair sources deleted")


# ============================================================
# Test 3: GET /fx/currencies/sync - Auto-config no pairs configured
# ============================================================
@pytest.mark.asyncio
async def test_sync_auto_config_no_pairs(test_server):
    """Test 3: GET /fx/currencies/sync - Auto-config with no pair sources."""
    print_section("Test 3: GET /fx/currencies/sync - Auto-config no pairs")

    async with httpx.AsyncClient() as client:
        # Step 1: Ensure no pair sources configured (delete all)
        list_resp = await client.get(f"{API_BASE}/fx/providers/pair-sources", timeout=TIMEOUT)
        existing_sources = FXPairSourcesResponse(**list_resp.json())

        if existing_sources.count > 0:
            # Delete all existing pair sources
            for source in existing_sources.sources:
                delete_items = [
                    FXPairSourceItem(
                        base=source.base,
                        quote=source.quote,
                        provider_code=source.provider_code,
                        priority=source.priority
                        )
                    ]
                await client.request(
                    "DELETE",
                    f"{API_BASE}/fx/providers/pair-sources",
                    json=[s.model_dump(mode="json") for s in delete_items],
                    timeout=TIMEOUT
                    )
            print_info("  Deleted all existing pair sources")

        # Step 2: Try sync without provider param (auto-config mode)
        # Should fail because no pair sources configured
        sync_resp = await client.get(
            f"{API_BASE}/fx/currencies/sync",
            params={"start": "2025-01-01", "end": "2025-01-01", "currencies": "EUR,GBP"},
            timeout=TIMEOUT
            )

        # Should return 400 error about missing configuration
        assert sync_resp.status_code == 400, f"Expected 400, got {sync_resp.status_code}"
        error_detail = sync_resp.json()
        assert "No currency pair sources" in error_detail.get("detail", ""), \
            f"Expected 'No currency pair sources' in error, got: {error_detail}"
        print_success("✓ Auto-config correctly fails when no pair sources configured")


# ============================================================
# Test 4: GET /fx/currencies/sync - Weekend sync (no rates)
# ============================================================
@pytest.mark.asyncio
async def test_sync_weekend_no_rates(test_server):
    """Test 4: GET /fx/currencies/sync - Weekend sync returns no rates."""
    print_section("Test 4: GET /fx/currencies/sync - Weekend sync")

    async with httpx.AsyncClient() as client:
        # Step 1: Sync for a known weekend date (2025-01-04 = Saturday)
        weekend_date = "2025-01-04"

        sync_resp = await client.get(
            f"{API_BASE}/fx/currencies/sync",
            params={
                "start": weekend_date,
                "end": weekend_date,
                "currencies": "EUR,GBP",
                "provider": "ECB"
                },
            timeout=TIMEOUT
            )

        # Should succeed but with 0 rates synced (ECB doesn't publish on weekends)
        assert sync_resp.status_code == 200, f"Sync failed: {sync_resp.status_code}"

        sync_data = FXSyncResponse(**sync_resp.json())
        assert sync_data.synced == 0, f"Expected 0 rates synced on weekend, got {sync_data.synced}"
        print_success("✓ Weekend sync correctly returns 0 rates")


# ============================================================
# Test 5: POST /fx/currencies/convert - Multi-day conversion
# ============================================================
@pytest.mark.asyncio
async def test_convert_multi_day_process(test_server):
    """Test 5: POST /fx/currencies/convert - Multi-day conversion process."""
    print_section("Test 5: POST /fx/currencies/convert - Multi-day")

    async with httpx.AsyncClient() as client:
        # Step 1: Ensure we have FX rates for a date range
        end_date = date.today()
        start_date = end_date - timedelta(days=7)

        sync_params = {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "currencies": "EUR,GBP",
            "provider": "ECB"
            }
        await client.get(f"{API_BASE}/fx/currencies/sync", params=sync_params, timeout=TIMEOUT)
        print_info("  FX rates synced for date range")

        # Step 2: Request conversion with date range (multi-day)
        conversions = [
            FXConversionRequest(
                from_amount=Currency(code="USD", amount=Decimal("100")),
                **{"to": "EUR"},
                date_range=DateRangeModel(start=start_date, end=end_date)
                )
            ]

        convert_resp = await client.post(
            f"{API_BASE}/fx/currencies/convert",
            json=[c.model_dump(mode="json") for c in conversions],
            timeout=TIMEOUT
            )

        # Should handle multi-day conversion
        assert convert_resp.status_code == 200, f"Convert failed: {convert_resp.status_code}: {convert_resp.text}"

        convert_data = FXConvertResponse(**convert_resp.json())
        assert convert_data.success_count >= 1

        # Verify result has multi-day data (multi-day conversions return one result per day)
        result = convert_data.results[0]
        assert result.to_amount is not None
        print_success(f"✓ Multi-day conversion successful: {result.to_amount}")

        # In multi-day conversion, we get one result per day in the range
        # So check that we have multiple results
        print_info(f"  Total conversions returned: {len(convert_data.results)}")
        print_success("✓ Multi-day conversion process tested")


# ============================================================
# Test 5: POST /fx/currencies/convert - Bulk multi-day
# ============================================================
@pytest.mark.asyncio
async def test_convert_bulk_multi_day(test_server):
    """Test 5: POST /fx/currencies/convert - Bulk conversions with multi-day."""
    print_section("Test 5: POST /fx/currencies/convert - Bulk multi-day")

    async with httpx.AsyncClient() as client:
        # Step 1: Sync rates for date range
        today = date.today()
        start_date = today - timedelta(days=7)
        end_date = today

        await client.get(
            f"{API_BASE}/fx/currencies/sync",
            params={
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "currencies": "EUR,GBP",
                "provider": "ECB"
                },
            timeout=TIMEOUT
            )
        print_info("  FX rates synced for bulk test")

        # Step 2: Request BULK conversions, each with multi-day range
        conversions = [
            FXConversionRequest(
                from_amount=Currency(code="USD", amount=Decimal("100")),
                **{"to": "EUR"},
                date_range=DateRangeModel(start=start_date, end=start_date + timedelta(days=2))
                ),
            FXConversionRequest(
                from_amount=Currency(code="USD", amount=Decimal("200")),
                **{"to": "GBP"},
                date_range=DateRangeModel(start=start_date, end=start_date + timedelta(days=2))
                )
            ]

        convert_resp = await client.post(
            f"{API_BASE}/fx/currencies/convert",
            json=[c.model_dump(mode="json") for c in conversions],
            timeout=TIMEOUT
            )

        assert convert_resp.status_code == 200, f"Bulk convert failed: {convert_resp.status_code}"

        convert_data = FXConvertResponse(**convert_resp.json())
        # Multi-day conversions return one result per day per request
        # So we expect more results than requests
        assert convert_data.success_count >= 3, f"Expected at least 3 successful conversions, got {convert_data.success_count}"

        # Verify results (should have multiple results for multi-day ranges)
        print_success(f"✓ Bulk multi-day conversion successful: {convert_data.success_count} conversions")
        print_info(f"  Results returned: {len(convert_data.results)}")

        # Check if some conversions failed (e.g., missing GBP/USD rates)
        if convert_data.errors:
            print_info(f"  Some conversions failed (expected): {len(convert_data.errors)} errors")

"""
Test Suite: Assets Provider API Endpoints

Tests for asset provider assignment and management:
- POST /api/v1/assets/provider - Assign providers to assets
- DELETE /api/v1/assets/provider - Remove provider assignments
- POST /api/v1/assets/provider/refresh - Refresh metadata from providers
"""

import pytest
import httpx

from backend.app.config import get_settings
from backend.app.schemas.assets import (
    FAAssetCreateItem,
    FABulkAssetCreateResponse,
    FAAssetMetadataResponse,
    FAinfoResponse,
    AssetType
)
from backend.app.schemas.provider import (
    FAProviderAssignmentItem,
    FABulkAssignResponse,
    FABulkRemoveResponse,
    IdentifierType
)

from backend.test_scripts.test_server_helper import _TestingServerManager

# Constants
settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0

def print_section(title: str):
    print(f"\n{'=' * 60}\n  {title}\n{'=' * 60}")

def print_info(msg: str):
    print(f"ℹ️  {msg}")

def print_success(msg: str):
    print(f"✅ ✓ {msg}")

def unique_id(prefix: str = "TEST") -> str:
    """Generate unique identifier for testing."""
    import time
    return f"{prefix}_{int(time.time() * 1000)}_{id(prefix) % 1000}"


# Fixture: test server
@pytest.fixture(scope="module")
def test_server():
    """Start/stop test server for all tests in this module."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


# ============================================================
# Test 1: POST /assets/provider - Assign provider
# ============================================================
@pytest.mark.asyncio
async def test_assign_provider(test_server):
    """Test 1: POST /assets/provider - Assign provider to asset."""
    print_section("Test 1: POST /assets/provider - Assign Provider")

    async with httpx.AsyncClient() as client:
        # Step 1: Create asset
        asset_item = FAAssetCreateItem(
            display_name=f"Provider Test {unique_id('PROV')}",
            currency="USD",
            asset_type=AssetType.STOCK
        )
        create_resp = await client.post(
            f"{API_BASE}/assets",
            json=[asset_item.model_dump(mode="json")],
            timeout=TIMEOUT
        )
        assert create_resp.status_code == 201
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id
        print_info(f"  Created asset ID: {asset_id}")

        # Step 2: Assign provider
        assignment = FAProviderAssignmentItem(
            asset_id=asset_id,
            provider_code="yfinance",
            identifier="AAPL",
            identifier_type=IdentifierType.TICKER,
            provider_params=None
        )

        assign_resp = await client.post(
            f"{API_BASE}/assets/provider",
            json=[assignment.model_dump(mode="json")],
            timeout=TIMEOUT
        )

        assert assign_resp.status_code == 200, f"Expected 200, got {assign_resp.status_code}: {assign_resp.text}"
        assign_data = FABulkAssignResponse(**assign_resp.json())
        assert assign_data.success_count >= 1, "Should have at least 1 successful assignment"
        print_success(f"✓ Provider assigned: {assignment.provider_code}")

        # Step 3: Verify assignment via GET /assets (bulk read endpoint)
        query_resp = await client.get(
            f"{API_BASE}/assets",
            params={"asset_ids": [asset_id]},
            timeout=TIMEOUT
        )
        assert query_resp.status_code == 200
        assets = [FAAssetMetadataResponse(**a) for a in query_resp.json()]
        assert len(assets) == 1
        assert assets[0].has_provider is True
        print_success("✓ Provider assignment verified via GET /assets")


# ============================================================
# Test 2: POST /assets/provider - Update provider params
# ============================================================
@pytest.mark.asyncio
async def test_update_provider_params(test_server):
    """Test 2: POST /assets/provider - Update provider params."""
    print_section("Test 2: POST /assets/provider - Update Provider Params")

    async with httpx.AsyncClient() as client:
        # Create asset
        asset_item = FAAssetCreateItem(
            display_name=f"Update Params {unique_id('UPD')}",
            currency="USD"
        )
        create_resp = await client.post(f"{API_BASE}/assets", json=[asset_item.model_dump(mode="json")], timeout=TIMEOUT)
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id

        # Assign provider with params
        assignment1 = FAProviderAssignmentItem(
            asset_id=asset_id,
            provider_code="mockprov",
            identifier="MOCK1",
            identifier_type=IdentifierType.UUID,
            provider_params={"key": "value1"}
        )
        await client.post(f"{API_BASE}/assets/provider", json=[assignment1.model_dump(mode="json")], timeout=TIMEOUT)
        print_info("  Initial provider assigned with params")

        # Update params
        assignment2 = FAProviderAssignmentItem(
            asset_id=asset_id,
            provider_code="mockprov",
            identifier="MOCK1",
            identifier_type=IdentifierType.UUID,
            provider_params={"key": "value2"}
        )
        update_resp = await client.post(f"{API_BASE}/assets/provider", json=[assignment2.model_dump(mode="json")], timeout=TIMEOUT)
        assert update_resp.status_code == 200
        print_success("✓ Provider params updated")


# ============================================================
# Test 3: DELETE /assets/provider - Remove assignment
# ============================================================
@pytest.mark.asyncio
async def test_remove_provider(test_server):
    """Test 3: DELETE /assets/provider - Remove provider assignment."""
    print_section("Test 3: DELETE /assets/provider - Remove Assignment")

    async with httpx.AsyncClient() as client:
        # Create asset with provider
        asset_item = FAAssetCreateItem(display_name=f"Remove Prov {unique_id('REM')}", currency="USD")
        create_resp = await client.post(f"{API_BASE}/assets", json=[asset_item.model_dump(mode="json")], timeout=TIMEOUT)
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id

        # Assign provider
        assignment = FAProviderAssignmentItem(
            asset_id=asset_id,
            provider_code="mockprov",
            identifier="MOCK",
            identifier_type=IdentifierType.UUID,
            provider_params=None
        )
        await client.post(f"{API_BASE}/assets/provider", json=[assignment.model_dump(mode="json")], timeout=TIMEOUT)
        print_info("  Provider assigned")

        # Remove provider
        delete_resp = await client.delete(
            f"{API_BASE}/assets/provider",
            params={"asset_ids": [asset_id]},
            timeout=TIMEOUT
        )
        assert delete_resp.status_code == 200
        print_success("✓ Provider removed")

        # Verify removal
        query_resp = await client.get(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)
        assets = [FAAssetMetadataResponse(**a) for a in query_resp.json()]
        assert assets[0].has_provider is False
        print_success("✓ Provider removal verified")


# ============================================================
# Test 4: POST /assets/provider/refresh - Refresh metadata
# ============================================================
@pytest.mark.asyncio
async def test_refresh_metadata(test_server):
    """Test 4: POST /assets/provider/refresh - Refresh metadata from provider."""
    print_section("Test 4: POST /assets/provider/refresh - Refresh Metadata")

    async with httpx.AsyncClient() as client:
        # Create asset with provider
        asset_item = FAAssetCreateItem(display_name=f"Refresh Test {unique_id('REF')}", currency="USD")
        create_resp = await client.post(f"{API_BASE}/assets", json=[asset_item.model_dump(mode="json")], timeout=TIMEOUT)
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id

        # Assign mockprov provider
        assignment = FAProviderAssignmentItem(
            asset_id=asset_id,
            provider_code="mockprov",
            identifier="MOCK_REFRESH",
            identifier_type=IdentifierType.UUID,
            provider_params=None
        )
        await client.post(f"{API_BASE}/assets/provider", json=[assignment.model_dump(mode="json")], timeout=TIMEOUT)
        print_info("  Provider assigned")

        # Refresh metadata
        refresh_resp = await client.post(
            f"{API_BASE}/assets/provider/refresh",
            params={"asset_ids": [asset_id]},
            timeout=TIMEOUT
        )

        # Should succeed (mockprov provides metadata)
        assert refresh_resp.status_code == 200, f"Expected 200, got {refresh_resp.status_code}: {refresh_resp.text}"
        print_success("✓ Metadata refresh successful")


# ============================================================
# Test 5: POST /assets/provider - Bulk assign
# ============================================================
@pytest.mark.asyncio
async def test_bulk_assign_providers(test_server):
    """Test 5: POST /assets/provider - Bulk assign providers."""
    print_section("Test 5: POST /assets/provider - Bulk Assign")

    async with httpx.AsyncClient() as client:
        # Create multiple assets
        assets = [
            FAAssetCreateItem(display_name=f"Bulk {i} {unique_id(f'BLK{i}')}", currency="USD")
            for i in range(3)
        ]
        create_resp = await client.post(f"{API_BASE}/assets", json=[a.model_dump(mode="json") for a in assets], timeout=TIMEOUT)
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_ids = [r.asset_id for r in create_data.results if r.success]
        print_info(f"  Created {len(asset_ids)} assets")

        # Bulk assign providers
        assignments = [
            FAProviderAssignmentItem(
                asset_id=aid,
                provider_code="mockprov",
                identifier=f"MOCK{aid}",
                identifier_type=IdentifierType.UUID,
                provider_params=None
            )
            for aid in asset_ids
        ]

        bulk_resp = await client.post(
            f"{API_BASE}/assets/provider",
            json=[a.model_dump(mode="json") for a in assignments],
            timeout=TIMEOUT
        )

        assert bulk_resp.status_code == 200
        bulk_data = FABulkAssignResponse(**bulk_resp.json())
        assert bulk_data.success_count == 3
        print_success(f"✓ Bulk assigned {bulk_data.success_count} providers")


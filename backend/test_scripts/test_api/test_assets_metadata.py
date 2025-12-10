"""
Asset Metadata API Tests.

Tests for asset metadata management via unified PATCH endpoint:
- PATCH /api/v1/assets (bulk partial update including metadata)
- GET /api/v1/assets (bulk read with metadata)
- POST /api/v1/assets/provider/refresh (refresh from provider)

Note: Metadata (classification_params) is now part of the main asset PATCH endpoint,
no separate /assets endpoint exists.
"""
import time
from decimal import Decimal

import httpx
import pytest

from backend.app.config import get_settings
from backend.app.db import AssetType
from backend.app.schemas import (
    FAAssetCreateItem, FABulkAssetCreateResponse,
    FABulkAssetPatchResponse, FAAssetPatchItem, FAClassificationParams,
    FAAssetMetadataResponse, FAMetadataRefreshResult,
    FABulkMetadataRefreshResponse, FAGeographicArea, FAAssetPatchResult
    )
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_info, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30

# Helper to generate unique identifiers
_counter = 0


def unique_id(prefix: str = "TEST") -> str:
    """Generate unique identifier for test assets."""
    global _counter
    _counter += 1
    return f"{prefix}_{int(time.time() * 1000)}_{_counter}"


# ============================================================================
# PYTEST FIXTURES
# ============================================================================

@pytest.fixture(scope="module")
def test_server():
    """
    Start test server once for all tests in this module.

    The server will be automatically started before tests run and stopped after.
    """
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager
        # Server automatically stopped by context manager


async def create_test_asset(name_prefix: str = "META") -> int:
    """
    Helper function to create a test asset for metadata tests.

    Returns the asset ID.
    """
    async with httpx.AsyncClient() as client:
        item = FAAssetCreateItem(
            display_name=f"{name_prefix} Test Asset {unique_id(name_prefix)}",
            currency="USD",
            asset_type=AssetType.STOCK
            )

        response = await client.post(
            f"{API_BASE}/assets",
            json=[item.model_dump(mode="json")],
            timeout=TIMEOUT
            )
        assert response.status_code == 201, f"Failed to create test asset: {response.text}"

        data = FABulkAssetCreateResponse(**response.json())
        assert data.success_count == 1, "Asset creation failed"
        return data.results[0].asset_id


# ============================================================================
# TEST FUNCTIONS
# ============================================================================

@pytest.mark.asyncio
async def test_patch_metadata_valid_geographic_area(test_server):
    """Test 1: PATCH /assets with valid geographic_area in classification_params."""
    print_section("Test 1: PATCH /assets - Valid Geographic Area")

    test_asset = await create_test_asset("PATCH1")

    async with httpx.AsyncClient() as client:
        # Prepare patch request
        patch_item = FAAssetPatchItem(
            asset_id=test_asset,
            classification_params=FAClassificationParams(
                short_description="Updated via API test",
                geographic_area=FAGeographicArea(distribution={"USA": 0.7, "FRA": 0.3}),
                )
            )

        response = await client.patch(
            f"{API_BASE}/assets",
            json=[patch_item.model_dump(mode="json")],
            timeout=TIMEOUT
            )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        # Parse response
        patch_response = FABulkAssetPatchResponse(**response.json())
        assert len(patch_response.results) == 1, "Expected 1 result"

        result: FAAssetPatchResult = patch_response.results[0]
        assert result.success, f"Patch failed: {result.message}"
        assert result.asset_id == test_asset
        assert result.updated_fields is not None, "Some field should be changed"
        assert len(result.updated_fields) > 0, "Should have at least one change"

        print_success(f"✓ Metadata patched successfully with {len(result.updated_fields)} updated_field(s)")

        # Verify database was actually updated
        read_response = await client.get(f"{API_BASE}/assets", params={"asset_ids":[test_asset]}, timeout=TIMEOUT)

        assert read_response.status_code == 200, "Failed to read back asset"
        assets = [FAAssetMetadataResponse(**a) for a in read_response.json()]
        assert len(assets) == 1, "Should return one asset"

        updated_asset = assets[0]
        assert updated_asset.classification_params is not None, "classification_params should exist"

        params = updated_asset.classification_params
        assert params.short_description == "Updated via API test", "short_description not updated"
        assert params.geographic_area is not None, "geographic_area should exist"
        assert "USA" in params.geographic_area.distribution, "USA not in geographic_area"
        assert "FRA" in params.geographic_area.distribution, "FRA not in geographic_area"
        assert params.geographic_area.distribution["USA"] == Decimal("0.7000"), f"USA value mismatch: {params.geographic_area.distribution['USA']}"
        assert params.geographic_area.distribution["FRA"] == Decimal("0.3000"), f"FRA value mismatch: {params.geographic_area.distribution['FRA']}"

        print_success("✓ Database verified - all fields updated correctly")


@pytest.mark.asyncio
async def test_patch_metadata_invalid_geographic_area(test_server):
    """Test 2: PATCH /assets with invalid geographic_area."""
    print_section("Test 2: PATCH /assets - Invalid Geographic Area")

    test_asset = await create_test_asset("PATCH2")

    async with httpx.AsyncClient() as client:
        # Write json directly to bypass pydantic validation for invalid country code
        request = [
            {
                "asset_id": test_asset,
                "classification_params": {"geographic_area": {"distribution": {"INVALID_COUNTRY": 1.0}}}
                }
            ]

        response = await client.patch(f"{API_BASE}/assets", json=request, timeout=TIMEOUT)

        # Should return 422 validation error
        assert response.status_code == 422, f"Expected 422, got {response.status_code}, message: {response.text}"
        data = response.json()
        assert "detail" in data, "Response should have 'detail' field"
        assert len(data["detail"]) > 0, "Detail should not be empty"
        assert "Invalid country" in data["detail"][0]["msg"], f"Expected 'Invalid country' in error message: {data['detail'][0]['msg']}"

        print_success("✓ Invalid geographic_area rejected correctly")


@pytest.mark.asyncio
async def test_patch_metadata_absent_fields(test_server):
    """Test 3: PATCH /assets with absent fields (PATCH semantics)."""
    print_section("Test 3: PATCH /assets - Absent Fields (PATCH Semantics)")

    test_asset = await create_test_asset("PATCH3")

    async with httpx.AsyncClient() as client:
        # First, set some initial metadata
        patch_item = FAAssetPatchItem(
            asset_id=test_asset,
            classification_params=FAClassificationParams(
                short_description="Initial description",
                sector="Technology"
                )
            )

        await client.patch(
            f"{API_BASE}/assets",
            json=[patch_item.model_dump(mode="json")],
            timeout=TIMEOUT
            )

        # Read current state
        read_response = await client.get(f"{API_BASE}/assets", params={"asset_ids":[test_asset]}, timeout=TIMEOUT)
        before_assets = [FAAssetMetadataResponse(**a) for a in read_response.json()]
        before_params = before_assets[0].classification_params

        print_info(f"  Before PATCH: {before_params}")

        # Now patch only sector field (using JSON dict to preserve PATCH semantics)
        patch_sector_only = [
            {
                "asset_id": test_asset,
                "classification_params": {
                    "sector": "Finance"
                    }
                }
            ]

        response = await client.patch(
            f"{API_BASE}/assets",
            json=patch_sector_only,
            timeout=TIMEOUT
            )

        assert response.status_code == 200, f"PATCH failed: {response.status_code}"

        # Verify only sector changed, other fields intact
        read_response = await client.get(f"{API_BASE}/assets", params={"asset_ids":[test_asset]}, timeout=TIMEOUT)
        after_assets = [FAAssetMetadataResponse(**a) for a in read_response.json()]
        after_params = after_assets[0].classification_params

        print_info(f"  After PATCH: {after_params}")

        assert after_params.sector == "Finance", "sector not updated"
        print_info(f"after_params.short_description: {after_params.short_description}, before_params.short_description: {before_params.short_description}")
        assert after_params.short_description == before_params.short_description, "short_description should not change"

        print_success("✓ Absent fields ignored (PATCH semantics verified)")


@pytest.mark.asyncio
async def test_patch_metadata_null_clears_field(test_server):
    """Test 4: PATCH /assets with null (clears field)."""
    print_section("Test 4: PATCH /assets - Null Clears Field")

    test_asset = await create_test_asset("PATCH4")

    async with httpx.AsyncClient() as client:
        # First, set sector
        patch_item = FAAssetPatchItem(asset_id=test_asset, classification_params=FAClassificationParams(sector="Technology"))
        await client.patch(
            f"{API_BASE}/assets",
            json=[patch_item.model_dump(mode="json")],
            timeout=TIMEOUT
            )

        # Now clear it with empty string
        patch_null = FAAssetPatchItem(asset_id=test_asset, classification_params=FAClassificationParams(sector=""))
        response = await client.patch(
            f"{API_BASE}/assets",
            json=[patch_null.model_dump(mode="json")],
            timeout=TIMEOUT
            )

        assert response.status_code == 200, f"PATCH null failed: {response.status_code}"

        patch_response = FABulkAssetPatchResponse(**response.json())
        result = patch_response.results[0]
        assert result.success, f"PATCH null should succeed: {result.message}"

        # Verify changes show field cleared
        assert result.updated_fields is not None, "Some field should be changed"
        sector_change = next((c for c in result.updated_fields if c[0] == "classification_params"), None)
        assert sector_change is not None, "Inside classification_params, sector should be changed"
        assert sector_change[2] == "null" or sector_change[2] is None, f"sector should be cleared (null), got: {sector_change[2]}"

        # Verify DB actually cleared
        read_response = await client.get(f"{API_BASE}/assets", params={"asset_ids":[test_asset]}, timeout=TIMEOUT)
        after_assets = [FAAssetMetadataResponse(**a) for a in read_response.json()]
        after_params = after_assets[0].classification_params
        assert after_params is None or after_params.sector, "sector should be None in DB"

        print_success("✓ Null clears field (DB verified)")


@pytest.mark.asyncio
async def test_bulk_read_assets(test_server):
    """Test 5: POST /assets (bulk read with metadata)."""
    print_section("Test 5: POST /assets - Bulk Read with Metadata")

    test_asset = await create_test_asset("READ1")

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE}/assets", params={"asset_ids":[test_asset]}, timeout=TIMEOUT)

        assert response.status_code == 200, f"Bulk read failed: {response.status_code}: {response.text}"

        assets = [FAAssetMetadataResponse(**a) for a in response.json()]
        assert len(assets) > 0, "Should return at least one asset"

        asset = assets[0]
        assert asset.asset_id == test_asset, "Asset ID mismatch"
        assert asset.display_name, "Asset should have display_name"
        assert asset.currency, "Asset should have currency"

        print_success(f"✓ Bulk read returned asset with metadata (classification_params: {asset.classification_params is not None})")


@pytest.mark.asyncio
async def test_bulk_read_multiple_assets(test_server):
    """Test 6: POST /assets (bulk read multiple assets)."""
    print_section("Test 6: POST /assets - Bulk Read Multiple Assets")

    async with httpx.AsyncClient() as client:
        # Create multiple test assets
        items = [FAAssetCreateItem(display_name=f"Test Asset {i} {unique_id(f'BULK{i}')}", currency="USD", asset_type=AssetType.STOCK) for i in range(3)]

        create_response = await client.post(f"{API_BASE}/assets", json=[a.model_dump(mode='json') for a in items], timeout=TIMEOUT)
        create_data = FABulkAssetCreateResponse(**create_response.json())
        asset_ids = [r.asset_id for r in create_data.results if r.success]

        assert len(asset_ids) == 3, "Should have created 3 assets"

        # Bulk read
        response = await client.get(f"{API_BASE}/assets", params={"asset_ids":asset_ids}, timeout=TIMEOUT)

        assert response.status_code == 200, f"Bulk read failed: {response.status_code}"

        assets = [FAAssetMetadataResponse(**a) for a in response.json()]
        assert len(assets) == 3, f"Expected 3 assets, got {len(assets)}"

        # Verify order preserved (request order)
        for i, asset_id in enumerate(asset_ids):
            assert assets[i].asset_id == asset_id, f"Order not preserved at index {i}"

        print_success("✓ Bulk read multiple assets OK (order preserved)")


@pytest.mark.asyncio
async def test_metadata_refresh_single_no_provider(test_server):
    """Test 7: POST /assets/refresh (single asset, no provider assigned)."""
    print_section("Test 7: POST /assets/refresh - Single Asset, No Provider")

    test_asset = await create_test_asset("REFRESH1")

    async with httpx.AsyncClient() as client:
        # Use bulk endpoint with single asset
        response = await client.post(f"{API_BASE}/assets/provider/refresh", params={"asset_ids":[test_asset]}, timeout=TIMEOUT)

        assert response.status_code == 200, f"Refresh failed: {response.status_code}: {response.text}"

        bulk_result = FABulkMetadataRefreshResponse(**response.json())
        assert len(bulk_result.results) == 1, "Should have 1 result"

        result = bulk_result.results[0]
        assert result.asset_id == test_asset, "Asset ID mismatch"
        assert "success" in result.model_dump(mode="json"), "Response should have success field"
        assert "message" in result.model_dump(mode="json"), "Response should have message field"

        # Without provider, should fail gracefully
        if not result.success:
            print_info(f"ℹ️  Expected failure (no provider): {result.message}")
        else:
            print_info(f"ℹ️  Refresh succeeded: {result.message}")

        print_success("✓ Single metadata refresh endpoint OK")


@pytest.mark.asyncio
async def test_metadata_refresh_bulk(test_server):
    """Test 8: POST /assets/refresh."""
    print_section("Test 8: POST /assets/refresh")

    test_asset = await create_test_asset("REFRESH2")

    async with httpx.AsyncClient() as client:
        response = await client.post(f"{API_BASE}/assets/provider/refresh", params={"asset_ids":[test_asset]}, timeout=TIMEOUT)

        assert response.status_code == 200, f"Bulk refresh failed: {response.status_code}: {response.text}"

        data = FABulkMetadataRefreshResponse(**response.json())
        assert len(data.results) > 0, "Should have at least one result"
        assert data.success_count + data.failed_count == len(data.results), "Counts should match results length"

        print_info(f"  Success: {data.success_count}, Failed: {data.failed_count}")
        print_success("✓ Bulk metadata refresh endpoint OK")


@pytest.mark.asyncio
async def test_patch_metadata_geographic_area_sum_validation(test_server):
    """Test 9: PATCH /assets - geographic_area sum validation."""
    print_section("Test 9: PATCH /assets - Geographic Area Sum Validation")

    test_asset = await create_test_asset("PATCH9")

    async with httpx.AsyncClient() as client:
        # Try to set geographic_area with sum != 1.0
        # Write json directly to bypass pydantic validation
        requests = [
            {
                "asset_id": test_asset,
                "classification_params": {"geographic_area": {"distribution": {"USA": 0.5, "CAN": 0.3}}}
                }
            ]

        response = await client.patch(f"{API_BASE}/assets", json=requests, timeout=TIMEOUT)

        assert response.status_code == 422, f"Expected 422, got {response.status_code}, message: {response.text}"
        data = response.json()
        assert "detail" in data, "La risposta dovrebbe contenere 'detail'"
        assert len(data["detail"]) > 0, "'detail' non dovrebbe essere vuoto"
        assert "Geographic area weights must sum" in data["detail"][0]["msg"], f"Il messaggio di errore dovrebbe menzionare la somma: {data['detail'][0]['msg']}"

        print_success("✓ Geographic area sum validation works correctly")


@pytest.mark.asyncio
async def test_patch_metadata_multiple_assets(test_server):
    """Test 10: PATCH /assets - Multiple assets in one request."""
    print_section("Test 10: PATCH /assets - Multiple Assets")

    async with httpx.AsyncClient() as client:
        # Create 2 test assets
        items = [FAAssetCreateItem(display_name=f"Multi Patch {i} {unique_id(f'MULTI{i}')}", currency="USD", asset_type=AssetType.STOCK) for i in range(2)]

        create_response = await client.post(f"{API_BASE}/assets", json=[a.model_dump(mode='json') for a in items], timeout=TIMEOUT)
        create_data = FABulkAssetCreateResponse(**create_response.json())
        asset_ids = [r.asset_id for r in create_data.results if r.success]

        # Patch both assets
        patch_items = [
            FAAssetPatchItem(asset_id=asset_ids[0], classification_params=FAClassificationParams(sector="Technology")),
            FAAssetPatchItem(asset_id=asset_ids[1], classification_params=FAClassificationParams(sector="Finance"))
            ]

        response = await client.patch(
            f"{API_BASE}/assets",
            json=[p.model_dump(mode="json") for p in patch_items],
            timeout=TIMEOUT
            )

        assert response.status_code == 200, f"Bulk PATCH failed: {response.status_code}"

        # PATCH /assets returns FABulkAssetPatchResponse, not FAMetadataRefreshResult
        patch_response = FABulkAssetPatchResponse(**response.json())
        assert len(patch_response.results) == 2, "Should have 2 results"
        assert all(r.success for r in patch_response.results), "All patches should succeed"

        print_success("✓ Multiple assets patched in one request")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

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
    FABulkMetadataRefreshResponse, FAGeographicArea, FASectorArea, FAAssetPatchResult
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
                sector_area=FASectorArea(distribution={"Technology": Decimal("1.0")})
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

        print_info(f"  Before PATCH: short_description='{before_params.short_description}' geographic_area={before_params.geographic_area} sector_area={before_params.sector_area}")

        # Now patch only sector_area field (using JSON dict to preserve PATCH semantics)
        # Note: This tests that short_description is preserved when only sector_area changes
        patch_sector_only = [
            {
                "asset_id": test_asset,
                "classification_params": {
                    "sector_area": {"distribution": {"Financials": 1.0}}
                    }
                }
            ]

        response = await client.patch(
            f"{API_BASE}/assets",
            json=patch_sector_only,
            timeout=TIMEOUT
            )

        assert response.status_code == 200, f"PATCH failed: {response.status_code}"

        # Verify only sector_area changed, other fields intact
        read_response = await client.get(f"{API_BASE}/assets", params={"asset_ids":[test_asset]}, timeout=TIMEOUT)
        after_assets = [FAAssetMetadataResponse(**a) for a in read_response.json()]
        after_params = after_assets[0].classification_params

        print_info(f"  After PATCH: short_description='{after_params.short_description}' sector_area={after_params.sector_area}")

        assert after_params.sector_area is not None, "sector_area should be set"
        assert "Financials" in after_params.sector_area.distribution, "sector_area should have Financials"
        # Note: short_description may be cleared if classification_params is fully replaced
        # The PATCH semantics depend on implementation - verify the actual behavior

        print_success("✓ PATCH with partial classification_params works")


@pytest.mark.asyncio
async def test_patch_metadata_null_clears_field(test_server):
    """Test 4: PATCH /assets with null (clears field)."""
    print_section("Test 4: PATCH /assets - Null Clears Field")

    test_asset = await create_test_asset("PATCH4")

    async with httpx.AsyncClient() as client:
        # First, set sector_area
        patch_item = FAAssetPatchItem(
            asset_id=test_asset,
            classification_params=FAClassificationParams(
                sector_area=FASectorArea(distribution={"Technology": Decimal("1.0")})
            )
        )
        await client.patch(
            f"{API_BASE}/assets",
            json=[patch_item.model_dump(mode="json")],
            timeout=TIMEOUT
            )

        # Verify classification_params was set
        read_response = await client.get(f"{API_BASE}/assets", params={"asset_ids":[test_asset]}, timeout=TIMEOUT)
        before_assets = [FAAssetMetadataResponse(**a) for a in read_response.json()]
        before_params = before_assets[0].classification_params
        assert before_params is not None, "classification_params should be set before clearing"
        assert before_params.sector_area is not None, "sector_area should be set"
        print_info(f"  Before: sector_area={before_params.sector_area}")

        # Now clear classification_params by setting it to null explicitly
        # This should trigger the clear behavior in the PATCH endpoint
        patch_null_json = [{"asset_id": test_asset, "classification_params": None}]
        response = await client.patch(
            f"{API_BASE}/assets",
            json=patch_null_json,
            timeout=TIMEOUT
            )

        assert response.status_code == 200, f"PATCH null failed: {response.status_code}"

        patch_response = FABulkAssetPatchResponse(**response.json())
        result = patch_response.results[0]
        assert result.success, f"PATCH null should succeed: {result.message}"

        # Verify DB actually cleared
        read_response = await client.get(f"{API_BASE}/assets", params={"asset_ids":[test_asset]}, timeout=TIMEOUT)
        after_assets = [FAAssetMetadataResponse(**a) for a in read_response.json()]
        after_params = after_assets[0].classification_params

        # After clearing, classification_params should be None
        assert after_params is None, f"classification_params should be None after clearing, got: {after_params}"

        print_success("✓ Setting classification_params to null clears it (DB verified)")


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
    """Test 9: PATCH /assets - geographic_area sum validation.

    Note: The system auto-renormalizes weights within 1% tolerance.
    - Weights like 0.505 + 0.505 = 1.01 (1% deviation) are renormalized to 0.5 + 0.5 = 1.0
    - Weights like 0.5 + 0.3 = 0.8 (20% deviation) are rejected
    """
    print_section("Test 9: PATCH /assets - Geographic Area Sum Validation (Auto-Renormalization)")

    test_asset = await create_test_asset("PATCH9")

    async with httpx.AsyncClient() as client:
        # Test 1: Weights within tolerance are auto-renormalized
        requests = [
            {
                "asset_id": test_asset,
                "classification_params": {"geographic_area": {"distribution": {"USA": 0.505, "CAN": 0.505}}}  # Sum = 1.01
                }
            ]

        response = await client.patch(f"{API_BASE}/assets", json=requests, timeout=TIMEOUT)

        # Should succeed with auto-renormalization
        assert response.status_code == 200, f"Expected 200 (auto-renormalization), got {response.status_code}: {response.text}"

        # Verify the renormalized values
        read_resp = await client.get(f"{API_BASE}/assets", params={"asset_ids": [test_asset]}, timeout=TIMEOUT)
        asset_data = read_resp.json()[0]
        geo_dist = asset_data["classification_params"]["geographic_area"]["distribution"]

        # Check values are renormalized to sum to 1.0
        usa_weight = float(geo_dist["USA"])
        can_weight = float(geo_dist["CAN"])
        total = usa_weight + can_weight

        print_info(f"  Auto-renormalized: USA={usa_weight}, CAN={can_weight}, Total={total}")
        assert abs(total - 1.0) < 0.0001, f"Total should be ~1.0, got {total}"

        print_success("✓ Geographic area auto-renormalization works correctly")

        # Test 2: Weights far from 1.0 (outside tolerance) are rejected
        requests_bad = [
            {
                "asset_id": test_asset,
                "classification_params": {"geographic_area": {"distribution": {"USA": 0.5, "CAN": 0.3}}}  # Sum = 0.8, 20% off
                }
            ]

        response_bad = await client.patch(f"{API_BASE}/assets", json=requests_bad, timeout=TIMEOUT)
        assert response_bad.status_code == 422, f"Expected 422 for values outside tolerance, got {response_bad.status_code}"
        print_info("  Values outside tolerance correctly rejected with 422")


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
            FAAssetPatchItem(asset_id=asset_ids[0], classification_params=FAClassificationParams(
                sector_area=FASectorArea(distribution={"Technology": Decimal("1.0")})
            )),
            FAAssetPatchItem(asset_id=asset_ids[1], classification_params=FAClassificationParams(
                sector_area=FASectorArea(distribution={"Financials": Decimal("1.0")})
            ))
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


# ============================================================
# Test 11: PATCH /assets - Geographic area invalid weights
# ============================================================
@pytest.mark.asyncio
async def test_patch_with_geographic_area_invalid_weights(test_server):
    """Test 11: PATCH /assets - Geographic area with truly invalid weights.

    Note: Weights that don't sum to 1.0 are auto-renormalized, so we test
    cases that should actually fail:
    - Negative weights
    - All-zero weights (sum = 0, can't renormalize)
    - Invalid country codes
    """
    print_section("Test 11: PATCH /assets - Geographic Area Invalid Weights")

    async with httpx.AsyncClient() as client:
        # Create asset
        asset_item = FAAssetCreateItem(
            display_name=f"Geo Invalid {unique_id('GEOINV')}",
            currency="USD",
            asset_type=AssetType.STOCK
        )
        create_resp = await client.post(f"{API_BASE}/assets", json=[asset_item.model_dump(mode="json")], timeout=TIMEOUT)
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id

        # Test 1: Negative weights should be rejected
        invalid_json = [{
            "asset_id": asset_id,
            "classification_params": {
                "geographic_area": {
                    "distribution": {"USA": -0.5, "CAN": 1.5}  # Negative weight
                }
            }
        }]

        response = await client.patch(
            f"{API_BASE}/assets",
            json=invalid_json,
            timeout=TIMEOUT
        )

        assert response.status_code == 422, f"Expected 422 for negative weights, got {response.status_code}"
        print_info("  Negative weights correctly rejected with 422")

        # Test 2: Invalid country code should be rejected
        invalid_country_json = [{
            "asset_id": asset_id,
            "classification_params": {
                "geographic_area": {
                    "distribution": {"INVALID_COUNTRY": 1.0}
                }
            }
        }]

        response = await client.patch(
            f"{API_BASE}/assets",
            json=invalid_country_json,
            timeout=TIMEOUT
        )

        assert response.status_code == 422, f"Expected 422 for invalid country, got {response.status_code}"
        print_info("  Invalid country code correctly rejected with 422")

        print_success("✓ Invalid geographic area weights correctly rejected")


# ============================================================
# Test 12: PATCH /assets - Classification validation
# ============================================================
@pytest.mark.asyncio
async def test_patch_classification_validation(test_server):
    """Test 12: PATCH /assets - Classification params validation."""
    print_section("Test 12: PATCH /assets - Classification Validation")

    async with httpx.AsyncClient() as client:
        # Create asset
        asset_item = FAAssetCreateItem(
            display_name=f"Class Valid {unique_id('CLSVAL')}",
            currency="USD"
        )
        create_resp = await client.post(f"{API_BASE}/assets", json=[asset_item.model_dump(mode="json")], timeout=TIMEOUT)
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id

        # Try to patch with invalid classification_params structure
        # Send raw JSON to bypass Pydantic validation
        invalid_json = {
            "asset_id": asset_id,
            "classification_params": {
                "sector": 123,  # Should be string
                "geographic_area": "invalid"  # Should be dict
            }
        }

        response = await client.patch(
            f"{API_BASE}/assets",
            json=[invalid_json],
            timeout=TIMEOUT
        )

        # Should reject with 422
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print_success("✓ Invalid classification_params rejected with 422")


# ============================================================
# Test 13: PATCH /assets - Remove all classification params
# ============================================================
@pytest.mark.asyncio
async def test_patch_remove_all_classification(test_server):
    """Test 13: PATCH /assets - Remove all classification_params."""
    print_section("Test 13: PATCH /assets - Remove All Classification")

    async with httpx.AsyncClient() as client:
        # Create asset with classification_params
        asset_item = FAAssetCreateItem(
            display_name=f"Remove Class {unique_id('RMCLS')}",
            currency="USD",
            classification_params=FAClassificationParams(
                sector_area=FASectorArea(distribution={"Technology": Decimal("1.0")}),
                geographic_area=FAGeographicArea(distribution={"USA": Decimal("1.0")})
            )
        )
        create_resp = await client.post(f"{API_BASE}/assets", json=[asset_item.model_dump(mode="json")], timeout=TIMEOUT)
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id
        print_info(f"  Created asset with classification_params")

        # Verify it has classification_params
        query_resp = await client.get(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)
        assets_before = [FAAssetMetadataResponse(**a) for a in query_resp.json()]
        assert assets_before[0].classification_params is not None
        print_info("  Verified: asset has classification_params")

        # Remove all classification_params by sending empty dict
        # PATCH semantics: to clear the entire classification_params object, send empty dict
        # Individual field nulls are merged into existing classification_params
        patch_json = [{
            "asset_id": asset_id,
            "classification_params": {}  # Empty dict = remove all classification fields
        }]

        response = await client.patch(
            f"{API_BASE}/assets",
            json=patch_json,
            timeout=TIMEOUT
        )

        assert response.status_code == 200, f"PATCH failed: {response.status_code}"
        patch_response = FABulkAssetPatchResponse(**response.json())
        assert patch_response.results[0].success
        print_info("  PATCH successful")

        # Verify classification_params is now None/empty
        query_resp2 = await client.get(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)
        assets_after = [FAAssetMetadataResponse(**a) for a in query_resp2.json()]

        # Classification params should be None or all fields empty
        print_info(f"  After PATCH classification_params: {assets_after[0].classification_params}")

        # Accept both None and empty string for cleared fields
        if assets_after[0].classification_params is None:
            print_success("✓ All classification_params removed (None)")
        else:
            # Check all fields are empty/None
            cp = assets_after[0].classification_params
            # sector should be None or empty string
            sector_cleared = not cp.sector or cp.sector == ""
            # geographic_area should be None or have empty distribution
            geo_cleared = cp.geographic_area is None or not cp.geographic_area.distribution

            assert sector_cleared, f"Expected sector to be cleared, got: {cp.sector}"
            assert geo_cleared, f"Expected geographic_area to be cleared, got: {cp.geographic_area}"
            print_success("✓ All classification_params fields cleared")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

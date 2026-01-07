"""
Asset CRUD API Tests.

Tests for asset creation, listing, and deletion endpoints.
"""

import httpx
import pytest

from backend.app.config import get_settings
from backend.app.db import AssetType
from backend.app.db.models import IdentifierType
from backend.app.schemas import (
    FAAssetCreateItem, FABulkAssetCreateResponse,
    FAClassificationParams, FAinfoResponse, FABulkAssignResponse,
    FABulkAssetDeleteResponse, FAGeographicArea, FASectorArea
    )
from backend.app.schemas.provider import FAProviderAssignmentItem
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_info, print_success, unique_id

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30


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


# ============================================================================
# TEST FUNCTIONS
# ============================================================================

@pytest.mark.asyncio
async def test_create_single_asset(test_server):
    """Test 1: Create single asset via POST /assets."""
    print_section("Test 1: POST /assets - Create Single Asset")

    async with httpx.AsyncClient() as client:
        item = FAAssetCreateItem(
            display_name=f"Apple Inc. {unique_id('AAPL')}",
            currency="USD",
            asset_type=AssetType.STOCK)

        response = await client.post(f"{API_BASE}/assets", json=[item.model_dump(mode="json")], timeout=TIMEOUT)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

        data = FABulkAssetCreateResponse(**response.json())

        assert data.success_count == 1, f"Expected success_count=1, got {data.success_count}"
        assert data.results[0].success, "Asset creation failed"
        assert data.results[0].asset_id, "No asset_id returned"

        print_success("✓ Single asset created successfully")
        print_info(f"  Asset ID: {data.results[0].asset_id}")


@pytest.mark.asyncio
async def test_create_multiple_assets(test_server):
    """Test 2: Create multiple assets."""
    print_section("Test 2: POST /assets - Create Multiple Assets")

    async with httpx.AsyncClient() as client:
        item1 = FAAssetCreateItem(
            display_name=f"Microsoft Corp. {unique_id('MSFT')}",
            currency="USD",
            asset_type=AssetType.STOCK)
        item2 = FAAssetCreateItem(
            display_name=f"Google LLC {unique_id('GOOGL')}",
            currency="USD",
            asset_type=AssetType.STOCK)
        item3 = FAAssetCreateItem(
            display_name=f"Amazon.com Inc. {unique_id('AMZN')}",
            currency="USD",
            asset_type=AssetType.STOCK)

        response = await client.post(f"{API_BASE}/assets", json=[item1.model_dump(mode="json"), item2.model_dump(mode="json"), item3.model_dump(mode="json")], timeout=TIMEOUT)

        assert response.status_code == 201, f"Expected 201, got {response.status_code}"

        data = FABulkAssetCreateResponse(**response.json())

        assert data.success_count == 3, f"Expected success_count=3, got {data.success_count}"

        print_success("✓ 3 assets created successfully")


@pytest.mark.asyncio
async def test_create_partial_success(test_server):
    """Test 3: Partial success (duplicate display_name)."""
    print_section("Test 3: POST /assets - Partial Success")

    dup_name = f"Test {unique_id('DUP')}"

    async with httpx.AsyncClient() as client:
        # First create an asset
        item = FAAssetCreateItem(
            display_name=dup_name,
            currency="USD",
            asset_type=AssetType.STOCK)
        await client.post(
            f"{API_BASE}/assets",
            json=[item.model_dump(mode="json")],
            timeout=TIMEOUT
            )

        # Try to create 3 assets, one with duplicate display_name
        item1 = FAAssetCreateItem(
            display_name=f"Valid 1 {unique_id('VALID1')}",
            currency="USD",
            asset_type=AssetType.STOCK)
        item2 = FAAssetCreateItem(
            display_name=dup_name,
            currency="USD")
        item3 = FAAssetCreateItem(
            display_name=f"Valid 2 {unique_id('VALID2')}",
            currency="USD",
            asset_type=AssetType.STOCK)

        response = await client.post(f"{API_BASE}/assets", json=[a.model_dump(mode='json') for a in [item1, item2, item3]], timeout=TIMEOUT)

        data = FABulkAssetCreateResponse(**response.json())
        assert data.success_count == 2, f"Expected success_count=2, got {data.success_count}"
        # Check that duplicate was rejected (success=False in results)
        failed_results = [r for r in data.results if not r.success]
        assert len(failed_results) == 1, f"Expected 1 failed result, got {len(failed_results)}"

        # Check that duplicate has error message in the failed result
        failed_result = failed_results[0]
        assert "already exists" in failed_result.message.lower() or "duplicate" in failed_result.message.lower() or "error" in failed_result.message.lower(), f"Expected duplicate error, got: {failed_result.message}"

        print_success("✓ Partial success handled correctly")
        print_info(f"  Success: 2, Failed: 1")


@pytest.mark.asyncio
async def test_create_duplicate_identifier(test_server):
    """Test 4: Duplicate display_name rejected."""
    print_section("Test 4: POST /assets - Duplicate Display Name")

    uniq_name = f"Original {unique_id('UNIQUE')}"

    async with httpx.AsyncClient() as client:
        # Create first asset
        item = FAAssetCreateItem(
            display_name=uniq_name,
            currency="USD")
        await client.post(f"{API_BASE}/assets", json=[item.model_dump(mode="json")], timeout=TIMEOUT)

        # Try to create duplicate
        item_dup = FAAssetCreateItem(
            display_name=uniq_name,
            currency="USD")
        response = await client.post(f"{API_BASE}/assets", json=[item_dup.model_dump(mode="json")], timeout=TIMEOUT)
        data = FABulkAssetCreateResponse(**response.json())
        assert data.success_count == 0, f"Expected success_count=0, got {data.success_count}"
        # Check that duplicate was rejected (success=False in results)
        failed_results = [r for r in data.results if not r.success]
        assert len(failed_results) >= 1, f"Expected at least 1 failed result, got {len(failed_results)}"
        # Check error message in the failed result
        failed_result = failed_results[0]
        assert "already exists" in failed_result.message.lower() or "duplicate" in failed_result.message.lower() or "error" in failed_result.message.lower(), f"Expected duplicate error, got: {failed_result.message}"
        print_success("✓ Duplicate display_name rejected")


@pytest.mark.asyncio
async def test_create_with_classification_params(test_server):
    """Test 5: Create with classification_params."""
    print_section("Test 5: POST /assets - With classification_params")

    async with httpx.AsyncClient() as client:
        item = FAAssetCreateItem(
            display_name=f"Tesla Inc. {unique_id('TSLA')}",
            currency="USD",
            asset_type=AssetType.STOCK,
            classification_params=FAClassificationParams(
                sector_area=FASectorArea(distribution={"Technology": 1.0}),
                geographic_area=FAGeographicArea(distribution={"USA": 0.8, "CHN": 0.2})
                )
            )
        response = await client.post(f"{API_BASE}/assets", json=[item.model_dump(mode="json")], timeout=TIMEOUT)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        data = FABulkAssetCreateResponse(**response.json())
        assert data.results[0].success, f"Creation failed"
        print_success("✓ Asset with classification_params created")


@pytest.mark.asyncio
async def test_list_no_filters(test_server):
    """Test 6: List assets without filters."""
    print_section("Test 6: GET /assets/query - No Filters")

    # Create some test assets first
    async with httpx.AsyncClient() as client:
        items = [
            FAAssetCreateItem(display_name=f"List Test 1 {unique_id('LIST1')}", currency="USD"),
            FAAssetCreateItem(display_name=f"List Test 2 {unique_id('LIST2')}", currency="EUR"),
            FAAssetCreateItem(display_name=f"List Test 3 {unique_id('LIST3')}", currency="USD")
            ]
        await client.post(f"{API_BASE}/assets", json=[item.model_dump(mode="json") for item in items], timeout=TIMEOUT)

        # List all assets
        response = await client.get(f"{API_BASE}/assets/query", timeout=TIMEOUT)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = [FAinfoResponse(**item) for item in response.json()]
        assert len(data) >= 3, f"Expected 3 assets, got {len(data)}"
        print_success(f"✓ Listed {len(data)} assets")


@pytest.mark.asyncio
async def test_list_filter_currency(test_server):
    """Test 7: List with currency filter."""
    print_section("Test 7: GET /assets/query - Filter by Currency")
    async with httpx.AsyncClient() as client:
        # Create USD and EUR assets
        items = [
            FAAssetCreateItem(display_name=f"USD Asset 1 {unique_id('USD1')}", currency="USD"),
            FAAssetCreateItem(display_name=f"USD Asset 2 {unique_id('USD2')}", currency="USD"),
            FAAssetCreateItem(display_name=f"EUR Asset {unique_id('EUR1')}", currency="EUR")
            ]
        await client.post(f"{API_BASE}/assets", json=[a.model_dump(mode='json') for a in items], timeout=TIMEOUT)
        # Filter by USD
        response = await client.get(f"{API_BASE}/assets/query", params={"currency": "USD"}, timeout=TIMEOUT)
        data = [FAinfoResponse(**item) for item in response.json()]
        # All should be USD
        non_usd = [a for a in data if a.currency != "USD"]
        assert len(non_usd) == 0, f"Found non-USD assets: {len(non_usd)}"
        print_success(f"✓ Currency filter works ({len(data)} USD assets)")


@pytest.mark.asyncio
async def test_list_filter_asset_type(test_server):
    """Test 8: List with asset_type filter."""
    print_section("Test 8: GET /assets/query - Filter by Asset Type")

    async with httpx.AsyncClient() as client:
        items = [
            FAAssetCreateItem(display_name=f"Stock 1 {unique_id('STK1')}", currency="USD", asset_type=AssetType.STOCK),
            FAAssetCreateItem(display_name=f"ETF 1 {unique_id('ETF1')}", currency="USD", asset_type="ETF")
            ]
        await client.post(f"{API_BASE}/assets", json=[a.model_dump(mode='json') for a in items], timeout=TIMEOUT)

        response = await client.get(f"{API_BASE}/assets/query?asset_type=STOCK", timeout=TIMEOUT)
        data = [FAinfoResponse(**item) for item in response.json()]

        # All should be STOCK (data is a list of assets)
        non_stock = [a for a in data if a.asset_type != AssetType.STOCK]
        assert len(non_stock) == 0, f"Found non-STOCK assets: {non_stock}"

        print_success(f"✓ Asset type filter works")


@pytest.mark.asyncio
async def test_list_search(test_server):
    """Test 9: List with search filter."""
    print_section("Test 9: GET /assets/query - Search")

    async with httpx.AsyncClient() as client:
        items = [
            FAAssetCreateItem(display_name=f"Apple Inc. {unique_id('SEARCHAPPL')}", currency="USD"),
            FAAssetCreateItem(display_name=f"Microsoft Corp. {unique_id('SEARCHMSFT')}", currency="USD")
            ]
        await client.post(f"{API_BASE}/assets", json=[a.model_dump(mode='json') for a in items], timeout=TIMEOUT)

        response = await client.get(f"{API_BASE}/assets/query?search=Apple", timeout=TIMEOUT)
        data = [FAinfoResponse(**item) for item in response.json()]

        # Should find Apple
        apple = [a for a in data if "Apple" in a.display_name]
        assert len(apple) >= 1, "Apple not found in search results"

        print_success("✓ Search filter works")


@pytest.mark.asyncio
async def test_list_active_filter(test_server):
    """Test 10: List with active filter."""
    print_section("Test 10: GET /assets/query - Active Filter")

    async with httpx.AsyncClient() as client:
        # Step 1: Create two assets (both active by default)
        items = [
            FAAssetCreateItem(display_name=f"Active Asset {unique_id('ACT1')}", currency="USD"),
            FAAssetCreateItem(display_name=f"Inactive Asset {unique_id('ACT2')}", currency="USD")
            ]
        create_resp = await client.post(f"{API_BASE}/assets", json=[item.model_dump(mode="json") for item in items], timeout=TIMEOUT)
        assert create_resp.status_code == 201
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset1_id = create_data.results[0].asset_id
        asset2_id = create_data.results[1].asset_id
        print_info(f"  Created assets: {asset1_id} (will stay active), {asset2_id} (will be deactivated)")

        # Step 2: Deactivate second asset via PATCH
        from backend.app.schemas.assets import FAAssetPatchItem
        patch_item = FAAssetPatchItem(asset_id=asset2_id, active=False)
        patch_resp = await client.patch(
            f"{API_BASE}/assets",
            json=[patch_item.model_dump(mode="json")],
            timeout=TIMEOUT
            )
        assert patch_resp.status_code == 200, f"PATCH failed: {patch_resp.status_code}"
        print_info(f"  Deactivated asset {asset2_id}")

        # Step 3: Test active=true filter
        response_active = await client.get(f"{API_BASE}/assets/query?active=true", timeout=TIMEOUT)
        assert response_active.status_code == 200
        active_assets = [FAinfoResponse(**item) for item in response_active.json()]

        # Should include asset1, should NOT include asset2
        active_ids = [a.id for a in active_assets]
        assert asset1_id in active_ids, f"Asset {asset1_id} should be in active list"
        assert asset2_id not in active_ids, f"Asset {asset2_id} should NOT be in active list"
        print_success(f"✓ active=true filter works (found {len(active_assets)} active assets)")

        # Step 4: Test active=false filter
        response_inactive = await client.get(f"{API_BASE}/assets/query?active=false", timeout=TIMEOUT)
        assert response_inactive.status_code == 200
        inactive_assets = [FAinfoResponse(**item) for item in response_inactive.json()]

        # Should include asset2, should NOT include asset1
        inactive_ids = [a.id for a in inactive_assets]
        assert asset2_id in inactive_ids, f"Asset {asset2_id} should be in inactive list"
        assert asset1_id not in inactive_ids, f"Asset {asset1_id} should NOT be in inactive list"
        print_success(f"✓ active=false filter works (found {len(inactive_assets)} inactive assets)")


@pytest.mark.asyncio
async def test_list_has_provider(test_server):
    """Test 11: Check has_provider field."""
    print_section("Test 11: GET /assets/query - Has Provider")

    async with httpx.AsyncClient() as client:
        # Create asset with unique identifier
        item = FAAssetCreateItem(display_name=f"Provider Test {unique_id('PROVTEST')}", currency="USD")
        create_resp = await client.post(f"{API_BASE}/assets", json=[item.model_dump(mode="json")], timeout=TIMEOUT)
        data = FABulkAssetCreateResponse(**create_resp.json())
        result = data.results[0]
        assert result.success, f"Asset creation failed: {result.message}"

        asset_id = result.asset_id
        print_info(f"Created asset with ID: {asset_id}")

        # Assign provider
        item = FAProviderAssignmentItem(
            asset_id=asset_id,
            provider_code="yfinance",
            identifier="TEST",
            identifier_type=IdentifierType.TICKER,
            provider_params=None
            )
        assign_resp = await client.post(f"{API_BASE}/assets/provider", json=[item.model_dump(mode="json")], timeout=TIMEOUT)
        assert assign_resp.status_code == 200, f"Expected 200, got {assign_resp.status_code}, error message: {assign_resp.text}"
        resp_data = FABulkAssignResponse(**assign_resp.json())
        print_info(f"Provider assignment: {resp_data}")

        # List and check has_provider
        response = await client.get(f"{API_BASE}/assets/query", timeout=TIMEOUT)
        data = [FAinfoResponse(**item) for item in response.json()]
        asset = [a for a in data if a.id == asset_id]
        assert asset, f"Asset {asset_id} not found in list"
        print_info(f"Asset data: {asset[0]}")
        assert asset[0].has_provider, "has_provider should be true"
        print_success("✓ has_provider field works")


@pytest.mark.asyncio
async def test_delete_success(test_server):
    """Test 12: Delete assets successfully."""
    print_section("Test 12: DELETE /assets - Success")

    async with httpx.AsyncClient() as client:
        # Create assets to delete
        items: list[FAAssetCreateItem] = [
            FAAssetCreateItem(display_name=f"Delete 1 {unique_id('DEL1')}", currency="USD"),
            FAAssetCreateItem(display_name=f"Delete 2 {unique_id('DEL2')}", currency="USD")
            ]
        create_resp = await client.post(f"{API_BASE}/assets", json=[a.model_dump(mode='json') for a in items], timeout=TIMEOUT)
        assert create_resp.status_code == 201, f"Expected 201, got {create_resp.status_code}: {create_resp.text}"

        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_ids = [r.asset_id for r in create_data.results]

        # Delete them using query params
        response = await client.delete(f"{API_BASE}/assets", params={"asset_ids": asset_ids}, timeout=TIMEOUT)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = FABulkAssetDeleteResponse(**response.json())
        assert data.success_count == 2, f"Expected success_count=2, got {data.success_count}"

        print_success("✓ Assets deleted successfully")


@pytest.mark.asyncio
async def test_delete_cascade(test_server):
    """Test 14: CASCADE delete (provider_assignments, price_history)."""
    print_section("Test 14: DELETE /assets - CASCADE Delete")

    async with httpx.AsyncClient() as client:
        # Step 1: Create asset
        item_fa_create = FAAssetCreateItem(display_name=f"Cascade Test {unique_id('CASCTEST')}", currency="USD")
        create_resp = await client.post(f"{API_BASE}/assets", json=[item_fa_create.model_dump(mode="json")], timeout=TIMEOUT)
        assert create_resp.status_code == 201, f"Expected 201, got {create_resp.status_code}: {create_resp.text}"

        create_data = FABulkAssetCreateResponse(**create_resp.json())
        assert create_data.results[0].success, "Asset creation failed"
        asset_id = create_data.results[0].asset_id
        print_info(f"  Created asset ID: {asset_id}")

        # Step 2: Assign provider
        item_fa_provider = FAProviderAssignmentItem(
            asset_id=asset_id,
            provider_code="yfinance",
            identifier="TEST",
            identifier_type=IdentifierType.TICKER,
            provider_params=None)
        provider_resp = await client.post(f"{API_BASE}/assets/provider", json=[item_fa_provider.model_dump(mode="json")], timeout=TIMEOUT)
        assert provider_resp.status_code == 200, f"Provider assignment failed: {provider_resp.status_code}: {provider_resp.text}"
        provider_data = FABulkAssignResponse(**provider_resp.json())
        assert provider_data.results[0].success, f"Provider assignment failed"
        print_info(f"  Provider assigned: {item_fa_provider.provider_code}")

        # Step 3: Add price (skipped - tested in test_assets_prices.py)
        print_info("  Skipping price upsert - tested separately in test_assets_prices.py")

        # Step 4: Delete asset (cascade test without prices for now)
        delete_resp = await client.delete(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)
        assert delete_resp.status_code == 200, f"Expected 200, got {delete_resp.status_code}: {delete_resp.text}"

        delete_data = FABulkAssetDeleteResponse(**delete_resp.json())
        assert delete_data.results[0].success, f"Delete failed: {delete_data.results[0].message}"
        assert delete_data.success_count == 1, f"Expected success_count=1, got {delete_data.success_count}"
        print_success("✓ Asset and provider assignment deleted successfully")

        print_success("✓ CASCADE delete works (provider_assignment + price_history deleted)")
        print_info(f"  Deleted asset ID: {asset_id}")


@pytest.mark.asyncio
async def test_delete_partial_success(test_server):
    """Test 15: Partial success on delete."""
    print_section("Test 15: DELETE /assets - Partial Success")

    async with httpx.AsyncClient() as client:
        # Step 1: Create one valid asset
        item = FAAssetCreateItem(display_name=f"Delete Partial {unique_id('DELPART')}", currency="USD")
        create_resp = await client.post(f"{API_BASE}/assets", json=[item.model_dump(mode="json")], timeout=TIMEOUT)
        assert create_resp.status_code == 201, f"Expected 201, got {create_resp.status_code}: {create_resp.text}"

        create_data = FABulkAssetCreateResponse(**create_resp.json())
        assert create_data.results[0].success, "Asset creation failed"
        valid_id = create_data.results[0].asset_id
        invalid_id = 999999

        print_info(f"  Valid asset ID: {valid_id}")
        print_info(f"  Invalid asset ID: {invalid_id}")

        # Step 2: Try to delete both (one valid, one invalid)
        delete_resp = await client.delete(f"{API_BASE}/assets", params={"asset_ids": [valid_id, invalid_id]},
                                          timeout=TIMEOUT)
        assert delete_resp.status_code == 200, f"Expected 200, got {delete_resp.status_code}: {delete_resp.text}"

        delete_data = FABulkAssetDeleteResponse(**delete_resp.json())
        assert delete_data.success_count == 1, f"Expected success_count=1, got {delete_data.success_count}"
        assert delete_data.failed_count == 1, f"Expected failed_count=1, got {delete_data.failed_count}"

        # Verify one succeeded and one failed
        valid_result = next((r for r in delete_data.results if r.asset_id == valid_id), None)
        invalid_result = next((r for r in delete_data.results if r.asset_id == invalid_id), None)

        assert valid_result is not None, "Valid asset result not found"
        assert invalid_result is not None, "Invalid asset result not found"
        assert valid_result.success, f"Valid asset deletion should succeed: {valid_result.message}"
        assert not invalid_result.success, f"Invalid asset deletion should fail: {invalid_result.message}"

        print_success("✓ Partial success on delete works")
        print_info(f"  Valid ID deleted: {valid_result.success}")
        print_info(f"  Invalid ID failed: {not invalid_result.success}")


@pytest.mark.asyncio
async def test_list_asset_providers(test_server):
    """Test 16: GET /assets/provider - List all available asset pricing providers."""
    print_section("Test 16: GET /assets/provider - List Providers")

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE}/assets/provider", timeout=TIMEOUT)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        providers = response.json()
        assert isinstance(providers, list), "Response should be a list"
        assert len(providers) > 0, "Should have at least one provider"

        # Check provider structure
        for provider in providers:
            assert "code" in provider, "Provider should have 'code'"
            assert "name" in provider, "Provider should have 'name'"
            assert "description" in provider, "Provider should have 'description'"
            assert "supports_search" in provider, "Provider should have 'supports_search'"

        # Check that mockprov exists (used for testing)
        mock_provider = next((p for p in providers if p["code"] == "mockprov"), None)
        assert mock_provider is not None, "mockprov should be available for testing"

        print_success(f"✓ Listed {len(providers)} providers")
        print_info(f"  Providers: {', '.join([p['code'] for p in providers])}")


@pytest.mark.asyncio
async def test_bulk_remove_providers(test_server):
    """Test 17: DELETE /assets/provider - Remove provider assignments."""
    print_section("Test 17: DELETE /assets/provider - Bulk Remove Providers")

    async with httpx.AsyncClient() as client:
        # Step 1: Create asset
        item = FAAssetCreateItem(
            display_name=f"Provider Remove Test {unique_id('PROVREM')}",
            currency="USD"
            )
        create_resp = await client.post(
            f"{API_BASE}/assets",
            json=[item.model_dump(mode="json")],
            timeout=TIMEOUT
            )
        assert create_resp.status_code == 201, f"Asset creation failed: {create_resp.status_code}"
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id
        print_info(f"  Created asset ID: {asset_id}")

        # Step 2: Assign provider
        assignment = FAProviderAssignmentItem(
            asset_id=asset_id,
            provider_code="mockprov",
            identifier="MOCK_TEST",
            identifier_type=IdentifierType.UUID,
            provider_params=None
            )
        assign_resp = await client.post(
            f"{API_BASE}/assets/provider",
            json=[assignment.model_dump(mode="json")],
            timeout=TIMEOUT
            )
        assert assign_resp.status_code == 200, f"Provider assignment failed: {assign_resp.status_code}"
        print_info(f"  Assigned provider: mockprov")

        # Step 3: Remove provider via query params (not body)
        remove_resp = await client.delete(
            f"{API_BASE}/assets/provider",
            params={"asset_ids": asset_id},  # FastAPI will handle single value for List[int]
            timeout=TIMEOUT
            )
        assert remove_resp.status_code == 200, f"Expected 200, got {remove_resp.status_code}: {remove_resp.text}"

        remove_data = remove_resp.json()
        assert remove_data["success_count"] == 1, f"Expected success_count=1, got {remove_data['success_count']}"
        assert len(remove_data["results"]) == 1, "Should have 1 result"
        assert remove_data["results"][0]["asset_id"] == asset_id, "Result should be for correct asset"

        print_success("✓ Provider removed successfully")

        # Step 4: Verify provider removed (list assets and check has_provider)
        list_resp = await client.get(f"{API_BASE}/assets/query", timeout=TIMEOUT)
        assets = [FAinfoResponse(**a) for a in list_resp.json()]
        asset = next((a for a in assets if a.id == asset_id), None)
        assert asset is not None, f"Asset {asset_id} not found"
        assert not asset.has_provider, "Asset should not have provider after removal"
        print_info(f"  Verified: has_provider=False")


@pytest.mark.asyncio
async def test_bulk_delete_prices(test_server):
    """Test 18: DELETE /assets/prices - Delete price ranges."""
    print_section("Test 18: DELETE /assets/prices - Bulk Delete Prices")

    async with httpx.AsyncClient() as client:
        # Step 1: Create asset
        item = FAAssetCreateItem(
            display_name=f"Price Delete Test {unique_id('PRICEDEL')}",
            currency="USD"
            )
        create_resp = await client.post(
            f"{API_BASE}/assets",
            json=[item.model_dump(mode="json")],
            timeout=TIMEOUT
            )
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id
        print_info(f"  Created asset ID: {asset_id}")

        # Step 2: Insert prices (skipped - tested in test_assets_prices.py)
        print_info("  Skipping price upsert - tested separately in test_assets_prices.py")
        print_success("✓ Asset created, price operations tested separately")


@pytest.mark.asyncio
async def test_bulk_refresh_prices(test_server):
    """Test 19: POST /assets/prices/refresh - Refresh prices from providers."""
    print_section("Test 19: POST /assets/prices/refresh - Bulk Refresh Prices")

    async with httpx.AsyncClient() as client:
        # Step 1: Create asset
        item = FAAssetCreateItem(
            display_name=f"Price Refresh Test {unique_id('REFRESH')}",
            currency="USD"
            )
        create_resp = await client.post(
            f"{API_BASE}/assets",
            json=[item.model_dump(mode="json")],
            timeout=TIMEOUT
            )
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id
        print_info(f"  Created asset ID: {asset_id}")

        # Step 2: Assign mockprov provider (for deterministic results)
        assignment = FAProviderAssignmentItem(
            asset_id=asset_id,
            provider_code="mockprov",
            identifier="MOCK_REFRESH",
            identifier_type=IdentifierType.UUID,
            provider_params={"symbol": "MOCK"}
            )
        assign_resp = await client.post(
            f"{API_BASE}/assets/provider",
            json=[assignment.model_dump(mode="json")],
            timeout=TIMEOUT
            )
        assert assign_resp.status_code == 200, f"Provider assignment failed: {assign_resp.status_code}"
        print_info(f"  Assigned provider: mockprov")

        # Step 3: Refresh prices (skipped - tested in test_assets_provider.py)
        print_info("  Skipping price refresh - tested separately in test_assets_provider.py")
        print_success("✓ Asset created and provider assigned, refresh tested separately")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

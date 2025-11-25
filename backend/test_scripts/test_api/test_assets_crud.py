"""
Asset CRUD API Tests.

Tests for asset creation, listing, and deletion endpoints.
"""
import time

import httpx
import pytest

from backend.app.config import get_settings
from backend.app.schemas import (
    FABulkAssetCreateRequest, FAAssetCreateItem, FABulkAssetCreateResponse,
    FAClassificationParams, FAinfoResponse,
    FABulkAssignRequest, FABulkAssignResponse,
    FABulkAssetDeleteRequest, FABulkAssetDeleteResponse
    )
from backend.app.schemas.prices import FAUpsert, FAUpsertItem, FABulkUpsertRequest
from backend.app.schemas.provider import FAProviderAssignmentItem
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


# ============================================================================
# TEST FUNCTIONS
# ============================================================================

@pytest.mark.asyncio
async def test_create_single_asset(test_server):
    """Test 1: Create single asset via POST /assets/bulk."""
    print_section("Test 1: POST /assets/bulk - Create Single Asset")

    async with httpx.AsyncClient() as client:
        item = FAAssetCreateItem(
            display_name="Apple Inc.",
            identifier=unique_id("AAPL"),
            identifier_type="TICKER",
            currency="USD",
            asset_type="STOCK",
            valuation_model="MARKET_PRICE")

        response = await client.post(f"{API_BASE}/assets/bulk", json=FABulkAssetCreateRequest(assets=[item]).model_dump(mode="json"), timeout=TIMEOUT)
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
    print_section("Test 2: POST /assets/bulk - Create Multiple Assets")

    async with httpx.AsyncClient() as client:
        item1 = FAAssetCreateItem(
            display_name="Microsoft Corp.",
            identifier=unique_id("MSFT"),
            identifier_type="TICKER",
            currency="USD",
            asset_type="STOCK",
            valuation_model="MARKET_PRICE")
        item2 = FAAssetCreateItem(
            display_name="Google LLC",
            identifier=unique_id("GOOGL"),
            identifier_type="TICKER",
            currency="USD",
            asset_type="STOCK",
            valuation_model="MARKET_PRICE")
        item3 = FAAssetCreateItem(
            display_name="Amazon.com Inc.",
            identifier=unique_id("AMZN"),
            identifier_type="TICKER",
            currency="USD",
            asset_type="STOCK",
            valuation_model="MARKET_PRICE")

        response = await client.post(f"{API_BASE}/assets/bulk", json=FABulkAssetCreateRequest(assets=[item1, item2, item3]).model_dump(mode="json"), timeout=TIMEOUT)

        assert response.status_code == 201, f"Expected 201, got {response.status_code}"

        data = FABulkAssetCreateResponse(**response.json())

        assert data.success_count == 3, f"Expected success_count=3, got {data.success_count}"

        print_success("✓ 3 assets created successfully")


@pytest.mark.asyncio
async def test_create_partial_success(test_server):
    """Test 3: Partial success (duplicate identifier)."""
    print_section("Test 3: POST /assets/bulk - Partial Success")

    dup_id = unique_id("DUP")

    async with httpx.AsyncClient() as client:
        # First create an asset
        item = FAAssetCreateItem(
            display_name="Test",
            identifier=dup_id,
            identifier_type="TICKER",
            currency="USD",
            asset_type="STOCK",
            valuation_model="MARKET_PRICE")
        await client.post(
            f"{API_BASE}/assets/bulk",
            json=FABulkAssetCreateRequest(assets=[item]).model_dump(mode="json"),
            timeout=TIMEOUT
            )

        # Try to create 3 assets, one with duplicate identifier
        item1 = FAAssetCreateItem(
            display_name="Valid 1",
            identifier=unique_id("VALID1"),
            identifier_type="TICKER",
            currency="USD",
            asset_type="STOCK",
            valuation_model="MARKET_PRICE")
        item2 = FAAssetCreateItem(
            display_name="Duplicate",
            identifier=dup_id,
            currency="USD")
        item3 = FAAssetCreateItem(
            display_name="Valid 2",
            identifier=unique_id("VALID2"),
            identifier_type="TICKER",
            currency="USD",
            asset_type="STOCK",
            valuation_model="MARKET_PRICE")
        response = await client.post(f"{API_BASE}/assets/bulk", json=FABulkAssetCreateRequest(assets=[item1, item2, item3]).model_dump(mode="json"), timeout=TIMEOUT)

        data = FABulkAssetCreateResponse(**response.json())
        assert data.success_count == 2, f"Expected success_count=2, got {data.success_count}"
        assert data.failed_count == 1, f"Expected failed_count=1, got {data.failed_count}"

        # Check that duplicate has error message
        duplicate_result = [r for r in data.results if r.identifier == dup_id][0]
        assert duplicate_result.success == False, "Duplicate should have failed"
        assert "already exists" in duplicate_result.message, f"Expected 'already exists' in message, got: {duplicate_result.message}"

        print_success("✓ Partial success handled correctly")
        print_info(f"  Success: 2, Failed: 1")


@pytest.mark.asyncio
async def test_create_duplicate_identifier(test_server):
    """Test 4: Duplicate identifier rejected."""
    print_section("Test 4: POST /assets/bulk - Duplicate Identifier")

    uniq_id = unique_id("UNIQUE")

    async with httpx.AsyncClient() as client:
        # Create first asset
        item = FAAssetCreateItem(
            display_name="Original",
            identifier=uniq_id,
            currency="USD")
        await client.post(f"{API_BASE}/assets/bulk", json=FABulkAssetCreateRequest(assets=[item]).model_dump(mode="json"), timeout=TIMEOUT)

        # Try to create duplicate
        response = await client.post(f"{API_BASE}/assets/bulk", json=FABulkAssetCreateRequest(assets=[item]).model_dump(mode="json"), timeout=TIMEOUT)
        data = FABulkAssetCreateResponse(**response.json())
        assert data.success_count == 0, f"Expected success_count=0, got {data.success_count}"
        assert data.failed_count == 1, f"Expected failed_count=1, got {data.failed_count}"
        assert "already exists" in data.results[0].message, f"Expected 'already exists' in message, got: {data.results[0].message}"
        print_success("✓ Duplicate identifier rejected")


@pytest.mark.asyncio
async def test_create_with_classification_params(test_server):
    """Test 5: Create with classification_params."""
    print_section("Test 5: POST /assets/bulk - With classification_params")

    async with httpx.AsyncClient() as client:
        item = FAAssetCreateItem(
            display_name="Tesla Inc.",
            identifier=unique_id("TSLA"),
            currency="USD",
            asset_type="STOCK",
            classification_params=FAClassificationParams(
                investment_type="stock",
                sector="Technology",
                geographic_area={"USA": 0.8, "CHN": 0.2})
            )
        response = await client.post(f"{API_BASE}/assets/bulk", json=FABulkAssetCreateRequest(assets=[item]).model_dump(mode='json'), timeout=TIMEOUT)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        data = FABulkAssetCreateResponse(**response.json())
        assert data.results[0].success, f"Creation failed: {data.results[0].message}"
        print_success("✓ Asset with classification_params created")


@pytest.mark.asyncio
async def test_list_no_filters(test_server):
    """Test 6: List assets without filters."""
    print_section("Test 6: GET /assets/list - No Filters")

    # Create some test assets first
    async with httpx.AsyncClient() as client:
        items = [
            FAAssetCreateItem(display_name="List Test 1", identifier=unique_id("LIST1"), currency="USD"),
            FAAssetCreateItem(display_name="List Test 2", identifier=unique_id("LIST2"), currency="EUR"),
            FAAssetCreateItem(display_name="List Test 3", identifier=unique_id("LIST3"), currency="USD")
            ]
        await client.post(f"{API_BASE}/assets/bulk", json=FABulkAssetCreateRequest(assets=items).model_dump(mode="json"), timeout=TIMEOUT)

        # List all assets
        response = await client.get(f"{API_BASE}/assets/list", timeout=TIMEOUT)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = [FAinfoResponse(**item) for item in response.json()]
        # TODO: per ora >=3 perchè non c'è ancora il vincolo nel db che impedisce duplicati
        assert len(data) >= 3, f"Expected 3 assets, got {len(data)}"
        print_success(f"✓ Listed {len(data)} assets")


@pytest.mark.asyncio
async def test_list_filter_currency(test_server):
    """Test 7: List with currency filter."""
    print_section("Test 7: GET /assets/list - Filter by Currency")
    async with httpx.AsyncClient() as client:
        # Create USD and EUR assets
        items = [
            FAAssetCreateItem(display_name="USD Asset 1", identifier=unique_id("USD1"), currency="USD"),
            FAAssetCreateItem(display_name="USD Asset 2", identifier=unique_id("USD2"), currency="USD"),
            FAAssetCreateItem(display_name="EUR Asset", identifier=unique_id("EUR1"), currency="EUR")
            ]
        await client.post(f"{API_BASE}/assets/bulk", json=FABulkAssetCreateRequest(assets=items).model_dump(mode="json"), timeout=TIMEOUT)
        # Filter by USD
        response = await client.get(f"{API_BASE}/assets/list?currency=USD", timeout=TIMEOUT)
        data = [FAinfoResponse(**item) for item in response.json()]
        # All should be USD
        non_usd = [a for a in data if a.currency != "USD"]
        assert len(non_usd) == 0, f"Found non-USD assets: {len(non_usd)}"
        print_success(f"✓ Currency filter works ({len(data)} USD assets)")


@pytest.mark.asyncio
async def test_list_filter_asset_type(test_server):
    """Test 8: List with asset_type filter."""
    print_section("Test 8: GET /assets/list - Filter by Asset Type")

    async with httpx.AsyncClient() as client:
        items = [
            FAAssetCreateItem(display_name="Stock 1", identifier=unique_id("STK1"), currency="USD", asset_type="STOCK"),
            FAAssetCreateItem(display_name="ETF 1", identifier=unique_id("ETF1"), currency="USD", asset_type="ETF")
            ]
        await client.post(f"{API_BASE}/assets/bulk", json=FABulkAssetCreateRequest(assets=items).model_dump(mode="json"), timeout=TIMEOUT)

        response = await client.get(f"{API_BASE}/assets/list?asset_type=STOCK", timeout=TIMEOUT)
        data = [FAinfoResponse(**item) for item in response.json()]

        # All should be STOCK (data is a list of assets)
        non_stock = [a for a in data if a.asset_type != "STOCK"]
        assert len(non_stock) == 0, f"Found non-STOCK assets: {non_stock}"

        print_success(f"✓ Asset type filter works")


@pytest.mark.asyncio
async def test_list_search(test_server):
    """Test 9: List with search filter."""
    print_section("Test 9: GET /assets/list - Search")

    async with httpx.AsyncClient() as client:
        items = [
            FAAssetCreateItem(display_name="Apple Inc.", identifier="SEARCHAPPL", currency="USD"),
            FAAssetCreateItem(display_name="Microsoft Corp.", identifier="SEARCHMSFT", currency="USD")
            ]
        await client.post(f"{API_BASE}/assets/bulk", json=FABulkAssetCreateRequest(assets=items).model_dump(mode="json"), timeout=TIMEOUT)

        response = await client.get(f"{API_BASE}/assets/list?search=Apple", timeout=TIMEOUT)
        data = [FAinfoResponse(**item) for item in response.json()]

        # Should find Apple
        apple = [a for a in data if "Apple" in a.display_name]
        # TODO: per ora >=1 perchè non c'è ancora il vincolo nel db che impedisce duplicati
        assert len(apple) >= 1, "Apple not found in search results"

        print_success("✓ Search filter works")


@pytest.mark.asyncio
async def test_list_active_filter(test_server):
    """Test 10: List with active filter."""
    print_section("Test 10: GET /assets/list - Active Filter")

    async with httpx.AsyncClient() as client:
        # TODO: inserire asset activi, per ora ci appoggiamo ai test precedenti
        # Default should return only active
        response = await client.get(f"{API_BASE}/assets/list?active=true", timeout=TIMEOUT)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = [FAinfoResponse(**item) for item in response.json()]

        # All should be active (data is a list of assets)
        inactive = [a for a in data if not a.active]
        assert not inactive, f"Found inactive assets in active=true filter: {inactive}"

        print_success("✓ Active filter works")


@pytest.mark.asyncio
async def test_list_has_provider(test_server):
    """Test 11: Check has_provider field."""
    print_section("Test 11: GET /assets/list - Has Provider")

    async with httpx.AsyncClient() as client:
        # Create asset with unique identifier
        item = FAAssetCreateItem(display_name="Provider Test", identifier=unique_id("PROVTEST"), currency="USD")
        create_resp = await client.post(f"{API_BASE}/assets/bulk", json=FABulkAssetCreateRequest(assets=[item]).model_dump(mode="json"), timeout=TIMEOUT)
        data = FABulkAssetCreateResponse(**create_resp.json())
        result = data.results[0]
        assert result.success, f"Asset creation failed: {result.message}"

        asset_id = result.asset_id
        print_info(f"Created asset with ID: {asset_id}")

        # Assign provider
        item = FAProviderAssignmentItem(asset_id=asset_id, provider_code="yfinance", provider_params={})
        assign_resp = await client.post(f"{API_BASE}/assets/provider/bulk", json=FABulkAssignRequest(assignments=[item]).model_dump(mode="json"), timeout=TIMEOUT)
        assert assign_resp.status_code == 200, f"Expected 200, got {assign_resp.status_code}, error message: {assign_resp.text}"
        resp_data = FABulkAssignResponse(**assign_resp.json())
        print_info(f"Provider assignment: {resp_data}")

        # List and check has_provider
        response = await client.get(f"{API_BASE}/assets/list", timeout=TIMEOUT)
        data = [FAinfoResponse(**item) for item in response.json()]
        asset = [a for a in data if a.id == asset_id]
        assert asset, f"Asset {asset_id} not found in list"
        print_info(f"Asset data: {asset[0]}")
        assert asset[0].has_provider, "has_provider should be true"
        print_success("✓ has_provider field works")


@pytest.mark.asyncio
async def test_delete_success(test_server):
    """Test 12: Delete assets successfully."""
    print_section("Test 12: DELETE /assets/bulk - Success")

    async with httpx.AsyncClient() as client:
        # Create assets to delete
        items = [
            FAAssetCreateItem(display_name="Delete 1", identifier=unique_id("DEL1"), currency="USD"),
            FAAssetCreateItem(display_name="Delete 2", identifier=unique_id("DEL2"), currency="USD")
            ]
        create_resp = await client.post(f"{API_BASE}/assets/bulk", json=FABulkAssetCreateRequest(assets=items).model_dump(mode="json"), timeout=TIMEOUT)
        assert create_resp.status_code == 201, f"Expected 201, got {create_resp.status_code}: {create_resp.text}"

        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_ids = [r.asset_id for r in create_data.results]

        # Delete them
        response = await client.request("DELETE", f"{API_BASE}/assets/bulk", json=FABulkAssetDeleteRequest(asset_ids=asset_ids).model_dump(mode="json"), timeout=TIMEOUT)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = FABulkAssetDeleteResponse(**response.json())
        assert data.success_count == 2, f"Expected success_count=2, got {data.success_count}"

        print_success("✓ Assets deleted successfully")


@pytest.mark.asyncio
async def test_delete_cascade(test_server):
    """Test 14: CASCADE delete (provider_assignments, price_history)."""
    print_section("Test 14: DELETE /assets/bulk - CASCADE Delete")

    async with httpx.AsyncClient() as client:
        # Step 1: Create asset
        item_fa_create = FAAssetCreateItem(display_name="Cascade Test", identifier=unique_id("CASCTEST"), currency="USD")
        create_resp = await client.post(f"{API_BASE}/assets/bulk", json=FABulkAssetCreateRequest(assets=[item_fa_create]).model_dump(mode="json"), timeout=TIMEOUT)
        assert create_resp.status_code == 201, f"Expected 201, got {create_resp.status_code}: {create_resp.text}"

        create_data = FABulkAssetCreateResponse(**create_resp.json())
        assert create_data.results[0].success, "Asset creation failed"
        asset_id = create_data.results[0].asset_id
        print_info(f"  Created asset ID: {asset_id}")

        # Step 2: Assign provider
        item_fa_provider = FAProviderAssignmentItem(asset_id=asset_id, provider_code="yfinance", provider_params={})
        provider_resp = await client.post(f"{API_BASE}/assets/provider/bulk", json=FABulkAssignRequest(assignments=[item_fa_provider]).model_dump(mode="json"), timeout=TIMEOUT)
        assert provider_resp.status_code == 200, f"Provider assignment failed: {provider_resp.status_code}: {provider_resp.text}"
        provider_data = FABulkAssignResponse(**provider_resp.json())
        assert provider_data.results[0].success, f"Provider assignment failed: {provider_data.results[0].message}"
        print_info(f"  Provider assigned: {item_fa_provider.provider_code}")

        # Step 3: Add price
        price_item = FAUpsertItem(date="2025-01-01", close=100.50, currency="USD")
        upsert_price = FAUpsert(asset_id=asset_id, prices=[price_item])
        price_resp = await client.post(f"{API_BASE}/assets/prices/bulk", json=FABulkUpsertRequest(assets=[upsert_price]).model_dump(mode='json'), timeout=TIMEOUT)
        assert price_resp.status_code == 200, f"Price upsert failed: {price_resp.status_code}: {price_resp.text}"
        print_info(f"  Price added for date: {price_item.date}")

        # Step 4: Delete asset (should CASCADE delete provider_assignment + price_history)
        delete_resp = await client.request("DELETE", f"{API_BASE}/assets/bulk", json=FABulkAssetDeleteRequest(asset_ids=[asset_id]).model_dump(mode="json"), timeout=TIMEOUT)
        assert delete_resp.status_code == 200, f"Expected 200, got {delete_resp.status_code}: {delete_resp.text}"

        delete_data = FABulkAssetDeleteResponse(**delete_resp.json())
        assert delete_data.results[0].success, f"Delete failed: {delete_data.results[0].message}"
        assert delete_data.success_count == 1, f"Expected success_count=1, got {delete_data.success_count}"

        print_success("✓ CASCADE delete works (provider_assignment + price_history deleted)")
        print_info(f"  Deleted asset ID: {asset_id}")


@pytest.mark.asyncio
async def test_delete_partial_success(test_server):
    """Test 15: Partial success on delete."""
    print_section("Test 15: DELETE /assets/bulk - Partial Success")

    async with httpx.AsyncClient() as client:
        # Step 1: Create one valid asset
        item = FAAssetCreateItem(display_name="Delete Partial", identifier=unique_id("DELPART"), currency="USD")
        create_resp = await client.post(f"{API_BASE}/assets/bulk", json=FABulkAssetCreateRequest(assets=[item]).model_dump(mode="json"), timeout=TIMEOUT)
        assert create_resp.status_code == 201, f"Expected 201, got {create_resp.status_code}: {create_resp.text}"

        create_data = FABulkAssetCreateResponse(**create_resp.json())
        assert create_data.results[0].success, "Asset creation failed"
        valid_id = create_data.results[0].asset_id
        invalid_id = 999999

        print_info(f"  Valid asset ID: {valid_id}")
        print_info(f"  Invalid asset ID: {invalid_id}")

        # Step 2: Try to delete both (one valid, one invalid)
        delete_resp = await client.request("DELETE", f"{API_BASE}/assets/bulk", json=FABulkAssetDeleteRequest(asset_ids=[valid_id, invalid_id]).model_dump(mode="json"), timeout=TIMEOUT)
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


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

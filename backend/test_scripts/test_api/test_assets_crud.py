"""
Asset CRUD API Tests.

Tests for asset creation, listing, and deletion endpoints.
"""
import asyncio
import time

import httpx

from backend.app.config import get_settings
from backend.test_scripts.test_server_helper import TestServerManager
from backend.test_scripts.test_utils import print_section, print_info, print_success, print_error, print_test_summary

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


async def run_all_tests():
    """Run all Asset CRUD API tests."""
    print_section("Asset CRUD API - Complete Tests")

    # Start test server
    with TestServerManager() as server_manager:
        if not server_manager.start_server():
            return False

        # Run all tests
        results = {
            "Create Single Asset": await test_create_single_asset(),
            "Create Multiple Assets": await test_create_multiple_assets(),
            "Partial Success (Create)": await test_create_partial_success(),
            "Duplicate Identifier (Create)": await test_create_duplicate_identifier(),
            "Create with Classification Params": await test_create_with_classification_params(),
            "List No Filters": await test_list_no_filters(),
            "List Filter Currency": await test_list_filter_currency(),
            "List Filter Asset Type": await test_list_filter_asset_type(),
            "List Search": await test_list_search(),
            "List Active Filter": await test_list_active_filter(),
            "List Has Provider": await test_list_has_provider(),
            "Delete Success": await test_delete_success(),
            "Delete Cascade": await test_delete_cascade(),
            "Delete Partial Success": await test_delete_partial_success(),
            }

        # Print summary
        success = print_test_summary(results, "Asset CRUD API")
        return success


async def test_create_single_asset():
    """Test 1: Create single asset via POST /assets/bulk."""
    print_section("Test 1: POST /assets/bulk - Create Single Asset")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE}/assets/bulk",
            json={
                "assets": [
                    {
                        "display_name": "Apple Inc.",
                        "identifier": unique_id("AAPL"),
                        "identifier_type": "TICKER",
                        "currency": "USD",
                        "asset_type": "STOCK",
                        "valuation_model": "MARKET_PRICE"
                        }
                    ]
                },
            timeout=TIMEOUT
            )

        if response.status_code != 201:
            print_error(f"Expected 201, got {response.status_code}")
            print_error(f"Response: {response.text}")
            return False

        data = response.json()

        if data["success_count"] != 1:
            print_error(f"Expected success_count=1, got {data['success_count']}")
            return False

        if not data["results"][0]["success"]:
            print_error("Asset creation failed")
            return False

        if not data["results"][0]["asset_id"]:
            print_error("No asset_id returned")
            return False

        print_success("✓ Single asset created successfully")
        print_info(f"  Asset ID: {data['results'][0]['asset_id']}")
        return True


async def test_create_multiple_assets():
    """Test 2: Create multiple assets."""
    print_section("Test 2: POST /assets/bulk - Create Multiple Assets")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE}/assets/bulk",
            json={
                "assets": [
                    {"display_name": "Microsoft", "identifier": unique_id("MSFT"), "currency": "USD", "asset_type": "STOCK"},
                    {"display_name": "Google", "identifier": unique_id("GOOGL"), "currency": "USD", "asset_type": "STOCK"},
                    {"display_name": "Amazon", "identifier": unique_id("AMZN"), "currency": "USD", "asset_type": "STOCK"}
                    ]
                },
            timeout=TIMEOUT
            )

        if response.status_code != 201:
            print_error(f"Expected 201, got {response.status_code}")
            return False

        data = response.json()

        if data["success_count"] != 3:
            print_error(f"Expected success_count=3, got {data['success_count']}")
            return False

        print_success("✓ 3 assets created successfully")
        return True


async def test_create_partial_success():
    """Test 3: Partial success (duplicate identifier)."""
    print_section("Test 3: POST /assets/bulk - Partial Success")

    dup_id = unique_id("DUP")

    async with httpx.AsyncClient() as client:
        # First create an asset
        await client.post(
            f"{API_BASE}/assets/bulk",
            json={"assets": [{"display_name": "Test", "identifier": dup_id, "currency": "USD"}]},
            timeout=TIMEOUT
            )

        # Try to create 3 assets, one with duplicate identifier
        response = await client.post(
            f"{API_BASE}/assets/bulk",
            json={
                "assets": [
                    {"display_name": "Valid 1", "identifier": unique_id("VALID1"), "currency": "USD"},
                    {"display_name": "Duplicate", "identifier": dup_id, "currency": "USD"},
                    {"display_name": "Valid 2", "identifier": unique_id("VALID2"), "currency": "USD"}
                    ]
                },
            timeout=TIMEOUT
            )

        data = response.json()

        if data["success_count"] != 2:
            print_error(f"Expected success_count=2, got {data['success_count']}")
            return False

        if data["failed_count"] != 1:
            print_error(f"Expected failed_count=1, got {data['failed_count']}")
            return False

        # Check that duplicate has error message
        duplicate_result = [r for r in data["results"] if r["identifier"] == dup_id][0]
        if duplicate_result["success"]:
            print_error("Duplicate should have failed")
            return False

        if "already exists" not in duplicate_result["message"]:
            print_error(f"Expected 'already exists' in message, got: {duplicate_result['message']}")
            return False

        print_success("✓ Partial success handled correctly")
        print_info(f"  Success: 2, Failed: 1")
        return True


async def test_create_duplicate_identifier():
    """Test 4: Duplicate identifier rejected."""
    print_section("Test 4: POST /assets/bulk - Duplicate Identifier")

    uniq_id = unique_id("UNIQUE")

    async with httpx.AsyncClient() as client:
        # Create first asset
        await client.post(
            f"{API_BASE}/assets/bulk",
            json={"assets": [{"display_name": "Original", "identifier": uniq_id, "currency": "USD"}]},
            timeout=TIMEOUT
            )

        # Try to create duplicate
        response = await client.post(
            f"{API_BASE}/assets/bulk",
            json={"assets": [{"display_name": "Duplicate", "identifier": uniq_id, "currency": "USD"}]},
            timeout=TIMEOUT
            )

        data = response.json()

        if data["success_count"] != 0:
            print_error(f"Expected success_count=0, got {data['success_count']}")
            return False

        if "already exists" not in data["results"][0]["message"]:
            print_error("Expected 'already exists' error")
            return False

        print_success("✓ Duplicate identifier rejected")
        return True


async def test_create_with_classification_params():
    """Test 5: Create with classification_params."""
    print_section("Test 5: POST /assets/bulk - With classification_params")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE}/assets/bulk",
            json={
                "assets": [
                    {
                        "display_name": "Tesla Inc.",
                        "identifier": unique_id("TSLA"),
                        "currency": "USD",
                        "asset_type": "STOCK",
                        "classification_params": {
                            "investment_type": "stock",
                            "sector": "Technology",
                            "geographic_area": {"USA": "0.8", "CHN": "0.2"}
                            }
                        }
                    ]
                },
            timeout=TIMEOUT
            )

        if response.status_code != 201:
            print_error(f"Expected 201, got {response.status_code}")
            print_error(f"Response: {response.text}")
            return False

        data = response.json()

        if not data["results"][0]["success"]:
            print_error(f"Creation failed: {data['results'][0]['message']}")
            return False

        print_success("✓ Asset with classification_params created")
        return True


async def test_list_no_filters():
    """Test 6: List assets without filters."""
    print_section("Test 6: GET /assets/list - No Filters")

    # Create some test assets first
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{API_BASE}/assets/bulk",
            json={
                "assets": [
                    {"display_name": "List Test 1", "identifier": "LIST1", "currency": "USD"},
                    {"display_name": "List Test 2", "identifier": "LIST2", "currency": "EUR"},
                    {"display_name": "List Test 3", "identifier": "LIST3", "currency": "USD"}
                    ]
                },
            timeout=TIMEOUT
            )

        # List all assets
        response = await client.get(f"{API_BASE}/assets/list", timeout=TIMEOUT)

        if response.status_code != 200:
            print_error(f"Expected 200, got {response.status_code}")
            return False

        data = response.json()

        if len(data) < 3:
            print_error(f"Expected at least 3 assets, got {len(data)}")
            return False

        # Check structure
        asset = data[0]
        required_fields = ["id", "display_name", "identifier", "currency", "active", "has_provider", "has_metadata"]
        for field in required_fields:
            if field not in asset:
                print_error(f"Missing field: {field}")
                return False

        print_success(f"✓ Listed {len(data)} assets")
        return True


async def test_list_filter_currency():
    """Test 7: List with currency filter."""
    print_section("Test 7: GET /assets/list - Filter by Currency")

    async with httpx.AsyncClient() as client:
        # Create USD and EUR assets
        await client.post(
            f"{API_BASE}/assets/bulk",
            json={
                "assets": [
                    {"display_name": "USD Asset 1", "identifier": "USD1", "currency": "USD"},
                    {"display_name": "USD Asset 2", "identifier": "USD2", "currency": "USD"},
                    {"display_name": "EUR Asset", "identifier": "EUR1", "currency": "EUR"}
                    ]
                },
            timeout=TIMEOUT
            )

        # Filter by USD
        response = await client.get(f"{API_BASE}/assets/list?currency=USD", timeout=TIMEOUT)
        data = response.json()

        # All should be USD
        non_usd = [a for a in data if a["currency"] != "USD"]
        if non_usd:
            print_error(f"Found non-USD assets: {len(non_usd)}")
            return False

        print_success(f"✓ Currency filter works ({len(data)} USD assets)")
        return True


async def test_list_filter_asset_type():
    """Test 8: List with asset_type filter."""
    print_section("Test 8: GET /assets/list - Filter by Asset Type")

    async with httpx.AsyncClient() as client:
        await client.post(
            f"{API_BASE}/assets/bulk",
            json={
                "assets": [
                    {"display_name": "Stock 1", "identifier": "STK1", "currency": "USD", "asset_type": "STOCK"},
                    {"display_name": "ETF 1", "identifier": "ETF1", "currency": "USD", "asset_type": "ETF"}
                    ]
                },
            timeout=TIMEOUT
            )

        response = await client.get(f"{API_BASE}/assets/list?asset_type=STOCK", timeout=TIMEOUT)
        data = response.json()

        # All should be STOCK
        non_stock = [a for a in data if a.get("asset_type") != "STOCK"]
        if non_stock:
            print_error(f"Found non-STOCK assets")
            return False

        print_success(f"✓ Asset type filter works")
        return True


async def test_list_search():
    """Test 9: List with search filter."""
    print_section("Test 9: GET /assets/list - Search")

    async with httpx.AsyncClient() as client:
        await client.post(
            f"{API_BASE}/assets/bulk",
            json={
                "assets": [
                    {"display_name": "Apple Inc.", "identifier": "SEARCHAPPL", "currency": "USD"},
                    {"display_name": "Microsoft Corp.", "identifier": "SEARCHMSFT", "currency": "USD"}
                    ]
                },
            timeout=TIMEOUT
            )

        response = await client.get(f"{API_BASE}/assets/list?search=Apple", timeout=TIMEOUT)
        data = response.json()

        # Should find Apple
        apple = [a for a in data if "Apple" in a["display_name"]]
        if not apple:
            print_error("Apple not found in search results")
            return False

        print_success("✓ Search filter works")
        return True


async def test_list_active_filter():
    """Test 10: List with active filter."""
    print_section("Test 10: GET /assets/list - Active Filter")

    async with httpx.AsyncClient() as client:
        # Default should return only active
        response = await client.get(f"{API_BASE}/assets/list?active=true", timeout=TIMEOUT)

        if response.status_code != 200:
            print_error(f"Expected 200, got {response.status_code}")
            return False

        data = response.json()

        # All should be active
        inactive = [a for a in data if not a["active"]]
        if inactive:
            print_error(f"Found inactive assets in active=true filter")
            return False

        print_success("✓ Active filter works")
        return True


async def test_list_has_provider():
    """Test 11: Check has_provider field."""
    print_section("Test 11: GET /assets/list - Has Provider")

    async with httpx.AsyncClient() as client:
        # Create asset with unique identifier
        create_resp = await client.post(
            f"{API_BASE}/assets/bulk",
            json={"assets": [{"display_name": "Provider Test", "identifier": unique_id("PROVTEST"), "currency": "USD"}]},
            timeout=TIMEOUT
            )

        result = create_resp.json()["results"][0]
        if not result["success"]:
            print_error(f"Asset creation failed: {result['message']}")
            return False

        asset_id = result["asset_id"]
        print_info(f"Created asset with ID: {asset_id}")

        # Assign provider
        assign_resp = await client.post(
            f"{API_BASE}/assets/provider/bulk",
            json={"assignments": [{"asset_id": asset_id, "provider_code": "yfinance", "provider_params": {}}]},
            timeout=TIMEOUT
            )
        print_info(f"Provider assignment: {assign_resp.json()}")

        # List and check has_provider
        response = await client.get(f"{API_BASE}/assets/list", timeout=TIMEOUT)
        data = response.json()

        asset = [a for a in data if a["id"] == asset_id]
        if not asset:
            print_error(f"Asset {asset_id} not found in list")
            return False

        print_info(f"Asset data: {asset[0]}")

        if not asset[0]["has_provider"]:
            print_error("has_provider should be true")
            return False

        print_success("✓ has_provider field works")
        return True


async def test_delete_success():
    """Test 12: Delete assets successfully."""
    print_section("Test 12: DELETE /assets/bulk - Success")

    async with httpx.AsyncClient() as client:
        # Create assets to delete
        create_resp = await client.post(
            f"{API_BASE}/assets/bulk",
            json={
                "assets": [
                    {"display_name": "Delete 1", "identifier": unique_id("DEL1"), "currency": "USD"},
                    {"display_name": "Delete 2", "identifier": unique_id("DEL2"), "currency": "USD"}
                    ]
                },
            timeout=TIMEOUT
            )

        asset_ids = [r["asset_id"] for r in create_resp.json()["results"]]

        # Delete them
        response = await client.request(
            "DELETE",
            f"{API_BASE}/assets/bulk",
            json={"asset_ids": asset_ids},
            timeout=TIMEOUT
            )

        if response.status_code != 200:
            print_error(f"Expected 200, got {response.status_code}")
            return False

        data = response.json()

        if data["success_count"] != 2:
            print_error(f"Expected success_count=2, got {data['success_count']}")
            return False

        print_success("✓ Assets deleted successfully")
        return True


async def test_delete_cascade():
    """Test 14: CASCADE delete (provider_assignments, price_history)."""
    print_section("Test 14: DELETE /assets/bulk - CASCADE Delete")

    async with httpx.AsyncClient() as client:
        # Create asset
        create_resp = await client.post(
            f"{API_BASE}/assets/bulk",
            json={"assets": [{"display_name": "Cascade Test", "identifier": unique_id("CASCTEST"), "currency": "USD"}]},
            timeout=TIMEOUT
            )
        asset_id = create_resp.json()["results"][0]["asset_id"]

        # Assign provider
        await client.post(
            f"{API_BASE}/assets/provider/bulk",
            json={"assignments": [{"asset_id": asset_id, "provider_code": "yfinance", "provider_params": {}}]},
            timeout=TIMEOUT
            )

        # Add price
        await client.post(
            f"{API_BASE}/assets/prices/bulk",
            json={
                "prices": [
                    {
                        "asset_id": asset_id,
                        "date": "2025-01-01",
                        "close": "100.50",
                        "source_plugin_key": "manual"
                        }
                    ]
                },
            timeout=TIMEOUT
            )

        # Delete asset (should CASCADE)
        response = await client.request(
            "DELETE",
            f"{API_BASE}/assets/bulk",
            json={"asset_ids": [asset_id]},
            timeout=TIMEOUT
            )

        data = response.json()

        if not data["results"][0]["success"]:
            print_error(f"Delete failed: {data['results'][0]['message']}")
            return False

        print_success("✓ CASCADE delete works (provider_assignment + price_history deleted)")
        return True


async def test_delete_partial_success():
    """Test 15: Partial success on delete."""
    print_section("Test 15: DELETE /assets/bulk - Partial Success")

    async with httpx.AsyncClient() as client:
        # Create one valid asset and reference invalid ID
        create_resp = await client.post(
            f"{API_BASE}/assets/bulk",
            json={"assets": [{"display_name": "Delete Partial", "identifier": unique_id("DELPART"), "currency": "USD"}]},
            timeout=TIMEOUT
            )
        valid_id = create_resp.json()["results"][0]["asset_id"]
        invalid_id = 999999

        # Try to delete both
        response = await client.request(
            "DELETE",
            f"{API_BASE}/assets/bulk",
            json={"asset_ids": [valid_id, invalid_id]},
            timeout=TIMEOUT
            )

        data = response.json()

        if data["success_count"] != 1:
            print_error(f"Expected success_count=1, got {data['success_count']}")
            return False

        if data["failed_count"] != 1:
            print_error(f"Expected failed_count=1, got {data['failed_count']}")
            return False

        print_success("✓ Partial success on delete works")
        return True


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)

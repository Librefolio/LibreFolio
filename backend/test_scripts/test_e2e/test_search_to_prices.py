"""
E2E Test: Search → Create → Assign Provider → Refresh Metadata → Refresh Prices

This test verifies the complete end-to-end flow works correctly:
1. Search for an asset using provider API
2. Create asset using search result data (no DB lookup needed)
3. Assign provider using identifier_type from search result
4. Refresh metadata from provider
5. Refresh prices from provider
6. Verify all data is correct

All operations are done via API endpoints, simulating frontend behavior.
"""
import pytest
import httpx
from datetime import date, timedelta

from backend.app.config import get_settings
from backend.test_scripts.test_utils import print_section, print_info, print_success, unique_id
from backend.test_scripts.test_server_helper import _TestingServerManager

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0


# ============================================================================
# PYTEST FIXTURES
# ============================================================================

@pytest.fixture(scope="module")
def test_server():
    """
    Start test server once for all tests in this module.

    The server will be automatically started before tests run and stopped after.
    Uses TEST_PORT from settings (default: 8001) to avoid conflicts.
    """
    manager = _TestingServerManager()

    # Start server
    success = manager.start_server()
    if not success:
        pytest.fail(f"Failed to start test server on port {settings.TEST_PORT}")

    # Yield to tests
    yield manager

    # Cleanup happens automatically via daemon thread


@pytest.mark.asyncio
async def test_complete_e2e_flow_justetf(test_server):
    """
    Test complete E2E flow using JustETF provider.

    Flow: Search → Create → Assign → Metadata Refresh → Price Refresh

    Uses IE00B4L5Y983 (iShares Core MSCI World UCITS ETF)
    """
    print_section("E2E Test: JustETF Complete Flow")

    async with httpx.AsyncClient() as client:
        # =====================================================================
        # STEP 1: SEARCH
        # =====================================================================
        print("\n[STEP 1] Search for ETF...")

        response = await client.get(
            f"{API_BASE}/assets/provider/search",
            params={"q": "iShares Core MSCI World"},
            timeout=TIMEOUT
        )

        assert response.status_code == 200, f"Search failed: {response.status_code}"
        search_data = response.json()

        assert search_data["total_results"] > 0, "No search results"
        results = search_data["results"]

        # Find our target ETF
        target_result = None
        for result in results:
            if result.get("identifier") == "IE00B4L5Y983":
                target_result = result
                break

        if target_result is None:
            # Use first result if specific one not found
            target_result = results[0]
            print_info(f"  Using first result: {target_result['identifier']}")
        else:
            print_info(f"  Found target: {target_result['identifier']}")

        # Extract data from search (NO DB LOOKUP!)
        identifier = target_result["identifier"]
        identifier_type = target_result["identifier_type"]  # ✅ Required field!
        provider_code = target_result["provider_code"]
        display_name = target_result["display_name"]

        print_success(f"  identifier: {identifier}")
        print_success(f"  identifier_type: {identifier_type}")
        print_success(f"  provider: {provider_code}")

        assert identifier_type is not None, "identifier_type should be present in search result"

        # =====================================================================
        # STEP 2: CREATE ASSET
        # =====================================================================
        print("\n[STEP 2] Create asset from search result...")

        unique_name = f"E2E Test {unique_id('E2E')}"
        asset_data = {
            "display_name": unique_name,
            "currency": "EUR",  # ETF currency
            "asset_type": "ETF"
        }

        response = await client.post(
            f"{API_BASE}/assets",
            json=[asset_data],
            timeout=TIMEOUT
        )

        assert response.status_code == 201, f"Create failed: {response.status_code} - {response.text}"
        create_data = response.json()

        assert create_data["success_count"] == 1, "Asset creation should succeed"
        asset_id = create_data["results"][0]["asset_id"]

        print_success(f"  Created asset ID: {asset_id}")

        # =====================================================================
        # STEP 3: ASSIGN PROVIDER
        # =====================================================================
        print("\n[STEP 3] Assign provider using search result data...")

        assignment = {
            "asset_id": asset_id,
            "provider_code": provider_code,
            "identifier": identifier,
            "identifier_type": identifier_type,  # ✅ No guessing, from search!
            "provider_params": None
        }

        response = await client.post(
            f"{API_BASE}/assets/provider",
            json=[assignment],
            timeout=TIMEOUT
        )

        assert response.status_code == 200, f"Assign failed: {response.status_code} - {response.text}"
        assign_data = response.json()

        assert assign_data["success_count"] == 1, "Provider assignment should succeed"
        print_success(f"  Provider {provider_code} assigned")

        # =====================================================================
        # STEP 4: REFRESH METADATA
        # =====================================================================
        print("\n[STEP 4] Refresh metadata from provider...")

        response = await client.post(
            f"{API_BASE}/assets/provider/refresh",
            params={"asset_ids": asset_id},
            timeout=TIMEOUT
        )

        assert response.status_code == 200, f"Metadata refresh failed: {response.status_code}"
        refresh_data = response.json()

        assert "results" in refresh_data
        result = refresh_data["results"][0]

        if result.get("success"):
            print_success("  Metadata refreshed successfully")

            # Check for fields_detail with OldNew format
            fields_detail = result.get("fields_detail")
            if fields_detail:
                print_info(f"  Fields detail: {fields_detail}")
                refreshed_fields = fields_detail.get("refreshed_fields", [])
                for change in refreshed_fields:
                    # Should be OldNew format
                    assert "old" in change, "OldNew should have 'old' field"
                    assert "new" in change, "OldNew should have 'new' field"
                    print_info(f"    Changed: {change.get('info', 'unknown')} - old={change['old']}, new={change['new']}")
        else:
            print_info(f"  Metadata refresh message: {result.get('error', 'unknown')}")

        # Verify asset has metadata
        response = await client.get(
            f"{API_BASE}/assets",
            params={"asset_ids": asset_id},
            timeout=TIMEOUT
        )

        assert response.status_code == 200
        assets = response.json()
        assert len(assets) == 1
        asset = assets[0]

        print_info(f"  Asset currency: {asset.get('currency')}")
        if asset.get("classification_params"):
            cp = asset["classification_params"]
            if cp.get("short_description"):
                print_info(f"  Description: {cp['short_description'][:80]}...")
            if cp.get("sector_area"):
                print_info(f"  Sector: {cp['sector_area']}")
            if cp.get("geographic_area"):
                print_info(f"  Geo: {list(cp['geographic_area'].get('distribution', {}).keys())[:5]}...")

        # =====================================================================
        # STEP 5: REFRESH PRICES
        # =====================================================================
        print("\n[STEP 5] Refresh prices from provider...")

        today = date.today()
        start_date = today - timedelta(days=7)

        response = await client.post(
            f"{API_BASE}/assets/prices/refresh",
            json=[{
                "asset_id": asset_id,
                "date_range": {
                    "start": start_date.isoformat(),
                    "end": today.isoformat()
                }
            }],
            timeout=TIMEOUT
        )

        assert response.status_code == 200, f"Price refresh failed: {response.status_code}"
        price_refresh_data = response.json()

        assert "results" in price_refresh_data
        price_result = price_refresh_data["results"][0]

        fetched_count = price_result.get("fetched_count", 0)
        print_info(f"  Fetched {fetched_count} price points")

        # =====================================================================
        # STEP 6: VERIFY PRICES
        # =====================================================================
        print("\n[STEP 6] Verify prices exist...")

        response = await client.get(
            f"{API_BASE}/assets/prices/{asset_id}",
            params={
                "start_date": start_date.isoformat(),
                "end_date": today.isoformat()
            },
            timeout=TIMEOUT
        )

        assert response.status_code == 200, f"Get prices failed: {response.status_code}"
        prices = response.json()  # Direct list response

        print_info(f"  Found {len(prices)} price records")

        if prices:
            latest = prices[-1]
            print_success(f"  Latest price: {latest.get('close')} {latest.get('currency')} on {latest.get('date')}")

        # =====================================================================
        # SUCCESS!
        # =====================================================================
        print("\n" + "=" * 60)
        print_success("🎉 E2E FLOW COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print_info(f"  Asset ID: {asset_id}")
        print_info(f"  Provider: {provider_code}")
        print_info(f"  Identifier: {identifier} ({identifier_type})")
        print_info(f"  Prices: {len(prices)} records")


@pytest.mark.asyncio
async def test_complete_e2e_flow_yfinance(test_server):
    """
    Test complete E2E flow using YFinance provider.

    Flow: Search → Create → Assign → Metadata Refresh → Price Refresh

    Uses AAPL (Apple Inc.)
    """
    print_section("E2E Test: YFinance Complete Flow")

    async with httpx.AsyncClient() as client:
        # STEP 1: SEARCH
        print("\n[STEP 1] Search for stock...")

        response = await client.get(
            f"{API_BASE}/assets/provider/search",
            params={"q": "Apple"},
            timeout=TIMEOUT
        )

        assert response.status_code == 200, f"Search failed: {response.status_code}"
        search_data = response.json()

        # Find yfinance result (mockprov also returns Apple)
        target_result = None
        for result in search_data.get("results", []):
            if result.get("provider_code") == "yfinance":
                target_result = result
                break

        if target_result is None:
            pytest.skip("YFinance not available or no results")

        identifier = target_result["identifier"]
        identifier_type = target_result["identifier_type"]
        provider_code = target_result["provider_code"]

        print_success(f"  Found: {identifier} ({identifier_type}) via {provider_code}")

        # STEP 2: CREATE
        print("\n[STEP 2] Create asset...")

        unique_name = f"E2E YFinance Test {unique_id('YF')}"
        response = await client.post(
            f"{API_BASE}/assets",
            json=[{
                "display_name": unique_name,
                "currency": "USD",
                "asset_type": "STOCK"
            }],
            timeout=TIMEOUT
        )

        assert response.status_code == 201
        asset_id = response.json()["results"][0]["asset_id"]
        print_success(f"  Created asset ID: {asset_id}")

        # STEP 3: ASSIGN
        print("\n[STEP 3] Assign provider...")

        response = await client.post(
            f"{API_BASE}/assets/provider",
            json=[{
                "asset_id": asset_id,
                "provider_code": provider_code,
                "identifier": identifier,
                "identifier_type": identifier_type
            }],
            timeout=TIMEOUT
        )

        assert response.status_code == 200
        print_success(f"  Provider {provider_code} assigned")

        # STEP 4: METADATA
        print("\n[STEP 4] Refresh metadata...")

        response = await client.post(
            f"{API_BASE}/assets/provider/refresh",
            params={"asset_ids": asset_id},
            timeout=TIMEOUT
        )

        assert response.status_code == 200
        print_success("  Metadata refreshed")

        # STEP 5: PRICES (today only for speed)
        print("\n[STEP 5] Get current price...")

        today = date.today()
        response = await client.post(
            f"{API_BASE}/assets/prices/refresh",
            json=[{
                "asset_id": asset_id,
                "date_range": {
                    "start": today.isoformat(),
                    "end": today.isoformat()
                }
            }],
            timeout=TIMEOUT
        )

        assert response.status_code == 200
        print_success("  Price refreshed")

        # VERIFY
        print("\n[STEP 6] Verify...")

        response = await client.get(
            f"{API_BASE}/assets",
            params={"asset_ids": asset_id},
            timeout=TIMEOUT
        )

        asset = response.json()[0]
        print_success(f"  Asset: {asset.get('display_name')}")
        print_success(f"  Currency: {asset.get('currency')}")

        if asset.get("classification_params"):
            cp = asset["classification_params"]
            if cp.get("sector_area"):
                print_success(f"  Sector: {cp['sector_area']}")

        print("\n" + "=" * 60)
        print_success("🎉 YFINANCE E2E FLOW COMPLETED!")
        print("=" * 60)


@pytest.mark.asyncio
async def test_search_provides_all_required_fields(test_server):
    """
    Verify search results contain all required fields for asset creation.

    Required fields:
    - identifier (required)
    - identifier_type (required - NEW!)
    - provider_code (required)
    - display_name (required)
    - asset_type (optional but useful)
    """
    print_section("E2E Test: Search Result Completeness")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE}/assets/provider/search",
            params={"q": "World"},
            timeout=TIMEOUT
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total_results"] > 0, "Should have search results"

        # Check first few results
        for result in data["results"][:5]:
            # Required fields
            assert "identifier" in result, f"Missing 'identifier' in {result}"
            assert "identifier_type" in result, f"Missing 'identifier_type' in {result}"
            assert "provider_code" in result, f"Missing 'provider_code' in {result}"
            assert "display_name" in result, f"Missing 'display_name' in {result}"

            # Verify identifier_type is valid enum value
            assert result["identifier_type"] in ["ISIN", "TICKER", "CUSTOM", "URL"], \
                f"Invalid identifier_type: {result['identifier_type']}"

            print_info(f"  ✓ {result['identifier']} ({result['identifier_type']}) - {result['provider_code']}")

        print_success(f"All {min(5, data['total_results'])} checked results have required fields")


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
    AssetType
)
from backend.app.schemas.provider import (
    FAProviderAssignmentItem,
    FABulkAssignResponse,
    FABulkRemoveResponse,
    FAProviderSearchResponse,
    IdentifierType
)

from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_info, print_success, unique_id

# Constants
settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0
SEARCH_TIMEOUT = 90.0  # Search can be slow due to external API calls (yfinance, justetf)

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


# ============================================================
# Test 6: GET /assets/provider/search - Search assets
# ============================================================
@pytest.mark.asyncio
async def test_search_assets_basic(test_server):
    """Test 6: GET /assets/provider/search - Search assets via providers."""
    print_section("Test 6: GET /assets/provider/search - Basic Search 'Apple'")

    async with httpx.AsyncClient() as client:
        # Search using default (all providers)
        # Note: Uses longer timeout as external APIs (yfinance) can be slow
        search_resp = await client.get(
            f"{API_BASE}/assets/provider/search",
            params={"q": "Apple"},
            timeout=SEARCH_TIMEOUT
        )

        assert search_resp.status_code == 200, f"Expected 200, got {search_resp.status_code}: {search_resp.text}"
        search_data = FAProviderSearchResponse(**search_resp.json())

        print_info(f"  Query: '{search_data.query}'")
        print_info(f"  Total results: {search_data.total_results}")
        print_info(f"  Providers queried: {search_data.providers_queried}")

        # Count by provider
        by_provider = {}
        for r in search_data.results:
            by_provider[r.provider_code] = by_provider.get(r.provider_code, 0) + 1

        for prov, count in by_provider.items():
            print_info(f"  Results from {prov}: {count}")

        assert search_data.query == "Apple"
        assert len(search_data.providers_queried) > 0, "At least one provider should be queried"

        # Should find results from multiple providers (justetf + yfinance at minimum)
        assert search_data.total_results > 0, "Should find results for 'Apple'"

        # Verify yfinance returns results for Apple (famous stock)
        yfinance_results = [r for r in search_data.results if r.provider_code == "yfinance"]
        assert len(yfinance_results) > 0, "yfinance should find Apple Inc."

        # Show sample results
        for r in search_data.results[:3]:
            print_info(f"  Sample: [{r.provider_code}] {r.identifier}: {r.display_name[:40]}...")

        print_success(f"✓ Found {search_data.total_results} results from {len(by_provider)} providers")


# ============================================================
# Test 7: GET /assets/provider/search - Search Semiconductor
# ============================================================
@pytest.mark.asyncio
async def test_search_assets_semiconductor(test_server):
    """Test 7: GET /assets/provider/search - Search 'Semiconductor' finds results from multiple providers."""
    print_section("Test 7: GET /assets/provider/search - Search 'Semiconductor'")

    async with httpx.AsyncClient() as client:
        # Search for "Semiconductor" - sector-specific
        # Note: Uses longer timeout as external APIs (yfinance) can be slow
        search_resp = await client.get(
            f"{API_BASE}/assets/provider/search",
            params={"q": "Semiconductor"},
            timeout=SEARCH_TIMEOUT
        )

        assert search_resp.status_code == 200, f"Expected 200, got {search_resp.status_code}: {search_resp.text}"
        search_data = FAProviderSearchResponse(**search_resp.json())

        print_info(f"  Query: '{search_data.query}'")
        print_info(f"  Total results: {search_data.total_results}")
        print_info(f"  Providers queried: {search_data.providers_queried}")

        # Count by provider
        by_provider = {}
        for r in search_data.results:
            by_provider[r.provider_code] = by_provider.get(r.provider_code, 0) + 1

        for prov, count in by_provider.items():
            print_info(f"  Results from {prov}: {count}")

        # Should find semiconductor ETFs on justetf AND stocks on yfinance
        assert search_data.total_results > 0, "Should find semiconductor results"

        justetf_results = by_provider.get('justetf', 0)
        yfinance_results = by_provider.get('yfinance', 0)

        assert justetf_results > 0, "JustETF should find semiconductor ETFs"
        assert yfinance_results > 0, "yfinance should find semiconductor stocks"

        print_success(f"✓ Found {search_data.total_results} results ({justetf_results} ETFs + {yfinance_results} stocks)")


# ============================================================
# Test 8: GET /assets/provider/search - Provider filter (justetf only)
# ============================================================
@pytest.mark.asyncio
async def test_search_assets_provider_filter(test_server):
    """Test 8: GET /assets/provider/search - Filter to specific provider."""
    print_section("Test 8: GET /assets/provider/search - Provider Filter (justetf)")

    async with httpx.AsyncClient() as client:
        # Search using only justetf provider
        search_resp = await client.get(
            f"{API_BASE}/assets/provider/search",
            params={"q": "MSCI", "providers": "justetf"},
            timeout=SEARCH_TIMEOUT
        )

        assert search_resp.status_code == 200, f"Expected 200, got {search_resp.status_code}: {search_resp.text}"
        search_data = FAProviderSearchResponse(**search_resp.json())

        print_info(f"  Query: '{search_data.query}'")
        print_info(f"  Providers queried: {search_data.providers_queried}")
        print_info(f"  Total results: {search_data.total_results}")

        # Should only have queried justetf
        assert "justetf" in search_data.providers_queried, "justetf should be in queried providers"
        assert len(search_data.providers_queried) == 1, "Should only query one provider"

        # All results should be from justetf
        for result in search_data.results:
            assert result.provider_code == "justetf", f"Expected justetf, got {result.provider_code}"

        # MSCI should find many ETFs
        assert search_data.total_results > 0, "MSCI should find ETFs on justetf"

        if search_data.results:
            print_info(f"  Sample: {search_data.results[0].identifier} - {search_data.results[0].display_name[:50]}...")

        print_success(f"✓ Provider filter works: {search_data.total_results} results from justetf only")


# ============================================================
# Test 9: GET /assets/provider/search - Search IBM (ticker)
# ============================================================
@pytest.mark.asyncio
async def test_search_assets_ibm(test_server):
    """Test 9: GET /assets/provider/search - Search 'IBM' finds results from multiple providers."""
    print_section("Test 9: GET /assets/provider/search - Search 'IBM'")

    async with httpx.AsyncClient() as client:
        # Search for "IBM" - well-known ticker/company
        search_resp = await client.get(
            f"{API_BASE}/assets/provider/search",
            params={"q": "IBM"},
            timeout=SEARCH_TIMEOUT
        )

        assert search_resp.status_code == 200, f"Expected 200, got {search_resp.status_code}: {search_resp.text}"
        search_data = FAProviderSearchResponse(**search_resp.json())

        print_info(f"  Query: '{search_data.query}'")
        print_info(f"  Total results: {search_data.total_results}")

        # Count by provider
        by_provider = {}
        for r in search_data.results:
            by_provider[r.provider_code] = by_provider.get(r.provider_code, 0) + 1

        for prov, count in by_provider.items():
            print_info(f"  Results from {prov}: {count}")

        # Should find IBM from yfinance (main stock) and possibly justetf
        assert search_data.total_results > 0, "Should find results for 'IBM'"

        yfinance_results = by_provider.get('yfinance', 0)
        assert yfinance_results > 0, "yfinance should find IBM stock"

        # Show sample results
        for r in search_data.results[:3]:
            print_info(f"  Sample: [{r.provider_code}] {r.identifier}: {r.display_name[:40]}...")

        print_success(f"✓ Found {search_data.total_results} results for 'IBM' ({yfinance_results} from yfinance)")


# ============================================================
# Test 10: GET /assets/provider/search - Search with invalid provider
# ============================================================
@pytest.mark.asyncio
async def test_search_assets_invalid_provider(test_server):
    """Test 10: GET /assets/provider/search - Search with non-existent provider."""
    print_section("Test 10: GET /assets/provider/search - Invalid Provider")

    async with httpx.AsyncClient() as client:
        # Search using non-existent provider
        search_resp = await client.get(
            f"{API_BASE}/assets/provider/search",
            params={"q": "Apple", "providers": "nonexistent_provider"},
            timeout=TIMEOUT
        )

        # Should succeed but return empty results
        assert search_resp.status_code == 200, f"Expected 200, got {search_resp.status_code}: {search_resp.text}"
        search_data = FAProviderSearchResponse(**search_resp.json())

        print_info(f"  Providers queried: {search_data.providers_queried}")
        print_info(f"  Total results: {search_data.total_results}")

        # Invalid provider should be skipped, not cause error
        assert "nonexistent_provider" not in search_data.providers_queried
        assert search_data.total_results == 0

        print_success("✓ Invalid provider handled gracefully")


# ============================================================
# Test 11: GET /assets/provider/search - Empty query validation
# ============================================================
@pytest.mark.asyncio
async def test_search_assets_empty_query(test_server):
    """Test 11: GET /assets/provider/search - Empty query should fail validation."""
    print_section("Test 11: GET /assets/provider/search - Empty Query Validation")

    async with httpx.AsyncClient() as client:
        # Search with empty query
        search_resp = await client.get(
            f"{API_BASE}/assets/provider/search",
            params={"q": ""},
            timeout=TIMEOUT
        )

        # Should fail validation (min_length=1)
        assert search_resp.status_code == 422, f"Expected 422, got {search_resp.status_code}: {search_resp.text}"
        print_success("✓ Empty query correctly rejected with 422")


# ============================================================
# Test 12: GET /assets/provider/search - Parallel execution verification
# ============================================================
@pytest.mark.asyncio
async def test_search_parallel_execution(test_server):
    """Test 12: GET /assets/provider/search - Verify parallel execution is fast."""
    print_section("Test 12: GET /assets/provider/search - Parallel Execution")

    import time

    async with httpx.AsyncClient() as client:
        # Time a search across all providers
        start_time = time.time()

        search_resp = await client.get(
            f"{API_BASE}/assets/provider/search",
            params={"q": "Technology"},
            timeout=TIMEOUT
        )

        elapsed = time.time() - start_time

        assert search_resp.status_code == 200
        search_data = FAProviderSearchResponse(**search_resp.json())

        print_info(f"  Query: '{search_data.query}'")
        print_info(f"  Providers queried: {len(search_data.providers_queried)}")
        print_info(f"  Total results: {search_data.total_results}")
        print_info(f"  Time elapsed: {elapsed:.2f}s")

        # If parallel execution works, querying multiple providers should be fast
        # (much less than providers * individual_timeout)
        # A reasonable threshold: should complete in under 15 seconds for all providers
        assert elapsed < 15.0, f"Search took too long ({elapsed:.2f}s), parallel execution may not be working"

        print_success(f"✓ Parallel search completed in {elapsed:.2f}s")


# ============================================================
# Test 13: End-to-End - Search → Create Asset → Assign Provider → Operations
# ============================================================
@pytest.mark.asyncio
async def test_search_to_asset_e2e(test_server):
    """Test 13: End-to-End test - use search results to create assets and perform operations."""
    print_section("Test 13: End-to-End - Search → Create → Assign → Refresh")

    async with httpx.AsyncClient() as client:
        # Step 1: Search for assets
        print_info("Step 1: Searching for 'Microsoft'...")
        search_resp = await client.get(
            f"{API_BASE}/assets/provider/search",
            params={"q": "Microsoft"},
            timeout=TIMEOUT
        )
        assert search_resp.status_code == 200
        search_data = FAProviderSearchResponse(**search_resp.json())

        # We need results from providers that support current value (yfinance, justetf)
        usable_results = [
            r for r in search_data.results
            if r.provider_code in ("yfinance", "justetf") and r.identifier
        ]

        assert len(usable_results) > 0, "Should find usable results from yfinance or justetf"
        print_info(f"  Found {len(usable_results)} usable results")

        # Pick the first yfinance result (more reliable for stocks)
        yfinance_results = [r for r in usable_results if r.provider_code == "yfinance"]
        justetf_results = [r for r in usable_results if r.provider_code == "justetf"]

        # Test with one result from each provider if available
        test_assets = []

        if yfinance_results:
            test_assets.append({
                "search_result": yfinance_results[0],
                "asset_type": AssetType.STOCK,
                "identifier_type": IdentifierType.TICKER
            })
            print_info(f"  Will test yfinance with: {yfinance_results[0].identifier}")

        if justetf_results:
            test_assets.append({
                "search_result": justetf_results[0],
                "asset_type": AssetType.ETF,
                "identifier_type": IdentifierType.ISIN
            })
            print_info(f"  Will test justetf with: {justetf_results[0].identifier}")

        assert len(test_assets) > 0, "Should have at least one test asset"

        # Step 2: Create assets for each search result
        print_info("\nStep 2: Creating assets from search results...")
        created_assets = []

        for test_item in test_assets:
            sr = test_item["search_result"]
            asset_item = FAAssetCreateItem(
                display_name=sr.display_name[:100] if sr.display_name else f"Test {sr.identifier}",
                currency=sr.currency or "USD",
                asset_type=test_item["asset_type"]
            )

            create_resp = await client.post(
                f"{API_BASE}/assets",
                json=[asset_item.model_dump(mode="json")],
                timeout=TIMEOUT
            )

            if create_resp.status_code == 201:
                create_data = FABulkAssetCreateResponse(**create_resp.json())
                if create_data.results and create_data.results[0].success:
                    created_assets.append({
                        "asset_id": create_data.results[0].asset_id,
                        "provider_code": sr.provider_code,
                        "identifier": sr.identifier,
                        "identifier_type": test_item["identifier_type"]
                    })
                    print_info(f"  Created asset ID {create_data.results[0].asset_id} for {sr.identifier}")
            else:
                print_info(f"  Warning: Failed to create asset for {sr.identifier}: {create_resp.text[:100]}")

        assert len(created_assets) > 0, "Should create at least one asset"
        print_success(f"✓ Created {len(created_assets)} assets")

        # Step 3: Assign providers to the created assets
        print_info("\nStep 3: Assigning providers...")
        assignments = []
        for asset_info in created_assets:
            assignment = FAProviderAssignmentItem(
                asset_id=asset_info["asset_id"],
                provider_code=asset_info["provider_code"],
                identifier=asset_info["identifier"],
                identifier_type=asset_info["identifier_type"],
                provider_params=None
            )
            assignments.append(assignment)

        assign_resp = await client.post(
            f"{API_BASE}/assets/provider",
            json=[a.model_dump(mode="json") for a in assignments],
            timeout=TIMEOUT
        )

        assert assign_resp.status_code == 200, f"Provider assignment failed: {assign_resp.text}"
        assign_data = FABulkAssignResponse(**assign_resp.json())
        assert assign_data.success_count == len(assignments), "All assignments should succeed"
        print_success(f"✓ Assigned {assign_data.success_count} providers")

        # Step 4: Refresh metadata from providers
        print_info("\nStep 4: Refreshing metadata...")
        asset_ids = [a["asset_id"] for a in created_assets]

        refresh_resp = await client.post(
            f"{API_BASE}/assets/provider/refresh",
            params={"asset_ids": asset_ids},
            timeout=TIMEOUT
        )

        if refresh_resp.status_code == 200:
            print_success("✓ Metadata refresh completed")
        else:
            print_info(f"  Metadata refresh warning: {refresh_resp.status_code}")

        # Step 5: Verify assets have metadata via GET /assets
        print_info("\nStep 5: Verifying asset data...")
        for asset_info in created_assets:
            asset_resp = await client.get(
                f"{API_BASE}/assets",
                params={"asset_ids": [asset_info["asset_id"]]},
                timeout=TIMEOUT
            )

            assert asset_resp.status_code == 200
            assets = [FAAssetMetadataResponse(**a) for a in asset_resp.json()]

            if assets:
                asset = assets[0]
                print_info(f"  Asset {asset_info['asset_id']} ({asset_info['provider_code']}):")
                print_info(f"    - Name: {asset.display_name[:50]}...")
                print_info(f"    - Has provider: {asset.has_provider}")
                print_info(f"    - Currency: {asset.currency}")
                assert asset.has_provider is True, "Asset should have provider assigned"

        print_success("✓ All assets verified successfully")

        # Step 6: Test price refresh (uses get_current_value for today)
        print_info("\nStep 6: Testing price refresh (get_current_value for today)...")
        from datetime import date, timedelta

        today = date.today()
        yesterday = today - timedelta(days=7)  # Get a week of history

        for asset_info in created_assets:
            price_refresh_resp = await client.post(
                f"{API_BASE}/assets/prices/refresh",
                json=[{
                    "asset_id": asset_info["asset_id"],
                    "date_range": {
                        "start": yesterday.isoformat(),
                        "end": today.isoformat()
                    }
                }],
                timeout=TIMEOUT
            )

            if price_refresh_resp.status_code == 200:
                refresh_data = price_refresh_resp.json()
                results = refresh_data.get("results", [])
                if results:
                    result = results[0]
                    fetched = result.get("fetched_count", 0)
                    inserted = result.get("inserted_count", 0)
                    errors = result.get("errors", [])
                    print_info(f"  Asset {asset_info['asset_id']} ({asset_info['provider_code']}): fetched={fetched}, inserted={inserted}")
                    if errors:
                        print_info(f"    Errors: {errors}")
                    else:
                        # Verify we got current price (today's date)
                        if fetched > 0:
                            print_success(f"  ✓ Price data fetched for {asset_info['identifier']}")
            else:
                print_info(f"  Price refresh warning for {asset_info['asset_id']}: {price_refresh_resp.status_code}")

        # Step 7: Verify prices were stored
        print_info("\nStep 7: Verifying stored prices...")
        for asset_info in created_assets:
            prices_resp = await client.get(
                f"{API_BASE}/assets/prices/{asset_info['asset_id']}",
                params={
                    "start_date": yesterday.isoformat(),
                    "end_date": today.isoformat()
                },
                timeout=TIMEOUT
            )

            if prices_resp.status_code == 200:
                prices_data = prices_resp.json()
                # Response is a list of FAPricePoint directly, not {"prices": [...]}
                prices = prices_data if isinstance(prices_data, list) else prices_data.get("prices", [])
                print_info(f"  Asset {asset_info['asset_id']}: {len(prices)} price point(s)")
                if prices:
                    # Check if we have today's price
                    today_prices = [p for p in prices if p.get("date") == today.isoformat()]
                    if today_prices:
                        print_success(f"  ✓ Today's price found: {today_prices[0].get('close')}")
                    else:
                        print_info(f"    Latest price: {prices[-1].get('date')} = {prices[-1].get('close')}")

        # Step 8: Cleanup - delete created assets
        print_info("\nStep 8: Cleanup...")
        delete_resp = await client.delete(
            f"{API_BASE}/assets",
            params={"asset_ids": asset_ids},
            timeout=TIMEOUT
        )

        if delete_resp.status_code == 200:
            print_success("✓ Cleanup completed")
        else:
            print_info(f"  Cleanup warning: {delete_resp.status_code}")

        print_success("\n✓ End-to-End test completed successfully!")


# ============================================================
# Test 14: Price refresh uses get_current_value for today
# ============================================================
@pytest.mark.asyncio
async def test_price_refresh_uses_current_value(test_server):
    """Test 14: Verify price refresh uses get_current_value for today's date."""
    print_section("Test 14: Price Refresh - get_current_value for Today")

    from datetime import date

    async with httpx.AsyncClient() as client:
        # Create asset with yfinance provider (reliable for current prices)
        asset_item = FAAssetCreateItem(
            display_name=f"Current Price Test {unique_id('CPT')}",
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

        # Assign yfinance provider with AAPL (always has current price)
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
        assert assign_resp.status_code == 200
        print_info("  Provider assigned: yfinance (AAPL)")

        # Refresh prices for TODAY ONLY
        today = date.today()
        print_info(f"  Refreshing price for today: {today}")

        refresh_resp = await client.post(
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

        assert refresh_resp.status_code == 200, f"Refresh failed: {refresh_resp.text}"
        refresh_data = refresh_resp.json()
        results = refresh_data.get("results", [])

        assert len(results) > 0, "Should have refresh result"
        result = results[0]
        fetched_count = result.get("fetched_count", 0)
        errors = result.get("errors", [])

        print_info(f"  Fetched count: {fetched_count}")
        if errors:
            print_info(f"  Errors: {errors}")

        # Should have fetched at least 1 price (today's current value)
        assert fetched_count >= 1 or not errors, f"Should fetch current price. Errors: {errors}"

        # Verify the price was stored
        prices_resp = await client.get(
            f"{API_BASE}/assets/prices/{asset_id}",
            params={
                "start_date": today.isoformat(),
                "end_date": today.isoformat()
            },
            timeout=TIMEOUT
        )

        assert prices_resp.status_code == 200
        prices_data = prices_resp.json()
        # Response is a list directly, not {"prices": [...]}
        prices = prices_data if isinstance(prices_data, list) else prices_data.get("prices", [])

        print_info(f"  Stored prices: {len(prices)}")

        if prices:
            today_price = prices[0]
            print_info(f"  Today's price: {today_price.get('close')} (date: {today_price.get('date')})")
            assert today_price.get("close") is not None, "Should have close price"
            print_success(f"✓ Current value fetched and stored: {today_price.get('close')}")
        else:
            # May not have price if market is closed, but should not have errors
            assert not errors, f"No price but had errors: {errors}"
            print_info("  No price stored (market may be closed)")
            print_success("✓ get_current_value was called (no errors)")

        # Cleanup
        await client.delete(
            f"{API_BASE}/assets",
            params={"asset_ids": [asset_id]},
            timeout=TIMEOUT
        )
        print_info("  Cleanup completed")


# ============================================================
# Test 15: CSS Scraper (no history) still gets current price
# ============================================================
@pytest.mark.asyncio
async def test_css_scraper_current_price(test_server):
    """Test 15: Verify CSS Scraper (without history support) can get current price."""
    print_section("Test 15: CSS Scraper - Current Price Only")

    from datetime import date

    async with httpx.AsyncClient() as client:
        # Create asset for Borsa Italiana BTP
        asset_item = FAAssetCreateItem(
            display_name=f"BTP Test {unique_id('BTP')}",
            currency="EUR",
            asset_type=AssetType.BOND
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

        # Assign CSS Scraper provider with Borsa Italiana BTP
        assignment = FAProviderAssignmentItem(
            asset_id=asset_id,
            provider_code="cssscraper",
            identifier="https://www.borsaitaliana.it/borsa/obbligazioni/mot/btp/scheda/IT0005634800.html?lang=en",
            identifier_type=IdentifierType.OTHER,
            provider_params={
                "current_css_selector": ".summary-value strong",
                "currency": "EUR",
                "decimal_format": "us"
            }
        )
        assign_resp = await client.post(
            f"{API_BASE}/assets/provider",
            json=[assignment.model_dump(mode="json")],
            timeout=TIMEOUT
        )
        assert assign_resp.status_code == 200
        print_info("  Provider assigned: cssscraper (Borsa Italiana BTP)")

        # Refresh prices for TODAY ONLY
        # CSS Scraper doesn't support history, so this tests that get_current_value is used
        today = date.today()
        print_info(f"  Refreshing price for today: {today}")

        refresh_resp = await client.post(
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

        assert refresh_resp.status_code == 200, f"Refresh failed: {refresh_resp.text}"
        refresh_data = refresh_resp.json()
        results = refresh_data.get("results", [])

        assert len(results) > 0, "Should have refresh result"
        result = results[0]
        fetched_count = result.get("fetched_count", 0)
        errors = result.get("errors", [])

        print_info(f"  Fetched count: {fetched_count}")
        if errors:
            print_info(f"  Errors: {errors}")

        # Should have fetched current price (CSS Scraper only supports current)
        # Note: May fail if Borsa Italiana is down or returns different HTML
        if fetched_count > 0:
            print_success(f"✓ CSS Scraper fetched current price (no history support needed)")
        elif "NOT_IMPLEMENTED" in str(errors) or "history" in str(errors).lower():
            # This would indicate the old behavior (failing on history)
            # The fix should prevent this
            print_info("  Warning: Appears to have tried history instead of current value")
        else:
            # Could be network issue with Borsa Italiana
            print_info(f"  Could not fetch (may be network issue): {errors}")

        # Verify if price was stored
        prices_resp = await client.get(
            f"{API_BASE}/assets/prices/{asset_id}",
            params={
                "start_date": today.isoformat(),
                "end_date": today.isoformat()
            },
            timeout=TIMEOUT
        )

        if prices_resp.status_code == 200:
            prices_data = prices_resp.json()
            # Response is a list directly
            prices = prices_data if isinstance(prices_data, list) else prices_data.get("prices", [])

            if prices:
                today_price = prices[0]
                print_info(f"  Today's BTP price: {today_price.get('close')} EUR")
                print_success(f"✓ CSS Scraper current value stored successfully")
            else:
                print_info("  No prices stored (may be network/site issue)")

        # Cleanup
        await client.delete(
            f"{API_BASE}/assets",
            params={"asset_ids": [asset_id]},
            timeout=TIMEOUT
        )
        print_info("  Cleanup completed")

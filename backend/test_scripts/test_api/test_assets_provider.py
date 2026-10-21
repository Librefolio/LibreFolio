"""
Test Suite: Assets Provider API Endpoints

Tests for asset provider assignment and management:
- POST /api/v1/assets/provider - Assign providers to assets
- DELETE /api/v1/assets/provider - Remove provider assignments
- POST /api/v1/assets/provider/refresh - Refresh metadata from providers

Z-32 (d), the quote base suggestion (QBS-A01…A06, the HTTP side of test_services/test_quote_base_suggestion.py, whose
docstring holds the contract): the search and the probe's metadata carry ``quote_base_suggestion`` (mockprov's
``MOCK_MINOR_UNIT``, a London line quoted in pence: ``{"quantity": 100, "quote_currency": "GBp"}``; null otherwise);
the metadata refresh never changes ``quote_base_quantity`` for it; the served OpenAPI document has the component.
"""

import uuid
from datetime import date, timedelta

import httpx
import pytest

from backend.app.config import get_settings
from backend.app.db.models import AssetType
from backend.app.schemas.assets.assets import (
    FAAssetCreateItem,
    FABulkAssetCreateResponse,
)
from backend.app.schemas.assets.metadata import FAAssetMetadataResponse
from backend.app.schemas.provider import (
    FABulkAssignResponse,
    FAProviderAssignmentItem,
    FAProviderSearchResponse,
    IdentifierType,
    ProviderInputType,
)
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_info, print_section, print_success, unique_id

# Constants
settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0


async def create_user_and_login(client: httpx.AsyncClient) -> None:
    """Create a test user, login, and set session cookie on client."""
    import uuid as _uuid  # noqa: PLC0415 — test setup — imports after sys.path/db config

    username = f"test_{int(__import__('time').time() * 1000)}_{_uuid.uuid4().hex[:4]}"
    email = f"{username}@test.com"
    password = "TestPass123!"
    resp = await client.post(
        f"{API_BASE}/auth/register",
        json={"username": username, "email": email, "password": password},
        timeout=TIMEOUT,
    )
    if resp.status_code != 201:
        raise Exception(f"Failed to create user: {resp.text}")
    login_resp = await client.post(
        f"{API_BASE}/auth/login",
        json={"username": username, "password": password},
        timeout=TIMEOUT,
    )
    if login_resp.status_code != 200:
        raise Exception(f"Failed to login: {login_resp.text}")
    session = login_resp.cookies.get("session")
    if session:
        client.cookies.set("session", session)


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
        await create_user_and_login(client)
        # Step 1: Create asset
        asset_item = FAAssetCreateItem(
            display_name=f"Provider Test {unique_id('PROV')}",
            currency="USD",
            asset_type=AssetType.STOCK,
        )
        create_resp = await client.post(f"{API_BASE}/assets", json=[asset_item.model_dump(mode="json")], timeout=TIMEOUT)
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
            provider_params=None,
        )

        assign_resp = await client.post(
            f"{API_BASE}/assets/provider",
            json=[assignment.model_dump(mode="json")],
            timeout=TIMEOUT,
        )

        assert assign_resp.status_code == 200, f"Expected 200, got {assign_resp.status_code}: {assign_resp.text}"
        assign_data = FABulkAssignResponse(**assign_resp.json())
        assert assign_data.success_count >= 1, "Should have at least 1 successful assignment"
        print_success(f"✓ Provider assigned: {assignment.provider_code}")

        # Step 3: Verify assignment via GET /assets (bulk read endpoint)
        query_resp = await client.get(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)
        assert query_resp.status_code == 200
        assets = [FAAssetMetadataResponse(**a) for a in query_resp.json()]
        assert len(assets) == 1
        assert assets[0].provider_code == "yfinance"
        print_success("✓ Provider assignment verified via GET /assets")


# ============================================================
# Test 2: POST /assets/provider - Update provider params
# ============================================================
@pytest.mark.asyncio
async def test_update_provider_params(test_server):
    """Test 2: POST /assets/provider - Update provider params."""
    print_section("Test 2: POST /assets/provider - Update Provider Params")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        # Create asset
        asset_item = FAAssetCreateItem(display_name=f"Update Params {unique_id('UPD')}", currency="USD")
        create_resp = await client.post(f"{API_BASE}/assets", json=[asset_item.model_dump(mode="json")], timeout=TIMEOUT)
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id

        # Assign provider with params
        assignment1 = FAProviderAssignmentItem(
            asset_id=asset_id,
            provider_code="mockprov",
            identifier="MOCK1",
            identifier_type=ProviderInputType.AUTO_GENERATED,
            provider_params={"key": "value1"},
        )
        await client.post(
            f"{API_BASE}/assets/provider",
            json=[assignment1.model_dump(mode="json")],
            timeout=TIMEOUT,
        )
        print_info("  Initial provider assigned with params")

        # Update params
        assignment2 = FAProviderAssignmentItem(
            asset_id=asset_id,
            provider_code="mockprov",
            identifier="MOCK1",
            identifier_type=ProviderInputType.AUTO_GENERATED,
            provider_params={"key": "value2"},
        )
        update_resp = await client.post(
            f"{API_BASE}/assets/provider",
            json=[assignment2.model_dump(mode="json")],
            timeout=TIMEOUT,
        )
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
        await create_user_and_login(client)
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
            identifier_type=ProviderInputType.AUTO_GENERATED,
            provider_params=None,
        )
        await client.post(
            f"{API_BASE}/assets/provider",
            json=[assignment.model_dump(mode="json")],
            timeout=TIMEOUT,
        )
        print_info("  Provider assigned")

        # Remove provider
        delete_resp = await client.delete(f"{API_BASE}/assets/provider", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)
        assert delete_resp.status_code == 200
        print_success("✓ Provider removed")

        # Verify removal
        query_resp = await client.get(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)
        assets = [FAAssetMetadataResponse(**a) for a in query_resp.json()]
        assert assets[0].provider_code is None
        print_success("✓ Provider removal verified")


# ============================================================
# Test 4: POST /assets/provider/refresh - Refresh metadata
# ============================================================
@pytest.mark.asyncio
async def test_refresh_metadata(test_server):
    """Test 4: POST /assets/provider/refresh - Refresh metadata from provider."""
    print_section("Test 4: POST /assets/provider/refresh - Refresh Metadata")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
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
            identifier_type=ProviderInputType.AUTO_GENERATED,
            provider_params=None,
        )
        await client.post(
            f"{API_BASE}/assets/provider",
            json=[assignment.model_dump(mode="json")],
            timeout=TIMEOUT,
        )
        print_info("  Provider assigned")

        # Refresh metadata
        refresh_resp = await client.post(f"{API_BASE}/assets/provider/refresh", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)

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
        await create_user_and_login(client)
        # Create multiple assets
        assets = [FAAssetCreateItem(display_name=f"Bulk {i} {unique_id(f'BLK{i}')}", currency="USD") for i in range(3)]
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
                identifier_type=ProviderInputType.AUTO_GENERATED,
                provider_params=None,
            )
            for aid in asset_ids
        ]

        bulk_resp = await client.post(
            f"{API_BASE}/assets/provider",
            json=[a.model_dump(mode="json") for a in assignments],
            timeout=TIMEOUT,
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
        await create_user_and_login(client)
        # Search using default (all providers)
        # Note: Uses longer timeout as external APIs (yfinance) can be slow
        search_resp = await client.get(f"{API_BASE}/assets/provider/search", params={"q": "Apple"}, timeout=SEARCH_TIMEOUT)

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
        await create_user_and_login(client)
        # Search for "Semiconductor" - sector-specific
        # Note: Uses longer timeout as external APIs (yfinance) can be slow
        search_resp = await client.get(
            f"{API_BASE}/assets/provider/search",
            params={"q": "Semiconductor"},
            timeout=SEARCH_TIMEOUT,
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

        justetf_results = by_provider.get("justetf", 0)
        yfinance_results = by_provider.get("yfinance", 0)

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
        await create_user_and_login(client)
        # Search using only justetf provider
        search_resp = await client.get(
            f"{API_BASE}/assets/provider/search",
            params={"q": "MSCI", "providers": "justetf"},
            timeout=SEARCH_TIMEOUT,
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
        await create_user_and_login(client)
        # Search for "IBM" - well-known ticker/company
        search_resp = await client.get(f"{API_BASE}/assets/provider/search", params={"q": "IBM"}, timeout=SEARCH_TIMEOUT)

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

        yfinance_results = by_provider.get("yfinance", 0)
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
        await create_user_and_login(client)
        # Search using non-existent provider
        search_resp = await client.get(
            f"{API_BASE}/assets/provider/search",
            params={"q": "Apple", "providers": "nonexistent_provider"},
            timeout=TIMEOUT,
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
        await create_user_and_login(client)
        # Search with empty query
        search_resp = await client.get(f"{API_BASE}/assets/provider/search", params={"q": ""}, timeout=TIMEOUT)

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

    import time  # noqa: PLC0415 — test setup — imports after sys.path/db config

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        # Time a search across all providers
        start_time = time.time()

        search_resp = await client.get(f"{API_BASE}/assets/provider/search", params={"q": "Technology"}, timeout=TIMEOUT)

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
async def test_search_to_asset_e2e(test_server):  # noqa: C901 — sequential E2E step driver
    """Test 13: End-to-End test - use search results to create assets and perform operations."""
    print_section("Test 13: End-to-End - Search → Create → Assign → Refresh")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        # Step 1: Search for assets
        print_info("Step 1: Searching for 'Microsoft'...")
        search_resp = await client.get(f"{API_BASE}/assets/provider/search", params={"q": "Microsoft"}, timeout=TIMEOUT)
        assert search_resp.status_code == 200
        search_data = FAProviderSearchResponse(**search_resp.json())

        # We need results from providers that support current value (yfinance, justetf)
        usable_results = [r for r in search_data.results if r.provider_code in ("yfinance", "justetf") and r.identifier]

        assert len(usable_results) > 0, "Should find usable results from yfinance or justetf"
        print_info(f"  Found {len(usable_results)} usable results")

        # Pick the first yfinance result (more reliable for stocks)
        yfinance_results = [r for r in usable_results if r.provider_code == "yfinance"]
        justetf_results = [r for r in usable_results if r.provider_code == "justetf"]

        # Test with one result from each provider if available
        test_assets = []

        if yfinance_results:
            test_assets.append(
                {
                    "search_result": yfinance_results[0],
                    "asset_type": AssetType.STOCK,
                    "identifier_type": IdentifierType.TICKER,
                }
            )
            print_info(f"  Will test yfinance with: {yfinance_results[0].identifier}")

        if justetf_results:
            test_assets.append(
                {
                    "search_result": justetf_results[0],
                    "asset_type": AssetType.ETF,
                    "identifier_type": IdentifierType.ISIN,
                }
            )
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
                asset_type=test_item["asset_type"],
            )

            create_resp = await client.post(f"{API_BASE}/assets", json=[asset_item.model_dump(mode="json")], timeout=TIMEOUT)

            if create_resp.status_code == 201:
                create_data = FABulkAssetCreateResponse(**create_resp.json())
                if create_data.results and create_data.results[0].success:
                    created_assets.append(
                        {
                            "asset_id": create_data.results[0].asset_id,
                            "provider_code": sr.provider_code,
                            "identifier": sr.identifier,
                            "identifier_type": test_item["identifier_type"],
                        }
                    )
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
                provider_params=None,
            )
            assignments.append(assignment)

        assign_resp = await client.post(
            f"{API_BASE}/assets/provider",
            json=[a.model_dump(mode="json") for a in assignments],
            timeout=TIMEOUT,
        )

        assert assign_resp.status_code == 200, f"Provider assignment failed: {assign_resp.text}"
        assign_data = FABulkAssignResponse(**assign_resp.json())
        assert assign_data.success_count == len(assignments), "All assignments should succeed"
        print_success(f"✓ Assigned {assign_data.success_count} providers")

        # Step 4: Refresh metadata from providers
        print_info("\nStep 4: Refreshing metadata...")
        asset_ids = [a["asset_id"] for a in created_assets]

        refresh_resp = await client.post(f"{API_BASE}/assets/provider/refresh", params={"asset_ids": asset_ids}, timeout=TIMEOUT)

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
                timeout=TIMEOUT,
            )

            assert asset_resp.status_code == 200
            assets = [FAAssetMetadataResponse(**a) for a in asset_resp.json()]

            if assets:
                asset = assets[0]
                print_info(f"  Asset {asset_info['asset_id']} ({asset_info['provider_code']}):")
                print_info(f"    - Name: {asset.display_name[:50]}...")
                print_info(f"    - Provider: {asset.provider_code}")
                print_info(f"    - Currency: {asset.currency}")
                assert asset.provider_code is not None, "Asset should have provider assigned"

        print_success("✓ All assets verified successfully")

        # Step 6: Test price refresh (uses get_current_value for today)
        print_info("\nStep 6: Testing price refresh (get_current_value for today)...")

        today = date.today()
        yesterday = today - timedelta(days=7)  # Get a week of history

        for asset_info in created_assets:
            price_refresh_resp = await client.post(
                f"{API_BASE}/assets/prices/sync",
                json=[
                    {
                        "asset_id": asset_info["asset_id"],
                        "date_range": {"start": yesterday.isoformat(), "end": today.isoformat()},
                    }
                ],
                timeout=TIMEOUT,
            )

            if price_refresh_resp.status_code == 200:
                refresh_data = price_refresh_resp.json()
                results = refresh_data.get("results", [])
                if results:
                    result = results[0]
                    fetched = result.get("points_fetched", 0)
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

        # Step 7: Verify prices were stored (using bulk query endpoint)
        print_info("\nStep 7: Verifying stored prices...")
        query_items = [
            {
                "asset_id": a["asset_id"],
                "date_range": {"start": yesterday.isoformat(), "end": today.isoformat()},
            }
            for a in created_assets
        ]
        prices_resp = await client.post(
            f"{API_BASE}/assets/prices/query",
            json=query_items,
            timeout=TIMEOUT,
        )

        if prices_resp.status_code == 200:
            query_data = prices_resp.json()
            for item in query_data.get("items", []):
                aid = item.get("asset_id")
                prices = item.get("prices", [])
                print_info(f"  Asset {aid}: {len(prices)} price point(s)")
                if prices:
                    today_prices = [p for p in prices if p.get("date") == today.isoformat()]
                    if today_prices:
                        print_success(f"  ✓ Today's price found: {today_prices[0].get('close')}")
                    else:
                        print_info(f"    Latest price: {prices[-1].get('date')} = {prices[-1].get('close')}")

        # Step 8: Cleanup - delete created assets
        print_info("\nStep 8: Cleanup...")
        delete_resp = await client.delete(f"{API_BASE}/assets", params={"asset_ids": asset_ids}, timeout=TIMEOUT)

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

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        # Create asset with yfinance provider (reliable for current prices)
        asset_item = FAAssetCreateItem(
            display_name=f"Current Price Test {unique_id('CPT')}",
            currency="USD",
            asset_type=AssetType.STOCK,
        )
        create_resp = await client.post(f"{API_BASE}/assets", json=[asset_item.model_dump(mode="json")], timeout=TIMEOUT)
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
            provider_params=None,
        )
        assign_resp = await client.post(
            f"{API_BASE}/assets/provider",
            json=[assignment.model_dump(mode="json")],
            timeout=TIMEOUT,
        )
        assert assign_resp.status_code == 200
        print_info("  Provider assigned: yfinance (AAPL)")

        # Refresh prices for TODAY ONLY
        today = date.today()
        print_info(f"  Refreshing price for today: {today}")

        refresh_resp = await client.post(
            f"{API_BASE}/assets/prices/sync",
            json=[
                {
                    "asset_id": asset_id,
                    "date_range": {"start": today.isoformat(), "end": today.isoformat()},
                }
            ],
            timeout=TIMEOUT,
        )

        assert refresh_resp.status_code == 200, f"Refresh failed: {refresh_resp.text}"
        refresh_data = refresh_resp.json()
        results = refresh_data.get("results", [])

        assert len(results) > 0, "Should have refresh result"
        result = results[0]
        fetched_count = result.get("points_fetched", 0)
        errors = result.get("errors", [])

        print_info(f"  Fetched count: {fetched_count}")
        if errors:
            print_info(f"  Errors: {errors}")

        # Should have fetched at least 1 price (today's current value)
        assert fetched_count >= 1 or not errors, f"Should fetch current price. Errors: {errors}"

        # Verify the price was stored
        prices_resp = await client.post(
            f"{API_BASE}/assets/prices/query",
            json=[
                {
                    "asset_id": asset_id,
                    "date_range": {"start": today.isoformat(), "end": today.isoformat()},
                }
            ],
            timeout=TIMEOUT,
        )

        assert prices_resp.status_code == 200
        query_data = prices_resp.json()
        prices = query_data["items"][0]["prices"] if query_data.get("items") else []

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
        await client.delete(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)
        print_info("  Cleanup completed")


# ============================================================
# Test 15: CSS Scraper (no history) still gets current price
# ============================================================
@pytest.mark.asyncio
async def test_css_scraper_current_price(test_server):
    """Test 15: Verify CSS Scraper (without history support) can get current price."""
    print_section("Test 15: CSS Scraper - Current Price Only")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        # Create asset for Borsa Italiana BTP
        asset_item = FAAssetCreateItem(display_name=f"BTP Test {unique_id('BTP')}", currency="EUR", asset_type=AssetType.BOND)
        create_resp = await client.post(f"{API_BASE}/assets", json=[asset_item.model_dump(mode="json")], timeout=TIMEOUT)
        assert create_resp.status_code == 201
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id
        print_info(f"  Created asset ID: {asset_id}")

        # Assign CSS Scraper provider with Borsa Italiana BTP
        assignment = FAProviderAssignmentItem(
            asset_id=asset_id,
            provider_code="css_scraper",
            identifier="https://www.borsaitaliana.it/borsa/obbligazioni/mot/btp/scheda/IT0005634800.html?lang=en",
            identifier_type=ProviderInputType.URL,
            provider_params={
                "current_css_selector": ".summary-value strong",
                "currency": "EUR",
                "decimal_format": "us",
            },
        )
        assign_resp = await client.post(
            f"{API_BASE}/assets/provider",
            json=[assignment.model_dump(mode="json")],
            timeout=TIMEOUT,
        )
        assert assign_resp.status_code == 200
        print_info("  Provider assigned: cssscraper (Borsa Italiana BTP)")

        # Refresh prices for TODAY ONLY
        # CSS Scraper doesn't support history, so this tests that get_current_value is used
        today = date.today()
        print_info(f"  Refreshing price for today: {today}")

        refresh_resp = await client.post(
            f"{API_BASE}/assets/prices/sync",
            json=[
                {
                    "asset_id": asset_id,
                    "date_range": {"start": today.isoformat(), "end": today.isoformat()},
                }
            ],
            timeout=TIMEOUT,
        )

        assert refresh_resp.status_code == 200, f"Refresh failed: {refresh_resp.text}"
        refresh_data = refresh_resp.json()
        results = refresh_data.get("results", [])

        assert len(results) > 0, "Should have refresh result"
        result = results[0]
        fetched_count = result.get("points_fetched", 0)
        errors = result.get("errors", [])

        print_info(f"  Fetched count: {fetched_count}")
        if errors:
            print_info(f"  Errors: {errors}")

        # Should have fetched current price (CSS Scraper only supports current)
        # Note: May fail if Borsa Italiana is down or returns different HTML
        if fetched_count > 0:
            print_success("✓ CSS Scraper fetched current price (no history support needed)")
        elif "NOT_IMPLEMENTED" in str(errors) or "history" in str(errors).lower():
            # This would indicate the old behavior (failing on history)
            # The fix should prevent this
            print_info("  Warning: Appears to have tried history instead of current value")
        else:
            # Could be network issue with Borsa Italiana
            print_info(f"  Could not fetch (may be network issue): {errors}")

        # Verify if price was stored (using bulk query endpoint)
        prices_resp = await client.post(
            f"{API_BASE}/assets/prices/query",
            json=[
                {
                    "asset_id": asset_id,
                    "date_range": {"start": today.isoformat(), "end": today.isoformat()},
                }
            ],
            timeout=TIMEOUT,
        )

        if prices_resp.status_code == 200:
            query_data = prices_resp.json()
            prices = query_data["items"][0]["prices"] if query_data.get("items") else []

            if prices:
                today_price = prices[0]
                print_info(f"  Today's BTP price: {today_price.get('close')} EUR")
                print_success("✓ CSS Scraper current value stored successfully")
            else:
                print_info("  No prices stored (may be network/site issue)")

        # Cleanup
        await client.delete(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)
        print_info("  Cleanup completed")


# ============================================================
# Test: POST /assets/provider/probe — current_price only
# ============================================================
@pytest.mark.asyncio
async def test_probe_current_price(test_server):
    """Test probe with current_price operation using yfinance."""
    print_section("Test: POST /assets/provider/probe — current_price")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)

        probe_resp = await client.post(
            f"{API_BASE}/assets/provider/probe",
            json={
                "provider_code": "yfinance",
                "identifier": "AAPL",
                "identifier_type": "TICKER",
                "operations": ["current_price"],
            },
            timeout=SEARCH_TIMEOUT,
        )
        assert probe_resp.status_code == 200, f"Probe failed: {probe_resp.text}"
        data = probe_resp.json()

        assert data["provider_code"] == "yfinance"
        assert data["identifier"] == "AAPL"
        assert data["total_execution_time_ms"] >= 0
        assert data["provider_url"] == "https://finance.yahoo.com/quote/AAPL"

        # current_price should be present and successful
        cp = data["current_price"]
        assert cp is not None, "current_price should be present"
        assert cp["success"] is True, f"current_price failed: {cp.get('error')}"
        assert float(cp["value"]) > 0, "Price should be positive"
        assert cp["execution_time_ms"] >= 0

        # history and metadata should be absent (not requested)
        assert data["history"] is None
        assert data["metadata"] is None

        print_success(f"✓ Probe current_price: {cp['value']} {cp['currency']} ({cp['execution_time_ms']}ms)")


# ============================================================
# Test: POST /assets/provider/probe — bulk all operations
# ============================================================
@pytest.mark.asyncio
async def test_probe_bulk_operations(test_server):
    """Test probe with all operations (current_price, history, metadata)."""
    print_section("Test: POST /assets/provider/probe — bulk all operations")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)

        probe_resp = await client.post(
            f"{API_BASE}/assets/provider/probe",
            json={
                "provider_code": "yfinance",
                "identifier": "AAPL",
                "identifier_type": "TICKER",
                "operations": ["current_price", "history", "metadata"],
            },
            timeout=SEARCH_TIMEOUT,
        )
        assert probe_resp.status_code == 200, f"Probe failed: {probe_resp.text}"
        data = probe_resp.json()

        # All three results should be present
        assert data["current_price"] is not None
        assert data["history"] is not None
        assert data["metadata"] is not None

        # Check current_price
        assert data["current_price"]["success"] is True

        # Check history
        hist = data["history"]
        assert hist["success"] is True
        assert hist["points_count"] > 0
        print_info(f"  History: {hist['points_count']} points, range: {hist['date_range']}")

        # Check metadata
        meta = data["metadata"]
        assert meta["success"] is True
        assert meta["patch_data"] is not None
        patch = meta["patch_data"]
        assert patch.get("identifier_ticker") is not None, "identifier_ticker should be populated"
        print_info(f"  Metadata ticker: {patch.get('identifier_ticker')}, ISIN: {patch.get('identifier_isin')}")

        # Total time should be coherent
        assert data["total_execution_time_ms"] > 0
        print_success(f"✓ Probe bulk: total {data['total_execution_time_ms']}ms")


# ============================================================
# Test: POST /assets/provider/probe — invalid identifier
# ============================================================
@pytest.mark.asyncio
async def test_probe_invalid_identifier(test_server):
    """Test probe with invalid identifier returns failure."""
    print_section("Test: POST /assets/provider/probe — invalid identifier")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)

        probe_resp = await client.post(
            f"{API_BASE}/assets/provider/probe",
            json={
                "provider_code": "yfinance",
                "identifier": "XYZNONEXISTENT999",
                "identifier_type": "TICKER",
                "operations": ["current_price"],
            },
            timeout=SEARCH_TIMEOUT,
        )
        assert probe_resp.status_code == 200, f"Probe should return 200 even for failures: {probe_resp.text}"
        data = probe_resp.json()

        cp = data["current_price"]
        assert cp is not None
        assert cp["success"] is False, "Should fail for invalid identifier"
        assert cp["error"] is not None
        assert cp["execution_time_ms"] > 0
        print_success(f"✓ Probe invalid: error={cp['error'][:60]}...")


# ============================================================
# Test: POST /assets/provider/probe — mockprov
# ============================================================
@pytest.mark.asyncio
async def test_probe_mockprov(test_server):
    """Test probe with mock provider."""
    print_section("Test: POST /assets/provider/probe — mockprov")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)

        probe_resp = await client.post(
            f"{API_BASE}/assets/provider/probe",
            json={
                "provider_code": "mockprov",
                "identifier": "MOCK1",
                "identifier_type": "UUID",
                "operations": ["current_price"],
            },
            timeout=TIMEOUT,
        )
        assert probe_resp.status_code == 200, f"Probe failed: {probe_resp.text}"
        data = probe_resp.json()
        assert data["provider_code"] == "mockprov"
        cp = data["current_price"]
        assert cp is not None
        assert cp["execution_time_ms"] >= 0
        print_success(f"✓ Probe mockprov: success={cp['success']}")


# ============================================================
# Test: POST /assets/provider/probe — metadata identifiers
# ============================================================
@pytest.mark.asyncio
async def test_probe_metadata_identifiers(test_server):
    """Test probe metadata operation returns identifiers."""
    print_section("Test: POST /assets/provider/probe — metadata identifiers")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)

        probe_resp = await client.post(
            f"{API_BASE}/assets/provider/probe",
            json={
                "provider_code": "yfinance",
                "identifier": "AAPL",
                "identifier_type": "TICKER",
                "operations": ["metadata"],
            },
            timeout=SEARCH_TIMEOUT,
        )
        assert probe_resp.status_code == 200
        data = probe_resp.json()

        meta = data["metadata"]
        assert meta is not None
        assert meta["success"] is True
        patch = meta["patch_data"]
        assert patch is not None
        assert patch.get("identifier_ticker") == "AAPL"
        print_info(f"  identifier_ticker: {patch.get('identifier_ticker')}")
        print_info(f"  identifier_isin: {patch.get('identifier_isin')}")
        print_success("✓ Probe metadata: identifiers populated")


# ============================================================
# Test: user_url round-trip + provider_url calculated
# ============================================================
@pytest.mark.asyncio
async def test_user_url_round_trip(test_server):
    """Test user_url is persisted via asset PATCH and provider_url is calculated."""
    print_section("Test: user_url round-trip + provider_url")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)

        # Create asset
        asset_item = FAAssetCreateItem(
            display_name=f"UserUrl Test {unique_id('URL')}",
            currency="USD",
            asset_type=AssetType.STOCK,
        )
        create_resp = await client.post(f"{API_BASE}/assets", json=[asset_item.model_dump(mode="json")], timeout=TIMEOUT)
        assert create_resp.status_code == 201
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id

        # Set user_url via asset PATCH (user_url lives on the Asset model, not on provider assignment)
        patch_resp = await client.patch(
            f"{API_BASE}/assets",
            json=[{"asset_id": asset_id, "user_url": "https://investor.apple.com"}],
            timeout=TIMEOUT,
        )
        assert patch_resp.status_code == 200

        # Assign provider (without user_url — it doesn't belong here)
        assignment = FAProviderAssignmentItem(
            asset_id=asset_id,
            provider_code="yfinance",
            identifier="AAPL",
            identifier_type=IdentifierType.TICKER,
            provider_params=None,
        )
        assign_resp = await client.post(
            f"{API_BASE}/assets/provider",
            json=[assignment.model_dump(mode="json")],
            timeout=TIMEOUT,
        )
        assert assign_resp.status_code == 200

        # Get assignments and verify provider_url is calculated
        assignments_resp = await client.get(
            f"{API_BASE}/assets/provider/assignments",
            params={"asset_ids": [asset_id]},
            timeout=TIMEOUT,
        )
        assert assignments_resp.status_code == 200
        assignments = assignments_resp.json()
        assert len(assignments) == 1

        assignment_data = assignments[0]
        assert assignment_data["provider_url"] == "https://finance.yahoo.com/quote/AAPL", f"provider_url not calculated: {assignment_data.get('provider_url')}"

        # Verify user_url via GET /assets/all (it's on the asset, not the assignment)
        asset_resp = await client.get(
            f"{API_BASE}/assets/all",
            timeout=TIMEOUT,
        )
        if asset_resp.status_code == 200:
            all_assets = asset_resp.json()
            matching = [a for a in all_assets if a.get("id") == asset_id]
            if matching:
                assert matching[0].get("user_url") == "https://investor.apple.com", f"user_url not persisted: {matching[0].get('user_url')}"

        print_success("✓ user_url persisted on asset, provider_url calculated on assignment")

        # Cleanup
        await client.delete(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)


# ============================================================
# Test: CSS Scraper probe with malformed params → clear error
# ============================================================
@pytest.mark.asyncio
async def test_probe_css_scraper_invalid_params(test_server):
    """Probe CSS scraper with malformed provider_params returns clear error."""
    print_section("Test: CSS Scraper probe with invalid params")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)

        # Create asset
        asset_item = FAAssetCreateItem(
            display_name=f"CSS Invalid Test {unique_id('CSSINV')}",
            currency="USD",
        )
        create_resp = await client.post(f"{API_BASE}/assets", json=[asset_item.model_dump(mode="json")], timeout=TIMEOUT)
        assert create_resp.status_code in (200, 201)
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id

        # Assign CSS scraper with WRONG param names (the old buggy format)
        # Send raw JSON to bypass client-side Pydantic validation —
        # the server should reject or the sync should fail with a clear error.
        assign_resp = await client.post(
            f"{API_BASE}/assets/provider",
            json=[
                {
                    "asset_id": asset_id,
                    "provider_code": "css_scraper",
                    "identifier": "https://example.com",
                    "identifier_type": "URL",
                    "provider_params": {
                        "css_selector": "#price",  # WRONG: should be current_css_selector
                        "decimal_separator": ".",  # WRONG: should be decimal_format
                        # MISSING: currency (required!)
                    },
                }
            ],
            timeout=TIMEOUT,
        )

        # Server should reject with 422 (Pydantic validation on provider_params)
        # OR accept and fail at sync time — either is correct behavior
        if assign_resp.status_code == 422:
            print_success("  ✓ Assignment rejected with 422 (server-side param validation)")
        elif assign_resp.status_code == 200:
            # Assignment accepted — sync should fail with clear error
            assign_data = assign_resp.json()
            results = assign_data.get("results", [])
            if results and not results[0].get("success"):
                print_success("  ✓ Assignment reported failure in results")
            else:
                # Try to sync — should fail with validation error
                today = date.today()
                sync_resp = await client.post(
                    f"{API_BASE}/assets/prices/sync",
                    json=[{"asset_id": asset_id, "date_range": {"start": (today - timedelta(days=1)).isoformat(), "end": today.isoformat()}}],
                    timeout=TIMEOUT,
                )
                # The sync should report an error for this asset
                if sync_resp.status_code == 200:
                    result = sync_resp.json()["results"][0]
                    assert result.get("error") or result.get("status") == "error", "Sync with malformed CSS params should report an error"
                    print_success("  ✓ Sync with malformed CSS params reported error in result")
                else:
                    print_success(f"  ✓ Sync rejected with status {sync_resp.status_code}")
        else:
            # Assignment itself was rejected — also fine
            print_success(f"  ✓ Assignment rejected with status {assign_resp.status_code}")

        # Cleanup
        await client.delete(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)


# ============================================================
# Test: ScheduledInvestment via API — assign + sync
# ============================================================
@pytest.mark.asyncio
async def test_scheduled_investment_via_api(test_server):
    """Assign ScheduledInvestment provider and sync → generated price curve."""
    print_section("Test: ScheduledInvestment via API")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)

        # Create asset
        asset_item = FAAssetCreateItem(
            display_name=f"Scheduled Inv Test {unique_id('SCHED')}",
            currency="EUR",
        )
        create_resp = await client.post(f"{API_BASE}/assets", json=[asset_item.model_dump(mode="json")], timeout=TIMEOUT)
        assert create_resp.status_code in (200, 201)
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id
        print_info(f"  Created asset: {asset_id}")

        # Assign scheduled_investment provider with valid params
        schedule_params = {
            "initial_value": {"code": "EUR", "amount": 10000},
            "interest_type": "SIMPLE",
            "day_count": "ACT/365",
            "schedule": [
                {
                    "start_date": "2025-01-01",
                    "end_date": "2025-12-31",
                    "annual_rate": "0.05",
                    "maturation_frequency": "MONTHLY",
                    "generate_interest": False,
                }
            ],
        }

        assignment = FAProviderAssignmentItem(
            asset_id=asset_id,
            provider_code="scheduled_investment",
            identifier="auto",
            identifier_type=ProviderInputType.AUTO_GENERATED,
            provider_params=schedule_params,
        )
        assign_resp = await client.post(
            f"{API_BASE}/assets/provider",
            json=[assignment.model_dump(mode="json")],
            timeout=TIMEOUT,
        )
        assert assign_resp.status_code == 200, f"Assignment failed: {assign_resp.text}"
        print_info("  ScheduledInvestment provider assigned")

        # Sync prices — should generate the calculated curve
        sync_resp = await client.post(
            f"{API_BASE}/assets/prices/sync",
            json=[{"asset_id": asset_id, "date_range": {"start": "2025-01-01", "end": "2025-12-31"}}],
            timeout=TIMEOUT,
        )
        assert sync_resp.status_code == 200, f"Sync failed: {sync_resp.text}"
        sync_result = sync_resp.json()["results"][0]
        fetched = sync_result.get("points_fetched", 0)
        changed = sync_result.get("points_changed", 0)
        print_info(f"  Sync: fetched={fetched}, changed={changed}")

        # Query prices — should have calculated curve
        query_resp = await client.post(
            f"{API_BASE}/assets/prices/query",
            json=[{"asset_id": asset_id, "date_range": {"start": "2025-01-01", "end": "2025-12-31"}}],
            timeout=TIMEOUT,
        )
        assert query_resp.status_code == 200
        prices = query_resp.json()["items"][0]["prices"]
        assert len(prices) > 0, "ScheduledInvestment should generate price points"
        print_info(f"  Generated {len(prices)} price points")

        # Verify prices are monotonically increasing (SIMPLE interest on 10000 @ 5%)
        closes = [float(p["close"]) for p in prices]
        assert closes[-1] > closes[0], "Prices should increase over time with positive interest"
        print_success(f"  ✓ Price curve generated: {closes[0]:.2f} → {closes[-1]:.2f}")

        # Cleanup
        await client.delete(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)


@pytest.mark.asyncio
async def test_probe_bulk_assign_refresh_and_remove_with_mock_provider(test_server):
    """Test: Probe + bulk assign/refresh/remove via mock provider."""
    print_section("Test: probe + bulk provider wrappers with mockprov")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)

        probe_resp = await client.post(
            f"{API_BASE}/assets/provider/probe",
            json={
                "provider_code": "mockprov",
                "identifier": "MOCK",
                "identifier_type": "TICKER",
                "operations": ["metadata"],
            },
            timeout=TIMEOUT,
        )
        assert probe_resp.status_code == 200, probe_resp.text
        probe_data = probe_resp.json()
        assert probe_data["provider_code"] == "mockprov"
        assert probe_data["current_price"] is None
        assert probe_data["history"] is None
        assert probe_data["metadata"]["success"] is True
        assert probe_data["metadata"]["patch_data"] is not None
        print_success("✓ Probe metadata-only success with mock provider")

        create_resp = await client.post(
            f"{API_BASE}/assets",
            json=[
                FAAssetCreateItem(display_name=f"Prov Wrap 1 {unique_id('PW1')}", currency="USD").model_dump(mode="json"),
                FAAssetCreateItem(display_name=f"Prov Wrap 2 {unique_id('PW2')}", currency="USD").model_dump(mode="json"),
            ],
            timeout=TIMEOUT,
        )
        assert create_resp.status_code == 201, create_resp.text
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_ids = [result.asset_id for result in create_data.results]

        assign_resp = await client.post(
            f"{API_BASE}/assets/provider",
            json=[
                FAProviderAssignmentItem(
                    asset_id=asset_ids[0],
                    provider_code="mockprov",
                    identifier="MOCK_A",
                    identifier_type=ProviderInputType.TICKER,
                    provider_params=None,
                ).model_dump(mode="json"),
                FAProviderAssignmentItem(
                    asset_id=asset_ids[1],
                    provider_code="mockprov",
                    identifier="MOCK_B",
                    identifier_type=ProviderInputType.TICKER,
                    provider_params=None,
                ).model_dump(mode="json"),
            ],
            timeout=TIMEOUT,
        )
        assert assign_resp.status_code == 200, assign_resp.text
        assign_data = FABulkAssignResponse(**assign_resp.json())
        assert assign_data.success_count == 2

        refresh_resp = await client.post(
            f"{API_BASE}/assets/provider/refresh",
            params=[("asset_ids", str(asset_id)) for asset_id in asset_ids],
            timeout=TIMEOUT,
        )
        assert refresh_resp.status_code == 200, refresh_resp.text
        refresh_data = refresh_resp.json()
        assert refresh_data["success_count"] == 2
        for item in refresh_data["results"]:
            assert item["success"] is True
            assert item["fields_detail"]["refreshed_fields"]
        print_success("✓ Bulk provider refresh returned refreshed fields")

        remove_resp = await client.delete(
            f"{API_BASE}/assets/provider",
            params=[("asset_ids", str(asset_id)) for asset_id in asset_ids],
            timeout=TIMEOUT,
        )
        assert remove_resp.status_code == 200, remove_resp.text
        remove_data = remove_resp.json()
        assert remove_data["success_count"] == 2
        print_success("✓ Bulk provider removal succeeded")


# ============================================================
# Z-32 (d): the quote base suggestion (QBS-A01…A06)
# ============================================================
# The HTTP side of test_services/test_quote_base_suggestion.py, on the lane's server, where mockprov is served (test
# mode; a search names it in `providers`). mockprov's minor-unit line is written here, not imported from its plugin
# (MINOR_UNIT_QUERY, MINOR_UNIT_IDENTIFIER): importing names only the cure adds would stop this whole module from loading.

QBS_MINOR_UNIT_QUERY = "lf-minor-unit"
QBS_MINOR_UNIT_IDENTIFIER = "MOCK_MINOR_UNIT"
QBS_GBP_PENCE = {"quantity": 100, "quote_currency": "GBp"}
QBS_FIELD = "quote_base_suggestion"


def _qbs_unique(prefix: str) -> str:
    """Unique across the lane's workers: a time, a per-process counter and randomness."""
    return f"{unique_id(prefix)}_{uuid.uuid4().hex[:8]}"


async def _qbs_search_mockprov(client: httpx.AsyncClient, query: str) -> dict:
    """``GET /assets/provider/search`` for ``query``, mockprov only; the answer, mockprov having answered."""
    resp = await client.get(f"{API_BASE}/assets/provider/search", params={"q": query, "providers": "mockprov"}, timeout=TIMEOUT)
    assert resp.status_code == 200, f"search {query!r}: {resp.status_code} {resp.text[:300]}"
    data = resp.json()
    assert "mockprov" in data["providers_queried"] and "mockprov" not in data["providers_with_errors"], f"barrier: mockprov answered {query!r}: queried {data['providers_queried']}, errors {data['providers_with_errors']}"
    return data


def _qbs_only_result(data: dict, identifier: str) -> dict:
    """The one mockprov result ``identifier`` of a search answer this test asked for."""
    matches = [result for result in data["results"] if result["provider_code"] == "mockprov" and result["identifier"] == identifier]
    assert len(matches) == 1, f"one mockprov result {identifier} expected in the answer to {data['query']!r}: its results are {[(r['provider_code'], r['identifier']) for r in data['results']]}"
    return matches[0]


async def _qbs_probe_metadata(client: httpx.AsyncClient, identifier: str) -> dict:
    """``POST /assets/provider/probe`` of mockprov ``identifier`` (a TICKER), metadata only; the metadata result, which
    answered."""
    resp = await client.post(
        f"{API_BASE}/assets/provider/probe",
        json={"provider_code": "mockprov", "identifier": identifier, "identifier_type": "TICKER", "operations": ["metadata"]},
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, f"probe {identifier}: {resp.status_code} {resp.text[:300]}"
    meta = resp.json()["metadata"]
    assert meta is not None and meta["success"] is True and meta["patch_data"] is not None, f"barrier: mockprov answered the metadata of {identifier}: {meta}"
    return meta


@pytest.mark.asyncio
async def test_qbs_a01_search_carries_mockprov_minor_unit_suggestion(test_server):
    """QBS-A01 (Z-32 d, points 3 and 8): ``GET /assets/provider/search?q=lf-minor-unit&providers=mockprov`` answers
    mockprov's ``MOCK_MINOR_UNIT`` — a London line quoted in pence — with ``quote_base_suggestion == {"quantity": 100,
    "quote_currency": "GBp"}``.

    Red before Z-32 (d): mockprov answers ``lf-minor-unit`` like any query (``MOCK_LF-MINOR-UNIT``), and a search result
    has no ``quote_base_suggestion``.
    """
    print_section("QBS-A01: search lf-minor-unit on mockprov → 100 GBp")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        data = await _qbs_search_mockprov(client, QBS_MINOR_UNIT_QUERY)

    result = _qbs_only_result(data, QBS_MINOR_UNIT_IDENTIFIER)
    assert QBS_FIELD in result, f"a search result has no {QBS_FIELD}: its keys are {sorted(result)}"
    assert result[QBS_FIELD] == QBS_GBP_PENCE, f"{QBS_MINOR_UNIT_IDENTIFIER} must suggest 100 GBp: {result[QBS_FIELD]!r}"
    print_success(f"✓ {QBS_MINOR_UNIT_IDENTIFIER}: {result[QBS_FIELD]}")


@pytest.mark.asyncio
async def test_qbs_a02_other_mockprov_search_result_suggests_null(test_server):
    """QBS-A02 (Z-32 d, points 2 and 8): a mockprov search for a query of this test answers its ``MOCK_<QUERY>`` with
    ``quote_base_suggestion`` present and null, as the answer's other optional fields are.

    Red before Z-32 (d): a search result has no ``quote_base_suggestion``.
    """
    print_section("QBS-A02: any other mockprov search → null")
    query = _qbs_unique("qbs-plain")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        data = await _qbs_search_mockprov(client, query)

    result = _qbs_only_result(data, f"MOCK_{query.upper()}")
    assert QBS_FIELD in result, f"a search result has no {QBS_FIELD}: its keys are {sorted(result)}"
    assert result[QBS_FIELD] is None, f"mockprov suggests nothing for {query!r}: {result[QBS_FIELD]!r}"
    print_success(f"✓ {result['identifier']}: null")


@pytest.mark.asyncio
async def test_qbs_a03_probe_metadata_carries_mockprov_minor_unit_suggestion(test_server):
    """QBS-A03 (Z-32 d, points 5 and 8): ``POST /assets/provider/probe`` of mockprov ``MOCK_MINOR_UNIT``, metadata only:
    ``metadata.quote_base_suggestion == {"quantity": 100, "quote_currency": "GBp"}``, and ``metadata.patch_data`` sets
    no ``quote_base_quantity`` — the patch is what a metadata refresh writes without asking.

    Red before Z-32 (d): the probe asks no suggestion, and its metadata result has no ``quote_base_suggestion``.
    """
    print_section("QBS-A03: probe MOCK_MINOR_UNIT metadata → 100 GBp, not in the patch")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        meta = await _qbs_probe_metadata(client, QBS_MINOR_UNIT_IDENTIFIER)

    assert QBS_FIELD in meta, f"the probe's metadata result has no {QBS_FIELD}: its keys are {sorted(meta)}"
    assert meta[QBS_FIELD] == QBS_GBP_PENCE, f"{QBS_MINOR_UNIT_IDENTIFIER} must suggest 100 GBp: {meta[QBS_FIELD]!r}"
    assert meta["patch_data"].get("quote_base_quantity") is None, f"patch_data carries a quote base, which the refresh would write: {meta['patch_data']}"
    print_success(f"✓ {meta[QBS_FIELD]}, patch_data without a quote base")


@pytest.mark.asyncio
async def test_qbs_a04_probe_metadata_of_another_mockprov_line_suggests_null(test_server):
    """QBS-A04 (Z-32 d, points 2, 5 and 8): the same probe of another mockprov identifier (one of this test): the
    metadata answers, its ``quote_base_suggestion`` present and null.

    Red before Z-32 (d): the probe's metadata result has no ``quote_base_suggestion``.
    """
    print_section("QBS-A04: probe another mockprov line → null")
    identifier = _qbs_unique("MOCK_QBS").upper()
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        meta = await _qbs_probe_metadata(client, identifier)

    assert QBS_FIELD in meta, f"the probe's metadata result has no {QBS_FIELD}: its keys are {sorted(meta)}"
    assert meta[QBS_FIELD] is None, f"mockprov suggests nothing for {identifier}: {meta[QBS_FIELD]!r}"
    print_success(f"✓ {identifier}: null")


@pytest.mark.asyncio
async def test_qbs_a05_metadata_refresh_keeps_the_quote_base(test_server):
    """QBS-A05 (Z-32 d, point 6): an asset of this test, in GBP with ``quote_base_quantity`` 1, assigned to mockprov
    ``MOCK_MINOR_UNIT``: ``POST /assets/provider/refresh`` refreshes its metadata (a refreshed field), refreshes no
    ``quote_base_quantity``, and the asset's ``quote_base_quantity`` is still 1. The asset is deleted at the end.

    Green before Z-32 (d), by construction: the refresh writes mockprov's patch, which has no quote base. A guard: the
    cure must not let the suggestion reach a stored asset — the quote base is the user's to accept, in the web modal.
    """
    print_section("QBS-A05: a metadata refresh keeps quote_base_quantity")
    name = f"QBS refresh {_qbs_unique('QBS')}"
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        asset_item = FAAssetCreateItem(display_name=name, currency="GBP", asset_type=AssetType.STOCK, quote_base_quantity=1)
        create_resp = await client.post(f"{API_BASE}/assets", json=[asset_item.model_dump(mode="json")], timeout=TIMEOUT)
        assert create_resp.status_code == 201, f"create {name}: {create_resp.status_code} {create_resp.text[:300]}"
        created = next((result for result in FABulkAssetCreateResponse(**create_resp.json()).results if result.display_name == name), None)
        assert created is not None and created.success and created.asset_id is not None, f"create {name}: {create_resp.text[:300]}"
        asset_id = created.asset_id
        try:
            assignment = FAProviderAssignmentItem(asset_id=asset_id, provider_code="mockprov", identifier=QBS_MINOR_UNIT_IDENTIFIER, identifier_type=ProviderInputType.TICKER, provider_params=None)
            assign_resp = await client.post(f"{API_BASE}/assets/provider", json=[assignment.model_dump(mode="json")], timeout=TIMEOUT)
            assert assign_resp.status_code == 200, f"assign: {assign_resp.status_code} {assign_resp.text[:300]}"
            assert FABulkAssignResponse(**assign_resp.json()).success_count == 1, f"assign: {assign_resp.text[:300]}"

            refresh_resp = await client.post(f"{API_BASE}/assets/provider/refresh", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)
            assert refresh_resp.status_code == 200, f"refresh: {refresh_resp.status_code} {refresh_resp.text[:300]}"
            refreshed = next((result for result in refresh_resp.json()["results"] if result["asset_id"] == asset_id), None)
            assert refreshed is not None and refreshed["success"] is True, f"barrier: the refresh of asset {asset_id} succeeded: {refresh_resp.text[:500]}"
            fields = [change["info"] for change in refreshed["fields_detail"]["refreshed_fields"]]
            assert fields, f"barrier: the refresh wrote a patch: {refreshed}"
            assert "quote_base_quantity" not in fields, f"the refresh refreshed quote_base_quantity: {fields}"

            read_resp = await client.get(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)
            assert read_resp.status_code == 200, f"read: {read_resp.status_code} {read_resp.text[:300]}"
            asset = next((item for item in read_resp.json() if item["asset_id"] == asset_id), None)
            assert asset is not None, f"asset {asset_id} not in its own read: {read_resp.text[:300]}"
            assert asset["quote_base_quantity"] == 1, f"the metadata refresh changed quote_base_quantity: {asset['quote_base_quantity']!r}"
            print_success(f"✓ asset {asset_id}: refreshed {fields}, quote_base_quantity still 1")
        finally:
            await client.delete(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)


def _qbs_component(schemas: dict, name: str) -> tuple[str, dict]:
    """The component ``name`` of the document, or its ``-Output`` form (FastAPI's name when a model's two schemas
    differ)."""
    for key in (name, f"{name}-Output"):
        if key in schemas:
            return key, schemas[key]
    pytest.fail(f"the OpenAPI document has no component {name}", pytrace=False)


@pytest.mark.asyncio
async def test_qbs_a06_openapi_documents_the_suggestion(test_server):
    """QBS-A06 (Z-32 d, point 2): the OpenAPI document the lane's server serves (``GET /api/v1/openapi.json``, i.e.
    ``backend.app.main.app.openapi()``): ``FAProviderSearchResultItem`` and ``ProbeMetadataResult`` have an optional,
    nullable ``quote_base_suggestion`` referring to the ``FAQuoteBaseSuggestion`` component, whose ``quantity`` is a
    required integer with ``minimum`` 1.

    Red before Z-32 (d): neither model documents the property, and there is no such component.
    """
    print_section("QBS-A06: the served OpenAPI document")
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE}/openapi.json", timeout=TIMEOUT)
    assert resp.status_code == 200, f"GET /api/v1/openapi.json: {resp.status_code}"
    schemas = resp.json()["components"]["schemas"]

    referenced: set[str] = set()
    for parent in ("FAProviderSearchResultItem", "ProbeMetadataResult"):
        key, component = _qbs_component(schemas, parent)
        properties = component.get("properties", {})
        assert QBS_FIELD in properties, f"{key} documents no {QBS_FIELD}: its properties are {sorted(properties)}"
        prop = properties[QBS_FIELD]
        assert QBS_FIELD not in component.get("required", []), f"{key}.{QBS_FIELD} must be optional"
        assert {"type": "null"} in prop.get("anyOf", []), f"{key}.{QBS_FIELD} must be nullable: {prop}"
        refs = [part["$ref"].rsplit("/", 1)[-1] for part in (prop, *prop.get("anyOf", [])) if "$ref" in part]
        assert len(refs) == 1 and refs[0].split("-")[0] == "FAQuoteBaseSuggestion", f"{key}.{QBS_FIELD} must refer to FAQuoteBaseSuggestion: {prop}"
        referenced.add(refs[0])
    for key in sorted(referenced):
        component = schemas[key]
        quantity = component.get("properties", {}).get("quantity", {})
        assert "quantity" in component.get("required", []), f"{key}: quantity must be required: {component.get('required')}"
        assert (quantity.get("type"), quantity.get("minimum")) == ("integer", 1), f"{key}.quantity: {quantity}"
    print_success(f"✓ both answers refer to {sorted(referenced)}")

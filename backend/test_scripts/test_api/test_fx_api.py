"""
FX API Tests.

Tests for Foreign Exchange (FX) endpoints:
- GET /fx/providers (list FX providers with target currencies)
- POST /fx/providers/pair-sources (CRUD for pair sources)
- POST /fx/sync (sync rates from providers)
- POST /fx/convert (currency conversion)
- POST /fx/rates (manual rate upsert)
- DELETE /fx/rates (rate deletion)

Note: The former GET /fx/currencies endpoint was removed and absorbed
by GET /fx/providers which now includes target_currencies per provider.
"""

from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest

from backend.app.config import get_settings
from backend.app.schemas import FXConvertResponse, FXBulkUpsertResponse, FXBulkDeleteResponse
from backend.app.schemas.common import DateRangeModel, Currency
from backend.app.schemas.fx import (
    FXConversionRequest,
    FXUpsertItem,
    FXDeleteItem,
    FXPairSourceItem,
    FXPairSourcesResponse,
    FXCreatePairSourcesResponse,
    FXDeletePairSourceItem,
    FXProviderInfo,
    )
from backend.app.schemas.refresh import FXSyncBulkResponse
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_info, print_success

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
async def test_providers_include_target_currencies(test_server):
    """Test 1: GET /fx/providers - Providers include target_currencies field.

    This test replaces the former test_get_currencies which tested the now-removed
    GET /fx/currencies endpoint. Target currencies are now part of the providers response.
    """
    print_section("Test 1: GET /fx/providers - target_currencies")

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE}/fx/providers", timeout=TIMEOUT)

        assert (
            response.status_code == 200
        ), f"Expected 200, got {response.status_code}: {response.text}"

        providers = [FXProviderInfo(**p) for p in response.json()]
        assert len(providers) > 0, "Should have at least one provider"

        for provider in providers:
            # Validate target_currencies field exists and is populated
            assert hasattr(provider, "target_currencies"), \
                f"Provider {provider.code} should have target_currencies field"
            assert isinstance(provider.target_currencies, list), \
                f"target_currencies should be a list for {provider.code}"
            assert len(provider.target_currencies) > 0, \
                f"Provider {provider.code} should have at least one target currency"

            # Validate currency codes format
            for currency in provider.target_currencies:
                assert len(currency) == 3, \
                    f"Currency code should be 3 chars: {currency} (provider: {provider.code})"
                assert currency.isupper(), \
                    f"Currency code should be uppercase: {currency} (provider: {provider.code})"

            # Base currency should be included in target currencies
            assert provider.base_currency in provider.target_currencies, \
                f"Base currency {provider.base_currency} should be in target_currencies for {provider.code}"

            print_success(
                f"✓ {provider.code}: {len(provider.target_currencies)} target currencies, "
                f"base_currencies={provider.base_currencies}"
            )


@pytest.mark.asyncio
async def test_old_currencies_endpoint_removed(test_server):
    """Test 1b: GET /fx/currencies - Should return 404/405 (endpoint removed)."""
    print_section("Test 1b: GET /fx/currencies - Removed endpoint")

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE}/fx/currencies", timeout=TIMEOUT)

        assert response.status_code in (404, 405), \
            f"Expected 404 or 405 for removed endpoint, got {response.status_code}"

        print_success("✓ GET /fx/currencies correctly removed (returns 404/405)")


@pytest.mark.asyncio
async def test_get_providers(test_server):
    """Test 2: GET /fx/providers - List FX providers with full info."""
    print_section("Test 2: GET /fx/providers")

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE}/fx/providers", timeout=TIMEOUT)

        assert (
            response.status_code == 200
        ), f"Expected 200, got {response.status_code}: {response.text}"

        # Parse response as List[FXProviderInfo]
        providers = [FXProviderInfo(**p) for p in response.json()]

        assert len(providers) > 0, "Should have at least one provider"

        # Validate each provider
        for provider in providers:
            assert provider.code, "Provider should have code"
            assert provider.name, "Provider should have name"
            assert provider.base_currency, "Provider should have base_currency"
            assert provider.base_currencies, "Provider should have base_currencies"
            assert provider.target_currencies, "Provider should have target_currencies"
            assert hasattr(provider, "icon_url"), "Provider should have icon_url field"
            # base_currency should be in base_currencies
            assert provider.base_currency in provider.base_currencies, \
                f"base_currency {provider.base_currency} should be in base_currencies"

        print_success(f"✓ Found {len(providers)} providers")
        print_info(f"  Providers: {', '.join([p.code for p in providers])}")

        # 2b. Test providers filter (single provider)
        print_info("2b. Filter by single provider (ECB)")
        response_filtered = await client.get(
            f"{API_BASE}/fx/providers",
            params={"providers": ["ECB"]},
            timeout=TIMEOUT,
            )
        assert response_filtered.status_code == 200
        filtered = [FXProviderInfo(**p) for p in response_filtered.json()]
        assert len(filtered) == 1, f"Expected 1 provider, got {len(filtered)}"
        assert filtered[0].code == "ECB"
        print_success("✓ Single provider filter works")

        # 2c. Test providers filter (multiple providers)
        print_info("2c. Filter by multiple providers (ECB, FED)")
        response_multi = await client.get(
            f"{API_BASE}/fx/providers",
            params={"providers": ["ECB", "FED"]},
            timeout=TIMEOUT,
            )
        assert response_multi.status_code == 200
        multi = [FXProviderInfo(**p) for p in response_multi.json()]
        assert len(multi) == 2, f"Expected 2 providers, got {len(multi)}"
        codes = {p.code for p in multi}
        assert codes == {"ECB", "FED"}, f"Expected ECB & FED, got {codes}"
        print_success("✓ Multi-provider filter works")

        # 2d. No filter returns all providers
        print_info("2d. No filter returns all")
        response_all = await client.get(f"{API_BASE}/fx/providers", timeout=TIMEOUT)
        all_providers = [FXProviderInfo(**p) for p in response_all.json()]
        assert len(all_providers) >= 4, f"Expected >= 4, got {len(all_providers)}"
        print_success(f"✓ No filter returns {len(all_providers)} providers")


@pytest.mark.asyncio
async def test_pair_sources_crud(test_server):
    """Test 3: POST /fx/providers/pair-sources - CRUD operations for pair sources."""
    print_section("Test 3: POST /fx/providers/pair-sources - CRUD")

    async with httpx.AsyncClient() as client:
        # 3a. List all pair sources (empty or existing)
        print_info("3a. List pair sources")
        response = await client.get(f"{API_BASE}/fx/providers/pair-sources", timeout=TIMEOUT)
        assert response.status_code == 200, f"GET failed: {response.status_code}"
        sources_response = FXPairSourcesResponse(**response.json())
        print_success(f"✓ Listed {len(sources_response.items)} initial sources")

        # 3b. Create a new pair source
        print_info("3b. Create pair source (USD/EUR)")
        create_request_sources = [
            FXPairSourceItem(
                base="USD",
                quote="EUR",
                provider_code="ECB",
                priority=2,  # Use priority 2 to avoid conflict with existing EUR/USD priority 1
                )
            ]
        response = await client.post(
            f"{API_BASE}/fx/providers/pair-sources",
            json=[s.model_dump(mode="json") for s in create_request_sources],
            timeout=TIMEOUT,
            )
        assert response.status_code == 201, f"POST failed: {response.status_code}: {response.text}"
        create_response = FXCreatePairSourcesResponse(**response.json())
        assert create_response.success_count == 1, "Should create 1 source"
        print_success("✓ Pair source created")

        # 3c. Read back to verify
        print_info("3c. Read back to verify")
        response = await client.get(f"{API_BASE}/fx/providers/pair-sources", timeout=TIMEOUT)
        assert response.status_code == 200, f"GET failed: {response.status_code}"
        sources_response = FXPairSourcesResponse(**response.json())
        usd_eur_sources = [
            s for s in sources_response.items if s.base == "USD" and s.quote == "EUR"
            ]
        assert len(usd_eur_sources) > 0, "USD/EUR source should exist"
        print_success("✓ Pair source verified")

        # 3d. Update priority
        print_info("3d. Update priority")
        update_request_sources = [
            FXPairSourceItem(
                base="USD", quote="EUR", provider_code="ECB", priority=3  # Update to priority 3
                )
            ]
        response = await client.post(
            f"{API_BASE}/fx/providers/pair-sources",
            json=[s.model_dump(mode="json") for s in update_request_sources],
            timeout=TIMEOUT,
            )
        assert response.status_code == 201, f"POST failed: {response.status_code}"
        update_response = FXCreatePairSourcesResponse(**response.json())
        assert update_response.success_count == 1, "Should update 1 source"
        print_success("✓ Priority updated")

        # 3e. Delete pair source
        print_info("3e. Delete pair source")

        delete_request_sources = [FXDeletePairSourceItem(base="USD", quote="EUR")]
        response = await client.request(
            method="DELETE",
            url=f"{API_BASE}/fx/providers/pair-sources",
            json=[s.model_dump(mode="json") for s in delete_request_sources],
            headers={"Content-Type": "application/json"},
            timeout=TIMEOUT,
            )
        assert (
            response.status_code == 200
        ), f"DELETE failed: {response.status_code}: {response.text}"
        print_success("✓ Pair source deleted")


@pytest.mark.asyncio
async def test_sync_rates(test_server):
    """Test 4: POST /fx/currencies/sync - Pair-based sync."""
    print_section("Test 4: POST /fx/currencies/sync")

    async with httpx.AsyncClient() as client:
        today = date.today()
        yesterday = today - timedelta(days=1)

        # Ensure pair sources exist
        await client.post(
            f"{API_BASE}/fx/providers/pair-sources",
            json=[{"base": "EUR", "quote": "GBP", "provider_code": "ECB", "priority": 1}],
            timeout=TIMEOUT,
            )

        # Sync rates using POST with pair slugs
        response = await client.post(
            f"{API_BASE}/fx/currencies/sync",
            json={
                "pairs": ["EUR-GBP"],
                "start": yesterday.isoformat(),
                "end": yesterday.isoformat(),
                },
            timeout=TIMEOUT,
            )

        assert (
            response.status_code == 200
        ), f"Expected 200, got {response.status_code}: {response.text}"

        sync_response = FXSyncBulkResponse(**response.json())
        assert len(sync_response.results) == 1
        pr = sync_response.results[0]
        assert pr.pair == "EUR-GBP"
        print_success(f"✓ Sync completed: status={pr.status}, pts_changed={pr.points_changed}")

        # Cleanup
        await client.request(
            "DELETE",
            f"{API_BASE}/fx/providers/pair-sources",
            json=[{"base": "EUR", "quote": "GBP"}],
            timeout=TIMEOUT,
            )


@pytest.mark.asyncio
async def test_sync_rates_auto_config(test_server):
    """Test 4b: POST /fx/currencies/sync - Auto-config mode with pair sources."""
    print_section("Test 4b: POST /fx/currencies/sync - Auto-config")

    async with httpx.AsyncClient() as client:
        today = date.today()
        yesterday = today - timedelta(days=1)

        # Step 1: Create pair source configuration in DB
        print_info("Step 1: Configure pair sources in DB")

        pair_sources = [
            FXPairSourceItem(base="EUR", quote="USD", provider_code="ECB", priority=1),
            FXPairSourceItem(base="GBP", quote="USD", provider_code="ECB", priority=1),
            ]

        create_response = await client.post(
            f"{API_BASE}/fx/providers/pair-sources",
            json=[s.model_dump(mode="json") for s in pair_sources],
            timeout=TIMEOUT,
            )
        assert (
            create_response.status_code == 201
        ), f"Expected 201, got {create_response.status_code}: {create_response.text}"

        create_data = FXCreatePairSourcesResponse(**create_response.json())
        assert create_data.success_count >= 2, "Should create at least 2 pair sources"
        print_success(f"✓ Created {create_data.success_count} pair sources")

        # Step 2: Sync rates using POST with pair slugs
        print_info("Step 2: Sync rates using pair slugs")

        sync_response = await client.post(
            f"{API_BASE}/fx/currencies/sync",
            json={
                "pairs": ["EUR-USD", "GBP-USD"],
                "start": yesterday.isoformat(),
                "end": yesterday.isoformat(),
                },
            timeout=TIMEOUT,
            )

        assert (
            sync_response.status_code == 200
        ), f"Expected 200, got {sync_response.status_code}: {sync_response.text}"

        sync_data = FXSyncBulkResponse(**sync_response.json())
        assert len(sync_data.results) == 2
        print_success(f"✓ Auto-config sync: {sync_data.success_count}/{len(sync_data.results)} ok")
        for pr in sync_data.results:
            print_info(f"  {pr.pair}: status={pr.status}, pts={pr.points_changed}")

        # Step 3: Cleanup - delete pair sources
        print_info("Step 3: Cleanup pair sources")

        delete_sources = [
            FXDeletePairSourceItem(base="EUR", quote="USD"),
            FXDeletePairSourceItem(base="GBP", quote="USD"),
            ]
        delete_response = await client.request(
            method="DELETE",
            url=f"{API_BASE}/fx/providers/pair-sources",
            json=[s.model_dump(mode="json") for s in delete_sources],
            timeout=TIMEOUT,
            )

        assert (
            delete_response.status_code == 200
        ), f"Expected 200, got {delete_response.status_code}"
        print_success("✓ Cleanup completed")


@pytest.mark.asyncio
async def test_convert_currency(test_server):
    """Test 5: POST /fx/currencies/convert - Currency conversion."""
    print_section("Test 5: POST /fx/currencies/convert")

    async with httpx.AsyncClient() as client:
        today = date.today()

        # First, ensure we have rates (sync via POST)
        await client.post(
            f"{API_BASE}/fx/providers/pair-sources",
            json=[{"base": "EUR", "quote": "GBP", "provider_code": "ECB", "priority": 1}],
            timeout=TIMEOUT,
            )
        await client.post(
            f"{API_BASE}/fx/currencies/sync",
            json={
                "pairs": ["EUR-GBP"],
                "start": (today - timedelta(days=7)).isoformat(),
                "end": today.isoformat(),
                },
            timeout=TIMEOUT,
            )

        # Now convert (use List directly)
        conversions = [
            FXConversionRequest(
                from_amount=Currency(code="USD", amount=Decimal("100")),
                **{"to": "EUR"},  # Use dict unpacking for aliased fields test
                date_range=DateRangeModel(start=today - timedelta(days=1)),
                )
            ]

        response = await client.post(
            f"{API_BASE}/fx/currencies/convert",
            json=[c.model_dump(mode="json") for c in conversions],
            timeout=TIMEOUT,
            )

        assert (
            response.status_code == 200
        ), f"Expected 200, got {response.status_code}: {response.text}"

        convert_response = FXConvertResponse(**response.json())

        if len(convert_response.results) > 0:
            result = convert_response.results[0]
            assert result.from_amount.amount == Decimal("100"), "Original amount should be 100"
            assert result.from_amount.code == "USD", "From currency should be USD"
            assert result.to_amount.code == "EUR", "To currency should be EUR"
            assert result.to_amount.amount > 0, "Converted amount should be positive"
            print_success(f"✓ Converted 100 USD to {result.to_amount.amount} EUR")
        else:
            print_info("ℹ️  No conversion result (rate may not be available)")


@pytest.mark.asyncio
async def test_convert_missing_rate(test_server):
    """Test 6: POST /fx/currencies/convert - Conversion with missing rate."""
    print_section("Test 6: POST /fx/currencies/convert - Missing Rate")

    async with httpx.AsyncClient() as client:
        # Use a fake currency pair that definitely doesn't exist
        conversions = [
            {
                "from_amount": {"code": "xxx", "amount": "100"},
                "to": "yyy",
                "date_range": {"start": date.today().isoformat()},
                }
            ]

        response = await client.post(
            f"{API_BASE}/fx/currencies/convert", json=conversions, timeout=TIMEOUT
            )

        # Should either return 200 with errors or 4xx
        if response.status_code == 200:
            convert_response = FXConvertResponse(**response.json())
            assert (
                len(convert_response.errors) > 0 or len(convert_response.results) == 0
            ), "Should have errors or no results for invalid currencies"
            print_success("✓ Missing rate handled gracefully (errors in response)")
        else:
            assert response.status_code in [
                400,
                404,
                422,
                ], f"Expected 400/404/422 for invalid currencies, got {response.status_code}"
            print_success(f"✓ Missing rate rejected with {response.status_code}")


@pytest.mark.asyncio
async def test_manual_rate_upsert(test_server):
    """Test 7: POST /fx/currencies/rate - Manual rate upsert."""
    print_section("Test 7: POST /fx/currencies/rate - Manual Upsert")

    async with httpx.AsyncClient() as client:
        today = date.today()

        # Upsert a test rate (use List directly)
        rates = [
            FXUpsertItem(
                **{"date": today},  # Use dict unpacking for aliased field
                base="GBP",
                quote="USD",
                rate=Decimal("1.25"),
                source="MANUAL",
                )
            ]

        response = await client.post(
            f"{API_BASE}/fx/currencies/rate",
            json=[r.model_dump(mode="json") for r in rates],
            timeout=TIMEOUT,
            )

        assert (
            response.status_code == 200
        ), f"Expected 200, got {response.status_code}: {response.text}"

        upsert_response = FXBulkUpsertResponse(**response.json())

        assert upsert_response.success_count == 1, "Should have 1 success"
        assert len(upsert_response.results) == 1, "Should have 1 result"

        result = upsert_response.results[0]
        assert result.success, "Upsert should succeed"
        assert result.base == "GBP", "Base should be GBP"
        assert result.quote == "USD", "Quote should be USD"
        assert result.rate == Decimal("1.25"), "Rate should be 1.25"
        assert result.action in ["inserted", "updated"], f"Invalid action: {result.action}"

        print_success(f"✓ Rate {result.action}: GBP/USD = 1.25")


@pytest.mark.asyncio
async def test_bulk_conversions(test_server):
    """Test 8: POST /fx/currencies/convert - Bulk conversions."""
    print_section("Test 8: POST /fx/currencies/convert - Bulk")

    async with httpx.AsyncClient() as client:
        today = date.today()

        # Setup: Ensure we have some rates
        upsert_rates = [
            FXUpsertItem(
                **{"date": today}, base="USD", quote="EUR", rate=Decimal("0.85"), source="MANUAL"
                ),
            FXUpsertItem(
                **{"date": today}, base="GBP", quote="USD", rate=Decimal("1.25"), source="MANUAL"
                ),
            ]
        await client.post(
            f"{API_BASE}/fx/currencies/rate",
            json=[r.model_dump(mode="json") for r in upsert_rates],
            timeout=TIMEOUT,
            )

        # Bulk convert
        conversions = [
            FXConversionRequest(
                from_amount=Currency(code="USD", amount=Decimal("100")),
                to="EUR",
                date_range=DateRangeModel(start=today),
                ),
            FXConversionRequest(
                from_amount=Currency(code="GBP", amount=Decimal("200")),
                to="USD",
                date_range=DateRangeModel(start=today),
                ),
            ]

        response = await client.post(
            f"{API_BASE}/fx/currencies/convert",
            json=[c.model_dump(mode="json") for c in conversions],
            timeout=TIMEOUT,
            )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        convert_response = FXConvertResponse(**response.json())
        assert len(convert_response.results) == 2, "Should have 2 results"

        print_success(f"✓ Bulk conversion completed: {len(convert_response.results)} results")


@pytest.mark.asyncio
async def test_bulk_rate_upserts(test_server):
    """Test 9: POST /fx/currencies/rate - Bulk rate upserts."""
    print_section("Test 9: POST /fx/currencies/rate - Bulk Upserts")

    async with httpx.AsyncClient() as client:
        today = date.today()

        # Bulk upsert
        rates = [
            FXUpsertItem(
                **{"date": today}, base="EUR", quote="USD", rate=Decimal("1.10"), source="MANUAL"
                ),
            FXUpsertItem(
                **{"date": today}, base="JPY", quote="USD", rate=Decimal("0.0067"), source="MANUAL"
                ),
            FXUpsertItem(
                **{"date": today}, base="CHF", quote="USD", rate=Decimal("1.12"), source="MANUAL"
                ),
            ]

        response = await client.post(
            f"{API_BASE}/fx/currencies/rate",
            json=[r.model_dump(mode="json") for r in rates],
            timeout=TIMEOUT,
            )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        upsert_response = FXBulkUpsertResponse(**response.json())
        assert (
            upsert_response.success_count == 3
        ), f"Expected 3 successes, got {upsert_response.success_count}"
        assert len(upsert_response.results) == 3, "Should have 3 results"

        print_success(f"✓ Bulk upsert: {upsert_response.success_count} rates inserted/updated")


@pytest.mark.asyncio
async def test_delete_rates(test_server):
    """Test 10: DELETE /fx/currencies/rate - Rate deletion."""
    print_section("Test 10: DELETE /fx/currencies/rate")

    async with httpx.AsyncClient() as client:
        today = date.today()
        yesterday = today - timedelta(days=1)

        # Setup: Insert some test rates
        upsert_rates = [
            FXUpsertItem(
                **{"date": yesterday},
                base="AUD",
                quote="USD",
                rate=Decimal("0.65"),
                source="MANUAL",
                ),
            FXUpsertItem(
                **{"date": today}, base="AUD", quote="USD", rate=Decimal("0.66"), source="MANUAL"
                ),
            ]
        await client.post(
            f"{API_BASE}/fx/currencies/rate",
            json=[r.model_dump(mode="json") for r in upsert_rates],
            timeout=TIMEOUT,
            )

        # Delete rate range
        deletions = [
            FXDeleteItem(
                **{"from": "AUD", "to": "USD"},  # Use dict unpacking for aliased fields
                date_range=DateRangeModel(start=yesterday, end=today),
                )
            ]

        response = await client.request(
            method="DELETE",
            url=f"{API_BASE}/fx/currencies/rate",
            json=[d.model_dump(mode="json") for d in deletions],
            headers={"Content-Type": "application/json"},
            timeout=TIMEOUT,
            )

        assert (
            response.status_code == 200
        ), f"Expected 200, got {response.status_code}: {response.text}"

        delete_response = FXBulkDeleteResponse(**response.json())
        assert len(delete_response.results) == 1, "Should have 1 result"

        result = delete_response.results[0]
        assert result.success, "Deletion should succeed"
        assert result.deleted_count >= 0, "Deleted count should be non-negative"

        print_success(f"✓ Deleted {result.deleted_count} rates (AUD/USD)")


@pytest.mark.asyncio
async def test_invalid_requests(test_server):
    """Test 11: Invalid request handling."""
    print_section("Test 11: Invalid Request Handling")

    async with httpx.AsyncClient() as client:
        # 11a. Invalid currency code (too short)
        print_info("11a. Invalid currency code")
        request = {
            "conversions": [
                {
                    "amount": "100",
                    "from": "US",  # Too short
                    "to": "EUR",
                    "start_date": date.today().isoformat(),
                    }
                ]
            }
        response = await client.post(
            f"{API_BASE}/fx/currencies/convert", json=request, timeout=TIMEOUT
            )
        assert (
            response.status_code == 422
        ), f"Expected 422 for invalid currency, got {response.status_code}"
        print_success("✓ Invalid currency rejected with 422")

        # 11b. Negative amount
        print_info("11b. Negative amount")
        request = {
            "conversions": [
                {
                    "amount": "-100",
                    "from": "USD",
                    "to": "EUR",
                    "start_date": date.today().isoformat(),
                    }
                ]
            }
        response = await client.post(
            f"{API_BASE}/fx/currencies/convert", json=request, timeout=TIMEOUT
            )
        assert (
            response.status_code == 422
        ), f"Expected 422 for negative amount, got {response.status_code}"
        print_success("✓ Negative amount rejected with 422")

        # 11c. Missing required field
        print_info("11c. Missing required field")
        request = {
            "conversions": [
                {
                    "amount": "100",
                    "from": "USD",
                    # Missing "to" field
                    "start_date": date.today().isoformat(),
                    }
                ]
            }
        response = await client.post(
            f"{API_BASE}/fx/currencies/convert", json=request, timeout=TIMEOUT
            )
        assert (
            response.status_code == 422
        ), f"Expected 422 for missing field, got {response.status_code}"
        print_success("✓ Missing field rejected with 422")

        # 11d. Invalid rate (zero)
        print_info("11d. Invalid rate (zero)")
        request = {
            "rates": [
                {
                    "date": date.today().isoformat(),
                    "base": "USD",
                    "quote": "EUR",
                    "rate": "0",  # Zero rate
                    "source": "MANUAL",
                    }
                ]
            }
        response = await client.post(
            f"{API_BASE}/fx/currencies/rate", json=request, timeout=TIMEOUT
            )
        assert (
            response.status_code == 422
        ), f"Expected 422 for zero rate, got {response.status_code}"
        print_success("✓ Zero rate rejected with 422")

        # 11e. Invalid date format
        print_info("11e. Invalid date format")
        request = {
            "conversions": [
                {"amount": "100", "from": "USD", "to": "EUR", "start_date": "invalid-date"}
                ]
            }
        response = await client.post(
            f"{API_BASE}/fx/currencies/convert", json=request, timeout=TIMEOUT
            )
        assert (
            response.status_code == 422
        ), f"Expected 422 for invalid date, got {response.status_code}"
        print_success("✓ Invalid date rejected with 422")


# ============================================================================
# MANUAL PROVIDER TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_manual_provider_hidden_from_list(test_server):
    """Test 12: MANUAL provider should NOT appear in GET /fx/providers."""
    print_section("Test 12: MANUAL provider hidden from GET /fx/providers")

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE}/fx/providers", timeout=TIMEOUT)
        assert response.status_code == 200

        providers = response.json()
        provider_codes = [p["code"] for p in providers]
        assert "MANUAL" not in provider_codes, \
            f"MANUAL should NOT appear in provider list, got: {provider_codes}"
        print_success(f"✓ MANUAL not in provider list: {provider_codes}")


@pytest.mark.asyncio
async def test_manual_pair_creation(test_server):
    """Test 13: Create a pair with only MANUAL provider."""
    print_section("Test 13: Create MANUAL-only pair")

    async with httpx.AsyncClient() as client:
        # Create a MANUAL-only pair
        create_data = [
            {"base": "BRL", "quote": "MXN", "provider_code": "MANUAL", "priority": 999}
        ]
        response = await client.post(
            f"{API_BASE}/fx/providers/pair-sources", json=create_data, timeout=TIMEOUT
        )
        assert response.status_code == 201, f"POST failed: {response.status_code}: {response.text}"
        print_success("✓ Created BRL/MXN with MANUAL provider")

        # Verify it appears in pair-sources
        response = await client.get(f"{API_BASE}/fx/providers/pair-sources", timeout=TIMEOUT)
        assert response.status_code == 200
        items = response.json()["items"]
        manual_pairs = [i for i in items if i["base"] == "BRL" and i["quote"] == "MXN"]
        assert len(manual_pairs) == 1, f"Expected 1 MANUAL pair, got {manual_pairs}"
        assert manual_pairs[0]["provider_code"] == "MANUAL"
        assert manual_pairs[0]["priority"] == 999
        print_success("✓ BRL/MXN MANUAL pair visible in pair-sources")


@pytest.mark.asyncio
async def test_manual_auto_removed_on_real_provider(test_server):
    """Test 14: MANUAL auto-removed when a real provider is added to the same pair."""
    print_section("Test 14: MANUAL auto-removed when real provider added")

    async with httpx.AsyncClient() as client:
        # First create a MANUAL-only pair
        create_manual = [
            {"base": "DKK", "quote": "PLN", "provider_code": "MANUAL", "priority": 999}
        ]
        response = await client.post(
            f"{API_BASE}/fx/providers/pair-sources", json=create_manual, timeout=TIMEOUT
        )
        assert response.status_code == 201
        print_success("✓ Created DKK/PLN with MANUAL")

        # Now add a real provider to the same pair
        create_real = [
            {"base": "DKK", "quote": "PLN", "provider_code": "ECB", "priority": 1}
        ]
        response = await client.post(
            f"{API_BASE}/fx/providers/pair-sources", json=create_real, timeout=TIMEOUT
        )
        assert response.status_code == 201
        print_success("✓ Added ECB to DKK/PLN")

        # Verify MANUAL was auto-removed
        response = await client.get(f"{API_BASE}/fx/providers/pair-sources", timeout=TIMEOUT)
        assert response.status_code == 200
        items = response.json()["items"]
        dkk_pln = [i for i in items if i["base"] == "DKK" and i["quote"] == "PLN"]
        provider_codes = [i["provider_code"] for i in dkk_pln]
        assert "MANUAL" not in provider_codes, \
            f"MANUAL should have been auto-removed, but found: {provider_codes}"
        assert "ECB" in provider_codes, f"ECB should be present: {provider_codes}"
        print_success(f"✓ MANUAL auto-removed, remaining providers: {provider_codes}")

        # Cleanup
        await client.request(
            "DELETE", f"{API_BASE}/fx/providers/pair-sources",
            json=[{"base": "DKK", "quote": "PLN"}], timeout=TIMEOUT
        )


@pytest.mark.asyncio
async def test_manual_auto_reinstated_on_last_provider_removed(test_server):
    """Test 15: MANUAL auto-reinstated when the last real provider is removed."""
    print_section("Test 15: MANUAL auto-reinstated when last provider removed")

    async with httpx.AsyncClient() as client:
        # Create a pair with a real provider
        create_real = [
            {"base": "HUF", "quote": "RON", "provider_code": "ECB", "priority": 1}
        ]
        response = await client.post(
            f"{API_BASE}/fx/providers/pair-sources", json=create_real, timeout=TIMEOUT
        )
        assert response.status_code == 201
        print_success("✓ Created HUF/RON with ECB")

        # Remove the real provider
        delete_data = [
            {"base": "HUF", "quote": "RON", "priority": 1}
        ]
        response = await client.request(
            "DELETE", f"{API_BASE}/fx/providers/pair-sources",
            json=delete_data, timeout=TIMEOUT
        )
        assert response.status_code == 200
        print_success("✓ Removed ECB from HUF/RON")

        # Verify MANUAL was auto-reinstated
        response = await client.get(f"{API_BASE}/fx/providers/pair-sources", timeout=TIMEOUT)
        assert response.status_code == 200
        items = response.json()["items"]
        huf_ron = [i for i in items if i["base"] == "HUF" and i["quote"] == "RON"]
        assert len(huf_ron) == 1, f"Expected 1 entry (MANUAL), got {huf_ron}"
        assert huf_ron[0]["provider_code"] == "MANUAL"
        assert huf_ron[0]["priority"] == 999
        print_success("✓ MANUAL auto-reinstated for HUF/RON")

        # Cleanup
        await client.request(
            "DELETE", f"{API_BASE}/fx/providers/pair-sources",
            json=[{"base": "HUF", "quote": "RON"}], timeout=TIMEOUT
        )


@pytest.mark.asyncio
async def test_manual_sync_returns_empty(test_server):
    """Test 16: Sync with MANUAL provider should return 0 results, no errors."""
    print_section("Test 16: Sync with MANUAL provider — silent skip")

    async with httpx.AsyncClient() as client:
        # Create a MANUAL-only pair
        create_data = [
            {"base": "ISK", "quote": "TRY", "provider_code": "MANUAL", "priority": 999}
        ]
        response = await client.post(
            f"{API_BASE}/fx/providers/pair-sources", json=create_data, timeout=TIMEOUT
        )
        assert response.status_code == 201

        # Attempt sync — should not error
        # Specify ISK-TRY pair to focus on the MANUAL pair
        response = await client.post(
            f"{API_BASE}/fx/currencies/sync",
            json={"pairs": ["ISK-TRY"], "start": "2025-01-01", "end": "2025-01-05"},
            timeout=TIMEOUT
        )
        # Sync should succeed (200) — MANUAL pairs are skipped
        assert response.status_code == 200, \
            f"Sync should succeed with MANUAL pairs, got {response.status_code}: {response.text}"
        sync_data = FXSyncBulkResponse(**response.json())
        assert len(sync_data.results) == 1
        assert sync_data.results[0].status == "skipped"
        print_success("✓ Sync completed successfully with MANUAL pair (skipped status)")

        # Cleanup
        await client.request(
            "DELETE", f"{API_BASE}/fx/providers/pair-sources",
            json=[{"base": "ISK", "quote": "TRY"}], timeout=TIMEOUT
        )


@pytest.mark.asyncio
async def test_manual_full_pair_delete_no_reinstate(test_server):
    """Test 17: Full pair delete (no priority) should NOT reinstate MANUAL."""
    print_section("Test 17: Full pair delete does not reinstate MANUAL")

    async with httpx.AsyncClient() as client:
        # Create a MANUAL-only pair
        create_data = [
            {"base": "ARS", "quote": "CLP", "provider_code": "MANUAL", "priority": 999}
        ]
        response = await client.post(
            f"{API_BASE}/fx/providers/pair-sources", json=create_data, timeout=TIMEOUT
        )
        assert response.status_code == 201
        print_success("✓ Created ARS/CLP with MANUAL")

        # Delete entire pair (no priority = delete ALL)
        response = await client.request(
            "DELETE", f"{API_BASE}/fx/providers/pair-sources",
            json=[{"base": "ARS", "quote": "CLP"}], timeout=TIMEOUT
        )
        assert response.status_code == 200
        print_success("✓ Deleted ARS/CLP (full pair)")

        # Verify pair is completely gone — MANUAL was NOT reinstated
        response = await client.get(f"{API_BASE}/fx/providers/pair-sources", timeout=TIMEOUT)
        assert response.status_code == 200
        items = response.json()["items"]
        ars_clp = [i for i in items if i["base"] == "ARS" and i["quote"] == "CLP"]
        assert len(ars_clp) == 0, \
            f"Pair should be completely deleted, but found: {ars_clp}"
        print_success("✓ Full pair delete: pair completely gone, MANUAL NOT reinstated")


@pytest.mark.asyncio
async def test_manual_cleanup_from_previous_tests(test_server):
    """Test 18: Cleanup pairs created by earlier MANUAL tests."""
    print_section("Test 18: Cleanup MANUAL test pairs")

    async with httpx.AsyncClient() as client:
        # Cleanup BRL/MXN from test 13
        await client.request(
            "DELETE", f"{API_BASE}/fx/providers/pair-sources",
            json=[{"base": "BRL", "quote": "MXN"}], timeout=TIMEOUT
        )
        print_success("✓ Cleanup BRL/MXN")



"""
FX API Tests.

Tests for Foreign Exchange (FX) endpoints:
- GET /fx/currencies (list supported currencies)
- GET /fx/providers (list FX providers)
- POST /fx/pair-sources (CRUD for pair sources)
- POST /fx/sync (sync rates from providers)
- POST /fx/convert (currency conversion)
- POST /fx/rates (manual rate upsert)
- DELETE /fx/rates (rate deletion)
"""
import time
from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest

from backend.app.config import get_settings
from backend.app.schemas import (
    FXConvertRequest, FXConvertResponse,
    FXBulkUpsertRequest, FXBulkUpsertResponse,
    FXBulkDeleteRequest, FXBulkDeleteResponse,
    )
from backend.app.schemas.fx import (
    FXProvidersResponse, FXConversionRequest, FXUpsertItem, FXDeleteItem, FXPairSourceItem, FXPairSourcesResponse,
    FXCreatePairSourcesRequest, FXCreatePairSourcesResponse,
    FXDeletePairSourcesRequest,
    )
from backend.app.schemas.refresh import FXSyncResponse
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_info, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30

# Helper to generate unique identifiers
_counter = 0


def unique_id(prefix: str = "TEST") -> str:
    """Generate unique identifier for test data."""
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
async def test_get_currencies(test_server):
    """Test 1: GET /fx/currencies - List supported currencies."""
    print_section("Test 1: GET /fx/currencies")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE}/fx/currencies",
            timeout=TIMEOUT
            )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()

        # Validate response structure
        assert "currencies" in data, "Response should have 'currencies' field"
        assert "count" in data, "Response should have 'count' field"
        assert isinstance(data["currencies"], list), "currencies should be a list"
        assert data["count"] == len(data["currencies"]), "count should match currencies length"

        # Validate currency codes
        for currency in data["currencies"]:
            assert len(currency) == 3, f"Currency code should be 3 chars: {currency}"
            assert currency.isupper(), f"Currency code should be uppercase: {currency}"

        print_success(f"✓ Found {data['count']} currencies")


@pytest.mark.asyncio
async def test_get_providers(test_server):
    """Test 2: GET /fx/providers - List FX providers."""
    print_section("Test 2: GET /fx/providers")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE}/fx/providers",
            timeout=TIMEOUT
            )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        # Parse response using Pydantic
        providers_response = FXProvidersResponse(**response.json())

        assert providers_response.count > 0, "Should have at least one provider"
        assert len(providers_response.providers) == providers_response.count, "Count mismatch"

        # Validate each provider
        for provider in providers_response.providers:
            assert provider.code, "Provider should have code"
            assert provider.name, "Provider should have name"
            assert provider.base_currency, "Provider should have base_currency"
            assert len(provider.base_currencies) > 0, "Provider should have at least one base currency"
            assert provider.description, "Provider should have description"

        print_success(f"✓ Found {providers_response.count} providers")
        print_info(f"  Providers: {', '.join([p.code for p in providers_response.providers])}")


@pytest.mark.asyncio
async def test_pair_sources_crud(test_server):
    """Test 3: POST /fx/pair-sources/bulk - CRUD operations for pair sources."""
    print_section("Test 3: POST /fx/pair-sources/bulk - CRUD")

    async with httpx.AsyncClient() as client:
        # 3a. List all pair sources (empty or existing)
        print_info("3a. List pair sources")
        response = await client.get(
            f"{API_BASE}/fx/pair-sources",
            timeout=TIMEOUT
            )
        assert response.status_code == 200, f"GET failed: {response.status_code}"
        sources_response = FXPairSourcesResponse(**response.json())
        print_success(f"✓ Listed {sources_response.count} initial sources")

        # 3b. Create a new pair source
        print_info("3b. Create pair source (USD/EUR)")
        create_request = FXCreatePairSourcesRequest(
            sources=[
                FXPairSourceItem(
                    base="USD",
                    quote="EUR",
                    provider_code="ECB",
                    priority=1
                    )
                ]
            )
        response = await client.post(
            f"{API_BASE}/fx/pair-sources/bulk",
            json=create_request.model_dump(mode="json"),
            timeout=TIMEOUT
            )
        assert response.status_code == 201, f"POST failed: {response.status_code}: {response.text}"
        create_response = FXCreatePairSourcesResponse(**response.json())
        assert create_response.success_count == 1, "Should create 1 source"
        print_success("✓ Pair source created")

        # 3c. Read back to verify
        print_info("3c. Read back to verify")
        response = await client.get(
            f"{API_BASE}/fx/pair-sources",
            timeout=TIMEOUT
            )
        assert response.status_code == 200, f"GET failed: {response.status_code}"
        sources_response = FXPairSourcesResponse(**response.json())
        usd_eur_sources = [s for s in sources_response.sources
                           if s.base == 'USD' and s.quote == 'EUR']
        assert len(usd_eur_sources) > 0, "USD/EUR source should exist"
        print_success("✓ Pair source verified")

        # 3d. Update priority
        print_info("3d. Update priority")
        update_request = FXCreatePairSourcesRequest(
            sources=[
                FXPairSourceItem(
                    base="USD",
                    quote="EUR",
                    provider_code="ECB",
                    priority=2
                    )
                ]
            )
        response = await client.post(
            f"{API_BASE}/fx/pair-sources/bulk",
            json=update_request.model_dump(mode="json"),
            timeout=TIMEOUT
            )
        assert response.status_code == 201, f"POST failed: {response.status_code}"
        update_response = FXCreatePairSourcesResponse(**response.json())
        assert update_response.success_count == 1, "Should update 1 source"
        print_success("✓ Priority updated")

        # 3e. Delete pair source
        print_info("3e. Delete pair source")

        delete_request = FXDeletePairSourcesRequest(
            sources=[
                {"base": "USD", "quote": "EUR", "provider_code": "ECB"}
                ]
            )
        response = await client.request(
            method="DELETE",
            url=f"{API_BASE}/fx/pair-sources/bulk",
            content=delete_request.model_dump_json(),
            headers={"Content-Type": "application/json"},
            timeout=TIMEOUT
            )
        assert response.status_code == 200, f"DELETE failed: {response.status_code}: {response.text}"
        print_success("✓ Pair source deleted")


@pytest.mark.asyncio
async def test_sync_rates(test_server):
    """Test 4: POST /fx/sync/bulk - Sync rates from providers."""
    print_section("Test 4: POST /fx/sync/bulk")

    async with httpx.AsyncClient() as client:
        today = date.today()
        yesterday = today - timedelta(days=1)

        # Sync rates using query parameters
        params = {
            "start": yesterday.isoformat(),
            "end": yesterday.isoformat(),
            "currencies": "EUR,GBP",
            "provider": "ECB"
            }

        response = await client.post(
            f"{API_BASE}/fx/sync/bulk",
            params=params,
            timeout=TIMEOUT
            )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        sync_response = FXSyncResponse(**response.json())

        assert sync_response.synced >= 0, "Synced count should be non-negative"
        assert sync_response.date_range[0] == yesterday, "Start date should match"
        assert sync_response.date_range[1] == yesterday, "End date should match"

        print_success(f"✓ Sync completed: {sync_response.synced} rates synced")
        print_info(f"  Currencies: {', '.join(sync_response.currencies)}")


@pytest.mark.asyncio
async def test_convert_currency(test_server):
    """Test 5: POST /fx/convert/bulk - Currency conversion."""
    print_section("Test 5: POST /fx/convert/bulk")

    async with httpx.AsyncClient() as client:
        today = date.today()

        # First, ensure we have a rate (sync or manual)
        # Try to sync first
        sync_params = {
            "start": (today - timedelta(days=7)).isoformat(),
            "end": today.isoformat(),
            "currencies": "EUR,GBP",
            "provider": "ECB"
            }
        await client.post(
            f"{API_BASE}/fx/sync/bulk",
            params=sync_params,
            timeout=TIMEOUT
            )

        # Now convert (use Pydantic models)
        request = FXConvertRequest(
            conversions=[
                FXConversionRequest(
                    amount=Decimal("100"),
                    **{"from": "USD", "to": "EUR"},  # Use dict unpacking for aliased fields test
                    start_date=today - timedelta(days=1)
                    )
                ]
            )

        response = await client.post(
            f"{API_BASE}/fx/convert/bulk",
            json=request.model_dump(mode="json"),
            timeout=TIMEOUT
            )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        convert_response = FXConvertResponse(**response.json())

        if len(convert_response.results) > 0:
            result = convert_response.results[0]
            assert result.amount == Decimal("100"), "Original amount should be 100"
            assert result.from_currency == "USD", "From currency should be USD"
            assert result.to_currency == "EUR", "To currency should be EUR"
            assert result.converted_amount > 0, "Converted amount should be positive"
            print_success(f"✓ Converted 100 USD to {result.converted_amount} EUR")
        else:
            print_info("ℹ️  No conversion result (rate may not be available)")


@pytest.mark.asyncio
async def test_convert_missing_rate(test_server):
    """Test 6: POST /fx/convert/bulk - Conversion with missing rate."""
    print_section("Test 6: POST /fx/convert/bulk - Missing Rate")

    async with httpx.AsyncClient() as client:
        # Use a fake currency pair that definitely doesn't exist
        request = FXConvertRequest(
            conversions=[
                FXConversionRequest(
                    amount=Decimal("100"),
                    **{"from": "XXX", "to": "YYY"},  # Invalid currencies
                    start_date=date.today()
                    )
                ]
            )

        response = await client.post(
            f"{API_BASE}/fx/convert/bulk",
            json=request.model_dump(mode="json"),
            timeout=TIMEOUT
            )

        # Should either return 200 with errors or 4xx
        if response.status_code == 200:
            convert_response = FXConvertResponse(**response.json())
            assert len(convert_response.errors) > 0 or len(convert_response.results) == 0, \
                "Should have errors or no results for invalid currencies"
            print_success("✓ Missing rate handled gracefully (errors in response)")
        else:
            assert response.status_code in [400, 404, 422], \
                f"Expected 400/404/422 for invalid currencies, got {response.status_code}"
            print_success(f"✓ Missing rate rejected with {response.status_code}")


@pytest.mark.asyncio
async def test_manual_rate_upsert(test_server):
    """Test 7: POST /fx/rate-set/bulk - Manual rate upsert."""
    print_section("Test 7: POST /fx/rate-set/bulk - Manual Upsert")

    async with httpx.AsyncClient() as client:
        today = date.today()

        # Upsert a test rate (use Pydantic model)
        request = FXBulkUpsertRequest(
            rates=[
                FXUpsertItem(
                    **{"date": today},  # Use dict unpacking for aliased field
                    base="GBP",
                    quote="USD",
                    rate=Decimal("1.25"),
                    source="MANUAL"
                    )
                ]
            )

        response = await client.post(
            f"{API_BASE}/fx/rate-set/bulk",
            json=request.model_dump(mode="json"),
            timeout=TIMEOUT
            )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

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
    """Test 8: POST /fx/convert/bulk - Bulk conversions."""
    print_section("Test 8: POST /fx/convert/bulk - Bulk")

    async with httpx.AsyncClient() as client:
        today = date.today()

        # Setup: Ensure we have some rates
        upsert_request = FXBulkUpsertRequest(
            rates=[
                FXUpsertItem(**{"date": today}, base="USD", quote="EUR", rate=Decimal("0.85"), source="MANUAL"),
                FXUpsertItem(**{"date": today}, base="GBP", quote="USD", rate=Decimal("1.25"), source="MANUAL"),
                ]
            )
        await client.post(
            f"{API_BASE}/fx/rate-set/bulk",
            json=upsert_request.model_dump(mode="json"),
            timeout=TIMEOUT
            )

        # Bulk convert
        request = FXConvertRequest(
            conversions=[
                FXConversionRequest(amount=Decimal("100"), **{"from": "USD", "to": "EUR"}, start_date=today),
                FXConversionRequest(amount=Decimal("200"), **{"from": "GBP", "to": "USD"}, start_date=today),
                ]
            )

        response = await client.post(
            f"{API_BASE}/fx/convert/bulk",
            json=request.model_dump(mode="json"),
            timeout=TIMEOUT
            )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        convert_response = FXConvertResponse(**response.json())
        assert len(convert_response.results) == 2, "Should have 2 results"

        print_success(f"✓ Bulk conversion completed: {len(convert_response.results)} results")


@pytest.mark.asyncio
async def test_bulk_rate_upserts(test_server):
    """Test 9: POST /fx/rate-set/bulk - Bulk rate upserts."""
    print_section("Test 9: POST /fx/rate-set/bulk - Bulk Upserts")

    async with httpx.AsyncClient() as client:
        today = date.today()

        # Bulk upsert
        request = FXBulkUpsertRequest(
            rates=[
                FXUpsertItem(**{"date": today}, base="EUR", quote="USD", rate=Decimal("1.10"), source="MANUAL"),
                FXUpsertItem(**{"date": today}, base="JPY", quote="USD", rate=Decimal("0.0067"), source="MANUAL"),
                FXUpsertItem(**{"date": today}, base="CHF", quote="USD", rate=Decimal("1.12"), source="MANUAL"),
                ]
            )

        response = await client.post(
            f"{API_BASE}/fx/rate-set/bulk",
            json=request.model_dump(mode="json"),
            timeout=TIMEOUT
            )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        upsert_response = FXBulkUpsertResponse(**response.json())
        assert upsert_response.success_count == 3, f"Expected 3 successes, got {upsert_response.success_count}"
        assert len(upsert_response.results) == 3, "Should have 3 results"

        print_success(f"✓ Bulk upsert: {upsert_response.success_count} rates inserted/updated")


@pytest.mark.asyncio
async def test_delete_rates(test_server):
    """Test 10: DELETE /fx/rate-set/bulk - Rate deletion."""
    print_section("Test 10: DELETE /fx/rate-set/bulk")

    async with httpx.AsyncClient() as client:
        today = date.today()
        yesterday = today - timedelta(days=1)

        # Setup: Insert some test rates
        upsert_request = FXBulkUpsertRequest(
            rates=[
                FXUpsertItem(**{"date": yesterday}, base="AUD", quote="USD", rate=Decimal("0.65"), source="MANUAL"),
                FXUpsertItem(**{"date": today}, base="AUD", quote="USD", rate=Decimal("0.66"), source="MANUAL"),
                ]
            )
        await client.post(
            f"{API_BASE}/fx/rate-set/bulk",
            json=upsert_request.model_dump(mode="json"),
            timeout=TIMEOUT
            )

        # Delete rate range
        request = FXBulkDeleteRequest(
            deletions=[
                FXDeleteItem(
                    **{"from": "AUD", "to": "USD"},  # Use dict unpacking for aliased fields
                    start_date=yesterday,
                    end_date=today
                    )
                ]
            )

        response = await client.request(
            method="DELETE",
            url=f"{API_BASE}/fx/rate-set/bulk",
            content=request.model_dump_json(),
            headers={"Content-Type": "application/json"},
            timeout=TIMEOUT
            )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

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
                    "start_date": date.today().isoformat()
                    }
                ]
            }
        response = await client.post(
            f"{API_BASE}/fx/convert/bulk",
            json=request,
            timeout=TIMEOUT
            )
        assert response.status_code == 422, f"Expected 422 for invalid currency, got {response.status_code}"
        print_success("✓ Invalid currency rejected with 422")

        # 11b. Negative amount
        print_info("11b. Negative amount")
        request = {
            "conversions": [
                {
                    "amount": "-100",
                    "from": "USD",
                    "to": "EUR",
                    "start_date": date.today().isoformat()
                    }
                ]
            }
        response = await client.post(
            f"{API_BASE}/fx/convert/bulk",
            json=request,
            timeout=TIMEOUT
            )
        assert response.status_code == 422, f"Expected 422 for negative amount, got {response.status_code}"
        print_success("✓ Negative amount rejected with 422")

        # 11c. Missing required field
        print_info("11c. Missing required field")
        request = {
            "conversions": [
                {
                    "amount": "100",
                    "from": "USD",
                    # Missing "to" field
                    "start_date": date.today().isoformat()
                    }
                ]
            }
        response = await client.post(
            f"{API_BASE}/fx/convert/bulk",
            json=request,
            timeout=TIMEOUT
            )
        assert response.status_code == 422, f"Expected 422 for missing field, got {response.status_code}"
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
                    "source": "MANUAL"
                    }
                ]
            }
        response = await client.post(
            f"{API_BASE}/fx/rate-set/bulk",
            json=request,
            timeout=TIMEOUT
            )
        assert response.status_code == 422, f"Expected 422 for zero rate, got {response.status_code}"
        print_success("✓ Zero rate rejected with 422")

        # 11e. Invalid date format
        print_info("11e. Invalid date format")
        request = {
            "conversions": [
                {
                    "amount": "100",
                    "from": "USD",
                    "to": "EUR",
                    "start_date": "invalid-date"
                    }
                ]
            }
        response = await client.post(
            f"{API_BASE}/fx/convert/bulk",
            json=request,
            timeout=TIMEOUT
            )
        assert response.status_code == 422, f"Expected 422 for invalid date, got {response.status_code}"
        print_success("✓ Invalid date rejected with 422")

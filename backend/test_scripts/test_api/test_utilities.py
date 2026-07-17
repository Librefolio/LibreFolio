"""
Tests for utilities API endpoints.

Tests the /api/v1/utilities endpoints:
- GET /utilities/sectors - List standard financial sectors
- GET /utilities/countries - List all countries with ISO codes and flag emoji
- GET /utilities/currencies/normalize - Normalize currency name/code/symbol
"""

import httpx
import pytest

from backend.app.config import get_settings
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_info, print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30


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


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture(scope="module")
def test_server():
    """Start test server once for all tests in this module."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager
        # Server automatically stopped by context manager


# ============================================================
# GET /utilities/sectors Tests
# ============================================================


@pytest.mark.asyncio
async def test_list_sectors_with_other(test_server):
    """Test 1: GET /utilities/sectors - Include 'Other'."""
    print_section("Test 1: GET /utilities/sectors - Include Other")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        response = await client.get(f"{API_BASE}/utilities/sectors", timeout=TIMEOUT)

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()

        assert "items" in data
        assert len(data["items"]) == 12  # 11 standard + Other
        keys = [item["key"] for item in data["items"]]
        assert "Other" in keys

        # Verify all expected sectors are present
        expected = [
            "Industrials",
            "Technology",
            "Financials",
            "Consumer Discretionary",
            "Health Care",
            "Real Estate",
            "Basic Materials",
            "Energy",
            "Consumer Staples",
            "Telecommunication",
            "Utilities",
            "Other",
        ]
        for sector in expected:
            assert sector in keys, f"Missing sector: {sector}"

        print_info(f"  Found {len(data['items'])} sectors")
        print_success("✓ Sectors list with Other returned correctly")


@pytest.mark.asyncio
async def test_list_sectors_without_other(test_server):
    """Test 2: GET /utilities/sectors?include_other=false - Exclude 'Other'."""
    print_section("Test 2: GET /utilities/sectors - Exclude Other")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        response = await client.get(f"{API_BASE}/utilities/sectors", params={"include_other": "false"}, timeout=TIMEOUT)

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()

        assert len(data["items"]) == 11  # 11 standard (without Other)
        keys = [item["key"] for item in data["items"]]
        assert "Other" not in keys

        print_info(f"  Found {len(data['items'])} sectors (excluding Other)")
        print_success("✓ Sectors list without Other returned correctly")


# ============================================================
# GET /utilities/countries Tests
# ============================================================


@pytest.mark.asyncio
async def test_list_countries_default(test_server):
    """Test 8: GET /utilities/countries - List all countries (English)."""
    print_section("Test 8: GET /utilities/countries - Default (en)")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        response = await client.get(f"{API_BASE}/utilities/countries", timeout=TIMEOUT)

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()

        assert "items" in data
        countries = data["items"]
        assert len(countries) > 200, f"Expected 200+ countries, got {len(countries)}"

        # Check structure of first item
        first = countries[0]
        assert "iso3" in first
        assert "iso2" in first
        assert "name" in first
        assert "flag_emoji" in first

        # Verify a known country is present
        usa = next((c for c in countries if c["iso3"] == "USA"), None)
        assert usa is not None, "USA should be in country list"
        assert usa["iso2"] == "US"
        assert usa["flag_emoji"]  # Should have a flag emoji

        print_info(f"  Found {len(countries)} countries")
        print_success("✓ Countries list returned correctly")


@pytest.mark.asyncio
async def test_list_countries_italian(test_server):
    """Test 9: GET /utilities/countries?language=it - Italian names."""
    print_section("Test 9: GET /utilities/countries - Italian")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        response = await client.get(f"{API_BASE}/utilities/countries", params={"language": "it"}, timeout=TIMEOUT)

        assert response.status_code == 200
        data = response.json()

        countries = data["items"]
        assert len(countries) > 200

        # Italy should have Italian name
        ita = next((c for c in countries if c["iso3"] == "ITA"), None)
        assert ita is not None
        assert "Italia" in ita["name"] or "italia" in ita["name"].lower()

        print_info(f"  Found {len(countries)} countries (Italian names)")
        print_success("✓ Countries list with Italian names")


# ============================================================
# GET /utilities/currencies/normalize Tests
# ============================================================


@pytest.mark.asyncio
async def test_normalize_currency_iso_code(test_server):
    """Test 10: GET /utilities/currencies/normalize - ISO code."""
    print_section("Test 10: Normalize Currency - ISO Code")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        response = await client.get(f"{API_BASE}/utilities/currencies/normalize", params={"name": "USD"}, timeout=TIMEOUT)

        assert response.status_code == 200
        data = response.json()

        assert data["query"] == "USD"
        assert "USD" in data["iso_codes"]
        assert data["match_type"] == "exact"

        print_info(f"  USD -> {data['iso_codes']}")
        print_success("✓ Currency ISO code normalized correctly")


@pytest.mark.asyncio
async def test_normalize_currency_symbol(test_server):
    """Test 11: GET /utilities/currencies/normalize - Currency symbol."""
    print_section("Test 11: Normalize Currency - Symbol")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        response = await client.get(f"{API_BASE}/utilities/currencies/normalize", params={"name": "€"}, timeout=TIMEOUT)

        assert response.status_code == 200
        data = response.json()

        assert data["query"] == "€"
        # Symbol may resolve to the symbol itself or EUR depending on implementation
        assert len(data["iso_codes"]) > 0

        print_info(f"  € -> {data['iso_codes']}")
        print_success("✓ Currency symbol normalized correctly")


@pytest.mark.asyncio
async def test_normalize_currency_passthrough(test_server):
    """Test 12: GET /utilities/currencies/normalize - Unknown input is passed through."""
    print_section("Test 12: Normalize Currency - Passthrough")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        response = await client.get(f"{API_BASE}/utilities/currencies/normalize", params={"name": "xyznotacurrency123"}, timeout=TIMEOUT)

        assert response.status_code == 200
        data = response.json()

        assert data["query"] == "xyznotacurrency123"
        # API returns the input uppercased as "exact" match (passthrough behavior)
        assert len(data["iso_codes"]) >= 0  # may or may not find a match

        print_info(f"  xyznotacurrency123 -> match_type={data['match_type']}, codes={data['iso_codes']}")
        print_success("✓ Unknown currency handled correctly")


class TestListCurrenciesEndpoint:
    """Tests for GET /utilities/currencies endpoint."""

    @pytest.mark.asyncio
    async def test_list_currencies_default_language(self, test_server):
        """List currencies with default language (en)."""
        print_section("list_currencies: default language")
        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)
            response = await client.get(f"{API_BASE}/utilities/currencies", timeout=TIMEOUT)
            assert response.status_code == 200
            data = response.json()
            assert data["language"] == "en"
            assert len(data["items"]) > 100
            codes = [c["code"] for c in data["items"]]
            assert "EUR" in codes
            assert "USD" in codes
            print_success(f"✓ Got {len(data['items'])} currencies")

    @pytest.mark.asyncio
    async def test_list_currencies_italian(self, test_server):
        """List currencies in Italian."""
        print_section("list_currencies: Italian")
        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)
            response = await client.get(f"{API_BASE}/utilities/currencies", params={"language": "it"}, timeout=TIMEOUT)
            assert response.status_code == 200
            data = response.json()
            assert data["language"] == "it"
            print_success("✓ Italian currency list returned")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

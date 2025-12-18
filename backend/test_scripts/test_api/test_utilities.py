"""
Tests for utilities API endpoints.

Tests the /api/v1/utilities endpoints:
- GET /utilities/sectors - List standard financial sectors
- GET /utilities/countries/normalize - Normalize country codes
"""
import httpx
import pytest

from backend.app.config import get_settings
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_info, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30


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
        response = await client.get(f"{API_BASE}/utilities/sectors", timeout=TIMEOUT)

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()

        assert "sectors" in data
        assert "count" in data
        assert data["count"] == 12  # 11 standard + Other
        assert "Other" in data["sectors"]

        # Verify all expected sectors are present
        expected = [
            "Industrials", "Technology", "Financials", "Consumer Discretionary",
            "Health Care", "Real Estate", "Basic Materials", "Energy",
            "Consumer Staples", "Telecommunication", "Utilities", "Other"
            ]
        for sector in expected:
            assert sector in data["sectors"], f"Missing sector: {sector}"

        print_info(f"  Found {data['count']} sectors")
        print_success("✓ Sectors list with Other returned correctly")


@pytest.mark.asyncio
async def test_list_sectors_without_other(test_server):
    """Test 2: GET /utilities/sectors?include_other=false - Exclude 'Other'."""
    print_section("Test 2: GET /utilities/sectors - Exclude Other")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE}/utilities/sectors",
            params={"include_other": "false"},
            timeout=TIMEOUT
            )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()

        assert data["count"] == 11  # 11 standard (without Other)
        assert "Other" not in data["sectors"]

        print_info(f"  Found {data['count']} sectors (excluding Other)")
        print_success("✓ Sectors list without Other returned correctly")


# ============================================================
# GET /utilities/countries/normalize Tests
# ============================================================

@pytest.mark.asyncio
async def test_normalize_country_iso3(test_server):
    """Test 3: GET /utilities/countries/normalize - ISO-3 code."""
    print_section("Test 3: Normalize Country - ISO-3 Code")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE}/utilities/countries/normalize",
            params={"name": "USA"},
            timeout=TIMEOUT
            )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()

        assert data["query"] == "USA"
        assert data["match_type"] == "exact"
        assert "USA" in data["iso3_codes"]
        assert data["error"] is None

        print_info(f"  USA -> {data['iso3_codes']}")
        print_success("✓ ISO-3 code normalized correctly")


@pytest.mark.asyncio
async def test_normalize_country_iso2(test_server):
    """Test 4: GET /utilities/countries/normalize - ISO-2 code."""
    print_section("Test 4: Normalize Country - ISO-2 Code")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE}/utilities/countries/normalize",
            params={"name": "IT"},
            timeout=TIMEOUT
            )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()

        assert data["query"] == "IT"
        assert data["match_type"] == "exact"
        assert "ITA" in data["iso3_codes"]

        print_info(f"  IT -> {data['iso3_codes']}")
        print_success("✓ ISO-2 code converted to ISO-3")


@pytest.mark.asyncio
async def test_normalize_country_name(test_server):
    """Test 5: GET /utilities/countries/normalize - Country name."""
    print_section("Test 5: Normalize Country - Country Name")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE}/utilities/countries/normalize",
            params={"name": "Germany"},
            timeout=TIMEOUT
            )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()

        assert data["query"] == "Germany"
        assert data["match_type"] == "exact"
        assert "DEU" in data["iso3_codes"]

        print_info(f"  Germany -> {data['iso3_codes']}")
        print_success("✓ Country name normalized to ISO-3")


@pytest.mark.asyncio
async def test_normalize_country_invalid(test_server):
    """Test 6: GET /utilities/countries/normalize - Invalid country."""
    print_section("Test 6: Normalize Country - Invalid Name")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE}/utilities/countries/normalize",
            params={"name": "InvalidCountryXYZ"},
            timeout=TIMEOUT
            )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()

        assert data["query"] == "InvalidCountryXYZ"
        assert data["match_type"] == "not_found"
        assert len(data["iso3_codes"]) == 0
        assert data["error"] is not None

        print_info(f"  InvalidCountryXYZ -> not_found (error: {data['error'][:50]}...)")
        print_success("✓ Invalid country handled correctly")


@pytest.mark.asyncio
async def test_normalize_country_case_insensitive(test_server):
    """Test 7: GET /utilities/countries/normalize - Case insensitive."""
    print_section("Test 7: Normalize Country - Case Insensitive")

    async with httpx.AsyncClient() as client:
        # Test various case combinations
        test_cases = [
            ("usa", "USA"),
            ("italy", "ITA"),
            ("FRANCE", "FRA"),
            ("jApAn", "JPN"),
            ]

        for name, expected_iso3 in test_cases:
            response = await client.get(
                f"{API_BASE}/utilities/countries/normalize",
                params={"name": name},
                timeout=TIMEOUT
                )

            assert response.status_code == 200
            data = response.json()
            assert expected_iso3 in data["iso3_codes"], f"{name} should normalize to {expected_iso3}"
            print_info(f"  {name} -> {data['iso3_codes']}")

        print_success("✓ Case-insensitive normalization works")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

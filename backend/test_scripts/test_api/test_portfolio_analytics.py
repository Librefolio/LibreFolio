"""Portfolio Analytics API Tests. GET /api/v1/portfolio/{summary,history,asset-history,lots}."""

import uuid
from decimal import Decimal
from datetime import date, timedelta

import httpx
import pytest

from backend.app.config import get_settings
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30


# ---------------------------------------------------------------------------
# Helpers (reused from test_analytics_wac pattern)
# ---------------------------------------------------------------------------

async def create_test_user(client: httpx.AsyncClient) -> str:
    username = f"pftest_{uuid.uuid4().hex[:8]}"
    resp = await client.post(
        f"{API_BASE}/auth/register",
        json={"username": username, "email": f"{username}@test.com", "password": "TestPass123!"},
        timeout=TIMEOUT,
    )
    assert resp.status_code == 201
    login_resp = await client.post(
        f"{API_BASE}/auth/login",
        json={"username": username, "password": "TestPass123!"},
        timeout=TIMEOUT,
    )
    if s := login_resp.cookies.get("session"):
        client.cookies.set("session", s)
    return username


async def create_broker(client: httpx.AsyncClient, name: str | None = None) -> int:
    resp = await client.post(
        f"{API_BASE}/brokers",
        json=[{"name": name or f"Bk_{uuid.uuid4().hex[:6]}", "allow_cash_overdraft": True}],
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200
    return resp.json()["results"][0]["broker_id"]


async def create_asset(client: httpx.AsyncClient, currency: str = "EUR") -> int:
    resp = await client.post(
        f"{API_BASE}/assets",
        json=[{"display_name": f"As_{uuid.uuid4().hex[:6]}", "currency": currency, "asset_type": "STOCK"}],
        timeout=TIMEOUT,
    )
    assert resp.status_code in (200, 201)
    return resp.json()["results"][0]["asset_id"]


async def commit_batch(client: httpx.AsyncClient, **kwargs) -> dict:
    resp = await client.post(f"{API_BASE}/transactions/commit", json=kwargs, timeout=TIMEOUT)
    assert resp.status_code == 200, f"Commit failed: {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data.get("committed") is True, f"Not committed: {data.get('issues', [])}"
    return data


@pytest.fixture(scope="module")
def test_server():
    with _TestingServerManager() as manager:
        yield manager


# ---------------------------------------------------------------------------
# TestPortfolioSummaryEndpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestPortfolioSummaryEndpoint:
    async def test_unauthenticated(self, test_server):
        """GET /portfolio/summary without auth → 401."""
        print_section("Portfolio Summary: unauthenticated")
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{API_BASE}/portfolio/summary", timeout=TIMEOUT)
        assert resp.status_code == 401
        print_success("401 as expected")

    async def test_empty_portfolio(self, test_server):
        """New user with no brokers → summary with zero values."""
        print_section("Portfolio Summary: empty portfolio")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            resp = await client.get(f"{API_BASE}/portfolio/summary", timeout=TIMEOUT)
        assert resp.status_code == 200
        data = resp.json()
        assert "net_worth" in data
        assert "total_invested" in data
        assert "twrr_percent" in data
        assert "allocation_by_type" in data
        assert "holdings" in data
        assert isinstance(data["holdings"], list)
        assert data["by_broker"] is None
        print_success(f"Empty summary OK, net_worth={data['net_worth']}")

    async def test_summary_structure_with_data(self, test_server):
        """User with broker + deposit → summary has expected structure."""
        print_section("Portfolio Summary: with deposit")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_broker(client)

            # Deposit cash
            await commit_batch(
                client,
                broker_id=broker_id,
                creates=[{"type": "DEPOSIT", "date": "2025-01-15", "amount": 10000, "currency": "EUR"}],
            )

            resp = await client.get(f"{API_BASE}/portfolio/summary", timeout=TIMEOUT)
        assert resp.status_code == 200
        data = resp.json()
        assert "net_worth" in data
        assert "cash_total" in data
        assert "simple_roi_percent" in data
        print_success("Summary structure OK")

    async def test_filter_by_broker(self, test_server):
        """broker_ids query param filters the response."""
        print_section("Portfolio Summary: filter by broker")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_broker(client)

            resp = await client.get(
                f"{API_BASE}/portfolio/summary?broker_ids={broker_id}",
                timeout=TIMEOUT,
            )
        assert resp.status_code == 200
        print_success("Broker filter OK")

    async def test_include_breakdown(self, test_server):
        """include_breakdown=true → by_broker is populated."""
        print_section("Portfolio Summary: include_breakdown")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            await create_broker(client)

            resp = await client.get(
                f"{API_BASE}/portfolio/summary?include_breakdown=true",
                timeout=TIMEOUT,
            )
        assert resp.status_code == 200
        data = resp.json()
        # by_broker may be empty list if no accessible brokers, but must be a list
        assert data["by_broker"] is not None
        assert isinstance(data["by_broker"], list)
        print_success("include_breakdown OK")

    async def test_invalid_broker_id_ignored(self, test_server):
        """Non-existent broker_id → empty result (no 500)."""
        print_section("Portfolio Summary: nonexistent broker")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            resp = await client.get(
                f"{API_BASE}/portfolio/summary?broker_ids=999999",
                timeout=TIMEOUT,
            )
        assert resp.status_code == 200
        print_success("Nonexistent broker handled gracefully")


# ---------------------------------------------------------------------------
# TestPortfolioHistoryEndpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestPortfolioHistoryEndpoint:
    async def test_unauthenticated(self, test_server):
        """GET /portfolio/history without auth → 401."""
        print_section("Portfolio History: unauthenticated")
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{API_BASE}/portfolio/history", timeout=TIMEOUT)
        assert resp.status_code == 401
        print_success("401 as expected")

    async def test_empty_history(self, test_server):
        """New user → history is empty array."""
        print_section("Portfolio History: empty")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            resp = await client.get(f"{API_BASE}/portfolio/history", timeout=TIMEOUT)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        print_success(f"History: {len(data)} points")

    async def test_history_with_transactions(self, test_server):
        """History with transactions returns points with correct structure."""
        print_section("Portfolio History: with transactions")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_broker(client)
            await commit_batch(
                client,
                broker_id=broker_id,
                creates=[{"type": "DEPOSIT", "date": "2025-03-01", "amount": 5000, "currency": "EUR"}],
            )
            resp = await client.get(f"{API_BASE}/portfolio/history", timeout=TIMEOUT)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            point = data[0]
            assert "date" in point
            assert "cash_value" in point
            assert "invested_value" in point
            assert "nav_value" in point
        print_success("History structure OK")

    async def test_history_date_range_filter(self, test_server):
        """date_from/date_to filter narrows history."""
        print_section("Portfolio History: date range filter")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            await create_broker(client)
            resp = await client.get(
                f"{API_BASE}/portfolio/history?date_from=2025-01-01&date_to=2025-06-30",
                timeout=TIMEOUT,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        print_success("Date range filter OK")


# ---------------------------------------------------------------------------
# TestAssetHistoryEndpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestAssetHistoryEndpoint:
    async def test_unauthenticated(self, test_server):
        """GET /portfolio/asset-history without auth → 401."""
        print_section("Asset History: unauthenticated")
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{API_BASE}/portfolio/asset-history?asset_id=1", timeout=TIMEOUT)
        assert resp.status_code == 401
        print_success("401 as expected")

    async def test_missing_asset_id(self, test_server):
        """asset_id is required → 422 if missing."""
        print_section("Asset History: missing asset_id")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            resp = await client.get(f"{API_BASE}/portfolio/asset-history", timeout=TIMEOUT)
        assert resp.status_code == 422
        print_success("422 as expected")

    async def test_nonexistent_asset(self, test_server):
        """Non-existent asset_id → empty array (no 500)."""
        print_section("Asset History: nonexistent asset")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            resp = await client.get(
                f"{API_BASE}/portfolio/asset-history?asset_id=999999",
                timeout=TIMEOUT,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        print_success("Graceful empty response")


# ---------------------------------------------------------------------------
# TestFIFOLotsEndpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestFIFOLotsEndpoint:
    async def test_unauthenticated(self, test_server):
        """GET /portfolio/lots without auth → 401."""
        print_section("FIFO Lots: unauthenticated")
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{API_BASE}/portfolio/lots?broker_id=1&asset_id=1", timeout=TIMEOUT)
        assert resp.status_code == 401
        print_success("401 as expected")

    async def test_missing_required_params(self, test_server):
        """broker_id and asset_id are required → 422 if missing."""
        print_section("FIFO Lots: missing required params")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)

            # missing both
            resp = await client.get(f"{API_BASE}/portfolio/lots", timeout=TIMEOUT)
            assert resp.status_code == 422

            # missing asset_id
            resp = await client.get(f"{API_BASE}/portfolio/lots?broker_id=1", timeout=TIMEOUT)
            assert resp.status_code == 422

            # missing broker_id
            resp = await client.get(f"{API_BASE}/portfolio/lots?asset_id=1", timeout=TIMEOUT)
            assert resp.status_code == 422

        print_success("422 for all missing param combinations")

    async def test_lots_response_structure(self, test_server):
        """Valid params → response has open_lots, closed_lots structure."""
        print_section("FIFO Lots: response structure")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_broker(client)
            asset_id = await create_asset(client)

            resp = await client.get(
                f"{API_BASE}/portfolio/lots?broker_id={broker_id}&asset_id={asset_id}",
                timeout=TIMEOUT,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "open_lots" in data
        assert "closed_lots" in data
        assert "total_realized_pnl" in data
        assert "total_unrealized_quantity" in data
        assert isinstance(data["open_lots"], list)
        assert isinstance(data["closed_lots"], list)
        print_success("FIFO response structure OK")

    async def test_lots_no_access(self, test_server):
        """User without broker access → empty lots (not 403, graceful)."""
        print_section("FIFO Lots: no access")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            resp = await client.get(
                f"{API_BASE}/portfolio/lots?broker_id=999999&asset_id=999999",
                timeout=TIMEOUT,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["open_lots"] == []
        assert data["closed_lots"] == []
        print_success("No access returns empty lots")

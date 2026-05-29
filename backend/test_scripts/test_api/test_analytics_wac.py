"""Analytics WAC API Tests (A1-A8). POST /api/v1/analytics/wac."""

import uuid
from decimal import Decimal

import httpx
import pytest

from backend.app.config import get_settings
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30


async def create_test_user(client: httpx.AsyncClient) -> str:
    username = f"anwac_{uuid.uuid4().hex[:8]}"
    resp = await client.post(f"{API_BASE}/auth/register", json={"username": username, "email": f"{username}@test.com", "password": "TestPass123!"}, timeout=TIMEOUT)
    assert resp.status_code == 201
    login_resp = await client.post(f"{API_BASE}/auth/login", json={"username": username, "password": "TestPass123!"}, timeout=TIMEOUT)
    if s := login_resp.cookies.get("session"):
        client.cookies.set("session", s)
    return username


async def create_broker(client: httpx.AsyncClient) -> int:
    resp = await client.post(f"{API_BASE}/brokers", json=[{"name": f"AnBk_{uuid.uuid4().hex[:6]}", "allow_cash_overdraft": True}], timeout=TIMEOUT)
    assert resp.status_code == 200
    return resp.json()["results"][0]["broker_id"]


async def create_asset(client: httpx.AsyncClient, currency: str = "EUR") -> int:
    resp = await client.post(f"{API_BASE}/assets", json=[{"display_name": f"AnAs_{uuid.uuid4().hex[:6]}", "currency": currency, "asset_type": "STOCK"}], timeout=TIMEOUT)
    assert resp.status_code in (200, 201)
    return resp.json()["results"][0]["asset_id"]


async def setup_env(client: httpx.AsyncClient, *, currency: str = "EUR") -> tuple[int, int]:
    await create_test_user(client)
    return await create_broker(client), await create_asset(client, currency=currency)


async def commit_batch(client: httpx.AsyncClient, **kwargs) -> dict:
    resp = await client.post(f"{API_BASE}/transactions/commit", json=kwargs, timeout=TIMEOUT)
    assert resp.status_code == 200, f"Commit HTTP failed: {resp.status_code}"
    data = resp.json()
    assert data.get("committed") is True, f"Not committed: {data.get('issues', [])}"
    return data


async def analytics_wac(client: httpx.AsyncClient, queries: list[dict]) -> dict:
    resp = await client.post(f"{API_BASE}/analytics/wac", json={"queries": queries}, timeout=TIMEOUT)
    assert resp.status_code == 200, f"Analytics WAC failed: {resp.status_code}: {resp.text}"
    return resp.json()


@pytest.fixture(scope="module")
def test_server():
    with _TestingServerManager() as mgr:
        if not mgr.start_server():
            pytest.fail("Failed to start test server")
        yield mgr


@pytest.mark.asyncio
class TestAnalyticsWAC:
    @pytest.fixture(autouse=True)
    def _server(self, test_server):
        pass

    async def test_a1_empty_pool(self):
        """A1: No transactions -> empty series."""
        print_section("A1: Empty pool")
        async with httpx.AsyncClient() as client:
            broker_id, asset_id = await setup_env(client)
            result = await analytics_wac(client, [{"broker_id": broker_id, "asset_id": asset_id}])
            assert result["results"][0]["series"] == []
            print_success("OK empty series")

    async def test_a2_single_buy(self):
        """A2: Single BUY -> 1 point, WAC = unit price."""
        print_section("A2: Single BUY")
        async with httpx.AsyncClient() as client:
            broker_id, asset_id = await setup_env(client)
            await commit_batch(client, creates=[
                {"broker_id": broker_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "10000"}},
                {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-15", "quantity": "10", "cash": {"code": "EUR", "amount": "-500"}},
            ])
            result = await analytics_wac(client, [{"broker_id": broker_id, "asset_id": asset_id}])
            s = result["results"][0]["series"]
            assert len(s) == 1
            assert s[0]["date"] == "2026-01-15"
            assert Decimal(s[0]["wac"]) == Decimal("50")
            assert Decimal(s[0]["pool_qty"]) == Decimal("10")
            assert s[0]["effect"] == "add"
            print_success("OK WAC=50 qty=10")

    async def test_a3_evolving_wac(self):
        """A3: Multiple BUYs -> WAC evolves."""
        print_section("A3: Evolving WAC")
        async with httpx.AsyncClient() as client:
            broker_id, asset_id = await setup_env(client)
            await commit_batch(client, creates=[
                {"broker_id": broker_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "50000"}},
                {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-02-01", "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
                {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-02-15", "quantity": "5", "cash": {"code": "EUR", "amount": "-800"}},
            ])
            result = await analytics_wac(client, [{"broker_id": broker_id, "asset_id": asset_id}])
            s = result["results"][0]["series"]
            assert len(s) == 2
            assert Decimal(s[0]["wac"]) == Decimal("100")
            assert Decimal(s[1]["wac"]) == Decimal("120")
            assert Decimal(s[1]["pool_qty"]) == Decimal("15")
            print_success("OK WAC 100->120")

    async def test_a4_date_range_filter(self):
        """A4: date_range filters series."""
        print_section("A4: date_range filter")
        async with httpx.AsyncClient() as client:
            broker_id, asset_id = await setup_env(client)
            await commit_batch(client, creates=[
                {"broker_id": broker_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "50000"}},
                {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-10", "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
                {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-02-10", "quantity": "5", "cash": {"code": "EUR", "amount": "-600"}},
                {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-03-10", "quantity": "5", "cash": {"code": "EUR", "amount": "-700"}},
            ])
            result = await analytics_wac(client, [{"broker_id": broker_id, "asset_id": asset_id, "date_range": {"start": "2026-02-01", "end": "2026-03-31"}}])
            s = result["results"][0]["series"]
            assert len(s) == 2
            assert s[0]["date"] == "2026-02-10"
            assert s[1]["date"] == "2026-03-10"
            print_success("OK filtered Feb-Mar")

    async def test_a5_sell_reduces_pool(self):
        """A5: SELL reduces pool, WAC unchanged."""
        print_section("A5: SELL reduces pool")
        async with httpx.AsyncClient() as client:
            broker_id, asset_id = await setup_env(client)
            await commit_batch(client, creates=[
                {"broker_id": broker_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "50000"}},
                {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-10", "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
                {"broker_id": broker_id, "asset_id": asset_id, "type": "SELL", "date": "2026-01-20", "quantity": "-3", "cash": {"code": "EUR", "amount": "450"}},
            ])
            result = await analytics_wac(client, [{"broker_id": broker_id, "asset_id": asset_id}])
            s = result["results"][0]["series"]
            assert len(s) == 2
            assert Decimal(s[1]["wac"]) == Decimal("100")
            assert Decimal(s[1]["pool_qty"]) == Decimal("7")
            assert s[1]["effect"] == "reduce"
            print_success("OK SELL pool 10->7")

    async def test_a6_nonexistent_asset(self):
        """A6: Non-existent asset -> empty series."""
        print_section("A6: Non-existent asset")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            result = await analytics_wac(client, [{"broker_id": 99999, "asset_id": 99999}])
            assert result["results"][0]["series"] == []
            print_success("OK graceful empty")

    async def test_a7_open_range_end_only(self):
        """A7: OpenDateRangeModel end only -> history up to end."""
        print_section("A7: Open range (end only)")
        async with httpx.AsyncClient() as client:
            broker_id, asset_id = await setup_env(client)
            await commit_batch(client, creates=[
                {"broker_id": broker_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "50000"}},
                {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-10", "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
                {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-03-10", "quantity": "5", "cash": {"code": "EUR", "amount": "-600"}},
            ])
            result = await analytics_wac(client, [{"broker_id": broker_id, "asset_id": asset_id, "date_range": {"end": "2026-02-01"}}])
            s = result["results"][0]["series"]
            assert len(s) == 1
            assert s[0]["date"] == "2026-01-10"
            print_success("OK end=Feb -> only Jan")

    async def test_a8_multiple_queries(self):
        """A8: Multiple queries -> results in order."""
        print_section("A8: Multiple queries")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_broker(client)
            asset1 = await create_asset(client, currency="EUR")
            asset2 = await create_asset(client, currency="USD")
            await commit_batch(client, creates=[
                {"broker_id": broker_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "50000"}},
                {"broker_id": broker_id, "asset_id": asset1, "type": "BUY", "date": "2026-01-10", "quantity": "5", "cash": {"code": "EUR", "amount": "-500"}},
            ])
            result = await analytics_wac(client, [
                {"broker_id": broker_id, "asset_id": asset1},
                {"broker_id": broker_id, "asset_id": asset2},
            ])
            assert len(result["results"]) == 2
            assert len(result["results"][0]["series"]) == 1
            assert len(result["results"][1]["series"]) == 0
            print_success("OK batch query")

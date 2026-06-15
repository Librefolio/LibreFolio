"""Portfolio API Tests. POST /api/v1/portfolio/{summary,history} + GET asset-history/lots."""

import uuid

import httpx
import pytest

from backend.app.config import get_settings
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30


# ---------------------------------------------------------------------------
# Helpers
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


async def create_asset(client: httpx.AsyncClient, currency: str = "EUR", quote_base_quantity: int | None = None) -> int:
    resp = await client.post(
        f"{API_BASE}/assets",
        json=[
            {
                "display_name": f"As_{uuid.uuid4().hex[:6]}",
                "currency": currency,
                "asset_type": "STOCK",
                **({"quote_base_quantity": quote_base_quantity} if quote_base_quantity is not None else {}),
            }
        ],
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


async def post_portfolio_summary(client: httpx.AsyncClient, body: dict | None = None) -> httpx.Response:
    return await client.post(f"{API_BASE}/portfolio/summary", json=body or {}, timeout=TIMEOUT)


async def post_portfolio_history(client: httpx.AsyncClient, body: dict | None = None) -> httpx.Response:
    return await client.post(f"{API_BASE}/portfolio/history", json=body or {}, timeout=TIMEOUT)


@pytest.fixture(scope="module")
def test_server():
    with _TestingServerManager() as manager:
        if not manager.start_server():
            pytest.fail("Failed to start test server")
        yield manager


# ---------------------------------------------------------------------------
# TestPortfolioSummaryEndpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestPortfolioSummaryEndpoint:
    async def test_unauthenticated(self, test_server):
        """POST /portfolio/summary without auth -> 401."""
        print_section("Portfolio Summary: unauthenticated")
        async with httpx.AsyncClient() as client:
            resp = await post_portfolio_summary(client)
        assert resp.status_code == 401
        print_success("401 as expected")

    async def test_empty_portfolio(self, test_server):
        """New user with no brokers → summary with zero values."""
        print_section("Portfolio Summary: empty portfolio")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            resp = await post_portfolio_summary(client)
        assert resp.status_code == 200
        data = resp.json()
        assert "net_worth" in data
        assert "total_invested" in data
        assert "twrr_percent" in data
        assert "allocation_by_type" in data
        assert "holdings" in data
        assert isinstance(data["holdings"], list)
        assert data["by_broker"] is None
        print_success(f"Empty summary OK, net_worth={data['net_worth']['amount']}")

    async def test_summary_structure_with_data(self, test_server):
        """User with broker + deposit → summary has expected structure."""
        print_section("Portfolio Summary: with deposit")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_broker(client)

            # Deposit cash
            await commit_batch(
                client,
                creates=[
                    {
                        "broker_id": broker_id,
                        "type": "DEPOSIT",
                        "date": "2025-01-15",
                        "quantity": "0",
                        "cash": {"code": "EUR", "amount": "10000"},
                    }
                ],
            )

            resp = await post_portfolio_summary(client)
        assert resp.status_code == 200
        data = resp.json()
        assert "net_worth" in data
        assert "cash_total" in data
        assert "simple_roi_percent" in data
        assert "missing_fx_pairs" in data
        assert "missing_prices_assets" in data
        print_success("Summary structure OK")

    async def test_summary_cash_uses_full_signed_ledger(self, test_server):
        """Cash total uses all signed transaction amounts and reports missing prices."""
        print_section("Portfolio Summary: signed cash ledger")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_broker(client)
            asset_id = await create_asset(client)

            await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "type": "DEPOSIT", "date": "2025-01-15", "quantity": "0", "cash": {"code": "EUR", "amount": "1000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2025-01-16", "quantity": "4", "cash": {"code": "EUR", "amount": "-400"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "DIVIDEND", "date": "2025-01-17", "quantity": "0", "cash": {"code": "EUR", "amount": "25"}},
                    {"broker_id": broker_id, "type": "FEE", "date": "2025-01-18", "quantity": "0", "cash": {"code": "EUR", "amount": "-10"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "SELL", "date": "2025-01-19", "quantity": "-1", "cash": {"code": "EUR", "amount": "150"}},
                ],
            )

            resp = await post_portfolio_summary(client)
        assert resp.status_code == 200
        data = resp.json()
        assert data["cash_total"]["amount"].startswith("765")
        assert data["net_worth"]["amount"].startswith("765")
        assert data["total_invested"]["amount"].startswith("1000")
        assert len(data["missing_prices_assets"]) == 1
        assert data["holdings"][0]["current_value"] is None
        print_success("Signed cash ledger and missing-price reporting OK")

    async def test_summary_uses_quote_base_quantity(self, test_server):
        """Summary valuation honors quote_base_quantity for raw market quotes."""
        print_section("Portfolio Summary: quote base quantity")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_broker(client)
            asset_id = await create_asset(client, currency="EUR", quote_base_quantity=100)

            await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "type": "DEPOSIT", "date": "2025-02-01", "quantity": "0", "cash": {"code": "EUR", "amount": "500"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2025-02-02", "quantity": "200", "cash": {"code": "EUR", "amount": "-200"}},
                ],
            )
            price_resp = await client.post(
                f"{API_BASE}/assets/prices",
                json=[
                    {
                        "asset_id": asset_id,
                        "prices": [
                            {
                                "date": "2025-02-03",
                                "close": "102.00",
                                "currency": "EUR",
                            }
                        ],
                    }
                ],
                timeout=TIMEOUT,
            )
            assert price_resp.status_code == 200, f"Price upsert failed: {price_resp.status_code}: {price_resp.text}"

            resp = await post_portfolio_summary(client)
        assert resp.status_code == 200
        data = resp.json()
        assert data["holdings"][0]["current_value"]["amount"].startswith("204")
        assert data["net_worth"]["amount"].startswith("504")
        print_success("quote_base_quantity summary valuation OK")

    async def test_filter_by_broker(self, test_server):
        """broker_ids body field filters the response."""
        print_section("Portfolio Summary: filter by broker")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_broker(client)

            resp = await post_portfolio_summary(client, {"broker_ids": [broker_id]})
        assert resp.status_code == 200
        print_success("Broker filter OK")

    async def test_include_breakdown(self, test_server):
        """include_breakdown=true in body -> by_broker is populated."""
        print_section("Portfolio Summary: include_breakdown")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            await create_broker(client)

            resp = await post_portfolio_summary(client, {"include_breakdown": True})
        assert resp.status_code == 200
        data = resp.json()
        # by_broker may be empty list if no accessible brokers, but must be a list
        assert data["by_broker"] is not None
        assert isinstance(data["by_broker"], list)
        print_success("include_breakdown OK")

    async def test_invalid_broker_id_ignored(self, test_server):
        """Non-existent broker_id in body -> empty result (no 500)."""
        print_section("Portfolio Summary: nonexistent broker")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            resp = await post_portfolio_summary(client, {"broker_ids": [999999]})
        assert resp.status_code == 200
        print_success("Nonexistent broker handled gracefully")


# ---------------------------------------------------------------------------
# TestPortfolioHistoryEndpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestPortfolioHistoryEndpoint:
    async def test_unauthenticated(self, test_server):
        """POST /portfolio/history without auth -> 401."""
        print_section("Portfolio History: unauthenticated")
        async with httpx.AsyncClient() as client:
            resp = await post_portfolio_history(client)
        assert resp.status_code == 401
        print_success("401 as expected")

    async def test_empty_history(self, test_server):
        """New user → history is empty array."""
        print_section("Portfolio History: empty")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            resp = await post_portfolio_history(client)
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
                creates=[
                    {
                        "broker_id": broker_id,
                        "type": "DEPOSIT",
                        "date": "2025-03-01",
                        "quantity": "0",
                        "cash": {"code": "EUR", "amount": "5000"},
                    }
                ],
            )
            resp = await post_portfolio_history(client)
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
        """date_range body filter narrows history."""
        print_section("Portfolio History: date range filter")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            await create_broker(client)
            resp = await post_portfolio_history(
                client,
                {"date_range": {"start": "2025-01-01", "end": "2025-06-30"}},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        print_success("Date range filter OK")

    async def test_history_cash_uses_all_signed_transactions(self, test_server):
        """History cash curve includes signed BUY/DIVIDEND/FEE events."""
        print_section("Portfolio History: signed cash ledger")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_broker(client)
            asset_id = await create_asset(client)

            await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "type": "DEPOSIT", "date": "2025-03-01", "quantity": "0", "cash": {"code": "EUR", "amount": "1000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2025-03-02", "quantity": "4", "cash": {"code": "EUR", "amount": "-400"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "DIVIDEND", "date": "2025-03-03", "quantity": "0", "cash": {"code": "EUR", "amount": "25"}},
                    {"broker_id": broker_id, "type": "FEE", "date": "2025-03-04", "quantity": "0", "cash": {"code": "EUR", "amount": "-10"}},
                ],
            )
            resp = await post_portfolio_history(
                client,
                {"date_range": {"start": "2025-03-01", "end": "2025-03-04"}},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert [point["date"] for point in data] == ["2025-03-01", "2025-03-02", "2025-03-03", "2025-03-04"]
        assert data[0]["cash_value"]["amount"].startswith("1000")
        assert data[1]["cash_value"]["amount"].startswith("600")
        assert data[2]["cash_value"]["amount"].startswith("625")
        assert data[3]["cash_value"]["amount"].startswith("615")
        print_success("Signed cash curve OK")

    async def test_history_uses_quote_base_quantity(self, test_server):
        """History mark-to-market uses quote_base_quantity for invested/nav values."""
        print_section("Portfolio History: quote base quantity")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_broker(client)
            asset_id = await create_asset(client, currency="EUR", quote_base_quantity=100)

            await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "type": "DEPOSIT", "date": "2025-04-01", "quantity": "0", "cash": {"code": "EUR", "amount": "500"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2025-04-02", "quantity": "200", "cash": {"code": "EUR", "amount": "-200"}},
                ],
            )
            price_resp = await client.post(
                f"{API_BASE}/assets/prices",
                json=[
                    {
                        "asset_id": asset_id,
                        "prices": [
                            {
                                "date": "2025-04-03",
                                "close": "102.00",
                                "currency": "EUR",
                            }
                        ],
                    }
                ],
                timeout=TIMEOUT,
            )
            assert price_resp.status_code == 200, f"Price upsert failed: {price_resp.status_code}: {price_resp.text}"

            resp = await post_portfolio_history(
                client,
                {"date_range": {"start": "2025-04-03", "end": "2025-04-03"}},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["invested_value"]["amount"].startswith("204")
        assert data[0]["nav_value"]["amount"].startswith("504")
        print_success("quote_base_quantity history valuation OK")


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

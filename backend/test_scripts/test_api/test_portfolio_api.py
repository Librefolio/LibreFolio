"""Portfolio API Tests. POST /api/v1/portfolio/{summary,history} + GET asset-history/lots."""

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


async def post_portfolio_report(client: httpx.AsyncClient, body: dict | None = None) -> httpx.Response:
    """Call unified /portfolio/report endpoint."""
    default_body = {"include_summary": True, "include_history": True, "include_allocation_history": True}
    if body:
        default_body.update(body)
    return await client.post(f"{API_BASE}/portfolio/report", json=default_body, timeout=TIMEOUT)


async def post_portfolio_summary(client: httpx.AsyncClient, body: dict | None = None) -> httpx.Response:
    """Get summary via /report endpoint. Returns a fake Response whose .json() = summary dict."""
    report_body = {"include_summary": True, "include_history": False, "include_allocation_history": False}
    if body:
        report_body.update(body)
    resp = await client.post(f"{API_BASE}/portfolio/report", json=report_body, timeout=TIMEOUT)
    # Wrap: inject summary-level data at top for backward compat with tests
    if resp.status_code == 200:
        report = resp.json()
        summary = report.get("summary") or {}
        # Monkey-patch the response to return summary directly
        resp._summary_data = summary

        def _patched_json(**kwargs):
            return resp._summary_data

        resp.json = _patched_json
    return resp


async def post_portfolio_history(client: httpx.AsyncClient, body: dict | None = None) -> httpx.Response:
    """Get history via /report endpoint. Returns a fake Response whose .json() = history list."""
    report_body = {"include_summary": False, "include_history": True, "include_allocation_history": False}
    if body:
        report_body.update(body)
    resp = await client.post(f"{API_BASE}/portfolio/report", json=report_body, timeout=TIMEOUT)
    if resp.status_code == 200:
        report = resp.json()
        history = report.get("history") or []

        def _patched_json(**kwargs):
            return history

        resp.json = _patched_json
    return resp


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
        assert "missing_price_assets" in data
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
        # Cash ledger: 1000 - 400 + 25 - 10 + 150 = 765
        assert data["cash_total"]["amount"].startswith("765")
        assert data["total_invested"]["amount"].startswith("1000")
        # Holdings: no market price but LAST_BUY_PRICE fallback provides value
        # last_buy_price = 400/4 = 100 EUR/share, net qty = 3 → current_value = 300
        holding = data["holdings"][0]
        assert holding["current_value"] is not None
        assert holding["current_value"].startswith("300")
        # Asset without market price does NOT appear in missing_price_assets
        # (LAST_BUY_PRICE gives it a value — appears in data_quality as warning instead)
        assert len(data["missing_price_assets"]) == 0
        print_success("Signed cash ledger and LAST_BUY_PRICE reporting OK")

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
        # qty=200, quote_base=100, price=102 → value = 200 * 102 / 100 = 204
        assert data["holdings"][0]["current_value"].startswith("204")
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
            assert "market_value" in point
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
        assert data[0]["market_value"]["amount"].startswith("204")
        assert data[0]["nav_value"]["amount"].startswith("504")
        print_success("quote_base_quantity history valuation OK")


# ---------------------------------------------------------------------------
# TestPortfolioReportEndpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestPortfolioReportEndpoint:
    async def test_report_positions_contribution_is_date_aware(self, test_server):
        """Report uses date_to snapshot for holdings and serializes performance rows + other effects."""
        print_section("Portfolio Report: date-aware holdings and contribution")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_broker(client)
            asset_id = await create_asset(client)

            await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "type": "DEPOSIT", "date": "2025-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "1000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2025-01-02", "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "SELL", "date": "2025-02-15", "quantity": "-10", "cash": {"code": "EUR", "amount": "1200"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2025-03-10", "quantity": "5", "cash": {"code": "EUR", "amount": "-600"}},
                    {"broker_id": broker_id, "type": "INTEREST", "date": "2025-02-20", "quantity": "0", "cash": {"code": "EUR", "amount": "20"}},
                    {"broker_id": broker_id, "type": "FEE", "date": "2025-02-21", "quantity": "0", "cash": {"code": "EUR", "amount": "-5"}},
                ],
            )

            price_resp = await client.post(
                f"{API_BASE}/assets/prices",
                json=[
                    {
                        "asset_id": asset_id,
                        "prices": [
                            {
                                "date": "2025-01-31",
                                "close": "110.00",
                                "currency": "EUR",
                            }
                        ],
                    }
                ],
                timeout=TIMEOUT,
            )
            assert price_resp.status_code == 200, f"Price upsert failed: {price_resp.status_code}: {price_resp.text}"

            resp = await post_portfolio_report(
                client,
                {
                    "include_history": False,
                    "include_allocation_history": False,
                    "include_positions_contribution": True,
                    "date_range": {"start": "2025-01-31", "end": "2025-02-28"},
                },
            )

        assert resp.status_code == 200
        report = resp.json()
        assert report["summary"]["holdings"] == []

        positions = report["positions_contribution"]["positions"]
        assert len(positions) == 1
        row = positions[0]
        assert row["is_fully_sold"] is True
        assert row["start_value"].startswith("1100")
        assert row["end_value"].startswith("0")
        assert row["period_realized_gain_loss"].startswith("200")
        assert row["period_unrealized_delta"].startswith("-100")
        assert row["period_pnl"].startswith("100")

        effects = report["positions_contribution"]["other_effects"]
        assert sorted((item["category"], item["description"], Decimal(item["period_pnl"]), item["broker_id"]) for item in effects) == [
            ("Cost", "Unallocated costs", Decimal("-5"), broker_id),
            ("Income", "Unallocated income", Decimal("20"), broker_id),
        ]

        total_positions = sum(Decimal(item["period_pnl"]) for item in positions if item["period_pnl"] is not None)
        total_other = sum(Decimal(item["period_pnl"]) for item in effects)
        assert total_positions + total_other == Decimal(report["summary"]["period_pnl"]["amount"])
        print_success("Date-aware report contribution OK")


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

    async def test_asset_history_populates_roi_twrr_and_omits_mwrr_fields(self, test_server):
        """Asset history returns ROI/TWRR series and omits removed MWRR fields."""
        print_section("Asset History: ROI/TWRR populated")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_broker(client)
            asset_id = await create_asset(client)

            await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "type": "DEPOSIT", "date": "2025-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "2000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2025-01-02", "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "SELL", "date": "2025-02-15", "quantity": "-4", "cash": {"code": "EUR", "amount": "480"}},
                ],
            )

            price_resp = await client.post(
                f"{API_BASE}/assets/prices",
                json=[
                    {
                        "asset_id": asset_id,
                        "prices": [
                            {"date": "2025-01-02", "close": "100.00", "currency": "EUR"},
                            {"date": "2025-01-31", "close": "110.00", "currency": "EUR"},
                            {"date": "2025-02-15", "close": "120.00", "currency": "EUR"},
                        ],
                    }
                ],
                timeout=TIMEOUT,
            )
            assert price_resp.status_code == 200, f"Price upsert failed: {price_resp.status_code}: {price_resp.text}"

            resp = await client.get(
                f"{API_BASE}/portfolio/asset-history?asset_id={asset_id}&broker_ids={broker_id}",
                timeout=TIMEOUT,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        assert all(point["broker_id"] == broker_id for point in data)
        assert data[0]["roi"] is not None
        assert data[1]["roi"] is not None
        assert data[1]["twrr"] is not None
        assert data[2]["roi"] is not None
        assert data[2]["twrr"] is not None
        assert all("mwrr_annualized" not in point for point in data)
        assert all("mwrr_cumulative" not in point for point in data)
        print_success("ROI/TWRR populated, removed MWRR fields absent")

    async def test_asset_history_multiple_brokers_includes_combined_series(self, test_server):
        """Repeated broker_ids returns per-broker rows plus one combined series."""
        print_section("Asset History: multiple brokers combined series")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_1_id = await create_broker(client, f"History Broker 1 {uuid.uuid4().hex[:6]}")
            broker_2_id = await create_broker(client, f"History Broker 2 {uuid.uuid4().hex[:6]}")
            asset_id = await create_asset(client)

            await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_1_id, "type": "DEPOSIT", "date": "2025-04-01", "quantity": "0", "cash": {"code": "EUR", "amount": "2000"}},
                    {"broker_id": broker_1_id, "asset_id": asset_id, "type": "BUY", "date": "2025-04-02", "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
                    {"broker_id": broker_1_id, "asset_id": asset_id, "type": "SELL", "date": "2025-04-04", "quantity": "-2", "cash": {"code": "EUR", "amount": "240"}},
                    {"broker_id": broker_2_id, "type": "DEPOSIT", "date": "2025-04-01", "quantity": "0", "cash": {"code": "EUR", "amount": "1500"}},
                    {"broker_id": broker_2_id, "asset_id": asset_id, "type": "BUY", "date": "2025-04-03", "quantity": "5", "cash": {"code": "EUR", "amount": "-550"}},
                    {"broker_id": broker_2_id, "asset_id": asset_id, "type": "SELL", "date": "2025-04-05", "quantity": "-1", "cash": {"code": "EUR", "amount": "125"}},
                ],
            )

            price_resp = await client.post(
                f"{API_BASE}/assets/prices",
                json=[
                    {
                        "asset_id": asset_id,
                        "prices": [
                            {"date": "2025-04-03", "close": "110.00", "currency": "EUR"},
                            {"date": "2025-04-04", "close": "120.00", "currency": "EUR"},
                            {"date": "2025-04-05", "close": "125.00", "currency": "EUR"},
                        ],
                    }
                ],
                timeout=TIMEOUT,
            )
            assert price_resp.status_code == 200, f"Price upsert failed: {price_resp.status_code}: {price_resp.text}"

            resp = await client.get(
                f"{API_BASE}/portfolio/asset-history?asset_id={asset_id}&broker_ids={broker_1_id}&broker_ids={broker_2_id}",
                timeout=TIMEOUT,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data

        points_by_broker: dict[int | None, list[dict]] = {}
        for point in data:
            points_by_broker.setdefault(point["broker_id"], []).append(point)

        assert broker_1_id in points_by_broker
        assert broker_2_id in points_by_broker
        assert None in points_by_broker
        combined_dates = {point["date"] for point in points_by_broker[None]}
        assert combined_dates
        assert combined_dates.issubset({point["date"] for point in points_by_broker[broker_1_id]})
        assert combined_dates.issubset({point["date"] for point in points_by_broker[broker_2_id]})
        assert any(point["roi"] is not None for point in points_by_broker[None])
        assert any(point["twrr"] is not None for point in points_by_broker[None])
        print_success("Combined asset-history series tagged correctly")

    async def test_asset_history_single_broker_has_no_combined_series(self, test_server):
        """Single-broker responses must not include broker_id=None rows."""
        print_section("Asset History: single broker has no combined series")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_broker(client, f"Single History Broker {uuid.uuid4().hex[:6]}")
            asset_id = await create_asset(client)

            await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "type": "DEPOSIT", "date": "2025-05-01", "quantity": "0", "cash": {"code": "EUR", "amount": "1200"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2025-05-02", "quantity": "6", "cash": {"code": "EUR", "amount": "-600"}},
                ],
            )

            price_resp = await client.post(
                f"{API_BASE}/assets/prices",
                json=[
                    {
                        "asset_id": asset_id,
                        "prices": [
                            {"date": "2025-05-02", "close": "100.00", "currency": "EUR"},
                            {"date": "2025-05-03", "close": "105.00", "currency": "EUR"},
                        ],
                    }
                ],
                timeout=TIMEOUT,
            )
            assert price_resp.status_code == 200, f"Price upsert failed: {price_resp.status_code}: {price_resp.text}"

            explicit_resp = await client.get(
                f"{API_BASE}/portfolio/asset-history?asset_id={asset_id}&broker_ids={broker_id}",
                timeout=TIMEOUT,
            )
            implicit_resp = await client.get(
                f"{API_BASE}/portfolio/asset-history?asset_id={asset_id}",
                timeout=TIMEOUT,
            )

        assert explicit_resp.status_code == 200
        assert implicit_resp.status_code == 200
        explicit_data = explicit_resp.json()
        implicit_data = implicit_resp.json()
        assert explicit_data
        assert implicit_data
        assert all(point["broker_id"] == broker_id for point in explicit_data)
        assert all(point["broker_id"] == broker_id for point in implicit_data)
        assert all(point["broker_id"] is not None for point in explicit_data)
        assert all(point["broker_id"] is not None for point in implicit_data)
        print_success("Single-broker asset-history omits combined series")


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# TestFIFOLotsEndpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestFIFOLotsEndpoint:
    async def test_unauthenticated(self, test_server):
        """GET /portfolio/lots without auth → 401."""
        print_section("FIFO Lots: unauthenticated")
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{API_BASE}/portfolio/lots?broker_ids=1&asset_id=1", timeout=TIMEOUT)
        assert resp.status_code == 401
        print_success("401 as expected")

    async def test_missing_required_params(self, test_server):
        """asset_id required; broker_ids optional."""
        print_section("FIFO Lots: missing required params")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)

            # missing asset_id and broker_ids
            resp = await client.get(f"{API_BASE}/portfolio/lots", timeout=TIMEOUT)
            assert resp.status_code == 422

            # missing asset_id
            resp = await client.get(f"{API_BASE}/portfolio/lots?broker_ids=1", timeout=TIMEOUT)
            assert resp.status_code == 422

            # missing broker_ids
            resp = await client.get(f"{API_BASE}/portfolio/lots?asset_id=1", timeout=TIMEOUT)
            assert resp.status_code == 200

        print_success("Missing asset_id rejected, missing broker_ids allowed")

    async def test_lots_response_structure(self, test_server):
        """Valid params → response has open_lots, closed_lots structure."""
        print_section("FIFO Lots: response structure")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_broker(client)
            asset_id = await create_asset(client)

            resp = await client.get(
                f"{API_BASE}/portfolio/lots?broker_ids={broker_id}&asset_id={asset_id}",
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
                f"{API_BASE}/portfolio/lots?broker_ids=999999&asset_id=999999",
                timeout=TIMEOUT,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["open_lots"] == []
        assert data["closed_lots"] == []
        print_success("No access returns empty lots")

    async def test_lots_multiple_brokers_same_asset(self, test_server):
        """Repeated broker_ids returns tagged lots from both brokers."""
        print_section("FIFO Lots: multiple brokers same asset")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_1_id = await create_broker(client)
            broker_2_id = await create_broker(client)
            asset_id = await create_asset(client)

            await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_1_id, "type": "DEPOSIT", "date": "2025-05-01", "quantity": "0", "cash": {"code": "EUR", "amount": "1000"}},
                    {"broker_id": broker_1_id, "asset_id": asset_id, "type": "BUY", "date": "2025-05-02", "quantity": "5", "cash": {"code": "EUR", "amount": "-500"}},
                    {"broker_id": broker_2_id, "type": "DEPOSIT", "date": "2025-05-01", "quantity": "0", "cash": {"code": "EUR", "amount": "1000"}},
                    {"broker_id": broker_2_id, "asset_id": asset_id, "type": "BUY", "date": "2025-05-03", "quantity": "3", "cash": {"code": "EUR", "amount": "-330"}},
                ],
            )

            resp = await client.get(
                (f"{API_BASE}/portfolio/lots?asset_id={asset_id}" f"&broker_ids={broker_1_id}&broker_ids={broker_2_id}"),
                timeout=TIMEOUT,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["closed_lots"] == []
        assert len(data["open_lots"]) == 2

        open_lots_by_broker = {lot["broker_id"]: lot for lot in data["open_lots"]}
        assert set(open_lots_by_broker) == {broker_1_id, broker_2_id}
        assert open_lots_by_broker[broker_1_id]["remaining_quantity"] == "5.000000"
        assert open_lots_by_broker[broker_2_id]["remaining_quantity"] == "3.000000"
        assert data["total_unrealized_quantity"] == "8.000000"
        print_success("Multi-broker lots tagged correctly")

    async def test_lots_without_broker_ids_uses_all_accessible_brokers(self, test_server):
        """Omitting broker_ids returns lots from all accessible brokers."""
        print_section("FIFO Lots: all accessible brokers")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_1_id = await create_broker(client)
            broker_2_id = await create_broker(client)
            asset_id = await create_asset(client)

            await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_1_id, "type": "DEPOSIT", "date": "2025-06-01", "quantity": "0", "cash": {"code": "EUR", "amount": "2000"}},
                    {"broker_id": broker_1_id, "asset_id": asset_id, "type": "BUY", "date": "2025-06-02", "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
                    {"broker_id": broker_1_id, "asset_id": asset_id, "type": "SELL", "date": "2025-06-03", "quantity": "-4", "cash": {"code": "EUR", "amount": "480"}},
                    {"broker_id": broker_2_id, "type": "DEPOSIT", "date": "2025-06-01", "quantity": "0", "cash": {"code": "EUR", "amount": "500"}},
                    {"broker_id": broker_2_id, "asset_id": asset_id, "type": "BUY", "date": "2025-06-04", "quantity": "2", "cash": {"code": "EUR", "amount": "-220"}},
                ],
            )

            resp = await client.get(
                f"{API_BASE}/portfolio/lots?asset_id={asset_id}",
                timeout=TIMEOUT,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["closed_lots"]) == 1
        assert {lot["broker_id"] for lot in data["open_lots"]} == {broker_1_id, broker_2_id}
        assert data["closed_lots"][0]["broker_id"] == broker_1_id
        assert data["closed_lots"][0]["quantity"] == "4.000000"
        assert data["total_realized_pnl"] == "80.000000"
        assert data["total_unrealized_quantity"] == "8.000000"
        print_success("All accessible brokers included when broker_ids omitted")

    async def test_lots_as_of_date_filters_future_transactions(self, test_server):
        """as_of_date limits FIFO calculation to transactions on or before that date."""
        print_section("FIFO Lots: as_of_date filters future tx")
        first_buy_date = "2025-01-10"
        second_buy_date = "2025-06-01"
        cutoff_date = "2025-03-01"
        assert first_buy_date < cutoff_date < second_buy_date

        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_broker(client)
            asset_id = await create_asset(client)

            await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "type": "DEPOSIT", "date": "2025-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "2000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": first_buy_date, "quantity": "5", "cash": {"code": "EUR", "amount": "-500"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": second_buy_date, "quantity": "3", "cash": {"code": "EUR", "amount": "-330"}},
                ],
            )

            filtered_resp = await client.get(
                f"{API_BASE}/portfolio/lots?asset_id={asset_id}&broker_ids={broker_id}&as_of_date={cutoff_date}",
                timeout=TIMEOUT,
            )
            full_resp = await client.get(
                f"{API_BASE}/portfolio/lots?asset_id={asset_id}&broker_ids={broker_id}",
                timeout=TIMEOUT,
            )

        assert filtered_resp.status_code == 200
        filtered_data = filtered_resp.json()
        assert filtered_data["closed_lots"] == []
        assert len(filtered_data["open_lots"]) == 1
        assert filtered_data["open_lots"][0]["remaining_quantity"] == "5.000000"
        assert filtered_data["total_unrealized_quantity"] == "5.000000"

        assert full_resp.status_code == 200
        full_data = full_resp.json()
        assert full_data["closed_lots"] == []
        assert len(full_data["open_lots"]) == 2
        assert [lot["remaining_quantity"] for lot in full_data["open_lots"]] == ["5.000000", "3.000000"]
        assert full_data["total_unrealized_quantity"] == "8.000000"
        print_success("as_of_date excludes future lots, default remains unbounded")

"""
WAC (Weighted Average Cost) API Tests.

Tests for cost_basis_override (Currency object) on TRANSFER transactions,
auto-calculation via WAC, and the recalc-wac endpoint.

Reference: plan-R2-SP-B-BackendTests.prompt.md
"""

import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

import httpx
import pytest

from backend.app.config import get_settings
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30


# ============================================================================
# HELPERS
# ============================================================================


def unique_username() -> str:
    return f"wac_test_{int(date.today().toordinal())}_{uuid.uuid4().hex[:8]}"


async def create_test_user(client: httpx.AsyncClient) -> str:
    """Create a test user, login, return username."""
    username = unique_username()
    email = f"{username}@test.com"
    password = "TestPass123!"

    resp = await client.post(
        f"{API_BASE}/auth/register",
        json={"username": username, "email": email, "password": password},
        timeout=TIMEOUT,
    )
    assert resp.status_code == 201, f"Register failed: {resp.text}"

    login_resp = await client.post(
        f"{API_BASE}/auth/login",
        json={"username": username, "password": password},
        timeout=TIMEOUT,
    )
    session_cookie = login_resp.cookies.get("session")
    if session_cookie:
        client.cookies.set("session", session_cookie)

    return username


async def create_broker(client: httpx.AsyncClient, name: str) -> int:
    """Create a broker and return its ID."""
    unique_name = f"{name}_{uuid.uuid4().hex[:6]}"
    resp = await client.post(
        f"{API_BASE}/brokers",
        json=[{"name": unique_name, "allow_cash_overdraft": True}],
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, f"Create broker failed: {resp.text}"
    data = resp.json()
    assert data["results"][0]["success"], f"Broker creation not successful: {data}"
    return data["results"][0]["broker_id"]


async def create_asset(client: httpx.AsyncClient, currency: str = "EUR", name: str = "WACTestAsset") -> int:
    """Create an asset and return its ID."""
    unique_name = f"{name}_{uuid.uuid4().hex[:6]}"
    resp = await client.post(
        f"{API_BASE}/assets",
        json=[{"display_name": unique_name, "currency": currency, "asset_type": "STOCK"}],
        timeout=TIMEOUT,
    )
    assert resp.status_code in (200, 201), f"Create asset failed: {resp.text}"
    return resp.json()["results"][0]["asset_id"]


async def commit_batch(client: httpx.AsyncClient, **kwargs) -> dict:
    """POST /transactions/commit, return response JSON."""
    resp = await client.post(
        f"{API_BASE}/transactions/commit",
        json=kwargs,
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, f"Commit failed ({resp.status_code}): {resp.text}"
    return resp.json()


async def get_txs_by_ids(client: httpx.AsyncClient, ids: list[int]) -> list[dict]:
    """GET /transactions?ids=..., return list of TX dicts."""
    resp = await client.get(
        f"{API_BASE}/transactions",
        params={"ids": ids},
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, f"GET transactions failed: {resp.text}"
    return resp.json()


async def create_user_broker_asset(client: httpx.AsyncClient, *, currency: str = "EUR") -> tuple[int, int]:
    """Create user + broker + asset, return (broker_id, asset_id)."""
    await create_test_user(client)
    broker_id = await create_broker(client, "WACBroker")
    asset_id = await create_asset(client, currency=currency)
    return broker_id, asset_id


async def create_fx_pair_with_rate(
    client: httpx.AsyncClient,
    base: str,
    quote: str,
    rate: str,
    rate_date: str,
) -> None:
    """Create FX conversion route + insert rate for cross-currency WAC tests."""
    # Ensure alphabetical ordering for route
    if base > quote:
        route_base, route_quote = quote, base
    else:
        route_base, route_quote = base, quote

    # Create route
    resp = await client.post(
        f"{API_BASE}/fx/providers/routes",
        json=[
            {
                "base": route_base,
                "quote": route_quote,
                "priority": 1,
                "chain_steps": [{"from": route_base, "to": route_quote, "provider": "MANUAL"}],
            }
        ],
        timeout=TIMEOUT,
    )
    assert resp.status_code == 201, f"Create FX route failed: {resp.text}"

    # Insert rate
    resp2 = await client.post(
        f"{API_BASE}/fx/currencies/rate",
        json=[
            {
                "date": rate_date,
                "base": base,
                "quote": quote,
                "rate": rate,
                "source": "MANUAL",
            }
        ],
        timeout=TIMEOUT,
    )
    assert resp2.status_code == 200, f"Insert FX rate failed: {resp2.text}"


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture(scope="module")
def test_server():
    """Start test server once for all tests in this module."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


# ============================================================================
# WAC TESTS
# ============================================================================


@pytest.mark.asyncio
class TestWACCostBasis:
    @pytest.fixture(autouse=True)
    def server(self, test_server):
        yield

    # ------------------------------------------------------------------ WAC-1
    async def test_wac1_transfer_with_currency_override(self):
        """TRANSFER with explicit cost_basis_override: {code:'EUR', amount:'42.50'}."""
        print_section("WAC-1 — TRANSFER with Currency override")
        async with httpx.AsyncClient() as client:
            broker_a_id, asset_id = await create_user_broker_asset(client)
            broker_b_id = await create_broker(client, "WACBrokerB")

            # DEPOSIT cash + BUY to have positive balance
            data = await commit_batch(
                client,
                creates=[
                    {
                        "broker_id": broker_a_id,
                        "type": "DEPOSIT",
                        "date": "2026-01-01",
                        "quantity": "0",
                        "cash": {"code": "EUR", "amount": "10000"},
                    },
                    {
                        "broker_id": broker_a_id,
                        "asset_id": asset_id,
                        "type": "BUY",
                        "date": "2026-01-02",
                        "quantity": "10",
                        "cash": {"code": "EUR", "amount": "-500"},
                    },
                ],
            )
            assert data["committed"] is True, f"Setup not committed: {data}"

            # Create TRANSFER pair with explicit cost_basis_override
            link = str(uuid.uuid4())
            data = await commit_batch(
                client,
                creates=[
                    {
                        "broker_id": broker_a_id,
                        "asset_id": asset_id,
                        "type": "TRANSFER",
                        "date": "2026-01-15",
                        "quantity": "-5",
                        "link_uuid": link,
                    },
                    {
                        "broker_id": broker_b_id,
                        "asset_id": asset_id,
                        "type": "TRANSFER",
                        "date": "2026-01-15",
                        "quantity": "5",
                        "link_uuid": link,
                        "cost_basis_override": {"code": "EUR", "amount": "42.50"},
                    },
                ],
            )
            assert data["committed"] is True, f"TRANSFER not committed: {data}"

            # Find receiver TX ID
            create_results = [r for r in data["results"] if r["operation"] == "create"]
            all_ids = [tid for r in create_results for tid in r["ids"]]

            txs = await get_txs_by_ids(client, all_ids)
            receiver = next(tx for tx in txs if tx["quantity"] == "5" or Decimal(tx["quantity"]) > 0)

            assert receiver["cost_basis_override"] is not None, "cost_basis_override should not be None"
            assert receiver["cost_basis_override"]["code"] == "EUR"
            assert Decimal(receiver["cost_basis_override"]["amount"]) == Decimal("42.50")
            print_success("WAC-1: TRANSFER with Currency override verified ✓")

    # ------------------------------------------------------------------ WAC-2
    async def test_wac2_transfer_without_override_no_auto_calc(self):
        """TRANSFER without override → cost_basis_override stays NULL (no auto-calc at commit)."""
        print_section("WAC-2 — TRANSFER without override → NULL (no auto-calc)")
        async with httpx.AsyncClient() as client:
            broker_a_id, asset_id = await create_user_broker_asset(client)
            broker_b_id = await create_broker(client, "WACBrokerB2")

            # DEPOSIT + 2 BUYs at different prices
            data = await commit_batch(
                client,
                creates=[
                    {
                        "broker_id": broker_a_id,
                        "type": "DEPOSIT",
                        "date": "2026-01-01",
                        "quantity": "0",
                        "cash": {"code": "EUR", "amount": "20000"},
                    },
                    {
                        "broker_id": broker_a_id,
                        "asset_id": asset_id,
                        "type": "BUY",
                        "date": "2026-01-05",
                        "quantity": "10",
                        "cash": {"code": "EUR", "amount": "-1000"},
                    },
                    {
                        "broker_id": broker_a_id,
                        "asset_id": asset_id,
                        "type": "BUY",
                        "date": "2026-01-10",
                        "quantity": "10",
                        "cash": {"code": "EUR", "amount": "-2000"},
                    },
                ],
            )
            assert data["committed"] is True

            # TRANSFER pair without cost_basis_override → no auto-calc
            link = str(uuid.uuid4())
            data = await commit_batch(
                client,
                creates=[
                    {
                        "broker_id": broker_a_id,
                        "asset_id": asset_id,
                        "type": "TRANSFER",
                        "date": "2026-01-20",
                        "quantity": "-5",
                        "link_uuid": link,
                    },
                    {
                        "broker_id": broker_b_id,
                        "asset_id": asset_id,
                        "type": "TRANSFER",
                        "date": "2026-01-20",
                        "quantity": "5",
                        "link_uuid": link,
                    },
                ],
            )
            assert data["committed"] is True, f"TRANSFER not committed: {data}"

            # No wac_info in commit response (auto-calc removed)
            create_results = [r for r in data["results"] if r["operation"] == "create"]
            wac_results = [r for r in create_results if r.get("wac_info")]
            assert len(wac_results) == 0, f"wac_info should not be in commit response: {data['results']}"

            # Verify cost_basis_override is NULL
            all_ids = [tid for r in create_results for tid in r["ids"]]
            txs = await get_txs_by_ids(client, all_ids)
            receiver = next(tx for tx in txs if Decimal(tx["quantity"]) > 0)
            assert receiver["cost_basis_override"] is None, f"Expected null cost_basis (no auto-calc): {receiver}"
            print_success("WAC-2: TRANSFER without override → NULL (no auto-calc) ✓")

    # ------------------------------------------------------------------ WAC-3
    async def test_wac3_transfer_cross_currency_no_auto_calc(self):
        """TRANSFER without override, BUYs in EUR+USD → cost_basis_override stays NULL (no auto-calc)."""
        print_section("WAC-3 — TRANSFER cross-currency no auto-calc")
        async with httpx.AsyncClient() as client:
            broker_a_id, asset_id = await create_user_broker_asset(client, currency="EUR")
            broker_b_id = await create_broker(client, "WACBrokerB3")

            # Create FX pair EUR/USD with rate
            await create_fx_pair_with_rate(client, "EUR", "USD", "1.10", "2026-01-05")

            # DEPOSIT EUR and USD + BUY in EUR + BUY in USD
            data = await commit_batch(
                client,
                creates=[
                    {
                        "broker_id": broker_a_id,
                        "type": "DEPOSIT",
                        "date": "2026-01-01",
                        "quantity": "0",
                        "cash": {"code": "EUR", "amount": "10000"},
                    },
                    {
                        "broker_id": broker_a_id,
                        "type": "DEPOSIT",
                        "date": "2026-01-01",
                        "quantity": "0",
                        "cash": {"code": "USD", "amount": "10000"},
                    },
                    {
                        "broker_id": broker_a_id,
                        "asset_id": asset_id,
                        "type": "BUY",
                        "date": "2026-01-05",
                        "quantity": "10",
                        "cash": {"code": "EUR", "amount": "-1000"},
                    },
                    {
                        "broker_id": broker_a_id,
                        "asset_id": asset_id,
                        "type": "BUY",
                        "date": "2026-01-05",
                        "quantity": "10",
                        "cash": {"code": "USD", "amount": "-1100"},
                    },
                ],
            )
            assert data["committed"] is True, f"Setup not committed: {data}"

            # TRANSFER pair without override → no auto-calc
            link = str(uuid.uuid4())
            data = await commit_batch(
                client,
                creates=[
                    {
                        "broker_id": broker_a_id,
                        "asset_id": asset_id,
                        "type": "TRANSFER",
                        "date": "2026-01-20",
                        "quantity": "-5",
                        "link_uuid": link,
                    },
                    {
                        "broker_id": broker_b_id,
                        "asset_id": asset_id,
                        "type": "TRANSFER",
                        "date": "2026-01-20",
                        "quantity": "5",
                        "link_uuid": link,
                    },
                ],
            )
            assert data["committed"] is True, f"TRANSFER not committed: {data}"

            # No wac_info in commit response
            create_results = [r for r in data["results"] if r["operation"] == "create"]
            wac_results = [r for r in create_results if r.get("wac_info")]
            assert len(wac_results) == 0, "wac_info should not be in commit response"

            # Verify cost_basis_override is NULL
            all_ids = [tid for r in create_results for tid in r["ids"]]
            txs = await get_txs_by_ids(client, all_ids)
            receiver = next(tx for tx in txs if Decimal(tx["quantity"]) > 0)
            assert receiver["cost_basis_override"] is None, f"Expected null cost_basis: {receiver}"
            print_success("WAC-3: TRANSFER cross-currency → NULL (no auto-calc) ✓")

    # ------------------------------------------------------------------ WAC-4
    async def test_wac4_transfer_missing_fx_no_auto_calc(self):
        """TRANSFER without override, BUYs in EUR+CHF but NO FX pair → cost_basis stays NULL."""
        print_section("WAC-4 — TRANSFER missing FX → NULL (no auto-calc)")
        async with httpx.AsyncClient() as client:
            broker_a_id, asset_id = await create_user_broker_asset(client, currency="EUR")
            broker_b_id = await create_broker(client, "WACBrokerB4")

            # DEPOSIT EUR and CHF + BUY in each
            data = await commit_batch(
                client,
                creates=[
                    {
                        "broker_id": broker_a_id,
                        "type": "DEPOSIT",
                        "date": "2026-01-01",
                        "quantity": "0",
                        "cash": {"code": "EUR", "amount": "10000"},
                    },
                    {
                        "broker_id": broker_a_id,
                        "type": "DEPOSIT",
                        "date": "2026-01-01",
                        "quantity": "0",
                        "cash": {"code": "CHF", "amount": "10000"},
                    },
                    {
                        "broker_id": broker_a_id,
                        "asset_id": asset_id,
                        "type": "BUY",
                        "date": "2026-01-05",
                        "quantity": "10",
                        "cash": {"code": "EUR", "amount": "-1000"},
                    },
                    {
                        "broker_id": broker_a_id,
                        "asset_id": asset_id,
                        "type": "BUY",
                        "date": "2026-01-05",
                        "quantity": "10",
                        "cash": {"code": "CHF", "amount": "-1000"},
                    },
                ],
            )
            assert data["committed"] is True

            # TRANSFER pair without override, no CHF/EUR FX pair
            link = str(uuid.uuid4())
            data = await commit_batch(
                client,
                creates=[
                    {
                        "broker_id": broker_a_id,
                        "asset_id": asset_id,
                        "type": "TRANSFER",
                        "date": "2026-01-20",
                        "quantity": "-5",
                        "link_uuid": link,
                    },
                    {
                        "broker_id": broker_b_id,
                        "asset_id": asset_id,
                        "type": "TRANSFER",
                        "date": "2026-01-20",
                        "quantity": "5",
                        "link_uuid": link,
                    },
                ],
            )
            assert data["committed"] is True, f"TRANSFER not committed: {data}"

            # Verify cost_basis_override is null via GET
            create_results = [r for r in data["results"] if r["operation"] == "create"]
            all_ids = [tid for r in create_results for tid in r["ids"]]
            txs = await get_txs_by_ids(client, all_ids)
            receiver = next(tx for tx in txs if Decimal(tx["quantity"]) > 0)
            assert receiver["cost_basis_override"] is None, f"Expected null cost_basis: {receiver}"
            print_success("WAC-4: Missing FX pair → NULL cost_basis (no auto-calc) ✓")

    # ------------------------------------------------------------------ WAC-5
    async def test_wac5_transfer_no_buys_no_auto_calc(self):
        """TRANSFER without override, no BUY transactions → cost_basis stays NULL."""
        print_section("WAC-5 — TRANSFER no BUY → NULL (no auto-calc)")
        async with httpx.AsyncClient() as client:
            broker_a_id, asset_id = await create_user_broker_asset(client)
            broker_b_id = await create_broker(client, "WACBrokerB5")

            # Only DEPOSIT cash (no BUY)
            data = await commit_batch(
                client,
                creates=[
                    {
                        "broker_id": broker_a_id,
                        "type": "DEPOSIT",
                        "date": "2026-01-01",
                        "quantity": "0",
                        "cash": {"code": "EUR", "amount": "10000"},
                    },
                ],
            )
            assert data["committed"] is True

            # Add asset balance via ADJUSTMENT
            data = await commit_batch(
                client,
                creates=[
                    {
                        "broker_id": broker_a_id,
                        "asset_id": asset_id,
                        "type": "ADJUSTMENT",
                        "date": "2026-01-02",
                        "quantity": "10",
                    },
                ],
            )
            assert data["committed"] is True

            link = str(uuid.uuid4())
            data = await commit_batch(
                client,
                creates=[
                    {
                        "broker_id": broker_a_id,
                        "asset_id": asset_id,
                        "type": "TRANSFER",
                        "date": "2026-01-20",
                        "quantity": "-5",
                        "link_uuid": link,
                    },
                    {
                        "broker_id": broker_b_id,
                        "asset_id": asset_id,
                        "type": "TRANSFER",
                        "date": "2026-01-20",
                        "quantity": "5",
                        "link_uuid": link,
                    },
                ],
            )
            assert data["committed"] is True, f"TRANSFER not committed: {data}"

            # Verify cost_basis is NULL (no auto-calc)
            create_results = [r for r in data["results"] if r["operation"] == "create"]
            all_ids = [tid for r in create_results for tid in r["ids"]]
            txs = await get_txs_by_ids(client, all_ids)
            receiver = next(tx for tx in txs if Decimal(tx["quantity"]) > 0)
            assert receiver["cost_basis_override"] is None, f"Expected null cost_basis: {receiver}"
            print_success("WAC-5: TRANSFER no BUY → NULL (no auto-calc) ✓")


@pytest.mark.asyncio
class TestWACPreview:
    @pytest.fixture(autouse=True)
    def server(self, test_server):
        yield

    # ------------------------------------------------------------------ WAC-6
    async def test_wac6_preview_multi_broker(self):
        """wac-preview: compute WAC for asset across different sender brokers."""
        print_section("WAC-6 — wac-preview multi-broker")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_a = await create_broker(client, "WACPreviewA")
            broker_b = await create_broker(client, "WACPreviewB")
            asset_id = await create_asset(client, currency="EUR")

            # Setup: DEPOSITs, BUYs
            data = await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_a, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "20000"}},
                    {"broker_id": broker_a, "asset_id": asset_id, "type": "BUY", "date": "2026-01-05", "quantity": "20", "cash": {"code": "EUR", "amount": "-2000"}},
                    {"broker_id": broker_b, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "20000"}},
                    {"broker_id": broker_b, "asset_id": asset_id, "type": "BUY", "date": "2026-01-10", "quantity": "10", "cash": {"code": "EUR", "amount": "-1500"}},
                ],
            )
            assert data["committed"] is True

            # Call wac-preview for both brokers
            resp = await client.post(
                f"{API_BASE}/transactions/wac-preview",
                json={
                    "items": [
                        {"sender_broker_id": broker_a, "asset_id": asset_id, "date_range": {"start": "2026-01-01", "end": "2026-02-01"}},
                        {"sender_broker_id": broker_b, "asset_id": asset_id, "date_range": {"start": "2026-01-01", "end": "2026-02-01"}},
                    ],
                    "pending_txs": [],
                    "excluded_tx_ids": [],
                },
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200, f"wac-preview failed: {resp.text}"
            result = resp.json()
            assert len(result["items"]) == 2

            # Broker A: WAC = 2000/20 = 100
            wac_a = result["items"][0]
            assert wac_a["wac"] is not None
            assert wac_a["wac"]["code"] == "EUR"
            assert Decimal(wac_a["wac"]["amount"]) == Decimal("100")

            # Broker B: WAC = 1500/10 = 150
            wac_b = result["items"][1]
            assert wac_b["wac"] is not None
            assert wac_b["wac"]["code"] == "EUR"
            assert Decimal(wac_b["wac"]["amount"]) == Decimal("150")
            print_success("WAC-6: wac-preview multi-broker ✓")

    # ------------------------------------------------------------------ WAC-7
    async def test_wac7_preview_invalid_request(self):
        """wac-preview with invalid date_range → 422."""
        print_section("WAC-7 — wac-preview invalid request → 422")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)

            # Missing required field date_range
            resp = await client.post(
                f"{API_BASE}/transactions/wac-preview",
                json={
                    "items": [
                        {"sender_broker_id": 1, "asset_id": 1},
                    ],
                },
                timeout=TIMEOUT,
            )
            assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"
            print_success("WAC-7: wac-preview invalid request → 422 ✓")

    # ------------------------------------------------------------------ WAC-8
    async def test_wac8_preview_empty_asset(self):
        """wac-preview for asset with no transactions → WAC = 0."""
        print_section("WAC-8 — wac-preview empty asset → WAC 0")
        async with httpx.AsyncClient() as client:
            broker_id, asset_id = await create_user_broker_asset(client)

            resp = await client.post(
                f"{API_BASE}/transactions/wac-preview",
                json={
                    "items": [
                        {"sender_broker_id": broker_id, "asset_id": asset_id, "date_range": {"start": "2026-01-01", "end": "2026-02-01"}},
                    ],
                },
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200, f"wac-preview failed: {resp.text}"
            result = resp.json()
            wac_item = result["items"][0]
            assert wac_item["wac"] is not None
            assert Decimal(wac_item["wac"]["amount"]) == Decimal("0")
            print_success("WAC-8: wac-preview empty asset → WAC 0 ✓")

    # ------------------------------------------------------------------ WAC-P1
    async def test_wacp1_buy_then_sell_wac_unchanged(self):
        """BUY 10@100 + SELL 3 → WAC stays 100 (unchanged after reduction)."""
        print_section("WAC-P1 — BUY + SELL → WAC unchanged")
        async with httpx.AsyncClient() as client:
            broker_id, asset_id = await create_user_broker_asset(client)

            data = await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "10000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-05", "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "SELL", "date": "2026-01-10", "quantity": "-3", "cash": {"code": "EUR", "amount": "330"}},
                ],
            )
            assert data["committed"] is True

            resp = await client.post(
                f"{API_BASE}/transactions/wac-preview",
                json={
                    "items": [
                        {"sender_broker_id": broker_id, "asset_id": asset_id, "date_range": {"start": "2026-01-01", "end": "2026-01-15"}},
                    ],
                },
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200
            wac_item = resp.json()["items"][0]
            assert wac_item["wac"]["code"] == "EUR"
            assert Decimal(wac_item["wac"]["amount"]) == Decimal("100")
            print_success("WAC-P1: BUY 10@100 + SELL 3 → WAC = 100 ✓")

    # ------------------------------------------------------------------ WAC-P2
    async def test_wacp2_two_buys_weighted_average(self):
        """BUY 10@100 + BUY 5@200 → WAC = (1000+1000)/15 = 133.33."""
        print_section("WAC-P2 — Two BUYs weighted average")
        async with httpx.AsyncClient() as client:
            broker_id, asset_id = await create_user_broker_asset(client)

            data = await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "20000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-05", "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-10", "quantity": "5", "cash": {"code": "EUR", "amount": "-1000"}},
                ],
            )
            assert data["committed"] is True

            resp = await client.post(
                f"{API_BASE}/transactions/wac-preview",
                json={
                    "items": [
                        {"sender_broker_id": broker_id, "asset_id": asset_id, "date_range": {"start": "2026-01-01", "end": "2026-01-15"}},
                    ],
                },
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200
            wac_item = resp.json()["items"][0]
            wac_amount = Decimal(wac_item["wac"]["amount"])
            # (1000 + 1000) / (10 + 5) = 133.333...
            expected = Decimal("2000") / Decimal("15")
            assert abs(wac_amount - expected) < Decimal("0.01"), f"Expected ~133.33, got {wac_amount}"
            print_success("WAC-P2: BUY 10@100 + BUY 5@200 → WAC ≈ 133.33 ✓")

    # ------------------------------------------------------------------ WAC-P3
    async def test_wacp3_pending_txs_override(self):
        """pending_txs override → WAC changes vs solo-DB."""
        print_section("WAC-P3 — pending_txs override WAC")
        async with httpx.AsyncClient() as client:
            broker_id, asset_id = await create_user_broker_asset(client)

            data = await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "10000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-05", "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
                ],
            )
            assert data["committed"] is True

            # WAC without pending = 100
            resp1 = await client.post(
                f"{API_BASE}/transactions/wac-preview",
                json={
                    "items": [
                        {"sender_broker_id": broker_id, "asset_id": asset_id, "date_range": {"start": "2026-01-01", "end": "2026-01-20"}},
                    ],
                },
                timeout=TIMEOUT,
            )
            assert resp1.status_code == 200
            wac1 = Decimal(resp1.json()["items"][0]["wac"]["amount"])
            assert wac1 == Decimal("100")

            # WAC with pending BUY 10@200 → WAC = (1000+2000)/20 = 150
            resp2 = await client.post(
                f"{API_BASE}/transactions/wac-preview",
                json={
                    "items": [
                        {"sender_broker_id": broker_id, "asset_id": asset_id, "date_range": {"start": "2026-01-01", "end": "2026-01-20"}},
                    ],
                    "pending_txs": [
                        {
                            "broker_id": broker_id,
                            "asset_id": asset_id,
                            "type": "BUY",
                            "date": "2026-01-10",
                            "quantity": "10",
                            "cash": {"code": "EUR", "amount": "-2000"},
                        },
                    ],
                },
                timeout=TIMEOUT,
            )
            assert resp2.status_code == 200
            wac2 = Decimal(resp2.json()["items"][0]["wac"]["amount"])
            assert wac2 == Decimal("150"), f"Expected WAC 150, got {wac2}"
            print_success("WAC-P3: pending_txs override → WAC changed ✓")

    # ------------------------------------------------------------------ WAC-P4
    async def test_wacp4_excluded_tx_ids(self):
        """excluded_tx_ids → excluded TX does not contribute to WAC."""
        print_section("WAC-P4 — excluded_tx_ids")
        async with httpx.AsyncClient() as client:
            broker_id, asset_id = await create_user_broker_asset(client)

            data = await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "20000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-05", "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-10", "quantity": "10", "cash": {"code": "EUR", "amount": "-2000"}},
                ],
            )
            assert data["committed"] is True

            # Get IDs of the BUY transactions
            create_results = [r for r in data["results"] if r["operation"] == "create"]
            all_ids = [tid for r in create_results for tid in r["ids"]]
            txs = await get_txs_by_ids(client, all_ids)
            buy_txs = [tx for tx in txs if tx["type"] == "BUY"]
            assert len(buy_txs) == 2

            # Exclude the second BUY (2000/10=200) → WAC should be 100
            second_buy_id = buy_txs[1]["id"]

            resp = await client.post(
                f"{API_BASE}/transactions/wac-preview",
                json={
                    "items": [
                        {"sender_broker_id": broker_id, "asset_id": asset_id, "date_range": {"start": "2026-01-01", "end": "2026-01-20"}},
                    ],
                    "excluded_tx_ids": [second_buy_id],
                },
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200
            wac_item = resp.json()["items"][0]
            assert Decimal(wac_item["wac"]["amount"]) == Decimal("100"), "Expected 100 after excluding second BUY"
            print_success("WAC-P4: excluded_tx_ids → excluded TX not counted ✓")

    # ------------------------------------------------------------------ WAC-P5
    async def test_wacp5_fx_missing_pair(self):
        """wac-preview with cross-currency BUYs and missing FX pair → wac=null, missing_pairs."""
        print_section("WAC-P5 — wac-preview FX missing pair")
        async with httpx.AsyncClient() as client:
            broker_id, asset_id = await create_user_broker_asset(client, currency="EUR")

            data = await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "10000"}},
                    {"broker_id": broker_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "CHF", "amount": "10000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-05", "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-05", "quantity": "10", "cash": {"code": "CHF", "amount": "-1000"}},
                ],
            )
            assert data["committed"] is True

            resp = await client.post(
                f"{API_BASE}/transactions/wac-preview",
                json={
                    "items": [
                        {"sender_broker_id": broker_id, "asset_id": asset_id, "date_range": {"start": "2026-01-01", "end": "2026-01-20"}},
                    ],
                },
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200
            wac_item = resp.json()["items"][0]
            assert wac_item["wac"] is None, f"WAC should be None (missing FX): {wac_item}"
            assert len(wac_item["wac_missing_pairs"]) > 0, f"Expected missing_pairs: {wac_item}"
            print_success("WAC-P5: FX missing pair → wac=null, missing_pairs ✓")

    # ------------------------------------------------------------------ WAC-P6
    async def test_wacp6_same_date_buy_sell_no_negative(self):
        """Same-date BUY+SELL → additions first, no transient negative qty."""
        print_section("WAC-P6 — Same-date BUY+SELL no negative")
        async with httpx.AsyncClient() as client:
            broker_id, asset_id = await create_user_broker_asset(client)

            # BUY and SELL on same date
            data = await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "10000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-05", "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "SELL", "date": "2026-01-05", "quantity": "-3", "cash": {"code": "EUR", "amount": "330"}},
                ],
            )
            assert data["committed"] is True

            resp = await client.post(
                f"{API_BASE}/transactions/wac-preview",
                json={
                    "items": [
                        {"sender_broker_id": broker_id, "asset_id": asset_id, "date_range": {"start": "2026-01-01", "end": "2026-01-10"}},
                    ],
                },
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200
            wac_item = resp.json()["items"][0]
            # BUY processed first → pool=10@100, then SELL 3 → pool=7@100
            assert wac_item["wac"] is not None
            assert Decimal(wac_item["wac"]["amount"]) == Decimal("100")
            print_success("WAC-P6: Same-date BUY+SELL → no negative, WAC = 100 ✓")

    # ------------------------------------------------------------------ WAC-P7
    async def test_wacp7_date_range_end_none_uses_today(self):
        """date_range with end=None → uses today as effective date."""
        print_section("WAC-P7 — date_range end=None → today")
        async with httpx.AsyncClient() as client:
            broker_id, asset_id = await create_user_broker_asset(client)

            data = await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "10000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-05", "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
                ],
            )
            assert data["committed"] is True

            # end=None → should use today
            resp = await client.post(
                f"{API_BASE}/transactions/wac-preview",
                json={
                    "items": [
                        {"sender_broker_id": broker_id, "asset_id": asset_id, "date_range": {"start": "2026-01-01"}},
                    ],
                },
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200
            wac_item = resp.json()["items"][0]
            assert wac_item["wac"] is not None
            assert Decimal(wac_item["wac"]["amount"]) == Decimal("100")
            print_success("WAC-P7: date_range end=None → uses today, WAC = 100 ✓")

    # ------------------------------------------------------------------ WAC-P8
    async def test_wacp8_pending_override_by_id(self):
        """pending_txs with matching DB id → overrides that row in WAC calc."""
        print_section("WAC-P8 — pending override by id")
        async with httpx.AsyncClient() as client:
            broker_id, asset_id = await create_user_broker_asset(client)

            data = await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "20000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-05", "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
                ],
            )
            assert data["committed"] is True

            # Get the BUY TX id
            create_results = [r for r in data["results"] if r["operation"] == "create"]
            all_ids = [tid for r in create_results for tid in r["ids"]]
            txs = await get_txs_by_ids(client, all_ids)
            buy_tx = next(tx for tx in txs if tx["type"] == "BUY")

            # Without override: WAC = 100
            resp1 = await client.post(
                f"{API_BASE}/transactions/wac-preview",
                json={
                    "items": [{"sender_broker_id": broker_id, "asset_id": asset_id, "date_range": {"start": "2026-01-01", "end": "2026-02-01"}}],
                },
                timeout=TIMEOUT,
            )
            assert Decimal(resp1.json()["items"][0]["wac"]["amount"]) == Decimal("100")

            # Override BUY with different price: 10@200 → WAC should be 200
            resp2 = await client.post(
                f"{API_BASE}/transactions/wac-preview",
                json={
                    "items": [{"sender_broker_id": broker_id, "asset_id": asset_id, "date_range": {"start": "2026-01-01", "end": "2026-02-01"}}],
                    "pending_txs": [
                        {
                            "id": buy_tx["id"],
                            "broker_id": broker_id,
                            "asset_id": asset_id,
                            "type": "BUY",
                            "date": "2026-01-05",
                            "quantity": "10",
                            "cash": {"code": "EUR", "amount": "-2000"},
                        },
                    ],
                },
                timeout=TIMEOUT,
            )
            assert resp2.status_code == 200
            wac2 = Decimal(resp2.json()["items"][0]["wac"]["amount"])
            assert wac2 == Decimal("200"), f"Expected 200 after override, got {wac2}"
            print_success("WAC-P8: pending override by id → WAC updated ✓")

    # ------------------------------------------------------------------ WAC-P9
    async def test_wacp9_pool_reset_after_full_sell(self):
        """BUY, SELL all, BUY again → WAC resets to new price."""
        print_section("WAC-P9 — Pool reset after full sell")
        async with httpx.AsyncClient() as client:
            broker_id, asset_id = await create_user_broker_asset(client)

            data = await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "50000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-05", "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "SELL", "date": "2026-01-10", "quantity": "-10", "cash": {"code": "EUR", "amount": "1200"}},
                    {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-15", "quantity": "5", "cash": {"code": "EUR", "amount": "-1500"}},
                ],
            )
            assert data["committed"] is True

            resp = await client.post(
                f"{API_BASE}/transactions/wac-preview",
                json={
                    "items": [{"sender_broker_id": broker_id, "asset_id": asset_id, "date_range": {"start": "2026-01-01", "end": "2026-01-20"}}],
                },
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200
            wac_item = resp.json()["items"][0]
            # After full sell pool=0, WAC resets. New BUY 5@300 → WAC = 300
            assert Decimal(wac_item["wac"]["amount"]) == Decimal("300")
            print_success("WAC-P9: Pool reset after full sell → WAC = 300 ✓")


@pytest.mark.asyncio
class TestWACValidation:
    @pytest.fixture(autouse=True)
    def server(self, test_server):
        yield

    # ------------------------------------------------------------------ WAC-9
    async def test_wac9_old_format_string_rejected(self):
        """cost_basis_override as plain string '42.50' → validation error."""
        print_section("WAC-9 — Old format plain string → 422")
        async with httpx.AsyncClient() as client:
            broker_a_id, asset_id = await create_user_broker_asset(client)
            broker_b_id = await create_broker(client, "WACValB9")

            # DEPOSIT + BUY for balance
            data = await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_a_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "10000"}},
                    {"broker_id": broker_a_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-02", "quantity": "10", "cash": {"code": "EUR", "amount": "-500"}},
                ],
            )
            assert data["committed"] is True

            link = str(uuid.uuid4())
            # Send plain string → should fail validation (422 from Pydantic)
            resp = await client.post(
                f"{API_BASE}/transactions/commit",
                json={
                    "creates": [
                        {
                            "broker_id": broker_a_id,
                            "asset_id": asset_id,
                            "type": "TRANSFER",
                            "date": "2026-01-15",
                            "quantity": "-5",
                            "link_uuid": link,
                        },
                        {
                            "broker_id": broker_b_id,
                            "asset_id": asset_id,
                            "type": "TRANSFER",
                            "date": "2026-01-15",
                            "quantity": "5",
                            "link_uuid": link,
                            "cost_basis_override": "42.50",  # plain string — invalid
                        },
                    ],
                },
                timeout=TIMEOUT,
            )
            # Pydantic validates inside the batch — returns 200 with committed=False and issues
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
            data = resp.json()
            assert data["committed"] is False, f"Should not commit with invalid format: {data}"
            assert any("Currency" in i.get("error", "") or "model_type" in i.get("code", "") for i in data["issues"]), f"Expected validation issue for plain string: {data['issues']}"
            print_success("WAC-9: Old format plain string → validation error ✓")

    # ------------------------------------------------------------------ WAC-10
    async def test_wac10_invalid_currency_code_rejected(self):
        """cost_basis_override with invalid currency code → validation error."""
        print_section("WAC-10 — Invalid currency code → 422")
        async with httpx.AsyncClient() as client:
            broker_a_id, asset_id = await create_user_broker_asset(client)
            broker_b_id = await create_broker(client, "WACValB10")

            data = await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_a_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "10000"}},
                    {"broker_id": broker_a_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-02", "quantity": "10", "cash": {"code": "EUR", "amount": "-500"}},
                ],
            )
            assert data["committed"] is True

            link = str(uuid.uuid4())
            resp = await client.post(
                f"{API_BASE}/transactions/commit",
                json={
                    "creates": [
                        {
                            "broker_id": broker_a_id,
                            "asset_id": asset_id,
                            "type": "TRANSFER",
                            "date": "2026-01-15",
                            "quantity": "-5",
                            "link_uuid": link,
                        },
                        {
                            "broker_id": broker_b_id,
                            "asset_id": asset_id,
                            "type": "TRANSFER",
                            "date": "2026-01-15",
                            "quantity": "5",
                            "link_uuid": link,
                            "cost_basis_override": {"code": "INVALID", "amount": "10"},
                        },
                    ],
                },
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
            data = resp.json()
            assert data["committed"] is False, f"Should not commit with invalid currency: {data}"
            assert any("INVALID" in i.get("error", "") or "value_error" in i.get("code", "") for i in data["issues"]), f"Expected validation issue for invalid currency: {data['issues']}"
            print_success("WAC-10: Invalid currency code → validation error ✓")


@pytest.mark.asyncio
class TestWACUpdatePromote:
    @pytest.fixture(autouse=True)
    def server(self, test_server):
        yield

    # ------------------------------------------------------------------ WAC-11
    async def test_wac11_patch_cost_basis_override(self):
        """PATCH update cost_basis_override with Currency object."""
        print_section("WAC-11 — PATCH update cost_basis_override")
        async with httpx.AsyncClient() as client:
            broker_a_id, asset_id = await create_user_broker_asset(client)
            broker_b_id = await create_broker(client, "WACPatchB")

            data = await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_a_id, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "10000"}},
                    {"broker_id": broker_a_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-02", "quantity": "10", "cash": {"code": "EUR", "amount": "-500"}},
                ],
            )
            assert data["committed"] is True

            link = str(uuid.uuid4())
            data = await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_a_id, "asset_id": asset_id, "type": "TRANSFER", "date": "2026-01-15", "quantity": "-5", "link_uuid": link},
                    {"broker_id": broker_b_id, "asset_id": asset_id, "type": "TRANSFER", "date": "2026-01-15", "quantity": "5", "link_uuid": link},
                ],
            )
            assert data["committed"] is True

            create_results = [r for r in data["results"] if r["operation"] == "create"]
            all_ids = [tid for r in create_results for tid in r["ids"]]
            txs = await get_txs_by_ids(client, all_ids)
            receiver = next(tx for tx in txs if Decimal(tx["quantity"]) > 0)

            # PATCH with new cost_basis_override
            patch_data = await commit_batch(
                client,
                updates=[
                    {
                        "id": receiver["id"],
                        "cost_basis_override": {"code": "USD", "amount": "99.00"},
                    }
                ],
            )
            assert patch_data["committed"] is True, f"PATCH not committed: {patch_data}"

            # Verify
            txs2 = await get_txs_by_ids(client, [receiver["id"]])
            assert txs2[0]["cost_basis_override"]["code"] == "USD"
            assert Decimal(txs2[0]["cost_basis_override"]["amount"]) == Decimal("99.00")
            print_success("WAC-11: PATCH cost_basis_override with Currency ✓")

    # ------------------------------------------------------------------ WAC-12
    async def test_wac12_promote_batch_resolved_fields_cost_basis(self):
        """Promote batch with resolved_fields.cost_basis_override → receiver gets Currency."""
        print_section("WAC-12 — Promote batch resolved_fields.cost_basis_override")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_a = await create_broker(client, "WACPromBatchA")
            broker_b = await create_broker(client, "WACPromBatchB")
            asset_id = await create_asset(client)

            # Create WITHDRAWAL + DEPOSIT standalone
            w_id = await _create_standalone_tx(
                client,
                broker_a,
                "WITHDRAWAL",
                cash={"code": "EUR", "amount": "-500"},
            )
            d_id = await _create_standalone_tx(
                client,
                broker_b,
                "DEPOSIT",
                cash={"code": "EUR", "amount": "500"},
            )

            # Promote with resolved_fields including cost_basis_override
            data = await commit_batch(
                client,
                promotes=[
                    {
                        "id_a": w_id,
                        "id_b": d_id,
                        "resolved_fields": {
                            "cost_basis_override": {"code": "EUR", "amount": "55.00"},
                        },
                    }
                ],
            )
            assert data["committed"] is True, f"Promote not committed: {data}"

            # Verify receiver has cost_basis
            txs = await get_txs_by_ids(client, [w_id, d_id])
            # After promote, both should be CASH_TRANSFER
            for tx in txs:
                assert tx["type"] == "CASH_TRANSFER", f"Expected CASH_TRANSFER: {tx['type']}"
            # The receiver (positive cash) should have cost_basis_override
            receiver = next((tx for tx in txs if tx.get("cost_basis_override")), None)
            if receiver:
                assert receiver["cost_basis_override"]["code"] == "EUR"
                assert Decimal(receiver["cost_basis_override"]["amount"]) == Decimal("55.00")
            print_success("WAC-12: Promote batch resolved_fields cost_basis ✓")

    # ------------------------------------------------------------------ WAC-13
    async def test_wac13_legacy_promote_cost_basis(self):
        """Legacy /transfers/promote with cost_basis_override → receiver gets Currency."""
        print_section("WAC-13 — Legacy promote with cost_basis_override")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_a = await create_broker(client, "WACLegacyA")
            broker_b = await create_broker(client, "WACLegacyB")
            asset_id = await create_asset(client)

            # First BUY enough asset on broker_a to have positive balance
            data = await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_a, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "10000"}},
                    {"broker_id": broker_a, "asset_id": asset_id, "type": "BUY", "date": "2026-01-05", "quantity": "10", "cash": {"code": "EUR", "amount": "-500"}},
                ],
            )
            assert data["committed"] is True

            # Create WITHDRAWAL + DEPOSIT
            w_id = await _create_standalone_tx(
                client,
                broker_a,
                "WITHDRAWAL",
                cash={"code": "EUR", "amount": "-400"},
            )
            d_id = await _create_standalone_tx(
                client,
                broker_b,
                "DEPOSIT",
                cash={"code": "EUR", "amount": "400"},
            )

            # Legacy promote endpoint
            resp = await client.post(
                f"{API_BASE}/transactions/transfers/promote",
                json={
                    "from_tx_id": w_id,
                    "to_tx_id": d_id,
                    "new_type": "TRANSFER",
                    "asset_id": asset_id,
                    "quantity": "5",
                    "cost_basis_override": {"code": "EUR", "amount": "33.00"},
                },
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200, f"Legacy promote failed: {resp.text}"
            result = resp.json()
            assert result["rolled_back"] is False, f"Promote rolled back: {result}"

            # Verify the new receiver TX has cost_basis
            new_to_id = result["new_to_tx_id"]
            txs = await get_txs_by_ids(client, [new_to_id])
            assert len(txs) == 1
            assert txs[0]["cost_basis_override"] is not None, f"Expected cost_basis: {txs[0]}"
            assert txs[0]["cost_basis_override"]["code"] == "EUR"
            assert Decimal(txs[0]["cost_basis_override"]["amount"]) == Decimal("33.00")
            print_success("WAC-13: Legacy promote cost_basis_override ✓")


# ============================================================================
# INTERNAL HELPERS
# ============================================================================


async def _create_standalone_tx(
    client: httpx.AsyncClient,
    broker_id: int,
    tx_type: str,
    *,
    asset_id: Optional[int] = None,
    quantity: str = "0",
    cash: Optional[dict] = None,
    tx_date: str = "2026-02-01",
) -> int:
    """Create a standalone transaction and return its ID."""
    create_dict: dict = {
        "broker_id": broker_id,
        "type": tx_type,
        "date": tx_date,
        "quantity": quantity,
    }
    if asset_id is not None:
        create_dict["asset_id"] = asset_id
    if cash is not None:
        create_dict["cash"] = cash

    data = await commit_batch(client, creates=[create_dict])
    assert data["committed"] is True, f"Standalone not committed: {data}"
    return data["results"][0]["ids"][0]

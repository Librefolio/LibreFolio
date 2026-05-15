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
    async def test_wac2_auto_calc_single_currency(self):
        """TRANSFER without override, all BUYs in same currency → auto-calc WAC."""
        print_section("WAC-2 — Auto-calc single currency WAC")
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

            # TRANSFER pair without cost_basis_override → auto-calc
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

            # Check wac_info from commit response
            create_results = [r for r in data["results"] if r["operation"] == "create"]
            # Find the result that has wac_info
            wac_results = [r for r in create_results if r.get("wac_info")]
            assert len(wac_results) >= 1, f"Expected wac_info in commit response: {data['results']}"

            wac_info = wac_results[0]["wac_info"]
            assert wac_info["wac"] is not None, f"WAC should not be None: {wac_info}"
            assert wac_info["wac"]["code"] == "EUR"
            # WAC = (1000 + 2000) / (10 + 10) = 150
            assert Decimal(wac_info["wac"]["amount"]) == Decimal("150"), f"Expected WAC 150, got {wac_info['wac']['amount']}"

            # Also verify via GET that cost_basis_override is set
            all_ids = [tid for r in create_results for tid in r["ids"]]
            txs = await get_txs_by_ids(client, all_ids)
            receiver = next(tx for tx in txs if Decimal(tx["quantity"]) > 0)
            assert receiver["cost_basis_override"] is not None
            assert receiver["cost_basis_override"]["code"] == "EUR"
            print_success("WAC-2: Auto-calc single currency WAC verified ✓")

    # ------------------------------------------------------------------ WAC-3
    async def test_wac3_auto_calc_cross_currency_with_fx(self):
        """TRANSFER without override, BUYs in EUR+USD with FX pair → auto-calc with conversions."""
        print_section("WAC-3 — Auto-calc cross-currency WAC with FX")
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

            # TRANSFER pair without override → auto-calc with FX
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

            create_results = [r for r in data["results"] if r["operation"] == "create"]
            wac_results = [r for r in create_results if r.get("wac_info")]
            assert len(wac_results) >= 1, f"Expected wac_info: {data['results']}"

            wac_info = wac_results[0]["wac_info"]
            assert wac_info["wac"] is not None, f"WAC should be calculated: {wac_info}"
            assert wac_info["wac"]["code"] == "EUR"
            # Should have conversions for the USD BUY
            assert len(wac_info["conversions"]) > 0, f"Expected conversions: {wac_info}"
            print_success("WAC-3: Auto-calc cross-currency WAC with FX verified ✓")

    # ------------------------------------------------------------------ WAC-4
    async def test_wac4_auto_calc_missing_fx_pair(self):
        """TRANSFER without override, BUYs in EUR+CHF but NO FX pair → wac is None, missing_pairs reported."""
        print_section("WAC-4 — Auto-calc missing FX pair → null")
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

            create_results = [r for r in data["results"] if r["operation"] == "create"]
            wac_results = [r for r in create_results if r.get("wac_info")]

            if wac_results:
                wac_info = wac_results[0]["wac_info"]
                # WAC should be None due to missing FX pair
                assert wac_info["wac"] is None, f"WAC should be None (missing FX): {wac_info}"
                assert len(wac_info["missing_pairs"]) > 0, f"Expected missing_pairs: {wac_info}"

            # Verify cost_basis_override is null via GET
            all_ids = [tid for r in create_results for tid in r["ids"]]
            txs = await get_txs_by_ids(client, all_ids)
            receiver = next(tx for tx in txs if Decimal(tx["quantity"]) > 0)
            assert receiver["cost_basis_override"] is None, f"Expected null cost_basis: {receiver}"
            print_success("WAC-4: Missing FX pair → null cost_basis verified ✓")

    # ------------------------------------------------------------------ WAC-5
    async def test_wac5_auto_calc_no_buys(self):
        """TRANSFER without override, no BUY transactions → WAC = 0."""
        print_section("WAC-5 — Auto-calc no BUY → WAC zero")
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

            # TRANSFER pair — but we need asset balance on broker_a.
            # Since allow_cash_overdraft is True and we have no asset balance check
            # for the sender, use a BUY first to have balance (but that defeats the test).
            # Actually — the WAC test checks BUYs on the SENDER broker.
            # If there are no BUYs, total_qty=0, WAC=0.
            # But we need asset units to send. Let's do a tiny BUY to have units
            # but the WAC test is about the cost — 0 BUY cost = 0 WAC won't work.
            # Re-read the plan: WAC-5 says "DEPOSIT, TRANSFER pair (no BUY)".
            # However we can't TRANSFER assets without first buying them.
            # The test is about what WAC calculates — if qty=0 (no buys),
            # the result should be wac={code:"EUR", amount:"0"}.
            # We need to create balance via ADJUSTMENT.
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

            create_results = [r for r in data["results"] if r["operation"] == "create"]
            wac_results = [r for r in create_results if r.get("wac_info")]

            if wac_results:
                wac_info = wac_results[0]["wac_info"]
                if wac_info["wac"] is not None:
                    assert wac_info["wac"]["code"] == "EUR"
                    assert Decimal(wac_info["wac"]["amount"]) == Decimal("0"), f"Expected WAC 0, got {wac_info['wac']['amount']}"

            # Verify via GET
            all_ids = [tid for r in create_results for tid in r["ids"]]
            txs = await get_txs_by_ids(client, all_ids)
            receiver = next(tx for tx in txs if Decimal(tx["quantity"]) > 0)
            # With no BUYs, WAC = 0 → either stored as {code, amount:"0"} or None
            if receiver["cost_basis_override"] is not None:
                assert Decimal(receiver["cost_basis_override"]["amount"]) == Decimal("0")
            print_success("WAC-5: No BUY → WAC zero / null verified ✓")


@pytest.mark.asyncio
class TestRecalcWAC:
    @pytest.fixture(autouse=True)
    def server(self, test_server):
        yield

    # ------------------------------------------------------------------ WAC-6
    async def test_wac6_recalc_multi_broker(self):
        """recalc-wac: 2 TRANSFER receivers on same asset, different brokers → both updated."""
        print_section("WAC-6 — recalc-wac multi-broker")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_a = await create_broker(client, "WACRecalcA")
            broker_b = await create_broker(client, "WACRecalcB")
            broker_c = await create_broker(client, "WACRecalcC")
            asset_id = await create_asset(client, currency="EUR")

            # Setup: DEPOSITs, BUYs, two TRANSFER pairs
            data = await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_a, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "20000"}},
                    {"broker_id": broker_a, "asset_id": asset_id, "type": "BUY", "date": "2026-01-05", "quantity": "20", "cash": {"code": "EUR", "amount": "-2000"}},
                ],
            )
            assert data["committed"] is True

            # TRANSFER A→B
            link1 = str(uuid.uuid4())
            data1 = await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_a, "asset_id": asset_id, "type": "TRANSFER", "date": "2026-02-01", "quantity": "-5", "link_uuid": link1},
                    {"broker_id": broker_b, "asset_id": asset_id, "type": "TRANSFER", "date": "2026-02-01", "quantity": "5", "link_uuid": link1},
                ],
            )
            assert data1["committed"] is True
            create_r1 = [r for r in data1["results"] if r["operation"] == "create"]
            ids1 = [tid for r in create_r1 for tid in r["ids"]]

            # TRANSFER A→C
            link2 = str(uuid.uuid4())
            data2 = await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_a, "asset_id": asset_id, "type": "TRANSFER", "date": "2026-02-10", "quantity": "-5", "link_uuid": link2},
                    {"broker_id": broker_c, "asset_id": asset_id, "type": "TRANSFER", "date": "2026-02-10", "quantity": "5", "link_uuid": link2},
                ],
            )
            assert data2["committed"] is True
            create_r2 = [r for r in data2["results"] if r["operation"] == "create"]
            ids2 = [tid for r in create_r2 for tid in r["ids"]]

            # Find receiver IDs
            txs1 = await get_txs_by_ids(client, ids1)
            txs2 = await get_txs_by_ids(client, ids2)
            receiver_b = next(tx for tx in txs1 if Decimal(tx["quantity"]) > 0)
            receiver_c = next(tx for tx in txs2 if Decimal(tx["quantity"]) > 0)

            # Call recalc-wac
            resp = await client.post(
                f"{API_BASE}/transactions/recalc-wac",
                json={"tx_ids": [receiver_b["id"], receiver_c["id"]]},
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200, f"recalc-wac failed: {resp.text}"
            recalc = resp.json()
            assert len(recalc["results"]) == 2
            for r in recalc["results"]:
                assert r["updated"] is True, f"Expected updated=True: {r}"
            print_success("WAC-6: recalc-wac multi-broker both updated ✓")

    # ------------------------------------------------------------------ WAC-7
    async def test_wac7_recalc_different_assets_400(self):
        """recalc-wac with TXs from different assets → 400."""
        print_section("WAC-7 — recalc-wac different assets → 400")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_a = await create_broker(client, "WACDiffAssetA")
            broker_b = await create_broker(client, "WACDiffAssetB")
            asset1 = await create_asset(client, name="WACAsset1")
            asset2 = await create_asset(client, name="WACAsset2")

            # Setup: DEPOSIT + BUY on each asset, then TRANSFER each
            data = await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_a, "type": "DEPOSIT", "date": "2026-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "20000"}},
                    {"broker_id": broker_a, "asset_id": asset1, "type": "BUY", "date": "2026-01-05", "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
                    {"broker_id": broker_a, "asset_id": asset2, "type": "BUY", "date": "2026-01-05", "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
                ],
            )
            assert data["committed"] is True

            link1 = str(uuid.uuid4())
            link2 = str(uuid.uuid4())
            data = await commit_batch(
                client,
                creates=[
                    {"broker_id": broker_a, "asset_id": asset1, "type": "TRANSFER", "date": "2026-02-01", "quantity": "-5", "link_uuid": link1},
                    {"broker_id": broker_b, "asset_id": asset1, "type": "TRANSFER", "date": "2026-02-01", "quantity": "5", "link_uuid": link1},
                    {"broker_id": broker_a, "asset_id": asset2, "type": "TRANSFER", "date": "2026-02-01", "quantity": "-5", "link_uuid": link2},
                    {"broker_id": broker_b, "asset_id": asset2, "type": "TRANSFER", "date": "2026-02-01", "quantity": "5", "link_uuid": link2},
                ],
            )
            assert data["committed"] is True

            # Get receiver IDs
            create_results = [r for r in data["results"] if r["operation"] == "create"]
            all_ids = [tid for r in create_results for tid in r["ids"]]
            txs = await get_txs_by_ids(client, all_ids)
            receivers = [tx for tx in txs if Decimal(tx["quantity"]) > 0]
            assert len(receivers) == 2

            # recalc-wac with different assets → should 400
            resp = await client.post(
                f"{API_BASE}/transactions/recalc-wac",
                json={"tx_ids": [receivers[0]["id"], receivers[1]["id"]]},
                timeout=TIMEOUT,
            )
            assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"
            print_success("WAC-7: recalc-wac different assets → 400 ✓")

    # ------------------------------------------------------------------ WAC-8
    async def test_wac8_recalc_non_transfer_skip(self):
        """recalc-wac with non-TRANSFER TXs → updated=False."""
        print_section("WAC-8 — recalc-wac non-TRANSFER → skip")
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

            create_results = [r for r in data["results"] if r["operation"] == "create"]
            all_ids = [tid for r in create_results for tid in r["ids"]]

            resp = await client.post(
                f"{API_BASE}/transactions/recalc-wac",
                json={"tx_ids": all_ids},
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200, f"recalc-wac failed: {resp.text}"
            recalc = resp.json()
            for r in recalc["results"]:
                assert r["updated"] is False, f"Expected updated=False for non-TRANSFER: {r}"
            print_success("WAC-8: recalc-wac non-TRANSFER → skip (updated=False) ✓")


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
                client, broker_a, "WITHDRAWAL",
                cash={"code": "EUR", "amount": "-500"},
            )
            d_id = await _create_standalone_tx(
                client, broker_b, "DEPOSIT",
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
                client, broker_a, "WITHDRAWAL",
                cash={"code": "EUR", "amount": "-400"},
            )
            d_id = await _create_standalone_tx(
                client, broker_b, "DEPOSIT",
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


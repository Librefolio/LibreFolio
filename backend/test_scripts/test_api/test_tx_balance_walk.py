"""
Transaction Balance Walk Tests.

Tests for same-day ordering, end-of-day balance validation,
and cascading effects of edits/deletes on balance integrity.

Covers edge cases documented in:
  plan-phase07-transaction-Part4_Round6_PlanC2Round2_FixRegressionsAndMockFX.prompt.md
  Section: "Pending: Same-Day Ordering Algorithm"

Key property under test:
  _validate_broker_balances() uses END-OF-DAY balance checking:
  all transactions of a day are accumulated BEFORE checking constraints.
  Order within a day does NOT matter — only the net balance at EOD.
"""

import uuid
from datetime import date, timedelta

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


def _uid() -> str:
    return f"bw_{uuid.uuid4().hex[:8]}"


async def _setup(client: httpx.AsyncClient) -> tuple[int, int]:
    """Create user, broker (no overdraft), asset. Return (broker_id, asset_id)."""
    username = _uid()
    email = f"{username}@test.com"
    pwd = "TestPass123!"

    await client.post(f"{API_BASE}/auth/register", json={"username": username, "email": email, "password": pwd}, timeout=TIMEOUT)
    await client.post(f"{API_BASE}/auth/login", json={"username": username, "password": pwd}, timeout=TIMEOUT)

    # Broker with overdraft DISABLED (balance constraints active)
    broker_name = f"BWBroker_{_uid()}"
    r = await client.post(f"{API_BASE}/brokers", json=[{"name": broker_name, "allow_cash_overdraft": False, "allow_asset_shorting": False}], timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    broker_id = r.json()["results"][0]["broker_id"]

    # Asset
    asset_name = f"BWAsset_{_uid()}"
    r = await client.post(f"{API_BASE}/assets", json=[{"display_name": asset_name, "currency": "EUR", "asset_type": "STOCK"}], timeout=TIMEOUT)
    assert r.status_code in (200, 201), r.text
    asset_id = r.json()["results"][0]["asset_id"]

    return broker_id, asset_id


async def _commit(client: httpx.AsyncClient, payload: dict) -> dict:
    r = await client.post(f"{API_BASE}/transactions/commit", json=payload, timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    return r.json()


async def _validate(client: httpx.AsyncClient, payload: dict) -> dict:
    r = await client.post(f"{API_BASE}/transactions/validate", json=payload, timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    return r.json()


# ============================================================================
# TEST CLASS
# ============================================================================


@pytest.fixture(scope="module")
def test_server():
    with _TestingServerManager() as mgr:
        if not mgr.start_server():
            pytest.fail("Failed to start test server")
        yield mgr


@pytest.mark.asyncio
class TestBalanceWalk:
    """End-of-day balance walk validation tests."""

    @pytest.fixture(autouse=True)
    def _server(self, test_server):
        yield

    # ------------------------------------------------------------------
    # Test 1: Same-day DEPOSIT+BUY (natural order) → pass
    # ------------------------------------------------------------------
    async def test_same_day_deposit_then_buy_pass(self):
        print_section("Balance Walk: same-day DEPOSIT then BUY → pass")
        async with httpx.AsyncClient() as client:
            broker_id, asset_id = await _setup(client)
            today = str(date.today())

            resp = await _commit(
                client,
                {
                    "creates": [
                        {"broker_id": broker_id, "type": "DEPOSIT", "date": today, "quantity": "0", "cash": {"code": "EUR", "amount": "1000"}},
                        {"broker_id": broker_id, "type": "BUY", "date": today, "quantity": "5", "asset_id": asset_id, "cash": {"code": "EUR", "amount": "-500"}},
                    ]
                },
            )

            assert resp["committed"] is True, f"Expected committed=True, got {resp}"
            assert len(resp.get("issues", [])) == 0
            print_success("DEPOSIT+BUY same day → committed OK (net EOD: +500)")

    # ------------------------------------------------------------------
    # Test 2: Same-day BUY+DEPOSIT (inverted order) → pass (end-of-day)
    # ------------------------------------------------------------------
    async def test_same_day_buy_then_deposit_pass(self):
        print_section("Balance Walk: same-day BUY then DEPOSIT (inverted) → pass")
        async with httpx.AsyncClient() as client:
            broker_id, asset_id = await _setup(client)
            today = str(date.today())

            # BUY first in array, DEPOSIT second — order should NOT matter
            resp = await _commit(
                client,
                {
                    "creates": [
                        {"broker_id": broker_id, "type": "BUY", "date": today, "quantity": "5", "asset_id": asset_id, "cash": {"code": "EUR", "amount": "-500"}},
                        {"broker_id": broker_id, "type": "DEPOSIT", "date": today, "quantity": "0", "cash": {"code": "EUR", "amount": "1000"}},
                    ]
                },
            )

            assert resp["committed"] is True, f"Expected committed=True (EOD check), got {resp}"
            assert len(resp.get("issues", [])) == 0
            print_success("BUY+DEPOSIT same day (inverted) → committed OK (EOD net: +500)")

    # ------------------------------------------------------------------
    # Test 3: Same-day net negative → fail
    # ------------------------------------------------------------------
    async def test_same_day_net_negative_fail(self):
        print_section("Balance Walk: same-day net negative → fail")
        async with httpx.AsyncClient() as client:
            broker_id, asset_id = await _setup(client)
            today = str(date.today())

            resp = await _commit(
                client,
                {
                    "creates": [
                        {"broker_id": broker_id, "type": "DEPOSIT", "date": today, "quantity": "0", "cash": {"code": "EUR", "amount": "100"}},
                        {"broker_id": broker_id, "type": "BUY", "date": today, "quantity": "5", "asset_id": asset_id, "cash": {"code": "EUR", "amount": "-200"}},
                    ]
                },
            )

            assert resp["committed"] is False
            issues = resp.get("issues", [])
            assert len(issues) > 0
            assert any("balanceCash" in (i.get("code") or "") for i in issues)
            print_success("Same-day net negative (-100) → correctly rejected")

    # ------------------------------------------------------------------
    # Test 4: Multi-day cumulative → fail on day 3
    # ------------------------------------------------------------------
    async def test_multi_day_cumulative(self):
        print_section("Balance Walk: multi-day cumulative → fail day 3")
        async with httpx.AsyncClient() as client:
            broker_id, asset_id = await _setup(client)
            d1 = str(date.today() - timedelta(days=10))
            d2 = str(date.today() - timedelta(days=5))
            d3 = str(date.today())

            resp = await _commit(
                client,
                {
                    "creates": [
                        {"broker_id": broker_id, "type": "DEPOSIT", "date": d1, "quantity": "0", "cash": {"code": "EUR", "amount": "1000"}},
                        {"broker_id": broker_id, "type": "BUY", "date": d2, "quantity": "5", "asset_id": asset_id, "cash": {"code": "EUR", "amount": "-500"}},
                        {"broker_id": broker_id, "type": "BUY", "date": d3, "quantity": "6", "asset_id": asset_id, "cash": {"code": "EUR", "amount": "-600"}},
                    ]
                },
            )

            assert resp["committed"] is False
            issues = resp.get("issues", [])
            assert any("balanceCash" in (i.get("code") or "") for i in issues)
            print_success("Multi-day: 1000 - 500 - 600 = -100 on day 3 → correctly rejected")

    # ------------------------------------------------------------------
    # Test 5: Edit move deposit date → cascading failure
    # ------------------------------------------------------------------
    async def test_edit_move_deposit_date_cascade(self):
        print_section("Balance Walk: move deposit to later date → cascade fail")
        async with httpx.AsyncClient() as client:
            broker_id, asset_id = await _setup(client)
            d1 = str(date.today() - timedelta(days=10))
            d2 = str(date.today() - timedelta(days=5))
            d3 = str(date.today())

            # First commit: DEPOSIT day1, BUY day2 → OK
            resp = await _commit(
                client,
                {
                    "creates": [
                        {"broker_id": broker_id, "type": "DEPOSIT", "date": d1, "quantity": "0", "cash": {"code": "EUR", "amount": "1000"}},
                        {"broker_id": broker_id, "type": "BUY", "date": d2, "quantity": "5", "asset_id": asset_id, "cash": {"code": "EUR", "amount": "-500"}},
                    ]
                },
            )
            assert resp["committed"] is True

            deposit_id = resp["results"][0]["id"]

            # Now move deposit to day3 (AFTER the BUY) → BUY on day2 has no cash
            resp2 = await _commit(
                client,
                {
                    "updates": [
                        {"id": deposit_id, "date": d3},
                    ]
                },
            )

            assert resp2["committed"] is False
            issues = resp2.get("issues", [])
            assert any("balanceCash" in (i.get("code") or "") for i in issues)
            print_success("Move deposit after BUY → cascade fail on BUY date")

    # ------------------------------------------------------------------
    # Test 6: Delete deposit → downstream BUY becomes invalid
    # ------------------------------------------------------------------
    async def test_delete_deposit_cascades(self):
        print_section("Balance Walk: delete deposit → downstream BUY invalid")
        async with httpx.AsyncClient() as client:
            broker_id, asset_id = await _setup(client)
            d1 = str(date.today() - timedelta(days=10))
            d2 = str(date.today() - timedelta(days=5))

            resp = await _commit(
                client,
                {
                    "creates": [
                        {"broker_id": broker_id, "type": "DEPOSIT", "date": d1, "quantity": "0", "cash": {"code": "EUR", "amount": "1000"}},
                        {"broker_id": broker_id, "type": "BUY", "date": d2, "quantity": "5", "asset_id": asset_id, "cash": {"code": "EUR", "amount": "-500"}},
                    ]
                },
            )
            assert resp["committed"] is True
            deposit_id = resp["results"][0]["id"]

            # Delete deposit → BUY on day2 has no cash
            resp2 = await _commit(client, {"deletes": [deposit_id]})
            assert resp2["committed"] is False
            issues = resp2.get("issues", [])
            assert any("balanceCash" in (i.get("code") or "") for i in issues)
            print_success("Delete deposit → downstream BUY correctly rejected")

    # ------------------------------------------------------------------
    # Test 7: Same-day multiple compensating ops → pass
    # ------------------------------------------------------------------
    async def test_same_day_multi_ops_compensating(self):
        print_section("Balance Walk: same-day multi ops compensating → pass")
        async with httpx.AsyncClient() as client:
            broker_id, asset_id = await _setup(client)
            today = str(date.today())

            resp = await _commit(
                client,
                {
                    "creates": [
                        {"broker_id": broker_id, "type": "DEPOSIT", "date": today, "quantity": "0", "cash": {"code": "EUR", "amount": "500"}},
                        {"broker_id": broker_id, "type": "BUY", "date": today, "quantity": "3", "asset_id": asset_id, "cash": {"code": "EUR", "amount": "-300"}},
                        {"broker_id": broker_id, "type": "SELL", "date": today, "quantity": "-2", "asset_id": asset_id, "cash": {"code": "EUR", "amount": "200"}},
                        {"broker_id": broker_id, "type": "WITHDRAWAL", "date": today, "quantity": "0", "cash": {"code": "EUR", "amount": "-400"}},
                    ]
                },
            )

            # Net cash: +500 -300 +200 -400 = 0 (OK)
            # Net asset: +3 -2 = 1 (OK)
            assert resp["committed"] is True, f"Expected pass (net=0), got {resp}"
            print_success("4 compensating ops same day → committed OK (net cash=0, net asset=1)")

    # ------------------------------------------------------------------
    # Test 8: Validate single row vs batch — context matters
    # ------------------------------------------------------------------
    async def test_validate_single_row_vs_batch(self):
        print_section("Balance Walk: validate single row vs batch → context matters")
        async with httpx.AsyncClient() as client:
            broker_id, asset_id = await _setup(client)
            today = str(date.today())

            buy_row = {"broker_id": broker_id, "type": "BUY", "date": today, "quantity": "5", "asset_id": asset_id, "cash": {"code": "EUR", "amount": "-500"}}
            deposit_row = {"broker_id": broker_id, "type": "DEPOSIT", "date": today, "quantity": "0", "cash": {"code": "EUR", "amount": "1000"}}

            # Single BUY alone → should fail (no cash)
            resp_single = await _validate(client, {"creates": [buy_row]})
            assert resp_single["committed"] is False
            issues_single = resp_single.get("issues", [])
            assert any("balanceCash" in (i.get("code") or "") for i in issues_single), f"Single BUY should fail: {resp_single}"

            # BUY + DEPOSIT together → should pass
            resp_batch = await _validate(client, {"creates": [buy_row, deposit_row]})
            assert len(resp_batch.get("issues", [])) == 0, f"Batch should pass: {resp_batch}"

            print_success("Single BUY → fail. BUY+DEPOSIT batch → pass. Context matters!")

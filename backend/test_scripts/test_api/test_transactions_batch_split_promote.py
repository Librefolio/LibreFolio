"""
Tests for batch split, promote, and promote-suggest in the unified pipeline.

Covers:
- B1: Split via batch pipeline (commit with splits[])
- B2: Promote via batch pipeline (commit with promotes[])
- B3: Promote-suggest endpoint (POST /transactions/promote-suggest)

Reference: plan-phase07-transaction-Part4_Round6_PlanD1_BackendBatchSuggest.prompt.md
"""

import uuid
from datetime import date, timedelta
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
    return f"sp_test_{int(date.today().toordinal())}_{uuid.uuid4().hex[:8]}"


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


async def get_or_create_asset(client: httpx.AsyncClient, name: str = "SplitPromoteTestAsset") -> int:
    """Create an asset for testing and return its ID."""
    unique_name = f"{name}_{uuid.uuid4().hex[:6]}"
    resp = await client.post(
        f"{API_BASE}/assets",
        json=[{"display_name": unique_name, "currency": "USD", "asset_type": "STOCK"}],
        timeout=TIMEOUT,
    )
    assert resp.status_code in (200, 201), f"Create asset failed: {resp.text}"
    return resp.json()["results"][0]["asset_id"]


async def create_transfer_pair(client: httpx.AsyncClient, broker_a_id: int, broker_b_id: int, asset_id: int, qty: str = "5") -> list[int]:
    """Create a TRANSFER pair and return both TX IDs.
    First creates a BUY on broker_a to ensure positive balance.
    """
    # First BUY enough asset on broker_a
    buy_resp = await client.post(
        f"{API_BASE}/transactions/commit",
        json={
            "creates": [
                {
                    "broker_id": broker_a_id,
                    "asset_id": asset_id,
                    "type": "BUY",
                    "date": "2026-01-01",
                    "quantity": str(int(qty) * 2),
                    "cash": {"code": "USD", "amount": str(-int(qty) * 100)},
                },
            ],
        },
        timeout=TIMEOUT,
    )
    assert buy_resp.status_code == 200, f"Buy setup failed: {buy_resp.text}"
    assert buy_resp.json()["committed"] is True, f"Buy not committed: {buy_resp.json()}"

    link_uuid = str(uuid.uuid4())
    resp = await client.post(
        f"{API_BASE}/transactions/commit",
        json={
            "creates": [
                {
                    "broker_id": broker_a_id,
                    "asset_id": asset_id,
                    "type": "TRANSFER",
                    "date": "2026-01-15",
                    "quantity": f"-{qty}",
                    "link_uuid": link_uuid,
                },
                {
                    "broker_id": broker_b_id,
                    "asset_id": asset_id,
                    "type": "TRANSFER",
                    "date": "2026-01-15",
                    "quantity": qty,
                    "link_uuid": link_uuid,
                },
            ],
        },
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, f"Create pair failed: {resp.text}"
    data = resp.json()
    assert data["committed"] is True, f"Pair not committed: {data}"
    return [r["ids"][0] for r in data["results"] if r["operation"] == "create"]


async def create_cash_transfer_pair(client: httpx.AsyncClient, broker_a_id: int, broker_b_id: int, amount: str = "1000", currency: str = "EUR") -> list[int]:
    """Create a CASH_TRANSFER pair and return both TX IDs."""
    link_uuid = str(uuid.uuid4())
    resp = await client.post(
        f"{API_BASE}/transactions/commit",
        json={
            "creates": [
                {
                    "broker_id": broker_a_id,
                    "type": "CASH_TRANSFER",
                    "date": "2026-01-20",
                    "quantity": "0",
                    "cash": {"code": currency, "amount": f"-{amount}"},
                    "link_uuid": link_uuid,
                },
                {
                    "broker_id": broker_b_id,
                    "type": "CASH_TRANSFER",
                    "date": "2026-01-20",
                    "quantity": "0",
                    "cash": {"code": currency, "amount": amount},
                    "link_uuid": link_uuid,
                },
            ],
        },
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, f"Create cash pair failed: {resp.text}"
    data = resp.json()
    assert data["committed"] is True, f"Cash pair not committed: {data}"
    return [r["ids"][0] for r in data["results"] if r["operation"] == "create"]


async def create_standalone_tx(
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

    resp = await client.post(
        f"{API_BASE}/transactions/commit",
        json={"creates": [create_dict]},
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, f"Create standalone failed: {resp.text}"
    data = resp.json()
    assert data["committed"] is True, f"Standalone not committed: {data}"
    return data["results"][0]["ids"][0]


# ============================================================================
# B1 — SPLIT VIA BATCH PIPELINE
# ============================================================================


@pytest.fixture(scope="module")
def test_server():
    """Start test server once for all tests in this module."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


@pytest.mark.asyncio
class TestBatchSplit:
    @pytest.fixture(autouse=True)
    def server(self, test_server):
        yield

    async def test_commit_with_split_transfer(self):
        """Split a TRANSFER pair via batch pipeline → both become ADJUSTMENT standalone."""
        print_section("B1.1 — Split TRANSFER pair via batch")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_a = await create_broker(client, "SplitA1")
            broker_b = await create_broker(client, "SplitB1")
            asset_id = await get_or_create_asset(client)

            tx_ids = await create_transfer_pair(client, broker_a, broker_b, asset_id)
            assert len(tx_ids) == 2

            # Split via commit
            resp = await client.post(
                f"{API_BASE}/transactions/commit",
                json={"splits": [{"id_a": tx_ids[0], "id_b": tx_ids[1]}]},
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["committed"] is True
            split_results = [r for r in data["results"] if r["operation"] == "split"]
            assert len(split_results) == 1

            # Verify both TXs are now ADJUSTMENT standalone
            resp2 = await client.get(
                f"{API_BASE}/transactions",
                params={"ids": tx_ids},
                timeout=TIMEOUT,
            )
            assert resp2.status_code == 200
            txs = resp2.json()
            for tx in txs:
                assert tx["type"] == "ADJUSTMENT", f"Expected ADJUSTMENT, got {tx['type']}"
                assert tx["related_transaction_id"] is None
            print_success("TRANSFER split → 2 ADJUSTMENT standalone ✓")

    async def test_commit_with_split_cash_transfer(self):
        """Split a CASH_TRANSFER pair → WITHDRAWAL + DEPOSIT standalone, asset_id=null."""
        print_section("B1.2 — Split CASH_TRANSFER pair via batch")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_a = await create_broker(client, "SplitCashA")
            broker_b = await create_broker(client, "SplitCashB")

            tx_ids = await create_cash_transfer_pair(client, broker_a, broker_b)
            assert len(tx_ids) == 2

            resp = await client.post(
                f"{API_BASE}/transactions/commit",
                json={"splits": [{"id_a": tx_ids[0], "id_b": tx_ids[1]}]},
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["committed"] is True

            resp2 = await client.get(
                f"{API_BASE}/transactions",
                params={"ids": tx_ids},
                timeout=TIMEOUT,
            )
            txs = resp2.json()
            types = sorted(tx["type"] for tx in txs)
            assert types == ["DEPOSIT", "WITHDRAWAL"], f"Expected DEPOSIT+WITHDRAWAL, got {types}"
            for tx in txs:
                assert tx["related_transaction_id"] is None
                assert tx["asset_id"] is None
            print_success("CASH_TRANSFER split → WITHDRAWAL + DEPOSIT standalone ✓")

    async def test_validate_split_not_found(self):
        """Split with non-existent ID → issue with code txNotFound."""
        print_section("B1.3 — Split not found")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)

            resp = await client.post(
                f"{API_BASE}/transactions/commit",
                json={"splits": [{"id_a": 999999, "id_b": 999998}]},
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["committed"] is False
            assert any(i["code"] == "txNotFound" for i in data["issues"]), f"Expected txNotFound issue: {data['issues']}"
            print_success("Split not found → txNotFound issue ✓")

    async def test_split_standalone_fails(self):
        """Split two standalone TXs (not a pair) → issue with code splitIdsMismatch."""
        print_section("B1.4 — Split standalone fails")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker = await create_broker(client, "SplitStandalone")

            tx_id_a = await create_standalone_tx(
                client,
                broker,
                "DEPOSIT",
                cash={"code": "EUR", "amount": "100"},
            )
            tx_id_b = await create_standalone_tx(
                client,
                broker,
                "DEPOSIT",
                cash={"code": "EUR", "amount": "200"},
            )

            resp = await client.post(
                f"{API_BASE}/transactions/commit",
                json={"splits": [{"id_a": tx_id_a, "id_b": tx_id_b}]},
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["committed"] is False
            assert any(i["code"] == "splitIdsMismatch" for i in data["issues"]), f"Expected splitIdsMismatch: {data['issues']}"
            print_success("Split standalone → splitIdsMismatch issue ✓")

    async def test_split_in_mixed_batch(self):
        """Creates + updates + splits in the same commit batch."""
        print_section("B1.5 — Mixed batch with split")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_a = await create_broker(client, "MixA")
            broker_b = await create_broker(client, "MixB")
            asset_id = await get_or_create_asset(client)

            # Create a TRANSFER pair first
            tx_ids = await create_transfer_pair(client, broker_a, broker_b, asset_id)

            # Now commit with a create + a split in the same batch
            resp = await client.post(
                f"{API_BASE}/transactions/commit",
                json={
                    "creates": [
                        {
                            "broker_id": broker_a,
                            "type": "DEPOSIT",
                            "date": "2026-03-01",
                            "quantity": "0",
                            "cash": {"code": "EUR", "amount": "500"},
                        }
                    ],
                    "splits": [{"id_a": tx_ids[0], "id_b": tx_ids[1]}],
                },
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["committed"] is True

            # Verify: 1 create + 1 split
            create_results = [r for r in data["results"] if r["operation"] == "create"]
            split_results = [r for r in data["results"] if r["operation"] == "split"]
            assert len(create_results) == 1
            assert len(split_results) == 1
            print_success("Mixed batch (create + split) committed ✓")


# ============================================================================
# B2 — PROMOTE VIA BATCH PIPELINE
# ============================================================================


@pytest.mark.asyncio
class TestBatchPromote:
    @pytest.fixture(autouse=True)
    def server(self, test_server):
        yield

    async def test_commit_promote_saved_saved(self):
        """Promote 2 saved standalone WITHDRAWAL+DEPOSIT → CASH_TRANSFER pair."""
        print_section("B2.1 — Promote saved+saved → CASH_TRANSFER")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_a = await create_broker(client, "PromSavedA")
            broker_b = await create_broker(client, "PromSavedB")

            w_id = await create_standalone_tx(
                client,
                broker_a,
                "WITHDRAWAL",
                cash={"code": "EUR", "amount": "-800"},
            )
            d_id = await create_standalone_tx(
                client,
                broker_b,
                "DEPOSIT",
                cash={"code": "EUR", "amount": "800"},
            )

            resp = await client.post(
                f"{API_BASE}/transactions/commit",
                json={"promotes": [{"id_a": w_id, "id_b": d_id}]},
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["committed"] is True, f"Promote not committed: {data}"
            assert data["issues"] == []

            # Verify both are CASH_TRANSFER with bidirectional link
            resp2 = await client.get(
                f"{API_BASE}/transactions",
                params={"ids": [w_id, d_id]},
                timeout=TIMEOUT,
            )
            txs = resp2.json()
            assert all(tx["type"] == "CASH_TRANSFER" for tx in txs)
            assert txs[0]["related_transaction_id"] == txs[1]["id"]
            assert txs[1]["related_transaction_id"] == txs[0]["id"]
            print_success("Promote saved+saved → CASH_TRANSFER pair ✓")

    async def test_commit_promote_new_new(self):
        """Promote 2 new creates via link_uuid in the same batch → TRANSFER pair."""
        print_section("B2.2 — Promote new+new via link_uuid → TRANSFER")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_a = await create_broker(client, "PromNewA")
            broker_b = await create_broker(client, "PromNewB")
            asset_id = await get_or_create_asset(client)

            # First BUY to have positive balance
            buy_resp = await client.post(
                f"{API_BASE}/transactions/commit",
                json={
                    "creates": [
                        {
                            "broker_id": broker_a,
                            "asset_id": asset_id,
                            "type": "BUY",
                            "date": "2026-01-01",
                            "quantity": "10",
                            "cash": {"code": "USD", "amount": "-500"},
                        },
                    ],
                },
                timeout=TIMEOUT,
            )
            assert buy_resp.json()["committed"] is True

            uuid_a = str(uuid.uuid4())
            uuid_b = str(uuid.uuid4())

            resp = await client.post(
                f"{API_BASE}/transactions/commit",
                json={
                    "creates": [
                        {
                            "broker_id": broker_a,
                            "asset_id": asset_id,
                            "type": "ADJUSTMENT",
                            "date": "2026-02-10",
                            "quantity": "-3",
                            "link_uuid": uuid_a,
                        },
                        {
                            "broker_id": broker_b,
                            "asset_id": asset_id,
                            "type": "ADJUSTMENT",
                            "date": "2026-02-10",
                            "quantity": "3",
                            "link_uuid": uuid_b,
                        },
                    ],
                    "promotes": [{"link_uuid_a": uuid_a, "link_uuid_b": uuid_b}],
                },
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["committed"] is True, f"Promote new+new not committed: {data}"

            # No issues (link_uuid not re-processed in Step 6)
            assert data["issues"] == [], f"Unexpected issues: {data['issues']}"

            # Verify: both are TRANSFER with bidirectional link
            create_results = [r for r in data["results"] if r["operation"] == "create"]
            tx_ids = [r["ids"][0] for r in create_results]
            assert len(tx_ids) == 2

            resp2 = await client.get(
                f"{API_BASE}/transactions",
                params={"ids": tx_ids},
                timeout=TIMEOUT,
            )
            txs = resp2.json()
            assert all(tx["type"] == "TRANSFER" for tx in txs), f"Expected TRANSFER, got {[tx['type'] for tx in txs]}"
            assert txs[0]["related_transaction_id"] == txs[1]["id"]
            assert txs[1]["related_transaction_id"] == txs[0]["id"]
            print_success("Promote new+new → TRANSFER pair, no Step 6 re-processing ✓")

    async def test_commit_promote_saved_new(self):
        """Promote 1 saved WITHDRAWAL + 1 new DEPOSIT → CASH_TRANSFER pair."""
        print_section("B2.3 — Promote saved+new → CASH_TRANSFER")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_a = await create_broker(client, "PromSvdNewA")
            broker_b = await create_broker(client, "PromSvdNewB")

            # Create saved WITHDRAWAL
            w_id = await create_standalone_tx(
                client,
                broker_a,
                "WITHDRAWAL",
                cash={"code": "EUR", "amount": "-300"},
                tx_date="2026-03-01",
            )

            # Promote with a new DEPOSIT via link_uuid
            new_uuid = str(uuid.uuid4())
            resp = await client.post(
                f"{API_BASE}/transactions/commit",
                json={
                    "creates": [
                        {
                            "broker_id": broker_b,
                            "type": "DEPOSIT",
                            "date": "2026-03-01",
                            "quantity": "0",
                            "cash": {"code": "EUR", "amount": "300"},
                            "link_uuid": new_uuid,
                        },
                    ],
                    "promotes": [{"id_a": w_id, "link_uuid_b": new_uuid}],
                },
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["committed"] is True, f"Promote saved+new not committed: {data}"
            assert data["issues"] == []

            # Get the new deposit ID
            create_results = [r for r in data["results"] if r["operation"] == "create"]
            new_d_id = create_results[0]["ids"][0]

            # Verify both are CASH_TRANSFER with bidirectional link
            resp2 = await client.get(
                f"{API_BASE}/transactions",
                params={"ids": [w_id, new_d_id]},
                timeout=TIMEOUT,
            )
            txs = resp2.json()
            assert all(tx["type"] == "CASH_TRANSFER" for tx in txs)
            assert txs[0]["related_transaction_id"] == txs[1]["id"]
            assert txs[1]["related_transaction_id"] == txs[0]["id"]
            print_success("Promote saved+new → CASH_TRANSFER pair ✓")

    async def test_validate_promote_incompatible(self):
        """BUY + SELL → no promote rule → noPromoteRule issue."""
        print_section("B2.4 — Promote incompatible types")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker = await create_broker(client, "PromIncompat")
            asset_id = await get_or_create_asset(client)

            buy_id = await create_standalone_tx(
                client,
                broker,
                "BUY",
                asset_id=asset_id,
                quantity="10",
                cash={"code": "USD", "amount": "-500"},
            )
            sell_id = await create_standalone_tx(
                client,
                broker,
                "SELL",
                asset_id=asset_id,
                quantity="-5",
                cash={"code": "USD", "amount": "250"},
            )

            resp = await client.post(
                f"{API_BASE}/transactions/commit",
                json={"promotes": [{"id_a": buy_id, "id_b": sell_id}]},
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["committed"] is False
            assert any(i["code"] == "noPromoteRule" for i in data["issues"]), f"Expected noPromoteRule: {data['issues']}"
            print_success("Promote incompatible types → noPromoteRule ✓")

    async def test_validate_promote_already_paired(self):
        """TX with related_transaction_id → promote → alreadyPaired issue."""
        print_section("B2.5 — Promote already-paired TX")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_a = await create_broker(client, "PromPairedA")
            broker_b = await create_broker(client, "PromPairedB")
            asset_id = await get_or_create_asset(client)

            # Create a TRANSFER pair (already linked)
            tx_ids = await create_transfer_pair(client, broker_a, broker_b, asset_id)

            # Try to promote one of the paired TXs with a new standalone
            standalone_id = await create_standalone_tx(
                client,
                broker_a,
                "ADJUSTMENT",
                asset_id=asset_id,
                quantity="1",
            )

            resp = await client.post(
                f"{API_BASE}/transactions/commit",
                json={"promotes": [{"id_a": tx_ids[0], "id_b": standalone_id}]},
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["committed"] is False
            assert any(i["code"] == "alreadyPaired" for i in data["issues"]), f"Expected alreadyPaired: {data['issues']}"
            print_success("Promote already-paired → alreadyPaired issue ✓")

    async def test_promote_resolved_fields(self):
        """resolved_fields: {description, tags} → both TXs get same values."""
        print_section("B2.6 — Promote with resolved_fields")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_a = await create_broker(client, "PromResA")
            broker_b = await create_broker(client, "PromResB")

            w_id = await create_standalone_tx(
                client,
                broker_a,
                "WITHDRAWAL",
                cash={"code": "EUR", "amount": "-200"},
            )
            d_id = await create_standalone_tx(
                client,
                broker_b,
                "DEPOSIT",
                cash={"code": "EUR", "amount": "200"},
            )

            resp = await client.post(
                f"{API_BASE}/transactions/commit",
                json={
                    "promotes": [
                        {
                            "id_a": w_id,
                            "id_b": d_id,
                            "resolved_fields": {
                                "description": "Merged transfer description",
                                "tags": ["alpha", "beta"],
                            },
                        }
                    ],
                },
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["committed"] is True, f"Not committed: {data}"

            resp2 = await client.get(
                f"{API_BASE}/transactions",
                params={"ids": [w_id, d_id]},
                timeout=TIMEOUT,
            )
            txs = resp2.json()
            for tx in txs:
                assert tx["description"] == "Merged transfer description"
                assert sorted(tx["tags"]) == ["alpha", "beta"]
            print_success("Promote resolved_fields applied to both TXs ✓")

    async def test_promote_constraint_fail(self):
        """Same broker for CASH_TRANSFER (violates broker_id: different) → noPromoteRule."""
        print_section("B2.7 — Promote constraint fail (same broker)")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker = await create_broker(client, "PromSameBroker")

            w_id = await create_standalone_tx(
                client,
                broker,
                "WITHDRAWAL",
                cash={"code": "EUR", "amount": "-100"},
            )
            d_id = await create_standalone_tx(
                client,
                broker,
                "DEPOSIT",
                cash={"code": "EUR", "amount": "100"},
            )

            resp = await client.post(
                f"{API_BASE}/transactions/commit",
                json={"promotes": [{"id_a": w_id, "id_b": d_id}]},
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200
            data = resp.json()
            # Same broker for both deposit/withdrawal won't match CASH_TRANSFER (requires different)
            # nor FX_CONVERSION (requires same but different currency)
            assert data["committed"] is False
            assert any(i["code"] == "noPromoteRule" for i in data["issues"]), f"Expected noPromoteRule: {data['issues']}"
            print_success("Promote same-broker W+D → noPromoteRule ✓")


# ============================================================================
# B3 — PROMOTE-SUGGEST
# ============================================================================


@pytest.mark.asyncio
class TestPromoteSuggest:
    @pytest.fixture(autouse=True)
    def server(self, test_server):
        yield

    async def test_suggest_finds_cash_transfer_candidate(self):
        """Input DEPOSIT EUR → finds WITHDRAWAL EUR in different broker."""
        print_section("B3.1 — Suggest finds CASH_TRANSFER candidate")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_a = await create_broker(client, "SuggestA")
            broker_b = await create_broker(client, "SuggestB")

            # Create a standalone WITHDRAWAL
            w_id = await create_standalone_tx(
                client,
                broker_a,
                "WITHDRAWAL",
                cash={"code": "EUR", "amount": "-600"},
                tx_date="2026-04-01",
            )

            # Suggest for a DEPOSIT
            resp = await client.post(
                f"{API_BASE}/transactions/promote-suggest",
                params={"tolerance_days": 7},
                json=[
                    {
                        "id": -1,
                        "type": "DEPOSIT",
                        "broker_id": broker_b,
                        "date": "2026-04-01",
                        "currency": "EUR",
                        "amount": "600",
                    }
                ],
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200
            data = resp.json()
            candidates = data["results"].get("-1", [])
            assert len(candidates) >= 1, f"Expected ≥1 candidate, got {candidates}"
            assert any(c["id"] == w_id for c in candidates), f"Expected w_id={w_id} in candidates: {candidates}"
            print_success("Suggest finds CASH_TRANSFER candidate ✓")

    async def test_suggest_respects_tolerance(self):
        """tolerance_days=1, TX at 30 days distance → no candidates."""
        print_section("B3.2 — Suggest respects tolerance")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_a = await create_broker(client, "SugTolA")
            broker_b = await create_broker(client, "SugTolB")

            # Create WITHDRAWAL 30 days ago
            await create_standalone_tx(
                client,
                broker_a,
                "WITHDRAWAL",
                cash={"code": "EUR", "amount": "-100"},
                tx_date="2026-01-01",
            )

            resp = await client.post(
                f"{API_BASE}/transactions/promote-suggest",
                params={"tolerance_days": 1},
                json=[
                    {
                        "id": -1,
                        "type": "DEPOSIT",
                        "broker_id": broker_b,
                        "date": "2026-02-01",
                        "currency": "EUR",
                        "amount": "100",
                    }
                ],
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200
            data = resp.json()
            candidates = data["results"].get("-1", [])
            assert len(candidates) == 0, f"Expected 0 candidates, got {candidates}"
            print_success("Suggest respects tolerance → empty results ✓")

    async def test_suggest_excludes_paired(self):
        """TX with related_transaction_id → not in results."""
        print_section("B3.3 — Suggest excludes paired TX")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_a = await create_broker(client, "SugPairedA")
            broker_b = await create_broker(client, "SugPairedB")

            # Create a CASH_TRANSFER pair (both linked)
            tx_ids = await create_cash_transfer_pair(client, broker_a, broker_b, amount="400", currency="EUR")

            # Look for a DEPOSIT candidate — the paired one should NOT appear
            resp = await client.post(
                f"{API_BASE}/transactions/promote-suggest",
                params={"tolerance_days": 30},
                json=[
                    {
                        "id": -1,
                        "type": "WITHDRAWAL",
                        "broker_id": broker_a,
                        "date": "2026-01-20",
                        "currency": "EUR",
                        "amount": "-400",
                    }
                ],
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200
            data = resp.json()
            candidates = data["results"].get("-1", [])
            paired_ids = set(tx_ids)
            for c in candidates:
                assert c["id"] not in paired_ids, f"Paired TX {c['id']} should be excluded"
            print_success("Suggest excludes paired TX ✓")

    async def test_suggest_excludes_self(self):
        """Input id=X (>0), DB has TX with id=X → X not in candidates."""
        print_section("B3.4 — Suggest excludes self")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_a = await create_broker(client, "SugSelfA")
            broker_b = await create_broker(client, "SugSelfB")

            # Create standalone WITHDRAWAL
            w_id = await create_standalone_tx(
                client,
                broker_a,
                "WITHDRAWAL",
                cash={"code": "EUR", "amount": "-100"},
                tx_date="2026-04-15",
            )

            # Suggest with the same ID — should NOT find itself
            resp = await client.post(
                f"{API_BASE}/transactions/promote-suggest",
                params={"tolerance_days": 7},
                json=[
                    {
                        "id": w_id,
                        "type": "DEPOSIT",
                        "broker_id": broker_b,
                        "date": "2026-04-15",
                        "currency": "EUR",
                        "amount": "100",
                    }
                ],
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200
            data = resp.json()
            key = str(w_id)
            candidates = data["results"].get(key, [])
            assert not any(c["id"] == w_id for c in candidates), f"Self-match found: {candidates}"
            print_success("Suggest excludes self ✓")

    async def test_suggest_multiple_inputs(self):
        """3 items bulk → Dict with 3 keys."""
        print_section("B3.5 — Suggest multiple inputs")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_a = await create_broker(client, "SugMultiA")
            broker_b = await create_broker(client, "SugMultiB")

            resp = await client.post(
                f"{API_BASE}/transactions/promote-suggest",
                params={"tolerance_days": 7},
                json=[
                    {"id": -1, "type": "DEPOSIT", "broker_id": broker_a, "date": "2026-04-01", "currency": "EUR", "amount": "100"},
                    {"id": -2, "type": "WITHDRAWAL", "broker_id": broker_b, "date": "2026-04-01", "currency": "EUR", "amount": "-100"},
                    {"id": -3, "type": "ADJUSTMENT", "broker_id": broker_a, "date": "2026-04-01", "quantity": "5"},
                ],
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["results"]) == 3, f"Expected 3 keys, got {len(data['results'])}"
            assert "-1" in data["results"]
            assert "-2" in data["results"]
            assert "-3" in data["results"]
            print_success("Suggest multiple inputs → 3 keys ✓")

    async def test_suggest_fake_id(self):
        """id=-1 (unsaved) → results keyed by -1."""
        print_section("B3.6 — Suggest fake ID")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker = await create_broker(client, "SugFake")

            resp = await client.post(
                f"{API_BASE}/transactions/promote-suggest",
                params={"tolerance_days": 7},
                json=[
                    {
                        "id": -1,
                        "type": "DEPOSIT",
                        "broker_id": broker,
                        "date": "2026-05-01",
                        "currency": "USD",
                        "amount": "50",
                    }
                ],
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "-1" in data["results"], f"Expected key '-1' in results: {data['results'].keys()}"
            print_success("Suggest fake ID → keyed by -1 ✓")

"""
Tests for batch split, promote, and promote-suggest in the unified pipeline.

Covers:
- B1: Split via batch pipeline (commit with splits[])
- B2: Promote via batch pipeline (commit with promotes[])
- B3: Promote-suggest endpoint (POST /transactions/promote-suggest)
- B4: Edits of rows an older version stored without a cost basis (N2)

Reference: plan-phase07-transaction-Part4_Round6_PlanD1_BackendBatchSuggest.prompt.md
"""

import contextlib
import io
import json
import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

import httpx
import pytest

import backend.app.api.v1.transactions as transactions_api
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
                    "cost_basis_mode": "auto",
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
    cost_basis_override: Optional[dict] = None,
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
    # Auto-add cost_basis for types that require it
    if tx_type in ("TRANSFER", "ADJUSTMENT") and not quantity.startswith("-") and float(quantity) > 0:
        create_dict["cost_basis_override"] = cost_basis_override or {"code": "USD", "amount": "50"}

    resp = await client.post(
        f"{API_BASE}/transactions/commit",
        json={"creates": [create_dict]},
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, f"Create standalone failed: {resp.text}"
    data = resp.json()
    assert data["committed"] is True, f"Standalone not committed: {data}"
    return data["results"][0]["ids"][0]


async def create_split_event(client: httpx.AsyncClient, asset_id: int, event_date: str, ratio: str, currency: str = "USD") -> int:
    """Create a manual SPLIT AssetEvent (value = ratio, e.g. "2" for 2:1) and return its id.

    Same approach as ``create_split_event`` in test_portfolio_wac.py: upsert the manual event,
    then read it back by asset and date to learn its id.
    """
    resp = await client.post(
        f"{API_BASE}/assets/events",
        json=[{"asset_id": asset_id, "events": [{"date": event_date, "type": "SPLIT", "value": {"code": currency, "amount": ratio}}]}],
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, f"Event upsert failed: {resp.status_code}: {resp.text}"
    query_resp = await client.post(
        f"{API_BASE}/assets/events/query",
        json=[{"asset_id": asset_id, "date_range": {"start": event_date, "end": event_date}}],
        timeout=TIMEOUT,
    )
    assert query_resp.status_code == 200, f"Event query failed: {query_resp.status_code}: {query_resp.text}"
    split_events = [event for item in query_resp.json()["items"] if item["asset_id"] == asset_id for event in item["events"] if event["type"] == "SPLIT"]
    assert len(split_events) == 1, f"Expected 1 SPLIT event on asset {asset_id} at {event_date}, got {query_resp.json()}"
    return split_events[0]["id"]


async def describe_transactions(client: httpx.AsyncClient, tx_ids: list[int]) -> str:
    """Read the rows back by id and render the fields a pair check looks at, for a failure message."""
    resp = await client.get(
        f"{API_BASE}/transactions",
        params={"ids": tx_ids},
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, f"Read back of {tx_ids} failed: {resp.text}"
    by_id = {tx["id"]: tx for tx in resp.json()}
    rendered = []
    for tx_id in tx_ids:
        tx = by_id.get(tx_id)
        if tx is None:
            rendered.append(f"id={tx_id} not found")
            continue
        rendered.append(f"id={tx_id} broker_id={tx['broker_id']} type={tx['type']} quantity={tx['quantity']} asset_id={tx['asset_id']} asset_event_id={tx['asset_event_id']} related_transaction_id={tx['related_transaction_id']} cost_basis_override={tx['cost_basis_override']}")
    return "; ".join(rendered)


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

    @pytest.mark.parametrize(
        "reverse_ids",
        [False, True],
        ids=["source-as-id-a", "destination-as-id-a"],
    )
    async def test_commit_with_split_cash_transfer(self, reverse_ids):
        """Split a CASH_TRANSFER pair → WITHDRAWAL + DEPOSIT standalone, asset_id=null."""
        print_section("B1.2 — Split CASH_TRANSFER pair via batch")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_a = await create_broker(client, "SplitCashA")
            broker_b = await create_broker(client, "SplitCashB")

            tx_ids = await create_cash_transfer_pair(client, broker_a, broker_b)
            assert len(tx_ids) == 2
            source_id, destination_id = tx_ids
            id_a, id_b = (destination_id, source_id) if reverse_ids else (source_id, destination_id)

            resp = await client.post(
                f"{API_BASE}/transactions/commit",
                json={"splits": [{"id_a": id_a, "id_b": id_b}]},
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["committed"] is True
            split_results = [result for result in data["results"] if result["operation"] == "split"]
            assert len(split_results) == 1
            assert split_results[0]["ids"] == [source_id, destination_id]

            resp2 = await client.get(
                f"{API_BASE}/transactions",
                params={"ids": tx_ids},
                timeout=TIMEOUT,
            )
            txs = resp2.json()
            by_id = {tx["id"]: tx for tx in txs}
            assert set(by_id) == {source_id, destination_id}
            assert by_id[source_id]["type"] == "WITHDRAWAL"
            assert Decimal(by_id[source_id]["cash"]["amount"]) == Decimal("-1000")
            assert by_id[destination_id]["type"] == "DEPOSIT"
            assert Decimal(by_id[destination_id]["cash"]["amount"]) == Decimal("1000")
            assert all(tx["related_transaction_id"] is None for tx in by_id.values())
            assert all(tx["asset_id"] is None for tx in by_id.values())
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
        """Split runs before updates whose type swaps only become valid post-split."""
        print_section("B1.5 — Split precedes dependent updates")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_a = await create_broker(client, "MixA")
            broker_b = await create_broker(client, "MixB")
            source_id, destination_id = await create_cash_transfer_pair(
                client,
                broker_a,
                broker_b,
            )
            source_description = f"post-split-source-{uuid.uuid4().hex}"
            destination_description = f"post-split-destination-{uuid.uuid4().hex}"

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
                    "updates": [
                        {
                            "id": source_id,
                            "type": "DEPOSIT",
                            "cash": {"code": "EUR", "amount": "125"},
                            "description": source_description,
                        },
                        {
                            "id": destination_id,
                            "type": "WITHDRAWAL",
                            "cash": {"code": "EUR", "amount": "-125"},
                            "description": destination_description,
                        },
                    ],
                    "splits": [{"id_a": destination_id, "id_b": source_id}],
                },
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["committed"] is True, data
            assert data["success_count"] == 4
            assert [(result["operation"], result["index"], result["status"]) for result in data["results"]] == [
                ("split", 0, "success"),
                ("update", 0, "success"),
                ("update", 1, "success"),
                ("create", 0, "success"),
            ]

            rows_response = await client.get(
                f"{API_BASE}/transactions",
                params={"ids": [source_id, destination_id]},
                timeout=TIMEOUT,
            )
            assert rows_response.status_code == 200, rows_response.text
            by_id = {tx["id"]: tx for tx in rows_response.json()}
            assert set(by_id) == {source_id, destination_id}
            assert by_id[source_id]["type"] == "DEPOSIT"
            assert by_id[source_id]["description"] == source_description
            assert Decimal(by_id[source_id]["cash"]["amount"]) == Decimal("125")
            assert by_id[destination_id]["type"] == "WITHDRAWAL"
            assert by_id[destination_id]["description"] == destination_description
            assert Decimal(by_id[destination_id]["cash"]["amount"]) == Decimal("-125")
            assert all(tx["related_transaction_id"] is None for tx in by_id.values())
            print_success("Post-split type swaps and fields persisted in stage order ✓")


# ============================================================================
# B2 — PROMOTE VIA BATCH PIPELINE
# ============================================================================


@pytest.mark.asyncio
class TestBatchPromote:
    @pytest.fixture(autouse=True)
    def server(self, test_server):
        yield

    @pytest.mark.parametrize(
        "reverse_ids",
        [False, True],
        ids=["withdrawal-as-id-a", "deposit-as-id-a"],
    )
    async def test_commit_promote_saved_saved(self, reverse_ids):
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
            id_a, id_b = (d_id, w_id) if reverse_ids else (w_id, d_id)

            resp = await client.post(
                f"{API_BASE}/transactions/commit",
                json={"promotes": [{"id_a": id_a, "id_b": id_b}]},
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["committed"] is True, f"Promote not committed: {data}"
            assert data["issues"] == []
            promote_results = [result for result in data["results"] if result["operation"] == "promote"]
            assert len(promote_results) == 1
            assert promote_results[0]["ids"] == [id_a, id_b]

            # Verify both are CASH_TRANSFER with bidirectional link
            resp2 = await client.get(
                f"{API_BASE}/transactions",
                params={"ids": [w_id, d_id]},
                timeout=TIMEOUT,
            )
            txs = resp2.json()
            by_id = {tx["id"]: tx for tx in txs}
            assert set(by_id) == {w_id, d_id}
            assert all(tx["type"] == "CASH_TRANSFER" for tx in by_id.values())
            assert by_id[w_id]["related_transaction_id"] == d_id
            assert by_id[d_id]["related_transaction_id"] == w_id
            assert Decimal(by_id[w_id]["cash"]["amount"]) == Decimal("-800")
            assert Decimal(by_id[d_id]["cash"]["amount"]) == Decimal("800")
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
                            # Promoted into the incoming TRANSFER leg, the +3 needs a cost basis like any receiver
                            "cost_basis_override": {"code": "USD", "amount": "50"},
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

    async def test_adjustment_without_cost_basis_is_rejected(self):
        """Control: positive ADJUSTMENT with no cost basis and no mode → costBasisRequired, not committed."""
        print_section("B2.8 — Positive ADJUSTMENT without cost basis → costBasisRequired")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_b = await create_broker(client, "CbReqB")
            asset_id = await get_or_create_asset(client)

            resp = await client.post(
                f"{API_BASE}/transactions/commit",
                json={
                    "creates": [
                        {
                            "broker_id": broker_b,
                            "asset_id": asset_id,
                            "type": "ADJUSTMENT",
                            "date": "2026-03-02",
                            "quantity": "5",
                        },
                    ],
                },
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200, resp.text
            data = resp.json()
            assert data["committed"] is False, f"Positive ADJUSTMENT without cost basis was committed: {data}"
            assert any(i.get("code") == "costBasisRequired" and i.get("field") == "cost_basis_override" and i.get("operation") == "create" and i.get("index") == 0 for i in data["issues"]), f"Expected costBasisRequired on cost_basis_override for create 0: {data['issues']}"
            print_success("Positive ADJUSTMENT without cost basis → costBasisRequired ✓")

    async def test_promote_saved_saved_clearing_cost_basis_is_rejected(self):
        """Promote saved ADJUSTMENT(-5) + saved ADJUSTMENT(+5) resolving cost_basis_override to null → costBasisRequired, not committed."""
        print_section("B2.9 — Promote saved+saved clearing the receiver cost basis → costBasisRequired")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_a = await create_broker(client, "PromClrCbA")
            broker_b = await create_broker(client, "PromClrCbB")
            asset_id = await get_or_create_asset(client)

            # A: +10 (the helper adds its USD 50 cost basis), then the outgoing -5
            await create_standalone_tx(
                client,
                broker_a,
                "ADJUSTMENT",
                asset_id=asset_id,
                quantity="10",
                tx_date="2026-03-01",
            )
            id_minus = await create_standalone_tx(
                client,
                broker_a,
                "ADJUSTMENT",
                asset_id=asset_id,
                quantity="-5",
                tx_date="2026-03-02",
            )
            # B: the incoming +5, saved with a manual cost basis
            id_plus = await create_standalone_tx(
                client,
                broker_b,
                "ADJUSTMENT",
                asset_id=asset_id,
                quantity="5",
                tx_date="2026-03-02",
                cost_basis_override={"code": "EUR", "amount": "10"},
            )

            # API-only path: the promote resolves the receiver's cost basis to null
            resp = await client.post(
                f"{API_BASE}/transactions/commit",
                json={
                    "promotes": [
                        {
                            "id_a": id_minus,
                            "id_b": id_plus,
                            "resolved_fields": {"cost_basis_override": None},
                        }
                    ],
                },
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200, resp.text
            data = resp.json()
            if data["committed"]:
                rows_resp = await client.get(
                    f"{API_BASE}/transactions",
                    params={"ids": [id_plus]},
                    timeout=TIMEOUT,
                )
                assert rows_resp.status_code == 200, rows_resp.text
                receiver = {tx["id"]: tx for tx in rows_resp.json()}.get(id_plus, {})
                pytest.fail(
                    f"Promote of saved ADJUSTMENT(-5) id={id_minus} + saved ADJUSTMENT(+5) id={id_plus} with resolved cost_basis_override=null was committed "
                    f"(issues={data['issues']}): receiver {id_plus} is now type={receiver.get('type')} cost_basis_override={receiver.get('cost_basis_override')}; "
                    f"expected committed=false with a costBasisRequired issue"
                )
            assert any(i.get("code") == "costBasisRequired" for i in data["issues"]), f"Expected costBasisRequired: {data['issues']}"
            print_success("Promote saved+saved clearing the receiver cost basis → costBasisRequired ✓")

    async def test_promote_saved_new_without_cost_basis_is_rejected(self):
        """Promote saved ADJUSTMENT(-5) + new ADJUSTMENT(+5) without cost basis → costBasisRequired for the create, not committed."""
        print_section("B2.10 — Promote saved+new, new receiver without cost basis → costBasisRequired")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_a = await create_broker(client, "PromNoCbA")
            broker_b = await create_broker(client, "PromNoCbB")
            asset_id = await get_or_create_asset(client)

            # A: +10 (the helper adds its USD 50 cost basis), then the outgoing -5
            await create_standalone_tx(
                client,
                broker_a,
                "ADJUSTMENT",
                asset_id=asset_id,
                quantity="10",
                tx_date="2026-03-01",
            )
            id_minus = await create_standalone_tx(
                client,
                broker_a,
                "ADJUSTMENT",
                asset_id=asset_id,
                quantity="-5",
                tx_date="2026-03-02",
            )

            # UI-reachable: bulk editor, new row + saved row → Promote pair.
            # The new receiver carries no cost basis and no cost_basis_mode.
            new_uuid = str(uuid.uuid4())
            resp = await client.post(
                f"{API_BASE}/transactions/commit",
                json={
                    "creates": [
                        {
                            "broker_id": broker_b,
                            "asset_id": asset_id,
                            "type": "ADJUSTMENT",
                            "date": "2026-03-02",
                            "quantity": "5",
                            "link_uuid": new_uuid,
                        },
                    ],
                    "promotes": [{"id_a": id_minus, "link_uuid_b": new_uuid}],
                },
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200, resp.text
            data = resp.json()
            if data["committed"]:
                new_ids = [tx_id for r in data["results"] if r["operation"] == "create" and r["index"] == 0 for tx_id in r["ids"]]
                assert new_ids, f"Committed without a create result for index 0: {data}"
                rows_resp = await client.get(
                    f"{API_BASE}/transactions",
                    params={"ids": new_ids},
                    timeout=TIMEOUT,
                )
                assert rows_resp.status_code == 200, rows_resp.text
                receivers = "; ".join(f"id={tx['id']} type={tx['type']} cost_basis_override={tx['cost_basis_override']}" for tx in rows_resp.json())
                pytest.fail(f"Promote of saved ADJUSTMENT(-5) id={id_minus} + new ADJUSTMENT(+5) without cost basis was committed (issues={data['issues']}): new receiver {receivers}; expected committed=false with a costBasisRequired issue for create 0")
            assert any(i.get("code") == "costBasisRequired" and i.get("operation") == "create" and i.get("index") == 0 for i in data["issues"]), f"Expected costBasisRequired for create 0: {data['issues']}"
            print_success("Promote saved+new without cost basis → costBasisRequired ✓")

    async def test_promote_saved_saved_adjustments_keep_receiver_cost(self):
        """Control: promote saved ADJUSTMENT(-5) + saved ADJUSTMENT(+5) with a cost basis, no resolved_fields → committed, receiver keeps its cost."""
        print_section("B2.11 — Promote saved+saved, receiver keeps its cost basis → committed")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_a = await create_broker(client, "PromKeepCbA")
            broker_b = await create_broker(client, "PromKeepCbB")
            asset_id = await get_or_create_asset(client)

            # A: +10 (the helper adds its USD 50 cost basis), then the outgoing -5
            await create_standalone_tx(
                client,
                broker_a,
                "ADJUSTMENT",
                asset_id=asset_id,
                quantity="10",
                tx_date="2026-03-01",
            )
            id_minus = await create_standalone_tx(
                client,
                broker_a,
                "ADJUSTMENT",
                asset_id=asset_id,
                quantity="-5",
                tx_date="2026-03-02",
            )
            # B: the incoming +5, saved with a manual cost basis
            id_plus = await create_standalone_tx(
                client,
                broker_b,
                "ADJUSTMENT",
                asset_id=asset_id,
                quantity="5",
                tx_date="2026-03-02",
                cost_basis_override={"code": "EUR", "amount": "10"},
            )

            # No resolved_fields: the promote leaves the receiver's saved cost basis untouched
            resp = await client.post(
                f"{API_BASE}/transactions/commit",
                json={"promotes": [{"id_a": id_minus, "id_b": id_plus}]},
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200, resp.text
            data = resp.json()
            assert data["committed"] is True, f"Promote of saved ADJUSTMENT(-5) id={id_minus} + saved ADJUSTMENT(+5) id={id_plus} with cost EUR 10 was not committed: {data}"
            assert data["issues"] == [], f"Unexpected issues: {data['issues']}"

            rows_resp = await client.get(
                f"{API_BASE}/transactions",
                params={"ids": [id_minus, id_plus]},
                timeout=TIMEOUT,
            )
            assert rows_resp.status_code == 200, rows_resp.text
            by_id = {tx["id"]: tx for tx in rows_resp.json()}
            assert set(by_id) == {id_minus, id_plus}, f"Expected rows {id_minus} and {id_plus}, got {sorted(by_id)}"
            assert by_id[id_minus]["type"] == "TRANSFER", f"Sender {id_minus}: expected TRANSFER, got {by_id[id_minus]['type']}"
            assert by_id[id_plus]["type"] == "TRANSFER", f"Receiver {id_plus}: expected TRANSFER, got {by_id[id_plus]['type']}"
            assert by_id[id_minus]["related_transaction_id"] == id_plus, f"Sender {id_minus}: expected related_transaction_id={id_plus}, got {by_id[id_minus]['related_transaction_id']}"
            assert by_id[id_plus]["related_transaction_id"] == id_minus, f"Receiver {id_plus}: expected related_transaction_id={id_minus}, got {by_id[id_plus]['related_transaction_id']}"
            receiver_cost = by_id[id_plus]["cost_basis_override"]
            assert receiver_cost is not None, f"Receiver {id_plus} lost its cost basis: {by_id[id_plus]}"
            assert receiver_cost["code"] == "EUR", f"Receiver {id_plus}: expected cost basis in EUR, got {receiver_cost}"
            assert Decimal(receiver_cost["amount"]) == Decimal("10"), f"Receiver {id_plus}: expected cost basis EUR 10, got {receiver_cost}"
            print_success("Promote saved+saved keeps the receiver cost basis → committed ✓")

    async def test_promote_saved_new_with_cost_basis_commits(self):
        """Control: promote saved ADJUSTMENT(-5) + new ADJUSTMENT(+5) carrying a cost basis → committed, new row is the linked TRANSFER receiver."""
        print_section("B2.12 — Promote saved+new, new receiver with cost basis → committed")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_a = await create_broker(client, "PromNewCbA")
            broker_b = await create_broker(client, "PromNewCbB")
            asset_id = await get_or_create_asset(client)

            # A: +10 (the helper adds its USD 50 cost basis), then the outgoing -5
            await create_standalone_tx(
                client,
                broker_a,
                "ADJUSTMENT",
                asset_id=asset_id,
                quantity="10",
                tx_date="2026-03-01",
            )
            id_minus = await create_standalone_tx(
                client,
                broker_a,
                "ADJUSTMENT",
                asset_id=asset_id,
                quantity="-5",
                tx_date="2026-03-02",
            )

            # Bulk editor, new row + saved row → Promote pair. The new receiver carries its cost basis.
            new_uuid = str(uuid.uuid4())
            resp = await client.post(
                f"{API_BASE}/transactions/commit",
                json={
                    "creates": [
                        {
                            "broker_id": broker_b,
                            "asset_id": asset_id,
                            "type": "ADJUSTMENT",
                            "date": "2026-03-02",
                            "quantity": "5",
                            "link_uuid": new_uuid,
                            "cost_basis_override": {"code": "EUR", "amount": "10"},
                        },
                    ],
                    "promotes": [{"id_a": id_minus, "link_uuid_b": new_uuid}],
                },
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200, resp.text
            data = resp.json()
            assert data["committed"] is True, f"Promote of saved ADJUSTMENT(-5) id={id_minus} + new ADJUSTMENT(+5) with cost EUR 10 was not committed: {data}"
            assert data["issues"] == [], f"Unexpected issues: {data['issues']}"
            new_ids = [tx_id for r in data["results"] if r["operation"] == "create" and r["index"] == 0 for tx_id in r["ids"]]
            assert len(new_ids) == 1, f"Expected one id for create 0, got {new_ids}: {data['results']}"
            new_id = new_ids[0]

            rows_resp = await client.get(
                f"{API_BASE}/transactions",
                params={"ids": [id_minus, new_id]},
                timeout=TIMEOUT,
            )
            assert rows_resp.status_code == 200, rows_resp.text
            by_id = {tx["id"]: tx for tx in rows_resp.json()}
            assert set(by_id) == {id_minus, new_id}, f"Expected rows {id_minus} and {new_id}, got {sorted(by_id)}"
            assert by_id[new_id]["type"] == "TRANSFER", f"New receiver {new_id}: expected TRANSFER, got {by_id[new_id]['type']}"
            assert by_id[id_minus]["type"] == "TRANSFER", f"Saved sender {id_minus}: expected TRANSFER, got {by_id[id_minus]['type']}"
            assert by_id[new_id]["related_transaction_id"] == id_minus, f"New receiver {new_id}: expected related_transaction_id={id_minus}, got {by_id[new_id]['related_transaction_id']}"
            assert by_id[id_minus]["related_transaction_id"] == new_id, f"Saved sender {id_minus}: expected related_transaction_id={new_id}, got {by_id[id_minus]['related_transaction_id']}"
            new_cost = by_id[new_id]["cost_basis_override"]
            assert new_cost is not None, f"New receiver {new_id} stored no cost basis: {by_id[new_id]}"
            assert new_cost["code"] == "EUR", f"New receiver {new_id}: expected cost basis in EUR, got {new_cost}"
            assert Decimal(new_cost["amount"]) == Decimal("10"), f"New receiver {new_id}: expected cost basis EUR 10, got {new_cost}"
            print_success("Promote saved+new with cost basis → linked TRANSFER pair ✓")

    async def test_transfer_pair_create_unbalanced_quantities_is_rejected(self):
        """TRANSFER pair create -3 on A / +5 on B under one link_uuid → pairQuantityMismatch, not committed.

        This is what the bulk editor sends after promoting two new ADJUSTMENTs (-3 / +5): it promotes
        them locally, giving both the type TRANSFER and one shared link_uuid, so the backend only sees
        a plain TRANSFER pair create.
        """
        print_section("B2.13 — TRANSFER pair create with unbalanced quantities → pairQuantityMismatch")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_a = await create_broker(client, "PairQtyA")
            broker_b = await create_broker(client, "PairQtyB")
            asset_id = await get_or_create_asset(client)

            # A: +10 (the helper adds its USD 50 cost basis), enough units for the outgoing -3
            await create_standalone_tx(
                client,
                broker_a,
                "ADJUSTMENT",
                asset_id=asset_id,
                quantity="10",
                tx_date="2026-03-01",
            )

            link_uuid = str(uuid.uuid4())
            resp = await client.post(
                f"{API_BASE}/transactions/commit",
                json={
                    "creates": [
                        {
                            "broker_id": broker_a,
                            "asset_id": asset_id,
                            "type": "TRANSFER",
                            "date": "2026-03-02",
                            "quantity": "-3",
                            "link_uuid": link_uuid,
                        },
                        {
                            "broker_id": broker_b,
                            "asset_id": asset_id,
                            "type": "TRANSFER",
                            "date": "2026-03-02",
                            "quantity": "5",
                            "link_uuid": link_uuid,
                            # The receiver carries its cost basis: the cost basis is not the issue here
                            "cost_basis_override": {"code": "EUR", "amount": "10"},
                        },
                    ],
                },
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200, resp.text
            data = resp.json()
            if data["committed"]:
                new_ids = [tx_id for r in data["results"] if r["operation"] == "create" for tx_id in r["ids"]]
                rows = await describe_transactions(client, new_ids)
                pytest.fail(
                    f"TRANSFER pair create -3 on broker {broker_a} / +5 on broker {broker_b} (link_uuid {link_uuid}) was committed (issues={data['issues']}): persisted {rows}. Broker {broker_b} gains 5 while broker {broker_a} loses 3; expected committed=false with a pairQuantityMismatch issue"
                )
            assert any(i.get("code") == "pairQuantityMismatch" for i in data["issues"]), f"Expected pairQuantityMismatch: {data}"
            print_success("TRANSFER pair create -3 / +5 → pairQuantityMismatch ✓")

    @pytest.mark.parametrize("endpoint", ["commit", "validate"])
    async def test_adjustment_pair_create_is_rejected(self, endpoint):
        """ADJUSTMENT -2 on A / +2 on B under one link_uuid → pairAdjustmentNotAllowed on create 0, not committed, nothing written.

        Two Adjustments cannot be linked (decision of 22/10/2026): units that move between brokers are an Asset
        Transfer. The refusal is at entry only: this is a create of a linked pair that no promote consumes.
        """
        print_section(f"B2.13b — ADJUSTMENT pair create under one link_uuid (/{endpoint}) → pairAdjustmentNotAllowed")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_a = await create_broker(client, "PairAdjA")
            broker_b = await create_broker(client, "PairAdjB")
            asset_id = await get_or_create_asset(client)

            # A: +10 (the helper adds its USD 50 cost basis), enough units for the outgoing -2
            seed_id = await create_standalone_tx(
                client,
                broker_a,
                "ADJUSTMENT",
                asset_id=asset_id,
                quantity="10",
                tx_date="2026-03-01",
            )

            link_uuid = str(uuid.uuid4())
            description = f"adjustment pair {uuid.uuid4().hex[:8]}"
            resp = await client.post(
                f"{API_BASE}/transactions/{endpoint}",
                json={
                    "creates": [
                        {
                            "broker_id": broker_a,
                            "asset_id": asset_id,
                            "type": "ADJUSTMENT",
                            "date": "2026-03-02",
                            "quantity": "-2",
                            "description": description,
                            "link_uuid": link_uuid,
                        },
                        {
                            "broker_id": broker_b,
                            "asset_id": asset_id,
                            "type": "ADJUSTMENT",
                            "date": "2026-03-02",
                            "quantity": "2",
                            "description": description,
                            "link_uuid": link_uuid,
                            # The receiver carries its cost basis: the cost basis is not the issue here
                            "cost_basis_override": {"code": "EUR", "amount": "10"},
                        },
                    ],
                },
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200, resp.text
            data = resp.json()
            refusal = [(i["operation"], i["index"], i.get("ref_id"), i["code"], i.get("params")) for i in data["issues"]]
            expected = [("create", 0, None, "pairAdjustmentNotAllowed", {"type": "ADJUSTMENT"})]
            what = f"ADJUSTMENT pair create -2 on broker {broker_a} / +2 on broker {broker_b} (link_uuid {link_uuid}, /{endpoint})"
            assert refusal == expected, f"{what}: expected exactly one pairAdjustmentNotAllowed on create 0 and none on create 1, got {data['issues']}"
            assert data["committed"] is False, f"ADJUSTMENT pair create (/{endpoint}) was reported committed: {data}"

            # Nothing was written: broker B (this test's own) holds no row, broker A only its seed
            rows_b = await client.get(f"{API_BASE}/transactions", params={"broker_id": broker_b}, timeout=TIMEOUT)
            assert rows_b.status_code == 200, rows_b.text
            assert [tx["id"] for tx in rows_b.json()] == [], f"A refused ADJUSTMENT pair left rows on broker {broker_b}: {rows_b.json()}"
            rows_a = await client.get(f"{API_BASE}/transactions", params={"broker_id": broker_a}, timeout=TIMEOUT)
            assert rows_a.status_code == 200, rows_a.text
            assert {tx["id"] for tx in rows_a.json()} == {seed_id}, f"A refused ADJUSTMENT pair changed broker {broker_a}: {rows_a.json()}"
            print_success(f"ADJUSTMENT pair -2 / +2 (/{endpoint}) → pairAdjustmentNotAllowed, nothing written ✓")

    async def test_transfer_pair_create_different_assets_is_rejected(self):
        """TRANSFER pair create asset X -3 on A / asset Y +3 on B under one link_uuid → pairAssetMismatch, not committed."""
        print_section("B2.14 — TRANSFER pair create across two assets → pairAssetMismatch")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_a = await create_broker(client, "PairAssetA")
            broker_b = await create_broker(client, "PairAssetB")
            asset_x = await get_or_create_asset(client, "PairAssetX")
            asset_y = await get_or_create_asset(client, "PairAssetY")

            # A: +10 of X (the helper adds its USD 50 cost basis), enough units for the outgoing -3
            await create_standalone_tx(
                client,
                broker_a,
                "ADJUSTMENT",
                asset_id=asset_x,
                quantity="10",
                tx_date="2026-03-01",
            )

            link_uuid = str(uuid.uuid4())
            resp = await client.post(
                f"{API_BASE}/transactions/commit",
                json={
                    "creates": [
                        {
                            "broker_id": broker_a,
                            "asset_id": asset_x,
                            "type": "TRANSFER",
                            "date": "2026-03-02",
                            "quantity": "-3",
                            "link_uuid": link_uuid,
                        },
                        {
                            "broker_id": broker_b,
                            "asset_id": asset_y,
                            "type": "TRANSFER",
                            "date": "2026-03-02",
                            "quantity": "3",
                            "link_uuid": link_uuid,
                            # The receiver carries its cost basis: the cost basis is not the issue here
                            "cost_basis_override": {"code": "EUR", "amount": "10"},
                        },
                    ],
                },
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200, resp.text
            data = resp.json()
            if data["committed"]:
                new_ids = [tx_id for r in data["results"] if r["operation"] == "create" for tx_id in r["ids"]]
                rows = await describe_transactions(client, new_ids)
                pytest.fail(
                    f"TRANSFER pair create asset {asset_x} -3 on broker {broker_a} / asset {asset_y} +3 on broker {broker_b} (link_uuid {link_uuid}) was committed (issues={data['issues']}): persisted {rows}. Asset {asset_x} leaves broker {broker_a} while asset {asset_y} appears on broker {broker_b}; expected committed=false with a pairAssetMismatch issue"
                )
            assert any(i.get("code") == "pairAssetMismatch" for i in data["issues"]), f"Expected pairAssetMismatch: {data}"
            print_success("TRANSFER pair create X -3 / Y +3 → pairAssetMismatch ✓")

    async def test_promote_split_linked_adjustment_is_rejected(self):
        """Promote saved ADJUSTMENT(-10) + saved SPLIT-linked ADJUSTMENT(+10) → eventTypeIncompatible on the promote, not committed.

        Business rule 9 forbids an asset_event_id on a TRANSFER: a promote must not turn an
        event-linked ADJUSTMENT into an event-linked TRANSFER.
        """
        print_section("B2.15 — Promote of a SPLIT-linked ADJUSTMENT → eventTypeIncompatible")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_a = await create_broker(client, "PromSplitA")
            broker_b = await create_broker(client, "PromSplitB")
            asset_id = await get_or_create_asset(client)
            split_date = "2026-03-10"

            # A: +10 (the helper adds its USD 50 cost basis), the units the outgoing -10 gives
            await create_standalone_tx(
                client,
                broker_a,
                "ADJUSTMENT",
                asset_id=asset_id,
                quantity="10",
                tx_date="2026-03-01",
            )
            # B: +10 before the split, then the 2:1 split realized as an ADJUSTMENT +10 linked to the event
            await create_standalone_tx(
                client,
                broker_b,
                "ADJUSTMENT",
                asset_id=asset_id,
                quantity="10",
                tx_date="2026-03-01",
            )
            event_id = await create_split_event(client, asset_id, split_date, "2")
            # Manual cost basis, not "auto": auto deliberately stores no cost basis on a SPLIT-linked row,
            # and the promoted receiver would then be refused with costBasisRequired, which is not the
            # subject here. With a cost basis the only problem left is the event link on a TRANSFER.
            split_resp = await client.post(
                f"{API_BASE}/transactions/commit",
                json={
                    "creates": [
                        {
                            "broker_id": broker_b,
                            "asset_id": asset_id,
                            "type": "ADJUSTMENT",
                            "date": split_date,
                            "quantity": "10",
                            "asset_event_id": event_id,
                            "cost_basis_mode": "manual",
                            "cost_basis_override": {"code": "EUR", "amount": "10"},
                        },
                    ],
                },
                timeout=TIMEOUT,
            )
            assert split_resp.status_code == 200, split_resp.text
            split_data = split_resp.json()
            assert split_data["committed"] is True, f"SPLIT-linked ADJUSTMENT(+10) on broker {broker_b} not committed: {split_data}"
            split_ids = [tx_id for r in split_data["results"] if r["operation"] == "create" and r["index"] == 0 for tx_id in r["ids"]]
            assert len(split_ids) == 1, f"Expected one id for create 0, got {split_ids}: {split_data}"
            split_adj_id = split_ids[0]
            # A: the outgoing -10, on the split date
            id_minus = await create_standalone_tx(
                client,
                broker_a,
                "ADJUSTMENT",
                asset_id=asset_id,
                quantity="-10",
                tx_date=split_date,
            )

            # Precondition: the +10 really is a saved ADJUSTMENT linked to the SPLIT event, with its cost basis
            pre_resp = await client.get(
                f"{API_BASE}/transactions",
                params={"ids": [split_adj_id]},
                timeout=TIMEOUT,
            )
            assert pre_resp.status_code == 200, pre_resp.text
            split_row = {tx["id"]: tx for tx in pre_resp.json()}.get(split_adj_id)
            assert split_row is not None, f"Saved SPLIT-linked row {split_adj_id} not found: {pre_resp.json()}"
            assert split_row["type"] == "ADJUSTMENT", f"Row {split_adj_id}: expected ADJUSTMENT before the promote, got {split_row}"
            assert split_row["asset_event_id"] == event_id, f"Row {split_adj_id}: expected asset_event_id={event_id} before the promote, got {split_row}"
            assert split_row["cost_basis_override"] is not None, f"Row {split_adj_id}: expected its manual cost basis before the promote, got {split_row}"

            resp = await client.post(
                f"{API_BASE}/transactions/commit",
                json={"promotes": [{"id_a": id_minus, "id_b": split_adj_id}]},
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200, resp.text
            data = resp.json()
            if data["committed"]:
                rows = await describe_transactions(client, [id_minus, split_adj_id])
                pytest.fail(
                    f"Promote of saved ADJUSTMENT(-10) id={id_minus} + SPLIT-linked ADJUSTMENT(+10) id={split_adj_id} (SPLIT event {event_id}) was committed (issues={data['issues']}): {rows}. The event-linked ADJUSTMENT became an event-linked TRANSFER; expected committed=false with an eventTypeIncompatible issue on operation promote"
                )
            assert any(i.get("code") == "eventTypeIncompatible" and i.get("operation") == "promote" for i in data["issues"]), f"Expected eventTypeIncompatible on operation promote: {data}"
            print_success("Promote of a SPLIT-linked ADJUSTMENT → eventTypeIncompatible ✓")

    async def test_promote_saved_new_unbalanced_quantities_is_refused(self):
        """Control: promote saved ADJUSTMENT(-3) + new ADJUSTMENT(+5) → noPromoteRule, not committed.

        The backend already refuses a saved+new promote whose quantities do not cancel
        (the TRANSFER promote rule wants opposite quantities), although the editor proposes it.
        """
        print_section("B2.16 — Promote saved+new with unbalanced quantities → noPromoteRule")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_a = await create_broker(client, "PromUnbalA")
            broker_b = await create_broker(client, "PromUnbalB")
            asset_id = await get_or_create_asset(client)

            # A: +10 (the helper adds its USD 50 cost basis), then the outgoing -3
            await create_standalone_tx(
                client,
                broker_a,
                "ADJUSTMENT",
                asset_id=asset_id,
                quantity="10",
                tx_date="2026-03-01",
            )
            id_minus = await create_standalone_tx(
                client,
                broker_a,
                "ADJUSTMENT",
                asset_id=asset_id,
                quantity="-3",
                tx_date="2026-03-02",
            )

            new_uuid = str(uuid.uuid4())
            resp = await client.post(
                f"{API_BASE}/transactions/commit",
                json={
                    "creates": [
                        {
                            "broker_id": broker_b,
                            "asset_id": asset_id,
                            "type": "ADJUSTMENT",
                            "date": "2026-03-02",
                            "quantity": "5",
                            "link_uuid": new_uuid,
                            "cost_basis_override": {"code": "EUR", "amount": "10"},
                        },
                    ],
                    "promotes": [{"id_a": id_minus, "link_uuid_b": new_uuid}],
                },
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200, resp.text
            data = resp.json()
            assert data["committed"] is False, f"Promote of saved ADJUSTMENT(-3) id={id_minus} + new ADJUSTMENT(+5) was committed: {data}"
            assert any(i.get("code") == "noPromoteRule" and i.get("operation") == "promote" for i in data["issues"]), f"Expected noPromoteRule on operation promote: {data}"

            # Nothing persisted: the saved -3 is still a standalone ADJUSTMENT
            rows_resp = await client.get(
                f"{API_BASE}/transactions",
                params={"ids": [id_minus]},
                timeout=TIMEOUT,
            )
            assert rows_resp.status_code == 200, rows_resp.text
            saved = {tx["id"]: tx for tx in rows_resp.json()}.get(id_minus)
            assert saved is not None, f"Saved row {id_minus} not found after the refused promote: {rows_resp.json()}"
            assert saved["type"] == "ADJUSTMENT", f"Saved row {id_minus}: expected ADJUSTMENT after the refused promote, got {saved}"
            assert saved["related_transaction_id"] is None, f"Saved row {id_minus}: expected no partner after the refused promote, got {saved}"
            print_success("Promote saved+new with unbalanced quantities → noPromoteRule ✓")


# ============================================================================
# B3 — PROMOTE-SUGGEST
# ============================================================================

# W-B71: promote_suggest_bulk searches each input's date ± tolerance_days. Around WINDOW_DAY one standalone WITHDRAWAL
# EUR -600 is stored at each offset (days): at tolerance_days=7 the offsets 0 and ±7 are inside the window, ±8 just
# outside. The calendar's edge days, 0001-01-01 and 9999-12-31, are where the window leaves the calendar.
WINDOW_DAY = date(2026, 3, 10)
WINDOW_INSIDE = (0, -7, 7)
WINDOW_OUTSIDE = (-8, 8)
CALENDAR_EDGES = (date.min, date.max)


async def create_window_withdrawals(client: httpx.AsyncClient, broker_id: int) -> dict[int, int]:
    """One standalone WITHDRAWAL EUR -600 on ``broker_id`` at each offset of WINDOW_INSIDE and WINDOW_OUTSIDE from WINDOW_DAY: ``{offset: id}``."""
    ids: dict[int, int] = {}
    for offset in (*WINDOW_INSIDE, *WINDOW_OUTSIDE):
        ids[offset] = await create_standalone_tx(client, broker_id, "WITHDRAWAL", cash={"code": "EUR", "amount": "-600"}, tx_date=(WINDOW_DAY + timedelta(days=offset)).isoformat())
    return ids


def deposit_input(input_id: int, broker_id: int, day: date) -> dict:
    """An unsaved DEPOSIT EUR 600 on ``broker_id`` dated ``day``: on another broker, each WITHDRAWAL EUR -600 is its CASH_TRANSFER other half."""
    return {"id": input_id, "type": "DEPOSIT", "broker_id": broker_id, "date": day.isoformat(), "currency": "EUR", "amount": "600"}


def candidate_ids(results: dict, input_id: int) -> list[int]:
    """The candidates of one input of a promote-suggest answer, by id, sorted."""
    return sorted(candidate["id"] for candidate in results.get(str(input_id), []))


async def post_on_its_own_connection(client: httpx.AsyncClient, url: str, **kwargs) -> httpx.Response:
    """POST with ``client``'s session on a connection of its own, for a request that may end in an unhandled exception.

    After such a 500 the server closes the connection; sent on the client's own, the next request (the cleanup) could be
    written to it and fail with a ReadError, leaving the test's rows behind.
    """
    async with httpx.AsyncClient(cookies=client.cookies) as own:
        return await own.post(url, **kwargs)


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

    async def test_suggest_direct_calls_service(self, monkeypatch: pytest.MonkeyPatch):
        """Happy path: route delegates to TransactionService.promote_suggest_bulk."""
        print_section("B3.6a — Suggest direct happy path")

        captured: dict = {}

        async def fake_promote_suggest_bulk(self, inputs, tolerance_days, user_id):
            captured["inputs"] = inputs
            captured["tolerance_days"] = tolerance_days
            captured["user_id"] = user_id
            return {"results": {"-1": []}}

        monkeypatch.setattr(
            transactions_api,
            "TransactionService",
            type(
                "FakeTransactionService",
                (),
                {"__init__": lambda self, session: None, "promote_suggest_bulk": fake_promote_suggest_bulk},
            ),
        )

        result = await transactions_api.promote_suggest(
            inputs=["input"],
            tolerance_days=7,
            session=object(),
            current_user=type("U", (), {"id": 1})(),
        )

        assert result == {"results": {"-1": []}}
        assert captured["inputs"] == ["input"]
        assert captured["tolerance_days"] == 7
        assert captured["user_id"] == 1
        print_success("Suggest direct happy path delegated to service ✓")

    async def test_suggest_accepts_more_than_500_inputs(self, monkeypatch: pytest.MonkeyPatch):
        """The 500-item cap was removed: large raw list bodies are delegated as-is."""
        print_section("B3.7 — Suggest accepts >500 inputs (no cap)")

        captured: dict = {}

        async def fake_promote_suggest_bulk(self, inputs, tolerance_days, user_id):
            captured["count"] = len(inputs)
            return {"results": {}}

        monkeypatch.setattr(
            transactions_api,
            "TransactionService",
            type(
                "FakeTransactionService",
                (),
                {"__init__": lambda self, session: None, "promote_suggest_bulk": fake_promote_suggest_bulk},
            ),
        )

        result = await transactions_api.promote_suggest(
            inputs=[object()] * 501,
            tolerance_days=7,
            session=object(),
            current_user=type("U", (), {"id": 1})(),
        )

        assert captured["count"] == 501
        assert result == {"results": {}}
        print_success("Suggest accepts >500 inputs (no cap) ✓")

    async def test_suggest_never_offers_an_event_linked_candidate(self):
        """A saved ADJUSTMENT linked to an asset event is never offered as the other half of a TRANSFER; its unlinked twin is.

        D2 (lot 42): no promote target accepts an asset-event link (TRANSFER, CASH_TRANSFER and
        FX_CONVERSION are all event_compatible=False), so a SPLIT-linked +5 can never be merged with a
        -5: the editor refuses the pair and the commit refuses the promote with eventTypeIncompatible
        (B2.15). Offering it is a dead end. The unlinked twin (same broker, day, quantity and cost
        basis: the link is the one difference) is the control the answer must keep.
        """
        print_section("B3.8 — Suggest never offers an event-linked candidate")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_a = await create_broker(client, "SugEvtCandA")
            broker_b = await create_broker(client, "SugEvtCandB")
            asset_id = await get_or_create_asset(client)
            day = "2026-03-10"
            event_id = await create_split_event(client, asset_id, day, "2")

            # B: the +5 linked to the SPLIT, with the USD 50 cost basis create_standalone_tx gives its twin below
            linked_resp = await client.post(
                f"{API_BASE}/transactions/commit",
                json={
                    "creates": [
                        {
                            "broker_id": broker_b,
                            "asset_id": asset_id,
                            "type": "ADJUSTMENT",
                            "date": day,
                            "quantity": "5",
                            "asset_event_id": event_id,
                            "cost_basis_mode": "manual",
                            "cost_basis_override": {"code": "USD", "amount": "50"},
                        },
                    ],
                },
                timeout=TIMEOUT,
            )
            assert linked_resp.status_code == 200, linked_resp.text
            linked_data = linked_resp.json()
            assert linked_data["committed"] is True, f"SPLIT-linked ADJUSTMENT(+5) on broker {broker_b} not committed: {linked_data}"
            linked_ids = [tx_id for r in linked_data["results"] if r["operation"] == "create" and r["index"] == 0 for tx_id in r["ids"]]
            assert len(linked_ids) == 1, f"Expected one id for create 0, got {linked_ids}: {linked_data}"
            linked_id = linked_ids[0]
            # B: the unlinked twin, same day and quantity
            twin_id = await create_standalone_tx(client, broker_b, "ADJUSTMENT", asset_id=asset_id, quantity="5", tx_date=day)

            # Precondition: the +5 really is saved linked to the SPLIT, and its twin unlinked
            pre_resp = await client.get(f"{API_BASE}/transactions", params={"ids": [linked_id, twin_id]}, timeout=TIMEOUT)
            assert pre_resp.status_code == 200, pre_resp.text
            saved = {tx["id"]: tx for tx in pre_resp.json()}
            assert saved.get(linked_id, {}).get("asset_event_id") == event_id, f"Row {linked_id}: expected asset_event_id={event_id} before the suggest, got {saved.get(linked_id)}"
            assert twin_id in saved and saved[twin_id]["asset_event_id"] is None, f"Row {twin_id}: expected no asset_event_id before the suggest, got {saved.get(twin_id)}"

            resp = await client.post(
                f"{API_BASE}/transactions/promote-suggest",
                params={"tolerance_days": 7},
                json=[{"id": -1, "type": "ADJUSTMENT", "broker_id": broker_a, "date": day, "asset_id": asset_id, "quantity": "-5"}],
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200, resp.text
            candidate_ids = [c["id"] for c in resp.json()["results"].get("-1", [])]
            assert twin_id in candidate_ids, f"Control: the unlinked ADJUSTMENT(+5) id={twin_id} on broker {broker_b} must be offered to a new ADJUSTMENT(-5) on broker {broker_a}; candidates {candidate_ids}"
            if linked_id in candidate_ids:
                rows = await describe_transactions(client, [linked_id, twin_id])
                pytest.fail(
                    f"promote-suggest offered the SPLIT-linked ADJUSTMENT(+5) id={linked_id} (SPLIT event {event_id}) as the other half of a new ADJUSTMENT(-5) on broker {broker_a}: candidates {candidate_ids}; rows {rows}. No promote target accepts an asset-event link (D2, lot 42), so this pair can never be merged; expected the unlinked twin id={twin_id} and not the linked row"
                )
            print_success("Suggest offers the unlinked twin, never the event-linked +5 ✓")

    async def test_suggest_gives_an_event_linked_input_no_candidate(self):
        """An input linked to an asset event gets no candidate; the same input without the link still finds the +5.

        asset_event_id is the new optional field of TXPromoteSuggestInput (D2, lot 42): the bulk editor
        sends each row's link, and a row linked to an event, which no promote target accepts, is not
        offered a pair it can never take. Without the field the answer is today's (control): the new
        field is backward compatible.
        """
        print_section("B3.9 — Suggest: an event-linked input gets no candidate")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_a = await create_broker(client, "SugEvtInA")
            broker_b = await create_broker(client, "SugEvtInB")
            asset_id = await get_or_create_asset(client)
            day = "2026-03-10"
            event_id = await create_split_event(client, asset_id, day, "2")
            # B: a saved, unlinked +5, the other half of a -5 on A
            plus_id = await create_standalone_tx(client, broker_b, "ADJUSTMENT", asset_id=asset_id, quantity="5", tx_date=day)
            minus_five = {"id": -1, "type": "ADJUSTMENT", "broker_id": broker_a, "date": day, "asset_id": asset_id, "quantity": "-5"}

            # (i) Control, without the field: the +5 is offered, as today
            control = await client.post(f"{API_BASE}/transactions/promote-suggest", params={"tolerance_days": 7}, json=[minus_five], timeout=TIMEOUT)
            assert control.status_code == 200, control.text
            control_ids = [c["id"] for c in control.json()["results"].get("-1", [])]
            assert plus_id in control_ids, f"Control: ADJUSTMENT(+5) id={plus_id} on broker {broker_b} must be offered to an unlinked ADJUSTMENT(-5) on broker {broker_a}; candidates {control_ids}"

            # (ii) The same -5, linked to the SPLIT: nothing to offer
            linked = await client.post(f"{API_BASE}/transactions/promote-suggest", params={"tolerance_days": 7}, json=[{**minus_five, "asset_event_id": event_id}], timeout=TIMEOUT)
            if linked.status_code != 200:
                pytest.fail(
                    f"promote-suggest answered HTTP {linked.status_code} to an input carrying asset_event_id={event_id}: {linked.text}. asset_event_id is the new optional field of TXPromoteSuggestInput (D2, lot 42); today the StrictModel does not declare it, so the key is refused as an extra field (422)"
                )
            linked_ids = [c["id"] for c in linked.json()["results"].get("-1", [])]
            assert linked_ids == [], f"An ADJUSTMENT(-5) linked to SPLIT event {event_id} was offered candidates {linked_ids} (the unlinked +5 is id={plus_id}): no promote target accepts an asset-event link, so a linked input gets no candidate"
            print_success("Suggest: an event-linked input gets no candidate, the unlinked one still finds the +5 ✓")

    async def test_suggest_treats_a_null_or_zero_asset_event_id_as_unlinked(self):
        """asset_event_id null or 0 means "not linked": the answer is exactly the one given without the field.

        The contract of the new optional field (D2, lot 42): None is an unlinked row, and 0 is the
        editor's unlink sentinel (an update's asset_event_id=0, txPayloadHelpers). Either leaves the
        answer as it is today, with the unlinked +5 offered.
        """
        print_section("B3.10 — Suggest: asset_event_id null or 0 = not linked")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_a = await create_broker(client, "SugEvtNullA")
            broker_b = await create_broker(client, "SugEvtNullB")
            asset_id = await get_or_create_asset(client)
            day = "2026-03-10"
            plus_id = await create_standalone_tx(client, broker_b, "ADJUSTMENT", asset_id=asset_id, quantity="5", tx_date=day)
            minus_five = {"id": -1, "type": "ADJUSTMENT", "broker_id": broker_a, "date": day, "asset_id": asset_id, "quantity": "-5"}

            # Control, without the field
            control = await client.post(f"{API_BASE}/transactions/promote-suggest", params={"tolerance_days": 7}, json=[minus_five], timeout=TIMEOUT)
            assert control.status_code == 200, control.text
            control_ids = sorted(c["id"] for c in control.json()["results"].get("-1", []))
            assert plus_id in control_ids, f"Control: ADJUSTMENT(+5) id={plus_id} on broker {broker_b} must be offered to an unlinked ADJUSTMENT(-5) on broker {broker_a}; candidates {control_ids}"

            for unlinked in (None, 0):
                resp = await client.post(f"{API_BASE}/transactions/promote-suggest", params={"tolerance_days": 7}, json=[{**minus_five, "asset_event_id": unlinked}], timeout=TIMEOUT)
                if resp.status_code != 200:
                    pytest.fail(
                        f"promote-suggest answered HTTP {resp.status_code} to an input carrying asset_event_id={unlinked!r}: {resp.text}. asset_event_id is the new optional field of TXPromoteSuggestInput (D2, lot 42), where None and 0 mean not linked; today the StrictModel does not declare it, so the key is refused as an extra field (422)"
                    )
                ids = sorted(c["id"] for c in resp.json()["results"].get("-1", []))
                assert ids == control_ids, f"asset_event_id={unlinked!r} must mean not linked: candidates {ids}, without the field {control_ids}"
            print_success("Suggest: asset_event_id null or 0 answers as without the field ✓")

    async def test_suggest_tolerance_zero_is_the_same_day_only(self):
        """tolerance_days=0 is the same day only: a new +5 on day D is offered the -5 of D, never the -5 of D-1.

        C-47: the bulk editor's Max delta days slider goes down to 0, where its local banner offers
        same-day pairs only; the database search must read 0 the same way. promote_suggest_bulk
        searches date ± tolerance_days, so 0 is lo == hi == date. Today the endpoint declares
        tolerance_days >= 1 and answers 422, which the editor only logs: its lightbulb offers nothing.
        The control, in its own request at tolerance_days=1, offers both rows: what 0 leaves out is
        the window's doing, nothing else.
        """
        print_section("B3.11 — Suggest: tolerance_days=0 = the same day only")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_a = await create_broker(client, "SugZeroA")
            broker_b = await create_broker(client, "SugZeroB")
            asset_id = await get_or_create_asset(client)
            day, day_before = "2026-03-10", "2026-03-09"
            # A: the position (create_standalone_tx gives the +20 a USD 50 cost basis), then a -5 on D-1 and a -5 on D
            await create_standalone_tx(client, broker_a, "ADJUSTMENT", asset_id=asset_id, quantity="20", tx_date="2026-03-01")
            day_before_id = await create_standalone_tx(client, broker_a, "ADJUSTMENT", asset_id=asset_id, quantity="-5", tx_date=day_before)
            same_day_id = await create_standalone_tx(client, broker_a, "ADJUSTMENT", asset_id=asset_id, quantity="-5", tx_date=day)
            plus_five = [{"id": -1, "type": "ADJUSTMENT", "broker_id": broker_b, "date": day, "asset_id": asset_id, "quantity": "5"}]

            # Control, its own request: one day either side reaches both -5
            control = await client.post(f"{API_BASE}/transactions/promote-suggest", params={"tolerance_days": 1}, json=plus_five, timeout=TIMEOUT)
            assert control.status_code == 200, control.text
            control_ids = sorted(c["id"] for c in control.json()["results"].get("-1", []))
            both = sorted([same_day_id, day_before_id])
            assert control_ids == both, f"Control: at tolerance_days=1 a new ADJUSTMENT(+5) on broker {broker_b} at {day} must be offered both ADJUSTMENT(-5) on broker {broker_a}, id={same_day_id} at {day} and id={day_before_id} at {day_before}; candidates {control_ids}"

            # tolerance_days=0: the same day only
            resp = await client.post(f"{API_BASE}/transactions/promote-suggest", params={"tolerance_days": 0}, json=plus_five, timeout=TIMEOUT)
            if resp.status_code != 200:
                pytest.fail(
                    f"promote-suggest answered HTTP {resp.status_code} to tolerance_days=0: {resp.text}. 0 is the new contract (C-47): the same day only, the window {day} ± 0 days, as the bulk editor's Max delta days slider means at 0; today the endpoint declares tolerance_days >= 1 and refuses it"
                )
            ids = sorted(c["id"] for c in resp.json()["results"].get("-1", []))
            assert ids == [same_day_id], f"tolerance_days=0 must offer the ADJUSTMENT(-5) id={same_day_id} of {day} alone, never id={day_before_id} of {day_before}; candidates {ids}"
            print_success("Suggest: tolerance_days=0 offers the same day only ✓")

    async def test_suggest_window_guard_inside_the_calendar(self):
        """B3.12 — W-B71 guard (passes before and after the cure): the window of an ordinary input, and the edge days at tolerance_days=0.

        At tolerance_days=7 a new DEPOSIT EUR 600 dated 2026-03-10 on broker B is offered the WITHDRAWALs EUR -600 of
        broker A 0 and 7 days away, either side, never those 8 days away. At tolerance_days=0 the same input, batched with
        two more dated 0001-01-01 and 9999-12-31, is answered today: a window of the day itself moves nothing past the
        calendar. One entry per input, the ordinary one keeps its same-day candidate, the edge ones have none. So the edge
        dates are accepted as such: what B3.13 adds is the window around them.
        """
        print_section("B3.12 — Suggest: the window inside the calendar (W-B71 guard)")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_ids: list[int] = []
            cleanup_problems: list[str] = []
            try:
                broker_a = await create_broker(client, "SugEdgeGuardA")
                broker_ids.append(broker_a)
                broker_b = await create_broker(client, "SugEdgeGuardB")
                broker_ids.append(broker_b)
                rows = await create_window_withdrawals(client, broker_a)
                inside = sorted(rows[offset] for offset in WINDOW_INSIDE)
                ordinary = deposit_input(-1, broker_b, WINDOW_DAY)

                week = await client.post(f"{API_BASE}/transactions/promote-suggest", params={"tolerance_days": 7}, json=[ordinary], timeout=TIMEOUT)
                assert week.status_code == 200, week.text
                found = candidate_ids(week.json()["results"], -1)
                assert found == inside, f"At tolerance_days=7 a DEPOSIT EUR 600 dated {WINDOW_DAY} on broker {broker_b} must be offered the WITHDRAWALs 0 and 7 days away {inside}, never those 8 days away {[rows[offset] for offset in WINDOW_OUTSIDE]}; candidates {found} (rows by offset {rows})"

                batch = [ordinary, deposit_input(-2, broker_b, date.min), deposit_input(-3, broker_b, date.max)]
                same_day = await client.post(f"{API_BASE}/transactions/promote-suggest", params={"tolerance_days": 0}, json=batch, timeout=TIMEOUT)
                assert same_day.status_code == 200, f"At tolerance_days=0 a batch with inputs dated 0001-01-01 and 9999-12-31 must be answered (the window is the day itself): HTTP {same_day.status_code} {same_day.text}"
                results = same_day.json()["results"]
                assert sorted(results) == ["-1", "-2", "-3"], f"One entry per input expected: {sorted(results)}"
                assert candidate_ids(results, -1) == [rows[0]], f"At tolerance_days=0 the ordinary input keeps its same-day WITHDRAWAL id={rows[0]}, next to the edge-dated inputs: {results}"
                assert (results["-2"], results["-3"]) == ([], []), f"Nothing is stored on 0001-01-01 or 9999-12-31: {results}"
                print_success("Suggest: the window reaches 7 days and no further; the edge days are answered at tolerance 0 ✓")
            finally:
                cleanup_problems = await delete_owned(client, broker_ids=broker_ids, asset_ids=[])
            assert cleanup_problems == [], f"Cleanup of the test's brokers: {cleanup_problems}"

    async def test_suggest_cuts_the_window_at_the_calendar_edges(self):
        """B3.13 — RED until W-B71: inputs dated 0001-01-01 and 9999-12-31 at tolerance_days=7 are answered with no candidate, and the ordinary input of the same batch keeps its own.

        promote_suggest_bulk searches date ± tolerance_days: 7 days before 0001-01-01 or after 9999-12-31 is outside the
        calendar, OverflowError, a 500 for the whole batch: every draft of the bulk editor loses its suggestions for one row
        with a mistyped year. The window must be cut at the calendar's edge (shift_date, saturating at date.min /
        date.max); not a 422, since the save refuses such a date already (N74). Then: one entry per input, none for the
        edge ones (nothing is stored that early or that late), and the DEPOSIT dated 2026-03-10 is still offered the
        WITHDRAWALs 0 and 7 days away and never those 8 days away, as in B3.12: the window is still the window.
        """
        print_section("B3.13 — Suggest: the window cut at the calendar's edges (W-B71)")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_ids: list[int] = []
            cleanup_problems: list[str] = []
            try:
                broker_a = await create_broker(client, "SugEdgeA")
                broker_ids.append(broker_a)
                broker_b = await create_broker(client, "SugEdgeB")
                broker_ids.append(broker_b)
                rows = await create_window_withdrawals(client, broker_a)
                inside = sorted(rows[offset] for offset in WINDOW_INSIDE)
                batch = [deposit_input(-1, broker_b, WINDOW_DAY), deposit_input(-2, broker_b, date.min), deposit_input(-3, broker_b, date.max)]

                resp = await post_on_its_own_connection(client, f"{API_BASE}/transactions/promote-suggest", params={"tolerance_days": 7}, json=batch, timeout=TIMEOUT)
                if resp.status_code != 200:
                    alone: dict[str, int] = {}
                    for edge in CALENDAR_EDGES:
                        probe = await post_on_its_own_connection(client, f"{API_BASE}/transactions/promote-suggest", params={"tolerance_days": 7}, json=[deposit_input(-1, broker_b, edge)], timeout=TIMEOUT)
                        alone[edge.isoformat()] = probe.status_code
                    pytest.fail(
                        f"W-B71: promote-suggest answered HTTP {resp.status_code} ({resp.text[:200]}) to a batch with an input dated 0001-01-01 and one dated 9999-12-31 at tolerance_days=7, next to an ordinary input dated {WINDOW_DAY}; each edge input alone: {alone}. promote_suggest_bulk computes date ∓ timedelta(days=7), which raises OverflowError (a 500) past the calendar, so the whole batch loses its suggestions; a window at the calendar's edge must be cut there (shift_date, saturating at date.min / date.max)",
                        pytrace=False,
                    )
                results = resp.json()["results"]
                assert sorted(results) == ["-1", "-2", "-3"], f"One entry per input expected: {sorted(results)}"
                assert (results["-2"], results["-3"]) == ([], []), f"Nothing is stored within 7 days of 0001-01-01 or of 9999-12-31, so the edge inputs have no candidate: {results}"
                found = candidate_ids(results, -1)
                assert found == inside, f"Next to the edge inputs, the DEPOSIT dated {WINDOW_DAY} on broker {broker_b} must still be offered the WITHDRAWALs 0 and 7 days away {inside}, never those 8 days away {[rows[offset] for offset in WINDOW_OUTSIDE]}; candidates {found} (rows by offset {rows})"
                print_success("Suggest: the window is cut at the calendar's edges, the batch keeps its suggestions ✓")
            finally:
                cleanup_problems = await delete_owned(client, broker_ids=broker_ids, asset_ids=[])
            assert cleanup_problems == [], f"Cleanup of the test's brokers: {cleanup_problems}"


# ============================================================================
# B4 — EDITS OF ROWS STORED WITHOUT A COST BASIS (N2)
# ============================================================================


def write_legacy_cost_rows(*, user_id: int, source_broker: int, dest_broker: int, asset_id: int, day: str, marker: str) -> dict[str, int]:
    """Write a TRANSFER pair and an ADJUSTMENT +5 without cost basis, as a version before the mandatory cost stored them.

    Through the lane-database helper ``test_db/legacy_cost_rows.py`` — the one the E2E data-quality spec runs as a
    script — called in-process: same lane (TEST_PORT / LIBREFOLIO_TEST_DATA_DIR, exported by the runner), same guards
    (this lane's test database only, both brokers owned by ``user_id``), one database transaction. TRANSFER 4 units of
    ``asset_id`` from ``source_broker`` to ``dest_broker`` and ADJUSTMENT +5 of it at ``dest_broker``, all on ``day``:
    amount 0, no currency, no cost basis; every description carries ``marker`` (the helper gives each leg its own).
    Returns the helper's three ids: ``transfer_out``, ``transfer_in``, ``adjustment_in``.
    """
    from backend.test_scripts.test_db import legacy_cost_rows  # noqa: PLC0415 — imported where used: the module runs setup_test_database() on import, which this one test needs and the collection of the whole file does not

    argv = ["--user-id", str(user_id), "--source-broker", str(source_broker), "--dest-broker", str(dest_broker), "--transfer-asset", str(asset_id), "--adjustment-asset", str(asset_id), "--date", day, "--marker", marker]
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        exit_code = legacy_cost_rows.main(argv)
    assert exit_code == 0, f"legacy_cost_rows refused, exit {exit_code}: {stderr.getvalue()}"
    lines = stdout.getvalue().strip().splitlines()
    assert len(lines) == 1, f"legacy_cost_rows prints one line of JSON; it printed {stdout.getvalue()!r}"
    return json.loads(lines[0])


async def delete_owned(client: httpx.AsyncClient, *, broker_ids: list[int], asset_ids: list[int]) -> list[str]:
    """Delete what a test created, by id: each broker with force, one request each as the E2E data-quality teardown
    does (their transactions go with them, rows written by ``legacy_cost_rows`` included), then the assets, which a
    remaining transaction would block.

    Returns the problems instead of raising, so that a failed cleanup never hides the test's own failure.
    """
    problems: list[str] = []
    try:
        for broker_id in broker_ids:
            resp = await client.delete(f"{API_BASE}/brokers", params={"ids": [broker_id], "force": "true"}, timeout=TIMEOUT)
            if resp.status_code != 200 or not any(item["id"] == broker_id and item["success"] for item in resp.json()["results"]):
                problems.append(f"broker {broker_id} not deleted: HTTP {resp.status_code} {resp.text}")
        if asset_ids:
            resp = await client.delete(f"{API_BASE}/assets", params={"asset_ids": asset_ids}, timeout=TIMEOUT)
            deleted = {item["asset_id"] for item in resp.json()["results"] if item["success"]} if resp.status_code == 200 else set()
            problems.extend(f"asset {asset_id} not deleted: HTTP {resp.status_code} {resp.text}" for asset_id in asset_ids if asset_id not in deleted)
    except httpx.HTTPError as exc:
        problems.append(f"cleanup request failed: {exc!r}")
    return problems


@pytest.mark.asyncio
class TestRowsStoredWithoutCostBasis:
    @pytest.fixture(autouse=True)
    def server(self, test_server):
        yield

    async def test_legacy_rows_description_only_update_commits(self):
        """B4.1 — RED until N2: a notes-only edit of rows an older version stored without a cost basis commits.

        The rows are ``legacy_cost_rows``': a TRANSFER pair (−4 / +4) and an ADJUSTMENT +5, amount 0, no currency, no
        cost basis. The edit sends a new description, and nothing else, for all three — both legs of the pair alike,
        as a pair keeps one description. It changes no type, quantity or cost: N2 lets it commit and repairs nothing.
        Today ``_check_update_cost_basis`` checks every update, and refuses the receiving leg (update 1) and the
        ADJUSTMENT (update 2) with ``costBasisRequired``: ``committed: false``. Service-level twin, with tags and
        both shapes apart: ``test_services/test_transaction_cost_basis_rule.py``.
        """
        print_section("B4.1 — Notes-only edit of rows stored without a cost basis → committed (N2)")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            me = await client.get(f"{API_BASE}/auth/me", timeout=TIMEOUT)
            assert me.status_code == 200, me.text
            user_id = me.json()["user"]["id"]
            broker_ids: list[int] = []
            asset_ids: list[int] = []
            cleanup_problems: list[str] = []
            try:
                broker_src = await create_broker(client, "LegacyCbSrc")
                broker_ids.append(broker_src)
                broker_dst = await create_broker(client, "LegacyCbDst")
                broker_ids.append(broker_dst)
                asset_id = await get_or_create_asset(client, "LegacyCbAsset")
                asset_ids.append(asset_id)
                # The source holds 10 units before the legacy transfer takes 4: the edit's balance replay re-reads that day.
                await create_standalone_tx(client, broker_src, "BUY", asset_id=asset_id, quantity="10", cash={"code": "USD", "amount": "-1000"}, tx_date="2026-03-01")
                marker = f"B4.1 legacy-cost {uuid.uuid4().hex}"
                legacy = write_legacy_cost_rows(user_id=user_id, source_broker=broker_src, dest_broker=broker_dst, asset_id=asset_id, day="2026-03-10", marker=marker)
                notes = f"{marker} notes edited"

                resp = await client.post(
                    f"{API_BASE}/transactions/commit",
                    json={"updates": [{"id": legacy[key], "description": notes} for key in ("transfer_out", "transfer_in", "adjustment_in")]},
                    timeout=TIMEOUT,
                )
                assert resp.status_code == 200, resp.text
                data = resp.json()
                if not data["committed"]:
                    pytest.fail(f"N2: a notes-only edit of rows stored without a cost basis (TRANSFER out id={legacy['transfer_out']}, in id={legacy['transfer_in']}, ADJUSTMENT +5 id={legacy['adjustment_in']}) changes no type, quantity or cost and must commit; it was refused: {data['issues']}")

                rows_resp = await client.get(f"{API_BASE}/transactions", params={"ids": list(legacy.values())}, timeout=TIMEOUT)
                assert rows_resp.status_code == 200, rows_resp.text
                by_id = {tx["id"]: tx for tx in rows_resp.json()}
                for key, tx_id in legacy.items():
                    tx = by_id.get(tx_id)
                    assert tx is not None, f"{key} id={tx_id} not found after the commit: {rows_resp.json()}"
                    assert tx["description"] == notes, f"{key} id={tx_id}: description {tx['description']!r} after a committed notes edit"
                for key in ("transfer_in", "adjustment_in"):
                    assert by_id[legacy[key]]["cost_basis_override"] is None, f"N2 repairs nothing: {key} id={legacy[key]} now has cost_basis_override={by_id[legacy[key]]['cost_basis_override']}"
                print_success("Notes-only edit of rows stored without a cost basis → committed, still no cost basis ✓")
            finally:
                cleanup_problems = await delete_owned(client, broker_ids=broker_ids, asset_ids=asset_ids)
            assert cleanup_problems == [], f"Cleanup of the test's brokers and asset: {cleanup_problems}"

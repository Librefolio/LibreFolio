"""
Transaction API Tests.

Tests for Transaction endpoints:
- POST /transactions: Bulk create transactions
- GET /transactions: Query transactions with filters
- GET /transactions/{id}: Get single transaction
- GET /transactions/types: Get transaction type metadata
- PATCH /transactions: Bulk update transactions
- DELETE /transactions: Bulk delete transactions

See checklist: 01_test_broker_transaction_subsystem.md - Category 5
Reference: backend/app/api/v1/transactions.py
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import Optional

import httpx
import pytest

import backend.app.api.v1.transactions as transactions_api
from backend.app.config import get_settings
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_info, print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def unique_username() -> str:
    """Generate unique username for test user."""
    return f"tx_test_{int(date.today().toordinal())}_{uuid.uuid4().hex[:8]}"


async def create_test_user(client: httpx.AsyncClient) -> tuple[str, str, Optional[str]]:
    """
    Create a test user and return (username, email, session_cookie).
    Also sets session cookie on the client.
    """
    username = unique_username()
    email = f"{username}@test.com"
    password = "TestPass123!"

    # Register
    resp = await client.post(
        f"{API_BASE}/auth/register",
        json={"username": username, "email": email, "password": password},
        timeout=TIMEOUT,
    )

    if resp.status_code != 201:
        return username, email, None

    # Login
    login_resp = await client.post(f"{API_BASE}/auth/login", json={"username": username, "password": password}, timeout=TIMEOUT)

    session_cookie = login_resp.cookies.get("session")
    if session_cookie:
        client.cookies.set("session", session_cookie)

    return username, email, session_cookie


# ============================================================================
# PYTEST FIXTURES
# ============================================================================


@pytest.fixture(scope="module")
def test_server():
    """
    Start test server once for all tests in this module.
    """
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


@pytest.fixture(scope="module")
def test_broker_id(test_server) -> int:
    """Create a test broker and return its ID."""
    import asyncio  # noqa: PLC0415 — test setup — imports after sys.path/db config

    async def create_broker():
        async with httpx.AsyncClient() as client:
            # First authenticate
            await create_test_user(client)

            # Now create broker
            unique_name = f"API Test Broker {uuid.uuid4().hex[:8]}"
            payload = [{"name": unique_name, "allow_cash_overdraft": True}]
            response = await client.post(
                f"{API_BASE}/brokers",
                json=payload,
                timeout=TIMEOUT,
            )
            assert response.status_code == 200, f"Failed to create broker: {response.text}"
            data = response.json()

            # Check if creation was successful
            if data["results"] and data["results"][0]["success"]:
                return data["results"][0]["broker_id"]

            # If creation failed, try to get an existing broker
            list_response = await client.get(f"{API_BASE}/brokers", timeout=TIMEOUT)
            if list_response.status_code == 200:
                brokers = list_response.json()
                if brokers:
                    return brokers[0]["id"]

            pytest.fail(f"Could not create or find broker: {data}")

    return asyncio.run(create_broker())


@pytest.fixture(scope="module")
def test_asset_id(test_server):
    """Create an asset owned by this module, yield its ID, delete it at teardown.

    Assets are global rows: the fixture never borrows an existing one. DELETE
    /assets refuses an asset that still has transactions, so every test using
    this fixture must delete the transactions it creates on it.
    """
    import asyncio  # noqa: PLC0415 — test setup — imports after sys.path/db config

    async def create_asset() -> tuple[int, str]:
        async with httpx.AsyncClient() as client:
            _, _, session_cookie = await create_test_user(client)
            assert session_cookie, "Could not authenticate the fixture user"

            payload = [
                {
                    "display_name": f"API Test Stock {uuid.uuid4().hex[:8]}",
                    "asset_type": "STOCK",
                    "currency": "EUR",
                }
            ]
            response = await client.post(
                f"{API_BASE}/assets",
                json=payload,
                timeout=TIMEOUT,
            )
            assert response.status_code == 201, f"Failed to create asset: {response.status_code} {response.text}"
            result = response.json()["results"][0]
            assert result["success"], f"Could not create test asset: {result}"
            return result["asset_id"], session_cookie

    async def delete_asset(asset_id: int, session_cookie: str) -> None:
        async with httpx.AsyncClient() as client:
            # Same user that created it: any authenticated user may delete an asset
            client.cookies.set("session", session_cookie)
            response = await client.delete(
                f"{API_BASE}/assets",
                params={"asset_ids": [asset_id]},
                timeout=TIMEOUT,
            )
            assert response.status_code == 200, f"Failed to delete asset {asset_id}: {response.status_code} {response.text}"
            results = response.json()["results"]
            assert [item["asset_id"] for item in results] == [asset_id], f"Unexpected delete results: {results}"
            assert all(item["success"] for item in results), f"Could not delete test asset {asset_id}: {results}"

    asset_id, session_cookie = asyncio.run(create_asset())
    yield asset_id
    asyncio.run(delete_asset(asset_id, session_cookie))


# ============================================================================
# 5.1 TRANSACTION API - CREATE
# ============================================================================


@pytest.mark.asyncio
async def test_post_transactions_single(test_server, test_broker_id):
    """TX-A-001: POST /transactions with 1 item."""
    print_section("Test TX-A-001: POST /transactions - single")

    async with httpx.AsyncClient() as client:
        # Authenticate first
        await create_test_user(client)

        # Create own broker for this test
        unique_name = f"TX Single Test Broker {uuid.uuid4().hex[:8]}"
        br_resp = await client.post(
            f"{API_BASE}/brokers",
            json=[{"name": unique_name, "allow_cash_overdraft": True}],
            timeout=TIMEOUT,
        )
        assert br_resp.status_code == 200
        broker_id = br_resp.json()["results"][0]["broker_id"]

        payload = [
            {
                "broker_id": broker_id,
                "type": "DEPOSIT",
                "date": date.today().isoformat(),
                "cash": {"code": "EUR", "amount": "1000"},
            }
        ]

        response = await client.post(
            f"{API_BASE}/transactions/commit",
            json={"creates": payload},
            timeout=TIMEOUT,
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert data["committed"] is True
        assert data["results"][0]["status"] == "success"
        assert data["results"][0]["ids"][0] is not None

        print_success("✓ Created 1 transaction successfully")


@pytest.mark.asyncio
async def test_post_transactions_bulk(test_server, test_broker_id):
    """TX-A-002: POST /transactions with 3 items."""
    print_section("Test TX-A-002: POST /transactions - bulk")

    async with httpx.AsyncClient() as client:
        # Authenticate first
        await create_test_user(client)

        # Create own broker for this test
        unique_name = f"TX Bulk Test Broker {uuid.uuid4().hex[:8]}"
        br_resp = await client.post(
            f"{API_BASE}/brokers",
            json=[{"name": unique_name, "allow_cash_overdraft": True}],
            timeout=TIMEOUT,
        )
        assert br_resp.status_code == 200
        broker_id = br_resp.json()["results"][0]["broker_id"]

        payload = [
            {
                "broker_id": broker_id,
                "type": "DEPOSIT",
                "date": date.today().isoformat(),
                "cash": {"code": "EUR", "amount": "5000"},
            },
            {
                "broker_id": broker_id,
                "type": "DEPOSIT",
                "date": date.today().isoformat(),
                "cash": {"code": "USD", "amount": "3000"},
            },
            {
                "broker_id": broker_id,
                "type": "WITHDRAWAL",
                "date": date.today().isoformat(),
                "cash": {"code": "EUR", "amount": "-500"},
            },
        ]

        response = await client.post(
            f"{API_BASE}/transactions/commit",
            json={"creates": payload},
            timeout=TIMEOUT,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["committed"] is True

        print_success("✓ Created 3 transactions successfully")


@pytest.mark.asyncio
async def test_post_transactions_validation_error(test_server, test_broker_id):
    """TX-A-003: POST /transactions with invalid item returns 422."""
    print_section("Test TX-A-003: POST /transactions - validation error")

    async with httpx.AsyncClient() as client:
        # Authenticate first
        await create_test_user(client)

        # Create own broker for this test
        unique_name = f"TX Validation Test Broker {uuid.uuid4().hex[:8]}"
        br_resp = await client.post(
            f"{API_BASE}/brokers",
            json=[{"name": unique_name, "allow_cash_overdraft": True}],
            timeout=TIMEOUT,
        )
        assert br_resp.status_code == 200
        broker_id = br_resp.json()["results"][0]["broker_id"]

        # Missing required cash for DEPOSIT
        payload = [
            {
                "broker_id": broker_id,
                "type": "DEPOSIT",
                "date": date.today().isoformat(),
                # cash is missing - required for DEPOSIT
            }
        ]

        response = await client.post(
            f"{API_BASE}/transactions/commit",
            json={"creates": payload},
            timeout=TIMEOUT,
        )

        # Unified batch pipeline: schema errors are collected into issues, not 422
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["committed"] is False, f"Expected committed=False for missing cash. Got: {data}"
        assert len(data.get("issues", [])) > 0, f"Expected issues for missing cash. Got: {data}"

        print_success("✓ Got committed=False with issues for validation error")


@pytest.mark.asyncio
async def test_post_transactions_balance_error(test_server):
    """TX-A-004: POST /transactions causing overdraft returns errors in response."""
    print_section("Test TX-A-004: POST /transactions - balance error")

    async with httpx.AsyncClient() as client:
        # First authenticate
        await create_test_user(client)

        # Create a broker with overdraft disabled
        unique_name = f"No Overdraft Broker {uuid.uuid4().hex[:8]}"
        broker_payload = [
            {
                "name": unique_name,
                "allow_cash_overdraft": False,
            }
        ]
        broker_resp = await client.post(
            f"{API_BASE}/brokers",
            json=broker_payload,
            timeout=TIMEOUT,
        )
        broker_data = broker_resp.json()
        assert broker_data["results"][0]["success"], f"Failed to create broker: {broker_data}"
        broker_id = broker_data["results"][0]["broker_id"]

        # Try to withdraw without deposit (should cause overdraft error)
        payload = [
            {
                "broker_id": broker_id,
                "type": "WITHDRAWAL",
                "date": date.today().isoformat(),
                "cash": {"code": "EUR", "amount": "-500"},
            }
        ]

        response = await client.post(
            f"{API_BASE}/transactions/commit",
            json={"creates": payload},
            timeout=TIMEOUT,
        )

        # The endpoint returns 200 with committed=false and issues when balance validation fails
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        # Unified batch: committed=false and issues list populated on balance violation
        assert data["committed"] is False, f"Expected committed=False for overdraft. Got: {data}"
        assert len(data.get("issues", [])) > 0, f"Expected issues for overdraft. Got: {data}"

        print_success("✓ Got balance/access error in response as expected")


# ============================================================================
# 5.2 TRANSACTION API - READ
# ============================================================================


@pytest.mark.asyncio
async def test_get_transactions(test_server, test_broker_id):
    """TX-A-010: GET /transactions returns list."""
    print_section("Test TX-A-010: GET /transactions")

    async with httpx.AsyncClient() as client:
        # Authenticate first
        await create_test_user(client)

        # Create broker with some transactions
        unique_name = f"TX Get Test Broker {uuid.uuid4().hex[:8]}"
        br_resp = await client.post(
            f"{API_BASE}/brokers",
            json=[{"name": unique_name, "allow_cash_overdraft": True}],
            timeout=TIMEOUT,
        )
        assert br_resp.status_code == 200
        broker_id = br_resp.json()["results"][0]["broker_id"]

        # Create a transaction
        await client.post(
            f"{API_BASE}/transactions/commit",
            json={
                "creates": [
                    {
                        "broker_id": broker_id,
                        "type": "DEPOSIT",
                        "date": date.today().isoformat(),
                        "cash": {"code": "EUR", "amount": "1000"},
                    }
                ]
            },
            timeout=TIMEOUT,
        )

        response = await client.get(
            f"{API_BASE}/transactions",
            params={"broker_id": broker_id},
            timeout=TIMEOUT,
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        print_success(f"✓ Got {len(data)} transactions")


@pytest.mark.asyncio
async def test_get_transactions_with_filters(test_server, test_broker_id):
    """TX-A-011: GET /transactions with filters."""
    print_section("Test TX-A-011: GET /transactions - with filters")

    async with httpx.AsyncClient() as client:
        # Authenticate first
        await create_test_user(client)

        # Create broker with transactions
        unique_name = f"TX Filter Test Broker {uuid.uuid4().hex[:8]}"
        br_resp = await client.post(
            f"{API_BASE}/brokers",
            json=[{"name": unique_name, "allow_cash_overdraft": True}],
            timeout=TIMEOUT,
        )
        assert br_resp.status_code == 200
        broker_id = br_resp.json()["results"][0]["broker_id"]

        # Create transactions
        await client.post(
            f"{API_BASE}/transactions/commit",
            json={
                "creates": [
                    {
                        "broker_id": broker_id,
                        "type": "DEPOSIT",
                        "date": date.today().isoformat(),
                        "cash": {"code": "EUR", "amount": "1000"},
                    },
                    {
                        "broker_id": broker_id,
                        "type": "WITHDRAWAL",
                        "date": date.today().isoformat(),
                        "cash": {"code": "EUR", "amount": "-100"},
                    },
                ]
            },
            timeout=TIMEOUT,
        )

        response = await client.get(
            f"{API_BASE}/transactions",
            params={
                "broker_id": broker_id,
                "types": ["DEPOSIT"],
            },
            timeout=TIMEOUT,
        )

        assert response.status_code == 200
        data = response.json()

        # All should be DEPOSIT
        for tx in data:
            assert tx["type"] == "DEPOSIT"

        print_success(f"✓ Filtered to {len(data)} DEPOSIT transactions")


@pytest.mark.asyncio
async def test_get_transactions_with_date_range_and_abs_amount_filters(monkeypatch: pytest.MonkeyPatch):
    """TX-A-011b: query_transactions builds date range and ABS(amount) filters."""
    print_section("Test TX-A-011b: GET /transactions - date range + abs amount")

    captured: dict = {}

    async def fake_query(self, params, user_id):
        captured["params"] = params
        captured["user_id"] = user_id
        return ["ok"]

    monkeypatch.setattr(transactions_api, "parse_ISO_date", lambda value: value)
    monkeypatch.setattr(
        transactions_api,
        "TransactionService",
        type("FakeTransactionService", (), {"__init__": lambda self, session: None, "query": fake_query}),
    )

    result = await transactions_api.query_transactions(
        broker_id=17,
        asset_id=None,
        types=None,
        date_start="2026-02-05",
        date_end="2026-02-15",
        tags=None,
        currency="EUR",
        ids=None,
        limit=None,
        offset=0,
        amount_abs_min=Decimal("150"),
        amount_abs_max=Decimal("250"),
        only_unlinked=False,
        exclude_ids=None,
        asset_event_id=None,
        session=object(),
        current_user=SimpleNamespace(id=7),
    )

    assert result == ["ok"]
    assert captured["user_id"] == 7
    assert captured["params"].broker_id == 17
    assert captured["params"].date_range.start == date(2026, 2, 5)
    assert captured["params"].date_range.end == date(2026, 2, 15)
    assert captured["params"].currency == "EUR"
    assert captured["params"].amount_abs_min == Decimal("150")
    assert captured["params"].amount_abs_max == Decimal("250")

    print_success("✓ Date range + ABS(amount) filters mapped into TXQueryParams")


@pytest.mark.asyncio
async def test_get_transactions_with_date_start_only_and_unlinked_exclusion(monkeypatch: pytest.MonkeyPatch):
    """TX-A-011c: query_transactions handles date_start-only, only_unlinked, exclude_ids."""
    print_section("Test TX-A-011c: GET /transactions - date_start + only_unlinked + exclude_ids")

    captured: dict = {}

    async def fake_query(self, params, user_id):
        captured["params"] = params
        captured["user_id"] = user_id
        return []

    monkeypatch.setattr(transactions_api, "parse_ISO_date", lambda value: value)
    monkeypatch.setattr(
        transactions_api,
        "TransactionService",
        type("FakeTransactionService", (), {"__init__": lambda self, session: None, "query": fake_query}),
    )

    result = await transactions_api.query_transactions(
        broker_id=23,
        asset_id=None,
        types=None,
        date_start="2026-03-02",
        date_end=None,
        tags=None,
        currency=None,
        ids=None,
        limit=10,
        offset=4,
        amount_abs_min=None,
        amount_abs_max=None,
        only_unlinked=True,
        exclude_ids=[101, 102],
        asset_event_id=None,
        session=object(),
        current_user=SimpleNamespace(id=9),
    )

    assert result == []
    assert captured["user_id"] == 9
    assert captured["params"].broker_id == 23
    assert captured["params"].date_range.start == date(2026, 3, 2)
    assert captured["params"].date_range.end is None
    assert captured["params"].only_unlinked is True
    assert captured["params"].exclude_ids == [101, 102]
    assert captured["params"].limit == 10
    assert captured["params"].offset == 4

    print_success("✓ date_start-only + only_unlinked + exclude_ids mapped into TXQueryParams")


@pytest.mark.asyncio
async def test_get_transactions_pagination(test_server, test_broker_id):
    """TX-A-012: GET /transactions with pagination."""
    print_section("Test TX-A-012: GET /transactions - pagination")

    async with httpx.AsyncClient() as client:
        # Authenticate first
        await create_test_user(client)

        # Create broker with transactions
        unique_name = f"TX Pagination Test Broker {uuid.uuid4().hex[:8]}"
        br_resp = await client.post(
            f"{API_BASE}/brokers",
            json=[{"name": unique_name, "allow_cash_overdraft": True}],
            timeout=TIMEOUT,
        )
        assert br_resp.status_code == 200
        broker_id = br_resp.json()["results"][0]["broker_id"]

        # Create several transactions
        await client.post(
            f"{API_BASE}/transactions/commit",
            json={
                "creates": [
                    {
                        "broker_id": broker_id,
                        "type": "DEPOSIT",
                        "date": date.today().isoformat(),
                        "cash": {"code": "EUR", "amount": "100"},
                    },
                    {
                        "broker_id": broker_id,
                        "type": "DEPOSIT",
                        "date": date.today().isoformat(),
                        "cash": {"code": "EUR", "amount": "200"},
                    },
                    {
                        "broker_id": broker_id,
                        "type": "DEPOSIT",
                        "date": date.today().isoformat(),
                        "cash": {"code": "EUR", "amount": "300"},
                    },
                ]
            },
            timeout=TIMEOUT,
        )

        # Get all
        all_response = await client.get(
            f"{API_BASE}/transactions",
            params={"broker_id": broker_id, "limit": 100},
            timeout=TIMEOUT,
        )
        all_data = all_response.json()

        if len(all_data) >= 2:
            # Get with offset
            paginated = await client.get(
                f"{API_BASE}/transactions",
                params={"broker_id": broker_id, "limit": 1, "offset": 1},
                timeout=TIMEOUT,
            )
            paginated_data = paginated.json()

            assert len(paginated_data) <= 1
            print_success("✓ Pagination works correctly")
        else:
            print_info("Skipping pagination test - not enough transactions")


@pytest.mark.asyncio
async def test_get_transaction_by_id(test_server, test_broker_id):
    """TX-A-013: GET /transactions?ids={id} returns single transaction (replacement for removed /{id} route)."""
    print_section("Test TX-A-013: GET /transactions?ids={id}")

    async with httpx.AsyncClient() as client:
        # Authenticate first
        await create_test_user(client)

        # Create broker
        unique_name = f"TX GetById Test Broker {uuid.uuid4().hex[:8]}"
        br_resp = await client.post(
            f"{API_BASE}/brokers",
            json=[{"name": unique_name, "allow_cash_overdraft": True}],
            timeout=TIMEOUT,
        )
        assert br_resp.status_code == 200
        broker_id = br_resp.json()["results"][0]["broker_id"]

        # Create a transaction
        payload = [
            {
                "broker_id": broker_id,
                "type": "DEPOSIT",
                "date": date.today().isoformat(),
                "cash": {"code": "EUR", "amount": "100"},
            }
        ]
        create_resp = await client.post(
            f"{API_BASE}/transactions/commit",
            json={"creates": payload},
            timeout=TIMEOUT,
        )
        tx_id = create_resp.json()["results"][0]["ids"][0]

        # Get by ID via ?ids=N
        response = await client.get(
            f"{API_BASE}/transactions",
            params={"ids": [tx_id]},
            timeout=TIMEOUT,
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) and len(data) == 1
        assert data[0]["id"] == tx_id

        print_success(f"✓ Got transaction {tx_id} via ?ids")


@pytest.mark.asyncio
async def test_get_transaction_not_found(test_server):
    """TX-A-014: GET /transactions?ids=... returns empty list when no match (replaces 404 of old /{id})."""
    print_section("Test TX-A-014: GET /transactions?ids=... - not found")

    async with httpx.AsyncClient() as client:
        # Authenticate first
        await create_test_user(client)

        response = await client.get(
            f"{API_BASE}/transactions",
            params={"ids": [999999]},
            timeout=TIMEOUT,
        )

        # New behavior: empty list, not 404 (the route /{tx_id} has been removed).
        assert response.status_code == 200
        assert response.json() == []

        print_success("✓ Got empty list as expected for missing ID")


@pytest.mark.asyncio
async def test_legacy_tx_id_route_is_removed(test_server):
    """TX-A-014b: GET /transactions/{id} must now 404 (route removed, not a live tx)."""
    print_section("Test TX-A-014b: GET /transactions/{id} removed")

    async with httpx.AsyncClient() as client:
        await create_test_user(client)
        response = await client.get(
            f"{API_BASE}/transactions/999999",
            timeout=TIMEOUT,
        )
        # FastAPI returns 404 because no route matches the path.
        assert response.status_code == 404

        print_success("✓ Legacy /{tx_id} route returns 404")


@pytest.mark.asyncio
async def test_get_transaction_types(test_server):
    """TX-A-015: GET /transactions/types returns type metadata."""
    print_section("Test TX-A-015: GET /transactions/types")

    async with httpx.AsyncClient() as client:
        # Authenticate first
        await create_test_user(client)

        response = await client.get(
            f"{API_BASE}/transactions/types",
            timeout=TIMEOUT,
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "transaction_types" in data
        assert "event_types" in data

        tx_types = data["transaction_types"]
        assert isinstance(tx_types, list)
        assert len(tx_types) > 0

        # Each tx type item should have metadata fields
        for item in tx_types:
            assert "code" in item  # e.g., "BUY", "SELL"
            assert "name" in item  # e.g., "Buy", "Sell"
            assert "description" in item
            assert "icon_slug" in item  # e.g., "buy", "sell"
            # cost_basis_mode must be present and valid
            assert "cost_basis_mode" in item, f"Missing cost_basis_mode for {item.get('code')}"
            assert item["cost_basis_mode"] in ("forbidden", "optional", "required_qty_pos"), f"Invalid cost_basis_mode '{item['cost_basis_mode']}' for {item['code']}"

        # Verify specific cost_basis rules
        types_by_code = {t["code"]: t for t in tx_types}
        # BUY: forbidden, no pair
        assert types_by_code["BUY"]["cost_basis_mode"] == "forbidden"
        assert types_by_code["BUY"].get("cost_basis_pair") is None
        # ADJUSTMENT: required_qty_pos, no pair
        assert types_by_code["ADJUSTMENT"]["cost_basis_mode"] == "required_qty_pos"
        assert types_by_code["ADJUSTMENT"].get("cost_basis_pair") is None
        # TRANSFER: forbidden standalone, pair = [forbidden, required_qty_pos]
        assert types_by_code["TRANSFER"]["cost_basis_mode"] == "forbidden"
        assert types_by_code["TRANSFER"]["cost_basis_pair"] == ["forbidden", "required_qty_pos"]

        # Event types should have emoji + compatible_tx_types
        ev_types = data["event_types"]
        assert isinstance(ev_types, list)
        assert len(ev_types) > 0
        for item in ev_types:
            assert "code" in item
            assert "emoji" in item
            assert "compatible_tx_types" in item

        print_success(f"✓ Got {len(tx_types)} transaction types, {len(ev_types)} event types")


@pytest.mark.asyncio
async def test_get_transaction_types_direct():
    """TX-A-015b: get_transaction_types direct call returns both metadata lists."""
    print_section("Test TX-A-015b: GET /transactions/types direct")

    result = await transactions_api.get_transaction_types(_current_user=SimpleNamespace(id=1))

    assert len(result.transaction_types) > 0
    assert len(result.event_types) > 0
    assert any(item.code == "BUY" for item in result.transaction_types)
    assert any(item.code == "DIVIDEND" for item in result.event_types)

    print_success("✓ Direct get_transaction_types call returned metadata")


# ============================================================================
# 5.3 TRANSACTION API - UPDATE
# ============================================================================


@pytest.mark.asyncio
async def test_patch_transactions(test_server, test_broker_id):
    """TX-A-020: PATCH /transactions updates transaction."""
    print_section("Test TX-A-020: PATCH /transactions")

    async with httpx.AsyncClient() as client:
        # Authenticate first
        await create_test_user(client)

        # Create broker
        unique_name = f"TX Patch Test Broker {uuid.uuid4().hex[:8]}"
        br_resp = await client.post(
            f"{API_BASE}/brokers",
            json=[{"name": unique_name, "allow_cash_overdraft": True}],
            timeout=TIMEOUT,
        )
        assert br_resp.status_code == 200
        broker_id = br_resp.json()["results"][0]["broker_id"]

        # Create a transaction
        payload = [
            {
                "broker_id": broker_id,
                "type": "DEPOSIT",
                "date": date.today().isoformat(),
                "cash": {"code": "EUR", "amount": "100"},
            }
        ]
        create_resp = await client.post(
            f"{API_BASE}/transactions/commit",
            json={"creates": payload},
            timeout=TIMEOUT,
        )
        tx_id = create_resp.json()["results"][0]["ids"][0]

        # Update it
        update_payload = [
            {
                "id": tx_id,
                "description": "Updated via API test",
            }
        ]
        response = await client.post(
            f"{API_BASE}/transactions/commit",
            json={"updates": update_payload},
            timeout=TIMEOUT,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["committed"] is True

        print_success("✓ Updated transaction successfully")


@pytest.mark.asyncio
async def test_patch_transactions_not_found(test_server):
    """TX-A-021: PATCH /transactions with invalid ID returns success=False."""
    print_section("Test TX-A-021: PATCH /transactions - not found")

    async with httpx.AsyncClient() as client:
        # Authenticate first
        await create_test_user(client)

        update_payload = [
            {
                "id": 999999,
                "description": "Should fail",
            }
        ]
        response = await client.post(
            f"{API_BASE}/transactions/commit",
            json={"updates": update_payload},
            timeout=TIMEOUT,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["committed"] is False
        assert len(data.get("issues", [])) > 0

        print_success("✓ Got committed=False for invalid ID")


# ============================================================================
# 5.4 TRANSACTION API - DELETE
# ============================================================================


@pytest.mark.asyncio
async def test_delete_transactions(test_server, test_broker_id):
    """TX-A-030: DELETE /transactions deletes transactions."""
    print_section("Test TX-A-030: DELETE /transactions")

    async with httpx.AsyncClient() as client:
        # Authenticate first
        await create_test_user(client)

        # Create broker
        unique_name = f"TX Delete Test Broker {uuid.uuid4().hex[:8]}"
        br_resp = await client.post(
            f"{API_BASE}/brokers",
            json=[{"name": unique_name, "allow_cash_overdraft": True}],
            timeout=TIMEOUT,
        )
        assert br_resp.status_code == 200
        broker_id = br_resp.json()["results"][0]["broker_id"]

        # Create transactions to delete
        payload = [
            {
                "broker_id": broker_id,
                "type": "DEPOSIT",
                "date": date.today().isoformat(),
                "cash": {"code": "EUR", "amount": "100"},
            },
            {
                "broker_id": broker_id,
                "type": "DEPOSIT",
                "date": date.today().isoformat(),
                "cash": {"code": "EUR", "amount": "200"},
            },
        ]
        create_resp = await client.post(
            f"{API_BASE}/transactions/commit",
            json={"creates": payload},
            timeout=TIMEOUT,
        )
        tx_ids = [r["ids"][0] for r in create_resp.json()["results"]]

        # Delete them
        response = await client.post(
            f"{API_BASE}/transactions/commit",
            json={"deletes": tx_ids},
            timeout=TIMEOUT,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["committed"] is True
        delete_results = [r for r in data["results"] if r["operation"] == "delete"]
        assert len(delete_results) == 2

        print_success("✓ Deleted 2 transactions")


@pytest.mark.asyncio
async def test_delete_linked_without_pair(test_server, test_asset_id):
    """TX-A-031: DELETE only one of linked pair fails."""
    print_section("Test TX-A-031: DELETE /transactions - linked without pair")

    async with httpx.AsyncClient() as client:
        # Authenticate first
        await create_test_user(client)

        # Create source and target brokers for the transfer
        source_name = f"TX Link Source Broker {uuid.uuid4().hex[:8]}"
        target_name = f"TX Link Target Broker {uuid.uuid4().hex[:8]}"
        br_resp = await client.post(
            f"{API_BASE}/brokers",
            json=[
                {"name": source_name, "allow_cash_overdraft": True},
                {"name": target_name, "allow_cash_overdraft": True},
            ],
            timeout=TIMEOUT,
        )
        assert br_resp.status_code == 200, f"Failed to create brokers: {br_resp.status_code} {br_resp.text}"
        brokers = {result["name"]: result for result in br_resp.json()["results"]}
        assert all(brokers.get(name, {}).get("success") for name in (source_name, target_name)), f"Broker creation failed: {br_resp.text}"
        source_broker_id = brokers[source_name]["broker_id"]
        target_broker_id = brokers[target_name]["broker_id"]

        # Everything this test commits on the module's asset: deleted in `finally`,
        # so that the fixture can delete the asset at teardown.
        created_tx_ids: list[int] = []
        try:
            # First add some asset to source broker via ADJUSTMENT
            # (qty > 0 requires a cost basis, like the receiving TRANSFER leg below)
            adj_payload = [
                {
                    "broker_id": source_broker_id,
                    "asset_id": test_asset_id,
                    "type": "ADJUSTMENT",
                    "date": (date.today() - timedelta(days=1)).isoformat(),
                    "quantity": "100",
                    "cost_basis_override": {"code": "EUR", "amount": "10"},
                }
            ]
            adj_resp = await client.post(f"{API_BASE}/transactions/commit", json={"creates": adj_payload}, timeout=TIMEOUT)
            assert adj_resp.status_code == 200, f"ADJUSTMENT commit failed: {adj_resp.status_code} {adj_resp.text}"
            adj_data = adj_resp.json()
            assert adj_data["committed"] is True, f"ADJUSTMENT not committed: {adj_data['issues']}"
            created_tx_ids.extend(tx_id for result in adj_data["results"] for tx_id in result["ids"])

            # Create linked transfer
            link_uuid = f"test-link-api-{uuid.uuid4().hex[:8]}"
            transfer_payload = [
                {
                    "broker_id": source_broker_id,
                    "asset_id": test_asset_id,
                    "type": "TRANSFER",
                    "date": date.today().isoformat(),
                    "quantity": "-10",
                    "link_uuid": link_uuid,
                },
                {
                    "broker_id": target_broker_id,
                    "asset_id": test_asset_id,
                    "type": "TRANSFER",
                    "date": date.today().isoformat(),
                    "quantity": "10",
                    "link_uuid": link_uuid,
                    "cost_basis_override": {"code": "EUR", "amount": "10"},
                },
            ]
            create_resp = await client.post(
                f"{API_BASE}/transactions/commit",
                json={"creates": transfer_payload},
                timeout=TIMEOUT,
            )
            assert create_resp.status_code == 200, f"TRANSFER commit failed: {create_resp.status_code} {create_resp.text}"
            create_data = create_resp.json()
            assert create_data["committed"] is True, f"TRANSFER pair not committed: {create_data['issues']}"
            # Legs in request order (`index`): tx_ids[0] = source leg, tx_ids[1] = target leg
            legs = sorted(create_data["results"], key=lambda item: item["index"])
            tx_ids = [tx_id for leg in legs for tx_id in leg["ids"]]
            created_tx_ids.extend(tx_ids)
            assert len(tx_ids) == 2, f"Expected the two legs of the pair, got {create_data['results']}"

            # Try to delete only the first one
            response = await client.post(
                f"{API_BASE}/transactions/commit",
                json={"deletes": [tx_ids[0]]},
                timeout=TIMEOUT,
            )

            assert response.status_code == 200
            data = response.json()
            # Should fail because pair is missing
            assert data["committed"] is False
            assert len(data.get("issues", [])) > 0
            assert any("pair" in issue.get("error", "").lower() for issue in data["issues"])

            # T4: the wire contract the frontend localizes on is the structured
            # code + params, not the English text — the bulk workspace resolves
            # `transactions.errors.pairDeleteIncomplete` from these. Pin them.
            pair_issues = [i for i in data["issues"] if i.get("code") == "pairDeleteIncomplete"]
            assert pair_issues, f"expected a pairDeleteIncomplete issue, got {data['issues']}"
            assert pair_issues[0].get("params", {}).get("id") == tx_ids[0]
            assert pair_issues[0].get("params", {}).get("partnerId") == tx_ids[1]

            print_success("✓ Got error when trying to delete only one of linked pair")
        finally:
            # Both legs of the pair together (one alone is refused, as asserted
            # above) plus the ADJUSTMENT, in one batch.
            if created_tx_ids:
                cleanup_resp = await client.post(
                    f"{API_BASE}/transactions/commit",
                    json={"deletes": created_tx_ids},
                    timeout=TIMEOUT,
                )
                assert cleanup_resp.status_code == 200, f"Cleanup failed: {cleanup_resp.status_code} {cleanup_resp.text}"
                cleanup_data = cleanup_resp.json()
                assert cleanup_data["committed"] is True, f"Cleanup not committed: {cleanup_data['issues']}"


# ============================================================================
# 5.9 TRANSACTION API - partner_broker_id
# ============================================================================


@pytest.mark.asyncio
async def test_get_transactions_partner_broker_id(test_server):
    """TX-A-PBR: GET /transactions returns partner_broker_id for linked pairs."""
    print_section("Test TX-A-PBR: partner_broker_id on paired transactions")

    async with httpx.AsyncClient() as client:
        await create_test_user(client)

        # Create two brokers
        br1_name = f"PBR Source Broker {uuid.uuid4().hex[:8]}"
        br2_name = f"PBR Target Broker {uuid.uuid4().hex[:8]}"
        br1_resp = await client.post(
            f"{API_BASE}/brokers",
            json=[
                {"name": br1_name, "allow_cash_overdraft": True},
                {"name": br2_name, "allow_cash_overdraft": True},
            ],
            timeout=TIMEOUT,
        )
        assert br1_resp.status_code == 200
        results = br1_resp.json()["results"]
        broker1_id = results[0]["broker_id"]
        broker2_id = results[1]["broker_id"]

        # Create asset
        asset_payload = [
            {
                "display_name": f"PBR Test Stock {uuid.uuid4().hex[:6]}",
                "asset_type": "STOCK",
                "currency": "EUR",
            }
        ]
        asset_resp = await client.post(f"{API_BASE}/assets", json=asset_payload, timeout=TIMEOUT)
        assert asset_resp.status_code in (200, 201), f"Asset creation failed: {asset_resp.status_code} {asset_resp.text}"
        asset_id = asset_resp.json()["results"][0]["asset_id"]

        # Seed balance: BUY on broker1
        seed_payload = [
            {"broker_id": broker1_id, "type": "DEPOSIT", "date": date.today().isoformat(), "cash": {"code": "EUR", "amount": "5000"}},
            {"broker_id": broker1_id, "asset_id": asset_id, "type": "BUY", "date": date.today().isoformat(), "quantity": "20", "cash": {"code": "EUR", "amount": "-2000"}},
        ]
        seed_resp = await client.post(
            f"{API_BASE}/transactions/commit",
            json={"creates": seed_payload},
            timeout=TIMEOUT,
        )
        assert seed_resp.status_code == 200
        assert seed_resp.json()["committed"] is True

        # Create TRANSFER pair: broker1 → broker2
        link_uuid = str(uuid.uuid4())
        transfer_payload = [
            {
                "broker_id": broker1_id,
                "asset_id": asset_id,
                "type": "TRANSFER",
                "date": date.today().isoformat(),
                "quantity": "-5",
                "link_uuid": link_uuid,
            },
            {
                "broker_id": broker2_id,
                "asset_id": asset_id,
                "type": "TRANSFER",
                "date": date.today().isoformat(),
                "quantity": "5",
                "link_uuid": link_uuid,
                "cost_basis_mode": "auto",
            },
        ]
        create_resp = await client.post(
            f"{API_BASE}/transactions/commit",
            json={"creates": transfer_payload},
            timeout=TIMEOUT,
        )
        assert create_resp.status_code == 200
        assert create_resp.json()["committed"] is True
        tx_ids = [r["ids"][0] for r in create_resp.json()["results"]]
        assert len(tx_ids) == 2

        # GET /transactions with ids filter
        get_resp = await client.get(
            f"{API_BASE}/transactions",
            params={"ids": tx_ids},
            timeout=TIMEOUT,
        )
        assert get_resp.status_code == 200
        txs = get_resp.json()

        # Both transactions should have partner_broker_id
        for tx in txs:
            assert "partner_broker_id" in tx, f"TX #{tx['id']} missing partner_broker_id"
            assert tx["partner_broker_id"] is not None, f"TX #{tx['id']} partner_broker_id is null"

        # Verify cross-reference: tx on broker1 → partner_broker_id = broker2
        tx_on_b1 = [t for t in txs if t["broker_id"] == broker1_id][0]
        tx_on_b2 = [t for t in txs if t["broker_id"] == broker2_id][0]
        assert tx_on_b1["partner_broker_id"] == broker2_id
        assert tx_on_b2["partner_broker_id"] == broker1_id

        print_success("✓ partner_broker_id correctly populated for linked pair")


# ============================================================================
# PAIR DESCRIPTION/TAGS VALIDATION
# ============================================================================


@pytest.mark.asyncio
class TestPairDescriptionTagsValidation:
    """Tests for pair description/tags consistency validation (Step 2 of Plan C2)."""

    @pytest.fixture(autouse=True)
    def server(self, test_server):
        yield

    async def _setup(self, client: httpx.AsyncClient) -> tuple[int, int, int]:
        """Register, login, create 2 brokers + 1 asset. Returns (broker1_id, broker2_id, asset_id)."""
        await create_test_user(client)
        # Create 2 brokers
        resp = await client.post(
            f"{API_BASE}/brokers",
            json=[
                {"name": f"PairVal-B1-{uuid.uuid4().hex[:6]}", "allow_cash_overdraft": True, "allow_asset_shorting": True},
                {"name": f"PairVal-B2-{uuid.uuid4().hex[:6]}", "allow_cash_overdraft": True, "allow_asset_shorting": True},
            ],
            timeout=TIMEOUT,
        )
        assert resp.status_code == 200
        brokers = resp.json()["results"]
        b1 = brokers[0]["broker_id"]
        b2 = brokers[1]["broker_id"]
        # Create asset
        asset_resp = await client.post(
            f"{API_BASE}/assets",
            json=[
                {"display_name": f"PairValAsset-{uuid.uuid4().hex[:6]}", "asset_type": "STOCK", "currency": "USD"},
            ],
            timeout=TIMEOUT,
        )
        assert asset_resp.status_code in (200, 201), f"Asset creation failed: {asset_resp.status_code} {asset_resp.text}"
        asset_id = asset_resp.json()["results"][0]["asset_id"]
        return b1, b2, asset_id

    async def test_create_pair_same_description_ok(self):
        """Create a TRANSFER pair with identical description → committed=True."""
        print_section("PAIR VALIDATION: same description OK")
        async with httpx.AsyncClient() as client:
            b1, b2, asset_id = await self._setup(client)
            link = str(uuid.uuid4())
            payload = {
                "creates": [
                    {"broker_id": b1, "asset_id": asset_id, "type": "TRANSFER", "date": "2026-01-10", "quantity": "-5", "link_uuid": link, "description": "Transfer A ↔ B", "tags": ["test"]},
                    {"broker_id": b2, "asset_id": asset_id, "type": "TRANSFER", "date": "2026-01-10", "quantity": "5", "link_uuid": link, "description": "Transfer A ↔ B", "tags": ["test"], "cost_basis_override": {"code": "USD", "amount": "50"}},
                ]
            }
            resp = await client.post(f"{API_BASE}/transactions/commit", json=payload, timeout=TIMEOUT)
            assert resp.status_code == 200
            data = resp.json()
            assert data["committed"] is True, f"Expected committed=True, got issues: {data.get('issues')}"
            print_success("✓ Pair with identical description committed OK")

    async def test_create_pair_different_description_rejected(self):
        """Create a TRANSFER pair with different descriptions → rejected."""
        print_section("PAIR VALIDATION: different description rejected")
        async with httpx.AsyncClient() as client:
            b1, b2, asset_id = await self._setup(client)
            link = str(uuid.uuid4())
            payload = {
                "creates": [
                    {"broker_id": b1, "asset_id": asset_id, "type": "TRANSFER", "date": "2026-01-10", "quantity": "-5", "link_uuid": link, "description": "Description A"},
                    {"broker_id": b2, "asset_id": asset_id, "type": "TRANSFER", "date": "2026-01-10", "quantity": "5", "link_uuid": link, "description": "Description B"},
                ]
            }
            resp = await client.post(f"{API_BASE}/transactions/commit", json=payload, timeout=TIMEOUT)
            assert resp.status_code == 200
            data = resp.json()
            assert data["committed"] is False
            codes = [i["code"] for i in data.get("issues", [])]
            assert "pairDescriptionMismatch" in codes, f"Expected pairDescriptionMismatch, got {codes}"
            print_success("✓ Pair with different descriptions correctly rejected")

    async def test_create_pair_different_tags_rejected(self):
        """Create a TRANSFER pair with different tags → rejected."""
        print_section("PAIR VALIDATION: different tags rejected")
        async with httpx.AsyncClient() as client:
            b1, b2, asset_id = await self._setup(client)
            link = str(uuid.uuid4())
            payload = {
                "creates": [
                    {"broker_id": b1, "asset_id": asset_id, "type": "TRANSFER", "date": "2026-01-10", "quantity": "-5", "link_uuid": link, "tags": ["alpha", "beta"]},
                    {"broker_id": b2, "asset_id": asset_id, "type": "TRANSFER", "date": "2026-01-10", "quantity": "5", "link_uuid": link, "tags": ["alpha", "gamma"]},
                ]
            }
            resp = await client.post(f"{API_BASE}/transactions/commit", json=payload, timeout=TIMEOUT)
            assert resp.status_code == 200
            data = resp.json()
            assert data["committed"] is False
            codes = [i["code"] for i in data.get("issues", [])]
            assert "pairTagsMismatch" in codes, f"Expected pairTagsMismatch, got {codes}"
            print_success("✓ Pair with different tags correctly rejected")

    async def test_update_description_pair_consistency(self):
        """Update description on one side without partner → rejected. Update both → OK."""
        print_section("PAIR VALIDATION: update consistency")
        async with httpx.AsyncClient() as client:
            b1, b2, asset_id = await self._setup(client)
            # First create a valid pair
            link = str(uuid.uuid4())
            payload = {
                "creates": [
                    {"broker_id": b1, "asset_id": asset_id, "type": "TRANSFER", "date": "2026-01-15", "quantity": "-2", "link_uuid": link, "description": "Original desc"},
                    {"broker_id": b2, "asset_id": asset_id, "type": "TRANSFER", "date": "2026-01-15", "quantity": "2", "link_uuid": link, "description": "Original desc", "cost_basis_override": {"code": "USD", "amount": "50"}},
                ]
            }
            create_resp = await client.post(f"{API_BASE}/transactions/commit", json=payload, timeout=TIMEOUT)
            assert create_resp.status_code == 200
            assert create_resp.json()["committed"] is True
            created_ids = [r["ids"][0] for r in create_resp.json()["results"] if r["operation"] == "create"]
            assert len(created_ids) == 2

            # Update only one side → should be rejected
            update_one = {
                "updates": [
                    {"id": created_ids[0], "description": "Changed desc"},
                ]
            }
            resp1 = await client.post(f"{API_BASE}/transactions/commit", json=update_one, timeout=TIMEOUT)
            assert resp1.status_code == 200
            data1 = resp1.json()
            assert data1["committed"] is False
            codes = [i["code"] for i in data1.get("issues", [])]
            assert "pairDescriptionMismatch" in codes, f"Expected mismatch, got {codes}"

            # Update both sides → should succeed
            update_both = {
                "updates": [
                    {"id": created_ids[0], "description": "Changed desc"},
                    {"id": created_ids[1], "description": "Changed desc"},
                ]
            }
            resp2 = await client.post(f"{API_BASE}/transactions/commit", json=update_both, timeout=TIMEOUT)
            assert resp2.status_code == 200
            assert resp2.json()["committed"] is True
            print_success("✓ Pair update consistency validated (reject one-sided, accept both)")


# ============================================================================
# C-65b — REVERSE LOOKUP: GET /transactions?asset_event_id=
# ============================================================================
#
# Which transactions point at an asset event? GET /transactions?asset_event_id=<id> answers it, scoped like
# every other read to the brokers the caller can VIEW; the id is an event id, so it is > 0. Before the fix the
# parameter does not exist: FastAPI ignores an unknown query parameter, and the call returns every transaction
# the caller can see, linked or not, whatever the id.
#
# The test owns everything it reads: a fresh asset (events are scoped by asset, so the fixed dates below meet
# no other test's rows), its two DIVIDEND events, one broker and three DIVIDENDs on it. At the end the broker
# goes first (force takes the transactions that pin the events), then the asset, which cascades its events.
# Users stay, as in the rest of this module. The helpers are local copies of test_assets_events.py's on
# purpose: that module belongs to another workstream.

EVENT_LOOKUP_DAYS = (date(2024, 3, 15), date(2024, 4, 15), date(2024, 5, 15))
EVENT_LOOKUP_WINDOW = {"start": "2024-01-01", "end": "2024-12-31"}


class _EventLookupRows:
    """What the reverse-lookup test created through the API, dropped in FK-safe order at the end."""

    def __init__(self) -> None:
        self.asset_ids: list[int] = []
        self.broker_ids: list[int] = []

    async def drop(self, client: httpx.AsyncClient) -> list[str]:
        """Drop brokers, then assets. Never raises: what could not be removed is returned."""
        problems: list[str] = []
        for broker_id in self.broker_ids:
            try:
                resp = await client.delete(f"{API_BASE}/brokers", params={"ids": [broker_id], "force": True}, timeout=TIMEOUT)
                done = resp.status_code == 200 and any(r.get("id") == broker_id and r.get("success") for r in resp.json().get("results", []))
                if not done:
                    problems.append(f"broker {broker_id}: HTTP {resp.status_code} {resp.text}")
            except Exception as exc:
                problems.append(f"broker {broker_id}: {exc!r}")
        if self.asset_ids:
            try:
                resp = await client.delete(f"{API_BASE}/assets", params={"asset_ids": self.asset_ids}, timeout=TIMEOUT)
                deleted = {r["asset_id"] for r in resp.json().get("results", []) if r.get("success")} if resp.status_code == 200 else set()
                problems += [f"asset {asset_id}: HTTP {resp.status_code} {resp.text}" for asset_id in self.asset_ids if asset_id not in deleted]
            except Exception as exc:
                problems.append(f"assets {self.asset_ids}: {exc!r}")
        return problems


async def _event_lookup_asset(client: httpx.AsyncClient, owned: _EventLookupRows) -> int:
    name = f"Event Lookup {uuid.uuid4().hex}"
    resp = await client.post(f"{API_BASE}/assets", json=[{"display_name": name, "currency": "USD"}], timeout=TIMEOUT)
    assert resp.status_code in (200, 201), resp.text
    row = next(r for r in resp.json()["results"] if r["display_name"] == name)
    assert row["success"] is True, row
    owned.asset_ids.append(row["asset_id"])
    return row["asset_id"]


async def _event_lookup_dividend_events(client: httpx.AsyncClient, asset_id: int, days: tuple[date, ...]) -> dict[date, int]:
    """Seed one DIVIDEND event per day on ``asset_id`` and return {day: event id}, read back from the API."""
    points = [{"date": day.isoformat(), "type": "DIVIDEND", "value": {"code": "USD", "amount": f"{n}.00"}} for n, day in enumerate(days, start=1)]
    resp = await client.post(f"{API_BASE}/assets/events", json=[{"asset_id": asset_id, "events": points}], timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    row = next(r for r in resp.json()["results"] if r["asset_id"] == asset_id)
    assert row["count"] == len(points), row
    query = await client.post(f"{API_BASE}/assets/events/query", json=[{"asset_id": asset_id, "date_range": EVENT_LOOKUP_WINDOW}], timeout=TIMEOUT)
    assert query.status_code == 200, query.text
    events = next(item for item in query.json()["items"] if item["asset_id"] == asset_id)["events"]
    by_day: dict[date, int] = {}
    for day in days:
        matches = [event["id"] for event in events if event["date"] == day.isoformat() and event["type"] == "DIVIDEND"]
        assert len(matches) == 1, f"expected exactly one DIVIDEND on {day} for asset {asset_id}, got {events}"
        by_day[day] = matches[0]
    return by_day


async def _event_lookup_broker(client: httpx.AsyncClient, owned: _EventLookupRows) -> int:
    name = f"Event Lookup Broker {uuid.uuid4().hex}"
    resp = await client.post(f"{API_BASE}/brokers", json=[{"name": name, "allow_cash_overdraft": True}], timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    row = next(r for r in resp.json()["results"] if r["name"] == name)
    assert row["success"] is True, row
    owned.broker_ids.append(row["broker_id"])
    return row["broker_id"]


def _event_lookup_dividend(broker_id: int, asset_id: int, day: date, amount: str, event_id: Optional[int]) -> dict:
    row = {"broker_id": broker_id, "asset_id": asset_id, "type": "DIVIDEND", "date": day.isoformat(), "cash": {"code": "USD", "amount": amount}}
    if event_id is not None:
        row["asset_event_id"] = event_id
    return row


@pytest.mark.asyncio
async def test_get_transactions_filters_by_asset_event_id(test_server):
    """C-65b: GET /transactions?asset_event_id=E returns the transactions linked to E, within the caller's brokers.

    Two DIVIDEND events E1, E2 on an owned asset; on one owned broker tx1 → E1, tx2 → E2, tx3 unlinked.
    - a second user, without access to that broker, asks for E1 → nothing (the scope guard; green before the fix too);
    - the owner asks for E1 → exactly [tx1]: the whole answer is this test's own, E1 exists only here.
    Before the fix the parameter is ignored and the owner gets [tx1, tx2, tx3].
    """
    print_section("C-65b: GET /transactions?asset_event_id= — reverse lookup")
    owned = _EventLookupRows()
    async with httpx.AsyncClient() as client, httpx.AsyncClient() as stranger:
        _, _, session_cookie = await create_test_user(client)
        assert session_cookie, "Could not authenticate the owner"
        try:
            asset_id = await _event_lookup_asset(client, owned)
            day1, day2, day3 = EVENT_LOOKUP_DAYS
            events = await _event_lookup_dividend_events(client, asset_id, (day1, day2))
            e1, e2 = events[day1], events[day2]
            broker_id = await _event_lookup_broker(client, owned)
            creates = [
                _event_lookup_dividend(broker_id, asset_id, day1, "1.25", e1),
                _event_lookup_dividend(broker_id, asset_id, day2, "2.50", e2),
                _event_lookup_dividend(broker_id, asset_id, day3, "3.75", None),
            ]
            commit = await client.post(f"{API_BASE}/transactions/commit", json={"creates": creates}, timeout=TIMEOUT)
            assert commit.status_code == 200, commit.text
            body = commit.json()
            assert body["committed"] is True, body["issues"]
            ids = {r["index"]: r["ids"][0] for r in body["results"] if r["operation"] == "create"}
            assert sorted(ids) == [0, 1, 2], body["results"]
            tx1, tx2, tx3 = ids[0], ids[1], ids[2]

            # Precondition: the links are what this test says they are.
            linked = await client.get(f"{API_BASE}/transactions", params={"ids": [tx1, tx2, tx3]}, timeout=TIMEOUT)
            assert linked.status_code == 200, linked.text
            assert {tx["id"]: tx["asset_event_id"] for tx in linked.json()} == {tx1: e1, tx2: e2, tx3: None}

            # The scope guard: the event is global, the transactions are not.
            _, _, stranger_cookie = await create_test_user(stranger)
            assert stranger_cookie, "Could not authenticate the second user"
            resp = await stranger.get(f"{API_BASE}/transactions", params={"asset_event_id": e1}, timeout=TIMEOUT)
            assert resp.status_code == 200, resp.text
            assert [tx["id"] for tx in resp.json()] == [], f"a user without access to broker {broker_id} sees none of its transactions, whatever the event"

            resp = await client.get(f"{API_BASE}/transactions", params={"asset_event_id": e1}, timeout=TIMEOUT)
            assert resp.status_code == 200, resp.text
            found = sorted(tx["id"] for tx in resp.json())
            assert found == [tx1], f"GET /transactions?asset_event_id={e1} must return only tx1={tx1}, the transaction linked to that event; got {found} (tx2={tx2} is linked to event {e2}, tx3={tx3} to none)"
            print_success(f"✓ Event {e1} → transaction {tx1}, and nothing for a user outside the broker")
        finally:
            leftovers = await owned.drop(client)
    assert not leftovers, leftovers


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_id", ["0", "-1"])
async def test_get_transactions_rejects_non_positive_asset_event_id(test_server, bad_id):
    """C-65b: asset_event_id is an event id, > 0 — 0 or a negative id is a 422, never «no filter».

    Before the fix the parameter is ignored: 200, with every transaction the caller can see.
    """
    print_section(f"C-65b: GET /transactions?asset_event_id={bad_id} → 422")
    async with httpx.AsyncClient() as client:
        _, _, session_cookie = await create_test_user(client)
        assert session_cookie, "Could not authenticate the test user"
        resp = await client.get(f"{API_BASE}/transactions", params={"asset_event_id": bad_id}, timeout=TIMEOUT)
        assert resp.status_code == 422, f"asset_event_id={bad_id} must be rejected with 422; got {resp.status_code}: {resp.text[:300]}"
        print_success(f"✓ asset_event_id={bad_id} rejected")

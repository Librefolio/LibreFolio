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
from typing import Optional

import httpx
import pytest

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
def test_asset_id(test_server) -> int:
    """Create a test asset and return its ID (using existing asset or create one)."""
    import asyncio  # noqa: PLC0415 — test setup — imports after sys.path/db config

    async def get_or_create_asset():
        async with httpx.AsyncClient() as client:
            # First authenticate
            await create_test_user(client)

            # Try to get existing assets first
            response = await client.get(f"{API_BASE}/assets", timeout=TIMEOUT)
            if response.status_code == 200:
                assets = response.json()
                if assets:
                    return assets[0]["id"]

            # Create a new asset
            payload = [{
                "display_name": f"API Test Stock {date.today().isoformat()}",
                "asset_type": "STOCK",
                "currency": "EUR",
            }]
            response = await client.post(
                f"{API_BASE}/assets",
                json=payload,
                timeout=TIMEOUT,
            )
            if response.status_code == 200:
                return response.json()["results"][0]["asset_id"]

            pytest.skip("Could not create test asset")

    return asyncio.run(get_or_create_asset())


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
        assert data["results"][0]["id"] is not None

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
            json={"creates": [
                {
                    "broker_id": broker_id,
                    "type": "DEPOSIT",
                    "date": date.today().isoformat(),
                    "cash": {"code": "EUR", "amount": "1000"},
                }
            ]},
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
            json={"creates": [
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
            ]},
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
            json={"creates": [
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
            ]},
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
        tx_id = create_resp.json()["results"][0]["id"]

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

        # Event types should have emoji + compatible_tx_types
        ev_types = data["event_types"]
        assert isinstance(ev_types, list)
        assert len(ev_types) > 0
        for item in ev_types:
            assert "code" in item
            assert "emoji" in item
            assert "compatible_tx_types" in item

        print_success(f"✓ Got {len(tx_types)} transaction types, {len(ev_types)} event types")


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
        tx_id = create_resp.json()["results"][0]["id"]

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
        tx_ids = [r["id"] for r in create_resp.json()["results"]]

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
async def test_delete_linked_without_pair(test_server, test_broker_id, test_asset_id):
    """TX-A-031: DELETE only one of linked pair fails."""
    print_section("Test TX-A-031: DELETE /transactions - linked without pair")

    async with httpx.AsyncClient() as client:
        # Authenticate first
        await create_test_user(client)

        # Create source broker
        unique_name = f"TX Link Source Broker {uuid.uuid4().hex[:8]}"
        br_resp = await client.post(
            f"{API_BASE}/brokers",
            json=[{"name": unique_name, "allow_cash_overdraft": True}],
            timeout=TIMEOUT,
        )
        assert br_resp.status_code == 200
        source_broker_id = br_resp.json()["results"][0]["broker_id"]

        # Create target broker for transfer
        ts = date.today().isoformat()
        broker_payload = [{"name": f"Transfer Target {ts}", "allow_cash_overdraft": True}]
        broker_resp = await client.post(
            f"{API_BASE}/brokers",
            json=broker_payload,
            timeout=TIMEOUT,
        )
        target_broker_id = broker_resp.json()["results"][0]["broker_id"]

        # First get or create an asset
        assets_resp = await client.get(f"{API_BASE}/assets", timeout=TIMEOUT)
        if assets_resp.status_code == 200 and assets_resp.json():
            asset_id = assets_resp.json()[0]["id"]
        else:
            # Create asset
            asset_resp = await client.post(
                f"{API_BASE}/assets",
                json={
                    "display_name": f"Test Asset {uuid.uuid4().hex[:8]}",
                    "asset_type": "STOCK",
                    "currency": "EUR",
                },
                timeout=TIMEOUT,
            )
            asset_id = asset_resp.json()["id"]

        # First add some asset to source broker via ADJUSTMENT
        adj_payload = [
            {
                "broker_id": source_broker_id,
                "asset_id": asset_id,
                "type": "ADJUSTMENT",
                "date": (date.today() - timedelta(days=1)).isoformat(),
                "quantity": "100",
            }
        ]
        await client.post(f"{API_BASE}/transactions/commit", json={"creates": adj_payload}, timeout=TIMEOUT)

        # Create linked transfer
        link_uuid = f"test-link-api-{uuid.uuid4().hex[:8]}"
        transfer_payload = [
            {
                "broker_id": source_broker_id,
                "asset_id": asset_id,
                "type": "TRANSFER",
                "date": date.today().isoformat(),
                "quantity": "-10",
                "link_uuid": link_uuid,
            },
            {
                "broker_id": target_broker_id,
                "asset_id": asset_id,
                "type": "TRANSFER",
                "date": date.today().isoformat(),
                "quantity": "10",
                "link_uuid": link_uuid,
            },
        ]
        create_resp = await client.post(
            f"{API_BASE}/transactions/commit",
            json={"creates": transfer_payload},
            timeout=TIMEOUT,
        )
        tx_ids = [r["id"] for r in create_resp.json()["results"]]

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

        print_success("✓ Got error when trying to delete only one of linked pair")

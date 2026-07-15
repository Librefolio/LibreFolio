"""
Broker API Tests.

Tests for Broker endpoints:
- POST /brokers: Create brokers (with optional initial deposits)
- GET /brokers: List all brokers
- GET /brokers/{id}: Get broker details
- GET /brokers/{id}/summary: Get broker with balances and holdings
- PATCH /brokers/{id}: Update broker
- DELETE /brokers: Bulk delete brokers

All endpoints now require authentication.
Creator becomes OWNER automatically.
Users only see brokers they have access to.

See checklist: 01_test_broker_transaction_subsystem.md - Category 5
Reference: backend/app/api/v1/brokers.py
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

import httpx
import pytest

from backend.app.config import PROJECT_ROOT, get_settings
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30


def unique_name(prefix: str) -> str:
    """Generate a unique name using UUID to avoid duplicate conflicts."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def unique_username() -> str:
    """Generate a unique username."""
    timestamp = int(datetime.now().timestamp() * 1000)
    return f"broker_test_{timestamp}_{uuid.uuid4().hex[:6]}"


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


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


async def login_user(client: httpx.AsyncClient, username: str, password: str) -> Optional[str]:
    """Login and return session cookie. Also sets cookie on client."""
    resp = await client.post(f"{API_BASE}/auth/login", json={"username": username, "password": password}, timeout=TIMEOUT)
    session_cookie = resp.cookies.get("session")
    if session_cookie:
        client.cookies.set("session", session_cookie)
    return session_cookie


# ============================================================================
# PYTEST FIXTURES
# ============================================================================


@pytest.fixture(scope="module")
def test_server():
    """Start test server once for all tests in this module."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


# ============================================================================
# BROKER API - CREATE (with auth)
# ============================================================================


class TestBrokerCreate:
    """Tests for POST /brokers with authentication."""

    @pytest.mark.asyncio
    async def test_post_brokers_requires_auth(self, test_server):
        """BR-A-000: POST /brokers without auth returns 401."""
        print_section("Test BR-A-000: POST /brokers - requires auth")

        async with httpx.AsyncClient() as client:
            payload = [{"name": unique_name("NoAuth Broker")}]
            response = await client.post(
                f"{API_BASE}/brokers",
                json=payload,
                timeout=TIMEOUT,
            )

            assert response.status_code == 401, f"Expected 401, got {response.status_code}"
            print_success("✓ Got 401 without authentication")

    @pytest.mark.asyncio
    async def test_post_brokers(self, test_server):
        """BR-A-001: POST /brokers creates broker."""
        print_section("Test BR-A-001: POST /brokers")

        async with httpx.AsyncClient() as client:
            await create_test_user(client)

            payload = [
                {
                    "name": unique_name("Create Test Broker"),
                    "description": "Created via API test",
                }
            ]

            response = await client.post(
                f"{API_BASE}/brokers",
                json=payload,
                timeout=TIMEOUT,
            )

            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

            data = response.json()
            assert data["success_count"] == 1
            assert data["results"][0]["success"] is True
            assert data["results"][0]["broker_id"] is not None

            print_success("✓ Created broker successfully")

    @pytest.mark.asyncio
    async def test_post_brokers_with_balances(self, test_server):
        """BR-A-002: POST /brokers with initial_balances creates deposits."""
        print_section("Test BR-A-002: POST /brokers - with initial balances")

        async with httpx.AsyncClient() as client:
            await create_test_user(client)

            payload = [
                {
                    "name": unique_name("Balance Broker"),
                    "initial_balances": [
                        {"code": "EUR", "amount": "5000"},
                        {"code": "USD", "amount": "3000"},
                    ],
                }
            ]

            response = await client.post(
                f"{API_BASE}/brokers",
                json=payload,
                timeout=TIMEOUT,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success_count"] == 1
            assert data["results"][0]["deposits_created"] == 2

            print_success("✓ Created broker with 2 initial deposits")

    @pytest.mark.asyncio
    async def test_post_brokers_with_zero_initial_balance(self, test_server):
        """BR-A-002B: POST /brokers with zero initial balance skips deposit creation."""
        print_section("Test BR-A-002B: POST /brokers - zero initial balance")

        async with httpx.AsyncClient() as client:
            await create_test_user(client)

            payload = [
                {
                    "name": unique_name("Zero Balance Broker"),
                    "initial_balances": [{"code": "EUR", "amount": "0"}],
                }
            ]

            response = await client.post(
                f"{API_BASE}/brokers",
                json=payload,
                timeout=TIMEOUT,
            )

            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

            data = response.json()
            assert data["success_count"] == 1
            assert data["results"][0]["success"] is True
            assert data["results"][0]["deposits_created"] == 0

            broker_id = data["results"][0]["broker_id"]
            summary_response = await client.get(f"{API_BASE}/brokers/{broker_id}/summary", timeout=TIMEOUT)
            assert summary_response.status_code == 200
            assert summary_response.json()["cash_balances"] == []

            print_success("✓ Created broker without deposit for zero initial balance")

    @pytest.mark.asyncio
    async def test_post_brokers_duplicate(self, test_server):
        """BR-A-003: POST /brokers with existing name fails."""
        print_section("Test BR-A-003: POST /brokers - duplicate name")

        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            name = unique_name("Duplicate Broker")

            # Create first
            payload1 = [{"name": name}]
            await client.post(f"{API_BASE}/brokers", json=payload1, timeout=TIMEOUT)

            # Try duplicate
            payload2 = [{"name": name}]
            response = await client.post(
                f"{API_BASE}/brokers",
                json=payload2,
                timeout=TIMEOUT,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["results"][0]["success"] is False
            # Error message can be "already exists" or "already have a broker named"
            error_msg = data["results"][0]["error"].lower()
            assert "already" in error_msg and ("exists" in error_msg or "have" in error_msg)

            print_success("✓ Got error for duplicate name")

    @pytest.mark.asyncio
    async def test_creator_becomes_owner(self, test_server):
        """BR-A-004: Creator automatically becomes OWNER."""
        print_section("Test BR-A-004: Creator becomes OWNER")

        async with httpx.AsyncClient() as client:
            await create_test_user(client)

            # Create broker
            payload = [{"name": unique_name("Owner Test Broker")}]
            create_resp = await client.post(
                f"{API_BASE}/brokers",
                json=payload,
                timeout=TIMEOUT,
            )
            broker_id = create_resp.json()["results"][0]["broker_id"]

            # Check access list
            access_resp = await client.get(
                f"{API_BASE}/brokers/{broker_id}/access",
                timeout=TIMEOUT,
            )

            assert access_resp.status_code == 200
            access_data = access_resp.json()
            assert len(access_data["items"]) == 1
            assert access_data["items"][0]["role"] == "OWNER"

            print_success("✓ Creator is OWNER")


# ============================================================================
# BROKER API - READ (with auth)
# ============================================================================


class TestBrokerRead:
    """Tests for GET /brokers with authentication."""

    @pytest.mark.asyncio
    async def test_get_brokers_requires_auth(self, test_server):
        """BR-A-009: GET /brokers without auth returns 401."""
        print_section("Test BR-A-009: GET /brokers - requires auth")

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE}/brokers", timeout=TIMEOUT)
            assert response.status_code == 401
            print_success("✓ Got 401 without authentication")

    @pytest.mark.asyncio
    async def test_get_brokers(self, test_server):
        """BR-A-010: GET /brokers returns user's brokers."""
        print_section("Test BR-A-010: GET /brokers")

        async with httpx.AsyncClient() as client:
            await create_test_user(client)

            # Create a broker first
            payload = [{"name": unique_name("List Test Broker")}]
            await client.post(f"{API_BASE}/brokers", json=payload, timeout=TIMEOUT)

            response = await client.get(f"{API_BASE}/brokers", timeout=TIMEOUT)

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, dict)
            assert "items" in data
            assert "inaccessible" in data
            assert len(data["items"]) >= 1
            assert data["inaccessible"] == []
            assert Decimal(str(data["items"][0]["user_share_percentage"])) == Decimal("1")

            print_success(f"✓ Got {len(data['items'])} brokers")

    @pytest.mark.asyncio
    async def test_get_brokers_include_inaccessible(self, test_server):
        """BR-A-010B: GET /brokers?include_inaccessible=true returns discovery items."""
        print_section("Test BR-A-010B: GET /brokers include inaccessible")

        async with httpx.AsyncClient() as owner_client, httpx.AsyncClient() as other_client:
            await create_test_user(owner_client)
            payload = [{"name": unique_name("Discovery Broker")}]
            create_resp = await owner_client.post(f"{API_BASE}/brokers", json=payload, timeout=TIMEOUT)
            broker_id = create_resp.json()["results"][0]["broker_id"]

            await create_test_user(other_client)

            default_resp = await other_client.get(f"{API_BASE}/brokers", timeout=TIMEOUT)
            assert default_resp.status_code == 200
            assert default_resp.json()["items"] == []
            assert default_resp.json()["inaccessible"] == []

            response = await other_client.get(
                f"{API_BASE}/brokers",
                params={"include_inaccessible": "true"},
                timeout=TIMEOUT,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["items"] == []
            discovered_broker = next((broker for broker in data["inaccessible"] if broker["id"] == broker_id), None)
            assert discovered_broker == {
                "id": broker_id,
                "name": payload[0]["name"],
                "icon_url": None,
            }

            print_success("✓ Discovery payload returns inaccessible brokers separately")

    @pytest.mark.asyncio
    async def test_get_broker_by_id(self, test_server):
        """BR-A-011: GET /brokers/{id} returns broker."""
        print_section("Test BR-A-011: GET /brokers/{id}")

        async with httpx.AsyncClient() as client:
            await create_test_user(client)

            # Create a broker first
            payload = [{"name": unique_name("GetById Broker")}]
            create_resp = await client.post(
                f"{API_BASE}/brokers",
                json=payload,
                timeout=TIMEOUT,
            )
            broker_id = create_resp.json()["results"][0]["broker_id"]

            # Get by ID
            response = await client.get(
                f"{API_BASE}/brokers/{broker_id}",
                timeout=TIMEOUT,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == broker_id

            print_success(f"✓ Got broker {broker_id}")

    @pytest.mark.asyncio
    async def test_get_broker_not_found(self, test_server):
        """BR-A-012: GET /brokers/{id} returns 404 for non-existent."""
        print_section("Test BR-A-012: GET /brokers/{id} - not found")

        async with httpx.AsyncClient() as client:
            await create_test_user(client)

            response = await client.get(
                f"{API_BASE}/brokers/999999",
                timeout=TIMEOUT,
            )

            assert response.status_code == 404

            print_success("✓ Got 404 as expected")

    @pytest.mark.asyncio
    async def test_get_broker_summary(self, test_server):
        """BR-A-013: GET /brokers/{id}/summary returns full summary."""
        print_section("Test BR-A-013: GET /brokers/{id}/summary")

        async with httpx.AsyncClient() as client:
            await create_test_user(client)

            # Create broker with balance
            payload = [
                {
                    "name": unique_name("Summary Broker"),
                    "initial_balances": [{"code": "EUR", "amount": "1000"}],
                }
            ]
            create_resp = await client.post(
                f"{API_BASE}/brokers",
                json=payload,
                timeout=TIMEOUT,
            )
            broker_id = create_resp.json()["results"][0]["broker_id"]

            # Get summary
            response = await client.get(
                f"{API_BASE}/brokers/{broker_id}/summary",
                timeout=TIMEOUT,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == broker_id
            assert "cash_balances" in data
            assert "holdings" in data
            assert len(data["cash_balances"]) == 1
            assert data["cash_balances"][0]["code"] == "EUR"

            print_success(f"✓ Got summary for broker {broker_id}")

    @pytest.mark.asyncio
    async def test_get_broker_summary_with_holdings_and_user_metadata(self, test_server):
        """BR-A-013B: GET /brokers/{id}/summary returns holdings and user metadata."""
        print_section("Test BR-A-013B: GET /brokers/{id}/summary - holdings")

        async with httpx.AsyncClient() as client:
            await create_test_user(client)

            broker_name = unique_name("Summary Holdings Broker")
            create_resp = await client.post(
                f"{API_BASE}/brokers",
                json=[{"name": broker_name, "allow_cash_overdraft": True}],
                timeout=TIMEOUT,
            )
            assert create_resp.status_code == 200, create_resp.text
            broker_id = create_resp.json()["results"][0]["broker_id"]

            asset_name = unique_name("Summary Asset")
            asset_resp = await client.post(
                f"{API_BASE}/assets",
                json=[{"display_name": asset_name, "asset_type": "STOCK", "currency": "EUR"}],
                timeout=TIMEOUT,
            )
            assert asset_resp.status_code in (200, 201), asset_resp.text
            asset_id = asset_resp.json()["results"][0]["asset_id"]

            tx_resp = await client.post(
                f"{API_BASE}/transactions/commit",
                json={
                    "creates": [
                        {
                            "broker_id": broker_id,
                            "type": "DEPOSIT",
                            "date": date.today().isoformat(),
                            "cash": {"code": "EUR", "amount": "5000"},
                        },
                        {
                            "broker_id": broker_id,
                            "asset_id": asset_id,
                            "type": "BUY",
                            "date": date.today().isoformat(),
                            "quantity": "10",
                            "cash": {"code": "EUR", "amount": "-1200"},
                        },
                    ]
                },
                timeout=TIMEOUT,
            )
            assert tx_resp.status_code == 200, tx_resp.text
            assert tx_resp.json()["committed"] is True

            response = await client.get(
                f"{API_BASE}/brokers/{broker_id}/summary",
                timeout=TIMEOUT,
            )

            assert response.status_code == 200, response.text
            data = response.json()
            assert data["id"] == broker_id
            assert data["user_role"] == "OWNER"
            assert Decimal(str(data["user_share_percentage"])) == Decimal("1")
            assert any(balance["code"] == "EUR" for balance in data["cash_balances"])

            holding = next((item for item in data["holdings"] if item["asset_id"] == asset_id), None)
            assert holding is not None
            assert holding["asset_name"] == asset_name
            assert Decimal(str(holding["quantity"])) == Decimal("10")
            assert holding["total_cost"]["code"] == "EUR"
            assert Decimal(str(holding["total_cost"]["amount"])) == Decimal("1200")

            print_success(f"✓ Got holdings summary for broker {broker_id}")


# ============================================================================
# BROKER API - UPDATE (with auth)
# ============================================================================


class TestBrokerUpdate:
    """Tests for PATCH /brokers with authentication."""

    @pytest.mark.asyncio
    async def test_patch_broker(self, test_server):
        """BR-A-020: PATCH /brokers/{id} updates broker."""
        print_section("Test BR-A-020: PATCH /brokers/{id}")

        async with httpx.AsyncClient() as client:
            await create_test_user(client)

            # Create broker
            payload = [{"name": unique_name("Update Broker")}]
            create_resp = await client.post(
                f"{API_BASE}/brokers",
                json=payload,
                timeout=TIMEOUT,
            )
            broker_id = create_resp.json()["results"][0]["broker_id"]

            # Update
            update_payload = {"description": "Updated via API"}
            response = await client.patch(
                f"{API_BASE}/brokers/{broker_id}",
                json=update_payload,
                timeout=TIMEOUT,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success_count"] == 1
            assert data["results"][0]["success"] is True

            print_success("✓ Updated broker successfully")

    @pytest.mark.asyncio
    async def test_patch_broker_not_found(self, test_server):
        """BR-A-021: PATCH /brokers/{id} for non-existent returns success=False."""
        print_section("Test BR-A-021: PATCH /brokers/{id} - not found")

        async with httpx.AsyncClient() as client:
            await create_test_user(client)

            response = await client.patch(
                f"{API_BASE}/brokers/999999",
                json={"description": "Should fail"},
                timeout=TIMEOUT,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["results"][0]["success"] is False

            print_success("✓ Got success=False for non-existent broker")


# ============================================================================
# BROKER API - DELETE (with auth)
# ============================================================================


class TestBrokerDelete:
    """Tests for DELETE /brokers with authentication."""

    @pytest.mark.asyncio
    async def test_delete_brokers(self, test_server):
        """BR-A-030: DELETE /brokers deletes empty broker."""
        print_section("Test BR-A-030: DELETE /brokers")

        async with httpx.AsyncClient() as client:
            await create_test_user(client)

            # Create broker
            payload = [{"name": unique_name("Delete Broker")}]
            create_resp = await client.post(
                f"{API_BASE}/brokers",
                json=payload,
                timeout=TIMEOUT,
            )
            broker_id = create_resp.json()["results"][0]["broker_id"]

            # Delete
            response = await client.delete(
                f"{API_BASE}/brokers",
                params={"ids": [broker_id]},
                timeout=TIMEOUT,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["total_deleted"] == 1

            print_success("✓ Deleted broker successfully")

    @pytest.mark.asyncio
    async def test_delete_brokers_with_tx_no_force(self, test_server):
        """BR-A-031: DELETE broker with transactions without force fails."""
        print_section("Test BR-A-031: DELETE /brokers - with transactions no force")

        async with httpx.AsyncClient() as client:
            await create_test_user(client)

            # Create broker with balance (creates transaction)
            payload = [
                {
                    "name": unique_name("Has TX Broker"),
                    "initial_balances": [{"code": "EUR", "amount": "1000"}],
                }
            ]
            create_resp = await client.post(
                f"{API_BASE}/brokers",
                json=payload,
                timeout=TIMEOUT,
            )
            broker_id = create_resp.json()["results"][0]["broker_id"]

            # Try to delete without force
            response = await client.delete(
                f"{API_BASE}/brokers",
                params={"ids": [broker_id], "force": False},
                timeout=TIMEOUT,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["results"][0]["success"] is False
            assert "transactions" in data["results"][0]["message"].lower()

            print_success("✓ Got error when deleting broker with transactions")

    @pytest.mark.asyncio
    async def test_delete_brokers_with_tx_force(self, test_server):
        """BR-A-032: DELETE broker with transactions with force succeeds."""
        print_section("Test BR-A-032: DELETE /brokers - with transactions force")

        async with httpx.AsyncClient() as client:
            await create_test_user(client)

            # Create broker with balance
            payload = [
                {
                    "name": unique_name("Force Delete Broker"),
                    "initial_balances": [{"code": "EUR", "amount": "1000"}],
                }
            ]
            create_resp = await client.post(
                f"{API_BASE}/brokers",
                json=payload,
                timeout=TIMEOUT,
            )
            broker_id = create_resp.json()["results"][0]["broker_id"]

            # Delete with force
            response = await client.delete(
                f"{API_BASE}/brokers",
                params={"ids": [broker_id], "force": True},
                timeout=TIMEOUT,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["results"][0]["success"] is True
            assert data["results"][0]["transactions_deleted"] >= 1

            print_success("✓ Force deleted broker with transactions")

    @pytest.mark.asyncio
    async def test_delete_brokers_partial_success(self, test_server):
        """BR-A-032B: DELETE /brokers can delete valid broker and keep blocked broker."""
        print_section("Test BR-A-032B: DELETE /brokers - partial success")

        async with httpx.AsyncClient() as client:
            await create_test_user(client)

            delete_resp = await client.post(
                f"{API_BASE}/brokers",
                json=[{"name": unique_name("Delete Partial OK")}],
                timeout=TIMEOUT,
            )
            assert delete_resp.status_code == 200, delete_resp.text
            deletable_broker_id = delete_resp.json()["results"][0]["broker_id"]

            blocked_resp = await client.post(
                f"{API_BASE}/brokers",
                json=[{"name": unique_name("Delete Partial Blocked"), "initial_balances": [{"code": "EUR", "amount": "1000"}]}],
                timeout=TIMEOUT,
            )
            assert blocked_resp.status_code == 200, blocked_resp.text
            blocked_broker_id = blocked_resp.json()["results"][0]["broker_id"]

            response = await client.delete(
                f"{API_BASE}/brokers",
                params={"ids": [deletable_broker_id, blocked_broker_id], "force": False},
                timeout=TIMEOUT,
            )

            assert response.status_code == 200, response.text
            data = response.json()
            assert data["success_count"] == 1
            assert data["total_deleted"] == 1

            result_by_id = {item["id"]: item for item in data["results"]}
            assert result_by_id[deletable_broker_id]["success"] is True
            assert result_by_id[blocked_broker_id]["success"] is False
            assert "transactions" in result_by_id[blocked_broker_id]["message"].lower()

            deleted_check = await client.get(f"{API_BASE}/brokers/{deletable_broker_id}", timeout=TIMEOUT)
            assert deleted_check.status_code == 404

            kept_check = await client.get(f"{API_BASE}/brokers/{blocked_broker_id}", timeout=TIMEOUT)
            assert kept_check.status_code == 200

            print_success("✓ Partial delete keeps broker with transactions")


# ============================================================================
# BROKER API - BULK OPERATIONS
# ============================================================================


class TestBrokerBulkOperations:
    """Tests for bulk broker operations."""

    @pytest.mark.asyncio
    async def test_bulk_create_multiple_brokers(self, test_server):
        """BR-A-040: POST /brokers creates multiple brokers in one request."""
        print_section("Test BR-A-040: Bulk create multiple brokers")

        async with httpx.AsyncClient() as client:
            await create_test_user(client)

            payload = [
                {"name": unique_name("Bulk Broker 1"), "description": "First"},
                {"name": unique_name("Bulk Broker 2"), "description": "Second"},
                {"name": unique_name("Bulk Broker 3"), "description": "Third"},
            ]

            response = await client.post(
                f"{API_BASE}/brokers",
                json=payload,
                timeout=TIMEOUT,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success_count"] == 3
            assert len(data["results"]) == 3
            assert all(r["success"] for r in data["results"])

            print_success("✓ Created 3 brokers in bulk")

    @pytest.mark.asyncio
    async def test_bulk_create_partial_failure(self, test_server):
        """BR-A-041: Bulk create with one duplicate fails only that item."""
        print_section("Test BR-A-041: Bulk create partial failure")

        async with httpx.AsyncClient() as client:
            await create_test_user(client)

            # Create first broker
            first_name = unique_name("First Broker")
            await client.post(
                f"{API_BASE}/brokers",
                json=[{"name": first_name}],
                timeout=TIMEOUT,
            )

            # Try to create 3 brokers, one with duplicate name
            payload = [
                {"name": unique_name("New Broker 1")},
                {"name": first_name},  # Duplicate!
                {"name": unique_name("New Broker 2")},
            ]

            response = await client.post(
                f"{API_BASE}/brokers",
                json=payload,
                timeout=TIMEOUT,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success_count"] == 2
            assert data["results"][0]["success"] is True
            assert data["results"][1]["success"] is False
            # Error message can be "already exists" or "already have a broker named"
            error_msg = data["results"][1]["error"].lower()
            assert "already" in error_msg and ("exists" in error_msg or "have" in error_msg)
            assert data["results"][2]["success"] is True

            print_success("✓ Bulk create with partial failure handled correctly")

    @pytest.mark.asyncio
    async def test_bulk_delete_multiple_brokers(self, test_server):
        """BR-A-042: DELETE /brokers deletes multiple brokers in one request."""
        print_section("Test BR-A-042: Bulk delete multiple brokers")

        async with httpx.AsyncClient() as client:
            await create_test_user(client)

            # Create 3 brokers
            broker_ids = []
            for i in range(3):
                resp = await client.post(
                    f"{API_BASE}/brokers",
                    json=[{"name": unique_name(f"Delete Bulk {i}")}],
                    timeout=TIMEOUT,
                )
                broker_ids.append(resp.json()["results"][0]["broker_id"])

            # Delete all 3
            response = await client.delete(
                f"{API_BASE}/brokers",
                params={"ids": broker_ids},
                timeout=TIMEOUT,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["total_deleted"] == 3
            assert all(r["success"] for r in data["results"])

            print_success("✓ Deleted 3 brokers in bulk")

    @pytest.mark.asyncio
    async def test_update_with_duplicate_name(self, test_server):
        """BR-A-043: PATCH with duplicate name fails."""
        print_section("Test BR-A-043: Update with duplicate name")

        async with httpx.AsyncClient() as client:
            await create_test_user(client)

            # Create two brokers
            name1 = unique_name("Broker One")
            name2 = unique_name("Broker Two")

            resp1 = await client.post(
                f"{API_BASE}/brokers",
                json=[{"name": name1}],
                timeout=TIMEOUT,
            )
            broker1_id = resp1.json()["results"][0]["broker_id"]

            await client.post(
                f"{API_BASE}/brokers",
                json=[{"name": name2}],
                timeout=TIMEOUT,
            )

            # Try to rename broker1 to broker2's name
            response = await client.patch(
                f"{API_BASE}/brokers/{broker1_id}",
                json={"name": name2},
                timeout=TIMEOUT,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["results"][0]["success"] is False
            assert "already exists" in data["results"][0]["error"]

            print_success("✓ Update with duplicate name correctly rejected")


# ============================================================================
# BROKER API - MULTIPLE OWNERS
# ============================================================================


class TestMultipleOwners:
    """Tests for brokers with multiple owners."""

    @pytest.mark.asyncio
    async def test_broker_with_multiple_owners(self, test_server):
        """BR-A-050: Broker can have multiple OWNERs."""
        print_section("Test BR-A-050: Multiple owners on same broker")

        async with httpx.AsyncClient() as client1, httpx.AsyncClient() as client2:
            # User 1 creates broker
            await create_test_user(client1)
            me_resp = await client1.get(f"{API_BASE}/auth/me", timeout=TIMEOUT)
            user1_id = me_resp.json()["user"]["id"]
            resp = await client1.post(
                f"{API_BASE}/brokers",
                json=[{"name": unique_name("Multi Owner Broker")}],
                timeout=TIMEOUT,
            )
            broker_id = resp.json()["results"][0]["broker_id"]

            # Create user 2 and add as OWNER
            user2_resp = await client2.post(
                f"{API_BASE}/auth/register",
                json={
                    "username": unique_username(),
                    "email": f"{unique_username()}@test.com",
                    "password": "TestPass123!",
                },
                timeout=TIMEOUT,
            )
            user2_id = user2_resp.json()["user"]["id"]

            # User 1 adds user 2 as OWNER via bulk update
            await client1.put(
                f"{API_BASE}/brokers/{broker_id}/access",
                json=[
                    {"user_id": user1_id, "role": "OWNER", "share_percentage": 0.5},
                    {"user_id": user2_id, "role": "OWNER", "share_percentage": 0.5},
                ],
                timeout=TIMEOUT,
            )

            # Login user 2
            await client2.post(
                f"{API_BASE}/auth/login",
                json={
                    "username": user2_resp.json()["user"]["username"],
                    "password": "TestPass123!",
                },
                timeout=TIMEOUT,
            )
            client2.cookies.set("session", client2.cookies.get("session"))

            # User 2 (also OWNER) can modify broker
            response = await client2.patch(
                f"{API_BASE}/brokers/{broker_id}",
                json={"description": "Modified by second owner"},
                timeout=TIMEOUT,
            )

            assert response.status_code == 200
            assert response.json()["results"][0]["success"] is True

            # Verify both are OWNERs
            access_resp = await client1.get(
                f"{API_BASE}/brokers/{broker_id}/access",
                timeout=TIMEOUT,
            )
            owners = [a for a in access_resp.json()["items"] if a["role"] == "OWNER"]
            assert len(owners) == 2

            print_success("✓ Broker with multiple owners works correctly")

    @pytest.mark.asyncio
    async def test_one_owner_can_remove_another(self, test_server):
        """BR-A-051: One OWNER can remove another OWNER (if not last)."""
        print_section("Test BR-A-051: One owner removes another")

        async with httpx.AsyncClient() as client1, httpx.AsyncClient() as client2:
            # Setup: user1 creates broker
            await create_test_user(client1)
            me_resp = await client1.get(f"{API_BASE}/auth/me", timeout=TIMEOUT)
            user1_id = me_resp.json()["user"]["id"]
            resp = await client1.post(
                f"{API_BASE}/brokers",
                json=[{"name": unique_name("Remove Owner Test")}],
                timeout=TIMEOUT,
            )
            broker_id = resp.json()["results"][0]["broker_id"]

            # Create user 2
            user2_resp = await client2.post(
                f"{API_BASE}/auth/register",
                json={
                    "username": unique_username(),
                    "email": f"{unique_username()}@test.com",
                    "password": "TestPass123!",
                },
                timeout=TIMEOUT,
            )
            user2_id = user2_resp.json()["user"]["id"]

            # Add user2 as OWNER via bulk
            await client1.put(
                f"{API_BASE}/brokers/{broker_id}/access",
                json=[
                    {"user_id": user1_id, "role": "OWNER", "share_percentage": 0.5},
                    {"user_id": user2_id, "role": "OWNER", "share_percentage": 0.5},
                ],
                timeout=TIMEOUT,
            )

            # User 1 removes user 2 by sending bulk with only user1
            response = await client1.put(
                f"{API_BASE}/brokers/{broker_id}/access",
                json=[
                    {"user_id": user1_id, "role": "OWNER", "share_percentage": 1.0},
                ],
                timeout=TIMEOUT,
            )

            assert response.status_code == 200
            assert response.json()["success_count"] == 1

            # Verify only user1 remains
            access_resp = await client1.get(
                f"{API_BASE}/brokers/{broker_id}/access",
                timeout=TIMEOUT,
            )
            assert len(access_resp.json()["items"]) == 1

            print_success("✓ Owner removed another owner successfully")


# ============================================================================
# BROKER API - BRIM IMPORT
# ============================================================================


class TestBrokerImportEndpoints:
    """Tests for BRIM endpoints in brokers router."""

    @pytest.mark.asyncio
    async def test_get_brim_file_preview_for_sample_report(self, test_server):
        """BR-A-060: GET /brokers/import/files/{id}/preview returns preview payload."""
        print_section("Test BR-A-060: GET /brokers/import/files/{id}/preview")

        async with httpx.AsyncClient() as client:
            await create_test_user(client)

            create_resp = await client.post(
                f"{API_BASE}/brokers",
                json=[{"name": unique_name("Preview Broker"), "allow_cash_overdraft": True}],
                timeout=TIMEOUT,
            )
            assert create_resp.status_code == 200, create_resp.text
            broker_id = create_resp.json()["results"][0]["broker_id"]

            sample_report = PROJECT_ROOT / "backend" / "app" / "services" / "brim_providers" / "sample_reports" / "generic_simple.csv"
            upload_resp = await client.post(
                f"{API_BASE}/brokers/import/upload",
                files={"file": (sample_report.name, sample_report.read_bytes(), "text/csv")},
                data={"broker_id": broker_id},
                timeout=TIMEOUT,
            )
            assert upload_resp.status_code == 200, upload_resp.text
            file_id = upload_resp.json()["file_id"]

            response = await client.get(
                f"{API_BASE}/brokers/import/files/{file_id}/preview",
                timeout=TIMEOUT,
            )

            assert response.status_code == 200, response.text
            data = response.json()
            assert data["preview_type"] == "table"
            assert data["filename"] == sample_report.name
            assert data["source_url"].endswith(f"/brokers/import/files/{file_id}/download?download=false")
            assert data["download_url"].endswith(f"/brokers/import/files/{file_id}/download")
            assert data["preview_url"] is None
            assert len(data["table_rows"]) > 1
            assert data["table_rows"][0][0] == "date"

            print_success("✓ BRIM preview payload returned from brokers API test")

    @pytest.mark.asyncio
    async def test_parse_file_with_auto_plugin(self, test_server):
        """BR-A-061: POST /brokers/import/files/{id}/parse auto-detects generic CSV fallback."""
        print_section("Test BR-A-061: POST /brokers/import/files/{id}/parse - auto plugin")

        async with httpx.AsyncClient() as client:
            await create_test_user(client)

            create_resp = await client.post(
                f"{API_BASE}/brokers",
                json=[{"name": unique_name("Parse Broker"), "allow_cash_overdraft": True}],
                timeout=TIMEOUT,
            )
            assert create_resp.status_code == 200, create_resp.text
            broker_id = create_resp.json()["results"][0]["broker_id"]

            sample_report = PROJECT_ROOT / "backend" / "app" / "services" / "brim_providers" / "sample_reports" / "generic_with_assets.csv"
            upload_resp = await client.post(
                f"{API_BASE}/brokers/import/upload",
                files={"file": (sample_report.name, sample_report.read_bytes(), "text/csv")},
                data={"broker_id": broker_id},
                timeout=TIMEOUT,
            )
            assert upload_resp.status_code == 200, upload_resp.text
            file_id = upload_resp.json()["file_id"]

            response = await client.post(
                f"{API_BASE}/brokers/import/files/{file_id}/parse",
                json={"plugin_code": "auto", "broker_id": broker_id},
                timeout=TIMEOUT,
            )

            assert response.status_code == 200, response.text
            data = response.json()
            assert data["file_id"] == file_id
            assert data["broker_id"] == broker_id
            assert data["plugin_code"] == "broker_generic_csv"
            assert len(data["transactions"]) > 0
            assert len(data["asset_mappings"]) >= 1
            assert set(data["duplicates"]) == {
                "tx_unique_indices",
                "tx_possible_duplicates",
                "tx_likely_duplicates",
            }

            last_parse_resp = await client.get(
                f"{API_BASE}/brokers/import/files/{file_id}/last-parse",
                timeout=TIMEOUT,
            )
            assert last_parse_resp.status_code == 200, last_parse_resp.text
            assert last_parse_resp.json()["plugin_code"] == "broker_generic_csv"

            print_success("✓ BRIM parse auto fallback returned cached generic CSV result")

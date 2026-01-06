"""
Broker API Tests.

Tests for Broker endpoints:
- POST /brokers: Create brokers (with optional initial deposits)
- GET /brokers: List all brokers
- GET /brokers/{id}: Get broker details
- GET /brokers/{id}/summary: Get broker with balances and holdings
- PATCH /brokers/{id}: Update broker
- DELETE /brokers: Bulk delete brokers

See checklist: 01_test_broker_transaction_subsystem.md - Category 5
Reference: backend/app/api/v1/brokers.py
"""
import uuid
from datetime import date

import httpx
import pytest

from backend.app.config import get_settings
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30


def unique_name(prefix: str) -> str:
    """Generate a unique name using UUID to avoid duplicate conflicts."""
    return f"{prefix} {uuid.uuid4().hex[:8]}"


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


# ============================================================================
# 5.5 BROKER API - CREATE
# ============================================================================

@pytest.mark.asyncio
async def test_post_brokers(test_server):
    """BR-A-001: POST /brokers creates broker."""
    print_section("Test BR-A-001: POST /brokers")

    async with httpx.AsyncClient() as client:
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
async def test_post_brokers_with_balances(test_server):
    """BR-A-002: POST /brokers with initial_balances creates deposits."""
    print_section("Test BR-A-002: POST /brokers - with initial balances")

    async with httpx.AsyncClient() as client:
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
async def test_post_brokers_duplicate(test_server):
    """BR-A-003: POST /brokers with existing name fails."""
    print_section("Test BR-A-003: POST /brokers - duplicate name")

    async with httpx.AsyncClient() as client:
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
        assert "already exists" in data["results"][0]["error"]

        print_success("✓ Got error for duplicate name")


# ============================================================================
# 5.6 BROKER API - READ
# ============================================================================

@pytest.mark.asyncio
async def test_get_brokers(test_server):
    """BR-A-010: GET /brokers returns list."""
    print_section("Test BR-A-010: GET /brokers")

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE}/brokers", timeout=TIMEOUT)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        print_success(f"✓ Got {len(data)} brokers")


@pytest.mark.asyncio
async def test_get_broker_by_id(test_server):
    """BR-A-011: GET /brokers/{id} returns broker."""
    print_section("Test BR-A-011: GET /brokers/{id}")

    async with httpx.AsyncClient() as client:
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
async def test_get_broker_not_found(test_server):
    """BR-A-012: GET /brokers/{id} returns 404 for non-existent."""
    print_section("Test BR-A-012: GET /brokers/{id} - not found")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE}/brokers/999999",
            timeout=TIMEOUT,
            )

        assert response.status_code == 404

        print_success("✓ Got 404 as expected")


@pytest.mark.asyncio
async def test_get_broker_summary(test_server):
    """BR-A-013: GET /brokers/{id}/summary returns full summary."""
    print_section("Test BR-A-013: GET /brokers/{id}/summary")

    async with httpx.AsyncClient() as client:
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
async def test_get_broker_summary_not_found(test_server):
    """BR-A-014: GET /brokers/{id}/summary returns 404 for non-existent."""
    print_section("Test BR-A-014: GET /brokers/{id}/summary - not found")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE}/brokers/999999/summary",
            timeout=TIMEOUT,
            )

        assert response.status_code == 404

        print_success("✓ Got 404 as expected")


# ============================================================================
# 5.7 BROKER API - UPDATE
# ============================================================================

@pytest.mark.asyncio
async def test_patch_broker(test_server):
    """BR-A-020: PATCH /brokers/{id} updates broker."""
    print_section("Test BR-A-020: PATCH /brokers/{id}")

    async with httpx.AsyncClient() as client:
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
async def test_patch_broker_not_found(test_server):
    """BR-A-021: PATCH /brokers/{id} for non-existent returns success=False."""
    print_section("Test BR-A-021: PATCH /brokers/{id} - not found")

    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"{API_BASE}/brokers/999999",
            json={"description": "Should fail"},
            timeout=TIMEOUT,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["results"][0]["success"] is False

        print_success("✓ Got success=False for non-existent broker")


@pytest.mark.asyncio
async def test_patch_broker_flag_validation(test_server):
    """BR-A-022: PATCH disable overdraft on broker with negative balance fails."""
    print_section("Test BR-A-022: PATCH /brokers/{id} - flag validation")

    async with httpx.AsyncClient() as client:
        # Create broker with overdraft enabled
        payload = [
            {
                "name": unique_name("Flag Validation Broker"),
                "allow_cash_overdraft": True,
                }
            ]
        create_resp = await client.post(
            f"{API_BASE}/brokers",
            json=payload,
            timeout=TIMEOUT,
            )
        broker_id = create_resp.json()["results"][0]["broker_id"]

        # Create withdrawal (negative balance)
        tx_payload = [
            {
                "broker_id": broker_id,
                "type": "WITHDRAWAL",
                "date": date.today().isoformat(),
                "cash": {"code": "EUR", "amount": "-500"},
                }
            ]
        await client.post(f"{API_BASE}/transactions", json=tx_payload, timeout=TIMEOUT)

        # Try to disable overdraft - should fail
        response = await client.patch(
            f"{API_BASE}/brokers/{broker_id}",
            json={"allow_cash_overdraft": False},
            timeout=TIMEOUT,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["results"][0]["success"] is False
        assert data["results"][0]["validation_triggered"] is True

        print_success("✓ Got validation error when disabling overdraft with negative balance")


# ============================================================================
# 5.8 BROKER API - DELETE
# ============================================================================

@pytest.mark.asyncio
async def test_delete_brokers(test_server):
    """BR-A-030: DELETE /brokers deletes empty broker."""
    print_section("Test BR-A-030: DELETE /brokers")

    async with httpx.AsyncClient() as client:
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
async def test_delete_brokers_with_tx_no_force(test_server):
    """BR-A-031: DELETE broker with transactions without force fails."""
    print_section("Test BR-A-031: DELETE /brokers - with transactions no force")

    async with httpx.AsyncClient() as client:
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
async def test_delete_brokers_with_tx_force(test_server):
    """BR-A-032: DELETE broker with transactions with force succeeds."""
    print_section("Test BR-A-032: DELETE /brokers - with transactions force")

    async with httpx.AsyncClient() as client:
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

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
from datetime import date, datetime, timedelta
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


async def create_brokers(client: httpx.AsyncClient, *prefixes: str, allow_cash_overdraft: bool = False) -> list[int]:
    """One broker per prefix, uniquely named, owned by the client's user: their ids, in the order of ``prefixes``."""
    names = [unique_name(prefix) for prefix in prefixes]
    resp = await client.post(f"{API_BASE}/brokers", json=[{"name": name, "allow_cash_overdraft": allow_cash_overdraft} for name in names], timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    results = {result["name"]: result for result in resp.json()["results"]}
    assert all(results.get(name, {}).get("success") for name in names), resp.text
    return [results[name]["broker_id"] for name in names]


async def create_assets(client: httpx.AsyncClient, *prefixes: str, currency: str = "EUR") -> list[int]:
    """One STOCK asset per prefix, uniquely named: their ids, in the order of ``prefixes``."""
    names = [unique_name(prefix) for prefix in prefixes]
    resp = await client.post(f"{API_BASE}/assets", json=[{"display_name": name, "asset_type": "STOCK", "currency": currency} for name in names], timeout=TIMEOUT)
    assert resp.status_code in (200, 201), resp.text
    results = {result["display_name"]: result for result in resp.json()["results"]}
    assert all(results.get(name, {}).get("success") for name in names), resp.text
    return [results[name]["asset_id"] for name in names]


async def commit_creates(client: httpx.AsyncClient, creates: list[dict]) -> list[int]:
    """Commit ``creates`` in one batch: the new transaction ids, in the order of ``creates``."""
    resp = await client.post(f"{API_BASE}/transactions/commit", json={"creates": creates}, timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["committed"] is True, f"Commit rejected: {body.get('issues')}"
    ids = {result["index"]: result["ids"] for result in body["results"] if result["operation"] == "create"}
    assert sorted(ids) == list(range(len(creates))) and all(len(tx_ids) == 1 for tx_ids in ids.values()), body
    return [ids[index][0] for index in range(len(creates))]


async def read_transactions(client: httpx.AsyncClient, tx_ids: list[int]) -> dict[int, dict]:
    """The transactions among ``tx_ids`` that exist and the client's user can see, by id."""
    resp = await client.get(f"{API_BASE}/transactions", params={"ids": tx_ids}, timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    return {transaction["id"]: transaction for transaction in resp.json()}


async def get_summary(client: httpx.AsyncClient, broker_id: int, as_of: Optional[date] = None) -> dict:
    """GET /brokers/{id}/summary as of ``as_of``; without it, as of the server's today."""
    params = {} if as_of is None else {"as_of": as_of.isoformat()}
    resp = await client.get(f"{API_BASE}/brokers/{broker_id}/summary", params=params, timeout=TIMEOUT)
    assert resp.status_code == 200, f"Summary of broker {broker_id} as of {as_of}: {resp.status_code} {resp.text}"
    summary = resp.json()
    assert summary["id"] == broker_id, summary
    return summary


def money(value: Optional[dict]) -> Optional[tuple[str, Decimal]]:
    """An API ``{code, amount}`` object as (code, Decimal amount), compared by value whatever its JSON form; None when absent."""
    return None if value is None else (value["code"], Decimal(str(value["amount"])))


def cash_by_currency(summary: dict) -> dict[str, Decimal]:
    """A summary's cash lines, by currency."""
    codes = [balance["code"] for balance in summary["cash_balances"]]
    assert len(codes) == len(set(codes)), f"One cash line per currency: {summary['cash_balances']}"
    return {balance["code"]: Decimal(str(balance["amount"])) for balance in summary["cash_balances"]}


def holdings_by_asset(summary: dict) -> dict[int, dict]:
    """A summary's holdings, by asset id: quantity, total cost and average cost per unit."""
    asset_ids = [holding["asset_id"] for holding in summary["holdings"]]
    assert len(asset_ids) == len(set(asset_ids)), f"One holding per asset: {summary['holdings']}"
    return {
        holding["asset_id"]: {
            "quantity": Decimal(str(holding["quantity"])),
            "total_cost": money(holding["total_cost"]),
            "average_cost": None if holding["average_cost_per_unit"] is None else Decimal(str(holding["average_cost_per_unit"])),
        }
        for holding in summary["holdings"]
    }


async def remove_owned(client: httpx.AsyncClient, broker_ids: list[int], asset_ids: list[int]) -> list[str]:
    """Whoever writes, cleans up: force-delete the test's brokers, their transactions with them, then its assets.

    ``broker_ids`` lists the brokers still standing: a test that deletes one itself takes it off
    the list. Returns what could not be removed: the caller fails on it, also after a red.
    """
    errors: list[str] = []
    if broker_ids:
        resp = await client.delete(f"{API_BASE}/brokers", params={"ids": broker_ids, "force": True}, timeout=TIMEOUT)
        deleted = {result["id"] for result in resp.json()["results"] if result["success"]} if resp.status_code == 200 else set()
        errors += [f"Broker {broker_id} not deleted: {resp.status_code} {resp.text}" for broker_id in broker_ids if broker_id not in deleted]
    if asset_ids:
        resp = await client.delete(f"{API_BASE}/assets", params={"asset_ids": asset_ids}, timeout=TIMEOUT)
        deleted = {result["asset_id"] for result in resp.json()["results"] if result["success"]} if resp.status_code == 200 else set()
        errors += [f"Asset {asset_id} not deleted: {resp.status_code} {resp.text}" for asset_id in asset_ids if asset_id not in deleted]
    return errors


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
    @pytest.mark.parametrize("amount", ["1E+101", "1E+5000000"])
    async def test_post_brokers_with_an_initial_balance_past_the_exponent_bound_answers_422_and_creates_nothing(self, test_server, amount):
        """R13-SEC7-3 (E's R13-SEC7, finding 3): an initial balance is a ``Currency``, whose amount's exponent is bounded
        at the boundary (``adjusted()`` within [-100, 100]).

        Red today: 200 — the service expands the amount with ``format(amount, "f")`` (5 MB for 1E+5000000), the batch
        refuses the deposit, and the route rolls the broker back.

        Contract: 422 before any work, its error on ``initial_balances.0.amount``; no broker of that name exists.
        """
        print_section(f"Test BR-A-002C: POST /brokers - initial balance of {amount} EUR, past the exponent bound")

        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            name = unique_name("R13-SEC7-3 Exponent Bound Broker")

            response = await client.post(f"{API_BASE}/brokers", json=[{"name": name, "initial_balances": [{"code": "EUR", "amount": amount}]}], timeout=TIMEOUT)

            listed = await client.get(f"{API_BASE}/brokers", timeout=TIMEOUT)
            assert listed.status_code == 200, listed.text
            created = [broker["id"] for broker in listed.json()["items"] if broker["name"] == name]
            # Whoever writes cleans up, also after a red.
            leftovers = await remove_owned(client, created, [])

            assert response.status_code == 422, f"R13-SEC7-3: POST /brokers with an initial balance of {amount} EUR must answer 422 at the boundary; it answered {response.status_code}: {response.text[:400]}"
            locs = [tuple(error["loc"]) for error in response.json()["detail"]]
            assert any(loc[-3:] == ("initial_balances", 0, "amount") for loc in locs), f"R13-SEC7-3: the 422 must name the balance's amount; its errors sit on {locs}"
            assert created == [], f"R13-SEC7-3: the request was refused, yet the broker {name!r} exists: {created}"
            assert leftovers == [], f"Cleanup failed: {leftovers}"
            print_success(f"✓ Initial balance of {amount} EUR refused with 422, nothing created")

    @pytest.mark.asyncio
    async def test_post_brokers_duplicate(self, test_server):
        """BR-A-003: POST /brokers with existing name fails."""
        print_section("Test BR-A-003: POST /brokers - duplicate name")

        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            name = unique_name("Duplicate Broker")

            # Create first
            payload1 = [{"name": name}]
            create_response = await client.post(f"{API_BASE}/brokers", json=payload1, timeout=TIMEOUT)
            assert create_response.status_code == 200, create_response.text
            create_data = create_response.json()
            assert create_data["success_count"] == 1
            assert create_data["results"][0]["success"] is True
            assert create_data["results"][0]["name"] == name
            assert create_data["results"][0]["broker_id"] is not None

            # Try duplicate
            payload2 = [{"name": name}]
            response = await client.post(
                f"{API_BASE}/brokers",
                json=payload2,
                timeout=TIMEOUT,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success_count"] == 0
            assert len(data["results"]) == 1
            assert data["results"][0]["success"] is False
            assert data["results"][0]["broker_id"] is None
            assert data["results"][0]["name"] == name
            assert data["results"][0]["deposits_created"] == 0
            assert set(data["results"][0].keys()) == {"success", "broker_id", "name", "deposits_created", "error"}

            error_msg = data["results"][0]["error"]
            assert error_msg.startswith(f"You already have a broker named '{name}'")
            assert error_msg.endswith("To resolve this, rename the existing broker or choose a different name for the broker you are adding.")

            print_success("✓ Got error for duplicate name")

    @pytest.mark.asyncio
    async def test_post_brokers_duplicate_other_owner(self, test_server):
        """BR-A-003B: Duplicate broker names report the owning user's prefix."""
        print_section("Test BR-A-003B: POST /brokers - duplicate name across owners")

        async with httpx.AsyncClient() as owner_client, httpx.AsyncClient() as other_client:
            owner_username, _, _ = await create_test_user(owner_client)
            await create_test_user(other_client)
            name = unique_name("Cross Owner Broker")

            create_response = await owner_client.post(f"{API_BASE}/brokers", json=[{"name": name}], timeout=TIMEOUT)
            assert create_response.status_code == 200, create_response.text
            assert create_response.json()["success_count"] == 1

            response = await other_client.post(f"{API_BASE}/brokers", json=[{"name": name}], timeout=TIMEOUT)

            assert response.status_code == 200
            data = response.json()
            assert data["success_count"] == 0
            assert len(data["results"]) == 1
            assert data["results"][0]["success"] is False
            assert data["results"][0]["broker_id"] is None
            assert data["results"][0]["name"] == name
            assert data["results"][0]["deposits_created"] == 0
            assert set(data["results"][0].keys()) == {"success", "broker_id", "name", "deposits_created", "error"}

            error_msg = data["results"][0]["error"]
            assert error_msg.startswith(f"Broker '{name}' already exists (owned by '{owner_username}')")
            assert error_msg.endswith("To resolve this, rename the existing broker or choose a different name for the broker you are adding.")

            print_success("✓ Got owner-specific duplicate error for another user")

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
            assert data["results"][0]["transaction_count"] >= 1
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
    async def test_delete_brokers_with_cross_broker_link_force(self, test_server):
        """BR-A-032C: Force delete of the sending broker leaves the incoming half of a cross-broker TRANSFER as the ADJUSTMENT a split of the pair leaves: unlinked, same quantity and cost basis (V-3, D-J4)."""
        print_section("Test BR-A-032C: DELETE /brokers - force turns the surviving TRANSFER half into an ADJUSTMENT")

        async with httpx.AsyncClient() as client:
            await create_test_user(client)

            broker_resp = await client.post(
                f"{API_BASE}/brokers",
                json=[
                    {"name": unique_name("Force Delete Link Source"), "allow_cash_overdraft": True},
                    {"name": unique_name("Force Delete Link Target"), "allow_cash_overdraft": True},
                ],
                timeout=TIMEOUT,
            )
            assert broker_resp.status_code == 200, broker_resp.text
            broker1_id = broker_resp.json()["results"][0]["broker_id"]
            broker2_id = broker_resp.json()["results"][1]["broker_id"]

            asset_resp = await client.post(
                f"{API_BASE}/assets",
                json=[{"display_name": unique_name("Force Delete Link Asset"), "asset_type": "STOCK", "currency": "EUR"}],
                timeout=TIMEOUT,
            )
            assert asset_resp.status_code in (200, 201), asset_resp.text
            asset_id = asset_resp.json()["results"][0]["asset_id"]

            seed_resp = await client.post(
                f"{API_BASE}/transactions/commit",
                json={"creates": [{"broker_id": broker1_id, "asset_id": asset_id, "type": "ADJUSTMENT", "date": date.today().isoformat(), "quantity": "10", "cost_basis_override": {"code": "EUR", "amount": "100"}}]},
                timeout=TIMEOUT,
            )
            assert seed_resp.status_code == 200, seed_resp.text
            assert seed_resp.json()["committed"] is True

            link_uuid = str(uuid.uuid4())
            create_resp = await client.post(
                f"{API_BASE}/transactions/commit",
                json={
                    "creates": [
                        {"broker_id": broker1_id, "asset_id": asset_id, "type": "TRANSFER", "date": date.today().isoformat(), "quantity": "-5", "link_uuid": link_uuid},
                        {"broker_id": broker2_id, "asset_id": asset_id, "type": "TRANSFER", "date": date.today().isoformat(), "quantity": "5", "link_uuid": link_uuid, "cost_basis_mode": "auto"},
                    ]
                },
                timeout=TIMEOUT,
            )
            assert create_resp.status_code == 200, create_resp.text
            assert create_resp.json()["committed"] is True
            target_tx_id = create_resp.json()["results"][1]["ids"][0]
            source_tx_id = next(result["ids"][0] for result in create_resp.json()["results"] if result["index"] == 0)

            legs_before = await read_transactions(client, [source_tx_id, target_tx_id])
            assert {tx_id: (tx["broker_id"], tx["type"], tx["related_transaction_id"]) for tx_id, tx in legs_before.items()} == {
                source_tx_id: (broker1_id, "TRANSFER", target_tx_id),
                target_tx_id: (broker2_id, "TRANSFER", source_tx_id),
            }, f"Precondition: the two legs must be a linked cross-broker TRANSFER pair: {legs_before}"
            target_before = legs_before[target_tx_id]
            assert money(target_before["cost_basis_override"]) is not None, f"Precondition: cost_basis_mode=auto must give the incoming leg a cost basis: {target_before}"

            delete_resp = await client.delete(
                f"{API_BASE}/brokers",
                params={"ids": [broker1_id], "force": True},
                timeout=TIMEOUT,
            )
            assert delete_resp.status_code == 200, delete_resp.text
            delete_data = delete_resp.json()
            assert delete_data["results"][0]["success"] is True
            assert delete_data["results"][0]["transactions_deleted"] >= 2

            get_resp = await client.get(f"{API_BASE}/transactions", params={"ids": [target_tx_id]}, timeout=TIMEOUT)
            assert get_resp.status_code == 200, get_resp.text
            txs = get_resp.json()
            assert len(txs) == 1
            assert txs[0]["broker_id"] == broker2_id
            assert txs[0]["related_transaction_id"] is None
            assert txs[0]["partner_broker_id"] is None
            # V-3, D-J4: the sending broker is gone, so the incoming half becomes the ADJUSTMENT a split of the pair leaves, not an unpaired TRANSFER.
            survivor = {"type": txs[0]["type"], "quantity": Decimal(str(txs[0]["quantity"])), "cost_basis": money(txs[0]["cost_basis_override"]), "asset_id": txs[0]["asset_id"], "date": txs[0]["date"]}
            assert survivor == {
                "type": "ADJUSTMENT",
                "quantity": Decimal("5"),
                "cost_basis": money(target_before["cost_basis_override"]),
                "asset_id": asset_id,
                "date": target_before["date"],
            }, f"The surviving half must become the ADJUSTMENT a split of the pair leaves: {txs[0]}"

            print_success("✓ Force delete left the surviving TRANSFER half as the unlinked ADJUSTMENT a split leaves, quantity and cost basis kept")

    @pytest.mark.asyncio
    async def test_delete_brokers_with_cross_broker_cash_transfer_force(self, test_server):
        """BR-A-032D: Force delete of the receiving broker leaves the sender's half of a cross-broker CASH_TRANSFER as the WITHDRAWAL a split of the pair leaves: same negative amount and currency, date, description and tags, unlinked (V-3, D-J4)."""
        print_section("Test BR-A-032D: DELETE /brokers - force turns the surviving CASH_TRANSFER half into a WITHDRAWAL")

        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_ids: list[int] = []
            try:
                broker_ids += await create_brokers(client, "Force Delete Cash Sender", "Force Delete Cash Receiver", allow_cash_overdraft=True)
                sender_id, receiver_id = broker_ids
                link_uuid = str(uuid.uuid4())
                day = date.today().isoformat()
                # A pair carries the same description and tags on both halves (TestPairDescriptionTagsValidation).
                description = unique_name("Force Delete Cash Transfer")
                tags = ["cash-pair", "force-delete"]
                sender_leg, receiver_leg = await commit_creates(
                    client,
                    [
                        {"broker_id": sender_id, "type": "CASH_TRANSFER", "date": day, "cash": {"code": "EUR", "amount": "-300"}, "link_uuid": link_uuid, "description": description, "tags": tags},
                        {"broker_id": receiver_id, "type": "CASH_TRANSFER", "date": day, "cash": {"code": "EUR", "amount": "300"}, "link_uuid": link_uuid, "description": description, "tags": tags},
                    ],
                )
                legs = await read_transactions(client, [sender_leg, receiver_leg])
                assert {tx_id: (tx["type"], tx["related_transaction_id"], tx["partner_broker_id"]) for tx_id, tx in legs.items()} == {
                    sender_leg: ("CASH_TRANSFER", receiver_leg, receiver_id),
                    receiver_leg: ("CASH_TRANSFER", sender_leg, sender_id),
                }, f"Precondition: the two legs must be a linked cross-broker CASH_TRANSFER pair: {legs}"

                delete_resp = await client.delete(f"{API_BASE}/brokers", params={"ids": [receiver_id], "force": True}, timeout=TIMEOUT)
                assert delete_resp.status_code == 200, delete_resp.text
                deleted = next((result for result in delete_resp.json()["results"] if result["id"] == receiver_id), None)
                assert deleted is not None and (deleted["success"], deleted["transactions_deleted"]) == (True, 1), delete_resp.text
                broker_ids.remove(receiver_id)

                after = await read_transactions(client, [sender_leg, receiver_leg])
                assert set(after) == {sender_leg}, f"The receiver's half must go with its broker and the sender's stay: {after}"
                leg = after[sender_leg]
                survivor = {
                    "type": leg["type"],
                    "broker_id": leg["broker_id"],
                    "asset_id": leg["asset_id"],
                    "date": leg["date"],
                    "quantity": Decimal(str(leg["quantity"])),
                    "cash": money(leg["cash"]),
                    "description": leg["description"],
                    "tags": sorted(leg["tags"] or []),
                    "related_transaction_id": leg["related_transaction_id"],
                    "partner_broker_id": leg["partner_broker_id"],
                }
                assert survivor == {
                    "type": "WITHDRAWAL",
                    "broker_id": sender_id,
                    "asset_id": None,
                    "date": day,
                    "quantity": Decimal("0"),
                    "cash": ("EUR", Decimal("-300")),
                    "description": description,
                    "tags": sorted(tags),
                    "related_transaction_id": None,
                    "partner_broker_id": None,
                }, f"The sender's half must become the WITHDRAWAL a split of the pair leaves (V-3, D-J4): {leg}"

                print_success("✓ Force delete left the sender's CASH_TRANSFER half as the unlinked WITHDRAWAL a split leaves, same amount")
            finally:
                cleanup_errors = await remove_owned(client, broker_ids, [])
                assert not cleanup_errors, f"Owned data cleanup failed: {cleanup_errors}"

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
            assert result_by_id[blocked_broker_id]["transaction_count"] >= 1
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


# ============================================================================
# BROKER API - SUMMARY AS OF A DAY (W-B5)
# ============================================================================
#
# GET /brokers/{id}/summary describes the broker on one day: ``as_of`` (YYYY-MM-DD), the user's
# today; the server's date when omitted. A transaction dated later counts in none of its figures:
# cash per currency, holdings, their cost. The API accepts future-dated transactions, which is how
# the broker page came to count them as today's cash (W-B5). Same semantics as the service tests
# test_broker_service.py::TestGetSummaryAsOf (BR-U-090..093).
#
# Every row is dated from date.today(), read once per test. Only BR-A-070 reads the server's day
# (no as_of), and it checks that the day did not change while it ran.

# (day offset from today, type, currency, amount): EUR deposited two days ago and tomorrow; USD in
# and out before today, so that its movements cancel out.
AS_OF_CASH_ROWS = (
    (-2, "DEPOSIT", "EUR", "1000"),
    (-2, "DEPOSIT", "USD", "100"),
    (-1, "WITHDRAWAL", "USD", "-100"),
    (1, "DEPOSIT", "EUR", "250"),  # tomorrow: a future-dated row
)
# The broker's cash as of each day offset, counting the rows dated up to that day inclusive.
AS_OF_CASH_VIEWS = {
    -3: {},  # the day before every row: no currency has a line
    -2: {"EUR": "1000", "USD": "100"},  # the first rows' own day: they count
    0: {"EUR": "1000", "USD": "0"},  # today: not tomorrow's deposit; USD, whose movements cancel out, keeps its line at zero
    1: {"EUR": "1250", "USD": "0"},  # tomorrow: every row
}


def as_of_cash_creates(broker_id: int, today: date) -> list[dict]:
    """The AS_OF_CASH_ROWS of a broker, dated from ``today``."""
    return [{"broker_id": broker_id, "type": tx_type, "date": (today + timedelta(days=offset)).isoformat(), "cash": {"code": code, "amount": amount}} for offset, tx_type, code, amount in AS_OF_CASH_ROWS]


def as_of_cash_view(offset: int) -> dict[str, Decimal]:
    """The cash AS_OF_CASH_VIEWS expects as of ``today + offset``."""
    return {code: Decimal(amount) for code, amount in AS_OF_CASH_VIEWS[offset].items()}


def eur_holding(quantity: str, total_cost: str, average_cost: str) -> dict:
    """A holding of an EUR asset, as holdings_by_asset reads it."""
    return {"quantity": Decimal(quantity), "total_cost": ("EUR", Decimal(total_cost)), "average_cost": Decimal(average_cost)}


class TestBrokerSummaryAsOf:
    """GET /brokers/{id}/summary as of a day: the caller's ``as_of``; without it, the server's today."""

    @pytest.mark.asyncio
    async def test_summary_without_as_of_reads_the_server_today(self, test_server):
        """BR-A-070: Without as_of the summary is the server's today: the EUR deposit of two days ago counts, tomorrow's does not; it reads exactly as as_of=today."""
        print_section("Test BR-A-070: GET /brokers/{id}/summary - without as_of, the server's today")

        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_ids: list[int] = []
            try:
                broker_ids += await create_brokers(client, "Summary AsOf Default")
                (broker_id,) = broker_ids
                today = date.today()
                await commit_creates(client, as_of_cash_creates(broker_id, today))

                omitted = await get_summary(client, broker_id)
                assert date.today() == today, f"Precondition broken: the server's day moved from {today} to {date.today()} during the test — rerun it"
                explicit = await get_summary(client, broker_id, as_of=today)

                assert cash_by_currency(omitted) == as_of_cash_view(0), "Tomorrow's deposit must not count in today's cash (W-B5)"
                assert omitted == explicit, "Without as_of the summary must read exactly as as_of=today"

                print_success("✓ Without as_of, tomorrow's deposit is not in today's cash")
            finally:
                cleanup_errors = await remove_owned(client, broker_ids, [])
                assert not cleanup_errors, f"Owned data cleanup failed: {cleanup_errors}"

    @pytest.mark.asyncio
    async def test_summary_as_of_counts_the_rows_up_to_that_day_inclusive(self, test_server):
        """BR-A-071: as_of decides, not the server's date: as of tomorrow both EUR deposits count; as of the first rows' day they count; as of the day before every row no currency has a line."""
        print_section("Test BR-A-071: GET /brokers/{id}/summary?as_of - cash up to that day inclusive")

        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_ids: list[int] = []
            try:
                broker_ids += await create_brokers(client, "Summary AsOf Cash")
                (broker_id,) = broker_ids
                today = date.today()
                await commit_creates(client, as_of_cash_creates(broker_id, today))

                views = {offset: cash_by_currency(await get_summary(client, broker_id, as_of=today + timedelta(days=offset))) for offset in AS_OF_CASH_VIEWS}

                assert views == {offset: as_of_cash_view(offset) for offset in AS_OF_CASH_VIEWS}

                print_success("✓ as_of counts the rows up to that day inclusive, and none after")
            finally:
                cleanup_errors = await remove_owned(client, broker_ids, [])
                assert not cleanup_errors, f"Owned data cleanup failed: {cleanup_errors}"

    @pytest.mark.asyncio
    async def test_summary_as_of_leaves_out_a_future_purchase(self, test_server):
        """BR-A-072: A BUY dated tomorrow is in no figure of today's summary (not its units, their cost, the cash paid) and in all of them as of its own day."""
        print_section("Test BR-A-072: GET /brokers/{id}/summary?as_of - holdings")

        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_ids: list[int] = []
            asset_ids: list[int] = []
            try:
                broker_ids += await create_brokers(client, "Summary AsOf Holdings", allow_cash_overdraft=True)
                (broker_id,) = broker_ids
                asset_ids += await create_assets(client, "Summary AsOf Held", "Summary AsOf Future")
                held, future_only = asset_ids
                today = date.today()
                tomorrow = today + timedelta(days=1)
                await commit_creates(
                    client,
                    [
                        # 10 @ 100, two days ago
                        {"broker_id": broker_id, "asset_id": held, "type": "BUY", "date": (today - timedelta(days=2)).isoformat(), "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
                        # 10 more @ 300, tomorrow
                        {"broker_id": broker_id, "asset_id": held, "type": "BUY", "date": tomorrow.isoformat(), "quantity": "10", "cash": {"code": "EUR", "amount": "-3000"}},
                        # 4 @ 200, tomorrow: the only row of this asset
                        {"broker_id": broker_id, "asset_id": future_only, "type": "BUY", "date": tomorrow.isoformat(), "quantity": "4", "cash": {"code": "EUR", "amount": "-800"}},
                    ],
                )

                views = {}
                for label, as_of in (("today", today), ("tomorrow", tomorrow)):
                    summary = await get_summary(client, broker_id, as_of=as_of)
                    views[label] = {"cash": cash_by_currency(summary), "holdings": holdings_by_asset(summary)}

                assert views == {
                    "today": {"cash": {"EUR": Decimal("-1000")}, "holdings": {held: eur_holding("10", "1000", "100")}},
                    "tomorrow": {"cash": {"EUR": Decimal("-4800")}, "holdings": {held: eur_holding("20", "4000", "200"), future_only: eur_holding("4", "800", "200")}},
                }

                print_success("✓ Tomorrow's purchases are out of today's holdings, cost and cash, and in tomorrow's")
            finally:
                cleanup_errors = await remove_owned(client, broker_ids, asset_ids)
                assert not cleanup_errors, f"Owned data cleanup failed: {cleanup_errors}"

    @pytest.mark.asyncio
    async def test_summary_as_of_not_a_date_is_rejected(self, test_server):
        """BR-A-073: as_of=not-a-date answers 422 on the as_of query parameter, where the same broker as of a real day answers 200."""
        print_section("Test BR-A-073: GET /brokers/{id}/summary?as_of=not-a-date - 422")

        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_ids: list[int] = []
            try:
                broker_ids += await create_brokers(client, "Summary AsOf Invalid")
                (broker_id,) = broker_ids
                await get_summary(client, broker_id, as_of=date.today())

                response = await client.get(f"{API_BASE}/brokers/{broker_id}/summary", params={"as_of": "not-a-date"}, timeout=TIMEOUT)

                assert response.status_code == 422, response.text
                assert [error["loc"] for error in response.json()["detail"]] == [["query", "as_of"]], response.text

                print_success("✓ as_of=not-a-date rejected with 422 on as_of")
            finally:
                cleanup_errors = await remove_owned(client, broker_ids, [])
                assert not cleanup_errors, f"Owned data cleanup failed: {cleanup_errors}"

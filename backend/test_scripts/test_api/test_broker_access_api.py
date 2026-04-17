"""
Broker Access API Tests.

Tests for broker access management endpoints:
- GET /brokers/{id}/access: List users with access
- PUT /brokers/{id}/access: Bulk replace access configuration (atomic)

Tests role hierarchy: OWNER > EDITOR > VIEWER
Tests multi-user isolation and superuser capabilities.

After refactoring: individual POST/PATCH/DELETE endpoints replaced
by a single PUT bulk endpoint.
"""

import uuid
from datetime import datetime
from typing import Optional

import httpx
import pytest

from backend.app.config import get_settings
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30


def unique_name(prefix: str) -> str:
    """Generate a unique name using UUID."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def unique_username() -> str:
    """Generate a unique username."""
    timestamp = int(datetime.now().timestamp() * 1000)
    return f"access_test_{timestamp}"


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def create_user_and_login(client: httpx.AsyncClient, username: Optional[str] = None) -> tuple[int, str, str, Optional[str]]:
    """
    Create a new user, login, and return (user_id, username, email, session).
    Sets session cookie on client.
    """
    username = username or unique_username()
    email = f"{username}@test.com"
    password = "TestPass123!"

    resp = await client.post(
        f"{API_BASE}/auth/register",
        json={"username": username, "email": email, "password": password},
        timeout=TIMEOUT,
    )

    if resp.status_code != 201:
        raise Exception(f"Failed to create user: {resp.text}")

    user_id = resp.json()["user"]["id"]

    login_resp = await client.post(f"{API_BASE}/auth/login", json={"username": username, "password": password}, timeout=TIMEOUT)

    session = login_resp.cookies.get("session")
    if session:
        client.cookies.set("session", session)

    return user_id, username, email, session


async def create_broker(client: httpx.AsyncClient, name: Optional[str] = None) -> int:
    """Create a broker and return its ID."""
    name = name or unique_name("Broker")
    payload = [{"name": name}]
    resp = await client.post(f"{API_BASE}/brokers", json=payload, timeout=TIMEOUT)
    assert resp.status_code == 200, f"Failed to create broker: {resp.text}"
    return resp.json()["results"][0]["broker_id"]


async def get_access_list(client: httpx.AsyncClient, broker_id: int) -> list:
    """Get the current access list for a broker."""
    resp = await client.get(f"{API_BASE}/brokers/{broker_id}/access", timeout=TIMEOUT)
    assert resp.status_code == 200, f"Failed to get access list: {resp.text}"
    return resp.json()["items"]


async def bulk_set_access(client: httpx.AsyncClient, broker_id: int, accesses: list) -> httpx.Response:
    """Send bulk access update. Returns the raw response."""
    return await client.put(
        f"{API_BASE}/brokers/{broker_id}/access",
        json=accesses,
        timeout=TIMEOUT,
    )


async def add_user_via_bulk(
    owner_client: httpx.AsyncClient,
    broker_id: int,
    owner_id: int,
    target_user_id: int,
    role: str,
    share_pct: float = 0,
    owner_share: float = 1.0,
) -> httpx.Response:
    """Helper: add a user by sending bulk with current owner + new user."""
    accesses = [
        {"user_id": owner_id, "role": "OWNER", "share_percentage": owner_share},
        {"user_id": target_user_id, "role": role, "share_percentage": share_pct},
    ]
    return await bulk_set_access(owner_client, broker_id, accesses)


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
# ACCESS LIST TESTS
# ============================================================================


class TestAccessList:
    """Tests for GET /brokers/{id}/access."""

    @pytest.mark.asyncio
    async def test_list_access_as_owner(self, test_server):
        """ACCESS-001: GET /brokers/{id}/access - owner can list."""
        print_section("ACCESS-001: List access as owner")

        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)
            broker_id = await create_broker(client)

            response = await client.get(
                f"{API_BASE}/brokers/{broker_id}/access",
                timeout=TIMEOUT,
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 1
            assert data["items"][0]["role"] == "OWNER"

            print_success("✓ Owner can list access")

    @pytest.mark.asyncio
    async def test_list_access_no_access(self, test_server):
        """ACCESS-002: GET /brokers/{id}/access - 404 without access."""
        print_section("ACCESS-002: List access without permission")

        async with httpx.AsyncClient() as client1, httpx.AsyncClient() as client2:
            await create_user_and_login(client1)
            broker_id = await create_broker(client1)

            await create_user_and_login(client2)
            response = await client2.get(
                f"{API_BASE}/brokers/{broker_id}/access",
                timeout=TIMEOUT,
            )

            assert response.status_code == 404

            print_success("✓ Got 404 without access")


# ============================================================================
# BULK ACCESS ADD TESTS (via PUT bulk)
# ============================================================================


class TestBulkAddAccess:
    """Tests for adding access via PUT /brokers/{id}/access."""

    @pytest.mark.asyncio
    async def test_owner_adds_viewer(self, test_server):
        """ACCESS-010: OWNER can add VIEWER via bulk."""
        print_section("ACCESS-010: Owner adds viewer")

        async with httpx.AsyncClient() as client1, httpx.AsyncClient() as client2:
            user1_id, _, _, _ = await create_user_and_login(client1)
            broker_id = await create_broker(client1)
            user2_id, _, _, _ = await create_user_and_login(client2)

            resp = await add_user_via_bulk(client1, broker_id, user1_id, user2_id, "VIEWER")
            assert resp.status_code == 200
            assert resp.json()["success_count"] == 2
            assert len(resp.json()["results"]) == 2

            # Verify the viewer was added
            accesses = await get_access_list(client1, broker_id)
            viewer = next((a for a in accesses if a["user_id"] == user2_id), None)
            assert viewer is not None
            assert viewer["role"] == "VIEWER"

            print_success("✓ Owner added viewer")

    @pytest.mark.asyncio
    async def test_owner_adds_editor(self, test_server):
        """ACCESS-011: OWNER can add EDITOR via bulk."""
        print_section("ACCESS-011: Owner adds editor")

        async with httpx.AsyncClient() as client1, httpx.AsyncClient() as client2:
            user1_id, _, _, _ = await create_user_and_login(client1)
            broker_id = await create_broker(client1)
            user2_id, _, _, _ = await create_user_and_login(client2)

            resp = await add_user_via_bulk(client1, broker_id, user1_id, user2_id, "EDITOR")
            assert resp.status_code == 200

            accesses = await get_access_list(client1, broker_id)
            editor = next((a for a in accesses if a["user_id"] == user2_id), None)
            assert editor is not None
            assert editor["role"] == "EDITOR"

            print_success("✓ Owner added editor")

    @pytest.mark.asyncio
    async def test_owner_adds_second_owner(self, test_server):
        """ACCESS-012: OWNER can add another OWNER via bulk."""
        print_section("ACCESS-012: Owner adds another owner")

        async with httpx.AsyncClient() as client1, httpx.AsyncClient() as client2:
            user1_id, _, _, _ = await create_user_and_login(client1)
            broker_id = await create_broker(client1)
            user2_id, _, _, _ = await create_user_and_login(client2)

            resp = await bulk_set_access(
                client1,
                broker_id,
                [
                    {"user_id": user1_id, "role": "OWNER", "share_percentage": 0.5},
                    {"user_id": user2_id, "role": "OWNER", "share_percentage": 0.5},
                ],
            )
            assert resp.status_code == 200

            accesses = await get_access_list(client1, broker_id)
            owner2 = next((a for a in accesses if a["user_id"] == user2_id), None)
            assert owner2 is not None
            assert owner2["role"] == "OWNER"

            print_success("✓ Owner added another owner")

    @pytest.mark.asyncio
    async def test_non_owner_cannot_bulk_update(self, test_server):
        """ACCESS-013: Non-OWNER cannot call bulk update."""
        print_section("ACCESS-013: Non-owner cannot manage access")

        async with httpx.AsyncClient() as client1, httpx.AsyncClient() as client2, httpx.AsyncClient() as client3:
            user1_id, _, _, _ = await create_user_and_login(client1)
            broker_id = await create_broker(client1)
            user2_id, _, _, _ = await create_user_and_login(client2)
            user3_id, _, _, _ = await create_user_and_login(client3)

            # Add user2 as EDITOR
            await add_user_via_bulk(client1, broker_id, user1_id, user2_id, "EDITOR")

            # User2 (EDITOR) tries to modify access → rejected
            resp = await bulk_set_access(
                client2,
                broker_id,
                [
                    {"user_id": user1_id, "role": "OWNER", "share_percentage": 1.0},
                    {"user_id": user2_id, "role": "EDITOR", "share_percentage": 0},
                    {"user_id": user3_id, "role": "VIEWER", "share_percentage": 0},
                ],
            )
            assert resp.status_code == 403

            print_success("✓ Non-owner correctly rejected")

    @pytest.mark.asyncio
    async def test_add_nonexistent_user(self, test_server):
        """ACCESS-017: Cannot add non-existent user."""
        print_section("ACCESS-017: Non-existent user")

        async with httpx.AsyncClient() as client:
            user_id, _, _, _ = await create_user_and_login(client)
            broker_id = await create_broker(client)

            resp = await bulk_set_access(
                client,
                broker_id,
                [
                    {"user_id": user_id, "role": "OWNER", "share_percentage": 1.0},
                    {"user_id": 999999, "role": "VIEWER", "share_percentage": 0},
                ],
            )
            assert resp.status_code == 400
            assert "not found" in resp.json()["detail"]

            print_success("✓ Non-existent user correctly rejected")


# ============================================================================
# BULK ACCESS UPDATE TESTS (role changes via PUT bulk)
# ============================================================================


class TestBulkUpdateAccess:
    """Tests for updating roles via PUT /brokers/{id}/access."""

    @pytest.mark.asyncio
    async def test_promote_viewer_to_editor(self, test_server):
        """ACCESS-020: OWNER promotes VIEWER to EDITOR via bulk."""
        print_section("ACCESS-020: Promote viewer to editor")

        async with httpx.AsyncClient() as client1, httpx.AsyncClient() as client2:
            user1_id, _, _, _ = await create_user_and_login(client1)
            broker_id = await create_broker(client1)
            user2_id, _, _, _ = await create_user_and_login(client2)

            # Add as viewer
            await add_user_via_bulk(client1, broker_id, user1_id, user2_id, "VIEWER")

            # Promote to editor via bulk
            resp = await bulk_set_access(
                client1,
                broker_id,
                [
                    {"user_id": user1_id, "role": "OWNER", "share_percentage": 1.0},
                    {"user_id": user2_id, "role": "EDITOR", "share_percentage": 0},
                ],
            )
            assert resp.status_code == 200

            accesses = await get_access_list(client1, broker_id)
            user2_acc = next(a for a in accesses if a["user_id"] == user2_id)
            assert user2_acc["role"] == "EDITOR"

            print_success("✓ Promoted to editor")

    @pytest.mark.asyncio
    async def test_degrade_editor_to_viewer(self, test_server):
        """ACCESS-021: OWNER degrades EDITOR to VIEWER via bulk."""
        print_section("ACCESS-021: Degrade editor to viewer")

        async with httpx.AsyncClient() as client1, httpx.AsyncClient() as client2:
            user1_id, _, _, _ = await create_user_and_login(client1)
            broker_id = await create_broker(client1)
            user2_id, _, _, _ = await create_user_and_login(client2)

            # Add as editor
            await add_user_via_bulk(client1, broker_id, user1_id, user2_id, "EDITOR")

            # Degrade to viewer
            resp = await bulk_set_access(
                client1,
                broker_id,
                [
                    {"user_id": user1_id, "role": "OWNER", "share_percentage": 1.0},
                    {"user_id": user2_id, "role": "VIEWER", "share_percentage": 0},
                ],
            )
            assert resp.status_code == 200

            accesses = await get_access_list(client1, broker_id)
            user2_acc = next(a for a in accesses if a["user_id"] == user2_id)
            assert user2_acc["role"] == "VIEWER"

            print_success("✓ Degraded to viewer")

    @pytest.mark.asyncio
    async def test_last_owner_cannot_be_degraded(self, test_server):
        """ACCESS-023: Last OWNER cannot be degraded via bulk."""
        print_section("ACCESS-023: Last owner cannot be degraded")

        async with httpx.AsyncClient() as client:
            user_id, _, _, _ = await create_user_and_login(client)
            broker_id = await create_broker(client)

            # Try to set self as EDITOR (no OWNER left)
            resp = await bulk_set_access(
                client,
                broker_id,
                [
                    {"user_id": user_id, "role": "EDITOR", "share_percentage": 0},
                ],
            )
            assert resp.status_code == 400
            assert "OWNER" in resp.json()["detail"]

            print_success("✓ Last owner cannot be degraded")


# ============================================================================
# BULK ACCESS REMOVE TESTS (removing users via PUT bulk)
# ============================================================================


class TestBulkRemoveAccess:
    """Tests for removing access via PUT /brokers/{id}/access."""

    @pytest.mark.asyncio
    async def test_owner_removes_viewer(self, test_server):
        """ACCESS-030: OWNER removes VIEWER by omitting from bulk."""
        print_section("ACCESS-030: Owner removes viewer")

        async with httpx.AsyncClient() as client1, httpx.AsyncClient() as client2:
            user1_id, _, _, _ = await create_user_and_login(client1)
            broker_id = await create_broker(client1)
            user2_id, _, _, _ = await create_user_and_login(client2)

            # Add viewer
            await add_user_via_bulk(client1, broker_id, user1_id, user2_id, "VIEWER")
            accesses = await get_access_list(client1, broker_id)
            assert len(accesses) == 2

            # Remove by sending only owner
            resp = await bulk_set_access(
                client1,
                broker_id,
                [
                    {"user_id": user1_id, "role": "OWNER", "share_percentage": 1.0},
                ],
            )
            assert resp.status_code == 200

            accesses = await get_access_list(client1, broker_id)
            assert len(accesses) == 1

            print_success("✓ Owner removed viewer")

    @pytest.mark.asyncio
    async def test_owner_removes_other_owner(self, test_server):
        """ACCESS-032: OWNER can remove another OWNER (if not last)."""
        print_section("ACCESS-032: Owner removes other owner")

        async with httpx.AsyncClient() as client1, httpx.AsyncClient() as client2:
            user1_id, _, _, _ = await create_user_and_login(client1)
            broker_id = await create_broker(client1)
            user2_id, _, _, _ = await create_user_and_login(client2)

            # Add second owner
            resp = await bulk_set_access(
                client1,
                broker_id,
                [
                    {"user_id": user1_id, "role": "OWNER", "share_percentage": 0.5},
                    {"user_id": user2_id, "role": "OWNER", "share_percentage": 0.5},
                ],
            )
            assert resp.status_code == 200

            # Remove second owner
            resp = await bulk_set_access(
                client1,
                broker_id,
                [
                    {"user_id": user1_id, "role": "OWNER", "share_percentage": 1.0},
                ],
            )
            assert resp.status_code == 200

            accesses = await get_access_list(client1, broker_id)
            assert len(accesses) == 1

            print_success("✓ Owner removed other owner")


# ============================================================================
# MULTI-USER ISOLATION TESTS
# ============================================================================


class TestMultiUserIsolation:
    """Tests for multi-user isolation."""

    @pytest.mark.asyncio
    async def test_user_cannot_see_others_brokers(self, test_server):
        """ACCESS-043: User A cannot see broker of User B."""
        print_section("ACCESS-043: User isolation")

        async with httpx.AsyncClient() as client1, httpx.AsyncClient() as client2:
            await create_user_and_login(client1)
            broker_id = await create_broker(client1, unique_name("User1Broker"))

            await create_user_and_login(client2)

            list_resp = await client2.get(f"{API_BASE}/brokers", timeout=TIMEOUT)
            broker_ids = [b["id"] for b in list_resp.json()]
            assert broker_id not in broker_ids

            direct_resp = await client2.get(
                f"{API_BASE}/brokers/{broker_id}",
                timeout=TIMEOUT,
            )
            assert direct_resp.status_code == 404

            print_success("✓ User isolation works correctly")


# ============================================================================
# SUPERUSER TESTS
# ============================================================================


class TestSuperuserAccess:
    """Tests for superuser bypass capabilities.

    Note: These tests require a clean database where the first user
    becomes superuser. See class docstring for manual test instructions.
    """

    @pytest.mark.asyncio
    async def test_superuser_sees_all_brokers_with_as_user_id_all(self, test_server):
        """ACCESS-050: Superuser with as_user_id=all sees all brokers."""
        print_section("ACCESS-050: Superuser sees all with as_user_id=all")

        async with httpx.AsyncClient() as admin_client, httpx.AsyncClient() as user_client:
            admin_id, admin_name, _, _ = await create_user_and_login(admin_client)

            me_resp = await admin_client.get(f"{API_BASE}/auth/me", timeout=TIMEOUT)
            is_superuser = me_resp.json().get("user", {}).get("is_superuser", False)

            if not is_superuser:
                pytest.skip("First user is not superuser (DB not clean). " "To test: ./dev.py db create-clean --test && ./dev.py test api broker-access -k superuser")

            await create_user_and_login(user_client)
            broker_id = await create_broker(user_client, unique_name("UserBroker"))

            response = await admin_client.get(
                f"{API_BASE}/brokers",
                params={"as_user_id": "all"},
                timeout=TIMEOUT,
            )

            assert response.status_code == 200
            broker_ids = [b["id"] for b in response.json()]
            assert broker_id in broker_ids

            print_success("✓ Superuser sees all brokers with as_user_id=all")

    @pytest.mark.asyncio
    async def test_non_superuser_cannot_use_as_user_id(self, test_server):
        """ACCESS-051: Non-superuser cannot use as_user_id parameter."""
        print_section("ACCESS-051: Non-superuser cannot use as_user_id")

        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)

            response = await client.get(
                f"{API_BASE}/brokers",
                params={"as_user_id": "all"},
                timeout=TIMEOUT,
            )

            assert response.status_code == 403
            assert "superuser" in response.json()["detail"].lower()

            print_success("✓ Non-superuser correctly rejected")


# ============================================================================
# SELF-MODIFICATION TESTS
# ============================================================================


class TestSelfModification:
    """Tests for modifying own role via bulk."""

    @pytest.mark.asyncio
    async def test_owner_cannot_degrade_self_if_last(self, test_server):
        """ACCESS-060: Last OWNER cannot degrade self."""
        print_section("ACCESS-060: Last owner cannot degrade self")

        async with httpx.AsyncClient() as client:
            user_id, _, _, _ = await create_user_and_login(client)
            broker_id = await create_broker(client)

            resp = await bulk_set_access(
                client,
                broker_id,
                [
                    {"user_id": user_id, "role": "EDITOR", "share_percentage": 0},
                ],
            )
            assert resp.status_code == 400
            assert "OWNER" in resp.json()["detail"]

            print_success("✓ Last owner cannot degrade self")

    @pytest.mark.asyncio
    async def test_owner_can_degrade_self_if_not_last(self, test_server):
        """ACCESS-061: OWNER can degrade self if not last owner."""
        print_section("ACCESS-061: Owner can degrade self if not last")

        async with httpx.AsyncClient() as client1, httpx.AsyncClient() as client2:
            user1_id, _, _, _ = await create_user_and_login(client1)
            broker_id = await create_broker(client1)
            user2_id, _, _, _ = await create_user_and_login(client2)

            # Add second owner
            resp = await bulk_set_access(
                client1,
                broker_id,
                [
                    {"user_id": user1_id, "role": "OWNER", "share_percentage": 0.5},
                    {"user_id": user2_id, "role": "OWNER", "share_percentage": 0.5},
                ],
            )
            assert resp.status_code == 200

            # User1 degrades self to EDITOR (user2 remains OWNER)
            resp = await bulk_set_access(
                client1,
                broker_id,
                [
                    {"user_id": user1_id, "role": "EDITOR", "share_percentage": 0},
                    {"user_id": user2_id, "role": "OWNER", "share_percentage": 1.0},
                ],
            )
            assert resp.status_code == 200

            accesses = await get_access_list(client1, broker_id)
            user1_acc = next(a for a in accesses if a["user_id"] == user1_id)
            assert user1_acc["role"] == "EDITOR"

            print_success("✓ Owner degraded self successfully")

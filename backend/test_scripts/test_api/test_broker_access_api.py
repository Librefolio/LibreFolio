"""
Broker Access API Tests.

Tests for broker access management endpoints:
- GET /brokers/{id}/access: List users with access
- POST /brokers/{id}/access: Add user access
- PATCH /brokers/{id}/access/{user_id}: Update user role
- DELETE /brokers/{id}/access/{user_id}: Remove user access

Tests role hierarchy: OWNER > EDITOR > VIEWER
Tests multi-user isolation and superuser capabilities.
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


async def create_user_and_login(
    client: httpx.AsyncClient, username: Optional[str] = None
    ) -> tuple[int, str, str, Optional[str]]:
    """
    Create a new user, login, and return (user_id, username, email, session).
    Sets session cookie on client.
    """
    username = username or unique_username()
    email = f"{username}@test.com"
    password = "TestPass123!"

    # Register
    resp = await client.post(
        f"{API_BASE}/auth/register",
        json={"username": username, "email": email, "password": password},
        timeout=TIMEOUT,
        )

    if resp.status_code != 201:
        raise Exception(f"Failed to create user: {resp.text}")

    user_id = resp.json()["user"]["id"]

    # Login
    login_resp = await client.post(
        f"{API_BASE}/auth/login", json={"username": username, "password": password}, timeout=TIMEOUT
        )

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


async def get_user_info(client: httpx.AsyncClient) -> dict:
    """Get current user info."""
    resp = await client.get(f"{API_BASE}/auth/me", timeout=TIMEOUT)
    return resp.json().get("user", {})


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
            assert data["count"] == 1
            assert data["accesses"][0]["role"] == "OWNER"

            print_success("✓ Owner can list access")

    @pytest.mark.asyncio
    async def test_list_access_no_access(self, test_server):
        """ACCESS-002: GET /brokers/{id}/access - 404 without access."""
        print_section("ACCESS-002: List access without permission")

        async with httpx.AsyncClient() as client1, httpx.AsyncClient() as client2:
            # User 1 creates broker
            await create_user_and_login(client1)
            broker_id = await create_broker(client1)

            # User 2 tries to list (no access)
            await create_user_and_login(client2)
            response = await client2.get(
                f"{API_BASE}/brokers/{broker_id}/access",
                timeout=TIMEOUT,
                )

            assert response.status_code == 404

            print_success("✓ Got 404 without access")


# ============================================================================
# ADD ACCESS TESTS
# ============================================================================


class TestAddAccess:
    """Tests for POST /brokers/{id}/access."""

    @pytest.mark.asyncio
    async def test_owner_adds_viewer(self, test_server):
        """ACCESS-010: OWNER can add VIEWER."""
        print_section("ACCESS-010: Owner adds viewer")

        async with httpx.AsyncClient() as client1, httpx.AsyncClient() as client2:
            # User 1 (owner) creates broker
            await create_user_and_login(client1)
            broker_id = await create_broker(client1)

            # Create user 2
            user2_id, _, _, _ = await create_user_and_login(client2)

            # User 1 adds user 2 as VIEWER
            response = await client1.post(
                f"{API_BASE}/brokers/{broker_id}/access",
                json={"user_id": user2_id, "role": "VIEWER"},
                timeout=TIMEOUT,
                )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["access"]["role"] == "VIEWER"

            print_success("✓ Owner added viewer")

    @pytest.mark.asyncio
    async def test_owner_adds_editor(self, test_server):
        """ACCESS-011: OWNER can add EDITOR."""
        print_section("ACCESS-011: Owner adds editor")

        async with httpx.AsyncClient() as client1, httpx.AsyncClient() as client2:
            await create_user_and_login(client1)
            broker_id = await create_broker(client1)

            user2_id, _, _, _ = await create_user_and_login(client2)

            response = await client1.post(
                f"{API_BASE}/brokers/{broker_id}/access",
                json={"user_id": user2_id, "role": "EDITOR"},
                timeout=TIMEOUT,
                )

            assert response.status_code == 200
            assert response.json()["access"]["role"] == "EDITOR"

            print_success("✓ Owner added editor")

    @pytest.mark.asyncio
    async def test_owner_adds_owner(self, test_server):
        """ACCESS-012: OWNER can add another OWNER."""
        print_section("ACCESS-012: Owner adds another owner")

        async with httpx.AsyncClient() as client1, httpx.AsyncClient() as client2:
            await create_user_and_login(client1)
            broker_id = await create_broker(client1)

            user2_id, _, _, _ = await create_user_and_login(client2)

            response = await client1.post(
                f"{API_BASE}/brokers/{broker_id}/access",
                json={"user_id": user2_id, "role": "OWNER"},
                timeout=TIMEOUT,
                )

            assert response.status_code == 200
            assert response.json()["access"]["role"] == "OWNER"

            print_success("✓ Owner added another owner")

    @pytest.mark.asyncio
    async def test_editor_cannot_add(self, test_server):
        """ACCESS-013: EDITOR cannot add access."""
        print_section("ACCESS-013: Editor cannot add access")

        async with (
            httpx.AsyncClient() as client1,
            httpx.AsyncClient() as client2,
            httpx.AsyncClient() as client3,
            ):
            # User 1 creates broker
            await create_user_and_login(client1)
            broker_id = await create_broker(client1)

            # Add user 2 as EDITOR
            user2_id, _, _, _ = await create_user_and_login(client2)
            await client1.post(
                f"{API_BASE}/brokers/{broker_id}/access",
                json={"user_id": user2_id, "role": "EDITOR"},
                timeout=TIMEOUT,
                )

            # Create user 3
            user3_id, _, _, _ = await create_user_and_login(client3)

            # User 2 (editor) tries to add user 3
            response = await client2.post(
                f"{API_BASE}/brokers/{broker_id}/access",
                json={"user_id": user3_id, "role": "VIEWER"},
                timeout=TIMEOUT,
                )

            assert response.status_code == 403
            assert "OWNER" in response.json()["detail"]

            print_success("✓ Editor correctly rejected")

    @pytest.mark.asyncio
    async def test_viewer_cannot_add(self, test_server):
        """ACCESS-014: VIEWER cannot add access."""
        print_section("ACCESS-014: Viewer cannot add access")

        async with (
            httpx.AsyncClient() as client1,
            httpx.AsyncClient() as client2,
            httpx.AsyncClient() as client3,
            ):
            await create_user_and_login(client1)
            broker_id = await create_broker(client1)

            user2_id, _, _, _ = await create_user_and_login(client2)
            await client1.post(
                f"{API_BASE}/brokers/{broker_id}/access",
                json={"user_id": user2_id, "role": "VIEWER"},
                timeout=TIMEOUT,
                )

            user3_id, _, _, _ = await create_user_and_login(client3)

            response = await client2.post(
                f"{API_BASE}/brokers/{broker_id}/access",
                json={"user_id": user3_id, "role": "VIEWER"},
                timeout=TIMEOUT,
                )

            assert response.status_code == 403

            print_success("✓ Viewer correctly rejected")

    @pytest.mark.asyncio
    async def test_add_user_already_has_access(self, test_server):
        """ACCESS-016: Cannot add user who already has access."""
        print_section("ACCESS-016: User already has access")

        async with httpx.AsyncClient() as client1, httpx.AsyncClient() as client2:
            await create_user_and_login(client1)
            broker_id = await create_broker(client1)

            user2_id, _, _, _ = await create_user_and_login(client2)

            # Add first time
            await client1.post(
                f"{API_BASE}/brokers/{broker_id}/access",
                json={"user_id": user2_id, "role": "VIEWER"},
                timeout=TIMEOUT,
                )

            # Try to add again
            response = await client1.post(
                f"{API_BASE}/brokers/{broker_id}/access",
                json={"user_id": user2_id, "role": "EDITOR"},
                timeout=TIMEOUT,
                )

            assert response.status_code == 400
            assert "already has access" in response.json()["detail"]

            print_success("✓ Duplicate correctly rejected")

    @pytest.mark.asyncio
    async def test_add_nonexistent_user(self, test_server):
        """ACCESS-017: Cannot add non-existent user."""
        print_section("ACCESS-017: Non-existent user")

        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)
            broker_id = await create_broker(client)

            response = await client.post(
                f"{API_BASE}/brokers/{broker_id}/access",
                json={"user_id": 999999, "role": "VIEWER"},
                timeout=TIMEOUT,
                )

            assert response.status_code == 400
            assert "not found" in response.json()["detail"]

            print_success("✓ Non-existent user correctly rejected")


# ============================================================================
# UPDATE ACCESS TESTS
# ============================================================================


class TestUpdateAccess:
    """Tests for PATCH /brokers/{id}/access/{user_id}."""

    @pytest.mark.asyncio
    async def test_owner_promotes_viewer_to_editor(self, test_server):
        """ACCESS-020: OWNER promotes VIEWER to EDITOR."""
        print_section("ACCESS-020: Promote viewer to editor")

        async with httpx.AsyncClient() as client1, httpx.AsyncClient() as client2:
            await create_user_and_login(client1)
            broker_id = await create_broker(client1)

            user2_id, _, _, _ = await create_user_and_login(client2)
            await client1.post(
                f"{API_BASE}/brokers/{broker_id}/access",
                json={"user_id": user2_id, "role": "VIEWER"},
                timeout=TIMEOUT,
                )

            # Promote
            response = await client1.patch(
                f"{API_BASE}/brokers/{broker_id}/access/{user2_id}",
                json={"role": "EDITOR"},
                timeout=TIMEOUT,
                )

            assert response.status_code == 200
            assert response.json()["access"]["role"] == "EDITOR"

            print_success("✓ Promoted to editor")

    @pytest.mark.asyncio
    async def test_owner_degrades_editor_to_viewer(self, test_server):
        """ACCESS-021: OWNER degrades EDITOR to VIEWER."""
        print_section("ACCESS-021: Degrade editor to viewer")

        async with httpx.AsyncClient() as client1, httpx.AsyncClient() as client2:
            await create_user_and_login(client1)
            broker_id = await create_broker(client1)

            user2_id, _, _, _ = await create_user_and_login(client2)
            await client1.post(
                f"{API_BASE}/brokers/{broker_id}/access",
                json={"user_id": user2_id, "role": "EDITOR"},
                timeout=TIMEOUT,
                )

            response = await client1.patch(
                f"{API_BASE}/brokers/{broker_id}/access/{user2_id}",
                json={"role": "VIEWER"},
                timeout=TIMEOUT,
                )

            assert response.status_code == 200
            assert response.json()["access"]["role"] == "VIEWER"

            print_success("✓ Degraded to viewer")

    @pytest.mark.asyncio
    async def test_last_owner_cannot_be_degraded(self, test_server):
        """ACCESS-023: Last OWNER cannot be degraded."""
        print_section("ACCESS-023: Last owner cannot be degraded")

        async with httpx.AsyncClient() as client:
            user_id, _, _, _ = await create_user_and_login(client)
            broker_id = await create_broker(client)

            # Try to degrade self (last owner)
            response = await client.patch(
                f"{API_BASE}/brokers/{broker_id}/access/{user_id}",
                json={"role": "EDITOR"},
                timeout=TIMEOUT,
                )

            assert response.status_code == 400
            assert "last OWNER" in response.json()["detail"]

            print_success("✓ Last owner cannot be degraded")

    @pytest.mark.asyncio
    async def test_editor_cannot_modify(self, test_server):
        """ACCESS-024: EDITOR cannot modify access."""
        print_section("ACCESS-024: Editor cannot modify access")

        async with (
            httpx.AsyncClient() as client1,
            httpx.AsyncClient() as client2,
            httpx.AsyncClient() as client3,
            ):
            await create_user_and_login(client1)
            broker_id = await create_broker(client1)

            # Add editor and viewer
            user2_id, _, _, _ = await create_user_and_login(client2)
            await client1.post(
                f"{API_BASE}/brokers/{broker_id}/access",
                json={"user_id": user2_id, "role": "EDITOR"},
                timeout=TIMEOUT,
                )

            user3_id, _, _, _ = await create_user_and_login(client3)
            await client1.post(
                f"{API_BASE}/brokers/{broker_id}/access",
                json={"user_id": user3_id, "role": "VIEWER"},
                timeout=TIMEOUT,
                )

            # Editor tries to modify viewer
            response = await client2.patch(
                f"{API_BASE}/brokers/{broker_id}/access/{user3_id}",
                json={"role": "EDITOR"},
                timeout=TIMEOUT,
                )

            assert response.status_code == 403
            assert "OWNER" in response.json()["detail"]

            print_success("✓ Editor correctly rejected")


# ============================================================================
# REMOVE ACCESS TESTS
# ============================================================================


class TestRemoveAccess:
    """Tests for DELETE /brokers/{id}/access/{user_id}."""

    @pytest.mark.asyncio
    async def test_owner_removes_viewer(self, test_server):
        """ACCESS-030: OWNER can remove VIEWER."""
        print_section("ACCESS-030: Owner removes viewer")

        async with httpx.AsyncClient() as client1, httpx.AsyncClient() as client2:
            await create_user_and_login(client1)
            broker_id = await create_broker(client1)

            user2_id, _, _, _ = await create_user_and_login(client2)
            await client1.post(
                f"{API_BASE}/brokers/{broker_id}/access",
                json={"user_id": user2_id, "role": "VIEWER"},
                timeout=TIMEOUT,
                )

            response = await client1.delete(
                f"{API_BASE}/brokers/{broker_id}/access/{user2_id}",
                timeout=TIMEOUT,
                )

            assert response.status_code == 200
            assert response.json()["success"] is True

            print_success("✓ Owner removed viewer")

    @pytest.mark.asyncio
    async def test_owner_removes_editor(self, test_server):
        """ACCESS-031: OWNER can remove EDITOR."""
        print_section("ACCESS-031: Owner removes editor")

        async with httpx.AsyncClient() as client1, httpx.AsyncClient() as client2:
            await create_user_and_login(client1)
            broker_id = await create_broker(client1)

            user2_id, _, _, _ = await create_user_and_login(client2)
            await client1.post(
                f"{API_BASE}/brokers/{broker_id}/access",
                json={"user_id": user2_id, "role": "EDITOR"},
                timeout=TIMEOUT,
                )

            response = await client1.delete(
                f"{API_BASE}/brokers/{broker_id}/access/{user2_id}",
                timeout=TIMEOUT,
                )

            assert response.status_code == 200

            print_success("✓ Owner removed editor")

    @pytest.mark.asyncio
    async def test_owner_removes_other_owner(self, test_server):
        """ACCESS-032: OWNER can remove another OWNER (if not last)."""
        print_section("ACCESS-032: Owner removes other owner")

        async with httpx.AsyncClient() as client1, httpx.AsyncClient() as client2:
            await create_user_and_login(client1)
            broker_id = await create_broker(client1)

            # Add second owner
            user2_id, _, _, _ = await create_user_and_login(client2)
            await client1.post(
                f"{API_BASE}/brokers/{broker_id}/access",
                json={"user_id": user2_id, "role": "OWNER"},
                timeout=TIMEOUT,
                )

            # Remove second owner
            response = await client1.delete(
                f"{API_BASE}/brokers/{broker_id}/access/{user2_id}",
                timeout=TIMEOUT,
                )

            assert response.status_code == 200

            print_success("✓ Owner removed other owner")

    @pytest.mark.asyncio
    async def test_last_owner_cannot_be_removed(self, test_server):
        """ACCESS-033: Last OWNER cannot be removed."""
        print_section("ACCESS-033: Last owner cannot be removed")

        async with httpx.AsyncClient() as client:
            user_id, _, _, _ = await create_user_and_login(client)
            broker_id = await create_broker(client)

            response = await client.delete(
                f"{API_BASE}/brokers/{broker_id}/access/{user_id}",
                timeout=TIMEOUT,
                )

            assert response.status_code == 400
            assert "last OWNER" in response.json()["detail"]

            print_success("✓ Last owner cannot be removed")

    @pytest.mark.asyncio
    async def test_editor_removes_self(self, test_server):
        """ACCESS-034: EDITOR can remove self."""
        print_section("ACCESS-034: Editor removes self")

        async with httpx.AsyncClient() as client1, httpx.AsyncClient() as client2:
            await create_user_and_login(client1)
            broker_id = await create_broker(client1)

            user2_id, _, _, _ = await create_user_and_login(client2)
            await client1.post(
                f"{API_BASE}/brokers/{broker_id}/access",
                json={"user_id": user2_id, "role": "EDITOR"},
                timeout=TIMEOUT,
                )

            # Editor removes self
            response = await client2.delete(
                f"{API_BASE}/brokers/{broker_id}/access/{user2_id}",
                timeout=TIMEOUT,
                )

            assert response.status_code == 200

            print_success("✓ Editor removed self")

    @pytest.mark.asyncio
    async def test_viewer_removes_self(self, test_server):
        """ACCESS-035: VIEWER can remove self."""
        print_section("ACCESS-035: Viewer removes self")

        async with httpx.AsyncClient() as client1, httpx.AsyncClient() as client2:
            await create_user_and_login(client1)
            broker_id = await create_broker(client1)

            user2_id, _, _, _ = await create_user_and_login(client2)
            await client1.post(
                f"{API_BASE}/brokers/{broker_id}/access",
                json={"user_id": user2_id, "role": "VIEWER"},
                timeout=TIMEOUT,
                )

            response = await client2.delete(
                f"{API_BASE}/brokers/{broker_id}/access/{user2_id}",
                timeout=TIMEOUT,
                )

            assert response.status_code == 200

            print_success("✓ Viewer removed self")

    @pytest.mark.asyncio
    async def test_editor_cannot_remove_others(self, test_server):
        """ACCESS-036: EDITOR cannot remove others."""
        print_section("ACCESS-036: Editor cannot remove others")

        async with (
            httpx.AsyncClient() as client1,
            httpx.AsyncClient() as client2,
            httpx.AsyncClient() as client3,
            ):
            await create_user_and_login(client1)
            broker_id = await create_broker(client1)

            user2_id, _, _, _ = await create_user_and_login(client2)
            await client1.post(
                f"{API_BASE}/brokers/{broker_id}/access",
                json={"user_id": user2_id, "role": "EDITOR"},
                timeout=TIMEOUT,
                )

            user3_id, _, _, _ = await create_user_and_login(client3)
            await client1.post(
                f"{API_BASE}/brokers/{broker_id}/access",
                json={"user_id": user3_id, "role": "VIEWER"},
                timeout=TIMEOUT,
                )

            # Editor tries to remove viewer
            response = await client2.delete(
                f"{API_BASE}/brokers/{broker_id}/access/{user3_id}",
                timeout=TIMEOUT,
                )

            assert response.status_code == 400
            assert "only remove yourself" in response.json()["detail"]

            print_success("✓ Editor correctly rejected")


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
            # User 1 creates broker
            await create_user_and_login(client1)
            broker_id = await create_broker(client1, unique_name("User1Broker"))

            # User 2 tries to access
            await create_user_and_login(client2)

            # List should not include user1's broker
            list_resp = await client2.get(f"{API_BASE}/brokers", timeout=TIMEOUT)
            broker_ids = [b["id"] for b in list_resp.json()]
            assert broker_id not in broker_ids

            # Direct access should return 404
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
    becomes superuser. When running after other tests, the DB already
    has users so these will be skipped.

    To test manually:
    1. Stop server: pkill -f uvicorn
    2. Recreate test DB: ./dev.py db create-clean --test
    3. Start test server: ./dev.py server --test
    4. Run only this test: ./dev.py test api broker-access -k superuser
    """

    @pytest.mark.asyncio
    async def test_superuser_sees_all_brokers_with_as_user_id_all(self, test_server):
        """ACCESS-050: Superuser with as_user_id=all sees all brokers.

        MANUAL TEST: Requires clean DB. See class docstring for instructions.
        """
        print_section("ACCESS-050: Superuser sees all with as_user_id=all")

        async with httpx.AsyncClient() as admin_client, httpx.AsyncClient() as user_client:
            # Create admin (first user becomes superuser)
            # Note: This test assumes clean DB or first user is admin
            admin_id, admin_name, _, _ = await create_user_and_login(admin_client)

            # Check if admin is superuser
            me_resp = await admin_client.get(f"{API_BASE}/auth/me", timeout=TIMEOUT)
            is_superuser = me_resp.json().get("user", {}).get("is_superuser", False)

            if not is_superuser:
                pytest.skip(
                    "First user is not superuser (DB not clean). "
                    "To test manually: ./dev.py db create-clean --test && "
                    "./dev.py server --test && ./dev.py test api broker-access -k superuser"
                    )

            # Create regular user with broker
            await create_user_and_login(user_client)
            broker_id = await create_broker(user_client, unique_name("UserBroker"))

            # Admin queries with as_user_id=all
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
    """Tests for modifying own role."""

    @pytest.mark.asyncio
    async def test_owner_cannot_degrade_self_if_last(self, test_server):
        """ACCESS-060: Last OWNER cannot degrade self."""
        print_section("ACCESS-060: Last owner cannot degrade self")

        async with httpx.AsyncClient() as client:
            user_id, _, _, _ = await create_user_and_login(client)
            broker_id = await create_broker(client)

            # Try to degrade self to EDITOR
            response = await client.patch(
                f"{API_BASE}/brokers/{broker_id}/access/{user_id}",
                json={"role": "EDITOR"},
                timeout=TIMEOUT,
                )

            assert response.status_code == 400
            assert "last OWNER" in response.json()["detail"]

            print_success("✓ Last owner cannot degrade self")

    @pytest.mark.asyncio
    async def test_owner_can_degrade_self_if_not_last(self, test_server):
        """ACCESS-061: OWNER can degrade self if not last owner."""
        print_section("ACCESS-061: Owner can degrade self if not last")

        async with httpx.AsyncClient() as client1, httpx.AsyncClient() as client2:
            user1_id, _, _, _ = await create_user_and_login(client1)
            broker_id = await create_broker(client1)

            # Add second owner
            user2_id, _, _, _ = await create_user_and_login(client2)
            await client1.post(
                f"{API_BASE}/brokers/{broker_id}/access",
                json={"user_id": user2_id, "role": "OWNER"},
                timeout=TIMEOUT,
                )

            # User 1 can now degrade self
            response = await client1.patch(
                f"{API_BASE}/brokers/{broker_id}/access/{user1_id}",
                json={"role": "EDITOR"},
                timeout=TIMEOUT,
                )

            assert response.status_code == 200
            assert response.json()["access"]["role"] == "EDITOR"

            print_success("✓ Owner degraded self successfully")

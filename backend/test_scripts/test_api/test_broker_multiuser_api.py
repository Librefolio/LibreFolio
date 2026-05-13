"""
Broker Multi-User Role API Tests.

Tests for role-based permissions on broker operations:
- OWNER: Can do everything (CRUD, manage access, delete)
- EDITOR: Can modify broker and transactions, cannot delete or share
- VIEWER: Read-only access

Tests verify that operations are correctly allowed/denied based on role.
"""

import uuid
from datetime import date, datetime
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
    """Generate a unique name."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def unique_username() -> str:
    """Generate a unique username."""
    timestamp = int(datetime.now().timestamp() * 1000)
    return f"multi_test_{timestamp}"


# ============================================================================
# HELPERS
# ============================================================================


async def create_user_and_login(client: httpx.AsyncClient, username: Optional[str] = None) -> tuple[int, str]:
    """Create user, login, return (user_id, username)."""
    username = username or unique_username()
    email = f"{username}@test.com"
    password = "TestPass123!"

    resp = await client.post(
        f"{API_BASE}/auth/register",
        json={"username": username, "email": email, "password": password},
        timeout=TIMEOUT,
    )
    user_id = resp.json()["user"]["id"]

    login_resp = await client.post(f"{API_BASE}/auth/login", json={"username": username, "password": password}, timeout=TIMEOUT)
    session = login_resp.cookies.get("session")
    if session:
        client.cookies.set("session", session)

    return user_id, username


async def create_broker(client: httpx.AsyncClient, name: Optional[str] = None) -> int:
    """Create broker, return ID."""
    name = name or unique_name("Broker")
    resp = await client.post(f"{API_BASE}/brokers", json=[{"name": name}], timeout=TIMEOUT)
    return resp.json()["results"][0]["broker_id"]


async def add_access(client: httpx.AsyncClient, broker_id: int, user_id: int, role: str) -> None:
    """Add user access to broker via bulk PUT (preserving existing accesses)."""
    # First get current access list
    access_resp = await client.get(
        f"{API_BASE}/brokers/{broker_id}/access",
        timeout=TIMEOUT,
    )
    current = access_resp.json()["items"]
    accesses = [{"user_id": a["user_id"], "role": a["role"], "share_percentage": float(a["share_percentage"])} for a in current]
    # Add new user (share=0 for non-OWNER)
    accesses.append({"user_id": user_id, "role": role, "share_percentage": 0})
    await client.put(
        f"{API_BASE}/brokers/{broker_id}/access",
        json=accesses,
        timeout=TIMEOUT,
    )


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture(scope="module")
def test_server():
    """Start test server."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


# ============================================================================
# TESTS
# ============================================================================


class TestMultiUserRoles:
    """Tests for role-based permissions."""

    @pytest.mark.asyncio
    async def test_creation_creates_owner_access(self, test_server):
        """MULTI-001: Creating broker creates BrokerUserAccess with OWNER role."""
        print_section("MULTI-001: Creation creates OWNER access")

        async with httpx.AsyncClient() as client:
            user_id, _ = await create_user_and_login(client)
            broker_id = await create_broker(client)

            # Check access
            resp = await client.get(f"{API_BASE}/brokers/{broker_id}/access", timeout=TIMEOUT)

            assert resp.status_code == 200
            data = resp.json()
            assert len(data["items"]) == 1
            assert data["items"][0]["user_id"] == user_id
            assert data["items"][0]["role"] == "OWNER"

            print_success("✓ Creator becomes OWNER")

    @pytest.mark.asyncio
    async def test_editor_can_modify_broker(self, test_server):
        """MULTI-002: EDITOR can modify broker."""
        print_section("MULTI-002: Editor can modify broker")

        async with httpx.AsyncClient() as owner_client, httpx.AsyncClient() as editor_client:
            # Owner creates broker
            await create_user_and_login(owner_client)
            broker_id = await create_broker(owner_client)

            # Add editor
            editor_id, _ = await create_user_and_login(editor_client)
            await add_access(owner_client, broker_id, editor_id, "EDITOR")

            # Editor modifies broker
            resp = await editor_client.patch(
                f"{API_BASE}/brokers/{broker_id}",
                json={"description": "Modified by editor"},
                timeout=TIMEOUT,
            )

            assert resp.status_code == 200
            assert resp.json()["results"][0]["success"] is True

            print_success("✓ Editor modified broker")

    @pytest.mark.asyncio
    async def test_editor_cannot_delete_broker(self, test_server):
        """MULTI-003: EDITOR cannot delete broker (403)."""
        print_section("MULTI-003: Editor cannot delete broker")

        async with httpx.AsyncClient() as owner_client, httpx.AsyncClient() as editor_client:
            await create_user_and_login(owner_client)
            broker_id = await create_broker(owner_client)

            editor_id, _ = await create_user_and_login(editor_client)
            await add_access(owner_client, broker_id, editor_id, "EDITOR")

            # Editor tries to delete
            resp = await editor_client.delete(f"{API_BASE}/brokers", params={"ids": [broker_id], "force": True}, timeout=TIMEOUT)

            # Should get success=False with "Access denied"
            assert resp.status_code == 200
            assert resp.json()["results"][0]["success"] is False
            assert "denied" in resp.json()["results"][0]["message"].lower()

            print_success("✓ Editor cannot delete broker")

    @pytest.mark.asyncio
    async def test_viewer_cannot_modify_broker(self, test_server):
        """MULTI-004: VIEWER cannot modify broker (403)."""
        print_section("MULTI-004: Viewer cannot modify broker")

        async with httpx.AsyncClient() as owner_client, httpx.AsyncClient() as viewer_client:
            await create_user_and_login(owner_client)
            broker_id = await create_broker(owner_client)

            viewer_id, _ = await create_user_and_login(viewer_client)
            await add_access(owner_client, broker_id, viewer_id, "VIEWER")

            # Viewer tries to modify
            resp = await viewer_client.patch(
                f"{API_BASE}/brokers/{broker_id}",
                json={"description": "Should fail"},
                timeout=TIMEOUT,
            )

            assert resp.status_code == 200
            assert resp.json()["results"][0]["success"] is False
            assert "denied" in resp.json()["results"][0]["error"].lower()

            print_success("✓ Viewer cannot modify broker")

    @pytest.mark.asyncio
    async def test_viewer_can_read_broker(self, test_server):
        """MULTI-005: VIEWER can read broker."""
        print_section("MULTI-005: Viewer can read broker")

        async with httpx.AsyncClient() as owner_client, httpx.AsyncClient() as viewer_client:
            await create_user_and_login(owner_client)
            broker_id = await create_broker(owner_client)

            viewer_id, _ = await create_user_and_login(viewer_client)
            await add_access(owner_client, broker_id, viewer_id, "VIEWER")

            # Viewer reads broker
            resp = await viewer_client.get(f"{API_BASE}/brokers/{broker_id}", timeout=TIMEOUT)

            assert resp.status_code == 200
            assert resp.json()["id"] == broker_id

            # Viewer reads summary
            summary_resp = await viewer_client.get(f"{API_BASE}/brokers/{broker_id}/summary", timeout=TIMEOUT)

            assert summary_resp.status_code == 200

            print_success("✓ Viewer can read broker")

    @pytest.mark.asyncio
    async def test_owner_can_delete_broker(self, test_server):
        """MULTI-006: OWNER can delete broker."""
        print_section("MULTI-006: Owner can delete broker")

        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)
            broker_id = await create_broker(client)

            resp = await client.delete(f"{API_BASE}/brokers", params={"ids": [broker_id]}, timeout=TIMEOUT)

            assert resp.status_code == 200
            assert resp.json()["total_deleted"] == 1

            print_success("✓ Owner deleted broker")

    @pytest.mark.asyncio
    async def test_editor_can_create_transactions(self, test_server):
        """MULTI-007: EDITOR can create transactions."""
        print_section("MULTI-007: Editor can create transactions")

        async with httpx.AsyncClient() as owner_client, httpx.AsyncClient() as editor_client:

            await create_user_and_login(owner_client)
            broker_id = await create_broker(owner_client)

            editor_id, _ = await create_user_and_login(editor_client)
            await add_access(owner_client, broker_id, editor_id, "EDITOR")

            # Editor creates a deposit transaction
            tx_payload = [
                {
                    "broker_id": broker_id,
                    "type": "DEPOSIT",
                    "date": date.today().isoformat(),
                    "cash": {"code": "EUR", "amount": "1000"},
                }
            ]

            resp = await editor_client.post(f"{API_BASE}/transactions/commit", json={"creates": tx_payload}, timeout=TIMEOUT)

            assert resp.status_code == 200
            data = resp.json()
            assert data["committed"] is True

            print_success("✓ Editor created transaction")

    @pytest.mark.asyncio
    async def test_viewer_cannot_create_transactions(self, test_server):
        """MULTI-008: VIEWER cannot create transactions (requires EDITOR role)."""
        print_section("MULTI-008: Viewer cannot create transactions")

        async with httpx.AsyncClient() as owner_client, httpx.AsyncClient() as viewer_client:

            await create_user_and_login(owner_client)
            broker_id = await create_broker(owner_client)

            viewer_id, _ = await create_user_and_login(viewer_client)
            await add_access(owner_client, broker_id, viewer_id, "VIEWER")

            # Viewer tries to create transaction
            tx_payload = [
                {
                    "broker_id": broker_id,
                    "type": "DEPOSIT",
                    "date": date.today().isoformat(),
                    "cash": {"code": "EUR", "amount": "1000"},
                }
            ]

            resp = await viewer_client.post(f"{API_BASE}/transactions/commit", json={"creates": tx_payload}, timeout=TIMEOUT)

            # Part 3: access check is batch-level → committed=false with issues (not HTTP 403).
            assert resp.status_code == 200
            data = resp.json()
            assert data["committed"] is False

            print_success("✓ Viewer correctly blocked from creating transactions")

    @pytest.mark.asyncio
    async def test_viewer_cannot_patch_transactions(self, test_server):
        """MULTI-008b (G.2 gap-fill): VIEWER cannot PATCH transactions (EDITOR required)."""
        print_section("MULTI-008b: Viewer cannot patch transactions")

        async with httpx.AsyncClient() as owner_client, httpx.AsyncClient() as viewer_client:
            await create_user_and_login(owner_client)
            broker_id = await create_broker(owner_client)

            # Owner seeds a transaction.
            tx_payload = [
                {
                    "broker_id": broker_id,
                    "type": "DEPOSIT",
                    "date": date.today().isoformat(),
                    "cash": {"code": "EUR", "amount": "1000"},
                }
            ]
            post_resp = await owner_client.post(f"{API_BASE}/transactions/commit", json={"creates": tx_payload}, timeout=TIMEOUT)
            assert post_resp.status_code == 200, post_resp.text
            tx_id = post_resp.json()["results"][0]["ids"][0]

            # Viewer is granted access then attempts update via commit.
            viewer_id, _ = await create_user_and_login(viewer_client)
            await add_access(owner_client, broker_id, viewer_id, "VIEWER")

            patch_resp = await viewer_client.post(
                f"{API_BASE}/transactions/commit",
                json={"updates": [{"id": tx_id, "description": "viewer tried to patch"}]},
                timeout=TIMEOUT,
            )
            # Batch-level access check → committed=false with accessDenied issue.
            assert patch_resp.status_code == 200, patch_resp.text
            data = patch_resp.json()
            assert data["committed"] is False

            print_success("✓ Viewer correctly blocked from patching transactions")

    @pytest.mark.asyncio
    async def test_viewer_cannot_delete_transactions(self, test_server):
        """MULTI-008c (G.2 gap-fill): VIEWER cannot DELETE transactions (EDITOR required)."""
        print_section("MULTI-008c: Viewer cannot delete transactions")

        async with httpx.AsyncClient() as owner_client, httpx.AsyncClient() as viewer_client:
            await create_user_and_login(owner_client)
            broker_id = await create_broker(owner_client)

            tx_payload = [
                {
                    "broker_id": broker_id,
                    "type": "DEPOSIT",
                    "date": date.today().isoformat(),
                    "cash": {"code": "EUR", "amount": "500"},
                }
            ]
            post_resp = await owner_client.post(f"{API_BASE}/transactions/commit", json={"creates": tx_payload}, timeout=TIMEOUT)
            assert post_resp.status_code == 200, post_resp.text
            tx_id = post_resp.json()["results"][0]["ids"][0]

            viewer_id, _ = await create_user_and_login(viewer_client)
            await add_access(owner_client, broker_id, viewer_id, "VIEWER")

            del_resp = await viewer_client.post(
                f"{API_BASE}/transactions/commit",
                json={"deletes": [tx_id]},
                timeout=TIMEOUT,
            )
            assert del_resp.status_code == 200, del_resp.text
            data = del_resp.json()
            assert data["committed"] is False

            # Transaction still present.
            check = await owner_client.get(f"{API_BASE}/transactions", params={"broker_id": broker_id}, timeout=TIMEOUT)
            assert check.status_code == 200
            ids_left = {t.get("id") for t in check.json()}
            assert tx_id in ids_left, f"tx unexpectedly deleted: {ids_left}"

            print_success("✓ Viewer correctly blocked from deleting transactions")


class TestEditorRestrictions:
    """Tests for EDITOR role restrictions."""

    @pytest.mark.asyncio
    async def test_editor_cannot_delete_broker(self, test_server):
        """MULTI-009: EDITOR cannot delete broker (requires OWNER)."""
        print_section("MULTI-009: Editor cannot delete broker")

        async with httpx.AsyncClient() as owner_client, httpx.AsyncClient() as editor_client:
            await create_user_and_login(owner_client)
            broker_id = await create_broker(owner_client)

            editor_id, _ = await create_user_and_login(editor_client)
            await add_access(owner_client, broker_id, editor_id, "EDITOR")

            # Editor tries to delete broker
            resp = await editor_client.delete(f"{API_BASE}/brokers", params={"ids": [broker_id]}, timeout=TIMEOUT)

            # Should fail - EDITOR cannot delete, only OWNER can
            assert resp.status_code == 200
            assert resp.json()["total_deleted"] == 0
            # The broker should still exist
            check_resp = await editor_client.get(f"{API_BASE}/brokers/{broker_id}", timeout=TIMEOUT)
            assert check_resp.status_code == 200

            print_success("✓ Editor correctly blocked from deleting broker")

    @pytest.mark.asyncio
    async def test_editor_cannot_share_broker(self, test_server):
        """MULTI-010: EDITOR cannot add access to broker (requires OWNER)."""
        print_section("MULTI-010: Editor cannot share broker")

        async with (
            httpx.AsyncClient() as owner_client,
            httpx.AsyncClient() as editor_client,
            httpx.AsyncClient() as third_client,
        ):
            await create_user_and_login(owner_client)
            broker_id = await create_broker(owner_client)

            editor_id, _ = await create_user_and_login(editor_client)
            await add_access(owner_client, broker_id, editor_id, "EDITOR")

            third_id, _ = await create_user_and_login(third_client)

            # Editor tries to bulk update access (add third user)
            resp = await editor_client.put(
                f"{API_BASE}/brokers/{broker_id}/access",
                json=[
                    {"user_id": editor_id, "role": "EDITOR", "share_percentage": 0},
                    {"user_id": third_id, "role": "VIEWER", "share_percentage": 0},
                ],
                timeout=TIMEOUT,
            )

            # Should fail with 403 (only OWNER can manage access)
            assert resp.status_code == 403

            print_success("✓ Editor correctly blocked from sharing broker")

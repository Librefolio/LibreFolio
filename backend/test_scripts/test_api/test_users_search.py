"""
Tests for User Search API and Share Percentage Validation.

Tests the GET /api/v1/users/search endpoint and the PUT /api/v1/brokers/{id}/access
bulk endpoint with share_percentage constraints.

After refactoring: individual add/update/remove access endpoints have been replaced
by a single PUT /brokers/{id}/access bulk endpoint (atomic replace).
"""

import time
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


def unique_username() -> str:
    """Generate a unique username."""
    timestamp = int(datetime.now().timestamp() * 1000)
    return f"usearch_{timestamp}_{uuid.uuid4().hex[:4]}"


async def create_user_and_login(
    client: httpx.AsyncClient, username: Optional[str] = None
    ) -> dict:
    """Create a new user, login, and return user info dict."""
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

    login_resp = await client.post(
        f"{API_BASE}/auth/login",
        json={"username": username, "password": password},
        timeout=TIMEOUT,
        )
    if login_resp.status_code != 200:
        raise Exception(f"Failed to login: {login_resp.text}")

    session = login_resp.cookies.get("session")
    if session:
        client.cookies.set("session", session)

    return {"user_id": user_id, "username": username, "email": email}


async def create_broker(client: httpx.AsyncClient, name: Optional[str] = None) -> int:
    """Create a broker and return its ID."""
    name = name or f"TestBroker_{int(time.time() * 1000)}"
    resp = await client.post(
        f"{API_BASE}/brokers",
        json=[{"name": name}],
        timeout=TIMEOUT,
        )
    assert resp.status_code == 200, f"Failed to create broker: {resp.text}"
    data = resp.json()
    return data["results"][0]["broker_id"]


async def get_access_list(client: httpx.AsyncClient, broker_id: int) -> list:
    """Get the current access list for a broker."""
    resp = await client.get(
        f"{API_BASE}/brokers/{broker_id}/access",
        timeout=TIMEOUT,
        )
    assert resp.status_code == 200, f"Failed to get access list: {resp.text}"
    return resp.json()["items"]


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture(scope="module")
def test_server():
    """Start test server once for all tests in this module."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


# ============================================================================
# USER SEARCH TESTS
# ============================================================================


class TestUserSearch:
    """Test user search endpoint."""

    @pytest.mark.asyncio
    async def test_search_returns_users(self, test_server):
        """USEARCH-001: Search returns matching users."""
        print_section("USEARCH-001: Search returns matching users")

        async with httpx.AsyncClient() as client:
            user_data = await create_user_and_login(client)
            username = user_data["username"]

            query = username[:10]
            resp = await client.get(
                f"{API_BASE}/users/search",
                params={"q": query},
                timeout=TIMEOUT,
                )
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
            data = resp.json()
            assert "items" in data
            assert len(data["items"]) >= 1

            found = any(u["username"] == username for u in data["items"])
            assert found, f"User {username} not found in results: {data['items']}"

            for u in data["items"]:
                assert "email" not in u, "Email should not be exposed"
                assert "id" in u
                assert "username" in u

            print_success("✓ Search returns matching users with no email exposed")

    @pytest.mark.asyncio
    async def test_search_min_query_length(self, test_server):
        """USEARCH-002: Search requires minimum 2 characters."""
        print_section("USEARCH-002: Search requires min 2 chars")

        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)

            resp = await client.get(
                f"{API_BASE}/users/search",
                params={"q": "a"},
                timeout=TIMEOUT,
                )
            assert resp.status_code == 422

            resp = await client.get(
                f"{API_BASE}/users/search",
                timeout=TIMEOUT,
                )
            assert resp.status_code == 422

            print_success("✓ Short queries rejected with 422")

    @pytest.mark.asyncio
    async def test_search_exclude_broker(self, test_server):
        """USEARCH-003: Search excludes users already on a broker."""
        print_section("USEARCH-003: Exclude users on broker")

        async with httpx.AsyncClient() as owner_client, httpx.AsyncClient() as other_client:
            owner_data = await create_user_and_login(owner_client)
            broker_id = await create_broker(owner_client)
            other_data = await create_user_and_login(other_client)
            other_username = other_data["username"]

            # Search without exclude — should find other user
            resp = await owner_client.get(
                f"{API_BASE}/users/search",
                params={"q": other_username[:10]},
                timeout=TIMEOUT,
                )
            assert resp.status_code == 200
            found = any(u["username"] == other_username for u in resp.json()["items"])
            assert found, "Other user should appear without exclude"

            # Add other user to broker via bulk update
            current = await get_access_list(owner_client, broker_id)
            new_accesses = [
                {
                    "user_id": a["user_id"], "role": a["role"],
                    "share_percentage": float(a["share_percentage"])
                    }
                for a in current
                ]
            new_accesses.append({
                "user_id": other_data["user_id"], "role": "VIEWER", "share_percentage": 0,
                })
            resp = await owner_client.put(
                f"{API_BASE}/brokers/{broker_id}/access",
                json=new_accesses,
                timeout=TIMEOUT,
                )
            assert resp.status_code == 200

            # Search WITH exclude — should NOT find other user
            resp = await owner_client.get(
                f"{API_BASE}/users/search",
                params={"q": other_username[:10], "exclude_broker_id": broker_id},
                timeout=TIMEOUT,
                )
            assert resp.status_code == 200
            found = any(u["username"] == other_username for u in resp.json()["items"])
            assert not found, "Other user should be excluded"

            print_success("✓ Exclude broker filter works")

    @pytest.mark.asyncio
    async def test_search_requires_auth(self, test_server):
        """USEARCH-004: Search requires authentication."""
        print_section("USEARCH-004: Auth required")

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{API_BASE}/users/search",
                params={"q": "test"},
                timeout=TIMEOUT,
                )
            assert resp.status_code == 401

            print_success("✓ Unauthenticated request rejected")

    @pytest.mark.asyncio
    async def test_search_includes_avatar(self, test_server):
        """USEARCH-005: Search results include avatar_url field."""
        print_section("USEARCH-005: Avatar URL in results")

        async with httpx.AsyncClient() as client:
            user_data = await create_user_and_login(client)

            resp = await client.get(
                f"{API_BASE}/users/search",
                params={"q": user_data["username"][:10]},
                timeout=TIMEOUT,
                )
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
            data = resp.json()
            assert len(data["items"]) >= 1

            for u in data["items"]:
                assert "avatar_url" in u

            print_success("✓ Avatar URL field present in results")


# ============================================================================
# BULK ACCESS / SHARE PERCENTAGE VALIDATION TESTS
# ============================================================================


class TestBulkAccessAndSharePercentage:
    """Test PUT /brokers/{id}/access bulk endpoint and share_percentage validation."""

    @pytest.mark.asyncio
    async def test_bulk_replace_access(self, test_server):
        """BULK-001: Bulk replace sets the exact desired access configuration."""
        print_section("BULK-001: Bulk replace access")

        async with httpx.AsyncClient() as owner_client, httpx.AsyncClient() as other_client:
            owner_data = await create_user_and_login(owner_client)
            broker_id = await create_broker(owner_client)
            other_data = await create_user_and_login(other_client)

            resp = await owner_client.put(
                f"{API_BASE}/brokers/{broker_id}/access",
                json=[
                    {"user_id": owner_data["user_id"], "role": "OWNER", "share_percentage": 0.6},
                    {"user_id": other_data["user_id"], "role": "VIEWER", "share_percentage": 0},
                    ],
                timeout=TIMEOUT,
                )
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
            data = resp.json()
            assert data["success_count"] == 2
            assert len(data["results"]) == 2

            accesses = await get_access_list(owner_client, broker_id)
            assert len(accesses) == 2

            print_success("✓ Bulk replace sets exact configuration")

    @pytest.mark.asyncio
    async def test_bulk_sum_exceeds_100_rejected(self, test_server):
        """SHARE-001: Cannot set access if sum of share% would exceed 100%."""
        print_section("SHARE-001: Sum > 100% blocked")

        async with httpx.AsyncClient() as owner_client, httpx.AsyncClient() as other_client:
            owner_data = await create_user_and_login(owner_client)
            broker_id = await create_broker(owner_client)
            other_data = await create_user_and_login(other_client)

            resp = await owner_client.put(
                f"{API_BASE}/brokers/{broker_id}/access",
                json=[
                    {"user_id": owner_data["user_id"], "role": "OWNER", "share_percentage": 0.8},
                    {"user_id": other_data["user_id"], "role": "OWNER", "share_percentage": 0.3},
                    ],
                timeout=TIMEOUT,
                )
            assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"

            print_success("✓ Sum > 100% correctly rejected")

    @pytest.mark.asyncio
    async def test_bulk_sum_at_100_allowed(self, test_server):
        """SHARE-002: Can set access if sum exactly 100%."""
        print_section("SHARE-002: Sum = 100% allowed")

        async with httpx.AsyncClient() as owner_client, httpx.AsyncClient() as other_client:
            owner_data = await create_user_and_login(owner_client)
            broker_id = await create_broker(owner_client)
            other_data = await create_user_and_login(other_client)

            resp = await owner_client.put(
                f"{API_BASE}/brokers/{broker_id}/access",
                json=[
                    {"user_id": owner_data["user_id"], "role": "OWNER", "share_percentage": 0.5},
                    {"user_id": other_data["user_id"], "role": "OWNER", "share_percentage": 0.5},
                    ],
                timeout=TIMEOUT,
                )
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

            print_success("✓ Sum = 100% works")

    @pytest.mark.asyncio
    async def test_bulk_sum_under_100_allowed(self, test_server):
        """SHARE-003: Can set access if sum under 100%."""
        print_section("SHARE-003: Sum < 100% allowed")

        async with httpx.AsyncClient() as owner_client, httpx.AsyncClient() as other_client:
            owner_data = await create_user_and_login(owner_client)
            broker_id = await create_broker(owner_client)
            other_data = await create_user_and_login(other_client)

            resp = await owner_client.put(
                f"{API_BASE}/brokers/{broker_id}/access",
                json=[
                    {"user_id": owner_data["user_id"], "role": "OWNER", "share_percentage": 0.5},
                    {"user_id": other_data["user_id"], "role": "VIEWER", "share_percentage": 0},
                    ],
                timeout=TIMEOUT,
                )
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

            print_success("✓ Sum < 100% works (phantom co-owner)")

    @pytest.mark.asyncio
    async def test_share_only_for_owners(self, test_server):
        """SHARE-004: share_percentage > 0 rejected for EDITOR/VIEWER roles."""
        print_section("SHARE-004: share% only for OWNERs")

        async with httpx.AsyncClient() as owner_client, httpx.AsyncClient() as other_client:
            owner_data = await create_user_and_login(owner_client)
            broker_id = await create_broker(owner_client)
            other_data = await create_user_and_login(other_client)

            # EDITOR with share > 0 → schema validation error (422)
            resp = await owner_client.put(
                f"{API_BASE}/brokers/{broker_id}/access",
                json=[
                    {"user_id": owner_data["user_id"], "role": "OWNER", "share_percentage": 1.0},
                    {"user_id": other_data["user_id"], "role": "EDITOR", "share_percentage": 0.1},
                    ],
                timeout=TIMEOUT,
                )
            assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"

            # VIEWER with share > 0 → schema validation error (422)
            resp = await owner_client.put(
                f"{API_BASE}/brokers/{broker_id}/access",
                json=[
                    {"user_id": owner_data["user_id"], "role": "OWNER", "share_percentage": 1.0},
                    {"user_id": other_data["user_id"], "role": "VIEWER", "share_percentage": 0.05},
                    ],
                timeout=TIMEOUT,
                )
            assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"

            print_success("✓ share_percentage > 0 rejected for non-OWNER roles")

    @pytest.mark.asyncio
    async def test_bulk_requires_at_least_one_owner(self, test_server):
        """BULK-002: Bulk update must keep at least one OWNER."""
        print_section("BULK-002: At least one OWNER required")

        async with httpx.AsyncClient() as owner_client, httpx.AsyncClient() as other_client:
            owner_data = await create_user_and_login(owner_client)
            broker_id = await create_broker(owner_client)
            other_data = await create_user_and_login(other_client)

            resp = await owner_client.put(
                f"{API_BASE}/brokers/{broker_id}/access",
                json=[
                    {"user_id": owner_data["user_id"], "role": "EDITOR", "share_percentage": 0},
                    {"user_id": other_data["user_id"], "role": "VIEWER", "share_percentage": 0},
                    ],
                timeout=TIMEOUT,
                )
            assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"

            print_success("✓ At least one OWNER required")

    @pytest.mark.asyncio
    async def test_bulk_removes_unlisted_users(self, test_server):
        """BULK-003: Users not in the bulk request are removed."""
        print_section("BULK-003: Unlisted users removed")

        async with httpx.AsyncClient() as owner_client, httpx.AsyncClient() as other_client:
            owner_data = await create_user_and_login(owner_client)
            broker_id = await create_broker(owner_client)
            other_data = await create_user_and_login(other_client)

            # Add other user
            resp = await owner_client.put(
                f"{API_BASE}/brokers/{broker_id}/access",
                json=[
                    {"user_id": owner_data["user_id"], "role": "OWNER", "share_percentage": 1.0},
                    {"user_id": other_data["user_id"], "role": "VIEWER", "share_percentage": 0},
                    ],
                timeout=TIMEOUT,
                )
            assert resp.status_code == 200
            accesses = await get_access_list(owner_client, broker_id)
            assert len(accesses) == 2

            # Remove other user by not including them
            resp = await owner_client.put(
                f"{API_BASE}/brokers/{broker_id}/access",
                json=[
                    {"user_id": owner_data["user_id"], "role": "OWNER", "share_percentage": 1.0},
                    ],
                timeout=TIMEOUT,
                )
            assert resp.status_code == 200
            accesses = await get_access_list(owner_client, broker_id)
            assert len(accesses) == 1

            print_success("✓ Unlisted users removed in bulk update")

    @pytest.mark.asyncio
    async def test_bulk_non_owner_rejected(self, test_server):
        """BULK-004: Non-OWNER cannot call bulk update."""
        print_section("BULK-004: Non-OWNER rejected")

        async with httpx.AsyncClient() as owner_client, httpx.AsyncClient() as viewer_client:
            owner_data = await create_user_and_login(owner_client)
            broker_id = await create_broker(owner_client)
            viewer_data = await create_user_and_login(viewer_client)

            # Add viewer
            resp = await owner_client.put(
                f"{API_BASE}/brokers/{broker_id}/access",
                json=[
                    {"user_id": owner_data["user_id"], "role": "OWNER", "share_percentage": 1.0},
                    {"user_id": viewer_data["user_id"], "role": "VIEWER", "share_percentage": 0},
                    ],
                timeout=TIMEOUT,
                )
            assert resp.status_code == 200

            # Viewer tries bulk update → should be rejected
            resp = await viewer_client.put(
                f"{API_BASE}/brokers/{broker_id}/access",
                json=[
                    {"user_id": viewer_data["user_id"], "role": "OWNER", "share_percentage": 1.0},
                    ],
                timeout=TIMEOUT,
                )
            assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"

            print_success("✓ Non-OWNER correctly rejected from bulk update")

    @pytest.mark.asyncio
    async def test_bulk_duplicate_user_ids_rejected(self, test_server):
        """BULK-005: Duplicate user_ids in request are rejected."""
        print_section("BULK-005: Duplicate user_ids rejected")

        async with httpx.AsyncClient() as client:
            user_data = await create_user_and_login(client)
            broker_id = await create_broker(client)

            resp = await client.put(
                f"{API_BASE}/brokers/{broker_id}/access",
                json=[
                    {"user_id": user_data["user_id"], "role": "OWNER", "share_percentage": 0.5},
                    {"user_id": user_data["user_id"], "role": "EDITOR", "share_percentage": 0},
                    ],
                timeout=TIMEOUT,
                )
            assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"

            print_success("✓ Duplicate user_ids rejected")

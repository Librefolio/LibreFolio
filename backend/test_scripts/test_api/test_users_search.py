"""
Tests for User Search API and Share Percentage Validation.

Tests the GET /api/v1/users/search endpoint and share_percentage sum constraints.
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

            query = username[:8]
            resp = await client.get(
                f"{API_BASE}/users/search",
                params={"q": query},
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "users" in data
            assert "count" in data
            assert data["count"] >= 1

            found = any(u["username"] == username for u in data["users"])
            assert found, f"User {username} not found in results"

            for u in data["users"]:
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

            broker_resp = await owner_client.post(
                f"{API_BASE}/brokers",
                json=[{"name": f"SearchTest_{int(time.time()*1000)}"}],
                timeout=TIMEOUT,
            )
            assert broker_resp.status_code == 200
            broker_id = broker_resp.json()["results"][0]["broker_id"]

            other_data = await create_user_and_login(other_client)
            other_username = other_data["username"]

            # Search without exclude
            resp = await owner_client.get(
                f"{API_BASE}/users/search",
                params={"q": other_username[:8]},
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200
            found = any(u["username"] == other_username for u in resp.json()["users"])
            assert found, "Other user should appear without exclude"

            # Add other user to broker
            add_resp = await owner_client.post(
                f"{API_BASE}/brokers/{broker_id}/access",
                json={"user_id": other_data["user_id"], "role": "VIEWER"},
                timeout=TIMEOUT,
            )
            assert add_resp.status_code == 200

            # Search with exclude
            resp = await owner_client.get(
                f"{API_BASE}/users/search",
                params={"q": other_username[:8], "exclude_broker_id": broker_id},
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200
            found = any(u["username"] == other_username for u in resp.json()["users"])
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
                params={"q": user_data["username"][:8]},
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["count"] >= 1

            for u in data["users"]:
                assert "avatar_url" in u

            print_success("✓ Avatar URL field present in results")


# ============================================================================
# SHARE PERCENTAGE VALIDATION TESTS
# ============================================================================


class TestSharePercentageValidation:
    """Test share_percentage sum validation (≤ 100%)."""

    @pytest.mark.asyncio
    async def test_add_access_exceeds_100(self, test_server):
        """SHARE-001: Cannot add access if sum would exceed 100%."""
        print_section("SHARE-001: Sum > 100% blocked on add")

        async with httpx.AsyncClient() as owner_client, httpx.AsyncClient() as other_client:
            await create_user_and_login(owner_client)

            broker_resp = await owner_client.post(
                f"{API_BASE}/brokers",
                json=[{"name": f"ShareTest_{int(time.time()*1000)}"}],
                timeout=TIMEOUT,
            )
            broker_id = broker_resp.json()["results"][0]["broker_id"]

            other_data = await create_user_and_login(other_client)

            # Owner has 100%. Try to add other with 1% -> 101% total
            resp = await owner_client.post(
                f"{API_BASE}/brokers/{broker_id}/access",
                json={
                    "user_id": other_data["user_id"],
                    "role": "EDITOR",
                    "share_percentage": 1,
                },
                timeout=TIMEOUT,
            )
            assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"

            print_success("✓ Adding access with sum > 100% rejected")

    @pytest.mark.asyncio
    async def test_add_access_at_100(self, test_server):
        """SHARE-002: Can add access if sum exactly 100%."""
        print_section("SHARE-002: Sum = 100% allowed")

        async with httpx.AsyncClient() as owner_client, httpx.AsyncClient() as other_client:
            owner_data = await create_user_and_login(owner_client)

            broker_resp = await owner_client.post(
                f"{API_BASE}/brokers",
                json=[{"name": f"ShareEq_{int(time.time()*1000)}"}],
                timeout=TIMEOUT,
            )
            broker_id = broker_resp.json()["results"][0]["broker_id"]

            # Reduce owner to 50%
            patch_resp = await owner_client.patch(
                f"{API_BASE}/brokers/{broker_id}/access/{owner_data['user_id']}",
                json={"role": "OWNER", "share_percentage": 50},
                timeout=TIMEOUT,
            )
            assert patch_resp.status_code == 200

            other_data = await create_user_and_login(other_client)

            # Add other with 50% -> 100% total
            resp = await owner_client.post(
                f"{API_BASE}/brokers/{broker_id}/access",
                json={
                    "user_id": other_data["user_id"],
                    "role": "OWNER",
                    "share_percentage": 50,
                },
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

            print_success("✓ Adding access with sum = 100% works")

    @pytest.mark.asyncio
    async def test_add_access_under_100(self, test_server):
        """SHARE-003: Can add access if sum under 100%."""
        print_section("SHARE-003: Sum < 100% allowed")

        async with httpx.AsyncClient() as owner_client, httpx.AsyncClient() as other_client:
            owner_data = await create_user_and_login(owner_client)

            broker_resp = await owner_client.post(
                f"{API_BASE}/brokers",
                json=[{"name": f"ShareLt_{int(time.time()*1000)}"}],
                timeout=TIMEOUT,
            )
            broker_id = broker_resp.json()["results"][0]["broker_id"]

            # Reduce owner to 50%
            await owner_client.patch(
                f"{API_BASE}/brokers/{broker_id}/access/{owner_data['user_id']}",
                json={"role": "OWNER", "share_percentage": 50},
                timeout=TIMEOUT,
            )

            other_data = await create_user_and_login(other_client)

            # Add other with 0% (viewer) -> 50% total
            resp = await owner_client.post(
                f"{API_BASE}/brokers/{broker_id}/access",
                json={
                    "user_id": other_data["user_id"],
                    "role": "VIEWER",
                    "share_percentage": 0,
                },
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

            print_success("✓ Adding access with sum < 100% works")

    @pytest.mark.asyncio
    async def test_update_access_exceeds_100(self, test_server):
        """SHARE-004: Cannot update share if sum would exceed 100%."""
        print_section("SHARE-004: Sum > 100% blocked on update")

        async with httpx.AsyncClient() as owner_client, httpx.AsyncClient() as other_client:
            await create_user_and_login(owner_client)

            broker_resp = await owner_client.post(
                f"{API_BASE}/brokers",
                json=[{"name": f"ShareUpd_{int(time.time()*1000)}"}],
                timeout=TIMEOUT,
            )
            broker_id = broker_resp.json()["results"][0]["broker_id"]

            other_data = await create_user_and_login(other_client)

            # Add other with 0%
            await owner_client.post(
                f"{API_BASE}/brokers/{broker_id}/access",
                json={"user_id": other_data["user_id"], "role": "EDITOR"},
                timeout=TIMEOUT,
            )

            # Try to set other to 1% -> 101% total (owner=100, other=1)
            resp = await owner_client.patch(
                f"{API_BASE}/brokers/{broker_id}/access/{other_data['user_id']}",
                json={"role": "EDITOR", "share_percentage": 1},
                timeout=TIMEOUT,
            )
            assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"

            print_success("✓ Updating share with sum > 100% rejected")


"""
Broker Multi-User Role API Tests.

Tests for role-based permissions on broker operations:
- OWNER: Can do everything (CRUD, manage access, delete)
- EDITOR: Can modify broker and transactions, cannot delete or share
- VIEWER: Read-only access

Tests verify that operations are correctly allowed/denied based on role.
"""

import contextlib
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

import httpx
import pytest

from backend.app.config import get_settings
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_error, print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30


def unique_name(prefix: str) -> str:
    """Generate a unique name."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def unique_username() -> str:
    """Generate a unique username."""
    timestamp = int(datetime.now().timestamp() * 1000)
    return f"multi_test_{timestamp}_{uuid.uuid4().hex[:8]}"


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

        async with httpx.AsyncClient() as client, _owning("MULTI-001") as owned:
            user_id, _ = await create_user_and_login(client)
            broker_id = await _new_broker(client, owned, "MULTI001")

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

        async with httpx.AsyncClient() as owner_client, httpx.AsyncClient() as editor_client, _owning("MULTI-002") as owned:
            # Owner creates broker
            await create_user_and_login(owner_client)
            broker_id = await _new_broker(owner_client, owned, "MULTI002")

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

        async with httpx.AsyncClient() as owner_client, httpx.AsyncClient() as editor_client, _owning("MULTI-003") as owned:
            await create_user_and_login(owner_client)
            broker_id = await _new_broker(owner_client, owned, "MULTI003")

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

        async with httpx.AsyncClient() as owner_client, httpx.AsyncClient() as viewer_client, _owning("MULTI-004") as owned:
            await create_user_and_login(owner_client)
            broker_id = await _new_broker(owner_client, owned, "MULTI004")

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

        async with httpx.AsyncClient() as owner_client, httpx.AsyncClient() as viewer_client, _owning("MULTI-005") as owned:
            await create_user_and_login(owner_client)
            broker_id = await _new_broker(owner_client, owned, "MULTI005")

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

        async with httpx.AsyncClient() as owner_client, httpx.AsyncClient() as editor_client, _owning("MULTI-007") as owned:

            await create_user_and_login(owner_client)
            broker_id = await _new_broker(owner_client, owned, "MULTI007")

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

        async with httpx.AsyncClient() as owner_client, httpx.AsyncClient() as viewer_client, _owning("MULTI-008") as owned:

            await create_user_and_login(owner_client)
            broker_id = await _new_broker(owner_client, owned, "MULTI008")

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

        async with httpx.AsyncClient() as owner_client, httpx.AsyncClient() as viewer_client, _owning("MULTI-008b") as owned:
            await create_user_and_login(owner_client)
            broker_id = await _new_broker(owner_client, owned, "MULTI008b")

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

        async with httpx.AsyncClient() as owner_client, httpx.AsyncClient() as viewer_client, _owning("MULTI-008c") as owned:
            await create_user_and_login(owner_client)
            broker_id = await _new_broker(owner_client, owned, "MULTI008c")

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

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "restricted_role",
        ["VIEWER", None],
        ids=["viewer-on-second-broker", "no-access-on-second-broker"],
    )
    async def test_cross_broker_access_failure_is_atomic(
        self,
        test_server,
        restricted_role,
    ):
        """EDITOR access on one broker cannot partially apply a two-broker batch.

        V-23: the refusal sits on the row that touches the restricted broker — create #1 here. Before the fix
        it is always (create, 0, None), the row of the broker the user may write.
        """
        print_section("MULTI-008d: Cross-broker access failure is atomic")
        # W-B12: the test owns its two brokers and cleans them up as the V-23 tests below do, after a red too.
        # ``_new_broker`` records each broker the moment it exists; ``_Owned.drop`` has the owner delete them with
        # force, which takes their accesses (ON DELETE CASCADE) and any transaction a regression wrote with them.
        # Users stay, as in the rest of this module.
        owned = _Owned()

        async with (
            httpx.AsyncClient() as owner_client,
            httpx.AsyncClient() as editor_client,
        ):
            try:
                await create_user_and_login(owner_client)
                editable_broker_id = await _new_broker(owner_client, owned, "M008dEditable")
                restricted_broker_id = await _new_broker(owner_client, owned, "M008dRestricted")

                editor_id, _ = await create_user_and_login(editor_client)
                await add_access(
                    owner_client,
                    editable_broker_id,
                    editor_id,
                    "EDITOR",
                )
                if restricted_role is not None:
                    await add_access(
                        owner_client,
                        restricted_broker_id,
                        editor_id,
                        restricted_role,
                    )

                editable_marker = unique_name("editable-create")
                restricted_marker = unique_name("restricted-create")
                response = await editor_client.post(
                    f"{API_BASE}/transactions/commit",
                    json={
                        "creates": [
                            {
                                "broker_id": editable_broker_id,
                                "type": "DEPOSIT",
                                "date": date.today().isoformat(),
                                "cash": {"code": "EUR", "amount": "100"},
                                "description": editable_marker,
                            },
                            {
                                "broker_id": restricted_broker_id,
                                "type": "DEPOSIT",
                                "date": date.today().isoformat(),
                                "cash": {"code": "EUR", "amount": "200"},
                                "description": restricted_marker,
                            },
                        ]
                    },
                    timeout=TIMEOUT,
                )

                assert response.status_code == 200, response.text
                body = response.json()
                assert body["committed"] is False
                assert body["results"] == []
                assert body["success_count"] == 0
                access_issues = [issue for issue in body["issues"] if issue["code"] == "accessDenied"]
                assert len(access_issues) == 1
                assert access_issues[0]["params"] == {"brokerId": restricted_broker_id}

                for broker_id, marker in (
                    (editable_broker_id, editable_marker),
                    (restricted_broker_id, restricted_marker),
                ):
                    check = await owner_client.get(
                        f"{API_BASE}/transactions",
                        params={"broker_id": broker_id},
                        timeout=TIMEOUT,
                    )
                    assert check.status_code == 200, check.text
                    assert not any(tx.get("description") == marker for tx in check.json())

                # V-23: last, so every check above has run when this one is red.
                denial = access_issues[0]
                assert (denial["operation"], denial["index"], denial["ref_id"]) == ("create", 1, None), f"the refusal must sit on create #1, the only row on broker {restricted_broker_id}; got {denial}"

                print_success("✓ Access denial returned no results or partial writes")
            finally:
                # drop() never raises, so a red body propagates untouched. What it could not delete is printed here,
                # where it shows beside a red body too, and fails the test below when the body was green.
                leftovers = await owned.drop()
                if leftovers:
                    print_error(f"MULTI-008d cleanup left behind: {leftovers}")
        assert not leftovers, leftovers


class TestEditorRestrictions:
    """Tests for EDITOR role restrictions."""

    @pytest.mark.asyncio
    async def test_editor_cannot_delete_broker(self, test_server):
        """MULTI-009: EDITOR cannot delete broker (requires OWNER)."""
        print_section("MULTI-009: Editor cannot delete broker")

        async with httpx.AsyncClient() as owner_client, httpx.AsyncClient() as editor_client, _owning("MULTI-009") as owned:
            await create_user_and_login(owner_client)
            broker_id = await _new_broker(owner_client, owned, "MULTI009")

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
            _owning("MULTI-010") as owned,
        ):
            await create_user_and_login(owner_client)
            broker_id = await _new_broker(owner_client, owned, "MULTI010")

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


# ============================================================================
# V-23 — THE ACCESS REFUSAL SITS ON THE ROW THAT TOUCHES THE BROKER
# ============================================================================
#
# A batch touching a broker on which the user lacks EDITOR is refused whole: committed=false, nothing
# written. The refusal is an issue, and the editor shows an issue on the row its coordinates point at,
# (operation, index, ref_id). So there is one refusal per ROW touching such a broker, carrying that row's
# coordinates — create #i with ref_id None, update / delete / split #i with ref_id the saved transaction
# on that broker — and params.brokerId naming the broker. Before the fix there is one refusal per BROKER,
# always at (create, 0, None) whatever row touched it: the TRANSFER whose receiving leg lands on a broker the
# user only views is reported on its sending leg, and an update, a delete or a split is reported as a create.
#
# Every test owns its users, brokers and asset. The cleanup deletes the brokers with force (their
# transactions go with them, both halves of a pair in one call), then the asset — after a red too. Users
# stay, as in the rest of this module.


@dataclass
class _Owned:
    """Brokers and assets one test created, each with the client of a user allowed to delete it."""

    brokers: list[tuple[httpx.AsyncClient, int]] = field(default_factory=list)
    assets: list[tuple[httpx.AsyncClient, int]] = field(default_factory=list)

    async def drop(self) -> list[str]:
        """Delete the brokers (force), grouped by owner, then the assets. Never raises: what is left is returned."""
        problems: list[str] = []
        by_owner: dict[int, tuple[httpx.AsyncClient, list[int]]] = {}
        for client, broker_id in self.brokers:
            by_owner.setdefault(id(client), (client, []))[1].append(broker_id)
        for client, broker_ids in by_owner.values():
            try:
                resp = await client.delete(f"{API_BASE}/brokers", params={"ids": broker_ids, "force": True}, timeout=TIMEOUT)
                deleted = {r.get("id") for r in resp.json().get("results", []) if r.get("success")} if resp.status_code == 200 else set()
                problems += [f"broker {broker_id}: HTTP {resp.status_code} {resp.text}" for broker_id in broker_ids if broker_id not in deleted]
            except Exception as exc:
                problems.append(f"brokers {broker_ids}: {exc!r}")
        for client, asset_id in self.assets:
            try:
                resp = await client.delete(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)
                deleted = {r.get("asset_id") for r in resp.json().get("results", []) if r.get("success")} if resp.status_code == 200 else set()
                if asset_id not in deleted:
                    problems.append(f"asset {asset_id}: HTTP {resp.status_code} {resp.text}")
            except Exception as exc:
                problems.append(f"asset {asset_id}: {exc!r}")
        return problems


@contextlib.asynccontextmanager
async def _owning(label: str):
    """The brokers a test creates with ``_new_broker``, dropped when the test ends.

    The contract of MULTI-008d's explicit ``try/finally`` (the V-23 tests' cleanup, plus the print): dropped after a
    red too, a red body propagates untouched (``drop`` never raises), what could not be deleted is printed, and a
    green body with leftovers fails. Use it as the LAST context of the ``async with``, so it exits while the clients
    are open.
    """
    owned = _Owned()
    try:
        yield owned
    finally:
        leftovers = await owned.drop()
        if leftovers:
            print_error(f"{label} cleanup left behind: {leftovers}")
    assert not leftovers, leftovers


async def _new_broker(client: httpx.AsyncClient, owned: _Owned, prefix: str, **flags) -> int:
    """A broker ``client``'s user owns, recorded for the cleanup the moment it exists."""
    name = unique_name(prefix)
    resp = await client.post(f"{API_BASE}/brokers", json=[{"name": name, **flags}], timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    row = next(r for r in resp.json()["results"] if r["name"] == name)
    assert row["success"] is True, row
    owned.brokers.append((client, row["broker_id"]))
    return row["broker_id"]


async def _new_asset(client: httpx.AsyncClient, owned: _Owned, prefix: str) -> int:
    """An asset of this test only, recorded for the cleanup the moment it exists."""
    name = unique_name(prefix)
    resp = await client.post(f"{API_BASE}/assets", json=[{"display_name": name, "asset_type": "STOCK", "currency": "USD"}], timeout=TIMEOUT)
    assert resp.status_code in (200, 201), resp.text
    row = next(r for r in resp.json()["results"] if r["display_name"] == name)
    assert row["success"] is True, row
    owned.assets.append((client, row["asset_id"]))
    return row["asset_id"]


async def _grant(owner_client: httpx.AsyncClient, broker_id: int, user_id: int, role: str) -> None:
    """``add_access``, verified: the role is read back from the broker's access list."""
    await add_access(owner_client, broker_id, user_id, role)
    resp = await owner_client.get(f"{API_BASE}/brokers/{broker_id}/access", timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    roles = {item["user_id"]: item["role"] for item in resp.json()["items"]}
    assert roles.get(user_id) == role, f"Precondition: user {user_id} must be {role} on broker {broker_id}, access list {roles}"


async def _editable_and_viewed(owner_client: httpx.AsyncClient, member_client: httpx.AsyncClient, owned: _Owned, **flags) -> tuple[int, int]:
    """Register the owner and the member; two brokers of the owner, the member EDITOR on the first and VIEWER on the second."""
    await create_user_and_login(owner_client)
    member_id, _ = await create_user_and_login(member_client)
    editable = await _new_broker(owner_client, owned, "V23Edit", **flags)
    viewed = await _new_broker(owner_client, owned, "V23View", **flags)
    await _grant(owner_client, editable, member_id, "EDITOR")
    await _grant(owner_client, viewed, member_id, "VIEWER")
    return editable, viewed


def _deposit(broker_id: int, amount: str, description: Optional[str] = None) -> dict:
    row = {"broker_id": broker_id, "type": "DEPOSIT", "date": date.today().isoformat(), "cash": {"code": "EUR", "amount": amount}}
    if description is not None:
        row["description"] = description
    return row


async def _commit_creates(client: httpx.AsyncClient, creates: list[dict]) -> list[int]:
    """Setup: commit ``creates`` as one batch and return the id of each create, in request order."""
    resp = await client.post(f"{API_BASE}/transactions/commit", json={"creates": creates}, timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["committed"] is True, f"Setup commit rejected: {body['issues']}"
    ids = {r["index"]: r["ids"] for r in body["results"] if r["operation"] == "create"}
    assert sorted(ids) == list(range(len(creates))) and all(len(tx_ids) == 1 for tx_ids in ids.values()), body["results"]
    return [ids[index][0] for index in range(len(creates))]


async def _read(client: httpx.AsyncClient, tx_ids: list[int]) -> dict[int, dict]:
    """The transactions among ``tx_ids`` that ``client`` can see, by id."""
    resp = await client.get(f"{API_BASE}/transactions", params={"ids": tx_ids}, timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    return {tx["id"]: tx for tx in resp.json()}


async def _broker_tx_ids(client: httpx.AsyncClient, broker_id: int) -> list[int]:
    """Ids of every transaction of ``broker_id`` (a broker of this test: the whole list is ours)."""
    resp = await client.get(f"{API_BASE}/transactions", params={"broker_id": broker_id}, timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    return sorted(tx["id"] for tx in resp.json())


def _access_denials(body: dict) -> list[tuple[str, int, Optional[int], Optional[int]]]:
    """Every accessDenied issue of a batch response as (operation, index, ref_id, params.brokerId), sorted."""
    denials = [(issue["operation"], issue["index"], issue["ref_id"], (issue.get("params") or {}).get("brokerId")) for issue in body["issues"] if issue.get("code") == "accessDenied"]
    return sorted(denials, key=lambda d: (d[0], d[1], -1 if d[2] is None else d[2], -1 if d[3] is None else d[3]))


class TestAccessRefusalPlacement:
    """V-23: one refusal per row touching a broker without EDITOR, on that row's coordinates."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint", ["validate", "commit"])
    async def test_v23_transfer_refused_on_the_leg_landing_on_a_viewer_broker(self, test_server, endpoint):
        """V-23 as reported: a TRANSFER from a broker the member owns to one it only views.

        Creates #0 (sending leg, broker S: OWNER) and #1 (receiving leg, broker R: VIEWER) share a link_uuid.
        Only #1 touches R, so the one refusal is (create, 1, None) with params {"brokerId": R}. Access is
        checked before balances: no holding is needed for the refusal. Before the fix: (create, 0, None),
        the sending leg, on the broker the member may write.
        """
        print_section(f"V-23: TRANSFER refused on its receiving leg ({endpoint})")
        owned = _Owned()
        async with httpx.AsyncClient() as member_client, httpx.AsyncClient() as owner_client:
            try:
                member_id, _ = await create_user_and_login(member_client)
                await create_user_and_login(owner_client)
                sender_broker = await _new_broker(member_client, owned, "V23Send")
                receiver_broker = await _new_broker(owner_client, owned, "V23Recv")
                await _grant(owner_client, receiver_broker, member_id, "VIEWER")
                asset_id = await _new_asset(member_client, owned, "V23Asset")

                link = str(uuid.uuid4())
                marker = unique_name("v23-transfer")
                day = date.today().isoformat()
                legs = [
                    {"broker_id": sender_broker, "asset_id": asset_id, "type": "TRANSFER", "date": day, "quantity": "-5", "link_uuid": link, "description": marker},
                    {"broker_id": receiver_broker, "asset_id": asset_id, "type": "TRANSFER", "date": day, "quantity": "5", "link_uuid": link, "description": marker, "cost_basis_override": {"code": "USD", "amount": "50"}},
                ]
                resp = await member_client.post(f"{API_BASE}/transactions/{endpoint}", json={"creates": legs}, timeout=TIMEOUT)

                assert resp.status_code == 200, resp.text
                body = resp.json()
                assert body["committed"] is False, body
                assert await _broker_tx_ids(member_client, sender_broker) == [], "a refused batch writes nothing on the sending broker"
                assert await _broker_tx_ids(owner_client, receiver_broker) == [], "a refused batch writes nothing on the receiving broker"
                assert _access_denials(body) == [("create", 1, None, receiver_broker)], f"one refusal, on the receiving leg (create #1), the only row on broker {receiver_broker} the member cannot write; issues: {body['issues']}"
                (denial,) = [issue for issue in body["issues"] if issue.get("code") == "accessDenied"]
                assert denial["params"] == {"brokerId": receiver_broker}, denial
                print_success("✓ The refusal sits on the receiving leg")
            finally:
                leftovers = await owned.drop()
        assert not leftovers, leftovers

    @pytest.mark.asyncio
    async def test_v23_one_refusal_per_row_on_the_viewer_broker(self, test_server):
        """V-23: one refusal per ROW touching the broker, not one per broker.

        creates [#0 viewed, #1 editable, #2 viewed] → (create, 0) and (create, 2), both naming the viewed
        broker. Before the fix a single (create, 0) stands for the broker: #2 is never pointed at.
        """
        print_section("V-23: one refusal per refused row")
        owned = _Owned()
        async with httpx.AsyncClient() as owner_client, httpx.AsyncClient() as member_client:
            try:
                editable, viewed = await _editable_and_viewed(owner_client, member_client, owned)
                creates = [_deposit(viewed, "100"), _deposit(editable, "200"), _deposit(viewed, "300")]
                resp = await member_client.post(f"{API_BASE}/transactions/commit", json={"creates": creates}, timeout=TIMEOUT)

                assert resp.status_code == 200, resp.text
                body = resp.json()
                assert body["committed"] is False, body
                for broker_id in (editable, viewed):
                    assert await _broker_tx_ids(owner_client, broker_id) == [], f"a refused batch writes nothing on broker {broker_id}"
                assert _access_denials(body) == [("create", 0, None, viewed), ("create", 2, None, viewed)], f"one refusal per row on broker {viewed} (creates #0 and #2); issues: {body['issues']}"
                print_success("✓ Each refused row carries its own refusal")
            finally:
                leftovers = await owned.drop()
        assert not leftovers, leftovers

    @pytest.mark.asyncio
    async def test_v23_update_refused_on_the_row_of_the_viewer_broker(self, test_server):
        """V-23, updates: [#0 a row of the editable broker, #1 a row of the viewed broker] → (update, 1, ref_id=that row).

        Nothing is written: both rows keep their description. Before the fix: (create, 0, None) — an update
        reported as a create that the batch does not even contain.
        """
        print_section("V-23: update refused on the viewer broker's row")
        owned = _Owned()
        async with httpx.AsyncClient() as owner_client, httpx.AsyncClient() as member_client:
            try:
                editable, viewed = await _editable_and_viewed(owner_client, member_client, owned)
                editable_tx, viewed_tx = await _commit_creates(owner_client, [_deposit(editable, "100", unique_name("v23-editable")), _deposit(viewed, "100", unique_name("v23-viewed"))])
                before = {tx_id: tx["description"] for tx_id, tx in (await _read(owner_client, [editable_tx, viewed_tx])).items()}
                assert set(before) == {editable_tx, viewed_tx}, f"Precondition: the owner reads both rows: {before}"

                updates = [{"id": editable_tx, "description": unique_name("v23-edited")}, {"id": viewed_tx, "description": unique_name("v23-edited")}]
                resp = await member_client.post(f"{API_BASE}/transactions/commit", json={"updates": updates}, timeout=TIMEOUT)

                assert resp.status_code == 200, resp.text
                body = resp.json()
                assert body["committed"] is False, body
                after = {tx_id: tx["description"] for tx_id, tx in (await _read(owner_client, [editable_tx, viewed_tx])).items()}
                assert after == before, "a refused batch changes no row"
                assert _access_denials(body) == [("update", 1, viewed_tx, viewed)], f"one refusal, on update #1 (transaction {viewed_tx} of broker {viewed}); issues: {body['issues']}"
                print_success("✓ The refusal sits on the refused update")
            finally:
                leftovers = await owned.drop()
        assert not leftovers, leftovers

    @pytest.mark.asyncio
    async def test_v23_delete_refused_on_the_row_of_the_viewer_broker(self, test_server):
        """V-23, deletes: [#0 a row of the editable broker, #1 a row of the viewed broker] → (delete, 1, ref_id=that row).

        Nothing is deleted. Before the fix: (create, 0, None).
        """
        print_section("V-23: delete refused on the viewer broker's row")
        owned = _Owned()
        async with httpx.AsyncClient() as owner_client, httpx.AsyncClient() as member_client:
            try:
                editable, viewed = await _editable_and_viewed(owner_client, member_client, owned)
                editable_tx, viewed_tx = await _commit_creates(owner_client, [_deposit(editable, "100"), _deposit(viewed, "100")])

                resp = await member_client.post(f"{API_BASE}/transactions/commit", json={"deletes": [editable_tx, viewed_tx]}, timeout=TIMEOUT)

                assert resp.status_code == 200, resp.text
                body = resp.json()
                assert body["committed"] is False, body
                assert set(await _read(owner_client, [editable_tx, viewed_tx])) == {editable_tx, viewed_tx}, "a refused batch deletes nothing"
                assert _access_denials(body) == [("delete", 1, viewed_tx, viewed)], f"one refusal, on delete #1 (transaction {viewed_tx} of broker {viewed}); issues: {body['issues']}"
                print_success("✓ The refusal sits on the refused delete")
            finally:
                leftovers = await owned.drop()
        assert not leftovers, leftovers

    @pytest.mark.asyncio
    async def test_v23_split_refused_on_the_leg_of_the_viewer_broker(self, test_server):
        """V-23, splits: a saved CASH_TRANSFER whose second leg is on the viewed broker → (split, 0, ref_id=that leg).

        The owner, OWNER of both brokers, saves the pair; the member (EDITOR on the sending broker, VIEWER on
        the receiving one) asks to split it with id_a = the editable leg, id_b = the viewed leg. Nothing is
        written: both legs stay a linked CASH_TRANSFER. Before the fix: (create, 0, None).
        """
        print_section("V-23: split refused on the viewer broker's leg")
        owned = _Owned()
        async with httpx.AsyncClient() as owner_client, httpx.AsyncClient() as member_client:
            try:
                editable, viewed = await _editable_and_viewed(owner_client, member_client, owned, allow_cash_overdraft=True)
                link = str(uuid.uuid4())
                marker = unique_name("v23-cash-transfer")
                day = date.today().isoformat()
                editable_leg, viewed_leg = await _commit_creates(
                    owner_client,
                    [
                        {"broker_id": editable, "type": "CASH_TRANSFER", "date": day, "cash": {"code": "EUR", "amount": "-100"}, "link_uuid": link, "description": marker},
                        {"broker_id": viewed, "type": "CASH_TRANSFER", "date": day, "cash": {"code": "EUR", "amount": "100"}, "link_uuid": link, "description": marker},
                    ],
                )
                pair = {tx_id: (tx["type"], tx["related_transaction_id"]) for tx_id, tx in (await _read(owner_client, [editable_leg, viewed_leg])).items()}
                assert pair == {editable_leg: ("CASH_TRANSFER", viewed_leg), viewed_leg: ("CASH_TRANSFER", editable_leg)}, f"Precondition: the two legs are a linked CASH_TRANSFER pair: {pair}"

                resp = await member_client.post(f"{API_BASE}/transactions/commit", json={"splits": [{"id_a": editable_leg, "id_b": viewed_leg}]}, timeout=TIMEOUT)

                assert resp.status_code == 200, resp.text
                body = resp.json()
                assert body["committed"] is False, body
                after = {tx_id: (tx["type"], tx["related_transaction_id"]) for tx_id, tx in (await _read(owner_client, [editable_leg, viewed_leg])).items()}
                assert after == pair, "a refused batch splits nothing"
                assert _access_denials(body) == [("split", 0, viewed_leg, viewed)], f"one refusal, on split #0, pointing at the leg on broker {viewed} (transaction {viewed_leg}); issues: {body['issues']}"
                print_success("✓ The refusal sits on the refused split, at the viewer broker's leg")
            finally:
                leftovers = await owned.drop()
        assert not leftovers, leftovers

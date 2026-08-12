"""Asset merge API tests — ``POST /api/v1/assets/merge``.

The merge *service* is covered in depth by ``test_db/test_asset_merge.py`` (12 tests on
transactions, prices, events, provider assignments and identifier demotion). What was
missing is the **HTTP surface**: status codes, body shape and the guarantee that
``dry_run`` writes nothing — the contract the confirmation dialog is built on.

Origin: P3 (asset identity), plan-phase00AssetIdentityAndIdentifiers.
"""

import uuid

import httpx
import pytest

from backend.app.config import get_settings
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def create_user_and_login(client: httpx.AsyncClient) -> str:
    username = f"merge_{uuid.uuid4().hex[:8]}"
    resp = await client.post(
        f"{API_BASE}/auth/register",
        json={"username": username, "email": f"{username}@test.com", "password": "TestPass123!"},
        timeout=TIMEOUT,
    )
    assert resp.status_code == 201, resp.text
    login = await client.post(
        f"{API_BASE}/auth/login",
        json={"username": username, "password": "TestPass123!"},
        timeout=TIMEOUT,
    )
    assert login.status_code == 200, login.text
    if session := login.cookies.get("session"):
        client.cookies.set("session", session)
    return username


async def create_broker(client: httpx.AsyncClient) -> int:
    resp = await client.post(
        f"{API_BASE}/brokers",
        json=[{"name": f"MergeBk_{uuid.uuid4().hex[:6]}", "allow_cash_overdraft": True}],
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["results"][0]["broker_id"]


async def create_bond(client: httpx.AsyncClient, isin: str, other: list[str] | None = None) -> int:
    """Create a bond carrying one primary ISIN and optional alternate identifiers."""
    payload: dict = {
        "display_name": f"BTP_{uuid.uuid4().hex[:6]}",
        "currency": "EUR",
        "asset_type": "BOND",
        "identifier_isin": isin,
    }
    if other:
        payload["identifier_other"] = other
    resp = await client.post(f"{API_BASE}/assets", json=[payload], timeout=TIMEOUT)
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["results"][0]["asset_id"]


async def get_asset(client: httpx.AsyncClient, asset_id: int) -> dict | None:
    """Read one asset back.

    ``/assets/query`` is the only endpoint exposing the raw identifier columns
    (``identifier_isin``, ``identifier_other``); the bulk read returns classification
    metadata instead. It has no id filter, so the row is picked client-side.
    """
    resp = await client.get(f"{API_BASE}/assets/query", timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    return next((row for row in resp.json() if row.get("id") == asset_id), None)


async def buy(client: httpx.AsyncClient, broker_id: int, asset_id: int, date: str) -> None:
    resp = await client.post(
        f"{API_BASE}/transactions/commit",
        json={
            "creates": [
                {"broker_id": broker_id, "type": "DEPOSIT", "date": date, "quantity": "0", "cash": {"code": "EUR", "amount": "1000"}},
                {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": date, "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
            ]
        },
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json().get("committed") is True, resp.text


async def count_transactions(client: httpx.AsyncClient, asset_id: int) -> int:
    resp = await client.get(f"{API_BASE}/transactions", params={"asset_id": asset_id}, timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    return len(resp.json())


@pytest.fixture(scope="module")
def test_server():
    with _TestingServerManager() as manager:
        if not manager.start_server():
            pytest.fail("Failed to start test server")
        yield manager


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAssetMergeEndpoint:
    """HTTP contract of ``POST /assets/merge``."""

    @pytest.mark.asyncio
    async def test_dry_run_writes_nothing_but_counts_for_real(self, test_server):
        """A preview must be free: real counts, zero side effects.

        This is what the confirmation dialog shows before anything is destroyed, so a
        preview that either lies about the counts or writes anyway is equally useless.
        """
        print_section("Merge API: dry_run previews without writing")
        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)
            broker_id = await create_broker(client)
            cum = await create_bond(client, "IT0005332827")
            mkt = await create_bond(client, "IT0005274805")
            await buy(client, broker_id, cum, "2025-03-01")

            resp = await client.post(
                f"{API_BASE}/assets/merge",
                json={"source_asset_id": cum, "target_asset_id": mkt, "dry_run": True},
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200, resp.text
            body = resp.json()

            assert body["dry_run"] is True
            assert body["success"] is True
            assert body["preview"]["transactions"] == 1, "preview must report the real number of movable transactions"
            assert "IT0005332827" in body["preview"]["identifiers_added"]

            # Nothing moved: the source is still there, still owning its transaction.
            assert await get_asset(client, cum) is not None, "dry_run deleted the source asset"
            assert await count_transactions(client, cum) == 1, "dry_run moved transactions"
            assert await count_transactions(client, mkt) == 0

        print_success("✓ dry_run returns real counts and writes nothing")

    @pytest.mark.asyncio
    async def test_merge_moves_transactions_and_deletes_the_source(self, test_server):
        print_section("Merge API: execution moves and deletes")
        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)
            broker_id = await create_broker(client)
            cum = await create_bond(client, "IT0005332827")
            mkt = await create_bond(client, "IT0005274805")
            await buy(client, broker_id, cum, "2025-03-02")

            resp = await client.post(
                f"{API_BASE}/assets/merge",
                json={"source_asset_id": cum, "target_asset_id": mkt},
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200, resp.text
            body = resp.json()

            assert body["success"] is True
            assert body["dry_run"] is False
            assert body["target_asset_id"] == mkt
            assert body["preview"]["transactions"] == 1

            assert await get_asset(client, cum) is None, "source asset survived the merge"
            assert await count_transactions(client, mkt) == 1, "transaction did not follow the merge"

        print_success("✓ merge moves the transaction and deletes the source")

    @pytest.mark.asyncio
    async def test_survivor_identifiers_are_the_union(self, test_server):
        """The whole point of P3: a code that cannot quote must still recognise.

        The placement ISIN is demoted into ``identifier_other``, never dropped — a later
        report carrying only that code has to find the asset again.
        """
        print_section("Merge API: identifiers are unioned, not replaced")
        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)
            cum = await create_bond(client, "IT0005332827", other=["XS9999999999"])
            mkt = await create_bond(client, "IT0005274805", other=["BTP-MKT-ALT"])

            resp = await client.post(
                f"{API_BASE}/assets/merge",
                json={"source_asset_id": cum, "target_asset_id": mkt},
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200, resp.text

            survivor = await get_asset(client, mkt)
            assert survivor is not None
            assert survivor["identifier_isin"] == "IT0005274805", "the quoted ISIN must stay primary"
            alternates = set(survivor.get("identifier_other") or [])
            assert {"IT0005332827", "XS9999999999", "BTP-MKT-ALT"} <= alternates, f"identifiers were lost: {alternates}"

        print_success("✓ survivor keeps every identifier from both sides")

    @pytest.mark.asyncio
    async def test_explicit_primary_swaps_and_demotes(self, test_server):
        print_section("Merge API: explicit primary election")
        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)
            cum = await create_bond(client, "IT0005332827")
            mkt = await create_bond(client, "IT0005274805")

            resp = await client.post(
                f"{API_BASE}/assets/merge",
                json={
                    "source_asset_id": cum,
                    "target_asset_id": mkt,
                    "identifier_primaries": {"identifier_isin": "IT0005332827"},
                },
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200, resp.text

            survivor = await get_asset(client, mkt)
            assert survivor is not None
            assert survivor["identifier_isin"] == "IT0005332827"
            assert "IT0005274805" in set(survivor.get("identifier_other") or []), "the demoted ISIN was dropped instead of kept"

        print_success("✓ explicit primary swaps the ISINs and demotes the loser")

    @pytest.mark.asyncio
    async def test_unknown_primary_is_refused(self, test_server):
        """A value belonging to neither asset is a typo, not a decision."""
        print_section("Merge API: unknown primary refused")
        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)
            cum = await create_bond(client, "IT0005332827")
            mkt = await create_bond(client, "IT0005274805")

            resp = await client.post(
                f"{API_BASE}/assets/merge",
                json={
                    "source_asset_id": cum,
                    "target_asset_id": mkt,
                    "identifier_primaries": {"identifier_isin": "IT0000000000"},
                },
                timeout=TIMEOUT,
            )
            assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"
            # Refusal must be total: nothing merged.
            assert await get_asset(client, cum) is not None

        print_success("✓ unknown primary is refused and nothing is merged")

    @pytest.mark.asyncio
    async def test_missing_asset_is_404_and_self_merge_is_400(self, test_server):
        print_section("Merge API: missing asset and self-merge")
        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)
            mkt = await create_bond(client, "IT0005274805")

            missing = await client.post(
                f"{API_BASE}/assets/merge",
                json={"source_asset_id": 99_999_999, "target_asset_id": mkt},
                timeout=TIMEOUT,
            )
            assert missing.status_code == 404, f"Expected 404, got {missing.status_code}: {missing.text}"

            same = await client.post(
                f"{API_BASE}/assets/merge",
                json={"source_asset_id": mkt, "target_asset_id": mkt},
                timeout=TIMEOUT,
            )
            assert same.status_code == 400, f"Expected 400, got {same.status_code}: {same.text}"
            assert await get_asset(client, mkt) is not None, "self-merge deleted the asset"

        print_success("✓ 404 for a missing asset, 400 for a self-merge")

    @pytest.mark.asyncio
    async def test_merge_requires_authentication(self, test_server):
        """Destructive and unauthenticated is the one combination that must not exist."""
        print_section("Merge API: authentication required")
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{API_BASE}/assets/merge",
                json={"source_asset_id": 1, "target_asset_id": 2},
                timeout=TIMEOUT,
            )
            assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"

        print_success("✓ anonymous merge is rejected")

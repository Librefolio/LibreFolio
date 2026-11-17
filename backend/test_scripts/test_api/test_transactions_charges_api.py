"""
Linked charges over HTTP (project 66, lot R3).

A charge (FEE, TAX) may point at a parent (BUY, SELL, DIVIDEND, INTEREST, DEPOSIT, WITHDRAWAL) through
``parent_transaction_id``. Covered here, end to end against the shared test backend:

- ``POST /transactions/commit``: a create names its parent by ``parent_ref`` (a ``ref`` of the same batch) or
  ``parent_transaction_id`` (a saved row); the link is written; a parent the user cannot see is "not found", never
  "access denied", and nothing is written.
- ``POST /transactions/validate``: same pipeline, nothing written.
- ``GET /transactions``: ``parent_transaction_id`` and ``charges_count`` on both branches (``ids`` and filters), the
  filters ``parent_ids`` and ``without_parent`` (with ``broker_id``, ``asset_id``, ``types``, ``limit``/``offset``),
  both ignored when ``ids`` is given.
- ``GET /transactions/types``: ``charge_role`` of every type.

RED until R3: the strict create schema refuses ``ref``, ``parent_ref`` and ``parent_transaction_id``, the read items
lack the two fields, the two filters do not exist and the type metadata does not expose ``charge_role`` over the wire.

Every test creates its own user, broker(s) and asset, and lists are always scoped by ``broker_id``: neighbours never
matter. Assertions are on ids, codes and params, never on translated text.
"""

import uuid
from datetime import date
from typing import Optional

import httpx
import pytest

from backend.app.config import get_settings
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30
TODAY = date.today().isoformat()


# ============================================================================
# HELPERS
# ============================================================================


async def _login_new_user(client: httpx.AsyncClient) -> None:
    """Register a fresh user and leave its session cookie on the client."""
    username = f"txch_{uuid.uuid4().hex[:12]}"
    password = "TestPass123!"
    resp = await client.post(f"{API_BASE}/auth/register", json={"username": username, "email": f"{username}@test.com", "password": password}, timeout=TIMEOUT)
    assert resp.status_code == 201, resp.text
    login = await client.post(f"{API_BASE}/auth/login", json={"username": username, "password": password}, timeout=TIMEOUT)
    assert login.status_code == 200, login.text
    cookie = login.cookies.get("session")
    assert cookie, "login returned no session cookie"
    client.cookies.set("session", cookie)


async def _make_broker(client: httpx.AsyncClient) -> int:
    resp = await client.post(f"{API_BASE}/brokers", json=[{"name": f"Charges Broker {uuid.uuid4().hex[:8]}", "allow_cash_overdraft": True}], timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    result = resp.json()["results"][0]
    assert result["success"], result
    return result["broker_id"]


async def _make_asset(client: httpx.AsyncClient) -> int:
    payload = [{"display_name": f"Charges Stock {uuid.uuid4().hex[:8]}", "asset_type": "STOCK", "currency": "EUR"}]
    resp = await client.post(f"{API_BASE}/assets", json=payload, timeout=TIMEOUT)
    assert resp.status_code == 201, resp.text
    result = resp.json()["results"][0]
    assert result["success"], result
    return result["asset_id"]


def _buy(broker_id: int, asset_id: int, **extra) -> dict:
    return {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": TODAY, "quantity": "10", "cash": {"code": "EUR", "amount": "-100"}, **extra}


def _charge(kind: str, broker_id: int, asset_id: Optional[int] = None, amount: str = "-1", **extra) -> dict:
    item = {"broker_id": broker_id, "type": kind, "date": TODAY, "quantity": "0", "cash": {"code": "EUR", "amount": amount}, **extra}
    if asset_id is not None:
        item["asset_id"] = asset_id
    return item


def _deposit(broker_id: int) -> dict:
    return {"broker_id": broker_id, "type": "DEPOSIT", "date": TODAY, "cash": {"code": "EUR", "amount": "500"}}


async def _post_batch(client: httpx.AsyncClient, endpoint: str, creates: list[dict]) -> dict:
    resp = await client.post(f"{API_BASE}/transactions/{endpoint}", json={"creates": creates}, timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _commit_ok(client: httpx.AsyncClient, creates: list[dict]) -> list[int]:
    """Commit, require success, return the id of each create, by index."""
    body = await _post_batch(client, "commit", creates)
    assert body["committed"] is True, body["issues"]
    ids = {r["index"]: r["ids"][0] for r in body["results"] if r["operation"] == "create"}
    assert sorted(ids) == list(range(len(creates))), body["results"]
    return [ids[i] for i in range(len(creates))]


async def _list(client: httpx.AsyncClient, **params) -> list[dict]:
    resp = await client.get(f"{API_BASE}/transactions", params=params, timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _broker_ids(client: httpx.AsyncClient, broker_id: int) -> set[int]:
    return {tx["id"] for tx in await _list(client, broker_id=broker_id)}


async def _cleanup(client: httpx.AsyncClient, broker_ids: list[int], asset_ids: list[int]) -> None:
    """Brokers first (they hold the transactions), then the assets: both were created by the test."""
    for broker_id in broker_ids:
        await client.delete(f"{API_BASE}/brokers", params={"ids": [broker_id], "force": True}, timeout=TIMEOUT)
    if asset_ids:
        await client.delete(f"{API_BASE}/assets", params={"asset_ids": asset_ids}, timeout=TIMEOUT)


# ============================================================================
# FIXTURE
# ============================================================================


@pytest.fixture(scope="module")
def test_server():
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


# ============================================================================
# TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_commit_links_charges_and_read_shows_them(test_server):
    """Commit [BUY r1, FEE parent_ref r1, TAX parent_ref r1]: the links, charges_count, and the `ids` branch."""
    print_section("charges: commit by parent_ref, read fields")
    async with httpx.AsyncClient() as client:
        await _login_new_user(client)
        broker_id = await _make_broker(client)
        asset_id = await _make_asset(client)
        try:
            buy, fee, tax = await _commit_ok(
                client,
                [_buy(broker_id, asset_id, ref="r1"), _charge("FEE", broker_id, asset_id, parent_ref="r1"), _charge("TAX", broker_id, asset_id, parent_ref="r1")],
            )
            rows = {tx["id"]: tx for tx in await _list(client, broker_id=broker_id)}
            assert {buy, fee, tax} <= set(rows), rows.keys()
            assert rows[fee]["parent_transaction_id"] == buy
            assert rows[tax]["parent_transaction_id"] == buy
            assert rows[buy]["parent_transaction_id"] is None
            assert rows[buy]["charges_count"] == 2
            assert rows[fee]["charges_count"] == 0
            assert rows[tax]["charges_count"] == 0

            # the `ids` branch carries the same fields
            by_ids = {tx["id"]: tx for tx in await _list(client, ids=[buy, fee])}
            assert by_ids[buy]["charges_count"] == 2
            assert by_ids[buy]["parent_transaction_id"] is None
            assert by_ids[fee]["parent_transaction_id"] == buy
            assert by_ids[fee]["charges_count"] == 0
            print_success("charges linked, counted on both read branches")
        finally:
            await _cleanup(client, [broker_id], [asset_id])


@pytest.mark.asyncio
async def test_commit_links_charge_to_saved_parent(test_server):
    """A later batch points a charge at a saved parent by parent_transaction_id."""
    print_section("charges: commit by parent_transaction_id")
    async with httpx.AsyncClient() as client:
        await _login_new_user(client)
        broker_id = await _make_broker(client)
        asset_id = await _make_asset(client)
        try:
            (buy,) = await _commit_ok(client, [_buy(broker_id, asset_id)])
            (fee,) = await _commit_ok(client, [_charge("FEE", broker_id, asset_id, parent_transaction_id=buy)])
            rows = {tx["id"]: tx for tx in await _list(client, ids=[buy, fee])}
            assert rows[fee]["parent_transaction_id"] == buy
            assert rows[buy]["charges_count"] == 1
        finally:
            await _cleanup(client, [broker_id], [asset_id])


@pytest.mark.asyncio
async def test_parent_ids_filter_returns_only_the_charges_of_those_parents(test_server):
    """?parent_ids=<b1>&parent_ids=<b2> → exactly the charges of the two parents, not other rows of the broker."""
    print_section("charges: parent_ids filter")
    async with httpx.AsyncClient() as client:
        await _login_new_user(client)
        broker_id = await _make_broker(client)
        asset_id = await _make_asset(client)
        try:
            ids = await _commit_ok(
                client,
                [
                    _buy(broker_id, asset_id, ref="a"),
                    _buy(broker_id, asset_id, ref="b"),
                    _buy(broker_id, asset_id, ref="c"),
                    _charge("FEE", broker_id, asset_id, parent_ref="a"),
                    _charge("TAX", broker_id, asset_id, parent_ref="a"),
                    _charge("FEE", broker_id, asset_id, parent_ref="b"),
                    _charge("FEE", broker_id, asset_id, parent_ref="c"),  # a third parent: must not show up
                    _charge("FEE", broker_id, asset_id),  # unlinked: must not show up
                ],
            )
            buy_a, buy_b, buy_c, fee_a, tax_a, fee_b, fee_c, loose = ids
            rows = await _list(client, broker_id=broker_id, parent_ids=[buy_a, buy_b])
            assert {tx["id"] for tx in rows} == {fee_a, tax_a, fee_b}
            assert {tx["id"] for tx in rows}.isdisjoint({buy_a, buy_b, buy_c, fee_c, loose})
        finally:
            await _cleanup(client, [broker_id], [asset_id])


@pytest.mark.asyncio
async def test_without_parent_filter(test_server):
    """?without_parent=true → the unlinked FEE/TAX only; combines with asset_id, types, limit/offset."""
    print_section("charges: without_parent filter")
    async with httpx.AsyncClient() as client:
        await _login_new_user(client)
        broker_id = await _make_broker(client)
        asset_id = await _make_asset(client)
        try:
            ids = await _commit_ok(
                client,
                [
                    _buy(broker_id, asset_id, ref="p"),
                    _charge("FEE", broker_id, asset_id, parent_ref="p"),  # linked: never offered
                    _charge("FEE", broker_id, asset_id),  # unlinked, with asset
                    _charge("FEE", broker_id),  # unlinked, no asset
                    _charge("TAX", broker_id, asset_id),  # unlinked, with asset
                    _deposit(broker_id),  # not a charge
                ],
            )
            _buy_id, linked, fee_asset, fee_cash, tax_asset, _dep = ids
            expected = {fee_asset, fee_cash, tax_asset}

            rows = await _list(client, broker_id=broker_id, without_parent=True)
            assert {tx["id"] for tx in rows} == expected

            rows = await _list(client, broker_id=broker_id, without_parent=True, asset_id=asset_id)
            assert {tx["id"] for tx in rows} == {fee_asset, tax_asset}

            rows = await _list(client, broker_id=broker_id, without_parent=True, types=["TAX"])
            assert {tx["id"] for tx in rows} == {tax_asset}

            # walk the pages: each unlinked charge once, then an empty page
            seen = []
            for offset in range(3):
                page = await _list(client, broker_id=broker_id, without_parent=True, limit=1, offset=offset)
                assert len(page) == 1, f"offset {offset}: {page}"
                seen.append(page[0]["id"])
            assert sorted(seen) == sorted(expected), seen
            assert await _list(client, broker_id=broker_id, without_parent=True, limit=1, offset=3) == []
            assert linked not in seen
        finally:
            await _cleanup(client, [broker_id], [asset_id])


@pytest.mark.asyncio
async def test_ids_wins_over_charge_filters(test_server):
    """With `ids`, parent_ids and without_parent are ignored: the id asked comes back."""
    print_section("charges: ids ignores the charge filters")
    async with httpx.AsyncClient() as client:
        await _login_new_user(client)
        broker_id = await _make_broker(client)
        asset_id = await _make_asset(client)
        try:
            buy, fee = await _commit_ok(client, [_buy(broker_id, asset_id, ref="p"), _charge("FEE", broker_id, asset_id, parent_ref="p")])
            # the BUY is no charge of anything and is not an unlinked charge: both filters would hide it
            rows = await _list(client, ids=[buy], parent_ids=[fee])
            assert [tx["id"] for tx in rows] == [buy]
            rows = await _list(client, ids=[buy], without_parent=True)
            assert [tx["id"] for tx in rows] == [buy]
        finally:
            await _cleanup(client, [broker_id], [asset_id])


@pytest.mark.asyncio
async def test_validate_with_charge_writes_nothing(test_server):
    """/validate on [BUY r1, FEE parent_ref r1]: no issues, and the broker still has no rows."""
    print_section("charges: validate writes nothing")
    async with httpx.AsyncClient() as client:
        await _login_new_user(client)
        broker_id = await _make_broker(client)
        asset_id = await _make_asset(client)
        try:
            body = await _post_batch(client, "validate", [_buy(broker_id, asset_id, ref="r1"), _charge("FEE", broker_id, asset_id, parent_ref="r1")])
            assert body["issues"] == [], body["issues"]
            assert body["committed"] is False
            assert await _broker_ids(client, broker_id) == set()
        finally:
            await _cleanup(client, [broker_id], [asset_id])


@pytest.mark.asyncio
async def test_parent_of_another_user_is_not_found_and_nothing_is_written(test_server):
    """User B links a FEE on B's broker to a BUY of user A: chargeParentNotFound {parentId}, no accessDenied."""
    print_section("charges: a parent the user cannot see")
    async with httpx.AsyncClient() as client_a, httpx.AsyncClient() as client_b:
        await _login_new_user(client_a)
        await _login_new_user(client_b)
        broker_a = await _make_broker(client_a)
        broker_b = await _make_broker(client_b)
        asset_id = await _make_asset(client_a)
        try:
            (buy_a,) = await _commit_ok(client_a, [_buy(broker_a, asset_id)])
            body = await _post_batch(client_b, "commit", [_charge("FEE", broker_b, parent_transaction_id=buy_a)])
            assert body["committed"] is False
            codes = [issue["code"] for issue in body["issues"]]
            assert "accessDenied" not in codes, body["issues"]
            issue = next(i for i in body["issues"] if i["code"] == "chargeParentNotFound")
            assert issue["operation"] == "create"
            assert issue["index"] == 0
            assert issue["params"]["parentId"] == buy_a
            assert await _broker_ids(client_b, broker_b) == set()
            assert {tx["id"] for tx in await _list(client_a, broker_id=broker_a)} == {buy_a}
        finally:
            await _cleanup(client_a, [broker_a], [asset_id])
            await _cleanup(client_b, [broker_b], [])


@pytest.mark.asyncio
async def test_types_expose_charge_role(test_server):
    """GET /transactions/types: FEE/TAX are "charge", the six parent types "parent", every other type null."""
    print_section("charges: charge_role in the type metadata")
    async with httpx.AsyncClient() as client:
        await _login_new_user(client)
        resp = await client.get(f"{API_BASE}/transactions/types", timeout=TIMEOUT)
        assert resp.status_code == 200, resp.text
        roles = {t["code"]: t["charge_role"] for t in resp.json()["transaction_types"]}
        charges = {"FEE", "TAX"}
        parents = {"BUY", "SELL", "DIVIDEND", "INTEREST", "DEPOSIT", "WITHDRAWAL"}
        assert charges | parents <= set(roles)
        for code in charges:
            assert roles[code] == "charge", code
        for code in parents:
            assert roles[code] == "parent", code
        for code, role in roles.items():
            if code not in charges | parents:
                assert role is None, f"{code} must have no charge role, got {role}"

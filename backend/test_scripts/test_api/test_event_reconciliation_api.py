"""
Test Suite: Event reconciliation — ``GET /api/v1/transactions/event-reconciliation`` (N68, lot X5-3)

The button «Ricollega eventi» of the Transactions page: after a currency change the dividend, interest and adjustment
transactions that were linked to the deleted events have ``asset_event_id`` NULL. This endpoint lists, for the caller,
every such transaction with the asset events it could be linked to again.

Contract:

- Rows: the caller's transactions that have an ``asset_id``, no ``asset_event_id`` and an event-compatible type
  (DIVIDEND, INTEREST, ADJUSTMENT; ``event_compatible`` in ``schemas/transactions/type_metadata.py``), on brokers where
  the caller is at least EDITOR (they are the ones who can link: a viewer-only broker's rows do not appear, nor do the
  rows of a broker the caller has no access to).
- Optional query filters ``broker_id`` and ``asset_id``. Order: newest first (date desc, id desc).
- Item (a ``StrictModel`` in ``schemas/transactions/``): ``transaction_id``, ``broker_id``, ``asset_id``, ``date``,
  ``type``, ``status`` in {``unique``, ``none``, ``several``}, ``candidates`` (a list of the existing
  ``TXEventSuggestCandidate``).
- Candidates: the rule of ``TransactionEventSuggestionsMixin.suggest_events_bulk`` with ``tolerance_days=0``: same asset,
  SAME DATE (no window), the event type that corresponds (DIVIDEND -> DIVIDEND, INTEREST -> INTEREST, ADJUSTMENT ->
  PRICE_ADJUSTMENT or SPLIT). ``unique`` = exactly one candidate, ``none`` = zero, ``several`` = more than one, all listed.
- The endpoint writes nothing and never links by itself. Linking is the existing batch update
  (``POST /transactions/commit`` with ``updates: [{id, asset_event_id}]``, ``asset_event_id`` > 0).

Dates are fixed and in the past: the API refuses a transaction dated after tomorrow.

Isolation: every test registers its own users and creates its own brokers and assets under unique names; each row it
reads is identified by the ids it created. The caller's list is filtered to those ids: it never counts or reads a row it
did not write.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

import httpx
import pytest
import pytest_asyncio

from backend.app.config import get_settings
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30
ENDPOINT = f"{API_BASE}/transactions/event-reconciliation"
WIDE_RANGE = {"start": "2000-01-01", "end": (date.today() + timedelta(days=365)).isoformat()}
ITEM_KEYS = ["asset_id", "broker_id", "candidates", "date", "status", "transaction_id", "type"]
CANDIDATE_KEYS = ["asset_id", "currency", "date", "distance_days", "id", "is_auto", "type", "value"]


@pytest.fixture(scope="module")
def test_server():
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


# ============================================================================
# Actors and rows
# ============================================================================


@dataclass
class _Actor:
    """A registered, logged-in user and the brokers it created."""

    client: httpx.AsyncClient
    user_id: int
    broker_ids: list[int] = field(default_factory=list)


@dataclass
class _World:
    """Everything the test created, dropped at the end: every actor's brokers (force: their transactions go with them),
    then the assets (their events cascade), then the clients."""

    actors: list[_Actor] = field(default_factory=list)
    asset_ids: list[int] = field(default_factory=list)

    async def actor(self) -> _Actor:
        client = httpx.AsyncClient()
        username = f"recon_{uuid.uuid4().hex[:12]}"
        password = "TestPass123!"
        reg = await client.post(f"{API_BASE}/auth/register", json={"username": username, "email": f"{username}@test.com", "password": password}, timeout=TIMEOUT)
        assert reg.status_code == 201, reg.text
        login = await client.post(f"{API_BASE}/auth/login", json={"username": username, "password": password}, timeout=TIMEOUT)
        assert login.status_code == 200, login.text
        session = login.cookies.get("session")
        if session:
            client.cookies.set("session", session)
        actor = _Actor(client=client, user_id=reg.json()["user"]["id"])
        self.actors.append(actor)
        return actor

    async def drop(self) -> list[str]:
        problems: list[str] = []
        for actor in self.actors:
            for broker_id in actor.broker_ids:
                try:
                    resp = await actor.client.delete(f"{API_BASE}/brokers", params={"ids": [broker_id], "force": True}, timeout=TIMEOUT)
                    if resp.status_code != 200:
                        problems.append(f"broker {broker_id}: {resp.status_code} {resp.text}")
                except Exception as exc:  # noqa: BLE001 — cleanup reports instead of masking the test's own outcome
                    problems.append(f"broker {broker_id}: {exc!r}")
        if self.asset_ids and self.actors:
            try:
                resp = await self.actors[0].client.delete(f"{API_BASE}/assets", params={"asset_ids": self.asset_ids}, timeout=TIMEOUT)
                if resp.status_code != 200:
                    problems.append(f"assets {self.asset_ids}: {resp.status_code} {resp.text}")
            except Exception as exc:  # noqa: BLE001
                problems.append(f"assets {self.asset_ids}: {exc!r}")
        for actor in self.actors:
            await actor.client.aclose()
        return problems


@pytest_asyncio.fixture
async def world(test_server):
    w = _World()
    yield w
    problems = await w.drop()
    assert not problems, problems


async def _asset(world: _World, actor: _Actor, currency: str = "USD") -> int:
    name = f"Recon Asset {uuid.uuid4().hex}"
    resp = await actor.client.post(f"{API_BASE}/assets", json=[{"display_name": name, "currency": currency}], timeout=TIMEOUT)
    assert resp.status_code in (200, 201), resp.text
    row = next(r for r in resp.json()["results"] if r["display_name"] == name)
    assert row["success"] is True, row
    world.asset_ids.append(row["asset_id"])
    return row["asset_id"]


async def _broker(actor: _Actor) -> int:
    name = f"Recon Broker {uuid.uuid4().hex}"
    resp = await actor.client.post(f"{API_BASE}/brokers", json=[{"name": name, "allow_cash_overdraft": True}], timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    row = next(r for r in resp.json()["results"] if r["name"] == name)
    assert row["success"] is True, row
    actor.broker_ids.append(row["broker_id"])
    return row["broker_id"]


async def _set_role(owner: _Actor, broker_id: int, grants: dict[int, str]) -> None:
    """Replace the broker's access list: the owner, and ``grants`` {user id: role}."""
    accesses = [{"user_id": owner.user_id, "role": "OWNER", "share_percentage": 1.0}] + [{"user_id": uid, "role": role, "share_percentage": 0} for uid, role in grants.items()]
    resp = await owner.client.put(f"{API_BASE}/brokers/{broker_id}/access", json=accesses, timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text


async def _event(actor: _Actor, asset_id: int, day: date, kind: str, currency: str = "USD") -> int:
    """One manual event of type ``kind`` on ``day``; its id, read back."""
    resp = await actor.client.post(
        f"{API_BASE}/assets/events",
        json=[{"asset_id": asset_id, "events": [{"date": day.isoformat(), "type": kind, "value": {"code": currency, "amount": "1.5"}}]}],
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, resp.text
    query = await actor.client.post(f"{API_BASE}/assets/events/query", json=[{"asset_id": asset_id, "date_range": WIDE_RANGE}], timeout=TIMEOUT)
    assert query.status_code == 200, query.text
    events = next(item for item in query.json()["items"] if item["asset_id"] == asset_id)["events"]
    ids = [e["id"] for e in events if e["date"] == day.isoformat() and e["type"] == kind]
    assert len(ids) == 1, f"expected one {kind} on {day} for asset {asset_id}, got {events}"
    return ids[0]


def _create_item(broker_id: int, asset_id: int | None, kind: str, day: date, event_id: int | None = None) -> dict[str, Any]:
    row: dict[str, Any] = {"broker_id": broker_id, "type": kind, "date": day.isoformat()}
    if asset_id is not None:
        row["asset_id"] = asset_id
    if kind in ("DIVIDEND", "INTEREST"):
        row["cash"] = {"code": "USD", "amount": "5"}
    elif kind == "ADJUSTMENT":
        row["quantity"] = "5"
        row["cost_basis_override"] = {"code": "USD", "amount": "10"}
    elif kind == "BUY":
        row["quantity"] = "1"
        row["cash"] = {"code": "USD", "amount": "-10"}
    elif kind == "DEPOSIT":
        row["quantity"] = "0"
        row["cash"] = {"code": "USD", "amount": "100"}
    if event_id is not None:
        row["asset_event_id"] = event_id
    return row


async def _commit(actor: _Actor, creates: list[dict[str, Any]]) -> list[int]:
    resp = await actor.client.post(f"{API_BASE}/transactions/commit", json={"creates": creates}, timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["committed"] is True, body["issues"]
    ids = {r["index"]: r["ids"][0] for r in body["results"] if r["operation"] == "create"}
    return [ids[i] for i in range(len(creates))]


async def _tx(actor: _Actor, broker_id: int, asset_id: int | None, kind: str, day: date, event_id: int | None = None) -> int:
    return (await _commit(actor, [_create_item(broker_id, asset_id, kind, day, event_id)]))[0]


async def _tx_rows(actor: _Actor, ids: list[int]) -> dict[int, dict[str, Any]]:
    resp = await actor.client.get(f"{API_BASE}/transactions", params={"ids": ids}, timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    return {tx["id"]: tx for tx in resp.json()}


# ============================================================================
# The endpoint, read as the client reads it
# ============================================================================


async def _reconciliation(actor: _Actor, **params: Any) -> list[dict[str, Any]]:
    """Every item of the endpoint for ``actor`` (a bare list, or an object holding ``items``: the container is the cure's
    choice, the items are the contract). Fails with the endpoint's own answer when it is not a 200."""
    resp = await actor.client.get(ENDPOINT, params=params, timeout=TIMEOUT)
    assert resp.status_code == 200, f"GET /transactions/event-reconciliation answered {resp.status_code}: {resp.text}. Red today: the endpoint does not exist"
    body = resp.json()
    items = body["items"] if isinstance(body, dict) else body
    assert isinstance(items, list), body
    return items


def _mine(items: list[dict[str, Any]], tx_ids: list[int]) -> dict[int, dict[str, Any]]:
    """The items whose transaction this test created, by transaction id."""
    wanted = set(tx_ids)
    return {item["transaction_id"]: item for item in items if item["transaction_id"] in wanted}


def _candidate_ids(item: dict[str, Any]) -> list[int]:
    return sorted(c["id"] for c in item["candidates"])


# ============================================================================
# Tests
# ============================================================================


@pytest.mark.asyncio
async def test_each_compatible_type_gets_its_unique_candidate_of_the_matching_type(world):
    """A DIVIDEND, an INTEREST and an ADJUSTMENT (a price adjustment event) on three days, each day also holding an event of
    another type: each transaction is ``unique`` with the one event of the type that corresponds; the item and candidate
    carry exactly the contract's keys."""
    print_section("Reconciliation: unique, mapping per type")
    user = await world.actor()
    asset_id = await _asset(world, user)
    broker_id = await _broker(user)
    d1, d2, d3 = date(2026, 5, 4), date(2026, 5, 5), date(2026, 5, 6)
    dividend_ev = await _event(user, asset_id, d1, "DIVIDEND")
    await _event(user, asset_id, d1, "INTEREST")  # decoy: the wrong type for a DIVIDEND
    interest_ev = await _event(user, asset_id, d2, "INTEREST")
    await _event(user, asset_id, d2, "DIVIDEND")  # decoy
    adjustment_ev = await _event(user, asset_id, d3, "PRICE_ADJUSTMENT")
    await _event(user, asset_id, d3, "DIVIDEND")  # decoy
    dividend_tx = await _tx(user, broker_id, asset_id, "DIVIDEND", d1)
    interest_tx = await _tx(user, broker_id, asset_id, "INTEREST", d2)
    adjustment_tx = await _tx(user, broker_id, asset_id, "ADJUSTMENT", d3)

    items = _mine(await _reconciliation(user), [dividend_tx, interest_tx, adjustment_tx])

    assert set(items) == {dividend_tx, interest_tx, adjustment_tx}, f"all three unlinked, event-compatible rows are listed: {sorted(items)}"
    for tx_id, kind, day, event_id in ((dividend_tx, "DIVIDEND", d1, dividend_ev), (interest_tx, "INTEREST", d2, interest_ev), (adjustment_tx, "ADJUSTMENT", d3, adjustment_ev)):
        item = items[tx_id]
        assert sorted(item) == ITEM_KEYS, f"item keys: {sorted(item)}"
        assert (item["broker_id"], item["asset_id"], item["date"], item["type"]) == (broker_id, asset_id, day.isoformat(), kind), item
        assert item["status"] == "unique", item
        assert _candidate_ids(item) == [event_id], f"{kind} transaction {tx_id}: expected the one event {event_id}, got {item['candidates']}"
        candidate = item["candidates"][0]
        assert sorted(candidate) == CANDIDATE_KEYS, f"candidate keys: {sorted(candidate)}"
        assert (candidate["asset_id"], candidate["date"], candidate["distance_days"], candidate["is_auto"]) == (asset_id, day.isoformat(), 0, False), candidate
    assert items[adjustment_tx]["candidates"][0]["type"] == "PRICE_ADJUSTMENT"
    print_success("DIVIDEND/INTEREST/ADJUSTMENT: unique, right type, exact keys")


@pytest.mark.asyncio
async def test_adjustment_maps_to_split_or_price_adjustment_and_several_lists_all(world):
    """ADJUSTMENT maps to PRICE_ADJUSTMENT or SPLIT, never to a DIVIDEND. One day with a SPLIT only, one with a
    PRICE_ADJUSTMENT only, one with both (``several``: both listed), one with a DIVIDEND only (``none``)."""
    print_section("Reconciliation: ADJUSTMENT mapping, several")
    user = await world.actor()
    asset_id = await _asset(world, user)
    broker_id = await _broker(user)
    days = [date(2026, 6, 1) + timedelta(days=i) for i in range(4)]
    split_only = await _event(user, asset_id, days[0], "SPLIT")
    price_only = await _event(user, asset_id, days[1], "PRICE_ADJUSTMENT")
    both_split = await _event(user, asset_id, days[2], "SPLIT")
    both_price = await _event(user, asset_id, days[2], "PRICE_ADJUSTMENT")
    await _event(user, asset_id, days[3], "DIVIDEND")
    txs = await _commit(user, [_create_item(broker_id, asset_id, "ADJUSTMENT", day) for day in days])

    items = _mine(await _reconciliation(user), txs)

    assert set(items) == set(txs), sorted(items)
    split_item, price_item, several_item, none_item = (items[tx] for tx in txs)
    assert (split_item["status"], _candidate_ids(split_item), split_item["candidates"][0]["type"]) == ("unique", [split_only], "SPLIT"), split_item
    assert (price_item["status"], _candidate_ids(price_item), price_item["candidates"][0]["type"]) == ("unique", [price_only], "PRICE_ADJUSTMENT"), price_item
    assert several_item["status"] == "several" and _candidate_ids(several_item) == sorted([both_split, both_price]), several_item
    assert {c["type"] for c in several_item["candidates"]} == {"SPLIT", "PRICE_ADJUSTMENT"}, several_item
    assert (none_item["status"], none_item["candidates"]) == ("none", []), f"a DIVIDEND event is no candidate of an ADJUSTMENT: {none_item}"
    print_success("ADJUSTMENT: SPLIT / PRICE_ADJUSTMENT candidates, several lists both, DIVIDEND excluded")


@pytest.mark.asyncio
async def test_an_event_on_another_day_or_of_another_asset_is_no_candidate(world):
    """No window: a DIVIDEND event the day before and the day after is not a candidate (``none``, empty list); neither is
    the same-day DIVIDEND event of another asset; an INTEREST with no event at all is ``none`` too."""
    print_section("Reconciliation: none")
    user = await world.actor()
    asset_id = await _asset(world, user)
    other_asset = await _asset(world, user)
    broker_id = await _broker(user)
    day = date(2026, 7, 15)
    await _event(user, asset_id, day - timedelta(days=1), "DIVIDEND")
    await _event(user, asset_id, day + timedelta(days=1), "DIVIDEND")
    await _event(user, other_asset, day, "DIVIDEND")
    dividend_tx = await _tx(user, broker_id, asset_id, "DIVIDEND", day)
    interest_tx = await _tx(user, broker_id, asset_id, "INTEREST", day)

    items = _mine(await _reconciliation(user), [dividend_tx, interest_tx])

    assert set(items) == {dividend_tx, interest_tx}, "rows with no candidate are still listed"
    for tx_id in (dividend_tx, interest_tx):
        assert (items[tx_id]["status"], items[tx_id]["candidates"]) == ("none", []), items[tx_id]
    print_success("other day / other asset: none")


@pytest.mark.asyncio
async def test_linked_and_incompatible_rows_do_not_appear(world):
    """A DIVIDEND already linked to its event, a BUY (not event-compatible) and a DEPOSIT (no asset) are not listed; the
    unlinked DIVIDEND is."""
    print_section("Reconciliation: which rows appear")
    user = await world.actor()
    asset_id = await _asset(world, user)
    broker_id = await _broker(user)
    day = date(2026, 8, 3)
    linked_event = await _event(user, asset_id, day, "DIVIDEND")
    linked_tx = await _tx(user, broker_id, asset_id, "DIVIDEND", day, event_id=linked_event)
    buy_tx = await _tx(user, broker_id, asset_id, "BUY", day)
    deposit_tx = await _tx(user, broker_id, None, "DEPOSIT", day)
    open_tx = await _tx(user, broker_id, asset_id, "DIVIDEND", day + timedelta(days=1))

    items = _mine(await _reconciliation(user), [linked_tx, buy_tx, deposit_tx, open_tx])

    assert set(items) == {open_tx}, f"only the unlinked, event-compatible, asset-bearing row is listed: {sorted(items)}"
    print_success("linked, BUY and DEPOSIT rows are left out")


@pytest.mark.asyncio
async def test_only_brokers_where_the_caller_is_editor_or_owner_appear(world):
    """Viewer-only broker rows do not appear, another user's broker rows do not appear; an EDITOR's and the OWNER's do. The
    role is read now: raising a VIEWER to EDITOR makes its row appear, lowering an EDITOR to VIEWER removes it."""
    print_section("Reconciliation: broker roles")
    owner = await world.actor()
    member = await world.actor()
    stranger = await world.actor()
    asset_id = await _asset(world, owner)
    day = date(2026, 4, 9)
    broker_viewer = await _broker(owner)
    broker_editor = await _broker(owner)
    broker_own = await _broker(member)
    broker_foreign = await _broker(stranger)
    await _set_role(owner, broker_viewer, {member.user_id: "VIEWER"})
    await _set_role(owner, broker_editor, {member.user_id: "EDITOR"})
    tx_viewer = await _tx(owner, broker_viewer, asset_id, "DIVIDEND", day)
    tx_editor = await _tx(owner, broker_editor, asset_id, "DIVIDEND", day)
    tx_own = await _tx(member, broker_own, asset_id, "DIVIDEND", day)
    tx_foreign = await _tx(stranger, broker_foreign, asset_id, "DIVIDEND", day)
    everything = [tx_viewer, tx_editor, tx_own, tx_foreign]

    assert set(_mine(await _reconciliation(member), everything)) == {tx_editor, tx_own}, "member: its own broker and the one where it is EDITOR; not the VIEWER one, not the foreign one"
    assert set(_mine(await _reconciliation(owner), everything)) == {tx_viewer, tx_editor}, "owner: both of its brokers, nothing of the others"
    assert set(_mine(await _reconciliation(stranger), everything)) == {tx_foreign}, "stranger: only its own broker"

    await _set_role(owner, broker_viewer, {member.user_id: "EDITOR"})
    await _set_role(owner, broker_editor, {member.user_id: "VIEWER"})
    assert set(_mine(await _reconciliation(member), everything)) == {tx_viewer, tx_own}, "roles swapped: the list follows"
    print_success("VIEWER and foreign brokers excluded, EDITOR and OWNER included, role read live")


@pytest.mark.asyncio
async def test_filters_by_broker_and_asset(world):
    """``broker_id`` and ``asset_id`` narrow the list, together or alone; a broker the caller has no editor access to
    narrows it to nothing of this test's."""
    print_section("Reconciliation: filters")
    user = await world.actor()
    stranger = await world.actor()
    a1, a2 = await _asset(world, user), await _asset(world, user)
    b1, b2 = await _broker(user), await _broker(user)
    foreign_broker = await _broker(stranger)
    day = date(2026, 4, 10)
    t_b1_a1 = await _tx(user, b1, a1, "DIVIDEND", day)
    t_b1_a2 = await _tx(user, b1, a2, "DIVIDEND", day)
    t_b2_a1 = await _tx(user, b2, a1, "DIVIDEND", day)
    everything = [t_b1_a1, t_b1_a2, t_b2_a1]

    assert set(_mine(await _reconciliation(user), everything)) == set(everything), "no filter: all of them"
    assert set(_mine(await _reconciliation(user, broker_id=b1), everything)) == {t_b1_a1, t_b1_a2}
    assert set(_mine(await _reconciliation(user, asset_id=a1), everything)) == {t_b1_a1, t_b2_a1}
    assert set(_mine(await _reconciliation(user, broker_id=b1, asset_id=a1), everything)) == {t_b1_a1}
    assert set(_mine(await _reconciliation(user, broker_id=foreign_broker), everything)) == set(), "a broker the caller cannot edit lists nothing"
    print_success("broker_id / asset_id filters")


@pytest.mark.asyncio
async def test_rows_come_newest_first(world):
    """Date descending, then id descending: three days, two rows on the latest one."""
    print_section("Reconciliation: order")
    user = await world.actor()
    asset_id = await _asset(world, user)
    broker_id = await _broker(user)
    d1, d2, d3 = date(2026, 3, 1), date(2026, 3, 2), date(2026, 3, 3)
    t_d2 = await _tx(user, broker_id, asset_id, "DIVIDEND", d2)
    t_d3_first = await _tx(user, broker_id, asset_id, "DIVIDEND", d3)
    t_d1 = await _tx(user, broker_id, asset_id, "DIVIDEND", d1)
    t_d3_second = await _tx(user, broker_id, asset_id, "INTEREST", d3)
    mine = [t_d2, t_d3_first, t_d1, t_d3_second]

    order = [item["transaction_id"] for item in await _reconciliation(user) if item["transaction_id"] in mine]

    assert order == [t_d3_second, t_d3_first, t_d2, t_d1], f"expected date desc then id desc, got {order}"
    print_success("newest first, ties by id desc")


@pytest.mark.asyncio
async def test_the_endpoint_writes_nothing_and_never_links_by_itself(world):
    """A ``unique`` row stays unlinked after the call, however often it is made: the transaction (every field, ``updated_at``
    included), the event, and the next answer are as before."""
    print_section("Reconciliation: read-only")
    user = await world.actor()
    asset_id = await _asset(world, user)
    broker_id = await _broker(user)
    day = date(2026, 2, 11)
    event_id = await _event(user, asset_id, day, "DIVIDEND")
    tx_id = await _tx(user, broker_id, asset_id, "DIVIDEND", day)
    row_before = (await _tx_rows(user, [tx_id]))[tx_id]

    first = _mine(await _reconciliation(user), [tx_id])
    second = _mine(await _reconciliation(user), [tx_id])

    assert first[tx_id]["status"] == "unique" and _candidate_ids(first[tx_id]) == [event_id], first
    assert first == second, "the same question, the same answer"
    assert (await _tx_rows(user, [tx_id]))[tx_id] == row_before, "the transaction is untouched: no automatic linking"
    linked = await user.client.get(f"{API_BASE}/transactions", params={"asset_event_id": event_id}, timeout=TIMEOUT)
    assert linked.status_code == 200 and linked.json() == [], f"nothing is linked to the event: {linked.text}"
    print_success("read-only, no automatic link")


@pytest.mark.asyncio
async def test_link_flow_end_to_end(world):
    """List -> take the unique candidate -> link it with the existing batch update -> the row no longer appears, and
    ``GET /transactions?asset_event_id=`` finds it. A ``none`` row and a ``several`` row stay in the list."""
    print_section("Reconciliation: link flow")
    user = await world.actor()
    asset_id = await _asset(world, user)
    broker_id = await _broker(user)
    day = date(2026, 2, 12)
    event_id = await _event(user, asset_id, day, "DIVIDEND")
    await _event(user, asset_id, day, "SPLIT")
    await _event(user, asset_id, day, "PRICE_ADJUSTMENT")
    unique_tx = await _tx(user, broker_id, asset_id, "DIVIDEND", day)
    none_tx = await _tx(user, broker_id, asset_id, "INTEREST", day)
    several_tx = await _tx(user, broker_id, asset_id, "ADJUSTMENT", day)
    mine = [unique_tx, none_tx, several_tx]
    listed = _mine(await _reconciliation(user), mine)
    assert {tx: listed[tx]["status"] for tx in mine} == {unique_tx: "unique", none_tx: "none", several_tx: "several"}, listed

    candidate = listed[unique_tx]["candidates"][0]
    commit = await user.client.post(f"{API_BASE}/transactions/commit", json={"updates": [{"id": unique_tx, "asset_event_id": candidate["id"]}]}, timeout=TIMEOUT)
    assert commit.status_code == 200 and commit.json()["committed"] is True, commit.text

    after = _mine(await _reconciliation(user), mine)
    assert set(after) == {none_tx, several_tx}, f"the linked row leaves the list, the others stay: {sorted(after)}"
    assert (await _tx_rows(user, [unique_tx]))[unique_tx]["asset_event_id"] == event_id
    found = await user.client.get(f"{API_BASE}/transactions", params={"asset_event_id": event_id}, timeout=TIMEOUT)
    assert found.status_code == 200, found.text
    assert [tx["id"] for tx in found.json()] == [unique_tx], f"the reverse lookup finds the linked transaction: {found.text}"
    print_success("listed, linked through commit/updates, gone from the list, found by the reverse lookup")


@pytest.mark.asyncio
async def test_requires_authentication(test_server):
    """No session cookie -> 401, as every transactions endpoint."""
    async with httpx.AsyncClient() as anonymous:
        resp = await anonymous.get(ENDPOINT, timeout=TIMEOUT)
    assert resp.status_code == 401, f"expected 401, got {resp.status_code}: {resp.text}. Red today: the route does not exist (404 or 405, or 422 if it meets a path parameter)"
    print_success("401 without authentication")

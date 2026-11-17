"""
Test Suite: reading and forgetting the asset profile through the routes (project 68, lot D1): ``/assets/profile``.

1. ``GET /assets/profile/catalogue``: ``{"voices": [...]}``, every voice of ``catalogue.CATALOGUE`` once, in its order,
   each with every field of ``FAProfileVoice`` as the catalogue holds it.
2. ``POST /assets/profile/query`` (body: a JSON list of items ``{asset_id, keys?, date_range, changes?}``): one result per
   item, in request order, under an ``as_of`` (aware UTC, the server's time before the read).
   - ``voices``: per voice, the steps ``{date, through, value, source, update_id}`` in ``date_range`` (two days, one day
     with ``end`` absent, or ``start: "min"``); ``keys`` restricts, absent is every voice with rows; an asset with no
     rows, or that does not exist, answers ``voices: {}``.
   - ``changes``: absent → ``null``; ``{}`` → the «Ultime variazioni» panel (a volatile voice shows only its ``user``
     rows and the first source row after one; the others every row); ``{"key": k}`` → every row of ``k``, volatile too.
     Newest first in (``read_on``, ``id``) order, each with ``previous``/``has_previous``; never filtered by
     ``date_range``.
   - A voice the catalogue does not list, in ``keys`` or in ``changes.key``: 422, ``detail`` ``{error_code:
     PROFILE_VOICE_UNKNOWN, message, voice}``. More than ``MAX_BULK_ITEMS`` items: 422 ``bulk_too_many_items``.
3. ``DELETE /assets/profile`` (body: ``[{asset_id, update_ids, as_of}]``): all or nothing over the whole request. An id
   that is not a row of that asset → 404 ``PROFILE_UPDATES_NOT_FOUND``; a row created after ``as_of`` → 409
   ``PROFILE_UPDATES_NEWER``; ``detail`` ``{error_code, message, asset_id, update_ids}``; nothing deleted from any item.
   ``as_of`` missing → 422. Success: 200, ``results[].deleted_count`` and ``total_deleted``; the steps follow from the
   rows left. Every refusal is followed by the same ids in a valid request: deleted then, so «nothing deleted» is never
   the answer of a route that deletes nothing.

Every test registers its own user and creates its own assets under unique names. Rows are seeded straight on the lane
database through the ``AssetProfileUpdate`` model (``PATCH /assets`` always writes today, and two steps need two days),
with chosen ``read_on`` and a fixed past ``created_at``; a row «newer» than an ``as_of`` takes ``as_of`` + 1 ms from the
server's answer, never the local clock. No enricher is bound: a route that binds one starts a background read. Each
seeding is read back from the lane database before the first route is called (a barrier, green while the routes are
missing), and every route answer is asserted on its status before its body.

Red until D1: the three routes do not exist (404/405), and each test fails on that status assertion.

Not pinned (open in the contract): ``changes`` for an asset that does not exist; which item's refusal is answered when
several items are refused; 404 against 409 when one item has both; ``date_range`` absent.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.db.models import AssetProfileUpdate
from backend.app.db.session import get_async_engine
from backend.app.services.assets.profile.catalogue import CATALOGUE, normalize_value
from backend.app.services.assets.profile.store import CHANGES_PAGE_SIZE
from backend.app.utils.date_range_limits import MAX_BULK_ITEMS
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success, unique_id

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
PROFILE = f"{API_BASE}/assets/profile"
TIMEOUT = 30.0

D = date.fromisoformat
SOURCE = "justetf"
USER = "user"
PROFILE_VOICE_UNKNOWN = "PROFILE_VOICE_UNKNOWN"
PROFILE_UPDATES_NOT_FOUND = "PROFILE_UPDATES_NOT_FOUND"
PROFILE_UPDATES_NEWER = "PROFILE_UPDATES_NEWER"
UNKNOWN_VOICE = "not_a_profile_voice"
#: Before every ``as_of`` a test can receive: the seeded rows are older than any page that reads them.
SEEDED_AT = datetime(2026, 1, 1, tzinfo=UTC)
#: How much later than an ``as_of`` a «newer» row is created: short, so a fresh ``as_of`` passes it at once.
NEWER_BY = timedelta(milliseconds=1)
#: How long a fresh ``as_of`` may take to pass a moment, in seconds (a bound, never a wait).
AS_OF_DEADLINE = 5.0
POLL_INTERVAL = 0.05
#: How far the server's clock and the test's may disagree, in seconds (same machine: a bound, never a wait).
CLOCK_TOLERANCE = timedelta(seconds=5)

#: Two readings of a TER (0.22 %, then 0.19 %) and the range that holds both.
TER_A, TER_B = "0.0022", "0.0019"
TER_A_DAY, TER_B_DAY = D("2026-03-02"), D("2026-04-01")
RANGE_START, RANGE_END = D("2026-02-01"), D("2026-06-30")
#: A gross yield read five times; the third one written by hand (volatile voice: the panel's filter).
YIELD_ROWS = [
    ("0.031", SOURCE, D("2026-03-03")),
    ("0.032", SOURCE, D("2026-03-10")),
    ("0.035", USER, D("2026-03-17")),
    ("0.033", SOURCE, D("2026-03-24")),
    ("0.034", SOURCE, D("2026-03-31")),
]


@pytest.fixture(scope="module")
def test_server():
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


# =============================================================================
# HELPERS
# =============================================================================


def _stored(key: str, value: Any) -> Any:
    """The value as the store answers it: the catalogue's stored form."""
    return normalize_value(key, value)


async def _login(client: httpx.AsyncClient) -> int:
    """A fresh user, logged in on ``client``: its id."""
    username = f"prq_{uuid.uuid4().hex[:12]}"
    password = "TestPass123!"
    resp = await client.post(f"{API_BASE}/auth/register", json={"username": username, "email": f"{username}@test.com", "password": password}, timeout=TIMEOUT)
    assert resp.status_code == 201, f"register: {resp.status_code} {resp.text}"
    login = await client.post(f"{API_BASE}/auth/login", json={"username": username, "password": password}, timeout=TIMEOUT)
    assert login.status_code == 200, f"login: {login.status_code} {login.text}"
    if login.cookies.get("session"):
        client.cookies.set("session", login.cookies.get("session"))
    me = await client.get(f"{API_BASE}/auth/me", timeout=TIMEOUT)
    assert me.status_code == 200, f"GET /auth/me: {me.status_code} {me.text}"
    return int(me.json()["user"]["id"])


async def _create(client: httpx.AsyncClient, tag: str) -> int:
    """An ETF of the test, unique name, no enricher bound (no background read)."""
    item = {"display_name": f"Profile query {unique_id(tag)}", "currency": "EUR", "asset_type": "ETF"}
    resp = await client.post(f"{API_BASE}/assets", json=[item], timeout=TIMEOUT)
    assert resp.status_code == 201, f"POST /assets: {resp.status_code} {resp.text}"
    result = resp.json()["results"][0]
    assert result["success"] and result["asset_id"] is not None, f"the asset must be created: {result}"
    return int(result["asset_id"])


async def _delete_assets(client: httpx.AsyncClient, asset_ids: list[int]) -> None:
    """The test's assets, and with them their profile rows (``CASCADE``)."""
    if asset_ids:
        await client.delete(f"{API_BASE}/assets", params={"asset_ids": asset_ids}, timeout=TIMEOUT)


async def _seed(asset_id: int, key: str, value: Any, source: str, read_on: date, *, user_id: int | None = None, created_at: datetime = SEEDED_AT) -> int:
    """One profile row straight on the lane database, its value in stored form as JSON text: its id."""
    stored = None if value is None else json.dumps(_stored(key, value), separators=(",", ":"))
    async with AsyncSession(get_async_engine()) as session:
        record = AssetProfileUpdate(asset_id=asset_id, key=key, value=stored, source=source, user_id=user_id, read_on=read_on, created_at=created_at)
        session.add(record)
        await session.commit()
        await session.refresh(record)
        return int(record.id)


async def _row_ids(asset_id: int) -> set[int]:
    """The ids of the asset's profile rows on the lane database."""
    async with AsyncSession(get_async_engine()) as session:
        result = await session.execute(text("SELECT id FROM asset_profile_updates WHERE asset_id = :asset"), {"asset": asset_id})
        return {int(row[0]) for row in result}


async def _assert_seeded(asset_id: int, ids: list[int]) -> None:
    """Barrier: the rows seeded are on the lane database (green while the routes are missing)."""
    assert set(ids) <= await _row_ids(asset_id), f"seeding: rows {ids} of asset {asset_id} must be on the lane database"


async def _seed_ter(asset_id: int) -> tuple[int, int]:
    """Two TER readings on two days: the ids, oldest first."""
    first = await _seed(asset_id, "ter", TER_A, SOURCE, TER_A_DAY)
    second = await _seed(asset_id, "ter", TER_B, SOURCE, TER_B_DAY)
    await _assert_seeded(asset_id, [first, second])
    return first, second


async def _seed_yield(asset_id: int, user_id: int) -> list[int]:
    """``YIELD_ROWS`` on ``asset_id`` (the ``user`` row by ``user_id``): the ids, in order."""
    ids = [await _seed(asset_id, "yield_gross", value, source, day, user_id=user_id if source == USER else None) for value, source, day in YIELD_ROWS]
    await _assert_seeded(asset_id, ids)
    return ids


def _span(start: date | str, end: date | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"start": start if isinstance(start, str) else start.isoformat()}
    if end is not None:
        body["end"] = end.isoformat()
    return body


def _ask(asset_id: int, date_range: dict[str, Any] | None = None, **fields: Any) -> dict[str, Any]:
    return {"asset_id": asset_id, "date_range": date_range or _span(RANGE_START, RANGE_END), **fields}


async def _query_raw(client: httpx.AsyncClient, items: list[dict[str, Any]]) -> httpx.Response:
    return await client.post(f"{PROFILE}/query", json=items, timeout=TIMEOUT)


async def _query(client: httpx.AsyncClient, items: list[dict[str, Any]]) -> dict[str, Any]:
    """``POST /assets/profile/query``: the body, after its status and one result per item in order."""
    resp = await _query_raw(client, items)
    assert resp.status_code == 200, f"POST /assets/profile/query: {resp.status_code} {resp.text}"
    body = resp.json()
    assert [result["asset_id"] for result in body["items"]] == [item["asset_id"] for item in items], f"one result per item, in order: {body}"
    return body


async def _query_one(client: httpx.AsyncClient, item: dict[str, Any]) -> dict[str, Any]:
    return (await _query(client, [item]))["items"][0]


async def _as_of(client: httpx.AsyncClient, asset_id: int) -> str:
    """A fresh ``as_of``, as the server answers it."""
    return (await _query(client, [_ask(asset_id)]))["as_of"]


async def _forget(client: httpx.AsyncClient, items: list[dict[str, Any]]) -> httpx.Response:
    return await client.request("DELETE", PROFILE, json=items, timeout=TIMEOUT)


def _steps(voice: list[dict[str, Any]]) -> list[tuple[str, str, Any, str, int]]:
    return [(step["date"], step["through"], step["value"], step["source"], step["update_id"]) for step in voice]


def _error(resp: httpx.Response, status: int, error_code: str) -> dict[str, Any]:
    """The refusal's ``detail``, after its status, its shape and its code."""
    assert resp.status_code == status, f"expected {status} {error_code}: {resp.status_code} {resp.text}"
    detail = resp.json().get("detail")
    assert isinstance(detail, dict), f"detail is an object: {resp.text}"
    assert detail.get("error_code") == error_code, f"error_code {error_code}: {detail}"
    return detail


async def _as_of_after(client: httpx.AsyncClient, asset_id: int, moment: datetime) -> str:
    """A fresh ``as_of`` later than ``moment``: the server is asked again until its clock passes it, or the deadline."""
    deadline = time.monotonic() + AS_OF_DEADLINE
    while True:
        as_of = await _as_of(client, asset_id)
        if datetime.fromisoformat(as_of) > moment or time.monotonic() >= deadline:
            return as_of
        await asyncio.sleep(POLL_INTERVAL)


def _just_after(as_of: str) -> datetime:
    """A ``created_at`` the page that read at ``as_of`` has not seen."""
    return datetime.fromisoformat(as_of) + NEWER_BY


async def _assert_deleted_now(client: httpx.AsyncClient, asset_id: int, update_ids: list[int], *, seen_after: datetime = SEEDED_AT) -> None:
    """Positive barrier after a refusal: the same ids, under a fresh ``as_of`` past ``seen_after`` (the newest
    ``created_at`` among them), are deleted."""
    resp = await _forget(client, [{"asset_id": asset_id, "update_ids": update_ids, "as_of": await _as_of_after(client, asset_id, seen_after)}])
    assert resp.status_code == 200, f"DELETE /assets/profile (valid): {resp.status_code} {resp.text}"
    assert not set(update_ids) & await _row_ids(asset_id), f"rows {update_ids} deleted by a valid request"


def _changes(page: dict[str, Any]) -> list[tuple[int, str, Any, Any, bool, str]]:
    return [(change["id"], change["key"], change["value"], change["previous"], change["has_previous"], change["source"]) for change in page["items"]]


# =============================================================================
# 1. GET /assets/profile/catalogue
# =============================================================================


@pytest.mark.asyncio
async def test_catalogue_answers_every_voice_once_in_order(test_server):
    print_section("D1: GET /assets/profile/catalogue")
    async with httpx.AsyncClient() as client:
        await _login(client)
        resp = await client.get(f"{PROFILE}/catalogue", timeout=TIMEOUT)

    assert resp.status_code == 200, f"GET /assets/profile/catalogue: {resp.status_code} {resp.text}"
    voices = resp.json()["voices"]
    assert [voice["key"] for voice in voices] == list(CATALOGUE), "every voice of the catalogue once, in its order"
    for voice in voices:
        assert voice == CATALOGUE[voice["key"]].model_dump(mode="json"), f"{voice['key']}: every field as the catalogue holds it"
    print_success("the catalogue, in order")


# =============================================================================
# 2. POST /assets/profile/query — the steps
# =============================================================================


@pytest.mark.asyncio
async def test_two_reads_on_two_days_are_two_steps(test_server):
    print_section("D1: POST /assets/profile/query")
    async with httpx.AsyncClient() as client:
        await _login(client)
        asset_id = await _create(client, "STEPS")
        try:
            first, second = await _seed_ter(asset_id)

            result = await _query_one(client, _ask(asset_id, keys=["ter"]))

            assert _steps(result["voices"]["ter"]) == [
                (TER_A_DAY.isoformat(), (TER_B_DAY - timedelta(days=1)).isoformat(), _stored("ter", TER_A), SOURCE, first),
                (TER_B_DAY.isoformat(), RANGE_END.isoformat(), _stored("ter", TER_B), SOURCE, second),
            ], result
            assert result["changes"] is None, f"no changes asked: none answered: {result}"
            print_success("two steps, date … through, value, source, update_id")
        finally:
            await _delete_assets(client, [asset_id])


@pytest.mark.asyncio
async def test_start_min_begins_at_the_first_row_and_answers_nothing_without_rows(test_server):
    async with httpx.AsyncClient() as client:
        await _login(client)
        asset_id = await _create(client, "MIN")
        empty_id = await _create(client, "MIN_EMPTY")
        try:
            first, second = await _seed_ter(asset_id)
            await _assert_seeded(empty_id, [])
            from_min = _span("min", RANGE_END)

            body = await _query(client, [_ask(asset_id, from_min), _ask(empty_id, from_min)])

            with_rows, without_rows = body["items"]
            assert [(step["date"], step["update_id"]) for step in with_rows["voices"]["ter"]] == [(TER_A_DAY.isoformat(), first), (TER_B_DAY.isoformat(), second)], with_rows
            assert with_rows["voices"]["ter"][-1]["through"] == RANGE_END.isoformat(), with_rows
            assert without_rows["voices"] == {}, f"min on an asset without rows: no voice: {without_rows}"
        finally:
            await _delete_assets(client, [asset_id, empty_id])


@pytest.mark.asyncio
async def test_a_range_without_end_is_one_point_per_voice(test_server):
    async with httpx.AsyncClient() as client:
        user_id = await _login(client)
        asset_id = await _create(client, "ONE_DAY")
        try:
            first, _ = await _seed_ter(asset_id)
            yields = await _seed_yield(asset_id, user_id)
            day = D("2026-03-20")  # after the third yield (17/03), before the second TER (01/04)

            result = await _query_one(client, _ask(asset_id, _span(day)))

            assert {key: _steps(voice) for key, voice in result["voices"].items()} == {
                "ter": [(day.isoformat(), day.isoformat(), _stored("ter", TER_A), SOURCE, first)],
                "yield_gross": [(day.isoformat(), day.isoformat(), _stored("yield_gross", "0.035"), USER, yields[2])],
            }, result
        finally:
            await _delete_assets(client, [asset_id])


@pytest.mark.asyncio
async def test_without_keys_every_voice_with_rows_and_keys_restricts(test_server):
    async with httpx.AsyncClient() as client:
        user_id = await _login(client)
        asset_id = await _create(client, "KEYS")
        try:
            await _seed_ter(asset_id)
            await _seed_yield(asset_id, user_id)

            every = await _query_one(client, _ask(asset_id))
            only_ter = await _query_one(client, _ask(asset_id, keys=["ter"]))

            assert set(every["voices"]) == {"ter", "yield_gross"}, f"without keys: every voice with rows: {sorted(every['voices'])}"
            assert set(only_ter["voices"]) == {"ter"}, f"keys restricts: {sorted(only_ter['voices'])}"
            assert only_ter["voices"]["ter"] == every["voices"]["ter"], "the same steps either way"
        finally:
            await _delete_assets(client, [asset_id])


@pytest.mark.asyncio
async def test_results_follow_the_request_order_and_a_missing_asset_answers_no_voice(test_server):
    async with httpx.AsyncClient() as client:
        await _login(client)
        asset_id = await _create(client, "ORDER")
        missing = 2_000_000_000 + int(uuid.uuid4().int % 1_000_000)
        try:
            await _seed_ter(asset_id)

            body = await _query(client, [_ask(missing), _ask(asset_id)])

            assert body["items"][0]["voices"] == {}, f"an asset that does not exist: no voice, not an error: {body['items'][0]}"
            assert set(body["items"][1]["voices"]) == {"ter"}, body["items"][1]
        finally:
            await _delete_assets(client, [asset_id])


@pytest.mark.asyncio
async def test_query_answers_an_aware_as_of_taken_now(test_server):
    async with httpx.AsyncClient() as client:
        await _login(client)
        asset_id = await _create(client, "AS_OF")
        try:
            before = datetime.now(UTC)
            as_of = datetime.fromisoformat(await _as_of(client, asset_id))
            after = datetime.now(UTC)

            assert as_of.tzinfo is not None and as_of.utcoffset() == timedelta(0), f"as_of is aware UTC: {as_of}"
            assert before - CLOCK_TOLERANCE <= as_of <= after + CLOCK_TOLERANCE, f"as_of is the server's time of the read: {as_of} not in [{before}, {after}]"
        finally:
            await _delete_assets(client, [asset_id])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "where",
    [pytest.param("keys", id="in-keys"), pytest.param("changes", id="in-changes-key")],
)
async def test_an_unknown_voice_is_refused_before_any_read(test_server, where):
    async with httpx.AsyncClient() as client:
        await _login(client)
        asset_id = await _create(client, "UNKNOWN")
        try:
            item = _ask(asset_id, keys=["ter", UNKNOWN_VOICE]) if where == "keys" else _ask(asset_id, changes={"key": UNKNOWN_VOICE})

            resp = await _query_raw(client, [item])

            detail = _error(resp, 422, PROFILE_VOICE_UNKNOWN)
            assert detail.get("voice") == UNKNOWN_VOICE and UNKNOWN_VOICE in str(detail.get("message")), f"the voice named: {detail}"
        finally:
            await _delete_assets(client, [asset_id])


@pytest.mark.asyncio
async def test_more_than_the_bulk_limit_of_items_is_refused(test_server):
    async with httpx.AsyncClient() as client:
        await _login(client)
        asset_id = await _create(client, "BULK")
        try:
            resp = await _query_raw(client, [_ask(asset_id)] * (MAX_BULK_ITEMS + 1))

            assert resp.status_code == 422, f"{MAX_BULK_ITEMS + 1} items: {resp.status_code} {resp.text[:500]}"
            detail = resp.json().get("detail")
            assert isinstance(detail, dict) and detail.get("code") == "bulk_too_many_items", f"bulk_too_many_items: {detail}"
        finally:
            await _delete_assets(client, [asset_id])


# =============================================================================
# 3. POST /assets/profile/query — the changes
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("changes", [pytest.param({}, id="empty"), pytest.param({"page": 0}, id="page-0")])
async def test_the_panel_keeps_of_a_volatile_voice_the_user_row_and_the_source_row_after_it(test_server, changes):
    print_section("D1: changes, the «Ultime variazioni» panel")
    async with httpx.AsyncClient() as client:
        user_id = await _login(client)
        asset_id = await _create(client, "PANEL")
        try:
            ter_first, ter_second = await _seed_ter(asset_id)
            yields = await _seed_yield(asset_id, user_id)
            y = [_stored("yield_gross", value) for value, _, _ in YIELD_ROWS]

            result = await _query_one(client, _ask(asset_id, changes=changes))

            page = result["changes"]
            assert page is not None, f"changes asked: a page answered: {result}"
            # Newest first in (read_on, id): TER 01/04, yield 24/03 (the source after the user's), yield 17/03 (the user's), TER 02/03
            assert _changes(page) == [
                (ter_second, "ter", _stored("ter", TER_B), _stored("ter", TER_A), True, SOURCE),
                (yields[3], "yield_gross", y[3], y[2], True, SOURCE),
                (yields[2], "yield_gross", y[2], y[1], True, USER),
                (ter_first, "ter", _stored("ter", TER_A), None, False, SOURCE),
            ], page
            assert (page["total"], page["page"], page["page_size"]) == (4, 0, CHANGES_PAGE_SIZE), page
            user_row = next(change for change in page["items"] if change["id"] == yields[2])
            assert (user_row["user_id"], user_row["read_on"]) == (user_id, YIELD_ROWS[2][2].isoformat()), f"the user row keeps its author: {user_row}"
            print_success("volatile voice: the user's row and the source's after it; the others all")
        finally:
            await _delete_assets(client, [asset_id])


@pytest.mark.asyncio
async def test_changes_of_one_voice_list_every_row_even_volatile(test_server):
    async with httpx.AsyncClient() as client:
        user_id = await _login(client)
        asset_id = await _create(client, "ONE_VOICE")
        try:
            await _seed_ter(asset_id)
            yields = await _seed_yield(asset_id, user_id)
            y = [_stored("yield_gross", value) for value, _, _ in YIELD_ROWS]

            page = (await _query_one(client, _ask(asset_id, changes={"key": "yield_gross"})))["changes"]

            assert page is not None and page["total"] == len(yields), f"every row of the voice: {page}"
            assert [(change["id"], change["value"], change["previous"], change["has_previous"]) for change in page["items"]] == [
                (yields[4], y[4], y[3], True),
                (yields[3], y[3], y[2], True),
                (yields[2], y[2], y[1], True),
                (yields[1], y[1], y[0], True),
                (yields[0], y[0], None, False),
            ], page
            assert {change["key"] for change in page["items"]} == {"yield_gross"}, "only the voice asked"
        finally:
            await _delete_assets(client, [asset_id])


@pytest.mark.asyncio
async def test_changes_are_not_filtered_by_the_date_range(test_server):
    async with httpx.AsyncClient() as client:
        await _login(client)
        asset_id = await _create(client, "NOT_FILTERED")
        try:
            first, second = await _seed_ter(asset_id)
            before_second = TER_B_DAY - timedelta(days=1)

            result = await _query_one(client, _ask(asset_id, _span(TER_A_DAY, before_second), keys=["ter"], changes={}))

            assert [step["update_id"] for step in result["voices"]["ter"]] == [first], f"the range ends before the second row: {result['voices']}"
            assert result["changes"] is not None and [change["id"] for change in result["changes"]["items"]] == [second, first], f"the changes list the row outside the range too: {result['changes']}"
        finally:
            await _delete_assets(client, [asset_id])


# =============================================================================
# 4. DELETE /assets/profile
# =============================================================================


@pytest.mark.asyncio
async def test_forget_the_last_row_and_the_previous_value_holds_again(test_server):
    print_section("D1: DELETE /assets/profile")
    async with httpx.AsyncClient() as client:
        await _login(client)
        asset_id = await _create(client, "FORGET")
        try:
            first, second = await _seed_ter(asset_id)
            as_of = await _as_of(client, asset_id)

            resp = await _forget(client, [{"asset_id": asset_id, "update_ids": [second], "as_of": as_of}])

            assert resp.status_code == 200, f"DELETE /assets/profile: {resp.status_code} {resp.text}"
            body = resp.json()
            assert [(result["asset_id"], result["deleted_count"]) for result in body["results"]] == [(asset_id, 1)] and body["total_deleted"] == 1, body
            assert await _row_ids(asset_id) == {first}, "only the row forgotten is gone"
            result = await _query_one(client, _ask(asset_id, keys=["ter"]))
            assert _steps(result["voices"]["ter"]) == [(TER_A_DAY.isoformat(), RANGE_END.isoformat(), _stored("ter", TER_A), SOURCE, first)], f"the previous value holds again: {result}"
            print_success("forgotten: the previous value is now again")
        finally:
            await _delete_assets(client, [asset_id])


@pytest.mark.asyncio
async def test_forget_a_row_of_another_asset_is_not_found_and_deletes_nothing(test_server):
    async with httpx.AsyncClient() as client:
        await _login(client)
        asset_id = await _create(client, "NOT_FOUND")
        other_id = await _create(client, "NOT_FOUND_OTHER")
        try:
            mine, _ = await _seed_ter(asset_id)
            others, _ = await _seed_ter(other_id)
            rows_before = await _row_ids(asset_id), await _row_ids(other_id)
            as_of = await _as_of(client, asset_id)

            resp = await _forget(client, [{"asset_id": asset_id, "update_ids": [mine, others], "as_of": as_of}])

            detail = _error(resp, 404, PROFILE_UPDATES_NOT_FOUND)
            assert (detail.get("asset_id"), detail.get("update_ids")) == (asset_id, [others]), f"the asset and the ids not its own: {detail}"
            assert (await _row_ids(asset_id), await _row_ids(other_id)) == rows_before, "nothing deleted, from either asset"
            await _assert_deleted_now(client, asset_id, [mine])
        finally:
            await _delete_assets(client, [asset_id, other_id])


@pytest.mark.asyncio
async def test_forget_a_row_written_after_as_of_is_refused_and_kept(test_server):
    async with httpx.AsyncClient() as client:
        await _login(client)
        asset_id = await _create(client, "NEWER")
        try:
            first, _ = await _seed_ter(asset_id)
            as_of = await _as_of(client, asset_id)
            newer = await _seed(asset_id, "ter", "0.0025", SOURCE, D("2026-05-04"), created_at=_just_after(as_of))
            await _assert_seeded(asset_id, [newer])

            resp = await _forget(client, [{"asset_id": asset_id, "update_ids": [first, newer], "as_of": as_of}])

            detail = _error(resp, 409, PROFILE_UPDATES_NEWER)
            assert (detail.get("asset_id"), detail.get("update_ids")) == (asset_id, [newer]), f"the asset and the rows the page had not seen: {detail}"
            assert {first, newer} <= await _row_ids(asset_id), "nothing deleted: the row seen and the newer one are still there"
            await _assert_deleted_now(client, asset_id, [first, newer], seen_after=_just_after(as_of))
        finally:
            await _delete_assets(client, [asset_id])


@pytest.mark.asyncio
@pytest.mark.parametrize("refusal", [pytest.param("not_found", id="second-not-found"), pytest.param("newer", id="second-newer")])
async def test_one_refused_item_deletes_nothing_from_the_others(test_server, refusal):
    async with httpx.AsyncClient() as client:
        await _login(client)
        kept_id = await _create(client, "ATOMIC_KEPT")
        refused_id = await _create(client, "ATOMIC_REFUSED")
        try:
            _, kept_row = await _seed_ter(kept_id)
            refused_row, _ = await _seed_ter(refused_id)
            as_of = await _as_of(client, kept_id)
            if refusal == "newer":
                bad = await _seed(refused_id, "ter", "0.0025", SOURCE, D("2026-05-04"), created_at=_just_after(as_of))
                await _assert_seeded(refused_id, [bad])
                second = {"asset_id": refused_id, "update_ids": [refused_row, bad], "as_of": as_of}
                status, code = 409, PROFILE_UPDATES_NEWER
            else:
                second = {"asset_id": refused_id, "update_ids": [refused_row, kept_row], "as_of": as_of}
                status, code = 404, PROFILE_UPDATES_NOT_FOUND
            rows_before = await _row_ids(kept_id), await _row_ids(refused_id)

            resp = await _forget(client, [{"asset_id": kept_id, "update_ids": [kept_row], "as_of": as_of}, second])

            detail = _error(resp, status, code)
            assert detail.get("asset_id") == refused_id, f"the refused item named: {detail}"
            assert (await _row_ids(kept_id), await _row_ids(refused_id)) == rows_before, "all or nothing over the request: the first item's row is still there"
            await _assert_deleted_now(client, kept_id, [kept_row])
        finally:
            await _delete_assets(client, [kept_id, refused_id])


@pytest.mark.asyncio
async def test_forget_without_as_of_is_refused(test_server):
    async with httpx.AsyncClient() as client:
        await _login(client)
        asset_id = await _create(client, "NO_AS_OF")
        try:
            first, _ = await _seed_ter(asset_id)
            # Barrier: the route exists and takes this body with as_of (a missing route answers 404/405, never this 200)
            other = await _seed(asset_id, "ter", "0.0025", SOURCE, D("2026-05-04"))
            ok = await _forget(client, [{"asset_id": asset_id, "update_ids": [other], "as_of": await _as_of(client, asset_id)}])
            assert ok.status_code == 200, f"barrier, DELETE /assets/profile with as_of: {ok.status_code} {ok.text}"

            resp = await _forget(client, [{"asset_id": asset_id, "update_ids": [first]}])

            assert resp.status_code == 422, f"as_of is required: {resp.status_code} {resp.text}"
            assert first in await _row_ids(asset_id), "nothing deleted"
        finally:
            await _delete_assets(client, [asset_id])

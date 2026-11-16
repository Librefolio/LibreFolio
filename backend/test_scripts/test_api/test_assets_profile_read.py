"""
Test Suite: reading the profile from the enrichers through the routes (project 68, lot B5a): ``/assets/profile``.

1. ``POST /assets/profile/ask`` (writes nothing). With ``asset_type`` and ``enrichers`` (``mockenrich``, a unique ISIN):
   the merged voices — ``ter`` ``"0.0022"`` from mockenrich with its ``source_date``, ``geography`` in stored form,
   ``distribution_policy``, the plugin's own ``description`` — and one ``ok`` outcome naming the voices it gave. With the
   ``asset_id`` of an asset bound to mockenrich: the same, and the asset's profile rows and enrichers' state unchanged.
   ``keys`` restricts the voices. 422 without ``asset_id`` and without ``asset_type`` + ``enrichers``, and with both
   ``asset_id`` and ``enrichers``.
2. ``POST /assets/profile/refresh`` (body: a JSON list of asset ids): the voices written as ``mockenrich`` rows with no
   user; ``GET /assets`` answers ``enrichers.state.mockenrich.status == "ok"``; a second refresh writes nothing new; an
   asset id that does not exist has a result with ``error``; an asset bound to ``MOCK_RATE_LIMITED`` has an outcome
   ``error`` with ``RATE_LIMITED`` and its ``retry_after``.

3. B5b, the background «Aggiorna»: after ``POST /assets`` with non-empty ``enrichers`` (each item created) and after a
   committed ``PATCH /assets`` whose item sets non-empty ``enrichers``, the server reads them after the answer: within
   ``BACKGROUND_DEADLINE`` ``GET /assets`` answers ``state.mockenrich.status == "ok"`` and the database holds the
   mockenrich rows, no user. Never after ``POST /assets/validate``, a refused batch, or a PATCH that does not set
   ``enrichers``: those assets, bound beforehand, keep ``state == {}`` and no row after a marker — a later POST whose
   own background read is awaited to ``ok``.
4. B5b, ``{"from": "mockenrich", "seen": …}`` in ``profile`` through the routes: ``/validate`` answers the warning
   ``profileSourceChanged`` (``params`` ``{voice, seen, now}`` in stored form) and writes nothing; ``PATCH`` answers the
   same, committed, and writes the row in mockenrich's name, no user, mockenrich's ``source_date``. (The resolution's
   rules are pinned in ``test_services/test_asset_profile_from.py``.)

Every test registers its own user and creates its own assets under unique names, bound to an ISIN no other test uses:
the backend's read cache is shared by every test of the lane and lives 30 minutes, so no assertion depends on what it
holds — ``from_cache`` is asserted only on a first read of a fresh ISIN. The rows of the database are read for the
test's own assets only. ``_create_bound`` binds straight on the lane's database (``bindings.save_config``), never through
a route: a route that sets ``enrichers`` starts a background read (B5b), which would race the read under test. A wait
polls ``GET /assets`` against a deadline, never a sleep in place of a condition.

Not pinned: a PATCH that sets ``enrichers`` to ``{}`` or ``null`` (nothing is left to read, so a read would leave no
trace to observe). A POST item that fails has no asset to observe: pinned only that the batch's created items are still
read, their ``config`` as sent.

Red until B5a: both routes raise ``NotImplementedError`` (500). The three 422 cases are green already (the request's
validator exists): they are guards.

Red until B5b: no background read exists (the waits reach their deadline: an assertion, never a hang); the catalogue
refuses ``{"from"}`` (``profileValueInvalid``). The tests of sections 1 and 2 stay green: their assets are bound without
a route.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.db.session import get_async_engine
from backend.app.services.assets.profile.catalogue import normalize_value
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success, unique_id

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0
MOCK_CODE = "mockenrich"
RATE_LIMITED = "RATE_LIMITED"
PROFILE_SOURCE_CHANGED = "profileSourceChanged"
#: How long the background «Aggiorna» may take to show its state, in seconds (a bound, never a wait).
BACKGROUND_DEADLINE = 15.0
POLL_INTERVAL = 0.1


@pytest.fixture(scope="module")
def test_server():
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


# =============================================================================
# HELPERS
# =============================================================================


def _mock() -> Any:
    """The test enricher's module: its fixed answers, read in the test body."""
    from backend.app.services.enricher_providers.mockenrich import plugin  # noqa: PLC0415 — the plugin's own rules, read in the test body

    return plugin


def _fake_isin() -> str:
    """An ISIN-shaped identifier no other test uses: mockenrich reads any identifier but its fixed ones."""
    return f"ZP{uuid.uuid4().hex[:10].upper()}"


def _expected_voices(isin: str) -> dict[str, Any]:
    """What mockenrich gives for ``isin``, in stored form."""
    mock = _mock()
    raw = {**mock.READ_VALUES, "description": f"Mock description of {isin}"}
    return {key: normalize_value(key, value) for key, value in raw.items()}


async def _login(client: httpx.AsyncClient) -> int:
    """A fresh user, logged in on ``client``: its id."""
    username = f"prf_{uuid.uuid4().hex[:12]}"
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


def _binding(identifier: str) -> dict[str, str]:
    return {"identifier_type": "ISIN", "identifier": identifier}


def _item(tag: str, **fields: Any) -> dict[str, Any]:
    return {"display_name": f"Profile read {unique_id(tag)}", "currency": "EUR", "asset_type": "ETF", **fields}


async def _post(client: httpx.AsyncClient, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """``POST /assets``: the result of each item, in order."""
    resp = await client.post(f"{API_BASE}/assets", json=items, timeout=TIMEOUT)
    assert resp.status_code == 201, f"POST /assets: {resp.status_code} {resp.text}"
    results = resp.json()["results"]
    assert len(results) == len(items), f"one result per item: {results}"
    return results


async def _create(client: httpx.AsyncClient, item: dict[str, Any]) -> int:
    result = (await _post(client, [item]))[0]
    assert result["success"] and result["asset_id"] is not None, f"the asset must be created: {result}"
    return int(result["asset_id"])


async def _bind(asset_id: int, identifier: str) -> None:
    """Bind the asset to mockenrich straight on the lane's database: no route, so no background read (B5b)."""
    from backend.app.services.enrichers import bindings  # noqa: PLC0415 — the service writing the bindings, imported in the test body

    async with AsyncSession(get_async_engine()) as session:
        await bindings.save_config(session, asset_id, {MOCK_CODE: _binding(identifier)})
        await session.commit()


async def _create_bound(client: httpx.AsyncClient, tag: str, identifier: str) -> int:
    """An ETF of the test, bound to mockenrich with ``identifier`` as ISIN, without a route (see the module docstring)."""
    asset_id = await _create(client, _item(tag))
    await _bind(asset_id, identifier)
    return asset_id


async def _delete(client: httpx.AsyncClient, asset_ids: list[int]) -> None:
    if asset_ids:
        await client.delete(f"{API_BASE}/assets", params={"asset_ids": asset_ids}, timeout=TIMEOUT)


async def _read_asset(client: httpx.AsyncClient, asset_id: int) -> dict[str, Any]:
    resp = await client.get(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)
    assert resp.status_code == 200, f"GET /assets: {resp.status_code} {resp.text}"
    found = [asset for asset in resp.json() if asset["asset_id"] == asset_id]
    assert len(found) == 1, f"asset {asset_id} not answered: {resp.text}"
    return found[0]


def _state_of(asset: dict[str, Any]) -> dict[str, Any]:
    return (asset.get("enrichers") or {}).get("state") or {}


async def _profile_rows(asset_id: int) -> list[dict[str, Any]]:
    """The asset's profile rows in the store's order (read_on, id), each with ``stored``: its value as the store reads it."""
    async with AsyncSession(get_async_engine()) as session:
        result = await session.execute(text("SELECT id, key, value, source, user_id, read_on, source_date FROM asset_profile_updates WHERE asset_id = :asset ORDER BY read_on, id"), {"asset": asset_id})
        rows = [dict(row._mapping) for row in result]
    for row in rows:
        row["stored"] = None if row["value"] is None else normalize_value(row["key"], json.loads(row["value"]))
    return rows


async def _ask(client: httpx.AsyncClient, body: dict[str, Any]) -> httpx.Response:
    return await client.post(f"{API_BASE}/assets/profile/ask", json=body, timeout=TIMEOUT)


async def _refresh(client: httpx.AsyncClient, asset_ids: list[int]) -> dict[int, dict[str, Any]]:
    """``POST /assets/profile/refresh``: the result of each asset, by id."""
    resp = await client.post(f"{API_BASE}/assets/profile/refresh", json=asset_ids, timeout=TIMEOUT)
    assert resp.status_code == 200, f"POST /assets/profile/refresh: {resp.status_code} {resp.text}"
    results = resp.json()["results"]
    by_id = {int(result["asset_id"]): result for result in results}
    assert len(by_id) == len(results) and set(asset_ids) <= set(by_id), f"one result per asset asked: {results}"
    return by_id


def _assert_mock_voices(body: dict[str, Any], isin: str) -> None:
    """The ask's answer is mockenrich's reading of ``isin``, merged, with one ok outcome."""
    mock = _mock()
    expected = _expected_voices(isin)
    voices = body["voices"]
    assert set(voices) == set(expected), f"every voice mockenrich gives: {sorted(voices)}"
    for key, value in expected.items():
        voice = voices[key]
        assert (voice["value"], voice["source"], voice["source_date"], voice["others"]) == (value, MOCK_CODE, mock.SOURCE_DATE.isoformat(), {}), f"{key}: {voice}"
    assert voices["ter"]["value"] == "0.0022", voices["ter"]
    outcomes = [outcome for outcome in body["outcomes"] if outcome["code"] == MOCK_CODE]
    assert len(outcomes) == 1, f"one mockenrich outcome: {body['outcomes']}"
    outcome = outcomes[0]
    assert (outcome["identifier_type"], outcome["identifier"], outcome["status"], outcome["error_code"]) == ("ISIN", isin, "ok", None), outcome
    assert set(outcome["voices"]) == set(expected), f"the voices it gave: {outcome}"


# =============================================================================
# 1. POST /assets/profile/ask
# =============================================================================


@pytest.mark.asyncio
async def test_ask_with_a_type_and_bindings_answers_the_merged_voices(test_server):
    print_section("B5a: POST /assets/profile/ask (an asset not created yet)")
    isin = _fake_isin()
    async with httpx.AsyncClient() as client:
        await _login(client)
        resp = await _ask(client, {"asset_type": "ETF", "enrichers": {MOCK_CODE: {"identifier_type": "ISIN", "identifier": isin}}})

    assert resp.status_code == 200, f"POST /assets/profile/ask: {resp.status_code} {resp.text}"
    body = resp.json()
    _assert_mock_voices(body, isin)
    assert [outcome["from_cache"] for outcome in body["outcomes"] if outcome["code"] == MOCK_CODE] == [False], f"a fresh ISIN is read now: {body['outcomes']}"
    print_success("mockenrich's voices merged, stored form")


@pytest.mark.asyncio
async def test_ask_with_an_asset_id_reads_its_bindings_and_writes_nothing(test_server):
    isin = _fake_isin()
    async with httpx.AsyncClient() as client:
        await _login(client)
        asset_id = await _create_bound(client, "ASK_ID", isin)
        try:
            rows_before = await _profile_rows(asset_id)
            state_before = _state_of(await _read_asset(client, asset_id))

            resp = await _ask(client, {"asset_id": asset_id})

            assert resp.status_code == 200, f"POST /assets/profile/ask: {resp.status_code} {resp.text}"
            _assert_mock_voices(resp.json(), isin)
            assert await _profile_rows(asset_id) == rows_before, "ask writes no profile row"
            assert _state_of(await _read_asset(client, asset_id)) == state_before, "ask writes no state"
        finally:
            await _delete(client, [asset_id])


@pytest.mark.asyncio
async def test_ask_with_keys_restricts_the_voices(test_server):
    isin = _fake_isin()
    async with httpx.AsyncClient() as client:
        await _login(client)
        resp = await _ask(client, {"asset_type": "ETF", "enrichers": {MOCK_CODE: {"identifier_type": "ISIN", "identifier": isin}}, "keys": ["ter"]})

    assert resp.status_code == 200, f"POST /assets/profile/ask: {resp.status_code} {resp.text}"
    voices = resp.json()["voices"]
    assert set(voices) == {"ter"} and voices["ter"]["value"] == "0.0022" and voices["ter"]["source"] == MOCK_CODE, f"only the voices asked: {voices}"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [
        pytest.param({}, id="nothing"),
        pytest.param({"asset_type": "ETF"}, id="type-without-enrichers"),
        pytest.param({"enrichers": {MOCK_CODE: {"identifier_type": "ISIN", "identifier": "ZP0000000000"}}}, id="enrichers-without-type"),
        pytest.param({"asset_id": 1, "enrichers": {MOCK_CODE: {"identifier_type": "ISIN", "identifier": "ZP0000000000"}}}, id="both"),
    ],
)
async def test_ask_needs_an_asset_id_or_a_type_with_enrichers_not_both(test_server, body):
    async with httpx.AsyncClient() as client:
        await _login(client)
        resp = await _ask(client, body)

    assert resp.status_code == 422, f"{body}: {resp.status_code} {resp.text}"


# =============================================================================
# 2. POST /assets/profile/refresh
# =============================================================================


@pytest.mark.asyncio
async def test_refresh_writes_the_mock_voices_and_the_state_then_nothing_new(test_server):
    print_section("B5a: POST /assets/profile/refresh")
    isin = _fake_isin()
    async with httpx.AsyncClient() as client:
        await _login(client)
        asset_id = await _create_bound(client, "REFRESH", isin)
        try:
            before = await _profile_rows(asset_id)
            expected = _expected_voices(isin)

            result = (await _refresh(client, [asset_id]))[asset_id]

            assert result["error"] is None and set(result["written"]) == set(expected), f"every voice written: {result}"
            assert [(outcome["code"], outcome["status"]) for outcome in result["outcomes"]] == [(MOCK_CODE, "ok")], result
            new_rows = [row for row in await _profile_rows(asset_id) if row["id"] not in {old["id"] for old in before}]
            assert {row["key"]: (row["stored"], row["source"], row["user_id"]) for row in new_rows} == {key: (value, MOCK_CODE, None) for key, value in expected.items()}, f"mockenrich rows, no user: {new_rows}"
            state = _state_of(await _read_asset(client, asset_id)).get(MOCK_CODE) or {}
            assert state.get("status") == "ok" and state.get("voices") == len(expected) and state.get("read_at"), f"GET /assets answers the read's state: {state}"

            again = (await _refresh(client, [asset_id]))[asset_id]

            assert again["written"] == [], f"the same values: nothing written: {again}"
            assert [row["id"] for row in await _profile_rows(asset_id)] == [row["id"] for row in before + new_rows], "no new row"
            print_success("written once, then nothing new")
        finally:
            await _delete(client, [asset_id])


@pytest.mark.asyncio
async def test_refresh_of_an_asset_that_does_not_exist_answers_an_error_for_it(test_server):
    isin = _fake_isin()
    async with httpx.AsyncClient() as client:
        await _login(client)
        asset_id = await _create_bound(client, "BESIDE_MISSING", isin)
        missing = 2_000_000_000 + int(uuid.uuid4().int % 1_000_000)
        try:
            results = await _refresh(client, [missing, asset_id])

            assert results[missing]["error"] and results[missing]["written"] == [], f"an asset that does not exist: {results[missing]}"
            assert set(results[asset_id]["written"]) == set(_expected_voices(isin)), f"the other asset is refreshed: {results[asset_id]}"
        finally:
            await _delete(client, [asset_id])


@pytest.mark.asyncio
async def test_refresh_of_an_asset_refused_for_too_many_requests(test_server):
    mock = _mock()
    async with httpx.AsyncClient() as client:
        await _login(client)
        asset_id = await _create_bound(client, "RATE", mock.RATE_LIMITED_IDENTIFIER)
        try:
            result = (await _refresh(client, [asset_id]))[asset_id]

            outcomes = [outcome for outcome in result["outcomes"] if outcome["code"] == MOCK_CODE]
            assert len(outcomes) == 1, f"one mockenrich outcome: {result}"
            assert (outcomes[0]["status"], outcomes[0]["error_code"], outcomes[0]["retry_after"]) == ("error", RATE_LIMITED, mock.RATE_LIMITED_RETRY_AFTER), outcomes[0]
            assert result["written"] == [] and await _profile_rows(asset_id) == [], f"nothing written: {result}"
            state = _state_of(await _read_asset(client, asset_id)).get(MOCK_CODE) or {}
            assert (state.get("status"), state.get("error_code")) == ("error", RATE_LIMITED), f"the refusal is in the state: {state}"
        finally:
            await _delete(client, [asset_id])


# =============================================================================
# 3. B5b: the background «Aggiorna» after a save that sets the enrichers
# =============================================================================


async def _wait_for_state(client: httpx.AsyncClient, asset_id: int) -> dict[str, Any]:
    """Poll ``GET /assets`` until the asset's ``state`` has a mockenrich entry, or the deadline: the last state seen."""
    deadline = time.monotonic() + BACKGROUND_DEADLINE
    while True:
        state = _state_of(await _read_asset(client, asset_id))
        if MOCK_CODE in state or time.monotonic() >= deadline:
            return state
        await asyncio.sleep(POLL_INTERVAL)


async def _assert_read_in_background(client: httpx.AsyncClient, asset_id: int, isin: str) -> None:
    """Within the deadline the asset's state says mockenrich read it, and its rows are mockenrich's, no user."""
    state = await _wait_for_state(client, asset_id)
    assert (state.get(MOCK_CODE) or {}).get("status") == "ok", f"within {BACKGROUND_DEADLINE}s the background read writes the state: {state}"
    rows = await _profile_rows(asset_id)
    assert {row["key"]: (row["stored"], row["source"], row["user_id"]) for row in rows} == {key: (value, MOCK_CODE, None) for key, value in _expected_voices(isin).items()}, f"mockenrich's rows, no user: {rows}"


@pytest.mark.asyncio
async def test_post_with_enrichers_reads_each_created_asset_after_the_answer(test_server):
    print_section("B5b: POST /assets with enrichers, then «Aggiorna» in the background")
    first, second = _fake_isin(), _fake_isin()
    async with httpx.AsyncClient() as client:
        await _login(client)
        failing = _item("BG_POST_FAIL", enrichers={MOCK_CODE: _binding(_fake_isin())}, profile={"ter": "-1"})
        results = await _post(client, [_item("BG_POST_A", enrichers={MOCK_CODE: _binding(first)}), failing, _item("BG_POST_B", enrichers={MOCK_CODE: _binding(second)})])
        asset_ids = [int(result["asset_id"]) for result in results if result["success"]]
        try:
            assert [result["success"] for result in results] == [True, False, True], f"the two valid items created, the invalid one failed: {results}"

            await _assert_read_in_background(client, asset_ids[0], first)
            await _assert_read_in_background(client, asset_ids[1], second)
            for asset_id, isin in zip(asset_ids, (first, second), strict=True):
                assert ((await _read_asset(client, asset_id)).get("enrichers") or {}).get("config") == {MOCK_CODE: _binding(isin)}, "the binding sent, untouched by the read"
            print_success("each created asset read after the answer")
        finally:
            await _delete(client, asset_ids)


@pytest.mark.asyncio
async def test_a_committed_patch_that_sets_enrichers_reads_them_after_the_answer(test_server):
    isin = _fake_isin()
    async with httpx.AsyncClient() as client:
        await _login(client)
        asset_id = await _create(client, _item("BG_PATCH"))
        try:
            resp = await client.patch(f"{API_BASE}/assets", json=[{"asset_id": asset_id, "enrichers": {MOCK_CODE: _binding(isin)}}], timeout=TIMEOUT)
            assert resp.status_code == 200 and resp.json()["committed"] is True, f"PATCH /assets: {resp.status_code} {resp.text}"

            await _assert_read_in_background(client, asset_id, isin)
        finally:
            await _delete(client, [asset_id])


@pytest.mark.asyncio
async def test_no_read_after_validate_a_refused_batch_or_a_patch_without_enrichers(test_server):
    """Three assets bound beforehand (without a route), so a read started by mistake would leave a state and rows:
    ``/validate`` setting their binding, a batch refused by a missing asset, a PATCH of the name only. Then a marker, a
    POST whose own background read is awaited: the reads that the three requests could have started, all earlier,
    have had their time."""
    print_section("B5b: no «Aggiorna» after validate, a refused batch, a patch without enrichers")
    validated, refused, renamed, marker = _fake_isin(), _fake_isin(), _fake_isin(), _fake_isin()
    missing = 2_000_000_000 + int(uuid.uuid4().int % 1_000_000)
    async with httpx.AsyncClient() as client:
        await _login(client)
        asset_ids: list[int] = []
        try:
            for tag, isin in (("BG_VALIDATE", validated), ("BG_REFUSED", refused), ("BG_RENAMED", renamed)):
                asset_ids.append(await _create_bound(client, tag, isin))
            validated_id, refused_id, renamed_id = asset_ids

            check = await client.post(f"{API_BASE}/assets/validate", json=[{"asset_id": validated_id, "enrichers": {MOCK_CODE: _binding(validated)}}], timeout=TIMEOUT)
            assert check.status_code == 200 and check.json()["committed"] is False and check.json()["issues"] == [], f"barrier: the dry run would save: {check.status_code} {check.text}"
            batch = await client.patch(f"{API_BASE}/assets", json=[{"asset_id": refused_id, "enrichers": {MOCK_CODE: _binding(refused)}}, {"asset_id": missing, "display_name": "nobody"}], timeout=TIMEOUT)
            assert batch.status_code == 200 and batch.json()["committed"] is False and batch.json()["issues"], f"barrier: the batch is refused: {batch.status_code} {batch.text}"
            rename = await client.patch(f"{API_BASE}/assets", json=[{"asset_id": renamed_id, "display_name": f"Profile read renamed {unique_id('BG_REN')}"}], timeout=TIMEOUT)
            assert rename.status_code == 200 and rename.json()["committed"] is True, f"barrier: the rename is saved: {rename.status_code} {rename.text}"

            marker_id = await _create(client, _item("BG_MARKER", enrichers={MOCK_CODE: _binding(marker)}))
            asset_ids.append(marker_id)
            await _assert_read_in_background(client, marker_id, marker)

            for asset_id in (validated_id, refused_id, renamed_id):
                assert _state_of(await _read_asset(client, asset_id)) == {}, f"asset {asset_id}: no read started"
                assert await _profile_rows(asset_id) == [], f"asset {asset_id}: no row written"
            print_success("no read without a committed save that sets the enrichers")
        finally:
            await _delete(client, asset_ids)


# =============================================================================
# 4. B5b: {"from": …} through the routes
# =============================================================================


@pytest.mark.asyncio
async def test_from_the_source_with_a_changed_seen_warns_and_writes_in_the_sources_name(test_server):
    print_section("B5b: profile {from: mockenrich, seen} on /validate and PATCH")
    mock = _mock()
    isin = _fake_isin()
    items = [{"asset_id": 0, "profile": {"ter": {"from": MOCK_CODE, "seen": "0.0030"}}}]
    async with httpx.AsyncClient() as client:
        await _login(client)
        asset_id = await _create_bound(client, "FROM", isin)
        items[0]["asset_id"] = asset_id
        expected = [(asset_id, 0, PROFILE_SOURCE_CHANGED, "profile.ter", {"voice": "ter", "seen": "0.003", "now": "0.0022"})]
        try:
            check = await client.post(f"{API_BASE}/assets/validate", json=items, timeout=TIMEOUT)
            assert check.status_code == 200, f"POST /assets/validate: {check.status_code} {check.text}"
            body = check.json()
            assert body["issues"] == [] and [(w["asset_id"], w["index"], w["code"], w["field"], w["params"]) for w in body["warnings"]] == expected, f"the dry run warns: {body}"
            assert await _profile_rows(asset_id) == [], "the dry run writes nothing"

            resp = await client.patch(f"{API_BASE}/assets", json=items, timeout=TIMEOUT)

            assert resp.status_code == 200, f"PATCH /assets: {resp.status_code} {resp.text}"
            body = resp.json()
            assert body["committed"] is True and [(w["asset_id"], w["index"], w["code"], w["field"], w["params"]) for w in body["warnings"]] == expected, f"saved, with the warning: {body}"
            rows = await _profile_rows(asset_id)
            assert [(row["key"], row["stored"], row["source"], row["user_id"], str(row["source_date"])) for row in rows] == [("ter", "0.0022", MOCK_CODE, None, mock.SOURCE_DATE.isoformat())], f"the row in mockenrich's name: {rows}"
        finally:
            await _delete(client, [asset_id])

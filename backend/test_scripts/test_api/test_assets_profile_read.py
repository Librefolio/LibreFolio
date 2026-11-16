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

Every test registers its own user and creates its own assets under unique names, bound to an ISIN no other test uses:
the backend's read cache is shared by every test of the lane and lives 30 minutes, so no assertion depends on what it
holds — ``from_cache`` is asserted only on a first read of a fresh ISIN. The rows of the database are read for the
test's own assets only.

Red until B5a: both routes raise ``NotImplementedError`` (500). The three 422 cases are green already (the request's
validator exists): they are guards.
"""

from __future__ import annotations

import json
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


async def _create_bound(client: httpx.AsyncClient, tag: str, identifier: str) -> int:
    """An ETF of the test, bound to mockenrich with ``identifier`` as ISIN."""
    item = {"display_name": f"Profile read {unique_id(tag)}", "currency": "EUR", "asset_type": "ETF", "enrichers": {MOCK_CODE: {"identifier_type": "ISIN", "identifier": identifier}}}
    resp = await client.post(f"{API_BASE}/assets", json=[item], timeout=TIMEOUT)
    assert resp.status_code == 201, f"POST /assets: {resp.status_code} {resp.text}"
    result = resp.json()["results"][0]
    assert result["success"] and result["asset_id"] is not None, f"the asset must be created: {result}"
    return int(result["asset_id"])


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

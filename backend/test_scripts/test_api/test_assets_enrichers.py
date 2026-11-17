"""
Test Suite: the enrichers and the profile of an asset through the asset routes (project 68, lot B3).

1. ``GET /assets/enrichers``: ``mockenrich`` (test mode) listed with its declarations; ``default_order`` has a key for
   every AssetType, ``mockenrich`` in the ETF one and not in the INDEX one.
2. ``enrichers`` on ``POST /assets`` and ``PATCH /assets``: the bindings stored in the order sent — codes not installed
   and a plugin's free keys kept — and read back by ``GET /assets`` (``enrichers.config``, ``enrichers.state``). PATCH: a
   new dict replaces, ``{}`` and ``null`` clear, absent leaves it. A key that is not an enricher code, or a binding
   without ``identifier``, is a 422.
3. ``profile`` on ``PATCH /assets`` (plan §3.5): a value → a ``user`` row by the caller; ``null`` → a NULL row over a
   value; a voice absent → untouched; a value of the wrong shape or an unknown voice → ``committed: false`` with one
   issue ``profileValueInvalid`` on ``profile.<voice>``, nothing of the item saved and no row — the same on
   ``POST /assets/validate``. With ``classification_params`` on the same voice, the profile value is «now». A PATCH of
   ``profile`` never changes the ``classification_params`` column; a PATCH of ``classification_params`` still writes
   both (A4).
4. ``profile`` on ``POST /assets``: ``user`` rows by the creator; an invalid value fails that item, the asset is not
   created.
5. B4, ``POST /assets/enrichers/recognize`` (Server-Sent Events, each ``data: {json}`` with an ``event`` key): with an
   ISIN and ``codes: ["mockenrich"]``, one ``enricher_result`` found with ``lei_of(isin)``, one ``identifier_learned``
   LEI from mockenrich, and last ``done`` with ``found_order``, ``default_order`` (the catalogue's order of the type,
   restricted to the codes asked, in that order) and every identifier known. An ``UNKNOWN…`` ISIN is not found and
   teaches nothing; ``codes`` leaving mockenrich out
   asks nothing (assumed: a code not installed is ignored); a type mockenrich does not cover asks nothing; empty
   ``identifiers`` is a 422; without ``codes`` mockenrich is asked too (only its events read), on CRYPTO, a type no
   real enricher covers. Every other recognize names ``codes``: a real enricher is never reached over the network with
   a fake ISIN.
6. B4, ``GET /assets/enrichers/{code}/search``: mockenrich does not search → 400 with a detail; unknown code → 404.
   ``POST /assets/enrichers/{code}/test``: mockenrich's answer for the binding (found, name, page, the LEI; not found
   for ``UNKNOWN…``); unknown code → 404; an asset of the test bound to the same binding is unchanged after it.

Every test registers its own user and creates its own assets under unique names; the rows of the database are read
for those assets only (``asset_profile_updates``, ``asset_enrichers``, ``assets``). Bodies are raw dicts: a
``model_dump`` would send ``enrichers: null`` and ``profile: null``, which mean «clear» here.

The background «Aggiorna» (B5b): a POST or a committed PATCH that sets non-empty ``enrichers`` reads them after the
answer, writing rows and ``state``. So ``ENRICHERS`` binds codes that are never installed only (the read has nothing to
read, ``state`` stays ``{}`` by design), and the «test» route's asset is bound to mockenrich straight on the lane's
database (``bindings.save_config``), never through a route: no read of the server runs beside the one under test.
``ENRICHERS_AGAIN`` keeps mockenrich: the tests that send it compare ``config`` only, which no read ever writes.

Not pinned: whether ``GET /assets`` answers ``enrichers: null`` or an empty ``config`` after a clear (both accepted),
and what the ``classification_params`` column holds when ``classification_params`` and ``profile`` touch the same voice.

Red until B3: ``bindings.py`` raises ``NotImplementedError`` (``GET /assets/enrichers`` answers 500, the direct
``update_state`` raises); ``POST /assets`` ignores ``enrichers`` and ``profile``; a ``PATCH`` carrying ``profile`` fails
the whole batch with ``patchFailed`` (``AttributeError`` while applying); ``GET /assets`` answers ``enrichers: null``.

Red until B4: the three B4 routes raise ``NotImplementedError`` (500).
"""

from __future__ import annotations

import json
import uuid
from decimal import Decimal
from typing import Any

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.db.models import AssetType
from backend.app.db.session import get_async_engine
from backend.app.services.assets.profile.catalogue import normalize_value
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success, unique_id

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0
MOCK_CODE = "mockenrich"
PROFILE_VALUE_INVALID = "profileValueInvalid"

#: Not alphabetical, codes never installed only (B5b: no background read finds anything to read), a free key of one
#: plugin (``mic``).
ENRICHERS_ORDER = ["zeta_lab", "mid_lab", "alpha_lab"]
ENRICHERS = {
    "zeta_lab": {"identifier_type": "ISIN", "identifier": "IE00B4L5Y983"},
    "mid_lab": {"identifier_type": "ISIN", "identifier": "IE00B4L5Y983"},
    "alpha_lab": {"identifier_type": "ISIN", "identifier": "IT0003128367", "mic": "MTA"},
}
ENRICHERS_AGAIN_ORDER = ["alpha_lab", MOCK_CODE]
ENRICHERS_AGAIN = {
    "alpha_lab": {"identifier_type": "LEI", "identifier": "815600C1E8D1A8C6E417", "platform": "ETF"},
    MOCK_CODE: {"identifier_type": "TICKER", "identifier": "SWDA"},
}
TER = "0.0022"


@pytest.fixture(scope="module")
def test_server():
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


# =============================================================================
# HELPERS
# =============================================================================


async def _login(client: httpx.AsyncClient) -> int:
    """A fresh user, logged in on ``client``: its id."""
    username = f"enr_{uuid.uuid4().hex[:12]}"
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


def _item(tag: str, **fields: Any) -> dict[str, Any]:
    return {"display_name": f"Enrichers {unique_id(tag)}", "currency": "EUR", "asset_type": "ETF", **fields}


async def _create(client: httpx.AsyncClient, item: dict[str, Any]) -> int:
    resp = await client.post(f"{API_BASE}/assets", json=[item], timeout=TIMEOUT)
    assert resp.status_code == 201, f"POST /assets: {resp.status_code} {resp.text}"
    result = resp.json()["results"][0]
    assert result["success"] and result["asset_id"] is not None, f"the asset must be created: {result}"
    return int(result["asset_id"])


async def _delete(client: httpx.AsyncClient, asset_ids: list[int]) -> None:
    if asset_ids:
        await client.delete(f"{API_BASE}/assets", params={"asset_ids": asset_ids}, timeout=TIMEOUT)


async def _read(client: httpx.AsyncClient, asset_id: int) -> dict[str, Any]:
    resp = await client.get(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)
    assert resp.status_code == 200, f"GET /assets: {resp.status_code} {resp.text}"
    found = [asset for asset in resp.json() if asset["asset_id"] == asset_id]
    assert len(found) == 1, f"asset {asset_id} not answered: {resp.text}"
    return found[0]


def _config_of(asset: dict[str, Any]) -> dict[str, Any]:
    """``enrichers.config`` of a read asset; an asset with no enrichers (``null``) has none."""
    return (asset.get("enrichers") or {}).get("config") or {}


async def _patch(client: httpx.AsyncClient, items: list[dict[str, Any]], *, route: str = "patch") -> dict[str, Any]:
    if route == "patch":
        resp = await client.patch(f"{API_BASE}/assets", json=items, timeout=TIMEOUT)
    else:
        resp = await client.post(f"{API_BASE}/assets/validate", json=items, timeout=TIMEOUT)
    assert resp.status_code == 200, f"{route} /assets: {resp.status_code} {resp.text}"
    return resp.json()


def _issues(body: dict[str, Any]) -> list[tuple[int, int, str, str | None]]:
    return [(issue["asset_id"], issue["index"], issue["code"], issue.get("field")) for issue in body["issues"]]


async def _profile_rows(asset_id: int) -> list[dict[str, Any]]:
    """The asset's profile rows in the store's order (read_on, id), each with ``stored``: its value as the store reads it."""
    async with AsyncSession(get_async_engine()) as session:
        result = await session.execute(text("SELECT id, key, value, source, user_id, read_on FROM asset_profile_updates WHERE asset_id = :asset ORDER BY read_on, id"), {"asset": asset_id})
        rows = [dict(row._mapping) for row in result]
    for row in rows:
        row["stored"] = None if row["value"] is None else normalize_value(row["key"], json.loads(row["value"]))
    return rows


def _new(before: list[dict[str, Any]], after: list[dict[str, Any]]) -> list[dict[str, Any]]:
    known = {row["id"] for row in before}
    return [row for row in after if row["id"] not in known]


def _summary(rows: list[dict[str, Any]]) -> list[tuple[str, Any, str, int | None]]:
    return sorted(((row["key"], row["stored"], row["source"], row["user_id"]) for row in rows), key=lambda item: item[0])


async def _column(asset_id: int) -> tuple[str, str | None]:
    """The asset's display name and stored ``classification_params`` text."""
    async with AsyncSession(get_async_engine()) as session:
        row = (await session.execute(text("SELECT display_name, classification_params FROM assets WHERE id = :asset"), {"asset": asset_id})).one()
    return row.display_name, row.classification_params


async def _asset_id_named(name: str) -> int | None:
    async with AsyncSession(get_async_engine()) as session:
        return (await session.execute(text("SELECT id FROM assets WHERE display_name = :name"), {"name": name})).scalar()


# =============================================================================
# 1. GET /assets/enrichers
# =============================================================================


@pytest.mark.asyncio
async def test_get_enrichers_lists_mockenrich_and_a_default_order_for_every_type(test_server):
    print_section("B3: GET /assets/enrichers")
    from backend.app.services.enricher_providers.mockenrich.plugin import MockEnricher  # noqa: PLC0415 — the plugin's own declarations, read in the test body

    async with httpx.AsyncClient() as client:
        await _login(client)
        resp = await client.get(f"{API_BASE}/assets/enrichers", timeout=TIMEOUT)

    assert resp.status_code == 200, f"GET /assets/enrichers: {resp.status_code} {resp.text}"
    body = resp.json()
    mock = next((info for info in body["enrichers"] if info["code"] == MOCK_CODE), None)
    assert mock is not None, f"mockenrich is listed in test mode: {[info['code'] for info in body['enrichers']]}"
    assert mock["name"] == MockEnricher.name and mock["terms"] == "open", mock
    assert mock["accepted_identifier_types"] == list(MockEnricher.accepted_identifier_types), mock
    assert mock["voices"]["ETF"] == sorted(MockEnricher.voices[AssetType.ETF]), f"the ETF voices as a sorted list: {mock['voices']}"
    assert set(mock["default_priority"]) == {asset_type.value for asset_type in AssetType}, f"a degree for every type: {mock['default_priority']}"
    assert mock["default_priority"]["ETF"] == 100 and mock["default_priority"]["INDEX"] is None, mock["default_priority"]
    assert set(body["default_order"]) == {asset_type.value for asset_type in AssetType}, f"a default order for every type: {sorted(body['default_order'])}"
    assert MOCK_CODE in body["default_order"]["ETF"] and MOCK_CODE not in body["default_order"]["INDEX"], body["default_order"]
    print_success("mockenrich listed; a default order for every asset type")


# =============================================================================
# 2. enrichers on POST and PATCH /assets
# =============================================================================


@pytest.mark.asyncio
async def test_post_stores_the_enrichers_in_the_order_sent_with_their_free_keys(test_server):
    print_section("B3: POST /assets with enrichers")
    async with httpx.AsyncClient() as client:
        await _login(client)
        asset_id = await _create(client, _item("ENR_POST", enrichers=ENRICHERS))
        try:
            asset = await _read(client, asset_id)
            enrichers = asset.get("enrichers")
            assert enrichers is not None, f"GET /assets must answer the enrichers: {asset}"
            assert list(enrichers["config"]) == ENRICHERS_ORDER, f"the order sent, codes not installed included: {list(enrichers['config'])}"
            assert enrichers["config"] == ENRICHERS, f"the bindings sent, the free key mic included: {enrichers['config']}"
            assert enrichers["state"] == {}, f"a new asset bound to enrichers not installed has no reads: {enrichers['state']}"
            print_success("order, codes not installed and free keys kept")
        finally:
            await _delete(client, [asset_id])


@pytest.mark.asyncio
async def test_patch_enrichers_replaces_them_in_the_new_order(test_server):
    async with httpx.AsyncClient() as client:
        await _login(client)
        asset_id = await _create(client, _item("ENR_REPLACE", enrichers=ENRICHERS))
        try:
            assert list(_config_of(await _read(client, asset_id))) == ENRICHERS_ORDER, "barrier: the POST stored the enrichers"

            body = await _patch(client, [{"asset_id": asset_id, "enrichers": ENRICHERS_AGAIN}])

            assert body["committed"] is True, body
            config = _config_of(await _read(client, asset_id))
            assert list(config) == ENRICHERS_AGAIN_ORDER and config == ENRICHERS_AGAIN, f"the PATCH replaces, in its order: {config}"
        finally:
            await _delete(client, [asset_id])


@pytest.mark.asyncio
@pytest.mark.parametrize("cleared", [pytest.param({}, id="empty-dict"), pytest.param(None, id="null")])
async def test_patch_enrichers_empty_or_null_clears_them(test_server, cleared):
    async with httpx.AsyncClient() as client:
        await _login(client)
        asset_id = await _create(client, _item("ENR_CLEAR", enrichers=ENRICHERS))
        try:
            assert list(_config_of(await _read(client, asset_id))) == ENRICHERS_ORDER, "barrier: the POST stored the enrichers"

            body = await _patch(client, [{"asset_id": asset_id, "enrichers": cleared}])

            assert body["committed"] is True, body
            assert _config_of(await _read(client, asset_id)) == {}, f"{cleared!r} clears the bindings"
        finally:
            await _delete(client, [asset_id])


@pytest.mark.asyncio
async def test_patch_without_enrichers_leaves_them(test_server):
    async with httpx.AsyncClient() as client:
        await _login(client)
        asset_id = await _create(client, _item("ENR_ABSENT", enrichers=ENRICHERS))
        try:
            assert list(_config_of(await _read(client, asset_id))) == ENRICHERS_ORDER, "barrier: the POST stored the enrichers"

            body = await _patch(client, [{"asset_id": asset_id, "display_name": f"Enrichers renamed {unique_id('ENR_ABS')}"}])

            assert body["committed"] is True, body
            config = _config_of(await _read(client, asset_id))
            assert list(config) == ENRICHERS_ORDER and config == ENRICHERS, f"an absent enrichers leaves them: {config}"
        finally:
            await _delete(client, [asset_id])


_MALFORMED = [
    pytest.param({"Bad-Code": {"identifier_type": "ISIN", "identifier": "IE00B4L5Y983"}}, id="not-a-code"),
    pytest.param({MOCK_CODE: {"identifier_type": "ISIN"}}, id="no-identifier"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("enrichers", _MALFORMED)
async def test_malformed_enrichers_are_a_422_on_post_and_patch(test_server, enrichers):
    async with httpx.AsyncClient() as client:
        await _login(client)
        item = _item("ENR_BAD", enrichers=enrichers)
        post = await client.post(f"{API_BASE}/assets", json=[item], timeout=TIMEOUT)
        assert post.status_code == 422, f"POST: {post.status_code} {post.text}"
        assert await _asset_id_named(item["display_name"]) is None, "a refused POST creates no asset"

        asset_id = await _create(client, _item("ENR_BAD_PATCH"))
        try:
            patch = await client.patch(f"{API_BASE}/assets", json=[{"asset_id": asset_id, "enrichers": enrichers}], timeout=TIMEOUT)
            assert patch.status_code == 422, f"PATCH: {patch.status_code} {patch.text}"
        finally:
            await _delete(client, [asset_id])


@pytest.mark.asyncio
async def test_get_assets_answers_the_state_a_read_wrote(test_server):
    """A read's state, written straight on the lane's database as the reads will write it, is answered by GET."""
    from backend.app.services.enrichers import bindings  # noqa: PLC0415 — the service under test, imported in the test body

    state = {"read_on": "2026-11-10", "outcome": "ok"}
    async with httpx.AsyncClient() as client:
        await _login(client)
        asset_id = await _create(client, _item("ENR_STATE", enrichers=ENRICHERS))
        try:
            async with AsyncSession(get_async_engine()) as session:
                await bindings.update_state(session, asset_id, {MOCK_CODE: state})
                await session.commit()

            enrichers = (await _read(client, asset_id)).get("enrichers")

            assert enrichers is not None, "GET /assets must answer the enrichers"
            assert enrichers["state"] == {MOCK_CODE: state}, f"the read's state: {enrichers['state']}"
            assert list(enrichers["config"]) == ENRICHERS_ORDER, f"the config untouched: {enrichers['config']}"
        finally:
            await _delete(client, [asset_id])


# =============================================================================
# 3. profile on PATCH /assets
# =============================================================================


@pytest.mark.asyncio
async def test_patch_profile_value_writes_a_user_row_by_the_caller(test_server):
    print_section("B3: PATCH /assets profile")
    async with httpx.AsyncClient() as client:
        user_id = await _login(client)
        asset_id = await _create(client, _item("PRF_VALUE"))
        try:
            before = await _profile_rows(asset_id)

            body = await _patch(client, [{"asset_id": asset_id, "profile": {"ter": TER}}])

            assert body["committed"] is True and body["issues"] == [], body
            new = _new(before, await _profile_rows(asset_id))
            assert _summary(new) == [("ter", normalize_value("ter", TER), "user", user_id)], f"one ter row by the caller: {_summary(new)}"
            print_success(f"profile row written by user {user_id}")
        finally:
            await _delete(client, [asset_id])


@pytest.mark.asyncio
async def test_patch_profile_null_empties_a_voice_with_a_value(test_server):
    async with httpx.AsyncClient() as client:
        user_id = await _login(client)
        asset_id = await _create(client, _item("PRF_NULL"))
        try:
            first = await _patch(client, [{"asset_id": asset_id, "profile": {"ter": TER}}])
            with_value = await _profile_rows(asset_id)
            assert first["committed"] is True and [row["key"] for row in with_value] == ["ter"], f"barrier: the ter value is written: {with_value}"

            body = await _patch(client, [{"asset_id": asset_id, "profile": {"ter": None}}])

            assert body["committed"] is True, body
            new = _new(with_value, await _profile_rows(asset_id))
            assert [(row["key"], row["value"], row["source"], row["user_id"]) for row in new] == [("ter", None, "user", user_id)], f"one NULL ter row by the caller: {new}"
        finally:
            await _delete(client, [asset_id])


@pytest.mark.asyncio
async def test_patch_profile_leaves_a_voice_it_does_not_name(test_server):
    async with httpx.AsyncClient() as client:
        user_id = await _login(client)
        asset_id = await _create(client, _item("PRF_ABSENT"))
        try:
            first = await _patch(client, [{"asset_id": asset_id, "profile": {"ter": TER}}])
            with_ter = await _profile_rows(asset_id)
            assert first["committed"] is True and [row["key"] for row in with_ter] == ["ter"], f"barrier: the ter value is written: {with_ter}"

            body = await _patch(client, [{"asset_id": asset_id, "profile": {"description": "A global equity ETF"}}])

            assert body["committed"] is True, body
            new = _new(with_ter, await _profile_rows(asset_id))
            assert _summary(new) == [("description", "A global equity ETF", "user", user_id)], f"only the description is written, ter untouched: {_summary(new)}"
        finally:
            await _delete(client, [asset_id])


_INVALID_PROFILE = [
    pytest.param("ter", "-0.1", id="negative-ter"),
    pytest.param("ter", 0.002, id="float-ter"),
    pytest.param("not_a_profile_voice", "x", id="unknown-voice"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("voice", "value"), _INVALID_PROFILE)
async def test_patch_with_an_invalid_profile_value_saves_nothing_of_the_item(test_server, voice, value):
    """One issue ``profileValueInvalid`` on ``profile.<voice>``; the item's rename is not saved; no profile row. The same
    body to ``POST /assets/validate``: the same issue, nothing written. Barrier, last: a valid profile is written."""
    async with httpx.AsyncClient() as client:
        await _login(client)
        asset_id = await _create(client, _item("PRF_BAD"))
        try:
            name_before, _ = await _column(asset_id)
            item = {"asset_id": asset_id, "display_name": f"Enrichers renamed {unique_id('PRF_BAD')}", "profile": {voice: value}}
            expected = [(asset_id, 0, PROFILE_VALUE_INVALID, f"profile.{voice}")]

            body = await _patch(client, [item])

            assert body["committed"] is False and _issues(body) == expected, f"one profileValueInvalid issue: committed={body['committed']} {_issues(body)}"
            assert (await _column(asset_id))[0] == name_before, "nothing of the item is saved: the name stays"
            assert await _profile_rows(asset_id) == [], "no profile row"

            dry = await _patch(client, [item], route="validate")

            assert dry["committed"] is False and _issues(dry) == expected, f"validate answers the same issue: {_issues(dry)}"
            assert (await _column(asset_id))[0] == name_before and await _profile_rows(asset_id) == [], "validate writes nothing"

            valid = await _patch(client, [{"asset_id": asset_id, "profile": {"ter": TER}}])
            assert valid["committed"] is True and [row["key"] for row in await _profile_rows(asset_id)] == ["ter"], "barrier: a valid profile value is written on this asset"
        finally:
            await _delete(client, [asset_id])


@pytest.mark.asyncio
async def test_profile_wins_over_classification_params_on_the_same_voice(test_server):
    """One PATCH sends a geography in ``classification_params`` and another in ``profile``: the geography «now» (the last
    row in the store's order) is the ``profile`` one."""
    async with httpx.AsyncClient() as client:
        user_id = await _login(client)
        asset_id = await _create(client, _item("PRF_WINS"))
        try:
            body = await _patch(
                client,
                [{"asset_id": asset_id, "classification_params": {"geographic_area": {"distribution": {"USA": "1"}}}, "profile": {"geography": {"JPN": "1"}}}],
            )

            assert body["committed"] is True, body
            geography = [row for row in await _profile_rows(asset_id) if row["key"] == "geography"]
            assert geography, "a geography row is written"
            now = geography[-1]
            assert (now["stored"], now["source"], now["user_id"]) == (normalize_value("geography", {"JPN": "1"}), "user", user_id), f"the profile value is now: {geography}"
        finally:
            await _delete(client, [asset_id])


_CLASSIFICATION = {
    "short_description": "Global developed-markets equity ETF",
    "geographic_area": {"distribution": {"USA": "0.6", "JPN": "0.4"}},
    "sector_area": {"distribution": {"Technology": "1"}},
}


@pytest.mark.asyncio
async def test_patch_profile_never_changes_the_classification_column(test_server):
    """``profile`` for geography, sector and description writes three ``user`` rows and leaves the
    ``classification_params`` column exactly as it was (design consultant, B3)."""
    async with httpx.AsyncClient() as client:
        user_id = await _login(client)
        asset_id = await _create(client, _item("PRF_COLUMN", classification_params=_CLASSIFICATION))
        try:
            _, column_before = await _column(asset_id)
            assert column_before is not None, "barrier: the column holds the classification"
            before = await _profile_rows(asset_id)
            profile = {"geography": {"GBR": "1"}, "sector": {"Energy": "1"}, "description": "Edited by hand in the profile"}

            body = await _patch(client, [{"asset_id": asset_id, "profile": profile}])

            assert body["committed"] is True, body
            new = _new(before, await _profile_rows(asset_id))
            expected = sorted(((key, normalize_value(key, value), "user", user_id) for key, value in profile.items()), key=lambda item: item[0])
            assert _summary(new) == expected, f"three user rows by the caller: {_summary(new)}"
            assert (await _column(asset_id))[1] == column_before, "a PATCH of profile never changes classification_params"
        finally:
            await _delete(client, [asset_id])


@pytest.mark.asyncio
async def test_patch_classification_still_writes_the_column_and_the_profile(test_server):
    """The contrast (A4): ``classification_params`` changes the column and writes the profile row."""
    async with httpx.AsyncClient() as client:
        user_id = await _login(client)
        asset_id = await _create(client, _item("PRF_A4", classification_params=_CLASSIFICATION))
        try:
            _, column_before = await _column(asset_id)
            before = await _profile_rows(asset_id)

            body = await _patch(client, [{"asset_id": asset_id, "classification_params": {"sector_area": {"distribution": {"Energy": "1"}}}}])

            assert body["committed"] is True, body
            _, column_after = await _column(asset_id)
            sectors = {name: Decimal(weight) for name, weight in json.loads(column_after)["sector_area"]["distribution"].items()}
            assert column_after != column_before and sectors == {"Energy": Decimal(1)}, f"the column changes: {column_after}"
            new = _new(before, await _profile_rows(asset_id))
            assert _summary(new) == [("sector", normalize_value("sector", {"Energy": "1"}), "user", user_id)], f"and the profile gets the sector row: {_summary(new)}"
        finally:
            await _delete(client, [asset_id])


# =============================================================================
# 4. profile on POST /assets
# =============================================================================


@pytest.mark.asyncio
async def test_post_with_a_profile_writes_user_rows_and_an_invalid_value_fails_the_item(test_server):
    """One batch: a valid profile → the asset with two ``user`` rows by the creator; ``ter: "-0.1"`` → that item fails,
    no asset of that name."""
    print_section("B3: POST /assets profile")
    async with httpx.AsyncClient() as client:
        user_id = await _login(client)
        good = _item("PRF_POST", profile={"ter": TER, "description": "Created with a profile"})
        bad = _item("PRF_POST_BAD", profile={"ter": "-0.1"})
        created: list[int] = []
        try:
            resp = await client.post(f"{API_BASE}/assets", json=[good, bad], timeout=TIMEOUT)
            assert resp.status_code == 201, f"POST /assets: {resp.status_code} {resp.text}"
            results = {result["display_name"]: result for result in resp.json()["results"]}
            created = [asset_id for name in (good["display_name"], bad["display_name"]) if (asset_id := await _asset_id_named(name)) is not None]

            assert results[good["display_name"]]["success"] is True, results
            good_id = int(results[good["display_name"]]["asset_id"])
            rows = await _profile_rows(good_id)
            assert _summary(rows) == [("description", "Created with a profile", "user", user_id), ("ter", normalize_value("ter", TER), "user", user_id)], f"two user rows by the creator: {_summary(rows)}"

            assert results[bad["display_name"]]["success"] is False and results[bad["display_name"]]["asset_id"] is None, f"the invalid item fails: {results[bad['display_name']]}"
            assert await _asset_id_named(bad["display_name"]) is None, "the asset with an invalid profile value is not created"
            print_success("valid profile written by the creator; invalid item not created")
        finally:
            await _delete(client, created)


# =============================================================================
# 5. B4: POST /assets/enrichers/recognize (Server-Sent Events)
# =============================================================================

#: The keys of an ``enricher_result`` event: the fields of ``FAEnricherRecognition``.
RECOGNITION_KEYS = {"code", "identifier_type", "identifier", "status", "name", "page_url", "identifiers", "conflicts", "error"}


def _fake_isin() -> str:
    """An ISIN-shaped identifier no other test uses: mockenrich finds any identifier without the ``UNKNOWN`` prefix."""
    return f"ZZ{uuid.uuid4().hex[:10].upper()}"


def _mock_page(identifier_type: str, identifier: str) -> str | None:
    from backend.app.services.enricher_providers.mockenrich.plugin import MockEnricher  # noqa: PLC0415 — the plugin's own rule, read in the test body
    from backend.app.services.enrichers.base import EnricherBinding  # noqa: PLC0415

    return MockEnricher().page_url(EnricherBinding(identifier_type=identifier_type, identifier=identifier))


async def _recognize(client: httpx.AsyncClient, body: dict[str, Any]) -> list[dict[str, Any]]:
    """The events of one recognize stream, read to its end: each ``data: {json}`` line, in order."""
    resp = await client.post(f"{API_BASE}/assets/enrichers/recognize", json=body, timeout=TIMEOUT)
    assert resp.status_code == 200, f"POST /assets/enrichers/recognize: {resp.status_code} {resp.text}"
    assert resp.headers.get("content-type", "").startswith("text/event-stream"), f"a Server-Sent Events stream: {resp.headers.get('content-type')}"
    events = [json.loads(line.removeprefix("data: ")) for line in resp.text.splitlines() if line.startswith("data: ")]
    assert events and all("event" in event for event in events), f"every event names its kind: {resp.text[:1000]}"
    assert [event["event"] for event in events].count("done") == 1 and events[-1]["event"] == "done", f"the stream ends with one done event: {events}"
    return events


def _results(events: list[dict[str, Any]], code: str | None = None) -> list[dict[str, Any]]:
    return [event for event in events if event["event"] == "enricher_result" and (code is None or event.get("code") == code)]


def _learned_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [event for event in events if event["event"] == "identifier_learned"]


async def _catalogue_order(client: httpx.AsyncClient, asset_type: str) -> list[str]:
    resp = await client.get(f"{API_BASE}/assets/enrichers", timeout=TIMEOUT)
    assert resp.status_code == 200, f"GET /assets/enrichers: {resp.status_code} {resp.text}"
    return resp.json()["default_order"][asset_type]


@pytest.mark.asyncio
async def test_recognize_streams_mockenrich_found_its_learned_lei_and_done(test_server):
    """An ISIN, mockenrich only (``codes``: no other enricher is reached): one ``enricher_result`` found with the LEI, one
    ``identifier_learned`` LEI from mockenrich, then ``done`` with the found order, the default order and every
    identifier known."""
    print_section("B4: POST /assets/enrichers/recognize")
    from backend.app.services.enricher_providers.mockenrich.plugin import lei_of  # noqa: PLC0415 — the plugin's own rule, read in the test body

    isin = _fake_isin()
    async with httpx.AsyncClient() as client:
        await _login(client)
        events = await _recognize(client, {"asset_type": "ETF", "identifiers": {"ISIN": isin}, "codes": [MOCK_CODE]})
        etf_order = await _catalogue_order(client, "ETF")

    results = _results(events, MOCK_CODE)
    assert len(results) == 1, f"one answer from mockenrich (found, not asked again with the LEI): {events}"
    result = results[0]
    assert RECOGNITION_KEYS <= set(result), f"the fields of FAEnricherRecognition: {sorted(result)}"
    assert (result["identifier_type"], result["identifier"], result["status"]) == ("ISIN", isin, "found"), result
    assert result["name"] == f"Mock {isin}" and result["page_url"] == _mock_page("ISIN", isin), result
    assert result["identifiers"] == {"LEI": lei_of(isin)} and result["conflicts"] == {} and result["error"] is None, result
    learned = _learned_events(events)
    assert [(event["identifier_type"], event["identifier"], event["source"]) for event in learned] == [("LEI", lei_of(isin), MOCK_CODE)], f"the LEI learned from mockenrich: {learned}"
    done = events[-1]
    assert done["found_order"] == [MOCK_CODE], f"found_order: {done}"
    assert done["identifiers"] == {"ISIN": isin, "LEI": lei_of(isin)}, f"every identifier known at the end: {done}"
    # The route restricts default_order to the enrichers asked (codes): the catalogue's ETF order, the codes asked only
    asked_order = [code for code in etf_order if code in {MOCK_CODE}]
    assert MOCK_CODE in done["default_order"] and done["default_order"] == asked_order, f"default_order: the catalogue's ETF order {etf_order} restricted to the codes asked: {done['default_order']} vs {asked_order}"
    print_success("found, LEI learned, done")


@pytest.mark.asyncio
async def test_recognize_an_unknown_isin_is_not_found_and_teaches_nothing(test_server):
    from backend.app.services.enricher_providers.mockenrich.plugin import UNKNOWN_PREFIX  # noqa: PLC0415 — the plugin's own rule, read in the test body

    unknown = f"{UNKNOWN_PREFIX}{uuid.uuid4().hex[:8].upper()}"
    async with httpx.AsyncClient() as client:
        await _login(client)
        events = await _recognize(client, {"asset_type": "ETF", "identifiers": {"ISIN": unknown}, "codes": [MOCK_CODE]})

    results = _results(events, MOCK_CODE)
    assert [(result["identifier"], result["status"]) for result in results] == [(unknown, "not_found")], f"not found: {events}"
    assert _learned_events(events) == [], f"nothing learned: {events}"
    assert events[-1]["found_order"] == [] and events[-1]["identifiers"] == {"ISIN": unknown}, f"done: {events[-1]}"


@pytest.mark.asyncio
async def test_recognize_without_codes_asks_every_installed_enricher(test_server):
    """No ``codes``: every installed enricher covering the type is asked, mockenrich among them. Only mockenrich's events
    are read. The type is CRYPTO, which mockenrich covers and the real enrichers do not (justETF covers the ETF family
    and COMMODITY; Borsa Italiana, Yahoo and ESMA leave CRYPTO out in their plans): with no ``codes`` the server asks
    every installed enricher covering the type, so an ETF here would send the fake ISIN to justetf.com. A real enricher
    that comes to cover CRYPTO must move this test to another type only mockenrich covers."""
    from backend.app.services.enricher_providers.mockenrich.plugin import lei_of  # noqa: PLC0415 — the plugin's own rule, read in the test body

    isin = _fake_isin()
    async with httpx.AsyncClient() as client:
        await _login(client)
        events = await _recognize(client, {"asset_type": "CRYPTO", "identifiers": {"ISIN": isin}})

    assert [(result["identifier"], result["status"]) for result in _results(events, MOCK_CODE)] == [(isin, "found")], f"mockenrich is asked and finds the ISIN: {events}"
    assert ("LEI", lei_of(isin), MOCK_CODE) in {(event["identifier_type"], event["identifier"], event["source"]) for event in _learned_events(events)}, f"the LEI learned from mockenrich: {events}"
    assert MOCK_CODE in events[-1]["found_order"], f"done: {events[-1]}"


@pytest.mark.asyncio
async def test_recognize_codes_restricts_the_enrichers_asked(test_server):
    """``codes`` naming an enricher not installed, mockenrich left out: mockenrich is not asked, nothing is found.
    (Assumption: a code not installed is ignored, not refused.)"""
    isin = _fake_isin()
    async with httpx.AsyncClient() as client:
        await _login(client)
        events = await _recognize(client, {"asset_type": "ETF", "identifiers": {"ISIN": isin}, "codes": [f"lab_absent_{uuid.uuid4().hex[:8]}"]})

    assert _results(events, MOCK_CODE) == [], f"mockenrich is left out by codes: {events}"
    assert _results(events) == [] and _learned_events(events) == [], f"no enricher asked: {events}"
    assert events[-1]["found_order"] == [] and events[-1]["identifiers"] == {"ISIN": isin}, f"done: {events[-1]}"


@pytest.mark.asyncio
async def test_recognize_asks_only_the_enrichers_covering_the_type(test_server):
    """INDEX, which mockenrich does not cover: no answer, and the default order of INDEX."""
    isin = _fake_isin()
    async with httpx.AsyncClient() as client:
        await _login(client)
        events = await _recognize(client, {"asset_type": "INDEX", "identifiers": {"ISIN": isin}, "codes": [MOCK_CODE]})
        index_order = await _catalogue_order(client, "INDEX")

    assert _results(events, MOCK_CODE) == [], f"mockenrich does not cover INDEX: {events}"
    asked_order = [code for code in index_order if code in {MOCK_CODE}]
    assert events[-1]["found_order"] == [] and events[-1]["default_order"] == asked_order, f"done: the catalogue's INDEX order {index_order} restricted to the codes asked {asked_order}: {events[-1]}"


@pytest.mark.asyncio
async def test_recognize_with_no_identifiers_is_a_422(test_server):
    async with httpx.AsyncClient() as client:
        await _login(client)
        resp = await client.post(f"{API_BASE}/assets/enrichers/recognize", json={"asset_type": "ETF", "identifiers": {}}, timeout=TIMEOUT)

    assert resp.status_code == 422, f"empty identifiers: {resp.status_code} {resp.text}"


# =============================================================================
# 6. B4: GET /assets/enrichers/{code}/search and POST /assets/enrichers/{code}/test
# =============================================================================


def _absent_code() -> str:
    return f"lab_absent_{uuid.uuid4().hex[:8]}"


@pytest.mark.asyncio
async def test_search_on_an_enricher_that_does_not_search_is_a_400(test_server):
    async with httpx.AsyncClient() as client:
        await _login(client)
        resp = await client.get(f"{API_BASE}/assets/enrichers/{MOCK_CODE}/search", params={"q": "world"}, timeout=TIMEOUT)

    assert resp.status_code == 400, f"mockenrich does not search: {resp.status_code} {resp.text}"
    detail = resp.json().get("detail")
    assert isinstance(detail, str) and detail.strip(), f"a detail that says why: {resp.text}"


@pytest.mark.asyncio
async def test_search_on_an_unknown_enricher_is_a_404(test_server):
    async with httpx.AsyncClient() as client:
        await _login(client)
        resp = await client.get(f"{API_BASE}/assets/enrichers/{_absent_code()}/search", params={"q": "world"}, timeout=TIMEOUT)

    assert resp.status_code == 404, f"an enricher not installed: {resp.status_code} {resp.text}"
    assert resp.json().get("detail"), resp.text


@pytest.mark.asyncio
async def test_test_route_recognizes_one_binding_on_mockenrich(test_server):
    print_section("B4: POST /assets/enrichers/{code}/test")
    from backend.app.services.enricher_providers.mockenrich.plugin import lei_of  # noqa: PLC0415 — the plugin's own rule, read in the test body

    isin = _fake_isin()
    async with httpx.AsyncClient() as client:
        await _login(client)
        resp = await client.post(f"{API_BASE}/assets/enrichers/{MOCK_CODE}/test", json={"binding": {"identifier_type": "ISIN", "identifier": isin}}, timeout=TIMEOUT)

    assert resp.status_code == 200, f"POST test: {resp.status_code} {resp.text}"
    body = resp.json()
    assert (body["code"], body["identifier_type"], body["identifier"], body["status"]) == (MOCK_CODE, "ISIN", isin, "found"), body
    assert body["name"] == f"Mock {isin}" and body["page_url"] == _mock_page("ISIN", isin), body
    assert body["identifiers"] == {"LEI": lei_of(isin)} and body["conflicts"] == {} and body["error"] is None, body
    print_success("mockenrich recognizes the binding")


@pytest.mark.asyncio
async def test_test_route_answers_not_found_for_an_unknown_identifier(test_server):
    from backend.app.services.enricher_providers.mockenrich.plugin import UNKNOWN_PREFIX  # noqa: PLC0415 — the plugin's own rule, read in the test body

    unknown = f"{UNKNOWN_PREFIX}{uuid.uuid4().hex[:8].upper()}"
    async with httpx.AsyncClient() as client:
        await _login(client)
        resp = await client.post(f"{API_BASE}/assets/enrichers/{MOCK_CODE}/test", json={"binding": {"identifier_type": "ISIN", "identifier": unknown}}, timeout=TIMEOUT)

    assert resp.status_code == 200, f"POST test: {resp.status_code} {resp.text}"
    body = resp.json()
    assert (body["code"], body["identifier"], body["status"], body["identifiers"]) == (MOCK_CODE, unknown, "not_found", {}), body


@pytest.mark.asyncio
async def test_test_route_on_an_unknown_enricher_is_a_404(test_server):
    async with httpx.AsyncClient() as client:
        await _login(client)
        resp = await client.post(f"{API_BASE}/assets/enrichers/{_absent_code()}/test", json={"binding": {"identifier_type": "ISIN", "identifier": _fake_isin()}}, timeout=TIMEOUT)

    assert resp.status_code == 404, f"an enricher not installed: {resp.status_code} {resp.text}"
    assert resp.json().get("detail"), resp.text


@pytest.mark.asyncio
async def test_test_route_writes_nothing_on_an_asset_bound_to_the_same_binding(test_server):
    """An asset of this test bound to mockenrich with a state: after the «test» of the same binding, its config, state
    and updated_at are as before."""
    from backend.app.services.enrichers import bindings  # noqa: PLC0415 — the service writing the state, as a read will

    isin = _fake_isin()
    binding = {"identifier_type": "ISIN", "identifier": isin}
    async with httpx.AsyncClient() as client:
        await _login(client)
        # Bound straight on the lane's database, not by the POST: a POST with enrichers starts a background read (B5b)
        # that would write the state while this test compares it.
        asset_id = await _create(client, _item("ENR_TEST_RO"))
        try:
            async with AsyncSession(get_async_engine()) as session:
                await bindings.save_config(session, asset_id, {MOCK_CODE: binding})
                await bindings.update_state(session, asset_id, {MOCK_CODE: {"read_on": "2026-11-10", "outcome": "ok"}})
                await session.commit()
            before = (await _read(client, asset_id)).get("enrichers")
            assert before is not None and before["config"] == {MOCK_CODE: binding} and before["state"], f"barrier: the asset is bound, with a state: {before}"

            resp = await client.post(f"{API_BASE}/assets/enrichers/{MOCK_CODE}/test", json={"binding": binding}, timeout=TIMEOUT)

            assert resp.status_code == 200 and resp.json()["status"] == "found", f"barrier: the test ran: {resp.status_code} {resp.text}"
            after = (await _read(client, asset_id)).get("enrichers")
            assert after == before, f"the test writes nothing: {before} → {after}"
        finally:
            await _delete(client, [asset_id])

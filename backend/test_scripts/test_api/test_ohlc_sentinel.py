"""
Test Suite: OHLC «clear» Semantics (F.4, N92) + Close Required

Covers the upsert rules of ``open``, ``high``, ``low`` and ``volume`` on PriceHistory, through
``POST /api/v1/assets/prices`` (bulk upsert). Phase 7 Part 3 Blocco F.4 introduced them with the ``-1`` sentinel; N92 (i)
(developer's decisions of 19/10) replaces the sentinel with the text ``"clear"``:

- ``null`` / omitted → no-op: the existing DB value is preserved (partial merge).
- a finite number ``>= 0`` → written (``0`` is a value, not an erase).
- ``"clear"``          → SET NULL on the DB column (NULL on a new row).
- any other text (``"d"``, ``"Clear"``, ``""``), a boolean, and any negative number — ``-1`` included, the old
  sentinel — → 422, nothing written.

``close`` is always required and must be above 0: ``0`` and ``"clear"`` are refused with 422 (use the DELETE endpoint to
remove a row).

The payloads are the JSON the data editor sends, written out: the wire contract is the subject, so no model builds them.

RED until N92 (expected failure before the cure): every case that sends ``"clear"`` (G.6.1, G.6.6, G.6.7, G.6.11) or
another text (G.6.9) — the answer model parses each value with ``Decimal(str(v))``, which raises
``decimal.InvalidOperation`` (no ValidationError): the endpoint answers 500 —, and ``-1`` (G.6.8), today the sentinel,
answered 200 with the field set NULL; G.6.10's ``"clear"`` close (500). GUARD (green before and after): the no-op of an
omitted or a null field (G.6.2), a value overwriting (G.6.3), the required close (G.6.4), a new row's NULLs (G.6.5), a
negative other than -1 (G.6.8b), a close of 0 (G.6.10's other case).

Isolation: write-scoped. Each test registers its own user and creates its own asset under a unique name, writes only that
asset's prices, and deletes the asset on the way out (its prices cascade), after a red too.

Endpoint under test: ``POST /api/v1/assets/prices`` (bulk upsert).

Spec: ``backend/app/schemas/prices.py::FAPriceWritePoint`` + ``backend/app/services/assets/price_store.py``
(``bulk_upsert_prices``, its per-field merge).

Related plans: ``plan-phase07-transaction-Part3_1_Closure_2-BlockG.prompt.md`` §G.6 (G-batch1);
``plan-phase01PluginsAssets.prompt.md``, «N92 (i) con "clear"».
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest

from backend.app.config import get_settings
from backend.app.schemas.assets.assets import FAAssetCreateItem, FABulkAssetCreateResponse
from backend.app.schemas.prices import FABulkUpsertResponse
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_info, print_section, print_success, unique_id

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0

#: The fields «clear» empties, and that a number writes or null leaves as stored.
OPTIONAL_FIELDS = ("open", "high", "low", "volume")


# ============================================================================
# Fixtures & helpers
# ============================================================================


async def create_user_and_login(client: httpx.AsyncClient) -> None:
    """Create a unique test user, register+login, persist session cookie."""
    import time  # noqa: PLC0415
    import uuid as _uuid  # noqa: PLC0415

    username = f"test_{int(time.time() * 1000)}_{_uuid.uuid4().hex[:4]}"
    email = f"{username}@test.com"
    password = "TestPass123!"

    resp = await client.post(
        f"{API_BASE}/auth/register",
        json={"username": username, "email": email, "password": password},
        timeout=TIMEOUT,
    )
    assert resp.status_code == 201, f"register failed: {resp.status_code} {resp.text}"
    login_resp = await client.post(
        f"{API_BASE}/auth/login",
        json={"username": username, "password": password},
        timeout=TIMEOUT,
    )
    assert login_resp.status_code == 200, f"login failed: {login_resp.status_code} {login_resp.text}"
    session = login_resp.cookies.get("session")
    if session:
        client.cookies.set("session", session)


@pytest.fixture(scope="module")
def test_server():
    """Start/stop test server for the whole module."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


async def _create_asset(client: httpx.AsyncClient, tag: str, currency: str = "USD") -> int:
    """Create a test asset and return its id."""
    item = FAAssetCreateItem(display_name=f"Sentinel Test {unique_id(tag)}", currency=currency)
    resp = await client.post(f"{API_BASE}/assets", json=[item.model_dump(mode="json")], timeout=TIMEOUT)
    assert resp.status_code in (200, 201), f"create asset failed: {resp.status_code} {resp.text}"
    data = FABulkAssetCreateResponse(**resp.json())
    return data.results[0].asset_id


@asynccontextmanager
async def _owned_asset(client: httpx.AsyncClient, tag: str) -> AsyncIterator[int]:
    """An asset of the test's own, deleted on the way out with its prices (they cascade), after a red too."""
    asset_id = await _create_asset(client, tag)
    try:
        yield asset_id
    finally:
        resp = await client.delete(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)
        if resp.status_code != 200:
            print_info(f"cleanup: asset {asset_id} not deleted ({resp.status_code} {resp.text[:200]})")


def _wire(day: date, close: object, **fields: object) -> dict:
    """One price point as the data editor's JSON carries it: the date, the close, and only the fields given."""
    return {"date": day.isoformat(), "close": close, **fields}


async def _upsert_prices(client: httpx.AsyncClient, asset_id: int, points: list[dict]) -> FABulkUpsertResponse:
    """Call POST /assets/prices with one asset's JSON points; the call must succeed."""
    resp = await client.post(f"{API_BASE}/assets/prices", json=[{"asset_id": asset_id, "prices": points}], timeout=TIMEOUT)
    assert resp.status_code == 200, f"upsert of {points} failed: {resp.status_code} {resp.text[:500]}"
    return FABulkUpsertResponse(**resp.json())


async def _post_prices(client: httpx.AsyncClient, asset_id: int, points: list[dict]) -> httpx.Response:
    """Call POST /assets/prices with one asset's JSON points, whatever the answer."""
    return await client.post(f"{API_BASE}/assets/prices", json=[{"asset_id": asset_id, "prices": points}], timeout=TIMEOUT)


def _refuses_the_field(resp: httpx.Response, field: str) -> bool:
    """Whether ``resp`` is a 422 one of whose errors is located on ``field`` (``body.0.prices.0.<field>``, a union
    branch's tag possibly after it)."""
    if resp.status_code != 422:
        return False
    detail = resp.json().get("detail")
    return isinstance(detail, list) and any(field in [str(part) for part in error.get("loc", [])] for error in detail if isinstance(error, dict))


async def _query_prices(client: httpx.AsyncClient, asset_id: int, start: date, end: date) -> list[dict]:
    """Query price history and return the raw ``prices`` list from items[0]."""
    resp = await client.post(
        f"{API_BASE}/assets/prices/query",
        json=[
            {
                "asset_id": asset_id,
                "date_range": {"start": start.isoformat(), "end": end.isoformat()},
            }
        ],
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, f"query failed: {resp.status_code} {resp.text}"
    items = resp.json().get("items", [])
    assert items, "query returned no items"
    return items[0].get("prices", [])


def _get_point_by_date(points: list[dict], target: date) -> dict:
    iso = target.isoformat()
    for p in points:
        if p.get("date") == iso:
            return p
    raise AssertionError(f"date {iso} not found in {[p.get('date') for p in points]}")


def _number(value: object) -> Decimal | None:
    """A stored value as the query answers it (a text, or null), as a Decimal or None."""
    return None if value is None else Decimal(str(value))


# ============================================================================
# G.6.1 — "clear" sets NULL on open
# ============================================================================
@pytest.mark.asyncio
async def test_clear_sets_null_on_open(test_server):
    """RED until N92: ``"clear"`` raises ``InvalidOperation`` in the answer model's parser: 500.

    Contract: ``"clear"`` on ``open`` for an existing row → the DB stores NULL (None in the answer); close untouched.
    """
    print_section('G.6.1 — "clear" empties open (NULL)')

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        async with _owned_asset(client, "G61") as asset_id:
            d = date.today() - timedelta(days=5)

            # Seed: open=50, close=100
            await _upsert_prices(client, asset_id, [_wire(d, "100", open="50")])
            seed = _get_point_by_date(await _query_prices(client, asset_id, d, d), d)
            assert _number(seed["open"]) == Decimal("50"), f"seed open should be 50, got {seed['open']}"
            print_info(f"seeded open={seed['open']}")

            # "clear" → SET NULL
            await _upsert_prices(client, asset_id, [_wire(d, "100", open="clear")])
            after = _get_point_by_date(await _query_prices(client, asset_id, d, d), d)
            assert after["open"] is None, f'open should be NULL after "clear", got {after["open"]}'
            assert _number(after["close"]) == Decimal("100"), "close must stay 100"
            print_success('open cleared to NULL via "clear"; close preserved')


# ============================================================================
# G.6.2 — null or omitted preserves the existing value (no-op)
# ============================================================================
@pytest.mark.asyncio
@pytest.mark.parametrize("how", ["omitted", "null"])
async def test_null_or_omitted_preserves_existing_open(test_server, how):
    """GUARD (green before and after): ``open`` omitted, or sent as ``null``, on a later upsert → the stored value is
    preserved; the close is updated."""
    print_section(f"G.6.2 — open {how} is a no-op (preserves existing)")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        async with _owned_asset(client, "G62") as asset_id:
            d = date.today() - timedelta(days=4)

            await _upsert_prices(client, asset_id, [_wire(d, "99", open="42.5")])
            second = _wire(d, "123") if how == "omitted" else _wire(d, "123", open=None)
            await _upsert_prices(client, asset_id, [second])

            after = _get_point_by_date(await _query_prices(client, asset_id, d, d), d)
            assert _number(after["open"]) == Decimal("42.5"), f"open should be preserved at 42.5 ({how} = no-op), got {after['open']}"
            assert _number(after["close"]) == Decimal("123"), f"close should be updated to 123, got {after['close']}"
            print_success(f"open preserved across an upsert with open {how}; close updated")


# ============================================================================
# G.6.3 — explicit value overwrites existing
# ============================================================================
@pytest.mark.asyncio
async def test_value_overwrites_existing_high(test_server):
    """GUARD (green before and after): an explicit non-negative value on ``high`` overwrites the stored one."""
    print_section("G.6.3 — explicit value overwrites existing")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        async with _owned_asset(client, "G63") as asset_id:
            d = date.today() - timedelta(days=3)

            await _upsert_prices(client, asset_id, [_wire(d, "95", high="100")])
            await _upsert_prices(client, asset_id, [_wire(d, "95", high="200")])

            after = _get_point_by_date(await _query_prices(client, asset_id, d, d), d)
            assert _number(after["high"]) == Decimal("200"), f"high should be overwritten to 200, got {after['high']}"
            print_success("high overwritten to 200")


# ============================================================================
# G.6.4 — close is required (Pydantic validation)
# ============================================================================
@pytest.mark.asyncio
async def test_close_is_required(test_server):
    """GUARD (green before and after): omitting ``close`` yields 422 from Pydantic (not 200, not 400)."""
    print_section("G.6.4 — close is required")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        async with _owned_asset(client, "G64") as asset_id:
            resp = await _post_prices(client, asset_id, [{"date": date.today().isoformat(), "open": "10"}])
            assert resp.status_code == 422, f"missing close should raise 422 (Pydantic validation), got {resp.status_code}: {resp.text}"
            print_success(f"missing close rejected with 422 (Pydantic); body: {resp.text[:120]}")


# ============================================================================
# G.6.5 — new row with only close keeps OHLC auxiliary fields NULL
# ============================================================================
@pytest.mark.asyncio
async def test_new_row_without_ohlc_keeps_null(test_server):
    """GUARD (green before and after): a new date upserted with only ``close`` → open/high/low/volume stay NULL."""
    print_section("G.6.5 — new row with only close keeps auxiliary fields NULL")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        async with _owned_asset(client, "G65") as asset_id:
            d = date.today() - timedelta(days=2)

            await _upsert_prices(client, asset_id, [_wire(d, "77")])

            p = _get_point_by_date(await _query_prices(client, asset_id, d, d), d)
            assert (p["open"], p["high"], p["low"], p["volume"]) == (None, None, None, None), f"open/high/low/volume should be NULL, got {p}"
            assert _number(p["close"]) == Decimal("77"), f"close should be 77, got {p['close']}"
            print_success("auxiliary OHLC fields NULL when only close is sent on a new date")


# ============================================================================
# G.6.6 — "clear" on volume
# ============================================================================
@pytest.mark.asyncio
async def test_clear_clears_volume(test_server):
    """RED until N92 (500, as G.6.1). Contract: ``"clear"`` also empties ``volume``."""
    print_section('G.6.6 — "clear" empties volume (NULL)')

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        async with _owned_asset(client, "G66") as asset_id:
            d = date.today() - timedelta(days=1)

            await _upsert_prices(client, asset_id, [_wire(d, "50", volume="1234")])
            seeded = _get_point_by_date(await _query_prices(client, asset_id, d, d), d)
            assert _number(seeded["volume"]) == Decimal("1234"), f"barrier: the seed should store a volume of 1234, got {seeded['volume']}"

            await _upsert_prices(client, asset_id, [_wire(d, "50", volume="clear")])
            p = _get_point_by_date(await _query_prices(client, asset_id, d, d), d)
            assert p["volume"] is None, f'volume should be NULL after "clear", got {p["volume"]}'
            print_success('volume cleared to NULL via "clear"')


# ============================================================================
# G.6.7 — mixed clear / preserve / value in a single batch
# ============================================================================
@pytest.mark.asyncio
async def test_mixed_clear_preserve_value_in_batch(test_server):
    """RED until N92 (500, as G.6.1). A single batch with 3 points exercising all 3 branches on ``low``:

    - day1: low="clear" → SET NULL (was 10)
    - day2: low omitted → preserve (stays 20)
    - day3: low=99      → overwrite (was 30)
    """
    print_section("G.6.7 — mixed clear/preserve/value in the same batch")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        async with _owned_asset(client, "G67") as asset_id:
            d1 = date.today() - timedelta(days=10)
            d2 = date.today() - timedelta(days=9)
            d3 = date.today() - timedelta(days=8)

            # Seed: low values 10/20/30 on three consecutive days.
            await _upsert_prices(client, asset_id, [_wire(d1, "100", low="10"), _wire(d2, "100", low="20"), _wire(d3, "100", low="30")])

            # Batch: clear / omit / value (close unchanged, just to satisfy required).
            await _upsert_prices(client, asset_id, [_wire(d1, "100", low="clear"), _wire(d2, "100"), _wire(d3, "100", low="99")])

            points = await _query_prices(client, asset_id, d1, d3)
            p1, p2, p3 = (_get_point_by_date(points, d) for d in (d1, d2, d3))
            assert p1["low"] is None, f'day1 low should be NULL ("clear"), got {p1["low"]}'
            assert _number(p2["low"]) == Decimal("20"), f"day2 low should be preserved at 20 (omitted = no-op), got {p2['low']}"
            assert _number(p3["low"]) == Decimal("99"), f"day3 low should be overwritten to 99, got {p3['low']}"
            print_success("all three branches behave correctly in a single batch")


# ============================================================================
# G.6.8 — a negative value is refused: -1 no longer clears
# ============================================================================
@pytest.mark.asyncio
async def test_minus_one_is_refused_and_nothing_is_written(test_server):
    """RED until N92: ``-1`` is the sentinel: 200, and the field is set NULL.

    Contract: ``-1`` on open, high, low or volume is a negative number: 422 naming the field, nothing written — the
    stored value stays (⚠️ breaking for a client that sends it; ``"clear"`` empties a field).
    """
    print_section("G.6.8 — -1 is a negative number: 422, nothing written")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        async with _owned_asset(client, "G68") as asset_id:
            d = date.today() - timedelta(days=6)
            seed = {"open": "11", "high": "14", "low": "9", "volume": "500"}
            await _upsert_prices(client, asset_id, [_wire(d, "12", **seed)])

            answered = {}
            for field in OPTIONAL_FIELDS:
                resp = await _post_prices(client, asset_id, [_wire(d, "12", **{field: -1})])
                answered[field] = resp.status_code if _refuses_the_field(resp, field) else f"{resp.status_code} {resp.text[:200]}"
            stored = _get_point_by_date(await _query_prices(client, asset_id, d, d), d)

            assert answered == dict.fromkeys(OPTIONAL_FIELDS, 422), f"-1 must be refused with a 422 naming its field: {answered}"
            kept = {field: _number(stored[field]) for field in OPTIONAL_FIELDS}
            assert kept == {field: Decimal(value) for field, value in seed.items()}, f"a refused -1 must write nothing: stored {kept}"
            print_success("-1 refused with 422 on every optional field; nothing written")


@pytest.mark.asyncio
async def test_a_negative_other_than_minus_one_is_refused(test_server):
    """GUARD (green before and after): ``-0.5`` on open, high, low or volume → 422 naming the field, nothing written."""
    print_section("G.6.8b — a negative value: 422, nothing written")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        async with _owned_asset(client, "G68b") as asset_id:
            d = date.today() - timedelta(days=6)
            await _upsert_prices(client, asset_id, [_wire(d, "12", open="11")])

            answered = {}
            for field in OPTIONAL_FIELDS:
                resp = await _post_prices(client, asset_id, [_wire(d, "12", **{field: -0.5})])
                answered[field] = resp.status_code if _refuses_the_field(resp, field) else f"{resp.status_code} {resp.text[:200]}"
            stored = _get_point_by_date(await _query_prices(client, asset_id, d, d), d)

            assert answered == dict.fromkeys(OPTIONAL_FIELDS, 422), f"-0.5 must be refused with a 422 naming its field: {answered}"
            assert _number(stored["open"]) == Decimal("11"), f"a refused upsert must write nothing: open {stored['open']}"
            print_success("-0.5 refused with 422 on every optional field")


# ============================================================================
# G.6.9 — a text other than "clear", or a boolean, is refused
# ============================================================================
@pytest.mark.asyncio
async def test_a_text_other_than_clear_is_refused(test_server):
    """RED until N92: ``"d"``, ``"Clear"`` and ``""`` raise ``InvalidOperation`` in the answer model's parser: 500.

    Contract: any text that is neither ``"clear"`` nor a number, and a boolean, on open/high/low/volume → 422 naming the
    field, nothing written. The marker is case-sensitive.
    """
    print_section('G.6.9 — a text other than "clear": 422, nothing written')

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        async with _owned_asset(client, "G69") as asset_id:
            d = date.today() - timedelta(days=7)
            await _upsert_prices(client, asset_id, [_wire(d, "12", open="11", volume="500")])

            sent = [(field, value) for field in OPTIONAL_FIELDS for value in ("d", "Clear", "")] + [("open", True)]
            answered = {}
            for field, value in sent:
                resp = await _post_prices(client, asset_id, [_wire(d, "12", **{field: value})])
                if not _refuses_the_field(resp, field):
                    answered[f"{field}={value!r}"] = f"{resp.status_code} {resp.text[:200]}"
            stored = _get_point_by_date(await _query_prices(client, asset_id, d, d), d)

            assert answered == {}, f'a value neither "clear" nor a number must be refused with a 422 naming its field; these were not: {answered}'
            assert (_number(stored["open"]), _number(stored["volume"])) == (Decimal("11"), Decimal("500")), f"a refused upsert must write nothing: {stored}"
            print_success('every text other than "clear" refused with 422')


# ============================================================================
# G.6.10 — close must be above 0, and is never cleared
# ============================================================================
@pytest.mark.asyncio
@pytest.mark.parametrize("close", [pytest.param(0, id="zero-guard"), pytest.param("clear", id="clear-red")])
async def test_close_must_be_above_zero(test_server, close):
    """``close`` 0 → 422 (GUARD, green before and after). ``close`` ``"clear"`` → 422 (RED until N92: 500, the answer
    model's parser raises ``InvalidOperation``): a close is never cleared; nothing written."""
    print_section(f"G.6.10 — close={close!r}: 422")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        async with _owned_asset(client, "G610") as asset_id:
            d = date.today() - timedelta(days=11)
            await _upsert_prices(client, asset_id, [_wire(d, "12")])

            resp = await _post_prices(client, asset_id, [_wire(d, close)])
            stored = _get_point_by_date(await _query_prices(client, asset_id, d, d), d)

            assert _refuses_the_field(resp, "close"), f"close={close!r} must be refused with a 422 naming close, got {resp.status_code}: {resp.text[:300]}"
            assert _number(stored["close"]) == Decimal("12"), f"a refused upsert must write nothing: close {stored['close']}"
            print_success(f"close={close!r} refused with 422")


# ============================================================================
# G.6.11 — "clear" on a new row keeps the field NULL
# ============================================================================
@pytest.mark.asyncio
async def test_clear_on_a_new_row_keeps_null(test_server):
    """RED until N92 (500, as G.6.1). Contract: ``"clear"`` on a date with no row → the row is created, the cleared
    fields NULL, the others written."""
    print_section('G.6.11 — "clear" on a new row')

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        async with _owned_asset(client, "G611") as asset_id:
            d = date.today() - timedelta(days=12)

            result = await _upsert_prices(client, asset_id, [_wire(d, "40", open="clear", high="41", low="clear", volume="0")])

            p = _get_point_by_date(await _query_prices(client, asset_id, d, d), d)
            assert result.results[0].count == 1, f"one price should be upserted: {result.results[0]}"
            assert (p["open"], _number(p["high"]), p["low"], _number(p["volume"]), _number(p["close"])) == (None, Decimal("41"), None, Decimal("0"), Decimal("40")), f"stored {p}"
            print_success('a new row with "clear" fields stored with those fields NULL; a volume of 0 written as 0')

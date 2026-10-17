"""MF-P2 — ``POST /assets/prices/period-changes`` and ``POST /fx/currencies/period-changes`` on the lane's server.

The routes' contract for their consumer (workstream X, the Assets and FX tables' Δ columns):

- login required (401 without a session);
- ``items`` in request order; an asset item is ``asset_id, as_of, currency, periods, errors``, an FX item
  ``base, quote, as_of, periods, errors``; each period ``key, days, change_ratio`` (+ ``inverse_change_ratio`` for FX),
  the ratios fractions serialised as fixed-point strings, null without a value; periods 1D … 5Y in display order;
- the numbers are the pages': the Assets page's ``computePeriodDelta`` on the dense series of
  ``POST /assets/prices/query``, the FX page's on the per-day rates of ``POST /fx/currencies/convert`` — both ported in
  ``fixtures/period_changes/page_ports.py`` and compared exactly (seeds of the form 2^a·5^b);
- base == quote is a 422;
- the bounds of a request (R13-SEC8, lot MF-P2b), each a 422: at most 10 000 assets or 1 000 pairs, at most 5 distinct
  ``as_of`` (each costs ten valued days), every ``as_of`` 1900-01-01 or later (on or before 0005-12-30 its 5Y reference,
  1825 days back, overflowed ``date``: a 500). The limits are written out, not imported: the contract the review fixed.

The services' cases (young and stale histories, currencies, missing rates, bulk order) are
``test_services/test_period_changes.py``.

Isolation. The asset is this test's (unique name, deleted with its prices). The rates are on AWG/TMT, a pair nothing
else in the repository uses, dated 1981-1987, deleted (``delete_all``) before seeding — a killed run's leftovers — and
after. The bounds' tests write nothing: their assets are an id no row can carry, their pair AWG/TMT, read only, and they
assert the status, the request's own items and the 422's ``detail``, never a value.
"""

import json
import re
import uuid
from collections.abc import Callable
from datetime import date, timedelta
from decimal import Decimal
from typing import NamedTuple

import httpx
import pytest

from backend.app.config import get_settings
from backend.test_scripts.fixtures.period_changes.page_ports import PAGE_PERIODS, asset_page_chart, asset_page_deltas, fx_page_deltas
from backend.test_scripts.fixtures.period_changes.seeds import TERMINATING_PRICES, TERMINATING_RATES, scattered_days, series
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success, unique_id

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30
ASSET_PATH = f"{API_BASE}/assets/prices/period-changes"
FX_PATH = f"{API_BASE}/fx/currencies/period-changes"

ASSET_CURRENCY = "AWG"
FX_BASE, FX_QUOTE = "AWG", "TMT"  # AWG < TMT: the stored orientation
RATE_SOURCE = "MFP2-API-TEST"

THURSDAY = date(1987, 3, 12)
FRIDAY = date(1987, 3, 13)
SATURDAY = date(1987, 3, 14)
SUNDAY = date(1987, 3, 15)  # nothing stored on Saturday or Sunday: Friday's price and rate carried
HISTORY_FIRST = date(1981, 1, 2)
RATES_FIRST = date(1981, 9, 1)
RATES_LAST = date(1987, 4, 30)
#: The range the pages load for the comparison: ``[as_of − 5Y − a bit, as_of]``.
PAGE_RANGE_DAYS = 1825 + 10
EXPECTED_PERIODS = [list(period) for period in PAGE_PERIODS]

# The bounds of a request (R13-SEC8, MF-P2b), written out.
MAX_ASSETS = 10_000
MAX_PAIRS = 1_000
MAX_AS_OF_DAYS = 5
AS_OF_FLOOR = date(1900, 1, 1)
#: An asset id no row can carry: the 10 000 items of the cap's guard value nothing, ten grouped queries that find nothing.
UNKNOWN_ASSET_ID = 2**62 - 1
#: The bounds' requests: a list at its cap values 10 000 assets, or 1 000 pairs × 10 days; room for a loaded lane (the rest keep TIMEOUT).
BULK_TIMEOUT = 120


async def create_user_and_login(client: httpx.AsyncClient) -> None:
    """Create a test user, log in, and keep the session cookie on ``client``."""
    username = f"mfp2_{unique_id('PC')}_{uuid.uuid4().hex[:6]}"
    password = "TestPass123!"
    resp = await client.post(f"{API_BASE}/auth/register", json={"username": username, "email": f"{username}@test.com", "password": password}, timeout=TIMEOUT)
    assert resp.status_code == 201, f"register: {resp.status_code} {resp.text}"
    login = await client.post(f"{API_BASE}/auth/login", json={"username": username, "password": password}, timeout=TIMEOUT)
    assert login.status_code == 200, f"login: {login.status_code} {login.text}"
    session = login.cookies.get("session")
    if session:
        client.cookies.set("session", session)


@pytest.fixture(scope="module")
def test_server():
    """Attach to the lane's shared backend (or start one when run alone)."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


def _percent(ratio: str | None) -> Decimal | None:
    return None if ratio is None else Decimal(ratio) * 100


def _history() -> dict[date, Decimal]:
    """Six years of irregular closes; Thursday ≠ Friday and nothing on the weekend, for the 1D pin."""
    days = [day for day in scattered_days(HISTORY_FIRST, FRIDAY, (3, 4, 11, 1, 6, 17, 2, 9, 5, 1)) if day not in (SATURDAY, SUNDAY)]
    prices = series(days, TERMINATING_PRICES, 7)
    prices.update({THURSDAY: Decimal("125"), FRIDAY: Decimal("160")})
    return prices


def _rates() -> dict[date, Decimal]:
    """AWG/TMT on scattered days, starting before the comparison range; none on the weekend."""
    rates = series(scattered_days(RATES_FIRST, RATES_LAST, (9, 13, 4, 21, 6)), TERMINATING_RATES, 3)
    rates.pop(SATURDAY, None)
    rates.pop(SUNDAY, None)
    return rates


async def _create_asset(client: httpx.AsyncClient) -> int:
    name = f"MF-P2 API {unique_id('PC')} {uuid.uuid4().hex[:8]}"
    resp = await client.post(f"{API_BASE}/assets", json=[{"display_name": name, "currency": ASSET_CURRENCY}], timeout=TIMEOUT)
    assert resp.status_code in (200, 201), f"create asset: {resp.status_code} {resp.text}"
    [created] = resp.json()["results"]
    assert created["success"], created
    return created["asset_id"]


async def _wipe_rates(client: httpx.AsyncClient) -> None:
    resp = await client.request("DELETE", f"{API_BASE}/fx/currencies/rate", json=[{"from": FX_BASE, "to": FX_QUOTE, "delete_all": True}], timeout=TIMEOUT)
    assert resp.status_code == 200, f"delete AWG/TMT rates: {resp.status_code} {resp.text}"


async def _assets_page(client: httpx.AsyncClient, asset_id: int, as_of: date) -> dict[str, Decimal | None]:
    """The Δ columns the Assets page computes: computePeriodDelta on ``POST /assets/prices/query``'s dense series."""
    resp = await client.post(f"{API_BASE}/assets/prices/query", json=[{"asset_id": asset_id, "date_range": {"start": (as_of - timedelta(days=PAGE_RANGE_DAYS)).isoformat(), "end": as_of.isoformat()}}], timeout=TIMEOUT)
    assert resp.status_code == 200, f"price query: {resp.status_code} {resp.text}"
    [result] = resp.json()["items"]
    prices = result["prices"]
    assert prices and prices[-1]["date"] == as_of.isoformat(), f"the series must reach {as_of}: {prices[-1:]}"
    return asset_page_deltas(asset_page_chart((date.fromisoformat(point["date"]), None if point["close"] is None else Decimal(point["close"])) for point in prices))


async def _fx_page_data(client: httpx.AsyncClient, as_of: date) -> list[tuple[date, Decimal]]:
    """The FX page's points for AWG/TMT: ``POST /fx/currencies/convert`` of 1 AWG on every day of the range."""
    request = [{"from_amount": {"code": FX_BASE, "amount": "1"}, "to": FX_QUOTE, "date_range": {"start": (as_of - timedelta(days=PAGE_RANGE_DAYS)).isoformat(), "end": as_of.isoformat()}}]
    resp = await client.post(f"{API_BASE}/fx/currencies/convert", json=request, timeout=TIMEOUT)
    assert resp.status_code == 200, f"convert: {resp.status_code} {resp.text}"
    results = resp.json()["results"]
    assert {(result["from_amount"]["code"], result["to_amount"]["code"]) for result in results} == {(FX_BASE, FX_QUOTE)}
    data = sorted((date.fromisoformat(result["conversion_date"]), Decimal(result["rate"])) for result in results)
    assert data[-1][0] == as_of, f"the conversions must reach {as_of}: {data[-1:]}"
    return data


# ============================================================================
# AUTHENTICATION AND VALIDATION
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "body"),
    [
        (ASSET_PATH, [{"asset_id": 1, "as_of": SUNDAY.isoformat()}]),
        (FX_PATH, [{"base": FX_BASE, "quote": FX_QUOTE, "as_of": SUNDAY.isoformat()}]),
    ],
    ids=["assets", "fx"],
)
async def test_period_changes_require_login(test_server, path, body):
    """Without a session both routes answer 401."""
    print_section(f"MF-P2: {path} without a session")
    async with httpx.AsyncClient() as client:
        resp = await client.post(path, json=body, timeout=TIMEOUT)
    assert resp.status_code == 401, f"expected 401 without a session, got {resp.status_code}: {resp.text}"
    print_success("401 without a session")


@pytest.mark.asyncio
@pytest.mark.parametrize(("base", "quote"), [("AWG", "AWG"), ("awg", "AWG")], ids=["same", "same-after-normalising"])
async def test_fx_period_changes_refuse_one_currency_on_both_sides(test_server, base, quote):
    """base == quote, also once the codes are upper-cased, is a 422."""
    print_section("MF-P2: FX period changes with base == quote")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        resp = await client.post(FX_PATH, json=[{"base": base, "quote": quote, "as_of": SUNDAY.isoformat()}], timeout=TIMEOUT)
    assert resp.status_code == 422, f"expected 422 for {base}/{quote}, got {resp.status_code}: {resp.text}"
    print_success(f"{base}/{quote} refused with 422")


# ============================================================================
# BOUNDS OF A REQUEST (R13-SEC8, MF-P2b)
# ============================================================================


def _asset_item(as_of: date) -> dict:
    return {"asset_id": UNKNOWN_ASSET_ID, "as_of": as_of.isoformat()}


def _fx_item(as_of: date) -> dict:
    return {"base": FX_BASE, "quote": FX_QUOTE, "as_of": as_of.isoformat()}


class _Route(NamedTuple):
    """A period-changes route: its path, the most items one request may list, one item at a given ``as_of``."""

    path: str
    cap: int
    item: Callable[[date], dict]


BOUNDED_ROUTES = [
    pytest.param(_Route(ASSET_PATH, MAX_ASSETS, _asset_item), id="assets"),
    pytest.param(_Route(FX_PATH, MAX_PAIRS, _fx_item), id="fx"),
]

#: Days before the floor: the day before it; the first day whose 5Y reference exists (``0001-01-01``) and the day before
#: it, the last whose 5Y reference overflowed ``date`` (a 500, as the first day was).
BEFORE_THE_FLOOR = [
    pytest.param(date(1899, 12, 31), id="1899-12-31"),
    pytest.param(date(5, 12, 31), id="0005-12-31"),
    pytest.param(date(5, 12, 30), id="0005-12-30"),
    pytest.param(date(1, 1, 1), id="0001-01-01"),
]


def _distinct_days(count: int) -> list[date]:
    return [SUNDAY - timedelta(days=offset) for offset in range(count)]


async def _post(client: httpx.AsyncClient, route: _Route, as_ofs: list[date]) -> httpx.Response:
    return await client.post(route.path, json=[route.item(as_of) for as_of in as_ofs], timeout=BULK_TIMEOUT)


def _refusal(resp: httpx.Response) -> list:
    """The 422's ``detail``: pydantic's error list (FastAPI drops each error's ``input``) or the route's own detail."""
    assert resp.status_code == 422, f"expected 422, got {resp.status_code}: {resp.text[:500]}"
    detail = resp.json()["detail"]
    return detail if isinstance(detail, list) else [detail]


def _names(detail: list, token: str) -> bool:
    """Whether the 422 names ``token`` (a field, a limit) as a whole word or number, wherever the route puts it."""
    return re.search(rf"(?<!\w){re.escape(token)}(?!\w|\.\d)", json.dumps(detail)) is not None


def _locs(detail: list) -> list:
    return [error.get("loc") for error in detail if isinstance(error, dict)]


@pytest.mark.asyncio
@pytest.mark.parametrize("route", BOUNDED_ROUTES)
async def test_period_changes_accept_a_list_at_its_cap(test_server, route):
    """Guard: a list of exactly the cap (10 000 assets, 1 000 pairs) is answered, one item per entry."""
    print_section(f"MF-P2b: {route.path} with {route.cap} items")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        resp = await _post(client, route, [SUNDAY] * route.cap)
    assert resp.status_code == 200, f"expected 200 for {route.cap} items, got {resp.status_code}: {resp.text[:500]}"
    items = resp.json()["items"]
    assert len(items) == route.cap, f"one answer per requested item: {len(items)} for {route.cap}"
    assert {item["as_of"] for item in items} == {SUNDAY.isoformat()}
    print_success(f"{route.cap} items answered")


@pytest.mark.asyncio
@pytest.mark.parametrize("route", BOUNDED_ROUTES)
async def test_period_changes_refuse_a_list_over_its_cap(test_server, route):
    """RED: one item over the cap (10 001 assets, 1 001 pairs) is a 422 that names the cap."""
    print_section(f"MF-P2b: {route.path} with {route.cap + 1} items")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        resp = await _post(client, route, [SUNDAY] * (route.cap + 1))
    detail = _refusal(resp)
    assert _names(detail, str(route.cap)), f"the 422 must name the cap {route.cap}: {detail}"
    print_success(f"{route.cap + 1} items refused with 422")


@pytest.mark.asyncio
@pytest.mark.parametrize("route", BOUNDED_ROUTES)
async def test_period_changes_accept_five_distinct_as_of(test_server, route):
    """Guard: five distinct ``as_of``, each asked twice, are answered in request order — the cap counts days, not items."""
    print_section(f"MF-P2b: {route.path} with {MAX_AS_OF_DAYS} distinct as_of")
    as_ofs = _distinct_days(MAX_AS_OF_DAYS) * 2
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        resp = await _post(client, route, as_ofs)
    assert resp.status_code == 200, f"expected 200 for {MAX_AS_OF_DAYS} distinct as_of, got {resp.status_code}: {resp.text[:500]}"
    assert [item["as_of"] for item in resp.json()["items"]] == [as_of.isoformat() for as_of in as_ofs]
    print_success(f"{MAX_AS_OF_DAYS} distinct as_of answered")


@pytest.mark.asyncio
@pytest.mark.parametrize("route", BOUNDED_ROUTES)
async def test_period_changes_refuse_a_sixth_distinct_as_of(test_server, route):
    """RED: six distinct ``as_of`` — sixty valued days — are a 422 that names ``as_of``."""
    print_section(f"MF-P2b: {route.path} with {MAX_AS_OF_DAYS + 1} distinct as_of")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        resp = await _post(client, route, _distinct_days(MAX_AS_OF_DAYS + 1))
    detail = _refusal(resp)
    assert _names(detail, "as_of"), f"the 422 must name as_of: {detail}"
    print_success(f"{MAX_AS_OF_DAYS + 1} distinct as_of refused with 422")


@pytest.mark.asyncio
@pytest.mark.parametrize("as_of", BEFORE_THE_FLOOR)
@pytest.mark.parametrize("route", BOUNDED_ROUTES)
async def test_period_changes_refuse_as_of_before_1900(test_server, route, as_of):
    """RED: an ``as_of`` before 1900-01-01 is a 422 on that item's ``as_of`` — on or before 0005-12-30 it was a 500."""
    print_section(f"MF-P2b: {route.path} at {as_of.isoformat()}")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        resp = await _post(client, route, [as_of])
    detail = _refusal(resp)
    assert ["body", 0, "as_of"] in _locs(detail), f"the 422 must be on the item's as_of: {detail}"
    print_success(f"as_of {as_of.isoformat()} refused with 422")


@pytest.mark.asyncio
@pytest.mark.parametrize("route", BOUNDED_ROUTES)
async def test_period_changes_accept_as_of_from_1900(test_server, route):
    """Guard: the floor itself, 1900-01-01, is answered."""
    print_section(f"MF-P2b: {route.path} at {AS_OF_FLOOR.isoformat()}")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        resp = await _post(client, route, [AS_OF_FLOOR])
    assert resp.status_code == 200, f"expected 200 at the floor, got {resp.status_code}: {resp.text[:500]}"
    assert [item["as_of"] for item in resp.json()["items"]] == [AS_OF_FLOOR.isoformat()]
    print_success("as_of 1900-01-01 answered")


# ============================================================================
# HAPPY PATHS: SHAPE AND THE PAGES' NUMBERS
# ============================================================================


def _assert_asset_item(item: dict, asset_id: int, as_of: date) -> None:
    assert set(item) == {"asset_id", "as_of", "currency", "periods", "errors"}, item.keys()
    assert (item["asset_id"], item["as_of"], item["currency"], item["errors"]) == (asset_id, as_of.isoformat(), ASSET_CURRENCY, [])
    assert [[period["key"], period["days"]] for period in item["periods"]] == EXPECTED_PERIODS
    for period in item["periods"]:
        assert set(period) == {"key", "days", "change_ratio"}, period
        assert isinstance(period["change_ratio"], str), f"six years of history: every period has a value, as a fixed-point string: {period}"


def _assert_fx_item(item: dict, base: str, quote: str, as_of: date) -> None:
    assert set(item) == {"base", "quote", "as_of", "periods", "errors"}, item.keys()
    assert (item["base"], item["quote"], item["as_of"], item["errors"]) == (base, quote, as_of.isoformat(), [])
    assert [[period["key"], period["days"]] for period in item["periods"]] == EXPECTED_PERIODS
    for period in item["periods"]:
        assert set(period) == {"key", "days", "change_ratio", "inverse_change_ratio"}, period
        assert isinstance(period["change_ratio"], str) and isinstance(period["inverse_change_ratio"], str), period


@pytest.mark.asyncio
async def test_asset_period_changes_answer_what_the_assets_page_shows(test_server):
    """One asset at two anchors: the answer's shape, the request order, every period equal to the Assets page's
    computePeriodDelta on the price query's series, and 1D exactly 0 on a Sunday (Friday's price carried)."""
    print_section("MF-P2: POST /assets/prices/period-changes")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        asset_id = await _create_asset(client)
        try:
            prices = _history()
            upsert = await client.post(f"{API_BASE}/assets/prices", json=[{"asset_id": asset_id, "prices": [{"date": day.isoformat(), "close": str(close)} for day, close in prices.items()]}], timeout=TIMEOUT)
            assert upsert.status_code == 200, f"upsert prices: {upsert.status_code} {upsert.text}"

            resp = await client.post(ASSET_PATH, json=[{"asset_id": asset_id, "as_of": SUNDAY.isoformat()}, {"asset_id": asset_id, "as_of": FRIDAY.isoformat()}], timeout=TIMEOUT)
            assert resp.status_code == 200, f"period changes: {resp.status_code} {resp.text}"
            body = resp.json()
            assert set(body) == {"items"}, body.keys()
            sunday, friday = body["items"]
            _assert_asset_item(sunday, asset_id, SUNDAY)
            _assert_asset_item(friday, asset_id, FRIDAY)

            for item, as_of in ((sunday, SUNDAY), (friday, FRIDAY)):
                page = await _assets_page(client, asset_id, as_of)
                for period in item["periods"]:
                    assert _percent(period["change_ratio"]) == page[period["key"]], f"{as_of} {period['key']}: route {period['change_ratio']}, page {page[period['key']]} %"
            assert sunday["periods"][0]["key"] == "1D" and Decimal(sunday["periods"][0]["change_ratio"]) == 0, sunday["periods"][0]
            print_success("Asset period changes: shape, order and the page's numbers")
        finally:
            await client.delete(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)


@pytest.mark.asyncio
async def test_fx_period_changes_answer_what_the_fx_page_shows(test_server):
    """A pair asked both ways: the answer's shape, the request order, each orientation equal to the FX page's
    computePeriodDelta on the rates of POST /fx/currencies/convert, and the reversed pair's orientations swapped."""
    print_section("MF-P2: POST /fx/currencies/period-changes")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        await _wipe_rates(client)
        try:
            rates = _rates()
            upsert = await client.post(f"{API_BASE}/fx/currencies/rate", json=[{"date": day.isoformat(), "base": FX_BASE, "quote": FX_QUOTE, "rate": str(rate), "source": RATE_SOURCE} for day, rate in rates.items()], timeout=TIMEOUT)
            assert upsert.status_code == 200, f"upsert rates: {upsert.status_code} {upsert.text}"
            assert upsert.json()["success_count"] == len(rates) and upsert.json()["errors"] == [], upsert.json()["errors"]

            resp = await client.post(FX_PATH, json=[{"base": FX_BASE, "quote": FX_QUOTE, "as_of": SUNDAY.isoformat()}, {"base": FX_QUOTE, "quote": FX_BASE, "as_of": SUNDAY.isoformat()}], timeout=TIMEOUT)
            assert resp.status_code == 200, f"period changes: {resp.status_code} {resp.text}"
            body = resp.json()
            assert set(body) == {"items"}, body.keys()
            forward, backward = body["items"]
            _assert_fx_item(forward, FX_BASE, FX_QUOTE, SUNDAY)
            _assert_fx_item(backward, FX_QUOTE, FX_BASE, SUNDAY)

            data = await _fx_page_data(client, SUNDAY)
            direct, inverse = fx_page_deltas(data, inverted=False), fx_page_deltas(data, inverted=True)
            for period in forward["periods"]:
                assert _percent(period["change_ratio"]) == direct[period["key"]], f"{period['key']}: route {period['change_ratio']}, page {direct[period['key']]} %"
                assert _percent(period["inverse_change_ratio"]) == inverse[period["key"]], f"{period['key']} inverted: route {period['inverse_change_ratio']}, page {inverse[period['key']]} %"
            for ahead, back in zip(forward["periods"], backward["periods"], strict=True):
                assert Decimal(back["change_ratio"]) == Decimal(ahead["inverse_change_ratio"]) and Decimal(back["inverse_change_ratio"]) == Decimal(ahead["change_ratio"]), ahead["key"]
            print_success("FX period changes: shape, order, both orientations and the page's numbers")
        finally:
            await _wipe_rates(client)

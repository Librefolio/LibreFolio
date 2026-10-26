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
- the bounds of a request, each a 422. The item counts and distinct days go through one function,
  ``schemas/common.py::period_changes_request_refusal``, whose ``detail`` is a dict with a ``code`` (coordinator's
  decision, aligned with Z-25): at most 1 000 items for both routes (Z-25's ``MAX_BULK_ITEMS``, ``bulk_too_many_items``
  with ``max_items`` and ``items`` — no longer pydantic's ``too_long`` list error, and no longer 10 000 for the assets),
  at most 5 distinct ``as_of`` and 5 distinct ``range_start`` (``period_changes_too_many_days`` with ``field``,
  ``max_days``, ``days``). ``as_of`` and ``range_start`` accept ANY day of the
  calendar, 0001-01-01 to 9999-12-31 (X5-6, D-P4 L4, developer decision: R13-SEC8's floor of 1900-01-01, set because the 5Y
  reference of an ``as_of`` on or before 0005-12-30 overflowed ``date``, is withdrawn). A period whose reference day
  (``as_of`` − ``days``) would fall before 0001-01-01 has a null ``change_ratio`` — as a change with no data —, never a 500 or
  a 422, and the other periods of the item are real. A day no ``date`` holds (year 0) is the calendar's own 422. The limits are written out, not
  imported: the contract. The function itself is tested pure in ``test_schemas/test_period_changes_bounds.py``.

The services' cases (young and stale histories, currencies, missing rates, bulk order) are
``test_services/test_period_changes.py``.

Isolation. The asset is this test's (unique name, deleted with its prices). The rates are on AWG/TMT, a pair nothing
else in the repository uses, dated 1981-1987, deleted (``delete_all``) before seeding — a killed run's leftovers — and
after. The bounds' tests write nothing: their assets are an id no row can carry, their pair AWG/TMT, read only, and they
assert the status, the request's own items and the 422's ``detail``, never a value.

X-R59 (rule 10, decision N80): an item may ask ``range_start`` (≤ ``as_of``, any day of the calendar, at most 5 distinct per
request), and its result carries ``range_change`` — null when the item asked none, so every item above now lists it, as
null. The happy paths compare it, as Decimals, with the first and last point of the series the pages load today for
``[range_start, as_of]``: ``POST /assets/prices/query`` for two assets of the test's own (one priced from before the
range, one from inside it), ``POST /fx/currencies/convert`` for GYD/HTG — another pair nothing else uses, wiped before
and after like AWG/TMT — read both ways. X5-6: the early days. The bounds' tests write nothing (an asset id no row carries, the AWG/TMT pair nothing stores before 1981): they
assert that 1899-12-31, 0005-12-30 and 0001-01-01 are answered, all nine periods null. The values are the happy paths of the
end: ``TestEarlyDays`` writes its own prices (an asset of the test's) and rates (KPW/SLE, a pair nothing else in the repository
uses, wiped before and after) in 1844-1850 and in the years 1 and 3, and compares every period with the reference day derived
with ``timedelta`` (1 825 days back is not five calendar years: 1848 had a 29 February), the last price or rate on or before it.
The bounds' refusals are only evidence next to an acceptance of the same
shape: HEAD refuses ``range_start`` itself (``extra_forbidden``, a 422 that even names the field), so each refusal test
first proves the field is accepted, and is RED on HEAD at that barrier.

X-R59, the asset page's live quote (decision c): ``POST /assets/prices/current`` takes an optional query parameter
``range_start`` (any day up to tomorrow; after it: 422); with it each result carries ``range_change`` (``reference_date``,
``change_abs``, ``change_ratio``) from the period changes' reference to the result's own price, null without it. The
asset of that test has stored prices only, so its current price is the last stored one (``db:last_known``): its
``range_change`` must be the period changes' for ``as_of`` = that price's day — the same reference, the same anchor.
"""

import uuid
from collections.abc import Callable
from datetime import date, timedelta
from decimal import Decimal
from typing import NamedTuple

import httpx
import pytest

from backend.app.config import get_settings
from backend.test_scripts.fixtures.period_changes.page_ports import PAGE_PERIODS, asset_page_chart, asset_page_deltas, fx_page_deltas
from backend.test_scripts.fixtures.period_changes.seeds import TERMINATING_PRICES, TERMINATING_RATES, first_carried_day, last_on_or_before, scattered_days, series
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

# The bounds of a request, written out: the items (Z-25's MAX_BULK_ITEMS, both routes) and the distinct days.
MAX_ITEMS = 1_000
MAX_AS_OF_DAYS = 5
#: The old floor (R13-SEC8), a landmark only: answered like every other day since X5-6.
AS_OF_FLOOR = date(1900, 1, 1)
#: An asset id no row can carry: the 1 000 items of the cap's guard value nothing, ten grouped queries that find nothing.
UNKNOWN_ASSET_ID = 2**62 - 1
#: The bounds' requests: a list at its cap values 1 000 assets, or 1 000 pairs × 10 days; room for a loaded lane (the rest keep TIMEOUT).
BULK_TIMEOUT = 120

# X-R59: the range change.
#: The most distinct ``range_start`` one request may list (the cap ``as_of`` has), written out.
MAX_RANGE_START_DAYS = 5
#: GYD < HTG: the stored orientation. Nothing else in the repository uses either currency.
RANGE_FX_BASE, RANGE_FX_QUOTE = "GYD", "HTG"
RANGE_RATE_SOURCE = "XR59-API-TEST"
#: The anchor of the range tests; Friday's price and rate are carried to it.
RANGE_AS_OF = SUNDAY
#: The asset priced from before every range start of the test.
RANGE_BEFORE_FIRST = SUNDAY - timedelta(days=600)
#: The asset priced from inside the range only.
RANGE_INSIDE_FIRST = SUNDAY - timedelta(days=200)
#: The carried range start is the first suitable day after this one: inside the first asset's history, before the second's.
RANGE_SEARCH_FROM = SUNDAY - timedelta(days=400)
#: GYD/HTG's first rate: the inside case's range starts 15 days before it, the carried case's after it.
RANGE_RATES_FIRST = SUNDAY - timedelta(days=300)
RANGE_ASSET_KEYS = {"reference_date", "change_abs", "change_ratio"}
RANGE_FX_KEYS = RANGE_ASSET_KEYS | {"inverse_change_abs", "inverse_change_ratio"}


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


async def _wipe_rates(client: httpx.AsyncClient, base: str = FX_BASE, quote: str = FX_QUOTE) -> None:
    resp = await client.request("DELETE", f"{API_BASE}/fx/currencies/rate", json=[{"from": base, "to": quote, "delete_all": True}], timeout=TIMEOUT)
    assert resp.status_code == 200, f"delete {base}/{quote} rates: {resp.status_code} {resp.text}"


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
# BOUNDS OF A REQUEST (MF-P2b, R13-SEC8; items and days aligned with Z-25)
# ============================================================================


def _asset_item(as_of: date) -> dict:
    return {"asset_id": UNKNOWN_ASSET_ID, "as_of": as_of.isoformat()}


def _fx_item(as_of: date) -> dict:
    return {"base": FX_BASE, "quote": FX_QUOTE, "as_of": as_of.isoformat()}


class _Route(NamedTuple):
    """A period-changes route: its path, one item at a given ``as_of``."""

    path: str
    item: Callable[[date], dict]


BOUNDED_ROUTES = [
    pytest.param(_Route(ASSET_PATH, _asset_item), id="assets"),
    pytest.param(_Route(FX_PATH, _fx_item), id="fx"),
]

#: Days the old floor refused, answered now: the day before it; the first day whose 5Y reference exists (``0005-12-31``)
#: and the last whose 5Y reference overflowed ``date`` (``0005-12-30``, a 500); the first day of the calendar.
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
    """The 422's ``detail`` as pydantic's error list (FastAPI drops each error's ``input``): an item's own field."""
    assert resp.status_code == 422, f"expected 422, got {resp.status_code}: {resp.text[:500]}"
    detail = resp.json()["detail"]
    assert isinstance(detail, list), f"an item's field is refused by its validation, a list of errors: {detail}"
    return detail


def _coded_refusal(resp: httpx.Response, code: str) -> dict:
    """The 422's ``detail`` as ``period_changes_request_refusal`` gives it: a dict with ``code`` and the numbers — never
    the message, whose text may change."""
    assert resp.status_code == 422, f"expected 422 {code}, got {resp.status_code}: {resp.text[:500]}"
    detail = resp.json()["detail"]
    assert isinstance(detail, dict) and detail.get("code") == code, f"expected detail.code == {code!r}: {detail}"
    assert isinstance(detail.get("message"), str), f"the refusal carries a message: {detail}"
    return detail


def _locs(detail: list) -> list:
    return [error.get("loc") for error in detail if isinstance(error, dict)]


@pytest.mark.asyncio
@pytest.mark.parametrize("route", BOUNDED_ROUTES)
async def test_period_changes_accept_a_list_at_its_cap(test_server, route):
    """Guard: a list of exactly the cap, 1 000 items, is answered on both routes, one item per entry."""
    print_section(f"Z-25 / MF-P2b: {route.path} with {MAX_ITEMS} items")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        resp = await _post(client, route, [SUNDAY] * MAX_ITEMS)
    assert resp.status_code == 200, f"expected 200 for {MAX_ITEMS} items, got {resp.status_code}: {resp.text[:500]}"
    items = resp.json()["items"]
    assert len(items) == MAX_ITEMS, f"one answer per requested item: {len(items)} for {MAX_ITEMS}"
    assert {item["as_of"] for item in items} == {SUNDAY.isoformat()}
    print_success(f"{MAX_ITEMS} items answered")


@pytest.mark.asyncio
@pytest.mark.parametrize("route", BOUNDED_ROUTES)
async def test_period_changes_refuse_a_list_over_its_cap(test_server, route):
    """RED: 1 001 items are a 422 ``bulk_too_many_items`` with ``max_items`` 1 000 and ``items`` 1 001, the price query's
    refusal (Z-25) — on HEAD the assets took 10 000 and the pairs answered pydantic's ``too_long`` list."""
    print_section(f"Z-25 / MF-P2b: {route.path} with {MAX_ITEMS + 1} items")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        resp = await _post(client, route, [SUNDAY] * (MAX_ITEMS + 1))
    detail = _coded_refusal(resp, "bulk_too_many_items")
    assert (detail["max_items"], detail["items"]) == (MAX_ITEMS, MAX_ITEMS + 1), detail
    print_success(f"{MAX_ITEMS + 1} items refused with 422 bulk_too_many_items")


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
    """RED: six distinct ``as_of`` — sixty valued days — are a 422 ``period_changes_too_many_days`` on ``as_of``, with
    ``max_days`` 5 and ``days`` 6."""
    print_section(f"MF-P2b: {route.path} with {MAX_AS_OF_DAYS + 1} distinct as_of")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        resp = await _post(client, route, _distinct_days(MAX_AS_OF_DAYS + 1))
    detail = _coded_refusal(resp, "period_changes_too_many_days")
    assert (detail["field"], detail["max_days"], detail["days"]) == ("as_of", MAX_AS_OF_DAYS, MAX_AS_OF_DAYS + 1), detail
    print_success(f"{MAX_AS_OF_DAYS + 1} distinct as_of refused with 422 period_changes_too_many_days")


@pytest.mark.asyncio
@pytest.mark.parametrize("as_of", BEFORE_THE_FLOOR)
@pytest.mark.parametrize("route", BOUNDED_ROUTES)
async def test_period_changes_accept_as_of_before_1900(test_server, route, as_of):
    """RED (X5-6): an ``as_of`` before 1900-01-01 is answered — 200, one item, its nine periods in display order, every
    change null (nothing is stored for that asset or before 1981 for that pair). On or before 0005-12-30 it was a 500 before
    the floor and a 422 on the item's ``as_of`` after it."""
    print_section(f"X5-6: {route.path} at {as_of.isoformat()}")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        resp = await _post(client, route, [as_of])
    assert resp.status_code == 200, f"expected 200 at {as_of}, got {resp.status_code}: {resp.text[:500]}"
    [item] = resp.json()["items"]
    assert item["as_of"] == as_of.isoformat()
    assert [[period["key"], period["days"]] for period in item["periods"]] == EXPECTED_PERIODS
    assert all(period["change_ratio"] is None for period in item["periods"]), item["periods"]
    print_success(f"as_of {as_of.isoformat()} answered, all periods null")


@pytest.mark.asyncio
@pytest.mark.parametrize("route", BOUNDED_ROUTES)
async def test_period_changes_still_refuse_a_day_the_calendar_has_not(test_server, route):
    """Guard: year 0 is no ``date``: a 422 on the item's ``as_of`` — the calendar's, which no rule of ours is behind."""
    print_section(f"X5-6: {route.path} at 0000-12-31")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        resp = await client.post(route.path, json=[{**route.item(SUNDAY), "as_of": "0000-12-31"}], timeout=TIMEOUT)
    detail = _refusal(resp)
    assert ["body", 0, "as_of"] in _locs(detail), f"the 422 must be on the item's as_of: {detail}"
    print_success("year 0 refused with 422")


@pytest.mark.asyncio
@pytest.mark.parametrize("route", BOUNDED_ROUTES)
async def test_period_changes_accept_as_of_from_1900(test_server, route):
    """Guard: the old floor, 1900-01-01, is answered."""
    print_section(f"MF-P2b: {route.path} at {AS_OF_FLOOR.isoformat()}")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        resp = await _post(client, route, [AS_OF_FLOOR])
    assert resp.status_code == 200, f"expected 200 at the floor, got {resp.status_code}: {resp.text[:500]}"
    assert [item["as_of"] for item in resp.json()["items"]] == [AS_OF_FLOOR.isoformat()]
    print_success("as_of 1900-01-01 answered")


async def _post_ranges(client: httpx.AsyncClient, route: _Route, range_starts: list[date]) -> httpx.Response:
    """One item per ``range_start``, all at ``RANGE_AS_OF``: one distinct ``as_of``, so only the range can break a rule."""
    return await client.post(route.path, json=[{**route.item(RANGE_AS_OF), "range_start": range_start.isoformat()} for range_start in range_starts], timeout=TIMEOUT)


def _answered(resp: httpx.Response, count: int) -> list[dict]:
    assert resp.status_code == 200, f"expected 200, got {resp.status_code}: {resp.text[:500]}"
    items = resp.json()["items"]
    assert len(items) == count and all(item["range_change"] is not None for item in items), f"an item with range_start answers a range_change object: {items}"
    return items


@pytest.mark.asyncio
@pytest.mark.parametrize("route", BOUNDED_ROUTES)
async def test_period_changes_refuse_a_sixth_distinct_range_start(test_server, route):
    """RED: five distinct ``range_start`` are answered — the barrier, which HEAD fails by refusing the field —, six are a
    422 ``period_changes_too_many_days`` on ``range_start``, with ``max_days`` 5 and ``days`` 6."""
    print_section(f"X-R59: {route.path} with {MAX_RANGE_START_DAYS + 1} distinct range_start")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        _answered(await _post_ranges(client, route, _distinct_days(MAX_RANGE_START_DAYS)), MAX_RANGE_START_DAYS)
        resp = await _post_ranges(client, route, _distinct_days(MAX_RANGE_START_DAYS + 1))
    detail = _coded_refusal(resp, "period_changes_too_many_days")
    assert (detail["field"], detail["max_days"], detail["days"]) == ("range_start", MAX_RANGE_START_DAYS, MAX_RANGE_START_DAYS + 1), detail
    print_success(f"{MAX_RANGE_START_DAYS + 1} distinct range_start refused with 422 period_changes_too_many_days")


@pytest.mark.asyncio
@pytest.mark.parametrize("route", BOUNDED_ROUTES)
async def test_period_changes_refuse_range_start_after_as_of(test_server, route):
    """RED: ``range_start`` equal to ``as_of`` is answered — the barrier —, the day after it is a 422."""
    print_section(f"X-R59: {route.path} with range_start after as_of")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        _answered(await _post_ranges(client, route, [RANGE_AS_OF]), 1)
        resp = await _post_ranges(client, route, [RANGE_AS_OF + timedelta(days=1)])
    assert resp.status_code == 422, f"expected 422 for range_start after as_of, got {resp.status_code}: {resp.text[:500]}"
    print_success("range_start after as_of refused with 422")


@pytest.mark.asyncio
@pytest.mark.parametrize("as_of", [pytest.param(date(1850, 6, 15), id="as_of-1850-06-15"), pytest.param(date(1, 1, 1), id="as_of-0001-01-01")])
@pytest.mark.parametrize("route", BOUNDED_ROUTES)
async def test_period_changes_accept_range_start_on_the_first_day_of_the_calendar(test_server, route, as_of):
    """RED (X5-6): ``range_start`` 0001-01-01 is answered (200, a ``range_change`` object) with an ``as_of`` of 1850 or of the
    same first day; with nothing stored in the range, the object is the empty one (all null)."""
    print_section(f"X5-6: {route.path} with range_start 0001-01-01, as_of {as_of.isoformat()}")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        resp = await client.post(route.path, json=[{**route.item(as_of), "range_start": date.min.isoformat()}], timeout=TIMEOUT)
    assert resp.status_code == 200, f"expected 200, got {resp.status_code}: {resp.text[:500]}"
    [item] = resp.json()["items"]
    assert item["range_change"] is not None and all(value is None for value in item["range_change"].values()), item["range_change"]
    print_success("range_start 0001-01-01 answered")


# ============================================================================
# HAPPY PATHS: SHAPE AND THE PAGES' NUMBERS
# ============================================================================


def _assert_asset_item(item: dict, asset_id: int, as_of: date) -> None:
    assert set(item) == {"asset_id", "as_of", "currency", "periods", "errors", "range_change"}, item.keys()
    assert item["range_change"] is None, f"an item without range_start asks no range change (X-R59): {item['range_change']}"
    assert (item["asset_id"], item["as_of"], item["currency"], item["errors"]) == (asset_id, as_of.isoformat(), ASSET_CURRENCY, [])
    assert [[period["key"], period["days"]] for period in item["periods"]] == EXPECTED_PERIODS
    for period in item["periods"]:
        assert set(period) == {"key", "days", "change_ratio"}, period
        assert isinstance(period["change_ratio"], str), f"six years of history: every period has a value, as a fixed-point string: {period}"


def _assert_fx_item(item: dict, base: str, quote: str, as_of: date) -> None:
    assert set(item) == {"base", "quote", "as_of", "periods", "errors", "range_change"}, item.keys()
    assert item["range_change"] is None, f"an item without range_start asks no range change (X-R59): {item['range_change']}"
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


# ============================================================================
# X-R59: THE RANGE CHANGE IS THE PAGES' FIRST AND LAST POINT
# ============================================================================


def _range_before_prices() -> dict[date, Decimal]:
    """Closes from RANGE_BEFORE_FIRST to FRIDAY: priced before every range start of the test."""
    return series(scattered_days(RANGE_BEFORE_FIRST, FRIDAY, (3, 4, 11, 1, 6, 17, 2, 9, 5, 1)), TERMINATING_PRICES, 7)


def _range_inside_prices() -> dict[date, Decimal]:
    """Closes from RANGE_INSIDE_FIRST to FRIDAY: priced from inside the range only."""
    return series(scattered_days(RANGE_INSIDE_FIRST, FRIDAY, (5, 2, 9, 4)), TERMINATING_PRICES, 5)


def _range_rates() -> dict[date, Decimal]:
    """GYD/HTG from RANGE_RATES_FIRST to FRIDAY on scattered days."""
    return series(scattered_days(RANGE_RATES_FIRST, FRIDAY, (6, 3, 11, 2, 8)), TERMINATING_RATES, 3)


async def _price_series_ends(client: httpx.AsyncClient, asset_id: int, start: date, end: date) -> tuple[dict, dict]:
    """The first and last point of ``POST /assets/prices/query``'s series over ``[start, end]``: what the Assets cards
    compute their whole-range Δ from today."""
    resp = await client.post(f"{API_BASE}/assets/prices/query", json=[{"asset_id": asset_id, "date_range": {"start": start.isoformat(), "end": end.isoformat()}}], timeout=TIMEOUT)
    assert resp.status_code == 200, f"price query: {resp.status_code} {resp.text}"
    [result] = resp.json()["items"]
    prices = result["prices"]
    assert prices and prices[-1]["date"] == end.isoformat(), f"the series must reach {end}: {prices[-1:]}"
    return prices[0], prices[-1]


async def _conversion_ends(client: httpx.AsyncClient, base: str, quote: str, start: date, end: date) -> tuple[tuple[date, Decimal], tuple[date, Decimal]]:
    """The first and last ``(day, rate)`` of ``POST /fx/currencies/convert`` of 1 ``base`` over ``[start, end]``: the
    days without a rate are dropped, so the first is the range start or the pair's first rate after it."""
    request = [{"from_amount": {"code": base, "amount": "1"}, "to": quote, "date_range": {"start": start.isoformat(), "end": end.isoformat()}}]
    resp = await client.post(f"{API_BASE}/fx/currencies/convert", json=request, timeout=TIMEOUT)
    assert resp.status_code == 200, f"convert: {resp.status_code} {resp.text}"
    data = sorted((date.fromisoformat(result["conversion_date"]), Decimal(result["rate"])) for result in resp.json()["results"])
    assert data and data[-1][0] == end, f"the conversions must reach {end}: {data[-1:]}"
    return data[0], data[-1]


@pytest.mark.asyncio
async def test_asset_range_change_is_the_price_query_first_and_last_point(test_server):
    """RED: ``range_change`` equals, as Decimals, ``last − first`` and ``last / first − 1`` of the first and last point
    of ``POST /assets/prices/query`` over ``[range_start, as_of]``, ``reference_date`` the first point's day — for an
    asset priced from before the range (first point: ``range_start``, carried) and one priced from inside it (first
    point: its first price). The same asset without ``range_start`` keeps ``range_change`` null."""
    print_section("X-R59: POST /assets/prices/period-changes with range_start")
    before_prices, inside_prices = _range_before_prices(), _range_inside_prices()
    range_start = first_carried_day(before_prices, RANGE_SEARCH_FROM, RANGE_AS_OF)
    assert range_start < RANGE_INSIDE_FIRST, f"precondition: the range starts before the second asset's history: {range_start}"
    assert inside_prices[RANGE_INSIDE_FIRST] != last_on_or_before(inside_prices, RANGE_AS_OF), "precondition: the second asset moves over the range"
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        created: list[int] = []
        try:
            for prices in (before_prices, inside_prices):
                created.append(await _create_asset(client))
                upsert = await client.post(f"{API_BASE}/assets/prices", json=[{"asset_id": created[-1], "prices": [{"date": day.isoformat(), "close": str(close)} for day, close in prices.items()]}], timeout=TIMEOUT)
                assert upsert.status_code == 200, f"upsert prices: {upsert.status_code} {upsert.text}"
            before_id, inside_id = created
            body = [
                {"asset_id": before_id, "as_of": RANGE_AS_OF.isoformat(), "range_start": range_start.isoformat()},
                {"asset_id": inside_id, "as_of": RANGE_AS_OF.isoformat(), "range_start": range_start.isoformat()},
                {"asset_id": before_id, "as_of": RANGE_AS_OF.isoformat()},
            ]

            resp = await client.post(ASSET_PATH, json=body, timeout=TIMEOUT)

            assert resp.status_code == 200, f"period changes: {resp.status_code} {resp.text}"
            before_item, inside_item, plain_item = resp.json()["items"]
            assert plain_item["range_change"] is None, plain_item["range_change"]
            assert plain_item["periods"] == before_item["periods"], "range_start leaves the periods unchanged"
            for item, asset_id, first_day in ((before_item, before_id, range_start), (inside_item, inside_id, RANGE_INSIDE_FIRST)):
                first, last = await _price_series_ends(client, asset_id, range_start, RANGE_AS_OF)
                assert first["date"] == first_day.isoformat(), f"precondition: the series of asset {asset_id} starts on {first_day}: {first}"
                change = item["range_change"]
                assert change is not None and set(change) == RANGE_ASSET_KEYS, change
                assert isinstance(change["change_abs"], str) and isinstance(change["change_ratio"], str), f"decimal strings: {change}"
                first_close, last_close = Decimal(first["close"]), Decimal(last["close"])
                assert change["reference_date"] == first["date"], change
                assert Decimal(change["change_abs"]) == last_close - first_close, f"asset {asset_id}: {change['change_abs']} vs {last_close} − {first_close}"
                assert Decimal(change["change_ratio"]) == last_close / first_close - 1, f"asset {asset_id}: {change['change_ratio']} vs {last_close} / {first_close} − 1"
            print_success("Asset range change: the price query's first and last point, carried and inside")
        finally:
            if created:
                await client.delete(f"{API_BASE}/assets", params={"asset_ids": created}, timeout=TIMEOUT)


@pytest.mark.asyncio
async def test_fx_range_change_is_the_conversions_first_and_last_rate(test_server):
    """RED: ``range_change`` equals, as Decimals, the change between the first and last rate of
    ``POST /fx/currencies/convert`` of 1 base over ``[range_start, as_of]`` — ``last − first``, ``last / first − 1`` and,
    inverted, ``1/last − 1/first``, ``first / last − 1`` —, ``reference_date`` the first rate's day: a range start with
    a rate carried from before, one before the pair's first rate, and the pair asked quote → base. The same pair without
    ``range_start`` keeps ``range_change`` null."""
    print_section("X-R59: POST /fx/currencies/period-changes with range_start")
    rates = _range_rates()
    carried = first_carried_day(rates, RANGE_RATES_FIRST, RANGE_AS_OF)
    before_rates = RANGE_RATES_FIRST - timedelta(days=15)
    cases = [
        (RANGE_FX_BASE, RANGE_FX_QUOTE, carried, carried),
        (RANGE_FX_BASE, RANGE_FX_QUOTE, before_rates, RANGE_RATES_FIRST),
        (RANGE_FX_QUOTE, RANGE_FX_BASE, carried, carried),
    ]
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        await _wipe_rates(client, RANGE_FX_BASE, RANGE_FX_QUOTE)
        try:
            upsert = await client.post(f"{API_BASE}/fx/currencies/rate", json=[{"date": day.isoformat(), "base": RANGE_FX_BASE, "quote": RANGE_FX_QUOTE, "rate": str(rate), "source": RANGE_RATE_SOURCE} for day, rate in rates.items()], timeout=TIMEOUT)
            assert upsert.status_code == 200, f"upsert rates: {upsert.status_code} {upsert.text}"
            assert upsert.json()["success_count"] == len(rates) and upsert.json()["errors"] == [], upsert.json()["errors"]
            body = [{"base": base, "quote": quote, "as_of": RANGE_AS_OF.isoformat(), "range_start": range_start.isoformat()} for base, quote, range_start, _first in cases]
            body.append({"base": RANGE_FX_BASE, "quote": RANGE_FX_QUOTE, "as_of": RANGE_AS_OF.isoformat()})

            resp = await client.post(FX_PATH, json=body, timeout=TIMEOUT)

            assert resp.status_code == 200, f"period changes: {resp.status_code} {resp.text}"
            *items, plain_item = resp.json()["items"]
            assert plain_item["range_change"] is None, plain_item["range_change"]
            assert plain_item["periods"] == items[0]["periods"], "range_start leaves the periods unchanged"
            for item, (base, quote, range_start, first_day) in zip(items, cases, strict=True):
                (start_day, first), (_end_day, last) = await _conversion_ends(client, base, quote, range_start, RANGE_AS_OF)
                assert start_day == first_day, f"precondition: the conversions of {base}/{quote} from {range_start} start on {first_day}: {start_day}"
                change = item["range_change"]
                assert change is not None and set(change) == RANGE_FX_KEYS, change
                label = f"{base}/{quote} from {range_start}"
                assert change["reference_date"] == start_day.isoformat(), (label, change)
                assert Decimal(change["change_abs"]) == last - first, (label, change, first, last)
                assert Decimal(change["change_ratio"]) == last / first - 1, (label, change, first, last)
                assert Decimal(change["inverse_change_abs"]) == 1 / last - 1 / first, (label, change, first, last)
                assert Decimal(change["inverse_change_ratio"]) == first / last - 1, (label, change, first, last)
            print_success("FX range change: the conversions' first and last rate, both orientations")
        finally:
            await _wipe_rates(client, RANGE_FX_BASE, RANGE_FX_QUOTE)


# ============================================================================
# X-R59: THE LIVE QUOTE'S RANGE CHANGE (POST /assets/prices/current?range_start=…)
# ============================================================================

CURRENT_PATH = f"{API_BASE}/assets/prices/current"


@pytest.mark.asyncio
@pytest.mark.parametrize("range_start", BEFORE_THE_FLOOR)
async def test_current_prices_accept_range_start_before_1900(test_server, range_start):
    """RED (X5-6): a ``range_start`` before 1900-01-01 — down to 0001-01-01 — is answered 200, one result for the id (no
    price: its ``range_change`` is the empty one). The old floor itself is answered too (the barrier)."""
    print_section(f"X5-6: {CURRENT_PATH}?range_start={range_start.isoformat()}")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        floor = await client.post(CURRENT_PATH, params={"range_start": AS_OF_FLOOR.isoformat()}, json=[UNKNOWN_ASSET_ID], timeout=TIMEOUT)
        assert floor.status_code == 200, f"expected 200 at the old floor, got {floor.status_code}: {floor.text[:500]}"
        resp = await client.post(CURRENT_PATH, params={"range_start": range_start.isoformat()}, json=[UNKNOWN_ASSET_ID], timeout=TIMEOUT)
    assert resp.status_code == 200, f"expected 200 for range_start {range_start}, got {resp.status_code}: {resp.text[:500]}"
    [result] = resp.json()["results"]
    assert result["asset_id"] == UNKNOWN_ASSET_ID and result["value"] is None, result
    print_success(f"range_start {range_start.isoformat()} answered")


@pytest.mark.asyncio
async def test_current_prices_refuse_range_start_after_tomorrow(test_server):
    """Guard: the ceiling stays — a ``range_start`` after tomorrow (9999-12-31) is a 422 on ``query.range_start``, while
    the first day of the calendar is answered (the barrier)."""
    print_section(f"X5-6: {CURRENT_PATH}?range_start after tomorrow")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        first = await client.post(CURRENT_PATH, params={"range_start": date.min.isoformat()}, json=[UNKNOWN_ASSET_ID], timeout=TIMEOUT)
        assert first.status_code == 200, f"expected 200 at 0001-01-01, got {first.status_code}: {first.text[:500]}"
        resp = await client.post(CURRENT_PATH, params={"range_start": date(9999, 12, 31).isoformat()}, json=[UNKNOWN_ASSET_ID], timeout=TIMEOUT)
    assert resp.status_code == 422, f"expected 422 after tomorrow, got {resp.status_code}: {resp.text[:500]}"
    assert ["query", "range_start"] in _locs(resp.json()["detail"]), resp.json()["detail"]
    print_success("range_start 9999-12-31 refused with 422")


@pytest.mark.asyncio
async def test_current_price_range_change_from_the_first_day_of_the_calendar(test_server):
    """RED (X5-6): an asset whose only stored prices are in 1850 (its current price is the last one, ``db:last_known``)
    asked with ``range_start`` 0001-01-01: nothing is stored on or before the range start, so the reference is the first
    price inside the range — 1850-01-04 — and the change is ``last − first``, ``last / first − 1`` of the stored closes."""
    print_section(f"X5-6: {CURRENT_PATH}?range_start=0001-01-01 on an 1850 asset")
    first_day, last_day, first_close, last_close = date(1850, 1, 4), date(1850, 6, 15), Decimal("100"), Decimal("160")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        asset_id = await _create_asset(client)
        try:
            prices = [{"date": first_day.isoformat(), "close": str(first_close)}, {"date": last_day.isoformat(), "close": str(last_close)}]
            upsert = await client.post(f"{API_BASE}/assets/prices", json=[{"asset_id": asset_id, "prices": prices}], timeout=TIMEOUT)
            assert upsert.status_code == 200, f"upsert prices: {upsert.status_code} {upsert.text}"

            resp = await client.post(CURRENT_PATH, params={"range_start": date.min.isoformat()}, json=[asset_id], timeout=TIMEOUT)

            assert resp.status_code == 200, f"current prices: {resp.status_code} {resp.text}"
            [result] = resp.json()["results"]
            assert (result["asset_id"], result["source"], result["as_of_date"], Decimal(result["value"])) == (asset_id, "db:last_known", last_day.isoformat(), last_close), f"precondition: the last stored price: {result}"
            change = result["range_change"]
            assert change is not None and set(change) == RANGE_ASSET_KEYS, change
            assert change["reference_date"] == first_day.isoformat(), change
            assert Decimal(change["change_abs"]) == last_close - first_close and Decimal(change["change_ratio"]) == last_close / first_close - 1, change
            print_success("Live range change from 0001-01-01: the first price inside the range")
        finally:
            await client.delete(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)


@pytest.mark.asyncio
async def test_current_prices_without_range_start_have_no_range_change(test_server):
    """Guard, green on HEAD too: without ``range_start`` no result carries a range change — priced or not."""
    print_section(f"X-R59: {CURRENT_PATH} without range_start")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        asset_id = await _create_asset(client)
        try:
            upsert = await client.post(f"{API_BASE}/assets/prices", json=[{"asset_id": asset_id, "prices": [{"date": FRIDAY.isoformat(), "close": "160"}]}], timeout=TIMEOUT)
            assert upsert.status_code == 200, f"upsert prices: {upsert.status_code} {upsert.text}"

            resp = await client.post(CURRENT_PATH, json=[asset_id, UNKNOWN_ASSET_ID], timeout=TIMEOUT)

            assert resp.status_code == 200, f"current prices: {resp.status_code} {resp.text}"
            priced, unknown = resp.json()["results"]
            assert (priced["asset_id"], priced["source"], unknown["asset_id"]) == (asset_id, "db:last_known", UNKNOWN_ASSET_ID), (priced, unknown)
            assert priced.get("range_change") is None and unknown.get("range_change") is None, (priced, unknown)
            print_success("No range_start, no range_change")
        finally:
            await client.delete(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)


@pytest.mark.asyncio
async def test_current_price_range_change_is_the_period_changes_one(test_server):
    """RED: two assets with stored prices only — their current price is the last stored one (``db:last_known``) — one
    priced from before ``range_start``, one from inside the range. With ``range_start`` each result's ``range_change``
    equals the period changes' ``range_change`` for ``as_of`` = that price's day: the same reference (``range_start``
    carried, the first price inside), the same anchor; and it is ``last − reference``, ``last / reference − 1`` of the
    stored closes. An unknown asset gets an empty ``range_change``; without ``range_start``, none."""
    print_section(f"X-R59: {CURRENT_PATH}?range_start=… against the period changes")
    before_prices, inside_prices = _range_before_prices(), _range_inside_prices()
    range_start = first_carried_day(before_prices, RANGE_SEARCH_FROM, RANGE_AS_OF)
    assert range_start < RANGE_INSIDE_FIRST, f"precondition: the range starts before the second asset's history: {range_start}"
    expected_reference = {"before": (range_start, last_on_or_before(before_prices, range_start)), "inside": (RANGE_INSIDE_FIRST, inside_prices[RANGE_INSIDE_FIRST])}
    histories = {"before": before_prices, "inside": inside_prices}
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        created: dict[str, int] = {}
        try:
            for name, prices in histories.items():
                created[name] = await _create_asset(client)
                upsert = await client.post(f"{API_BASE}/assets/prices", json=[{"asset_id": created[name], "prices": [{"date": day.isoformat(), "close": str(close)} for day, close in prices.items()]}], timeout=TIMEOUT)
                assert upsert.status_code == 200, f"upsert prices: {upsert.status_code} {upsert.text}"
            asked = [created["before"], created["inside"], UNKNOWN_ASSET_ID]

            resp = await client.post(CURRENT_PATH, params={"range_start": range_start.isoformat()}, json=asked, timeout=TIMEOUT)
            plain = await client.post(CURRENT_PATH, json=asked, timeout=TIMEOUT)

            assert resp.status_code == 200 and plain.status_code == 200, f"current prices: {resp.status_code} {resp.text[:500]} / {plain.status_code}"
            results = dict(zip(("before", "inside", "unknown"), resp.json()["results"], strict=True))
            assert [result.get("range_change") for result in plain.json()["results"]] == [None, None, None], "without range_start, no range_change"
            assert results["unknown"]["value"] is None and results["unknown"]["range_change"] == dict.fromkeys(RANGE_ASSET_KEYS), results["unknown"]

            period_items = [{"asset_id": created[name], "as_of": results[name]["as_of_date"], "range_start": range_start.isoformat()} for name in histories]
            period = await client.post(ASSET_PATH, json=period_items, timeout=TIMEOUT)
            assert period.status_code == 200, f"period changes: {period.status_code} {period.text}"

            for name, period_item in zip(histories, period.json()["items"], strict=True):
                live, prices = results[name], histories[name]
                assert (live["asset_id"], live["source"], live["currency"]) == (created[name], "db:last_known", ASSET_CURRENCY), f"precondition: no provider, the last stored price: {live}"
                assert live["as_of_date"] == max(prices).isoformat() and Decimal(live["value"]) == prices[max(prices)], f"precondition: {name} is valued at its last stored price: {live}"
                change, expected = live["range_change"], period_item["range_change"]
                assert change is not None and set(change) == RANGE_ASSET_KEYS, change
                assert change["reference_date"] == expected["reference_date"], (name, change, expected)
                assert Decimal(change["change_abs"]) == Decimal(expected["change_abs"]), (name, change, expected)
                assert Decimal(change["change_ratio"]) == Decimal(expected["change_ratio"]), (name, change, expected)
                reference_day, reference = expected_reference[name]
                anchor = Decimal(live["value"])
                assert change["reference_date"] == reference_day.isoformat(), (name, change)
                assert Decimal(change["change_abs"]) == anchor - reference, (name, change, reference, anchor)
                assert Decimal(change["change_ratio"]) == anchor / reference - 1, (name, change, reference, anchor)
            print_success("Live range change: the period changes' reference and anchor, carried and inside")
        finally:
            if created:
                await client.delete(f"{API_BASE}/assets", params={"asset_ids": list(created.values())}, timeout=TIMEOUT)


# ============================================================================
# X5-6: THE EARLY DAYS HAVE REAL VALUES (1850), AND A NULL WHERE THE REFERENCE IS BEFORE YEAR 1
# ============================================================================

#: KPW < SLE: the stored orientation. Nothing else in the repository uses either currency.
EARLY_FX_BASE, EARLY_FX_QUOTE = "KPW", "SLE"
EARLY_RATE_SOURCE = "X56-API-TEST"
EARLY_AS_OF_1850 = date(1850, 6, 15)
FIRST_DAY = date.min
YEAR_3_AS_OF = date(3, 6, 15)
YEAR_3_PREVIOUS = date(3, 6, 14)
PERIOD_DAYS = dict(PAGE_PERIODS)


def _fits(as_of: date, days: int) -> bool:
    """Whether ``as_of − days`` is a day of the calendar (on or after 0001-01-01), by ordinals."""
    return (as_of - date.min).days >= days


def _expected_ratios(stored: dict[date, Decimal], as_of: date) -> dict[str, tuple[Decimal | None, Decimal | None]]:
    """Each period's ``(change_ratio, inverse_change_ratio)`` of a series of the test's own: the value on
    ``as_of − days`` (derived with ``timedelta``) is the last stored one on or before it; None where that day is before
    0001-01-01 or nothing is stored on or before it."""
    anchor = last_on_or_before(stored, as_of)
    expected: dict[str, tuple[Decimal | None, Decimal | None]] = {}
    for key, days in PAGE_PERIODS:
        reference = last_on_or_before(stored, as_of - timedelta(days=days)) if _fits(as_of, days) else None
        expected[key] = (None, None) if reference is None or anchor is None else (anchor / reference - 1, reference / anchor - 1)
    return expected


def _early_prices() -> dict[date, Decimal]:
    """Closes from 1844 to ``EARLY_AS_OF_1850``; the 5Y reference day (1 825 days back, derived) and both its neighbours carry
    a close of their own, so a reference read on the wrong day (five calendar years back) is a different number."""
    prices = series(scattered_days(date(1844, 1, 1), EARLY_AS_OF_1850, (9, 13, 4, 21, 6)), TERMINATING_PRICES, 7)
    reference = EARLY_AS_OF_1850 - timedelta(days=1825)
    prices.update({reference - timedelta(days=1): Decimal("250"), reference: Decimal("64"), reference + timedelta(days=1): Decimal("40"), EARLY_AS_OF_1850: Decimal("160")})
    return prices


def _early_rates() -> dict[date, Decimal]:
    """KPW/SLE from 1844 to ``EARLY_AS_OF_1850``, with a rate of its own on the 5Y reference day and its neighbours."""
    rates = series(scattered_days(date(1844, 1, 1), EARLY_AS_OF_1850, (9, 13, 4, 21, 6)), TERMINATING_RATES, 3)
    reference = EARLY_AS_OF_1850 - timedelta(days=1825)
    rates.update({reference - timedelta(days=1): Decimal("5"), reference: Decimal("1.6"), reference + timedelta(days=1): Decimal("0.8"), EARLY_AS_OF_1850: Decimal("2.5")})
    return rates


def _year_3_prices() -> dict[date, Decimal]:
    """A close on the calendar's first day and on the two days before the anchor: the first day is the (carried) reference of
    every period up to 2Y, and what a 3Y or 5Y period must NOT read."""
    return {FIRST_DAY: Decimal("200"), YEAR_3_PREVIOUS: Decimal("125"), YEAR_3_AS_OF: Decimal("160")}


def _year_3_rates() -> dict[date, Decimal]:
    return {FIRST_DAY: Decimal("2"), YEAR_3_PREVIOUS: Decimal("1.25"), YEAR_3_AS_OF: Decimal("2.5")}


async def _upsert_prices(client: httpx.AsyncClient, asset_id: int, prices: dict[date, Decimal]) -> None:
    upsert = await client.post(f"{API_BASE}/assets/prices", json=[{"asset_id": asset_id, "prices": [{"date": day.isoformat(), "close": str(close)} for day, close in prices.items()]}], timeout=TIMEOUT)
    assert upsert.status_code == 200, f"upsert prices: {upsert.status_code} {upsert.text}"


async def _upsert_rates(client: httpx.AsyncClient, rates: dict[date, Decimal]) -> None:
    upsert = await client.post(f"{API_BASE}/fx/currencies/rate", json=[{"date": day.isoformat(), "base": EARLY_FX_BASE, "quote": EARLY_FX_QUOTE, "rate": str(rate), "source": EARLY_RATE_SOURCE} for day, rate in rates.items()], timeout=TIMEOUT)
    assert upsert.status_code == 200, f"upsert rates: {upsert.status_code} {upsert.text}"
    assert upsert.json()["success_count"] == len(rates) and upsert.json()["errors"] == [], upsert.json()["errors"]


def _ratio(value: str | None) -> Decimal | None:
    return None if value is None else Decimal(value)


def _assert_asset_periods(item: dict, expected: dict[str, tuple[Decimal | None, Decimal | None]]) -> None:
    assert [[period["key"], period["days"]] for period in item["periods"]] == EXPECTED_PERIODS
    assert {period["key"]: _ratio(period["change_ratio"]) for period in item["periods"]} == {key: ratios[0] for key, ratios in expected.items()}, item["periods"]


def _assert_fx_periods(item: dict, expected: dict[str, tuple[Decimal | None, Decimal | None]]) -> None:
    assert [[period["key"], period["days"]] for period in item["periods"]] == EXPECTED_PERIODS
    assert {period["key"]: (_ratio(period["change_ratio"]), _ratio(period["inverse_change_ratio"])) for period in item["periods"]} == expected, item["periods"]


@pytest.mark.asyncio
async def test_asset_period_changes_in_1850_are_real_to_the_five_year_reference(test_server):
    """RED (X5-6): an asset priced from 1844, ``as_of`` 1850-06-15 — a day the 1900 floor refused: all nine periods are
    numbers, each the change from the last close on or before ``as_of − days`` (the 5Y one 1 825 days back, 1845-06-16 by
    ``timedelta``, with a close of its own), and asking ``range_start`` 0001-01-01 gives a ``range_change`` from the asset's
    first close (nothing is stored on or before the range start) to the anchor."""
    print_section("X5-6: POST /assets/prices/period-changes in 1850")
    prices = _early_prices()
    expected = _expected_ratios(prices, EARLY_AS_OF_1850)
    assert all(ratios[0] is not None for ratios in expected.values()), "precondition: every reference of 1850 is stored"
    first_day = min(prices)
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        asset_id = await _create_asset(client)
        try:
            await _upsert_prices(client, asset_id, prices)

            resp = await client.post(ASSET_PATH, json=[{"asset_id": asset_id, "as_of": EARLY_AS_OF_1850.isoformat()}, {"asset_id": asset_id, "as_of": EARLY_AS_OF_1850.isoformat(), "range_start": FIRST_DAY.isoformat()}], timeout=TIMEOUT)

            assert resp.status_code == 200, f"period changes: {resp.status_code} {resp.text}"
            plain, ranged = resp.json()["items"]
            for item in (plain, ranged):
                assert (item["asset_id"], item["as_of"], item["currency"], item["errors"]) == (asset_id, EARLY_AS_OF_1850.isoformat(), ASSET_CURRENCY, [])
                _assert_asset_periods(item, expected)
            assert plain["range_change"] is None
            change = ranged["range_change"]
            assert change is not None and set(change) == RANGE_ASSET_KEYS, change
            assert change["reference_date"] == first_day.isoformat(), change
            anchor, first = prices[EARLY_AS_OF_1850], prices[first_day]
            assert Decimal(change["change_abs"]) == anchor - first and Decimal(change["change_ratio"]) == anchor / first - 1, change
            print_success("1850: nine real periods and a range change from 0001-01-01")
        finally:
            await client.delete(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)


@pytest.mark.asyncio
async def test_asset_period_changes_in_year_3_are_null_where_the_reference_is_before_year_1(test_server):
    """RED (X5-6): an asset priced on 0001-01-01, 0003-06-14 and 0003-06-15. For ``as_of`` 0003-06-15 the 1D change is a true
    value (160 over 125), 1W … 2Y read the carried close of the first day (160 over 200), and 3Y and 5Y — whose reference
    days are before 0001-01-01 — are null, although a close IS stored on the first day (no clamping onto it): no 500, no
    422. For ``as_of`` = 0001-01-01 every period is null (no reference exists) and ``range_start`` 0001-01-01 is the
    range's own anchor (0 change, reference_date the first day)."""
    print_section("X5-6: POST /assets/prices/period-changes in the year 3")
    prices = _year_3_prices()
    expected = _expected_ratios(prices, YEAR_3_AS_OF)
    assert expected["1D"][0] == Decimal("0.28") and expected["2Y"][0] == Decimal("-0.2") and expected["3Y"][0] is None and expected["5Y"][0] is None, f"precondition: {expected}"
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        asset_id = await _create_asset(client)
        try:
            await _upsert_prices(client, asset_id, prices)
            body = [
                {"asset_id": asset_id, "as_of": YEAR_3_AS_OF.isoformat()},
                {"asset_id": asset_id, "as_of": YEAR_3_AS_OF.isoformat(), "range_start": FIRST_DAY.isoformat()},
                {"asset_id": asset_id, "as_of": FIRST_DAY.isoformat(), "range_start": FIRST_DAY.isoformat()},
            ]

            resp = await client.post(ASSET_PATH, json=body, timeout=TIMEOUT)

            assert resp.status_code == 200, f"period changes: {resp.status_code} {resp.text}"
            plain, ranged, first = resp.json()["items"]
            _assert_asset_periods(plain, expected)
            _assert_asset_periods(ranged, expected)
            _assert_asset_periods(first, _expected_ratios(prices, FIRST_DAY))
            assert all(period["change_ratio"] is None for period in first["periods"]), first["periods"]
            assert plain["range_change"] is None
            assert ranged["range_change"]["reference_date"] == FIRST_DAY.isoformat() and Decimal(ranged["range_change"]["change_ratio"]) == Decimal("-0.2"), ranged["range_change"]
            assert first["range_change"]["reference_date"] == FIRST_DAY.isoformat() and Decimal(first["range_change"]["change_ratio"]) == 0, first["range_change"]
            print_success("Year 3: 1D … 2Y real, 3Y and 5Y null; the first day all null")
        finally:
            await client.delete(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)


@pytest.mark.asyncio
async def test_fx_period_changes_in_1850_are_real_to_the_five_year_reference(test_server):
    """RED (X5-6): the FX twin of the 1850 asset test, KPW/SLE: nine real periods in both orientations from the last rate on
    or before ``as_of − days`` (1 825 days back for 5Y), and ``range_start`` 0001-01-01 answered with the pair's first rate as
    the reference. The reversed pair swaps the orientations."""
    print_section("X5-6: POST /fx/currencies/period-changes in 1850")
    rates = _early_rates()
    expected = _expected_ratios(rates, EARLY_AS_OF_1850)
    assert all(ratios[0] is not None for ratios in expected.values()), "precondition: every reference of 1850 has a rate"
    first_day = min(rates)
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        await _wipe_rates(client, EARLY_FX_BASE, EARLY_FX_QUOTE)
        try:
            await _upsert_rates(client, rates)
            pair = {"base": EARLY_FX_BASE, "quote": EARLY_FX_QUOTE, "as_of": EARLY_AS_OF_1850.isoformat()}
            body = [pair, {**pair, "range_start": FIRST_DAY.isoformat()}, {"base": EARLY_FX_QUOTE, "quote": EARLY_FX_BASE, "as_of": EARLY_AS_OF_1850.isoformat()}]

            resp = await client.post(FX_PATH, json=body, timeout=TIMEOUT)

            assert resp.status_code == 200, f"period changes: {resp.status_code} {resp.text}"
            plain, ranged, reverse = resp.json()["items"]
            for item in (plain, ranged):
                _assert_fx_periods(item, expected)
            _assert_fx_periods(reverse, {key: (inverse, direct) for key, (direct, inverse) in expected.items()})
            assert plain["range_change"] is None
            change = ranged["range_change"]
            assert change is not None and set(change) == RANGE_FX_KEYS, change
            assert change["reference_date"] == first_day.isoformat(), change
            anchor, first = rates[EARLY_AS_OF_1850], rates[first_day]
            assert Decimal(change["change_ratio"]) == anchor / first - 1 and Decimal(change["inverse_change_ratio"]) == first / anchor - 1, change
            print_success("FX 1850: nine real periods both ways and a range change from 0001-01-01")
        finally:
            await _wipe_rates(client, EARLY_FX_BASE, EARLY_FX_QUOTE)


@pytest.mark.asyncio
async def test_fx_period_changes_in_year_3_are_null_where_the_reference_is_before_year_1(test_server):
    """RED (X5-6): the FX twin of the year-3 asset test: a rate on 0001-01-01, 0003-06-14 and 0003-06-15 gives a true 1D
    (2.5 over 1.25), 1W … 2Y from the first day's rate (2.5 over 2), 3Y and 5Y null both ways, and ``as_of`` 0001-01-01
    every period null both ways."""
    print_section("X5-6: POST /fx/currencies/period-changes in the year 3")
    rates = _year_3_rates()
    expected = _expected_ratios(rates, YEAR_3_AS_OF)
    assert expected["1D"] == (Decimal("1"), Decimal("-0.5")) and expected["2Y"] == (Decimal("0.25"), Decimal("-0.2")) and expected["3Y"] == expected["5Y"] == (None, None), f"precondition: {expected}"
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        await _wipe_rates(client, EARLY_FX_BASE, EARLY_FX_QUOTE)
        try:
            await _upsert_rates(client, rates)
            pair = {"base": EARLY_FX_BASE, "quote": EARLY_FX_QUOTE}
            body = [{**pair, "as_of": YEAR_3_AS_OF.isoformat()}, {**pair, "as_of": YEAR_3_AS_OF.isoformat(), "range_start": FIRST_DAY.isoformat()}, {**pair, "as_of": FIRST_DAY.isoformat(), "range_start": FIRST_DAY.isoformat()}]

            resp = await client.post(FX_PATH, json=body, timeout=TIMEOUT)

            assert resp.status_code == 200, f"period changes: {resp.status_code} {resp.text}"
            plain, ranged, first = resp.json()["items"]
            _assert_fx_periods(plain, expected)
            _assert_fx_periods(ranged, expected)
            _assert_fx_periods(first, dict.fromkeys(PERIOD_DAYS, (None, None)))
            assert plain["range_change"] is None
            assert ranged["range_change"]["reference_date"] == FIRST_DAY.isoformat() and Decimal(ranged["range_change"]["change_ratio"]) == Decimal("0.25"), ranged["range_change"]
            assert first["range_change"]["reference_date"] == FIRST_DAY.isoformat() and Decimal(first["range_change"]["change_ratio"]) == 0, first["range_change"]
            print_success("FX year 3: 1D … 2Y real, 3Y and 5Y null; the first day all null")
        finally:
            await _wipe_rates(client, EARLY_FX_BASE, EARLY_FX_QUOTE)

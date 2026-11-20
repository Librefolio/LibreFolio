"""BOG FX provider: the Bank of Ghana interbank rate table, a wpDataTables read through ``admin-ajax.php`` (no network, no DB, no server).

Lane 75, wave 2 (plan ``plan-phase02FxCentralBanksOndata2.prompt.md``). The page is read as a browser would: one GET
for the hidden nonce of table 40, then one POST with the DataTables server-side form and the date window in the first
column's search. The answer is JSON sent as ``text/html``; each row is ``[date, name, pair, buy, sell, mid]``, newest
first, and the plugin reads the mid. Pairs are ``USDGHS`` (GHS per unit) or ``GHSGMD`` (units per GHS); the leone is
quoted in old leones until 11/09/2026 and in new leones from then on.

Every page and answer here is synthetic, written by hand in the feed's shape with an invented nonce, never downloaded.

Isolation: PURE. ``fetch_rates`` and ``get_supported_currencies`` run whole, their module's ``httpx`` replaced for the
test by the real module whose ``AsyncClient`` answers through an ``httpx.MockTransport`` (``_route``, from
``test_rate_limit_http_providers.py``).
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from urllib.parse import parse_qs

import httpx
import pytest

from backend.app.services.fx.base import FXRateLimitedError, FXServiceError
from backend.app.services.fx_providers.bog import plugin as bog_mod
from backend.app.services.fx_providers.bog.plugin import BOGProvider
from backend.test_scripts.test_services.test_rate_limit_http_providers import _route

PAGE_URL = "https://www.bog.gov.gh/treasury-and-the-markets/historical-interbank-fx-rates/"
AJAX_URL = "https://www.bog.gov.gh/wp-admin/admin-ajax.php"
NONCE = "abc123def0"
CATALOGUE = ["AUD", "CAD", "CHF", "CNY", "DKK", "EUR", "GBP", "GHS", "GMD", "JPY", "NGN", "NOK", "NZD", "SEK", "SLE", "USD", "XOF", "ZAR"]
RANGE = (date(2026, 11, 1), date(2026, 11, 19))
D = date(2026, 11, 19)


def _page(nonce: str | None = NONCE) -> str:
    """The table page: the hidden nonce input of table 40 (invented value), or none when ``nonce`` is None."""
    field = ""
    if nonce is not None:
        field = "".join(
            [
                '<input type="hidden" id="wdtNonceFrontendServerSide_40" ',
                f'name="wdtNonceFrontendServerSide_40" value="{nonce}" />',
            ]
        )
    return f"<html><body><div class='wdt'>{field}</div></body></html>"


def _row(day: str, pair: str, mid: str, buy: str = "1.0000", sell: str = "999.0000") -> list[str]:
    """One row: buy and sell differ from the mid on purpose, so a wrong index shows."""
    return [day, "A Currency", pair, buy, sell, mid]


def _table(rows: list[list[str]]) -> dict:
    """The DataTables answer body, newest first as given."""
    return {"draw": 1, "recordsTotal": str(len(rows)), "recordsFiltered": str(len(rows)), "data": rows}


def _html(body: object, status: int = 200) -> httpx.Response:
    """A body sent as ``text/html``, like wpDataTables does even for JSON."""
    text = body if isinstance(body, str) else json.dumps(body)
    return httpx.Response(status, headers={"content-type": "text/html; charset=UTF-8"}, content=text.encode())


def _form(request: httpx.Request) -> dict[str, str]:
    """The POSTed form fields of a request, one value each."""
    return {key: values[0] for key, values in parse_qs(request.content.decode(), keep_blank_values=True).items()}


def _site(post: object | None = None, get: httpx.Response | None = None):
    """A handler: the GET gets the page (or ``get``), the POST gets ``post`` (a body, or a response)."""

    def handle(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return get if get is not None else httpx.Response(200, text=_page())
        if isinstance(post, httpx.Response):
            return post
        return _html(_table([]) if post is None else post)

    return handle


def _posts(asked: list[httpx.Request]) -> list[httpx.Request]:
    return [r for r in asked if r.method == "POST"]


def _rows_of(rows: list[list[str]]):
    return _site(_table(rows))


USD_NOW = [_row("19 Nov 2026", "USDGHS", "11.7700", buy="11.7641", sell="11.7759")]


# ── Identity and catalogue ───────────────────────────────────────────────────────


def test_bog_identity_and_constants():
    """Code, base, level, docs page, URLs, table, first day, page length, leone cut and its factor."""
    provider = BOGProvider()
    assert (provider.code, provider.base_currency, provider.warning_level) == ("BOG", "GHS", "warning")
    assert provider.docs_url == "/mkdocs/user/fx/providers/bog/"
    assert (bog_mod.PAGE_URL, bog_mod.AJAX_URL, bog_mod.TABLE_ID) == (PAGE_URL, AJAX_URL, "40")
    assert bog_mod.FIRST_DAY == date(2020, 1, 1)
    assert bog_mod.PAGE_LENGTH == 100000
    assert bog_mod.SLE_FROM == date(2026, 9, 11)
    assert bog_mod.SLL_PER_SLE == Decimal(1000)


def test_bog_pairs_map_and_discarded_pairs():
    """Thirteen per-unit pairs, four inverse ones, and the two pairs the plugin discards are absent."""
    pairs = bog_mod.PAIRS
    assert pairs["USDGHS"] == ("USD", "per_unit")
    assert pairs["GHSGMD"] == ("GMD", "inverse")
    assert pairs["GHSSLL"] == ("SLE", "inverse")
    assert sum(1 for _, kind in pairs.values() if kind == "per_unit") == 13
    assert sum(1 for _, kind in pairs.values() if kind == "inverse") == 4
    assert "WAUGHS" not in pairs and "GHSMRO" not in pairs


@pytest.mark.asyncio
async def test_bog_catalogue_is_fixed_and_needs_no_request(monkeypatch: pytest.MonkeyPatch):
    """Eighteen sorted codes including GHS, the same as ``fallback_currencies``, and not one request made."""
    asked = _route(monkeypatch, bog_mod, _rows_of(USD_NOW))

    currencies = await BOGProvider().get_supported_currencies()

    assert currencies == CATALOGUE
    assert BOGProvider().fallback_currencies == CATALOGUE
    assert asked == []


@pytest.mark.asyncio
async def test_bog_other_base_currency_is_refused(monkeypatch: pytest.MonkeyPatch):
    """``base_currency`` EUR raises ``ValueError``; GHS and None (the default) are fine."""
    _route(monkeypatch, bog_mod, _rows_of(USD_NOW))

    with pytest.raises(ValueError):
        await BOGProvider().fetch_rates(RANGE, ["USD"], base_currency="EUR")

    assert len((await BOGProvider().fetch_rates(RANGE, ["USD"], base_currency="GHS"))["USD"]) == 1
    assert len((await BOGProvider().fetch_rates(RANGE, ["USD"], base_currency=None))["USD"]) == 1


# ── The flow: GET the nonce, then one POST ───────────────────────────────────────


@pytest.mark.asyncio
async def test_bog_one_get_then_one_post_with_the_server_side_form(monkeypatch: pytest.MonkeyPatch):
    """GET of the page, then one POST to ``AJAX_URL?action=get_wdtable&table_id=40`` with the echoed nonce and six columns."""
    asked = _route(monkeypatch, bog_mod, _rows_of(USD_NOW))

    await BOGProvider().fetch_rates(RANGE, ["USD"])

    assert [r.method for r in asked] == ["GET", "POST"]
    assert str(asked[0].url) == PAGE_URL
    post = asked[1]
    assert f"{post.url.scheme}://{post.url.host}{post.url.path}" == AJAX_URL
    assert post.url.params["action"] == "get_wdtable"
    assert post.url.params["table_id"] == "40"
    form = _form(post)
    assert form["wdtNonce"] == NONCE
    assert (form["draw"], form["start"], form["length"]) == ("1", "0", "100000")
    assert (form["order[0][column]"], form["order[0][dir]"]) == ("0", "desc")
    for i in range(6):
        assert (form[f"columns[{i}][data]"], form[f"columns[{i}][searchable]"], form[f"columns[{i}][orderable]"]) == (str(i), "true", "true")
        if i:
            assert form[f"columns[{i}][search][value]"] == ""
    assert "columns[6][data]" not in form
    assert form["columns[0][search][value]"] == "01 Nov 2026|19 Nov 2026"


@pytest.mark.asyncio
async def test_bog_one_client_keeps_the_cookie_of_the_page(monkeypatch: pytest.MonkeyPatch):
    """A cookie set by the GET is sent on the POST: the whole call is one client."""

    def handle(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, text=_page(), headers={"Set-Cookie": "wp_session=abc; path=/"})
        return _html(_table(USD_NOW))

    asked = _route(monkeypatch, bog_mod, handle)

    await BOGProvider().fetch_rates(RANGE, ["USD"])

    assert "wp_session=abc" in _posts(asked)[0].headers.get("cookie", "")


@pytest.mark.parametrize("nonce", ["abc123def0", "0f9e8d7c6b"])
@pytest.mark.asyncio
async def test_bog_the_nonce_of_the_page_is_the_one_echoed(monkeypatch: pytest.MonkeyPatch, nonce: str):
    """Whatever value the page carries is the value sent back."""
    asked = _route(monkeypatch, bog_mod, _site(_table(USD_NOW), get=httpx.Response(200, text=_page(nonce))))

    await BOGProvider().fetch_rates(RANGE, ["USD"])

    assert _form(_posts(asked)[0])["wdtNonce"] == nonce


@pytest.mark.parametrize(
    ("start", "end", "expected"),
    [
        pytest.param(date(2026, 11, 1), date(2026, 11, 19), "01 Nov 2026|19 Nov 2026", id="plain"),
        pytest.param("min", date(2026, 11, 19), "01 Jan 2020|19 Nov 2026", id="min"),
        pytest.param(date(2015, 3, 5), date(2026, 5, 7), "01 Jan 2020|07 May 2026", id="before-first-day"),
        pytest.param(date(2020, 1, 1), date(2020, 1, 31), "01 Jan 2020|31 Jan 2020", id="first-day"),
        pytest.param(date(2025, 9, 5), date(2025, 12, 31), "05 Sep 2025|31 Dec 2025", id="english-months"),
    ],
)
@pytest.mark.asyncio
async def test_bog_the_window_is_english_dd_mon_yyyy_from_the_first_day(monkeypatch: pytest.MonkeyPatch, start, end, expected: str):
    """The first column's search is ``from|to``; the lower bound is never before 01/01/2020."""
    asked = _route(monkeypatch, bog_mod, _rows_of([]))

    await BOGProvider().fetch_rates((start, end), ["USD"])

    assert _form(_posts(asked)[0])["columns[0][search][value]"] == expected


# ── No request at all ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bog_nothing_servable_or_an_empty_range_asks_nothing(monkeypatch: pytest.MonkeyPatch):
    """GHS alone, a currency outside the catalogue, a start after the end, an end before the first day: no request."""
    asked = _route(monkeypatch, bog_mod, _rows_of(USD_NOW))

    assert await BOGProvider().fetch_rates(RANGE, ["GHS"]) == {}
    assert await BOGProvider().fetch_rates(RANGE, ["BRL"]) == {"BRL": []}
    assert await BOGProvider().fetch_rates((RANGE[1], RANGE[0]), ["USD"]) == {"USD": []}
    assert await BOGProvider().fetch_rates((date(2015, 1, 1), date(2019, 12, 31)), ["USD"]) == {"USD": []}
    assert await BOGProvider().fetch_rates(("min", date(2019, 12, 31)), ["USD"]) == {"USD": []}
    assert asked == []


@pytest.mark.asyncio
async def test_bog_every_asked_currency_but_ghs_is_a_key(monkeypatch: pytest.MonkeyPatch):
    """GHS is no key; a currency the bank does not publish (BRL) is a key with ``[]``; a listed one with no row too."""
    _route(monkeypatch, bog_mod, _rows_of(USD_NOW))

    rates = await BOGProvider().fetch_rates(RANGE, ["GHS", "BRL", "USD", "EUR"])

    assert set(rates) == {"BRL", "USD", "EUR"}
    assert rates["BRL"] == []
    assert rates["EUR"] == []
    assert len(rates["USD"]) == 1


# ── Values and directions ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bog_per_unit_pair_is_ghs_per_one_unit_and_uses_the_mid(monkeypatch: pytest.MonkeyPatch):
    """«USDGHS» mid 11.7700 (buy and sell differ) is ``(d, USD, GHS, 11.7700)``."""
    _route(monkeypatch, bog_mod, _rows_of(USD_NOW))

    rates = await BOGProvider().fetch_rates(RANGE, ["USD"])

    assert rates["USD"] == [(D, "USD", "GHS", Decimal("11.7700"))]


@pytest.mark.asyncio
async def test_bog_inverse_pair_is_units_per_one_ghs(monkeypatch: pytest.MonkeyPatch):
    """«GHSGMD», «GHSNGN» and «GHSXOF» are ``(d, GHS, CUR, mid)``, the value not inverted."""
    rows = [_row("19 Nov 2026", "GHSGMD", "6.1000"), _row("19 Nov 2026", "GHSNGN", "130.2500"), _row("19 Nov 2026", "GHSXOF", "50.5000")]
    _route(monkeypatch, bog_mod, _rows_of(rows))

    rates = await BOGProvider().fetch_rates(RANGE, ["GMD", "NGN", "XOF"])

    assert rates["GMD"] == [(D, "GHS", "GMD", Decimal("6.1000"))]
    assert rates["NGN"] == [(D, "GHS", "NGN", Decimal("130.2500"))]
    assert rates["XOF"] == [(D, "GHS", "XOF", Decimal("50.5000"))]


@pytest.mark.asyncio
async def test_bog_thousands_separators_are_removed(monkeypatch: pytest.MonkeyPatch):
    """«2,906.6300» reads as 2906.6300."""
    _route(monkeypatch, bog_mod, _rows_of([_row("19 Nov 2026", "GHSXOF", "2,906.6300")]))

    rates = await BOGProvider().fetch_rates(RANGE, ["XOF"])

    assert rates["XOF"] == [(D, "GHS", "XOF", Decimal("2906.6300"))]


@pytest.mark.asyncio
async def test_bog_dates_are_english_abbreviations(monkeypatch: pytest.MonkeyPatch):
    """«05 Sep 2026» and «19 Nov 2026» parse."""
    rows = [_row("19 Nov 2026", "USDGHS", "11.7"), _row("05 Sep 2026", "USDGHS", "11.2")]
    _route(monkeypatch, bog_mod, _rows_of(rows))

    rates = await BOGProvider().fetch_rates((date(2026, 9, 1), D), ["USD"])

    assert [r[0] for r in rates["USD"]] == [date(2026, 9, 5), D]


@pytest.mark.parametrize(
    ("day", "mid", "expected"),
    [
        pytest.param("10 Sep 2026", "2,109.3917", Decimal("2.1093917"), id="old-leones-divided"),
        pytest.param("11 Sep 2026", "2.1082", Decimal("2.1082"), id="new-leones-from-the-cut"),
        pytest.param("19 Nov 2026", "2.1100", Decimal("2.1100"), id="new-leones-later"),
        pytest.param("01 Jan 2026", "2,000.0000", Decimal("2.0000"), id="old-leones-earlier"),
    ],
)
@pytest.mark.asyncio
async def test_bog_leone_before_the_cut_is_divided_by_one_thousand(monkeypatch: pytest.MonkeyPatch, day: str, mid: str, expected: Decimal):
    """«GHSSLL» is old leones before 11/09/2026 (mid / 1000) and new leones from that day (inclusive), always as SLE."""
    _route(monkeypatch, bog_mod, _rows_of([_row(day, "GHSSLL", mid)]))

    rates = await BOGProvider().fetch_rates(("min", D), ["SLE"])

    assert len(rates["SLE"]) == 1
    _, source, destination, value = rates["SLE"][0]
    assert (source, destination) == ("GHS", "SLE")
    assert value == expected


@pytest.mark.asyncio
async def test_bog_the_whole_catalogue_in_one_call(monkeypatch: pytest.MonkeyPatch):
    """Every mapped pair on one day, each with its own direction."""
    rows = [_row("19 Nov 2026", pair, "2.5000") for pair in bog_mod.PAIRS]
    _route(monkeypatch, bog_mod, _rows_of(rows))

    rates = await BOGProvider().fetch_rates(RANGE, [c for c in CATALOGUE if c != "GHS"])

    assert set(rates) == set(CATALOGUE) - {"GHS"}
    for iso, kind in bog_mod.PAIRS.values():
        assert len(rates[iso]) == 1
        _, source, destination, _ = rates[iso][0]
        assert (source, destination) == ((iso, "GHS") if kind == "per_unit" else ("GHS", iso))


# ── Rows ─────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bog_pair_codes_are_stripped_before_the_lookup(monkeypatch: pytest.MonkeyPatch):
    """« USDGHS » finds its currency after ``strip()``."""
    _route(monkeypatch, bog_mod, _rows_of([_row("19 Nov 2026", " USDGHS ", "11.77")]))

    rates = await BOGProvider().fetch_rates(RANGE, ["USD"])

    assert [r[3] for r in rates["USD"]] == [Decimal("11.77")]


@pytest.mark.asyncio
async def test_bog_unknown_and_discarded_pairs_are_dropped(monkeypatch: pytest.MonkeyPatch):
    """WAUGHS, GHSMRO and a pair never seen give nothing; the known rows stay."""
    rows = [_row("19 Nov 2026", "WAUGHS", "5.5"), _row("19 Nov 2026", "GHSMRO", "5.5"), _row("19 Nov 2026", "XYZGHS", "5.5")] + USD_NOW
    _route(monkeypatch, bog_mod, _rows_of(rows))

    rates = await BOGProvider().fetch_rates(RANGE, ["USD", "EUR"])

    assert set(rates) == {"USD", "EUR"}
    assert rates["EUR"] == []
    assert len(rates["USD"]) == 1


@pytest.mark.asyncio
async def test_bog_rows_newest_first_come_out_ascending(monkeypatch: pytest.MonkeyPatch):
    """The feed is newest first; the tuples are ascending by date."""
    rows = [_row(f"{day} Nov 2026", "USDGHS", "11.7") for day in (19, 18, 17, 16)]
    _route(monkeypatch, bog_mod, _rows_of(rows))

    rates = await BOGProvider().fetch_rates(RANGE, ["USD"])

    assert [r[0] for r in rates["USD"]] == [date(2026, 11, 16), date(2026, 11, 17), date(2026, 11, 18), D]


@pytest.mark.asyncio
async def test_bog_unreadable_rows_are_skipped_and_the_others_stay(monkeypatch: pytest.MonkeyPatch):
    """A bad day and mids «0.0000», «», «n/a», a negative one lose only their row."""
    rows = [
        _row("19 Nov 2026", "USDGHS", "11.7700"),
        _row("not-a-day", "USDGHS", "11.1"),
        _row("18 Nov 2026", "USDGHS", "0.0000"),
        _row("17 Nov 2026", "USDGHS", ""),
        _row("16 Nov 2026", "USDGHS", "n/a"),
        _row("15 Nov 2026", "USDGHS", "-3"),
        _row("10 Nov 2026", "USDGHS", "11.5"),
    ]
    _route(monkeypatch, bog_mod, _rows_of(rows))

    rates = await BOGProvider().fetch_rates(RANGE, ["USD"])

    assert [(r[0], r[3]) for r in rates["USD"]] == [(date(2026, 11, 10), Decimal("11.5")), (D, Decimal("11.7700"))]


@pytest.mark.asyncio
async def test_bog_rows_outside_the_asked_range_are_skipped(monkeypatch: pytest.MonkeyPatch):
    """A day after the end and one before the start are dropped, the edges are kept."""
    rows = [_row(f"{d} 2026", "USDGHS", "11.7") for d in ("20 Nov", "19 Nov", "02 Nov", "30 Oct")]
    _route(monkeypatch, bog_mod, _rows_of(rows))

    rates = await BOGProvider().fetch_rates((date(2026, 11, 2), D), ["USD"])

    assert [r[0] for r in rates["USD"]] == [date(2026, 11, 2), D]


@pytest.mark.asyncio
async def test_bog_a_day_with_two_different_mids_is_dropped_and_equal_ones_kept_once(monkeypatch: pytest.MonkeyPatch):
    """Two mids for one day and currency drop that day for it (other currencies stay); the same mid twice is one tuple."""
    rows = [
        _row("18 Nov 2026", "USDGHS", "11.60"),
        _row("18 Nov 2026", "USDGHS", "11.70"),
        _row("18 Nov 2026", "EURGHS", "13.50"),
        _row("19 Nov 2026", "USDGHS", "11.77"),
        _row("19 Nov 2026", "USDGHS", "11.77"),
    ]
    _route(monkeypatch, bog_mod, _rows_of(rows))

    rates = await BOGProvider().fetch_rates(RANGE, ["USD", "EUR"])

    assert rates["USD"] == [(D, "USD", "GHS", Decimal("11.77"))]
    assert [r[0] for r in rates["EUR"]] == [date(2026, 11, 18)]


# ── Format errors ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bog_a_page_without_the_nonce_is_a_service_error_and_no_post(monkeypatch: pytest.MonkeyPatch):
    """The GET page has no ``wdtNonceFrontendServerSide_40``: ``FXServiceError``, no POST."""
    asked = _route(monkeypatch, bog_mod, _site(_table(USD_NOW), get=httpx.Response(200, text=_page(None))))

    with pytest.raises(FXServiceError) as refused:
        await BOGProvider().fetch_rates(RANGE, ["USD"])

    assert not isinstance(refused.value, FXRateLimitedError)
    assert _posts(asked) == []


@pytest.mark.parametrize(
    "body",
    [
        pytest.param("", id="empty"),
        pytest.param("<!DOCTYPE html><html><body>Forbidden</body></html>", id="html-page"),
        pytest.param("not json at all", id="non-json"),
        pytest.param('{"draw": 1, "recordsTotal": "0"}', id="json-without-data"),
        pytest.param('{"data": "oops"}', id="data-not-a-list"),
    ],
)
@pytest.mark.asyncio
async def test_bog_a_body_that_is_not_a_table_is_a_service_error(monkeypatch: pytest.MonkeyPatch, body: str):
    """An empty body, an HTML page, non-JSON text or JSON without a ``data`` list: ``FXServiceError``."""
    _route(monkeypatch, bog_mod, _site(_html(body)))

    with pytest.raises(FXServiceError) as refused:
        await BOGProvider().fetch_rates(RANGE, ["USD"])

    assert not isinstance(refused.value, FXRateLimitedError)


@pytest.mark.asyncio
async def test_bog_an_answer_cut_at_the_page_length_is_a_service_error(monkeypatch: pytest.MonkeyPatch):
    """``recordsFiltered`` above the rows sent means the page was cut: ``FXServiceError``, for a string or an int."""
    for filtered in ("3", 3):
        _route(monkeypatch, bog_mod, _site({**_table(USD_NOW * 2), "recordsFiltered": filtered}))

        with pytest.raises(FXServiceError, match="cut"):
            await BOGProvider().fetch_rates(RANGE, ["USD"])


@pytest.mark.parametrize("filtered", ["2", 2])
@pytest.mark.asyncio
async def test_bog_records_filtered_equal_to_the_rows_is_a_whole_answer(monkeypatch: pytest.MonkeyPatch, filtered):
    """``recordsFiltered`` equal to the rows sent, as a string or an int, is accepted."""
    rows = [_row("19 Nov 2026", "USDGHS", "11.77"), _row("18 Nov 2026", "USDGHS", "11.60")]
    _route(monkeypatch, bog_mod, _site({**_table(rows), "recordsFiltered": filtered}))

    rates = await BOGProvider().fetch_rates(RANGE, ["USD"])

    assert [r[0] for r in rates["USD"]] == [date(2026, 11, 18), D]


# ── HTTP ─────────────────────────────────────────────────────────────────────────


def _failing_on(method: str, failure):
    """A handler answering well, but where ``method`` (GET or POST) is decided by ``failure(request)``."""

    def handle(request: httpx.Request) -> httpx.Response:
        if request.method == method:
            return failure(request)
        return httpx.Response(200, text=_page()) if request.method == "GET" else _html(_table(USD_NOW))

    return handle


@pytest.mark.parametrize("method", ["GET", "POST"])
@pytest.mark.asyncio
async def test_bog_too_many_requests_is_a_rate_limit(monkeypatch: pytest.MonkeyPatch, method: str):
    """HTTP 429 on the GET or on the POST raises ``FXRateLimitedError``."""
    _route(monkeypatch, bog_mod, _failing_on(method, lambda request: httpx.Response(429, headers={"Retry-After": "30"})))

    with pytest.raises(FXRateLimitedError):
        await BOGProvider().fetch_rates(RANGE, ["USD"])


@pytest.mark.parametrize("method", ["GET", "POST"])
@pytest.mark.asyncio
async def test_bog_http_500_is_a_service_error(monkeypatch: pytest.MonkeyPatch, method: str):
    """500 on the GET or on the POST: ``FXServiceError``, not the rate-limit subclass."""
    _route(monkeypatch, bog_mod, _failing_on(method, lambda request: httpx.Response(500, text="Internal error")))

    with pytest.raises(FXServiceError) as refused:
        await BOGProvider().fetch_rates(RANGE, ["USD"])

    assert not isinstance(refused.value, FXRateLimitedError)


@pytest.mark.parametrize("method", ["GET", "POST"])
@pytest.mark.asyncio
async def test_bog_unreachable_is_a_service_error(monkeypatch: pytest.MonkeyPatch, method: str):
    """A transport failure on the GET or on the POST is ``FXServiceError``."""

    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    _route(monkeypatch, bog_mod, _failing_on(method, refuse))

    with pytest.raises(FXServiceError):
        await BOGProvider().fetch_rates(RANGE, ["USD"])

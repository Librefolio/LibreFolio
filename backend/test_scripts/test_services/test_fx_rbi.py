"""RBI FX provider: the Reserve Bank of India reference rate archive, an ASP.NET form posted a year at a time (no network, no DB, no server).

Lane 75, wave 2 (plan ``plan-phase02FxCentralBanksOndata2.prompt.md``). The archive page is read as a browser would:
one GET for the form and its hidden fields, then one POST per window of at most 365 days, each POST echoing the hidden
fields of the previous answer. The table has one column per currency, headed ``USD (INR / 1 USD)``, ``JPY (INR / 100
JPY)``: INR per N units.

Every page here is synthetic, written by hand in the page's shape with invented token strings, never downloaded.

Isolation: PURE. ``fetch_rates`` and ``get_supported_currencies`` run whole, their module's ``httpx`` replaced for the
test by the real module whose ``AsyncClient`` answers through an ``httpx.MockTransport`` (``_route``, from
``test_rate_limit_http_providers.py``). The pause between windows is zero, or a recorder, never a real sleep.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from urllib.parse import parse_qs

import httpx
import pytest

from backend.app.services.fx.base import FXRateLimitedError, FXServiceError
from backend.app.services.fx_providers.rbi import plugin as rbi_mod
from backend.app.services.fx_providers.rbi.plugin import RBIProvider
from backend.test_scripts.test_services.test_rate_limit_http_providers import _route

PAGE_URL = "https://www.rbi.org.in/Scripts/ReferenceRateArchive.aspx"
CATALOGUE = ["AED", "EUR", "GBP", "IDR", "INR", "JPY", "RUB", "USD"]
HEADERS = [
    "USD (INR / 1 USD) ",
    "GBP (INR / 1 GBP) ",
    "EUR (INR / 1 EUR) ",
    "JPY (INR / 100 JPY) ",
    "AED (INR / 1 AED) ",
    "IDR (INR / 10000 IDR) ",
    "RUB (INR / 1 RUB) ",
]
RANGE = (date(2026, 11, 1), date(2026, 11, 19))
D = date(2026, 11, 19)


@pytest.fixture(autouse=True)
def _no_pause(monkeypatch: pytest.MonkeyPatch) -> None:
    """No test waits between two windows, unless it records the pause itself."""
    monkeypatch.setattr(RBIProvider, "PAUSE_SECONDS", 0)


def _page(token: str, table: str = "", form: bool = True, extra_script: str = "") -> str:
    """A page of the archive: the form with its hidden fields (invented values built on ``token``), then ``table``."""
    if not form:
        return f"<html><body><p>{table}</p></body></html>"
    return "".join(
        [
            f"<html><head><script>{extra_script}</script></head><body>",
            '<form method="post" action="./ReferenceRateArchive.aspx" id="frmReferenceRateArchive">',
            '<input type="hidden" name="__EVENTTARGET" id="__EVENTTARGET" value=""/>',
            '<input type="hidden" name="__EVENTARGUMENT" id="__EVENTARGUMENT" value=""/>',
            f'<input type="hidden" name="__VIEWSTATE" id="__VIEWSTATE" value="vs-{token}"/>',
            f'<input type="hidden" name="__VIEWSTATEGENERATOR" id="__VIEWSTATEGENERATOR" value="gen-{token}"/>',
            f'<input type="hidden" name="__EVENTVALIDATION" id="__EVENTVALIDATION" value="ev-{token}"/>',
            '<input name="txtFromDate" type="text" id="txtFromDate" value=""/>',
            '<input name="txtToDate" type="text" id="txtToDate" value=""/>',
            "</form>",
            table,
            "</body></html>",
        ]
    )


def _table(rows: list[str], headers: list[str] | None = None, first: str = "Date") -> str:
    """The result table: a layout table first (no header cells), then the rates table."""
    head = "".join(f'<td class="tableheader"><b>{h}</b></td>' for h in [first, *(HEADERS if headers is None else headers)])
    return "".join(
        [
            '<table width="100%" border="0" class="tablebg"><tr><td>layout only</td></tr></table>',
            f'<table width="100%" border="0" class="tablebg"><tr>{head}</tr>',
            *rows,
            "</table>",
        ]
    )


def _row(day: str, *cells: str) -> str:
    """One data row: the date cell, then one cell per column (the first with the table's ``align``)."""
    values = "".join(f'<td align="right">{c}</td>' for c in cells)
    return f'<tr><td height="20" >{day}</td>{values}</tr>'


def _full(day: str, usd: str = "93.3461") -> str:
    """A row with the seven columns filled; only USD varies."""
    return _row(day, usd, "122.6577", "102.3770", "58.5200", "25.4151", "51.1244", "1.1348")


def _form(request: httpx.Request) -> dict[str, str]:
    """The POSTed form fields of a request, one value each."""
    return {key: values[0] for key, values in parse_qs(request.content.decode(), keep_blank_values=True).items()}


def _site(answers: list[httpx.Response | str], get: httpx.Response | str | None = None):
    """A handler: the GET gets ``get`` (the bare form by default), the n-th POST gets ``answers[n]``."""
    posted = {"n": 0}

    def reply(item: httpx.Response | str) -> httpx.Response:
        return item if isinstance(item, httpx.Response) else httpx.Response(200, text=item)

    def handle(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return reply(_page("get") if get is None else get)
        item = answers[min(posted["n"], len(answers) - 1)]
        posted["n"] += 1
        return reply(item)

    return handle


def _posts(asked: list[httpx.Request]) -> list[httpx.Request]:
    return [r for r in asked if r.method == "POST"]


def _pairs(rows: list[tuple]) -> list[tuple[date, Decimal]]:
    return [(r[0], r[3]) for r in rows]


def _one_day(usd: str = "93.3461") -> str:
    return _page("p1", _table([_full("19/11/2026", usd)]))


# ── Identity ─────────────────────────────────────────────────────────────────────


def test_rbi_identity_and_constants():
    """Code, base, level, docs page, URL, first day, window length and default pause."""
    provider = RBIProvider()
    assert (provider.code, provider.base_currency, provider.warning_level) == ("RBI", "INR", "warning")
    assert provider.docs_url == "/mkdocs/user/fx/providers/rbi/"
    assert rbi_mod.PAGE_URL == PAGE_URL
    assert rbi_mod.FIRST_DAY == date(1998, 8, 25)
    assert rbi_mod.WINDOW_DAYS == 365


def test_rbi_pause_is_one_second_by_default(monkeypatch: pytest.MonkeyPatch):
    """The class default, seen with the fixture's zero undone."""
    monkeypatch.undo()
    assert RBIProvider.PAUSE_SECONDS == 1.0


@pytest.mark.asyncio
async def test_rbi_catalogue_is_fixed_and_needs_no_request(monkeypatch: pytest.MonkeyPatch):
    """Eight sorted codes including INR, the same as ``fallback_currencies``, and not one request made."""
    asked = _route(monkeypatch, rbi_mod, _site([_one_day()]))

    currencies = await RBIProvider().get_supported_currencies()

    assert currencies == CATALOGUE
    assert RBIProvider().fallback_currencies == CATALOGUE
    assert asked == []


@pytest.mark.asyncio
async def test_rbi_other_base_currency_is_refused(monkeypatch: pytest.MonkeyPatch):
    """``base_currency`` EUR raises ``ValueError``; None and INR are fine."""
    _route(monkeypatch, rbi_mod, _site([_one_day()]))

    with pytest.raises(ValueError):
        await RBIProvider().fetch_rates(RANGE, ["USD"], base_currency="EUR")

    assert len((await RBIProvider().fetch_rates(RANGE, ["USD"], base_currency="INR"))["USD"]) == 1
    assert len((await RBIProvider().fetch_rates(RANGE, ["USD"], base_currency=None))["USD"]) == 1


# ── The flow: GET, then POSTs echoing the hidden fields ──────────────────────────


@pytest.mark.asyncio
async def test_rbi_one_get_then_one_post_with_the_form_of_the_page(monkeypatch: pytest.MonkeyPatch):
    """GET of the page, then one POST to it: every hidden field of the GET, the checkbox, the dates and the button."""
    asked = _route(monkeypatch, rbi_mod, _site([_one_day()]))

    await RBIProvider().fetch_rates(RANGE, ["USD"])

    assert [(r.method, str(r.url)) for r in asked] == [("GET", PAGE_URL), ("POST", PAGE_URL)]
    form = _form(asked[1])
    assert form["__VIEWSTATE"] == "vs-get"
    assert form["__VIEWSTATEGENERATOR"] == "gen-get"
    assert form["__EVENTVALIDATION"] == "ev-get"
    assert (form["__EVENTTARGET"], form["__EVENTARGUMENT"]) == ("", "")
    assert form["chkAll"] == "on"
    assert (form["txtFromDate"], form["txtToDate"]) == ("01/11/2026", "19/11/2026")
    assert form["btnSubmit"] == " GO "


@pytest.mark.asyncio
async def test_rbi_the_second_post_echoes_the_fields_of_the_first_answer(monkeypatch: pytest.MonkeyPatch):
    """Two windows: the second POST carries the tokens of the first POST's answer, not those of the GET."""
    answers = [_page("p1", _table([_full("15/01/2025")])), _page("p2", _table([_full("15/01/2026")]))]
    asked = _route(monkeypatch, rbi_mod, _site(answers))

    await RBIProvider().fetch_rates((date(2025, 1, 1), date(2026, 1, 31)), ["USD"])

    posts = _posts(asked)
    assert len(posts) == 2
    assert _form(posts[0])["__VIEWSTATE"] == "vs-get"
    assert _form(posts[1])["__VIEWSTATE"] == "vs-p1"
    assert _form(posts[1])["__EVENTVALIDATION"] == "ev-p1"


@pytest.mark.asyncio
async def test_rbi_one_client_keeps_the_session_cookie(monkeypatch: pytest.MonkeyPatch):
    """A cookie set by the GET is sent on the POSTs: the whole call is one client."""

    def handle(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, text=_page("get"), headers={"Set-Cookie": "ASP.NET_SessionId=abc; path=/"})
        return httpx.Response(200, text=_one_day())

    asked = _route(monkeypatch, rbi_mod, handle)

    await RBIProvider().fetch_rates(RANGE, ["USD"])

    assert "ASP.NET_SessionId=abc" in _posts(asked)[0].headers.get("cookie", "")


# ── Windows and pauses ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rbi_a_short_range_over_new_year_is_one_window(monkeypatch: pytest.MonkeyPatch):
    """14 days across the year end: one POST, asked with the exact range."""
    asked = _route(monkeypatch, rbi_mod, _site([_one_day()]))

    await RBIProvider().fetch_rates((date(2025, 12, 25), date(2026, 1, 7)), ["USD"])

    posts = _posts(asked)
    assert len(posts) == 1
    assert (_form(posts[0])["txtFromDate"], _form(posts[0])["txtToDate"]) == ("25/12/2025", "07/01/2026")


@pytest.mark.asyncio
async def test_rbi_two_years_and_a_day_are_three_windows_with_two_pauses(monkeypatch: pytest.MonkeyPatch):
    """Windows of 365 days from the start; the pause comes between two POSTs only, never before the first."""
    monkeypatch.setattr(RBIProvider, "PAUSE_SECONDS", 1.0)
    slept: list[float] = []

    async def record(seconds: float) -> None:
        slept.append(seconds)

    monkeypatch.setattr(rbi_mod.asyncio, "sleep", record)
    asked = _route(monkeypatch, rbi_mod, _site([_page("p", _table([]))]))

    await RBIProvider().fetch_rates((date(2023, 1, 1), date(2024, 12, 31)), ["USD"])

    dates = [(_form(r)["txtFromDate"], _form(r)["txtToDate"]) for r in _posts(asked)]
    assert dates == [("01/01/2023", "31/12/2023"), ("01/01/2024", "30/12/2024"), ("31/12/2024", "31/12/2024")]
    assert slept == [1.0, 1.0]


@pytest.mark.asyncio
async def test_rbi_one_window_needs_no_pause(monkeypatch: pytest.MonkeyPatch):
    """A single POST is neither preceded nor followed by a pause."""
    monkeypatch.setattr(RBIProvider, "PAUSE_SECONDS", 1.0)
    slept: list[float] = []

    async def record(seconds: float) -> None:
        slept.append(seconds)

    monkeypatch.setattr(rbi_mod.asyncio, "sleep", record)
    _route(monkeypatch, rbi_mod, _site([_one_day()]))

    await RBIProvider().fetch_rates(RANGE, ["USD"])

    assert slept == []


@pytest.mark.parametrize("start", ["min", date(1990, 1, 1)])
@pytest.mark.asyncio
async def test_rbi_min_and_an_earlier_start_begin_at_the_first_day(monkeypatch: pytest.MonkeyPatch, start):
    """``"min"`` and any start before 25/08/1998 ask from 25/08/1998."""
    asked = _route(monkeypatch, rbi_mod, _site([_page("p", _table([]))]))

    await RBIProvider().fetch_rates((start, date(1998, 12, 31)), ["USD"])

    assert _form(_posts(asked)[0])["txtFromDate"] == "25/08/1998"


# ── No request at all ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rbi_nothing_servable_or_an_empty_range_asks_nothing(monkeypatch: pytest.MonkeyPatch):
    """INR alone, a currency outside the catalogue alone, a start after the end, an end before the first day: no request."""
    asked = _route(monkeypatch, rbi_mod, _site([_one_day()]))

    assert await RBIProvider().fetch_rates(RANGE, ["INR"]) == {}
    assert await RBIProvider().fetch_rates(RANGE, ["BRL"]) == {"BRL": []}
    assert await RBIProvider().fetch_rates((RANGE[1], RANGE[0]), ["USD"]) == {"USD": []}
    assert await RBIProvider().fetch_rates((date(1990, 1, 1), date(1998, 8, 24)), ["USD"]) == {"USD": []}
    assert await RBIProvider().fetch_rates(("min", date(1998, 8, 24)), ["USD"]) == {"USD": []}
    assert asked == []


# ── Values and directions ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rbi_per_unit_column_is_inr_per_one_unit(monkeypatch: pytest.MonkeyPatch):
    """«USD (INR / 1 USD) 93.3461» is ``(d, USD, INR, 93.3461)``."""
    _route(monkeypatch, rbi_mod, _site([_one_day()]))

    rates = await RBIProvider().fetch_rates(RANGE, ["USD"])

    assert rates["USD"] == [(D, "USD", "INR", Decimal("93.3461"))]


@pytest.mark.asyncio
async def test_rbi_the_unit_is_read_from_the_header(monkeypatch: pytest.MonkeyPatch):
    """JPY per 100 and IDR per 10000 are divided by the unit of their own header."""
    _route(monkeypatch, rbi_mod, _site([_one_day()]))

    rates = await RBIProvider().fetch_rates(RANGE, ["JPY", "IDR", "EUR", "AED", "GBP", "RUB"])

    assert rates["JPY"] == [(D, "JPY", "INR", Decimal("0.5852"))]
    assert rates["IDR"] == [(D, "IDR", "INR", Decimal("0.00511244"))]
    assert rates["EUR"][0][3] == Decimal("102.3770")
    assert rates["AED"][0][3] == Decimal("25.4151")
    assert rates["GBP"][0][3] == Decimal("122.6577")
    assert rates["RUB"][0][3] == Decimal("1.1348")


@pytest.mark.asyncio
async def test_rbi_only_the_asked_currencies_come_out_and_inr_is_no_key(monkeypatch: pytest.MonkeyPatch):
    """Asking INR, USD and BRL gives the keys USD and BRL; BRL, outside the catalogue, is empty."""
    _route(monkeypatch, rbi_mod, _site([_one_day()]))

    rates = await RBIProvider().fetch_rates(RANGE, ["INR", "USD", "BRL"])

    assert set(rates) == {"USD", "BRL"}
    assert rates["BRL"] == []
    assert len(rates["USD"]) == 1


@pytest.mark.asyncio
async def test_rbi_rows_newest_first_come_out_ascending(monkeypatch: pytest.MonkeyPatch):
    """The page lists the newest day first; the tuples are ascending by date."""
    rows = [_full(f"{day}/11/2026") for day in (19, 18, 17, 16)]
    _route(monkeypatch, rbi_mod, _site([_page("p", _table(rows))]))

    rates = await RBIProvider().fetch_rates(RANGE, ["USD"])

    assert [r[0] for r in rates["USD"]] == [date(2026, 11, 16), date(2026, 11, 17), date(2026, 11, 18), date(2026, 11, 19)]


@pytest.mark.asyncio
async def test_rbi_a_currency_with_no_values_is_an_empty_key(monkeypatch: pytest.MonkeyPatch):
    """Old rows have no AED: the key is there with ``[]``."""
    rows = [_row("19/11/2002", "48.0000", "75.0000", "47.0000", "40.0000", "", "", "")]
    _route(monkeypatch, rbi_mod, _site([_page("p", _table(rows))]))

    rates = await RBIProvider().fetch_rates((date(2002, 11, 1), date(2002, 11, 30)), ["USD", "AED"])

    assert len(rates["USD"]) == 1
    assert rates["AED"] == []


@pytest.mark.asyncio
async def test_rbi_a_bad_cell_loses_only_that_cell(monkeypatch: pytest.MonkeyPatch):
    """An empty cell, «0.0000» and a text lose their own currency only; the other cells of the row stay."""
    rows = [_row("19/11/2026", "93.3461", "122.6577", "0.0000", "", "abc", "51.1244", "1.1348")]
    _route(monkeypatch, rbi_mod, _site([_page("p", _table(rows))]))

    rates = await RBIProvider().fetch_rates(RANGE, ["USD", "GBP", "EUR", "JPY", "AED", "IDR", "RUB"])

    assert [len(rates[c]) for c in ("USD", "GBP", "IDR", "RUB")] == [1, 1, 1, 1]
    assert [rates[c] for c in ("EUR", "JPY", "AED")] == [[], [], []]


@pytest.mark.asyncio
async def test_rbi_a_row_with_an_unreadable_date_is_skipped(monkeypatch: pytest.MonkeyPatch):
    """«not-a-day» loses its row; the neighbours stay."""
    rows = [_full("19/11/2026"), _full("not-a-day", "1.0"), _full("18/11/2026")]
    _route(monkeypatch, rbi_mod, _site([_page("p", _table(rows))]))

    rates = await RBIProvider().fetch_rates(RANGE, ["USD"])

    assert [r[0] for r in rates["USD"]] == [date(2026, 11, 18), D]


@pytest.mark.asyncio
async def test_rbi_sunday_rows_are_skipped_and_saturdays_kept(monkeypatch: pytest.MonkeyPatch):
    """11/10/1998 is a Sunday and goes; 23/09/2000 is a Saturday and stays."""
    sunday = _page("p", _table([_row("11/10/1998", "42.5000", "70.0000", "0.0000", "", "", "", "")]))
    saturday = _page("p", _table([_row("23/09/2000", "46.5000", "68.0000", "42.0000", "", "", "", "")]))
    _route(monkeypatch, rbi_mod, _site([sunday]))
    old = await RBIProvider().fetch_rates((date(1998, 10, 1), date(1998, 10, 31)), ["USD"])
    _route(monkeypatch, rbi_mod, _site([saturday]))
    kept = await RBIProvider().fetch_rates((date(2000, 9, 1), date(2000, 9, 30)), ["USD"])

    assert old["USD"] == []
    assert kept["USD"] == [(date(2000, 9, 23), "USD", "INR", Decimal("46.5000"))]


@pytest.mark.asyncio
async def test_rbi_rows_outside_the_asked_range_are_skipped(monkeypatch: pytest.MonkeyPatch):
    """A day after the end and one before the start are dropped, the edges are kept."""
    rows = [_full("20/11/2026"), _full("19/11/2026"), _full("02/11/2026"), _full("30/10/2026")]
    _route(monkeypatch, rbi_mod, _site([_page("p", _table(rows))]))

    rates = await RBIProvider().fetch_rates((date(2026, 11, 2), D), ["USD"])

    assert [r[0] for r in rates["USD"]] == [date(2026, 11, 2), D]


@pytest.mark.asyncio
async def test_rbi_a_date_with_two_values_is_dropped_and_equal_values_kept_once(monkeypatch: pytest.MonkeyPatch):
    """Across two windows: one day with two USD values is dropped for USD (GBP stays); a day repeated with the same value is kept once."""
    first = _page("p1", _table([_full("20/06/2025", "90.0"), _full("21/06/2025", "91.0")]))
    second = _page("p2", _table([_full("20/06/2025", "95.0"), _full("21/06/2025", "91.0")]))
    _route(monkeypatch, rbi_mod, _site([first, second]))

    rates = await RBIProvider().fetch_rates((date(2025, 1, 1), date(2026, 6, 30)), ["USD", "GBP"])

    assert _pairs(rates["USD"]) == [(date(2025, 6, 21), Decimal("91.0"))]
    assert [r[0] for r in rates["GBP"]] == [date(2025, 6, 20), date(2025, 6, 21)]


# ── Empty answers ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rbi_an_empty_window_gives_no_rows_and_the_next_post_still_happens(monkeypatch: pytest.MonkeyPatch):
    """The form without a result table (the word ``tableheader`` only inside a script) is no rows; the next POST uses its tokens."""
    empty = _page("empty", extra_script="var cls = 'tableheader';")
    asked = _route(monkeypatch, rbi_mod, _site([empty, _page("p2", _table([_full("15/01/2026")]))]))

    rates = await RBIProvider().fetch_rates((date(2025, 1, 1), date(2026, 1, 31)), ["USD"])

    posts = _posts(asked)
    assert len(posts) == 2
    assert _form(posts[1])["__VIEWSTATE"] == "vs-empty"
    assert [r[0] for r in rates["USD"]] == [date(2026, 1, 15)]


# ── Format errors ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "page",
    [
        pytest.param("<html><body>Access denied</body></html>", id="no-form"),
        pytest.param(
            '<html><body><form id="frmReferenceRateArchive"><input name="txtFromDate"/></form></body></html>',
            id="no-viewstate",
        ),
    ],
)
@pytest.mark.asyncio
async def test_rbi_a_get_page_that_is_not_the_form_is_a_service_error(monkeypatch: pytest.MonkeyPatch, page: str):
    """No form, or no ``__VIEWSTATE``, on the GET: ``FXServiceError`` and no POST."""
    asked = _route(monkeypatch, rbi_mod, _site([_one_day()], get=page))

    with pytest.raises(FXServiceError) as refused:
        await RBIProvider().fetch_rates(RANGE, ["USD"])

    assert not isinstance(refused.value, FXRateLimitedError)
    assert _posts(asked) == []


@pytest.mark.asyncio
async def test_rbi_a_post_answer_without_the_form_is_a_service_error(monkeypatch: pytest.MonkeyPatch):
    """The POST answered with a page without ``txtFromDate``: ``FXServiceError``."""
    _route(monkeypatch, rbi_mod, _site(["<html><body>Server busy</body></html>"]))

    with pytest.raises(FXServiceError):
        await RBIProvider().fetch_rates(RANGE, ["USD"])


@pytest.mark.asyncio
async def test_rbi_a_header_that_does_not_match_is_a_service_error(monkeypatch: pytest.MonkeyPatch):
    """A header cell like «USD rate» is no ``CUR (INR / N CUR)``: ``FXServiceError``."""
    table = _table([_full("19/11/2026")], headers=["USD rate", *HEADERS[1:]])
    _route(monkeypatch, rbi_mod, _site([_page("p", table)]))

    with pytest.raises(FXServiceError):
        await RBIProvider().fetch_rates(RANGE, ["USD"])


@pytest.mark.asyncio
async def test_rbi_a_catalogue_currency_missing_from_the_header_is_a_service_error(monkeypatch: pytest.MonkeyPatch):
    """A table without the RUB column: ``FXServiceError``, even if RUB was not asked."""
    table = _table([_row("19/11/2026", "93.3", "122.6", "102.3", "58.5", "25.4", "51.1")], headers=HEADERS[:-1])
    _route(monkeypatch, rbi_mod, _site([_page("p", table)]))

    with pytest.raises(FXServiceError):
        await RBIProvider().fetch_rates(RANGE, ["USD"])


# ── HTTP ─────────────────────────────────────────────────────────────────────────


def _failing_on(method: str, failure):
    """A handler answering well, but where ``method`` (GET or POST) is decided by ``failure(request)``."""

    def handle(request: httpx.Request) -> httpx.Response:
        if request.method == method:
            return failure(request)
        return httpx.Response(200, text=_page("get") if request.method == "GET" else _one_day())

    return handle


@pytest.mark.parametrize("method", ["GET", "POST"])
@pytest.mark.asyncio
async def test_rbi_too_many_requests_is_a_rate_limit(monkeypatch: pytest.MonkeyPatch, method: str):
    """HTTP 429 on the GET or on a POST raises ``FXRateLimitedError``."""
    _route(monkeypatch, rbi_mod, _failing_on(method, lambda request: httpx.Response(429, headers={"Retry-After": "30"})))

    with pytest.raises(FXRateLimitedError):
        await RBIProvider().fetch_rates(RANGE, ["USD"])


@pytest.mark.parametrize("method", ["GET", "POST"])
@pytest.mark.asyncio
async def test_rbi_http_500_is_a_service_error(monkeypatch: pytest.MonkeyPatch, method: str):
    """500 on the GET or on a POST: ``FXServiceError``, not the rate-limit subclass."""
    _route(monkeypatch, rbi_mod, _failing_on(method, lambda request: httpx.Response(500, text="Internal error")))

    with pytest.raises(FXServiceError) as refused:
        await RBIProvider().fetch_rates(RANGE, ["USD"])

    assert not isinstance(refused.value, FXRateLimitedError)


@pytest.mark.parametrize("method", ["GET", "POST"])
@pytest.mark.asyncio
async def test_rbi_unreachable_is_a_service_error(monkeypatch: pytest.MonkeyPatch, method: str):
    """A transport failure on the GET or on a POST is ``FXServiceError``."""

    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    _route(monkeypatch, rbi_mod, _failing_on(method, refuse))

    with pytest.raises(FXServiceError):
        await RBIProvider().fetch_rates(RANGE, ["USD"])

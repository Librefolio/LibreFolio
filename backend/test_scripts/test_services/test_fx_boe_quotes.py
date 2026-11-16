"""BOE FX provider: its CSV download, which series each currency reads, and what it refuses (no network, no DB, no server).

Lane 75, wave 0 (research ``ricerca-FX-banche-centrali.md`` §2, run on the real plugin on 16/11/2026). Measured before
the cure:

- BOE asked ``/boeapps/database/fromshowcolumns.asp``, which now answers the HTML page «Data Series» to every request,
  so nothing was downloaded. The CSV comes from ``/boeapps/database/_iadb-fromshowcolumns.asp`` with ``csv.x=yes``;
  without that parameter the same path answers HTML too (the developer's decision on that path and the site's
  robots.txt: lane 75, 16/11/2026, in the plugin's docstring). A ``Datefrom`` before 01/Jan/1963 is refused (302 to
  ``ErrorPage.asp?ei=905``), and ``"min"`` asked from 1900.
- BOE read EUR from ``XUDLERD``, which the Bank labels «Euro into US $» (EUR per 1 USD), not from ``XUDLERS`` «Euro into
  Sterling» (EUR per 1 GBP): every BOE GBP/EUR rate was a EUR/USD rate.
- BOE's guard against a page in place of the CSV looked for ``<html`` in the first bytes only: the body of the Bank's
  302 (``<head><title>Object moved</title>…``) and the CSV of another series went to the parser, the second stored as
  this currency's rate; an HTML page was logged three times. Now the first line must be ``DATE,<series>``: anything
  else is one ``FXServiceError``, logged once, and no rate.

The expected table is written out by hand from the Bank's labels, never read from the plugin. A guard checks the
plugin's table holds exactly these currencies. Every answer is synthetic, never data downloaded from the Bank.

Isolation: PURE. ``fetch_rates`` runs whole, its module's ``httpx`` replaced for the test by the real module whose
``AsyncClient`` answers through an ``httpx.MockTransport`` (``_route``, from ``test_rate_limit_http_providers.py``):
the plugin's requests, parameters and ``raise_for_status()`` run unchanged and never leave the process. The log capture
is structlog's, in process.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import httpx
import pytest
from structlog.testing import capture_logs

from backend.app.services.fx.base import FXServiceError
from backend.app.services.fx_providers.boe import plugin as boe_mod
from backend.app.services.fx_providers.boe.plugin import BOEProvider
from backend.test_scripts.test_services.test_rate_limit_http_providers import _route

#: Every BOE currency and its series: all «<currency> into Sterling», that is CUR per 1 GBP. From the Bank's own labels.
BOE_EXPECTED: dict[str, str] = {
    "USD": "XUDLUSS",
    "EUR": "XUDLERS",
    "JPY": "XUDLJYS",
    "CHF": "XUDLSFS",
    "CAD": "XUDLCDS",
    "AUD": "XUDLADS",
    "NZD": "XUDLNDS",
    "SEK": "XUDLSKS",
    "NOK": "XUDLNKS",
    "DKK": "XUDLDKS",
    "CNY": "XUDLBK89",
    "HKD": "XUDLHDS",
    "SGD": "XUDLSGS",
    "ZAR": "XUDLZRS",
    "INR": "XUDLBK97",
}

BOE_CSV_PATH = "/boeapps/database/_iadb-fromshowcolumns.asp"
#: The earliest ``Datefrom`` the BOE database accepts.
BOE_FIRST_DAY = date(1963, 1, 1)

DAY = date(2026, 1, 5)
RANGE = (date(2026, 1, 2), date(2026, 1, 9))
#: A synthetic value, the same for every series: what it means is the direction under test.
VALUE = Decimal("2.5000")


def _boe_answer(series: str, lines: list[str]) -> httpx.Response:
    return httpx.Response(200, headers={"content-type": "application/csv"}, text="\n".join([f"DATE,{series}", *lines]) + "\n")


def test_guard_boe_serves_exactly_the_currencies_of_the_expected_table():
    """GUARD — the plugin's table and this test's hold the same currencies, each on the same series."""
    assert dict(BOEProvider.CURRENCY_SERIES) == BOE_EXPECTED, f"BOE's series differ from the Bank's labels as written in this test: {sorted(set(BOEProvider.CURRENCY_SERIES.items()) ^ set(BOE_EXPECTED.items()))}"


@pytest.mark.parametrize("currency", sorted(BOE_EXPECTED))
@pytest.mark.asyncio
async def test_boe_asks_the_csv_download_and_returns_each_series_per_one_gbp(monkeypatch: pytest.MonkeyPatch, currency: str):
    """Each BOE series comes from the CSV download (``_iadb-fromshowcolumns.asp`` with ``csv.x=yes``) and is «1 GBP = v CUR».

    Before the cure the request went to ``fromshowcolumns.asp`` without ``csv.x``, which answers the HTML page «Data
    Series»: no rate at all. And EUR read ``XUDLERD``, EUR per 1 USD."""
    series = BOE_EXPECTED[currency]
    asked = _route(monkeypatch, boe_mod, lambda request: _boe_answer(request.url.params["SeriesCodes"], ["05 Jan 2026,2.5000"]))

    rates = await BOEProvider().fetch_rates(RANGE, [currency])

    assert len(asked) == 1, f"BOE made {len(asked)} requests for {currency}"
    request = asked[0]
    assert request.url.path == BOE_CSV_PATH, f"BOE asked {request.url.path}: the CSV download is {BOE_CSV_PATH}"
    assert request.url.params.get("csv.x") == "yes", f"BOE's request has no csv.x=yes ({dict(request.url.params)}): the Bank answers HTML without it"
    assert request.url.params["SeriesCodes"] == series
    assert rates[currency] == [(DAY, "GBP", currency, VALUE)]


@pytest.mark.asyncio
async def test_boe_asks_min_from_the_first_day_the_database_accepts(monkeypatch: pytest.MonkeyPatch):
    """``"min"`` asks from 01/Jan/1963: the Bank refuses an earlier ``Datefrom`` (302 to an error page)."""
    asked = _route(monkeypatch, boe_mod, lambda request: _boe_answer("XUDLUSS", ["02 Jan 1975,2.3359"]))

    rates = await BOEProvider().fetch_rates(("min", date(1975, 1, 2)), ["USD"])

    assert [request.url.params["Datefrom"] for request in asked] == ["01/Jan/1963"]
    assert rates["USD"] == [(date(1975, 1, 2), "GBP", "USD", Decimal("2.3359"))]


@pytest.mark.asyncio
async def test_boe_asks_nothing_before_the_first_day_the_database_accepts(monkeypatch: pytest.MonkeyPatch):
    """A range ending before 1963 cannot be asked: no request, no rate."""
    asked = _route(monkeypatch, boe_mod, lambda request: _boe_answer("XUDLUSS", []))

    rates = await BOEProvider().fetch_rates((date(1950, 1, 1), date(1962, 12, 31)), ["USD"])

    assert asked == [] and rates["USD"] == []


@pytest.mark.asyncio
async def test_guard_boe_html_answer_gives_no_rate(monkeypatch: pytest.MonkeyPatch):
    """GUARD — an HTML page in place of the CSV (the Bank's error page, a changed endpoint) is no rate, never parsed."""
    _route(monkeypatch, boe_mod, lambda request: httpx.Response(200, headers={"content-type": "text/html"}, text="<!DOCTYPE html>\n<html><title>Data Series | Bank of England</title></html>"))

    rates = await BOEProvider().fetch_rates(RANGE, ["USD"])

    assert rates["USD"] == []


#: Answers that are not the CSV of the series asked (USD, ``XUDLUSS``): each must be refused with a clear
#: ``FXServiceError`` and give no rate. Before the cure the page with no ``<html`` in its first bytes (the body of the
#: Bank's 302 to its error page) and the CSV of another series went to the parser: the second stored EUR per USD as
#: GBP/USD.
_NOT_THE_CSV = [
    pytest.param("text/html", "<!DOCTYPE html>\n<html lang='en'><head><title>Data Series | Bank of England | Database</title></head></html>", id="html-page"),
    pytest.param("application/csv", '<head><title>Object moved</title></head>\n<body><h1>Object Moved</h1>This object may be found <a HREF="ErrorPage.asp?ei=905">here</a>.</body>', id="object-moved"),
    pytest.param("application/csv", "DATE,XUDLERD\n05 Jan 2026,0.8931\n", id="other-series"),
    pytest.param("application/csv", "", id="empty"),
]


@pytest.mark.parametrize(("content_type", "body"), _NOT_THE_CSV)
@pytest.mark.asyncio
async def test_boe_refuses_an_answer_that_is_not_the_csv_of_the_series(monkeypatch: pytest.MonkeyPatch, content_type: str, body: str):
    """The answer must start with ``DATE,<series>``: anything else is an ``FXServiceError`` saying so, logged once where
    ``fetch_rates`` skips the currency, and no rate is returned."""
    _route(monkeypatch, boe_mod, lambda request: httpx.Response(200, headers={"content-type": content_type}, text=body))

    with capture_logs() as events:
        rates = await BOEProvider().fetch_rates(RANGE, ["USD"])

    assert rates["USD"] == [], f"BOE returned {rates['USD']} from an answer that is not the CSV of XUDLUSS: {body[:60]!r}"
    refusals = [e for e in events if e.get("log_level") == "warning" and "not the CSV of series XUDLUSS" in str(e)]
    assert len(refusals) == 1, f"expected one warning naming the refused answer (FXServiceError «… not the CSV of series XUDLUSS …»), got: {events}"


def test_boe_check_csv_raises_a_clear_fx_service_error_on_html():
    """The format check itself: an HTML page is an ``FXServiceError`` naming the currency, the series and the HTML."""
    with pytest.raises(FXServiceError, match=r"USD.*not the CSV of series XUDLUSS.*HTML"):
        BOEProvider()._check_csv("<!DOCTYPE html>\n<html></html>", "XUDLUSS", "USD")

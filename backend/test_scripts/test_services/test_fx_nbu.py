"""NBU FX provider: its range endpoint, the direction and unit of each rate, its dates, and what it refuses (no network, no DB, no server).

Lane 75, wave 1, lot L5 (plan ``plan-phase02FxCentralBanks.prompt.md``). Measured on the real API on 16/11/2026:

- ``NBU_Exchange/exchange_site?start=YYYYMMDD&end=YYYYMMDD&valcode=<cur>&sort=exchangedate&order=asc&json`` answers a
  JSON list, one object per day: ``exchangedate`` (the day the rate is valid, ``DD.MM.YYYY``), ``calcdate`` (the
  business day it was set), ``rate`` per ``units`` units, ``rate_per_unit`` (UAH per 1 unit), ``group`` ("3" = metals).
- Saturdays and Sundays have rows (a copy of Friday's value, same ``calcdate``), and tomorrow's row is there from the
  afternoon before (asked on 16/11: a row for 17.11, ``calcdate`` 16.11).
- Before 02.09.1996 the values are in karbovanets (USD 176100 on 01.09.1996, 1.761 on 02.09.1996).
- An unknown ``valcode`` and an empty range answer ``[]``; a malformed date answers HTTP 200 with a body that is no JSON
  (``[{ Wrong date format/period }]``).
- ``NBUStatService/v1/statdirectory/exchange?json`` lists the day's 45 entries: 40 currencies, the SDR and 4 metals.

Every answer here is synthetic, written by hand in the feed's shape, never data downloaded from the bank.

Isolation: PURE. ``fetch_rates`` runs whole, its module's ``httpx`` replaced for the test by the real module whose
``AsyncClient`` answers through an ``httpx.MockTransport`` (``_route``, from ``test_rate_limit_http_providers.py``);
the pause between requests is set to zero.
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

import httpx
import pytest
from structlog.testing import capture_logs

from backend.app.services.fx.base import FXRateLimitedError, FXServiceError
from backend.app.services.fx_providers.nbu import plugin as nbu_mod
from backend.app.services.fx_providers.nbu.plugin import NBUProvider
from backend.test_scripts.test_services.test_rate_limit_http_providers import _route

RANGE = (date(2026, 1, 5), date(2026, 1, 12))


@pytest.fixture(autouse=True)
def _no_pause(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(NBUProvider, "PAUSE_SECONDS", 0.0)


def _row(currency: str, day: str, rate: str, units: int = 1, calcdate: str = "", group: str = "1") -> str:
    """One object in the feed's shape, numbers written as the bank writes them (JSON numbers)."""
    per_unit = Decimal(rate) / units
    return f'{{"exchangedate":"{day}","r030":0,"cc":"{currency}","txt":"x","enname":"Some currency","rate":{rate},"units":{units},"rate_per_unit":{per_unit},"group":"{group}","calcdate":"{calcdate}","special":null}}'


def _json(*rows: str) -> httpx.Response:
    return httpx.Response(200, headers={"content-type": "application/json; charset=utf-8"}, text="[\n" + ",\n".join(rows) + "\n]")


def _by_currency(rows_by_currency: dict[str, list[str]]):
    """An answer per ``valcode`` (the bank's codes are lower case in the request, upper case in the answer)."""
    return lambda request: _json(*rows_by_currency.get(request.url.params["valcode"].upper(), []))


# ── Direction, unit and days ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_nbu_returns_each_rate_as_uah_per_one_unit(monkeypatch: pytest.MonkeyPatch):
    """«1 USD = 41.5 UAH» stays as published; «10 JPY = 2.8423 UAH» is read from ``rate_per_unit``: 1 JPY = 0.28423 UAH."""
    _route(monkeypatch, nbu_mod, _by_currency({"USD": [_row("USD", "05.01.2026", "41.5")], "JPY": [_row("JPY", "05.01.2026", "2.8423", units=10)]}))

    rates = await NBUProvider().fetch_rates(RANGE, ["USD", "JPY"])

    assert rates["USD"] == [(date(2026, 1, 5), "USD", "UAH", Decimal("41.5"))]
    assert rates["JPY"] == [(date(2026, 1, 5), "JPY", "UAH", Decimal("0.28423"))]


@pytest.mark.asyncio
async def test_nbu_asks_one_range_per_currency_in_series(monkeypatch: pytest.MonkeyPatch):
    """One request per currency, one after the other, on the range endpoint: start, end, lower-case valcode, JSON."""
    asked = _route(monkeypatch, nbu_mod, _by_currency({}))

    rates = await NBUProvider().fetch_rates(RANGE, ["USD", "UAH", "EUR"])

    assert [r.url.params["valcode"] for r in asked] == ["eur", "usd"]
    for request in asked:
        assert request.url.path == "/NBU_Exchange/exchange_site"
        assert (request.url.params["start"], request.url.params["end"]) == ("20260105", "20260112")
        assert "json" in request.url.params and request.url.params["sort"] == "exchangedate"
    assert rates == {"EUR": [], "USD": []}, "the base currency is no series; an empty answer is no rate"


@pytest.mark.asyncio
async def test_nbu_keeps_weekend_and_tomorrow_rows_under_their_exchangedate(monkeypatch: pytest.MonkeyPatch):
    """D2: every row under its ``exchangedate`` (the day the bank says it is valid), Saturday and Sunday included, no
    dedup on ``calcdate``; tomorrow's row too: the core, not the plugin, drops days after the sync's end."""
    rows = [
        _row("USD", "09.01.2026", "41.1", calcdate="08.01.2026"),
        _row("USD", "10.01.2026", "41.2", calcdate="09.01.2026"),
        _row("USD", "11.01.2026", "41.2", calcdate="09.01.2026"),
        _row("USD", "12.01.2026", "41.2", calcdate="09.01.2026"),
        _row("USD", "13.01.2026", "41.3", calcdate="12.01.2026"),
    ]
    _route(monkeypatch, nbu_mod, _by_currency({"USD": rows}))

    rates = await NBUProvider().fetch_rates(RANGE, ["USD"])

    assert [(r[0], r[3]) for r in rates["USD"]] == [
        (date(2026, 1, 9), Decimal("41.1")),
        (date(2026, 1, 10), Decimal("41.2")),
        (date(2026, 1, 11), Decimal("41.2")),
        (date(2026, 1, 12), Decimal("41.2")),
        (date(2026, 1, 13), Decimal("41.3")),
    ]


@pytest.mark.asyncio
async def test_nbu_asks_from_the_hryvnia_and_nothing_before_it(monkeypatch: pytest.MonkeyPatch):
    """``"min"`` and any earlier start ask from 02.09.1996 (before it the values are karbovanets, 100 000 times larger);
    a range ending before that day makes no request."""
    asked = _route(monkeypatch, nbu_mod, _by_currency({"USD": [_row("USD", "02.09.1996", "176.1", units=100)]}))

    rates = await NBUProvider().fetch_rates(("min", date(1996, 9, 2)), ["USD"])
    assert asked[0].url.params["start"] == "19960902"
    assert rates["USD"] == [(date(1996, 9, 2), "USD", "UAH", Decimal("1.761"))]

    await NBUProvider().fetch_rates((date(1996, 8, 1), date(1996, 9, 3)), ["USD"])
    assert asked[1].url.params["start"] == "19960902"

    before = await NBUProvider().fetch_rates((date(1995, 1, 1), date(1996, 9, 1)), ["USD"])
    assert len(asked) == 2 and before == {"USD": []}


@pytest.mark.asyncio
async def test_nbu_reads_the_rate_and_units_when_rate_per_unit_is_missing(monkeypatch: pytest.MonkeyPatch):
    row = '{"exchangedate":"05.01.2026","cc":"KRW","rate":2.9,"units":100,"group":"1","calcdate":"02.01.2026"}'
    _route(monkeypatch, nbu_mod, lambda request: _json(row))

    rates = await NBUProvider().fetch_rates(RANGE, ["KRW"])

    assert rates["KRW"] == [(date(2026, 1, 5), "KRW", "UAH", Decimal("0.029"))]


# ── What it skips and what it refuses ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_nbu_unreadable_row_loses_only_its_day(monkeypatch: pytest.MonkeyPatch):
    """X-R50: a row with no number, a zero or an unreadable day loses its day, never the currency."""
    rows = [
        '{"exchangedate":"05.01.2026","cc":"USD","rate":null,"units":1,"rate_per_unit":null,"group":"1"}',
        _row("USD", "06.01.2026", "0"),
        _row("USD", "2026-01-07", "41.0"),
        _row("USD", "08.01.2026", "41.4"),
    ]
    _route(monkeypatch, nbu_mod, lambda request: _json(*rows))

    rates = await NBUProvider().fetch_rates(RANGE, ["USD"])

    assert rates["USD"] == [(date(2026, 1, 8), "USD", "UAH", Decimal("41.4"))]


@pytest.mark.asyncio
async def test_nbu_ignores_rows_of_another_currency_or_a_metal(monkeypatch: pytest.MonkeyPatch):
    _route(monkeypatch, nbu_mod, lambda request: _json(_row("EUR", "05.01.2026", "48.0"), _row("USD", "05.01.2026", "41.5", group="3"), _row("USD", "06.01.2026", "41.6")))

    rates = await NBUProvider().fetch_rates(RANGE, ["USD"])

    assert rates["USD"] == [(date(2026, 1, 6), "USD", "UAH", Decimal("41.6"))]


#: Answers that are not the bank's JSON list: each is an ``FXServiceError`` naming the currency, logged once where
#: ``fetch_rates`` skips the currency, and no rate. The second is what the bank answers to a malformed date.
_NOT_THE_JSON = [
    pytest.param(200, "text/html", "<!DOCTYPE html>\n<html><head><title>Just a moment...</title></head></html>", id="html-page"),
    pytest.param(200, "application/json", "[\n{ \nWrong date format/period\n }\n]", id="wrong-date-format"),
    pytest.param(200, "application/json", '{"error": "x"}', id="object-not-list"),
    pytest.param(200, "application/json", "", id="empty"),
    pytest.param(500, "text/plain", "Internal error", id="server-error"),
]


@pytest.mark.parametrize(("status", "content_type", "body"), _NOT_THE_JSON)
@pytest.mark.asyncio
async def test_nbu_skips_a_currency_whose_answer_is_not_the_json_list(monkeypatch: pytest.MonkeyPatch, status: int, content_type: str, body: str):
    """XRL-H09: one currency's bad answer skips that currency only; the others arrive."""
    _route(monkeypatch, nbu_mod, lambda request: httpx.Response(status, headers={"content-type": content_type}, text=body) if request.url.params["valcode"] == "usd" else _json(_row("EUR", "05.01.2026", "48.0")))

    with capture_logs() as events:
        rates = await NBUProvider().fetch_rates(RANGE, ["USD", "EUR"])

    assert rates["USD"] == [] and rates["EUR"] == [(date(2026, 1, 5), "EUR", "UAH", Decimal("48.0"))]
    warnings = [e for e in events if e.get("log_level") == "warning" and "USD" in str(e)]
    assert len(warnings) == 1, f"expected one warning for USD, got {events}"


@pytest.mark.asyncio
async def test_nbu_403_stops_the_call_with_a_clear_error(monkeypatch: pytest.MonkeyPatch):
    """Cloudflare is in front of bank.gov.ua: a 403 refuses the client, not one currency. It stops the call with an
    error that says so, and no further request is sent (never a retry, never a way around it)."""
    asked = _route(monkeypatch, nbu_mod, lambda request: httpx.Response(403, headers={"content-type": "text/html"}, text="<html>Access denied</html>"))

    with pytest.raises(FXServiceError, match="403"):
        await NBUProvider().fetch_rates(RANGE, ["USD", "EUR", "GBP"])

    assert len(asked) == 1


@pytest.mark.asyncio
async def test_nbu_too_many_requests_is_a_rate_limit(monkeypatch: pytest.MonkeyPatch):
    _route(monkeypatch, nbu_mod, lambda request: httpx.Response(429, headers={"Retry-After": "60"}))

    with pytest.raises(FXRateLimitedError):
        await NBUProvider().fetch_rates(RANGE, ["USD", "EUR"])


# ── Catalogue ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_nbu_catalogue_drops_metals_and_sdr(monkeypatch: pytest.MonkeyPatch):
    entries = [{"r030": 840, "txt": "x", "rate": 41.5, "cc": cc, "exchangedate": "05.01.2026", "special": None} for cc in ("USD", "EUR", "JPY", "XAU", "XAG", "XPT", "XPD", "XDR")]
    asked = _route(monkeypatch, nbu_mod, lambda request: httpx.Response(200, headers={"content-type": "application/json"}, text=json.dumps(entries)))

    currencies = await NBUProvider().get_supported_currencies()

    assert currencies == ["EUR", "JPY", "UAH", "USD"]
    assert asked[0].url.path == "/NBUStatService/v1/statdirectory/exchange"


@pytest.mark.asyncio
async def test_nbu_catalogue_refuses_an_html_answer(monkeypatch: pytest.MonkeyPatch):
    _route(monkeypatch, nbu_mod, lambda request: httpx.Response(200, headers={"content-type": "text/html"}, text="<html></html>"))

    with pytest.raises(FXServiceError, match="not the JSON list"):
        await NBUProvider().get_supported_currencies()


def test_nbu_identity_and_texts():
    provider = NBUProvider()
    assert (provider.code, provider.base_currency, provider.warning_level) == ("NBU", "UAH", "info")
    for texts in (provider.description_i18n, provider.warning_i18n):
        assert set(texts) == {"en", "it", "fr", "es"} and all(texts.values())
    assert "National Bank of Ukraine" in provider.description_i18n["en"]
    assert "UAH" in provider.fallback_currencies and not {"XAU", "XDR"} & set(provider.fallback_currencies)

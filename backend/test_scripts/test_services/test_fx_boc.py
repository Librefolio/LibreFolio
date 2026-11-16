"""BOC FX provider: its Valet group endpoint, the direction of each series, its dates, and what it refuses (no network, no DB, no server).

Lane 75, wave 1, lot L10 (plan ``plan-phase02FxCentralBanks.prompt.md``). Measured on the real API on 16/11/2026:

- ``valet/observations/group/FX_RATES_DAILY/json?start_date=…&end_date=…`` answers every series of the group in one
  JSON: ``observations`` is one object per business day, ``{"d": "YYYY-MM-DD", "FX<CUR>CAD": {"v": "1.4181"}, …}``,
  every value «CAD per 1 unit», as a string; ``seriesDetail`` names the series.
- The group starts on 2017-01-03 (the older noon rates are another group, not used). A weekend range answers 200 with
  ``"observations": []``. An unknown series in a series request is HTTP 404 for the whole request (hence the group);
  a malformed date is HTTP 400 with a JSON ``message``.
- ``…/group/FX_RATES_DAILY/json?recent=1`` gives each series' last observation: 24 live, VND (2019-12-31), RUB and SAR
  (2026-04-30) closed.

Every answer here is synthetic, written by hand in the feed's shape, never data downloaded from the bank.

Isolation: PURE. ``fetch_rates`` runs whole, its module's ``httpx`` replaced for the test by the real module whose
``AsyncClient`` answers through an ``httpx.MockTransport`` (``_route``, from ``test_rate_limit_http_providers.py``).
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

import httpx
import pytest

from backend.app.services.fx.base import FXRateLimitedError, FXServiceError
from backend.app.services.fx_providers.boc import plugin as boc_mod
from backend.app.services.fx_providers.boc.plugin import BOCProvider
from backend.test_scripts.test_services.test_rate_limit_http_providers import _route

RANGE = (date(2026, 1, 5), date(2026, 1, 9))
GROUP_PATH = "/valet/observations/group/FX_RATES_DAILY/json"


def _answer(*observations: dict, series: tuple[str, ...] = ("FXUSDCAD", "FXJPYCAD", "FXEURCAD")) -> httpx.Response:
    body = {
        "terms": {"url": "https://www.bankofcanada.ca/terms/"},
        "groupDetail": {"label": "Daily exchange rates"},
        "seriesDetail": {s: {"label": f"{s[2:5]}/CAD"} for s in series},
        "observations": list(observations),
    }
    return httpx.Response(200, headers={"content-type": "application/json; charset=utf-8"}, text=json.dumps(body))


def _day(d: str, **values: str) -> dict:
    return {"d": d, **{f"FX{cur}CAD": {"v": v} for cur, v in values.items()}}


# ── Direction and days ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_boc_returns_each_series_as_cad_per_one_unit(monkeypatch: pytest.MonkeyPatch):
    """«1 USD = 1.4181 CAD» and «1 JPY = 0.008940 CAD» stay as published, foreign currency first: the series is
    ``FX<CUR>CAD``, CAD per 1 unit; never «1 CAD = 1.4181 USD» (the FED mistake of wave 0)."""
    _route(monkeypatch, boc_mod, lambda request: _answer(_day("2026-01-05", USD="1.4181", JPY="0.008940", EUR="1.5839")))

    rates = await BOCProvider().fetch_rates(RANGE, ["USD", "JPY"])

    assert rates == {
        "USD": [(date(2026, 1, 5), "USD", "CAD", Decimal("1.4181"))],
        "JPY": [(date(2026, 1, 5), "JPY", "CAD", Decimal("0.008940"))],
    }


@pytest.mark.asyncio
async def test_boc_asks_the_group_once_for_every_currency(monkeypatch: pytest.MonkeyPatch):
    """One request on the group for any number of currencies (D9), with the asked range: never a series request, which
    a series the bank removed would turn into a 404 for all."""
    asked = _route(monkeypatch, boc_mod, lambda request: _answer())

    rates = await BOCProvider().fetch_rates(RANGE, ["USD", "CAD", "EUR", "PEN"])

    assert len(asked) == 1 and asked[0].url.path == GROUP_PATH
    assert (asked[0].url.params["start_date"], asked[0].url.params["end_date"]) == ("2026-01-05", "2026-01-09")
    assert rates == {"EUR": [], "PEN": [], "USD": []}, "the base currency is no series; a currency with no value has an empty list"


@pytest.mark.asyncio
async def test_boc_asks_nothing_for_the_base_currency_alone(monkeypatch: pytest.MonkeyPatch):
    asked = _route(monkeypatch, boc_mod, lambda request: _answer())

    assert await BOCProvider().fetch_rates(RANGE, ["CAD"]) == {}
    assert asked == []


@pytest.mark.asyncio
async def test_boc_asks_from_2017_and_nothing_before(monkeypatch: pytest.MonkeyPatch):
    """``"min"`` and any earlier start ask from 2017-01-03, the first day of the group (the older noon rates are a
    different series, never mixed in); a range ending before it makes no request."""
    asked = _route(monkeypatch, boc_mod, lambda request: _answer(_day("2017-01-03", USD="1.3435")))

    rates = await BOCProvider().fetch_rates(("min", date(2017, 1, 3)), ["USD"])
    assert asked[0].url.params["start_date"] == "2017-01-03"
    assert rates["USD"] == [(date(2017, 1, 3), "USD", "CAD", Decimal("1.3435"))]

    await BOCProvider().fetch_rates((date(2010, 1, 1), date(2017, 2, 1)), ["USD"])
    assert asked[1].url.params["start_date"] == "2017-01-03"

    assert await BOCProvider().fetch_rates((date(2010, 1, 1), date(2016, 12, 30)), ["USD"]) == {"USD": []}
    assert len(asked) == 2


@pytest.mark.asyncio
async def test_boc_keeps_every_day_as_the_bank_dates_it(monkeypatch: pytest.MonkeyPatch):
    """D2: every value under its ``d``; the plugin filters no day."""
    _route(monkeypatch, boc_mod, lambda request: _answer(_day("2026-01-08", USD="1.41"), _day("2026-01-09", USD="1.42"), _day("2026-01-12", USD="1.43")))

    rates = await BOCProvider().fetch_rates(RANGE, ["USD"])

    assert [r[0] for r in rates["USD"]] == [date(2026, 1, 8), date(2026, 1, 9), date(2026, 1, 12)]


# ── What it skips and what it refuses ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_boc_unreadable_value_loses_only_its_day(monkeypatch: pytest.MonkeyPatch):
    """X-R50: an empty value, a value that is no number, a zero or an unreadable day loses its day only."""
    _route(
        monkeypatch,
        boc_mod,
        lambda request: _answer(
            _day("2026-01-05", USD=""),
            _day("2026-01-06", USD="n/a"),
            _day("2026-01-07", USD="0"),
            {"d": "07/01/2026", "FXUSDCAD": {"v": "1.40"}},
            {"d": "2026-01-08", "FXUSDCAD": "1.40"},
            _day("2026-01-09", USD="1.4181"),
        ),
    )

    rates = await BOCProvider().fetch_rates(RANGE, ["USD"])

    assert rates["USD"] == [(date(2026, 1, 9), "USD", "CAD", Decimal("1.4181"))]


@pytest.mark.asyncio
async def test_boc_no_observation_is_no_rate_and_no_error(monkeypatch: pytest.MonkeyPatch):
    _route(monkeypatch, boc_mod, lambda request: _answer())

    assert await BOCProvider().fetch_rates((date(2026, 1, 10), date(2026, 1, 11)), ["USD", "JPY"]) == {"USD": [], "JPY": []}


#: Answers that are not the group's JSON: each is one ``FXServiceError`` for the whole call (it is one request for every
#: currency), never a rate.
_NOT_THE_JSON = [
    pytest.param(200, "text/html", "<!DOCTYPE html>\n<html><head><title>Bank of Canada</title></head></html>", "HTML", id="html-page"),
    pytest.param(200, "application/json", '{"terms": {}, "seriesDetail": {}}', "observations", id="no-observations"),
    pytest.param(200, "application/json", "[]", "observations", id="list-not-object"),
    pytest.param(200, "application/json", "", "JSON", id="empty"),
    pytest.param(400, "application/json", '{"message": "Start date contains a value that is not allowed."}', "400", id="bad-request"),
    pytest.param(404, "application/json", '{"message": "Group FX_RATES_DAILY not found."}', "404", id="group-gone"),
    pytest.param(500, "text/plain", "Internal error", "500", id="server-error"),
]


@pytest.mark.parametrize(("status", "content_type", "body", "named"), _NOT_THE_JSON)
@pytest.mark.asyncio
async def test_boc_refuses_an_answer_that_is_not_the_group_json(monkeypatch: pytest.MonkeyPatch, status: int, content_type: str, body: str, named: str):
    _route(monkeypatch, boc_mod, lambda request: httpx.Response(status, headers={"content-type": content_type}, text=body))

    with pytest.raises(FXServiceError, match=named):
        await BOCProvider().fetch_rates(RANGE, ["USD"])


@pytest.mark.asyncio
async def test_boc_too_many_requests_is_a_rate_limit(monkeypatch: pytest.MonkeyPatch):
    _route(monkeypatch, boc_mod, lambda request: httpx.Response(429, headers={"Retry-After": "60"}))

    with pytest.raises(FXRateLimitedError):
        await BOCProvider().fetch_rates(RANGE, ["USD"])


# ── Catalogue ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_boc_catalogue_drops_closed_series(monkeypatch: pytest.MonkeyPatch):
    """``recent=1`` gives each series' last observation: a series whose last value is more than a month older than the
    newest one is closed (VND, RUB on 2026-11-16); CAD, the base, is listed; a key that is no ``FX<CUR>CAD`` is ignored."""
    asked = _route(
        monkeypatch,
        boc_mod,
        lambda request: _answer(
            _day("2019-12-31", VND="0.000056"),
            {"d": "2026-01-09", "FXUSDCAD": {"v": "1.4"}, "FXJPYCAD": {"v": "0.009"}, "SOMEINDEX": {"v": "100"}},
            _day("2026-01-08", PEN="0.41"),
            _day("2025-04-30", RUB="0.017"),
        ),
    )

    currencies = await BOCProvider().get_supported_currencies()

    assert currencies == ["CAD", "JPY", "PEN", "USD"]
    assert asked[0].url.path == GROUP_PATH and asked[0].url.params["recent"] == "1"


@pytest.mark.asyncio
async def test_boc_catalogue_refuses_an_html_answer(monkeypatch: pytest.MonkeyPatch):
    _route(monkeypatch, boc_mod, lambda request: httpx.Response(200, headers={"content-type": "text/html"}, text="<html></html>"))

    with pytest.raises(FXServiceError, match="HTML"):
        await BOCProvider().get_supported_currencies()


def test_boc_identity_and_texts():
    provider = BOCProvider()
    assert (provider.code, provider.base_currency, provider.warning_level) == ("BOC", "CAD", "warning")
    for texts in (provider.description_i18n, provider.warning_i18n):
        assert set(texts) == {"en", "it", "fr", "es"} and all(texts.values())
    assert "Bank of Canada" in provider.description_i18n["en"]
    assert "IDR" in provider.warning_i18n["en"] and "KRW" in provider.warning_i18n["en"], "the low precision of IDR and KRW is said"
    assert "CAD" in provider.fallback_currencies and not {"VND", "RUB", "SAR"} & set(provider.fallback_currencies)

"""Banxico FX provider: its SIE series request, the direction of each series, its dates, its token and what it refuses (no network, no DB, no server).

Lane 75, wave 2, lot L21 (plan ``plan-phase02FxCentralBanksOndata2.prompt.md``). Measured on the real API on 19/11/2026:

- Without a valid token the API answers HTTP 400 with a JSON ``{"error": {"mensaje": "Token inválido", …}}``.
- The doc of ``consultaDatosSerieRango`` says: up to 20 series per request, dates ``yyyy-MM-dd``, limits of 200 requests
  per 5 minutes and 10 000 per day; the token travels in the ``Bmx-Token`` header.
- The documented answer is ``{"bmx": {"series": [{"idSerie": "SF43718", "titulo": "…", "datos": [{"fecha": "13/11/2026",
  "dato": "18.5525"}]}]}}``: ``fecha`` is DD/MM/YYYY, ``dato`` a string, MXN per 1 unit of the foreign currency;
  a day without publication carries ``"dato": "N/E"``.

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

from backend.app.services.fx.base import FXNotConfiguredError, FXRateLimitedError, FXServiceError
from backend.app.services.fx_providers.banxico import plugin as banxico_mod
from backend.app.services.fx_providers.banxico.plugin import BanxicoProvider
from backend.app.services.plugin_settings.contract import BoundSettings
from backend.app.services.plugin_settings.fields import SettingScope, SettingType
from backend.test_scripts.test_services.test_rate_limit_http_providers import _route

TOKEN = "3f9a1c7e5b2d48a09e6c1f4b7d8a2e5c0b9f3d6a1e4c7b8d2f5a0c9e3b6d1a47"
RANGE = (date(2026, 11, 9), date(2026, 11, 13))
SERIES_ROOT = "/SieAPIRest/service/v1/series/"


def _provider(token: str | None = TOKEN) -> BanxicoProvider:
    provider = BanxicoProvider()
    if token is not None:
        provider.bind_settings(BoundSettings(BanxicoProvider.settings_fields, {}, {"token": token}))
    return provider


def _serie(series_id: str, *rows: tuple[str, str]) -> dict:
    return {"idSerie": series_id, "titulo": f"Synthetic {series_id}", "datos": [{"fecha": f, "dato": d} for f, d in rows]}


def _answer(*series: dict) -> httpx.Response:
    return httpx.Response(200, headers={"content-type": "application/json"}, text=json.dumps({"bmx": {"series": list(series)}}))


def _json(status: int, body: dict, headers: dict | None = None) -> httpx.Response:
    return httpx.Response(status, headers={"content-type": "application/json", **(headers or {})}, text=json.dumps(body))


# ── Direction, request and days ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_banxico_returns_each_series_as_mxn_per_one_unit(monkeypatch: pytest.MonkeyPatch):
    """«1 USD = 18.5525 MXN» and «1 JPY = 0.1160 MXN» stay as published, foreign currency first: never inverted."""
    _route(
        monkeypatch,
        banxico_mod,
        lambda request: _answer(_serie("SF43718", ("13/11/2026", "18.5525")), _serie("SF46406", ("13/11/2026", "0.1160"))),
    )

    rates = await _provider().fetch_rates(RANGE, ["USD", "JPY"])

    assert rates == {
        "USD": [(date(2026, 11, 13), "USD", "MXN", Decimal("18.5525"))],
        "JPY": [(date(2026, 11, 13), "JPY", "MXN", Decimal("0.1160"))],
    }


@pytest.mark.asyncio
async def test_banxico_asks_one_request_for_all_series_with_the_token_in_the_header(monkeypatch: pytest.MonkeyPatch):
    """One GET for every wanted series, ids in the order of the sorted currencies, ISO dates in the path; the token is
    the ``Bmx-Token`` header and never part of the URL."""
    asked = _route(monkeypatch, banxico_mod, lambda request: _answer())

    await _provider().fetch_rates(RANGE, ["USD", "EUR"])

    assert len(asked) == 1
    request = asked[0]
    assert request.url.path == f"{SERIES_ROOT}SF46410,SF43718/datos/2026-11-09/2026-11-13"
    assert request.headers["Bmx-Token"] == TOKEN
    assert TOKEN not in str(request.url)


@pytest.mark.asyncio
async def test_banxico_every_asked_currency_is_a_key_and_mxn_is_no_series(monkeypatch: pytest.MonkeyPatch):
    """The base currency is no series; a currency with no value gets an empty list."""
    asked = _route(monkeypatch, banxico_mod, lambda request: _answer(_serie("SF43718", ("10/11/2026", "18.40"))))

    rates = await _provider().fetch_rates(RANGE, ["USD", "MXN", "EUR"])

    assert asked[0].url.path.startswith(f"{SERIES_ROOT}SF46410,SF43718/")
    assert rates == {"USD": [(date(2026, 11, 10), "USD", "MXN", Decimal("18.40"))], "EUR": []}


@pytest.mark.asyncio
async def test_banxico_unknown_currency_is_empty_and_not_asked(monkeypatch: pytest.MonkeyPatch):
    """A currency with no series (CHF) maps to ``[]`` and is not in the request."""
    asked = _route(monkeypatch, banxico_mod, lambda request: _answer(_serie("SF43718", ("10/11/2026", "18.40"))))

    rates = await _provider().fetch_rates(RANGE, ["USD", "CHF"])

    assert asked[0].url.path.startswith(f"{SERIES_ROOT}SF43718/datos/")
    assert rates["CHF"] == [] and len(rates["USD"]) == 1


@pytest.mark.asyncio
async def test_banxico_asks_nothing_without_wanted_series_or_with_an_inverted_range(monkeypatch: pytest.MonkeyPatch):
    asked = _route(monkeypatch, banxico_mod, lambda request: _answer())

    assert await _provider().fetch_rates(RANGE, ["CHF"]) == {"CHF": []}
    assert await _provider().fetch_rates(RANGE, ["MXN"]) == {}
    assert await _provider().fetch_rates((date(2026, 11, 13), date(2026, 11, 9)), ["USD"]) == {"USD": []}
    assert asked == []


@pytest.mark.asyncio
async def test_banxico_asks_from_1991_and_nothing_before(monkeypatch: pytest.MonkeyPatch):
    """``"min"`` and any earlier start ask from 1991-11-12, the first day of the series."""
    asked = _route(monkeypatch, banxico_mod, lambda request: _answer())

    await _provider().fetch_rates(("min", date(2026, 11, 13)), ["USD"])
    await _provider().fetch_rates((date(1980, 1, 1), date(2026, 11, 13)), ["USD"])

    assert [r.url.path.split("/datos/")[1] for r in asked] == ["1991-11-12/2026-11-13"] * 2


@pytest.mark.asyncio
async def test_banxico_other_base_currency_is_refused(monkeypatch: pytest.MonkeyPatch):
    asked = _route(monkeypatch, banxico_mod, lambda request: _answer())

    with pytest.raises(ValueError):
        await _provider().fetch_rates(RANGE, ["USD"], base_currency="EUR")

    assert await _provider().fetch_rates(RANGE, ["USD"], base_currency="MXN") == {"USD": []}
    assert len(asked) == 1


# ── What it skips ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_banxico_unreadable_value_loses_only_its_day(monkeypatch: pytest.MonkeyPatch):
    """«N/E» (no publication), a non-number, a zero and a negative lose their day only; the others stay."""
    _route(
        monkeypatch,
        banxico_mod,
        lambda request: _answer(
            _serie("SF43718", ("09/11/2026", "N/E"), ("10/11/2026", "abc"), ("11/11/2026", "0"), ("12/11/2026", "-3.5"), ("13/11/2026", "18.5525")),
        ),
    )

    rates = await _provider().fetch_rates(RANGE, ["USD"])

    assert rates["USD"] == [(date(2026, 11, 13), "USD", "MXN", Decimal("18.5525"))]


@pytest.mark.asyncio
async def test_banxico_reads_a_thousands_separator(monkeypatch: pytest.MonkeyPatch):
    _route(monkeypatch, banxico_mod, lambda request: _answer(_serie("SF43718", ("13/11/2026", "1,234.5"))))

    assert (await _provider().fetch_rates(RANGE, ["USD"]))["USD"] == [(date(2026, 11, 13), "USD", "MXN", Decimal("1234.5"))]


@pytest.mark.asyncio
async def test_banxico_skips_a_day_outside_the_range(monkeypatch: pytest.MonkeyPatch):
    _route(monkeypatch, banxico_mod, lambda request: _answer(_serie("SF43718", ("06/11/2026", "18.1"), ("10/11/2026", "18.2"), ("16/11/2026", "18.3"))))

    rates = await _provider().fetch_rates(RANGE, ["USD"])

    assert rates["USD"] == [(date(2026, 11, 10), "USD", "MXN", Decimal("18.2"))]


@pytest.mark.asyncio
async def test_banxico_series_without_data_or_not_asked(monkeypatch: pytest.MonkeyPatch):
    """A series with no ``datos`` gives ``[]``; an ``idSerie`` that was not asked is ignored."""
    _route(
        monkeypatch,
        banxico_mod,
        lambda request: _answer(
            {"idSerie": "SF43718", "titulo": "no data"},
            _serie("SF46410", ("10/11/2026", "21.5")),
        ),
    )

    rates = await _provider().fetch_rates(RANGE, ["USD"])

    assert rates == {"USD": []}


# ── Token ────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_banxico_without_a_token_is_not_configured_and_asks_nothing(monkeypatch: pytest.MonkeyPatch):
    asked = _route(monkeypatch, banxico_mod, lambda request: _answer())

    with pytest.raises(FXNotConfiguredError) as refused:
        await _provider(token=None).fetch_rates(RANGE, ["USD"])

    assert refused.value.missing == ["token"] and asked == []


# ── Errors ───────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_banxico_too_many_requests_is_a_rate_limit(monkeypatch: pytest.MonkeyPatch):
    _route(monkeypatch, banxico_mod, lambda request: httpx.Response(429))

    with pytest.raises(FXRateLimitedError):
        await _provider().fetch_rates(RANGE, ["USD"])


@pytest.mark.asyncio
async def test_banxico_400_with_seconds_to_reset_is_a_rate_limit_with_its_wait(monkeypatch: pytest.MonkeyPatch):
    """The API answers a quota overrun as HTTP 400 carrying ``Bmx-secondsToReset``: the wait is read from it."""
    _route(monkeypatch, banxico_mod, lambda request: _json(400, {"error": {"mensaje": "Limit exceeded"}}, {"Bmx-secondsToReset": "120"}))

    with pytest.raises(FXRateLimitedError) as refused:
        await _provider().fetch_rates(RANGE, ["USD"])

    assert refused.value.retry_after == 120.0


@pytest.mark.asyncio
async def test_banxico_invalid_token_is_a_service_error_not_a_rate_limit(monkeypatch: pytest.MonkeyPatch):
    """HTTP 400 without ``Bmx-secondsToReset`` is a refusal of the token: a plain ``FXServiceError`` that says «token»
    and never shows its value."""
    body = {"error": {"mensaje": "Token inválido", "detalle": "El token enviado no es válido, favor de verificar."}}
    _route(monkeypatch, banxico_mod, lambda request: _json(400, body))

    with pytest.raises(FXServiceError) as refused:
        await _provider().fetch_rates(RANGE, ["USD"])

    assert not isinstance(refused.value, FXRateLimitedError)
    assert "token" in str(refused.value).lower() and TOKEN not in str(refused.value)


@pytest.mark.asyncio
async def test_banxico_other_refusal_keeps_the_bank_message(monkeypatch: pytest.MonkeyPatch):
    """Another HTTP 400 the bank explains (a range it does not accept, say) keeps its ``mensaje`` in the error: neither
    a token refusal nor a rate limit."""
    _route(monkeypatch, banxico_mod, lambda request: _json(400, {"error": {"mensaje": "Rango de fechas no válido"}}))

    with pytest.raises(FXServiceError) as refused:
        await _provider().fetch_rates(RANGE, ["USD"])

    assert not isinstance(refused.value, FXRateLimitedError)
    assert "Rango de fechas no válido" in str(refused.value) and "token" not in str(refused.value).lower()


_NOT_THE_JSON = [
    pytest.param(500, "text/plain", "Internal error", id="server-error"),
    pytest.param(200, "text/html", "<!DOCTYPE html>\n<html><head><title>Banxico</title></head></html>", id="html-page"),
    pytest.param(200, "application/json", '{"bmx": {}}', id="no-series"),
    pytest.param(200, "application/json", '{"bmx": {"series": "x"}}', id="series-not-a-list"),
    pytest.param(200, "text/plain", "not json at all", id="not-json"),
]


@pytest.mark.parametrize(("status", "content_type", "body"), _NOT_THE_JSON)
@pytest.mark.asyncio
async def test_banxico_refuses_an_answer_that_is_not_the_series_json(monkeypatch: pytest.MonkeyPatch, status: int, content_type: str, body: str):
    _route(monkeypatch, banxico_mod, lambda request: httpx.Response(status, headers={"content-type": content_type}, text=body))

    with pytest.raises(FXServiceError) as refused:
        await _provider().fetch_rates(RANGE, ["USD"])

    assert not isinstance(refused.value, FXRateLimitedError) and TOKEN not in str(refused.value)


@pytest.mark.asyncio
async def test_banxico_transport_failure_is_a_service_error(monkeypatch: pytest.MonkeyPatch):
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    _route(monkeypatch, banxico_mod, refuse)

    with pytest.raises(FXServiceError):
        await _provider().fetch_rates(RANGE, ["USD"])


# ── Catalogue and identity ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_banxico_catalogue_is_static_and_makes_no_request(monkeypatch: pytest.MonkeyPatch):
    asked = _route(monkeypatch, banxico_mod, lambda request: _answer())

    currencies = await BanxicoProvider().get_supported_currencies()

    assert currencies == ["CNY", "EUR", "GBP", "JPY", "MXN", "USD", "XDR"]
    assert BanxicoProvider().fallback_currencies == currencies
    assert asked == []


def test_banxico_identity_and_series():
    provider = BanxicoProvider()
    assert (provider.code, provider.base_currency, provider.warning_level) == ("BANXICO", "MXN", "info")
    assert provider.docs_url == "/mkdocs/user/fx/providers/banxico/"
    assert banxico_mod.SERIES == {
        "USD": "SF43718",
        "EUR": "SF46410",
        "JPY": "SF46406",
        "GBP": "SF46407",
        "CNY": "SF290383",
        "XDR": "SF46411",
    }
    assert banxico_mod.FIRST_DAY == date(1991, 11, 12)
    assert banxico_mod.API_ROOT == "https://www.banxico.org.mx/SieAPIRest/service/v1/series"


def test_banxico_declares_one_secret_system_token_field():
    """Its own field is the token; the others are the call limits the core adds to every plugin that calls out (76 U4)."""
    fields = {field.key: field for field in BanxicoProvider.settings_fields}
    assert {key for key in fields if key != "token"} == {f"call_limit_{window}" for window in ("minute", "hour", "day", "week", "month")}
    token = fields["token"]
    assert (token.key, token.type, token.scope, token.secret, token.required) == ("token", SettingType.STRING, SettingScope.SYSTEM, True, True)
    assert token.label_key == "pluginSettings.fx.BANXICO.label.token"
    assert token.description_key == "pluginSettings.fx.BANXICO.description.token"
    assert token.missing_key == "pluginSettings.fx.BANXICO.missing.token"
    assert BanxicoProvider().settings.missing == ("token",)

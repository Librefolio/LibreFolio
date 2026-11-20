"""BDI FX provider: the Banca d'Italia's time series, the direction of each rate, its dates, and what it refuses (no network, no DB, no server).

Lane 75, wave 1, lot L7 (plan ``plan-phase02FxCentralBanks.prompt.md``; developer decision D1: Banca d'Italia yes,
synthetic fixtures only). Measured on the real API on 16/11/2026:

- ``…/terzevalute-wf-web/rest/v1.0/dailyTimeSeries?startDate=YYYY-MM-DD&endDate=YYYY-MM-DD&baseCurrencyIsoCode=<CUR>
  &currencyIsoCode=EUR&lang=en`` with ``Accept: application/json`` answers ``{"resultsInfo": {…, "exchangeConventionCode":
  "C"}, "rates": [{"referenceDate": "…", "avgRate": "176.8300", "exchangeConvention": "Foreign currency amount for 1
  Euro."}]}``: CUR per 1 EUR, as a string. Every one of the 171 currencies of a day had convention C.
- ``baseCurrencyIsoCode`` is the foreign currency; the other way round the API answers HTTP 400 with a plain-text
  «WARNING! Parameter currencyIsoCode can take the value of: EUR, USD or ITL».
- A weekend range answers 200 with ``totalRecords: 0`` and no rate. The euro series start on 1999-01-04.
- A suspended currency keeps its rows with ``avgRate`` ``"N.A."`` (RUB from 2022-03-02).
- ``latestRates`` lists every country's currency of the last day (172 rows, 150 currencies, EUR included): four «N.A.»
  (BYN, IRR, KPW, RUB) and the SDR.

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

from backend.app.config import PROJECT_ROOT
from backend.app.services.fx.base import FXRateLimitedError
from backend.app.services.fx_providers.bdi import plugin as bdi_mod
from backend.app.services.fx_providers.bdi.plugin import BDIProvider
from backend.test_scripts.test_services.test_rate_limit_http_providers import _route

RANGE = (date(2026, 1, 5), date(2026, 1, 9))
FOR_ONE_EURO = "Foreign currency amount for 1 Euro."


@pytest.fixture(autouse=True)
def _no_pause(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(BDIProvider, "PAUSE_SECONDS", 0.0)


def _series(currency: str, *rows: tuple[str, str], convention_code: str = "C", convention: str = FOR_ONE_EURO) -> httpx.Response:
    body = {
        "resultsInfo": {"totalRecords": len(rows), "currency": "x", "isoCode": currency, "uicCode": "000", "exchangeConventionCode": convention_code, "notice": "DISCLAIMER: …"},
        "rates": [{"referenceDate": day, "avgRate": value, "exchangeConvention": convention} for day, value in rows],
    }
    if not rows:
        body["resultsInfo"] = {"totalRecords": 0, "notice": "DISCLAIMER: …"}
    return httpx.Response(200, headers={"content-type": "application/json"}, text=json.dumps(body))


def _by_currency(rows_by_currency: dict[str, list[tuple[str, str]]]):
    return lambda request: _series(request.url.params["baseCurrencyIsoCode"], *rows_by_currency.get(request.url.params["baseCurrencyIsoCode"], []))


# ── Direction and days ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bdi_returns_each_rate_as_foreign_currency_per_one_euro(monkeypatch: pytest.MonkeyPatch):
    """«1 EUR = 1498.5186 NGN» and «1 EUR = 176.83 JPY», euro first: the bank's convention C. Never «1 NGN = 1498 EUR»
    (the FED mistake of wave 0)."""
    _route(monkeypatch, bdi_mod, _by_currency({"NGN": [("2026-01-05", "1498.5186")], "JPY": [("2026-01-05", "176.8300")]}))

    rates = await BDIProvider().fetch_rates(RANGE, ["NGN", "JPY"])

    assert rates == {
        "JPY": [(date(2026, 1, 5), "EUR", "JPY", Decimal("176.8300"))],
        "NGN": [(date(2026, 1, 5), "EUR", "NGN", Decimal("1498.5186"))],
    }


@pytest.mark.asyncio
async def test_bdi_asks_each_currency_against_the_euro_in_json_in_series(monkeypatch: pytest.MonkeyPatch):
    """One time-series request per currency, in series: the foreign currency in ``baseCurrencyIsoCode``, EUR in
    ``currencyIsoCode`` (the other way round is a 400), the asked range, JSON by the ``Accept`` header."""
    asked = _route(monkeypatch, bdi_mod, _by_currency({}))

    rates = await BDIProvider().fetch_rates(RANGE, ["NGN", "EUR", "KES"])

    assert [r.url.params["baseCurrencyIsoCode"] for r in asked] == ["KES", "NGN"]
    for request in asked:
        assert request.url.path.endswith("/terzevalute-wf-web/rest/v1.0/dailyTimeSeries")
        assert request.url.params["currencyIsoCode"] == "EUR"
        assert (request.url.params["startDate"], request.url.params["endDate"]) == ("2026-01-05", "2026-01-09")
        assert request.headers["accept"] == "application/json"
    assert rates == {"KES": [], "NGN": []}, "the base currency is no series; an empty answer is no rate"


@pytest.mark.asyncio
async def test_bdi_asks_from_1999_and_nothing_before(monkeypatch: pytest.MonkeyPatch):
    """``"min"`` and any earlier start ask from 1999-01-04, the first day of the euro series; a range ending before makes
    no request."""
    asked = _route(monkeypatch, bdi_mod, _by_currency({"USD": [("1999-01-04", "1.1789")]}))

    rates = await BDIProvider().fetch_rates(("min", date(1999, 1, 4)), ["USD"])
    assert asked[0].url.params["startDate"] == "1999-01-04"
    assert rates["USD"] == [(date(1999, 1, 4), "EUR", "USD", Decimal("1.1789"))]

    await BDIProvider().fetch_rates((date(1990, 1, 1), date(1999, 2, 1)), ["USD"])
    assert asked[1].url.params["startDate"] == "1999-01-04"

    assert await BDIProvider().fetch_rates((date(1990, 1, 1), date(1998, 12, 31)), ["USD"]) == {"USD": []}
    assert len(asked) == 2


@pytest.mark.asyncio
async def test_bdi_keeps_every_day_as_the_bank_dates_it(monkeypatch: pytest.MonkeyPatch):
    """D2: every value under its ``referenceDate``; the plugin filters no day."""
    _route(monkeypatch, bdi_mod, _by_currency({"NGN": [("2026-01-08", "1500"), ("2026-01-09", "1501"), ("2026-01-12", "1502")]}))

    rates = await BDIProvider().fetch_rates(RANGE, ["NGN"])

    assert [r[0] for r in rates["NGN"]] == [date(2026, 1, 8), date(2026, 1, 9), date(2026, 1, 12)]


# ── What it skips and what it refuses ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_bdi_not_available_and_unreadable_values_lose_only_their_day(monkeypatch: pytest.MonkeyPatch):
    """«N.A.» (a suspended currency, RUB since 2022), an empty value, a zero, an unreadable day: each loses its day."""
    rows = [("2026-01-05", "N.A."), ("2026-01-06", ""), ("2026-01-07", "0"), ("07/01/2026", "92.5"), ("2026-01-08", "92.5673")]
    _route(monkeypatch, bdi_mod, _by_currency({"RUB": rows}))

    rates = await BDIProvider().fetch_rates(RANGE, ["RUB"])

    assert rates["RUB"] == [(date(2026, 1, 8), "EUR", "RUB", Decimal("92.5673"))]


#: Answers that are not the euro series of the currency asked: each is an ``FXServiceError`` for that currency only,
#: logged once where ``fetch_rates`` skips it (XRL-H09), and no rate. The convention cases guard the direction: a
#: series quoted the other way round («Euro amount for 1 …», code I) would otherwise be stored upside down.
_NOT_THE_SERIES = [
    pytest.param(lambda: httpx.Response(400, headers={"content-type": "application/json"}, text="WARNING! Parameter currencyIsoCode can take the value of: EUR, USD or ITL "), id="wrong-parameters-400"),
    pytest.param(lambda: httpx.Response(200, headers={"content-type": "text/html"}, text="<!DOCTYPE html><html><title>Banca d'Italia</title></html>"), id="html-page"),
    pytest.param(lambda: httpx.Response(200, headers={"content-type": "application/json"}, text="Currency,ISO Code,UIC Code,Rate\nNaira,NGN,081,1498.5\n"), id="csv-not-json"),
    pytest.param(lambda: httpx.Response(200, headers={"content-type": "application/json"}, text='{"resultsInfo": {"totalRecords": 1}}'), id="no-rates-list"),
    pytest.param(lambda: _series("NGN", ("2026-01-05", "1498.5"), convention_code="I", convention="Euro amount for 1 foreign currency."), id="convention-inverted"),
    pytest.param(lambda: _series("NGN", ("2026-01-05", "1498.5"), convention="Foreign currency amount for 1 Dollar."), id="convention-dollar"),
    pytest.param(lambda: httpx.Response(500, text="Internal error"), id="server-error"),
]


@pytest.mark.parametrize("answer", _NOT_THE_SERIES)
@pytest.mark.asyncio
async def test_bdi_skips_a_currency_whose_answer_is_not_its_euro_series(monkeypatch: pytest.MonkeyPatch, answer):
    _route(monkeypatch, bdi_mod, lambda request: answer() if request.url.params["baseCurrencyIsoCode"] == "NGN" else _series("KES", ("2026-01-05", "143.6662")))

    with capture_logs() as events:
        rates = await BDIProvider().fetch_rates(RANGE, ["NGN", "KES"])

    assert rates["NGN"] == [], f"BDI returned {rates['NGN']} from an answer that is not NGN's euro series"
    assert rates["KES"] == [(date(2026, 1, 5), "EUR", "KES", Decimal("143.6662"))]
    warnings = [e for e in events if e.get("log_level") == "warning" and "NGN" in str(e)]
    assert len(warnings) == 1, f"expected one warning for NGN, got {events}"


@pytest.mark.asyncio
async def test_bdi_too_many_requests_is_a_rate_limit(monkeypatch: pytest.MonkeyPatch):
    _route(monkeypatch, bdi_mod, lambda request: httpx.Response(429, headers={"Retry-After": "60"}))

    with pytest.raises(FXRateLimitedError):
        await BDIProvider().fetch_rates(RANGE, ["NGN", "KES"])


# ── Catalogue ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bdi_catalogue_keeps_the_currencies_with_a_rate(monkeypatch: pytest.MonkeyPatch):
    """``latestRates``: one row per country (a currency shared by many countries repeats), «N.A.» for a suspended one, the
    SDR; EUR, the base, is listed."""
    rows = [("NIGERIA", "NGN", "1498.5"), ("BENIN", "XOF", "655.957"), ("SENEGAL", "XOF", "655.957"), ("RUSSIA", "RUB", "N.A."), ("IMF", "XDR", "0.84"), ("EURO AREA", "EUR", "1")]
    body = {"resultsInfo": {"totalRecords": len(rows)}, "latestRates": [{"country": c, "currency": "x", "isoCode": i, "uicCode": "0", "eurRate": r, "usdRate": "1", "referenceDate": "2026-01-09"} for c, i, r in rows]}
    asked = _route(monkeypatch, bdi_mod, lambda request: httpx.Response(200, headers={"content-type": "application/json"}, text=json.dumps(body)))

    currencies = await BDIProvider().get_supported_currencies()

    assert currencies == ["EUR", "NGN", "XOF"]
    assert asked[0].url.path.endswith("/latestRates")


def test_bdi_identity_and_texts():
    provider = BDIProvider()
    assert (provider.code, provider.base_currency, provider.warning_level) == ("BDI", "EUR", "warning")
    for texts in (provider.description_i18n, provider.warning_i18n):
        assert set(texts) == {"en", "it", "fr", "es"} and all(texts.values())
    assert "Banca d'Italia" in provider.description_i18n["en"]
    assert "EUR" in provider.fallback_currencies and not {"XDR", "RUB"} & set(provider.fallback_currencies)


def test_bdi_icon_is_our_own_static_file():
    """Banca d'Italia's favicon is served with ``Cross-Origin-Resource-Policy: same-origin`` (19/11/2026), so no other
    site can show it: the provider points at our copy, ``/icons/fx/bdi.png`` (the frontend's static folder, copied into
    the user guide by ``dev.py mkdocs build``), and the copy is a real PNG. The other FX providers keep the bank's URL."""
    assert BDIProvider().icon == "/icons/fx/bdi.png"

    icon = PROJECT_ROOT / "frontend" / "static" / "icons" / "fx" / "bdi.png"
    assert icon.is_file(), f"missing {icon}"
    assert icon.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n", "the icon is not a PNG"

"""NORGES FX provider: its SDMX CSV, the direction and unit of each series, and what it refuses (no network, no DB, no server).

Lane 75, wave 1, lot L3 (plan ``plan-phase02FxCentralBanks.prompt.md``). Measured on the real API on 16/11/2026:

- ``EXR/B.<c1>+<c2>.NOK.SP?format=csv`` answers every asked series in one CSV, ``;``-separated, one row per day:
  ``BASE_CUR`` is the foreign currency, ``QUOTE_CUR`` is NOK, ``OBS_VALUE`` is NOK per ``10**UNIT_MULT`` units
  (``UNIT_MULT`` 0 for USD, 2 for JPY, SEK, DKK, CHF…).
- With ``locale=en`` the values carry a thousands separator (CHF ``1,140.68``); without ``locale`` they are plain
  (``1140.68``). The plugin never sends ``locale``.
- A range with no observation (a weekend) answers HTTP 404 with an SDMX error, code 100 «No data»: no rate, no error.
- An unknown currency in the key is ignored by the API; the catalogue ``B..NOK.SP?lastNObservations=1`` also lists two
  indices (``I44``, ``TWI``), the SDR (``XDR``) and series closed long ago (RUB 2022-03-01, HRK 2022-12-30,
  BGN 2025-12-31).

Every answer here is synthetic, written by hand in the feed's shape, never data downloaded from the bank.

Isolation: PURE. ``fetch_rates`` runs whole, its module's ``httpx`` replaced for the test by the real module whose
``AsyncClient`` answers through an ``httpx.MockTransport`` (``_route``, from ``test_rate_limit_http_providers.py``).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import httpx
import pytest

from backend.app.services.fx.base import FXRateLimitedError, FXServiceError
from backend.app.services.fx_providers.norges import plugin as norges_mod
from backend.app.services.fx_providers.norges.plugin import NorgesBankProvider
from backend.test_scripts.test_services.test_rate_limit_http_providers import _route

HEADER = "FREQ;Frequency;BASE_CUR;Base Currency;QUOTE_CUR;Quote Currency;TENOR;Tenor;DECIMALS;CALCULATED;UNIT_MULT;Unit Multiplier;COLLECTION;Collection Indicator;TIME_PERIOD;OBS_VALUE"
RANGE = (date(2026, 1, 5), date(2026, 1, 9))
NO_DATA = (
    "<?xml version='1.0' encoding='UTF-8'?>\n"
    '<message:Error xmlns:message="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message" '
    'xmlns:com="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common">\n'
    '  <message:ErrorMessage code="100">\n    <com:Text>No data for data query against the dataflow</com:Text>\n'
    "  </message:ErrorMessage>\n</message:Error>\n"
)


def _row(currency: str, unit_mult: int, day: str, value: str, quote: str = "NOK") -> str:
    """One CSV row in the feed's shape. Labels are fixed: only the codes, the multiplier, the day and the value matter."""
    unit_label = "Hundreds" if unit_mult == 2 else "Units"
    return f"B;Business;{currency};Some currency;{quote};Norwegian krone;SP;Spot;4;false;{unit_mult};{unit_label};C;ECB concertation time 14:15 CET;{day};{value}"


def _csv(*rows: str, header: str = HEADER) -> httpx.Response:
    return httpx.Response(200, headers={"content-type": "text/csv;charset=UTF-8"}, text="\n".join([header, *rows]) + "\n")


# ── Direction and unit ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_norges_returns_each_series_as_nok_per_one_unit(monkeypatch: pytest.MonkeyPatch):
    """«1 USD = 9.5 NOK» stays as published; «100 JPY = 5.9772 NOK» becomes «1 JPY = 0.059772 NOK».

    The direction is the bank's (foreign currency per NOK would be the FED mistake of wave 0), and the unit
    multiplier is divided, never stored as the rate."""
    _route(monkeypatch, norges_mod, lambda request: _csv(_row("USD", 0, "2026-01-05", "9.5000"), _row("JPY", 2, "2026-01-05", "5.9772")))

    rates = await NorgesBankProvider().fetch_rates(RANGE, ["USD", "JPY"])

    assert rates["USD"] == [(date(2026, 1, 5), "USD", "NOK", Decimal("9.5000"))]
    assert rates["JPY"] == [(date(2026, 1, 5), "JPY", "NOK", Decimal("0.059772"))]


@pytest.mark.asyncio
async def test_norges_asks_every_currency_in_one_request_without_locale(monkeypatch: pytest.MonkeyPatch):
    """One request for all currencies (D9: one range endpoint), the key ``B.<c1>+<c2>.NOK.SP``, the asked range, CSV,
    and no ``locale``: with ``locale=en`` the bank writes ``1,140.68``."""
    asked = _route(monkeypatch, norges_mod, lambda request: _csv(_row("CHF", 2, "2026-01-05", "1140.68")))

    rates = await NorgesBankProvider().fetch_rates(RANGE, ["USD", "CHF", "NOK"])

    assert len(asked) == 1, f"NORGES made {len(asked)} requests: one is enough for every currency"
    request = asked[0]
    assert request.url.path.endswith("/EXR/B.CHF+USD.NOK.SP"), f"unexpected key: {request.url.path}"
    assert request.url.params["format"] == "csv"
    assert request.url.params["startPeriod"] == "2026-01-05" and request.url.params["endPeriod"] == "2026-01-09"
    assert "locale" not in request.url.params, "with locale the values carry a thousands separator"
    assert rates["CHF"] == [(date(2026, 1, 5), "CHF", "NOK", Decimal("11.4068"))]
    assert rates["USD"] == [], "an asked currency with no row has an empty list"
    assert "NOK" not in rates, "the base currency is no series"


@pytest.mark.asyncio
async def test_norges_asks_nothing_for_the_base_currency_alone(monkeypatch: pytest.MonkeyPatch):
    asked = _route(monkeypatch, norges_mod, lambda request: _csv())

    assert await NorgesBankProvider().fetch_rates(RANGE, ["NOK"]) == {}
    assert asked == []


@pytest.mark.asyncio
async def test_norges_asks_min_from_the_earliest_day(monkeypatch: pytest.MonkeyPatch):
    """``"min"`` asks from 1900: the API answers each series from its own first day (USD 1980-12-10)."""
    asked = _route(monkeypatch, norges_mod, lambda request: _csv(_row("USD", 0, "1980-12-10", "5.2225")))

    rates = await NorgesBankProvider().fetch_rates(("min", date(1980, 12, 31)), ["USD"])

    assert asked[0].url.params["startPeriod"] == "1900-01-01"
    assert rates["USD"] == [(date(1980, 12, 10), "USD", "NOK", Decimal("5.2225"))]


@pytest.mark.asyncio
async def test_norges_keeps_every_day_as_the_bank_dates_it(monkeypatch: pytest.MonkeyPatch):
    """D2: every value under the day the bank gives it, a future one included; the core, not the plugin, drops days
    after the sync's end."""
    _route(monkeypatch, norges_mod, lambda request: _csv(_row("USD", 0, "2026-01-08", "9.1"), _row("USD", 0, "2026-01-09", "9.2"), _row("USD", 0, "2026-01-12", "9.3")))

    rates = await NorgesBankProvider().fetch_rates(RANGE, ["USD"])

    assert [r[0] for r in rates["USD"]] == [date(2026, 1, 8), date(2026, 1, 9), date(2026, 1, 12)]


# ── What it skips and what it refuses ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_norges_unreadable_value_loses_only_its_day(monkeypatch: pytest.MonkeyPatch):
    """X-R50: a value that is no number (empty, ``NaN``) loses its day, never the series."""
    _route(monkeypatch, norges_mod, lambda request: _csv(_row("USD", 0, "2026-01-05", ""), _row("USD", 0, "2026-01-06", "NaN"), _row("USD", 0, "2026-01-07", "9.4")))

    rates = await NorgesBankProvider().fetch_rates(RANGE, ["USD"])

    assert rates["USD"] == [(date(2026, 1, 7), "USD", "NOK", Decimal("9.4"))]


@pytest.mark.asyncio
async def test_norges_ignores_rows_it_did_not_ask_or_not_against_nok(monkeypatch: pytest.MonkeyPatch):
    _route(monkeypatch, norges_mod, lambda request: _csv(_row("SEK", 2, "2026-01-05", "95.0"), _row("USD", 0, "2026-01-05", "1.1", quote="EUR"), _row("USD", 0, "2026-01-05", "9.5")))

    rates = await NorgesBankProvider().fetch_rates(RANGE, ["USD"])

    assert rates == {"USD": [(date(2026, 1, 5), "USD", "NOK", Decimal("9.5"))]}


@pytest.mark.asyncio
async def test_norges_no_data_answer_is_no_rate_and_no_error(monkeypatch: pytest.MonkeyPatch):
    """A range with no business day (a weekend) is HTTP 404 with the SDMX error code 100: empty lists, no error."""
    _route(monkeypatch, norges_mod, lambda request: httpx.Response(404, headers={"content-type": "application/xml;charset=UTF-8"}, text=NO_DATA))

    rates = await NorgesBankProvider().fetch_rates((date(2026, 1, 10), date(2026, 1, 11)), ["USD", "JPY"])

    assert rates == {"USD": [], "JPY": []}


#: Answers that are not the CSV: each must be one clear ``FXServiceError`` for the whole call, never a rate. The call
#: is one request for every currency, so the error is the call's: the core records it on every leg, and nothing empty
#: goes into its fetch cache.
_NOT_THE_CSV = [
    pytest.param(200, "text/html", "<!DOCTYPE html>\n<html><head><title>Norges Bank</title></head></html>", "HTML", id="html-page"),
    pytest.param(200, "text/csv", "TIME_PERIOD;OBS_VALUE\n2026-01-05;9.5\n", "columns", id="missing-columns"),
    pytest.param(200, "text/csv", "", "columns", id="empty"),
    pytest.param(404, "text/html", "<html><body>Not found</body></html>", "404", id="404-without-sdmx-no-data"),
    pytest.param(500, "text/plain", "Internal error", "500", id="server-error"),
]


@pytest.mark.parametrize(("status", "content_type", "body", "named"), _NOT_THE_CSV)
@pytest.mark.asyncio
async def test_norges_refuses_an_answer_that_is_not_the_csv(monkeypatch: pytest.MonkeyPatch, status: int, content_type: str, body: str, named: str):
    _route(monkeypatch, norges_mod, lambda request: httpx.Response(status, headers={"content-type": content_type}, text=body))

    with pytest.raises(FXServiceError, match=named):
        await NorgesBankProvider().fetch_rates(RANGE, ["USD"])


@pytest.mark.asyncio
async def test_norges_too_many_requests_is_a_rate_limit(monkeypatch: pytest.MonkeyPatch):
    _route(monkeypatch, norges_mod, lambda request: httpx.Response(429, headers={"Retry-After": "120"}))

    with pytest.raises(FXRateLimitedError):
        await NorgesBankProvider().fetch_rates(RANGE, ["USD"])


# ── Catalogue ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_norges_catalogue_drops_indices_sdr_and_closed_series(monkeypatch: pytest.MonkeyPatch):
    """The last observation of each series: indices (I44, TWI), the SDR and a series whose last value is more than a
    month older than the newest one in the answer are dropped; NOK, the base, is listed."""
    asked = _route(
        monkeypatch,
        norges_mod,
        lambda request: _csv(
            _row("USD", 0, "2026-01-09", "9.5"),
            _row("JPY", 2, "2026-01-08", "5.9"),
            _row("I44", 0, "2026-01-09", "109.3"),
            _row("TWI", 0, "2026-01-09", "120.8"),
            _row("XDR", 0, "2026-01-09", "12.8"),
            _row("RUB", 2, "2022-03-01", "8.4"),
            _row("BGN", 2, "2025-12-01", "605.5"),
        ),
    )

    currencies = await NorgesBankProvider().get_supported_currencies()

    assert currencies == ["JPY", "NOK", "USD"]
    assert asked[0].url.path.endswith("/EXR/B..NOK.SP") and asked[0].url.params["lastNObservations"] == "1"


@pytest.mark.asyncio
async def test_norges_catalogue_refuses_an_html_answer(monkeypatch: pytest.MonkeyPatch):
    _route(monkeypatch, norges_mod, lambda request: httpx.Response(200, headers={"content-type": "text/html"}, text="<html></html>"))

    with pytest.raises(FXServiceError, match="HTML"):
        await NorgesBankProvider().get_supported_currencies()


def test_norges_identity_and_texts():
    provider = NorgesBankProvider()
    assert (provider.code, provider.base_currency, provider.warning_level) == ("NORGES", "NOK", "info")
    for texts in (provider.description_i18n, provider.warning_i18n):
        assert set(texts) == {"en", "it", "fr", "es"} and all(texts.values())
    assert "NLOD" in provider.description_i18n["en"]
    assert "NOK" in provider.fallback_currencies and "XDR" not in provider.fallback_currencies

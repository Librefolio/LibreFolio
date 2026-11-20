"""BOI FX provider: the Bank of Israel SDMX CSV of daily representative rates (no network, no DB, no server).

Lane 75, wave 2 (plan ``plan-phase02FxCentralBanksOndata2.prompt.md``). Measured on the real API:

- ``{DATA_URL}/RER_EUR_ILS+RER_USD_ILS?startperiod=..&endperiod=..&format=csv`` answers every asked series in one CSV,
  one row per day: ``OBS_VALUE`` is ILS per ``10**UNIT_MULT`` units of the foreign currency (``UNIT_MULT`` 0 for USD,
  2 for JPY).
- A range with no data (a weekend, an unknown key) answers 200 with an empty body and ``text/html``.
- Series such as ``RER_USD_ILS_GLBLIMP`` and ``RER_LBP_ILS`` share the feed's shape but are not served.

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
from backend.app.services.fx_providers.boi import plugin as boi_mod
from backend.app.services.fx_providers.boi.plugin import BOIProvider
from backend.test_scripts.test_services.test_rate_limit_http_providers import _route

HEADER = "SERIES_CODE,FREQ,BASE_CURRENCY,COUNTER_CURRENCY,UNIT_MEASURE,DATA_TYPE,DATA_SOURCE,TIME_COLLECT,CONF_STATUS,PUB_WEBSITE,UNIT_MULT,COMMENTS,TIME_PERIOD,OBS_VALUE,RELEASE_STATUS"
RANGE = (date(2026, 11, 16), date(2026, 11, 20))
D = date(2026, 11, 19)
DATA_URL = "https://edge.boi.gov.il/FusionEdgeServer/sdmx/v2/data/dataflow/BOI.STATISTICS/EXR/1.0"


def _row(currency: str, day: str, value: str, unit_mult: str = "0", series: str | None = None) -> str:
    """One CSV row in the feed's shape; only the series code, the multiplier, the day and the value matter."""
    code = series if series is not None else f"RER_{currency}_ILS"
    return f"{code},D,{currency},ILS,ILS,OF00,BOI_MRKT,V,F,Y,{unit_mult},,{day},{value},YP"


def _csv(*rows: str, header: str = HEADER) -> httpx.Response:
    """A 200 text/csv answer: header then the rows."""
    return httpx.Response(200, headers={"content-type": "text/csv"}, text="\n".join([header, *rows]) + "\n")


def _answer(*rows: str):
    """A handler answering the same CSV to every request."""
    return lambda request: _csv(*rows)


# ── Values and unit ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_boi_usd_is_ils_per_one_unit(monkeypatch: pytest.MonkeyPatch):
    """«USD 3.282» with UNIT_MULT 0 is 1 USD = 3.282 ILS."""
    _route(monkeypatch, boi_mod, _answer(_row("USD", "2026-11-19", "3.282")))

    rates = await BOIProvider().fetch_rates(RANGE, ["USD"])

    assert rates["USD"] == [(D, "USD", "ILS", Decimal("3.282"))]


@pytest.mark.asyncio
async def test_boi_unit_multiplier_is_divided(monkeypatch: pytest.MonkeyPatch):
    """«JPY 2.0951» with UNIT_MULT 2 is ILS per 100 yen: 1 JPY = 0.020951 ILS."""
    _route(monkeypatch, boi_mod, _answer(_row("JPY", "2026-11-19", "2.0951", unit_mult="2")))

    rates = await BOIProvider().fetch_rates(RANGE, ["JPY"])

    assert rates["JPY"] == [(D, "JPY", "ILS", Decimal("0.020951"))]


@pytest.mark.asyncio
async def test_boi_empty_unit_multiplier_is_zero(monkeypatch: pytest.MonkeyPatch):
    """An empty UNIT_MULT means 10**0: the value stays as published."""
    _route(monkeypatch, boi_mod, _answer(_row("EUR", "2026-11-19", "3.8", unit_mult="")))

    rates = await BOIProvider().fetch_rates(RANGE, ["EUR"])

    assert rates["EUR"] == [(D, "EUR", "ILS", Decimal("3.8"))]


@pytest.mark.asyncio
async def test_boi_columns_are_read_by_name(monkeypatch: pytest.MonkeyPatch):
    """A header with the columns in another order still gives the right values."""
    header = "OBS_VALUE,TIME_PERIOD,UNIT_MULT,SERIES_CODE"
    _route(monkeypatch, boi_mod, lambda request: _csv("2.0951,2026-11-19,2,RER_JPY_ILS", "3.282,2026-11-19,0,RER_USD_ILS", header=header))

    rates = await BOIProvider().fetch_rates(RANGE, ["JPY", "USD"])

    assert rates["JPY"] == [(D, "JPY", "ILS", Decimal("0.020951"))]
    assert rates["USD"] == [(D, "USD", "ILS", Decimal("3.282"))]


@pytest.mark.asyncio
async def test_boi_rows_come_out_ascending_per_currency(monkeypatch: pytest.MonkeyPatch):
    """Rows in any order are returned ascending by date."""
    _route(monkeypatch, boi_mod, _answer(_row("USD", "2026-11-19", "3.3"), _row("USD", "2026-11-17", "3.1"), _row("USD", "2026-11-18", "3.2")))

    rates = await BOIProvider().fetch_rates(RANGE, ["USD"])

    assert [r[0] for r in rates["USD"]] == [date(2026, 11, 17), date(2026, 11, 18), D]


# ── Skipped rows ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_boi_ignores_series_that_are_not_an_asked_rer_series(monkeypatch: pytest.MonkeyPatch):
    """«RER_USD_ILS_GLBLIMP», «RER_LBP_ILS» and a series not asked (EUR) are ignored; the asked one stays."""
    rows = [
        _row("USD", "2026-11-19", "9.9", series="RER_USD_ILS_GLBLIMP"),
        _row("LBP", "2026-11-19", "0.0001", series="RER_LBP_ILS"),
        _row("EUR", "2026-11-19", "3.8"),
        _row("USD", "2026-11-19", "3.282"),
    ]
    _route(monkeypatch, boi_mod, _answer(*rows))

    rates = await BOIProvider().fetch_rates(RANGE, ["USD"])

    assert rates == {"USD": [(D, "USD", "ILS", Decimal("3.282"))]}


@pytest.mark.parametrize(
    "bad_row",
    [
        pytest.param(_row("USD", "not-a-day", "3.1"), id="bad-day"),
        pytest.param(_row("USD", "2026-11-18", ""), id="empty-value"),
        pytest.param(_row("USD", "2026-11-18", "abc"), id="text-value"),
        pytest.param(_row("USD", "2026-11-18", "0"), id="zero-value"),
        pytest.param(_row("USD", "2026-11-18", "-3.1"), id="negative-value"),
        pytest.param(_row("USD", "2026-11-18", "3.1", unit_mult="x"), id="bad-multiplier"),
        pytest.param(_row("USD", "2026-11-15", "3.1"), id="before-start"),
        pytest.param(_row("USD", "2026-11-21", "3.1"), id="after-end"),
    ],
)
@pytest.mark.asyncio
async def test_boi_unreadable_or_out_of_range_row_loses_only_itself(monkeypatch: pytest.MonkeyPatch, bad_row: str):
    """A row that cannot be read, or lies outside the range, is skipped; the good row stays."""
    _route(monkeypatch, boi_mod, _answer(bad_row, _row("USD", "2026-11-19", "3.282")))

    rates = await BOIProvider().fetch_rates(RANGE, ["USD"])

    assert rates["USD"] == [(D, "USD", "ILS", Decimal("3.282"))]


@pytest.mark.asyncio
async def test_boi_same_day_with_two_values_is_dropped_and_equal_ones_kept_once(monkeypatch: pytest.MonkeyPatch):
    """Two different values for one day and currency drop that day; the same value twice stays once."""
    rows = [
        _row("USD", "2026-11-17", "3.1"),
        _row("USD", "2026-11-17", "3.2"),
        _row("USD", "2026-11-18", "3.3"),
        _row("USD", "2026-11-18", "3.3"),
        _row("EUR", "2026-11-17", "3.8"),
    ]
    _route(monkeypatch, boi_mod, _answer(*rows))

    rates = await BOIProvider().fetch_rates(RANGE, ["USD", "EUR"])

    assert rates["USD"] == [(date(2026, 11, 18), "USD", "ILS", Decimal("3.3"))]
    assert [r[0] for r in rates["EUR"]] == [date(2026, 11, 17)]


# ── The request ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_boi_asks_one_request_with_the_sorted_keys(monkeypatch: pytest.MonkeyPatch):
    """One GET for all currencies: keys sorted and joined by «+», the asked range and ``format=csv``."""
    asked = _route(monkeypatch, boi_mod, _answer(_row("USD", "2026-11-19", "3.282")))

    rates = await BOIProvider().fetch_rates(RANGE, ["USD", "EUR"])

    assert len(asked) == 1, f"BOI made {len(asked)} requests: one is enough for every currency"
    request = asked[0]
    assert request.method == "GET"
    assert f"{request.url.scheme}://{request.url.host}{request.url.path}" == f"{DATA_URL}/RER_EUR_ILS+RER_USD_ILS"
    assert request.url.params["startperiod"] == "2026-11-16"
    assert request.url.params["endperiod"] == "2026-11-20"
    assert request.url.params["format"] == "csv"
    assert rates["EUR"] == []


@pytest.mark.asyncio
async def test_boi_min_and_an_earlier_start_ask_from_the_first_day(monkeypatch: pytest.MonkeyPatch):
    """``"min"`` and a start before 1986-01-01 both ask from 1986-01-01."""
    asked = _route(monkeypatch, boi_mod, _answer(_row("USD", "1989-12-29", "2.0")))

    await BOIProvider().fetch_rates(("min", date(1990, 1, 1)), ["USD"])
    await BOIProvider().fetch_rates((date(1970, 1, 1), date(1990, 1, 1)), ["USD"])

    assert [r.url.params["startperiod"] for r in asked] == ["1986-01-01", "1986-01-01"]


@pytest.mark.asyncio
async def test_boi_a_later_start_is_asked_as_given(monkeypatch: pytest.MonkeyPatch):
    """A start after the first day is not moved."""
    asked = _route(monkeypatch, boi_mod, _answer(_row("USD", "2000-03-15", "4.1")))

    await BOIProvider().fetch_rates((date(2000, 3, 1), date(2000, 3, 31)), ["USD"])

    assert asked[0].url.params["startperiod"] == "2000-03-01"


@pytest.mark.asyncio
async def test_boi_only_served_currencies_are_asked(monkeypatch: pytest.MonkeyPatch):
    """ILS and a currency the bank does not serve (LBP) are left out of the key."""
    asked = _route(monkeypatch, boi_mod, _answer(_row("USD", "2026-11-19", "3.282")))

    rates = await BOIProvider().fetch_rates(RANGE, ["ILS", "LBP", "USD"])

    assert asked[0].url.path.endswith("/RER_USD_ILS")
    assert set(rates) == {"LBP", "USD"}
    assert rates["LBP"] == []


@pytest.mark.parametrize(
    ("currencies", "expected"),
    [
        pytest.param(["ILS"], {}, id="base-alone"),
        pytest.param(["LBP"], {"LBP": []}, id="unserved-alone"),
        pytest.param(["LBP", "XYZ"], {"LBP": [], "XYZ": []}, id="unknown-only"),
    ],
)
@pytest.mark.asyncio
async def test_boi_nothing_servable_asks_nothing(monkeypatch: pytest.MonkeyPatch, currencies: list[str], expected: dict):
    """Only the base, or only currencies outside the list: no request, every non-base currency an empty key."""
    asked = _route(monkeypatch, boi_mod, _answer())

    assert await BOIProvider().fetch_rates(RANGE, currencies) == expected
    assert asked == []


@pytest.mark.parametrize(
    "span",
    [
        pytest.param((date(2026, 11, 20), date(2026, 11, 16)), id="start-after-end"),
        pytest.param((date(1980, 1, 1), date(1985, 12, 31)), id="end-before-first-day"),
    ],
)
@pytest.mark.asyncio
async def test_boi_an_empty_range_asks_nothing(monkeypatch: pytest.MonkeyPatch, span: tuple[date, date]):
    """A start after the end, or an end before 1986-01-01: no request, an empty key."""
    asked = _route(monkeypatch, boi_mod, _answer())

    assert await BOIProvider().fetch_rates(span, ["USD"]) == {"USD": []}
    assert asked == []


@pytest.mark.asyncio
async def test_boi_base_currency_other_than_ils_is_refused(monkeypatch: pytest.MonkeyPatch):
    """``base_currency`` EUR raises ``ValueError``; None and ILS are fine."""
    _route(monkeypatch, boi_mod, _answer(_row("USD", "2026-11-19", "3.282")))

    with pytest.raises(ValueError):
        await BOIProvider().fetch_rates(RANGE, ["USD"], base_currency="EUR")

    assert len((await BOIProvider().fetch_rates(RANGE, ["USD"], base_currency="ILS"))["USD"]) == 1
    assert len((await BOIProvider().fetch_rates(RANGE, ["USD"], base_currency=None))["USD"]) == 1


# ── Empty answers ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "response",
    [
        pytest.param(httpx.Response(200, headers={"content-type": "text/html"}, text=""), id="empty-html"),
        pytest.param(httpx.Response(200, headers={"content-type": "text/csv"}, text=""), id="empty-csv"),
        pytest.param(httpx.Response(200, headers={"content-type": "text/html"}, text="  \n\n "), id="whitespace"),
        pytest.param(httpx.Response(200, headers={"content-type": "text/csv"}, text=HEADER + "\n"), id="header-only"),
    ],
)
@pytest.mark.asyncio
async def test_boi_no_data_answer_is_no_rate_and_no_error(monkeypatch: pytest.MonkeyPatch, response: httpx.Response):
    """A weekend answers 200 with an empty body; a header-only CSV has no rows: empty lists, no error."""
    _route(monkeypatch, boi_mod, lambda request: response)

    rates = await BOIProvider().fetch_rates(RANGE, ["USD", "JPY"])

    assert rates == {"USD": [], "JPY": []}


LONG_RANGE = (date(2026, 10, 1), date(2026, 11, 19))
SHORT_RANGE = (date(2026, 11, 14), date(2026, 11, 15))
NOT_FOUND_PAGE = "<html><body>Not found</body></html>"


@pytest.mark.asyncio
async def test_boi_404_on_a_short_range_is_no_rate_and_no_error(monkeypatch: pytest.MonkeyPatch):
    """A weekend can answer HTTP 404 with an HTML page: empty lists, no error."""
    _route(monkeypatch, boi_mod, lambda request: httpx.Response(404, headers={"content-type": "text/html"}, text=NOT_FOUND_PAGE))

    rates = await BOIProvider().fetch_rates(SHORT_RANGE, ["USD", "JPY"])

    assert rates == {"USD": [], "JPY": []}


@pytest.mark.parametrize(
    "response",
    [
        pytest.param(httpx.Response(404, headers={"content-type": "text/html"}, text=NOT_FOUND_PAGE), id="404"),
        pytest.param(httpx.Response(200, headers={"content-type": "text/html"}, text=""), id="empty-body"),
        pytest.param(httpx.Response(200, headers={"content-type": "text/csv"}, text=HEADER + "\n"), id="header-only"),
    ],
)
@pytest.mark.asyncio
async def test_boi_no_data_on_a_long_range_is_a_service_error(monkeypatch: pytest.MonkeyPatch, response: httpx.Response):
    """Over EMPTY_SPAN_DAYS no data is not a holiday gap: the API may have moved, so ``FXServiceError`` «no rate», never a rate limit."""
    _route(monkeypatch, boi_mod, lambda request: response)

    with pytest.raises(FXServiceError, match="no rate") as refused:
        await BOIProvider().fetch_rates(LONG_RANGE, ["USD"])

    assert not isinstance(refused.value, FXRateLimitedError)


@pytest.mark.asyncio
async def test_boi_the_empty_span_limit_is_ten_days_inclusive(monkeypatch: pytest.MonkeyPatch):
    """Ten days apart is still a short range; eleven is long."""
    _route(monkeypatch, boi_mod, lambda request: httpx.Response(404, text=NOT_FOUND_PAGE))

    assert await BOIProvider().fetch_rates((date(2026, 11, 1), date(2026, 11, 11)), ["USD"]) == {"USD": []}
    with pytest.raises(FXServiceError, match="no rate"):
        await BOIProvider().fetch_rates((date(2026, 11, 1), date(2026, 11, 12)), ["USD"])


# ── Errors ───────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "body",
    [
        pytest.param("<!DOCTYPE html><html><body>Blocked</body></html>", id="html-page"),
        pytest.param("<?xml version='1.0'?><error/>", id="xml-page"),
        pytest.param("TIME_PERIOD,OBS_VALUE,UNIT_MULT\n2026-11-19,3.282,0\n", id="no-series-code"),
        pytest.param("SERIES_CODE,OBS_VALUE,UNIT_MULT\nRER_USD_ILS,3.282,0\n", id="no-time-period"),
        pytest.param("SERIES_CODE,TIME_PERIOD,UNIT_MULT\nRER_USD_ILS,2026-11-19,0\n", id="no-obs-value"),
        pytest.param("SERIES_CODE,TIME_PERIOD,OBS_VALUE\nRER_USD_ILS,2026-11-19,3.282\n", id="no-unit-mult"),
    ],
)
@pytest.mark.asyncio
async def test_boi_an_answer_that_is_not_the_csv_is_a_service_error(monkeypatch: pytest.MonkeyPatch, body: str):
    """An HTML page (a block, or the API changed) or a CSV without a needed column: ``FXServiceError``, not the rate-limit one."""
    _route(monkeypatch, boi_mod, lambda request: httpx.Response(200, headers={"content-type": "text/csv"}, text=body))

    with pytest.raises(FXServiceError) as refused:
        await BOIProvider().fetch_rates(RANGE, ["USD"])

    assert not isinstance(refused.value, FXRateLimitedError)


@pytest.mark.asyncio
async def test_boi_http_500_is_a_service_error(monkeypatch: pytest.MonkeyPatch):
    _route(monkeypatch, boi_mod, lambda request: httpx.Response(500, text="Internal error"))

    with pytest.raises(FXServiceError) as refused:
        await BOIProvider().fetch_rates(RANGE, ["USD"])

    assert not isinstance(refused.value, FXRateLimitedError)


@pytest.mark.asyncio
async def test_boi_unreachable_is_a_service_error(monkeypatch: pytest.MonkeyPatch):
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    _route(monkeypatch, boi_mod, refuse)

    with pytest.raises(FXServiceError):
        await BOIProvider().fetch_rates(RANGE, ["USD"])


@pytest.mark.asyncio
async def test_boi_too_many_requests_is_a_rate_limit(monkeypatch: pytest.MonkeyPatch):
    _route(monkeypatch, boi_mod, lambda request: httpx.Response(429, headers={"Retry-After": "60"}))

    with pytest.raises(FXRateLimitedError):
        await BOIProvider().fetch_rates(RANGE, ["USD"])


# ── Catalogue and identity ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_boi_catalogue_is_the_served_currencies_plus_ils_without_a_request(monkeypatch: pytest.MonkeyPatch):
    """The sorted served currencies and ILS; the fallback list is the same; LBP is not served; no request."""
    asked = _route(monkeypatch, boi_mod, _answer())

    currencies = await BOIProvider().get_supported_currencies()

    assert currencies == sorted((*boi_mod.CURRENCIES, "ILS"))
    assert "LBP" not in currencies
    assert BOIProvider().fallback_currencies == currencies
    assert asked == []


def test_boi_identity_and_constants():
    """Code, base, level, docs page, URL, first day and the served currencies."""
    provider = BOIProvider()
    assert (provider.code, provider.base_currency, provider.warning_level) == ("BOI", "ILS", "warning")
    assert provider.docs_url == "/mkdocs/user/fx/providers/boi/"
    assert boi_mod.DATA_URL == DATA_URL
    assert boi_mod.FIRST_DAY == date(1986, 1, 1)
    assert boi_mod.EMPTY_SPAN_DAYS == 10
    assert boi_mod.CURRENCIES == ("AUD", "CAD", "CHF", "DKK", "EGP", "EUR", "GBP", "JOD", "JPY", "NOK", "SEK", "USD", "ZAR")

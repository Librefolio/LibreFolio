"""BCRA FX provider: one JSON series per currency, read in three-year windows, pesos per unit (no network, no DB, no server).

Lane 75, wave 2 (plan ``plan-phase02FxCentralBanksOndata2.prompt.md``). The shape of the feed, from the bank's
``estadisticascambiarias/v1.0`` API:

- ``GET …/Cotizaciones/{code}?fechadesde=…&fechahasta=…&limit=1000`` answers ``{"status", "metadata": {"resultset":
  {"count", "offset", "limit"}}, "results": [{"fecha", "detalle": [{"codigoMoneda", "descripcion", "tipoPase",
  "tipoCotizacion"}]}]}``, newest first. ``count`` counts records, not dates: a date may carry two.
- An empty range answers 200 with count 0 and ``"results": []``; a bad parameter answers HTTP 400 with ``errorMessages``.
- ``tipoCotizacion`` is pesos per ``divisor`` units (VND is quoted per 1000); ``tipoPase`` is never read.

Every answer here is synthetic, written by hand in the feed's shape, never data downloaded from the bank.

Isolation: PURE. ``fetch_rates`` and ``get_supported_currencies`` run whole, their module's ``httpx`` replaced for the
test by the real module whose ``AsyncClient`` answers through an ``httpx.MockTransport`` (``_route``, from
``test_rate_limit_http_providers.py``). The pause between requests is zero, or a recorder, never a real sleep.
"""

from __future__ import annotations

import asyncio
from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest

from backend.app.services.fx.base import FXRateLimitedError, FXServiceError
from backend.app.services.fx_providers.bcra import plugin as bcra_mod
from backend.app.services.fx_providers.bcra.plugin import BCRAProvider
from backend.test_scripts.test_services.test_rate_limit_http_providers import _route

BASE_URL = "https://api.bcra.gob.ar/estadisticascambiarias/v1.0"
RANGE = (date(2026, 11, 16), date(2026, 11, 19))
ISO_CODES = [
    "AUD", "AWG", "BOB", "BRL", "CAD", "CHF", "CLP", "CNY", "COP", "CZK", "DKK", "EUR", "GBP", "HKD", "ILS", "INR",
    "JPY", "MXN", "NIO", "NOK", "NZD", "PEN", "PYG", "RSD", "RUB", "SEK", "SGD", "TRY", "USD", "UYU", "VND", "ZAR",
]  # fmt: skip


def _rec(code: str, value: str, pase: str = "1.0") -> str:
    """One ``detalle`` record; ``value`` is the raw JSON text of the number."""
    return f'{{"codigoMoneda":"{code}","descripcion":"X","tipoPase":{pase},"tipoCotizacion":{value}}}'


def _day(day: str, *records: str) -> str:
    return f'{{"fecha":"{day}","detalle":[{",".join(records)}]}}'


def _body(*days: str, count: int | None = None) -> str:
    """An answer from days given newest first; ``count`` defaults to the number of records in them."""
    if count is None:
        count = sum(day.count('"codigoMoneda"') for day in days)
    meta = f'{{"resultset":{{"count":{count},"offset":0,"limit":1000}}}}'
    return f'{{"status":200,"metadata":{meta},"results":[{",".join(days)}]}}'


def _json(body: str, status: int = 200) -> httpx.Response:
    return httpx.Response(status, headers={"content-type": "application/json"}, content=body.encode())


def _code_of(request: httpx.Request) -> str:
    """The BCRA code of a request (``…/Cotizaciones/REF``)."""
    return request.url.path.rsplit("/", 1)[-1]


def _from_of(request: httpx.Request) -> date:
    return date.fromisoformat(request.url.params["fechadesde"])


EMPTY = _body()
USD_BODY = _body(
    _day("2026-11-19", _rec("REF", "1562.9893")),
    _day("2026-11-18", _rec("REF", "1550.5")),
    _day("2026-11-17", _rec("REF", "1540")),
)
EUR_BODY = _body(_day("2026-11-19", _rec("EUR", "1800.25")), _day("2026-11-18", _rec("EUR", "1790.5")))


@pytest.fixture(autouse=True)
def _no_pause(monkeypatch: pytest.MonkeyPatch) -> None:
    """No test waits between two requests, unless it records the pause itself."""
    monkeypatch.setattr(BCRAProvider, "PAUSE_SECONDS", 0)


def _by_code(feeds: dict[str, str]):
    """An answer function serving the body of the code asked; an unknown code gets an empty answer."""
    return lambda request: _json(feeds.get(_code_of(request), EMPTY))


# ── Identity and catalogue ───────────────────────────────────────────────────────


def test_bcra_identity_and_constants():
    provider = BCRAProvider()
    assert (provider.code, provider.base_currency, provider.warning_level) == ("BCRA", "ARS", "warning")
    assert provider.docs_url == "/mkdocs/user/fx/providers/bcra/"
    assert bcra_mod.BASE_URL == BASE_URL
    assert bcra_mod.FIRST_DAY == date(2002, 3, 4)
    assert (bcra_mod.WINDOW_DAYS, bcra_mod.PAGE_LIMIT) == (1095, 1000)
    assert (BCRAProvider.MAX_PARALLEL, BCRAProvider.PAUSE_SECONDS) == (3, 0)


def test_bcra_pause_between_requests_is_a_third_of_a_second_by_default(monkeypatch: pytest.MonkeyPatch):
    """The class default, seen with the fixture's zero undone."""
    monkeypatch.undo()
    assert BCRAProvider.PAUSE_SECONDS == 0.3


def test_bcra_codes_table():
    codes = bcra_mod.CODES
    assert sorted(codes) == ISO_CODES and len(codes) == 32
    assert codes["USD"] == ("REF", Decimal(1))
    assert codes["MXN"] == ("MXP", Decimal(1))
    assert codes["VND"] == ("VND", Decimal(1000))
    assert all(codes[c] == (c, Decimal(1)) for c in ISO_CODES if c not in ("USD", "MXN", "VND"))
    for absent in ("XDR", "XAU", "XAG", "CNH", "VEB", "ATS", "DEM", "ESP", "ITL", "ARS"):
        assert absent not in codes


@pytest.mark.asyncio
async def test_bcra_catalogue_is_the_codes_plus_ars_without_a_request(monkeypatch: pytest.MonkeyPatch):
    asked = _route(monkeypatch, bcra_mod, lambda request: _json(EMPTY))

    currencies = await BCRAProvider().get_supported_currencies()

    assert currencies == sorted([*ISO_CODES, "ARS"])
    assert asked == []
    assert BCRAProvider().fallback_currencies == currencies


@pytest.mark.asyncio
async def test_bcra_other_base_currency_is_refused(monkeypatch: pytest.MonkeyPatch):
    asked = _route(monkeypatch, bcra_mod, _by_code({"REF": USD_BODY}))

    with pytest.raises(ValueError):
        await BCRAProvider().fetch_rates(RANGE, ["USD"], base_currency="EUR")

    assert len((await BCRAProvider().fetch_rates(RANGE, ["USD"], base_currency="ARS"))["USD"]) == 3
    assert len((await BCRAProvider().fetch_rates(RANGE, ["USD"], base_currency=None))["USD"]) == 3
    assert len(asked) == 2


# ── Values ───────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bcra_usd_is_pesos_per_unit_ascending_and_exact(monkeypatch: pytest.MonkeyPatch):
    """``1562.9893`` is ``Decimal("1562.9893")``, rows ``(d, USD, ARS, value)`` oldest first."""
    _route(monkeypatch, bcra_mod, _by_code({"REF": USD_BODY}))

    rates = await BCRAProvider().fetch_rates(RANGE, ["USD"])

    assert rates["USD"] == [
        (date(2026, 11, 17), "USD", "ARS", Decimal("1540")),
        (date(2026, 11, 18), "USD", "ARS", Decimal("1550.5")),
        (date(2026, 11, 19), "USD", "ARS", Decimal("1562.9893")),
    ]
    assert all(isinstance(row[3], Decimal) for row in rates["USD"])


@pytest.mark.asyncio
async def test_bcra_small_value_keeps_every_digit(monkeypatch: pytest.MonkeyPatch):
    _route(monkeypatch, bcra_mod, _by_code({"EUR": _body(_day("2026-11-19", _rec("EUR", "0.000487")))}))

    rates = await BCRAProvider().fetch_rates(RANGE, ["EUR"])

    assert str(rates["EUR"][0][3]) == "0.000487"


@pytest.mark.asyncio
async def test_bcra_vnd_is_divided_by_a_thousand(monkeypatch: pytest.MonkeyPatch):
    """The feed quotes VND per 1000 units: ``53.361793`` is ``0.053361793`` pesos."""
    _route(monkeypatch, bcra_mod, _by_code({"VND": _body(_day("2026-11-19", _rec("VND", "53.361793")))}))

    rates = await BCRAProvider().fetch_rates(RANGE, ["VND"])

    assert rates["VND"] == [(date(2026, 11, 19), "VND", "ARS", Decimal("0.053361793"))]


@pytest.mark.asyncio
async def test_bcra_reads_tipo_cotizacion_never_tipo_pase(monkeypatch: pytest.MonkeyPatch):
    _route(monkeypatch, bcra_mod, _by_code({"EUR": _body(_day("2026-11-19", _rec("EUR", "1800.25", pase="1.08")))}))

    rates = await BCRAProvider().fetch_rates(RANGE, ["EUR"])

    assert rates["EUR"][0][3] == Decimal("1800.25")


# ── Requests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bcra_one_get_per_currency_with_code_and_query(monkeypatch: pytest.MonkeyPatch):
    """USD asks ``REF``, MXN asks ``MXP``, EUR asks ``EUR``; sorted order, ``limit=1000``, ISO dates."""
    asked = _route(monkeypatch, bcra_mod, lambda request: _json(EMPTY))

    await BCRAProvider().fetch_rates(RANGE, ["USD", "MXN", "EUR"])

    assert [r.url.path for r in asked] == [
        "/estadisticascambiarias/v1.0/Cotizaciones/EUR",
        "/estadisticascambiarias/v1.0/Cotizaciones/MXP",
        "/estadisticascambiarias/v1.0/Cotizaciones/REF",
    ]
    assert all(r.method == "GET" and str(r.url).startswith(BASE_URL + "/Cotizaciones/") for r in asked)
    for request in asked:
        assert dict(request.url.params) == {"fechadesde": "2026-11-16", "fechahasta": "2026-11-19", "limit": "1000"}


@pytest.mark.asyncio
async def test_bcra_min_and_earlier_start_begin_at_the_first_day(monkeypatch: pytest.MonkeyPatch):
    asked = _route(monkeypatch, bcra_mod, lambda request: _json(EMPTY))

    await BCRAProvider().fetch_rates(("min", date(2002, 3, 10)), ["USD"])
    await BCRAProvider().fetch_rates((date(1990, 1, 1), date(2002, 3, 10)), ["USD"])

    assert [(r.url.params["fechadesde"], r.url.params["fechahasta"]) for r in asked] == [("2002-03-04", "2002-03-10")] * 2


@pytest.mark.asyncio
async def test_bcra_long_range_is_cut_in_windows_oldest_first(monkeypatch: pytest.MonkeyPatch):
    """2002-03-04..2010-12-31 is three windows: each at most 1095 days, the next one day after the previous end."""
    asked = _route(monkeypatch, bcra_mod, lambda request: _json(EMPTY))

    await BCRAProvider().fetch_rates((date(2002, 3, 4), date(2010, 12, 31)), ["USD"])

    windows = [(date.fromisoformat(r.url.params["fechadesde"]), date.fromisoformat(r.url.params["fechahasta"])) for r in asked]
    assert len(windows) == 3
    assert windows[0][0] == date(2002, 3, 4) and windows[-1][1] == date(2010, 12, 31)
    assert windows[0][1] == windows[0][0] + timedelta(days=1094)
    for (_, previous_end), (next_start, _) in zip(windows, windows[1:], strict=False):
        assert next_start == previous_end + timedelta(days=1)
    assert all((end - start).days + 1 <= 1095 for start, end in windows)


@pytest.mark.asyncio
async def test_bcra_a_range_of_exactly_one_window_is_one_request(monkeypatch: pytest.MonkeyPatch):
    start = date(2026, 1, 1)
    asked = _route(monkeypatch, bcra_mod, lambda request: _json(EMPTY))

    await BCRAProvider().fetch_rates((start, start + timedelta(days=1094)), ["USD"])
    assert len(asked) == 1
    await BCRAProvider().fetch_rates((start, start + timedelta(days=1095)), ["USD"])
    assert len(asked) == 3


@pytest.mark.asyncio
async def test_bcra_windows_of_one_currency_are_joined_and_ascending(monkeypatch: pytest.MonkeyPatch):
    def answer(request: httpx.Request) -> httpx.Response:
        if _from_of(request) == date(2026, 1, 1):
            return _json(_body(_day("2028-12-29", _rec("REF", "30")), _day("2026-01-02", _rec("REF", "10"))))
        return _json(_body(_day("2029-01-05", _rec("REF", "40"))))

    _route(monkeypatch, bcra_mod, answer)

    rates = await BCRAProvider().fetch_rates((date(2026, 1, 1), date(2029, 1, 10)), ["USD"])

    assert [row[0] for row in rates["USD"]] == [date(2026, 1, 2), date(2028, 12, 29), date(2029, 1, 5)]


@pytest.mark.asyncio
async def test_bcra_every_asked_currency_is_a_key_and_ars_is_none(monkeypatch: pytest.MonkeyPatch):
    _route(monkeypatch, bcra_mod, _by_code({"REF": USD_BODY}))

    rates = await BCRAProvider().fetch_rates(RANGE, ["USD", "ARS", "EUR"])

    assert set(rates) == {"USD", "EUR"}
    assert rates["EUR"] == [] and len(rates["USD"]) == 3


@pytest.mark.asyncio
async def test_bcra_a_currency_outside_the_codes_is_empty_and_not_asked(monkeypatch: pytest.MonkeyPatch):
    asked = _route(monkeypatch, bcra_mod, _by_code({"REF": USD_BODY}))

    rates = await BCRAProvider().fetch_rates(RANGE, ["XDR", "USD"])

    assert rates["XDR"] == [] and len(rates["USD"]) == 3
    assert [_code_of(r) for r in asked] == ["REF"]


@pytest.mark.parametrize(
    ("window", "currencies"),
    [
        pytest.param(RANGE, ["ARS"], id="ars-only"),
        pytest.param(RANGE, ["XDR", "XAU"], id="outside-codes"),
        pytest.param((date(2026, 11, 19), date(2026, 11, 16)), ["USD"], id="start-after-end"),
        pytest.param((date(1999, 1, 1), date(2002, 3, 3)), ["USD"], id="end-before-first-day"),
    ],
)
@pytest.mark.asyncio
async def test_bcra_no_request_when_nothing_can_be_asked(monkeypatch: pytest.MonkeyPatch, window, currencies):
    asked = _route(monkeypatch, bcra_mod, lambda request: _json(USD_BODY))

    rates = await BCRAProvider().fetch_rates(window, currencies)

    assert asked == []
    assert set(rates) == {c for c in currencies if c != "ARS"}
    assert all(rows == [] for rows in rates.values())


# ── What it skips ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bcra_unreadable_records_are_skipped_and_the_others_stay(monkeypatch: pytest.MonkeyPatch):
    """Another code, a zero, a negative, a bad fecha and days out of range lose only their own record."""
    body = _body(
        _day("2026-11-19", _rec("REF", "1562.9893")),
        _day("2026-11-18", _rec("EUR", "1800")),
        _day("2026-11-17", _rec("REF", "0")),
        _day("2026-11-16", _rec("REF", "-3.5")),
        _day("not-a-date", _rec("REF", "1500")),
        _day("2026-11-20", _rec("REF", "1600")),
        _day("2026-11-10", _rec("REF", "1400")),
    )
    _route(monkeypatch, bcra_mod, _by_code({"REF": body}))

    rates = await BCRAProvider().fetch_rates(RANGE, ["USD"])

    assert rates["USD"] == [(date(2026, 11, 19), "USD", "ARS", Decimal("1562.9893"))]


@pytest.mark.asyncio
async def test_bcra_a_date_with_two_different_values_is_dropped_and_equal_ones_kept_once(monkeypatch: pytest.MonkeyPatch):
    body = _body(
        _day("2026-11-19", _rec("REF", "1562.9893")),
        _day("2026-11-18", _rec("REF", "1550"), _rec("REF", "1551")),
        _day("2026-11-17", _rec("REF", "1540"), _rec("REF", "1540.0"), _rec("REF", "1540")),
    )
    _route(monkeypatch, bcra_mod, _by_code({"REF": body}))

    rates = await BCRAProvider().fetch_rates(RANGE, ["USD"])

    assert [row[0] for row in rates["USD"]] == [date(2026, 11, 17), date(2026, 11, 19)]


@pytest.mark.asyncio
async def test_bcra_empty_answer_is_a_currency_without_data_not_an_error(monkeypatch: pytest.MonkeyPatch):
    _route(monkeypatch, bcra_mod, lambda request: _json(EMPTY))

    assert await BCRAProvider().fetch_rates(RANGE, ["USD"]) == {"USD": []}


# ── Windows with holes ───────────────────────────────────────────────────────────

LONG = (date(2002, 3, 4), date(2010, 12, 31))
_WINDOW_STARTS = [date(2002, 3, 4), date(2005, 3, 3), date(2008, 3, 2)]


def _windowed(*window_bodies: str):
    """An answer by window: the body of the first, second, third window, found by ``fechadesde``."""
    return lambda request: _json(window_bodies[_WINDOW_STARTS.index(_from_of(request))])


@pytest.mark.asyncio
async def test_bcra_empty_window_between_two_with_rows_fails_that_currency(monkeypatch: pytest.MonkeyPatch):
    rows = _body(_day("2003-01-02", _rec("REF", "3")))

    def answer(request: httpx.Request) -> httpx.Response:
        if _code_of(request) == "EUR":
            return _json(EMPTY)
        return _windowed(rows, EMPTY, _body(_day("2009-01-02", _rec("REF", "4"))))(request)

    _route(monkeypatch, bcra_mod, answer)

    rates = await BCRAProvider().fetch_rates(LONG, ["USD", "EUR"])
    assert rates["USD"] == [] and rates["EUR"] == []

    # With only USD asked, the failure is the whole call and the message says what happened.
    with pytest.raises(FXServiceError, match="empty"):
        await BCRAProvider().fetch_rates(LONG, ["USD"])


@pytest.mark.asyncio
async def test_bcra_empty_first_window_and_empty_last_window_are_fine(monkeypatch: pytest.MonkeyPatch):
    first = _windowed(EMPTY, _body(_day("2006-05-02", _rec("REF", "3"))), _body(_day("2009-01-02", _rec("REF", "4"))))
    _route(monkeypatch, bcra_mod, first)
    assert [r[0] for r in (await BCRAProvider().fetch_rates(LONG, ["USD"]))["USD"]] == [date(2006, 5, 2), date(2009, 1, 2)]

    last = _windowed(_body(_day("2003-01-02", _rec("REF", "3"))), _body(_day("2006-05-02", _rec("REF", "4"))), EMPTY)
    _route(monkeypatch, bcra_mod, last)
    assert [r[0] for r in (await BCRAProvider().fetch_rates(LONG, ["USD"]))["USD"]] == [date(2003, 1, 2), date(2006, 5, 2)]


@pytest.mark.asyncio
async def test_bcra_a_cut_window_fails_the_currency(monkeypatch: pytest.MonkeyPatch):
    """``count`` 5 but one record returned: the answer was cut, the currency is skipped."""
    cut = _body(_day("2026-11-19", _rec("EUR", "1800")), count=5)
    _route(monkeypatch, bcra_mod, _by_code({"EUR": cut, "REF": USD_BODY}))

    rates = await BCRAProvider().fetch_rates(RANGE, ["EUR", "USD"])
    assert rates["EUR"] == [] and len(rates["USD"]) == 3

    with pytest.raises(FXServiceError, match="cut"):
        await BCRAProvider().fetch_rates(RANGE, ["EUR"])


@pytest.mark.asyncio
async def test_bcra_count_of_records_not_dates_is_what_is_compared(monkeypatch: pytest.MonkeyPatch):
    """One date with two equal records and count 2: not cut."""
    body = _body(_day("2026-11-19", _rec("REF", "1562"), _rec("REF", "1562")), count=2)
    _route(monkeypatch, bcra_mod, _by_code({"REF": body}))

    rates = await BCRAProvider().fetch_rates(RANGE, ["USD"])

    assert rates["USD"] == [(date(2026, 11, 19), "USD", "ARS", Decimal("1562"))]


# ── Pause between requests ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bcra_pauses_before_every_request_but_the_first(monkeypatch: pytest.MonkeyPatch):
    """Two currencies by two windows: four requests, three pauses of 0.3."""
    monkeypatch.setattr(BCRAProvider, "PAUSE_SECONDS", 0.3)
    slept: list[float] = []

    async def record(seconds: float) -> None:
        slept.append(seconds)

    monkeypatch.setattr(bcra_mod.asyncio, "sleep", record)
    asked = _route(monkeypatch, bcra_mod, lambda request: _json(EMPTY))
    start = date(2026, 1, 1)

    await BCRAProvider().fetch_rates((start, start + timedelta(days=1100)), ["USD", "EUR"])

    assert len(asked) == 4
    assert slept == [0.3, 0.3, 0.3]


@pytest.mark.asyncio
async def test_bcra_one_request_needs_no_pause(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(BCRAProvider, "PAUSE_SECONDS", 0.3)
    slept: list[float] = []

    async def record(seconds: float) -> None:
        slept.append(seconds)

    monkeypatch.setattr(bcra_mod.asyncio, "sleep", record)
    _route(monkeypatch, bcra_mod, _by_code({"REF": USD_BODY}))

    await BCRAProvider().fetch_rates(RANGE, ["USD"])

    assert slept == []


# ── Errors ───────────────────────────────────────────────────────────────────────

_BAD_ANSWERS = [
    pytest.param(lambda request: _json("Internal error", status=500), id="http-500"),
    pytest.param(lambda request: _json('{"status":400,"errorMessages":["Parámetro erróneo: fechadesde"]}', status=400), id="http-400"),
    pytest.param(lambda request: httpx.Response(200, headers={"content-type": "text/html"}, text="<!DOCTYPE html><html></html>"), id="html-page"),
    pytest.param(lambda request: httpx.Response(200, text="not json at all"), id="non-json"),
    pytest.param(lambda request: _json('{"status":200,"metadata":{"resultset":{"count":0}}}'), id="no-results"),
    pytest.param(lambda request: _json('{"status":200,"results":{"fecha":"2026-11-19"}}'), id="results-not-a-list"),
]


@pytest.mark.parametrize("answer", _BAD_ANSWERS)
@pytest.mark.asyncio
async def test_bcra_one_failed_currency_is_empty_and_the_others_are_returned(monkeypatch: pytest.MonkeyPatch, answer):
    def route(request: httpx.Request) -> httpx.Response:
        return answer(request) if _code_of(request) == "EUR" else _json(USD_BODY)

    asked = _route(monkeypatch, bcra_mod, route)

    rates = await BCRAProvider().fetch_rates(RANGE, ["EUR", "USD"])

    assert rates["EUR"] == [] and len(rates["USD"]) == 3
    assert len(asked) == 2


@pytest.mark.asyncio
async def test_bcra_transport_failure_of_one_currency_does_not_lose_the_others(monkeypatch: pytest.MonkeyPatch):
    def route(request: httpx.Request) -> httpx.Response:
        if _code_of(request) == "EUR":
            raise httpx.ConnectError("no route", request=request)
        return _json(USD_BODY)

    _route(monkeypatch, bcra_mod, route)

    rates = await BCRAProvider().fetch_rates(RANGE, ["EUR", "USD"])

    assert rates["EUR"] == [] and len(rates["USD"]) == 3


@pytest.mark.asyncio
async def test_bcra_a_failed_later_window_loses_only_its_currency(monkeypatch: pytest.MonkeyPatch):
    def route(request: httpx.Request) -> httpx.Response:
        if _code_of(request) == "EUR" and _from_of(request) > date(2026, 1, 1):
            return _json("boom", status=500)
        return _json(_body(_day("2026-02-02", _rec(_code_of(request), "10"))))

    _route(monkeypatch, bcra_mod, route)

    rates = await BCRAProvider().fetch_rates((date(2026, 1, 1), date(2029, 1, 10)), ["EUR", "USD"])

    assert rates["EUR"] == [] and len(rates["USD"]) == 1


@pytest.mark.parametrize(
    "answer",
    [
        pytest.param(lambda request: _json("Internal error", status=500), id="http-500"),
        pytest.param(lambda request: _json('{"status":400,"errorMessages":["bad"]}', status=400), id="http-400"),
    ],
)
@pytest.mark.asyncio
async def test_bcra_every_currency_failed_is_a_service_error(monkeypatch: pytest.MonkeyPatch, answer):
    _route(monkeypatch, bcra_mod, answer)

    with pytest.raises(FXServiceError) as refused:
        await BCRAProvider().fetch_rates(RANGE, ["USD", "EUR"])

    assert not isinstance(refused.value, FXRateLimitedError)


@pytest.mark.asyncio
async def test_bcra_every_currency_unreachable_is_a_service_error(monkeypatch: pytest.MonkeyPatch):
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    _route(monkeypatch, bcra_mod, refuse)

    with pytest.raises(FXServiceError):
        await BCRAProvider().fetch_rates(RANGE, ["USD"])


@pytest.mark.asyncio
async def test_bcra_too_many_requests_is_a_rate_limit_and_stops_the_call(monkeypatch: pytest.MonkeyPatch):
    """HTTP 429 on AUD (first in sorted order) raises ``FXRateLimitedError``: the currencies queued behind the three in
    flight (AUD, AWG, BOB) are never asked."""

    def answer(request: httpx.Request) -> httpx.Response:
        if _code_of(request) == "AUD":
            return httpx.Response(429, headers={"Retry-After": "30"})
        return _json(USD_BODY)

    asked = _route(monkeypatch, bcra_mod, answer)

    with pytest.raises(FXRateLimitedError):
        await BCRAProvider().fetch_rates(RANGE, ["USD", "EUR", "CHF", "BOB", "AWG", "AUD"])

    codes = {_code_of(r) for r in asked}
    assert "AUD" in codes
    assert codes <= {"AUD", "AWG", "BOB"}, f"a currency queued after the refusal was asked: {sorted(codes)}"


@pytest.mark.asyncio
async def test_bcra_too_many_requests_in_a_later_window_is_a_rate_limit(monkeypatch: pytest.MonkeyPatch):
    def answer(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429) if _from_of(request) > date(2026, 1, 1) else _json(EMPTY)

    _route(monkeypatch, bcra_mod, answer)

    with pytest.raises(FXRateLimitedError):
        await BCRAProvider().fetch_rates((date(2026, 1, 1), date(2029, 1, 10)), ["USD"])


@pytest.mark.asyncio
async def test_bcra_asks_at_most_three_currencies_at_once(monkeypatch: pytest.MonkeyPatch):
    """Six currencies: never more than ``MAX_PARALLEL`` (3) in flight, every currency asked once and its value returned."""
    in_flight = 0
    peak = 0
    asked: list[str] = []

    async def fake_fetch_one(self, currency: str, start: date, end: date):
        nonlocal in_flight, peak
        in_flight += 1
        peak = max(peak, in_flight)
        asked.append(currency)
        for _ in range(5):
            await asyncio.sleep(0)
        in_flight -= 1
        return [(end, Decimal("1.5"))]

    monkeypatch.setattr(BCRAProvider, "_fetch_one", fake_fetch_one)
    currencies = ["AUD", "BRL", "CHF", "EUR", "JPY", "USD"]

    rates = await BCRAProvider().fetch_rates(RANGE, currencies)

    assert BCRAProvider.MAX_PARALLEL == 3
    assert peak == 3
    assert sorted(asked) == currencies
    for currency in currencies:
        assert rates[currency] == [(RANGE[1], currency, "ARS", Decimal("1.5"))]

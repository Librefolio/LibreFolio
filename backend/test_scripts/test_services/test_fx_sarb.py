"""SARB FX provider: one JSON series per currency, mixed direction (rand per unit or unit per rand) and what it refuses (no network, no DB, no server).

Lane 75, wave 2, lot L25 (plan ``plan-phase02FxCentralBanksOndata2.prompt.md``). Measured on the real feed on 19/11/2026:

- The API help page (``/SarbWebApi/Help``) answers 404, so the series codes come from
  ``…/WebIndicators/HistoricalExchangeRatesDaily/``, the list behind the bank's «Selected Historical Rates» page.
- Direction is mixed: 3 series are «Rand per X» (USD, GBP, EUR), 21 are «X per Rand» (CHF 0.0488 per ZAR).
- Values have 4 decimals (``FormatNumber 0.0000``); the answer is a JSON list, newest first.
- An unknown code, or a range without data (a weekend), answers ``[]``.
- The full history of one series is ~4 MB in ~7 s; from 2010 it is ~1.5 s.

Every answer here is synthetic, written by hand in the feed's shape, never data downloaded from the bank.

Isolation: PURE. ``fetch_rates`` and ``get_supported_currencies`` run whole, their module's ``httpx`` replaced for the
test by the real module whose ``AsyncClient`` answers through an ``httpx.MockTransport`` (``_route``, from
``test_rate_limit_http_providers.py``). The pause between series is zero, or a recorder, never a real sleep.
"""

from __future__ import annotations

import asyncio
from datetime import date
from decimal import Decimal

import httpx
import pytest

from backend.app.services.fx.base import FXRateLimitedError, FXServiceError
from backend.app.services.fx_providers.sarb import plugin as sarb_mod
from backend.app.services.fx_providers.sarb.plugin import SARBProvider
from backend.test_scripts.test_services.test_rate_limit_http_providers import _route

SERIES_URL = "https://custom.resbank.co.za/SarbWebApi/WebIndicators/Shared/GetTimeseriesObservations"
RANGE = (date(2026, 11, 16), date(2026, 11, 19))
DESCRIPTION = "Weighted average of the banks' daily rates at approximately 10:30 am."


def _row(day: str, value: str, title: str = "Rand per US Dollar") -> str:
    """One observation as the feed writes it; ``value`` is the raw JSON text of the number."""
    fields = [
        f'"Period":"{day}T00:00:00"',
        f'"Timeseries":"{title}"',
        f'"Description":"{DESCRIPTION}"',
        f'"Value":{value}',
        '"FormatNumber":"0.0000"',
        '"FormatDate":"yyyy-MM-dd"',
    ]
    return "{" + ",".join(fields) + "}"


def _feed(*rows: str) -> str:
    """A JSON list from rows given newest first, as the bank sends it."""
    return "[" + ",".join(rows) + "]"


def _json(body: str, status: int = 200) -> httpx.Response:
    return httpx.Response(status, headers={"content-type": "application/json"}, content=body.encode())


def _code_of(request: httpx.Request) -> str:
    """The series code of a request (``…/GetTimeseriesObservations/EXCX135D/2026-11-16/2026-11-19``)."""
    return request.url.path.split("/")[-3]


USD_FEED = _feed(_row("2026-11-19", "17.2532"), _row("2026-11-18", "17.3000"), _row("2026-11-17", "17.4100"))
CHF_FEED = _feed(_row("2026-11-19", "0.0488", "CHF per Rand"), _row("2026-11-18", "0.0490", "CHF per Rand"))
JPY_FEED = _feed(_row("2026-11-19", "9.2609", "Yen per Rand"), _row("2026-11-18", "9.3000", "Yen per Rand"))


@pytest.fixture(autouse=True)
def _no_pause(monkeypatch: pytest.MonkeyPatch) -> None:
    """No test waits between two series, unless it records the pause itself."""
    monkeypatch.setattr(SARBProvider, "PAUSE_SECONDS", 0)


def _by_code(feeds: dict[str, str]):
    """An answer function serving the feed of the series asked; an unknown code gets ``[]``, like the bank."""
    return lambda request: _json(feeds.get(_code_of(request), "[]"))


# ── Direction and values ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sarb_rand_per_unit_series_is_one_unit_in_zar(monkeypatch: pytest.MonkeyPatch):
    """«Rand per US Dollar 17.2532» is 1 USD = 17.2532 ZAR: ``(d, USD, ZAR, value)``, in ascending date order."""
    _route(monkeypatch, sarb_mod, _by_code({"EXCX135D": USD_FEED}))

    rates = await SARBProvider().fetch_rates(RANGE, ["USD"])

    assert rates["USD"] == [
        (date(2026, 11, 17), "USD", "ZAR", Decimal("17.4100")),
        (date(2026, 11, 18), "USD", "ZAR", Decimal("17.3000")),
        (date(2026, 11, 19), "USD", "ZAR", Decimal("17.2532")),
    ]


@pytest.mark.asyncio
async def test_sarb_unit_per_rand_series_is_one_zar_in_the_currency(monkeypatch: pytest.MonkeyPatch):
    """«CHF per Rand 0.0488» is 1 ZAR = 0.0488 CHF and «Yen per Rand 9.2609» is 1 ZAR = 9.2609 JPY: ZAR is the source."""
    _route(monkeypatch, sarb_mod, _by_code({"EXCB016D": CHF_FEED, "EXCB120D": JPY_FEED}))

    rates = await SARBProvider().fetch_rates(RANGE, ["CHF", "JPY"])

    assert rates["CHF"] == [
        (date(2026, 11, 18), "ZAR", "CHF", Decimal("0.0490")),
        (date(2026, 11, 19), "ZAR", "CHF", Decimal("0.0488")),
    ]
    assert rates["JPY"][-1] == (date(2026, 11, 19), "ZAR", "JPY", Decimal("9.2609"))


@pytest.mark.asyncio
async def test_sarb_values_are_exact_decimals_of_the_json_text(monkeypatch: pytest.MonkeyPatch):
    """``0.0488`` is ``Decimal("0.0488")``, never a float artefact; the type is ``Decimal``."""
    _route(monkeypatch, sarb_mod, _by_code({"EXCB016D": _feed(_row("2026-11-19", "0.0488"))}))

    rates = await SARBProvider().fetch_rates(RANGE, ["CHF"])

    value = rates["CHF"][0][3]
    assert isinstance(value, Decimal)
    assert str(value) == "0.0488"


@pytest.mark.asyncio
async def test_sarb_mixed_direction_in_one_call(monkeypatch: pytest.MonkeyPatch):
    """USD (rand per unit) and CHF (unit per rand) together keep their own direction."""
    _route(monkeypatch, sarb_mod, _by_code({"EXCX135D": USD_FEED, "EXCB016D": CHF_FEED}))

    rates = await SARBProvider().fetch_rates(RANGE, ["USD", "CHF"])

    assert (rates["USD"][0][1], rates["USD"][0][2]) == ("USD", "ZAR")
    assert (rates["CHF"][0][1], rates["CHF"][0][2]) == ("ZAR", "CHF")


# ── Requests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sarb_asks_one_get_per_currency_in_sorted_order_with_a_path_only_url(monkeypatch: pytest.MonkeyPatch):
    """CHF, JPY, USD asked in that order, each on ``SERIES_URL/<code>/<start>/<end>``, no query string."""
    asked = _route(monkeypatch, sarb_mod, lambda request: _json("[]"))

    await SARBProvider().fetch_rates(RANGE, ["USD", "JPY", "CHF"])

    assert [str(r.url) for r in asked] == [
        f"{SERIES_URL}/EXCB016D/2026-11-16/2026-11-19",
        f"{SERIES_URL}/EXCB120D/2026-11-16/2026-11-19",
        f"{SERIES_URL}/EXCX135D/2026-11-16/2026-11-19",
    ]
    assert all(r.method == "GET" and r.url.query == b"" for r in asked)


@pytest.mark.asyncio
async def test_sarb_asks_from_2010_for_min_and_for_an_earlier_start(monkeypatch: pytest.MonkeyPatch):
    """``"min"`` and any earlier start begin at 2010-01-01."""
    asked = _route(monkeypatch, sarb_mod, lambda request: _json("[]"))

    await SARBProvider().fetch_rates(("min", date(2026, 11, 19)), ["USD"])
    await SARBProvider().fetch_rates((date(1999, 1, 1), date(2026, 11, 19)), ["USD"])

    assert [str(r.url) for r in asked] == [f"{SERIES_URL}/EXCX135D/2010-01-01/2026-11-19"] * 2


@pytest.mark.asyncio
async def test_sarb_every_asked_currency_is_a_key_and_zar_is_none(monkeypatch: pytest.MonkeyPatch):
    """The base currency is no key; a currency answered ``[]`` stays a key with ``[]``."""
    _route(monkeypatch, sarb_mod, _by_code({"EXCX135D": USD_FEED}))

    rates = await SARBProvider().fetch_rates(RANGE, ["USD", "ZAR", "CHF"])

    assert set(rates) == {"USD", "CHF"}
    assert rates["CHF"] == [] and len(rates["USD"]) == 3


@pytest.mark.asyncio
async def test_sarb_a_currency_outside_the_series_is_empty_and_not_asked(monkeypatch: pytest.MonkeyPatch):
    """XXX is not in ``SERIES``: its key is ``[]`` and only USD costs a request."""
    asked = _route(monkeypatch, sarb_mod, _by_code({"EXCX135D": USD_FEED}))

    rates = await SARBProvider().fetch_rates(RANGE, ["XXX", "USD"])

    assert rates["XXX"] == [] and len(rates["USD"]) == 3
    assert len(asked) == 1


@pytest.mark.asyncio
async def test_sarb_serves_rub_as_roubles_per_rand(monkeypatch: pytest.MonkeyPatch):
    """RUB (``EXCB110D``, «Russia: Rouble per Rand») is served since the developer's answer to Q3 (19/11/2026): one
    request on its series, ``(d, "ZAR", "RUB", v)``, never inverted."""
    rub = _feed(_row("2026-11-19", "4.7549", "Russia: Rouble per Rand"))
    asked = _route(monkeypatch, sarb_mod, _by_code({"EXCB110D": rub}))

    rates = await SARBProvider().fetch_rates(RANGE, ["RUB"])

    assert rates == {"RUB": [(date(2026, 11, 19), "ZAR", "RUB", Decimal("4.7549"))]}
    assert [_code_of(request) for request in asked] == ["EXCB110D"]


def test_sarb_note_names_the_rouble_neutrally_in_every_language():
    """The note says where the rouble rate comes from, in the four languages (Q3: a neutral note)."""
    for language, text in SARBProvider().warning_i18n.items():
        assert "RUB" in text, f"{language}: the note does not name RUB"


@pytest.mark.asyncio
async def test_sarb_asks_nothing_without_wanted_series_or_with_an_inverted_range(monkeypatch: pytest.MonkeyPatch):
    asked = _route(monkeypatch, sarb_mod, lambda request: _json(USD_FEED))

    assert await SARBProvider().fetch_rates(RANGE, ["ZAR"]) == {}
    assert await SARBProvider().fetch_rates((date(2026, 11, 19), date(2026, 11, 16)), ["USD"]) == {"USD": []}
    assert asked == []


@pytest.mark.asyncio
async def test_sarb_other_base_currency_is_refused(monkeypatch: pytest.MonkeyPatch):
    asked = _route(monkeypatch, sarb_mod, _by_code({"EXCX135D": USD_FEED}))

    with pytest.raises(ValueError):
        await SARBProvider().fetch_rates(RANGE, ["USD"], base_currency="EUR")

    assert len((await SARBProvider().fetch_rates(RANGE, ["USD"], base_currency="ZAR"))["USD"]) == 3
    assert len((await SARBProvider().fetch_rates(RANGE, ["USD"], base_currency=None))["USD"]) == 3
    assert len(asked) == 2


# ── What it skips ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sarb_unreadable_rows_are_skipped_and_the_others_stay(monkeypatch: pytest.MonkeyPatch):
    """A null, a zero, a negative, a text Value, a bad Period and a day out of range lose only their own row."""
    body = _feed(
        _row("2026-11-19", "17.2532"),
        _row("2026-11-18", "null"),
        _row("2026-11-17", "0"),
        _row("2026-11-16", "-3.5"),
        _row("2026-11-15", '"abc"'),
        _row("not-a-date", "17.0"),
        _row("2026-11-20", "17.9"),
        _row("2026-11-10", "17.1"),
    )
    _route(monkeypatch, sarb_mod, _by_code({"EXCX135D": body}))

    rates = await SARBProvider().fetch_rates(RANGE, ["USD"])

    assert rates["USD"] == [(date(2026, 11, 19), "USD", "ZAR", Decimal("17.2532"))]


@pytest.mark.asyncio
async def test_sarb_empty_list_is_a_currency_without_data_not_an_error(monkeypatch: pytest.MonkeyPatch):
    """A weekend (``[]``) gives an empty list and no exception."""
    _route(monkeypatch, sarb_mod, lambda request: _json("[]"))

    assert await SARBProvider().fetch_rates(RANGE, ["USD"]) == {"USD": []}


# ── Pause between series ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sarb_pauses_between_two_series_but_not_before_the_first(monkeypatch: pytest.MonkeyPatch):
    """Three currencies: two pauses of ``PAUSE_SECONDS`` (0.3), none before the first request."""
    monkeypatch.setattr(SARBProvider, "PAUSE_SECONDS", 0.3)
    slept: list[float] = []

    async def record(seconds: float) -> None:
        slept.append(seconds)

    monkeypatch.setattr(sarb_mod.asyncio, "sleep", record)
    asked = _route(monkeypatch, sarb_mod, lambda request: _json("[]"))

    await SARBProvider().fetch_rates(RANGE, ["USD", "CHF", "JPY"])

    assert len(asked) == 3
    assert slept == [0.3, 0.3]


@pytest.mark.asyncio
async def test_sarb_one_series_needs_no_pause(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(SARBProvider, "PAUSE_SECONDS", 0.3)
    slept: list[float] = []

    async def record(seconds: float) -> None:
        slept.append(seconds)

    monkeypatch.setattr(sarb_mod.asyncio, "sleep", record)
    _route(monkeypatch, sarb_mod, _by_code({"EXCX135D": USD_FEED}))

    await SARBProvider().fetch_rates(RANGE, ["USD"])

    assert slept == []


# ── Errors ───────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sarb_too_many_requests_is_a_rate_limit_and_stops_the_series(monkeypatch: pytest.MonkeyPatch):
    """HTTP 429 on AUD (first in sorted order) raises ``FXRateLimitedError`` for the whole call: the series queued behind
    the three in flight (JPY, USD) are never asked (lane 75, L25c: at most 3 at once, a 429 stops the call as in BOE)."""

    def answer(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"Retry-After": "30"}) if _code_of(request) == "EXCB080D" else _json(CHF_FEED)

    asked = _route(monkeypatch, sarb_mod, answer)

    with pytest.raises(FXRateLimitedError):
        await SARBProvider().fetch_rates(RANGE, ["USD", "JPY", "CHF", "BWP", "AUD"])

    codes = {_code_of(r) for r in asked}
    assert "EXCB080D" in codes
    assert codes <= {"EXCB080D", "EXCB051D", "EXCB016D"}, f"a series queued after the refusal was asked: {sorted(codes)}"


@pytest.mark.asyncio
async def test_sarb_asks_at_most_three_series_at_once(monkeypatch: pytest.MonkeyPatch):
    """Six currencies: never more than ``MAX_PARALLEL`` (3) requests in flight, every currency still asked once and its
    rows returned (lane 75, L25c, consultant's decision of 19/11/2026)."""
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
        return [(end, currency, "ZAR", Decimal("1.0"))]

    monkeypatch.setattr(SARBProvider, "_fetch_one", fake_fetch_one)
    currencies = ["AUD", "BWP", "CHF", "JPY", "KES", "USD"]

    rates = await SARBProvider().fetch_rates(RANGE, currencies)

    assert SARBProvider.MAX_PARALLEL == 3
    assert peak == 3
    assert sorted(asked) == currencies
    assert all(len(rates[c]) == 1 for c in currencies)


_NOT_A_SERIES = [
    pytest.param(lambda request: _json("Internal error", status=500), id="http-500"),
    pytest.param(lambda request: httpx.Response(200, headers={"content-type": "text/html"}, text="<!DOCTYPE html><html></html>"), id="html-page"),
    pytest.param(lambda request: httpx.Response(200, text="not json at all"), id="non-json"),
    pytest.param(lambda request: _json('{"Message":"An error has occurred."}'), id="json-not-a-list"),
]


@pytest.mark.parametrize("answer", _NOT_A_SERIES)
@pytest.mark.asyncio
async def test_sarb_one_failed_series_is_empty_and_the_others_are_returned(monkeypatch: pytest.MonkeyPatch, answer):
    """CHF fails in any of four ways: its key is ``[]``, USD is still asked and returned."""

    def route(request: httpx.Request) -> httpx.Response:
        return answer(request) if _code_of(request) == "EXCB016D" else _json(USD_FEED)

    asked = _route(monkeypatch, sarb_mod, route)

    rates = await SARBProvider().fetch_rates(RANGE, ["CHF", "USD"])

    assert rates["CHF"] == []
    assert len(rates["USD"]) == 3
    assert len(asked) == 2


@pytest.mark.asyncio
async def test_sarb_transport_failure_of_one_series_does_not_lose_the_others(monkeypatch: pytest.MonkeyPatch):
    def route(request: httpx.Request) -> httpx.Response:
        if _code_of(request) == "EXCB016D":
            raise httpx.ConnectError("no route", request=request)
        return _json(USD_FEED)

    _route(monkeypatch, sarb_mod, route)

    rates = await SARBProvider().fetch_rates(RANGE, ["CHF", "USD"])

    assert rates["CHF"] == [] and len(rates["USD"]) == 3


@pytest.mark.asyncio
async def test_sarb_every_series_failed_is_a_service_error(monkeypatch: pytest.MonkeyPatch):
    """All wanted currencies fail: ``FXServiceError``, and not the rate-limit subclass."""
    _route(monkeypatch, sarb_mod, lambda request: _json("Internal error", status=500))

    with pytest.raises(FXServiceError) as refused:
        await SARBProvider().fetch_rates(RANGE, ["USD", "CHF"])

    assert not isinstance(refused.value, FXRateLimitedError)


@pytest.mark.asyncio
async def test_sarb_every_series_unreachable_is_a_service_error(monkeypatch: pytest.MonkeyPatch):
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    _route(monkeypatch, sarb_mod, refuse)

    with pytest.raises(FXServiceError):
        await SARBProvider().fetch_rates(RANGE, ["USD"])


# ── Catalogue ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sarb_catalogue_is_the_series_plus_zar_without_a_request(monkeypatch: pytest.MonkeyPatch):
    """26 sorted codes (25 series and ZAR), RUB among them, and not one request made."""
    asked = _route(monkeypatch, sarb_mod, lambda request: _json("[]"))

    currencies = await SARBProvider().get_supported_currencies()

    assert currencies == sorted([*sarb_mod.SERIES, "ZAR"])
    assert len(currencies) == 26 and "RUB" in currencies
    assert asked == []
    assert SARBProvider().fallback_currencies == currencies


# ── Identity ─────────────────────────────────────────────────────────────────────


def test_sarb_identity_urls_and_series_table():
    provider = SARBProvider()
    assert (provider.code, provider.base_currency, provider.warning_level) == ("SARB", "ZAR", "warning")
    assert provider.docs_url == "/mkdocs/user/fx/providers/sarb/"
    assert sarb_mod.SERIES_URL == SERIES_URL
    assert SARBProvider.FIRST_DAY == date(2010, 1, 1)
    assert len(sarb_mod.SERIES) == 25
    assert sarb_mod.SERIES["RUB"] == ("EXCB110D", False)
    assert {c for c, (_, per_unit) in sarb_mod.SERIES.items() if per_unit} == {"USD", "GBP", "EUR"}
    assert sarb_mod.SERIES["USD"] == ("EXCX135D", True)
    assert sarb_mod.SERIES["GBP"] == ("EXCZ001D", True)
    assert sarb_mod.SERIES["EUR"] == ("EXCZ002D", True)
    assert sarb_mod.SERIES["CHF"] == ("EXCB016D", False)
    assert sarb_mod.SERIES["JPY"] == ("EXCB120D", False)


def test_sarb_pause_between_series_is_a_third_of_a_second_by_default(monkeypatch: pytest.MonkeyPatch):
    """The class default, seen with the fixture's zero undone."""
    monkeypatch.undo()
    assert SARBProvider.PAUSE_SECONDS == 0.3

"""CBC FX provider: the Central Bank of the Republic of China (Taiwan) interbank closing rate of the New Taiwan dollar (no network, no DB, no server).

Lane 75, wave 2, lot L29 (plan ``plan-phase02FxCentralBanksOndata2.prompt.md``). Measured on the real feed on 19/11/2026:

- One GET of the open-data URL answers the whole series: 4 691 rows from 20080102, ~190 KB, ~2 s. The endpoint has no
  date filter, so the plugin filters the asked range itself.
- The answer is a JSON list, oldest first, with no duplicate and every value numeric; each row is an object with a
  Chinese key for the day (``日期``, ``yyyyMMdd``) and ``NTD_USD`` (a number as text). Today's value is present
  (published between 16:00 and 17:00 Taiwan time).
- The rate is TWD per 1 USD, the interbank closing rate of Taipei Forex Inc. Licence: Open Government Data License,
  version 1 (data.gov.tw dataset 7232), attribution to the CBC.
- The CBC's 18-currency table ``BP01D01`` is left out: it is about two weeks late, and BDI publishes those currencies
  daily.

Every answer here is synthetic, written by hand in the feed's shape, never data downloaded from the CBC.

Isolation: PURE. ``fetch_rates`` and ``get_supported_currencies`` run whole, their module's ``httpx`` replaced for the
test by the real module whose ``AsyncClient`` answers through an ``httpx.MockTransport`` (``_route``, from
``test_rate_limit_http_providers.py``). No real sleep.
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

import httpx
import pytest

from backend.app.services.fx.base import FXRateLimitedError, FXServiceError
from backend.app.services.fx_providers.cbc import plugin as cbc_mod
from backend.app.services.fx_providers.cbc.plugin import CBCProvider
from backend.test_scripts.test_services.test_rate_limit_http_providers import _route

DATA_URL = "https://cpx.cbc.gov.tw/api/OpenData/FTDOpenData_Day"
RANGE = (date(2026, 11, 10), date(2026, 11, 19))


def _row(day: str, value: str) -> dict:
    """One row as the feed writes it: the day as ``yyyyMMdd`` under the Chinese key, the value as text."""
    return {"日期": day, "NTD_USD": value}


def _answer(rows: object, status: int = 200) -> httpx.Response:
    """A JSON body as the endpoint sends it."""
    return httpx.Response(status, headers={"content-type": "application/json"}, content=json.dumps(rows).encode())


GOOD = [
    _row("20261118", "32.947"),
    _row("20261119", "32.942"),
]


# ── Direction and values ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cbc_one_usd_is_so_many_dollars_oldest_first(monkeypatch: pytest.MonkeyPatch):
    """«32.942» is 1 USD = 32.942 TWD, one tuple per row, in ascending date order."""
    _route(monkeypatch, cbc_mod, lambda request: _answer(GOOD))

    rates = await CBCProvider().fetch_rates(RANGE, ["USD"])

    assert rates["USD"] == [
        (date(2026, 11, 18), "USD", "TWD", Decimal("32.947")),
        (date(2026, 11, 19), "USD", "TWD", Decimal("32.942")),
    ]


@pytest.mark.asyncio
async def test_cbc_values_are_decimals_made_from_the_text(monkeypatch: pytest.MonkeyPatch):
    """The value is a ``Decimal`` built from the string, not from a float."""
    _route(monkeypatch, cbc_mod, lambda request: _answer(GOOD))

    value = (await CBCProvider().fetch_rates(RANGE, ["USD"]))["USD"][-1][3]

    assert isinstance(value, Decimal)
    assert str(value) == "32.942"


@pytest.mark.asyncio
async def test_cbc_a_dump_from_2008_asked_for_two_days_gives_two_rows(monkeypatch: pytest.MonkeyPatch):
    """The whole series comes back; only the days inside the asked range are kept, ends included."""
    dump = [
        _row("20080102", "32.5"),
        _row("20150615", "30.9"),
        _row("20261117", "32.9"),
        _row("20261118", "32.947"),
        _row("20261119", "32.942"),
    ]
    _route(monkeypatch, cbc_mod, lambda request: _answer(dump))

    rates = await CBCProvider().fetch_rates((date(2026, 11, 18), date(2026, 11, 19)), ["USD"])

    assert rates["USD"] == [
        (date(2026, 11, 18), "USD", "TWD", Decimal("32.947")),
        (date(2026, 11, 19), "USD", "TWD", Decimal("32.942")),
    ]


@pytest.mark.asyncio
async def test_cbc_rows_in_any_order_come_out_in_ascending_date_order(monkeypatch: pytest.MonkeyPatch):
    """Even if the feed were not sorted, the tuples are ascending."""
    _route(monkeypatch, cbc_mod, lambda request: _answer(list(reversed(GOOD))))

    rates = await CBCProvider().fetch_rates(RANGE, ["USD"])

    assert [d for d, _, _, _ in rates["USD"]] == [date(2026, 11, 18), date(2026, 11, 19)]


@pytest.mark.asyncio
async def test_cbc_a_range_without_rows_gives_an_empty_list(monkeypatch: pytest.MonkeyPatch):
    """Rows exist but none falls inside the asked range: ``{"USD": []}``."""
    _route(monkeypatch, cbc_mod, lambda request: _answer(GOOD))

    rates = await CBCProvider().fetch_rates((date(2026, 1, 1), date(2026, 1, 31)), ["USD"])

    assert rates == {"USD": []}


# ── Requests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cbc_asks_one_get_of_the_url_without_a_query_string(monkeypatch: pytest.MonkeyPatch):
    """GET ``DATA_URL`` once, with no query string: the endpoint has no date filter."""
    asked = _route(monkeypatch, cbc_mod, lambda request: _answer(GOOD))

    await CBCProvider().fetch_rates(RANGE, ["USD"])

    assert len(asked) == 1
    request = asked[0]
    assert request.method == "GET"
    assert f"{request.url.scheme}://{request.url.host}{request.url.path}" == DATA_URL
    assert request.url.query == b""


@pytest.mark.asyncio
async def test_cbc_min_and_an_earlier_start_begin_at_the_first_day(monkeypatch: pytest.MonkeyPatch):
    """``"min"`` and any earlier start are raised to 2008-01-02: a row of 2007 is never returned."""
    dump = [_row("20071231", "32.4"), _row("20080102", "32.5"), _row("20080103", "32.6")]
    _route(monkeypatch, cbc_mod, lambda request: _answer(dump))
    expected = [
        (date(2008, 1, 2), "USD", "TWD", Decimal("32.5")),
        (date(2008, 1, 3), "USD", "TWD", Decimal("32.6")),
    ]

    from_min = await CBCProvider().fetch_rates(("min", date(2008, 1, 3)), ["USD"])
    from_earlier = await CBCProvider().fetch_rates((date(1980, 1, 1), date(2008, 1, 3)), ["USD"])

    assert from_min["USD"] == expected
    assert from_earlier["USD"] == expected


@pytest.mark.asyncio
async def test_cbc_an_end_before_the_first_day_asks_nothing(monkeypatch: pytest.MonkeyPatch):
    """With the start raised to 2008-01-02, an end in 2007 is an inverted range: no request."""
    asked = _route(monkeypatch, cbc_mod, lambda request: _answer(GOOD))

    assert await CBCProvider().fetch_rates(("min", date(2007, 6, 1)), ["USD"]) == {"USD": []}
    assert asked == []


@pytest.mark.asyncio
async def test_cbc_every_asked_currency_but_twd_is_a_key_and_only_usd_is_served(monkeypatch: pytest.MonkeyPatch):
    """EUR is a key with ``[]``, TWD is no key, USD costs the one request."""
    asked = _route(monkeypatch, cbc_mod, lambda request: _answer(GOOD))

    rates = await CBCProvider().fetch_rates(RANGE, ["EUR", "TWD", "USD"])

    assert set(rates) == {"EUR", "USD"}
    assert rates["EUR"] == [] and len(rates["USD"]) == 2
    assert len(asked) == 1


@pytest.mark.asyncio
async def test_cbc_without_usd_asks_nothing(monkeypatch: pytest.MonkeyPatch):
    """EUR alone, or TWD alone: no request."""
    asked = _route(monkeypatch, cbc_mod, lambda request: _answer(GOOD))

    assert await CBCProvider().fetch_rates(RANGE, ["EUR"]) == {"EUR": []}
    assert await CBCProvider().fetch_rates(RANGE, ["TWD"]) == {}
    assert asked == []


@pytest.mark.asyncio
async def test_cbc_inverted_range_asks_nothing(monkeypatch: pytest.MonkeyPatch):
    """Start after end: ``{"USD": []}`` and no request."""
    asked = _route(monkeypatch, cbc_mod, lambda request: _answer(GOOD))

    assert await CBCProvider().fetch_rates((date(2026, 11, 19), date(2026, 11, 10)), ["USD"]) == {"USD": []}
    assert asked == []


@pytest.mark.asyncio
async def test_cbc_other_base_currency_is_refused(monkeypatch: pytest.MonkeyPatch):
    """``base_currency`` EUR raises ``ValueError``; None and TWD are fine."""
    asked = _route(monkeypatch, cbc_mod, lambda request: _answer(GOOD))

    with pytest.raises(ValueError):
        await CBCProvider().fetch_rates(RANGE, ["USD"], base_currency="EUR")

    assert len((await CBCProvider().fetch_rates(RANGE, ["USD"], base_currency="TWD"))["USD"]) == 2
    assert len((await CBCProvider().fetch_rates(RANGE, ["USD"], base_currency=None))["USD"]) == 2
    assert len(asked) == 2


# ── What it skips ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cbc_unreadable_rows_are_skipped_and_the_others_stay(monkeypatch: pytest.MonkeyPatch):
    """A bad day, a text, a zero, a negative and two missing keys lose only their own row."""
    rows = [
        _row("20261110", "32.1"),
        _row("not-a-day", "32.2"),
        _row("20261112", "abc"),
        _row("20261113", "0"),
        _row("20261114", "-32.5"),
        {"日期": "20261115"},
        {"NTD_USD": "32.6"},
        _row("20261118", "32.947"),
    ]
    _route(monkeypatch, cbc_mod, lambda request: _answer(rows))

    rates = await CBCProvider().fetch_rates(RANGE, ["USD"])

    assert rates["USD"] == [
        (date(2026, 11, 10), "USD", "TWD", Decimal("32.1")),
        (date(2026, 11, 18), "USD", "TWD", Decimal("32.947")),
    ]


@pytest.mark.asyncio
async def test_cbc_an_empty_list_is_a_range_without_data_not_an_error(monkeypatch: pytest.MonkeyPatch):
    """``[]`` gives an empty list and no exception."""
    _route(monkeypatch, cbc_mod, lambda request: _answer([]))

    assert await CBCProvider().fetch_rates(RANGE, ["USD"]) == {"USD": []}


# ── Errors ───────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cbc_too_many_requests_is_a_rate_limit(monkeypatch: pytest.MonkeyPatch):
    """HTTP 429 raises ``FXRateLimitedError``."""
    _route(monkeypatch, cbc_mod, lambda request: httpx.Response(429))

    with pytest.raises(FXRateLimitedError):
        await CBCProvider().fetch_rates(RANGE, ["USD"])


@pytest.mark.asyncio
async def test_cbc_http_500_is_a_service_error_and_not_a_rate_limit(monkeypatch: pytest.MonkeyPatch):
    """Any other HTTP error is ``FXServiceError``, not the rate-limit subclass."""
    _route(monkeypatch, cbc_mod, lambda request: httpx.Response(500, text="Internal error"))

    with pytest.raises(FXServiceError) as refused:
        await CBCProvider().fetch_rates(RANGE, ["USD"])

    assert not isinstance(refused.value, FXRateLimitedError)


@pytest.mark.asyncio
async def test_cbc_unreachable_is_a_service_error(monkeypatch: pytest.MonkeyPatch):
    """A transport failure is ``FXServiceError``."""

    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    _route(monkeypatch, cbc_mod, refuse)

    with pytest.raises(FXServiceError):
        await CBCProvider().fetch_rates(RANGE, ["USD"])


@pytest.mark.parametrize(
    "body",
    [
        pytest.param("<!DOCTYPE html><html><body>Maintenance</body></html>", id="html"),
        pytest.param("not json at all", id="non-json"),
        pytest.param('{"error": true, "message": "unavailable"}', id="json-object"),
        pytest.param('"just a string"', id="json-string"),
    ],
)
@pytest.mark.asyncio
async def test_cbc_a_body_that_is_not_a_list_is_a_service_error(monkeypatch: pytest.MonkeyPatch, body: str):
    """An HTML page, non-JSON text, or JSON that is not a list: ``FXServiceError``, never a rate limit."""
    _route(monkeypatch, cbc_mod, lambda request: httpx.Response(200, content=body.encode()))

    with pytest.raises(FXServiceError) as refused:
        await CBCProvider().fetch_rates(RANGE, ["USD"])

    assert not isinstance(refused.value, FXRateLimitedError)


# ── Catalogue and identity ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cbc_catalogue_is_twd_and_usd_without_a_request(monkeypatch: pytest.MonkeyPatch):
    """``["TWD", "USD"]`` and not one request made."""
    asked = _route(monkeypatch, cbc_mod, lambda request: _answer(GOOD))

    currencies = await CBCProvider().get_supported_currencies()

    assert currencies == ["TWD", "USD"]
    assert CBCProvider().fallback_currencies == currencies
    assert asked == []


def test_cbc_identity_urls_and_constants():
    """Code, base, level, docs page and the two module constants."""
    provider = CBCProvider()
    assert (provider.code, provider.base_currency, provider.warning_level) == ("CBC", "TWD", "info")
    assert provider.docs_url == "/mkdocs/user/fx/providers/cbc/"
    assert cbc_mod.DATA_URL == DATA_URL
    assert cbc_mod.FIRST_DAY == date(2008, 1, 2)

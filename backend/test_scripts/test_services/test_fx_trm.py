"""TRM FX provider: Colombia's Tasa Representativa del Mercado from the datos.gov.co Socrata dataset (no network, no DB, no server).

Lane 75, wave 2, lot L28 (plan ``plan-phase02FxCentralBanksOndata2.prompt.md``). Measured on the real feed on 19/11/2026:

- One request with ``$limit=50000`` gives the whole dataset: 8 389 rows from 1991-12-02, ~1 MB, ~3.9 s.
- 1 947 rows span several days (weekends, holidays); there is no gap and no overlap between rows.
- The fields are ``valor`` (a number as text), ``unidad`` (always ``COP``) and ``vigenciadesde`` / ``vigenciahasta``
  (floating timestamps, both ends included).
- The TRM is COP per 1 USD, computed from the previous banking day's spot trades and certified by the
  Superintendencia Financiera de Colombia. Licence CC BY-SA 4.0, attribution to the Superintendencia.
- Decision D2 of the lane: a row is valid on every day from ``vigenciadesde`` to ``vigenciahasta``, so weekends and
  holidays carry the TRM the Superintendencia declares valid for them.

Every answer here is synthetic, written by hand in the feed's shape, never data downloaded from the portal.

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
from backend.app.services.fx_providers.trm import plugin as trm_mod
from backend.app.services.fx_providers.trm.plugin import TRMProvider
from backend.test_scripts.test_services.test_rate_limit_http_providers import _route

DATASET_URL = "https://www.datos.gov.co/resource/32sa-8pi3.json"
RANGE = (date(2026, 11, 10), date(2026, 11, 19))


def _row(value: str, since: str, until: str, unit: str = "COP") -> dict:
    """One row as Socrata writes it: text value, unit and a validity interval of floating timestamps."""
    return {
        "valor": value,
        "unidad": unit,
        "vigenciadesde": f"{since}T00:00:00.000",
        "vigenciahasta": f"{until}T00:00:00.000",
    }


def _answer(rows: object, status: int = 200) -> httpx.Response:
    """A JSON body as the portal sends it."""
    return httpx.Response(status, headers={"content-type": "application/json"}, content=json.dumps(rows).encode())


GOOD = [
    _row("3297.07", "2026-11-11", "2026-11-12"),
    _row("3316.7", "2026-11-14", "2026-11-17"),
]


# ── Direction and values ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_trm_one_usd_is_so_many_pesos_and_a_row_covers_its_whole_interval(monkeypatch: pytest.MonkeyPatch):
    """«3316.7» is 1 USD = 3316.7 COP, and the 14->17 Nov row gives one tuple per day, both ends included, oldest first."""
    _route(monkeypatch, trm_mod, lambda request: _answer(GOOD))

    rates = await TRMProvider().fetch_rates(RANGE, ["USD"])

    assert rates["USD"] == [
        (date(2026, 11, 11), "USD", "COP", Decimal("3297.07")),
        (date(2026, 11, 12), "USD", "COP", Decimal("3297.07")),
        (date(2026, 11, 14), "USD", "COP", Decimal("3316.7")),
        (date(2026, 11, 15), "USD", "COP", Decimal("3316.7")),
        (date(2026, 11, 16), "USD", "COP", Decimal("3316.7")),
        (date(2026, 11, 17), "USD", "COP", Decimal("3316.7")),
    ]


@pytest.mark.asyncio
async def test_trm_values_are_decimals_made_from_the_text(monkeypatch: pytest.MonkeyPatch):
    """The value is a ``Decimal`` built from the string, not from a float."""
    _route(monkeypatch, trm_mod, lambda request: _answer(GOOD))

    value = (await TRMProvider().fetch_rates(RANGE, ["USD"]))["USD"][-1][3]

    assert isinstance(value, Decimal)
    assert str(value) == "3316.7"


@pytest.mark.asyncio
async def test_trm_a_single_day_row_gives_one_tuple(monkeypatch: pytest.MonkeyPatch):
    """A row whose ``vigenciadesde`` equals ``vigenciahasta`` is valid on that one day."""
    _route(monkeypatch, trm_mod, lambda request: _answer([_row("3300.5", "2026-11-13", "2026-11-13")]))

    rates = await TRMProvider().fetch_rates(RANGE, ["USD"])

    assert rates["USD"] == [(date(2026, 11, 13), "USD", "COP", Decimal("3300.5"))]


@pytest.mark.asyncio
async def test_trm_only_the_days_inside_the_asked_range_are_returned(monkeypatch: pytest.MonkeyPatch):
    """Asked 15-16 Nov, the 14->17 Nov row gives two tuples, and the row outside the range gives none."""
    rows = [*GOOD, _row("3000", "2026-11-01", "2026-11-03")]
    _route(monkeypatch, trm_mod, lambda request: _answer(rows))

    rates = await TRMProvider().fetch_rates((date(2026, 11, 15), date(2026, 11, 16)), ["USD"])

    assert rates["USD"] == [
        (date(2026, 11, 15), "USD", "COP", Decimal("3316.7")),
        (date(2026, 11, 16), "USD", "COP", Decimal("3316.7")),
    ]


# ── Requests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_trm_asks_one_get_with_the_exact_query(monkeypatch: pytest.MonkeyPatch):
    """GET ``DATASET_URL`` with ``$where`` on the validity interval, ``$order``, ``$limit`` and ``$offset``."""
    asked = _route(monkeypatch, trm_mod, lambda request: _answer(GOOD))

    await TRMProvider().fetch_rates(RANGE, ["USD"])

    assert len(asked) == 1
    request = asked[0]
    assert request.method == "GET"
    assert f"{request.url.scheme}://{request.url.host}{request.url.path}" == DATASET_URL
    assert dict(request.url.params) == {
        "$where": "vigenciahasta >= '2026-11-10T00:00:00' AND vigenciadesde <= '2026-11-19T00:00:00'",
        "$order": "vigenciadesde",
        "$limit": "50000",
        "$offset": "0",
    }


@pytest.mark.asyncio
async def test_trm_asks_from_1991_for_min_and_for_an_earlier_start(monkeypatch: pytest.MonkeyPatch):
    """``"min"`` and any earlier start begin at 1991-12-02, the first day of the dataset."""
    asked = _route(monkeypatch, trm_mod, lambda request: _answer([]))

    await TRMProvider().fetch_rates(("min", date(2026, 11, 19)), ["USD"])
    await TRMProvider().fetch_rates((date(1980, 1, 1), date(2026, 11, 19)), ["USD"])

    wheres = [r.url.params["$where"] for r in asked]
    assert wheres == ["vigenciahasta >= '1991-12-02T00:00:00' AND vigenciadesde <= '2026-11-19T00:00:00'"] * 2


@pytest.mark.asyncio
async def test_trm_pages_until_a_short_page(monkeypatch: pytest.MonkeyPatch):
    """With ``PAGE_SIZE`` 2 and pages of 2, 2 and 1 rows: three requests, ``$offset`` 0, 2, 4, five days in all."""
    monkeypatch.setattr(trm_mod, "PAGE_SIZE", 2)
    days = [f"2026-11-{n:02d}" for n in range(10, 15)]
    pages = {0: days[0:2], 2: days[2:4], 4: days[4:5]}

    def serve(request: httpx.Request) -> httpx.Response:
        assert request.url.params["$limit"] == "2"
        return _answer([_row("3300", day, day) for day in pages[int(request.url.params["$offset"])]])

    asked = _route(monkeypatch, trm_mod, serve)

    rates = await TRMProvider().fetch_rates(RANGE, ["USD"])

    assert [r.url.params["$offset"] for r in asked] == ["0", "2", "4"]
    assert [d for d, _, _, _ in rates["USD"]] == [date(2026, 11, n) for n in range(10, 15)]


@pytest.mark.asyncio
async def test_trm_every_asked_currency_but_cop_is_a_key_and_only_usd_is_served(monkeypatch: pytest.MonkeyPatch):
    """EUR is a key with ``[]``, COP is no key, USD costs the one request."""
    asked = _route(monkeypatch, trm_mod, lambda request: _answer(GOOD))

    rates = await TRMProvider().fetch_rates(RANGE, ["EUR", "COP", "USD"])

    assert set(rates) == {"EUR", "USD"}
    assert rates["EUR"] == [] and len(rates["USD"]) == 6
    assert len(asked) == 1


@pytest.mark.asyncio
async def test_trm_without_usd_asks_nothing(monkeypatch: pytest.MonkeyPatch):
    """EUR alone, or COP alone: no request."""
    asked = _route(monkeypatch, trm_mod, lambda request: _answer(GOOD))

    assert await TRMProvider().fetch_rates(RANGE, ["EUR"]) == {"EUR": []}
    assert await TRMProvider().fetch_rates(RANGE, ["COP"]) == {}
    assert asked == []


@pytest.mark.asyncio
async def test_trm_inverted_range_asks_nothing(monkeypatch: pytest.MonkeyPatch):
    """Start after end: ``{"USD": []}`` and no request."""
    asked = _route(monkeypatch, trm_mod, lambda request: _answer(GOOD))

    assert await TRMProvider().fetch_rates((date(2026, 11, 19), date(2026, 11, 10)), ["USD"]) == {"USD": []}
    assert asked == []


@pytest.mark.asyncio
async def test_trm_other_base_currency_is_refused(monkeypatch: pytest.MonkeyPatch):
    """``base_currency`` EUR raises ``ValueError``; None and COP are fine."""
    asked = _route(monkeypatch, trm_mod, lambda request: _answer(GOOD))

    with pytest.raises(ValueError):
        await TRMProvider().fetch_rates(RANGE, ["USD"], base_currency="EUR")

    assert len((await TRMProvider().fetch_rates(RANGE, ["USD"], base_currency="COP"))["USD"]) == 6
    assert len((await TRMProvider().fetch_rates(RANGE, ["USD"], base_currency=None))["USD"]) == 6
    assert len(asked) == 2


# ── What it skips ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_trm_unreadable_rows_are_skipped_and_the_others_stay(monkeypatch: pytest.MonkeyPatch):
    """A text, a zero, a negative, another unit, a bad date and an inverted interval lose only their own row."""
    rows = [
        _row("3300", "2026-11-10", "2026-11-10"),
        _row("abc", "2026-11-11", "2026-11-11"),
        _row("0", "2026-11-12", "2026-11-12"),
        _row("-3300", "2026-11-13", "2026-11-13"),
        _row("3300", "2026-11-14", "2026-11-14", unit="USD"),
        {"valor": "3300", "unidad": "COP", "vigenciadesde": "yesterday", "vigenciahasta": "2026-11-15"},
        _row("3300", "2026-11-17", "2026-11-16"),
        _row("3310", "2026-11-18", "2026-11-18"),
    ]
    _route(monkeypatch, trm_mod, lambda request: _answer(rows))

    rates = await TRMProvider().fetch_rates(RANGE, ["USD"])

    assert rates["USD"] == [
        (date(2026, 11, 10), "USD", "COP", Decimal("3300")),
        (date(2026, 11, 18), "USD", "COP", Decimal("3310")),
    ]


@pytest.mark.asyncio
async def test_trm_a_day_covered_by_two_rows_is_dropped_for_both(monkeypatch: pytest.MonkeyPatch):
    """Rows 10->12 and 12->14 overlap on the 12th: that day is dropped (never a random pick), the other days stay."""
    rows = [_row("3300", "2026-11-10", "2026-11-12"), _row("3400", "2026-11-12", "2026-11-14")]
    _route(monkeypatch, trm_mod, lambda request: _answer(rows))

    rates = await TRMProvider().fetch_rates(RANGE, ["USD"])

    assert rates["USD"] == [
        (date(2026, 11, 10), "USD", "COP", Decimal("3300")),
        (date(2026, 11, 11), "USD", "COP", Decimal("3300")),
        (date(2026, 11, 13), "USD", "COP", Decimal("3400")),
        (date(2026, 11, 14), "USD", "COP", Decimal("3400")),
    ]


@pytest.mark.asyncio
async def test_trm_an_empty_list_is_a_range_without_data_not_an_error(monkeypatch: pytest.MonkeyPatch):
    """``[]`` gives an empty list and no exception."""
    _route(monkeypatch, trm_mod, lambda request: _answer([]))

    assert await TRMProvider().fetch_rates(RANGE, ["USD"]) == {"USD": []}


# ── Errors ───────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_trm_too_many_requests_is_a_rate_limit(monkeypatch: pytest.MonkeyPatch):
    """HTTP 429 raises ``FXRateLimitedError``."""
    _route(monkeypatch, trm_mod, lambda request: httpx.Response(429))

    with pytest.raises(FXRateLimitedError):
        await TRMProvider().fetch_rates(RANGE, ["USD"])


@pytest.mark.asyncio
async def test_trm_http_500_is_a_service_error_and_not_a_rate_limit(monkeypatch: pytest.MonkeyPatch):
    """Any other HTTP error is ``FXServiceError``, not the rate-limit subclass."""
    _route(monkeypatch, trm_mod, lambda request: httpx.Response(500, text="Internal error"))

    with pytest.raises(FXServiceError) as refused:
        await TRMProvider().fetch_rates(RANGE, ["USD"])

    assert not isinstance(refused.value, FXRateLimitedError)


@pytest.mark.asyncio
async def test_trm_unreachable_is_a_service_error(monkeypatch: pytest.MonkeyPatch):
    """A transport failure is ``FXServiceError``."""

    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    _route(monkeypatch, trm_mod, refuse)

    with pytest.raises(FXServiceError):
        await TRMProvider().fetch_rates(RANGE, ["USD"])


@pytest.mark.parametrize(
    "body",
    [
        pytest.param("<!DOCTYPE html><html><body>Maintenance</body></html>", id="html"),
        pytest.param("not json at all", id="non-json"),
        pytest.param('{"error": true, "message": "query.soql.no-such-column"}', id="socrata-error-object"),
    ],
)
@pytest.mark.asyncio
async def test_trm_a_body_that_is_not_a_list_is_a_service_error(monkeypatch: pytest.MonkeyPatch, body: str):
    """An HTML page, non-JSON text, or Socrata's error object: ``FXServiceError``, never a rate limit."""
    _route(monkeypatch, trm_mod, lambda request: httpx.Response(200, content=body.encode()))

    with pytest.raises(FXServiceError) as refused:
        await TRMProvider().fetch_rates(RANGE, ["USD"])

    assert not isinstance(refused.value, FXRateLimitedError)


# ── Catalogue and identity ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_trm_catalogue_is_cop_and_usd_without_a_request(monkeypatch: pytest.MonkeyPatch):
    """``["COP", "USD"]`` and not one request made."""
    asked = _route(monkeypatch, trm_mod, lambda request: _answer(GOOD))

    currencies = await TRMProvider().get_supported_currencies()

    assert currencies == ["COP", "USD"]
    assert TRMProvider().fallback_currencies == currencies
    assert asked == []


def test_trm_identity_urls_and_constants():
    """Code, base, level, docs page and the three module constants."""
    provider = TRMProvider()
    assert (provider.code, provider.base_currency, provider.warning_level) == ("TRM", "COP", "info")
    assert provider.docs_url == "/mkdocs/user/fx/providers/trm/"
    assert trm_mod.DATASET_URL == DATASET_URL
    assert trm_mod.FIRST_DAY == date(1991, 12, 2)
    assert trm_mod.PAGE_SIZE == 50000

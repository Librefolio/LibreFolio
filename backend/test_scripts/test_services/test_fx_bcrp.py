"""BCRP FX provider: one BCRPData series (interbank USD, sell), Spanish month names, no-data days and what it refuses (no network, no DB, no server).

Lane 75, wave 2, lot L27 (plan ``plan-phase02FxCentralBanksOndata2.prompt.md``). Measured on the real feed on 19/11/2026:

- One request gives the whole history: 1990-01-01 -> today is ~470 KB in ~4.4 s; the values start at 02.Ene.97, ``n.d.``
  before that and on 356 later days (Peruvian holidays and the last 1-3 days not published yet).
- The JSON is served as ``text/html; charset=UTF-8``, so the content type says nothing about the body.
- The period name is ``dd.Mmm.yy`` with Spanish month abbreviations (``Set`` for September).
- An unknown series answers an Incapsula HTML page, not JSON.
- The BCRP's EUR series is left out: it is inconsistent with USD x EUR/USD (research note).

Every answer here is synthetic, written by hand in the feed's shape, never data downloaded from the bank.

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
from backend.app.services.fx_providers.bcrp import plugin as bcrp_mod
from backend.app.services.fx_providers.bcrp.plugin import BCRPProvider
from backend.test_scripts.test_services.test_rate_limit_http_providers import _route

API_URL = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api"
RANGE = (date(2026, 11, 10), date(2026, 11, 19))
TITLE = "Tipo de cambio - TC Interbancario (S/ por US$) - Venta"


def _period(name: str, value: str) -> dict:
    """One period as the feed writes it: a name and a list with the one value, as text."""
    return {"name": name, "values": [value]}


def _feed(*periods: dict) -> str:
    """The answer body, periods oldest first, as the BCRP sends it."""
    config = {"title": "Tipo de cambio", "series": [{"name": TITLE, "dec": "3"}]}
    return json.dumps({"config": config, "periods": list(periods)})


def _answer(body: str, status: int = 200) -> httpx.Response:
    """A JSON body with the content type the BCRP really uses: ``text/html``."""
    return httpx.Response(status, headers={"content-type": "text/html; charset=UTF-8"}, content=body.encode())


GOOD = _feed(
    _period("10.Nov.26", "3.41621428571429"),
    _period("11.Nov.26", "3.4200"),
    _period("12.Nov.26", "3.4180"),
)

INCAPSULA = "".join(
    [
        '<!DOCTYPE html><html><head><META NAME="robots" CONTENT="noindex,nofollow">',
        '<script src="/_Incapsula_Resource?SWJIYLWA=5074a744e2e3d891814e9a2dace20bd4"></script>',
        "</head><body></body></html>",
    ]
)


# ── Direction and values ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bcrp_one_usd_is_so_many_soles(monkeypatch: pytest.MonkeyPatch):
    """«3.416… S/ por US$» is 1 USD = 3.416… PEN: ``(d, USD, PEN, value)``, oldest first."""
    _route(monkeypatch, bcrp_mod, lambda request: _answer(GOOD))

    rates = await BCRPProvider().fetch_rates(RANGE, ["USD"])

    assert rates["USD"] == [
        (date(2026, 11, 10), "USD", "PEN", Decimal("3.41621428571429")),
        (date(2026, 11, 11), "USD", "PEN", Decimal("3.4200")),
        (date(2026, 11, 12), "USD", "PEN", Decimal("3.4180")),
    ]


@pytest.mark.asyncio
async def test_bcrp_values_keep_every_digit_of_the_text(monkeypatch: pytest.MonkeyPatch):
    """The value is a ``Decimal`` made from the string, with all its 14 decimals."""
    _route(monkeypatch, bcrp_mod, lambda request: _answer(GOOD))

    value = (await BCRPProvider().fetch_rates(RANGE, ["USD"]))["USD"][0][3]

    assert isinstance(value, Decimal)
    assert str(value) == "3.41621428571429"


@pytest.mark.asyncio
async def test_bcrp_spanish_months_and_two_digit_years_are_read(monkeypatch: pytest.MonkeyPatch):
    """All twelve month tokens (``Set`` and ``Sep`` for September), 97 is 1997 and 26 is 2026."""
    names = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Set", "Oct", "Nov", "Dic"]
    periods = [_period(f"05.{token}.26", f"3.{month:02d}") for month, token in enumerate(names, start=1)]
    periods.append(_period("06.Sep.26", "3.99"))
    periods.append(_period("02.Ene.97", "2.50"))
    periods.append(_period("31.Dic.99", "3.50"))
    _route(monkeypatch, bcrp_mod, lambda request: _answer(_feed(*periods)))

    rates = await BCRPProvider().fetch_rates(("min", date(2026, 12, 31)), ["USD"])

    days = {d: v for d, _, _, v in rates["USD"]}
    assert days[date(1997, 1, 2)] == Decimal("2.50")
    assert days[date(1999, 12, 31)] == Decimal("3.50")
    assert [d.month for d in days if d.year == 2026 and d.day == 5] == list(range(1, 13))
    assert days[date(2026, 9, 5)] == Decimal("3.09")
    assert days[date(2026, 9, 6)] == Decimal("3.99")


# ── Requests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bcrp_asks_one_get_with_a_path_only_url(monkeypatch: pytest.MonkeyPatch):
    """``API_URL/PD04638PD/json/<start>/<end>``: no language segment, no query string."""
    asked = _route(monkeypatch, bcrp_mod, lambda request: _answer(GOOD))

    await BCRPProvider().fetch_rates(RANGE, ["USD"])

    assert [str(r.url) for r in asked] == [f"{API_URL}/PD04638PD/json/2026-11-10/2026-11-19"]
    assert asked[0].method == "GET" and asked[0].url.query == b""


@pytest.mark.asyncio
async def test_bcrp_asks_from_1997_for_min_and_for_an_earlier_start(monkeypatch: pytest.MonkeyPatch):
    """``"min"`` and any earlier start begin at 1997-01-02, the first day of the series."""
    asked = _route(monkeypatch, bcrp_mod, lambda request: _answer(_feed()))

    await BCRPProvider().fetch_rates(("min", date(2026, 11, 19)), ["USD"])
    await BCRPProvider().fetch_rates((date(1980, 1, 1), date(2026, 11, 19)), ["USD"])

    assert [str(r.url) for r in asked] == [f"{API_URL}/PD04638PD/json/1997-01-02/2026-11-19"] * 2


@pytest.mark.asyncio
async def test_bcrp_every_asked_currency_but_pen_is_a_key_and_only_usd_is_served(monkeypatch: pytest.MonkeyPatch):
    """EUR is a key with ``[]``, PEN is no key, USD costs the one request."""
    asked = _route(monkeypatch, bcrp_mod, lambda request: _answer(GOOD))

    rates = await BCRPProvider().fetch_rates(RANGE, ["EUR", "PEN", "USD"])

    assert set(rates) == {"EUR", "USD"}
    assert rates["EUR"] == [] and len(rates["USD"]) == 3
    assert len(asked) == 1


@pytest.mark.asyncio
async def test_bcrp_without_usd_asks_nothing(monkeypatch: pytest.MonkeyPatch):
    """EUR alone, or PEN alone: no request."""
    asked = _route(monkeypatch, bcrp_mod, lambda request: _answer(GOOD))

    assert await BCRPProvider().fetch_rates(RANGE, ["EUR"]) == {"EUR": []}
    assert await BCRPProvider().fetch_rates(RANGE, ["PEN"]) == {}
    assert asked == []


@pytest.mark.asyncio
async def test_bcrp_inverted_range_asks_nothing(monkeypatch: pytest.MonkeyPatch):
    """Start after end: ``{"USD": []}`` and no request."""
    asked = _route(monkeypatch, bcrp_mod, lambda request: _answer(GOOD))

    assert await BCRPProvider().fetch_rates((date(2026, 11, 19), date(2026, 11, 10)), ["USD"]) == {"USD": []}
    assert asked == []


@pytest.mark.asyncio
async def test_bcrp_other_base_currency_is_refused(monkeypatch: pytest.MonkeyPatch):
    """``base_currency`` EUR raises ``ValueError``; None and PEN are fine."""
    asked = _route(monkeypatch, bcrp_mod, lambda request: _answer(GOOD))

    with pytest.raises(ValueError):
        await BCRPProvider().fetch_rates(RANGE, ["USD"], base_currency="EUR")

    assert len((await BCRPProvider().fetch_rates(RANGE, ["USD"], base_currency="PEN"))["USD"]) == 3
    assert len((await BCRPProvider().fetch_rates(RANGE, ["USD"], base_currency=None))["USD"]) == 3
    assert len(asked) == 2


# ── What it skips ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bcrp_no_data_days_are_skipped_never_a_zero(monkeypatch: pytest.MonkeyPatch):
    """``n.d.`` (a holiday, or a day not published yet) loses its own day and nothing else."""
    body = _feed(
        _period("10.Nov.26", "3.4162"),
        _period("11.Nov.26", "n.d."),
        _period("17.Nov.26", "n.d."),
        _period("18.Nov.26", "3.4300"),
    )
    _route(monkeypatch, bcrp_mod, lambda request: _answer(body))

    rates = await BCRPProvider().fetch_rates(RANGE, ["USD"])

    assert [(d, v) for d, _, _, v in rates["USD"]] == [
        (date(2026, 11, 10), Decimal("3.4162")),
        (date(2026, 11, 18), Decimal("3.4300")),
    ]


@pytest.mark.asyncio
async def test_bcrp_unreadable_rows_are_skipped_and_the_others_stay(monkeypatch: pytest.MonkeyPatch):
    """A text, a zero, a negative, a bad name, an unknown month and a day out of range lose only their own row."""
    body = _feed(
        _period("10.Nov.26", "3.4162"),
        _period("11.Nov.26", "abc"),
        _period("12.Nov.26", "0"),
        _period("13.Nov.26", "-3.5"),
        _period("not-a-date", "3.4"),
        _period("14.Xyz.26", "3.4"),
        _period("09.Nov.26", "3.3"),
        _period("20.Nov.26", "3.5"),
    )
    _route(monkeypatch, bcrp_mod, lambda request: _answer(body))

    rates = await BCRPProvider().fetch_rates(RANGE, ["USD"])

    assert rates["USD"] == [(date(2026, 11, 10), "USD", "PEN", Decimal("3.4162"))]


@pytest.mark.asyncio
async def test_bcrp_no_periods_is_a_range_without_data_not_an_error(monkeypatch: pytest.MonkeyPatch):
    """A Sunday (``"periods": []``) gives an empty list and no exception."""
    _route(monkeypatch, bcrp_mod, lambda request: _answer(_feed()))

    assert await BCRPProvider().fetch_rates(RANGE, ["USD"]) == {"USD": []}


# ── Errors ───────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bcrp_too_many_requests_is_a_rate_limit(monkeypatch: pytest.MonkeyPatch):
    """HTTP 429 raises ``FXRateLimitedError``."""
    _route(monkeypatch, bcrp_mod, lambda request: httpx.Response(429))

    with pytest.raises(FXRateLimitedError):
        await BCRPProvider().fetch_rates(RANGE, ["USD"])


@pytest.mark.asyncio
async def test_bcrp_http_500_is_a_service_error_and_not_a_rate_limit(monkeypatch: pytest.MonkeyPatch):
    """Any other HTTP error is ``FXServiceError``, not the rate-limit subclass."""
    _route(monkeypatch, bcrp_mod, lambda request: httpx.Response(500, text="Internal error"))

    with pytest.raises(FXServiceError) as refused:
        await BCRPProvider().fetch_rates(RANGE, ["USD"])

    assert not isinstance(refused.value, FXRateLimitedError)


@pytest.mark.asyncio
async def test_bcrp_unreachable_is_a_service_error(monkeypatch: pytest.MonkeyPatch):
    """A transport failure is ``FXServiceError``."""

    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    _route(monkeypatch, bcrp_mod, refuse)

    with pytest.raises(FXServiceError):
        await BCRPProvider().fetch_rates(RANGE, ["USD"])


@pytest.mark.asyncio
async def test_bcrp_html_page_is_a_service_error_and_not_a_rate_limit(monkeypatch: pytest.MonkeyPatch):
    """The Incapsula challenge page (what an unknown series gets) starts with ``<``: ``FXServiceError``."""
    _route(monkeypatch, bcrp_mod, lambda request: _answer(INCAPSULA))

    with pytest.raises(FXServiceError) as refused:
        await BCRPProvider().fetch_rates(RANGE, ["USD"])

    assert not isinstance(refused.value, FXRateLimitedError)


@pytest.mark.parametrize(
    "body",
    [
        pytest.param("not json at all", id="non-json"),
        pytest.param('{"config": {"title": "Tipo de cambio"}}', id="no-periods"),
        pytest.param('{"periods": "none"}', id="periods-not-a-list"),
    ],
)
@pytest.mark.asyncio
async def test_bcrp_a_body_that_is_not_the_feed_is_a_service_error(monkeypatch: pytest.MonkeyPatch, body: str):
    """Non-JSON text, or JSON without a ``periods`` list: ``FXServiceError``."""
    _route(monkeypatch, bcrp_mod, lambda request: _answer(body))

    with pytest.raises(FXServiceError):
        await BCRPProvider().fetch_rates(RANGE, ["USD"])


# ── Catalogue and identity ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bcrp_catalogue_is_pen_and_usd_without_a_request(monkeypatch: pytest.MonkeyPatch):
    """``["PEN", "USD"]`` and not one request made."""
    asked = _route(monkeypatch, bcrp_mod, lambda request: _answer(GOOD))

    currencies = await BCRPProvider().get_supported_currencies()

    assert currencies == ["PEN", "USD"]
    assert BCRPProvider().fallback_currencies == currencies
    assert asked == []


def test_bcrp_identity_urls_and_series():
    """Code, base, level, docs page and the three module constants."""
    provider = BCRPProvider()
    assert (provider.code, provider.base_currency, provider.warning_level) == ("BCRP", "PEN", "info")
    assert provider.docs_url == "/mkdocs/user/fx/providers/bcrp/"
    assert bcrp_mod.API_URL == API_URL
    assert bcrp_mod.USD_SERIES == "PD04638PD"
    assert bcrp_mod.FIRST_DAY == date(1997, 1, 2)

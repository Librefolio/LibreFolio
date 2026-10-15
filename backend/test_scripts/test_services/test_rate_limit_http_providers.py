"""X-RL X3: the HTTP providers on a 429 — the CSS scraper and the four FX providers (ECB, FED, BOE, SNB).

Plan 06 of Z, section «Z7 — disegno», contract X3; implementation notes in plan 03, section «X-RL (X1–X8)», step 3.
The contract pinned here:

1. CSS scraper: a 429 is ``AssetRateLimitedError`` with the response's ``Retry-After`` and the page's host as its
   scope (lowercase, without the port), after one request; any other status keeps ``HTTP_ERROR``.
2. The four FX providers: a 429 is ``FXRateLimitedError`` with the response's ``Retry-After``, from the
   ``httpx.HTTPStatusError``, on every request they make — the rates, ECB's catalogue, SNB's currency map (a refused
   map is not kept); another status keeps the provider's old handling.
3. A provider refusing one currency refuses the whole call: FED and BOE ask their currencies together and raise the
   refusal with the longest ``Retry-After`` (one without counts as the shortest), dropping what the other currencies
   answered; ECB asks them one at a time and stops at the first refused currency, while a currency failing otherwise is
   skipped as before. SNB asks once for every currency.
4. The real ECB plugin through ``call_fx_provider``: its 429 pauses ECB for max(base, ``Retry-After``), and the next
   call makes no request.

Pure: no database, no server, no network. Each plugin module's ``httpx`` is replaced, for the test only, by the real
module whose ``AsyncClient`` answers through an ``httpx.MockTransport``: the plugin's own requests, parameters and
``raise_for_status()`` run unchanged, and the handler counts what was asked. The pauses of case 4 are a private
``Cooldowns`` on a fake clock, and SNB's class-level currency map is put back after each test.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from datetime import date
from decimal import Decimal

import httpx
import pytest

from backend.app.db import IdentifierType
from backend.app.services.asset_source_providers.css_scraper import plugin as css_module
from backend.app.services.asset_source_providers.css_scraper.plugin import CSSScraperProvider
from backend.app.services.assets.base import AssetRateLimitedError, AssetSourceError
from backend.app.services.fx import runtime as fx_runtime
from backend.app.services.fx.base import FXRateLimitedError, FXServiceError
from backend.app.services.fx_providers.boe import plugin as boe_module
from backend.app.services.fx_providers.boe.plugin import BOEProvider
from backend.app.services.fx_providers.ecb import plugin as ecb_module
from backend.app.services.fx_providers.ecb.plugin import ECBProvider
from backend.app.services.fx_providers.fed import plugin as fed_module
from backend.app.services.fx_providers.fed.plugin import FEDProvider
from backend.app.services.fx_providers.snb import plugin as snb_module
from backend.app.services.fx_providers.snb.plugin import SNBProvider
from backend.app.services.platform import provider_cooldown
from backend.app.utils.runtime.cooldown import Cooldowns
from backend.test_scripts.test_utils import print_section, print_success

_REAL_ASYNC_CLIENT = httpx.AsyncClient
RANGE = (date(2026, 1, 2), date(2026, 1, 9))
CSS_PARAMS = {"current_css_selector": ".price", "currency": "EUR"}
#: What each FX provider's series code stands for, to read the currency a request is about.
FED_SERIES = {series: currency for currency, series in FEDProvider.CURRENCY_SERIES.items()}
BOE_SERIES = {series: currency for currency, series in BOEProvider.CURRENCY_SERIES.items()}


class FakeClock:
    """A clock that moves only when the test moves it."""

    def __init__(self, start: float = 1_000_000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now


class _HttpxWithTransport:
    """The ``httpx`` a plugin module sees: the real module, except that every ``AsyncClient`` answers through ``handler``."""

    def __init__(self, handler: Callable[[httpx.Request], httpx.Response]) -> None:
        self._transport = httpx.MockTransport(handler)

    def AsyncClient(self, *args, **kwargs):  # noqa: N802 — the name the plugin calls
        return _REAL_ASYNC_CLIENT(*args, transport=self._transport, **kwargs)

    def __getattr__(self, name: str):
        return getattr(httpx, name)


def _route(monkeypatch: pytest.MonkeyPatch, module, answers: Callable[[httpx.Request], httpx.Response]) -> list[httpx.Request]:
    """``module``'s requests go to ``answers``; the list returned holds every request, in the order made."""
    asked: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        asked.append(request)
        return answers(request)

    monkeypatch.setattr(module, "httpx", _HttpxWithTransport(handler))
    return asked


def _refused(retry_after: str | None = None) -> httpx.Response:
    return httpx.Response(429, headers={"Retry-After": retry_after} if retry_after is not None else {})


def _ecb_currency(request: httpx.Request) -> str:
    """The currency of an ECB request (``…/EXR/D.USD.EUR.SP00.A``); empty for the catalogue (``D..EUR``)."""
    return request.url.path.rsplit("/", 1)[-1].split(".")[1]


def _fed_currency(request: httpx.Request) -> str:
    return FED_SERIES[request.url.params["id"]]


def _boe_currency(request: httpx.Request) -> str:
    return BOE_SERIES[request.url.params["SeriesCodes"]]


@pytest.fixture(autouse=True)
def _snb_map_put_back(monkeypatch: pytest.MonkeyPatch) -> None:
    """SNB keeps its currency map on the class: each test starts without one, and the process's comes back after."""
    monkeypatch.setattr(SNBProvider, "_iso_to_d1", None)
    monkeypatch.setattr(SNBProvider, "_d1_to_iso", None)


# =============================================================================
# 1. CSS scraper
# =============================================================================


@pytest.mark.parametrize(
    ("url", "headers", "retry_after"),
    [
        pytest.param("https://prices.example/quote/IT0005634800", {"Retry-After": "120"}, 120.0, id="retry-after"),
        pytest.param("https://Prices.EXAMPLE:8443/quote?isin=IT0005634800", {}, None, id="no-retry-after-port-and-case"),
    ],
)
@pytest.mark.asyncio
async def test_a_css_429_is_a_refusal_scoped_to_the_host(monkeypatch: pytest.MonkeyPatch, url: str, headers: dict, retry_after: float | None):
    """XRL-H01 — contract 1: ``AssetRateLimitedError`` from the ``HTTPStatusError``, its ``Retry-After`` and the host, after one request."""
    asked = _route(monkeypatch, css_module, lambda _request: httpx.Response(429, headers=headers))

    with pytest.raises(AssetRateLimitedError) as refused:
        await CSSScraperProvider().get_current_value(url, IdentifierType.OTHER, CSS_PARAMS)

    assert (refused.value.error_code, refused.value.retry_after, refused.value.scope) == ("RATE_LIMITED", retry_after, "prices.example")
    assert isinstance(refused.value.__cause__, httpx.HTTPStatusError)
    assert len(asked) == 1


@pytest.mark.asyncio
async def test_another_css_status_keeps_http_error(monkeypatch: pytest.MonkeyPatch):
    """XRL-H02 — contract 1: a 503 with a ``Retry-After`` is still ``HTTP_ERROR``, with its status in the details."""
    _route(monkeypatch, css_module, lambda _request: httpx.Response(503, headers={"Retry-After": "120"}))

    with pytest.raises(AssetSourceError) as failed:
        await CSSScraperProvider().get_current_value("https://prices.example/quote/1", IdentifierType.OTHER, CSS_PARAMS)

    assert not isinstance(failed.value, AssetRateLimitedError)
    assert (failed.value.error_code, failed.value.details["status_code"]) == ("HTTP_ERROR", 503)


@pytest.mark.asyncio
async def test_a_css_page_that_answers_is_scraped(monkeypatch: pytest.MonkeyPatch):
    """XRL-H03 — barrier for 1: the same transport serving a page gives the price, so the refusals above come from the 429 alone."""
    _route(monkeypatch, css_module, lambda _request: httpx.Response(200, text='<html><span class="price">1,234.50</span></html>'))

    value = await CSSScraperProvider().get_current_value("https://prices.example/quote/1", IdentifierType.OTHER, CSS_PARAMS)

    assert (value.value, value.currency) == (Decimal("1234.50"), "EUR")


# =============================================================================
# 2–3. ECB: one currency at a time, stopping at the first refusal
# =============================================================================


@pytest.mark.asyncio
async def test_ecb_stops_at_the_first_refused_currency(monkeypatch: pytest.MonkeyPatch):
    """XRL-H04 — contracts 2–3: USD answers, GBP is refused: ``FXRateLimitedError`` with GBP's ``Retry-After``, and JPY is never asked."""
    print_section("XRL-H04: ECB stops at the first refusal")
    asked = _route(monkeypatch, ecb_module, lambda request: _refused("90") if _ecb_currency(request) == "GBP" else httpx.Response(200, text=""))

    with pytest.raises(FXRateLimitedError) as refused:
        await ECBProvider().fetch_rates(RANGE, ["USD", "GBP", "JPY"])

    assert [_ecb_currency(request) for request in asked] == ["USD", "GBP"]
    assert refused.value.retry_after == 90.0
    assert isinstance(refused.value.__cause__, httpx.HTTPStatusError)
    print_success("two requests, the third currency never asked")


@pytest.mark.asyncio
async def test_ecb_skips_a_currency_failing_otherwise(monkeypatch: pytest.MonkeyPatch):
    """XRL-H05 — contract 3, the other side: a 500 on GBP is skipped as before, and JPY is still asked."""
    asked = _route(monkeypatch, ecb_module, lambda request: httpx.Response(500) if _ecb_currency(request) == "GBP" else httpx.Response(200, text=""))

    rates = await ECBProvider().fetch_rates(RANGE, ["USD", "GBP", "JPY"])

    assert [_ecb_currency(request) for request in asked] == ["USD", "GBP", "JPY"]
    assert rates == {"USD": [], "GBP": [], "JPY": []}


@pytest.mark.asyncio
async def test_ecb_catalogue_refused(monkeypatch: pytest.MonkeyPatch):
    """XRL-H06 — contract 2: the catalogue request refused is ``FXRateLimitedError`` too, not «ECB API error»."""
    asked = _route(monkeypatch, ecb_module, lambda _request: _refused("30"))

    with pytest.raises(FXRateLimitedError) as refused:
        await ECBProvider().get_supported_currencies()

    assert refused.value.retry_after == 30.0
    assert [_ecb_currency(request) for request in asked] == [""]


# =============================================================================
# 3. FED and BOE: currencies together, one refusal refuses the whole call
# =============================================================================


def _fed_answers(refusals: dict[str, str | None]) -> Callable[[httpx.Request], httpx.Response]:
    """FED: the currencies in ``refusals`` refused with that ``Retry-After``; the others answer one rate on 2 January."""

    def answer(request: httpx.Request) -> httpx.Response:
        currency = _fed_currency(request)
        if currency in refusals:
            return _refused(refusals[currency])
        return httpx.Response(200, text=f"observation_date,{request.url.params['id']}\n2026-01-02,1.1000\n")

    return answer


def _boe_answers(refusals: dict[str, str | None]) -> Callable[[httpx.Request], httpx.Response]:
    """BOE: as ``_fed_answers``, in BOE's CSV."""

    def answer(request: httpx.Request) -> httpx.Response:
        currency = _boe_currency(request)
        if currency in refusals:
            return _refused(refusals[currency])
        return httpx.Response(200, text=f"DATE,{request.url.params['SeriesCodes']}\n02 Jan 2026,1.2700\n")

    return answer


@pytest.mark.parametrize(
    ("module", "provider", "answers", "currency_of"),
    [
        pytest.param(fed_module, FEDProvider, _fed_answers, _fed_currency, id="FED"),
        pytest.param(boe_module, BOEProvider, _boe_answers, _boe_currency, id="BOE"),
    ],
)
@pytest.mark.asyncio
async def test_one_refused_currency_refuses_the_whole_parallel_call(monkeypatch: pytest.MonkeyPatch, module, provider, answers, currency_of):
    """XRL-H07 — contract 3: three currencies asked together, two refused (30 s and 300 s): the 300 s refusal is raised, the third's rates dropped."""
    print_section(f"XRL-H07: {provider.__name__}, one refused currency refuses the call")
    asked = _route(monkeypatch, module, answers({"EUR": "30", "JPY": "300"}))
    currencies = ["EUR", "JPY", "CHF"]

    with pytest.raises(FXRateLimitedError) as refused:
        await provider().fetch_rates(RANGE, currencies)

    assert sorted(currency_of(request) for request in asked) == sorted(currencies)
    assert refused.value.retry_after == 300.0
    print_success("three requests, the longest Retry-After raised")


@pytest.mark.parametrize(
    ("module", "provider", "answers"),
    [pytest.param(fed_module, FEDProvider, _fed_answers, id="FED"), pytest.param(boe_module, BOEProvider, _boe_answers, id="BOE")],
)
@pytest.mark.asyncio
async def test_a_refusal_without_retry_after_counts_as_the_shortest(monkeypatch: pytest.MonkeyPatch, module, provider, answers):
    """XRL-H08 — contract 3: one refusal without ``Retry-After``, one with 10 s: the 10 s one is raised."""
    _route(monkeypatch, module, answers({"EUR": None, "JPY": "10"}))

    with pytest.raises(FXRateLimitedError) as refused:
        await provider().fetch_rates(RANGE, ["EUR", "JPY"])

    assert refused.value.retry_after == 10.0


@pytest.mark.parametrize(
    ("module", "provider", "answers", "currency_of", "base", "rate"),
    [
        pytest.param(fed_module, FEDProvider, _fed_answers, _fed_currency, "USD", Decimal("1.1000"), id="FED"),
        pytest.param(boe_module, BOEProvider, _boe_answers, _boe_currency, "GBP", Decimal("1.2700"), id="BOE"),
    ],
)
@pytest.mark.asyncio
async def test_a_currency_failing_otherwise_is_skipped_and_the_others_kept(monkeypatch: pytest.MonkeyPatch, module, provider, answers, currency_of, base: str, rate: Decimal):
    """XRL-H09 — contract 3, the other side: a 500 on one currency is skipped as before; the other's rate arrives."""
    answering = answers({})
    _route(monkeypatch, module, lambda request: httpx.Response(500) if currency_of(request) == "EUR" else answering(request))

    rates = await provider().fetch_rates(RANGE, ["EUR", "JPY"])

    assert rates["EUR"] == []
    assert [(day, observed) for day, *_pair, observed in rates["JPY"]] == [(date(2026, 1, 2), rate)]
    assert base in rates["JPY"][0][1:3]


# =============================================================================
# 2. SNB
# =============================================================================


@pytest.mark.asyncio
async def test_snb_rates_refused(monkeypatch: pytest.MonkeyPatch):
    """XRL-H10 — contract 2: with the currency map known, the one data request refused is ``FXRateLimitedError`` with its ``Retry-After``."""
    monkeypatch.setattr(SNBProvider, "_iso_to_d1", {"EUR": "EUR1", "CNY": "CNY100"})
    monkeypatch.setattr(SNBProvider, "_d1_to_iso", {"EUR1": ("EUR", 1), "CNY100": ("CNY", 100)})
    asked = _route(monkeypatch, snb_module, lambda _request: _refused("45"))

    with pytest.raises(FXRateLimitedError) as refused:
        await SNBProvider().fetch_rates(RANGE, ["EUR", "CNY"])

    assert refused.value.retry_after == 45.0
    assert [request.url.path.endswith("/data/json/en") for request in asked] == [True]


@pytest.mark.asyncio
async def test_snb_another_status_keeps_its_service_error(monkeypatch: pytest.MonkeyPatch):
    """XRL-H11 — contract 2, the other side: a 502 on the data request is the old ``FXServiceError``."""
    monkeypatch.setattr(SNBProvider, "_iso_to_d1", {"EUR": "EUR1"})
    monkeypatch.setattr(SNBProvider, "_d1_to_iso", {"EUR1": ("EUR", 1)})
    _route(monkeypatch, snb_module, lambda _request: httpx.Response(502))

    with pytest.raises(FXServiceError) as failed:
        await SNBProvider().fetch_rates(RANGE, ["EUR"])

    assert not isinstance(failed.value, FXRateLimitedError)


@pytest.mark.asyncio
async def test_snb_currency_map_refused(monkeypatch: pytest.MonkeyPatch):
    """XRL-H12 — contract 2: the currency-map request refused, from the catalogue or before the rates: ``FXRateLimitedError``, and no data request follows."""
    asked = _route(monkeypatch, snb_module, lambda _request: _refused("600"))

    with pytest.raises(FXRateLimitedError) as catalogue:
        await SNBProvider().get_supported_currencies()
    with pytest.raises(FXRateLimitedError) as rates:
        await SNBProvider().fetch_rates(RANGE, ["EUR"])

    assert (catalogue.value.retry_after, rates.value.retry_after) == (600.0, 600.0)
    assert [request.url.path.endswith("/dimensions/en") for request in asked] == [True, True]
    assert SNBProvider._iso_to_d1 is None, "a refused map is not kept"


@pytest.mark.asyncio
async def test_snb_currency_map_failing_otherwise_keeps_its_service_error(monkeypatch: pytest.MonkeyPatch):
    """XRL-H13 — contract 2, the other side: a 503 on the currency map is the old ``FXServiceError``."""
    _route(monkeypatch, snb_module, lambda _request: httpx.Response(503))

    with pytest.raises(FXServiceError) as failed:
        await SNBProvider().get_supported_currencies()

    assert not isinstance(failed.value, FXRateLimitedError)


# =============================================================================
# 4. Through the FX boundary
# =============================================================================


@pytest.mark.asyncio
async def test_an_ecb_429_through_the_boundary_pauses_ecb(monkeypatch: pytest.MonkeyPatch):
    """XRL-H14 — contract 4: the real plugin, the real boundary: paused for max(60, 240), and the next call asks nothing."""
    for name in list(os.environ):
        if name.startswith("LIBREFOLIO_PROVIDER_COOLDOWN_"):
            monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS", "60")
    monkeypatch.setenv("LIBREFOLIO_PROVIDER_COOLDOWN_MAX_SECONDS", "3600")
    cooldowns = Cooldowns(60, 3600, jitter=0.0, clock=FakeClock())
    monkeypatch.setattr(provider_cooldown, "PROVIDER_COOLDOWNS", cooldowns)
    asked = _route(monkeypatch, ecb_module, lambda _request: _refused("240"))
    ecb = ECBProvider()

    with pytest.raises(FXRateLimitedError) as refused:
        await fx_runtime.call_fx_provider(ecb, lambda: ecb.fetch_rates(RANGE, ["USD"]))
    with pytest.raises(FXRateLimitedError) as paused:
        await fx_runtime.call_fx_provider(ecb, lambda: ecb.fetch_rates(RANGE, ["USD"]))

    assert (refused.value.retry_after, paused.value.retry_after) == (240.0, 240.0)
    assert len(asked) == 1
    assert [(state.key, state.refusals) for state in cooldowns.snapshot()] == [(("fx", "ECB", None), 1)]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

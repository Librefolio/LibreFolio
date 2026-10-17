"""X-RL X1/X2: the «too many requests» errors of the two provider domains and the helpers that recognise a refusal.

Plan 06 of Z, section «Z7 — disegno», contract X1–X2; implementation notes in plan 03, section «X-RL (X1–X8)». The
contract pinned here:

1. ``AssetRateLimitedError(message, *, retry_after, scope, details)`` is an ``AssetSourceError`` with
   ``error_code="RATE_LIMITED"`` and a ``RateLimitedError``: every ``except AssetSourceError`` keeps catching it.
2. ``rate_limited_from_response(response, provider_name, *, scope)``: an ``AssetRateLimitedError`` for an HTTP 429
   (``httpx`` or ``requests``), its ``Retry-After`` read in seconds — a number, or an HTTP date measured from now —
   None when absent or unreadable; None for any other status, for no response at all.
3. ``rate_limited_from_exception(error, provider_name, *, scope)``: the error itself when it already is an
   ``AssetRateLimitedError``; a refusal for an error carrying a 429 response; a refusal for a message — a library
   without an error class of its own, or an error flattened to text — saying «status 429», «status code 429», «HTTP 429»
   or «HTTP Error 429» (a colon allowed, any case), or the reason phrase «Too Many Requests» (the texts of urllib,
   requests and httpx); 429 as a whole number only — «4290» and «status code 4291» are no refusal.
4. ``raise_if_rate_limited``: raises that refusal from the error, re-raises an ``AssetRateLimitedError`` as it is
   (passthrough), returns for anything else.
5. ``AssetSourceProvider.cooldown_scope`` is None by default; the CSS scraper answers the host of its URL identifier,
   lowercase and without the port, None for a malformed URL or one without a host. Every registered provider answers
   the hook with None or a non-empty text.
6. ``FXRateLimitedError(message, *, retry_after, scope)`` is an ``FXServiceError`` and a ``RateLimitedError``, with the
   class attribute ``error_code="RATE_LIMITED"``.
7. ``fx_rate_limited_from_response`` and ``raise_if_fx_rate_limited``: as 2 and 4, for the ``httpx`` error of an FX
   plugin's ``except httpx.HTTPError``.
8. ``longest_refusal(outcomes)``: among the outcomes of calls made together, the ``FXRateLimitedError`` with the longest
   ``Retry-After`` (one without counts as the shortest), None when none was refused; ``raise_longest_refusal`` raises
   that very error, and returns when there is none.

Pure: no database, no server, no network. The HTTP responses and errors are built in memory — the library texts of
contract 3 are those urllib, requests and httpx write themselves; the one clock read, the «now» an HTTP-date
``Retry-After`` is measured from, is fixed by replacing ``time`` in the cooldown module, never the process's.
"""

from __future__ import annotations

import urllib.error
from datetime import UTC, datetime
from email.utils import format_datetime
from http import HTTPStatus
from types import SimpleNamespace
from urllib.parse import urlsplit

import httpx
import pytest
import requests
from requests.structures import CaseInsensitiveDict

from backend.app.db import IdentifierType
from backend.app.services.asset_source_providers.css_scraper.plugin import CSSScraperProvider, _url_host
from backend.app.services.asset_source_providers.mockprov.plugin import MockProvider
from backend.app.services.assets import core
from backend.app.services.assets.base import AssetRateLimitedError, AssetSourceError, raise_if_rate_limited, rate_limited_from_exception, rate_limited_from_response
from backend.app.services.assets.registry import AssetProviderRegistry
from backend.app.services.fx.base import FXRateLimitedError, FXServiceError, fx_rate_limited_from_response, longest_refusal, raise_if_fx_rate_limited, raise_longest_refusal
from backend.app.utils.runtime import cooldown as cooldown_module
from backend.app.utils.runtime.cooldown import RateLimitedError
from backend.test_scripts.test_utils import print_section, print_success

PROVIDER = "Lab Provider"
FX_CODE = "LABFX"
QUOTE_URL = "https://prices.example/quote"
#: The moment an HTTP-date ``Retry-After`` names, and «now», 150 s before it.
RESUME_AT = datetime(2026, 10, 15, 19, 30, tzinfo=UTC)
NOW = RESUME_AT.timestamp() - 150


@pytest.fixture
def fixed_now(monkeypatch: pytest.MonkeyPatch) -> float:
    """«Now» for the HTTP-date form of ``Retry-After``: the cooldown module's ``time`` only, never the process's."""
    monkeypatch.setattr(cooldown_module, "time", SimpleNamespace(time=lambda: NOW))
    return NOW


def _response(status: int, headers: dict[str, str] | None = None) -> httpx.Response:
    return httpx.Response(status, headers=headers or {}, request=httpx.Request("GET", QUOTE_URL))


def _status_error(status: int, headers: dict[str, str] | None = None) -> httpx.HTTPStatusError:
    """The error ``raise_for_status()`` raises for that response, as a plugin's ``except`` receives it."""
    try:
        _response(status, headers).raise_for_status()
    except httpx.HTTPStatusError as error:
        return error
    raise AssertionError(f"status {status} raised nothing")


def _requests_response(status: int, headers: dict[str, str]) -> requests.Response:
    response = requests.Response()
    response.status_code = status
    response.headers = CaseInsensitiveDict(headers)
    return response


# The texts the HTTP libraries write for a status, computed from the libraries themselves: what a plugin's message
# carries when an error is flattened to text. A library that changes its wording changes these too.


def _httpx_text(status: int) -> str:
    """httpx: «Client error '429 Too Many Requests' for url '…'», then an MDN link ending in «HTTP/Status/429»."""
    return str(_status_error(status))


def _requests_text(status: int) -> str:
    """requests: «429 Client Error: Too Many Requests for url: …», with the standard reason phrase a server sends."""
    response = _requests_response(status, {})
    response.reason, response.url = HTTPStatus(status).phrase, QUOTE_URL
    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        return str(error)
    raise AssertionError(f"status {status} raised nothing")


def _urllib_text(status: int, reason: str | None = None) -> str:
    """urllib: «HTTP Error 429: Too Many Requests», or the reason phrase of the server's own when it sends one."""
    error = urllib.error.HTTPError(QUOTE_URL, status, reason or HTTPStatus(status).phrase, None, None)
    try:
        return str(error)
    finally:
        error.close()


# =============================================================================
# 1. AssetRateLimitedError
# =============================================================================


def test_the_asset_refusal_is_an_asset_source_error_and_a_rate_limited_error():
    """XRL-E01 — contract 1: code RATE_LIMITED, wait and scope kept, details default to {}; ``except AssetSourceError`` catches it."""
    print_section("XRL-E01: AssetRateLimitedError")

    error = AssetRateLimitedError("refused", retry_after=12.5, scope="prices.example")

    assert isinstance(error, AssetSourceError) and isinstance(error, RateLimitedError)
    assert (error.error_code, error.message, error.retry_after, error.scope, error.details) == ("RATE_LIMITED", "refused", 12.5, "prices.example", {})
    assert str(error) == "refused"
    assert AssetRateLimitedError("refused", details={"url": "https://prices.example/q"}).details == {"url": "https://prices.example/q"}
    bare = AssetRateLimitedError("refused")
    assert (bare.retry_after, bare.scope) == (None, None)
    with pytest.raises(AssetSourceError) as caught:
        raise error
    assert caught.value is error
    print_success("RATE_LIMITED, an AssetSourceError and a RateLimitedError")


# =============================================================================
# 2. rate_limited_from_response
# =============================================================================


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        pytest.param({"Retry-After": "120"}, 120.0, id="seconds"),
        pytest.param({"retry-after": "1.5"}, 1.5, id="decimal-seconds-any-case"),
        pytest.param({}, None, id="no-header"),
        pytest.param({"Retry-After": "soon"}, None, id="unreadable"),
        pytest.param({"Retry-After": "-5"}, None, id="negative"),
    ],
)
def test_a_429_response_is_a_refusal_with_its_retry_after(header: dict[str, str], expected: float | None):
    """XRL-E02 — contract 2: an HTTP 429 is an ``AssetRateLimitedError`` carrying ``Retry-After`` in seconds, None when it says nothing usable."""
    refused = rate_limited_from_response(_response(429, header), PROVIDER, scope="prices.example")

    assert isinstance(refused, AssetRateLimitedError)
    assert (refused.error_code, refused.retry_after, refused.scope) == ("RATE_LIMITED", expected, "prices.example")
    assert PROVIDER in refused.message, "the message names the provider"


def test_an_http_date_retry_after_is_the_seconds_left_until_that_date(fixed_now: float):
    """XRL-E03 — contract 2: ``Retry-After`` as an HTTP date is measured from now; a date already past is 0."""
    ahead = rate_limited_from_response(_response(429, {"Retry-After": format_datetime(RESUME_AT, usegmt=True)}), PROVIDER)
    past = rate_limited_from_response(_response(429, {"Retry-After": "Wed, 21 Oct 2015 07:28:00 GMT"}), PROVIDER)

    assert ahead is not None and ahead.retry_after == 150.0
    assert past is not None and past.retry_after == 0.0


@pytest.mark.parametrize("status", [200, 403, 500, 503])
def test_any_other_status_is_no_refusal(status: int):
    """XRL-E04 — contract 2: only 429 is «too many requests», whatever headers come with the other statuses."""
    assert rate_limited_from_response(_response(status, {"Retry-After": "30"}), PROVIDER) is None


def test_no_response_or_a_response_without_headers():
    """XRL-E05 — contract 2: no response, or an object without a status, is no refusal; a 429 without headers has no wait."""
    assert rate_limited_from_response(None, PROVIDER) is None
    assert rate_limited_from_response(object(), PROVIDER) is None
    headless = rate_limited_from_response(SimpleNamespace(status_code=429), PROVIDER)
    assert isinstance(headless, AssetRateLimitedError) and headless.retry_after is None


def test_a_requests_response_is_read_like_an_httpx_one():
    """XRL-E06 — contract 2: a ``requests`` 429 (case-insensitive headers) gives the same refusal."""
    refused = rate_limited_from_response(_requests_response(429, {"retry-after": "7"}), PROVIDER)

    assert isinstance(refused, AssetRateLimitedError) and refused.retry_after == 7.0
    assert rate_limited_from_response(_requests_response(404, {"Retry-After": "7"}), PROVIDER) is None


# =============================================================================
# 3. rate_limited_from_exception
# =============================================================================


def test_an_asset_refusal_is_recognised_as_it_is():
    """XRL-E07 — contract 3: an ``AssetRateLimitedError`` comes back as the very same object, its wait and scope untouched."""
    error = AssetRateLimitedError("already a refusal", retry_after=42.0, scope="a.example")

    assert rate_limited_from_exception(error, PROVIDER, scope="b.example") is error
    assert (error.retry_after, error.scope) == (42.0, "a.example")


@pytest.mark.parametrize("make", [pytest.param(lambda: _status_error(429, {"Retry-After": "90"}), id="httpx"), pytest.param(lambda: requests.HTTPError("429 Client Error", response=_requests_response(429, {"Retry-After": "90"})), id="requests")])
def test_an_error_carrying_a_429_response_is_a_refusal(make):
    """XRL-E08 — contract 3: ``httpx.HTTPStatusError`` and ``requests.HTTPError`` with a 429: a refusal with the response's ``Retry-After`` and the scope given."""
    refused = rate_limited_from_exception(make(), PROVIDER, scope="prices.example")

    assert isinstance(refused, AssetRateLimitedError)
    assert (refused.retry_after, refused.scope) == (90.0, "prices.example")


@pytest.mark.parametrize(
    "message",
    [
        pytest.param("Got status 429 when requesting overview.\nError page saved to 'overview-error-page.html'.", id="justetf-helpers"),
        pytest.param("Failed to fetch ETF page for IE00B4L5Y983: status 429", id="justetf-profile"),
        pytest.param("HTTP 429 from upstream", id="http-429"),
        pytest.param("STATUS 429", id="any-case"),
        pytest.param("http429", id="no-space"),
        pytest.param("Unexpected status code 429 from the quote server", id="status-code-429"),
        pytest.param("Upstream answered HTTP: 429", id="http-colon-429"),
        pytest.param("Status Code: 429", id="status-code-colon-429"),
        pytest.param(_urllib_text(429, "Slow Down"), id="urllib-http-error-429-own-reason"),
        pytest.param("Too Many Requests", id="reason-phrase"),
        pytest.param(_urllib_text(429), id="urllib"),
        pytest.param(_requests_text(429), id="requests"),
        pytest.param(_httpx_text(429), id="httpx"),
    ],
)
def test_a_message_saying_status_429_is_a_refusal_without_a_wait(message: str):
    """XRL-E09 — contract 3: a message that only says it is refused, with no ``Retry-After``: «status 429», «status code 429», «HTTP 429», «HTTP Error 429» (a colon or not, any case), or the reason phrase «Too Many Requests».

    urllib's, requests' and httpx's own texts, flattened to a message; urllib's with a reason of the server's own («Slow Down») is caught by «HTTP Error 429» alone.
    """
    refused = rate_limited_from_exception(RuntimeError(message), PROVIDER, scope="prices.example")

    assert isinstance(refused, AssetRateLimitedError)
    assert (refused.retry_after, refused.scope) == (None, "prices.example")


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(RuntimeError("Got status 4290 when requesting overview"), id="status-4290"),
        pytest.param(RuntimeError("Unexpected status code 4291"), id="status-code-4291"),
        pytest.param(RuntimeError("No data for 4290.T"), id="ticker-4290"),
        pytest.param(RuntimeError("HTTP 1429 points"), id="http-1429"),
        pytest.param(RuntimeError("429 apples"), id="429-without-status"),
        pytest.param(RuntimeError("Got status 500 when requesting overview"), id="status-500"),
        pytest.param(RuntimeError(_urllib_text(503)), id="urllib-503"),
        pytest.param(RuntimeError(_requests_text(503)), id="requests-503"),
        pytest.param(RuntimeError(_httpx_text(503)), id="httpx-503"),
        pytest.param(ValueError("boom"), id="plain"),
    ],
)
def test_anything_else_is_no_refusal(error: BaseException):
    """XRL-E10 — contract 3: «4290», «status code 4291», «1429», a bare 429, another status — in the libraries' own texts too, httpx's link ending in «HTTP/Status/503» — or a plain error: no refusal."""
    assert rate_limited_from_exception(error, PROVIDER) is None


def test_an_error_carrying_another_status_is_no_refusal():
    """XRL-E11 — contract 3: a 503 response is no refusal even with a ``Retry-After``."""
    assert rate_limited_from_exception(_status_error(503, {"Retry-After": "30"}), PROVIDER) is None


# =============================================================================
# 4. raise_if_rate_limited
# =============================================================================


def test_raise_if_rate_limited_raises_the_refusal_from_the_error():
    """XRL-E12 — contract 4: a recognised refusal is raised with the original as its cause."""
    original = _status_error(429, {"Retry-After": "15"})

    with pytest.raises(AssetRateLimitedError) as raised:
        raise_if_rate_limited(original, PROVIDER, scope="prices.example")

    assert raised.value.__cause__ is original
    assert (raised.value.retry_after, raised.value.scope) == (15.0, "prices.example")


def test_raise_if_rate_limited_passes_an_asset_refusal_through_as_it_is():
    """XRL-E13 — contract 4: an ``AssetRateLimitedError`` is re-raised as itself, with no cause added."""
    error = AssetRateLimitedError("already a refusal", retry_after=3.0)

    with pytest.raises(AssetRateLimitedError) as raised:
        raise_if_rate_limited(error, PROVIDER)

    assert raised.value is error
    assert raised.value.__cause__ is None


def test_raise_if_rate_limited_returns_for_anything_else():
    """XRL-E14 — contract 4: the other errors go on to the plugin's own handling."""
    assert raise_if_rate_limited(RuntimeError("Got status 500 when requesting overview"), PROVIDER) is None
    assert raise_if_rate_limited(_status_error(404), PROVIDER) is None


# =============================================================================
# 5. The cooldown_scope hook
# =============================================================================


def test_the_hook_is_none_by_default_and_the_host_for_the_css_scraper():
    """XRL-E15 — contract 5: the base hook pauses the whole provider; the CSS scraper pauses the site of its URL."""
    print_section("XRL-E15: cooldown_scope")
    css = CSSScraperProvider()

    assert MockProvider().cooldown_scope("MOCK", IdentifierType.TICKER, {}) is None
    assert css.cooldown_scope("https://Prices.EXAMPLE:8443/quote?isin=IT0005634800") == "prices.example"
    assert css.cooldown_scope("http://other.example/p", IdentifierType.OTHER, {"currency": "EUR"}) == "other.example"
    assert css.cooldown_scope("http://[::1") is None, "a malformed URL has no host to pause"
    assert css.cooldown_scope("not a url") is None
    assert css.cooldown_scope("") is None
    assert (_url_host(None), _url_host(42), _url_host("  https://Spaced.example/x  ")) == (None, None, "spaced.example")
    print_success("None by default, the lowercase host without the port for css_scraper")


def test_every_registered_provider_answers_the_hook_with_none_or_a_text():
    """XRL-E16 — contract 5: called before every call, on every provider's own test cases: None or a non-empty text, never an error."""
    answers: dict[str, list[str | None]] = {}
    css_hosts: list[str | None] = []
    for listed in AssetProviderRegistry.list_providers():
        provider = AssetProviderRegistry.get_provider_instance(listed["code"])
        cases = getattr(provider, "test_cases", None) or [{"identifier": "X"}]
        answers[listed["code"]] = [core.cooldown_scope_for(provider, case["identifier"], case.get("identifier_type"), case.get("provider_params")) for case in cases]
        if listed["code"] == "css_scraper":
            css_hosts = [urlsplit(case["identifier"]).hostname for case in cases]

    assert {"css_scraper", "mockprov"} <= set(answers), f"barrier: the registry lists {sorted(answers)}"
    assert all(scope is None or (isinstance(scope, str) and scope) for scopes in answers.values() for scope in scopes), answers
    assert css_hosts and all(css_hosts), "barrier: the CSS scraper's own test cases are URLs with a host"
    assert answers["css_scraper"] == css_hosts
    assert all(scope is None for scope in answers["mockprov"])


# =============================================================================
# 6–7. FXRateLimitedError and its helpers
# =============================================================================


def test_the_fx_refusal_is_an_fx_service_error_and_a_rate_limited_error():
    """XRL-E17 — contract 6: an ``FXServiceError`` (the sync records a failed leg) with ``error_code`` RATE_LIMITED."""
    error = FXRateLimitedError("refused", retry_after=30.0)

    assert isinstance(error, FXServiceError) and isinstance(error, RateLimitedError)
    assert (FXRateLimitedError.error_code, error.error_code, str(error), error.retry_after, error.scope) == ("RATE_LIMITED", "RATE_LIMITED", "refused", 30.0, None)


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        pytest.param({"Retry-After": "300"}, 300.0, id="seconds"),
        pytest.param({}, None, id="no-header"),
        pytest.param({"Retry-After": "later"}, None, id="unreadable"),
    ],
)
def test_an_fx_429_response_is_a_refusal_with_its_retry_after(header: dict[str, str], expected: float | None):
    """XRL-E18 — contract 7: an HTTP 429 is an ``FXRateLimitedError`` naming the provider; ``Retry-After`` in seconds or None."""
    refused = fx_rate_limited_from_response(_response(429, header), FX_CODE)

    assert isinstance(refused, FXRateLimitedError)
    assert refused.retry_after == expected
    assert FX_CODE in str(refused)


def test_an_fx_http_date_retry_after_is_measured_from_now(fixed_now: float):
    """XRL-E19 — contract 7: the HTTP-date form, as for the assets."""
    refused = fx_rate_limited_from_response(_response(429, {"Retry-After": format_datetime(RESUME_AT, usegmt=True)}), FX_CODE)

    assert refused is not None and refused.retry_after == 150.0


def test_an_fx_response_of_another_status_or_none_is_no_refusal():
    """XRL-E20 — contract 7: 500, 503 or no response at all."""
    assert fx_rate_limited_from_response(_response(500, {"Retry-After": "30"}), FX_CODE) is None
    assert fx_rate_limited_from_response(_response(503), FX_CODE) is None
    assert fx_rate_limited_from_response(None, FX_CODE) is None


def test_raise_if_fx_rate_limited_raises_from_a_429_and_returns_otherwise():
    """XRL-E21 — contract 7: the 429 of an ``httpx`` error is raised from it; another status, or an error without a response, returns."""
    original = _status_error(429, {"Retry-After": "45"})

    with pytest.raises(FXRateLimitedError) as raised:
        raise_if_fx_rate_limited(original, FX_CODE)

    assert raised.value.__cause__ is original and raised.value.retry_after == 45.0
    assert raise_if_fx_rate_limited(_status_error(502), FX_CODE) is None
    assert raise_if_fx_rate_limited(httpx.ConnectError("refused", request=httpx.Request("GET", "https://fx.example/")), FX_CODE) is None


# =============================================================================
# 8. longest_refusal and raise_longest_refusal
# =============================================================================


def test_longest_refusal_picks_the_longest_retry_after_among_mixed_outcomes():
    """XRL-E22 — contract 8: answers, other errors, an asset refusal and FX refusals: the FX one with the longest wait wins."""
    print_section("XRL-E22: longest_refusal")
    longest = FXRateLimitedError("GBP refused", retry_after=50.0)
    outcomes = [("USD", []), ValueError("JPY failed"), FXRateLimitedError("EUR refused", retry_after=5.0), longest, FXRateLimitedError("CHF refused"), AssetRateLimitedError("not of the FX domain", retry_after=500.0)]

    assert longest_refusal(outcomes) is longest
    with pytest.raises(FXRateLimitedError) as raised:
        raise_longest_refusal(outcomes)
    assert raised.value is longest
    print_success("the 50 s refusal of the four, the asset one ignored")


def test_a_refusal_without_retry_after_counts_as_the_shortest():
    """XRL-E23 — contract 8: a refusal with a wait beats one without; with none known, one of them is still returned."""
    timed = FXRateLimitedError("timed", retry_after=10.0)
    untimed = [FXRateLimitedError("first"), FXRateLimitedError("second")]

    assert longest_refusal([untimed[0], timed, untimed[1]]) is timed
    chosen = longest_refusal(untimed)
    assert chosen in untimed and chosen.retry_after is None


def test_no_refusal_among_the_outcomes():
    """XRL-E24 — contract 8: None, and ``raise_longest_refusal`` returns without raising."""
    outcomes = [("USD", []), ValueError("boom"), FXServiceError("down")]

    assert longest_refusal(outcomes) is None
    assert longest_refusal([]) is None
    assert raise_longest_refusal(outcomes) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

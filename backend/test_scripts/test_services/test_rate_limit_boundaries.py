"""X-RL X4: the pauses after «too many requests» at the two provider-call boundaries, ``core.call_provider`` and ``fx/runtime.call_fx_provider``.

Plan 06 of Z, section «Z7 — disegno», contract X4; implementation notes in plan 03, section «X-RL (X1–X8)», step 2.
The contract pinned here, for the asset boundary (mockprov) and the FX one (MockFX) alike:

1. A refusal the plugin raises pauses the provider for max(base, ``Retry-After``) — above the cap too, up to the hard
   maximum — and leaves the boundary with ``retry_after`` set to that pause; the plugin was called once.
2. While the pause runs no call reaches the plugin, whatever the operation: the caller gets the domain's
   ``RATE_LIMITED`` error at once, ``retry_after`` the seconds left.
3. When the pause ends one trial call goes through; a concurrent caller is refused for the trial's window without
   reaching the plugin; the trial's answer ends the pause.
4. Any other end of the trial — another error, a cancellation — frees it: the next caller goes through, the pause
   record stays until an answer.
5. Pauses off (``LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS=0``): every call reaches the plugin, nothing is recorded,
   and the refusal keeps the plugin's own ``Retry-After``.
6. The scope: the CSS scraper's sites pause apart (two hosts on an ``httpx.MockTransport``); the plugin's own scope
   applies when the caller names none; a ``cooldown_scope`` hook that fails, or answers no text, means the whole
   provider (``cooldown_scope_for`` → None), and a failure is logged with the provider and the error type.
7. A test double that is not a plugin is called as it is: never paused, never pausing, its refusal untouched.
8. A ``RateLimitedError`` that is not the domain's own leaves as a fresh domain ``RATE_LIMITED`` error with the pause
   decided and the scope, and no link to the original.
9. Secrets: a refusal whose text shows a secret is masked in place (same object, same wait); one whose text masking
   cannot rewrite is replaced by a fresh ``RATE_LIMITED`` error carrying the pause and the scope, without the secret.

Pure: no database, no server, no network (the CSS scraper's sites are an ``httpx.MockTransport``). The pauses are a
private ``Cooldowns`` on a fake clock, without jitter, put in place of ``provider_cooldown.PROVIDER_COOLDOWNS`` for each
test, so nothing is paused in the process beyond the test; the two variables are set by each test with
``monkeypatch``; MockFX's «too many requests» mode is a class attribute set with ``monkeypatch``. The concurrent cases
hold the trial call on an event the test releases, never on the clock.
"""

from __future__ import annotations

import asyncio
import os
import threading
import uuid
from collections import Counter
from collections.abc import Callable
from datetime import date
from decimal import Decimal

import httpx
import pytest
from structlog.testing import capture_logs

from backend.app.db import IdentifierType
from backend.app.services.asset_source_providers.css_scraper import plugin as css_module
from backend.app.services.asset_source_providers.css_scraper.plugin import CSSScraperProvider
from backend.app.services.asset_source_providers.mockprov.plugin import MockProvider
from backend.app.services.assets import core
from backend.app.services.assets.base import AssetRateLimitedError, AssetSourceError
from backend.app.services.fx import runtime as fx_runtime
from backend.app.services.fx.base import FXRateLimitedError, FXServiceError
from backend.app.services.fx_providers.mockfx.plugin import MockFXProvider
from backend.app.services.platform import provider_cooldown
from backend.app.services.platform.provider_cooldown import record_refusal
from backend.app.services.plugin_settings.contract import BoundSettings
from backend.app.utils.runtime.cooldown import Cooldowns, RateLimitedError
from backend.app.utils.runtime.secret_masking import MASK
from backend.test_scripts.test_utils import print_section, print_success

BASE_VARIABLE = "LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS"
MAX_VARIABLE = "LIBREFOLIO_PROVIDER_COOLDOWN_MAX_SECONDS"
START = 1_000_000.0
#: How long a trial call holds the way after a pause, in this test's ``Cooldowns``.
TRIAL_SECONDS = 45.0
MOCK_KEY = ("asset", "mockprov", None)
MOCKFX_KEY = ("fx", "MOCKFX", None)
RANGE = (date(2026, 1, 5), date(2026, 1, 6))
CSS_PARAMS = {"current_css_selector": ".price", "currency": "EUR"}

_REAL_ASYNC_CLIENT = httpx.AsyncClient


class FakeClock:
    """A clock that moves only when the test moves it: ``clock.now += …``."""

    def __init__(self, start: float = START) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now


class _Calls:
    """The ``fn`` a boundary receives: counts the calls the boundary let through, then builds the plugin's coroutine."""

    def __init__(self, make: Callable[[], object]) -> None:
        self.count = 0
        self._make = make

    def __call__(self):
        self.count += 1
        return self._make()


class _HttpxWithTransport:
    """The ``httpx`` a plugin module sees: the real module, except that every ``AsyncClient`` answers through ``handler``."""

    def __init__(self, handler: Callable[[httpx.Request], httpx.Response]) -> None:
        self._transport = httpx.MockTransport(handler)

    def AsyncClient(self, *args, **kwargs):  # noqa: N802 — the name the plugin calls
        return _REAL_ASYNC_CLIENT(*args, transport=self._transport, **kwargs)

    def __getattr__(self, name: str):
        return getattr(httpx, name)


class _NotAPlugin:
    """A test double of the suites: no settings mixin, so the boundaries call it as it is."""

    provider_code = "double"


class _BrokenScope(MockProvider):
    """mockprov with a ``cooldown_scope`` hook that fails."""

    def cooldown_scope(self, identifier, identifier_type=None, provider_params=None):
        raise RuntimeError("the scope hook failed")


class _NoTextScope(MockProvider):
    """mockprov with a ``cooldown_scope`` hook that answers something other than a non-empty text."""

    def __init__(self, answer: object) -> None:
        super().__init__()
        self._answer = answer

    def cooldown_scope(self, identifier, identifier_type=None, provider_params=None):
        return self._answer


class _SlotsRefusal(RateLimitedError):
    """A refusal whose text a ``__str__`` builds from state outside ``__dict__``: masking cannot rewrite it."""

    __slots__ = ("_hidden",)

    def __init__(self, hidden: str) -> None:
        super().__init__("opaque refusal", retry_after=20.0, scope="api.example")
        self._hidden = hidden

    def __str__(self) -> str:
        return f"refused for key {self._hidden}"


@pytest.fixture(autouse=True)
def pauses_on(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every inherited ``LIBREFOLIO_PROVIDER_COOLDOWN_*`` removed, then the defaults written out: base 60 s, max 3600 s."""
    for name in list(os.environ):
        if name.startswith("LIBREFOLIO_PROVIDER_COOLDOWN_"):
            monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(BASE_VARIABLE, "60")
    monkeypatch.setenv(MAX_VARIABLE, "3600")


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture(autouse=True)
def cooldowns(monkeypatch: pytest.MonkeyPatch, clock: FakeClock) -> Cooldowns:
    """A private instance on the fake clock, without jitter, in place of the process's: no test pauses the shipped one."""
    private = Cooldowns(60, 3600, jitter=0.0, trial_seconds=TRIAL_SECONDS, clock=clock)
    monkeypatch.setattr(provider_cooldown, "PROVIDER_COOLDOWNS", private)
    return private


def _state(cooldowns: Cooldowns) -> dict:
    """``{key: (refusals in a row, seconds left)}`` of every pause the private instance holds."""
    return {state.key: (state.refusals, state.remaining) for state in cooldowns.snapshot()}


async def _returns(value):
    return value


async def _raises(error: BaseException):
    raise error


def _current(plugin: MockProvider, params: dict | None = None) -> _Calls:
    return _Calls(lambda: plugin.get_current_value("MOCK", IdentifierType.TICKER, params or {}))


async def _refuse(plugin: MockProvider, asked: object) -> AssetRateLimitedError:
    """One call mockprov refuses (``mock_rate_limited``), through the boundary: the pause it decided."""
    with pytest.raises(AssetRateLimitedError) as refused:
        await core.call_provider(plugin, _current(plugin, {"mock_rate_limited": asked}), timeout=10)
    return refused.value


async def _refuse_fx(monkeypatch: pytest.MonkeyPatch, fx: MockFXProvider, retry_after: float | None) -> FXRateLimitedError:
    """One call MockFX refuses, through the boundary; MockFX answers again afterwards (its pause stays)."""
    monkeypatch.setattr(MockFXProvider, "rate_limited", True)
    monkeypatch.setattr(MockFXProvider, "rate_limited_retry_after", retry_after)
    with pytest.raises(FXRateLimitedError) as refused:
        await fx_runtime.call_fx_provider(fx, lambda: fx.fetch_rates(RANGE, ["USD"]))
    monkeypatch.setattr(MockFXProvider, "rate_limited", False)
    return refused.value


def _marker() -> str:
    return f"lfsecret{uuid.uuid4().hex[:16]}"


# =============================================================================
# 1–2. A refusal pauses; during the pause nothing reaches the plugin
# =============================================================================


@pytest.mark.parametrize(
    ("asked", "pause"),
    [
        pytest.param(30, 60.0, id="retry-after-below-base"),
        pytest.param(90, 90.0, id="retry-after-above-base"),
        pytest.param(7200, 7200.0, id="retry-after-above-the-cap"),
        pytest.param(True, 60.0, id="no-retry-after"),
    ],
)
@pytest.mark.asyncio
async def test_an_asset_refusal_pauses_the_provider_for_max_of_base_and_retry_after(cooldowns: Cooldowns, asked: object, pause: float):
    """XRL-B01 — contract 1: one call, one refusal, a pause of max(60, Retry-After) under the provider's key, reported as ``retry_after``."""
    plugin = MockProvider()
    calls = _current(plugin, {"mock_rate_limited": asked})

    with pytest.raises(AssetRateLimitedError) as refused:
        await core.call_provider(plugin, calls, timeout=10)

    assert calls.count == 1
    assert (refused.value.error_code, refused.value.retry_after, refused.value.scope) == ("RATE_LIMITED", pause, None)
    assert _state(cooldowns) == {MOCK_KEY: (1, pause)}


@pytest.mark.asyncio
async def test_while_an_asset_provider_is_paused_no_operation_reaches_it(clock: FakeClock, cooldowns: Cooldowns):
    """XRL-B02 — contract 2: current value, history, metadata and search refused at once, with the seconds left; no refusal counted."""
    print_section("XRL-B02: asset boundary, the pause holds every operation")
    plugin = MockProvider()
    await _refuse(plugin, 90)
    clock.now += 25
    operations = {
        "current": _current(plugin),
        "history": _Calls(lambda: plugin.get_history_value("MOCK", IdentifierType.TICKER, {}, *RANGE)),
        "metadata": _Calls(lambda: plugin.fetch_asset_metadata("MOCK", IdentifierType.TICKER, {})),
        "search": _Calls(lambda: plugin.search("anything")),
    }

    waits = {}
    for name, calls in operations.items():
        with pytest.raises(AssetRateLimitedError) as paused:
            await core.call_provider(plugin, calls, timeout=10)
        waits[name] = (paused.value.error_code, paused.value.retry_after, paused.value.scope)

    assert {name: calls.count for name, calls in operations.items()} == dict.fromkeys(operations, 0)
    assert waits == dict.fromkeys(operations, ("RATE_LIMITED", 65.0, None))
    assert _state(cooldowns) == {MOCK_KEY: (1, 65.0)}
    print_success("four operations, zero plugin calls, 65 s left each")


# =============================================================================
# 3–4. After the pause: one trial; its answer ends the pause, any other end frees it
# =============================================================================


@pytest.mark.asyncio
async def test_after_an_asset_pause_one_trial_goes_and_a_concurrent_caller_is_refused(clock: FakeClock, cooldowns: Cooldowns):
    """XRL-B03 — contract 3: the trial is held in the provider's thread; a second caller meanwhile is refused for the trial's window; the answer ends the pause."""
    print_section("XRL-B03: asset boundary, one trial after the pause")
    plugin = MockProvider()
    await _refuse(plugin, 30)
    clock.now += 60
    started, release = threading.Event(), threading.Event()

    async def held_answer():
        started.set()
        assert release.wait(10), "the test never released the trial call"
        return await plugin.get_current_value("MOCK", IdentifierType.TICKER, {})

    trial_calls, second = _Calls(held_answer), _current(plugin)
    trial = asyncio.create_task(core.call_provider(plugin, trial_calls, timeout=30))
    try:
        assert await asyncio.to_thread(started.wait, 10), "the trial call never reached the plugin"
        with pytest.raises(AssetRateLimitedError) as waiting:
            await core.call_provider(plugin, second, timeout=10)
    finally:
        release.set()
    answer = await trial

    assert (trial_calls.count, second.count) == (1, 0)
    assert waiting.value.retry_after == TRIAL_SECONDS
    assert answer.value == Decimal("100.00")
    assert _state(cooldowns) == {}, "the trial's answer ends the pause"
    third = _current(plugin)
    await core.call_provider(plugin, third, timeout=10)
    assert third.count == 1
    print_success("one trial, the other refused, the answer ended the pause")


@pytest.mark.asyncio
async def test_another_error_of_the_trial_frees_it_for_the_next_asset_caller(clock: FakeClock, cooldowns: Cooldowns):
    """XRL-B04 — contract 4: a NOT_FOUND from the trial is no verdict: the record stays, the next caller goes through and its answer ends the pause."""
    plugin = MockProvider()
    await _refuse(plugin, 30)
    clock.now += 60
    failing = _Calls(lambda: plugin.get_current_value("INVALID_TICKER_12345", IdentifierType.TICKER, {}))

    with pytest.raises(AssetSourceError) as failed:
        await core.call_provider(plugin, failing, timeout=10)

    assert failed.value.error_code == "NOT_FOUND" and failing.count == 1
    (state,) = cooldowns.snapshot()
    assert (state.key, state.refusals, state.trial_in_flight) == (MOCK_KEY, 1, False)
    following = _current(plugin)
    await core.call_provider(plugin, following, timeout=10)
    assert following.count == 1
    assert _state(cooldowns) == {}


@pytest.mark.asyncio
async def test_a_cancelled_trial_frees_it_for_the_next_asset_caller(clock: FakeClock, cooldowns: Cooldowns):
    """XRL-B05 — contract 4: the caller of the trial is cancelled while the provider's thread holds it: the next caller goes through."""
    plugin = MockProvider()
    await _refuse(plugin, 30)
    clock.now += 60
    started, release, finished = threading.Event(), threading.Event(), threading.Event()

    async def held_answer():
        started.set()
        try:
            release.wait(10)
            return await plugin.get_current_value("MOCK", IdentifierType.TICKER, {})
        finally:
            finished.set()

    trial = asyncio.create_task(core.call_provider(plugin, _Calls(held_answer), timeout=30))
    try:
        assert await asyncio.to_thread(started.wait, 10), "the trial call never reached the plugin"
        trial.cancel()
        with pytest.raises(asyncio.CancelledError):
            await trial
        (state,) = cooldowns.snapshot()
        assert (state.refusals, state.trial_in_flight) == (1, False)
        following = _current(plugin)
        await core.call_provider(plugin, following, timeout=10)
        assert following.count == 1
        assert _state(cooldowns) == {}
    finally:
        release.set()
        assert await asyncio.to_thread(finished.wait, 10), "the abandoned provider thread never ended"


# =============================================================================
# 5. Pauses off
# =============================================================================


@pytest.mark.asyncio
async def test_with_pauses_off_every_asset_call_reaches_the_plugin_with_its_own_retry_after(monkeypatch: pytest.MonkeyPatch, cooldowns: Cooldowns):
    """XRL-B06 — contract 5: base 0 — three refused calls, three plugin calls, the plugin's 30 s (or nothing) kept, nothing recorded."""
    monkeypatch.setenv(BASE_VARIABLE, "0")
    plugin = MockProvider()
    timed, untimed = _current(plugin, {"mock_rate_limited": 30}), _current(plugin, {"mock_rate_limited": True})

    waits = []
    for calls in (timed, timed, untimed):
        with pytest.raises(AssetRateLimitedError) as refused:
            await core.call_provider(plugin, calls, timeout=10)
        waits.append(refused.value.retry_after)

    assert (timed.count, untimed.count) == (2, 1)
    assert waits == [30.0, 30.0, None]
    assert _state(cooldowns) == {}


# =============================================================================
# 6. Scope
# =============================================================================


@pytest.mark.asyncio
async def test_two_css_sites_pause_apart(monkeypatch: pytest.MonkeyPatch, cooldowns: Cooldowns):
    """XRL-B07 — contract 6: a 429 from one host pauses that host only, for its Retry-After; the other host keeps answering."""
    print_section("XRL-B07: CSS scraper, one pause per site")
    requests_by_host: Counter[str] = Counter()

    def handler(request: httpx.Request) -> httpx.Response:
        requests_by_host[request.url.host] += 1
        if request.url.host == "busy.example":
            return httpx.Response(429, headers={"Retry-After": "300"})
        return httpx.Response(200, text='<html><span class="price">101.25</span></html>')

    monkeypatch.setattr(css_module, "httpx", _HttpxWithTransport(handler))
    css = CSSScraperProvider()

    async def scrape(url: str):
        scope = core.cooldown_scope_for(css, url, IdentifierType.OTHER, CSS_PARAMS)
        return await core.call_provider(css, lambda: css.get_current_value(url, IdentifierType.OTHER, CSS_PARAMS), timeout=10, scope=scope)

    with pytest.raises(AssetRateLimitedError) as refused:
        await scrape("https://busy.example/quote/1")
    calm = await scrape("https://calm.example/quote/1")
    with pytest.raises(AssetRateLimitedError) as paused:
        await scrape("https://BUSY.example:8443/quote/2")
    calm_again = await scrape("https://calm.example/quote/2")

    assert (refused.value.retry_after, refused.value.scope) == (300.0, "busy.example")
    assert (paused.value.retry_after, paused.value.scope) == (300.0, "busy.example")
    assert (calm.value, calm_again.value) == (Decimal("101.25"), Decimal("101.25"))
    assert dict(requests_by_host) == {"busy.example": 1, "calm.example": 2}
    assert _state(cooldowns) == {("asset", "css_scraper", "busy.example"): (1, 300.0)}
    print_success("busy.example paused 300 s after one request, calm.example asked twice")


@pytest.mark.asyncio
async def test_the_plugins_own_scope_applies_when_the_caller_names_none(cooldowns: Cooldowns):
    """XRL-B08 — contract 6: a call made without a scope (a search) whose refusal names one pauses that scope, and the error carries it."""
    plugin = MockProvider()

    with pytest.raises(AssetRateLimitedError) as refused:
        await core.call_provider(plugin, _Calls(lambda: _raises(AssetRateLimitedError("site refused", retry_after=90.0, scope="site.example"))), timeout=10)

    assert (refused.value.retry_after, refused.value.scope) == (90.0, "site.example")
    assert _state(cooldowns) == {("asset", "mockprov", "site.example"): (1, 90.0)}
    paused = _current(plugin)
    with pytest.raises(AssetRateLimitedError):
        await core.call_provider(plugin, paused, timeout=10, scope="site.example")
    assert paused.count == 0


def test_a_broken_scope_hook_means_the_whole_provider_and_is_logged():
    """XRL-B09 — contract 6: ``cooldown_scope_for`` answers None for a hook that raises, and logs a warning naming the provider and the error type."""
    canary = f"xrl-canary-{uuid.uuid4().hex}"

    with capture_logs() as events:
        core.logger.warning(canary)
        scope = core.cooldown_scope_for(_BrokenScope(), "MOCK", IdentifierType.TICKER, {})

    assert any(event.get("event") == canary for event in events), "barrier: the core's logger does not reach capture_logs"
    warnings = [event for event in events if event.get("log_level") == "warning" and event.get("event") != canary]
    assert scope is None
    assert [(event.get("provider"), event.get("error")) for event in warnings] == [("mockprov", "RuntimeError")]


@pytest.mark.parametrize("answer", [42, "", None, b"bytes.example"], ids=["number", "empty", "none", "bytes"])
def test_a_scope_hook_that_answers_no_text_means_the_whole_provider(answer: object):
    """XRL-B10 — contract 6: only a non-empty text is a scope."""
    assert core.cooldown_scope_for(_NoTextScope(answer), "MOCK") is None


def test_an_object_without_the_hook_has_no_scope():
    """XRL-B11 — contract 6: a test double without ``cooldown_scope`` pauses, if anything, the whole provider."""
    assert core.cooldown_scope_for(_NotAPlugin(), "MOCK") is None
    assert core.cooldown_scope_for(object(), "MOCK") is None


# =============================================================================
# 7. Test doubles
# =============================================================================


@pytest.mark.asyncio
async def test_a_test_double_is_never_paused_and_never_pauses(cooldowns: Cooldowns):
    """XRL-B12 — contract 7: with its code paused by hand, a double is still called; its refusal passes untouched and records nothing, at both boundaries."""
    record_refusal("asset", "double", None, 600)
    record_refusal("fx", "double", None, 600)
    double = _NotAPlugin()
    asset_answer, fx_answer = _Calls(lambda: _returns("asset answer")), _Calls(lambda: _returns("fx answer"))
    asset_refusal, fx_refusal = AssetRateLimitedError("double refused", retry_after=30.0), FXRateLimitedError("double refused", retry_after=30.0)

    assert await core.call_provider(double, asset_answer, timeout=5) == "asset answer"
    assert await fx_runtime.call_fx_provider(double, fx_answer) == "fx answer"
    with pytest.raises(AssetRateLimitedError) as asset_raised:
        await core.call_provider(double, _Calls(lambda: _raises(asset_refusal)), timeout=5)
    with pytest.raises(FXRateLimitedError) as fx_raised:
        await fx_runtime.call_fx_provider(double, _Calls(lambda: _raises(fx_refusal)))

    assert (asset_answer.count, fx_answer.count) == (1, 1)
    assert asset_raised.value is asset_refusal and fx_raised.value is fx_refusal
    assert (asset_refusal.retry_after, fx_refusal.retry_after) == (30.0, 30.0)
    assert _state(cooldowns) == {("asset", "double", None): (1, 600.0), ("fx", "double", None): (1, 600.0)}


# =============================================================================
# 8. A refusal of another domain
# =============================================================================


@pytest.mark.parametrize(
    "foreign",
    [
        pytest.param(lambda: RateLimitedError("slow down", retry_after=45.0, scope="api.example"), id="bare-marker"),
        pytest.param(lambda: FXRateLimitedError("slow down", retry_after=45.0, scope="api.example"), id="fx-refusal"),
    ],
)
@pytest.mark.asyncio
async def test_a_foreign_refusal_from_an_asset_plugin_leaves_as_an_asset_refusal(cooldowns: Cooldowns, foreign: Callable[[], RateLimitedError]):
    """XRL-B13 — contract 8: a fresh ``AssetRateLimitedError`` naming the provider, with the pause decided and the plugin's scope, no link to the original."""
    plugin = MockProvider()

    with pytest.raises(AssetRateLimitedError) as raised:
        await core.call_provider(plugin, _Calls(lambda: _raises(foreign())), timeout=10)

    error = raised.value
    assert type(error) is AssetRateLimitedError and error.error_code == "RATE_LIMITED"
    assert (error.retry_after, error.scope) == (60.0, "api.example")
    assert error.__cause__ is None and error.__context__ is None
    assert "mockprov" in error.message
    assert _state(cooldowns) == {("asset", "mockprov", "api.example"): (1, 60.0)}


@pytest.mark.parametrize(
    "foreign",
    [
        pytest.param(lambda: RateLimitedError("slow down", retry_after=200.0), id="bare-marker"),
        pytest.param(lambda: AssetRateLimitedError("slow down", retry_after=200.0), id="asset-refusal"),
    ],
)
@pytest.mark.asyncio
async def test_a_foreign_refusal_from_an_fx_plugin_leaves_as_an_fx_refusal(cooldowns: Cooldowns, foreign: Callable[[], RateLimitedError]):
    """XRL-B14 — contract 8: a fresh ``FXRateLimitedError`` naming the provider, with the pause decided, no link to the original."""
    fx = MockFXProvider()

    with pytest.raises(FXRateLimitedError) as raised:
        await fx_runtime.call_fx_provider(fx, _Calls(lambda: _raises(foreign())))

    error = raised.value
    assert type(error) is FXRateLimitedError and error.retry_after == 200.0
    assert error.__cause__ is None and error.__context__ is None
    assert "MOCKFX" in str(error)
    assert _state(cooldowns) == {MOCKFX_KEY: (1, 200.0)}


# =============================================================================
# 9. Secrets
# =============================================================================


@pytest.mark.asyncio
async def test_an_asset_refusal_showing_a_secret_is_masked_in_place():
    """XRL-B15 — contract 9: the very error the plugin raised, its text masked, its wait set to the pause."""
    secret = _marker()
    plugin = MockProvider()
    plugin.bind_settings(BoundSettings(MockProvider.settings_fields, {}, {"api_key": secret}))
    raised_by_the_plugin = AssetRateLimitedError(f"429 for key {secret}", retry_after=30.0)

    with pytest.raises(AssetRateLimitedError) as raised:
        await core.call_provider(plugin, _Calls(lambda: _raises(raised_by_the_plugin)), timeout=10)

    assert raised.value is raised_by_the_plugin
    assert (raised.value.message, str(raised.value)) == (f"429 for key {MASK}", f"429 for key {MASK}")
    assert raised.value.retry_after == 60.0


@pytest.mark.asyncio
async def test_an_asset_refusal_that_cannot_be_masked_is_replaced(cooldowns: Cooldowns):
    """XRL-B16 — contract 9: a fresh ``AssetRateLimitedError`` with the pause and the plugin's scope, its text masked, no link to the original."""
    secret = _marker()
    plugin = MockProvider()
    plugin.bind_settings(BoundSettings(MockProvider.settings_fields, {}, {"api_key": secret}))

    with pytest.raises(AssetRateLimitedError) as raised:
        await core.call_provider(plugin, _Calls(lambda: _raises(_SlotsRefusal(secret))), timeout=10)

    error = raised.value
    assert type(error) is AssetRateLimitedError
    assert (error.retry_after, error.scope) == (60.0, "api.example")
    assert secret not in str(error) and f"_SlotsRefusal: refused for key {MASK}" in str(error)
    assert error.__cause__ is None and error.__context__ is None
    assert _state(cooldowns) == {("asset", "mockprov", "api.example"): (1, 60.0)}


@pytest.mark.asyncio
async def test_an_fx_refusal_showing_a_secret_is_masked_in_place(cooldowns: Cooldowns):
    """XRL-B17 — contract 9 at the FX boundary: the very error, its text masked, the pause it decided holding the next call."""
    secret = _marker()
    fx = MockFXProvider()
    fx.bind_settings(BoundSettings(MockFXProvider.settings_fields, {}, {"api_key": secret}))
    raised_by_the_plugin = FXRateLimitedError(f"429 for token {secret}", retry_after=90.0)
    following = _Calls(lambda: _returns("never asked"))

    with pytest.raises(FXRateLimitedError) as masked:
        await fx_runtime.call_fx_provider(fx, _Calls(lambda: _raises(raised_by_the_plugin)))
    with pytest.raises(FXRateLimitedError) as paused:
        await fx_runtime.call_fx_provider(MockFXProvider(), following)

    assert masked.value is raised_by_the_plugin
    assert (str(masked.value), masked.value.retry_after) == (f"429 for token {MASK}", 90.0)
    assert (paused.value.retry_after, following.count) == (90.0, 0)
    assert _state(cooldowns) == {MOCKFX_KEY: (1, 90.0)}


@pytest.mark.asyncio
async def test_an_fx_refusal_that_cannot_be_masked_is_replaced(cooldowns: Cooldowns):
    """XRL-B18 — contract 9 at the FX boundary: a fresh ``FXRateLimitedError`` with the pause, its text masked, no link to the original."""
    secret = _marker()
    fx = MockFXProvider()
    fx.bind_settings(BoundSettings(MockFXProvider.settings_fields, {}, {"api_key": secret}))

    with pytest.raises(FXRateLimitedError) as raised:
        await fx_runtime.call_fx_provider(fx, _Calls(lambda: _raises(_SlotsRefusal(secret))))

    error = raised.value
    assert type(error) is FXRateLimitedError and error.retry_after == 60.0
    assert secret not in str(error) and f"_SlotsRefusal: refused for key {MASK}" in str(error)
    assert error.__cause__ is None and error.__context__ is None
    assert _state(cooldowns) == {MOCKFX_KEY: (1, 60.0)}


# =============================================================================
# 1–5 at the FX boundary
# =============================================================================


@pytest.mark.parametrize(
    ("retry_after", "pause"),
    [
        pytest.param(120.0, 120.0, id="retry-after-above-base"),
        pytest.param(15.0, 60.0, id="retry-after-below-base"),
        pytest.param(None, 60.0, id="no-retry-after"),
    ],
)
@pytest.mark.asyncio
async def test_an_fx_refusal_pauses_the_provider_for_max_of_base_and_retry_after(monkeypatch: pytest.MonkeyPatch, cooldowns: Cooldowns, retry_after: float | None, pause: float):
    """XRL-B19 — contract 1 at the FX boundary: MockFX's «too many requests» mode, one call, the pause as ``retry_after``."""
    monkeypatch.setattr(MockFXProvider, "rate_limited", True)
    monkeypatch.setattr(MockFXProvider, "rate_limited_retry_after", retry_after)
    fx = MockFXProvider()
    calls = _Calls(lambda: fx.fetch_rates(RANGE, ["USD", "GBP"]))

    with pytest.raises(FXRateLimitedError) as refused:
        await fx_runtime.call_fx_provider(fx, calls)

    assert calls.count == 1
    assert (refused.value.error_code, refused.value.retry_after, refused.value.scope) == ("RATE_LIMITED", pause, None)
    assert _state(cooldowns) == {MOCKFX_KEY: (1, pause)}


@pytest.mark.asyncio
async def test_while_an_fx_provider_is_paused_neither_catalogue_nor_rates_are_asked(monkeypatch: pytest.MonkeyPatch, clock: FakeClock, cooldowns: Cooldowns):
    """XRL-B20 — contract 2 at the FX boundary: a refused catalogue pauses the rates too; MockFX answering again changes nothing until the pause ends."""
    monkeypatch.setattr(MockFXProvider, "rate_limited", True)
    monkeypatch.setattr(MockFXProvider, "rate_limited_retry_after", 300.0)
    fx = MockFXProvider()
    with pytest.raises(FXRateLimitedError):
        await fx_runtime.call_fx_provider(fx, lambda: fx.get_supported_currencies())
    monkeypatch.setattr(MockFXProvider, "rate_limited", False)
    clock.now += 100
    catalogue, rates = _Calls(lambda: fx.get_supported_currencies()), _Calls(lambda: fx.fetch_rates(RANGE, ["USD"]))

    waits = []
    for calls in (catalogue, rates):
        with pytest.raises(FXRateLimitedError) as paused:
            await fx_runtime.call_fx_provider(fx, calls)
        waits.append(paused.value.retry_after)

    assert (catalogue.count, rates.count) == (0, 0)
    assert waits == [200.0, 200.0]
    assert _state(cooldowns) == {MOCKFX_KEY: (1, 200.0)}


@pytest.mark.asyncio
async def test_after_an_fx_pause_one_trial_goes_and_a_concurrent_caller_is_refused(monkeypatch: pytest.MonkeyPatch, clock: FakeClock, cooldowns: Cooldowns):
    """XRL-B21 — contract 3 at the FX boundary: the trial waits on an event; the concurrent caller is refused for the trial's window; the answer ends the pause."""
    print_section("XRL-B21: FX boundary, one trial after the pause")
    fx = MockFXProvider()
    await _refuse_fx(monkeypatch, fx, 60.0)
    clock.now += 60
    started, release = asyncio.Event(), asyncio.Event()

    async def held_answer():
        started.set()
        await release.wait()
        return await fx.fetch_rates(RANGE, ["USD"])

    trial_calls, second = _Calls(held_answer), _Calls(lambda: fx.fetch_rates(RANGE, ["USD"]))
    trial = asyncio.create_task(fx_runtime.call_fx_provider(fx, trial_calls))
    try:
        await asyncio.wait_for(started.wait(), timeout=10)
        with pytest.raises(FXRateLimitedError) as waiting:
            await fx_runtime.call_fx_provider(fx, second)
    finally:
        release.set()
    answer = await trial

    assert (trial_calls.count, second.count) == (1, 0)
    assert waiting.value.retry_after == TRIAL_SECONDS
    assert [rate for _day, _base, _quote, rate in answer["USD"]], "the trial answered with rates"
    assert _state(cooldowns) == {}
    print_success("one trial, the other refused, the answer ended the pause")


@pytest.mark.asyncio
async def test_another_error_or_a_cancellation_of_the_fx_trial_frees_it(monkeypatch: pytest.MonkeyPatch, clock: FakeClock, cooldowns: Cooldowns):
    """XRL-B22 — contract 4 at the FX boundary: an ``FXServiceError``, then a cancelled trial, each leave the way to the next caller."""
    fx = MockFXProvider()
    await _refuse_fx(monkeypatch, fx, 60.0)
    clock.now += 60

    with pytest.raises(FXServiceError) as failed:
        await fx_runtime.call_fx_provider(fx, _Calls(lambda: _raises(FXServiceError("upstream answered 500"))))
    (after_error,) = cooldowns.snapshot()

    started, never = asyncio.Event(), asyncio.Event()

    async def hangs():
        started.set()
        await never.wait()

    trial = asyncio.create_task(fx_runtime.call_fx_provider(fx, _Calls(hangs)))
    await asyncio.wait_for(started.wait(), timeout=10)
    trial.cancel()
    with pytest.raises(asyncio.CancelledError):
        await trial
    (after_cancel,) = cooldowns.snapshot()
    following = _Calls(lambda: fx.get_supported_currencies())
    await fx_runtime.call_fx_provider(fx, following)

    assert type(failed.value) is FXServiceError
    assert (after_error.refusals, after_error.trial_in_flight) == (1, False)
    assert (after_cancel.refusals, after_cancel.trial_in_flight) == (1, False)
    assert following.count == 1
    assert _state(cooldowns) == {}


@pytest.mark.asyncio
async def test_with_pauses_off_every_fx_call_reaches_the_plugin_with_its_own_retry_after(monkeypatch: pytest.MonkeyPatch, cooldowns: Cooldowns):
    """XRL-B23 — contract 5 at the FX boundary: base 0 — every call reaches MockFX, its 120 s (or nothing) kept, nothing recorded."""
    monkeypatch.setenv(BASE_VARIABLE, "0")
    monkeypatch.setattr(MockFXProvider, "rate_limited", True)
    fx = MockFXProvider()
    calls = _Calls(lambda: fx.fetch_rates(RANGE, ["USD"]))

    waits = []
    for retry_after in (120.0, 120.0, None):
        monkeypatch.setattr(MockFXProvider, "rate_limited_retry_after", retry_after)
        with pytest.raises(FXRateLimitedError) as refused:
            await fx_runtime.call_fx_provider(fx, calls)
        waits.append(refused.value.retry_after)

    assert calls.count == 3
    assert waits == [120.0, 120.0, None]
    assert _state(cooldowns) == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

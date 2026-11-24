"""Plan 68 C0: the four routes that make the enrichers call their sources with any identifier a user types draw from the
per-user limit of ``POST /assets/provider/probe`` — the same limiter, the same count.

The routes: ``POST /assets/enrichers/recognize`` (``recognize_enrichers``, a Server-Sent Events stream that asks every
installed enricher), ``POST /assets/enrichers/{code}/test`` (``test_enricher``), ``GET /assets/enrichers/{code}/search``
(``search_enricher``) and ``POST /assets/profile/ask`` (``ask_profile``). Each asks ``providers.probe_limiter()`` — the
limiter in force, ``LIBREFOLIO_PROBE_RATE_LIMIT`` a minute (30 by default, ``0`` off), one ``SlidingWindowLimiter`` per
value in ``PROBES_BY_LIMIT`` keyed by user id — and counts ONE hit for the caller before anything else, however many
enrichers the call then reaches. A refused call answers 429 ``{"error_code": "PROBE_RATE_LIMITED", "retry_after": s,
"message": …}`` with ``Retry-After: s``, ``s = max(1, ceil(wait))`` — exactly as the probe — reaches no registry, no
enricher, no database, and is not counted. Recognize checks the limit before its stream starts: a refused call raises
from the route itself, it is never a stream. ``POST /assets/profile/refresh`` («Aggiorna», reading saved bindings) is
not limited.

Called directly, never through the shared backend (whose lane runs the limit at ``0``). As in
``test_probe_rate_limit.py``: a private ``SlidingWindowLimiter`` of ``LIMIT`` hits per ``WINDOW`` s on a fake clock
answers ``probe_limiter()`` through the providers module (``monkeypatch``), time moves by advancing the clock, ``LIMIT``
is not 30 on purpose, no assertion reads the message text. Two tests let the real ``probe_limiter()`` build its limiters
from the variable, each on the fake clock. What the routes call after the limit is a recording stub: the enricher
registry's lookups, the plugin's ``search`` and ``recognize``, the route module's ``installed_enrichers``,
``recognize_cascade`` and ``default_order``, the profile's ``read_and_merge`` and ``refresh_assets``, the manager's
probe, and a database session that records — and refuses — any use. The user is passed positionally: the routes may
rename their user parameter when they start reading its id.

Red on HEAD ``fb1e66267`` (before C0): every test that expects a refusal or a count on the four routes — they ask no
limiter. Guards, green there and kept: the limit off (``probe_limiter()`` None, or the variable at ``0``) limits none
of them, and refresh is not limited.

Pure: no database, no server, no network.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Awaitable, Callable

import pytest
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from backend.app.api.v1.assets import enrichers, profile, providers
from backend.app.db.models import AssetType
from backend.app.schemas.assets.enrichers import FAEnricherBinding, FAEnricherRecognizeRequest, FAEnricherTestRequest
from backend.app.schemas.assets.profile import FAProfileAskRequest
from backend.app.schemas.provider import FAProviderProbeRequest, ProbeOperation
from backend.app.services.assets.manager import AssetSourceManager
from backend.app.services.enrichers.base import EnricherBinding
from backend.app.services.enrichers.recognize import Recognized, RecognizeStatus
from backend.app.services.enrichers.registry import EnricherRegistry
from backend.app.utils.runtime.rate_window import SlidingWindowLimiter

LIMIT = 5
WINDOW = 60
START = 1_000_000.0
USER_A = SimpleNamespace(id=9_201)
USER_B = SimpleNamespace(id=9_202)

PROBE_LIMIT_VARIABLE = "LIBREFOLIO_PROBE_RATE_LIMIT"
#: The window of every limiter ``probe_limiter()`` builds, in seconds.
PROBE_WINDOW = 60
#: Calls of one user while the limit is off: more than the default 30 allows.
OFF_CALLS = 40

#: The enricher the search and test routes name; the registry stub serves it and nothing else.
CODE = "c0-stub-enricher"
UNKNOWN_CODE = "c0-no-such-enricher"
#: The installed enrichers recognize asks, all of them in one call.
INSTALLED = ("c0-stub-a", "c0-stub-b", "c0-stub-c")
#: The four routes under the probe's limit.
ENRICHER_ROUTES = ("recognize", "search", "test", "ask")
#: What each route reaches once past the limit: the tag its stub records.
REACHES = {"recognize": "cascade", "search": "search", "test": "test", "ask": "ask", "probe": "probe", "refresh": "refresh"}
#: The answer of the manager's probe stub, returned by the probe route as it is.
_PROBE_ANSWER = object()


class FakeClock:
    """A monotonic clock that moves only when told to."""

    def __init__(self, start: float) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock(START)


@pytest.fixture(autouse=True)
def _no_inherited_probe_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Any ``LIBREFOLIO_PROBE_RATE_LIMIT`` the process inherited is removed: a test sees only the value it sets."""
    monkeypatch.delenv(PROBE_LIMIT_VARIABLE, raising=False)


@pytest.fixture(autouse=True)
def _fresh_probe_limiters(monkeypatch: pytest.MonkeyPatch) -> None:
    """The test's own limiters by limit and its own «already logged»: nothing counted or logged by another test, or by
    the module's import, is seen here, and nothing of this test outlives it."""
    monkeypatch.setattr(providers, "PROBES_BY_LIMIT", {}, raising=True)
    monkeypatch.setattr(providers, "_PROBE_SETTING_LOGGED", set(), raising=True)


@pytest.fixture
def limiter(monkeypatch: pytest.MonkeyPatch, clock: FakeClock) -> SlidingWindowLimiter:
    """A private limiter on the fake clock, answered by ``providers.probe_limiter()`` in place of the one in force."""
    private = SlidingWindowLimiter(LIMIT, WINDOW, clock=clock)
    monkeypatch.setattr(providers, "probe_limiter", lambda: private, raising=True)
    return private


@pytest.fixture
def built_on_fake_clock(monkeypatch: pytest.MonkeyPatch, clock: FakeClock) -> list[SlidingWindowLimiter]:
    """The limiters the real ``probe_limiter()`` builds, each a real ``SlidingWindowLimiter`` on the fake clock, in the
    order it builds them."""
    built: list[SlidingWindowLimiter] = []

    def on_fake_clock(limit: int, window_seconds: float, **options: Any) -> SlidingWindowLimiter:
        made = SlidingWindowLimiter(limit, window_seconds, clock=clock, **options)
        built.append(made)
        return made

    monkeypatch.setattr(providers, "SlidingWindowLimiter", on_fake_clock, raising=True)
    return built


# ============================================================================
# What the routes reach: recording stubs
# ============================================================================


class RecordingSession:
    """Stands in for the ``AsyncSession``: any use is recorded and refused — these routes reach no database here."""

    def __init__(self, events: list[tuple]) -> None:
        self._events = events

    def __getattr__(self, name: str) -> Callable[..., Awaitable[None]]:
        self._events.append(("session", name))

        async def refused(*_args: object, **_kwargs: object) -> None:
            raise AssertionError(f"session.{name} used: no database in this test")

        return refused


class StubEnricher:
    """An installed enricher: searches and recognizes, recording each call."""

    supports_search = True

    def __init__(self, code: str, events: list[tuple]) -> None:
        self.code = code
        self._events = events

    def search(self, query: str) -> list:
        self._events.append(("search", self.code, query))
        return []

    def recognize(self, binding: EnricherBinding) -> SimpleNamespace:
        self._events.append(("test", self.code, binding.identifier))
        return SimpleNamespace(found=True, name="C0 stub", page_url=None, identifiers={})


@dataclass
class Routes:
    """The routes called directly, and every event their stubs recorded, in order."""

    events: list[tuple]
    session: RecordingSession
    probe_request: FAProviderProbeRequest

    def reached(self, route: str) -> int:
        """How many times ``route`` got past the limit to what it calls."""
        return sum(1 for event in self.events if event[0] == REACHES[route])

    async def call(self, route: str, user: SimpleNamespace) -> Any:
        """One call of ``route`` as ``user``; recognize's stream is drained, so the cascade runs."""
        answer = await self.start(route, user)
        if route == "recognize":
            assert isinstance(answer, StreamingResponse), f"recognize must answer a stream when allowed, got {answer!r}"
            return [chunk async for chunk in answer.body_iterator]
        return answer

    async def start(self, route: str, user: SimpleNamespace) -> Any:
        """The route coroutine awaited, nothing more: recognize's stream is not read, so a refusal raised only while
        streaming (a 200 then a broken stream) does not count as a refusal."""
        if route == "recognize":
            return await enrichers.recognize_enrichers(RECOGNIZE_REQUEST, user)
        if route == "search":
            return await enrichers.search_enricher(CODE, "c0 word", user)
        if route == "test":
            return await enrichers.test_enricher(CODE, TEST_REQUEST, user)
        if route == "ask":
            return await profile.ask_profile(ASK_REQUEST, self.session, user)
        if route == "probe":
            return await providers.probe_provider_config(request=self.probe_request, current_user=user)
        if route == "refresh":
            return await profile.refresh_profile([9_999], self.session, user)
        raise AssertionError(f"unknown route {route}")

    async def passes(self, route: str, user: SimpleNamespace) -> None:
        """The call is allowed and reaches what the route calls."""
        before = self.reached(route)
        await self.call(route, user)
        assert self.reached(route) == before + 1, f"{route} did not reach its stub: {self.events[-5:]}"

    async def refused(self, route: str, user: SimpleNamespace) -> HTTPException:
        """The call raises the 429 ``PROBE_RATE_LIMITED`` from the route coroutine itself — for recognize, before any
        stream exists — and reaches nothing; returns it."""
        before = list(self.events)
        with pytest.raises(HTTPException) as excinfo:
            await self.start(route, user)
        refused = excinfo.value
        assert refused.status_code == 429, f"{route}: expected 429, got {refused.status_code}: {refused.detail}"
        assert isinstance(refused.detail, dict) and refused.detail.get("error_code") == "PROBE_RATE_LIMITED", refused.detail
        assert self.events == before, f"a refused {route} reached {self.events[len(before):]}"
        return refused


RECOGNIZE_REQUEST = FAEnricherRecognizeRequest(asset_type=AssetType.ETF, identifiers={"ISIN": "IE00C0STUB01"})
TEST_REQUEST = FAEnricherTestRequest(binding=FAEnricherBinding(identifier_type="ISIN", identifier="IE00C0STUB02"))
ASK_REQUEST = FAProfileAskRequest(asset_type=AssetType.ETF, enrichers={CODE: FAEnricherBinding(identifier_type="ISIN", identifier="IE00C0STUB03")})


@pytest.fixture
def routes(monkeypatch: pytest.MonkeyPatch) -> Routes:
    """Every call past the limit lands on a recording stub: no registry, no plugin, no network, no database."""
    events: list[tuple] = []
    stub = StubEnricher(CODE, events)

    def get_plugin(code: str) -> object | None:
        events.append(("registry", "get_plugin", code))
        return StubEnricher if code == CODE else None

    def get_plugin_instance(code: str, **_kwargs: object) -> StubEnricher | None:
        events.append(("registry", "get_plugin_instance", code))
        return stub if code == CODE else None

    monkeypatch.setattr(EnricherRegistry, "get_plugin", staticmethod(get_plugin))
    monkeypatch.setattr(EnricherRegistry, "get_plugin_instance", staticmethod(get_plugin_instance))

    def installed_enrichers() -> list[StubEnricher]:
        events.append(("installed",))
        return [StubEnricher(code, events) for code in INSTALLED]

    async def recognize_cascade(asset_type, identifiers, *, plugins=None, seeds=()):
        events.append(("cascade", tuple(plugin.code for plugin in plugins or ())))
        for plugin in plugins or ():
            events.append(("asked", plugin.code))
            yield Recognized(code=plugin.code, binding=EnricherBinding(identifier_type="ISIN", identifier=identifiers["ISIN"]), status=RecognizeStatus.FOUND)

    def default_order(asset_type, *, price_provider_code=None, found_order=()):
        return list(found_order)

    monkeypatch.setattr(enrichers, "installed_enrichers", installed_enrichers)
    monkeypatch.setattr(enrichers, "recognize_cascade", recognize_cascade)
    monkeypatch.setattr(enrichers, "default_order", default_order)

    async def read_and_merge(asset_type, config, keys=None):
        events.append(("ask", tuple(config)))
        return SimpleNamespace(voices={}, outcomes=[])

    async def refresh_assets(session, asset_ids, **_kwargs):
        events.append(("refresh", tuple(asset_ids)))
        return []

    monkeypatch.setattr(profile, "read_and_merge", read_and_merge)
    monkeypatch.setattr(profile, "refresh_assets", refresh_assets)

    async def recording_probe(config, operations, *, user_id=None):
        events.append(("probe", user_id))
        return _PROBE_ANSWER

    monkeypatch.setattr(AssetSourceManager, "probe_provider_config", staticmethod(recording_probe))

    probe_request = FAProviderProbeRequest(provider_code="scheduled_investment", identifier="c0-probe", identifier_type="AUTO_GENERATED", provider_params=None, operations=[ProbeOperation.CURRENT_PRICE])
    return Routes(events=events, session=RecordingSession(events), probe_request=probe_request)


async def _use_the_whole_limit(routes: Routes, route: str, user: SimpleNamespace) -> None:
    for _ in range(LIMIT):
        await routes.passes(route, user)


# ============================================================================
# Each route, on its own
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ENRICHER_ROUTES)
async def test_calls_up_to_the_limit_pass_each_counting_one_hit(limiter, routes, route):
    """Red: the first ``LIMIT`` calls of a user reach what the route calls, each counting ONE hit for the user's id on
    the limiter ``probe_limiter()`` answers (before C0: the routes counted nothing)."""
    await _use_the_whole_limit(routes, route, USER_A)
    assert limiter.count(USER_A.id) == LIMIT


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ENRICHER_ROUTES)
async def test_call_past_the_limit_is_429_and_reaches_nothing(limiter, routes, route):
    """Red: the call after the limit raises 429 ``PROBE_RATE_LIMITED`` with an int ``retry_after`` ≥ 1, the same value in
    ``Retry-After`` and a ``message`` — the probe's refusal —; it reaches no registry, enricher or session, and is not
    counted, so the next one is refused the same."""
    await _use_the_whole_limit(routes, route, USER_A)

    for _ in range(2):
        refused = await routes.refused(route, USER_A)
        assert set(refused.detail) == {"error_code", "retry_after", "message"}
        retry_after = refused.detail["retry_after"]
        assert type(retry_after) is int and retry_after >= 1, f"retry_after is {retry_after!r}"
        assert refused.headers == {"Retry-After": str(retry_after)}

    assert routes.reached(route) == LIMIT
    assert limiter.count(USER_A.id) == LIMIT


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ENRICHER_ROUTES)
@pytest.mark.parametrize(
    ("elapsed", "expected_seconds"),
    [
        pytest.param(0.0, 60, id="at-once-60"),
        pytest.param(20.5, 40, id="after-20.5s-ceil-39.5-is-40"),
        pytest.param(59.75, 1, id="after-59.75s-ceil-0.25-is-1"),
    ],
)
async def test_retry_after_is_the_wait_rounded_up_to_whole_seconds(limiter, routes, clock, route, elapsed, expected_seconds):
    """Red: ``retry_after`` (and ``Retry-After``) is the limiter's wait rounded up, never 0 — as for the probe."""
    await _use_the_whole_limit(routes, route, USER_A)
    clock.advance(elapsed)

    refused = await routes.refused(route, USER_A)
    assert refused.detail["retry_after"] == expected_seconds
    assert refused.headers == {"Retry-After": str(expected_seconds)}


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ENRICHER_ROUTES)
async def test_after_the_window_the_user_calls_again(limiter, routes, clock, route):
    """Red: half a second before the window ends the user is still refused; once the clock has moved past it, the call
    reaches the route's work again, one hit in the new window."""
    await _use_the_whole_limit(routes, route, USER_A)

    clock.advance(WINDOW - 0.5)
    await routes.refused(route, USER_A)

    clock.advance(1.0)
    await routes.passes(route, USER_A)
    assert routes.reached(route) == LIMIT + 1
    assert limiter.count(USER_A.id) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ENRICHER_ROUTES)
async def test_another_user_is_not_limited(limiter, routes, route):
    """Red: the count is per user: while one user is refused, another one's call passes."""
    await _use_the_whole_limit(routes, route, USER_A)
    await routes.refused(route, USER_A)

    await routes.passes(route, USER_B)
    assert (limiter.count(USER_A.id), limiter.count(USER_B.id)) == (LIMIT, 1)


@pytest.mark.asyncio
async def test_recognize_counts_one_hit_however_many_enrichers_it_asks(limiter, routes):
    """Red: one recognize asks every installed enricher (three here) and counts ONE hit, not one per enricher: ``LIMIT``
    recognizes ask ``3 × LIMIT`` enrichers and the next is refused before the stream starts. The hit is counted when the
    route answers, before a byte of the stream is read."""
    response = await routes.start("recognize", USER_A)
    assert isinstance(response, StreamingResponse), f"recognize must answer a stream when allowed, got {response!r}"
    assert limiter.count(USER_A.id) == 1, "the hit must be counted before the stream starts"
    [chunk async for chunk in response.body_iterator]
    assert [event[1] for event in routes.events if event[0] == "asked"] == list(INSTALLED)
    assert limiter.count(USER_A.id) == 1

    for _ in range(LIMIT - 1):
        await routes.passes("recognize", USER_A)
    assert sum(1 for event in routes.events if event[0] == "asked") == len(INSTALLED) * LIMIT
    assert limiter.count(USER_A.id) == LIMIT
    await routes.refused("recognize", USER_A)


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ["search", "test"])
async def test_unknown_enricher_counts_and_a_refusal_comes_before_the_404(limiter, routes, route):
    """Red: the limit is counted before anything else — a call naming an enricher that does not exist answers 404 and
    counts its hit; once the limit is used, the same call answers 429, never 404, without a registry lookup."""

    async def unknown() -> Any:
        if route == "search":
            return await enrichers.search_enricher(UNKNOWN_CODE, "c0 word", USER_A)
        return await enrichers.test_enricher(UNKNOWN_CODE, TEST_REQUEST, USER_A)

    with pytest.raises(HTTPException) as missing:
        await unknown()
    assert missing.value.status_code == 404, missing.value.detail
    assert limiter.count(USER_A.id) == 1

    for _ in range(LIMIT - 1):
        await routes.passes(route, USER_A)
    lookups = [event for event in routes.events if event[0] == "registry"]
    with pytest.raises(HTTPException) as refused:
        await unknown()
    assert refused.value.status_code == 429, f"expected 429 before the 404, got {refused.value.status_code}"
    assert [event for event in routes.events if event[0] == "registry"] == lookups, "a refused call looked the enricher up"


@pytest.mark.asyncio
async def test_a_refused_ask_by_asset_id_never_touches_the_database(limiter, routes):
    """Red: ``ask`` by ``asset_id`` reads the asset from the database; refused, it never touches the session."""
    await _use_the_whole_limit(routes, "ask", USER_A)
    before = list(routes.events)
    with pytest.raises(HTTPException) as refused:
        await profile.ask_profile(FAProfileAskRequest(asset_id=9_999), routes.session, USER_A)
    assert refused.value.status_code == 429, refused.value.detail
    assert routes.events == before, f"a refused ask reached {routes.events[len(before):]}"


# ============================================================================
# One count with the probe
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ENRICHER_ROUTES)
async def test_probes_and_enricher_calls_share_the_count(limiter, routes, route):
    """Red: probes and enricher calls of one user draw from one count: ``LIMIT - 1`` probes, then one call of ``route``
    passes, and the next call of any of the five routes — probe included — is refused."""
    for _ in range(LIMIT - 1):
        await routes.passes("probe", USER_A)
    await routes.passes(route, USER_A)
    assert limiter.count(USER_A.id) == LIMIT

    for following in (*ENRICHER_ROUTES, "probe"):
        await routes.refused(following, USER_A)


@pytest.mark.asyncio
async def test_enricher_calls_use_up_the_probe_limit(limiter, routes):
    """Red: the reverse: one call of each of the four routes, then one probe passes (the ``LIMIT``-th hit); the next
    probe is refused and never reaches the manager."""
    assert LIMIT == len(ENRICHER_ROUTES) + 1
    for route in ENRICHER_ROUTES:
        await routes.passes(route, USER_A)
    await routes.passes("probe", USER_A)

    await routes.refused("probe", USER_A)
    assert routes.reached("probe") == 1
    assert limiter.count(USER_A.id) == LIMIT


@pytest.mark.asyncio
async def test_a_user_held_by_the_shared_count_does_not_hold_another(limiter, routes):
    """Red: user A's count, spent over the five routes, refuses A everywhere; user B's probe and search pass, B's count
    its own."""
    for route in ENRICHER_ROUTES:
        await routes.passes(route, USER_A)
    await routes.passes("probe", USER_A)
    await routes.refused("search", USER_A)

    await routes.passes("probe", USER_B)
    await routes.passes("search", USER_B)
    assert (limiter.count(USER_A.id), limiter.count(USER_B.id)) == (LIMIT, 2)


@pytest.mark.asyncio
async def test_the_routes_count_on_the_limiter_the_setting_built(monkeypatch, built_on_fake_clock, routes):
    """Red: through the real ``probe_limiter()``, with ``LIBREFOLIO_PROBE_RATE_LIMIT=2``: one probe and one search pass,
    the next recognize is refused with ``retry_after`` 60 — and ONE limiter of 2 per 60 s was built for them all, two hits
    on it: the same mechanism and the same count, no limiter of the enrichers' own."""
    monkeypatch.setenv(PROBE_LIMIT_VARIABLE, "2")

    await routes.passes("probe", USER_A)
    await routes.passes("search", USER_A)
    refused = await routes.refused("recognize", USER_A)
    assert refused.detail["retry_after"] == PROBE_WINDOW
    assert [(built.limit, built.window_seconds, built.count(USER_A.id)) for built in built_on_fake_clock] == [(2, PROBE_WINDOW, 2)], f"built {built_on_fake_clock}"


# ============================================================================
# Not limited: the limit off, and refresh
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ENRICHER_ROUTES)
async def test_with_the_limiter_off_no_route_limits(monkeypatch, routes, route):
    """Guard: with ``probe_limiter()`` answering None (``LIBREFOLIO_PROBE_RATE_LIMIT=0``) the route limits nothing: 40
    calls of one user — past the default 30 — all pass."""
    monkeypatch.setattr(providers, "probe_limiter", lambda: None, raising=True)
    for _ in range(OFF_CALLS):
        await routes.passes(route, USER_A)


@pytest.mark.asyncio
async def test_with_the_setting_at_0_nothing_is_built_and_nothing_refused(monkeypatch, built_on_fake_clock, routes):
    """Guard: with ``LIBREFOLIO_PROBE_RATE_LIMIT=0`` and the real ``probe_limiter()``, 40 calls of each of the five
    routes by one user all pass and no limiter is built."""
    monkeypatch.setenv(PROBE_LIMIT_VARIABLE, "0")
    for route in (*ENRICHER_ROUTES, "probe"):
        for _ in range(OFF_CALLS):
            await routes.passes(route, USER_A)
    assert built_on_fake_clock == []


@pytest.mark.asyncio
async def test_refresh_is_not_limited(limiter, routes):
    """Guard: «Aggiorna» (``POST /assets/profile/refresh``) reads the bindings already saved and is not limited: it never
    counts a hit, and a user whose limit is used up by probes still refreshes, past ``LIMIT`` calls."""
    for _ in range(LIMIT + 2):
        await routes.passes("refresh", USER_A)
    assert limiter.count(USER_A.id) == 0

    for _ in range(LIMIT):
        await routes.passes("probe", USER_A)
    await routes.refused("probe", USER_A)
    for _ in range(LIMIT + 2):
        await routes.passes("refresh", USER_A)
    assert routes.reached("refresh") == 2 * (LIMIT + 2)
    assert limiter.count(USER_A.id) == LIMIT

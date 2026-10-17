"""``backend.app.services.platform.sleep_wake.activity``: the process's record of the user's presence and of the work
in progress (plan phase01SleepWake §Z2a, decision D-S1, lot Z2a).

An idle monitor (lot Z2b) will read it to suspend a Fly machine after N idle minutes when nothing is busy, and the
scheduler's catch-up (lot Z3) to run on the first request after a silence. Every HTTP request counts as the user's
presence except the probes and ``wake-sync``. The contract pinned here:

(a) ``PROBE_PATHS`` holds ``/system/health``, ``/system/ready`` and ``/system/test-lane-health``, ``WAKE_PATHS`` holds
    ``/system/wake-sync``, all under ``API_V1_PREFIX``; both are frozensets. ``request_kind(path)`` ignores trailing
    slashes, then matches exactly, case included: ``"probe"``, ``"wake"``, anything else ``"user"`` — ``/``, the site,
    the docs, an unknown path, and every near miss: ``/system/healthz``, ``/system/health/extra``,
    ``/system/wake-sync/x``, a probe without the prefix or in another case.
(b) ``Activity(*, clock=time.time)``: every timestamp comes from ``clock``, the wall clock by default — a suspend must
    count as silence —; ``started_at`` is ``clock()`` at construction; ``in_flight`` (0) and ``last_user_request_at``
    (None) are read-only properties.
(c) ``request(presence=True)``, a sync context manager. Entering counts the request in ``in_flight``; with presence the
    silence, ``idle_seconds(now)``, is read before ``last_user_request_at = now`` is stamped, then every return listener
    whose ``after_seconds`` is at most the silence is called with it, a float, in registration order, on the calling
    thread, before the body.
(d) Leaving it — normally, by an exception, by a ``BaseException`` such as ``CancelledError`` or ``KeyboardInterrupt`` —
    takes the request out of ``in_flight`` and, with presence, stamps ``last_user_request_at = clock()`` again; the
    exception propagates unchanged.
(e) ``presence=False`` counts the request in ``in_flight`` and does nothing else: no stamp, no listener. Requests nest
    and overlap, and end in any order: ``in_flight`` counts every one still open.
(f) Return listeners: one raising an ``Exception`` is logged — WARNING, "Return listener failed", ``listener=<name>`` —
    and the next ones and the body still run; each has its own threshold; a name registered again replaces its callback
    and its threshold. ``remove_return_listener(name)`` removes the listener of that name: it is never called again, the
    others still are, and the name can be registered anew; a name never registered, or already removed, is no error and
    returns None; an empty or blank name is a ``ValueError``, and nothing is removed.
(g) ``idle_seconds(now=None)``: ``now`` — ``clock()`` when None — less the last user request's stamp, or ``started_at``
    before any; never below 0.0, even when the clock goes back.
(h) ``busy(reason)``: a sync context manager, nestable, usable from any thread; ``reason`` is listed while at least one
    span of it is open, whichever thread opened it; an exception going through propagates and closes the span. An
    empty or blank ``reason`` is a ``ValueError`` before anything is counted.
(i) ``register_busy_check(name, check)``: a blank name is a ``ValueError``; a name registered again replaces its check.
    The check runs at every ``busy_reasons()``, never cached: truthy lists ``name``, falsy does not; an ``Exception``
    lists it too — when in doubt, not idle — and is logged — WARNING, "Busy check failed", ``check=<name>`` — at the
    first failure of a streak only: one answer without an exception, true or false, ends the streak. Each check has a
    streak of its own.
(j) ``busy_reasons()``: a tuple of str, no reason twice — ``"requests"`` while ``in_flight > 0``, wake requests
    included; every open ``busy()`` reason; every check truthy or raising —; empty at rest; its order is not part of the
    contract.
(k) Thread safety: threads opening and closing requests and busy spans together never find their own open span
    missing, and leave ``in_flight`` at 0 and ``busy_reasons()`` empty.
(l) ``ACTIVITY`` is the process's ``Activity``; ``current_activity()`` returns the module's ``ACTIVITY`` as it is at the
    call, so ``monkeypatch.setattr`` replaces it.
(m) ``ActivityMiddleware(app, *, activity=None)``, pure ASGI. A scope other than ``http`` reaches the app as it came and
    touches nothing; a probe passes uncounted; ``wake-sync`` is in flight without presence; any other path — one the
    router answers 404 included — is presence, its listeners run before the app, and it stays in flight until the app
    returns: through the last chunk of a streaming response and its background tasks, the end stamped after them. An
    exception or a cancellation goes through unchanged and leaves the count. Without ``activity`` the middleware reads
    ``current_activity()`` at each request.
(n) ``MIDDLEWARE_STACK`` starts with ``activity``, ``ActivityMiddleware`` without options — the outermost entry, which
    sees every request first and counts the compression of a response as in flight —; ``install_middleware`` makes it
    ``app.user_middleware[0]``.
(o) Response headers (lot Z5, «Aggiornamento prezzi…», N-Z5-5): ``register_response_header(name, provider)`` replaces a
    provider of the same name, the name's case ignored; ``remove_response_header(name)`` removes it, and is a no-op for
    a name never registered; ``response_headers()`` is a tuple of ``(name, value)``, one for each provider whose answer
    *now* is a non-empty str, in registration order — None, "" or a non-str gives nothing, and a provider that raises is
    skipped and logged while the others still answer. ``ActivityMiddleware`` adds them to the answer of every HTTP
    request whose path starts with ``/api/`` and that is not a probe, on ``http.response.start`` — read then, not at the
    request's start —, the name lower-cased and the value in latin-1, unless the answer already has a header of that
    name (the app's value wins); a streaming answer gets them once, on its single start message. A probe, and any path
    outside ``/api/`` (the site, the docs), get none.

Pure: no database, no server, no lane port, no network. Every ``Activity`` under test is the test's own, on a fake clock
that moves only when the test sets it; an autouse fixture puts a decoy in place of the process's ``ACTIVITY``, which is
otherwise replaced only through ``monkeypatch``. The middleware runs in FastAPI apps built here and served in this
process by ``httpx.ASGITransport``, or is called directly with a fake inner app; ``backend.app.main`` is never imported.
Threads meet on barriers and events with bounded timeouts and are joined within a deadline; nothing sleeps, and no
assertion depends on a duration. The listeners that read the activity run in a worker thread joined within a deadline,
so that a lock held around the listeners fails a test instead of hanging the run. The log is read with
``structlog.testing.capture_logs`` behind a barrier: a canary logged through the module's own ``logger`` must reach the
capture, or "nothing was logged" would prove nothing.

Red until ``backend/app/services/platform/sleep_wake/activity.py`` exists: the module does not import. Then (n) stays
red until ``MIDDLEWARE_STACK`` starts with the activity entry. The removal of (f), SWA-038…040, stays red until
``Activity.remove_return_listener`` exists (lot Z3). The response headers of (o), SWA-041…050, stay red until
``Activity.register_response_header`` exists and ``ActivityMiddleware`` adds them (lot Z5): an ``AttributeError`` per
case, then a missing header on the answers.
"""

from __future__ import annotations

import asyncio
import sys
import threading
import time
from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import contextmanager
from typing import Any, get_args

import httpx
import pytest
from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.responses import PlainTextResponse, StreamingResponse
from structlog.testing import capture_logs

from backend.app.config import API_V1_PREFIX
from backend.app.services.platform.middleware import MIDDLEWARE_STACK, install_middleware
from backend.app.services.platform.sleep_wake import activity as activity_module
from backend.app.services.platform.sleep_wake.activity import (
    PROBE_PATHS,
    WAKE_PATHS,
    Activity,
    ActivityMiddleware,
    RequestKind,
    current_activity,
    request_kind,
)
from backend.test_scripts.test_utils import print_section, print_success

#: Composed here from the imported prefix, never read from the module under test.
HEALTH = f"{API_V1_PREFIX}/system/health"
READY = f"{API_V1_PREFIX}/system/ready"
LANE_HEALTH = f"{API_V1_PREFIX}/system/test-lane-health"
WAKE_SYNC = f"{API_V1_PREFIX}/system/wake-sync"
EXPECTED_PROBE_PATHS = frozenset({HEALTH, READY, LANE_HEALTH})
EXPECTED_WAKE_PATHS = frozenset({WAKE_SYNC})
#: A route of the test apps that is neither a probe nor wake-sync: the user's.
USER_ROUTE = "/x"
#: Every path the test app answers with its plain handler: the probes and wake-sync, one of each with a trailing slash
#: too, and the user's route.
OBSERVED_PATHS = (HEALTH, READY, LANE_HEALTH, f"{READY}/", WAKE_SYNC, f"{WAKE_SYNC}/", USER_ROUTE)

START = 1_000.0
DECOY_START = 9_000.0
#: How far the clock moves while a handler runs, and while the tail of a response runs: the end of a streaming body, a
#: background task.
HANDLER_SECONDS = 20.0
TAIL_SECONDS = 30.0
STREAM_CHUNKS = 3

THREADS = 8
CYCLES = 400
SHARED_REASON = "shared"
#: The longest a test waits for a thread of its own: a barrier, an event, a join.
THREAD_WAIT_SECONDS = 30.0
#: The interpreter's thread switch interval during the concurrency test, instead of 5 ms: a race shows up.
SWITCH_INTERVAL_SECONDS = 1e-5

LOG_CANARY = "sleep-wake activity test: canary through the module's logger"
LISTENER_FAILED = "Return listener failed"
CHECK_FAILED = "Busy check failed"

#: What the module ships with, read at import, before the autouse fixture replaces it.
SHIPPED_ACTIVITY = getattr(activity_module, "ACTIVITY", None)

REQUEST_KINDS = [
    pytest.param(HEALTH, "probe", id="health"),
    pytest.param(READY, "probe", id="ready"),
    pytest.param(LANE_HEALTH, "probe", id="test-lane-health"),
    pytest.param(WAKE_SYNC, "wake", id="wake-sync"),
    # Trailing slashes, one or more, are ignored.
    pytest.param(f"{HEALTH}/", "probe", id="health-one-trailing-slash"),
    pytest.param(f"{HEALTH}//", "probe", id="health-two-trailing-slashes"),
    pytest.param(f"{LANE_HEALTH}/", "probe", id="test-lane-health-trailing-slash"),
    pytest.param(f"{WAKE_SYNC}/", "wake", id="wake-sync-one-trailing-slash"),
    pytest.param(f"{WAKE_SYNC}///", "wake", id="wake-sync-three-trailing-slashes"),
    # Everything else is the user: the root, the SPA, the docs, the chunks, the rest of the API, an unknown path...
    pytest.param("/", "user", id="root"),
    pytest.param("/assets/1", "user", id="spa-page"),
    pytest.param("/mkdocs/x", "user", id="docs"),
    pytest.param("/_app/x.js", "user", id="chunk"),
    pytest.param(f"{API_V1_PREFIX}/system/info", "user", id="system-info"),
    pytest.param("/no/such/path", "user", id="unknown"),
    # ...and every near miss: a longer name, a path below, another case, no prefix.
    pytest.param(f"{API_V1_PREFIX}/system/healthz", "user", id="healthz"),
    pytest.param(f"{HEALTH}/extra", "user", id="below-health"),
    pytest.param(f"{WAKE_SYNC}/x", "user", id="below-wake-sync"),
    pytest.param("/API/v1/system/health", "user", id="prefix-in-another-case"),
    pytest.param(f"{API_V1_PREFIX}/system/Health", "user", id="name-in-another-case"),
    pytest.param("/system/health", "user", id="without-the-prefix"),
]

PROBE_REQUESTS = [
    pytest.param(HEALTH, id="health"),
    pytest.param(READY, id="ready"),
    pytest.param(LANE_HEALTH, id="test-lane-health"),
    pytest.param(f"{READY}/", id="ready-with-a-trailing-slash"),
]
WAKE_REQUESTS = [pytest.param(WAKE_SYNC, id="wake-sync"), pytest.param(f"{WAKE_SYNC}/", id="wake-sync-with-a-trailing-slash")]
#: ``(path, status, where the app records it)``: a route, or a path the router answers 404 through the app's handler.
USER_REQUESTS = [
    pytest.param(USER_ROUTE, 200, "handler", id="a-route"),
    pytest.param("/no-such-route", 404, "not-found", id="an-unknown-path"),
    pytest.param(f"{API_V1_PREFIX}/system/healthz", 404, "not-found", id="near-a-probe"),
    pytest.param(f"{HEALTH}/extra", 404, "not-found", id="below-a-probe"),
    pytest.param(f"{WAKE_SYNC}/x", 404, "not-found", id="below-wake-sync"),
]


# =============================================================================
# HELPERS
# =============================================================================


class FakeClock:
    """A clock that moves only when the test sets it: ``clock.now = …``."""

    def __init__(self, start: float = START) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now


class Answers:
    """A busy check answering what the test puts in ``answer``: a value, or an exception to raise. ``calls`` counts its runs."""

    def __init__(self, answer: object = False) -> None:
        self.answer = answer
        self.calls = 0

    def __call__(self) -> object:
        self.calls += 1
        if isinstance(self.answer, BaseException):
            raise self.answer
        return self.answer


class Observed:
    """What the test app reads and writes: the activity under test, its clock, and what the app saw, in order."""

    def __init__(self, activity: Activity, clock: FakeClock) -> None:
        self.activity = activity
        self.clock = clock
        self.seen: list[tuple[Any, ...]] = []

    def record(self, where: str, detail: object) -> None:
        """``(where, detail, in_flight, last_user_request_at)``, as the activity reads at this moment."""
        self.seen.append((where, detail, self.activity.in_flight, self.activity.last_user_request_at))

    def listener(self, silence: float) -> None:
        """A return listener: it records that it ran, with the silence it was given, and reads nothing."""
        self.seen.append(("listener", silence))


@pytest.fixture(autouse=True)
def decoy(monkeypatch: pytest.MonkeyPatch) -> Activity:
    """A private ``Activity`` in place of the process's ``ACTIVITY`` for every test: none counts on the shipped instance, and a middleware given its own ``activity`` must leave this one untouched."""
    replacement = Activity(clock=FakeClock(DECOY_START))
    monkeypatch.setattr(activity_module, "ACTIVITY", replacement)
    return replacement


@pytest.fixture
def frequent_thread_switches() -> Iterator[None]:
    """The interpreter hands the GIL over every 10 µs instead of every 5 ms while the test runs, then as before."""
    previous = sys.getswitchinterval()
    sys.setswitchinterval(SWITCH_INTERVAL_SECONDS)
    try:
        yield
    finally:
        sys.setswitchinterval(previous)


def _activity(start: float = START) -> tuple[Activity, FakeClock]:
    """An ``Activity`` of the test's own, on a fake clock standing at ``start``."""
    clock = FakeClock(start)
    return Activity(clock=clock), clock


def _user_request(activity: Activity) -> None:
    """One user request whose body moves no clock: stamped at the clock's time, at its start and at its end."""
    with activity.request():
        pass


@contextmanager
def _activity_log() -> Iterator[list[dict[str, Any]]]:
    """What the module logs inside the block, behind a barrier: a canary logged through its own logger must arrive first."""
    with capture_logs() as events:
        activity_module.logger.debug(LOG_CANARY)
        assert any(event.get("event") == LOG_CANARY for event in events), f"barrier: the module's logger does not reach capture_logs, so what this test reads of the log proves nothing: {events}"
        yield events


def _logged(events: list[dict[str, Any]], event: str, key: str) -> list[tuple[Any, Any]]:
    """``(<key>, level)`` of every captured ``event``, in order."""
    return [(entry.get(key), entry.get("log_level")) for entry in events if entry.get("event") == event]


def _join(threads: list[threading.Thread], seconds: float = THREAD_WAIT_SECONDS) -> None:
    """Every thread of ``threads`` ends within ``seconds``: a deadlock fails the test instead of hanging the run."""
    deadline = time.monotonic() + seconds
    for thread in threads:
        thread.join(max(0.0, deadline - time.monotonic()))
    assert not [thread.name for thread in threads if thread.is_alive()], f"still running after {seconds} s, a deadlock? {threads}"


def _run_in_a_thread(target: Callable[[], None], name: str) -> int:
    """``target`` run to its end in a daemon thread of its own, joined within the deadline; what it raised is raised here. Returns the thread's ident."""
    raised: list[Exception] = []

    def run() -> None:
        try:
            target()
        except Exception as exc:  # handed over to the test's thread below
            raised.append(exc)

    thread = threading.Thread(target=run, name=name, daemon=True)
    thread.start()
    _join([thread])
    if raised:
        raise raised[0]
    assert thread.ident is not None
    return thread.ident


def _client(app: Any, *, raise_app_exceptions: bool = True) -> httpx.AsyncClient:
    """A client of ``app`` served in this process: no socket, no port."""
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app, raise_app_exceptions=raise_app_exceptions), base_url="http://testserver")


def _http_scope(path: str) -> dict[str, Any]:
    """The scope of ``GET path`` as a server hands it to the app."""
    return {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.4"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "root_path": "",
        "query_string": b"",
        "headers": [(b"host", b"testserver")],
        "client": ("127.0.0.1", 50000),
        "server": ("testserver", 80),
    }


def _non_http_scope(kind: str) -> dict[str, Any]:
    """A ``lifespan`` scope, or a ``websocket`` one on the user's route: neither is an HTTP request."""
    if kind == "lifespan":
        return {"type": "lifespan", "asgi": {"version": "3.0", "spec_version": "2.0"}, "state": {}}
    return {
        "type": "websocket",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "scheme": "ws",
        "path": USER_ROUTE,
        "raw_path": USER_ROUTE.encode(),
        "root_path": "",
        "query_string": b"",
        "headers": [(b"host", b"testserver")],
        "client": ("127.0.0.1", 50000),
        "server": ("testserver", 80),
        "subprotocols": [],
    }


async def _receive() -> dict[str, Any]:
    return {"type": "http.request", "body": b"", "more_body": False}


async def _send(message: dict[str, Any]) -> None:
    """Swallows what the app sends: a direct call looks at the activity, not at the response."""


def _observed(request: Request) -> Observed:
    return request.app.state.observed


async def _handler(request: Request) -> PlainTextResponse:
    observed = _observed(request)
    observed.record("handler", request.url.path)
    observed.clock.now += HANDLER_SECONDS
    return PlainTextResponse("ok")


async def _not_found(request: Request, exc: Exception) -> PlainTextResponse:
    """The app's answer to a path no route serves: the router raises a 404, and this handler is the app answering it."""
    observed = _observed(request)
    observed.record("not-found", request.url.path)
    observed.clock.now += HANDLER_SECONDS
    return PlainTextResponse("not found", status_code=404)


async def _chunks(observed: Observed) -> AsyncIterator[str]:
    for index in range(STREAM_CHUNKS):
        observed.record("chunk", index)
        yield f"chunk-{index}\n"
    observed.record("after-the-last-chunk", STREAM_CHUNKS)
    observed.clock.now += TAIL_SECONDS


async def _stream(request: Request) -> StreamingResponse:
    return StreamingResponse(_chunks(_observed(request)), media_type="text/plain")


async def _after_the_response(observed: Observed) -> None:
    observed.record("task", "/background")
    observed.clock.now += TAIL_SECONDS


async def _background(request: Request, tasks: BackgroundTasks) -> PlainTextResponse:
    observed = _observed(request)
    observed.record("handler", request.url.path)
    observed.clock.now += HANDLER_SECONDS
    tasks.add_task(_after_the_response, observed)
    return PlainTextResponse("accepted")


async def _broken(request: Request) -> PlainTextResponse:
    observed = _observed(request)
    observed.record("handler", request.url.path)
    observed.clock.now += HANDLER_SECONDS
    raise RuntimeError("provoked: the handler fails")


def _observed_app(observed: Observed) -> FastAPI:
    """A small app reading ``observed.activity`` from inside, with ``ActivityMiddleware`` added on that activity.

    ``OBSERVED_PATHS`` answer 200, ``/stream`` streams ``STREAM_CHUNKS`` chunks, ``/background`` runs a background task
    after its response, ``/raise`` raises, and any other path is answered 404 by the app's handler. Each records what the
    activity reads in ``observed.seen``; a handler moves the clock on by ``HANDLER_SECONDS``, the end of the streaming
    body and the background task by ``TAIL_SECONDS``.
    """
    app = FastAPI()
    app.state.observed = observed
    for path in OBSERVED_PATHS:
        app.add_api_route(path, _handler, methods=["GET"])
    app.add_api_route("/stream", _stream, methods=["GET"])
    app.add_api_route("/background", _background, methods=["GET"])
    app.add_api_route("/raise", _broken, methods=["GET"])
    app.add_exception_handler(404, _not_found)
    app.add_middleware(ActivityMiddleware, activity=observed.activity)
    return app


# =============================================================================
# (a) THE KIND OF A REQUEST
# =============================================================================


def test_the_probe_and_wake_paths_are_built_on_the_api_prefix() -> None:
    """SWA-001 — contract (a): ``PROBE_PATHS`` is health, ready and test-lane-health, ``WAKE_PATHS`` is wake-sync, all under ``API_V1_PREFIX``, both frozensets; a ``RequestKind`` is ``"probe"``, ``"wake"`` or ``"user"``."""
    print_section("SWA-001: PROBE_PATHS, WAKE_PATHS, RequestKind")

    assert isinstance(PROBE_PATHS, frozenset)
    assert PROBE_PATHS == EXPECTED_PROBE_PATHS
    assert isinstance(WAKE_PATHS, frozenset)
    assert WAKE_PATHS == EXPECTED_WAKE_PATHS
    assert set(get_args(getattr(RequestKind, "__value__", RequestKind))) == {"probe", "wake", "user"}
    print_success(f"{len(PROBE_PATHS)} probes and wake-sync under {API_V1_PREFIX}")


@pytest.mark.parametrize(("path", "kind"), REQUEST_KINDS)
def test_request_kind_ignores_trailing_slashes_then_matches_exactly(path: str, kind: str) -> None:
    """SWA-002 — contract (a): the probes and wake-sync, with or without trailing slashes, are ``"probe"`` and ``"wake"``; the root, the site, the docs, the chunks, the rest of the API, an unknown path and every near miss — a longer name, a path below, another case, no prefix — are ``"user"``."""
    print_section(f"SWA-002: request_kind({path!r})")

    assert request_kind(path) == kind
    print_success(kind)


# =============================================================================
# (b) A NEW ACTIVITY AND ITS CLOCK
# =============================================================================


def test_a_new_activity_starts_at_its_clock_with_nothing_in_flight_or_busy() -> None:
    """SWA-003 — contract (b): ``started_at`` is the clock's time at construction, kept when the clock moves on; nothing in flight, no user request, nothing busy, idle for 0 s at the start."""
    print_section("SWA-003: a new Activity")
    activity, clock = _activity()
    clock.now = 1_234.0

    assert activity.started_at == START
    assert (activity.in_flight, activity.last_user_request_at) == (0, None)
    assert activity.busy_reasons() == ()
    assert activity.idle_seconds(START) == 0.0
    print_success(f"started at {START}, idle and empty")


@pytest.mark.parametrize("attribute", ["in_flight", "last_user_request_at"])
def test_in_flight_and_the_last_user_request_are_read_only(attribute: str) -> None:
    """SWA-004 — contract (b): neither can be assigned: only the requests change them."""
    print_section(f"SWA-004: Activity.{attribute} is read-only")
    activity, _ = _activity()

    with pytest.raises(AttributeError):
        setattr(activity, attribute, 5)
    assert (activity.in_flight, activity.last_user_request_at) == (0, None)
    print_success("AttributeError")


def test_by_default_every_timestamp_is_the_wall_clock() -> None:
    """SWA-005 — contract (b): without a clock, ``started_at`` and the stamps of a user request are ``time.time()``'s: the time a machine spends suspended counts as silence, where a monotonic clock may stand still."""
    print_section("SWA-005: Activity() on the wall clock")

    before = time.time()
    activity = Activity()
    after = time.time()
    assert before <= activity.started_at <= after

    before = time.time()
    _user_request(activity)
    after = time.time()
    assert activity.last_user_request_at is not None
    assert before <= activity.last_user_request_at <= after
    print_success("time.time()")


# =============================================================================
# (c)-(e) REQUESTS
# =============================================================================


def test_a_user_request_is_in_flight_and_stamped_when_it_starts_and_when_it_ends() -> None:
    """SWA-006 — contracts (c), (d) and (j): the block gets None; inside it the request is in flight, "requests" is busy and the stamp is the start's time, 1100; after it nothing is in flight or busy and the stamp is the end's time, 1130."""
    print_section("SWA-006: request(), presence")
    activity, clock = _activity()
    clock.now = 1_100.0
    inside: list[tuple[Any, ...]] = []

    with activity.request() as entered:
        inside.append((entered, activity.in_flight, activity.last_user_request_at, activity.busy_reasons()))
        clock.now = 1_130.0

    assert inside == [(None, 1, 1_100.0, ("requests",))]
    assert (activity.in_flight, activity.last_user_request_at) == (0, 1_130.0)
    assert activity.busy_reasons() == ()
    print_success("in flight inside; stamped at 1100, then 1130")


def test_a_request_without_presence_is_in_flight_and_nothing_else() -> None:
    """SWA-007 — contract (e): ``presence=False`` — a wake request — is in flight and busy, and that is all: no stamp, no listener; the silence still runs from the start."""
    print_section("SWA-007: request(presence=False)")
    activity, clock = _activity()
    calls: list[float] = []
    activity.register_return_listener("catch-up", 0.0, calls.append)
    clock.now = 1_100.0
    inside: list[tuple[Any, ...]] = []

    with activity.request(presence=False):
        inside.append((activity.in_flight, activity.last_user_request_at, set(activity.busy_reasons())))
        clock.now = 1_150.0

    assert inside == [(1, None, {"requests"})]
    assert (activity.in_flight, activity.last_user_request_at, calls) == (0, None, [])
    assert activity.idle_seconds() == 150.0
    print_success("in flight, never stamped, no listener")


def test_requests_nest_and_overlap_and_end_in_any_order() -> None:
    """SWA-008 — contract (e): two requests open count 2, nested or overlapping as two concurrent requests do; when the first one opened ends first, 1 is left, then 0."""
    print_section("SWA-008: nested and overlapping requests")
    activity, _ = _activity()
    counts: list[int] = []

    with activity.request():
        with activity.request(presence=False):
            counts.append(activity.in_flight)
        counts.append(activity.in_flight)
    counts.append(activity.in_flight)

    first, second = activity.request(), activity.request(presence=False)
    first.__enter__()
    second.__enter__()
    counts.append(activity.in_flight)
    first.__exit__(None, None, None)
    counts.append(activity.in_flight)
    second.__exit__(None, None, None)
    counts.append(activity.in_flight)

    assert counts == [2, 1, 0, 2, 1, 0]
    print_success("2, 1, 0 both ways")


@pytest.mark.parametrize("presence", [True, False], ids=["presence", "no-presence"])
@pytest.mark.parametrize("failure_type", [RuntimeError, asyncio.CancelledError, KeyboardInterrupt])
def test_a_request_left_by_an_exception_propagates_it_and_leaves_the_count(failure_type: type[BaseException], presence: bool) -> None:
    """SWA-009 — contract (d): an exception, a cancellation or an interrupt inside the request goes through unchanged; the request is out of ``in_flight``, and with presence its end is stamped all the same."""
    print_section(f"SWA-009: {failure_type.__name__} through request(presence={presence})")
    activity, clock = _activity()
    clock.now = 1_100.0
    failure = failure_type("provoked: the body fails")

    with pytest.raises(failure_type) as caught:
        with activity.request(presence=presence):
            clock.now = 1_130.0
            raise failure

    assert caught.value is failure
    assert activity.in_flight == 0
    assert activity.last_user_request_at == (1_130.0 if presence else None)
    assert activity.busy_reasons() == ()
    print_success("propagated; out of flight" + (", end stamped" if presence else ""))


# =============================================================================
# (c), (f) RETURN LISTENERS
# =============================================================================


def test_listeners_at_or_below_the_silence_run_in_order_on_the_calling_thread_before_the_body() -> None:
    """SWA-010 — contracts (c) and (f): the first user request comes at 1300, 300 s after the start. The listeners of 300 s — the silence itself —, 0 s and 120 s are called with 300.0, a float, in their order of registration, and the one of 301 s is not; each finds the request already counted and stamped, on the thread that entered the request — a worker here —, before the body. Nothing is logged.

    The request runs in a worker thread joined within a deadline: a listener reading the activity while a lock the
    request holds is still taken fails the test instead of hanging the run.
    """
    print_section("SWA-010: return listeners, thresholds and order")
    activity, clock = _activity()
    seen: list[tuple[Any, ...]] = []

    def listener(name: str) -> Callable[[float], None]:
        def called(silence: float) -> None:
            seen.append((name, silence, type(silence), activity.in_flight, activity.last_user_request_at, threading.get_ident()))

        return called

    for name, after_seconds in (("at-the-silence", 300.0), ("above-it", 301.0), ("from-zero", 0.0), ("below-it", 120.0)):
        activity.register_return_listener(name, after_seconds, listener(name))
    clock.now = 1_300.0

    def enter() -> None:
        with activity.request():
            seen.append(("body", threading.get_ident()))

    with _activity_log() as events:
        worker = _run_in_a_thread(enter, "swa-listeners")

    assert seen == [
        ("at-the-silence", 300.0, float, 1, 1_300.0, worker),
        ("from-zero", 300.0, float, 1, 1_300.0, worker),
        ("below-it", 300.0, float, 1, 1_300.0, worker),
        ("body", worker),
    ]
    assert _logged(events, LISTENER_FAILED, "listener") == []
    print_success("300, 0 and 120 called with 300.0, in order, before the body; 301 not")


def test_the_silence_runs_from_the_start_then_from_the_end_of_the_last_user_request() -> None:
    """SWA-011 — contracts (c), (e) and (g): the first user request, at 1300, finds 300 s since the start; the next, at 1450, finds 90 s since the end of the first, stamped at 1360 — a request without presence at 1400 in between counts for nothing —; one at 1400 after the clock went back finds 0.0, which a listener of 0 s still receives."""
    print_section("SWA-011: the silence a listener receives")
    activity, clock = _activity()
    silences: list[float] = []
    activity.register_return_listener("catch-up", 0.0, silences.append)

    clock.now = 1_300.0
    with activity.request():
        clock.now = 1_360.0
    clock.now = 1_400.0
    with activity.request(presence=False):
        clock.now = 1_410.0
    clock.now = 1_450.0
    _user_request(activity)
    clock.now = 1_400.0
    _user_request(activity)

    assert silences == [300.0, 90.0, 0.0]
    print_success("300 from the start, 90 from the last end, 0 when the clock went back")


def test_a_listener_that_raises_is_logged_and_the_next_ones_and_the_body_still_run() -> None:
    """SWA-012 — contract (f): of three listeners the second raises: it is logged once — WARNING, "Return listener failed", ``listener="broken"`` —, the third and the body run, and the request ends as usual."""
    print_section("SWA-012: a listener that raises")
    activity, clock = _activity()
    ran: list[str] = []

    def broken(silence: float) -> None:
        ran.append("broken")
        raise RuntimeError("provoked: this listener fails")

    activity.register_return_listener("first", 0.0, lambda silence: ran.append("first"))
    activity.register_return_listener("broken", 0.0, broken)
    activity.register_return_listener("last", 0.0, lambda silence: ran.append("last"))
    clock.now = 1_300.0

    with _activity_log() as events:
        with activity.request():
            ran.append("body")
            clock.now = 1_310.0

    assert ran == ["first", "broken", "last", "body"]
    assert _logged(events, LISTENER_FAILED, "listener") == [("broken", "warning")]
    assert (activity.in_flight, activity.last_user_request_at) == (0, 1_310.0)
    print_success("logged once as a warning; the others and the body ran")


def test_registering_a_listener_name_again_replaces_its_callback_and_its_threshold() -> None:
    """SWA-013 — contract (f): "catch-up" registered twice is called once, through the second callback; registered again with 1000 s, a silence of 300 s no longer calls it, and one of 1000 s does."""
    print_section("SWA-013: a listener's name registered again")
    activity, clock = _activity()
    calls: list[tuple[str, float]] = []
    activity.register_return_listener("catch-up", 10.0, lambda silence: calls.append(("old", silence)))
    activity.register_return_listener("catch-up", 10.0, lambda silence: calls.append(("new", silence)))
    clock.now = 1_300.0
    _user_request(activity)
    assert calls == [("new", 300.0)]

    activity.register_return_listener("catch-up", 1_000.0, lambda silence: calls.append(("newer", silence)))
    clock.now = 1_600.0
    _user_request(activity)
    clock.now = 2_600.0
    _user_request(activity)

    assert calls == [("new", 300.0), ("newer", 1_000.0)]
    print_success("one call per request, the latest callback at the latest threshold")


# =============================================================================
# (g) IDLE SECONDS
# =============================================================================


def test_idle_seconds_counts_from_the_start_then_from_the_last_user_request_never_below_zero() -> None:
    """SWA-014 — contract (g): before any user request, from ``started_at``: 250 s at 1250 by the clock — ``now=None`` the same —, 400 s at a ``now`` of 1400 given, 0.0 before the start. After a request stamped at 1300, from it: 60 s at 1360, 0.0 at 1200, 90 s at 1390 by the clock, and 0.0 once the clock went back to 1100. Always a float."""
    print_section("SWA-014: idle_seconds")
    activity, clock = _activity()

    clock.now = 1_250.0
    readings = [activity.idle_seconds(), activity.idle_seconds(None), activity.idle_seconds(1_400.0), activity.idle_seconds(900.0)]
    clock.now = 1_300.0
    _user_request(activity)
    readings += [activity.idle_seconds(1_360.0), activity.idle_seconds(1_200.0)]
    clock.now = 1_390.0
    readings.append(activity.idle_seconds())
    clock.now = 1_100.0
    readings.append(activity.idle_seconds())

    assert readings == [250.0, 250.0, 400.0, 0.0, 60.0, 0.0, 90.0, 0.0]
    assert all(type(reading) is float for reading in readings), [type(reading) for reading in readings]
    print_success("from the start, then from the last user request; 0.0 at worst")


# =============================================================================
# (h) BUSY SPANS
# =============================================================================


def test_busy_lists_a_reason_while_one_of_its_spans_is_open() -> None:
    """SWA-015 — contract (h): ``busy("backup")`` gives the block None and lists "backup"; opened a second time, it stays listed — once — until both spans are closed; another reason beside it is listed too."""
    print_section("SWA-015: busy(), nested")
    activity, _ = _activity()
    seen: list[tuple[Any, ...]] = []

    with activity.busy("backup") as entered:
        seen.append((entered, activity.busy_reasons()))
        with activity.busy("backup"), activity.busy("export"):
            seen.append(("both", sorted(activity.busy_reasons())))
        seen.append(("outer", activity.busy_reasons()))
    seen.append(("closed", activity.busy_reasons()))

    assert seen == [(None, ("backup",)), ("both", ["backup", "export"]), ("outer", ("backup",)), ("closed", ())]
    print_success("listed until its last span is closed")


def test_busy_counts_the_spans_of_every_thread() -> None:
    """SWA-016 — contract (h): a span another thread opened is listed here; this thread's own span of the same reason, once closed, leaves it listed while the other one is open; closed there too, it is gone."""
    print_section("SWA-016: busy() across threads")
    activity, _ = _activity()
    opened, release = threading.Event(), threading.Event()

    def hold() -> None:
        with activity.busy("restore"):
            opened.set()
            release.wait(THREAD_WAIT_SECONDS)

    holder = threading.Thread(target=hold, name="swa-busy-holder", daemon=True)
    holder.start()
    try:
        assert opened.wait(THREAD_WAIT_SECONDS), "barrier: the holder never opened its span"
        assert activity.busy_reasons() == ("restore",)
        with activity.busy("restore"):
            assert activity.busy_reasons() == ("restore",)
        assert activity.busy_reasons() == ("restore",), "closing this thread's span closed the holder's too"
    finally:
        release.set()
        _join([holder])

    assert activity.busy_reasons() == ()
    print_success("one count per reason, whatever the thread")


@pytest.mark.parametrize("failure_type", [RuntimeError, asyncio.CancelledError])
def test_an_exception_through_busy_propagates_and_closes_the_span(failure_type: type[BaseException]) -> None:
    """SWA-017 — contract (h): an exception or a cancellation inside ``busy("export")`` goes through unchanged, and "export" is no longer listed."""
    print_section(f"SWA-017: {failure_type.__name__} through busy()")
    activity, _ = _activity()
    failure = failure_type("provoked: the job fails")

    with pytest.raises(failure_type) as caught:
        with activity.busy("export"):
            raise failure

    assert caught.value is failure
    assert activity.busy_reasons() == ()
    print_success("propagated; the span closed")


@pytest.mark.parametrize("reason", ["", " ", "\t\n "], ids=["empty", "a-space", "whitespace"])
def test_a_blank_busy_reason_is_refused_before_anything_is_counted(reason: str) -> None:
    """SWA-018 — contract (h): an empty or blank reason is a ``ValueError``, raised before the block runs and before anything is listed."""
    print_section(f"SWA-018: busy({reason!r})")
    activity, _ = _activity()
    ran: list[str] = []

    with pytest.raises(ValueError):
        with activity.busy(reason):
            ran.append(reason)

    assert ran == []
    assert activity.busy_reasons() == ()
    print_success("ValueError; nothing counted")


# =============================================================================
# (i) BUSY CHECKS
# =============================================================================


@pytest.mark.parametrize("name", ["", "   "], ids=["empty", "blank"])
def test_a_blank_busy_check_name_is_refused_and_nothing_is_registered(name: str) -> None:
    """SWA-019 — contract (i): an empty or blank name is a ``ValueError``, and its check — always true — is never read."""
    print_section(f"SWA-019: register_busy_check({name!r})")
    activity, _ = _activity()
    check = Answers(True)

    with pytest.raises(ValueError):
        activity.register_busy_check(name, check)

    assert activity.busy_reasons() == ()
    assert check.calls == 0
    print_success("ValueError; nothing registered")


@pytest.mark.parametrize(
    ("answer", "listed"),
    [
        pytest.param(True, True, id="True"),
        pytest.param(1, True, id="1"),
        pytest.param("yes", True, id="a-word"),
        pytest.param([0], True, id="a-non-empty-list"),
        pytest.param(False, False, id="False"),
        pytest.param(0, False, id="0"),
        pytest.param("", False, id="an-empty-string"),
        pytest.param(None, False, id="None"),
        pytest.param([], False, id="an-empty-list"),
    ],
)
def test_a_busy_check_lists_its_name_when_its_answer_is_truthy(answer: object, listed: bool) -> None:
    """SWA-020 — contract (i): a truthy answer lists the check's name, a falsy one does not; an answer is never logged."""
    print_section(f"SWA-020: a busy check answering {answer!r}")
    activity, _ = _activity()
    activity.register_busy_check("tools", Answers(answer))

    with _activity_log() as events:
        reasons = activity.busy_reasons()

    assert reasons == (("tools",) if listed else ())
    assert _logged(events, CHECK_FAILED, "check") == []
    print_success("listed" if listed else "not listed")


def test_a_busy_check_runs_at_every_reading_never_cached() -> None:
    """SWA-021 — contract (i): a check whose answer flips four times is read afresh by every ``busy_reasons()``: both readings after each flip follow the answer of the moment, and each of the eight readings runs the check."""
    print_section("SWA-021: a busy check is never cached")
    activity, _ = _activity()
    check = Answers()
    activity.register_busy_check("tools", check)
    trace: list[tuple[tuple[str, ...], tuple[str, ...]]] = []

    for answer in (True, False, True, False):
        check.answer = answer
        trace.append((activity.busy_reasons(), activity.busy_reasons()))

    assert trace == [(("tools",), ("tools",)), ((), ()), (("tools",), ("tools",)), ((), ())]
    assert check.calls == 2 * len(trace), f"{check.calls} runs of the check for {2 * len(trace)} readings: a reading answered without running it"
    print_success("each reading runs the check and follows the answer of the moment")


def test_registering_a_busy_check_name_again_replaces_the_check() -> None:
    """SWA-022 — contract (i): "tools" registered again with another check: only the new one is read from then on."""
    print_section("SWA-022: a busy check's name registered again")
    activity, _ = _activity()
    old, new = Answers(True), Answers(False)
    activity.register_busy_check("tools", old)
    assert activity.busy_reasons() == ("tools",)
    old_calls = old.calls

    activity.register_busy_check("tools", new)
    assert activity.busy_reasons() == ()
    new.answer = True
    assert activity.busy_reasons() == ("tools",)
    assert old.calls == old_calls, "the replaced check is still read"
    print_success("the new check alone")


def test_a_failing_busy_check_counts_as_busy_and_warns_once_per_streak() -> None:
    """SWA-023 — contract (i): a check that raises lists its name — when in doubt, not idle — and is logged — WARNING, "Busy check failed", ``check="flaky"`` — at the first failure of a streak only, however many readings the streak lasts; one answer without an exception, false or true, ends the streak, and the next failure warns again."""
    print_section("SWA-023: a failing busy check, its streaks")
    activity, _ = _activity()
    check = Answers()
    activity.register_busy_check("flaky", check)
    failure = RuntimeError("provoked: the check fails")
    steps = [
        # (answer, busy_reasons(), warnings logged so far)
        (failure, ("flaky",), 1),  # the first failure: logged
        (failure, ("flaky",), 1),  # the streak goes on: not again
        (failure, ("flaky",), 1),
        (False, (), 1),  # an answer ends the streak
        (failure, ("flaky",), 2),  # a new streak: logged
        (failure, ("flaky",), 2),
        (True, ("flaky",), 2),  # a true answer ends it too
        (failure, ("flaky",), 3),
    ]
    trace: list[tuple[tuple[str, ...], int]] = []

    with _activity_log() as events:
        for answer, _, _ in steps:
            check.answer = answer
            trace.append((activity.busy_reasons(), len(_logged(events, CHECK_FAILED, "check"))))

    assert trace == [(reasons, warnings) for _, reasons, warnings in steps]
    assert _logged(events, CHECK_FAILED, "check") == [("flaky", "warning")] * 3
    print_success("busy at every failure; three streaks, three warnings")


def test_each_busy_check_has_a_streak_of_its_own() -> None:
    """SWA-024 — contract (i): two checks failing together warn once each; while "b" goes on failing, "a" answers, then fails again: only "a" warns again."""
    print_section("SWA-024: one streak per busy check")
    activity, _ = _activity()
    failure = RuntimeError("provoked: the check fails")
    first, second = Answers(failure), Answers(failure)
    activity.register_busy_check("a", first)
    activity.register_busy_check("b", second)

    with _activity_log() as events:
        listed = [set(activity.busy_reasons()), set(activity.busy_reasons())]
        first.answer = False
        listed.append(set(activity.busy_reasons()))
        first.answer = failure
        listed.append(set(activity.busy_reasons()))

    assert listed == [{"a", "b"}, {"a", "b"}, {"b"}, {"a", "b"}]
    assert sorted(_logged(events, CHECK_FAILED, "check")) == [("a", "warning"), ("a", "warning"), ("b", "warning")]
    print_success("a twice, b once")


# =============================================================================
# (j) BUSY REASONS
# =============================================================================


def test_busy_reasons_lists_requests_spans_and_checks_each_once() -> None:
    """SWA-025 — contract (j): a request without presence, ``busy("backup")`` and ``busy("requests")``, a true check "backup", a failing check "export" and a false one "tools" give "requests", "backup" and "export", each once, a tuple of str; with the spans and the request closed, the two checks; with the checks answering false, nothing."""
    print_section("SWA-025: busy_reasons() without duplicates")
    activity, _ = _activity()
    backup, export = Answers(True), Answers(RuntimeError("provoked: the check fails"))
    activity.register_busy_check("backup", backup)
    activity.register_busy_check("export", export)
    activity.register_busy_check("tools", Answers(False))
    states: list[tuple[str, ...]] = []

    with _activity_log():
        with activity.busy("backup"), activity.busy("requests"), activity.request(presence=False):
            states.append(activity.busy_reasons())
        states.append(activity.busy_reasons())
        backup.answer = export.answer = False
        states.append(activity.busy_reasons())

    for reasons in states:
        assert isinstance(reasons, tuple) and all(isinstance(reason, str) for reason in reasons), reasons
        assert len(reasons) == len(set(reasons)), f"a reason listed twice: {reasons}"
    assert [set(reasons) for reasons in states] == [{"requests", "backup", "export"}, {"backup", "export"}, set()]
    print_success("each reason once, in a tuple of str; nothing at rest")


# =============================================================================
# (k) THREAD SAFETY
# =============================================================================


@pytest.mark.usefixtures("frequent_thread_switches")
def test_concurrent_requests_and_busy_spans_balance_out() -> None:
    """SWA-026 — contract (k): eight threads, released together, each open 400 times a span of its own, a span of a shared reason and a request — with presence one time in two —; inside, each finds its request in flight and its two reasons and "requests" listed. At the end nothing is in flight or busy, and the listener of 0 s was called once per request with presence."""
    print_section(f"SWA-026: {THREADS} threads × {CYCLES} cycles")
    activity, _ = _activity()
    calls: list[float] = []
    activity.register_return_listener("every-return", 0.0, calls.append)
    barrier = threading.Barrier(THREADS, timeout=THREAD_WAIT_SECONDS)
    problems: list[str] = []

    def work(own: str) -> None:
        try:
            barrier.wait()
            for cycle in range(CYCLES):
                with activity.busy(own), activity.busy(SHARED_REASON), activity.request(presence=cycle % 2 == 0):
                    in_flight, reasons = activity.in_flight, set(activity.busy_reasons())
                    if in_flight < 1 or not {own, SHARED_REASON, "requests"} <= reasons:
                        problems.append(f"{own}, cycle {cycle}: in_flight {in_flight}, reasons {sorted(reasons)}")
        except Exception as exc:  # handed over to the test's thread through problems
            problems.append(f"{own}: {exc!r}")

    threads = [threading.Thread(target=work, args=(f"worker-{index}",), name=f"swa-worker-{index}", daemon=True) for index in range(THREADS)]
    for thread in threads:
        thread.start()
    _join(threads)

    assert problems == [], problems[:10]
    assert (activity.in_flight, activity.busy_reasons()) == (0, ())
    assert len(calls) == THREADS * CYCLES // 2
    print_success(f"{THREADS * CYCLES} requests and {2 * THREADS * CYCLES} spans balanced")


# =============================================================================
# (l) THE PROCESS'S ACTIVITY
# =============================================================================


def test_current_activity_returns_the_module_attribute_at_each_call(monkeypatch: pytest.MonkeyPatch, decoy: Activity) -> None:
    """SWA-027 — contract (l): ``ACTIVITY`` as shipped is an ``Activity``; ``current_activity()`` returns whatever ``ACTIVITY`` is at the call — the fixture's decoy, another instance, the shipped one again."""
    print_section("SWA-027: ACTIVITY and current_activity()")

    assert isinstance(SHIPPED_ACTIVITY, Activity), f"ACTIVITY as shipped: {SHIPPED_ACTIVITY!r}"
    assert current_activity() is decoy
    other = Activity(clock=FakeClock())
    monkeypatch.setattr(activity_module, "ACTIVITY", other)
    assert current_activity() is other
    monkeypatch.setattr(activity_module, "ACTIVITY", SHIPPED_ACTIVITY)
    assert current_activity() is SHIPPED_ACTIVITY
    print_success("read at each call")


# =============================================================================
# (m) THE MIDDLEWARE
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["lifespan", "websocket"])
async def test_a_scope_other_than_http_reaches_the_app_as_it_came_and_touches_nothing(kind: str) -> None:
    """SWA-028 — contract (m): the inner app is called once, with the very scope, receive and send given — a websocket on the user's route included —, and finds nothing in flight; no stamp, no listener."""
    print_section(f"SWA-028: a {kind} scope")
    activity, clock = _activity()
    calls: list[float] = []
    activity.register_return_listener("catch-up", 0.0, calls.append)
    clock.now = 1_300.0
    scope = _non_http_scope(kind)
    reached: list[tuple[Any, ...]] = []

    async def inner(given_scope: dict[str, Any], given_receive: Any, given_send: Any) -> None:
        reached.append((given_scope is scope, given_receive is _receive, given_send is _send, activity.in_flight))

    await ActivityMiddleware(inner, activity=activity)(scope, _receive, _send)

    assert reached == [(True, True, True, 0)]
    assert (activity.in_flight, activity.last_user_request_at, calls) == (0, None, [])
    print_success("passed as it came; nothing counted")


@pytest.mark.asyncio
@pytest.mark.parametrize("path", PROBE_REQUESTS)
async def test_a_probe_passes_through_uncounted(path: str) -> None:
    """SWA-029 — contract (m): during a probe nothing is in flight; after it, the last user request is still the one stamped at 1100, and no listener was called."""
    print_section(f"SWA-029: GET {path}")
    activity, clock = _activity()
    clock.now = 1_100.0
    _user_request(activity)
    observed = Observed(activity, clock)
    activity.register_return_listener("catch-up", 0.0, observed.listener)
    clock.now = 1_500.0

    async with _client(_observed_app(observed)) as client:
        response = await client.get(path)

    assert response.status_code == 200
    assert observed.seen == [("handler", path, 0, 1_100.0)]
    assert (activity.in_flight, activity.last_user_request_at) == (0, 1_100.0)
    print_success("not in flight, not presence")


@pytest.mark.asyncio
@pytest.mark.parametrize("path", WAKE_REQUESTS)
async def test_wake_sync_is_in_flight_without_presence(path: str) -> None:
    """SWA-030 — contract (m): during ``wake-sync`` the request is in flight; the last user request stays the one stamped at 1100, and no listener is called."""
    print_section(f"SWA-030: GET {path}")
    activity, clock = _activity()
    clock.now = 1_100.0
    _user_request(activity)
    observed = Observed(activity, clock)
    activity.register_return_listener("catch-up", 0.0, observed.listener)
    clock.now = 1_500.0

    async with _client(_observed_app(observed)) as client:
        response = await client.get(path)

    assert response.status_code == 200
    assert observed.seen == [("handler", path, 1, 1_100.0)]
    assert (activity.in_flight, activity.last_user_request_at) == (0, 1_100.0)
    print_success("in flight, not presence")


@pytest.mark.asyncio
@pytest.mark.parametrize(("path", "status", "where"), USER_REQUESTS)
async def test_any_other_path_is_presence_and_in_flight_its_listeners_first(path: str, status: int, where: str, decoy: Activity) -> None:
    """SWA-031 — contract (m): the first request, at 1300, to a route or to a path the router answers 404: the listener of 60 s is called with 300.0 before the app runs; the app finds the request in flight and stamped at 1300; the end is stamped at 1320, once the app is done. The decoy in place of ``ACTIVITY`` is never touched."""
    print_section(f"SWA-031: GET {path}")
    activity, clock = _activity()
    observed = Observed(activity, clock)
    activity.register_return_listener("catch-up", 60.0, observed.listener)
    clock.now = 1_300.0

    async with _client(_observed_app(observed)) as client:
        response = await client.get(path)

    assert response.status_code == status
    assert observed.seen == [("listener", 300.0), (where, path, 1, 1_300.0)]
    assert (activity.in_flight, activity.last_user_request_at) == (0, 1_300.0 + HANDLER_SECONDS)
    assert (decoy.in_flight, decoy.last_user_request_at) == (0, None)
    print_success(f"{status}: presence, in flight, the listener first, stamped at both ends")


@pytest.mark.asyncio
async def test_a_streaming_response_is_in_flight_until_its_last_chunk() -> None:
    """SWA-032 — contract (m): every chunk, and the generator's end after the last one, find the request in flight and stamped at its start; once the client has the whole body nothing is in flight, and the end is stamped as the generator left the clock."""
    print_section("SWA-032: a streaming response")
    activity, clock = _activity()
    observed = Observed(activity, clock)
    clock.now = 1_300.0

    async with _client(_observed_app(observed)) as client:
        response = await client.get("/stream")

    assert response.status_code == 200
    assert response.text == "".join(f"chunk-{index}\n" for index in range(STREAM_CHUNKS))
    assert observed.seen == [*(("chunk", index, 1, 1_300.0) for index in range(STREAM_CHUNKS)), ("after-the-last-chunk", STREAM_CHUNKS, 1, 1_300.0)]
    assert (activity.in_flight, activity.last_user_request_at) == (0, 1_300.0 + TAIL_SECONDS)
    print_success(f"in flight through {STREAM_CHUNKS} chunks and the generator's end")


@pytest.mark.asyncio
async def test_a_background_task_runs_in_flight_and_the_end_is_stamped_after_it() -> None:
    """SWA-033 — contract (m): the handler, then its background task — run after the response was sent —, both find the request in flight and stamped at its start; the end is stamped once the task is done."""
    print_section("SWA-033: a background task")
    activity, clock = _activity()
    observed = Observed(activity, clock)
    clock.now = 1_300.0

    async with _client(_observed_app(observed)) as client:
        response = await client.get("/background")

    assert (response.status_code, response.text) == (200, "accepted")
    assert observed.seen == [("handler", "/background", 1, 1_300.0), ("task", "/background", 1, 1_300.0)]
    assert (activity.in_flight, activity.last_user_request_at) == (0, 1_300.0 + HANDLER_SECONDS + TAIL_SECONDS)
    print_success("the task in flight; the end stamped after it")


@pytest.mark.asyncio
async def test_a_handler_that_raises_ends_its_request_all_the_same() -> None:
    """SWA-034 — contract (m): the handler finds the request in flight; its exception goes through the middleware to the app's error middleware outside it, which answers 500; nothing is left in flight, and the end is stamped."""
    print_section("SWA-034: a handler that raises")
    activity, clock = _activity()
    observed = Observed(activity, clock)
    clock.now = 1_300.0

    async with _client(_observed_app(observed), raise_app_exceptions=False) as client:
        response = await client.get("/raise")

    assert response.status_code == 500
    assert observed.seen == [("handler", "/raise", 1, 1_300.0)]
    assert (activity.in_flight, activity.last_user_request_at) == (0, 1_300.0 + HANDLER_SECONDS)
    print_success("500; out of flight, end stamped")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "in_flight", "stamped"),
    [
        pytest.param(USER_ROUTE, 1, True, id="user"),
        pytest.param(WAKE_SYNC, 1, False, id="wake-sync"),
        pytest.param(HEALTH, 0, False, id="probe"),
    ],
)
@pytest.mark.parametrize("failure_type", [RuntimeError, asyncio.CancelledError])
async def test_an_exception_or_a_cancellation_in_the_app_goes_through_and_leaves_the_count(failure_type: type[BaseException], path: str, in_flight: int, stamped: bool) -> None:
    """SWA-035 — contract (m): the inner app raises, or is cancelled, during the request: the very exception comes out of the middleware, nothing is left in flight, and a user request has its end stamped."""
    print_section(f"SWA-035: {failure_type.__name__} in the app, GET {path}")
    activity, clock = _activity()
    clock.now = 1_300.0
    failure = failure_type("provoked: the app fails")
    inside: list[int] = []

    async def inner(scope: dict[str, Any], receive: Any, send: Any) -> None:
        inside.append(activity.in_flight)
        clock.now += HANDLER_SECONDS
        raise failure

    with pytest.raises(failure_type) as caught:
        await ActivityMiddleware(inner, activity=activity)(_http_scope(path), _receive, _send)

    assert caught.value is failure
    assert inside == [in_flight]
    assert (activity.in_flight, activity.last_user_request_at) == (0, (1_300.0 + HANDLER_SECONDS) if stamped else None)
    print_success("propagated unchanged; out of flight")


@pytest.mark.asyncio
async def test_without_an_activity_the_middleware_reads_current_activity_at_each_request(monkeypatch: pytest.MonkeyPatch, decoy: Activity) -> None:
    """SWA-036 — contract (m): added without ``activity``, the middleware counts the first request on the instance ``ACTIVITY`` is then, and the second — ``ACTIVITY`` replaced in between — on the new one, each stamped on its own clock; the decoy ``ACTIVITY`` was before either is never touched."""
    print_section("SWA-036: ActivityMiddleware without an activity")
    first, _ = _activity(1_000.0)
    second, _ = _activity(2_000.0)
    seen: list[tuple[int, int]] = []

    async def endpoint() -> PlainTextResponse:
        seen.append((first.in_flight, second.in_flight))
        return PlainTextResponse("ok")

    app = FastAPI()
    app.add_api_route(USER_ROUTE, endpoint, methods=["GET"])
    app.add_middleware(ActivityMiddleware)

    async with _client(app) as client:
        monkeypatch.setattr(activity_module, "ACTIVITY", first)
        assert (await client.get(USER_ROUTE)).status_code == 200
        monkeypatch.setattr(activity_module, "ACTIVITY", second)
        assert (await client.get(USER_ROUTE)).status_code == 200

    assert seen == [(1, 0), (0, 1)]
    assert (first.last_user_request_at, second.last_user_request_at) == (1_000.0, 2_000.0)
    assert (first.in_flight, second.in_flight) == (0, 0)
    assert (decoy.in_flight, decoy.last_user_request_at) == (0, None)
    print_success("each request on the ACTIVITY of its moment")


# =============================================================================
# (n) THE STACK
# =============================================================================


@pytest.mark.asyncio
async def test_the_activity_middleware_is_the_outermost_entry_of_the_stack(monkeypatch: pytest.MonkeyPatch) -> None:
    """SWA-037 — contract (n): ``MIDDLEWARE_STACK`` starts with "activity", ``ActivityMiddleware`` without options, and names it once; ``install_middleware`` makes it ``app.user_middleware[0]``, without arguments, and the app it builds counts a request on the ``ACTIVITY`` of the moment."""
    print_section("SWA-037: activity, the outermost entry of MIDDLEWARE_STACK")
    first = MIDDLEWARE_STACK[0]
    assert (first.name, first.cls, dict(first.options)) == ("activity", ActivityMiddleware, {})
    assert [entry.name for entry in MIDDLEWARE_STACK].count("activity") == 1

    app = FastAPI()
    install_middleware(app)
    outermost = app.user_middleware[0]
    assert (outermost.cls, outermost.args, outermost.kwargs) == (ActivityMiddleware, (), {})

    activity, clock = _activity()
    observed = Observed(activity, clock)
    monkeypatch.setattr(activity_module, "ACTIVITY", activity)
    app.state.observed = observed
    app.add_api_route(USER_ROUTE, _handler, methods=["GET"])
    clock.now = 1_300.0
    async with _client(app) as client:
        response = await client.get(USER_ROUTE)

    assert response.status_code == 200
    assert observed.seen == [("handler", USER_ROUTE, 1, 1_300.0)]
    assert (activity.in_flight, activity.last_user_request_at) == (0, 1_300.0 + HANDLER_SECONDS)
    print_success("first in the stack and in user_middleware; counting on current_activity()")


# =============================================================================
# (f) REMOVING A RETURN LISTENER (lot Z3)
# =============================================================================


def test_a_removed_listener_is_never_called_again_and_the_others_still_are() -> None:
    """SWA-038 — contract (f): "catch-up" — a listener that raises — and "other" are both called on a return. Once "catch-up" is removed — ``remove_return_listener`` returns None —, the next two returns call "other" alone and log nothing; registered anew, "catch-up" is called again."""
    print_section("SWA-038: remove_return_listener")
    activity, clock = _activity()
    calls: list[tuple[str, float]] = []

    def broken(silence: float) -> None:
        calls.append(("catch-up", silence))
        raise RuntimeError("provoked: this listener fails")

    activity.register_return_listener("catch-up", 60.0, broken)
    activity.register_return_listener("other", 0.0, lambda silence: calls.append(("other", silence)))
    clock.now = 1_300.0
    with _activity_log() as events:
        _user_request(activity)
    assert calls == [("catch-up", 300.0), ("other", 300.0)]
    assert _logged(events, LISTENER_FAILED, "listener") == [("catch-up", "warning")]

    assert activity.remove_return_listener("catch-up") is None
    with _activity_log() as events:
        clock.now = 1_600.0
        _user_request(activity)
        clock.now = 2_600.0
        _user_request(activity)
    assert calls[2:] == [("other", 300.0), ("other", 1_000.0)]
    assert _logged(events, LISTENER_FAILED, "listener") == []

    activity.register_return_listener("catch-up", 60.0, lambda silence: calls.append(("catch-up anew", silence)))
    clock.now = 2_700.0
    _user_request(activity)
    assert sorted(calls[4:]) == [("catch-up anew", 100.0), ("other", 100.0)]
    print_success("removed: never called again; the other one still called; registered anew: called")


def test_removing_a_name_never_registered_or_already_removed_does_nothing() -> None:
    """SWA-039 — contract (f): removing "never-registered" raises nothing, returns None, and leaves "catch-up" in place; "catch-up" removed twice, the second removal raises nothing either, and a return calls nothing."""
    print_section("SWA-039: remove_return_listener of an unknown name")
    activity, clock = _activity()
    calls: list[float] = []
    activity.register_return_listener("catch-up", 0.0, calls.append)

    assert activity.remove_return_listener("never-registered") is None
    clock.now = 1_300.0
    _user_request(activity)
    assert calls == [300.0]

    activity.remove_return_listener("catch-up")
    assert activity.remove_return_listener("catch-up") is None
    clock.now = 1_600.0
    _user_request(activity)
    assert calls == [300.0]
    print_success("no error; nothing else removed")


@pytest.mark.parametrize("name", ["", " ", "\t\n "], ids=["empty", "a-space", "whitespace"])
def test_a_blank_name_to_remove_is_refused_and_nothing_is_removed(name: str) -> None:
    """SWA-040 — contract (f): an empty or blank name is a ``ValueError``; the listener registered is still called on the next return."""
    print_section(f"SWA-040: remove_return_listener({name!r})")
    activity, clock = _activity()
    calls: list[float] = []
    activity.register_return_listener("catch-up", 0.0, calls.append)

    with pytest.raises(ValueError):
        activity.remove_return_listener(name)

    clock.now = 1_300.0
    _user_request(activity)
    assert calls == [300.0]
    print_success("ValueError; nothing removed")


# =============================================================================
# (o) RESPONSE HEADERS (lot Z5)
# =============================================================================

#: A header of the tests, and a second one; never the scheduler's own, so that a case does not depend on lot Z5's names.
TEST_HEADER = "X-LibreFolio-Test-Refresh"
OTHER_HEADER = "X-LibreFolio-Test-Other"
#: The routes of the header app: two under the API prefix, one answering with the test header of its own, a streaming one.
API_PLAIN = f"{API_V1_PREFIX}/z5-headers/plain"
API_OWN_HEADER = f"{API_V1_PREFIX}/z5-headers/own-header"
API_STREAM = f"{API_V1_PREFIX}/z5-headers/stream"
API_UNKNOWN = f"{API_V1_PREFIX}/z5-headers/no-route-here"
#: Paths outside ``/api/``: the site, the docs, the user's route of the other apps.
NON_API_PATHS = ("/", "/docs-z5", USER_ROUTE)


class Box:
    """A provider answering what the test puts in ``value``; ``calls`` counts its readings."""

    def __init__(self, value: object) -> None:
        self.value = value
        self.calls = 0

    def __call__(self) -> object:
        self.calls += 1
        if isinstance(self.value, BaseException):
            raise self.value
        return self.value


def _named(pairs: Any) -> list[tuple[str, str]]:
    """``response_headers()`` as ``[(name lower-cased, value)]``, in order: the case the names come back in is not part of the contract."""
    assert isinstance(pairs, tuple), f"response_headers() must be a tuple, got {pairs!r}"
    return [(name.lower(), value) for name, value in pairs]


def _header_app(activity: Activity | None, box: Box | None = None) -> FastAPI:
    """Routes under ``/api/`` and outside it, the probes, behind ``ActivityMiddleware`` — on ``activity``, or without it.

    ``API_PLAIN`` answers 200; when ``box`` is given, its handler sets ``box.value = "late"`` first, so the value at the
    answer's start differs from the value at the request's start. ``API_OWN_HEADER`` answers with ``TEST_HEADER: app``.
    ``API_STREAM`` streams three chunks. Any other path is answered 404 by the router.
    """
    app = FastAPI()

    async def plain() -> PlainTextResponse:
        if box is not None:
            box.value = "late"
        return PlainTextResponse("ok")

    async def own_header() -> PlainTextResponse:
        return PlainTextResponse("ok", headers={TEST_HEADER: "app"})

    async def chunks() -> AsyncIterator[str]:
        for index in range(STREAM_CHUNKS):
            yield f"chunk-{index}\n"

    async def stream() -> StreamingResponse:
        return StreamingResponse(chunks(), media_type="text/plain")

    async def site() -> PlainTextResponse:
        return PlainTextResponse("site")

    app.add_api_route(API_PLAIN, plain, methods=["GET"])
    app.add_api_route(API_OWN_HEADER, own_header, methods=["GET"])
    app.add_api_route(API_STREAM, stream, methods=["GET"])
    for path in (HEALTH, READY, LANE_HEALTH, WAKE_SYNC, *NON_API_PATHS):
        app.add_api_route(path, site, methods=["GET"])
    if activity is None:
        app.add_middleware(ActivityMiddleware)
    else:
        app.add_middleware(ActivityMiddleware, activity=activity)
    return app


def test_response_headers_are_the_providers_with_a_value_now_in_registration_order() -> None:
    """SWA-041 — contract (o): a new record gives ``()``; two providers give their pairs in registration order; each answer is read at the call; None, "" or a non-str gives nothing."""
    print_section("SWA-041: register_response_header and response_headers()")
    activity, _ = _activity()
    assert activity.response_headers() == ()

    first, second = Box("starting"), Box("b")
    activity.register_response_header(TEST_HEADER, first)
    activity.register_response_header(OTHER_HEADER, second)
    assert _named(activity.response_headers()) == [(TEST_HEADER.lower(), "starting"), (OTHER_HEADER.lower(), "b")]

    first.value = "running"
    assert _named(activity.response_headers()) == [(TEST_HEADER.lower(), "running"), (OTHER_HEADER.lower(), "b")], "read at each call, never cached"

    for nothing in (None, "", 42):
        first.value = nothing
        assert _named(activity.response_headers()) == [(OTHER_HEADER.lower(), "b")], f"a provider answering {nothing!r} gives no header"
    print_success("in order, read now, only non-empty strings")


def test_a_header_registered_again_in_another_case_replaces_the_provider() -> None:
    """SWA-042 — contract (o): "X-LibreFolio-Test-Refresh" then "x-librefolio-test-refresh": one pair, the second provider's value."""
    print_section("SWA-042: a provider replaced")
    activity, _ = _activity()
    activity.register_response_header(TEST_HEADER, Box("first"))
    activity.register_response_header(OTHER_HEADER, Box("other"))

    activity.register_response_header(TEST_HEADER.lower(), Box("second"))

    named = _named(activity.response_headers())
    assert [value for name, value in named if name == TEST_HEADER.lower()] == ["second"]
    assert sorted(named) == sorted([(TEST_HEADER.lower(), "second"), (OTHER_HEADER.lower(), "other")])
    print_success("one provider per name, whatever its case")


def test_removing_a_header_stops_it_and_an_unknown_name_is_no_error() -> None:
    """SWA-043 — contract (o): removed, the provider is no longer read and gives nothing, the other still answers; removing it again, or a name never registered, raises nothing and returns None."""
    print_section("SWA-043: remove_response_header")
    activity, _ = _activity()
    removed, kept = Box("starting"), Box("b")
    activity.register_response_header(TEST_HEADER, removed)
    activity.register_response_header(OTHER_HEADER, kept)

    assert activity.remove_response_header(TEST_HEADER) is None
    calls = removed.calls
    assert _named(activity.response_headers()) == [(OTHER_HEADER.lower(), "b")]
    assert removed.calls == calls, "a removed provider must not be read"
    assert activity.remove_response_header(TEST_HEADER) is None
    assert activity.remove_response_header("X-Never-Registered") is None
    assert _named(activity.response_headers()) == [(OTHER_HEADER.lower(), "b")]
    print_success("removed; no-op for an unknown name")


def test_a_provider_that_raises_is_skipped_and_logged_and_the_others_still_answer() -> None:
    """SWA-044 — contract (o): the first provider raises: no exception reaches the caller, the second still answers, and something is logged about it."""
    print_section("SWA-044: a provider that raises")
    activity, _ = _activity()
    activity.register_response_header(TEST_HEADER, Box(RuntimeError("provoked: the provider fails")))
    activity.register_response_header(OTHER_HEADER, Box("b"))

    with _activity_log() as events:
        pairs = activity.response_headers()

    assert _named(pairs) == [(OTHER_HEADER.lower(), "b")]
    assert [event for event in events if event.get("event") != LOG_CANARY], "the provider's failure must be logged"
    print_success("skipped, logged; the other answers")


@pytest.mark.asyncio
@pytest.mark.parametrize("path", [API_PLAIN, WAKE_SYNC, API_UNKNOWN], ids=["an-api-route", "wake-sync", "an-api-path-answered-404"])
async def test_an_api_answer_carries_the_headers_lower_cased_in_latin_1(path: str) -> None:
    """SWA-045 — contract (o): ``GET path`` under ``/api/``, not a probe — a route, ``wake-sync``, a path answered 404 —: the answer's raw headers hold each pair once, the name lower-cased, the value in latin-1."""
    print_section(f"SWA-045: GET {path}")
    activity, _ = _activity()
    activity.register_response_header(TEST_HEADER, Box("café"))
    activity.register_response_header(OTHER_HEADER, Box("running"))

    async with _client(_header_app(activity)) as client:
        response = await client.get(path)

    raw = [(name, value) for name, value in response.headers.raw if name.lower() in (TEST_HEADER.lower().encode(), OTHER_HEADER.lower().encode())]
    assert raw == [(TEST_HEADER.lower().encode("latin-1"), "café".encode("latin-1")), (OTHER_HEADER.lower().encode("latin-1"), b"running")], f"{response.status_code}: {response.headers.raw}"
    print_success(f"{response.status_code}: both headers, lower-cased, latin-1")


@pytest.mark.asyncio
@pytest.mark.parametrize("path", [HEALTH, READY, LANE_HEALTH, *NON_API_PATHS], ids=["health", "ready", "test-lane-health", "the-site-root", "a-site-page", "the-user-route"])
async def test_a_probe_or_a_path_outside_the_api_gets_no_header(path: str) -> None:
    """SWA-046 — contract (o): a probe, or a path outside ``/api/``, is answered without the headers, and the providers are not needed for it."""
    print_section(f"SWA-046: GET {path}")
    activity, _ = _activity()
    activity.register_response_header(TEST_HEADER, Box("starting"))

    async with _client(_header_app(activity)) as client:
        response = await client.get(path)

    assert response.status_code == 200
    assert TEST_HEADER.lower() not in response.headers, f"{path} must not get the header: {response.headers.raw}"
    print_success("no header")


@pytest.mark.asyncio
async def test_the_app_header_of_the_same_name_wins() -> None:
    """SWA-047 — contract (o): the route answers ``X-LibreFolio-Test-Refresh: app``, the provider "middleware": the answer holds one value, the app's; the other header is still added."""
    print_section("SWA-047: the app's own header")
    activity, _ = _activity()
    activity.register_response_header(TEST_HEADER, Box("middleware"))
    activity.register_response_header(OTHER_HEADER, Box("b"))

    async with _client(_header_app(activity)) as client:
        response = await client.get(API_OWN_HEADER)

    assert response.headers.get_list(TEST_HEADER) == ["app"]
    assert response.headers.get_list(OTHER_HEADER) == ["b"]
    print_success("the app's value, once")


@pytest.mark.asyncio
async def test_the_values_are_read_when_the_answer_starts_not_when_the_request_starts() -> None:
    """SWA-048 — contract (o): the provider answers None when the request starts and the handler sets it to "late": the answer says "late"."""
    print_section("SWA-048: read at http.response.start")
    activity, _ = _activity()
    box = Box(None)
    activity.register_response_header(TEST_HEADER, box)

    async with _client(_header_app(activity, box)) as client:
        response = await client.get(API_PLAIN)

    assert response.status_code == 200
    assert response.headers.get_list(TEST_HEADER) == ["late"]
    print_success("the value of the answer's start")


@pytest.mark.asyncio
async def test_a_streaming_answer_gets_the_headers_once_and_its_body_intact() -> None:
    """SWA-049 — contract (o): a streaming answer under ``/api/`` holds the header once, and its three chunks in order."""
    print_section("SWA-049: a streaming answer")
    activity, _ = _activity()
    activity.register_response_header(TEST_HEADER, Box("running"))

    async with _client(_header_app(activity)) as client:
        response = await client.get(API_STREAM)

    assert response.status_code == 200
    assert response.headers.get_list(TEST_HEADER) == ["running"]
    assert response.text == "".join(f"chunk-{index}\n" for index in range(STREAM_CHUNKS))
    print_success("once, on the start; the body intact")


@pytest.mark.asyncio
async def test_without_its_own_activity_the_middleware_reads_the_providers_of_current_activity(decoy: Activity) -> None:
    """SWA-050 — contract (o), (m): a provider registered on the record ``current_activity()`` answers (the decoy), with a middleware given no ``activity``: the answer carries it."""
    print_section("SWA-050: the providers of current_activity()")
    decoy.register_response_header(TEST_HEADER, Box("starting"))

    async with _client(_header_app(None)) as client:
        response = await client.get(API_PLAIN)

    assert response.headers.get_list(TEST_HEADER) == ["starting"]
    print_success("the process's record")

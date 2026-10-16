"""The user's presence and the work in progress, for this process (release 1.3, decision D-S1).

Owner: workstream Z. Every HTTP request crosses ``ActivityMiddleware``, the outermost entry of ``MIDDLEWARE_STACK``. A
request of the user stamps the moment of the user's last request, at its start and at its end, and every request but a
probe is *in flight* until the app has finished with it: the last chunk of a streamed body and the background tasks of
the response included. The probes (``PROBE_PATHS``: health, readiness, the test lane's health) are not counted at all,
so an orchestrator calling them every few seconds never keeps a machine awake. ``wake-sync`` (``WAKE_PATHS``) is in
flight but it is not the user: a scheduled wake-up must not look like a visit. Any other request is the user, the
frontend's polling included: the frontend stops polling in a hidden tab and after ten minutes without input.

Work that runs outside a request says so with ``busy(reason)``; a source the process cannot wrap, such as a backup run
by another process, is read through ``register_busy_check``. The idle monitor suspends only when ``busy_reasons()`` is
empty and ``idle_seconds()`` has reached its threshold; a return listener lets the scheduler catch up on the first
request after a silence.

The clock is the wall clock: the time a machine spends suspended must count as silence, and a monotonic clock stops
with the machine. ``ACTIVITY`` is read at call time (``current_activity()``), so a test can replace it.
"""

from __future__ import annotations

import threading
import time
from collections import Counter
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from typing import Literal

from starlette.types import ASGIApp, Receive, Scope, Send

from backend.app.config import API_V1_PREFIX
from backend.app.logging_config import get_logger

logger = get_logger(__name__)

#: The probes of an orchestrator or of the test runner: never the user, never in flight.
PROBE_PATHS: frozenset[str] = frozenset({f"{API_V1_PREFIX}/system/health", f"{API_V1_PREFIX}/system/ready", f"{API_V1_PREFIX}/system/test-lane-health"})
#: The scheduled wake-up: in flight while its jobs run, but never the user.
WAKE_PATHS: frozenset[str] = frozenset({f"{API_V1_PREFIX}/system/wake-sync"})

RequestKind = Literal["probe", "wake", "user"]

#: The reason ``busy_reasons()`` gives while at least one request is in flight.
REQUESTS_REASON = "requests"


def request_kind(path: str) -> RequestKind:
    """``"probe"``, ``"wake"`` or ``"user"`` for a request path; trailing slashes are ignored."""
    normalized = path.rstrip("/") or "/"
    if normalized in PROBE_PATHS:
        return "probe"
    if normalized in WAKE_PATHS:
        return "wake"
    return "user"


def _require_name(value: object, what: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{what} must be a non-empty string, got {value!r}")
    return value


class Activity:
    """The user's last request, the requests in flight and the work in progress; thread-safe, in memory."""

    def __init__(self, *, clock: Callable[[], float] = time.time) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self.started_at: float = clock()
        self._last_user_request_at: float | None = None
        self._in_flight = 0
        self._busy: Counter[str] = Counter()
        self._checks: dict[str, Callable[[], object]] = {}
        self._failing_checks: set[str] = set()
        self._listeners: dict[str, tuple[float, Callable[[float], object]]] = {}

    @property
    def in_flight(self) -> int:
        """The requests in flight, probes excluded, ``wake-sync`` included."""
        with self._lock:
            return self._in_flight

    @property
    def last_user_request_at(self) -> float | None:
        """The wall-clock time of the user's last request, at its start or at its end; None before the first."""
        with self._lock:
            return self._last_user_request_at

    def _idle_locked(self, now: float) -> float:
        reference = self.started_at if self._last_user_request_at is None else self._last_user_request_at
        return max(0.0, float(now - reference))

    def idle_seconds(self, now: float | None = None) -> float:
        """Seconds since the user's last request, or since this record was created; never negative."""
        current = self._clock() if now is None else now
        with self._lock:
            return self._idle_locked(current)

    @contextmanager
    def _request(self, presence: bool) -> Iterator[None]:
        due: list[tuple[str, Callable[[float], object]]] = []
        silence = 0.0
        with self._lock:
            self._in_flight += 1
            if presence:
                now = self._clock()
                silence = self._idle_locked(now)
                self._last_user_request_at = now
                due = [(name, callback) for name, (after_seconds, callback) in self._listeners.items() if silence >= after_seconds]
        try:
            for name, callback in due:
                try:
                    callback(silence)
                except Exception:
                    logger.warning("Return listener failed", listener=name, silence_s=round(silence, 1), exc_info=True)
            yield
        finally:
            with self._lock:
                self._in_flight = max(0, self._in_flight - 1)
                if presence:
                    self._last_user_request_at = self._clock()

    def request(self, *, presence: bool = True) -> AbstractContextManager[None]:
        """A request in flight for the duration of the block; with ``presence``, the user's, stamped at both ends.

        At the start of a request of the user, the return listeners whose threshold the silence has reached are called
        with the silence, before the block runs. One that raises is logged, and the request goes on.
        """
        return self._request(presence)

    def register_return_listener(self, name: str, after_seconds: float, callback: Callable[[float], object]) -> None:
        """Call ``callback(silence)`` at the start of each request of the user after ``after_seconds`` of silence.

        The callback runs on the request's thread, before the request: it must be quick and must not block (schedule
        the work, do not do it). A listener registered under the same name is replaced.
        """
        _require_name(name, "a return listener's name")
        with self._lock:
            self._listeners[name] = (after_seconds, callback)

    def remove_return_listener(self, name: str) -> None:
        """Stop calling the return listener registered as ``name``; an unknown name is not an error."""
        _require_name(name, "a return listener's name")
        with self._lock:
            self._listeners.pop(name, None)

    @contextmanager
    def _busy_block(self, reason: str) -> Iterator[None]:
        with self._lock:
            self._busy[reason] += 1
        try:
            yield
        finally:
            with self._lock:
                self._busy[reason] -= 1
                if self._busy[reason] <= 0:
                    del self._busy[reason]

    def busy(self, reason: str) -> AbstractContextManager[None]:
        """Work in progress for the duration of the block, listed as ``reason``; nestable, from any thread."""
        return self._busy_block(_require_name(reason, "a busy reason"))

    def register_busy_check(self, name: str, check: Callable[[], object]) -> None:
        """Ask ``check()`` at each reading whether ``name`` is busy; a check that raises counts as busy.

        A check under the same name is replaced. It is called outside any lock, at each ``busy_reasons()``: it must
        be quick. Its first failure in a row is logged as a warning.
        """
        _require_name(name, "a busy check's name")
        with self._lock:
            self._checks[name] = check
            self._failing_checks.discard(name)

    def busy_reasons(self) -> tuple[str, ...]:
        """What keeps the process busy: ``"requests"``, the open ``busy()`` reasons, the checks that answer yes or fail."""
        with self._lock:
            reasons = [REQUESTS_REASON] if self._in_flight > 0 else []
            reasons.extend(sorted(self._busy))
            checks = list(self._checks.items())
        for name, check in checks:
            try:
                answer = check()
            except Exception as exc:
                with self._lock:
                    first = name not in self._failing_checks
                    self._failing_checks.add(name)
                if first:
                    logger.warning("Busy check failed", check=name, error=repr(exc), exc_info=True)
                reasons.append(name)
                continue
            with self._lock:
                self._failing_checks.discard(name)
            if answer:
                reasons.append(name)
        return tuple(dict.fromkeys(reasons))

    def is_busy(self) -> bool:
        """True while ``busy_reasons()`` is not empty."""
        return bool(self.busy_reasons())


#: The process's record, read at call time by ``current_activity()``.
ACTIVITY = Activity()


def current_activity() -> Activity:
    """The process's ``ACTIVITY``, as it is when called."""
    return ACTIVITY


class ActivityMiddleware:
    """Counts each HTTP request: a probe not at all, ``wake-sync`` in flight only, any other the user's and in flight.

    Pure ASGI, the outermost middleware: a request is in flight from its first byte until the app returns, so until the
    last chunk of a streamed body and the background tasks of its response. Without ``activity``, the process's record
    is read at each request.
    """

    def __init__(self, app: ASGIApp, *, activity: Activity | None = None) -> None:
        self.app = app
        self._activity = activity

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        kind = request_kind(scope["path"])
        if kind == "probe":
            await self.app(scope, receive, send)
            return
        activity = self._activity if self._activity is not None else current_activity()
        with activity.request(presence=kind == "user"):
            await self.app(scope, receive, send)

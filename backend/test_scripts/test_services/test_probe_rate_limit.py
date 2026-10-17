"""MF-SI2 (E's review of R13-SEC7-2): ``POST /assets/provider/probe`` is limited per user, 30 probes a minute; MF-SEC9a
(E's review of R13-SEC9): the limit is read at each probe.

Before MF-SI2: a probe — a dry run any signed-in user may start, which may call a provider or generate a schedule — had
no limit of its own. Now (``backend/app/api/v1/assets/providers.py``): ``probe_provider_config`` asks ``probe_limiter()``
for the limiter in force at each probe and counts one hit for ``current_user.id`` before anything else; a refused hit
answers 429 ``{"error_code": "PROBE_RATE_LIMITED", "retry_after": s, "message": …}`` with the header ``Retry-After: s``,
``s = max(1, ceil(retry_after))`` — the style of ``api/v1/email.py::_rate_limited``. A refused probe never reaches
``AssetSourceManager.probe_provider_config`` and is not counted.

The route coroutine is called directly, never through the shared backend: there, the test user's real limiter would be
consumed and the other probe tests of the lane refused. The route tests put a private ``SlidingWindowLimiter`` of
``LIMIT`` hits per ``WINDOW`` seconds on a fake clock behind ``probe_limiter`` and a recording stub in place of the
manager's probe, both with ``monkeypatch``; time moves by advancing the clock, never by waiting. ``LIMIT`` is not 30 on
purpose: the route must defer to the limiter ``probe_limiter()`` answers, whatever its limit.
``test_probe_limiter_without_the_variable_is_30_probes_per_60_seconds`` pins the default to the contract. No assertion
reads the message text.

The override, ``LIBREFOLIO_PROBE_RATE_LIMIT``. ``config/plugins.py::probe_rate_limit()`` reads it from ``os.environ`` at
each call: unset or blank, 30; stripped, ASCII digits only and at most 10 000, that number, ``0`` turning the limit off;
anything else raises ``ValueError`` naming the variable and the value as read (stripped). ``providers.probe_limiter()``
reads it at each call too (MF-SEC9a, as ``login_limit_enabled()`` reads its variable): ``SlidingWindowLimiter(n, 60)``,
one per value in ``PROBES_BY_LIMIT`` and reused, so a new value applies at the next probe — no restart — and a value the
setting comes back to finds its counts; None for 0, with a warning naming ``LIBREFOLIO_PROBE_RATE_LIMIT=0``; for a value
it cannot use, an error naming the variable and the value, and 30 — the limit never turns off by mistake. Each warning
and error is logged once per value (``_PROBE_SETTING_LOGGED``), never once per probe. ``./dev.py server --test`` hands
the lane's server the variable at ``"0"``, and only in test mode.

An autouse fixture removes any ``LIBREFOLIO_PROBE_RATE_LIMIT`` the process inherited, and gives each test an empty
``PROBES_BY_LIMIT`` and ``_PROBE_SETTING_LOGGED`` of its own (``monkeypatch``): no count and no «already logged» leaks
from one test, or from the module's import, into another. A test sets its own value. Where a test reads the log, the
module's ``logger`` is a recorder. The route tests of the override let the route build its limiters through
``probe_limiter()`` itself, each ``SlidingWindowLimiter`` bound to the fake clock. The lane switch runs
``dev.cmd_server`` in this process through ``test_dev_designer_lab_banner.start_server`` — the builds, checks, runtime
configuration and the uvicorn launch stood in for, any real process, exec or signal failing the test, ``os.environ``
unchanged — and reads the environment handed to the stood-in launch; it is imported only by those tests.

Red on HEAD ``f252acb4a`` (before MF-SI2): every test of the route, of ``probe_limiter`` and of the setting — no
``probe_rate_limit`` in ``config/plugins.py``, no ``probe_limiter`` nor ``SlidingWindowLimiter`` in ``providers``, a
route that never refuses — and the lane switch (no variable in the lane's server environment).

Red on HEAD ``04955c498`` (MF-SI2 in, before MF-SEC9a), the limiter read once at import into ``PROBES_BY_USER``: every
route test — the route counts on that limiter, never asking ``probe_limiter()``, so the private one is never hit and a
value set by the test never applies —; ``test_probe_limiter_without_the_variable_is_30_probes_per_60_seconds`` (a new
limiter at each call: counts that would never add up); ``test_a_limit_the_setting_comes_back_to_keeps_its_counts`` and
``test_each_warning_and_error_is_logged_once_per_value`` (logged at each call). Green there: the setting's tests, the
single-call ones of ``probe_limiter`` and the lane switch.

One guard: a server started without ``--test`` is handed no ``LIBREFOLIO_PROBE_RATE_LIMIT``.

Pure: no database, no server, no network. The probe request is a real ``FAProviderProbeRequest`` for
``scheduled_investment`` without parameters (its plugin validates them, offline); the stub answers in its place.
"""

from __future__ import annotations

import importlib
import os
import subprocess
from collections.abc import Callable
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest
from fastapi import HTTPException

from backend.app.api.v1.assets import providers
from backend.app.config import plugins as plugin_config
from backend.app.schemas.provider import FAProviderProbeRequest, ProbeOperation
from backend.app.services.assets.manager import AssetSourceManager
from backend.app.utils.runtime.rate_window import SlidingWindowLimiter

LIMIT = 3
WINDOW = 60
START = 1_000_000.0
USER_A = SimpleNamespace(id=9_101)
USER_B = SimpleNamespace(id=9_102)
# What the stub answers: the route returns the manager's result as it is.
_ANSWER = object()

PROBE_LIMIT_VARIABLE = "LIBREFOLIO_PROBE_RATE_LIMIT"
#: The limit without the variable, and with a value that cannot be used.
DEFAULT_LIMIT = 30
#: The window of every limiter ``probe_limiter()`` builds, in seconds.
PROBE_WINDOW = 60
#: Probes of one user while the limit is off: more than the default allows.
OFF_PROBES = 40
#: The levels of a logged error.
ERROR_LEVELS = ("error", "exception", "critical")
#: The module whose in-process ``cmd_server`` harness the lane-switch tests reuse: imported by them only.
SERVER_HARNESS = "backend.test_scripts.test_utilities.test_dev_designer_lab_banner"


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


@pytest.fixture
def limiter(monkeypatch: pytest.MonkeyPatch, clock: FakeClock) -> SlidingWindowLimiter:
    """A private limiter on the fake clock, answered by ``probe_limiter()`` in place of the one in force: the route asks
    for it at each probe (before f252acb4a there was no ``probe_limiter`` and this fails)."""
    private = SlidingWindowLimiter(LIMIT, WINDOW, clock=clock)
    monkeypatch.setattr(providers, "probe_limiter", lambda: private, raising=True)
    return private


@pytest.fixture
def manager_calls(monkeypatch: pytest.MonkeyPatch) -> list[tuple]:
    """Every call that reached the manager's probe, as ``(config, operations, user_id)``; the stub answers ``_ANSWER``."""
    calls: list[tuple] = []

    async def recording_probe(config, operations, *, user_id=None):
        calls.append((config, operations, user_id))
        return _ANSWER

    monkeypatch.setattr(AssetSourceManager, "probe_provider_config", staticmethod(recording_probe))
    return calls


class LogRecorder:
    """Stands in for ``providers.logger``: every call recorded as ``(level, event, fields)``, in order."""

    LEVELS = ("debug", "info", "warning", *ERROR_LEVELS)

    def __init__(self) -> None:
        self.records: list[tuple[str, str, dict[str, Any]]] = []

    def __getattr__(self, level: str) -> Callable[..., None]:
        if level not in LogRecorder.LEVELS:
            raise AttributeError(level)

        def record(event: object, *_args: object, **fields: Any) -> None:
            self.records.append((level, str(event), fields))

        return record

    def at(self, *levels: str) -> list[str]:
        """The events logged at these levels, in order."""
        return [event for level, event, _fields in self.records if level in levels]


@pytest.fixture(autouse=True)
def _no_inherited_probe_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Any ``LIBREFOLIO_PROBE_RATE_LIMIT`` the process inherited is removed: a test sees only the value it sets."""
    monkeypatch.delenv(PROBE_LIMIT_VARIABLE, raising=False)


@pytest.fixture(autouse=True)
def _fresh_probe_limiters(monkeypatch: pytest.MonkeyPatch) -> None:
    """The test's own limiters by limit and its own «already logged»: nothing counted or logged by another test, or by
    the module's import, is seen here, and nothing of this test outlives it. ``raising=False``: code without the names
    (HEAD 04955c498) then runs as it did, and its tests fail on what it does, not on a missing name."""
    monkeypatch.setattr(providers, "PROBES_BY_LIMIT", {}, raising=False)
    monkeypatch.setattr(providers, "_PROBE_SETTING_LOGGED", set(), raising=False)


@pytest.fixture
def set_probe_limit(monkeypatch: pytest.MonkeyPatch) -> Callable[[str | None], None]:
    """``LIBREFOLIO_PROBE_RATE_LIMIT=value``, or unset for None."""

    def set_value(value: str | None) -> None:
        if value is None:
            monkeypatch.delenv(PROBE_LIMIT_VARIABLE, raising=False)
        else:
            monkeypatch.setenv(PROBE_LIMIT_VARIABLE, value)

    return set_value


@pytest.fixture
def log(monkeypatch: pytest.MonkeyPatch) -> LogRecorder:
    """The recorder in place of ``providers.logger``, for this test only."""
    recorder = LogRecorder()
    monkeypatch.setattr(providers, "logger", recorder, raising=True)
    return recorder


@pytest.fixture
def built_on_fake_clock(monkeypatch: pytest.MonkeyPatch, clock: FakeClock) -> list[SlidingWindowLimiter]:
    """The limiters ``probe_limiter()`` builds, each a real ``SlidingWindowLimiter`` on the fake clock, in the order it
    builds them: the module's name is replaced (before MF-SI2 the module had no such name and this fails)."""
    built: list[SlidingWindowLimiter] = []

    def on_fake_clock(limit: int, window_seconds: float, **options: Any) -> SlidingWindowLimiter:
        made = SlidingWindowLimiter(limit, window_seconds, clock=clock, **options)
        built.append(made)
        return made

    monkeypatch.setattr(providers, "SlidingWindowLimiter", on_fake_clock, raising=True)
    return built


@pytest.fixture(scope="module")
def probe_request() -> FAProviderProbeRequest:
    """A valid probe request: ``scheduled_investment`` without parameters validates offline (its default schedule)."""
    return FAProviderProbeRequest(provider_code="scheduled_investment", identifier="mf-si2-probe", identifier_type="AUTO_GENERATED", provider_params=None, operations=[ProbeOperation.CURRENT_PRICE])


async def _probe(probe_request: FAProviderProbeRequest, user: SimpleNamespace):
    return await providers.probe_provider_config(request=probe_request, current_user=user)


async def _refused(probe_request: FAProviderProbeRequest, user: SimpleNamespace) -> HTTPException:
    """The probe raises the 429 ``PROBE_RATE_LIMITED``; returns the exception."""
    with pytest.raises(HTTPException) as excinfo:
        await _probe(probe_request, user)
    refused = excinfo.value
    assert refused.status_code == 429, f"expected 429, got {refused.status_code}: {refused.detail}"
    assert isinstance(refused.detail, dict) and refused.detail.get("error_code") == "PROBE_RATE_LIMITED", refused.detail
    return refused


async def _use_the_whole_limit(probe_request: FAProviderProbeRequest, user: SimpleNamespace) -> None:
    for _ in range(LIMIT):
        assert await _probe(probe_request, user) is _ANSWER


# ============================================================================
# The limiter in force by default
# ============================================================================


def test_probe_limiter_without_the_variable_is_30_probes_per_60_seconds():
    """Red: without ``LIBREFOLIO_PROBE_RATE_LIMIT`` the limiter in force is one ``SlidingWindowLimiter`` of 30 hits per
    60 s, the same object at every call — a new one per probe would never count past one hit (on HEAD 04955c498:
    ``probe_limiter()`` built a new limiter at each call, the route kept the one of the import)."""
    first = providers.probe_limiter()
    assert isinstance(first, SlidingWindowLimiter), f"probe_limiter() returned {first!r}"
    assert (first.limit, first.window_seconds) == (DEFAULT_LIMIT, PROBE_WINDOW)
    assert providers.probe_limiter() is first, "probe_limiter() must answer the limiter in force, not a new one each call"


# ============================================================================
# The route
# ============================================================================


@pytest.mark.asyncio
async def test_probes_up_to_the_limit_reach_the_manager(limiter, manager_calls, probe_request):
    """Red: the first ``LIMIT`` probes of a user reach the manager with the request, its operations and the user's id,
    and each counts one hit for that id."""
    await _use_the_whole_limit(probe_request, USER_A)
    assert manager_calls == [(probe_request, probe_request.operations, USER_A.id)] * LIMIT
    assert limiter.count(USER_A.id) == LIMIT


@pytest.mark.asyncio
async def test_probe_past_the_limit_is_429_and_never_reaches_the_manager(limiter, manager_calls, probe_request):
    """Red: the probe after the limit raises 429 ``PROBE_RATE_LIMITED`` with an int ``retry_after`` ≥ 1, the same value
    in ``Retry-After``, and a ``message``; the manager is not called for it, and a refused probe is not counted, so the
    next one is refused the same (before: every probe reaches the manager)."""
    await _use_the_whole_limit(probe_request, USER_A)

    for _ in range(2):
        refused = await _refused(probe_request, USER_A)
        assert set(refused.detail) == {"error_code", "retry_after", "message"}
        retry_after = refused.detail["retry_after"]
        assert type(retry_after) is int and retry_after >= 1, f"retry_after is {retry_after!r}"
        assert refused.headers == {"Retry-After": str(retry_after)}

    assert len(manager_calls) == LIMIT
    assert limiter.count(USER_A.id) == LIMIT


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("elapsed", "expected_seconds"),
    [
        pytest.param(0.0, 60, id="at-once-60"),
        pytest.param(20.5, 40, id="after-20.5s-ceil-39.5-is-40"),
        pytest.param(59.75, 1, id="after-59.75s-ceil-0.25-is-1"),
    ],
)
async def test_retry_after_is_the_wait_rounded_up_to_whole_seconds(limiter, manager_calls, probe_request, clock, elapsed, expected_seconds):
    """Red: ``retry_after`` (and ``Retry-After``) is the limiter's wait — until the oldest hit leaves the window —
    rounded up, so a wait under a second still says 1, never 0."""
    await _use_the_whole_limit(probe_request, USER_A)
    clock.advance(elapsed)

    refused = await _refused(probe_request, USER_A)
    assert refused.detail["retry_after"] == expected_seconds
    assert refused.headers == {"Retry-After": str(expected_seconds)}
    assert len(manager_calls) == LIMIT


@pytest.mark.asyncio
async def test_another_user_is_not_limited(limiter, manager_calls, probe_request):
    """Red: the count is per user: while one user is refused, another one's probe reaches the manager with its own id."""
    await _use_the_whole_limit(probe_request, USER_A)
    await _refused(probe_request, USER_A)

    assert await _probe(probe_request, USER_B) is _ANSWER
    assert len(manager_calls) == LIMIT + 1
    assert manager_calls[-1][2] == USER_B.id
    assert (limiter.count(USER_A.id), limiter.count(USER_B.id)) == (LIMIT, 1)


@pytest.mark.asyncio
async def test_after_the_window_the_user_probes_again(limiter, manager_calls, probe_request, clock):
    """Red: half a second before the window ends the user is still refused; once the clock has moved past it, the
    user's probe reaches the manager again."""
    await _use_the_whole_limit(probe_request, USER_A)

    clock.advance(WINDOW - 0.5)
    await _refused(probe_request, USER_A)
    assert len(manager_calls) == LIMIT

    clock.advance(1.0)
    assert await _probe(probe_request, USER_A) is _ANSWER
    assert len(manager_calls) == LIMIT + 1
    assert manager_calls[-1][2] == USER_A.id
    assert limiter.count(USER_A.id) == 1


# ============================================================================
# The setting: probe_rate_limit()
# ============================================================================


@pytest.mark.parametrize("value", [None, "", "   ", "\t \n"], ids=["unset", "empty", "spaces", "tab-newline"])
def test_setting_unset_or_blank_is_30(set_probe_limit, value):
    """Red: without ``LIBREFOLIO_PROBE_RATE_LIMIT``, or with nothing but spaces, the limit is 30 (before: no
    ``probe_rate_limit``)."""
    set_probe_limit(value)
    assert plugin_config.probe_rate_limit() == DEFAULT_LIMIT


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param("0", 0, id="0-off"),
        pytest.param("1", 1, id="1"),
        pytest.param("45", 45, id="45"),
        pytest.param(" 12 ", 12, id="spaces-around-12"),
        pytest.param("10000", 10_000, id="10000-the-most"),
    ],
)
def test_setting_is_a_whole_number_up_to_10000(set_probe_limit, value, expected):
    """Red: a whole number from 0 to 10 000, spaces around allowed, is the limit as an int; 0 is off."""
    set_probe_limit(value)
    limit = plugin_config.probe_rate_limit()
    assert type(limit) is int and limit == expected, f"{PROBE_LIMIT_VARIABLE}={value!r}: {limit!r}"


#: Neither blank nor a whole number of ASCII digits up to 10 000. ``int()`` itself takes the two over 10 000 and the last
#: four (a sign, an underscore, non-ASCII digits): the setting must not.
REFUSED_VALUES = [
    pytest.param("abc", id="letters"),
    pytest.param("off", id="off-is-not-0"),
    pytest.param("-1", id="negative"),
    pytest.param("1.5", id="decimal"),
    pytest.param("1e3", id="exponent"),
    pytest.param("0x1F", id="hex"),
    pytest.param("3 0", id="space-inside"),
    pytest.param(" abc ", id="letters-spaces-around"),
    pytest.param("10001", id="over-10000"),
    pytest.param("99999999999999999999", id="far-over"),
    pytest.param("+5", id="plus-sign"),
    pytest.param("1_000", id="underscore"),
    pytest.param("٣", id="arabic-indic-digit"),
    pytest.param("３０", id="fullwidth-digits"),
]


@pytest.mark.parametrize("value", REFUSED_VALUES)
def test_setting_refuses_any_other_value_naming_the_variable_and_the_value(set_probe_limit, value):
    """Red: any other value raises ``ValueError`` whose message names ``LIBREFOLIO_PROBE_RATE_LIMIT`` and the value as
    read — stripped, in its ``repr``."""
    set_probe_limit(value)
    with pytest.raises(ValueError) as excinfo:
        plugin_config.probe_rate_limit()
    message = str(excinfo.value)
    assert PROBE_LIMIT_VARIABLE in message, message
    assert repr(value.strip()) in message, f"the value as read, {value.strip()!r}, is not named in: {message}"


def test_setting_is_read_at_each_call(set_probe_limit):
    """Red: the variable is read from ``os.environ`` at each call, never cached: 5, then 7, then unset gives 30."""
    seen = []
    for value in ("5", "7", None):
        set_probe_limit(value)
        seen.append(plugin_config.probe_rate_limit())
    assert seen == [5, 7, DEFAULT_LIMIT]


# ============================================================================
# The limiter: probe_limiter()
# ============================================================================


@pytest.mark.parametrize(
    ("value", "limit"),
    [
        pytest.param(None, DEFAULT_LIMIT, id="unset-30"),
        pytest.param("1", 1, id="1"),
        pytest.param("45", 45, id="45"),
        pytest.param("10000", 10_000, id="10000"),
    ],
)
def test_limiter_is_the_setting_per_60_seconds(set_probe_limit, log, value, limit):
    """Red: ``probe_limiter()`` is a ``SlidingWindowLimiter`` of the setting's probes per 60 s, and logs nothing (before:
    no ``probe_limiter``)."""
    set_probe_limit(value)
    built = providers.probe_limiter()
    assert isinstance(built, SlidingWindowLimiter), f"{PROBE_LIMIT_VARIABLE}={value!r}: probe_limiter() returned {built!r}"
    assert (built.limit, built.window_seconds) == (limit, PROBE_WINDOW)
    assert log.records == [], f"{PROBE_LIMIT_VARIABLE}={value!r}: nothing to log, got {log.records}"


@pytest.mark.parametrize("value", ["0", " 0 "], ids=["0", "0-spaces-around"])
def test_limiter_off_is_none_with_one_warning(set_probe_limit, log, value):
    """Red: at 0 ``probe_limiter()`` is None — no limit — and logs one warning naming ``LIBREFOLIO_PROBE_RATE_LIMIT=0``,
    no error."""
    set_probe_limit(value)
    assert providers.probe_limiter() is None
    warnings = log.at("warning")
    assert len(warnings) == 1, f"one warning expected, got {log.records}"
    assert f"{PROBE_LIMIT_VARIABLE}=0" in warnings[0], warnings[0]
    assert log.at(*ERROR_LEVELS) == [], log.records


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("abc", id="letters"),
        pytest.param("-1", id="negative"),
        pytest.param("1.5", id="decimal"),
        pytest.param("10001", id="over-10000"),
        pytest.param("٣", id="arabic-indic-digit"),
    ],
)
def test_limiter_keeps_30_with_one_error_for_a_value_it_cannot_use(set_probe_limit, log, value):
    """Red: a value the setting refuses never turns the limit off: ``probe_limiter()`` is a ``SlidingWindowLimiter`` of
    30 per 60 s, and logs one error naming ``LIBREFOLIO_PROBE_RATE_LIMIT`` and the value, no warning."""
    set_probe_limit(value)
    built = providers.probe_limiter()
    assert isinstance(built, SlidingWindowLimiter), f"{PROBE_LIMIT_VARIABLE}={value!r} must not turn the limit off: probe_limiter() returned {built!r}"
    assert (built.limit, built.window_seconds) == (DEFAULT_LIMIT, PROBE_WINDOW)
    errors = log.at(*ERROR_LEVELS)
    assert len(errors) == 1, f"one error expected, got {log.records}"
    assert PROBE_LIMIT_VARIABLE in errors[0] and repr(value) in errors[0], errors[0]
    assert log.at("warning") == [], log.records


# ============================================================================
# The route under the override
# ============================================================================


@pytest.mark.asyncio
async def test_with_the_limit_off_every_probe_reaches_the_manager(set_probe_limit, log, manager_calls, probe_request):
    """Red: with ``LIBREFOLIO_PROBE_RATE_LIMIT=0`` the route, asking ``probe_limiter()`` at each probe, counts and
    refuses nothing: 40 probes of one user — past the default 30 — all reach the manager with the user's id; the warning
    naming ``LIBREFOLIO_PROBE_RATE_LIMIT=0`` is logged once, not once per probe (on HEAD 04955c498 the route counted on
    the limiter of the import, 30 a minute: the 31st probe was refused)."""
    set_probe_limit("0")

    for _ in range(OFF_PROBES):
        assert await _probe(probe_request, USER_A) is _ANSWER
    assert manager_calls == [(probe_request, probe_request.operations, USER_A.id)] * OFF_PROBES
    warnings = log.at("warning")
    assert len(warnings) == 1 and f"{PROBE_LIMIT_VARIABLE}=0" in warnings[0], f"one warning over {OFF_PROBES} probes expected, got {log.records}"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("value", "applied"),
    [
        pytest.param("2", 2, id="set-2"),
        pytest.param(None, DEFAULT_LIMIT, id="unset-30"),
        pytest.param("-1", DEFAULT_LIMIT, id="unusable-keeps-30"),
    ],
)
async def test_the_route_applies_the_limit_the_setting_built(set_probe_limit, log, built_on_fake_clock, manager_calls, probe_request, value, applied):
    """Red: the limiter the route counts on is the one ``probe_limiter()`` builds from the variable: the first
    ``applied`` probes of a user reach the manager and the next one is 429 ``PROBE_RATE_LIMITED`` with ``retry_after``
    60, never reaching it; ONE limiter built for them all, of ``applied`` per 60 s. A value that cannot be used applies
    30, not no limit, its error logged once over the 31 probes. (On HEAD 04955c498 the route counted on the limiter of
    the import: none built, the number configured never applied.)"""
    set_probe_limit(value)

    for _ in range(applied):
        assert await _probe(probe_request, USER_A) is _ANSWER
    refused = await _refused(probe_request, USER_A)
    assert refused.detail["retry_after"] == PROBE_WINDOW
    assert len(manager_calls) == applied
    assert [(built.limit, built.window_seconds) for built in built_on_fake_clock] == [(applied, PROBE_WINDOW)], f"one limiter of {applied} per {PROBE_WINDOW} s expected, built {built_on_fake_clock}"
    assert len(log.at(*ERROR_LEVELS)) == (1 if value == "-1" else 0), log.records


@pytest.mark.asyncio
async def test_a_new_limit_applies_at_the_next_probe(set_probe_limit, log, built_on_fake_clock, manager_calls, probe_request):
    """Red: a limit changed between two probes applies at the next one, with no restart. At 2 the third probe of a user
    is refused; set to 5, the next probe reaches the manager — a limiter of 5 of its own, its first hit — and so do four
    more, the sixth refused; turned off, the next probes reach the manager, counted nowhere. (On HEAD 04955c498 the
    limit of the import applied until the next start: the third probe at 2 reached the manager.)"""
    set_probe_limit("2")
    for _ in range(2):
        assert await _probe(probe_request, USER_A) is _ANSWER
    await _refused(probe_request, USER_A)

    set_probe_limit("5")
    for _ in range(5):
        assert await _probe(probe_request, USER_A) is _ANSWER
    await _refused(probe_request, USER_A)

    set_probe_limit("0")
    for _ in range(3):
        assert await _probe(probe_request, USER_A) is _ANSWER

    assert len(manager_calls) == 2 + 5 + 3
    assert [(built.limit, built.count(USER_A.id)) for built in built_on_fake_clock] == [(2, 2), (5, 5)], f"built {built_on_fake_clock}"


@pytest.mark.asyncio
async def test_a_limit_the_setting_comes_back_to_keeps_its_counts(set_probe_limit, log, built_on_fake_clock, manager_calls, probe_request, clock):
    """Red: a limit the setting comes back to is the same limiter, its counts kept: at 2, two probes; at 5, one; back at
    2, the user is refused at once — the two hits of before still in the window — and ``probe_limiter()`` answers the
    first limiter again; once the window has passed, the user probes again. Two limiters built in all, never a third.
    (On HEAD 04955c498 the route counted on the limiter of the import: back at 2 the probe reached the manager.)"""
    set_probe_limit("2")
    for _ in range(2):
        assert await _probe(probe_request, USER_A) is _ANSWER
    first = providers.probe_limiter()

    set_probe_limit("5")
    assert await _probe(probe_request, USER_A) is _ANSWER

    set_probe_limit("2")
    await _refused(probe_request, USER_A)
    assert providers.probe_limiter() is first, "back at 2, probe_limiter() must answer the limiter of 2 it built before"
    assert len(manager_calls) == 3

    clock.advance(WINDOW + 1)
    assert await _probe(probe_request, USER_A) is _ANSWER
    assert len(manager_calls) == 4
    assert [built.limit for built in built_on_fake_clock] == [2, 5], f"built {built_on_fake_clock}"


def test_each_warning_and_error_is_logged_once_per_value(set_probe_limit, log):
    """Red: read at each probe, the setting is logged once per value, never once per read: ``0`` read seven times
    (five, then two after other values) gives one warning; ``abc`` read seven times and ``-1`` three give one error
    each, naming its value; an unset or a usable value logs nothing. Every read still answers the limit in force: None
    when off, 30 for a value that cannot be used. (On HEAD 04955c498 ``probe_limiter()`` logged at each call — one line
    per probe once read at each probe.)"""
    reads = [("0", 5), ("abc", 5), ("-1", 3), ("0", 2), ("abc", 2), (None, 2), ("7", 2)]
    answers = []
    for value, times in reads:
        set_probe_limit(value)
        for _ in range(times):
            in_force = providers.probe_limiter()
            answers.append((value, None if in_force is None else in_force.limit))

    limit_of = {"0": None, "abc": DEFAULT_LIMIT, "-1": DEFAULT_LIMIT, None: DEFAULT_LIMIT, "7": 7}
    assert answers == [(value, limit_of[value]) for value, times in reads for _ in range(times)]
    warnings, errors = log.at("warning"), log.at(*ERROR_LEVELS)
    assert len(warnings) == 1 and f"{PROBE_LIMIT_VARIABLE}=0" in warnings[0], f"one warning expected, got {log.records}"
    assert len(errors) == 2, f"one error per unusable value expected, got {log.records}"
    assert repr("abc") in errors[0] and repr("-1") in errors[1], errors


# ============================================================================
# The lane switch: ./dev.py server --test
# ============================================================================


def _server_env(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path, *, test_mode: bool) -> dict[str, str]:
    """The environment ``dev.cmd_server`` hands the server, run in this process by the Designer Lab banner's harness.

    The harness stands in for the runtime configuration, the builds, the checks and the uvicorn launch, and fails the
    test when ``os.environ`` changed; here any real process, exec or signal fails it too. Imported here, not at the top:
    only these tests depend on ``dev.py``. The environment is never printed: it holds the JWT secret.
    """
    harness: ModuleType = importlib.import_module(SERVER_HARNESS)
    for name in ("run", "Popen"):
        harness.forbid(monkeypatch, subprocess, name)
    for name in ("execvpe", "kill", "killpg"):
        harness.forbid(monkeypatch, os, name)

    start = harness.start_server(monkeypatch, capsys, tmp_path, lambda *_args, **_kwargs: False, test=test_mode)

    commands = [launch.cmd for launch in start.launches]
    assert len(commands) == 1 and "backend.app.main:app" in commands[0], f"cmd_server must reach the uvicorn launch exactly once: {commands}"
    env = start.launches[0].env
    assert env is not None, "cmd_server must hand the server an environment of its own"
    return env


def test_lane_server_starts_with_the_probe_limit_off(monkeypatch, capsys, tmp_path):
    """Red: ``./dev.py server --test`` hands the lane's server ``LIBREFOLIO_PROBE_RATE_LIMIT=0``: the E2E suites probe
    many times as one user (before: not set, so the lane's server limited them at 30 a minute)."""
    env = _server_env(monkeypatch, capsys, tmp_path, test_mode=True)
    assert env.get(PROBE_LIMIT_VARIABLE) == "0", f"the lane's server got {PROBE_LIMIT_VARIABLE}={env.get(PROBE_LIMIT_VARIABLE)!r}"


def test_server_without_test_mode_keeps_the_probe_limit(monkeypatch, capsys, tmp_path):
    """Guard: ``./dev.py server`` without ``--test``, the variable unset, hands the server no
    ``LIBREFOLIO_PROBE_RATE_LIMIT``: the default 30 applies; only a test lane turns the limit off."""
    env = _server_env(monkeypatch, capsys, tmp_path, test_mode=False)
    assert PROBE_LIMIT_VARIABLE not in env, f"a server outside test mode got {PROBE_LIMIT_VARIABLE}={env.get(PROBE_LIMIT_VARIABLE)!r}"

"""
A restore whose owner has no account yet serves no data: the guard's part (LibreFolio 1.3, workstream H, lot H5-3).
Selector: ``services restore-owner-guard``. Written RED before H5-3.

After a restore from the app on a managed instance, the first start gives the owner their account
(``instance_backup/owner.py: assign_restored_owner``, workstream B). Until that is recorded the instance serves NO data,
fail-closed, on the same mechanism as the interrupted restore (B-33, ``test_restore_guard.py``). Pinned here:

(a) ``restore_guard``: ``_owner_problem`` (None), ``OWNER_RECHECK_SECONDS = 2.0``, the patchable clock ``_monotonic`` (default
    ``time.monotonic``) and ``_owner_checked_at``, ``PROBE_OWNER_MESSAGE``.
(b) ``probe_owner_assignment(data_dir=None)``: asks ``apply.owner_assignment_problem(data_dir or get_data_dir())`` through the
    ``apply`` module, keeps the answer, stamps ``_owner_checked_at = _monotonic()``, returns it; one error line
    (``PROBE_OWNER_MESSAGE``, ``problem=<answer>``, never a path or an address) when the answer is not None, none otherwise.
(c) ``restore_interrupted()`` is ``_interrupted or _owner_problem is not None`` (pure); ``restore_interrupted_reason()`` is
    ``restore_state`` (wins) / ``owner_assignment`` / ``None``.
(d) ``async refresh_restore_state()``: only a ``pending`` answer whose last check is at least ``OWNER_RECHECK_SECONDS`` old is
    asked again, in a thread; a ``<CODE>`` and ``None`` are never asked again; never raises; asks nothing when not due.
(e) ``app_lifespan.STARTUP_STEPS``: ``restore-owner`` right after ``restore-commit`` (before ``backup-leftovers``), no
    ``skip_when``, not blocking; it awaits ``app_lifespan.assign_restored_owner()`` and THEN probes; the steps after it that
    skip when the instance serves no data (stored-currencies, provider-prewarm, market-holidays, brim-parse-pool, scheduler)
    skip while ``_owner_problem`` is set.
(f) Two workers, two process states (module variables): the one stuck in ``pending`` refuses, then heals once the other
    records the outcome in a real committed ``restore.json`` (the fixtures and fakes of ``test_backup_owner.py``).

Every name of H5-3 is read by the test that needs it, so the file collects and each test reports its own red. Pure: no server,
no network, no file outside ``tmp_path``; every variable through ``monkeypatch``. One case starts a child interpreter that only
imports the module.
"""

from __future__ import annotations

import asyncio
import importlib
import inspect
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from structlog.testing import capture_logs

from backend.app.config import get_data_dir
from backend.app.logging_config import get_logger
from backend.app.services.platform import app_lifespan
from backend.app.services.platform.instance_backup import apply as apply_module
from backend.app.services.platform.lifecycle import Step, run_startup_steps
from backend.test_scripts.test_services.test_backup_owner import (  # noqa: F401 — the fixtures of B5-1's tests, reused
    FakeA,
    FakeOutcome,
    FakeOwnerAssignmentError,
    databases,
    owner,
    owner_lock_held,
    use_fake,
    write_state,
)
from backend.test_scripts.test_services.test_backup_owner import data_dir as owner_data_dir  # noqa: F401 — a fixture of B5-1's tests, reused under this name
from backend.test_scripts.test_utils import print_section, print_success

GUARD_MODULE = "backend.app.services.platform.restore_guard"
AWAIT_VARIABLE = "LIBREFOLIO_AWAIT_RESTORE"
#: The one error line of the owner probe, word for word (the contract's text).
PROBE_OWNER_MESSAGE = "The owner of the restored data has no account yet: LibreFolio serves no data until it is set"
LOG_CANARY = "h53 restore owner guard log barrier"

#: The steps after ``restore-owner`` that skip while the instance serves no data, and the function each one's ``run`` calls.
SKIPPED_AFTER_OWNER = {
    "stored-currencies": "_start_stored_currency_audit",
    "provider-prewarm": "_start_provider_prewarm",
    "market-holidays": "_start_market_holiday_prewarm",
    "brim-parse-pool": "_start_brim_parse_pool_prewarm",
    "scheduler": "_start_scheduler",
}
#: What an owner problem can be: ``pending``, or the code of A's refusal.
PROBLEMS = ("pending", "EMAIL_TAKEN")

_MISSING = object()


# =============================================================================
# Helpers (reused by test_restore_owner_guard_api.py)
# =============================================================================


def guard() -> ModuleType:
    try:
        return importlib.import_module(GUARD_MODULE)
    except ModuleNotFoundError as exc:
        if exc.name != GUARD_MODULE:
            raise
        pytest.fail(f"H5-3: there is no {GUARD_MODULE}")


def guard_name(name: str) -> Any:
    value = getattr(guard(), name, _MISSING)
    if value is _MISSING:
        pytest.fail(f"H5-3: {GUARD_MODULE} gives no {name}")
    return value


def guard_set(monkeypatch: pytest.MonkeyPatch, name: str, value: Any) -> None:
    """A module variable of the guard set with ``monkeypatch`` (restored after the case); the test fails when it is missing."""
    if getattr(guard(), name, _MISSING) is _MISSING:
        pytest.fail(f"H5-3: {GUARD_MODULE} keeps no {name}")
    monkeypatch.setattr(guard(), name, value)


class Clock:
    """The guard's patchable clock (``_monotonic``): time stands where the test puts it."""

    def __init__(self, now: float = 0.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


def arm(monkeypatch: pytest.MonkeyPatch, *, problem: str | None, interrupted: bool = False, now: float = 0.0, checked_at: float | None = None) -> Clock:
    """The process's state as the contract says: ``_owner_problem``, ``_interrupted``, the clock at ``now`` and the last
    check at ``checked_at`` (default ``now``)."""
    guard_set(monkeypatch, "_owner_problem", problem)
    guard_set(monkeypatch, "_interrupted", interrupted)
    clock = Clock(now)
    guard_set(monkeypatch, "_monotonic", clock)
    guard_set(monkeypatch, "_owner_checked_at", now if checked_at is None else checked_at)
    return clock


class Asker:
    """``apply.owner_assignment_problem`` replaced: answers ``answers`` in turn (the last one for ever), or raises; records
    the data directory it is asked about, the thread it runs in, and (in ``log``) the order of its calls."""

    def __init__(self, *answers: str | None, raises: BaseException | None = None, log: list[str] | None = None) -> None:
        self.answers = list(answers) or [None]
        self.raises = raises
        self.log = log
        self.calls: list[Path | None] = []
        self.threads: list[int] = []

    def __call__(self, data_dir: Path | None = None) -> str | None:
        self.calls.append(data_dir)
        self.threads.append(threading.get_ident())
        if self.log is not None:
            self.log.append("probe")
        if self.raises is not None:
            raise self.raises
        return self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]


def install(monkeypatch: pytest.MonkeyPatch, asker: Asker) -> Asker:
    monkeypatch.setattr(apply_module, "owner_assignment_problem", asker)
    return asker


def trap_owner_io(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Both of B's hooks replaced by traps that record a call: what a pure function must never reach."""
    reached: list[str] = []

    def trap(name: str) -> Callable[..., None]:
        def hook(*_args: Any, **_kwargs: Any) -> None:
            reached.append(name)

        return hook

    monkeypatch.setattr(apply_module, "owner_assignment_problem", trap("owner_assignment_problem"))
    monkeypatch.setattr(apply_module, "restore_state_problem", trap("restore_state_problem"))
    return reached


def _steps() -> dict[str, Step]:
    return {step.name: step for step in app_lifespan.STARTUP_STEPS}


def _restore_owner_step() -> Step:
    step = _steps().get("restore-owner")
    if step is None:
        pytest.fail(f"H5-3: no startup step restore-owner: {[s.name for s in app_lifespan.STARTUP_STEPS]}")
    return step


def set_assign(monkeypatch: pytest.MonkeyPatch, replacement: Callable[..., Any]) -> None:
    """``app_lifespan.assign_restored_owner`` replaced (the name the step reads when it runs)."""
    if getattr(app_lifespan, "assign_restored_owner", _MISSING) is _MISSING:
        pytest.fail("H5-3: app_lifespan does not import assign_restored_owner")
    monkeypatch.setattr(app_lifespan, "assign_restored_owner", replacement)


# =============================================================================
# (a) The names
# =============================================================================


def test_the_guard_keeps_its_constants_and_its_clock():
    """(a) ``OWNER_RECHECK_SECONDS`` is 2.0, ``PROBE_OWNER_MESSAGE`` is the contract's text, ``_monotonic`` is
    ``time.monotonic`` and ``_owner_checked_at`` is a number."""
    print_section("H5-3: the guard's constants")
    assert guard_name("OWNER_RECHECK_SECONDS") == 2.0, "the pending state is asked again every 2.0 seconds"
    assert guard_name("PROBE_OWNER_MESSAGE") == PROBE_OWNER_MESSAGE, "the probe's one error line, word for word"
    assert guard_name("_monotonic") is time.monotonic, "the clock is time.monotonic until a test patches it"
    assert isinstance(guard_name("_owner_checked_at"), (int, float)), "_owner_checked_at is a number"
    print_success("2.0 s, the message, time.monotonic")


def test_a_process_that_never_probed_has_no_owner_problem():
    """(a) In a child interpreter that only imports the module: ``_owner_problem`` is None, nothing is interrupted, the
    reason is None."""
    guard()
    code = f"import importlib; m = importlib.import_module({GUARD_MODULE!r}); print(repr(m._owner_problem), m.restore_interrupted(), m.restore_interrupted_reason())"
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=180, cwd=Path(__file__).resolve().parents[3], check=False)
    assert done.returncode == 0, f"the child interpreter could not read the guard's state: {done.stderr[-2000:]}"
    assert done.stdout.strip().splitlines()[-1:] == ["None False None"], f"a process that never probed serves: {done.stdout[-500:]}"


# =============================================================================
# (b) probe_owner_assignment
# =============================================================================


@pytest.mark.parametrize("answer", [None, "pending", "EMAIL_TAKEN"], ids=["none", "pending", "code"])
def test_the_owner_probe_asks_keeps_stamps_and_returns_the_answer(monkeypatch, tmp_path, answer):
    """(b) The probe asks ``apply.owner_assignment_problem`` about the given data directory once, returns the answer, keeps
    it in ``_owner_problem`` (replacing the previous one) and stamps ``_owner_checked_at`` with the clock."""
    probe = guard_name("probe_owner_assignment")
    previous = "pending" if answer is None else None
    clock = arm(monkeypatch, problem=previous, now=100.0, checked_at=5.0)
    clock.now = 321.5
    asker = install(monkeypatch, Asker(answer))

    returned = probe(tmp_path)

    assert asker.calls == [tmp_path], f"the probe asks about the given data directory once: {asker.calls}"
    assert returned == answer, f"the probe returns the answer: {returned!r}"
    assert guard_name("_owner_problem") == answer, f"the answer is kept, the previous one replaced: {guard_name('_owner_problem')!r}"
    assert guard_name("_owner_checked_at") == 321.5, "the check is stamped with the clock, read when the probe runs"


def test_the_owner_probe_without_an_argument_asks_about_the_instances_own_data_directory(monkeypatch, tmp_path):
    """(b) ``probe_owner_assignment()`` asks about ``get_data_dir()``."""
    probe = guard_name("probe_owner_assignment")
    arm(monkeypatch, problem=None)
    root = (tmp_path / "data").resolve()
    root.mkdir()
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(root))
    monkeypatch.delenv(AWAIT_VARIABLE, raising=False)
    assert get_data_dir() == root, f"Barrier: the data directory is this case's own: {get_data_dir()}"
    asker = install(monkeypatch, Asker(None))

    probe()

    assert asker.calls == [root], f"the probe asks about get_data_dir() ({root}): {asker.calls}"


@pytest.mark.parametrize("problem", PROBLEMS)
def test_an_owner_problem_is_logged_once_as_an_error_with_its_value_only(monkeypatch, tmp_path, problem):
    """(b) A problem: exactly one error line ``PROBE_OWNER_MESSAGE`` with ``problem=<answer>``; no path, no address.
    Barrier: a canary through the module's logger reaches the capture."""
    probe = guard_name("probe_owner_assignment")
    arm(monkeypatch, problem=None)
    install(monkeypatch, Asker(problem))
    barrier_logger = getattr(guard(), "logger", None) or get_logger(GUARD_MODULE)

    with capture_logs() as events:
        barrier_logger.error(LOG_CANARY)
        probe(tmp_path)

    assert any(event.get("event") == LOG_CANARY for event in events), f"Barrier: the module's log reaches capture_logs: {events}"
    lines = [event for event in events if event.get("event") == PROBE_OWNER_MESSAGE]
    assert len(lines) == 1, f"one line {PROBE_OWNER_MESSAGE!r}: {events}"
    assert (lines[0].get("log_level"), lines[0].get("problem")) == ("error", problem), f"an error line with problem={problem!r}: {lines[0]}"
    logged = repr([event for event in events if event.get("event") != LOG_CANARY])
    assert str(tmp_path) not in logged and "@" not in logged, f"the line holds the value only, never a path or an address: {logged}"


def test_no_owner_problem_logs_nothing(monkeypatch, tmp_path):
    """(b) No problem: no error line. Barrier: a canary through the module's logger reaches the capture."""
    probe = guard_name("probe_owner_assignment")
    arm(monkeypatch, problem="pending")
    install(monkeypatch, Asker(None))
    barrier_logger = getattr(guard(), "logger", None) or get_logger(GUARD_MODULE)

    with capture_logs() as events:
        barrier_logger.info(LOG_CANARY)
        probe(tmp_path)

    assert any(event.get("event") == LOG_CANARY for event in events), f"Barrier: the module's log reaches capture_logs: {events}"
    errors = [event for event in events if event.get("log_level") in ("error", "critical")]
    assert errors == [], f"no problem, no error line: {errors}"


# =============================================================================
# (c) restore_interrupted() and restore_interrupted_reason()
# =============================================================================


@pytest.mark.parametrize(
    ("interrupted", "problem", "expected_interrupted", "expected_reason"),
    [
        pytest.param(False, None, False, None, id="serving"),
        pytest.param(False, "pending", True, "owner_assignment", id="owner-pending"),
        pytest.param(False, "EMAIL_TAKEN", True, "owner_assignment", id="owner-code"),
        pytest.param(True, None, True, "restore_state", id="state-unreadable"),
        pytest.param(True, "pending", True, "restore_state", id="state-wins-over-pending"),
        pytest.param(True, "EMAIL_TAKEN", True, "restore_state", id="state-wins-over-code"),
    ],
)
def test_the_interruption_and_its_reason_follow_the_two_variables_and_do_no_io(monkeypatch, interrupted, problem, expected_interrupted, expected_reason):
    """(c) ``restore_interrupted()`` is ``_interrupted or _owner_problem is not None``; the reason is ``restore_state``
    when the state is unreadable, else ``owner_assignment`` when an owner problem is set, else None. Both are pure: none of
    B's hooks is reached."""
    arm(monkeypatch, problem=problem, interrupted=interrupted)
    reached = trap_owner_io(monkeypatch)

    answers = (guard_name("restore_interrupted")(), guard_name("restore_interrupted_reason")())

    assert answers == (expected_interrupted, expected_reason), f"_interrupted={interrupted}, _owner_problem={problem!r}: {answers}"
    assert reached == [], f"restore_interrupted() and its reason read no file: {reached}"


# =============================================================================
# (d) refresh_restore_state()
# =============================================================================


def test_refresh_restore_state_is_a_coroutine_function():
    """(d) ``refresh_restore_state`` is ``async def`` (the dependency awaits it)."""
    assert inspect.iscoroutinefunction(guard_name("refresh_restore_state")), "refresh_restore_state is a coroutine function"


@pytest.mark.asyncio
@pytest.mark.parametrize("answer", [None, "pending", "OWNER_EMAIL_NOT_SET"], ids=["heals", "stays-pending", "becomes-code"])
async def test_a_due_pending_state_is_asked_again_in_a_thread_and_the_new_answer_kept(monkeypatch, answer):
    """(d) ``pending`` and at least ``OWNER_RECHECK_SECONDS`` since the last check (exactly 2.0 is due): the guard asks
    ``owner_assignment_problem`` once, in a worker thread, and keeps the new answer."""
    refresh = guard_name("refresh_restore_state")
    arm(monkeypatch, problem="pending", now=12.0, checked_at=10.0)
    asker = install(monkeypatch, Asker(answer))
    loop_thread = threading.get_ident()

    await refresh()

    assert len(asker.calls) == 1, f"a due pending state is asked once: {asker.calls}"
    assert asker.threads[0] != loop_thread, "the question is asked in a worker thread, off the event loop"
    assert guard_name("_owner_problem") == answer, f"the new answer is kept: {guard_name('_owner_problem')!r}"


@pytest.mark.asyncio
@pytest.mark.parametrize(("now", "due"), [pytest.param(10.0, False, id="same-instant"), pytest.param(11.999, False, id="just-before"), pytest.param(12.0, True, id="exactly-due"), pytest.param(500.0, True, id="long-after")])
async def test_the_recheck_waits_for_its_interval(monkeypatch, now, due):
    """(d) Not due (less than 2.0 s since the last check) the guard asks nothing and keeps the state; due, it asks once."""
    refresh = guard_name("refresh_restore_state")
    arm(monkeypatch, problem="pending", now=now, checked_at=10.0)
    asker = install(monkeypatch, Asker(None))

    await refresh()

    assert len(asker.calls) == (1 if due else 0), f"now={now}, last check 10.0: asked {len(asker.calls)} time(s), due={due}"
    assert guard_name("_owner_problem") == (None if due else "pending"), f"the state follows the question: {guard_name('_owner_problem')!r}"


@pytest.mark.asyncio
@pytest.mark.parametrize("problem", [None, "EMAIL_TAKEN", "USER_NOT_FOUND"], ids=["none", "code-a", "code-b"])
async def test_a_code_and_none_are_never_asked_again(monkeypatch, problem):
    """(d) ``None`` and a ``<CODE>`` are final for the process: however late, the guard asks nothing and keeps them."""
    refresh = guard_name("refresh_restore_state")
    arm(monkeypatch, problem=problem, now=100_000.0, checked_at=0.0)
    asker = install(monkeypatch, Asker("pending", None))

    await refresh()
    await refresh()

    assert asker.calls == [], f"{problem!r} is never asked again: {asker.calls}"
    assert guard_name("_owner_problem") == problem, f"the answer is kept: {guard_name('_owner_problem')!r}"


@pytest.mark.asyncio
async def test_a_pending_state_still_pending_is_not_asked_again_before_the_next_interval(monkeypatch):
    """(d, inferred from "cheap when not due"; confirm with the coordinator) After a re-ask that finds ``pending`` again the
    next call at the same instant asks nothing — a request does not read the file each time — and one 2.0 s later asks again."""
    refresh = guard_name("refresh_restore_state")
    clock = arm(monkeypatch, problem="pending", now=10.0, checked_at=0.0)
    asker = install(monkeypatch, Asker("pending", "pending", None))

    await refresh()
    await refresh()
    assert len(asker.calls) == 1, f"one question for two calls at the same instant: {asker.calls}"
    clock.now += 2.0
    await refresh()
    assert len(asker.calls) == 2, f"2.0 s later the next question is asked: {asker.calls}"
    clock.now += 2.0
    await refresh()
    assert len(asker.calls) == 3 and guard_name("_owner_problem") is None, f"the third finds None: {asker.calls}, {guard_name('_owner_problem')!r}"


@pytest.mark.asyncio
async def test_a_failing_re_ask_never_raises_and_keeps_the_previous_answer(monkeypatch):
    """(d) The probe in the thread raises: ``refresh_restore_state`` raises nothing and the state stays ``pending``."""
    refresh = guard_name("refresh_restore_state")
    arm(monkeypatch, problem="pending", now=50.0, checked_at=0.0)
    asker = install(monkeypatch, Asker(raises=RuntimeError("h53 the file cannot be read now")))

    await refresh()

    assert len(asker.calls) == 1, f"Barrier: the failing probe was reached: {asker.calls}"
    assert guard_name("_owner_problem") == "pending", f"a failing probe keeps the previous answer: {guard_name('_owner_problem')!r}"


# =============================================================================
# (e) The startup
# =============================================================================


def test_the_restore_owner_step_comes_right_after_restore_commit_and_carries_no_skip():
    """(e) ``restore-owner`` is the step right after ``restore-commit``, right before ``backup-leftovers``, after
    ``admin-bootstrap``, before every step that serves; no ``skip_when``; not blocking; the name is used once."""
    print_section("H5-3: the restore-owner step")
    names = [step.name for step in app_lifespan.STARTUP_STEPS]
    assert "restore-commit" in names and "backup-leftovers" in names, f"Barrier: restore-commit and backup-leftovers are startup steps: {names}"
    assert names.count("restore-owner") == 1, f"H5-3: one startup step restore-owner: {names}"
    assert names.index("restore-owner") == names.index("restore-commit") + 1, f"restore-owner comes right after restore-commit: {names}"
    assert names.index("backup-leftovers") == names.index("restore-owner") + 1, f"backup-leftovers comes right after restore-owner: {names}"
    assert names.index("admin-bootstrap") < names.index("restore-owner"), f"admin-bootstrap runs before restore-owner: {names}"
    assert all(names.index(name) > names.index("restore-owner") for name in SKIPPED_AFTER_OWNER), f"the steps that serve come after restore-owner: {names}"
    step = _restore_owner_step()
    assert getattr(step, "skip_when", None) is None, "restore-owner always runs"
    assert step.blocking is False, "restore-owner is not a blocking step"
    print_success("restore-commit → restore-owner → backup-leftovers")


@pytest.mark.asyncio
@pytest.mark.parametrize("answer", [None, "pending", "EMAIL_TAKEN"], ids=["none", "pending", "code"])
async def test_the_restore_owner_step_assigns_without_arguments_awaits_it_and_then_probes(monkeypatch, tmp_path, answer):
    """(e) Run alone through ``run_startup_steps``: ``assign_restored_owner()`` is called once, with no argument, and awaited
    to its end BEFORE the owner problem is probed; the probe asks about the instance's data directory and leaves
    ``_owner_problem`` at its answer (the previous one replaced); the start goes on (a marker step after it runs)."""
    step = _restore_owner_step()
    root = (tmp_path / "data").resolve()
    root.mkdir()
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(root))
    monkeypatch.delenv(AWAIT_VARIABLE, raising=False)
    arm(monkeypatch, problem="pending" if answer is None else None)
    events: list[str] = []
    calls: list[tuple[tuple, dict]] = []

    async def assign(*args: Any, **kwargs: Any) -> None:
        calls.append((args, kwargs))
        events.append("assign")
        await asyncio.sleep(0)
        events.append("assign-done")

    set_assign(monkeypatch, assign)
    asker = install(monkeypatch, Asker(answer, log=events))
    ran: list[str] = []

    await run_startup_steps((step, Step("next", lambda: ran.append("next"))))

    assert calls == [((), {})], f"assign_restored_owner() called once without arguments: {calls}"
    assert events == ["assign", "assign-done", "probe"], f"the assignment is awaited to its end, then the probe: {events}"
    assert asker.calls in ([root], [None]), f"the probe asks about the instance's data directory: {asker.calls}"
    assert guard_name("_owner_problem") == answer, f"the probe's answer is kept: {guard_name('_owner_problem')!r}"
    assert guard_name("restore_interrupted")() is (answer is not None), "restore_interrupted() follows it"
    assert ran == ["next"], "the start goes on after restore-owner"


@pytest.mark.parametrize("problem", PROBLEMS)
def test_the_steps_after_restore_owner_skip_while_an_owner_problem_is_set(monkeypatch, problem):
    """(e) Outside the awaiting-restore mode, with the state readable, each of the five ``skip_when()`` after
    ``restore-owner`` is True while ``_owner_problem`` is set and False without it."""
    steps = _steps()
    missing = [name for name in SKIPPED_AFTER_OWNER if getattr(steps.get(name), "skip_when", None) is None]
    assert missing == [], f"these steps carry no skip_when: {missing}"
    monkeypatch.delenv(AWAIT_VARIABLE, raising=False)
    arm(monkeypatch, problem=None)
    free = {name: steps[name].skip_when() for name in SKIPPED_AFTER_OWNER}
    arm(monkeypatch, problem=problem)
    held = {name: steps[name].skip_when() for name in SKIPPED_AFTER_OWNER}

    assert free == dict.fromkeys(SKIPPED_AFTER_OWNER, False), f"Barrier: without an owner problem nothing skips: {free}"
    assert held == dict.fromkeys(SKIPPED_AFTER_OWNER, True), f"owner problem {problem!r}: every one of the five skips: {held}"


@pytest.mark.asyncio
@pytest.mark.parametrize(("name", "function"), list(SKIPPED_AFTER_OWNER.items()), ids=list(SKIPPED_AFTER_OWNER))
@pytest.mark.parametrize("problem", PROBLEMS)
async def test_while_an_owner_problem_is_set_each_step_after_restore_owner_calls_nothing(monkeypatch, name, function, problem):
    """(e) The step ``name``, alone, through ``run_startup_steps``, the function it calls replaced by a recorder: with no
    owner problem it is called once (barrier); with one, never."""
    step = _steps().get(name)
    assert step is not None, f"Barrier: {name} is a startup step"
    monkeypatch.delenv(AWAIT_VARIABLE, raising=False)
    arm(monkeypatch, problem=None)
    calls: list[str] = []
    monkeypatch.setattr(app_lifespan, function, lambda *_args, **_kwargs: calls.append(name))
    await run_startup_steps((step,))
    assert calls == [name], f"Barrier: without an owner problem the step calls {function} once: {calls}"

    arm(monkeypatch, problem=problem)
    await run_startup_steps((step,))
    assert calls == [name], f"while the owner problem is {problem!r} the step {name} must call nothing: {calls}"


# =============================================================================
# (f) Two workers
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("outcome", ["sent", "error:EMAIL_TAKEN"], ids=["assigned", "refused-by-A"])
async def test_a_worker_stuck_in_pending_heals_once_the_other_records_the_outcome(owner, owner_data_dir, monkeypatch, outcome):  # noqa: F811 — fixtures imported from test_backup_owner.py
    """(f) A real committed restore (admin, owner chosen, no outcome) in ``tmp_path``; the guard's variables are worker B's.
    B's step ``restore-owner`` while the worker A holds ``owner.lock``: the real ``assign_restored_owner`` leaves the owner to
    A (A's function not called) and B's probe finds ``pending``: B refuses (interrupted, reason ``owner_assignment``). While
    the files still say pending, B's re-ask keeps it. Then A gives the owner their account (a fake of A's function) and
    records the outcome; B's next re-ask, due, reads it: ``sent`` → B serves; ``error:<CODE>`` → B keeps refusing with the
    code, and never asks again."""
    print_section(f"H5-3 two workers: {outcome}")
    root = owner_data_dir.root
    step = _restore_owner_step()
    refresh = guard_name("refresh_restore_state")
    write_state(root, owner_user_id=owner_data_dir.owner_id)
    clock = arm(monkeypatch, problem=None, now=1_000.0)
    real = apply_module.owner_assignment_problem
    asked: list[Path | None] = []

    def spy(data_dir: Path | None = None) -> str | None:
        asked.append(data_dir)
        return real(data_dir) if data_dir is not None else real(root)

    monkeypatch.setattr(apply_module, "owner_assignment_problem", spy)
    fake = FakeA(outcome=FakeOutcome.SENT) if outcome == "sent" else FakeA(raises=FakeOwnerAssignmentError("EMAIL_TAKEN"))
    use_fake(monkeypatch, owner, fake)

    # Worker B starts while A holds the lock: it assigns nothing and finds the owner pending.
    with owner_lock_held(root):
        await run_startup_steps((step,))
    assert fake.calls == [], f"B never calls A's function while A holds the lock: {fake.calls}"
    assert (guard_name("_owner_problem"), guard_name("restore_interrupted")(), guard_name("restore_interrupted_reason")()) == ("pending", True, "owner_assignment"), "B refuses: the owner is pending"
    assert len(asked) == 1, f"B's start asked once: {asked}"

    # The files still say pending: B's due re-ask keeps the refusal.
    clock.now += 3.0
    await refresh()
    assert len(asked) == 2 and guard_name("_owner_problem") == "pending", f"still pending in the files: {asked}, {guard_name('_owner_problem')!r}"

    # A gives the owner their account and records the outcome in the real restore.json.
    await owner.assign_restored_owner(root)
    assert len(fake.calls) == 1, f"A's function called once by the worker that holds the lock: {fake.calls}"

    # B's next due re-ask reads it.
    clock.now += 100.0
    await refresh()
    expected = None if outcome == "sent" else "EMAIL_TAKEN"
    assert guard_name("_owner_problem") == expected, f"B heals to {expected!r}: {guard_name('_owner_problem')!r}"
    assert guard_name("restore_interrupted")() is (expected is not None), f"B serves exactly when the owner is set: {outcome}"
    assert guard_name("restore_interrupted_reason")() == (None if expected is None else "owner_assignment"), "the reason follows"
    assert len(asked) == 3, f"three questions so far: {asked}"

    # Final: neither None nor a code is ever asked again.
    clock.now += 100_000.0
    await refresh()
    assert len(asked) == 3, f"nothing is asked once the outcome is read: {asked}"
    print_success(f"{outcome}: B refused, then healed")

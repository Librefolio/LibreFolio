"""
An unreadable restore state serves no data: the probe and the startup (LibreFolio 1.3, workstream H, lot B-33, the
start's part). Developer decision (22/10, via the coordinator): when ``.restore/restore.json`` cannot be read, the
instance serves no data until the administrator runs ``./dev.py backup pending --recover previous`` (workstream B).

Under test, written by B-33 (H) and missing today:

(a) ``backend.app.services.platform.restore_guard``:
    - ``probe_restore_state(data_dir=None) -> bool`` asks ``apply.restore_state_problem(data_dir or get_data_dir())``
      (looked up through the ``apply`` module, so a test patches it there), keeps the answer in the process and returns
      whether the restore is interrupted; on a problem it logs ONE error line, ``PROBE_MESSAGE``, with
      ``reason=<problem.reason>`` and never the content of the state file.
    - ``restore_interrupted() -> bool``: False in a process that never probed, then the last probe's answer.
    - The module-level name ``_interrupted``, which the tests set with ``monkeypatch`` (restored after each case).
(b) ``app_lifespan.STARTUP_STEPS``: a step ``restore-state`` right after ``pending-restore`` runs the probe, never
    stops the start, carries no ``skip_when``. While interrupted, the eight steps that repair, write or warm the data
    skip (``post-migration-fixes``, ``lone-transfer-legs`` and the six of the awaiting-restore mode); ``database``,
    ``global-settings``, ``pending-restore``, ``restore-state``, ``restore-commit``, ``backup-leftovers``,
    ``serving-lock`` and ``idle-monitor`` keep running. Each of the eight, run alone through ``run_startup_steps`` with
    the function it calls replaced by a recorder, calls nothing while interrupted and calls it once outside.

The pin of the exact set of steps with a ``skip_when`` (eight) and their answer in the awaiting-restore mode is in
``test_await_restore_mode.py``. B's hook (``apply.restore_state_problem``) is B's and exists: its reads here are guards.

Every name of B-33 is read by the test that needs it, so the file collects and each test reports its own red.

Pure: no server, no database, no network, no file outside ``tmp_path``; every variable and switch through
``monkeypatch``. One case starts a child interpreter that only imports the module, to read the answer of a process that
never probed.
"""

from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from structlog.testing import capture_logs

from backend.app.config import get_data_dir
from backend.app.logging_config import get_logger
from backend.app.services.platform import app_lifespan
from backend.app.services.platform.instance_backup import apply as apply_module
from backend.app.services.platform.instance_backup.paths import restore_state_path
from backend.app.services.platform.lifecycle import Step, run_startup_steps
from backend.test_scripts.test_utils import print_section, print_success

GUARD_MODULE = "backend.app.services.platform.restore_guard"
AWAIT_VARIABLE = "LIBREFOLIO_AWAIT_RESTORE"
#: The one error line of the probe, word for word (the contract's text, a log line, not a translated UI text).
PROBE_MESSAGE = "The state of the restore cannot be read: LibreFolio serves no data until the administrator runs ./dev.py backup pending --recover previous"
REASONS = ("io", "not_a_file", "invalid")
#: Written in an unreadable state file: never in the log.
STATE_CANARY = "b33canary_state_content_7f3a"
LOG_CANARY = "b33 restore guard log barrier"

#: The steps skipped while the restore is interrupted, and the function each one's ``run`` calls (a global of
#: ``app_lifespan``, read when the step runs).
SKIPPED_WHEN_INTERRUPTED = {
    "post-migration-fixes": "run_post_migration_fixes_at_startup",
    "lone-transfer-legs": "convert_lone_giving_legs_at_startup",
    "admin-bootstrap": "startup_admin_bootstrap",
    "stored-currencies": "_start_stored_currency_audit",
    "provider-prewarm": "_start_provider_prewarm",
    "market-holidays": "_start_market_holiday_prewarm",
    "brim-parse-pool": "_start_brim_parse_pool_prewarm",
    "scheduler": "_start_scheduler",
}
#: The steps that keep running while interrupted (B guards the copies itself; the serving lock keeps ``--recover`` out
#: while LibreFolio runs).
KEPT_WHEN_INTERRUPTED = ("pending-restore", "restore-state", "serving-lock", "database", "global-settings", "restore-commit", "restore-owner", "backup-leftovers", "idle-monitor")

_MISSING = object()


def guard() -> ModuleType:
    """``services.platform.restore_guard``, imported by the test that needs it."""
    try:
        return importlib.import_module(GUARD_MODULE)
    except ModuleNotFoundError as exc:
        if exc.name != GUARD_MODULE:
            raise
        pytest.fail(f"B-33: there is no {GUARD_MODULE}")


def guard_name(name: str) -> Any:
    module = guard()
    value = getattr(module, name, _MISSING)
    if value is _MISSING:
        pytest.fail(f"B-33: {GUARD_MODULE} gives no {name}")
    return value


def interrupted(monkeypatch: pytest.MonkeyPatch, value: bool) -> None:
    """The process's answer, set as the contract says (``_interrupted``); restored after the case."""
    module = guard()
    if not hasattr(module, "_interrupted"):
        pytest.fail(f"B-33: {GUARD_MODULE} keeps no _interrupted")
    monkeypatch.setattr(module, "_interrupted", value)


class Recorder:
    """``apply.restore_state_problem`` replaced: records the data directory it is asked about, answers ``problem``."""

    def __init__(self, problem: apply_module.RestoreStateUnreadableError | None) -> None:
        self.problem = problem
        self.asked: list[Path | None] = []

    def __call__(self, data_dir: Path | None = None) -> apply_module.RestoreStateUnreadableError | None:
        self.asked.append(data_dir)
        return self.problem


@pytest.fixture
def data_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Test mode on ``tmp_path/data``: ``get_data_dir()`` is this case's own."""
    root = (tmp_path / "data").resolve()
    root.mkdir()
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(root))
    monkeypatch.delenv(AWAIT_VARIABLE, raising=False)
    assert get_data_dir() == root, f"Precondition: the data directory is this case's own, not {get_data_dir()}"
    return root


def _probe_lines(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [event for event in events if event.get("event") == PROBE_MESSAGE]


def _steps() -> dict[str, Step]:
    return {step.name: step for step in app_lifespan.STARTUP_STEPS}


# =============================================================================
# (a) restore_interrupted() and probe_restore_state()
# =============================================================================


def test_a_process_that_never_probed_is_not_interrupted():
    """(a) ``restore_interrupted()`` is False in a process that never probed (the in-process ASGI tests, a script):
    read in a child interpreter that only imports the module."""
    guard()
    code = f"import importlib; print(importlib.import_module({GUARD_MODULE!r}).restore_interrupted())"
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=180, cwd=Path(__file__).resolve().parents[3], check=False)
    assert done.returncode == 0, f"the child interpreter could not read restore_interrupted(): {done.stderr[-2000:]}"
    assert done.stdout.strip().splitlines()[-1:] == ["False"], f"a process that never probed is not interrupted: {done.stdout[-500:]}"


@pytest.mark.parametrize("reason", REASONS)
def test_a_problem_interrupts_the_restore_and_is_kept(monkeypatch, data_dir, reason):
    """(a) ``apply.restore_state_problem`` answers a problem: the probe asks about the data directory it was given,
    returns True, and ``restore_interrupted()`` answers True afterwards."""
    probe = guard_name("probe_restore_state")
    interrupted(monkeypatch, False)
    asked = Recorder(apply_module.RestoreStateUnreadableError(reason))
    monkeypatch.setattr(apply_module, "restore_state_problem", asked)

    answer = probe(data_dir)

    assert asked.asked == [data_dir], f"the probe asks apply.restore_state_problem about the given data directory once: {asked.asked}"
    assert (answer, guard_name("restore_interrupted")()) == (True, True), f"a problem ({reason}): the probe returns True and the process keeps it: {answer}"


def test_without_a_problem_the_restore_is_not_interrupted(monkeypatch, data_dir):
    """(a) No problem: the probe returns False and ``restore_interrupted()`` answers False — also after a process that
    was interrupted (the last probe's answer is kept)."""
    probe = guard_name("probe_restore_state")
    interrupted(monkeypatch, True)
    monkeypatch.setattr(apply_module, "restore_state_problem", Recorder(None))

    answer = probe(data_dir)

    assert (answer, guard_name("restore_interrupted")()) == (False, False), f"no problem: the probe returns False and keeps it: {answer}"


def test_without_a_data_directory_the_probe_asks_about_the_instances_own(monkeypatch, data_dir):
    """(a) ``probe_restore_state()`` without an argument asks about ``get_data_dir()``."""
    probe = guard_name("probe_restore_state")
    interrupted(monkeypatch, False)
    asked = Recorder(None)
    monkeypatch.setattr(apply_module, "restore_state_problem", asked)

    probe()

    assert asked.asked == [data_dir], f"the probe asks about get_data_dir() ({data_dir}): {asked.asked}"


@pytest.mark.parametrize("reason", REASONS)
def test_a_problem_is_logged_once_as_an_error_with_its_reason(monkeypatch, data_dir, reason):
    """(a) A problem: exactly one error line ``PROBE_MESSAGE`` with ``reason``. Barrier: a canary through the module's
    logger reaches the capture."""
    probe = guard_name("probe_restore_state")
    interrupted(monkeypatch, False)
    monkeypatch.setattr(apply_module, "restore_state_problem", Recorder(apply_module.RestoreStateUnreadableError(reason)))
    module = guard()
    barrier_logger = getattr(module, "logger", None) or get_logger(GUARD_MODULE)

    with capture_logs() as events:
        barrier_logger.error(LOG_CANARY)
        probe(data_dir)

    assert any(event.get("event") == LOG_CANARY for event in events), f"Barrier: the module's log reaches capture_logs: {events}"
    lines = _probe_lines(events)
    assert len(lines) == 1, f"one line {PROBE_MESSAGE!r}: {events}"
    assert (lines[0].get("log_level"), lines[0].get("reason")) == ("error", reason), f"an error line with reason={reason!r}: {lines[0]}"


def test_no_problem_logs_nothing(monkeypatch, data_dir):
    """(a) No problem: no error line at all. Barrier: a canary through the module's logger reaches the capture."""
    probe = guard_name("probe_restore_state")
    interrupted(monkeypatch, False)
    monkeypatch.setattr(apply_module, "restore_state_problem", Recorder(None))
    barrier_logger = getattr(guard(), "logger", None) or get_logger(GUARD_MODULE)

    with capture_logs() as events:
        barrier_logger.info(LOG_CANARY)
        probe(data_dir)

    assert any(event.get("event") == LOG_CANARY for event in events), f"Barrier: the module's log reaches capture_logs: {events}"
    errors = [event for event in events if event.get("log_level") in ("error", "critical")]
    assert errors == [], f"a readable state logs no error: {errors}"


def test_a_real_unreadable_state_interrupts_and_its_content_never_reaches_the_log(monkeypatch, data_dir):
    """(a) With B's real hook: a state file that holds no state (a canary in it) → ``reason=invalid``; the probe
    returns True and logs its line; the canary is in no logged event. Barrier: B's hook reads it as ``invalid``."""
    path = restore_state_path(data_dir)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_text(f'{{"{STATE_CANARY}": "{STATE_CANARY}"}}', encoding="utf-8")
    path.chmod(0o600)
    problem = apply_module.restore_state_problem(data_dir)
    assert problem is not None and problem.reason == "invalid", f"Barrier: B's hook reads the canary file as invalid: {problem!r}"
    probe = guard_name("probe_restore_state")
    interrupted(monkeypatch, False)

    with capture_logs() as events:
        answer = probe(data_dir)

    assert answer is True, "a real unreadable state interrupts the restore"
    lines = _probe_lines(events)
    assert len(lines) == 1 and lines[0].get("reason") == "invalid", f"one line with reason=invalid: {events}"
    assert STATE_CANARY not in repr(events), f"the content of the state file reached the log: {events}"


# =============================================================================
# (b) The startup
# =============================================================================


def test_the_restore_state_step_comes_right_after_pending_restore_and_carries_no_skip():
    """(b) ``restore-state`` is the step right after ``pending-restore``, and nothing skips it."""
    print_section("B-33: the restore-state step")
    names = [step.name for step in app_lifespan.STARTUP_STEPS]
    assert "pending-restore" in names, f"Barrier: pending-restore is a startup step: {names}"
    assert "restore-state" in names, f"B-33: no startup step restore-state: {names}"
    assert names.index("restore-state") == names.index("pending-restore") + 1, f"restore-state comes right after pending-restore: {names}"
    assert getattr(_steps()["restore-state"], "skip_when", None) is None, "restore-state always runs"
    print_success("pending-restore → restore-state")


@pytest.mark.asyncio
@pytest.mark.parametrize(("problem", "expected"), [pytest.param("io", True, id="unreadable"), pytest.param(None, False, id="readable")])
async def test_the_restore_state_step_runs_the_probe_and_never_stops_the_start(monkeypatch, data_dir, problem, expected):
    """(b) The step ``restore-state``, alone, through ``run_startup_steps``: it asks B's hook about the instance's data
    directory and leaves ``restore_interrupted()`` at its answer; a problem never stops the start (a marker step after
    it runs)."""
    steps = _steps()
    if "restore-state" not in steps:
        pytest.fail("B-33: no startup step restore-state")
    interrupted(monkeypatch, not expected)
    asked = Recorder(apply_module.RestoreStateUnreadableError(problem) if problem else None)
    monkeypatch.setattr(apply_module, "restore_state_problem", asked)
    ran: list[str] = []

    await run_startup_steps((steps["restore-state"], Step("next", lambda: ran.append("next"))))

    assert asked.asked == [data_dir], f"the step asks about the instance's data directory once: {asked.asked}"
    assert guard_name("restore_interrupted")() is expected, f"after the step restore_interrupted() is {expected}"
    assert ran == ["next"], "the start goes on after restore-state"


def test_the_steps_kept_while_interrupted_carry_no_skip():
    """(b) ``database``, ``global-settings``, ``pending-restore``, ``restore-state``, ``restore-commit``, ``restore-owner``
    (H5-3), ``backup-leftovers``, ``serving-lock`` and ``idle-monitor`` are startup steps and nothing skips them."""
    steps = _steps()
    missing = [name for name in KEPT_WHEN_INTERRUPTED if name not in steps]
    assert missing == [], f"these kept steps are not in STARTUP_STEPS: {missing}"
    skipped = [name for name in KEPT_WHEN_INTERRUPTED if getattr(steps[name], "skip_when", None) is not None]
    assert skipped == [], f"these steps must keep running while interrupted: {skipped}"


@pytest.mark.parametrize(("value", "expected"), [pytest.param(True, True, id="interrupted"), pytest.param(False, False, id="not-interrupted")])
def test_the_skip_of_the_eight_steps_follows_the_interruption(monkeypatch, data_dir, value, expected):
    """(b) Outside the awaiting-restore mode, each of the eight ``skip_when()`` is ``restore_interrupted()`` at the
    moment of the call."""
    steps = _steps()
    missing = [name for name in SKIPPED_WHEN_INTERRUPTED if getattr(steps.get(name), "skip_when", None) is None]
    if missing:
        pytest.fail(f"B-33: these steps carry no skip_when: {missing}")
    interrupted(monkeypatch, value)
    answers = {name: steps[name].skip_when() for name in SKIPPED_WHEN_INTERRUPTED}
    assert answers == dict.fromkeys(SKIPPED_WHEN_INTERRUPTED, expected), f"interrupted={value}: {answers}"


@pytest.mark.asyncio
@pytest.mark.parametrize(("name", "function"), list(SKIPPED_WHEN_INTERRUPTED.items()), ids=list(SKIPPED_WHEN_INTERRUPTED))
async def test_while_interrupted_each_of_the_eight_steps_calls_nothing(monkeypatch, data_dir, name, function):
    """(b) The step ``name``, alone, through ``run_startup_steps``, the function it calls replaced by a recorder:
    while interrupted nothing is called; outside, once (barrier: the recorder is the step's own call)."""
    step = _steps().get(name)
    assert step is not None, f"Barrier: {name} is a startup step"
    interrupted(monkeypatch, False)
    calls: list[str] = []
    monkeypatch.setattr(app_lifespan, function, lambda *_args, **_kwargs: calls.append(name))
    monkeypatch.setenv("LIBREFOLIO_ADMIN_EMAIL", "b33-admin@example.test")
    await run_startup_steps((step,))
    assert calls == [name], f"Barrier: not interrupted, the step calls {function} once: {calls}"

    interrupted(monkeypatch, True)
    await run_startup_steps((step,))
    assert calls == [name], f"while interrupted the step {name} must call nothing: {calls}"

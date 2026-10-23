"""
The «awaiting restore» mode, its switch and the startup (LibreFolio 1.3, workstream H, lot H-62): contract L3 §6.

Under test, written by H-62 and missing today:

(a) ``backend.app.config.platform.awaiting_restore()``: ``LIBREFOLIO_AWAIT_RESTORE``, read at each call, with the
    values of ``LIBREFOLIO_BLOCKED`` (``instance_blocked()``): unset, blank, ``0``, ``false``, ``no``, ``off`` → False;
    ``1``, ``true``, ``yes``, ``on`` → True, in any case and stripped; any other value raises ``ValueError`` naming the
    variable.
(b) The startup configuration checks (``config_audit.log_configuration_audit``) stop the server on a value
    ``awaiting_restore()`` cannot read, before anything is logged, as they do for ``LIBREFOLIO_BLOCKED``; a readable
    value lets the start go on.
(c) ``lifecycle.Step`` gains ``skip_when: Callable[[], bool] | None = None``; ``run_startup_steps`` does not call a step
    whose ``skip_when()`` is true at the moment the step comes (read then, not when the step was built), and runs the
    others in order.
(d) ``app_lifespan.STARTUP_STEPS``: ``admin-bootstrap``, ``scheduler``, ``provider-prewarm``, ``market-holidays``,
    ``brim-parse-pool`` and ``stored-currencies`` carry a ``skip_when``, true in the mode and false outside it;
    ``database``, ``pending-restore``, ``restore-commit`` and ``idle-monitor`` keep running (pinned by the set). B-33
    (22/10): exactly eight steps carry a ``skip_when`` — those six, and ``post-migration-fixes`` and
    ``lone-transfer-legs``, which skip only while the restore is interrupted (false in the mode); all eight true while
    interrupted is in ``test_restore_guard.py``. Each of the six, run through ``run_startup_steps`` with the function it calls replaced by a recorder, calls
    nothing in the mode (so no ``/setup`` link is born with ``LIBREFOLIO_ADMIN_EMAIL`` set) and calls it once outside.

Every name of H-62 is read by the test that needs it, so the file collects and each test reports its own red.

Pure: no server, no database, no network, no file outside ``tmp_path``; every variable through ``monkeypatch``.
"""

from __future__ import annotations

import dataclasses
import importlib
from typing import Any

import pytest

from backend.app.services.platform import app_lifespan, config_audit, lifecycle
from backend.app.services.platform.lifecycle import Step, run_startup_steps
from backend.test_scripts.test_services import test_config_audit as audit
from backend.test_scripts.test_utils import print_section, print_success

AWAIT_VARIABLE = "LIBREFOLIO_AWAIT_RESTORE"
#: The six steps the mode skips (§6), and the function each one's ``run`` calls, a global of ``app_lifespan``.
SKIPPED_IN_THE_MODE = {
    "admin-bootstrap": "startup_admin_bootstrap",
    "scheduler": "_start_scheduler",
    "provider-prewarm": "_start_provider_prewarm",
    "market-holidays": "_start_market_holiday_prewarm",
    "brim-parse-pool": "_start_brim_parse_pool_prewarm",
    "stored-currencies": "_start_stored_currency_audit",
}
#: B-33: the steps that skip only while the restore is interrupted (``restore_guard.restore_interrupted()``), never for
#: the mode alone.
SKIPPED_ONLY_WHEN_INTERRUPTED = ("post-migration-fixes", "lone-transfer-legs")
#: Steps the mode keeps (§6): a guard that they are there and carry no skip.
KEPT_IN_THE_MODE = ("database", "pending-restore", "restore-commit", "idle-monitor")

_MISSING = object()


def awaiting_restore() -> Any:
    """``config.platform.awaiting_restore``, read by the test that needs it."""
    platform = importlib.import_module("backend.app.config.platform")
    value = getattr(platform, "awaiting_restore", _MISSING)
    if value is _MISSING:
        pytest.fail("H-62: backend.app.config.platform gives no awaiting_restore()")
    return value


def _set(monkeypatch: pytest.MonkeyPatch, value: str | None) -> None:
    if value is None:
        monkeypatch.delenv(AWAIT_VARIABLE, raising=False)
    else:
        monkeypatch.setenv(AWAIT_VARIABLE, value)


def _skip_when(step: Step) -> Any:
    return getattr(step, "skip_when", None)


# =============================================================================
# (a) awaiting_restore()
# =============================================================================


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(None, False, id="unset"),
        pytest.param("", False, id="empty"),
        pytest.param("   ", False, id="blank"),
        pytest.param("0", False, id="0"),
        pytest.param("false", False, id="false"),
        pytest.param("No", False, id="No"),
        pytest.param(" OFF ", False, id="OFF-stripped"),
        pytest.param("1", True, id="1"),
        pytest.param("true", True, id="true"),
        pytest.param("YES", True, id="YES"),
        pytest.param(" on\n", True, id="on-stripped"),
    ],
)
def test_awaiting_restore_reads_the_eight_words_of_the_block(monkeypatch, value, expected):
    """(a) The values of ``LIBREFOLIO_BLOCKED``: unset or blank is off; the four words of each side, in any case and
    stripped."""
    function = awaiting_restore()
    _set(monkeypatch, value)
    assert function() is expected, f"{AWAIT_VARIABLE}={value!r}: awaiting_restore() must be {expected}"


@pytest.mark.parametrize("value", ["2", "y", "n", "enabled", "awaiting", "true false", "-1"])
def test_awaiting_restore_raises_on_any_other_value_naming_the_variable(monkeypatch, value):
    """(a) Any other value is an error naming the variable, never a guess either way."""
    function = awaiting_restore()
    _set(monkeypatch, value)
    with pytest.raises(ValueError, match=AWAIT_VARIABLE):
        function()


def test_awaiting_restore_is_read_at_each_call(monkeypatch):
    """(a) Read at each call: a change of the variable shows at the next call."""
    function = awaiting_restore()
    _set(monkeypatch, "1")
    first = function()
    _set(monkeypatch, "0")
    assert (first, function()) == (True, False), "the variable is read at each call"


# =============================================================================
# (b) The startup checks stop on an unreadable value
# =============================================================================


@pytest.fixture
def configuration(monkeypatch, tmp_path) -> Any:
    """The configuration of ``test_config_audit.py`` (every check ok but the unset JWT secret), its logger recorded."""
    made = audit._configure(monkeypatch, tmp_path, production=False)
    made.set(JWT_SECRET=audit.GOOD_JWT_SECRET, LIBREFOLIO_INSTANCE_KEY=audit.GOOD_INSTANCE_KEY)
    monkeypatch.delenv(AWAIT_VARIABLE, raising=False)
    recorder = audit.LogRecorder()
    monkeypatch.setattr(config_audit, "logger", recorder)
    return recorder


@pytest.mark.parametrize("value", ["maybe", "2"])
def test_startup_stops_on_an_await_restore_value_that_cannot_be_read(configuration, monkeypatch, value):
    """(b) ``LIBREFOLIO_AWAIT_RESTORE`` that cannot be read stops the start, before anything is logged, naming the
    variable: the mode is never left to chance (as ``LIBREFOLIO_BLOCKED``)."""
    monkeypatch.setenv(AWAIT_VARIABLE, value)
    with pytest.raises(ValueError, match=AWAIT_VARIABLE):
        config_audit.log_configuration_audit()
    assert configuration.records == [], f"nothing is logged before the start is stopped: {configuration.records}"


@pytest.mark.parametrize("value", ["1", "off", ""])
def test_startup_goes_on_with_a_readable_await_restore_value(configuration, monkeypatch, value):
    """(b) Guard: a readable value never stops the start."""
    monkeypatch.setenv(AWAIT_VARIABLE, value)
    config_audit.log_configuration_audit()


# =============================================================================
# (c) Step.skip_when and run_startup_steps
# =============================================================================


def test_a_step_has_an_optional_skip_when_none_by_default():
    """(c) ``Step`` gains ``skip_when``, ``None`` by default: a step built as today runs as today."""
    fields = {field.name: field for field in dataclasses.fields(Step)}
    assert "skip_when" in fields, f"H-62: lifecycle.Step has no skip_when: {sorted(fields)}"
    assert fields["skip_when"].default is None, f"skip_when defaults to None: {fields['skip_when'].default!r}"
    assert Step("plain", lambda: None).skip_when is None


@pytest.mark.asyncio
async def test_run_startup_steps_skips_a_step_whose_skip_when_is_true_when_it_comes():
    """(c) ``run_startup_steps``: a step whose ``skip_when()`` is true is not called; one whose ``skip_when()`` is false,
    and one without, run, in order. ``skip_when`` is read when the step comes: a switch turned on by an earlier step
    skips a later one."""
    print_section("H-62 §6: Step.skip_when")
    if "skip_when" not in {field.name for field in dataclasses.fields(Step)}:
        pytest.fail("H-62: lifecycle.Step has no skip_when")
    ran: list[str] = []
    switch = {"on": False}
    steps = (
        Step("first", lambda: ran.append("first")),
        Step("skipped", lambda: ran.append("skipped"), skip_when=lambda: True),
        Step("kept", lambda: ran.append("kept"), skip_when=lambda: False),
        Step("turns-on", lambda: (ran.append("turns-on"), switch.__setitem__("on", True))),
        Step("late", lambda: ran.append("late"), skip_when=lambda: switch["on"]),
        Step("last", lambda: ran.append("last")),
    )
    await run_startup_steps(steps)

    assert ran == ["first", "kept", "turns-on", "last"], f"the skipped steps are not called, the others run in order: {ran}"
    assert lifecycle.current_step() is None, "no step is left named in progress"
    print_success(f"ran {ran}")


# =============================================================================
# (d) The six steps of the mode
# =============================================================================


def test_exactly_the_eight_steps_of_the_mode_and_of_the_interruption_carry_a_skip_when():
    """(d) In ``STARTUP_STEPS`` exactly eight steps carry a ``skip_when`` (B-33, 22/10): the six of §6 and the two that
    skip only while the restore is interrupted; the steps the mode keeps are there and carry none."""
    names = [step.name for step in app_lifespan.STARTUP_STEPS]
    with_skip = sorted(step.name for step in app_lifespan.STARTUP_STEPS if _skip_when(step) is not None)
    expected = sorted((*SKIPPED_IN_THE_MODE, *SKIPPED_ONLY_WHEN_INTERRUPTED))
    assert set(KEPT_IN_THE_MODE) <= set(names), f"Barrier: the kept steps are in STARTUP_STEPS: {names}"
    assert with_skip == expected, f"the steps with skip_when must be exactly {expected}: {with_skip}"


@pytest.mark.parametrize(("value", "expected"), [pytest.param("1", True, id="awaiting"), pytest.param(None, False, id="unset"), pytest.param("off", False, id="off")])
def test_the_skip_of_the_six_steps_follows_the_switch(monkeypatch, value, expected):
    """(d) Each of the six ``skip_when()`` is ``awaiting_restore()`` at the moment of the call."""
    steps = {step.name: step for step in app_lifespan.STARTUP_STEPS}
    missing = [name for name in SKIPPED_IN_THE_MODE if _skip_when(steps[name]) is None]
    if missing:
        pytest.fail(f"H-62: these steps carry no skip_when: {missing}")
    _set(monkeypatch, value)
    answers = {name: steps[name].skip_when() for name in SKIPPED_IN_THE_MODE}
    assert answers == dict.fromkeys(SKIPPED_IN_THE_MODE, expected), f"{AWAIT_VARIABLE}={value!r}: {answers}"


@pytest.mark.parametrize("value", [pytest.param("1", id="awaiting"), pytest.param(None, id="unset")])
def test_the_two_steps_of_the_interruption_never_skip_for_the_mode(monkeypatch, value):
    """(d, B-33) ``post-migration-fixes`` and ``lone-transfer-legs`` carry a ``skip_when`` that the mode alone never
    makes true: they skip only while the restore is interrupted (this process never probed it)."""
    steps = {step.name: step for step in app_lifespan.STARTUP_STEPS}
    missing = [name for name in SKIPPED_ONLY_WHEN_INTERRUPTED if _skip_when(steps[name]) is None]
    if missing:
        pytest.fail(f"B-33: these steps carry no skip_when: {missing}")
    _set(monkeypatch, value)
    answers = {name: steps[name].skip_when() for name in SKIPPED_ONLY_WHEN_INTERRUPTED}
    assert answers == dict.fromkeys(SKIPPED_ONLY_WHEN_INTERRUPTED, False), f"{AWAIT_VARIABLE}={value!r}: {answers}"


@pytest.mark.asyncio
@pytest.mark.parametrize(("name", "function"), list(SKIPPED_IN_THE_MODE.items()), ids=list(SKIPPED_IN_THE_MODE))
async def test_in_the_mode_each_of_the_six_steps_calls_nothing(monkeypatch, name, function):
    """(d) The step ``name``, alone, through ``run_startup_steps``, the function it calls replaced by a recorder: in the
    mode nothing is called (admin-bootstrap: no ``/setup`` link is born, whatever ``LIBREFOLIO_ADMIN_EMAIL`` says);
    outside it, once (barrier: the recorder is the step's own call)."""
    step = next(step for step in app_lifespan.STARTUP_STEPS if step.name == name)
    calls: list[str] = []
    monkeypatch.setattr(app_lifespan, function, lambda *_args, **_kwargs: calls.append(name))
    monkeypatch.setenv("LIBREFOLIO_ADMIN_EMAIL", "h62-admin@example.test")
    monkeypatch.delenv(AWAIT_VARIABLE, raising=False)
    await run_startup_steps((step,))
    assert calls == [name], f"Barrier: outside the mode the step calls {function} once: {calls}"

    monkeypatch.setenv(AWAIT_VARIABLE, "1")
    await run_startup_steps((step,))
    assert calls == [name], f"in the mode the step {name} must call nothing: {calls}"

"""``LIBREFOLIO_LOGIN_LIMIT``: the switch of the limit on failed sign-ins, and its configuration check (release 1.3, workstream A, lot A8a — F15, decision D-A5 and point 4 of 14/10).

The limit on failed sign-ins (``login_throttle``, pinned in ``test_login_throttle.py``) is on unless the operator turns
it off; turned off, the startup log and the admin's «Security» tab say so, and a value that is neither on nor off stops
the start. The contract pinned here:

C3. ``backend.app.config.accounts.login_limit_enabled() -> bool``, read at each call, in the style of
    ``registration_mode_override()``: unset or blank is ``True``; ``on`` / ``off`` in any case, spaces around, ``True``
    / ``False``; any other value — ``1``, ``true`` and ``yes``, which other switches accept, included — a ``ValueError``
    naming ``LIBREFOLIO_LOGIN_LIMIT`` and the value as ``_blank_to_none()`` reads it: stripped.
C4. ``backend.app.services.accounts.checks``: ``ACCOUNTS_CONFIG_CHECKS = (check_login_limit,)``, in the shape of E's
    ``EMAIL_CONFIG_CHECKS``. ``check_login_limit()`` is ``ConfigCheck("accounts.login_limit", "ok",
    "auth.checks.loginLimit.ok")`` while the limit is on (unset, blank, ``on``); a ``warning`` /
    ``auth.checks.loginLimit.off`` while it is off, with an English summary naming ``LIBREFOLIO_LOGIN_LIMIT=off``, one
    fixed text however ``off`` is written; an ``error`` / ``auth.checks.loginLimit.invalid`` for any other value, with
    ``detail == {"value": <the value, stripped>}``; it never raises. ``config_audit.CONFIG_CHECKS`` holds it, once, so
    ``run_config_checks()`` returns its result, once; each new module can be imported first (a fresh interpreter, as
    E's EMK-012). ``log_configuration_audit()`` stops the start on an unusable value — a ``ValueError`` naming the
    variable, raised before any check is logged: the validation sits next to ``admin_bootstrap_config()``, before the
    loop that logs the checks, as for an unusable ``LIBREFOLIO_ADMIN_*`` — and goes on with the limit off, logging the
    check's warning as it logs every check that is not ok.

The owner's answers of 17/10 are pinned as given: the stripped value in the detail and in the error (LC-004b), one
fixed summary for every spelling of ``off`` (LC-003), the stop before any check is logged (LC-008).

Guards, green today and to stay green: ``run_config_checks()`` returns whatever the variable holds; the startup audit
goes on with the limit on or off, and says nothing about the limit while it is on.

Pure: no database, no server, no network. An autouse fixture removes any ``LIBREFOLIO_LOGIN_LIMIT`` the lane inherited;
each test sets its own with ``monkeypatch``. ``run_config_checks()`` and the audit run with the platform isolated as
``test_config_audit.py`` and ``test_email_checks.py`` isolate it — test mode, the data directory in ``tmp_path`` with no
instance key yet, no JWT secret, no instance key, no block, cookie ``auto``, log level ``INFO``, profile ``selfhosted``
— and without any ``LIBREFOLIO_SMTP_*``, ``LIBREFOLIO_PUBLIC_URL`` or ``LIBREFOLIO_ADMIN_*``: every other check is ok
but the unset JWT secret (info), and nothing but ``LIBREFOLIO_LOGIN_LIMIT`` can stop the audit. ``config_audit``'s
logger is replaced by a recorder. The fresh interpreters run in test mode, their data directory in ``tmp_path``, without
``LIBREFOLIO_LOGIN_LIMIT``, bounded by a timeout that is never a wait.

Red until lot A8a: ``login_limit_enabled`` and ``backend/app/services/accounts/checks.py`` do not exist. Each test
reaches them in its own body (``getattr`` and ``importlib``), so each fails on its own with «red until A8a»; the reds of
the audit say what the audit did instead.
"""

from __future__ import annotations

import importlib
import inspect
import json
import os
import subprocess
import sys
import textwrap
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from backend.app.config import accounts
from backend.app.services.platform import config_audit
from backend.app.services.platform.config_audit import ConfigCheck
from backend.app.services.platform.instance_key import INSTANCE_KEY_FILE, instance_key_path
from backend.test_scripts.test_utils import print_section, print_success

LOGIN_LIMIT_VARIABLE = "LIBREFOLIO_LOGIN_LIMIT"
CHECKS_MODULE = "backend.app.services.accounts.checks"
THROTTLE_MODULE = "backend.app.services.accounts.login_throttle"
CONFIG_AUDIT_MODULE = "backend.app.services.platform.config_audit"
#: The names lot A8a adds in ``checks``.
CHECKS_NAMES = ("ACCOUNTS_CONFIG_CHECKS", "check_login_limit")
CHECK_ID = "accounts.login_limit"
OK_KEY = "auth.checks.loginLimit.ok"
OFF_KEY = "auth.checks.loginLimit.off"
INVALID_KEY = "auth.checks.loginLimit.invalid"
#: What the summary of the ``off`` warning names.
OFF_NAMED = "LIBREFOLIO_LOGIN_LIMIT=off"
#: The platform's own record of every isolated audit: the unset JWT secret, at info.
JWT_CHECK_ID = "platform.jwt_secret"

#: The limit on: the variable unset (``None``), empty, blank, or ``on`` however written.
ON_VALUES = [
    pytest.param(None, id="unset"),
    pytest.param("", id="empty"),
    pytest.param("   ", id="blank"),
    pytest.param("on", id="on"),
    pytest.param("ON", id="ON"),
    pytest.param("On", id="On"),
    pytest.param(" on ", id="spaces-around-on"),
    pytest.param("\ton\n", id="tab-and-newline-around-on"),
]
#: The limit off: ``off`` however written.
OFF_VALUES = [
    pytest.param("off", id="off"),
    pytest.param("OFF", id="OFF"),
    pytest.param("Off", id="Off"),
    pytest.param(" off ", id="spaces-around-off"),
    pytest.param("\toff\n", id="tab-and-newline-around-off"),
]
#: Neither on nor off. Written without spaces around, so the value set is the value read; none of them can appear by
#: chance in a message that names ``on`` and ``off``.
INVALID_VALUES = [
    pytest.param("maybe", id="maybe"),
    pytest.param("1", id="one"),
    pytest.param("0", id="zero"),
    pytest.param("true", id="true"),
    pytest.param("false", id="false"),
    pytest.param("yes", id="yes"),
    pytest.param("disabled", id="disabled"),
    pytest.param("onn", id="onn"),
    pytest.param("offf", id="offf"),
    pytest.param("o n", id="o-space-n"),
    pytest.param("on off", id="on-space-off"),
]
#: An invalid value with spaces and a tab around it, and that value as ``_blank_to_none()`` reads it. The tab is what
#: shows a message naming the value as written: no message names a value with a tab, written or escaped, by chance.
PADDED_INVALID = " \tmaybe\t "
PADDED_INVALID_READ = "maybe"

#: The working directory of the fresh interpreters: the project root, where ``import backend`` resolves.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
#: A bound for a fresh interpreter that hangs, never a wait.
FRESH_INTERPRETER_TIMEOUT_SECONDS = 300
FRESH_IMPORT_MARKER = "FRESH-IMPORT "
#: What a fresh interpreter runs: it imports the modules named on its command line, in that order, then reports the
#: names in ``ACCOUNTS_CONFIG_CHECKS``, how many times each of those very objects is in ``CONFIG_CHECKS``, and the ids
#: ``run_config_checks()`` returns for the login limit; ``preloaded`` proves that no watched module was there before.
FRESH_IMPORT = textwrap.dedent("""
    import importlib
    import json
    import sys

    watched = ("backend.app.services.accounts.checks", "backend.app.services.accounts.login_throttle", "backend.app.services.platform.config_audit")
    preloaded = [name for name in watched if name in sys.modules]
    for name in sys.argv[1:]:
        importlib.import_module(name)
    from backend.app.services.accounts.checks import ACCOUNTS_CONFIG_CHECKS
    from backend.app.services.platform.config_audit import CONFIG_CHECKS, run_config_checks

    report = {
        "preloaded": preloaded,
        "listed": [check.__name__ for check in ACCOUNTS_CONFIG_CHECKS],
        "in_config_checks": [sum(listed is check for listed in CONFIG_CHECKS) for check in ACCOUNTS_CONFIG_CHECKS],
        "ran": [result.check_id for result in run_config_checks() if result.check_id == "accounts.login_limit"],
    }
    print("FRESH-IMPORT " + json.dumps(report))
    """)


# =============================================================================
# FIXTURES AND HELPERS
# =============================================================================


@pytest.fixture(autouse=True)
def _no_inherited_login_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Any ``LIBREFOLIO_LOGIN_LIMIT`` the lane inherited is removed: a test sees only the value it sets itself."""
    monkeypatch.delenv(LOGIN_LIMIT_VARIABLE, raising=False)


def _isolate_platform(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """The platform's side of ``run_config_checks()`` and of the startup audit, isolated as ``test_config_audit.py``'s ``_configure`` and ``test_email_checks.py``'s ``platform`` isolate it, without email nor initial administrator either: only ``LIBREFOLIO_LOGIN_LIMIT`` can stop the audit, and the only other check that is not ok is the unset JWT secret (info). The data directory, verified to be the one the instance key is looked for in."""
    for variable in [name for name in os.environ if name.endswith("_FILE") and (name == "JWT_SECRET_FILE" or name.startswith("LIBREFOLIO_"))]:
        monkeypatch.delenv(variable)
    for variable in [name for name in os.environ if name.startswith(("LIBREFOLIO_SMTP_", "LIBREFOLIO_ADMIN_"))]:
        monkeypatch.delenv(variable)
    for variable in ("JWT_SECRET", "LIBREFOLIO_INSTANCE_KEY", "LIBREFOLIO_LOG_LEVEL", "LIBREFOLIO_DATA_DIR", "LIBREFOLIO_TEST_DATA_DIR", "LIBREFOLIO_BLOCKED", "LIBREFOLIO_DELETION_DATE", "LIBREFOLIO_PUBLIC_URL"):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "auto")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    # Set, not removed: a .env may name a profile, and the environment wins over it
    monkeypatch.setenv("LIBREFOLIO_PROFILE", "selfhosted")
    data_dir = (tmp_path / "data").resolve()
    assert instance_key_path() == data_dir / INSTANCE_KEY_FILE, f"the instance key must be looked for in the data directory of this test, not at {instance_key_path()}"
    return data_dir


@pytest.fixture
def platform(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    return _isolate_platform(monkeypatch, tmp_path)


class LogRecorder:
    """Stands in for ``config_audit``'s structlog logger, as in ``test_config_audit.py``: one ``(level, summary, fields)`` per call."""

    def __init__(self) -> None:
        self.records: list[tuple[str, str, dict]] = []

    def info(self, event: str, **fields) -> None:
        self.records.append(("info", event, fields))

    def warning(self, event: str, **fields) -> None:
        self.records.append(("warning", event, fields))

    def error(self, event: str, **fields) -> None:
        self.records.append(("error", event, fields))


def _record_audit(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str, dict]]:
    recorder = LogRecorder()
    monkeypatch.setattr(config_audit, "logger", recorder)
    return recorder.records


@pytest.fixture
def logged(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str, dict]]:
    """The records of the startup audit: ``config_audit.logger`` replaced by a recorder."""
    return _record_audit(monkeypatch)


def _set_login_limit(monkeypatch: pytest.MonkeyPatch, value: str | None) -> None:
    """``LIBREFOLIO_LOGIN_LIMIT=value``, or unset for ``None``."""
    if value is None:
        monkeypatch.delenv(LOGIN_LIMIT_VARIABLE, raising=False)
    else:
        monkeypatch.setenv(LOGIN_LIMIT_VARIABLE, value)


def _module_or_red(name: str) -> ModuleType:
    """The module ``name``; when it does not exist, the test fails as a red of lot A8a. A module that exists and cannot be imported raises as it is."""
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as exc:
        if exc.name != name:
            raise
        pytest.fail(f"red until A8a: {name} does not exist", pytrace=False)


def _checks_module() -> ModuleType:
    """``backend.app.services.accounts.checks`` holding the names of C4, or a red of lot A8a naming what is missing."""
    module = _module_or_red(CHECKS_MODULE)
    missing = [name for name in CHECKS_NAMES if not hasattr(module, name)]
    if missing:
        pytest.fail(f"red until A8a: {CHECKS_MODULE} has no {', '.join(missing)}", pytrace=False)
    return module


def _login_limit_enabled() -> Callable[[], bool]:
    """``backend.app.config.accounts.login_limit_enabled``, or a red of lot A8a."""
    enabled = getattr(accounts, "login_limit_enabled", None)
    if enabled is None:
        pytest.fail("red until A8a: backend.app.config.accounts has no login_limit_enabled", pytrace=False)
    return enabled


def _evaluate(check: Callable[[], ConfigCheck]) -> ConfigCheck:
    """What ``check()`` returns; a configuration check never raises, so an exception fails the test, naming it."""
    try:
        return check()
    except Exception as exc:
        pytest.fail(f"{check.__name__}() must never raise; with {LOGIN_LIMIT_VARIABLE}={os.environ.get(LOGIN_LIMIT_VARIABLE)!r} it raised {exc!r}", pytrace=False)


# =============================================================================
# H5-4: the owner's email change check, ``accounts.owner_email_change``
# =============================================================================

OWNER_CHECK_ID = "accounts.owner_email_change"
OWNER_KEY_PREFIX = "auth.checks.ownerEmailChange."
INSTANCE_OWNER_MODULE = "backend.app.services.accounts.instance_owner"
#: The three states ``instance_owner.startup_change_state()`` gives, and what the check makes of each: severity and key.
OWNER_STATES = [
    pytest.param(None, "ok", OWNER_KEY_PREFIX + "ok", id="none-ok"),
    pytest.param("pending", "info", OWNER_KEY_PREFIX + "pending", id="pending-info"),
    pytest.param("blocked", "warning", OWNER_KEY_PREFIX + "blocked", id="blocked-warning"),
]
#: Canaries the check must never show: an address and a user name, in the variable that names the owner.
OWNER_ADDRESS_CANARY = "h54-canary-owner@canary.example"
OWNER_NAME_CANARY = "h54-canary-owner-username"


def _owner_check() -> Callable[[], ConfigCheck]:
    """``checks.check_owner_email_change``, or a red of lot H5-4 naming it."""
    module = _module_or_red(CHECKS_MODULE)
    check = getattr(module, "check_owner_email_change", None)
    if check is None:
        pytest.fail(f"red until H5-4: {CHECKS_MODULE} has no check_owner_email_change", pytrace=False)
    return check


def _stand_in_for_state(monkeypatch: pytest.MonkeyPatch, state: Any) -> None:
    """``instance_owner.startup_change_state`` answers ``state`` — or raises it, when it is an exception — until the test ends.
    The check must read it through the module attribute at each call, or this patch never reaches it."""
    module = importlib.import_module(INSTANCE_OWNER_MODULE)

    def stand_in() -> Any:
        if isinstance(state, BaseException):
            raise state
        return state

    monkeypatch.setattr(module, "startup_change_state", stand_in)


def _owner_records(records: list[tuple[str, str, dict]]) -> list[tuple[str, str, dict]]:
    """The records of the audit about the owner's email change."""
    return [record for record in records if record[2].get("check") == OWNER_CHECK_ID]


def _login_limit_records(records: list[tuple[str, str, dict]]) -> list[tuple[str, str, dict]]:
    """The records of the audit about the login limit."""
    return [record for record in records if record[2].get("check") == CHECK_ID]


def _as_logged(result: ConfigCheck) -> tuple[str, str, dict]:
    """The record ``log_configuration_audit`` writes for a check that is not ok: its severity, its summary, its id and detail."""
    return (result.severity, result.summary, {"check": result.check_id, "detail": result.detail})


def _assert_the_audit_ran(records: list[tuple[str, str, dict]]) -> None:
    """Barrier: the audit reached its checks and the recorder hears it — the unset JWT secret is always logged here."""
    assert any(fields.get("check") == JWT_CHECK_ID for _, _, fields in records), f"barrier: the audit's record of the unset JWT secret must reach the recorder: {records}"


def _fresh_environment(tmp_path: Path) -> dict[str, str]:
    """This process's environment for a fresh interpreter: no ``LIBREFOLIO_LOGIN_LIMIT``, ``LIBREFOLIO_SMTP_*`` nor ``LIBREFOLIO_PUBLIC_URL``, test mode, its data directory in ``tmp_path``, the project root importable."""
    environment = {name: value for name, value in os.environ.items() if name not in (LOGIN_LIMIT_VARIABLE, "LIBREFOLIO_PUBLIC_URL") and not name.startswith("LIBREFOLIO_SMTP_")}
    environment["LIBREFOLIO_TEST_MODE"] = "1"
    environment["LIBREFOLIO_TEST_DATA_DIR"] = str(tmp_path / "data")
    environment["PYTHONPATH"] = os.pathsep.join(filter(None, [str(PROJECT_ROOT), environment.get("PYTHONPATH")]))
    return environment


# =============================================================================
# C3. login_limit_enabled()
# =============================================================================


# red until A8a
@pytest.mark.parametrize("value", ON_VALUES)
def test_unset_blank_or_on_is_the_limit_on(monkeypatch: pytest.MonkeyPatch, value: str | None) -> None:
    """LE-001 — C3: unset, empty, blank, and ``on`` in any case with spaces around: ``True``, the bool."""
    print_section(f"LE-001: {LOGIN_LIMIT_VARIABLE}={value!r}")
    enabled = _login_limit_enabled()
    _set_login_limit(monkeypatch, value)

    result = enabled()

    assert result is True, f"{LOGIN_LIMIT_VARIABLE}={value!r}: login_limit_enabled() must be True, not {result!r}"
    print_success("on")


# red until A8a
@pytest.mark.parametrize("value", OFF_VALUES)
def test_off_however_written_is_the_limit_off(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    """LE-002 — C3: ``off`` in any case with spaces around: ``False``, the bool."""
    print_section(f"LE-002: {LOGIN_LIMIT_VARIABLE}={value!r}")
    enabled = _login_limit_enabled()
    monkeypatch.setenv(LOGIN_LIMIT_VARIABLE, value)

    result = enabled()

    assert result is False, f"{LOGIN_LIMIT_VARIABLE}={value!r}: login_limit_enabled() must be False, not {result!r}"
    print_success("off")


# red until A8a
@pytest.mark.parametrize("value", INVALID_VALUES)
def test_any_other_value_is_a_value_error_naming_the_variable_and_the_value(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    """LE-003 — C3: neither on nor off — ``1``, ``true`` or ``yes`` included — is a ``ValueError`` whose message names ``LIBREFOLIO_LOGIN_LIMIT`` and the value."""
    print_section(f"LE-003: {LOGIN_LIMIT_VARIABLE}={value!r}")
    enabled = _login_limit_enabled()
    monkeypatch.setenv(LOGIN_LIMIT_VARIABLE, value)

    with pytest.raises(ValueError) as raised:
        enabled()

    message = str(raised.value)
    assert LOGIN_LIMIT_VARIABLE in message and value in message, f"the error must name {LOGIN_LIMIT_VARIABLE} and {value!r}: {message!r}"
    print_success(message)


# red until A8a
def test_the_variable_is_read_at_each_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """LE-004 — C3: one function, the variable changed between its calls — ``off``, ``on``, a value neither, unset, `` OFF `` —: ``False``, ``True``, a ``ValueError``, ``True``, ``False``. Nothing is remembered from one call to the next."""
    print_section("LE-004: read at each call")
    enabled = _login_limit_enabled()
    seen: list[object] = []

    for value in ("off", "on", "maybe", None, " OFF "):
        _set_login_limit(monkeypatch, value)
        try:
            seen.append(enabled())
        except ValueError:
            seen.append(ValueError)

    assert seen == [False, True, ValueError, True, False], f"login_limit_enabled() must read {LOGIN_LIMIT_VARIABLE} at each call: {seen}"
    print_success("read at each call")


# =============================================================================
# C4. check_login_limit() AND ACCOUNTS_CONFIG_CHECKS
# =============================================================================


# red until A8a
def test_accounts_config_checks_is_the_login_limit_check_alone() -> None:
    """LC-001 — C4, H5-4: ``ACCOUNTS_CONFIG_CHECKS`` is a tuple holding ``check_login_limit`` then ``check_owner_email_change`` (H5-4) and nothing else, as E's ``EMAIL_CONFIG_CHECKS`` holds its checks."""
    print_section("LC-001: ACCOUNTS_CONFIG_CHECKS")
    checks = _checks_module()
    owner_check = _owner_check()

    listed = checks.ACCOUNTS_CONFIG_CHECKS

    assert isinstance(listed, tuple) and listed == (checks.check_login_limit, owner_check), f"ACCOUNTS_CONFIG_CHECKS must be (check_login_limit, check_owner_email_change): {listed!r}"
    print_success("(check_login_limit, check_owner_email_change)")


# red until A8a
@pytest.mark.parametrize("value", ON_VALUES)
def test_the_check_is_ok_while_the_limit_is_on(monkeypatch: pytest.MonkeyPatch, value: str | None) -> None:
    """LC-002 — C4: the limit on — unset, empty, blank, ``on`` however written —: exactly ``ConfigCheck("accounts.login_limit", "ok", "auth.checks.loginLimit.ok")``, no detail, no summary."""
    print_section(f"LC-002: check_login_limit with {LOGIN_LIMIT_VARIABLE}={value!r}")
    check = _checks_module().check_login_limit
    _set_login_limit(monkeypatch, value)

    result = _evaluate(check)

    assert result == ConfigCheck(CHECK_ID, "ok", OK_KEY), f"{LOGIN_LIMIT_VARIABLE}={value!r}: expected ok / {OK_KEY}, got {result}"
    print_success(f"{result.severity} {result.i18n_key}")


# red until A8a
@pytest.mark.parametrize("value", OFF_VALUES)
def test_the_check_warns_while_the_limit_is_off(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    """LC-003 — C4 and the owner's answer 2 of 17/10: the limit off, however written: a ``warning`` of ``accounts.login_limit`` with the key ``auth.checks.loginLimit.off``, an English summary for the log naming ``LIBREFOLIO_LOGIN_LIMIT=off`` — one fixed text, the very summary of a plain ``off``, never an echo of the spelling —, and a detail whose values are strings or integers, as every i18n parameter."""
    print_section(f"LC-003: check_login_limit with {LOGIN_LIMIT_VARIABLE}={value!r}")
    check = _checks_module().check_login_limit
    monkeypatch.setenv(LOGIN_LIMIT_VARIABLE, "off")
    plain = _evaluate(check)
    monkeypatch.setenv(LOGIN_LIMIT_VARIABLE, value)

    result = _evaluate(check)

    assert (result.check_id, result.severity, result.i18n_key) == (CHECK_ID, "warning", OFF_KEY), f"{LOGIN_LIMIT_VARIABLE}={value!r}: expected a warning / {OFF_KEY}, got {result}"
    assert OFF_NAMED in result.summary, f"the summary for the log must name {OFF_NAMED}: {result.summary!r}"
    assert result.summary == plain.summary, f"the summary is one fixed text for every spelling of off: {result.summary!r} for {value!r}, {plain.summary!r} for 'off'"
    assert all(isinstance(parameter, str | int) for parameter in result.detail.values()), f"the parameters of an i18n message are strings or integers: {result.detail}"
    print_success(result.summary)


# red until A8a
@pytest.mark.parametrize("value", INVALID_VALUES)
def test_the_check_is_an_error_holding_the_value_and_never_raises(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    """LC-004 — C4: a value neither on nor off: the check returns — it never raises — an ``error`` of ``accounts.login_limit`` with the key ``auth.checks.loginLimit.invalid`` and ``detail == {"value": <the value>}``."""
    print_section(f"LC-004: check_login_limit with {LOGIN_LIMIT_VARIABLE}={value!r}")
    check = _checks_module().check_login_limit
    monkeypatch.setenv(LOGIN_LIMIT_VARIABLE, value)

    result = _evaluate(check)

    actual = (result.check_id, result.severity, result.i18n_key, result.detail)
    assert actual == (CHECK_ID, "error", INVALID_KEY, {"value": value}), f"{LOGIN_LIMIT_VARIABLE}={value!r}: expected an error / {INVALID_KEY} with the value as detail, got {result}"
    print_success(f"{result.severity} {result.detail}")


# red until A8a
def test_a_padded_invalid_value_is_held_and_named_stripped(monkeypatch: pytest.MonkeyPatch) -> None:
    """LC-004b — C3 and C4, the owner's answer 1 of 17/10: an invalid value with spaces and a tab around it is read as ``_blank_to_none()`` reads it, stripped. The check's ``detail == {"value": "maybe"}``, and the ``ValueError`` of ``login_limit_enabled()`` names ``maybe`` without its padding: the tab is nowhere in the message, neither as written nor escaped."""
    print_section(f"LC-004b: {LOGIN_LIMIT_VARIABLE}={PADDED_INVALID!r}")
    check = _checks_module().check_login_limit
    enabled = _login_limit_enabled()
    monkeypatch.setenv(LOGIN_LIMIT_VARIABLE, PADDED_INVALID)

    result = _evaluate(check)
    with pytest.raises(ValueError) as raised:
        enabled()

    actual = (result.check_id, result.severity, result.i18n_key, result.detail)
    assert actual == (CHECK_ID, "error", INVALID_KEY, {"value": PADDED_INVALID_READ}), f"{LOGIN_LIMIT_VARIABLE}={PADDED_INVALID!r}: expected an error / {INVALID_KEY} holding the value stripped, {PADDED_INVALID_READ!r}, got {result}"
    message = str(raised.value)
    assert LOGIN_LIMIT_VARIABLE in message and PADDED_INVALID_READ in message, f"the error must name {LOGIN_LIMIT_VARIABLE} and {PADDED_INVALID_READ!r}: {message!r}"
    assert "\t" not in message and "\\t" not in message, f"the error must name the value stripped, as it is read, not as written: {message!r}"
    print_success(f"{result.detail}; {message}")


# =============================================================================
# C4. IN THE PLATFORM'S CONFIG_CHECKS
# =============================================================================


# red until A8a
@pytest.mark.parametrize("value", [pytest.param(None, id="unset-ok"), pytest.param("off", id="off-warning"), pytest.param("maybe", id="invalid-error")])
def test_run_config_checks_carries_the_login_limit_check_once(platform: Path, monkeypatch: pytest.MonkeyPatch, value: str | None) -> None:
    """LC-005 — C4: whatever the variable holds — on, off, neither —, ``run_config_checks()`` returns one ``accounts.login_limit`` result, equal to what ``check_login_limit()`` returns alone; ``config_audit.CONFIG_CHECKS`` holds the very ``check_login_limit`` of the module, once."""
    print_section(f"LC-005: run_config_checks with {LOGIN_LIMIT_VARIABLE}={value!r}")
    _set_login_limit(monkeypatch, value)

    results = config_audit.run_config_checks()

    ours = [result for result in results if result.check_id == CHECK_ID]
    assert len(ours) == 1, f"red until A8a: run_config_checks() must return one {CHECK_ID} result; it returned {[result.check_id for result in results]}"
    check = _checks_module().check_login_limit
    assert config_audit.CONFIG_CHECKS.count(check) == 1, f"CONFIG_CHECKS must hold check_login_limit once: {[listed.__name__ for listed in config_audit.CONFIG_CHECKS]}"
    assert ours == [_evaluate(check)], "run_config_checks() must carry what check_login_limit() returns on its own"
    print_success(f"{ours[0].check_id}={ours[0].severity}")


# guard
@pytest.mark.parametrize("value", [None, "", "on", "off", "maybe"], ids=["unset", "empty", "on", "off", "invalid"])
def test_guard_run_config_checks_returns_whatever_the_variable_holds(platform: Path, monkeypatch: pytest.MonkeyPatch, value: str | None) -> None:
    """LC-006 — guard, green today and to stay green: whatever ``LIBREFOLIO_LOGIN_LIMIT`` holds, ``run_config_checks()`` returns its list of ``ConfigCheck``, for the «Security» tab — a configuration check never raises, the login limit's included."""
    print_section(f"LC-006: run_config_checks returns with {LOGIN_LIMIT_VARIABLE}={value!r} (guard)")
    _set_login_limit(monkeypatch, value)

    results = config_audit.run_config_checks()

    assert results and all(isinstance(result, ConfigCheck) for result in results), f"run_config_checks() must return its checks: {results!r}"
    print_success(f"{len(results)} checks")


FRESH_ORDERS = [
    pytest.param((CHECKS_MODULE, CONFIG_AUDIT_MODULE), id="checks-then-config-audit"),
    pytest.param((CONFIG_AUDIT_MODULE, CHECKS_MODULE), id="config-audit-then-checks"),
    pytest.param((THROTTLE_MODULE, CONFIG_AUDIT_MODULE), id="login-throttle-first"),
]


# red until A8a
@pytest.mark.parametrize("order", FRESH_ORDERS)
def test_each_new_module_can_be_imported_first_in_a_fresh_interpreter(tmp_path: Path, order: tuple[str, ...]) -> None:
    """LC-007 — C4, in the shape of E's EMK-012: a fresh interpreter — without ``LIBREFOLIO_LOGIN_LIMIT``, test mode, its data directory in ``tmp_path`` — imports ``order`` in that order and exits 0; it reports ``ACCOUNTS_CONFIG_CHECKS`` as ``check_login_limit`` then ``check_owner_email_change`` (H5-4), each of those very objects once in ``CONFIG_CHECKS``, and runs the login limit's: ``accounts.login_limit``. ``checks`` meets ``config_audit`` half-initialised in neither order.

    First, in this process, the modules of the order exist (red until A8a, with a message rather than a traceback from
    the child). Barrier: no watched module was loaded before the first import, so the order is the one the case names.
    """
    print_section(f"LC-007: {' then '.join(order)}")
    _checks_module()
    for name in order:
        _module_or_red(name)

    completed = subprocess.run([sys.executable, "-c", FRESH_IMPORT, *order], cwd=PROJECT_ROOT, env=_fresh_environment(tmp_path), capture_output=True, text=True, timeout=FRESH_INTERPRETER_TIMEOUT_SECONDS, check=False)

    assert completed.returncode == 0, f"importing {' then '.join(order)} in a fresh interpreter failed with {completed.returncode}:\n{completed.stderr[-4000:]}"
    reports = [line.removeprefix(FRESH_IMPORT_MARKER) for line in completed.stdout.splitlines() if line.startswith(FRESH_IMPORT_MARKER)]
    assert len(reports) == 1, f"the fresh interpreter must report once: {completed.stdout[-4000:]}"
    report = json.loads(reports[0])
    assert report["preloaded"] == [], f"barrier: a fresh interpreter loads no watched module before the first import: {report['preloaded']}"
    assert report == {"preloaded": [], "listed": ["check_login_limit", "check_owner_email_change"], "in_config_checks": [1, 1], "ran": [CHECK_ID]}, f"{' then '.join(order)} (H5-4: the owner's check is listed after the login limit's): {report}"
    print_success(f"{' then '.join(order)}: {report['ran']}")


# =============================================================================
# C4. THE STARTUP AUDIT
# =============================================================================


# red until A8a
@pytest.mark.parametrize("value", ["maybe", "false", "1"], ids=["maybe", "false", "one"])
def test_the_startup_audit_stops_on_a_value_neither_on_nor_off_before_any_check_is_logged(platform: Path, logged: list, monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    """LC-008 — C4 and the owner's answer 4 of 17/10: ``LIBREFOLIO_LOGIN_LIMIT`` neither on nor off: ``log_configuration_audit()`` raises a ``ValueError`` naming the variable before any check is logged, and the server does not start — as with an unusable ``LIBREFOLIO_ADMIN_*``, whose validation it sits next to, before the loop that logs the checks. Nothing else can stop the audit here: the platform is isolated.

    Barrier first: the same audit with the variable unset reaches the recorder (the unset JWT secret), so «nothing
    logged» after the stop is an absence, not a deaf recorder.
    """
    print_section(f"LC-008: the startup audit with {LOGIN_LIMIT_VARIABLE}={value!r}")
    config_audit.log_configuration_audit()
    _assert_the_audit_ran(logged)
    logged.clear()
    monkeypatch.setenv(LOGIN_LIMIT_VARIABLE, value)

    try:
        config_audit.log_configuration_audit()
    except ValueError as exc:
        raised = exc
    else:
        pytest.fail(f"red until A8a: log_configuration_audit() went on with {LOGIN_LIMIT_VARIABLE}={value!r}; a value neither on nor off must stop the start with a ValueError naming the variable, before any check is logged", pytrace=False)

    assert LOGIN_LIMIT_VARIABLE in str(raised), f"the error that stops the start must name {LOGIN_LIMIT_VARIABLE}: {raised!r}"
    assert logged == [], f"nothing is logged before the start is stopped: {logged}"
    print_success(str(raised))


# guard
@pytest.mark.parametrize("value", [None, "", "on", " ON ", "off", " Off "], ids=["unset", "empty", "on", "spaces-around-ON", "off", "spaces-around-Off"])
def test_guard_the_startup_audit_goes_on_with_the_limit_on_or_off(platform: Path, logged: list, monkeypatch: pytest.MonkeyPatch, value: str | None) -> None:
    """LC-009 — guard, green today and to stay green: the limit on or off, however written, ``log_configuration_audit()`` returns — the start goes on — after running its checks (the barrier: their records reach the recorder)."""
    print_section(f"LC-009: the startup audit goes on with {LOGIN_LIMIT_VARIABLE}={value!r} (guard)")
    _set_login_limit(monkeypatch, value)

    returned = config_audit.log_configuration_audit()

    assert returned is None
    _assert_the_audit_ran(logged)
    print_success("the start goes on")


# red until A8a
@pytest.mark.parametrize("value", ["off", " OFF "], ids=["off", "spaces-around-OFF"])
def test_the_startup_audit_warns_that_the_limit_is_off(platform: Path, logged: list, monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    """LC-010 — C4: the limit off: the startup audit logs one record about ``accounts.login_limit``, the ``warning`` of the check with its summary and detail — the check's own result, so the check is what spoke."""
    print_section(f"LC-010: the startup log with {LOGIN_LIMIT_VARIABLE}={value!r}")
    monkeypatch.setenv(LOGIN_LIMIT_VARIABLE, value)

    config_audit.log_configuration_audit()

    _assert_the_audit_ran(logged)
    records = _login_limit_records(logged)
    assert len(records) == 1 and records[0][0] == "warning", f"red until A8a: with {LOGIN_LIMIT_VARIABLE}={value!r} the startup audit must log one warning about {CHECK_ID}; it logged {records}"
    expected = _evaluate(_checks_module().check_login_limit)
    assert records == [_as_logged(expected)], f"the record must be the check's own result, {_as_logged(expected)}: {records}"
    print_success(f"warning: {expected.summary}")


# guard
@pytest.mark.parametrize("value", [None, "", "on"], ids=["unset", "empty", "on"])
def test_guard_the_startup_audit_says_nothing_about_the_limit_while_it_is_on(platform: Path, logged: list, monkeypatch: pytest.MonkeyPatch, value: str | None) -> None:
    """LC-011 — guard, green today and to stay green: the limit on, the startup audit logs nothing about ``accounts.login_limit`` — an ok check is not logged.

    Barrier first: the audit's record of the unset JWT secret reached the recorder, so «nothing about the limit» is an
    absence, not a deaf recorder.
    """
    print_section(f"LC-011: nothing logged about the limit with {LOGIN_LIMIT_VARIABLE}={value!r} (guard)")
    _set_login_limit(monkeypatch, value)

    config_audit.log_configuration_audit()

    _assert_the_audit_ran(logged)
    assert _login_limit_records(logged) == [], f"the limit on is the default: nothing to log about it: {logged}"
    print_success("nothing logged about the limit")


# =============================================================================
# H5-4. check_owner_email_change() — the owner's address change, from memory
# =============================================================================
#
# Contract (lot H5-4, A's request A5-1b): ``checks.CHECK_OWNER_EMAIL_CHANGE = "accounts.owner_email_change"`` and
# ``check_owner_email_change() -> ConfigCheck``, listed in ``ACCOUNTS_CONFIG_CHECKS`` after ``check_login_limit``. It reads
# ``instance_owner.startup_change_state()`` at each call (memory only, sync, no database): None is ``ok`` /
# ``auth.checks.ownerEmailChange.ok``; ``"pending"`` is ``info`` / ``...pending``; ``"blocked"`` is ``warning`` /
# ``...blocked``. No detail; a fixed English summary at most, with no address and no name. It never raises: a state
# function that raises gives ``ok``. The startup audit logs the pending and blocked states only.


# red until H5-4
def test_the_owner_check_has_its_id_constant() -> None:
    """OE-001 — H5-4: ``checks.CHECK_OWNER_EMAIL_CHANGE`` is ``"accounts.owner_email_change"``, as ``CHECK_LOGIN_LIMIT`` names the login limit's."""
    print_section("OE-001: CHECK_OWNER_EMAIL_CHANGE")
    module = _module_or_red(CHECKS_MODULE)

    value = getattr(module, "CHECK_OWNER_EMAIL_CHANGE", None)

    assert value == OWNER_CHECK_ID, f"red until H5-4: {CHECKS_MODULE}.CHECK_OWNER_EMAIL_CHANGE must be {OWNER_CHECK_ID!r}: {value!r}"
    print_success(value)


# red until H5-4
@pytest.mark.parametrize(("state", "severity", "key"), OWNER_STATES)
def test_the_owner_check_follows_the_startup_state(monkeypatch: pytest.MonkeyPatch, state: str | None, severity: str, key: str) -> None:
    """OE-002 — H5-4: None is exactly ``ConfigCheck("accounts.owner_email_change", "ok", "auth.checks.ownerEmailChange.ok")`` (no detail, no summary); ``pending`` is ``info`` with ``...pending``; ``blocked`` is ``warning`` with ``...blocked``; no detail for any of them. A summary, when there is one, is a fixed English text."""
    print_section(f"OE-002: check_owner_email_change with the state {state!r}")
    check = _owner_check()
    _stand_in_for_state(monkeypatch, state)

    result = _evaluate(check)

    assert (result.check_id, result.severity, result.i18n_key) == (OWNER_CHECK_ID, severity, key), f"state {state!r}: expected {OWNER_CHECK_ID} / {severity} / {key}, got {result}"
    assert result.detail == {}, f"the message has no parameter: {result}"
    if state is None:
        assert result == ConfigCheck(OWNER_CHECK_ID, "ok", OWNER_KEY_PREFIX + "ok"), f"ok is the bare check: {result}"
    else:
        assert isinstance(result.summary, str) and result.summary, f"a state worth logging has an English summary for the log: {result}"
    print_success(f"{result.severity} {result.i18n_key}")


# red until H5-4
@pytest.mark.parametrize("state", ["pending", "blocked"])
def test_the_owner_check_never_shows_an_address_or_a_name(monkeypatch: pytest.MonkeyPatch, state: str) -> None:
    """OE-003 — H5-4: no address and no user name in the result. The variable that names the owner holds an address and the environment a name, both canaries; neither is in any field of the result, and the summary holds no ``@`` at all. Barrier: the result is the state's, not ``ok`` (so the check really ran its branch)."""
    print_section(f"OE-003: no address in the {state} check")
    check = _owner_check()
    monkeypatch.setenv("LIBREFOLIO_ADMIN_EMAIL", OWNER_ADDRESS_CANARY)
    monkeypatch.setenv("LIBREFOLIO_ADMIN_USERNAME", OWNER_NAME_CANARY)
    _stand_in_for_state(monkeypatch, state)

    result = _evaluate(check)

    assert result.severity != "ok" and result.i18n_key.endswith(state), f"barrier: the check answered the state {state!r}: {result}"
    shown = repr(result)
    assert OWNER_ADDRESS_CANARY not in shown and OWNER_NAME_CANARY not in shown, f"the result shows the owner's address or name: {result}"
    assert "@" not in shown, f"no address of any kind in the result: {result}"
    print_success("no address, no name")


# red until H5-4
def test_the_owner_check_reads_the_state_at_each_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """OE-004 — H5-4: ``startup_change_state()`` is read at each call, through the module: a state that changes between two calls (the owner confirmed, a restart found a conflict) changes the result at the next call, none is cached."""
    print_section("OE-004: read at each call")
    check = _owner_check()
    module = importlib.import_module(INSTANCE_OWNER_MODULE)
    states = iter([None, "pending", "blocked", "pending", None])
    monkeypatch.setattr(module, "startup_change_state", lambda: next(states))

    severities = [_evaluate(check).severity for _ in range(5)]

    assert severities == ["ok", "info", "warning", "info", "ok"], f"each call reads the state anew: {severities}"
    print_success(str(severities))


# red until H5-4
@pytest.mark.parametrize("error", [RuntimeError("memory gone"), ValueError("not a state"), OSError("nope")], ids=["runtime", "value", "os"])
def test_the_owner_check_never_raises_and_is_ok_when_the_state_cannot_be_read(monkeypatch: pytest.MonkeyPatch, error: Exception) -> None:
    """OE-005 — H5-4: a configuration check never raises: a state function that raises gives severity ``ok`` (nothing is known to wait), the check's id and no detail. A bare ``_evaluate`` would fail the test on an exception."""
    print_section(f"OE-005: the state function raises {error!r}")
    check = _owner_check()
    _stand_in_for_state(monkeypatch, error)

    result = _evaluate(check)

    assert result.check_id == OWNER_CHECK_ID and result.severity == "ok", f"a state that cannot be read is ok, never an exception: {result}"
    assert result.detail == {}, f"no detail: {result}"
    print_success("ok, no exception")


# red until H5-4
def test_the_owner_check_is_synchronous_and_reads_no_database(monkeypatch: pytest.MonkeyPatch) -> None:
    """OE-006 — H5-4: ``check_owner_email_change`` is a plain function (the checks are called synchronously by ``run_config_checks()``), and it needs no database: with ``owner_change_status`` (the database reader) made to fail, the result is still the memory state's."""
    print_section("OE-006: synchronous, memory only")
    check = _owner_check()
    module = importlib.import_module(INSTANCE_OWNER_MODULE)

    async def database_reader(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("the check must not read the database: owner_change_status was called")

    monkeypatch.setattr(module, "owner_change_status", database_reader)
    _stand_in_for_state(monkeypatch, "blocked")

    assert not inspect.iscoroutinefunction(check), "a configuration check is synchronous"
    result = _evaluate(check)

    assert isinstance(result, ConfigCheck) and result.severity == "warning", f"the memory state decides: {result}"
    print_success("sync, no database")


# red until H5-4
@pytest.mark.parametrize(("state", "severity", "key"), OWNER_STATES)
def test_run_config_checks_carries_the_owner_check_once_right_after_the_login_limit(platform: Path, monkeypatch: pytest.MonkeyPatch, state: str | None, severity: str, key: str) -> None:
    """OE-007 — H5-4: whatever the state, ``run_config_checks()`` returns one ``accounts.owner_email_change`` result, equal to the check alone and right after ``accounts.login_limit`` in the list; ``config_audit.CONFIG_CHECKS`` holds the very ``check_owner_email_change`` once, right after ``check_login_limit``; with the state patched, its severity and key are the state's."""
    print_section(f"OE-007: run_config_checks with the state {state!r}")
    check = _owner_check()
    _stand_in_for_state(monkeypatch, state)

    results = config_audit.run_config_checks()

    ids = [result.check_id for result in results]
    assert ids.count(OWNER_CHECK_ID) == 1, f"red until H5-4: run_config_checks() must return one {OWNER_CHECK_ID} result: {ids}"
    assert ids.index(OWNER_CHECK_ID) == ids.index(CHECK_ID) + 1, f"{OWNER_CHECK_ID} comes right after {CHECK_ID}: {ids}"
    assert config_audit.CONFIG_CHECKS.count(check) == 1, f"CONFIG_CHECKS must hold check_owner_email_change once: {[listed.__name__ for listed in config_audit.CONFIG_CHECKS]}"
    names = [listed.__name__ for listed in config_audit.CONFIG_CHECKS]
    assert names.index("check_owner_email_change") == names.index("check_login_limit") + 1, f"CONFIG_CHECKS lists the owner's check right after the login limit's: {names}"
    ours = results[ids.index(OWNER_CHECK_ID)]
    assert ours == _evaluate(check) and (ours.severity, ours.i18n_key) == (severity, key), f"run_config_checks() carries what the check returns on its own: {ours}"
    print_success(f"{ours.check_id}={ours.severity}")


# red until H5-4
@pytest.mark.parametrize(("state", "severity"), [pytest.param("pending", "info", id="pending-info"), pytest.param("blocked", "warning", id="blocked-warning")])
def test_the_startup_audit_logs_a_pending_or_blocked_change(platform: Path, logged: list, monkeypatch: pytest.MonkeyPatch, state: str, severity: str) -> None:
    """OE-008 — H5-4, in the shape of LC-010: a change that waits (``pending``, info) or is stuck (``blocked``, warning): the startup audit logs one record about ``accounts.owner_email_change`` at the check's own severity, with its summary, id and detail, and no address."""
    print_section(f"OE-008: the startup log with the state {state!r}")
    check = _owner_check()
    _stand_in_for_state(monkeypatch, state)

    config_audit.log_configuration_audit()

    _assert_the_audit_ran(logged)
    records = _owner_records(logged)
    assert len(records) == 1 and records[0][0] == severity, f"red until H5-4: with the state {state!r} the startup audit must log one {severity} about {OWNER_CHECK_ID}; it logged {records}"
    expected = _evaluate(check)
    assert records == [_as_logged(expected)], f"the record must be the check's own result, {_as_logged(expected)}: {records}"
    assert "@" not in repr(records), f"no address in the record: {records}"
    print_success(f"{severity}: {expected.summary}")


# guard-shaped, red until H5-4 only for the missing check
def test_the_startup_audit_says_nothing_while_no_change_waits(platform: Path, logged: list, monkeypatch: pytest.MonkeyPatch) -> None:
    """OE-009 — H5-4, in the shape of LC-011: no change waiting (state None), the startup audit logs nothing about ``accounts.owner_email_change`` — an ok check is not logged. Barrier: the check exists and is ok on its own, and the audit's record of the unset JWT secret reached the recorder."""
    print_section("OE-009: nothing logged while no change waits")
    check = _owner_check()
    _stand_in_for_state(monkeypatch, None)
    assert _evaluate(check).severity == "ok", "barrier: the check is ok with no change waiting"

    config_audit.log_configuration_audit()

    _assert_the_audit_ran(logged)
    assert _owner_records(logged) == [], f"nothing waits: nothing to log about it: {logged}"
    print_success("nothing logged")

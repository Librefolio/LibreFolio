"""
Instance backup, its configuration checks (workstream B, lot B-9): ``instance_backup/checks.py``.

An unusable ``LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN`` (or its ``_FILE``) showed only at the hosting panel's first request,
an unusable ``LIBREFOLIO_BACKUP_MAX_UPLOAD_MB`` only at the first restore upload: the startup audit named neither. Under
test, the two checks that join the platform's configuration checks (``config_audit``, workstream H), as the contract of
lot B-9 froze them, its revision of 06:42 included (an unset token is ``ok``: a default start logs nothing new):

(a) ``check_panel_token()``, ``backup.panel_token``, reading ``config.backup.backup_download_token()``: neither the
    variable nor its ``_FILE`` set (a blank variable is unset) ``ok`` / ``backup.checks.panelToken.off``; a usable token,
    from the variable or from its file, ``ok`` / ``panelToken.ok``; one holding anything but visible ASCII ``error`` /
    ``panelToken.notVisibleAscii``; one shorter than 32 characters ``error`` / ``panelToken.tooShort`` with
    ``{"minimum": 32}``; a ``_FILE`` that cannot give it (missing, blank, not UTF-8) ``error`` / ``panelToken.unreadable``
    with ``{"reason": <the reader's SecretFileError, as text>}``. The variable wins over its file, broken or not.
(b) ``check_upload_limit()``, ``backup.upload_limit``, reading ``backup_max_upload_mb()``: a limit ``ok`` /
    ``uploadLimit.limited`` with ``{"limit_mb": n}`` (the managed profile's 500 included); none (``0``, or unset in the
    self-hosted profile) ``ok`` / ``uploadLimit.unlimited``; a value that is not a whole number ``error`` /
    ``uploadLimit.invalid``; H's profile table giving the limit a value of another type (H-27), or none under a profile
    other than selfhosted (H-37), on which the reader raises ``ProfileDefaultError``, ``error`` /
    ``uploadLimit.profileTable``; the self-hosted profile reads no entry. The variable wins over a wrong table.
(c) Every result is the platform's ``ConfigCheck``, its detail of strings and integers; one that is not ``ok`` carries a
    summary for the log: one line, naming its variable. The checks never raise: each reader, made to raise each of its
    documented errors, gives the error state, and was read.
(d) No token in any result: a token holding a marker, in the variable or in a file, usable or not, in a file that is not
    UTF-8 or is too large, is in no field of either result, nor in a record or an event of the startup audit.
(e) ``BACKUP_CONFIG_CHECKS`` is the two checks, in that order; ``config_audit.CONFIG_CHECKS`` holds them, the very
    objects, once each, together, before the email checks, which still close the tuple, and ``run_config_checks()``
    carries what each returns. Either
    module can be imported first: in a fresh interpreter, ``checks`` then ``config_audit`` and the reverse both import
    and run the two checks (``ConfigCheck`` is imported only when a check runs).
(f) The startup audit: an unusable token or upload limit is one ERROR record with the check's summary, id and detail,
    and the start goes on (``log_configuration_audit()`` returns); a default self-hosted start, no token and no limit
    set, logs nothing about either check.
(g) The i18n: every key of (a) and (b) is a message in the four catalogues of ``frontend/src/lib/i18n/backup``, naming
    exactly the placeholders of its detail (``{minimum}``, ``{reason}``, ``{limit_mb}``), and the others none.

Pure: no database, no server, no network. Every variable the checks read is removed by an autouse fixture, the profile
set to self-hosted; each test sets its own with ``monkeypatch``, and token files live in ``tmp_path``. The startup audit
runs with the platform isolated as ``test_config_audit.py`` isolates it (test mode, its data directory in ``tmp_path``,
no JWT secret, no instance key, no block, email off) and ``config_audit``'s logger replaced by a recorder; structlog's
own events are captured beside it. The fresh interpreters run in test mode, their data directory in ``tmp_path``,
bounded by a timeout that is never a wait. The catalogues are read from their sources, as §3 writes them.

Red until lot B-9: ``instance_backup.checks`` is imported by each test that needs it (the ``checks`` fixture), never at
collection, so each test fails on its own, saying so; the catalogues' test fails on the keys they do not hold yet.
"""

from __future__ import annotations

import importlib
import json
import os
import re
import subprocess
import sys
import textwrap
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import pytest
from structlog.testing import capture_logs

from backend.app import config
from backend.app.config import SECRET_FILE_MAX_BYTES, ProfileDefaultError, SecretFileError
from backend.app.config import backup as backup_config
from backend.app.config.backup import BackupConfigError, backup_download_token, backup_max_upload_mb
from backend.app.services.email.checks import EMAIL_CONFIG_CHECKS
from backend.app.services.platform import config_audit
from backend.app.services.platform.config_audit import ConfigCheck
from backend.app.services.platform.instance_key import INSTANCE_KEY_FILE, instance_key_path
from backend.test_scripts.test_utils import print_section, print_success

CHECKS_MODULE = "backend.app.services.platform.instance_backup.checks"
#: The variables of the two checks, as the deployments write them: spelled out here, so that a rename shows.
TOKEN_VARIABLE = "LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN"
TOKEN_FILE_VARIABLE = "LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN_FILE"
LIMIT_VARIABLE = "LIBREFOLIO_BACKUP_MAX_UPLOAD_MB"
PROFILE_VARIABLE = "LIBREFOLIO_PROFILE"
#: The shortest token the panel's routes take.
MINIMUM = 32

PANEL_TOKEN_ID = "backup.panel_token"
UPLOAD_LIMIT_ID = "backup.upload_limit"
PANEL_OFF = "backup.checks.panelToken.off"
PANEL_OK = "backup.checks.panelToken.ok"
NOT_VISIBLE_ASCII = "backup.checks.panelToken.notVisibleAscii"
TOO_SHORT = "backup.checks.panelToken.tooShort"
UNREADABLE = "backup.checks.panelToken.unreadable"
LIMITED = "backup.checks.uploadLimit.limited"
UNLIMITED = "backup.checks.uploadLimit.unlimited"
INVALID = "backup.checks.uploadLimit.invalid"
PROFILE_TABLE = "backup.checks.uploadLimit.profileTable"
#: Every message of the two checks, with the placeholders it names: the keys of the detail that goes with it.
MESSAGES: dict[str, set[str]] = {
    PANEL_OFF: set(),
    PANEL_OK: set(),
    NOT_VISIBLE_ASCII: set(),
    TOO_SHORT: {"minimum"},
    UNREADABLE: {"reason"},
    LIMITED: {"limit_mb"},
    UNLIMITED: set(),
    INVALID: set(),
    PROFILE_TABLE: set(),
}

#: A usable token: 64 visible ASCII characters, as ``openssl rand -hex 32`` gives one.
GOOD_TOKEN = "0f1e2d3c4b5a69788796a5b4c3d2e1f00f1e2d3c4b5a69788796a5b4c3d2e1f0"
#: A ``_FILE`` naming a file that does not exist; any ``bytes`` value is the content of the file it names.
MISSING_FILE = "<a token file that does not exist>"
#: Stands for the text of the ``SecretFileError`` the reader raises for the configuration: the reason the check reports.
READER_REASON = "<the reader's SecretFileError, as text>"
#: Leaves H's profile table as shipped; ``REMOVED`` removes the managed profile's entry for the upload limit (H-37); any
#: other value replaces that entry.
AS_SHIPPED = "<the profile table as shipped>"
REMOVED = "<the managed entry removed>"
#: Marks every token of the leak tests (the marker of ``test_config_audit.py``): no field of a result, no record or
#: event of the startup audit may hold it.
CANARY = "Zq7canary"
#: A usable token holding the marker: visible ASCII, 49 characters.
CANARY_TOKEN = f"{CANARY}-" + "c" * 39

#: The project root: the working directory of the fresh interpreters, and where the catalogues are.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
CATALOGUES = PROJECT_ROOT / "frontend" / "src" / "lib" / "i18n" / "backup"
LANGUAGES = ("en", "it", "fr", "es")
#: A placeholder of an ICU message: ``{name}``, or the name of ``{name, plural, ...}``; never the ``{#`` of a plural branch.
PLACEHOLDER = re.compile(r"\{\s*([A-Za-z_]\w*)\s*[,}]")
#: A bound for a fresh interpreter that hangs, never a wait.
FRESH_INTERPRETER_TIMEOUT_SECONDS = 300
FRESH_IMPORT_MARKER = "FRESH-IMPORT "

#: What a fresh interpreter runs: it imports the modules named on its command line, in that order, then reports which of
#: ``CONFIG_CHECKS`` are the backup checks (the very objects of ``BACKUP_CONFIG_CHECKS``) and what they return;
#: ``preloaded`` proves that no watched module was there before.
FRESH_IMPORT = textwrap.dedent("""
    import importlib
    import json
    import sys

    watched = ("backend.app.services.platform.instance_backup.checks", "backend.app.services.platform.config_audit")
    preloaded = [name for name in watched if name in sys.modules]
    for name in sys.argv[1:]:
        importlib.import_module(name)
    from backend.app.services.platform.config_audit import CONFIG_CHECKS
    from backend.app.services.platform.instance_backup.checks import BACKUP_CONFIG_CHECKS

    registered = [check for check in CONFIG_CHECKS if any(check is ours for ours in BACKUP_CONFIG_CHECKS)]
    report = {
        "preloaded": preloaded,
        "registered": [check.__name__ for check in registered],
        "ran": [[result.check_id, result.severity, result.i18n_key] for result in (check() for check in BACKUP_CONFIG_CHECKS)],
    }
    print("FRESH-IMPORT " + json.dumps(report))
    """)


# =============================================================================
# Fixtures and helpers
# =============================================================================


@pytest.fixture(autouse=True)
def _no_inherited_backup_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every variable the two checks read is removed, and the profile set to self-hosted (the environment wins over a
    ``.env``): a test sees only what it sets itself."""
    for variable in (TOKEN_VARIABLE, TOKEN_FILE_VARIABLE, LIMIT_VARIABLE):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv(PROFILE_VARIABLE, "selfhosted")


@pytest.fixture
def checks() -> ModuleType:
    """``instance_backup.checks`` (lot B-9), imported by each test that needs it, never at collection: until it exists,
    each test fails on its own, with this message."""
    try:
        return importlib.import_module(CHECKS_MODULE)
    except ModuleNotFoundError as exc:
        if exc.name != CHECKS_MODULE:
            raise
        pytest.fail(f"{CHECKS_MODULE} does not exist: lot B-9 is not written yet ({exc})")


@pytest.fixture
def platform(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """The platform's side of the startup audit, isolated as ``test_config_audit.py``'s ``_configure`` isolates it: test
    mode, a data directory in ``tmp_path`` with no instance key yet, no JWT secret, no instance key, no block, email off,
    cookie ``auto``, log level ``INFO``, profile ``selfhosted``: every platform check is ok but the unset JWT secret
    (info). The data directory, verified to be the one the instance key is looked for in."""
    for variable in [name for name in os.environ if name.endswith("_FILE") and (name == "JWT_SECRET_FILE" or name.startswith("LIBREFOLIO_"))]:
        monkeypatch.delenv(variable)
    for variable in ("JWT_SECRET", "LIBREFOLIO_INSTANCE_KEY", "LIBREFOLIO_LOG_LEVEL", "LIBREFOLIO_DATA_DIR", "LIBREFOLIO_TEST_DATA_DIR", "LIBREFOLIO_BLOCKED", "LIBREFOLIO_DELETION_DATE", "LIBREFOLIO_PUBLIC_URL"):
        monkeypatch.delenv(variable, raising=False)
    for variable in [name for name in os.environ if name.startswith("LIBREFOLIO_SMTP_")]:
        monkeypatch.delenv(variable)
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "auto")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv(PROFILE_VARIABLE, "selfhosted")
    data_dir = (tmp_path / "data").resolve()
    assert instance_key_path() == data_dir / INSTANCE_KEY_FILE, f"the instance key must be looked for in the data directory of this test, not at {instance_key_path()}"
    return data_dir


class LogRecorder:
    """Stands in for ``config_audit``'s structlog logger, as in ``test_config_audit.py``: one ``(level, summary, fields)``
    per call."""

    def __init__(self) -> None:
        self.records: list[tuple[str, str, dict]] = []

    def info(self, event: str, **fields) -> None:
        self.records.append(("info", event, fields))

    def warning(self, event: str, **fields) -> None:
        self.records.append(("warning", event, fields))

    def error(self, event: str, **fields) -> None:
        self.records.append(("error", event, fields))


@pytest.fixture
def logged(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str, dict]]:
    """The records of the startup audit: ``config_audit.logger`` replaced by a recorder."""
    recorder = LogRecorder()
    monkeypatch.setattr(config_audit, "logger", recorder)
    return recorder.records


def configure_token(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, variable: str | None, file: bytes | str | None) -> None:
    """``LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN`` set to ``variable`` unless ``None``; its ``_FILE`` naming a file of
    ``tmp_path`` holding ``file``, or ``MISSING_FILE`` for one that does not exist, unless ``None``."""
    if variable is not None:
        monkeypatch.setenv(TOKEN_VARIABLE, variable)
    if file is not None:
        path = tmp_path / "panel-token"
        if file != MISSING_FILE:
            path.write_bytes(file)
        monkeypatch.setenv(TOKEN_FILE_VARIABLE, str(path))


def set_managed_entry(monkeypatch: pytest.MonkeyPatch, table: object) -> None:
    """H's managed entry for the upload limit: left as shipped (``AS_SHIPPED``), removed (``REMOVED``), or ``table``."""
    if table == REMOVED:
        monkeypatch.delitem(config.ENVIRONMENT_PROFILE_DEFAULTS["managed"], LIMIT_VARIABLE)
    elif table != AS_SHIPPED:
        monkeypatch.setitem(config.ENVIRONMENT_PROFILE_DEFAULTS["managed"], LIMIT_VARIABLE, table)


def reader_failure(reader: Callable[[], object], error: type[Exception]) -> str:
    """The text of the documented ``error`` that ``reader`` raises for the configuration of the test: what a check reports
    of it. Checked, so that the case is the one it names."""
    try:
        reader()
    except error as exc:
        return str(exc)
    pytest.fail(f"precondition: {reader.__name__}() raises {error.__name__} for this configuration; it returned a value")


def assert_state(result: ConfigCheck, check_id: str, severity: str, key: str, detail: dict, variable: str) -> None:
    """``result`` is the expected state, and has what the admin interface and the log need: the platform's
    ``ConfigCheck``, a detail of strings and integers, and, when it is not ok, a summary of one line naming ``variable``."""
    assert isinstance(result, ConfigCheck), f"a check returns the platform's ConfigCheck, not {type(result).__name__}"
    actual = (result.check_id, result.severity, result.i18n_key, result.detail)
    assert actual == (check_id, severity, key, detail), f"expected {(check_id, severity, key, detail)}, not {actual}"
    assert all(isinstance(value, str | int) for value in result.detail.values()), f"the parameters of an i18n message are strings or integers: {result.detail}"
    if severity != "ok":
        summary = result.summary
        assert summary.strip() and "\n" not in summary and variable in summary, f"{check_id} is {severity}: its summary is one line for the log, naming {variable}: {summary!r}"


def backup_records(records: list[tuple[str, str, dict]]) -> list[tuple[str, str, dict]]:
    """The records of the startup audit about a backup check."""
    return [record for record in records if str(record[2].get("check", "")).startswith("backup.")]


def as_logged(result: ConfigCheck) -> tuple[str, str, dict]:
    """The record ``log_configuration_audit`` writes for a check that is not ok: its severity, its summary, its id and
    detail."""
    return (result.severity, result.summary, {"check": result.check_id, "detail": result.detail})


def flattened(catalogue: object, prefix: str = "") -> dict[str, object]:
    """A catalogue as ``{dotted key: message}``, nested objects walked."""
    if not isinstance(catalogue, dict):
        return {prefix: catalogue}
    found: dict[str, object] = {}
    for name, value in catalogue.items():
        found.update(flattened(value, f"{prefix}.{name}" if prefix else name))
    return found


def fresh_environment(tmp_path: Path) -> dict[str, str]:
    """This process's environment for a fresh interpreter: no backup variable, test mode, its data directory in
    ``tmp_path``, the self-hosted profile, the project root importable."""
    environment = {name: value for name, value in os.environ.items() if name not in (TOKEN_VARIABLE, TOKEN_FILE_VARIABLE, LIMIT_VARIABLE)}
    environment.update(LIBREFOLIO_TEST_MODE="1", LIBREFOLIO_TEST_DATA_DIR=str(tmp_path / "data"), LIBREFOLIO_PROFILE="selfhosted")
    environment["PYTHONPATH"] = os.pathsep.join(filter(None, [str(PROJECT_ROOT), environment.get("PYTHONPATH")]))
    return environment


# =============================================================================
# (a) check_panel_token
# =============================================================================


#: (the variable, its ``_FILE``, severity, i18n key, detail): every row of the contract's first table, from the variable
#: and from the file. ``READER_REASON`` is the reader's own ``SecretFileError`` text, read by the test.
PANEL_CASES = [
    pytest.param(None, None, "ok", PANEL_OFF, {}, id="unset-is-off-and-ok"),
    pytest.param("   ", None, "ok", PANEL_OFF, {}, id="a-blank-variable-is-unset"),
    pytest.param(GOOD_TOKEN, None, "ok", PANEL_OK, {}, id="usable"),
    pytest.param("k" * MINIMUM, None, "ok", PANEL_OK, {}, id="32-characters"),
    pytest.param("k" * (MINIMUM - 1), None, "error", TOO_SHORT, {"minimum": MINIMUM}, id="31-characters"),
    pytest.param(GOOD_TOKEN + " ", None, "error", NOT_VISIBLE_ASCII, {}, id="a-space-after-it"),
    pytest.param(GOOD_TOKEN[:32] + "\t" + GOOD_TOKEN[32:], None, "error", NOT_VISIBLE_ASCII, {}, id="a-tab-inside"),
    pytest.param("\u00e9" + GOOD_TOKEN, None, "error", NOT_VISIBLE_ASCII, {}, id="a-letter-outside-ascii"),
    pytest.param(None, GOOD_TOKEN.encode() + b"\n", "ok", PANEL_OK, {}, id="usable-from-its-file"),
    pytest.param(None, b"k" * (MINIMUM - 1) + b"\n", "error", TOO_SHORT, {"minimum": MINIMUM}, id="31-characters-from-its-file"),
    pytest.param(None, MISSING_FILE, "error", UNREADABLE, READER_REASON, id="its-file-missing"),
    pytest.param(None, b"   \n", "error", UNREADABLE, READER_REASON, id="its-file-blank"),
    pytest.param(None, b"\xff\xfe" + GOOD_TOKEN.encode(), "error", UNREADABLE, READER_REASON, id="its-file-not-utf8"),
    pytest.param("   ", MISSING_FILE, "error", UNREADABLE, READER_REASON, id="a-blank-variable-hides-no-broken-file"),
    pytest.param(GOOD_TOKEN, MISSING_FILE, "ok", PANEL_OK, {}, id="the-variable-wins-over-its-broken-file"),
]


@pytest.mark.parametrize(("variable", "file", "severity", "key", "detail"), PANEL_CASES)
def test_the_panel_token_check_in_each_state(checks, monkeypatch, tmp_path, variable, file, severity, key, detail):
    """(a) The state of ``backup.panel_token`` follows ``backup_download_token()``. Revision 06:42: neither the variable
    nor its file set is ``ok``, key ``.off``, no detail; email off by default is ok too (``email.checks.smtp.off``)."""
    configure_token(monkeypatch, tmp_path, variable, file)
    if detail == READER_REASON:
        detail = {"reason": reader_failure(backup_download_token, SecretFileError)}
        assert TOKEN_FILE_VARIABLE in detail["reason"], f"precondition: the reader's error names {TOKEN_FILE_VARIABLE}: {detail['reason']!r}"

    result = checks.check_panel_token()

    assert_state(result, PANEL_TOKEN_ID, severity, key, detail, TOKEN_VARIABLE)
    print_success(f"{severity} {result.i18n_key} {result.detail}")


# =============================================================================
# (b) check_upload_limit
# =============================================================================


#: (profile, the variable, H's managed entry for it, severity, i18n key, detail): every row of the contract's second
#: table. ``AS_SHIPPED`` leaves the table as it is (500 in the managed profile), ``REMOVED`` removes the managed entry.
UPLOAD_CASES = [
    pytest.param("selfhosted", None, AS_SHIPPED, "ok", UNLIMITED, {}, id="self-hosted-unset"),
    pytest.param("selfhosted", "0", AS_SHIPPED, "ok", UNLIMITED, {}, id="0"),
    pytest.param("selfhosted", "250", AS_SHIPPED, "ok", LIMITED, {"limit_mb": 250}, id="250"),
    pytest.param("selfhosted", " 250 ", AS_SHIPPED, "ok", LIMITED, {"limit_mb": 250}, id="spaces-around"),
    pytest.param("managed", None, AS_SHIPPED, "ok", LIMITED, {"limit_mb": 500}, id="managed-unset-500"),
    pytest.param("managed", "0", AS_SHIPPED, "ok", UNLIMITED, {}, id="managed-0"),
    pytest.param("selfhosted", "abc", AS_SHIPPED, "error", INVALID, {}, id="letters"),
    pytest.param("selfhosted", "-1", AS_SHIPPED, "error", INVALID, {}, id="negative"),
    pytest.param("selfhosted", "1.5", AS_SHIPPED, "error", INVALID, {}, id="decimal"),
    pytest.param("managed", None, "500", "error", PROFILE_TABLE, {}, id="the-table-gives-text"),
    pytest.param("managed", None, None, "error", PROFILE_TABLE, {}, id="the-table-gives-null"),
    pytest.param("managed", None, REMOVED, "error", PROFILE_TABLE, {}, id="the-managed-entry-removed"),
    pytest.param("selfhosted", None, REMOVED, "ok", UNLIMITED, {}, id="self-hosted-reads-no-entry"),
    pytest.param("managed", "250", "500", "ok", LIMITED, {"limit_mb": 250}, id="the-variable-wins-over-a-wrong-table"),
]


@pytest.mark.parametrize(("profile", "value", "table", "severity", "key", "detail"), UPLOAD_CASES)
def test_the_upload_limit_check_in_each_state(checks, monkeypatch, profile, value, table, severity, key, detail):
    """(b) The state of ``backup.upload_limit`` follows ``backup_max_upload_mb()``; an entry of H's table of another type
    (H-27), or none under the managed profile (H-37), is checked to make the reader raise ``ProfileDefaultError``, so the
    case is the one it names. The self-hosted profile reads no entry: removed, it changes nothing."""
    monkeypatch.setenv(PROFILE_VARIABLE, profile)
    if value is not None:
        monkeypatch.setenv(LIMIT_VARIABLE, value)
    set_managed_entry(monkeypatch, table)
    if key == PROFILE_TABLE:
        reader_failure(backup_max_upload_mb, ProfileDefaultError)

    result = checks.check_upload_limit()

    assert_state(result, UPLOAD_LIMIT_ID, severity, key, detail, LIMIT_VARIABLE)
    print_success(f"{severity} {result.i18n_key} {result.detail}")


# =============================================================================
# (c) Never raises
# =============================================================================


#: (the check, the reader it reads, the documented error the reader is made to raise, the key and detail of the result).
READER_ERRORS = [
    pytest.param("check_panel_token", "backup_download_token", lambda: BackupConfigError(TOKEN_VARIABLE, "BACKUP_DOWNLOAD_TOKEN_NOT_VISIBLE_ASCII", "expected visible ASCII characters only"), NOT_VISIBLE_ASCII, {}, id="token-not-visible-ascii"),
    pytest.param("check_panel_token", "backup_download_token", lambda: BackupConfigError(TOKEN_VARIABLE, "BACKUP_DOWNLOAD_TOKEN_TOO_SHORT", "expected at least 32 characters"), TOO_SHORT, {"minimum": MINIMUM}, id="token-too-short"),
    pytest.param(
        "check_panel_token",
        "backup_download_token",
        lambda: SecretFileError(f"{TOKEN_FILE_VARIABLE}: /run/secrets/panel-token does not exist"),
        UNREADABLE,
        {"reason": f"{TOKEN_FILE_VARIABLE}: /run/secrets/panel-token does not exist"},
        id="token-file-unreadable",
    ),
    pytest.param("check_upload_limit", "backup_max_upload_mb", lambda: BackupConfigError(LIMIT_VARIABLE, "BACKUP_MAX_UPLOAD_MB_INVALID", "expected a whole number of megabytes"), INVALID, {}, id="limit-invalid"),
    pytest.param("check_upload_limit", "backup_max_upload_mb", lambda: ProfileDefaultError(f"{LIMIT_VARIABLE}: the managed profile gives '500', a str"), PROFILE_TABLE, {}, id="profile-table-wrong"),
]


@pytest.mark.parametrize(("check_name", "reader_name", "error", "key", "detail"), READER_ERRORS)
def test_a_check_never_raises_on_a_documented_error_of_its_reader(checks, monkeypatch, check_name, reader_name, error, key, detail):
    """(c) Each reader made to raise each of its documented errors, wherever the check looks it up (``config.backup``, or
    the name the module imported): the check returns its error state, never the exception. Barrier: the reader was
    called, so the error came from it."""
    calls: list[str] = []

    def failing_reader() -> object:
        calls.append(reader_name)
        raise error()

    monkeypatch.setattr(backup_config, reader_name, failing_reader)
    monkeypatch.setattr(checks, reader_name, failing_reader, raising=False)
    try:
        result = getattr(checks, check_name)()
    except Exception as exc:
        pytest.fail(f"{check_name}() raised {type(exc).__name__} from {reader_name}(): a configuration check never raises")

    assert calls, f"barrier: {check_name}() reads {reader_name}(), made to raise here, and never called it"
    assert (result.severity, result.i18n_key, result.detail) == ("error", key, detail), f"{check_name}(): error {key} {detail}, not {result.severity} {result.i18n_key} {result.detail}"
    print_success(f"{check_name}: error {key}")


# =============================================================================
# (d) No token in any result, nor in the startup audit
# =============================================================================


#: (the variable, its ``_FILE``, the key the panel's check gives): tokens holding the marker, usable or not, from the
#: variable and from a file; files that cannot give them (not UTF-8, too large) hold it too.
CANARY_CASES = [
    pytest.param(CANARY_TOKEN, None, PANEL_OK, id="usable-variable"),
    pytest.param(f"{CANARY} {CANARY_TOKEN}", None, NOT_VISIBLE_ASCII, id="a-space-inside"),
    pytest.param(f"{CANARY}-short", None, TOO_SHORT, id="short-variable"),
    pytest.param(None, CANARY_TOKEN.encode() + b"\n", PANEL_OK, id="usable-file"),
    pytest.param(None, f"{CANARY}-short\n".encode(), TOO_SHORT, id="short-file"),
    pytest.param(None, CANARY.encode() + b"\xff\xfe", UNREADABLE, id="file-not-utf8"),
    pytest.param(None, (CANARY_TOKEN * (SECRET_FILE_MAX_BYTES // len(CANARY_TOKEN) + 1)).encode()[: SECRET_FILE_MAX_BYTES + 1], UNREADABLE, id="file-too-large"),
]


@pytest.mark.parametrize(("variable", "file", "key"), CANARY_CASES)
def test_no_token_reaches_a_result_or_the_startup_audit(checks, platform, logged, monkeypatch, tmp_path, variable, file, key):
    """(d) Results name variables, paths, rules and lengths; never the token. Neither check's result, nor any result of
    ``run_config_checks()``, nor a record of the startup audit, nor a structlog event while it runs holds the marker.
    Barrier: the panel's check gives the key the case names, so the token was read, or refused, where the case says."""
    configure_token(monkeypatch, tmp_path, variable, file)
    panel = checks.check_panel_token()
    assert panel.i18n_key == key, f"precondition: {key}, not {panel.i18n_key}"

    results = [panel, checks.check_upload_limit(), *config_audit.run_config_checks()]
    with capture_logs() as events:
        returned = config_audit.log_configuration_audit()

    leaks = [result.check_id for result in results if CANARY in repr(result)]
    assert leaks == [], f"a configuration check put the token in its result: {leaks}"
    assert CANARY not in repr(logged), "the startup audit put the token in a record"
    assert CANARY not in repr(events), "an event logged during the startup audit holds the token"
    assert returned is None, "the startup audit returns: the start goes on"
    print_success(f"{panel.severity} {key}: the token shown nowhere")


# =============================================================================
# (e) BACKUP_CONFIG_CHECKS, in the platform's CONFIG_CHECKS
# =============================================================================


def test_backup_config_checks_is_the_two_checks_in_order(checks):
    """(e) The panel's token, then the upload limit: the tuple the platform's ``CONFIG_CHECKS`` takes."""
    print_section("BACKUP_CONFIG_CHECKS")

    assert checks.BACKUP_CONFIG_CHECKS == (checks.check_panel_token, checks.check_upload_limit), f"BACKUP_CONFIG_CHECKS: {checks.BACKUP_CONFIG_CHECKS!r}"
    print_success("check_panel_token, check_upload_limit")


def test_config_checks_runs_the_backup_checks_together_before_the_email_checks(checks, platform):
    """(e) §2, as ordered at round 2: ``CONFIG_CHECKS`` holds the very objects of ``BACKUP_CONFIG_CHECKS``, once each, in
    order and together, before the email checks (``*BACKUP_CONFIG_CHECKS,`` then ``*EMAIL_CONFIG_CHECKS,``), which still
    close the tuple as E's own tests pin it; before, not immediately before, so other lines may come in between.
    ``run_config_checks()`` carries what each returns on its own."""
    config_checks = list(config_audit.CONFIG_CHECKS)
    ours = list(checks.BACKUP_CONFIG_CHECKS)
    names = [check.__name__ for check in config_checks]
    positions = [index for index, check in enumerate(config_checks) if any(check is our for our in ours)]

    assert [config_checks[index] for index in positions] == ours, f"CONFIG_CHECKS must hold BACKUP_CONFIG_CHECKS, once each, in order: {names}"
    assert positions == list(range(positions[0], positions[0] + len(ours))), f"together: {names}"
    assert positions[-1] < min(config_checks.index(check) for check in EMAIL_CONFIG_CHECKS), f"before the email checks: {names}"
    results = [result for result in config_audit.run_config_checks() if result.check_id.startswith("backup.")]
    assert results == [check() for check in ours], "run_config_checks must carry what the backup checks return on their own"
    print_success(f"{', '.join(names[index] for index in positions)} at {positions}")


@pytest.mark.parametrize(
    "order",
    [
        pytest.param((CHECKS_MODULE, "backend.app.services.platform.config_audit"), id="checks-then-config-audit"),
        pytest.param(("backend.app.services.platform.config_audit", CHECKS_MODULE), id="config-audit-then-checks"),
    ],
)
def test_either_module_can_be_imported_first_in_a_fresh_interpreter(tmp_path, order):
    """(e) §1: ``config_audit`` imports ``checks``, so ``checks`` imports ``ConfigCheck`` only when a check runs. A fresh
    interpreter (no backup variable, test mode, its data directory in ``tmp_path``) imports ``order`` and exits 0, finds
    the two checks in ``CONFIG_CHECKS`` and runs them: ``.off`` and ``.unlimited``, both ok. Barrier first: no watched
    module was loaded before the first import, so the order is the one the case names."""
    completed = subprocess.run([sys.executable, "-c", FRESH_IMPORT, *order], cwd=PROJECT_ROOT, env=fresh_environment(tmp_path), capture_output=True, text=True, timeout=FRESH_INTERPRETER_TIMEOUT_SECONDS, check=False)

    assert completed.returncode == 0, f"importing {' then '.join(order)} in a fresh interpreter failed with {completed.returncode}:\n{completed.stderr[-4000:]}"
    reports = [line.removeprefix(FRESH_IMPORT_MARKER) for line in completed.stdout.splitlines() if line.startswith(FRESH_IMPORT_MARKER)]
    assert len(reports) == 1, f"the fresh interpreter must report once: {completed.stdout[-4000:]}"
    report = json.loads(reports[0])
    assert report["preloaded"] == [], f"barrier: a fresh interpreter loads no watched module before the first import: {report['preloaded']}"
    expected = {"preloaded": [], "registered": ["check_panel_token", "check_upload_limit"], "ran": [[PANEL_TOKEN_ID, "ok", PANEL_OFF], [UPLOAD_LIMIT_ID, "ok", UNLIMITED]]}
    assert report == expected, f"{' then '.join(order)}: {report}"
    print_success(f"{' then '.join(order)}: {report['registered']}")


# =============================================================================
# (f) The startup audit
# =============================================================================


#: (variables, the token's ``_FILE``, H's managed entry for the limit, the check that speaks, its key): unusable
#: configurations of each check, the other left at its default (ok).
UNUSABLE = [
    pytest.param({TOKEN_VARIABLE: "k" * (MINIMUM - 1)}, None, AS_SHIPPED, "check_panel_token", TOO_SHORT, id="token-too-short"),
    pytest.param({TOKEN_VARIABLE: GOOD_TOKEN + " "}, None, AS_SHIPPED, "check_panel_token", NOT_VISIBLE_ASCII, id="token-not-visible-ascii"),
    pytest.param({}, MISSING_FILE, AS_SHIPPED, "check_panel_token", UNREADABLE, id="token-file-missing"),
    pytest.param({}, b"\n", AS_SHIPPED, "check_panel_token", UNREADABLE, id="token-file-blank"),
    pytest.param({LIMIT_VARIABLE: "abc"}, None, AS_SHIPPED, "check_upload_limit", INVALID, id="limit-invalid"),
    pytest.param({PROFILE_VARIABLE: "managed"}, None, "500", "check_upload_limit", PROFILE_TABLE, id="profile-table-wrong"),
    pytest.param({PROFILE_VARIABLE: "managed"}, None, REMOVED, "check_upload_limit", PROFILE_TABLE, id="profile-table-entry-removed"),
]


@pytest.mark.parametrize(("variables", "file", "table", "check_name", "key"), UNUSABLE)
def test_the_startup_audit_logs_an_unusable_backup_configuration_as_an_error_and_goes_on(checks, platform, logged, monkeypatch, tmp_path, variables, file, table, check_name, key):
    """(f) ``log_configuration_audit()`` returns, the start goes on, after one backup record: the ERROR of the check that
    cannot use its configuration, with its summary, id and detail; nothing about the other backup check, ok."""
    print_section(f"The startup audit: {key}")
    for name, value in variables.items():
        monkeypatch.setenv(name, value)
    configure_token(monkeypatch, tmp_path, None, file)
    set_managed_entry(monkeypatch, table)
    expected = getattr(checks, check_name)()
    assert (expected.severity, expected.i18n_key) == ("error", key), f"precondition: {check_name}() is an error {key}: {expected.severity} {expected.i18n_key}"

    try:
        returned = config_audit.log_configuration_audit()
    except Exception as exc:
        pytest.fail(f"the startup audit raised {type(exc).__name__}: an unusable backup configuration never stops the start")

    assert returned is None
    assert backup_records(logged) == [as_logged(expected)], f"one ERROR record of {expected.check_id}, with its summary, id and detail: {backup_records(logged)}"
    print_success(f"error: {expected.summary}")


def test_a_default_start_logs_nothing_about_the_backup_checks(checks, platform, logged):
    """(f) Revision 06:42: no token and no limit set, the self-hosted profile, the default of every install: both checks
    ok (``.off``, ``.unlimited``), so the audit, which runs them, logs nothing about them; a default start logs nothing
    new. Barriers: the audit runs the backup checks, and its record of the unset JWT secret reaches the recorder, so «no
    backup record» is heard, not assumed."""
    registered = [check for check in config_audit.CONFIG_CHECKS if any(check is our for our in checks.BACKUP_CONFIG_CHECKS)]
    assert registered == list(checks.BACKUP_CONFIG_CHECKS), f"barrier: the startup audit runs the backup checks: {[check.__name__ for check in config_audit.CONFIG_CHECKS]}"
    states = [(result.check_id, result.severity, result.i18n_key) for result in (checks.check_panel_token(), checks.check_upload_limit())]
    assert states == [(PANEL_TOKEN_ID, "ok", PANEL_OFF), (UPLOAD_LIMIT_ID, "ok", UNLIMITED)], f"precondition: a default configuration, both ok: {states}"

    config_audit.log_configuration_audit()

    assert any(fields.get("check") == "platform.jwt_secret" for _, _, fields in logged), f"barrier: the audit's record of the unset JWT secret must reach the recorder: {logged}"
    assert backup_records(logged) == [], f"a default start logs nothing about backup.panel_token nor backup.upload_limit: {backup_records(logged)}"
    print_success("nothing logged about the backup checks")


# =============================================================================
# (g) The messages, in the four catalogues
# =============================================================================


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_message_of_the_checks_is_in_the_catalogue_with_its_placeholders(language):
    """(g) §3: each key of the two tables is a message of ``frontend/src/lib/i18n/backup/<language>.json``, naming exactly
    the placeholders its detail gives (``{minimum}``, ``{reason}``, ``{limit_mb}``) and, for a result without a detail,
    none: the Security tab (A8b) renders them with the detail as it comes."""
    path = CATALOGUES / f"{language}.json"
    messages = flattened(json.loads(path.read_text(encoding="utf-8")))
    problems = []

    for key, placeholders in MESSAGES.items():
        message = messages.get(key)
        if not isinstance(message, str) or not message.strip():
            problems.append(f"{key}: no message")
            continue
        named = set(PLACEHOLDER.findall(message))
        if named != placeholders:
            problems.append(f"{key}: names {sorted(named)}, its detail gives {sorted(placeholders)}")

    assert problems == [], f"{path.relative_to(PROJECT_ROOT)}:\n- " + "\n- ".join(problems)
    print_success(f"{language}: {len(MESSAGES)} messages")

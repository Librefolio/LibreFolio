"""
The startup check of the stored plugin secrets (workstream H, platform, 1.3.0 item H-15).

Under test: ``backend/app/services/platform/plugin_secrets_check.py``. The plugin settings of workstream X keep their
secrets encrypted with a subkey of the instance key, each row recording the id of the key that encrypted it, and
``plugin_secrets_key_status(session)`` (``services/plugin_settings/crypto.py``) counts by scope the stored secrets the
current key cannot read. This check turns that count into a ``ConfigCheck`` (``config_audit.py``) and logs it at
startup. The contract:

(a) ``CHECK_ID`` is ``platform.plugin_secrets``. ``check_plugin_secrets(session)`` asks ``plugin_secrets_key_status``,
    through the module's name, with the session it is given: no unreadable system secret is ``ok``
    (``instance.checks.pluginSecrets.ok``, no detail), whatever the user count; any is an ``error``
    (``instance.checks.pluginSecrets.unreadable``) whose detail is exactly ``{"count": <system>}``, an ``int``, with an
    English summary that gives that count. The user count appears nowhere, neither in the detail nor in the summary: the
    admin sees only the system count (rule of workstream X).
(b) ``log_plugin_secrets_check()``, the startup step, opens ``AsyncSession(get_async_engine())`` and runs the check: it
    logs nothing when the check is ok, and a check that is not ok at its severity, as ``log_configuration_audit()`` does:
    the summary, with ``check`` and ``detail``.
(c) It never raises: an exception of ``plugin_secrets_key_status`` (a ``RuntimeError``, an SQLAlchemy
    ``OperationalError``) is one warning, ``Plugin secrets check could not run``, whose ``error`` field is the class name
    of the exception, never its message, and the coroutine returns normally.
(d) On a real database, with no instance key configured and an empty data directory: without a stored secret nothing is
    logged and the key file is not generated, so a fresh self-hosted install never generates the key at startup; one
    system secret under another key id is one error with ``detail == {"count": 1}``, the user secrets left out.

The step itself, ``plugin-secrets-check`` after ``global-settings`` and before ``scheduler`` in ``STARTUP_STEPS``, is
checked in ``test_app_lifecycle.py``.

Pure: the module's logger is replaced by a recorder, and ``get_async_engine`` by a private engine on a file under
``tmp_path``. In (a), (b) and (c) ``plugin_secrets_key_status`` is a stub and the engine is never opened; in (d) the
real one reads a private SQLite file built with ``SQLModel.metadata.create_all``. The data directory is in ``tmp_path``
and the instance key variables are removed with ``monkeypatch``. No lane DB, no server, no network. Each test imports
the module itself, so that until it exists every test fails on that import, on its own.
"""

from __future__ import annotations

import importlib
import sqlite3
from collections.abc import AsyncIterator
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import Session

from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.db.models import PluginSystemSetting, PluginUserSetting, User
from backend.app.services.platform.config_audit import ConfigCheck
from backend.app.services.platform.instance_key import INSTANCE_KEY_FILE, instance_key_path
from backend.app.services.plugin_settings.crypto import UnreadableSecrets, encrypt_secret, key_id_of, secret_aad
from backend.test_scripts.test_utils import print_section, print_success

MODULE = "backend.app.services.platform.plugin_secrets_check"
CHECK_ID = "platform.plugin_secrets"
OK_MESSAGE = "instance.checks.pluginSecrets.ok"
UNREADABLE_MESSAGE = "instance.checks.pluginSecrets.unreadable"
COULD_NOT_RUN = "Plugin secrets check could not run"
#: Marks the messages of the exceptions and the plaintexts of the secrets: none may reach a log record.
CANARY = "Zq7canary"
#: A subkey that is not this instance's, as for the secrets of a backup made by another instance.
FOREIGN_SUBKEY = bytes([7]) * 32


# =============================================================================
# HELPERS AND FIXTURES
# =============================================================================


def _module() -> ModuleType:
    """The module under test, imported by each test: until it exists, every test fails here, on its own."""
    return importlib.import_module(MODULE)


class LogRecorder:
    """Stands in for the module's structlog logger: one ``(level, summary, fields)`` per call, whatever the level."""

    def __init__(self) -> None:
        self.records: list[tuple[str, str, dict[str, Any]]] = []

    def debug(self, event: str, **fields: Any) -> None:
        self.records.append(("debug", event, fields))

    def info(self, event: str, **fields: Any) -> None:
        self.records.append(("info", event, fields))

    def warning(self, event: str, **fields: Any) -> None:
        self.records.append(("warning", event, fields))

    def error(self, event: str, **fields: Any) -> None:
        self.records.append(("error", event, fields))

    def exception(self, event: str, **fields: Any) -> None:
        self.records.append(("exception", event, fields))

    def critical(self, event: str, **fields: Any) -> None:
        self.records.append(("critical", event, fields))


def _recorded_log(monkeypatch: pytest.MonkeyPatch, module: ModuleType) -> list[tuple[str, str, dict[str, Any]]]:
    """Replace the module's logger by a recorder; what it records."""
    recorder = LogRecorder()
    monkeypatch.setattr(module, "logger", recorder)
    return recorder.records


class StatusStub:
    """Stands in for ``plugin_secrets_key_status``: gives ``answer``, or raises it, and records the sessions it is given."""

    def __init__(self, answer: UnreadableSecrets | BaseException) -> None:
        self.answer = answer
        self.sessions: list[Any] = []

    async def __call__(self, session: Any) -> UnreadableSecrets:
        self.sessions.append(session)
        if isinstance(self.answer, BaseException):
            raise self.answer
        return self.answer


@pytest.fixture
def data_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """An empty data directory of this test, in test mode, with no instance key configured: a generated key would land in it."""
    for variable in ("LIBREFOLIO_INSTANCE_KEY", "LIBREFOLIO_INSTANCE_KEY_FILE", "LIBREFOLIO_DATA_DIR"):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / "data"))
    data = (tmp_path / "data").resolve()
    data.mkdir()
    assert instance_key_path() == data / INSTANCE_KEY_FILE, f"the key file must live in the data directory of this test, not at {instance_key_path()}"
    return data


@pytest_asyncio.fixture
async def idle_engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    """What ``get_async_engine`` gives in (a) to (c): an engine on a private file, never opened by the stubbed status."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'never-opened.db'}", poolclass=NullPool)
    try:
        yield engine
    finally:
        await engine.dispose()


def _build_schema(db: Path) -> int:
    """A private database with the whole ORM schema and one user; the user's id."""
    engine = create_engine(f"sqlite:///{db}", poolclass=NullPool)
    try:
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            user = User(username="alice", email="alice@example.test", hashed_password="$argon2id$test")
            session.add(user)
            session.commit()
            return user.id
    finally:
        engine.dispose()


@pytest_asyncio.fixture
async def private_db(tmp_path: Path) -> AsyncIterator[tuple[AsyncEngine, int]]:
    """A private SQLite file with the ORM schema and one user, outside the data directory, opened as production opens its own."""
    db = tmp_path / "plugin-secrets.db"
    user_id = _build_schema(db)
    engine = create_async_engine(f"sqlite+aiosqlite:///{db}", poolclass=NullPool)
    try:
        yield engine, user_id
    finally:
        await engine.dispose()


def _foreign_secret(model: type[PluginSystemSetting] | type[PluginUserSetting], field_key: str, user_id: int | None = None) -> PluginSystemSetting | PluginUserSetting:
    """A secret row encrypted under ``FOREIGN_SUBKEY``, as a restore without the backup's key leaves it."""
    scope = "user" if model is PluginUserSetting else "system"
    blob = encrypt_secret(FOREIGN_SUBKEY, secret_aad("asset", "lab", field_key, scope, user_id), f"{CANARY}-{field_key}")
    extra = {"user_id": user_id} if model is PluginUserSetting else {}
    return model(family="asset", plugin_code="lab", field_key=field_key, secret_ciphertext=blob, key_id=key_id_of(FOREIGN_SUBKEY), **extra)


# =============================================================================
# (a) THE CHECK
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [pytest.param(UnreadableSecrets(), id="nothing-unreadable"), pytest.param(UnreadableSecrets(system=0, user=517), id="only-user-secrets-unreadable")])
async def test_no_unreadable_system_secret_is_ok(monkeypatch: pytest.MonkeyPatch, status: UnreadableSecrets) -> None:
    """(a) ok, without detail, whatever the user count: the admin's check is about the system secrets alone."""
    print_section(f"Plugin secrets check: {status} is ok")
    check = _module()
    stub = StatusStub(status)
    monkeypatch.setattr(check, "plugin_secrets_key_status", stub)
    session = object()

    result = await check.check_plugin_secrets(session)

    assert check.CHECK_ID == CHECK_ID, f"the check id is {CHECK_ID!r}, not {check.CHECK_ID!r}"
    assert isinstance(result, ConfigCheck), f"the check must give the ConfigCheck of config_audit.py, not {result!r}"
    actual = (result.check_id, result.severity, result.i18n_key, result.detail)
    assert actual == (CHECK_ID, "ok", OK_MESSAGE, {}), f"no unreadable system secret must be ok without detail, not {actual}"
    assert stub.sessions == [session], f"check_plugin_secrets must ask plugin_secrets_key_status once, with the session it is given: {stub.sessions}"
    assert "517" not in repr(result), f"the user count reached the result: {result!r}"
    print_success(f"{status}: ok")


@pytest.mark.asyncio
@pytest.mark.parametrize(("system", "user"), [pytest.param(2, 517, id="2-system-517-user"), pytest.param(13, 0, id="13-system-no-user"), pytest.param(40, 9311, id="40-system-9311-user")])
async def test_unreadable_system_secrets_are_an_error_that_counts_them_alone(monkeypatch: pytest.MonkeyPatch, system: int, user: int) -> None:
    """(a) An error whose detail is the system count alone, an ``int``; the summary gives it; the user count appears nowhere."""
    print_section(f"Plugin secrets check: {system} system and {user} user secrets unreadable")
    check = _module()
    monkeypatch.setattr(check, "plugin_secrets_key_status", StatusStub(UnreadableSecrets(system=system, user=user)))

    result = await check.check_plugin_secrets(object())

    actual = (result.check_id, result.severity, result.i18n_key, result.detail)
    assert actual == (CHECK_ID, "error", UNREADABLE_MESSAGE, {"count": system}), f"unreadable system secrets must be an error with the system count alone, not {actual}"
    assert type(result.detail["count"]) is int, f"the count is a parameter of an i18n message: an int, not {type(result.detail['count']).__name__}"
    assert result.summary.strip() and str(system) in result.summary, f"the summary for the log must give the system count {system}: {result.summary!r}"
    if user:
        assert str(user) not in result.summary and str(user) not in repr(result.detail), f"the user count {user} reached the result: {result!r}"
    print_success(f"error, count {system}: {result.summary}")


# =============================================================================
# (b) AT STARTUP
# =============================================================================


@pytest.mark.asyncio
async def test_at_startup_an_ok_check_logs_nothing(monkeypatch: pytest.MonkeyPatch, idle_engine: AsyncEngine) -> None:
    """(b) The check runs on a session of ``get_async_engine()``; ok, nothing is logged, at any level."""
    check = _module()
    logged = _recorded_log(monkeypatch, check)
    stub = StatusStub(UnreadableSecrets(user=517))
    monkeypatch.setattr(check, "get_async_engine", lambda: idle_engine)
    monkeypatch.setattr(check, "plugin_secrets_key_status", stub)

    assert await check.log_plugin_secrets_check() is None

    sessions = [(isinstance(session, AsyncSession), getattr(session, "bind", None) is idle_engine) for session in stub.sessions]
    assert sessions == [(True, True)], f"the check must run once, on an AsyncSession of get_async_engine() (is an AsyncSession, on that engine): {sessions}"
    assert logged == [], f"an ok check must not be logged: {logged}"
    print_success("ok, nothing logged")


@pytest.mark.asyncio
async def test_at_startup_unreadable_system_secrets_are_logged_as_an_error(monkeypatch: pytest.MonkeyPatch, idle_engine: AsyncEngine) -> None:
    """(b) A check that is not ok is logged at its severity, as the configuration audit logs: summary, check and detail."""
    check = _module()
    logged = _recorded_log(monkeypatch, check)
    monkeypatch.setattr(check, "get_async_engine", lambda: idle_engine)
    monkeypatch.setattr(check, "plugin_secrets_key_status", StatusStub(UnreadableSecrets(system=2, user=517)))
    expected = await check.check_plugin_secrets(object())

    assert await check.log_plugin_secrets_check() is None

    assert logged == [("error", expected.summary, {"check": CHECK_ID, "detail": {"count": 2}})], f"two unreadable system secrets must be one error with the check's summary, id and detail: {logged}"
    assert "517" not in repr(logged), f"the user count reached the log: {logged}"
    print_success(f"one error: {expected.summary}")


# =============================================================================
# (c) NEVER RAISES
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [
        pytest.param(RuntimeError(f"the status failed {CANARY}"), id="runtime-error"),
        pytest.param(OperationalError("SELECT count(*) FROM plugin_system_settings", {}, sqlite3.OperationalError(f"database is locked {CANARY}")), id="sqlalchemy-operational-error"),
    ],
)
async def test_at_startup_a_check_that_cannot_run_is_a_warning_and_never_raises(monkeypatch: pytest.MonkeyPatch, idle_engine: AsyncEngine, error: Exception) -> None:
    """(c) The start goes on: one warning naming the class of the exception, never its message."""
    print_section(f"Plugin secrets check: {type(error).__name__} at startup")
    check = _module()
    logged = _recorded_log(monkeypatch, check)
    monkeypatch.setattr(check, "get_async_engine", lambda: idle_engine)
    monkeypatch.setattr(check, "plugin_secrets_key_status", StatusStub(error))

    assert await check.log_plugin_secrets_check() is None

    assert [(level, summary) for level, summary, _ in logged] == [("warning", COULD_NOT_RUN)], f"a check that cannot run must be one warning {COULD_NOT_RUN!r}: {logged}"
    fields = logged[0][2]
    assert fields.get("error") == type(error).__name__, f"the warning's error field must be the class name {type(error).__name__!r}: {fields}"
    assert CANARY not in repr(logged) and "exc_info" not in fields, f"the message of the exception must not reach the log, neither in a field nor in a traceback: {logged}"
    print_success(f"{type(error).__name__}: one warning, the start goes on")


# =============================================================================
# (d) ON A REAL DATABASE
# =============================================================================


@pytest.mark.asyncio
async def test_without_a_stored_secret_startup_logs_nothing_and_generates_no_key(monkeypatch: pytest.MonkeyPatch, data_dir: Path, private_db: tuple[AsyncEngine, int]) -> None:
    """(d) Plain values only, no key configured: nothing logged, and no key file, so a fresh install generates no key at startup."""
    print_section("Plugin secrets check: a fresh install, no stored secret")
    check = _module()
    engine, user_id = private_db
    logged = _recorded_log(monkeypatch, check)
    monkeypatch.setattr(check, "get_async_engine", lambda: engine)
    async with AsyncSession(engine) as session:
        session.add(PluginSystemSetting(family="asset", plugin_code="lab", field_key="region", value_json='"us"'))
        session.add(PluginUserSetting(user_id=user_id, family="asset", plugin_code="lab", field_key="limit", value_json="7"))
        await session.commit()

    assert await check.log_plugin_secrets_check() is None

    assert logged == [], f"no stored secret, nothing unreadable: nothing to log, got {logged}"
    assert not instance_key_path().exists(), f"the startup check generated {instance_key_path()}: without a stored secret it must read no key"
    assert not (data_dir / INSTANCE_KEY_FILE.parent).exists(), "the startup check created the folder of the key file"
    print_success("nothing logged, no key generated")


@pytest.mark.asyncio
async def test_a_system_secret_under_another_key_is_one_error_at_startup(monkeypatch: pytest.MonkeyPatch, data_dir: Path, private_db: tuple[AsyncEngine, int]) -> None:
    """(d) One system secret and two user secrets under another key id: one error, counting the system secret alone."""
    print_section("Plugin secrets check: one system secret under another key")
    check = _module()
    engine, user_id = private_db
    logged = _recorded_log(monkeypatch, check)
    monkeypatch.setattr(check, "get_async_engine", lambda: engine)
    async with AsyncSession(engine) as session:
        session.add_all(
            [
                _foreign_secret(PluginSystemSetting, "api_key"),
                _foreign_secret(PluginUserSetting, "token", user_id),
                _foreign_secret(PluginUserSetting, "password", user_id),
                PluginSystemSetting(family="asset", plugin_code="lab", field_key="region", value_json='"us"'),
            ]
        )
        await session.commit()

    assert await check.log_plugin_secrets_check() is None

    records = [(level, fields) for level, _, fields in logged]
    assert records == [("error", {"check": CHECK_ID, "detail": {"count": 1}})], f"one system secret under another key must be one error counting it alone: {logged}"
    assert CANARY not in repr(logged), f"a secret reached the log: {logged}"
    print_success(f"one error, count 1: {logged[0][1]}")

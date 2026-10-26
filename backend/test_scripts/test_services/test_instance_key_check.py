"""
The instance key check: a wrong instance key is told, not served around (LibreFolio 1.3, workstream H, lot H5-7, decision D6).
Selector: ``services instance-key-check``. Written RED before H5-7.

Developer decision 26/10/2026: ``GET /panel/status`` says ``instance_key: ok|mismatch``, from a check value stored beside the
key. With a wrong key only the hosting panel's backup jobs and ``wake-sync`` stop; the instance keeps serving. Under test,
``backend/app/services/platform/instance_key_check.py`` (this file: the module; ``test_api/test_instance_key_check_api.py``: the routes):

(a) the names: ``KEY_CHECK_FILE`` (``secrets/instance.key.check``), ``instance_key_check_path()`` (the current data directory, read at
    each call), ``ACCEPT_VARIABLE``, ``InstanceKeyState``, the three message constants; ``config.platform.instance_key_accept()``
    (the values of ``awaiting_restore()``, any other raises ``ValueError`` naming the variable) and the start's refusal of an
    invalid value (``config_audit.log_configuration_audit``).
(b) ``key_check_value()``: 64 lowercase hex, an HMAC of a fixed label under a purpose key of its own; the same key gives the same
    value, another key another; never the key nor a derived key.
(c) ``instance_key_state(session)``: step 1 ``not_created`` or an unusable key is ``ok`` (nothing to compare, no key generated);
    step 2 the check file decides (equal ``ok``, different ``mismatch``; unreadable or not 64 hex is ``ok`` and one warning per
    process); step 3 no file, so R1: ``mismatch`` only when there is a stored secret and EVERY one is under another key (system and
    user rows both count). Never raises, creates nothing, remembers nothing: every call recomputes.
(d) ``check_instance_key_at_start(session)``: accept writes (always, replacing, one warning each start); no file and ``mismatch`` is
    one error and NOTHING written; no file otherwise writes (exclusive, ``0600`` in ``0700``, one winner among workers); a file
    ``mismatch`` is one error and is not rewritten; a file ``ok`` is silent; never raises; never a key nor a value in a log.
(e) ``app_lifespan``: the step ``instance-key-check`` right after ``plugin-secrets-check``, not blocking, no ``skip_when``, running (d).
(f) ``check_instance_key(session)``: the ``ConfigCheck`` of the admin's Security tab.

Every name of H5-7 is read by the test that needs it, so the file collects and each test reports its own red. Pure: a private
SQLite file under ``tmp_path`` with the real tables, the data directory in ``tmp_path``, the key from ``LIBREFOLIO_INSTANCE_KEY``
or a key file there; every variable through ``monkeypatch``. The once-per-process warning is measured in child interpreters
(a process's own memory cannot be reset from a test). No server, no network, no file outside ``tmp_path``.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import hmac
import importlib
import inspect
import json
import os
import re
import sqlite3
import subprocess
import sys
import threading
import typing
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import Session
from structlog.testing import capture_logs

from backend.app.config import platform as platform_config
from backend.app.db import session as db_session_module
from backend.app.db.base import SQLModel
from backend.app.db.models import PluginSystemSetting, PluginUserSetting, User
from backend.app.logging_config import get_logger
from backend.app.services.platform import app_lifespan, config_audit
from backend.app.services.platform.config_audit import ConfigCheck
from backend.app.services.platform.instance_key import InstanceKeyError, derive_key, derive_key_from
from backend.app.services.plugin_settings.crypto import encrypt_secret, key_id_of, secret_aad, settings_subkey
from backend.test_scripts.test_utils import print_section, print_success

MODULE = "backend.app.services.platform.instance_key_check"
ACCEPT_VARIABLE = "LIBREFOLIO_INSTANCE_KEY_ACCEPT"
#: ID COLLISION (reported to the coordinator): the contract names this check ``platform.instance_key``, which ``config_audit.check_instance_key`` already uses
#: (key file unusable / loose modes, in ``CONFIG_CHECKS``, ``checkGuides.json``): two checks cannot share an id in the Security list and the guide map. Until the
#: coordinator decides, the new check is ``platform.instance_key_check``; its i18n keys are the contract's (the ``ok`` text is shared, ``mismatch`` is new).
CHECK_ID = "platform.instance_key_check"
OK_KEY = "instance.checks.instanceKey.ok"
MISMATCH_KEY = "instance.checks.instanceKey.mismatch"
PURPOSE = "instance.key-check.v1"
LABEL = b"LibreFolio instance key check v1"
#: Two instance keys (at least 32 characters each) and a third, for the cases that change the key more than once.
KEY_A = "h57-instance-key-A-0123456789abcdefghij"
KEY_B = "h57-instance-key-B-9876543210jihgfedcba"
KEY_C = "h57-instance-key-C-abcdefghij0123456789"
#: A subkey that is nobody's here: the secrets of a backup made by another instance.
FOREIGN_SUBKEY = bytes([7]) * 32
BARRIER = "h57 instance key check log barrier"
CANARY = "h57canary-" + "z" * 54  # 64 characters, not hexadecimal: a check file's content that must never reach a log
HEX64 = re.compile(r"[0-9a-f]{64}")
_MISSING = object()
LEVELS_ABOVE_INFO = ("warning", "error", "critical")


# =============================================================================
# Helpers (reused by test_instance_key_check_api.py)
# =============================================================================


def ikc() -> ModuleType:
    try:
        return importlib.import_module(MODULE)
    except ModuleNotFoundError as exc:
        if exc.name != MODULE:
            raise
        pytest.fail(f"H5-7: there is no {MODULE}")


def ikc_name(name: str) -> Any:
    value = getattr(ikc(), name, _MISSING)
    if value is _MISSING:
        pytest.fail(f"H5-7: {MODULE} gives no {name}")
    return value


def expected_value(key: str) -> str:
    """The check value of ``key``, computed here from the contract's formula: HMAC-SHA256 of the label under the 32-byte purpose key."""
    return hmac.new(derive_key_from(key, PURPOSE, 32), LABEL, hashlib.sha256).hexdigest()


@dataclass
class World:
    """A data directory of this test (test mode, no key configured, no accept variable) and the monkeypatch of its environment."""

    data: Path
    monkeypatch: pytest.MonkeyPatch

    @property
    def secrets(self) -> Path:
        return self.data / "secrets"

    @property
    def check_file(self) -> Path:
        return self.secrets / "instance.key.check"

    @property
    def key_file(self) -> Path:
        return self.secrets / "instance.key"

    def set_key(self, key: str | None) -> None:
        if key is None:
            self.monkeypatch.delenv("LIBREFOLIO_INSTANCE_KEY", raising=False)
        else:
            self.monkeypatch.setenv("LIBREFOLIO_INSTANCE_KEY", key)

    def accept(self, on: bool = True) -> None:
        if on:
            self.monkeypatch.setenv(ACCEPT_VARIABLE, "1")
        else:
            self.monkeypatch.delenv(ACCEPT_VARIABLE, raising=False)

    def write_check(self, text: str, *, mode: int = 0o600) -> Path:
        self.secrets.mkdir(mode=0o700, exist_ok=True)
        self.check_file.write_text(text, encoding="utf-8")
        self.check_file.chmod(mode)
        return self.check_file

    def write_key_file(self, key: str) -> Path:
        self.secrets.mkdir(mode=0o700, exist_ok=True)
        self.key_file.write_text(key + "\n", encoding="ascii")
        self.key_file.chmod(0o600)
        return self.key_file

    def files(self) -> list[str]:
        """Every file under the data directory, relative, sorted: what a test that says «nothing written» compares."""
        return sorted(str(path.relative_to(self.data)) for path in self.data.rglob("*") if path.is_file())


@pytest.fixture
def world(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> World:
    for variable in ("LIBREFOLIO_INSTANCE_KEY", "LIBREFOLIO_INSTANCE_KEY_FILE", "LIBREFOLIO_DATA_DIR", ACCEPT_VARIABLE, "LIBREFOLIO_AWAIT_RESTORE", "LIBREFOLIO_BLOCKED", "LIBREFOLIO_DELETION_DATE"):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    data = (tmp_path / "data").resolve()
    data.mkdir()
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(data))
    return World(data=data, monkeypatch=monkeypatch)


def build_schema(db: Path) -> int:
    """A private database with the whole ORM schema and one user; the user's id."""
    engine = create_engine(f"sqlite:///{db}", poolclass=NullPool)
    try:
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            user = User(username="h57user", email="h57user@example.test", hashed_password="$argon2id$test")
            session.add(user)
            session.commit()
            return user.id
    finally:
        engine.dispose()


@pytest.fixture
def schema_db(tmp_path: Path) -> tuple[Path, int]:
    path = tmp_path / "instance-key-check.db"
    return path, build_schema(path)


class Db:
    """A private database of a test, opened as production opens its own, and the rows a test puts in it."""

    def __init__(self, engine: AsyncEngine, user_id: int) -> None:
        self.engine = engine
        self.user_id = user_id
        self._count = 0

    @contextlib.asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        async with AsyncSession(self.engine, expire_on_commit=False) as session:
            yield session

    async def add_secret(self, scope: str, *, readable: bool, plain_too: int = 0) -> None:
        """One stored secret of ``scope`` (``system`` or ``user``): under the instance key in force now when ``readable``, else under another key."""
        self._count += 1
        field_key = f"secret_{self._count}"
        user_id = self.user_id if scope == "user" else None
        subkey = settings_subkey() if readable else FOREIGN_SUBKEY
        blob = encrypt_secret(subkey, secret_aad("asset", "lab", field_key, scope, user_id), "h57-plaintext")
        model = PluginUserSetting if scope == "user" else PluginSystemSetting
        extra = {"user_id": self.user_id} if scope == "user" else {}
        async with self.session() as session:
            session.add(model(family="asset", plugin_code="lab", field_key=field_key, secret_ciphertext=blob, key_id=key_id_of(subkey), **extra))
            await session.commit()

    async def add_plain(self, scope: str) -> None:
        """One plain (not secret) setting: never a stored secret, so never counted."""
        self._count += 1
        model = PluginUserSetting if scope == "user" else PluginSystemSetting
        extra = {"user_id": self.user_id} if scope == "user" else {}
        async with self.session() as session:
            session.add(model(family="asset", plugin_code="lab", field_key=f"plain_{self._count}", value_json='"x"', **extra))
            await session.commit()


@pytest_asyncio.fixture
async def db(schema_db: tuple[Path, int]) -> AsyncIterator[Db]:
    path, user_id = schema_db
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}", poolclass=NullPool)
    try:
        yield Db(engine, user_id)
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def empty_db(tmp_path: Path) -> AsyncIterator[Db]:
    """A database with NO table: every query of it fails."""
    path = tmp_path / "no-tables.db"
    sqlite3.connect(path).close()
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}", poolclass=NullPool)
    try:
        yield Db(engine, 0)
    finally:
        await engine.dispose()


async def state_of(db: Db) -> str:
    function = ikc_name("instance_key_state")
    async with db.session() as session:
        return await function(session)


async def start_on(db: Db) -> None:
    function = ikc_name("check_instance_key_at_start")
    async with db.session() as session:
        result = await function(session)
    assert result is None, f"the start step returns None: {result!r}"


class Captured:
    """The structlog events of a block, the barrier removed (it proves the capture hears this module's logger)."""

    def __init__(self, events: list[dict[str, Any]]) -> None:
        self._events = events

    @property
    def events(self) -> list[dict[str, Any]]:
        return [event for event in self._events if event.get("event") != BARRIER]

    @property
    def barrier_heard(self) -> bool:
        return any(event.get("event") == BARRIER for event in self._events)

    def at(self, *levels: str) -> list[dict[str, Any]]:
        return [event for event in self.events if event.get("log_level") in levels]

    def text(self) -> str:
        return repr(self.events)


@contextlib.contextmanager
def captured() -> Iterator[Captured]:
    with capture_logs() as raw:
        get_logger(MODULE).warning(BARRIER)
        view = Captured(raw)
        yield view
    assert view.barrier_heard, f"Barrier: the capture hears the logger of {MODULE}: {raw}"


def assert_no_secret_in(text: str, *keys: str) -> None:
    """Neither a key, nor a check value, nor a derived key, nor the key id reached ``text``."""
    leaked = []
    for key in keys:
        candidates = {
            "the key": key,
            "its check value": expected_value(key),
            "its check-purpose key": derive_key_from(key, PURPOSE, 32).hex(),
            "its secrets subkey": derive_key_from(key, "plugins.settings.v1", 32).hex(),
            "its key id": key_id_of(derive_key_from(key, "plugins.settings.v1", 32)),
        }
        leaked += [f"{what} of {key[:12]}..." for what, value in candidates.items() if value in text]
    assert leaked == [], f"a secret reached the log: {leaked}"


def needs_posix_modes() -> None:
    if os.name == "nt":
        pytest.skip("POSIX modes only")


def needs_a_user_the_modes_bind() -> None:
    needs_posix_modes()
    if os.geteuid() == 0:
        pytest.skip("root ignores file modes")


# =============================================================================
# (a) The names, and the variable
# =============================================================================


def test_the_module_names_its_file_its_variable_its_state_and_its_messages(world):
    """(a) ``KEY_CHECK_FILE``, ``ACCEPT_VARIABLE``, ``InstanceKeyState`` and the three messages are as the contract says."""
    print_section("H5-7: the module's names")
    assert ikc_name("KEY_CHECK_FILE") == Path("secrets") / "instance.key.check", "the check file lives beside the key: secrets/instance.key.check"
    assert ikc_name("ACCEPT_VARIABLE") == ACCEPT_VARIABLE
    assert set(typing.get_args(ikc_name("InstanceKeyState"))) == {"ok", "mismatch"}, "the state is ok or mismatch, nothing else"
    messages = [ikc_name(name) for name in ("MISMATCH_MESSAGE", "ACCEPTED_MESSAGE", "UNREADABLE_MESSAGE")]
    assert all(isinstance(message, str) and message.strip() for message in messages) and len(set(messages)) == 3, f"three distinct non-empty messages: {messages}"
    print_success("names ok")


def test_the_check_path_is_in_the_current_data_directory_at_each_call(world, tmp_path):
    """(a) ``instance_key_check_path()`` is ``<data directory>/secrets/instance.key.check`` and follows the data directory, as ``instance_key_path()`` does."""
    path_of = ikc_name("instance_key_check_path")
    assert path_of() == world.check_file, f"in the data directory of the test: {path_of()}"
    other = (tmp_path / "other-data").resolve()
    other.mkdir()
    world.monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(other))
    assert path_of() == other / "secrets" / "instance.key.check", f"read at each call, not kept: {path_of()}"


@pytest.mark.parametrize(("raw", "expected"), [(None, False), ("", False), ("  ", False), ("0", False), ("false", False), ("No", False), ("OFF", False), ("1", True), ("true", True), ("YES", True), (" on ", True)])
def test_the_accept_variable_has_the_values_of_the_awaiting_restore_switch(world, raw, expected):
    """(a) ``instance_key_accept()`` reads ``LIBREFOLIO_INSTANCE_KEY_ACCEPT`` with ``awaiting_restore()``'s values: unset or blank is False."""
    reader = getattr(platform_config, "instance_key_accept", _MISSING)
    if reader is _MISSING:
        pytest.fail("H5-7: backend.app.config.platform gives no instance_key_accept")
    if raw is None:
        world.monkeypatch.delenv(ACCEPT_VARIABLE, raising=False)
    else:
        world.monkeypatch.setenv(ACCEPT_VARIABLE, raw)
    assert reader() is expected, f"{ACCEPT_VARIABLE}={raw!r} is {expected}"


@pytest.mark.parametrize("raw", ["maybe", "2", "enabled", "y", "tru"])
def test_an_invalid_accept_value_raises_naming_the_variable(world, raw):
    """(a) Any other value raises ``ValueError`` naming the variable."""
    reader = getattr(platform_config, "instance_key_accept", _MISSING)
    if reader is _MISSING:
        pytest.fail("H5-7: backend.app.config.platform gives no instance_key_accept")
    world.monkeypatch.setenv(ACCEPT_VARIABLE, raw)
    with pytest.raises(ValueError, match=ACCEPT_VARIABLE):
        reader()


def test_the_accept_variable_is_read_at_each_call(world):
    """(a) No memory: the value of now is the answer of now."""
    reader = getattr(platform_config, "instance_key_accept", _MISSING)
    if reader is _MISSING:
        pytest.fail("H5-7: backend.app.config.platform gives no instance_key_accept")
    answers = []
    for raw in ("1", None, "0", "true", None):
        if raw is None:
            world.monkeypatch.delenv(ACCEPT_VARIABLE, raising=False)
        else:
            world.monkeypatch.setenv(ACCEPT_VARIABLE, raw)
        answers.append(reader())
    assert answers == [True, False, False, True, False], f"each call reads the variable: {answers}"


@pytest.mark.parametrize("raw", ["maybe", "2", "enabled"])
def test_the_start_stops_on_an_invalid_accept_value_as_it_does_for_the_awaiting_restore_one(world, raw):
    """(a) ``log_configuration_audit()`` raises ``ValueError`` naming the variable: an unreadable value stops the start, never leaves the choice to chance.
    Barrier: with ``1`` the same audit goes on (returns None)."""
    world.set_key(KEY_A)
    world.monkeypatch.setenv(ACCEPT_VARIABLE, "1")
    assert config_audit.log_configuration_audit() is None, "Barrier: with a valid value the audit goes on"
    world.monkeypatch.setenv(ACCEPT_VARIABLE, raw)
    with pytest.raises(ValueError, match=ACCEPT_VARIABLE):
        config_audit.log_configuration_audit()


# =============================================================================
# (b) key_check_value
# =============================================================================


def test_the_check_value_is_64_lowercase_hex_of_the_contracts_formula(world):
    """(b) ``key_check_value()`` is the HMAC-SHA256 of the label under ``derive_key("instance.key-check.v1", 32)``, in lowercase hex."""
    value_of = ikc_name("key_check_value")
    world.set_key(KEY_A)
    value = value_of()
    assert HEX64.fullmatch(value), f"64 lowercase hex characters: {value!r}"
    assert value == expected_value(KEY_A), "the contract's formula"
    assert value == hmac.new(derive_key(PURPOSE, 32), LABEL, hashlib.sha256).hexdigest(), "from the instance key in force, through derive_key"


def test_the_same_key_gives_the_same_value_and_another_key_another(world):
    """(b) Stable for a key, different for another; never the key, a derived key or their text."""
    value_of = ikc_name("key_check_value")
    values = {}
    for key in (KEY_A, KEY_B, KEY_C, KEY_A):
        world.set_key(key)
        values.setdefault(key, set()).add(value_of())
    assert all(len(found) == 1 for found in values.values()), f"the same key, the same value, however often: {values}"
    assert len({next(iter(found)) for found in values.values()}) == 3, f"three keys, three values: {values}"
    for key, found in values.items():
        value = next(iter(found))
        forbidden = {key, derive_key_from(key, PURPOSE, 32).hex(), derive_key_from(key, "plugins.settings.v1", 32).hex(), key_id_of(derive_key_from(key, "plugins.settings.v1", 32))}
        assert value not in forbidden and key not in value, "never the key nor a derived key"


def test_an_unusable_key_raises_instance_key_error(world):
    """(b) A key that cannot be used raises ``InstanceKeyError`` (the one of ``instance_key.py``)."""
    value_of = ikc_name("key_check_value")
    world.set_key("too-short")
    with pytest.raises(InstanceKeyError):
        value_of()


# =============================================================================
# (c) instance_key_state: step 1, nothing to compare
# =============================================================================


@pytest.mark.asyncio
async def test_without_a_key_the_state_is_ok_and_nothing_is_created(world, db):
    """(c) Step 1: ``not_created`` is ``ok`` even with foreign secrets stored and a check file there: the key is never generated by the check, no file made."""
    await db.add_secret("system", readable=False)
    world.write_check(expected_value(KEY_B))
    before = world.files()
    assert await state_of(db) == "ok", "no key, nothing to compare"
    assert world.files() == before and not world.key_file.exists(), f"no key generated, no file made: {world.files()}"


@pytest.mark.asyncio
async def test_without_a_key_and_without_anything_the_state_is_ok_and_the_folder_is_not_made(world, db):
    """(c) A fresh install: ``ok``, and neither ``secrets/`` nor any file appears."""
    assert await state_of(db) == "ok"
    assert not world.secrets.exists() and world.files() == [], "a state read creates nothing"


@pytest.mark.asyncio
@pytest.mark.parametrize("how", ["env", "key-file"])
async def test_a_key_that_cannot_be_used_is_ok_whatever_the_check_file_says(world, db, how):
    """(c) Step 1: a short configured key, or a short generated key file, is ``ok`` against a check file of another value: ``problem`` first."""
    if how == "env":
        world.set_key("short")
    else:
        world.write_key_file("short")
    world.write_check(expected_value(KEY_B))
    await db.add_secret("system", readable=False)
    assert await state_of(db) == "ok", f"{how}: a key that cannot be used is not a mismatch"


# =============================================================================
# (c) instance_key_state: step 2, the check file decides
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("ending", ["", "\n"], ids=["no-newline", "one-newline"])
async def test_a_check_file_of_the_keys_value_is_ok(world, db, ending):
    """(c) Step 2: the 64 hex characters, one trailing newline allowed, equal to ``key_check_value()``: ``ok``."""
    world.set_key(KEY_A)
    world.write_check(expected_value(KEY_A) + ending)
    assert await state_of(db) == "ok"


@pytest.mark.asyncio
@pytest.mark.parametrize("ending", ["", "\n"], ids=["no-newline", "one-newline"])
async def test_a_check_file_of_another_keys_value_is_a_mismatch(world, db, ending):
    """(c) Step 2: a well-formed value of another key is ``mismatch``."""
    world.set_key(KEY_A)
    world.write_check(expected_value(KEY_B) + ending)
    assert await state_of(db) == "mismatch"


@pytest.mark.asyncio
async def test_the_check_file_decides_before_the_stored_secrets(world, db):
    """(c) The file wins over R1 both ways: a different value is ``mismatch`` with every secret readable; the right value is ``ok`` with every secret foreign."""
    world.set_key(KEY_A)
    await db.add_secret("system", readable=True)
    world.write_check(expected_value(KEY_B))
    assert await state_of(db) == "mismatch", "other key's value, readable secrets: the file decides"
    world.write_check(expected_value(KEY_A))
    await db.add_secret("system", readable=False)
    async with db.session() as session:
        await session.execute(PluginSystemSetting.__table__.delete().where(PluginSystemSetting.key_id == key_id_of(settings_subkey())))
        await session.commit()
    assert await state_of(db) == "ok", "the key's own value, only foreign secrets: the file decides"


@pytest.mark.asyncio
async def test_a_check_file_with_a_key_file_beside_it_is_compared_with_the_generated_key(world, db):
    """(c) The generated key (``secrets/instance.key``) is compared like a configured one."""
    world.write_key_file(KEY_A)
    world.write_check(expected_value(KEY_A))
    assert await state_of(db) == "ok"
    world.write_key_file(KEY_B)
    assert await state_of(db) == "mismatch", "the key file replaced by another: the next call says mismatch"


@pytest.mark.asyncio
async def test_with_a_check_file_the_database_is_not_asked(world, empty_db):
    """(c) A database with no table (every query fails): the file's answer stands, ``mismatch`` and ``ok``, without a warning: step 3 is never reached."""
    world.set_key(KEY_A)
    with captured() as logs:
        world.write_check(expected_value(KEY_B))
        first = await state_of(empty_db)
        world.write_check(expected_value(KEY_A))
        second = await state_of(empty_db)
    assert (first, second) == ("mismatch", "ok"), f"the file decides: {first}, {second}"
    assert logs.at(*LEVELS_ABOVE_INFO) == [], f"no query failed, since none was made: {logs.events}"


MALFORMED = {
    "empty": "",
    "newline-only": "\n",
    "63-hex": "a" * 63,
    "65-hex": "a" * 65,
    "64-not-hex": CANARY,
    "text": "this is not a check value",
    "two-lines": "a" * 64 + "\n" + "a" * 64,
}


@pytest.mark.asyncio
@pytest.mark.parametrize("content", list(MALFORMED.values()), ids=list(MALFORMED))
async def test_a_check_file_that_is_not_64_hex_is_ok_and_its_content_is_never_logged(world, db, content):
    """(c) Step 2: present but not 64 hex characters is ``ok`` (a file that cannot be understood is not a wrong key), and the content reaches no log."""
    world.set_key(KEY_A)
    world.write_check(content)
    with captured() as logs:
        found = await state_of(db)
    assert found == "ok", f"not a check value: ok, not a mismatch: {found}"
    assert CANARY not in logs.text() and (not content.strip() or content.strip() not in logs.text()), f"the content is never logged: {logs.events}"
    assert_no_secret_in(logs.text(), KEY_A)


@pytest.mark.asyncio
async def test_a_folder_in_place_of_the_check_file_is_ok(world, db):
    """(c) Step 2: present but unreadable (a folder in its place) is ``ok``, never raises."""
    world.set_key(KEY_A)
    world.secrets.mkdir(mode=0o700)
    world.check_file.mkdir()
    assert await state_of(db) == "ok"


@pytest.mark.asyncio
async def test_a_check_file_without_read_permission_is_ok(world, db):
    """(c) Step 2: present but unreadable (permissions) is ``ok``, never raises."""
    needs_a_user_the_modes_bind()
    world.set_key(KEY_A)
    path = world.write_check(expected_value(KEY_B), mode=0o000)
    try:
        assert await state_of(db) == "ok", "a file nobody can read says nothing about the key"
    finally:
        path.chmod(0o600)


# =============================================================================
# (c) instance_key_state: step 3, no file: R1 on the stored secrets
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("rows", "expected"),
    [
        pytest.param([], "ok", id="no-row"),
        pytest.param([("plain", "system"), ("plain", "user")], "ok", id="plain-values-only"),
        pytest.param([("readable", "system")], "ok", id="one-readable"),
        pytest.param([("readable", "system"), ("readable", "user")], "ok", id="all-readable"),
        pytest.param([("foreign", "system"), ("readable", "system")], "ok", id="mixed-system"),
        pytest.param([("foreign", "system"), ("foreign", "system"), ("readable", "user")], "ok", id="foreign-system-readable-user"),
        pytest.param([("foreign", "user"), ("foreign", "user"), ("readable", "system")], "ok", id="foreign-user-readable-system"),
        pytest.param([("foreign", "system")], "mismatch", id="one-foreign-system"),
        pytest.param([("foreign", "system"), ("foreign", "system"), ("foreign", "system")], "mismatch", id="all-foreign-system"),
        pytest.param([("foreign", "user")], "mismatch", id="one-foreign-user"),
        pytest.param([("foreign", "system"), ("foreign", "user"), ("foreign", "user")], "mismatch", id="all-foreign-both-scopes"),
        pytest.param([("plain", "system"), ("plain", "user"), ("foreign", "system")], "mismatch", id="plain-rows-do-not-count"),
    ],
)
async def test_without_a_check_file_the_state_is_the_stored_secrets_all_foreign_or_not(world, db, rows, expected):
    """(c) Step 3 (R1): ``mismatch`` only when there is at least one stored secret and EVERY one (system and user) is under another key; some readable row, or none, is ``ok``."""
    world.set_key(KEY_A)
    for kind, scope in rows:
        if kind == "plain":
            await db.add_plain(scope)
        else:
            await db.add_secret(scope, readable=kind == "readable")
    assert await state_of(db) == expected, f"{rows}: {expected}"
    assert not world.secrets.exists(), "R1 reads, writes nothing: no check file, no folder"


@pytest.mark.asyncio
async def test_a_failing_query_is_ok_and_never_raises(world, empty_db):
    """(c) Step 3: a database that cannot be asked is ``ok`` (the warning, once per process, is measured in a child interpreter below)."""
    world.set_key(KEY_A)
    assert await state_of(empty_db) == "ok"
    assert not world.secrets.exists(), "nothing written"


@pytest.mark.asyncio
async def test_the_state_is_recomputed_at_every_call_from_the_key_the_file_and_the_rows(world, db):
    """(c) No memory (the lesson of H5-5): one process, one database, the key, the file and the rows changed between calls; each call answers for NOW."""
    world.set_key(KEY_A)
    await db.add_secret("system", readable=True)
    await db.add_secret("user", readable=True)
    assert await state_of(db) == "ok", "key A, secrets under A, no file: ok"
    world.set_key(KEY_B)
    assert await state_of(db) == "mismatch", "the key changed under the same rows, no file: every secret is foreign now"
    world.write_check(expected_value(KEY_B))
    assert await state_of(db) == "ok", "a file written for B: ok at once"
    world.set_key(KEY_A)
    assert await state_of(db) == "mismatch", "key A again against B's file: mismatch at once"
    world.check_file.unlink()
    assert await state_of(db) == "ok", "the file gone: R1, the secrets are A's: ok at once"
    world.write_check(expected_value(KEY_B))
    assert await state_of(db) == "mismatch", "a file of another value written meanwhile: mismatch at once"
    world.write_check(expected_value(KEY_A))
    assert await state_of(db) == "ok", "and back"


# =============================================================================
# The once-per-process warning, in child interpreters
# =============================================================================

CHILD = """
import asyncio, json, sys
from structlog.testing import capture_logs
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from backend.app.services.platform import instance_key_check as m

async def main(url):
    engine = create_async_engine(url, poolclass=NullPool)
    states = []
    try:
        with capture_logs() as events:
            for _ in range(4):
                async with AsyncSession(engine) as session:
                    states.append(await m.instance_key_state(session))
    finally:
        await engine.dispose()
    warnings = [e for e in events if e.get("log_level") == "warning"]
    print("RESULT" + json.dumps({"states": states, "warnings": len(warnings), "events": repr(events)}))

asyncio.run(main(sys.argv[1]))
"""


def run_child(world: World, url: str) -> dict[str, Any]:
    ikc()
    environment = {**os.environ, "LIBREFOLIO_TEST_MODE": "1", "LIBREFOLIO_TEST_DATA_DIR": str(world.data), "LIBREFOLIO_INSTANCE_KEY": KEY_A, "PYTHONPATH": str(Path(__file__).resolve().parents[3])}
    environment.pop(ACCEPT_VARIABLE, None)
    done = subprocess.run([sys.executable, "-c", CHILD, url], capture_output=True, text=True, timeout=300, cwd=Path(__file__).resolve().parents[3], env=environment, check=False)
    assert done.returncode == 0, f"the child interpreter failed: {done.stderr[-2000:]}"
    line = next((line for line in done.stdout.splitlines() if line.startswith("RESULT")), None)
    assert line is not None, f"the child gave no result: {done.stdout[-500:]} {done.stderr[-500:]}"
    return json.loads(line[len("RESULT") :])


@pytest.mark.parametrize("failure", ["folder", "not-hex", "empty", "query"])
def test_a_check_that_cannot_be_read_warns_once_per_process_and_never_per_request(world, schema_db, tmp_path, failure):
    """(c) Four calls in one process meet the same failure (a folder in the file's place, a file that is not 64 hex characters, an empty one, a failing query): ``ok`` each time, ONE warning in all, never the content."""
    path, _user = schema_db
    url = f"sqlite+aiosqlite:///{path}"
    if failure == "folder":
        world.secrets.mkdir(mode=0o700)
        world.check_file.mkdir()
    elif failure == "not-hex":
        world.write_check(CANARY)
    elif failure == "empty":
        world.write_check("")
    else:
        broken = tmp_path / "child-no-tables.db"
        sqlite3.connect(broken).close()
        url = f"sqlite+aiosqlite:///{broken}"

    result = run_child(world, url)

    assert result["states"] == ["ok"] * 4, f"{failure}: ok every time: {result['states']}"
    assert result["warnings"] == 1, f"{failure}: exactly one warning for four calls of one process: {result['events']}"
    assert CANARY not in result["events"], f"{failure}: the content of the file reached the log"
    assert_no_secret_in(result["events"], KEY_A)


def test_a_process_with_a_good_check_file_warns_of_nothing(world, schema_db):
    """(c) Barrier of the child: with a right value in the file, four calls give ``ok`` and no warning at all, so the one warning above is the failure's."""
    path, _user = schema_db
    world.write_check(expected_value(KEY_A))
    result = run_child(world, f"sqlite+aiosqlite:///{path}")
    assert (result["states"], result["warnings"]) == (["ok"] * 4, 0), f"nothing to warn of: {result}"


# =============================================================================
# (d) check_instance_key_at_start
# =============================================================================


@pytest.mark.asyncio
async def test_with_no_file_and_ok_the_start_writes_the_value_with_the_right_modes_and_says_nothing(world, db):
    """(d) No file, state ``ok``: the check file is written (the value, ``0600`` in a new folder ``0700``), no warning, no error; the state stays ``ok``."""
    needs_posix_modes()
    world.set_key(KEY_A)
    await db.add_secret("system", readable=True)
    with captured() as logs:
        await start_on(db)
    assert world.check_file.read_text(encoding="utf-8").strip() == expected_value(KEY_A), "the file holds the key's check value"
    assert HEX64.fullmatch(world.check_file.read_text(encoding="utf-8").strip())
    assert (world.check_file.stat().st_mode & 0o777, world.secrets.stat().st_mode & 0o777) == (0o600, 0o700), "file 0600 in a folder 0700"
    assert sorted(path.name for path in world.secrets.iterdir()) == ["instance.key.check"], "no temporary file left behind"
    assert logs.at(*LEVELS_ABOVE_INFO) == [], f"silent: {logs.events}"
    assert await state_of(db) == "ok"
    assert_no_secret_in(logs.text(), KEY_A)


@pytest.mark.asyncio
async def test_the_start_writes_the_check_beside_a_generated_key_and_leaves_the_key_alone(world, db):
    """(d) A generated key file: the check lands in the same folder, and ``instance.key`` is byte for byte what it was."""
    key_file = world.write_key_file(KEY_A)
    before = key_file.read_bytes()
    await start_on(db)
    assert key_file.read_bytes() == before, "the key file is never touched"
    assert world.check_file.read_text(encoding="utf-8").strip() == expected_value(KEY_A)


@pytest.mark.asyncio
async def test_with_no_key_at_all_the_start_writes_nothing_and_generates_no_key(world, db):
    """(d) Step 1 says nothing can be compared: no check file, no key generated, even with the accept variable set."""
    for accept in (False, True):
        world.accept(accept)
        await start_on(db)
        assert world.files() == [] and not world.secrets.exists(), f"accept={accept}: nothing written, no key generated: {world.files()}"


@pytest.mark.asyncio
async def test_with_an_unusable_key_the_start_writes_nothing_even_with_accept(world, db):
    """(d) A key that cannot be used: no check file (there is no value to store)."""
    world.set_key("short")
    for accept in (False, True):
        world.accept(accept)
        await start_on(db)
        assert world.files() == [], f"accept={accept}: nothing written: {world.files()}"


@pytest.mark.asyncio
async def test_with_no_file_and_every_secret_foreign_the_start_logs_one_error_and_writes_nothing(world, db):
    """(d) No file, R1 says ``mismatch``: one ERROR line (the mismatch message) and NOTHING written: writing would bless the wrong key. The state stays ``mismatch``."""
    world.set_key(KEY_A)
    await db.add_secret("system", readable=False)
    await db.add_secret("user", readable=False)
    with captured() as logs:
        await start_on(db)
    errors = logs.at("error", "critical")
    assert [event.get("event") for event in errors] == [ikc_name("MISMATCH_MESSAGE")], f"one error line, the mismatch message: {logs.events}"
    assert world.files() == [], f"nothing written: {world.files()}"
    assert await state_of(db) == "mismatch", "and still a mismatch"
    assert_no_secret_in(logs.text(), KEY_A)


@pytest.mark.asyncio
async def test_with_no_file_and_some_readable_secret_the_start_writes_the_value(world, db):
    """(d) No file, one secret readable among foreign ones: ``ok`` by R1, so the file is written."""
    world.set_key(KEY_A)
    await db.add_secret("system", readable=False)
    await db.add_secret("system", readable=True)
    await start_on(db)
    assert world.check_file.read_text(encoding="utf-8").strip() == expected_value(KEY_A)


@pytest.mark.asyncio
async def test_with_a_file_of_another_key_the_start_logs_one_error_and_never_rewrites_it(world, db):
    """(d) File present, ``mismatch``: one error line, the file byte for byte as it was (no accept variable)."""
    world.set_key(KEY_A)
    wrong = expected_value(KEY_B) + "\n"
    world.write_check(wrong)
    with captured() as logs:
        await start_on(db)
    assert [event.get("event") for event in logs.at("error", "critical")] == [ikc_name("MISMATCH_MESSAGE")], f"one error line: {logs.events}"
    assert world.check_file.read_text(encoding="utf-8") == wrong, "an existing wrong file is NOT overwritten without the accept variable"
    assert await state_of(db) == "mismatch"
    assert_no_secret_in(logs.text(), KEY_A, KEY_B)


@pytest.mark.asyncio
@pytest.mark.parametrize("ending", ["", "\n"], ids=["no-newline", "one-newline"])
async def test_with_a_file_of_this_key_the_start_is_silent_and_rewrites_nothing(world, db, ending):
    """(d) File present, ``ok``: no line at warning or above, the file is not touched."""
    world.set_key(KEY_A)
    path = world.write_check(expected_value(KEY_A) + ending)
    os.utime(path, (1_000_000_000, 1_000_000_000))
    with captured() as logs:
        await start_on(db)
    assert logs.at(*LEVELS_ABOVE_INFO) == [], f"silent: {logs.events}"
    assert path.read_text(encoding="utf-8") == expected_value(KEY_A) + ending and int(path.stat().st_mtime) == 1_000_000_000, "an ok file is left as it is"


@pytest.mark.asyncio
async def test_a_file_that_cannot_be_understood_is_not_rewritten_without_accept(world, db):
    """(d) File present and garbage: state ``ok``, so the start neither logs an error nor replaces it."""
    world.set_key(KEY_A)
    world.write_check("garbage")
    with captured() as logs:
        await start_on(db)
    assert logs.at("error", "critical") == [], f"not a mismatch: no error: {logs.events}"
    assert world.check_file.read_text(encoding="utf-8") == "garbage", "never replaced without accept"


@pytest.mark.asyncio
async def test_accept_replaces_a_wrong_file_with_one_warning_and_the_right_modes(world, db):
    """(d) ``LIBREFOLIO_INSTANCE_KEY_ACCEPT=1``: the file of another key is replaced (atomically: no temporary file left) by this key's value, ``0600`` in ``0700``; one WARNING (the accepted message), no error, never the value."""
    needs_posix_modes()
    world.set_key(KEY_A)
    world.write_check(expected_value(KEY_B), mode=0o644)
    world.accept()
    with captured() as logs:
        await start_on(db)
    assert world.check_file.read_text(encoding="utf-8").strip() == expected_value(KEY_A), "the accepted key's value"
    assert world.check_file.stat().st_mode & 0o777 == 0o600, "file 0600"
    assert sorted(path.name for path in world.secrets.iterdir()) == ["instance.key.check"], "no temporary file left behind"
    assert [event.get("event") for event in logs.at("warning")] == [ikc_name("ACCEPTED_MESSAGE")], f"one warning, the accepted message: {logs.events}"
    assert logs.at("error", "critical") == [], f"accepted, so no mismatch error: {logs.events}"
    assert await state_of(db) == "ok"
    assert_no_secret_in(logs.text(), KEY_A, KEY_B)


@pytest.mark.asyncio
async def test_accept_overrides_a_mismatch_by_the_secrets_when_no_file_exists(world, db):
    """(d) Every secret foreign and no file: without accept nothing is written; with it the value is written and the instance stops being a mismatch."""
    world.set_key(KEY_A)
    await db.add_secret("system", readable=False)
    await start_on(db)
    assert world.files() == [], "without accept: nothing written"
    world.accept()
    await start_on(db)
    assert world.check_file.read_text(encoding="utf-8").strip() == expected_value(KEY_A), "with accept: written"
    assert await state_of(db) == "ok"


@pytest.mark.asyncio
async def test_accept_warns_at_every_start_even_when_nothing_changed(world, db):
    """(d) While the variable is set, each start logs the warning, also when the file already holds the value; read at each call, so unset it stops the warnings."""
    world.set_key(KEY_A)
    world.write_check(expected_value(KEY_A))
    world.accept()
    counts = []
    for _ in range(3):
        with captured() as logs:
            await start_on(db)
        counts.append([event.get("event") for event in logs.at("warning")])
    assert counts == [[ikc_name("ACCEPTED_MESSAGE")]] * 3, f"one accepted warning per start: {counts}"
    world.accept(False)
    with captured() as logs:
        await start_on(db)
    assert logs.at(*LEVELS_ABOVE_INFO) == [], f"unset, silent again: {logs.events}"


@pytest.mark.asyncio
async def test_accept_replaces_a_file_that_cannot_be_understood(world, db):
    """(d) Garbage in the file and accept: replaced by the value."""
    world.set_key(KEY_A)
    world.write_check("garbage")
    world.accept()
    await start_on(db)
    assert world.check_file.read_text(encoding="utf-8").strip() == expected_value(KEY_A)


@pytest.mark.asyncio
async def test_the_start_never_raises_when_the_file_cannot_be_written(world, db):
    """(d) A ``secrets/`` folder nobody can write to: the start goes on (returns None), one warning naming the class only, no file, no key in the log."""
    needs_a_user_the_modes_bind()
    world.set_key(KEY_A)
    world.secrets.mkdir(mode=0o700)
    world.secrets.chmod(0o500)
    try:
        with captured() as logs:
            await start_on(db)
        assert world.files() == [], "nothing could be written"
        assert logs.at("warning"), f"the failure is told: {logs.events}"
        assert "PermissionError" in logs.text(), f"naming the class: {logs.events}"
        assert str(world.data) not in logs.text(), f"never a path: {logs.events}"
        assert_no_secret_in(logs.text(), KEY_A)
    finally:
        world.secrets.chmod(0o700)


@pytest.mark.asyncio
async def test_the_start_never_raises_on_a_database_that_cannot_be_asked(world, empty_db):
    """(d) No file and a failing query: the start returns None (R1 failing is ``ok``, so the file is written)."""
    world.set_key(KEY_A)
    await start_on(empty_db)
    assert world.check_file.read_text(encoding="utf-8").strip() == expected_value(KEY_A)


def test_two_or_more_workers_starting_together_leave_one_valid_file(world, schema_db):
    """(d) Several workers, each its own loop and connection, start at the same instant on a data directory with no check file: one valid file (the key's value, ``0600``), no temporary file, nobody raised."""
    needs_posix_modes()
    path, _user = schema_db
    world.set_key(KEY_A)
    function = ikc_name("check_instance_key_at_start")
    url = f"sqlite+aiosqlite:///{path}"
    workers = 6
    errors: list[BaseException] = []

    def worker(barrier: threading.Barrier) -> None:
        async def run() -> None:
            engine = create_async_engine(url, poolclass=NullPool)
            try:
                async with AsyncSession(engine) as session:
                    barrier.wait(timeout=60)
                    await function(session)
            finally:
                await engine.dispose()

        try:
            asyncio.run(run())
        except BaseException as exc:  # noqa: BLE001 — collected for the assertion
            errors.append(exc)

    for round_number in range(5):
        if world.secrets.exists():
            for leftover in world.secrets.iterdir():
                leftover.unlink()
            world.secrets.rmdir()
        barrier = threading.Barrier(workers)
        threads = [threading.Thread(target=worker, args=(barrier,)) for _ in range(workers)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=120)
        assert errors == [], f"round {round_number}: no worker raised: {errors}"
        assert sorted(item.name for item in world.secrets.iterdir()) == ["instance.key.check"], f"round {round_number}: one file, no temporary one"
        assert world.check_file.read_text(encoding="utf-8").strip() == expected_value(KEY_A), f"round {round_number}: the file holds the value, whole"
        assert world.check_file.stat().st_mode & 0o777 == 0o600, f"round {round_number}: 0600"


@pytest.mark.asyncio
@pytest.mark.parametrize("path_name", ["accept", "absent-ok", "absent-mismatch", "present-mismatch", "present-garbage"])
async def test_no_start_path_logs_a_key_a_check_value_or_a_file_content(world, db, path_name):
    """(d) Every path of the start, with another key's value, a garbage canary and a secret stored: the log holds codes only."""
    world.set_key(KEY_A)
    if path_name == "absent-mismatch":
        await db.add_secret("system", readable=False)
    if path_name == "present-mismatch":
        world.write_check(expected_value(KEY_B))
    if path_name == "present-garbage":
        world.write_check(CANARY)
    if path_name == "accept":
        world.write_check(expected_value(KEY_B))
        world.accept()
    with captured() as logs:
        await start_on(db)
        await state_of(db)
    assert CANARY not in logs.text(), f"{path_name}: a file's content reached the log"
    assert_no_secret_in(logs.text(), KEY_A, KEY_B)


# =============================================================================
# (e) The startup step
# =============================================================================


def _steps() -> list[Any]:
    return list(app_lifespan.STARTUP_STEPS)


def _instance_key_step() -> Any:
    matching = [step for step in _steps() if step.name == "instance-key-check"]
    if len(matching) != 1:
        pytest.fail(f"H5-7: one startup step instance-key-check expected, found {[step.name for step in _steps()]}")
    return matching[0]


def test_the_step_stands_right_after_the_plugin_secrets_check_and_blocks_nothing():
    """(e) ``instance-key-check`` is the step right after ``plugin-secrets-check``, with no ``skip_when`` (it runs while awaiting a restore too) and not blocking."""
    step = _instance_key_step()
    names = [item.name for item in _steps()]
    assert names.index("instance-key-check") == names.index("plugin-secrets-check") + 1, f"right after plugin-secrets-check: {names}"
    assert step.skip_when is None, "no skip_when: the check runs on every start"
    assert step.blocking is False, "not blocking"


@pytest.mark.asyncio
async def test_the_step_awaits_the_start_check_on_its_own_session_and_writes_the_file(world, db, monkeypatch):
    """(e) Run for real on a private engine in place of ``get_async_engine`` (wherever the app reads it): the step returns an awaitable, awaited to its end, and the check file is there; a second run changes nothing."""
    world.set_key(KEY_A)
    step = _instance_key_step()
    engine = db.engine
    monkeypatch.setattr(db_session_module, "get_async_engine", lambda: engine)
    monkeypatch.setattr(app_lifespan, "get_async_engine", lambda: engine)
    monkeypatch.setattr(ikc(), "get_async_engine", lambda: engine, raising=False)

    returned = step.run()
    assert inspect.isawaitable(returned), f"the step returns the check for the runner to await, not {returned!r}"
    await asyncio.wait_for(returned, 60)

    assert world.check_file.read_text(encoding="utf-8").strip() == expected_value(KEY_A), "the step ran the start check to its end"
    before = world.check_file.read_bytes()
    again = step.run()
    await asyncio.wait_for(again, 60)
    assert world.check_file.read_bytes() == before, "a second start finds the file and leaves it"


# =============================================================================
# (f) check_instance_key: the Security tab
# =============================================================================


@pytest.mark.asyncio
async def test_the_security_check_is_ok_without_a_mismatch(world, db):
    """(f) ``ConfigCheck("platform.instance_key_check", "ok", "instance.checks.instanceKey.ok")`` and nothing else, for no key, a right file and no file."""
    check = ikc_name("check_instance_key")
    expected = ConfigCheck(CHECK_ID, "ok", OK_KEY)
    for prepare in ("no-key", "right-file", "no-file"):
        if prepare == "right-file":
            world.set_key(KEY_A)
            world.write_check(expected_value(KEY_A))
        if prepare == "no-file":
            world.check_file.unlink()
        async with db.session() as session:
            result = await check(session)
        assert result == expected, f"{prepare}: {result!r}"


@pytest.mark.asyncio
@pytest.mark.parametrize("by", ["file", "secrets"])
async def test_the_security_check_is_an_error_without_parameters_on_a_mismatch(world, db, by):
    """(f) A mismatch is an ``error`` with the mismatch key, an empty ``detail`` and an English summary that holds no key and no value."""
    check = ikc_name("check_instance_key")
    world.set_key(KEY_A)
    if by == "file":
        world.write_check(expected_value(KEY_B))
    else:
        await db.add_secret("system", readable=False)
    async with db.session() as session:
        result = await check(session)
    assert isinstance(result, ConfigCheck), f"a ConfigCheck: {result!r}"
    assert (result.check_id, result.severity, result.i18n_key, result.detail) == (CHECK_ID, "error", MISMATCH_KEY, {}), f"{by}: {result!r}"
    assert result.summary.strip(), "an English detail for the log"
    assert_no_secret_in(repr(result), KEY_A, KEY_B)

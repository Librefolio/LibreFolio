"""The two settings of the clean-up of the kept backups (workstream B, lot FB-24, contract ``B6r-fb24-backend-interface`` §4).

``backup_cleanup_max_mb`` (the most the kept backups may weigh together, in MiB) and ``backup_cleanup_max_days`` (the
oldest a kept backup may be, in days), both global settings of type ``int``; 0 is off. The cleaning itself is
``test_backup_retention.py``'s; here the values.

(a) ``GLOBAL_SETTINGS_DEFAULTS`` lists both, type ``int``, value ``"0"``; a save accepts ``0`` to ``1048576`` and ``0`` to
    ``3650`` (integers only, surrounding spaces dropped) and refuses the rest; the startup seeds both rows with ``0``, not
    written by any administrator.
(b) The value a setting has *now* (``get_setting_value``, ``get_global_setting``, ``get_all_global_settings``,
    ``effective_stored_value``) while no administrator wrote its row (missing, or ``updated_by_user_id`` empty): on a
    ``selfhosted`` instance the default, 0 (the clean-up is off); on a ``managed`` one (``LIBREFOLIO_PROFILE``) 250 MB and 30
    days. From the first save of an administrator on, the row wins, even a ``0`` on the days. ``get_setting_value`` answers
    an ``int`` in every case, the pinned one too. The profile pins no other setting.
(c) The profile ``managed`` refuses to save ``backup_cleanup_max_mb`` as ``0`` (the space cannot be switched off):
    ``GlobalSettingValueError``, the key among its errors, nothing written, nothing of the same save written either (all or
    nothing); ``backup_cleanup_max_days`` as ``0`` it accepts (the age can). A ``selfhosted`` instance accepts ``0`` on both.
(d) ``retention.read_policy()``, synchronous: the two values as (b) gives them, from the database, as a ``CleanupPolicy``
    of ``int``; a value that is not a whole number of at least 0, a database it cannot open or one without the table: off
    (0 and 0), never an exception.

How: a private SQLite file under ``tmp_path`` with the whole ORM schema and the seeded global settings, read by the async
services and, for (d), by a synchronous engine on the same file put in place of the process's (``get_sync_engine``); the
profile through ``monkeypatch`` (``get_settings()`` reads it at each call). Isolation: pure. No lane database, no server,
no network.
"""

from __future__ import annotations

import asyncio
import importlib
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import create_engine, delete, select, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.db.base import SQLModel  # imports every model: SQLModel.metadata holds the whole schema
from backend.app.db.models import GlobalSetting, User
from backend.app.schemas.settings import GLOBAL_SETTINGS_DEFAULTS, validate_global_setting_value
from backend.app.services.accounts import settings_service
from backend.app.services.accounts.global_settings_service import effective_stored_value, get_setting_value
from backend.app.services.accounts.settings_service import GlobalSettingValueError
from backend.test_scripts.test_utils import print_section, print_success

RETENTION = "backend.app.services.platform.instance_backup.retention"
PROFILE_VARIABLE = "LIBREFOLIO_PROFILE"
MB_KEY = "backup_cleanup_max_mb"
DAYS_KEY = "backup_cleanup_max_days"
#: (key, largest value a save accepts)
LIMITS = [pytest.param(MB_KEY, 1048576, id="max_mb"), pytest.param(DAYS_KEY, 3650, id="max_days")]
#: What the profile ``managed`` gives while no administrator wrote the row.
MANAGED = {MB_KEY: 250, DAYS_KEY: 30}


@pytest.fixture(autouse=True)
def _no_inherited_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    """A test sees the profile it sets itself, ``selfhosted`` otherwise."""
    monkeypatch.setenv(PROFILE_VARIABLE, "selfhosted")


def managed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(PROFILE_VARIABLE, "managed")
    from backend.app.config import get_settings  # noqa: PLC0415 — read after the environment is set

    assert get_settings().LIBREFOLIO_PROFILE == "managed", "barrier: the profile is managed"


@pytest_asyncio.fixture
async def database(tmp_path: Path) -> AsyncIterator[tuple[AsyncEngine, Path]]:
    """A private SQLite file with the whole ORM schema and the default global settings (``updated_by_user_id`` NULL)."""
    path = tmp_path / "backup_cleanup_settings.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(engine) as session:
            await settings_service.initialize_global_settings(session)
        yield engine, path
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def engine(database: tuple[AsyncEngine, Path]) -> AsyncEngine:
    return database[0]


async def _add_admin(engine: AsyncEngine) -> User:
    username = f"fb24_admin_{uuid4().hex[:8]}"
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username=username, email=f"{username}@example.com", hashed_password="marker-hash-not-bcrypt", is_active=True)
        session.add(user)
        await session.commit()
    return user


async def _save(engine: AsyncEngine, *items: tuple[str, str]) -> list:
    """An administrator saves ``items`` through the service the API uses, which records who."""
    admin = await _add_admin(engine)
    async with AsyncSession(engine) as session:
        return await settings_service.update_global_settings(list(items), admin.id, session)


async def _row(engine: AsyncEngine, key: str) -> GlobalSetting | None:
    async with AsyncSession(engine) as session:
        return (await session.execute(select(GlobalSetting).where(GlobalSetting.key == key))).scalar_one_or_none()


async def _effective(engine: AsyncEngine, key: str):
    async with AsyncSession(engine) as session:
        return await get_setting_value(session, key, "?")


async def _listed(engine: AsyncEngine) -> dict[str, str]:
    async with AsyncSession(engine) as session:
        return {item.key: item.value for item in await settings_service.get_all_global_settings(session)}


# =============================================================================
# (a) the settings, their defaults and their constraints
# =============================================================================


@pytest.mark.parametrize("key", [MB_KEY, DAYS_KEY])
def test_both_settings_are_integers_that_default_to_zero(key):
    """(a) 0 is off, on a self-hosted instance."""
    entry = GLOBAL_SETTINGS_DEFAULTS.get(key)
    assert entry is not None, f"red until FB-24: GLOBAL_SETTINGS_DEFAULTS has no {key}"
    assert (entry["value"], entry["type"]) == ("0", "int"), f"{key} is an int whose default is 0: {entry}"
    assert entry["description"], "and it says what it is"


@pytest.mark.parametrize(("key", "largest"), LIMITS)
def test_a_save_accepts_zero_to_the_limit_and_nothing_else(key, largest):
    """(a) ``0..1048576`` MB and ``0..3650`` days, whole numbers, spaces dropped."""
    for text, stored in (("0", "0"), ("1", "1"), (" 250 ", "250"), (str(largest), str(largest))):
        assert validate_global_setting_value(key, text, "int") == stored, f"{text!r} is accepted as {stored}"
    for text in ("-1", str(largest + 1), "abc", "1.5", "", "1e3", "0x10"):
        with pytest.raises(ValueError):
            validate_global_setting_value(key, text, "int")


@pytest.mark.asyncio
@pytest.mark.parametrize("key", [MB_KEY, DAYS_KEY])
async def test_the_startup_seeds_both_rows_with_zero_and_no_author(engine, key):
    row = await _row(engine, key)
    assert row is not None, f"red until FB-24: the startup seeds no {key} row"
    assert (row.value, row.value_type, row.updated_by_user_id) == ("0", "int", None), f"the seeded row: {row!r}"


# =============================================================================
# (b) the value in force
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("key", [MB_KEY, DAYS_KEY])
async def test_a_selfhosted_instance_has_the_clean_up_off_as_an_integer(engine, key):
    """(b) Seeded row, or no row at all: 0, an ``int``."""
    value = await _effective(engine, key)
    assert value == 0 and type(value) is int, f"selfhosted: 0 as an int, got {value!r}"
    async with AsyncSession(engine) as session:
        await session.execute(delete(GlobalSetting).where(GlobalSetting.key == key))
        await session.commit()
    value = await _effective(engine, key)
    assert value == 0 and type(value) is int, f"no row: still the default, got {value!r}"


@pytest.mark.asyncio
@pytest.mark.parametrize(("key", "expected"), list(MANAGED.items()))
async def test_a_managed_instance_has_250_mb_and_30_days_until_an_administrator_chooses(engine, monkeypatch, key, expected):
    """(b) The seeded row (nobody wrote it) and no row: the profile's value, an ``int``; the lists say it as text."""
    print_section(f"managed: {key}")
    managed(monkeypatch)
    value = await _effective(engine, key)
    assert value == expected and type(value) is int, f"managed, seeded row: {expected} as an int, got {value!r}"
    assert str((await _listed(engine))[key]) == str(expected), "and the list of settings (GET /settings/global) says the same"
    async with AsyncSession(engine) as session:
        single = await settings_service.get_global_setting(key, session)
    assert single is not None and str(single.value) == str(expected), f"and so does the setting read alone: {single}"
    async with AsyncSession(engine) as session:
        await session.execute(delete(GlobalSetting).where(GlobalSetting.key == key))
        await session.commit()
    value = await _effective(engine, key)
    assert value == expected and type(value) is int, f"no row either: {value!r}"
    print_success(f"{key}: {value}")


@pytest.mark.parametrize(("key", "expected"), list(MANAGED.items()))
def test_effective_stored_value_pins_a_managed_row_nobody_wrote(monkeypatch, key, expected):
    """(b) Missing, or written by no administrator: the profile's value; written by one: nothing stands behind it."""
    managed(monkeypatch)
    seeded = GlobalSetting(key=key, value="0", value_type="int", description="", updated_by_user_id=None)
    written = GlobalSetting(key=key, value="7", value_type="int", description="", updated_by_user_id=1)
    assert str(effective_stored_value(key, None)) == str(expected), "no row"
    assert str(effective_stored_value(key, seeded)) == str(expected), "a row nobody wrote"
    assert effective_stored_value(key, written) is None, "a row an administrator wrote"


@pytest.mark.asyncio
@pytest.mark.parametrize("profile", ["selfhosted", "managed"])
async def test_the_row_an_administrator_wrote_wins_in_either_profile(engine, monkeypatch, profile):
    """(b) 100 MB and 0 days (the age switched off, which managed allows): from the first save the row says it, ints."""
    if profile == "managed":
        managed(monkeypatch)
    await _save(engine, (MB_KEY, "100"), (DAYS_KEY, "0"))
    mb, days = await _effective(engine, MB_KEY), await _effective(engine, DAYS_KEY)
    assert (mb, days) == (100, 0) and type(mb) is int and type(days) is int, f"{profile}: the administrator's values, as ints: {mb!r}, {days!r}"
    assert {key: str(value) for key, value in (await _listed(engine)).items() if key in MANAGED} == {MB_KEY: "100", DAYS_KEY: "0"}, "and the list says them"


@pytest.mark.asyncio
async def test_a_managed_administrator_who_saves_the_profile_value_again_keeps_it_by_the_row(engine, monkeypatch):
    """(b) The row wins even when it says what the profile would: later the profile can change, the row stays."""
    managed(monkeypatch)
    await _save(engine, (MB_KEY, "250"))
    row = await _row(engine, MB_KEY)
    assert row is not None and (row.value, row.updated_by_user_id is not None) == ("250", True)
    monkeypatch.setenv(PROFILE_VARIABLE, "selfhosted")
    assert await _effective(engine, MB_KEY) == 250, "the administrator's 250 stays even where the profile would say 0"


@pytest.mark.asyncio
async def test_the_managed_profile_pins_no_other_setting(engine, monkeypatch):
    managed(monkeypatch)
    assert await _effective(engine, "session_ttl_hours") == 24 and await _effective(engine, "max_file_upload_mb") == 10


# =============================================================================
# (c) what a managed instance refuses
# =============================================================================


@pytest.mark.asyncio
async def test_a_managed_instance_refuses_to_switch_the_space_off_and_writes_nothing(engine, monkeypatch):
    """(c) ``backup_cleanup_max_mb`` as 0: ``GlobalSettingValueError`` naming the key; the row, and the other setting of the
    same save, as they were."""
    print_section("managed refuses max_mb = 0")
    managed(monkeypatch)
    admin = await _add_admin(engine)
    async with AsyncSession(engine) as session:
        with pytest.raises(GlobalSettingValueError) as refused:
            await settings_service.update_global_settings([(MB_KEY, "0"), (DAYS_KEY, "7")], admin.id, session)
    assert MB_KEY in [key for key, _reason in refused.value.errors], f"the key is among the errors: {refused.value.errors}"
    for key in (MB_KEY, DAYS_KEY):
        row = await _row(engine, key)
        assert row is not None and (row.value, row.updated_by_user_id) == ("0", None), f"{key} was not written: {row!r}"
    assert (await _effective(engine, MB_KEY), await _effective(engine, DAYS_KEY)) == (250, 30), "and the profile's values are still in force"
    print_success("refused, nothing written")


@pytest.mark.asyncio
async def test_a_managed_instance_lets_the_age_be_switched_off(engine, monkeypatch):
    managed(monkeypatch)
    written = await _save(engine, (DAYS_KEY, "0"))
    assert [(item.key, str(item.value)) for item in written] == [(DAYS_KEY, "0")], f"max_days 0 is accepted: {written}"
    assert await _effective(engine, DAYS_KEY) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("key", [MB_KEY, DAYS_KEY])
async def test_a_selfhosted_instance_accepts_zero_on_both(engine, key):
    await _save(engine, (key, "5"))
    await _save(engine, (key, "0"))
    row = await _row(engine, key)
    assert row is not None and row.value == "0", f"selfhosted accepts 0 for {key}: {row!r}"


@pytest.mark.asyncio
@pytest.mark.parametrize(("key", "largest"), LIMITS)
async def test_a_save_over_the_limit_is_refused_on_either_profile(engine, key, largest):
    admin = await _add_admin(engine)
    async with AsyncSession(engine) as session:
        with pytest.raises(GlobalSettingValueError) as refused:
            await settings_service.update_global_settings([(key, str(largest + 1))], admin.id, session)
    assert [name for name, _reason in refused.value.errors] == [key]


# =============================================================================
# (d) read_policy
# =============================================================================


def retention_module():
    try:
        return importlib.import_module(RETENTION)
    except ModuleNotFoundError as exc:
        if exc.name != RETENTION:
            raise
        pytest.fail(f"[new] {RETENTION} does not exist yet: lot FB-24 brings it (§3)", pytrace=False)


def use_sync_engine(monkeypatch: pytest.MonkeyPatch, make) -> None:
    """``get_sync_engine`` answers ``make()`` wherever the policy may reach it: the session module, the package that
    re-exports it and the clean-up's own module, were it to bind the name."""
    module = retention_module()
    for name in ("backend.app.db.session", "backend.app.db"):
        monkeypatch.setattr(importlib.import_module(name), "get_sync_engine", make)
    monkeypatch.setattr(module, "get_sync_engine", make, raising=False)


async def policy_read(monkeypatch: pytest.MonkeyPatch, path: Path) -> tuple[int, int]:
    """``read_policy()`` on a synchronous engine on ``path`` (it runs in a thread, as in production), as a pair; it
    must give a ``CleanupPolicy`` of ints."""
    engine = create_engine(f"sqlite:///{path}", poolclass=NullPool)
    try:
        use_sync_engine(monkeypatch, lambda: engine)
        policy = await asyncio.to_thread(retention_module().read_policy)
    finally:
        engine.dispose()
    assert type(policy).__name__ == "CleanupPolicy", f"a CleanupPolicy: {policy!r}"
    assert type(policy.max_mb) is int and type(policy.max_days) is int, f"of ints: {policy!r}"
    return policy.max_mb, policy.max_days


@pytest.mark.asyncio
async def test_the_policy_of_a_selfhosted_instance_is_off(database, monkeypatch):
    assert await policy_read(monkeypatch, database[1]) == (0, 0)


@pytest.mark.asyncio
async def test_the_policy_of_a_managed_instance_is_250_mb_and_30_days(database, monkeypatch):
    managed(monkeypatch)
    assert await policy_read(monkeypatch, database[1]) == (250, 30)


@pytest.mark.asyncio
@pytest.mark.parametrize("profile", ["selfhosted", "managed"])
async def test_the_policy_is_what_the_administrator_saved(database, monkeypatch, profile):
    engine, path = database
    if profile == "managed":
        managed(monkeypatch)
    await _save(engine, (MB_KEY, "100"), (DAYS_KEY, "0" if profile == "managed" else "7"))
    assert await policy_read(monkeypatch, path) == (100, 0 if profile == "managed" else 7)


@pytest.mark.asyncio
@pytest.mark.parametrize("junk", ["abc", "-5", "", "1.5"])
async def test_a_value_that_is_not_a_whole_number_of_zero_or_more_switches_the_clean_up_off(database, monkeypatch, junk):
    """(d) Written by an administrator and unusable: off, not an exception, and not the profile's value either."""
    engine, path = database
    admin = await _add_admin(engine)
    async with AsyncSession(engine) as session:
        await session.execute(update(GlobalSetting).where(GlobalSetting.key.in_([MB_KEY, DAYS_KEY])).values(value=junk, updated_by_user_id=admin.id))  # type: ignore[attr-defined]
        await session.commit()
    managed(monkeypatch)
    assert await policy_read(monkeypatch, path) == (0, 0)


@pytest.mark.asyncio
async def test_a_database_without_the_table_or_an_engine_that_fails_switches_the_clean_up_off(tmp_path, monkeypatch):
    """(d) Never an exception: an empty file, then an engine that raises."""
    empty = tmp_path / "empty.db"
    empty.write_bytes(b"")
    assert await policy_read(monkeypatch, empty) == (0, 0), "a database without the table"

    def failing():
        raise RuntimeError("no database")

    use_sync_engine(monkeypatch, failing)
    policy = await asyncio.to_thread(retention_module().read_policy)
    assert (policy.max_mb, policy.max_days) == (0, 0), "an engine that cannot be made"

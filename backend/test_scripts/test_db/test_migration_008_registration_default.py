"""Migration ``008_registration_invite_default``: an install with accounts keeps the registration it had (plan phase01Accounts, lot A6d, contract C9; decision 36 of the developer).

From release 1.3 a new instance lets people in by invitation only: the default of ``registration_mode`` in
``GLOBAL_SETTINGS_DEFAULTS`` becomes ``invite``, and the application's startup seeding writes every missing setting with
its default. An install that holds accounts but no ``registration_mode`` row has run with the old default, ``open`` —
1.1 and 1.2 read a missing ``enable_registration`` as true, and 006 converts only a row that is there —, and must not
close in silence at its first start on 1.3: 008 writes that row before the seeding can. Data only: no table, no column.
The contract pinned here:

1. The revision: id ``008_registration_invite_default`` (31 characters; ``alembic_version.version_num`` holds 32), in
   ``008_registration_invite_default.py``, on top of ``007_plugin_settings``; the chain keeps exactly one head, which is
   not named.
2. The upgrade writes ``open`` where an install has accounts and no row: no ``registration_mode`` in ``global_settings``
   and at least one row in ``users``, active or not, give one new row — value ``open``, ``value_type`` ``str``, the
   description «Who may create an account: open, invite or disabled», ``updated_at`` the UTC time of the upgrade, a
   timestamp the application reads back like every other, ``updated_by_user_id`` NULL. Type and description are the
   registry's, ``GLOBAL_SETTINGS_DEFAULTS["registration_mode"]``, from which a new install seeds its row; the value is
   not: the registry's default is ``invite`` from this lot on, the install had ``open``. No other setting changes.
3. A row that is there is never touched, whatever its value — ``open``, ``invite``, ``disabled``, an odd one — and
   whatever its metadata: with accounts present, the row alone keeps the upgrade from writing.
4. Without accounts nothing is written, up or down: ``users`` never filled, or emptied. A new install gets the new
   default from the startup seeding, not from the migration.
5. Idempotent: upgrade, downgrade and upgrade again give the settings of the first upgrade, ``updated_at`` included —
   the second run of the body finds its own row and leaves it.
6. The downgrade does nothing: at 007 every setting is as it was at 008 — the ``open`` row 008 wrote, which is what the
   earlier default meant (006's downgrade turns it into ``enable_registration = 'true'``), and a value an administrator
   set after the upgrade.
7. No other row of any table changes, up or down, on a populated install: the real 1.1 install of
   ``test_post_migration``, taken to 007 by the real migrations. As it is — ``registration_mode = 'disabled'``, which
   006 converted from ``enable_registration = 'false'`` — 008 changes no row at all; with that row deleted, the upgrade
   adds the ``open`` row and nothing else. No foreign-key violation.
8. End to end, a 1.1 install upgraded to head keeps the registration it had. Without its ``enable_registration`` row,
   which 1.1 read as its default, true, it is ``open``, written by the upgrade; with ``'false'`` it is ``disabled`` and
   with ``'true'`` ``open``, both with the 1.1 row's author and time.

Safety and fidelity: the harness of ``test_migration_005_accounts`` and the settings helpers of
``test_migration_006_registration``, reused as they are. Every database is a file under ``tmp_path``; Alembic runs in
this process on that file alone — a connect listener refuses any other — with ``PRAGMA foreign_keys`` asserted 1 at
every step, as production migrates. Rows are written with plain SQL, the way a real install holds them, never through
the models.

Red until the migration exists: every test migrates to ``008_registration_invite_default`` (Alembic cannot locate it),
or to head and then checks that the database includes it. The databases at 007 need ``007_plugin_settings`` too —
workstream X's revision, in ``dev_release2`` and not yet in this branch —: until it is merged their fixtures fail.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

import pytest
from sqlalchemy import DateTime
from sqlalchemy.dialects import sqlite

from backend.app.schemas.settings import GLOBAL_SETTINGS_DEFAULTS
from backend.test_scripts.test_db.test_migration_005_accounts import (
    BOOKKEEPING,
    Rows,
    _connect,
    _copy,
    _foreign_keys_on,
    _insert_user,
    _lineage,
    _migrate,
    _revision,
    _rows,
    _scripts,
    _violations,
)
from backend.test_scripts.test_db.test_migration_006_registration import (
    NEW_DESCRIPTION,
    NEW_KEY,
    NEW_TYPE,
    OLD_KEY,
    V110_ROW_AUTHOR,
    V110_ROW_STAMP,
    Setting,
    _differences,
    _others,
    _settings,
    _without_registration_rows,
    _write_neighbours,
    _write_setting,
)
from backend.test_scripts.test_db.test_post_migration import _install_v110
from backend.test_scripts.test_utils import print_section, print_success

REV_007 = "007_plugin_settings"
REV_008 = "008_registration_invite_default"
#: What an install with accounts and no row ran with until 1.3, and what 008 writes for it.
OPEN = "open"

# A row written before 008 ran, with metadata 008 never writes: the 1.1 spelling of the type, a description of its own,
# an author, an earlier time.
EARLIER_TYPE = "string"
EARLIER_DESCRIPTION = "Registration, as an administrator left it"
STAMP = "2026-10-14 08:15:30.123456"
# When an administrator changed the row, after the upgrade.
ADMIN_STAMP = "2026-10-16 09:00:00.000000"

EXISTING_VALUES = [pytest.param(value, id=f"{value!r}-kept") for value in ("open", "invite", "disabled", "OPEN", "", "maybe")]
# users.is_active of the only account: an account counts whether it may log in or not.
ACCOUNTS = [pytest.param(1, id="an-active-account"), pytest.param(0, id="only-an-inactive-account")]
# How users came to be empty: never filled; never filled, other settings written; filled, then emptied.
NO_ACCOUNTS = [pytest.param("never", id="never-an-account"), pytest.param("settings", id="never-an-account-other-settings"), pytest.param("deleted", id="every-account-deleted")]
# What an administrator set after the upgrade; None: the row the upgrade wrote, as it wrote it.
AFTERWARDS = [pytest.param(None, id="the-row-the-upgrade-wrote"), pytest.param("invite", id="invite-set-afterwards"), pytest.param("disabled", id="disabled-set-afterwards")]
# A 1.1 install's enable_registration, and the registration_mode it holds at head.
KEPT_AT_HEAD = [pytest.param("false", "disabled", id="false->disabled"), pytest.param("true", "open", id="true->open")]


# =============================================================================
# HELPERS
# =============================================================================


def _assert_includes_008(db: Path) -> None:
    """Barrier: ``db`` is at 008 or above; otherwise nothing that follows is about 008."""
    revision = _revision(db)
    assert REV_008 in _lineage(revision), f"barrier: {db.name} is at {revision}, which does not include {REV_008}: the assertions that follow would say nothing about the migration"


def _accounts(db: Path) -> int:
    """How many rows ``users`` holds, active or not: the condition 008 reads."""
    with _connect(db) as conn:
        return conn.execute("SELECT count(*) FROM users").fetchone()[0]


def _without_bookkeeping(rows: Rows) -> Rows:
    """Every table but Alembic's own, every row of it, ``global_settings`` included whole."""
    return {table: content for table, content in rows.items() if table not in BOOKKEEPING}


def _utc_now() -> datetime:
    """Now, as the database holds a time: UTC, without an offset."""
    return datetime.now(UTC).replace(tzinfo=None)


def _read_back(stamp: Any) -> datetime:
    """``stamp`` as the application reads ``global_settings.updated_at``: through SQLAlchemy's ``DateTime`` on SQLite."""
    dialect = sqlite.dialect()
    read = DateTime().dialect_impl(dialect).result_processor(dialect, None)
    assert read is not None, "setup: SQLAlchemy reads a SQLite DateTime through a result processor"
    return read(stamp)


def _assert_written_by_the_upgrade(setting: Optional[Setting], started: datetime, finished: datetime) -> None:
    """``setting`` is the row 008 writes: ``open``, ``str``, the frozen description, nobody's, at the UTC time of the upgrade.

    ``updated_at`` is read back the way the application reads it, and must be what every other timestamp of the database
    is: text without an offset, in UTC — SQLAlchemy storing ``utcnow()``, or SQLite's ``CURRENT_TIMESTAMP``. The window
    opens at the second the upgrade started: ``CURRENT_TIMESTAMP`` has no fraction.
    """
    assert setting is not None, f"the install has accounts and no {NEW_KEY}: the upgrade must write it, {OPEN!r}"
    value, value_type, description, updated_at, updated_by = setting
    assert (value, value_type, description, updated_by) == (OPEN, NEW_TYPE, NEW_DESCRIPTION, None), f"{NEW_KEY} must be {OPEN!r}, value_type {NEW_TYPE!r}, described {NEW_DESCRIPTION!r}, signed by nobody; got {setting}"
    assert isinstance(updated_at, str) and updated_at, f"updated_at must be a timestamp, is {updated_at!r}"
    try:
        written = _read_back(updated_at)
    except (TypeError, ValueError) as error:
        pytest.fail(f"updated_at {updated_at!r} is not a timestamp the application can read back: {error}")
    assert written.tzinfo is None, f"updated_at {updated_at!r} carries an offset: the application would read an aware datetime where every other timestamp of the database is naive UTC"
    assert started.replace(microsecond=0) <= written <= finished, f"updated_at {updated_at!r} must be the UTC time of the upgrade, between {started:%Y-%m-%d %H:%M:%S} and {finished:%Y-%m-%d %H:%M:%S}"


def _leave_no_account(conn: sqlite3.Connection, history: str) -> None:
    """``users`` empty, one of three ways: never filled; never filled, other settings written; filled, then emptied."""
    if history == "settings":
        _write_setting(conn, "session_ttl_hours", ("48", "int", "Session cookie TTL in hours", STAMP, None))
        _write_setting(conn, "default_language", ("it", "str", None, STAMP, None))
    elif history == "deleted":
        account = _insert_user(conn, "gone")
        _write_neighbours(conn, account)
        assert conn.execute("DELETE FROM users WHERE id = ?", (account,)).rowcount == 1, "setup: the only account is deleted"


def _without_its_row(install: Path, target: Path) -> Path:
    """A copy of the install at 007 whose registration row was deleted with plain SQL: accounts, and no row."""
    db = _copy(install, target)
    with _foreign_keys_on(db) as conn:
        deleted = conn.execute("DELETE FROM global_settings WHERE key = ?", (NEW_KEY,)).rowcount
        conn.commit()
    assert deleted == 1 and _accounts(db) > 0, "setup: the install has accounts and, now, no registration row"
    return db


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(scope="module")
def at_007(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A new database at 007: no account, no setting. Read-only for the tests: ``_copy`` it to write."""
    db = tmp_path_factory.mktemp("at-007") / "app.db"
    _migrate(db, "upgrade", REV_007)
    assert _revision(db) == REV_007, "setup: the database is at 007"
    assert _settings(db) == {} and _accounts(db) == 0, "setup: the migrations create no account and seed no setting, the application does"
    return db


@pytest.fixture(scope="module")
def install_1_1(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The real 1.1 install of test_post_migration — every table, gaps, a deleted user —, at its 1.1 revision. Read-only: ``_copy`` it to write."""
    db = tmp_path_factory.mktemp("install-1.1") / "sqlite" / "app.db"
    _install_v110(db)
    settings = _settings(db)
    assert settings.get(OLD_KEY, ("",))[0] == "false" and NEW_KEY not in settings, f"setup: the 1.1 install holds enable_registration = 'false' and no registration_mode: {settings}"
    assert _accounts(db) > 0, "setup: the 1.1 install has accounts"
    return db


@pytest.fixture(scope="module")
def install_at_007(install_1_1: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The 1.1 install taken to 007 by the real migrations: accounts, and the ``disabled`` row 006 converted. Read-only: ``_copy`` it to write."""
    db = _copy(install_1_1, tmp_path_factory.mktemp("install-007") / "sqlite" / "app.db")
    _migrate(db, "upgrade", REV_007)
    assert _revision(db) == REV_007, "setup: the install is at 007"
    assert _settings(db).get(NEW_KEY) == ("disabled", NEW_TYPE, NEW_DESCRIPTION, V110_ROW_STAMP, V110_ROW_AUTHOR), f"setup: 006 converted the 1.1 row into registration_mode = 'disabled' with its metadata: {_settings(db)}"
    assert _accounts(db) > 0, "setup: the install has accounts"
    return db


# =============================================================================
# 1. THE REVISION
# =============================================================================


def test_revision_008_sits_on_007_and_the_chain_keeps_one_head() -> None:
    """Contract 1: ``008_registration_invite_default`` exists in ``008_registration_invite_default.py``, fits ``version_num``, revises 007; one head, not named."""
    print_section("Contract 1: revision 008_registration_invite_default")
    scripts = _scripts()
    revisions = {script.revision: script for script in scripts.walk_revisions()}

    assert REV_008 in revisions, f"revision {REV_008} not found; the chain has {sorted(revisions)}"
    script = revisions[REV_008]
    assert len(script.revision) <= 32, f"{script.revision!r} is {len(script.revision)} characters: alembic_version.version_num is VARCHAR(32)"
    assert script.down_revision == REV_007, f"{REV_008} must revise {REV_007}, revises {script.down_revision!r}"
    assert Path(script.path).name == f"{REV_008}.py", f"the revision id is the file name without .py, found in {Path(script.path).name}"
    heads = scripts.get_heads()
    assert len(heads) == 1, f"the chain must not fork: {len(heads)} heads {heads}"
    print_success(f"{REV_008} revises {REV_007}; one head ({heads[0]})")


# =============================================================================
# 2. ACCOUNTS AND NO ROW: THE UPGRADE WRITES OPEN
# =============================================================================


@pytest.mark.parametrize("is_active", ACCOUNTS)
def test_an_install_with_accounts_and_no_row_gets_open(at_007: Path, tmp_path: Path, is_active: int) -> None:
    """Contract 2: one account, active or not, and no ``registration_mode``: the upgrade writes ``open``, ``str``, the frozen description, nobody's, at the UTC time of the upgrade; it writes nothing else, and the other settings stay as they were."""
    print_section(f"Contract 2: an account (is_active={is_active}) and no row → open")
    db = _copy(at_007, tmp_path / "app.db")
    with _foreign_keys_on(db) as conn:
        account = _insert_user(conn, "account")
        assert conn.execute("UPDATE users SET is_active = ? WHERE id = ?", (is_active, account)).rowcount == 1, "setup: the account is as the case says"
        neighbours = _write_neighbours(conn, account)
        conn.commit()
    assert _accounts(db) == 1 and NEW_KEY not in _settings(db), "setup: one account, no registration row"

    started = _utc_now()
    _migrate(db, "upgrade", REV_008)
    finished = _utc_now()
    _assert_includes_008(db)
    settings = _settings(db)

    _assert_written_by_the_upgrade(settings.get(NEW_KEY), started, finished)
    assert set(settings) == set(neighbours) | {NEW_KEY}, f"the upgrade must write {NEW_KEY} and no other setting: {sorted(settings)}"
    assert _others(settings) == neighbours, f"the upgrade touched other settings: {_others(settings)}"
    print_success("open, str, the frozen description, nobody's, written now; the neighbours untouched")


def test_the_written_row_is_the_row_a_new_install_seeds_but_for_its_value(at_007: Path, tmp_path: Path) -> None:
    """Contract 2: the ``value_type`` and the description 008 writes are the registry's, ``GLOBAL_SETTINGS_DEFAULTS["registration_mode"]``, from which a new install seeds its row; the value is ``open``, the install's, whatever default the registry gives a new install (``invite`` from this lot on).

    GUARD: it compares the migration's frozen text with the registry, whatever both say, so that they cannot drift
    apart; ``NEW_TYPE`` and ``NEW_DESCRIPTION`` pin what they say.
    """
    print_section("Contract 2: the written row is a new install's row, but for its value")
    db = _copy(at_007, tmp_path / "app.db")
    with _foreign_keys_on(db) as conn:
        _insert_user(conn, "account")
        conn.commit()

    _migrate(db, "upgrade", REV_008)
    _assert_includes_008(db)
    written = _settings(db).get(NEW_KEY)
    seeded = GLOBAL_SETTINGS_DEFAULTS[NEW_KEY]

    assert written is not None, f"the install has an account and no {NEW_KEY}: the upgrade must write it"
    assert written[1:3] == (seeded["type"], seeded["description"]), f"the migration writes {written}, a new install seeds {seeded}: an upgraded install and a new one must hold the same row, but for its value"
    assert written[0] == OPEN, f"the value is the one the install ran with, {OPEN!r}, not the registry's default {seeded['value']!r}; got {written[0]!r}"
    print_success(f"value_type {seeded['type']!r} and the description as a new install seeds them; the value {OPEN!r}")


# =============================================================================
# 3. A ROW THAT IS THERE IS NEVER TOUCHED
# =============================================================================


@pytest.mark.parametrize("value", EXISTING_VALUES)
def test_a_row_that_is_there_is_left_as_it_was(at_007: Path, tmp_path: Path, value: str) -> None:
    """Contract 3: an account, and a ``registration_mode`` written before 008 with metadata 008 never writes (another type spelling, its own description, an author, an earlier time): every setting is as it was, whatever the value says — an odd one included.

    The account is there on purpose: without it contract 4 alone would explain why nothing is written.
    """
    print_section(f"Contract 3: registration_mode={value!r} is kept")
    db = _copy(at_007, tmp_path / "app.db")
    with _foreign_keys_on(db) as conn:
        author = _insert_user(conn, "author")
        _write_setting(conn, NEW_KEY, (value, EARLIER_TYPE, EARLIER_DESCRIPTION, STAMP, author))
        _write_neighbours(conn, author)
        conn.commit()
    before = _settings(db)
    assert _accounts(db) > 0, "setup: the install has an account, so the row alone must keep the upgrade from writing"

    _migrate(db, "upgrade", REV_008)
    _assert_includes_008(db)
    after = _settings(db)

    assert after.get(NEW_KEY) == before[NEW_KEY], f"{NEW_KEY} was there: the upgrade must leave it as it was, metadata included, {before[NEW_KEY]}; got {after.get(NEW_KEY)}"
    assert after == before, f"the upgrade changed settings it had no reason to touch: {before} then {after}"
    print_success(f"{value!r} kept, with its type, description, author and time")


# =============================================================================
# 4. WITHOUT ACCOUNTS NOTHING IS WRITTEN
# =============================================================================


@pytest.mark.parametrize("history", NO_ACCOUNTS)
def test_without_accounts_nothing_is_written_up_or_down(at_007: Path, tmp_path: Path, history: str) -> None:
    """Contract 4: ``users`` empty — never filled, never filled with other settings written, or emptied (the settings an account signed then signed by nobody) — and no ``registration_mode``: the upgrade and the downgrade work and change no setting; the default is the startup seeding's job."""
    print_section(f"Contract 4: no account ({history}), nothing written")
    db = _copy(at_007, tmp_path / "app.db")
    with _foreign_keys_on(db) as conn:
        _leave_no_account(conn, history)
        conn.commit()
    before = _settings(db)
    assert _accounts(db) == 0 and NEW_KEY not in before, f"setup: no account and no registration row: {before}"

    _migrate(db, "upgrade", REV_008)
    _assert_includes_008(db)
    after_upgrade = _settings(db)
    _migrate(db, "downgrade", REV_007)
    after_downgrade = _settings(db)

    assert after_upgrade == before, f"without accounts the upgrade must write nothing — a new install gets the default from the startup seeding: {before} then {after_upgrade}"
    assert after_downgrade == before, f"the downgrade must change no setting: {before} then {after_downgrade}"
    assert _revision(db) == REV_007
    print_success("up and down, nothing written, nothing lost")


# =============================================================================
# 5. IDEMPOTENT
# =============================================================================


def test_up_down_and_up_again_gives_the_settings_of_the_first_upgrade(at_007: Path, tmp_path: Path) -> None:
    """Contract 5: an account and no row; upgrade, downgrade, upgrade again: every setting as after the first upgrade, ``updated_at`` of the ``open`` row included.

    A second run that rewrote the row within the same second would look the same here: contract 3 (an ``open`` row with
    other metadata kept as it is) is what rules that out.
    """
    print_section("Contract 5: up, down and up again")
    db = _copy(at_007, tmp_path / "app.db")
    with _foreign_keys_on(db) as conn:
        _write_neighbours(conn, _insert_user(conn, "author"))
        conn.commit()

    _migrate(db, "upgrade", REV_008)
    _assert_includes_008(db)
    first = _settings(db)
    _migrate(db, "downgrade", REV_007)
    between = _settings(db)
    _migrate(db, "upgrade", REV_008)
    again = _settings(db)

    assert first.get(NEW_KEY, ("",))[0] == OPEN, f"barrier: the first upgrade did not write the open row, so the round trip would be about nothing: {first}"
    assert between == first, f"the downgrade must leave every setting as it was at 008: {first} then {between}"
    assert again == first, f"upgrade, downgrade and upgrade again must give the settings of the first upgrade: {first} then {again}"
    print_success("up → down → up: the same settings, the same row")


def test_the_round_trip_on_a_populated_install_gives_the_settings_of_the_first_upgrade(install_at_007: Path, tmp_path: Path) -> None:
    """Contract 5 on real data: the 1.1 install at 007 without its registration row; upgrade, downgrade, upgrade again: every setting as after the first upgrade."""
    print_section("Contract 5: the round trip on a populated install")
    db = _without_its_row(install_at_007, tmp_path / "app.db")

    _migrate(db, "upgrade", REV_008)
    _assert_includes_008(db)
    first = _settings(db)
    _migrate(db, "downgrade", REV_007)
    between = _settings(db)
    _migrate(db, "upgrade", REV_008)
    again = _settings(db)

    assert first.get(NEW_KEY, ("",))[0] == OPEN, f"barrier: the first upgrade did not write the open row, so the round trip would be about nothing: {first}"
    assert between == first, f"the downgrade must leave every setting as it was at 008: {first} then {between}"
    assert again == first, f"upgrade, downgrade and upgrade again must give the settings of the first upgrade: {first} then {again}"
    print_success("up → down → up on the 1.1 install: the same settings")


# =============================================================================
# 6. THE DOWNGRADE DOES NOTHING
# =============================================================================


@pytest.mark.parametrize("set_afterwards", AFTERWARDS)
def test_the_downgrade_leaves_every_setting_as_it_was_at_008(at_007: Path, tmp_path: Path, set_afterwards: Optional[str]) -> None:
    """Contract 6: at 008 the ``open`` row the upgrade wrote — as it wrote it, or changed by an administrator to ``invite`` or ``disabled`` —; after ``downgrade 007`` every setting is as it was at 008: 008's downgrade neither removes the row it wrote nor converts anything."""
    print_section(f"Contract 6: the downgrade keeps {set_afterwards or 'the row the upgrade wrote'}")
    db = _copy(at_007, tmp_path / "app.db")
    with _foreign_keys_on(db) as conn:
        author = _insert_user(conn, "author")
        _write_neighbours(conn, author)
        conn.commit()
    _migrate(db, "upgrade", REV_008)
    _assert_includes_008(db)
    assert NEW_KEY in _settings(db), f"barrier: the upgrade wrote no {NEW_KEY}, so the downgrade would have nothing to keep"
    if set_afterwards is not None:
        with _foreign_keys_on(db) as conn:
            changed = conn.execute("UPDATE global_settings SET value = ?, updated_at = ?, updated_by_user_id = ? WHERE key = ?", (set_afterwards, ADMIN_STAMP, author, NEW_KEY)).rowcount
            conn.commit()
        assert changed == 1, "setup: an administrator changes the row after the upgrade"
    at_008 = _settings(db)

    _migrate(db, "downgrade", REV_007)

    assert _revision(db) == REV_007
    assert _settings(db) == at_008, f"the downgrade must do nothing: every setting as at 008, {at_008}; got {_settings(db)}"
    print_success(f"at 007 again, {NEW_KEY} = {at_008[NEW_KEY][0]!r} as it was at 008")


# =============================================================================
# 7. NO OTHER ROW IS TOUCHED, ON A POPULATED INSTALL
# =============================================================================


def test_an_install_holding_its_row_changes_no_row_up_or_down(install_at_007: Path, tmp_path: Path) -> None:
    """Contract 7, and contract 3 on real data: the 1.1 install at 007 as it is — accounts, and the ``registration_mode = 'disabled'`` 006 converted from ``enable_registration = 'false'`` —: the upgrade and then the downgrade change no row of any table, that row included, metadata and all. No foreign-key violation at either end.

    Doing nothing is all 008 may do here, so the barrier is that it ran; the next test proves, on the same install, that
    it writes when the row is missing.
    """
    print_section("Contract 7: an install holding its row, up and down")
    db = _copy(install_at_007, tmp_path / "app.db")
    rows_at_007 = _rows(db)

    _migrate(db, "upgrade", REV_008)
    _assert_includes_008(db)
    rows_at_008, settings_at_008, violations_at_008 = _rows(db), _settings(db), _violations(db)
    _migrate(db, "downgrade", REV_007)
    rows_down = _rows(db)

    assert settings_at_008.get(NEW_KEY) == ("disabled", NEW_TYPE, NEW_DESCRIPTION, V110_ROW_STAMP, V110_ROW_AUTHOR), f"the 1.1 install had registration off: it must stay disabled, with its author and time; got {settings_at_008.get(NEW_KEY)}"
    up = _differences(_without_bookkeeping(rows_at_007), _without_bookkeeping(rows_at_008))
    assert not up, f"the upgrade changed rows of an install that holds its registration row: {up}"
    down = _differences(_without_bookkeeping(rows_at_008), _without_bookkeeping(rows_down))
    assert not down, f"the downgrade changed rows: {down}"
    assert _revision(db) == REV_007
    assert violations_at_008 == [] and _violations(db) == []
    print_success(f"{len(_without_bookkeeping(rows_at_007))} tables, every row as it was, both ways; still disabled")


def test_an_install_without_its_row_gains_only_the_open_row(install_at_007: Path, tmp_path: Path) -> None:
    """Contract 7, and contract 2 on real data: the 1.1 install at 007 with its registration row deleted with plain SQL: the upgrade adds the ``open`` row and changes nothing else — no other setting, no other table, no ``enable_registration`` —; the downgrade changes no row at all. No foreign-key violation at either end."""
    print_section("Contract 7: an install without its row, up and down")
    db = _without_its_row(install_at_007, tmp_path / "app.db")
    rows_at_007 = _rows(db)

    started = _utc_now()
    _migrate(db, "upgrade", REV_008)
    finished = _utc_now()
    _assert_includes_008(db)
    rows_at_008, settings_at_008, violations_at_008 = _rows(db), _settings(db), _violations(db)
    _migrate(db, "downgrade", REV_007)
    rows_down = _rows(db)

    _assert_written_by_the_upgrade(settings_at_008.get(NEW_KEY), started, finished)
    assert OLD_KEY not in settings_at_008, f"the upgrade must not write {OLD_KEY}: {settings_at_008}"
    up = _differences(_without_registration_rows(rows_at_007), _without_registration_rows(rows_at_008))
    assert not up, f"the upgrade changed rows it had no reason to touch: {up}"
    down = _differences(_without_bookkeeping(rows_at_008), _without_bookkeeping(rows_down))
    assert not down, f"the downgrade changed rows, the open row included: {down}"
    assert _revision(db) == REV_007
    assert violations_at_008 == [] and _violations(db) == []
    print_success("the open row added, every other row as it was; the downgrade kept everything")


# =============================================================================
# 8. A 1.1 INSTALL AT HEAD
# =============================================================================


def test_a_1_1_install_without_its_registration_row_is_open_at_head(install_1_1: Path, tmp_path: Path) -> None:
    """Contract 8: a 1.1 install with accounts and no ``enable_registration`` — deleted with plain SQL at 1.1; 1.1 read the missing row as its default, true — upgraded to head holds ``registration_mode = 'open'``, written by the upgrade: 006 had nothing to convert, 008 wrote it."""
    print_section("Contract 8: a 1.1 install without enable_registration, at head")
    db = _copy(install_1_1, tmp_path / "sqlite" / "app.db")
    with _foreign_keys_on(db) as conn:
        deleted = conn.execute("DELETE FROM global_settings WHERE key = ?", (OLD_KEY,)).rowcount
        conn.commit()
    assert deleted == 1 and _accounts(db) > 0, "setup: a 1.1 install with accounts and no enable_registration"

    started = _utc_now()
    _migrate(db, "upgrade", "head")
    finished = _utc_now()
    _assert_includes_008(db)
    settings = _settings(db)

    assert _revision(db) == _scripts().get_current_head()
    assert OLD_KEY not in settings, f"nothing may bring {OLD_KEY} back: {settings}"
    _assert_written_by_the_upgrade(settings.get(NEW_KEY), started, finished)
    print_success("no enable_registration at 1.1 (open by default) → registration_mode = open at head")


@pytest.mark.parametrize(("enabled", "mode"), KEPT_AT_HEAD)
def test_a_1_1_install_keeps_its_registration_at_head(install_1_1: Path, tmp_path: Path, enabled: str, mode: str) -> None:
    """Contract 8: a 1.1 install with ``enable_registration = enabled``, written by user 1 on 2025-05-01, upgraded to head holds ``registration_mode = mode`` with that author and time: 006 converted it, 008 left it — a closed install is not reopened."""
    print_section(f"Contract 8: a 1.1 install with enable_registration={enabled!r}, at head")
    db = _copy(install_1_1, tmp_path / "sqlite" / "app.db")
    with _foreign_keys_on(db) as conn:
        changed = conn.execute("UPDATE global_settings SET value = ? WHERE key = ?", (enabled, OLD_KEY)).rowcount
        conn.commit()
    assert changed == 1, f"setup: the 1.1 install holds enable_registration = {enabled!r}"

    _migrate(db, "upgrade", "head")
    _assert_includes_008(db)
    settings = _settings(db)

    assert _revision(db) == _scripts().get_current_head()
    assert OLD_KEY not in settings
    assert settings.get(NEW_KEY) == (mode, NEW_TYPE, NEW_DESCRIPTION, V110_ROW_STAMP, V110_ROW_AUTHOR), f"the 1.1 install had enable_registration = {enabled!r}: {NEW_KEY} must be {mode!r}, by user {V110_ROW_AUTHOR} at {V110_ROW_STAMP}; got {settings.get(NEW_KEY)}"
    print_success(f"enable_registration={enabled!r} → registration_mode={mode!r}, same author, same time")

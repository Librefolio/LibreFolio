"""Migration ``006_registration_mode``: who may create an account (plan phase01Accounts §17 A5.1, lot A5a, contract point 1).

Until 1.3 one boolean row decided it, ``global_settings.enable_registration``. Release 1.3 has three modes — ``open``,
``invite``, ``disabled`` — held by one row, ``registration_mode``, and 006 converts the first into the second on
installations that hold real data. Data only: no table, no column. The contract pinned here:

1. The revision: id ``006_registration_mode`` (21 characters; ``alembic_version.version_num`` holds 32), in
   ``006_registration_mode.py``, on top of ``005_accounts_invites``; the chain keeps exactly one head, which is not named
   (the plugin settings of workstream X go on top as 007).
2. The upgrade converts the old row exactly as the application read it until now. ``get_setting_value`` parsed a
   ``bool`` as ``value.lower() in ("true", "1", "yes", "on")`` — no strip — and anything else as False. So the new row
   is ``open`` for those four spellings in any case, and ``disabled`` for every other value: ``false``, ``0``, ``no``,
   ``off``, the empty string, odd text, a value with spaces around it. Fail-closed, and what the server already did with
   that row. The new row has ``value_type`` ``str`` — the type of every text setting in ``schemas/settings.py``
   ("str", "int", "bool", "json"; review of 15/10), so the row an upgrade writes is the row a new install seeds — and the
   description «Who may create an account: open, invite or disabled»; ``updated_at`` and ``updated_by_user_id`` are the
   old row's, ``NULL`` included; the old row is gone.
3. The downgrade converts back: ``open`` → ``"true"``, ``invite`` and ``disabled`` → ``"false"``; ``value_type``
   ``bool``, the description «Allow new user registration», the metadata copied, the new row gone.
4. Idempotent both ways. An upgrade that finds ``registration_mode`` already there keeps it exactly as it is and only
   drops the old row; a downgrade that finds ``enable_registration`` already there keeps it and only drops the new one.
   A database with neither row migrates both ways and gains neither: the default comes from the application's startup
   seeding, not from the migration.
5. No other row is touched — of ``global_settings`` or of any table —, on a populated install, up and down.
6. A real 1.1 install (``test_post_migration``'s schema and rows: ``enable_registration = 'false'``, written by user 1)
   upgraded to head holds ``registration_mode = 'disabled'`` with that metadata; up, down and up again gives the same
   settings as the first upgrade.

Safety and fidelity: the harness of ``test_migration_005_accounts``, reused as it is. Every database is a file under
``tmp_path``; Alembic runs in this process on that file alone — a connect listener refuses any other — with
``PRAGMA foreign_keys`` asserted 1 at every step, as production migrates. Rows are written with plain SQL, the way a
real install holds them, never through the models.

Red until the migration exists: every test migrates to ``006_registration_mode`` (Alembic cannot locate it) or first
checks that the database it reads includes it. Since the review of 15/10, the cases that read the converted row are red
until 006 writes ``value_type`` ``str`` instead of ``string``.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Optional

import pytest

from backend.app.schemas.settings import GLOBAL_SETTINGS_DEFAULTS
from backend.test_scripts.test_db.test_migration_005_accounts import (
    REV_005,
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
from backend.test_scripts.test_db.test_post_migration import _install_v110
from backend.test_scripts.test_utils import print_section, print_success

REV_006 = "006_registration_mode"
OLD_KEY = "enable_registration"
NEW_KEY = "registration_mode"
NEW_DESCRIPTION = "Who may create an account: open, invite or disabled"
#: The value_type of every text setting in schemas/settings.py ("str", "int", "bool", "json"): what a new install seeds.
NEW_TYPE = "str"
OLD_DESCRIPTION = "Allow new user registration"
# Alembic's own bookkeeping: its row is expected to change.
BOOKKEEPING = frozenset({"alembic_version"})

STAMP = "2026-09-30 18:45:12.345678"
NEIGHBOUR_STAMP = "2026-10-01 07:00:00.000000"

# How get_setting_value read a "bool" until 1.3: value.lower() in ("true", "1", "yes", "on"), no strip.
OPEN_SPELLINGS = ("true", "TRUE", "True", "1", "yes", "YES", "on", "On")
CLOSED_SPELLINGS = ("false", "FALSE", "0", "no", "off", "Off", "", " true", "true ", "\ttrue", "yes\n", " 1", "2", "y", "t", "enabled", "maybe")
CONVERSIONS = [pytest.param(value, "open", id=f"{value!r}->open") for value in OPEN_SPELLINGS] + [pytest.param(value, "disabled", id=f"{value!r}->disabled") for value in CLOSED_SPELLINGS]
DOWNGRADES = [pytest.param("open", "true", id="open->true"), pytest.param("invite", "false", id="invite->false"), pytest.param("disabled", "false", id="disabled->false")]

# The row of the 1.1 install (test_post_migration.V110_ROWS): 'false', written by alice (user 1) on 2025-05-01.
V110_ROW_STAMP = "2025-05-01 10:00:00.000000"
V110_ROW_AUTHOR = 1

#: A global_settings row as SQLite holds it: (value, value_type, description, updated_at, updated_by_user_id).
Setting = tuple[str, str, Optional[str], str, Optional[int]]


# =============================================================================
# HELPERS
# =============================================================================


def _assert_includes_006(db: Path) -> None:
    """Barrier: ``db`` is at 006 or above; otherwise nothing that follows is about 006."""
    revision = _revision(db)
    assert REV_006 in _lineage(revision), f"barrier: {db.name} is at {revision}, which does not include {REV_006}: the assertions that follow would say nothing about the migration"


def _settings(db: Path) -> dict[str, Setting]:
    """Every row of ``global_settings``, by key, exactly as SQLite holds it."""
    with _connect(db) as conn:
        rows = conn.execute("SELECT key, value, value_type, description, updated_at, updated_by_user_id FROM global_settings").fetchall()
    return {key: (value, value_type, description, updated_at, updated_by) for key, value, value_type, description, updated_at, updated_by in rows}


def _write_setting(conn: sqlite3.Connection, key: str, setting: Setting) -> None:
    """One ``global_settings`` row, written as a real install holds it."""
    conn.execute("INSERT INTO global_settings (key, value, value_type, description, updated_at, updated_by_user_id) VALUES (?, ?, ?, ?, ?, ?)", (key, *setting))


def _write_neighbours(conn: sqlite3.Connection, author: int) -> dict[str, Setting]:
    """Two other settings beside the one 006 converts, one with an author and one without; what was written, by key."""
    neighbours: dict[str, Setting] = {
        "session_ttl_hours": ("48", "int", "Session cookie TTL in hours", NEIGHBOUR_STAMP, author),
        "default_language": ("it", "str", None, NEIGHBOUR_STAMP, None),
    }
    for key, setting in neighbours.items():
        _write_setting(conn, key, setting)
    return neighbours


def _others(settings: dict[str, Setting]) -> dict[str, Setting]:
    """``settings`` without the two rows 006 is about."""
    return {key: setting for key, setting in settings.items() if key not in (OLD_KEY, NEW_KEY)}


def _without_registration_rows(rows: Rows) -> Rows:
    """Every table but Alembic's bookkeeping, with ``global_settings`` stripped of the two rows 006 is about."""
    kept: Rows = {}
    for table, (columns, content) in rows.items():
        if table in BOOKKEEPING:
            continue
        if table == "global_settings":
            key_at = columns.index("key")
            content = [row for row in content if row[key_at] not in (OLD_KEY, NEW_KEY)]
        kept[table] = (columns, content)
    return kept


def _differences(expected: Rows, actual: Rows) -> dict[str, Any]:
    """The tables whose rows differ between ``expected`` and ``actual``, with a sample of what is missing and what is new."""
    differences: dict[str, Any] = {}
    for table in sorted(set(expected) | set(actual)):
        if table not in actual or table not in expected:
            differences[table] = "the table is only on one side"
            continue
        wanted, found = expected[table][1], actual[table][1]
        if expected[table][0] != actual[table][0] or wanted != found:
            differences[table] = {"missing or changed": [row for row in wanted if row not in found][:2], "unexpected": [row for row in found if row not in wanted][:2]}
    return differences


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(scope="module")
def at_005(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A new database at 005, without any setting row. Read-only for the tests: ``_copy`` it to write."""
    db = tmp_path_factory.mktemp("at-005") / "app.db"
    _migrate(db, "upgrade", REV_005)
    assert _settings(db) == {}, "setup: the migrations seed no global setting, the application's startup does"
    return db


@pytest.fixture(scope="module")
def install_at_005(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A populated install at 005: the real 1.1 schema and rows of test_post_migration, taken to 005 by the real migrations. Read-only: ``_copy`` it to write."""
    db = tmp_path_factory.mktemp("install-005") / "sqlite" / "app.db"
    _install_v110(db)
    _migrate(db, "upgrade", REV_005)
    assert _revision(db) == REV_005, "setup: the install is at 005"
    assert _settings(db).get(OLD_KEY, ("",))[0] == "false", f"setup: the 1.1 install holds enable_registration = 'false': {_settings(db)}"
    return db


# =============================================================================
# 1. THE REVISION
# =============================================================================


def test_revision_006_sits_on_005_and_the_chain_keeps_one_head() -> None:
    """Contract 1: ``006_registration_mode`` exists in ``006_registration_mode.py``, fits ``version_num``, revises 005; one head, not named."""
    print_section("Contract 1: revision 006_registration_mode")
    scripts = _scripts()
    revisions = {script.revision: script for script in scripts.walk_revisions()}

    assert REV_006 in revisions, f"revision {REV_006} not found; the chain has {sorted(revisions)}"
    script = revisions[REV_006]
    assert len(script.revision) <= 32, f"{script.revision!r} is {len(script.revision)} characters: alembic_version.version_num is VARCHAR(32)"
    assert script.down_revision == REV_005, f"{REV_006} must revise {REV_005}, revises {script.down_revision!r}"
    assert Path(script.path).name == f"{REV_006}.py", f"the revision id is the file name without .py, found in {Path(script.path).name}"
    heads = scripts.get_heads()
    assert len(heads) == 1, f"the chain must not fork: {len(heads)} heads {heads}"
    print_success(f"{REV_006} revises {REV_005}; one head ({heads[0]})")


# =============================================================================
# 2. THE UPGRADE CONVERTS THE ROW AS THE APPLICATION READ IT
# =============================================================================


@pytest.mark.parametrize(("old_value", "mode"), CONVERSIONS)
def test_the_upgrade_converts_enable_registration_as_the_application_read_it(at_005: Path, tmp_path: Path, old_value: str, mode: str) -> None:
    """Contract 2: ``open`` exactly when ``old_value.lower()`` is true, 1, yes or on — no strip —, ``disabled`` otherwise; type, description and metadata as pinned; the old row gone; the neighbours as they were."""
    print_section(f"Contract 2: enable_registration={old_value!r} → {mode}")
    db = _copy(at_005, tmp_path / "app.db")
    with _foreign_keys_on(db) as conn:
        author = _insert_user(conn, "author")
        _write_setting(conn, OLD_KEY, (old_value, "bool", "Allow new users to register", STAMP, author))
        neighbours = _write_neighbours(conn, author)
        conn.commit()

    _migrate(db, "upgrade", REV_006)
    _assert_includes_006(db)
    settings = _settings(db)

    assert OLD_KEY not in settings, f"the upgrade must delete {OLD_KEY}: {settings}"
    assert settings.get(NEW_KEY) == (
        mode,
        NEW_TYPE,
        NEW_DESCRIPTION,
        STAMP,
        author,
    ), f"{OLD_KEY}={old_value!r} was read as {'True' if mode == 'open' else 'False'} by the application until now (value.lower() in true/1/yes/on, no strip): {NEW_KEY} must be {mode!r}, value_type {NEW_TYPE!r} with its description, written at {STAMP} by user {author}; got {settings.get(NEW_KEY)}"
    assert _others(settings) == neighbours, f"the upgrade touched other settings: {_others(settings)}"
    print_success(f"{old_value!r} → {mode}, metadata copied, neighbours untouched")


def test_the_upgrade_keeps_a_row_without_an_author_without_one(at_005: Path, tmp_path: Path) -> None:
    """Contract 2: an ``enable_registration`` nobody signed (``updated_by_user_id`` NULL) gives a ``registration_mode`` nobody signed — NULL is copied, never filled in."""
    print_section("Contract 2: a NULL author stays NULL")
    db = _copy(at_005, tmp_path / "app.db")
    with _foreign_keys_on(db) as conn:
        _write_setting(conn, OLD_KEY, ("true", "bool", "Allow new users to register", STAMP, None))
        conn.commit()

    _migrate(db, "upgrade", REV_006)
    _assert_includes_006(db)

    assert _settings(db) == {NEW_KEY: ("open", NEW_TYPE, NEW_DESCRIPTION, STAMP, None)}
    print_success("open, written at the old row's time, by nobody")


def test_the_converted_row_is_the_row_a_new_install_seeds(at_005: Path, tmp_path: Path) -> None:
    """Contract 2 (review of 15/10): the ``value_type`` and the description 006 writes are the registry's, ``GLOBAL_SETTINGS_DEFAULTS["registration_mode"]``, from which a new install seeds its row: an upgraded install and a new one hold the same row.

    GUARD: it compares the migration with the registry, whatever both say, so that they cannot drift apart again;
    ``NEW_TYPE`` pins what they say.
    """
    print_section("Contract 2: the converted row is a new install's row")
    db = _copy(at_005, tmp_path / "app.db")
    with _foreign_keys_on(db) as conn:
        _write_setting(conn, OLD_KEY, ("true", "bool", "Allow new users to register", STAMP, None))
        conn.commit()

    _migrate(db, "upgrade", REV_006)
    _assert_includes_006(db)
    converted = _settings(db).get(NEW_KEY)
    seeded = GLOBAL_SETTINGS_DEFAULTS[NEW_KEY]

    assert converted is not None and converted[1:3] == (seeded["type"], seeded["description"]), f"the migration writes {converted}, a new install seeds {seeded}: an upgraded install and a new one must hold the same row"
    print_success(f"value_type {seeded['type']!r} and the description, as a new install seeds them")


# =============================================================================
# 3. THE DOWNGRADE CONVERTS BACK
# =============================================================================


@pytest.mark.parametrize(("mode", "old_value"), DOWNGRADES)
def test_the_downgrade_converts_registration_mode_back(at_005: Path, tmp_path: Path, mode: str, old_value: str) -> None:
    """Contract 3: ``open`` → ``"true"``, ``invite`` and ``disabled`` → ``"false"``, a ``bool`` with its old description, the metadata copied; the new row gone; the neighbours as they were; at 005."""
    print_section(f"Contract 3: registration_mode={mode} → {old_value}")
    db = _copy(at_005, tmp_path / "app.db")
    _migrate(db, "upgrade", REV_006)
    _assert_includes_006(db)
    with _foreign_keys_on(db) as conn:
        author = _insert_user(conn, "author")
        _write_setting(conn, NEW_KEY, (mode, NEW_TYPE, NEW_DESCRIPTION, STAMP, author))
        neighbours = _write_neighbours(conn, author)
        conn.commit()

    _migrate(db, "downgrade", REV_005)
    settings = _settings(db)

    assert _revision(db) == REV_005
    assert NEW_KEY not in settings, f"the downgrade must delete {NEW_KEY}: {settings}"
    assert settings.get(OLD_KEY) == (old_value, "bool", OLD_DESCRIPTION, STAMP, author), f"{NEW_KEY}={mode!r} must go back to {OLD_KEY}={old_value!r}, a bool described {OLD_DESCRIPTION!r}, written at {STAMP} by user {author}; got {settings.get(OLD_KEY)}"
    assert _others(settings) == neighbours, f"the downgrade touched other settings: {_others(settings)}"
    print_success(f"{mode} → {old_value}, metadata copied, neighbours untouched")


# =============================================================================
# 4. IDEMPOTENT BOTH WAYS
# =============================================================================


def test_an_upgrade_that_finds_registration_mode_keeps_it_and_drops_the_old_row(at_005: Path, tmp_path: Path) -> None:
    """Contract 4: both rows at 005 — a run that wrote the new row and stopped, or a row seeded early —: ``registration_mode`` stays exactly as it is, whatever ``enable_registration`` says, and ``enable_registration`` goes.

    The two rows disagree on purpose (``invite`` against ``'true'``, another author, another time): a conversion that ran
    anyway would overwrite the new row with ``open`` and the old row's metadata.
    """
    print_section("Contract 4: the upgrade keeps an existing registration_mode")
    db = _copy(at_005, tmp_path / "app.db")
    existing: Setting = ("invite", NEW_TYPE, "Seeded before the migration ran", NEIGHBOUR_STAMP, None)
    with _foreign_keys_on(db) as conn:
        author = _insert_user(conn, "author")
        _write_setting(conn, OLD_KEY, ("true", "bool", "Allow new users to register", STAMP, author))
        _write_setting(conn, NEW_KEY, existing)
        neighbours = _write_neighbours(conn, author)
        conn.commit()

    _migrate(db, "upgrade", REV_006)
    _assert_includes_006(db)
    settings = _settings(db)

    assert OLD_KEY not in settings, f"the upgrade must delete {OLD_KEY} even when {NEW_KEY} is already there: {settings}"
    assert settings.get(NEW_KEY) == existing, f"{NEW_KEY} was already there: the upgrade must leave it as it was, {existing}; got {settings.get(NEW_KEY)}"
    assert _others(settings) == neighbours
    print_success("registration_mode kept as it was, enable_registration dropped")


def test_a_downgrade_that_finds_enable_registration_keeps_it_and_drops_the_new_row(at_005: Path, tmp_path: Path) -> None:
    """Contract 4: both rows at 006: ``enable_registration`` stays exactly as it is and ``registration_mode`` goes — the two disagree on purpose (``'true'`` against ``disabled``)."""
    print_section("Contract 4: the downgrade keeps an existing enable_registration")
    db = _copy(at_005, tmp_path / "app.db")
    _migrate(db, "upgrade", REV_006)
    _assert_includes_006(db)
    existing: Setting = ("true", "bool", "Allow new users to register", NEIGHBOUR_STAMP, None)
    with _foreign_keys_on(db) as conn:
        author = _insert_user(conn, "author")
        _write_setting(conn, NEW_KEY, ("disabled", NEW_TYPE, NEW_DESCRIPTION, STAMP, author))
        _write_setting(conn, OLD_KEY, existing)
        neighbours = _write_neighbours(conn, author)
        conn.commit()

    _migrate(db, "downgrade", REV_005)
    settings = _settings(db)

    assert _revision(db) == REV_005
    assert NEW_KEY not in settings, f"the downgrade must delete {NEW_KEY} even when {OLD_KEY} is already there: {settings}"
    assert settings.get(OLD_KEY) == existing, f"{OLD_KEY} was already there: the downgrade must leave it as it was, {existing}; got {settings.get(OLD_KEY)}"
    assert _others(settings) == neighbours
    print_success("enable_registration kept as it was, registration_mode dropped")


def test_a_database_without_either_row_migrates_both_ways_and_gains_neither(at_005: Path, tmp_path: Path) -> None:
    """Contract 4: no ``enable_registration`` at 005 (a new database, settings never seeded): the upgrade works and creates no ``registration_mode`` — the default is the startup seeding's job —, the downgrade works and creates no ``enable_registration``; the other settings as they were."""
    print_section("Contract 4: a database without the row")
    db = _copy(at_005, tmp_path / "app.db")
    with _foreign_keys_on(db) as conn:
        neighbours = _write_neighbours(conn, _insert_user(conn, "author"))
        conn.commit()

    _migrate(db, "upgrade", REV_006)
    _assert_includes_006(db)
    after_upgrade = _settings(db)
    _migrate(db, "downgrade", REV_005)
    after_downgrade = _settings(db)

    assert after_upgrade == neighbours, f"the upgrade of a database without {OLD_KEY} must change no setting: {after_upgrade}"
    assert after_downgrade == neighbours, f"the downgrade of a database without {NEW_KEY} must change no setting: {after_downgrade}"
    assert _revision(db) == REV_005
    print_success("up and down, nothing created, nothing lost")


# =============================================================================
# 5. NO OTHER ROW IS TOUCHED
# =============================================================================


def test_up_and_down_touch_no_other_row_of_a_populated_install(install_at_005: Path, tmp_path: Path) -> None:
    """Contract 5: on the 1.1 install at 005 — every table populated, gaps, a deleted user —, the upgrade and then the downgrade change no row of any table but the registration row; no foreign-key violation at either end.

    Barrier first: the upgrade did convert the row, or "nothing else changed" would pass for a migration that does nothing.
    """
    print_section("Contract 5: no other row, up and down")
    db = _copy(install_at_005, tmp_path / "app.db")
    rows_at_005 = _rows(db)

    _migrate(db, "upgrade", REV_006)
    _assert_includes_006(db)
    rows_at_006 = _rows(db)
    converted = _settings(db)
    violations_at_006 = _violations(db)
    _migrate(db, "downgrade", REV_005)
    rows_down = _rows(db)

    assert OLD_KEY not in converted and NEW_KEY in converted, f"barrier: the upgrade did not convert the registration row, so the comparisons below would prove nothing: {converted}"
    up = _differences(_without_registration_rows(rows_at_005), _without_registration_rows(rows_at_006))
    assert not up, f"the upgrade changed rows it had no reason to touch: {up}"
    down = _differences(_without_registration_rows(rows_at_006), _without_registration_rows(rows_down))
    assert not down, f"the downgrade changed rows it had no reason to touch: {down}"
    assert violations_at_006 == [] and _violations(db) == []
    print_success(f"{len(_without_registration_rows(rows_at_005))} tables, every other row as it was, both ways")


# =============================================================================
# 6. A REAL 1.1 INSTALL
# =============================================================================


def test_a_1_1_install_upgraded_to_head_holds_its_mode_with_its_metadata(install_at_005: Path, tmp_path: Path) -> None:
    """Contract 6: the 1.1 install's ``enable_registration = 'false'``, written by user 1 on 2025-05-01, is ``registration_mode = 'disabled'`` at head, written by the same user at the same time — whatever revisions sit above 006."""
    print_section("Contract 6: a 1.1 install at head")
    db = _copy(install_at_005, tmp_path / "app.db")

    _migrate(db, "upgrade", "head")
    _assert_includes_006(db)
    settings = _settings(db)

    assert _revision(db) == _scripts().get_current_head()
    assert OLD_KEY not in settings
    assert settings.get(NEW_KEY) == ("disabled", NEW_TYPE, NEW_DESCRIPTION, V110_ROW_STAMP, V110_ROW_AUTHOR), f"the 1.1 install had registration off: {NEW_KEY} must be disabled, value_type {NEW_TYPE!r}, by user {V110_ROW_AUTHOR} at {V110_ROW_STAMP}; got {settings.get(NEW_KEY)}"
    print_success("enable_registration=false became registration_mode=disabled, same author, same time")


def test_up_down_and_up_again_gives_the_settings_of_the_first_upgrade(install_at_005: Path, tmp_path: Path) -> None:
    """Contract 4 and 6: on the 1.1 install, upgrade to 006, downgrade to 005, upgrade again: every setting as after the first upgrade, and the intermediate state is the 1.1 row's meaning in the old shape (``'false'``)."""
    print_section("Contract 4/6: the round trip")
    db = _copy(install_at_005, tmp_path / "app.db")

    _migrate(db, "upgrade", REV_006)
    _assert_includes_006(db)
    first = _settings(db)
    _migrate(db, "downgrade", REV_005)
    between = _settings(db)
    _migrate(db, "upgrade", REV_006)
    again = _settings(db)

    assert between.get(OLD_KEY) == ("false", "bool", OLD_DESCRIPTION, V110_ROW_STAMP, V110_ROW_AUTHOR), f"at 005 again: {between.get(OLD_KEY)}"
    assert again == first, f"up, down and up again must give the settings of the first upgrade: {first} then {again}"
    print_success("up → down → up: the same settings")

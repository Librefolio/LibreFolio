"""Migration ``011_provider_exchange_timezone``: the timezone a provider dates by, and the sentinel on the assignments whose rows the old Yahoo rule dated (release 1.3, workstream Z, lot Z-33, the coordinator's decision N86).

yfinance 1.7.0 stamps every daily quote, dividend and split at midnight in the exchange's timezone. Until Z-33 the Yahoo
plugin dated that midnight by its UTC date: the day before for every exchange east of UTC (Milan all year, London in
summer time, Tokyo). From Z-33 the plugin dates each bar on the exchange's own calendar and reports the timezone; the
refresh keeps it on the provider assignment, in the new column ``asset_provider_assignments.exchange_timezone``. The
rows a yfinance assignment already holds were dated by the old rule: the upgrade marks those assignments with the
sentinel ``legacy-utc``, and the first refresh that learns the exchange's timezone re-dates them
(``test_asset_source_refresh``, the ``test_z33_*`` cases). The contract pinned here (N86 §3, with §4 for the model):

1. The revision: id ``011_provider_exchange_timezone`` (30 characters; ``alembic_version.version_num`` holds 32), in
   ``011_provider_exchange_timezone.py``, on top of ``010_provider_reported_currency``; the chain keeps one head, which
   is not named.
2. A new database at 011 — the revision named, not head: the head moves on, and what a later revision adds to this table
   is that revision's to pin —: ``exchange_timezone VARCHAR(64)``, nullable, no default, in no key, index or constraint;
   every other column, key and index of the table as at 010. A row written without it reads NULL, a yfinance one too —
   the sentinel is no default: a new assignment's rows are dated by the new rule —; ``Europe/London`` reads as written.
3. The ``AssetProviderAssignment`` model declares the same column (§4): the service suites build their databases with
   ``create_all``, production with the migrations.
4. A populated install at 010 upgraded to 011 keeps every row of every table, ids included, each table read on the
   columns it had — the assignments' ``updated_at`` too: the marking is plain SQL, no edit of the assignment —; then
   every assignment whose ``provider_code`` is ``yfinance`` reads ``legacy-utc`` and every other one NULL; every other
   object of the schema keeps its SQL; no foreign-key violation, integrity ok; taken on to head, the database is at head.
5. The downgrade to 010 of that install at 011 drops the column and nothing else — plain ``ALTER TABLE``, never a batch,
   with foreign keys on, as 010: a rebuild of the table would cascade into the provider events and trip the transactions
   linked to them (``ON DELETE RESTRICT``) —, every row of every table kept. Upgrading again gives the column back and
   marks every yfinance assignment again: the values, a learnt ``Europe/London`` included, went with the downgrade.
6. Idempotent both ways: an upgrade that finds the column (a run that stopped after its ``ALTER``, the revision still
   010) only marks the yfinance assignments still NULL, every value it finds kept, on any provider; a downgrade that
   finds the column gone (the revision still 011) goes through and changes nothing.
7. The restore of an old backup (N86 §6): a backup at 004 (a 1.2 install, whose Yahoo rows are the shifted ones) or at
   010, taken to head by the restore staging's own step (``instance_backup.staging._upgrade``: ``alembic upgrade head``
   on the copy, in a process of its own), gets the sentinel on its yfinance assignments and NULL on the others, and its
   rows as they were: the migration marks, it never re-dates. The seam chosen for §6: the marking is pinned here, on the
   restore path itself; the re-dating that follows is the refresh's, pinned from a ``legacy-utc`` assignment in
   ``test_asset_source_refresh`` — a refresh runs on the live database only, which a restored copy becomes after the
   swap and a restart, never inside this process.

Safety and fidelity: the harness of ``test_migration_005_accounts`` and ``_full_shape`` of
``test_migration_007_plugin_settings``, as ``test_migration_010_reported_currency`` uses them, with that file's London
line and values. Every database is a file under ``tmp_path``; Alembic runs in this process on that file alone — a
connect listener refuses any other — with ``PRAGMA foreign_keys`` asserted 1 at every step, as production migrates
(``staging._upgrade`` runs its own process, on the copy named by ``-x sqlalchemy.url`` only). Rows are written with
plain SQL, the way a real install holds them. The 1.2 backup is the install of 005 (the v1.1.0 install of
``test_post_migration`` taken to 004, converted by the post-migration fixes, plus the rows only 1.2 writes) and a Milan
line stored by the old rule: Eni, its yfinance assignment, three closes and a dividend each on the day before its
exchange day, and the broker's DIVIDEND linked to that dividend. The install at 010 is that backup taken to 006 with the
account tokens of 1.3, to 009 with 010's London line (Vodafone, yfinance, a provider dividend and its transaction), to
010 with the codes 010 learns (``GBp``, ``USD``). Assignments: three on yfinance (AAPL from 1.1, Eni, Vodafone), two on
other providers (mockprov, borsa_italiana).

Red until Z-33: Alembic cannot locate 011 (each test that migrates to it fails saying so, never as an error of its
fixture), the head does not include it, the model has no ``exchange_timezone``. Each test says which.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from backend.app.db import post_migration
from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.services.platform.instance_backup import staging
from backend.test_scripts.test_db.test_migration_005_accounts import (
    BOOKKEEPING,
    HEAD_ROWS,
    REV_004,
    ROWS_1_2,
    Declared,
    Rows,
    _connect,
    _copy,
    _foreign_keys_on,
    _integrity,
    _lineage,
    _migrate,
    _revision,
    _row_changes,
    _rows,
    _scripts,
    _table_info,
    _violations,
)
from backend.test_scripts.test_db.test_migration_007_plugin_settings import _full_shape
from backend.test_scripts.test_db.test_migration_010_reported_currency import (
    LONDON_LINE,
    LONDON_TICKER,
    REPORTED_AT_010,
    REV_006,
    REV_009,
    REV_010,
    _beside_the_table,
    _insert_asset,
    _insert_assignment,
    _schema,
    _write_reported_at_010,
)
from backend.test_scripts.test_db.test_post_migration import _install_v110
from backend.test_scripts.test_utils import print_section, print_success

REV_011 = "011_provider_exchange_timezone"
TABLE = "asset_provider_assignments"
COLUMN = "exchange_timezone"
#: What the upgrade writes on a yfinance assignment: its rows were dated by the old rule, the next refresh re-dates them.
SENTINEL = "legacy-utc"
YAHOO = "yfinance"
#: What ``PRAGMA table_info`` must say of the new column (§2): ``VARCHAR(64)``, nullable, no default, not a key.
DECLARED = Declared("VARCHAR(64)", False, None, False)
#: The column as §2 declares it, added by hand: the state a run interrupted after its ``ALTER`` leaves.
ADD_COLUMN = f"ALTER TABLE {TABLE} ADD COLUMN {COLUMN} VARCHAR(64)"
DROP_COLUMN = f"ALTER TABLE {TABLE} DROP COLUMN {COLUMN}"
#: The entries of ``_full_shape`` that list the table's columns: the new one is taken out to compare with 010.
COLUMN_ENTRIES = ("columns (name: nullable)", "column types")
#: The entries of ``_full_shape`` that list keys, indexes and constraints: the new column must be in none of them.
KEY_ENTRIES = ("primary key", "foreign keys", "indexes (name, columns, unique)", "unique column sets", "unique constraints", "check constraints (name: sql)")
STAMP = "2025-05-10 09:00:00.000000"
FETCHED = "2025-05-21 21:00:00.000000"
MILAN_NAME = "Eni S.p.A."
MILAN_TICKER = "ENI.MI"
#: A zone a refresh learns and keeps (§5: lost with the downgrade).
LEARNT = "Europe/London"

# A Milan line as a 1.2 server stored it: the closes of Monday 2025-05-19 to Wednesday 05-21 and the dividend of Monday
# 05-19, each on the day before (yfinance's midnight in Milan, read in UTC); the broker's DIVIDEND, paid on 05-21, linked
# to the dividend. Written at 004, with foreign keys on; every column named, so it reads the same at 004 and at 010.
MILAN_LINE = f"""
PRAGMA foreign_keys = ON;
BEGIN;

INSERT INTO assets (display_name, currency, asset_type, quote_base_quantity, active, identifier_ticker, created_at, updated_at)
    VALUES ('{MILAN_NAME}', 'EUR', 'STOCK', 1, 1, '{MILAN_TICKER}', '{STAMP}', '{STAMP}');
INSERT INTO asset_provider_assignments (asset_id, provider_code, identifier, identifier_type, provider_params, last_fetch_at, created_at, updated_at)
    SELECT id, '{YAHOO}', '{MILAN_TICKER}', 'TICKER', NULL, '{FETCHED}', '{STAMP}', '{FETCHED}' FROM assets WHERE display_name = '{MILAN_NAME}';
INSERT INTO price_history (asset_id, date, close, currency, source_plugin_key, fetched_at)
    SELECT id, '2025-05-18', 13.10, 'EUR', '{YAHOO}', '{FETCHED}' FROM assets WHERE display_name = '{MILAN_NAME}';
INSERT INTO price_history (asset_id, date, close, currency, source_plugin_key, fetched_at)
    SELECT id, '2025-05-19', 13.22, 'EUR', '{YAHOO}', '{FETCHED}' FROM assets WHERE display_name = '{MILAN_NAME}';
INSERT INTO price_history (asset_id, date, close, currency, source_plugin_key, fetched_at)
    SELECT id, '2025-05-20', 13.05, 'EUR', '{YAHOO}', '{FETCHED}' FROM assets WHERE display_name = '{MILAN_NAME}';
INSERT INTO asset_events (asset_id, date, type, value, currency, provider_assignment_id, notes, created_at, updated_at)
    SELECT asset_id, '2025-05-18', 'DIVIDEND', 0.35, 'EUR', id, NULL, '{FETCHED}', '{FETCHED}' FROM asset_provider_assignments WHERE identifier = '{MILAN_TICKER}';
INSERT INTO transactions (broker_id, asset_id, type, date, quantity, amount, currency, asset_event_id, created_at, updated_at)
    SELECT 1, e.asset_id, 'DIVIDEND', '2025-05-21', 0, 35.0, 'EUR', e.id, '{FETCHED}', '{FETCHED}'
      FROM asset_events e JOIN asset_provider_assignments a ON a.id = e.provider_assignment_id WHERE a.identifier = '{MILAN_TICKER}';

COMMIT;
"""


# =============================================================================
# HELPERS
# =============================================================================


def _missing_011() -> Optional[str]:
    """Why nothing can be migrated to 011 yet, or None when Alembic knows the revision."""
    scripts = _scripts()
    if REV_011 in {script.revision for script in scripts.walk_revisions()}:
        return None
    return f"red until Z-33: Alembic cannot locate {REV_011}; the chain ends at {scripts.get_current_head()}"


def _require_011() -> None:
    """Barrier of the tests that migrate to 011 themselves: the test fails, saying why, rather than erroring in Alembic."""
    missing = _missing_011()
    if missing is not None:
        pytest.fail(missing, pytrace=False)


def _ran[ResultT](result: ResultT | str) -> ResultT:
    """The result of a fixture that migrates to 011, or the test fails with the reason the fixture could not."""
    if isinstance(result, str):
        pytest.fail(result, pytrace=False)
    return result


def _assert_includes_011(db: Path) -> None:
    """Barrier: ``db`` is at 011 or above; otherwise nothing that follows is about 011."""
    revision = _revision(db)
    assert REV_011 in _lineage(revision), f"red until Z-33: {db.name} is at {revision}, which does not include {REV_011}"


def _without_column(columns: dict[str, Declared]) -> dict[str, Declared]:
    return {name: declared for name, declared in columns.items() if name != COLUMN}


def _shape_without_column(shape: dict[str, Any]) -> dict[str, Any]:
    """``_full_shape`` of the table, the new column taken out of the entries that list columns."""
    return {key: ({name: value for name, value in entry.items() if name != COLUMN} if key in COLUMN_ENTRIES else entry) for key, entry in shape.items()}


def _keys_naming_the_column(shape: dict[str, Any]) -> dict[str, Any]:
    """The key, index and constraint entries of ``_full_shape`` that name the new column: none, by §2."""
    return {key: shape[key] for key in KEY_ENTRIES if COLUMN in repr(shape[key])}


def _zones(db: Path) -> dict[int, Optional[str]]:
    """``{assignment id: exchange_timezone}`` of every assignment."""
    with _connect(db) as conn:
        return dict(conn.execute(f"SELECT id, {COLUMN} FROM {TABLE}").fetchall())


def _codes(db: Path) -> dict[int, str]:
    """``{assignment id: provider_code}`` of every assignment."""
    with _connect(db) as conn:
        return dict(conn.execute(f"SELECT id, provider_code FROM {TABLE}").fetchall())


def _marked(codes: dict[int, str]) -> dict[int, Optional[str]]:
    """What the upgrade leaves on assignments that held NULL: the sentinel on yfinance, NULL on every other provider."""
    return {assignment_id: (SENTINEL if code == YAHOO else None) for assignment_id, code in codes.items()}


def _codes_in(rows: Rows) -> dict[int, str]:
    """``{assignment id: provider_code}`` of the assignments in a ``_rows`` snapshot."""
    columns, content = rows[TABLE]
    return {row[columns.index("id")]: row[columns.index("provider_code")] for row in content}


def _id_of(db: Path, identifier: str) -> int:
    with _connect(db) as conn:
        (assignment_id,) = conn.execute(f"SELECT id FROM {TABLE} WHERE identifier = ?", (identifier,)).fetchone()
    return assignment_id


def _provider_events(db: Path) -> dict[int, int]:
    """``{event id: assignment id}`` of every event a provider assignment generated."""
    with _connect(db) as conn:
        return dict(conn.execute("SELECT id, provider_assignment_id FROM asset_events WHERE provider_assignment_id IS NOT NULL").fetchall())


def _linked_transactions(db: Path) -> dict[int, int]:
    """``{transaction id: event id}`` of every transaction linked to an event a provider generated."""
    with _connect(db) as conn:
        return dict(conn.execute("SELECT t.id, t.asset_event_id FROM transactions t JOIN asset_events e ON e.id = t.asset_event_id WHERE e.provider_assignment_id IS NOT NULL").fetchall())


def _line(db: Path, ticker: str) -> dict[str, list[tuple[Any, ...]]]:
    """The rows of the line assigned under ``ticker``, by their dates: its prices, its events, the transactions linked to them."""
    with _connect(db) as conn:
        return {
            "prices (date, close, source)": conn.execute(f"SELECT p.date, p.close, p.source_plugin_key FROM price_history p JOIN {TABLE} a ON a.asset_id = p.asset_id WHERE a.identifier = ? ORDER BY p.date", (ticker,)).fetchall(),
            "events (id, date, type, assignment)": conn.execute(f"SELECT e.id, e.date, e.type, e.provider_assignment_id FROM asset_events e JOIN {TABLE} a ON a.asset_id = e.asset_id WHERE a.identifier = ? ORDER BY e.id", (ticker,)).fetchall(),
            "linked transactions (id, date, event)": conn.execute(
                f"SELECT t.id, t.date, t.asset_event_id FROM transactions t JOIN asset_events e ON e.id = t.asset_event_id JOIN {TABLE} a ON a.asset_id = e.asset_id WHERE a.identifier = ? ORDER BY t.id",
                (ticker,),
            ).fetchall(),
        }


def _check_population(db: Path) -> None:
    """Setup barrier: yfinance assignments and assignments of other providers both there, events of providers linked to
    transactions, the Milan line as the old rule stored it — or «marks yfinance only» and «nothing cascades» prove nothing."""
    codes = _codes(db)
    yahoo = [assignment_id for assignment_id, code in codes.items() if code == YAHOO]
    others = [assignment_id for assignment_id, code in codes.items() if code != YAHOO]
    assert len(yahoo) >= 2 and len(others) >= 2, f"setup: yfinance assignments {yahoo} and others {others}, two of each at least"
    events, linked = _provider_events(db), _linked_transactions(db)
    assert len(set(events.values())) >= 2 and len(linked) >= 2, f"setup: events of two assignments, each linked to a transaction; events {events}, linked {linked}"
    milan = _line(db, MILAN_TICKER)
    assert [day for day, _close, _source in milan["prices (date, close, source)"]] == ["2025-05-18", "2025-05-19", "2025-05-20"], f"setup: the Milan line's closes as the old rule stored them: {milan}"
    assert len(milan["linked transactions (id, date, event)"]) == 1, f"setup: the Milan dividend's transaction: {milan}"
    assert _violations(db) == [], "setup: the rows are consistent"


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(scope="module")
def fresh_head(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A new database taken to head by the real migrations. Read-only for the tests: ``_copy`` it to write."""
    db = tmp_path_factory.mktemp("fresh-head") / "app.db"
    _migrate(db, "upgrade", "head")
    return db


@pytest.fixture(scope="module")
def fresh_011(tmp_path_factory: pytest.TempPathFactory) -> Path | str:
    """A new database taken to 011 by name, not to head: §2 is 011's own contract, and the head moves on with later
    revisions (the lesson of MIG010-002 when 011 landed). Read-only for the tests: ``_copy`` it to write. While Alembic
    knows no 011, the reason instead: each test fails on it."""
    missing = _missing_011()
    if missing is not None:
        return missing
    db = tmp_path_factory.mktemp("fresh-011") / "app.db"
    _migrate(db, "upgrade", REV_011)
    assert _revision(db) == REV_011, f"setup: the new database is at {_revision(db)}, not at {REV_011}"
    return db


@pytest.fixture(scope="module")
def fresh_010(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A new database taken to 010: the table as it is before this lot. Read-only."""
    db = tmp_path_factory.mktemp("fresh-010") / "app.db"
    _migrate(db, "upgrade", REV_010)
    assert COLUMN not in _table_info(db, TABLE), "setup: at 010 the table has no exchange_timezone"
    return db


@pytest.fixture(scope="module")
def created_by_models(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A new database built by ``SQLModel.metadata.create_all``, as the service suites build theirs. Read-only."""
    db = tmp_path_factory.mktemp("create-all") / "app.db"
    engine = create_engine(f"sqlite:///{db}", poolclass=NullPool)
    try:
        SQLModel.metadata.create_all(engine)
    finally:
        engine.dispose()
    return db


@pytest.fixture(scope="module")
def backup_at_004(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A 1.2 install at 004 holding the Milan line the old rule stored (see the module docstring). Read-only."""
    db = tmp_path_factory.mktemp("backup-004") / "sqlite" / "app.db"
    _install_v110(db)
    _migrate(db, "upgrade", REV_004)
    report = post_migration.run_post_migration_fixes(db, None)
    assert report.outcomes.get("autoincrement") == "applied", f"setup: the post-migration fixes did not convert the 1.1 rows: {report}"
    with _foreign_keys_on(db) as conn:
        conn.executescript(ROWS_1_2)
        conn.executescript(MILAN_LINE)
    assert _revision(db) == REV_004, "setup: a 1.2 install is at 004"
    _check_population(db)
    return db


@pytest.fixture(scope="module")
def install_at_010(backup_at_004: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The 1.2 backup taken to 010 with the rows of 1.3 (see the module docstring). Read-only: ``_copy`` it to write."""
    db = _copy(backup_at_004, tmp_path_factory.mktemp("install-010") / "sqlite" / "app.db")
    _migrate(db, "upgrade", REV_006)
    with _foreign_keys_on(db) as conn:
        conn.executescript(HEAD_ROWS)
    _migrate(db, "upgrade", REV_009)
    with _foreign_keys_on(db) as conn:
        conn.executescript(LONDON_LINE)
    _migrate(db, "upgrade", REV_010)
    _write_reported_at_010(db)
    assert _revision(db) == REV_010, "setup: the install is at 010"
    assert COLUMN not in _table_info(db, TABLE), "setup: an install at 010 has no exchange_timezone"
    _check_population(db)
    assert {_codes(db)[_id_of(db, ticker)] for ticker in (LONDON_TICKER, MILAN_TICKER, "AAPL")} == {YAHOO}, "setup: Vodafone, Eni and AAPL on yfinance"
    with _connect(db) as conn:
        learnt = dict(conn.execute(f"SELECT identifier, reported_currency FROM {TABLE} WHERE reported_currency IS NOT NULL").fetchall())
    assert learnt == REPORTED_AT_010, f"setup: the codes 010 learnt, which 011 must keep: {learnt}"
    return db


@dataclass(frozen=True)
class Upgrade:
    """A copy of the install at 010: its schema and rows before ``upgrade 011`` and right after; then taken on to head."""

    db: Path
    rows_before: Rows
    schema_before: list[tuple[Any, ...]]
    table_before: dict[str, Any]
    shape_before: dict[str, Any]
    codes: dict[int, str]
    rows_after: Rows
    schema_after: list[tuple[Any, ...]]
    table_after: dict[str, Any]
    shape_after: dict[str, Any]
    zones_after: dict[int, Optional[str]]
    violations: list[tuple[Any, ...]]
    integrity: list[tuple[Any, ...]]


@pytest.fixture(scope="module")
def upgraded(install_at_010: Path, tmp_path_factory: pytest.TempPathFactory) -> Upgrade | str:
    """The upgrade of the install to 011, or, while Alembic knows no 011, the reason: each test fails on it."""
    missing = _missing_011()
    if missing is not None:
        return missing
    db = _copy(install_at_010, tmp_path_factory.mktemp("upgraded") / "app.db")
    rows_before, schema_before, table_before, shape_before = _rows(db), _schema(db), _table_info(db, TABLE), _full_shape(db, TABLE)
    _migrate(db, "upgrade", REV_011)
    upgrade = Upgrade(
        db=db,
        rows_before=rows_before,
        schema_before=schema_before,
        table_before=table_before,
        shape_before=shape_before,
        codes=_codes(db),
        rows_after=_rows(db),
        schema_after=_schema(db),
        table_after=_table_info(db, TABLE),
        shape_after=_full_shape(db, TABLE),
        zones_after=_zones(db),
        violations=_violations(db),
        integrity=_integrity(db),
    )
    _migrate(db, "upgrade", "head")
    return upgrade


@dataclass(frozen=True)
class RoundTrip:
    """A copy of the install taken to 011, Vodafone's zone learnt (``LEARNT``), downgraded to 010, then upgraded to 011 again.

    ``downgrade_error`` is what the downgrade raised, None when it went through; the reads after it are of the database
    as the downgrade left it. ``*_again`` are None when the downgrade failed: nothing was upgraded again.
    """

    db: Path
    rows_at_011: Rows
    schema_at_011: list[tuple[Any, ...]]
    table_at_011: dict[str, Any]
    shape_at_011: dict[str, Any]
    events_at_011: dict[int, int]
    linked_at_011: dict[int, int]
    downgrade_error: Optional[str]
    revision_down: str
    table_down: dict[str, Any]
    shape_down: Optional[dict[str, Any]]
    schema_down: list[tuple[Any, ...]]
    rows_down: Rows
    events_down: dict[int, int]
    linked_down: dict[int, int]
    violations_down: list[tuple[Any, ...]]
    integrity_down: list[tuple[Any, ...]]
    revision_again: Optional[str]
    table_again: Optional[dict[str, Any]]
    shape_again: Optional[dict[str, Any]]
    zones_again: Optional[dict[int, Optional[str]]]
    rows_again: Optional[Rows]


@pytest.fixture(scope="module")
def round_trip(install_at_010: Path, tmp_path_factory: pytest.TempPathFactory) -> RoundTrip | str:
    """The round trip of the module docstring (5), or, while Alembic knows no 011, the reason: each test fails on it."""
    missing = _missing_011()
    if missing is not None:
        return missing
    db = _copy(install_at_010, tmp_path_factory.mktemp("round-trip") / "app.db")
    _migrate(db, "upgrade", REV_011)
    with _foreign_keys_on(db) as conn:
        conn.execute(f"UPDATE {TABLE} SET {COLUMN} = ? WHERE identifier = ?", (LEARNT, LONDON_TICKER))
        conn.commit()
    assert _zones(db)[_id_of(db, LONDON_TICKER)] == LEARNT, "barrier: Vodafone's zone is learnt before the downgrade"
    rows_at_011, schema_at_011, table_at_011, shape_at_011 = _rows(db), _schema(db), _table_info(db, TABLE), _full_shape(db, TABLE)
    events_at_011, linked_at_011 = _provider_events(db), _linked_transactions(db)

    downgrade_error: Optional[str] = None
    try:
        _migrate(db, "downgrade", REV_010)
    except AssertionError:
        raise  # the harness's own setup checks: never a verdict on the migration
    except Exception as error:  # what the downgrade raises is the finding: its tests report it
        if isinstance(error, RuntimeError) and str(error).startswith("safety:"):
            raise
        downgrade_error = f"{type(error).__name__}: {error}"

    again: dict[str, Any] = dict.fromkeys(("revision_again", "table_again", "shape_again", "zones_again", "rows_again"))
    trip = {
        "revision_down": _revision(db),
        "table_down": _table_info(db, TABLE),
        "shape_down": _full_shape(db, TABLE),
        "schema_down": _schema(db),
        "rows_down": _rows(db),
        "events_down": _provider_events(db),
        "linked_down": _linked_transactions(db),
        "violations_down": _violations(db),
        "integrity_down": _integrity(db),
    }
    if downgrade_error is None:
        _migrate(db, "upgrade", REV_011)
        again = {"revision_again": _revision(db), "table_again": _table_info(db, TABLE), "shape_again": _full_shape(db, TABLE), "zones_again": _zones(db), "rows_again": _rows(db)}
    return RoundTrip(
        db=db,
        rows_at_011=rows_at_011,
        schema_at_011=schema_at_011,
        table_at_011=table_at_011,
        shape_at_011=shape_at_011,
        events_at_011=events_at_011,
        linked_at_011=linked_at_011,
        downgrade_error=downgrade_error,
        **trip,
        **again,
    )


def _went_down(trip: RoundTrip) -> None:
    """Barrier of the tests that read the database after the downgrade: it went through."""
    assert trip.downgrade_error is None, f"barrier: the downgrade to {REV_010} failed, so what follows would read a database it left half way: {trip.downgrade_error}"


# =============================================================================
# 1. THE REVISION
# =============================================================================


def test_revision_011_sits_on_010_and_the_chain_keeps_one_head() -> None:
    """MIG011-001 — §1, red until Z-33 (Alembic knows no 011): ``011_provider_exchange_timezone`` exists, in ``011_provider_exchange_timezone.py``, fits ``version_num``, and revises ``010_provider_reported_currency``; one head, not named."""
    print_section(f"MIG011-001: revision {REV_011}")
    scripts = _scripts()
    revisions = {script.revision: script for script in scripts.walk_revisions()}

    assert REV_011 in revisions, f"red until Z-33: revision {REV_011} not found; the chain has {sorted(revisions)}"
    script = revisions[REV_011]
    assert len(script.revision) <= 32, f"{script.revision!r} is {len(script.revision)} characters: alembic_version.version_num is VARCHAR(32)"
    assert script.down_revision == REV_010, f"{REV_011} must revise {REV_010}, revises {script.down_revision!r}"
    assert Path(script.path).name == f"{REV_011}.py", f"the revision id is the file name without .py, found in {Path(script.path).name}"
    heads = scripts.get_heads()
    assert len(heads) == 1, f"the chain must not fork: {len(heads)} heads {heads}"
    print_success(f"{REV_011} revises {REV_010}; one head ({heads[0]})")


# =============================================================================
# 2. A NEW DATABASE AT 011
# =============================================================================


def test_a_new_database_at_head_has_the_column_and_the_rest_of_the_table_as_at_010(fresh_011: Path | str, fresh_010: Path) -> None:
    """MIG011-002 — §2, red until Z-33 (Alembic cannot locate 011): ``exchange_timezone`` is ``VARCHAR(64)``, nullable, without a default, not the key; every other column as at 010, and the keys and their ``ON DELETE``, the unique constraint and the index as at 010, so the new column is in none of them.

    The database is taken to ``011_provider_exchange_timezone`` by name, not to head, though the test's name, its id,
    still says head: «every other column as at 010» is 011's own contract, and a later revision adding a column to this
    table would be counted against 011 (as 011 itself was against 010 in MIG010-002).
    """
    print_section(f"MIG011-002: {TABLE}.{COLUMN} on a new database at {REV_011}")
    db = _ran(fresh_011)
    _assert_includes_011(db)
    columns = _table_info(db, TABLE)

    assert columns.get(COLUMN) == DECLARED, f"{TABLE}.{COLUMN} must be {DECLARED}, is {columns.get(COLUMN)}"
    assert _without_column(columns) == _table_info(fresh_010, TABLE), "every other column must be declared as at 010"
    shape = _full_shape(db, TABLE)
    assert _keys_naming_the_column(shape) == {}, f"{COLUMN} must be in no key, index or constraint: {_keys_naming_the_column(shape)}"
    assert _shape_without_column(shape) == _full_shape(fresh_010, TABLE), "the keys, ON DELETE, unique constraint and index must be as at 010"
    print_success(f"{COLUMN} VARCHAR(64) NULL, nothing else changed")


def test_a_new_assignment_reads_null_even_on_yfinance_and_a_zone_reads_as_written(fresh_011: Path | str, tmp_path: Path) -> None:
    """MIG011-003 — §2 and §4, red until Z-33 (Alembic cannot locate 011): with foreign keys on, a yfinance assignment and a mockprov one written without the column both read NULL — the sentinel is no default: a new assignment's rows are dated by the new rule —, one written with ``Europe/London`` reads it.

    At ``011_provider_exchange_timezone`` by name, as MIG011-002: the rows are written with the columns of 011's table.
    """
    db = _copy(_ran(fresh_011), tmp_path / "app.db")
    _assert_includes_011(db)

    with _foreign_keys_on(db) as conn:
        new_yahoo = _insert_assignment(conn, _insert_asset(conn, "new on yfinance"), "NEW.L")
        new_mock = _insert_assignment(conn, _insert_asset(conn, "new on mockprov"), "NEW-MOCK", provider_code="mockprov")
        learnt = _insert_assignment(conn, _insert_asset(conn, "zone learnt"), "LEARNT.L", **{COLUMN: LEARNT})
        conn.commit()

    assert _zones(db) == {new_yahoo: None, new_mock: None, learnt: LEARNT}


# =============================================================================
# 3. THE MODEL AND THE MIGRATION AGREE ON THE COLUMN
# =============================================================================


def test_the_model_declares_the_column_the_migration_adds(fresh_head: Path, created_by_models: Path) -> None:
    """MIG011-004 — §3, red until Z-33 (the model declares no ``exchange_timezone``; then the head does not include 011): ``create_all`` and ``alembic upgrade head`` declare ``exchange_timezone`` alike — ``VARCHAR(64)``, nullable, no default, in no key, index or constraint — and give the table the same columns. The rest of the table is not compared (a drift older than this lot, as 010 notes).

    At head on purpose, unlike MIG011-002 and 003: the models describe the head, whichever revision it is, so the two
    column sets are compared there; ``exchange_timezone`` itself is held to 011's declaration.
    """
    print_section(f"MIG011-004: {COLUMN}, migration = model")
    modelled = _table_info(created_by_models, TABLE)
    assert COLUMN in modelled, f"red until Z-33: the AssetProviderAssignment model declares no {COLUMN}; create_all builds {sorted(modelled)}"
    _assert_includes_011(fresh_head)
    migrated = _table_info(fresh_head, TABLE)

    assert (migrated.get(COLUMN), modelled.get(COLUMN)) == (DECLARED, DECLARED), f"migration {migrated.get(COLUMN)}, model {modelled.get(COLUMN)}: both must be {DECLARED}"
    assert set(migrated) == set(modelled), f"the migration and the model must give the table the same columns: only in the migration {sorted(set(migrated) - set(modelled))}, only in the model {sorted(set(modelled) - set(migrated))}"
    assert _keys_naming_the_column(_full_shape(created_by_models, TABLE)) == {}, "the model must put the column in no key, index or constraint"
    print_success(f"{COLUMN}: the same declaration both ways")


# =============================================================================
# 4. A POPULATED INSTALL UPGRADED
# =============================================================================


def test_a_populated_install_keeps_every_row_of_every_table(upgraded: Upgrade | str) -> None:
    """MIG011-005 — §4, red until Z-33 (Alembic cannot locate 011): every table of the install at 010, ids included and ``sqlite_sequence`` too, read on the columns it had at 010 — the assignments' ``updated_at`` and ``reported_currency`` too, and the Milan line's shifted rows: the migration marks, it never re-dates —: as it was; no table added or dropped."""
    print_section("MIG011-005: the install at 010, upgraded")
    up = _ran(upgraded)

    assert set(up.rows_after) == set(up.rows_before), f"the upgrade must add or drop no table: added {sorted(set(up.rows_after) - set(up.rows_before))}, dropped {sorted(set(up.rows_before) - set(up.rows_after))}"
    changes = _row_changes(up.rows_before, up.rows_after, set(up.rows_before) - BOOKKEEPING, columns_of=up.rows_before)
    assert not changes, f"the upgrade changed rows: {changes}"
    print_success(f"{len(set(up.rows_before) - BOOKKEEPING)} tables, every row as it was")


def test_every_yfinance_assignment_gets_the_sentinel_and_every_other_reads_null(upgraded: Upgrade | str) -> None:
    """MIG011-006 — §4, red until Z-33 (Alembic cannot locate 011): after the upgrade the column is declared as on a new database; every yfinance assignment (AAPL, Eni, Vodafone) reads ``legacy-utc``, every other (mockprov, borsa_italiana) NULL."""
    up = _ran(upgraded)

    assert up.table_after.get(COLUMN) == DECLARED, f"{TABLE}.{COLUMN} must be {DECLARED}, is {up.table_after.get(COLUMN)}"
    assert _without_column(up.table_after) == up.table_before, "every other column must be declared as at 010"
    assert up.zones_after == _marked(up.codes), f"yfinance assignments must read {SENTINEL!r}, the others NULL; codes {up.codes}, zones {up.zones_after}"


def test_the_upgrade_leaves_every_other_object_and_no_violation(upgraded: Upgrade | str) -> None:
    """MIG011-007 — §4, red until Z-33 (Alembic cannot locate 011): every object of the schema but the table and its indexes keeps its SQL; the table keeps its keys, ``ON DELETE``, unique constraint and index; ``PRAGMA foreign_key_check`` is empty, ``integrity_check`` ok."""
    up = _ran(upgraded)

    assert _beside_the_table(up.schema_after) == _beside_the_table(up.schema_before), "the upgrade must touch no other object of the schema"
    assert _shape_without_column(up.shape_after) == up.shape_before, "the table must keep its keys, ON DELETE, unique constraint and index"
    assert (up.violations, up.integrity) == ([], [("ok",)])


def test_a_populated_install_reaches_the_head(upgraded: Upgrade | str) -> None:
    """MIG011-008 — red until Z-33 (Alembic cannot locate 011): taken on to head, the install is at the head of the chain, whichever revision that is."""
    up = _ran(upgraded)

    _assert_includes_011(up.db)
    assert _revision(up.db) == _scripts().get_current_head()


# =============================================================================
# 5. THE DOWNGRADE, AND BACK
# =============================================================================


def test_the_downgrade_goes_through_with_foreign_keys_on_and_drops_the_column_only(round_trip: RoundTrip | str, install_at_010: Path) -> None:
    """MIG011-009 — §5, red until Z-33 (Alembic cannot locate 011): the downgrade to 010 of the install at 011, the sentinel on yfinance and ``Europe/London`` learnt on Vodafone, goes through with foreign keys on (``FOREIGN KEY constraint failed`` is what a rebuild of the table raises here), and leaves the table declared exactly as at 010: its columns, keys and their ``ON DELETE``, unique constraint and index."""
    print_section("MIG011-009: the downgrade drops the column only")
    trip = _ran(round_trip)

    assert trip.downgrade_error is None, f"the downgrade to {REV_010} must go through with foreign keys on, as production migrates: {trip.downgrade_error}"
    assert trip.revision_down == REV_010, f"the downgrade must leave the database at {REV_010}: {trip.revision_down}"
    assert COLUMN not in trip.table_down, f"the downgrade must drop {COLUMN}"
    assert trip.table_down == _table_info(install_at_010, TABLE), "the table must be declared exactly as at 010"
    assert trip.shape_down == _full_shape(install_at_010, TABLE), "the table must keep the keys, ON DELETE, unique constraint and index it had at 010"
    print_success(f"at {REV_010}; {COLUMN} dropped, the table as at 010")


def test_the_downgrade_keeps_every_row_the_provider_events_and_their_transactions(round_trip: RoundTrip | str) -> None:
    """MIG011-010 — §5, red until Z-33 (Alembic cannot locate 011): after the downgrade every table is there, every row as at 011 read on the columns the table keeps — the events the providers generated and the transactions linked to them above all, which a rebuild of the table deletes with its rows —; every other object of the schema keeps its SQL; no violation, integrity ok."""
    print_section("MIG011-010: the downgrade touches no other row")
    trip = _ran(round_trip)
    _went_down(trip)

    assert trip.events_down == trip.events_at_011, f"the events the providers generated must survive the downgrade: at 011 {trip.events_at_011}, after {trip.events_down}"
    assert trip.linked_down == trip.linked_at_011, f"the transactions linked to them must keep their link: at 011 {trip.linked_at_011}, after {trip.linked_down}"
    assert set(trip.rows_down) == set(trip.rows_at_011), f"the downgrade must add or drop no table: added {sorted(set(trip.rows_down) - set(trip.rows_at_011))}, dropped {sorted(set(trip.rows_at_011) - set(trip.rows_down))}"
    changes = _row_changes(trip.rows_at_011, trip.rows_down, set(trip.rows_down) - BOOKKEEPING, columns_of=trip.rows_down)
    assert not changes, f"the downgrade changed rows it had no reason to touch: {changes}"
    assert _beside_the_table(trip.schema_down) == _beside_the_table(trip.schema_at_011), "the downgrade must touch no other object of the schema"
    assert (trip.violations_down, trip.integrity_down) == ([], [("ok",)])
    print_success(f"{len(set(trip.rows_down) - BOOKKEEPING)} tables, every row as it was at 011")


def test_upgrading_again_brings_the_column_back_and_marks_yfinance_again(round_trip: RoundTrip | str) -> None:
    """MIG011-011 — §5, red until Z-33 (Alembic cannot locate 011): ``upgrade 011`` after the downgrade gives the table it had at 011 — the column declared the same, the keys and the index the same —, every yfinance assignment ``legacy-utc`` again (Vodafone's learnt ``Europe/London`` went with the downgrade), every other NULL, every other row as after the downgrade."""
    trip = _ran(round_trip)
    _went_down(trip)

    assert trip.revision_again == REV_011
    assert (trip.table_again, trip.shape_again) == (trip.table_at_011, trip.shape_at_011), "upgrading again must give the table it had at 011"
    assert trip.zones_again == _marked(_codes_in(trip.rows_down)), f"upgrading again must mark every yfinance assignment again, Vodafone's included, and leave the others NULL: {trip.zones_again}"
    changes = _row_changes(trip.rows_down, trip.rows_again, set(trip.rows_down) - BOOKKEEPING, columns_of=trip.rows_down)
    assert not changes, f"upgrading again changed rows: {changes}"


# =============================================================================
# 6. IDEMPOTENT BOTH WAYS
# =============================================================================


def test_an_upgrade_that_finds_the_column_marks_only_the_null_yfinance_assignments(install_at_010: Path, tmp_path: Path) -> None:
    """MIG011-012 — §6, red until Z-33 (Alembic cannot locate 011): the install at 010 with the column already added as §2 declares it — a run interrupted after its ``ALTER``, the revision still 010 —, Vodafone holding ``Europe/London``, Eni the sentinel, the mockprov assignment ``UTC``, AAPL and borsa_italiana NULL: ``upgrade 011`` goes through, the column declared once, AAPL alone marked (the one yfinance assignment still NULL), every value found kept, every other row of every table as before."""
    print_section("MIG011-012: an upgrade that finds the column")
    _require_011()
    db = _copy(install_at_010, tmp_path / "app.db")
    with _foreign_keys_on(db) as conn:
        conn.execute(ADD_COLUMN)
        conn.execute(f"UPDATE {TABLE} SET {COLUMN} = ? WHERE identifier = ?", (LEARNT, LONDON_TICKER))
        conn.execute(f"UPDATE {TABLE} SET {COLUMN} = ? WHERE identifier = ?", (SENTINEL, MILAN_TICKER))
        conn.execute(f"UPDATE {TABLE} SET {COLUMN} = 'UTC' WHERE provider_code = 'mockprov'")
        conn.commit()
    assert _revision(db) == REV_010 and _table_info(db, TABLE).get(COLUMN) == DECLARED, "setup: the interrupted state"
    rows_before, zones_before = _rows(db), _zones(db)
    aapl = _id_of(db, "AAPL")
    assert zones_before[aapl] is None and sum(zone is None for zone in zones_before.values()) >= 2, f"setup: AAPL and another assignment NULL: {zones_before}"

    _migrate(db, "upgrade", REV_011)

    assert _revision(db) == REV_011
    assert _table_info(db, TABLE).get(COLUMN) == DECLARED and _without_column(_table_info(db, TABLE)) == _table_info(install_at_010, TABLE), "the column must be there once, as §2 declares it, beside the columns of 010"
    assert _zones(db) == zones_before | {aapl: SENTINEL}, f"only the yfinance assignment still NULL must be marked, every value found kept: before {zones_before}, after {_zones(db)}"
    unchanged_columns = {table: ([name for name in columns if name != COLUMN] if table == TABLE else columns, content) for table, (columns, content) in rows_before.items()}
    changes = _row_changes(rows_before, _rows(db), set(rows_before) - BOOKKEEPING, columns_of=unchanged_columns)
    assert not changes, f"the upgrade over its own column changed rows: {changes}"
    print_success("the column found; AAPL marked, every value found kept")


def test_a_downgrade_that_finds_the_column_gone_changes_nothing_else(install_at_010: Path, tmp_path: Path) -> None:
    """MIG011-013 — §6, red until Z-33 (Alembic cannot locate 011): the install at 011 whose column was already dropped — a downgrade interrupted after its ``ALTER``, the revision still 011 —: ``downgrade 010`` goes through, at 010, and changes no object of the schema and no row of any table."""
    print_section("MIG011-013: a downgrade that finds the column gone")
    _require_011()
    db = _copy(install_at_010, tmp_path / "app.db")
    _migrate(db, "upgrade", REV_011)
    with _foreign_keys_on(db) as conn:
        conn.execute(DROP_COLUMN)
        conn.commit()
    assert _revision(db) == REV_011 and COLUMN not in _table_info(db, TABLE), "setup: the interrupted state"
    rows_before, schema_before = _rows(db), _schema(db)

    _migrate(db, "downgrade", REV_010)

    assert _revision(db) == REV_010
    assert _schema(db) == schema_before, "a downgrade that finds the column gone must change no object of the schema"
    changes = _row_changes(rows_before, _rows(db), set(rows_before) - BOOKKEEPING, columns_of=rows_before)
    assert not changes, f"a downgrade that finds the column gone changed rows: {changes}"
    print_success("nothing to drop, nothing changed")


# =============================================================================
# 7. THE RESTORE OF AN OLD BACKUP
# =============================================================================


@pytest.mark.parametrize("revision", [pytest.param(REV_004, id="a-1.2-backup-at-004"), pytest.param(REV_010, id="a-backup-at-010")])
def test_a_restored_backup_upgraded_by_the_staging_marks_yfinance_and_moves_no_row(revision: str, backup_at_004: Path, install_at_010: Path, tmp_path: Path) -> None:
    """MIG011-014 — §7 (N86 §6), red until Z-33 (Alembic cannot locate 011): a backup at 004 — a 1.2 install, its Milan line stored by the old rule — or at 010, copied and taken to head by the restore staging's own step (``staging._upgrade``: ``alembic upgrade head`` on the copy, in a process of its own), is at head; every yfinance assignment reads ``legacy-utc``, every other NULL; the Milan line's closes, dividend and linked DIVIDEND keep their dates: the next refresh re-dates them (``test_asset_source_refresh``, ``test_z33_*``), the migration never does."""
    print_section(f"MIG011-014: a backup at {revision}, restored")
    _require_011()
    db = _copy({REV_004: backup_at_004, REV_010: install_at_010}[revision], tmp_path / "stage" / "data" / "sqlite" / "app.db")
    assert _revision(db) == revision, f"setup: the backup is at {revision}"
    milan_before, codes = _line(db, MILAN_TICKER), _codes(db)

    staging._upgrade(db)

    assert _revision(db) == _scripts().get_current_head(), f"the staging must take the copy to the head: {_revision(db)}"
    _assert_includes_011(db)
    assert _zones(db) == _marked(codes), f"a restored backup must get {SENTINEL!r} on its yfinance assignments and NULL elsewhere; codes {codes}, zones {_zones(db)}"
    assert _line(db, MILAN_TICKER) == milan_before, "the migration must move no row: the refresh re-dates them"
    print_success(f"restored from {revision}: yfinance marked, every row where it was")

"""AUTOINCREMENT on exactly the census tables: migrations, models and ``create_all`` agree (plan 34_accountAndIdReuse §2.2).

Without AUTOINCREMENT SQLite gives the id of a deleted row to the next insert, and the ids of six
tables leave the backend and stay saved: URLs, localStorage, BRIM sidecars and ``broker_<id>``
folders, exports. Decision D1 of the developer fixed that census. A schema comes from three places,
and this file pins the census in each:

1. The census: ``users``, ``brokers``, ``assets``, ``transactions``, ``fx_conversion_routes``,
   ``asset_events``. ``AUTOINCREMENT_TABLES`` names exactly those, once each.
2. ``alembic upgrade head`` on a new database declares AUTOINCREMENT on exactly those tables and on
   no other: the high-volume series and the tables whose ids stay inside the backend keep a plain
   ``INTEGER PRIMARY KEY``.
3. The SQLModel models declare ``sqlite_autoincrement`` on exactly those tables. SQLAlchemy does not
   read AUTOINCREMENT back from a database, so a later batch migration would rebuild a table without
   it unless the model says so.
4. ``SQLModel.metadata.create_all`` writes AUTOINCREMENT into exactly those tables: three service
   suites build their databases that way.

Every database is a temporary file under ``tmp_path``. Alembic runs in a child process, always with
``-x sqlalchemy.url=`` pointing at it (without it ``backend/alembic/env.py`` falls back to the
configured database), and with the configured test data dir pointed at a temporary folder too.

Contract 1 is a guard: the stub's census is already final, so it passes there. Contracts 2-4 are red
until ``001_initial.py`` and the models change.
"""

from __future__ import annotations

import os
import re
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path

from sqlalchemy import create_engine

from backend.app.config import PROJECT_ROOT
from backend.app.db.base import SQLModel
from backend.app.db.post_migration import AUTOINCREMENT_TABLES

# Decision D1 of the developer (plan §0.1), written out here so that the census cannot drift silently.
CENSUS = frozenset({"users", "brokers", "assets", "transactions", "fx_conversion_routes", "asset_events"})
AUTOINCREMENT = re.compile(r"\bAUTOINCREMENT\b", re.IGNORECASE)
CHILD_TIMEOUT = 300


def _alembic_upgrade_head(db: Path, data_dir: Path) -> None:
    """``alembic upgrade head`` on ``db`` in a child process, whose configured data dir is ``data_dir``."""
    assert db.is_absolute(), db
    db.parent.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "LIBREFOLIO_TEST_MODE": "1", "LIBREFOLIO_TEST_DATA_DIR": str(data_dir)}
    completed = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "backend/alembic.ini", "-x", f"sqlalchemy.url=sqlite:///{db}", "upgrade", "head"],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=CHILD_TIMEOUT,
        check=False,
    )
    assert completed.returncode == 0, f"setup: alembic upgrade head failed on {db}\n{completed.stdout[-2000:]}\n{completed.stderr[-4000:]}"


def _tables_with_autoincrement(db: Path) -> set[str]:
    """The tables whose ``CREATE TABLE`` in ``sqlite_master`` says AUTOINCREMENT."""
    assert db.is_file(), f"{db} does not exist"
    with closing(sqlite3.connect(db)) as conn:
        tables = conn.execute("SELECT name, sql FROM sqlite_master WHERE type = 'table'").fetchall()
    return {name for name, sql in tables if sql and AUTOINCREMENT.search(sql)}


def _differences(found: set[str]) -> str:
    return f"missing: {sorted(CENSUS - found)}, unexpected: {sorted(found - CENSUS)}"


def test_the_census_is_the_one_the_developer_approved() -> None:
    """Contract 1 — guard: ``AUTOINCREMENT_TABLES`` names the six tables of decision D1, each once.

    Green on the stub, whose census is already final. It fails if the census drifts, which would
    silently move every other check with it.
    """
    assert sorted(AUTOINCREMENT_TABLES) == sorted(CENSUS)


def test_a_new_database_has_autoincrement_on_exactly_the_census_tables(tmp_path: Path) -> None:
    """Contract 2: after ``alembic upgrade head`` on a new database, AUTOINCREMENT is on the six census tables and on no other.

    Read from ``sqlite_master``: what SQLite will actually do, whatever the migrations meant.
    """
    data_dir = tmp_path / "data"
    db = data_dir / "sqlite" / "app.db"

    _alembic_upgrade_head(db, data_dir)

    found = _tables_with_autoincrement(db)
    assert found == CENSUS, _differences(found)


def test_the_models_declare_sqlite_autoincrement_on_exactly_the_census_tables() -> None:
    """Contract 3: in ``SQLModel.metadata``, ``sqlite_autoincrement`` is on for the six census tables and for no other."""
    found = {name for name, table in SQLModel.metadata.tables.items() if table.dialect_options["sqlite"]["autoincrement"]}

    assert found == CENSUS, _differences(found)


def test_create_all_gives_autoincrement_to_exactly_the_census_tables(tmp_path: Path) -> None:
    """Contract 4: ``SQLModel.metadata.create_all`` on a new database file writes AUTOINCREMENT into the six census tables and into no other."""
    db = tmp_path / "create_all.db"
    engine = create_engine(f"sqlite:///{db}")
    try:
        SQLModel.metadata.create_all(engine)
    finally:
        engine.dispose()

    found = _tables_with_autoincrement(db)
    assert found == CENSUS, _differences(found)

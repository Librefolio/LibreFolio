"""B6-1 (B-56): ``dev.py db check --integrity`` — the restore's checks, on demand, on the live database file.

``backend/app/services/platform/db_integrity_check.py`` runs on a database file, read only, the checks the restore
runs on a backup's copy and reuses them (``describe_database``, the UTF-8 scan, the revision plan of ``staging``):

1. A sound database at the app's head: no problem, exit 0.
2. A reference to a row that is gone: counted, a problem, exit 1.
3. A text that is not UTF-8: the table and the rowid, never the content; a problem, exit 1.
4. A revision this LibreFolio does not know, or none recorded: named, a problem, exit 1. An older one is not a problem
   (the start upgrades it).
5. A file that is no database, or missing: exit 2, nothing written.
6. The file is the same, byte for byte, after the check.
7. ``dev.py db check --integrity`` hands the named file to that module; without the flag ``db check`` is unchanged.

Every database is a private file under ``tmp_path``; the module is run in-process.
"""

from __future__ import annotations

import argparse
import hashlib
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

import dev
from backend.app.services.platform import db_integrity_check as check
from backend.app.services.platform.instance_backup.staging import ALEMBIC_INI

SECRET_TEXT = "café-secret"


def _head() -> str:
    return ScriptDirectory.from_config(Config(str(ALEMBIC_INI))).get_current_head()


@pytest.fixture
def database(tmp_path: Path) -> Path:
    """A sound database: a parent and a child table, at the app's head."""
    path = tmp_path / "app.db"
    with closing(sqlite3.connect(path)) as conn:
        conn.execute("CREATE TABLE parent (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("CREATE TABLE child (id INTEGER PRIMARY KEY, parent_id INTEGER REFERENCES parent(id), note TEXT)")
        conn.execute("CREATE TABLE alembic_version (version_num TEXT NOT NULL)")
        conn.execute("INSERT INTO alembic_version VALUES (?)", (_head(),))
        conn.execute("INSERT INTO parent VALUES (1, 'a')")
        conn.execute("INSERT INTO child VALUES (1, 1, 'ok')")
        conn.commit()
    return path


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, sql: str, *args) -> None:
    with closing(sqlite3.connect(path)) as conn:
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute(sql, args)
        conn.commit()


def test_a_sound_database_has_no_problem(database):
    report = check.check_database(database)

    assert report.problems() == []
    assert check.main(["--db-file", str(database)]) == 0


def test_a_reference_to_a_row_that_is_gone_is_a_problem(database):
    _write(database, "INSERT INTO child VALUES (2, 99, 'orphan')")

    report = check.check_database(database)

    assert report.foreign_key_violations == 1
    assert any("foreign" in problem.lower() for problem in report.problems())
    assert check.main(["--db-file", str(database)]) == 1


def test_a_text_that_is_not_utf8_is_named_by_table_and_rowid_never_by_content(database, capsys):
    _write(database, "INSERT INTO child VALUES (7, 1, CAST(X'FFFE' AS TEXT))")
    _write(database, "INSERT INTO parent VALUES (5, ?)", SECRET_TEXT)

    report = check.check_database(database)

    assert report.undecodable == {"child": [7]}
    assert check.main(["--db-file", str(database)]) == 1
    out = capsys.readouterr()
    assert "child" in out.out and "7" in out.out
    assert SECRET_TEXT not in out.out + out.err


def test_an_unknown_revision_is_a_problem_and_an_older_one_is_not(database):
    _write(database, "UPDATE alembic_version SET version_num = 'zzz_unknown'")
    unknown = check.check_database(database)
    assert unknown.revision_status == "unknown" and unknown.problems()

    with closing(sqlite3.connect(database)) as conn:
        conn.execute("DELETE FROM alembic_version")
        conn.commit()
    missing = check.check_database(database)
    assert missing.revision_status == "missing" and missing.problems()


def test_the_head_revision_is_reported_as_the_head(database):
    assert check.check_database(database).revision_status == "head"


def test_a_file_that_is_no_database_or_missing_exits_2(tmp_path):
    junk = tmp_path / "junk.db"
    junk.write_bytes(b"this is not a sqlite file" * 100)

    assert check.main(["--db-file", str(junk)]) == 2
    assert check.main(["--db-file", str(tmp_path / "missing.db")]) == 2


def test_the_check_leaves_the_file_byte_for_byte_as_it_was(database):
    _write(database, "INSERT INTO child VALUES (2, 99, 'orphan')")
    before = _sha(database)

    check.check_database(database)
    check.main(["--db-file", str(database)])

    assert _sha(database) == before
    assert sorted(p.name for p in database.parent.iterdir()) == ["app.db"]


def test_db_check_with_integrity_runs_the_module_on_the_named_file(monkeypatch, database):
    commands: list[list[str]] = []
    monkeypatch.setattr(dev, "run_pipenv", lambda cmd, env=None: commands.append((cmd, env)) or 0)

    assert dev.cmd_db_check(argparse.Namespace(path=str(database), integrity=True)) == 0

    ((cmd, _env),) = commands
    assert "backend.app.services.platform.db_integrity_check" in cmd
    assert str(database) in cmd


def test_db_check_without_the_flag_still_checks_the_constraints(monkeypatch, database):
    commands: list[list[str]] = []
    monkeypatch.setattr(dev, "run_pipenv", lambda cmd, env=None: commands.append((cmd, env)) or 0)

    assert dev.cmd_db_check(argparse.Namespace(path=str(database), integrity=False)) == 0

    ((cmd, _env),) = commands
    assert "backend.alembic.check_constraints_hook" in cmd

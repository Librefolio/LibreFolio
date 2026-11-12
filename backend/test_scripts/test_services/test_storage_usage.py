"""What the instance's data directory weighs (lot FB-29, contract ``B6r-fb29-interface`` §3): ``services/platform/storage_usage.py``.

The storage bar of the Files page shows the parts of the data directory (the database, the uploads, the broker reports,
the kept backups, the rest) against the volume or against a limit. The numbers come from here; the API route
(``test_backup_storage_api.py``) and the settings (``test_storage_limit_settings.py``) have suites of their own.

(a) ``folder_bytes(path)``: the sum of the bytes of the *files* below ``path`` (``lstat``; a directory counts for nothing
    by itself, so the figure does not depend on the file system's directory size), recursive. A link is never followed:
    it counts for itself (its own ``lstat`` size), not for its target, a file or a folder. A missing folder is 0; a
    path that is itself a link is 0; an entry that vanishes while the folder is walked, or a folder it cannot read, is 0
    and the rest still counts. It never raises.
(b) ``measure_storage(data_dir, limit_mb=None, limit_locked=False)``: a ``StorageUsage`` (frozen dataclass) whose five
    parts, ``database_bytes`` (``sqlite/``), ``uploads_bytes`` (``custom-uploads/``), ``broker_reports_bytes``
    (``broker_reports/``), ``backups_bytes`` (``backups/`` whole, ``.jobs/`` included) and ``other_bytes`` (every other
    entry of the data directory, folders of the same name deeper down included), add up to ``data_bytes``, which is also
    ``folder_bytes(data_dir)``. The volume comes from ``shutil.disk_usage(data_dir)``; when that raises, the three
    ``volume_*`` fields are ``None``. ``limit_mb`` and ``limit_locked`` are handed through. A missing data directory is a
    measurement of zero, not an exception.
(c) ``read_limit()`` (synchronous): ``(limit_mb, locked)``. ``LIBREFOLIO_STORAGE_LIMIT_MB`` set and valid decides, without
    the database: ``(value, True)``, ``(None, True)`` for 0. Set but invalid (and a blank one is not set): ignored, the row
    ``storage_limit_mb`` is read through the synchronous engine (``db_session.get_sync_engine()``) and ``locked`` is False.
    No variable: the row. 0, a value that is no whole number, a missing row, a missing table, an engine that fails:
    ``(None, False)``. It never raises.

How: data directories under ``tmp_path``; ``shutil.disk_usage`` replaced; for (c) a private SQLite file with the whole ORM
schema read through a synchronous engine put in place of the process's (``get_sync_engine``). Isolation: pure. No lane
database, no server, no network.
"""

from __future__ import annotations

import dataclasses
import importlib
import os
import shutil
from collections import namedtuple
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from backend.app.db.base import SQLModel  # imports every model: SQLModel.metadata holds the whole schema
from backend.app.db.models import GlobalSetting, User
from backend.test_scripts.test_utils import print_section, print_success

MODULE = "backend.app.services.platform.storage_usage"
VARIABLE = "LIBREFOLIO_STORAGE_LIMIT_MB"
KEY = "storage_limit_mb"
FIELDS = [
    "database_bytes",
    "uploads_bytes",
    "broker_reports_bytes",
    "backups_bytes",
    "other_bytes",
    "data_bytes",
    "volume_total_bytes",
    "volume_used_bytes",
    "volume_free_bytes",
    "limit_mb",
    "limit_locked",
    "restore_bytes",
]
PARTS = ["database_bytes", "uploads_bytes", "broker_reports_bytes", "backups_bytes", "other_bytes", "restore_bytes"]


def service():
    """The module under test; absent, every test that needs it is red with this reason."""
    try:
        return importlib.import_module(MODULE)
    except ModuleNotFoundError as exc:
        if exc.name != MODULE:
            raise
        pytest.fail(f"[new] {MODULE} does not exist yet: lot FB-29 brings it (§3)", pytrace=False)


@pytest.fixture(autouse=True)
def _no_inherited_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """A test sees the variable it sets itself, none otherwise."""
    monkeypatch.delenv(VARIABLE, raising=False)


def put(root: Path, relative: str, size: int) -> Path:
    """A file of ``size`` bytes at ``root / relative``, folders made."""
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)
    return path


def a_data_dir(root: Path) -> tuple[Path, dict[str, int]]:
    """A data directory with known weights; the expected parts as a dict (``other`` holds a same-named folder deeper down
    and a loose file at the top)."""
    put(root, "sqlite/app.db", 100)
    put(root, "sqlite/app.db-wal", 50)
    put(root, "custom-uploads/a/b.bin", 300)
    put(root, "broker_reports/r.csv", 70)
    put(root, "backups/.jobs/job1/state.json", 10)
    put(root, "backups/librefolio-backup-20261001-000000-ui-0123abcd/archive.zip", 1000)
    put(root, "logs/app.log", 20)
    put(root, ".restore/stage/x", 30)
    put(root, "scenario_catalog/s.json", 40)
    put(root, ".restore/custom-uploads/deeper.bin", 7)  # a folder of the same name is not the uploads
    put(root, "top.txt", 5)
    return root, {
        "database_bytes": 150,
        "uploads_bytes": 300,
        "broker_reports_bytes": 70,
        "backups_bytes": 1010,
        "other_bytes": 20 + 40 + 5,
        # C9-7: a restore under way is a part of its own, a folder of the same name as another part inside it included.
        "restore_bytes": 30 + 7,
    }


# =============================================================================
# (a) folder_bytes
# =============================================================================


def test_folder_bytes_sums_the_files_of_the_tree(tmp_path):
    folder = tmp_path / "tree"
    put(folder, "one.bin", 10)
    put(folder, "a/two.bin", 200)
    put(folder, "a/b/c/three.bin", 3000)
    (folder / "empty").mkdir()
    assert service().folder_bytes(folder) == 3210, "the files of every depth, an empty folder counts for nothing"


def test_folder_bytes_of_a_missing_folder_or_a_file_is_not_an_error(tmp_path):
    assert service().folder_bytes(tmp_path / "missing") == 0, "a missing folder weighs 0"
    assert service().folder_bytes(Path(tmp_path / "nowhere" / "deeper")) == 0
    assert type(service().folder_bytes(tmp_path)) is int


def test_a_link_counts_for_itself_and_is_never_followed(tmp_path):
    """(a) A link to a big file and one to a big folder, both outside the tree: each weighs its own ``lstat`` size."""
    outside = tmp_path / "outside"
    big = put(outside, "big.bin", 1_000_000)
    put(outside, "folder/inside.bin", 500_000)
    tree = tmp_path / "tree"
    put(tree, "real.bin", 10)
    file_link = tree / "link-to-file"
    folder_link = tree / "link-to-folder"
    dangling = tree / "dangling"
    file_link.symlink_to(big)
    folder_link.symlink_to(outside / "folder", target_is_directory=True)
    dangling.symlink_to(tmp_path / "gone.bin")
    expected = 10 + sum(os.lstat(link).st_size for link in (file_link, folder_link, dangling))

    assert service().folder_bytes(tree) == expected, "own size for each link, the targets not counted"
    assert expected < 1000, "premise: a link weighs a path's length"


def test_a_data_folder_that_is_a_link_weighs_nothing(tmp_path):
    real = tmp_path / "real"
    put(real, "a.bin", 100)
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    assert service().folder_bytes(real) == 100, "premise"
    assert service().folder_bytes(link) == 0, "a link is never followed, even when it is the folder asked"


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads every folder: nothing is unreadable")
def test_a_folder_that_cannot_be_read_counts_zero_and_the_rest_still_counts(tmp_path):
    tree = tmp_path / "tree"
    put(tree, "ok.bin", 100)
    put(tree, "closed/hidden.bin", 500)
    put(tree, "open/seen.bin", 20)
    (tree / "closed").chmod(0)
    try:
        assert service().folder_bytes(tree) == 120, "the unreadable folder counts 0, the others count"
    finally:
        (tree / "closed").chmod(0o700)


def test_an_entry_that_vanishes_during_the_walk_counts_zero_and_nothing_raises(tmp_path, monkeypatch):
    """(a) A file is removed between the listing of its folder and the reading of its size (a backup deleted while the
    bar measures). Best effort on the seam: when the walk lists with ``os.scandir`` the removal lands between the two steps
    and the answer excludes the file; with any other listing the file is still there and counts. Either way: no exception
    and no other figure."""
    tree = tmp_path / "tree"
    put(tree, "stay.bin", 100)
    victim = put(tree, "sub/vanishing.bin", 4000)
    put(tree, "sub/stay2.bin", 11)
    real_scandir = os.scandir
    fired: list[bool] = []

    class Listing:
        def __init__(self, entries):
            self.entries = iter(entries)

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def __iter__(self):
            return self

        def __next__(self):
            return next(self.entries)

        def close(self):
            return None

    def scandir(path="."):
        with real_scandir(path) as listing:
            entries = list(listing)
        # An open directory (an int) is how ``shutil.rmtree`` scans on a disk temp folder: only a path can be the victim's folder
        if not isinstance(path, int) and Path(path) == victim.parent and victim.exists():
            victim.unlink()
            fired.append(True)
        return Listing(entries)

    monkeypatch.setattr(os, "scandir", scandir)
    result = service().folder_bytes(tree)

    assert result == (111 if fired else 4111), f"the vanished file counts 0 (fired={bool(fired)}): {result}"


# =============================================================================
# (b) measure_storage
# =============================================================================


def test_the_result_is_a_frozen_dataclass_with_the_eleven_fields(tmp_path):
    usage = service().measure_storage(a_data_dir(tmp_path / "data")[0])
    assert dataclasses.is_dataclass(usage) and type(usage).__name__ == "StorageUsage", f"a StorageUsage: {usage!r}"
    assert [field.name for field in dataclasses.fields(usage)] == FIELDS, "the fields of the contract, in order"
    with pytest.raises(dataclasses.FrozenInstanceError):
        usage.data_bytes = 1  # type: ignore[misc]
    for name in PARTS + ["data_bytes"]:
        assert type(getattr(usage, name)) is int, f"{name} is an int"


def test_the_five_parts_add_up_to_the_data_directory(tmp_path):
    print_section("measure_storage: the five parts")
    data, expected = a_data_dir(tmp_path / "data")
    usage = service().measure_storage(data)
    assert {name: getattr(usage, name) for name in PARTS} == expected, "each part as planted"
    assert usage.data_bytes == sum(expected.values()) == 1_632, "the whole is the sum of the five"
    assert usage.data_bytes == service().folder_bytes(data), "and the whole folder walked"
    assert usage.data_bytes == sum(getattr(usage, name) for name in PARTS), "parts are mutually exclusive"
    print_success(f"{usage.data_bytes} bytes in five parts")


def test_a_data_directory_with_only_some_of_the_folders(tmp_path):
    data = tmp_path / "data"
    put(data, "custom-uploads/a.bin", 42)
    usage = service().measure_storage(data)
    assert (usage.uploads_bytes, usage.database_bytes, usage.broker_reports_bytes, usage.backups_bytes, usage.other_bytes, usage.data_bytes) == (42, 0, 0, 0, 0, 42)


def test_links_in_the_data_directory_are_not_followed(tmp_path):
    """(b) A link to a big file inside each part and a link at the top: each weighs its own size, in the part it sits in."""
    big = put(tmp_path / "outside", "big.bin", 5_000_000)
    data, expected = a_data_dir(tmp_path / "data")
    links = {
        "uploads_bytes": data / "custom-uploads" / "link.bin",
        "backups_bytes": data / "backups" / "link.bin",
        "other_bytes": data / "link-at-the-top",
    }
    for link in links.values():
        link.symlink_to(big)
    usage = service().measure_storage(data)
    for name, link in links.items():
        assert getattr(usage, name) == expected[name] + os.lstat(link).st_size, f"{name}: the link counts for itself"
    assert usage.data_bytes < 10_000, "the 5 MB target is not counted anywhere"
    assert usage.data_bytes == sum(getattr(usage, name) for name in PARTS)


def test_the_volume_comes_from_disk_usage_of_the_data_directory(tmp_path, monkeypatch):
    Usage = namedtuple("Usage", "total used free")  # noqa: PYI024 — the shape of shutil's own answer
    asked: list[object] = []

    def disk_usage(path):
        asked.append(path)
        return Usage(1_000_000, 600_000, 400_000)

    monkeypatch.setattr(shutil, "disk_usage", disk_usage)
    monkeypatch.setattr(service(), "disk_usage", disk_usage, raising=False)  # were the name bound in the module
    data = a_data_dir(tmp_path / "data")[0]
    usage = service().measure_storage(data)
    assert (usage.volume_total_bytes, usage.volume_used_bytes, usage.volume_free_bytes) == (1_000_000, 600_000, 400_000)
    assert asked and Path(asked[0]).resolve() == data.resolve(), f"asked for the data directory's volume: {asked}"


@pytest.mark.parametrize("error", [OSError("no such volume"), PermissionError("denied"), RuntimeError("anything")])
def test_a_volume_that_cannot_be_read_gives_three_nones_and_the_parts_stay(tmp_path, monkeypatch, error):
    def disk_usage(_path):
        raise error

    monkeypatch.setattr(shutil, "disk_usage", disk_usage)
    monkeypatch.setattr(service(), "disk_usage", disk_usage, raising=False)
    data, expected = a_data_dir(tmp_path / "data")
    usage = service().measure_storage(data)
    assert (usage.volume_total_bytes, usage.volume_used_bytes, usage.volume_free_bytes) == (None, None, None)
    assert usage.data_bytes == sum(expected.values()), "the parts are measured all the same"


def test_a_missing_data_directory_is_a_measurement_of_zero(tmp_path):
    usage = service().measure_storage(tmp_path / "never-made")
    assert (*(getattr(usage, name) for name in PARTS), usage.data_bytes) == (0,) * (len(PARTS) + 1)
    assert usage.limit_mb is None and usage.limit_locked is False


def test_the_limit_is_handed_through(tmp_path):
    data = a_data_dir(tmp_path / "data")[0]
    default = service().measure_storage(data)
    assert (default.limit_mb, default.limit_locked) == (None, False), "no limit, not locked, by default"
    given = service().measure_storage(data, limit_mb=250, limit_locked=True)
    assert (given.limit_mb, given.limit_locked) == (250, True)
    assert given.data_bytes == default.data_bytes, "the limit changes no figure"


# =============================================================================
# (c) read_limit
# =============================================================================


def use_sync_engine(monkeypatch: pytest.MonkeyPatch, make) -> None:
    """``get_sync_engine`` answers ``make()`` wherever the reader may reach it: the session module, the package that
    re-exports it and the service's own module, were it to bind the name."""
    module = service()
    for name in ("backend.app.db.session", "backend.app.db"):
        monkeypatch.setattr(importlib.import_module(name), "get_sync_engine", make)
    monkeypatch.setattr(module, "get_sync_engine", make, raising=False)


def a_database(tmp_path: Path, value: str | None, *, written_by: int | None = None) -> Path:
    """A private SQLite file with the ORM schema and, when ``value`` is not None, the row ``storage_limit_mb``."""
    path = tmp_path / "limit.db"
    engine = create_engine(f"sqlite:///{path}", poolclass=NullPool)
    try:
        SQLModel.metadata.create_all(engine)
        if value is not None:
            with Session(engine) as session:
                if written_by is not None:
                    session.add(User(id=written_by, username=f"fb29_admin_{written_by}", email=f"fb29_admin_{written_by}@example.com", hashed_password="marker-hash-not-bcrypt", is_active=True))
                    session.flush()
                session.add(GlobalSetting(key=KEY, value=value, value_type="int", description="", updated_by_user_id=written_by))
                session.commit()
    finally:
        engine.dispose()
    return path


def read_with(monkeypatch: pytest.MonkeyPatch, path: Path) -> tuple[int | None, bool]:
    engine = create_engine(f"sqlite:///{path}", poolclass=NullPool)
    try:
        use_sync_engine(monkeypatch, lambda: engine)
        return service().read_limit()
    finally:
        engine.dispose()


def failing_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    def failing():
        raise RuntimeError("the database must not be asked")

    use_sync_engine(monkeypatch, failing)


@pytest.mark.parametrize(("text", "expected"), [("250", (250, True)), (" 250 ", (250, True)), ("1", (1, True)), ("0", (None, True)), ("10485760", (10485760, True))])
def test_the_variable_decides_without_the_database(monkeypatch, text, expected):
    """(c) Valid: ``(value, True)``, 0 is ``(None, True)``; the database is not even asked (the engine of the test raises)."""
    monkeypatch.setenv(VARIABLE, text)
    failing_engine(monkeypatch)
    assert service().read_limit() == expected


def test_the_variable_wins_over_the_row_an_administrator_saved(tmp_path, monkeypatch):
    path = a_database(tmp_path, "100", written_by=1)
    monkeypatch.setenv(VARIABLE, "250")
    assert read_with(monkeypatch, path) == (250, True)


@pytest.mark.parametrize("text", ["abc", "-1", "1.5", "１２", "250MB", "1e3"])
def test_an_invalid_variable_is_ignored_and_the_row_is_read_unlocked(tmp_path, monkeypatch, text):
    """(c) Set but unusable: it stands for nothing here (the startup audit stops at it); the row speaks, ``locked`` False."""
    path = a_database(tmp_path, "300")
    monkeypatch.setenv(VARIABLE, text)
    assert read_with(monkeypatch, path) == (300, False)


def test_a_blank_variable_is_not_set(tmp_path, monkeypatch):
    path = a_database(tmp_path, "300")
    monkeypatch.setenv(VARIABLE, "   ")
    assert read_with(monkeypatch, path) == (300, False)


@pytest.mark.parametrize(("value", "expected"), [("300", (300, False)), ("0", (None, False)), ("1", (1, False)), ("10485760", (10485760, False))])
def test_without_the_variable_the_row_decides(tmp_path, monkeypatch, value, expected):
    assert read_with(monkeypatch, a_database(tmp_path, value)) == expected


def test_the_row_an_administrator_wrote_is_read_like_any_other(tmp_path, monkeypatch):
    assert read_with(monkeypatch, a_database(tmp_path, "75", written_by=3)) == (75, False)


@pytest.mark.parametrize("junk", ["abc", "", "1.5", "1e3", " "])
def test_a_row_that_is_no_whole_number_means_no_limit(tmp_path, monkeypatch, junk):
    assert read_with(monkeypatch, a_database(tmp_path, junk)) == (None, False)


def test_a_missing_row_a_missing_table_or_a_failing_engine_mean_no_limit(tmp_path, monkeypatch):
    """(c) Never an exception: a database without the row, an empty file, an engine that cannot be made."""
    print_section("read_limit: nothing to read")
    assert read_with(monkeypatch, a_database(tmp_path, None)) == (None, False), "table without the row"
    empty = tmp_path / "empty.db"
    empty.write_bytes(b"")
    assert read_with(monkeypatch, empty) == (None, False), "a database without the table"
    failing_engine(monkeypatch)
    assert service().read_limit() == (None, False), "an engine that cannot be made"
    print_success("(None, False) each time")


def test_a_failing_engine_does_not_unlock_an_invalid_variable(monkeypatch):
    monkeypatch.setenv(VARIABLE, "abc")
    failing_engine(monkeypatch)
    assert service().read_limit() == (None, False)

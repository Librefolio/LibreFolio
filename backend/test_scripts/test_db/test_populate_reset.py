"""
``populate --force`` must leave no BRIM file of the database it deletes (plan 33_e2eImportInfra §2.1).

Every E2E invocation runs ``populate_mock_data --force --with-reports``. ``--force`` deletes the
database file but left ``broker_reports/{uploaded,parsed,failed}/broker_<id>/`` on disk. Broker ids
are reused (no AUTOINCREMENT), so the brokers of the next invocation inherited the files of brokers
that no longer existed, and ``--with-reports`` stacked one more copy of every sample per run.

``reset_broker_reports(data_dir, db_path)`` is the cure. The contract pinned here:

1. When ``db_path`` resolves inside ``data_dir``, the three status folders are emptied completely,
   files and ``broker_<id>/`` subfolders alike, and exist, empty, afterwards.
2. Nothing else is touched: not ``broker_reports/.locks``, not ``custom-uploads`` (``--clean``'s
   job), not the database, not the rest of the data dir, nothing outside it.
3. When ``db_path`` resolves outside ``data_dir``, nothing at all is touched and the result is 0.
4. The result is the number of files removed, counted recursively; folders do not count.
5. Missing ``broker_reports`` or status folders are created: ``uploaded``, ``parsed``, ``failed``.
6. A second call returns 0 and changes nothing.
7. A symlink inside a status folder is removed as a link; its target is never followed.

Every directory and file lives under ``tmp_path``. The configured test data dir — what
``get_data_dir()`` returns — is pointed at a sandbox for each test (autouse fixture), so even an
implementation that ignored its ``data_dir`` argument could only ever empty a canary, never the
lane's real ``broker_reports``.

A test asserting that something was *kept* first proves the same call *did* reset the status
folders — the barrier. A function that does nothing keeps everything, and must not pass for it.
Only the contract-3 tests pass against a function that does nothing: they are guards, and say so.
The warning printed for a DB outside the data dir is never asserted: its text is not a contract.
"""

from __future__ import annotations

import ast
import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

# Setup test database BEFORE importing app modules
from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

# populate_mock_data configures the test database again when imported and builds a lazy NullPool
# engine: the import opens no connection. Nothing below hands it a path outside tmp_path.
from backend.app.db.models import Asset, AssetType, Broker
from backend.app.services.assets.profile.catalogue import normalize_value
from backend.test_scripts.test_db import populate_mock_data
from backend.test_scripts.test_db.populate_mock_data import reset_broker_reports

PROJECT_ROOT = Path(__file__).resolve().parents[3]
STATUS_FOLDERS = ("uploaded", "parsed", "failed")
EMPTIED = {"uploaded": [], "parsed": [], "failed": []}
SQLITE_BYTES = b"SQLite format 3\x00" + bytes(84)
CSV_BYTES = b"date,amount\n2025-01-02,100\n"
NO_RESET = "barrier: the status folders were not emptied, so the reset did not run and the assertion below would pass for a function that does nothing"

Snapshot = dict[str, tuple[str, bytes | str | None]]


# =============================================================================
# HELPERS
# =============================================================================


def _plant(path: Path, content: bytes = CSV_BYTES) -> Path:
    """Write ``content`` at ``path``, creating its folders."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def _plant_report(folder: Path, n: int) -> None:
    """One stored report as the BRIM storage writes it: ``<uuid>.csv`` plus its ``<uuid>.json`` sidecar."""
    file_id = str(uuid.UUID(int=n))
    _plant(folder / f"{file_id}.csv")
    _plant(folder / f"{file_id}.json", json.dumps({"file_id": file_id}).encode())


def _db_path(data_dir: Path) -> Path:
    return data_dir / "sqlite" / "app.db"


def _build_data_dir(data_dir: Path) -> Path:
    """A test data dir as the app and a few ``populate --with-reports`` runs leave it."""
    _plant(_db_path(data_dir), SQLITE_BYTES)
    _plant(data_dir / "sqlite" / "app.db-wal", b"wal")
    _plant(data_dir / "sqlite" / "app.db-shm", b"shm")
    _plant(data_dir / "custom-uploads" / f"{uuid.UUID(int=90)}.png", b"\x89PNG\r\n\x1a\n")
    _plant(data_dir / "custom-uploads" / f"{uuid.UUID(int=90)}.json", b"{}")
    _plant(data_dir / "logs" / "librefolio.log", b"started\n")
    _plant(data_dir / "scheduler_state.json", b"{}")
    reports = data_dir / "broker_reports"
    _plant(reports / ".locks" / "broker_1.lock", b"")
    _plant(reports / ".locks" / "broker_2.lock", b"")
    _plant_report(reports / "uploaded" / "broker_1", 1)
    _plant_report(reports / "uploaded", 2)  # an upload with no broker sits at the folder root
    _plant_report(reports / "parsed" / "broker_2", 3)
    _plant_report(reports / "failed" / "broker_2", 4)
    # Every upload creates its broker folder under all three statuses: most of them stay empty.
    for empty_broker_folder in ("uploaded/broker_2", "parsed/broker_1", "failed/broker_1"):
        (reports / empty_broker_folder).mkdir()
    return data_dir


def _status_folders(data_dir: Path) -> dict[str, list[str] | None]:
    """The entries of each status folder, by name; ``None`` for a folder that does not exist."""
    contents: dict[str, list[str] | None] = {}
    for status in STATUS_FOLDERS:
        folder = data_dir / "broker_reports" / status
        contents[status] = sorted(entry.name for entry in folder.iterdir()) if folder.is_dir() else None
    return contents


def _describe(path: Path) -> tuple[str, bytes | str | None]:
    """One entry, read without following links: its kind, and its bytes or its link target."""
    if path.is_symlink():
        return ("link", str(path.readlink()))
    if path.is_dir():
        return ("dir", None)
    if path.is_file():
        return ("file", path.read_bytes())
    return ("missing", None)


def _snapshot(root: Path, *, skip: tuple[Path, ...] = ()) -> Snapshot:
    """``root`` and every entry below it, links never followed, the ``skip`` subtrees left out.

    Two equal snapshots prove that nothing there was created, removed, rewritten or re-pointed.
    """
    snapshot: Snapshot = {".": _describe(root)}
    pending = [root] if snapshot["."][0] == "dir" else []
    while pending:
        folder = pending.pop()
        for entry in folder.iterdir():
            if entry in skip:
                continue
            kind, content = _describe(entry)
            snapshot[entry.relative_to(root).as_posix()] = (kind, content)
            if kind == "dir":
                pending.append(entry)
    return snapshot


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def configured_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the configured test data dir (``get_data_dir()``) at a sandbox holding a canary report.

    ``reset_broker_reports`` works on the ``data_dir`` it is given, so no test here needs the
    configured one. Redirecting it means that an implementation reaching for ``get_data_dir()``
    anyway empties this sandbox and not the lane's real ``broker_reports`` — and the canary says so.
    """
    sandbox = tmp_path / "configured-lane"
    _plant_report(sandbox / "broker_reports" / "uploaded" / "broker_1", 99)
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(sandbox))
    return sandbox


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    """The data dir under reset, laid out as the app leaves it; its database is ``sqlite/app.db``."""
    return _build_data_dir(tmp_path / "data")


# =============================================================================
# 1. DB INSIDE THE DATA DIR: THE THREE STATUS FOLDERS ARE EMPTIED
# =============================================================================


def test_empties_the_three_status_folders(data_dir: Path) -> None:
    """Contract 1: ``uploaded``, ``parsed`` and ``failed`` lose everything and stay, empty.

    Everything means reports at the folder root, ``broker_<id>/`` folders with their ``<uuid>.csv``
    and ``<uuid>.json``, and the broker folders that were already empty.
    """
    reset_broker_reports(data_dir=data_dir, db_path=_db_path(data_dir))

    assert _status_folders(data_dir) == EMPTIED


def test_a_db_path_through_dot_dot_that_stays_inside_counts_as_inside(data_dir: Path) -> None:
    """Contract 1: ``data_dir/sqlite/../sqlite/app.db`` resolves inside the data dir, so the reset runs.

    A ``..`` is resolved, not refused.
    """
    reset_broker_reports(data_dir=data_dir, db_path=data_dir / "sqlite" / ".." / "sqlite" / "app.db")

    assert _status_folders(data_dir) == EMPTIED


def test_a_data_dir_given_through_a_symlink_is_compared_resolved(data_dir: Path, tmp_path: Path) -> None:
    """Contract 1: a data dir given through a symlink, with the DB at its real path, is inside once both are resolved.

    On macOS ``/tmp`` is itself a link to ``/private/tmp``: two spellings of one lane path are an
    ordinary sight, and comparing them unresolved would silently skip the reset.
    """
    link = tmp_path / "data-link"
    link.symlink_to(data_dir, target_is_directory=True)

    reset_broker_reports(data_dir=link, db_path=_db_path(data_dir))

    assert _status_folders(data_dir) == EMPTIED


def test_a_db_path_reached_through_a_symlink_is_compared_resolved(data_dir: Path, tmp_path: Path) -> None:
    """Contract 1: a DB reached through a symlink to the data dir's ``sqlite/`` resolves inside it, so the reset runs."""
    link = tmp_path / "sqlite-link"
    link.symlink_to(data_dir / "sqlite", target_is_directory=True)

    reset_broker_reports(data_dir=data_dir, db_path=link / "app.db")

    assert _status_folders(data_dir) == EMPTIED


def test_a_db_path_already_deleted_still_counts_as_inside(data_dir: Path) -> None:
    """Contract 1: the check is about where the DB is, not whether its file still exists.

    ``--force`` deletes the DB file, and the reset may well run after that.
    """
    _db_path(data_dir).unlink()

    reset_broker_reports(data_dir=data_dir, db_path=_db_path(data_dir))

    assert _status_folders(data_dir) == EMPTIED


# =============================================================================
# 2. NOTHING ELSE IS TOUCHED — every test proves first that the reset ran
# =============================================================================


def test_keeps_the_lock_files(data_dir: Path) -> None:
    """Contract 2: ``broker_reports/.locks`` and its lock files are untouched — a running server may hold them.

    Barrier first: the same call emptied the status folders, or a function doing nothing would pass.
    """
    locks = data_dir / "broker_reports" / ".locks"
    before = _snapshot(locks)

    reset_broker_reports(data_dir=data_dir, db_path=_db_path(data_dir))

    assert _status_folders(data_dir) == EMPTIED, NO_RESET
    assert _snapshot(locks) == before


def test_keeps_custom_uploads(data_dir: Path) -> None:
    """Contract 2: ``custom-uploads`` and its files are untouched — emptying them stays ``--clean``'s job.

    Barrier first: the same call emptied the status folders, or a function doing nothing would pass.
    """
    uploads = data_dir / "custom-uploads"
    before = _snapshot(uploads)

    reset_broker_reports(data_dir=data_dir, db_path=_db_path(data_dir))

    assert _status_folders(data_dir) == EMPTIED, NO_RESET
    assert _snapshot(uploads) == before


def test_keeps_the_database_file(data_dir: Path) -> None:
    """Contract 2: the database file, and the WAL/SHM journals beside it, are untouched.

    Barrier first: the same call emptied the status folders, or a function doing nothing would pass.
    """
    sqlite = data_dir / "sqlite"
    before = _snapshot(sqlite)

    reset_broker_reports(data_dir=data_dir, db_path=_db_path(data_dir))

    assert _status_folders(data_dir) == EMPTIED, NO_RESET
    assert _snapshot(sqlite) == before


def test_keeps_the_rest_of_the_data_dir(data_dir: Path) -> None:
    """Contract 2: every other entry of the data dir — here ``logs/`` and ``scheduler_state.json`` — is untouched.

    Nothing new appears beside them either. ``broker_reports``, ``custom-uploads`` and ``sqlite``
    have tests of their own. Barrier first: the same call emptied the status folders.
    """
    pinned_elsewhere = (data_dir / "broker_reports", data_dir / "custom-uploads", data_dir / "sqlite")
    before = _snapshot(data_dir, skip=pinned_elsewhere)

    reset_broker_reports(data_dir=data_dir, db_path=_db_path(data_dir))

    assert _status_folders(data_dir) == EMPTIED, NO_RESET
    assert _snapshot(data_dir, skip=pinned_elsewhere) == before


def test_keeps_unknown_entries_beside_the_status_folders(data_dir: Path) -> None:
    """Contract 2: only the three status folders are emptied; a stray file or folder elsewhere in ``broker_reports`` stays.

    ``broker_reports`` is not wiped and rebuilt around ``.locks``. Barrier first: the same call
    emptied the status folders.
    """
    reports = data_dir / "broker_reports"
    _plant(reports / "README.txt", b"notes\n")
    _plant(reports / "archive" / "old.csv")
    pinned_elsewhere = (*(reports / status for status in STATUS_FOLDERS), reports / ".locks")
    before = _snapshot(reports, skip=pinned_elsewhere)

    reset_broker_reports(data_dir=data_dir, db_path=_db_path(data_dir))

    assert _status_folders(data_dir) == EMPTIED, NO_RESET
    assert _snapshot(reports, skip=pinned_elsewhere) == before


def test_keeps_everything_outside_the_data_dir(data_dir: Path, tmp_path: Path, configured_data_dir: Path) -> None:
    """Contract 2: nothing outside the data dir is touched.

    Here a neighbouring lane with the very same layout, and a loose file beside the data dir. The
    configured data dir has a test of its own. Barrier first: the same call emptied the status folders.
    """
    _build_data_dir(tmp_path / "neighbour-lane")
    _plant(tmp_path / "loose.csv")
    pinned_elsewhere = (data_dir, configured_data_dir)
    before = _snapshot(tmp_path, skip=pinned_elsewhere)

    reset_broker_reports(data_dir=data_dir, db_path=_db_path(data_dir))

    assert _status_folders(data_dir) == EMPTIED, NO_RESET
    assert _snapshot(tmp_path, skip=pinned_elsewhere) == before


def test_works_on_the_given_data_dir_not_the_configured_one(data_dir: Path, configured_data_dir: Path) -> None:
    """Contract 2: the configured test data dir — what ``get_data_dir()`` returns — lies outside ``data_dir`` and is untouched.

    The function works on its argument only. That is the likeliest slip, since ``clean_data_dirs``
    reads ``get_data_dir()`` itself; the autouse sandbox makes it cost a canary, not the lane's
    reports. Barrier first: the same call emptied the status folders.
    """
    before = _snapshot(configured_data_dir)

    reset_broker_reports(data_dir=data_dir, db_path=_db_path(data_dir))

    assert _status_folders(data_dir) == EMPTIED, NO_RESET
    assert _snapshot(configured_data_dir) == before


# =============================================================================
# 3. DB OUTSIDE THE DATA DIR: NOTHING AT ALL IS TOUCHED
# =============================================================================


@pytest.mark.parametrize("where", ["dot-dot-escape", "name-prefix-sibling", "parent-of-data-dir"])
def test_a_db_outside_the_data_dir_touches_nothing(data_dir: Path, tmp_path: Path, where: str) -> None:
    """Contract 3: a DB that resolves outside the data dir leaves every file where it was, and the result is 0.

    Each location looks inside to one wrong check:

    - ``dot-dot-escape``, ``data_dir/../other/app.db``: to a comparison of unresolved paths;
    - ``name-prefix-sibling``, ``data-old/sqlite/app.db``: to a string-prefix comparison;
    - ``parent-of-data-dir``, ``app.db`` in the folder holding the data dir: to an overlap test
      (either path containing the other) or a containment test with its arguments swapped.

    Guard: a function that does nothing passes it; it fails only if the check lets such a path through.
    """
    db_path = {
        "dot-dot-escape": data_dir / ".." / "other" / "app.db",
        "name-prefix-sibling": data_dir.with_name(f"{data_dir.name}-old") / "sqlite" / "app.db",
        "parent-of-data-dir": data_dir.parent / "app.db",
    }[where]
    _plant(db_path, SQLITE_BYTES)
    before = _snapshot(tmp_path)

    removed = reset_broker_reports(data_dir=data_dir, db_path=db_path)

    assert removed == 0
    assert _snapshot(tmp_path) == before


def test_a_db_outside_the_data_dir_creates_no_folder(tmp_path: Path) -> None:
    """Contract 3: touching nothing includes creating nothing — contract 5's missing folders stay missing when the DB is elsewhere.

    Guard: a function that does nothing passes it; it fails if the folders are ensured before the
    data-dir check.
    """
    data_dir = tmp_path / "data"
    _plant(data_dir / "custom-uploads" / "avatar.png", b"\x89PNG\r\n\x1a\n")
    db_path = _plant(tmp_path / "other" / "sqlite" / "app.db", SQLITE_BYTES)
    before = _snapshot(tmp_path)

    removed = reset_broker_reports(data_dir=data_dir, db_path=db_path)

    assert removed == 0
    assert _snapshot(tmp_path) == before


# =============================================================================
# 4. THE RESULT COUNTS THE FILES REMOVED
# =============================================================================


def test_returns_the_number_of_files_removed(tmp_path: Path) -> None:
    """Contract 4: two brokers holding one report each, a csv and its json sidecar → 4.

    Not 6: the lock file and the custom upload beside them are not removed, so they are not counted.
    """
    data_dir = tmp_path / "data"
    _plant(_db_path(data_dir), SQLITE_BYTES)
    _plant(data_dir / "custom-uploads" / "avatar.png", b"\x89PNG\r\n\x1a\n")
    reports = data_dir / "broker_reports"
    _plant(reports / ".locks" / "broker_1.lock", b"")
    _plant_report(reports / "uploaded" / "broker_1", 1)
    _plant_report(reports / "parsed" / "broker_2", 2)
    (reports / "failed").mkdir()

    assert reset_broker_reports(data_dir=data_dir, db_path=_db_path(data_dir)) == 4


def test_counts_files_at_every_depth_and_never_folders(tmp_path: Path) -> None:
    """Contract 4: the count is recursive, and folders count for nothing.

    Six files: an upload with no broker at the root of ``uploaded`` (2); a ``failed`` broker folder
    holding a report plus the temp sidecar an interrupted atomic write leaves behind (3); one file
    two folders below a ``parsed`` broker folder (1). The five folders removed with them — an empty
    broker folder among them — are not counted.
    """
    data_dir = tmp_path / "data"
    _plant(_db_path(data_dir), SQLITE_BYTES)
    reports = data_dir / "broker_reports"
    _plant_report(reports / "uploaded", 1)
    (reports / "uploaded" / "broker_5").mkdir()
    _plant_report(reports / "failed" / "broker_3", 2)
    _plant(reports / "failed" / "broker_3" / f"{uuid.UUID(int=2)}.json.tmp.{uuid.UUID(int=3).hex}", b"{")
    _plant(reports / "parsed" / "broker_4" / "nested" / "deeper" / "report.csv")

    assert reset_broker_reports(data_dir=data_dir, db_path=_db_path(data_dir)) == 6


# =============================================================================
# 5. MISSING FOLDERS ARE CREATED
# =============================================================================


def test_creates_the_status_folders_when_broker_reports_is_missing(tmp_path: Path) -> None:
    """Contract 5: a data dir with no ``broker_reports`` ends with the three status folders, empty, and the result is 0."""
    data_dir = tmp_path / "data"
    _plant(_db_path(data_dir), SQLITE_BYTES)

    removed = reset_broker_reports(data_dir=data_dir, db_path=_db_path(data_dir))

    assert removed == 0
    assert _status_folders(data_dir) == EMPTIED


def test_creates_the_missing_status_folders(tmp_path: Path) -> None:
    """Contract 5: ``broker_reports`` holding only an empty ``uploaded`` gains ``parsed`` and ``failed``, and the result is 0."""
    data_dir = tmp_path / "data"
    _plant(_db_path(data_dir), SQLITE_BYTES)
    (data_dir / "broker_reports" / "uploaded").mkdir(parents=True)

    removed = reset_broker_reports(data_dir=data_dir, db_path=_db_path(data_dir))

    assert removed == 0
    assert _status_folders(data_dir) == EMPTIED


# =============================================================================
# 6. IDEMPOTENT
# =============================================================================


def test_a_second_call_returns_zero_and_changes_nothing(data_dir: Path, tmp_path: Path) -> None:
    """Contract 6: once the data dir is reset, a second reset returns 0 and leaves every file as it was.

    Barrier first: the first call emptied the status folders. A function that does nothing is
    idempotent for free.
    """
    reset_broker_reports(data_dir=data_dir, db_path=_db_path(data_dir))
    assert _status_folders(data_dir) == EMPTIED, NO_RESET
    before = _snapshot(tmp_path)

    removed = reset_broker_reports(data_dir=data_dir, db_path=_db_path(data_dir))

    assert removed == 0
    assert _snapshot(tmp_path) == before


# =============================================================================
# 7. A SYMLINK IS REMOVED AS A LINK, NEVER FOLLOWED
# =============================================================================


@pytest.mark.parametrize("link", ["uploaded/linked.csv", "uploaded/broker_1/linked.csv"])
def test_a_symlink_to_a_file_is_removed_as_a_link(data_dir: Path, tmp_path: Path, link: str) -> None:
    """Contract 7: a link to a file outside the data dir goes; the file it points to stays, bytes unchanged.

    Planted at the root of a status folder, then inside a broker folder.
    """
    outside = tmp_path / "outside"
    target = _plant(outside / "precious.csv")
    (data_dir / "broker_reports" / link).symlink_to(target)
    before = _snapshot(outside)

    reset_broker_reports(data_dir=data_dir, db_path=_db_path(data_dir))

    assert _snapshot(outside) == before
    assert _status_folders(data_dir) == EMPTIED


@pytest.mark.parametrize("link", ["uploaded/broker_77", "uploaded/broker_1/linked"])
def test_a_symlink_to_a_folder_is_removed_as_a_link(data_dir: Path, tmp_path: Path, link: str) -> None:
    """Contract 7: a link to a folder outside the data dir goes; the folder and everything below it stay.

    Planted at the root of a status folder, named like a broker folder, then inside a broker folder.
    ``shutil.rmtree`` refuses a link given as its root, and a walk that follows links empties the target.
    """
    outside = tmp_path / "outside"
    _plant_report(outside / "precious", 7)
    _plant(outside / "precious" / "sub" / "deeper.csv")
    (data_dir / "broker_reports" / link).symlink_to(outside / "precious", target_is_directory=True)
    before = _snapshot(outside)

    reset_broker_reports(data_dir=data_dir, db_path=_db_path(data_dir))

    assert _snapshot(outside) == before
    assert _status_folders(data_dir) == EMPTIED


# ---------------------------------------------------------------------------
# C6-6 (C-51) and W6-10 (U-B9): the mock data write the shapes the models read
# ---------------------------------------------------------------------------


def _mock_classifications() -> dict[str, dict]:
    """``display_name`` -> the dict the mock asset passes to ``json.dumps`` (read as source, never run)."""
    tree = ast.parse(Path(populate_mock_data.__file__).read_text(encoding="utf-8"))
    found: dict[str, dict] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        entries = {k.value: v for k, v in zip(node.keys, node.values, strict=True) if isinstance(k, ast.Constant)}
        name, params = entries.get("display_name"), entries.get(populate_mock_data.LEGACY_CLASSIFICATION_KEY)
        if isinstance(name, ast.Constant) and isinstance(params, ast.Call) and params.args:
            found[name.value] = ast.literal_eval(params.args[0])
    return found


def _mock_dict_literals(key: str) -> list[dict]:
    """Every dict literal of ``populate_mock_data.py`` that carries ``key``, as written in the source."""
    tree = ast.parse(Path(populate_mock_data.__file__).read_text(encoding="utf-8"))
    return [{k.value: v for k, v in zip(node.keys, node.values, strict=True) if isinstance(k, ast.Constant)} for node in ast.walk(tree) if isinstance(node, ast.Dict) and any(isinstance(k, ast.Constant) and k.value == key for k in node.keys)]


#: The parts of a mock classification and the profile voices they become (plan 68, A4; migration 006).
_VOICE_OF_PART = {"short_description": "description", "geographic_area": "geography", "sector_area": "sector"}


def test_every_mock_asset_classification_validates_against_the_model():
    """C6-6 (C-51): not one mock asset writes a shape the profile's catalogue refuses; the failures are named. Since plan
    68 D7a the old container's model is gone: each part is checked as the voice it becomes."""
    assets = _mock_dict_literals(populate_mock_data.LEGACY_CLASSIFICATION_KEY)
    assert len(assets) >= 10, "the mock assets were not found: update this test"

    refused = {}
    for entry in assets:
        params = entry[populate_mock_data.LEGACY_CLASSIFICATION_KEY]
        if not (isinstance(params, ast.Call) and params.args):
            continue
        try:
            # Read as the mirror reads the JSON the seed writes: the weights as Decimals
            for part, value in json.loads(json.dumps(ast.literal_eval(params.args[0])), parse_float=Decimal).items():
                normalize_value(_VOICE_OF_PART[part], value if part == "short_description" else value["distribution"])
        except ValueError as exc:
            refused[ast.literal_eval(entry["display_name"])] = str(exc).splitlines()[0]

    assert not refused, f"mock assets whose classification the profile catalogue refuses: {refused}"


def test_every_mock_asset_classification_is_mirrored_into_the_profile():
    """Plan 68, D2: since the portfolio engine reads countries and sectors from the profile only, a populated database
    holds the ``legacy`` profile rows migration 006 would copy from the old column: one per part present
    (description, geography, sector), in the catalogue's stored form. Without them every mock allocation is Unknown."""
    mirror = getattr(populate_mock_data, "_legacy_profile_rows", None)
    assert mirror is not None, "populate_mock_data has no _legacy_profile_rows: the mock classifications never reach the profile"
    mocks = _mock_classifications()
    assert len(mocks) >= 10, "the mock assets were not found: update this test"
    parts = {"short_description": "description", "geographic_area": "geography", "sector_area": "sector"}
    for name, params in mocks.items():
        rows = mirror(Asset(id=7, display_name=name, currency="EUR"), json.dumps(params))
        expected = {}
        for part, voice in parts.items():
            if params.get(part) is None:
                continue
            raw = params[part] if part == "short_description" else {key: str(weight) for key, weight in params[part]["distribution"].items()}
            expected[voice] = normalize_value(voice, raw)
        got = {row.key: json.loads(row.value) for row in rows}
        assert got == expected, f"{name}: profile rows {got} != {expected}"
        assert all(row.asset_id == 7 and row.source == "legacy" and row.read_on is not None for row in rows), f"{name}: {rows}"


def test_the_mock_legacy_rows_are_dated_on_the_assets_first_day():
    """Plan 68, A4b: migration 006 dates each ``legacy`` row on its asset's first day — the earliest of the day of its
    ``created_at``, its first price and its first transaction; with neither, the day of ``created_at``. The mock data
    mirrors it, after the prices and the transactions are in: ``date_legacy_profile_rows``."""
    from sqlalchemy import text  # noqa: PLC0415 — an in-memory database of this test only
    from sqlmodel import Session, SQLModel, create_engine  # noqa: PLC0415

    redate = getattr(populate_mock_data, "date_legacy_profile_rows", None)
    assert redate is not None, "populate_mock_data has no date_legacy_profile_rows: the mock legacy rows stay on the populate day"
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    stamp = "2026-11-10 09:30:00.000000"
    with Session(engine) as session:
        session.add(Broker(id=1, name="First day broker"))
        session.flush()
        for asset_id in (1, 2, 3):
            session.add(Asset(id=asset_id, display_name=f"A{asset_id}", currency="EUR", asset_type=AssetType.ETF, created_at=datetime(2026, 11, 10, 9, 30, tzinfo=UTC), updated_at=datetime(2026, 11, 10, 9, 30, tzinfo=UTC)))
            session.flush()
            session.exec(text(f"INSERT INTO asset_profile_updates (asset_id, key, value, source, read_on, created_at) VALUES ({asset_id}, 'description', '\"d\"', 'legacy', '2026-11-17', '{stamp}')"))
        session.exec(text(f"INSERT INTO price_history (asset_id, date, close, currency, source_plugin_key, fetched_at) VALUES (1, '2021-03-01', 100, 'EUR', 'manual', '{stamp}')"))
        session.exec(text(f"INSERT INTO price_history (asset_id, date, close, currency, source_plugin_key, fetched_at) VALUES (2, '2021-03-01', 100, 'EUR', 'manual', '{stamp}')"))
        session.exec(text(f"INSERT INTO transactions (broker_id, asset_id, type, date, quantity, amount, currency, created_at, updated_at) VALUES (1, 2, 'BUY', '2019-06-14', 1, -100, 'EUR', '{stamp}', '{stamp}')"))
        session.exec(text(f"INSERT INTO asset_profile_updates (asset_id, key, value, source, read_on, created_at) VALUES (3, 'ter', '\"0.002\"', 'justetf', '2026-11-17', '{stamp}')"))
        session.commit()
        redate(session)
        days = {(row[0], row[1]): row[2] for row in session.exec(text("SELECT asset_id, source, read_on FROM asset_profile_updates"))}
    assert days[(1, "legacy")] == "2021-03-01", f"first price before created_at: {days}"
    assert days[(2, "legacy")] == "2019-06-14", f"a transaction before everything: {days}"
    assert days[(3, "legacy")] == "2026-11-10", f"neither price nor transaction: the created_at day: {days}"
    assert days[(3, "justetf")] == "2026-11-17", f"a row of a source is never redated: {days}"


def test_the_mock_legacy_rows_are_dated_after_the_prices_and_transactions():
    """The populate run calls ``date_legacy_profile_rows`` after every step that writes prices or transactions."""
    tree = ast.parse(Path(populate_mock_data.__file__).read_text(encoding="utf-8"))
    order: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id.startswith(("populate_", "date_legacy_", "link_", "create_split", "add_balance")):
            order.append((node.lineno, node.func.id))
    calls = [name for _, name in sorted(order)]
    assert "date_legacy_profile_rows" in calls, f"the populate run never redates the legacy rows: {calls}"
    position = calls.index("date_legacy_profile_rows")
    for writer in ("populate_price_history", "populate_transactions", "populate_wac_test_transactions", "create_split_transaction", "add_balance_safe_cash_prefunds"):
        assert writer in calls and calls.index(writer) < position, f"{writer} must run before date_legacy_profile_rows: {calls}"


def test_every_mock_broker_key_is_a_field_of_the_broker_model():
    """W6-10 (U-B9): ``Broker(**data)`` drops an unknown key without a word (``brim_plugin_key`` did, for every broker)."""
    brokers = _mock_dict_literals("allow_cash_overdraft")
    assert brokers, "the mock brokers were not found: update this test"

    unknown = {ast.literal_eval(b["name"]): sorted(set(b) - set(Broker.model_fields)) for b in brokers if set(b) - set(Broker.model_fields)}

    assert not unknown, f"mock broker keys that are not Broker fields: {unknown}"


def test_every_mock_broker_default_import_plugin_is_an_installed_plugin():
    plugins = {p.name for p in (PROJECT_ROOT / "backend/app/services/brim_providers").iterdir() if p.is_dir()}
    chosen = {ast.literal_eval(b["name"]): ast.literal_eval(b["default_import_plugin"]) for b in _mock_dict_literals("allow_cash_overdraft") if "default_import_plugin" in b}

    assert len(chosen) >= 7, f"the mock brokers must each name a default import plugin: {chosen}"
    assert {name: code for name, code in chosen.items() if code not in plugins} == {}

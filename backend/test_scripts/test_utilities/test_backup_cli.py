"""
Instance backup, the command line (workstream B, lot B1): ``scripts/backup_cli.py``.

``dev.py backup`` is registered in a later step: the commands are tested through the module's functions and through
``python scripts/backup_cli.py``.

(a) ``_output_path``: no ``--output``, the archive goes to ``<data dir>/backups/<name>``; an existing folder receives
    it under its own name; any other path is the archive's file; a relative path is relative to the working
    directory, and ``~`` is the home folder.
(b) ``_drop_root_privileges``: run as root (``docker compose exec`` without a user) on a data directory owned by
    another user, the command drops its supplementary groups, takes the owner's group, then the owner's user, in that
    order (once the user is changed, the group can no longer be). A failure comes back as a message and the command
    stops. Nothing changes when the command is not root, when the owner is root, or without ``os.geteuid``.
(c) ``_dispatch`` without a subcommand prints how to get help and returns 1.
(d) ``cmd_inspect``: 0 for an intact archive, and for ``--no-verify``, which reads the manifest only; 1 for a missing
    file, a file that is not a zip, a zip without manifest, an entry altered or added, and a damaged archive.
(e) ``cmd_create``: 1 without a data directory, without a database (nothing written), with an ``--output`` file that
    already exists (nothing run), and when the switch to the owner of the data directory fails; 0 otherwise, with the
    archive (0600) where it was asked for and the job's folder removed.
(f) The script: ``python scripts/backup_cli.py create``, then ``inspect`` on the archive it wrote, both exit 0;
    without a command, exit 1.

Pure: data directories in ``tmp_path``. In this process a command sees a production data directory of the test through
its environment (``LIBREFOLIO_TEST_MODE`` removed, ``LIBREFOLIO_DATA_DIR`` in ``tmp_path``, set with ``monkeypatch``
and checked before any command runs). A child process gets this process's environment without ``LIBREFOLIO_*`` and
``COVERAGE_*``, plus that ``LIBREFOLIO_DATA_DIR``, and runs in ``tmp_path``. In every root case ``os.geteuid``,
``os.setgroups``, ``os.setgid`` and ``os.setuid`` are replaced: no test changes the identity of its process.
``LF_APP_VERSION`` is set, so no git process runs. No lane database, no server, no network.
"""

from __future__ import annotations

import argparse
import os
import re
import shlex
import sqlite3
import stat
import struct
import subprocess
import sys
import zipfile
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.app.config import get_data_dir
from backend.app.services.platform.instance_backup.archive import build_archive, check_archive
from backend.app.services.platform.instance_backup.manifest import BackupManifest
from backend.app.services.platform.instance_backup.paths import DATABASE_ENTRY, MANIFEST_ENTRY, backups_dir, jobs_dir
from backend.app.utils.runtime.version import get_git_version
from backend.test_scripts.test_utils import print_section, print_success
from scripts import backup_cli

POSIX = os.name != "nt"
AS_ROOT = POSIX and os.geteuid() == 0
needs_posix_modes = pytest.mark.skipif(not POSIX, reason="file modes are POSIX only")

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = PROJECT_ROOT / "scripts" / "backup_cli.py"
APP_VERSION = "v0.0.0-b1-cli-test"
REVISION = "b1a2c3d4e5f6"
NAME = "librefolio-backup-20261015-101500.zip"
#: Seconds. A child imports the application first, and a loaded parallel run is slow; a hang still ends.
CLI_TIMEOUT = 120
#: Characters of a child's output quoted by an assertion message.
TAIL = 3000
FILES = {
    "custom-uploads/a.txt": b"uploaded file\n" * 64,
    "broker_reports/uploaded/r.csv": b"date,amount\n2026-10-01,10.00\n",
    "scenario_catalog/s.json": b'{"scenarios": [1, 2, 3]}\n',
}


# =============================================================================
# Helpers
# =============================================================================


@pytest.fixture(autouse=True)
def app_version(monkeypatch):
    """The version of every manifest, without a git process; ``get_git_version``'s process-wide cache emptied around the test."""
    monkeypatch.setenv("LF_APP_VERSION", APP_VERSION)
    get_git_version.cache_clear()
    yield
    get_git_version.cache_clear()


def make_data_dir(root: Path, *, database: bool = True) -> Path:
    """A data directory: a small database (unless ``database`` is false) and one file in each archived folder."""
    for entry, content in FILES.items():
        (root / entry).parent.mkdir(parents=True, exist_ok=True)
        (root / entry).write_bytes(content)
    if database:
        (root / DATABASE_ENTRY).parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(root / DATABASE_ENTRY)) as conn:
            conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
            conn.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)")
            with conn:
                conn.executemany("INSERT INTO users (id, name) VALUES (?, ?)", [(1, "ada"), (2, "grace")])
                conn.execute("INSERT INTO alembic_version (version_num) VALUES (?)", (REVISION,))
    return root


def point_at(monkeypatch, root: Path) -> Path:
    """Make ``root`` the production data directory the commands of this process see; checked before returning it."""
    monkeypatch.delenv("LIBREFOLIO_TEST_MODE", raising=False)
    monkeypatch.delenv("LIBREFOLIO_TEST_DATA_DIR", raising=False)
    monkeypatch.setenv("LIBREFOLIO_DATA_DIR", str(root))
    assert get_data_dir() == root.resolve(), f"precondition: the command must work on this test's data directory, not on {get_data_dir()}"
    return root.resolve()


def listing(root: Path) -> list[str]:
    return sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))


def create_args(output: str | None = None) -> argparse.Namespace:
    return argparse.Namespace(test_db=False, output=output)


def inspect(path: Path, *, no_verify: bool = False) -> int:
    return backup_cli.cmd_inspect(argparse.Namespace(archive=str(path), no_verify=no_verify))


@pytest.fixture
def good_archive(tmp_path) -> Path:
    data = make_data_dir(tmp_path / "data")
    work = tmp_path / "work"
    work.mkdir()
    return build_archive(data, work, work / NAME, origin="cli").path


def rebuilt(source: Path, target: Path, *, drop: tuple[str, ...] = (), swap: dict[str, bytes] | None = None, add: dict[str, bytes] | None = None) -> Path:
    """A copy of the archive ``source`` with entries left out, given other bytes, or added."""
    with zipfile.ZipFile(source) as old, zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as new:
        for info in old.infolist():
            if info.filename not in drop:
                new.writestr(info, (swap or {}).get(info.filename, old.read(info)))
        for name, data in (add or {}).items():
            new.writestr(name, data)
    return target


def corrupt(source: Path, target: Path, entry: str) -> Path:
    """A copy of the archive ``source`` with one byte inverted in the middle of the stored data of ``entry``."""
    raw = bytearray(source.read_bytes())
    with zipfile.ZipFile(source) as zf:
        info = zf.getinfo(entry)
    signature, *_, name_length, extra_length = struct.unpack("<4s2B4HL2L2H", raw[info.header_offset : info.header_offset + 30])
    assert signature == b"PK\x03\x04", "precondition: the local header of the entry is where the central directory says"
    raw[info.header_offset + 30 + name_length + extra_length + info.compress_size // 2] ^= 0xFF
    target.write_bytes(bytes(raw))
    return target


# =============================================================================
# (a) _output_path
# =============================================================================


def test_without_output_the_archive_goes_to_the_backups_folder_of_the_data_directory(tmp_path):
    print_section("_output_path")
    data = tmp_path / "data"
    for output in (None, ""):
        assert backup_cli._output_path(output, data, NAME) == data / "backups" / NAME, f"--output {output!r}: the archive goes to <data dir>/backups/"
    print_success("no --output → <data dir>/backups/<name>")


def test_an_existing_folder_receives_the_archive_under_its_own_name(tmp_path):
    nas = tmp_path / "nas"
    nas.mkdir()
    for output in (str(nas), f"{nas}/"):
        assert backup_cli._output_path(output, tmp_path / "data", NAME) == nas / NAME, f"--output {output}: an existing folder receives the archive"
    print_success("existing folder → <folder>/<name>")


def test_any_other_path_is_the_archive_file(tmp_path):
    target = tmp_path / "nas" / "monday.zip"
    assert backup_cli._output_path(str(target), tmp_path / "data", NAME) == target, "a path that is not an existing folder is the archive's file, its folder created later"
    print_success("file path → that file")


def test_a_relative_path_is_relative_to_the_working_directory(tmp_path, monkeypatch):
    (tmp_path / "nas").mkdir()
    monkeypatch.chdir(tmp_path)
    assert backup_cli._output_path("nas", tmp_path / "data", NAME) == Path.cwd() / "nas" / NAME, "a relative folder is found from the working directory"
    assert backup_cli._output_path("monday.zip", tmp_path / "data", NAME) == Path.cwd() / "monday.zip", "a relative file too"
    print_success("relative paths from the working directory")


def test_a_path_from_the_home_folder_is_expanded(tmp_path, monkeypatch):
    home = tmp_path / "home"
    (home / "nas").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    assert backup_cli._output_path("~/nas", tmp_path / "data", NAME) == home / "nas" / NAME, "~ is the home folder"
    print_success("~/nas → <home>/nas/<name>")


# =============================================================================
# (b) _drop_root_privileges
# =============================================================================


class Owned:
    """A data directory as ``stat()`` describes it: owned by ``uid``:``gid``."""

    def __init__(self, uid: int, gid: int):
        self.uid = uid
        self.gid = gid

    def stat(self) -> SimpleNamespace:
        return SimpleNamespace(st_uid=self.uid, st_gid=self.gid)

    def __str__(self) -> str:
        return "/srv/librefolio-data"


def refuse(identity: int) -> None:
    raise PermissionError(1, "Operation not permitted")


@pytest.fixture
def identity(monkeypatch) -> list[tuple[str, object]]:
    """The identity changes, recorded instead of made; the effective user is root unless a test says otherwise."""
    calls: list[tuple[str, object]] = []
    monkeypatch.setattr(backup_cli.os, "geteuid", lambda: 0, raising=False)
    monkeypatch.setattr(backup_cli.os, "setgroups", lambda groups: calls.append(("setgroups", list(groups))), raising=False)
    monkeypatch.setattr(backup_cli.os, "setgid", lambda gid: calls.append(("setgid", gid)), raising=False)
    monkeypatch.setattr(backup_cli.os, "setuid", lambda uid: calls.append(("setuid", uid)), raising=False)
    return calls


def test_as_root_the_command_becomes_the_owner_of_the_data_directory(identity):
    """(b) Groups dropped, then the group, then the user: every file it writes (archive, lock, SQLite's) is the server's."""
    print_section("_drop_root_privileges")
    assert backup_cli._drop_root_privileges(Owned(1000, 1001)) is None, "a successful switch returns no message"
    assert identity == [("setgroups", []), ("setgid", 1001), ("setuid", 1000)], f"root must drop its groups, take gid 1001, then uid 1000, in that order: {identity}"
    print_success("setgroups([]) → setgid(1001) → setuid(1000)")


def test_a_failed_switch_is_a_message_naming_the_owner(identity, monkeypatch):
    monkeypatch.setattr(backup_cli.os, "setuid", refuse)
    message = backup_cli._drop_root_privileges(Owned(1000, 1001))
    assert message is not None and "1000:1001" in message and "Run the command as that user" in message, f"the message names the owner and what to do: {message!r}"
    print_success(message)


@pytest.mark.parametrize("case", ["not-root", "owner-is-root", "no-geteuid"])
def test_nothing_changes_when_there_is_nothing_to_drop(identity, monkeypatch, case):
    if case == "not-root":
        monkeypatch.setattr(backup_cli.os, "geteuid", lambda: 1000)
    elif case == "no-geteuid":
        monkeypatch.delattr(backup_cli.os, "geteuid")
    owner = Owned(0, 0) if case == "owner-is-root" else Owned(1000, 1001)
    assert backup_cli._drop_root_privileges(owner) is None, f"{case}: no message"
    assert identity == [], f"{case}: the identity must not change: {identity}"
    print_success(f"{case}: nothing changed")


@pytest.mark.skipif(not POSIX or AS_ROOT, reason="needs a data directory owned by a user other than root")
def test_create_stops_when_the_switch_to_the_owner_fails(tmp_path, monkeypatch, identity, capsys):
    """(b)(e) Started as root, unable to become the owner: the command stops before writing anything as root."""
    root = point_at(monkeypatch, make_data_dir(tmp_path / "data"))
    monkeypatch.setattr(backup_cli.os, "setuid", refuse)
    before = listing(root)
    assert backup_cli.cmd_create(create_args()) == 1, "a failed switch is exit code 1"
    assert "cannot switch to the owner" in capsys.readouterr().out, "the command says why it stopped"
    assert listing(root) == before, f"nothing may be written: {sorted(set(listing(root)) - set(before))}"
    print_success("switch refused → exit 1, nothing written")


# =============================================================================
# (c) _dispatch
# =============================================================================


def test_without_a_command_the_cli_says_how_to_get_help_and_exits_1(capsys):
    assert backup_cli._dispatch(argparse.Namespace(test_db=False)) == 1, "no subcommand is exit code 1"
    assert "backup command required" in capsys.readouterr().out, "and says a command is required"
    print_success("no subcommand → 1")


# =============================================================================
# (d) cmd_inspect
# =============================================================================


def test_inspect_an_intact_archive(good_archive, capsys):
    print_section("cmd_inspect")
    assert inspect(good_archive) == 0, "an intact archive is exit code 0"
    out = capsys.readouterr().out
    assert "✅ Every entry matches the manifest" in out, f"the verification is reported: {out}"
    for fact in (f"LibreFolio {APP_VERSION} (cli)", f"revision {REVISION}", "Files: 3", "Instance key: not included"):
        assert fact in out, f"inspect shows {fact!r}: {out}"
    print_success("intact archive → 0")


def test_inspect_without_verification_reads_the_manifest_only(good_archive, tmp_path, capsys):
    tampered = rebuilt(good_archive, tmp_path / "tampered.zip", swap={"custom-uploads/a.txt": FILES["custom-uploads/a.txt"].upper()})
    assert inspect(tampered, no_verify=True) == 0, "--no-verify does not read the entries: names right, exit code 0"
    assert "entries not verified (--no-verify)" in capsys.readouterr().out, "and says the entries were not verified"
    assert inspect(tampered) == 1, "verified, the same archive is exit code 1"
    print_success("--no-verify → 0 with a notice; verified → 1")


def bad_archive(case: str, good: Path, tmp_path: Path) -> Path:
    if case == "missing-file":
        return tmp_path / "absent.zip"
    if case == "not-a-zip":
        path = tmp_path / "not-a-zip.zip"
        path.write_text("not a zip\n", encoding="utf-8")
        return path
    if case == "no-manifest":
        return rebuilt(good, tmp_path / "bad.zip", drop=(MANIFEST_ENTRY,))
    if case == "altered-entry":
        return rebuilt(good, tmp_path / "bad.zip", swap={"custom-uploads/a.txt": b"something else"})
    return rebuilt(good, tmp_path / "bad.zip", add={"custom-uploads/extra.txt": b"not in the manifest"})


@pytest.mark.parametrize(
    ("case", "said"),
    [
        ("missing-file", "No file at"),
        ("not-a-zip", "(archive_unreadable)"),
        ("no-manifest", "(manifest_missing)"),
        ("altered-entry", "1 entry different from the manifest: custom-uploads/a.txt"),
        ("added-entry", "1 entry not in the manifest: custom-uploads/extra.txt"),
    ],
)
def test_inspect_says_what_is_wrong_and_exits_1(good_archive, tmp_path, capsys, case, said):
    assert inspect(bad_archive(case, good_archive, tmp_path)) == 1, f"{case}: exit code 1"
    out = capsys.readouterr().out
    assert said in out, f"{case}: inspect must say {said!r}: {out}"
    print_success(f"{case} → 1: {said}")


def test_inspect_reports_a_damaged_archive_and_exits_1(good_archive, tmp_path, capsys):
    """(d) One byte of an entry damaged, the zip structure intact: what ``inspect`` is run for, on a suspect backup."""
    damaged = corrupt(good_archive, tmp_path / "damaged.zip", "custom-uploads/a.txt")
    try:
        code = inspect(damaged)
    except Exception as exc:
        pytest.fail(f"backup inspect crashed with {type(exc).__module__}.{type(exc).__name__} ({exc}) on an archive with one damaged entry, where it must say so and exit 1: cmd_inspect catches ArchiveError and ManifestError only, and check_archive lets zipfile's own errors through")
    assert code == 1, f"a damaged archive is exit code 1, not {code}"
    print_success("damaged archive → 1")


# =============================================================================
# (e) cmd_create
# =============================================================================


def test_create_without_a_data_directory_exits_1(tmp_path, monkeypatch, capsys):
    print_section("cmd_create")
    absent = point_at(monkeypatch, tmp_path / "absent")
    assert backup_cli.cmd_create(create_args()) == 1, "no data directory is exit code 1"
    assert "No data directory at" in capsys.readouterr().out, "the command says the data directory is missing"
    assert not absent.exists(), "and does not create it"
    print_success("no data directory → 1")


def test_create_without_a_database_exits_1_and_writes_nothing(tmp_path, monkeypatch, capsys):
    root = point_at(monkeypatch, make_data_dir(tmp_path / "data", database=False))
    before = listing(root)
    assert backup_cli.cmd_create(create_args()) == 1, "no database is exit code 1"
    assert "nothing to back up" in capsys.readouterr().out, "the command says there is no database to back up"
    assert listing(root) == before, f"nothing may be written, not even backups/: {sorted(set(listing(root)) - set(before))}"
    print_success("no database → 1, nothing written")


def test_create_refuses_an_output_file_that_already_exists_before_running(tmp_path, monkeypatch, capsys):
    root = point_at(monkeypatch, make_data_dir(tmp_path / "data"))
    existing = tmp_path / "monday.zip"
    existing.write_bytes(b"an archive kept by the user")
    assert backup_cli.cmd_create(create_args(str(existing))) == 1, "an existing --output file is exit code 1"
    assert "already exists" in capsys.readouterr().out, "the command says the file exists"
    assert existing.read_bytes() == b"an archive kept by the user", "the existing file is untouched"
    assert not backups_dir(root).exists(), "no backup ran: nothing was written in the data directory"
    print_success("existing --output file → 1 before any run")


def test_create_writes_the_archive_where_asked_and_removes_its_job(tmp_path, monkeypatch, capsys):
    root = point_at(monkeypatch, make_data_dir(tmp_path / "data"))
    nas = tmp_path / "nas"
    nas.mkdir()
    assert backup_cli.cmd_create(create_args(str(nas))) == 0, "a backup into an existing folder is exit code 0"
    written = sorted(nas.iterdir())
    assert len(written) == 1 and re.fullmatch(r"librefolio-backup-\d{8}-\d{6}\.zip", written[0].name), f"the folder receives one archive, named after its time: {[path.name for path in written]}"
    check = check_archive(written[0])
    assert check.ok and check.manifest.origin == "cli", f"the archive checks ok and says the CLI made it: {check}"
    if POSIX:
        assert stat.S_IMODE(written[0].stat().st_mode) == 0o600, "the archive stays readable by its owner only (0600)"
    assert [path.name for path in jobs_dir(root).iterdir() if path.name != ".lock"] == [], "the job's folder is removed once the archive is moved"
    out = capsys.readouterr().out
    assert f"✅ Backup written: {written[0]}" in out and "keep it private" in out, f"the command says where the archive is and that it is private: {out}"
    print_success(f"{written[0].name} written, job folder removed")


# =============================================================================
# (f) the script
# =============================================================================


def child_env(data: Path) -> dict[str, str]:
    """This process's environment without what could point a child elsewhere (or start coverage in it), plus the data dir."""
    env = {name: value for name, value in os.environ.items() if not name.startswith(("LIBREFOLIO_", "COVERAGE_"))}
    env.update(LIBREFOLIO_DATA_DIR=str(data), LF_APP_VERSION=APP_VERSION, PYTHONUNBUFFERED="1", PYTHONUTF8="1")
    return env


def script(*argv: str, env: dict[str, str], cwd: Path) -> subprocess.CompletedProcess:
    command = [sys.executable, str(SCRIPT), *argv]
    try:
        return subprocess.run(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL, capture_output=True, encoding="utf-8", errors="replace", timeout=CLI_TIMEOUT, check=False)
    except subprocess.TimeoutExpired as exc:
        pytest.fail(f"`{shlex.join(command)}` did not end within {CLI_TIMEOUT}s: {exc.stdout!r} {exc.stderr!r}")


def test_the_script_creates_an_archive_then_inspects_it(tmp_path):
    """(f) ``python scripts/backup_cli.py create`` then ``inspect``, as ``dev.py backup`` will run them."""
    print_section("python scripts/backup_cli.py")
    data = make_data_dir(tmp_path / "data").resolve()
    env = child_env(data)
    created = script("create", env=env, cwd=tmp_path)
    assert created.returncode == 0, f"create must exit 0, it exited {created.returncode}\n--- stdout\n{created.stdout[-TAIL:]}\n--- stderr\n{created.stderr[-TAIL:]}"
    written = sorted(backups_dir(data).glob("*.zip"))
    assert len(written) == 1, f"create writes one archive in <data dir>/backups/: {[path.name for path in written]}"
    assert [path.name for path in jobs_dir(data).iterdir() if path.name != ".lock"] == [], "the job's folder is removed"
    with zipfile.ZipFile(written[0]) as zf:
        manifest = BackupManifest.from_bytes(zf.read(MANIFEST_ENTRY))
    assert (manifest.origin, manifest.app_version, manifest.alembic_revision) == ("cli", APP_VERSION, REVISION), f"the archive was made by the CLI of this test: {manifest.origin}, {manifest.app_version}, {manifest.alembic_revision}"
    inspected = script("inspect", str(written[0]), env=env, cwd=tmp_path)
    assert inspected.returncode == 0 and "Every entry matches the manifest" in inspected.stdout, f"inspect must exit 0 on it\n--- stdout\n{inspected.stdout[-TAIL:]}\n--- stderr\n{inspected.stderr[-TAIL:]}"
    print_success(f"create → {written[0].name}, inspect → 0")


def test_the_script_without_a_command_exits_1(tmp_path):
    done = script(env=child_env(tmp_path / "data"), cwd=tmp_path)
    assert done.returncode == 1 and "backup command required" in done.stdout, f"no command: exit 1 and a hint, got {done.returncode}\n{done.stdout[-TAIL:]}{done.stderr[-TAIL:]}"
    print_success("no command → exit 1")

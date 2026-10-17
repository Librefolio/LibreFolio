"""
The «secure» backup on the command line (workstream B, lot B4, contract §6): ``dev.py backup create`` with a password,
``inspect`` and ``restore --dry-run`` of an envelope (``.lfbk``), and the new ``decrypt``.

Written before the code (red until lot B4 lands): the password options and the ``decrypt`` command do not exist yet, so
argparse refuses them (exit 2); the envelope module (contract §1), with which the tests seal their inputs and open what
the commands write, is imported inside the tests that need it, so the file collects and each test fails on its own. The
messages are not final: the tests pin exit codes, what is on disk, and the stable codes on a ❌ line, never whole lines
but those ``inspect`` and a dry run already print for a zip (``test_backup_cli.py``), which an envelope must print too.

(a) A password never comes from an argument. Each of ``--password-file F`` and ``--password-stdin`` is accepted alone by
    ``create``, ``inspect``, ``restore`` and ``decrypt``; the two together are an argparse error (exit 2), in either
    order. ``--password X`` is an argparse error (exit 2) on each command, and X ends up in no file.
(b) ``create --password-file F`` (F: the password and a line break; a BOM and a CRLF too) or ``--password-stdin`` (one
    line), ``--encrypt`` or not: exit 0, one archive in ``<data dir>/backups/``, ``librefolio-backup-YYYYMMDD-HHMMSS.lfbk``,
    0600, its first bytes ``LFBK``, named on a ✅ line. The password without its line break (and BOM) unlocks it, and it
    holds a backup made by the command line that ``check_archive`` accepts. No clear archive is left in the data
    directory, nor a job folder; no file of the data directory holds the password; nothing is asked.
(c) ``create --encrypt`` without a terminal or a source: exit 1, a ❌ line naming ``password_required``, nothing written,
    nothing asked; the password waiting on standard input is not read without ``--password-stdin``. At a terminal (a
    pty): the password is asked twice through ``getpass``; the same answer twice gives an envelope it unlocks, two
    different answers exit 1 and write nothing.
(d) A weak password (from a file): exit 1, a ❌ line naming ``password_too_weak`` and the rules failed in the rules' order
    (``password_too_weak: min_length, digit``). The archive rules are A's (decision 37) with a minimum of 12 characters
    (P12): 11 characters that meet A's rules are refused. A password file that is blank or missing: a ❌ line and exit 1,
    never a traceback. Nothing written in either case.
(e) ``inspect ENVELOPE`` with either source: exit 0, the summary ``inspect`` prints for the zip it holds, line for line and
    in the same order (its first line, which names the file, aside; other lines may come between). ``inspect ZIP`` with
    either source: the source is ignored, exit 0, the zip's own output.
(f) ``restore ENVELOPE --dry-run`` with either source: exit 0, the report a dry run prints for the zip it holds (as
    ``test_backup_cli.py`` pins it), the copy removed, the live data directory as it was.
(g) ``inspect`` and ``restore --dry-run`` that cannot open the envelope: another password → ``wrong_password``; no source
    and no terminal → ``password_required`` (the right password waiting on standard input all the same); the last chunk
    of a two-chunk envelope altered, so that a whole chunk is decrypted before the failure → ``envelope_damaged``. Exit
    1, the code on a ❌ line, no copy left in ``.restore/stage``, the live database as it was (and, for the dry run, the
    whole data directory but ``.restore``).
    On success (e, f) and refusal (g) alike, no clear archive is left in the data directory — a file named ``*.zip`` or
    ``*.part``, or starting with a zip's first bytes, that was not there before (§6: the decrypted zip lives in a
    private folder of the data directory, removed at the end) — nor in the system's temporary folder.
(h) ``decrypt ENVELOPE -o OUT`` with either source: exit 0, OUT byte for byte the zip that was sealed, 0600, alone in
    its folder (no ``.part`` left), and ``inspect`` accepts it. OUT already there: exit 1, a ❌ line, OUT untouched. A
    zip given to ``decrypt``: exit 1, ``not_an_envelope``, OUT not created. Another password, no source without a
    terminal, a damaged envelope: exit 1, the code, OUT not created, no ``.part`` left.
(i) The script: ``python scripts/backup_cli.py create --password-stdin``, then ``inspect``, ``restore --dry-run`` and
    ``decrypt`` of the envelope it wrote with ``--password-file``, each exit 0: the password is on no stream of any of
    the four processes and in no file of the data directory, where no clear archive is left. ``create --encrypt`` in a
    process without a terminal, the password waiting on its standard input: exit 1, ``password_required``, no backup.
(j) Security review, a hard kill: ``inspect`` of an envelope decrypts into ``<data dir>/backups/.decrypt-<random>/``,
    which a killed ``inspect`` leaves behind with a clear archive inside. When ``inspect`` of an envelope makes its own
    folder, it first removes every ``backups/.decrypt-*`` FOLDER last modified more than an hour (3600 s) ago — one
    left while checking (``archive.zip``), one while decrypting (``archive.zip.part``), two hours old — and nothing
    else. A younger one, just made or 50 minutes old, stays: another ``inspect`` may be using it. An entry that is not
    a plain folder is neither followed nor removed, however old: a link to a folder outside the data directory (the
    link, its folder and the folder's file two hours old), a file named ``.decrypt-file``. A job folder of
    ``backups/.jobs/`` and the earlier backups beside it (a ``.zip``, an ``.lfbk``), two hours old, stay too. Each
    entry kept as it was, to its mode and modification time; ``inspect`` exits 0 as before, its own folder removed.

No password — a weak, a wrong or a second one included — reaches stdout or stderr of any run.

Pure, as ``test_backup_cli.py``, whose fixtures and helpers are imported: data directories under ``tmp_path`` seen
through ``LIBREFOLIO_DATA_DIR`` (production mode, checked); the inputs (archives, envelopes, password files) and the
decrypted files outside them. The commands run in this process through the parser ``register_subparser`` builds, as
``dev.py backup`` runs them; the script in a child with this process's environment without ``LIBREFOLIO_*`` and
``COVERAGE_*``, in a session of its own (no controlling terminal). Without a terminal ``sys.stdin`` is a pipe, a
terminal is a pty (as in ``test_backup_cli_restore.py``). ``getpass`` reads ``/dev/tty``, not ``sys.stdin``: in every
test it is replaced by a stand-in that records its prompts and answers as a closed terminal does (EOF), or with the
answers a terminal test types, so that no prompt ever waits on the terminal the suite runs in. Python's temporary folder
is moved under ``tmp_path`` where a test looks for clear copies. The tests seal their envelopes at scrypt's lowest
accepted cost (``log2_n=14``); the restore cases use the real database at the head made once for the module by
``alembic upgrade``. The ages the sweep of (j) reads are set with ``os.utime`` — a link's own with
``follow_symlinks=False``, never its target's — and checked before the run. POSIX-only (pty, modes, links).
"""

from __future__ import annotations

import argparse
import getpass
import importlib
import os
import pty
import random
import re
import shlex
import shutil
import sqlite3
import stat
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterator
from contextlib import closing, contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from backend.app.services.accounts.password_policy import failed_rules
from backend.app.services.platform.instance_backup.archive import build_archive, check_archive
from backend.app.services.platform.instance_backup.paths import DATABASE_ENTRY, backups_dir, ensure_private_dir
from backend.test_scripts.test_utilities import test_backup_cli as cli
from backend.test_scripts.test_utils import print_section, print_success
from scripts import backup_cli

pytestmark = pytest.mark.skipif(os.name == "nt", reason="a terminal is a pty, and file modes are POSIX only")

# The fixtures of the command line's tests, re-exported: ``app_version`` (autouse) and the real database at the head.
app_version = cli.app_version
head_database = cli.head_database

#: Lot B4's envelope (contract §1): imported by the tests that need it, so that this file collects before it exists.
ENVELOPE_MODULE = "backend.app.services.platform.instance_backup.envelope"
#: The first bytes of an envelope, and of a zip.
ENVELOPE_MAGIC = b"LFBK"
ZIP_MAGIC = b"PK\x03\x04"
#: scrypt's cost for the envelopes the tests seal (``encrypt_file(..., log2_n=)``): the lowest a reader accepts (§0).
TEST_LOG2_N = 14
#: The archive rules' minimum length (P12): A's rules, with at least this many characters.
ARCHIVE_MINIMUM_LENGTH = 12
#: The name of the archive ``create`` writes with a password (§4).
ENVELOPE_NAME = re.compile(r"librefolio-backup-\d{8}-\d{6}\.lfbk")
#: Not real secrets: a password the archive rules accept, two others, and one typed as an argument.
PASSWORD = "Correct-Horse-Battery-9"
WRONG_PASSWORD = "Wrong-Horse-Battery-8"
OTHER_PASSWORD = "Another-Horse-Battery-7"
ARGUMENT_PASSWORD = "Typed-On-The-Command-Line-5"
#: The line ``inspect`` closes a verified archive with.
VERIFIED_LINE = "✅ Every entry matches the manifest"
#: What a user keeps in the file ``decrypt`` is told to write.
KEPT = b"a file the user keeps"
#: The commands that take a password source (§6).
COMMANDS = ["create", "inspect", "restore", "decrypt"]
#: The two sources of a password, for the commands that read one.
SOURCES = [pytest.param("file", id="password-file"), pytest.param("stdin", id="password-stdin")]


# =============================================================================
# The envelope, the inputs
# =============================================================================


def envelope() -> ModuleType:
    """Lot B4's envelope (contract §1), imported when a test needs it."""
    return importlib.import_module(ENVELOPE_MODULE)


def password_file(folder: Path, content: str, name: str = "password.txt") -> Path:
    """A password file holding ``content`` (UTF-8, as given), readable by its owner only, outside the data directory."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_bytes(content.encode("utf-8"))
    path.chmod(0o600)
    return path


def given(source: str, folder: Path, password: str = PASSWORD) -> tuple[list[str], str]:
    """How ``password`` reaches a command through ``source``: the arguments, and what standard input holds."""
    if source == "file":
        return ["--password-file", str(password_file(folder, f"{password}\n"))], ""
    return ["--password-stdin"], f"{password}\n"


def clear_archive(folder: Path, *, big: bool = False) -> Path:
    """A backup archive (a zip) of a small data directory of its own under ``folder``, outside the data directory the
    commands see. ``big``: one more file of random bytes, so that the archive is longer than a chunk of an envelope."""
    source = cli.make_data_dir(folder / "source")
    if big:
        (source / "custom-uploads" / "big.bin").write_bytes(random.Random(4).randbytes(envelope().CHUNK_SIZE + (64 << 10)))
    work = folder / "work"
    work.mkdir()
    return build_archive(source, work, work / cli.NAME, origin="cli").path


def sealed(clear: Path, folder: Path, password: str = PASSWORD) -> Path:
    """``clear`` sealed in an envelope, ``folder/backup.lfbk``, at the tests' scrypt cost."""
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / "backup.lfbk"
    envelope().encrypt_file(clear, target, password, log2_n=TEST_LOG2_N)
    return target


def damage_the_last_chunk(path: Path) -> None:
    """The last byte of the last chunk's ciphertext inverted, the first chunk intact: whoever decrypts the envelope at
    ``path`` writes a whole chunk of the zip before the failure."""
    module = envelope()
    raw = bytearray(path.read_bytes())
    assert len(raw) > module.HEADER_SIZE + module.CHUNK_SIZE + module.TAG_SIZE, f"precondition: an envelope of two chunks at least, so that a chunk is decrypted before the damaged one: {len(raw)} bytes"
    raw[-(module.TAG_SIZE + 1)] ^= 0xFF
    path.write_bytes(bytes(raw))


def unlocked(path: Path, password: str) -> Any:
    """The key of the envelope at ``path``: ``password``, as given, must open it."""
    module = envelope()
    try:
        return module.unlock(path, password)
    except module.EnvelopeError as exc:
        pytest.fail(f"{path.name} must open with the password, without the line break or the byte order mark of its source: {exc.code}")


def opened(path: Path, password: str, folder: Path) -> Path:
    """The archive the envelope at ``path`` holds, decrypted with ``password`` into ``folder``."""
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / "opened.zip"
    envelope().decrypt_file(path, target, unlocked(path, password))
    return target


def holds_a_backup_of_the_cli(path: Path, password: str, folder: Path) -> None:
    """``path`` is an envelope that ``password`` opens, and what it holds is a whole backup archive made by the command line."""
    assert starts_with(path, ENVELOPE_MAGIC) and envelope().is_envelope(path), f"{path.name} is an envelope, its first bytes {ENVELOPE_MAGIC!r}: {path.read_bytes()[:8]!r}"
    check = check_archive(opened(path, password, folder))
    assert check.ok and check.manifest.origin == "cli", f"it holds a backup archive made by the command line, whole: {check}"


# =============================================================================
# The data directories, what is on disk
# =============================================================================


def instance(tmp_path: Path, monkeypatch) -> Path:
    """The data directory the commands see (production mode, checked), with its own small database and files."""
    return cli.point_at(monkeypatch, cli.make_data_dir(tmp_path / "instance"))


def instance_at_head(root: Path, database: Path) -> Path:
    """A data directory whose database is a copy of ``database`` (at the head) with the accounts of ``cli.RESTORE_ACCOUNTS``,
    and ``cli.FILES``: what ``cli.restorable`` archives, kept as a data directory so that the script backs it up itself."""
    data = cli.make_data_dir(root, database=False)
    (data / DATABASE_ENTRY).parent.mkdir(parents=True)
    shutil.copyfile(database, data / DATABASE_ENTRY)
    with closing(sqlite3.connect(data / DATABASE_ENTRY)) as conn, conn:
        conn.executemany(
            "INSERT INTO users (username, email, hashed_password, is_active, is_superuser, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(name, f"{name}@example.test", "$argon2id$not-a-real-hash", active, admin, cli.CREATED, cli.CREATED) for name, active, admin in cli.RESTORE_ACCOUNTS],
        )
    return data.resolve()


@pytest.fixture
def system_temp(monkeypatch, tmp_path) -> Path:
    """The system's temporary folder as Python's ``tempfile`` sees it, moved under ``tmp_path``: a clear archive written
    there instead of the private folder of the data directory (§6) is seen."""
    folder = tmp_path / "system-temp"
    folder.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(folder))
    return folder


def starts_with(path: Path, magic: bytes) -> bool:
    with path.open("rb") as handle:
        return handle.read(len(magic)) == magic


def clear_copies(root: Path) -> set[str]:
    """The files under ``root`` that are, or may be, a clear archive: named ``*.zip`` or ``*.part``, or starting with a
    zip's first bytes."""
    return {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file() and not path.is_symlink() and (path.suffix in (".zip", ".part") or starts_with(path, ZIP_MAGIC))}


def holding(root: Path, secret: str) -> list[str]:
    """The files under ``root`` whose bytes hold ``secret`` (UTF-8)."""
    needle = secret.encode("utf-8")
    return sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file() and not path.is_symlink() and needle in path.read_bytes())


def written_archives(root: Path) -> list[Path]:
    """The archives in ``<data dir>/backups/``, its job folder aside."""
    folder = backups_dir(root)
    return sorted(path for path in folder.iterdir() if path.is_file()) if folder.is_dir() else []


def output_path(tmp_path: Path) -> Path:
    """Where ``decrypt`` is told to write, outside the data directory: a file not there yet, in an empty folder of its own."""
    folder = tmp_path / "out"
    folder.mkdir()
    return folder / "decrypted.zip"


def the_envelope_written(root: Path, out: str) -> Path:
    """The one archive ``create`` wrote: an envelope in ``<data dir>/backups/``, named as §4 says, readable by its owner
    only, named on a ✅ line of ``out``; no clear archive left in the data directory, no job folder."""
    archives = written_archives(root)
    assert len(archives) == 1 and ENVELOPE_NAME.fullmatch(archives[0].name), f"one archive in backups/, librefolio-backup-YYYYMMDD-HHMMSS.lfbk: {[path.name for path in archives]}"
    archive = archives[0]
    mode = stat.S_IMODE(archive.stat().st_mode)
    assert mode == 0o600, f"the archive is readable by its owner only (0600), not {oct(mode)}"
    assert [line for line in out.splitlines() if line.startswith("✅") and str(archive) in line], f"a ✅ line names {archive}: {out[-cli.TAIL:]}"
    assert clear_copies(root) == set(), f"no clear archive is left in the data directory (§4: the zip removed): {sorted(clear_copies(root))}"
    assert cli.job_folders(root) == [], f"the job's folder is removed: {cli.job_folders(root)}"
    return archive


# =============================================================================
# The commands, the terminal
# =============================================================================


@dataclass(frozen=True)
class Ran:
    """What one command did: its exit code, and what it printed on each stream."""

    code: int | str | None
    out: str
    err: str

    @property
    def text(self) -> str:
        return f"{self.out}{self.err}"

    @property
    def refused(self) -> list[str]:
        """Its ❌ lines: how this command line refuses."""
        return [line for line in self.text.splitlines() if line.startswith("❌")]

    def refusals(self, code: str) -> list[str]:
        """Its ❌ lines naming ``code``."""
        return [line for line in self.refused if code in line]


def backup_parser() -> argparse.ArgumentParser:
    """``dev.py``'s parser with the ``backup`` group, as ``register_subparser`` declares it."""
    parser = argparse.ArgumentParser(prog="dev.py")
    backup_cli.register_subparser(parser.add_subparsers(dest="command"))
    return parser


def run(capsys, *argv: str) -> Ran:
    """``dev.py backup <argv>`` in this process: parsed as ``register_subparser`` declares it, then run. An argument the
    command line does not take, or an exception escaping the command (a traceback for the user), fails the test."""
    capsys.readouterr()
    try:
        args = backup_parser().parse_args(["backup", *argv])
    except SystemExit as exc:
        pytest.fail(f"dev.py backup {shlex.join(argv)}: the command line does not take these arguments (argparse exit {exc.code}): {capsys.readouterr().err[-cli.TAIL:]}")
    try:
        code = args.func(args)
    except Exception as exc:
        pytest.fail(f"dev.py backup {shlex.join(argv)} raised {type(exc).__name__} ({exc}): the user would get a traceback instead of a message and exit code 1")
    captured = capsys.readouterr()
    return Ran(code, captured.out, captured.err)


def refused_by_argparse(capsys, *argv: str) -> Ran:
    """``dev.py backup <argv>`` refused while its arguments are read: argparse's exit code and message; nothing runs."""
    capsys.readouterr()
    try:
        backup_parser().parse_args(["backup", *argv])
    except SystemExit as exc:
        captured = capsys.readouterr()
        return Ran(exc.code, captured.out, captured.err)
    pytest.fail(f"dev.py backup {shlex.join(argv)} was accepted: argparse must refuse it")


def accepts(capsys, *argv: str) -> None:
    """Precondition: the arguments of ``dev.py backup <argv>`` are read without an error (nothing runs)."""
    capsys.readouterr()
    try:
        backup_parser().parse_args(["backup", *argv])
    except SystemExit as exc:
        pytest.fail(f"precondition: dev.py backup {shlex.join(argv)} must be accepted (lot B4's password sources, §6): argparse exit {exc.code}: {capsys.readouterr().err[-cli.TAIL:]}")


def command(name: str, tmp_path: Path) -> list[str]:
    """``name`` and its arguments before a password source (§6); only the arguments are read, the files need not exist."""
    archive = str(tmp_path / "inputs" / "backup.lfbk")
    return {"create": ["create"], "inspect": ["inspect", archive], "restore": ["restore", archive, "--dry-run"], "decrypt": ["decrypt", archive, "-o", str(tmp_path / "out" / "decrypted.zip")]}[name]


def not_shown(ran: Ran, *secrets: str) -> None:
    """No password reaches the terminal: neither stream holds one."""
    shown = [secret for secret in secrets if secret in ran.text]
    assert shown == [], f"a password reached the terminal: {shown} in {ran.text[-cli.TAIL:]}"


@contextmanager
def stdin_holding(monkeypatch, text: str) -> Iterator[None]:
    """``sys.stdin`` a pipe, not a terminal, holding ``text`` and then its end."""
    read_end, write_end = os.pipe()
    os.write(write_end, text.encode("utf-8"))
    os.close(write_end)
    reader = open(read_end, encoding="utf-8")
    monkeypatch.setattr(sys, "stdin", reader)
    try:
        yield
    finally:
        reader.close()


@contextmanager
def at_a_terminal(monkeypatch) -> Iterator[None]:
    """``sys.stdin`` a terminal (a pty), as ``test_backup_cli_restore.py`` makes one. A few empty lines wait in it: a
    command that read the password from it instead of asking through ``getpass`` would get an empty line, not wait."""
    keep, read_end = pty.openpty()
    os.write(keep, b"\n" * 4)
    reader = open(read_end, encoding="utf-8")
    monkeypatch.setattr(sys, "stdin", reader)
    try:
        yield
    finally:
        reader.close()
        os.close(keep)


def prompt_with(monkeypatch, stand_in) -> None:
    """``getpass.getpass`` replaced by ``stand_in``, and ``backup_cli.getpass`` too when the module imported the function."""
    monkeypatch.setattr(getpass, "getpass", stand_in)
    if callable(getattr(backup_cli, "getpass", None)):
        monkeypatch.setattr(backup_cli, "getpass", stand_in)


@pytest.fixture(autouse=True)
def prompts(monkeypatch) -> list[str]:
    """No test has a terminal to type on unless it makes one: ``getpass``, which reads ``/dev/tty`` and not
    ``sys.stdin``, answers as a closed terminal does (``EOFError``), so that no prompt waits on the terminal the suite runs
    in. The prompts it was called with: a test that gives a source, or has no terminal, expects none."""
    asked: list[str] = []

    def closed_terminal(prompt: str = "Password: ", *args: Any, **kwargs: Any) -> str:
        asked.append(prompt)
        raise EOFError

    prompt_with(monkeypatch, closed_terminal)
    return asked


def answering(monkeypatch, *answers: str) -> list[str]:
    """A terminal on which ``answers`` are typed, one for each ``getpass`` call, then Ctrl-D (``EOFError``): the prompts."""
    asked: list[str] = []

    def terminal(prompt: str = "Password: ", *args: Any, **kwargs: Any) -> str:
        asked.append(prompt)
        if len(asked) > len(answers):
            raise EOFError
        return answers[len(asked) - 1]

    prompt_with(monkeypatch, terminal)
    return asked


def script(*argv: str, env: dict[str, str], cwd: Path, typed: str | None = None) -> subprocess.CompletedProcess:
    """``python scripts/backup_cli.py <argv>`` as ``test_backup_cli.py`` runs it, ``typed`` on its standard input (a pipe;
    ``None``: ``/dev/null``). In a session of its own: without a controlling terminal, a ``getpass`` the command should
    not call cannot wait on the terminal the suite runs in."""
    command_line = [sys.executable, str(cli.SCRIPT), *argv]
    stdin: dict[str, Any] = {"stdin": subprocess.DEVNULL} if typed is None else {"input": typed}
    try:
        return subprocess.run(command_line, cwd=cwd, env=env, capture_output=True, encoding="utf-8", errors="replace", timeout=cli.CLI_TIMEOUT, check=False, start_new_session=True, **stdin)
    except subprocess.TimeoutExpired as exc:
        pytest.fail(f"`{shlex.join(command_line)}` did not end within {cli.CLI_TIMEOUT}s: {exc.stdout!r} {exc.stderr!r}")


def streams(done: subprocess.CompletedProcess) -> str:
    return f"exit {done.returncode}\n--- stdout\n{done.stdout[-cli.TAIL:]}\n--- stderr\n{done.stderr[-cli.TAIL:]}"


# =============================================================================
# (a) Password sources, never an argument
# =============================================================================


@pytest.mark.parametrize("name", COMMANDS)
def test_the_two_password_sources_exclude_each_other(tmp_path, capsys, name):
    """(a) §6: each source alone is accepted by every command that reads a password; the two together are an argparse
    error, in either order."""
    print_section("Password sources")
    base = command(name, tmp_path)
    file = str(tmp_path / "inputs" / "password.txt")
    accepts(capsys, *base, "--password-file", file)
    accepts(capsys, *base, "--password-stdin")
    for both in (["--password-file", file, "--password-stdin"], ["--password-stdin", "--password-file", file]):
        refused = refused_by_argparse(capsys, *base, *both)
        assert refused.code == 2, f"{name} {shlex.join(both)}: an argparse error, exit 2, not {refused.code}: {refused.err[-cli.TAIL:]}"
    print_success(f"{name}: --password-file and --password-stdin exclude each other")


@pytest.mark.parametrize("name", COMMANDS)
def test_a_password_is_never_an_argument(tmp_path, monkeypatch, capsys, name):
    """(a) §6, «never an argument» (``ps``, the shell's history): ``--password X`` is an argparse error on every command,
    while the two sources are there (checked first: the refusal is not that of a command line without them). Nothing
    runs, so X is in no file."""
    root = instance(tmp_path, monkeypatch)
    before = cli.listing(root)
    base = command(name, tmp_path)
    accepts(capsys, *base, "--password-file", str(tmp_path / "inputs" / "password.txt"))
    refused = refused_by_argparse(capsys, *base, "--password", ARGUMENT_PASSWORD)
    assert refused.code == 2, f"{name} --password X: an argparse error, exit 2, not {refused.code}: {refused.err[-cli.TAIL:]}"
    assert cli.listing(root) == before, f"nothing written: {sorted(set(cli.listing(root)) - set(before))}"
    assert holding(tmp_path, ARGUMENT_PASSWORD) == [], f"the password typed as an argument is in a file: {holding(tmp_path, ARGUMENT_PASSWORD)}"
    print_success(f"{name} --password X → exit 2, in no file")


# =============================================================================
# (b) create with a password
# =============================================================================


#: How ``create`` gets its password (§6): its arguments (``{file}``: the password file's path), what the file holds
#: (``None``: no file) and what standard input holds. ``--encrypt`` is implied by a source, and allowed with it.
CREATE_SOURCES = [
    pytest.param(["--password-file", "{file}"], f"{PASSWORD}\n", "", id="file"),
    pytest.param(["--password-file", "{file}"], f"\ufeff{PASSWORD}\r\n", "", id="file-with-bom-and-crlf"),
    pytest.param(["--encrypt", "--password-file", "{file}"], f"{PASSWORD}\n", "", id="encrypt-and-file"),
    pytest.param(["--password-stdin"], None, f"{PASSWORD}\n", id="stdin"),
    pytest.param(["--encrypt", "--password-stdin"], None, f"{PASSWORD}\n", id="encrypt-and-stdin"),
]


@pytest.mark.parametrize(("flags", "in_file", "typed"), CREATE_SOURCES)
def test_create_with_a_password_writes_an_envelope_the_password_opens(tmp_path, monkeypatch, capsys, prompts, flags, in_file, typed):
    """(b) §4, §6: one ``.lfbk`` in ``backups/``, 0600, named on a ✅ line; the password without the line break (and the
    BOM) of its source opens it, and it holds the backup; no clear zip, no job folder, no file holding the password."""
    print_section("dev.py backup create, with a password")
    assert failed_rules(PASSWORD) == [] and len(PASSWORD) >= ARCHIVE_MINIMUM_LENGTH, f"precondition: the password meets the archive rules: {failed_rules(PASSWORD)}"
    root = instance(tmp_path, monkeypatch)
    file = password_file(tmp_path / "inputs", in_file) if in_file is not None else None
    argv = [str(file) if flag == "{file}" else flag for flag in flags]
    with stdin_holding(monkeypatch, typed):
        ran = run(capsys, "create", *argv)
    assert ran.code == 0, f"create {' '.join(flags)}: exit 0, not {ran.code}: {ran.text[-cli.TAIL:]}"
    archive = the_envelope_written(root, ran.out)
    holds_a_backup_of_the_cli(archive, PASSWORD, tmp_path / "opened")
    assert holding(root, PASSWORD) == [], f"no file of the data directory holds the password: {holding(root, PASSWORD)}"
    assert prompts == [], f"a source was given: nothing is asked: {prompts}"
    not_shown(ran, PASSWORD)
    print_success(f"{' '.join(flags)} → {archive.name}")


# =============================================================================
# (c) No terminal, a terminal
# =============================================================================


def test_create_encrypt_without_a_terminal_or_a_source_is_refused_and_writes_nothing(tmp_path, monkeypatch, capsys, prompts):
    """(c) §6: nobody to ask and nothing given. The password waiting on standard input is not read: only
    ``--password-stdin`` reads it."""
    print_section("dev.py backup create --encrypt, no source")
    root = instance(tmp_path, monkeypatch)
    before = cli.listing(root)
    with stdin_holding(monkeypatch, f"{PASSWORD}\n"):
        ran = run(capsys, "create", "--encrypt")
    assert ran.code == 1 and ran.refusals("password_required"), f"exit 1, a ❌ line naming password_required: exit {ran.code}: {ran.text[-cli.TAIL:]}"
    assert cli.listing(root) == before, f"nothing written: {sorted(set(cli.listing(root)) - set(before))}"
    assert prompts == [], f"nothing is asked without a terminal: {prompts}"
    not_shown(ran, PASSWORD)
    print_success("--encrypt, no terminal, no source → password_required, nothing written")


def test_create_encrypt_at_a_terminal_asks_the_password_twice(tmp_path, monkeypatch, capsys):
    """(c) §6: at a terminal without a source, ``getpass`` asks twice for ``create``; the same answer twice seals the
    backup with it."""
    root = instance(tmp_path, monkeypatch)
    asked = answering(monkeypatch, PASSWORD, PASSWORD)
    with at_a_terminal(monkeypatch):
        ran = run(capsys, "create", "--encrypt")
    assert ran.code == 0, f"the same password typed twice: exit 0, not {ran.code}: {ran.text[-cli.TAIL:]}"
    assert len(asked) == 2, f"asked twice through getpass: {asked}"
    holds_a_backup_of_the_cli(the_envelope_written(root, ran.out), PASSWORD, tmp_path / "opened")
    not_shown(ran, PASSWORD)
    print_success("a terminal: asked twice, sealed")


def test_create_encrypt_at_a_terminal_with_two_different_answers_writes_nothing(tmp_path, monkeypatch, capsys):
    """(c) The second answer is there to catch a typing mistake: two different answers seal nothing (asked again or
    not, a terminal that ends gives up)."""
    root = instance(tmp_path, monkeypatch)
    before = cli.listing(root)
    asked = answering(monkeypatch, PASSWORD, OTHER_PASSWORD)
    with at_a_terminal(monkeypatch):
        ran = run(capsys, "create", "--encrypt")
    assert ran.code == 1 and ran.refused, f"two different answers: exit 1 and a ❌ line, not {ran.code}: {ran.text[-cli.TAIL:]}"
    assert len(asked) >= 2, f"both answers asked before they are compared: {asked}"
    assert cli.listing(root) == before, f"nothing written: {sorted(set(cli.listing(root)) - set(before))}"
    not_shown(ran, PASSWORD, OTHER_PASSWORD)
    print_success("a terminal, two different answers → exit 1, nothing written")


# =============================================================================
# (d) A password refused
# =============================================================================


#: Passwords the archive rules refuse (A's five rules, at least 12 characters: P12), and the codes of the rules they
#: fail, in the rules' order.
WEAK = [
    pytest.param("Short-Pass1", ["min_length"], id="eleven-characters-meeting-the-account-rules"),
    pytest.param("Short-Pass", ["min_length", "digit"], id="short-without-a-digit"),
    pytest.param("correcthorsebattery", ["uppercase", "digit", "special"], id="long-lowercase-only"),
]


@pytest.mark.parametrize(("weak", "failed"), WEAK)
def test_create_with_a_weak_password_names_the_rules_it_fails_and_writes_nothing(tmp_path, monkeypatch, capsys, prompts, weak, failed):
    """(d) §6: ``❌ … (password_too_weak: min_length, digit)``, exit 1, nothing written. A's rules, read from A's module
    first, fail the same codes but the minimum length: the archive's raise it to 12."""
    print_section("dev.py backup create, a password refused")
    assert failed_rules(weak) == [code for code in failed if code != "min_length"], f"precondition: A's rules (decision 37) fail {failed_rules(weak)} for this password; the archive's add only the minimum of {ARCHIVE_MINIMUM_LENGTH} characters"
    root = instance(tmp_path, monkeypatch)
    before = cli.listing(root)
    file = password_file(tmp_path / "inputs", f"{weak}\n")
    with stdin_holding(monkeypatch, ""):
        ran = run(capsys, "create", "--password-file", str(file))
    said = f"password_too_weak: {', '.join(failed)}"
    assert ran.code == 1 and ran.refusals(said), f"exit 1, a ❌ line naming ({said}): exit {ran.code}: {ran.text[-cli.TAIL:]}"
    assert cli.listing(root) == before, f"nothing written: {sorted(set(cli.listing(root)) - set(before))}"
    assert prompts == [], f"a source was given: nothing is asked: {prompts}"
    not_shown(ran, weak)
    print_success(f"({said}), nothing written")


@pytest.mark.parametrize("case", ["blank", "missing"])
def test_create_with_a_password_file_that_gives_no_password_is_refused_and_writes_nothing(tmp_path, monkeypatch, capsys, case):
    """(d) §6: the file is read with ``config.read_secret_file``, which refuses a file of spaces and line breaks, and a
    missing one: a ❌ line and exit 1, never a traceback; nothing written."""
    root = instance(tmp_path, monkeypatch)
    before = cli.listing(root)
    inputs = tmp_path / "inputs"
    file = password_file(inputs, " \n\n") if case == "blank" else inputs / "absent.txt"
    with stdin_holding(monkeypatch, ""):
        ran = run(capsys, "create", "--password-file", str(file))
    assert ran.code == 1 and ran.refused, f"a {case} password file: exit 1 and a ❌ line, not {ran.code}: {ran.text[-cli.TAIL:]}"
    assert cli.listing(root) == before, f"nothing written: {sorted(set(cli.listing(root)) - set(before))}"
    print_success(f"{case} password file → exit 1, nothing written")


# =============================================================================
# (e) inspect
# =============================================================================


def summary(out: str) -> list[str]:
    """What ``inspect`` says of an archive: its lines but the first (``📦 <the file>``) and the blank ones."""
    return [line for line in out.splitlines() if line.strip() and not line.startswith("📦")]


def in_order(expected: list[str], lines: list[str]) -> bool:
    """Whether each line of ``expected`` is one of ``lines``, in the same order; other lines may come between."""
    remaining = iter(lines)
    return all(any(line == wanted for line in remaining) for wanted in expected)


@pytest.mark.parametrize("source", SOURCES)
def test_inspect_of_an_envelope_shows_the_summary_of_the_archive_it_holds(tmp_path, monkeypatch, capsys, prompts, system_temp, source):
    """(e)(g) §6: the summary ``inspect`` prints for the sealed zip, line for line, in order; the zip decrypted for it
    is gone, from the data directory and from the system's temporary folder."""
    print_section("dev.py backup inspect, an envelope")
    root = instance(tmp_path, monkeypatch)
    clear = clear_archive(tmp_path / "backup")
    path = sealed(clear, tmp_path / "inputs")
    plain = run(capsys, "inspect", str(clear))
    assert plain.code == 0 and VERIFIED_LINE in plain.out, f"precondition: inspect of the zip exits 0: {plain.text[-cli.TAIL:]}"
    copies = clear_copies(root)
    flags, typed = given(source, tmp_path / "inputs")
    with stdin_holding(monkeypatch, typed):
        ran = run(capsys, "inspect", str(path), *flags)
    assert ran.code == 0, f"the right password: exit 0, not {ran.code}: {ran.text[-cli.TAIL:]}"
    assert in_order(summary(plain.out), ran.out.splitlines()), f"the summary of the zip it holds, in order: {summary(plain.out)} in {ran.out[-cli.TAIL:]}"
    assert clear_copies(root) - copies == set() and clear_copies(system_temp) == set(), f"no clear archive left: data directory {sorted(clear_copies(root) - copies)}, system temporary folder {sorted(clear_copies(system_temp))}"
    assert prompts == [], f"a source was given: nothing is asked: {prompts}"
    not_shown(ran, PASSWORD)
    print_success(f"{source}: the zip's summary, no clear copy left")


@pytest.mark.parametrize("source", SOURCES)
def test_inspect_of_a_zip_ignores_the_password_source(tmp_path, monkeypatch, capsys, prompts, source):
    """(e) §6: on a zip the sources are ignored: exit 0, every line ``inspect`` prints without one, in order."""
    instance(tmp_path, monkeypatch)
    clear = clear_archive(tmp_path / "backup")
    plain = run(capsys, "inspect", str(clear))
    assert plain.code == 0 and VERIFIED_LINE in plain.out, f"precondition: inspect of the zip exits 0: {plain.text[-cli.TAIL:]}"
    flags, typed = given(source, tmp_path / "inputs")
    with stdin_holding(monkeypatch, typed):
        ran = run(capsys, "inspect", str(clear), *flags)
    expected = [line for line in plain.out.splitlines() if line.strip()]
    assert ran.code == 0 and in_order(expected, ran.out.splitlines()), f"a zip with a password source: exit 0 and its own output, not {ran.code}: {expected} in {ran.out[-cli.TAIL:]}"
    assert prompts == [], f"nothing is asked: {prompts}"
    not_shown(ran, PASSWORD)
    print_success(f"a zip, {source} ignored")


# =============================================================================
# (f) restore --dry-run
# =============================================================================


def dry_run_report(clear: Path) -> list[str]:
    """What a dry run of the restorable zip ``clear`` prints, as ``test_backup_cli.py`` pins it."""
    return [
        f"📦 Made by LibreFolio {cli.APP_VERSION} (cli)",
        f"   Database: revision {cli.revision_in(clear)}, this LibreFolio's own: restored as it is",
        f"   Files: {len(cli.FILES)}",
        cli.LEDGER_SAME,
        "   Instance key: not included",
        "   Administrators: ada_admin, zoe_admin",
        *cli.ACCOUNT_LINK_LINES,
        cli.RESTORABLE_LINE,
    ]


@pytest.mark.parametrize("source", SOURCES)
def test_a_dry_run_of_an_envelope_reports_what_a_restore_would_do_and_leaves_the_instance_as_it_was(tmp_path, monkeypatch, capsys, prompts, system_temp, head_database, source):
    """(f)(g) §6: the report of the zip it holds, as a dry run prints it for that zip; the copy removed, the data
    directory as it was but ``.restore``, the live database the same; no clear archive left anywhere."""
    print_section("dev.py backup restore --dry-run, an envelope")
    root = instance(tmp_path, monkeypatch)
    clear = cli.restorable(tmp_path / "backup", head_database)
    path = sealed(clear, tmp_path / "inputs")
    before, database, copies = cli.outside_restore(root), cli.sha256_of(root / DATABASE_ENTRY), clear_copies(root)
    flags, typed = given(source, tmp_path / "inputs")
    with stdin_holding(monkeypatch, typed):
        ran = run(capsys, "restore", str(path), "--dry-run", *flags)
    assert ran.code == 0, f"a restorable backup, the right password: exit 0, not {ran.code}: {ran.text[-cli.TAIL:]}"
    missing = [line for line in dry_run_report(clear) if line not in ran.out]
    assert missing == [] and ran.refused == [], f"the dry run's report of the zip it holds: {missing} missing, {ran.refused}: {ran.out[-cli.TAIL:]}"
    assert cli.stages_left(root) == [], f"the copy is removed: {cli.stages_left(root)}"
    assert (cli.outside_restore(root), cli.sha256_of(root / DATABASE_ENTRY)) == (before, database), f"the data directory is as it was: {sorted(set(cli.outside_restore(root)) ^ set(before))}"
    assert clear_copies(root) - copies == set() and clear_copies(system_temp) == set(), f"no clear archive left: data directory {sorted(clear_copies(root) - copies)}, system temporary folder {sorted(clear_copies(system_temp))}"
    assert prompts == [], f"a source was given: nothing is asked: {prompts}"
    not_shown(ran, PASSWORD)
    print_success(f"{source}: dry run → 0, the zip's report, nothing left")


# =============================================================================
# (g) An envelope that cannot be opened
# =============================================================================


#: Why a command cannot open an envelope, by the code that says it (§1, §6).
CANNOT_OPEN = [
    pytest.param("wrong_password", id="wrong-password"),
    pytest.param("password_required", id="no-source-no-terminal"),
    pytest.param("envelope_damaged", id="last-chunk-damaged"),
]


def cannot_open(code: str, tmp_path: Path) -> tuple[Path, list[str], str]:
    """An envelope a command cannot open for ``code``, with the arguments and the standard input of the run: another
    password through a file (``wrong_password``); no source, the right password waiting on standard input all the same
    (``password_required``); the right password, the last chunk of a two-chunk envelope altered (``envelope_damaged``)."""
    inputs = tmp_path / "inputs"
    path = sealed(clear_archive(tmp_path / "backup", big=code == "envelope_damaged"), inputs)
    if code == "envelope_damaged":
        damage_the_last_chunk(path)
    if code == "password_required":
        return path, [], f"{PASSWORD}\n"
    flags, _typed = given("file", inputs, WRONG_PASSWORD if code == "wrong_password" else PASSWORD)
    return path, flags, ""


@pytest.mark.parametrize("code", CANNOT_OPEN)
@pytest.mark.parametrize("name", ["inspect", "restore"])
def test_an_envelope_that_cannot_be_opened_is_refused_with_its_code_and_leaves_no_clear_archive(tmp_path, monkeypatch, capsys, prompts, system_temp, name, code):
    """(g) §6: exit 1, the code on a ❌ line. Nothing decrypted is left — the damaged envelope's first chunk was — in
    the data directory or the system's temporary folder; no copy in ``.restore/stage``; the live database as it was,
    and after a dry run the whole data directory but ``.restore``."""
    print_section(f"dev.py backup {name}, an envelope that cannot be opened")
    root = instance(tmp_path, monkeypatch)
    path, flags, typed = cannot_open(code, tmp_path)
    before, database, copies = cli.outside_restore(root), cli.sha256_of(root / DATABASE_ENTRY), clear_copies(root)
    argv = ["inspect", str(path)] if name == "inspect" else ["restore", str(path), "--dry-run"]
    with stdin_holding(monkeypatch, typed):
        ran = run(capsys, *argv, *flags)
    assert ran.code == 1 and ran.refusals(code), f"{name}: exit 1, a ❌ line naming {code}: exit {ran.code}: {ran.text[-cli.TAIL:]}"
    assert clear_copies(root) - copies == set() and clear_copies(system_temp) == set(), f"no clear archive left: data directory {sorted(clear_copies(root) - copies)}, system temporary folder {sorted(clear_copies(system_temp))}"
    assert cli.stages_left(root) == [] and cli.sha256_of(root / DATABASE_ENTRY) == database, f"no copy left, the live database as it was: {cli.stages_left(root)}"
    if name == "restore":
        assert cli.outside_restore(root) == before, f"a dry run leaves the data directory as it was: {sorted(set(cli.outside_restore(root)) ^ set(before))}"
    assert prompts == [], f"nothing is asked: {prompts}"
    not_shown(ran, PASSWORD, WRONG_PASSWORD)
    print_success(f"{name}: ({code}), nothing left")


# =============================================================================
# (h) decrypt
# =============================================================================


@pytest.mark.parametrize("source", SOURCES)
def test_decrypt_writes_the_archive_the_envelope_holds_readable_by_its_owner_only(tmp_path, monkeypatch, capsys, prompts, system_temp, source):
    """(h) §6: OUT is the zip that was sealed, byte for byte, 0600, alone in its folder (no ``.part``), and ``inspect``
    accepts it; no other clear copy is left."""
    print_section("dev.py backup decrypt")
    root = instance(tmp_path, monkeypatch)
    clear = clear_archive(tmp_path / "backup")
    path = sealed(clear, tmp_path / "inputs")
    out = output_path(tmp_path)
    copies = clear_copies(root)
    flags, typed = given(source, tmp_path / "inputs")
    with stdin_holding(monkeypatch, typed):
        ran = run(capsys, "decrypt", str(path), "-o", str(out), *flags)
    assert ran.code == 0, f"the right password: exit 0, not {ran.code}: {ran.text[-cli.TAIL:]}"
    assert out.is_file() and cli.sha256_of(out) == cli.sha256_of(clear), "OUT is the zip that was sealed, byte for byte"
    mode = stat.S_IMODE(out.stat().st_mode)
    assert mode == 0o600, f"OUT is readable by its owner only (0600), not {oct(mode)}"
    assert sorted(entry.name for entry in out.parent.iterdir()) == [out.name], f"OUT alone in its folder, no .part left: {sorted(entry.name for entry in out.parent.iterdir())}"
    inspected = run(capsys, "inspect", str(out))
    assert inspected.code == 0 and VERIFIED_LINE in inspected.out, f"inspect accepts OUT: {inspected.text[-cli.TAIL:]}"
    assert clear_copies(root) - copies == set() and clear_copies(system_temp) == set(), f"no other clear copy: data directory {sorted(clear_copies(root) - copies)}, system temporary folder {sorted(clear_copies(system_temp))}"
    assert prompts == [], f"a source was given: nothing is asked: {prompts}"
    not_shown(ran, PASSWORD)
    print_success(f"{source}: OUT written 0600, inspect → 0")


def test_decrypt_never_replaces_a_file(tmp_path, monkeypatch, capsys):
    """(h) §6: OUT already there: refused, exit 1, OUT untouched, nothing beside it."""
    instance(tmp_path, monkeypatch)
    path = sealed(clear_archive(tmp_path / "backup"), tmp_path / "inputs")
    out = output_path(tmp_path)
    out.write_bytes(KEPT)
    flags, typed = given("file", tmp_path / "inputs")
    with stdin_holding(monkeypatch, typed):
        ran = run(capsys, "decrypt", str(path), "-o", str(out), *flags)
    assert ran.code == 1 and ran.refused, f"OUT already there: exit 1 and a ❌ line, not {ran.code}: {ran.text[-cli.TAIL:]}"
    assert out.read_bytes() == KEPT, "OUT is untouched"
    assert sorted(entry.name for entry in out.parent.iterdir()) == [out.name], f"nothing written beside OUT: {sorted(entry.name for entry in out.parent.iterdir())}"
    not_shown(ran, PASSWORD)
    print_success("OUT already there → exit 1, untouched")


def test_decrypt_of_a_file_that_is_not_an_envelope_is_refused(tmp_path, monkeypatch, capsys):
    """(h) §6: a zip given to ``decrypt``: exit 1, ``not_an_envelope``, OUT not created."""
    instance(tmp_path, monkeypatch)
    clear = clear_archive(tmp_path / "backup")
    out = output_path(tmp_path)
    flags, typed = given("file", tmp_path / "inputs")
    with stdin_holding(monkeypatch, typed):
        ran = run(capsys, "decrypt", str(clear), "-o", str(out), *flags)
    assert ran.code == 1 and ran.refusals("not_an_envelope"), f"a zip: exit 1, a ❌ line naming not_an_envelope: exit {ran.code}: {ran.text[-cli.TAIL:]}"
    assert list(out.parent.iterdir()) == [], f"OUT not created: {sorted(entry.name for entry in out.parent.iterdir())}"
    not_shown(ran, PASSWORD)
    print_success("a zip → not_an_envelope")


@pytest.mark.parametrize("code", CANNOT_OPEN)
def test_decrypt_that_cannot_open_the_envelope_is_refused_with_its_code_and_writes_nothing(tmp_path, monkeypatch, capsys, prompts, system_temp, code):
    """(h) §1, §6: exit 1, the code on a ❌ line; OUT not created and no ``.part`` left beside it — after a damaged
    envelope's first chunk was decrypted too — nor a clear copy in the system's temporary folder."""
    instance(tmp_path, monkeypatch)
    path, flags, typed = cannot_open(code, tmp_path)
    out = output_path(tmp_path)
    with stdin_holding(monkeypatch, typed):
        ran = run(capsys, "decrypt", str(path), "-o", str(out), *flags)
    assert ran.code == 1 and ran.refusals(code), f"exit 1, a ❌ line naming {code}: exit {ran.code}: {ran.text[-cli.TAIL:]}"
    assert list(out.parent.iterdir()) == [], f"OUT not created, no .part left: {sorted(entry.name for entry in out.parent.iterdir())}"
    assert clear_copies(system_temp) == set(), f"no clear copy in the system temporary folder: {sorted(clear_copies(system_temp))}"
    assert prompts == [], f"nothing is asked: {prompts}"
    not_shown(ran, PASSWORD, WRONG_PASSWORD)
    print_success(f"decrypt: ({code}), nothing written")


# =============================================================================
# (i) The script
# =============================================================================


def test_the_script_creates_inspects_checks_and_decrypts_an_envelope_and_never_prints_the_password(tmp_path, head_database):
    """(i) Four processes, as ``dev.py backup`` runs them: every byte they print is read, logs and warnings included.
    ``create --password-stdin``, then ``inspect``, ``restore --dry-run`` and ``decrypt`` with ``--password-file``."""
    print_section("python scripts/backup_cli.py, an envelope")
    data = instance_at_head(tmp_path / "data", head_database)
    env = cli.child_env(data)
    file = password_file(tmp_path / "inputs", f"{PASSWORD}\n")
    runs = {"create": script("create", "--password-stdin", env=env, cwd=tmp_path, typed=f"{PASSWORD}\n")}
    assert runs["create"].returncode == 0, f"create --password-stdin must exit 0: {streams(runs['create'])}"
    archives = written_archives(data)
    assert len(archives) == 1 and ENVELOPE_NAME.fullmatch(archives[0].name), f"one envelope in backups/: {[path.name for path in archives]}"
    out = output_path(tmp_path)
    for step, argv, said in (
        ("inspect", ["inspect", str(archives[0])], "Every entry matches the manifest"),
        ("restore --dry-run", ["restore", str(archives[0]), "--dry-run"], cli.RESTORABLE_LINE),
        ("decrypt", ["decrypt", str(archives[0]), "-o", str(out)], ""),
    ):
        runs[step] = script(*argv, "--password-file", str(file), env=env, cwd=tmp_path)
        assert runs[step].returncode == 0 and said in runs[step].stdout, f"{step} must exit 0 and say {said!r}: {streams(runs[step])}"
    check = check_archive(out)
    assert check.ok and check.manifest.origin == "cli", f"decrypt wrote the backup the script made: {check}"
    shown = [step for step, done in runs.items() if PASSWORD in f"{done.stdout}{done.stderr}"]
    assert shown == [], f"the password reached a stream of: {shown}"
    assert clear_copies(data) == set() and holding(data, PASSWORD) == [], f"no clear archive, no file holding the password in the data directory: {sorted(clear_copies(data))}, {holding(data, PASSWORD)}"
    print_success("create, inspect, restore --dry-run, decrypt → 0; the password on no stream, in no file")


def test_the_script_without_a_terminal_refuses_to_encrypt_without_a_source(tmp_path):
    """(i) A process with no terminal at all (its own session, standard input a pipe): ``create --encrypt`` refuses,
    the password waiting on its standard input unread, and writes no backup."""
    data = cli.make_data_dir(tmp_path / "data").resolve()
    done = script("create", "--encrypt", env=cli.child_env(data), cwd=tmp_path, typed=f"{PASSWORD}\n")
    refusals = [line for line in f"{done.stdout}{done.stderr}".splitlines() if line.startswith("❌") and "password_required" in line]
    assert done.returncode == 1 and refusals, f"exit 1, a ❌ line naming password_required: {streams(done)}"
    assert not backups_dir(data).exists() and clear_copies(data) == set(), f"no backup written: {cli.listing(data)}"
    assert PASSWORD not in f"{done.stdout}{done.stderr}", "the password reached a stream"
    print_success("no terminal, --encrypt → password_required, no backup")


# =============================================================================
# (j) What a killed inspect left
# =============================================================================


#: Seconds. ``inspect`` of an envelope first removes the ``backups/.decrypt-*`` folders older than this.
SWEEP_AGE = 3600
#: Seconds: two hours. The age of what a killed ``inspect`` left, and of every entry the sweep must leave alone all the same.
OLD = 2 * 3600
#: The folders two killed ``inspect`` runs left, and the clear file in each: one was checking, one decrypting.
STALE = {".decrypt-old": "archive.zip", ".decrypt-killed": "archive.zip.part"}
#: Younger ``.decrypt-*`` folders and their age in seconds, just made or 50 minutes old: another ``inspect`` may be using them.
YOUNG = {".decrypt-new": 0, ".decrypt-recent": 50 * 60}
#: An earlier secure backup, beside the earlier clear one (``cli.NAME``).
EARLIER_ENVELOPE = Path(cli.NAME).with_suffix(".lfbk").name


def aged(path: Path, seconds: float) -> Path:
    """``path`` last modified ``seconds`` ago; for a link, the link itself (where the system allows it), never what it
    points to."""
    moment = time.time() - seconds
    if not path.is_symlink():
        os.utime(path, (moment, moment))
    elif os.utime in os.supports_follow_symlinks:
        os.utime(path, (moment, moment), follow_symlinks=False)
    return path


def folder_holding(folder: Path, entry: str, content: bytes, age: float) -> Path:
    """``folder/entry`` as ``inspect`` makes them (the folder 0700, the file 0600), both last modified ``age`` seconds ago."""
    folder.mkdir(mode=0o700, parents=True)
    (folder / entry).write_bytes(content)
    (folder / entry).chmod(0o600)
    aged(folder / entry, age)
    return aged(folder, age)


def entries(root: Path) -> dict[str, tuple[Any, ...]]:
    """Every entry below ``root``, read without following a link: its kind (a link with its target, a file with the
    SHA-256 of its bytes), its mode and its modification time — whatever a sweep could change."""
    found: dict[str, tuple[Any, ...]] = {}
    for folder, folders, files in os.walk(root):  # a link to a folder is listed with the folders, and never entered
        for name in (*folders, *files):
            path = Path(folder, name)
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode):
                kind: tuple[Any, ...] = ("link", os.readlink(path))
            elif stat.S_ISDIR(info.st_mode):
                kind = ("folder",)
            else:
                kind = ("file", cli.sha256_of(path))
            found[path.relative_to(root).as_posix()] = (*kind, oct(stat.S_IMODE(info.st_mode)), info.st_mtime_ns)
    return found


def without(snapshot: dict[str, tuple[Any, ...]], tops: set[str]) -> dict[str, tuple[Any, ...]]:
    """``snapshot`` without the entries ``tops`` and everything below them."""
    return {name: value for name, value in snapshot.items() if name.split("/", 1)[0] not in tops}


def differences(expected: dict[str, tuple[Any, ...]], actual: dict[str, tuple[Any, ...]]) -> dict[str, tuple[Any, Any]]:
    """The entries ``actual`` holds otherwise than ``expected``: ``(expected, actual)``, ``None`` on a side without it."""
    return {name: (expected.get(name), actual.get(name)) for name in sorted(expected.keys() | actual.keys()) if expected.get(name) != actual.get(name)}


def test_inspect_of_an_envelope_first_removes_the_decrypt_folders_a_killed_inspect_left_and_nothing_else(tmp_path, monkeypatch, capsys, prompts):
    """(j) Security review: a hard kill leaves ``backups/.decrypt-<random>/`` behind, a clear archive inside, and nothing
    swept it. Every case in one ``backups/``, as the sweep finds them: the stale folders that must go prove the sweep
    ran — without them, «untouched» would also hold for a sweep that never runs, as today."""
    print_section("dev.py backup inspect, the folders a killed inspect left")
    root = instance(tmp_path, monkeypatch)
    clear = clear_archive(tmp_path / "backup")
    path = sealed(clear, tmp_path / "inputs")
    backups = ensure_private_dir(backups_dir(root), root)
    # (a) Left by two killed inspects, two hours ago, a clear archive in each. (b) Younger: perhaps in use.
    for name, entry in STALE.items():
        folder_holding(backups / name, entry, clear.read_bytes(), OLD)
    for name, age in YOUNG.items():
        folder_holding(backups / name, "archive.zip", clear.read_bytes(), age)
    # (c) A link to a folder outside the data directory: the link, the folder and its file two hours old.
    target = folder_holding(tmp_path / "outside" / "linked", "kept.txt", KEPT, OLD)
    link = backups / ".decrypt-link"
    link.symlink_to(target, target_is_directory=True)
    aged(link, OLD)
    # (d) A file named as the folders are, two hours old.
    (backups / ".decrypt-file").write_bytes(KEPT)
    aged(backups / ".decrypt-file", OLD)
    # (e) A job's folder, and the earlier backups, a clear one and a secure one: two hours old.
    job = cli.job_archive(root)
    for entry in (job, job.parent, job.parent.parent):
        aged(entry, OLD)
    for name, source in ((cli.NAME, clear), (EARLIER_ENVELOPE, path)):
        shutil.copyfile(source, backups / name)
        aged(backups / name, OLD)
    ages = {name: round(time.time() - (backups / name).lstat().st_mtime) for name in [*STALE, *YOUNG]}
    assert all(ages[name] > SWEEP_AGE for name in STALE) and all(ages[name] < SWEEP_AGE for name in YOUNG), f"precondition: the stale folders older than an hour, the young ones younger (seconds): {ages}"
    assert link.is_symlink() and link.is_dir(), "precondition: .decrypt-link is a link to a folder"
    before, outside = entries(backups), entries(target.parent)
    flags, typed = given("file", tmp_path / "inputs")
    with stdin_holding(monkeypatch, typed):
        ran = run(capsys, "inspect", str(path), *flags)
    assert ran.code == 0 and VERIFIED_LINE in ran.out, f"inspect of the envelope exits 0, as before: exit {ran.code}: {ran.text[-cli.TAIL:]}"
    changed = differences(without(before, set(STALE)), without(entries(backups), set(STALE)))
    left = sorted(name for name in STALE if os.path.lexists(backups / name))
    assert left == [], f"the .decrypt-* folders older than an hour are removed, with the clear archive in each: {left} still there (elsewhere in backups/: {changed or 'nothing changed'})"
    assert changed == {}, f"nothing else in backups/ changes, to its mode and modification time — the younger folders, the link, the file, the job, the earlier backups — and inspect's own folder is gone: {changed}"
    assert entries(target.parent) == outside, f"the folder the link points to, outside the data directory, and its file are untouched: {differences(outside, entries(target.parent))}"
    assert prompts == [], f"a source was given: nothing is asked: {prompts}"
    not_shown(ran, PASSWORD)
    print_success("stale .decrypt-* folders removed; the young ones, the link and its folder, the file, the job and the earlier backups untouched")

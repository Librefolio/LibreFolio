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
    Lot B4b moves that rule into the backend (``leftovers.py``); the command line keeps this behaviour, unchanged here.
(k) Lot B4b, B-24 (red until it lands): ``decrypt`` of an envelope whose archive carries the instance key — its
    manifest says so — ends with one more line, verbatim, once, after the ✅ and 🔒 lines of every decrypt:
    ``🔑 It also holds the instance key: with it, every saved provider key can be read.``; never the key itself. No key
    in the archive, or a zip or a manifest it cannot read (an envelope holding no zip; a zip without its manifest, the
    key entry in it all the same): no such line, exit 0, the file written. Each of those first decrypts an archive with
    the key, so that «no such line» never holds only because the line does not exist yet.
(l) Lot B4b, B-25 (red until it lands): ``--password-stdin`` when standard input is a terminal takes the terminal path
    — a line read there was echoed as it was typed. ``getpass`` asks twice for ``create``, once for ``inspect``,
    ``restore`` and ``decrypt``; nothing is read from standard input, where a wrong password waits, typed ahead; the
    password typed at the prompt is the one used. At ``create``: two different passwords → ``password_mismatch``,
    end-of-file or an empty password at the prompt → ``password_required``, nothing written. From a pipe, unchanged (a
    guard, green before and after): the first line is the password — a second one is neither ``create``'s
    confirmation nor part of it — and nothing is asked.
(m) Lot B-19 (red until it lands; §1-bis, the contract revised): started as root, ``decrypt`` reads ``--password-file``
    first, as the user that started it — as ``create``, ``inspect`` and ``restore`` do, so that a secret only root can
    read works — then runs as the owner of the data directory when there is one, with the same
    ``_drop_root_privileges`` as the other commands (groups dropped, the owner's group, the owner's user, in that
    order), and only then reads the archive. The order is the barrier: the password file readable until the recorded
    ``setuid`` and never after it, the archive only from it on. ``--test-db``: the test data directory's owner, never
    the production one's. Without a data directory (the variable pointing to a folder that does not exist), or not
    started as root: no identity change, decrypt as before — each of those first shows that the same decrypt, as root
    with the data directory there, does switch. Not root, the data directory's setting is never read: one that
    ``get_data_dir()`` refuses (a ``#`` in ``LIBREFOLIO_DATA_DIR``) is never in the way, decrypt as today — after the
    barrier that, as root, the same setting is read and refused. As root, that setting: one ❌ line naming the problem,
    exit 1, no traceback, nothing at ``-o``, no prompt, no identity change. A switch refused: exit 1, one ❌ line naming
    the owner (``uid:gid``) and «Run the command as that user», nothing at ``-o``, the password never asked. An archive
    it cannot read (mode 000): one ❌ line, ``Cannot read <path>: <the system's reason> (archive_unreadable)``, never
    ``not_an_envelope``; exit 1, nothing at ``-o``, the password never asked. The cases that switch, or read mode 000,
    are skipped as root: a folder the test makes is root's, and mode 000 denies root nothing.

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
``follow_symlinks=False``, never its target's — and checked before the run. At a terminal (l), ``sys.stdin`` is
watched — every read through it recorded — and end-of-file waits after what was typed ahead, so that no read ever
waits. The identity changes of (m) are recorded instead of made (``os.geteuid``, ``setgroups``, ``setgid``,
``setuid`` replaced, as ``test_backup_cli.py`` does), ``geteuid`` answering root until the recorded ``setuid``;
``--test-db`` writes ``LIBREFOLIO_TEST_MODE`` and drops this process's database engines: both put back after the test.
POSIX-only (pty, modes, links).
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
from collections.abc import Callable, Iterator
from contextlib import closing, contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, TextIO

import pytest

from backend.app.config import get_data_dir
from backend.app.services.accounts.password_policy import failed_rules
from backend.app.services.platform.instance_backup.archive import build_archive, check_archive
from backend.app.services.platform.instance_backup.paths import DATABASE_ENTRY, MANIFEST_ENTRY, backups_dir, ensure_private_dir
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


def clear_archive(folder: Path, *, big: bool = False, instance_key: str | None = None) -> Path:
    """A backup archive (a zip) of a small data directory of its own under ``folder``, outside the data directory the
    commands see. ``big``: one more file of random bytes, so that the archive is longer than a chunk of an envelope.
    ``instance_key``: the key the archive carries, as a secure backup's does (its entry, and its manifest saying so)."""
    source = cli.make_data_dir(folder / "source")
    if big:
        (source / "custom-uploads" / "big.bin").write_bytes(random.Random(4).randbytes(envelope().CHUNK_SIZE + (64 << 10)))
    work = folder / "work"
    work.mkdir()
    return build_archive(source, work, work / cli.NAME, origin="cli", instance_key=instance_key).path


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


def output_path(tmp_path: Path, name: str = "out") -> Path:
    """Where ``decrypt`` is told to write, outside the data directory: a file not there yet, in an empty folder of its
    own, ``name``."""
    folder = tmp_path / name
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


# =============================================================================
# (k) decrypt says when the zip opens the saved keys (lot B4b, B-24)
# =============================================================================


#: What ``decrypt`` says last of a zip that carries the instance key (B-24): verbatim.
KEY_LINE = "🔑 It also holds the instance key: with it, every saved provider key can be read."
#: Not a real key: the instance key a test archive carries.
INSTANCE_KEY = "test-only-instance-key-never-a-secret-0123456789"
#: Archives with no key ``decrypt`` may announce (B-24: «no such line, still exit 0, the file written»): a zip without
#: the key; no zip at all; a zip without its manifest, the key entry in it all the same — the line follows what the
#: manifest says, never an entry's name.
NO_KEY_TO_ANNOUNCE = [pytest.param("no-key", id="zip-without-the-key"), pytest.param("not-a-zip", id="not-a-zip"), pytest.param("no-manifest", id="key-entry-without-a-manifest")]


def decrypting(monkeypatch, capsys, path: Path, out: Path, *, before: tuple[str, ...] = ()) -> Ran:
    """``decrypt path -o out``, the password from a file beside the envelope, standard input an empty pipe; ``before``:
    options of ``backup`` itself (``--test-db``)."""
    flags, typed = given("file", path.parent)
    with stdin_holding(monkeypatch, typed):
        return run(capsys, *before, "decrypt", str(path), "-o", str(out), *flags)


def key_lines(ran: Ran) -> list[str]:
    """The 🔑 lines of ``ran``."""
    return [line for line in ran.text.splitlines() if line.startswith("🔑")]


def with_no_key_to_announce(case: str, folder: Path) -> Path:
    """The file the envelope of ``case`` holds, made under ``folder``."""
    if case == "no-key":
        return clear_archive(folder)
    if case == "not-a-zip":
        folder.mkdir(parents=True)
        path = folder / "not-a-zip.bin"
        path.write_bytes(b"not a zip, sealed all the same\n" * 64)
        return path
    return cli.rebuilt(clear_archive(folder, instance_key=INSTANCE_KEY), folder / "no-manifest.zip", drop=(MANIFEST_ENTRY,))


def test_decrypt_of_an_archive_holding_the_instance_key_ends_with_the_key_line(tmp_path, monkeypatch, capsys, prompts):
    """(k) B-24: the zip ``decrypt`` wrote opens every saved provider key, and ``decrypt`` says so last, once, after the
    lines every decrypt prints; the key itself never reaches the terminal."""
    print_section("dev.py backup decrypt, an archive holding the instance key")
    instance(tmp_path, monkeypatch)
    clear = clear_archive(tmp_path / "backup", instance_key=INSTANCE_KEY)
    assert check_archive(clear).manifest.instance_key.included, "precondition: the manifest says the archive carries the instance key"
    out = output_path(tmp_path)
    ran = decrypting(monkeypatch, capsys, sealed(clear, tmp_path / "inputs"), out)
    lines = [line for line in ran.out.splitlines() if line.strip()]
    assert ran.code == 0 and lines[-1:] == [KEY_LINE], f"exit 0, and the last line says the zip opens the saved keys, verbatim {KEY_LINE!r}: exit {ran.code}: {ran.text[-cli.TAIL:]}"
    assert len(lines) >= 3 and lines[-3].startswith("✅ Decrypted: ") and lines[-2].startswith("🔒") and key_lines(ran) == [KEY_LINE], f"once, right after the ✅ and 🔒 lines of every decrypt: {lines}"
    assert cli.sha256_of(out) == cli.sha256_of(clear), "OUT is the zip that was sealed, its key entry in it"
    assert INSTANCE_KEY not in ran.text, "the key itself is never printed"
    assert prompts == [], f"a source was given: nothing is asked: {prompts}"
    not_shown(ran, PASSWORD)
    print_success("the key line, last, once")


@pytest.mark.parametrize("case", NO_KEY_TO_ANNOUNCE)
def test_decrypt_announces_no_key_its_manifest_does_not_announce(tmp_path, monkeypatch, capsys, prompts, case):
    """(k) B-24: no key in the archive, or a written zip or manifest that cannot be read: no 🔑 line, exit 0, never a
    traceback, the file written. The presence barrier first: an archive with the key gets the line, so that «no such
    line» cannot hold only because no such line exists yet (as today)."""
    instance(tmp_path, monkeypatch)
    keyed = decrypting(monkeypatch, capsys, sealed(clear_archive(tmp_path / "keyed", instance_key=INSTANCE_KEY), tmp_path / "keyed" / "inputs"), output_path(tmp_path, "keyed-out"))
    assert keyed.code == 0 and key_lines(keyed) == [KEY_LINE], f"the presence barrier: an archive with the key gets the key line (without it, «no such line» below holds by construction): exit {keyed.code}: {keyed.text[-cli.TAIL:]}"
    clear = with_no_key_to_announce(case, tmp_path / "case")
    out = output_path(tmp_path)
    ran = decrypting(monkeypatch, capsys, sealed(clear, tmp_path / "case" / "inputs"), out)
    assert ran.code == 0 and any(line.startswith("✅ Decrypted: ") for line in ran.out.splitlines()), f"{case}: decrypted, exit 0: exit {ran.code}: {ran.text[-cli.TAIL:]}"
    assert key_lines(ran) == [], f"{case}: no key line: {key_lines(ran)}"
    assert cli.sha256_of(out) == cli.sha256_of(clear), f"{case}: the file is written, byte for byte what was sealed"
    assert prompts == [], f"a source was given: nothing is asked: {prompts}"
    not_shown(ran, PASSWORD)
    print_success(f"{case}: exit 0, no key line")


# =============================================================================
# (l) --password-stdin at a terminal (lot B4b, B-25)
# =============================================================================


#: How many times a terminal asks the password: twice to choose one (``create``), once to open an envelope.
ASKED = [pytest.param("create", 2, id="create"), pytest.param("inspect", 1, id="inspect"), pytest.param("restore", 1, id="restore"), pytest.param("decrypt", 1, id="decrypt")]
#: What waits in standard input at a terminal: a wrong password typed ahead, twice — what a read would take instead of
#: the password typed at the prompt.
TYPED_AHEAD = f"{WRONG_PASSWORD}\n" * 2
#: At ``create``, what is typed at the prompts, and the code of the refusal: the terminal path's own errors (B-25).
TYPED_AT_CREATE = [
    pytest.param((PASSWORD, OTHER_PASSWORD), "password_mismatch", id="two-different-passwords"),
    pytest.param((), "password_required", id="end-of-file-at-the-prompt"),
    pytest.param(("", ""), "password_required", id="empty-password"),
]


class WatchedStdin:
    """``sys.stdin`` as a command sees it, every read through it recorded; the rest (``isatty``, ``fileno`` …) is the
    stream's own."""

    def __init__(self, stream: TextIO) -> None:
        self._stream = stream
        self.reads: list[str] = []

    def __getattr__(self, name: str) -> Any:
        return getattr(self._stream, name)

    def __iter__(self) -> Iterator[str]:
        self.reads.append("iteration")
        return iter(self._stream)

    def __next__(self) -> str:
        self.reads.append("next")
        return next(self._stream)

    def read(self, *args: Any) -> str:
        self.reads.append("read")
        return self._stream.read(*args)

    def readline(self, *args: Any) -> str:
        self.reads.append("readline")
        return self._stream.readline(*args)

    def readlines(self, *args: Any) -> list[str]:
        self.reads.append("readlines")
        return self._stream.readlines(*args)


@contextmanager
def terminal_holding(monkeypatch, typed_ahead: str) -> Iterator[WatchedStdin]:
    """``sys.stdin`` a terminal (a pty), watched, ``typed_ahead`` waiting in it, then end-of-file three times (Ctrl-D):
    a read takes what was typed ahead, and never waits."""
    keep, read_end = pty.openpty()
    os.write(keep, typed_ahead.encode("utf-8") + b"\x04" * 3)
    reader = open(read_end, encoding="utf-8")
    watched = WatchedStdin(reader)
    monkeypatch.setattr(sys, "stdin", watched)
    try:
        yield watched
    finally:
        reader.close()
        os.close(keep)


def password_command(name: str, root: Path, tmp_path: Path, request: pytest.FixtureRequest) -> tuple[list[str], Callable[[Ran], None]]:
    """``name`` ready to run but for its password source: its arguments, and the check that the run used ``PASSWORD``.
    ``create`` backs up ``root``, and its envelope must open with ``PASSWORD``; ``inspect``, ``restore --dry-run`` and
    ``decrypt`` get an envelope sealed with it (``restore``: of a restorable backup), and must do their work."""
    if name == "create":

        def created(ran: Ran) -> None:
            assert ran.code == 0, f"create: exit 0, not {ran.code}: {ran.text[-cli.TAIL:]}"
            holds_a_backup_of_the_cli(the_envelope_written(root, ran.out), PASSWORD, tmp_path / "opened")

        return ["create"], created
    clear = cli.restorable(tmp_path / "backup", request.getfixturevalue("head_database")) if name == "restore" else clear_archive(tmp_path / "backup")
    path = sealed(clear, tmp_path / "inputs")
    out = output_path(tmp_path)
    argv = {"inspect": ["inspect", str(path)], "restore": ["restore", str(path), "--dry-run"], "decrypt": ["decrypt", str(path), "-o", str(out)]}[name]
    said = {"inspect": VERIFIED_LINE, "restore": cli.RESTORABLE_LINE, "decrypt": "✅ Decrypted: "}[name]

    def did_its_work(ran: Ran) -> None:
        assert ran.code == 0 and said in ran.out, f"{name}: the envelope opened with the password, exit 0 and {said!r}: exit {ran.code}: {ran.text[-cli.TAIL:]}"
        if name == "decrypt":
            assert cli.sha256_of(out) == cli.sha256_of(clear), "decrypt: OUT is the zip that was sealed"

    return argv, did_its_work


@pytest.mark.parametrize(("name", "times"), ASKED)
def test_password_stdin_at_a_terminal_is_asked_through_getpass_and_nothing_is_read(tmp_path, monkeypatch, capsys, request, name, times):
    """(l) B-25: at a terminal, ``--password-stdin`` takes the terminal path — a line read from standard input there was
    echoed as it was typed. ``getpass`` asks, twice to choose a password and once to open an envelope; standard input
    is never read; the password typed at the prompt is the one used, not the wrong one typed ahead."""
    print_section(f"dev.py backup {name} --password-stdin, at a terminal")
    root = instance(tmp_path, monkeypatch)
    argv, used_the_password = password_command(name, root, tmp_path, request)
    asked = answering(monkeypatch, *[PASSWORD] * times)
    with terminal_holding(monkeypatch, TYPED_AHEAD) as stdin:
        ran = run(capsys, *argv, "--password-stdin")
    assert (stdin.reads, len(asked)) == ([], times), f"at a terminal: asked through getpass {times}×, standard input never read: reads {stdin.reads}, prompts {asked}, exit {ran.code}: {ran.text[-cli.TAIL:]}"
    used_the_password(ran)
    not_shown(ran, PASSWORD, WRONG_PASSWORD)
    print_success(f"{name}: asked {times}×, standard input never read, the password typed used")


@pytest.mark.parametrize(("typed", "code"), TYPED_AT_CREATE)
def test_password_stdin_at_a_terminal_refuses_at_create_what_the_terminal_path_refuses(tmp_path, monkeypatch, capsys, typed, code):
    """(l) B-25: the terminal path's errors, unchanged: exit 1, the code on a ❌ line, nothing written; standard input
    never read, not even after an end-of-file at the prompt."""
    root = instance(tmp_path, monkeypatch)
    before = cli.listing(root)
    asked = answering(monkeypatch, *typed)
    with terminal_holding(monkeypatch, TYPED_AHEAD) as stdin:
        ran = run(capsys, "create", "--password-stdin")
    assert ran.code == 1 and ran.refusals(code), f"exit 1, a ❌ line naming {code}: exit {ran.code}, reads {stdin.reads}, prompts {asked}: {ran.text[-cli.TAIL:]}"
    assert stdin.reads == [] and asked, f"asked at the terminal, standard input never read: reads {stdin.reads}, prompts {asked}"
    assert cli.listing(root) == before, f"nothing written: {sorted(set(cli.listing(root)) - set(before))}"
    not_shown(ran, PASSWORD, OTHER_PASSWORD, WRONG_PASSWORD)
    print_success(f"({code}), nothing written")


@pytest.mark.parametrize("name", COMMANDS)
def test_password_stdin_from_a_pipe_is_still_its_first_line(tmp_path, monkeypatch, capsys, prompts, request, name):
    """(l) B-25 leaves a pipe as it was (a guard, green before and after): one line, the password; a second line is
    neither ``create``'s confirmation nor part of the password; nothing is asked."""
    root = instance(tmp_path, monkeypatch)
    argv, used_the_password = password_command(name, root, tmp_path, request)
    with stdin_holding(monkeypatch, f"{PASSWORD}\n{WRONG_PASSWORD}\n"):
        ran = run(capsys, *argv, "--password-stdin")
    used_the_password(ran)
    assert prompts == [], f"from a pipe, nothing is asked: {prompts}"
    not_shown(ran, PASSWORD, WRONG_PASSWORD)
    print_success(f"{name}: the first line of the pipe, nothing asked")


# =============================================================================
# (m) decrypt started as root (B-19)
# =============================================================================


#: Run as root, a folder a test makes is root's — there is no owner to switch to — and mode 000 denies root nothing.
needs_another_owner = pytest.mark.skipif(cli.AS_ROOT, reason="as root, a folder the test makes is root's (no owner to switch to), and mode 000 denies root nothing")


class Identity:
    """Who this process is, as the command sees it: ``os.geteuid()`` answers ``euid`` until a ``setuid`` changes it, so
    that a second switch in the same run finds a process that is no longer root, as a real one would; ``setgroups``,
    ``setgid`` and ``setuid`` are recorded instead of made, as ``test_backup_cli.py``'s ``identity`` fixture records
    them. ``at_switch`` runs at the ``setuid``: the order barrier."""

    def __init__(self, euid: int, at_switch: Callable[[], None] | None = None) -> None:
        self.euid = euid
        self.calls: list[tuple[str, object]] = []
        self._at_switch = at_switch

    def geteuid(self) -> int:
        return self.euid

    def setgroups(self, groups: Any) -> None:
        self.calls.append(("setgroups", list(groups)))

    def setgid(self, gid: int) -> None:
        self.calls.append(("setgid", gid))

    def setuid(self, uid: int) -> None:
        self.calls.append(("setuid", uid))
        self.euid = uid
        if self._at_switch is not None:
            self._at_switch()


def faked_identity(monkeypatch, euid: int, *, at_switch: Callable[[], None] | None = None, refuse_setuid: bool = False) -> Identity:
    """This process's identity replaced by an ``Identity`` that starts as ``euid``; ``refuse_setuid``: ``setuid``
    refused as it is to a process without the privilege (EPERM)."""
    identity = Identity(euid, at_switch)
    monkeypatch.setattr(backup_cli.os, "geteuid", identity.geteuid, raising=False)
    monkeypatch.setattr(backup_cli.os, "setgroups", identity.setgroups, raising=False)
    monkeypatch.setattr(backup_cli.os, "setgid", identity.setgid, raising=False)
    monkeypatch.setattr(backup_cli.os, "setuid", cli.refuse if refuse_setuid else identity.setuid, raising=False)
    return identity


def owner_switch(root: Path) -> list[tuple[str, object]]:
    """The identity changes that make a root process the owner of ``root``, in their order: its groups dropped, then
    the owner's group, then the owner's user."""
    owner = root.stat()
    return [("setgroups", []), ("setgid", owner.st_gid), ("setuid", owner.st_uid)]


def an_envelope(tmp_path: Path, name: str) -> tuple[Path, Path, Path]:
    """A sealed backup of its own, made under ``tmp_path/name``: the zip, its envelope, and where ``decrypt`` writes."""
    clear = clear_archive(tmp_path / name)
    return clear, sealed(clear, tmp_path / name / "inputs"), output_path(tmp_path, f"{name}-out")


def decrypted_as_before(ran: Ran, clear: Path, out: Path) -> bool:
    """Whether ``ran`` decrypted as ``decrypt`` always does: exit 0, ``out`` the zip that was sealed."""
    return ran.code == 0 and out.is_file() and cli.sha256_of(out) == cli.sha256_of(clear)


def switched_as_root(capsys, monkeypatch, tmp_path: Path, root: Path) -> None:
    """The presence barrier of the cases where nothing switches: the same decrypt, as root with the data directory
    ``root`` there, becomes its owner — so that «no identity change» never holds only because ``decrypt`` never
    switches (as before B-19)."""
    identity = faked_identity(monkeypatch, 0)
    clear, path, out = an_envelope(tmp_path, "barrier")
    ran = decrypting(monkeypatch, capsys, path, out)
    assert identity.calls == owner_switch(root) and decrypted_as_before(ran, clear, out), f"the barrier: as root with the data directory there, decrypt becomes its owner, then decrypts — identity changes {identity.calls}, not {owner_switch(root)}: exit {ran.code}: {ran.text[-cli.TAIL:]}"


def keep_engines(monkeypatch) -> None:
    """``--test-db`` (``set_test_mode``) drops this process's database engines: they are put back after the test."""
    from backend.app.db import session  # noqa: PLC0415 — only the --test-db case needs it, as set_test_mode itself

    monkeypatch.setattr(session, "sync_engine", session.sync_engine)
    monkeypatch.setattr(session, "async_engine", session.async_engine)


@needs_another_owner
def test_decrypt_as_root_first_becomes_the_owner_of_the_data_directory(tmp_path, monkeypatch, capsys, prompts):
    """(m) B-19, §1-bis: ``--password-file`` read first, as the user that started the command (as ``create``,
    ``inspect`` and ``restore`` read it: a secret only root can read works); then groups dropped, the owner's group,
    the owner's user; and only then the archive is read. The order is the barrier: the password file is readable until
    the recorded ``setuid`` and never after it, the archive only from it on. Then decrypt as always: the zip that was
    sealed, 0600."""
    print_section("dev.py backup decrypt, started as root")
    root = instance(tmp_path, monkeypatch)
    clear, path, out = an_envelope(tmp_path, "backup")
    flags, _typed = given("file", path.parent)
    secret = Path(flags[1])

    def at_the_switch() -> None:
        path.chmod(0o600)  # the archive: readable from the switch on, so read after it
        secret.chmod(0o000)  # the password file: readable until the switch, so read before it

    path.chmod(0o000)
    identity = faked_identity(monkeypatch, 0, at_switch=at_the_switch)
    with stdin_holding(monkeypatch, ""):
        ran = run(capsys, "decrypt", str(path), "-o", str(out), *flags)
    assert identity.calls == owner_switch(root), f"as root, decrypt becomes the owner of the data directory — its groups dropped, the owner's group, the owner's user: {owner_switch(root)}, not {identity.calls}: exit {ran.code}: {ran.text[-cli.TAIL:]}"
    assert decrypted_as_before(ran, clear, out), f"the password file read before the switch (nobody can read it after), the archive after it (nobody could before): exit {ran.code}: {ran.text[-cli.TAIL:]}"
    mode = stat.S_IMODE(out.stat().st_mode)
    assert mode == 0o600, f"the zip is readable by its owner only (0600), not {oct(mode)}"
    assert prompts == [], f"a source was given: nothing is asked: {prompts}"
    not_shown(ran, PASSWORD)
    print_success("root → the password file, then setgroups([]), setgid, setuid of the owner, then the archive: decrypted")


@needs_another_owner
def test_decrypt_with_test_db_as_root_becomes_the_owner_of_the_test_data_directory(tmp_path, monkeypatch, capsys, prompts):
    """(m) B-19: ``--test-db`` honoured, as by the other commands: the owner taken is the test data directory's, never
    the production one's. The production directory missing, a decrypt that ignored ``--test-db`` would switch to
    nobody; then the other way round, the test directory missing and the production one there, it would switch to the
    production directory's owner."""
    production, test_data = tmp_path / "production", cli.make_data_dir(tmp_path / "test-data").resolve()
    monkeypatch.delenv("LIBREFOLIO_TEST_MODE", raising=False)  # set_test_mode writes it: put back after the test
    monkeypatch.setenv("LIBREFOLIO_DATA_DIR", str(production))
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(test_data))
    keep_engines(monkeypatch)
    identity = faked_identity(monkeypatch, 0)
    clear, path, out = an_envelope(tmp_path, "backup")
    ran = decrypting(monkeypatch, capsys, path, out, before=("--test-db",))
    assert identity.calls == owner_switch(test_data) and decrypted_as_before(ran, clear, out), f"--test-db as root: the owner of the test data directory, {owner_switch(test_data)}, not {identity.calls}: exit {ran.code}: {ran.text[-cli.TAIL:]}"
    cli.make_data_dir(production)
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / "test-data-absent"))
    identity = faked_identity(monkeypatch, 0)
    clear, path, out = an_envelope(tmp_path, "again")
    ran = decrypting(monkeypatch, capsys, path, out, before=("--test-db",))
    assert identity.calls == [] and decrypted_as_before(ran, clear, out), f"--test-db without its test data directory: never the production directory's owner, decrypted as before: identity changes {identity.calls}: exit {ran.code}: {ran.text[-cli.TAIL:]}"
    assert not (tmp_path / "test-data-absent").exists(), "no test data directory is created"
    print_success("--test-db → the test data directory's owner, never the production one's")


@needs_another_owner
def test_decrypt_as_root_without_a_data_directory_stays_who_it_is(tmp_path, monkeypatch, capsys, prompts):
    """(m) B-19: decrypting on another computer, no LibreFolio data there (the variable pointing to a folder that does
    not exist): nothing to switch to, decrypt as before — «it needs no data directory» stays true. The barrier first."""
    switched_as_root(capsys, monkeypatch, tmp_path, instance(tmp_path, monkeypatch))
    absent = cli.point_at(monkeypatch, tmp_path / "absent")
    identity = faked_identity(monkeypatch, 0)
    clear, path, out = an_envelope(tmp_path, "elsewhere")
    ran = decrypting(monkeypatch, capsys, path, out)
    assert identity.calls == [] and decrypted_as_before(ran, clear, out), f"as root without a data directory: no identity change, decrypted as before: {identity.calls}: exit {ran.code}: {ran.text[-cli.TAIL:]}"
    assert not absent.exists(), "no data directory is created"
    print_success("root, no data directory → no identity change, decrypted")


@needs_another_owner
def test_decrypt_not_started_as_root_changes_no_identity(tmp_path, monkeypatch, capsys, prompts):
    """(m) B-19: started as the owner itself, not root: nothing to drop, decrypt as before. The barrier first, on the
    same data directory."""
    root = instance(tmp_path, monkeypatch)
    switched_as_root(capsys, monkeypatch, tmp_path, root)
    identity = faked_identity(monkeypatch, root.stat().st_uid)
    clear, path, out = an_envelope(tmp_path, "backup")
    ran = decrypting(monkeypatch, capsys, path, out)
    assert identity.calls == [] and decrypted_as_before(ran, clear, out), f"not root: no identity change, decrypted as before: {identity.calls}: exit {ran.code}: {ran.text[-cli.TAIL:]}"
    print_success("not root → no identity change, decrypted")


@needs_another_owner
def test_decrypt_as_root_that_cannot_become_the_owner_stops_before_anything(tmp_path, monkeypatch, capsys):
    """(m) B-19: the switch refused (``setuid``, EPERM): one ❌ line naming the owner and what to do, exit 1, nothing at
    ``-o``, and the password never asked — at a terminal, where it would be, the right one ready to be typed."""
    root = instance(tmp_path, monkeypatch)
    _clear, path, out = an_envelope(tmp_path, "backup")
    faked_identity(monkeypatch, 0, refuse_setuid=True)
    asked = answering(monkeypatch, PASSWORD)
    with terminal_holding(monkeypatch, TYPED_AHEAD) as stdin:
        ran = run(capsys, "decrypt", str(path), "-o", str(out))
    owner = root.stat()
    said = [line for line in ran.refused if f"({owner.st_uid}:{owner.st_gid})" in line and "Run the command as that user" in line]
    assert ran.code == 1 and len(ran.refused) == 1 and said == ran.refused, f"exit 1, one ❌ line naming the owner ({owner.st_uid}:{owner.st_gid}) and «Run the command as that user»: exit {ran.code}: {ran.text[-cli.TAIL:]}"
    assert list(out.parent.iterdir()) == [], f"nothing at -o: {sorted(entry.name for entry in out.parent.iterdir())}"
    assert (asked, stdin.reads) == ([], []), f"the password is never asked: prompts {asked}, reads {stdin.reads}"
    not_shown(ran, PASSWORD, WRONG_PASSWORD)
    print_success("switch refused → exit 1, the owner named, nothing written, nothing asked")


@cli.needs_permission_checks
def test_decrypt_of_an_archive_it_cannot_read_says_so_before_the_password(tmp_path, monkeypatch, capsys):
    """(m) B-19: an archive the command cannot read — now possibly a root-only file, once it runs as the server's user —
    is not «not a secure backup» (``is_envelope`` answers False for a file it cannot read): one ❌ line, ``Cannot read
    <path>: <the system's reason> (archive_unreadable)``, exit 1, nothing at ``-o``, the password never asked."""
    instance(tmp_path, monkeypatch)
    _clear, path, out = an_envelope(tmp_path, "backup")
    path.chmod(0o000)
    asked = answering(monkeypatch, PASSWORD)
    with terminal_holding(monkeypatch, TYPED_AHEAD) as stdin:
        ran = run(capsys, "decrypt", str(path), "-o", str(out))
    prefix, code = f"❌ Cannot read {path}: ", "(archive_unreadable)"
    said = [line for line in ran.refused if line.startswith(prefix) and line.rstrip().endswith(code) and line.rstrip()[len(prefix) : -len(code)].strip()]
    assert ran.code == 1 and len(ran.refused) == 1 and said == ran.refused, f"exit 1, one ❌ line: {prefix}<the system's reason> {code} — never not_an_envelope: exit {ran.code}: {ran.text[-cli.TAIL:]}"
    assert list(out.parent.iterdir()) == [], f"nothing at -o: {sorted(entry.name for entry in out.parent.iterdir())}"
    assert (asked, stdin.reads) == ([], []), f"the password is never asked: prompts {asked}, reads {stdin.reads}"
    print_success("an archive it cannot read → (archive_unreadable), nothing written, nothing asked")


def broken_data_dir_setting(monkeypatch, tmp_path: Path) -> str:
    """Production mode, ``LIBREFOLIO_DATA_DIR`` set to a value ``get_data_dir()`` refuses here (a ``#`` in it): the
    message of its ``ValueError``, checked before any command runs."""
    monkeypatch.delenv("LIBREFOLIO_TEST_MODE", raising=False)
    monkeypatch.delenv("LIBREFOLIO_TEST_DATA_DIR", raising=False)
    monkeypatch.setenv("LIBREFOLIO_DATA_DIR", str(tmp_path / "data#broken"))
    try:
        found = get_data_dir()
    except ValueError as exc:
        return str(exc)
    pytest.fail(f"precondition: a # in LIBREFOLIO_DATA_DIR must make get_data_dir() raise ValueError here, not give {found}")


def refused_for_the_setting(capsys, monkeypatch, envelope_made: tuple[Path, Path, Path], problem: str) -> None:
    """The presence barrier of the case where the setting is never read: as root, the same decrypt reads it and refuses
    it — so that «decrypt as today» never holds only because ``decrypt`` reads no setting at all (as before B-19)."""
    faked_identity(monkeypatch, 0)
    _clear, path, out = envelope_made
    ran = decrypting(monkeypatch, capsys, path, out)
    assert ran.code == 1 and ran.refusals(problem), f"the barrier: as root, decrypt reads the data directory's setting and refuses one get_data_dir() refuses ({problem}): exit {ran.code}: {ran.text[-cli.TAIL:]}"


def test_decrypt_not_started_as_root_never_reads_the_data_directory_setting(tmp_path, monkeypatch, capsys, prompts):
    """(m) B-19, §1-bis: not root there is nothing to switch, so the data directory's setting is never read — one that
    ``get_data_dir()`` refuses is never in the way: decrypt as today, exit 0, the zip written. The barrier first: as
    root, the same setting is read, and refused."""
    barrier, (clear, path, out) = an_envelope(tmp_path, "barrier"), an_envelope(tmp_path, "backup")
    problem = broken_data_dir_setting(monkeypatch, tmp_path)
    refused_for_the_setting(capsys, monkeypatch, barrier, problem)
    identity = faked_identity(monkeypatch, 1000)
    ran = decrypting(monkeypatch, capsys, path, out)
    assert identity.calls == [] and decrypted_as_before(ran, clear, out), f"not root, a data directory setting get_data_dir() refuses ({problem}): decrypted as today, never refused for it: identity changes {identity.calls}, exit {ran.code}: {ran.text[-cli.TAIL:]}"
    assert prompts == [], f"a source was given: nothing is asked: {prompts}"
    not_shown(ran, PASSWORD)
    print_success("not root, a data directory setting it cannot use → decrypted as today")


def test_decrypt_as_root_with_a_data_directory_setting_it_cannot_use_stops_with_its_message(tmp_path, monkeypatch, capsys):
    """(m) B-19, §1-bis: as root the setting must be read, to know whose data this is; one ``get_data_dir()`` refuses is
    said on one ❌ line naming the problem — exit 1, never a traceback — before anything else: nothing at ``-o``, no
    prompt (at a terminal, where there would be one, the right password ready to be typed), no identity change."""
    _clear, path, out = an_envelope(tmp_path, "backup")
    problem = broken_data_dir_setting(monkeypatch, tmp_path)
    identity = faked_identity(monkeypatch, 0)
    asked = answering(monkeypatch, PASSWORD)
    with terminal_holding(monkeypatch, TYPED_AHEAD) as stdin:
        ran = run(capsys, "decrypt", str(path), "-o", str(out))
    said = ran.refusals(problem)
    assert ran.code == 1 and len(ran.refused) == 1 and said == ran.refused, f"exit 1, one ❌ line naming the problem ({problem}): exit {ran.code}: {ran.text[-cli.TAIL:]}"
    assert "Traceback" not in ran.text, f"never a traceback: {ran.text[-cli.TAIL:]}"
    assert list(out.parent.iterdir()) == [], f"nothing at -o: {sorted(entry.name for entry in out.parent.iterdir())}"
    assert (asked, stdin.reads, identity.calls) == ([], [], []), f"no prompt, no identity change: prompts {asked}, reads {stdin.reads}, identity changes {identity.calls}"
    not_shown(ran, PASSWORD, WRONG_PASSWORD)
    print_success("root, a data directory setting it cannot use → one ❌ line, exit 1, nothing asked, nothing written")

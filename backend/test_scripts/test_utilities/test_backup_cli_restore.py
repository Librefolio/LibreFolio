"""
Restoring a backup from the command line (workstream B, lot B3, contract §8 and §11): ``dev.py backup restore ARCHIVE``
without ``--dry-run``, and ``dev.py backup pending [--cancel]``.

Written before the code (red until lot B3 lands): ``apply.py`` does not exist yet, and every name of lot B3 is imported
inside the test that needs it, so the file collects and each test fails on its own. The messages are not final: the
tests pin exit codes, what is on disk, the stable codes in parentheses and a few key words (``waits for the next
start``, ``Nothing restored``, ``--yes``, ``rolled back``), never whole lines — but one: the line saying that a restore
waits for the hosting provider's block to end, which the developer decided word for word (§11, P7; written red before
it), printed by ``pending`` and by a confirmation on a blocked instance.

(a) ``restore ARCHIVE --yes``: the check on a copy and its report, as ``--dry-run`` prints it, then the confirmation:
    exit 0, a ✅ that the restore ``waits for the next start``; the copy kept; ``.restore/restore.json`` (0600)
    ``pending``, its stage the copy's, ``confirmed_by`` ``cli``, the data directory resolved, ``action`` and the
    backup's version from the report. The live database and files are untouched, and nothing restarts the server.
    §11, P7: on a blocked instance the command line does not refuse — whoever runs the server, the hosting provider,
    may prepare a restore for the unblock — and says so: exit 0, the restore pending, the usual confirmation lines,
    then one more line, the decided one, the last printed. A ``LIBREFOLIO_BLOCKED`` that cannot be read counts as
    blocked; without it, no such line.
(b) Without ``--yes``: on a terminal (a pty), typing ``restore`` confirms, as ``--yes`` does, the spaces around it
    ignored and its case kept; anything else typed (``Restore`` included) is declined, ``Nothing restored``, exit 1, the
    copy removed, nothing pending. Not a terminal (a pipe, ``restore``
    waiting in it all the same): refused, exit 1, the message names ``--yes``, the copy removed, nothing pending.
(c) A restore ACTIVE (pending, or one a start is applying): exit 1 with ``(restore_already_pending)`` before the check
    (no copy made, no progress of a check), the restore and its copy as they were. ``--dry-run`` meanwhile is as before:
    exit 0, its own copy removed, the pending one kept. A backup without an active administrator: exit 1, the copy
    removed, nothing pending. A confirmation that fails (the head moved since the check, or ``confirm_restore`` raising
    each of its errors): exit 1, one ❌ line ending with the code in parentheses, the copy removed, nothing pending.
(d) ``pending``: without a restore, «no restore», exit 0, nothing created; each phase on disk, exit 0. The ``waiting``
    line and the ``reason`` line of a rolled back restore end with the stable code in parentheses (the words before it
    are not final); ``instance_blocked`` (§11) too, and its line is the decided one, word for word. §11, P7, decided:
    ``pending`` reads the block live. A pending restore on an instance blocked now (or whose block cannot be read)
    prints that line once, whether or not the last start recorded ``instance_blocked``; recorded, it is printed even
    unset now (what that start found); another reason recorded and the instance blocked now, both lines, the recorded
    one first — but ``other_data_directory`` recorded wins, as at a start, and the line is not printed (this copy never
    applies the restore). Anything but a pending restore — in progress, committed, rolled back, or none — never prints
    it.
(e) ``pending --cancel``: a pending restore cancelled with its copy (``drop_copy=True``), exit 0, the live data as it
    was. Nothing pending: one ❌ line ending with ``(restore_not_pending)``, exit 1; without a state file nothing is
    created, not even ``.restore/apply.lock``; a restore being applied or finished keeps its state as it was.
(f) ``python scripts/backup_cli.py pending`` end to end; the help names ``--yes`` and ``--cancel``.
(g) B-32 (red until it lands; contract §2, §3): a state the file system cannot read is said, never taken for «no
    restore». ``pending``, ``pending --cancel`` and ``restore ARCHIVE --yes`` print one line, verbatim,
    ``❌ The state of the restore cannot be read: <reason> (restore_state_unreadable)`` — the system's reason, never a
    path — and exit 1, no traceback; the state, and a pending restore's copy, kept; ``restore`` checks nothing (no
    copy made), while its ``--dry-run``, which never reads the state, works as before (a guard). In this process the
    state is a file ``os.open`` refuses (EACCES, EIO), every other open the real one; for the script the file system
    refuses it for real (the state file of mode 000, or ``.restore`` without its search permission, which ``lexists``
    used to read as «no state»), skipped as root. ``pending --cancel`` refused before the restore is dropped (the
    state's removal refused, EPERM; or ``.restore`` read-only for real, EACCES): one line, verbatim, ``❌ The restore
    could not be cancelled: <strerror>. It still waits for the next start (restore_cancel_failed)``, exit 1, the
    restore and its copy kept. Dropped, its copy left (its removal raising, which B-31 logs as a WARNING; leaving it
    without a word, the copy's folder read-only for real; or ``.restore/stage`` not searchable for real, where a look at
    the copy is refused too and counts as the copy still there, §2 amended): exactly ``✅ The restore waiting for the
    next start was dropped: the data stays as it is`` then ``⚠️  Its checked copy could not be removed: it goes when its
    check expires``, exit 0, the copy still there; the usual drop keeps its «with its copy» line (a guard). A mode changed
    for a test is given back when the command ends, failed or not.
(h) B-18 (red until it lands; contract §2): ``restore ARCHIVE --instance-key-file FILE`` gives the old instance key, so
    that a clear archive's saved provider keys — under the key K1 of the instance it came from — are re-encrypted with
    this instance's own key, K2 (the source and its secrets: ``test_backup_secure.py``'s ``secret_source``, on this
    module's database at the head). A dry run: exit 0, ``   Instance key: not included; given with
    --instance-key-file``, the «re-encrypted» line with their count, no ⚠️ line for them, the copy removed. Confirmed
    (``--yes``): its copy waits, every saved key in it under K2, and ``pending`` shows it. A file that gives no key
    (missing, blank, mode 000): ``❌ <its message> (instance_key_unreadable)``, exit 1, no copy, and the password of a
    secure archive never asked: the file is read before it. A key shorter than 32 characters: ``❌ The instance key given
    is too short: an instance key has at least 32 characters (instance_key_invalid)``, exit 1, no copy left. D1: a
    secure archive carrying its own key uses it, ``ℹ️  The archive carries its own instance key: --instance-key-file is
    not used`` right after the key line. D2: a wrong key of 32 characters or more, ``⚠️  The key given with
    --instance-key-file reads none of the saved provider keys: …`` right before the ⚠️ line of the unreadable keys —
    unless this instance's own key cannot be used (``LIBREFOLIO_INSTANCE_KEY`` too short), then ``⚠️  This instance's
    own key cannot be used, so nothing was re-encrypted with the key given: <problem>`` in its place, the right key
        given all the same; B-34 (red until it lands): also when this instance has no key yet and the check cannot create
        one (``secrets/`` not writable, skipped as root), the problem then ``<its secrets/instance.key>: there is no
        instance key yet, and it could not be created``. As root (B-19's fake identity, ``test_backup_cli_secure.py``), the
        file is read before the switch to the owner: a file root alone could read works. No key text ever reaches standard
        output or error.
(i) B-35 (red until it lands; contract §3, CLI): ``restore`` honours ``LIBREFOLIO_BACKUP_MAX_RESTORE_MB``, the largest
    total a check unpacks (what the manifest declares; MB of 1024², ``0`` no limit; unset, no limit self-hosted and 8
    times the upload limit in any other profile). Over it: exactly one ❌ line ending in ``(unpacked_too_large)``, exit 1,
    after the 🔎 line (the limit is checked inside the check), no copy left. A limit that cannot be read — not a whole
    number, or, managed, an upload limit whose profile entry is of the wrong type — exactly one ❌ line naming the
    variable at fault and ending in ``(backup_restore_unavailable)``, exit 1, before the 🔎 line, no copy. ``0`` lifts
    the profile's limit for one command: the archive is checked as today, after the barrier that, unset, the same
    archive is refused. Managed, unset, an upload limit of 1 MB: a limit of 8 MB, an archive declaring more refused, one
    declaring less checked as today. The archives are the staging tests' data directory (its files 2.5 MiB and a bit),
    plus, for the one over 8 MB, a file of zeros that deflate shrinks a thousandfold: small to upload, big to unpack.
(j) B-43 (red until it lands): ``restore ARCHIVE --dry-run`` of an archive whose database holds an index on an
    expression calling a function this LibreFolio does not have (``test_backup_staging``'s ``archive_calling`` with its
    ``IN_AN_INDEX``, on this module's database at the head): SQLite fails the copy's integrity check, «unknown function».
    Exactly one ❌ line, after the 🔎 line, ending in ``(database_damaged)``, exit 1, no traceback; no copy left, the live
    data untouched, the function's name (the archive's text) on neither output.
(k) Lot L3-2 (red until it lands; contract L3 §5): a restore the command line confirms — with ``--yes``, or the word
    typed on a terminal — records ``confirmed_via`` ``cli`` in ``restore.json``, beside ``confirmed_by`` ``cli``.
(l) B-33 (red until it lands; interface ``B-b33-interface.md`` §3). ``pending`` with a state that cannot be read —
    refused by the file system (``io``), a folder (``not_a_file``), no state (``invalid``): exit 1, exactly one ❌ line
    holding ``restore_state_unreadable`` and the reason word; then what is on disk — the swapped folders
    ``.restore/previous/`` holds, how many checked copies are kept — and the command ``./dev.py backup pending
    --recover previous``; never the state's content, never a path, no traceback; nothing changed. (g)'s ``pending`` cases
    now expect this (they pinned one line, the system's words in it); ``pending --cancel`` and ``restore --yes`` keep (g)'s
    one line. ``pending --recover previous``: with such a state, exit 0, a ✅ line, the folders it moved named, ``./dev.py
    backup restore`` named; each folder of ``previous/`` back in place, its live one in ``.restore/failed/``, the state
    renamed ``restore.json.unreadable-<UTC>``; then ``pending`` says no restore. With no state: exit 3, one line
    ``❌ Nothing to recover…``; with a state this LibreFolio reads: exit 4; nothing moved. While a server serves the data
    directory (its serving lock held by this process, as ``hold_serving_lock`` holds it): exit 5, one ❌ line, nothing
    moved. ``--recover`` with ``--cancel``: refused by the parser (exit 2). The help names ``--recover``.
    Lot B5-2 (interface ``B-b52-interface.md``): ``--recover`` takes its choice (it was a bare flag, never released), and
    the exit codes of 1.3's development builds (1) became 3, 4 and 5; the rest of ``--recover`` and ``--json`` is pinned by
    ``test_backup_cli_recover.py``.
(m) Lot B5-1 (interface ``B-b51-interface.md`` §5; written RED before it): ``pending`` of a committed restore confirmed
    via ``admin`` with an owner chosen prints one more line than the same restore without one, naming the owner's
    account: ``sent`` (the link went to the owner's mailbox), ``link_only`` (the reset path, once, with «only to the
    owner»), ``already_issued`` and ``already_done``, ``error:<CODE>`` (the code), and nothing recorded yet («next
    start»). Never the path but for ``link_only``. A restore confirmed via ``cli`` or ``panel``, or without an owner,
    prints no such line (a guard). ``pending --json`` never holds the owner's id, outcome, reset path or email (a guard,
    green before and after: its keys are B5-2's). The owner's fields are written into the state file as raw JSON, so
    that what ``pending`` prints is what fails.

Pure, as ``test_backup_cli.py``, whose fixtures and helpers are imported: data directories under ``tmp_path`` seen through
``LIBREFOLIO_DATA_DIR`` (production mode, checked); a real database at the head made once by ``alembic upgrade`` for the
module. The commands go through the parser ``register_subparser`` builds, as ``dev.py backup`` runs them. A terminal is a
pty, a pipe is a pipe: ``sys.stdin`` replaced for one test. No signal can reach this process: ``restart.send_signal``
and ``os.kill`` as ``restart`` sees it record, and must stay unused. States only a start can reach are written as
``apply.RestoreState`` would write them; the reason a pending restore waits is written into the state file itself
(``waiting_for``), whatever the models accept, so that what ``pending`` prints is what fails. The block is
``LIBREFOLIO_BLOCKED`` in this process's environment, which ``config.platform.instance_blocked()`` reads at each call:
the one a developer's shell may carry is removed before every test (``no_inherited_block``), and a test of the block
sets its own with ``monkeypatch``; the instance key it may carry is removed too (``no_inherited_instance_key``), and the
restore limit (``no_inherited_restore_limit``). POSIX-only (pty, modes).
"""

from __future__ import annotations

import argparse
import errno
import importlib
import json
import os
import pty
import re
import stat
import sys
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from backend.app.config import ENVIRONMENT_PROFILE_DEFAULTS, SecretFileError, read_secret_file
from backend.app.config.backup import MAX_UPLOAD_VARIABLE
from backend.app.config.platform import instance_blocked
from backend.app.services.platform.instance_backup.archive import read_manifest
from backend.app.services.platform.instance_backup.paths import DATABASE_ENTRY, restore_dir, stage_data_dir, stage_dir, stages_dir
from backend.app.services.platform.instance_backup.staging import read_report
from backend.app.services.platform.instance_key import instance_key_status
from backend.test_scripts.test_services import test_backup_secure as secure_cases
from backend.test_scripts.test_services import test_backup_staging as staging_cases
from backend.test_scripts.test_utilities import test_backup_cli as cli
from backend.test_scripts.test_utilities import test_backup_cli_secure as secure_cli
from backend.test_scripts.test_utils import print_section, print_success
from scripts import backup_cli

pytestmark = pytest.mark.skipif(os.name == "nt", reason="a terminal is a pty, and file modes are POSIX only")

# The fixtures of the command line's tests, re-exported: ``app_version`` (autouse) and the real database at the head.
app_version = cli.app_version
head_database = cli.head_database
# (B-18) Autouse, as in test_backup_secure.py: the instance key a developer's shell may carry (LIBREFOLIO_INSTANCE_KEY,
# LIBREFOLIO_INSTANCE_KEY_FILE) is removed for every test; a check reads the key of the data directory it works on.
no_inherited_instance_key = secure_cases.no_inherited_instance_key

ACTIVE = ["pending", "applying", "applied", "rolling_back"]
TERMINAL = ["committed", "rolled_back"]
CONFIRMED_AT = datetime(2026, 10, 15, 22, 0, tzinfo=UTC)
FINISHED_AT = datetime(2026, 10, 15, 23, 0, tzinfo=UTC)
#: The errors ``apply.confirm_restore`` raises, and their codes (contract §2).
CONFIRM_ERRORS = {
    "RestoreStageMissingError": "restore_stage_not_found",
    "RestoreNotRestorableError": "restore_not_restorable",
    "RestoreStageExpiredError": "restore_stage_expired",
    "RestoreStageOutdatedError": "restore_stage_outdated",
    "RestoreAlreadyPendingError": "restore_already_pending",
}
#: (§11, P7) The hosting provider's block, which ``config.platform.instance_blocked()`` reads from this process's
#: environment at each call.
BLOCKED_VARIABLE = "LIBREFOLIO_BLOCKED"
#: (B-35) The largest total a restore unpacks, in megabytes (``0``: no limit), which every ``restore`` reads; lot B-35
#: brings its reader, ``config.backup.MAX_RESTORE_VARIABLE``.
RESTORE_LIMIT_VARIABLE = "LIBREFOLIO_BACKUP_MAX_RESTORE_MB"
#: (§11, P7) The line saying that a restore waits for the hosting provider's block to end, which the developer decided
#: word for word: ``pending`` prints it for a pending restore the last start found blocked, or on an instance blocked
#: now; a confirmation on a blocked instance prints it after its usual lines. Pinned whole.
INSTANCE_BLOCKED_LINE = "⚠️  The hosting provider blocked this instance: the restore waits until it is unblocked (instance_blocked)"
#: Why a start left a restore pending (contract §2, §10, §11): each ``waiting`` line of ``pending`` ends with its code.
WAIT_REASONS = ["backup_running", "other_data_directory", "server_running", "instance_blocked"]
#: (§11) The block now, as a test sets it: the value of ``LIBREFOLIO_BLOCKED`` (``None``: unset), and how
#: ``instance_blocked()`` reads it. A value that cannot be read counts as blocked.
BLOCKED_NOW = [pytest.param("true", "blocked", id="blocked-now"), pytest.param("maybe", "unreadable", id="unreadable-now")]
BLOCK_NOW = [*BLOCKED_NOW, pytest.param(None, "not blocked", id="unset-now")]


# =============================================================================
# Lot B3's names, the commands, the terminal
# =============================================================================


def product(name: str) -> ModuleType:
    """A module of the application, imported when a test needs it: this file collects before lot B3's modules exist."""
    return importlib.import_module(f"backend.app.{name}")


def apply_module() -> ModuleType:
    return product("services.platform.instance_backup.apply")


def state_path(root: Path) -> Path:
    """``.restore/restore.json``, as ``paths.restore_state_path`` gives it (lot B3)."""
    return product("services.platform.instance_backup.paths").restore_state_path(root)


def optional(module: str) -> ModuleType | None:
    try:
        return product(module)
    except ModuleNotFoundError:
        return None


class OsWithoutKill:
    """``os`` as ``restart`` sees it, ``kill`` recorded instead of sent."""

    def __init__(self, calls: list) -> None:
        self._calls = calls

    def __getattr__(self, name: str) -> Any:
        return getattr(os, name)

    def kill(self, pid: int, sig: int) -> None:
        self._calls.append((pid, sig))


@pytest.fixture(autouse=True)
def no_restart(monkeypatch) -> Iterator[list]:
    """No signal reaches this process; at the end of each test, the command line restarted nothing: a confirmed restore
    waits for the next start."""
    signals: list = []
    restart = optional("services.platform.instance_backup.restart")
    if restart is not None:
        monkeypatch.setattr(restart, "send_signal", lambda pid, sig: signals.append((pid, sig)), raising=False)
        monkeypatch.setattr(restart, "os", OsWithoutKill(signals), raising=False)
    yield signals
    assert signals == [], f"the command line sent a signal: {signals}"


@pytest.fixture(autouse=True)
def no_inherited_block(monkeypatch) -> None:
    """§11: a confirmation on a blocked instance says that the restore waits for the unblock, and the block is read from
    this process's environment at each call. The ``LIBREFOLIO_BLOCKED`` a developer's shell may carry is removed for
    every test: a test sees only the block it sets itself."""
    monkeypatch.delenv(BLOCKED_VARIABLE, raising=False)


@pytest.fixture(autouse=True)
def no_inherited_restore_limit(monkeypatch) -> None:
    """B-35: every ``restore`` reads ``LIBREFOLIO_BACKUP_MAX_RESTORE_MB``. The one a developer's shell may carry is removed
    for every test: a test of the limit sets its own (``limits``)."""
    monkeypatch.delenv(RESTORE_LIMIT_VARIABLE, raising=False)


def block_as_read() -> str:
    """How ``config.platform.instance_blocked()`` reads the block now: ``blocked``, ``not blocked`` or ``unreadable``."""
    try:
        return "blocked" if instance_blocked() else "not blocked"
    except ValueError:
        return "unreadable"


def block_now(monkeypatch, value: str | None, as_read: str) -> str:
    """The block now: ``LIBREFOLIO_BLOCKED`` set to ``value`` (``None``: removed), checked as ``instance_blocked()``
    reads it (``as_read``); how a failure names it."""
    if value is None:
        monkeypatch.delenv(BLOCKED_VARIABLE, raising=False)
    else:
        monkeypatch.setenv(BLOCKED_VARIABLE, value)
    described = f"{BLOCKED_VARIABLE} unset" if value is None else f"{BLOCKED_VARIABLE}={value!r}"
    assert block_as_read() == as_read, f"precondition: instance_blocked() reads {described} as {as_read}, not {block_as_read()}"
    return described


def run(*argv: str) -> int:
    """``dev.py backup <argv>``: parsed as ``register_subparser`` declares it, then run."""
    parser = argparse.ArgumentParser(prog="dev.py")
    backup_cli.register_subparser(parser.add_subparsers(dest="command"))
    try:
        args = parser.parse_args(["backup", *argv])
    except SystemExit as exc:
        pytest.fail(f"dev.py backup {' '.join(argv)}: the command line does not take these arguments (argparse exit {exc.code})")
    try:
        return args.func(args)
    except Exception as exc:
        pytest.fail(f"dev.py backup {' '.join(argv)} raised {type(exc).__name__} ({exc}): the user would get a traceback instead of a message")


@contextmanager
def stdin_with(monkeypatch, typed: str, *, terminal: bool) -> Iterator[None]:
    """``sys.stdin`` a terminal (a pty) or a pipe, ``typed`` and a line break waiting in it."""
    if terminal:
        keep, read_end = pty.openpty()
        os.write(keep, f"{typed}\n".encode())
    else:
        read_end, write_end = os.pipe()
        os.write(write_end, f"{typed}\n".encode())
        os.close(write_end)
        keep = None
    reader = open(read_end, encoding="utf-8")
    monkeypatch.setattr(sys, "stdin", reader)
    try:
        yield
    finally:
        reader.close()
        if keep is not None:
            os.close(keep)


def instance(tmp_path: Path, monkeypatch) -> Path:
    """The data directory of the commands: the production one they see, with its own small database and files."""
    return cli.point_at(monkeypatch, cli.make_data_dir(tmp_path / "instance"))


def live(root: Path) -> tuple[list[str], str]:
    """What a restore must not touch before the next start: every path but ``.restore``, and the live database."""
    return cli.outside_restore(root), cli.sha256_of(root / DATABASE_ENTRY)


def nothing_pending(root: Path) -> None:
    assert not state_path(root).exists(), f"nothing is pending: {sorted(path.name for path in restore_dir(root).iterdir())}"
    assert cli.stages_left(root) == [], f"the copy is removed: {cli.stages_left(root)}"


def write_state(root: Path, status: str, stage_id: str = "0123456789abcdef0123456789abcdef", **extra: Any) -> bytes:
    """A restore in phase ``status``, as a start leaves it on disk, any field replaced by ``extra``: its bytes."""
    apply = apply_module()
    fields: dict[str, Any] = {
        "status": status,
        "stage_id": stage_id,
        "data_dir": str(root.resolve()),
        "confirmed_at": CONFIRMED_AT,
        "confirmed_by": "cli",
        "backup_created_at": CONFIRMED_AT - timedelta(days=1),
        "backup_app_version": "v1.2.0",
        "action": "same",
    }
    if status in ("applying", "applied", "rolling_back"):
        fields["swap"] = [apply.SwapEntry(name=name, live=True, staged=True) for name in ("sqlite", "custom-uploads", "broker_reports", "scenario_catalog")]
        fields["boot"] = apply.Boot(pid=999_999, started=1_760_000_000.0)
    if status in ("applied", "committed"):
        fields["applied_at"] = FINISHED_AT - timedelta(minutes=5)
    if status in TERMINAL:
        fields["finished_at"] = FINISHED_AT
    if status in ("rolling_back", "rolled_back"):
        fields["reason"] = "first_start_failed"
    state = apply.RestoreState(**{**fields, **extra})
    path = state_path(root)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_text(state.model_dump_json(), encoding="utf-8")
    path.chmod(0o600)
    return path.read_bytes()


def confirmed_with_yes(root: Path, tmp_path: Path, database: Path, capsys) -> str:
    """An archive checked and confirmed with ``--yes``: the stage of the pending restore."""
    assert run("restore", str(cli.restorable(tmp_path / "first", database)), "--yes") == 0, f"precondition: a pending restore: {capsys.readouterr().out}"
    capsys.readouterr()
    stages = cli.stages_left(root)
    assert len(stages) == 1, f"precondition: the pending restore's copy: {stages}"
    return stages[0]


# =============================================================================
# (a) restore ARCHIVE --yes
# =============================================================================


def test_restore_with_yes_confirms_and_the_restore_waits_for_the_next_start(tmp_path, monkeypatch, capsys, head_database):
    print_section("dev.py backup restore ARCHIVE --yes")
    root = instance(tmp_path, monkeypatch)
    archive = cli.restorable(tmp_path, head_database)
    before = live(root)
    code = run("restore", str(archive), "--yes")
    out = capsys.readouterr().out
    assert code == 0, f"a restorable archive, confirmed: exit 0: {out}"
    assert "Administrators: ada_admin, zoe_admin" in out, f"the check's report is printed first, as --dry-run prints it: {out}"
    assert "waits for the next start" in out and "✅" in out, f"the restore waits for the next start: {out}"
    lines = out.splitlines()
    confirmed_at = next(index for index, line in enumerate(lines) if "waits for the next start" in line)
    missing = [line for line in cli.ACCOUNT_LINK_LINES if line not in lines[:confirmed_at]]
    assert missing == [], f"the report says, before the confirmation, the notice on the invitations and links, verbatim: {missing} not before line {confirmed_at} of {out}"
    stages = cli.stages_left(root)
    assert len(stages) == 1, f"the copy is kept, for the next start: {stages}"
    path = state_path(root)
    assert stat.S_IMODE(path.lstat().st_mode) == 0o600, f"the state is readable by its owner only: {oct(stat.S_IMODE(path.lstat().st_mode))}"
    state = json.loads(path.read_text(encoding="utf-8"))
    expected = {"status": "pending", "stage_id": stages[0], "confirmed_by": "cli", "data_dir": str(root.resolve()), "action": "same", "backup_app_version": cli.APP_VERSION}
    assert {key: state.get(key) for key in expected} == expected, f"the restore waiting: {state}"
    assert live(root) == before, "nothing of the live data directory changes before the next start"
    print_success(f"exit 0, pending {stages[0]}, copy kept")


#: (§11, P7) ``restore ARCHIVE --yes`` and the hosting provider's block: the value of ``LIBREFOLIO_BLOCKED`` (``None``:
#: unset), how ``instance_blocked()`` reads it, and whether the confirmation ends with the decided line. A value that
#: cannot be read counts as blocked.
CONFIRMED_UNDER_A_BLOCK = [
    pytest.param("true", "blocked", True, id="blocked"),
    pytest.param("maybe", "unreadable", True, id="unreadable-counts-as-blocked"),
    pytest.param(None, "not blocked", False, id="unset"),
]


@pytest.mark.parametrize(("value", "as_read", "said"), CONFIRMED_UNDER_A_BLOCK)
def test_restore_with_yes_on_a_blocked_instance_confirms_and_then_says_that_the_restore_waits_for_the_unblock(tmp_path, monkeypatch, capsys, head_database, value, as_read, said):
    """(a) §11, P7: the command line does not refuse on a blocked instance — whoever runs the server, the hosting
    provider, may prepare a restore for the unblock — and says so. Exit 0; the report and the usual confirmation lines,
    the restore pending with its copy kept, the live data as it was; then one more line, the decided one, once and
    last. Unset, the confirmation is the usual one, without that line."""
    root = instance(tmp_path, monkeypatch)
    archive = cli.restorable(tmp_path, head_database)
    before = live(root)
    described = block_now(monkeypatch, value, as_read)
    code = run("restore", str(archive), "--yes")
    out = capsys.readouterr().out
    lines = out.splitlines()
    confirmed_at = next((index for index, line in enumerate(lines) if line.startswith("✅") and "waits for the next start" in line), None)
    assert code == 0 and confirmed_at is not None, f"{described}: confirmed, exit 0, the usual ✅ that the restore waits for the next start: exit {code}: {out}"
    assert "Administrators: ada_admin, zoe_admin" in "\n".join(lines[:confirmed_at]), f"{described}: the check's report first, as usual: {out}"
    stages = cli.stages_left(root)
    assert len(stages) == 1, f"{described}: the copy is kept, for the start after the unblock: {stages}"
    state = json.loads(state_path(root).read_text(encoding="utf-8"))
    assert (state["status"], state["stage_id"], state["confirmed_by"]) == ("pending", stages[0], "cli"), f"{described}: the restore pending, as usual: {state}"
    assert live(root) == before, f"{described}: nothing of the live data directory changes before the next start"
    if said:
        printed = [line for line in lines if line.strip()]
        assert lines.count(INSTANCE_BLOCKED_LINE) == 1, f"{described}: the decided line, once and word for word: {INSTANCE_BLOCKED_LINE!r} in {lines}"
        assert lines.index(INSTANCE_BLOCKED_LINE) > confirmed_at and printed[-1] == INSTANCE_BLOCKED_LINE, f"{described}: the usual confirmation lines, then the decided line, the last printed: {lines[confirmed_at:]}"
    else:
        assert [line for line in lines if "instance_blocked" in line] == [], f"{described}: the usual confirmation, nothing about a block: {lines[confirmed_at:]}"
    print_success(f"{described}: exit 0, pending, {'then the decided line' if said else 'no line about a block'}")


# =============================================================================
# (b) The confirmation without --yes
# =============================================================================


@pytest.mark.parametrize("typed", ["restore", " restore "])
def test_typing_restore_on_a_terminal_confirms(tmp_path, monkeypatch, capsys, head_database, typed):
    """(b) The word, the spaces around it ignored."""
    print_section("The confirmation")
    root = instance(tmp_path, monkeypatch)
    archive = cli.restorable(tmp_path, head_database)
    with stdin_with(monkeypatch, typed, terminal=True):
        code = run("restore", str(archive))
    out = capsys.readouterr().out
    assert code == 0 and "waits for the next start" in out, f"{typed!r} typed on a terminal confirms: exit {code}: {out}"
    state = json.loads(state_path(root).read_text(encoding="utf-8"))
    assert (state["status"], state["stage_id"], state["confirmed_by"]) == ("pending", cli.stages_left(root)[0], "cli"), f"pending: {state}"
    print_success(f"{typed!r} typed → pending")


@pytest.mark.parametrize("typed", ["Restore", "no", "y", "yes", ""])
def test_anything_else_typed_on_a_terminal_declines(tmp_path, monkeypatch, capsys, head_database, typed):
    root = instance(tmp_path, monkeypatch)
    archive = cli.restorable(tmp_path, head_database)
    before = live(root)
    with stdin_with(monkeypatch, typed, terminal=True):
        code = run("restore", str(archive))
    out = capsys.readouterr().out
    assert code == 1 and "Nothing restored" in out, f"{typed!r} typed: declined, exit 1: exit {code}: {out}"
    nothing_pending(root)
    assert live(root) == before, f"{typed!r}: the live data directory as it was"
    print_success(f"{typed!r} → Nothing restored")


def test_without_a_terminal_and_without_yes_nothing_is_restored(tmp_path, monkeypatch, capsys, head_database):
    """(b) A script, a pipe: nobody can type the word. ``restore`` waiting in the pipe does not confirm; the message
    names ``--yes``."""
    root = instance(tmp_path, monkeypatch)
    archive = cli.restorable(tmp_path, head_database)
    with stdin_with(monkeypatch, "restore", terminal=False):
        code = run("restore", str(archive))
    out = capsys.readouterr().out
    assert code == 1 and "--yes" in out, f"not a terminal: refused, exit 1, --yes named: exit {code}: {out}"
    nothing_pending(root)
    print_success("not a terminal → refused, --yes named")


# =============================================================================
# (c) Refused before or after the check
# =============================================================================


def test_a_restore_already_pending_stops_the_next_before_its_check(tmp_path, monkeypatch, capsys, head_database):
    print_section("Refusals")
    root = instance(tmp_path, monkeypatch)
    pending_stage = confirmed_with_yes(root, tmp_path, head_database, capsys)
    before = (state_path(root).read_bytes(), cli.listing(stage_dir(root, pending_stage)))
    code = run("restore", str(cli.restorable(tmp_path / "second", head_database)), "--yes")
    out = capsys.readouterr().out
    assert code == 1 and "(restore_already_pending)" in out, f"a restore already pending: exit 1 (restore_already_pending): exit {code}: {out}"
    assert "… unpacking" not in out and cli.stages_left(root) == [pending_stage], f"stopped before the check: no copy made: {cli.stages_left(root)}: {out}"
    assert (state_path(root).read_bytes(), cli.listing(stage_dir(root, pending_stage))) == before, "the pending restore and its copy as they were"
    print_success("(restore_already_pending), before the check")


@pytest.mark.parametrize("phase", ACTIVE[1:])
def test_a_restore_being_applied_stops_the_next_before_its_check(tmp_path, monkeypatch, capsys, head_database, phase):
    root = instance(tmp_path, monkeypatch)
    before = write_state(root, phase)
    code = run("restore", str(cli.restorable(tmp_path, head_database)), "--yes")
    out = capsys.readouterr().out
    assert code == 1 and "(restore_already_pending)" in out, f"{phase}: exit 1 (restore_already_pending): exit {code}: {out}"
    assert cli.stages_left(root) == [] and state_path(root).read_bytes() == before, f"{phase}: no copy made, the state as it was"
    print_success(f"{phase}: (restore_already_pending)")


def test_a_dry_run_while_a_restore_is_pending_is_as_before(tmp_path, monkeypatch, capsys, head_database):
    """(c) ``--dry-run`` is unchanged: it checks on its own copy, removes it, and leaves the pending restore alone."""
    root = instance(tmp_path, monkeypatch)
    pending_stage = confirmed_with_yes(root, tmp_path, head_database, capsys)
    before = (state_path(root).read_bytes(), cli.listing(stage_dir(root, pending_stage)))
    code = run("restore", str(cli.restorable(tmp_path / "second", head_database)), "--dry-run")
    out = capsys.readouterr().out
    assert code == 0, f"a dry run while a restore is pending: exit 0: {out}"
    assert cli.stages_left(root) == [pending_stage], f"the dry run's copy is removed, the pending one kept: {cli.stages_left(root)}"
    assert (state_path(root).read_bytes(), cli.listing(stage_dir(root, pending_stage))) == before, "the pending restore and its copy as they were"
    print_success("--dry-run: exit 0, pending restore untouched")


def test_a_backup_without_an_active_administrator_is_not_restored(tmp_path, monkeypatch, capsys, head_database):
    root = instance(tmp_path, monkeypatch)
    code = run("restore", str(cli.restorable(tmp_path, head_database, cli.WITHOUT_ADMINISTRATOR)), "--yes")
    out = capsys.readouterr().out
    assert code == 1, f"blocked: exit 1, even with --yes: {out}"
    nothing_pending(root)
    print_success("no active administrator → exit 1, copy removed")


@pytest.mark.parametrize(("error", "error_code"), [pytest.param("head-moved", "restore_stage_outdated", id="head-moved"), *(pytest.param(name, code, id=code) for name, code in CONFIRM_ERRORS.items())])
def test_a_confirmation_that_fails_says_its_code_and_removes_the_copy(tmp_path, monkeypatch, capsys, head_database, error, error_code):
    """(c) After a good check, ``confirm_restore`` refuses: the head moved since the check (for real), or each of its
    errors raised (a restore confirmed elsewhere meanwhile, the copy gone, …). One ❌ line, ending with the code."""
    root = instance(tmp_path, monkeypatch)
    apply = apply_module()
    if error == "head-moved":
        monkeypatch.setattr(apply, "alembic_head_revision", lambda: "999_from_an_update")
    else:

        def refuse(*args: Any, **kwargs: Any) -> Any:
            raise getattr(apply, error)("simulated refusal")

        monkeypatch.setattr(apply, "confirm_restore", refuse)
    code = run("restore", str(cli.restorable(tmp_path, head_database)), "--yes")
    out = capsys.readouterr().out
    refusals = [line for line in out.splitlines() if line.startswith("❌")]
    assert code == 1 and len(refusals) == 1 and refusals[0].rstrip().endswith(f"({error_code})"), f"exit 1, one ❌ line ending with ({error_code}): exit {code}: {out}"
    nothing_pending(root)
    print_success(f"{error}: ({error_code})")


# =============================================================================
# (d) pending
# =============================================================================


def test_pending_without_a_restore_says_so_and_creates_nothing(tmp_path, monkeypatch, capsys):
    print_section("dev.py backup pending")
    root = instance(tmp_path, monkeypatch)
    before = cli.listing(root)
    assert run("pending") == 0, "pending is exit 0, restore or not"
    out = capsys.readouterr().out
    assert "no restore" in out.lower(), f"no restore: {out}"
    assert cli.listing(root) == before, f"a read creates nothing: {sorted(set(cli.listing(root)) - set(before))}"
    print_success("no restore")


@pytest.mark.parametrize("phase", ACTIVE + TERMINAL)
def test_pending_shows_each_phase_and_exits_0(tmp_path, monkeypatch, capsys, phase):
    root = instance(tmp_path, monkeypatch)
    write_state(root, phase)
    assert run("pending") == 0, f"{phase}: exit 0"
    out = capsys.readouterr().out
    assert "no restore" not in out.lower(), f"{phase}: a restore is shown: {out}"
    print_success(f"{phase}: shown")


def ends_a_line(out: str, code: str) -> bool:
    """Whether a line of ``out`` ends with ``(code)``: how the command line says a stable code."""
    return any(line.rstrip().endswith(f"({code})") for line in out.splitlines())


def waiting_for(root: Path, waiting: str | None) -> None:
    """A pending restore, and what the last start recorded on it (``None``: nothing): the reason written in the state file
    as a start writes it, whatever the models of this LibreFolio accept — what ``pending`` prints is under test."""
    write_state(root, "pending")
    if waiting is None:
        return
    path = state_path(root)
    record = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(json.dumps({**record, "waiting": waiting}), encoding="utf-8")


def waiting_codes(out: str) -> list[str]:
    """Why ``pending`` says the restore waits: the code each of its lines ends with, among ``WAIT_REASONS``, in order."""
    return [code for line in out.splitlines() for code in WAIT_REASONS if line.rstrip().endswith(f"({code})")]


@pytest.mark.parametrize("waiting", WAIT_REASONS)
def test_pending_ends_the_waiting_line_with_its_code(tmp_path, monkeypatch, capsys, waiting):
    root = instance(tmp_path, monkeypatch)
    waiting_for(root, waiting)
    assert run("pending") == 0, "a waiting restore: exit 0"
    out = capsys.readouterr().out
    assert ends_a_line(out, waiting), f"a line ends with ({waiting}): {out}"
    print_success(f"waiting: ({waiting})")


#: (§11, P7, decided) What the last start recorded on a pending restore (``None``: nothing), for ``pending``.
RECORDED = [pytest.param(None, id="nothing-recorded"), *(pytest.param(reason, id=f"{reason}-recorded") for reason in WAIT_REASONS)]


@pytest.mark.parametrize(("value", "as_read"), BLOCK_NOW)
@pytest.mark.parametrize("recorded", RECORDED)
def test_pending_says_once_that_a_pending_restore_waits_for_the_unblock_after_what_the_last_start_recorded(tmp_path, monkeypatch, capsys, recorded, value, as_read):
    """(d) §11, P7, decided: ``pending`` reads the block live. The decided line is printed, once, when the last start
    recorded ``instance_blocked`` (even unset now: it tells what that start found), or when the instance is blocked now
    (``true``, or a value that cannot be read) and the last start did not record ``other_data_directory``. That one
    wins, as at a start: a copy of another data directory never applies the restore, and the block line would promise
    it. Another reason recorded and the instance blocked now: both lines, the recorded one first, then the block's.
    Otherwise no such line, and the recorded reason as before."""
    root = instance(tmp_path, monkeypatch)
    waiting_for(root, recorded)
    described = block_now(monkeypatch, value, as_read)
    expected = [recorded] if recorded not in (None, "instance_blocked") else []
    if recorded == "instance_blocked" or (as_read != "not blocked" and recorded != "other_data_directory"):
        expected.append("instance_blocked")
    code = run("pending")
    out = capsys.readouterr().out
    case = f"{recorded or 'nothing'} recorded, {described}"
    assert code == 0 and "no restore" not in out.lower(), f"{case}: the pending restore shown, exit 0: exit {code}: {out}"
    assert waiting_codes(out) == expected, f"{case}: why it waits, in this order: {expected}, not {waiting_codes(out)}: {out}"
    assert out.splitlines().count(INSTANCE_BLOCKED_LINE) == expected.count("instance_blocked"), f"{case}: the decided line word for word, {expected.count('instance_blocked')} time(s): {out}"
    print_success(f"{case}: {', '.join(f'({code})' for code in expected) or 'no waiting line'}")


#: (§11, P7, decided) What ``pending`` finds that is not a pending restore: a restore in progress (applying, applied,
#: rolling back), committed or rolled back — and no restore at all.
NOT_PENDING = [pytest.param(None, id="no-restore"), *(pytest.param(phase, id=phase) for phase in [*ACTIVE[1:], *TERMINAL])]


@pytest.mark.parametrize(("value", "as_read"), BLOCKED_NOW)
@pytest.mark.parametrize("phase", NOT_PENDING)
def test_pending_never_says_that_anything_but_a_pending_restore_waits_for_the_unblock(tmp_path, monkeypatch, capsys, phase, value, as_read):
    """(d) §11, P7, decided: the block holds back a restore waiting for a start, nothing else. On an instance blocked now,
    or whose block cannot be read, a restore that is not pending — as a start leaves it on disk — is shown as it is,
    exit 0, and ``pending`` prints no line about the block; without a restore, «no restore», and nothing more."""
    root = instance(tmp_path, monkeypatch)
    if phase is not None:
        write_state(root, phase)
    described = block_now(monkeypatch, value, as_read)
    code = run("pending")
    out = capsys.readouterr().out
    case = f"{phase or 'no restore'}, {described}"
    assert code == 0 and ("no restore" in out.lower()) == (phase is None), f"{case}: shown as it is, exit 0: exit {code}: {out}"
    assert [line for line in out.splitlines() if "instance_blocked" in line] == [], f"{case}: no line about the block: {out}"
    print_success(f"{case}: nothing about the block")


#: What a state may hold that a terminal would obey: an escape sequence clearing the screen, a bell, a window title, a C1
#: control (CSI), a carriage return, a backspace. Each must reach the terminal as ``?``.
HOSTILE = {
    "backup_app_version": ("1.3\x1b[2J\x07", "1.3?[2J?"),
    "confirmed_by": ("cli\x1b]0;owned\x07\x9b31m\r\x08", "cli?]0;owned??31m??"),
    "data_dir": ("/srv/data\x1b[31m", "/srv/data?[31m"),
}


def test_pending_prints_no_control_character_from_a_state(tmp_path, monkeypatch, capsys):
    """(d) §10: a state is read from disk, and what it holds reaches the operator's terminal only through ``_safe``:
    every character that is not printable becomes ``?``, escape sequences included. The ``other_data_directory`` line
    prints ``data_dir`` too."""
    root = instance(tmp_path, monkeypatch)
    write_state(root, "pending", waiting="other_data_directory", **{field: raw for field, (raw, _shown) in HOSTILE.items()})
    assert run("pending") == 0, "a pending restore: exit 0"
    out = capsys.readouterr().out
    # Split on line feeds only: a carriage return left in the output must be seen, not taken for a line break.
    unprintable = sorted({repr(char) for line in out.split("\n") for char in line if not char.isprintable()})
    assert unprintable == [], f"no control character reaches the terminal: {unprintable} in {out!r}"
    missing = [shown for _raw, shown in HOSTILE.values() if shown not in out]
    assert missing == [], f"each control character shown as ?: {missing} not in {out!r}"
    print_success("pending: control characters shown as ?")


@pytest.mark.parametrize("reason", ["first_start_failed", "swap_interrupted", "swap_failed", "stage_missing"])
def test_pending_ends_the_reason_line_of_a_rolled_back_restore_with_its_code(tmp_path, monkeypatch, capsys, reason):
    root = instance(tmp_path, monkeypatch)
    write_state(root, "rolled_back", reason=reason)
    assert run("pending") == 0, "a rolled back restore: exit 0"
    out = capsys.readouterr().out
    assert ends_a_line(out, reason), f"a line ends with ({reason}): {out}"
    print_success(f"rolled back: ({reason})")


# =============================================================================
# (e) pending --cancel
# =============================================================================


def test_cancel_removes_a_pending_restore_and_its_copy(tmp_path, monkeypatch, capsys, head_database):
    print_section("dev.py backup pending --cancel")
    root = instance(tmp_path, monkeypatch)
    confirmed_with_yes(root, tmp_path, head_database, capsys)
    before = live(root)
    assert run("pending", "--cancel") == 0, f"a pending restore is cancelled: {capsys.readouterr().out}"
    nothing_pending(root)
    assert live(root) == before, "the live data directory as it was"
    print_success("cancelled, copy removed")


def refused_as_not_pending(capsys) -> None:
    """``pending --cancel`` with nothing pending: exit 1, one ❌ line ending with ``(restore_not_pending)``."""
    code = run("pending", "--cancel")
    out = capsys.readouterr().out
    refusals = [line for line in out.splitlines() if line.startswith("❌")]
    assert code == 1 and len(refusals) == 1 and refusals[0].rstrip().endswith("(restore_not_pending)"), f"nothing to cancel: exit 1, one ❌ line ending with (restore_not_pending): exit {code}: {out}"


@pytest.mark.parametrize("found", ["nothing", "after-a-dry-run"])
def test_cancel_without_a_state_file_creates_nothing(tmp_path, monkeypatch, capsys, head_database, found):
    """(e) No state file, in a data directory that never saw a restore or after a dry run (``.restore/stage`` and its
    lock there): refused, and nothing created, not even ``.restore/apply.lock``."""
    root = instance(tmp_path, monkeypatch)
    if found == "after-a-dry-run":
        assert run("restore", str(cli.restorable(tmp_path, head_database)), "--dry-run") == 0, f"precondition: a dry run: {capsys.readouterr().out}"
        capsys.readouterr()
    before = cli.listing(root)
    refused_as_not_pending(capsys)
    assert cli.listing(root) == before, f"{found}: nothing created: {sorted(set(cli.listing(root)) - set(before))}"
    print_success(f"{found}: (restore_not_pending), nothing created")


@pytest.mark.parametrize("phase", [*ACTIVE[1:], *TERMINAL])
def test_cancel_without_a_pending_restore_exits_1(tmp_path, monkeypatch, capsys, phase):
    root = instance(tmp_path, monkeypatch)
    before = write_state(root, phase)
    refused_as_not_pending(capsys)
    assert state_path(root).read_bytes() == before, f"{phase}: the state as it was"
    print_success(f"{phase}: (restore_not_pending)")


# =============================================================================
# (f) The script, the help
# =============================================================================


def test_the_script_shows_that_no_restore_is_pending(tmp_path):
    data = cli.make_data_dir(tmp_path / "instance").resolve()
    done = cli.script("pending", env=cli.child_env(data), cwd=tmp_path)
    assert done.returncode == 0 and "no restore" in done.stdout.lower(), f"python scripts/backup_cli.py pending: exit {done.returncode}\n{done.stdout[-cli.TAIL:]}{done.stderr[-cli.TAIL:]}"
    print_success("script pending → 0, no restore")


def test_the_help_names_yes_and_cancel(monkeypatch, capsys):
    restore_help = cli.help_of(monkeypatch, capsys, "backup", "restore")
    assert "--yes" in restore_help and "--dry-run" in restore_help, f"restore --help: {restore_help}"
    pending_help = cli.help_of(monkeypatch, capsys, "backup", "pending")
    assert "--cancel" in pending_help, f"pending --help: {pending_help}"
    print_success("--yes, --cancel")


# =============================================================================
# (g) B-32 — a state that cannot be read, a cancel refused or half done
# =============================================================================


#: (B-32, §2) What a cancel that dropped the restore says: with its copy (unchanged), or without it, then why.
DROPPED_WITH_COPY = "✅ The restore waiting for the next start was dropped, with its copy: the data stays as it is"
DROPPED = "✅ The restore waiting for the next start was dropped: the data stays as it is"
COPY_KEPT = "⚠️  Its checked copy could not be removed: it goes when its check expires"
#: How the command line starts a line it says; whatever else reaches standard output (a log record) is not one.
SIGNS = ("✅", "⚠️", "❌", "ℹ️", "⏳")


def unreadable_line(error: int) -> str:
    """(B-32, §3) The line of a state the file system cannot read, ``error``'s reason in it: verbatim, never a path."""
    return f"❌ The state of the restore cannot be read: {os.strerror(error)} (restore_state_unreadable)"


def cancel_failed_line(error: int) -> str:
    """(B-32, §2) The line of a cancel refused before the restore is dropped, ``error``'s reason in it: verbatim."""
    return f"❌ The restore could not be cancelled: {os.strerror(error)}. It still waits for the next start (restore_cancel_failed)"


def said(out: str) -> list[str]:
    """The lines the command line said in ``out``, in their order: those starting with one of its signs."""
    return [line for line in out.splitlines() if line.startswith(SIGNS)]


def refused_for(path: Path, error: int, real: Any) -> Any:
    """``real`` (``os.open``, ``os.unlink``, ``os.remove``) refusing ``path`` with ``error``, the real one for any other
    path; a name relative to a folder descriptor is matched by its name."""

    def refusing(target: Any, *args: Any, dir_fd: int | None = None, **kwargs: Any) -> Any:
        name = os.fspath(target)
        if name == os.fspath(path) or (dir_fd is not None and name == path.name):
            raise OSError(error, os.strerror(error), name)
        return real(target, *args, dir_fd=dir_fd, **kwargs)

    return refusing


def unreadable_state(monkeypatch, root: Path, error: int = errno.EACCES) -> None:
    """``.restore/restore.json`` a file the file system will not open (``error``: EACCES, as for a file of mode 000, or
    EIO): ``os.open`` of that path refuses, every other open is the real one, and the file stays on disk as it was.
    Checked before the command runs."""
    path = state_path(root)
    monkeypatch.setattr(os, "open", refused_for(path, error, os.open))
    try:
        os.close(os.open(path, os.O_RDONLY))
    except OSError as exc:
        assert exc.errno == error, f"precondition: the state is refused with {errno.errorcode[error]}, not {exc!r}"
    else:
        pytest.fail("precondition: the state of the restore must be a file the file system will not open")


def state_removal_refused(monkeypatch, root: Path, error: int = errno.EPERM) -> None:
    """The removal of ``.restore/restore.json`` refused (``error``: EPERM, as for a file the system will not let go),
    every other removal the real one: the cancel fails before the restore is dropped."""
    path = state_path(root)
    for name in ("unlink", "remove"):
        monkeypatch.setattr(os, name, refused_for(path, error, getattr(os, name)))


def copy_removal_raises(monkeypatch) -> list[str]:
    """The removal of the checked copy raising (EACCES) once the restore is dropped, as B-31 meets it: ``remove_stage``
    as ``cancel_restore`` calls it (through ``_remove_leftovers``), the copy left whole. The stages it was asked for."""
    asked: list[str] = []

    def refuse(data_dir: Path, stage_id: str) -> None:
        asked.append(stage_id)
        raise OSError(errno.EACCES, os.strerror(errno.EACCES))

    monkeypatch.setattr(apply_module(), "remove_stage", refuse)
    return asked


@contextmanager
def mode_for_a_while(path: Path, mode: int) -> Iterator[None]:
    """``path`` given ``mode`` while the command runs — a refusal of the file system itself — then its own mode again,
    the command failed or not, so that the test reads the state back and ``tmp_path`` can be removed."""
    own = stat.S_IMODE(path.lstat().st_mode)
    path.chmod(mode)
    try:
        yield
    finally:
        path.chmod(own)


@pytest.mark.parametrize("error", [errno.EACCES, errno.EIO], ids=["permission-denied", "input-output-error"])
def test_pending_says_that_the_state_cannot_be_read_and_exits_1(tmp_path, monkeypatch, capsys, error):
    """(g) §3, as B-33 §3 amends it (l): a state the file system cannot read is never «no restore». Exit 1, one ❌ line
    with ``restore_state_unreadable`` and the reason ``io`` (B-33; it was the system's words), the ``--recover`` command,
    never the path, no traceback; the state as it was."""
    print_section("B-32: a state that cannot be read")
    root = instance(tmp_path, monkeypatch)
    before = write_state(root, "pending")
    unreadable_state(monkeypatch, root, error)
    code = run("pending")
    out = capsys.readouterr().out
    assert_said_unreadable(code, out, "io", root)
    assert state_path(root).read_bytes() == before, "the state as it was"
    print_success(f"{errno.errorcode[error]}: (restore_state_unreadable), exit 1")


def test_cancel_of_a_state_that_cannot_be_read_says_so_and_keeps_the_restore(tmp_path, monkeypatch, capsys, head_database):
    """(g) §2, §3: today ``(restore_not_pending)`` — the restore that may wait taken for none. The unreadable line,
    exit 1; the state and the copy of the pending restore as they were."""
    root = instance(tmp_path, monkeypatch)
    stage = confirmed_with_yes(root, tmp_path, head_database, capsys)
    before = (state_path(root).read_bytes(), cli.listing(stage_dir(root, stage)))
    unreadable_state(monkeypatch, root)
    code = run("pending", "--cancel")
    out = capsys.readouterr().out
    assert (code, said(out)) == (1, [unreadable_line(errno.EACCES)]), f"exit 1 and one line, verbatim {unreadable_line(errno.EACCES)!r}, never (restore_not_pending): exit {code}: {out}"
    assert "Traceback" not in out, f"no traceback: {out}"
    assert (state_path(root).read_bytes(), cli.listing(stage_dir(root, stage))) == before, "the pending restore and its copy as they were"
    print_success("--cancel: (restore_state_unreadable), the restore kept")


#: (B-32, §2) A cancel refused before the restore is dropped, and the system's reason: the state's removal refused
#: (EPERM); or ``.restore`` read-only for real (EACCES; skipped as root), which refuses the removal all the same.
CANCEL_REFUSED = [
    pytest.param("state-removal-refused", errno.EPERM, id="state-removal-refused"),
    pytest.param("restore-folder-read-only", errno.EACCES, id="restore-folder-read-only", marks=cli.needs_permission_checks),
]


@pytest.mark.parametrize(("fault", "error"), CANCEL_REFUSED)
def test_a_cancel_refused_before_the_drop_says_so_and_the_restore_still_waits(tmp_path, monkeypatch, capsys, head_database, fault, error):
    """(g) §2: today the ``OSError`` reaches the user as a traceback. One line, verbatim, its reason in it; exit 1; the
    restore still waits, with its copy."""
    root = instance(tmp_path, monkeypatch)
    stage = confirmed_with_yes(root, tmp_path, head_database, capsys)
    before = (state_path(root).read_bytes(), cli.listing(stage_dir(root, stage)))
    if fault == "state-removal-refused":
        state_removal_refused(monkeypatch, root, error)
        code = run("pending", "--cancel")
    else:
        with mode_for_a_while(restore_dir(root), 0o500):
            code = run("pending", "--cancel")
    out = capsys.readouterr().out
    assert (code, said(out)) == (1, [cancel_failed_line(error)]), f"{fault}: exit 1 and one line, verbatim {cancel_failed_line(error)!r}: exit {code}: {out}"
    assert "Traceback" not in out, f"no traceback: {out}"
    assert (state_path(root).read_bytes(), cli.listing(stage_dir(root, stage))) == before, f"{fault}: the restore still waits, with its copy"
    print_success(f"{fault}: (restore_cancel_failed), the restore kept")


#: (B-32, §2) How the copy's removal fails once the restore is dropped: raising (B-31 logs a WARNING), or leaving it
#: without a word — ``remove_stage`` removes with its errors ignored — the copy's folder read-only for real (skipped as
#: root); or ``.restore/stage`` without its search permission for real (skipped as root): ``remove_stage``'s lstat raises
#: EACCES, and a look at the copy (§2 amended, ``os.lstat``) is refused too — an error other than «not found» counts as
#: the copy still there. The command line tells each by the copy still there.
COPY_LEFT = [
    pytest.param("removal-raises", id="removal-raises"),
    pytest.param("removal-leaves-it", id="removal-leaves-it", marks=cli.needs_permission_checks),
    pytest.param("stage-folder-not-searchable", id="stage-folder-not-searchable", marks=cli.needs_permission_checks),
]


@pytest.mark.parametrize("fault", COPY_LEFT)
def test_a_cancel_whose_copy_stays_says_the_restore_was_dropped_and_its_copy_was_not(tmp_path, monkeypatch, capsys, head_database, fault):
    """(g) §2: today «dropped, with its copy» while the copy is still there. Exactly the dropped line without «with its
    copy», then the ⚠️ line; exit 0; the restore dropped, its copy still there."""
    root = instance(tmp_path, monkeypatch)
    stage = confirmed_with_yes(root, tmp_path, head_database, capsys)
    if fault == "removal-raises":
        asked = copy_removal_raises(monkeypatch)
        code = run("pending", "--cancel")
        assert asked == [stage], f"precondition: the removal of this restore's copy was refused: {asked}"
    else:
        locked, mode = (stage_data_dir(root, stage), 0o500) if fault == "removal-leaves-it" else (stages_dir(root), 0o600)
        with mode_for_a_while(locked, mode):
            code = run("pending", "--cancel")
    out = capsys.readouterr().out
    assert (code, said(out)) == (0, [DROPPED, COPY_KEPT]), f"{fault}: exit 0 and exactly {[DROPPED, COPY_KEPT]}, never «with its copy»: exit {code}: {out}"
    assert not state_path(root).exists() and os.path.lexists(stage_dir(root, stage)), f"{fault}: the restore dropped, its copy still there: {cli.stages_left(root)}"
    print_success(f"{fault}: dropped, then ⚠️ its copy stays")


def test_a_cancel_that_removes_the_copy_still_says_with_its_copy(tmp_path, monkeypatch, capsys, head_database):
    """(g) §2, a guard (green before and after): the usual drop keeps its one line, «with its copy», and the copy goes."""
    root = instance(tmp_path, monkeypatch)
    stage = confirmed_with_yes(root, tmp_path, head_database, capsys)
    code = run("pending", "--cancel")
    out = capsys.readouterr().out
    assert (code, said(out)) == (0, [DROPPED_WITH_COPY]), f"exit 0 and exactly {DROPPED_WITH_COPY!r}: exit {code}: {out}"
    assert not os.path.lexists(stage_dir(root, stage)), "the copy is gone"
    print_success("dropped, with its copy")


def test_restore_with_yes_and_a_state_that_cannot_be_read_stops_before_its_check(tmp_path, monkeypatch, capsys, head_database):
    """(g) §3: today the archive is checked and confirmed over a state nobody could read — a restore that may still
    wait. The unreadable line, exit 1, before the check: no copy made, the state as it was."""
    root = instance(tmp_path, monkeypatch)
    archive = cli.restorable(tmp_path, head_database)
    before = write_state(root, "pending")
    unreadable_state(monkeypatch, root)
    code = run("restore", str(archive), "--yes")
    out = capsys.readouterr().out
    assert (code, said(out)) == (1, [unreadable_line(errno.EACCES)]), f"exit 1 and one line, verbatim {unreadable_line(errno.EACCES)!r}: exit {code}: {out}"
    assert "🔎" not in out and cli.stages_left(root) == [], f"nothing checked, no copy made: {cli.stages_left(root)}: {out}"
    assert state_path(root).read_bytes() == before, "the state as it was, never replaced"
    print_success("restore --yes: (restore_state_unreadable) before the check")


def test_a_dry_run_never_reads_the_state_and_works_as_before(tmp_path, monkeypatch, capsys, head_database):
    """(g) §3, a guard (green before and after): ``--dry-run`` never reads the state of the restore, so one that cannot
    be read changes nothing: exit 0, restorable, the copy removed, the state as it was."""
    root = instance(tmp_path, monkeypatch)
    archive = cli.restorable(tmp_path, head_database)
    before = write_state(root, "pending")
    unreadable_state(monkeypatch, root)
    code = run("restore", str(archive), "--dry-run")
    out = capsys.readouterr().out
    assert code == 0 and cli.RESTORABLE_LINE in out, f"the dry run as before: exit {code}: {out}"
    assert cli.stages_left(root) == [] and state_path(root).read_bytes() == before, f"its copy removed, the state as it was: {cli.stages_left(root)}"
    print_success("--dry-run: as before")


#: (B-32, §3) A state the file system itself refuses, for the script: the state file of mode 000, or ``.restore``
#: without its search permission — which ``lexists`` read as «no state» — (the path, and the mode it is given).
REAL_REFUSALS = [pytest.param("state-file-000", id="state-file-000"), pytest.param("restore-folder-not-searchable", id="restore-folder-not-searchable")]


@cli.needs_permission_checks
@pytest.mark.parametrize("fault", REAL_REFUSALS)
@pytest.mark.parametrize("argv", [("pending",), ("pending", "--cancel")], ids=["pending", "pending-cancel"])
def test_the_script_says_that_a_state_the_file_system_refuses_cannot_be_read(tmp_path, argv, fault):
    """(g) §3, end to end: a real refusal of the file system, in a process of its own. The unreadable line, exit 1, no
    traceback, the state kept."""
    data = cli.make_data_dir(tmp_path / "instance").resolve()
    before = write_state(data, "pending")
    locked, mode = (state_path(data), 0o000) if fault == "state-file-000" else (restore_dir(data), 0o600)
    with mode_for_a_while(locked, mode):
        done = cli.script(*argv, env=cli.child_env(data), cwd=tmp_path)
    expected = unreadable_line(errno.EACCES)
    if argv == ("pending",):
        # B-33 §3 (l): pending says the reason word and what to run, not (g)'s one line.
        assert_said_unreadable(done.returncode, done.stdout, "io", data)
    else:
        assert (done.returncode, said(done.stdout)) == (1, [expected]), f"{' '.join(argv)}, {fault}: exit 1 and one line, verbatim {expected!r}: exit {done.returncode}\n{done.stdout[-cli.TAIL:]}{done.stderr[-cli.TAIL:]}"
    assert "Traceback" not in done.stderr, f"no traceback: {done.stderr[-cli.TAIL:]}"
    assert state_path(data).read_bytes() == before, "the state kept"
    print_success(f"script {' '.join(argv)}, {fault}: (restore_state_unreadable)")


# =============================================================================
# (h) B-18 — restore --instance-key-file
# =============================================================================


#: (B-18) Test keys, never a real one: this instance's own key (K2, generated), a key of 32 characters or more that is
#: not the source's, and two shorter than an instance key may be — one given, one configured as this instance's. The
#: source's key, K1, is ``secure_cases.SOURCE_KEY``.
THIS_KEY = "LibreFolio-b18-this-instance-key-0123456789"
WRONG_KEY = "LibreFolio-b18-not-the-source-key-9876543210"
SHORT_KEY = "LibreFolio-b18-short-key"
UNUSABLE_OWN_KEY = "LibreFolio-b18-own-key-short"
#: (B-18, §2) The lines of the report, verbatim.
KEY_GIVEN_LINE = "   Instance key: not included; given with --instance-key-file"
KEY_INCLUDED_LINE = "   Instance key: included"
KEY_NOT_USED_LINE = "ℹ️  The archive carries its own instance key: --instance-key-file is not used"
WRONG_KEY_LINE = "⚠️  The key given with --instance-key-file reads none of the saved provider keys: it is not the key of the instance this backup came from"
TOO_SHORT_LINE = "❌ The instance key given is too short: an instance key has at least 32 characters (instance_key_invalid)"
#: (B-34) The end of D2's exception when this instance has no key yet and the check could not create one; the path of
#: the key file it could not create comes first.
NO_KEY_YET = "there is no instance key yet, and it could not be created"
#: The saved provider keys of a ``secure_cases.secret_source``, every one under its key.
SAVED_KEYS = len(secure_cases.SECRET_ROWS)
#: (B-18, §2) A key file that gives no key: missing, blank, or one the file system will not read (skipped as root).
NO_KEY_GIVEN = [pytest.param("missing", id="missing"), pytest.param("blank", id="blank"), pytest.param("unreadable", id="unreadable", marks=cli.needs_permission_checks)]


def rekeyed_line(count: int) -> str:
    """The report's line of the saved provider keys re-encrypted with this instance's key (lot B4), verbatim."""
    return f"   Saved provider keys: {count} re-encrypted with this instance's key"


def unreadable_keys_line(count: int) -> str:
    """The report's ⚠️ line of the saved provider keys this instance's key cannot read (lot B4), verbatim."""
    return f"⚠️  {count} saved provider key{'s' if count != 1 else ''} cannot be read with this instance's key: enter {'them' if count != 1 else 'it'} again after the restore"


def own_key_unusable_line(problem: str) -> str:
    """(B-18, §2) D2's exception: this instance's own key cannot be used, ``problem`` as ``instance_key_status`` says it."""
    return f"⚠️  This instance's own key cannot be used, so nothing was re-encrypted with the key given: {problem}"


def from_k1(tmp_path: Path, monkeypatch, database: Path) -> Any:
    """A source whose saved provider keys its generated key K1 encrypted — ``secure_cases.secret_source`` on this module's
    database at the head (the staging tests' ``Databases`` holding it; ``secret_source`` reads ``head`` only),
    configured as this process's data directory, as on the server it is backed up from."""
    return secure_cases.secret_source(tmp_path / "source", secure_cases.cases.Databases(head=database, older=database), monkeypatch)


def checked_on_k2(tmp_path: Path, monkeypatch) -> Path:
    """The live instance a restore is checked on, configured, its own key K2 generated: its root."""
    root = instance(tmp_path, monkeypatch)
    secure_cases.write_key_file(root, THIS_KEY)
    return root


def key_given(tmp_path: Path, text: str) -> Path:
    """The file given with ``--instance-key-file``, outside the data directories: ``text`` and a line break, 0600."""
    return secure_cli.password_file(tmp_path / "keys", f"{text}\n", name="old-instance.key")


def restored_with_key(capsys, archive: Path, key_file: Path, *flags: str) -> tuple[int, list[str], str]:
    """``restore ARCHIVE <flags> --instance-key-file <key_file>``: its exit code, the lines of its standard output, and
    both its streams as one text."""
    code = run("restore", str(archive), *flags, "--instance-key-file", str(key_file))
    captured = capsys.readouterr()
    return code, captured.out.splitlines(), captured.out + captured.err


def no_key_shown(text: str, *keys: str) -> None:
    """(B-18) No key text reaches standard output or error."""
    shown = [f"<a key of {len(key)} characters>" for key in keys if key in text]
    assert shown == [], f"a key text reached the terminal: {shown}"


def unreadable_keys_in(lines: list[str]) -> list[str]:
    """The ⚠️ lines of saved provider keys this instance's key cannot read."""
    return [line for line in lines if line.startswith("⚠️") and "cannot be read with this instance's key" in line]


def test_a_dry_run_with_the_old_key_re_encrypts_the_saved_provider_keys(tmp_path, monkeypatch, capsys, head_database):
    """(h) B-18, c1: a clear archive whose saved provider keys are under K1, checked on an instance under K2, K1 given:
    every saved key re-encrypted, none left unreadable, the report says the key was given; the copy removed."""
    print_section("B-18: restore --instance-key-file")
    source = from_k1(tmp_path, monkeypatch, head_database)
    archive = secure_cases.clear_backup(source.data)
    root = checked_on_k2(tmp_path, monkeypatch)
    secure_cases.own_subkey(root)
    code, lines, text = restored_with_key(capsys, archive, key_given(tmp_path, source.key), "--dry-run")
    assert code == 0 and cli.RESTORABLE_LINE in lines, f"a dry run with the old key: exit 0, restorable: exit {code}: {lines}"
    assert KEY_GIVEN_LINE in lines and rekeyed_line(SAVED_KEYS) in lines, f"the key line, verbatim {KEY_GIVEN_LINE!r}, and {rekeyed_line(SAVED_KEYS)!r}: {lines}"
    assert unreadable_keys_in(lines) == [] and WRONG_KEY_LINE not in lines, f"no saved key left unreadable: {lines}"
    assert cli.stages_left(root) == [], f"the copy removed: {cli.stages_left(root)}"
    no_key_shown(text, source.key, THIS_KEY)
    print_success(f"--dry-run with K1: {SAVED_KEYS} re-encrypted")


def test_a_confirmed_restore_with_the_old_key_waits_with_its_saved_keys_re_encrypted(tmp_path, monkeypatch, capsys, head_database):
    """(h) B-18, c2: the same without ``--dry-run``, with ``--yes``: confirmed, its copy waits with every saved key
    re-encrypted under K2 (``secure_cases.assert_rekeyed_to`` on the copy's report), and ``pending`` shows it."""
    source = from_k1(tmp_path, monkeypatch, head_database)
    archive = secure_cases.clear_backup(source.data)
    root = checked_on_k2(tmp_path, monkeypatch)
    own = secure_cases.own_subkey(root)
    code, lines, text = restored_with_key(capsys, archive, key_given(tmp_path, source.key), "--yes")
    assert code == 0 and any(line.startswith("✅") and "waits for the next start" in line for line in lines), f"confirmed: exit 0, the restore waits for the next start: exit {code}: {lines}"
    assert KEY_GIVEN_LINE in lines and rekeyed_line(SAVED_KEYS) in lines, f"the report as with --dry-run: {lines}"
    stages = cli.stages_left(root)
    assert len(stages) == 1, f"the copy is kept, for the next start: {stages}"
    secure_cases.assert_rekeyed_to(own, root, read_report(root, stages[0]), source)
    assert run("pending") == 0, "pending: exit 0"
    pending = capsys.readouterr()
    assert "⏳ A restore waits for the next start of the server" in pending.out.splitlines(), f"pending shows the restore waiting: {pending.out}"
    no_key_shown(text + pending.out + pending.err, source.key, THIS_KEY)
    print_success("--yes with K1: confirmed, the copy under K2, pending shows it")


@pytest.mark.parametrize("case", NO_KEY_GIVEN)
def test_a_key_file_that_gives_no_key_stops_before_the_password_and_any_copy(tmp_path, monkeypatch, capsys, case):
    """(h) B-18, c3: the file is read before anything else — before the password a secure archive asks at a terminal,
    the right one ready to be typed: ``❌ <read_secret_file's message> (instance_key_unreadable)``, exit 1, no copy,
    nothing asked, nothing read from standard input."""
    root = instance(tmp_path, monkeypatch)
    path = secure_cli.sealed(secure_cli.clear_archive(tmp_path / "backup"), tmp_path / "inputs")
    key_file = tmp_path / "keys" / "old-instance.key"
    if case != "missing":
        key_file = key_given(tmp_path, " " if case == "blank" else secure_cases.SOURCE_KEY)
    if case == "unreadable":
        key_file.chmod(0o000)
    try:
        read_secret_file(key_file, "instance key file")
    except SecretFileError as exc:
        expected = f"❌ {exc} (instance_key_unreadable)"
    else:
        pytest.fail(f"precondition: the {case} key file must give no key")
    asked = secure_cli.answering(monkeypatch, secure_cli.PASSWORD)
    with secure_cli.terminal_holding(monkeypatch, secure_cli.TYPED_AHEAD) as stdin:
        code = run("restore", str(path), "--dry-run", "--instance-key-file", str(key_file))
    captured = capsys.readouterr()
    refusals = [line for line in captured.out.splitlines() if line.startswith("❌")]
    assert (code, refusals) == (1, [expected]), f"{case}: exit 1 and one line, verbatim {expected!r}: exit {code}: {captured.out}"
    assert "🔎" not in captured.out and cli.stages_left(root) == [], f"{case}: nothing checked, no copy: {cli.stages_left(root)}"
    assert (asked, stdin.reads) == ([], []), f"{case}: the password never asked: prompts {asked}, reads {stdin.reads}"
    no_key_shown(captured.out + captured.err, secure_cases.SOURCE_KEY)
    print_success(f"{case}: (instance_key_unreadable), nothing asked")


def test_a_key_too_short_is_refused_before_any_copy_is_made(tmp_path, monkeypatch, capsys, head_database):
    """(h) B-18, c4: a key of fewer than 32 characters can be no instance's key: the ❌ line of the check, verbatim,
    exit 1, no copy left; the key itself never said, nor its length."""
    root = instance(tmp_path, monkeypatch)
    archive = cli.restorable(tmp_path, head_database)
    code, lines, text = restored_with_key(capsys, archive, key_given(tmp_path, SHORT_KEY), "--dry-run")
    assert (code, [line for line in lines if line.startswith("❌")]) == (1, [TOO_SHORT_LINE]), f"exit 1 and one line, verbatim {TOO_SHORT_LINE!r}: exit {code}: {lines}"
    assert cli.stages_left(root) == [], f"no copy left: {cli.stages_left(root)}"
    no_key_shown(text, SHORT_KEY)
    print_success("a short key → (instance_key_invalid), no copy")


def test_an_archive_carrying_its_own_key_uses_it_and_says_the_file_is_not_used(tmp_path, monkeypatch, capsys, head_database):
    """(h) B-18, c5 (D1): a secure archive that carries its key K1, and a wrong key given: the archive's key wins — every
    saved key re-encrypted — and right after the key line, unchanged («included»), the ℹ️ line says the file is not
    used."""
    source = from_k1(tmp_path, monkeypatch, head_database)
    _job, envelope = secure_cases.secure_backup(source.data)
    root = checked_on_k2(tmp_path, monkeypatch)
    secure_cases.own_subkey(root)
    password = secure_cli.password_file(tmp_path / "inputs", f"{secure_cases.PASSWORD}\n")
    secure_cli.answering(monkeypatch)
    code, lines, text = restored_with_key(capsys, envelope, key_given(tmp_path, WRONG_KEY), "--dry-run", "--password-file", str(password))
    assert code == 0 and KEY_INCLUDED_LINE in lines, f"a secure archive carrying its key: exit 0, {KEY_INCLUDED_LINE!r}: exit {code}: {lines}"
    following = lines[lines.index(KEY_INCLUDED_LINE) + 1 : lines.index(KEY_INCLUDED_LINE) + 2]
    assert following == [KEY_NOT_USED_LINE], f"right after the key line, verbatim {KEY_NOT_USED_LINE!r}, not {following}: {lines}"
    assert rekeyed_line(SAVED_KEYS) in lines and unreadable_keys_in(lines) == [] and WRONG_KEY_LINE not in lines, f"the archive's key re-encrypts every saved key, the file's is not used: {lines}"
    no_key_shown(text, source.key, WRONG_KEY, THIS_KEY)
    print_success("D1: the archive's own key, ℹ️ the file not used")


def test_a_wrong_key_reads_no_saved_key_and_says_so_before_the_unreadable_line(tmp_path, monkeypatch, capsys, head_database):
    """(h) B-18, c6 (D2): a key of 32 characters or more that is not K1 reads none of the saved keys: nothing
    re-encrypted, and right before the ⚠️ line of the unreadable keys, the ⚠️ line that names the key given."""
    source = from_k1(tmp_path, monkeypatch, head_database)
    archive = secure_cases.clear_backup(source.data)
    root = checked_on_k2(tmp_path, monkeypatch)
    secure_cases.own_subkey(root)
    code, lines, text = restored_with_key(capsys, archive, key_given(tmp_path, WRONG_KEY), "--dry-run")
    unreadable = unreadable_keys_line(SAVED_KEYS)
    assert code == 0 and KEY_GIVEN_LINE in lines and unreadable in lines, f"exit 0, the key line and {unreadable!r}: exit {code}: {lines}"
    before = lines[lines.index(unreadable) - 1]
    assert before == WRONG_KEY_LINE, f"right before the unreadable line, verbatim {WRONG_KEY_LINE!r}, not {before!r}: {lines}"
    assert rekeyed_line(SAVED_KEYS) not in lines and not any(line.startswith("⚠️  This instance's own key") for line in lines), f"nothing re-encrypted, and this instance's key is not blamed: {lines}"
    no_key_shown(text, WRONG_KEY, source.key, THIS_KEY)
    print_success("D2: ⚠️ the key given reads none, before the unreadable line")


def test_when_this_instance_s_own_key_cannot_be_used_it_is_said_instead_of_blaming_the_key_given(tmp_path, monkeypatch, capsys, head_database):
    """(h) B-18, c7 (D2's exception): this instance's own key cannot be used (``LIBREFOLIO_INSTANCE_KEY`` too short), so
    nothing is re-encrypted whatever the key given — here the right one, K1. In the place of D2's line, the one that
    says so with ``instance_key_status``'s problem (its source named, never a key); never D2's."""
    source = from_k1(tmp_path, monkeypatch, head_database)
    archive = secure_cases.clear_backup(source.data)
    checked_on_k2(tmp_path, monkeypatch)
    monkeypatch.setenv("LIBREFOLIO_INSTANCE_KEY", UNUSABLE_OWN_KEY)
    problem = instance_key_status().problem
    assert problem is not None and UNUSABLE_OWN_KEY not in problem, f"precondition: this instance's own key cannot be used, said without the key: {problem!r}"
    code, lines, text = restored_with_key(capsys, archive, key_given(tmp_path, source.key), "--dry-run")
    unreadable = unreadable_keys_line(SAVED_KEYS)
    assert code == 0 and unreadable in lines, f"exit 0, every saved key left unreadable: exit {code}: {lines}"
    before = lines[lines.index(unreadable) - 1]
    assert before == own_key_unusable_line(problem), f"right before the unreadable line, verbatim {own_key_unusable_line(problem)!r}, not {before!r}: {lines}"
    assert WRONG_KEY_LINE not in lines and rekeyed_line(SAVED_KEYS) not in lines, f"the right key is never blamed, nothing re-encrypted: {lines}"
    no_key_shown(text, source.key, UNUSABLE_OWN_KEY, THIS_KEY)
    print_success("D2's exception: this instance's own key named, not the key given")


@contextmanager
def secrets_unwritable(root: Path) -> Iterator[Path]:
    """(B-34) ``<root>/secrets`` a folder this process may search but not write (0500): no ``instance.key`` in it, and
    none can be made there — the first use of a key that cannot be generated. Its mode restored at the end, so that the
    folder can be removed."""
    folder = root / "secrets"
    folder.mkdir(mode=0o700)
    folder.chmod(0o500)
    try:
        yield folder
    finally:
        folder.chmod(0o700)


@cli.needs_permission_checks
def test_when_this_instance_has_no_key_yet_and_none_can_be_created_it_is_said_instead_of_blaming_the_key_given(tmp_path, monkeypatch, capsys, head_database):
    """(h) B-34, D2's exception when this instance has no key yet: none in the environment, no ``secrets/instance.key``,
    and the check cannot create one (``secrets/`` not writable). Nothing is re-encrypted whatever the key given — here
    the right one, K1. Right before the unreadable line, the line that says so, naming the key file that could not be
    created (a printable path: ``_safe`` leaves it as it is); never D2's, which would blame the right key."""
    source = from_k1(tmp_path, monkeypatch, head_database)
    archive = secure_cases.clear_backup(source.data)
    root = instance(tmp_path, monkeypatch)
    key_path = root / "secrets" / "instance.key"
    with secrets_unwritable(root) as folder:
        status = instance_key_status()
        assert (status.source, status.problem, status.path) == ("not_created", None, key_path) and str(key_path).isprintable(), f"precondition: no key in the environment nor at {key_path}, and none made yet: {status}"
        code, lines, text = restored_with_key(capsys, archive, key_given(tmp_path, source.key), "--dry-run")
        after = instance_key_status()
        made = sorted(path.name for path in folder.iterdir())
    assert (after.source, made) == ("not_created", []), f"precondition: the check could not create this instance's key, nor left anything in secrets/: {after}, {made}"
    expected = own_key_unusable_line(f"{key_path}: {NO_KEY_YET}")
    unreadable = unreadable_keys_line(SAVED_KEYS)
    assert code == 0 and cli.RESTORABLE_LINE in lines and unreadable in lines, f"exit 0, restorable, every saved key left unreadable: exit {code}: {lines}"
    before = lines[lines.index(unreadable) - 1]
    assert before == expected, f"right before the unreadable line, verbatim {expected!r}, not {before!r}: {lines}"
    assert WRONG_KEY_LINE not in lines, f"the right key is never blamed: {lines}"
    assert [line for line in lines if "re-encrypted with this instance's key" in line] == [], f"nothing re-encrypted: {lines}"
    no_key_shown(text, source.key)
    print_success("D2's exception, no key yet: the key file that could not be created named, not the key given")


@secure_cli.needs_another_owner
def test_the_key_file_is_read_before_the_switch_to_the_owner_of_the_data_directory(tmp_path, monkeypatch, capsys, head_database):
    """(h) B-18, c8: started as root (B-19's fake identity), the key file is read before the switch to the owner, like
    ``--password-file``: it is readable until the recorded ``setuid`` and never after it (a Docker secret root alone can
    read), and K1 re-encrypts every saved key all the same."""
    source = from_k1(tmp_path, monkeypatch, head_database)
    archive = secure_cases.clear_backup(source.data)
    root = checked_on_k2(tmp_path, monkeypatch)
    secure_cases.own_subkey(root)
    key_file = key_given(tmp_path, source.key)
    identity = secure_cli.faked_identity(monkeypatch, 0, at_switch=lambda: key_file.chmod(0o000))
    code, lines, text = restored_with_key(capsys, archive, key_file, "--dry-run")
    assert identity.calls == secure_cli.owner_switch(root), f"as root, the owner of the data directory: {secure_cli.owner_switch(root)}, not {identity.calls}: exit {code}: {lines}"
    assert code == 0 and KEY_GIVEN_LINE in lines and rekeyed_line(SAVED_KEYS) in lines, f"the key file read before the switch (nobody can read it after), K1 used: exit {code}: {lines}"
    no_key_shown(text, source.key, THIS_KEY)
    print_success("root: the key file read before the switch")


# =============================================================================
# (i) B-35 — the restore limit
# =============================================================================


#: (B-35, §1) A megabyte of the limits (1024²), and K: unset, a profile other than selfhosted limits a restore to K times
#: its upload limit.
MIB = 1024 * 1024
RESTORE_TO_UPLOAD = 8
#: The file of zeros of the archive over 8 MB: deflate shrinks it a thousandfold, small to upload and big to unpack.
ZEROS = "custom-uploads/b35-zeros.bin"
#: (B-35, §3) A limit that cannot be read, and the variable its ❌ line names: a value that is not a whole number; or, in
#: the managed profile with neither limit set, an upload limit whose profile entry is of the wrong type — the restore
#: limit fails closed through it (``ProfileDefaultError``).
UNREADABLE_LIMITS = [
    pytest.param("not-a-number", RESTORE_LIMIT_VARIABLE, id="not-a-number"),
    pytest.param("upload-entry-of-the-wrong-type", MAX_UPLOAD_VARIABLE, id="managed-upload-entry-of-the-wrong-type"),
]


def limits(monkeypatch, *, profile: str = "selfhosted", upload: str | None = None, restore: str | None = None) -> None:
    """The profile, ``LIBREFOLIO_BACKUP_MAX_UPLOAD_MB`` and ``LIBREFOLIO_BACKUP_MAX_RESTORE_MB`` (``None``: unset) the
    command runs with, whatever this process inherited; read at each call."""
    monkeypatch.setenv("LIBREFOLIO_PROFILE", profile)
    for variable, value in ((MAX_UPLOAD_VARIABLE, upload), (RESTORE_LIMIT_VARIABLE, restore)):
        if value is None:
            monkeypatch.delenv(variable, raising=False)
        else:
            monkeypatch.setenv(variable, value)


def a_backup_of(tmp_path: Path, monkeypatch, database: Path, name: str, *, zeros: int = 0) -> Path:
    """A clear archive of a source at the head, ``tmp_path/name``: the staging tests' data directory
    (``secure_cases.source_dir`` on this module's database), plus ``zeros`` bytes of zeros. The source is configured as
    this process's data directory while it is backed up: the live instance is configured after."""
    files = {ZEROS: bytes(zeros)} if zeros else None
    data = secure_cases.source_dir(tmp_path / name, secure_cases.cases.Databases(head=database, older=database), monkeypatch, files=files)
    return secure_cases.clear_backup(data)


def declared(archive: Path) -> int:
    """The total the manifest of ``archive`` declares, in bytes: what a check would unpack."""
    with zipfile.ZipFile(archive) as zf:
        return sum(entry.size for entry in read_manifest(zf).files)


def dry_run(capsys, archive: Path) -> tuple[int, list[str]]:
    """``restore ARCHIVE --dry-run``: its exit code and the lines of its standard output."""
    code = run("restore", str(archive), "--dry-run")
    return code, capsys.readouterr().out.splitlines()


def refusals(lines: list[str]) -> list[str]:
    """The ❌ lines of ``lines``."""
    return [line.rstrip() for line in lines if line.startswith("❌")]


def checking(lines: list[str]) -> bool:
    """Whether the check started: its 🔎 line was printed."""
    return any(line.startswith("🔎 Checking") for line in lines)


def refused_as_too_large(code: int, lines: list[str]) -> bool:
    """Exit 1 and exactly one ❌ line, ending in ``(unpacked_too_large)``, after the 🔎 line."""
    found = refusals(lines)
    return code == 1 and len(found) == 1 and found[0].endswith("(unpacked_too_large)") and checking(lines)


def test_a_dry_run_over_the_restore_limit_is_refused_inside_the_check(tmp_path, monkeypatch, capsys, head_database):
    """(i) B-35, u1: ``LIBREFOLIO_BACKUP_MAX_RESTORE_MB`` below the total the archive declares: refused by the check —
    after its 🔎 line — with ``unpacked_too_large``; exit 1, no copy left."""
    print_section("B-35: the restore limit")
    archive = a_backup_of(tmp_path, monkeypatch, head_database, "source")
    root = instance(tmp_path, monkeypatch)
    limits(monkeypatch, restore="1")
    assert declared(archive) > MIB, f"precondition: the archive declares more than 1 MB: {declared(archive)} bytes"
    code, lines = dry_run(capsys, archive)
    assert refused_as_too_large(code, lines), f"exit 1, exactly one ❌ line ending in (unpacked_too_large), after the 🔎 line: exit {code}: {lines}"
    assert cli.stages_left(root) == [], f"no copy left: {cli.stages_left(root)}"
    print_success("over the limit → (unpacked_too_large), inside the check")


@pytest.mark.parametrize(("case", "named"), UNREADABLE_LIMITS)
def test_a_restore_limit_that_cannot_be_read_stops_before_the_check(tmp_path, monkeypatch, capsys, head_database, case, named):
    """(i) B-35, u2: a limit that cannot be read is said before anything is checked: exactly one ❌ line naming the
    variable at fault and ending in ``(backup_restore_unavailable)``, exit 1, no 🔎 line, no copy."""
    archive = cli.restorable(tmp_path, head_database)
    root = instance(tmp_path, monkeypatch)
    if case == "not-a-number":
        limits(monkeypatch, restore="abc")
    else:
        limits(monkeypatch, profile="managed")
        monkeypatch.setitem(ENVIRONMENT_PROFILE_DEFAULTS["managed"], MAX_UPLOAD_VARIABLE, "500")
    code, lines = dry_run(capsys, archive)
    found = refusals(lines)
    assert code == 1 and len(found) == 1 and named in found[0] and found[0].endswith("(backup_restore_unavailable)"), f"{case}: exit 1, exactly one ❌ line naming {named} and ending in (backup_restore_unavailable): exit {code}: {lines}"
    assert not checking(lines) and cli.stages_left(root) == [], f"{case}: before the check, no copy: {cli.stages_left(root)}: {lines}"
    print_success(f"{case} → (backup_restore_unavailable), before the check")


def test_a_restore_limit_of_0_lifts_the_profile_s_for_one_command(tmp_path, monkeypatch, capsys, head_database):
    """(i) B-35, u3: ``0`` is no limit, and an explicit value always wins: the operator lifts the profile's limit for
    one command, and the archive is checked as today. The barrier first: managed, unset, an upload limit of 1 MB, the
    same archive is refused — so that «as today» never holds only because there is no limit at all (as before B-35)."""
    over = a_backup_of(tmp_path, monkeypatch, head_database, "over", zeros=RESTORE_TO_UPLOAD * MIB)
    root = instance(tmp_path, monkeypatch)
    assert declared(over) > RESTORE_TO_UPLOAD * MIB, f"precondition: the archive declares more than 8 MB: {declared(over)} bytes"
    limits(monkeypatch, profile="managed", upload="1")
    code, lines = dry_run(capsys, over)
    assert refused_as_too_large(code, lines), f"the barrier: managed, unset, an upload limit of 1 MB → refused (unpacked_too_large): exit {code}: {lines}"
    limits(monkeypatch, profile="managed", upload="1", restore="0")
    code, lines = dry_run(capsys, over)
    assert code == 0 and cli.RESTORABLE_LINE in lines and refusals(lines) == [], f"LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0: no limit, checked as today: exit {code}: {lines}"
    assert cli.stages_left(root) == [], f"the dry run's copy removed: {cli.stages_left(root)}"
    print_success("=0 → no limit, for one command")


def test_the_managed_profile_limits_a_restore_to_8_times_its_upload_limit(tmp_path, monkeypatch, capsys, head_database):
    """(i) B-35, u4: managed, the restore limit unset, an upload limit of 1 MB: a limit of 8 MB (K = 8). An archive
    declaring more is refused inside the check; one declaring less is checked as today."""
    over = a_backup_of(tmp_path, monkeypatch, head_database, "over", zeros=RESTORE_TO_UPLOAD * MIB)
    under = a_backup_of(tmp_path, monkeypatch, head_database, "under")
    root = instance(tmp_path, monkeypatch)
    assert declared(under) < RESTORE_TO_UPLOAD * MIB < declared(over), f"precondition: one archive under 8 MB declared, one over: {declared(under)}, {declared(over)} bytes"
    limits(monkeypatch, profile="managed", upload="1")
    code, lines = dry_run(capsys, over)
    assert refused_as_too_large(code, lines), f"over 8 MB: exit 1, exactly one ❌ line ending in (unpacked_too_large), after the 🔎 line: exit {code}: {lines}"
    assert cli.stages_left(root) == [], f"no copy left: {cli.stages_left(root)}"
    code, lines = dry_run(capsys, under)
    assert code == 0 and cli.RESTORABLE_LINE in lines and refusals(lines) == [], f"under 8 MB: checked as today: exit {code}: {lines}"
    assert cli.stages_left(root) == [], f"the dry run's copy removed: {cli.stages_left(root)}"
    print_success("managed, upload 1 MB → a limit of 8 MB: over refused, under checked")


# =============================================================================
# (j) B-43 — a function the reader lacks
# =============================================================================


def test_a_dry_run_of_an_archive_whose_index_calls_a_function_this_librefolio_lacks_says_database_damaged(tmp_path, monkeypatch, capsys, head_database):
    """(j) B-43: the database of the archive holds an index on an expression calling a function this LibreFolio does not
    have; SQLite fails the copy's integrity check, «unknown function». Exactly one ❌ line, after the 🔎 line, ending in
    ``(database_damaged)``, exit 1, no traceback (red before B-43: the ``sqlite3.OperationalError`` escapes the command,
    which ``_check_on_a_copy`` does not catch). No copy left, the live data untouched, the function's name on neither
    output."""
    print_section("B-43: a function the reader lacks")
    archive = staging_cases.archive_calling(tmp_path / "b43", head_database, staging_cases.IN_AN_INDEX)
    root = instance(tmp_path, monkeypatch)
    before = live(root)
    code = run("restore", str(archive), "--dry-run")
    captured = capsys.readouterr()
    lines = captured.out.splitlines()
    found = refusals(lines)
    assert code == 1 and len(found) == 1 and found[0].endswith("(database_damaged)") and checking(lines), f"exit 1 and exactly one ❌ line ending in (database_damaged), after the 🔎 line: exit {code}: {lines}"
    assert "Traceback" not in captured.out + captured.err, f"no traceback: {captured.out[-cli.TAIL:]}{captured.err[-cli.TAIL:]}"
    assert staging_cases.B43_FUNCTION not in captured.out + captured.err, f"the function's name, the archive's text, on neither output: {lines}"
    assert (cli.stages_left(root), live(root)) == ([], before), f"no copy left, the live data untouched: {cli.stages_left(root)}"
    print_success("restore --dry-run: ❌ … (database_damaged), exit 1, no traceback")


# =============================================================================
# (k) Lot L3-2: confirmed_via cli
# =============================================================================


@pytest.mark.parametrize("how", ["--yes", "typed-on-a-terminal"])
def test_a_restore_the_command_line_confirms_is_recorded_via_cli(tmp_path, monkeypatch, capsys, head_database, how):
    """(k) L3-2: the command line's confirmation writes ``confirmed_via`` ``cli`` in ``restore.json``, beside
    ``confirmed_by`` ``cli``, with ``--yes`` as with the word typed on a terminal."""
    print_section(f"(k) L3-2 confirmed_via cli, {how}")
    root = instance(tmp_path, monkeypatch)
    archive = cli.restorable(tmp_path, head_database)
    if how == "--yes":
        code = run("restore", str(archive), "--yes")
    else:
        with stdin_with(monkeypatch, "restore", terminal=True):
            code = run("restore", str(archive))
    out = capsys.readouterr().out
    assert code == 0 and "waits for the next start" in out, f"precondition: the restore is confirmed: exit {code}: {out}"
    state = json.loads(state_path(root).read_text(encoding="utf-8"))
    recorded = (state["status"], state["confirmed_by"], state.get("confirmed_via", "<missing: no confirmed_via before L3-2>"))
    assert recorded == ("pending", "cli", "cli"), f"pending, confirmed by cli, via cli: {state}"
    print_success(f"{how}: confirmed_via cli")


# =============================================================================
# (l) B-33: pending with a state that cannot be read, pending --recover
# =============================================================================


#: (l) B-33 §3, as B-33's follow-up B5-2 amends it: the command ``pending`` gives to run (``--recover`` takes its choice).
RECOVER_COMMAND = "./dev.py backup pending --recover previous"
#: (l) What a state nobody can read holds: never printed.
STATE_MARK = "b33-the-content-of-a-state-nobody-can-read"
#: (l) The folders a restore swaps (``paths.SWAPPED_FOLDERS``), spelled out.
SWAPPED = ("sqlite", "custom-uploads", "broker_reports", "scenario_catalog")
#: (l) The data of before, as ``.restore/previous/`` keeps it: one file in each folder, none the live instance's.
BEFORE = {name: {f"{name}/before.bin": f"the {name} of before\n".encode()} for name in SWAPPED}
#: (l) The three reasons, each one way.
REASONS = [pytest.param("io", id="io"), pytest.param("not_a_file", id="not_a_file"), pytest.param("invalid", id="invalid")]


def assert_said_unreadable(code: int, out: str, reason: str, root: Path) -> None:
    """(l) B-33 §3: ``pending`` with a state that cannot be read: exit 1; exactly one ❌ line, holding
    ``restore_state_unreadable`` and the reason word; the ``--recover`` command; never the state's content nor a path of
    the data directory; no traceback."""
    refusals = [line for line in said(out) if line.startswith("❌")]
    assert code == 1 and len(refusals) == 1, f"exit 1 and one ❌ line: exit {code}: {out}"
    assert "restore_state_unreadable" in refusals[0] and re.search(rf"\b{reason}\b", refusals[0]), f"[new] B-33 §3: the ❌ line holds restore_state_unreadable and the reason {reason!r}: {refusals[0]!r}"
    assert RECOVER_COMMAND in out, f"[new] B-33 §3: pending names the command to run, {RECOVER_COMMAND!r}: {out}"
    assert STATE_MARK not in out and os.fspath(root) not in out and "Traceback" not in out, f"never the state's content, a path, a traceback: {out}"


def unreadable_as(monkeypatch, root: Path, reason: str) -> None:
    """``.restore/restore.json`` (a restore applying, as a start leaves it) made a state that cannot be read: refused by
    the file system (``io``, EACCES), a folder (``not_a_file``), or no state (``invalid``)."""
    write_state(root, "applying")
    if reason == "io":
        unreadable_state(monkeypatch, root)
    elif reason == "not_a_file":
        state_path(root).unlink()
        state_path(root).mkdir(mode=0o700)
        (state_path(root) / "inside.json").write_text(STATE_MARK, encoding="utf-8")
    else:
        state_path(root).write_text("{" + STATE_MARK, encoding="utf-8")


def previous_holding(root: Path, *names: str) -> Path:
    """``.restore/previous/`` holding the data of before of ``names``: what a swap stopped half way leaves."""
    previous = restore_dir(root) / "previous"
    previous.mkdir(mode=0o700, parents=True, exist_ok=True)
    for name in names:
        for entry, content in BEFORE[name].items():
            (previous / entry).parent.mkdir(parents=True, exist_ok=True)
            (previous / entry).write_bytes(content)
    return previous


def checked_copies(root: Path, count: int) -> list[str]:
    """``count`` checked copies kept in ``.restore/stage/``: their ids."""
    ids = [f"{index:032x}" for index in range(1, count + 1)]
    for stage_id in ids:
        (stage_data_dir(root, stage_id) / "sqlite").mkdir(mode=0o700, parents=True)
        (stage_dir(root, stage_id) / "report.json").write_text("{}\n", encoding="utf-8")
    return ids


def files_below(folder: Path) -> dict[str, bytes] | None:
    """Every file below ``folder`` with its bytes, by its path from it; ``None`` where nothing stands."""
    if not os.path.lexists(folder):
        return None
    return {path.relative_to(folder).as_posix(): path.read_bytes() for path in sorted(folder.rglob("*")) if path.is_file() and not path.is_symlink()}


def everything(root: Path) -> dict[str, tuple]:
    """Every path below ``root``, ``.restore`` included, never through a link: its kind, a file's bytes. The apply lock
    aside: a refusal taken under it may create it, which moves nothing."""
    found: dict[str, tuple] = {}
    for folder, names, files in os.walk(root):
        for name in [*names, *files]:
            path = Path(folder) / name
            if path == restore_dir(root) / "apply.lock":
                continue
            info = path.lstat()
            kind = "link" if stat.S_ISLNK(info.st_mode) else "folder" if stat.S_ISDIR(info.st_mode) else "file"
            found[path.relative_to(root).as_posix()] = (kind, path.read_bytes() if kind == "file" and stat.S_ISREG(info.st_mode) else None)
    return found


@pytest.mark.parametrize("reason", REASONS)
def test_pending_with_a_state_that_cannot_be_read_says_what_is_on_disk_and_what_to_run(tmp_path, monkeypatch, capsys, reason):
    """(l) B-33 §3: exit 1, one ❌ line with ``restore_state_unreadable`` and the reason word; the swapped folders
    ``previous/`` holds, each named; how many checked copies are kept (2); the command ``./dev.py backup pending
    --recover``; never the state's content or a path; nothing changed on disk. Red before B-33: ``io`` printed the
    system's words without the command, ``not_a_file`` and ``invalid`` read as no restore (exit 0)."""
    print_section("(l) B-33: pending with a state that cannot be read")
    root = instance(tmp_path, monkeypatch)
    unreadable_as(monkeypatch, root, reason)
    previous_holding(root, "custom-uploads", "broker_reports")
    checked_copies(root, 2)
    before = everything(root) if reason != "io" else None
    code = run("pending")
    out = capsys.readouterr().out
    assert_said_unreadable(code, out, reason, root)
    held = [name for name in ("custom-uploads", "broker_reports") if name not in out]
    assert "previous" in out and held == [], f"[new] B-33 §3: what previous/ holds, each folder named: missing {held}: {out}"
    assert any(re.search(r"\b2\b", line) and "cop" in line.lower() for line in out.splitlines()), f"[new] B-33 §3: how many checked copies are kept (2): {out}"
    if before is not None:
        assert everything(root) == before, "nothing changed on disk"
    print_success(f"{reason}: ❌ (restore_state_unreadable), previous/ and the copies said, --recover named")


def test_recover_puts_the_data_of_before_back_and_pending_then_says_no_restore(tmp_path, monkeypatch, capsys):
    """(l) B-33 §3: ``pending --recover`` with a state that cannot be read (``invalid``), ``previous/`` holding
    ``custom-uploads`` and ``broker_reports``: exit 0, a ✅ line, the two folders named, ``./dev.py backup restore``
    named. On disk: the two folders of before back in place, the live ones in ``.restore/failed/``, ``scenario_catalog``
    and the database as they were; the state renamed ``restore.json.unreadable-<UTC>``, kept as it was. Then ``pending``:
    exit 0, no restore."""
    root = instance(tmp_path, monkeypatch)
    unreadable_as(monkeypatch, root, "invalid")
    state = state_path(root).read_bytes()
    previous_holding(root, "custom-uploads", "broker_reports")
    live_before = {name: files_below(root / name) for name in SWAPPED}
    code = run("pending", "--recover", "previous")
    out = capsys.readouterr().out
    lines = said(out)
    assert code == 0 and any(line.startswith("✅") for line in lines) and not any(line.startswith("❌") for line in lines), f"[new] B-33 §3: --recover with an unreadable state: exit 0, a ✅ line, no ❌: exit {code}: {out}"
    assert "custom-uploads" in out and "broker_reports" in out and "./dev.py backup restore" in out, f"the folders moved named, and ./dev.py backup restore: {out}"
    assert STATE_MARK not in out and "Traceback" not in out, f"never the state's content, no traceback: {out}"
    for name in ("custom-uploads", "broker_reports"):
        assert files_below(root / name) == {"before.bin": BEFORE[name][f"{name}/before.bin"]}, f"{name}: the data of before back in place"
        assert files_below(restore_dir(root) / "failed" / name) == live_before[name], f"{name}: the live one in .restore/failed/"
    assert {name: files_below(root / name) for name in ("sqlite", "scenario_catalog")} == {name: live_before[name] for name in ("sqlite", "scenario_catalog")}, "the folders previous/ did not hold, as they were"
    kept = [path.name for path in restore_dir(root).iterdir() if re.fullmatch(r"restore\.json\.unreadable-\d{8}T\d{6}Z", path.name)]
    assert not os.path.lexists(state_path(root)) and len(kept) == 1 and (restore_dir(root) / kept[0]).read_bytes() == state, f"the state renamed, kept as it was: {sorted(path.name for path in restore_dir(root).iterdir())}"
    again = run("pending")
    out = capsys.readouterr().out
    assert again == 0 and "no restore" in out.lower(), f"then pending: exit 0, no restore: exit {again}: {out}"
    print_success("--recover: exit 0, two folders back, the state kept aside; pending: no restore")


def _no_state_at_all(monkeypatch, root: Path) -> None:
    previous_holding(root, "custom-uploads")


def _a_readable_pending_restore(monkeypatch, root: Path) -> None:
    write_state(root, "pending")
    previous_holding(root, "custom-uploads")


@pytest.mark.parametrize(("arrange", "expected"), [(_no_state_at_all, 3), (_a_readable_pending_restore, 4)], ids=["no-state", "readable-pending"])
def test_recover_previous_with_nothing_to_recover_exits_3_or_4_and_moves_nothing(tmp_path, monkeypatch, capsys, arrange, expected):
    """(l) B-33 §3, with B5-2's exit codes (interface ``B-b52-interface.md``): ``pending --recover previous`` with no state:
    exit 3, one line ``❌ Nothing to recover…``; with a state this LibreFolio reads (``previous/`` there all the same):
    ``previous`` is not a valid choice in that state, exit 4, one ❌ line. Nothing moved, written or removed."""
    root = instance(tmp_path, monkeypatch)
    arrange(monkeypatch, root)
    before = everything(root)
    code = run("pending", "--recover", "previous")
    out = capsys.readouterr().out
    refusals = [line for line in said(out) if line.startswith("❌")]
    assert code == expected and len(refusals) == 1, f"[new] B5-2: exit {expected}, one ❌ line: exit {code}: {out}"
    if expected == 3:
        assert refusals[0].startswith("❌ Nothing to recover"), f"[new] B-33 §3: the line says Nothing to recover…: {out}"
    assert everything(root) == before, "nothing moved, written or removed"
    print_success(f"{arrange.__name__}: ❌, exit {expected}")


def test_recover_while_a_server_serves_the_data_directory_exits_5_and_moves_nothing(tmp_path, monkeypatch, capsys):
    """(l) B-33 §3: a server holds the serving lock of the data directory (this process, through a descriptor of its
    own, as ``hold_serving_lock`` holds it; released at the end): ``pending --recover previous`` exits 5 (B5-2) with one ❌ line, nothing
    moved, written or removed."""
    root = instance(tmp_path, monkeypatch)
    unreadable_as(monkeypatch, root, "invalid")
    previous_holding(root, "custom-uploads")
    apply = apply_module()
    key = str(root.resolve())
    assert apply.hold_serving_lock(root) is True, "precondition: a server serves the data directory"
    try:
        before = everything(root)
        code = run("pending", "--recover", "previous")
    finally:
        os.close(apply._SERVING.pop(key))
    out = capsys.readouterr().out
    refusals = [line for line in said(out) if line.startswith("❌")]
    assert code == 5 and len(refusals) == 1, f"[new] B5-2: exit 5, one ❌ line while a server serves the data directory: exit {code}: {out}"
    assert everything(root) == before, "nothing moved, written or removed"
    print_success("served: ❌, exit 1, nothing moved")


def test_recover_and_cancel_together_are_refused_by_the_parser(tmp_path, monkeypatch, capsys):
    """(l) B-33 §3: ``--recover`` and ``--cancel`` exclude each other: the parser refuses them together (exit 2, «not
    allowed with»), naming ``--recover``; nothing runs. Red before B-33: refused, but as an argument it does not know."""
    root = instance(tmp_path, monkeypatch)
    unreadable_as(monkeypatch, root, "invalid")
    before = everything(root)
    parser = argparse.ArgumentParser(prog="dev.py")
    backup_cli.register_subparser(parser.add_subparsers(dest="command"))
    with pytest.raises(SystemExit) as done:
        parser.parse_args(["backup", "pending", "--recover", "previous", "--cancel"])
    err = capsys.readouterr().err
    assert done.value.code == 2 and "not allowed with" in err and "--recover" in err, f"[new] B-33 §3: refused by the parser as exclusive (exit 2, «not allowed with», --recover named), not as an unknown argument: exit {done.value.code}: {err}"
    assert everything(root) == before, "nothing ran"
    print_success("--recover previous --cancel: exit 2")


def test_the_help_of_pending_names_recover(monkeypatch, capsys):
    """(l) B-33 §3: ``backup pending --help`` names ``--recover``."""
    pending_help = cli.help_of(monkeypatch, capsys, "backup", "pending")
    assert "--recover" in pending_help, f"[new] B-33 §3: pending --help names --recover: {pending_help}"
    print_success("pending --help: --recover")


# =============================================================================
# (m) Lot B5-1: what became of the owner's account
# =============================================================================

#: A's reset link for ``link_only``, recorded in the state: printed once by ``pending``, never by ``pending --json``.
OWNER_RESET_PATH = "/reset-password#token=b51-cli-secret-0123456789abcdef"
OWNER_EMAIL = "owner.b51@example.com"
OWNER_ID = 42


def committed_with_owner(root: Path, **owner: Any) -> None:
    """A committed restore confirmed via ``admin``, the owner's fields ``owner`` written into the state file as raw JSON."""
    write_state(root, "committed", confirmed_by="b51-admin", confirmed_via="admin")
    path = state_path(root)
    record = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(json.dumps({**record, **owner}), encoding="utf-8")


def pending_lines(capsys) -> list[str]:
    assert run("pending") == 0, "pending is exit 0"
    return capsys.readouterr().out.splitlines()


def owner_lines(tmp_path: Path, monkeypatch, capsys, **owner: Any) -> tuple[list[str], str]:
    """The lines ``pending`` prints for a committed restore with ``owner``, beyond those of the same restore without an
    owner; and the whole output."""
    baseline_root = instance(tmp_path / "baseline", monkeypatch)
    committed_with_owner(baseline_root)
    baseline = pending_lines(capsys)
    root = instance(tmp_path / "with-owner", monkeypatch)
    committed_with_owner(root, **owner)
    lines = pending_lines(capsys)
    return [line for line in lines if line not in baseline], "\n".join(lines)


#: (the outcome recorded, what its one line must hold besides «owner»).
OWNER_OUTCOMES = [
    pytest.param("sent", (), id="sent"),
    pytest.param("link_only", ("only to the owner",), id="link_only"),
    pytest.param("already_issued", (), id="already_issued"),
    pytest.param("already_done", (), id="already_done"),
    pytest.param("error:EMAIL_TAKEN", ("EMAIL_TAKEN",), id="error"),
    pytest.param(None, ("next start",), id="not-yet"),
]


@pytest.mark.parametrize(("outcome", "words"), OWNER_OUTCOMES)
def test_pending_says_what_became_of_the_owner_s_account_in_one_line(tmp_path, monkeypatch, capsys, outcome, words):
    """(m) B5-1: one line more than without an owner, naming the owner, with what the outcome needs; the reset path,
    for ``link_only`` only, printed exactly once."""
    print_section(f"(m) B5-1 pending: owner {outcome}")
    path = OWNER_RESET_PATH if outcome == "link_only" else None
    extra, out = owner_lines(tmp_path, monkeypatch, capsys, owner_user_id=OWNER_ID, owner_outcome=outcome, owner_reset_path=path)
    assert len(extra) == 1, f"[new] B5-1: one line about the owner's account, not {len(extra)}: {extra}\n{out}"
    line = extra[0]
    assert "owner" in line.lower(), f"the line names the owner: {line!r}"
    missing = [word for word in words if word.lower() not in line.lower()]
    assert missing == [], f"{outcome}: the line holds {missing}: {line!r}"
    assert out.count(OWNER_RESET_PATH) == (1 if outcome == "link_only" else 0), f"{outcome}: the reset path printed {out.count(OWNER_RESET_PATH)} times: {out}"
    print_success(f"{outcome}: {line}")


@pytest.mark.parametrize(
    "owner",
    [
        pytest.param({"confirmed_via": "cli", "confirmed_by": "cli", "owner_user_id": None}, id="via-cli"),
        pytest.param({"confirmed_via": "panel", "confirmed_by": "panel", "owner_user_id": None}, id="via-panel"),
        pytest.param({"owner_user_id": None, "owner_outcome": None}, id="admin-without-owner"),
    ],
)
def test_pending_says_nothing_of_an_owner_nobody_chose(tmp_path, monkeypatch, capsys, owner):
    """(m) B5-1, a guard: a committed restore without an owner chosen prints no line about one."""
    root = instance(tmp_path, monkeypatch)
    committed_with_owner(root, **owner)
    out = "\n".join(pending_lines(capsys))
    assert "owner" not in out.lower(), f"no owner line: {out}"
    print_success(f"{owner}: no owner line")


@pytest.mark.parametrize("outcome", ["link_only", "sent", None])
def test_pending_json_never_holds_the_owner(tmp_path, monkeypatch, capsys, outcome):
    """(m) B5-1, a guard: ``pending --json`` holds neither the owner's id, outcome or reset path, nor the owner's email,
    whatever the state records."""
    monkeypatch.setenv("LIBREFOLIO_ADMIN_EMAIL", OWNER_EMAIL)
    root = instance(tmp_path, monkeypatch)
    committed_with_owner(root, owner_user_id=OWNER_ID, owner_outcome=outcome, owner_reset_path=OWNER_RESET_PATH if outcome == "link_only" else None)
    code = run("pending", "--json")
    captured = capsys.readouterr()
    assert code == 0, f"pending --json: exit 0: {captured.out} {captured.err}"
    answer = json.loads(captured.out)
    assert answer.get("state") == "committed", f"barrier: the committed restore is read: {answer}"
    both = (captured.out + captured.err).lower()
    shown = [secret for secret in ("owner", OWNER_RESET_PATH.lower(), "reset-password", OWNER_EMAIL) if secret in both]
    assert shown == [], f"pending --json holds {shown}: {captured.out}"
    print_success(f"{outcome}: nothing of the owner")

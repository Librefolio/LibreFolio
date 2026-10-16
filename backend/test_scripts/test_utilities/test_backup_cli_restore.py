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

Pure, as ``test_backup_cli.py``, whose fixtures and helpers are imported: data directories under ``tmp_path`` seen through
``LIBREFOLIO_DATA_DIR`` (production mode, checked); a real database at the head made once by ``alembic upgrade`` for the
module. The commands go through the parser ``register_subparser`` builds, as ``dev.py backup`` runs them. A terminal is a
pty, a pipe is a pipe: ``sys.stdin`` replaced for one test. No signal can reach this process: ``restart.send_signal``
and ``os.kill`` as ``restart`` sees it record, and must stay unused. States only a start can reach are written as
``apply.RestoreState`` would write them; the reason a pending restore waits is written into the state file itself
(``waiting_for``), whatever the models accept, so that what ``pending`` prints is what fails. The block is
``LIBREFOLIO_BLOCKED`` in this process's environment, which ``config.platform.instance_blocked()`` reads at each call:
the one a developer's shell may carry is removed before every test (``no_inherited_block``), and a test of the block
sets its own with ``monkeypatch``. POSIX-only (pty, modes).
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import pty
import stat
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from backend.app.config.platform import instance_blocked
from backend.app.services.platform.instance_backup.paths import DATABASE_ENTRY, restore_dir, stage_dir
from backend.test_scripts.test_utilities import test_backup_cli as cli
from backend.test_scripts.test_utils import print_section, print_success
from scripts import backup_cli

pytestmark = pytest.mark.skipif(os.name == "nt", reason="a terminal is a pty, and file modes are POSIX only")

# The fixtures of the command line's tests, re-exported: ``app_version`` (autouse) and the real database at the head.
app_version = cli.app_version
head_database = cli.head_database

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

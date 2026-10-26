"""
``dev.py backup pending --json`` and ``backup pending --recover <choice>`` (workstream B, lot B5-2; interface
``B-b52-interface.md``; requester: the cloud coordinator, ``lfc istanza recupera``). Selector: ``utils backup-cli-recover``.

Written before the code (red until lot B5-2 lands): ``--json`` does not exist, and ``--recover`` is still a bare flag
that takes no argument, so argparse refuses what the tests give it and each test fails on its own with that message.
The human messages are not final: the tests pin exit codes, the one-line JSON object, what is on disk, and the stable
codes already on a ❌ line (``restore_nothing_to_recover``, ``restore_in_use``, ``restore_apply_failed``).

(a) ``pending --json`` (a read): exactly one line on standard output, ``\\n`` at its end, valid JSON, no ANSI escape, no
    other byte. Keys, always present: ``state`` (``none``, ``pending``, ``in_progress``, ``committed``, ``rolled_back``,
    ``unreadable``), ``reason`` (the rollback reason of ``rolled_back``, the unreadable reason ``io`` / ``not_a_file`` /
    ``invalid`` of ``unreadable``, else ``null``), ``waiting``, ``backup_created_at`` (ISO 8601 UTC with ``Z``;
    ``null`` for ``none`` and ``unreadable``), ``safety_copy`` (``{"present", "at"}``: ``.restore/previous/`` a plain
    folder holding one of the swapped folders; ``at`` the readable state's ``applied_at``, else the modification time of
    ``previous/``) and ``choices`` (``[]``, ``["cancel"]`` for ``pending``, ``["previous"]`` for ``unreadable``). Exit 0
    whenever the line was printed, an unreadable state included; nothing is written to the data directory. The log lines
    of the modules the command calls (the unreadable state logs an error; the standard output is where a logging handler
    of the application writes) never reach standard output.
(b) Privacy: ``confirmed_by`` (``alice@example.test``), the data directory (a distinctively named folder) and the stage
    id are in neither the line nor, for ``pending --json``, standard error.
(c) A data directory that is missing, or is no folder: standard output stays empty, the cause is on standard error, exit
    5. Usage errors are argparse's (exit 2): ``--json`` with ``--cancel``, ``--recover`` without an argument,
    ``--recover`` with ``--cancel``. The choice word is not an argparse ``choices``: an unknown word is exit 4.
(d) ``--recover previous``: with an unreadable state (each reason) exit 0, the data of before back, the state kept
    aside; run again, exit 3 and the data directory byte for byte as the first run left it. A readable state: exit 4;
    none: exit 3; an unknown word: exit 4 whatever the state; ``--recover cancel`` on a pending restore: exit 0, dropped
    with its copy, again exit 3; on an unreadable state exit 4; a server serving the data directory: exit 5, nothing
    moved; a move that fails, or an ``OSError``: exit 5, nothing claimed done. It never asks anything.
(e) With ``--json``, one line again: the state AFTER the action, ``recover`` = ``{"choice", "done"}``, and ``error``
    (``nothing_to_recover``, ``choice_not_valid``, ``restore_in_use``, ``restore_apply_failed``, ``failed``) when the exit
    code is not 0. (f) Without ``--json`` the same codes, today's human text (a ✅ line when done, a ❌ line when not).

(g) Lot B5-1b (interface ``B-b51-interface.md`` §9.2; written RED before it): ``--recover owner``, the way out of an
    ``owner_outcome`` of ``error:<CODE>`` (a committed restore confirmed from the app, an owner named). The snapshot of
    exactly that state is ``reason: "owner_assignment"``, ``choices: ["owner"]`` (no code, name, id or link anywhere); every
    other committed state keeps ``reason: null``, ``choices: []``. ``--recover owner`` where the state does not offer it:
    exit 4 ``choice_not_valid`` (no state at all: exit 3), nothing changes — and a second run after a success is such a
    state (exit 4); a race lost to another reset (``RestoreOwnerNotFailedError``): exit 3; ``owner.lock`` held: exit 5
    ``restore_in_use``; ``OSError``/``BackupPathError``: exit 5 ``failed``. Offered: the outcome is cleared; a server
    serves the data directory: nothing else, A not called, exit 0 and one ✅ line; nobody serves: the step runs at once
    (A's function played by a fake behind ``owner._assign_owner``): outcome recorded (``sent`` or ``link_only``), not
    ``error:`` -> exit 0 and the lines ``_print_owner_outcome`` prints for it (R13: for ``link_only`` one ⚠️ line saying
    the link is in the instance log, never a link, a path or a token anywhere: the fake result carries a stray
    ``reset_path`` canary and a stale state may carry an ``owner_reset_path`` key, neither reaches the state file, the
    output or the log); ``error:`` again ->
    exit 5 ``owner_assignment_failed`` and a ❌ line with the code; nothing recorded (A missing, a transient failure) ->
    exit 0 and a ⏳ line. With ``--json`` one line that names no code, name, address, id or link, and the log lines of the
    modules never reach standard output.

Pure, as ``test_backup_cli_restore.py``, whose fixtures and helpers are imported: data directories under ``tmp_path`` seen
through ``LIBREFOLIO_DATA_DIR`` (production mode, checked); the commands run in this process through the parser
``register_subparser`` builds, standard output and standard error told apart by ``capsys``; the cases that must not hang
(a FIFO where the state should be) and the real streams run the script in a process of their own, with a timeout.
POSIX-only (modes, FIFOs).
"""

from __future__ import annotations

import argparse
import errno
import fcntl
import importlib
import json
import logging
import os
import re
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from enum import StrEnum
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from backend.app.services.platform.instance_backup.paths import restore_dir, stage_data_dir, stage_dir
from backend.test_scripts.test_utilities import test_backup_cli as cli
from backend.test_scripts.test_utilities import test_backup_cli_restore as base
from backend.test_scripts.test_utils import print_section, print_success
from scripts import backup_cli

pytestmark = pytest.mark.skipif(os.name == "nt", reason="file modes and FIFOs are POSIX only")

# The fixtures of the restore tests, re-exported (autouse there, so here): the application version, no signal sent,
# no block nor restore limit inherited from a developer's shell.
app_version = cli.app_version
no_restart = base.no_restart
no_inherited_block = base.no_inherited_block
no_inherited_restore_limit = base.no_inherited_restore_limit

#: The keys of the line, always present (interface, ``backup pending --json``).
KEYS = {"state", "reason", "waiting", "backup_created_at", "safety_copy", "choices"}
#: What a state's ``choices`` are, by ``state``.
CHOICES = {"none": [], "pending": ["cancel"], "in_progress": [], "committed": [], "rolled_back": [], "unreadable": ["previous"]}
#: The backup the states ``base.write_state`` writes were made from.
BACKUP_AT = base.CONFIRMED_AT - timedelta(days=1)
#: Privacy canaries: nothing of these may be in what a script reads (interface: never a username, an email, a path, a stage id).
CANARY_USER = "alice@example.test"
CANARY_FOLDER = "canary-datadir-7f3a"
CANARY_STAGE = "5ca1ab1e0000000000000000c0ffee77"
CANARIES = (CANARY_USER, CANARY_FOLDER, CANARY_STAGE)
assert len(CANARY_STAGE) == 32
ISO_UTC = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z")
#: The time the modification time of ``.restore/previous/`` is set to: whole seconds.
PREVIOUS_AT = datetime(2026, 10, 22, 10, 0, 0, tzinfo=UTC)


# =============================================================================
# Running a command, reading its line
# =============================================================================


@dataclass
class Ran:
    """What one command did: its exit code, and what it printed on each stream."""

    code: int
    out: str
    err: str

    @property
    def lines(self) -> list[str]:
        return base.said(self.out)

    @property
    def refused(self) -> list[str]:
        return [line for line in self.lines if line.startswith("❌")]


def parser() -> argparse.ArgumentParser:
    """``dev.py``'s parser with the ``backup`` group, as ``register_subparser`` declares it."""
    root = argparse.ArgumentParser(prog="dev.py")
    backup_cli.register_subparser(root.add_subparsers(dest="command"))
    return root


@pytest.fixture(autouse=True)
def asks_nothing(monkeypatch) -> None:
    """Interface: ``--recover`` never asks anything (no prompt, no terminal needed): a question is a failure."""

    def asked(*args: Any, **kwargs: Any) -> str:
        raise AssertionError("the command asked a question: --recover never asks anything")

    monkeypatch.setattr("builtins.input", asked)
    monkeypatch.setattr("getpass.getpass", asked)


def go(capsys, *argv: str) -> Ran:
    """``dev.py backup <argv>`` in this process: parsed as ``register_subparser`` declares it, then run. An argument the
    command line does not take, or an exception escaping the command (a traceback for the user), fails the test."""
    capsys.readouterr()
    try:
        args = parser().parse_args(["backup", *argv])
    except SystemExit as exc:
        pytest.fail(f"dev.py backup {' '.join(argv)}: the command line does not take these arguments (argparse exit {exc.code}): {capsys.readouterr().err[-cli.TAIL:]}")
    try:
        code = args.func(args)
    except Exception as exc:
        pytest.fail(f"dev.py backup {' '.join(argv)} raised {type(exc).__name__} ({exc}): the user would get a traceback instead of a message")
    captured = capsys.readouterr()
    return Ran(code, captured.out, captured.err)


def refused_by_parser(capsys, *argv: str) -> str:
    """The message argparse refuses ``dev.py backup <argv>`` with (exit 2); the test fails when it is accepted."""
    capsys.readouterr()
    with pytest.raises(SystemExit) as done:
        parser().parse_args(["backup", *argv])
    err = capsys.readouterr().err
    assert done.value.code == 2, f"dev.py backup {' '.join(argv)}: argparse exit 2, not {done.value.code}: {err}"
    return err


def accepts(capsys, *argv: str) -> None:
    """Barrier: the arguments of ``dev.py backup <argv>`` are read without an error (nothing runs)."""
    capsys.readouterr()
    try:
        parser().parse_args(["backup", *argv])
    except SystemExit as exc:
        pytest.fail(f"precondition: dev.py backup {' '.join(argv)} must be accepted (lot B5-2's options): argparse exit {exc.code}: {capsys.readouterr().err[-cli.TAIL:]}")


def the_line(ran: Ran) -> dict[str, Any]:
    """The one JSON object a ``--json`` command printed: exactly one line, ``\\n`` at its end, no escape sequence, no
    other control character."""
    out = ran.out
    assert out.endswith("\n") and out.count("\n") == 1, f"standard output is exactly one line ending with a line break (exit {ran.code}): {out!r}"
    assert "\x1b" not in out and all(char.isprintable() for char in out[:-1]), f"no ANSI escape, no control character on the line: {out!r}"
    try:
        line = json.loads(out)
    except ValueError:
        pytest.fail(f"the line is valid JSON (exit {ran.code}): {out!r}")
    assert isinstance(line, dict), f"the line is a JSON object: {out!r}"
    return line


def instant(value: Any) -> datetime:
    """An ISO 8601 UTC moment with ``Z``, as a datetime."""
    assert isinstance(value, str) and ISO_UTC.fullmatch(value), f"an ISO 8601 UTC moment ending with Z: {value!r}"
    return datetime.fromisoformat(value[:-1] + "+00:00")


def instance(tmp_path: Path, monkeypatch, name: str = "instance") -> Path:
    """The data directory of the commands: the production one they see."""
    return cli.point_at(monkeypatch, cli.make_data_dir(tmp_path / name))


def previous_at(root: Path, moment: datetime = PREVIOUS_AT) -> None:
    """The modification time of ``.restore/previous/`` set to ``moment`` (whole seconds)."""
    stamp = moment.timestamp()
    os.utime(restore_dir(root) / "previous", (stamp, stamp))


@contextmanager
def serving(root: Path) -> Iterator[None]:
    """A server serving the data directory: its serving lock held by this process, through a descriptor of its own, as
    ``hold_serving_lock`` holds it; released at the end."""
    apply = base.apply_module()
    assert apply.hold_serving_lock(root) is True, "precondition: a server serves the data directory"
    try:
        yield
    finally:
        os.close(apply._SERVING.pop(str(root.resolve())))


# =============================================================================
# The states, each as a start leaves it on disk
# =============================================================================

Arrange = Callable[[Any, Path], None]


def _none(monkeypatch, root: Path) -> None:
    """No state file at all."""


def _status(status: str, **extra: Any) -> Arrange:
    return lambda monkeypatch, root: base.write_state(root, status, **extra)


def _unreadable(reason: str) -> Arrange:
    return lambda monkeypatch, root: base.unreadable_as(monkeypatch, root, reason)


#: Every state ``--json`` names: how it is written, its ``state``, ``reason`` and whether a backup is named.
STATES = [
    pytest.param(_none, "none", None, False, id="none"),
    pytest.param(_status("pending"), "pending", None, True, id="pending"),
    pytest.param(_status("applying"), "in_progress", None, True, id="applying"),
    pytest.param(_status("applied"), "in_progress", None, True, id="applied"),
    # The rolling-back state carries the reason it is rolled back for; ``in_progress`` has none (interface table).
    pytest.param(_status("rolling_back"), "in_progress", None, True, id="rolling_back"),
    pytest.param(_status("committed"), "committed", None, True, id="committed"),
    pytest.param(_status("rolled_back", reason="first_start_failed"), "rolled_back", "first_start_failed", True, id="rolled_back-first_start_failed"),
    pytest.param(_status("rolled_back", reason="swap_interrupted"), "rolled_back", "swap_interrupted", True, id="rolled_back-swap_interrupted"),
    pytest.param(_status("rolled_back", reason="swap_failed"), "rolled_back", "swap_failed", True, id="rolled_back-swap_failed"),
    pytest.param(_status("rolled_back", reason="stage_missing"), "rolled_back", "stage_missing", True, id="rolled_back-stage_missing"),
    pytest.param(_unreadable("io"), "unreadable", "io", False, id="unreadable-io"),
    pytest.param(_unreadable("not_a_file"), "unreadable", "not_a_file", False, id="unreadable-not_a_file"),
    pytest.param(_unreadable("invalid"), "unreadable", "invalid", False, id="unreadable-invalid"),
]


def canary_state(status: str, **extra: Any) -> Arrange:
    """The state of ``status`` with the canaries in it: the administrator, the stage id (the data directory is the
    canary folder). Unreadable ones keep the canaries in what they hold."""

    def arrange(monkeypatch, root: Path) -> None:
        if status in ("io", "not_a_file", "invalid"):
            raw = base.write_state(root, "applying", confirmed_by=CANARY_USER, stage_id=CANARY_STAGE)
            path = base.state_path(root)
            if status == "invalid":
                path.write_bytes(b"{" + raw)
            elif status == "not_a_file":
                path.unlink()
                path.mkdir(mode=0o700)
                (path / "inside.json").write_bytes(raw)
            else:
                base.unreadable_state(monkeypatch, root)
            return
        base.write_state(root, status, confirmed_by=CANARY_USER, stage_id=CANARY_STAGE, **extra)

    return arrange


CANARY_STATES = [
    pytest.param(canary_state("pending", waiting="other_data_directory"), id="pending"),
    pytest.param(canary_state("applying"), id="applying"),
    pytest.param(canary_state("committed"), id="committed"),
    pytest.param(canary_state("rolled_back"), id="rolled_back"),
    pytest.param(canary_state("io"), id="unreadable-io"),
    pytest.param(canary_state("not_a_file"), id="unreadable-not_a_file"),
    pytest.param(canary_state("invalid"), id="unreadable-invalid"),
]


# =============================================================================
# (a) pending --json
# =============================================================================


@pytest.mark.parametrize(("arrange", "state", "reason", "has_backup"), STATES)
def test_pending_json_is_one_line_with_the_state_and_writes_nothing(tmp_path, monkeypatch, capsys, arrange, state, reason, has_backup):
    """(a) Each of the six states (and each reason): exit 0, one line, the keys, ``state``, ``reason``, ``choices``,
    ``waiting`` null, ``backup_created_at`` named or null, no safety copy; no ``recover``, no ``error``; nothing written."""
    print_section("pending --json: the six states")
    root = instance(tmp_path, monkeypatch)
    arrange(monkeypatch, root)
    before = base.everything(root)
    ran = go(capsys, "pending", "--json")
    line = the_line(ran)
    assert ran.code == 0, f"exit 0 whenever the line was printed, an unreadable state included: exit {ran.code}: {ran.out}"
    assert KEYS <= set(line), f"the keys are always present: missing {sorted(KEYS - set(line))}: {line}"
    assert (line["state"], line["reason"], line["choices"], line["waiting"]) == (state, reason, CHOICES[state], None), f"state, reason, choices, waiting: {line}"
    assert "recover" not in line and "error" not in line, f"a read has no recover object and no error: {line}"
    if has_backup:
        assert instant(line["backup_created_at"]) == BACKUP_AT, f"the backup's moment, in UTC: {line}"
    else:
        assert line["backup_created_at"] is None, f"no backup named: {line}"
    assert line["safety_copy"] == {"present": False, "at": None}, f"no data of before kept: {line}"
    assert base.everything(root) == before, "a read writes, moves and removes nothing"
    print_success(f"{state}/{reason}: exit 0, one line")


@pytest.mark.parametrize("waiting", [*base.WAIT_REASONS, None])
def test_pending_json_names_why_a_pending_restore_waits(tmp_path, monkeypatch, capsys, waiting):
    """(a) ``waiting``: what the last start recorded on a pending restore, or null."""
    root = instance(tmp_path, monkeypatch)
    base.write_state(root, "pending", **({"waiting": waiting} if waiting else {}))
    ran = go(capsys, "pending", "--json")
    line = the_line(ran)
    assert (ran.code, line["state"], line["waiting"], line["choices"]) == (0, "pending", waiting, ["cancel"]), f"{waiting}: {line}"
    print_success(f"waiting {waiting}")


def test_pending_json_gives_the_backup_moment_in_utc_with_z(tmp_path, monkeypatch, capsys):
    """(a) ``backup_created_at`` is the instant in UTC, ending with ``Z``, whatever the offset the state was written with."""
    root = instance(tmp_path, monkeypatch)
    made = datetime(2026, 10, 20, 10, 30, 15, tzinfo=timezone(timedelta(hours=2)))
    base.write_state(root, "committed", backup_created_at=made)
    line = the_line(go(capsys, "pending", "--json"))
    assert instant(line["backup_created_at"]) == datetime(2026, 10, 20, 8, 30, 15, tzinfo=UTC), f"10:30:15+02:00 is 08:30:15Z: {line}"
    print_success("backup_created_at: UTC with Z")


# =============================================================================
# (a) safety_copy
# =============================================================================


def _previous_with(*names: str) -> Callable[[Path, Path], None]:
    return lambda root, elsewhere: base.previous_holding(root, *names)


def _previous_empty(root: Path, elsewhere: Path) -> None:
    (restore_dir(root) / "previous").mkdir(mode=0o700, parents=True)


def _previous_with_a_note_only(root: Path, elsewhere: Path) -> None:
    _previous_empty(root, elsewhere)
    (restore_dir(root) / "previous" / "notes.txt").write_text("not a swapped folder\n", encoding="utf-8")


def _previous_a_link(root: Path, elsewhere: Path) -> None:
    (elsewhere / "sqlite").mkdir(parents=True)
    restore_dir(root).mkdir(mode=0o700, parents=True, exist_ok=True)
    os.symlink(elsewhere, restore_dir(root) / "previous")


def _previous_a_file(root: Path, elsewhere: Path) -> None:
    restore_dir(root).mkdir(mode=0o700, parents=True, exist_ok=True)
    (restore_dir(root) / "previous").write_text("sqlite", encoding="utf-8")


def _no_previous(root: Path, elsewhere: Path) -> None:
    restore_dir(root).mkdir(mode=0o700, parents=True, exist_ok=True)


NO_SAFETY_COPY = [
    pytest.param(_no_previous, id="no-previous"),
    pytest.param(_previous_empty, id="empty"),
    pytest.param(_previous_with_a_note_only, id="no-swapped-folder"),
    pytest.param(_previous_a_link, id="a-link-to-a-folder-holding-sqlite"),
    pytest.param(_previous_a_file, id="a-file"),
]


@pytest.mark.parametrize("arrange", NO_SAFETY_COPY)
@pytest.mark.parametrize("state", [_none, _status("pending"), _unreadable("invalid")], ids=["none", "pending", "unreadable"])
def test_safety_copy_is_absent_unless_previous_is_a_plain_folder_holding_a_swapped_folder(tmp_path, monkeypatch, capsys, arrange, state):
    """(a) ``{"present": false, "at": null}``: no ``previous/``, an empty one, one with no swapped folder, a link, a file."""
    root = instance(tmp_path, monkeypatch)
    state(monkeypatch, root)
    arrange(root, tmp_path / "elsewhere")
    line = the_line(go(capsys, "pending", "--json"))
    assert line["safety_copy"] == {"present": False, "at": None}, f"no data of before kept: {line}"
    print_success("safety_copy absent")


@pytest.mark.parametrize("names", [("sqlite",), ("custom-uploads", "broker_reports"), ("scenario_catalog",)], ids=["sqlite", "two-folders", "scenario_catalog"])
@pytest.mark.parametrize("state", [_none, _status("pending"), _unreadable("invalid"), _unreadable("not_a_file")], ids=["none", "pending", "unreadable-invalid", "unreadable-not_a_file"])
def test_safety_copy_is_present_with_the_modification_time_of_previous(tmp_path, monkeypatch, capsys, names, state):
    """(a) With no readable ``applied_at``: ``present`` and ``at`` the modification time of ``.restore/previous/``, in UTC,
    whole seconds, ``Z``."""
    root = instance(tmp_path, monkeypatch)
    state(monkeypatch, root)
    base.previous_holding(root, *names)
    previous_at(root)
    line = the_line(go(capsys, "pending", "--json"))
    assert line["safety_copy"]["present"] is True and instant(line["safety_copy"]["at"]) == PREVIOUS_AT, f"present, at the folder's modification time {PREVIOUS_AT}: {line}"
    assert set(line["safety_copy"]) == {"present", "at"}, f"safety_copy is {{present, at}}: {line}"
    print_success(f"safety_copy {names}: present, at the folder's time")


@pytest.mark.parametrize("status", ["applied", "committed"])
def test_safety_copy_takes_the_applied_at_of_a_readable_state(tmp_path, monkeypatch, capsys, status):
    """(a) ``at``: the readable state's ``applied_at`` (the folder's modification time is another moment)."""
    root = instance(tmp_path, monkeypatch)
    base.write_state(root, status)
    base.previous_holding(root, "sqlite")
    previous_at(root)
    line = the_line(go(capsys, "pending", "--json"))
    applied = base.FINISHED_AT - timedelta(minutes=5)
    assert line["safety_copy"]["present"] is True and instant(line["safety_copy"]["at"]) == applied, f"at the state's applied_at {applied}, not {PREVIOUS_AT}: {line}"
    print_success(f"{status}: at = applied_at")


# =============================================================================
# (a)(b) what never reaches standard output
# =============================================================================


@pytest.mark.parametrize("arrange", CANARY_STATES)
def test_pending_json_names_neither_the_administrator_nor_the_data_directory_nor_the_stage(tmp_path, monkeypatch, capsys, arrange):
    """(b) A state whose ``confirmed_by`` is an email, in a data directory with a distinctive name, with a distinctive
    stage id: none of the three is in the line, nor on standard error; no key named after them either."""
    root = instance(tmp_path, monkeypatch, CANARY_FOLDER)
    arrange(monkeypatch, root)
    ran = go(capsys, "pending", "--json")
    line = the_line(ran)
    assert ran.code == 0, f"exit 0: {ran.out}"
    for canary in CANARIES:
        assert canary not in ran.out, f"{canary!r} must not be on standard output: {ran.out}"
        assert canary not in ran.err, f"{canary!r} must not be on standard error: {ran.err}"
    assert os.fspath(root) not in ran.out and not ({"confirmed_by", "data_dir", "stage_id", "path"} & set(line)), f"no path, no confirmed_by, data_dir or stage_id key: {line}"
    print_success("no canary on either stream")


@pytest.mark.parametrize("choice", ["previous", "cancel"])
def test_recover_json_names_neither_the_administrator_nor_the_data_directory_nor_the_stage(tmp_path, monkeypatch, capsys, choice):
    """(b) The same for the line an action prints."""
    root = instance(tmp_path, monkeypatch, CANARY_FOLDER)
    if choice == "previous":
        canary_state("invalid")(monkeypatch, root)
        base.previous_holding(root, "custom-uploads")
    else:
        (stage_data_dir(root, CANARY_STAGE) / "sqlite").mkdir(mode=0o700, parents=True)
        (stage_dir(root, CANARY_STAGE) / "report.json").write_text("{}\n", encoding="utf-8")
        base.write_state(root, "pending", confirmed_by=CANARY_USER, stage_id=CANARY_STAGE)
    ran = go(capsys, "pending", "--json", "--recover", choice)
    the_line(ran)
    assert ran.code == 0, f"precondition: {choice} done: exit {ran.code}: {ran.out}"
    for canary in CANARIES:
        assert canary not in ran.out, f"{canary!r} must not be on standard output: {ran.out}"
    print_success(f"--recover {choice} --json: no canary")


class StdoutHandler(logging.Handler):
    """A logging handler writing to whatever ``sys.stdout`` is when a record is emitted: where the application's console
    handler writes (``logging_config``); it also records what was logged."""

    def __init__(self) -> None:
        super().__init__(logging.DEBUG)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())
        sys.stdout.write(record.getMessage() + "\n")


@contextmanager
def logs_to_stdout() -> Iterator[StdoutHandler]:
    handler = StdoutHandler()
    root = logging.getLogger()
    level = root.level
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)
    try:
        yield handler
    finally:
        root.removeHandler(handler)
        root.setLevel(level)


@pytest.mark.parametrize("argv", [("pending", "--json"), ("pending", "--json", "--recover", "previous")], ids=["pending", "recover-previous"])
def test_log_lines_of_the_modules_never_reach_standard_output(tmp_path, monkeypatch, capsys, argv):
    """(a) The unreadable state logs an error (and a recovery a warning) from the modules the command calls; a logging
    handler writing to standard output must not put them before the line: standard output is that one line alone."""
    root = instance(tmp_path, monkeypatch)
    base.unreadable_as(monkeypatch, root, "invalid")
    base.previous_holding(root, "custom-uploads")
    with logs_to_stdout() as handler:
        # Control: this handler would show the log line of the module on standard output.
        base.apply_module().restore_state_problem(root)
        control = capsys.readouterr().out
        assert handler.messages and control, f"precondition: reading the unreadable state logs a line this handler writes to standard output: {handler.messages}: {control!r}"
        ran = go(capsys, *argv)
    line = the_line(ran)
    assert ran.code == 0 and line["state"] in ("unreadable", "none"), f"exit 0, the line: {ran.out}"
    print_success("no log line on standard output")


def test_the_script_prints_one_line_on_standard_output_for_each_state(tmp_path):
    """(a), end to end, in a process of its own: its real streams, for an unreadable state (it logs) and for none."""
    data = cli.make_data_dir(tmp_path / "instance").resolve()
    env = cli.child_env(data)
    none = cli.script("pending", "--json", env=env, cwd=tmp_path)
    assert none.returncode == 0 and json.loads(none.stdout)["state"] == "none" and none.stdout.count("\n") == 1, f"none: exit {none.returncode}\n{none.stdout[-cli.TAIL:]}{none.stderr[-cli.TAIL:]}"
    base.write_state(data, "applying")
    base.state_path(data).write_text("{" + base.STATE_MARK, encoding="utf-8")
    done = cli.script("pending", "--json", env=env, cwd=tmp_path)
    assert done.returncode == 0 and done.stdout.count("\n") == 1, f"unreadable: exit {done.returncode}\n{done.stdout[-cli.TAIL:]}{done.stderr[-cli.TAIL:]}"
    line = json.loads(done.stdout)
    assert (line["state"], line["reason"], line["choices"]) == ("unreadable", "invalid", ["previous"]), f"the unreadable state: {line}"
    assert base.STATE_MARK not in done.stdout and "Traceback" not in done.stderr, f"nothing of the state's content, no traceback: {done.stderr[-cli.TAIL:]}"
    print_success("script: one line for none and for unreadable")


@cli.needs_fifos
def test_a_fifo_where_the_state_should_be_is_never_opened(tmp_path):
    """(a) ``not_a_file`` for a FIFO, in a process of its own with a timeout: opening it would wait for a writer for ever.
    ``--recover previous`` then sets it aside, still without opening it."""
    data = cli.make_data_dir(tmp_path / "instance").resolve()
    base.state_path(data).parent.mkdir(mode=0o700, parents=True)
    os.mkfifo(base.state_path(data))
    base.previous_holding(data, "custom-uploads")
    env = cli.child_env(data)
    shown = cli.script("pending", "--json", env=env, cwd=tmp_path)
    assert shown.returncode == 0, f"pending --json: exit 0: exit {shown.returncode}\n{shown.stdout[-cli.TAIL:]}{shown.stderr[-cli.TAIL:]}"
    line = json.loads(shown.stdout)
    assert (line["state"], line["reason"], line["choices"]) == ("unreadable", "not_a_file", ["previous"]), f"a FIFO is not a file: {line}"
    done = cli.script("pending", "--json", "--recover", "previous", env=env, cwd=tmp_path)
    assert done.returncode == 0, f"--recover previous: exit 0: exit {done.returncode}\n{done.stdout[-cli.TAIL:]}{done.stderr[-cli.TAIL:]}"
    assert (json.loads(done.stdout)["state"], json.loads(done.stdout)["recover"]) == ("none", {"choice": "previous", "done": True}), f"recovered: {done.stdout}"
    print_success("FIFO: not_a_file, recovered, never opened")


def test_a_link_where_the_state_should_be_is_not_a_file(tmp_path, monkeypatch, capsys):
    """(a) A link to a good state file is ``not_a_file``: it is never followed."""
    root = instance(tmp_path, monkeypatch)
    base.write_state(root, "pending")
    target = tmp_path / "elsewhere.json"
    target.write_bytes(base.state_path(root).read_bytes())
    base.state_path(root).unlink()
    base.state_path(root).symlink_to(target)
    ran = go(capsys, "pending", "--json")
    line = the_line(ran)
    assert (ran.code, line["state"], line["reason"]) == (0, "unreadable", "not_a_file"), f"a link is not followed: {line}"
    print_success("link: not_a_file")


# =============================================================================
# (c) a data directory that cannot be determined, usage errors
# =============================================================================


@pytest.mark.parametrize("what", ["missing", "a-file"])
@pytest.mark.parametrize("argv", [("pending", "--json"), ("pending", "--json", "--recover", "previous")], ids=["pending", "recover-previous"])
def test_a_data_directory_that_cannot_be_used_is_exit_5_with_nothing_on_standard_output(tmp_path, monkeypatch, capsys, what, argv):
    """(c) Missing, or no folder: standard output empty, the cause on standard error, exit 5; nothing created."""
    place = tmp_path / "absent"
    if what == "a-file":
        place.write_text("not a folder", encoding="utf-8")
    cli.point_at(monkeypatch, place)
    ran = go(capsys, *argv)
    assert (ran.code, ran.out) == (5, ""), f"exit 5 and an empty standard output: exit {ran.code}: {ran.out!r}"
    assert ran.err.strip(), "the cause is on standard error"
    assert place.is_file() if what == "a-file" else not place.exists(), "nothing created"
    print_success(f"{what}: exit 5, stdout empty")


def test_json_is_accepted_beside_the_actions_that_may_take_it(capsys):
    """(c) Barrier: ``--json`` alone, and with ``--recover <word>`` in either order (any word: the word is judged by the
    command, exit 4, not by argparse)."""
    for argv in (("pending", "--json"), ("pending", "--json", "--recover", "previous"), ("pending", "--recover", "cancel", "--json"), ("pending", "--recover=previous"), ("pending", "--json", "--recover", "restore")):
        accepts(capsys, *argv)
    print_success("--json and --recover WORD accepted")


@pytest.mark.parametrize("argv", [("pending", "--json", "--cancel"), ("pending", "--cancel", "--json")], ids=["json-cancel", "cancel-json"])
def test_json_and_cancel_cannot_go_together(capsys, argv):
    """(c) argparse refuses them (exit 2) naming both; the message is not «unrecognized arguments» (``--json`` exists)."""
    accepts(capsys, "pending", "--json")
    err = refused_by_parser(capsys, *argv)
    assert "--json" in err and "--cancel" in err and "unrecognized" not in err, f"refused as exclusive, both named: {err}"
    print_success(f"{' '.join(argv)}: exit 2")


@pytest.mark.parametrize("argv", [("pending", "--recover"), ("pending", "--recover", "--json"), ("pending", "--json", "--recover")], ids=["bare", "bare-then-json", "json-then-bare"])
def test_recover_needs_an_argument(capsys, argv):
    """(c) ``--recover`` was a bare flag in the 1.3 development builds, never released: it now takes a choice."""
    accepts(capsys, "pending", "--recover", "previous")
    err = refused_by_parser(capsys, *argv)
    assert "--recover" in err and "expected one argument" in err, f"refused: --recover expects one argument: {err}"
    print_success(f"{' '.join(argv)}: exit 2")


@pytest.mark.parametrize("argv", [("pending", "--cancel", "--recover", "x"), ("pending", "--recover", "x", "--cancel"), ("pending", "--recover", "previous", "--cancel")], ids=["cancel-recover", "recover-cancel", "previous-cancel"])
def test_recover_and_cancel_exclude_each_other(capsys, argv):
    """(c) argparse refuses them together (exit 2), naming both."""
    accepts(capsys, "pending", "--recover", "x")
    err = refused_by_parser(capsys, *argv)
    assert "not allowed with" in err and "--recover" in err and "--cancel" in err, f"refused as exclusive: {err}"
    print_success(f"{' '.join(argv)}: exit 2")


# =============================================================================
# (d)(e)(f) --recover <choice>
# =============================================================================


def unreadable_with_previous(monkeypatch, root: Path) -> None:
    base.unreadable_as(monkeypatch, root, "invalid")
    base.previous_holding(root, "custom-uploads", "broker_reports")


def pending_with_a_copy(monkeypatch, root: Path) -> None:
    """A pending restore whose checked copy is kept in ``.restore/stage/``."""
    stage = base.checked_copies(root, 1)[0]
    base.write_state(root, "pending", stage_id=stage)


def pending_and_previous(monkeypatch, root: Path) -> None:
    base.write_state(root, "pending")
    base.previous_holding(root, "custom-uploads")


def none_with_previous(monkeypatch, root: Path) -> None:
    base.previous_holding(root, "custom-uploads")


def applying_with_previous(monkeypatch, root: Path) -> None:
    base.write_state(root, "applying")
    base.previous_holding(root, "custom-uploads")


@dataclass(frozen=True)
class Case:
    """One ``--recover`` and what it must do: the choice, the exit code, the ``error`` of its line, the ``state`` the
    line describes after the action, whether a server serves the data directory, what is made to fail."""

    arrange: Arrange
    choice: str
    code: int
    error: str | None
    after: str
    serve: bool = False
    fail: str | None = None
    #: The stable code the human text holds on its ❌ line (today's messages), where the interface fixes one.
    word: str | None = None


NOT_VALID = "choice_not_valid"
CASES = [
    pytest.param(Case(unreadable_with_previous, "previous", 0, None, "none"), id="previous-on-unreadable"),
    pytest.param(Case(none_with_previous, "previous", 3, "nothing_to_recover", "none", word="restore_nothing_to_recover"), id="previous-on-none"),
    pytest.param(Case(pending_and_previous, "previous", 4, NOT_VALID, "pending"), id="previous-on-pending"),
    pytest.param(Case(applying_with_previous, "previous", 4, NOT_VALID, "in_progress"), id="previous-on-applying"),
    pytest.param(Case(lambda mp, root: base.write_state(root, "committed"), "previous", 4, NOT_VALID, "committed"), id="previous-on-committed"),
    pytest.param(Case(lambda mp, root: base.write_state(root, "rolled_back"), "previous", 4, NOT_VALID, "rolled_back"), id="previous-on-rolled_back"),
    pytest.param(Case(unreadable_with_previous, "restore", 4, NOT_VALID, "unreadable"), id="unknown-word-on-unreadable"),
    pytest.param(Case(_none, "restore", 4, NOT_VALID, "none"), id="unknown-word-on-none"),
    pytest.param(Case(pending_and_previous, "restore", 4, NOT_VALID, "pending"), id="unknown-word-on-pending"),
    pytest.param(Case(pending_with_a_copy, "cancel", 0, None, "none"), id="cancel-on-pending"),
    pytest.param(Case(_none, "cancel", 3, "nothing_to_recover", "none"), id="cancel-on-none"),
    pytest.param(Case(unreadable_with_previous, "cancel", 4, NOT_VALID, "unreadable"), id="cancel-on-unreadable"),
    pytest.param(Case(unreadable_with_previous, "previous", 5, "restore_in_use", "unreadable", serve=True, word="restore_in_use"), id="previous-while-served"),
    pytest.param(Case(unreadable_with_previous, "previous", 5, "restore_apply_failed", "unreadable", fail="move", word="restore_apply_failed"), id="previous-move-fails"),
    pytest.param(Case(unreadable_with_previous, "previous", 5, "failed", "unreadable", fail="recover"), id="previous-oserror"),
    pytest.param(Case(pending_with_a_copy, "cancel", 5, "failed", "pending", fail="cancel"), id="cancel-oserror"),
]


def make_it_fail(monkeypatch, what: str | None) -> None:
    """A move of the recovery that fails (``OSError``), or the whole recovery or cancel raising an ``OSError``."""
    apply = base.apply_module()

    def refused(*args: Any, **kwargs: Any) -> None:
        raise OSError(errno.EIO, os.strerror(errno.EIO))

    if what == "move":
        monkeypatch.setattr(apply, "_move", refused)
    elif what == "recover":
        monkeypatch.setattr(apply, "recover_unreadable_restore", refused)
    elif what == "cancel":
        monkeypatch.setattr(apply, "cancel_restore", refused)


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
@pytest.mark.parametrize("case", CASES)
def test_recover_exits_with_the_code_of_the_interface_with_or_without_json(tmp_path, monkeypatch, capsys, case, as_json):
    """(d)(e)(f) The exit codes are fixed and the same with or without ``--json``: 0 done, 3 nothing to recover, 4 the
    choice is not valid in this state, 5 failed. With ``--json``: one line, the state after the action, ``recover`` and
    ``error``; without it today's text, a ✅ line when done and a ❌ line when not. A refusal changes nothing."""
    print_section("pending --recover <choice>")
    root = instance(tmp_path, monkeypatch)
    case.arrange(monkeypatch, root)
    make_it_fail(monkeypatch, case.fail)
    before = base.everything(root)
    argv = ("pending", *(("--json",) if as_json else ()), "--recover", case.choice)
    with serving(root) if case.serve else nullcontext():
        ran = go(capsys, *argv)
    assert ran.code == case.code, f"{' '.join(argv)}: exit {case.code}, not {ran.code}\n{ran.out}{ran.err}"
    if as_json:
        line = the_line(ran)
        assert line["state"] == case.after and line["choices"] == CHOICES[case.after], f"the state after the action is {case.after}: {line}"
        assert line["recover"] == {"choice": case.choice, "done": case.code == 0}, f"recover says what was asked and whether it was done: {line}"
        assert line.get("error") == case.error, f"error {case.error!r} (absent when the exit code is 0): {line}"
        if case.code == 0:
            assert "error" not in line, f"no error when done: {line}"
    else:
        assert not ran.out.lstrip().startswith("{"), f"human text, not the line: {ran.out}"
        if case.code == 0:
            assert any(line.startswith("✅") for line in ran.lines) and not ran.refused, f"done: a ✅ line, no ❌: {ran.out}"
        else:
            assert ran.refused and not any(line.startswith("✅") for line in ran.lines), f"not done: a ❌ line, no ✅ (nothing is claimed done): {ran.out}"
            if case.word:
                assert case.word in " ".join(ran.refused), f"today's code {case.word} stays on the ❌ line: {ran.refused}"
    if case.code != 0 and case.fail != "move":
        assert base.everything(root) == before, "a refused or failed recovery changes nothing"
    print_success(f"{case.choice}: exit {case.code}, {'json' if as_json else 'human'}")


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
@pytest.mark.parametrize("reason", base.REASONS)
def test_recover_previous_puts_the_data_of_before_back_and_a_second_run_changes_nothing(tmp_path, monkeypatch, capsys, reason, as_json):
    """(d) With an unreadable state (each reason): exit 0; each folder of ``previous/`` back in place, its live one in
    ``.restore/failed/``, the others as they were; the state kept aside as ``restore.json.unreadable-<UTC>``. Run again:
    exit 3 and the data directory, ``.restore`` included, byte for byte as the first run left it."""
    root = instance(tmp_path, monkeypatch)
    base.unreadable_as(monkeypatch, root, reason)
    state = None if reason == "not_a_file" else base.state_path(root).read_bytes()
    base.previous_holding(root, "custom-uploads", "broker_reports")
    live_before = {name: base.files_below(root / name) for name in base.SWAPPED}
    flags = ("--json",) if as_json else ()
    first = go(capsys, "pending", *flags, "--recover", "previous")
    assert first.code == 0, f"--recover previous on an unreadable state ({reason}): exit 0: exit {first.code}\n{first.out}{first.err}"
    if as_json:
        assert (the_line(first)["state"], the_line(first)["recover"]) == ("none", {"choice": "previous", "done": True}), f"the state after is none: {first.out}"
    for name in ("custom-uploads", "broker_reports"):
        assert base.files_below(root / name) == {"before.bin": base.BEFORE[name][f"{name}/before.bin"]}, f"{name}: the data of before back in place"
        assert base.files_below(restore_dir(root) / "failed" / name) == live_before[name], f"{name}: the live one in .restore/failed/"
    assert {name: base.files_below(root / name) for name in ("sqlite", "scenario_catalog")} == {name: live_before[name] for name in ("sqlite", "scenario_catalog")}, "the folders previous/ did not hold, as they were"
    kept = [path for path in restore_dir(root).iterdir() if re.fullmatch(r"restore\.json\.unreadable-\d{8}T\d{6}Z", path.name)]
    assert not os.path.lexists(base.state_path(root)) and len(kept) == 1, f"the state renamed: {sorted(path.name for path in restore_dir(root).iterdir())}"
    if state is not None:
        assert kept[0].read_bytes() == state, "the state kept as it was"
    after_first = base.everything(root)
    second = go(capsys, "pending", *flags, "--recover", "previous")
    assert second.code == 3, f"--recover previous again: nothing to recover, exit 3: exit {second.code}\n{second.out}{second.err}"
    assert base.everything(root) == after_first, "the second run moved nothing, wrote nothing, kept no second unreadable state"
    if as_json:
        line = the_line(second)
        assert (line["state"], line["recover"], line["error"]) == ("none", {"choice": "previous", "done": False}, "nothing_to_recover"), f"the second line: {line}"
    print_success(f"{reason}: back, then exit 3 and nothing changed")


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
def test_recover_cancel_drops_a_pending_restore_with_its_copy_and_a_second_run_changes_nothing(tmp_path, monkeypatch, capsys, as_json):
    """(d) ``--recover cancel`` on a pending restore: exit 0, the state gone, its checked copy gone, the live data as it
    was. Run again: exit 3 and nothing changed."""
    root = instance(tmp_path, monkeypatch)
    pending_with_a_copy(monkeypatch, root)
    live = base.live(root)
    flags = ("--json",) if as_json else ()
    first = go(capsys, "pending", *flags, "--recover", "cancel")
    assert first.code == 0, f"--recover cancel: exit 0: exit {first.code}\n{first.out}{first.err}"
    base.nothing_pending(root)
    assert base.live(root) == live, "the live data as it was"
    if as_json:
        assert (the_line(first)["state"], the_line(first)["recover"]) == ("none", {"choice": "cancel", "done": True}), f"the state after is none: {first.out}"
    after_first = base.everything(root)
    second = go(capsys, "pending", *flags, "--recover", "cancel")
    assert second.code == 3, f"--recover cancel again: nothing to recover, exit 3: exit {second.code}\n{second.out}{second.err}"
    assert base.everything(root) == after_first, "the second run changed nothing"
    print_success("cancel: dropped with its copy, then exit 3")


def test_recover_previous_moves_nothing_when_the_move_fails_and_claims_nothing(tmp_path, monkeypatch, capsys):
    """(d) A move that fails (``OSError``): exit 5, ``restore_apply_failed``; the state is still unreadable and still there,
    not kept aside; the live folders are as they were; and the next run, once the fault is gone, still recovers."""
    root = instance(tmp_path, monkeypatch)
    unreadable_with_previous(monkeypatch, root)
    state = base.state_path(root).read_bytes()
    live_before = {name: base.files_below(root / name) for name in base.SWAPPED}
    with monkeypatch.context() as broken:
        make_it_fail(broken, "move")
        failed = go(capsys, "pending", "--json", "--recover", "previous")
    line = the_line(failed)
    assert (failed.code, line["state"], line["error"], line["recover"]["done"]) == (5, "unreadable", "restore_apply_failed", False), f"exit 5, still unreadable, not done: {failed.out}"
    assert base.state_path(root).read_bytes() == state and not [path for path in restore_dir(root).iterdir() if "unreadable-" in path.name], "the state is where it was, not kept aside"
    assert {name: base.files_below(root / name) for name in base.SWAPPED} == live_before, "the live folders are as they were"
    again = go(capsys, "pending", "--json", "--recover", "previous")
    assert (again.code, the_line(again)["state"]) == (0, "none"), f"the fault gone, the next run recovers: exit {again.code}: {again.out}"
    print_success("move fails: exit 5, state kept, the next run recovers")


# =============================================================================
# (g) B5-1b §9.2: --recover owner
# =============================================================================

OWNER_MODULE = "backend.app.services.platform.instance_backup.owner"
APPLY_MODULE = "backend.app.services.platform.instance_backup.apply"
#: The chosen account, a distinctive number: it must never be in a line (a plain 42 could be a minute of a timestamp).
OWNER_ID = 4217
OWNER_EMAIL = "owner.b51c@example.com"
#: A stray ``reset_path`` on A's ``link_only`` result and the value of a stale ``owner_reset_path`` key in a state file
#: of an older LibreFolio: a canary that must reach no state file, no standard stream and no log line (A writes the real
#: link in the instance log itself).
LINK_CANARY = "/reset-password#token=b51c-canary-0123456789abcdef"
#: The owner's chosen-account codes that must never reach the line.
FAILED_CODE = "EMAIL_TAKEN"
OTHER_CODE = "USER_NOT_FOUND"


class Outcome(StrEnum):
    """A's ``OwnerResetOutcome``: ``sent`` or ``link_only`` only."""

    SENT = "sent"
    LINK_ONLY = "link_only"


class FakeOwnerAssignmentError(Exception):
    """A's ``OwnerAssignmentError``: its ``code`` is all that is recorded."""

    def __init__(self, code: str) -> None:
        super().__init__(f"the owner {OWNER_EMAIL} cannot be assigned: {code}")
        self.code = code


@dataclass
class FakeA:
    """A's ``assign_owner_and_send_reset(session, user_id, *, now=None)``: each call's user id recorded, then ``outcome``
    answered or ``raises`` raised; a ``since=`` is a ``TypeError``, as for the real function. It reads no database: the
    commands under test never give it more than a session object."""

    outcome: Outcome | None = None
    raises: BaseException | None = None
    calls: list[int] = field(default_factory=list)

    async def __call__(self, session: Any, user_id: int, *, now: Any = None) -> Any:
        self.calls.append(user_id)
        if self.raises is not None:
            raise self.raises
        assert self.outcome is not None, "a FakeA answers an outcome or raises"
        result = SimpleNamespace(outcome=self.outcome, user_id=user_id, username="b51c_owner", email=OWNER_EMAIL, expires_at=None)
        if self.outcome is Outcome.LINK_ONLY:
            result.reset_path = LINK_CANARY  # a stray attribute: the restore must never read it
        return result


@dataclass
class Wired:
    """What ``owner._assign_owner`` was asked: the fake, and each lookup."""

    fake: FakeA | None
    lookups: list[str] = field(default_factory=list)


def wire(monkeypatch, fake: FakeA | None) -> Wired:
    """``owner._assign_owner`` replaced, as ``test_backup_owner.py`` does: it returns ``(fake, FakeOwnerAssignmentError)``,
    or raises ``ImportError`` (A not merged) for ``fake`` ``None``. The command must reach A's function only through it."""
    owner = importlib.import_module(OWNER_MODULE)
    assert callable(getattr(owner, "_assign_owner", None)), "precondition: owner._assign_owner() is the lazy lookup of A's function (B5-1)"
    wired = Wired(fake)

    def lookup() -> tuple[Any, type[Exception]]:
        wired.lookups.append("_assign_owner")
        if fake is None:
            raise ImportError("cannot import name 'assign_owner_and_send_reset' from 'backend.app.services.accounts.instance_owner'")
        return fake, FakeOwnerAssignmentError

    monkeypatch.setattr(owner, "_assign_owner", lookup)
    return wired


def owner_state(status: str = "committed", *, code: str | None = FAILED_CODE, outcome: str | None = None, **extra: Any) -> Arrange:
    """A restore confirmed from the app with the owner named, its outcome ``error:<code>`` (or ``outcome`` as given)."""
    recorded = outcome if outcome is not None else (f"error:{code}" if code else None)
    fields: dict[str, Any] = {"confirmed_by": "b51c-admin", "confirmed_via": "admin", "owner_user_id": OWNER_ID, "owner_outcome": recorded, **extra}
    return lambda monkeypatch, root: base.write_state(root, status, **fields)


def recorded_owner(root: Path) -> tuple[Any, Any]:
    """What ``restore.json`` says of the owner: id, outcome. The file never holds an ``owner_reset_path`` key nor a link."""
    raw = base.state_path(root).read_text(encoding="utf-8")
    record = json.loads(raw)
    assert "owner_reset_path" not in record, f"the state has no owner_reset_path key: {sorted(record)}"
    assert LINK_CANARY not in raw, "no link in restore.json"
    return tuple(record.get(name, "<missing>") for name in ("owner_user_id", "owner_outcome"))


def with_stale_link(root: Path) -> None:
    """``owner_reset_path`` written into the state file as raw JSON, as a state of an older LibreFolio holds it."""
    path = base.state_path(root)
    record = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(json.dumps({**record, "owner_reset_path": LINK_CANARY}), encoding="utf-8")
    path.chmod(0o600)


def outcome_lines(capsys, outcome: str | None) -> list[str]:
    """The lines ``_print_owner_outcome`` prints for a state recording ``outcome``: what a recovery that ends with that
    outcome must say, whatever the words are."""
    capsys.readouterr()
    backup_cli._print_owner_outcome(SimpleNamespace(owner_user_id=OWNER_ID, owner_outcome=outcome))
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert lines, f"precondition: _print_owner_outcome says something for {outcome!r}"
    return lines


@contextmanager
def owner_lock_held(root: Path) -> Iterator[None]:
    """``.restore/owner.lock`` held by another holder, as the startup step of a server (or a second command) holds it: an
    exclusive ``flock`` on a descriptor of the test's own, which conflicts with the product's."""
    fd = os.open(restore_dir(root) / "owner.lock", os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def never_in(ran: Ran, *secrets: str) -> None:
    shown = [secret for secret in secrets if secret in ran.out]
    assert shown == [], f"standard output holds {shown}: {ran.out}"


# --- the snapshot ---------------------------------------------------------------

#: (how the state is written, its ``state``, ``reason``, ``choices``).
OWNER_SNAPSHOTS = [
    pytest.param(owner_state(code=FAILED_CODE), "committed", "owner_assignment", ["owner"], id="committed-admin-owner-error"),
    pytest.param(owner_state(code=OTHER_CODE), "committed", "owner_assignment", ["owner"], id="committed-admin-owner-other-error"),
    pytest.param(owner_state(code=None), "committed", None, [], id="committed-owner-pending"),
    *(pytest.param(owner_state(outcome=value), "committed", None, [], id=f"committed-{value}") for value in ("sent", "link_only")),
    # B5-1j: the owner picked at a confirmation from the command line or by the hosting panel is recovered like the app's.
    pytest.param(owner_state(confirmed_by="cli", confirmed_via="cli"), "committed", "owner_assignment", ["owner"], id="committed-cli-error"),
    pytest.param(owner_state(confirmed_by="panel", confirmed_via="panel"), "committed", "owner_assignment", ["owner"], id="committed-panel-error"),
    pytest.param(owner_state(code=None, confirmed_by="cli", confirmed_via="cli"), "committed", None, [], id="committed-cli-owner-pending"),
    pytest.param(owner_state(outcome="link_only", confirmed_by="cli", confirmed_via="cli"), "committed", None, [], id="committed-cli-link_only"),
    pytest.param(owner_state(owner_user_id=None, outcome="none", confirmed_by="cli", confirmed_via="cli"), "committed", None, [], id="committed-cli-nobody-picked"),
    pytest.param(owner_state(owner_user_id=None), "committed", None, [], id="committed-no-owner-error"),
    pytest.param(owner_state("pending"), "pending", None, ["cancel"], id="pending-owner-error"),
    pytest.param(owner_state("applying"), "in_progress", None, [], id="applying-owner-error"),
    pytest.param(owner_state("rolled_back"), "rolled_back", "first_start_failed", [], id="rolled_back-owner-error"),
]


@pytest.mark.parametrize(("arrange", "state", "reason", "choices"), OWNER_SNAPSHOTS)
def test_pending_json_offers_owner_only_for_a_failed_owner_assignment(tmp_path, monkeypatch, capsys, arrange, state, reason, choices):
    """(g) §9.2, B5-1j: ``reason: "owner_assignment"`` and ``choices: ["owner"]`` only for a committed restore with an owner
    named and an ``error:`` outcome, whoever confirmed it (the app, the command line, the panel); every other state is as
    today. A read: nothing written."""
    print_section("(g) B5-1b pending --json: the owner's choice")
    root = instance(tmp_path, monkeypatch)
    arrange(monkeypatch, root)
    before = base.everything(root)
    ran = go(capsys, "pending", "--json")
    line = the_line(ran)
    assert ran.code == 0, f"exit 0: {ran.out}"
    assert (line["state"], line["reason"], line["choices"]) == (state, reason, choices), f"state, reason, choices: {line}"
    assert base.everything(root) == before, "a read writes nothing"
    print_success(f"{state}/{reason}: {choices}")


@pytest.mark.parametrize("code", [FAILED_CODE, OTHER_CODE])
def test_the_owner_assignment_snapshot_names_no_code_name_address_id_or_link(tmp_path, monkeypatch, capsys, code):
    """(g) §9.2: the line of a failed owner assignment has the usual keys and no other, and none of the code, the owner's
    id, its address, the link of a stale state (an ``owner_reset_path`` key an older LibreFolio wrote), the administrator, the stage or the data directory; standard error is as
    clean."""
    monkeypatch.setenv("LIBREFOLIO_ADMIN_EMAIL", OWNER_EMAIL)
    root = instance(tmp_path, monkeypatch, CANARY_FOLDER)
    owner_state(code=code, confirmed_by=CANARY_USER, stage_id=CANARY_STAGE)(monkeypatch, root)
    with_stale_link(root)
    ran = go(capsys, "pending", "--json")
    line = the_line(ran)
    assert set(line) == KEYS and line["choices"] == ["owner"], f"only the usual keys: {line}"
    secrets = (*CANARIES, code, str(OWNER_ID), OWNER_EMAIL, LINK_CANARY, "reset-password", "owner_user_id", "owner_outcome", "owner_reset_path")
    shown = [secret for secret in secrets if secret in ran.out or secret in ran.err]
    assert shown == [], f"the line and standard error hold {shown}: {ran.out}{ran.err}"
    print_success("owner_assignment: names nothing")


def test_the_help_and_the_choices_name_owner():
    """(g) §9.2: ``RECOVER_CHOICES`` is ``("previous", "cancel", "owner")``."""
    assert backup_cli.RECOVER_CHOICES == ("previous", "cancel", "owner"), f"the choices: {backup_cli.RECOVER_CHOICES}"
    print_success("RECOVER_CHOICES")


def test_pending_help_names_the_owner_choice(monkeypatch, capsys):
    """(g) §9.2: the help of ``--recover`` names ``owner``."""
    text = cli.help_of(monkeypatch, capsys, "backup", "pending")
    recover = text[text.rindex("--recover") :].split(" --json ")[0]
    assert recover.startswith("--recover CHOICE") and "owner" in recover, f"--recover's own entry of the help names owner: {recover}"
    print_success("pending --help: owner")


# --- --recover owner where the state does not offer it ----------------------------

NOT_OFFERED = [
    pytest.param(_none, 3, "nothing_to_recover", "none", id="no-state"),
    pytest.param(owner_state(code=None), 4, NOT_VALID, "committed", id="committed-owner-pending"),
    *(pytest.param(owner_state(outcome=value), 4, NOT_VALID, "committed", id=f"committed-{value}") for value in ("sent", "link_only")),
    pytest.param(owner_state(code=None, confirmed_by="cli", confirmed_via="cli"), 4, NOT_VALID, "committed", id="committed-cli-owner-pending"),
    pytest.param(owner_state(owner_user_id=None, outcome="none", confirmed_by="panel", confirmed_via="panel"), 4, NOT_VALID, "committed", id="committed-panel-nobody-picked"),
    pytest.param(owner_state(owner_user_id=None), 4, NOT_VALID, "committed", id="committed-no-owner-error"),
    pytest.param(lambda mp, root: base.write_state(root, "committed"), 4, NOT_VALID, "committed", id="committed-no-owner-at-all"),
    pytest.param(owner_state("pending"), 4, NOT_VALID, "pending", id="pending-owner-error"),
    pytest.param(owner_state("applying"), 4, NOT_VALID, "in_progress", id="applying-owner-error"),
    pytest.param(owner_state("rolled_back"), 4, NOT_VALID, "rolled_back", id="rolled_back-owner-error"),
    pytest.param(_unreadable("invalid"), 4, NOT_VALID, "unreadable", id="unreadable"),
]


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
@pytest.mark.parametrize(("arrange", "code", "error", "after"), NOT_OFFERED)
def test_recover_owner_where_the_state_does_not_offer_it_changes_nothing(tmp_path, monkeypatch, capsys, arrange, code, error, after, as_json):
    """(g) §9.2, B5-1j: anything but a failed owner assignment (no outcome yet, an outcome of A, nobody picked, no
    owner, another phase, an unreadable state): exit 4 ``choice_not_valid``, and with no state at all exit 3
    ``nothing_to_recover``; a ❌ line; nothing on disk changes; A's function is never looked up."""
    print_section("(g) B5-1b --recover owner: not offered")
    root = instance(tmp_path, monkeypatch)
    arrange(monkeypatch, root)
    wired = wire(monkeypatch, FakeA(outcome=Outcome.SENT))
    before = base.everything(root)
    argv = ("pending", *(("--json",) if as_json else ()), "--recover", "owner")
    ran = go(capsys, *argv)
    assert ran.code == code, f"{' '.join(argv)}: exit {code}, not {ran.code}\n{ran.out}{ran.err}"
    if as_json:
        line = the_line(ran)
        assert line["state"] == after and "owner" not in line["choices"], f"the state after is {after}, owner not offered: {line}"
        assert (line["recover"], line["error"]) == ({"choice": "owner", "done": False}, error), f"recover not done, error {error}: {line}"
    else:
        assert ran.refused and not any(line.startswith("✅") for line in ran.lines), f"not done: a ❌ line, no ✅: {ran.out}"
    assert base.everything(root) == before, "a refused --recover owner changes nothing"
    assert (wired.lookups, wired.fake.calls) == ([], []), f"A's function never reached: {wired.lookups}, {wired.fake.calls}"
    print_success(f"exit {code} {error}")


@pytest.mark.parametrize("choice", ["previous", "cancel"])
def test_the_other_choices_are_not_valid_while_the_owner_assignment_failed(tmp_path, monkeypatch, capsys, choice):
    """(g) §9.2: a failed owner assignment offers ``owner`` only: ``--recover previous`` and ``--recover cancel`` are exit 4
    ``choice_not_valid`` there, the line saying ``["owner"]`` is what is valid, nothing changed."""
    root = instance(tmp_path, monkeypatch)
    owner_state()(monkeypatch, root)
    before = base.everything(root)
    ran = go(capsys, "pending", "--json", "--recover", choice)
    line = the_line(ran)
    assert (ran.code, line["error"], line["choices"], line["reason"]) == (4, NOT_VALID, ["owner"], "owner_assignment"), f"{choice}: exit 4, owner still offered: {line}"
    assert base.everything(root) == before, "nothing changed"
    print_success(f"{choice}: exit 4, owner still offered")


# --- --recover owner, offered -------------------------------------------------------


def run_owner(capsys, as_json: bool) -> Ran:
    return go(capsys, "pending", *(("--json",) if as_json else ()), "--recover", "owner")


def text_of(ran: Ran, as_json: bool) -> str:
    """What the command said in words: standard output, or with ``--json`` standard error."""
    return ran.err if as_json else ran.out


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
@pytest.mark.parametrize("outcome", [Outcome.SENT, Outcome.LINK_ONLY])
def test_recover_owner_clears_the_outcome_and_assigns_the_owner_at_once_when_nobody_serves(tmp_path, monkeypatch, capsys, caplog, outcome, as_json):
    """(g) §9.2: nobody serves the data directory: the outcome is cleared, A's function called once for the chosen account,
    its outcome recorded, exit 0 and the lines ``_print_owner_outcome`` prints for it — for ``link_only`` the ⚠️ line that
    says the link is in the instance log, never a link: the stray ``reset_path`` of A's result is in no stream, no log
    line and no state file. A ``--json`` line: committed, no reason, no choice left, ``recover`` done."""
    print_section(f"(g) B5-1b --recover owner: {outcome.value}")
    root = instance(tmp_path, monkeypatch)
    owner_state()(monkeypatch, root)
    fake = FakeA(outcome=outcome)
    wire(monkeypatch, fake)
    expected = outcome_lines(capsys, outcome.value)
    ran = run_owner(capsys, as_json)
    assert ran.code == 0, f"exit 0: exit {ran.code}\n{ran.out}{ran.err}"
    assert fake.calls == [OWNER_ID], f"A called once, for the chosen account: {fake.calls}"
    assert recorded_owner(root) == (OWNER_ID, outcome.value), f"the new outcome recorded, no link key: {recorded_owner(root)}"
    said_lines = text_of(ran, as_json).splitlines()
    missing = [line for line in expected if line not in said_lines]
    assert missing == [], f"the lines of the new outcome are said: {missing}\n{text_of(ran, as_json)}"
    assert not any(line.startswith("❌") for line in said_lines), f"nothing failed: {ran.out}{ran.err}"
    both = ran.out + ran.err
    assert LINK_CANARY not in both and "reset-password" not in both, f"no link in any stream: {both}"
    assert LINK_CANARY not in caplog.text, "no link in any log line"
    if outcome is Outcome.LINK_ONLY:
        warned = [line for line in said_lines if line.startswith("⚠️")]
        assert len(warned) == 1 and "log" in warned[0].lower(), f"link_only: one ⚠️ line that sends to the instance log: {said_lines}"
    if as_json:
        line = the_line(ran)
        assert (line["state"], line["reason"], line["choices"], line["recover"]) == ("committed", None, [], {"choice": "owner", "done": True}), f"the line: {line}"
        assert "error" not in line, f"no error when done: {line}"
        never_in(ran, LINK_CANARY, str(OWNER_ID), FAILED_CODE, OWNER_EMAIL, "reset-password")
    print_success(f"{outcome.value}: exit 0")


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
@pytest.mark.parametrize("via", ["cli", "panel"])
def test_recover_owner_clears_the_failed_outcome_of_a_command_line_or_panel_restore_and_assigns_the_owner(tmp_path, monkeypatch, capsys, caplog, via, as_json):
    """(g) B5-1j: the owner picked for a restore confirmed via ``cli`` or ``panel`` whose assignment failed
    (``error:EMAIL_TAKEN``): ``--recover owner`` clears the error and, nobody serving, calls A once for the picked account and
    records its outcome — exit 0, the lines ``_print_owner_outcome`` prints for it, no link anywhere. Red before B5-1j:
    exit 4 ``choice_not_valid``."""
    print_section(f"(g) B5-1j --recover owner via {via}")
    root = instance(tmp_path, monkeypatch)
    owner_state(confirmed_by=via, confirmed_via=via)(monkeypatch, root)
    fake = FakeA(outcome=Outcome.LINK_ONLY)
    wire(monkeypatch, fake)
    snapshot = the_line(go(capsys, "pending", "--json"))
    assert (snapshot["reason"], snapshot["choices"]) == ("owner_assignment", ["owner"]), f"[new] B5-1j: the snapshot offers owner for a restore via {via}: {snapshot}"
    expected = outcome_lines(capsys, "link_only")
    ran = run_owner(capsys, as_json)
    assert ran.code == 0, f"exit 0: exit {ran.code}\n{ran.out}{ran.err}"
    assert fake.calls == [OWNER_ID], f"A called once, for the picked account: {fake.calls}"
    assert recorded_owner(root) == (OWNER_ID, "link_only"), f"the new outcome recorded: {recorded_owner(root)}"
    said_lines = text_of(ran, as_json).splitlines()
    assert [line for line in expected if line not in said_lines] == [], f"the lines of the new outcome are said: {text_of(ran, as_json)}"
    assert LINK_CANARY not in ran.out + ran.err + caplog.text and "reset-password" not in ran.out + ran.err, "no link in any stream or log"
    print_success(f"via {via}: recovered")


def test_the_link_only_line_sends_to_the_instance_log_and_prints_no_link(capsys):
    """(g) R13: the ``link_only`` line of ``_print_owner_outcome`` is one ⚠️ line that says the account is set, no email
    could be sent and the link is in the instance log: no link, path or token, even when the state object still carries
    an ``owner_reset_path`` attribute (a stale one is never read)."""
    capsys.readouterr()
    backup_cli._print_owner_outcome(SimpleNamespace(owner_user_id=OWNER_ID, owner_outcome="link_only", owner_reset_path=LINK_CANARY))
    out = capsys.readouterr().out
    lines = [line for line in out.splitlines() if line.strip()]
    assert len(lines) == 1 and lines[0].startswith("⚠️") and "log" in lines[0].lower(), f"[new] R13: one ⚠️ line that names the instance log: {out!r}"
    assert LINK_CANARY not in out and "reset-password" not in out, f"no link, no path: {out!r}"
    print_success("link_only: one ⚠️ line, the log, no link")


@pytest.mark.parametrize("outcome", ["already_issued", "already_done"])
def test_the_outcomes_a_no_longer_answers_are_not_said_as_a_success(capsys, outcome):
    """(g) R13: ``already_issued`` and ``already_done`` are gone from A: a state that still records one (never written by
    this LibreFolio) is not reported as an account that is set — it falls in the generic ❌ line."""
    capsys.readouterr()
    backup_cli._print_owner_outcome(SimpleNamespace(owner_user_id=OWNER_ID, owner_outcome=outcome))
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert len(lines) == 1 and lines[0].startswith("❌"), f"[new] R13: {outcome} is no known outcome: {lines}"
    print_success(f"{outcome}: not a success")


def test_recover_owner_drops_a_stale_link_key_from_the_state(tmp_path, monkeypatch, capsys, caplog):
    """(g) R13: a state of an older LibreFolio that still holds ``owner_reset_path``: after ``--recover owner`` the file has
    no such key and the old link is in no stream and no log line."""
    root = instance(tmp_path, monkeypatch)
    owner_state()(monkeypatch, root)
    with_stale_link(root)
    wire(monkeypatch, FakeA(outcome=Outcome.SENT))
    ran = run_owner(capsys, False)
    assert ran.code == 0, f"exit 0: exit {ran.code}\n{ran.out}{ran.err}"
    assert recorded_owner(root) == (OWNER_ID, "sent"), f"recorded, the stale key and its link gone: {recorded_owner(root)}"
    assert LINK_CANARY not in ran.out + ran.err + caplog.text, "the old link is in no stream and no log"
    print_success("stale link dropped")


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
def test_recover_owner_says_the_new_error_and_exits_5_when_a_refuses_again(tmp_path, monkeypatch, capsys, as_json):
    """(g) §9.2: A refuses again (another code): the new ``error:<CODE>`` is recorded, exit 5 ``owner_assignment_failed``,
    a ❌ line with the code and no ✅ line; the snapshot offers ``owner`` again, still without the code."""
    root = instance(tmp_path, monkeypatch)
    owner_state(code=FAILED_CODE)(monkeypatch, root)
    fake = FakeA(raises=FakeOwnerAssignmentError(OTHER_CODE))
    wire(monkeypatch, fake)
    ran = run_owner(capsys, as_json)
    assert ran.code == 5, f"exit 5: exit {ran.code}\n{ran.out}{ran.err}"
    assert fake.calls == [OWNER_ID], f"A called once: {fake.calls}"
    assert recorded_owner(root) == (OWNER_ID, f"error:{OTHER_CODE}"), f"the new code recorded: {recorded_owner(root)}"
    said_lines = text_of(ran, as_json).splitlines()
    failed = [line for line in said_lines if line.startswith("❌")]
    assert failed and OTHER_CODE in " ".join(failed) and not any(line.startswith("✅") for line in said_lines), f"a ❌ line with the code, no ✅: {ran.out}{ran.err}"
    if as_json:
        line = the_line(ran)
        assert (line["state"], line["reason"], line["choices"], line["recover"], line["error"]) == ("committed", "owner_assignment", ["owner"], {"choice": "owner", "done": False}, "owner_assignment_failed"), f"the line: {line}"
        never_in(ran, OTHER_CODE, FAILED_CODE, str(OWNER_ID), OWNER_EMAIL)
    print_success("refused again: exit 5")


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
def test_recover_owner_can_be_run_again_after_a_new_failure(tmp_path, monkeypatch, capsys, as_json):
    """(g) §9.2: after exit 5 the same state offers ``owner`` again: a second run, A answering now, exits 0."""
    root = instance(tmp_path, monkeypatch)
    owner_state()(monkeypatch, root)
    with monkeypatch.context() as first:
        wire(first, FakeA(raises=FakeOwnerAssignmentError(OTHER_CODE)))
        assert run_owner(capsys, as_json).code == 5, "precondition: the first run fails again"
    fake = FakeA(outcome=Outcome.SENT)
    wire(monkeypatch, fake)
    ran = run_owner(capsys, as_json)
    assert ran.code == 0 and fake.calls == [OWNER_ID], f"the second run assigns the owner: exit {ran.code}, {fake.calls}\n{ran.out}{ran.err}"
    assert recorded_owner(root) == (OWNER_ID, "sent"), f"sent: {recorded_owner(root)}"
    print_success("fail then succeed")


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
@pytest.mark.parametrize("missing", ["a-missing", "a-transient-failure"])
def test_recover_owner_says_it_is_set_at_the_next_start_when_nothing_is_recorded(tmp_path, monkeypatch, capsys, missing, as_json):
    """(g) §9.2: A's function missing (``ImportError``) or failing with something that is not its refusal: no outcome is
    recorded, exit 0, a ⏳ line (the account is set at the next start), no ❌ line; the outcome stays cleared and the
    snapshot offers nothing."""
    root = instance(tmp_path, monkeypatch)
    owner_state()(monkeypatch, root)
    with_stale_link(root)
    wired = wire(monkeypatch, None if missing == "a-missing" else FakeA(raises=RuntimeError("b51c transient failure text")))
    expected = outcome_lines(capsys, None)
    ran = run_owner(capsys, as_json)
    assert ran.code == 0, f"exit 0: exit {ran.code}\n{ran.out}{ran.err}"
    assert wired.lookups == ["_assign_owner"], f"A's function looked up once, through owner._assign_owner: {wired.lookups}"
    assert recorded_owner(root) == (OWNER_ID, None), f"nothing recorded, the old outcome and a stale link gone: {recorded_owner(root)}"
    said_lines = text_of(ran, as_json).splitlines()
    assert [line for line in expected if line not in said_lines] == [] and any(line.startswith("⏳") for line in said_lines), f"the ⏳ line: {ran.out}{ran.err}"
    assert not any(line.startswith("❌") for line in said_lines), f"not a failure: {ran.out}{ran.err}"
    if as_json:
        line = the_line(ran)
        assert (line["state"], line["reason"], line["choices"], line["recover"]) == ("committed", None, [], {"choice": "owner", "done": True}), f"the line: {line}"
        assert "error" not in line, f"no error: {line}"
    print_success(f"{missing}: exit 0, pending")


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
def test_recover_owner_while_a_server_serves_clears_the_outcome_and_calls_nothing(tmp_path, monkeypatch, capsys, as_json):
    """(g) §9.2: a server serves the data directory: the outcome is cleared and nothing else changes (the file has no
    ``owner_reset_path`` key before nor after), A's function is not even looked up, exit 0 and one ✅ line saying the
    account is set when LibreFolio starts again."""
    root = instance(tmp_path, monkeypatch)
    owner_state()(monkeypatch, root)
    wired = wire(monkeypatch, FakeA(outcome=Outcome.SENT))
    before = json.loads(base.state_path(root).read_text(encoding="utf-8"))
    with serving(root):
        ran = run_owner(capsys, as_json)
    assert ran.code == 0, f"exit 0: exit {ran.code}\n{ran.out}{ran.err}"
    assert (wired.lookups, wired.fake.calls) == ([], []), f"a running server only retries at its start: A not reached: {wired.lookups}, {wired.fake.calls}"
    after = json.loads(base.state_path(root).read_text(encoding="utf-8"))
    assert "owner_reset_path" not in before and "owner_reset_path" not in after, f"no owner_reset_path key before nor after: {sorted(before)} / {sorted(after)}"
    assert after["owner_outcome"] is None, f"cleared: {after}"
    assert {key: value for key, value in after.items() if key != "owner_outcome"} == {key: value for key, value in before.items() if key != "owner_outcome"}, "nothing else changed"
    said_lines = text_of(ran, as_json).splitlines()
    done = [line for line in said_lines if line.startswith("✅")]
    assert len(done) == 1 and "start" in done[0].lower() and not any(line.startswith("❌") for line in said_lines), f"one ✅ line about the next start: {ran.out}{ran.err}"
    if as_json:
        line = the_line(ran)
        assert (line["state"], line["reason"], line["choices"], line["recover"]) == ("committed", None, [], {"choice": "owner", "done": True}), f"the line: {line}"
        never_in(ran, LINK_CANARY, str(OWNER_ID), FAILED_CODE)
    print_success("served: cleared, A not called")


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
def test_recover_owner_while_the_owner_lock_is_held_is_exit_5_restore_in_use(tmp_path, monkeypatch, capsys, as_json):
    """(g) §9.2: another process holds ``.restore/owner.lock``: exit 5 ``restore_in_use``, a ❌ line (naming it), no ✅ line,
    the state byte for byte, A not reached; the snapshot still offers ``owner``."""
    root = instance(tmp_path, monkeypatch)
    owner_state()(monkeypatch, root)
    wired = wire(monkeypatch, FakeA(outcome=Outcome.SENT))
    with owner_lock_held(root):
        before = base.everything(root)
        ran = run_owner(capsys, as_json)
        after = base.everything(root)
    assert ran.code == 5, f"exit 5: exit {ran.code}\n{ran.out}{ran.err}"
    assert after == before, "the state and the folder as they were"
    assert (wired.lookups, wired.fake.calls) == ([], []), f"A not reached: {wired.lookups}"
    said_lines = text_of(ran, as_json).splitlines()
    failed = [line for line in said_lines if line.startswith("❌")]
    assert failed and "restore_in_use" in " ".join(failed) and not any(line.startswith("✅") for line in said_lines), f"a ❌ line with restore_in_use: {ran.out}{ran.err}"
    if as_json:
        line = the_line(ran)
        assert (line["state"], line["reason"], line["choices"], line["recover"], line["error"]) == ("committed", "owner_assignment", ["owner"], {"choice": "owner", "done": False}, "restore_in_use"), f"the line: {line}"
    print_success("owner lock held: exit 5")


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
@pytest.mark.parametrize(
    ("raised", "code", "error"),
    [
        pytest.param("not-failed", 3, "nothing_to_recover", id="reset-meanwhile"),
        pytest.param("oserror", 5, "failed", id="oserror"),
        pytest.param("path", 5, "failed", id="backup-path-error"),
    ],
)
def test_recover_owner_maps_what_the_reset_raises(tmp_path, monkeypatch, capsys, raised, code, error, as_json):
    """(g) §9.2: ``RestoreOwnerNotFailedError`` (someone reset it meanwhile): exit 3 ``nothing_to_recover``;
    ``OSError`` or ``BackupPathError``: exit 5 ``failed``. A ❌ line, no ✅ line, A not reached, nothing claimed done."""
    apply = importlib.import_module(APPLY_MODULE)
    paths = importlib.import_module("backend.app.services.platform.instance_backup.paths")
    root = instance(tmp_path, monkeypatch)
    owner_state()(monkeypatch, root)
    wired = wire(monkeypatch, FakeA(outcome=Outcome.SENT))
    errors = {
        "not-failed": lambda: getattr(apply, "RestoreOwnerNotFailedError", None) and apply.RestoreOwnerNotFailedError("someone reset it"),
        "oserror": lambda: OSError(errno.EIO, os.strerror(errno.EIO)),
        "path": lambda: paths.BackupPathError(root),
    }
    error_to_raise = errors[raised]()
    assert error_to_raise is not None, "[new] B5-1b §9.1: apply.RestoreOwnerNotFailedError does not exist yet"

    def refused(*args: Any, **kwargs: Any) -> bool:
        raise error_to_raise

    monkeypatch.setattr(apply, "reset_owner_assignment", refused, raising=False)
    before = base.everything(root)
    ran = run_owner(capsys, as_json)
    assert ran.code == code, f"{raised}: exit {code}, not {ran.code}\n{ran.out}{ran.err}"
    said_lines = text_of(ran, as_json).splitlines()
    assert any(line.startswith("❌") for line in said_lines) and not any(line.startswith("✅") for line in said_lines), f"a ❌ line, no ✅: {ran.out}{ran.err}"
    assert (wired.lookups, wired.fake.calls) == ([], []), f"A not reached: {wired.lookups}"
    assert base.everything(root) == before, "nothing changed"
    if as_json:
        line = the_line(ran)
        assert (line["recover"], line["error"]) == ({"choice": "owner", "done": False}, error), f"recover not done, error {error}: {line}"
    print_success(f"{raised}: exit {code}")


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
@pytest.mark.parametrize("path", ["served", "assigned"])
def test_a_second_recover_owner_finds_a_state_that_does_not_offer_it(tmp_path, monkeypatch, capsys, path, as_json):
    """(g) §9.2 idempotence: once the outcome is cleared (a server served) or replaced (A answered) the state offers no
    ``owner``: the second run is exit 4 ``choice_not_valid`` and changes nothing, A is not called again."""
    root = instance(tmp_path, monkeypatch)
    owner_state()(monkeypatch, root)
    fake = FakeA(outcome=Outcome.SENT)
    wire(monkeypatch, fake)
    with serving(root) if path == "served" else nullcontext():
        assert run_owner(capsys, as_json).code == 0, "precondition: the first run is done"
    calls = list(fake.calls)
    after_first = base.everything(root)
    second = run_owner(capsys, as_json)
    assert second.code == 4, f"the second run: exit 4, not {second.code}\n{second.out}{second.err}"
    assert base.everything(root) == after_first and fake.calls == calls, "the second run changed nothing and called nothing"
    if as_json:
        assert the_line(second)["error"] == NOT_VALID, f"choice_not_valid: {second.out}"
    print_success(f"{path}: second run exit 4")


# --- --json: one line that names nothing, no log line on standard output -----------

#: How each scenario of ``--recover owner --json`` is set up: the fake, whether a server serves or the lock is held, and
#: what the line must say happened (barrier: the recovery really ran, so that "names nothing" is not true of a refusal).
SCENARIOS = [
    pytest.param(FakeA(outcome=Outcome.SENT), "free", True, None, id="sent"),
    pytest.param(FakeA(outcome=Outcome.LINK_ONLY), "free", True, None, id="link_only"),
    pytest.param(FakeA(raises=FakeOwnerAssignmentError(OTHER_CODE)), "free", False, "owner_assignment_failed", id="refused-again"),
    pytest.param(FakeA(outcome=Outcome.SENT), "served", True, None, id="served"),
    pytest.param(FakeA(outcome=Outcome.SENT), "locked", False, "restore_in_use", id="locked"),
]


@pytest.mark.parametrize(("fake", "where", "done", "error"), SCENARIOS)
def test_recover_owner_json_is_one_line_that_names_nothing(tmp_path, monkeypatch, capsys, fake, where, done, error):
    """(g) §9.2: whatever happened, standard output is the one line, whose keys are the usual ones plus ``recover`` (and
    ``error``), and it holds none of the owner's id, address, link, either code, the administrator, the stage or the data
    directory."""
    monkeypatch.setenv("LIBREFOLIO_ADMIN_EMAIL", OWNER_EMAIL)
    root = instance(tmp_path, monkeypatch, CANARY_FOLDER)
    owner_state(confirmed_by=CANARY_USER, stage_id=CANARY_STAGE)(monkeypatch, root)
    with_stale_link(root)
    wire(monkeypatch, FakeA(outcome=fake.outcome, raises=fake.raises))
    with serving(root) if where == "served" else owner_lock_held(root) if where == "locked" else nullcontext():
        ran = run_owner(capsys, True)
    line = the_line(ran)
    assert line.get("recover") == {"choice": "owner", "done": done} and line.get("error") == error, f"barrier: the recovery ran as the scenario says (done {done}, error {error}): {line}"
    assert set(line) <= KEYS | {"recover", "error"} and KEYS <= set(line), f"the usual keys, recover and error: {line}"
    never_in(ran, *CANARIES, str(OWNER_ID), OWNER_EMAIL, LINK_CANARY, "reset-password", FAILED_CODE, OTHER_CODE, "owner_user_id", "owner_reset_path")
    assert os.fspath(root) not in ran.out, "no path on standard output"
    print_success(f"{where}: one line, names nothing")


def test_log_lines_of_the_owner_recovery_never_reach_standard_output(tmp_path, monkeypatch, capsys):
    """(g) §9.2: the reset and the step log (the reset one line, the step one more); a logging handler writing to standard
    output must not put them before the line: with ``--json`` standard output is that one line alone."""
    root = instance(tmp_path, monkeypatch)
    owner_state()(monkeypatch, root)
    wire(monkeypatch, FakeA(outcome=Outcome.SENT))
    other = cli.make_data_dir(tmp_path / "other")
    base.unreadable_as(monkeypatch, other, "invalid")
    with logs_to_stdout() as handler:
        # Control: this handler would show the log line of a module on standard output.
        base.apply_module().restore_state_problem(other)
        control = capsys.readouterr().out
        assert handler.messages and control, f"precondition: a module's log line reaches this handler's standard output: {handler.messages}: {control!r}"
        seen = len(handler.messages)
        ran = run_owner(capsys, True)
    line = the_line(ran)
    assert ran.code == 0 and line["recover"]["done"] is True, f"exit 0, done: {ran.out}"
    assert len(handler.messages) > seen, f"barrier: the recovery logged (the reset's line), so the check proves something: {handler.messages}"
    print_success("no log line on standard output")

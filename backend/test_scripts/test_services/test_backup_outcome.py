"""
The outcome of a restore read with a one-time ticket instead of a session (workstream B, lot B5c): the new module
``instance_backup/outcome.py``, the names ``paths.py`` gains for its file, and ``RestoreOutcome`` of
``backend/app/schemas/backup.py``. Selector: ``services backup-outcome``.

Written RED, before B5c. ``outcome.py``, ``paths.OUTCOME_TICKET_FILE`` and ``paths.outcome_ticket_path``, and
``RestoreOutcome`` are looked up by the test that needs them (``outcome_module``, ``new_name``), never imported at the
top: the file collects without them, and each test fails on its own, saying what is missing ("[new] …").

Why a ticket. ``POST /backup/restore/restart`` stops the server; the start that follows applies the restore and ends every
session (decision 40). The page that asked for the restart must still learn how it ended — committed, rolled back, still
waiting — with no session left, and on an instance its hosting provider blocked as well. The restart's answer carries a
ticket for that read, and only that answer: ``.restore`` keeps its hash, and ``.restore`` is never swapped, so the ticket
outlives the restart, the swap, the commit and a rollback (``test_backup_apply.py`` (n) follows it through them).

(a) The layout and the models. ``.restore/outcome-ticket.json`` (``OUTCOME_TICKET_FILE``, ``outcome_ticket_path``), beside
    the restore's state. ``OUTCOME_TICKET_TTL``: one hour. ``OutcomeTicket`` is frozen and holds its five fields, nothing
    else: ``format`` 1, ``sha256`` 64 lowercase hexadecimal digits, ``stage_id`` a stage id (``RestoreState``'s pattern),
    ``issued_at``, ``expires_at``. ``RestoreOutcome``: ``state`` (pending, in_progress, committed, rolled_back),
    ``reason`` (the four reasons of a rollback, or null), ``waiting`` (the four reasons a restore waits,
    ``instance_blocked`` included, or null), nothing else.
(b) ``issue_ticket(stage_id, *, data_dir, now)``: a ticket of 43 URL-safe characters (``secrets.token_urlsafe(32)``), a
    new one at each call. Its file holds the SHA-256 of the ticket in hex, never the ticket, with the stage id,
    ``issued_at`` = ``now`` and ``expires_at`` an hour later; 0600, ``.restore`` still 0700; written beside then renamed,
    nothing else left in ``.restore``; a link in place of the file is replaced, never written through, dangling or not.
    ``.restore`` a link or a file: ``BackupPathError`` naming it, nothing written anywhere. A stage id that is not one:
    refused, nothing written. A second ticket replaces the first, which no longer opens anything.
(c) ``read_outcome(ticket, state, *, data_dir, now)``: the ``RestoreOutcome`` of ``state`` for the ticket of its stage —
    ``applying``, ``applied`` and ``rolling_back`` are ``in_progress``, ``reason`` and ``waiting`` as recorded — while
    ``now < expires_at``. ``None`` for anything else, the same ``None`` whatever the case: no ticket, an empty or malformed
    one (not 43 URL-safe characters), no file, a file that cannot be read or is not a ticket (an extra key, a folder, a
    link: never followed), another ticket (the hashes compared in constant time), an expired one (at ``expires_at``
    already, a final outcome too; its file removed), no restore, a restore of another stage. A ticket that does not open
    the outcome never removes it: the route has no session, anyone may present one, and the right ticket still reads
    after it; an expired ticket's file goes only when its own ticket presents it. One restore, one ticket, not one read
    (decision N53): every outcome, a final one (``committed``, ``rolled_back``) included, keeps the file and gives the
    same answer at every read until ``expires_at`` — a final answer lost on the way (a connection reset at the start) is
    read again, rather than the page falling back on a session the restore ended. One ticket follows its restore from
    ``pending`` to its commit, and reads it again after. The ticket goes when a new restart replaces it (b), a new
    confirmation or a cancel removes it (``test_backup_apply.py`` (n)), or its holder presents it expired. B-41:
    ``state`` may also be a reader of it, a function of no argument, as the route gives one: called once, and only for
    the ticket that opens — once its form, ``.restore``, its file, the hashes and its expiry have let it through — never
    for any other (none, malformed, another, expired, no file, a file not to be trusted, ``.restore`` a link or a file).
(d) ``drop_ticket(*, data_dir)``: the file removed, nothing else; without one, nothing done and nothing created; it never
    raises (a file that cannot be removed is logged, as a warning or an error) and removes nothing through a link, in
    place of ``.restore`` or of the file.
(e) Neither a ticket nor its hash is ever logged — issued, replaced, read (right, wrong, malformed, of another stage,
    expired, final and read again), dropped, or presented to a file that cannot be used (B-42: an error, then a line at
    debug) — in a structlog event or a stdlib record.
(f) Without ``data_dir`` and ``now``: the configured data directory and the clock.
(g) B-42, a ticket's file that cannot be used, which anyone reaches without a session with any well-formed ticket:
    unreadable (an ``OSError``: a link in its place, opened without following it; mode 000; ``os.open`` refusing it),
    over 4096 bytes, or not an ``OutcomeTicket``. However often it is read, it is one error, then nothing louder than
    debug while the same failure — the same event and the same ``error`` — lasts. It is an error again once the file is
    written (``issue_ticket``), read whole and valid, removed (``drop_ticket``) or found missing by a read, each alone;
    and when it fails in another way, a return to the first failure included. Each data directory remembers its own: two
    with the same failure, one error each. The answers never change: ``None``.

How. Pure: every data directory under ``tmp_path``, its ``.restore`` made as ``ensure_private_dir`` makes it. The
restore's state is a ``RestoreState`` built in the test as a start leaves it: ``read_outcome`` reads only the state it is
given. The ticket file is always the product's, but where a case needs one the product never writes (an extra key, a
folder, a link). A ticket's file that cannot be used (g) is the test's own as well: its bytes, a link, mode 000 (never
as root), or ``os.open`` refusing that one path (EIO), every other path handed to the real one. The process's
configured data directory is a folder of the test that must stay absent (``configured_data_dir`` of the staging tests,
imported, autouse), but in (f), where it is the test's instance. ``now`` is given everywhere but in (f). Logs are read
with ``structlog.testing.capture_logs`` and pytest's ``caplog``, each behind a barrier: a canary through a logger of
``outcome``'s name must reach it. Modes and links are POSIX-only. No database, no server, no network.
"""

from __future__ import annotations

import ast
import errno
import hashlib
import importlib
import inspect
import json
import logging
import os
import re
import secrets
import stat
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError
from structlog.testing import capture_logs

from backend.app.logging_config import get_logger
from backend.app.services.platform.instance_backup import paths
from backend.app.services.platform.instance_backup.apply import Boot, RestoreState, SwapEntry
from backend.app.services.platform.instance_backup.paths import SWAPPED_FOLDERS, BackupPathError, ensure_private_dir, restore_dir, restore_state_path
from backend.test_scripts.test_services import test_backup_staging as cases
from backend.test_scripts.test_utils import print_section, print_success

# Autouse: the production data directory of this process is a folder of the test that must stay absent.
configured_data_dir = cases.configured_data_dir

POSIX = os.name != "nt"
AS_ROOT = POSIX and os.geteuid() == 0
pytestmark = pytest.mark.skipif(not POSIX, reason="modes and links are POSIX only")

OUTCOME = "backend.app.services.platform.instance_backup.outcome"
SCHEMAS = "backend.app.schemas.backup"
#: The ticket's file, spelled out here: a rename in paths.py would strand the tickets of the restarts in flight.
TICKET_FILE_NAME = "outcome-ticket.json"
TTL = timedelta(hours=1)
#: What ``secrets.token_urlsafe(32)`` gives: 32 random bytes in URL-safe base64, without padding.
A_TICKET = re.compile(r"[A-Za-z0-9_-]{43}")
TICKET_FIELDS = {"format", "sha256", "stage_id", "issued_at", "expires_at"}
OUTCOME_FIELDS = {"state", "reason", "waiting"}
OUTCOME_STATES = {"pending", "in_progress", "committed", "rolled_back"}
STAGE = "0123456789abcdef0123456789abcdef"
OTHER_STAGE = "fedcba9876543210fedcba9876543210"
#: A ticket as a client holds one, for the cases that only need its hash.
SOME_TICKET = "Zm9yIHRoZSBtb2RlbCBvZiB0aGUgZmlsZSBvbmx5Lg"
#: The times of a restore, its restart and its read: the ticket is read half-way through its hour, but where its expiry
#: is the subject.
CONFIRMED_AT = datetime(2026, 10, 16, 14, 55, tzinfo=UTC)
BACKUP_CREATED_AT = datetime(2026, 10, 14, 9, 0, tzinfo=UTC)
ISSUED_AT = datetime(2026, 10, 16, 15, 0, tzinfo=UTC)
APPLIED_AT = ISSUED_AT + timedelta(minutes=2)
FINISHED_AT = ISSUED_AT + timedelta(minutes=3)
READ_AT = ISSUED_AT + TTL / 2
#: Every phase of a restore, and the state of the outcome it reads as.
OUTCOME_OF = {"pending": "pending", "applying": "in_progress", "applied": "in_progress", "rolling_back": "in_progress", "committed": "committed", "rolled_back": "rolled_back"}
PHASES = tuple(OUTCOME_OF)
FINAL = ("committed", "rolled_back")
NOT_FINAL = ("pending", "applying", "applied", "rolling_back")
WAIT_REASONS = ("backup_running", "other_data_directory", "server_running", "instance_blocked")
ROLLBACK_REASONS = ("first_start_failed", "swap_interrupted", "swap_failed", "stage_missing")
#: Not a stage id: a ticket is issued for a stage of ``.restore/stage/`` only, never for a path.
NOT_STAGE_IDS = ["", "../" + "0" * 29, STAGE.upper(), STAGE[:31], STAGE + "0", STAGE + "\n"]
LOG_CANARY = "b5c outcome test: canary through a logger of outcome's name"
#: A field removed from a record.
ABSENT = object()


# =============================================================================
# The product, looked up when a test needs it
# =============================================================================


def outcome_module() -> Any:
    """``instance_backup.outcome``, imported by the test that needs it: its absence is that test's red, not a collection
    error of the whole file."""
    try:
        return importlib.import_module(OUTCOME)
    except ModuleNotFoundError as exc:
        if exc.name != OUTCOME:
            raise
        pytest.fail(f"[new] {OUTCOME} does not exist yet: lot B5c brings it")


def new_name(module: Any, name: str) -> Any:
    """A name lot B5c adds to ``module``, looked up by the test that needs it."""
    value = getattr(module, name, None)
    assert value is not None, f"[new] {module.__name__}.{name} does not exist yet: lot B5c adds it"
    return value


def ticket_file(root: Path) -> Path:
    """``.restore/outcome-ticket.json`` of the data directory ``root``, as ``paths.outcome_ticket_path`` gives it."""
    return new_name(paths, "outcome_ticket_path")(root)


def outcome_model() -> Any:
    """``RestoreOutcome`` of ``schemas/backup.py``: what ``read_outcome`` returns, and the route answers."""
    return new_name(importlib.import_module(SCHEMAS), "RestoreOutcome")


def issued(root: Path, stage_id: str = STAGE, *, now: datetime = ISSUED_AT) -> str:
    """A ticket issued for the restore of ``stage_id`` in ``root`` at ``now``, as the restart issues it."""
    return outcome_module().issue_ticket(stage_id, data_dir=root, now=now)


def opened(ticket: str | None, state: RestoreState | Callable[[], RestoreState | None] | None, root: Path, *, now: datetime = READ_AT) -> Any:
    """What ``ticket`` opens in ``root`` at ``now`` for the restore ``state`` — or, B-41, for the state its reader
    returns: half-way through its hour, unless said."""
    return outcome_module().read_outcome(ticket, state, data_dir=root, now=now)


def drop(root: Path) -> Any:
    return outcome_module().drop_ticket(data_dir=root)


# =============================================================================
# Data directories, states, records
# =============================================================================


def hash_of(ticket: str) -> str:
    """What the ticket's file keeps of it: its SHA-256, in hexadecimal."""
    return hashlib.sha256(ticket.encode("ascii")).hexdigest()


def mode(path: Path) -> int:
    return stat.S_IMODE(path.lstat().st_mode)


def moment(value: str) -> datetime:
    return datetime.fromisoformat(value)


def an_instance(tmp_path: Path, name: str = "instance") -> Path:
    """A data directory of the test, its ``.restore`` private, as the confirmation of a restore leaves it."""
    root = tmp_path / name
    root.mkdir()
    ensure_private_dir(restore_dir(root), root)
    return root


def contents(folder: Path) -> dict[str, tuple]:
    """Everything below ``folder``, links never followed: a folder with its mode, a link with its target, a file with its
    mode and bytes. ``{}`` where no plain folder stands."""
    found: dict[str, tuple] = {}
    pending = [folder] if paths.is_plain_dir(folder) else []
    while pending:
        current = pending.pop()
        for path in current.iterdir():
            info = path.lstat()
            name = path.relative_to(folder).as_posix()
            if stat.S_ISLNK(info.st_mode):
                found[name] = ("link", os.readlink(path))
            elif stat.S_ISDIR(info.st_mode):
                found[name] = ("folder", stat.S_IMODE(info.st_mode))
                pending.append(path)
            else:
                found[name] = ("file", stat.S_IMODE(info.st_mode), path.read_bytes())
    return dict(sorted(found.items()))


def restore_in(root: Path, phase: str, *, stage_id: str = STAGE, **changes: Any) -> RestoreState:
    """The restore of ``stage_id`` in ``phase``, its state as a start leaves it (and ``changes``): ``read_outcome`` is
    given it, as the route gives it what ``apply.read_restore`` reads."""
    fields: dict[str, Any] = {}
    if phase in ("applying", "applied", "rolling_back"):
        fields["swap"] = [SwapEntry(name=name, live=True, staged=True) for name in SWAPPED_FOLDERS]
        fields["boot"] = Boot(pid=999_999, started=1_760_000_000.0)
    if phase in ("applied", "committed"):
        fields["applied_at"] = APPLIED_AT
    if phase in ("rolling_back", "rolled_back"):
        fields["reason"] = "first_start_failed"
    if phase in FINAL:
        fields["finished_at"] = FINISHED_AT
    if phase == "committed":
        fields["session_version"] = int(FINISHED_AT.timestamp() * 1000)
    fields.update(changes)
    return RestoreState(status=phase, stage_id=stage_id, data_dir=str(root.resolve()), confirmed_at=CONFIRMED_AT, confirmed_by="b5c-admin", backup_created_at=BACKUP_CREATED_AT, backup_app_version="v1.2.0", action="same", **fields)


def outcome_of(state: RestoreState) -> dict[str, Any]:
    """The outcome of ``state`` as the contract says it: the state of an outcome, its reason, why it waits."""
    return {"state": OUTCOME_OF[state.status], "reason": state.reason, "waiting": state.waiting}


def shown(outcome: Any) -> dict[str, Any] | None:
    """An outcome as the route answers it, ``None`` as ``None``: what an assertion compares and a failure shows."""
    return None if outcome is None else outcome.model_dump()


def with_changes(record: dict[str, Any], changes: dict[str, Any]) -> dict[str, Any]:
    """``record`` with ``changes``: a value replaced or added, ``ABSENT`` removing the field."""
    changed = dict(record)
    for name, value in changes.items():
        if value is ABSENT:
            changed.pop(name, None)
        else:
            changed[name] = value
    return changed


def a_record(**changes: Any) -> dict[str, Any]:
    """The fields of a ticket's file for ``SOME_TICKET``, as ``OutcomeTicket`` takes them, with ``changes``."""
    return with_changes({"format": 1, "sha256": hash_of(SOME_TICKET), "stage_id": STAGE, "issued_at": ISSUED_AT, "expires_at": ISSUED_AT + TTL}, changes)


def rewrite(path: Path, **changes: Any) -> None:
    """The ticket's file at ``path`` written again as JSON, with ``changes``: a file the product never writes."""
    path.write_text(json.dumps(with_changes(json.loads(path.read_bytes()), changes)), encoding="utf-8")


def values_of(schema: dict[str, Any], definitions: dict[str, Any]) -> set[Any]:
    """The values a property of a JSON schema allows, through a ``$ref`` into ``definitions``; ``None`` among them when it
    is nullable."""
    values: set[Any] = set()
    for option in schema.get("anyOf", [schema]):
        allowed = definitions[option["$ref"].rsplit("/", 1)[-1]] if "$ref" in option else option
        values |= set(allowed.get("enum", [allowed["const"]] if "const" in allowed else []))
        if allowed.get("type") == "null":
            values.add(None)
    return values


def called_names(module: Any) -> set[str]:
    """The names of every function ``module`` calls, as its source says: ``hmac.compare_digest(...)`` is
    ``compare_digest``."""
    names: set[str] = set()
    for node in ast.walk(ast.parse(inspect.getsource(module))):
        if isinstance(node, ast.Call):
            names.add(node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", ""))
    return names


# =============================================================================
# Logs
# =============================================================================


@contextmanager
def logs_of_outcome(caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch) -> Iterator[list[dict[str, Any]]]:
    """What is logged inside the block: the structlog events (yielded) and the stdlib records (``caplog.records``), each
    behind a barrier — a canary through a logger of ``outcome``'s name must reach it, or "nothing leaked" would prove
    nothing."""
    monkeypatch.setattr(logging.getLogger(OUTCOME), "disabled", False)
    caplog.set_level(logging.DEBUG)
    caplog.set_level(logging.DEBUG, logger=OUTCOME)
    with capture_logs() as events:
        get_logger(OUTCOME).warning(LOG_CANARY)
        logging.getLogger(OUTCOME).warning(LOG_CANARY)
        assert any(event.get("event") == LOG_CANARY for event in events), f"barrier: a structlog logger of {OUTCOME} does not reach capture_logs: {events}"
        assert any(record.name == OUTCOME and record.getMessage() == LOG_CANARY for record in caplog.records), f"barrier: a stdlib logger of {OUTCOME} does not reach caplog"
        yield events


def leaked(events: list[dict[str, Any]], records: list[logging.LogRecord], hidden: list[str]) -> list[str]:
    """Every event and record that carries one of ``hidden``, shown, so that a failure names the leak."""
    found = [repr(event) for event in events if any(text in repr(event) for text in hidden)]
    found += [f"{record.name}: {record.getMessage()}" for record in records if any(text in record.getMessage() or text in repr(vars(record)) for text in hidden)]
    return found


def warned(events: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """What was logged in the block as a warning or worse, the canary left out: (level, message)."""
    return [(str(event.get("log_level")), str(event.get("event"))) for event in events if event.get("event") != LOG_CANARY and event.get("log_level") in ("warning", "error", "critical")]


def lines(events: list[dict[str, Any]]) -> list[tuple[str, str, Any]]:
    """Every line logged in the block, the canary left out — (level, message, ``error``) — for a failure to show."""
    return [(str(event.get("log_level")), str(event.get("event")), event.get("error")) for event in events if event.get("event") != LOG_CANARY]


# =============================================================================
# A ticket's file that cannot be used (B-42)
# =============================================================================

#: B-42: what ``read_outcome`` logs for a ticket's file it cannot use, by failure — spelled out: these are the words an
#: administrator looks for in the log.
TICKET_CANNOT_BE_READ = "The restore outcome ticket cannot be read"
TICKET_NOT_WRITTEN_HERE = "The restore outcome ticket is not one this LibreFolio wrote: it is ignored"
TICKET_NOT_READABLE = "The restore outcome ticket is not one this LibreFolio can read: it is ignored"
#: B-42: the most of a ticket's file ever read: one byte more, and it is not one this LibreFolio wrote.
MAX_TICKET_FILE_BYTES = 4096
#: B-42: the one way of breaking the file that is ``os.open``'s, not the disk's.
REFUSED = "refused-EIO"


def a_ticket_s_file() -> bytes:
    """A valid ticket's file for ``SOME_TICKET``, as ``issue_ticket`` writes one, but written by the test: what a broken
    file is made from, and a file a read finds whole and valid with nothing issued (B-42)."""
    return new_name(outcome_module(), "OutcomeTicket").model_validate(a_record()).model_dump_json(indent=2).encode("utf-8") + b"\n"


def _not_an_outcome_ticket(path: Path, pointed: Path) -> None:
    path.write_bytes(b"{not a ticket")


def _past_4096_bytes(path: Path, pointed: Path) -> None:
    """A valid ticket's file padded past 4096 bytes: whole, it would read as valid; it is never read past its limit."""
    path.write_bytes(a_ticket_s_file() + b" " * MAX_TICKET_FILE_BYTES)


def _a_link_to_a_ticket_s_file(path: Path, pointed: Path) -> None:
    """A link in its place to a valid ticket's file elsewhere: opened without following it (ELOOP)."""
    pointed.write_bytes(a_ticket_s_file())
    path.symlink_to(pointed)


def _of_mode_000(path: Path, pointed: Path) -> None:
    """A valid ticket's file nobody may read: the file system refuses it (EACCES); root reads it all the same."""
    path.write_bytes(a_ticket_s_file())
    path.chmod(0o000)


def _refused_to_a_reader(path: Path, pointed: Path) -> None:
    """A valid ticket's file, which ``os.open`` refuses to a reader (EIO): ``BrokenTicketFile`` refuses it."""
    path.write_bytes(a_ticket_s_file())


#: B-42: each way a ticket's file cannot be used: what makes it so, and what ``read_outcome`` logs for it. The same event
#: with another ``error`` — a link (ELOOP), mode 000 (EACCES), an EIO — is another failure.
BREAKING = {
    "not-a-ticket": (_not_an_outcome_ticket, TICKET_NOT_READABLE),
    "over-4096-bytes": (_past_4096_bytes, TICKET_NOT_WRITTEN_HERE),
    "a-link": (_a_link_to_a_ticket_s_file, TICKET_CANNOT_BE_READ),
    "mode-000": (_of_mode_000, TICKET_CANNOT_BE_READ),
    REFUSED: (_refused_to_a_reader, TICKET_CANNOT_BE_READ),
}
#: B-42: the ways, as the tests take them: root reads a file of mode 000 all the same.
BROKEN_WAYS = [pytest.param(way, id=way, marks=pytest.mark.skipif(AS_ROOT and way == "mode-000", reason="root reads a file of mode 000 all the same")) for way in BREAKING]
#: B-42: a way for each event ``read_outcome`` logs for the file, wherever the tests run.
EVERY_FAILURE = ("not-a-ticket", "over-4096-bytes", "a-link", REFUSED)


class BrokenTicketFile:
    """B-42: the ticket's file of the data directory ``root``, broken in one way of ``BREAKING`` each time the test says
    so (``now``), whatever stood there (removed, a link never followed). ``refused-EIO`` is ``os.open`` refusing that one
    path to anyone (EIO), every other path handed to the real one, until ``mend`` or the next ``now``; every other way
    lies on disk, and what the product writes next replaces it."""

    def __init__(self, root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self.root = root
        self.pointed = root.parent / f"{root.name}-pointed.json"
        self.refusing = False
        target = os.path.realpath(ticket_file(root))
        real_open = os.open

        def opening(path: Any, flags: int, mode: int = 0o777, *, dir_fd: int | None = None) -> int:
            if self.refusing and dir_fd is None and os.path.realpath(path) == target:
                raise OSError(errno.EIO, os.strerror(errno.EIO))
            return real_open(path, flags, mode, dir_fd=dir_fd)

        monkeypatch.setattr(os, "open", opening)

    def now(self, way: str) -> str:
        """The ticket's file broken in ``way`` from now on: what ``read_outcome`` logs for it."""
        make, failure = BREAKING[way]
        self.refusing = False
        path = ticket_file(self.root)
        path.unlink(missing_ok=True)
        make(path, self.pointed)
        self.refusing = way == REFUSED
        return failure

    def mend(self) -> None:
        """``os.open`` lets the file be read again; what lies on disk is left as it is."""
        self.refusing = False


# =============================================================================
# (a) The layout and the models
# =============================================================================


def test_the_ticket_lives_in_restore_beside_the_state_of_the_restore(tmp_path):
    """(a) ``.restore/outcome-ticket.json``: in the restore's own folder, which no restore swaps, beside ``restore.json``.
    A path, nothing created to say it."""
    print_section("(a) The ticket's file and the models")
    root = tmp_path / "instance"
    assert new_name(paths, "OUTCOME_TICKET_FILE") == TICKET_FILE_NAME, f"the ticket's file: {paths.OUTCOME_TICKET_FILE!r}"
    path = ticket_file(root)
    assert path == restore_dir(root) / TICKET_FILE_NAME == restore_state_path(root).with_name(TICKET_FILE_NAME), f"beside the state of the restore, in .restore: {path}"
    assert restore_dir(root).name not in SWAPPED_FOLDERS, "precondition: .restore is never swapped, so the ticket outlives the swap"
    assert not root.exists(), "a path: nothing created"
    print_success(f".restore/{TICKET_FILE_NAME}")


def test_a_ticket_lives_one_hour():
    """(a) ``OUTCOME_TICKET_TTL``: one hour from the restart's request, a constant, no variable."""
    assert new_name(outcome_module(), "OUTCOME_TICKET_TTL") == TTL, f"one hour: {outcome_module().OUTCOME_TICKET_TTL}"
    print_success("one hour")


def test_the_ticket_s_file_is_a_frozen_outcome_ticket_of_five_fields():
    """(a) ``OutcomeTicket``: ``format`` 1 (by default), the hash, the stage, two times; frozen."""
    model = new_name(outcome_module(), "OutcomeTicket")
    ticket = model.model_validate(a_record())
    assert ticket.model_dump() == a_record(), f"the five fields, as given: {ticket.model_dump()}"
    assert model.model_validate(a_record(format=ABSENT)).format == 1, "format 1 when the file does not say it"
    with pytest.raises((ValidationError, TypeError, AttributeError)):
        ticket.stage_id = OTHER_STAGE
    assert ticket.stage_id == STAGE, "frozen: the stage is the one read"
    print_success("OutcomeTicket: format, sha256, stage_id, issued_at, expires_at; frozen")


#: A record that is not the file of a ticket: a field more, a field missing, a hash or a stage id that is not one.
NOT_A_TICKET_RECORD = [
    pytest.param({"note": "a field more"}, id="an-extra-key"),
    pytest.param({"format": 2}, id="format-2"),
    pytest.param({"sha256": ABSENT}, id="no-hash"),
    pytest.param({"sha256": hash_of(SOME_TICKET).upper()}, id="hash-uppercase"),
    pytest.param({"sha256": hash_of(SOME_TICKET)[:63]}, id="hash-of-63-digits"),
    pytest.param({"sha256": hash_of(SOME_TICKET) + "0"}, id="hash-of-65-digits"),
    pytest.param({"sha256": hash_of(SOME_TICKET) + "\n"}, id="hash-and-a-line-feed"),
    pytest.param({"sha256": "g" * 64}, id="hash-not-hexadecimal"),
    pytest.param({"stage_id": "../" + "0" * 29}, id="stage-id-a-path"),
    pytest.param({"stage_id": STAGE.upper()}, id="stage-id-uppercase"),
    pytest.param({"stage_id": STAGE + "\n"}, id="stage-id-and-a-line-feed"),
    pytest.param({"issued_at": ABSENT}, id="no-issued-at"),
    pytest.param({"expires_at": ABSENT}, id="no-expires-at"),
]


@pytest.mark.parametrize("changes", NOT_A_TICKET_RECORD)
def test_anything_but_the_five_fields_of_a_ticket_s_file_is_refused(changes):
    """(a) ``extra="forbid"``; ``sha256`` 64 lowercase hexadecimal digits; ``stage_id`` the stage id pattern of
    ``RestoreState`` (a line feed after it included, as (c) of the API's tests pins it for the state)."""
    model = new_name(outcome_module(), "OutcomeTicket")
    with pytest.raises(ValidationError):
        model.model_validate(a_record(**changes))
    print_success(f"refused: {changes}")


def test_an_outcome_says_its_state_why_it_rolled_back_and_why_it_waits_nothing_more():
    """(a) ``RestoreOutcome``, the route's answer: no name, no date, no version, no path; ``none`` is not an outcome."""
    schema = outcome_model().model_json_schema()
    properties = schema["properties"]
    assert set(properties) == OUTCOME_FIELDS, f"state, reason, waiting, and nothing else: {sorted(properties)}"
    allowed = {name: values_of(properties[name], schema.get("$defs", {})) for name in sorted(OUTCOME_FIELDS)}
    expected = {"reason": {*ROLLBACK_REASONS, None}, "state": OUTCOME_STATES, "waiting": {*WAIT_REASONS, None}}
    assert allowed == expected, f"the values of each field: {allowed}"
    print_success("RestoreOutcome: state, reason, waiting")


# =============================================================================
# (b) issue_ticket
# =============================================================================


def test_a_ticket_is_43_url_safe_characters_and_its_file_holds_its_hash_never_the_ticket(tmp_path):
    """(b) What the restart's answer carries, and what ``.restore`` keeps of it: the hash, the stage, issued now, an hour
    to live; 0600; written beside then renamed, nothing else left; nothing written outside ``.restore``."""
    print_section("(b) issue_ticket")
    root = an_instance(tmp_path)
    ticket = issued(root)
    assert isinstance(ticket, str) and A_TICKET.fullmatch(ticket), f"43 URL-safe characters, as secrets.token_urlsafe(32) gives them: {len(ticket)} characters"
    path = ticket_file(root)
    assert path.is_file() and not path.is_symlink() and mode(path) == 0o600, f"a file of its owner only: {oct(mode(path))}"
    raw = path.read_bytes()
    assert ticket.encode("ascii") not in raw, "the file never holds the ticket"
    record = json.loads(raw)
    assert set(record) == TICKET_FIELDS, f"the five fields, nothing else: {sorted(record)}"
    found = (record["format"], record["sha256"], record["stage_id"], moment(record["issued_at"]), moment(record["expires_at"]))
    assert found == (1, hash_of(ticket), STAGE, ISSUED_AT, ISSUED_AT + TTL), f"its SHA-256, its stage, issued now, expiring an hour later: {found}"
    model = new_name(outcome_module(), "OutcomeTicket")
    assert model.model_validate_json(raw) == model.model_validate(a_record(sha256=hash_of(ticket))), "the file reads back as an OutcomeTicket"
    assert list(contents(restore_dir(root))) == [TICKET_FILE_NAME], f"written beside then renamed: nothing else left in .restore: {list(contents(restore_dir(root)))}"
    assert mode(restore_dir(root)) == 0o700 and list(contents(root)) == [".restore", f".restore/{TICKET_FILE_NAME}"], "nothing written outside .restore, which stays private"
    print_success(f"{len(ticket)} characters; the file: its hash, {STAGE}, an hour")


def test_each_call_issues_a_new_ticket_and_the_file_holds_the_last(tmp_path):
    """(b) A new ticket at each restart; the file keeps the hash of the last one only."""
    root = an_instance(tmp_path)
    tickets = [issued(root, now=ISSUED_AT + timedelta(seconds=n)) for n in range(8)]
    assert len(set(tickets)) == len(tickets) and all(A_TICKET.fullmatch(ticket) for ticket in tickets), f"eight tickets, all different: {len(set(tickets))}"
    assert json.loads(ticket_file(root).read_bytes())["sha256"] == hash_of(tickets[-1]), "the file holds the last ticket's hash"
    print_success("8 restarts, 8 tickets, the last one kept")


@pytest.mark.parametrize("second_stage", [STAGE, OTHER_STAGE], ids=["for-the-same-stage", "for-another-stage"])
def test_a_second_ticket_replaces_the_first_which_no_longer_opens_anything(tmp_path, second_stage):
    """(b) A second restart, of the same restore or after another one was confirmed: one ticket at a time, the last."""
    root = an_instance(tmp_path)
    first = issued(root)
    second = issued(root, second_stage, now=ISSUED_AT + timedelta(minutes=1))
    record = json.loads(ticket_file(root).read_bytes())
    assert (record["sha256"], record["stage_id"]) == (hash_of(second), second_stage), f"the file is the second ticket's: {record}"
    state = restore_in(root, "pending", stage_id=second_stage)
    assert opened(first, state, root) is None, "the first ticket opens nothing any more"
    assert shown(opened(second, state, root)) == outcome_of(state), "the second does"
    print_success(f"{second_stage}: the second ticket replaces the first")


@pytest.mark.parametrize("pointed", ["a-file", "nothing"], ids=["a-link-to-a-file", "a-dangling-link"])
def test_a_link_in_place_of_the_file_is_replaced_and_never_written_through(tmp_path, pointed):
    """(b) Written beside without following a link, then renamed over the name: a link there is replaced, what it points
    to never written, nor created when it does not exist."""
    root = an_instance(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    target = elsewhere / "pointed.json"
    if pointed == "a-file":
        target.write_bytes(b"a file a link points to\n")
    ticket_file(root).symlink_to(target)
    before = contents(elsewhere)
    ticket = issued(root)
    path = ticket_file(root)
    assert path.is_file() and not path.is_symlink(), "the link replaced by the ticket's file"
    assert contents(elsewhere) == before, f"nothing written through the link: {sorted(contents(elsewhere))}"
    assert shown(opened(ticket, restore_in(root, "pending"), root)) == outcome_of(restore_in(root, "pending")), "the ticket opens its outcome"
    print_success(f"{pointed}: replaced, never written through")


def _restore_a_link(root: Path, elsewhere: Path) -> None:
    restore_dir(root).symlink_to(elsewhere, target_is_directory=True)


def _restore_a_file(root: Path, elsewhere: Path) -> None:
    restore_dir(root).write_bytes(b"a file where the restore's folder should be")


@pytest.mark.parametrize("make", [_restore_a_link, _restore_a_file], ids=["a-link", "a-file"])
def test_a_restore_folder_that_is_not_a_plain_folder_is_refused_and_nothing_is_written(tmp_path, make):
    """(b) ``.restore`` a link (to a folder) or a file: ``BackupPathError`` naming it; nothing written where the link
    points, nor anywhere in the data directory."""
    root = tmp_path / "instance"
    root.mkdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    make(root, elsewhere)
    before = (contents(root), contents(elsewhere))
    with pytest.raises(BackupPathError) as raised:
        issued(root)
    assert raised.value.path == restore_dir(root), f"the error names .restore: {raised.value.path}"
    assert (contents(root), contents(elsewhere)) == before, "nothing written, through the link or anywhere else"
    print_success(f"{make.__name__}: BackupPathError, nothing written")


@pytest.mark.parametrize("value", NOT_STAGE_IDS)
def test_a_ticket_is_issued_for_a_stage_id_and_nothing_else(tmp_path, value):
    """(b) The stage id of ``RestoreState``'s pattern only: anything else is refused (a ``ValueError``, the model's
    ``ValidationError`` included) and nothing is written."""
    root = an_instance(tmp_path)
    with pytest.raises(ValueError):
        issued(root, value)
    assert contents(restore_dir(root)) == {}, f"{value!r}: nothing written"
    print_success(f"{value!r}: refused")


# =============================================================================
# (c) read_outcome
# =============================================================================


@pytest.mark.parametrize("phase", PHASES)
def test_the_ticket_of_a_restore_opens_its_outcome_in_each_phase(tmp_path, phase):
    """(c) A ``RestoreOutcome``: ``applying``, ``applied`` and ``rolling_back`` are ``in_progress``; the reason and why it
    waits as the state records them."""
    print_section("(c) read_outcome")
    root = an_instance(tmp_path)
    state = restore_in(root, phase)
    ticket = issued(root)
    outcome = opened(ticket, state, root)
    assert isinstance(outcome, outcome_model()), f"{phase}: a RestoreOutcome: {outcome!r}"
    assert outcome.model_dump() == outcome_of(state), f"{phase}: {outcome.model_dump()}"
    print_success(f"{phase} → {outcome.state}")


@pytest.mark.parametrize("waiting", WAIT_REASONS)
def test_the_outcome_of_a_restore_a_start_left_waiting_says_why(tmp_path, waiting):
    """(c) ``pending`` with its reason: a backup running, another data directory, another server process, or the
    hosting provider's block (§11) — what the page shows after a restart that applied nothing."""
    root = an_instance(tmp_path)
    state = restore_in(root, "pending", waiting=waiting)
    assert shown(opened(issued(root), state, root)) == {"state": "pending", "reason": None, "waiting": waiting}, f"pending, waiting {waiting}"
    print_success(f"pending, {waiting}")


@pytest.mark.parametrize("reason", ROLLBACK_REASONS)
def test_the_outcome_of_a_restore_rolled_back_says_why(tmp_path, reason):
    root = an_instance(tmp_path)
    state = restore_in(root, "rolled_back", reason=reason)
    assert shown(opened(issued(root), state, root)) == {"state": "rolled_back", "reason": reason, "waiting": None}, f"rolled back, {reason}"
    print_success(f"rolled_back, {reason}")


def _a_character_changed(ticket: str) -> str:
    return ticket[:-1] + ("A" if ticket[-1] != "A" else "B")


#: What a client may present instead of the ticket: nothing, a malformed one, another one, the file's own hash.
NOT_THE_TICKET: list[Any] = [
    pytest.param(lambda ticket: None, id="no-ticket"),
    pytest.param(lambda ticket: "", id="empty"),
    pytest.param(lambda ticket: " " * 43, id="43-spaces"),
    pytest.param(lambda ticket: ticket[:-1], id="a-character-short"),
    pytest.param(lambda ticket: ticket + "A", id="a-character-more"),
    pytest.param(lambda ticket: ticket[:-1] + "+", id="standard-base64-plus"),
    pytest.param(lambda ticket: ticket[:-1] + "/", id="standard-base64-slash"),
    pytest.param(lambda ticket: ticket + "=", id="padded"),
    pytest.param(lambda ticket: " " + ticket, id="a-space-before"),
    pytest.param(lambda ticket: ticket + "\n", id="a-line-feed-after"),
    pytest.param(lambda ticket: "é" * 43, id="43-characters-not-ascii"),
    pytest.param(hash_of, id="its-hash"),
    pytest.param(_a_character_changed, id="a-character-changed"),
    pytest.param(lambda ticket: secrets.token_urlsafe(32), id="another-ticket"),
]


@pytest.mark.parametrize("present", NOT_THE_TICKET)
def test_what_is_not_the_ticket_opens_nothing_and_never_removes_it(tmp_path, present):
    """(c) ``None``, and the file as it was: the route has no session, so anyone may present anything, and nothing but
    the ticket itself does anything with its file. On a committed restore, the outcome the page waits for most: the right
    ticket still reads it after them."""
    root = an_instance(tmp_path)
    state = restore_in(root, "committed")
    ticket = issued(root)
    before = ticket_file(root).read_bytes()
    presented = present(ticket)
    assert presented != ticket, "precondition: not the ticket"
    assert opened(presented, state, root) is None, f"{presented!r}: opens nothing"
    assert ticket_file(root).read_bytes() == before, "the file as it was"
    assert shown(opened(ticket, state, root)) == outcome_of(state), "the ticket itself still opens the outcome"
    print_success("None, the outcome left for its ticket")


def _not_json(path: Path, ticket: str, elsewhere: Path) -> None:
    path.write_bytes(b"{not a ticket")


def _empty_file(path: Path, ticket: str, elsewhere: Path) -> None:
    path.write_bytes(b"")


def _not_text(path: Path, ticket: str, elsewhere: Path) -> None:
    path.write_bytes(b"\xff\xfe\x00 not text at all")


def _a_list(path: Path, ticket: str, elsewhere: Path) -> None:
    path.write_bytes(b"[]")


def _an_extra_key(path: Path, ticket: str, elsewhere: Path) -> None:
    rewrite(path, note="a field more")


def _no_expiry(path: Path, ticket: str, elsewhere: Path) -> None:
    rewrite(path, expires_at=ABSENT)


def _format_2(path: Path, ticket: str, elsewhere: Path) -> None:
    rewrite(path, format=2)


def _hash_uppercase(path: Path, ticket: str, elsewhere: Path) -> None:
    rewrite(path, sha256=hash_of(ticket).upper())


def _stage_id_a_path(path: Path, ticket: str, elsewhere: Path) -> None:
    rewrite(path, stage_id="../" + "0" * 29)


def _a_folder(path: Path, ticket: str, elsewhere: Path) -> None:
    path.unlink()
    path.mkdir()


def _a_link(path: Path, ticket: str, elsewhere: Path) -> None:
    """The ticket's own valid file moved out of ``.restore``, a link to it in its place: followed, it would open."""
    target = elsewhere / TICKET_FILE_NAME
    path.rename(target)
    path.symlink_to(target)


#: A ticket's file that cannot be trusted, the right ticket presented: unreadable, not a ticket, or a link.
UNTRUSTED_FILES = [
    pytest.param(_not_json, id="not-json"),
    pytest.param(_empty_file, id="empty"),
    pytest.param(_not_text, id="not-text"),
    pytest.param(_a_list, id="a-list"),
    pytest.param(_an_extra_key, id="an-extra-key"),
    pytest.param(_no_expiry, id="no-expiry"),
    pytest.param(_format_2, id="format-2"),
    pytest.param(_hash_uppercase, id="hash-uppercase"),
    pytest.param(_stage_id_a_path, id="stage-id-a-path"),
    pytest.param(_a_folder, id="a-folder"),
    pytest.param(_a_link, id="a-link-to-the-valid-file"),
]


@pytest.mark.parametrize("spoil", UNTRUSTED_FILES)
def test_a_file_that_cannot_be_trusted_opens_nothing_and_a_link_is_never_followed(tmp_path, spoil):
    """(c) ``None`` for the right ticket and the right restore: the file is read only as a plain file, read whole and
    valid as an ``OutcomeTicket``. What a link points to is neither read (it would open) nor changed."""
    root = an_instance(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    state = restore_in(root, "pending")
    ticket = issued(root)
    spoil(ticket_file(root), ticket, elsewhere)
    pointed = contents(elsewhere)
    assert opened(ticket, state, root) is None, f"{spoil.__name__}: opens nothing"
    assert contents(elsewhere) == pointed, f"{spoil.__name__}: nothing changed where a link points"
    print_success(f"{spoil.__name__}: None")


@pytest.mark.parametrize("restore_folder", [True, False], ids=["no-ticket-file", "no-restore-folder"])
def test_without_a_ticket_file_nothing_opens_and_nothing_is_created(tmp_path, restore_folder):
    """(c) A well-formed ticket and a restore, but no file (a restart from the command line issues none): ``None``; a
    read creates nothing, not even ``.restore``."""
    root = an_instance(tmp_path) if restore_folder else tmp_path / "instance"
    root.mkdir(exist_ok=True)
    before = contents(root)
    assert opened(secrets.token_urlsafe(32), restore_in(root, "pending"), root) is None, "no file: nothing opens"
    assert contents(root) == before, "nothing created"
    print_success("no file: None, nothing created")


#: When the ticket is read, after its issue; whether it still opens. ``now >= expires_at`` is expired.
EXPIRY = [
    pytest.param("pending", TTL - timedelta(microseconds=1), True, id="a-microsecond-before-expires-at"),
    pytest.param("pending", TTL, False, id="at-expires-at"),
    pytest.param("pending", TTL + timedelta(days=1), False, id="a-day-later"),
    pytest.param("committed", TTL - timedelta(microseconds=1), True, id="a-final-outcome-a-microsecond-before-expires-at"),
    pytest.param("committed", TTL, False, id="a-final-outcome-at-expires-at"),
]


@pytest.mark.parametrize(("phase", "after", "opens"), EXPIRY)
def test_a_ticket_expires_at_its_expires_at_and_its_file_is_removed(tmp_path, phase, after, opens):
    """(c) An hour after the restart, at that very instant already, the ticket opens nothing, a final outcome neither, and
    the read that finds it expired removes its file. Until then it opens, and keeps its file: a final outcome too (N53)."""
    root = an_instance(tmp_path)
    state = restore_in(root, phase)
    ticket = issued(root)
    outcome = opened(ticket, state, root, now=ISSUED_AT + after)
    if opens:
        assert shown(outcome) == outcome_of(state) and ticket_file(root).is_file(), f"{phase}, before expires_at: the outcome, the file kept: {shown(outcome)}, file {ticket_file(root).is_file()}"
        print_success(f"{phase}, a microsecond before: opens, kept")
        return
    assert outcome is None, f"{after} after its issue: expired, opens nothing: {shown(outcome)}"
    assert not os.path.lexists(ticket_file(root)), "the expired ticket's file is removed"
    assert opened(ticket, state, root, now=ISSUED_AT) is None, "gone: nothing opens any more, whatever the time"
    print_success(f"{phase}, {after} after: expired, file removed")


@pytest.mark.parametrize("found", ["no-restore", "a-restore-of-another-stage"])
def test_a_ticket_opens_the_outcome_of_its_own_stage_only(tmp_path, found):
    """(c) The ticket names the stage of the restore it was issued for: without a restore (``apply.read_restore`` found
    none, or none it can read), or with another one, it opens nothing. The control first: it opens its own."""
    root = an_instance(tmp_path)
    ticket = issued(root)
    own = restore_in(root, "pending")
    assert shown(opened(ticket, own, root)) == outcome_of(own), "control: the ticket opens the outcome of its own stage"
    state = None if found == "no-restore" else restore_in(root, "committed", stage_id=OTHER_STAGE)
    assert opened(ticket, state, root) is None, f"{found}: opens nothing"
    print_success(f"{found}: None")


@pytest.mark.parametrize("phase", FINAL)
def test_a_final_outcome_reads_the_same_until_its_ticket_expires(tmp_path, phase):
    """(c) Decision N53, one restore, one ticket — not one read: the outcome the page waits for most is not used up by
    its first read, which a connection reset at the start may lose. The same answer at every read, the file as it was,
    up to a microsecond before ``expires_at``; at ``expires_at`` the ticket opens nothing and its file goes, and it opens
    nothing after, whatever the time asked."""
    root = an_instance(tmp_path)
    state = restore_in(root, phase)
    ticket = issued(root)
    before = ticket_file(root).read_bytes()
    moments = [READ_AT, READ_AT, READ_AT + timedelta(minutes=5), ISSUED_AT + TTL - timedelta(microseconds=1)]
    reads = [(shown(opened(ticket, state, root, now=moment)), os.path.lexists(ticket_file(root))) for moment in moments]
    assert reads == [(outcome_of(state), True)] * len(moments), f"{phase}: the same outcome at every read until its expiry, the file kept after each: {reads}"
    assert ticket_file(root).read_bytes() == before, f"{phase}: the file as it was: a read does not use the ticket up"
    assert opened(ticket, state, root, now=ISSUED_AT + TTL) is None, f"{phase}: at expires_at the ticket opens nothing"
    assert not os.path.lexists(ticket_file(root)), f"{phase}: the expired ticket's file goes when its holder presents it"
    assert opened(ticket, state, root, now=READ_AT) is None, f"{phase}: gone: nothing opens any more, whatever the time"
    print_success(f"{phase}: read {len(moments)} times until its expiry, then gone")


@pytest.mark.parametrize("phase", NOT_FINAL)
def test_an_outcome_not_final_yet_reads_again_and_keeps_its_file(tmp_path, phase):
    """(c) ``pending`` and ``in_progress`` are not the end: the page reads again, the file as it was."""
    root = an_instance(tmp_path)
    state = restore_in(root, phase)
    ticket = issued(root)
    before = ticket_file(root).read_bytes()
    reads = [shown(opened(ticket, state, root, now=READ_AT + timedelta(minutes=n))) for n in range(3)]
    assert reads == [outcome_of(state)] * 3, f"{phase}: the same outcome at each read: {reads}"
    assert ticket_file(root).read_bytes() == before, f"{phase}: the file as it was"
    print_success(f"{phase}: read three times, kept")


def test_one_ticket_follows_its_restore_from_pending_to_its_commit(tmp_path):
    """(c) The ticket is issued while the restore waits; the start applies it, then commits it: the same ticket answers at
    each step, and ``committed`` again after (N53), its file kept for a page that lost the first answer."""
    root = an_instance(tmp_path)
    ticket = issued(root)
    steps = ("pending", "applying", "applied", "committed", "committed")
    seen = [shown(opened(ticket, restore_in(root, phase), root, now=ISSUED_AT + timedelta(minutes=minute))) for minute, phase in enumerate(steps, start=1)]
    assert seen == [outcome_of(restore_in(root, phase)) for phase in steps], f"pending, in progress twice, committed twice: {seen}"
    assert ticket_file(root).is_file(), "committed and read twice: the ticket's file is still there until it expires"
    print_success("pending → in_progress → in_progress → committed → committed")


def test_an_expired_ticket_goes_only_when_its_own_holder_presents_it(tmp_path):
    """(c) Expired, the ticket's file stays until its own ticket is presented: none, a malformed one, its hash or another
    ticket, at or after ``expires_at``, open nothing and remove nothing — nobody without the ticket can remove it. Then
    the ticket itself, expired: nothing, and its file goes."""
    root = an_instance(tmp_path)
    state = restore_in(root, "committed")
    ticket = issued(root)
    before = ticket_file(root).read_bytes()
    expired_at = ISSUED_AT + TTL
    others = [None, "", ticket[:-1], hash_of(ticket), secrets.token_urlsafe(32)]
    assert [opened(other, state, root, now=moment) for other in others for moment in (expired_at, expired_at + TTL)] == [None] * (2 * len(others)), "expired, nothing opens"
    assert ticket_file(root).read_bytes() == before, "the file as it was: only its own ticket removes it"
    assert opened(ticket, state, root, now=expired_at) is None and not os.path.lexists(ticket_file(root)), "its own ticket, expired: nothing, and the file goes"
    print_success("expired: removed by its own ticket only")


def test_the_hashes_are_compared_in_constant_time():
    """(c) The hash of the presented ticket is compared with the file's by ``hmac.compare_digest`` (``secrets`` gives the
    same): a comparison that stops at the first difference tells, by its time, how much of a guess is right."""
    names = called_names(outcome_module())
    assert "compare_digest" in names, f"[new] outcome.py compares the hashes with compare_digest: it calls {sorted(name for name in names if name)}"
    print_success("compare_digest")


# (c) B-41: the state read for the ticket that opens, and for it only.


def a_reader(state: RestoreState | None, calls: list[RestoreState | None]) -> Callable[[], RestoreState | None]:
    """B-41: a reader of the restore's state, as the route gives one to ``read_outcome`` in place of the state: a function
    of no argument that returns ``state``. It records each call in ``calls`` and never raises: a call is seen even where
    the caller would swallow what it raised."""

    def read() -> RestoreState | None:
        calls.append(state)
        return state

    return read


@pytest.mark.parametrize("found", ["its-own-restore", "no-restore", "a-restore-of-another-stage"])
def test_the_state_may_be_a_reader_called_once_for_the_ticket_that_opens(tmp_path, found):
    """(c) B-41: ``state`` may be a function of no argument that reads it, as the route gives it, so that the restore's
    state is read for the ticket that opens, and for it only. For that ticket the reader is called exactly once, and the
    outcome is that of the state it returns: ``pending`` for its own restore; ``None`` for no restore, or one of another
    stage.

    RED until B-41's code: ``read_outcome`` takes the reader for a state (``'function' object has no attribute
    'stage_id'``)."""
    print_section("(c) B-41: the state read for the ticket that opens, and for it only")
    root = an_instance(tmp_path)
    ticket = issued(root)
    own = restore_in(root, "pending")
    state = {"its-own-restore": own, "no-restore": None, "a-restore-of-another-stage": restore_in(root, "pending", stage_id=OTHER_STAGE)}[found]
    calls: list[RestoreState | None] = []
    outcome = opened(ticket, a_reader(state, calls), root)
    assert len(calls) == 1, f"{found}: the reader of the state called exactly once: {len(calls)} calls"
    expected = outcome_of(own) if found == "its-own-restore" else None
    assert shown(outcome) == expected, f"{found}: the outcome of the state it read: {shown(outcome)}"
    print_success(f"{found}: read once → {shown(outcome)}")


@pytest.mark.parametrize("present", NOT_THE_TICKET)
def test_what_is_not_the_ticket_never_calls_the_reader_of_the_state(tmp_path, present):
    """(c) B-41, a GUARD: green before the code, and it must stay so. None, an empty or malformed ticket, its hash,
    another one — whatever a caller without the ticket may present — opens nothing, and the reader of the state is never
    called. The reader records every call and never raises: a call swallowed would still be seen (that it records one is
    the red test's own assertion)."""
    root = an_instance(tmp_path)
    ticket = issued(root)
    presented = present(ticket)
    assert presented != ticket, "precondition: not the ticket"
    calls: list[RestoreState | None] = []
    assert opened(presented, a_reader(restore_in(root, "committed"), calls), root) is None, f"{presented!r}: opens nothing"
    assert calls == [], f"{presented!r}: the reader of the state never called: {len(calls)} calls"
    print_success("None, the state never read")


@pytest.mark.parametrize("spoil", UNTRUSTED_FILES)
def test_a_ticket_s_file_that_cannot_be_trusted_never_calls_the_reader_of_the_state(tmp_path, spoil):
    """(c) B-41, a GUARD: the right ticket, its file not one to trust — not a ticket, a key more, a folder, a link in its
    place —: nothing opens, and the reader of the state is never called."""
    root = an_instance(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    ticket = issued(root)
    spoil(ticket_file(root), ticket, elsewhere)
    calls: list[RestoreState | None] = []
    assert opened(ticket, a_reader(restore_in(root, "pending"), calls), root) is None, f"{spoil.__name__}: opens nothing"
    assert calls == [], f"{spoil.__name__}: the reader of the state never called: {len(calls)} calls"
    print_success(f"{spoil.__name__}: None, the state never read")


def _without_its_file(root: Path, elsewhere: Path) -> None:
    """``.restore`` without the ticket's file: a restart from the command line issues none."""
    ensure_private_dir(restore_dir(root), root)


def _without_restore(root: Path, elsewhere: Path) -> None:
    """Nothing: the data directory of an instance that never restored anything."""


#: B-41: no ticket's file to be found in the data directory: none, no ``.restore``, or ``.restore`` a link (to the folder
#: of the presented ticket's valid file: followed, it would open) or a file (the builders of (b)).
NO_TICKET_S_FILE = [
    pytest.param(_without_its_file, id="no-ticket-file"),
    pytest.param(_without_restore, id="no-restore-folder"),
    pytest.param(_restore_a_link, id="restore-a-link"),
    pytest.param(_restore_a_file, id="restore-a-file"),
]


@pytest.mark.parametrize("make", NO_TICKET_S_FILE)
def test_without_a_ticket_s_file_the_reader_of_the_state_is_never_called(tmp_path, make):
    """(c) B-41, a GUARD: a well-formed ticket whose valid file is in another data directory's ``.restore``, and here no
    file to read: none, no ``.restore``, ``.restore`` a link to that folder (never followed: it would open) or a file.
    Nothing opens, and the reader of the state is never called."""
    elsewhere = an_instance(tmp_path, "elsewhere")
    ticket = issued(elsewhere)
    root = tmp_path / "instance"
    root.mkdir()
    make(root, restore_dir(elsewhere))
    calls: list[RestoreState | None] = []
    assert opened(ticket, a_reader(restore_in(root, "pending"), calls), root) is None, f"{make.__name__}: opens nothing"
    assert calls == [], f"{make.__name__}: the reader of the state never called: {len(calls)} calls"
    print_success(f"{make.__name__}: None, the state never read")


#: B-41: the ticket's own file, expired: the cases of ``EXPIRY`` where it opens nothing.
EXPIRED = [pytest.param(*case.values[:2], id=case.id, marks=case.marks) for case in EXPIRY if not case.values[2]]


@pytest.mark.parametrize(("phase", "after"), EXPIRED)
def test_an_expired_ticket_never_calls_the_reader_of_the_state_and_its_file_goes(tmp_path, phase, after):
    """(c) B-41, a GUARD: the right ticket, at its ``expires_at`` or after: nothing opens, a final outcome neither, and
    the reader of the state is never called; the expired ticket's file is removed, as before."""
    root = an_instance(tmp_path)
    ticket = issued(root)
    calls: list[RestoreState | None] = []
    assert opened(ticket, a_reader(restore_in(root, phase), calls), root, now=ISSUED_AT + after) is None, f"{phase}, {after} after its issue: expired, opens nothing"
    assert calls == [], f"{phase}, {after} after its issue: the reader of the state never called: {len(calls)} calls"
    assert not os.path.lexists(ticket_file(root)), f"{phase}, {after} after its issue: the expired ticket's file is removed, as before"
    print_success(f"{phase}, {after} after: None, the state never read, the file removed")


# =============================================================================
# (d) drop_ticket
# =============================================================================


def test_drop_ticket_removes_the_ticket_and_nothing_else(tmp_path):
    """(d) What a new confirmation and a cancel do (``apply.confirm_restore``, ``apply.cancel_restore``): the file goes,
    the rest of ``.restore`` stays; the ticket opens nothing any more."""
    print_section("(d) drop_ticket")
    root = an_instance(tmp_path)
    restore_state_path(root).write_bytes(b"the state of a restore, left as it is")
    ticket = issued(root)
    before = {name: value for name, value in contents(root).items() if name != f".restore/{TICKET_FILE_NAME}"}
    assert drop(root) is None, "drop_ticket returns nothing"
    assert contents(root) == before, f"the ticket's file removed, nothing else: {sorted(contents(root))}"
    assert opened(ticket, restore_in(root, "pending"), root) is None, "the ticket opens nothing any more"
    print_success("dropped")


def _no_ticket_file(root: Path) -> None:
    ensure_private_dir(restore_dir(root), root)


def _no_restore_folder(root: Path) -> None:
    """Nothing: the data directory of an instance that never restored anything."""


def _restore_folder_a_file(root: Path) -> None:
    restore_dir(root).write_bytes(b"a file where the restore's folder should be")


@pytest.mark.parametrize("make", [_no_ticket_file, _no_restore_folder, _restore_folder_a_file], ids=["no-ticket-file", "no-restore-folder", "restore-a-file"])
def test_drop_ticket_without_a_ticket_does_nothing_creates_nothing_and_does_not_raise(tmp_path, make):
    """(d) A confirmation or a cancel without a restart before them (the command line's): nothing to drop, nothing
    created, not even ``.restore``; never a refusal."""
    root = tmp_path / "instance"
    root.mkdir()
    make(root)
    before = contents(root)
    drop(root)
    assert contents(root) == before, f"{make.__name__}: nothing done, nothing created"
    print_success(f"{make.__name__}: nothing")


def test_drop_ticket_never_removes_anything_through_a_link_in_place_of_restore(tmp_path):
    """(d) ``.restore`` a link to a folder holding a file of the ticket's name: left there, as every restore's write and
    removal refuses to go through a link."""
    root = tmp_path / "instance"
    root.mkdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / TICKET_FILE_NAME).write_bytes(b"a file of the link's target")
    restore_dir(root).symlink_to(elsewhere, target_is_directory=True)
    before = (contents(root), contents(elsewhere))
    drop(root)
    assert (contents(root), contents(elsewhere)) == before, "nothing removed through the link"
    print_success(".restore a link: nothing removed")


def test_drop_ticket_never_removes_what_a_link_in_place_of_the_file_points_to(tmp_path):
    """(d) The file a link: what it points to stays as it is."""
    root = an_instance(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    target = elsewhere / "pointed.json"
    target.write_bytes(b"a file a link points to\n")
    ticket_file(root).symlink_to(target)
    drop(root)
    assert contents(elsewhere) == {"pointed.json": ("file", mode(target), b"a file a link points to\n")}, "what the link points to is left as it is"
    print_success("the file a link: its target kept")


@pytest.mark.skipif(AS_ROOT, reason="root removes files from a folder it cannot write")
def test_a_ticket_that_cannot_be_removed_is_logged_and_drop_ticket_does_not_raise(tmp_path, caplog, monkeypatch):
    """(d) ``.restore`` that cannot be written (0500): the file stays, a warning or an error says so, and the caller — a
    confirmation, a cancel — goes on. Neither the ticket nor its hash in what is logged."""
    root = an_instance(tmp_path)
    ticket = issued(root)
    restore_dir(root).chmod(0o500)
    try:
        with logs_of_outcome(caplog, monkeypatch) as events:
            try:
                drop(root)
            except Exception as exc:  # the contract: drop_ticket never raises; say so rather than show a traceback
                pytest.fail(f"drop_ticket raised: {type(exc).__name__}: {exc}")
    finally:
        restore_dir(root).chmod(0o700)
    assert ticket_file(root).is_file(), "precondition: the file could not be removed"
    assert warned(events) != [], f"the failure is logged, as a warning or an error: {events}"
    assert leaked(events, caplog.records, [ticket, hash_of(ticket)]) == [], "neither the ticket nor its hash in the logs"
    print_success(f"not removed, logged: {warned(events)}")


# =============================================================================
# (e) The logs
# =============================================================================


def test_neither_a_ticket_nor_its_hash_is_ever_logged(tmp_path, caplog, monkeypatch):
    """(e) Every path of the module, the stage id free to appear: a ticket issued then replaced; read wrong, malformed,
    for another stage, right, expired; another read twice once committed (N53: the same answer); another dropped
    twice; then (B-42) a ticket of the instance presented twice to its file broken in a way of each failure of (g): an
    error, then a line at debug — the ticket the file was written for among those that must not appear."""
    print_section("(e) The logs")
    root = an_instance(tmp_path)
    pending, committed = restore_in(root, "pending"), restore_in(root, "committed")
    with logs_of_outcome(caplog, monkeypatch) as events:
        replaced = issued(root)
        ticket = issued(root, now=ISSUED_AT + timedelta(minutes=1))
        opened(replaced, pending, root)
        opened(ticket[:-1], pending, root)
        opened(ticket, restore_in(root, "pending", stage_id=OTHER_STAGE), root)
        opened(ticket, pending, root)
        opened(ticket, pending, root, now=ISSUED_AT + 2 * TTL)
        final = issued(root, now=ISSUED_AT + timedelta(minutes=2))
        opened(final, committed, root)
        opened(final, committed, root)
        dropped = issued(root, now=ISSUED_AT + timedelta(minutes=3))
        drop(root)
        drop(root)
        broken = BrokenTicketFile(root, monkeypatch)
        spoiled = issued(root, now=ISSUED_AT + timedelta(minutes=4))
        for way in EVERY_FAILURE:
            broken.now(way)
            opened(spoiled, pending, root)
            opened(spoiled, pending, root)
    tickets = [replaced, ticket, final, dropped, spoiled, SOME_TICKET]
    hidden = tickets + [hash_of(value) for value in tickets]
    assert leaked(events, caplog.records, hidden) == [], "neither a ticket nor its hash is logged"
    print_success(f"{len(events)} events and {len(caplog.records)} records checked: no ticket, no hash")


# =============================================================================
# (f) The configured data directory and the clock
# =============================================================================


def test_without_data_dir_or_now_the_configured_data_directory_and_the_clock_are_used(tmp_path, monkeypatch):
    """(f) As ``apply``'s functions: ``data_dir`` is ``get_data_dir()`` when not given, ``now`` the clock — a ticket
    issued now opens, one issued two hours ago has expired."""
    print_section("(f) The defaults")
    root = an_instance(tmp_path, "configured-instance")
    cases.configure(monkeypatch, root)
    outcome = outcome_module()
    started = datetime.now(UTC)
    ticket = outcome.issue_ticket(STAGE)
    ended = datetime.now(UTC)
    record = json.loads(ticket_file(root).read_bytes())
    issued_at = moment(record["issued_at"])
    assert started - timedelta(seconds=1) <= issued_at <= ended and moment(record["expires_at"]) == issued_at + TTL, f"issued now (a second of slack: the precision of a time is not the contract's), in the configured data directory: {record}"
    state = restore_in(root, "pending")
    assert shown(outcome.read_outcome(ticket, state)) == outcome_of(state), "read now, in the configured data directory: it opens"
    old = outcome.issue_ticket(STAGE, now=datetime.now(UTC) - 2 * TTL)
    assert outcome.read_outcome(old, state) is None and not os.path.lexists(ticket_file(root)), "the clock is now: a ticket of two hours ago has expired, its file removed"
    outcome.issue_ticket(STAGE)
    outcome.drop_ticket()
    assert not os.path.lexists(ticket_file(root)), "dropped from the configured data directory"
    print_success("the configured data directory, the clock")


# =============================================================================
# (g) B-42: a ticket's file that cannot be used, one error while the same failure lasts
# =============================================================================


@pytest.mark.parametrize("way", BROKEN_WAYS)
def test_a_ticket_s_file_that_cannot_be_used_is_one_error_however_often_it_is_read(tmp_path, caplog, monkeypatch, way):
    """(g) B-42: anyone, without a session, reaches the ticket's file with any well-formed ticket. Broken in ``way``, and
    read three times, each with another well-formed ticket that is not the right one: ``None`` each time, and one error,
    that failure's — nothing louder after it while it lasts (whether a line at debug is captured is not asserted).

    RED until B-42's code: an error at every read, anybody's to repeat as often as they like."""
    print_section("(g) B-42: a ticket's file that cannot be used")
    root = an_instance(tmp_path)
    broken = BrokenTicketFile(root, monkeypatch)
    failure = broken.now(way)
    state = restore_in(root, "pending")
    with logs_of_outcome(caplog, monkeypatch) as events:
        answers = [opened(secrets.token_urlsafe(32), state, root) for _ in range(3)]
    assert answers == [None] * 3, f"{way}: None at every read: {answers}"
    assert warned(events) == [("error", failure)], f"{way}: one error while the same failure lasts, not one per read: {lines(events)}"
    print_success(f"{way}: read three times, one error")


def _written_again(root: Path) -> None:
    """A new restart: ``issue_ticket`` writes the ticket's file."""
    issued(root, now=ISSUED_AT + timedelta(minutes=1))


def _read_whole_and_valid(root: Path) -> None:
    """A valid ticket's file put back by the test (nothing issued), then read whole and valid by a well-formed ticket that
    is not its own: nothing opens, but the file was read."""
    path = ticket_file(root)
    path.unlink(missing_ok=True)
    path.write_bytes(a_ticket_s_file())
    assert opened(secrets.token_urlsafe(32), None, root) is None, "precondition: a ticket that is not the file's opens nothing"


def _dropped(root: Path) -> None:
    """A confirmation or a cancel: ``drop_ticket`` removes the file."""
    drop(root)


def _found_missing(root: Path) -> None:
    """The file removed behind the product's back, then a read that finds none."""
    ticket_file(root).unlink()
    assert opened(secrets.token_urlsafe(32), None, root) is None, "precondition: without a file, nothing opens"


#: B-42: what makes the same failure an error again, each alone: the file written by ``issue_ticket``, read whole and
#: valid, removed by ``drop_ticket``, or found missing by a read.
SEEN_CHANGED = [
    pytest.param(_written_again, id="written"),
    pytest.param(_read_whole_and_valid, id="read-whole-and-valid"),
    pytest.param(_dropped, id="dropped"),
    pytest.param(_found_missing, id="found-missing"),
]


@pytest.mark.parametrize("change", SEEN_CHANGED)
@pytest.mark.parametrize("way", BROKEN_WAYS)
def test_the_same_failure_is_an_error_again_once_the_file_is_written_read_or_removed(tmp_path, caplog, monkeypatch, way, change):
    """(g) B-42: broken, read twice: one error. Then the failure mended and the file written, read whole and valid,
    removed or found missing — each alone — and broken the same way again, read twice: one more error, for a file the
    product saw change in between. ``None`` at every read.

    RED until B-42's code: four errors."""
    root = an_instance(tmp_path)
    broken = BrokenTicketFile(root, monkeypatch)
    state = restore_in(root, "pending")
    with logs_of_outcome(caplog, monkeypatch) as events:
        failure = broken.now(way)
        answers = [opened(secrets.token_urlsafe(32), state, root) for _ in range(2)]
        broken.mend()
        change(root)
        broken.now(way)
        answers += [opened(secrets.token_urlsafe(32), state, root) for _ in range(2)]
    assert answers == [None] * 4, f"{way}, {change.__name__}: None at every read: {answers}"
    assert warned(events) == [("error", failure)] * 2, f"{way}, {change.__name__}: one error before, one again after: {lines(events)}"
    print_success(f"{way}, {change.__name__}: an error again")


#: B-42: failures one after the other, each read twice: another event (not a ticket, then over 4096 bytes), or the same
#: event with another ``error`` (a link's ELOOP, then an EIO); then back to the first, another failure again.
CHANGES_OF_FAILURE = [
    pytest.param(("not-a-ticket", "over-4096-bytes", "not-a-ticket"), id="another-event-and-back"),
    pytest.param(("a-link", REFUSED, "a-link"), id="the-same-event-another-error-and-back"),
]


@pytest.mark.parametrize("ways", CHANGES_OF_FAILURE)
def test_a_failure_of_another_kind_is_an_error_even_back_to_the_first(tmp_path, caplog, monkeypatch, ways):
    """(g) B-42: what is remembered is the failure that lasts, its event and its ``error``: each change of failure is an
    error, a return to the first one included; its repeats are not. ``None`` at every read.

    RED until B-42's code: six errors."""
    root = an_instance(tmp_path)
    broken = BrokenTicketFile(root, monkeypatch)
    state = restore_in(root, "pending")
    failures: list[str] = []
    answers: list[Any] = []
    with logs_of_outcome(caplog, monkeypatch) as events:
        for way in ways:
            failures.append(broken.now(way))
            answers += [opened(secrets.token_urlsafe(32), state, root) for _ in range(2)]
    sequence = " → ".join(ways)
    assert answers == [None] * (2 * len(ways)), f"{sequence}: None at every read: {answers}"
    assert warned(events) == [("error", failure) for failure in failures], f"{sequence}: an error at each change of failure, none for its repeats: {lines(events)}"
    print_success(f"{sequence}: {len(failures)} errors")


@pytest.mark.parametrize("way", BROKEN_WAYS)
def test_each_data_directory_remembers_its_own_failure(tmp_path, caplog, monkeypatch, way):
    """(g) B-42: two data directories, their ticket's files broken the same way, read in turn, twice each: one error each
    — the memory of one is not the other's. ``None`` at every read.

    RED until B-42's code: four errors."""
    roots = [an_instance(tmp_path, "first"), an_instance(tmp_path, "second")]
    breakers = [BrokenTicketFile(root, monkeypatch) for root in roots]
    failures = [broken.now(way) for broken in breakers]
    with logs_of_outcome(caplog, monkeypatch) as events:
        answers = [opened(secrets.token_urlsafe(32), restore_in(root, "pending"), root) for _ in range(2) for root in roots]
    assert answers == [None] * 4, f"{way}: None at every read: {answers}"
    assert warned(events) == [("error", failure) for failure in failures], f"{way}: one error for each data directory: {lines(events)}"
    print_success(f"{way}: two data directories, one error each")

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
    confirmation or a cancel removes it (``test_backup_apply.py`` (n)), or its holder presents it expired.
(d) ``drop_ticket(*, data_dir)``: the file removed, nothing else; without one, nothing done and nothing created; it never
    raises (a file that cannot be removed is logged, as a warning or an error) and removes nothing through a link, in
    place of ``.restore`` or of the file.
(e) Neither a ticket nor its hash is ever logged — issued, replaced, read (right, wrong, malformed, of another stage,
    expired, final and read again) or dropped — in a structlog event or a stdlib record.
(f) Without ``data_dir`` and ``now``: the configured data directory and the clock.

How. Pure: every data directory under ``tmp_path``, its ``.restore`` made as ``ensure_private_dir`` makes it. The
restore's state is a ``RestoreState`` built in the test as a start leaves it: ``read_outcome`` reads only the state it is
given. The ticket file is always the product's, but where a case needs one the product never writes (an extra key, a
folder, a link). The process's configured data directory is a folder of the test that must stay absent
(``configured_data_dir`` of the staging tests, imported, autouse), but in (f), where it is the test's instance. ``now`` is
given everywhere but in (f). Logs are read with ``structlog.testing.capture_logs`` and pytest's ``caplog``, each behind a
barrier: a canary through a logger of ``outcome``'s name must reach it. Modes and links are POSIX-only. No database, no
server, no network.
"""

from __future__ import annotations

import ast
import hashlib
import importlib
import inspect
import json
import logging
import os
import re
import secrets
import stat
from collections.abc import Iterator
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


def opened(ticket: str | None, state: RestoreState | None, root: Path, *, now: datetime = READ_AT) -> Any:
    """What ``ticket`` opens in ``root`` at ``now`` for the restore ``state``: half-way through its hour, unless said."""
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
    twice."""
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
    tickets = [replaced, ticket, final, dropped]
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

"""The outcome of a restore for the page that restarted the server, read with a one-time ticket (lot B5c).

A restore ends every session, and without ``JWT_SECRET`` every start of LibreFolio does too: after a restart the page
cannot tell from its session whether the restore was applied. So ``POST /backup/restore/restart`` hands it a ticket,
and ``GET /backup/restore/outcome`` tells the holder of that ticket, without a session, what became of the restore,
and nothing else: no names, dates, versions or paths.

The ticket is 256 random bits (``secrets.token_urlsafe(32)``). Only its SHA-256 is kept, in
``.restore/outcome-ticket.json`` (0600, written atomically without following a link), with the stage of the restore it
belongs to and its expiry, one hour after the restart was asked. ``.restore`` is never swapped, so the ticket outlives
the restart, the swap, the commit and a rollback. One restore, one ticket (decision N53): a new restart request
replaces it, a new confirmation and a cancel remove it (``apply.confirm_restore``, ``apply.cancel_restore``), and its
own holder presenting it expired removes it; until then it answers as often as asked, a final outcome included, so
that a final answer lost on its way (a connection cut while LibreFolio starts) can be read again. This module does
not import ``apply``, which imports it: the caller hands ``read_outcome`` the state of the restore, or the function
that reads it, called only for the ticket of a restart not expired: no other caller makes LibreFolio read the state,
nor log that it cannot (B-41).
"""

import contextlib
import hashlib
import hmac
import os
import re
import secrets
import threading
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from backend.app.config import get_data_dir
from backend.app.logging_config import get_logger
from backend.app.schemas.backup import RestoreOutcome
from backend.app.services.platform.instance_backup.paths import BackupPathError, is_plain_dir, outcome_ticket_path, restore_dir

if TYPE_CHECKING:
    from backend.app.services.platform.instance_backup.apply import RestoreState

logger = get_logger(__name__)

#: How long the page that asked the restart can read the outcome: a first start that migrates a large database fits.
OUTCOME_TICKET_TTL = timedelta(hours=1)

#: What ``secrets.token_urlsafe(32)`` gives: 43 characters of the URL-safe base64 alphabet.
_TICKET = re.compile(r"[A-Za-z0-9_-]{43}")
_PARTIAL_SUFFIX = ".part"
#: The ticket file is a few hundred bytes: a larger one is not ours.
_MAX_RECORD_BYTES = 4096
_IN_PROGRESS = frozenset({"applying", "applied", "rolling_back"})

#: The failure of each data directory's ticket file last logged as an error (B-42). Any 43 URL-safe characters reach
#: that file without a session: a failure is logged once, then at debug while it lasts, and again once the file has been
#: written, removed or read in between, or fails otherwise.
_REPORTED: dict[str, tuple[str, str | None]] = {}
_REPORTED_GUARD = threading.Lock()


class OutcomeTicket(BaseModel):
    """What ``.restore/outcome-ticket.json`` holds: the hash of the ticket, never the ticket."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    format: Literal[1] = 1
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    stage_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    issued_at: datetime
    expires_at: datetime


def _now() -> datetime:
    return datetime.now(UTC)


def _digest(ticket: str) -> str:
    return hashlib.sha256(ticket.encode("ascii")).hexdigest()


def _fsync_dir(folder: Path) -> None:
    """Make the rename inside ``folder`` durable; nothing where the file system cannot."""
    with contextlib.suppress(OSError):
        fd = os.open(folder, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def _report(data_dir: Path, event: str, error: str | None = None) -> None:
    """A failure to read the ticket file: an error the first time, a debug line while the same failure lasts (B-42)."""
    with _REPORTED_GUARD:
        repeated = _REPORTED.get(str(data_dir)) == (event, error)
        _REPORTED[str(data_dir)] = (event, error)
    fields = {} if error is None else {"error": error}
    if repeated:
        logger.debug(event, **fields)
    else:
        logger.error(event, **fields)


def _forget(data_dir: Path) -> None:
    """The ticket file written, removed or read: its next failure is a new one, logged as an error (B-42)."""
    with _REPORTED_GUARD:
        _REPORTED.pop(str(data_dir), None)


def issue_ticket(stage_id: str, *, data_dir: Path | None = None, now: datetime | None = None) -> str:
    """A new ticket for the outcome of the restore of ``stage_id``, replacing any other.

    ``BackupPathError`` when ``.restore`` is a link or a file; an ``OSError`` when the file cannot be written.
    """
    data_dir = data_dir or get_data_dir()
    now = now or _now()
    folder = restore_dir(data_dir)
    if not is_plain_dir(folder):
        raise BackupPathError(folder)
    ticket = secrets.token_urlsafe(32)
    record = OutcomeTicket(sha256=_digest(ticket), stage_id=stage_id, issued_at=now, expires_at=now + OUTCOME_TICKET_TTL)
    target = outcome_ticket_path(data_dir)
    partial = target.with_name(target.name + _PARTIAL_SUFFIX)
    fd = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        os.fchmod(handle.fileno(), 0o600)
        handle.write(record.model_dump_json(indent=2))
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(partial, target)
    _fsync_dir(folder)
    _forget(data_dir)
    logger.info("Restore outcome ticket issued", stage_id=stage_id, expires_at=record.expires_at.isoformat())
    return ticket


def _read_record(data_dir: Path) -> OutcomeTicket | None:
    """The ticket file, read without following a link; ``None`` when there is none or it cannot be read: logged as an
    error once while the same failure lasts (``_report``, B-42)."""
    try:
        with os.fdopen(os.open(outcome_ticket_path(data_dir), os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)), "rb") as handle:
            raw = handle.read(_MAX_RECORD_BYTES + 1)
    except FileNotFoundError:
        _forget(data_dir)
        return None
    except OSError as exc:
        _report(data_dir, "The restore outcome ticket cannot be read", f"{type(exc).__name__}: {exc.strerror or exc}")
        return None
    if len(raw) > _MAX_RECORD_BYTES:
        _report(data_dir, "The restore outcome ticket is not one this LibreFolio wrote: it is ignored")
        return None
    try:
        record = OutcomeTicket.model_validate_json(raw)
    except ValidationError:
        _report(data_dir, "The restore outcome ticket is not one this LibreFolio can read: it is ignored")
        return None
    _forget(data_dir)
    return record


def read_outcome(ticket: str | None, state: "RestoreState | Callable[[], RestoreState | None] | None", *, data_dir: Path | None = None, now: datetime | None = None) -> RestoreOutcome | None:
    """What became of the restore ``state``, for the holder of its ticket; ``None``, alike, for any ticket that does not
    give it: none, malformed, unknown, of another restore, or expired (then removed). A wrong ticket changes nothing;
    the right one reads the outcome as often as asked until it expires, a final one included (decision N53).

    ``state`` may be the function that reads it: called once, and only for the ticket of a restart not expired, so that
    no other caller makes LibreFolio read the state of the restore, nor log that it cannot (B-41)."""
    if ticket is None or not _TICKET.fullmatch(ticket):
        return None
    data_dir = data_dir or get_data_dir()
    now = now or _now()
    if not is_plain_dir(restore_dir(data_dir)):
        return None
    record = _read_record(data_dir)
    if record is None:
        return None
    # A wrong ticket leaves the file as it is: nobody without the ticket can spend or remove it.
    if not hmac.compare_digest(record.sha256, _digest(ticket)):
        return None
    if now >= record.expires_at:
        drop_ticket(data_dir=data_dir)
        return None
    if callable(state):
        state = state()
    if state is None or state.stage_id != record.stage_id:
        return None
    phase = "in_progress" if state.status in _IN_PROGRESS else state.status
    return RestoreOutcome(state=phase, reason=state.reason, waiting=state.waiting)


def drop_ticket(*, data_dir: Path | None = None) -> None:
    """Remove the ticket, if there is one; never raises (a failure is logged)."""
    data_dir = data_dir or get_data_dir()
    if not is_plain_dir(restore_dir(data_dir)):
        return
    try:
        outcome_ticket_path(data_dir).unlink(missing_ok=True)
        _forget(data_dir)
    except OSError as exc:
        logger.error("The restore outcome ticket could not be removed", error=f"{type(exc).__name__}: {exc.strerror or exc}")

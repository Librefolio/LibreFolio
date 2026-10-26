"""The owner of a managed instance after a restore from the app (B5-1): the account the owner chose gets their address.

On an instance a hosting provider runs (profile ``managed``), the owner is the person whose address is
``LIBREFOLIO_ADMIN_EMAIL``. A backup an administrator uploads may come from anywhere: in it the owner may be missing,
demoted, or hold a password someone else knows. So a restore confirmed from the app names the account of the backup
that becomes the owner's (``apply.confirm_restore``: mandatory in ``managed``), and the first start on the restored data
gives that account the owner's address, makes it a protected administrator, makes its password unusable, and sends the
owner a link to choose a new one: workstream A's ``assign_owner_and_send_reset``. Whoever prepared the backup cannot sign
in as the owner.

A restore confirmed on the command line or by the hosting panel has nobody to ask (B5-1j): the confirmation picks the
account itself from the checked copy (``apply.pick_owner``: the account that holds the owner's address, else the one
active administrator the backup marks as its owner), and everything else is the same. The link goes to
``LIBREFOLIO_ADMIN_EMAIL``, never to an address of the backup. When nobody can be picked the restore goes on without an
owner (``owner_outcome`` ``none``) and the operator names one with ``./dev.py user reassign-owner <username>``.

The step ``restore-owner`` runs right after ``restore-commit``; it never raises. What it did (``sent``, ``link_only``, or
``error:<CODE>``) is kept in the state of the restore (``owner_outcome``). A does the whole treatment at every call and
repeating it is harmless (it revokes the old link and sends a new one), so a start that dies after the call and before the
record simply calls again. For ``link_only`` A writes the link in the instance log; it is never kept here, shown in the
report or answered by the API: every administrator reads the report, the one who prepared the backup included. A restore
confirmed by the hosting panel or on the command line names it through ``apply.pick_owner``.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import sqlite3
from pathlib import Path

from backend.app.config import get_data_dir, get_settings
from backend.app.logging_config import get_logger

logger = get_logger(__name__)


def owner_choice_required() -> bool:
    """Whether a restore confirmed from the app must name the owner's account: on a managed instance only."""
    return get_settings().LIBREFOLIO_PROFILE == "managed"


def configured_owner_email() -> str | None:
    """The owner's address (``LIBREFOLIO_ADMIN_EMAIL``), or ``None`` when it is not set or cannot be read. Never raises:
    a value that cannot be used stops the server at its start already (F02)."""
    from backend.app.config.accounts import admin_bootstrap_config  # noqa: PLC0415 — config imports nothing of this

    try:
        config = admin_bootstrap_config()
    except Exception:  # noqa: BLE001 — a probe: an unusable value means no address here, the startup audit says why
        return None
    return config.email if config is not None else None


#: A's call is tried this many times when the database is locked by another writer (the other workers of the start, a
#: backup running), with this pause between two tries; any other failure is not retried. Repeating the call is harmless.
_ATTEMPTS = 4
_RETRY_PAUSE_SECONDS = 1.0
#: How long a connection waits for a lock before SQLite gives up, in seconds (the busy timeout).
_BUSY_TIMEOUT_SECONDS = 30


#: Held by the worker that gives the owner their account: the others of the same start leave it to that one.
OWNER_LOCK_FILE = "owner.lock"


def _take_owner_lock(data_dir: Path) -> int | None:
    """The exclusive lock of the owner's assignment, not waited for: its descriptor, or ``None`` when another worker
    holds it (or the lock cannot be had at all: that worker, or the next start, does it)."""
    import fcntl  # noqa: PLC0415 — POSIX; the managed profile runs on Linux

    from backend.app.services.platform.instance_backup.paths import restore_dir  # noqa: PLC0415

    fd = os.open(restore_dir(data_dir) / OWNER_LOCK_FILE, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        return None
    return fd


@contextlib.contextmanager
def held_owner_lock(data_dir: Path):
    """The owner's lock for a block, not waited for: yields whether this process holds it. Taken before the apply lock,
    as the startup step does."""
    fd = _take_owner_lock(data_dir)
    try:
        yield fd is not None
    finally:
        if fd is not None:
            with contextlib.suppress(OSError):
                os.close(fd)


def _assign_owner():
    """Workstream A's ``assign_owner_and_send_reset`` and its ``OwnerAssignmentError``, looked up at each call."""
    from backend.app.services.accounts.instance_owner import OwnerAssignmentError, assign_owner_and_send_reset  # noqa: PLC0415

    return assign_owner_and_send_reset, OwnerAssignmentError


async def assign_restored_owner(data_dir: Path | None = None):
    """The startup step ``restore-owner``: give the owner the account they chose, once the restore is committed.

    Nothing (``None``) unless the restore is committed, was confirmed from the app with an owner named, and has no
    recorded outcome yet. Otherwise the recorded state. Never raises: a failure is logged, and a failure that is not
    A's own refusal leaves the call for the next start.
    """
    from backend.app.services.platform.instance_backup.apply import owner_pending  # noqa: PLC0415

    data_dir = data_dir or get_data_dir()
    try:
        pending = await asyncio.to_thread(owner_pending, data_dir)
    except Exception as exc:  # noqa: BLE001 — a startup step after restore-commit never stops the start
        logger.error("The owner of the restored data could not be looked up", error=type(exc).__name__)
        return None
    if pending is None:
        return None
    try:
        lock = await asyncio.to_thread(_take_owner_lock, data_dir)
    except OSError as exc:
        logger.error("The owner of the restored data cannot be set now: the next start tries again", error=type(exc).__name__)
        return None
    if lock is None:
        return None  # another worker of this start gives it
    try:
        return await _assign_locked(data_dir)
    finally:
        with contextlib.suppress(OSError):
            os.close(lock)


def _is_lock_error(exc: BaseException) -> bool:
    """Whether ``exc`` is SQLite saying the database or a table is locked or busy: the one failure that is waited out."""
    cause = getattr(exc, "orig", None) or exc
    return isinstance(cause, sqlite3.OperationalError) and any(word in str(cause).lower() for word in ("locked", "busy"))


async def _assign_with_retries(assign, engine, user_id: int):
    """A's call on a fresh session, tried again (a few times, after a pause) while the database is locked."""
    from sqlalchemy.ext.asyncio import AsyncSession  # noqa: PLC0415

    for attempt in range(1, _ATTEMPTS + 1):
        try:
            async with AsyncSession(engine, expire_on_commit=False) as session:
                return await assign(session, user_id)
        except Exception as exc:  # noqa: BLE001 — only a lock error is waited out; the rest is re-raised unchanged
            if not _is_lock_error(exc) or attempt == _ATTEMPTS:
                raise
            logger.warning("The database is locked: the owner's assignment is tried again", attempt=attempt, attempts=_ATTEMPTS)
            await asyncio.sleep(_RETRY_PAUSE_SECONDS)
    raise AssertionError("unreachable")  # pragma: no cover — the loop returns or raises


async def _assign_locked(data_dir: Path):
    """``assign_restored_owner`` once its lock is held: the pending owner read again, A called, its outcome recorded."""
    from backend.app.services.platform.instance_backup.apply import owner_pending, record_owner_outcome  # noqa: PLC0415

    pending = await asyncio.to_thread(owner_pending, data_dir)
    if pending is None:
        return None
    stage_id, user_id = pending
    try:
        assign, refusal = _assign_owner()
    except ImportError as exc:
        logger.error("The owner of the restored data cannot be set: this LibreFolio lacks the function", stage_id=stage_id, error=type(exc).__name__)
        return None
    from sqlalchemy.ext.asyncio import create_async_engine  # noqa: PLC0415
    from sqlalchemy.pool import NullPool  # noqa: PLC0415

    from backend.app.services.platform.instance_backup.paths import database_path  # noqa: PLC0415

    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path(data_dir)}", poolclass=NullPool, connect_args={"timeout": _BUSY_TIMEOUT_SECONDS})
    try:
        result = await _assign_with_retries(assign, engine, user_id)
    except refusal as exc:
        outcome = f"error:{getattr(exc, 'code', 'UNKNOWN')}"
        logger.error("The owner of the restored data could not be set", stage_id=stage_id, user_id=user_id, code=getattr(exc, "code", None))
    except Exception as exc:  # noqa: BLE001 — the next start calls again; the start goes on
        logger.error("The owner of the restored data could not be set: the next start tries again", stage_id=stage_id, user_id=user_id, error=type(exc).__name__)
        return None
    else:
        outcome = str(getattr(result.outcome, "value", result.outcome))
        logger.warning("The owner of the restored data is set", stage_id=stage_id, user_id=user_id, outcome=outcome)
    finally:
        await engine.dispose()
    try:
        return await asyncio.to_thread(record_owner_outcome, data_dir, stage_id, outcome)
    except Exception as exc:  # noqa: BLE001 — not recorded: the next start calls again, which is harmless
        logger.error("The outcome of the owner could not be recorded: the next start tries again", stage_id=stage_id, error=type(exc).__name__)
        return None

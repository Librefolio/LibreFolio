"""
Restoring a backup, the confirmation through the API (workstream B, lot B3, contract §5, §6 and §11): the four new routes
of ``/api/v1/backup/restore``, and what they change in the two of lot B2b that drop and prune a checked copy. Lot B5c
adds the outcome of a restart read with a one-time ticket, without a session (``GET /backup/restore/outcome``, (i)), and
B-17: a cancel drops the checked copy (d).

Written before the code (red until lot B3 lands): ``apply.py`` and ``restart.py`` do not exist yet. Every name of lot B3
is imported inside the test that needs it (``product``), so the file collects, and each test fails on its own. The
``instance_blocked`` cases (§11, P7) were written red the same way, before P7, and lot B5c's before B5c: ``outcome.py``
(``outcome_module``) and ``paths.outcome_ticket_path`` (``ticket_path``) are looked up by the test that needs them.

Under test: ``backend/app/api/v1/backup/restore.py`` (the routes), ``restore_jobs.confirm_check`` / ``remove_check`` /
``prune``, ``instance_backup/apply.py`` as the routes reach it, ``instance_backup/restart.py`` (``send_signal``),
``instance_backup/outcome.py`` as the routes reach it, and ``RestoreStatus``, ``RestoreRestartAccepted`` and
``RestoreOutcome`` of ``backend/app/schemas/backup.py``.

(a) ``POST /backup/restore/stage/{stage_id}/confirm``: 202 ``RestoreStatus`` ``pending``. On disk,
    ``.restore/restore.json`` (0600): ``pending``, the stage, the data directory resolved, ``confirmed_by`` the
    administrator's username, ``confirmed_at`` the time of the request, ``backup_created_at``, ``backup_app_version`` and
    ``action`` from the check's report, nothing of a swap yet. The copy and its check are kept as they were; nothing else
    of the data directory is touched. ``GET /status`` answers the same. A second confirmation, of this copy or another,
    while a restore is ACTIVE (pending, applying, applied, rolling back): 409 ``restore_already_pending``, the state
    unchanged.
(b) The refusals of a confirmation, each code of §6, nothing written: 404 ``restore_stage_not_found`` (no such check;
    its copy's database or its report gone), 409 ``restore_stage_running``, 409 ``restore_not_restorable`` (a report
    with a blocker; a failed check), 410 ``restore_stage_expired``, 409 ``restore_stage_outdated`` (the report's head is
    not this LibreFolio's; ``apply.alembic_head_revision`` moved; not judged when it is ``None``); never a path in the
    answer. Once the check ended, ``.restore`` a link or a file: 500 ``restore_folder_unusable`` (``confirm_check`` checks
    it first: it writes there); a link in place of ``checks/`` or ``stage/``: the check or its copy is not found, 404
    ``restore_stage_not_found``. Nothing written through any of them, nor anywhere in the data directory. B-31, a
    confirmation that fails on the way (its lock, the write of its state): a full disk or a quota, itself or as a cause,
    is 507 ``backup_no_space`` and one warning; any other ``OSError`` 500 ``restore_confirm_failed`` and one error naming
    its type and the system's words, which stay out of the answer. Nothing is confirmed (the state is written last,
    atomically), and the same confirmation, the failure gone, is 202.
(c) ``GET /backup/restore/status``: ``none`` without a restore, and nothing created to say so; each phase on disk as
    its state (applying, applied and rolling back are ``in_progress``), its fields as recorded; a pending restore says
    why a start left it waiting, for each of the four reasons (§11, P7: ``instance_blocked``, on an instance not blocked
    itself, since a blocked one answers no restore route); a ``restore.json`` that is a link is never followed. B-33 §1:
    a ``restore.json`` that is a link, or that holds no state this LibreFolio reads (not JSON, §10's strict cases), is
    a state that cannot be read: 500 ``restore_state_unreadable`` (it was ``none``), nothing changed.
(d) ``DELETE /backup/restore/pending``: 204, the state removed and, since B-17 (lot B5c, as the command line's
    ``pending --cancel``), the checked copy and its check with it: polling it or confirming it again is 404
    ``restore_stage_not_found``; another check is not the restore's, and stays. The ticket of a restart goes too (i).
    Without a state file, 404 ``restore_not_pending`` and nothing created, not even ``.restore/apply.lock`` (the lock is
    taken only once a state file is found); a restore being applied or finished, 404 too, its state unchanged, and the
    ticket of its restart kept for its outcome. B-31: an ``OSError`` before the restore is dropped (its lock, the removal
    of its state file) is 500 ``restore_cancel_failed`` and one error, the restore still pending, and the cancel, the
    failure gone, is 204; an ``OSError`` while its copy is removed, once the restore is dropped, is a 204 all the same,
    with one warning naming the stage: the copy goes when its check expires.
(e) ``POST /backup/restore/restart``: 202 ``RestoreRestartAccepted``: the ``RestoreStatus`` (pending) and, since lot B5c,
    the ticket of its outcome (i); after the answer is sent, a SIGTERM to the server's process (``restart.server_pid()``),
    through ``restart.send_signal`` and nothing else; the state unchanged. 409 ``restore_not_pending`` otherwise, no
    signal, and no ticket written. B-31 pins its failure: ``prepare_restart`` raising an ``OSError`` (a full disk
    included) is 500 ``restore_restart_failed`` and one error, no restart scheduled, no signal, no ticket, the restore
    still pending.
(f) The copy of an ACTIVE restore: ``DELETE /backup/restore/stage/{id}`` is 409 ``restore_pending`` and keeps it;
    another check is dropped as before, and so is the copy of a finished restore. ``prune``, however old everything
    looks, keeps the ACTIVE restore's check and copy, the command line's copy that no check records included; a
    finished restore's old copy is pruned as before.
(g) Administrators only: a regular user gets 403 from each new route, and nothing changes, no signal. None of the four
    is allowed on a blocked instance. OpenAPI: the four operations carry ``Backup & Export``, their success and model
    (the restart's ``RestoreRestartAccepted`` since lot B5c), and document their refusals with their codes; the drop
    documents ``restore_pending``; ``RestoreStatus.waiting`` lists exactly the four reasons, ``instance_blocked``
    included (§11). B-31: the confirmation documents 507 ``backup_no_space`` and its 500 names ``restore_confirm_failed``
    beside ``restore_folder_unusable``; the cancel documents a 500 ``restore_cancel_failed``; the restart's 500 names
    ``restore_restart_failed``.
(h) ``upload_limit_mb`` (§6), in every ``RestoreStatus`` answer, ``none`` included: the largest archive the upload
    accepts now, in MB, read by ``backup_max_upload_mb()`` when the answer is built: 0 unset and self-hosted, 500 unset
    and managed, the variable's value when set (over the profile), ``null`` when it cannot be read, with one error
    logged naming the variable, as the upload's 503 logs it. The same in the answers of confirm, status and restart; a
    change of the variable between two answers shows in the second. In the ``RestoreStatus`` schema.
(i) Lot B5c, the outcome of a restart without a session. The restart's answer carries ``outcome_ticket`` (43 URL-safe
    characters), with ``Cache-Control: no-store``; its file (``.restore/outcome-ticket.json``, 0600: its SHA-256, the
    stage, ``issued_at``, ``expires_at`` an hour later, never the ticket) is on disk before the answer begins; a 409
    writes none; a second restart replaces it. ``GET /backup/restore/outcome`` answers a caller without any session or
    cookie, the ticket in ``X-Restore-Ticket`` only (``?ticket=`` is ignored): 200 ``{state, reason, waiting}`` and
    nothing more, ``Cache-Control: no-store``, for each phase (applying, applied, rolling back: ``in_progress``) and each
    reason a start leaves a restore waiting. Every ticket that does not open it — none, empty, malformed, another one,
    its hash, in the query, replaced, expired, its file gone, unreadable, with a key more or a link, no restore, another
    stage, dropped by a cancel — gets one and the same 404 ``restore_outcome_not_found``: status, headers and bytes. One
    restore, one ticket, not one read (decision N53): every outcome, a final one (committed, rolled back) included, is
    answered again, the same, its file kept, until the ticket expires — an answer lost on the way (a connection reset
    while the server starts) is asked again instead of the page falling back on a session the restore ended; expired,
    the one 404, its file removed. A cancel and a new confirmation drop the ticket. Neither the ticket nor its hash is
    logged. On a blocked instance the outcome still answers — a restore a start left waiting for the unblock reads
    ``pending``, ``instance_blocked`` — RED until workstream H's line puts it in ``ALLOWED_WHEN_BLOCKED``; every other
    restore route stays 423 for a signed-in administrator. OpenAPI documents the route, its header, its 404 code,
    ``RestoreOutcome`` and ``RestoreRestartAccepted``.
(j) B-32, a state the file system cannot read: a regular ``restore.json`` whose opening fails, ``os.open`` refusing it
    (EACCES, EIO) or, for real, its mode 000 (never as root, who reads it all the same). Not a state hidden: the routes
    say so. ``GET /status``, ``DELETE /pending`` with a pending restore, ``POST /restart``, and the confirmation of a
    fresh check while a pending restore's state cannot be read: 500 ``restore_state_unreadable`` (the status's message
    «The state of the restore cannot be read: the server's log has the cause»), and the log has it: the reader's error
    with the exception's type and its system's words, which stay out of the answer with any path. Nothing written: the
    state, its copy, its check and its ticket as they were, no ticket issued, no restart requested, the state not
    replaced by the confirmation (an unknown restore may be half applied); once the file can be read again, the restore
    still waits. ``GET /outcome`` with that restore's ticket keeps today's one 404 ``restore_outcome_not_found`` and
    leaves the ticket as it was (a guard): readable again, the same ticket opens the outcome. OpenAPI: the status
    documents a 500 naming ``restore_state_unreadable``; the 500s of the cancel, the restart and the confirmation name
    it too. B-33 §1 (m): the content too — a state no restore can hold, the (c) case named «unreadable» included, is no
    longer ``none`` but the same 500. B-41: only the right ticket of a restart that has not expired makes ``GET /outcome`` read the state (b5);
    every case of (i) the ticket alone decides, the state file then made unreadable, is the one 404 without the state
    file ever opened, nor «The state of the restore cannot be read» logged — else anyone could repeat that error.
(m) B-33 §1 (interface ``B-b33-interface.md``; written RED before it, the status code unchanged in this lot): a
    ``restore.json`` that is not a file (a folder, a link) or not valid (not JSON, ``format`` 2) cannot be read either.
    ``GET /status``, ``DELETE /pending``, ``POST /restart`` with that state, and the confirmation of a fresh check
    beside it: 500 ``restore_state_unreadable`` (the status's message as (j)'s), never ``none``, a 404, a 409 or a 202;
    no ticket, no restart, no signal; nothing written, removed or replaced, here or where a link points. (a)'s state
    file that is a link is refused so too (it was replaced before B-33), the link and its target as they were.
(k) Lot L3-2 (contract L3 §5): ``RestoreStatus`` gains ``confirmed_via`` (``admin``, ``cli`` or ``panel``; null
    without a restore), in ``GET /status`` and in the confirmation's answer. The administrators' route confirms via
    ``admin`` — an administrator whose username is literally ``cli`` or ``panel`` too —, written in ``restore.json``.
    ``GET /status`` reads each value as recorded, and a state written before L3-2 (no key) as ``cli`` when
    ``confirmed_by`` is ``cli``, ``admin`` otherwise. Written RED: ``STATUS_FIELDS`` holds ``confirmed_via``, so every
    test that compares a whole ``RestoreStatus`` (the confirmation of (a), ``none`` of (c), the OpenAPI schema) is red
    on that one field too, until L3-2.
(n) The status of an unreadable state, with its reason (interface ``B-sec345-interface.md``, «Status»): every route of
    ``/backup/restore`` that answers ``restore_state_unreadable`` — ``GET /status``, the confirmation of a fresh check,
    ``DELETE /pending``, ``POST /restart`` — answers 500 with ``detail`` exactly ``{"code": "restore_state_unreadable",
    "message": …, "reason": …}``, the message (j)'s, ``reason`` the ``RestoreStateUnreadableError.reason``: ``io`` (the
    file system refuses the state file, EIO), ``not_a_file`` (a folder, a link), ``invalid`` (not JSON, ``format`` 2).
    The OpenAPI description of the status's 500 names ``reason``. Written RED: the detail has no ``reason`` yet.
(o) Lot B5-1 (interface ``B-b51-interface.md`` §2, §3; written RED before it): the owner's choice. In ``managed``
    (``LIBREFOLIO_PROFILE``), ``GET /stage/{id}`` of a finished check carries ``report.owner_choice``: ``required``
    true, ``owner_email`` the configured one (``LIBREFOLIO_ADMIN_EMAIL`` as ``admin_bootstrap_config()`` reads it),
    ``forced_user_id`` the candidate holding it (A–Z case aside) or null, and the ``candidates`` (``user_id``,
    ``username``, ``email``, ``owner_email``, ``administrator``) by username; ``selfhosted``: ``owner_choice`` null. The
    confirmation takes an optional body ``RestoreConfirmRequest`` ``{owner_user_id}`` (``extra="forbid"``: an unknown
    key is 422): in ``managed`` the forced candidate is 202, its id in ``restore.json``; no body 409
    ``owner_choice_required``; another administrator while one holds the owner's email 409 ``owner_choice_invalid``;
    the owner's email unset 409 ``owner_email_not_set``; ``selfhosted`` with an owner id 400
    ``owner_choice_not_applicable``; nothing written by a refusal. ``RestoreStatus`` is unchanged (in
    ``STATUS_FIELDS``, so (a), (c) and the OpenAPI schema of (g) are red on it too), never the id nor the reset path.
    OpenAPI documents the new 409 and 400 codes and the body. The archive of (o) is a backup whose accounts have
    addresses of ``example.com`` (an address of ``.test`` is no email the configuration accepts), built once for the
    module by ``test_backup_staging.backup_with_accounts``. Security addendum §7.2 (written RED before it): the owner's
    address changed since the check (not only its case) is 409 ``restore_stage_outdated``; a check that found an owner
    conflict (``BOB_USER`` beside ``bob_user``) is 409 ``owner_conflict`` whatever the choice; the 409's description
    names ``owner_conflict``.

Pure, as ``test_backup_restore.py`` (lot B2b), whose fixtures and helpers are imported: an app of each test holds
``backup_router``, ``get_current_user`` overridden; the data directory of the routes under ``tmp_path`` (``apply``'s
and ``outcome``'s ``get_data_dir`` as well), the process configured with another folder that must stay absent;
``threading`` as ``restore_jobs`` sees it replaced. Real archives from the module fixtures of ``test_backup_staging.py``.
No signal is ever sent: ``restart.send_signal`` records in every test, and ``os.kill`` as ``restart`` sees it records too
(it must stay unused). States of a restore that only a start can reach (applying, applied, rolling back, committed,
rolled back) are written as ``apply.RestoreState`` would write them, and a ticket for them is issued by
``outcome.issue_ticket``, as the restart before that start issued it. ``prune`` is called with a ``now`` far ahead: no
file is aged, no clock waited for. The outcome is read as the page reads it once the start ended every session: through
an app with nobody signed in (``anonymous_app``: the real ``get_current_user``, which answers 401 to a request without a
cookie before any database) and no cookie at all; the database session of that app is a stand-in that fails the test if
anything reaches it. A blocked instance is ``backup_router`` behind ``refuse_when_blocked``, as ``router.py`` mounts every
route of ``/api/v1`` (``blocked_app``), ``LIBREFOLIO_BLOCKED`` set with ``monkeypatch``. ``refuse_when_blocked`` asks
``auth.get_current_user`` itself, outside FastAPI's overrides: where an administrator must be signed in, it is replaced
for the test by a stand-in that signs in whoever carries a session cookie and leaves anyone else to the real one. A
state the file system cannot read (j) is made so once the test's own setup is done: ``os.open`` replaced, refusing that
one file and handing every other path to the real one, or the file's mode set to 000; readable again at the end of the
test, whatever it did.
"""

from __future__ import annotations

import contextlib
import errno
import hashlib
import importlib
import json
import logging
import os
import re
import secrets
import signal
import stat
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import httpx
import pytest
from fastapi import APIRouter, Depends, FastAPI, Request
from structlog.testing import capture_logs

from backend.app.api.v1 import auth
from backend.app.api.v1.auth import SESSION_COOKIE_NAME
from backend.app.api.v1.backup import backup_router, restore
from backend.app.api.v1.instance_block import ALLOWED_WHEN_BLOCKED, refuse_when_blocked
from backend.app.config.platform import instance_blocked
from backend.app.db.session import get_session_generator
from backend.app.logging_config import get_logger
from backend.app.services.platform.instance_backup import restore_jobs
from backend.app.services.platform.instance_backup import staging as staging_service
from backend.app.services.platform.instance_backup.paths import check_state_path, restore_dir, stage_dir
from backend.app.services.platform.instance_backup.staging import STAGE_LIFETIME, StagingReport, read_report
from backend.test_scripts.test_api import test_backup_restore as api
from backend.test_scripts.test_services import test_backup_staging as cases
from backend.test_scripts.test_utils import print_section, print_success

# The fixtures of lot B2b's tests, re-exported: ``instance`` (autouse: the data directory of the routes, the fake threads,
# the configured data directory that must stay absent) and the real databases and archives.
instance = api.instance
databases = api.databases
head_archive = api.head_archive

CONFIRM = f"{api.STAGE}/{{stage_id}}/confirm"
STATUS = f"{api.API}/status"
PENDING = f"{api.API}/pending"
RESTART = f"{api.API}/restart"
#: The administrator who confirms: ``confirmed_by`` must be its username, not a constant.
B3_ADMIN = SimpleNamespace(id=7, username="b3-admin", is_superuser=True)
#: Every field of ``RestoreStatus`` (``extra="forbid"``): an answer has these and no other.
#: Lot B5-1 (o) keeps ``RestoreStatus`` as it was: what became of the owner's account is told by ``dev.py backup pending``
#: on the server only (workstream H's panel status is built from this model, closed, so a field here would reach it).
STATUS_FIELDS = {"state", "stage_id", "confirmed_at", "confirmed_by", "confirmed_via", "backup_created_at", "backup_app_version", "action", "finished_at", "reason", "waiting", "upload_limit_mb"}
ACTIVE = ["pending", "applying", "applied", "rolling_back"]
TERMINAL = ["committed", "rolled_back"]
#: The state ``GET /status`` answers for each phase on disk.
STATE_OF = {"pending": "pending", "applying": "in_progress", "applied": "in_progress", "rolling_back": "in_progress", "committed": "committed", "rolled_back": "rolled_back"}
#: The fields a hand-written state carries for its phase, as a start leaves them.
CONFIRMED_AT = datetime(2026, 10, 15, 22, 0, tzinfo=UTC)
BACKUP_CREATED_AT = datetime(2026, 10, 14, 9, 0, tzinfo=UTC)
FINISHED_AT = datetime(2026, 10, 15, 23, 0, tzinfo=UTC)
#: Everything older than a check's lifetime, as ``prune`` judges it with this ``now``.
FAR_AHEAD = timedelta(days=30)

# Lot B5c: the outcome of a restart, read with its ticket.
OUTCOME = f"{api.API}/outcome"
OUTCOME_MODULE = "backend.app.services.platform.instance_backup.outcome"
ROUTES_MODULE = "backend.app.api.v1.backup.restore"
#: Where the page sends the ticket, the only place the route reads it from.
TICKET_HEADER = "X-Restore-Ticket"
#: The ticket's file, spelled out here: ``test_backup_outcome.py`` pins the name.
TICKET_FILE_NAME = "outcome-ticket.json"
TICKET_TTL = timedelta(hours=1)
#: What ``secrets.token_urlsafe(32)`` gives: 32 random bytes in URL-safe base64, without padding.
A_TICKET = re.compile(r"[A-Za-z0-9_-]{43}")
#: The restart's answer: the restore's status and the ticket of its outcome (``RestoreRestartAccepted``).
RESTART_FIELDS = STATUS_FIELDS | {"outcome_ticket"}
TICKET_FIELDS = {"format", "sha256", "stage_id", "issued_at", "expires_at"}
#: The outcome, and nothing more: no name, no date, no version, no path.
OUTCOME_FIELDS = {"state", "reason", "waiting"}
OUTCOME_STATES = {"pending", "in_progress", "committed", "rolled_back"}
ROLLBACK_REASONS = ["first_start_failed", "swap_interrupted", "swap_failed", "stage_missing"]
#: The one answer to every ticket that does not open the outcome, whatever the reason.
NOT_FOUND = {"detail": {"code": "restore_outcome_not_found", "message": "No restore outcome for this ticket"}}
#: Another stage than the restore's.
OTHER_STAGE_ID = "fedcba9876543210fedcba9876543210"
BLOCKED_VARIABLE = "LIBREFOLIO_BLOCKED"
#: What a signed-in caller gets from a route the block refuses (``instance_block.py``), whole.
BLOCKED_ANSWER = {"detail": {"code": "instance_blocked", "message": "This instance is blocked by its hosting provider"}}
#: A session cookie, as the browser of an administrator still signed in sends it.
SIGNED_IN = {"Cookie": f"{SESSION_COOKIE_NAME}=an-administrator-session"}
LOG_CANARY = "b5c restore api test: canary through a logger of this name"


# =============================================================================
# Lot B3's names, imported when a test needs them
# =============================================================================


def product(name: str) -> ModuleType:
    """A module of the application, imported when a test needs it: this file collects before lot B3's modules exist,
    and each test that needs one fails on its own until it does."""
    return importlib.import_module(f"backend.app.{name}")


def apply_module() -> ModuleType:
    return product("services.platform.instance_backup.apply")


def restart_module() -> ModuleType:
    return product("services.platform.instance_backup.restart")


def state_path(root: Path) -> Path:
    """``.restore/restore.json``, as ``paths.restore_state_path`` gives it (lot B3)."""
    return product("services.platform.instance_backup.paths").restore_state_path(root)


def optional(module: str) -> ModuleType | None:
    """The module, or ``None`` while lot B3 has not written it."""
    try:
        return product(module)
    except ModuleNotFoundError:
        return None


class Answered:
    """The app of a test, wrapped: ``done`` turns true once the last byte of the answer has been sent. With ``look``,
    ``seen`` is what it found as the answer began: its status and headers on their way, nothing of its body yet."""

    def __init__(self, app: FastAPI, look: Callable[[], Any] | None = None) -> None:
        self.app = app
        self.done = False
        self.look = look
        self.seen: Any = None

    async def __call__(self, scope, receive, send) -> None:
        async def sending(message) -> None:
            if message.get("type") == "http.response.start" and self.look is not None:
                self.seen = self.look()
            await send(message)
            if message.get("type") == "http.response.body" and not message.get("more_body", False):
                self.done = True

        await self.app(scope, receive, sending)


class OsWithoutKill:
    """``os`` as ``restart`` sees it, ``kill`` recorded instead of sent: a restart goes through ``send_signal``."""

    def __init__(self, calls: list) -> None:
        self._calls = calls

    def __getattr__(self, name: str) -> Any:
        return getattr(os, name)

    def kill(self, pid: int, sig: int) -> None:
        self._calls.append((pid, sig))


@dataclass
class Signals:
    """The signals of a test: those ``restart.send_signal`` was asked to send, as (pid, signal, whether the answer had
    been sent then), and those tried with ``os.kill`` around it (there must be none)."""

    sent: list[tuple[int, int, bool | None]] = field(default_factory=list)
    around: list[tuple[int, int]] = field(default_factory=list)
    answered: Answered | None = None

    def send(self, pid: int, sig: int) -> None:
        self.sent.append((pid, sig, self.answered.done if self.answered is not None else None))


@pytest.fixture(autouse=True)
def signals(instance, monkeypatch) -> Signals:
    """Every test: ``apply`` (and ``outcome``, once lot B5c wrote it) use the data directory of the routes, and no signal
    can reach this process."""
    recorded = Signals()
    apply = optional("services.platform.instance_backup.apply")
    if apply is not None:
        monkeypatch.setattr(apply, "get_data_dir", lambda: instance.root, raising=False)
    outcome = optional("services.platform.instance_backup.outcome")
    if outcome is not None:
        monkeypatch.setattr(outcome, "get_data_dir", lambda: instance.root, raising=False)
    restart = optional("services.platform.instance_backup.restart")
    if restart is not None:
        monkeypatch.setattr(restart, "send_signal", recorded.send, raising=False)
        monkeypatch.setattr(restart, "os", OsWithoutKill(recorded.around), raising=False)
    return recorded


# =============================================================================
# Requests and states
# =============================================================================


async def confirm(stage_id: str, *, user: SimpleNamespace = B3_ADMIN) -> httpx.Response:
    return await api.call("POST", CONFIRM.format(stage_id=stage_id), user=user)


async def restore_status(*, user: SimpleNamespace = B3_ADMIN) -> httpx.Response:
    return await api.call("GET", STATUS, user=user)


async def cancel(*, user: SimpleNamespace = B3_ADMIN) -> httpx.Response:
    return await api.call("DELETE", PENDING, user=user)


async def restart(*, user: SimpleNamespace = B3_ADMIN, answered: Signals | None = None) -> httpx.Response:
    """``POST /restart``; with ``answered``, the app is wrapped so the signals it records say whether the answer had
    been sent."""
    app = Answered(api.restore_app(user))
    if answered is not None:
        answered.answered = app
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://in-process") as client:
        return await client.post(RESTART)


async def checked(archive) -> str:
    """``archive`` uploaded and checked through the routes, restorable: its stage id."""
    state = await api.ended(archive.path.read_bytes())
    assert state["status"] == "done" and state["report"]["restorable"], f"precondition: a restorable check: {state}"
    return state["stage_id"]


async def confirmed(archive) -> str:
    stage_id = await checked(archive)
    response = await confirm(stage_id)
    assert response.status_code == 202, f"precondition: the restore is confirmed: {api.shown(response)}"
    return stage_id


def write_state(root: Path, status: str, stage_id: str) -> bytes:
    """A restore in phase ``status`` for the stage ``stage_id``, as a start leaves it on disk: its bytes."""
    apply = apply_module()
    fields: dict[str, Any] = {}
    if status in ("applying", "applied", "rolling_back"):
        fields["swap"] = [apply.SwapEntry(name=name, live=True, staged=True) for name in ("sqlite", "custom-uploads", "broker_reports", "scenario_catalog")]
        fields["boot"] = apply.Boot(pid=999_999, started=1_760_000_000.0)
    if status in ("applied", "committed"):
        fields["applied_at"] = FINISHED_AT - timedelta(minutes=5)
    if status == "rolling_back":
        fields["reason"] = "first_start_failed"
    if status in TERMINAL:
        fields["finished_at"] = FINISHED_AT
    if status == "rolled_back":
        fields["reason"] = "first_start_failed"
    if status == "committed":
        fields["session_version"] = int(FINISHED_AT.timestamp() * 1000)
    state = apply.RestoreState(
        status=status,
        stage_id=stage_id,
        data_dir=str(root.resolve()),
        confirmed_at=CONFIRMED_AT,
        confirmed_by="b3-admin",
        backup_created_at=BACKUP_CREATED_AT,
        backup_app_version="v1.2.0",
        action="upgrade",
        **fields,
    )
    path = state_path(root)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_text(state.model_dump_json(), encoding="utf-8")
    path.chmod(0o600)
    return path.read_bytes()


def rewrite_report(root: Path, stage_id: str, **changes: Any) -> None:
    """The report of a check, some of its fields changed, written back where the check left it."""
    path = stage_dir(root, stage_id) / "report.json"
    report: StagingReport = read_report(root, stage_id).model_copy(update=changes)
    path.write_text(report.model_dump_json(indent=2), encoding="utf-8")


def no_path_in(response: httpx.Response, root: Path) -> None:
    for form in (str(root), str(root.resolve()), ".restore"):
        assert form not in response.text, f"no path in the answer: {response.text}"


# =============================================================================
# The outcome of a restart (lot B5c), read as the page reads it
# =============================================================================


def outcome_module() -> ModuleType:
    return product("services.platform.instance_backup.outcome")


def ticket_path(root: Path) -> Path:
    """``.restore/outcome-ticket.json``, as ``paths.outcome_ticket_path`` gives it (lot B5c)."""
    module = product("services.platform.instance_backup.paths")
    assert hasattr(module, "outcome_ticket_path"), "[new] paths.outcome_ticket_path does not exist yet: lot B5c adds it"
    return module.outcome_ticket_path(root)


def hash_of(ticket: str) -> str:
    """What the ticket's file keeps of it: its SHA-256, in hexadecimal."""
    return hashlib.sha256(ticket.encode("ascii")).hexdigest()


def no_store(response: httpx.Response) -> bool:
    """Whether ``Cache-Control`` says ``no-store``: no cache along the way keeps the answer."""
    return "no-store" in {directive.strip().lower() for directive in response.headers.get("cache-control", "").split(",")}


def same_answer(response: httpx.Response, other: httpx.Response) -> bool:
    """Whether two answers cannot be told apart: status, headers and bytes."""
    return (response.status_code, response.headers.multi_items(), response.content) == (other.status_code, other.headers.multi_items(), other.content)


class NoDatabase:
    """The database session of the apps without an administrator: nothing may reach it, and anything that does fails
    the test (the special names a library may probe are left to Python)."""

    def __getattr__(self, name: str) -> Any:
        if name.startswith("__"):
            raise AttributeError(name)
        raise AssertionError(f"the database was reached: session.{name}")


def no_database() -> NoDatabase:
    return NoDatabase()


def anonymous_app() -> FastAPI:
    """``backup_router`` under ``/api/v1`` with nobody signed in: ``get_current_user`` is the real one, which answers 401
    to a request without a session cookie before it looks for a database."""
    app = FastAPI()
    app.include_router(backup_router, prefix="/api/v1")
    app.dependency_overrides[get_session_generator] = no_database
    return app


def blocked_app() -> FastAPI:
    """``backup_router`` behind ``refuse_when_blocked``, as ``router.py`` mounts every route of ``/api/v1``; nobody signed
    in through FastAPI, no database."""
    v1 = APIRouter(dependencies=[Depends(refuse_when_blocked)])
    v1.include_router(backup_router)
    app = FastAPI()
    app.include_router(v1, prefix="/api/v1")
    app.dependency_overrides[get_session_generator] = no_database
    return app


async def send(app: Any, method: str, path: str, **kwargs: Any) -> httpx.Response:
    """A request to ``app`` (an app of the test, or one wrapped), through the in-process transport."""
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://in-process") as client:
        return await client.request(method, path, **kwargs)


async def get_outcome(ticket: str | None = None, *, params: dict[str, str] | None = None, app: FastAPI | None = None) -> httpx.Response:
    """``GET /outcome`` as the page sends it after the restart: no cookie at all, the ticket in ``X-Restore-Ticket``
    (``None``: no header), ``params`` in the query."""
    headers = {} if ticket is None else {TICKET_HEADER: ticket}
    return await send(app or anonymous_app(), "GET", OUTCOME, headers=headers, params=params)


async def restarted() -> str:
    """The restart of the restore pending: the ticket its answer carries."""
    response = await restart()
    assert response.status_code == 202, f"precondition: the restart is accepted: {api.shown(response)}"
    body = response.json()
    assert "outcome_ticket" in body, f"[new] the restart's answer carries the ticket of its outcome (RestoreRestartAccepted, lot B5c): {sorted(body)}"
    return body["outcome_ticket"]


async def restart_requested(root: Path, stage_id: str = api.UNKNOWN_ID) -> str:
    """A restore of ``stage_id`` waiting (its state as a confirmation writes it; the restart reads nothing else) and its
    restart requested: the ticket of the answer."""
    write_state(root, "pending", stage_id)
    return await restarted()


def issued(root: Path, stage_id: str = api.UNKNOWN_ID, *, now: datetime | None = None) -> str:
    """A ticket issued by ``outcome.issue_ticket``, as the restart before a start issued it: for the phases only a start
    reaches."""
    return outcome_module().issue_ticket(stage_id, data_dir=root, now=now)


def left_waiting(root: Path, waiting: str) -> None:
    """The pending restore as a start that did not apply it leaves it: ``waiting`` recorded, as the start writes it."""
    path = state_path(root)
    record = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(json.dumps({**record, "waiting": waiting}), encoding="utf-8")


def file_bytes(path: Path) -> bytes | None:
    return path.read_bytes() if os.path.lexists(path) else None


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


# =============================================================================
# (a) A confirmation
# =============================================================================


@pytest.mark.asyncio
async def test_a_confirmed_restore_waits_for_the_next_start_with_its_state_on_disk(instance, head_archive):
    print_section("POST /backup/restore/stage/{id}/confirm")
    root = instance.root
    stage_id = await checked(head_archive)
    report = read_report(root, stage_id)
    copy_before = api.tree(stage_dir(root, stage_id))
    started = datetime.now(UTC)
    response = await confirm(stage_id)
    ended = datetime.now(UTC)
    assert response.status_code == 202, f"a checked, restorable copy is confirmed: {api.shown(response)}"
    body = response.json()
    assert set(body) == STATUS_FIELDS, f"a RestoreStatus, nothing more: {sorted(body)}"
    assert (body["state"], body["stage_id"], body["confirmed_by"], body["action"]) == ("pending", stage_id, B3_ADMIN.username, report.action), f"pending, confirmed by the administrator who asked: {body}"
    assert (api.moment(body["backup_created_at"]), body["backup_app_version"]) == (report.backup.created_at, report.backup.app_version), f"the backup, as the report says it: {body}"
    assert (body["finished_at"], body["reason"], body["waiting"]) == (None, None, None), f"nothing of a start yet: {body}"
    path = state_path(root)
    assert path == restore_dir(root) / "restore.json", f"the state of the restore is .restore/restore.json: {path}"
    if os.name != "nt":
        assert stat.S_IMODE(path.lstat().st_mode) == 0o600, f"the state is readable by its owner only: {oct(stat.S_IMODE(path.lstat().st_mode))}"
    state = json.loads(path.read_text(encoding="utf-8"))
    expected = {"format": 1, "status": "pending", "stage_id": stage_id, "data_dir": str(root.resolve()), "confirmed_by": B3_ADMIN.username, "backup_app_version": report.backup.app_version, "action": report.action}
    assert {key: state.get(key) for key in expected} == expected, f"the state written: {state}"
    nothing_yet = {key: state.get(key) for key in ("swap", "boot", "applied_at", "finished_at", "reason", "waiting", "session_version")}
    assert nothing_yet == {"swap": [], "boot": None, "applied_at": None, "finished_at": None, "reason": None, "waiting": None, "session_version": None}, f"nothing of a start yet: {nothing_yet}"
    assert api.moment(state["backup_created_at"]) == report.backup.created_at, f"backup_created_at from the report: {state['backup_created_at']}"
    assert started <= api.moment(state["confirmed_at"]) <= ended and api.moment(body["confirmed_at"]) == api.moment(state["confirmed_at"]), f"confirmed now: {state['confirmed_at']}"
    assert api.tree(stage_dir(root, stage_id)) == copy_before and check_state_path(root, stage_id).is_file(), "the copy and its check are kept as they were"
    status = await restore_status()
    assert (status.status_code, status.json()) == (200, body), f"GET /status says the same: {api.shown(status)}"
    print_success(f"202 pending, restore.json 0600, confirmed by {B3_ADMIN.username}")


@pytest.mark.asyncio
async def test_a_second_confirmation_is_refused_while_a_restore_is_pending(instance, head_archive):
    """(a) The same copy again, or another one: 409 ``restore_already_pending``, the state as it was."""
    root = instance.root
    first = await confirmed(head_archive)
    before = state_path(root).read_bytes()
    second = await checked(head_archive)
    answers = {name: api.code(await confirm(stage_id)) for name, stage_id in (("the same copy", first), ("another copy", second))}
    assert answers == dict.fromkeys(answers, (409, "restore_already_pending")), f"one restore at a time: {answers}"
    assert state_path(root).read_bytes() == before, "the pending restore is unchanged"
    print_success("409 restore_already_pending, twice")


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ACTIVE[1:])
async def test_no_confirmation_while_a_restore_is_being_applied(instance, head_archive, phase):
    """(a) A restore being applied (or undone) is ACTIVE too: no other may be confirmed meanwhile."""
    root = instance.root
    applying = await checked(head_archive)
    before = write_state(root, phase, applying)
    other = await checked(head_archive)
    response = await confirm(other)
    assert api.code(response) == (409, "restore_already_pending"), f"{phase}: 409 restore_already_pending: {api.shown(response)}"
    assert state_path(root).read_bytes() == before, f"{phase}: the restore's state is unchanged"
    print_success(f"{phase}: 409 restore_already_pending")


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", TERMINAL)
async def test_a_finished_restore_does_not_stop_the_next_confirmation(instance, head_archive, phase):
    """(a) A committed or rolled back restore is over: a new one can be confirmed, its state replacing the old."""
    root = instance.root
    write_state(root, phase, await checked(head_archive))
    stage_id = await checked(head_archive)
    response = await confirm(stage_id)
    assert response.status_code == 202, f"after a {phase} restore, a new one is confirmed: {api.shown(response)}"
    state = json.loads(state_path(root).read_text(encoding="utf-8"))
    assert (state["status"], state["stage_id"]) == ("pending", stage_id), f"the new restore's state: {state}"
    print_success(f"{phase}, then 202 pending")


# =============================================================================
# (b) The refusals of a confirmation
# =============================================================================


@dataclass
class Setting:
    """What a refusal's case may need to prepare its stage."""

    root: Path
    instance: Any
    archive: Any
    databases: Any
    tmp_path: Path
    monkeypatch: pytest.MonkeyPatch


async def no_such_check(s: Setting) -> str:
    return api.UNKNOWN_ID


async def copy_database_gone(s: Setting) -> str:
    stage_id = await checked(s.archive)
    (stage_dir(s.root, stage_id) / "data" / "sqlite" / "app.db").unlink()
    return stage_id


async def copy_folder_a_link(s: Setting) -> str:
    """A folder of the copy replaced by a link: the copy is not one a restore may move into place."""
    stage_id = await checked(s.archive)
    folder = stage_dir(s.root, stage_id) / "data" / "custom-uploads"
    elsewhere = s.tmp_path / "elsewhere-uploads"
    folder.rename(elsewhere)
    folder.symlink_to(elsewhere, target_is_directory=True)
    return stage_id


async def report_gone(s: Setting) -> str:
    stage_id = await checked(s.archive)
    (stage_dir(s.root, stage_id) / "report.json").unlink()
    return stage_id


async def check_running(s: Setting) -> str:
    s.instance.threads.hold = True
    return (await api.started(s.archive.path.read_bytes()))["stage_id"]


async def blocked_report(s: Setting) -> str:
    source = s.tmp_path / "source"
    archive = cases.build_into(cases.make_data_dir(source / "data", s.databases.head, accounts=cases.WITHOUT_ADMINISTRATOR), source / "work")
    state = await api.ended(archive.path.read_bytes())
    assert state["status"] == "done" and state["report"]["blockers"] == ["no_administrator"], f"precondition: a check whose report has a blocker: {state}"
    return state["stage_id"]


async def failed_check(s: Setting) -> str:
    state = await api.ended(b"these are not the bytes of a backup")
    assert (state["status"], state["error_code"]) == ("failed", "not_a_backup"), f"precondition: a failed check: {state}"
    return state["stage_id"]


async def expired(s: Setting) -> str:
    stage_id = await checked(s.archive)
    now = datetime.now(UTC)
    rewrite_report(s.root, stage_id, staged_at=now - STAGE_LIFETIME - timedelta(minutes=1), expires_at=now - timedelta(minutes=1))
    return stage_id


async def checked_before_an_update(s: Setting) -> str:
    """The report says another head than this LibreFolio's: it was checked before an update."""
    stage_id = await checked(s.archive)
    rewrite_report(s.root, stage_id, head_revision=cases.OLDER)
    return stage_id


async def head_moved(s: Setting) -> str:
    """This LibreFolio's head, as ``apply`` reads it, is no longer the report's."""
    stage_id = await checked(s.archive)
    s.monkeypatch.setattr(apply_module(), "alembic_head_revision", lambda: "999_from_an_update")
    return stage_id


REFUSALS = [
    pytest.param(no_such_check, 404, "restore_stage_not_found", id="no-such-check"),
    pytest.param(copy_database_gone, 404, "restore_stage_not_found", id="copy-database-gone"),
    pytest.param(copy_folder_a_link, 404, "restore_stage_not_found", id="copy-folder-a-link", marks=pytest.mark.skipif(os.name == "nt", reason="symbolic links need a privilege on Windows")),
    pytest.param(report_gone, 404, "restore_stage_not_found", id="report-gone"),
    pytest.param(check_running, 409, "restore_stage_running", id="check-running"),
    pytest.param(blocked_report, 409, "restore_not_restorable", id="report-with-a-blocker"),
    pytest.param(failed_check, 409, "restore_not_restorable", id="failed-check"),
    pytest.param(expired, 410, "restore_stage_expired", id="expired"),
    pytest.param(checked_before_an_update, 409, "restore_stage_outdated", id="report-of-another-head"),
    pytest.param(head_moved, 409, "restore_stage_outdated", id="head-moved"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("prepare", "status_code", "error"), REFUSALS)
async def test_a_confirmation_that_cannot_be_made_is_refused_with_its_code(instance, head_archive, databases, tmp_path, monkeypatch, prepare, status_code, error):
    """(b) Each refusal of §6, with its status and code; no restore written, the copy as it was, no path said."""
    root = instance.root
    stage_id = await prepare(Setting(root, instance, head_archive, databases, tmp_path, monkeypatch))
    copy_before = api.tree(stage_dir(root, stage_id)) if stage_dir(root, stage_id).is_dir() else None
    response = await confirm(stage_id)
    assert api.code(response) == (status_code, error), f"{status_code} {error} expected: {api.shown(response)}"
    assert not state_path(root).exists(), f"{error}: no restore written: {api.files_in(restore_dir(root))}"
    if copy_before is not None:
        assert api.tree(stage_dir(root, stage_id)) == copy_before, f"{error}: the copy is left as it was"
    no_path_in(response, root)
    instance.threads.run_held()
    print_success(f"{status_code} {error}")


@pytest.mark.asyncio
@pytest.mark.skipif(os.name == "nt", reason="symbolic links need a privilege on Windows")
async def test_a_state_file_that_is_a_link_refuses_the_confirmation_never_written_through(instance, head_archive, tmp_path):
    """(a) B-33 §1 (replaced by the new state before B-33): a ``restore.json`` that is a link is a state that cannot be
    read (``not_a_file``): a restore may have stopped half way behind it. The confirmation is 500
    ``restore_state_unreadable``; the link left as it is, its target never written."""
    root = instance.root
    stage_id = await checked(head_archive)
    elsewhere = tmp_path / "elsewhere.json"
    elsewhere.write_text("a file a link points to", encoding="utf-8")
    state_path(root).symlink_to(elsewhere)
    response = await confirm(stage_id)
    assert api.code(response) == (500, "restore_state_unreadable"), f"refused: 500 restore_state_unreadable, not {api.shown(response)}"
    assert state_path(root).is_symlink() and os.readlink(state_path(root)) == str(elsewhere), "the link left as it is"
    assert elsewhere.read_text(encoding="utf-8") == "a file a link points to", "nothing written through the link"
    print_success("restore.json a link: 500 restore_state_unreadable, link and target untouched")


@pytest.mark.asyncio
async def test_a_head_that_cannot_be_read_does_not_refuse_a_confirmation(instance, head_archive, monkeypatch):
    """(b) ``restore_stage_outdated`` is judged only when ``apply.alembic_head_revision`` gives a revision."""
    stage_id = await checked(head_archive)
    monkeypatch.setattr(apply_module(), "alembic_head_revision", lambda: None)
    response = await confirm(stage_id)
    assert response.status_code == 202, f"no head to compare with: confirmed: {api.shown(response)}"
    print_success("head unknown → 202")


#: A folder of the restore replaced once the check ended, and the answer of a confirmation: ``.restore`` is where it
#: writes, checked first (500); behind ``checks/`` or ``stage/``, the check or its copy is simply not found (404).
NOT_PLAIN = [
    pytest.param(".restore", "link", 500, "restore_folder_unusable", id="restore-a-link"),
    pytest.param(".restore", "file", 500, "restore_folder_unusable", id="restore-a-file"),
    pytest.param("checks", "link", 404, "restore_stage_not_found", id="checks-a-link"),
    pytest.param("stage", "link", 404, "restore_stage_not_found", id="stage-a-link"),
]


@pytest.mark.asyncio
@pytest.mark.skipif(os.name == "nt", reason="symbolic links need a privilege on Windows")
@pytest.mark.parametrize(("name", "replaced_by", "status_code", "error"), NOT_PLAIN)
async def test_a_confirmation_never_writes_through_a_restore_folder_that_is_not_a_plain_folder(instance, head_archive, tmp_path, name, replaced_by, status_code, error):
    """(b) The folder moved aside (behind a link in its place, or a file in place of ``.restore``): refused with its code;
    nothing written where the folder went, nor anywhere in the data directory (no state, no lock)."""
    root = instance.root
    stage_id = await checked(head_archive)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    if replaced_by == "link":
        moved = api.moved_behind_a_link(root, name, elsewhere)
    else:
        moved = elsewhere / "restore"
        restore_dir(root).rename(moved)
        restore_dir(root).write_bytes(b"a file where the restore's folder should be")
    before = (api.tree(moved), api.tree(root))
    response = await confirm(stage_id)
    assert api.code(response) == (status_code, error), f"{name} a {replaced_by}: {status_code} {error}: {api.shown(response)}"
    after = (api.tree(moved), api.tree(root))
    assert after == before, f"{name} a {replaced_by}: nothing written: {cases.changed(before[0], after[0]) + cases.changed(before[1], after[1])}"
    no_path_in(response, root)
    print_success(f"{name} a {replaced_by}: {status_code} {error}")


#: B-31: what a confirmation and a cancel that fail answer and log.
NO_SPACE_TO_CONFIRM = "Not enough free space to confirm the restore"
CONFIRM_FAILED = "The restore could not be confirmed: the server's log has the cause"
CONFIRM_NO_SPACE_WARNING = "A restore could not be confirmed: not enough free space"
CONFIRM_ERROR = "A restore could not be confirmed"
CANCEL_FAILED = "The restore could not be cancelled: the server's log has the cause"
CANCEL_ERROR = "A pending restore could not be cancelled"
COPY_LEFT_WARNING = "The copy of a cancelled restore could not be removed: it goes when its check expires"
#: B-31: the steps of ``apply`` a failure is put in. A confirmation: its lock (``apply._apply_lock``, refused as it is
#: taken) and the write of its state (``apply._write_state``, its first call: the confirmation's own). A cancel: its lock,
#: and the removal of its state file (``apply.restore_state_path``'s ``unlink``), both before the restore is dropped.
CONFIRM_STEPS = ["its-lock", "its-state"]
CANCEL_STEPS = ["its-lock", "its-state-file"]
#: B-31: failures that are not a lack of space.
OTHER_FAILURES = [pytest.param(errno.EACCES, id="EACCES"), pytest.param(errno.EIO, id="EIO")]


def caused_by_a_full_disk() -> OSError:
    """Another error of the file system whose cause is a full disk, as a failure wrapped on its way up leaves it."""
    error = OSError(errno.EIO, os.strerror(errno.EIO))
    error.__cause__ = OSError(errno.ENOSPC, os.strerror(errno.ENOSPC))
    return error


#: B-31: a full disk or a quota, the failure itself or the cause of another (``out_of_space`` walks the chain).
NO_SPACE_FAILURES = [
    pytest.param(lambda: OSError(errno.ENOSPC, os.strerror(errno.ENOSPC)), id="ENOSPC"),
    pytest.param(lambda: OSError(api.EDQUOT, os.strerror(api.EDQUOT)), id="EDQUOT", marks=api.needs_edquot),
    pytest.param(caused_by_a_full_disk, id="EIO-caused-by-ENOSPC"),
]
#: The system's words of every failure above: never in an answer.
SYSTEM_WORDS = tuple(os.strerror(code) for code in (errno.ENOSPC, api.EDQUOT, errno.EIO, errno.EACCES) if code is not None)


class Failure:
    """A failure put in one step of ``apply``: ``error()`` raised the first time the step is reached, once, unless
    ``cured``; what it raised in ``raised``."""

    def __init__(self, error: Callable[[], OSError]) -> None:
        self.error = error
        self.raised: list[OSError] = []
        self.cured = False

    def due(self) -> bool:
        """Whether the step fails if it is reached now: not cured, and nothing raised yet."""
        return not self.cured and not self.raised

    def fail(self) -> None:
        raised = self.error()
        self.raised.append(raised)
        raise raised


def _lock_refused(apply: ModuleType, failure: Failure) -> Callable[[Path], Any]:
    """``apply._apply_lock``, refused as it is taken while the failure is due; otherwise the real lock."""
    real_lock = apply._apply_lock

    @contextlib.contextmanager
    def apply_lock(data_dir: Path) -> Iterator[None]:
        if failure.due():
            failure.fail()
        with real_lock(data_dir):
            yield

    return apply_lock


def _state_not_written(apply: ModuleType, failure: Failure) -> Callable[[Path, Any], None]:
    """``apply._write_state``, failing while the failure is due (the confirmation's own write: its first); otherwise the
    real write."""
    real_write = apply._write_state

    def write_state(data_dir: Path, state: Any) -> None:
        if failure.due():
            failure.fail()
        real_write(data_dir, state)

    return write_state


def _state_file_that_stays(apply: ModuleType, failure: Failure) -> Callable[[Path], Path]:
    """``apply.restore_state_path``, while the failure is due a path whose removal fails, everything else of it the real
    path's; otherwise the real path."""
    real_path = apply.restore_state_path

    class StateFileThatStays(type(Path())):
        def unlink(self, missing_ok: bool = False) -> None:
            failure.fail()

    def restore_state_path(data_dir: Path) -> Path:
        path = real_path(data_dir)
        return StateFileThatStays(path) if failure.due() else path

    return restore_state_path


#: Each step a failure is put in: the name of ``apply`` replaced, and what replaces it.
FAILING = {"its-lock": ("_apply_lock", _lock_refused), "its-state": ("_write_state", _state_not_written), "its-state-file": ("restore_state_path", _state_file_that_stays)}


def fail_at(monkeypatch: pytest.MonkeyPatch, step: str, error: Callable[[], OSError]) -> Failure:
    """``step`` of ``apply`` raises ``error()`` the next time it is reached, once, unless ``cured``; everything else is the
    module's own: its lock refused as it is taken, the first write of its state, or the removal of its state file."""
    apply = apply_module()
    failure = Failure(error)
    name, failing = FAILING[step]
    monkeypatch.setattr(apply, name, failing(apply, failure))
    return failure


def nothing_shown(response: httpx.Response, root: Path) -> None:
    """Neither a path nor the system's words in the answer."""
    no_path_in(response, root)
    shown = [words for words in SYSTEM_WORDS if words in response.text]
    assert shown == [], f"the system's words stay in the server: {shown} in {response.text}"


@pytest.mark.asyncio
@pytest.mark.parametrize("step", CONFIRM_STEPS)
@pytest.mark.parametrize("error", NO_SPACE_FAILURES)
async def test_a_confirmation_on_a_full_disk_is_507_and_confirms_nothing(instance, head_archive, monkeypatch, step, error):
    """(b) B-31: a full disk or a quota while the confirmation takes its lock or writes its state, itself or as the cause
    of another error: 507 ``backup_no_space``, «Not enough free space to confirm the restore», never the plain 500 of an
    error escaping the route; one WARNING, «A restore could not be confirmed: not enough free space». Nothing confirmed:
    the status as before, no state file; the check and its copy kept, so the same confirmation, the failure gone, is
    202. Barrier: the confirmation failed at that step, once."""
    root = instance.root
    stage_id = await checked(head_archive)
    before = (await restore_status()).json()
    failure = fail_at(monkeypatch, step, error)

    with capture_logs() as events:
        response = await confirm(stage_id)

    assert len(failure.raised) == 1, f"barrier: the confirmation failed at {step}, once: {failure.raised}"
    assert api.refusal(response) == (507, "backup_no_space", NO_SPACE_TO_CONFIRM), f"a full disk at {step}: 507 backup_no_space, not {api.shown(response)}"
    assert [(event.get("log_level"), event.get("event")) for event in api.loud(events)] == [("warning", CONFIRM_NO_SPACE_WARNING)], f"one warning: {api.loud(events)}"
    assert ((await restore_status()).json(), os.path.lexists(state_path(root))) == (before, False), "nothing confirmed: the status as before, no state file"
    nothing_shown(response, root)
    failure.cured = True
    again = await confirm(stage_id)
    assert again.status_code == 202, f"room again: the same confirmation is 202 (the check and its copy kept), not {api.shown(again)}"
    print_success(f"{step}: 507 backup_no_space, nothing confirmed, then 202")


@pytest.mark.asyncio
@pytest.mark.parametrize("step", CONFIRM_STEPS)
@pytest.mark.parametrize("error_number", OTHER_FAILURES)
async def test_a_confirmation_that_fails_otherwise_is_500_restore_confirm_failed_and_confirms_nothing(instance, head_archive, monkeypatch, step, error_number):
    """(b) B-31: any other ``OSError`` while the confirmation takes its lock or writes its state (EACCES, EIO): 500
    ``restore_confirm_failed``, «The restore could not be confirmed: the server's log has the cause»; one ERROR, «A
    restore could not be confirmed», whose ``error`` is the exception's type and its system's words, which stay out of
    the answer with any path. Nothing confirmed, and the same confirmation, the failure gone, is 202. Barrier: the
    confirmation failed at that step, once."""
    root = instance.root
    stage_id = await checked(head_archive)
    before = (await restore_status()).json()
    failure = fail_at(monkeypatch, step, lambda: OSError(error_number, os.strerror(error_number)))

    with capture_logs() as events:
        response = await confirm(stage_id)

    assert len(failure.raised) == 1, f"barrier: the confirmation failed at {step}, once: {failure.raised}"
    raised = failure.raised[0]
    assert api.refusal(response) == (500, "restore_confirm_failed", CONFIRM_FAILED), f"{errno.errorcode[error_number]} at {step}: 500 restore_confirm_failed, not {api.shown(response)}"
    logged = [(event.get("log_level"), event.get("event"), event.get("error")) for event in api.loud(events)]
    assert logged == [("error", CONFIRM_ERROR, f"{type(raised).__name__}: {raised.strerror}")], f"one error, with the type and the system's words: {api.loud(events)}"
    assert ((await restore_status()).json(), os.path.lexists(state_path(root))) == (before, False), "nothing confirmed: the status as before, no state file"
    nothing_shown(response, root)
    failure.cured = True
    again = await confirm(stage_id)
    assert again.status_code == 202, f"the failure gone: the same confirmation is 202, not {api.shown(again)}"
    print_success(f"{errno.errorcode[error_number]} at {step}: 500 restore_confirm_failed, nothing confirmed, then 202")


# =============================================================================
# (c) GET /status
# =============================================================================


@pytest.mark.asyncio
async def test_without_a_restore_the_status_is_none_and_nothing_is_created(instance):
    print_section("GET /backup/restore/status")
    response = await restore_status()
    assert response.status_code == 200, api.shown(response)
    assert response.json() == {**dict.fromkeys(STATUS_FIELDS), "state": "none", "upload_limit_mb": 0}, f"none, the upload limit of a self-hosted instance (0), every other field null: {response.json()}"
    assert not restore_dir(instance.root).exists(), "a status read creates nothing, not even .restore"
    print_success("none, nothing created")


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ACTIVE + TERMINAL)
async def test_the_status_of_each_phase_is_what_its_state_records(instance, phase):
    """(c) Applying, applied and rolling back are ``in_progress``; each field as recorded."""
    write_state(instance.root, phase, api.UNKNOWN_ID)
    state = json.loads(state_path(instance.root).read_text(encoding="utf-8"))
    response = await restore_status()
    assert response.status_code == 200, api.shown(response)
    body = response.json()
    assert body["state"] == STATE_OF[phase], f"{phase} reads as {STATE_OF[phase]}: {body}"
    for key in ("stage_id", "confirmed_by", "backup_app_version", "action", "reason", "waiting"):
        assert body[key] == state.get(key), f"{phase}: {key} as recorded: {body[key]!r}, {state.get(key)!r}"
    for key in ("confirmed_at", "backup_created_at", "finished_at"):
        assert (body[key] and api.moment(body[key])) == (state.get(key) and api.moment(state[key])), f"{phase}: {key} as recorded"
    print_success(f"{phase} → {body['state']}")


#: Why a start left a restore pending (contract §2; §10: another server process serves the data directory; §11, P7: the
#: hosting provider blocked the instance).
WAIT_REASONS = ["backup_running", "other_data_directory", "server_running", "instance_blocked"]


@pytest.mark.asyncio
@pytest.mark.parametrize("waiting", WAIT_REASONS)
async def test_a_restore_waiting_says_why(instance, waiting):
    """(c) A pending restore a start could not apply says why: ``waiting``. ``instance_blocked`` (§11) too, read here on
    an instance that is not blocked itself: a blocked one answers none of the restore routes. The reason is written in
    the state file as a start writes it, whatever the models of this LibreFolio accept: the answer is under test."""
    write_state(instance.root, "pending", api.UNKNOWN_ID)
    path = state_path(instance.root)
    record = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(json.dumps({**record, "waiting": waiting}), encoding="utf-8")
    response = await restore_status()
    assert response.status_code == 200, f"{waiting}: the status answers: {api.shown(response)}"
    body = response.json()
    assert (body["state"], body["waiting"]) == ("pending", waiting), f"pending, waiting {waiting}: {body}"
    print_success(f"pending, waiting {waiting}")


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["a-link", "unreadable"])
async def test_a_state_file_that_is_a_link_or_unreadable_is_a_500_never_followed(instance, tmp_path, case):
    """(c) A ``restore.json`` that is a link is never followed, even to a valid state. B-33 §1 (``none`` before B-33):
    it, and one whose content is no state, cannot be read: 500 ``restore_state_unreadable``, nothing changed."""
    root = instance.root
    if case == "a-link":
        valid = write_state(root, "pending", api.UNKNOWN_ID)
        elsewhere = tmp_path / "elsewhere.json"
        elsewhere.write_bytes(valid)
        state_path(root).unlink()
        state_path(root).symlink_to(elsewhere)
    else:
        restore_dir(root).mkdir(mode=0o700)
        state_path(root).write_text("{not a state", encoding="utf-8")
    before = api.tree(root)
    response = await restore_status()
    assert api.refusal(response) == (500, "restore_state_unreadable", STATE_UNREADABLE), f"{case}: 500 restore_state_unreadable, not {api.shown(response)}"
    assert api.tree(root) == before, f"{case}: nothing changed: {cases.changed(before, api.tree(root))}"
    print_success(f"{case}: 500 restore_state_unreadable")


def broken_state(root: Path, case: str) -> None:
    """A state file as a start writes it, then one of its values changed into one no restore can hold (§10)."""
    write_state(root, "applying", api.UNKNOWN_ID)
    path = state_path(root)
    record = json.loads(path.read_text(encoding="utf-8"))
    if case == "stage-id-a-path":
        record["stage_id"] = "../../" + "0" * 26
    elif case == "stage-id-uppercase":
        record["stage_id"] = api.UNKNOWN_ID.upper()
    elif case == "stage-id-31-digits":
        record["stage_id"] = api.UNKNOWN_ID[:31]
    elif case == "stage-id-trailing-newline":
        # ``$`` of Python's re matches before a final line feed; the pattern must not.
        record["stage_id"] = api.UNKNOWN_ID + "\n"
    elif case == "swap-entry-secrets":
        record["swap"][0]["name"] = "secrets"
    else:
        record["swap"][0]["name"] = "../sqlite"
    path.write_text(json.dumps(record), encoding="utf-8")


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["stage-id-a-path", "stage-id-uppercase", "stage-id-31-digits", "stage-id-trailing-newline", "swap-entry-secrets", "swap-entry-a-path"])
async def test_a_state_no_restore_can_hold_is_a_500_and_nothing_it_names_is_followed(instance, case):
    """(c) §10, a strict state: its ``stage_id`` 32 lowercase hexadecimal digits, each swap entry one of the swapped
    folders. A state file that breaks either is unreadable: an error logged, and nothing it names is ever followed.
    B-33 §1 (``none`` before B-33): 500 ``restore_state_unreadable``."""
    root = instance.root
    broken_state(root, case)
    before = api.tree(root)
    with capture_logs() as events:
        response = await restore_status()
    assert api.refusal(response) == (500, "restore_state_unreadable", STATE_UNREADABLE), f"{case}: 500 restore_state_unreadable, not {api.shown(response)}"
    errors = [event for event in events if event.get("log_level") == "error"]
    assert errors, f"{case}: the unreadable state is logged as an error: {events}"
    assert api.tree(root) == before, f"{case}: nothing created or changed: {cases.changed(before, api.tree(root))}"
    print_success(f"{case}: 500 restore_state_unreadable, logged")


# =============================================================================
# (d) DELETE /pending
# =============================================================================


@pytest.mark.asyncio
async def test_a_pending_restore_is_cancelled_with_its_checked_copy(instance, head_archive):
    """(d) B-17 (lot B5c): the cancel drops the checked copy and its check, as the command line's ``pending --cancel``
    does (``cancel_restore(drop_copy=True)``): nothing of the restore is left to poll or to confirm again. Another check
    is not the restore's: it stays as it was."""
    print_section("DELETE /backup/restore/pending")
    root = instance.root
    stage_id = await confirmed(head_archive)
    other = await checked(head_archive)
    other_before = (api.tree(stage_dir(root, other)), check_state_path(root, other).read_bytes())
    response = await cancel()
    assert (response.status_code, response.content) == (204, b""), f"cancelled: {api.shown(response)}"
    assert not state_path(root).exists(), "the state of the restore is removed"
    left = [name for name, path in (("the copy", stage_dir(root, stage_id)), ("its check", check_state_path(root, stage_id))) if os.path.lexists(path)]
    assert left == [], f"B-17: the checked copy and its check are dropped with the restore: {left} left"
    assert (api.tree(stage_dir(root, other)), check_state_path(root, other).read_bytes()) == other_before, "another check and its copy are kept as they were"
    assert (await restore_status()).json()["state"] == "none", "no restore any more"
    polled, again = await api.poll(stage_id), await confirm(stage_id)
    assert (api.code(polled), api.code(again)) == ((404, "restore_stage_not_found"), (404, "restore_stage_not_found")), f"nothing left to poll or to confirm again: {api.shown(polled)} / {api.shown(again)}"
    print_success("204, the copy and its check dropped; 404 to confirm again")


@pytest.mark.asyncio
async def test_a_cancel_drops_the_ticket_of_the_restart(instance):
    """(d) Lot B5c: the restore no longer waits, and the ticket of its restart goes with it (``cancel_restore`` drops it):
    the outcome answers the 404 of a ticket that opens nothing."""
    root = instance.root
    ticket = await restart_requested(root)
    response = await cancel()
    assert response.status_code == 204, f"cancelled: {api.shown(response)}"
    assert not os.path.lexists(ticket_path(root)), "the ticket's file is removed"
    after = await get_outcome(ticket)
    assert (after.status_code, after.json()) == (404, NOT_FOUND), f"the ticket opens nothing: {api.shown(after)}"
    print_success("204, the ticket dropped")


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ["applied", *TERMINAL])
async def test_a_cancel_refused_keeps_the_ticket_of_the_restart(instance, phase):
    """(d) A restore being applied or finished cannot be cancelled: 404, and the ticket its restart gave stays for the
    outcome the page waits for."""
    root = instance.root
    write_state(root, phase, api.UNKNOWN_ID)
    issued(root)
    before = ticket_path(root).read_bytes()
    response = await cancel()
    assert api.code(response) == (404, "restore_not_pending"), f"{phase}: 404 restore_not_pending: {api.shown(response)}"
    assert ticket_path(root).read_bytes() == before, f"{phase}: the ticket kept as it was"
    print_success(f"{phase}: 404, the ticket kept")


@pytest.mark.asyncio
@pytest.mark.parametrize("found", ["nothing", "a-checked-copy"])
async def test_a_cancel_without_a_restore_is_404_and_creates_nothing(instance, head_archive, found):
    """(d) No state file, in an empty data directory or beside a checked copy: 404 ``restore_not_pending``, and nothing
    created, not even ``.restore/apply.lock``: the lock is taken only once a state file is found."""
    root = instance.root
    if found == "a-checked-copy":
        await checked(head_archive)
    before = api.tree(root)
    response = await cancel()
    assert api.code(response) == (404, "restore_not_pending"), f"{found}: 404 restore_not_pending: {api.shown(response)}"
    assert api.tree(root) == before, f"{found}: nothing created: {cases.changed(before, api.tree(root))}"
    print_success(f"{found}: 404, nothing created")


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", [*ACTIVE[1:], *TERMINAL])
async def test_only_a_pending_restore_can_be_cancelled(instance, phase):
    """(d) A restore being applied or undone, or one finished: 404 ``restore_not_pending``, its state as it was."""
    root = instance.root
    before = write_state(root, phase, api.UNKNOWN_ID)
    response = await cancel()
    assert api.code(response) == (404, "restore_not_pending"), f"{phase}: 404 restore_not_pending: {api.shown(response)}"
    assert state_path(root).read_bytes() == before, f"{phase}: the state is as it was"
    print_success(f"{phase}: 404")


@pytest.mark.asyncio
@pytest.mark.parametrize("step", CANCEL_STEPS)
@pytest.mark.parametrize("error_number", OTHER_FAILURES)
async def test_a_cancel_that_fails_before_the_restore_is_dropped_is_500_and_the_restore_still_waits(instance, head_archive, monkeypatch, step, error_number):
    """(d) B-31: an ``OSError`` before the restore is dropped, its lock refused as it is taken or its state file that
    cannot be removed (EACCES, EIO): 500 ``restore_cancel_failed``, «The restore could not be cancelled: the server's log
    has the cause», never the plain 500 of an error escaping the route; one ERROR, «A pending restore could not be
    cancelled», whose ``error`` is the exception's type and its system's words, which stay out of the answer with any
    path. The restore still waits: the status ``pending`` for its stage, its state file as it was, its copy and its check
    kept; and the cancel, the failure gone, is 204. Barrier: the cancel failed at that step, once."""
    root = instance.root
    stage_id = await confirmed(head_archive)
    before = (state_path(root).read_bytes(), api.tree(stage_dir(root, stage_id)), check_state_path(root, stage_id).read_bytes())
    failure = fail_at(monkeypatch, step, lambda: OSError(error_number, os.strerror(error_number)))

    with capture_logs() as events:
        response = await cancel()

    assert len(failure.raised) == 1, f"barrier: the cancel failed at {step}, once: {failure.raised}"
    raised = failure.raised[0]
    assert api.refusal(response) == (500, "restore_cancel_failed", CANCEL_FAILED), f"{errno.errorcode[error_number]} at {step}: 500 restore_cancel_failed, not {api.shown(response)}"
    logged = [(event.get("log_level"), event.get("event"), event.get("error")) for event in api.loud(events)]
    assert logged == [("error", CANCEL_ERROR, f"{type(raised).__name__}: {raised.strerror}")], f"one error, with the type and the system's words: {api.loud(events)}"
    after = (await restore_status()).json()
    assert (after["state"], after["stage_id"]) == ("pending", stage_id), f"the restore still waits: {after}"
    assert (state_path(root).read_bytes(), api.tree(stage_dir(root, stage_id)), check_state_path(root, stage_id).read_bytes()) == before, "its state file, its copy and its check as they were"
    nothing_shown(response, root)
    failure.cured = True
    again = await cancel()
    assert (again.status_code, again.content) == (204, b""), f"the failure gone: the cancel is 204, not {api.shown(again)}"
    print_success(f"{errno.errorcode[error_number]} at {step}: 500 restore_cancel_failed, still pending, then 204")


@pytest.mark.asyncio
@pytest.mark.parametrize("error_number", OTHER_FAILURES)
async def test_a_copy_that_cannot_be_removed_does_not_fail_the_cancel(instance, head_archive, monkeypatch, error_number):
    """(d) B-31: the restore dropped (its state file removed), an ``OSError`` while its checked copy is removed
    (``apply._remove_leftovers``, EACCES, EIO): 204 all the same, never the plain 500 of a cancel that did happen; one
    WARNING, «The copy of a cancelled restore could not be removed: it goes when its check expires», naming the stage and
    the error (its system's words). The restore is cancelled: no state file, the status ``none``. The copy and its check
    are left for ``prune``, which removes them once they are old, as the warning says. Barrier: the removal of that
    stage's copy was asked once, its state file already gone."""
    root = instance.root
    stage_id = await confirmed(head_archive)
    apply = apply_module()
    asked: list[tuple[str | None, bool]] = []

    def remove_leftovers(data_dir: Path, stage: str | None) -> None:
        asked.append((stage, os.path.lexists(state_path(root))))
        raise OSError(error_number, os.strerror(error_number))

    monkeypatch.setattr(apply, "_remove_leftovers", remove_leftovers)
    with capture_logs() as events:
        response = await cancel()

    assert asked == [(stage_id, False)], f"barrier: the copy of {stage_id} was to be removed, once, the restore already dropped: {asked}"
    assert (response.status_code, response.content) == (204, b""), f"{errno.errorcode[error_number]} removing the copy: the restore is cancelled, 204, not {api.shown(response)}"
    loud = api.loud(events)
    assert [(event.get("log_level"), event.get("event"), event.get("stage_id")) for event in loud] == [("warning", COPY_LEFT_WARNING, stage_id)], f"one warning naming the stage: {loud}"
    assert os.strerror(error_number) in str(loud[0].get("error")), f"the warning names the error: {loud[0]}"
    assert (os.path.lexists(state_path(root)), (await restore_status()).json()["state"]) == (False, "none"), "the restore is cancelled"
    left = (stage_dir(root, stage_id).is_dir(), check_state_path(root, stage_id).is_file())
    assert left == (True, True), f"the copy and its check are left for prune: {left}"
    prune_far_ahead(root)
    gone = (os.path.lexists(stage_dir(root, stage_id)), os.path.lexists(check_state_path(root, stage_id)))
    assert gone == (False, False), f"prune removes them once they are old: {gone}"
    print_success(f"{errno.errorcode[error_number]} removing the copy: 204, one warning, the copy left for prune")


# =============================================================================
# (e) POST /restart
# =============================================================================


@pytest.mark.asyncio
async def test_a_restart_answers_then_stops_the_server_with_sigterm(instance, head_archive, signals):
    """(e) The answer first, then ``request_restart``: a SIGTERM to the server's process, once, through
    ``restart.send_signal``. Under Docker the container comes back by itself."""
    print_section("POST /backup/restore/restart")
    root = instance.root
    stage_id = await confirmed(head_archive)
    before = state_path(root).read_bytes()
    response = await restart(answered=signals)
    assert response.status_code == 202, f"a pending restore: 202: {api.shown(response)}"
    body = response.json()
    assert set(body) == RESTART_FIELDS and (body["state"], body["stage_id"]) == ("pending", stage_id), f"the pending restore, and the ticket of its outcome (RestoreRestartAccepted, lot B5c): {sorted(body)}"
    pid = restart_module().server_pid()
    assert signals.sent == [(pid, signal.SIGTERM, True)], f"one SIGTERM to the server ({pid}), once the answer was sent: {signals.sent}"
    assert signals.around == [], f"no signal outside restart.send_signal: {signals.around}"
    assert state_path(root).read_bytes() == before, "the restart changes nothing of the restore: the next start applies it"
    print_success(f"202, then SIGTERM to {pid}")


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", [None, *ACTIVE[1:], *TERMINAL])
async def test_no_restart_without_a_pending_restore(instance, signals, phase):
    root = instance.root
    if phase:
        write_state(root, phase, api.UNKNOWN_ID)
    response = await restart(answered=signals)
    assert api.code(response) == (409, "restore_not_pending"), f"{phase or 'no restore'}: 409 restore_not_pending: {api.shown(response)}"
    assert (signals.sent, signals.around) == ([], []), f"{phase or 'no restore'}: no signal: {signals.sent} {signals.around}"
    print_success(f"{phase or 'no restore'}: 409, no signal")


#: B-31: what a restart that cannot be prepared answers and logs, as the route does before B-31 (pinned, unchanged).
RESTART_FAILED = "The restart could not be prepared: the server's log has the cause"
RESTART_ERROR = "The ticket of the restore's outcome could not be written: no restart"


@pytest.mark.asyncio
@pytest.mark.parametrize("error_number", [pytest.param(errno.EACCES, id="EACCES"), pytest.param(errno.ENOSPC, id="ENOSPC")])
async def test_a_restart_that_cannot_be_prepared_is_500_and_restarts_nothing(instance, signals, monkeypatch, error_number):
    """(e) B-31, a GUARD: green before the code, the route already catches it; B-31 pins it. ``prepare_restart``, as
    ``restore.py`` imported it, raising an ``OSError`` (EACCES; ENOSPC too: a full disk is no 507 here): 500
    ``restore_restart_failed``, «The restart could not be prepared: the server's log has the cause»; one ERROR, «The
    ticket of the restore's outcome could not be written: no restart», whose ``error`` is the exception's type and its
    system's words, which stay out of the answer with any path. No restart scheduled (``restore._restart`` never
    called), no signal; the restore still pending, its state file as it was; no ticket. Barrier: ``prepare_restart`` was
    asked once."""
    root = instance.root
    before = write_state(root, "pending", api.UNKNOWN_ID)
    raised: list[OSError] = []
    restarts: list[str] = []

    def prepare_restart(*, data_dir: Path) -> Any:
        error = OSError(error_number, os.strerror(error_number))
        raised.append(error)
        raise error

    monkeypatch.setattr(restore, "prepare_restart", prepare_restart)
    monkeypatch.setattr(restore, "_restart", lambda: restarts.append("restart"))
    with capture_logs() as events:
        response = await restart(answered=signals)

    assert len(raised) == 1, f"barrier: prepare_restart was asked once: {raised}"
    assert api.refusal(response) == (500, "restore_restart_failed", RESTART_FAILED), f"{errno.errorcode[error_number]}: 500 restore_restart_failed, not {api.shown(response)}"
    logged = [(event.get("log_level"), event.get("event"), event.get("error")) for event in api.loud(events)]
    assert logged == [("error", RESTART_ERROR, f"{type(raised[0]).__name__}: {raised[0].strerror}")], f"one error, with the type and the system's words: {api.loud(events)}"
    assert (restarts, signals.sent, signals.around) == ([], [], []), f"no restart scheduled, no signal: {restarts} {signals.sent} {signals.around}"
    after = (await restore_status()).json()
    assert (after["state"], after["stage_id"], state_path(root).read_bytes()) == ("pending", api.UNKNOWN_ID, before), f"the restore still waits, its state file as it was: {after}"
    assert not os.path.lexists(ticket_path(root)), "no ticket written"
    nothing_shown(response, root)
    print_success(f"{errno.errorcode[error_number]}: 500 restore_restart_failed, no restart, still pending")


# =============================================================================
# (f) The copy of an ACTIVE restore: never dropped, never pruned
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ACTIVE)
async def test_the_copy_of_an_active_restore_cannot_be_dropped(instance, head_archive, phase):
    """(f) 409 ``restore_pending``: the copy and its check stay as they are. Another check is dropped as before."""
    print_section("The copy of an active restore")
    root = instance.root
    if phase == "pending":
        stage_id = await confirmed(head_archive)
    else:
        stage_id = await checked(head_archive)
        write_state(root, phase, stage_id)
    other = await checked(head_archive)
    before = (api.tree(stage_dir(root, stage_id)), check_state_path(root, stage_id).read_bytes())
    response = await api.drop(stage_id)
    assert api.code(response) == (409, "restore_pending"), f"{phase}: the restore's copy cannot be dropped: {api.shown(response)}"
    assert (api.tree(stage_dir(root, stage_id)), check_state_path(root, stage_id).read_bytes()) == before, f"{phase}: the copy and its check are kept as they were"
    assert (await api.drop(other)).status_code == 204 and not stage_dir(root, other).exists(), f"{phase}: another check is dropped as before"
    print_success(f"{phase}: 409 restore_pending; another check dropped")


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", TERMINAL)
async def test_the_copy_of_a_finished_restore_can_be_dropped(instance, head_archive, phase):
    root = instance.root
    stage_id = await checked(head_archive)
    write_state(root, phase, stage_id)
    response = await api.drop(stage_id)
    assert response.status_code == 204 and not stage_dir(root, stage_id).exists(), f"{phase}: dropped: {api.shown(response)}"
    print_success(f"{phase}: 204")


def prune_far_ahead(root: Path) -> None:
    """``prune`` as if a month had passed: every check, copy and upload is older than a check's lifetime."""
    restore_jobs.prune(root, now=datetime.now(UTC) + FAR_AHEAD)


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ACTIVE)
async def test_prune_keeps_the_check_and_copy_of_an_active_restore_however_old(instance, head_archive, phase):
    """(f) A month on, the ACTIVE restore's check and copy are still there; another ended check is pruned as before."""
    root = instance.root
    if phase == "pending":
        stage_id = await confirmed(head_archive)
    else:
        stage_id = await checked(head_archive)
        write_state(root, phase, stage_id)
    other = await checked(head_archive)
    before = (api.tree(stage_dir(root, stage_id)), check_state_path(root, stage_id).read_bytes())
    prune_far_ahead(root)
    assert (api.tree(stage_dir(root, stage_id)), check_state_path(root, stage_id).read_bytes()) == before, f"{phase}: the restore's check and copy are kept"
    assert not stage_dir(root, other).exists() and not check_state_path(root, other).exists(), f"{phase}: another old check is pruned"
    print_success(f"{phase}: kept; another check pruned")


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", TERMINAL)
async def test_prune_removes_the_old_copy_of_a_finished_restore(instance, head_archive, phase):
    root = instance.root
    stage_id = await checked(head_archive)
    write_state(root, phase, stage_id)
    prune_far_ahead(root)
    assert not stage_dir(root, stage_id).exists() and not check_state_path(root, stage_id).exists(), f"{phase}: pruned as any old check"
    print_success(f"{phase}: pruned")


def test_prune_keeps_the_command_lines_copy_of_a_pending_restore(instance, head_archive):
    """(f) The command line checks on a copy no check records, and confirms it: ``prune`` keeps it however old, while
    the restore is pending; cancelled, it is an old unrecorded copy like any other, and pruned."""
    root = instance.root
    apply = apply_module()
    report = staging_service.stage_archive(head_archive.path, root)
    apply.confirm_restore(report.stage_id, confirmed_by="cli", data_dir=root)
    before = api.tree(stage_dir(root, report.stage_id))
    assert not check_state_path(root, report.stage_id).exists(), "precondition: no check records the copy"
    prune_far_ahead(root)
    assert api.tree(stage_dir(root, report.stage_id)) == before, "the pending restore's copy is kept, however old"
    apply.cancel_restore(data_dir=root)
    prune_far_ahead(root)
    assert not stage_dir(root, report.stage_id).exists(), "once the restore is cancelled, the old copy is pruned"
    print_success("CLI copy kept while pending, pruned once cancelled")


# =============================================================================
# (g) Administrators only, never on a blocked instance, OpenAPI
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ["confirm", "status", "cancel", "restart"])
async def test_a_regular_user_is_refused_403_and_nothing_happens(instance, head_archive, signals, route):
    """(g) A restore replaces every user's data: each route is for administrators. A regular user's request is 403;
    nothing is confirmed, read, cancelled or restarted."""
    print_section("Administrators only")
    root = instance.root
    stage_id = await checked(head_archive)
    if route != "confirm":
        assert (await confirm(stage_id)).status_code == 202, "precondition: a pending restore"
    before = api.tree(restore_dir(root))
    requests = {
        "confirm": lambda: confirm(stage_id, user=api.REGULAR_USER),
        "status": lambda: restore_status(user=api.REGULAR_USER),
        "cancel": lambda: cancel(user=api.REGULAR_USER),
        "restart": lambda: restart(user=api.REGULAR_USER, answered=signals),
    }
    response = await requests[route]()
    assert (response.status_code, response.json()) == api.ADMIN_ONLY_ANSWER, f"{route} as a regular user: 403: {api.shown(response)}"
    assert api.tree(restore_dir(root)) == before, f"{route}: nothing changed under .restore"
    assert (signals.sent, signals.around) == ([], []), f"{route}: no signal"
    print_success(f"{route}: 403")


#: The four routes of lot B3, as ``restore_router`` declares them (under the ``/backup`` prefix of ``backup_router``).
NEW_ROUTES = {("POST", "/restore/stage/{stage_id}/confirm"), ("GET", "/restore/status"), ("DELETE", "/restore/pending"), ("POST", "/restore/restart")}


def test_no_new_restore_route_is_allowed_on_a_blocked_instance():
    """(g) The block lets the data leave, never come in, nor the server be stopped: none of the four is in
    ``ALLOWED_WHEN_BLOCKED``."""
    endpoints = {(method, route.path): route.endpoint for route in restore.restore_router.routes for method in getattr(route, "methods", ())}
    missing = sorted(NEW_ROUTES - set(endpoints))
    assert missing == [], f"routes of lot B3 not declared by restore.py: {missing}"
    allowed = sorted(f"{method} {path}" for method, path in NEW_ROUTES if endpoints[(method, path)] in ALLOWED_WHEN_BLOCKED)
    assert allowed == [], f"a restore route allowed on a blocked instance: {allowed}"


def test_openapi_documents_the_four_routes_their_answers_and_codes():
    """(g) Each operation under ``Backup & Export``, its success and model, its refusals documented with their codes;
    the drop of a check documents ``restore_pending``. The restart answers ``RestoreRestartAccepted`` since lot B5c: the
    status and the ticket of its outcome. B-31: the confirmation documents its 507 ``backup_no_space`` (as every 507 of
    the backup names its code) and its 500 names ``restore_confirm_failed`` beside ``restore_folder_unusable``; the
    cancel documents a 500 naming ``restore_cancel_failed``; the restart's 500 names ``restore_restart_failed``
    (already true: that row is a guard)."""
    document = api.restore_app().openapi()
    paths = {("POST", CONFIRM): "post", ("GET", STATUS): "get", ("DELETE", PENDING): "delete", ("POST", RESTART): "post"}
    missing = sorted(f"{method} {path}" for (method, path), verb in paths.items() if verb not in document["paths"].get(path, {}))
    assert missing == [], f"operations missing from OpenAPI: {missing}"
    operations = {key: document["paths"][key[1]][verb] for key, verb in paths.items()}
    tags = {key: operation["tags"] for key, operation in operations.items()}
    assert tags == dict.fromkeys(paths, [api.TAG]), f"each under {api.TAG} and no other: {tags}"
    success = {key: next(status for status in operation["responses"] if status.startswith("2")) for key, operation in operations.items()}
    assert success == {("POST", CONFIRM): "202", ("GET", STATUS): "200", ("DELETE", PENDING): "204", ("POST", RESTART): "202"}, f"the success of each: {success}"
    models = {key: operation["responses"][success[key]].get("content", {}).get("application/json", {}).get("schema") for key, operation in operations.items()}
    status_model = {"$ref": "#/components/schemas/RestoreStatus"}
    restart_model = {"$ref": "#/components/schemas/RestoreRestartAccepted"}
    assert models == {("POST", CONFIRM): status_model, ("GET", STATUS): status_model, ("DELETE", PENDING): None, ("POST", RESTART): restart_model}, f"the model of each success: {models}"
    codes = {
        ("POST", CONFIRM): {
            "404": ["restore_stage_not_found"],
            "409": ["restore_stage_running", "restore_not_restorable", "restore_stage_outdated", "restore_already_pending"],
            "410": ["restore_stage_expired"],
            "500": ["restore_folder_unusable", "restore_confirm_failed"],
            "507": ["backup_no_space"],
        },
        ("DELETE", PENDING): {"404": ["restore_not_pending"], "500": ["restore_cancel_failed"]},
        ("POST", RESTART): {"409": ["restore_not_pending"], "500": ["restore_restart_failed"]},
    }
    undocumented: dict[str, list[str]] = {}
    for key, statuses in codes.items():
        for status, names in statuses.items():
            description = operations[key]["responses"].get(status, {}).get("description", "")
            if absent := [name for name in names if name not in description]:
                undocumented[f"{key[0]} {key[1]} {status}"] = absent
    assert undocumented == {}, f"refusals answered but not documented with their code: {undocumented}"
    drop = document["paths"][api.STAGE_ITEM]["delete"]["responses"].get("409", {}).get("description", "")
    assert "restore_pending" in drop, f"the drop of a check documents restore_pending: {drop!r}"
    schema = document["components"]["schemas"]["RestoreStatus"]
    assert set(schema["properties"]) == STATUS_FIELDS, f"RestoreStatus has its 12 fields, upload_limit_mb and confirmed_via (L3-2) included: {sorted(schema['properties'])}"
    waiting = schema["properties"]["waiting"]
    reasons = {value for option in waiting.get("anyOf", [waiting]) for value in option.get("enum", [])}
    assert reasons == set(WAIT_REASONS), f"RestoreStatus.waiting lists exactly the four reasons, instance_blocked included (§11): {waiting}"
    print_success("4 operations documented, RestoreStatus with upload_limit_mb")


# =============================================================================
# (h) upload_limit_mb
# =============================================================================


#: (profile, the variable, the limit every RestoreStatus says): the variable wins over the profile when set.
STATUS_LIMITS = [
    pytest.param("selfhosted", None, 0, id="self-hosted-unset"),
    pytest.param("managed", None, 500, id="managed-unset"),
    pytest.param("selfhosted", "250", 250, id="self-hosted-250"),
    pytest.param("managed", "120", 120, id="managed-the-variable-wins"),
    pytest.param("managed", "0", 0, id="managed-0-lifts-the-limit"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("profile", "value", "limit"), STATUS_LIMITS)
async def test_the_status_says_the_upload_limit_without_a_restore(instance, monkeypatch, profile, value, limit):
    """(h) ``state: none`` too: a client learns the limit before it uploads anything."""
    print_section("upload_limit_mb")
    monkeypatch.setenv(api.PROFILE_VARIABLE, profile)
    if value is not None:
        monkeypatch.setenv(api.LIMIT_VARIABLE, value)
    response = await restore_status()
    assert response.status_code == 200, api.shown(response)
    assert (response.json()["state"], response.json()["upload_limit_mb"]) == ("none", limit), f"{profile}, {api.LIMIT_VARIABLE}={value!r}: {limit}: {response.json()}"
    print_success(f"{profile}, {value!r}: {limit}")


@pytest.mark.asyncio
async def test_a_limit_that_cannot_be_read_is_null_and_logged_once_naming_the_variable(instance, monkeypatch):
    """(h) The status still answers, the limit ``null``; one error in the log names the variable, as the upload's 503."""
    monkeypatch.setenv(api.LIMIT_VARIABLE, "abc")
    with capture_logs() as events:
        response = await restore_status()
    assert (response.status_code, response.json()["upload_limit_mb"]) == (200, None), f"200, the limit null: {api.shown(response)}"
    errors = [event for event in events if event.get("log_level") == "error"]
    assert len(errors) == 1 and api.LIMIT_VARIABLE in str(errors[0].get("error")), f"one error in the log, naming the variable: {errors}"
    print_success("unreadable: null, one error naming the variable")


@pytest.mark.asyncio
async def test_confirm_status_and_restart_say_the_same_limit(instance, head_archive, monkeypatch, signals):
    monkeypatch.setenv(api.LIMIT_VARIABLE, "321")
    stage_id = await checked(head_archive)
    answers = {"confirm": await confirm(stage_id), "status": await restore_status(), "restart": await restart(answered=signals)}
    limits = {name: (response.status_code, response.json().get("upload_limit_mb")) for name, response in answers.items()}
    assert limits == {"confirm": (202, 321), "status": (200, 321), "restart": (202, 321)}, f"the same limit in every answer: {limits}"
    print_success("confirm, status, restart: 321")


@pytest.mark.asyncio
async def test_the_limit_is_read_when_each_answer_is_built(instance, head_archive, monkeypatch):
    """(h) Never kept from an earlier answer: the variable changed between two answers shows in the second."""
    monkeypatch.setenv(api.LIMIT_VARIABLE, "100")
    stage_id = await checked(head_archive)
    first = await confirm(stage_id)
    monkeypatch.setenv(api.LIMIT_VARIABLE, "200")
    second = await restore_status()
    monkeypatch.delenv(api.LIMIT_VARIABLE)
    third = await restore_status()
    limits = [(response.status_code, response.json().get("upload_limit_mb")) for response in (first, second, third)]
    assert limits == [(202, 100), (200, 200), (200, 0)], f"each answer reads the variable as it is then: {limits}"
    print_success("100, then 200, then 0")


# =============================================================================
# (i) Lot B5c: the outcome of a restart, read with its ticket, without a session
# =============================================================================


@pytest.mark.asyncio
async def test_a_restart_gives_the_ticket_of_its_outcome_on_disk_before_the_answer(instance, head_archive, signals):
    """(i) The restart's answer: the status of the restore and ``outcome_ticket``, 43 URL-safe characters, never kept by
    a cache (``no-store``). Its file is on disk as the answer begins — the restart is requested only after the answer —
    holding the ticket's hash for the restore's stage, an hour to live, 0600, never the ticket. The SIGTERM still follows
    the answer."""
    print_section("(i) The outcome of a restart (lot B5c)")
    root = instance.root
    stage_id = await confirmed(head_archive)
    path = ticket_path(root)
    started = datetime.now(UTC)
    app = Answered(api.restore_app(B3_ADMIN), look=lambda: file_bytes(path))
    response = await send(app, "POST", RESTART)
    ended = datetime.now(UTC)
    assert response.status_code == 202, f"a pending restore: 202: {api.shown(response)}"
    body = response.json()
    assert set(body) == RESTART_FIELDS and (body["state"], body["stage_id"]) == ("pending", stage_id), f"the status and the ticket of the outcome: {sorted(body)}"
    ticket = body["outcome_ticket"]
    assert isinstance(ticket, str) and A_TICKET.fullmatch(ticket), f"43 URL-safe characters: {len(str(ticket))} characters"
    assert no_store(response), f"Cache-Control: no-store: {response.headers.get('cache-control')!r}"
    raw = path.read_bytes()
    assert app.seen == raw, "the ticket's file was on disk as the answer began, and was not written again after"
    assert ticket.encode("ascii") not in raw, "the file never holds the ticket"
    record = json.loads(raw)
    issued_at = api.moment(record["issued_at"])
    found = (set(record), record["sha256"], record["stage_id"], api.moment(record["expires_at"]) - issued_at)
    assert found == (TICKET_FIELDS, hash_of(ticket), stage_id, TICKET_TTL), f"its hash, the restore's stage, an hour: {record}"
    assert started - timedelta(seconds=1) <= issued_at <= ended, f"issued by this request (a second of slack: the precision of a time is not the contract's): {record['issued_at']}"
    assert os.name == "nt" or stat.S_IMODE(path.lstat().st_mode) == 0o600, f"a file of its owner only: {oct(stat.S_IMODE(path.lstat().st_mode))}"
    assert [(pid, sig) for pid, sig, _answered in signals.sent] == [(restart_module().server_pid(), signal.SIGTERM)], f"the restart still follows: {signals.sent}"
    print_success("202 with its ticket, the file on disk before the answer, no-store")


@pytest.mark.asyncio
async def test_a_second_restart_replaces_the_ticket_of_the_first(instance):
    """(i) One ticket at a time, the last restart's: the first opens nothing any more."""
    root = instance.root
    first = await restart_requested(root)
    second = await restarted()
    assert first != second, "each restart gives a new ticket"
    record = json.loads(ticket_path(root).read_bytes())
    assert (record["sha256"], record["stage_id"]) == (hash_of(second), api.UNKNOWN_ID), f"the file is the second ticket's: {record}"
    old, new = await get_outcome(first), await get_outcome(second)
    assert (old.status_code, old.json()) == (404, NOT_FOUND), f"the first ticket opens nothing: {api.shown(old)}"
    assert (new.status_code, new.json()) == (200, {"state": "pending", "reason": None, "waiting": None}), f"the second does: {api.shown(new)}"
    print_success("the second ticket replaces the first")


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", [None, *ACTIVE[1:], *TERMINAL])
async def test_a_restart_refused_writes_no_ticket(instance, signals, phase):
    """(i) 409 ``restore_not_pending`` as before, and nothing written: no ticket for a restart that does not happen."""
    root = instance.root
    if phase:
        write_state(root, phase, api.UNKNOWN_ID)
    before = api.tree(root)
    response = await restart(answered=signals)
    assert api.code(response) == (409, "restore_not_pending"), f"{phase or 'no restore'}: 409: {api.shown(response)}"
    assert not os.path.lexists(ticket_path(root)), f"{phase or 'no restore'}: no ticket written"
    assert api.tree(root) == before and "outcome_ticket" not in response.text, f"{phase or 'no restore'}: nothing written, no ticket in the answer"
    print_success(f"{phase or 'no restore'}: 409, no ticket")


@pytest.mark.asyncio
async def test_the_outcome_needs_no_session_and_reads_its_ticket_from_the_header_only(instance):
    """(i) The start ended every session: the page asks with no cookie at all, the ticket in ``X-Restore-Ticket``. Never
    in the URL, where access logs and histories keep it: ``?ticket=`` is ignored, the 404 of no ticket. The barrier: this
    app has nobody signed in (``GET /status`` is 401)."""
    root = instance.root
    ticket = await restart_requested(root)
    barrier = await send(anonymous_app(), "GET", STATUS)
    assert barrier.status_code == 401, f"barrier: nobody is signed in to this app: {api.shown(barrier)}"
    response = await get_outcome(ticket)
    assert response.status_code == 200, f"no session, the ticket in its header: 200: {api.shown(response)}"
    assert response.json() == {"state": "pending", "reason": None, "waiting": None}, f"the outcome, and nothing more: {response.json()}"
    assert no_store(response), f"Cache-Control: no-store: {response.headers.get('cache-control')!r}"
    in_the_query = await get_outcome(params={"ticket": ticket})
    assert (in_the_query.status_code, in_the_query.json()) == (404, NOT_FOUND), f"in the query: ignored: {api.shown(in_the_query)}"
    assert same_answer(in_the_query, await get_outcome()), "the very answer of no ticket at all"
    print_success("200 without a session, the header only")


@dataclass
class Presenting:
    """What a case of a ticket that opens nothing may need: the data directory, the restore's stage, the restart's ticket,
    a folder outside the data directory."""

    root: Path
    stage_id: str
    ticket: str
    elsewhere: Path


@dataclass
class Presented:
    """What the client sends: a ticket in ``X-Restore-Ticket`` (``None``: no header), and a query."""

    ticket: str | None = None
    params: dict[str, str] | None = None


async def _no_ticket(s: Presenting) -> Presented:
    return Presented()


async def _an_empty_header(s: Presenting) -> Presented:
    return Presented("")


async def _a_character_short(s: Presenting) -> Presented:
    return Presented(s.ticket[:-1])


async def _a_character_more(s: Presenting) -> Presented:
    return Presented(s.ticket + "A")


async def _standard_base64(s: Presenting) -> Presented:
    return Presented(s.ticket[:-1] + "+")


async def _another_ticket(s: Presenting) -> Presented:
    return Presented(secrets.token_urlsafe(32))


async def _its_hash(s: Presenting) -> Presented:
    return Presented(hash_of(s.ticket))


async def _in_the_query(s: Presenting) -> Presented:
    return Presented(params={"ticket": s.ticket})


async def _replaced_by_another_restart(s: Presenting) -> Presented:
    await restarted()
    return Presented(s.ticket)


async def _expired(s: Presenting) -> Presented:
    """A ticket issued two hours ago, as a restart then issued it: an hour past its expiry."""
    return Presented(issued(s.root, s.stage_id, now=datetime.now(UTC) - 2 * TICKET_TTL))


async def _its_file_gone(s: Presenting) -> Presented:
    ticket_path(s.root).unlink()
    return Presented(s.ticket)


async def _its_file_unreadable(s: Presenting) -> Presented:
    ticket_path(s.root).write_bytes(b"{not a ticket")
    return Presented(s.ticket)


async def _its_file_with_a_key_more(s: Presenting) -> Presented:
    path = ticket_path(s.root)
    path.write_text(json.dumps({**json.loads(path.read_bytes()), "note": "a key more"}), encoding="utf-8")
    return Presented(s.ticket)


async def _its_file_a_link(s: Presenting) -> Presented:
    """The valid file moved out of ``.restore``, a link to it in its place: followed, it would open."""
    path, target = ticket_path(s.root), s.elsewhere / TICKET_FILE_NAME
    path.rename(target)
    path.symlink_to(target)
    return Presented(s.ticket)


async def _no_restore(s: Presenting) -> Presented:
    state_path(s.root).unlink()
    return Presented(s.ticket)


async def _a_restore_of_another_stage(s: Presenting) -> Presented:
    write_state(s.root, "pending", OTHER_STAGE_ID)
    return Presented(s.ticket)


async def _dropped_by_a_cancel(s: Presenting) -> Presented:
    """The restore cancelled through the API after its restart was asked: no restore, and its ticket gone with it."""
    response = await cancel()
    assert response.status_code == 204, f"precondition: the pending restore is cancelled: {api.shown(response)}"
    return Presented(s.ticket)


#: Every ticket that does not open the outcome, and why. A final outcome read before is not among them (N53): its ticket
#: reads it again until it expires.
NOT_OPENING = [
    pytest.param(_no_ticket, id="no-ticket"),
    pytest.param(_an_empty_header, id="an-empty-header"),
    pytest.param(_a_character_short, id="a-character-short"),
    pytest.param(_a_character_more, id="a-character-more"),
    pytest.param(_standard_base64, id="not-url-safe"),
    pytest.param(_another_ticket, id="another-ticket"),
    pytest.param(_its_hash, id="its-hash"),
    pytest.param(_in_the_query, id="in-the-query"),
    pytest.param(_replaced_by_another_restart, id="replaced-by-another-restart"),
    pytest.param(_expired, id="expired"),
    pytest.param(_its_file_gone, id="its-file-gone"),
    pytest.param(_its_file_unreadable, id="its-file-unreadable"),
    pytest.param(_its_file_with_a_key_more, id="its-file-with-a-key-more"),
    pytest.param(_its_file_a_link, id="its-file-a-link", marks=pytest.mark.skipif(os.name == "nt", reason="symbolic links need a privilege on Windows")),
    pytest.param(_no_restore, id="no-restore"),
    pytest.param(_a_restore_of_another_stage, id="a-restore-of-another-stage"),
    pytest.param(_dropped_by_a_cancel, id="dropped-by-a-cancel"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("present", NOT_OPENING)
async def test_every_ticket_that_does_not_open_the_outcome_gets_one_and_the_same_404(instance, tmp_path, present):
    """(i) 404 ``restore_outcome_not_found``, and the very answer of a request without a ticket — status, headers and
    bytes: nobody learns which ticket was close, replaced, expired or dropped, nor whether a restore exists. No path, no
    ticket in it."""
    root = instance.root
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    ticket = await restart_requested(root)
    presented = await present(Presenting(root, api.UNKNOWN_ID, ticket, elsewhere))
    response = await get_outcome(presented.ticket, params=presented.params)
    assert api.code(response) == (404, "restore_outcome_not_found"), f"{present.__name__}: 404 restore_outcome_not_found: {api.shown(response)}"
    assert response.json() == NOT_FOUND, f"{present.__name__}: the one body: {response.json()}"
    nothing = await get_outcome()
    assert same_answer(response, nothing), f"{present.__name__}: the answer of no ticket at all, status, headers and bytes: {response.headers.multi_items()} / {nothing.headers.multi_items()}"
    assert ticket not in response.text and hash_of(ticket) not in response.text, "no ticket in the answer"
    no_path_in(response, root)
    print_success(f"{present.__name__}: the one 404")


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ACTIVE + TERMINAL)
async def test_the_outcome_of_each_phase_is_its_state_its_reason_and_why_it_waits(instance, phase):
    """(i) Applying, applied and rolling back are ``in_progress``; the reason and the wait as recorded; nothing more."""
    root = instance.root
    write_state(root, phase, api.UNKNOWN_ID)
    record = json.loads(state_path(root).read_text(encoding="utf-8"))
    response = await get_outcome(issued(root))
    assert response.status_code == 200, f"{phase}: 200: {api.shown(response)}"
    assert response.json() == {"state": STATE_OF[phase], "reason": record.get("reason"), "waiting": record.get("waiting")}, f"{phase}: {response.json()}"
    assert no_store(response), f"{phase}: no-store"
    print_success(f"{phase} → {response.json()['state']}")


@pytest.mark.asyncio
@pytest.mark.parametrize("waiting", WAIT_REASONS)
async def test_the_outcome_of_a_restore_a_start_left_waiting_says_why(instance, waiting):
    """(i) The restart happened, the restore was not applied: the page says why (§2, §10, §11)."""
    root = instance.root
    ticket = await restart_requested(root)
    left_waiting(root, waiting)
    response = await get_outcome(ticket)
    assert (response.status_code, response.json()) == (200, {"state": "pending", "reason": None, "waiting": waiting}), f"pending, {waiting}: {api.shown(response)}"
    print_success(f"pending, {waiting}")


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", TERMINAL)
async def test_a_final_outcome_is_answered_the_same_until_its_ticket_expires(instance, phase):
    """(i) Decision N53: one restore, one ticket — not one read. Committed or rolled back, the page reads the outcome as
    often as it asks: the very same answer each time (status, headers and bytes), the ticket's file as it was. An answer
    lost on the way (a connection reset while the server starts) is asked again, and never turns into the 404 that sent
    the page back to a session the restore had ended — without ``JWT_SECRET``, «restored» shown after a rollback. Until
    the ticket expires: a ticket of that restore an hour old gets the one 404, and its file goes."""
    root = instance.root
    ticket = await restart_requested(root)
    write_state(root, phase, api.UNKNOWN_ID)
    record = json.loads(state_path(root).read_text(encoding="utf-8"))
    before = ticket_path(root).read_bytes()
    answers = [await get_outcome(ticket) for _ in range(3)]
    expected = {"state": phase, "reason": record.get("reason"), "waiting": None}
    assert [(answer.status_code, answer.json()) for answer in answers] == [(200, expected)] * 3, f"{phase}: the outcome at every read, not once: {[api.shown(answer) for answer in answers]}"
    assert all(same_answer(answer, answers[0]) for answer in answers[1:]), f"{phase}: the very same answer each time: {[answer.headers.multi_items() for answer in answers]}"
    assert ticket_path(root).read_bytes() == before, f"{phase}: the ticket's file as it was: a read does not use it up"
    expired = issued(root, now=datetime.now(UTC) - 2 * TICKET_TTL)
    late = await get_outcome(expired)
    assert (late.status_code, late.json()) == (404, NOT_FOUND) and same_answer(late, await get_outcome()), f"{phase}: expired, the one 404: {api.shown(late)}"
    assert not os.path.lexists(ticket_path(root)), f"{phase}: the expired ticket's file goes when its holder presents it"
    print_success(f"{phase}: the same answer three times; expired, the one 404")


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ACTIVE)
async def test_an_outcome_not_final_yet_is_answered_again(instance, phase):
    """(i) Pending or in progress: the page asks again until the end; the file as it was."""
    root = instance.root
    ticket = await restart_requested(root)
    write_state(root, phase, api.UNKNOWN_ID)
    before = ticket_path(root).read_bytes()
    answers = [await get_outcome(ticket) for _ in range(2)]
    assert [(answer.status_code, answer.json().get("state")) for answer in answers] == [(200, STATE_OF[phase])] * 2, f"{phase}: answered twice: {[api.shown(answer) for answer in answers]}"
    assert ticket_path(root).read_bytes() == before, f"{phase}: the file as it was"
    print_success(f"{phase}: again")


@pytest.mark.asyncio
async def test_a_new_confirmation_drops_the_ticket_of_the_restore_before(instance, head_archive):
    """(i) A ticket names one restart of one restore: a restore rolled back, its outcome never read, then another
    confirmed — the old ticket goes."""
    root = instance.root
    write_state(root, "rolled_back", api.UNKNOWN_ID)
    ticket = issued(root)
    stage_id = await checked(head_archive)
    response = await confirm(stage_id)
    assert response.status_code == 202, f"another restore confirmed: {api.shown(response)}"
    assert not os.path.lexists(ticket_path(root)), "the ticket of the restore before is dropped"
    after = await get_outcome(ticket)
    assert (after.status_code, after.json()) == (404, NOT_FOUND), f"it opens nothing: {api.shown(after)}"
    print_success("confirmed: the old ticket dropped")


@pytest.mark.asyncio
async def test_the_ticket_is_never_logged(instance, caplog, monkeypatch):
    """(i) Whoever reads the logs must not be able to read an outcome: neither the ticket nor its hash in a structlog
    event or a stdlib record — two restarts, the outcome read right, with the replaced ticket, malformed, once committed
    read twice (N53: the same answer), then a ticket of that restore an hour old, whose file goes. Behind a barrier for
    each logger and each capture.

    The ticket travels only as the page sends it, in ``X-Restore-Ticket``. Put in a URL, it is the test client's own
    request line (httpx) that logs it, not the product, which never writes it there: the query, ignored, is pinned on its
    own (``in-the-query``, and the read without a session)."""
    root = instance.root
    loggers = (OUTCOME_MODULE, ROUTES_MODULE)
    for name in loggers:
        monkeypatch.setattr(logging.getLogger(name), "disabled", False)
        caplog.set_level(logging.DEBUG, logger=name)
    caplog.set_level(logging.DEBUG)
    write_state(root, "pending", api.UNKNOWN_ID)
    with capture_logs() as events:
        for name in loggers:
            get_logger(name).warning(LOG_CANARY)
            logging.getLogger(name).warning(LOG_CANARY)
        replaced = await restarted()
        ticket = await restarted()
        for presented in (replaced, ticket, ticket[:-1]):
            await get_outcome(presented)
        write_state(root, "committed", api.UNKNOWN_ID)
        await get_outcome(ticket)
        await get_outcome(ticket)
        expired = issued(root, now=datetime.now(UTC) - 2 * TICKET_TTL)
        await get_outcome(expired)
    canaries = [event for event in events if event.get("event") == LOG_CANARY]
    assert len(canaries) == len(loggers), f"barrier: a structlog logger of each name reaches capture_logs: {canaries}"
    assert {record.name for record in caplog.records if record.getMessage() == LOG_CANARY} == set(loggers), "barrier: a stdlib logger of each name reaches caplog"
    hidden = [text for value in (replaced, ticket, expired) for text in (value, hash_of(value))]
    leaked = [repr(event) for event in events if any(text in repr(event) for text in hidden)]
    leaked += [f"{record.name}: {record.getMessage()}" for record in caplog.records if any(text in record.getMessage() or text in repr(vars(record)) for text in hidden)]
    assert leaked == [], f"a ticket or its hash in the logs: {leaked}"
    print_success(f"{len(events)} events and {len(caplog.records)} records: no ticket, no hash")


@pytest.mark.asyncio
async def test_on_a_blocked_instance_the_outcome_answers_its_ticket_without_a_session(instance, monkeypatch):
    """(i) P7/P8: a restart asked for before the hosting provider blocked the instance; the start that followed did not
    apply the restore (``pending``, ``instance_blocked``). The page, with no session, still reads why: the outcome only
    reports a restart already asked for, and starts nothing.

    RED until workstream H's line lands: ``GET /backup/restore/outcome`` in ``ALLOWED_WHEN_BLOCKED``
    (``api/v1/instance_block.py``, H's list; its pin in ``test_instance_block.py`` is agreed with H). Until then
    ``refuse_when_blocked`` answers this caller without a session the 401 of ``get_current_user``."""
    root = instance.root
    ticket = await restart_requested(root)
    left_waiting(root, "instance_blocked")
    monkeypatch.setenv(BLOCKED_VARIABLE, "true")
    assert instance_blocked() is True, "precondition: the instance is blocked"
    response = await get_outcome(ticket, app=blocked_app())
    assert response.status_code == 200, f"blocked: the outcome still answers its ticket: {api.shown(response)} (401: the route is not in ALLOWED_WHEN_BLOCKED yet, workstream H's line)"
    assert response.json() == {"state": "pending", "reason": None, "waiting": "instance_blocked"}, f"pending, waiting for the unblock: {response.json()}"
    assert no_store(response), "no-store"
    print_success("blocked: 200 pending, instance_blocked")


def sign_in_whoever_carries_a_cookie(monkeypatch: pytest.MonkeyPatch) -> None:
    """``auth.get_current_user`` as ``refuse_when_blocked`` calls it (itself, outside FastAPI's overrides), replaced for
    the test: whoever carries a session cookie is the administrator; anyone else meets the real one, whose 401 comes
    before any database."""
    real = auth.get_current_user

    async def get_current_user(request: Request, session: Any) -> SimpleNamespace:
        if request.cookies.get(SESSION_COOKIE_NAME):
            return B3_ADMIN
        return await real(request, session)

    monkeypatch.setattr(auth, "get_current_user", get_current_user)


def restore_routes() -> list[tuple[str, str]]:
    """Every route of ``restore.py``, as (method, path under ``/api/v1``), a stage id where one is asked."""
    return sorted((method, "/api/v1/backup" + route.path.replace("{stage_id}", api.UNKNOWN_ID)) for route in restore.restore_router.routes for method in getattr(route, "methods", None) or ())


#: The restore routes of lots B2b and B3: on a blocked instance, none of them answers.
REFUSED_WHEN_BLOCKED = {
    ("PUT", f"{api.API}/upload"),
    ("POST", api.STAGE),
    ("GET", f"{api.STAGE}/{api.UNKNOWN_ID}"),
    ("DELETE", f"{api.STAGE}/{api.UNKNOWN_ID}"),
    ("POST", f"{api.STAGE}/{api.UNKNOWN_ID}/confirm"),
    ("GET", STATUS),
    ("DELETE", PENDING),
    ("POST", RESTART),
}


@pytest.mark.asyncio
async def test_on_a_blocked_instance_every_other_restore_route_stays_423(instance, monkeypatch):
    """(i) The block lets the data leave, never come in, nor the server be stopped: every restore route but the outcome
    answers a signed-in administrator 423 ``instance_blocked``, and nothing is written — the pending restore is not
    cancelled, no ticket is issued. What must not change with lot B5c."""
    root = instance.root
    write_state(root, "pending", api.UNKNOWN_ID)
    monkeypatch.setenv(BLOCKED_VARIABLE, "true")
    assert instance_blocked() is True, "precondition: the instance is blocked"
    sign_in_whoever_carries_a_cookie(monkeypatch)
    routes = [(method, path) for method, path in restore_routes() if path != OUTCOME]
    assert REFUSED_WHEN_BLOCKED <= set(routes), f"precondition: the routes of lots B2b and B3: {sorted(REFUSED_WHEN_BLOCKED - set(routes))} missing"
    before = api.tree(root)
    answers = {}
    for method, path in routes:
        response = await send(blocked_app(), method, path, headers=SIGNED_IN)
        answers[f"{method} {path}"] = (response.status_code, response.json() if "json" in response.headers.get("content-type", "") else response.text)
    assert answers == dict.fromkeys(answers, (423, BLOCKED_ANSWER)), f"423 instance_blocked to a signed-in administrator, each: {answers}"
    assert api.tree(root) == before, f"nothing written: {cases.changed(before, api.tree(root))}"
    print_success(f"{len(answers)} restore routes: 423")


def test_the_outcome_is_the_one_restore_route_allowed_on_a_blocked_instance():
    """(i) RED until both lot B5c (the route) and workstream H's line (``ALLOWED_WHEN_BLOCKED``) land: of all the routes of
    ``restore.py``, the outcome alone, which starts nothing."""
    endpoints = {(method, route.path): route.endpoint for route in restore.restore_router.routes for method in getattr(route, "methods", None) or ()}
    assert ("GET", "/restore/outcome") in endpoints, f"[new] GET /backup/restore/outcome is not a route of restore.py yet (lot B5c): {sorted(endpoints)}"
    allowed = sorted(f"{method} {path}" for (method, path), endpoint in endpoints.items() if endpoint in ALLOWED_WHEN_BLOCKED)
    assert allowed == ["GET /restore/outcome"], f"the outcome, and no other restore route, in ALLOWED_WHEN_BLOCKED (workstream H's line): {allowed}"
    print_success("GET /restore/outcome alone")


def test_openapi_documents_the_outcome_its_header_its_404_and_the_ticket_of_the_restart():
    """(i) The generated client sends the ticket in its header and reads ``RestoreOutcome``: the operation under
    ``Backup & Export``, one parameter (``X-Restore-Ticket``, a header, not required: without it, the one 404), its 404
    with its code; ``RestoreOutcome`` its three fields and their values; ``RestoreRestartAccepted`` the status and the
    ticket, required."""
    document = api.restore_app().openapi()
    operation = document["paths"].get(OUTCOME, {}).get("get")
    assert operation is not None, f"[new] GET {OUTCOME} is not documented: lot B5c adds it"
    assert operation["tags"] == [api.TAG], f"under {api.TAG}: {operation['tags']}"
    success = operation["responses"].get("200", {}).get("content", {}).get("application/json", {}).get("schema")
    assert success == {"$ref": "#/components/schemas/RestoreOutcome"}, f"200 RestoreOutcome: {success}"
    described = operation["responses"].get("404", {}).get("description", "")
    assert "restore_outcome_not_found" in described, f"the 404 documents its code: {described!r}"
    parameters = sorted((parameter["in"], parameter["name"].lower(), parameter.get("required", False)) for parameter in operation.get("parameters", []))
    assert parameters == [("header", TICKET_HEADER.lower(), False)], f"one parameter, the ticket's header, not required; none in the query: {parameters}"
    schemas = document["components"]["schemas"]
    outcome = schemas.get("RestoreOutcome", {}).get("properties", {})
    assert set(outcome) == OUTCOME_FIELDS, f"RestoreOutcome: state, reason, waiting, nothing else: {sorted(outcome)}"
    allowed = {name: values_of(outcome[name], schemas) for name in sorted(OUTCOME_FIELDS)}
    assert allowed == {"reason": {*ROLLBACK_REASONS, None}, "state": OUTCOME_STATES, "waiting": {*WAIT_REASONS, None}}, f"the values of each field: {allowed}"
    accepted = schemas.get("RestoreRestartAccepted", {})
    assert set(accepted.get("properties", {})) == RESTART_FIELDS and "outcome_ticket" in accepted.get("required", []), f"RestoreRestartAccepted: the status and the ticket, required: {accepted}"
    print_success("GET /outcome, its header, its 404; RestoreOutcome; RestoreRestartAccepted")


# =============================================================================
# (j) B-32: a state the file system cannot read
# =============================================================================


#: B-32: what the status answers, and what the reader logs, when the file system refuses the state file.
STATE_UNREADABLE = "The state of the restore cannot be read: the server's log has the cause"
STATE_READ_ERROR = "The state of the restore cannot be read"
#: B-32: the error ``os.open`` raises for the state file, by way; with ``mode-000`` the real file system refuses it.
REFUSED_WITH = {"EACCES": errno.EACCES, "EIO": errno.EIO}
#: B-32: each test of (j) once for each way the state file is made unreadable. Root, and Windows, read a file of mode
#: 000 all the same: that way is skipped there.
UNREADABLE_WAYS = [
    pytest.param("EACCES", id="EACCES"),
    pytest.param("EIO", id="EIO"),
    pytest.param("mode-000", id="mode-000", marks=pytest.mark.skipif(os.name == "nt" or os.geteuid() == 0, reason="root, or Windows, reads a file of mode 000 all the same")),
]


class UnreadableState:
    """The state file of the restore made unreadable at the moment the test chooses (``now``), until ``cure``: every
    opening of it fails, the rest of the file system untouched. ``refused`` records each opening that failed: the barrier
    that a route reached the file, and was refused."""

    def __init__(self, root: Path, way: str, monkeypatch: pytest.MonkeyPatch) -> None:
        self.path = state_path(root)
        self.way = way
        self.monkeypatch = monkeypatch
        self.refused: list[OSError] = []
        self.unreadable = False

    def now(self) -> None:
        """From now on the state file cannot be opened: ``os.open`` refuses it, handing every other path to the real one;
        or its mode is 000, and the real one refuses it."""
        assert self.path.is_file() and not self.path.is_symlink(), f"precondition: a regular state file to make unreadable: {self.path.name}"
        target = os.path.realpath(self.path)
        real_open = os.open

        def opening(path: Any, flags: int, mode: int = 0o777, *, dir_fd: int | None = None) -> int:
            if not self.unreadable or dir_fd is not None or os.path.realpath(path) != target:
                return real_open(path, flags, mode, dir_fd=dir_fd)
            if self.way in REFUSED_WITH:
                error = OSError(REFUSED_WITH[self.way], os.strerror(REFUSED_WITH[self.way]))
                self.refused.append(error)
                raise error
            try:
                return real_open(path, flags, mode)
            except OSError as exc:
                self.refused.append(exc)
                raise

        self.monkeypatch.setattr(os, "open", opening)
        self.unreadable = True
        if self.way == "mode-000":
            self.path.chmod(0o000)
            assert not os.access(self.path, os.R_OK), "precondition: with its mode 000, this process cannot read the state file"

    def cure(self) -> None:
        """The state file readable again, as it was; a file that replaced it is left as it is."""
        if self.unreadable and self.way == "mode-000" and self.path.is_file() and not self.path.is_symlink():
            self.path.chmod(0o600)
        self.unreadable = False


@pytest.fixture(params=UNREADABLE_WAYS)
def unreadable(request: pytest.FixtureRequest, instance, monkeypatch: pytest.MonkeyPatch) -> Iterator[UnreadableState]:
    """B-32: the state file of the test's data directory, made unreadable when the test says so (``now``), in one of the
    ways; readable again at the end, whatever the test did, before ``instance`` looks at the data directory."""
    state = UnreadableState(instance.root, request.param, monkeypatch)
    yield state
    state.cure()


def cause_in_the_log(events: list[dict], unreadable: UnreadableState) -> bool:
    """Whether the log has the cause as the reader logs it: its error, with the exception's type and its system's words."""
    refused = unreadable.refused[0]
    expected = ("error", STATE_READ_ERROR, f"{type(refused).__name__}: {refused.strerror}")
    return expected in [(event.get("log_level"), event.get("event"), event.get("error")) for event in events]


def answer_of(response: httpx.Response) -> tuple[int, Any]:
    """Status and body: the JSON one, or the text of an answer that has none (a plain 500)."""
    return response.status_code, response.json() if "json" in response.headers.get("content-type", "") else response.text


@pytest.mark.asyncio
async def test_a_state_the_file_system_cannot_read_is_a_500_of_the_status_and_nothing_changes(instance, unreadable):
    """(j) B-32 (b1): a pending restore whose state file the file system refuses. ``GET /status``: 500
    ``restore_state_unreadable``, «The state of the restore cannot be read: the server's log has the cause», never the
    200 ``none`` that hid a restore which may well wait. The log has the cause (the reader's error, with the exception's
    type and its system's words); the answer neither those words nor a path. Nothing written or removed. Barrier: the
    status opened the state file, and was refused."""
    print_section("B-32: a state the file system cannot read")
    root = instance.root
    write_state(root, "pending", api.UNKNOWN_ID)
    before = api.tree(root)
    unreadable.now()

    with capture_logs() as events:
        response = await restore_status()

    assert unreadable.refused, f"barrier: the status opened the state file ({unreadable.way}), and was refused"
    assert api.refusal(response) == (500, "restore_state_unreadable", STATE_UNREADABLE), f"{unreadable.way}: 500 restore_state_unreadable, not {api.shown(response)}"
    assert cause_in_the_log(events, unreadable), f"{unreadable.way}: the cause in the server's log: {api.loud(events)}"
    nothing_shown(response, root)
    unreadable.cure()
    assert api.tree(root) == before, f"{unreadable.way}: nothing written or removed: {cases.changed(before, api.tree(root))}"
    print_success(f"{unreadable.way}: 500 restore_state_unreadable, the cause logged, nothing changed")


@pytest.mark.asyncio
async def test_a_cancel_of_a_restore_whose_state_cannot_be_read_is_500_and_touches_nothing(instance, head_archive, unreadable):
    """(j) B-32 (b2): a pending restore, its checked copy, its check and the ticket of its restart; then its state file
    refused by the file system. ``DELETE /pending``: 500 ``restore_state_unreadable``, never the 404
    ``restore_not_pending`` that told the page nothing waited; the cause in the log, neither the system's words nor a
    path in the answer. The state, the copy, the check's record and the ticket as they were, nothing else written;
    readable again, the restore still waits. Barrier: the cancel opened the state file, and was refused."""
    root = instance.root
    stage_id = await confirmed(head_archive)
    await restarted()
    assert os.path.lexists(ticket_path(root)), "precondition: the ticket of the restart"
    before = api.tree(root)
    unreadable.now()

    with capture_logs() as events:
        response = await cancel()

    assert unreadable.refused, f"barrier: the cancel opened the state file ({unreadable.way}), and was refused"
    assert api.code(response) == (500, "restore_state_unreadable"), f"{unreadable.way}: 500 restore_state_unreadable, not {api.shown(response)}"
    assert cause_in_the_log(events, unreadable), f"{unreadable.way}: the cause in the server's log: {api.loud(events)}"
    nothing_shown(response, root)
    unreadable.cure()
    assert api.tree(root) == before, f"{unreadable.way}: the state, the copy, the check's record and the ticket untouched, nothing written: {cases.changed(before, api.tree(root))}"
    after = (await restore_status()).json()
    assert (after["state"], after["stage_id"]) == ("pending", stage_id), f"{unreadable.way}: readable again, the restore still waits: {after}"
    print_success(f"{unreadable.way}: 500 restore_state_unreadable, nothing touched, still pending")


@pytest.mark.asyncio
async def test_a_restart_of_a_restore_whose_state_cannot_be_read_is_500_without_a_ticket_or_a_restart(instance, signals, monkeypatch, unreadable):
    """(j) B-32 (b3): a pending restore whose state file the file system refuses. ``POST /restart``: 500
    ``restore_state_unreadable``, never the 409 ``restore_not_pending``; the cause in the log, neither the system's words
    nor a path in the answer. No ticket written, no restart requested (``restore._restart`` never called, recorded as in
    B-31), no signal; nothing else written. Barrier: the restart opened the state file, and was refused."""
    root = instance.root
    write_state(root, "pending", api.UNKNOWN_ID)
    restarts: list[str] = []
    monkeypatch.setattr(restore, "_restart", lambda: restarts.append("restart"))
    before = api.tree(root)
    unreadable.now()

    with capture_logs() as events:
        response = await restart(answered=signals)

    assert unreadable.refused, f"barrier: the restart opened the state file ({unreadable.way}), and was refused"
    assert api.code(response) == (500, "restore_state_unreadable"), f"{unreadable.way}: 500 restore_state_unreadable, not {api.shown(response)}"
    assert cause_in_the_log(events, unreadable), f"{unreadable.way}: the cause in the server's log: {api.loud(events)}"
    assert (restarts, signals.sent, signals.around) == ([], [], []), f"{unreadable.way}: no restart requested, no signal: {restarts} {signals.sent} {signals.around}"
    assert not os.path.lexists(ticket_path(root)), f"{unreadable.way}: no ticket written"
    nothing_shown(response, root)
    unreadable.cure()
    assert api.tree(root) == before, f"{unreadable.way}: nothing written: {cases.changed(before, api.tree(root))}"
    print_success(f"{unreadable.way}: 500 restore_state_unreadable, no ticket, no restart")


@pytest.mark.asyncio
async def test_a_confirmation_while_the_state_cannot_be_read_is_500_and_replaces_nothing(instance, head_archive, unreadable):
    """(j) B-32 (b4): a pending restore whose state file the file system refuses, and a fresh check of another copy. Its
    confirmation: 500 ``restore_state_unreadable``, never the 202 that wrote a new state over one it could not read (a
    restore that may be half applied: its journal), nor a 409; the cause in the log, neither the system's words nor a
    path in the answer. The state file's bytes as they were, nothing else written; readable again, the first restore
    still waits. Barrier: the confirmation opened the state file, and was refused."""
    root = instance.root
    waiting = await confirmed(head_archive)
    fresh = await checked(head_archive)
    state_before = state_path(root).read_bytes()
    before = api.tree(root)
    unreadable.now()

    with capture_logs() as events:
        response = await confirm(fresh)

    assert unreadable.refused, f"barrier: the confirmation opened the state file ({unreadable.way}), and was refused"
    assert api.code(response) == (500, "restore_state_unreadable"), f"{unreadable.way}: 500 restore_state_unreadable, not {api.shown(response)}"
    assert cause_in_the_log(events, unreadable), f"{unreadable.way}: the cause in the server's log: {api.loud(events)}"
    nothing_shown(response, root)
    unreadable.cure()
    assert state_path(root).read_bytes() == state_before, f"{unreadable.way}: the state file's bytes as they were, not replaced"
    assert api.tree(root) == before, f"{unreadable.way}: nothing written: {cases.changed(before, api.tree(root))}"
    after = (await restore_status()).json()
    assert (after["state"], after["stage_id"]) == ("pending", waiting), f"{unreadable.way}: readable again, the first restore still waits: {after}"
    print_success(f"{unreadable.way}: 500 restore_state_unreadable, the state not replaced")


@pytest.mark.asyncio
async def test_the_outcome_of_a_restore_whose_state_cannot_be_read_is_the_one_404_its_ticket_kept(instance, unreadable):
    """(j) B-32 (b5), a GUARD: green before the code, and it must stay so. The outcome reads the state leniently: a state
    the file system refuses is no restore there, and ``GET /outcome`` with the ticket of the restart answers the one 404
    ``restore_outcome_not_found``, the cause in the log; the ticket left as it was. Readable again, the same ticket opens
    the outcome: ``pending``. Barrier: the outcome opened the state file, and was refused."""
    root = instance.root
    ticket = await restart_requested(root)
    kept = ticket_path(root).read_bytes()
    unreadable.now()

    with capture_logs() as events:
        response = await get_outcome(ticket)

    assert unreadable.refused, f"barrier: the outcome opened the state file ({unreadable.way}), and was refused"
    assert answer_of(response) == (404, NOT_FOUND), f"{unreadable.way}: the one 404 restore_outcome_not_found, not {api.shown(response)}"
    assert cause_in_the_log(events, unreadable), f"{unreadable.way}: the cause in the server's log: {api.loud(events)}"
    assert ticket_path(root).read_bytes() == kept, f"{unreadable.way}: the ticket as it was"
    unreadable.cure()
    again = await get_outcome(ticket)
    assert answer_of(again) == (200, {"state": "pending", "reason": None, "waiting": None}), f"{unreadable.way}: readable again, the same ticket opens the outcome: {api.shown(again)}"
    print_success(f"{unreadable.way}: the one 404, the ticket kept; readable again, pending")


#: B-41: the cases of (i) that present the RIGHT ticket of a restart that has not expired, with no restore or another
#: stage's: its holder reads the state, and one that cannot be read is the one 404 with its cause logged (b5). Every other
#: case of (i) is decided by the ticket alone.
READ_BY_ITS_HOLDER = {"no-restore", "a-restore-of-another-stage"}
#: B-41: built from ``NOT_OPENING`` by id, so that a case added to (i) is never left out without saying so.
DECIDED_BY_THE_TICKET = [case for case in NOT_OPENING if case.id not in READ_BY_ITS_HOLDER]


@pytest.mark.asyncio
@pytest.mark.parametrize("present", DECIDED_BY_THE_TICKET)
async def test_a_ticket_that_does_not_open_the_outcome_never_reads_the_state_nor_logs_it(instance, tmp_path, unreadable, present):
    """(j) B-41: ``GET /outcome`` answers anyone, without a session: a caller without the ticket of a restart that has not
    expired must never make LibreFolio open the restore's state, nor log that it cannot — else that error is anybody's
    to repeat, as often as asked. Every case of (i) the ticket alone decides (``NOT_OPENING`` but ``no-restore`` and
    ``a-restore-of-another-stage``, whose right ticket reads the state: b5), presented as (i) presents it, then the state
    file made unreadable in each way of (j): the ``unreadable`` fixture, every case three times, cheap in-process
    requests. ``dropped-by-a-cancel`` gets a pending state written back after its cancel, its ticket still gone. The one
    404 ``restore_outcome_not_found``; the state file never opened; «The state of the restore cannot be read» never
    logged, at any level. A ticket's file that cannot be used logs its own error (``its-file-…``): B-42, not asserted
    here. Barrier, once the route has answered: read directly, the state file is refused and its reader logs it — it was
    unreadable, and the log heard, all along.

    RED until B-41's code: the route reads the state before it looks at the ticket."""
    root = instance.root
    assert READ_BY_ITS_HOLDER <= {case.id for case in NOT_OPENING}, f"barrier: the cases left out are cases of (i): {sorted(READ_BY_ITS_HOLDER - {case.id for case in NOT_OPENING})}"
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    ticket = await restart_requested(root)
    presented = await present(Presenting(root, api.UNKNOWN_ID, ticket, elsewhere))
    if present is _dropped_by_a_cancel:
        # The cancel removed the state with the ticket: a state written back, its ticket still gone, to make unreadable.
        assert not os.path.lexists(ticket_path(root)), "precondition: the cancel dropped the ticket"
        write_state(root, "pending", api.UNKNOWN_ID)
    unreadable.now()
    case = f"{present.__name__}, {unreadable.way}"

    with capture_logs() as events:
        response = await get_outcome(presented.ticket, params=presented.params)
    tried = list(unreadable.refused)
    logged = [(event.get("log_level"), event.get("error")) for event in events if event.get("event") == STATE_READ_ERROR]
    with capture_logs() as heard, pytest.raises(apply_module().RestoreStateUnreadableError):
        apply_module().read_restore(root)

    assert len(unreadable.refused) == len(tried) + 1 and cause_in_the_log(heard, unreadable), f"barrier: {case}: read directly, the state file is refused and its reader logs it: {unreadable.refused} {api.loud(heard)}"
    assert answer_of(response) == (404, NOT_FOUND), f"{case}: the one 404 restore_outcome_not_found, not {api.shown(response)}"
    assert tried == [], f"{case}: the state file never opened for a ticket that does not open the outcome: {tried}"
    assert logged == [], f"{case}: «{STATE_READ_ERROR}» never logged, at any level: {logged}"
    print_success(f"{case}: the one 404, the state never opened, nothing logged of it")


def test_openapi_documents_the_state_that_cannot_be_read():
    """(j) B-32 (b6): ``GET /status`` documents a 500 whose description names ``restore_state_unreadable``; the 500s of
    ``DELETE /pending``, ``POST /restart`` and the confirmation name it too, beside their own codes."""
    document = api.restore_app().openapi()
    operations = {("GET", STATUS): "get", ("DELETE", PENDING): "delete", ("POST", RESTART): "post", ("POST", CONFIRM): "post"}
    described = {f"{method} {path}": document["paths"].get(path, {}).get(verb, {}).get("responses", {}).get("500", {}).get("description", "") for (method, path), verb in operations.items()}
    undocumented = sorted(operation for operation, description in described.items() if "restore_state_unreadable" not in description)
    assert undocumented == [], f"a 500 naming restore_state_unreadable, missing from: {undocumented}"
    print_success("restore_state_unreadable documented: status, cancel, restart, confirmation")


# =============================================================================
# (k) Lot L3-2: confirmed_via
# =============================================================================

#: Administrators whose username is one of the other ways to confirm: the username never decides ``confirmed_via``.
ADMIN_NAMED_CLI = SimpleNamespace(id=8, username="cli", is_superuser=True)
ADMIN_NAMED_PANEL = SimpleNamespace(id=9, username="panel", is_superuser=True)


def write_recorded_state(root: Path, stage_id: str, *, confirmed_by: str, confirmed_via: str | None) -> dict[str, Any]:
    """A pending restore's ``restore.json``, written by hand: ``confirmed_via`` as given, or no such key (``None``), as
    a state written before L3-2. The record."""
    record: dict[str, Any] = {
        "format": 1,
        "status": "pending",
        "stage_id": stage_id,
        "data_dir": str(root.resolve()),
        "confirmed_at": CONFIRMED_AT.isoformat(),
        "confirmed_by": confirmed_by,
        "backup_created_at": BACKUP_CREATED_AT.isoformat(),
        "backup_app_version": "v1.2.0",
        "action": "same",
    }
    if confirmed_via is not None:
        record["confirmed_via"] = confirmed_via
    path = state_path(root)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_text(json.dumps(record), encoding="utf-8")
    path.chmod(0o600)
    return record


@pytest.mark.asyncio
@pytest.mark.parametrize("user", [B3_ADMIN, ADMIN_NAMED_CLI, ADMIN_NAMED_PANEL], ids=["b3-admin", "named-cli", "named-panel"])
async def test_the_administrators_route_confirms_via_admin_whatever_the_username(instance, head_archive, user):
    """(k) L3-2: a confirmation through ``POST /backup/restore/stage/{id}/confirm`` answers ``confirmed_via`` ``admin``
    and ``confirmed_by`` the username, writes ``admin`` in ``restore.json``, and ``GET /status`` says the same — for an
    administrator literally named ``cli`` or ``panel`` too."""
    print_section(f"(k) L3-2 confirmed_via, {user.username}")
    stage_id = await checked(head_archive)
    response = await confirm(stage_id, user=user)
    assert response.status_code == 202, f"precondition: confirmed: {api.shown(response)}"
    body = response.json()
    assert (body["confirmed_by"], body.get("confirmed_via", "<missing>")) == (user.username, "admin"), f"confirmed by {user.username}, via admin: {body}"
    written = json.loads(state_path(instance.root).read_text(encoding="utf-8")).get("confirmed_via", "<missing>")
    assert written == "admin", f"restore.json says via admin: {written!r}"
    status = await restore_status()
    assert status.json().get("confirmed_via", "<missing>") == "admin", f"GET /status says via admin: {status.json()}"
    print_success(f"{user.username}: via admin")


#: ``restore.json`` as recorded → what ``GET /status`` says: ``confirmed_by``, ``confirmed_via`` (None: no key, a state
#: of before L3-2), and the ``confirmed_via`` answered.
RECORDED_VIA = [
    pytest.param("panel", "panel", "panel", id="via-panel"),
    pytest.param("cli", "cli", "cli", id="via-cli"),
    pytest.param("b3-admin", "admin", "admin", id="via-admin"),
    pytest.param("cli", None, "cli", id="before-l3-2-cli"),
    pytest.param("b3-admin", None, "admin", id="before-l3-2-an-administrator"),
    pytest.param("panel", None, "admin", id="before-l3-2-an-administrator-named-panel"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("confirmed_by", "recorded", "answered"), RECORDED_VIA)
async def test_the_status_says_confirmed_via_as_recorded(instance, confirmed_by, recorded, answered):
    """(k) L3-2: ``GET /status`` answers ``confirmed_via`` as ``restore.json`` records it; a state written before L3-2
    (no key) answers ``cli`` when ``confirmed_by`` is ``cli``, ``admin`` otherwise. ``confirmed_by`` as recorded."""
    write_recorded_state(instance.root, api.UNKNOWN_ID, confirmed_by=confirmed_by, confirmed_via=recorded)
    response = await restore_status()
    assert response.status_code == 200, api.shown(response)
    body = response.json()
    assert (body["state"], body["confirmed_by"], body.get("confirmed_via", "<missing>")) == ("pending", confirmed_by, answered), f"{confirmed_by!r}/{recorded!r}: via {answered}: {body}"
    print_success(f"{confirmed_by!r}, recorded {recorded!r}: via {answered}")


@pytest.mark.asyncio
async def test_without_a_restore_confirmed_via_is_null(instance):
    """(k) L3-2: ``none`` answers ``confirmed_via`` null, present."""
    response = await restore_status()
    body = response.json()
    assert (response.status_code, body["state"], body.get("confirmed_via", "<missing>")) == (200, "none", None), f"none: confirmed_via null: {body}"


# =============================================================================
# (m) B-33 §1: a state that is not a file or not valid
# =============================================================================


#: (m) What a state nobody can read holds: never in an answer.
B33_STATE_MARK = "b33-the-content-of-a-state-nobody-can-read"


def _b33_a_folder(root: Path, elsewhere: Path) -> None:
    state_path(root).unlink()
    state_path(root).mkdir(mode=0o700)
    (state_path(root) / "inside.json").write_text(B33_STATE_MARK, encoding="utf-8")


def _b33_a_link(root: Path, elsewhere: Path) -> None:
    # A link to the valid state it replaced: never followed, so never read.
    target = elsewhere / "restore.json"
    state_path(root).rename(target)
    state_path(root).symlink_to(target)


def _b33_not_json(root: Path, elsewhere: Path) -> None:
    state_path(root).write_text("{" + B33_STATE_MARK, encoding="utf-8")


def _b33_format_2(root: Path, elsewhere: Path) -> None:
    record = json.loads(state_path(root).read_text(encoding="utf-8"))
    state_path(root).write_text(json.dumps({**record, "format": 2}), encoding="utf-8")


#: (m) B-33 §1: a pending restore's state made one that cannot be read, not as a file (a folder, a link) or not as a
#: state (not JSON, ``format`` 2).
B33_WAYS = [
    pytest.param(_b33_a_folder, id="not_a_file-a-folder"),
    pytest.param(_b33_a_link, id="not_a_file-a-link", marks=pytest.mark.skipif(os.name == "nt", reason="symbolic links need a privilege on Windows")),
    pytest.param(_b33_not_json, id="invalid-not-json"),
    pytest.param(_b33_format_2, id="invalid-format-2"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("way", B33_WAYS)
@pytest.mark.parametrize("route", ["status", "cancel", "restart", "confirm"])
async def test_a_state_that_is_not_a_file_or_not_valid_is_a_500_of_every_route_and_nothing_changes(instance, head_archive, tmp_path, monkeypatch, signals, route, way):
    """(m) B-33 §1: a pending restore whose ``restore.json`` is a folder, a link, not JSON, or of ``format`` 2. ``GET
    /status``, ``DELETE /pending``, ``POST /restart`` and the confirmation of a fresh check: 500
    ``restore_state_unreadable`` (the status with (j)'s message), never ``none``, the 404 or 409 ``restore_not_pending``,
    nor a 202 that wrote a new state over it; neither the state's content nor a path in the answer; no restart requested,
    no signal, no ticket; nothing written, removed or replaced, here or where a link points. Red before B-33: the state
    read as none."""
    print_section("(m) B-33: a state that is not a file or not valid")
    root = instance.root
    fresh = None
    if route == "confirm":
        await confirmed(head_archive)
        fresh = await checked(head_archive)
    else:
        write_state(root, "pending", api.UNKNOWN_ID)
    restarts: list[str] = []
    monkeypatch.setattr(restore, "_restart", lambda: restarts.append("restart"))
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    way(root, elsewhere)
    before = (api.tree(root), api.tree(elsewhere))
    calls = {"status": restore_status, "cancel": cancel, "restart": restart, "confirm": lambda: confirm(fresh)}
    response = await calls[route]()
    case = f"{route}, {way.__name__}"
    if route == "status":
        assert api.refusal(response) == (500, "restore_state_unreadable", STATE_UNREADABLE), f"{case}: 500 restore_state_unreadable, not {api.shown(response)}"
    else:
        assert api.code(response) == (500, "restore_state_unreadable"), f"{case}: 500 restore_state_unreadable, not {api.shown(response)}"
    assert B33_STATE_MARK not in response.text, f"{case}: never the state's content: {response.text}"
    no_path_in(response, root)
    assert (restarts, signals.sent, signals.around) == ([], [], []), f"{case}: no restart requested, no signal: {restarts} {signals.sent} {signals.around}"
    assert not os.path.lexists(ticket_path(root)), f"{case}: no ticket written"
    assert (api.tree(root), api.tree(elsewhere)) == before, f"{case}: nothing written, removed or replaced: {cases.changed(before[0], api.tree(root))}"
    print_success(f"{case}: 500 restore_state_unreadable, nothing changed")


# =============================================================================
# (n) The reason of a state that cannot be read, in the answer
# =============================================================================


def _n_refused_eio(root: Path, elsewhere: Path, monkeypatch: pytest.MonkeyPatch) -> UnreadableState:
    state = UnreadableState(root, "EIO", monkeypatch)
    state.now()
    return state


def _n_shape(way: Callable[[Path, Path], None]) -> Callable[[Path, Path, pytest.MonkeyPatch], None]:
    def made(root: Path, elsewhere: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        way(root, elsewhere)

    made.__name__ = way.__name__
    return made


#: (n) Each way a pending restore's state cannot be read, and the ``reason`` the answer must give.
REASON_WAYS = [
    pytest.param(_n_refused_eio, "io", id="io-EIO"),
    pytest.param(_n_shape(_b33_a_folder), "not_a_file", id="not_a_file-a-folder"),
    pytest.param(_n_shape(_b33_a_link), "not_a_file", id="not_a_file-a-link", marks=pytest.mark.skipif(os.name == "nt", reason="symbolic links need a privilege on Windows")),
    pytest.param(_n_shape(_b33_not_json), "invalid", id="invalid-not-json"),
    pytest.param(_n_shape(_b33_format_2), "invalid", id="invalid-format-2"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("way", "reason"), REASON_WAYS)
@pytest.mark.parametrize("route", ["status", "confirm", "cancel", "restart"])
async def test_every_route_says_why_the_state_cannot_be_read(instance, head_archive, tmp_path, monkeypatch, signals, route, way, reason):
    """(n) A pending restore whose state cannot be read, in each way: ``GET /status``, the confirmation of a fresh check,
    ``DELETE /pending`` and ``POST /restart`` answer 500, ``detail`` exactly ``code`` ``restore_state_unreadable``,
    (j)'s message and ``reason`` the reader's (``io``, ``not_a_file``, ``invalid``); no restart requested, no signal.
    Red until the cure: the detail carries no ``reason``."""
    print_section("(n) The reason of a state that cannot be read")
    root = instance.root
    fresh = None
    if route == "confirm":
        await confirmed(head_archive)
        fresh = await checked(head_archive)
    else:
        write_state(root, "pending", api.UNKNOWN_ID)
    restarts: list[str] = []
    monkeypatch.setattr(restore, "_restart", lambda: restarts.append("restart"))
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    made = way(root, elsewhere, monkeypatch)
    calls = {"status": restore_status, "cancel": cancel, "restart": restart, "confirm": lambda: confirm(fresh)}
    try:
        response = await calls[route]()
    finally:
        if isinstance(made, UnreadableState):
            made.cure()
    case = f"{route}, {way.__name__}"
    if isinstance(made, UnreadableState):
        assert made.refused, f"barrier: {case}: the route opened the state file, and was refused"
    detail = response.json().get("detail") if "json" in response.headers.get("content-type", "") else None
    assert response.status_code == 500 and isinstance(detail, dict) and detail.get("code") == "restore_state_unreadable", f"{case}: 500 restore_state_unreadable, not {api.shown(response)}"
    assert detail == {"code": "restore_state_unreadable", "message": STATE_UNREADABLE, "reason": reason}, f"{case}: the detail with reason {reason!r}, and nothing else: {detail}"
    assert (restarts, signals.sent) == ([], []), f"{case}: no restart requested, no signal: {restarts} {signals.sent}"
    print_success(f"{case}: 500 restore_state_unreadable, reason {reason}")


def test_openapi_names_the_reason_of_a_state_that_cannot_be_read():
    """(n) The OpenAPI description of the 500 of ``GET /status`` names ``reason`` beside ``restore_state_unreadable``.
    Red until the cure."""
    document = api.restore_app().openapi()
    described = document["paths"].get(STATUS, {}).get("get", {}).get("responses", {}).get("500", {}).get("description", "")
    assert "restore_state_unreadable" in described and "reason" in described, f"the status's 500 names restore_state_unreadable and reason: {described!r}"
    print_success("the status's 500 names reason")


# =============================================================================
# (o) Lot B5-1: the owner's choice
# =============================================================================

OWNER_EMAIL_VARIABLE = "LIBREFOLIO_ADMIN_EMAIL"
OWNER_SIDE_VARIABLES = ("LIBREFOLIO_ADMIN_USERNAME", "LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN", "LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN_FILE")
#: The candidates' fields as the administrators' view shows them.
#: B5-1: is_superuser and is_active as the backup holds them, the labels of A's OwnerChoiceModal (its signature, 23/10).
VIEW_CANDIDATE_FIELDS = {"user_id", "username", "email", "owner_email", "administrator", "is_superuser", "is_active"}
#: The value of a stale ``owner_reset_path`` key in a state file of an older LibreFolio: never in an answer (R13: the
#: state no longer has the field, the owner's link is in the instance log only).
STALE_RESET_PATH = "/reset-password#token=b51-api-secret-never-in-an-answer-0123456789"


@dataclass(frozen=True)
class OwnerArchive:
    """A backup at the head whose accounts are ``test_backup_staging.OWNER_ACCOUNTS`` (``owen_user`` holding the owner's
    email in another case), and each account as the copy describes it, by username."""

    archive: Any
    accounts: dict[str, dict[str, Any]]


@pytest.fixture(scope="module")
def owner_archive(databases, tmp_path_factory) -> OwnerArchive:
    root = tmp_path_factory.mktemp("b51-owner-archive")
    with pytest.MonkeyPatch.context() as patch:
        cases.configure(patch, root / "configured-data-dir")
        try:
            archive, described = cases.backup_with_accounts(root, databases, cases.OWNER_ACCOUNTS)
        finally:
            cases.get_git_version.cache_clear()
    assert not (root / "configured-data-dir").exists(), "precondition: the archive was built without writing in the configured data directory"
    return OwnerArchive(archive=archive, accounts=described)


def owner_setting(monkeypatch: pytest.MonkeyPatch, profile: str, owner_email: str | None) -> None:
    """The profile and the owner's email of this process, the other F02 variables unset."""
    monkeypatch.setenv(api.PROFILE_VARIABLE, profile)
    for name in OWNER_SIDE_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    if owner_email is None:
        monkeypatch.delenv(OWNER_EMAIL_VARIABLE, raising=False)
    else:
        monkeypatch.setenv(OWNER_EMAIL_VARIABLE, owner_email)


def configured_owner_email() -> str:
    """The owner's email as the configuration reads it (``admin_bootstrap_config()``)."""
    from backend.app.config.accounts import admin_bootstrap_config  # noqa: PLC0415

    config = admin_bootstrap_config()
    assert config is not None, "precondition: the owner's email is set"
    return config.email


async def confirm_with(stage_id: str, body: Any) -> httpx.Response:
    """The confirmation with a JSON body (``body`` as given)."""
    return await api.call("POST", CONFIRM.format(stage_id=stage_id), user=B3_ADMIN, json=body)


def owner_on_disk(root: Path) -> tuple[Any, Any]:
    """The owner's keys of ``restore.json``: id, outcome. The file never holds an ``owner_reset_path`` key."""
    record = json.loads(state_path(root).read_text(encoding="utf-8"))
    assert "owner_reset_path" not in record, f"no owner_reset_path key in the state: {sorted(record)}"
    return tuple(record.get(name, "<missing>") for name in ("owner_user_id", "owner_outcome"))


@pytest.mark.asyncio
async def test_the_managed_report_offers_the_owner_s_choice(instance, owner_archive, monkeypatch):
    """(o) B5-1: ``managed``, the owner's email set: the report of a finished check carries ``owner_choice``, the owner's
    email holder forced, the candidates by username with their emails, whether each holds the owner's email and is an
    active administrator."""
    print_section("(o) B5-1 the owner's choice in the report")
    owner_setting(monkeypatch, "managed", cases.OWNER_EMAIL)
    stage_id = await checked(owner_archive.archive)
    response = await api.poll(stage_id, user=B3_ADMIN)
    assert response.status_code == 200, api.shown(response)
    report = response.json()["report"]
    assert "owner_choice" in report, f"[new] B5-1: the report has no owner_choice yet: {sorted(report)}"
    choice = report["owner_choice"]
    accounts = owner_archive.accounts
    expected_candidates = [
        {"user_id": accounts[name]["user_id"], "username": name, "email": accounts[name]["email"], "owner_email": name == "owen_user", "administrator": name != "owen_user", "is_superuser": accounts[name]["is_superuser"], "is_active": accounts[name]["is_active"]}
        for name in cases.CANDIDATES_WITH_OWNER
    ]
    expected = {"required": True, "owner_email": configured_owner_email(), "forced_user_id": accounts["owen_user"]["user_id"], "candidates": expected_candidates}
    assert choice == expected, f"the owner's choice: {choice}"
    print_success(f"forced {choice['forced_user_id']}, {len(choice['candidates'])} candidates")


@pytest.mark.asyncio
async def test_a_managed_report_without_an_owner_s_email_holder_forces_nobody(instance, head_archive, monkeypatch):
    """(o) B5-1: ``managed``, nobody in the backup holding the owner's email: ``forced_user_id`` null, the candidates the
    active administrators, none holding the owner's email."""
    owner_setting(monkeypatch, "managed", "nobody.b51@example.com")
    stage_id = await checked(head_archive)
    report = (await api.poll(stage_id, user=B3_ADMIN)).json()["report"]
    assert "owner_choice" in report, f"[new] B5-1: the report has no owner_choice yet: {sorted(report)}"
    choice = report["owner_choice"]
    assert (choice["required"], choice["forced_user_id"]) == (True, None), f"required, nobody forced: {choice}"
    assert [(candidate["username"], candidate["owner_email"], candidate["administrator"]) for candidate in choice["candidates"]] == [(name, False, True) for name in cases.ADMINISTRATORS], f"the active administrators: {choice['candidates']}"
    assert all(set(candidate) == VIEW_CANDIDATE_FIELDS for candidate in choice["candidates"]), f"each candidate has exactly {sorted(VIEW_CANDIDATE_FIELDS)}: {choice['candidates']}"
    print_success("nobody forced")


@pytest.mark.asyncio
async def test_a_self_hosted_report_offers_no_owner_s_choice(instance, owner_archive, monkeypatch):
    """(o) B5-1: ``selfhosted``, the owner's email set or not: ``owner_choice`` null."""
    owner_setting(monkeypatch, "selfhosted", cases.OWNER_EMAIL)
    stage_id = await checked(owner_archive.archive)
    report = (await api.poll(stage_id, user=B3_ADMIN)).json()["report"]
    assert "owner_choice" in report and report["owner_choice"] is None, f"self-hosted: owner_choice null: {report.get('owner_choice', '<missing>')}"
    print_success("selfhosted: null")


@pytest.mark.asyncio
async def test_a_managed_confirmation_naming_the_forced_owner_is_accepted_and_recorded(instance, owner_archive, monkeypatch):
    """(o) B5-1: ``managed``: the body ``{owner_user_id}`` naming the holder of the owner's email: 202, a
    ``RestoreStatus``, nothing of the owner; ``restore.json`` records the id."""
    print_section("(o) B5-1 the owner's choice confirmed")
    owner_setting(monkeypatch, "managed", cases.OWNER_EMAIL)
    stage_id = await checked(owner_archive.archive)
    owen = owner_archive.accounts["owen_user"]["user_id"]
    response = await confirm_with(stage_id, {"owner_user_id": owen})
    assert response.status_code == 202, f"the forced owner is confirmed: {api.shown(response)}"
    body = response.json()
    assert set(body) == STATUS_FIELDS, f"a RestoreStatus, nothing of the owner: {body}"
    assert owner_on_disk(instance.root) == (owen, None), f"restore.json records the owner: {owner_on_disk(instance.root)}"
    print_success(f"202, owner {owen}")


#: (the owner's email at the confirmation, the body, the code). ``None`` body: no body at all.
MANAGED_REFUSALS = [
    pytest.param(cases.OWNER_EMAIL, None, "owner_choice_required", id="no-body"),
    pytest.param(cases.OWNER_EMAIL, {"owner_user_id": None}, "owner_choice_required", id="owner-null"),
    pytest.param(cases.OWNER_EMAIL, {"owner_user_id": "ada_admin"}, "owner_choice_invalid", id="another-administrator-while-forced"),
    pytest.param(cases.OWNER_EMAIL, {"owner_user_id": 999_999}, "owner_choice_invalid", id="not-a-candidate"),
    pytest.param(None, {"owner_user_id": "ada_admin"}, "owner_email_not_set", id="owner-email-unset"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("owner_email", "body", "code"), MANAGED_REFUSALS)
async def test_a_managed_confirmation_without_a_valid_owner_choice_is_409_and_writes_nothing(instance, owner_archive, monkeypatch, owner_email, body, code):
    """(o) B5-1: ``managed``: no choice, a choice the candidates do not allow, the owner's email unset (at the
    confirmation): 409 with its code; no state written, the copy and its check as they were."""
    owner_setting(monkeypatch, "managed", cases.OWNER_EMAIL)
    stage_id = await checked(owner_archive.archive)
    owner_setting(monkeypatch, "managed", owner_email)
    if isinstance(body, dict) and isinstance(body.get("owner_user_id"), str):
        body = {"owner_user_id": owner_archive.accounts[body["owner_user_id"]]["user_id"]}
    copy_before = api.tree(stage_dir(instance.root, stage_id))
    response = await (confirm(stage_id) if body is None else confirm_with(stage_id, body))
    assert api.code(response) == (409, code), f"409 {code}: {api.shown(response)}"
    assert not os.path.lexists(state_path(instance.root)), "nothing confirmed: no state written"
    assert api.tree(stage_dir(instance.root, stage_id)) == copy_before and check_state_path(instance.root, stage_id).is_file(), "the copy and its check as they were"
    status = (await restore_status()).json()
    assert status["state"] == "none", f"no restore waits: {status}"
    print_success(f"409 {code}, nothing written")


@pytest.mark.asyncio
async def test_a_self_hosted_confirmation_naming_an_owner_is_400_and_writes_nothing(instance, owner_archive, monkeypatch):
    """(o) B5-1: ``selfhosted``: an owner id in the body is 400 ``owner_choice_not_applicable``, nothing written; the
    same confirmation without it is 202, no owner recorded (a guard)."""
    owner_setting(monkeypatch, "selfhosted", cases.OWNER_EMAIL)
    stage_id = await checked(owner_archive.archive)
    refused = await confirm_with(stage_id, {"owner_user_id": owner_archive.accounts["ada_admin"]["user_id"]})
    assert api.code(refused) == (400, "owner_choice_not_applicable"), f"400 owner_choice_not_applicable: {api.shown(refused)}"
    assert not os.path.lexists(state_path(instance.root)), "nothing confirmed: no state written"
    accepted = await confirm(stage_id)
    assert accepted.status_code == 202, f"without the owner, confirmed: {api.shown(accepted)}"
    assert owner_on_disk(instance.root) == (None, None), f"no owner recorded: {owner_on_disk(instance.root)}"
    print_success("selfhosted with an owner: 400; without: 202")


@pytest.mark.asyncio
@pytest.mark.parametrize("profile", ["managed", "selfhosted"])
async def test_a_confirmation_body_with_an_unknown_key_is_422(instance, owner_archive, monkeypatch, profile):
    """(o) B5-1: ``RestoreConfirmRequest`` forbids any other key: 422, nothing written."""
    owner_setting(monkeypatch, profile, cases.OWNER_EMAIL)
    stage_id = await checked(owner_archive.archive)
    owen = owner_archive.accounts["owen_user"]["user_id"]
    response = await confirm_with(stage_id, {"owner_user_id": owen, "owner_email": "attacker.b51@example.com"})
    assert response.status_code == 422, f"{profile}: an unknown key is 422: {api.shown(response)}"
    assert not os.path.lexists(state_path(instance.root)), "nothing confirmed: no state written"
    print_success(f"{profile}: 422")


@pytest.mark.asyncio
@pytest.mark.parametrize("outcome", ["sent", "link_only", "error:EMAIL_TAKEN", None])
async def test_the_status_says_the_owner_s_outcome_never_the_id_nor_the_path(instance, outcome):
    """(o) B5-1: ``GET /status`` of a committed restore says nothing of the owner's account: neither its outcome (told on the
    server by ``dev.py backup pending``), nor ``owner_user_id``, nor a reset path. The state file is written with a stale
    ``owner_reset_path`` key (an older LibreFolio): it is ignored, the status is a 200 without it (R13)."""
    root = instance.root
    write_state(root, "committed", api.UNKNOWN_ID)
    path = state_path(root)
    record = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(json.dumps({**record, "confirmed_via": "admin", "owner_user_id": 42, "owner_outcome": outcome, "owner_reset_path": STALE_RESET_PATH}), encoding="utf-8")
    response = await restore_status()
    assert response.status_code == 200, api.shown(response)
    body = response.json()
    assert set(body) == STATUS_FIELDS, f"nothing of the owner with outcome {outcome!r}: {body}"
    assert "owner_user_id" not in body and "owner_reset_path" not in body, f"never the id nor the path: {sorted(body)}"
    assert "b51-api-secret" not in response.text and "reset-password" not in response.text, f"the reset path never in the answer: {response.text}"
    print_success(f"owner_outcome {outcome!r}")


def test_openapi_documents_the_owner_s_choice():
    """(o) B5-1: the confirmation documents its body (``RestoreConfirmRequest``, optional, ``owner_user_id`` its only
    property), its 409s ``owner_choice_required``, ``owner_choice_invalid``, ``owner_email_not_set`` and its 400
    ``owner_choice_not_applicable``; ``RestoreStageReport`` has ``owner_choice``; ``RestoreStatus`` nothing of the owner."""
    document = api.restore_app().openapi()
    operation = document["paths"][CONFIRM]["post"]
    responses = operation["responses"]
    missing = {status: [name for name in names if name not in responses.get(status, {}).get("description", "")] for status, names in (("409", ["owner_choice_required", "owner_choice_invalid", "owner_email_not_set"]), ("400", ["owner_choice_not_applicable"]))}
    assert missing == {"409": [], "400": []}, f"the confirmation documents the owner's refusals: missing {missing}"
    body = operation.get("requestBody", {})
    assert not body.get("required", False), f"the body is optional: {body}"
    schemas = document["components"]["schemas"]
    assert "RestoreConfirmRequest" in schemas and set(schemas["RestoreConfirmRequest"].get("properties", {})) == {"owner_user_id"}, f"RestoreConfirmRequest {{owner_user_id}}: {schemas.get('RestoreConfirmRequest')}"
    assert schemas["RestoreConfirmRequest"].get("additionalProperties") is False, "RestoreConfirmRequest forbids other keys"
    assert "owner_choice" in schemas["RestoreStageReport"]["properties"], f"RestoreStageReport has owner_choice: {sorted(schemas['RestoreStageReport']['properties'])}"
    assert "owner_outcome" not in schemas["RestoreStatus"]["properties"], "RestoreStatus says nothing of the owner (H's panel status is built from it)"
    print_success("OpenAPI: body, 409s, 400, owner_choice")


# -----------------------------------------------------------------------------
# (o) Lot B5-1, security addendum §7.2 at the route
# -----------------------------------------------------------------------------

#: A backup whose two accounts differ only by the case of their usernames: ``duplicate_username`` (§7.1).
CONFLICTED_ACCOUNTS = (*cases.OWNER_ACCOUNTS, ("BOB_USER", "bob2.b51@example.com", 1, 0))


@pytest.fixture(scope="module")
def conflicted_archive(databases, tmp_path_factory) -> OwnerArchive:
    """``owner_archive`` with one more account, ``BOB_USER``, beside ``bob_user``."""
    root = tmp_path_factory.mktemp("b51-conflicted-archive")
    with pytest.MonkeyPatch.context() as patch:
        cases.configure(patch, root / "configured-data-dir")
        try:
            archive, described = cases.backup_with_accounts(root, databases, CONFLICTED_ACCOUNTS)
        finally:
            cases.get_git_version.cache_clear()
    assert not (root / "configured-data-dir").exists(), "precondition: the archive was built without writing in the configured data directory"
    return OwnerArchive(archive=archive, accounts=described)


@pytest.mark.asyncio
async def test_a_managed_confirmation_after_the_owner_s_address_changed_is_409_outdated(instance, owner_archive, monkeypatch):
    """(o) B5-1 §7.2: the archive checked with the owner's address, the address changed before the confirmation: 409
    ``restore_stage_outdated`` for the forced choice of the check; nothing written."""
    print_section("(o) B5-1 §7.2 the owner's address changed since the check")
    owner_setting(monkeypatch, "managed", cases.OWNER_EMAIL)
    stage_id = await checked(owner_archive.archive)
    owner_setting(monkeypatch, "managed", "someone.else.b51@example.com")
    copy_before = api.tree(stage_dir(instance.root, stage_id))
    response = await confirm_with(stage_id, {"owner_user_id": owner_archive.accounts["owen_user"]["user_id"]})
    assert api.code(response) == (409, "restore_stage_outdated"), f"409 restore_stage_outdated: {api.shown(response)}"
    assert not os.path.lexists(state_path(instance.root)), "nothing confirmed: no state written"
    assert api.tree(stage_dir(instance.root, stage_id)) == copy_before, "the copy as it was"
    print_success("409 restore_stage_outdated")


@pytest.mark.asyncio
async def test_a_managed_confirmation_after_a_case_only_change_of_the_owner_s_address_is_accepted(instance, owner_archive, monkeypatch):
    """(o) B5-1 §7.2: the same address in another A–Z case is the same: 202, the owner recorded (a guard)."""
    owner_setting(monkeypatch, "managed", cases.OWNER_EMAIL)
    stage_id = await checked(owner_archive.archive)
    owner_setting(monkeypatch, "managed", cases.OWNER_EMAIL.swapcase())
    owen = owner_archive.accounts["owen_user"]["user_id"]
    response = await confirm_with(stage_id, {"owner_user_id": owen})
    assert response.status_code == 202, f"a case-only change: confirmed: {api.shown(response)}"
    assert owner_on_disk(instance.root) == (owen, None), f"restore.json records the owner: {owner_on_disk(instance.root)}"
    print_success("case only: 202")


@pytest.mark.asyncio
@pytest.mark.parametrize("chosen", ["owen_user", "ada_admin", None], ids=["the-forced-user", "an-administrator", "no-body"])
async def test_a_managed_confirmation_of_a_copy_with_owner_conflicts_is_409_owner_conflict(instance, conflicted_archive, monkeypatch, chosen):
    """(o) B5-1 §7.2: a check that found a conflict (two usernames equal case aside): 409 ``owner_conflict`` whatever
    the choice; nothing written."""
    print_section("(o) B5-1 §7.2 owner_conflict")
    owner_setting(monkeypatch, "managed", cases.OWNER_EMAIL)
    stage_id = await checked(conflicted_archive.archive)
    copy_before = api.tree(stage_dir(instance.root, stage_id))
    response = await (confirm(stage_id) if chosen is None else confirm_with(stage_id, {"owner_user_id": conflicted_archive.accounts[chosen]["user_id"]}))
    assert api.code(response) == (409, "owner_conflict"), f"{chosen}: 409 owner_conflict: {api.shown(response)}"
    assert not os.path.lexists(state_path(instance.root)), "nothing confirmed: no state written"
    assert api.tree(stage_dir(instance.root, stage_id)) == copy_before, "the copy as it was"
    print_success(f"{chosen}: 409 owner_conflict")


def test_openapi_documents_the_owner_conflict():
    """(o) B5-1 §7.2: the confirmation's 409 names ``owner_conflict``."""
    described = api.restore_app().openapi()["paths"][CONFIRM]["post"]["responses"].get("409", {}).get("description", "")
    assert "owner_conflict" in described.replace("owner_conflicts", ""), f"the 409 names owner_conflict: {described!r}"
    print_success("OpenAPI: owner_conflict")


# -----------------------------------------------------------------------------
# (o) Lot B5-1g: a pending administrator in the backup, and a backup with no active administrator
# -----------------------------------------------------------------------------
#
# Admin-bootstrap runs before ``restore-commit`` at the first start: an inactive account with an admin-setup link nobody
# used takes the owner's address unless some account holds it, and A's assignment then fails with EMAIL_TAKEN for good.
# So the check names it (``pending_administrator``, in the owner's conflicts) and the confirmation is refused
# ``owner_conflict``. And a backup with no ACTIVE administrator is not restorable at all (blocker ``no_administrator``):
# the confirmation is refused ``restore_not_restorable`` on a managed instance whatever owner it names.

ADA_ACCOUNT = ("ada_admin", "ada.b51@example.com", 1, 1)
PENDING_ACCOUNT = ("pend_admin", "pend.b51@example.com", 0, 1)
HOLDER_ACCOUNT = ("owen_user", cases.OWNER_EMAIL_STORED, 1, 0)
SETUP_LINK = [("pend_admin", "admin_setup", False)]


def built_archives(root: Path, databases: Any, recipes: dict[str, dict[str, Any]]) -> dict[str, OwnerArchive]:
    """One archive per recipe, ``cases.crafted_backup``'s arguments, built without writing in the configured data
    directory; each with its accounts by username as a candidate would describe them (ids 1, 2, … in the order given)."""
    built: dict[str, OwnerArchive] = {}
    for name, recipe in recipes.items():
        with pytest.MonkeyPatch.context() as patch:
            cases.configure(patch, root / f"configured-{name}")
            try:
                archive = cases.crafted_backup(root / name, databases, **recipe)
            finally:
                cases.get_git_version.cache_clear()
        assert not (root / f"configured-{name}").exists(), "precondition: the archive was built without writing in the configured data directory"
        built[name] = OwnerArchive(archive=archive, accounts={account[0]: {"user_id": number} for number, account in enumerate(recipe["accounts"], start=1)})
    return built


@pytest.fixture(scope="module")
def pending_archives(databases, tmp_path_factory) -> dict[str, OwnerArchive]:
    root = tmp_path_factory.mktemp("b51g-pending-archives")
    return built_archives(
        root,
        databases,
        {
            "alone": {"accounts": (ADA_ACCOUNT, PENDING_ACCOUNT), "tokens": SETUP_LINK},
            "address-held": {"accounts": (ADA_ACCOUNT, PENDING_ACCOUNT, HOLDER_ACCOUNT), "tokens": SETUP_LINK},
        },
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("chosen", ["ada_admin", None], ids=["a-valid-choice", "no-body"])
async def test_a_managed_confirmation_of_a_copy_with_a_pending_administrator_is_409_owner_conflict(instance, pending_archives, monkeypatch, chosen):
    """(o) B5-1g: a backup holding an administrator that waits for its setup (inactive, an admin-setup link unused) while no
    account holds the owner's address: the check ends restorable, and the confirmation is 409 ``owner_conflict``
    whatever the choice; nothing written. Red before B5-1g: the check found no conflict and the confirmation was 202."""
    print_section("(o) B5-1g pending administrator: 409 owner_conflict")
    owner_setting(monkeypatch, "managed", cases.OWNER_EMAIL)
    archive = pending_archives["alone"]
    stage_id = await checked(archive.archive)
    copy_before = api.tree(stage_dir(instance.root, stage_id))
    response = await (confirm(stage_id) if chosen is None else confirm_with(stage_id, {"owner_user_id": archive.accounts[chosen]["user_id"]}))
    assert api.code(response) == (409, "owner_conflict"), f"{chosen}: 409 owner_conflict: {api.shown(response)}"
    assert not os.path.lexists(state_path(instance.root)), "nothing confirmed: no state written"
    assert api.tree(stage_dir(instance.root, stage_id)) == copy_before, "the copy as it was"
    print_success(f"{chosen}: 409 owner_conflict")


@pytest.mark.asyncio
async def test_a_pending_administrator_does_not_refuse_the_confirmation_when_another_account_holds_the_owner_s_address(instance, pending_archives, monkeypatch):
    """(o) B5-1g, the guard: the same pending administrator, but another account of the backup holds the owner's address:
    no conflict, the forced choice is 202 and recorded. Green before B5-1g, and it must stay so."""
    owner_setting(monkeypatch, "managed", cases.OWNER_EMAIL)
    archive = pending_archives["address-held"]
    stage_id = await checked(archive.archive)
    owen = archive.accounts["owen_user"]["user_id"]
    response = await confirm_with(stage_id, {"owner_user_id": owen})
    assert response.status_code == 202, f"another account holds the address: confirmed: {api.shown(response)}"
    assert owner_on_disk(instance.root) == (owen, None), f"restore.json records the owner: {owner_on_disk(instance.root)}"
    print_success("another holder: 202")


#: (the accounts of the backup, the holder of the owner's address among them or None): none is an active administrator.
NO_ADMINISTRATOR_RECIPES = {
    "nobody-holds-the-address": {"accounts": (("bob_user", "bob.b51@example.com", 1, 0), ("olga_former_admin", "olga.b51@example.com", 0, 1))},
    "the-only-account-is-a-plain-user-holding-the-address": {"accounts": (HOLDER_ACCOUNT,)},
    "the-only-account-is-a-disabled-administrator-holding-the-address": {"accounts": (("owen_off_admin", cases.OWNER_EMAIL_STORED, 0, 1),)},
    "a-plain-holder-and-a-disabled-administrator": {"accounts": (HOLDER_ACCOUNT, ("olga_former_admin", "olga.b51@example.com", 0, 1))},
}
#: The username that holds the owner's address in each recipe; ``None`` where nobody does.
NO_ADMINISTRATOR_HOLDERS = {
    "nobody-holds-the-address": None,
    "the-only-account-is-a-plain-user-holding-the-address": "owen_user",
    "the-only-account-is-a-disabled-administrator-holding-the-address": "owen_off_admin",
    "a-plain-holder-and-a-disabled-administrator": "owen_user",
}


@pytest.fixture(scope="module")
def no_administrator_archives(databases, tmp_path_factory) -> dict[str, OwnerArchive]:
    return built_archives(tmp_path_factory.mktemp("b51g-no-administrator-archives"), databases, NO_ADMINISTRATOR_RECIPES)


#: (the recipe, who the confirmation names): "the-holder" only where somebody holds the owner's address.
NO_ADMINISTRATOR_CASES = [pytest.param(recipe, naming, id=f"{recipe}--{naming}") for recipe in NO_ADMINISTRATOR_RECIPES for naming in ("no-body", "the-holder", "an-account-of-the-backup", "an-id-that-is-no-account") if not (naming == "the-holder" and NO_ADMINISTRATOR_HOLDERS[recipe] is None)]


@pytest.mark.asyncio
@pytest.mark.parametrize(("recipe", "naming"), NO_ADMINISTRATOR_CASES)
async def test_a_managed_confirmation_of_a_backup_with_no_active_administrator_is_409_not_restorable(instance, no_administrator_archives, monkeypatch, recipe, naming):
    """(o) B5-1g: a backup with no ACTIVE administrator cannot be restored on a ``managed`` instance: the check ends with
    the blocker ``no_administrator`` (not restorable, no administrators), and the confirmation is 409
    ``restore_not_restorable`` — whatever owner it names, none, the holder of the owner's address, another account of the
    backup or an id that is no account, and even when the only account of the backup holds the owner's address
    without being an active administrator. The refusal names the blocker's code; nothing written, the copy as it was.
    Pins: the blocker is checked before the owner."""
    print_section(f"(o) B5-1g no active administrator: {recipe} / {naming}")
    owner_setting(monkeypatch, "managed", cases.OWNER_EMAIL)
    archive = no_administrator_archives[recipe]
    state = await api.ended(archive.archive.path.read_bytes())
    report = state["report"]
    assert (state["status"], report["restorable"], report["blockers"], report["administrators"]) == ("done", False, ["no_administrator"], []), f"precondition: the check blocks the archive: {state['status']}, {report['restorable']}, {report['blockers']}, {report['administrators']}"
    stage_id = state["stage_id"]
    holder = NO_ADMINISTRATOR_HOLDERS[recipe]
    ids = {"no-body": None, "the-holder": archive.accounts.get(holder, {}).get("user_id"), "an-account-of-the-backup": next(iter(archive.accounts.values()))["user_id"], "an-id-that-is-no-account": 999_999}
    copy_before = api.tree(stage_dir(instance.root, stage_id))
    owner_id = ids[naming]
    response = await (confirm(stage_id) if naming == "no-body" else confirm_with(stage_id, {"owner_user_id": owner_id}))
    assert api.code(response) == (409, "restore_not_restorable"), f"409 restore_not_restorable: {api.shown(response)}"
    assert "no_administrator" in response.json()["detail"]["message"], f"the refusal names the blocker: {response.json()['detail']}"
    assert not os.path.lexists(state_path(instance.root)), "nothing confirmed: no state written"
    assert api.tree(stage_dir(instance.root, stage_id)) == copy_before, "the copy as it was"
    print_success(f"{recipe} / {naming}: 409 restore_not_restorable")

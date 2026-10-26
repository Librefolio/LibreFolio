"""
Restoring a checked backup at the next start (workstream B, lot B3, contract §1–§4, §7, §10 and §11):
``instance_backup/apply.py`` and ``instance_backup/restart.py`` (new), the names ``paths.py`` gains, the three startup
steps of ``app_lifespan.py``. Selector: ``services backup-apply``.

Written RED, before B3. ``apply.py``, ``restart.py`` and the new names of ``paths.py`` are looked up by the test that
needs them (``apply_module``, ``restart_module``, ``new_path_name``), never imported at the top: the file collects
without them, and each test fails on its own, saying what is missing ("[new] …"). The tests of (m) were written red the
same way, before P7 (§11), and those of (n) before B5c (``instance_backup/outcome.py``, ``outcome_module``); the B-31
case of (f), a copy that cannot be removed, before B-31; those of (o) before B-32, each failing on today's answer first
(``None``, ``restore_not_pending``, a confirmation that goes on), ``apply.RestoreStateUnreadableError`` looked up last.

(a) §1 The layout: ``.restore/restore.json`` (the state), ``.restore/apply.lock``, ``.restore/previous/`` (the data a
    restore replaced), ``.restore/failed/`` (the restored data a rollback set aside); ``SWAPPED_FOLDERS``, the database's
    folder then the archived folders, in this order: a restore swaps exactly what an archive carries;
    ``stage_data_dir``, ``ValueError`` for anything that is not a stage id.
(b) §2 The errors, each a ``RestoreStateError`` with its stable ``code`` (§10: ``RestoreInUseError``,
    ``restore_in_use``); ``ACTIVE``; frozen models whose defaults say that nothing has happened yet.
(c) §2 Boots. ``current_boot``: the server's root process, read through ``restart.server_pid`` (this process when
    multiprocessing did not start it, or when its parent no longer runs), with its creation time rounded to the
    millisecond, 0.0 when it cannot be read; §10: read once per process, so a creation time psutil says differently
    later (a clock step) does not change it. ``boot_alive`` reads live: that pid runs, created at that time (a reused pid
    is another process).
(d) §2 ``read_restore`` and ``protected_stage``. An ordinary start (no ``.restore``, or no state): ``None``, and the two
    steps create nothing. ``.restore`` or the state a link (never followed), a file, unreadable (logged as an error):
    ``None``, nothing touched. §10, strict: a journal entry that is not a swapped folder (``../x``, ``secrets``, an
    absolute path) or a stage id that is not 32 lowercase hex digits reads as unreadable, and the steps do nothing. The
    stage of an ACTIVE restore only. B-33 changed what the state file's own cases read as: (r).
(e) §2 ``confirm_restore``. The refusals in the contract's order — the copy missing or unusable, blockers, expired
    (``expires_at <= now``), LibreFolio updated since the check (``apply.alembic_head_revision``), a restore already ACTIVE
    in each of its four phases — each writing nothing. The state written: ``pending``, the report's fields, the data
    directory resolved, 0600, atomically (no ``.part`` left), never through a link. A finished restore's ``previous/``
    and ``failed/`` removed. ``.restore`` a link or a file: ``BackupPathError``.
(f) §2 ``cancel_restore``: a ``pending`` restore only, its state returned; the checked copy kept unless ``drop_copy``;
    anything else ``RestoreNotPendingError``, nothing changed. B-31: with ``drop_copy``, an ``OSError`` while the copy is
    removed (``_remove_leftovers``) comes once the restore is dropped: one warning with the stage and the error, never
    raised, the restore cancelled and its state returned, the info line «Pending restore cancelled» with
    ``copy_dropped`` False; without ``drop_copy``, ``_remove_leftovers`` is never called, ``copy_dropped`` False too.
(g) §2 ``apply_pending_restore``, the step ``pending-restore``. A pending restore swaps the four folders, in every
    combination of a live folder and a restored one: the restored data live (each folder with the mode of the one it
    replaces), the replaced data in ``previous/``, the journal (``swap``) on disk before the first rename, ``applied``
    with its boot; ``secrets/``, ``logs/``, ``scheduler_state.json``, ``backups/`` and the production marker untouched.
    Applied by this boot: nothing; by another that runs: §10, the start stops (``RestoreInUseError``), nothing written,
    moved or undone, an error logged; by one that ended (a pid no process has, a process that ran and ended, a reused
    pid): the undo, ``first_start_failed``, the old data back exactly, the restored data and what the failed start wrote
    in ``failed/``, a folder it made where neither existed left alone. Killed after
    any rename of the swap or of the undo: the next start puts the old data back exactly (``swap_interrupted``, a reason
    already given kept). A rename that fails: ``swap_failed`` during the swap; during the undo ``RestoreApplyError``,
    the state ``rolling_back``, the next start finishing it. Waiting, nothing moved: another data directory, a backup
    running. The copy unusable: ``stage_missing``; a live folder that is a link or a file: ``swap_failed``; both before
    anything moves. Leftover ``previous/`` and ``failed/`` removed before the journal. Committed or rolled back: nothing.
    Two workers of one server (two spawn children of this process): one swap, the other waiting for the apply lock while
    it runs; both answer ``applied`` by the same boot.
    §10, never under a running server: while a server process (a spawn child) holds the serving lock, a pending restore
    waits (``server_running``, an error logged, nothing moved) and a restore a dead start applied is not undone (the
    start stops, ``RestoreInUseError``); once it exited, the next start swaps, or undoes. A swap a killed start left half
    done is undone even then: only the undo makes the data directory whole; an error says that the server must be
    restarted (none when nobody serves). While a step moves folders (the swap and its
    ``swap_failed`` undo, the undo of a dead start, the undo of a killed swap) it holds the serving lock exclusively,
    from its checks to its last rename: at every rename a shared lock asked through another descriptor is refused; it
    is free again once the step returned, or raised. ``hold_serving_lock``: a shared lock on the data directory itself
    (``True``, no file created, one descriptor per data directory and process, held by two processes at once), asked
    first without waiting: granted, nothing logged; refused (a restore moving the folders), a warning that this start
    waits, then a plain shared lock waited for. A
    restore's probe (``_exclusive_serving_lock``) finds it held while a holder lives, and then holds nothing; found free,
    it keeps it exclusively for its block, and only for its block. Without ``fcntl``, on a directory that cannot be
    opened, on a file system that refuses ``flock`` (a warning for these two): ``False``, nothing held, and a probe
    cannot tell.
(h) §2, §3 ``finish_pending_restore``, the step ``restore-commit``. Applied by this boot: ``committed``, every account's
    ``session_version`` = max(R, A + 1, B + 1) — R the restore time in milliseconds, A and B the largest version of the
    restored database and of the one before it (0 when that one cannot be read or holds no account) — recorded in the
    state; ``previous/``, ``failed/``, this restore's copy and its check state removed, nothing else of ``.restore``; at a
    later start, nothing more. Rolled back: its leftovers removed. Applied by another boot: §10, the start stops
    (``RestoreInUseError``), nothing done. Anything else: nothing.
    The one-time links of the restored database (night decision, pending the developer): every ``account_tokens`` row
    neither consumed nor revoked, of any purpose, expired or not, gets ``revoked_at`` = the restore time, stored as
    SQLAlchemy stores a datetime in SQLite (UTC, no offset, ``YYYY-MM-DD HH:MM:SS.ffffff``), in the same transaction as
    the session versions; consumed and revoked rows, every other row and the database before untouched; A's
    ``token_service`` reads each of them back as revoked, at the restore time, and none of them opens anything any more.
    ``_close_the_way_in(data_dir, now)`` answers the session value and the count; the count is logged, the state gains
    no field.
(i) §3 Sessions on the restored database, in-process as ``test_session_version.py`` tests them (decision of 00:17): the
    clock ahead of both databases, behind the one before (an account at R + 5000) or behind the restored one (R + 9):
    no cookie at any version either database held signs in, a login does. A restore on top of a committed restore, the
    clock forward or back: every account strictly above both histories, the cookies of both refused. Then a password
    change (``end_sessions``) raises that account alone by one.
(j) §7, §10 The startup steps: ``pending-restore`` between ``tool-catalog`` and ``data-directories``; ``serving-lock``
    after ``data-directories`` and before ``risk-scenarios`` and ``database`` (held before any data is read);
    ``restore-commit`` between ``global-settings`` and ``provider-prewarm``, and after ``admin-bootstrap`` (decision N57:
    a bootstrap that fails on the restored data still rolls the restore back at the next start); each reaches
    ``app_lifespan.<its function>`` when its awaitable runs, once, without arguments, off the event loop. Lot B4b, N66:
    ``backup-leftovers`` after ``restore-commit``, the leftovers of killed runs removed once the restore is settled, by a
    step that never raises (``test_backup_leftovers.py`` tests the step itself).
(k) §4 ``restart.py``: ``server_pid`` (this process without a multiprocessing parent, the parent in a spawn child; §10:
    this process when its parent no longer runs, the pid it had may be another process's);
    ``request_restart`` sends ``SIGTERM`` through ``send_signal`` (``os.kill`` by default, read when it runs) to the pid
    given or the server's, returns it and logs a warning. No real signal: ``os.kill`` itself is replaced too.
(l) B2 then B3 with real archives at the head and at ``OLDER``: checked, confirmed, applied, committed; the live database
    at the head with the rows the report's ``after`` says, the archive's files live, the copy gone.
(m) §11, P7 (the developer's decision of 2026-10-16): no restore on a blocked instance. ``WaitReason`` gains
    ``instance_blocked``. ``LIBREFOLIO_BLOCKED`` blocking (``true``, ``1``, ``yes``, ``ON``): a pending restore is not
    applied — ``pending``, ``waiting = instance_blocked`` recorded in the state file, the rest of the state as
    confirmed, nothing moved, written or removed but the state (an earlier restore's ``previous/`` and ``failed/``
    included), one warning logged («The hosting provider blocked the instance: the restore waits until it is
    unblocked») and no error, the apply lock and the serving lock free once the step returned; the variable removed,
    the next start applies it and clears ``waiting``. A value that cannot be read (``maybe``) counts as blocked: the
    same, an error logged, and the step does not raise. ``false``, ``0``, unset: applied as before. The order:
    ``other_data_directory`` first (a copy of the data directory never applies the restore, blocked or not), then
    ``instance_blocked``, before ``server_running`` and ``backup_running`` (each seen to hold the restore back on its
    own once the block is lifted). Unchanged while blocked: the undo of a restore a dead start applied
    (``first_start_failed``), of a swap a killed start left ``applying`` and of an undo it left ``rolling_back``
    (``swap_interrupted``), the data of before back exactly; the commit of a restore this boot applied.
(n) Lot B5c, the ticket of a restart's outcome (``instance_backup/outcome.py``, ``.restore/outcome-ticket.json``;
    ``test_backup_outcome.py`` tests the module itself). ``confirm_restore`` drops a ticket left behind (no restore, or
    one committed or rolled back): a new confirmation is another restore. ``cancel_restore`` drops it, whether it keeps
    the checked copy or not. A refused confirmation writes nothing, as (e) says (another copy while one waits, a copy that
    is not there): the waiting restore keeps its ticket; so does a refused cancel (applied, committed, rolled back), whose
    outcome the ticket still reads. ``.restore`` is never swapped: the swap, the commit and a rollback (a rename of the
    swap failing; the first start dying, undone by the next) leave the file byte for byte. Decision N53, one restore, one
    ticket, not one read: the ticket then reads the final outcome again, the same, its file kept, until it expires; at
    ``expires_at`` it opens nothing, and its file goes. ``prepare_restart``, the restart's first step, returns the
    restore waiting and a new ticket for its stage, issued while the restore's lock is held; without a pending restore
    ``RestoreNotPendingError``, nothing written (without a restore not even the lock), an earlier ticket kept.
(o) B-32 §3, a state the file system cannot read (placed after the B-31 cases of (f)): the state file there and regular,
    its opening failing (EACCES, EIO; its mode 000), or a ``.restore/`` the server cannot search. A restore may still
    wait, so the strict callers say so: ``read_restore`` raises ``RestoreStateUnreadableError``
    (``restore_state_unreadable``, its ``reason`` the system's words, the contract's message, never a path), an error
    logged, nothing created or changed; ``cancel_restore`` raises it too, never ``RestoreNotPendingError`` (the state,
    the copy and the ticket byte for byte); ``prepare_restart`` (no ticket) and ``confirm_restore`` of another copy (the
    state never written over, nothing removed) as well. Lenient, as before: ``apply_pending_restore``,
    ``finish_pending_restore`` and ``protected_stage`` give ``None``, nothing moved, an error logged. A state that is a
    folder reads as none, logged; a link and a content no restore can hold stay as (d) has them.
(p) B-55 and B-53, the report of the checked copy (``staging.read_report``, read since lot B-53 through
    ``paths.read_regular_file``). A confirmation takes only a report that is not there or cannot be one —
    ``read_report``'s ``FileNotFoundError``: nothing there, a folder, a link, a special file, no permission, a content
    that is no report — for «no checked copy» (``RestoreStageMissingError``, the route's 404, after which the tab forgets
    the check). A transient error reading it (``os.open`` failing ``EIO`` for the report alone) reaches the caller as it
    is, the route's 500 ``restore_confirm_failed``, which the tab retries; nothing confirmed, written or removed. A
    report that is a folder is still no checked copy, nothing written, and twenty confirmations of it leave no
    descriptor open on it; a report of mode 000 is still no checked copy (skipped as root).
(q) Lot L3-2, how a restore was confirmed (contract L3 §5: the panel sees ``confirmed_via``, never a username).
    ``apply.ConfirmedVia`` is ``Literal["admin", "cli", "panel"]``; ``RestoreState.confirmed_via`` is written in
    ``restore.json``; ``confirm_restore(..., confirmed_via=)`` and ``restore_jobs.confirm_check(..., confirmed_via=)``
    record it, ``admin`` without one — whatever ``confirmed_by`` says, a username ``cli`` or ``panel`` included. A state
    written before L3-2 (no key) reads ``cli`` when ``confirmed_by`` is ``cli``, ``admin`` otherwise. Written RED: the
    names are looked up by the test that needs them (``l3_2_name``, ``l3_2_parameter``), each failing with a "[new]
    L3-2 …" message; (e)'s state and (h)'s ``STATE_FIELDS`` now hold ``confirmed_via`` too, red on the same field.
(r) B-33 (interface ``B-b33-interface.md`` §1-§3, written RED before it; placed after (o)). §1: ``None`` only without a
    state file (no ``.restore``, no ``restore.json``; a ``.restore`` that is a link or a file is ignored as before);
    any state file that cannot be read is ``RestoreStateUnreadableError`` with ``reason`` ``io`` (the file system
    refused it: (o)'s cases, whose ``reason`` was the system's words and is now ``io``, the message unchanged),
    ``not_a_file`` (a folder, a link, a FIFO — never waited on) or ``invalid`` (not JSON, fields missing, ``format``
    2, and (d)'s §10 strict cases), logged once; ``read_restore`` and ``confirm_restore`` raise it — (d)'s state link and
    invalid state, (e)'s state link (replaced before B-33, refused now) and (o)'s folder (``None`` before B-33) were
    updated so —, the startup steps keep ``None`` with an error logged. ``restore_state_problem(data_dir=None)``: that
    error returned, or ``None``, never raised. §2: ``protected_stage`` is ``EVERY_STAGE`` (``"*"``) for every reason
    (it left (o)'s lenient callers). §3: ``recover_unreadable_restore(data_dir=None)`` → ``RecoveredRestore``
    (frozen: ``moved_back``, ``set_aside``, ``state_kept_as``): each swapped folder in ``previous/`` back in place, its
    live one to ``failed/``; the state renamed ``restore.json.unreadable-<YYYYMMDDTHHMMSSZ>``; no previous/, nothing
    moved; a readable state or none, ``RestoreNothingToRecoverError`` (``restore_nothing_to_recover``); a server
    serving the directory, ``RestoreInUseError``; nothing changed by a refusal or by a second call. Names looked up by
    the test that needs them (``b33_name``, "[new] B-33 …"). Data directories of (r) are bare (no database) but for the
    confirmation; a call that may meet a FIFO runs in a thread given a deadline (``in_time``), its reader let go after.
(s) Lot B5-1 (interface ``B-b51-interface.md`` §0, §3; written RED before it): the owner's choice at the confirmation.
    ``confirm_restore(..., owner_user_id=None)``; ``RestoreState`` gains ``owner_user_id`` and ``owner_outcome``,
    both ``None`` by default — a state written before B5-1 reads them ``None``, and (e)'s state and (h)'s
    ``STATE_FIELDS`` hold them too; it has no ``owner_reset_path`` (R13 security review: the owner's link is never kept
    in the state; a file that still has the key reads fine and the key is dropped). In the ``managed`` profile (``LIBREFOLIO_PROFILE``), a confirmation via
    ``admin`` must name the owner's account among the report's ``owner_candidates``: none, ``owner_choice_required``;
    ``LIBREFOLIO_ADMIN_EMAIL`` unset,
    ``owner_email_not_set``; an id that is no candidate, a candidate that is neither an active administrator nor the
    holder of the owner's email (A–Z case aside, read at the confirmation), or another account while a candidate holds
    the owner's email (the choice is then forced), ``owner_choice_invalid`` — each a ``RestoreStateError`` with that
    ``code``, nothing written. The forced account, even not an administrator, and an active administrator when nobody
    holds the owner's email, are confirmed, ``owner_user_id`` recorded in the state returned and in ``restore.json``.
    ``selfhosted`` asks nothing (``owner_user_id`` ``None``); ``panel`` and ``cli`` never need one, in ``managed`` too.
    The candidates are written into the copy's ``report.json`` as B5-1's check writes them (raw JSON, so the file reads
    before B5-1 too), with the addendum's ``owner_email_checked`` (the owner's email of the case) and ``owner_conflicts``
    (``[]``) unless a case says otherwise. Security addendum §7.2: in ``managed`` via ``admin``, a report checked with
    another address (``email_fold``), with none, or written before the addendum is ``restore_stage_outdated`` before
    the choice is looked at; one whose ``owner_conflicts`` is not empty is ``owner_conflict``
    (``RestoreOwnerConflictError``) whatever the choice; nothing written. Panel, CLI and ``selfhosted`` unaffected.
(t) Lot B5-1, security addendum §7.5 (written RED before it): ``finish_pending_restore`` of a restore confirmed via
    ``admin`` naming ``owner_user_id`` closes that account in the commit's transaction
    (``_close_the_way_in(data_dir, now, owner_user_id=None)``): a real bcrypt hash the backup's password does not open;
    with the owner's address set and held by no other account, that address, ``is_superuser`` and ``is_active`` 1, A's
    ``is_instance_owner`` 1 only where the column exists. Another holder: only the password, a warning, committed; the
    address unset: only the password; an id the database does not hold: nothing, a warning, committed; a restore
    without an owner: no password touched. One line with the stage, the account and ``assigned``; no address, username,
    hash or password in the log. The backup's accounts get real bcrypt hashes of a known password in the copy, and the
    state's ``owner_user_id`` is rewritten after the confirmation where a case needs an account it would refuse.

(v) Lot B5-1j (analysis ``B-5-1j-analisi-titolare-nel-restore-cli.md`` §2, §4, §6, §8; written RED before it): the owner's account
    of a restore confirmed from the COMMAND LINE or by the HOSTING PANEL on a ``managed`` instance whose
    ``LIBREFOLIO_ADMIN_EMAIL`` is set. ``apply.pick_owner(candidates, owner_email) -> OwnerPick(user_id, username, how)``
    (frozen): the account holding the address (``user_service.same_email``, A–Z only; whatever its role or state) is
    ``holds_address``; else the ONE candidate that is marked as the owner by the backup (``is_instance_owner``), an active
    administrator, is ``marked``; else ``none`` — nobody marked, two or more marked, a marked account that is not an active
    administrator —, never «the first by id». ``confirm_restore`` stores the pick in ``owner_user_id`` and, when there is none,
    records ``owner_outcome == "none"`` (the startup step does not run for it) and logs a warning with no username and no
    address; a report not checked with the current address is ``restore_stage_outdated``, one with conflicts is
    ``owner_conflict`` (the message says to make a new backup), nothing written; ``owner_user_id=`` is still
    ``owner_choice_not_applicable``; without the address, or self-hosted, nothing changes. The commit closes the picked
    account as it does for the app, whatever the channel. The administrators' path is unchanged.

How. Real databases and archives come from ``test_backup_staging.py`` (its module fixtures, imported: two databases made
once by ``alembic upgrade`` in a process of their own, the archives at the head and at ``OLDER``). The head archive is
checked once for the module (``checked``); each test copies that checked copy into a data directory of its own and
removes the folders its layout does not restore. Every rename of the swap and of the undo goes through ``apply._move``
(contract): a ``Mover`` records each one and makes it, or plays what goes wrong at the n-th — the process killed just
before or just after it (``_Crash``, a ``BaseException`` the product must not catch: the state on disk stays as the kill
left it) or the rename failing (``OSError``, nothing moved). A data directory is compared whole outside ``.restore``:
every path with its mode, a file with its size and SHA-256 (``fingerprint`` of the staging tests); "back exactly" is that
comparison, equal. Boots: a pid no process can have, a process that ran and ended, this process's pid with another
creation time, and this process itself. Logs are read with ``structlog.testing.capture_logs`` behind a barrier (a warning
through a logger of ``apply``'s name must reach the capture). Cookies are signed with ``test_session_version.py``'s known
JWT secret (its autouse fixture, imported); ``now`` is always given, so no value depends on the real clock. One-time
links are written and read in-process through A's ``token_service``, on the database file, as A writes and reads them;
``apply._close_the_way_in`` (contract) is also called on its own, to show that the database before is only read and
that the links and the sessions change together or not at all (a trigger refuses one of the two updates). A server
serving a data directory is a spawn child holding its serving lock (``serving``), let go and waited for at the end of its
block; what ``hold_serving_lock`` takes in this process is released by the fixture ``serving_here``, so that no lock
stays held in the pytest process. Whether a process reaching ``serving-lock`` could take the lock is asked without a
child (``serving_lock_free``, at every rename through ``Mover.on_each``): a shared ``flock`` through a descriptor of
the test's own, which conflicts with a lock this process holds through another, since such a lock belongs to an open
file description. ``apply._boot_of`` keeps the boots it read for the life of a process: its cache is
emptied before and after every test (``fresh_boots``). The block is ``LIBREFOLIO_BLOCKED`` in this process's environment,
which ``config.platform.instance_blocked()`` reads at each call: the one a developer's shell may carry is removed before
every test (``no_inherited_block``), and each test of (m) sets its own with ``monkeypatch`` — after any spawn child it
needs has started, so that the child never sees it. A state (o) cannot read: ``os.open`` replaced for the test, failing
for that one file and opening every other path as it is; or a mode taken away (``Modes``: put back before the tree is
compared, and in any case when the test ends), those cases skipped as root, which reads everything. (p)'s transient
error is the global ``os.open`` failing for the report alone (``opening_fails`` of ``test_backup_archive.py``), its
descriptors found in ``/dev/fd`` by what they are open on (``descriptors_on``, of the same module).

Pure: every data directory under ``tmp_path``. This process, and the processes it starts, are configured with a
production data directory of the test that must stay absent (``configured_data_dir`` of the staging tests, imported,
autouse): a write anywhere else fails the test, and the lane's data directory is never reached. No lane database, no
server, no network, no signal. Every wait is an ``Event``, a ``Queue`` read or a ``join`` with a deadline. Modes, links
and ``flock`` are POSIX-only.
"""

from __future__ import annotations

import dataclasses
import fcntl
import hashlib
import importlib
import inspect
import json
import multiprocessing
import os
import queue
import re
import shutil
import signal
import sqlite3
import stat
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import closing, contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from errno import EACCES, EIO, ENOLCK, EWOULDBLOCK, EXDEV
from pathlib import Path
from types import SimpleNamespace
from typing import Any, get_args

import psutil
import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from structlog.testing import capture_logs

from backend.app.config import PRODUCTION_DATA_MARKER
from backend.app.config.platform import instance_blocked
from backend.app.db.models import AccountTokenPurpose
from backend.app.logging_config import get_logger
from backend.app.services.accounts import auth_service, token_service
from backend.app.services.platform.instance_backup import jobs, paths, restore_jobs
from backend.app.services.platform.instance_backup.paths import (
    ARCHIVED_FOLDERS,
    CHECKS_FOLDER,
    DATABASE_ENTRY,
    STAGE_DATA_FOLDER,
    STAGE_FOLDER,
    STAGE_REPORT_FILE,
    UPLOAD_FOLDER,
    BackupPathError,
    check_state_path,
    checks_dir,
    ensure_private_dir,
    lock_path,
    restore_dir,
    stage_dir,
    stages_dir,
    upload_path,
    uploads_dir,
)
from backend.app.services.platform.instance_backup.restore_jobs import RestoreCheck
from backend.app.services.platform.instance_backup.staging import StagingReport, stage_archive
from backend.app.utils.runtime.version import get_git_version
from backend.test_scripts.test_services import test_backup_staging as cases
from backend.test_scripts.test_services import test_session_version as sessions
from backend.test_scripts.test_services.test_backup_archive import close_all, descriptors_on, needs_dev_fd, opening_fails
from backend.test_scripts.test_utils import print_section, print_success

# The module fixtures of test_backup_staging.py (lot B2a), re-exported: the real databases and archives restored here.
databases = cases.databases
head_archive = cases.head_archive
older_archive = cases.older_archive
# Autouse, both. The production data directory of this process and of its children is a folder of the test that must
# stay absent, LF_APP_VERSION is set; the JWT secret is test_session_version.py's known one, in this process.
configured_data_dir = cases.configured_data_dir
secret = sessions.secret

POSIX = os.name != "nt"
pytestmark = pytest.mark.skipif(not POSIX, reason="modes, links and flock are POSIX only")

APPLY = "backend.app.services.platform.instance_backup.apply"
RESTART = "backend.app.services.platform.instance_backup.restart"

#: The folders a restore swaps, in their order (§1), spelled out here: a change in paths.py shows in (a).
SWAPPED = ("sqlite", "custom-uploads", "broker_reports", "scenario_catalog")
STATE_FILE_NAME = "restore.json"
APPLY_LOCK_NAME = "apply.lock"
PREVIOUS_NAME = "previous"
FAILED_NAME = "failed"
ACTIVE_PHASES = ("pending", "applying", "applied", "rolling_back")
TERMINAL_PHASES = ("committed", "rolled_back")
ERROR_CODES = {
    "RestoreStageMissingError": "restore_stage_not_found",
    "RestoreNotRestorableError": "restore_not_restorable",
    "RestoreStageExpiredError": "restore_stage_expired",
    "RestoreStageOutdatedError": "restore_stage_outdated",
    "RestoreAlreadyPendingError": "restore_already_pending",
    "RestoreNotPendingError": "restore_not_pending",
    "RestoreApplyError": "restore_apply_failed",
    "RestoreInUseError": "restore_in_use",
}
#: A head no LibreFolio has yet: what alembic_head_revision answers once LibreFolio was updated after the check.
NEWER_HEAD = "999_a_head_after_the_check"

#: The mode staging gives every folder of a copy: what a restored folder keeps when it replaces none.
STAGED_MODE = 0o700
#: The modes of the live instance's folders: each its own, none the copy's 0700, so that a mode that moved shows.
LIVE_MODES = {"sqlite": 0o755, "custom-uploads": 0o750, "broker_reports": 0o751, "scenario_catalog": 0o710}
#: The live instance's own files in the folders a restore swaps, by folder: none of them is in the backup.
LIVE_FILES = {
    "custom-uploads": {"live-logo.png": b"the live instance's own logo\n", "avatars/live-user.webp": b"RIFF\x24\x00\x00\x00WEBPVP8 live" + bytes(48)},
    "broker_reports": {"uploaded/2026-11.csv": b"date,amount\n2026-11-01,30.00\n"},
    "scenario_catalog": {"live-scenarios.json": b'{"scenarios": ["live"]}\n'},
}
#: What a restore never touches (§1): the instance key, the logs, the scheduler's state, the backups, the marker.
UNTOUCHED = {
    "secrets/instance.key": b"instance-key-of-the-live-instance-7f3a91\n",
    "logs/librefolio.log": b'{"event": "a log line of the live instance"}\n',
    "scheduler_state.json": b'{"jobs": {"fx-sync": "2026-10-15T09:00:00Z"}}\n',
    "backups/librefolio-backup-20261014-090000.zip": b"PK an older backup of the live instance",
    "backups/.jobs/.lock": b"",
    PRODUCTION_DATA_MARKER: b"LibreFolio production data root\n",
}
#: The live instance's accounts and their session versions; the backup's are test_backup_staging.ACCOUNTS (olga's
#: account disabled), with these versions.
LIVE_ACCOUNTS = (("live_admin", 1, 1), ("live_user", 1, 0))
LIVE_VERSIONS = {"live_admin": 7, "live_user": 3}
BACKUP_VERSIONS = {"zoe_admin": 2, "bob_user": 11, "olga_former_admin": 5, "ada_admin": 0}
CONFIRMED_BY = "ada_admin"
#: A second checked copy beside the instance's own.
OTHER_STAGE = "fedcba9876543210fedcba9876543210"
#: What else ``.restore`` holds and no restore may remove: another archive's failed check, an upload in progress.
UNRELATED_CHECK = "00112233445566778899aabbccddeeff"
UNRELATED_UPLOAD = "ffeeddccbbaa99887766554433221100"
#: The upload the instance's own copy was checked from (removed when its check ended).
CHECK_UPLOAD = "0f1e2d3c4b5a69788796a5b4c3d2e1f0"
#: A pid no process can have: above Linux's largest pid_max (2**22) and macOS's (99 999).
NO_SUCH_PID = 2**22 + 7
#: Seconds. Every wait of this module ends by then (a spawn child imports the application first); none decides alone.
DEADLINE_S = 120
LOG_CANARY = "b3 apply test: canary through a logger of apply's name"
#: What an operator reads (§10): a server found serving a data directory a restore left half swapped, and a start
#: waiting for a restore to finish moving the folders.
HALF_SWAPPED_UNDER_A_SERVER = "A server serves a data directory that a restore left half swapped: it is put back all the same, and that server must be restarted"
WAITING_FOR_THE_MOVES = "A restore is moving the folders of the data directory: this start waits until they have moved"
#: (§11, P7) The hosting provider's block, which ``config.platform.instance_blocked()`` reads from this process's
#: environment at each call; and what an operator reads when a pending restore waits for the block to end.
BLOCKED_VARIABLE = "LIBREFOLIO_BLOCKED"
INSTANCE_BLOCKED_WAITS = "The hosting provider blocked the instance: the restore waits until it is unblocked"
#: (B-31) What an operator reads when the copy of a cancelled restore could not be removed: the restore is cancelled all
#: the same, and its copy goes with its check, when that expires.
COPY_NOT_REMOVED = "The copy of a cancelled restore could not be removed: it goes when its check expires"
#: The line every cancel logs, at INFO: its ``copy_dropped`` is ``True`` only when the copy was removed (B-31).
RESTORE_CANCELLED = "Pending restore cancelled"

#: Each folder's (live, restored), every combination for each archived folder across the four layouts; the database's
#: folder is restored always (a copy without a database is not usable), replacing a live one or none.
FULL = dict.fromkeys(SWAPPED, (True, True))
MIXED = {"sqlite": (True, True), "custom-uploads": (True, False), "broker_reports": (False, True), "scenario_catalog": (False, False)}
NO_LIVE_DATABASE = {"sqlite": (False, True), "custom-uploads": (False, True), "broker_reports": (False, False), "scenario_catalog": (True, False)}
OTHER_MIX = {"sqlite": (True, True), "custom-uploads": (False, False), "broker_reports": (True, False), "scenario_catalog": (False, True)}
LAYOUTS = [
    pytest.param(FULL, id="every-folder-live-and-restored"),
    pytest.param(MIXED, id="uploads-live-only-reports-restored-only-scenarios-neither"),
    pytest.param(NO_LIVE_DATABASE, id="no-live-database-uploads-restored-only-reports-neither-scenarios-live-only"),
    pytest.param(OTHER_MIX, id="uploads-neither-reports-live-only-scenarios-restored-only"),
]


# =============================================================================
# The product, looked up when a test needs it
# =============================================================================


def _new_module(name: str) -> Any:
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as exc:
        if exc.name != name:
            raise
        pytest.fail(f"[new] {name} does not exist yet: lot B3 brings it (contract §2, §4)")


def apply_module() -> Any:
    """``instance_backup.apply``, imported by the test that needs it: its absence is that test's red, not a collection
    error of the whole file."""
    return _new_module(APPLY)


def restart_module() -> Any:
    """``instance_backup.restart``, imported the same way."""
    return _new_module(RESTART)


def new_path_name(name: str) -> Any:
    """A name ``paths.py`` gains with lot B3, looked up by the test that needs it."""
    value = getattr(paths, name, None)
    assert value is not None, f"[new] paths.{name} does not exist yet: lot B3 adds it (contract §1)"
    return value


def _clear_boots() -> None:
    """Empty ``apply._boot_of``'s cache, when ``apply`` is loaded: it keeps a boot for the life of the process."""
    boot_of = getattr(sys.modules.get(APPLY), "_boot_of", None)
    if boot_of is not None and hasattr(boot_of, "cache_clear"):
        boot_of.cache_clear()


@pytest.fixture(autouse=True)
def fresh_boots() -> Iterator[None]:
    """§10: ``current_boot`` reads a root process's creation time once per process. Emptied before and after every test,
    so that no test sees a boot another one read (a replaced ``create_time``, a stand-in parent)."""
    _clear_boots()
    yield
    _clear_boots()


@pytest.fixture(autouse=True)
def no_inherited_block(monkeypatch: pytest.MonkeyPatch) -> None:
    """§11: a pending restore is not applied on a blocked instance, and the block is read from this process's
    environment at each call. The ``LIBREFOLIO_BLOCKED`` a developer's shell may carry is removed for every test, and for
    the spawn children it starts: a test sees only the block it sets itself."""
    monkeypatch.delenv(BLOCKED_VARIABLE, raising=False)


@pytest.fixture
def serving_here() -> Iterator[Any]:
    """``apply``, and what ``hold_serving_lock`` takes in this process during the test released at its end: each key it
    added to ``apply._SERVING`` popped, its descriptor closed. Nothing stays held in the pytest process."""
    apply = apply_module()
    before = set(apply._SERVING)
    try:
        yield apply
    finally:
        for key in [key for key in apply._SERVING if key not in before]:
            os.close(apply._SERVING.pop(key))


# =============================================================================
# Paths, trees, databases, boots
# =============================================================================


def state_file(root: Path) -> Path:
    return restore_dir(root) / STATE_FILE_NAME


def previous_of(root: Path) -> Path:
    return restore_dir(root) / PREVIOUS_NAME


def failed_of(root: Path) -> Path:
    return restore_dir(root) / FAILED_NAME


def apply_lock_of(root: Path) -> Path:
    return restore_dir(root) / APPLY_LOCK_NAME


def lexists(path: Path) -> bool:
    """Whether anything stands at ``path``: a dangling link too."""
    return os.path.lexists(path)


def tree(path: Path) -> dict[str, tuple] | None:
    """What a folder holds, every path below it with its mode, a file with its size and SHA-256; ``None`` where nothing
    stands. The folder's own mode is not part of it: ``cases.mode`` reads that."""
    return cases.fingerprint(path) if lexists(path) else None


def outside(fingerprint: dict[str, tuple]) -> dict[str, tuple]:
    """A data directory's fingerprint without the folders a restore swaps: what a restore never touches."""
    return {name: value for name, value in fingerprint.items() if Path(name).parts[0] not in SWAPPED}


def restore_items(root: Path) -> dict[str, tuple]:
    """Everything below ``.restore``, as ``fingerprint`` sees a folder (``{}`` when it is not a plain folder)."""
    return cases.fingerprint(restore_dir(root)) if paths.is_plain_dir(restore_dir(root)) else {}


def restore_items_but_the_state(root: Path) -> dict[str, tuple]:
    """Everything below ``.restore`` but the state file: the checked copy, the checks, the uploads, the apply lock, and
    ``previous/`` or ``failed/`` where they stand. What a restore that only records why it waits leaves as it was."""
    return {name: value for name, value in restore_items(root).items() if name != STATE_FILE_NAME}


def restore_kind(root: Path) -> str | None:
    """What stands at ``.restore``: a folder, a link, a file, or nothing."""
    folder = restore_dir(root)
    if folder.is_symlink():
        return "link"
    if paths.is_plain_dir(folder):
        return "folder"
    return "file" if lexists(folder) else None


def set_versions(database: Path, versions: dict[str, int]) -> None:
    """Give accounts of ``database`` these session versions, by user name."""
    with closing(sqlite3.connect(database)) as conn, conn:
        for username, version in versions.items():
            updated = conn.execute("UPDATE users SET session_version = ? WHERE username = ?", (version, username)).rowcount
            assert updated == 1, f"precondition: {username} is an account of {database}"


def versions_of(database: Path) -> dict[str, int]:
    """Every account of ``database`` with its session version, by user name."""
    return dict(cases.rows_of(database, "SELECT username, session_version FROM users"))


def table_rows(database: Path) -> dict[str, int]:
    """The rows of every table of ``database``, as the report and the manifest count them."""
    names = [row[0] for row in cases.rows_of(database, "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")]
    return {name: cases.rows_of(database, f'SELECT count(*) FROM "{name}"')[0][0] for name in names}


def millis(moment: datetime) -> int:
    """A moment as §3 counts the restore time: ``int(now.timestamp() * 1000)``."""
    return int(moment.timestamp() * 1000)


def this_boot(apply: Any) -> Any:
    """This process, as ``current_boot`` reads a process: alive."""
    return apply.Boot(pid=os.getpid(), started=round(psutil.Process().create_time(), 3))


def never_ran(apply: Any, n: int = 0) -> Any:
    """A boot no process can be: its pid is above every pid_max. ``n`` makes another one."""
    return apply.Boot(pid=NO_SUCH_PID + n, started=1_792_000_000.125 + n)


def ended(apply: Any) -> Any:
    """A boot that ran and ended: a process started here, its creation time read while it lived, then waited for."""
    child = subprocess.Popen([sys.executable, "-c", "import sys; sys.stdin.read()"], stdin=subprocess.PIPE)
    try:
        started = round(psutil.Process(child.pid).create_time(), 3)
    finally:
        child.stdin.close()
        child.wait(timeout=DEADLINE_S)
    return apply.Boot(pid=child.pid, started=started)


def reused_pid(apply: Any) -> Any:
    """This process's pid created an hour earlier: another process, which once had the pid."""
    return apply.Boot(pid=os.getpid(), started=round(psutil.Process().create_time() - 3600, 3))


# =============================================================================
# Renames, logs, the lock
# =============================================================================


class _Crash(BaseException):
    """The process killed at this point: no handler of the product runs. A ``BaseException``, neither an ``OSError`` nor
    an ``Exception``: ``apply_pending_restore`` handles ``OSError`` only (contract), so the state on disk stays as the
    kill left it, as after a real one."""


@dataclass
class Mover:
    """``apply._move`` as a test drives it: every rename of the swap and of the undo goes through it (contract). Each
    call is recorded and made with the real ``_move``, unless the plan says otherwise for the n-th call (from 1):
    ``kill_before`` (the process killed just before that rename), ``kill_after`` (just after it), ``fail_at`` (the
    rename fails, ``OSError``: nothing moved). ``on_first`` runs at the first call, ``on_each`` at every call, both
    before that call moves anything (or fails)."""

    real: Callable[[Path, Path], None]
    kill_before: int | None = None
    kill_after: int | None = None
    fail_at: frozenset[int] = frozenset()
    on_first: Callable[[], None] | None = None
    on_each: Callable[[], None] | None = None
    calls: int = 0
    moved: list[tuple[Path, Path]] = field(default_factory=list)

    def __call__(self, source: Path, target: Path) -> None:
        self.calls += 1
        if self.calls == 1 and self.on_first is not None:
            self.on_first()
        if self.on_each is not None:
            self.on_each()
        if self.calls == self.kill_before:
            raise _Crash(f"killed before rename {self.calls}")
        if self.calls in self.fail_at:
            raise OSError(EXDEV, os.strerror(EXDEV), str(source))
        self.real(source, target)
        self.moved.append((Path(source), Path(target)))
        if self.calls == self.kill_after:
            raise _Crash(f"killed after rename {self.calls}")


def killed_after(renames: int) -> dict[str, int]:
    """The plan of a process killed once ``renames`` renames are done: before the first one, for 0."""
    return {"kill_before": 1} if renames == 0 else {"kill_after": renames}


@contextmanager
def moving(apply: Any, **plan: Any) -> Iterator[Mover]:
    """``apply._move`` replaced by a ``Mover`` of ``plan`` for the block."""
    assert hasattr(apply, "_move"), "[new] every rename of the swap and of the undo goes through apply._move(source, target) (contract)"
    mover = Mover(real=apply._move, **plan)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(apply, "_move", mover)
        yield mover


def apply_lock_free(root: Path) -> bool:
    """Whether the apply lock could be taken now: a probe, as ``jobs._lock_held`` makes it, which creates nothing."""
    return not jobs._lock_held(apply_lock_of(root))


def serving_lock_free(root: Path) -> bool:
    """Whether a process reaching its step ``serving-lock`` could take the serving lock of ``root`` now: a shared
    ``flock`` on the directory, not waited for, taken and released at once, nothing created. Through a descriptor of its
    own: a ``flock`` lock belongs to an open file description, so this conflicts with a lock this very process holds
    through another one, as another process's would."""
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        fcntl.flock(fd, fcntl.LOCK_UN)
        return True
    finally:
        os.close(fd)


@contextmanager
def logs(name: str = APPLY) -> Iterator[list[dict[str, Any]]]:
    """What is logged inside the block, behind a barrier: a warning through a logger of ``name`` must reach the capture,
    or "an error was logged" would prove nothing either way."""
    with capture_logs() as events:
        get_logger(name).warning(LOG_CANARY)
        assert any(event.get("event") == LOG_CANARY for event in events), f"barrier: a logger of {name} does not reach capture_logs: {events}"
        yield events


def levels(events: list[dict[str, Any]]) -> set[str]:
    """The levels of what was logged in the block, the canary left out."""
    return {str(event.get("log_level")) for event in events if event.get("event") != LOG_CANARY}


def said(events: list[dict[str, Any]], message: str) -> list[str]:
    """The level of each time ``message`` was logged in the block, in order."""
    return [str(event.get("log_level")) for event in events if event.get("event") == message]


def an_error(events: list[dict[str, Any]]) -> bool:
    return bool(levels(events) & {"error", "critical"})


def a_warning(events: list[dict[str, Any]]) -> bool:
    """A warning, or worse: what an operator must see."""
    return bool(levels(events) & {"warning", "error", "critical"})


def logged(events: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """What was logged in the block, (level, message) in order, the canary left out: what a failure shows."""
    return [(str(event.get("log_level")), str(event.get("event"))) for event in events if event.get("event") != LOG_CANARY]


# =============================================================================
# The instances
# =============================================================================


@dataclass(frozen=True)
class Checked:
    """The head archive checked once for the module, as B2 leaves it: its stage folder (``data/`` and ``report.json``)."""

    stage: Path
    report: StagingReport


@pytest.fixture(scope="module")
def checked(head_archive, tmp_path_factory) -> Checked:
    root = tmp_path_factory.mktemp("checked")
    instance = root / "instance"
    instance.mkdir()
    with pytest.MonkeyPatch.context() as patch:
        cases.configure(patch, root / "configured-data-dir")
        try:
            report = stage_archive(head_archive.path, instance)
        finally:
            get_git_version.cache_clear()
    copy = stage_dir(instance, report.stage_id) / STAGE_DATA_FOLDER
    assert (report.restorable, report.action, report.head_revision) == (True, "same", cases.HEAD), f"precondition: the head archive is restorable as it is: {report.blockers}, {report.action}"
    assert [name for name in SWAPPED if not paths.is_plain_dir(copy / name)] == [], f"precondition: the checked copy holds every folder a restore swaps: {cases.listing(copy)[:12]}"
    return Checked(stage=stage_dir(instance, report.stage_id), report=report)


@dataclass
class Instance:
    """A data directory of a test, a checked copy waiting in it. ``before`` is the whole data directory outside
    ``.restore`` before the restore; ``live`` and ``staged`` each swapped folder, live and in the copy (``None`` where
    there is none). The times are the restore's own: confirmed a minute after the check, applied, committed."""

    root: Path
    stage_id: str
    report: StagingReport
    layout: dict[str, tuple[bool, bool]]
    live: dict[str, dict[str, tuple] | None]
    staged: dict[str, dict[str, tuple] | None]
    before: dict[str, tuple]

    @property
    def copy(self) -> Path:
        return stage_dir(self.root, self.stage_id) / STAGE_DATA_FOLDER

    @property
    def confirm_at(self) -> datetime:
        return self.report.staged_at + timedelta(minutes=1)

    @property
    def applied_at(self) -> datetime:
        return self.report.staged_at + timedelta(minutes=10)

    @property
    def committed_at(self) -> datetime:
        return self.report.staged_at + timedelta(minutes=11)

    @property
    def renames(self) -> int:
        """The renames a swap of this layout makes: a live folder set aside, a restored folder moved in, one each."""
        return sum(int(live) + int(staged) for live, staged in self.layout.values())


def live_instance(root: Path, databases: cases.Databases, layout: dict[str, tuple[bool, bool]], *, live_accounts: tuple = LIVE_ACCOUNTS, live_versions: dict[str, int] | None = None, live_database: bytes | None = None) -> None:
    """The live data directory a restore lands in: the folders ``layout`` says live, with the live instance's own data
    and modes (``live_database``: these bytes for its database instead of one), and what a restore never touches."""
    root.mkdir(parents=True)
    for name in SWAPPED:
        if not layout[name][0]:
            continue
        folder = root / name
        folder.mkdir()
        if name != "sqlite":
            cases.write_files(folder, LIVE_FILES[name])
        elif live_database is not None:
            (root / DATABASE_ENTRY).write_bytes(live_database)
        else:
            shutil.copyfile(databases.head, root / DATABASE_ENTRY)
            cases.add_accounts(root / DATABASE_ENTRY, live_accounts)
            set_versions(root / DATABASE_ENTRY, LIVE_VERSIONS if live_versions is None else live_versions)
        folder.chmod(LIVE_MODES[name])
    cases.write_files(root, UNTOUCHED)


def write_check(root: Path, stage_id: str, report: StagingReport, *, status: str = "done", error_code: str | None = None, upload_id: str = CHECK_UPLOAD) -> None:
    """The state of a check, as ``restore_jobs`` writes it (lot B2b)."""
    ensure_private_dir(checks_dir(root), root)
    check = RestoreCheck(stage_id=stage_id, upload_id=upload_id, status=status, phase=None, done_bytes=report.files_size, total_bytes=report.files_size, created_at=report.staged_at, finished_at=report.staged_at, error_code=error_code)
    restore_jobs._write_state(root, check)


def write_report(stage: Path, report: StagingReport) -> None:
    (stage / STAGE_REPORT_FILE).write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")


def build(root: Path, databases: cases.Databases, checked: Checked, layout: dict[str, tuple[bool, bool]] = FULL, *, restore: bool = True, **live: Any) -> Instance:
    """A live data directory (``live_instance``) and, with ``restore``, the module's checked copy waiting in
    ``.restore/stage/`` without the folders ``layout`` does not restore, the backup's accounts at ``BACKUP_VERSIONS``,
    beside the state of its check, another archive's failed check and an upload in progress."""
    live_instance(root, databases, layout, **live)
    stage_id = checked.report.stage_id
    if restore:
        ensure_private_dir(stages_dir(root), root)
        shutil.copytree(checked.stage, stage_dir(root, stage_id), symlinks=True)
        copy = stage_dir(root, stage_id) / STAGE_DATA_FOLDER
        for name in SWAPPED:
            if not layout[name][1]:
                shutil.rmtree(copy / name)
        set_versions(copy / DATABASE_ENTRY, BACKUP_VERSIONS)
        write_check(root, stage_id, checked.report)
        write_check(root, UNRELATED_CHECK, checked.report, status="failed", error_code="checksum_mismatch", upload_id=UNRELATED_UPLOAD)
        ensure_private_dir(uploads_dir(root), root)
        upload_path(root, UNRELATED_UPLOAD).write_bytes(b"PK an archive being uploaded for another check")
    instance = Instance(root=root, stage_id=stage_id, report=checked.report, layout=dict(layout), live={}, staged={}, before=cases.fingerprint(root))
    instance.live = {name: tree(root / name) for name in SWAPPED}
    instance.staged = {name: tree(instance.copy / name) for name in SWAPPED}
    return instance


def add_stage(instance: Instance, checked: Checked, stage_id: str, **changes: Any) -> StagingReport:
    """Another checked copy beside the instance's: the module's, under ``stage_id``, its report saying so (and
    ``changes``), with the state of its check."""
    stage = stage_dir(instance.root, stage_id)
    shutil.copytree(checked.stage, stage, symlinks=True)
    report = checked.report.model_copy(update={"stage_id": stage_id, **changes})
    write_report(stage, report)
    write_check(instance.root, stage_id, report)
    return report


def confirm(apply: Any, instance: Instance, stage_id: str | None = None, *, now: datetime | None = None) -> Any:
    """``confirm_restore`` of the instance's copy (or of ``stage_id``) by an administrator, a minute after its check."""
    return apply.confirm_restore(stage_id or instance.stage_id, confirmed_by=CONFIRMED_BY, data_dir=instance.root, now=now or instance.confirm_at)


def killed(apply: Any, instance: Instance, renames: int, *, boot: Any, now: datetime) -> Mover:
    """``apply_pending_restore`` killed once ``renames`` renames are done; its ``Mover``. The apply lock must be free
    again: a killed process loses it with its descriptors, and the next start of this process would wait forever."""
    with moving(apply, **killed_after(renames)) as mover:
        try:
            outcome = apply.apply_pending_restore(instance.root, boot=boot, now=now)
        except _Crash:
            assert apply_lock_free(instance.root), "a call killed in the middle must not keep the apply lock held in this process"
            assert len(mover.moved) == renames, f"precondition: killed after {renames} renames, not {len(mover.moved)}"
            return mover
    pytest.fail(f"the call ended after {mover.calls} renames, before this case could kill it after {renames}: {outcome}")


def into_phase(apply: Any, instance: Instance, phase: str) -> Any:
    """The instance's restore brought to ``phase`` as a server brings it there (a full layout: rolled back by its third
    rename failing, so that ``failed/`` holds the restored database); the state on disk."""
    confirm(apply, instance)
    first, second = never_ran(apply), never_ran(apply, 1)
    if phase == "applying":
        killed(apply, instance, 0, boot=first, now=instance.applied_at)
    elif phase == "rolling_back":
        killed(apply, instance, instance.renames, boot=first, now=instance.applied_at)
        killed(apply, instance, 0, boot=second, now=instance.applied_at)
    elif phase in ("applied", "committed"):
        apply.apply_pending_restore(instance.root, boot=first, now=instance.applied_at)
        if phase == "committed":
            apply.finish_pending_restore(instance.root, boot=first, now=instance.committed_at)
    elif phase == "rolled_back":
        with moving(apply, fail_at=frozenset({3})):
            apply.apply_pending_restore(instance.root, boot=first, now=instance.applied_at)
    state = apply.read_restore(instance.root)
    assert state is not None and state.status == phase, f"precondition: the restore is {phase}: {state}"
    return state


def assert_swapped(instance: Instance) -> None:
    """The restored data live, the replaced data in ``previous/``, each folder as its layout says, moved out of the
    copy; nothing else of the data directory touched; nothing set aside in ``failed/``."""
    root = instance.root
    for name in SWAPPED:
        live, staged = instance.layout[name]
        here, kept = root / name, previous_of(root) / name
        assert tree(here) == (instance.staged[name] if staged else None), f"{name}: live after the swap, {'the restored folder' if staged else 'nothing: the backup has none'}"
        if staged:
            wanted = LIVE_MODES[name] if live else STAGED_MODE
            assert cases.mode(here) == wanted, f"{name}: the restored folder takes the mode of the folder it replaces, or keeps its own when it replaces none ({oct(wanted)}): {oct(cases.mode(here))}"
        assert tree(kept) == (instance.live[name] if live else None), f"{name}: previous/ holds {'the replaced live folder' if live else 'nothing'}"
        if live:
            assert cases.mode(kept) == LIVE_MODES[name], f"{name}: the replaced folder keeps its mode in previous/"
        assert not lexists(instance.copy / name), f"{name}: the restored folder is moved out of the copy, not copied"
    changed = cases.changed(outside(instance.before), outside(cases.fingerprint(root)))
    assert changed == [], f"a restore touches nothing but the four folders: {changed}"
    assert not tree(failed_of(root)), f"a swap sets nothing aside in failed/: {tree(failed_of(root))}"


def assert_put_back(instance: Instance) -> None:
    """The data directory exactly as before the restore, outside ``.restore``; nothing left in ``previous/``; the
    restored data of each folder whole, either still in the copy (never moved in) or in ``failed/`` (moved back out)."""
    root = instance.root
    changed = cases.changed(instance.before, cases.fingerprint(root))
    assert changed == [], f"the data directory must be back exactly as it was before the restore: {changed}"
    assert not tree(previous_of(root)), f"nothing is left in previous/: {tree(previous_of(root))}"
    for name in SWAPPED:
        in_copy, in_failed = tree(instance.copy / name), tree(failed_of(root) / name)
        if instance.layout[name][1]:
            assert (in_copy, in_failed) in ((instance.staged[name], None), (None, instance.staged[name])), f"{name}: the restored data, whole, in the copy or in failed/ and not both: in the copy {in_copy is not None}, in failed/ {in_failed is not None}"
        else:
            assert in_failed is None, f"{name}: nothing was restored, nothing is set aside"


def assert_unrelated_kept(root: Path) -> None:
    assert check_state_path(root, UNRELATED_CHECK).is_file() and upload_path(root, UNRELATED_UPLOAD).is_file(), "what .restore holds for other archives (a check's state, an upload in progress) is never removed by a restore"


# =============================================================================
# (a) §1 The layout
# =============================================================================


def test_the_state_its_lock_and_the_two_folders_of_a_restore_live_in_restore():
    """(a) Where a restore keeps its state and the data it moves aside: a change here strands the restores on disk."""
    print_section("(a) The layout of a restore")
    expected = {"RESTORE_STATE_FILE": STATE_FILE_NAME, "APPLY_LOCK_FILE": APPLY_LOCK_NAME, "PREVIOUS_FOLDER": PREVIOUS_NAME, "FAILED_FOLDER": FAILED_NAME}
    found = {name: new_path_name(name) for name in expected}
    assert found == expected, f"the names of .restore's items moved: {found}"
    data = Path("/srv/librefolio-data")
    where = {function: new_path_name(function)(data) for function in ("restore_state_path", "apply_lock_path", "previous_dir", "failed_dir")}
    assert where == {"restore_state_path": state_file(data), "apply_lock_path": apply_lock_of(data), "previous_dir": previous_of(data), "failed_dir": failed_of(data)}, f"each directly in <data dir>/.restore: {where}"
    items = [STAGE_FOLDER, UPLOAD_FOLDER, CHECKS_FOLDER, *found.values()]
    assert len(set(items)) == len(items), f"each item of .restore has a name of its own: {items}"
    print_success(".restore/{restore.json, apply.lock, previous/, failed/}")


def test_the_swapped_folders_are_what_an_archive_carries_the_databases_folder_first():
    swapped = new_path_name("SWAPPED_FOLDERS")
    assert swapped == SWAPPED, f"the folders a restore swaps, in this order: {swapped}"
    assert swapped == (DATABASE_ENTRY.split("/")[0], *ARCHIVED_FOLDERS), f"a restore swaps exactly what an archive carries: {swapped} against {DATABASE_ENTRY}, {ARCHIVED_FOLDERS}"
    print_success(f"SWAPPED_FOLDERS = {swapped}")


def test_stage_data_dir_is_the_data_folder_of_a_stage():
    stage_data_dir = new_path_name("stage_data_dir")
    data = Path("/srv/librefolio-data")
    assert stage_data_dir(data, cases.VALID_ID) == stage_dir(data, cases.VALID_ID) / STAGE_DATA_FOLDER == data / ".restore" / "stage" / cases.VALID_ID / "data"
    print_success(".restore/stage/<id>/data")


@pytest.mark.parametrize("value", cases.NOT_STAGE_IDS)
def test_stage_data_dir_never_builds_a_path_from_anything_but_a_stage_id(value):
    stage_data_dir = new_path_name("stage_data_dir")
    with pytest.raises(ValueError):
        stage_data_dir(Path("/srv/librefolio-data"), value)
    print_success(f"{value!r}: ValueError")


# =============================================================================
# (b) §2 The errors and the models
# =============================================================================


def test_every_refusal_is_a_restore_state_error_with_its_stable_code():
    print_section("(b) Errors and models")
    apply = apply_module()
    assert issubclass(apply.RestoreStateError, RuntimeError), "RestoreStateError is a RuntimeError"
    missing = [name for name in ERROR_CODES if not hasattr(apply, name)]
    assert missing == [], f"[new] errors of the contract missing from apply: {missing}"
    found = {name: (issubclass(getattr(apply, name), apply.RestoreStateError), getattr(apply, name).code) for name in ERROR_CODES}
    assert found == {name: (True, code) for name, code in ERROR_CODES.items()}, f"each a RestoreStateError with its code: {found}"
    assert apply.ACTIVE == {"pending", "applying", "applied", "rolling_back"}, f"the phases of a restore not finished yet: {apply.ACTIVE}"
    print_success(f"{len(ERROR_CODES)} errors, their codes; ACTIVE")


def test_a_state_is_frozen_and_its_defaults_say_nothing_happened_yet(checked):
    apply = apply_module()
    report = checked.report
    state = apply.RestoreState(status="pending", stage_id=report.stage_id, data_dir="/srv/librefolio-data", confirmed_at=report.staged_at, confirmed_by="cli", backup_created_at=report.backup.created_at, backup_app_version=report.backup.app_version, action=report.action)
    defaults = (state.format, state.swap, state.boot, state.applied_at, state.finished_at, state.reason, state.waiting, state.session_version)
    assert defaults == (1, [], None, None, None, None, None, None), f"format 1, nothing swapped, applied, finished, waited for, ended: {defaults}"
    assert apply.RestoreState.model_validate_json(state.model_dump_json()) == state, "a state reads back as it was written"
    entry, boot = apply.SwapEntry(name="sqlite", live=True, staged=True), apply.Boot(pid=4242, started=1792000000.125)
    for model, field_name, value in ((state, "status", "applied"), (entry, "live", False), (boot, "pid", 1)):
        with pytest.raises(ValidationError):
            setattr(model, field_name, value)
    print_success("RestoreState, SwapEntry, Boot: frozen")


# =============================================================================
# (c) §2 Boots
# =============================================================================


def test_current_boot_of_a_process_multiprocessing_did_not_start_is_this_process():
    """(c) Under uvicorn without workers, or under the CLI: the server is this process."""
    print_section("(c) Boots")
    apply = apply_module()
    assert multiprocessing.parent_process() is None, "precondition: this test runs in a process multiprocessing did not start"
    assert apply.current_boot() == this_boot(apply), f"this process, created at its creation time rounded to the millisecond: {apply.current_boot()}"
    print_success(f"current_boot() = {this_boot(apply)}")


def test_current_boot_reads_the_server_pid_and_says_0_when_its_creation_time_cannot_be_read(monkeypatch):
    apply = apply_module()
    restart = restart_module()
    monkeypatch.setattr(restart, "server_pid", lambda: NO_SUCH_PID)
    assert apply.current_boot() == apply.Boot(pid=NO_SUCH_PID, started=0.0), "current_boot reads restart.server_pid() when it runs, and 0.0 for a creation time psutil cannot read"
    print_success("server_pid read at call time; started 0.0")


def test_the_boot_is_read_once_per_process_and_boot_alive_reads_it_live(monkeypatch):
    """(c) §10 On Linux psutil derives a creation time from the system's boot time, which a clock step moves: the two
    steps of one start must still find the same boot. ``current_boot()`` reads it once per process (``_boot_of``, by
    pid): psutil saying another creation time afterwards does not change it. ``boot_alive`` reads it live."""
    apply = apply_module()
    first = apply.current_boot()
    assert first == this_boot(apply), f"precondition: this process, at its creation time: {first}"
    real_create_time = psutil.Process.create_time

    def create_time(process: psutil.Process) -> float:
        # This process's creation time, as psutil gives it once the clock was stepped an hour forward.
        return real_create_time(process) + 3600.0 if process.pid == os.getpid() else real_create_time(process)

    monkeypatch.setattr(psutil.Process, "create_time", create_time)
    moved = round(psutil.Process(os.getpid()).create_time(), 3)
    assert moved != first.started, "barrier: psutil now says another creation time for this process"
    assert apply.current_boot() == first, f"read once per process: the boot the first step read, not {apply.current_boot()}"
    assert apply.boot_alive(first) is False, "boot_alive reads live: the creation time psutil says now is another one"
    assert apply.boot_alive(apply.Boot(pid=os.getpid(), started=moved)) is True, "boot_alive reads live: the creation time psutil says now"
    print_success(f"current_boot() stays {first}; boot_alive reads {moved}")


BOOTS = [
    pytest.param(this_boot, True, id="this-process"),
    pytest.param(reused_pid, False, id="its-pid-created-at-another-time"),
    pytest.param(ended, False, id="a-process-that-ended"),
    pytest.param(never_ran, False, id="a-pid-no-process-has"),
]


@pytest.mark.parametrize(("make", "alive"), BOOTS)
def test_boot_alive_only_for_a_running_process_created_at_that_time(make, alive):
    """(c) A pid is reused: the process that holds it now is another one unless it was created at the boot's time."""
    apply = apply_module()
    boot = make(apply)
    assert apply.boot_alive(boot) is alive, f"boot_alive({boot}) must be {alive}"
    print_success(f"{boot}: {alive}")


# =============================================================================
# (d) §2 Reading the state
# =============================================================================


@pytest.mark.parametrize("restore", [False, True], ids=["no-restore-folder", "a-restore-folder-without-state"])
def test_an_ordinary_start_reads_no_restore_and_creates_nothing(tmp_path, databases, checked, restore):
    """(d) Every start of every instance runs the two steps: without a state they answer ``None`` at once and create
    nothing, not even ``.restore`` or the lock file."""
    print_section("(d) Reading the state")
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked, restore=restore)
    listed = cases.listing(instance.root)
    found = (apply.read_restore(instance.root), apply.protected_stage(instance.root))
    stepped = (apply.apply_pending_restore(instance.root, boot=never_ran(apply), now=instance.applied_at), apply.finish_pending_restore(instance.root, boot=never_ran(apply), now=instance.committed_at))
    assert (found, stepped) == ((None, None), (None, None)), f"no restore: None everywhere, {found}, {stepped}"
    assert cases.listing(instance.root) == listed, f"nothing created: {sorted(set(cases.listing(instance.root)) - set(listed))}"
    print_success("None, nothing created")


def test_the_steps_without_arguments_read_the_configured_data_directory_and_create_nothing(configured_data_dir, serving_here):
    """(d) The steps run without arguments: the data directory is the configured one (here a folder that must stay
    absent), the boot is ``current_boot()``. The serving lock of a data directory that cannot be opened is not held, and
    a warning says so."""
    apply = serving_here
    found = (apply.read_restore(), apply.protected_stage(configured_data_dir), apply.apply_pending_restore(), apply.finish_pending_restore())
    assert found == (None, None, None, None), f"no restore in the configured data directory: {found}"
    with logs() as events:
        held = apply.hold_serving_lock()
    assert (held, str(configured_data_dir.resolve()) in apply._SERVING) == (False, False), f"no serving lock on a data directory that cannot be opened: {held}"
    assert a_warning(events), f"a warning says the lock is not held: {levels(events)}"
    assert not configured_data_dir.exists(), "nothing created in the configured data directory"
    print_success("None, the configured data directory untouched")


def _restore_folder_a_link(instance: Instance, elsewhere: Path) -> None:
    # Not named .restore where it lands: fingerprint() skips any path below a .restore, and would not see a write there.
    shutil.move(restore_dir(instance.root), elsewhere / "moved-restore-folder")
    restore_dir(instance.root).symlink_to(elsewhere / "moved-restore-folder", target_is_directory=True)


def _restore_folder_a_file(instance: Instance, elsewhere: Path) -> None:
    shutil.rmtree(restore_dir(instance.root))
    restore_dir(instance.root).write_bytes(b"a file where .restore belongs\n")


def _state_a_link(instance: Instance, elsewhere: Path) -> None:
    shutil.move(state_file(instance.root), elsewhere / STATE_FILE_NAME)
    state_file(instance.root).symlink_to(elsewhere / STATE_FILE_NAME)


def _state_unreadable(instance: Instance, elsewhere: Path) -> None:
    state_file(instance.root).write_text('{"format": 1, "status": "pending", "stage_id": "half a sta', encoding="utf-8")


#: A pending restore made untrustworthy, whether the contract has an error logged for it, and how ``read_restore`` reads
#: it since B-33: ``None`` for a ``.restore`` that is a link or a file (ignored, as before), the ``reason`` of its
#: ``RestoreStateUnreadableError`` for a state file that is a link (``not_a_file``) or not valid (``invalid``).
UNTRUSTED = [
    pytest.param(_restore_folder_a_link, True, None, id="restore-folder-a-link"),
    pytest.param(_restore_folder_a_file, True, None, id="restore-folder-a-file"),
    pytest.param(_state_a_link, False, "not_a_file", id="state-a-link"),
    pytest.param(_state_unreadable, True, "invalid", id="state-unreadable"),
]


@pytest.mark.parametrize(("untrust", "error_logged", "read_as"), UNTRUSTED)
def test_a_restore_that_cannot_be_trusted_is_not_read_applied_or_committed(tmp_path, databases, checked, untrust, error_logged, read_as):
    """(d)(g)(h) ``.restore`` or the state a link (never followed), a file, unreadable: no restore is applied or
    committed, nothing is moved, written or removed, neither here nor where a link points. For ``finish`` the contract
    only says "no state, None": a link it must not follow either. B-33 §1, §2: ``.restore`` a link or a file is still no
    restore (``read_restore`` and ``protected_stage`` ``None``); a state file that is a link or not valid is a state that
    cannot be read: ``read_restore`` raises ``RestoreStateUnreadableError`` with its reason, ``protected_stage`` is
    ``EVERY_STAGE``. The startup steps unchanged: ``None``."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    confirm(apply, instance)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    untrust(instance, elsewhere)
    data, items, pointed, kind = cases.fingerprint(instance.root), restore_items(instance.root), cases.fingerprint(elsewhere), restore_kind(instance.root)
    with moving(apply) as mover, logs() as events:
        returned, raised = answer_of(lambda: apply.read_restore(instance.root))
        protected = apply.protected_stage(instance.root)
        stepped = (apply.apply_pending_restore(instance.root, boot=never_ran(apply), now=instance.applied_at), apply.finish_pending_restore(instance.root, boot=never_ran(apply), now=instance.committed_at))
    if read_as is None:
        assert (returned, raised, protected) == (None, None, None), f"{untrust.__name__}: no restore read, no stage protected: {returned!r}, {raised!r}, {protected!r}"
    else:
        assert_unreadable_for(apply, "read_restore", returned, raised, read_as, instance.root)
        assert protected == b33_name(apply, "EVERY_STAGE"), f"{untrust.__name__}: a state that cannot be read protects every stage (B-33 §2), not {protected!r}"
    assert stepped == (None, None), f"the startup steps read nothing to trust: {stepped}"
    assert mover.calls == 0, f"nothing moved: {mover.moved}"
    assert (cases.fingerprint(instance.root), restore_items(instance.root), cases.fingerprint(elsewhere), restore_kind(instance.root)) == (data, items, pointed, kind), "nothing written or removed, here or where a link points; .restore left as it stands"
    if error_logged:
        assert an_error(events), f"an error logged: {levels(events)}"
    print_success(f"{untrust.__name__}: None, nothing touched")


#: (§10) A state the product never writes, naming something else than a swapped folder or a stage: a journal entry leading
#: out of the data directory, naming the instance key's folder, an absolute path; a stage id leading out, in capitals.
UNTRUSTED_FIELDS = [
    pytest.param("swap", "../x", id="a-swap-entry-leading-out"),
    pytest.param("swap", "secrets", id="a-swap-entry-naming-secrets"),
    pytest.param("swap", "an-absolute-path", id="a-swap-entry-an-absolute-path"),
    pytest.param("stage_id", "../" + "0" * 29, id="a-stage-id-leading-out"),
    pytest.param("stage_id", cases.VALID_ID.upper(), id="a-stage-id-in-capitals"),
]


@pytest.mark.parametrize(("field_name", "value"), UNTRUSTED_FIELDS)
def test_a_state_naming_anything_but_a_swapped_folder_or_a_stage_is_unreadable_and_nothing_is_done(tmp_path, databases, checked, field_name, value):
    """(d) §10 The state file lives in the data directory: a name read from it never becomes a path. A restore applied
    by a start that died (the next start would undo it, by the names of its journal) whose journal or stage id was
    changed: the steps do nothing — nothing moved, written or removed, here or where a name leads — and an error is
    logged. B-33 §1, §2: ``read_restore`` raises ``RestoreStateUnreadableError`` (``invalid``), ``protected_stage`` is
    ``EVERY_STAGE`` (it was ``None``)."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    confirm(apply, instance)
    apply.apply_pending_restore(instance.root, boot=never_ran(apply), now=instance.applied_at)
    elsewhere, beside = tmp_path / "elsewhere", tmp_path / "x"
    cases.write_files(elsewhere, {"keep.txt": b"a folder outside the data directory\n"})
    cases.write_files(beside, {"keep.txt": b"a folder beside the data directory\n"})
    document = json.loads(state_file(instance.root).read_text(encoding="utf-8"))
    if field_name == "swap":
        document["swap"][-1]["name"] = str(elsewhere) if value == "an-absolute-path" else value
    else:
        document["stage_id"] = value
    state_file(instance.root).write_text(json.dumps(document), encoding="utf-8")
    snapshot = (cases.fingerprint(instance.root), restore_items(instance.root), tree(elsewhere), tree(beside))
    with moving(apply) as mover, logs() as events:
        returned, raised = answer_of(lambda: apply.read_restore(instance.root))
        protected = apply.protected_stage(instance.root)
        stepped = (apply.apply_pending_restore(instance.root, boot=never_ran(apply, 1), now=instance.committed_at), apply.finish_pending_restore(instance.root, boot=never_ran(apply, 1), now=instance.committed_at))
    assert stepped == (None, None), f"{field_name} = {value!r}: an unreadable state, nothing done: {stepped}"
    assert_unreadable_for(apply, "read_restore", returned, raised, "invalid", instance.root)
    assert protected == b33_name(apply, "EVERY_STAGE"), f"{field_name} = {value!r}: every stage protected (B-33 §2), not {protected!r}"
    assert mover.calls == 0, f"nothing moved: {mover.moved}"
    assert (cases.fingerprint(instance.root), restore_items(instance.root), tree(elsewhere), tree(beside)) == snapshot, "nothing written or removed, here or where a name leads; the state file left as it is"
    assert an_error(events), f"an error logged: {levels(events)}"
    print_success(f"{field_name} = {value!r}: unreadable, nothing done")


@pytest.mark.parametrize("phase", [*ACTIVE_PHASES, *TERMINAL_PHASES])
def test_the_protected_stage_is_the_copy_of_an_active_restore_only(tmp_path, databases, checked, phase):
    """(d) The copy a restore needs until it ends: ``prune`` and the API keep their hands off it."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    into_phase(apply, instance, phase)
    expected = instance.stage_id if phase in ACTIVE_PHASES else None
    assert apply.protected_stage(instance.root) == expected, f"{phase}: {apply.protected_stage(instance.root)}, not {expected}"
    print_success(f"{phase}: {expected}")


# =============================================================================
# (e) §2 confirm_restore
# =============================================================================


def test_confirm_writes_a_pending_state_from_the_report_atomically_and_privately(tmp_path, databases, checked):
    """(e) The state a start will apply: ``pending``, what the report says of the backup, the data directory as it
    resolves (the path given is not), 0600, written beside as ``.part`` then renamed: none left. The copy is kept."""
    print_section("(e) confirm_restore")
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    copy_before = tree(stage_dir(instance.root, instance.stage_id))
    given = instance.root / ".." / instance.root.name
    assert str(given) != str(instance.root.resolve()), "precondition: the path given is not resolved"
    state = apply.confirm_restore(instance.stage_id, confirmed_by=CONFIRMED_BY, data_dir=given, now=instance.confirm_at)
    report = instance.report
    expected = {
        "format": 1,
        "status": "pending",
        "stage_id": instance.stage_id,
        "data_dir": str(instance.root.resolve()),
        "confirmed_at": instance.confirm_at,
        "confirmed_by": CONFIRMED_BY,
        "confirmed_via": "admin",
        "backup_created_at": report.backup.created_at,
        "backup_app_version": report.backup.app_version,
        "action": report.action,
        "swap": [],
        "boot": None,
        "applied_at": None,
        "finished_at": None,
        "reason": None,
        "waiting": None,
        "session_version": None,
        # Lot B5-1 (s): the owner's choice and what became of it, nothing for a self-hosted confirmation.
        "owner_user_id": None,
        "owner_outcome": None,
        # Lot B5-1d: only the swap sets it.
        "token_watermark": None,
    }
    assert state.model_dump() == expected, f"the state of a confirmed restore: {state.model_dump()}"
    written = state_file(instance.root)
    assert written.is_file() and not written.is_symlink() and cases.mode(written) == 0o600, f"restore.json, a file of its owner only: {oct(cases.mode(written))}"
    assert apply.RestoreState.model_validate_json(written.read_text(encoding="utf-8")) == state == apply.read_restore(instance.root), "the state on disk is the state returned"
    assert [path.name for path in restore_dir(instance.root).iterdir() if path.name.endswith(".part")] == [], "written atomically: no .part left"
    assert cases.mode(restore_dir(instance.root)) == 0o700, ".restore stays private"
    assert cases.changed(instance.before, cases.fingerprint(instance.root)) == [], "nothing written outside .restore"
    assert tree(stage_dir(instance.root, instance.stage_id)) == copy_before, "the checked copy is kept as it is, for the start"
    assert apply.protected_stage(instance.root) == instance.stage_id, "and protected"
    print_success(f"pending, {state.data_dir}")


def _no_checked_copy(instance: Instance, elsewhere: Path) -> None:
    shutil.rmtree(stage_dir(instance.root, instance.stage_id))


def _no_data_folder(instance: Instance, elsewhere: Path) -> None:
    shutil.rmtree(instance.copy)


def _no_database(instance: Instance, elsewhere: Path) -> None:
    (instance.copy / DATABASE_ENTRY).unlink()


def _database_a_folder(instance: Instance, elsewhere: Path) -> None:
    (instance.copy / DATABASE_ENTRY).unlink()
    (instance.copy / DATABASE_ENTRY).mkdir()


def _a_folder_of_the_copy_a_link(instance: Instance, elsewhere: Path) -> None:
    shutil.move(instance.copy / "custom-uploads", elsewhere / "custom-uploads")
    (instance.copy / "custom-uploads").symlink_to(elsewhere / "custom-uploads", target_is_directory=True)


def _the_data_folder_a_link(instance: Instance, elsewhere: Path) -> None:
    shutil.move(instance.copy, elsewhere / "data")
    instance.copy.symlink_to(elsewhere / "data", target_is_directory=True)


def _no_report(instance: Instance, elsewhere: Path) -> None:
    (stage_dir(instance.root, instance.stage_id) / STAGE_REPORT_FILE).unlink()


def _not_a_report(instance: Instance, elsewhere: Path) -> None:
    (stage_dir(instance.root, instance.stage_id) / STAGE_REPORT_FILE).write_text('{"stage_id": "not a report"}', encoding="utf-8")


#: A checked copy a restore cannot use (the contract's ``RestoreStageMissingError``, and ``stage_missing`` at a start).
UNUSABLE_COPIES = [
    pytest.param(_no_checked_copy, id="no-checked-copy"),
    pytest.param(_no_data_folder, id="no-data-folder"),
    pytest.param(_no_database, id="no-database"),
    pytest.param(_database_a_folder, id="database-a-folder"),
    pytest.param(_a_folder_of_the_copy_a_link, id="a-folder-of-the-copy-a-link"),
    pytest.param(_the_data_folder_a_link, id="the-data-folder-a-link"),
]
UNREADABLE_REPORTS = [pytest.param(_no_report, id="no-report"), pytest.param(_not_a_report, id="not-a-report")]


@pytest.mark.parametrize("unusable", UNUSABLE_COPIES + UNREADABLE_REPORTS)
def test_a_copy_that_cannot_be_restored_is_refused_as_missing_and_nothing_is_written(tmp_path, databases, checked, unusable):
    """(e) Step 1: no readable report, the copy's database not a file, a folder of the copy not a plain folder."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    unusable(instance, elsewhere)
    items, pointed = restore_items(instance.root), cases.fingerprint(elsewhere)
    with pytest.raises(apply.RestoreStateError) as raised:
        confirm(apply, instance)
    assert (type(raised.value).__name__, raised.value.code) == ("RestoreStageMissingError", "restore_stage_not_found"), f"{unusable.__name__}: {type(raised.value).__name__}: {raised.value}"
    assert (restore_items(instance.root), cases.fingerprint(elsewhere)) == (items, pointed), f"{unusable.__name__}: nothing written, not even the lock, nor anything where a link points"
    print_success(f"{unusable.__name__}: restore_stage_not_found")


#: The problems a confirmation can meet at once, and the refusal that must win: the contract's order.
PRECEDENCE = [
    pytest.param(("missing", "blockers", "expired", "outdated", "pending"), "RestoreStageMissingError", id="a-missing-copy-first"),
    pytest.param(("blockers", "expired", "outdated", "pending"), "RestoreNotRestorableError", id="then-blockers"),
    pytest.param(("expired", "outdated", "pending"), "RestoreStageExpiredError", id="then-expired"),
    pytest.param(("outdated", "pending"), "RestoreStageOutdatedError", id="then-outdated"),
    pytest.param(("pending",), "RestoreAlreadyPendingError", id="then-already-pending"),
]


@pytest.mark.parametrize(("problems", "refusal"), PRECEDENCE)
def test_confirm_refuses_in_the_contracts_order_and_writes_nothing(tmp_path, databases, checked, monkeypatch, problems, refusal):
    """(e) A second copy (``OTHER_STAGE``) confirmed with ``problems``: its database gone, a blocker in its report, past
    its ``expires_at``, LibreFolio updated since its check, the instance's own restore pending. The first problem in the
    contract's order decides."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    if "pending" in problems:
        confirm(apply, instance)
    blocked = {"blockers": ["no_administrator"], "administrators": []} if "blockers" in problems else {}
    report = add_stage(instance, checked, OTHER_STAGE, **blocked)
    if "missing" in problems:
        (stage_dir(instance.root, OTHER_STAGE) / STAGE_DATA_FOLDER / DATABASE_ENTRY).unlink()
    if "outdated" in problems:
        assert hasattr(apply, "alembic_head_revision"), "[new] apply imports alembic_head_revision into its namespace (contract)"
        monkeypatch.setattr(apply, "alembic_head_revision", lambda: NEWER_HEAD)
    now = report.expires_at if "expired" in problems else instance.confirm_at
    items = restore_items(instance.root)
    with pytest.raises(apply.RestoreStateError) as raised:
        confirm(apply, instance, OTHER_STAGE, now=now)
    assert type(raised.value).__name__ == refusal, f"{problems}: {refusal} must win, not {type(raised.value).__name__}: {raised.value}"
    assert raised.value.code == ERROR_CODES[refusal], f"{refusal}: the code {ERROR_CODES[refusal]}, not {raised.value.code}"
    assert restore_items(instance.root) == items, f"{refusal}: nothing written"
    print_success(f"{problems}: {refusal}")


@pytest.mark.parametrize(("before_expiry", "expired"), [(timedelta(0), True), (timedelta(microseconds=1), False)], ids=["at-expires-at", "a-microsecond-before"])
def test_a_checked_copy_expires_at_its_expires_at(tmp_path, databases, checked, before_expiry, expired):
    """(e) ``expires_at <= now`` is expired: at that very instant already."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    now = instance.report.expires_at - before_expiry
    if not expired:
        assert confirm(apply, instance, now=now).status == "pending", "a microsecond before its expiry, the copy is confirmed"
        return
    items = restore_items(instance.root)
    with pytest.raises(apply.RestoreStageExpiredError) as raised:
        confirm(apply, instance, now=now)
    assert raised.value.code == "restore_stage_expired" and restore_items(instance.root) == items, "expired at expires_at, nothing written"
    print_success("expired at expires_at")


def test_a_head_that_cannot_be_read_does_not_stop_the_confirmation(tmp_path, databases, checked, monkeypatch):
    """(e) Step 4 compares the head only when ``alembic_head_revision`` can read it."""
    apply = apply_module()
    assert hasattr(apply, "alembic_head_revision"), "[new] apply imports alembic_head_revision into its namespace (contract)"
    monkeypatch.setattr(apply, "alembic_head_revision", lambda: None)
    instance = build(tmp_path / "instance", databases, checked)
    assert confirm(apply, instance).status == "pending", "a head that cannot be read is no proof LibreFolio was updated"
    print_success("head None: pending")


@pytest.mark.parametrize("phase", ACTIVE_PHASES)
def test_confirm_while_a_restore_is_active_is_refused_and_changes_nothing(tmp_path, databases, checked, phase):
    """(e) Step 5: one restore at a time, in every phase until it ends. Its ``previous/`` is not a leftover."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    state = into_phase(apply, instance, phase)
    add_stage(instance, checked, OTHER_STAGE)
    data, items = cases.fingerprint(instance.root), restore_items(instance.root)
    with pytest.raises(apply.RestoreAlreadyPendingError) as raised:
        confirm(apply, instance, OTHER_STAGE)
    assert raised.value.code == "restore_already_pending", raised.value.code
    assert (cases.fingerprint(instance.root), restore_items(instance.root), apply.read_restore(instance.root)) == (data, items, state), f"{phase}: nothing changed"
    print_success(f"{phase}: restore_already_pending")


@pytest.mark.parametrize("finished", ["rolled-back", "no-state-left"])
def test_confirm_removes_the_leftovers_of_a_finished_restore(tmp_path, databases, checked, finished):
    """(e) ``previous/`` and ``failed/`` a restore left (rolled back before its commit cleaned up, or with no state at
    all) are removed under the lock; nothing else of ``.restore``."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    if finished == "rolled-back":
        into_phase(apply, instance, "rolled_back")
    else:
        cases.write_files(previous_of(instance.root), {"custom-uploads/left.png": b"set aside by an earlier restore"})
        cases.write_files(failed_of(instance.root), {"sqlite/app.db": b"a restored database a rollback set aside"})
    assert tree(failed_of(instance.root)), "precondition: failed/ holds what a finished restore left"
    add_stage(instance, checked, OTHER_STAGE)
    state = confirm(apply, instance, OTHER_STAGE)
    assert (state.status, state.stage_id) == ("pending", OTHER_STAGE), f"the new restore is pending: {state}"
    assert [path.name for path in (previous_of(instance.root), failed_of(instance.root)) if lexists(path)] == [], "the leftovers are removed"
    assert_unrelated_kept(instance.root)
    print_success(f"{finished}: previous/ and failed/ removed")


@pytest.mark.parametrize("make", [_restore_folder_a_link, _restore_folder_a_file], ids=["a-link", "a-file"])
def test_confirm_refuses_a_restore_folder_that_is_not_a_plain_folder_and_writes_nothing_through_it(tmp_path, databases, checked, make):
    """(e) ``.restore`` a link (to a folder holding the very copy) or a file: ``BackupPathError`` naming it. The
    contract lists reading the report first; a file there makes the report unreadable too, and must still be this."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    make(instance, elsewhere)
    pointed, kind = cases.fingerprint(elsewhere), restore_kind(instance.root)
    with pytest.raises(BackupPathError) as raised:
        confirm(apply, instance)
    assert raised.value.path == restore_dir(instance.root), f"the error names .restore: {raised.value.path}"
    assert cases.fingerprint(elsewhere) == pointed, f"nothing written through the link: {cases.changed(pointed, cases.fingerprint(elsewhere))}"
    assert restore_kind(instance.root) == kind, f".restore left as it stands, a {kind}"
    print_success(f"{make.__name__}: BackupPathError")


def test_confirm_refuses_a_state_that_is_a_link_and_never_writes_through_it(tmp_path, databases, checked):
    """(e) B-33 §1 (it replaced the link before B-33): a state file that is a link is a state that cannot be read
    (``not_a_file``): a restore may have stopped half way behind it. ``confirm_restore`` raises
    ``RestoreStateUnreadableError``; the link stays, what it points to never written, nothing else written."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    pointed = tmp_path / "elsewhere" / STATE_FILE_NAME
    pointed.parent.mkdir()
    pointed.write_text("a file a link points to\n", encoding="utf-8")
    state_file(instance.root).symlink_to(pointed)
    data, items = cases.fingerprint(instance.root), but_the_lock(restore_items(instance.root))
    returned, raised = answer_of(lambda: confirm(apply, instance))
    assert_unreadable_for(apply, "confirm_restore", returned, raised, "not_a_file", instance.root)
    assert pointed.read_text(encoding="utf-8") == "a file a link points to\n", "never written through the link"
    assert state_file(instance.root).is_symlink(), "the link left as it is"
    assert (cases.fingerprint(instance.root), but_the_lock(restore_items(instance.root))) == (data, items), "nothing written or removed (the apply lock aside)"
    print_success("a link: restore_state_unreadable (not_a_file), the link and its target untouched")


@pytest.mark.parametrize("value", cases.NOT_STAGE_IDS)
def test_confirm_never_builds_a_path_from_anything_but_a_stage_id(tmp_path, databases, checked, value):
    """(e) The contract does not name the error for a stage id that is not one (stage_dir's ``ValueError``, or no such
    copy): either, as long as nothing is written."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    items = restore_items(instance.root)
    with pytest.raises((ValueError, apply.RestoreStageMissingError)):
        apply.confirm_restore(value, confirmed_by=CONFIRMED_BY, data_dir=instance.root, now=instance.confirm_at)
    assert restore_items(instance.root) == items, f"{value!r}: nothing written"
    print_success(f"{value!r}: refused")


# =============================================================================
# (f) §2 cancel_restore
# =============================================================================


def test_cancel_removes_a_pending_restore_and_keeps_its_checked_copy(tmp_path, databases, checked):
    """(f) The API's cancel: the restore no longer waits; its copy stays until it expires, and can be confirmed again."""
    print_section("(f) cancel_restore")
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    pending = confirm(apply, instance)
    copy_before = tree(stage_dir(instance.root, instance.stage_id))
    assert apply.cancel_restore(data_dir=instance.root) == pending, "the state the restore had"
    assert (lexists(state_file(instance.root)), apply.read_restore(instance.root)) == (False, None), "no restore waits"
    assert tree(stage_dir(instance.root, instance.stage_id)) == copy_before and check_state_path(instance.root, instance.stage_id).is_file(), "the copy and its check kept"
    assert cases.changed(instance.before, cases.fingerprint(instance.root)) == [], "nothing else changed"
    assert_unrelated_kept(instance.root)
    assert confirm(apply, instance).status == "pending", "the checked copy can be confirmed again"
    print_success("cancelled, copy kept, confirmed again")


def test_cancel_with_drop_copy_removes_the_copy_and_its_check_too(tmp_path, databases, checked):
    """(f) The CLI's ``pending --cancel``: nothing of that restore is left."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    pending = confirm(apply, instance)
    assert apply.cancel_restore(data_dir=instance.root, drop_copy=True) == pending, "the state the restore had"
    left = [path.name for path in (state_file(instance.root), stage_dir(instance.root, instance.stage_id), check_state_path(instance.root, instance.stage_id)) if lexists(path)]
    assert left == [], f"the state, the copy and its check removed: {left}"
    assert cases.changed(instance.before, cases.fingerprint(instance.root)) == [], "nothing else changed"
    assert_unrelated_kept(instance.root)
    print_success("cancelled, copy dropped")


@pytest.mark.parametrize("phase", ["none", "applying", "applied", "rolling_back", *TERMINAL_PHASES])
def test_cancel_of_anything_but_a_pending_restore_is_refused_and_changes_nothing(tmp_path, databases, checked, phase):
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    if phase != "none":
        into_phase(apply, instance, phase)
    data, items = cases.fingerprint(instance.root), restore_items(instance.root)
    with pytest.raises(apply.RestoreNotPendingError) as raised:
        apply.cancel_restore(data_dir=instance.root, drop_copy=True)
    assert raised.value.code == "restore_not_pending", raised.value.code
    assert (cases.fingerprint(instance.root), restore_items(instance.root)) == (data, items), f"{phase}: nothing changed, the copy kept"
    print_success(f"{phase}: restore_not_pending")


@pytest.mark.parametrize("code", [EACCES, EIO], ids=["EACCES", "EIO"])
def test_a_copy_that_cannot_be_removed_leaves_the_restore_cancelled_with_a_warning(tmp_path, databases, checked, monkeypatch, code):
    """(f) B-31, ``drop_copy``: the copy goes once the restore is dropped (``_remove_leftovers``, inside the lock). An
    ``OSError`` there comes too late to keep the restore, cancelled already: ``cancel_restore`` returns its state, the
    state file gone, and one warning says that the copy goes when its check expires, with the stage and the error (its
    type and the system's words); the one info line of the cancel says ``copy_dropped`` False. It never raises. Red
    before B-31: the ``OSError`` gets out, once the state is gone."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    pending = confirm(apply, instance)
    failure = OSError(code, os.strerror(code), str(stage_dir(instance.root, instance.stage_id)))
    calls: list[tuple[Path, str | None]] = []

    def failing_removal(data_dir: Path, stage_id: str | None) -> None:
        calls.append((Path(data_dir), stage_id))
        raise failure

    monkeypatch.setattr(apply, "_remove_leftovers", failing_removal)
    with logs() as events:
        try:
            returned = apply.cancel_restore(data_dir=instance.root, drop_copy=True)
        except OSError as exc:
            pytest.fail(f"cancel_restore let the OSError of the copy's removal out, once the restore was dropped: {exc!r}")
    assert calls == [(instance.root, instance.stage_id)], f"precondition: the copy's removal was tried once, for its stage: {calls}"
    assert returned == pending, f"the state the restore had: {returned}"
    assert (lexists(state_file(instance.root)), apply.read_restore(instance.root)) == (False, None), "the restore is cancelled: its state is gone"
    warned = [(level, message) for level, message in logged(events) if level in ("warning", "error", "critical")]
    assert warned == [("warning", COPY_NOT_REMOVED)], f"one warning, and only that one: {logged(events)}"
    event = next(event for event in events if event.get("event") == COPY_NOT_REMOVED)
    error = str(event.get("error"))
    assert event.get("stage_id") == instance.stage_id and type(failure).__name__ in error and str(failure.strerror) in error, f"the warning gives the stage and the error, its type and the system's words ({type(failure).__name__}, {failure.strerror}): {event}"
    cancelled = [(event.get("log_level"), event.get("copy_dropped")) for event in events if event.get("event") == RESTORE_CANCELLED]
    assert cancelled == [("info", False)], f"one info line says the restore is cancelled, its copy not dropped: {cancelled}"
    print_success(f"{type(failure).__name__}: cancelled, one warning, nothing raised, copy_dropped=False")


def test_a_cancel_that_keeps_the_copy_never_tries_to_remove_it(tmp_path, databases, checked, monkeypatch):
    """(f) B-31, a guard (unchanged behaviour, green before B-31 too): without ``drop_copy`` the copy is not touched, so
    no failure to remove it can come: ``_remove_leftovers`` is never called, the restore cancelled, its copy kept, and
    the info line says ``copy_dropped`` False."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    pending = confirm(apply, instance)
    copy_before = tree(stage_dir(instance.root, instance.stage_id))
    calls: list[tuple[Any, ...]] = []

    def no_removal(*args: Any) -> None:
        calls.append(args)
        raise AssertionError("_remove_leftovers ran for a cancel that keeps the copy")

    monkeypatch.setattr(apply, "_remove_leftovers", no_removal)
    with logs() as events:
        returned = apply.cancel_restore(data_dir=instance.root, drop_copy=False)
    assert returned == pending, "the state the restore had"
    assert calls == [], f"no removal tried: {calls}"
    assert (lexists(state_file(instance.root)), tree(stage_dir(instance.root, instance.stage_id))) == (False, copy_before), "the restore cancelled, its copy kept as it was"
    cancelled = [(event.get("log_level"), event.get("copy_dropped")) for event in events if event.get("event") == RESTORE_CANCELLED]
    assert cancelled == [("info", False)], f"one info line says the restore is cancelled, its copy not dropped: {cancelled}"
    print_success("drop_copy=False: _remove_leftovers never called, copy_dropped=False")


# =============================================================================
# (o) B-32 §3 A state the file system cannot read
# =============================================================================
#
# The state file is there, a regular file, and it cannot be read: opening it fails (EACCES or EIO: ``os.open`` failing
# for that file alone, every other path opened as it is; or its mode 000), or ``.restore/`` cannot be searched. A
# restore may still wait, so the callers that act on it say so (strict); the startup steps read it as none, the error
# logged (lenient). B-33: its ``reason`` is ``io``, and ``protected_stage`` is ``EVERY_STAGE`` (r); a state that is not a
# file or not valid is unreadable too (r), no longer «none».

#: (B-32) What ``RestoreStateUnreadableError`` says before its reason, the system's words.
STATE_UNREADABLE = "The state of the restore cannot be read: "
#: How a state file comes to be unreadable: its opening failing (EACCES, EIO), or its mode 000 (root reads it all the same).
UNREADABLE_STATES = [
    pytest.param("EACCES", id="its-opening-fails-EACCES"),
    pytest.param("EIO", id="its-opening-fails-EIO"),
    pytest.param("mode-000", id="its-mode-000", marks=cases.needs_permission_checks),
]
#: The callers that keep reading such a state as none (lenient): the two startup steps. ``protected_stage`` left them with
#: B-33: it is ``EVERY_STAGE`` then (r).
LENIENT = ["apply_pending_restore", "finish_pending_restore"]


class Modes:
    """``chmod`` for a test: every mode it changed is put back by ``put_back``, at the latest when the test ends, whatever
    happened (pytest must clean ``tmp_path``, and the tree is read whole to be compared)."""

    def __init__(self) -> None:
        self._changed: list[tuple[Path, int]] = []

    def chmod(self, path: Path, mode: int) -> None:
        self._changed.append((path, cases.mode(path)))
        path.chmod(mode)

    def put_back(self) -> None:
        while self._changed:
            path, mode = self._changed.pop()
            path.chmod(mode)


@pytest.fixture
def modes() -> Iterator[Modes]:
    changed = Modes()
    try:
        yield changed
    finally:
        changed.put_back()


def make_state_unreadable(patch: pytest.MonkeyPatch, modes: Modes, root: Path, how: str) -> str:
    """The state file of ``root`` made one the file system cannot read, as ``how`` says (``UNREADABLE_STATES``); the
    reason a reader gives for it, the system's words. ``os.open`` fails only when it is asked for that very file."""
    if how == "mode-000":
        modes.chmod(state_file(root), 0o000)
        return os.strerror(EACCES)
    code = {"EACCES": EACCES, "EIO": EIO}[how]
    target = os.path.realpath(state_file(root))
    real_open = os.open

    def failing_open(path: Any, flags: int, *args: Any, **kwargs: Any) -> int:
        if kwargs.get("dir_fd") is None and os.path.realpath(os.fsdecode(path)) == target:
            raise OSError(code, os.strerror(code), os.fsdecode(path))
        return real_open(path, flags, *args, **kwargs)

    patch.setattr(os, "open", failing_open)
    return os.strerror(code)


def answer_of(call: Callable[[], Any]) -> tuple[Any, Exception | None]:
    """What ``call`` returned, or the exception it raised."""
    try:
        return call(), None
    except Exception as exc:
        return None, exc


def assert_unreadable_for(apply: Any, what: str, returned: Any, raised: Exception | None, reason: str, root: Path) -> None:
    """``what`` said that the state cannot be read: ``RestoreStateUnreadableError``, a ``RestoreStateError``, its code,
    its ``reason`` the word of B-33 §1 (``io``, ``not_a_file``, ``invalid``), its message the contract's opening, no path
    in it. Asked in this order, so that a failure shows today's answer first (``None``, ``restore_not_pending``, a
    confirmation that went on)."""
    assert raised is not None, f"{what} answered {returned!r} for a state it cannot read: a restore may still wait there, so it must raise, not answer as if none did"
    code = getattr(raised, "code", None)
    assert code == "restore_state_unreadable", f"{what} raised {type(raised).__name__} ({code}) for a state it cannot read: restore_state_unreadable expected: {raised}"
    unreadable = getattr(apply, "RestoreStateUnreadableError", None)
    assert unreadable is not None and isinstance(raised, unreadable) and isinstance(raised, apply.RestoreStateError), f"[new] {what}: an apply.RestoreStateUnreadableError, a RestoreStateError: {type(raised).__mro__}"
    assert getattr(raised, "reason", None) == reason, f"[new] B-33 §1: {what}: its reason is {reason!r}, not {getattr(raised, 'reason', None)!r}: {raised}"
    assert str(raised).startswith(STATE_UNREADABLE.rstrip(": ")), f"{what}: the contract's message: {raised}"
    cases.holds_no_path(str(raised), state_file(root), root)


def assert_state_unreadable(apply: Any, what: str, returned: Any, raised: Exception | None, words: str, root: Path) -> None:
    """(o) B-32, as amended by B-33 §1: a state the file system refused, ``RestoreStateUnreadableError`` with the reason
    ``io`` (it was the system's words before B-33); its message still the contract's with the system's ``words``."""
    assert_unreadable_for(apply, what, returned, raised, "io", root)
    assert str(raised) == STATE_UNREADABLE + words, f"{what}: the contract's message, the system's words in it: {raised}"


def but_the_lock(items: dict[str, tuple]) -> dict[str, tuple]:
    """What ``.restore`` holds (``restore_items``) but the apply lock, which a refusal taken under it may create."""
    return {name: value for name, value in items.items() if name != APPLY_LOCK_NAME}


def bytes_of(path: Path) -> bytes | None:
    """The bytes of a file, ``None`` where nothing stands."""
    return path.read_bytes() if lexists(path) else None


@pytest.mark.parametrize("how", UNREADABLE_STATES)
def test_read_restore_says_that_a_state_it_cannot_read_cannot_be_read(tmp_path, databases, checked, monkeypatch, modes, how):
    """(o) B-32 §3 (s1) A restore waits, its state a regular file that cannot be read: ``read_restore`` raises
    ``RestoreStateUnreadableError`` (``restore_state_unreadable``, its reason «Permission denied» or «Input/output
    error», no path), an error logged; nothing created or changed. Red before B-32: ``None``, as if no restore waited."""
    print_section("(o) B-32: a state the file system cannot read")
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    confirm(apply, instance)
    data, items = cases.fingerprint(instance.root), restore_items(instance.root)
    reason = make_state_unreadable(monkeypatch, modes, instance.root, how)
    with logs() as events:
        returned, raised = answer_of(lambda: apply.read_restore(instance.root))
    modes.put_back()
    assert_state_unreadable(apply, "read_restore", returned, raised, reason, instance.root)
    assert an_error(events), f"an error logged: {logged(events)}"
    assert (cases.fingerprint(instance.root), restore_items(instance.root)) == (data, items), "nothing created or changed"
    print_success(f"{how}: restore_state_unreadable, {reason}")


@cases.needs_permission_checks
@pytest.mark.parametrize("caller", ["read_restore", "cancel_restore"])
def test_a_restore_folder_the_server_cannot_search_is_unreadable_never_no_restore(tmp_path, databases, checked, modes, caller):
    """(o) B-32 §3 (s2) ``.restore/`` without its search permission: whether a state is there cannot be known, and a
    restore may wait. ``read_restore`` raises ``RestoreStateUnreadableError``, and so does ``cancel_restore`` — not
    ``RestoreNotPendingError``, which its look for the file before the lock (``lexists``) answered. Nothing created or
    changed. Red before B-32: ``None``; ``restore_not_pending``."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    confirm(apply, instance)
    data, items = cases.fingerprint(instance.root), restore_items(instance.root)
    folder = restore_dir(instance.root)
    modes.chmod(folder, cases.mode(folder) & ~0o111)
    calls = {"read_restore": lambda: apply.read_restore(instance.root), "cancel_restore": lambda: apply.cancel_restore(data_dir=instance.root, drop_copy=True)}
    with logs() as events:
        returned, raised = answer_of(calls[caller])
    modes.put_back()
    assert_state_unreadable(apply, caller, returned, raised, os.strerror(EACCES), instance.root)
    assert an_error(events), f"an error logged: {logged(events)}"
    assert (cases.fingerprint(instance.root), restore_items(instance.root)) == (data, items), "nothing created or changed"
    print_success(f"{caller}: restore_state_unreadable")


@pytest.mark.parametrize("how", UNREADABLE_STATES)
def test_a_pending_restore_whose_state_cannot_be_read_is_not_cancelled(tmp_path, databases, checked, monkeypatch, modes, how):
    """(o) B-32 §3 (s3) ``cancel_restore(drop_copy=True)`` while the state of a waiting restore cannot be read: raises
    ``RestoreStateUnreadableError``; the state file, the copy and the ticket stay byte for byte, nothing else changes.
    Red before B-32: ``restore_not_pending``, as if none waited."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    confirm(apply, instance)
    ticket_of(instance)
    kept = (bytes_of(state_file(instance.root)), tree(stage_dir(instance.root, instance.stage_id)), bytes_of(ticket_file_of(instance.root)))
    data, items = cases.fingerprint(instance.root), restore_items(instance.root)
    reason = make_state_unreadable(monkeypatch, modes, instance.root, how)
    returned, raised = answer_of(lambda: apply.cancel_restore(data_dir=instance.root, drop_copy=True))
    modes.put_back()
    assert_state_unreadable(apply, "cancel_restore", returned, raised, reason, instance.root)
    assert (bytes_of(state_file(instance.root)), tree(stage_dir(instance.root, instance.stage_id)), bytes_of(ticket_file_of(instance.root))) == kept, "the state file, the copy and the ticket byte for byte"
    assert (cases.fingerprint(instance.root), restore_items(instance.root)) == (data, items), "nothing else changed"
    print_success(f"{how}: not cancelled, restore_state_unreadable")


@pytest.mark.parametrize("how", UNREADABLE_STATES)
def test_a_restart_with_a_state_that_cannot_be_read_issues_no_ticket(tmp_path, databases, checked, monkeypatch, modes, how):
    """(o) B-32 §3 (s4) ``prepare_restart``, the restart's first step, while the state cannot be read: raises
    ``RestoreStateUnreadableError``; no ticket written, nothing changed. Red before B-32: ``restore_not_pending``."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    confirm(apply, instance)
    assert not lexists(ticket_file_of(instance.root)), "precondition: no ticket yet"
    data, items = cases.fingerprint(instance.root), restore_items(instance.root)
    reason = make_state_unreadable(monkeypatch, modes, instance.root, how)
    returned, raised = answer_of(lambda: apply.prepare_restart(data_dir=instance.root))
    modes.put_back()
    assert_state_unreadable(apply, "prepare_restart", returned, raised, reason, instance.root)
    assert not lexists(ticket_file_of(instance.root)), "no ticket written"
    assert (cases.fingerprint(instance.root), restore_items(instance.root)) == (data, items), "nothing changed"
    print_success(f"{how}: no ticket, restore_state_unreadable")


@pytest.mark.parametrize("how", UNREADABLE_STATES)
def test_a_confirmation_never_writes_over_a_state_it_cannot_read(tmp_path, databases, checked, monkeypatch, modes, how):
    """(o) B-32 §3 (s5) Another checked copy confirmed while the state cannot be read: the restore found there is
    unknown, maybe half applied, and its journal must not be written over. ``confirm_restore`` raises
    ``RestoreStateUnreadableError``; the state file byte for byte, nothing removed or written. Red before B-32: the
    confirmation goes on, and replaces the state."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    confirm(apply, instance)
    add_stage(instance, checked, OTHER_STAGE)
    state = bytes_of(state_file(instance.root))
    data, items = cases.fingerprint(instance.root), restore_items(instance.root)
    reason = make_state_unreadable(monkeypatch, modes, instance.root, how)
    returned, raised = answer_of(lambda: confirm(apply, instance, OTHER_STAGE))
    modes.put_back()
    assert_state_unreadable(apply, "confirm_restore", returned, raised, reason, instance.root)
    assert bytes_of(state_file(instance.root)) == state, "the state file byte for byte: never written over"
    assert (cases.fingerprint(instance.root), restore_items(instance.root)) == (data, items), "nothing removed or written"
    print_success(f"{how}: not confirmed, restore_state_unreadable")


@pytest.mark.parametrize("how", UNREADABLE_STATES)
@pytest.mark.parametrize("caller", LENIENT)
def test_the_startup_steps_read_a_state_they_cannot_read_as_none(tmp_path, databases, checked, monkeypatch, modes, caller, how):
    """(o) B-32 §3 (s6) A guard, green before B-32 too: lenient, the startup steps go on with the data as it is —
    ``apply_pending_restore`` and ``finish_pending_restore`` give ``None``, nothing moved, written or removed; an error
    logged by the reader. B-33 left them so (§1); ``protected_stage`` is no longer lenient (r)."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    confirm(apply, instance)
    data, items = cases.fingerprint(instance.root), restore_items(instance.root)
    make_state_unreadable(monkeypatch, modes, instance.root, how)
    calls = {
        "apply_pending_restore": lambda: apply.apply_pending_restore(instance.root, boot=never_ran(apply), now=instance.applied_at),
        "finish_pending_restore": lambda: apply.finish_pending_restore(instance.root, boot=never_ran(apply), now=instance.committed_at),
    }
    with moving(apply) as mover, logs() as events:
        returned, raised = answer_of(calls[caller])
    modes.put_back()
    assert (returned, raised) == (None, None), f"{caller}: None, nothing raised: {returned!r}, {raised!r}"
    assert mover.calls == 0, f"{caller}: nothing moved: {mover.moved}"
    assert an_error(events), f"{caller}: an error logged: {logged(events)}"
    assert (cases.fingerprint(instance.root), restore_items(instance.root)) == (data, items), f"{caller}: nothing written or removed"
    print_success(f"{caller}, {how}: None, an error logged")


# =============================================================================
# (r) B-33: a state that cannot be read — its reason, the copies kept, the recovery
# =============================================================================
#
# B-33 §1: ``None`` only without a state file; a state file that cannot be read for any reason is
# ``RestoreStateUnreadableError`` with ``reason`` ``io`` (the file system refused it), ``not_a_file`` (a folder, a link,
# a FIFO) or ``invalid`` (not JSON, wrong fields, a ``format`` other than 1). §2: ``protected_stage`` is then
# ``EVERY_STAGE``. §3: ``recover_unreadable_restore`` puts the data of before back from what the files say.

#: (r) B-33 §1: the reasons of a state that cannot be read.
B33_REASONS = ("io", "not_a_file", "invalid")
#: (r) B-33 §2: what ``protected_stage`` answers while the state cannot be read; no stage id can equal it.
EVERY_STAGE_VALUE = "*"
#: (r) Bytes a state that cannot be read holds: never a state, never shown.
STATE_MARK = b"b33-the-content-of-a-state-nobody-can-read"
#: (r) Seconds a call is given: a reader waiting on a FIFO never ends by itself (it is let go after).
B33_DEADLINE_S = 20
#: (r) The moment a hand-written state of (r) was confirmed.
B33_CONFIRMED_AT = datetime(2026, 10, 15, 22, 0, tzinfo=UTC)
#: (r) What a recovery renames the state file into: ``restore.json.unreadable-<YYYYMMDDTHHMMSSZ>`` (§3).
KEPT_AS = re.compile(r"restore\.json\.unreadable-(\d{8}T\d{6}Z)")
#: (r) The folders of a data directory a restore stopped half way: the restored data live, the data of before in
#: ``previous/``, each folder its own files.
RESTORED_FILES = {name: {"restored.bin": f"the restored {name}\n".encode()} for name in SWAPPED}
BEFORE_FILES = {name: {"before.bin": f"the {name} of before\n".encode(), "deeper/kept.txt": b"kept\n"} for name in SWAPPED}


def b33_name(module: Any, name: str) -> Any:
    """``module.<name>``, a name B-33 adds, read when the test needs it: its absence fails that test alone."""
    value = getattr(module, name, None)
    if value is None:
        pytest.fail(f"[new] B-33: {module.__name__}.{name} does not exist yet (interface §1-§3)", pytrace=False)
    return value


def bare_restore(apply: Any, root: Path, status: str = "pending", **fields: Any) -> bytes:
    """A data directory without databases: what a restore never touches; ``.restore`` (0700) with its apply lock and the
    state of a restore in ``status``, written as ``apply`` writes it (any field replaced by ``fields``). Its bytes."""
    cases.write_files(root, UNTOUCHED)
    restore_dir(root).mkdir(mode=0o700)
    apply_lock_of(root).touch(mode=0o600)
    state = apply.RestoreState(
        status=status,
        stage_id=cases.VALID_ID,
        data_dir=str(root.resolve()),
        confirmed_at=B33_CONFIRMED_AT,
        confirmed_by=CONFIRMED_BY,
        backup_created_at=B33_CONFIRMED_AT - timedelta(days=1),
        backup_app_version="v1.2.0",
        action="same",
        **fields,
    )
    state_file(root).write_text(state.model_dump_json(indent=2) + "\n", encoding="utf-8")
    state_file(root).chmod(0o600)
    return state_file(root).read_bytes()


def journal_of(apply: Any) -> dict[str, Any]:
    """The journal and the boot of a restore a start applied: every folder live and restored."""
    return {"swap": [apply.SwapEntry(name=name, live=True, staged=True) for name in SWAPPED], "boot": never_ran(apply)}


def _refused_eio(root: Path, elsewhere: Path, patch: pytest.MonkeyPatch) -> None:
    make_state_unreadable(patch, None, root, "EIO")  # type: ignore[arg-type]  # no mode is changed for EIO


def _a_folder(root: Path, elsewhere: Path, patch: pytest.MonkeyPatch) -> None:
    state_file(root).unlink()
    state_file(root).mkdir(mode=0o700)
    (state_file(root) / "inside.json").write_bytes(STATE_MARK)


def _a_link(root: Path, elsewhere: Path, patch: pytest.MonkeyPatch) -> None:
    shutil.move(state_file(root), elsewhere / STATE_FILE_NAME)
    state_file(root).symlink_to(elsewhere / STATE_FILE_NAME)


def _a_fifo(root: Path, elsewhere: Path, patch: pytest.MonkeyPatch) -> None:
    state_file(root).unlink()
    os.mkfifo(state_file(root), 0o600)


def _not_json(root: Path, elsewhere: Path, patch: pytest.MonkeyPatch) -> None:
    state_file(root).write_bytes(b"{" + STATE_MARK)


def _fields_missing(root: Path, elsewhere: Path, patch: pytest.MonkeyPatch) -> None:
    state_file(root).write_text(json.dumps({"format": 1, "status": "pending", "note": STATE_MARK.decode()}), encoding="utf-8")


def _format_2(root: Path, elsewhere: Path, patch: pytest.MonkeyPatch) -> None:
    record = json.loads(state_file(root).read_text(encoding="utf-8"))
    state_file(root).write_text(json.dumps({**record, "format": 2}), encoding="utf-8")


#: (r) B-33 §1: a state file that cannot be read, each way, with its reason.
NOT_A_FILE_OR_INVALID = [
    pytest.param("not_a_file", _a_folder, id="not_a_file-a-folder"),
    pytest.param("not_a_file", _a_link, id="not_a_file-a-link"),
    pytest.param("not_a_file", _a_fifo, id="not_a_file-a-fifo"),
    pytest.param("invalid", _not_json, id="invalid-not-json"),
    pytest.param("invalid", _fields_missing, id="invalid-fields-missing"),
    pytest.param("invalid", _format_2, id="invalid-format-2"),
]
B33_UNREADABLE = [pytest.param("io", _refused_eio, id="io-EIO"), *NOT_A_FILE_OR_INVALID]
#: (r) One way for each reason: the recovery's cases.
ONE_OF_EACH = [pytest.param("io", _refused_eio, id="io-EIO"), pytest.param("not_a_file", _a_folder, id="not_a_file-a-folder"), pytest.param("invalid", _not_json, id="invalid-not-json")]


def on_disk(root: Path) -> dict[str, tuple]:
    """Every path below ``root``, ``.restore`` included, never through a link and never read from a FIFO: a folder with
    its mode, a link with its target, a file with its mode, size and SHA-256, anything else with its kind and mode."""
    found: dict[str, tuple] = {}
    for folder, names, files in os.walk(root):
        for name in [*names, *files]:
            path = Path(folder) / name
            info = path.lstat()
            relative = path.relative_to(root).as_posix()
            if stat.S_ISLNK(info.st_mode):
                found[relative] = ("link", os.readlink(path))
            elif stat.S_ISDIR(info.st_mode):
                found[relative] = ("folder", stat.S_IMODE(info.st_mode))
            elif stat.S_ISREG(info.st_mode):
                found[relative] = ("file", stat.S_IMODE(info.st_mode), info.st_size, cases.sha256(path.read_bytes()))
            else:
                found[relative] = ("special", stat.S_IFMT(info.st_mode), stat.S_IMODE(info.st_mode))
    return dict(sorted(found.items()))


def in_time(call: Callable[[], Any], root: Path) -> tuple[bool, Any, Exception | None]:
    """``call`` in a thread of its own, given ``B33_DEADLINE_S``: whether it ended in time, what it returned, what it
    raised. A reader left waiting on a FIFO at the state's place is let go before this returns (a writer opened without
    waiting, closed at once), so that a red run never hangs the suite."""
    ended: dict[str, Any] = {}

    def run() -> None:
        try:
            ended["value"] = call()
        except Exception as exc:
            ended["raised"] = exc

    thread = threading.Thread(target=run, name="b33-state-reader", daemon=True)
    thread.start()
    thread.join(B33_DEADLINE_S)
    timely = not thread.is_alive()
    deadline = time.monotonic() + B33_DEADLINE_S
    while thread.is_alive() and time.monotonic() < deadline:
        try:
            os.close(os.open(state_file(root), os.O_WRONLY | os.O_NONBLOCK))
        except OSError:
            pass
        thread.join(0.05)
    return timely, ended.get("value"), ended.get("raised")


def errors_in(events: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """The errors (and worse) logged in the block, (level, message)."""
    return [(level, message) for level, message in logged(events) if level in ("error", "critical")]


def test_b33_names_every_stage_the_two_errors_and_the_recovery():
    """(r) B-33: ``EVERY_STAGE`` is ``"*"``, which no stage id can be; ``RestoreNothingToRecoverError`` a
    ``RestoreStateError`` with the code ``restore_nothing_to_recover``; ``RecoveredRestore`` a frozen dataclass of
    ``moved_back``, ``set_aside`` and ``state_kept_as``; ``restore_state_problem`` and ``recover_unreadable_restore`` take
    ``data_dir``, ``None`` by default (the configured data directory)."""
    print_section("(r) B-33: a state that cannot be read")
    apply = apply_module()
    assert (b33_name(apply, "EVERY_STAGE"), paths.is_job_id(EVERY_STAGE_VALUE)) == (EVERY_STAGE_VALUE, False), f"EVERY_STAGE is {EVERY_STAGE_VALUE!r}, no stage id: {apply.EVERY_STAGE!r}"
    nothing = b33_name(apply, "RestoreNothingToRecoverError")
    assert issubclass(nothing, apply.RestoreStateError) and nothing.code == "restore_nothing_to_recover", f"a RestoreStateError, restore_nothing_to_recover: {nothing.__mro__}, {getattr(nothing, 'code', None)}"
    recovered = b33_name(apply, "RecoveredRestore")
    assert dataclasses.is_dataclass(recovered) and recovered.__dataclass_params__.frozen, f"RecoveredRestore: a frozen dataclass: {recovered}"
    assert [item.name for item in dataclasses.fields(recovered)] == ["moved_back", "set_aside", "state_kept_as"], f"its fields: {dataclasses.fields(recovered)}"
    for name in ("restore_state_problem", "recover_unreadable_restore"):
        parameter = inspect.signature(b33_name(apply, name)).parameters.get("data_dir")
        assert parameter is not None and parameter.default is None, f"{name}(data_dir=None): {inspect.signature(getattr(apply, name))}"
    print_success("EVERY_STAGE, RestoreNothingToRecoverError, RecoveredRestore, the two functions")


@pytest.mark.parametrize(("reason", "make"), B33_UNREADABLE)
def test_read_restore_raises_unreadable_with_its_reason_never_waiting_on_it(tmp_path, reason, make):
    """(r) B-33 §1: a state file the file system refuses (``io``), that is a folder, a link or a FIFO (``not_a_file``),
    or not a state this LibreFolio reads (``invalid``): ``read_restore`` raises ``RestoreStateUnreadableError`` with that
    reason, the contract's message, no path; one error logged; within the deadline (a FIFO is never waited on); nothing
    created or changed. Red before B-33 but for ``io``: ``None``, as if no restore were there."""
    apply = apply_module()
    root, elsewhere = tmp_path / "data", tmp_path / "elsewhere"
    elsewhere.mkdir()
    bare_restore(apply, root)
    with pytest.MonkeyPatch.context() as patch:
        make(root, elsewhere, patch)
        before = (on_disk(root), on_disk(elsewhere))
        with logs() as events:
            timely, returned, raised = in_time(lambda: apply.read_restore(root), root)
    assert timely, f"{reason}: read_restore returns within {B33_DEADLINE_S} s: it waited on the state"
    assert_unreadable_for(apply, "read_restore", returned, raised, reason, root)
    assert len(errors_in(events)) == 1, f"{reason}: logged once, as an error: {logged(events)}"
    assert (on_disk(root), on_disk(elsewhere)) == before, f"{reason}: nothing created or changed"
    print_success(f"{make.__name__}: restore_state_unreadable ({reason})")


def _no_restore_folder(root: Path) -> None:
    shutil.rmtree(restore_dir(root))


def _no_state_file(root: Path) -> None:
    state_file(root).unlink()


def _restore_folder_a_file_b33(root: Path) -> None:
    shutil.rmtree(restore_dir(root))
    restore_dir(root).write_bytes(STATE_MARK)


def _restore_folder_a_link_b33(root: Path) -> None:
    # A link to a folder holding a state no restore can hold: never followed, so never read.
    target = root.parent / "linked-restore-folder"
    target.mkdir()
    (target / STATE_FILE_NAME).write_bytes(b"{" + STATE_MARK)
    shutil.rmtree(restore_dir(root))
    restore_dir(root).symlink_to(target, target_is_directory=True)


@pytest.mark.parametrize("make", [_no_restore_folder, _no_state_file, _restore_folder_a_file_b33, _restore_folder_a_link_b33], ids=["no-restore-folder", "no-state-file", "restore-folder-a-file", "restore-folder-a-link"])
def test_without_a_state_file_to_read_there_is_no_restore_and_no_problem(tmp_path, make):
    """(r) B-33 §1: ``None`` only when there is no state file — no ``.restore``, no ``restore.json`` — or, as before, a
    ``.restore`` that is a file or a link (ignored, never followed). ``read_restore``, ``protected_stage`` and
    ``restore_state_problem`` all ``None``, nothing raised, nothing created."""
    apply = apply_module()
    root = tmp_path / "data"
    bare_restore(apply, root)
    make(root)
    problem = b33_name(apply, "restore_state_problem")
    before = on_disk(root)
    found = (answer_of(lambda: apply.read_restore(root)), answer_of(lambda: apply.protected_stage(root)), answer_of(lambda: problem(root)))
    assert found == ((None, None), (None, None), (None, None)), f"{make.__name__}: no restore, no stage protected, no problem: {found}"
    assert on_disk(root) == before, f"{make.__name__}: nothing created"
    print_success(f"{make.__name__}: None, None, None")


def test_restore_state_problem_without_arguments_reads_the_configured_data_directory(configured_data_dir):
    """(r) B-33 §1: ``restore_state_problem()`` reads the configured data directory (here a folder that must stay absent):
    ``None``, nothing created."""
    problem = b33_name(apply_module(), "restore_state_problem")
    assert answer_of(problem) == (None, None), "the configured data directory has no restore: None"
    assert not configured_data_dir.exists(), "nothing created in the configured data directory"
    print_success("restore_state_problem(): None")


@pytest.mark.parametrize(("reason", "make"), B33_UNREADABLE)
def test_restore_state_problem_is_the_error_a_read_would_raise_and_never_raises(tmp_path, reason, make):
    """(r) B-33 §1, the hook for H-62: ``restore_state_problem(data_dir)`` returns the ``RestoreStateUnreadableError`` a
    read would raise, with its reason, never raising it; within the deadline; nothing changed."""
    apply = apply_module()
    problem = b33_name(apply, "restore_state_problem")
    root, elsewhere = tmp_path / "data", tmp_path / "elsewhere"
    elsewhere.mkdir()
    bare_restore(apply, root)
    with pytest.MonkeyPatch.context() as patch:
        make(root, elsewhere, patch)
        before = on_disk(root)
        timely, returned, raised = in_time(lambda: problem(root), root)
    assert timely, f"{reason}: restore_state_problem returns within {B33_DEADLINE_S} s"
    assert raised is None, f"{reason}: restore_state_problem never raises: {raised!r}"
    assert isinstance(returned, apply.RestoreStateUnreadableError) and getattr(returned, "reason", None) == reason, f"{reason}: the error a read would raise, returned: {returned!r}"
    assert on_disk(root) == before, f"{reason}: nothing changed"
    print_success(f"{make.__name__}: returned ({reason})")


@pytest.mark.parametrize("phase", [*ACTIVE_PHASES, *TERMINAL_PHASES])
def test_restore_state_problem_of_a_readable_state_is_none(tmp_path, phase):
    """(r) B-33 §1: a state this LibreFolio reads, in any phase: no problem, ``None``."""
    apply = apply_module()
    problem = b33_name(apply, "restore_state_problem")
    root = tmp_path / "data"
    bare_restore(apply, root, phase, **(journal_of(apply) if phase in ("applying", "applied", "rolling_back") else {}))
    assert answer_of(lambda: problem(root)) == (None, None), f"{phase}: a readable state, no problem"
    print_success(f"{phase}: None")


@pytest.mark.parametrize(("reason", "make"), B33_UNREADABLE)
def test_protected_stage_is_every_stage_while_the_state_cannot_be_read(tmp_path, reason, make):
    """(r) B-33 §2: which copy a restore waits for is unknown, so no copy is touched: ``protected_stage`` is
    ``EVERY_STAGE``, for each reason, within the deadline, nothing raised. Red before B-33: ``None``."""
    apply = apply_module()
    root, elsewhere = tmp_path / "data", tmp_path / "elsewhere"
    elsewhere.mkdir()
    bare_restore(apply, root)
    with pytest.MonkeyPatch.context() as patch:
        make(root, elsewhere, patch)
        timely, returned, raised = in_time(lambda: apply.protected_stage(root), root)
    assert timely and raised is None, f"{reason}: protected_stage answers in time, never raises: {raised!r}"
    assert returned == EVERY_STAGE_VALUE, f"[new] B-33 §2: {reason}: every stage protected ({EVERY_STAGE_VALUE!r}), not {returned!r}"
    print_success(f"{make.__name__}: EVERY_STAGE")


@pytest.mark.parametrize("step", ["apply_pending_restore", "finish_pending_restore"])
@pytest.mark.parametrize(("reason", "make"), B33_UNREADABLE)
def test_the_startup_steps_go_on_beside_a_state_that_cannot_be_read(tmp_path, reason, make, step):
    """(r) B-33 §1, a guard: ``_state_at_start`` unchanged for every reason — the step logs an error and gives ``None``,
    the start goes on; nothing moved, written or removed; within the deadline (H-62 adds the block)."""
    apply = apply_module()
    root, elsewhere = tmp_path / "data", tmp_path / "elsewhere"
    elsewhere.mkdir()
    bare_restore(apply, root)
    calls = {
        "apply_pending_restore": lambda: apply.apply_pending_restore(root, boot=never_ran(apply), now=B33_CONFIRMED_AT),
        "finish_pending_restore": lambda: apply.finish_pending_restore(root, boot=never_ran(apply), now=B33_CONFIRMED_AT),
    }
    with pytest.MonkeyPatch.context() as patch:
        make(root, elsewhere, patch)
        before = on_disk(root)
        with moving(apply) as mover, logs() as events:
            timely, returned, raised = in_time(calls[step], root)
    assert timely and (returned, raised) == (None, None), f"{step}, {reason}: None in time, nothing raised: {timely}, {returned!r}, {raised!r}"
    assert mover.calls == 0, f"{step}: nothing moved: {mover.moved}"
    assert errors_in(events), f"{step}, {reason}: an error logged: {logged(events)}"
    assert on_disk(root) == before, f"{step}, {reason}: nothing written or removed"
    print_success(f"{step}, {make.__name__}: None, logged")


@pytest.mark.parametrize(("reason", "make"), NOT_A_FILE_OR_INVALID)
def test_a_confirmation_never_writes_over_a_state_that_is_not_a_file_or_not_valid(tmp_path, databases, checked, reason, make):
    """(r) B-33 §1: another checked copy confirmed while the state is not a file or not valid: a restore may have stopped
    half way behind it. ``confirm_restore`` raises ``RestoreStateUnreadableError`` with that reason; nothing written over
    it, removed or created, within the deadline. Red before B-33: the confirmation went on and replaced the state."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    confirm(apply, instance)
    add_stage(instance, checked, OTHER_STAGE)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    with pytest.MonkeyPatch.context() as patch:
        make(instance.root, elsewhere, patch)
        before = (on_disk(instance.root), on_disk(elsewhere))
        timely, returned, raised = in_time(lambda: confirm(apply, instance, OTHER_STAGE), instance.root)
    assert timely, f"{reason}: the confirmation returns within {B33_DEADLINE_S} s"
    assert_unreadable_for(apply, "confirm_restore", returned, raised, reason, instance.root)
    assert (on_disk(instance.root), on_disk(elsewhere)) == before, f"{reason}: nothing written over the state, removed or created"
    print_success(f"{make.__name__}: not confirmed ({reason})")


@dataclass
class Halfway:
    """A data directory a restore stopped half way, its state then made unreadable: what each swapped folder held live
    (the restored data) and in ``previous/`` (the data of before), what the copy and the rest held, before the
    recovery."""

    root: Path
    live: dict[str, dict[str, tuple] | None]
    before: dict[str, dict[str, tuple] | None]
    copy: dict[str, tuple] | None
    rest: dict[str, tuple]


def halfway(apply: Any, root: Path, *, previous: tuple[str, ...] | None, live: tuple[str, ...] = SWAPPED) -> Halfway:
    """A restore applied, then stopped half way: ``live`` folders hold the restored data, ``previous/`` (absent with
    ``None``) the data of before of ``previous``; the copy it came from (``.restore/stage/<id>/``); the state, readable
    still (an ``applying`` journal)."""
    bare_restore(apply, root, "applying", **journal_of(apply))
    for name in live:
        cases.write_files(root / name, RESTORED_FILES[name])
    if previous is not None:
        previous_of(root).mkdir(mode=0o700)
        for name in previous:
            cases.write_files(previous_of(root) / name, BEFORE_FILES[name])
    cases.write_files(stage_dir(root, cases.VALID_ID), {"report.json": b"{}\n"})
    return Halfway(
        root=root,
        live={name: tree(root / name) for name in SWAPPED},
        before={name: tree(previous_of(root) / name) for name in SWAPPED},
        copy=tree(stage_dir(root, cases.VALID_ID)),
        rest=outside(cases.fingerprint(root)),
    )


def the_state(root: Path, name: str = STATE_FILE_NAME) -> dict[str, tuple]:
    """The state file of ``root``, under ``name``, as ``on_disk`` sees it (a folder with what it holds), keyed from it."""
    entries = on_disk(restore_dir(root))
    return {key.replace(name, "<state>", 1): value for key, value in entries.items() if key == name or key.startswith(f"{name}/")}


def recovered_in_time(apply: Any, root: Path) -> tuple[Any, Exception | None]:
    """``recover_unreadable_restore(root)`` within the deadline: what it returned, what it raised."""
    recover = b33_name(apply, "recover_unreadable_restore")
    timely, returned, raised = in_time(lambda: recover(root), root)
    assert timely, f"recover_unreadable_restore returns within {B33_DEADLINE_S} s"
    return returned, raised


def assert_recovered(apply: Any, world: Halfway, result: Any, raised: Exception | None, moved: set[str], state: dict[str, tuple], started: datetime, ended: datetime) -> None:
    """The recovery of ``world`` done: each folder of ``moved`` back from ``previous/`` (its live one, if any, in
    ``failed/``), every other one as it was; the state file renamed ``restore.json.unreadable-<UTC>``, kept as it was;
    nothing else touched; a ``RecoveredRestore`` saying so."""
    root = world.root
    assert raised is None, f"recover_unreadable_restore raised {type(raised).__name__}: {raised}"
    assert isinstance(result, b33_name(apply, "RecoveredRestore")), f"a RecoveredRestore: {result!r}"
    set_aside = {name for name in moved if world.live[name] is not None}
    assert (sorted(result.moved_back), sorted(result.set_aside)) == (sorted(moved), sorted(set_aside)), f"moved back {sorted(moved)}, set aside {sorted(set_aside)}: {result}"
    for name in SWAPPED:
        if name in moved:
            assert (tree(root / name), tree(previous_of(root) / name)) == (world.before[name], None), f"{name}: the data of before back in place, whole, out of previous/"
            assert tree(failed_of(root) / name) == world.live[name], f"{name}: the live (restored) folder in failed/, whole{'' if world.live[name] else ': none was live'}"
        else:
            assert tree(root / name) == world.live[name], f"{name}: not in previous/, left as it was"
            assert not lexists(failed_of(root) / name), f"{name}: nothing set aside"
    kept = KEPT_AS.fullmatch(str(result.state_kept_as))
    assert kept is not None, f"the state kept as restore.json.unreadable-<YYYYMMDDTHHMMSSZ>: {result.state_kept_as!r}"
    at = datetime.strptime(kept.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
    assert started.replace(microsecond=0) <= at <= ended, f"its time, UTC, the recovery's: {at} not in [{started}, {ended}]"
    assert not lexists(state_file(root)), "no state file left: no new state written"
    assert the_state(root, result.state_kept_as) == state, "the state file renamed, kept as it was (never read again)"
    assert (tree(stage_dir(root, cases.VALID_ID)), outside(cases.fingerprint(root))) == (world.copy, world.rest), "the copy and everything outside the swapped folders untouched"


@pytest.mark.parametrize(("reason", "make"), ONE_OF_EACH)
def test_recover_puts_the_data_of_before_back_and_sets_the_state_aside(tmp_path, reason, make):
    """(r) B-33 §3 (a): ``previous/`` holds two of the swapped folders, every live one present: those two go live again
    from ``previous/``, their live (restored) ones to ``failed/``; the two others stay as they are. The state renamed
    ``restore.json.unreadable-<UTC>``; then ``read_restore`` is ``None`` and ``restore_state_problem`` too."""
    apply = apply_module()
    root, elsewhere = tmp_path / "data", tmp_path / "elsewhere"
    elsewhere.mkdir()
    world = halfway(apply, root, previous=("sqlite", "custom-uploads"))
    with pytest.MonkeyPatch.context() as patch:
        make(root, elsewhere, patch)
        state = the_state(root)
        started = datetime.now(UTC)
        result, raised = recovered_in_time(apply, root)
        ended = datetime.now(UTC)
    assert_recovered(apply, world, result, raised, {"sqlite", "custom-uploads"}, state, started, ended)
    assert (answer_of(lambda: apply.read_restore(root)), answer_of(lambda: apply.restore_state_problem(root))) == ((None, None), (None, None)), "no restore left, no problem"
    print_success(f"{make.__name__}: two folders back, two set aside, the state kept as {result.state_kept_as}")


def test_recover_after_a_swap_cut_moves_back_a_folder_whose_live_one_is_missing(tmp_path):
    """(r) B-33 §3 (b): the swap cut after a live folder went to ``previous/`` and before its restored one came in: it
    moves back, nothing goes to ``failed/``; the other folders stay."""
    apply = apply_module()
    root, elsewhere = tmp_path / "data", tmp_path / "elsewhere"
    elsewhere.mkdir()
    world = halfway(apply, root, previous=("broker_reports",), live=tuple(name for name in SWAPPED if name != "broker_reports"))
    with pytest.MonkeyPatch.context() as patch:
        _not_json(root, elsewhere, patch)
        state = the_state(root)
        started = datetime.now(UTC)
        result, raised = recovered_in_time(apply, root)
        ended = datetime.now(UTC)
    assert_recovered(apply, world, result, raised, {"broker_reports"}, state, started, ended)
    assert not tree(failed_of(root)), f"nothing set aside: {tree(failed_of(root))}"
    print_success("broker_reports back, nothing set aside")


def test_recover_without_previous_moves_nothing_and_sets_the_state_aside(tmp_path):
    """(r) B-33 §3 (c): no ``previous/``: nothing to put back, every live folder as it was; the state set aside all the
    same, so that nothing waits any more."""
    apply = apply_module()
    root, elsewhere = tmp_path / "data", tmp_path / "elsewhere"
    elsewhere.mkdir()
    world = halfway(apply, root, previous=None)
    with pytest.MonkeyPatch.context() as patch:
        _not_json(root, elsewhere, patch)
        state = the_state(root)
        started = datetime.now(UTC)
        result, raised = recovered_in_time(apply, root)
        ended = datetime.now(UTC)
    assert_recovered(apply, world, result, raised, set(), state, started, ended)
    assert not lexists(failed_of(root)), "no failed/ made"
    print_success("nothing moved, the state set aside")


def _nothing_to_recover_no_state(apply: Any, root: Path) -> None:
    halfway(apply, root, previous=("sqlite",))
    state_file(root).unlink()


def _nothing_to_recover_pending(apply: Any, root: Path) -> None:
    halfway(apply, root, previous=None)
    bare_state = apply.RestoreState.model_validate_json(state_file(root).read_bytes()).model_copy(update={"status": "pending", "swap": [], "boot": None})
    state_file(root).write_text(bare_state.model_dump_json(), encoding="utf-8")


def _nothing_to_recover_applied(apply: Any, root: Path) -> None:
    halfway(apply, root, previous=("sqlite", "custom-uploads"))
    applied = apply.RestoreState.model_validate_json(state_file(root).read_bytes()).model_copy(update={"status": "applied", "applied_at": B33_CONFIRMED_AT})
    state_file(root).write_text(applied.model_dump_json(), encoding="utf-8")


@pytest.mark.parametrize("arrange", [_nothing_to_recover_no_state, _nothing_to_recover_pending, _nothing_to_recover_applied], ids=["no-state-previous-there", "readable-pending", "readable-applied-previous-there"])
def test_recover_with_a_readable_state_or_none_has_nothing_to_recover_and_moves_nothing(tmp_path, arrange):
    """(r) B-33 §3 (d): a readable state (a restore waiting; one applied, ``previous/`` holding the data of before) or no
    state at all (``previous/`` there all the same): ``RestoreNothingToRecoverError`` (``restore_nothing_to_recover``, a
    ``RestoreStateError``); nothing moved, written or removed."""
    apply = apply_module()
    root = tmp_path / "data"
    arrange(apply, root)
    before = on_disk(root)
    result, raised = recovered_in_time(apply, root)
    nothing = b33_name(apply, "RestoreNothingToRecoverError")
    assert isinstance(raised, nothing) and isinstance(raised, apply.RestoreStateError) and raised.code == "restore_nothing_to_recover", f"{arrange.__name__}: restore_nothing_to_recover, not {result!r} / {raised!r}"
    assert on_disk(root) == before, f"{arrange.__name__}: nothing moved, written or removed"
    print_success(f"{arrange.__name__}: restore_nothing_to_recover")


def test_recover_while_a_server_serves_the_data_directory_is_refused_and_moves_nothing(tmp_path, serving_here):
    """(r) B-33 §3 (e): a server holds the serving lock (here this process, through its own descriptor, as
    ``hold_serving_lock`` holds it): the recovery cannot take it exclusively, ``RestoreInUseError``
    (``restore_in_use``); nothing moved, written or removed, the state left where it is."""
    apply = serving_here
    root, elsewhere = tmp_path / "data", tmp_path / "elsewhere"
    elsewhere.mkdir()
    halfway(apply, root, previous=("sqlite", "custom-uploads"))
    with pytest.MonkeyPatch.context() as patch:
        _not_json(root, elsewhere, patch)
        assert apply.hold_serving_lock(root) is True, "precondition: a server serves the data directory"
        before = on_disk(root)
        result, raised = recovered_in_time(apply, root)
    assert isinstance(raised, apply.RestoreInUseError), f"restore_in_use while a server serves the data directory, not {result!r} / {raised!r}"
    assert on_disk(root) == before, "nothing moved, written or removed"
    print_success("restore_in_use, nothing moved")


def test_a_second_recovery_finds_nothing_to_recover_and_changes_nothing(tmp_path):
    """(r) B-33 §3 (f): idempotent outcome. Once recovered, a second call finds no state that cannot be read:
    ``RestoreNothingToRecoverError``, nothing changed since the first."""
    apply = apply_module()
    root, elsewhere = tmp_path / "data", tmp_path / "elsewhere"
    elsewhere.mkdir()
    halfway(apply, root, previous=("sqlite", "custom-uploads"))
    with pytest.MonkeyPatch.context() as patch:
        _not_json(root, elsewhere, patch)
    first, raised = recovered_in_time(apply, root)
    assert raised is None, f"precondition: the first recovery is done: {raised!r}"
    after_first = on_disk(root)
    again, raised = recovered_in_time(apply, root)
    assert isinstance(raised, b33_name(apply, "RestoreNothingToRecoverError")), f"nothing to recover the second time, not {again!r} / {raised!r}"
    assert on_disk(root) == after_first, "nothing changed by the second call"
    print_success("second call: restore_nothing_to_recover")


# =============================================================================
# (g) §2 apply_pending_restore: the swap
# =============================================================================


@pytest.mark.parametrize("layout", LAYOUTS)
def test_a_pending_restore_swaps_the_four_folders_and_keeps_the_ones_it_replaces(tmp_path, databases, checked, layout):
    """(g) Every combination of a live folder and a restored one: the restored data live, each folder with the mode of
    the one it replaces; the replaced data in ``previous/``; nothing else of the data directory touched; ``applied``
    with its journal and its boot, a warning logged."""
    print_section("(g) apply_pending_restore")
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked, layout)
    confirmed = confirm(apply, instance)
    boot = never_ran(apply)
    with moving(apply) as mover, logs() as events:
        state = apply.apply_pending_restore(instance.root, boot=boot, now=instance.applied_at)
    assert_swapped(instance)
    swap = [apply.SwapEntry(name=name, live=layout[name][0], staged=layout[name][1]) for name in SWAPPED]
    found = (state.status, state.swap, state.boot, state.applied_at, state.waiting, state.reason, state.finished_at)
    assert found == ("applied", swap, boot, instance.applied_at, None, None, None), f"applied, the journal of what existed, the boot: {found}"
    assert (state.stage_id, state.confirmed_at, state.data_dir) == (confirmed.stage_id, confirmed.confirmed_at, confirmed.data_dir), "the confirmation is kept"
    assert apply.read_restore(instance.root) == state, "the state on disk is the state returned"
    assert len(mover.moved) == instance.renames, f"one rename per live folder set aside and per restored folder moved in: {len(mover.moved)}, not {instance.renames}"
    assert a_warning(events), f"a restore applied is logged as a warning: {levels(events)}"
    print_success(f"{instance.renames} renames, applied")


def test_the_journal_is_on_disk_before_the_first_rename(tmp_path, databases, checked):
    """(g) Step 6: a start killed at the first rename finds what existed, and whose start it was."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked, MIXED)
    confirm(apply, instance)
    seen: dict[str, Any] = {}

    def read_the_journal() -> None:
        seen["journal"] = json.loads(state_file(instance.root).read_text(encoding="utf-8"))

    boot = never_ran(apply)
    with moving(apply, on_first=read_the_journal):
        apply.apply_pending_restore(instance.root, boot=boot, now=instance.applied_at)
    journal = seen.get("journal")
    assert journal is not None, "no rename went through apply._move"
    assert journal["status"] == "applying", f"applying before the first rename: {journal['status']}"
    assert journal["swap"] == [{"name": name, "live": MIXED[name][0], "staged": MIXED[name][1]} for name in SWAPPED], f"one entry per folder, in order: {journal['swap']}"
    assert journal["boot"] == boot.model_dump(mode="json"), f"the boot of this start: {journal['boot']}"
    print_success("applying, swap and boot on disk before the first rename")


def test_a_restore_this_boot_applied_is_left_as_it_is(tmp_path, databases, checked):
    """(g) The second worker of a server, or a step run twice: nothing more."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    confirm(apply, instance)
    applied = apply.apply_pending_restore(instance.root, boot=never_ran(apply), now=instance.applied_at)
    snapshot = (cases.fingerprint(instance.root), restore_items(instance.root))
    with moving(apply) as mover:
        again = apply.apply_pending_restore(instance.root, boot=never_ran(apply), now=instance.committed_at)
    assert (again, mover.calls) == (applied, 0), f"nothing moved, the state as it was: {again}"
    assert (cases.fingerprint(instance.root), restore_items(instance.root)) == snapshot, "nothing changed"
    print_success("same boot: nothing")


def test_a_restore_a_running_server_applied_stops_this_start_and_is_left_as_it_is(tmp_path, databases, checked):
    """(g) §10 Applied by another boot whose process runs (this process here): another server uses the data directory.
    This start stops (``RestoreInUseError``, ``restore_in_use``) rather than serve data whose restore is not committed:
    nothing written, moved or undone, the state as it was, an error logged, the apply lock released."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    confirm(apply, instance)
    applied = apply.apply_pending_restore(instance.root, boot=this_boot(apply), now=instance.applied_at)
    snapshot = (cases.fingerprint(instance.root), restore_items(instance.root))
    with moving(apply) as mover, logs() as events, pytest.raises(apply.RestoreInUseError) as raised:
        apply.apply_pending_restore(instance.root, boot=never_ran(apply), now=instance.committed_at)
    assert raised.value.code == "restore_in_use", raised.value.code
    assert mover.calls == 0, f"nothing moved or undone: {mover.moved}"
    assert (cases.fingerprint(instance.root), restore_items(instance.root)) == snapshot, "nothing written"
    assert apply.read_restore(instance.root) == applied, "the state as it was"
    assert an_error(events), f"another server on the data directory is logged as an error: {levels(events)}"
    assert apply_lock_free(instance.root), "the apply lock is released when the step stops"
    print_success("another live boot: restore_in_use, nothing done")


def test_boot_alive_is_looked_up_when_the_step_runs(tmp_path, databases, checked):
    """(g) ``apply.boot_alive``, a module attribute read at call time: told the first start still runs, the next one
    stops (``RestoreInUseError``) and leaves its restore as it is; with the real one, it undoes it."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    confirm(apply, instance)
    applied = apply.apply_pending_restore(instance.root, boot=never_ran(apply), now=instance.applied_at)
    snapshot = (cases.fingerprint(instance.root), restore_items(instance.root))
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(apply, "boot_alive", lambda boot: True)
        with moving(apply) as mover, logs() as events, pytest.raises(apply.RestoreInUseError):
            apply.apply_pending_restore(instance.root, boot=never_ran(apply, 1), now=instance.committed_at)
        assert mover.calls == 0, f"a boot said alive: nothing moved or undone: {mover.moved}"
    assert (cases.fingerprint(instance.root), restore_items(instance.root), apply.read_restore(instance.root)) == (*snapshot, applied), "nothing written, the state as it was"
    assert an_error(events), f"an error logged: {levels(events)}"
    state = apply.apply_pending_restore(instance.root, boot=never_ran(apply, 1), now=instance.committed_at)
    assert (state.status, state.reason) == ("rolled_back", "first_start_failed"), f"the real boot_alive: the first start never ran: {state.status}, {state.reason}"
    print_success("boot_alive read at call time")


DEAD_BOOTS = [pytest.param(never_ran, id="a-pid-no-process-has"), pytest.param(ended, id="a-process-that-ended"), pytest.param(reused_pid, id="a-reused-pid")]


@pytest.mark.parametrize("dead", DEAD_BOOTS)
def test_a_restore_whose_first_start_died_is_undone_and_the_old_data_put_back(tmp_path, databases, checked, dead):
    """(g) The first start after the swap died before its commit: the next start undoes the swap (decision 41). The old
    data back exactly; what stood in place of each live folder (the restored folder, with what the failed start wrote in
    it, or a folder it made) in ``failed/``; a restored folder that replaced none in ``failed/``; a folder the failed
    start made where neither existed left alone. ``first_start_failed``, an error logged."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked, MIXED)
    confirm(apply, instance)
    apply.apply_pending_restore(instance.root, boot=dead(apply), now=instance.applied_at)
    # What the failed start left: the database opened, the data folders made (data-directories), files written.
    (instance.root / "sqlite" / "app.db-wal").write_bytes(b"pages the failed start wrote")
    cases.write_files(instance.root, {"custom-uploads/.avatars_seeded": b"Seeded 0 avatars\n", "broker_reports/parsed/failed-start.csv": b"date,amount\n", "scenario_catalog/failed-start.json": b"{}\n"})
    standing = {name: tree(instance.root / name) for name in SWAPPED}
    with logs() as events:
        state = apply.apply_pending_restore(instance.root, boot=never_ran(apply, 1), now=instance.committed_at)
    assert (state.status, state.reason, state.finished_at) == ("rolled_back", "first_start_failed", instance.committed_at), f"{state.status}, {state.reason}, {state.finished_at}"
    assert an_error(events), f"a rollback is logged as an error: {levels(events)}"
    for name in SWAPPED:
        live, staged = MIXED[name]
        if live or staged:
            assert tree(failed_of(instance.root) / name) == standing[name], f"{name}: what stood there is set aside in failed/, whole"
        if live:
            assert (tree(instance.root / name), cases.mode(instance.root / name)) == (instance.live[name], LIVE_MODES[name]), f"{name}: the old data back exactly"
        elif staged:
            assert not lexists(instance.root / name), f"{name}: the restored folder, which replaced none, is gone"
        else:
            assert tree(instance.root / name) == standing[name] and not lexists(failed_of(instance.root) / name), f"{name}: a folder the failed start made where neither existed is left alone"
    assert outside(cases.fingerprint(instance.root)) == outside(instance.before), "nothing else touched"
    assert not tree(previous_of(instance.root)), "nothing left in previous/"
    print_success(f"{dead.__name__}: first_start_failed, the old data back")


@pytest.mark.parametrize("renames", range(9), ids=lambda renames: f"killed-after-{renames}-renames")
def test_a_swap_killed_after_any_of_its_renames_is_undone_at_the_next_start(tmp_path, databases, checked, renames):
    """(g) The journal is ``applying``; the next start undoes what was done, from the files: ``swap_interrupted``."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    assert instance.renames == 8, "precondition: a full swap is eight renames"
    confirm(apply, instance)
    killed(apply, instance, renames, boot=never_ran(apply), now=instance.applied_at)
    journal = apply.read_restore(instance.root)
    assert (journal.status, journal.boot, [entry.name for entry in journal.swap]) == ("applying", never_ran(apply), list(SWAPPED)), f"the kill left the journal: {journal}"
    with logs() as events:
        state = apply.apply_pending_restore(instance.root, boot=never_ran(apply, 1), now=instance.committed_at)
    assert (state.status, state.reason, state.finished_at) == ("rolled_back", "swap_interrupted", instance.committed_at), f"{state.status}, {state.reason}"
    assert an_error(events), f"a rollback is logged as an error: {levels(events)}"
    assert_put_back(instance)
    print_success(f"killed after {renames}: put back")


@pytest.mark.parametrize("renames", range(9), ids=lambda renames: f"killed-after-{renames}-renames")
def test_an_undo_killed_after_any_of_its_renames_is_finished_at_the_next_start(tmp_path, databases, checked, renames):
    """(g) The undo writes ``rolling_back`` first, then renames back (two per folder of a full swap); killed after any
    of them, the next start finishes it from the files."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    confirm(apply, instance)
    killed(apply, instance, instance.renames, boot=never_ran(apply), now=instance.applied_at)
    killed(apply, instance, renames, boot=never_ran(apply, 1), now=instance.committed_at)
    on_disk = apply.read_restore(instance.root)
    assert (on_disk.status, on_disk.reason) == ("rolling_back", "swap_interrupted"), f"the state is written rolling_back, with its reason, before the first rename back: {on_disk.status}, {on_disk.reason}"
    state = apply.apply_pending_restore(instance.root, boot=never_ran(apply, 2), now=instance.committed_at + timedelta(minutes=1))
    assert (state.status, state.reason) == ("rolled_back", "swap_interrupted"), f"{state.status}, {state.reason}"
    assert_put_back(instance)
    print_success(f"undo killed after {renames}: finished")


def test_an_undo_after_a_failed_first_start_keeps_its_reason_when_it_is_interrupted(tmp_path, databases, checked):
    """(g) ``rolling_back`` with a reason: the next start finishes the undo and keeps that reason."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    confirm(apply, instance)
    apply.apply_pending_restore(instance.root, boot=never_ran(apply), now=instance.applied_at)
    killed(apply, instance, 3, boot=never_ran(apply, 1), now=instance.committed_at)
    on_disk = apply.read_restore(instance.root)
    assert (on_disk.status, on_disk.reason) == ("rolling_back", "first_start_failed"), f"{on_disk.status}, {on_disk.reason}"
    state = apply.apply_pending_restore(instance.root, boot=never_ran(apply, 2), now=instance.committed_at)
    assert (state.status, state.reason) == ("rolled_back", "first_start_failed"), f"the reason given first is kept: {state.reason}"
    assert_put_back(instance)
    print_success("first_start_failed kept")


@pytest.mark.parametrize("failing", range(1, 9), ids=lambda failing: f"rename-{failing}-fails")
def test_a_rename_that_fails_during_the_swap_puts_the_data_back_at_once(tmp_path, databases, checked, failing):
    """(g) An ``OSError`` during the moves (a folder that is a mount point, a disk error): the undo at once,
    ``swap_failed``; the start goes on with the data as it was."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    confirm(apply, instance)
    with moving(apply, fail_at=frozenset({failing})), logs() as events:
        state = apply.apply_pending_restore(instance.root, boot=never_ran(apply), now=instance.applied_at)
    assert (state.status, state.reason, state.finished_at) == ("rolled_back", "swap_failed", instance.applied_at), f"{state.status}, {state.reason}"
    assert apply.read_restore(instance.root) == state, "the state on disk is the state returned"
    assert an_error(events), f"a rollback is logged as an error: {levels(events)}"
    assert_put_back(instance)
    print_success(f"rename {failing} fails: swap_failed, put back")


@pytest.mark.parametrize("failing", range(1, 9), ids=lambda failing: f"rename-back-{failing}-fails")
def test_a_rename_that_fails_during_an_undo_stops_the_start_and_the_next_start_finishes_it(tmp_path, databases, checked, failing):
    """(g) The data directory half restored: ``RestoreApplyError``, the startup stops, the state stays
    ``rolling_back``; the next start tries again."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    confirm(apply, instance)
    killed(apply, instance, instance.renames, boot=never_ran(apply), now=instance.applied_at)
    with moving(apply, fail_at=frozenset({failing})), pytest.raises(apply.RestoreApplyError) as raised:
        apply.apply_pending_restore(instance.root, boot=never_ran(apply, 1), now=instance.committed_at)
    assert raised.value.code == "restore_apply_failed", raised.value.code
    on_disk = apply.read_restore(instance.root)
    assert (on_disk.status, on_disk.reason) == ("rolling_back", "swap_interrupted"), f"{on_disk.status}, {on_disk.reason}"
    assert apply_lock_free(instance.root), "the apply lock is released when the step fails"
    state = apply.apply_pending_restore(instance.root, boot=never_ran(apply, 2), now=instance.committed_at)
    assert (state.status, state.reason) == ("rolled_back", "swap_interrupted"), f"{state.status}, {state.reason}"
    assert_put_back(instance)
    print_success(f"rename back {failing} fails: RestoreApplyError, then finished")


def test_a_swap_and_its_undo_that_both_fail_stay_rolling_back_with_the_first_reason(tmp_path, databases, checked):
    """(g) Rename 3 fails (``swap_failed``), then the undo's second rename (the database's back from ``previous/``):
    ``RestoreApplyError``, ``rolling_back`` with ``swap_failed``, kept when the next start finishes the undo."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    confirm(apply, instance)
    with moving(apply, fail_at=frozenset({3, 5})), pytest.raises(apply.RestoreApplyError):
        apply.apply_pending_restore(instance.root, boot=never_ran(apply), now=instance.applied_at)
    on_disk = apply.read_restore(instance.root)
    assert (on_disk.status, on_disk.reason) == ("rolling_back", "swap_failed"), f"{on_disk.status}, {on_disk.reason}"
    state = apply.apply_pending_restore(instance.root, boot=never_ran(apply, 1), now=instance.committed_at)
    assert (state.status, state.reason) == ("rolled_back", "swap_failed"), f"the reason given first is kept: {state.reason}"
    assert_put_back(instance)
    print_success("swap_failed kept through a failed undo")


# =============================================================================
# (g) §2 apply_pending_restore: waiting, refusing, two workers
# =============================================================================


def test_a_restore_confirmed_for_another_data_directory_waits_and_moves_nothing(tmp_path, databases, checked):
    """(g) Step 1: the data directory was moved, or another mounted with its ``.restore``: nothing moved, the state
    ``pending`` with ``waiting = other_data_directory``, a warning logged. Back where it was confirmed, it applies."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    confirmed = confirm(apply, instance)
    elsewhere = tmp_path / "mounted-elsewhere"
    instance.root.rename(elsewhere)
    before = cases.fingerprint(elsewhere)
    with moving(apply) as mover, logs() as events:
        state = apply.apply_pending_restore(elsewhere, boot=never_ran(apply), now=instance.applied_at)
    assert (state.status, state.waiting, state.data_dir) == ("pending", "other_data_directory", confirmed.data_dir), f"{state.status}, {state.waiting}, {state.data_dir}"
    assert apply.read_restore(elsewhere) == state, "the waiting is written"
    assert (mover.calls, cases.fingerprint(elsewhere)) == (0, before), "nothing moved"
    assert a_warning(events), f"a warning logged: {levels(events)}"
    elsewhere.rename(instance.root)
    state = apply.apply_pending_restore(instance.root, boot=never_ran(apply), now=instance.committed_at)
    assert (state.status, state.waiting) == ("applied", None), f"back in its data directory: applied, no longer waiting: {state.status}, {state.waiting}"
    assert_swapped(instance)
    print_success("other_data_directory: waits, then applies")


def test_a_restore_waits_while_a_backup_runs_and_moves_nothing(tmp_path, databases, checked):
    """(g) Step 2: a backup holds ``backups/.jobs/.lock`` (as ``jobs._lock_held`` probes it): nothing moved,
    ``waiting = backup_running``, an error logged. Once the backup ends, the next start applies."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    confirm(apply, instance)
    backup = jobs._RunLock(lock_path(instance.root))
    assert backup.try_acquire(), "precondition: the backup lock is free"
    try:
        with moving(apply) as mover, logs() as events:
            state = apply.apply_pending_restore(instance.root, boot=never_ran(apply), now=instance.applied_at)
    finally:
        backup.release()
    assert (state.status, state.waiting) == ("pending", "backup_running"), f"{state.status}, {state.waiting}"
    assert apply.read_restore(instance.root) == state, "the waiting is written"
    assert (mover.calls, cases.changed(instance.before, cases.fingerprint(instance.root))) == (0, []), "nothing moved"
    assert an_error(events), f"an error logged: {levels(events)}"
    state = apply.apply_pending_restore(instance.root, boot=never_ran(apply), now=instance.committed_at)
    assert (state.status, state.waiting) == ("applied", None), f"the backup over: applied: {state.status}, {state.waiting}"
    print_success("backup_running: waits, then applies")


@pytest.mark.parametrize("unusable", UNUSABLE_COPIES)
def test_a_copy_gone_unusable_since_the_confirmation_rolls_the_restore_back_before_anything_moves(tmp_path, databases, checked, unusable):
    """(g) Step 3: the copy's data folder or database missing, or one of its folders not a plain folder:
    ``rolled_back``, ``stage_missing``, nothing moved, nothing followed."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    confirm(apply, instance)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    unusable(instance, elsewhere)
    pointed = cases.fingerprint(elsewhere)
    with moving(apply) as mover:
        state = apply.apply_pending_restore(instance.root, boot=never_ran(apply), now=instance.applied_at)
    assert (state.status, state.reason, state.finished_at) == ("rolled_back", "stage_missing", instance.applied_at), f"{unusable.__name__}: {state.status}, {state.reason}"
    assert mover.calls == 0 and cases.changed(instance.before, cases.fingerprint(instance.root)) == [], f"{unusable.__name__}: nothing moved"
    assert cases.fingerprint(elsewhere) == pointed, f"{unusable.__name__}: nothing moved or written where a link points"
    print_success(f"{unusable.__name__}: stage_missing")


def _live_folder_a_link(folder: Path, elsewhere: Path) -> None:
    folder.symlink_to(elsewhere, target_is_directory=True)


def _live_folder_a_dangling_link(folder: Path, elsewhere: Path) -> None:
    folder.symlink_to(elsewhere / "nowhere", target_is_directory=True)


def _live_folder_a_file(folder: Path, elsewhere: Path) -> None:
    folder.write_bytes(b"a file where the uploads folder belongs\n")


@pytest.mark.parametrize("make", [_live_folder_a_link, _live_folder_a_dangling_link, _live_folder_a_file], ids=["a-link", "a-dangling-link", "a-file"])
def test_a_live_folder_that_is_not_a_plain_folder_fails_the_restore_before_anything_moves(tmp_path, databases, checked, make):
    """(g) Step 4: ``custom-uploads`` a link (dangling too) or a file: ``rolled_back``, ``swap_failed``, nothing moved —
    not even the database, which comes first — the link in place, what it points to untouched."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    elsewhere = tmp_path / "elsewhere"
    cases.write_files(elsewhere, {"photo.png": b"a file the link points to\n"})
    shutil.rmtree(instance.root / "custom-uploads")
    make(instance.root / "custom-uploads", elsewhere)
    confirm(apply, instance)
    data, pointed = cases.fingerprint(instance.root), cases.fingerprint(elsewhere)
    with moving(apply) as mover:
        state = apply.apply_pending_restore(instance.root, boot=never_ran(apply), now=instance.applied_at)
    assert (state.status, state.reason) == ("rolled_back", "swap_failed"), f"{make.__name__}: {state.status}, {state.reason}"
    assert (mover.calls, cases.fingerprint(instance.root), cases.fingerprint(elsewhere)) == (0, data, pointed), f"{make.__name__}: nothing moved, nothing followed"
    assert not lexists(elsewhere / "nowhere"), "a dangling link is not made to point to a new folder"
    print_success(f"{make.__name__}: swap_failed, nothing moved")


def test_the_leftovers_of_an_earlier_restore_are_removed_before_the_journal(tmp_path, databases, checked):
    """(g) Step 5: ``previous/`` and ``failed/`` that an earlier restore left are gone before the first rename, so that
    ``previous/`` holds exactly what this swap replaces."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    confirm(apply, instance)
    cases.write_files(previous_of(instance.root), {"custom-uploads/stale.png": b"set aside by an earlier restore", "sqlite/app.db": b"an older database"})
    cases.write_files(failed_of(instance.root), {"broker_reports/stale.csv": b"set aside by an earlier rollback"})
    seen: dict[str, Any] = {}

    def look() -> None:
        seen["left"] = (tree(previous_of(instance.root)), tree(failed_of(instance.root)))

    with moving(apply, on_first=look):
        state = apply.apply_pending_restore(instance.root, boot=never_ran(apply), now=instance.applied_at)
    assert state.status == "applied", f"applied: {state.status}, {state.reason}"
    assert seen.get("left") in ((None, None), ({}, None), (None, {}), ({}, {})), f"previous/ and failed/ emptied before the first rename: {seen.get('left')}"
    assert_swapped(instance)
    print_success("leftovers removed first")


@pytest.mark.parametrize("phase", TERMINAL_PHASES)
def test_a_finished_restore_is_left_as_it_is_at_the_next_start(tmp_path, databases, checked, phase):
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    state = into_phase(apply, instance, phase)
    snapshot = (cases.fingerprint(instance.root), restore_items(instance.root))
    with moving(apply) as mover:
        again = apply.apply_pending_restore(instance.root, boot=never_ran(apply, 2), now=instance.committed_at + timedelta(days=1))
    assert (again, mover.calls) == (state, 0), f"{phase}: nothing more: {again}"
    assert (cases.fingerprint(instance.root), restore_items(instance.root)) == snapshot, f"{phase}: nothing changed"
    print_success(f"{phase}: nothing")


def _answers(results: Any, processes: list[Any]) -> list[dict[str, Any]]:
    """One answer per process, read with a deadline: a process that dies or hangs fails the test instead of blocking it."""
    answers: list[dict[str, Any]] = []
    deadline = time.monotonic() + DEADLINE_S
    while len(answers) < len(processes):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            pytest.fail(f"only {len(answers)} of {len(processes)} processes answered within {DEADLINE_S}s: {answers}")
        try:
            answers.append(results.get(timeout=min(remaining, 1.0)))
        except queue.Empty:
            if not any(process.is_alive() for process in processes) and results.empty():
                pytest.fail(f"the processes exited without answering (exit codes {[process.exitcode for process in processes]}): {answers}")
    return answers


def _stop(processes: list[Any]) -> None:
    for process in processes:
        process.join(timeout=DEADLINE_S)
        if process.is_alive():
            process.kill()
            process.join(timeout=10)


def _a_worker_applies(root: str, barrier: Any, in_swap: Any, go: Any, asking: Any, results: Any) -> None:
    """One worker of a server started with two (``uvicorn --workers 2``), at its step ``pending-restore``: a spawn child
    of the test process, so that both workers read the same ``current_boot()``, their parent's.

    Module level, so that the spawned interpreter imports it by name. Every rename it makes is counted; at the first
    one it says so (``in_swap``) and waits for ``go``: the swap is then in progress, the apply lock held. Every blocking
    request for an exclusive file lock (``fcntl.flock`` or ``fcntl.lockf``: the contract's ``flock``) is said before it
    is made (``asking``). Its answer, or what failed, is sent back."""
    answer: dict[str, Any] = {"pid": os.getpid(), "renames": 0}
    try:
        fcntl = importlib.import_module("fcntl")
        apply = importlib.import_module(APPLY)
        real_move, real_flock, real_lockf = apply._move, fcntl.flock, fcntl.lockf

        def move(source: Path, target: Path) -> None:
            answer["renames"] += 1
            if answer["renames"] == 1:
                in_swap.set()
                if not go.wait(DEADLINE_S):
                    raise TimeoutError("the test never let the swap go on")
            real_move(source, target)

        def blocking(operation: int) -> bool:
            return bool(operation & fcntl.LOCK_EX) and not operation & fcntl.LOCK_NB

        def flock(fd: int, operation: int) -> None:
            if blocking(operation):
                asking.set()
            real_flock(fd, operation)

        def lockf(fd: int, operation: int, *args: Any) -> Any:
            if blocking(operation):
                asking.set()
            return real_lockf(fd, operation, *args)

        apply._move, fcntl.flock, fcntl.lockf = move, flock, lockf  # this spawned interpreter only
        barrier.wait(timeout=DEADLINE_S)
        state = apply.apply_pending_restore(Path(root))
        answer["state"] = None if state is None else state.model_dump(mode="json")
    except Exception as exc:  # sent back: the test reports it instead of waiting for an answer that never comes
        answer["error"] = f"{type(exc).__name__}: {exc}"
    results.put(answer)


def test_two_workers_of_one_server_make_one_swap_and_both_answer_applied_by_the_same_boot(tmp_path, databases, checked):
    """(g) Both workers start together. Whichever takes the apply lock first swaps, and is held at its first rename
    until the other has asked for the lock: only then does the swap go on. The other then finds ``applied`` by its own
    boot and does nothing. Without the lock it would read ``applying`` and undo a swap in progress."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    confirm(apply, instance)
    context = multiprocessing.get_context("spawn")
    barrier, in_swap, go, results = context.Barrier(2), context.Event(), context.Event(), context.Queue()
    asking = [context.Event(), context.Event()]
    workers = [context.Process(target=_a_worker_applies, args=(str(instance.root), barrier, in_swap, go, asking[n], results), name=f"b3-restore-worker-{n}", daemon=True) for n in range(2)]
    for worker in workers:
        worker.start()
    try:
        swapping = in_swap.wait(DEADLINE_S)
        asked = [event.wait(DEADLINE_S) for event in asking] if swapping else [False, False]
        held = swapping and not apply_lock_free(instance.root)
    finally:
        go.set()
    try:
        answers = _answers(results, workers)
    finally:
        _stop(workers)
    assert [answer["error"] for answer in answers if "error" in answer] == [], f"a worker failed: {answers}"
    assert swapping, f"no worker began the swap within {DEADLINE_S}s: {answers}"
    assert asked == [True, True], "while one worker swapped, the other must wait for the apply lock: it never asked for it (an exclusive, blocking flock)"
    assert held, "the apply lock is held while the swap is in progress"
    states = [answer.get("state") for answer in answers]
    assert [state and state["status"] for state in states] == ["applied", "applied"], f"both workers answer applied: {states}"
    assert states[0] == states[1], f"the second answers the state the first left: {states}"
    assert states[0]["boot"] == this_boot(apply).model_dump(mode="json"), f"the boot of both is their parent's, the server's: {states[0]['boot']}"
    assert sorted(answer["renames"] for answer in answers) == [0, instance.renames], f"one swap: one worker made every rename, the other none: {[answer['renames'] for answer in answers]}"
    assert_swapped(instance)
    assert [worker.exitcode for worker in workers] == [0, 0], f"both workers ended cleanly: {[worker.exitcode for worker in workers]}"
    print_success("one swap, both applied by the same boot")


# =============================================================================
# (g) §10 Never under a running server: the serving lock
# =============================================================================


def _a_server_serves(root: str, results: Any, release: Any) -> None:
    """A server process past its step ``serving-lock``, in a spawn child of the test process: it holds the serving lock
    of ``root`` (asked twice: once per data directory and process), says so, and serves until the test lets it go; then
    it exits, and the system releases the lock with it. Module level, so that the spawned interpreter imports it by
    name. What fails is sent back: the test reports it instead of waiting for an answer that never comes."""
    answer: dict[str, Any] = {"pid": os.getpid()}
    try:
        apply = importlib.import_module(APPLY)
        answer["held"] = [apply.hold_serving_lock(Path(root)), apply.hold_serving_lock(Path(root))]
        answer["descriptors"] = len(apply._SERVING)
    except Exception as exc:  # sent back: the test reports it
        answer["error"] = f"{type(exc).__name__}: {exc}"
    results.put(answer)
    release.wait(DEADLINE_S)


@contextmanager
def serving(root: Path) -> Iterator[dict[str, Any]]:
    """A server serving the data directory ``root`` for the block: a spawn child holding its serving lock, its answer
    yielded once it holds it. At the end of the block the child is let go and waited for: the lock is free again."""
    context = multiprocessing.get_context("spawn")
    results, release = context.Queue(), context.Event()
    server = context.Process(target=_a_server_serves, args=(str(root), results, release), name="b3-serving-server", daemon=True)
    server.start()
    try:
        [answer] = _answers(results, [server])
        assert "error" not in answer and answer.get("held") == [True, True], f"precondition: the server holds the serving lock of its data directory: {answer}"
        yield answer
    finally:
        release.set()
        _stop([server])


def test_while_a_server_serves_a_pending_restore_waits_and_the_first_start_without_it_applies_it(tmp_path, databases, checked):
    """(g) §10 A worker uvicorn starts again under its running siblings, or a second server on the data directory: a
    pending restore is not applied under a server that serves the data. ``waiting = server_running``, an error logged,
    nothing moved. Once that server exited, the next start applies it."""
    print_section("(g) The serving lock")
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    confirm(apply, instance)
    copy_before = tree(stage_dir(instance.root, instance.stage_id))
    with serving(instance.root):
        with moving(apply) as mover, logs() as events:
            state = apply.apply_pending_restore(instance.root, boot=never_ran(apply), now=instance.applied_at)
        assert (state.status, state.waiting) == ("pending", "server_running"), f"{state.status}, {state.waiting}"
        assert apply.read_restore(instance.root) == state, "the waiting is written"
        assert mover.calls == 0 and cases.changed(instance.before, cases.fingerprint(instance.root)) == [], f"nothing moved: {mover.moved}"
        assert tree(stage_dir(instance.root, instance.stage_id)) == copy_before, "the checked copy as it was"
        assert an_error(events), f"an error logged: {levels(events)}"
    state = apply.apply_pending_restore(instance.root, boot=never_ran(apply), now=instance.committed_at)
    assert (state.status, state.waiting) == ("applied", None), f"the server gone: applied, no longer waiting: {state.status}, {state.waiting}"
    assert_swapped(instance)
    print_success("server_running: waits, then applies")


def test_while_a_server_serves_a_restore_a_dead_start_applied_is_not_undone_and_the_start_stops(tmp_path, databases, checked):
    """(g) §10 Applied by a start that died, while a server serves the data directory (a worker it left behind, a second
    server): putting the data of before back would move it from under that server. ``RestoreInUseError``, nothing
    undone or written, the state as it was, an error logged. Once that server exited, the next start undoes it."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    confirm(apply, instance)
    applied = apply.apply_pending_restore(instance.root, boot=never_ran(apply), now=instance.applied_at)
    snapshot = (cases.fingerprint(instance.root), restore_items(instance.root))
    with serving(instance.root):
        with moving(apply) as mover, logs() as events, pytest.raises(apply.RestoreInUseError) as raised:
            apply.apply_pending_restore(instance.root, boot=never_ran(apply, 1), now=instance.committed_at)
        assert raised.value.code == "restore_in_use", raised.value.code
        assert mover.calls == 0, f"nothing undone: {mover.moved}"
        assert (cases.fingerprint(instance.root), restore_items(instance.root), apply.read_restore(instance.root)) == (*snapshot, applied), "nothing written, the state as it was"
        assert an_error(events), f"an error logged: {levels(events)}"
        assert apply_lock_free(instance.root), "the apply lock is released when the step stops"
    state = apply.apply_pending_restore(instance.root, boot=never_ran(apply, 1), now=instance.committed_at)
    assert (state.status, state.reason) == ("rolled_back", "first_start_failed"), f"the server gone: undone: {state.status}, {state.reason}"
    assert_put_back(instance)
    print_success("restore_in_use under a server, then undone")


def test_a_probe_from_another_process_finds_the_serving_lock_held_while_a_server_lives_and_free_once_it_exited(tmp_path):
    """(g) §10 Two server processes hold the lock together (a shared lock: the workers of one server), each once (one
    descriptor for two calls). A restore's probe (``_exclusive_serving_lock``) finds it held while they live, and then
    holds nothing: another worker can still take its shared lock. Free, the probe keeps it exclusively for its block
    (a server process would wait), and only for its block: after it, another probe finds it free again. No file is
    created: the lock is on the directory itself."""
    apply = apply_module()
    root = tmp_path / "data"
    cases.write_files(root, UNTOUCHED)
    listed = cases.listing(root)
    with apply._exclusive_serving_lock(root) as served:
        assert served is False, "barrier: nobody serves the data directory yet"
        assert serving_lock_free(root) is False, "found free, the probe keeps the lock exclusively for its block: a server process would wait"
    with apply._exclusive_serving_lock(root) as served:
        assert served is False, "after the block, another probe is free again: the first released what it held"
    with serving(root) as first, serving(root) as second:
        assert (first["descriptors"], second["descriptors"]) == (1, 1), f"once per data directory and process: one descriptor each: {first}, {second}"
        with apply._exclusive_serving_lock(root) as served:
            assert served is True, "a probe from another process finds the lock held"
            assert serving_lock_free(root) is True, "and holds nothing: another worker can still take its shared lock"
        assert cases.listing(root) == listed, f"no file created: {sorted(set(cases.listing(root)) - set(listed))}"
    with apply._exclusive_serving_lock(root) as served:
        assert served is False, "free once every server process exited"
    assert serving_lock_free(root) is True, "and free again after the probe's block"
    assert cases.listing(root) == listed, "and still no file"
    print_success("held while a server lives, free once it exited")


def test_hold_serving_lock_holds_the_data_directory_itself_once_per_process_and_creates_nothing(tmp_path, serving_here):
    """(g) §10 In one process: ``True``, the descriptor kept (one, on the data directory itself: its ``fstat`` is the
    directory's), the same at a second call; nothing logged: granted at once, there is nothing to say; no file created.
    Released by the fixture: nothing stays held."""
    apply = serving_here
    root = tmp_path / "data"
    cases.write_files(root, UNTOUCHED)
    listed = cases.listing(root)
    key = str(root.resolve())
    assert key not in apply._SERVING, "precondition: not held yet"
    with logs() as events:
        held = apply.hold_serving_lock(root)
        fd = apply._SERVING.get(key)
        again = (apply.hold_serving_lock(root), apply._SERVING.get(key))
    assert held is True, "held"
    assert fd is not None and os.path.samestat(os.fstat(fd), os.stat(root)), "a descriptor kept, on the data directory itself"
    assert again == (True, fd), f"once per data directory and process: the same descriptor: {again}"
    assert levels(events) == set(), f"granted at once: nothing logged, {levels(events)}"
    assert cases.listing(root) == listed, f"no file created: {sorted(set(cases.listing(root)) - set(listed))}"
    print_success("True, one descriptor on the directory, nothing logged, nothing created")


class _ARestoreMovesTheFolders:
    """``fcntl`` as a starting process finds it while a restore holds the serving lock exclusively: a request not waited
    for is refused (``BlockingIOError``), the one waited for is granted (the restore done). Each request is recorded
    with how many warnings that the start waits had been logged by then (in ``events``, set by the test)."""

    LOCK_SH, LOCK_EX, LOCK_NB, LOCK_UN = fcntl.LOCK_SH, fcntl.LOCK_EX, fcntl.LOCK_NB, fcntl.LOCK_UN

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self.calls: list[tuple[int, int, int]] = []

    def flock(self, fd: int, operation: int) -> None:
        self.calls.append((fd, operation, len(said(self.events, WAITING_FOR_THE_MOVES))))
        if operation & self.LOCK_NB:
            raise BlockingIOError(EWOULDBLOCK, os.strerror(EWOULDBLOCK))


def test_a_start_that_finds_a_restore_moving_the_folders_warns_that_it_waits_then_holds_the_lock(tmp_path, serving_here, monkeypatch):
    """(g) §10 ``hold_serving_lock`` asks first without waiting. Refused (``BlockingIOError``: a restore holds the lock
    exclusively while it moves the folders), it says in a warning that this start waits — before it waits, so that a
    start stuck there says why — then waits for a plain shared lock on the same descriptor, and holds it once granted:
    ``True``."""
    apply = serving_here
    root = tmp_path / "data"
    cases.write_files(root, UNTOUCHED)
    restore = _ARestoreMovesTheFolders()
    monkeypatch.setattr(apply, "fcntl", restore)
    with logs() as events:
        restore.events = events
        held = apply.hold_serving_lock(root)
    fd = apply._SERVING.get(str(root.resolve()))
    assert (held, fd is not None) == (True, True), f"held once granted: {held}, descriptor {fd}"
    assert restore.calls == [(fd, fcntl.LOCK_SH | fcntl.LOCK_NB, 0), (fd, fcntl.LOCK_SH, 1)], f"first a request not waited for; refused, the warning logged, then a plain shared lock waited for, on the descriptor it keeps: {restore.calls}"
    assert said(events, WAITING_FOR_THE_MOVES) == ["warning"], f"one warning says this start waits: {levels(events)}"
    print_success("refused, warned, waited, held")


def test_without_fcntl_the_serving_lock_is_not_held_and_a_probe_cannot_tell(tmp_path, serving_here, monkeypatch):
    """(g) §10 Not POSIX: ``hold_serving_lock`` is ``False`` and holds nothing; a restore's probe
    (``_exclusive_serving_lock``) finds nobody serving and holds nothing either: a restore then behaves as before the
    lock existed. Nothing created."""
    apply = serving_here
    root = tmp_path / "data"
    cases.write_files(root, UNTOUCHED)
    listed = cases.listing(root)
    monkeypatch.setattr(apply, "fcntl", None)
    assert (apply.hold_serving_lock(root), str(root.resolve()) in apply._SERVING) == (False, False), "not held"
    with apply._exclusive_serving_lock(root) as served:
        holds_nothing = serving_lock_free(root)
    assert (served, holds_nothing) == (False, True), f"a probe cannot tell, and holds nothing: {served}, {holds_nothing}"
    assert cases.listing(root) == listed, "nothing created"
    print_success("no fcntl: False, nothing held")


def test_a_data_directory_that_cannot_be_opened_is_neither_held_nor_found_served_and_a_warning_says_so(tmp_path, serving_here):
    """(g) §10 A data directory that cannot be opened (here, absent): the lock is not held, a restore's probe finds
    nobody serving it; each says in a warning that the lock cannot be relied on. Nothing is created to open it."""
    apply = serving_here
    missing = tmp_path / "no-data-directory-here"
    with logs() as held_events:
        held = apply.hold_serving_lock(missing)
    with logs() as probe_events, apply._exclusive_serving_lock(missing) as served:
        pass
    assert (held, served, str(missing.resolve()) in apply._SERVING) == (False, False, False), f"not held, not found served: {held}, {served}"
    assert a_warning(held_events) and a_warning(probe_events), f"each says so: {levels(held_events)}, {levels(probe_events)}"
    assert not lexists(missing), "nothing created"
    print_success("cannot be opened: False, False, a warning each")


class _FlockRefused:
    """``fcntl`` on a file system that refuses ``flock`` (some network file systems): every request fails, ``ENOLCK``."""

    LOCK_SH, LOCK_EX, LOCK_NB, LOCK_UN = fcntl.LOCK_SH, fcntl.LOCK_EX, fcntl.LOCK_NB, fcntl.LOCK_UN

    @staticmethod
    def flock(fd: int, operation: int) -> None:
        raise OSError(ENOLCK, os.strerror(ENOLCK))


def test_a_file_system_that_refuses_flock_holds_nothing_finds_nobody_serving_and_a_warning_says_so(tmp_path, serving_here, monkeypatch):
    """(g) §10 The directory opens, but ``flock`` is refused (``ENOLCK``, not ``BlockingIOError``: nobody is known to
    hold it). ``hold_serving_lock`` is ``False`` and holds nothing; a restore's probe finds nobody serving and holds
    nothing; each says so in a warning: a restore then behaves as before the lock existed, and an operator can tell.
    Nothing created."""
    apply = serving_here
    root = tmp_path / "data"
    cases.write_files(root, UNTOUCHED)
    listed = cases.listing(root)
    monkeypatch.setattr(apply, "fcntl", _FlockRefused)
    with logs() as held_events:
        held = apply.hold_serving_lock(root)
    with logs() as probe_events, apply._exclusive_serving_lock(root) as served:
        holds_nothing = serving_lock_free(root)
    assert (held, str(root.resolve()) in apply._SERVING) == (False, False), f"not held: {held}"
    assert (served, holds_nothing) == (False, True), f"a probe finds nobody serving, and holds nothing: {served}, {holds_nothing}"
    assert a_warning(held_events) and a_warning(probe_events), f"each says so: {levels(held_events)}, {levels(probe_events)}"
    assert cases.listing(root) == listed, "nothing created"
    print_success("flock refused: False, False, a warning each")


#: The renames a killed start made before it died: the database's two (the live one to previous/, the restored one in)
#: and the live uploads to previous/. Its undo then has three to make: the uploads back; the restored database set aside
#: in failed/, the database back.
HALF_SWAPPED = 3


def _pending(apply: Any, instance: Instance) -> None:
    confirm(apply, instance)


def _applied_by_a_start_that_died(apply: Any, instance: Instance) -> None:
    into_phase(apply, instance, "applied")


def _half_swapped_by_a_start_that_was_killed(apply: Any, instance: Instance) -> None:
    # Not into_phase(..., "applying"): it kills the swap before its first rename, and the undo would then rename nothing.
    confirm(apply, instance)
    killed(apply, instance, HALF_SWAPPED, boot=never_ran(apply), now=instance.applied_at)


#: Every way a step moves folders, from the restore it finds: how it ends, and how the data directory then stands.
MOVING_STEPS = [
    pytest.param(_pending, ("applied", None), assert_swapped, id="the-swap-of-a-pending-restore"),
    pytest.param(_applied_by_a_start_that_died, ("rolled_back", "first_start_failed"), assert_put_back, id="the-undo-of-a-restore-a-dead-start-applied"),
    pytest.param(_half_swapped_by_a_start_that_was_killed, ("rolled_back", "swap_interrupted"), assert_put_back, id="the-undo-of-a-swap-a-killed-start-left-half-done"),
]


@pytest.mark.parametrize(("prepare", "outcome", "stands"), MOVING_STEPS)
def test_while_a_step_moves_the_folders_no_process_can_take_the_serving_lock_and_once_it_returned_one_can(tmp_path, databases, checked, prepare, outcome, stands):
    """(g) §10 A process reaching its step ``serving-lock`` while a restore moves the folders would read them half
    moved: the step holds the serving lock exclusively from its checks to its last rename, and that process waits. At
    every rename, a shared lock asked through another descriptor without waiting is refused (``BlockingIOError``: a
    ``flock`` lock belongs to an open file description, even in one process); this probes every rename, not only the
    first. Once the step returned, the same request succeeds."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    prepare(apply, instance)
    assert serving_lock_free(instance.root), "barrier: before the step, a process could take the serving lock"
    seen: list[bool] = []
    with moving(apply, on_each=lambda: seen.append(serving_lock_free(instance.root))) as mover, logs() as events:
        state = apply.apply_pending_restore(instance.root, boot=never_ran(apply, 1), now=instance.committed_at)
    assert (state.status, state.reason) == outcome, f"precondition: the step ends {outcome}: {state.status}, {state.reason}"
    stands(instance)
    assert mover.calls > 0 and len(seen) == mover.calls, f"precondition: the step renamed folders, each rename probed: {mover.calls} renames, {len(seen)} probes"
    assert seen == [False] * mover.calls, f"at every rename the serving lock is held exclusively: free at renames {[n for n, free in enumerate(seen, 1) if free]} of {mover.calls}"
    assert serving_lock_free(instance.root), "once the step returned, a process can take the serving lock again"
    assert said(events, HALF_SWAPPED_UNDER_A_SERVER) == [], "nobody serves: no server is reported to restart (the undo of a killed swap included)"
    print_success(f"{outcome}: held at each of {mover.calls} renames, free once returned")


def test_a_swap_that_failed_is_undone_under_the_serving_lock_and_frees_it_once_the_step_returned(tmp_path, databases, checked):
    """(g) §10 The second rename of the swap fails (``OSError``): the step puts the data of before back
    (``swap_failed``) still holding the serving lock exclusively, and frees it when it returns."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    confirm(apply, instance)
    seen: list[bool] = []
    with moving(apply, fail_at=frozenset({2}), on_each=lambda: seen.append(serving_lock_free(instance.root))) as mover:
        state = apply.apply_pending_restore(instance.root, boot=never_ran(apply), now=instance.applied_at)
    assert (state.status, state.reason) == ("rolled_back", "swap_failed"), f"precondition: the swap failed and was undone: {state.status}, {state.reason}"
    assert_put_back(instance)
    assert mover.calls > 2, f"precondition: the undo renamed folders after the rename that failed: {mover.calls} renames"
    assert seen == [False] * mover.calls, f"the swap and its undo, every rename under the lock: free at renames {[n for n, free in enumerate(seen, 1) if free]} of {mover.calls}"
    assert serving_lock_free(instance.root), "free once the step returned"
    print_success(f"swap_failed: held at each of {mover.calls} renames, free once returned")


#: A step that raises while it holds the serving lock: the restore it finds, the plan of its renames, what it raises
#: (a name of ``apply``, or a class of this module), the status it leaves on disk.
RAISING_STEPS = [
    pytest.param(_pending, {"fail_at": frozenset({2, 3})}, "RestoreApplyError", "rolling_back", id="the-swap-fails-then-its-undo"),
    pytest.param(_pending, {"kill_after": 2}, _Crash, "applying", id="killed-during-the-swap"),
    pytest.param(_applied_by_a_start_that_died, {"fail_at": frozenset({1})}, "RestoreApplyError", "rolling_back", id="the-undo-of-a-dead-start-fails"),
    pytest.param(_half_swapped_by_a_start_that_was_killed, {"fail_at": frozenset({1})}, "RestoreApplyError", "rolling_back", id="the-undo-of-a-killed-swap-fails"),
]


@pytest.mark.parametrize(("prepare", "plan", "raised", "left"), RAISING_STEPS)
def test_a_step_that_raises_frees_the_serving_lock(tmp_path, databases, checked, prepare, plan, raised, left):
    """(g) §10 However the step ends — an undo that fails (``RestoreApplyError``: the start stops), an exception no
    handler of the product catches (``_Crash``) — the serving lock is not kept: held at every rename until then, free
    once the step raised, the apply lock too. A process that dies loses it with its descriptors; one that only raised
    must not keep it, or every process reaching its step ``serving-lock`` would wait for it."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    prepare(apply, instance)
    expected = getattr(apply, raised) if isinstance(raised, str) else raised
    seen: list[bool] = []
    with moving(apply, on_each=lambda: seen.append(serving_lock_free(instance.root)), **plan), pytest.raises(expected):
        apply.apply_pending_restore(instance.root, boot=never_ran(apply, 1), now=instance.committed_at)
    state = apply.read_restore(instance.root)
    assert state is not None and state.status == left, f"precondition: the step stopped with the restore {left}: {state}"
    assert seen and seen == [False] * len(seen), f"held at every rename until the step raised: {seen}"
    assert serving_lock_free(instance.root), "free once the step raised"
    assert apply_lock_free(instance.root), "and the apply lock too"
    print_success(f"{expected.__name__}: held at each of {len(seen)} renames, free once raised")


def test_a_half_swapped_data_directory_is_made_whole_even_while_a_server_serves_it(tmp_path, databases, checked):
    """(g) §10 A start killed in the middle of the swap left the data directory half swapped: only the undo makes it
    whole again, so it runs whoever serves the data directory (the serving lock then cannot be held).
    ``swap_interrupted``, the data of before back exactly; an error says that the server serving it must be restarted
    (it has been serving half-swapped data)."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    _half_swapped_by_a_start_that_was_killed(apply, instance)
    with serving(instance.root):
        with logs() as events:
            state = apply.apply_pending_restore(instance.root, boot=never_ran(apply, 1), now=instance.committed_at)
        assert (state.status, state.reason) == ("rolled_back", "swap_interrupted"), f"undone under a server: {state.status}, {state.reason}"
        assert_put_back(instance)
        assert said(events, HALF_SWAPPED_UNDER_A_SERVER) == ["error"], f"an error says the server must be restarted, once: {levels(events)}"
    print_success("half swapped: undone, whoever serves; the server to restart reported")


# =============================================================================
# (h) §2, §3 finish_pending_restore
# =============================================================================


def test_a_restore_this_boot_applied_is_committed_and_its_leftovers_removed(tmp_path, databases, checked):
    """(h) The first start reached ``restore-commit``: every session ends (§3), ``committed``; the data replaced
    (``previous/``), a ``failed/`` left from before, this restore's copy and its check state removed, nothing else of
    ``.restore``. A later start finds it committed and does nothing more."""
    print_section("(h) finish_pending_restore")
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    confirm(apply, instance)
    boot = never_ran(apply)
    applied = apply.apply_pending_restore(instance.root, boot=boot, now=instance.applied_at)
    cases.write_files(failed_of(instance.root), {"custom-uploads/left-by-an-earlier-rollback.png": b"set aside before"})
    state = apply.finish_pending_restore(instance.root, boot=boot, now=instance.committed_at)
    found = (state.status, state.finished_at, state.session_version, state.boot, state.applied_at, state.reason, state.waiting)
    assert found == ("committed", instance.committed_at, millis(instance.committed_at), boot, applied.applied_at, None, None), f"committed at the time given, the sessions' value recorded: {found}"
    assert apply.read_restore(instance.root) == state, "the state on disk is the state returned"
    left = [path.name for path in (previous_of(instance.root), failed_of(instance.root), stage_dir(instance.root, instance.stage_id), check_state_path(instance.root, instance.stage_id)) if lexists(path)]
    assert left == [], f"previous/, failed/, the copy and its check state removed: {left}"
    assert_unrelated_kept(instance.root)
    assert {name: tree(instance.root / name) for name in SWAPPED[1:]} == {name: instance.staged[name] for name in SWAPPED[1:]}, "the restored files stay live"
    assert set(versions_of(instance.root / DATABASE_ENTRY).values()) == {state.session_version}, "every account at the value"
    assert cases.changed(outside(instance.before), outside(cases.fingerprint(instance.root))) == [], "nothing else touched"
    snapshot = (cases.fingerprint(instance.root), restore_items(instance.root))
    again = apply.finish_pending_restore(instance.root, boot=never_ran(apply, 1), now=instance.committed_at + timedelta(days=1))
    assert again == state and (cases.fingerprint(instance.root), restore_items(instance.root)) == snapshot, "at a later start: nothing more"
    print_success(f"committed, session_version {state.session_version}")


#: Accounts set ahead of the restore time R by these milliseconds, in the database before (the live one) and in the
#: restored one; and how far above R every account must end.
SESSION_VALUES = [
    pytest.param({}, {}, 0, id="the-restore-time"),
    pytest.param({"live_admin": 5000}, {}, 5001, id="the-clock-behind-the-database-before"),
    pytest.param({}, {"bob_user": 9}, 10, id="the-clock-behind-the-restored-database"),
    pytest.param({"live_user": 5000}, {"zoe_admin": 9000}, 9001, id="the-clock-behind-both-the-restored-further"),
]


def held_versions(database: Path) -> set[int]:
    """The versions the accounts of ``database`` hold; none when it cannot be read (absent, or not a database)."""
    if not database.is_file():
        return set()
    try:
        return set(versions_of(database).values())
    except sqlite3.DatabaseError:
        return set()


def committed_with(apply: Any, instance: Instance, before_ahead: dict[str, int], restored_ahead: dict[str, int]) -> tuple[Any, set[int]]:
    """The instance's restore confirmed, applied and committed, its accounts first set ahead of the restore time as
    given; the committed state, and every version either database held."""
    restore_time = millis(instance.committed_at)
    before_db, restored_db = instance.root / DATABASE_ENTRY, instance.copy / DATABASE_ENTRY
    if before_ahead:
        set_versions(before_db, {name: restore_time + ahead for name, ahead in before_ahead.items()})
    if restored_ahead:
        set_versions(restored_db, {name: restore_time + ahead for name, ahead in restored_ahead.items()})
    held = held_versions(before_db) | held_versions(restored_db)
    confirm(apply, instance)
    apply.apply_pending_restore(instance.root, boot=never_ran(apply), now=instance.applied_at)
    return apply.finish_pending_restore(instance.root, boot=never_ran(apply), now=instance.committed_at), held


@pytest.mark.parametrize(("before_ahead", "restored_ahead", "above"), SESSION_VALUES)
def test_every_account_gets_the_largest_of_the_restore_time_and_of_each_database_plus_one(tmp_path, databases, checked, before_ahead, restored_ahead, above):
    """(h) §3: ``max(R, A + 1, B + 1)``, a time, not a counter: R in practice, one more than a stored value only when the
    clock is behind it. Every account of the restored database, the disabled one included."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    state, held = committed_with(apply, instance, before_ahead, restored_ahead)
    value = millis(instance.committed_at) + above
    assert (state.status, state.session_version) == ("committed", value), f"R + {above}: {state.session_version - millis(instance.committed_at) if state.session_version else state.session_version}"
    assert versions_of(instance.root / DATABASE_ENTRY) == dict.fromkeys(BACKUP_VERSIONS, value), "every account of the restored database at the value"
    assert value > max(held), "above every version either database held"
    print_success(f"R + {above}")


@pytest.mark.parametrize("before", ["no-database-before", "not-a-database", "no-account"])
def test_a_database_before_that_cannot_be_read_or_holds_no_account_counts_as_zero(tmp_path, databases, checked, before):
    """(h) §3: B is 0 when the database before cannot be read (none was live; not a database) — and when it holds no
    account, as an instance restored right after its installation does."""
    apply = apply_module()
    if before == "no-database-before":
        instance = build(tmp_path / "instance", databases, checked, NO_LIVE_DATABASE)
    elif before == "not-a-database":
        instance = build(tmp_path / "instance", databases, checked, live_database=b"SQLite format 2\x00 not a database at all\n")
    else:
        instance = build(tmp_path / "instance", databases, checked, live_accounts=(), live_versions={})
    state, _held = committed_with(apply, instance, {}, {})
    assert (state.status, state.session_version) == ("committed", millis(instance.committed_at)), f"{before}: the restore time, {state.status}, {state.session_version}"
    assert set(versions_of(instance.root / DATABASE_ENTRY).values()) == {state.session_version}, "every account at the value"
    print_success(f"{before}: B = 0")


def test_finish_stops_the_start_on_a_restore_another_boot_applied(tmp_path, databases, checked):
    """(h) §10 Applied by another boot: not this start's to commit, and serving data whose restore is not committed is
    worse. The start stops (``RestoreInUseError``, ``restore_in_use``): nothing written or removed, no session ended,
    no link revoked, the state as it was, an error logged, the apply lock released."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    confirm(apply, instance)
    applied = apply.apply_pending_restore(instance.root, boot=never_ran(apply), now=instance.applied_at)
    snapshot = (cases.fingerprint(instance.root), restore_items(instance.root))
    with logs() as events, pytest.raises(apply.RestoreInUseError) as raised:
        apply.finish_pending_restore(instance.root, boot=never_ran(apply, 1), now=instance.committed_at)
    assert raised.value.code == "restore_in_use", raised.value.code
    assert (cases.fingerprint(instance.root), restore_items(instance.root)) == snapshot, "nothing written or removed: the restored database (no session ended), previous/, the copy"
    assert apply.read_restore(instance.root) == applied, "the state as it was"
    assert an_error(events), f"an error logged: {levels(events)}"
    assert apply_lock_free(instance.root), "the apply lock is released when the step stops"
    print_success("another boot at the commit: restore_in_use")


def test_finish_removes_what_a_rollback_left_and_the_restore_stays_rolled_back(tmp_path, databases, checked):
    """(h) Rolled back (here by a rename that failed): ``failed/``, ``previous/``, the copy and its check state removed;
    the state and the data as they were."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    rolled = into_phase(apply, instance, "rolled_back")
    assert tree(failed_of(instance.root) / "sqlite"), "precondition: failed/ holds the restored database"
    state = apply.finish_pending_restore(instance.root, boot=never_ran(apply), now=instance.committed_at)
    assert state == rolled, f"still rolled back, as it was: {state}"
    left = [path.name for path in (previous_of(instance.root), failed_of(instance.root), stage_dir(instance.root, instance.stage_id), check_state_path(instance.root, instance.stage_id)) if lexists(path)]
    assert left == [], f"the leftovers removed: {left}"
    assert_unrelated_kept(instance.root)
    assert cases.changed(instance.before, cases.fingerprint(instance.root)) == [], "the data as it was"
    print_success("rolled_back: leftovers removed")


@pytest.mark.parametrize("phase", ["pending", "applying", "rolling_back"])
def test_finish_leaves_a_restore_that_is_not_applied_alone(tmp_path, databases, checked, phase):
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    state = into_phase(apply, instance, phase)
    snapshot = (cases.fingerprint(instance.root), restore_items(instance.root))
    assert apply.finish_pending_restore(instance.root, boot=never_ran(apply), now=instance.committed_at) == state, f"{phase}: nothing done"
    assert (cases.fingerprint(instance.root), restore_items(instance.root)) == snapshot, f"{phase}: nothing changed"
    print_success(f"{phase}: nothing")


# =============================================================================
# (h) §3 The one-time links of the restored database
# =============================================================================

#: The fields of a restore's state (contract §2): the commit adds none; its count of revoked links goes to the log.
#: Lot B5-1 (s) adds the owner's two fields, written at the confirmation and after the first start, not by the commit;
#: lot B5-1d adds ``token_watermark``, written by the swap.
STATE_FIELDS = {
    "format",
    "status",
    "stage_id",
    "data_dir",
    "confirmed_at",
    "confirmed_by",
    "confirmed_via",
    "backup_created_at",
    "backup_app_version",
    "action",
    "swap",
    "boot",
    "applied_at",
    "finished_at",
    "reason",
    "waiting",
    "session_version",
    "owner_user_id",
    "owner_outcome",
    "token_watermark",
}
#: How SQLAlchemy stores a datetime in SQLite: UTC, no offset, always six digits of microseconds.
SQLALCHEMY_DATETIME = "%Y-%m-%d %H:%M:%S.%f"
#: How long after its issue a link of the plans below was consumed or revoked.
ACTED_AFTER = timedelta(minutes=5)


@dataclass(frozen=True)
class LinkPlan:
    """A one-time link to write: its purpose, the account it acts on (an invitation: none), how long before the restore
    it was issued and for how long (``None``: A's default), and what it is at the restore: ``valid`` or ``expired`` (both
    live: neither consumed nor revoked), ``consumed`` or ``revoked`` (``ACTED_AFTER`` its issue)."""

    name: str
    purpose: AccountTokenPurpose
    account: str | None
    issued_before: timedelta
    ttl: timedelta | None
    became: str


@dataclass(frozen=True)
class Link:
    """A link written through A's ``token_service``: its plan, its plaintext (shown once, never stored), its row id."""

    plan: LinkPlan
    token: str
    token_id: int

    @property
    def live(self) -> bool:
        return self.plan.became in ("valid", "expired")


#: The links of the restored database: every purpose live and valid, live ones expired, consumed ones, revoked ones.
RESTORED_LINKS = (
    LinkPlan("invite-valid", AccountTokenPurpose.INVITE, None, timedelta(hours=1), None, "valid"),
    LinkPlan("password-reset-valid", AccountTokenPurpose.PASSWORD_RESET, "bob_user", timedelta(minutes=10), None, "valid"),
    LinkPlan("email-verification-valid", AccountTokenPurpose.EMAIL_VERIFICATION, "zoe_admin", timedelta(hours=1), None, "valid"),
    LinkPlan("admin-setup-valid", AccountTokenPurpose.ADMIN_SETUP, "ada_admin", timedelta(hours=1), None, "valid"),
    LinkPlan("invite-expired", AccountTokenPurpose.INVITE, None, timedelta(days=10), None, "expired"),
    LinkPlan("password-reset-expired", AccountTokenPurpose.PASSWORD_RESET, "bob_user", timedelta(days=2), None, "expired"),
    LinkPlan("invite-consumed", AccountTokenPurpose.INVITE, None, timedelta(days=3), None, "consumed"),
    LinkPlan("email-verification-consumed", AccountTokenPurpose.EMAIL_VERIFICATION, "zoe_admin", timedelta(days=3), None, "consumed"),
    LinkPlan("password-reset-revoked", AccountTokenPurpose.PASSWORD_RESET, "bob_user", timedelta(hours=5), timedelta(hours=1), "revoked"),
    LinkPlan("admin-setup-revoked", AccountTokenPurpose.ADMIN_SETUP, "ada_admin", timedelta(days=1), None, "revoked"),
)
#: How many of them are live: the count the commit revokes.
LIVE_RESTORED = sum(1 for plan in RESTORED_LINKS if plan.became in ("valid", "expired"))
#: The links of the database before the restore, live: that database is only read, and none of them enters the other.
BEFORE_LINKS = (
    LinkPlan("before-invite-valid", AccountTokenPurpose.INVITE, None, timedelta(hours=1), None, "valid"),
    LinkPlan("before-password-reset-valid", AccountTokenPurpose.PASSWORD_RESET, "live_admin", timedelta(minutes=10), None, "valid"),
)
#: The commit's ``now``: in UTC, in another zone (the same instant), on a whole second (still six digits stored).
RESTORE_TIMES = [pytest.param("utc", id="now-in-utc"), pytest.param("utc+2", id="now-in-another-zone"), pytest.param("whole-second", id="now-on-a-whole-second")]


def restore_time_of(instance: Instance, variant: str) -> datetime:
    """The commit's ``now``, a minute after the swap, as ``variant`` gives it."""
    utc = instance.committed_at.astimezone(UTC).replace(microsecond=250_125)
    if variant == "whole-second":
        return utc.replace(microsecond=0)
    if variant == "utc+2":
        return utc.astimezone(timezone(timedelta(hours=2)))
    return utc


def links_engine(database: Path) -> AsyncEngine:
    """The database file as A's code opens it: ``sqlite+aiosqlite``, NullPool, the app's connect listener."""
    return create_async_engine(f"sqlite+aiosqlite:///{database}", poolclass=NullPool)


async def write_links(database: Path, plans: tuple[LinkPlan, ...], restore_utc: datetime) -> list[Link]:
    """``plans`` written into ``database`` through A's ``token_service``: issued, then consumed or revoked, each at its
    time before ``restore_utc``; committed."""
    accounts = dict(cases.rows_of(database, "SELECT username, id FROM users"))
    engine = links_engine(database)
    links: list[Link] = []
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            for plan in plans:
                issued_at = restore_utc - plan.issued_before
                grants_admin = plan.purpose == AccountTokenPurpose.INVITE and plan.became == "valid"
                issued = await token_service.issue_token(session, plan.purpose, user_id=accounts[plan.account] if plan.account else None, email=f"{plan.name}@example.test", grants_admin=grants_admin, ttl=plan.ttl, now=issued_at)
                if plan.became == "consumed":
                    spent = await token_service.consume_token(session, issued.token, plan.purpose, consumed_by_user_id=accounts[plan.account or CONFIRMED_BY], now=issued_at + ACTED_AFTER)
                    assert spent is not None, f"precondition: {plan.name} is consumed"
                elif plan.became == "revoked":
                    assert await token_service.revoke_tokens(session, token_id=issued.record.id, now=issued_at + ACTED_AFTER) == 1, f"precondition: {plan.name} is revoked"
                links.append(Link(plan=plan, token=issued.token, token_id=issued.record.id))
            await session.commit()
    finally:
        await engine.dispose()
    return links


async def read_links(database: Path, links: list[Link], at: datetime) -> dict[str, tuple[str, datetime | None]]:
    """Each link as A's ``token_service.inspect_token`` reads it at ``at``: its status, and its ``revoked_at`` as
    SQLAlchemy loads it."""
    engine = links_engine(database)
    try:
        async with AsyncSession(engine) as session:
            found: dict[str, tuple[str, datetime | None]] = {}
            for link in links:
                inspection = await token_service.inspect_token(session, link.token, link.plan.purpose, now=at)
                found[link.plan.name] = (inspection.status.value, inspection.record.revoked_at if inspection.record is not None else None)
            return found
    finally:
        await engine.dispose()


async def still_open(database: Path, links: list[Link], at: datetime) -> list[str]:
    """The links A's ``token_service.consume_token`` would spend at ``at``: tried, then rolled back."""
    engine = links_engine(database)
    try:
        async with AsyncSession(engine) as session:
            opened = [link.plan.name for link in links if await token_service.consume_token(session, link.token, link.plan.purpose, now=at) is not None]
            await session.rollback()
            return opened
    finally:
        await engine.dispose()


async def written(database: Path, plans: tuple[LinkPlan, ...], restore_utc: datetime) -> list[Link]:
    """``plans`` written into ``database`` and checked through A's reader, at the restore time: each what its plan says,
    the valid ones opening (rolled back). Left in rollback-journal mode: the file holds the whole database, and only
    reading it creates nothing beside it."""
    links = await write_links(database, plans, restore_utc)
    statuses = {name: status for name, (status, _revoked_at) in (await read_links(database, links, restore_utc)).items()}
    assert statuses == {link.plan.name: link.plan.became for link in links}, f"precondition: every link is what its plan says at the restore time: {statuses}"
    valid = [link.plan.name for link in links if link.plan.became == "valid"]
    assert await still_open(database, links, restore_utc) == valid, "barrier: before the restore, the valid links open and no other does (rolled back)"
    with closing(sqlite3.connect(database)) as conn:
        conn.execute("PRAGMA journal_mode=DELETE")
    return links


def rows_by_table(database: Path) -> dict[str, list[dict[str, Any]]]:
    """Every row of every table of ``database``, by column name, each table's rows in one order whatever the scan's."""
    with closing(cases.read_only(database)) as conn:
        names = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        found: dict[str, list[dict[str, Any]]] = {}
        for name in names:
            cursor = conn.execute(f'SELECT * FROM "{name}"')
            columns = [column[0] for column in cursor.description]
            found[name] = sorted((dict(zip(columns, row, strict=True)) for row in cursor.fetchall()), key=lambda row: repr(sorted(row.items())))
    return found


def with_changes(tables: dict[str, list[dict[str, Any]]], changes: dict[tuple[str, str], Callable[[dict[str, Any]], Any]]) -> dict[str, list[dict[str, Any]]]:
    """``tables`` with ``changes`` made: for (table, column), the new value of each row, from the row (``...``: kept)."""
    changed_tables = {name: [dict(row) for row in rows] for name, rows in tables.items()}
    for (table, column), value_of in changes.items():
        for row in changed_tables[table]:
            value = value_of(row)
            if value is not ...:
                row[column] = value
    return {name: sorted(rows, key=lambda row: repr(sorted(row.items()))) for name, rows in changed_tables.items()}


@pytest.mark.asyncio
@pytest.mark.parametrize("variant", RESTORE_TIMES)
async def test_the_commit_revokes_every_live_link_of_the_restored_database_at_the_restore_time(tmp_path, databases, checked, variant):
    """(h) An invitation, a password reset, an email verification or the admin setup still live in the backup would open
    the restored instance to whoever holds the link. At the commit, exactly the live ones, expired or not, get
    ``revoked_at`` = the restore time, as SQLAlchemy stores it (UTC, no offset, six digits); consumed and revoked links
    keep what they had; every other row of the restored database is as the check left it, but the session versions;
    A's ``token_service`` reads each formerly live link as revoked at the restore time, and none of them opens
    anything; no link of the database before enters the restored one. The count goes to the log, the state gains no
    field."""
    print_section("(h) The one-time links of the restored database")
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    now = restore_time_of(instance, variant)
    restore_utc = now.astimezone(UTC)
    restored_links = await written(instance.copy / DATABASE_ENTRY, RESTORED_LINKS, restore_utc)
    before_links = await written(instance.root / DATABASE_ENTRY, BEFORE_LINKS, restore_utc)
    snapshot = rows_by_table(instance.copy / DATABASE_ENTRY)
    confirm(apply, instance)
    boot = never_ran(apply)
    apply.apply_pending_restore(instance.root, boot=boot, now=instance.applied_at)
    with logs() as events:
        state = apply.finish_pending_restore(instance.root, boot=boot, now=now)
    assert (state.status, state.session_version) == ("committed", millis(now)), f"committed, every account at the restore time: {state.status}, {state.session_version}"
    database = instance.root / DATABASE_ENTRY
    stored = restore_utc.strftime(SQLALCHEMY_DATETIME)
    live_ids = {link.token_id for link in restored_links if link.live}
    revoked_at = dict(cases.rows_of(database, "SELECT id, revoked_at FROM account_tokens"))
    assert {token_id for token_id, value in revoked_at.items() if value == stored} == live_ids, f"exactly the live links revoked at the restore time, stored as {stored!r}: {revoked_at}"
    expected = with_changes(snapshot, {("users", "session_version"): lambda row: state.session_version, ("account_tokens", "revoked_at"): lambda row: stored if row["id"] in live_ids else ...})
    after = rows_by_table(database)
    assert after == expected, f"only the session versions and the live links' revoked_at changed: {[name for name in expected.keys() | after.keys() if expected.get(name) != after.get(name)]}"
    before_hashes = {token_service.hash_token(link.token) for link in before_links}
    assert before_hashes.isdisjoint(row[0] for row in cases.rows_of(database, "SELECT token_hash FROM account_tokens")), "no link of the database before enters the restored one"

    restored_naive = restore_utc.replace(tzinfo=None)
    read = await read_links(database, restored_links, restore_utc + timedelta(minutes=1))
    wanted = {link.plan.name: ("revoked", restored_naive) if link.live else ("consumed", None) if link.plan.became == "consumed" else ("revoked", (restore_utc - link.plan.issued_before + ACTED_AFTER).replace(tzinfo=None)) for link in restored_links}
    assert read == wanted, f"A's reader: every formerly live link revoked at the restore time (naive UTC), the others as they were: {read}"
    assert await still_open(database, restored_links, restore_utc + timedelta(minutes=1)) == [], "no link of the backup opens anything after the restore"

    counted = [event for event in events if event.get("event") != LOG_CANARY and any(value == LIVE_RESTORED and not isinstance(value, bool) for key, value in event.items() if key not in ("event", "log_level"))]
    assert counted, f"the count of links revoked ({LIVE_RESTORED}) is logged, as a field of an event of the commit: {events}"
    assert set(json.loads(state_file(instance.root).read_text(encoding="utf-8"))) == set(apply.RestoreState.model_fields) == STATE_FIELDS, "the state gains no field: the count goes to the log only"
    print_success(f"{variant}: {len(live_ids)} live links revoked at {stored}")


# -----------------------------------------------------------------------------
# (h) Lot B5-1d: the token watermark. A link the same start issues before the commit (admin-bootstrap's /setup link on a
# restore whose data has no account at all) is not the backup's: only the tokens the SWAPPED database held are revoked
# -----------------------------------------------------------------------------

#: A moment far from the restore, either side: ``created_at`` is written by whoever prepared the backup (or by the clock
#: of the start), so the criterion to keep a token is its id against the watermark, never its date.
FAR_FUTURE = datetime(2126, 1, 1, tzinfo=UTC)
FAR_PAST = datetime(2001, 1, 1, tzinfo=UTC)
#: The id of a token of the backup, far above the others: the watermark is exactly it.
HUGE_TOKEN_ID = 1_000_000


def put_token(database: Path, name: str, *, created_at: datetime, token_id: int | None = None, user_id: int | None = None, consumed: bool = False, revoked: bool = False) -> int:
    """One ``account_tokens`` row written by hand with sqlite3 (an invitation: no account needed), its id returned. The hash
    is the SHA-256 of ``name``; ``consumed`` / ``revoked`` ``ACTED_AFTER`` its issue. Stored as SQLAlchemy stores a datetime."""

    def stored(moment: datetime) -> str:
        return moment.astimezone(UTC).replace(tzinfo=None).isoformat(sep=" ", timespec="microseconds")

    acted = stored(created_at + ACTED_AFTER)
    with closing(sqlite3.connect(database)) as conn, conn:
        cursor = conn.execute(
            "INSERT INTO account_tokens (id, purpose, token_hash, user_id, email, grants_admin, created_at, expires_at, consumed_at, revoked_at) VALUES (?, 'invite', ?, ?, ?, 0, ?, ?, ?, ?)",
            (token_id, hashlib.sha256(name.encode()).hexdigest(), user_id, f"{name}@example.test", stored(created_at), stored(created_at + timedelta(days=1)), acted if consumed else None, acted if revoked else None),
        )
        return int(cursor.lastrowid)


def token_rows(database: Path) -> dict[int, tuple[str | None, str | None]]:
    """Each token's (consumed_at, revoked_at) by id."""
    return {token_id: (consumed_at, revoked_at) for token_id, consumed_at, revoked_at in cases.rows_of(database, "SELECT id, consumed_at, revoked_at FROM account_tokens")}


def revoked_count_logged(events: list[dict[str, Any]]) -> list[Any]:
    return [event["links_revoked"] for event in events if "links_revoked" in event]


def raw_state(instance: Instance) -> dict[str, Any]:
    return json.loads(state_file(instance.root).read_text(encoding="utf-8"))


def backup_tokens_into(instance: Instance, *, with_users: bool = True) -> dict[str, int]:
    """The tokens of the backup, in the checked copy before the restore: a live one now, a live one dated in the FUTURE, a
    live one with the largest id (``HUGE_TOKEN_ID``, dated in the future), a consumed and a revoked one. Their ids by name."""
    database = instance.copy / DATABASE_ENTRY
    when = instance.report.staged_at
    ids = {
        "live": put_token(database, "b5d-live", created_at=when),
        "live-future": put_token(database, "b5d-live-future", created_at=FAR_FUTURE),
        "consumed": put_token(database, "b5d-consumed", created_at=when - timedelta(days=3), consumed=True),
        "revoked": put_token(database, "b5d-revoked", created_at=when - timedelta(days=2), revoked=True),
        "live-huge-id": put_token(database, "b5d-live-huge", created_at=FAR_FUTURE, token_id=HUGE_TOKEN_ID),
    }
    with closing(sqlite3.connect(database)) as conn:
        conn.execute("PRAGMA journal_mode=DELETE")
    return ids


def bootstrap_after_the_swap(instance: Instance, created_at: datetime, name: str = "b5d-bootstrap") -> tuple[int, int]:
    """What ``admin-bootstrap`` does in the same start, between the swap and the commit: an administrator and the /setup
    link for it, written into the swapped database. (the user's id, the token's id)"""
    database = instance.root / DATABASE_ENTRY
    cases.add_accounts(database, [(f"{name}_admin", 1, 1)])
    user_id = cases.rows_of(database, f"SELECT id FROM users WHERE username = '{name}_admin'")[0][0]
    return user_id, put_token(database, name, created_at=created_at, user_id=user_id)


def swapped(apply: Any, instance: Instance) -> Any:
    """``confirm_restore`` then ``apply_pending_restore`` in this boot: the ``applied`` state."""
    confirm(apply, instance)
    state = apply.apply_pending_restore(instance.root, boot=never_ran(apply), now=instance.applied_at)
    assert state is not None and state.status == "applied", f"precondition: the swap is applied: {state}"
    return state


def _no_table(database: Path) -> None:
    """A backup database without ``account_tokens``: a database of before the table, with only a ``users``."""
    database.unlink()
    with closing(sqlite3.connect(database)) as conn, conn:
        conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, session_version INTEGER NOT NULL DEFAULT 0)")


def _unreadable(database: Path) -> None:
    database.write_bytes(b"this is not a SQLite database " * 64)


@pytest.mark.asyncio
@pytest.mark.parametrize("shape", ["restored-links", "no-tokens", "no-table", "unreadable"])
async def test_the_swap_records_the_largest_token_id_of_the_backup_as_the_watermark(tmp_path, databases, checked, shape):
    """(h) B5-1d: ``apply_pending_restore`` records ``token_watermark`` in the ``applied`` state, in ``restore.json`` too: the
    largest ``account_tokens.id`` of the swapped database (an int); ``0`` when the backup has no token or no table; ``None``
    when the database cannot be read (fail closed). Read from the swapped database only, never from the state or the clock."""
    print_section(f"(h) B5-1d token watermark: {shape}")
    apply = apply_module()
    assert "token_watermark" in apply.RestoreState.model_fields, "[new] B5-1d: RestoreState.token_watermark (int | None, default None)"
    instance = build(tmp_path / "instance", databases, checked)
    database = instance.copy / DATABASE_ENTRY
    if shape == "restored-links":
        links = await written(database, RESTORED_LINKS, instance.report.staged_at)
        expected: int | None = max(link.token_id for link in links)
        assert cases.rows_of(database, "SELECT MAX(id) FROM account_tokens") == [(expected,)], "precondition: the largest id of the backup"
    elif shape == "no-tokens":
        assert cases.rows_of(database, "SELECT COUNT(*) FROM account_tokens") == [(0,)], "precondition: the backup holds no token"
        expected = 0
    elif shape == "no-table":
        _no_table(database)
        expected = 0
    else:
        _unreadable(database)
        expected = None
    state = swapped(apply, instance)
    assert state.token_watermark == expected, f"{shape}: the watermark in the state returned: {state.token_watermark!r}, not {expected!r}"
    assert raw_state(instance).get("token_watermark", "<missing>") == expected, f"{shape}: and in restore.json: {raw_state(instance)}"
    assert apply.read_restore(instance.root).token_watermark == expected, f"{shape}: and in what read_restore reads"
    print_success(f"{shape}: watermark {expected!r}")


def test_a_state_has_no_watermark_until_the_swap(tmp_path, databases, checked):
    """(h) B5-1d: a confirmed restore not yet applied holds ``token_watermark`` ``None``: only the swap sets it."""
    apply = apply_module()
    assert "token_watermark" in apply.RestoreState.model_fields, "[new] B5-1d: RestoreState.token_watermark (int | None, default None)"
    instance = build(tmp_path / "instance", databases, checked)
    state = confirm(apply, instance)
    assert state.token_watermark is None, f"pending: no watermark: {state.token_watermark!r}"
    print_success("pending: None")


@pytest.mark.parametrize(
    "created_at",
    [pytest.param(FAR_FUTURE, id="issued-in-the-far-future"), pytest.param(FAR_PAST, id="issued-in-the-far-past"), pytest.param(None, id="issued-at-the-restore-time")],
)
def test_a_token_the_same_start_issues_after_the_swap_survives_the_commit(tmp_path, databases, checked, created_at):
    """(h) B5-1d: a token written into the swapped database between the swap and the commit (admin-bootstrap's /setup link)
    has an id above the watermark: ``revoked_at`` stays ``NULL`` whatever its ``created_at`` says; the backup's live tokens
    are revoked. Every account still gets the restore time as its session version."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    backup = backup_tokens_into(instance)
    now = restore_time_of(instance, "utc")
    state = swapped(apply, instance)
    assert state.token_watermark == HUGE_TOKEN_ID, f"precondition: the watermark is the backup's largest id: {state.token_watermark!r}"
    _user, issued = bootstrap_after_the_swap(instance, created_at or now)
    assert issued > state.token_watermark, f"precondition: the new token is above the watermark: {issued} / {state.token_watermark}"
    with logs() as events:
        committed = apply.finish_pending_restore(instance.root, boot=never_ran(apply), now=now)
    assert committed.status == "committed" and committed.session_version == millis(now), f"committed, every account at the restore time: {committed}"
    rows = token_rows(instance.root / DATABASE_ENTRY)
    assert rows[issued] == (None, None), f"the token this start issued is untouched: {rows[issued]}"
    stored = now.astimezone(UTC).strftime(SQLALCHEMY_DATETIME)
    assert [rows[backup[name]][1] for name in ("live", "live-future", "live-huge-id")] == [stored] * 3, f"the backup's live tokens revoked at the restore time: {rows}"
    assert revoked_count_logged(events) == [3], f"links_revoked counts only what was revoked: {revoked_count_logged(events)}"
    print_success("a token above the watermark survives")


@pytest.mark.parametrize("created_at", [pytest.param(FAR_FUTURE, id="issued-in-the-far-future"), pytest.param(FAR_PAST, id="issued-in-the-far-past")])
def test_a_restore_whose_data_has_no_account_keeps_the_bootstrap_link(tmp_path, databases, checked, created_at):
    """(h) B5-1d, the case: the restored data has no account and no token; the start's admin-bootstrap then creates the
    first administrator and its /setup link before the commit. The watermark is ``0``, the link survives the commit and
    nothing was counted as revoked; the administrator gets the restore time as its session version."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    database = instance.copy / DATABASE_ENTRY
    cases.execute(database, "DELETE FROM users", "DELETE FROM account_tokens")
    now = restore_time_of(instance, "utc")
    state = swapped(apply, instance)
    assert state.token_watermark == 0, f"no token in the backup: the watermark is 0: {state.token_watermark!r}"
    user_id, issued = bootstrap_after_the_swap(instance, created_at)
    with logs() as events:
        committed = apply.finish_pending_restore(instance.root, boot=never_ran(apply), now=now)
    assert committed.status == "committed", f"committed: {committed}"
    assert token_rows(instance.root / DATABASE_ENTRY) == {issued: (None, None)}, "the /setup link of the first administrator is live"
    assert cases.rows_of(instance.root / DATABASE_ENTRY, f"SELECT session_version FROM users WHERE id = {user_id}") == [(millis(now),)], "its session version is the restore time"
    assert revoked_count_logged(events) == [0], f"nothing revoked: {revoked_count_logged(events)}"
    print_success("no account in the backup: the bootstrap link lives")


def test_the_commit_revokes_the_backup_s_live_tokens_even_when_planted_to_look_new(tmp_path, databases, checked):
    """(h) B5-1d, security: the criterion comes from this process (the id against the watermark), never from the restored
    database. Live tokens of the backup — one with a ``created_at`` in the future, one with the largest id (equal to the
    watermark) — are revoked at the restore time; the consumed one and the one revoked before keep what they had."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    backup = backup_tokens_into(instance)
    before = token_rows(instance.copy / DATABASE_ENTRY)
    now = restore_time_of(instance, "utc")
    swapped(apply, instance)
    with logs() as events:
        apply.finish_pending_restore(instance.root, boot=never_ran(apply), now=now)
    rows = token_rows(instance.root / DATABASE_ENTRY)
    stored = now.astimezone(UTC).strftime(SQLALCHEMY_DATETIME)
    live = ("live", "live-future", "live-huge-id")
    assert {name: rows[backup[name]][1] for name in live} == dict.fromkeys(live, stored), f"live, future-dated and largest-id tokens revoked at the restore time: {rows}"
    assert rows[backup["consumed"]] == before[backup["consumed"]] and rows[backup["revoked"]] == before[backup["revoked"]], f"consumed and already revoked tokens untouched: {rows}"
    assert rows[backup["consumed"]][1] is None and rows[backup["revoked"]][1] is not None, "precondition: they differ in what they had"
    assert revoked_count_logged(events) == [len(live)], f"links_revoked counts only what was revoked: {revoked_count_logged(events)}"
    print_success("the backup's live tokens revoked, planted dates or not")


@pytest.mark.parametrize("created_at", [pytest.param(FAR_FUTURE, id="issued-in-the-far-future"), pytest.param(None, id="issued-at-the-restore-time")])
def test_a_state_without_a_watermark_revokes_every_live_token_as_before(tmp_path, databases, checked, created_at):
    """(h) B5-1d: an ``applied`` state written without the key (as an older server leaves it) reads ``token_watermark``
    ``None``: the commit revokes every live token of the database, one issued after the swap included."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    backup = backup_tokens_into(instance)
    now = restore_time_of(instance, "utc")
    swapped(apply, instance)
    record = raw_state(instance)
    assert "token_watermark" in record, "[new] B5-1d: the swap wrote token_watermark (the next lines remove it by hand)"
    del record["token_watermark"]
    state_file(instance.root).write_text(json.dumps(record), encoding="utf-8")
    state_file(instance.root).chmod(0o600)
    assert apply.read_restore(instance.root).token_watermark is None, "a state without the key reads None"
    _user, issued = bootstrap_after_the_swap(instance, created_at or now)
    with logs() as events:
        apply.finish_pending_restore(instance.root, boot=never_ran(apply), now=now)
    rows = token_rows(instance.root / DATABASE_ENTRY)
    stored = now.astimezone(UTC).strftime(SQLALCHEMY_DATETIME)
    revoked = {token_id for token_id, (_consumed, revoked_at) in rows.items() if revoked_at == stored}
    assert revoked == {backup["live"], backup["live-future"], backup["live-huge-id"], issued}, f"every live token revoked, the new one too: {rows}"
    assert revoked_count_logged(events) == [4], f"links_revoked: {revoked_count_logged(events)}"
    print_success("no watermark: all live tokens revoked")


def test_an_unreadable_database_at_the_swap_fails_closed_at_the_commit(tmp_path, databases, checked):
    """(h) B5-1d: the watermark is ``None`` when the swapped database could not be read; the commit then revokes every live
    token (here, the database became readable again before the commit: a copy of the backup's, with a token issued after)."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    _unreadable(instance.copy / DATABASE_ENTRY)
    swapped(apply, instance)
    assert raw_state(instance).get("token_watermark", "<missing>") is None, "precondition: the swap could not read the database: None"
    database = instance.root / DATABASE_ENTRY
    shutil.copyfile(databases.head, database)
    now = restore_time_of(instance, "utc")
    issued = put_token(database, "b5d-after", created_at=now)
    with logs() as events:
        apply.finish_pending_restore(instance.root, boot=never_ran(apply), now=now)
    stored = now.astimezone(UTC).strftime(SQLALCHEMY_DATETIME)
    assert token_rows(database)[issued][1] == stored, "no watermark: the live token is revoked"
    assert revoked_count_logged(events) == [1], f"links_revoked: {revoked_count_logged(events)}"
    print_success("unreadable at the swap: fail closed")


@pytest.mark.asyncio
async def test_close_the_way_in_answers_the_value_and_the_count_and_only_reads_the_database_before(tmp_path, databases, checked):
    """(h) ``apply._close_the_way_in(data_dir, now)`` on a swapped data directory: ``(max(R, A + 1, B + 1), the count)``;
    the database before, in ``previous/``, only read — its file byte for byte as it was, nothing beside it, its own live
    links still live."""
    apply = apply_module()
    assert hasattr(apply, "_close_the_way_in"), "[new] the commit's work on the restored database is apply._close_the_way_in(data_dir, now) -> (value, revoked_count) (contract)"
    instance = build(tmp_path / "instance", databases, checked)
    now = restore_time_of(instance, "utc")
    await written(instance.copy / DATABASE_ENTRY, RESTORED_LINKS, now)
    await written(instance.root / DATABASE_ENTRY, BEFORE_LINKS, now)
    confirm(apply, instance)
    apply.apply_pending_restore(instance.root, boot=never_ran(apply), now=instance.applied_at)
    kept = previous_of(instance.root) / "sqlite"
    before = tree(kept)
    assert before is not None and "app.db" in before, f"precondition: the database before is in previous/: {before}"
    outcome = apply._close_the_way_in(instance.root, now)
    assert outcome == (millis(now), LIVE_RESTORED), f"(the session value, the links revoked): {outcome}"
    assert tree(kept) == before, f"the database before is only read: {cases.changed(before, tree(kept) or {})}"
    assert cases.rows_of(kept / "app.db", "SELECT count(*) FROM account_tokens WHERE revoked_at IS NULL") == [(len(BEFORE_LINKS),)], "its own links still live"
    stored = now.strftime(SQLALCHEMY_DATETIME)
    assert cases.rows_of(instance.root / DATABASE_ENTRY, f"SELECT count(*) FROM account_tokens WHERE revoked_at = '{stored}'") == [(LIVE_RESTORED,)], "the count is the rows revoked"
    print_success(f"({millis(now)}, {LIVE_RESTORED}); the database before byte for byte")


@pytest.mark.asyncio
@pytest.mark.parametrize(("table", "column"), [("account_tokens", "revoked_at"), ("users", "session_version")], ids=["the-links-refused", "the-sessions-refused"])
async def test_the_links_and_the_sessions_change_together_or_not_at_all(tmp_path, databases, checked, table, column):
    """(h) One transaction: a trigger of the restored database refuses one of the two updates (whichever the product
    makes first, one of the two cases refuses the second); then neither the links nor the session versions changed.
    Whether the refusal reaches the caller is not this test's question."""
    apply = apply_module()
    assert hasattr(apply, "_close_the_way_in"), "[new] the commit's work on the restored database is apply._close_the_way_in(data_dir, now) -> (value, revoked_count) (contract)"
    instance = build(tmp_path / "instance", databases, checked)
    now = restore_time_of(instance, "utc")
    await written(instance.copy / DATABASE_ENTRY, RESTORED_LINKS, now)
    confirm(apply, instance)
    apply.apply_pending_restore(instance.root, boot=never_ran(apply), now=instance.applied_at)
    database = instance.root / DATABASE_ENTRY
    cases.execute(database, f"CREATE TRIGGER b3_refused BEFORE UPDATE OF {column} ON {table} BEGIN SELECT RAISE(ABORT, 'refused by the test'); END")
    with pytest.raises(sqlite3.DatabaseError):
        cases.execute(database, f"UPDATE {table} SET {column} = {column}")
    snapshot = rows_by_table(database)
    try:
        outcome: object = apply._close_the_way_in(instance.root, now)
    except Exception as exc:  # whether the refusal reaches the caller is not this test's question
        outcome = exc
    assert rows_by_table(database) == snapshot, f"{table}.{column} refused: neither the links nor the session versions may have changed ({outcome!r})"
    print_success(f"{table}.{column} refused: nothing changed")


# =============================================================================
# (i) §3 Sessions on the restored database
# =============================================================================


def active_accounts(database: Path) -> dict[str, int]:
    """The active accounts of ``database``, their ids by user name: an inactive one is refused before its version."""
    return dict(cases.rows_of(database, "SELECT username, id FROM users WHERE is_active = 1"))


async def signs_in(engine: AsyncEngine, user_id: int, version: int) -> bool:
    return sessions._signed_in_as(await sessions._current_user(engine, sessions._cookie(user_id, version)), user_id)


async def assert_only_a_login_signs_in(database: Path, held: set[int], value: int) -> None:
    """On the restored database, for every active account: a login (a cookie issued at the account's version now) signs
    in; a cookie at any version either database held is refused, «Session expired or invalid»."""
    assert value not in held, f"precondition: the value {value} is none a database held"
    engine = create_async_engine(f"sqlite+aiosqlite:///{database}", poolclass=NullPool)
    try:
        for username, user_id in active_accounts(database).items():
            account = await sessions._account(engine, username)
            assert account.session_version == value, f"{username}: at {account.session_version}, not {value}"
            login = await sessions._current_user(engine, auth_service.create_jwt_token(user_id, 1, account.session_version))
            assert sessions._signed_in_as(login, user_id), f"{username}: a login after the restore signs in: {sessions._describe(login)}"
            for version in sorted(held):
                outcome = await sessions._current_user(engine, sessions._cookie(user_id, version))
                assert sessions._refusal(outcome) == sessions.SESSION_EXPIRED, f"{username}: a cookie at {version}, a version a database held, must be refused: {sessions._describe(outcome)}"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize(("before_ahead", "restored_ahead", "above"), SESSION_VALUES[:3])
async def test_after_a_restore_no_cookie_of_either_database_signs_in_and_a_login_does(tmp_path, databases, checked, before_ahead, restored_ahead, above):
    """(i) Decision 40, case 1: with the clock ahead of both databases, or behind the one before (an account at
    R + 5000), or behind the restored one (R + 9), every account ends at ``max + 1`` or R, and no cookie at any version
    either database held signs in: neither the live instance's nor the backup's, whatever account id it carries."""
    print_section("(i) Sessions after a restore")
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    state, held = committed_with(apply, instance, before_ahead, restored_ahead)
    value = millis(instance.committed_at) + above
    assert (state.status, state.session_version) == ("committed", value), f"R + {above}: {state.session_version}"
    await assert_only_a_login_signs_in(instance.root / DATABASE_ENTRY, held, value)
    print_success(f"R + {above}: {len(held)} versions refused, a login accepted")


@pytest.mark.asyncio
@pytest.mark.parametrize("clock", ["forward", "back"])
async def test_a_restore_on_top_of_a_committed_restore_puts_every_account_above_both_histories(tmp_path, databases, checked, clock):
    """(i) Decision 40, case 2. A first restore, committed: every account at R1. Then a backup taken from an instance
    that was itself restored three days earlier (its versions that restore's milliseconds, one more for an account whose
    password changed since) is restored on top. The clock forward (R2 = R1 + 2 h) or back (R2 = R1 - 1 h): every
    account strictly above every value of both histories; the cookies of both refused."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    database = instance.root / DATABASE_ENTRY
    first_history = held_versions(database) | held_versions(instance.copy / DATABASE_ENTRY)
    confirm(apply, instance)
    apply.apply_pending_restore(instance.root, boot=never_ran(apply), now=instance.applied_at)
    first = apply.finish_pending_restore(instance.root, boot=never_ran(apply), now=instance.committed_at)
    assert (first.status, set(versions_of(database).values())) == ("committed", {first.session_version}), "precondition: the first restore committed, every account at its value"
    earlier = millis(instance.committed_at - timedelta(days=3))
    add_stage(instance, checked, OTHER_STAGE)
    second_copy = stage_dir(instance.root, OTHER_STAGE) / STAGE_DATA_FOLDER / DATABASE_ENTRY
    set_versions(second_copy, {**dict.fromkeys(BACKUP_VERSIONS, earlier), "ada_admin": earlier + 1})
    second_history = set(versions_of(second_copy).values())
    second_at = instance.committed_at + (timedelta(hours=2) if clock == "forward" else -timedelta(hours=1))
    confirm(apply, instance, OTHER_STAGE, now=second_at - timedelta(minutes=1))
    apply.apply_pending_restore(instance.root, boot=never_ran(apply, 1), now=second_at)
    second = apply.finish_pending_restore(instance.root, boot=never_ran(apply, 1), now=second_at)
    expected = millis(second_at) if clock == "forward" else first.session_version + 1
    held = first_history | {first.session_version} | second_history
    assert (second.status, second.session_version) == ("committed", expected), f"clock {clock}: {second.session_version}, not {expected}"
    assert expected > max(held), "strictly above every value either history held"
    assert versions_of(database) == dict.fromkeys(BACKUP_VERSIONS, expected), "every account at the new value"
    await assert_only_a_login_signs_in(database, held, expected)
    print_success(f"clock {clock}: {expected - first.session_version:+} from the first restore's value")


@pytest.mark.asyncio
async def test_a_password_change_after_the_restore_raises_that_account_alone_by_one(tmp_path, databases, checked):
    """(i) Decision 40, case 3: ``user_service.end_sessions`` (a password change) after the commit raises the account
    to value + 1: its cookie at the value refused, at value + 1 accepted; the other accounts untouched at the value."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    state, _held = committed_with(apply, instance, {}, {})
    value = state.session_version
    database = instance.root / DATABASE_ENTRY
    accounts = active_accounts(database)
    engine = create_async_engine(f"sqlite+aiosqlite:///{database}", poolclass=NullPool)
    try:
        signed = {username: await signs_in(engine, user_id, value) for username, user_id in accounts.items()}
        assert all(signed.values()), f"barrier: every account's cookie at the restore's value signs in: {signed}"
        await sessions._end_sessions_of(engine, accounts["ada_admin"])
        assert versions_of(database) == {**dict.fromkeys(BACKUP_VERSIONS, value), "ada_admin": value + 1}, f"ada one higher, nobody else: {versions_of(database)}"
        refused = await sessions._current_user(engine, sessions._cookie(accounts["ada_admin"], value))
        assert sessions._refusal(refused) == sessions.SESSION_EXPIRED, f"ada's cookie at the value is refused: {sessions._describe(refused)}"
        assert await signs_in(engine, accounts["ada_admin"], value + 1), "ada's cookie at value + 1 signs in"
        others = {username: await signs_in(engine, user_id, value) for username, user_id in accounts.items() if username != "ada_admin"}
        assert all(others.values()), f"the other accounts still sign in at the value: {others}"
    finally:
        await engine.dispose()
    print_success("ada value + 1, the others at the value")


# =============================================================================
# (j) §7 The startup steps
# =============================================================================


def assert_in_relative_order(steps: Any, expected: tuple[str, ...], why: str = "") -> None:
    """``expected`` among the names of ``steps``, in this relative order, any other step before, between or after: what
    ``test_app_lifecycle.assert_in_relative_order`` checks. Not imported from there: that module imports
    ``backend.app.main``, whose ``configure_logging()`` writes a log in the configured data directory (here a folder that
    must stay absent; at the top of this module, the lane's). ``why``, the reason for the order, ends the message of a
    failure."""
    names = [step.name for step in steps]
    because = f". Why: {why}" if why else ""
    missing = [name for name in expected if name not in names]
    assert not missing, f"[new] {missing} missing from STARTUP_STEPS: {names}{because}"
    positions = [names.index(name) for name in expected]
    assert positions == sorted(positions), f"{list(expected)} must keep this relative order, found {[names[position] for position in sorted(positions)]} in {names}{because}"


def test_the_restore_steps_stand_where_the_contract_puts_them():
    """(j) ``pending-restore`` before anything opens the data (``data-directories``, the database); ``serving-lock``
    right after the folders exist and before any step reads a swapped folder (``risk-scenarios`` reads
    ``scenario_catalog/``, ``default-avatars`` writes ``custom-uploads/``) or the database: a process holds it before it
    reads any data, so a start never undoes a restore under a process that read it; ``restore-commit`` once the restored
    database is migrated and fixed and ``admin-bootstrap`` has run (decision N57), before anything runs in the
    background. The bootstrap reads and writes the restored data (it counts the accounts, may create the pending
    administrator, sets ``registration_mode`` to invitations only) and can raise on a data error: before
    ``restore-commit`` such a failure rolls the restore back at the next start (``first_start_failed``); after it, the
    restore would already be kept and the server would fall at every start. Relative only: ``test_admin_bootstrap.py``
    (STEP-001) pins ``admin-bootstrap`` right after ``global-settings``. Lot B4b, N66: ``backup-leftovers`` after
    ``restore-commit``: the leftovers are removed once the restore is settled, and since a step that raises after
    ``restore-commit`` would stop every start, that one never raises."""
    print_section("(j) The startup steps")
    from backend.app.services.platform import app_lifespan  # noqa: PLC0415 — the app's whole startup: kept out of the spawn children that import this module

    assert_in_relative_order(app_lifespan.STARTUP_STEPS, ("tool-catalog", "pending-restore", "data-directories"))
    assert_in_relative_order(app_lifespan.STARTUP_STEPS, ("pending-restore", "data-directories", "serving-lock", "risk-scenarios"))
    assert_in_relative_order(app_lifespan.STARTUP_STEPS, ("serving-lock", "database"))
    assert_in_relative_order(app_lifespan.STARTUP_STEPS, ("global-settings", "restore-commit", "provider-prewarm"))
    assert_in_relative_order(
        app_lifespan.STARTUP_STEPS,
        ("admin-bootstrap", "restore-commit"),
        why="admin-bootstrap reads and writes the restored data and can raise on a data error: before restore-commit the next start rolls the restore back (first_start_failed); after it, the restore would already be kept and the server would fall at every start",
    )
    assert_in_relative_order(
        app_lifespan.STARTUP_STEPS,
        ("restore-commit", "backup-leftovers"),
        why="the leftovers are removed once the restore is settled; after restore-commit a step that raises would stop every start, so this one never raises (N66)",
    )
    print_success("tool-catalog < pending-restore < data-directories < serving-lock < risk-scenarios; serving-lock < database; global-settings < restore-commit < provider-prewarm; admin-bootstrap < restore-commit; restore-commit < backup-leftovers")


@pytest.mark.asyncio
@pytest.mark.parametrize(("step_name", "function_name"), [("pending-restore", "apply_pending_restore"), ("restore-commit", "finish_pending_restore"), ("serving-lock", "hold_serving_lock")])
async def test_a_restore_step_reaches_its_function_through_the_module_when_its_awaitable_runs(step_name, function_name, monkeypatch):
    """(j) ``Step(name, lambda: asyncio.to_thread(<function>))``: ``run()`` returns the awaitable, the function is
    called when it is awaited — read from ``app_lifespan`` then, once, without arguments, in a worker thread (its file
    I/O and its ``flock`` must not block the loop). ``test_app_lifecycle``'s generic check closes the coroutine without
    awaiting it, so it would see no call: these three are awaited here. The real functions never run."""
    from backend.app.services.platform import app_lifespan  # noqa: PLC0415 — the app's whole startup: kept out of the spawn children that import this module

    assert hasattr(app_lifespan, function_name), f"[new] app_lifespan imports {function_name} (contract §7)"
    steps = [step for step in app_lifespan.STARTUP_STEPS if step.name == step_name]
    assert len(steps) == 1, f"[new] one startup step {step_name!r}: {[step.name for step in app_lifespan.STARTUP_STEPS]}"
    calls: list[tuple[tuple, dict, int]] = []
    sentinel = object()

    def replacement(*args: Any, **kwargs: Any) -> object:
        calls.append((args, kwargs, threading.get_ident()))
        return sentinel

    monkeypatch.setattr(app_lifespan, function_name, replacement)
    outcome = steps[0].run()
    assert inspect.isawaitable(outcome), f"{step_name}: run() returns the awaitable of asyncio.to_thread, not {outcome!r}"
    result = await outcome
    assert [(args, kwargs) for args, kwargs, _thread in calls] == [((), {})], f"{step_name}: app_lifespan.{function_name} called once, without arguments, when the awaitable runs: {calls}"
    assert calls[0][2] != threading.get_ident(), f"{step_name}: called in a worker thread, off the event loop"
    assert result is sentinel, f"{step_name}: the step's result is the function's"
    print_success(f"{step_name} → app_lifespan.{function_name}(), in a thread")


# =============================================================================
# (k) §4 restart.py
# =============================================================================


def test_the_server_of_a_process_multiprocessing_did_not_start_is_that_process():
    print_section("(k) restart.py")
    restart = restart_module()
    assert multiprocessing.parent_process() is None, "precondition: this test runs in a process multiprocessing did not start"
    assert restart.server_pid() == os.getpid(), f"no parent: this process, {os.getpid()}, not {restart.server_pid()}"
    print_success(f"server_pid() = {os.getpid()}")


def test_a_worker_whose_server_died_is_its_own_server(monkeypatch):
    """(k)(c) §10 The parent counts only while it is alive: the pid a dead master had may since belong to another
    process. A stand-in for ``multiprocessing.parent_process()``, as ``restart`` reads it: alive, its pid (the barrier:
    the stand-in reaches ``restart``); dead, this process — and so is the boot ``current_boot`` reads."""
    restart = restart_module()
    apply = apply_module()
    live, dead = SimpleNamespace(pid=NO_SUCH_PID, is_alive=lambda: True), SimpleNamespace(pid=NO_SUCH_PID, is_alive=lambda: False)
    monkeypatch.setattr(restart.multiprocessing, "parent_process", lambda: live)
    assert restart.server_pid() == NO_SUCH_PID, "barrier: a parent alive is the server"
    monkeypatch.setattr(restart.multiprocessing, "parent_process", lambda: dead)
    assert restart.server_pid() == os.getpid(), f"a parent no longer alive: this process, {os.getpid()}, not {restart.server_pid()}"
    assert apply.current_boot() == this_boot(apply), f"and the boot is this process's: {apply.current_boot()}"
    print_success(f"dead parent: server_pid() = {os.getpid()}")


def _the_server_a_worker_sees(results: Any) -> None:
    """Runs in a spawn child of the test process, as a uvicorn worker under its master: the server pid and the boot it
    reads, sent back, or what failed. Module level, so that the spawned interpreter imports it by name."""
    try:
        restart = importlib.import_module(RESTART)
        apply = importlib.import_module(APPLY)
        results.put({"pid": os.getpid(), "server_pid": restart.server_pid(), "boot": apply.current_boot().model_dump(mode="json")})
    except Exception as exc:  # sent back: the test reports it instead of waiting for an answer that never comes
        results.put({"error": f"{type(exc).__name__}: {exc}"})


def test_in_a_worker_process_the_server_and_its_boot_are_its_parents():
    """(c)(k) Under ``uvicorn --workers N`` (or its reloader) the server is the master: the parent of the worker."""
    apply = apply_module()
    restart_module()
    context = multiprocessing.get_context("spawn")
    results = context.Queue()
    worker = context.Process(target=_the_server_a_worker_sees, args=(results,), name="b3-server-pid", daemon=True)
    worker.start()
    try:
        [answer] = _answers(results, [worker])
    finally:
        _stop([worker])
    assert "error" not in answer, f"the worker failed: {answer}"
    assert answer["pid"] != os.getpid(), "precondition: the answer comes from the child"
    assert answer["server_pid"] == os.getpid(), f"a worker's server is its parent, {os.getpid()}: {answer['server_pid']}"
    assert answer["boot"] == this_boot(apply).model_dump(mode="json"), f"a worker's boot is its parent's: {answer['boot']}"
    print_success(f"server_pid() = {os.getpid()} in the worker")


def test_send_signal_is_os_kill_until_replaced():
    restart = restart_module()
    assert restart.send_signal is os.kill, f"send_signal is os.kill by default: {restart.send_signal!r}"
    print_success("send_signal is os.kill")


def test_request_restart_sends_sigterm_to_the_server_through_send_signal_read_when_it_runs(monkeypatch):
    """(k) No pid given: the server's (``server_pid``, read when it runs), SIGTERM, through ``restart.send_signal`` as it
    is when it runs; the pid returned, a warning logged. ``os.kill`` is replaced too: no real signal, whatever path."""
    restart = restart_module()
    sent: list[tuple[int, int]] = []
    killed_pids: list[tuple[int, int]] = []
    monkeypatch.setattr(os, "kill", lambda pid, signum: killed_pids.append((pid, signum)))
    monkeypatch.setattr(restart, "send_signal", lambda pid, signum: sent.append((pid, signum)))
    monkeypatch.setattr(restart, "server_pid", lambda: NO_SUCH_PID)
    with logs(RESTART) as events:
        pid = restart.request_restart()
    assert (pid, sent, killed_pids) == (NO_SUCH_PID, [(NO_SUCH_PID, signal.SIGTERM)], []), f"SIGTERM to the server through send_signal, its pid returned: {pid}, {sent}, os.kill {killed_pids}"
    assert a_warning(events), f"a restart is logged as a warning: {levels(events)}"
    print_success("SIGTERM → server_pid(), through send_signal")


def test_request_restart_with_a_pid_signals_that_pid(monkeypatch):
    restart = restart_module()
    sent: list[tuple[int, int]] = []
    killed_pids: list[tuple[int, int]] = []
    monkeypatch.setattr(os, "kill", lambda pid, signum: killed_pids.append((pid, signum)))
    monkeypatch.setattr(restart, "send_signal", lambda pid, signum: sent.append((pid, signum)))
    monkeypatch.setattr(restart, "server_pid", lambda: NO_SUCH_PID)
    assert restart.request_restart(pid=NO_SUCH_PID + 1) == NO_SUCH_PID + 1, "the pid given is returned"
    assert (sent, killed_pids) == ([(NO_SUCH_PID + 1, signal.SIGTERM)], []), f"SIGTERM to the pid given, not the server's: {sent}, os.kill {killed_pids}"
    print_success("SIGTERM → the pid given")


# =============================================================================
# (l) B2 then B3, with real archives
# =============================================================================


@pytest.mark.parametrize("archive", ["head_archive", "older_archive"])
def test_a_checked_backup_is_confirmed_applied_and_committed(tmp_path, databases, request, archive):
    """(l) ``stage_archive`` → ``confirm_restore`` → ``apply_pending_restore`` → ``finish_pending_restore``, on a live
    instance with data of its own. At the head, and at ``OLDER`` (the copy upgraded by a real ``alembic upgrade``):
    committed; the live database at the head with the rows the report's ``after`` says, its active administrators the
    report's, every account at the restore's value; the archive's files live, the instance's own gone; the copy,
    ``previous/`` and ``failed/`` gone; nothing else of the data directory touched."""
    print_section("(l) B2 then B3, real archives")
    apply = apply_module()
    built = request.getfixturevalue(archive)
    root = tmp_path / "instance"
    live_instance(root, databases, FULL)
    before = cases.fingerprint(root)
    report = stage_archive(built.path, root)
    assert (report.restorable, report.action) == (True, "same" if archive == "head_archive" else "upgrade"), f"precondition: {report.action}, {report.blockers}"
    confirm_at, applied_at, committed_at = (report.staged_at + timedelta(minutes=minutes) for minutes in (1, 10, 11))
    boot = never_ran(apply)
    pending = apply.confirm_restore(report.stage_id, confirmed_by="cli", data_dir=root, now=confirm_at)
    assert (pending.status, pending.action, pending.backup_created_at, pending.backup_app_version) == ("pending", report.action, report.backup.created_at, report.backup.app_version), f"{pending}"
    assert apply.apply_pending_restore(root, boot=boot, now=applied_at).status == "applied", "applied"
    committed = apply.finish_pending_restore(root, boot=boot, now=committed_at)
    assert (committed.status, committed.session_version) == ("committed", millis(committed_at)), f"{committed.status}, {committed.session_version}"
    database = root / DATABASE_ENTRY
    assert cases.revisions_of(database) == [cases.HEAD], f"the live database at the head: {cases.revisions_of(database)}"
    assert table_rows(database) == {name: rows.after for name, rows in report.tables.items() if rows.after is not None}, "the rows the check's report says"
    administrators = [row[0] for row in cases.rows_of(database, "SELECT username FROM users WHERE is_superuser = 1 AND is_active = 1 ORDER BY username")]
    assert administrators == report.administrators == cases.ADMINISTRATORS, f"the backup's administrators sign in after it: {administrators}"
    assert set(versions_of(database).values()) == {committed.session_version}, "every account at the restore's value"
    assert {entry: (root / entry).read_bytes() for entry in cases.FILES} == cases.FILES, "the archive's files live, byte for byte"
    assert not lexists(root / "custom-uploads" / "live-logo.png"), "the instance's own uploads replaced"
    left = [path.name for path in (stage_dir(root, report.stage_id), previous_of(root), failed_of(root)) if lexists(path)]
    assert (left, apply.protected_stage(root)) == ([], None), f"nothing of the restore left: {left}"
    assert cases.changed(outside(before), outside(cases.fingerprint(root))) == [], "nothing else of the data directory touched"
    print_success(f"{archive}: committed, {len(report.tables)} tables as the report said")


# =============================================================================
# (m) §11 P7: no restore on a blocked instance
# =============================================================================

#: Why a pending restore waits at a start: a backup running, another data directory (§2), another server process
#: serving it (§10), the hosting provider's block (§11).
WAIT_REASONS = {"backup_running", "other_data_directory", "server_running", "instance_blocked"}
#: What blocks the instance (``config.platform``: its words, in any case), and what does not (``None``: unset).
BLOCKING = ["true", "1", "yes", "ON"]
NOT_BLOCKING = [pytest.param("false", id="false"), pytest.param("0", id="0"), pytest.param(None, id="unset")]
#: A value ``instance_blocked()`` cannot read: it raises ``ValueError``.
UNREADABLE_BLOCK = "maybe"


def test_a_pending_restore_waits_for_one_of_four_reasons_the_block_among_them():
    """(m) §11: ``WaitReason`` gains ``instance_blocked``, beside the three of §2 and §10."""
    print_section("(m) §11 P7: no restore on a blocked instance")
    apply = apply_module()
    reasons = set(get_args(apply.WaitReason))
    assert reasons == WAIT_REASONS, f"[new] the reasons a pending restore waits for, instance_blocked among them (contract §11): {sorted(reasons)}"
    print_success(f"WaitReason: {', '.join(sorted(reasons))}")


@pytest.mark.parametrize("value", BLOCKING)
def test_on_a_blocked_instance_a_pending_restore_waits_and_the_first_start_unblocked_applies_it(tmp_path, databases, checked, monkeypatch, value):
    """(m) §11: a restore confirmed before the hosting provider blocked the instance is not applied while it is blocked.
    ``pending``, ``waiting = instance_blocked`` recorded in the state file, the rest of the state as it was confirmed;
    nothing moved, written or removed but the state — the data directory, the checked copy, its check, what
    ``.restore`` holds for other archives, what an earlier restore left in ``previous/`` and ``failed/`` (a swap removes
    those first); one warning, no error; the apply lock and the serving lock free once the step returned. The variable
    removed, the next start applies the restore and clears ``waiting``."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    confirmed = confirm(apply, instance)
    cases.write_files(previous_of(instance.root), {"custom-uploads/stale.png": b"set aside by an earlier restore"})
    cases.write_files(failed_of(instance.root), {"broker_reports/stale.csv": b"set aside by an earlier rollback"})
    monkeypatch.setenv(BLOCKED_VARIABLE, value)
    assert instance_blocked() is True, f"precondition: {BLOCKED_VARIABLE}={value!r} blocks the instance"
    data, kept = cases.fingerprint(instance.root), restore_items_but_the_state(instance.root)
    with moving(apply) as mover, logs() as events:
        state = apply.apply_pending_restore(instance.root, boot=never_ran(apply), now=instance.applied_at)
    assert (state.status, state.waiting) == ("pending", "instance_blocked"), f"{BLOCKED_VARIABLE}={value!r}: pending, waiting for the unblock: {state.status}, {state.waiting}"
    assert state == confirmed.model_copy(update={"waiting": "instance_blocked"}), f"the rest of the state as confirmed: no journal, no boot, nothing applied or finished: {state}"
    assert apply.read_restore(instance.root) == state, "the state on disk is the state returned"
    assert json.loads(state_file(instance.root).read_text(encoding="utf-8"))["waiting"] == "instance_blocked", "the reason is recorded in the state file"
    assert mover.calls == 0, f"nothing moved: {mover.moved}"
    assert cases.changed(data, cases.fingerprint(instance.root)) == [], "the data directory as it was"
    assert cases.changed(kept, restore_items_but_the_state(instance.root)) == [], ".restore as it was but the state: the copy, its check, what it holds for other archives, an earlier restore's previous/ and failed/; nothing new"
    assert said(events, INSTANCE_BLOCKED_WAITS) == ["warning"] and not an_error(events), f"one warning says that the restore waits for the unblock, and no error: {logged(events)}"
    assert (apply_lock_free(instance.root), serving_lock_free(instance.root)) == (True, True), "the apply lock and the serving lock are free once the step returned"
    monkeypatch.delenv(BLOCKED_VARIABLE)
    state = apply.apply_pending_restore(instance.root, boot=never_ran(apply), now=instance.committed_at)
    assert (state.status, state.waiting) == ("applied", None), f"unblocked: applied, no longer waiting: {state.status}, {state.waiting}"
    assert_swapped(instance)
    print_success(f"{BLOCKED_VARIABLE}={value!r}: instance_blocked, nothing moved; unblocked: applied")


def test_a_block_that_cannot_be_read_counts_as_blocked_and_an_error_says_so(tmp_path, databases, checked, monkeypatch):
    """(m) §11: a ``LIBREFOLIO_BLOCKED`` that ``instance_blocked()`` cannot read (``ValueError``) counts as blocked —
    fail closed: the startup checks stop the server on it anyway. The step does not raise: ``pending``, ``waiting =
    instance_blocked`` recorded, nothing moved or removed, an error logged, both locks free."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    confirm(apply, instance)
    monkeypatch.setenv(BLOCKED_VARIABLE, UNREADABLE_BLOCK)
    with pytest.raises(ValueError, match=BLOCKED_VARIABLE):  # precondition: the configuration cannot read it
        instance_blocked()
    data, kept = cases.fingerprint(instance.root), restore_items_but_the_state(instance.root)
    with moving(apply) as mover, logs() as events:
        try:
            state = apply.apply_pending_restore(instance.root, boot=never_ran(apply), now=instance.applied_at)
        except ValueError as exc:
            pytest.fail(f"{BLOCKED_VARIABLE}={UNREADABLE_BLOCK!r} must not stop the step: it counts as blocked ({exc})")
    assert (state.status, state.waiting) == ("pending", "instance_blocked"), f"{BLOCKED_VARIABLE}={UNREADABLE_BLOCK!r}: counted as blocked: {state.status}, {state.waiting}"
    assert apply.read_restore(instance.root) == state, "the reason is recorded in the state file"
    assert mover.calls == 0, f"nothing moved: {mover.moved}"
    assert (cases.changed(data, cases.fingerprint(instance.root)), cases.changed(kept, restore_items_but_the_state(instance.root))) == ([], []), "nothing written or removed but the state"
    assert an_error(events), f"an error says that the value cannot be read: {logged(events)}"
    assert (apply_lock_free(instance.root), serving_lock_free(instance.root)) == (True, True), "both locks free once the step returned"
    print_success(f"{BLOCKED_VARIABLE}={UNREADABLE_BLOCK!r}: instance_blocked, an error logged")


@pytest.mark.parametrize("value", NOT_BLOCKING)
def test_on_an_instance_that_is_not_blocked_a_pending_restore_is_applied_as_before(tmp_path, databases, checked, monkeypatch, value):
    """(m) §11: ``false``, ``0``, or no ``LIBREFOLIO_BLOCKED`` at all — every install its hosting provider does not
    block: the swap, as before P7; nothing says that the restore waits."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    confirm(apply, instance)
    described = f"{BLOCKED_VARIABLE} unset" if value is None else f"{BLOCKED_VARIABLE}={value!r}"
    if value is None:
        monkeypatch.delenv(BLOCKED_VARIABLE, raising=False)
    else:
        monkeypatch.setenv(BLOCKED_VARIABLE, value)
    assert instance_blocked() is False, f"precondition: {described} does not block the instance"
    with logs() as events:
        state = apply.apply_pending_restore(instance.root, boot=never_ran(apply), now=instance.applied_at)
    assert (state.status, state.waiting) == ("applied", None), f"{described}: applied: {state.status}, {state.waiting}"
    assert_swapped(instance)
    assert said(events, INSTANCE_BLOCKED_WAITS) == [], f"nothing says that the restore waits: {logged(events)}"
    print_success(f"{described}: applied")


def test_on_a_blocked_instance_a_restore_confirmed_for_another_data_directory_says_so_first(tmp_path, databases, checked, monkeypatch):
    """(m) §11, the order, 1: a copy of the data directory never applies the restore, blocked or not.
    ``other_data_directory`` comes first: it is what is recorded, with the warning of §2 and not the block's; nothing
    moved."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    confirmed = confirm(apply, instance)
    elsewhere = tmp_path / "mounted-elsewhere"
    instance.root.rename(elsewhere)
    monkeypatch.setenv(BLOCKED_VARIABLE, "true")
    data, kept = cases.fingerprint(elsewhere), restore_items_but_the_state(elsewhere)
    with moving(apply) as mover, logs() as events:
        state = apply.apply_pending_restore(elsewhere, boot=never_ran(apply), now=instance.applied_at)
    assert (state.status, state.waiting, state.data_dir) == ("pending", "other_data_directory", confirmed.data_dir), f"another data directory, blocked: other_data_directory comes first: {state.status}, {state.waiting}"
    assert apply.read_restore(elsewhere) == state, "the reason is recorded in the state file"
    assert mover.calls == 0, f"nothing moved: {mover.moved}"
    assert (cases.changed(data, cases.fingerprint(elsewhere)), cases.changed(kept, restore_items_but_the_state(elsewhere))) == ([], []), "nothing written or removed but the state"
    assert a_warning(events) and said(events, INSTANCE_BLOCKED_WAITS) == [], f"the warning of another data directory, not the block's: {logged(events)}"
    print_success("blocked, another data directory: other_data_directory")


@contextmanager
def _a_backup_runs(root: Path) -> Iterator[None]:
    """A backup runs on ``root`` for the block: it holds ``backups/.jobs/.lock``, as ``jobs._lock_held`` probes it."""
    backup = jobs._RunLock(lock_path(root))
    assert backup.try_acquire(), "precondition: the backup lock is free"
    try:
        yield
    finally:
        backup.release()


@contextmanager
def _another_process_serves(root: Path) -> Iterator[None]:
    """Another process serves ``root`` for the block: a spawn child holding its serving lock (``serving``)."""
    with serving(root):
        yield


#: What else holds a pending restore back at a start (§2 step 2, §10), and the reason it records once the block is
#: lifted.
BEHIND_THE_BLOCK = [
    pytest.param(_a_backup_runs, "backup_running", id="a-backup-running"),
    pytest.param(_another_process_serves, "server_running", id="another-process-holding-the-serving-lock"),
]


@pytest.mark.parametrize(("cause", "alone"), BEHIND_THE_BLOCK)
def test_on_a_blocked_instance_the_block_is_recorded_before_a_running_backup_or_a_serving_process(tmp_path, databases, checked, monkeypatch, cause, alone):
    """(m) §11, the order, 2 before 3: blocked while a backup runs, or while another process holds the serving lock, the
    restore records ``instance_blocked``, with the block's warning; nothing moved. The barrier: the block lifted and the
    cause still there, the next start records the cause — the step did see it. The block is set once the cause is in
    place: a serving child never sees it."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    confirm(apply, instance)
    data, kept = cases.fingerprint(instance.root), restore_items_but_the_state(instance.root)
    with cause(instance.root), moving(apply) as mover:
        monkeypatch.setenv(BLOCKED_VARIABLE, "true")
        with logs() as events:
            state = apply.apply_pending_restore(instance.root, boot=never_ran(apply), now=instance.applied_at)
        monkeypatch.delenv(BLOCKED_VARIABLE)
        unblocked = apply.apply_pending_restore(instance.root, boot=never_ran(apply), now=instance.committed_at)
    assert (state.status, state.waiting) == ("pending", "instance_blocked"), f"blocked, and {alone}: the block comes first: {state.status}, {state.waiting}"
    assert said(events, INSTANCE_BLOCKED_WAITS) == ["warning"], f"the block's warning: {logged(events)}"
    assert (unblocked.status, unblocked.waiting) == ("pending", alone), f"barrier: the block lifted, {alone} alone holds the restore back: {unblocked.status}, {unblocked.waiting}"
    assert mover.calls == 0, f"nothing moved: {mover.moved}"
    assert (cases.changed(data, cases.fingerprint(instance.root)), cases.changed(kept, restore_items_but_the_state(instance.root))) == ([], []), "nothing written or removed but the state"
    assert (apply_lock_free(instance.root), serving_lock_free(instance.root)) == (True, True), "both locks free once the backup ended, or the serving process exited"
    print_success(f"blocked and {alone}: instance_blocked; unblocked: {alone}")


def _an_undo_a_killed_start_left_rolling_back(apply: Any, instance: Instance) -> None:
    into_phase(apply, instance, "rolling_back")


#: A start's repair of the data directory (§11: unchanged while blocked), from the restore it finds, and how it ends.
REPAIRS_WHILE_BLOCKED = [
    pytest.param(_applied_by_a_start_that_died, ("rolled_back", "first_start_failed"), id="the-undo-of-a-restore-a-dead-start-applied"),
    pytest.param(_half_swapped_by_a_start_that_was_killed, ("rolled_back", "swap_interrupted"), id="the-undo-of-a-swap-a-killed-start-left-applying"),
    pytest.param(_an_undo_a_killed_start_left_rolling_back, ("rolled_back", "swap_interrupted"), id="the-end-of-an-undo-a-killed-start-left-rolling-back"),
]


@pytest.mark.parametrize(("prepare", "outcome"), REPAIRS_WHILE_BLOCKED)
def test_on_a_blocked_instance_a_start_still_puts_the_data_of_before_back(tmp_path, databases, checked, monkeypatch, prepare, outcome):
    """(m) §11, unchanged while blocked: the block keeps a restore from coming in, never the data of before from coming
    back. The undo of a restore a dead start applied (``first_start_failed``), of a swap a killed start left
    ``applying``, of an undo it left ``rolling_back`` (``swap_interrupted``): each runs on a blocked instance, the data
    of before back exactly, nothing waiting; both locks free once the step returned."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    prepare(apply, instance)
    monkeypatch.setenv(BLOCKED_VARIABLE, "true")
    assert instance_blocked() is True, "precondition: the instance is blocked"
    with logs() as events:
        state = apply.apply_pending_restore(instance.root, boot=never_ran(apply, 2), now=instance.committed_at)
    assert (state.status, state.reason, state.waiting) == (*outcome, None), f"undone on a blocked instance: {state.status}, {state.reason}, {state.waiting}"
    assert apply.read_restore(instance.root) == state, "the state on disk is the state returned"
    assert_put_back(instance)
    assert said(events, INSTANCE_BLOCKED_WAITS) == [], f"nothing waits for the unblock: {logged(events)}"
    assert (apply_lock_free(instance.root), serving_lock_free(instance.root)) == (True, True), "both locks free once the step returned"
    print_success(f"blocked: {outcome[0]}, {outcome[1]}")


def test_on_a_blocked_instance_a_restore_this_boot_applied_is_still_committed(tmp_path, databases, checked, monkeypatch):
    """(m) §11, unchanged while blocked: the block cannot change during one start (an environment variable read at the
    start), and ``restore-commit`` does not ask about it. A restore this boot applied is committed: every account at
    the restore time; the data of before, the copy and its check removed."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    confirm(apply, instance)
    boot = never_ran(apply)
    applied = apply.apply_pending_restore(instance.root, boot=boot, now=instance.applied_at)
    assert applied.status == "applied", f"precondition: applied by this boot: {applied.status}"
    monkeypatch.setenv(BLOCKED_VARIABLE, "true")
    assert instance_blocked() is True, "precondition: the instance is blocked"
    state = apply.finish_pending_restore(instance.root, boot=boot, now=instance.committed_at)
    found = (state.status, state.finished_at, state.session_version)
    assert found == ("committed", instance.committed_at, millis(instance.committed_at)), f"committed on a blocked instance, the sessions' value recorded: {found}"
    assert apply.read_restore(instance.root) == state, "the state on disk is the state returned"
    left = [path.name for path in (previous_of(instance.root), failed_of(instance.root), stage_dir(instance.root, instance.stage_id), check_state_path(instance.root, instance.stage_id)) if lexists(path)]
    assert left == [], f"previous/, failed/, the copy and its check state removed: {left}"
    assert set(versions_of(instance.root / DATABASE_ENTRY).values()) == {state.session_version}, "every account at the restore's value"
    print_success(f"blocked: committed, session_version {state.session_version}")


# =============================================================================
# (n) Lot B5c: the ticket of a restart's outcome, through a confirmation, a cancel, the commit and a rollback
# =============================================================================

OUTCOME = "backend.app.services.platform.instance_backup.outcome"


def outcome_module() -> Any:
    """``instance_backup.outcome`` (lot B5c), imported by the test that needs it, as ``apply_module``."""
    try:
        return importlib.import_module(OUTCOME)
    except ModuleNotFoundError as exc:
        if exc.name != OUTCOME:
            raise
        pytest.fail(f"[new] {OUTCOME} does not exist yet: lot B5c brings it")


def ticket_file_of(root: Path) -> Path:
    """``.restore/outcome-ticket.json``, as ``paths.outcome_ticket_path`` gives it (lot B5c)."""
    path_of = getattr(paths, "outcome_ticket_path", None)
    assert path_of is not None, "[new] paths.outcome_ticket_path does not exist yet: lot B5c adds it"
    return path_of(root)


def ticket_of(instance: Instance, *, now: datetime | None = None) -> tuple[str, bytes]:
    """A ticket for the instance's restore, as ``POST /backup/restore/restart`` issues it (by default a minute after the
    confirmation, an hour to live): the ticket, and the bytes of its file."""
    ticket = outcome_module().issue_ticket(instance.stage_id, data_dir=instance.root, now=now or instance.confirm_at + timedelta(minutes=1))
    return ticket, ticket_file_of(instance.root).read_bytes()


def outcome_read(ticket: str, state: Any, instance: Instance, *, at: datetime | None = None) -> dict[str, Any] | None:
    """What ``ticket`` opens for ``state`` at ``at`` (by default the commit's time), as the route answers it."""
    outcome = outcome_module().read_outcome(ticket, state, data_dir=instance.root, now=at or instance.committed_at)
    return None if outcome is None else outcome.model_dump()


def expiry_of(file: bytes) -> datetime:
    """The ``expires_at`` the ticket's file ``file`` records."""
    return datetime.fromisoformat(json.loads(file)["expires_at"])


def reads_until_it_expires(ticket: str, state: Any, instance: Instance, file: bytes) -> list[tuple[dict[str, Any] | None, bytes | None]]:
    """N53: what ``ticket`` opens for ``state`` at the commit's time, a minute later and a microsecond before it expires,
    each with the bytes of the ticket's file after that read (``None``: gone)."""
    seen: list[tuple[dict[str, Any] | None, bytes | None]] = []
    for moment in (instance.committed_at, instance.committed_at + timedelta(minutes=1), expiry_of(file) - timedelta(microseconds=1)):
        opened = outcome_read(ticket, state, instance, at=moment)
        path = ticket_file_of(instance.root)
        seen.append((opened, path.read_bytes() if lexists(path) else None))
    return seen


@pytest.mark.parametrize("before", ["no-restore", "committed", "rolled_back"])
def test_a_new_confirmation_drops_the_ticket_the_restore_before_left(tmp_path, databases, checked, before):
    """(n) A ticket names one restart of one restore. A new confirmation (the API's and the command line's) is another
    restore: the ticket a restart left unread goes, whether that restore committed, rolled back, or left no state."""
    print_section("(n) B5c: the ticket of a restart's outcome")
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    if before != "no-restore":
        into_phase(apply, instance, before)
    ticket_of(instance)
    add_stage(instance, checked, OTHER_STAGE)
    state = confirm(apply, instance, OTHER_STAGE)
    assert (state.status, state.stage_id) == ("pending", OTHER_STAGE), f"precondition: the new restore waits: {state.status}, {state.stage_id}"
    assert not lexists(ticket_file_of(instance.root)), f"{before}: the ticket left is dropped by the new confirmation"
    assert_unrelated_kept(instance.root)
    print_success(f"{before}: dropped by the new confirmation")


@pytest.mark.parametrize("refused", ["another-copy-while-one-waits", "a-copy-that-is-not-there"])
def test_a_refused_confirmation_keeps_the_ticket_of_the_restore_that_waits(tmp_path, databases, checked, refused):
    """(n) A refused confirmation writes nothing (e): the restore that waits keeps its ticket, and the page that asked for
    its restart still reads its outcome. Refused because another restore waits (``restore_already_pending``), or before
    anything (``restore_stage_not_found``)."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    pending = confirm(apply, instance)
    ticket, file = ticket_of(instance)
    if refused == "another-copy-while-one-waits":
        add_stage(instance, checked, OTHER_STAGE)
        stage_id, refusal = OTHER_STAGE, apply.RestoreAlreadyPendingError
    else:
        stage_id, refusal = UNRELATED_CHECK, apply.RestoreStageMissingError
    with pytest.raises(refusal):
        confirm(apply, instance, stage_id)
    assert ticket_file_of(instance.root).read_bytes() == file, f"{refused}: the ticket kept as it was"
    assert outcome_read(ticket, pending, instance) == {"state": "pending", "reason": None, "waiting": None}, f"{refused}: it still opens the outcome"
    print_success(f"{refused}: {refusal.__name__}, the ticket kept")


@pytest.mark.parametrize("drop_copy", [False, True], ids=["the-copy-kept", "the-copy-dropped"])
def test_a_cancel_drops_the_ticket_with_the_restore(tmp_path, databases, checked, drop_copy):
    """(n) The restore no longer waits: its ticket goes with it, whichever way the copy goes (the API's and the command
    line's cancel both drop the copy since B-17; the service keeps both ways)."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    confirm(apply, instance)
    ticket_of(instance)
    apply.cancel_restore(data_dir=instance.root, drop_copy=drop_copy)
    assert lexists(stage_dir(instance.root, instance.stage_id)) is not drop_copy, f"precondition: the copy {'dropped' if drop_copy else 'kept'}"
    assert not lexists(ticket_file_of(instance.root)), f"drop_copy={drop_copy}: the ticket dropped with the restore"
    assert_unrelated_kept(instance.root)
    print_success(f"drop_copy={drop_copy}: the ticket dropped")


@pytest.mark.parametrize("phase", ["applied", *TERMINAL_PHASES])
def test_a_refused_cancel_keeps_the_ticket_whose_outcome_is_coming(tmp_path, databases, checked, phase):
    """(n) Only a pending restore can be cancelled: a cancel of one being applied or finished is refused, and the ticket
    stays for the page that waits for the outcome."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    state = into_phase(apply, instance, phase)
    ticket, file = ticket_of(instance, now=instance.applied_at)
    with pytest.raises(apply.RestoreNotPendingError):
        apply.cancel_restore(data_dir=instance.root, drop_copy=True)
    assert ticket_file_of(instance.root).read_bytes() == file, f"{phase}: the ticket kept as it was"
    opened = outcome_read(ticket, state, instance)
    assert opened is not None and opened["state"] == {"applied": "in_progress"}.get(phase, phase), f"{phase}: it still opens the outcome: {opened}"
    print_success(f"{phase}: refused, the ticket kept")


def test_prepare_restart_issues_the_ticket_of_the_pending_restore_under_its_lock(tmp_path, databases, checked, monkeypatch):
    """(n) ``POST /backup/restore/restart`` prepares itself with ``apply.prepare_restart``: the restore waiting, as on
    disk, and a new ticket for its stage, issued once while the restore's lock is held — a cancel or a confirmation from
    another page cannot come in between, and two restart requests take turns on the ticket's file. The lock is free
    again once it returned; the new ticket replaces an older one and opens ``pending``."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    pending = confirm(apply, instance)
    older, _file = ticket_of(instance)
    assert hasattr(apply, "prepare_restart") and hasattr(apply, "issue_ticket"), "[new] apply.prepare_restart issues the ticket through outcome.issue_ticket, imported into apply"
    real, lock_held = apply.issue_ticket, []

    def issue_ticket(*args: Any, **kwargs: Any) -> str:
        lock_held.append(not apply_lock_free(instance.root))
        return real(*args, **kwargs)

    monkeypatch.setattr(apply, "issue_ticket", issue_ticket)
    state, ticket = apply.prepare_restart(data_dir=instance.root)
    assert state == pending == apply.read_restore(instance.root), f"the restore waiting, as it is on disk: {state}"
    assert lock_held == [True], f"one ticket, issued while the restore's lock is held: {lock_held}"
    assert apply_lock_free(instance.root), "the restore's lock is free again once prepare_restart returned"
    assert json.loads(ticket_file_of(instance.root).read_bytes())["stage_id"] == instance.stage_id, "the ticket of the pending restore's stage"
    now = datetime.now(UTC)
    assert outcome_read(ticket, state, instance, at=now) == {"state": "pending", "reason": None, "waiting": None}, "the new ticket opens pending"
    assert outcome_read(older, state, instance, at=now) is None, "the older ticket is replaced"
    print_success("prepare_restart: pending, one ticket under the lock")


@pytest.mark.parametrize("phase", ["none", "applied", *TERMINAL_PHASES])
def test_prepare_restart_without_a_pending_restore_is_refused_and_writes_nothing(tmp_path, databases, checked, phase):
    """(n) No restore, or one being applied or finished: ``RestoreNotPendingError`` (the route's 409), and nothing
    written — without a restore not even the lock; a ticket an earlier restart gave stays as it was, for the outcome its
    page waits for."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    if phase != "none":
        into_phase(apply, instance, phase)
        ticket_of(instance, now=instance.applied_at)
    data, items = cases.fingerprint(instance.root), restore_items(instance.root)
    with pytest.raises(apply.RestoreNotPendingError) as raised:
        apply.prepare_restart(data_dir=instance.root)
    assert raised.value.code == "restore_not_pending", raised.value.code
    assert (cases.fingerprint(instance.root), restore_items(instance.root)) == (data, items), f"{phase}: nothing written, the lock and an earlier ticket included: {cases.changed(items, restore_items(instance.root))}"
    print_success(f"{phase}: restore_not_pending, nothing written")


def test_the_swap_and_the_commit_keep_the_ticket_which_reads_committed_until_it_expires(tmp_path, databases, checked):
    """(n) ``.restore`` is never swapped, and the commit removes the data of before, the copy and its check, never the
    ticket: issued before the restart, its file is there byte for byte after the start. N53, one restore, one ticket:
    it opens ``committed`` at every read, its file kept, until it expires; at ``expires_at`` it opens nothing, and its
    file goes."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    confirm(apply, instance)
    ticket, file = ticket_of(instance)
    boot = never_ran(apply)
    applied = apply.apply_pending_restore(instance.root, boot=boot, now=instance.applied_at)
    assert applied.status == "applied" and ticket_file_of(instance.root).read_bytes() == file, f"the swap leaves the ticket as it was: {applied.status}"
    state = apply.finish_pending_restore(instance.root, boot=boot, now=instance.committed_at)
    assert state.status == "committed" and ticket_file_of(instance.root).read_bytes() == file, f"the commit leaves the ticket as it was: {state.status}"
    expected = {"state": "committed", "reason": None, "waiting": None}
    seen = reads_until_it_expires(ticket, state, instance, file)
    assert seen == [(expected, file)] * 3, f"N53: committed at every read, the ticket's file as it was, until it expires: {[(opened, kept is not None) for opened, kept in seen]}"
    assert outcome_read(ticket, state, instance, at=expiry_of(file)) is None, "at expires_at the ticket opens nothing"
    assert not lexists(ticket_file_of(instance.root)), "expired, its file goes when its holder presents it"
    print_success("swapped, committed, the ticket read three times until it expired")


def _rolled_back_by_a_rename_failing(apply: Any, instance: Instance) -> Any:
    with moving(apply, fail_at=frozenset({3})):
        return apply.apply_pending_restore(instance.root, boot=never_ran(apply), now=instance.applied_at)


def _rolled_back_after_the_first_start_died(apply: Any, instance: Instance) -> Any:
    apply.apply_pending_restore(instance.root, boot=never_ran(apply), now=instance.applied_at)
    return apply.apply_pending_restore(instance.root, boot=never_ran(apply, 1), now=instance.committed_at)


#: The rollbacks a restart can end in, and the reason they record.
ROLLBACKS = [
    pytest.param(_rolled_back_by_a_rename_failing, "swap_failed", id="a-rename-of-the-swap-failing"),
    pytest.param(_rolled_back_after_the_first_start_died, "first_start_failed", id="the-first-start-dying"),
]


@pytest.mark.parametrize(("roll_back", "reason"), ROLLBACKS)
def test_a_rollback_keeps_the_ticket_which_reads_rolled_back_until_it_expires(tmp_path, databases, checked, roll_back, reason):
    """(n) The undo puts the data of before back, and ``restore-commit`` removes what the rollback left: neither touches
    the ticket. N53: it opens ``rolled_back`` with its reason at every read, its file kept, until it expires; at
    ``expires_at`` it opens nothing, and its file goes."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    confirm(apply, instance)
    ticket, file = ticket_of(instance)
    rolled = roll_back(apply, instance)
    assert (rolled.status, rolled.reason) == ("rolled_back", reason), f"precondition: rolled back, {reason}: {rolled.status}, {rolled.reason}"
    state = apply.finish_pending_restore(instance.root, boot=never_ran(apply, 2), now=instance.committed_at)
    assert state == rolled and ticket_file_of(instance.root).read_bytes() == file, "the rollback and its cleaning leave the ticket as it was"
    expected = {"state": "rolled_back", "reason": reason, "waiting": None}
    seen = reads_until_it_expires(ticket, state, instance, file)
    assert seen == [(expected, file)] * 3, f"N53: rolled_back, {reason}, at every read, the ticket's file as it was, until it expires: {[(opened, kept is not None) for opened, kept in seen]}"
    assert outcome_read(ticket, state, instance, at=expiry_of(file)) is None, "at expires_at the ticket opens nothing"
    assert not lexists(ticket_file_of(instance.root)), "expired, its file goes when its holder presents it"
    print_success(f"{reason}: the ticket read three times until it expired")


# =============================================================================
# (p) B-55 and B-53: the report of the checked copy, read through the one reader
# =============================================================================
#
# The confirmation took any ``OSError`` reading the report for «no checked copy» (``RestoreStageMissingError``, the
# route's 404), after which the tab forgets the check: a disk that failed once made it drop a good copy. B-55, the
# coordinator's rule, the jobs' since B-50: only a report that is not there or cannot be one — ``read_report``'s
# ``FileNotFoundError`` — is «no checked copy»; any other ``OSError``, a transient one, reaches the caller (the route's
# 500 ``restore_confirm_failed``), which the tab retries. And a report that is a folder left one descriptor open per
# confirmation (B-53).


def report_of(instance: Instance) -> Path:
    """The report of the instance's checked copy: ``.restore/stage/<id>/report.json``."""
    return stage_dir(instance.root, instance.stage_id) / STAGE_REPORT_FILE


def refusal_of(raised: Exception | None) -> tuple[str, str | None]:
    """What a confirmation raised, as the route tells it: its class, and its stable code when it has one."""
    return type(raised).__name__, getattr(raised, "code", None)


def test_a_transient_error_reading_the_report_reaches_the_caller_and_nothing_is_confirmed(tmp_path, databases, checked, monkeypatch):
    """(p) B-55 A checked copy whose report ``os.open`` fails to open with ``EIO`` (that file alone): ``confirm_restore``
    raises that very error — the route's 500 ``restore_confirm_failed``, which the tab retries — never
    ``RestoreStageMissingError`` (the route's 404, after which the tab forgets the check). Nothing confirmed, written or
    removed: no state of a restore, ``.restore`` and the data directory as they were. Red before B-55:
    ``RestoreStageMissingError``."""
    print_section("(p) B-55, B-53: the report of the checked copy")
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    data, items = cases.fingerprint(instance.root), restore_items(instance.root)
    refusal = opening_fails(monkeypatch, report_of(instance), EIO)
    returned, raised = answer_of(lambda: confirm(apply, instance))
    assert raised is refusal, f"the very EIO os.open raised reading the report, as it is; not {refusal_of(raised)}: {raised} (returned {returned!r})"
    assert not lexists(state_file(instance.root)), "nothing confirmed: no state of a restore"
    assert (cases.fingerprint(instance.root), restore_items(instance.root)) == (data, items), f"nothing written or removed: {cases.changed(items, restore_items(instance.root))}"
    print_success("EIO reading the report: raised as it is, nothing confirmed")


@needs_dev_fd
def test_a_report_that_is_a_folder_is_no_checked_copy_and_leaves_no_descriptor_open(tmp_path, databases, checked):
    """(p) B-53 A checked copy whose report is a folder: ``RestoreStageMissingError`` (``restore_stage_not_found``) at
    every confirmation and nothing written, as before B-53; and, confirmed twenty times, no descriptor left open on the
    folder. Red before B-53: twenty descriptors, one per confirmation — ``os.fdopen`` refused the folder without closing
    the descriptor ``os.open`` gave."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    report = report_of(instance)
    report.unlink()
    report.mkdir(mode=0o700)
    data, items = cases.fingerprint(instance.root), restore_items(instance.root)
    assert descriptors_on(report) == [], "precondition: no descriptor of this process is open on the folder"
    answers: set[tuple[str, str | None]] = set()
    for _ in range(cases.LEAK_READS):
        _returned, raised = answer_of(lambda: confirm(apply, instance))
        answers.add(refusal_of(raised))
    left_open = close_all(descriptors_on(report))
    assert answers == {("RestoreStageMissingError", "restore_stage_not_found")}, f"a report that is a folder: no checked copy, at every confirmation: {sorted(answers, key=str)}"
    assert (cases.fingerprint(instance.root), restore_items(instance.root)) == (data, items), f"nothing written, not even the lock: {cases.changed(items, restore_items(instance.root))}"
    assert left_open == [], f"{len(left_open)} descriptor(s) left open on the folder by {cases.LEAK_READS} confirmations: {left_open}"
    print_success(f"a report that is a folder: restore_stage_not_found at each of {cases.LEAK_READS} confirmations, no descriptor left open")


@cases.needs_permission_checks
def test_a_report_the_server_may_not_read_is_no_checked_copy(tmp_path, databases, checked, modes):
    """(p) B-55, the guard (green before and after): a checked copy whose report is of mode 000 is no checked copy —
    ``RestoreStageMissingError`` (``restore_stage_not_found``), as a folder, a link or a content that is no report. The
    coordinator's rule: no permission is «no check» (the tab forgets it), only a transient error is one to retry; nothing
    is written. Root reads it all the same: skipped."""
    apply = apply_module()
    instance = build(tmp_path / "instance", databases, checked)
    data, items = cases.fingerprint(instance.root), restore_items(instance.root)
    modes.chmod(report_of(instance), 0o000)
    _returned, raised = answer_of(lambda: confirm(apply, instance))
    modes.put_back()
    assert refusal_of(raised) == ("RestoreStageMissingError", "restore_stage_not_found"), f"a report of mode 000: no checked copy, not {refusal_of(raised)}: {raised}"
    assert (cases.fingerprint(instance.root), restore_items(instance.root)) == (data, items), f"nothing written: {cases.changed(items, restore_items(instance.root))}"
    print_success("a report of mode 000: restore_stage_not_found, nothing written")


# =============================================================================
# (q) Lot L3-2: how a restore was confirmed
# =============================================================================

#: How a restore may be confirmed (contract L3 §5): the administrators' route, the command line, the hosting panel.
CONFIRMED_VIA = ("admin", "cli", "panel")
#: What ``confirmed_via`` reads as before L3-2, when ``RestoreState`` has no such attribute: never a valid value.
NO_VIA = "<missing: RestoreState has no confirmed_via before L3-2>"


def l3_2_name(module: Any, name: str) -> Any:
    """``module.<name>``, a name lot L3-2 adds, read when the test needs it: its absence fails that test alone."""
    value = getattr(module, name, None)
    if value is None:
        pytest.fail(f"[new] L3-2: {module.__name__}.{name} does not exist yet (contract L3 §5)", pytrace=False)
    return value


def l3_2_parameter(function: Callable[..., Any], name: str) -> None:
    """The keyword ``name`` of ``function``, which lot L3-2 adds; before it, a failure that says so."""
    if name not in inspect.signature(function).parameters:
        pytest.fail(f"[new] L3-2: {function.__qualname__}() takes no {name!r} yet (contract L3 §5)", pytrace=False)


def via_of(state: Any) -> str:
    return getattr(state, "confirmed_via", NO_VIA)


def via_on_disk(root: Path) -> object:
    return json.loads(state_file(root).read_text(encoding="utf-8")).get("confirmed_via", NO_VIA)


def test_a_restore_is_confirmed_via_admin_cli_or_panel():
    """(q) L3-2: ``ConfirmedVia`` is ``Literal["admin", "cli", "panel"]``, in this order, and ``RestoreState`` has the
    field ``confirmed_via``."""
    print_section("(q) L3-2 confirmed_via")
    apply = apply_module()
    via = get_args(l3_2_name(apply, "ConfirmedVia"))
    assert via == CONFIRMED_VIA, f"ConfirmedVia is Literal{list(CONFIRMED_VIA)}: {via}"
    assert "confirmed_via" in apply.RestoreState.model_fields, f"RestoreState has confirmed_via: {sorted(apply.RestoreState.model_fields)}"
    print_success("admin, cli, panel")


@pytest.mark.parametrize("via", CONFIRMED_VIA)
def test_confirm_restore_records_how_it_was_confirmed(tmp_path, databases, checked, via):
    """(q) L3-2: ``confirm_restore(..., confirmed_via=)`` records it, in the state it returns, in ``restore.json`` and
    in what ``read_restore`` reads; ``confirmed_by`` stays as given."""
    apply = apply_module()
    l3_2_parameter(apply.confirm_restore, "confirmed_via")
    instance = build(tmp_path / "instance", databases, checked)
    state = apply.confirm_restore(instance.stage_id, confirmed_by=CONFIRMED_BY, confirmed_via=via, data_dir=instance.root, now=instance.confirm_at)
    assert (state.confirmed_by, via_of(state)) == (CONFIRMED_BY, via), f"confirmed by {CONFIRMED_BY}, via {via}: {state}"
    assert via_on_disk(instance.root) == via, f"restore.json says via {via}: {via_on_disk(instance.root)}"
    assert via_of(apply.read_restore(instance.root)) == via, "read_restore reads it back"
    print_success(f"via {via}")


@pytest.mark.parametrize("confirmed_by", [CONFIRMED_BY, "cli", "panel"])
def test_confirm_restore_without_confirmed_via_is_admin_whatever_the_username(tmp_path, databases, checked, confirmed_by):
    """(q) L3-2: without ``confirmed_via`` a confirmation is the administrators' route's, ``admin``, even for an
    administrator whose username is literally ``cli`` or ``panel``: the username never decides how it was confirmed."""
    apply = apply_module()
    l3_2_parameter(apply.confirm_restore, "confirmed_via")
    instance = build(tmp_path / "instance", databases, checked)
    state = apply.confirm_restore(instance.stage_id, confirmed_by=confirmed_by, data_dir=instance.root, now=instance.confirm_at)
    assert (state.confirmed_by, via_of(state), via_on_disk(instance.root)) == (confirmed_by, "admin", "admin"), f"{confirmed_by!r}: via admin: {state}"
    print_success(f"{confirmed_by!r}: via admin")


@pytest.mark.parametrize("via", [None, *CONFIRMED_VIA], ids=["not-given", *CONFIRMED_VIA])
def test_confirm_check_records_how_it_was_confirmed(tmp_path, databases, checked, via):
    """(q) L3-2: ``restore_jobs.confirm_check(..., confirmed_via=)`` hands it to ``confirm_restore``: the state says it;
    without one, ``admin``."""
    apply = apply_module()
    l3_2_parameter(restore_jobs.confirm_check, "confirmed_via")
    instance = build(tmp_path / "instance", databases, checked)
    given = {} if via is None else {"confirmed_via": via}
    state = restore_jobs.confirm_check(instance.stage_id, confirmed_by=CONFIRMED_BY, data_dir=instance.root, **given)
    expected = via or "admin"
    assert (state.status, via_of(state), via_on_disk(instance.root)) == ("pending", expected, expected), f"pending, via {expected}: {state}"
    assert via_of(apply.read_restore(instance.root)) == expected, "read_restore reads it back"
    print_success(f"{via or 'not given'}: via {expected}")


@pytest.mark.parametrize(("confirmed_by", "via"), [("cli", "cli"), (CONFIRMED_BY, "admin"), ("panel", "admin")])
def test_a_state_written_before_l3_2_reads_its_confirmed_via_from_confirmed_by(tmp_path, confirmed_by, via):
    """(q) L3-2: ``restore.json`` without the key ``confirmed_via`` — every state written before L3-2 — reads ``cli``
    when ``confirmed_by`` is ``cli`` (the command line's mark), ``admin`` otherwise: before L3-2 the panel confirmed
    nothing, so a username ``panel`` was an administrator's."""
    apply = apply_module()
    root = tmp_path / "instance"
    root.mkdir(mode=0o700)
    ensure_private_dir(restore_dir(root), root)
    record = {
        "format": 1,
        "status": "pending",
        "stage_id": UNRELATED_CHECK,
        "data_dir": str(root.resolve()),
        "confirmed_at": "2026-10-15T22:00:00Z",
        "confirmed_by": confirmed_by,
        "backup_created_at": "2026-10-14T09:00:00Z",
        "backup_app_version": "v1.2.0",
        "action": "same",
    }
    state_file(root).write_text(json.dumps(record), encoding="utf-8")
    state_file(root).chmod(0o600)
    state = apply.read_restore(root)
    assert state is not None, "precondition: a state of before L3-2 is read"
    assert (state.confirmed_by, via_of(state)) == (confirmed_by, via), f"{confirmed_by!r} without confirmed_via reads via {via}: {state}"
    print_success(f"{confirmed_by!r}: via {via}")


# =============================================================================
# (s) Lot B5-1: the owner's choice at the confirmation
# =============================================================================

PROFILE_VARIABLE = "LIBREFOLIO_PROFILE"
OWNER_EMAIL_VARIABLE = "LIBREFOLIO_ADMIN_EMAIL"
OWNER_SIDE_VARIABLES = ("LIBREFOLIO_ADMIN_USERNAME", "LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN", "LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN_FILE")
#: The owner's email as the operator writes it; ``OWEN`` holds it in another A–Z case.
OWNER_EMAIL = "Owner.B51@Example.COM"
#: The candidates a B5-1 check writes into a report (``staging.OwnerCandidate``), by name. Their ids are the report's:
#: the confirmation reads nothing else.
ADA = {"user_id": 4, "username": "ada_admin", "email": "ada.b51@example.com", "is_superuser": True, "is_active": True}
ZOE = {"user_id": 1, "username": "zoe_admin", "email": "zoe.b51@example.com", "is_superuser": True, "is_active": True}
#: A candidate that is neither an active administrator nor the owner's email holder: an administrator now disabled, whose
#: address was the owner's when the archive was checked (the variable changed since).
OLGA = {"user_id": 3, "username": "olga_former_admin", "email": "olga.b51@example.com", "is_superuser": True, "is_active": False}
#: A plain user holding the owner's email: the forced choice.
OWEN = {"user_id": 5, "username": "owen_user", "email": "OWNER.b51@EXAMPLE.com", "is_superuser": False, "is_active": True}
NO_SUCH_USER = 999


def b51_parameter(function: Callable[..., Any], name: str) -> None:
    """The keyword ``name`` of ``function``, which lot B5-1 adds; before it, a failure that says so."""
    if name not in inspect.signature(function).parameters:
        pytest.fail(f"[new] B5-1: {function.__qualname__}() takes no {name!r} yet (interface §3)", pytrace=False)


def use_profile(monkeypatch: pytest.MonkeyPatch, profile: str) -> None:
    """``LIBREFOLIO_PROFILE`` as ``profile`` in this process; barrier: ``get_settings()`` reads it."""
    from backend.app.config import get_settings  # noqa: PLC0415 — read at each call, as the product reads it

    monkeypatch.setenv(PROFILE_VARIABLE, profile)
    assert get_settings().LIBREFOLIO_PROFILE == profile, f"barrier: get_settings() reads the profile {profile!r}"


def owner_email_is(monkeypatch: pytest.MonkeyPatch, value: str | None) -> None:
    """``LIBREFOLIO_ADMIN_EMAIL`` set to ``value`` (``None``: unset), the other F02 variables unset."""
    for name in OWNER_SIDE_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    if value is None:
        monkeypatch.delenv(OWNER_EMAIL_VARIABLE, raising=False)
    else:
        monkeypatch.setenv(OWNER_EMAIL_VARIABLE, value)


#: A key of ``report.json`` left out: the report was written before the addendum (§7.1).
ABSENT = object()


def with_candidates(instance: Instance, candidates: list[dict[str, Any]], **report: Any) -> None:
    """The instance's checked copy, its report naming ``candidates`` as B5-1's check writes them, and the keys
    ``report`` (``ABSENT``: left out): raw JSON, so that the report reads before B5-1 too (the keys then ignored)."""
    path = stage_dir(instance.root, instance.stage_id) / STAGE_REPORT_FILE
    record = json.loads(path.read_text(encoding="utf-8"))
    record["owner_candidates"] = candidates
    for name, value in report.items():
        if value is ABSENT:
            record.pop(name, None)
        else:
            record[name] = value
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def owner_case(tmp_path: Path, databases: cases.Databases, checked: Checked, monkeypatch: pytest.MonkeyPatch, *, profile: str, owner_email: str | None, candidates: list[dict[str, Any]], **report: Any) -> Instance:
    """An instance whose checked copy names ``candidates``, under ``profile`` with that owner's email. Its report says,
    as the addendum's check writes it (§7.1), that it was checked with that same address and found no conflict, unless
    ``report`` says otherwise (``owner_email_checked``, ``owner_conflicts``; ``ABSENT``: the key left out)."""
    use_profile(monkeypatch, profile)
    owner_email_is(monkeypatch, owner_email)
    instance = build(tmp_path / "instance", databases, checked)
    with_candidates(instance, candidates, **{"owner_email_checked": owner_email, "owner_conflicts": [], **report})
    return instance


def but_the_apply_lock(root: Path) -> dict[str, tuple]:
    """Everything below ``.restore`` but its apply lock, which a refused confirmation may have taken: what it leaves."""
    return {name: value for name, value in restore_items(root).items() if name != APPLY_LOCK_NAME}


def on_disk_owner(root: Path) -> tuple[object, object]:
    """The owner's keys of ``restore.json``: id, outcome. The file never holds an ``owner_reset_path`` key."""
    record = json.loads(state_file(root).read_text(encoding="utf-8"))
    assert "owner_reset_path" not in record, f"no owner_reset_path key in the state: {sorted(record)}"
    return tuple(record.get(name, "<missing>") for name in ("owner_user_id", "owner_outcome"))


#: (the candidates, the owner's email, the id chosen, the code of the refusal).
REFUSED_CHOICES = [
    pytest.param([ADA, OLGA, ZOE], OWNER_EMAIL, None, "owner_choice_required", id="none-chosen"),
    pytest.param([ADA, OWEN, ZOE], OWNER_EMAIL, None, "owner_choice_required", id="none-chosen-a-forced-user-there"),
    pytest.param([ADA, ZOE], None, ADA["user_id"], "owner_email_not_set", id="owner-email-unset"),
    pytest.param([ADA, OLGA, ZOE], OWNER_EMAIL, NO_SUCH_USER, "owner_choice_invalid", id="not-a-candidate"),
    pytest.param([ADA, OLGA, ZOE], OWNER_EMAIL, OLGA["user_id"], "owner_choice_invalid", id="neither-an-active-administrator-nor-the-owner"),
    pytest.param([ADA, OWEN, ZOE], OWNER_EMAIL, ADA["user_id"], "owner_choice_invalid", id="another-administrator-while-a-forced-user-exists"),
    pytest.param([ADA, OWEN, ZOE], "someone.else.b51@example.com", OWEN["user_id"], "owner_choice_invalid", id="the-holder-of-an-email-no-longer-the-owner-s"),
]


@pytest.mark.parametrize(("candidates", "owner_email", "chosen", "code"), REFUSED_CHOICES)
def test_a_managed_confirmation_without_a_valid_owner_choice_is_refused_and_writes_nothing(tmp_path, databases, checked, monkeypatch, candidates, owner_email, chosen, code):
    """(s) B5-1: ``managed``, confirmed via ``admin``: no choice, no owner's email, or a choice the candidates do not
    allow is a ``RestoreStateError`` with its stable ``code``; no state written, nothing of ``.restore`` changed but
    its apply lock."""
    print_section("(s) B5-1 an owner choice refused")
    apply = apply_module()
    b51_parameter(apply.confirm_restore, "owner_user_id")
    instance = owner_case(tmp_path, databases, checked, monkeypatch, profile="managed", owner_email=owner_email, candidates=candidates)
    before = but_the_apply_lock(instance.root)
    with pytest.raises(apply.RestoreStateError) as raised:
        apply.confirm_restore(instance.stage_id, confirmed_by=CONFIRMED_BY, confirmed_via="admin", owner_user_id=chosen, data_dir=instance.root, now=instance.confirm_at)
    assert raised.value.code == code, f"refused with {code}, not {raised.value.code}: {raised.value}"
    assert not lexists(state_file(instance.root)), "a refused confirmation writes no state"
    assert but_the_apply_lock(instance.root) == before, f"nothing of .restore changed: {cases.changed(before, but_the_apply_lock(instance.root))}"
    assert apply.read_restore(instance.root) is None, "no restore waits"
    print_success(f"{code}, nothing written")


def test_a_managed_confirmation_without_the_keyword_is_refused_as_owner_choice_required(tmp_path, databases, checked, monkeypatch):
    """(s) B5-1: ``owner_user_id`` defaults to ``None``: an administrators' confirmation that names nobody — as every
    caller did before B5-1 — is refused ``owner_choice_required`` in ``managed``. Red before B5-1: it was confirmed."""
    apply = apply_module()
    instance = owner_case(tmp_path, databases, checked, monkeypatch, profile="managed", owner_email=OWNER_EMAIL, candidates=[ADA, ZOE])
    try:
        state = apply.confirm_restore(instance.stage_id, confirmed_by=CONFIRMED_BY, data_dir=instance.root, now=instance.confirm_at)
    except apply.RestoreStateError as exc:
        assert exc.code == "owner_choice_required", f"refused owner_choice_required, not {exc.code}: {exc}"
    else:
        pytest.fail(f"a managed confirmation naming no owner was confirmed: {state}")
    assert not lexists(state_file(instance.root)), "a refused confirmation writes no state"
    print_success("no keyword: owner_choice_required")


#: (the candidates, the id chosen): what a managed administrator may confirm.
ALLOWED_CHOICES = [
    pytest.param([ADA, OWEN, ZOE], OWEN["user_id"], id="the-forced-user-even-not-an-administrator"),
    pytest.param([ADA, OLGA, ZOE], ADA["user_id"], id="an-active-administrator-nobody-holding-the-owner-s-email"),
    pytest.param([ADA, ZOE], ZOE["user_id"], id="another-active-administrator"),
]


@pytest.mark.parametrize(("candidates", "chosen"), ALLOWED_CHOICES)
def test_a_managed_confirmation_with_a_valid_owner_choice_records_it(tmp_path, databases, checked, monkeypatch, candidates, chosen):
    """(s) B5-1: the choice the candidates allow is confirmed: ``pending``, ``owner_user_id`` the id chosen in the state
    returned, in ``restore.json`` and in what ``read_restore`` reads; ``owner_outcome`` ``None``
    (only the first start writes it), and no ``owner_reset_path`` key in the file."""
    print_section("(s) B5-1 an owner choice recorded")
    apply = apply_module()
    b51_parameter(apply.confirm_restore, "owner_user_id")
    instance = owner_case(tmp_path, databases, checked, monkeypatch, profile="managed", owner_email=OWNER_EMAIL, candidates=candidates)
    state = apply.confirm_restore(instance.stage_id, confirmed_by=CONFIRMED_BY, confirmed_via="admin", owner_user_id=chosen, data_dir=instance.root, now=instance.confirm_at)
    assert (state.status, state.owner_user_id, state.owner_outcome) == ("pending", chosen, None), f"pending, the owner {chosen} recorded: {state}"
    assert on_disk_owner(instance.root) == (chosen, None), f"restore.json records the owner {chosen}: {on_disk_owner(instance.root)}"
    assert apply.read_restore(instance.root).owner_user_id == chosen, "read_restore reads it back"
    print_success(f"owner {chosen} recorded")


def test_a_self_hosted_confirmation_asks_no_owner(tmp_path, databases, checked, monkeypatch):
    """(s) B5-1: ``selfhosted``, the owner's email set or not: an administrators' confirmation naming nobody is
    confirmed as before, ``owner_user_id`` ``None``."""
    apply = apply_module()
    b51_parameter(apply.confirm_restore, "owner_user_id")
    instance = owner_case(tmp_path, databases, checked, monkeypatch, profile="selfhosted", owner_email=OWNER_EMAIL, candidates=[ADA, OWEN, ZOE])
    state = apply.confirm_restore(instance.stage_id, confirmed_by=CONFIRMED_BY, confirmed_via="admin", owner_user_id=None, data_dir=instance.root, now=instance.confirm_at)
    assert (state.status, state.owner_user_id) == ("pending", None), f"self-hosted: pending, no owner: {state}"
    assert on_disk_owner(instance.root) == (None, None), f"restore.json: no owner: {on_disk_owner(instance.root)}"
    print_success("selfhosted: no owner asked")


@pytest.mark.parametrize("via", ["panel", "cli"])
def test_a_managed_confirmation_via_the_panel_or_the_command_line_without_the_owner_s_address_never_needs_an_owner(tmp_path, databases, checked, monkeypatch, via):
    """(s) B5-1, narrowed by B5-1j: the hosting panel and the command line never ask the owner's choice, and on a
    managed instance WITHOUT ``LIBREFOLIO_ADMIN_EMAIL`` they pick none either (there is no trusted address): confirmed,
    ``owner_user_id`` ``None``, ``owner_outcome`` ``None``. With the address set they pick the owner's account: (v)."""
    apply = apply_module()
    b51_parameter(apply.confirm_restore, "owner_user_id")
    instance = owner_case(tmp_path, databases, checked, monkeypatch, profile="managed", owner_email=None, candidates=[ADA, OWEN, ZOE])
    state = apply.confirm_restore(instance.stage_id, confirmed_by=via, confirmed_via=via, data_dir=instance.root, now=instance.confirm_at)
    assert (state.status, state.confirmed_via, state.owner_user_id, state.owner_outcome) == ("pending", via, None, None), f"managed via {via}, no address: pending, no owner: {state}"
    assert on_disk_owner(instance.root) == (None, None), f"restore.json: no owner: {on_disk_owner(instance.root)}"
    print_success(f"managed via {via}, no address: no owner needed")


def test_confirm_check_hands_the_owner_choice_to_confirm_restore(tmp_path, databases, checked, monkeypatch):
    """(s) B5-1: ``restore_jobs.confirm_check(..., owner_user_id=)`` hands it to ``confirm_restore``: the state says it."""
    apply = apply_module()
    b51_parameter(restore_jobs.confirm_check, "owner_user_id")
    instance = owner_case(tmp_path, databases, checked, monkeypatch, profile="managed", owner_email=OWNER_EMAIL, candidates=[ADA, ZOE])
    state = restore_jobs.confirm_check(instance.stage_id, confirmed_by=CONFIRMED_BY, owner_user_id=ADA["user_id"], data_dir=instance.root)
    assert (state.status, state.owner_user_id) == ("pending", ADA["user_id"]), f"pending, owner ada: {state}"
    assert apply.read_restore(instance.root).owner_user_id == ADA["user_id"], "read_restore reads it back"
    print_success("confirm_check: owner handed on")


def test_a_state_written_before_b5_1_reads_no_owner(tmp_path):
    """(s) B5-1: ``restore.json`` without the owner's keys — every state written before B5-1 — still reads, its
    ``owner_user_id`` and ``owner_outcome`` ``None``, and it has no ``owner_reset_path`` at all."""
    apply = apply_module()
    root = tmp_path / "instance"
    root.mkdir(mode=0o700)
    ensure_private_dir(restore_dir(root), root)
    record = {
        "format": 1,
        "status": "committed",
        "stage_id": UNRELATED_CHECK,
        "data_dir": str(root.resolve()),
        "confirmed_at": "2026-10-15T22:00:00Z",
        "confirmed_by": CONFIRMED_BY,
        "confirmed_via": "admin",
        "backup_created_at": "2026-10-14T09:00:00Z",
        "backup_app_version": "v1.2.0",
        "action": "same",
        "finished_at": "2026-10-15T23:00:00Z",
    }
    state_file(root).write_text(json.dumps(record), encoding="utf-8")
    state_file(root).chmod(0o600)
    state = apply.read_restore(root)
    assert state is not None, "precondition: a state of before B5-1 is read"
    owner = tuple(getattr(state, name, "<missing>") for name in ("owner_user_id", "owner_outcome"))
    assert owner == (None, None), f"no owner: {owner}"
    assert not hasattr(state, "owner_reset_path"), "the state has no owner_reset_path"
    print_success("no keys: no owner")


# -----------------------------------------------------------------------------
# (s) Lot B5-1, security addendum §7.2: the owner's address the check used, and the copy's conflicts
# -----------------------------------------------------------------------------

#: The copy's conflicts a check may report (§7.1).
OWNER_CONFLICTS = ["address_is_a_username", "duplicate_email", "duplicate_username"]
#: A report checked with an address that is no longer the owner's, without one, or written before the addendum.
STALE_CHECKS = [
    pytest.param("someone.else.b51@example.com", id="checked-with-another-address"),
    pytest.param(None, id="checked-without-an-address"),
    pytest.param(ABSENT, id="a-report-written-before-the-addendum"),
]


def refused_with(apply: Any, instance: Instance, chosen: int | None) -> Any:
    """``confirm_restore`` via ``admin`` naming ``chosen``, expected refused: the error, once checked that nothing was
    written (no state, nothing of ``.restore`` changed but its apply lock, no restore waiting)."""
    before = but_the_apply_lock(instance.root)
    with pytest.raises(apply.RestoreStateError) as raised:
        apply.confirm_restore(instance.stage_id, confirmed_by=CONFIRMED_BY, confirmed_via="admin", owner_user_id=chosen, data_dir=instance.root, now=instance.confirm_at)
    assert not lexists(state_file(instance.root)), f"({raised.value.code}) a refused confirmation writes no state"
    assert but_the_apply_lock(instance.root) == before, f"({raised.value.code}) nothing of .restore changed: {cases.changed(before, but_the_apply_lock(instance.root))}"
    assert apply.read_restore(instance.root) is None, f"({raised.value.code}) no restore waits"
    return raised.value


@pytest.mark.parametrize("chosen", [None, ADA["user_id"]], ids=["none-chosen", "a-valid-choice"])
@pytest.mark.parametrize("checked_with", STALE_CHECKS)
def test_a_managed_confirmation_of_a_check_made_with_another_owner_address_is_outdated(tmp_path, databases, checked, monkeypatch, checked_with, chosen):
    """(s) B5-1 §7.2: ``managed``, via ``admin``: the owner's address now differs (``email_fold``) from the one the
    check used, the check used none, or its report predates the addendum: ``restore_stage_outdated`` («check the
    archive again»), before the choice itself is looked at (none chosen, or a valid one); nothing written."""
    print_section("(s) B5-1 §7.2 a check made with another owner's address")
    apply = apply_module()
    b51_parameter(apply.confirm_restore, "owner_user_id")
    instance = owner_case(tmp_path, databases, checked, monkeypatch, profile="managed", owner_email=OWNER_EMAIL, candidates=[ADA, ZOE], owner_email_checked=checked_with)
    shown = "<absent>" if checked_with is ABSENT else repr(checked_with)
    error = refused_with(apply, instance, chosen)
    assert error.code == "restore_stage_outdated", f"checked with {shown}: restore_stage_outdated, not {error.code}: {error}"
    print_success(f"{shown}: restore_stage_outdated")


@pytest.mark.parametrize("checked_with", [OWNER_EMAIL.lower(), OWNER_EMAIL.upper()], ids=["lower-case", "upper-case"])
def test_a_check_made_with_the_owner_s_address_in_another_case_is_not_outdated(tmp_path, databases, checked, monkeypatch, checked_with):
    """(s) B5-1 §7.2: the same address in another A–Z case is the same address: the confirmation goes on, the choice
    recorded."""
    apply = apply_module()
    b51_parameter(apply.confirm_restore, "owner_user_id")
    instance = owner_case(tmp_path, databases, checked, monkeypatch, profile="managed", owner_email=OWNER_EMAIL, candidates=[ADA, ZOE], owner_email_checked=checked_with)
    state = apply.confirm_restore(instance.stage_id, confirmed_by=CONFIRMED_BY, confirmed_via="admin", owner_user_id=ADA["user_id"], data_dir=instance.root, now=instance.confirm_at)
    assert (state.status, state.owner_user_id) == ("pending", ADA["user_id"]), f"checked with {checked_with!r}: confirmed: {state}"
    print_success(f"{checked_with!r}: confirmed")


#: (the candidates, the id chosen): every kind of choice, a valid one included.
EVERY_CHOICE = [
    pytest.param([ADA, ZOE], None, id="none-chosen"),
    pytest.param([ADA, ZOE], ADA["user_id"], id="an-active-administrator"),
    pytest.param([ADA, OWEN, ZOE], OWEN["user_id"], id="the-forced-user"),
    pytest.param([ADA, ZOE], NO_SUCH_USER, id="not-a-candidate"),
]


@pytest.mark.parametrize(("candidates", "chosen"), EVERY_CHOICE)
@pytest.mark.parametrize("conflicts", [[code] for code in OWNER_CONFLICTS] + [OWNER_CONFLICTS], ids=[*OWNER_CONFLICTS, "all-three"])
def test_a_managed_confirmation_of_a_copy_with_owner_conflicts_is_refused_whatever_the_choice(tmp_path, databases, checked, monkeypatch, conflicts, candidates, chosen):
    """(s) B5-1 §7.2: ``managed``, via ``admin``: a report whose ``owner_conflicts`` is not empty is refused
    ``owner_conflict`` (``RestoreOwnerConflictError``, a ``RestoreStateError``), whatever the choice — none, a valid
    one, the forced one, one that is no candidate; nothing written."""
    print_section("(s) B5-1 §7.2 owner conflicts")
    apply = apply_module()
    b51_parameter(apply.confirm_restore, "owner_user_id")
    conflict_error = getattr(apply, "RestoreOwnerConflictError", None)
    if conflict_error is None:
        pytest.fail("[new] B5-1 §7.2: apply.RestoreOwnerConflictError does not exist yet", pytrace=False)
    assert issubclass(conflict_error, apply.RestoreStateError) and conflict_error.code == "owner_conflict", f"RestoreOwnerConflictError is a RestoreStateError of code owner_conflict: {conflict_error.__mro__}, {conflict_error.code}"
    instance = owner_case(tmp_path, databases, checked, monkeypatch, profile="managed", owner_email=OWNER_EMAIL, candidates=candidates, owner_conflicts=conflicts)
    error = refused_with(apply, instance, chosen)
    assert (type(error).__name__, error.code) == ("RestoreOwnerConflictError", "owner_conflict"), f"{conflicts}, choice {chosen}: owner_conflict, not {type(error).__name__} {error.code}: {error}"
    print_success(f"{conflicts}, choice {chosen}: owner_conflict")


@pytest.mark.parametrize(("profile", "via"), [("selfhosted", "admin"), ("selfhosted", "cli"), ("selfhosted", "panel")])
def test_only_a_managed_confirmation_reads_the_owner_s_address_and_conflicts(tmp_path, databases, checked, monkeypatch, profile, via):
    """(s) B5-1 §7.2, narrowed by B5-1j: a self-hosted instance never reads the owner's address, whoever confirms: a report
    checked with another address and holding every conflict is confirmed as before (a guard). The managed command line and
    hosting panel read both since B5-1j: (v)."""
    apply = apply_module()
    instance = owner_case(tmp_path, databases, checked, monkeypatch, profile=profile, owner_email=OWNER_EMAIL, candidates=[ADA, ZOE], owner_email_checked="someone.else.b51@example.com", owner_conflicts=OWNER_CONFLICTS)
    state = apply.confirm_restore(instance.stage_id, confirmed_by=CONFIRMED_BY if via == "admin" else via, confirmed_via=via, data_dir=instance.root, now=instance.confirm_at)
    assert (state.status, state.confirmed_via) == ("pending", via), f"{profile} via {via}: confirmed as before: {state}"
    print_success(f"{profile} via {via}: confirmed")


# =============================================================================
# (t) Lot B5-1, security addendum §7.5: the chosen account closed at the commit
# =============================================================================
#
# Whoever prepared the backup knows the password of the account the owner chose. From the commit on — before A's call,
# and whether it ever comes — that password opens nothing: the account gets a bcrypt hash of a secret nobody sees, in
# the commit's own transaction, and, when the owner's address is set and no other account holds it, that address and
# the role of a protected administrator.

#: The password whoever prepared the backup gave every account of it.
BACKUP_PASSWORD = "b51-the-backup-s-own-password"
#: A bcrypt hash, as ``auth_service.hash_password`` makes one.
BCRYPT_HASH = re.compile(r"\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}")
#: The backup's accounts by name (``test_backup_staging.ACCOUNTS``) and their ids in the copy.
BOB_ID = 2
#: Bob holding the owner's address, his account disabled: the forced choice, neither active nor an administrator.
BOB_HOLDER = {"user_id": BOB_ID, "username": "bob_user", "email": "OWNER.b51@EXAMPLE.com", "is_superuser": False, "is_active": False}
#: A's column (its migration 006, in the head schema since A is merged): set to 1 for the chosen account only when it exists.
OWNER_COLUMN = "is_instance_owner"


def accounts_of(database: Path) -> dict[str, dict[str, Any]]:
    """Every account of ``database``, each row by column name, by username."""
    with closing(cases.read_only(database)) as conn:
        cursor = conn.execute("SELECT * FROM users")
        columns = [column[0] for column in cursor.description]
        return {row["username"]: row for row in (dict(zip(columns, values, strict=True)) for values in cursor.fetchall())}


def with_backup_passwords(database: Path) -> dict[str, str]:
    """Every account of ``database`` given a real bcrypt hash of ``BACKUP_PASSWORD``, each its own salt: the hashes by
    username."""
    with closing(sqlite3.connect(database)) as conn, conn:
        for (username,) in conn.execute("SELECT username FROM users").fetchall():
            conn.execute("UPDATE users SET hashed_password = ? WHERE username = ?", (auth_service.hash_password(BACKUP_PASSWORD), username))
    hashes = {name: row["hashed_password"] for name, row in accounts_of(database).items()}
    assert all(auth_service.verify_password(BACKUP_PASSWORD, value) for value in hashes.values()), "precondition: the backup's password opens every account"
    return hashes


def state_owner_is(root: Path, user_id: int) -> None:
    """``owner_user_id`` of the waiting restore rewritten in ``restore.json``: what the commit reads, whatever the
    confirmation allowed."""
    path = state_file(root)
    record = json.loads(path.read_text(encoding="utf-8"))
    record["owner_user_id"] = user_id
    path.write_text(json.dumps(record), encoding="utf-8")


def committed_after(apply: Any, instance: Instance, *, via: str = "admin", owner_user_id: int | None = None, before_apply: Callable[[], None] | None = None, before_commit: Callable[[], None] | None = None) -> tuple[Any, list[dict[str, Any]]]:
    """The instance's restore confirmed (via ``via``, naming ``owner_user_id``), applied and committed as a start does;
    ``before_apply`` run once it is confirmed, ``before_commit`` once it is applied. The state, and what the commit
    logged (its canary left out)."""
    by = CONFIRMED_BY if via == "admin" else via
    if owner_user_id is None:
        apply.confirm_restore(instance.stage_id, confirmed_by=by, confirmed_via=via, data_dir=instance.root, now=instance.confirm_at)
    else:
        apply.confirm_restore(instance.stage_id, confirmed_by=by, confirmed_via=via, owner_user_id=owner_user_id, data_dir=instance.root, now=instance.confirm_at)
    if before_apply is not None:
        before_apply()
    boot = never_ran(apply)
    apply.apply_pending_restore(instance.root, boot=boot, now=instance.applied_at)
    if before_commit is not None:
        before_commit()
    with logs() as events:
        state = apply.finish_pending_restore(instance.root, boot=boot, now=instance.committed_at)
    return state, [event for event in events if event.get("event") != LOG_CANARY]


def configured_address() -> str:
    """The owner's address as the configuration reads it (``configured_owner_email()``)."""
    from backend.app.services.platform.instance_backup.owner import configured_owner_email  # noqa: PLC0415

    address = configured_owner_email()
    assert address is not None, "precondition: the owner's address is set"
    return address


def closed(chosen: dict[str, Any], backup_hash: str) -> None:
    """The chosen account's password: a real bcrypt hash, not the backup's, which the backup's password no longer
    opens."""
    stored = chosen["hashed_password"]
    assert stored != backup_hash, "the chosen account's hash is not the backup's"
    assert BCRYPT_HASH.fullmatch(stored or ""), f"the chosen account holds a real bcrypt hash (length {len(stored or '')})"
    assert not auth_service.verify_password(BACKUP_PASSWORD, stored), "the backup's password no longer opens the chosen account"


def untouched_but(before: dict[str, dict[str, Any]], after: dict[str, dict[str, Any]], *names: str) -> None:
    """Every account but ``names`` as the backup held it, its session version aside (the commit's own)."""
    left = {name: {key: value for key, value in row.items() if key != "session_version"} for name, row in before.items() if name not in names}
    now = {name: {key: value for key, value in row.items() if key != "session_version"} for name, row in after.items() if name not in names}
    assert now == left, f"the other accounts as the backup held them: {sorted(name for name in left if left[name] != now.get(name))}"


def nothing_secret_logged(events: list[dict[str, Any]], *texts: str) -> None:
    """No log line of the commit holds an address, a username, a hash or the backup's password, in any case."""
    lines = repr(events).lower()
    shown = sorted({text for text in texts if text and text.lower() in lines})
    assert shown == [], f"the commit's log holds {len(shown)} secret(s) or personal value(s): {shown}"


def owner_line(events: list[dict[str, Any]], stage_id: str, user_id: int) -> list[Any]:
    """The ``assigned`` of each line of the commit naming the restore's stage and the chosen account."""
    return [event.get("assigned") for event in events if event.get("stage_id") == stage_id and event.get("user_id") == user_id and "assigned" in event]


def b51_close_parameter(apply: Any) -> None:
    """``_close_the_way_in`` takes ``owner_user_id`` (default ``None``); before §7.5, a failure that says so."""
    parameter = inspect.signature(apply._close_the_way_in).parameters.get("owner_user_id")
    if parameter is None:
        pytest.fail("[new] B5-1 §7.5: apply._close_the_way_in() takes no owner_user_id yet", pytrace=False)
    assert parameter.default is None, f"owner_user_id defaults to None: {parameter.default!r}"


#: (the chosen account by name, what the copy holds for it first, the candidates).
CHOSEN_ACCOUNTS = [
    pytest.param("ada_admin", None, [ADA, ZOE], id="an-active-administrator"),
    pytest.param("bob_user", BOB_HOLDER, [ADA, BOB_HOLDER, ZOE], id="the-address-holder-a-disabled-plain-user"),
]


@pytest.mark.parametrize(("chosen_name", "holder", "candidates"), CHOSEN_ACCOUNTS)
def test_the_commit_closes_the_chosen_account_and_gives_it_the_owner_s_address(tmp_path, databases, checked, monkeypatch, chosen_name, holder, candidates):
    """(t) B5-1 §7.5: a restore confirmed from the app of a managed instance, naming an account: at the commit, that
    account holds a real bcrypt hash that is not the backup's and that the backup's password does not open; its email
    is the owner's address, ``is_superuser`` and ``is_active`` 1 (A's ``is_instance_owner`` column absent here: no
    error). Every other account as the backup held it; the restore committed. One line names the stage, the account and
    ``assigned`` true; no line holds an address, a username, a hash or the password."""
    print_section("(t) B5-1 §7.5 the chosen account closed at the commit")
    apply = apply_module()
    b51_parameter(apply.confirm_restore, "owner_user_id")
    instance = owner_case(tmp_path, databases, checked, monkeypatch, profile="managed", owner_email=OWNER_EMAIL, candidates=candidates)
    copy_database = instance.copy / DATABASE_ENTRY
    if holder is not None:
        cases.execute(copy_database, f"UPDATE users SET email = '{holder['email']}', is_active = 0 WHERE id = {holder['user_id']}")
    hashes = with_backup_passwords(copy_database)
    before = accounts_of(copy_database)
    chosen_id = before[chosen_name]["id"]
    assert OWNER_COLUMN in before[chosen_name], f"precondition: A's {OWNER_COLUMN} (its migration 006) is in the head schema"
    state, events = committed_after(apply, instance, owner_user_id=chosen_id)
    assert (state.status, state.owner_user_id) == ("committed", chosen_id), f"committed, the owner {chosen_id}: {state}"
    after = accounts_of(instance.root / DATABASE_ENTRY)
    chosen = after[chosen_name]
    closed(chosen, hashes[chosen_name])
    address = configured_address()
    assert (chosen["email"], chosen["is_superuser"], chosen["is_active"]) == (address, 1, 1), f"the owner's address, an active administrator: {(chosen['email'] == address, chosen['is_superuser'], chosen['is_active'])}"
    untouched_but(before, after, chosen_name)
    assert owner_line(events, instance.stage_id, chosen_id) == [True], f"one line: stage, account, assigned true: {logged(events)}"
    nothing_secret_logged(events, OWNER_EMAIL, address, BOB_HOLDER["email"], BACKUP_PASSWORD, chosen["hashed_password"], *hashes.values(), *(row["email"] for row in before.values()), *before)
    print_success(f"{chosen_name}: closed, the owner's address, an active administrator")


#: A real bcrypt hash (cost 4) of a secret nobody knows, made once with ``auth_service.hash_password``: what a faked
#: ``auth_service.unusable_password_hash`` answers, so that a hash the commit made itself cannot be mistaken for it.
UNUSABLE_SENTINEL = "$2b$04$dL/FsEAkMOTYguoge.H9V.fvCJ4tIdBJFGxDqRHDXrnDCnrwQKKQC"


def test_the_commit_takes_the_chosen_account_s_unusable_hash_from_a_s_auth_service(tmp_path, databases, checked, monkeypatch):
    """(t) B5-1e: the commit does not make its own unusable hash: the chosen account's ``hashed_password`` is exactly what
    ``auth_service.unusable_password_hash()`` answers (asked once), and no other account's password changed."""
    apply = apply_module()
    instance = owner_case(tmp_path, databases, checked, monkeypatch, profile="managed", owner_email=OWNER_EMAIL, candidates=[ADA, ZOE])
    hashes = with_backup_passwords(instance.copy / DATABASE_ENTRY)
    asked: list[str] = []

    def sentinel() -> str:
        asked.append("asked")
        return UNUSABLE_SENTINEL

    monkeypatch.setattr(auth_service, "unusable_password_hash", sentinel)
    state, _events = committed_after(apply, instance, owner_user_id=ADA["user_id"])
    assert state.status == "committed", f"committed: {state}"
    after = accounts_of(instance.root / DATABASE_ENTRY)
    assert after["ada_admin"]["hashed_password"] == UNUSABLE_SENTINEL, "[new] B5-1e: the chosen account holds the hash auth_service.unusable_password_hash() answered"
    assert asked == ["asked"], f"asked once, for the one chosen account: {asked}"
    assert {name: row["hashed_password"] for name, row in after.items() if name != "ada_admin"} == {name: value for name, value in hashes.items() if name != "ada_admin"}, "no other account's password changed"
    print_success("the unusable hash is A's")


def test_the_commit_marks_the_instance_owner_where_a_s_column_exists(tmp_path, databases, checked, monkeypatch):
    """(t) B5-1 §7.5: where the restored database has A's ``is_instance_owner`` column (its migration 006), the chosen
    account gets 1 there, every other account keeps its 0."""
    apply = apply_module()
    b51_parameter(apply.confirm_restore, "owner_user_id")
    instance = owner_case(tmp_path, databases, checked, monkeypatch, profile="managed", owner_email=OWNER_EMAIL, candidates=[ADA, ZOE])
    copy_database = instance.copy / DATABASE_ENTRY
    assert OWNER_COLUMN in accounts_of(copy_database)["ada_admin"], f"precondition: the head schema has A's {OWNER_COLUMN} (its migration 006)"
    hashes = with_backup_passwords(copy_database)
    state, _events = committed_after(apply, instance, owner_user_id=ADA["user_id"])
    assert state.status == "committed", f"committed: {state}"
    after = accounts_of(instance.root / DATABASE_ENTRY)
    closed(after["ada_admin"], hashes["ada_admin"])
    marked = {name: row[OWNER_COLUMN] for name, row in after.items()}
    assert marked == {name: int(name == "ada_admin") for name in after}, f"{OWNER_COLUMN}: the chosen account only: {marked}"
    print_success(f"{OWNER_COLUMN}: ada only")


def test_when_another_account_holds_the_owner_s_address_only_the_password_changes(tmp_path, databases, checked, monkeypatch):
    """(t) B5-1 §7.5: another account of the backup holds the owner's address (A–Z case aside): the chosen account's
    password is closed and nothing else of it changes — its email, its role, its state —, the holder keeps its address
    (the unique index never violated, no ``IntegrityError``), the restore committed. A warning names the stage and the
    account, the line says ``assigned`` false; never the address."""
    apply = apply_module()
    b51_parameter(apply.confirm_restore, "owner_user_id")
    instance = owner_case(tmp_path, databases, checked, monkeypatch, profile="managed", owner_email=OWNER_EMAIL, candidates=[ADA, ZOE])
    copy_database = instance.copy / DATABASE_ENTRY
    holder_email = "OWNER.b51@EXAMPLE.com"
    # After the check: the report names no holder, so the confirmation allows ada; the commit reads the database.
    cases.execute(copy_database, f"UPDATE users SET email = '{holder_email}' WHERE username = 'zoe_admin'")
    hashes = with_backup_passwords(copy_database)
    before = accounts_of(copy_database)
    try:
        state, events = committed_after(apply, instance, owner_user_id=ADA["user_id"])
    except sqlite3.IntegrityError as exc:
        pytest.fail(f"the commit violated the unique index of the addresses: {type(exc).__name__}", pytrace=False)
    assert state.status == "committed", f"committed all the same: {state}"
    after = accounts_of(instance.root / DATABASE_ENTRY)
    ada = after["ada_admin"]
    closed(ada, hashes["ada_admin"])
    assert {key: value for key, value in ada.items() if key not in ("hashed_password", "session_version")} == {key: value for key, value in before["ada_admin"].items() if key not in ("hashed_password", "session_version")}, "only ada's password changed"
    untouched_but(before, after, "ada_admin")
    assert owner_line(events, instance.stage_id, ADA["user_id"]) == [False], f"one line: stage, account, assigned false: {logged(events)}"
    warned = [event for event in events if event.get("log_level") in ("warning", "error", "critical") and event.get("user_id") == ADA["user_id"] and event.get("stage_id") == instance.stage_id]
    assert warned, f"a warning names the stage and the account: {logged(events)}"
    nothing_secret_logged(events, OWNER_EMAIL, holder_email, configured_address(), BACKUP_PASSWORD, ada["hashed_password"], *hashes.values(), *before)
    print_success("another holder: only the password, committed")


def test_without_the_owner_s_address_at_the_commit_only_the_password_changes(tmp_path, databases, checked, monkeypatch):
    """(t) B5-1 §7.5: the owner's address unset when the commit runs: the chosen account (here a plain user, named in
    the state) has its password closed, and keeps its email, its role and its state."""
    apply = apply_module()
    b51_parameter(apply.confirm_restore, "owner_user_id")
    instance = owner_case(tmp_path, databases, checked, monkeypatch, profile="managed", owner_email=OWNER_EMAIL, candidates=[ADA, ZOE])
    copy_database = instance.copy / DATABASE_ENTRY
    hashes = with_backup_passwords(copy_database)
    before = accounts_of(copy_database)
    assert before["bob_user"]["id"] == BOB_ID and before["bob_user"]["is_superuser"] == 0, "precondition: bob is a plain user"
    state, events = committed_after(apply, instance, owner_user_id=ADA["user_id"], before_apply=lambda: state_owner_is(instance.root, BOB_ID), before_commit=lambda: owner_email_is(monkeypatch, None))
    assert (state.status, state.owner_user_id) == ("committed", BOB_ID), f"committed, the owner bob: {state}"
    after = accounts_of(instance.root / DATABASE_ENTRY)
    bob = after["bob_user"]
    closed(bob, hashes["bob_user"])
    assert {key: value for key, value in bob.items() if key not in ("hashed_password", "session_version")} == {key: value for key, value in before["bob_user"].items() if key not in ("hashed_password", "session_version")}, "only bob's password changed"
    untouched_but(before, after, "bob_user")
    nothing_secret_logged(events, OWNER_EMAIL, BACKUP_PASSWORD, bob["hashed_password"], *hashes.values(), *before)
    print_success("no address: only the password")


def test_an_owner_the_restored_database_does_not_hold_changes_nothing_and_the_commit_goes_on(tmp_path, databases, checked, monkeypatch):
    """(t) B5-1 §7.5: the state names an account the restored database does not hold: no account touched, a warning
    naming the stage and the id, the restore committed."""
    apply = apply_module()
    b51_parameter(apply.confirm_restore, "owner_user_id")
    b51_close_parameter(apply)
    instance = owner_case(tmp_path, databases, checked, monkeypatch, profile="managed", owner_email=OWNER_EMAIL, candidates=[ADA, ZOE])
    copy_database = instance.copy / DATABASE_ENTRY
    with_backup_passwords(copy_database)
    before = accounts_of(copy_database)
    state, events = committed_after(apply, instance, owner_user_id=ADA["user_id"], before_apply=lambda: state_owner_is(instance.root, NO_SUCH_USER))
    assert (state.status, state.owner_user_id) == ("committed", NO_SUCH_USER), f"committed: {state}"
    untouched_but(before, accounts_of(instance.root / DATABASE_ENTRY))
    warned = [event for event in events if event.get("log_level") in ("warning", "error", "critical") and event.get("user_id") == NO_SUCH_USER and event.get("stage_id") == instance.stage_id]
    assert warned, f"a warning names the stage and the id: {logged(events)}"
    print_success("no such account: nothing touched, committed")


#: (the profile, how it was confirmed, the owner's address): the restores that name no owner. B5-1j: a managed command line or
#: hosting panel names none only without the owner's address; with it they pick one, or record that none was found: (v).
NO_OWNER_NAMED = [
    pytest.param("managed", "cli", None, id="managed-cli-no-address"),
    pytest.param("managed", "panel", None, id="managed-panel-no-address"),
    pytest.param("selfhosted", "admin", OWNER_EMAIL, id="selfhosted-admin"),
    pytest.param("selfhosted", "cli", OWNER_EMAIL, id="selfhosted-cli"),
    pytest.param("selfhosted", "panel", OWNER_EMAIL, id="selfhosted-panel"),
]


@pytest.mark.parametrize(("profile", "via", "owner_email"), NO_OWNER_NAMED)
def test_a_restore_without_an_owner_touches_no_password_at_the_commit(tmp_path, databases, checked, monkeypatch, profile, via, owner_email):
    """(t) B5-1 §7.5: a restore that names no owner (a managed command line or panel without the owner's address, a
    self-hosted instance): at the commit every account is as the backup held it (its session version aside), as before.
    Barrier: ``_close_the_way_in`` takes ``owner_user_id``."""
    apply = apply_module()
    b51_close_parameter(apply)
    instance = owner_case(tmp_path, databases, checked, monkeypatch, profile=profile, owner_email=owner_email, candidates=[ADA, ZOE])
    copy_database = instance.copy / DATABASE_ENTRY
    with_backup_passwords(copy_database)
    before = accounts_of(copy_database)
    state, _events = committed_after(apply, instance, via=via)
    assert (state.status, state.owner_user_id, state.owner_outcome) == ("committed", None, None), f"{profile} via {via}: committed, no owner, no outcome: {state}"
    untouched_but(before, accounts_of(instance.root / DATABASE_ENTRY))
    print_success(f"{profile} via {via}: no password touched")


@pytest.mark.asyncio
async def test_close_the_way_in_without_an_owner_keeps_its_contract(tmp_path, databases, checked):
    """(t) B5-1 §7.5: ``_close_the_way_in(data_dir, now)`` — no ``owner_user_id`` — answers ``(value, revoked)`` and
    changes only the session versions and the live links, as (h) pins; ``owner_user_id`` defaults to ``None``."""
    apply = apply_module()
    b51_close_parameter(apply)
    instance = build(tmp_path / "instance", databases, checked)
    now = restore_time_of(instance, "utc")
    await written(instance.copy / DATABASE_ENTRY, RESTORED_LINKS, now)
    with_backup_passwords(instance.copy / DATABASE_ENTRY)
    confirm(apply, instance)
    apply.apply_pending_restore(instance.root, boot=never_ran(apply), now=instance.applied_at)
    database = instance.root / DATABASE_ENTRY
    before = accounts_of(database)
    assert apply._close_the_way_in(instance.root, now) == (millis(now), LIVE_RESTORED), "(the session value, the links revoked)"
    untouched_but(before, accounts_of(database))
    print_success("no owner: the contract of (h)")


@pytest.mark.asyncio
async def test_the_owner_s_password_changes_with_the_sessions_and_the_links_or_not_at_all(tmp_path, databases, checked, monkeypatch):
    """(t) B5-1 §7.5: the owner's account is closed in the commit's own transaction: a trigger of the restored database
    refusing the update of a password leaves the session versions and the links unchanged too. Whether the refusal
    reaches the caller is not this test's question."""
    apply = apply_module()
    b51_close_parameter(apply)
    # B5-1j: the command line's confirmation on a managed instance with the owner's address reads the report's address and
    # candidates, so the report is the one a check made with that address writes (no candidate: nobody picked).
    instance = owner_case(tmp_path, databases, checked, monkeypatch, profile="managed", owner_email=OWNER_EMAIL, candidates=[ADA, ZOE])
    now = restore_time_of(instance, "utc")
    await written(instance.copy / DATABASE_ENTRY, RESTORED_LINKS, now)
    apply.confirm_restore(instance.stage_id, confirmed_by="cli", confirmed_via="cli", data_dir=instance.root, now=instance.confirm_at)
    apply.apply_pending_restore(instance.root, boot=never_ran(apply), now=instance.applied_at)
    database = instance.root / DATABASE_ENTRY
    cases.execute(database, "CREATE TRIGGER b51_refused BEFORE UPDATE OF hashed_password ON users BEGIN SELECT RAISE(ABORT, 'refused by the test'); END")
    snapshot = rows_by_table(database)
    try:
        outcome: object = apply._close_the_way_in(instance.root, now, owner_user_id=ADA["user_id"])
    except Exception as exc:  # whether the refusal reaches the caller is not this test's question
        outcome = exc
    assert rows_by_table(database) == snapshot, f"the owner's password refused: neither the sessions nor the links may have changed ({type(outcome).__name__})"
    print_success("the password refused: nothing changed")


# =============================================================================
# (u) Lot B5-1g: the owner's flag of the backup, the commit's connection, a pending administrator
# =============================================================================
#
# ``users.is_instance_owner`` (A's migration 006) marks the one account that is the instance's owner, and a partial unique
# index allows one. A backup carries its author's flag. The restored instance's owner is the account the restore
# assigns, so the commit clears the flag of EVERY account first, then sets it on the chosen account only when that
# account was assigned. A restore that assigns nobody (the hosting panel, the command line, an owner whose address another
# account holds, an address no longer set, an account the database does not hold) ends with no account flagged: the
# owner's account does not exist yet, and A's call (or the next admin-bootstrap) creates it.


def flags_of(database: Path) -> dict[str, int]:
    """``is_instance_owner`` of every account of ``database``, by username."""
    return {name: row[OWNER_COLUMN] for name, row in accounts_of(database).items()}


def flag_the_backups_owner(database: Path, username: str) -> None:
    """The backup's author's flag: ``username`` marked as the instance owner in the copy. Barrier: it is the only one."""
    cases.execute(database, f"UPDATE users SET {OWNER_COLUMN} = 1 WHERE username = '{username}'")
    assert sorted(name for name, value in flags_of(database).items() if value) == [username], f"precondition: the copy flags {username} only: {flags_of(database)}"


@pytest.mark.parametrize(("profile", "via", "owner_email"), NO_OWNER_NAMED)
def test_a_restore_naming_no_owner_ends_with_no_account_flagged_as_the_instance_owner(tmp_path, databases, checked, monkeypatch, profile, via, owner_email):
    """(u) B5-1g: a restore that names no owner (a managed command line or panel without the owner's address, a self-hosted
    instance, whoever confirms): the commit clears ``is_instance_owner`` of every account, so the backup author's flag
    does not survive. Committed. Red before B5-1g: the flag stayed on the account it was on."""
    print_section("(u) B5-1g no owner named: no flag")
    apply = apply_module()
    instance = owner_case(tmp_path, databases, checked, monkeypatch, profile=profile, owner_email=owner_email, candidates=[ADA, ZOE])
    flag_the_backups_owner(instance.copy / DATABASE_ENTRY, "zoe_admin")
    state, _events = committed_after(apply, instance, via=via)
    assert (state.status, state.owner_user_id, state.owner_outcome) == ("committed", None, None), f"{profile} via {via}: committed, no owner, no outcome: {state}"
    flags = flags_of(instance.root / DATABASE_ENTRY)
    assert set(flags.values()) == {0}, f"no account is the instance owner: {sorted(name for name, value in flags.items() if value)}"
    print_success(f"{profile} via {via}: no flag")


def holder_of_the_address(instance: Instance, monkeypatch: pytest.MonkeyPatch) -> None:
    """Another account of the copy (``zoe_admin``) holds the owner's address, after the check: the confirmation allows
    ada, the commit reads the database."""
    del monkeypatch
    cases.execute(instance.copy / DATABASE_ENTRY, "UPDATE users SET email = 'OWNER.b51@EXAMPLE.com' WHERE username = 'zoe_admin'")


#: (the name of the case, what changes between the confirmation and the commit); the backup flags ``zoe_admin`` in each.
NOT_ASSIGNED_CASES = ["another-account-holds-the-address", "the-address-is-no-longer-set", "the-database-has-no-such-account"]


@pytest.mark.parametrize("case", NOT_ASSIGNED_CASES)
def test_an_owner_who_was_not_assigned_leaves_no_account_flagged(tmp_path, databases, checked, monkeypatch, case):
    """(u) B5-1g: an owner IS chosen but the commit cannot assign them (another account holds the address, the address is
    no longer set, the database does not hold the account): the flag of the backup's author is cleared all the same and
    nobody is set, so no account is flagged. Committed. Red before B5-1g: the others kept their flag."""
    print_section(f"(u) B5-1g owner not assigned: {case}")
    apply = apply_module()
    instance = owner_case(tmp_path, databases, checked, monkeypatch, profile="managed", owner_email=OWNER_EMAIL, candidates=[ADA, ZOE])
    copy_database = instance.copy / DATABASE_ENTRY
    flag_the_backups_owner(copy_database, "zoe_admin")
    before = accounts_of(copy_database)
    options: dict[str, Any] = {}
    if case == "another-account-holds-the-address":
        holder_of_the_address(instance, monkeypatch)
    elif case == "the-address-is-no-longer-set":
        options["before_commit"] = lambda: owner_email_is(monkeypatch, None)
    else:
        options["before_apply"] = lambda: state_owner_is(instance.root, NO_SUCH_USER)
    state, events = committed_after(apply, instance, owner_user_id=ADA["user_id"], **options)
    assert state.status == "committed", f"committed all the same: {state}"
    after = accounts_of(instance.root / DATABASE_ENTRY)
    flags = {name: row[OWNER_COLUMN] for name, row in after.items()}
    assert set(flags.values()) == {0}, f"no account is the instance owner: {sorted(name for name, value in flags.items() if value)}"
    assert after["ada_admin"]["email"] == before["ada_admin"]["email"], "the chosen account did not take the owner's address (it was not assigned)"
    nothing_secret_logged(events, OWNER_EMAIL, "OWNER.b51@EXAMPLE.com", *before)
    print_success(f"{case}: no flag")


def test_the_assigned_owner_is_the_only_account_flagged_whatever_the_backup_flagged(tmp_path, databases, checked, monkeypatch):
    """(u) B5-1g, the guard: the backup flags ``zoe_admin``, the owner chooses ``ada_admin`` and it is assigned: ada is
    flagged and zoe is not — the flag of the chosen account is not lost when every flag is cleared first. Green before
    B5-1g, and it must stay so."""
    apply = apply_module()
    instance = owner_case(tmp_path, databases, checked, monkeypatch, profile="managed", owner_email=OWNER_EMAIL, candidates=[ADA, ZOE])
    flag_the_backups_owner(instance.copy / DATABASE_ENTRY, "zoe_admin")
    state, events = committed_after(apply, instance, owner_user_id=ADA["user_id"])
    assert (state.status, state.owner_user_id) == ("committed", ADA["user_id"]), f"committed, the owner ada: {state}"
    assert owner_line(events, instance.stage_id, ADA["user_id"]) == [True], f"ada was assigned: {logged(events)}"
    flags = flags_of(instance.root / DATABASE_ENTRY)
    assert flags == {name: int(name == "ada_admin") for name in flags}, f"{OWNER_COLUMN}: ada only: {flags}"
    print_success("ada flagged, zoe not")


@pytest.mark.parametrize("owner_chosen", [True, False], ids=["owner-chosen", "no-owner"])
def test_a_database_without_the_owner_column_still_commits(tmp_path, databases, checked, monkeypatch, owner_chosen):
    """(u) B5-1g, the guard: a backup whose database has no ``is_instance_owner`` column (a schema before A's migration 006,
    here the head's index and column dropped after the check) is committed as before: no error, the sessions and the
    links closed, the chosen account closed and given the owner's address. Green before B5-1g, and it must stay so."""
    apply = apply_module()
    instance = owner_case(tmp_path, databases, checked, monkeypatch, profile="managed", owner_email=OWNER_EMAIL, candidates=[ADA, ZOE])
    copy_database = instance.copy / DATABASE_ENTRY
    cases.execute(copy_database, "DROP INDEX ux_users_instance_owner", f"ALTER TABLE users DROP COLUMN {OWNER_COLUMN}")
    assert OWNER_COLUMN not in accounts_of(copy_database)["ada_admin"], "precondition: the copy has no owner column"
    state, _events = committed_after(apply, instance, owner_user_id=ADA["user_id"] if owner_chosen else None, via="admin" if owner_chosen else "cli")
    assert state.status == "committed", f"committed: {state}"
    after = accounts_of(instance.root / DATABASE_ENTRY)
    assert OWNER_COLUMN not in after["ada_admin"], "the column is still absent: the commit added nothing"
    if owner_chosen:
        assert (after["ada_admin"]["email"], after["ada_admin"]["is_superuser"], after["ada_admin"]["is_active"]) == (configured_address(), 1, 1), "the chosen account took the owner's address, an active administrator"
    print_success(f"no column, {'owner chosen' if owner_chosen else 'no owner'}: committed")


# -----------------------------------------------------------------------------
# (u) B5-1g: the connection the commit opens runs with trusted_schema off, like every other reader of a copy
# -----------------------------------------------------------------------------


@pytest.mark.parametrize("owner_chosen", [False, True], ids=["no-owner", "owner-chosen"])
def test_the_connection_the_commit_opens_on_the_restored_database_turns_trusted_schema_off_first(tmp_path, databases, checked, monkeypatch, owner_chosen):
    """(u) B5-1g: the read-write connection of ``_close_the_way_in`` on the restored database runs ``PRAGMA trusted_schema =
    OFF`` before any other statement (B-37: the schema of a copy may call a function in a view, a trigger, a CHECK or
    a default; with the setting off it can reach none that is not harmless). Recorded as test_backup_staging.py records
    the connections of a check. Red before B5-1g: the first statement is the busy timeout."""
    print_section("(u) B5-1g trusted_schema off first at the commit")
    apply = apply_module()
    instance = owner_case(tmp_path, databases, checked, monkeypatch, profile="managed", owner_email=OWNER_EMAIL, candidates=[ADA, ZOE])
    opened: list[Any] = []
    live = (instance.root / DATABASE_ENTRY).resolve()

    def record_connections() -> None:
        monkeypatch.setattr(apply, "sqlite3", cases.RecordingConnect(sqlite3, "apply", opened))

    if owner_chosen:
        state, _events = committed_after(apply, instance, owner_user_id=ADA["user_id"], before_commit=record_connections)
    else:
        state, _events = committed_after(apply, instance, via="cli", before_commit=record_connections)
    assert state.status == "committed", f"committed: {state}"
    on_live = [record for record in opened if record.path == live]
    assert on_live, f"precondition: the commit opened the restored database through apply.sqlite3: {[(record.by, record.target) for record in opened]}"
    trusting = [record for record in on_live if not cases.turns_trust_off_first(record)]
    assert not trusting, f"every connection of the commit to the restored database turns trusted_schema off first: {cases.first_statements(trusting)}"
    print_success(f"{len(on_live)} connection(s), trusted_schema=OFF first")


def test_the_read_only_connection_that_reads_the_largest_session_version_turns_trusted_schema_off_first(tmp_path, monkeypatch):
    """(u) B5-1h: ``_largest_session_version`` (the ``previous/`` database at the commit) opens a read-only connection
    and runs ``PRAGMA trusted_schema = OFF`` before its SELECT, as every other reader of a copy does (B-37). Recorded as
    the test above records the commit's connection. The value is pinned too: the largest ``session_version`` of the
    accounts, and 0 for a file that is missing or is no file (no connection opened for either). Red before B5-1h only
    for the first statement: it is the SELECT."""
    print_section("(u) B5-1h trusted_schema off first in _largest_session_version")
    apply = apply_module()
    database = tmp_path / "previous.db"
    with closing(sqlite3.connect(database)) as conn, conn:
        conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, session_version INTEGER NOT NULL DEFAULT 0)")
        conn.executemany("INSERT INTO users (session_version) VALUES (?)", [(3,), (9,), (5,)])
    opened: list[Any] = []
    monkeypatch.setattr(apply, "sqlite3", cases.RecordingConnect(sqlite3, "apply", opened))

    largest = apply._largest_session_version(database)
    assert largest == 9, f"the largest session version of the accounts: {largest}"
    on_database = [record for record in opened if record.path == database.resolve()]
    assert len(on_database) == 1, f"one connection opened on the database: {[(record.by, record.target) for record in opened]}"
    assert on_database[0].opened_read_only, f"read only, as a mode=ro URI: {on_database[0].target}"
    assert cases.turns_trust_off_first(on_database[0]), f"the first statement of the connection turns trusted_schema off: {cases.first_statements(on_database)}"
    assert any("session_version" in statement for statement in on_database[0].statements[1:]), f"the SELECT follows the PRAGMA: {on_database[0].statements}"

    opened.clear()
    folder = tmp_path / "a-folder"
    folder.mkdir()
    for absent in (tmp_path / "missing.db", folder):
        assert apply._largest_session_version(absent) == 0, f"{absent.name}: 0, no database to read"
    assert opened == [], f"no connection opened for a missing database or a folder: {[(record.by, record.target) for record in opened]}"
    print_success("trusted_schema=OFF first; 9 for the database, 0 for a missing file and a folder")


# -----------------------------------------------------------------------------
# (u) B5-1g: a pending administrator of the backup refuses the owner's confirmation
# -----------------------------------------------------------------------------

PENDING_ADMIN = "pend_admin"
INSERT_PENDING_ADMIN = "INSERT INTO users (username, email, hashed_password, is_active, is_superuser, created_at, updated_at) VALUES (?, 'pend.b51@example.com', 'x', 0, 1, ?, ?)"


def plant_pending_administrator(database: Path) -> None:
    """An administrator waiting for its setup in the copy: inactive, with an admin-setup link nobody used."""
    with closing(sqlite3.connect(database)) as conn, conn:
        conn.execute(INSERT_PENDING_ADMIN, (PENDING_ADMIN, cases.CREATED, cases.CREATED))
    cases.add_tokens(database, [(PENDING_ADMIN, "admin_setup", False)])


def checked_report_of(instance: Instance) -> list[str]:
    """What the check says of the owner's conflicts for the copy as it is now (``staging._owner_check``), written into the
    report as the check writes it; the codes."""
    from backend.app.services.platform.instance_backup import staging  # noqa: PLC0415

    _address, _candidates, conflicts = staging._owner_check(instance.copy / DATABASE_ENTRY)
    with_candidates(instance, [ADA, ZOE], owner_conflicts=conflicts)
    return conflicts


@pytest.mark.parametrize("chosen", [None, ADA["user_id"]], ids=["none-chosen", "a-valid-choice"])
def test_a_managed_confirmation_of_a_copy_with_a_pending_administrator_is_refused_as_owner_conflict(tmp_path, databases, checked, monkeypatch, chosen):
    """(u) B5-1g: the copy holds a pending administrator and nobody holds the owner's address: the check reports
    ``pending_administrator`` and the confirmation via ``admin`` on ``managed`` is refused ``owner_conflict``
    (``RestoreOwnerConflictError``) whatever the choice, naming the code; nothing written. Red before B5-1g: the check
    reported no conflict and the confirmation went through."""
    print_section("(u) B5-1g a pending administrator refuses the confirmation")
    apply = apply_module()
    instance = owner_case(tmp_path, databases, checked, monkeypatch, profile="managed", owner_email=OWNER_EMAIL, candidates=[ADA, ZOE])
    plant_pending_administrator(instance.copy / DATABASE_ENTRY)
    conflicts = checked_report_of(instance)
    assert conflicts == ["pending_administrator"], f"the check reports the pending administrator: {conflicts}"
    error = refused_with(apply, instance, chosen)
    assert (type(error).__name__, error.code) == ("RestoreOwnerConflictError", "owner_conflict"), f"owner_conflict, not {type(error).__name__} {error.code}: {error}"
    assert "pending_administrator" in str(error), f"the refusal names the code: {error}"
    print_success(f"choice {chosen}: owner_conflict")


def test_a_pending_administrator_does_not_refuse_when_another_account_holds_the_owner_s_address(tmp_path, databases, checked, monkeypatch):
    """(u) B5-1g, the guard: the same pending administrator, but another account of the copy holds the owner's address:
    no conflict, the forced choice is confirmed. Green before B5-1g, and it must stay so."""
    apply = apply_module()
    instance = owner_case(tmp_path, databases, checked, monkeypatch, profile="managed", owner_email=OWNER_EMAIL, candidates=[ADA, OWEN, ZOE])
    holder_of_the_address(instance, monkeypatch)
    plant_pending_administrator(instance.copy / DATABASE_ENTRY)
    assert checked_report_of(instance) == [], "no conflict: an account holds the owner's address"
    with_candidates(instance, [ADA, OWEN, ZOE], owner_conflicts=[])
    state = apply.confirm_restore(instance.stage_id, confirmed_by=CONFIRMED_BY, confirmed_via="admin", owner_user_id=OWEN["user_id"], data_dir=instance.root, now=instance.confirm_at)
    assert (state.status, state.owner_user_id) == ("pending", OWEN["user_id"]), f"confirmed: {state}"
    print_success("another holder: confirmed")


@pytest.mark.parametrize("conflicts", [["pending_administrator"], ["duplicate_email", "pending_administrator"], [*OWNER_CONFLICTS, "pending_administrator"]], ids=["pending-alone", "duplicate-email-and-pending", "every-code"])
def test_every_conflict_code_still_refuses_and_is_named(tmp_path, databases, checked, monkeypatch, conflicts):
    """(u) B5-1g, the guard: a report whose ``owner_conflicts`` holds the earlier codes, alone or with the new one, is refused
    ``owner_conflict`` as before, and the refusal names every code. Green before B5-1g, and it must stay so."""
    apply = apply_module()
    instance = owner_case(tmp_path, databases, checked, monkeypatch, profile="managed", owner_email=OWNER_EMAIL, candidates=[ADA, ZOE], owner_conflicts=conflicts)
    error = refused_with(apply, instance, ADA["user_id"])
    assert (type(error).__name__, error.code) == ("RestoreOwnerConflictError", "owner_conflict"), f"owner_conflict: {type(error).__name__} {error.code}"
    assert all(code in str(error) for code in conflicts), f"the refusal names every code {conflicts}: {error}"
    print_success(f"{conflicts}: owner_conflict")


# =============================================================================
# (v) Lot B5-1j: the owner's account of a restore confirmed from the command line or by the hosting panel
# =============================================================================
#
# The analysis (§2) is the contract. On ``managed`` with ``LIBREFOLIO_ADMIN_EMAIL`` set, a confirmation via ``cli`` or
# ``panel`` picks the owner's account itself from the staged report (``apply.pick_owner``) and stores it in the state; the
# commit, the startup step and the guard are the app path's machinery. Nothing here names an address or a username in a log.

VIA_NO_ADMIN = ["cli", "panel"]
#: The codes ``owner_conflicts`` may hold (B5-1 §7.1 and B5-1g).
EVERY_CONFLICT = [*OWNER_CONFLICTS, "pending_administrator"]
#: What the advice of the refusal says to do (the CLI is English only: this phrase is the contract).
MAKE_A_NEW_BACKUP = "make a new backup"
#: The line every confirmation logs, at WARNING: not the one of an owner that could not be picked.
RESTORE_CONFIRMED = "Restore confirmed: the next start of the server applies it"
#: A plain user that is marked and holds nothing: never a candidate of a real check, but ``pick_owner`` must not choose it.
MARKED_PLAIN = {"user_id": 7, "username": "mark_plain_user", "email": "mark.plain.b51j@example.com", "is_superuser": False, "is_active": True, "is_instance_owner": True}
#: A user whose address differs from the owner's by a letter outside A–Z only (``same_email`` folds A–Z and nothing else).
UMLAUT_USER = {"user_id": 8, "username": "umlaut_user", "email": "Ünal.b51j@example.com", "is_superuser": False, "is_active": True, "is_instance_owner": False}
UMLAUT_OWNER_EMAIL = "ünal.b51j@example.com"


def marked(candidate: dict[str, Any]) -> dict[str, Any]:
    """``candidate`` as the report of a check writes it when the backup marks the account as the instance's owner."""
    return {**candidate, "is_instance_owner": True}


def pick_function() -> tuple[Any, Callable[..., Any]]:
    """``apply`` and ``apply.pick_owner``; before B5-1j, a failure that says so."""
    apply = apply_module()
    function = getattr(apply, "pick_owner", None)
    if function is None:
        pytest.fail("[new] B5-1j: apply.pick_owner does not exist yet (analysis §2)", pytrace=False)
    return apply, function


def as_candidates(rows: list[dict[str, Any]]) -> list[Any]:
    """The report's candidates as ``staging.OwnerCandidate`` reads them."""
    from backend.app.services.platform.instance_backup.staging import OwnerCandidate  # noqa: PLC0415

    return [OwnerCandidate.model_validate(row) for row in rows]


#: (the candidates, the owner's address, the pick's account (``None``: nobody), how).
PICKS = [
    pytest.param([ADA, OWEN, ZOE], OWNER_EMAIL, OWEN, "holds_address", id="holds-address-a-plain-user"),
    pytest.param([ADA, OWEN, ZOE], OWNER_EMAIL.upper(), OWEN, "holds_address", id="holds-address-in-another-letter-case"),
    pytest.param([ADA, OWEN, ZOE], OWNER_EMAIL.lower(), OWEN, "holds_address", id="holds-address-in-lower-case"),
    pytest.param([ADA, BOB_HOLDER, ZOE], OWNER_EMAIL, BOB_HOLDER, "holds_address", id="holds-address-a-disabled-plain-user"),
    pytest.param([marked(ADA), OWEN, ZOE], OWNER_EMAIL, OWEN, "holds_address", id="the-holder-wins-over-a-marked-administrator"),
    pytest.param([ADA, marked(ZOE)], OWNER_EMAIL, ZOE, "marked", id="marked-the-second-by-name"),
    pytest.param([marked(ADA), ZOE], OWNER_EMAIL, ADA, "marked", id="marked-the-first-by-name"),
    pytest.param([ADA, ZOE], OWNER_EMAIL, None, "none", id="none-nobody-marked"),
    pytest.param([marked(ADA), marked(ZOE)], OWNER_EMAIL, None, "none", id="none-two-marked-never-the-first-by-id"),
    pytest.param([ADA, marked(OLGA), ZOE], OWNER_EMAIL, None, "none", id="none-the-marked-one-is-a-disabled-administrator"),
    pytest.param([ADA, MARKED_PLAIN, ZOE], OWNER_EMAIL, None, "none", id="none-the-marked-one-is-an-ordinary-account"),
    pytest.param([], OWNER_EMAIL, None, "none", id="none-no-candidate"),
    pytest.param([ADA, marked(ZOE), UMLAUT_USER], UMLAUT_OWNER_EMAIL, ZOE, "marked", id="a-letter-outside-a-z-is-not-folded-so-it-holds-nothing"),
]


@pytest.mark.parametrize(("rows", "owner_email", "expected", "how"), PICKS)
def test_pick_owner_takes_the_holder_of_the_address_then_the_one_marked_administrator_and_else_nobody(rows, owner_email, expected, how):
    """(v) B5-1j §2: ``pick_owner(candidates, owner_email)`` answers an ``OwnerPick``: rule 1, the account whose address is
    the owner's (``same_email``: A–Z folded and nothing else), whatever its role or state, ``holds_address``; rule 2,
    otherwise the ONE candidate that is marked, an administrator and active, ``marked``; rule 3, otherwise ``user_id`` and
    ``username`` ``None`` and ``none`` — nobody marked, two or more marked, the marked account not an active administrator
    or not an administrator at all. Never the first by id. A pure function: it changes nothing it is given."""
    print_section("(v) B5-1j pick_owner")
    apply, pick_owner = pick_function()
    candidates = as_candidates(rows)
    before = [candidate.model_dump() for candidate in candidates]
    picked = pick_owner(candidates, owner_email)
    got = (picked.user_id, picked.username, picked.how)
    assert got == (None if expected is None else expected["user_id"], None if expected is None else expected["username"], how), f"{how}: the pick is {None if expected is None else expected['username']}: {got}"
    assert [candidate.model_dump() for candidate in candidates] == before, "the candidates were not changed"
    print_success(f"{how}: {got[1]}")


def test_an_owner_pick_is_a_frozen_dataclass_of_three_fields():
    """(v) B5-1j: ``OwnerPick`` is a frozen dataclass: ``user_id``, ``username``, ``how``; two picks of the same account
    compare equal."""
    apply, pick_owner = pick_function()
    pick_class = getattr(apply, "OwnerPick", None)
    assert pick_class is not None and dataclasses.is_dataclass(pick_class), f"apply.OwnerPick is a dataclass: {pick_class}"
    assert [field_.name for field_ in dataclasses.fields(pick_class)] == ["user_id", "username", "how"], f"its fields: {[field_.name for field_ in dataclasses.fields(pick_class)]}"
    picked = pick_owner(as_candidates([ADA, marked(ZOE)]), OWNER_EMAIL)
    assert isinstance(picked, pick_class), f"pick_owner answers an OwnerPick: {type(picked)}"
    with pytest.raises(dataclasses.FrozenInstanceError):
        picked.user_id = 99  # type: ignore[misc]
    assert picked == pick_class(ZOE["user_id"], ZOE["username"], "marked"), "equal to the same pick built by hand"
    print_success("OwnerPick: frozen, user_id, username, how")


def refused_via(apply: Any, instance: Instance, via: str) -> Any:
    """``confirm_restore`` via ``via`` expected refused: the error, once checked that nothing was written (no state, nothing
    of ``.restore`` changed but its apply lock, no restore waiting)."""
    before = but_the_apply_lock(instance.root)
    with pytest.raises(apply.RestoreStateError) as raised:
        apply.confirm_restore(instance.stage_id, confirmed_by=via, confirmed_via=via, data_dir=instance.root, now=instance.confirm_at)
    assert not lexists(state_file(instance.root)), f"({raised.value.code}) a refused confirmation writes no state"
    assert but_the_apply_lock(instance.root) == before, f"({raised.value.code}) nothing of .restore changed: {cases.changed(before, but_the_apply_lock(instance.root))}"
    assert apply.read_restore(instance.root) is None, f"({raised.value.code}) no restore waits"
    return raised.value


def confirmed_via_with_logs(apply: Any, instance: Instance, via: str) -> tuple[Any, list[dict[str, Any]]]:
    """``confirm_restore`` via ``via`` naming nobody: the state, and what it logged (its canary left out)."""
    with logs() as events:
        state = apply.confirm_restore(instance.stage_id, confirmed_by=via, confirmed_via=via, data_dir=instance.root, now=instance.confirm_at)
    return state, [event for event in events if event.get("event") != LOG_CANARY]


def owner_warnings(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The warnings of the log about the owner: any but the line every confirmation logs."""
    return [event for event in events if event.get("log_level") in ("warning", "error", "critical") and event.get("event") != RESTORE_CONFIRMED and "owner" in str(event.get("event")).lower()]


#: (the candidates of the report, the account the confirmation must record).
PICKED_AT_THE_CONFIRMATION = [
    pytest.param([ADA, OWEN, ZOE], OWEN, id="the-holder-of-the-address-even-a-plain-user"),
    pytest.param([marked(ADA), OWEN, ZOE], OWEN, id="the-holder-wins-over-a-marked-administrator"),
    pytest.param([ADA, marked(ZOE)], ZOE, id="the-one-marked-administrator"),
]


@pytest.mark.parametrize("via", VIA_NO_ADMIN)
@pytest.mark.parametrize(("candidates", "expected"), PICKED_AT_THE_CONFIRMATION)
def test_a_managed_command_line_or_panel_confirmation_records_the_owner_it_picks(tmp_path, databases, checked, monkeypatch, via, candidates, expected):
    """(v) B5-1j §2: ``managed``, the owner's address set, the report checked with it and without conflict: a confirmation
    via ``cli`` or ``panel`` that names nobody records the picked account in the state it returns, in ``restore.json``
    and in what ``read_restore`` reads; ``owner_outcome`` ``None`` (only the first start writes it), ``pending``. Red before
    B5-1j: ``owner_user_id`` was ``None``."""
    print_section("(v) B5-1j the pick is recorded")
    apply = apply_module()
    instance = owner_case(tmp_path, databases, checked, monkeypatch, profile="managed", owner_email=OWNER_EMAIL, candidates=candidates)
    state, events = confirmed_via_with_logs(apply, instance, via)
    assert (state.status, state.confirmed_via, state.owner_user_id, state.owner_outcome) == ("pending", via, expected["user_id"], None), f"via {via}: pending, the owner {expected['username']}: {state}"
    assert on_disk_owner(instance.root) == (expected["user_id"], None), f"restore.json records the owner: {on_disk_owner(instance.root)}"
    assert apply.read_restore(instance.root).owner_user_id == expected["user_id"], "read_restore reads it back"
    assert owner_warnings(events) == [], f"an owner that was found is no warning: {logged(events)}"
    nothing_secret_logged(events, OWNER_EMAIL, *(row["email"] for row in candidates), *(row["username"] for row in candidates))
    print_success(f"via {via}: owner {expected['username']} recorded")


#: Reports from which nobody can be picked.
NOT_PICKED = [
    pytest.param([ADA, ZOE], id="nobody-is-marked"),
    pytest.param([marked(ADA), marked(ZOE)], id="two-are-marked"),
    pytest.param([ADA, marked(OLGA), ZOE], id="the-marked-one-is-a-disabled-administrator"),
    pytest.param([], id="no-candidate"),
]


@pytest.mark.parametrize("via", VIA_NO_ADMIN)
@pytest.mark.parametrize("candidates", NOT_PICKED)
def test_when_nobody_can_be_picked_the_confirmation_goes_on_records_none_and_warns_without_a_name(tmp_path, databases, checked, monkeypatch, via, candidates):
    """(v) B5-1j §2.3: nobody holds the owner's address and the report does not mark exactly one active administrator
    (none marked, two marked — never the first by id —, a marked disabled one): the confirmation is NOT refused. The state
    has ``owner_user_id`` ``None`` and ``owner_outcome`` ``"none"`` (a plain string, in the state returned, in ``restore.json``
    and in what ``read_restore`` reads), and a warning about the owner is logged that holds no username and no address."""
    print_section("(v) B5-1j nobody picked")
    apply = apply_module()
    instance = owner_case(tmp_path, databases, checked, monkeypatch, profile="managed", owner_email=OWNER_EMAIL, candidates=candidates)
    state, events = confirmed_via_with_logs(apply, instance, via)
    assert (state.status, state.owner_user_id, state.owner_outcome) == ("pending", None, "none"), f"via {via}: confirmed, no owner, outcome none: {state}"
    assert on_disk_owner(instance.root) == (None, "none"), f"restore.json: no owner, outcome none: {on_disk_owner(instance.root)}"
    read_back = apply.read_restore(instance.root)
    assert (read_back.owner_user_id, read_back.owner_outcome) == (None, "none"), f"read_restore reads it back: {read_back}"
    assert owner_warnings(events), f"a warning about the owner is logged: {logged(events)}"
    nothing_secret_logged(events, OWNER_EMAIL, OWNER_EMAIL.lower(), *(row["email"] for row in (ADA, ZOE, OWEN, OLGA, BOB_HOLDER)), *(row["username"] for row in (ADA, ZOE, OWEN, OLGA, BOB_HOLDER)))
    print_success(f"via {via}: confirmed, outcome none, a warning without a name")


#: A report checked with another address, with none, or written before the addendum.
@pytest.mark.parametrize("via", VIA_NO_ADMIN)
@pytest.mark.parametrize("checked_with", STALE_CHECKS)
def test_a_managed_command_line_or_panel_confirmation_of_a_check_made_with_another_address_is_outdated(tmp_path, databases, checked, monkeypatch, via, checked_with):
    """(v) B5-1j §2: the owner's address is set but the report was checked with another one (``email_fold``), with none, or
    before the addendum: ``restore_stage_outdated`` («check the archive again»), nothing written — the candidates were read
    for an address that is not the owner's. Red before B5-1j: it was confirmed."""
    print_section("(v) B5-1j a check made with another address")
    apply = apply_module()
    instance = owner_case(tmp_path, databases, checked, monkeypatch, profile="managed", owner_email=OWNER_EMAIL, candidates=[ADA, marked(ZOE)], owner_email_checked=checked_with)
    error = refused_via(apply, instance, via)
    assert error.code == "restore_stage_outdated", f"via {via}, checked with {checked_with!r}: restore_stage_outdated, not {error.code}: {error}"
    print_success(f"via {via}: restore_stage_outdated")


@pytest.mark.parametrize("via", VIA_NO_ADMIN)
@pytest.mark.parametrize("checked_with", [OWNER_EMAIL.lower(), OWNER_EMAIL.upper()], ids=["lower-case", "upper-case"])
def test_a_check_made_with_the_owner_s_address_in_another_case_is_not_outdated_for_the_command_line_or_panel(tmp_path, databases, checked, monkeypatch, via, checked_with):
    """(v) B5-1j: the same address in another A–Z case is the same address: confirmed, the marked administrator picked."""
    apply = apply_module()
    instance = owner_case(tmp_path, databases, checked, monkeypatch, profile="managed", owner_email=OWNER_EMAIL, candidates=[ADA, marked(ZOE)], owner_email_checked=checked_with)
    state, _events = confirmed_via_with_logs(apply, instance, via)
    assert (state.status, state.owner_user_id) == ("pending", ZOE["user_id"]), f"via {via}, checked with {checked_with!r}: confirmed, zoe picked: {state}"
    print_success(f"via {via}, {checked_with!r}: confirmed")


@pytest.mark.parametrize("via", VIA_NO_ADMIN)
@pytest.mark.parametrize("conflicts", [[code] for code in EVERY_CONFLICT] + [EVERY_CONFLICT], ids=[*EVERY_CONFLICT, "all"])
@pytest.mark.parametrize("candidates", [pytest.param([ADA, marked(ZOE)], id="a-pick-exists"), pytest.param([ADA, ZOE], id="no-pick")])
def test_a_managed_command_line_or_panel_confirmation_of_a_copy_with_owner_conflicts_is_refused_with_what_to_do(tmp_path, databases, checked, monkeypatch, via, conflicts, candidates):
    """(v) B5-1j §2: a report whose ``owner_conflicts`` is not empty is refused ``owner_conflict``
    (``RestoreOwnerConflictError``) via ``cli`` and ``panel`` as via ``admin``, whatever the pick would be: nothing written.
    The message says what to do: it holds «make a new backup» (remove the duplicate account or free the address in the
    instance the backup came from, make a new backup, check it again). Red before B5-1j: it was confirmed."""
    print_section("(v) B5-1j owner conflicts")
    apply = apply_module()
    instance = owner_case(tmp_path, databases, checked, monkeypatch, profile="managed", owner_email=OWNER_EMAIL, candidates=candidates, owner_conflicts=conflicts)
    error = refused_via(apply, instance, via)
    assert (type(error).__name__, error.code) == ("RestoreOwnerConflictError", "owner_conflict"), f"via {via}, {conflicts}: owner_conflict, not {type(error).__name__} {error.code}: {error}"
    assert MAKE_A_NEW_BACKUP in str(error), f"the message says what to do ({MAKE_A_NEW_BACKUP!r}): {error}"
    print_success(f"via {via}, {conflicts}: owner_conflict, with advice")


@pytest.mark.parametrize("via", VIA_NO_ADMIN)
def test_a_check_made_with_another_address_is_outdated_before_its_conflicts_are_read(tmp_path, databases, checked, monkeypatch, via):
    """(v) B5-1j: the order of the administrators' path holds: a stale report with conflicts is ``restore_stage_outdated``
    first, as via ``admin`` (a conflict list read for another address says nothing about this one)."""
    apply = apply_module()
    instance = owner_case(tmp_path, databases, checked, monkeypatch, profile="managed", owner_email=OWNER_EMAIL, candidates=[ADA, marked(ZOE)], owner_email_checked="someone.else.b51j@example.com", owner_conflicts=["duplicate_email"])
    error = refused_via(apply, instance, via)
    assert error.code == "restore_stage_outdated", f"via {via}: restore_stage_outdated first, not {error.code}: {error}"
    print_success(f"via {via}: outdated before conflict")


@pytest.mark.parametrize("via", VIA_NO_ADMIN)
@pytest.mark.parametrize(
    ("profile", "owner_email"),
    [pytest.param("managed", OWNER_EMAIL, id="managed"), pytest.param("selfhosted", OWNER_EMAIL, id="selfhosted"), pytest.param("managed", None, id="managed-no-address")],
)
def test_naming_an_owner_with_the_command_line_or_the_panel_is_still_refused_as_not_applicable(tmp_path, databases, checked, monkeypatch, via, profile, owner_email):
    """(v) B5-1j, a guard: the owner is picked by the code, never named by the caller: ``owner_user_id=`` via ``cli`` or
    ``panel`` is ``owner_choice_not_applicable`` (``RestoreOwnerChoiceNotApplicableError``), in every profile; nothing
    written."""
    apply = apply_module()
    instance = owner_case(tmp_path, databases, checked, monkeypatch, profile=profile, owner_email=owner_email, candidates=[ADA, marked(ZOE)])
    before = but_the_apply_lock(instance.root)
    with pytest.raises(apply.RestoreStateError) as raised:
        apply.confirm_restore(instance.stage_id, confirmed_by=via, confirmed_via=via, owner_user_id=ADA["user_id"], data_dir=instance.root, now=instance.confirm_at)
    assert (type(raised.value).__name__, raised.value.code) == ("RestoreOwnerChoiceNotApplicableError", "owner_choice_not_applicable"), f"{profile} via {via}: not applicable: {raised.value}"
    assert not lexists(state_file(instance.root)) and but_the_apply_lock(instance.root) == before, "nothing written"
    print_success(f"{profile} via {via}: owner_choice_not_applicable")


@pytest.mark.parametrize("via", VIA_NO_ADMIN)
def test_a_managed_confirmation_without_the_owner_s_address_picks_and_refuses_nothing_even_with_conflicts(tmp_path, databases, checked, monkeypatch, via):
    """(v) B5-1j §2 (the case outside the rule): ``managed`` without ``LIBREFOLIO_ADMIN_EMAIL``: no pick, no refusal —
    a report with marks, conflicts and another address is confirmed as today, ``owner_user_id`` and ``owner_outcome``
    ``None``, and no warning about an owner."""
    apply = apply_module()
    instance = owner_case(tmp_path, databases, checked, monkeypatch, profile="managed", owner_email=None, candidates=[ADA, marked(ZOE)], owner_email_checked="someone.else.b51j@example.com", owner_conflicts=OWNER_CONFLICTS)
    state, events = confirmed_via_with_logs(apply, instance, via)
    assert (state.status, state.owner_user_id, state.owner_outcome) == ("pending", None, None), f"via {via}: confirmed as today: {state}"
    assert on_disk_owner(instance.root) == (None, None), f"restore.json: no owner, no outcome: {on_disk_owner(instance.root)}"
    assert owner_warnings(events) == [], f"no owner, no warning: {logged(events)}"
    print_success(f"via {via}: no address, nothing picked, nothing refused")


@pytest.mark.parametrize("via", ["admin", "cli", "panel"])
def test_a_self_hosted_confirmation_picks_and_refuses_nothing_whoever_confirms(tmp_path, databases, checked, monkeypatch, via):
    """(v) B5-1j, a guard: ``selfhosted`` has no owner's concept: marked candidates, conflicts and a check made with
    another address change nothing — confirmed, no owner, no outcome, no warning about an owner."""
    apply = apply_module()
    instance = owner_case(tmp_path, databases, checked, monkeypatch, profile="selfhosted", owner_email=OWNER_EMAIL, candidates=[ADA, marked(ZOE)], owner_email_checked="someone.else.b51j@example.com", owner_conflicts=OWNER_CONFLICTS)
    state, events = confirmed_via_with_logs(apply, instance, via)
    assert (state.status, state.owner_user_id, state.owner_outcome) == ("pending", None, None), f"selfhosted via {via}: as before: {state}"
    assert owner_warnings(events) == [], f"no owner, no warning: {logged(events)}"
    print_success(f"selfhosted via {via}: unchanged")


# -----------------------------------------------------------------------------
# (v) the commit: the picked account is closed whatever the channel
# -----------------------------------------------------------------------------


def others_as_the_backup_held_them(before: dict[str, dict[str, Any]], after: dict[str, dict[str, Any]], chosen: str) -> None:
    """Every account but ``chosen`` keeps its password, address, role and state (its session version and its owner flag, which
    the commit writes, aside)."""
    ignored = ("session_version", OWNER_COLUMN)
    left = {name: {key: value for key, value in row.items() if key not in ignored} for name, row in before.items() if name != chosen}
    now = {name: {key: value for key, value in row.items() if key not in ignored} for name, row in after.items() if name != chosen}
    assert now == left, f"the other accounts as the backup held them: {sorted(name for name in left if left[name] != now.get(name))}"


#: (the account picked, what the copy holds for it first, the candidates, the account the backup's author flagged).
CLOSED_AT_THE_COMMIT = [
    pytest.param("zoe_admin", None, [ADA, marked(ZOE)], "zoe_admin", id="the-marked-administrator"),
    pytest.param("zoe_admin", None, [ADA, marked(ZOE)], "ada_admin", id="a-marked-administrator-the-copy-flags-elsewhere"),
    pytest.param("bob_user", BOB_HOLDER, [ADA, BOB_HOLDER, ZOE], "ada_admin", id="the-address-holder-a-disabled-plain-user"),
]


@pytest.mark.parametrize("via", VIA_NO_ADMIN)
@pytest.mark.parametrize(("chosen_name", "holder", "candidates", "flagged"), CLOSED_AT_THE_COMMIT)
def test_the_commit_of_a_command_line_or_panel_restore_closes_the_picked_account_and_makes_it_the_only_owner(tmp_path, databases, checked, monkeypatch, via, chosen_name, holder, candidates, flagged):
    """(v) B5-1j §8 (Anna), end to end up to the commit: a restore confirmed via ``cli`` or ``panel`` on a managed
    instance, the owner picked at the confirmation. At the commit the picked account holds a real bcrypt hash that is not
    the backup's and that the backup's password does not open; its email is the owner's address, an active administrator,
    and the only account flagged ``is_instance_owner`` (the backup flagged another one: cleared); every other account keeps
    its password hash, address, role and state; every account's session version is the restore's; the owner is
    ``pending`` for the startup step (``owner_assignment_problem``, ``owner_pending``). One line names the stage, the account
    and ``assigned`` true; no line holds an address, a username, a hash or the password. Red before B5-1j: nobody was picked,
    the commit closed no account."""
    print_section("(v) B5-1j the picked account is closed at the commit")
    apply = apply_module()
    instance = owner_case(tmp_path, databases, checked, monkeypatch, profile="managed", owner_email=OWNER_EMAIL, candidates=candidates)
    copy_database = instance.copy / DATABASE_ENTRY
    if holder is not None:
        cases.execute(copy_database, f"UPDATE users SET email = '{holder['email']}', is_active = 0 WHERE id = {holder['user_id']}")
    hashes = with_backup_passwords(copy_database)
    flag_the_backups_owner(copy_database, flagged)
    before = accounts_of(copy_database)
    chosen_id = before[chosen_name]["id"]
    state, events = committed_after(apply, instance, via=via)
    assert (state.status, state.confirmed_via, state.owner_user_id, state.owner_outcome) == ("committed", via, chosen_id, None), f"committed via {via}, the owner {chosen_name}, the first start still to give it: {state}"
    after = accounts_of(instance.root / DATABASE_ENTRY)
    closed(after[chosen_name], hashes[chosen_name])
    address = configured_address()
    chosen = after[chosen_name]
    assert (chosen["email"], chosen["is_superuser"], chosen["is_active"]) == (address, 1, 1), f"the owner's address, an active administrator: {(chosen['email'] == address, chosen['is_superuser'], chosen['is_active'])}"
    others_as_the_backup_held_them(before, after, chosen_name)
    assert {name: row[OWNER_COLUMN] for name, row in after.items()} == {name: int(name == chosen_name) for name in after}, f"{OWNER_COLUMN}: the picked account only: {flags_of(instance.root / DATABASE_ENTRY)}"
    assert {row["session_version"] for row in after.values()} == {state.session_version}, f"every account gets the restore's session version: {state.session_version}, {sorted({row['session_version'] for row in after.values()})}"
    assert apply.owner_assignment_problem(instance.root) == "pending", "the guard: the owner's account is still to be given by the first start"
    assert apply.owner_pending(instance.root) == (instance.stage_id, chosen_id), "the startup step has the stage and the account to give"
    assert owner_line(events, instance.stage_id, chosen_id) == [True], f"one line: stage, account, assigned true: {logged(events)}"
    nothing_secret_logged(events, OWNER_EMAIL, address, BOB_HOLDER["email"], BACKUP_PASSWORD, chosen["hashed_password"], *hashes.values(), *(row["email"] for row in before.values()), *before)
    print_success(f"via {via}: {chosen_name} closed, the owner's address, the only owner")


@pytest.mark.parametrize("via", VIA_NO_ADMIN)
def test_the_commit_of_a_restore_that_picked_nobody_clears_every_flag_touches_no_password_and_leaves_nothing_pending(tmp_path, databases, checked, monkeypatch, via):
    """(v) B5-1j §2.3: two administrators flagged by the backup (its unique index dropped, as a crafted copy has it): nobody
    is picked, ``owner_outcome`` ``"none"``; at the commit every flag is cleared, no password, address or role changes
    (only the session versions), the restore is committed, and nothing is pending for the startup step or the guard.
    Red before B5-1j: the outcome stayed ``None``."""
    print_section("(v) B5-1j nobody picked: the commit")
    apply = apply_module()
    instance = owner_case(tmp_path, databases, checked, monkeypatch, profile="managed", owner_email=OWNER_EMAIL, candidates=[marked(ADA), marked(ZOE)])
    copy_database = instance.copy / DATABASE_ENTRY
    cases.execute(copy_database, "DROP INDEX ux_users_instance_owner", f"UPDATE users SET {OWNER_COLUMN} = 1 WHERE username IN ('ada_admin', 'zoe_admin')")
    assert sorted(name for name, value in flags_of(copy_database).items() if value) == ["ada_admin", "zoe_admin"], "precondition: the copy flags two administrators"
    with_backup_passwords(copy_database)
    before = accounts_of(copy_database)
    state, events = committed_after(apply, instance, via=via)
    assert (state.status, state.owner_user_id, state.owner_outcome) == ("committed", None, "none"), f"committed, nobody picked, outcome none: {state}"
    after = accounts_of(instance.root / DATABASE_ENTRY)
    assert set(flags_of(instance.root / DATABASE_ENTRY).values()) == {0}, f"nobody is the instance owner: {flags_of(instance.root / DATABASE_ENTRY)}"
    others_as_the_backup_held_them(before, after, "<nobody>")
    assert {row["session_version"] for row in after.values()} == {state.session_version}, "every session ended all the same"
    assert (apply.owner_assignment_problem(instance.root), apply.owner_pending(instance.root)) == (None, None), "nothing keeps the guard or the startup step waiting"
    nothing_secret_logged(events, OWNER_EMAIL, *(row["email"] for row in before.values()), *before)
    print_success(f"via {via}: nobody picked, flags cleared, no password touched")

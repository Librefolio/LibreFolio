"""
The backup API (``/backup``), lot B1 of workstream B: the backup of the whole instance, and the order of the routes.

Under test: ``backend/app/api/v1/backup/instance.py`` (the four routes of ``/backup/instance``, for administrators
only) and ``backend/app/api/v1/backup/__init__.py`` (``backup_router``, composed from ``instance.py`` then
``exports.py``), on the lane's server. The jobs underneath (``services/platform/instance_backup/``) have suites of
their own, ``services backup-jobs`` and ``services backup-archive``; so do the per-series exports.

- BACKUP-001, pure (C2): ``backup_router`` registers the five routes of ``instance.py``, the four of ``panel.py``, the
  nine of ``restore.py``, then the three exports of ``exports.py``, in that order, each with its method and its endpoint, and a single tag: Hosting panel on the four of ``panel.py``, Backup & Export on the others.
- BACKUP-002: without a session each of the four routes answers 401; BACKUP-003: an ordinary user gets 403 from each.
  Both on an existing job and its archive; a refused DELETE leaves the job in place.
- BACKUP-004: an administrator's backup, from the start to the download. The start answers 202 with a running job;
  polled, the job ends done, with its file name and size and every byte counted (``done_bytes == total_bytes``). The
  download answers 200, ``application/zip``, an attachment under the job's file name, ``Cache-Control: no-store``,
  as many bytes as the job says: a zip whose first entry is ``sqlite/app.db`` and whose last is ``manifest.json``, the
  manifest listing every other entry, at the Alembic revision of the lane's database, and the archived database
  holding this module's administrator.
- BACKUP-005: while the run lock is held, here by the test itself, a start answers 409 ``backup_busy``.
- BACKUP-006: DELETE of a finished job answers 204; then the job and its file answer 404 ``backup_job_not_found``,
  and its folder, archive included, is gone from the data directory.
- BACKUP-007: a job without an archive, its state written by the test. While its run holds the lock, its file answers
  409 ``backup_job_not_ready`` and its DELETE 409 ``backup_job_running``; once the lock is free it reads as failed,
  ``backup_interrupted``, its file is still 409, and DELETE removes it (204).
- BACKUP-008: an unknown job id of the right shape: 404 ``backup_job_not_found`` from the job, its file and DELETE.
- BACKUP-009: ids the jobs never make (``abc``, 31 or 33 hex digits, uppercase hex, a letter that is not hex): the same
  404 from the three, never a 500.
- BACKUP-010: the four placeholders B1 removed (``POST /backup/export``, ``POST /backup/restore``,
  ``GET /backup/formats``, ``GET /backup/status``) answer 404 or 405, to an administrator too.

Ownership. The module registers an administrator (promoted in this process with ``user_service.set_user_admin``, on
the lane's database) and an ordinary user, and deletes both at its end. Every job a test starts, a start that should
have been refused and answered 202 included, is waited for and deleted through the API at the test's teardown, after a
red too. The jobs of others are never read nor touched, and nothing is counted that the test did not create.

Isolation: ``api`` is write-scoped, and so is this unit. Its one global surface is the lane's backup run lock
(``backups/.jobs/.lock``), the lock every backup of the lane takes. No other unit starts a backup on the lane, every
job of this module is waited for until its run has released the lock, and BACKUP-005 and BACKUP-007 hold the lock
themselves only for the requests that need it (one, and three). No sleep stands in for a state: every wait polls the
job, or the lock, with a deadline.
"""

import asyncio
import email.message
import json
import os
import re
import secrets
import shutil
import sqlite3
import time
import uuid
import zipfile
from collections.abc import AsyncIterator, Coroutine, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager, closing
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import fcntl
except ImportError:  # pragma: no cover - not POSIX: the run lock is then a lock of the server's process
    fcntl = None  # type: ignore[assignment]

import httpx
import pytest
from fastapi.routing import iter_route_contexts
from sqlalchemy.ext.asyncio import AsyncSession

import backend.app.api.v1.backup as backup_module
from backend.app.api.v1.auth import SESSION_COOKIE_NAME
from backend.app.config import get_data_dir, get_settings
from backend.app.db.session import get_async_engine
from backend.app.services.accounts import user_service
from backend.app.services.platform.instance_backup import jobs, paths
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
INSTANCE_URL = f"{API_BASE}/backup/instance"
TIMEOUT = 30.0
#: Seconds a backup of the lane (its database and its uploads) may take on a loaded machine: a hang still ends.
JOB_DEADLINE_S = 120.0
#: Seconds between two reads of the state a wait polls.
POLL_INTERVAL_S = 0.1
PASSWORD = "TestPass123!"

#: The archive's contract: the database first, the manifest last, the name ``archive_name`` gives it (UTC).
DATABASE_ENTRY = "sqlite/app.db"
MANIFEST_ENTRY = "manifest.json"
ARCHIVE_NAME = re.compile(r"librefolio-backup-\d{8}-\d{6}\.zip")

#: The four routes of instance.py, as (method, path below /backup/instance); ``{job_id}`` is an existing job's.
INSTANCE_ROUTES = [
    pytest.param("POST", "", id="start"),
    pytest.param("GET", "/jobs/{job_id}", id="job"),
    pytest.param("GET", "/jobs/{job_id}/file", id="file"),
    pytest.param("DELETE", "/jobs/{job_id}", id="delete"),
]
#: The three routes of one job.
JOB_ROUTES = [("GET", "/jobs/{job_id}"), ("GET", "/jobs/{job_id}/file"), ("DELETE", "/jobs/{job_id}")]

_HEX = "0123456789abcdef" * 2
#: Not job ids, which are 32 lowercase hexadecimal digits and nothing else (``paths.is_job_id``).
MALFORMED_JOB_IDS = [
    pytest.param("abc", id="abc"),
    pytest.param(_HEX[:31], id="31-hex-digits"),
    pytest.param(_HEX + "0", id="33-hex-digits"),
    pytest.param(_HEX.upper(), id="uppercase-hex"),
    pytest.param("g" + _HEX[1:], id="not-hex"),
]

#: The placeholders lot B1 removed (plan 07_backupDocker §3.9), each with the body its old test sent.
REMOVED_PLACEHOLDERS = [
    pytest.param("POST", "/backup/export", {"format": "json", "scope": ["all"]}, id="export"),
    pytest.param("POST", "/backup/restore", {"file_id": "nonexistent", "overwrite_existing": False}, id="restore"),
    pytest.param("GET", "/backup/formats", None, id="formats"),
    pytest.param("GET", "/backup/status", None, id="status"),
]

needs_flock = pytest.mark.skipif(fcntl is None, reason="the backup run lock is an flock on POSIX only; elsewhere it is a lock of the server's process, out of a test's reach")


# ============================================================================
# Helpers
# ============================================================================


@dataclass(frozen=True)
class Account:
    """A user of this module, logged in: ``client()`` opens a client that carries its session."""

    username: str
    user_id: int
    session: str

    def client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(cookies={SESSION_COOKIE_NAME: self.session}, timeout=TIMEOUT)


@dataclass(frozen=True)
class Accounts:
    admin: Account
    user: Account


def job_url(job_id: str) -> str:
    return f"{INSTANCE_URL}/jobs/{job_id}"


def file_url(job_id: str) -> str:
    return f"{job_url(job_id)}/file"


def describe(resp: httpx.Response) -> str:
    """A response read in full, for an assertion's message."""
    return f"{resp.request.method} {resp.request.url} answered {resp.status_code}: {resp.text[:500]}"


def error_code(resp: httpx.Response) -> str | None:
    """``detail.code`` of an error answer (``{"detail": {"code": ..., "message": ...}}``); None when it has none."""
    try:
        body = resp.json()
    except ValueError:
        return None
    detail = body.get("detail") if isinstance(body, dict) else None
    return detail.get("code") if isinstance(detail, dict) else None


def assert_error(resp: httpx.Response, status: int, code: str) -> None:
    assert resp.status_code == status and error_code(resp) == code, f"expected {status} with detail.code {code!r}: {describe(resp)}"


def content_disposition(header: str) -> tuple[str | None, str | None]:
    """The disposition type and the file name of a ``Content-Disposition`` header, its quoting or encoding undone."""
    message = email.message.Message()
    message["Content-Disposition"] = header
    return message.get_content_disposition(), message.get_filename()


def read_only(db: Path) -> sqlite3.Connection:
    """The SQLite database at ``db``, opened read-only."""
    return sqlite3.connect(f"{db.resolve().as_uri()}?mode=ro", uri=True)


def is_superuser(db: Path, username: str) -> bool | None:
    """Whether ``username`` is an administrator in the database at ``db``; None when it has no such user."""
    with closing(read_only(db)) as conn:
        row = conn.execute("SELECT is_superuser FROM users WHERE username = ?", (username,)).fetchone()
    return None if row is None else bool(row[0])


def alembic_revision(db: Path) -> str:
    """The one revision ``alembic_version`` records in the database at ``db``."""
    with closing(read_only(db)) as conn:
        rows = conn.execute("SELECT version_num FROM alembic_version").fetchall()
    assert len(rows) == 1, f"premise: {db} must record exactly one Alembic revision, it records {rows}"
    return rows[0][0]


def run_lock_held() -> bool:
    """Whether a backup run holds the lane's run lock now: a probe, taken and released at once when free, as jobs.py probes it."""
    if fcntl is None:
        return False
    try:
        fd = os.open(paths.lock_path(get_data_dir()), os.O_RDWR | getattr(os, "O_NOFOLLOW", 0))
    except FileNotFoundError:
        return False
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return True
    else:
        fcntl.flock(fd, fcntl.LOCK_UN)
        return False
    finally:
        os.close(fd)


@asynccontextmanager
async def holding_the_run_lock() -> AsyncIterator[None]:
    """Hold the lane's backup run lock as a running backup does (an exclusive ``flock``), released on the way out.

    Taken as soon as it is free: every job of this module is waited for until its run has released it, so only a run
    this module did not start could hold it, and the wait for one has a deadline.
    """
    data_dir = get_data_dir()
    paths.ensure_private_dir(paths.jobs_dir(data_dir), data_dir)
    fd = os.open(paths.lock_path(data_dir), os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        deadline = time.monotonic() + JOB_DEADLINE_S
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise AssertionError(f"the lane's backup run lock stayed held for {JOB_DEADLINE_S:.0f}s by a run this module did not start") from None
                await asyncio.sleep(POLL_INTERVAL_S)
        try:
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


async def post_start(client: httpx.AsyncClient, created: list[str]) -> httpx.Response:
    """``POST /backup/instance``. A job it starts (202) joins ``created``, to be deleted at teardown even where a refusal was expected."""
    resp = await client.post(INSTANCE_URL)
    if resp.status_code == 202:
        created.append(resp.json()["job_id"])
    return resp


async def start_backup(client: httpx.AsyncClient, created: list[str]) -> dict:
    """Start a backup as an administrator: the job the 202 answers with."""
    resp = await post_start(client, created)
    assert resp.status_code == 202, f"an administrator's start must answer 202 with the job to poll: {describe(resp)}"
    return resp.json()


async def poll_until_finished(client: httpx.AsyncClient, job_id: str) -> httpx.Response:
    """Read the job until it has ended and its run has released the lane's lock, or until it is gone: the last answer.

    The run writes its final state just before it releases the lock (jobs.py): a job read as done may still hold it for
    an instant, and the next start of this module would meet it as busy. The lock is part of the condition.
    """
    deadline = time.monotonic() + JOB_DEADLINE_S
    while True:
        resp = await client.get(job_url(job_id))
        if resp.status_code != 200 or (resp.json()["status"] != "running" and not run_lock_held()):
            return resp
        if time.monotonic() >= deadline:
            raise AssertionError(f"backup job {job_id} has not ended within {JOB_DEADLINE_S:.0f}s: last state {resp.json()}, run lock held: {run_lock_held()}")
        await asyncio.sleep(POLL_INTERVAL_S)


async def wait_until_finished(client: httpx.AsyncClient, job_id: str) -> dict:
    """The final state of a job, read once it has ended and its run has released the lock."""
    resp = await poll_until_finished(client, job_id)
    assert resp.status_code == 200, f"a job must stay readable until it is deleted: {describe(resp)}"
    return resp.json()


async def remove_jobs(admin: Account, job_ids: list[str]) -> list[str]:
    """Wait for each job to end, then delete it through the API as the administrator: what could not be removed.

    A job its test deleted already answers 404, and is left at that.
    """
    problems: list[str] = []
    async with admin.client() as client:
        for job_id in job_ids:
            try:
                last = await poll_until_finished(client, job_id)
                if last.status_code == 404:
                    continue
                resp = await client.delete(job_url(job_id))
                if resp.status_code not in (204, 404):
                    problems.append(f"job {job_id}: {describe(resp)}")
            except Exception as exc:  # every job gets its attempt; the failures are reported together
                problems.append(f"job {job_id}: {exc!r}")
    return problems


async def download(client: httpx.AsyncClient, job_id: str, target: Path) -> httpx.Headers:
    """Stream the archive of a job into ``target``: the headers it came with."""
    async with client.stream("GET", file_url(job_id)) as resp:
        if resp.status_code != 200:
            await resp.aread()
            raise AssertionError(f"the archive of a done job must download: {describe(resp)}")
        with target.open("wb") as handle:
            async for chunk in resp.aiter_bytes():
                handle.write(chunk)
        return resp.headers


async def call_route(client: httpx.AsyncClient, method: str, route: str, job_id: str, created: list[str]) -> httpx.Response:
    """One route of ``INSTANCE_ROUTES``, on the job ``job_id`` where the route names one; a start goes through ``post_start``."""
    if method == "POST":
        return await post_start(client, created)
    return await client.request(method, INSTANCE_URL + route.format(job_id=job_id))


async def assert_job_in_place(admin: Account, job_id: str) -> None:
    """The job is still there, done: a refused DELETE removed nothing."""
    async with admin.client() as client:
        resp = await client.get(job_url(job_id))
    assert resp.status_code == 200 and resp.json()["status"] == "done", f"a refused DELETE must leave the job in place: {describe(resp)}"


# ============================================================================
# Fixtures: the server, this module's accounts, and the jobs its tests start
# ============================================================================


def run_async(coroutine: Coroutine[Any, Any, Any]) -> Any:
    """Run ``coroutine`` to its end on a loop of its own, in a thread of its own.

    The fixtures of this module are synchronous (two are module-scoped): their coroutines never touch the loop
    pytest-asyncio gives a test, nor the main thread's current loop.
    """
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="backup-api-fixture") as pool:
        return pool.submit(asyncio.run, coroutine).result()


async def _open_account(registered: list[int], *, admin: bool) -> Account:
    """Register a user (its id joins ``registered``), promote it when ``admin``, log it in, and check its role through ``/auth/me``."""
    username = f"backup_api_{'admin' if admin else 'user'}_{uuid.uuid4().hex[:12]}"
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(f"{API_BASE}/auth/register", json={"username": username, "email": f"{username}@example.com", "password": PASSWORD})
        assert resp.status_code == 201, f"registering {username}: {describe(resp)}"
        user_id = resp.json()["user"]["id"]
        registered.append(user_id)
        if admin:
            async with AsyncSession(get_async_engine()) as session:
                promoted, error = await user_service.set_user_admin(session, username, is_admin=True)
            # The first account of an empty database is an administrator already.
            assert promoted or "already an admin" in (error or ""), f"promoting {username} to administrator: {error}"
        resp = await client.post(f"{API_BASE}/auth/login", json={"username": username, "password": PASSWORD})
        assert resp.status_code == 200, f"logging in {username}: {describe(resp)}"
        session_cookie = resp.cookies.get(SESSION_COOKIE_NAME)
        assert session_cookie, f"logging in {username} set no {SESSION_COOKIE_NAME} cookie"
    account = Account(username=username, user_id=user_id, session=session_cookie)
    async with account.client() as client:
        me = await client.get(f"{API_BASE}/auth/me")
    assert me.status_code == 200 and me.json()["user"]["is_superuser"] is admin, f"premise: {username} must {'be' if admin else 'not be'} an administrator: {describe(me)}"
    return account


async def _open_accounts(registered: list[int]) -> Accounts:
    return Accounts(admin=await _open_account(registered, admin=True), user=await _open_account(registered, admin=False))


async def _delete_users(user_ids: list[int]) -> list[str]:
    """Delete these users of the lane through ``user_service.delete_user``, each in a session of its own: what failed."""
    problems: list[str] = []
    for user_id in user_ids:
        async with AsyncSession(get_async_engine()) as session:
            try:
                await user_service.delete_user(session, user_id)
            except Exception as exc:  # every account gets its attempt; the failures are reported together
                problems.append(f"user {user_id}: {exc!r}")
    return problems


async def _finished_backup(admin: Account, created: list[str]) -> dict:
    async with admin.client() as client:
        started = await start_backup(client, created)
        job = await wait_until_finished(client, started["job_id"])
    assert job["status"] == "done", f"premise: the module's backup must end done: {job}"
    return job


@pytest.fixture(scope="module")
def test_server():
    """Start test server for all tests in this module."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


@pytest.fixture(scope="module")
def accounts(test_server) -> Iterator[Accounts]:
    """This module's administrator and ordinary user, deleted at its end, after a red too.

    Also the premise of every look at the data directory: the lane database this process reads is the server's, since
    it holds the administrator the server has just registered.
    """
    registered: list[int] = []
    try:
        opened = run_async(_open_accounts(registered))
        lane_db = paths.database_path(get_data_dir())
        assert is_superuser(lane_db, opened.admin.username) is True, f"premise: the lane database this test reads, {lane_db}, must be the server's, yet it has no administrator {opened.admin.username}"
    except BaseException:
        run_async(_delete_users(registered))
        raise
    yield opened
    problems = run_async(_delete_users(registered))
    assert not problems, "could not delete the accounts of this module:\n" + "\n".join(problems)


@pytest.fixture(scope="module")
def done_job(accounts) -> Iterator[dict]:
    """A finished backup of this module's administrator, for the cases that need an existing job and its archive."""
    created: list[str] = []
    try:
        job = run_async(_finished_backup(accounts.admin, created))
    except BaseException:
        run_async(remove_jobs(accounts.admin, created))
        raise
    yield job
    problems = run_async(remove_jobs(accounts.admin, created))
    assert not problems, "could not delete the backup job of this module:\n" + "\n".join(problems)


@pytest.fixture
def created_jobs(accounts) -> Iterator[list[str]]:
    """The jobs this test starts: each is waited for and deleted through the API at its teardown, after a red too."""
    created: list[str] = []
    yield created
    problems = run_async(remove_jobs(accounts.admin, created))
    assert not problems, "could not delete the backup jobs of this test:\n" + "\n".join(problems)


# ============================================================================
# BACKUP-001: the /backup router, one module per resource (rule C2) — pure
# ============================================================================
#
# backup_router (api/v1/backup/__init__.py) composes instance.py (the backup of the whole instance), panel.py (the same
# for a hosting panel), restore.py (the check of an archive and the restore), then exports.py (the per-series exports). The registration order is the order of the OpenAPI document and the order routes are
# matched in, and swapping the two include_router calls would change both without any error. Pure: the test reads the
# composed router object, so it requests neither test_server nor the database. With FastAPI 0.141 an included router
# is a wrapper in .routes: iter_route_contexts yields the effective routes, with the prefix and the tags applied.

#: The routes of backup_router, in registration order, as (method, path, endpoint), the endpoint that serves the route
#: as <module>.<function> under backend.app.api.v1.backup.
BACKUP_ROUTES = [
    ("POST", "/backup/instance", "instance.start_instance_backup"),
    ("GET", "/backup/instance/options", "instance.get_instance_backup_options"),
    ("GET", "/backup/instance/jobs/{job_id}", "instance.get_instance_backup_job"),
    ("GET", "/backup/instance/jobs/{job_id}/file", "instance.download_instance_backup"),
    ("DELETE", "/backup/instance/jobs/{job_id}", "instance.delete_instance_backup_job"),
    ("POST", "/backup/panel/jobs", "panel.start_panel_backup"),
    ("GET", "/backup/panel/jobs/{job_id}", "panel.get_panel_backup_job"),
    ("GET", "/backup/panel/jobs/{job_id}/file", "panel.download_panel_backup"),
    ("DELETE", "/backup/panel/jobs/{job_id}", "panel.delete_panel_backup_job"),
    ("PUT", "/backup/restore/upload", "restore.upload_restore_archive"),
    ("POST", "/backup/restore/stage", "restore.start_restore_check"),
    ("GET", "/backup/restore/stage/{stage_id}", "restore.get_restore_check"),
    ("DELETE", "/backup/restore/stage/{stage_id}", "restore.delete_restore_check"),
    ("POST", "/backup/restore/stage/{stage_id}/confirm", "restore.confirm_restore_check"),
    ("GET", "/backup/restore/status", "restore.get_restore_status"),
    ("DELETE", "/backup/restore/pending", "restore.cancel_pending_restore"),
    ("POST", "/backup/restore/restart", "restore.restart_for_restore"),
    ("GET", "/backup/restore/outcome", "restore.get_restore_outcome"),
    ("GET", "/backup/asset/{asset_id}/prices", "exports.backup_asset_prices"),
    ("GET", "/backup/asset/{asset_id}/events", "exports.backup_asset_events"),
    ("GET", "/backup/fx/{base}/{quote}/rates", "exports.backup_fx_rates"),
]


def test_the_backup_router_registers_its_routes_in_order():
    """BACKUP-001 (C2): backup_router registers the five routes of instance.py, the four of panel.py, the nine of restore.py, then the three exports of exports.py, in that order, each with its method and endpoint, and a single tag: Hosting panel on panel.py's four, Backup & Export elsewhere."""
    print_section("BACKUP-001: the /backup router registers its routes in order (C2)")
    contexts = list(iter_route_contexts(backup_module.backup_router.routes))
    served = [(",".join(sorted(ctx.methods or ())), ctx.path, f"{getattr(ctx.endpoint, '__module__', '?').removeprefix(backup_module.__name__ + '.')}.{getattr(ctx.endpoint, '__name__', '?')}") for ctx in contexts]
    assert served == BACKUP_ROUTES, f"the /backup router changed: it must register the five routes of instance.py, the four of panel.py, the nine of restore.py, then the three exports of exports.py, in this order:\n  expected {BACKUP_ROUTES}\n  got      {served}"
    tags = [(ctx.path, list(getattr(ctx, "tags", []))) for ctx in contexts]
    assert tags == [(path, ["Hosting panel"] if endpoint.startswith("panel.") else ["Backup & Export"]) for _method, path, endpoint in BACKUP_ROUTES], f"each route of the /backup router must carry a single tag, Hosting panel on the four of panel.py, Backup & Export on the others:\n  got {tags}"
    print_success(f"{len(served)} routes, in their order: {[f'{method} {path}' for method, path, _endpoint in served]}")


# ============================================================================
# BACKUP-002/003: administrators only
# ============================================================================


@pytest.mark.asyncio
class TestAdministratorsOnly:
    """Every route of /backup/instance is for administrators: an archive holds every user's data."""

    @pytest.mark.parametrize(("method", "route"), INSTANCE_ROUTES)
    async def test_without_a_session_401(self, accounts, done_job, created_jobs, method, route):
        """BACKUP-002: without a session the route answers 401, on an existing job and its archive too; a refused DELETE leaves the job in place."""
        print_section(f"BACKUP-002: {method} /backup/instance{route} without a session → 401")

        async with httpx.AsyncClient(timeout=TIMEOUT) as anonymous:
            resp = await call_route(anonymous, method, route, done_job["job_id"], created_jobs)

        assert resp.status_code == 401, f"without a session the route must answer 401: {describe(resp)}"
        if method == "DELETE":
            await assert_job_in_place(accounts.admin, done_job["job_id"])
        print_success(f"{method} /backup/instance{route}: 401")

    @pytest.mark.parametrize(("method", "route"), INSTANCE_ROUTES)
    async def test_ordinary_user_403(self, accounts, done_job, created_jobs, method, route):
        """BACKUP-003: an ordinary user gets 403 from the route, on an existing job and its archive too; a refused DELETE leaves the job in place."""
        print_section(f"BACKUP-003: {method} /backup/instance{route} as an ordinary user → 403")

        async with accounts.user.client() as user:
            resp = await call_route(user, method, route, done_job["job_id"], created_jobs)

        assert resp.status_code == 403, f"an ordinary user must get 403: {describe(resp)}"
        if method == "DELETE":
            await assert_job_in_place(accounts.admin, done_job["job_id"])
        print_success(f"{method} /backup/instance{route}: 403")


# ============================================================================
# BACKUP-004..007: an administrator's jobs
# ============================================================================


@pytest.mark.asyncio
class TestInstanceBackup:
    async def test_backup_from_start_to_download(self, accounts, created_jobs, tmp_path):
        """BACKUP-004: start (202, running) → poll → done, every byte counted → download: a private zip attachment of the lane, database first, manifest last."""
        print_section("BACKUP-004: an administrator's backup, from the start to the download")
        lane_db = paths.database_path(get_data_dir())

        async with accounts.admin.client() as admin:
            started = await start_backup(admin, created_jobs)
            assert paths.is_job_id(started["job_id"]) and (started["status"], started["phase"]) == ("running", "preparing"), f"a start must answer with a job running, preparing: {started}"
            job = await wait_until_finished(admin, started["job_id"])
            assert (job["status"], job["error_code"]) == ("done", None) and job["finished_at"], f"the backup must end done: {job}"
            assert ARCHIVE_NAME.fullmatch(job["file_name"] or ""), f"a done job names its archive librefolio-backup-YYYYMMDD-HHMMSS.zip: {job}"
            assert job["file_size"] and job["total_bytes"] > 0 and job["done_bytes"] == job["total_bytes"], f"a done job gives the size of its archive and counts every byte it read: {job}"
            archive = tmp_path / job["file_name"]
            headers = await download(admin, job["job_id"], archive)

        disposition, filename = content_disposition(headers.get("content-disposition", ""))
        assert headers.get("content-type", "").split(";")[0].strip() == "application/zip", f"the archive must be served as application/zip, not {headers.get('content-type')!r}"
        assert (disposition, filename) == ("attachment", job["file_name"]), f"the archive must come as an attachment named {job['file_name']}: Content-Disposition {headers.get('content-disposition')!r}"
        assert headers.get("cache-control") == "no-store", f"an archive holds every user's data, and no cache may keep it: Cache-Control {headers.get('cache-control')!r}"
        assert archive.stat().st_size == job["file_size"], f"the download must be the job's archive, {job['file_size']} bytes, got {archive.stat().st_size}"

        archived_db = tmp_path / "archived-app.db"
        with zipfile.ZipFile(archive) as zf:
            names = zf.namelist()
            assert names[0] == DATABASE_ENTRY and names[-1] == MANIFEST_ENTRY, f"the archive's first entry must be {DATABASE_ENTRY} and its last {MANIFEST_ENTRY}: {names[:3]} … {names[-3:]}"
            damaged = zf.testzip()
            assert damaged is None, f"entry {damaged} of the archive fails its CRC"
            manifest = json.loads(zf.read(MANIFEST_ENTRY))
            with zf.open(DATABASE_ENTRY) as source, archived_db.open("wb") as target:
                shutil.copyfileobj(source, target)
        assert (manifest["format"], manifest["origin"]) == ("librefolio-backup", "ui"), f"the manifest of a backup started from the API: {manifest['format']!r}, origin {manifest['origin']!r}"
        assert [entry["path"] for entry in manifest["files"]] == names[:-1], "the manifest must list every other entry of the archive, in its order"
        assert manifest["alembic_revision"] == alembic_revision(lane_db), f"the manifest must give the Alembic revision of the lane's database, {alembic_revision(lane_db)!r}: {manifest['alembic_revision']!r}"
        assert is_superuser(archived_db, accounts.admin.username) is True, f"the archived database must be the lane's, as of the start: it must hold the administrator {accounts.admin.username}"
        print_success(f"{job['file_name']}: {job['file_size']} bytes, {len(names)} entries, revision {manifest['alembic_revision']}, {accounts.admin.username} inside")

    @needs_flock
    async def test_start_while_a_run_holds_the_lock_is_busy(self, accounts, created_jobs):
        """BACKUP-005: while a run holds the lane's backup lock, a start answers 409 backup_busy."""
        print_section("BACKUP-005: a start while a run holds the lock → 409 backup_busy")

        async with accounts.admin.client() as admin:
            # The lane's backup run lock is a global surface: every backup of the lane takes it. This test holds it for
            # the duration of this one request, as a running backup would; no other unit starts a backup on the lane,
            # and every job of this module has released it before its own test ends.
            async with holding_the_run_lock():
                resp = await post_start(admin, created_jobs)

        assert_error(resp, 409, "backup_busy")
        print_success("409 backup_busy")

    async def test_delete_removes_a_finished_job(self, accounts, created_jobs):
        """BACKUP-006: DELETE of a finished job answers 204; then the job and its file answer 404 backup_job_not_found, and its folder, archive included, is gone."""
        print_section("BACKUP-006: DELETE of a finished job")

        async with accounts.admin.client() as admin:
            started = await start_backup(admin, created_jobs)
            job = await wait_until_finished(admin, started["job_id"])
            assert job["status"] == "done", f"premise: the job must end done: {job}"
            folder = paths.job_dir(get_data_dir(), job["job_id"])
            assert (folder / job["file_name"]).is_file(), f"premise: the archive of the job must be on the server, in {folder}"

            deleted = await admin.delete(job_url(job["job_id"]))
            read = await admin.get(job_url(job["job_id"]))
            fetched = await admin.get(file_url(job["job_id"]))

        assert deleted.status_code == 204 and not deleted.content, f"DELETE of a finished job must answer 204, without a body: {describe(deleted)}"
        assert_error(read, 404, "backup_job_not_found")
        assert_error(fetched, 404, "backup_job_not_found")
        assert not folder.exists(), f"DELETE must remove the job's folder and its archive from the server: {folder} still holds {sorted(path.name for path in folder.iterdir())}"
        print_success("204, then 404 backup_job_not_found for the job and its file, the folder gone")

    @needs_flock
    async def test_a_job_without_an_archive(self, accounts, created_jobs):
        """BACKUP-007: while its run holds the lock, a job's file is 409 backup_job_not_ready and its DELETE 409 backup_job_running; with the lock free it reads as failed, backup_interrupted, and DELETE removes it."""
        print_section("BACKUP-007: a job without an archive: running, then interrupted")
        data_dir = get_data_dir()
        job_id = secrets.token_hex(16)
        created_jobs.append(job_id)
        # A run in progress, as jobs.py writes one; its run is this test, holding the lock below.
        folder = paths.ensure_private_dir(paths.job_dir(data_dir, job_id), data_dir)
        running = jobs.BackupJob(job_id=job_id, origin="ui", status="running", phase="files", done_bytes=1, total_bytes=2, created_at=datetime.now(UTC))
        (folder / paths.STATE_FILE).write_text(running.to_json(), encoding="utf-8")

        async with accounts.admin.client() as admin:
            # The lane's backup run lock, held for the three requests that need a run in progress, as BACKUP-005 does.
            async with holding_the_run_lock():
                while_running = await admin.get(job_url(job_id))
                file_while_running = await admin.get(file_url(job_id))
                delete_while_running = await admin.delete(job_url(job_id))
            interrupted = await admin.get(job_url(job_id))
            file_interrupted = await admin.get(file_url(job_id))
            deleted = await admin.delete(job_url(job_id))
            gone = await admin.get(job_url(job_id))

        assert while_running.status_code == 200 and while_running.json()["status"] == "running", f"while its run holds the lock the job reads as running: {describe(while_running)}"
        assert_error(file_while_running, 409, "backup_job_not_ready")
        assert_error(delete_while_running, 409, "backup_job_running")
        assert interrupted.status_code == 200, f"the job must stay readable: {describe(interrupted)}"
        state = interrupted.json()
        assert (state["status"], state["error_code"]) == ("failed", "backup_interrupted") and state["finished_at"], f"a running state with the lock free belongs to a run that died: failed, backup_interrupted: {state}"
        assert_error(file_interrupted, 409, "backup_job_not_ready")
        assert deleted.status_code == 204, f"DELETE of a failed job must answer 204: {describe(deleted)}"
        assert_error(gone, 404, "backup_job_not_found")
        assert not folder.exists(), f"DELETE must remove the job's folder: {folder} still holds {sorted(path.name for path in folder.iterdir())}"
        print_success("running: file 409 backup_job_not_ready, DELETE 409 backup_job_running; then failed, backup_interrupted; DELETE 204")


# ============================================================================
# BACKUP-008/009: job ids
# ============================================================================


@pytest.mark.asyncio
class TestJobIds:
    async def test_unknown_job_404(self, accounts):
        """BACKUP-008: a job id of the right shape that names no job: 404 backup_job_not_found from the job, its file and DELETE."""
        print_section("BACKUP-008: an unknown job id → 404 backup_job_not_found")
        job_id = secrets.token_hex(16)
        assert not paths.job_dir(get_data_dir(), job_id).exists(), f"premise: the lane has no job {job_id}"

        async with accounts.admin.client() as admin:
            answers = [await admin.request(method, INSTANCE_URL + route.format(job_id=job_id)) for method, route in JOB_ROUTES]

        for resp in answers:
            assert_error(resp, 404, "backup_job_not_found")
        print_success(f"{', '.join(f'{method} {route}' for method, route in JOB_ROUTES)}: 404 backup_job_not_found")

    @pytest.mark.parametrize("job_id", MALFORMED_JOB_IDS)
    async def test_malformed_job_id_404(self, accounts, job_id):
        """BACKUP-009: an id the jobs never make is not found by the job, its file or DELETE: 404 backup_job_not_found, never a 500."""
        print_section(f"BACKUP-009: job id {job_id!r} → 404 backup_job_not_found")

        async with accounts.admin.client() as admin:
            answers = [await admin.request(method, INSTANCE_URL + route.format(job_id=job_id)) for method, route in JOB_ROUTES]

        for resp in answers:
            assert_error(resp, 404, "backup_job_not_found")
        print_success(f"{job_id!r}: 404 backup_job_not_found from the job, its file and DELETE")


# ============================================================================
# BACKUP-010: the placeholders are gone
# ============================================================================


@pytest.mark.asyncio
class TestRemovedPlaceholders:
    @pytest.mark.parametrize(("method", "path", "body"), REMOVED_PLACEHOLDERS)
    async def test_placeholder_is_gone(self, accounts, method, path, body):
        """BACKUP-010: a placeholder lot B1 removed answers 404 or 405, to an administrator too: no route serves it any more."""
        print_section(f"BACKUP-010: {method} {path} is gone")

        async with accounts.admin.client() as admin:
            resp = await admin.request(method, f"{API_BASE}{path}", json=body)

        assert resp.status_code in (404, 405), f"{method} {path} went with the placeholders (B1), yet a route serves it: {describe(resp)}"
        print_success(f"{method} {path}: {resp.status_code}")

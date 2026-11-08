"""
The list of the instance's kept backups (lot FB-24 backend, interface §5): ``GET /api/v1/backup/instance/jobs``, and the
guard that the hosting panel's routes do not move.

Under test: ``backend/app/api/v1/backup/instance.py`` (the new list route), ``job_views.py``, ``panel.py`` and
``backend/app/schemas/backup.py`` (``InstanceBackupList``, ``InstanceBackupEntry``), through the jobs of
``services/platform/instance_backup/jobs.py`` run for real. The service side (``list_kept``, ``plan_cleanup``, the
settings' effective values) has suites of its own, ``services backup-*``.

Contract (``B6r-fb24-backend-interface.md`` §2, §5):

- LIST-001, who: without a session 401, an ordinary user 403, an administrator 200 ``{"items": [...]}``. The hosting
  panel gets no list: ``GET /backup/panel/jobs`` is still no route (404 or 405), whatever the token.
- LIST-002, the entries: a backup of each origin the app can start (``ui``, ``panel``, a secure ``ui`` one with a
  password) shows in the list under its ``job_id`` with the fields of ``InstanceBackupJob`` (equal to what the job's
  own ``GET`` says) and ``origin``; ``file_sha256`` is 64 lowercase hex digits and the SHA-256 of the bytes the download
  serves; ``encrypted`` is true for the secure backup only; the newest backup of those three comes first.
- LIST-003, kept means a folder: a finished backup moves from ``backups/.jobs/<id>/`` to
  ``backups/librefolio-backup-YYYYMMDD-HHMMSS-<origin>-<first 8 of the id>/`` with its ``state.json`` and its archive
  (the archive keeps today's name); the job id does not change.
- LIST-004, what is never listed: a running job, a failed one, a done one that never left ``.jobs/``, a failed state or
  a state with no archive in a kept-looking folder, a loose archive of the old layout. A real kept backup is listed
  beside them (the barrier: an empty list is not an answer).
- LIST-005, the id outlives the move: after the backup is done, ``GET /jobs/{id}``, its ``/file`` and ``DELETE`` answer
  on the same id (guard, green before the change); after ``DELETE`` the id is not listed and its folder is gone (red).
- LIST-006, the panel's routes do not change from the outside (GUARD, green before and after the change): ``POST`` 202
  with a running job; the poll ends done with ``file_name``, ``file_size``, ``file_sha256``, ``sealed``; ``/file`` gives
  the bytes whose SHA-256 the job states (``application/zip``, or ``application/x-tar`` when sealed); ``DELETE`` 204,
  then 404 ``backup_job_not_found`` for the job and its file, and no folder of it left under ``backups/``; a ``ui`` job
  seen with the panel's token is 404 from the three routes and stays untouched.
- LIST-007, OpenAPI. Guard (green before): the panel's and the administrators' ``GET /jobs/{id}`` answer
  ``InstanceBackupJob``, which has NO ``origin`` field. Contract (red before): ``GET /backup/instance/jobs`` answers
  ``InstanceBackupList`` whose ``items`` are ``InstanceBackupEntry``: the properties of ``InstanceBackupJob`` plus
  ``origin``, one of ``ui``, ``cli``, ``pre-restore``, ``panel``.

Untestable here: that a kept backup never expires by age (``JOB_RETENTION`` is a constant of the service, with no seam
the API reaches; the service suite owns it), and the cleanup's own cases (``plan_cleanup``, ``apply_cleanup``).

Pure (``isolation="pure"``): an app of the test holds ``backup_router`` under ``/api/v1``; ``get_current_user`` answers
the administrator (or an ordinary user, or the real one for the 401), so the real ``require_admin`` decides. The data
directory is a copy of a migrated database under ``tmp_path`` (as ``test_backup_secure_api.py`` makes it) and the
process is configured with it, the panel's token set with ``monkeypatch``: the backups run for real, in threads of this
process, under that directory's own run lock. No lane server, data directory or network is reached, and nothing is
counted or indexed: every assertion is about the ``job_id`` the test started or wrote.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
import secrets
import time
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from pyrage import x25519

from backend.app.api.v1.auth import get_current_user
from backend.app.api.v1.backup import backup_router
from backend.app.services.platform.instance_backup import jobs, paths
from backend.app.services.platform.instance_backup.jobs import _RunLock
from backend.app.utils.runtime.version import get_git_version
from backend.test_scripts.test_services import test_backup_staging as cases
from backend.test_scripts.test_utils import print_section, print_success

# The module fixtures of test_backup_staging.py, as test_backup_secure_api.py takes them: a database made once by alembic.
databases = cases.databases

IN_PROCESS = "http://in-process"
INSTANCE = "/api/v1/backup/instance"
JOBS = f"{INSTANCE}/jobs"
PANEL = "/api/v1/backup/panel/jobs"

ADMIN = SimpleNamespace(id=1, username="fb24-admin", is_superuser=True)
REGULAR = SimpleNamespace(id=2, username="fb24-user", is_superuser=False)

TOKEN_VARIABLE = "LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN"
TOKEN_FILE_VARIABLE = "LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN_FILE"
RECIPIENTS_VARIABLE = "LIBREFOLIO_BACKUP_RECIPIENTS"
INSTANCE_KEY_VARIABLE = "LIBREFOLIO_INSTANCE_KEY"
INSTANCE_KEY_FILE_VARIABLE = "LIBREFOLIO_INSTANCE_KEY_FILE"
PROFILE_VARIABLE = "LIBREFOLIO_PROFILE"

#: The password of the secure backup of this module (meets the archive rules), a test value.
PASSWORD = "Correct-Horse-Battery-9"
#: Seconds a backup of a tiny data directory may take on a loaded machine: a hang still ends.
JOB_DEADLINE_S = 120.0
POLL_INTERVAL_S = 0.05

#: The name a finished backup's folder takes in ``backups/`` (interface §1): the archive inside keeps today's name.
KEPT_NAME = re.compile(r"librefolio-backup-\d{8}-\d{6}-(?P<origin>[a-z-]+)-(?P<short>[0-9a-f]{8})")
SHA256 = re.compile(r"[0-9a-f]{64}")
ORIGINS = {"ui", "cli", "pre-restore", "panel"}
#: What an entry adds to its job's view: who made it, and the space it takes once restored (A10, T-10).
ENTRY_ONLY = {"origin", "content_bytes", "content_parts"}
JOB_NOT_FOUND = (404, "backup_job_not_found")


# =============================================================================
# The instance of a test, the app, the requests
# =============================================================================


@dataclass(frozen=True)
class Instance:
    """A real data directory of the test, the process's own for the test, and the hosting panel's token."""

    data: Path
    token: str

    @property
    def bearer(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}


def lock_held(path: Path) -> bool:
    """Whether a run holds the lock at ``path`` now: a probe, taken and released at once when free; none is created."""
    if not path.exists():
        return False
    probe = _RunLock(path)
    if probe.try_acquire():
        probe.release()
        return False
    return True


def wait_for_free_lock(data: Path) -> None:
    """Block (with a deadline) until no run of ``data`` holds its lock: the end of every backup a test started."""
    deadline = time.monotonic() + JOB_DEADLINE_S
    while lock_held(paths.lock_path(data)):
        assert time.monotonic() < deadline, f"a backup of {data} still holds the run lock after {JOB_DEADLINE_S:.0f}s"
        time.sleep(POLL_INTERVAL_S)


@pytest.fixture
def instance(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, databases) -> Iterator[Instance]:
    """A real data directory under ``tmp_path`` (a database at the head, accounts, files), configured as this process's,
    the panel's routes on with a token of the test, no recipients, self-hosted. Every backup it started has ended at the
    end of the test, after a red too."""
    data = cases.make_data_dir(tmp_path / "data", databases.head)
    cases.configure(monkeypatch, data)
    for name in (INSTANCE_KEY_VARIABLE, INSTANCE_KEY_FILE_VARIABLE, TOKEN_FILE_VARIABLE, RECIPIENTS_VARIABLE):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(PROFILE_VARIABLE, "selfhosted")
    token = secrets.token_hex(32)
    monkeypatch.setenv(TOKEN_VARIABLE, token)
    yield Instance(data, token)
    wait_for_free_lock(data)
    get_git_version.cache_clear()


def backup_app(user: SimpleNamespace | None = ADMIN) -> FastAPI:
    """``backup_router`` under ``/api/v1``, as ``router.py`` mounts it. ``get_current_user`` answers ``user``, so the real
    ``require_admin`` decides; None leaves the real one, which refuses a request with no session (401)."""
    app = FastAPI()
    app.include_router(backup_router, prefix="/api/v1")
    if user is not None:
        app.dependency_overrides[get_current_user] = lambda: user
    return app


async def call(method: str, path: str, *, app: FastAPI | None = None, **request: Any) -> httpx.Response:
    """One request to an app of the test, an administrator's by default. An exception a route does not turn into an
    answer comes back as a plain 500 and fails an assertion instead of erroring."""
    transport = httpx.ASGITransport(app=app or backup_app(), raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url=IN_PROCESS) as client:
        return await client.request(method, path, **request)


def shown(response: httpx.Response) -> str:
    return f"{response.request.method} {response.request.url} answered {response.status_code}: {response.text[:600]}"


def code_of(response: httpx.Response) -> tuple[int, str | None]:
    if not response.headers.get("content-type", "").startswith("application/json"):
        return response.status_code, None
    body = response.json()
    detail = body.get("detail") if isinstance(body, dict) else None
    return response.status_code, detail.get("code") if isinstance(detail, dict) else None


async def ended(instance: Instance, job_id: str) -> dict:
    """The final state of a job (read as an administrator, who sees every job), once it has ended and its run has let the
    run lock go. A job that is gone fails the test; the only wait, with a deadline."""
    deadline = time.monotonic() + JOB_DEADLINE_S
    while True:
        response = await call("GET", f"{JOBS}/{job_id}")
        assert response.status_code == 200, f"a job must stay readable until it is deleted: {shown(response)}"
        if response.json()["status"] != "running" and not lock_held(paths.lock_path(instance.data)):
            return response.json()
        assert time.monotonic() < deadline, f"backup job {job_id} has not ended within {JOB_DEADLINE_S:.0f}s: {response.json()}"
        await asyncio.sleep(POLL_INTERVAL_S)


async def start(instance: Instance, origin: str, *, password: str | None = None) -> str:
    """Start a backup of ``origin`` (``ui``: an administrator's, with ``password`` for a secure one; ``panel``: the panel's
    token) and wait for it to end done: its job id."""
    if origin == "panel":
        response = await call("POST", PANEL, headers=instance.bearer)
    else:
        response = await call("POST", INSTANCE, json={"password": password} if password else None)
    assert response.status_code == 202, f"the start of a {origin} backup answers 202 and its job: {shown(response)}"
    job_id = response.json()["job_id"]
    job = await ended(instance, job_id)
    assert (job["status"], job["error_code"]) == ("done", None), f"premise: the {origin} backup ends done: {job}"
    return job_id


async def listed(entries_of: str = JOBS) -> dict[str, dict]:
    """The administrator's list, by job id. Anything but a 200 with ``items`` fails the test with the answer."""
    response = await call("GET", entries_of)
    assert response.status_code == 200 and isinstance(response.json().get("items"), list), f"GET {entries_of} must answer 200 with items: {shown(response)}"
    return {item["job_id"]: item for item in response.json()["items"]}


def kept_folders(data: Path, job_id: str) -> list[Path]:
    """The folders of ``backups/`` that are this job's kept backup: a kept-looking name ending in the job's short id."""
    folder = paths.backups_dir(data)
    if not folder.is_dir():
        return []
    return sorted(path for path in folder.iterdir() if path.is_dir() and KEPT_NAME.fullmatch(path.name) and path.name.endswith(f"-{job_id[:8]}"))


def a_recipient() -> str:
    return str(x25519.Identity.generate().to_public())


def job_state(job_id: str, *, status: str, file_name: str | None = None, created_at: datetime | None = None, origin: str = "ui") -> jobs.BackupJob:
    """A state as a run writes it, for a job the test makes up."""
    created = created_at or datetime.now(UTC) - timedelta(minutes=5)
    done = status == "done"
    return jobs.BackupJob(
        job_id=job_id,
        origin=origin,  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        phase="files" if status == "running" else None,
        done_bytes=1,
        total_bytes=1 if status != "running" else 2,
        created_at=created,
        finished_at=None if status == "running" else created + timedelta(seconds=1),
        file_name=file_name,
        file_size=4 if file_name else None,
        file_sha256=hashlib.sha256(b"fake").hexdigest() if done and file_name else None,
        error_code="backup_failed" if status == "failed" else None,
    )


def write_job(folder: Path, state: jobs.BackupJob, *, archive: bool) -> None:
    """A job folder with its ``state.json`` (and a small archive named ``state.file_name``)."""
    folder.mkdir(parents=True)
    (folder / paths.STATE_FILE).write_text(state.to_json(), encoding="utf-8")
    if archive and state.file_name:
        (folder / state.file_name).write_bytes(b"fake")


# =============================================================================
# LIST-001: who may read the list
# =============================================================================


@pytest.mark.asyncio
async def test_the_list_is_for_administrators_only(instance):
    """LIST-001: no session 401, an ordinary user 403, an administrator 200 with ``items``; the panel's token opens no
    list. Red today: ``GET /backup/instance/jobs`` is no route, every request is 404 (or 405)."""
    print_section("LIST-001: GET /backup/instance/jobs, who")

    anonymous = await call("GET", JOBS, app=backup_app(None))
    ordinary = await call("GET", JOBS, app=backup_app(REGULAR))
    admin = await call("GET", JOBS)
    panel_list = await call("GET", PANEL, headers=instance.bearer)

    assert anonymous.status_code == 401, f"without a session the list answers 401: {shown(anonymous)}"
    assert ordinary.status_code == 403, f"an ordinary user gets 403 from the list: {shown(ordinary)}"
    assert admin.status_code == 200 and isinstance(admin.json().get("items"), list), f"an administrator gets 200 and {{items: [...]}}: {shown(admin)}"
    assert panel_list.status_code in (404, 405), f"the hosting panel has no list route (no new route under /backup/panel): {shown(panel_list)}"
    print_success("401 / 403 / 200 {items}; the panel has no list")


# =============================================================================
# LIST-002 .. LIST-004: what the list says
# =============================================================================


@pytest.mark.asyncio
async def test_the_list_shows_each_kept_backup_with_its_origin_hash_and_flags(instance):
    """LIST-002: a ui backup, a panel one (token) and a secure ui one (password), each started and finished in turn: each
    is in the list under its job id with the fields of its own job view plus ``origin``; ``file_sha256`` is the SHA-256 of
    the downloaded bytes; ``encrypted`` is true for the secure one only; the newest of the three comes first. Red today:
    the list route does not exist."""
    print_section("LIST-002: the kept backups, their origin, hash and flags")
    ui_id = await start(instance, "ui")
    panel_id = await start(instance, "panel")
    secure_id = await start(instance, "ui", password=PASSWORD)

    entries = await listed()

    wanted = {ui_id: ("ui", False), panel_id: ("panel", False), secure_id: ("ui", True)}
    missing = sorted(set(wanted) - set(entries))
    assert missing == [], f"every finished backup is listed; missing {missing} (listed ids: {sorted(entries)})"
    for job_id, (origin, encrypted) in wanted.items():
        entry = entries[job_id]
        job = (await call("GET", f"{JOBS}/{job_id}")).json()
        assert entry["origin"] == origin, f"{job_id}: origin {origin!r}: {entry}"
        assert {name: value for name, value in entry.items() if name not in ENTRY_ONLY} == job, f"{job_id}: an entry is the job's own view plus origin and its content"
        parts = entry["content_parts"]
        assert entry["content_bytes"] > 0 and parts["database_bytes"] > 0, f"{job_id}: A10, the space it takes once restored: {entry['content_bytes']}, {parts}"
        assert sum(parts.values()) == entry["content_bytes"], f"{job_id}: its parts add up to it: {parts}"
        assert (entry["encrypted"], entry["status"]) == (encrypted, "done"), f"{job_id}: encrypted {encrypted}, done: {entry}"
        assert SHA256.fullmatch(entry["file_sha256"] or ""), f"{job_id}: file_sha256 is 64 lowercase hex digits: {entry['file_sha256']!r}"
        assert entry["file_name"] and entry["file_size"], f"{job_id}: the file's name and size: {entry}"
        download = await call("GET", f"{JOBS}/{job_id}/file")
        assert download.status_code == 200 and len(download.content) == entry["file_size"], f"{job_id}: the download is the listed file: {shown(download)[:200]}"
        assert hashlib.sha256(download.content).hexdigest() == entry["file_sha256"], f"{job_id}: file_sha256 is the SHA-256 of the bytes the download serves"
    order = [job_id for job_id in entries if job_id in wanted]
    assert order == [secure_id, panel_id, ui_id], f"newest first among the three backups made one after the other: {order}"
    print_success("ui, panel and secure entries: origin, SHA-256, encrypted, newest first")


@pytest.mark.asyncio
async def test_a_sealed_panel_backup_is_listed_sealed(instance, monkeypatch):
    """LIST-002b: with ``LIBREFOLIO_BACKUP_RECIPIENTS`` set the panel's backup is a sealed ``.tar``; its entry reads
    ``origin`` panel, ``sealed`` true, ``sealed_recipients`` the recipient, ``encrypted`` true. Red today: no list."""
    print_section("LIST-002b: a sealed panel backup in the list")
    recipient = a_recipient()
    monkeypatch.setenv(RECIPIENTS_VARIABLE, recipient)
    job_id = await start(instance, "panel")

    entries = await listed()

    assert job_id in entries, f"the sealed backup is listed; listed ids: {sorted(entries)}"
    entry = entries[job_id]
    assert (entry["origin"], entry["sealed"], entry["sealed_recipients"], entry["encrypted"]) == ("panel", True, [recipient], True), f"a sealed panel backup: {entry}"
    assert entry["file_name"].endswith(".tar"), f"a sealed backup is a .tar: {entry['file_name']}"
    print_success(f"{entry['file_name']}: sealed for 1 recipient")


@pytest.mark.asyncio
async def test_a_finished_backup_moves_into_backups_under_its_kept_name(instance):
    """LIST-003: once done, the backup is not in ``backups/.jobs/`` any more: it is in
    ``backups/librefolio-backup-YYYYMMDD-HHMMSS-<origin>-<first 8 of the id>/`` with its ``state.json`` (the same job id)
    and its archive under the name it always had. The folder name carries the creation time (UTC) of the job and its
    origin. Red today: the folder stays in ``.jobs/``."""
    print_section("LIST-003: the move into backups/")
    ui_id = await start(instance, "ui")
    panel_id = await start(instance, "panel")

    for job_id, origin in ((ui_id, "ui"), (panel_id, "panel")):
        job = (await call("GET", f"{JOBS}/{job_id}")).json()
        folders = kept_folders(instance.data, job_id)
        assert len(folders) == 1, f"{origin}: one kept folder named librefolio-backup-<date>-<origin>-<id[:8]> under backups/: {sorted(p.name for p in paths.backups_dir(instance.data).iterdir())}"
        folder = folders[0]
        parts = KEPT_NAME.fullmatch(folder.name)
        assert parts is not None and parts["origin"] == origin and parts["short"] == job_id[:8], f"{origin}: the name carries the origin and the short id: {folder.name}"
        created = datetime.fromisoformat(job["created_at"]).astimezone(UTC)
        assert folder.name.startswith(f"librefolio-backup-{created:%Y%m%d-%H%M%S}-"), f"{origin}: the name carries the job's creation time in UTC: {folder.name} vs {created.isoformat()}"
        assert (folder / job["file_name"]).is_file(), f"{origin}: the archive keeps its name inside: {sorted(p.name for p in folder.iterdir())}"
        state = jobs.BackupJob.from_json((folder / paths.STATE_FILE).read_text(encoding="utf-8"))
        assert (state.job_id, state.status, state.origin) == (job_id, "done", origin), f"{origin}: the state inside is the same job: {state}"
        assert not paths.job_dir(instance.data, job_id).exists(), f"{origin}: nothing of the job is left in backups/.jobs/"
    print_success("ui and panel backups: backups/<kept name>/state.json + archive; .jobs/<id> gone")


@pytest.mark.asyncio
async def test_what_is_not_a_finished_kept_backup_is_never_listed(instance):
    """LIST-004: a running job and a failed one and a done one still in ``.jobs/``; in ``backups/`` a kept-looking folder
    whose state failed, one whose state is done but whose archive is missing, and a loose archive of the old layout: none
    is listed, while a real backup made by the test is (the barrier). Red today: the list does not exist."""
    print_section("LIST-004: running, failed and loose files are not listed")
    real_id = await start(instance, "ui")
    data = instance.data
    decoys: dict[str, str] = {}
    # In .jobs/: a run in progress, a failed run, and a done run that was never kept.
    for label, status in (("running-in-jobs", "running"), ("failed-in-jobs", "failed"), ("done-in-jobs", "done")):
        job_id = secrets.token_hex(16)
        name = "librefolio-backup-20261001-000000.zip"
        write_job(paths.job_dir(data, job_id), job_state(job_id, status=status, file_name=name if status == "done" else None), archive=True)
        decoys[label] = job_id
    # In backups/ under a kept-looking name: a failed state, and a done state with no archive.
    for label, status in (("failed-kept-looking", "failed"), ("done-without-archive", "done")):
        job_id = secrets.token_hex(16)
        folder = paths.backups_dir(data) / f"librefolio-backup-20261001-000000-ui-{job_id[:8]}"
        write_job(folder, job_state(job_id, status=status, file_name="librefolio-backup-20261001-000000.zip" if status == "done" else None), archive=False)
        decoys[label] = job_id
    loose = paths.backups_dir(data) / "librefolio-backup-20261001-000000.zip"
    loose.write_bytes(b"PK an archive of the old flat layout")

    entries = await listed()

    assert real_id in entries, f"the barrier: a real kept backup is listed; listed ids: {sorted(entries)}"
    shown_decoys = sorted(label for label, job_id in decoys.items() if job_id in entries)
    assert shown_decoys == [], f"never listed: {shown_decoys}"
    assert all(item["status"] == "done" for item in entries.values()), "the list holds finished backups only"
    assert loose.read_bytes() == b"PK an archive of the old flat layout", "a loose archive of the old layout is neither listed nor touched"
    print_success("running, failed, loose: none listed; the real backup is")


# =============================================================================
# LIST-005: the id outlives the move
# =============================================================================


@pytest.mark.asyncio
async def test_a_finished_backup_stays_readable_downloadable_and_deletable_under_its_id(instance):
    """LIST-005a (GUARD, green before and after): after the backup is done (and moved), ``GET /jobs/{id}``, its
    ``/file`` and ``DELETE`` still answer on the very same id; the file is the one the job describes; DELETE is 204, then
    404 ``backup_job_not_found`` for the job and its file, and nothing of the job is left under ``backups/``."""
    print_section("LIST-005a: GET, file and DELETE on the id after the backup ended")
    job_id = await start(instance, "ui")

    job = await call("GET", f"{JOBS}/{job_id}")
    archive = await call("GET", f"{JOBS}/{job_id}/file")
    deleted = await call("DELETE", f"{JOBS}/{job_id}")
    after = await call("GET", f"{JOBS}/{job_id}")
    file_after = await call("GET", f"{JOBS}/{job_id}/file")

    assert job.status_code == 200 and job.json()["status"] == "done", f"the finished job still reads: {shown(job)}"
    assert archive.status_code == 200 and hashlib.sha256(archive.content).hexdigest() == job.json()["file_sha256"], f"the archive downloads, and is the described one: {shown(archive)[:200]}"
    assert deleted.status_code == 204 and not deleted.content, f"DELETE answers 204: {shown(deleted)}"
    assert code_of(after) == JOB_NOT_FOUND and code_of(file_after) == JOB_NOT_FOUND, f"after DELETE the id is unknown: {shown(after)} / {shown(file_after)}"
    assert not paths.job_dir(instance.data, job_id).exists() and kept_folders(instance.data, job_id) == [], "no folder of the job is left, in .jobs/ or in backups/"
    print_success("done job: GET 200, file 200, DELETE 204, then 404 backup_job_not_found")


@pytest.mark.asyncio
async def test_a_deleted_backup_leaves_the_list(instance):
    """LIST-005b: a kept backup is listed; after ``DELETE`` its id is not (a neighbour that was not deleted still is). Red
    today: the list does not exist."""
    print_section("LIST-005b: DELETE removes the entry")
    gone_id = await start(instance, "ui")
    kept_id = await start(instance, "ui")
    before = await listed()

    deleted = await call("DELETE", f"{JOBS}/{gone_id}")
    after = await listed()

    assert gone_id in before and kept_id in before, f"premise: both backups are listed before; listed ids: {sorted(before)}"
    assert deleted.status_code == 204, f"DELETE answers 204: {shown(deleted)}"
    assert gone_id not in after, "the deleted backup is not listed any more"
    assert kept_id in after, "the other backup is still listed"
    print_success("deleted entry gone, the other one stays")


# =============================================================================
# LIST-006: the panel's routes do not change from the outside
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("sealed", [False, True], ids=["clear", "sealed"])
async def test_the_panel_routes_are_identical_from_the_outside(instance, monkeypatch, sealed):
    """LIST-006 (GUARD, green before and after the change): the panel starts (202, running), polls its job to done with
    ``file_name``, ``file_size``, ``file_sha256`` (the SHA-256 of what ``/file`` serves) and ``sealed``, downloads the
    archive (``application/zip``; ``application/x-tar`` when sealed), deletes it (204), then every route answers 404
    ``backup_job_not_found`` and no folder of the job is left in ``backups/``. The job view has no ``origin``."""
    print_section(f"LIST-006: the hosting panel's four routes, {'sealed' if sealed else 'clear'}")
    recipient = a_recipient()
    if sealed:
        monkeypatch.setenv(RECIPIENTS_VARIABLE, recipient)
    bearer = instance.bearer

    started = await call("POST", PANEL, headers=bearer)
    assert started.status_code == 202, f"the panel's start answers 202: {shown(started)}"
    first = started.json()
    job_id = first["job_id"]
    assert first["status"] == "running" and "origin" not in first, f"a running job, and a view with no origin: {first}"
    await ended(instance, job_id)
    polled = await call("GET", f"{PANEL}/{job_id}", headers=bearer)
    archive = await call("GET", f"{PANEL}/{job_id}/file", headers=bearer)
    deleted = await call("DELETE", f"{PANEL}/{job_id}", headers=bearer)
    after = [await call(method, path, headers=bearer) for method, path in (("GET", f"{PANEL}/{job_id}"), ("GET", f"{PANEL}/{job_id}/file"), ("DELETE", f"{PANEL}/{job_id}"))]

    job = polled.json()
    assert polled.status_code == 200 and job["status"] == "done" and "origin" not in job, f"the poll ends done, the view still has no origin: {shown(polled)}"
    assert job["file_name"] and job["file_size"] and job["sealed"] is sealed, f"file_name, file_size and sealed on the done job: {job}"
    assert job["file_name"].endswith(".tar" if sealed else ".zip"), f"a sealed backup is a .tar, a clear one a .zip: {job['file_name']}"
    assert archive.status_code == 200 and len(archive.content) == job["file_size"], f"/file gives the archive: {shown(archive)[:200]}"
    assert hashlib.sha256(archive.content).hexdigest() == job["file_sha256"], "file_sha256 is the SHA-256 of the bytes /file serves"
    expected_type = "application/x-tar" if sealed else "application/zip"
    assert archive.headers["content-type"].split(";")[0] == expected_type, f"/file is {expected_type}: {archive.headers['content-type']}"
    assert deleted.status_code == 204, f"DELETE answers 204: {shown(deleted)}"
    assert [code_of(response) for response in after] == [JOB_NOT_FOUND] * 3, f"after DELETE the poll, the file and a second DELETE are 404 backup_job_not_found: {[shown(r) for r in after]}"
    assert not paths.job_dir(instance.data, job_id).exists() and kept_folders(instance.data, job_id) == [], "DELETE leaves no folder of the job under backups/"
    print_success(f"{job['file_name']}: 202 → done → file → 204 → 404")


@pytest.mark.asyncio
async def test_a_ui_job_is_invisible_to_the_panel_after_it_is_kept(instance):
    """LIST-006b (GUARD): an administrator's (``ui``) finished backup seen with the panel's token answers 404
    ``backup_job_not_found`` from the poll, the download and the delete; the job and its archive are untouched (the
    administrator still reads and downloads it)."""
    print_section("LIST-006b: a ui job is 404 to the panel")
    job_id = await start(instance, "ui")

    answers = [await call(method, f"{PANEL}/{job_id}{suffix}", headers=instance.bearer) for method, suffix in (("GET", ""), ("GET", "/file"), ("DELETE", ""))]
    job = await call("GET", f"{JOBS}/{job_id}")
    archive = await call("GET", f"{JOBS}/{job_id}/file")

    assert [code_of(response) for response in answers] == [JOB_NOT_FOUND] * 3, f"the panel cannot see a ui job: {[shown(r) for r in answers]}"
    assert job.status_code == 200 and archive.status_code == 200, f"the ui job is untouched by the panel's DELETE: {shown(job)}, {shown(archive)[:200]}"
    print_success("ui job: 404 to the panel, intact for the administrator")


# =============================================================================
# LIST-007: OpenAPI
# =============================================================================


def schema_ref(operation: dict, status: str = "200") -> str | None:
    """The component an operation's JSON answer ``status`` points to."""
    content = operation.get("responses", {}).get(status, {}).get("content", {}).get("application/json", {})
    schema = content.get("schema", {})
    return schema.get("$ref", "").rsplit("/", 1)[-1] or None


def test_the_job_view_has_no_origin_and_the_panel_routes_answer_it():
    """LIST-007a (GUARD, green before and after): ``InstanceBackupJob`` has no ``origin`` property, and the panel's start and
    poll, and the administrators' start and poll, all answer it."""
    document = backup_app().openapi()
    job_schema = document["components"]["schemas"]["InstanceBackupJob"]
    refs = {
        "POST panel": schema_ref(document["paths"]["/api/v1/backup/panel/jobs"]["post"], "202"),
        "GET panel job": schema_ref(document["paths"]["/api/v1/backup/panel/jobs/{job_id}"]["get"]),
        "POST instance": schema_ref(document["paths"]["/api/v1/backup/instance"]["post"], "202"),
        "GET instance job": schema_ref(document["paths"]["/api/v1/backup/instance/jobs/{job_id}"]["get"]),
    }
    assert "origin" not in job_schema["properties"], f"InstanceBackupJob gets no origin (the panel's answers do not change): {sorted(job_schema['properties'])}"
    assert refs == dict.fromkeys(refs, "InstanceBackupJob"), f"these four routes keep answering InstanceBackupJob: {refs}"


def test_the_list_answers_entries_that_are_a_job_plus_its_origin():
    """LIST-007b: ``GET /backup/instance/jobs`` answers ``InstanceBackupList``, whose ``items`` are ``InstanceBackupEntry``:
    every property of ``InstanceBackupJob`` plus ``origin`` (one of ui, cli, pre-restore, panel). Red today: the route and
    both schemas do not exist."""
    document = backup_app().openapi()
    operation = document["paths"].get("/api/v1/backup/instance/jobs", {}).get("get")
    assert operation is not None, f"the route GET /backup/instance/jobs is documented: {sorted(p for p in document['paths'] if p.startswith('/api/v1/backup/instance'))}"
    schemas = document["components"]["schemas"]
    assert schema_ref(operation) == "InstanceBackupList", f"the list answers InstanceBackupList: {schema_ref(operation)}"
    item_ref = schemas["InstanceBackupList"]["properties"]["items"]["items"].get("$ref", "").rsplit("/", 1)[-1]
    assert item_ref == "InstanceBackupEntry", f"its items are InstanceBackupEntry: {item_ref!r}"
    entry, job = schemas["InstanceBackupEntry"]["properties"], schemas["InstanceBackupJob"]["properties"]
    assert set(entry) == set(job) | ENTRY_ONLY, f"an entry is a job plus origin and its content: extra {sorted(set(entry) - set(job))}, missing {sorted(set(job) - set(entry))}"
    origin = entry["origin"]
    values = set(origin.get("enum") or [c.get("const") for c in origin.get("anyOf", []) + origin.get("oneOf", [])])
    assert values == ORIGINS, f"origin is one of {sorted(ORIGINS)}: {origin}"
    assert operation.get("security") is None or "BackupPanelToken" not in repr(operation["security"]), "the list asks for a session, not the panel's token"

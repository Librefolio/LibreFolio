"""
Instance backup, starting a run from the API (workstream B, lot B1): what ``POST /backup/instance`` answers when the run
cannot start.

Under test: ``backend/app/api/v1/backup/instance.py``, ``start_instance_backup``.

(a) A folder of ``backups/`` is a link or a file (``BackupPathError``, for ``backups`` or ``backups/.jobs``): 500 with
    ``detail.code`` ``backup_folder_unusable``. A full disk or a quota (``ENOSPC``, ``EDQUOT``, the failure itself or a
    cause of it: ``jobs.out_of_space`` walks the chain): 507 ``backup_no_space``, «Not enough free space to start the
    backup», and one WARNING with the run's origin, as the same disk a second later ends the run (B-30). Any other
    ``OSError`` before the run (``backups/`` cannot be written, a read-only file system): 500 ``backup_failed``. Another
    run in progress (``BackupBusyError``): 409 ``backup_busy``, as before. The answer carries the code and the route's
    own message, never the path of the data directory nor the system's words: those go to the server log.
(b) A run that starts: 202 and its first state. It is the barrier of (a): the app of this test does reach the route, so
    an answer without the code cannot come from a route that was never called.
(c) OpenAPI: the start documents its 507 beside its 409 and its 500 (``START_RESPONSES``, B-30).

Pure: an app of this test holds ``instance_router`` under ``/api/v1/backup``; ``require_admin`` is overridden by an
administrator and ``jobs.start_backup`` is replaced for each case, so no data directory, database, server or network
is reached. The app runs in this process behind ``httpx.ASGITransport`` (as ``test_tools_api.py`` does) with
``raise_app_exceptions=False``: an exception the route does not turn into an answer comes back as the plain 500 a
client would get, and fails the assertion on the code instead of erroring.
"""

from __future__ import annotations

import errno
import os
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI
from structlog.testing import capture_logs

from backend.app.api.v1.backup.instance import instance_router
from backend.app.api.v1.settings import require_admin
from backend.app.services.platform.instance_backup import jobs
from backend.app.services.platform.instance_backup.paths import BackupPathError
from backend.test_scripts.test_utils import print_section, print_success

URL = "/api/v1/backup/instance"
VALID_ID = "0123456789abcdef0123456789abcdef"
#: The data directory the errors of this module name: no answer may carry it.
DATA_DIR = Path("/srv/librefolio-data-b1-errors")
#: The system's words for the errors of this module: they belong in the log, not in an answer.
SYSTEM_WORDS = (os.strerror(errno.EACCES), os.strerror(errno.EROFS))
#: ``EDQUOT`` (quota exceeded) where the platform has it.
EDQUOT = getattr(errno, "EDQUOT", None)
needs_edquot = pytest.mark.skipif(EDQUOT is None, reason="this platform has no EDQUOT")
#: B-30: the system's words of a full disk, of a quota and of the error a full disk can cause: never in an answer.
NO_SPACE_WORDS = tuple(os.strerror(code) for code in (errno.ENOSPC, EDQUOT, errno.EIO) if code is not None)
#: B-30: what a start on a full disk answers and logs.
NO_SPACE_MESSAGE = "Not enough free space to start the backup"
NO_SPACE_WARNING = "Instance backup could not start: not enough free space"


def administrator() -> SimpleNamespace:
    """``require_admin``'s answer for an administrator: the route reads nothing of it."""
    return SimpleNamespace(id=1, username="b1-admin", is_superuser=True)


async def post_start() -> httpx.Response:
    """``POST /backup/instance`` on an app of this test: the route alone, its administrator check passed."""
    app = FastAPI()
    app.include_router(instance_router, prefix="/api/v1/backup")
    app.dependency_overrides[require_admin] = administrator
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://in-process") as client:
        return await client.post(URL)


def replace_start(monkeypatch, outcome: Callable[[], jobs.BackupJob]) -> list[str]:
    """``jobs.start_backup`` gives ``outcome()`` (or raises what it raises); returns the origins it was called with."""
    calls: list[str] = []

    def start_backup(*, origin: str = "ui", data_dir: Path | None = None, password: str | None = None) -> jobs.BackupJob:
        calls.append(origin)
        return outcome()

    monkeypatch.setattr(jobs, "start_backup", start_backup)
    return calls


def raising(error: BaseException) -> Callable[[], jobs.BackupJob]:
    def outcome() -> jobs.BackupJob:
        raise error

    return outcome


def detail_code(response: httpx.Response) -> str | None:
    """``detail.code`` of a JSON error answer; ``None`` for anything else (a plain 500 is text)."""
    if not response.headers.get("content-type", "").startswith("application/json"):
        return None
    detail = response.json().get("detail")
    return detail.get("code") if isinstance(detail, dict) else None


@pytest.mark.asyncio
async def test_a_run_that_starts_answers_202_with_its_first_state(monkeypatch):
    """(b) The barrier: the route is reached and answers the job ``start_backup`` returned."""
    print_section("POST /backup/instance")
    first = jobs.BackupJob(job_id=VALID_ID, origin="ui", status="running", phase="preparing", done_bytes=0, total_bytes=0, created_at=datetime(2026, 10, 15, 10, 15, tzinfo=UTC))
    calls = replace_start(monkeypatch, lambda: first)
    response = await post_start()
    assert response.status_code == 202, f"a run that starts is 202, not {response.status_code}: {response.text}"
    body = response.json()
    assert (body["job_id"], body["status"], body["phase"], body["error_code"]) == (VALID_ID, "running", "preparing", None), f"the answer is the first state of the run: {body}"
    assert calls == ["ui"], f"the route starts one run, from the UI: {calls}"
    print_success("202, running/preparing")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "status_code", "code"),
    [
        pytest.param(lambda: BackupPathError(DATA_DIR / "backups"), 500, "backup_folder_unusable", id="backups-is-a-link-or-a-file"),
        pytest.param(lambda: BackupPathError(DATA_DIR / "backups" / ".jobs"), 500, "backup_folder_unusable", id="jobs-is-a-link-or-a-file"),
        pytest.param(lambda: PermissionError(errno.EACCES, os.strerror(errno.EACCES), str(DATA_DIR / "backups" / ".jobs")), 500, "backup_failed", id="backups-cannot-be-written"),
        pytest.param(lambda: OSError(errno.EROFS, os.strerror(errno.EROFS), str(DATA_DIR / "backups")), 500, "backup_failed", id="read-only-file-system"),
        pytest.param(lambda: jobs.BackupBusyError("Another backup is running"), 409, "backup_busy", id="another-run-in-progress"),
    ],
)
async def test_a_run_that_cannot_start_answers_its_code_and_nothing_of_the_server(monkeypatch, error, status_code, code):
    """(a) Each reason has its code; the path and the system's words stay in the server's log."""
    calls = replace_start(monkeypatch, raising(error()))
    response = await post_start()
    assert calls == ["ui"], f"precondition: the route asked for a run: {calls}"
    assert (response.status_code, detail_code(response)) == (status_code, code), f"expected {status_code} with detail.code {code!r}, got {response.status_code}: {response.text}"
    leaked = [word for word in (str(DATA_DIR), *SYSTEM_WORDS) if word in response.text]
    assert leaked == [], f"the answer must not carry the server's path or the system's words: {leaked} in {response.text}"
    print_success(f"{status_code} {code}")


def caused_by_a_full_disk() -> OSError:
    """Another error of the file system whose cause is a full disk, as a failure wrapped on its way up leaves it."""
    error = OSError(errno.EIO, os.strerror(errno.EIO), str(DATA_DIR / "backups" / ".jobs"))
    error.__cause__ = OSError(errno.ENOSPC, os.strerror(errno.ENOSPC))
    return error


#: B-30: a start on a full disk or a quota, the failure itself or the cause of another.
NO_SPACE_STARTS = [
    pytest.param(lambda: OSError(errno.ENOSPC, os.strerror(errno.ENOSPC), str(DATA_DIR / "backups" / ".jobs")), id="ENOSPC"),
    pytest.param(lambda: OSError(EDQUOT, os.strerror(EDQUOT), str(DATA_DIR / "backups")), id="EDQUOT", marks=needs_edquot),
    pytest.param(caused_by_a_full_disk, id="EIO-caused-by-ENOSPC"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("error", NO_SPACE_STARTS)
async def test_a_run_that_cannot_start_for_lack_of_space_answers_507_and_warns_once(monkeypatch, error):
    """(a) B-30 (5): ``start_backup`` meets a full disk or a quota (``jobs.out_of_space``: the failure or a cause of it):
    507 ``backup_no_space``, «Not enough free space to start the backup», never 500 ``backup_failed``; one WARNING,
    «Instance backup could not start: not enough free space», with the origin ``ui``; neither the path nor the system's
    words in the answer."""
    calls = replace_start(monkeypatch, raising(error()))
    with capture_logs() as events:
        response = await post_start()
    assert calls == ["ui"], f"precondition: the route asked for a run: {calls}"
    body = response.json() if response.headers.get("content-type", "").startswith("application/json") else None
    detail = body.get("detail") if isinstance(body, dict) else None
    answer = (response.status_code, *((detail.get("code"), detail.get("message")) if isinstance(detail, dict) else (None, None)))
    assert answer == (507, "backup_no_space", NO_SPACE_MESSAGE), f"expected 507 backup_no_space, got {response.status_code}: {response.text}"
    loud = [(event.get("log_level"), event.get("event"), event.get("origin")) for event in events if event.get("log_level") in ("warning", "error", "critical")]
    assert loud == [("warning", NO_SPACE_WARNING, "ui")], f"one warning, with the origin: {loud}"
    leaked = [word for word in (str(DATA_DIR), *NO_SPACE_WORDS) if word in response.text]
    assert leaked == [], f"the answer must not carry the server's path or the system's words: {leaked} in {response.text}"
    print_success("507 backup_no_space, one warning")


def test_openapi_documents_507_on_the_start():
    """(c) B-30: ``POST /backup/instance`` documents its 507 beside its 409 and its 500 (``START_RESPONSES``)."""
    app = FastAPI()
    app.include_router(instance_router, prefix="/api/v1/backup")
    documented = set(app.openapi()["paths"][URL]["post"]["responses"])
    assert {"409", "500", "507"} <= documented, f"the start's refusals, 507 included: {sorted(documented)}"

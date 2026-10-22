"""
The hosting panel's backup token (workstream B, lot B8): the four routes of ``/api/v1/backup/panel/jobs``.

Under test: ``backend/app/config/backup.py`` (``backup_download_token``), ``backend/app/api/v1/backup/panel.py``
(``require_panel_token`` and its four routes) and ``backend/app/api/v1/backup/job_views.py``, which the panel shares with
the administrators' routes of ``instance.py``.

- PANEL-001..006, ``backup_download_token()``: ``LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN`` as written, or else the text of the
  file its ``_FILE`` names, without a leading BOM and its trailing line breaks; the variable wins over the file, and a
  blank one leaves the file in charge; neither set, or both blank, is None. Under 32 characters it raises
  ``BackupConfigError`` (``BACKUP_DOWNLOAD_TOKEN_TOO_SHORT``, the variable named, never the value); 32 is enough. A file
  that cannot give the token (missing, unreadable, empty, blank) raises ``SecretFileError``, naming the ``_FILE``.
- PANEL-007..009, the characters: a token holds visible ASCII characters only, ``!`` (0x21) to ``~`` (0x7E). A space or
  a tab around it or inside it, a character outside ASCII (``é``, ``€``, a no-break space), DEL or another control
  character raises ``BackupConfigError`` ``BACKUP_DOWNLOAD_TOKEN_NOT_VISIBLE_ASCII`` (the variable named, never the
  value), from the variable as from the file, where the spaces before the line break stay; the characters are checked
  before the length. 32 characters from ``!`` to ``~``, and every visible ASCII character, are taken as written.
- PANEL-010, the routes off: without a token each route answers 404 ``{"detail": "Not Found"}``, the answer of a path
  that does not exist, whatever the request carries, a token that used to be right included; the jobs are never reached.
- PANEL-011, a token the server cannot use (too short, from the variable or from its file; its file missing, unreadable,
  empty or blank): each route answers 503 ``backup_panel_unavailable`` with or without a token presented, the short value
  itself included, never the file's path; each request logs one error naming the variable, never its value; the jobs
  are never reached.
- PANEL-012, the token missing or wrong (no ``Authorization``, the token under ``Basic``, ``Bearer`` with nothing,
  another token, a prefix, an extension or the capitals of the token, the token in the query string): each route
  answers 401 ``backup_panel_unauthorized`` with ``WWW-Authenticate: Bearer``; the jobs are never reached.
- PANEL-013..017, with the token, the panel's own jobs and nothing else. The start asks for a run of origin ``panel``,
  without a password (B4: the panel never encrypts) (202, its first state). The poll, the download and the deletion read
  the job first, and a job of another origin (``ui``, ``cli``, ``pre-restore``) answers exactly as a job that does not
  exist, 404 ``backup_job_not_found``: its archive is never read, the job never deleted. The calls: start →
  start_backup("panel"); poll → get_job; download → get_job, job_archive; delete → get_job, delete_job. The download is
  the archive's exact bytes, ``application/zip``, an attachment under its name, ``Cache-Control: no-store``. A running job
  of the panel: 409 ``backup_job_not_ready`` and ``backup_job_running``. The token read from its file opens the routes as
  the variable does, and the variable wins.
- PANEL-018, a start that cannot run answers the administrators' codes (``job_views.start_job``): 409 ``backup_busy``,
  500 ``backup_folder_unusable``, 500 ``backup_failed``, never a path or the system's words.
- PANEL-019, an administrator (``instance.py``, no origin) sees every job, the panel's included, with the calls of
  before B8: start → start_backup("ui"); poll → get_job; download → job_archive; delete → delete_job.
- PANEL-020, OpenAPI: the four routes of the panel ask for the ``BackupPanelToken`` bearer scheme, and no other route.
- PANEL-021, a token with spaces around it, in the variable: no request can present it as written, since a header loses
  the spaces around its credentials. Each route answers 503 ``backup_panel_unavailable``, without a header and to that
  very token, and each request logs one error naming the variable, never the value; the jobs are never reached. The same
  token without its spaces opens the routes.
- PANEL-022 (B-30), a full disk at the panel's start: ``start_backup`` raising ``ENOSPC`` through ``job_views.start_job``,
  with the token: 507 ``backup_no_space``, one WARNING with the origin ``panel``, never a path or the system's words;
  OpenAPI documents the start's 507 (``START_RESPONSES``).
- PANEL-023 (B-8), a start refused while the panel's own job runs (``BackupBusyError.running``, a job of origin
  ``panel``): 409 ``backup_busy`` whose detail names that job, exactly ``{code, message, job_id, origin: panel}``, the
  message as before; the id is one the panel follows (its poll answers that job, running).
- PANEL-024 (B-8), a guard become contract: a start refused while a job the panel cannot see runs (``ui``, ``cli``,
  ``pre-restore``), or with no job read: the detail stays exactly ``{code, message}``, no ``job_id`` nor ``origin``. A
  job of another origin is as invisible in a refusal as at its poll (PANEL-015). The refusal is built as PANEL-018's,
  its ``running`` set on it: the test does not depend on how the constructor takes it.
- PANEL-025..027 (lot L3), what a job's view tells of its archive. ``InstanceBackupJob`` gains ``file_sha256`` (64
  lowercase hex digits, the SHA-256 of the very bytes the download serves; null while the job runs) and
  ``instance_key_included`` (false unless the archive carries the instance key). PANEL-025: the panel's poll of its done
  job gives the SHA-256 of the bytes its download returns, and ``instance_key_included`` false (the panel never
  encrypts, so never carries the key); a running job answers ``file_sha256`` null. PANEL-026: the same through the
  administrators' routes (PANEL-019's), for a job of the panel. PANEL-027: a secure job of the Backup tab whose archive
  carries the key (``jobs.BackupJob.instance_key_included`` true) reads ``instance_key_included`` true to an
  administrator; before L3 the dataclass has no such field, and the test says so.
- PANEL-028..034 (lot L3-2, interface §5; contract L3 §2, §4), the sealed backup of the panel. The start reads
  ``LIBREFOLIO_BACKUP_RECIPIENTS`` at each request: one ``age1…`` (an X25519 recipient made here by ``pyrage``), or two
  (spaces around each ignored, the order kept), and the start asks for a run of origin ``panel`` with
  ``recipients=(…)`` and no password. A value it cannot use (garbage, an ``AGE-SECRET-KEY-1…`` private key, an empty
  item, three recipients, one twice): 503 ``backup_panel_unavailable``, one error line naming the variable and never the
  value, the jobs never reached. Unset in the ``managed`` profile: 503 ``backup_panel_unavailable``, one error line, the
  jobs never reached (barrier: set, the same profile starts a sealed run). Unset ``selfhosted``: the start of before,
  no recipients. A sealed done job reads ``sealed`` true and ``sealed_recipients``; one not sealed, false and ``[]``;
  a running job's ``phase`` may be ``sealing``. The download of a ``.tar`` is ``application/x-tar``.
- PANEL-035..038 (lot L3-2 addendum, contract L3 §6), the «awaiting restore» mode of workstream H (H-62), read through
  ``backend.app.config.platform.await_restore()``, which H adds later: the start looks it up at each request
  (``getattr``, absent: never awaiting). Awaiting: the start answers 409 ``backup_awaiting_restore``, detail exactly
  ``{code, message}``, and ``start_backup`` is never called — recipients unset, set, unusable (the mode wins over the
  503 of a value it cannot use) or unset in ``managed``: a backup of an empty instance is never made, whatever the
  config. Not awaiting (``False``, or no such function): the start of before, 202. The poll, the download and the
  deletion are not touched by the mode. OpenAPI documents the start's 409 ``backup_awaiting_restore``. Written RED:
  the route does not read the mode yet; the rows without it (absent, ``False``) and the routes the mode leaves alone
  are guards, green today.
- Every request of this module: the token, and whatever the caller presented, never appears in the answer, its body or
  its headers, nor in the log.

Pure: an app of each test holds ``backup_router`` under ``/api/v1``, as ``router.py`` mounts it, and nothing else: the
panel's routes need no session and no database, and ``require_admin`` is overridden where the administrators' routes are
called. In every test ``jobs.start_backup``, ``get_job``, ``job_archive`` and ``delete_job`` are replaced by a fake that
records its calls and holds jobs of the test, their archives under ``tmp_path``: no data directory, database, server or
network is reached, and no backup runs. Both token variables are deleted before each test, then set through
``monkeypatch``: nothing is inherited from the runner's environment. The log of each request is captured with
``structlog.testing.capture_logs``, as ``test_post_migration.py`` and ``test_email_checks.py`` capture ``get_logger``;
the 503 cases are its barrier, each request's error event must be there. The app runs behind ``httpx.ASGITransport``
with ``raise_app_exceptions=False``, so an exception a route does not turn into an answer comes back as a client's plain
500 and fails an assertion instead of erroring.
"""

from __future__ import annotations

import errno
import hashlib
import os
import re
import secrets
import shutil
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass, field, fields, replace
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI
from pyrage import x25519
from structlog.testing import capture_logs

from backend.app import config
from backend.app.api.v1.backup import backup_router, job_views
from backend.app.api.v1.settings import require_admin
from backend.app.config import SecretFileError
from backend.app.config import platform as platform_module
from backend.app.config.backup import PANEL_TOKEN_MIN_LENGTH, PANEL_TOKEN_VARIABLE, BackupConfigError, backup_download_token
from backend.app.services.platform.instance_backup import jobs
from backend.app.services.platform.instance_backup.paths import BackupPathError
from backend.test_scripts.test_utils import print_section, print_success

#: The variables of the token, as .env.example and the deployments write them: spelled out here, so a rename shows.
TOKEN_VARIABLE = "LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN"
TOKEN_FILE_VARIABLE = "LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN_FILE"
#: The shortest token the server takes.
MIN_LENGTH = 32
#: Lot L3-2 (contract L3 §2): the age recipients a panel job is sealed for, and the instance's profile.
RECIPIENTS_VARIABLE = "LIBREFOLIO_BACKUP_RECIPIENTS"
PROFILE_VARIABLE = "LIBREFOLIO_PROFILE"

PANEL = "/api/v1/backup/panel/jobs"
INSTANCE = "/api/v1/backup/instance"

#: The routes off: the answer of a path that does not exist, whole.
OFF_ANSWER = (404, {"detail": "Not Found"})
#: The token missing or wrong, whole.
UNAUTHORIZED_ANSWER = (401, {"detail": {"code": "backup_panel_unauthorized", "message": "A valid panel token is required"}})
#: A token the server cannot use: status and code.
UNAVAILABLE = (503, "backup_panel_unavailable")
#: A job the caller may not see, or that does not exist: status and code.
JOB_NOT_FOUND = (404, "backup_job_not_found")

#: The data directory the start errors of this module name, and the system's words for them: no answer may carry them.
DATA_DIR = Path("/srv/librefolio-data-b8-panel")
SYSTEM_WORDS = (os.strerror(errno.EACCES), os.strerror(errno.EROFS))

#: When the fake's jobs start and end: the name of an archive follows (``jobs.archive_name``).
CREATED_AT = datetime(2026, 10, 15, 10, 15, tzinfo=UTC)
FINISHED_AT = datetime(2026, 10, 15, 10, 16, tzinfo=UTC)

#: Files that cannot give a token, by what is wrong with them: each builder leaves such a thing at ``path``.
BROKEN_FILES: dict[str, Callable[[Path], object]] = {
    "file-missing": lambda path: None,
    "file-unreadable": lambda path: path.mkdir(),
    "file-empty": lambda path: path.write_bytes(b""),
    "file-blank": lambda path: path.write_bytes(b" \n\r\n"),
}


def a_token() -> str:
    """A token as the documentation suggests one (``openssl rand -hex 32``): 64 characters, new at each call."""
    return secrets.token_hex(32)


# =============================================================================
# The service replaced, the environment cleared, the app of a test
# =============================================================================


@dataclass
class FakeJobs:
    """``jobs.start_backup``, ``get_job``, ``job_archive`` and ``delete_job``, the service the routes call, replaced in this
    process. It holds jobs of the test, each finished one with a small archive of its own under ``folder``, and records
    every call as ``(name, origin)`` for a start and ``(name, job id)`` for the others; the password each start received
    (B4) is recorded apart, in ``start_passwords``, so the calls read as they did before. It answers as the service does:
    an unknown id raises ``BackupJobNotFoundError``; the archive of a job not done, and the deletion of a running one,
    ``BackupJobStateError``."""

    folder: Path
    calls: list[tuple[str, str]] = field(default_factory=list)
    #: The ``password`` of each ``start_backup``, in order: None for a backup in the clear.
    start_passwords: list[str | None] = field(default_factory=list)
    #: The ``recipients`` of each ``start_backup`` (lot L3-2), in order: None for a backup that is not sealed.
    start_recipients: list[tuple[str, ...] | None] = field(default_factory=list)
    known: dict[str, jobs.BackupJob] = field(default_factory=dict)
    #: What ``start_backup`` raises instead of starting a run; None: it starts one.
    start_error: BaseException | None = None

    def running(self, origin: str) -> jobs.BackupJob:
        """A job of ``origin`` as a start leaves it: running, preparing."""
        job = jobs.BackupJob(job_id=uuid4().hex, origin=origin, status="running", phase="preparing", done_bytes=0, total_bytes=0, created_at=CREATED_AT)
        self.known[job.job_id] = job
        return job

    def finish(self, job_id: str) -> jobs.BackupJob:
        """The job ``job_id`` done, with its archive: bytes of its own, every byte value included; its ``file_sha256`` the
        SHA-256 of those bytes, as a run records it."""
        job = self.known[job_id]
        archive = self.folder / job_id / jobs.archive_name(job.created_at)
        archive.parent.mkdir(parents=True)
        archive.write_bytes(job_id.encode() + bytes(range(256)))
        size = archive.stat().st_size
        sha256 = hashlib.sha256(archive.read_bytes()).hexdigest()
        done = replace(job, status="done", phase=None, done_bytes=size, total_bytes=size, finished_at=FINISHED_AT, file_name=archive.name, file_size=size, file_sha256=sha256)
        self.known[job_id] = done
        return done

    def done(self, origin: str) -> jobs.BackupJob:
        """A finished job of ``origin``, with its archive."""
        return self.finish(self.running(origin).job_id)

    def archive(self, job: jobs.BackupJob) -> Path:
        """Where the archive of a finished job is."""
        assert job.file_name is not None, f"Precondition: the job {job.job_id} has an archive"
        return self.folder / job.job_id / job.file_name

    # --- the service, as the routes call it ------------------------------------------------------------------------

    def start_backup(self, *, origin: str = "ui", data_dir: Path | None = None, password: str | None = None, recipients: tuple[str, ...] | None = None) -> jobs.BackupJob:
        self.calls.append(("start_backup", origin))
        self.start_passwords.append(password)
        self.start_recipients.append(None if recipients is None else tuple(recipients))
        if self.start_error is not None:
            raise self.start_error
        return self.running(origin)

    def get_job(self, job_id: str, *, data_dir: Path | None = None) -> jobs.BackupJob:
        self.calls.append(("get_job", job_id))
        return self._job(job_id)

    def job_archive(self, job_id: str, *, data_dir: Path | None = None) -> tuple[Path, str]:
        self.calls.append(("job_archive", job_id))
        job = self._job(job_id)
        if job.status != "done" or job.file_name is None:
            raise jobs.BackupJobStateError(job.status)
        return self.archive(job), job.file_name

    def delete_job(self, job_id: str, *, data_dir: Path | None = None) -> None:
        self.calls.append(("delete_job", job_id))
        job = self._job(job_id)
        if job.status == "running":
            raise jobs.BackupJobStateError(job.status)
        del self.known[job_id]
        shutil.rmtree(self.folder / job_id, ignore_errors=True)

    def _job(self, job_id: str) -> jobs.BackupJob:
        if job_id not in self.known:
            raise jobs.BackupJobNotFoundError("No such backup job")
        return self.known[job_id]


@pytest.fixture(autouse=True)
def service(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> FakeJobs:
    """Every test of this module, the unit tests included: the service replaced, so no request can start a real backup."""
    assert job_views.jobs is jobs, "Precondition: the routes call the very module replaced here, so no real backup can run"
    fake = FakeJobs(tmp_path / "jobs")
    for name in ("start_backup", "get_job", "job_archive", "delete_job"):
        monkeypatch.setattr(jobs, name, getattr(fake, name))
    return fake


@pytest.fixture(autouse=True)
def no_inherited_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test starts with neither variable of the token, no backup recipients (lot L3-2) and the ``selfhosted``
    profile: nothing comes from the runner's environment."""
    monkeypatch.delenv(TOKEN_VARIABLE, raising=False)
    monkeypatch.delenv(TOKEN_FILE_VARIABLE, raising=False)
    monkeypatch.delenv(RECIPIENTS_VARIABLE, raising=False)
    monkeypatch.setenv(PROFILE_VARIABLE, "selfhosted")


def backup_app(*, administrator: bool = False) -> FastAPI:
    """``backup_router`` under ``/api/v1``, as ``router.py`` mounts it, in an app of the test and nothing else. With
    ``administrator``, ``require_admin`` lets the administrators' routes through without a session or a database."""
    app = FastAPI()
    app.include_router(backup_router, prefix="/api/v1")
    if administrator:
        app.dependency_overrides[require_admin] = lambda: SimpleNamespace(id=1, username="b8-admin", is_superuser=True)
    return app


@pytest.fixture
def app() -> FastAPI:
    return backup_app()


@dataclass(frozen=True)
class Exchange:
    """One request to an app of the test: the answer, and the events the server logged while it ran."""

    response: httpx.Response
    events: list[dict[str, Any]]

    @property
    def answer(self) -> tuple[int, object]:
        """Status and body: the JSON of a JSON answer, the first bytes of any other (an archive), so a red always reads."""
        if self.response.headers.get("content-type", "").startswith("application/json"):
            return self.response.status_code, self.response.json()
        return self.response.status_code, self.response.content[:64]

    @property
    def code(self) -> tuple[int, str | None]:
        """Status and ``detail.code``; None for an answer without one."""
        status, body = self.answer
        detail = body.get("detail") if isinstance(body, dict) else None
        return status, detail.get("code") if isinstance(detail, dict) else None

    @property
    def errors(self) -> list[dict[str, Any]]:
        """The events logged at error level."""
        return [event for event in self.events if event.get("log_level") == "error"]

    def shows(self, values: Iterable[str]) -> list[str]:
        """Where a value of ``values`` shows: the body, the headers (names and values), the log. Empty values are skipped,
        and a value is named by its position, never written out."""
        headers = "\n".join(f"{name}: {value}" for name, value in self.response.headers.multi_items())
        places = []
        for index, value in enumerate(values):
            if not value:
                continue
            found = {"body": value.encode() in self.response.content, "headers": value in headers, "log": value in repr(self.events)}
            places.extend(f"value #{index} in the {place}" for place, shown in found.items() if shown)
        return places


async def send(app: FastAPI, method: str, path: str, *, authorization: str | None = None, params: dict[str, str] | None = None, never: Iterable[str] = ()) -> Exchange:
    """``method path`` on ``app``, in this process, with ``Authorization`` only when given; the log captured meanwhile.

    Ends on what every request of this module must hold: no value of ``never`` (the token, what the caller presented)
    in the answer nor in the log; what the caller presented is checked without being listed.
    """
    headers = {} if authorization is None else {"Authorization": authorization}
    presented = [] if authorization is None else [authorization.partition(" ")[2].strip()]
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    with capture_logs() as events:
        async with httpx.AsyncClient(transport=transport, base_url="http://in-process") as client:
            response = await client.request(method, path, headers=headers, params=params)
    exchange = Exchange(response, list(events))
    leaked = exchange.shows([*never, *presented, *(params or {}).values()])
    assert not leaked, f"{method} {path}: a secret left the server: {leaked}"
    return exchange


async def with_calls(service: FakeJobs, request: Awaitable[Exchange]) -> tuple[Exchange, list[tuple[str, str]]]:
    """The exchange of ``request``, and the calls the service received while it ran."""
    mark = len(service.calls)
    exchange = await request
    return exchange, service.calls[mark:]


def panel_routes(job_id: str) -> list[tuple[str, str]]:
    """The four routes of the panel for one job: start, poll, download, delete."""
    return [("POST", PANEL), ("GET", f"{PANEL}/{job_id}"), ("GET", f"{PANEL}/{job_id}/file"), ("DELETE", f"{PANEL}/{job_id}")]


def job_routes(job_id: str) -> list[tuple[str, str]]:
    """The three routes of the panel that read one job: poll, download, delete."""
    return panel_routes(job_id)[1:]


def write_token_file(tmp_path: Path, text: str) -> Path:
    """A file holding ``text``, as a Docker secret mounts one."""
    path = tmp_path / "panel-token"
    path.write_bytes(text.encode("utf-8"))
    return path


# =============================================================================
# PANEL-001..006: backup_download_token()
# =============================================================================


@pytest.mark.parametrize(
    "variables",
    [
        pytest.param({}, id="neither-variable"),
        pytest.param({TOKEN_VARIABLE: ""}, id="empty-variable"),
        pytest.param({TOKEN_VARIABLE: " \t "}, id="blank-variable"),
        pytest.param({TOKEN_FILE_VARIABLE: ""}, id="empty-file-variable"),
        pytest.param({TOKEN_FILE_VARIABLE: "   "}, id="blank-file-variable"),
        pytest.param({TOKEN_VARIABLE: " ", TOKEN_FILE_VARIABLE: " "}, id="both-blank"),
    ],
)
def test_no_token_when_neither_variable_gives_one(monkeypatch, variables):
    """PANEL-001: neither variable set, or blank, is no token at all: None, the panel routes are off."""
    print_section("Backup panel token: backup_download_token()")
    for name, value in variables.items():
        monkeypatch.setenv(name, value)
    assert backup_download_token() is None, f"{sorted(variables)} set to blank values must count as unset"
    print_success(f"{variables or 'nothing set'}: None")


def test_the_variable_is_the_token_as_written(monkeypatch):
    """PANEL-002: the variable, when not blank, is the token as written."""
    token = a_token()
    monkeypatch.setenv(TOKEN_VARIABLE, token)
    assert backup_download_token() == token, f"{TOKEN_VARIABLE} must be the token as written"


@pytest.mark.parametrize(
    ("before", "after"),
    [
        pytest.param("", "\n", id="line-break"),
        pytest.param("", "\r\n", id="crlf"),
        pytest.param("", "\n\n", id="two-line-breaks"),
        pytest.param("\ufeff", "\n", id="bom-and-line-break"),
        pytest.param("", "", id="no-line-break"),
    ],
)
def test_the_file_gives_the_token_without_its_bom_and_trailing_line_breaks(monkeypatch, tmp_path, before, after):
    """PANEL-003: the file named by ``_FILE`` holds the token; a leading BOM and the trailing line breaks are not part of it."""
    token = a_token()
    monkeypatch.setenv(TOKEN_FILE_VARIABLE, str(write_token_file(tmp_path, before + token + after)))
    assert backup_download_token() == token, f"the token of a file holding {before!r} + token + {after!r}"


def test_the_variable_wins_over_the_file_and_a_blank_one_leaves_it_the_file(monkeypatch, tmp_path):
    """PANEL-004: both set, the variable is the token; blank, it counts as unset and the file is the token."""
    from_variable, from_file = a_token(), a_token()
    monkeypatch.setenv(TOKEN_FILE_VARIABLE, str(write_token_file(tmp_path, from_file + "\n")))
    monkeypatch.setenv(TOKEN_VARIABLE, from_variable)
    both = backup_download_token()
    monkeypatch.setenv(TOKEN_VARIABLE, "  ")
    blank_variable = backup_download_token()

    assert both == from_variable, "both set: the variable wins over the file"
    assert blank_variable == from_file, "a blank variable counts as unset: the file gives the token"


def set_token(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, source: str, value: str) -> None:
    """``value`` as the token, from the variable or (followed by a line break) from the file of ``_FILE``."""
    if source == "variable":
        monkeypatch.setenv(TOKEN_VARIABLE, value)
    else:
        monkeypatch.setenv(TOKEN_FILE_VARIABLE, str(write_token_file(tmp_path, value + "\n")))


@pytest.mark.parametrize("source", ["variable", "file"])
def test_31_characters_are_refused_without_the_value_and_32_are_a_token(monkeypatch, tmp_path, source):
    """PANEL-005: under 32 characters ``BackupConfigError`` (code ``BACKUP_DOWNLOAD_TOKEN_TOO_SHORT``, ``variable`` the
    variable), its message naming the variable and the rule, never the value; 32 characters are a token. From the file,
    the line break that follows the value is not counted."""
    assert (PANEL_TOKEN_VARIABLE, PANEL_TOKEN_MIN_LENGTH) == (TOKEN_VARIABLE, MIN_LENGTH), "Precondition: the rule applied is the rule documented"
    too_short, long_enough = a_token()[: MIN_LENGTH - 1], a_token()[:MIN_LENGTH]
    set_token(monkeypatch, tmp_path, source, too_short)
    with pytest.raises(BackupConfigError) as refused:
        backup_download_token()
    set_token(monkeypatch, tmp_path, source, long_enough)
    taken = backup_download_token()

    error = refused.value
    assert (error.code, error.variable) == ("BACKUP_DOWNLOAD_TOKEN_TOO_SHORT", TOKEN_VARIABLE), f"the error's code and variable: {(error.code, error.variable)}"
    assert TOKEN_VARIABLE in str(error) and str(MIN_LENGTH) in str(error), f"the message names the variable and the rule: {error}"
    assert too_short not in f"{error} {error!r} {error.args}", "the message must never carry the value"
    assert taken == long_enough, f"{MIN_LENGTH} characters are a token"
    print_success(f"{source}: {MIN_LENGTH - 1} characters refused (code, variable, no value), {MIN_LENGTH} taken")


@pytest.mark.parametrize("problem", sorted(BROKEN_FILES))
def test_a_file_that_cannot_give_the_token_raises_secret_file_error(monkeypatch, tmp_path, problem):
    """PANEL-006: a ``_FILE`` that is missing, a folder, empty or blank cannot give the token: ``SecretFileError``,
    naming the ``_FILE`` variable."""
    path = tmp_path / "panel-token"
    BROKEN_FILES[problem](path)
    monkeypatch.setenv(TOKEN_FILE_VARIABLE, str(path))
    with pytest.raises(SecretFileError) as raised:
        backup_download_token()
    assert TOKEN_FILE_VARIABLE in str(raised.value), f"the error names the variable: {raised.value}"


# =============================================================================
# PANEL-007..009: the characters of a token
# =============================================================================

#: The characters a token may hold, in order: the visible ASCII ones, from "!" (0x21) to "~" (0x7E).
VISIBLE_ASCII = "".join(chr(code) for code in range(0x21, 0x7F))

#: A character no token may hold, put on an otherwise valid token of 40 characters (``spoil(token)``): before it, after
#: it, or between its two halves. From the variable; and from the file, whose line break after the token goes
#: (``env_secret``) while the spaces before it stay.
NOT_VISIBLE_ASCII = [
    pytest.param("variable", lambda token: f" {token}", id="leading-space"),
    pytest.param("variable", lambda token: f"{token} ", id="trailing-space"),
    pytest.param("variable", lambda token: f"{token}\t", id="trailing-tab"),
    pytest.param("variable", lambda token: f"{token[:20]} {token[20:]}", id="inner-space"),
    pytest.param("variable", lambda token: f"{token[:20]}\u00e9{token[20:]}", id="e-acute-u00e9"),
    pytest.param("variable", lambda token: f"{token[:20]}\u20ac{token[20:]}", id="euro-sign-u20ac"),
    pytest.param("variable", lambda token: f"{token[:20]}\u00a0{token[20:]}", id="no-break-space-u00a0"),
    pytest.param("variable", lambda token: f"{token[:20]}\x7f{token[20:]}", id="del-0x7f"),
    pytest.param("variable", lambda token: f"{token[:20]}\x01{token[20:]}", id="control-0x01"),
    pytest.param("file", lambda token: f"{token}  ", id="file-spaces-before-the-line-break"),
]


@pytest.mark.parametrize(("source", "spoil"), NOT_VISIBLE_ASCII)
def test_a_token_holding_anything_but_visible_ascii_is_refused_without_the_value(monkeypatch, tmp_path, source, spoil):
    """PANEL-007: a token holds visible ASCII characters only. A space or a tab (around it or inside it), a character
    outside ASCII (é, €, a no-break space), DEL or another control character raises ``BackupConfigError`` with the code
    ``BACKUP_DOWNLOAD_TOKEN_NOT_VISIBLE_ASCII`` and ``variable`` the variable; its message names the variable and the
    rule, never the value nor a part of it. Each value is an otherwise valid token of 40 characters, so its length is
    never the reason; from the file, the line break after the token goes and the spaces before it stay."""
    print_section("Backup panel token: visible ASCII characters only")
    valid = a_token()[:40]
    value = spoil(valid)
    set_token(monkeypatch, tmp_path, source, value)
    with pytest.raises(BackupConfigError) as refused:
        backup_download_token()

    error = refused.value
    shown = [part for part in (value, valid[:20], valid[20:]) if part in f"{error} {error!r} {error.args}"]
    assert (error.code, error.variable) == ("BACKUP_DOWNLOAD_TOKEN_NOT_VISIBLE_ASCII", TOKEN_VARIABLE), f"the error's code and variable: {(error.code, error.variable)}"
    assert TOKEN_VARIABLE in str(error) and "visible ASCII" in str(error), f"the message names the variable and the rule: {error}"
    assert shown == [], f"the message must never carry the value, nor a part of it: {len(shown)} part(s) shown"
    print_success(f"{source}: refused, BACKUP_DOWNLOAD_TOKEN_NOT_VISIBLE_ASCII, the variable named, no value")


@pytest.mark.parametrize(
    "spoil",
    [
        pytest.param(lambda token: f"{token}\u00e9", id="short-and-non-ascii"),
        pytest.param(lambda token: f" {token}", id="short-with-a-leading-space"),
    ],
)
def test_the_characters_are_checked_before_the_length(monkeypatch, spoil):
    """PANEL-008: a value too short that also holds a character outside visible ASCII raises the code of the characters,
    ``BACKUP_DOWNLOAD_TOKEN_NOT_VISIBLE_ASCII``, checked first, never that of the length; never with the value."""
    short = a_token()[:10]
    value = spoil(short)
    assert len(value) < MIN_LENGTH, "Precondition: the value is too short as well"
    monkeypatch.setenv(TOKEN_VARIABLE, value)
    with pytest.raises(BackupConfigError) as refused:
        backup_download_token()

    error = refused.value
    assert error.code == "BACKUP_DOWNLOAD_TOKEN_NOT_VISIBLE_ASCII", f"the characters are checked before the length: {error.code}"
    assert short not in f"{error} {error!r} {error.args}", "the message must never carry the value"


#: Tokens at the edges of the rule, each taken as written: 32 characters, the shortest token, from "!" (0x21) to "~"
#: (0x7E), the first and the last visible ASCII characters, with the punctuation of base64 and of its URL-safe variant
#: between them (1 + 6 + 24 + 1); and a token of every visible ASCII character.
EDGE_TOKENS = [
    pytest.param("!" + "+/=-_." + "0123456789abcdefABCDEFGH" + "~", id="32-characters-from-0x21-to-0x7e"),
    pytest.param(VISIBLE_ASCII, id="every-visible-ascii-character"),
]


@pytest.mark.parametrize("source", ["variable", "file"])
@pytest.mark.parametrize("token", EDGE_TOKENS)
def test_tokens_at_the_edges_of_visible_ascii_are_taken_as_written(monkeypatch, tmp_path, token, source):
    """PANEL-009: the edges are inside the rule: ``!``, ``~``, the punctuation of a generated token (``+/=-_.``) and every
    visible ASCII character, in a token of 32 characters or more, are returned as written, from the variable and from
    the file."""
    assert len(token) >= MIN_LENGTH and set(token) <= set(VISIBLE_ASCII), "Precondition: a token of visible ASCII characters, long enough"
    set_token(monkeypatch, tmp_path, source, token)
    assert backup_download_token() == token, f"{source}: a token of visible ASCII characters is returned as written"


# =============================================================================
# PANEL-010..012: the routes off, a token that cannot be used, a request without the token
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "unset",
    [
        pytest.param({}, id="neither-variable"),
        pytest.param({TOKEN_VARIABLE: "   "}, id="blank-variable"),
        pytest.param({TOKEN_FILE_VARIABLE: " "}, id="blank-file-variable"),
    ],
)
async def test_without_a_token_the_routes_answer_as_a_path_that_does_not_exist(app, monkeypatch, service, unset):
    """PANEL-010: no token, each route answers 404 ``{"detail": "Not Found"}`` whatever the request carries, as a path that
    does not exist; the jobs are never reached. Barrier: with a token set, the same four paths answer the panel's 401."""
    print_section("Backup panel: the routes off")
    token = a_token()
    job = service.done("panel")
    with monkeypatch.context() as on:
        on.setenv(TOKEN_VARIABLE, token)
        mounted = {f"{method} {path}": (await send(app, method, path, never=[token])).answer for method, path in panel_routes(job.job_id)}
    for name, value in unset.items():
        monkeypatch.setenv(name, value)
    requests = [("no Authorization", None), ("Bearer, the token of before", f"Bearer {token}"), ("Bearer, another token", f"Bearer {a_token()}"), ("Basic", "Basic YjgtcGFuZWw6cGFzc3dvcmQ=")]

    nowhere = await send(app, "GET", f"{PANEL}/{job.job_id}/nowhere")
    answers = {f"{method} {path}, {label}": (await send(app, method, path, authorization=authorization, never=[token])).answer for method, path in panel_routes(job.job_id) for label, authorization in requests}

    assert mounted == dict.fromkeys(mounted, UNAUTHORIZED_ANSWER), f"Barrier: with a token set, each path answers the panel's 401, so the routes are there: {mounted}"
    assert nowhere.answer == OFF_ANSWER, f"Barrier: a path that does not exist answers {OFF_ANSWER}: {nowhere.answer}"
    assert answers == dict.fromkeys(answers, OFF_ANSWER), f"without a token each route must answer as a path that does not exist, {OFF_ANSWER}: {answers}"
    assert service.calls == [], f"the jobs must never be reached while the routes are off: {service.calls}"
    print_success(f"{len(answers)} requests without a token: 404 Not Found, the jobs untouched")


def set_unusable_token(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, kind: str) -> tuple[str | None, Path | None]:
    """A token the server cannot use, by ``kind``: ``too-short`` (the variable), ``too-short-in-its-file``, or a file of
    ``BROKEN_FILES``. Returns the short value (None when there is none) and the file (None when there is none)."""
    short = a_token()[: MIN_LENGTH - 1]
    if kind == "too-short":
        monkeypatch.setenv(TOKEN_VARIABLE, short)
        return short, None
    if kind == "too-short-in-its-file":
        path = write_token_file(tmp_path, short + "\n")
    else:
        path, short = tmp_path / "panel-token", None
        BROKEN_FILES[kind](path)
    monkeypatch.setenv(TOKEN_FILE_VARIABLE, str(path))
    return short, path


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["too-short", "too-short-in-its-file", *sorted(BROKEN_FILES)])
async def test_a_token_the_server_cannot_use_closes_every_route_with_503_and_one_log_line(app, monkeypatch, tmp_path, service, kind):
    """PANEL-011: each route answers 503 ``backup_panel_unavailable``, with or without a token presented, the short value
    included, never the file's path; each request logs one error naming the variable, never the value (the barrier of
    every log check of this module: the capture sees the panel's logger); the jobs are never reached."""
    print_section(f"Backup panel: a token the server cannot use ({kind})")
    short, path = set_unusable_token(monkeypatch, tmp_path, kind)
    job = service.done("panel")
    requests = [("no Authorization", None), ("Bearer, a token of the right length", f"Bearer {a_token()}"), ("Basic", f"Basic {a_token()}")]
    if short is not None:
        requests.append(("Bearer, the short value itself", f"Bearer {short}"))

    exchanges = {f"{method} {path_}, {label}": await send(app, method, path_, authorization=authorization, never=[short or ""]) for method, path_ in panel_routes(job.job_id) for label, authorization in requests}

    codes = {name: exchange.code for name, exchange in exchanges.items()}
    messages = {name: exchange.answer[1]["detail"].get("message") for name, exchange in exchanges.items() if exchange.code == UNAVAILABLE}
    logged = {name: [TOKEN_VARIABLE in repr(event) for event in exchange.errors] for name, exchange in exchanges.items()}
    paths_shown = [name for name, exchange in exchanges.items() if path is not None and str(path) in exchange.response.text]
    assert codes == dict.fromkeys(codes, UNAVAILABLE), f"each route must answer {UNAVAILABLE} whatever the request presents: {codes}"
    assert logged == dict.fromkeys(logged, [True]), f"each request logs exactly one error, naming {TOKEN_VARIABLE}: {logged}"
    assert all(isinstance(message, str) and message for message in messages.values()), f"each 503 carries a message: {messages}"
    assert paths_shown == [], f"the path of the token's file belongs in the log, never in an answer: {paths_shown}"
    assert service.calls == [], f"the jobs must never be reached with a token the server cannot use: {service.calls}"
    print_success(f"{len(exchanges)} requests: 503 backup_panel_unavailable, one error line each naming the variable")


@pytest.mark.asyncio
async def test_without_the_token_each_route_answers_401_and_reaches_no_job(app, monkeypatch, service):
    """PANEL-012: the token missing or wrong, each route answers the panel's 401 with ``WWW-Authenticate: Bearer`` and the
    jobs are never reached. Barrier: the right token then reads the job."""
    print_section("Backup panel: a request without the token")
    token = a_token()
    monkeypatch.setenv(TOKEN_VARIABLE, token)
    job = service.done("panel")
    wrong = [
        ("no Authorization", None, None),
        ("Basic, the token", f"Basic {token}", None),
        ("Bearer with nothing", "Bearer", None),
        ("Bearer and a space", "Bearer ", None),
        ("Bearer, another token", f"Bearer {a_token()}", None),
        ("Bearer, a prefix of the token", f"Bearer {token[:-1]}", None),
        ("Bearer, an extension of the token", f"Bearer {token}0", None),
        ("Bearer, the token in capitals", f"Bearer {token.upper()}", None),
        ("the token in the query string", None, {"token": token, "access_token": token}),
    ]

    exchanges = {f"{method} {path}, {label}": await send(app, method, path, authorization=authorization, params=params, never=[token]) for method, path in panel_routes(job.job_id) for label, authorization, params in wrong}
    refused_calls = list(service.calls)
    served = await send(app, "GET", f"{PANEL}/{job.job_id}", authorization=f"Bearer {token}", never=[token])

    answers = {name: exchange.answer for name, exchange in exchanges.items()}
    challenges = {name: exchange.response.headers.get("www-authenticate") for name, exchange in exchanges.items()}
    assert answers == dict.fromkeys(answers, UNAUTHORIZED_ANSWER), f"each route must answer the panel's 401 without the right token: {answers}"
    assert challenges == dict.fromkeys(challenges, "Bearer"), f"each 401 must ask for a Bearer token: {challenges}"
    assert refused_calls == [], f"the jobs must never be reached without the right token: {refused_calls}"
    assert served.response.status_code == 200 and service.calls == [("get_job", job.job_id)], f"Barrier: the right token reads the job: {served.answer}, calls {service.calls}"
    print_success(f"{len(exchanges)} requests without the right token: 401 Bearer, the jobs untouched")


# =============================================================================
# PANEL-013..017: with the token, the panel's own jobs
# =============================================================================


@pytest.mark.asyncio
async def test_with_the_token_the_panel_starts_polls_downloads_and_deletes_its_job(app, monkeypatch, service):
    """PANEL-013: start 202 with its first state, a run of origin ``panel`` without a password (the panel never encrypts);
    poll 200 done; download 200 with the archive's exact bytes, ``application/zip``, an attachment, ``Cache-Control:
    no-store``; delete 204; then the job is gone. Each route reaches the service with exactly the calls of the panel."""
    print_section("Backup panel: a backup, from the start to the deletion")
    token = a_token()
    monkeypatch.setenv(TOKEN_VARIABLE, token)
    bearer = f"Bearer {token}"

    started, start_calls = await with_calls(service, send(app, "POST", PANEL, authorization=bearer, never=[token]))
    assert started.response.status_code == 202, f"POST {PANEL} with the token: 202 with the job: {started.answer}"
    job_id = started.response.json()["job_id"]
    done = service.finish(job_id)
    archive = service.archive(done).read_bytes()
    polled, poll_calls = await with_calls(service, send(app, "GET", f"{PANEL}/{job_id}", authorization=bearer, never=[token]))
    downloaded, file_calls = await with_calls(service, send(app, "GET", f"{PANEL}/{job_id}/file", authorization=bearer, never=[token]))
    deleted, delete_calls = await with_calls(service, send(app, "DELETE", f"{PANEL}/{job_id}", authorization=bearer, never=[token]))
    gone = await send(app, "GET", f"{PANEL}/{job_id}", authorization=bearer, never=[token])

    first = started.response.json()
    assert (first["status"], first["phase"], first["error_code"]) == ("running", "preparing", None) and start_calls == [("start_backup", "panel")], f"the start asks for one run of origin panel and answers its first state: {first}, calls {start_calls}"
    assert service.start_passwords == [None], f"the panel never encrypts: its start carries no password: {service.start_passwords}"
    assert polled.response.status_code == 200 and poll_calls == [("get_job", job_id)], f"the poll reads the job: {polled.answer}, calls {poll_calls}"
    view = polled.response.json()
    assert (view["job_id"], view["status"], view["file_name"], view["file_size"]) == (job_id, "done", done.file_name, len(archive)), f"the poll answers the job done, with its archive: {view}"
    assert (downloaded.response.status_code, downloaded.response.content) == (200, archive), f"the download is the archive's exact bytes: {downloaded.answer}"
    headers = {name: downloaded.response.headers.get(name) for name in ("content-type", "cache-control", "content-disposition")}
    assert headers == {"content-type": "application/zip", "cache-control": "no-store", "content-disposition": f'attachment; filename="{done.file_name}"'}, f"the download's headers: {headers}"
    assert file_calls == [("get_job", job_id), ("job_archive", job_id)], f"the download reads the job, then its archive: {file_calls}"
    assert (deleted.response.status_code, deleted.response.content) == (204, b"") and delete_calls == [("get_job", job_id), ("delete_job", job_id)], f"the deletion reads the job, then deletes it: {deleted.answer}, calls {delete_calls}"
    assert gone.code == JOB_NOT_FOUND, f"a deleted job is no longer found: {gone.answer}"
    print_success("start 202 (origin panel), poll 200 done, download 200 with the archive's bytes, no-store, delete 204")


@pytest.mark.asyncio
async def test_the_token_from_its_file_opens_the_routes_and_the_variable_wins(app, monkeypatch, tmp_path, service):
    """PANEL-014: the token read from the ``_FILE`` (a line break after it) opens the routes; with the variable set too,
    the variable's token opens them and the file's no longer does."""
    from_file, from_variable = a_token(), a_token()
    monkeypatch.setenv(TOKEN_FILE_VARIABLE, str(write_token_file(tmp_path, from_file + "\n")))
    job = service.done("panel")
    path = f"{PANEL}/{job.job_id}"

    file_only = await send(app, "GET", path, authorization=f"Bearer {from_file}", never=[from_file, from_variable])
    monkeypatch.setenv(TOKEN_VARIABLE, from_variable)
    variable = await send(app, "GET", path, authorization=f"Bearer {from_variable}", never=[from_file, from_variable])
    file_after = await send(app, "GET", path, authorization=f"Bearer {from_file}", never=[from_file, from_variable])

    assert file_only.response.status_code == 200, f"the token of the file opens the routes: {file_only.answer}"
    assert variable.response.status_code == 200, f"both set, the variable's token opens the routes: {variable.answer}"
    assert file_after.answer == UNAUTHORIZED_ANSWER, f"both set, the file's token no longer opens them: {file_after.answer}"


@pytest.mark.asyncio
@pytest.mark.parametrize("origin", ["ui", "cli", "pre-restore"])
async def test_a_job_of_another_origin_is_invisible_to_the_panel(app, monkeypatch, service, origin):
    """PANEL-015: with the right token, a job the panel did not start answers the poll, the download and the deletion
    exactly as a job that does not exist, 404 ``backup_job_not_found``: only the job is read, never its archive, and it
    is never deleted. Barrier: the panel's own job is served."""
    print_section(f"Backup panel: a job of origin {origin}")
    token = a_token()
    monkeypatch.setenv(TOKEN_VARIABLE, token)
    bearer = f"Bearer {token}"
    own, other, unknown = service.done("panel"), service.done(origin), uuid4().hex

    served = await send(app, "GET", f"{PANEL}/{own.job_id}/file", authorization=bearer, never=[token])
    hidden = {f"{method} {path.replace(other.job_id, '{other}')}": await with_calls(service, send(app, method, path, authorization=bearer, never=[token])) for method, path in job_routes(other.job_id)}
    absent = {f"{method} {path.replace(unknown, '{other}')}": await send(app, method, path, authorization=bearer, never=[token]) for method, path in job_routes(unknown)}

    assert (served.response.status_code, served.response.content) == (200, service.archive(own).read_bytes()), f"Barrier: the right token downloads the panel's own job: {served.answer}"
    answers = {route: (exchange.code, calls) for route, (exchange, calls) in hidden.items()}
    assert answers == dict.fromkeys(answers, (JOB_NOT_FOUND, [("get_job", other.job_id)])), f"a job of origin {origin} must answer 404 backup_job_not_found, the job read and nothing else: {answers}"
    as_absent = {route: (exchange.answer, absent[route].answer) for route, (exchange, _calls) in hidden.items()}
    assert all(seen == unknown_answer for seen, unknown_answer in as_absent.values()), f"a job of origin {origin} must answer exactly as a job that does not exist: {as_absent}"
    assert other.job_id in service.known and service.archive(other).is_file(), f"the job of origin {origin} and its archive must stay"
    print_success(f"origin {origin}: poll, download, delete answer 404 as for no job; never the archive, never deleted")


@pytest.mark.asyncio
async def test_an_unknown_job_answers_404_after_reading_the_job_only(app, monkeypatch, service):
    """PANEL-016: a job id of the right shape that no job has: the poll, the download and the deletion answer 404
    ``backup_job_not_found``, each after one read of the job and nothing else."""
    token = a_token()
    monkeypatch.setenv(TOKEN_VARIABLE, token)
    unknown = uuid4().hex

    answers = {f"{method} {path}": await with_calls(service, send(app, method, path, authorization=f"Bearer {token}", never=[token])) for method, path in job_routes(unknown)}

    codes = {route: (exchange.code, calls) for route, (exchange, calls) in answers.items()}
    assert codes == dict.fromkeys(codes, (JOB_NOT_FOUND, [("get_job", unknown)])), f"an unknown job: 404 backup_job_not_found after one read: {codes}"


@pytest.mark.asyncio
async def test_a_running_job_of_the_panel_has_no_archive_yet_and_cannot_be_deleted(app, monkeypatch, service):
    """PANEL-017: a running job of the panel polls 200 running; its download answers 409 ``backup_job_not_ready`` and its
    deletion 409 ``backup_job_running``, each after reading the job; the job stays."""
    token = a_token()
    monkeypatch.setenv(TOKEN_VARIABLE, token)
    bearer = f"Bearer {token}"
    job = service.running("panel")

    polled, poll_calls = await with_calls(service, send(app, "GET", f"{PANEL}/{job.job_id}", authorization=bearer, never=[token]))
    downloaded, file_calls = await with_calls(service, send(app, "GET", f"{PANEL}/{job.job_id}/file", authorization=bearer, never=[token]))
    deleted, delete_calls = await with_calls(service, send(app, "DELETE", f"{PANEL}/{job.job_id}", authorization=bearer, never=[token]))

    assert polled.response.status_code == 200 and polled.response.json()["status"] == "running" and poll_calls == [("get_job", job.job_id)], f"the poll of a running job: {polled.answer}, calls {poll_calls}"
    assert (downloaded.code, file_calls) == ((409, "backup_job_not_ready"), [("get_job", job.job_id), ("job_archive", job.job_id)]), f"the download of a running job: {downloaded.answer}, calls {file_calls}"
    assert (deleted.code, delete_calls) == ((409, "backup_job_running"), [("get_job", job.job_id), ("delete_job", job.job_id)]), f"the deletion of a running job: {deleted.answer}, calls {delete_calls}"
    assert job.job_id in service.known, "a running job stays"


# =============================================================================
# PANEL-018..020: the start errors, the administrators' view, OpenAPI
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "status_code", "code"),
    [
        pytest.param(lambda: jobs.BackupBusyError("Another backup is running"), 409, "backup_busy", id="another-run-in-progress"),
        pytest.param(lambda: BackupPathError(DATA_DIR / "backups"), 500, "backup_folder_unusable", id="backups-is-a-link-or-a-file"),
        pytest.param(lambda: PermissionError(errno.EACCES, os.strerror(errno.EACCES), str(DATA_DIR / "backups" / ".jobs")), 500, "backup_failed", id="backups-cannot-be-written"),
        pytest.param(lambda: OSError(errno.EROFS, os.strerror(errno.EROFS), str(DATA_DIR / "backups")), 500, "backup_failed", id="read-only-file-system"),
    ],
)
async def test_a_panel_start_that_cannot_run_answers_the_shared_codes_and_nothing_of_the_server(app, monkeypatch, service, error, status_code, code):
    """PANEL-018: the start errors of the administrators' route, through ``job_views.start_job``: each reason its code,
    never the data directory's path nor the system's words in the answer."""
    token = a_token()
    monkeypatch.setenv(TOKEN_VARIABLE, token)
    service.start_error = error()

    started = await send(app, "POST", PANEL, authorization=f"Bearer {token}", never=[token])

    assert service.calls == [("start_backup", "panel")], f"Precondition: the route asked for a run of origin panel: {service.calls}"
    assert service.start_passwords == [None], f"the panel never encrypts: its start carries no password: {service.start_passwords}"
    assert started.code == (status_code, code), f"expected {status_code} with detail.code {code!r}: {started.answer}"
    leaked = [word for word in (str(DATA_DIR), *SYSTEM_WORDS) if word in started.response.text]
    assert leaked == [], f"the answer must not carry the server's path or the system's words: {leaked} in {started.response.text}"
    print_success(f"{status_code} {code}")


@pytest.mark.asyncio
async def test_an_administrator_sees_every_job_the_panels_included(monkeypatch, service):
    """PANEL-019: the administrators' routes (``instance.py``, no origin) keep the calls of before B8 and see a job of the
    panel too: start → start_backup("ui"); poll → get_job; download → job_archive, the exact bytes; delete →
    delete_job."""
    print_section("Backup panel: an administrator sees the panel's jobs")
    app = backup_app(administrator=True)
    job = service.done("panel")
    archive = service.archive(job).read_bytes()

    started, start_calls = await with_calls(service, send(app, "POST", INSTANCE))
    polled, poll_calls = await with_calls(service, send(app, "GET", f"{INSTANCE}/jobs/{job.job_id}"))
    downloaded, file_calls = await with_calls(service, send(app, "GET", f"{INSTANCE}/jobs/{job.job_id}/file"))
    deleted, delete_calls = await with_calls(service, send(app, "DELETE", f"{INSTANCE}/jobs/{job.job_id}"))

    assert (started.response.status_code, start_calls) == (202, [("start_backup", "ui")]), f"an administrator's start asks for a run of origin ui: {started.answer}, calls {start_calls}"
    assert (polled.response.status_code, poll_calls) == (200, [("get_job", job.job_id)]), f"an administrator polls a job of the panel: {polled.answer}, calls {poll_calls}"
    assert polled.response.json()["job_id"] == job.job_id, f"the poll answers the panel's job: {polled.answer}"
    assert (downloaded.response.status_code, downloaded.response.content, file_calls) == (200, archive, [("job_archive", job.job_id)]), f"an administrator downloads a job of the panel, its archive read directly: {downloaded.answer}, calls {file_calls}"
    assert (deleted.response.status_code, delete_calls) == (204, [("delete_job", job.job_id)]), f"an administrator deletes a job of the panel directly: {deleted.answer}, calls {delete_calls}"
    print_success("an administrator: start (ui), poll, download, delete of a panel job, with the calls of before B8")


def test_openapi_asks_the_panel_token_on_the_four_panel_routes_only():
    """PANEL-020: OpenAPI documents ``BackupPanelToken`` as an HTTP bearer scheme, required by the four routes of the
    panel and by no other route of ``/backup``."""
    document = backup_app().openapi()
    scheme = document["components"]["securitySchemes"]["BackupPanelToken"]
    asking = {f"{method.upper()} {path}": operation.get("security") for path, item in document["paths"].items() for method, operation in item.items() if "BackupPanelToken" in repr(operation.get("security"))}
    expected = {f"{method} {path}": [{"BackupPanelToken": []}] for method, path in panel_routes("{job_id}")}

    assert (scheme["type"], scheme["scheme"]) == ("http", "bearer"), f"BackupPanelToken is an HTTP bearer scheme: {scheme}"
    assert asking == expected, f"the four routes of the panel, and only they, ask for BackupPanelToken: {asking}"


# =============================================================================
# PANEL-021: a token with spaces around it
# =============================================================================


@pytest.mark.asyncio
async def test_a_token_with_spaces_around_it_answers_503_even_to_that_very_token(app, monkeypatch, service):
    """PANEL-021: a token written with spaces around it, in the variable, could never be presented as written: a header
    loses the spaces around its credentials, so the panel would meet a 401 at every request and the server would say
    nothing. Each route answers 503 ``backup_panel_unavailable`` instead, without a header and to that very token, with
    its spaces or without them, and each request logs one error naming the variable, never the value; the jobs are never
    reached. Barrier: the same token without its spaces opens the routes."""
    print_section("Backup panel: a token with spaces around it")
    token = a_token()
    spaced = f" {token} "
    monkeypatch.setenv(TOKEN_VARIABLE, spaced)
    job = service.done("panel")
    requests = [("no Authorization", None), ("Bearer, the token with its spaces", f"Bearer {spaced}"), ("Bearer, the token without its spaces", f"Bearer {token}")]

    exchanges = {f"{method} {path}, {label}": await send(app, method, path, authorization=authorization, never=[spaced, token]) for method, path in panel_routes(job.job_id) for label, authorization in requests}
    refused_calls = list(service.calls)
    monkeypatch.setenv(TOKEN_VARIABLE, token)
    opened = await send(app, "GET", f"{PANEL}/{job.job_id}", authorization=f"Bearer {token}", never=[token])

    codes = {name: exchange.code for name, exchange in exchanges.items()}
    logged = {name: [TOKEN_VARIABLE in repr(event) for event in exchange.errors] for name, exchange in exchanges.items()}
    assert codes == dict.fromkeys(codes, UNAVAILABLE), f"a token with spaces around it: each route must answer {UNAVAILABLE}, to that very token too: {codes}"
    assert logged == dict.fromkeys(logged, [True]), f"each request logs exactly one error, naming {TOKEN_VARIABLE}: {logged}"
    assert refused_calls == [], f"the jobs must never be reached with a token the server cannot use: {refused_calls}"
    assert opened.response.status_code == 200 and service.calls == [("get_job", job.job_id)], f"Barrier: the same token without its spaces opens the routes: {opened.answer}, calls {service.calls}"
    print_success(f"{len(exchanges)} requests: 503 backup_panel_unavailable, to that very token too, one error line each; without its spaces the token opens the routes")


# =============================================================================
# PANEL-022: a full disk at the panel's start (B-30)
# =============================================================================


@pytest.mark.asyncio
async def test_a_panel_start_on_a_full_disk_answers_507_backup_no_space(app, monkeypatch, service):
    """PANEL-022 (B-30): the panel's start through ``job_views.start_job``, ``start_backup`` raising ``ENOSPC``: with the
    token, 507 ``backup_no_space``, never 500 ``backup_failed``; one WARNING, «Instance backup could not start: not
    enough free space», with the origin ``panel``; never the data directory's path nor the system's words."""
    token = a_token()
    monkeypatch.setenv(TOKEN_VARIABLE, token)
    service.start_error = OSError(errno.ENOSPC, os.strerror(errno.ENOSPC), str(DATA_DIR / "backups" / ".jobs"))

    started = await send(app, "POST", PANEL, authorization=f"Bearer {token}", never=[token])

    assert service.calls == [("start_backup", "panel")], f"Precondition: the route asked for a run of origin panel: {service.calls}"
    assert started.code == (507, "backup_no_space"), f"a full disk at the panel's start: 507 backup_no_space: {started.answer}"
    loud = [(event.get("log_level"), event.get("event"), event.get("origin")) for event in started.events if event.get("log_level") in ("warning", "error", "critical")]
    assert loud == [("warning", "Instance backup could not start: not enough free space", "panel")], f"one warning, with the origin panel: {loud}"
    leaked = [word for word in (str(DATA_DIR), os.strerror(errno.ENOSPC)) if word in started.response.text]
    assert leaked == [], f"the answer must not carry the server's path or the system's words: {leaked} in {started.response.text}"
    print_success("507 backup_no_space, one warning")


def test_openapi_documents_507_on_the_panel_start():
    """PANEL-022 (B-30): the panel's start documents its 507 beside its 409 and its 500, as the administrators' start does
    (``START_RESPONSES``)."""
    documented = set(backup_app().openapi()["paths"][PANEL]["post"]["responses"])
    assert {"409", "500", "507"} <= documented, f"the panel's start, its refusals, 507 included: {sorted(documented)}"


# =============================================================================
# PANEL-023..024: a start refused while a job runs (B-8)
# =============================================================================

#: What a start refused while another run is in progress says, as before B-8.
BUSY_MESSAGE = "Another backup is running"


def busy_with(running: jobs.BackupJob | None) -> jobs.BackupBusyError:
    """The refusal of a start while another run holds the lock, built as PANEL-018 builds it, carrying the running job it
    could read (B-8), or None. ``running`` is set on the instance: the test does not depend on how the constructor takes
    it."""
    error = jobs.BackupBusyError(BUSY_MESSAGE)
    error.running = running
    return error


@pytest.mark.asyncio
async def test_a_panel_start_refused_while_its_own_job_runs_names_that_job(app, monkeypatch, service):
    """PANEL-023 (B-8): a start refused while a job of the panel runs names that job: 409, ``detail`` exactly ``{code:
    backup_busy, message: «Another backup is running», job_id, origin: panel}``. A panel whose start answer was lost
    finds its job there, and follows it: its poll answers that job, running."""
    print_section("Backup panel: a start refused while the panel's own job runs (B-8)")
    token = a_token()
    monkeypatch.setenv(TOKEN_VARIABLE, token)
    bearer = f"Bearer {token}"
    running = service.running("panel")
    service.start_error = busy_with(running)

    started = await send(app, "POST", PANEL, authorization=bearer, never=[token])

    assert service.calls[:1] == [("start_backup", "panel")], f"Precondition: the route asked for a run of origin panel: {service.calls}"
    expected = {"detail": {"code": "backup_busy", "message": BUSY_MESSAGE, "job_id": running.job_id, "origin": "panel"}}
    assert started.answer == (409, expected), f"a start refused while the panel's own job runs must name that job: {started.answer}"
    followed = await send(app, "GET", f"{PANEL}/{started.response.json()['detail']['job_id']}", authorization=bearer, never=[token])
    polled = followed.response.json() if followed.response.status_code == 200 else {}
    assert (followed.response.status_code, polled.get("job_id"), polled.get("status")) == (200, running.job_id, "running"), f"the panel follows the job its refusal names: {followed.answer}"
    print_success("409 backup_busy naming the panel's running job; its poll answers it, running")


@pytest.mark.asyncio
@pytest.mark.parametrize("origin", ["ui", "cli", "pre-restore", pytest.param(None, id="no-job-read")])
async def test_a_panel_start_refused_while_a_job_it_cannot_see_runs_names_no_job(app, monkeypatch, service, origin):
    """PANEL-024 (B-8), a guard become contract: a start refused while a job of another origin runs (the Backup tab's,
    the command line's, a pre-restore backup), or with no job read, names none: 409, ``detail`` exactly ``{code:
    backup_busy, message}``, no ``job_id`` nor ``origin``. The panel sees only its own jobs (PANEL-015), in a refusal
    too."""
    token = a_token()
    monkeypatch.setenv(TOKEN_VARIABLE, token)
    running = None if origin is None else service.running(origin)
    service.start_error = busy_with(running)

    started = await send(app, "POST", PANEL, authorization=f"Bearer {token}", never=[token])

    assert service.calls[:1] == [("start_backup", "panel")], f"Precondition: the route asked for a run of origin panel: {service.calls}"
    assert started.answer == (409, {"detail": {"code": "backup_busy", "message": BUSY_MESSAGE}}), f"a job of origin {origin} is not the panel's: the refusal must not name it: {started.answer}"
    print_success(f"origin {origin}: 409 backup_busy, code and message only")


# =============================================================================
# PANEL-025..027: what a job's view tells of its archive (lot L3)
# =============================================================================

#: A SHA-256 as a job's view gives it: 64 lowercase hex digits.
SHA256_HEX = re.compile(r"[0-9a-f]{64}")


def archive_facts(view: dict[str, Any]) -> dict[str, object]:
    """What lot L3 adds to a job's view, or ``<missing>`` where the view has no such field."""
    return {name: view.get(name, "<missing>") for name in ("file_sha256", "instance_key_included")}


@pytest.mark.asyncio
async def test_the_panel_s_poll_gives_the_sha256_of_the_bytes_its_download_serves(app, monkeypatch, service):
    """PANEL-025 (L3): the panel's poll of its done job gives ``file_sha256``, the SHA-256 of the exact bytes its download
    returns, 64 lowercase hex digits, and ``instance_key_included`` false; a running job of the panel answers
    ``file_sha256`` null and ``instance_key_included`` false."""
    print_section("Backup panel: the SHA-256 of the archive, in the job's view (L3)")
    token = a_token()
    monkeypatch.setenv(TOKEN_VARIABLE, token)
    bearer = f"Bearer {token}"
    done, running = service.done("panel"), service.running("panel")

    polled = await send(app, "GET", f"{PANEL}/{done.job_id}", authorization=bearer, never=[token])
    downloaded = await send(app, "GET", f"{PANEL}/{done.job_id}/file", authorization=bearer, never=[token])
    still_running = await send(app, "GET", f"{PANEL}/{running.job_id}", authorization=bearer, never=[token])

    assert (polled.response.status_code, downloaded.response.status_code, still_running.response.status_code) == (200, 200, 200), f"precondition: the poll and the download answer: {polled.answer}, {downloaded.answer}, {still_running.answer}"
    served = hashlib.sha256(downloaded.response.content).hexdigest()
    facts = archive_facts(polled.response.json())
    assert facts == {"file_sha256": served, "instance_key_included": False}, f"the done job's view: the SHA-256 of the bytes served ({served}), no instance key: {facts}"
    assert SHA256_HEX.fullmatch(str(facts["file_sha256"])), f"64 lowercase hex digits: {facts['file_sha256']!r}"
    assert archive_facts(still_running.response.json()) == {"file_sha256": None, "instance_key_included": False}, f"a running job has no archive yet: {archive_facts(still_running.response.json())}"
    print_success(f"done: sha256 {served[:12]}…, no key; running: null")


@pytest.mark.asyncio
async def test_an_administrator_s_poll_gives_the_same_sha256_of_a_panel_job(monkeypatch, service):
    """PANEL-026 (L3): the administrators' routes (PANEL-019's) answer a job of the panel with the same
    ``file_sha256``, that of the bytes their own download serves, and ``instance_key_included`` false; a running job,
    ``file_sha256`` null."""
    app = backup_app(administrator=True)
    done, running = service.done("panel"), service.running("panel")

    polled = await send(app, "GET", f"{INSTANCE}/jobs/{done.job_id}")
    downloaded = await send(app, "GET", f"{INSTANCE}/jobs/{done.job_id}/file")
    still_running = await send(app, "GET", f"{INSTANCE}/jobs/{running.job_id}")

    assert (polled.response.status_code, downloaded.response.status_code, still_running.response.status_code) == (200, 200, 200), f"precondition: the poll and the download answer: {polled.answer}, {downloaded.answer}, {still_running.answer}"
    served = hashlib.sha256(downloaded.response.content).hexdigest()
    assert archive_facts(polled.response.json()) == {"file_sha256": served, "instance_key_included": False}, f"an administrator reads the SHA-256 of the bytes served, no instance key: {archive_facts(polled.response.json())}"
    assert archive_facts(still_running.response.json()) == {"file_sha256": None, "instance_key_included": False}, f"a running job has no archive yet: {archive_facts(still_running.response.json())}"


@pytest.mark.asyncio
async def test_an_administrator_reads_that_a_secure_job_carries_the_instance_key(monkeypatch, service):
    """PANEL-027 (L3): a secure job of the Backup tab whose archive carries the instance key
    (``jobs.BackupJob.instance_key_included`` true, as ``_run`` records it) reads ``instance_key_included`` true to an
    administrator, beside the SHA-256 of its archive."""
    if "instance_key_included" not in {item.name for item in fields(jobs.BackupJob)}:
        pytest.fail("red until L3: jobs.BackupJob has no field instance_key_included", pytrace=False)
    app = backup_app(administrator=True)
    done = service.done("ui")
    secure = replace(done, encrypted=True, instance_key_included=True)
    service.known[done.job_id] = secure

    polled = await send(app, "GET", f"{INSTANCE}/jobs/{done.job_id}")

    assert polled.response.status_code == 200, f"precondition: an administrator polls the job: {polled.answer}"
    view = polled.response.json()
    assert (view.get("encrypted"), *archive_facts(view).values()) == (True, secure.file_sha256, True), f"a secure job carrying the key: {view}"


# =============================================================================
# PANEL-028..034 (lot L3-2): the sealed backup of the panel
# =============================================================================


def a_recipient() -> str:
    """A new age X25519 recipient, ``age1…``: the public half of an identity made for one test."""
    return str(x25519.Identity.generate().to_public())


def a_private_key() -> str:
    """A new age X25519 identity, ``AGE-SECRET-KEY-1…``: a test key, given where a recipient belongs."""
    return str(x25519.Identity.generate())


def use_profile(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, profile: str) -> None:
    """``get_settings()`` reads ``LIBREFOLIO_PROFILE`` as ``profile`` from this environment alone, in test mode and with
    a data directory of the test (as ``test_donation_managed_profile.py`` sets it); barrier: it reads that profile."""
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(PROFILE_VARIABLE, profile)
    cache_clear = getattr(config.get_settings, "cache_clear", None)
    if callable(cache_clear):
        cache_clear()
    resolved = config.get_settings().LIBREFOLIO_PROFILE
    assert resolved == profile, f"barrier: get_settings() reads the profile {profile!r}, not {resolved!r}"


async def panel_start(app: FastAPI, service: FakeJobs, token: str, *, never: Iterable[str] = ()) -> tuple[Exchange, list[tuple[str, str]], list[tuple[str, ...] | None], list[str | None]]:
    """``POST`` the panel's start with the token: the exchange, the calls, and the recipients and passwords each start
    received meanwhile."""
    marks = (len(service.start_recipients), len(service.start_passwords))
    exchange, calls = await with_calls(service, send(app, "POST", PANEL, authorization=f"Bearer {token}", never=[token, *never]))
    return exchange, calls, service.start_recipients[marks[0] :], service.start_passwords[marks[1] :]


def sealed_fields_exist() -> None:
    """Lot L3-2's fields of ``jobs.BackupJob``; before it, a failure that says so."""
    missing = [name for name in ("sealed", "sealed_recipients") if name not in {item.name for item in fields(jobs.BackupJob)}]
    if missing:
        pytest.fail(f"red until L3-2: jobs.BackupJob has no field {', '.join(missing)}", pytrace=False)


def sealed_done(service: FakeJobs, recipients: tuple[str, ...]) -> jobs.BackupJob:
    """A done job of the panel, sealed for ``recipients``: its archive a ``.tar`` (bytes of its own), as a sealed run
    leaves it."""
    sealed_fields_exist()
    job = service.running("panel")
    name = archive_name_tar(job.created_at)
    archive = service.folder / job.job_id / name
    archive.parent.mkdir(parents=True)
    archive.write_bytes(b"manifest.json\0" + job.job_id.encode() + bytes(range(256)))
    size = archive.stat().st_size
    done = replace(
        job,
        status="done",
        phase=None,
        done_bytes=size,
        total_bytes=size,
        finished_at=FINISHED_AT,
        file_name=name,
        file_size=size,
        file_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
        encrypted=True,
        sealed=True,
        sealed_recipients=recipients,
    )
    service.known[job.job_id] = done
    return done


def archive_name_tar(created_at: datetime) -> str:
    """The name of a sealed archive (contract §3.1): ``librefolio-backup-YYYYMMDD-HHMMSS.tar``, in UTC."""
    return f"librefolio-backup-{created_at.astimezone(UTC):%Y%m%d-%H%M%S}.tar"


@pytest.mark.asyncio
@pytest.mark.parametrize("count", [1, 2])
@pytest.mark.parametrize("spaced", [False, True], ids=["as-written", "spaces-around"])
async def test_with_recipients_the_panel_starts_a_sealed_run_without_a_password(app, monkeypatch, service, count, spaced):
    """PANEL-028 (L3-2): ``LIBREFOLIO_BACKUP_RECIPIENTS`` set to one or two recipients (spaces around each ignored): the
    start answers 202 and asks for one run of origin ``panel`` with exactly those recipients, in order, and no
    password."""
    print_section(f"Backup panel: a sealed start, {count} recipient(s)")
    token = a_token()
    monkeypatch.setenv(TOKEN_VARIABLE, token)
    recipients = tuple(a_recipient() for _ in range(count))
    monkeypatch.setenv(RECIPIENTS_VARIABLE, f"  {' , '.join(recipients)} " if spaced else ",".join(recipients))

    started, calls, given, passwords = await panel_start(app, service, token)

    assert started.response.status_code == 202 and calls == [("start_backup", "panel")], f"one run of origin panel: {started.answer}, calls {calls}"
    assert given == [recipients], f"the start carries the recipients, in order: {given}, expected {[recipients]}"
    assert passwords == [None], f"a sealed run takes no password from the panel: {passwords}"
    print_success(f"{count} recipient(s): start_backup('panel', recipients=…)")


#: Values of ``LIBREFOLIO_BACKUP_RECIPIENTS`` the server cannot use (contract L3 §2), each built at the call.
UNUSABLE_RECIPIENTS: dict[str, Callable[[], list[str]]] = {
    "garbage": lambda: ["not-an-age-recipient"],
    "a-private-key": lambda: [a_private_key()],
    "an-empty-item": lambda: [a_recipient(), "", a_recipient()],
    "three-recipients": lambda: [a_recipient(), a_recipient(), a_recipient()],
    "one-twice": lambda: [recipient := a_recipient(), recipient],
}


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", sorted(UNUSABLE_RECIPIENTS))
async def test_recipients_the_server_cannot_use_answer_503_with_one_log_line_and_reach_no_job(app, monkeypatch, service, kind):
    """PANEL-029 (L3-2, D1): a value of ``LIBREFOLIO_BACKUP_RECIPIENTS`` the server cannot use: the start answers 503
    ``backup_panel_unavailable``, never a clear zip; one error line naming the variable and never the value (nor an item
    of it); the jobs never reached."""
    print_section(f"Backup panel: recipients the server cannot use ({kind})")
    token = a_token()
    monkeypatch.setenv(TOKEN_VARIABLE, token)
    items = UNUSABLE_RECIPIENTS[kind]()
    monkeypatch.setenv(RECIPIENTS_VARIABLE, ",".join(items))

    refused, calls, _given, _passwords = await panel_start(app, service, token, never=[",".join(items), *items])

    assert refused.code == UNAVAILABLE, f"a value it cannot use closes the start: {refused.answer}"
    logged = [RECIPIENTS_VARIABLE in repr(event) for event in refused.errors]
    assert logged == [True], f"one error line, naming {RECIPIENTS_VARIABLE}: {[event.get('event') for event in refused.errors]}"
    assert calls == [], f"the jobs must never be reached: {calls}"
    print_success(f"{kind}: 503 backup_panel_unavailable, one error line, no job")


@pytest.mark.asyncio
async def test_without_recipients_a_managed_instance_answers_503_and_reaches_no_job(app, monkeypatch, tmp_path, service):
    """PANEL-030 (L3-2, D1): ``LIBREFOLIO_BACKUP_RECIPIENTS`` unset in the ``managed`` profile: 503
    ``backup_panel_unavailable``, one error line, the jobs never reached. Barrier: set, the same profile starts a sealed
    run."""
    print_section("Backup panel: managed, no recipients")
    token = a_token()
    monkeypatch.setenv(TOKEN_VARIABLE, token)
    use_profile(monkeypatch, tmp_path, "managed")

    refused, calls, _given, _passwords = await panel_start(app, service, token)
    recipient = a_recipient()
    monkeypatch.setenv(RECIPIENTS_VARIABLE, recipient)
    started, started_calls, given, _ = await panel_start(app, service, token)

    assert started.response.status_code == 202 and started_calls == [("start_backup", "panel")] and given == [(recipient,)], f"barrier: managed with recipients starts a sealed run: {started.answer}, {started_calls}, {given}"
    assert refused.code == UNAVAILABLE, f"managed without recipients: never a clear zip: {refused.answer}"
    assert len(refused.errors) == 1, f"one error line: {[event.get('event') for event in refused.errors]}"
    assert calls == [], f"the jobs must never be reached: {calls}"
    print_success("managed, unset: 503; set: a sealed start")


@pytest.mark.asyncio
async def test_without_recipients_a_selfhosted_instance_starts_the_clear_backup_of_before(app, monkeypatch, tmp_path, service):
    """PANEL-031 (L3-2): unset in the ``selfhosted`` profile: the start of before, origin ``panel``, no recipients, no
    password."""
    token = a_token()
    monkeypatch.setenv(TOKEN_VARIABLE, token)
    use_profile(monkeypatch, tmp_path, "selfhosted")

    started, calls, given, passwords = await panel_start(app, service, token)

    assert started.response.status_code == 202 and calls == [("start_backup", "panel")], f"the start of before: {started.answer}, calls {calls}"
    assert (given, passwords) == ([None], [None]), f"no recipients, no password: {given}, {passwords}"


@pytest.mark.asyncio
async def test_the_panel_s_view_of_a_sealed_job_carries_the_seal_and_its_tar_downloads_as_x_tar(app, monkeypatch, service):
    """PANEL-032, PANEL-034 (L3-2, contract §4): a sealed done job reads ``encrypted`` and ``sealed`` true,
    ``sealed_recipients`` its recipients, ``instance_key_included`` false and ``file_sha256`` the SHA-256 of the bytes
    its download serves; the download is ``application/x-tar``, an attachment under its name, ``no-store``. A job not
    sealed reads ``sealed`` false and ``sealed_recipients`` ``[]``."""
    print_section("Backup panel: the view and the download of a sealed job")
    token = a_token()
    monkeypatch.setenv(TOKEN_VARIABLE, token)
    bearer = f"Bearer {token}"
    recipients = (a_recipient(), a_recipient())
    sealed = sealed_done(service, recipients)
    clear = service.done("panel")

    polled = await send(app, "GET", f"{PANEL}/{sealed.job_id}", authorization=bearer, never=[token])
    downloaded = await send(app, "GET", f"{PANEL}/{sealed.job_id}/file", authorization=bearer, never=[token])
    clear_polled = await send(app, "GET", f"{PANEL}/{clear.job_id}", authorization=bearer, never=[token])

    assert (polled.response.status_code, downloaded.response.status_code, clear_polled.response.status_code) == (200, 200, 200), f"precondition: the polls and the download answer: {polled.answer}, {downloaded.answer}, {clear_polled.answer}"
    view = polled.response.json()
    facts = {name: view.get(name, "<missing>") for name in ("file_name", "encrypted", "sealed", "sealed_recipients", "instance_key_included", "file_sha256")}
    expected = {"file_name": sealed.file_name, "encrypted": True, "sealed": True, "sealed_recipients": list(recipients), "instance_key_included": False, "file_sha256": hashlib.sha256(downloaded.response.content).hexdigest()}
    assert facts == expected, f"the view of a sealed job: {facts}"
    headers = {name: downloaded.response.headers.get(name) for name in ("content-type", "cache-control", "content-disposition")}
    assert headers == {"content-type": "application/x-tar", "cache-control": "no-store", "content-disposition": f'attachment; filename="{sealed.file_name}"'}, f"a .tar downloads as application/x-tar: {headers}"
    clear_view = clear_polled.response.json()
    assert (clear_view.get("sealed", "<missing>"), clear_view.get("sealed_recipients", "<missing>")) == (False, []), f"a job not sealed: {clear_view}"
    print_success(f"{sealed.file_name}: sealed for 2, application/x-tar")


@pytest.mark.asyncio
async def test_a_running_panel_job_reads_its_phase_sealing(app, monkeypatch, service):
    """PANEL-033 (L3-2): the phase ``sealing`` is one of a job's view: a running job in it answers 200 with that phase."""
    token = a_token()
    monkeypatch.setenv(TOKEN_VARIABLE, token)
    job = service.running("panel")
    service.known[job.job_id] = replace(job, phase="sealing", done_bytes=10, total_bytes=10)

    polled = await send(app, "GET", f"{PANEL}/{job.job_id}", authorization=f"Bearer {token}", never=[token])

    assert polled.response.status_code == 200, f"a job sealing is answered: {polled.answer}"
    assert polled.response.json()["phase"] == "sealing", f"its phase is sealing: {polled.answer}"


# =============================================================================
# PANEL-035..038 (lot L3-2 addendum): the «awaiting restore» mode refuses the start
# =============================================================================

#: The mode's refusal of a start (contract L3 §6): status and code.
AWAITING_RESTORE = (409, "backup_awaiting_restore")


def awaiting_restore(monkeypatch: pytest.MonkeyPatch, value: bool | None) -> None:
    """``config.platform.await_restore()``, which workstream H adds (H-62), answering ``value``; ``None``: no such
    function, as in this tree before H."""
    if value is None:
        monkeypatch.delattr(platform_module, "await_restore", raising=False)
    else:
        monkeypatch.setattr(platform_module, "await_restore", lambda: value, raising=False)


def recipients_unset(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> list[str]:
    return []


def one_recipient(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> list[str]:
    monkeypatch.setenv(RECIPIENTS_VARIABLE, a_recipient())
    return []


def unusable_recipients(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> list[str]:
    items = UNUSABLE_RECIPIENTS["a-private-key"]()
    monkeypatch.setenv(RECIPIENTS_VARIABLE, ",".join(items))
    return [",".join(items), *items]


def managed_without_recipients(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> list[str]:
    use_profile(monkeypatch, tmp_path, "managed")
    return []


AWAITING_CONFIGS = [
    pytest.param(recipients_unset, id="recipients-unset"),
    pytest.param(one_recipient, id="one-recipient"),
    pytest.param(unusable_recipients, id="recipients-unusable"),
    pytest.param(managed_without_recipients, id="managed-recipients-unset"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("configure", AWAITING_CONFIGS)
async def test_awaiting_restore_the_panel_start_answers_409_and_starts_no_backup(app, monkeypatch, tmp_path, service, configure):
    """PANEL-035 (L3-2, contract §6): with ``await_restore()`` true the panel's start answers 409
    ``backup_awaiting_restore``, detail exactly ``{code, message}``, and never calls ``start_backup``: a backup of an
    empty instance is never made, whatever ``LIBREFOLIO_BACKUP_RECIPIENTS`` says — unset, set, a value the server cannot
    use (the mode wins over its 503), unset in ``managed`` (the mode wins over that 503 too)."""
    print_section(f"Backup panel: awaiting restore, {configure.__name__}")
    token = a_token()
    monkeypatch.setenv(TOKEN_VARIABLE, token)
    never = configure(monkeypatch, tmp_path)
    awaiting_restore(monkeypatch, True)

    refused, calls, _given, _passwords = await panel_start(app, service, token, never=never)

    assert refused.code == AWAITING_RESTORE, f"awaiting a restore, the start is refused with 409 backup_awaiting_restore: {refused.answer}"
    detail = refused.response.json()["detail"]
    assert set(detail) == {"code", "message"} and isinstance(detail["message"], str) and detail["message"], f"the detail is exactly {{code, message}}: {detail}"
    assert calls == [], f"no backup is ever started while awaiting a restore: {calls}"
    print_success(f"{configure.__name__}: 409 backup_awaiting_restore, start_backup never called")


@pytest.mark.asyncio
async def test_the_mode_is_read_at_each_request_and_its_absence_is_never_awaiting(app, monkeypatch, service):
    """PANEL-036 (L3-2): the start looks ``await_restore`` up at each request on the same app: absent (this tree before
    workstream H) → 202, the start of before; true → 409 ``backup_awaiting_restore`` and no call; false → 202 again,
    one run of origin ``panel``."""
    token = a_token()
    monkeypatch.setenv(TOKEN_VARIABLE, token)
    answers: dict[str, tuple[tuple[int, str | None], list[tuple[str, str]]]] = {}
    for label, value in (("absent", None), ("true", True), ("false", False)):
        awaiting_restore(monkeypatch, value)
        exchange, calls, _given, _passwords = await panel_start(app, service, token)
        answers[label] = ((exchange.response.status_code, exchange.code[1]), calls)

    started = ((202, None), [("start_backup", "panel")])
    assert answers["absent"] == started, f"no await_restore: never awaiting, the start of before: {answers['absent']}"
    assert answers["true"] == (AWAITING_RESTORE, []), f"await_restore() true: 409 backup_awaiting_restore, no call: {answers['true']}"
    assert answers["false"] == started, f"await_restore() false, read at this request: the start of before: {answers['false']}"
    print_success("absent 202, true 409, false 202: read at each request")


@pytest.mark.asyncio
async def test_awaiting_restore_the_poll_download_and_delete_keep_working(app, monkeypatch, service):
    """PANEL-037 (L3-2): the mode refuses only the start. The panel's done job is polled (200), downloaded (200, its
    bytes) and deleted (204) with the calls of before, while ``await_restore()`` is true."""
    token = a_token()
    monkeypatch.setenv(TOKEN_VARIABLE, token)
    bearer = f"Bearer {token}"
    job = service.done("panel")
    archive = service.archive(job).read_bytes()
    awaiting_restore(monkeypatch, True)

    polled, poll_calls = await with_calls(service, send(app, "GET", f"{PANEL}/{job.job_id}", authorization=bearer, never=[token]))
    downloaded, file_calls = await with_calls(service, send(app, "GET", f"{PANEL}/{job.job_id}/file", authorization=bearer, never=[token]))
    deleted, delete_calls = await with_calls(service, send(app, "DELETE", f"{PANEL}/{job.job_id}", authorization=bearer, never=[token]))

    assert (polled.response.status_code, poll_calls) == (200, [("get_job", job.job_id)]), f"the poll answers as before: {polled.answer}, {poll_calls}"
    assert (downloaded.response.status_code, downloaded.response.content, file_calls) == (200, archive, [("get_job", job.job_id), ("job_archive", job.job_id)]), f"the download answers as before: {downloaded.answer}, {file_calls}"
    assert (deleted.response.status_code, delete_calls) == (204, [("get_job", job.job_id), ("delete_job", job.job_id)]), f"the deletion answers as before: {deleted.answer}, {delete_calls}"
    print_success("awaiting restore: poll 200, download 200, delete 204")


def test_openapi_documents_409_backup_awaiting_restore_on_the_panel_start():
    """PANEL-038 (L3-2): the panel's start documents its 409 ``backup_awaiting_restore`` (beside ``backup_busy``)."""
    description = backup_app().openapi()["paths"][PANEL]["post"]["responses"].get("409", {}).get("description", "")
    assert "backup_awaiting_restore" in description and "backup_busy" in description, f"the start's 409 names backup_awaiting_restore and backup_busy: {description!r}"

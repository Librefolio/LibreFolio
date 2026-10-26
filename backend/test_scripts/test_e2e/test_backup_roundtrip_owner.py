"""
A backup restored from the app on a MANAGED instance, with the owner's choice, across the real start sequence (workstream B,
lot B5-1f; contract B5-1). Selector: ``e2e backup-roundtrip-owner``.

On an instance a hosting provider runs (``LIBREFOLIO_PROFILE=managed``) the owner is the person whose address is
``LIBREFOLIO_ADMIN_EMAIL``. A backup an administrator uploads may come from anywhere, so the restore names the account of
the backup that becomes the owner's, and the first start on the restored data (``pending-restore`` … ``admin-bootstrap``,
``restore-commit``, ``restore-owner``, ``owner-sync``) gives that account the owner's address, makes its password unusable
and sends the owner a link to choose a new one. With no SMTP the link goes to the instance's log only (``link_only``).

1. Happy path, ``link_only``: the target's administrator uploads the backup; the check offers ``owner_choice``; a
   confirmation without an owner is 409 ``owner_choice_required``, one with the backup's administrator is 202; the restart
   makes the process exit; a new process with the same environment applies and commits it. The chosen account has the
   owner's address, is an active administrator and the only owner, its old password (the backup's author knew it) is
   refused, a session of before the restore is refused, the link is in the child's log and in no other place (the status,
   the state file, the restore's folder, the data directory but its logs), it lets the owner choose a password once and
   sign in; the state records ``link_only`` and the chosen id, never the link.
2. At most once: one more start of the same instance calls nothing again: no new link in the log, the state file
   unchanged, the owner's password still works.
3. Fail closed: the owner's address is changed, between the confirmation and the start, to one another account of the
   backup holds. The assignment is refused (``error:EMAIL_TAKEN``), the instance serves no data (423 on a user route,
   ``restore_interrupted_reason`` ``owner_assignment``), until the cause is removed and ``backup pending --recover owner``
   clears the error: the next start gives the owner the account and its link.
4. B5-1j, a restore from the COMMAND LINE (the same managed instance, the real CLI, no owner named by anybody) picks the owner
   itself. "Anna": the backup's only active administrator, flagged by its author as the instance's owner, holds
   ``old@example.com``; the instance's owner is ``new@example.com``. The CLI names her by username and prints no address; the
   restore is confirmed; the server restarts; Anna holds the owner's address, is the only flagged account, an active
   administrator; her old password and a session of before are refused; a password-reset link exists ONLY in the child's log
   (``link_only``: no SMTP), spends once, and is never in the state, the data directory's files, the API or the CLI's output.
5. B5-1j, nobody can be picked: two flagged administrators (the unique index of a crafted copy dropped), or a flag on an
   ordinary account only. The restore is confirmed all the same, the state records no owner and the outcome ``none``, the
   CLI says there is no owner and gives ``./dev.py user reassign-owner <username>``, the instance serves, nobody is flagged,
   no account is closed, no link is written, and the lines about the owner in the CLI's output and in the logs name no
   account and no address.

The instances are real servers: ``uvicorn backend.app.main:app`` in a child process in test mode on a data directory of the
test, listening on a Unix socket in a short folder under ``/tmp`` (as ``test_backup_roundtrip_l3.py`` does), never on a
TCP port: the lane's port and server are never touched. Each child runs with ``test_backup_roundtrip.child_env`` (none of the
lane's ``LIBREFOLIO_*`` variables, coverage or secrets) plus the managed profile's: ``LIBREFOLIO_PROFILE=managed``, the
owner's address and the setup administrator's name, a lane id (the managed profile refuses test mode without one, H-46), a
public address, the scheduler off, no SMTP. The source is populated as the B3 round trip populates it (``populate_mock_data
--force`` in a child) and its backup made by ``jobs.run_backup``; the author's flag ``is_instance_owner`` is put on an
ordinary account of it. The target's first administrator is the initial administrator of ``admin-bootstrap``: its setup
link is read from the child's log, in the test only (it is a secret: never printed, never in a message), and spent on
``POST /auth/setup``, which answers with the session the upload needs. Every wait polls a condition with a deadline,
waiting on the server process itself between two polls, so a server that dies ends the wait at once.

PURE: data directories, archives and sockets of the test; the lane's data directory, database and server are never read
or written. POSIX only (Unix sockets, process groups).
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import secrets
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterator, Mapping
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import pytest

from backend.app.services.platform.instance_backup import jobs
from backend.app.services.platform.instance_backup.paths import DATABASE_ENTRY, restore_dir
from backend.app.utils.runtime.version import get_git_version
from backend.test_scripts.test_e2e import test_backup_roundtrip as b3
from backend.test_scripts.test_services import test_backup_staging as cases
from backend.test_scripts.test_utils import print_section, print_success

# Autouse (the module fixture of ``test_backup_staging.py``, re-exported as ``test_backup_roundtrip.py`` does): this process's
# production data directory is a folder of the test that must stay absent.
configured_data_dir = cases.configured_data_dir

pytestmark = pytest.mark.skipif(os.name == "nt", reason="Unix sockets and process groups are POSIX only")

API = "/api/v1"
HEALTH = f"{API}/system/health"
INSTANCE = f"{API}/system/instance"
LOGIN = f"{API}/auth/login"
ME = f"{API}/auth/me"
SETUP = f"{API}/auth/setup"
PASSWORD_RESET = f"{API}/auth/password-reset"
RESTORE = f"{API}/backup/restore"
RESTORE_UPLOAD = f"{RESTORE}/upload"
RESTORE_STAGE = f"{RESTORE}/stage"
RESTORE_RESTART = f"{RESTORE}/restart"
RESTORE_STATUS = f"{RESTORE}/status"

#: A short folder for the sockets: an AF_UNIX path holds about 100 bytes, fewer than pytest's tmp_path may take.
SHORT_TMP = "/tmp" if os.path.isdir("/tmp") else tempfile.gettempdir()
SOCKET_PATH_LIMIT = 100
BASE_URL = "http://owner-roundtrip.test"
#: The instance's public address: the owner's reset link is built on it.
PUBLIC_URL = "https://owner-roundtrip.example.test"
#: Seconds a server may take to start (imports, migrations, a restore applied), a check to end, a request to be answered,
#: a server to exit after a SIGTERM: on a loaded machine. Every wait still ends.
START_SECONDS = 300.0
CHECK_SECONDS = 900.0
REQUEST_SECONDS = 120.0
EXIT_SECONDS = 60.0
LOG_SECONDS = 30.0
#: How long the test waits on the server process between two polls: the wait ends at once if the process exits.
POLL_SECONDS = 0.2
TAIL = 4000

#: The owner's address (``LIBREFOLIO_ADMIN_EMAIL``): held by nobody in the backup. The initial administrator's name.
OWNER_EMAIL = "owner@b5f-owner.example.com"
SETUP_USERNAME = "target_setup_admin"
SETUP_PASSWORD = "Target-Setup-Pass-2026!"
#: The password the owner chooses with the link.
OWNER_NEW_PASSWORD = "Owner-Chosen-Pass-2026!"
#: The backup's administrator, as populate_mock_data writes it: the account the owner chooses, whose password its author
#: (the test) knows. The ordinary account that carries the author's owner flag, and another that holds a known address.
SOURCE_ADMIN = "e2e_test_admin"
SOURCE_ADMIN_PASSWORD = "E2eAdminPass123!"
FLAGGED_USER = "e2e_test_user"
OTHER_USER = "e2e_user_alice"
OTHER_USER_PASSWORD = "AlicePass123!"
OTHER_USER_EMAIL = "alice@test.example.com"

#: The log lines that hold a link, whose token the test reads (never prints).
SETUP_LINK_LINE = "Setup link of the initial administrator"
RESET_LINK_LINE = "Password-reset link for the instance owner"
OWNER_ASSIGNED_LINE = "The owner of the restored data is set"
_TOKEN = re.compile(r"token=([A-Za-z0-9_\-]+)")
#: What a log tail quoted by a message hides: the token of a link.
_REDACT = re.compile(r"(token=)[A-Za-z0-9_%\-]+")


def redacted(text: str) -> str:
    """``text`` without the token of any link."""
    return _REDACT.sub(r"\1<redacted>", text)


# =============================================================================
# A server of the test
# =============================================================================


def detail(response: httpx.Response) -> dict[str, Any]:
    """The ``detail`` of an error body, or ``{}``."""
    try:
        found = response.json().get("detail")
    except (ValueError, AttributeError):
        return {}
    return found if isinstance(found, dict) else {"text": found}


def code_of(response: httpx.Response) -> str | None:
    """The code an error body carries (``code`` of the backup routes, ``error_code`` of the accounts')."""
    found = detail(response)
    return found.get("code") or found.get("error_code")


def shown(response: httpx.Response) -> str:
    return redacted(f"{response.request.method} {response.request.url.path} → {response.status_code} {response.text[:TAIL]}")


def session_of(response: httpx.Response) -> str | None:
    """The value of the session cookie a response sets, or ``None``."""
    for header in response.headers.get_list("set-cookie"):
        match = re.match(r"session=([^;]*)", header)
        if match and match.group(1):
            return match.group(1)
    return None


class Server:
    """``uvicorn backend.app.main:app`` on a Unix socket, in test mode on ``data_dir``: each ``start`` a new process."""

    def __init__(self, name: str, data_dir: Path, socket_dir: Path, log_dir: Path) -> None:
        self.name = name
        self.data_dir = data_dir
        self.socket_dir = socket_dir
        self.log_dir = log_dir
        self.process: subprocess.Popen[bytes] | None = None
        self.socket: Path | None = None
        self.log_path: Path | None = None
        self.starts = 0
        self.variables: dict[str, str] = {}
        #: Owns this process tree for the managed profile (H-46): the same for every start of this server.
        self.lane_id = secrets.token_hex(16)

    @property
    def running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def environment(self, variables: Mapping[str, str]) -> dict[str, str]:
        """The environment of a child: the test's, without the lane's, plus the managed profile's and ``variables``."""
        env = b3.child_env(self.data_dir)
        env.update(LIBREFOLIO_NO_SCHEDULER="1", LIBREFOLIO_TEST_LANE_ID=self.lane_id, LIBREFOLIO_PUBLIC_URL=PUBLIC_URL, **variables)
        return env

    def start(self, variables: Mapping[str, str]) -> None:
        """A new process with ``variables`` beside the test's environment, once it answers its health route."""
        assert not self.running, f"barrier: {self.name}'s previous process still runs"
        self.starts += 1
        self.variables = dict(variables)
        self.socket = self.socket_dir / f"{self.name[:6]}-{self.starts}.sock"
        assert len(os.fsencode(self.socket)) < SOCKET_PATH_LIMIT, f"barrier: the socket path {self.socket} is too long for AF_UNIX"
        self.log_path = self.log_dir / f"{self.name}-{self.starts}.log"
        command = [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--uds", str(self.socket), "--lifespan", "on", "--log-level", "warning"]
        with self.log_path.open("wb") as log:
            self.process = subprocess.Popen(command, cwd=b3.PROJECT_ROOT, env=self.environment(variables), stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        deadline = time.monotonic() + START_SECONDS
        problem = "its socket was never created"
        while time.monotonic() < deadline:
            if self.socket.exists():
                try:
                    with self._client(10.0) as client:
                        response = client.get(BASE_URL + HEALTH)
                    if response.status_code == 200:
                        return
                    problem = f"the health route answered {response.status_code}"
                except httpx.HTTPError as error:
                    problem = repr(error)
            self.keeps_running(POLL_SECONDS, "starting")
        pytest.fail(f"{self.name} did not answer within {START_SECONDS} s ({problem}):\n{self.output()}")

    def ensure_started(self) -> None:
        """Start the server again with the variables of its last start, if it is not running: a test that finds it stopped
        by another one does not depend on the order they run in."""
        if not self.running:
            self.start(self.variables)

    def _client(self, timeout: float) -> httpx.Client:
        assert self.socket is not None
        return httpx.Client(transport=httpx.HTTPTransport(uds=str(self.socket)), timeout=timeout)

    def call(self, method: str, path: str, *, cookie: str | None = None, **kwargs: Any) -> httpx.Response:
        """One request; with ``cookie``, as the session it names."""
        headers = dict(kwargs.pop("headers", {}))
        if cookie is not None:
            headers["Cookie"] = f"session={cookie}"
        with self._client(REQUEST_SECONDS) as client:
            return client.request(method, BASE_URL + path, headers=headers, **kwargs)

    def keeps_running(self, seconds: float, while_doing: str) -> None:
        """Wait ``seconds`` on the process, and fail if it exits: it was not meant to while ``while_doing``."""
        assert self.process is not None
        try:
            self.process.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            return
        pytest.fail(f"{self.name} exited with status {self.process.returncode} while {while_doing}:\n{self.output()}")

    def exits(self, why: str) -> int:
        """Wait for the process to exit by itself; its status."""
        assert self.process is not None
        try:
            return self.process.wait(timeout=EXIT_SECONDS)
        except subprocess.TimeoutExpired:
            pytest.fail(f"{self.name} still runs {EXIT_SECONDS} s after {why}:\n{self.output()}")

    def stop(self) -> None:
        """SIGTERM, as a supervisor stops it, and wait for the exit."""
        if self.running:
            assert self.process is not None
            self.process.send_signal(signal.SIGTERM)
            self.exits("a SIGTERM")

    def cleanup(self) -> None:
        """Kill the process with its whole group if it still runs, and reap it."""
        if self.process is not None:
            if self.process.poll() is None:
                with contextlib.suppress(ProcessLookupError, PermissionError):
                    os.killpg(self.process.pid, signal.SIGKILL)
            with contextlib.suppress(subprocess.TimeoutExpired):
                self.process.wait(timeout=EXIT_SECONDS)

    def output(self) -> str:
        """The tail of the current log, without any link's token."""
        text = self.log_path.read_text(encoding="utf-8", errors="replace") if self.log_path is not None and self.log_path.exists() else ""
        return f"--- {self.log_path}\n{redacted(text)[-TAIL:]}"

    # -- the instance's log: the one place a link may be -------------------------------------------------------------

    def logs(self) -> list[Path]:
        """The log of every process of this server, in the order they ran."""
        return sorted(self.log_dir.glob(f"{self.name}-*.log"), key=lambda path: int(path.stem.rsplit("-", 1)[1]))

    def lines_with(self, marker: str, *, only_last: bool = False) -> list[str]:
        """The log lines holding ``marker``, of every process (or of the last one)."""
        paths = self.logs()[-1:] if only_last else self.logs()
        return [line for path in paths for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if marker in line]

    def token_in_log(self, marker: str, *, only_last: bool = True) -> str | None:
        """The token of the link the last line holding ``marker`` writes, or ``None``. A secret: never printed."""
        for line in reversed(self.lines_with(marker, only_last=only_last)):
            found = _TOKEN.search(line)
            if found:
                return found.group(1)
        return None

    def wait_for_token(self, marker: str) -> str:
        """The token of the link ``marker`` names, once the log has it (a background delivery writes it after the start)."""
        deadline = time.monotonic() + LOG_SECONDS
        while True:
            token = self.token_in_log(marker)
            if token is not None:
                return token
            if time.monotonic() >= deadline:
                pytest.fail(f"the log of {self.name} has no link after {marker!r} within {LOG_SECONDS} s:\n{self.output()}")
            self.keeps_running(POLL_SECONDS, f"waiting for {marker!r}")


@contextlib.contextmanager
def server(name: str, data_dir: Path, socket_dir: Path, log_dir: Path) -> Iterator[Server]:
    found = Server(name, data_dir, socket_dir, log_dir)
    try:
        yield found
    finally:
        found.cleanup()


@pytest.fixture(scope="module")
def socket_dir() -> Iterator[Path]:
    directory = Path(tempfile.mkdtemp(prefix="lf-own-", dir=SHORT_TMP))
    yield directory
    shutil.rmtree(directory, ignore_errors=True)


# =============================================================================
# The source and its backup
# =============================================================================


@dataclass(frozen=True)
class SourceBackup:
    """The populated source (stopped), its instance key, its archive, and the ids of the accounts the tests name."""

    root: Path
    instance_key: str
    archive: Path
    admin_id: int
    flagged_id: int
    other_id: int
    users: int


def rows(database: Path, sql: str, *params: Any) -> list[tuple]:
    with closing(cases.read_only(database)) as conn:
        return conn.execute(sql, params).fetchall()


@pytest.fixture(scope="module")
def source_backup(tmp_path_factory) -> SourceBackup:
    """The project's mock data in a new instance of the test, with the owner flag of «whoever prepared the backup» on an
    ordinary account, a first start, then its archive."""
    base = tmp_path_factory.mktemp("owner-source")
    root = base / "source"
    root.mkdir()
    b3.populate(root)
    b3.assert_populated(root / DATABASE_ENTRY)
    started = b3.start(root, b3.FIRST_START)
    assert started.returncode == 0, f"precondition: the source's first start: {b3.shown(started)}"
    database = root / DATABASE_ENTRY
    with closing(sqlite3.connect(database)) as conn:
        conn.execute("UPDATE users SET is_instance_owner = 1 WHERE username = ?", (FLAGGED_USER,))
        conn.commit()
    ids = {name: rows(database, "SELECT id FROM users WHERE username = ?", name)[0][0] for name in (SOURCE_ADMIN, FLAGGED_USER, OTHER_USER)}
    assert rows(database, "SELECT username FROM users WHERE is_instance_owner = 1") == [(FLAGGED_USER,)], "precondition: the backup's author flagged one ordinary account"
    assert rows(database, "SELECT count(*) FROM users WHERE is_superuser = 1 AND is_active = 1")[0][0] == 1, "precondition: the backup has one active administrator"
    assert rows(database, "SELECT count(*) FROM users WHERE lower(email) = lower(?)", OWNER_EMAIL)[0][0] == 0, "precondition: nobody in the backup holds the owner's address"
    key_file = root / "secrets" / "instance.key"
    instance_key = key_file.read_text(encoding="utf-8").strip() if key_file.is_file() else secrets.token_urlsafe(32)
    with pytest.MonkeyPatch.context() as patch:
        configured = cases.configure(patch, base / "configured-data-dir")
        try:
            job, folder = jobs.run_backup(origin="cli", data_dir=root)
        finally:
            get_git_version.cache_clear()
    assert not configured.exists(), f"the backup wrote in the configured data directory: {cases.listing(configured)}"
    assert (job.status, job.error_code) == ("done", None) and job.file_name, f"precondition: the source is archived: {job}"
    assert not b3.production_of(root).exists(), "a child wrote in its production data directory"
    return SourceBackup(
        root=root,
        instance_key=instance_key,
        archive=folder / job.file_name,
        admin_id=ids[SOURCE_ADMIN],
        flagged_id=ids[FLAGGED_USER],
        other_id=ids[OTHER_USER],
        users=rows(database, "SELECT count(*) FROM users")[0][0],
    )


def managed_variables(source: SourceBackup, *, owner_email: str = OWNER_EMAIL) -> dict[str, str]:
    """The variables of a managed instance whose owner is ``owner_email``: no SMTP (so the owner's link is only in the log),
    the source's instance key (every secret of the backup readable)."""
    return {
        "LIBREFOLIO_PROFILE": "managed",
        "LIBREFOLIO_ADMIN_EMAIL": owner_email,
        "LIBREFOLIO_ADMIN_USERNAME": SETUP_USERNAME,
        "LIBREFOLIO_INSTANCE_KEY": source.instance_key,
    }


# =============================================================================
# The target and its restore
# =============================================================================


def signed_in(instance: Server, username: str, password: str) -> httpx.Response:
    return instance.call("POST", LOGIN, json={"username": username, "password": password})


def first_session(instance: Server) -> str:
    """The first administrator's session on a fresh managed target: the initial administrator of ``admin-bootstrap`` waits
    for its setup; its link is in the instance's log (read here, never printed), and spending it signs the administrator in."""
    token = instance.wait_for_token(SETUP_LINK_LINE)
    response = instance.call("POST", SETUP, json={"token": token, "new_password": SETUP_PASSWORD})
    assert response.status_code == 200, f"precondition: the setup link opens the initial administrator's session: {shown(response)}"
    cookie = session_of(response)
    assert cookie, "precondition: the setup answers with a session"
    me = instance.call("GET", ME, cookie=cookie)
    assert me.status_code == 200 and me.json()["user"]["is_superuser"] is True, f"precondition: the session is an administrator's: {shown(me)}"
    return cookie


def checked(instance: Server, cookie: str, archive: Path) -> dict[str, Any]:
    """Upload ``archive`` and check it; the finished check."""
    uploaded = instance.call("PUT", RESTORE_UPLOAD, cookie=cookie, content=archive.read_bytes(), headers={"Content-Type": "application/octet-stream"})
    assert uploaded.status_code == 201, f"the administrator uploads the backup: {shown(uploaded)}"
    staged = instance.call("POST", RESTORE_STAGE, cookie=cookie, json={"upload_id": uploaded.json()["upload_id"]})
    assert staged.status_code == 202, f"the check starts: {shown(staged)}"
    stage_id = staged.json()["stage_id"]
    deadline = time.monotonic() + CHECK_SECONDS
    while True:
        response = instance.call("GET", f"{RESTORE_STAGE}/{stage_id}", cookie=cookie)
        assert response.status_code == 200, f"the check is read: {shown(response)}"
        body = response.json()
        if body["status"] in ("done", "failed"):
            assert (body["status"], body.get("error_code")) == ("done", None), f"the check ends with a report: {body}"
            return body
        if time.monotonic() >= deadline:
            pytest.fail(f"the check still runs after {CHECK_SECONDS} s: {body}")
        instance.keeps_running(POLL_SECONDS, "the check")


def restarted(instance: Server, cookie: str) -> None:
    """Ask the restart the restore needs, and wait for the process to exit."""
    response = instance.call("POST", RESTORE_RESTART, cookie=cookie)
    assert response.status_code == 202, f"the administrator asks the restart: {shown(response)}"
    instance.exits("the restart the administrator asked")


@dataclass
class Flow:
    """What the restore of the backup on a managed target did, as the module's tests assert it."""

    instance: Server
    root: Path
    variables: dict[str, str]
    #: The initial administrator's session, from before the restore.
    old_cookie: str
    check: dict[str, Any]
    #: The confirmation with no owner, and with the backup's administrator.
    refused: httpx.Response
    confirmed: httpx.Response
    #: The state file of the restore as the first start left it, and the restore's status read from the API.
    state: dict[str, Any]
    status: httpx.Response
    #: The token of the owner's link, read from the log (a secret).
    reset_token: str
    #: The owner's use of the link, a second use, the first sign-in with the password chosen, and its session.
    reset: httpx.Response
    reset_again: httpx.Response
    owner_login: httpx.Response
    owner_cookie: str | None


def users_of(root: Path) -> dict[str, dict[str, Any]]:
    """The accounts of the instance at ``root`` by name, read-only: what the restore left."""
    found = rows(root / DATABASE_ENTRY, "SELECT id, username, email, is_superuser, is_active, is_instance_owner FROM users")
    return {row[1]: {"id": row[0], "email": row[2], "is_superuser": bool(row[3]), "is_active": bool(row[4]), "is_instance_owner": bool(row[5])} for row in found}


def walk_json_keys(found: Any) -> set[str]:
    """Every key of a JSON value, however deep."""
    if isinstance(found, dict):
        return set(found) | {key for value in found.values() for key in walk_json_keys(value)}
    if isinstance(found, list):
        return {key for value in found for key in walk_json_keys(value)}
    return set()


def holders_of(root: Path, secret: str, *, in_logs: bool = False) -> list[str]:
    """The files of the data directory whose bytes hold ``secret``: all but the instance's logs, the one place the link is
    meant to be (``in_logs``: the files of the logs only)."""
    needle = secret.encode()
    logs = root / "logs"
    found = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink() and ((logs in path.parents) == in_logs):
            try:
                if needle in path.read_bytes():
                    found.append(path.relative_to(root).as_posix())
            except OSError:
                continue
    return found


@pytest.fixture(scope="module")
def flow(source_backup, tmp_path_factory, socket_dir) -> Iterator[Flow]:
    """The whole restore of the first scenario, run once: a fresh managed target, its administrator's session, the check,
    the confirmation without and with the owner's choice, the restart, the start that applies and commits it, and the
    owner's use of the link. The server is left running on the committed data."""
    base = tmp_path_factory.mktemp("owner-target")
    root = base / "target"
    root.mkdir()
    variables = managed_variables(source_backup)
    with server("target", root, socket_dir, base) as target:
        target.start(variables)
        cookie = first_session(target)
        check = checked(target, cookie, source_backup.archive)
        refused = target.call("POST", f"{RESTORE_STAGE}/{check['stage_id']}/confirm", cookie=cookie, json={})
        confirmed = target.call("POST", f"{RESTORE_STAGE}/{check['stage_id']}/confirm", cookie=cookie, json={"owner_user_id": source_backup.admin_id})
        assert confirmed.status_code == 202, f"precondition: the confirmation with the owner's account: {shown(confirmed)}"
        restarted(target, cookie)

        # A new process, the same variables: the restore applied and committed, the owner assigned.
        target.start(variables)
        state = b3.restore_state(root)
        assert state is not None, "precondition: the restore left its state"
        token = target.wait_for_token(RESET_LINK_LINE)
        reset = target.call("POST", PASSWORD_RESET, json={"token": token, "new_password": OWNER_NEW_PASSWORD})
        reset_again = target.call("POST", PASSWORD_RESET, json={"token": token, "new_password": OWNER_NEW_PASSWORD + "x"})
        owner_login = signed_in(target, SOURCE_ADMIN, OWNER_NEW_PASSWORD)
        owner_cookie = session_of(owner_login)
        # The restore ended every session: the status is read with the owner's, the first administrator of the restored data.
        status = target.call("GET", RESTORE_STATUS, cookie=owner_cookie)
        yield Flow(target, root, variables, cookie, check, refused, confirmed, state, status, token, reset, reset_again, owner_login, owner_cookie)
    assert not b3.production_of(root).exists(), "a child wrote in its production data directory"


# =============================================================================
# 1. The happy path, link_only
# =============================================================================


def test_the_check_offers_the_owner_s_choice_and_a_confirmation_without_one_is_refused(flow, source_backup):
    """B5-1: on a managed instance the administrator's check carries ``owner_choice`` (required, the owner's address, the
    backup's accounts as candidates, among them the administrator, none holding the owner's address, so nothing forced);
    a confirmation that names no account is 409 ``owner_choice_required`` and confirms nothing; with the account, 202."""
    print_section("B5-1f 1a The owner's choice")
    choice = flow.check["report"]["owner_choice"]
    assert choice is not None and choice["required"] is True, f"the check asks the owner's choice: {choice}"
    assert choice["owner_email"].lower() == OWNER_EMAIL, "the choice shows the owner's address"
    assert choice["forced_user_id"] is None, f"nobody holds the owner's address: nothing is forced: {choice['forced_user_id']}"
    candidates = {candidate["user_id"]: candidate for candidate in choice["candidates"]}
    assert source_backup.admin_id in candidates, f"the backup's administrator is a candidate: {sorted(candidates)}"
    assert candidates[source_backup.admin_id]["administrator"] is True and candidates[source_backup.admin_id]["username"] == SOURCE_ADMIN, "it is an active administrator"
    assert not [candidate for candidate in choice["candidates"] if candidate["owner_email"]], "no candidate holds the owner's address"
    assert (flow.refused.status_code, code_of(flow.refused)) == (409, "owner_choice_required"), f"no account named: {shown(flow.refused)}"
    assert (flow.confirmed.status_code, flow.confirmed.json()["state"]) == (202, "pending"), f"the account named: {shown(flow.confirmed)}"
    assert flow.confirmed.json()["confirmed_via"] == "admin", f"confirmed from the app: {flow.confirmed.json()}"
    print_success("owner_choice offered, 409 owner_choice_required without an account, 202 with the administrator's")


def test_a_restore_from_the_app_gives_the_owner_the_chosen_account_and_the_link_only_in_the_log(flow, source_backup):
    """B5-1, the first start on the restored data: committed; the chosen account holds the owner's address, is an active
    administrator and the only owner (the author's flag on an ordinary account is gone); its old password is refused, as is
    a session of before the restore; the others' passwords work. The link is in the child's log and nowhere else: not in the
    status, not in the state file, not in the restore's folder, not in any file of the data directory but the logs; the state
    records ``link_only`` and the chosen id and no link key; the owner spends the link once, chooses a password and signs in."""
    print_section("B5-1f 1b The owner's account, the link, the password")
    instance, root = flow.instance, flow.root
    instance.ensure_started()
    assert flow.status.status_code == 200 and flow.status.json()["state"] == "committed", f"committed by the new process: {shown(flow.status)}"
    assert flow.status.json()["stage_id"] == flow.check["stage_id"], "the restore of the administrator's check"
    state = b3.restore_state(root)
    assert state is not None and state["status"] == "committed", f"committed: {state}"
    assert (state["owner_user_id"], state["owner_outcome"], state["confirmed_via"]) == (source_backup.admin_id, "link_only", "admin"), f"the state records the owner's account and where the link went: {state}"
    assert not {"reset_path", "link", "token", "reset_link"} & walk_json_keys(state), f"the state keeps no link: {sorted(walk_json_keys(state))}"

    users = users_of(root)
    assert len(users) == source_backup.users, f"the accounts of the backup, and no other: {len(users)} of {source_backup.users}"
    owner = users[SOURCE_ADMIN]
    assert (owner["id"], (owner["email"] or "").lower(), owner["is_superuser"], owner["is_active"], owner["is_instance_owner"]) == (source_backup.admin_id, OWNER_EMAIL, True, True, True), "the chosen account is the active administrator and owner with the owner's address"
    assert [name for name, row in users.items() if row["is_instance_owner"]] == [SOURCE_ADMIN], "the only owner is the chosen account: the author's flag on another is gone"
    assert SETUP_USERNAME not in users, "the target's initial administrator is not in the restored data"

    # The old password (the author's), a session of before the restore.
    old = signed_in(instance, SOURCE_ADMIN, SOURCE_ADMIN_PASSWORD)
    assert old.status_code in (400, 401, 403) and session_of(old) is None, f"the author's password opens nothing: {shown(old)}"
    before = instance.call("GET", ME, cookie=flow.old_cookie)
    assert before.status_code == 401, f"a session of before the restore is refused: {shown(before)}"
    other = signed_in(instance, OTHER_USER, OTHER_USER_PASSWORD)
    assert other.status_code == 200, f"another account of the backup signs in with its password: {shown(other)}"

    # The link: in the log, and in no other place.
    assert len(instance.lines_with(RESET_LINK_LINE)) == 1, f"one link written for the owner: {len(instance.lines_with(RESET_LINK_LINE))}"
    assert len(instance.lines_with(OWNER_ASSIGNED_LINE)) == 1, "one start said the owner was set"
    secret = flow.reset_token
    status_now = instance.call("GET", RESTORE_STATUS, cookie=flow.owner_cookie)
    assert secret not in flow.status.text and secret not in status_now.text, "the restore's status holds no link"
    assert secret not in json.dumps(flow.check), "the check's report holds no link"
    assert secret not in (restore_dir(root) / "restore.json").read_text(encoding="utf-8"), "the state file holds no link"
    assert holders_of(root, secret, in_logs=True), "barrier: the instance's own log folder holds the link (so the search below can find one)"
    assert holders_of(root, secret) == [], f"no file of the data directory but the logs holds the link: {holders_of(root, secret)}"

    # The link works, once, and the owner signs in with the password it chose.
    assert flow.reset.status_code == 200, f"the link lets the owner choose a password: {shown(flow.reset)}"
    assert (flow.reset_again.status_code, code_of(flow.reset_again)) == (400, "TOKEN_INVALID"), f"a link is spent once: {shown(flow.reset_again)}"
    assert flow.owner_login.status_code == 200 and flow.owner_login.json()["user"]["email"].lower() == OWNER_EMAIL, f"the owner signs in with the password chosen: {shown(flow.owner_login)}"
    assert flow.owner_login.json()["user"]["is_superuser"] is True, "as an administrator"
    still_old = signed_in(instance, SOURCE_ADMIN, SOURCE_ADMIN_PASSWORD)
    assert still_old.status_code in (400, 401, 403), f"the author's password is still refused: {shown(still_old)}"
    print_success("owner assigned, link only in the log, spent once, the owner signed in; old password and old session refused")


# =============================================================================
# 2. At most once
# =============================================================================


def test_another_start_of_the_restored_instance_calls_the_owner_assignment_no_more(flow):
    """A start of the same instance after the owner was given the account: the restore-owner step has nothing to do, so no
    new link is written (the count of lines with a link, over every process, is the same), the state file is unchanged
    (compared as JSON), and the owner's password still opens the instance."""
    print_section("B5-1f 2 At most once")
    instance, root = flow.instance, flow.root
    instance.ensure_started()
    state_before = json.loads((restore_dir(root) / "restore.json").read_text(encoding="utf-8"))
    links_before, assigned_before = len(instance.lines_with(RESET_LINK_LINE)), len(instance.lines_with(OWNER_ASSIGNED_LINE))
    assert (links_before, assigned_before) == (1, 1), f"precondition: the first start wrote the owner's link: {links_before}, {assigned_before}"
    owner_before = users_of(root)[SOURCE_ADMIN]
    instance.stop()
    instance.start(flow.variables)
    state_after = json.loads((restore_dir(root) / "restore.json").read_text(encoding="utf-8"))
    assert state_after == state_before, "the state file is unchanged by another start"
    assert len(instance.lines_with(RESET_LINK_LINE)) == links_before, "no new link written"
    assert len(instance.lines_with(OWNER_ASSIGNED_LINE)) == assigned_before, "the assignment is not called again"
    assert users_of(root)[SOURCE_ADMIN] == owner_before, "the owner's account is unchanged"
    signed = signed_in(instance, SOURCE_ADMIN, OWNER_NEW_PASSWORD)
    assert signed.status_code == 200, f"the owner's password still works: {shown(signed)}"
    print_success("another start: no new link, state unchanged, the owner signs in")


# =============================================================================
# 3. Fail closed
# =============================================================================


def test_an_owner_assignment_that_is_refused_serves_no_data_until_it_is_recovered(source_backup, tmp_path, socket_dir):
    """The owner's address changes (the hosting panel updates ``LIBREFOLIO_ADMIN_EMAIL``) between the confirmation and the
    start, to one another account of the backup holds: A's assignment answers ``EMAIL_TAKEN``. The start records
    ``error:EMAIL_TAKEN``; the instance serves no restored data (423 on a user route, ``restore_interrupted_reason`` is
    ``owner_assignment``) and writes no link. With the cause gone, ``backup pending --recover owner`` clears the error and
    the next start gives the owner the account and its link: the instance serves again."""
    print_section("B5-1f 3 Fail closed, then recovered")
    root = tmp_path / "target"
    root.mkdir()
    variables = managed_variables(source_backup)
    taken = managed_variables(source_backup, owner_email=OTHER_USER_EMAIL)
    with server("failed", root, socket_dir, tmp_path) as target:
        target.start(variables)
        cookie = first_session(target)
        check = checked(target, cookie, source_backup.archive)
        confirmed = target.call("POST", f"{RESTORE_STAGE}/{check['stage_id']}/confirm", cookie=cookie, json={"owner_user_id": source_backup.admin_id})
        assert confirmed.status_code == 202, f"precondition: the confirmation with the owner's account: {shown(confirmed)}"
        restarted(target, cookie)

        target.start(taken)
        state = b3.restore_state(root)
        assert state is not None and (state["status"], state["owner_outcome"]) == ("committed", "error:EMAIL_TAKEN"), f"the refusal is recorded: {state}"
        assert target.lines_with(RESET_LINK_LINE) == [], "no link was written"
        instance = target.call("GET", INSTANCE)
        assert instance.status_code == 200, f"the public configuration answers: {shown(instance)}"
        assert instance.json().get("restore_interrupted_reason") == "owner_assignment", f"the instance says why it serves no data: {instance.json().get('restore_interrupted_reason')}"
        refused = signed_in(target, OTHER_USER, OTHER_USER_PASSWORD)
        assert refused.status_code == 423, f"a user route serves no restored data: {shown(refused)}"

        # The cause removed (the owner's address is the one the check offered): the way out is the command, run while the server
        # that refuses to serve is still up (it clears the error; the next start gives the account, and its link goes to that log).
        env = b3.child_env(root)
        env.update(LIBREFOLIO_PROFILE="managed", LIBREFOLIO_TEST_LANE_ID=target.lane_id, **{key: value for key, value in variables.items() if key != "LIBREFOLIO_PROFILE"})
        recovered = subprocess.run([sys.executable, str(b3.SCRIPT), "--test-db", "pending", "--recover", "owner"], cwd=root.parent, env=env, stdin=subprocess.DEVNULL, capture_output=True, encoding="utf-8", errors="replace", timeout=b3.CHILD_TIMEOUT_S, check=False)
        assert recovered.returncode == 0, f"backup pending --recover owner: {redacted(b3.shown(recovered))}"
        cleared = b3.restore_state(root)
        assert cleared is not None and cleared["owner_outcome"] is None, f"the error is cleared: {cleared}"

        target.stop()
        target.start(variables)
        final = b3.restore_state(root)
        assert final is not None and final["owner_outcome"] in ("link_only", "sent"), f"the owner's account is given: {final}"
        assert final["owner_outcome"] == "link_only" and target.token_in_log(RESET_LINK_LINE) is not None, "the owner's link is in the log of the start that gave the account"
        instance = target.call("GET", INSTANCE)
        assert instance.json().get("restore_interrupted_reason") is None, "the instance serves its data again"
        users = users_of(root)
        assert (users[SOURCE_ADMIN]["email"] or "").lower() == OWNER_EMAIL and users[SOURCE_ADMIN]["is_instance_owner"] is True, "the chosen account is the owner's"
        open_again = signed_in(target, OTHER_USER, OTHER_USER_PASSWORD)
        assert open_again.status_code == 200, f"another account of the backup signs in: {shown(open_again)}"
        target.stop()
    assert not b3.production_of(root).exists(), "a child wrote in its production data directory"
    print_success("EMAIL_TAKEN: 423 and owner_assignment, then recovered")


# =============================================================================
# 4. The command line picks the owner (Anna), 5. nobody can be picked
# =============================================================================

#: B5-1j: the addresses of the Anna scenario (``example.com``: nothing real); the owner's is ``LIBREFOLIO_ADMIN_EMAIL``.
ANNA_OLD_EMAIL = "old@example.com"
ANNA_NEW_EMAIL = "new@example.com"
REASSIGN_HINT = "./dev.py user reassign-owner <username>"
SECOND_FLAGGED = OTHER_USER


def backup_variant(source: SourceBackup, base: Path, name: str, *statements: str) -> Path:
    """The archive of a copy of the source's data directory whose database ``statements`` changed: a backup as another
    author might have prepared it. The copy is stopped, as the source is."""
    root = base / name
    shutil.copytree(source.root, root, symlinks=True)
    shutil.rmtree(root / "backups", ignore_errors=True)
    database = root / DATABASE_ENTRY
    with closing(sqlite3.connect(database)) as conn:
        for statement in statements:
            conn.execute(statement)
        conn.commit()
    with pytest.MonkeyPatch.context() as patch:
        configured = cases.configure(patch, base / f"{name}-configured-data-dir")
        try:
            job, folder = jobs.run_backup(origin="cli", data_dir=root)
        finally:
            get_git_version.cache_clear()
    assert not configured.exists(), f"the backup wrote in the configured data directory: {cases.listing(configured)}"
    assert (job.status, job.error_code) == ("done", None) and job.file_name, f"precondition: the variant is archived: {job}"
    return folder / job.file_name


def cli_restore(target: Server, root: Path, variables: Mapping[str, str], archive: Path) -> subprocess.CompletedProcess[str]:
    """``dev.py backup restore ARCHIVE --yes`` on the stopped instance at ``root``, as the operator runs it."""
    env = b3.child_env(root)
    env.update(LIBREFOLIO_TEST_LANE_ID=target.lane_id, **variables)
    return subprocess.run(
        [sys.executable, str(b3.SCRIPT), "--test-db", "restore", str(archive), "--yes"],
        cwd=root.parent,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=b3.CHILD_TIMEOUT_S,
        check=False,
    )


def owner_lines_of(text: str) -> list[str]:
    return [line for line in text.splitlines() if "owner" in line.lower()]


def test_a_command_line_restore_picks_the_flagged_administrator_and_gives_the_owner_the_account_and_a_link_only_in_the_log(source_backup, tmp_path, socket_dir):
    """B5-1j §8 (Anna): the backup's only active administrator is flagged as the owner and holds ``old@example.com``; the
    instance's owner is ``new@example.com``. The real CLI restore (``--yes``) names her by username and prints no address; the
    state records her id; after the restart she holds the owner's address, is an active administrator and the only flagged
    account; her old password and a session of before the restore are refused; one password-reset link exists, in the child's
    log only (``link_only``), spends once, and the owner signs in with the password chosen. Red before B5-1j: nobody was
    picked, the flag was cleared and no link was written."""
    print_section("B5-1j 4 Anna: the command line picks the owner")
    root = tmp_path / "target"
    root.mkdir()
    variables = managed_variables(source_backup, owner_email=ANNA_NEW_EMAIL)
    archive = backup_variant(
        source_backup,
        tmp_path,
        "anna",
        "UPDATE users SET is_instance_owner = 0",
        f"UPDATE users SET email = '{ANNA_OLD_EMAIL}', is_instance_owner = 1 WHERE username = '{SOURCE_ADMIN}'",
    )
    with server("anna", root, socket_dir, tmp_path) as target:
        target.start(variables)
        old_cookie = first_session(target)
        target.stop()
        confirmed = cli_restore(target, root, variables, archive)
        assert confirmed.returncode == 0, f"restore --yes on the managed instance: {redacted(b3.shown(confirmed))}"
        said = confirmed.stdout + confirmed.stderr
        assert [line for line in owner_lines_of(said) if SOURCE_ADMIN in line], f"[new] B5-1j: the CLI names the account by username: {redacted(said)}"
        assert REASSIGN_HINT not in said, "an account was picked: no reassign hint"
        assert not [address for address in (ANNA_NEW_EMAIL, ANNA_OLD_EMAIL) if address in said.lower()], f"the CLI prints no address: {redacted(said)}"
        pending = b3.restore_state(root)
        assert pending is not None and (pending["status"], pending["confirmed_via"], pending.get("owner_user_id"), pending.get("owner_outcome")) == ("pending", "cli", source_backup.admin_id, None), f"[new] B5-1j: waiting, from the command line, Anna picked: {pending}"

        target.start(variables)
        state = b3.restore_state(root)
        assert state is not None and (state["status"], state["owner_user_id"], state["owner_outcome"]) == ("committed", source_backup.admin_id, "link_only"), f"committed, the link only in the log: {state}"
        assert not {"reset_path", "link", "token", "reset_link"} & walk_json_keys(state), f"the state keeps no link: {sorted(walk_json_keys(state))}"
        users = users_of(root)
        anna = users[SOURCE_ADMIN]
        assert (anna["id"], (anna["email"] or "").lower(), anna["is_superuser"], anna["is_active"], anna["is_instance_owner"]) == (source_backup.admin_id, ANNA_NEW_EMAIL, True, True, True), f"Anna holds the owner's address, an active administrator and the owner: {anna}"
        assert [name for name, row in users.items() if row["is_instance_owner"]] == [SOURCE_ADMIN], "the only owner is Anna"
        assert signed_in(target, SOURCE_ADMIN, SOURCE_ADMIN_PASSWORD).status_code in (400, 401, 403), "her old password is refused"
        assert target.call("GET", ME, cookie=old_cookie).status_code == 401, "a session of before the restore is refused"
        assert signed_in(target, OTHER_USER, OTHER_USER_PASSWORD).status_code == 200, "another account of the backup signs in with its password"

        token = target.wait_for_token(RESET_LINK_LINE)
        assert len(target.lines_with(RESET_LINK_LINE)) == 1, "one link written for the owner"
        assert holders_of(root, token, in_logs=True), "barrier: the child's log holds the link"
        assert holders_of(root, token) == [], f"no file of the data directory but the logs holds the link: {holders_of(root, token)}"
        assert token not in said and token not in target.call("GET", INSTANCE).text, "the link is in neither the CLI's output nor the public configuration"
        reset = target.call("POST", PASSWORD_RESET, json={"token": token, "new_password": OWNER_NEW_PASSWORD})
        again = target.call("POST", PASSWORD_RESET, json={"token": token, "new_password": OWNER_NEW_PASSWORD + "x"})
        assert reset.status_code == 200 and (again.status_code, code_of(again)) == (400, "TOKEN_INVALID"), f"the link spends once: {shown(reset)} / {shown(again)}"
        signed = signed_in(target, SOURCE_ADMIN, OWNER_NEW_PASSWORD)
        assert signed.status_code == 200 and signed.json()["user"]["email"].lower() == ANNA_NEW_EMAIL, f"Anna signs in with the password she chose: {shown(signed)}"
        target.stop()
    assert not b3.production_of(root).exists(), "a child wrote in its production data directory"
    print_success("Anna picked, closed, the owner's address, link only in the log, spent once")


def assert_nobody_was_picked(root: Path, target: Server, variables: Mapping[str, str], archive: Path, flagged: list[str]) -> None:
    """The restore of ``archive`` from the command line on the stopped ``target`` picks nobody: the CLI says so and gives the
    command, the state records the outcome ``none``, the first start commits it and serves, nobody is flagged, no account is
    closed, no link is written, and nothing about the owner in the CLI's output or in the logs names an account or an address."""
    confirmed = cli_restore(target, root, variables, archive)
    assert confirmed.returncode == 0, f"restore --yes on the managed instance: {redacted(b3.shown(confirmed))}"
    said = confirmed.stdout + confirmed.stderr
    hint = [line for line in owner_lines_of(said) if REASSIGN_HINT in line and "no owner" in line.lower()]
    assert hint, f"[new] B5-1j: the CLI says there is no owner and gives the command: {redacted(said)}"
    pending = b3.restore_state(root)
    assert pending is not None and (pending["status"], pending["confirmed_via"], pending.get("owner_user_id"), pending.get("owner_outcome")) == ("pending", "cli", None, "none"), f"[new] B5-1j: waiting, nobody picked, the outcome none: {pending}"

    target.start(variables)
    state = b3.restore_state(root)
    assert state is not None and (state["status"], state.get("owner_user_id"), state.get("owner_outcome")) == ("committed", None, "none"), f"committed, no owner, the outcome none: {state}"
    users = users_of(root)
    assert [name for name, row in users.items() if row["is_instance_owner"]] == [], f"nobody is the owner: the author's flags are gone: {users}"
    assert not [name for name, row in users.items() if (row["email"] or "").lower() == OWNER_EMAIL], "no account took the owner's address"
    assert target.lines_with(RESET_LINK_LINE) == [], "no owner's link written"
    assert signed_in(target, SOURCE_ADMIN, SOURCE_ADMIN_PASSWORD).status_code == 200, "no account was closed: the backup's password works"
    assert signed_in(target, OTHER_USER, OTHER_USER_PASSWORD).status_code == 200, "the instance serves"
    # The lines about the owner (the CLI's output, the logs of the instance and of the command) name nobody.
    texts = [said, *(path.read_text(encoding="utf-8", errors="replace") for path in sorted((root / "logs").glob("*")) if path.is_file()), *(path.read_text(encoding="utf-8", errors="replace") for path in target.logs())]
    about_the_owner = [line.lower() for text in texts for line in owner_lines_of(text) if SETUP_LINK_LINE not in line]
    named = sorted({word for line in about_the_owner for word in (*flagged, OWNER_EMAIL, OTHER_USER_EMAIL, SOURCE_ADMIN, FLAGGED_USER) if word.lower() in line})
    assert named == [], f"no line about the owner names an account or an address: {named}"


def test_a_command_line_restore_of_a_backup_flagging_an_ordinary_account_picks_nobody_and_clears_the_flag(source_backup, tmp_path, socket_dir):
    """B5-1j §2.3: the backup's author flagged an ORDINARY account (not an administrator): not a candidate, nobody holds the
    owner's address, so nobody is picked. The restore goes on, the outcome is ``none``, the flag is cleared, no account is closed
    and the instance serves. (Before B5-1j: the same, without the outcome and the command in the CLI's words.)"""
    print_section("B5-1j 5a Nobody picked: a flag on an ordinary account")
    root = tmp_path / "target"
    root.mkdir()
    variables = managed_variables(source_backup)
    with server("cli", root, socket_dir, tmp_path) as target:
        target.start(variables)
        target.stop()
        assert_nobody_was_picked(root, target, variables, source_backup.archive, [FLAGGED_USER])
        target.stop()
    assert not b3.production_of(root).exists(), "a child wrote in its production data directory"
    print_success("flag on an ordinary account: outcome none, flag cleared, no account closed")


def test_a_command_line_restore_of_a_backup_with_two_flagged_administrators_picks_nobody(source_backup, tmp_path, socket_dir):
    """B5-1j §2.3 (revision of A): two active administrators flagged by the backup (a crafted copy: the unique index of the
    flag dropped): never «the first by id» — nobody is picked. Confirmed all the same, the outcome ``none``, the instance
    serves, nobody is flagged, no account closed, the warning and the lines name no account and no address."""
    print_section("B5-1j 5b Nobody picked: two flagged administrators")
    root = tmp_path / "target"
    root.mkdir()
    variables = managed_variables(source_backup)
    archive = backup_variant(
        source_backup,
        tmp_path,
        "two-flagged",
        "DROP INDEX ux_users_instance_owner",
        f"UPDATE users SET is_superuser = 1, is_active = 1 WHERE username = '{SECOND_FLAGGED}'",
        f"UPDATE users SET is_instance_owner = 1 WHERE username IN ('{SOURCE_ADMIN}', '{SECOND_FLAGGED}')",
    )
    with server("two", root, socket_dir, tmp_path) as target:
        target.start(variables)
        target.stop()
        assert_nobody_was_picked(root, target, variables, archive, [SECOND_FLAGGED])
        target.stop()
    assert not b3.production_of(root).exists(), "a child wrote in its production data directory"
    print_success("two flagged administrators: nobody picked, the instance serves")

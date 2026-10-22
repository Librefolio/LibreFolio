"""
The sealed nightly backup, restored through the hosting panel, end to end (workstream B, lot B5; contract L3 §2-§7).
Selector: ``e2e backup-roundtrip-l3``.

1. A populated instance, its backups sealed for a test recipient (``LIBREFOLIO_BACKUP_RECIPIENTS``), makes a backup for
   the panel (``POST /api/v1/backup/panel/jobs`` with a signed ``backup`` ticket): done, ``sealed``, a ``.tar`` without the
   instance key, whose download has the job's SHA-256. The coordinator's side reads it as the contract says (§3.5):
   ``read_sealed``, the manifest naming the recipient, ``open_password`` with the test identity, ``check_password``
   against the envelope's header; another identity opens nothing.
2. An empty instance started in the «awaiting restore» mode (``LIBREFOLIO_AWAIT_RESTORE=1``, §6), with the source's
   instance key (§7: set before the upload): ``GET /api/v1/panel/status`` says ``mode: awaiting_restore``, a user route
   answers 423 ``instance_awaiting_restore``, a backup of the panel 409 ``backup_awaiting_restore``.
3. The panel restores it (§5, one new ``backup:restore`` ticket per call): the ``backup.lfbk`` member uploaded as a raw
   body, the check with its password, the panel's reduced report (R1: no ``administrators``, no differences, no
   ``tables``; ``administrators_count`` instead), the confirmation, the restart: the process exits. A new process with
   the same environment applies and commits it: ``committed`` on ``…/restore/status`` and on the panel's status.
4. The coordinator leaves the mode (R4): a new process without ``LIBREFOLIO_AWAIT_RESTORE`` serves normally; the target
   has the source's rows, files, ledger totals and every account's portfolio report (the totals of
   ``test_backup_roundtrip.py``, computed the same way), and the backup's administrator signs in.
5. A ``backup`` ticket never opens the restore routes (``panel_ticket_*``), and out of the mode they answer 409
   ``restore_mode_required``.

The instances are real servers: ``uvicorn backend.app.main:app`` in a child process in test mode on a data directory of
the test, listening on a Unix socket in a short folder of its own under ``/tmp`` (as ``test_shutdown_budget_process.py``
does), never on a TCP port: the lane's port and server are never touched, and the restart of §5 stops only that child.
Every child runs with ``test_backup_roundtrip.child_env`` (none of the lane's ``LIBREFOLIO_*`` variables, coverage or
secrets) plus the panel's variables of the test: an Ed25519 key of the test (``LIBREFOLIO_PANEL_PUBLIC_KEYS``), a public
address (``LIBREFOLIO_PUBLIC_URL``, the tickets' audience), the scheduler off. The recipient and its identity are the
L3 vectors' (``fixtures/backup_l3/test-identity-1.txt``, TEST ONLY). The source is populated as the B3 round trip
populates it (``populate_mock_data --force`` in a child); its instance key, given to both servers by the environment, is
the one the populate generated, or a new one when it generated none. Every wait polls a condition with a deadline,
waiting on the server process itself between two polls, so a server that dies ends the wait at once.

PURE: data directories, archives and sockets of the test; the lane's data directory, database and server are never read
or written. POSIX only (Unix sockets, process groups).

RED until workstream H's lot H-62 lands: today the restore routes of the panel do not exist (404) and the mode does
not exist (``LIBREFOLIO_AWAIT_RESTORE`` is ignored: ``panel/status`` has no ``mode``). Step 1 is its own test, green
today. Where the contract leaves a detail to H, the test uses the contract's words, marked ``# H-62 contract §…``.
"""

from __future__ import annotations

import base64
import contextlib
import hashlib
import json
import os
import re
import secrets
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from backend.app.services.platform.instance_backup.paths import DATABASE_ENTRY
from backend.app.services.platform.instance_backup.sealed import FORMAT, MEMBERS, PASSWORD_LENGTH, SealedError, check_password, extract_envelope, open_password, read_identities, read_sealed
from backend.test_scripts.test_e2e import test_backup_roundtrip as b3
from backend.test_scripts.test_utils import print_section, print_success

pytestmark = pytest.mark.skipif(os.name == "nt", reason="Unix sockets and process groups are POSIX only")

FIXTURES = b3.PROJECT_ROOT / "backend" / "test_scripts" / "fixtures" / "backup_l3"
#: The L3 vectors' test identities (TEST ONLY): the first is the recipient of the backups, the second opens nothing.
IDENTITY_FILE = FIXTURES / "test-identity-1.txt"
OTHER_IDENTITY_FILE = FIXTURES / "test-identity-2.txt"
RECIPIENT = json.loads((FIXTURES / "vectors.json").read_text(encoding="utf-8"))["recipients"][IDENTITY_FILE.name]

#: The instance's public address, and so the tickets' audience: its canonical origin.
PUBLIC_URL = "https://l3-roundtrip.example.test"
AUDIENCE = PUBLIC_URL
#: The panel's test key: Ed25519 from a fixed seed, never a key of a real panel.
KID = "b5-l3-test-key"
_SEED = hashlib.sha256(b"LibreFolio B5 L3 round trip, test_backup_roundtrip_l3.py: a test key never used in production").digest()
PANEL_KEY = Ed25519PrivateKey.from_private_bytes(_SEED)
PANEL_KEYS_VALUE = f"{KID}:" + base64.urlsafe_b64encode(PANEL_KEY.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)).rstrip(b"=").decode("ascii")
TICKET_TYPE = "lf-panel+jwt"

#: The scopes of the panel's tickets.
SCOPE_BACKUP = "backup"
SCOPE_STATUS = "status"
# H-62 contract §5: «solo il biglietto L2 di scopo nuovo `backup:restore`» — the scope string as the contract spells it.
SCOPE_RESTORE = "backup:restore"

#: The backup's administrator, as populate_mock_data writes it.
ADMIN_USERNAME = "e2e_test_admin"
ADMIN_PASSWORD = "E2eAdminPass123!"

API = "/api/v1"
HEALTH = f"{API}/system/health"
LOGIN = f"{API}/auth/login"
PANEL_STATUS = f"{API}/panel/status"
PANEL_JOBS = f"{API}/backup/panel/jobs"
# H-62 contract §5, the routes of the panel's restore.
RESTORE = f"{API}/backup/panel/restore"
RESTORE_UPLOAD = f"{RESTORE}/upload"
RESTORE_STAGE = f"{RESTORE}/stage"
RESTORE_RESTART = f"{RESTORE}/restart"
RESTORE_STATUS = f"{RESTORE}/status"

AWAIT_RESTORE = {"LIBREFOLIO_AWAIT_RESTORE": "1"}
#: R1 (contract §5): what the panel's view of a check's report never carries.
REPORT_FORBIDDEN_KEYS = ("administrators", "control_totals_differences", "tables", "files", "files_size", "database_size")

#: A short folder for the sockets: an AF_UNIX path holds about 100 bytes, fewer than pytest's tmp_path may take.
SHORT_TMP = "/tmp" if os.path.isdir("/tmp") else tempfile.gettempdir()
SOCKET_PATH_LIMIT = 100
BASE_URL = "http://l3-roundtrip.test"
#: Seconds a server may take to start (imports, migrations, a restore applied), a job or a check to end, a request to
#: be answered, a server to exit after a SIGTERM: on a loaded machine. Every wait still ends.
START_SECONDS = 300.0
JOB_SECONDS = 900.0
REQUEST_SECONDS = 120.0
EXIT_SECONDS = 60.0
#: How long the test waits on the server process between two polls: the wait ends at once if the process exits.
POLL_SECONDS = 0.2
TAIL = 4000


# =============================================================================
# The panel's tickets
# =============================================================================


def ticket(scope: str) -> str:
    """A ticket of the panel for ``scope``, as the coordinator signs one per call: EdDSA, a new ``jti``, 240 s to live."""
    now = int(time.time())
    claims = {"aud": AUDIENCE, "scope": scope, "iat": now - 5, "exp": now + 240, "jti": secrets.token_urlsafe(16)}
    return jwt.encode(claims, PANEL_KEY, algorithm="EdDSA", headers={"typ": TICKET_TYPE, "kid": KID})


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


def shown(response: httpx.Response) -> str:
    return f"{response.request.method} {response.request.url.path} → {response.status_code} {response.text[:TAIL]}"


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

    def start(self, variables: Mapping[str, str]) -> None:
        """A new process with ``variables`` beside the test's environment, once it answers its health route."""
        assert self.process is None or self.process.poll() is not None, f"barrier: {self.name}'s previous process still runs"
        self.starts += 1
        self.socket = self.socket_dir / f"{self.name[:6]}-{self.starts}.sock"
        assert len(os.fsencode(self.socket)) < SOCKET_PATH_LIMIT, f"barrier: the socket path {self.socket} is too long for AF_UNIX"
        self.log_path = self.log_dir / f"{self.name}-{self.starts}.log"
        env = b3.child_env(self.data_dir)
        env.update(LIBREFOLIO_NO_SCHEDULER="1", LIBREFOLIO_PANEL_PUBLIC_KEYS=PANEL_KEYS_VALUE, LIBREFOLIO_PUBLIC_URL=PUBLIC_URL, **variables)
        command = [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--uds", str(self.socket), "--lifespan", "on", "--log-level", "warning"]
        with self.log_path.open("wb") as log:
            self.process = subprocess.Popen(command, cwd=b3.PROJECT_ROOT, env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
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

    def _client(self, timeout: float) -> httpx.Client:
        assert self.socket is not None
        return httpx.Client(transport=httpx.HTTPTransport(uds=str(self.socket)), timeout=timeout)

    def call(self, method: str, path: str, *, scope: str | None = None, **kwargs: Any) -> httpx.Response:
        """One request; with ``scope``, under a new ticket of the panel for it."""
        headers = dict(kwargs.pop("headers", {}))
        if scope is not None:
            headers["Authorization"] = f"Bearer {ticket(scope)}"
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

    def poll(self, path: str, scope: str, what: str) -> dict[str, Any]:
        """GET ``path`` until its ``status`` is no longer ``running``; the last body."""
        deadline = time.monotonic() + JOB_SECONDS
        while True:
            response = self.call("GET", path, scope=scope)
            assert response.status_code == 200, f"{what}: {shown(response)}"
            body = response.json()
            if body.get("status") != "running":
                return body
            if time.monotonic() >= deadline:
                pytest.fail(f"{what} still runs after {JOB_SECONDS} s: {body}")
            self.keeps_running(POLL_SECONDS, what)

    def exits(self, why: str) -> int:
        """Wait for the process to exit by itself; its status."""
        assert self.process is not None
        try:
            return self.process.wait(timeout=EXIT_SECONDS)
        except subprocess.TimeoutExpired:
            pytest.fail(f"{self.name} still runs {EXIT_SECONDS} s after {why}:\n{self.output()}")

    def stop(self) -> None:
        """SIGTERM, as a supervisor stops it, and wait for the exit."""
        assert self.process is not None
        if self.process.poll() is None:
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
        text = self.log_path.read_text(encoding="utf-8", errors="replace") if self.log_path is not None and self.log_path.exists() else ""
        return f"--- {self.log_path}\n{text[-TAIL:]}"


@contextlib.contextmanager
def server(name: str, data_dir: Path, socket_dir: Path, log_dir: Path) -> Iterator[Server]:
    found = Server(name, data_dir, socket_dir, log_dir)
    try:
        yield found
    finally:
        found.cleanup()


@pytest.fixture(scope="module")
def socket_dir() -> Iterator[Path]:
    directory = Path(tempfile.mkdtemp(prefix="lf-l3-", dir=SHORT_TMP))
    yield directory
    shutil.rmtree(directory, ignore_errors=True)


def signed_in(instance: Server) -> httpx.Response:
    return instance.call("POST", LOGIN, json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD})


# =============================================================================
# The source and its sealed backup
# =============================================================================


@dataclass(frozen=True)
class SealedBackup:
    """The populated source (stopped), its instance key, the panel's finished job and its downloaded archive."""

    root: Path
    instance_key: str
    job: dict[str, Any]
    archive: Path
    content_type: str


@pytest.fixture(scope="module")
def sealed_backup(tmp_path_factory, socket_dir) -> SealedBackup:
    """The project's mock data in a new instance, served with its backups sealed for ``RECIPIENT``; the panel's backup of
    it, downloaded; the server stopped."""
    base = tmp_path_factory.mktemp("l3-source")
    root = base / "source"
    root.mkdir()
    b3.populate(root)
    b3.assert_populated(root / DATABASE_ENTRY)
    key_file = root / "secrets" / "instance.key"
    instance_key = key_file.read_text(encoding="utf-8").strip() if key_file.is_file() else secrets.token_urlsafe(32)
    with server("source", root, socket_dir, base) as source:
        source.start({"LIBREFOLIO_BACKUP_RECIPIENTS": RECIPIENT, "LIBREFOLIO_INSTANCE_KEY": instance_key})
        # A barrier for step 4: the backup's administrator signs in on the source, through this socket.
        response = signed_in(source)
        assert response.status_code == 200, f"precondition: {ADMIN_USERNAME} signs in on the source: {shown(response)}"
        started = source.call("POST", PANEL_JOBS, scope=SCOPE_BACKUP)
        assert started.status_code == 202, f"the panel starts a backup: {shown(started)}"
        job = source.poll(f"{PANEL_JOBS}/{started.json()['job_id']}", SCOPE_BACKUP, "the panel's backup")
        assert (job["status"], job.get("error_code")) == ("done", None), f"precondition: the panel's backup is done: {job}"
        downloaded = source.call("GET", f"{PANEL_JOBS}/{job['job_id']}/file", scope=SCOPE_BACKUP)
        assert downloaded.status_code == 200, f"the panel downloads its backup: {shown(downloaded)}"
        source.stop()
    archive = base / (job.get("file_name") or "backup.download")
    archive.write_bytes(downloaded.content)
    assert not b3.production_of(root).exists(), "a child wrote in its production data directory"
    return SealedBackup(root=root, instance_key=instance_key, job=job, archive=archive, content_type=downloaded.headers.get("content-type", ""))


def test_the_panel_s_backup_is_sealed_for_the_instance_s_recipient(sealed_backup):
    """§2-§4, §3.5: the job's view (sealed for the recipient, a ``.tar``, never the instance key), the download (its
    SHA-256 and size are the job's, ``application/x-tar``), and the coordinator's reading: the three members, the
    manifest naming the recipient, the password opened by the test identity and checked against the envelope; the other
    test identity opens nothing."""
    print_section("L3 §4 The panel's backup, sealed")
    job, data = sealed_backup.job, sealed_backup.archive.read_bytes()
    assert re.fullmatch(r"librefolio-backup-\d{8}-\d{6}\.tar", job["file_name"] or ""), f"a sealed backup's name (§3.1): {job['file_name']}"
    assert (job["sealed"], job["sealed_recipients"], job["encrypted"], job["instance_key_included"]) == (True, [RECIPIENT], True, False), f"the job's view (§4, §7): {job}"
    assert (job["file_size"], job["file_sha256"]) == (len(data), hashlib.sha256(data).hexdigest()), "the download is the bytes the job describes"
    assert sealed_backup.content_type.startswith("application/x-tar"), f"the download's type (§4): {sealed_backup.content_type}"

    archive = read_sealed(sealed_backup.archive)
    assert (archive.manifest["format"], archive.manifest["recipients"], archive.manifest["password_member"]) == (FORMAT, [RECIPIENT], MEMBERS[1]), f"the manifest (§3.2): {archive.manifest}"
    password = open_password(archive, read_identities(IDENTITY_FILE))
    assert len(password) == PASSWORD_LENGTH, "a password LibreFolio writes"
    check_password(archive, password)
    with pytest.raises(SealedError) as refused:
        open_password(archive, read_identities(OTHER_IDENTITY_FILE))
    assert refused.value.code == "sealed_no_identity", f"another identity opens nothing: {refused.value.code}"
    print_success(f"{job['file_name']}: {len(data)} bytes, sealed for {RECIPIENT[:12]}…, opened by the test identity")


# =============================================================================
# The restore through the panel (H-62)
# =============================================================================


def test_the_sealed_backup_restored_by_the_panel_on_an_empty_instance_gives_the_same_totals(sealed_backup, tmp_path, socket_dir):
    """§5-§7 and R1, R4: the empty instance awaits the restore and refuses everything else; the panel uploads the
    envelope, checks it (a report without personal or portfolio data), confirms and restarts; a new process commits it,
    still in the mode; a process without the mode serves the source's data, and its administrator signs in."""
    print_section("L3 §5 The panel restores a sealed backup on an empty instance")
    archive = read_sealed(sealed_backup.archive)
    password = open_password(archive, read_identities(IDENTITY_FILE))
    envelope = tmp_path / "backup.lfbk"
    extract_envelope(sealed_backup.archive, archive, envelope)
    body = envelope.read_bytes()
    target_root = tmp_path / "target"
    target_root.mkdir()
    # §7: the source's instance key, set before the upload.
    awaiting = {"LIBREFOLIO_INSTANCE_KEY": sealed_backup.instance_key, **AWAIT_RESTORE}
    normal = {"LIBREFOLIO_INSTANCE_KEY": sealed_backup.instance_key}

    with server("target", target_root, socket_dir, tmp_path) as target:
        target.start(awaiting)

        # Step 2, the mode (§6).
        status = target.call("GET", PANEL_STATUS, scope=SCOPE_STATUS)
        assert status.status_code == 200, f"the panel reads the status: {shown(status)}"
        assert status.json().get("mode") == "awaiting_restore", f"H-62 contract §6: panel/status says the mode: {status.json()}"
        assert status.json().get("restore") is None, f"no restore recorded yet: {status.json()}"
        refused = signed_in(target)
        assert (refused.status_code, detail(refused).get("code")) == (423, "instance_awaiting_restore"), f"a user route waits for the restore (§6): {shown(refused)}"
        refused = target.call("POST", PANEL_JOBS, scope=SCOPE_BACKUP)
        assert (refused.status_code, detail(refused).get("code")) == (409, "backup_awaiting_restore"), f"no backup of an empty instance (§6): {shown(refused)}"

        # Step 3, the restore (§5).
        uploaded = target.call("PUT", RESTORE_UPLOAD, scope=SCOPE_RESTORE, content=body, headers={"Content-Type": "application/octet-stream"})
        assert uploaded.status_code == 201, f"H-62 contract §5: the panel uploads the envelope: {shown(uploaded)}"
        assert (uploaded.json()["kind"], uploaded.json()["size"]) == ("envelope", len(body)), f"the upload: {uploaded.json()}"
        staged = target.call("POST", RESTORE_STAGE, scope=SCOPE_RESTORE, json={"upload_id": uploaded.json()["upload_id"], "password": password})
        assert staged.status_code == 202, f"the check starts: {shown(staged)}"
        stage_id = staged.json()["stage_id"]
        check = target.poll(f"{RESTORE_STAGE}/{stage_id}", SCOPE_RESTORE, "the panel's check")
        assert (check["status"], check.get("error_code")) == ("done", None), f"the check ends with a report: {check}"
        report = check["report"]
        # H-62 contract §5, R1: the panel's report (PanelRestoreStageReport), its field names as the contract's table writes them.
        assert report["restorable"] is True, f"restorable: {report}"
        assert report["secrets_unreadable"] == {"system": 0, "user": 0}, f"§7: every secret readable with the source's key: {report['secrets_unreadable']}"
        assert report["control_totals"] == "same", f"the ledger's totals the same: {report['control_totals']}"
        assert sorted(set(REPORT_FORBIDDEN_KEYS) & set(report)) == [], f"R1: no personal or portfolio data in the panel's report: {sorted(report)}"
        assert report.get("administrators_count", 0) >= 1, f"R1: administrators_count instead of the names: {report.get('administrators_count')}"
        assert ADMIN_USERNAME not in json.dumps(check), "R1: no username anywhere in the panel's check"

        confirmed = target.call("POST", f"{RESTORE_STAGE}/{stage_id}/confirm", scope=SCOPE_RESTORE)
        assert confirmed.status_code == 202 and confirmed.json()["state"] == "pending", f"the panel confirms: {shown(confirmed)}"
        # H-62 contract §5, R1: confirmed_via "panel", never a username.
        assert confirmed.json().get("confirmed_via", "panel") == "panel", f"confirmed via the panel: {confirmed.json()}"
        assert ADMIN_USERNAME not in confirmed.text, f"R1: no username in the panel's status: {confirmed.json()}"
        restarted = target.call("POST", RESTORE_RESTART, scope=SCOPE_RESTORE)
        assert restarted.status_code == 202, f"the panel asks the restart: {shown(restarted)}"
        target.exits("the restart the panel asked")

        # A new process, the same variables: the restore applied and committed, still in the mode (R4 step 2).
        target.start(awaiting)
        state = target.call("GET", RESTORE_STATUS, scope=SCOPE_RESTORE)
        assert state.status_code == 200 and state.json()["state"] == "committed", f"committed by the new process: {shown(state)}"
        assert state.json()["stage_id"] == stage_id, f"the restore of the panel's check: {state.json()}"
        status = target.call("GET", PANEL_STATUS, scope=SCOPE_STATUS)
        assert status.status_code == 200, f"the panel reads the status: {shown(status)}"
        assert (status.json().get("mode"), (status.json().get("restore") or {}).get("state")) == ("awaiting_restore", "committed"), f"H-62 contract §6: {status.json()}"
        refused = signed_in(target)
        assert (refused.status_code, detail(refused).get("code")) == (423, "instance_awaiting_restore"), f"R4: still closed until the coordinator leaves the mode: {shown(refused)}"
        target.stop()

        # Step 4, the coordinator leaves the mode (R4 step 3).
        target.start(normal)
        status = target.call("GET", PANEL_STATUS, scope=SCOPE_STATUS)
        assert status.status_code == 200 and status.json().get("mode") == "normal", f"H-62 contract §6: out of the mode: {shown(status)}"
        target.stop()
        original, restored = b3.totals(sealed_backup.root), b3.totals(target_root)
        assert original["reports"], "precondition: an account of the source has a portfolio to report"
        assert b3.differences(original["rows"], restored["rows"]) == [], f"the rows of every table: {b3.differences(original['rows'], restored['rows'])}"
        assert b3.differences(original["files"], restored["files"]) == [], f"every file: {b3.differences(original['files'], restored['files'])}"
        assert b3.differences(original["reports"], restored["reports"]) == [], f"every account's portfolio report: {b3.differences(original['reports'], restored['reports'])}"
        assert restored["control_totals"] == original["control_totals"], f"the ledger's control totals: {b3.differences(b3.ledger_lines(original['control_totals']), b3.ledger_lines(restored['control_totals']))}"
        target.start(normal)
        welcomed = signed_in(target)
        assert welcomed.status_code == 200, f"the backup's administrator signs in: {shown(welcomed)}"
        target.stop()
    assert not b3.production_of(target_root).exists(), "a child wrote in its production data directory"
    print_success(f"{len(restored['rows'])} tables, {len(restored['files'])} files, {len(restored['reports'])} reports: the same, restored by the panel")


def test_the_panel_s_restore_routes_want_their_scope_and_the_mode(tmp_path, socket_dir):
    """§5: a ``backup`` ticket never opens the restore routes, even in the mode (a refusal of the ticket,
    ``panel_ticket_*``, the barrier being the ``backup:restore`` ticket the same route accepts); out of the mode, the
    ``backup:restore`` ticket gets 409 ``restore_mode_required`` on the upload and on the status."""
    print_section("L3 §5 The restore routes: their scope, their mode")
    root = tmp_path / "instance"
    root.mkdir()
    with server("scopes", root, socket_dir, tmp_path) as instance:
        instance.start(AWAIT_RESTORE)
        for method, path, extra in (("PUT", RESTORE_UPLOAD, {"content": b"not read"}), ("GET", RESTORE_STATUS, {})):
            refused = instance.call(method, path, scope=SCOPE_BACKUP, **extra)
            assert refused.status_code == 401 and str(detail(refused).get("code", "")).startswith("panel_ticket_"), f"H-62 contract §5: a backup ticket on {path}: {shown(refused)}"
        accepted = instance.call("GET", RESTORE_STATUS, scope=SCOPE_RESTORE)
        assert accepted.status_code == 200 and accepted.json()["state"] == "none", f"barrier: the restore ticket opens the route: {shown(accepted)}"
        instance.stop()

        instance.start({})
        for method, path, extra in (("PUT", RESTORE_UPLOAD, {"content": b"not read"}), ("GET", RESTORE_STATUS, {})):
            refused = instance.call(method, path, scope=SCOPE_RESTORE, **extra)
            assert (refused.status_code, detail(refused).get("code")) == (409, "restore_mode_required"), f"H-62 contract §5: out of the mode, {path}: {shown(refused)}"
        instance.stop()
    print_success("backup tickets refused, restore_mode_required out of the mode")

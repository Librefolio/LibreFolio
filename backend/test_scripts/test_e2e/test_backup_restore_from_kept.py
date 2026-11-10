"""
A real restore from end to end, from a backup the server keeps (release 1.3, lot C9-B; C9-8, C9-9, C9-10). Selector:
``e2e backup-restore-from-kept``.

The developer's acceptance: «un ripristino vero da capo a fondo, su dati di test: dal file del server, cifrato e no, fino
al riavvio e all'accesso con la password verificata».

1. A populated instance (the B3 round trip's ``populate_mock_data --force`` in a child), served, its administrator
   (``e2e_test_admin``, whose password populate writes) signed in, makes two backups through ``POST /backup/instance``: a
   clear one, and a secure one with a password that meets ``GET /backup/instance/options``. A hosting panel's backup,
   sealed for the L3 test recipient (``POST /backup/panel/jobs`` with a signed ``backup`` ticket), is made too. The
   three are listed by ``GET /backup/instance/jobs``, found by their ``job_id``. Then the instance moves on: the
   administrator changes the password, and creates a broker. The backups hold neither.
2. The clear backup: ``POST /backup/restore/upload/from-backup`` answers an upload of kind ``zip``, the size of the kept
   archive: a hard link (the archive's link count goes from 1 to 2), never a copy, never a move. The check
   (``POST /backup/restore/stage``, polled) reports it restorable, ``e2e_test_admin`` among its administrators, the size
   of its uploads and of its broker reports. Its end removes the link and keeps the archive: link count 1, the SHA-256
   of the job. ``verify-password`` answers ``matches: true`` for the backup's password, ``false`` for the password of
   today and for a wrong one, 404 ``restore_admin_not_found`` for an unknown account and for an account that is not an
   administrator; ``avatar/{username}`` gives the administrator's picture from the copy (the bytes the source holds),
   404 ``restore_avatar_not_found`` for an unknown account. The check is dropped (204), the archive stays.
3. The secure backup: the upload is an ``envelope``; the check without its password is 400 ``password_required``, with a
   wrong one 400 ``wrong_password``, the upload kept for the next try; with the right one it runs, ``encrypted``, every
   secret readable. ``verify-password`` as above. Confirmed (202 ``pending``), the restart asked (202): the process exits;
   a new process with the same environment applies and commits it (``GET /backup/restore/status``: ``committed``, the
   check's ``stage_id``). The password ``verify-password`` said matches signs in; the password of before the restore
   does not, nor does the session of before; the broker created after the backup is gone.
4. Refusals: a sealed backup (a hosting panel's) is 409 ``backup_sealed_unsupported``, an id no backup has is 404
   ``backup_job_not_found``; neither leaves an upload, and the sealed archive stays.
5. No password the test sends (the account's, the backup's, the wrong ones) is ever in the log of a child, nor in a log
   file of the data directory.

The instances are real servers: ``uvicorn backend.app.main:app`` in a child process in test mode on a data directory of
the test, on a Unix socket in a short folder under ``/tmp`` (``test_backup_roundtrip_owner.Server``, cookie sessions),
never on a TCP port: the lane's port and server are never touched, and a restart stops only that child. Each child runs
with ``test_backup_roundtrip.child_env`` (none of the lane's ``LIBREFOLIO_*`` variables, coverage or secrets) plus the
panel's variables of ``test_backup_roundtrip_l3`` (its Ed25519 test key, public address and test recipient), the
scheduler off. The source is made once for the module and stopped; each test serves its own copy of it, so the restore of
one never reaches the other. Every wait polls a condition with a deadline, waiting on the server process between two
polls, so a server that dies ends the wait at once.

PURE: data directories, archives and sockets of the test; the lane's data directory, database and server are never read
or written. POSIX only (Unix sockets, hard links, process groups).
"""

from __future__ import annotations

import contextlib
import hashlib
import os
import shutil
import sqlite3
import tempfile
import time
from collections.abc import Iterator, Mapping
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from backend.app.services.platform.instance_backup.paths import DATABASE_ENTRY
from backend.test_scripts.test_e2e import test_backup_roundtrip as b3
from backend.test_scripts.test_e2e import test_backup_roundtrip_l3 as l3
from backend.test_scripts.test_e2e import test_backup_roundtrip_owner as owner
from backend.test_scripts.test_services import test_backup_staging as cases
from backend.test_scripts.test_utils import print_section, print_success, unique_id

# Autouse (the module fixture of ``test_backup_staging.py``, re-exported as the siblings do): this process's production
# data directory is a folder of the test that must stay absent.
configured_data_dir = cases.configured_data_dir

pytestmark = pytest.mark.skipif(os.name == "nt", reason="Unix sockets, hard links and process groups are POSIX only")

API = "/api/v1"
LOGIN = f"{API}/auth/login"
ME = f"{API}/auth/me"
CHANGE_PASSWORD = f"{API}/auth/change-password"
BROKERS = f"{API}/brokers"
BACKUP_INSTANCE = f"{API}/backup/instance"
BACKUP_OPTIONS = f"{BACKUP_INSTANCE}/options"
BACKUP_JOBS = f"{BACKUP_INSTANCE}/jobs"
PANEL_JOBS = f"{API}/backup/panel/jobs"
RESTORE = f"{API}/backup/restore"
FROM_BACKUP = f"{RESTORE}/upload/from-backup"
RESTORE_STAGE = f"{RESTORE}/stage"
RESTORE_RESTART = f"{RESTORE}/restart"
RESTORE_STATUS = f"{RESTORE}/status"

#: The backup's administrator, as populate_mock_data writes it, and an ordinary account of the same populate.
ADMIN = "e2e_test_admin"
ADMIN_PASSWORD = "E2eAdminPass123!"
PLAIN_USER = "e2e_test_user"
#: The administrator's password after the backups: the instance moved on, the backups did not.
CHANGED_PASSWORD = "Changed-After-The-Backup-2026!"
#: The secure backup's password (it meets the archive rules: long, every class of character), and wrong ones.
BACKUP_PASSWORD = "C9B-Kept-Secure-Backup-Pass-2026!"
WRONG_BACKUP_PASSWORD = "C9B-Not-The-Backup-Pass-2026!"
WRONG_ACCOUNT_PASSWORD = "C9B-Not-The-Admin-Pass-2026!"
#: Every password the test sends: none may appear in a log.
SECRETS = (ADMIN_PASSWORD, CHANGED_PASSWORD, BACKUP_PASSWORD, WRONG_BACKUP_PASSWORD, WRONG_ACCOUNT_PASSWORD)

#: A job id no backup has (32 lowercase hex digits, as the route's pattern wants).
UNKNOWN_JOB_ID = "0" * 32

#: Seconds a backup or a check may take on a loaded machine. Every wait still ends.
JOB_SECONDS = 900.0


# =============================================================================
# A server of the test
# =============================================================================


class Server(owner.Server):
    """``test_backup_roundtrip_owner.Server`` (cookie sessions, a new process per start), self-hosted: no managed profile,
    the panel's variables of ``test_backup_roundtrip_l3`` (so a sealed backup can be made), the scheduler off."""

    def environment(self, variables: Mapping[str, str]) -> dict[str, str]:
        env = b3.child_env(self.data_dir)
        env.update(LIBREFOLIO_NO_SCHEDULER="1", LIBREFOLIO_PANEL_PUBLIC_KEYS=l3.PANEL_KEYS_VALUE, LIBREFOLIO_PUBLIC_URL=l3.PUBLIC_URL, LIBREFOLIO_BACKUP_RECIPIENTS=l3.RECIPIENT)
        env.update(variables)
        return env

    def poll_job(self, path: str, what: str, *, cookie: str | None = None, panel: bool = False) -> dict[str, Any]:
        """GET ``path`` until its ``status`` is no longer ``running``; the last body. As the session ``cookie``, or with
        ``panel`` under a new ``backup`` ticket of the panel for each request (a ticket is for one call)."""
        deadline = time.monotonic() + JOB_SECONDS
        while True:
            response = self.call("GET", path, cookie=cookie, headers=panel_ticket() if panel else {})
            assert response.status_code == 200, f"{what}: {owner.shown(response)}"
            body = response.json()
            if body.get("status") != "running":
                return body
            if time.monotonic() >= deadline:
                pytest.fail(f"{what} still runs after {JOB_SECONDS} s: {body}")
            self.keeps_running(owner.POLL_SECONDS, what)


def panel_ticket() -> dict[str, str]:
    """The header of a new ``backup`` ticket of the panel (``test_backup_roundtrip_l3``'s test key)."""
    return {"Authorization": f"Bearer {l3.ticket(l3.SCOPE_BACKUP)}"}


@contextlib.contextmanager
def serve(name: str, data_dir: Path, socket_dir: Path, log_dir: Path) -> Iterator[Server]:
    """A server of the test, killed with its process group at the end whatever happened."""
    found = Server(name, data_dir, socket_dir, log_dir)
    try:
        yield found
    finally:
        found.cleanup()


def sign_in(instance: Server, password: str) -> str:
    """The session of ``ADMIN`` signed in with ``password``."""
    response = instance.call("POST", LOGIN, json={"username": ADMIN, "password": password})
    assert response.status_code == 200, f"{ADMIN} signs in: {owner.shown(response)}"
    cookie = owner.session_of(response)
    assert cookie, "the sign-in answers with a session"
    return cookie


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rows(database: Path, sql: str, *params: Any) -> list[tuple]:
    """``sql`` on ``database``, read-only: the server is stopped when the test reads it."""
    with closing(sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True)) as conn:
        return conn.execute(sql, params).fetchall()


def leaks(log_dir: Path, data_dir: Path) -> list[str]:
    """The log files (the children's output, the data directory's ``logs/``) that hold one of ``SECRETS``: which file
    and which secret's index, never the secret."""
    files = sorted(log_dir.glob("*.log"))
    logs = data_dir / "logs"
    if logs.is_dir():
        files += sorted(path for path in logs.rglob("*") if path.is_file() and not path.is_symlink())
    assert files, "barrier: the children wrote a log to search"
    found = []
    for path in files:
        content = path.read_bytes()
        found += [f"{path} holds secret #{index}" for index, secret in enumerate(SECRETS) if secret.encode() in content]
    return found


# =============================================================================
# The source: populated, three backups kept, then changed
# =============================================================================


@dataclass(frozen=True)
class Kept:
    """The populated source (stopped), the three backups it keeps, and what changed after them."""

    root: Path
    clear: dict[str, Any]
    secure: dict[str, Any]
    sealed: dict[str, Any]
    later_broker: str
    avatar: bytes


@pytest.fixture(scope="module")
def socket_dir() -> Iterator[Path]:
    directory = Path(tempfile.mkdtemp(prefix="lf-c9b-", dir=owner.SHORT_TMP))
    yield directory
    shutil.rmtree(directory, ignore_errors=True)


def archive_of(data_dir: Path, job: dict[str, Any]) -> Path:
    """The archive of the kept backup ``job`` in ``data_dir``: ``backups/<folder>/<file name>``, the one folder named
    after its job id."""
    found = [folder / job["file_name"] for folder in (data_dir / "backups").iterdir() if folder.name.endswith(f"-{job['job_id'][:8]}")]
    assert len(found) == 1 and found[0].is_file(), f"barrier: one kept folder holds the archive of {job['job_id']}: {found}"
    return found[0]


def backed_up(instance: Server, cookie: str, body: dict[str, Any] | None) -> dict[str, Any]:
    """A backup through ``POST /backup/instance``, polled until it ends; done, without an error."""
    started = instance.call("POST", BACKUP_INSTANCE, cookie=cookie, json=body)
    assert started.status_code == 202, f"the administrator starts a backup: {owner.shown(started)}"
    job = instance.poll_job(f"{BACKUP_JOBS}/{started.json()['job_id']}", "the backup", cookie=cookie)
    assert (job["status"], job.get("error_code")) == ("done", None), f"precondition: the backup is done: {job}"
    return job


@pytest.fixture(scope="module")
def kept(tmp_path_factory, socket_dir) -> Kept:
    """The project's mock data in a new instance, served; a clear, a secure and a sealed backup of it, kept; then the
    administrator's password changed and a broker created; the server stopped."""
    base = tmp_path_factory.mktemp("c9b-source")
    root = base / "source"
    root.mkdir()
    b3.populate(root)
    b3.assert_populated(root / DATABASE_ENTRY)
    [(avatar_url,)] = rows(root / DATABASE_ENTRY, "SELECT s.avatar_url FROM user_settings AS s JOIN users AS u ON u.id = s.user_id WHERE u.username = ?", ADMIN)
    assert avatar_url and avatar_url.startswith(f"{API}/uploads/file/"), f"precondition: the populate gives {ADMIN} an uploaded avatar: {avatar_url}"
    file_id = avatar_url.rsplit("/", 1)[1]
    pictures = [path for path in (root / "custom-uploads").glob(f"{file_id}.*") if path.suffix != ".json"]
    assert len(pictures) == 1, f"precondition: the avatar of {ADMIN} is one file of the uploads: {pictures}"
    avatar = pictures[0].read_bytes()
    later_broker = f"C9B broker after the backup {unique_id()}"

    with serve("source", root, socket_dir, base) as found:
        found.start({})
        cookie = sign_in(found, ADMIN_PASSWORD)
        options = found.call("GET", BACKUP_OPTIONS, cookie=cookie)
        assert options.status_code == 200 and options.json()["password_rules"], f"the rules of a backup's password: {owner.shown(options)}"
        clear = backed_up(found, cookie, None)
        secure = backed_up(found, cookie, {"password": BACKUP_PASSWORD})
        assert (clear["encrypted"], secure["encrypted"], secure["sealed"]) == (False, True, False), f"precondition: a clear and a secure backup: {clear}, {secure}"
        started = found.call("POST", PANEL_JOBS, headers=panel_ticket())
        assert started.status_code == 202, f"the panel starts a backup: {owner.shown(started)}"
        sealed = found.poll_job(f"{PANEL_JOBS}/{started.json()['job_id']}", "the panel's backup", panel=True)
        assert (sealed["status"], sealed["sealed"]) == ("done", True), f"precondition: a sealed backup: {sealed}"

        listed = found.call("GET", BACKUP_JOBS, cookie=cookie)
        assert listed.status_code == 200, f"the kept backups: {owner.shown(listed)}"
        kept_jobs = {item["job_id"]: item for item in listed.json()["items"]}
        for job, origin in ((clear, "ui"), (secure, "ui"), (sealed, "panel")):
            assert job["job_id"] in kept_jobs and kept_jobs[job["job_id"]]["origin"] == origin, f"the backup {job['job_id']} is kept, made by {origin}: {sorted(kept_jobs)}"

        # The instance moves on: what the backups do not hold.
        changed = found.call("POST", CHANGE_PASSWORD, cookie=cookie, json={"current_password": ADMIN_PASSWORD, "new_password": CHANGED_PASSWORD})
        assert changed.status_code == 200, f"the administrator changes the password: {owner.shown(changed)}"
        cookie = owner.session_of(changed) or sign_in(found, CHANGED_PASSWORD)
        created = found.call("POST", BROKERS, cookie=cookie, json=[{"name": later_broker}])
        assert created.status_code in (200, 201) and created.json().get("success_count", 1) == 1, f"a broker created after the backups: {owner.shown(created)}"
        found.stop()

    assert leaks(base, root) == [], f"no password in a log of the source: {leaks(base, root)}"
    assert rows(root / DATABASE_ENTRY, "SELECT count(*) FROM brokers WHERE name = ?", later_broker) == [(1,)], "precondition: the later broker is in the source"
    for job in (clear, secure, sealed):
        assert sha256_of(archive_of(root, job)) == job["file_sha256"], f"precondition: the kept archive of {job['job_id']} is the job's"
    assert not b3.production_of(root).exists(), "a child wrote in its production data directory"
    return Kept(root=root, clear=clear, secure=secure, sealed=sealed, later_broker=later_broker, avatar=avatar)


@pytest.fixture
def instance(kept, tmp_path, socket_dir, request) -> Iterator[tuple[Server, Path]]:
    """A copy of the source, for one test, served; at the end, killed if still running, and no log holds a password."""
    root = tmp_path / "instance"
    shutil.copytree(kept.root, root, symlinks=True)
    logs = tmp_path / "logs"
    logs.mkdir()
    # A short name of its own: its socket and logs are named after it.
    name = "t" + hashlib.sha256(request.node.name.encode()).hexdigest()[:5]
    with serve(name, root, socket_dir, logs) as found:
        found.start({})
        yield found, root
    assert leaks(logs, root) == [], f"no password in a log: {leaks(logs, root)}"
    assert not b3.production_of(root).exists(), "a child wrote in its production data directory"


# =============================================================================
# The check of a kept backup
# =============================================================================


def taken(instance: Server, cookie: str, job: dict[str, Any], kind: str) -> dict[str, Any]:
    """``from-backup`` on the kept backup ``job``: an upload of ``kind``, the archive's size."""
    response = instance.call("POST", FROM_BACKUP, cookie=cookie, json={"job_id": job["job_id"]})
    assert response.status_code == 201, f"the kept backup taken for a restore: {owner.shown(response)}"
    upload = response.json()
    assert (upload["kind"], upload["size"]) == (kind, job["file_size"]), f"an upload of the kept archive: {upload}, {job}"
    return upload


def checked(instance: Server, cookie: str, upload_id: str, password: str | None = None) -> dict[str, Any]:
    """The check of ``upload_id`` started and polled to its end: done, with a report."""
    body: dict[str, Any] = {"upload_id": upload_id}
    if password is not None:
        body["password"] = password
    staged = instance.call("POST", RESTORE_STAGE, cookie=cookie, json=body)
    assert staged.status_code == 202, f"the check starts: {owner.shown(staged)}"
    check = instance.poll_job(f"{RESTORE_STAGE}/{staged.json()['stage_id']}", "the check", cookie=cookie)
    assert (check["status"], check.get("error_code")) == ("done", None) and check["report"] is not None, f"the check ends with a report: {check}"
    return check


def assert_report(report: dict[str, Any]) -> None:
    assert report["restorable"] is True, f"restorable: blockers {report['blockers']}, warnings {report['warnings']}"
    assert ADMIN in report["administrators"], f"{ADMIN} is an administrator of the backup: {report['administrators']}"
    assert report["uploads_size"] > 0, f"the backup's uploads are measured (the avatars at least): {report['uploads_size']}"
    assert isinstance(report["broker_reports_size"], int) and report["broker_reports_size"] >= 0, f"the backup's broker reports are measured: {report['broker_reports_size']}"
    assert report["secrets_unreadable"] == {"system": 0, "user": 0}, f"every secret readable on its own instance: {report['secrets_unreadable']}"


def assert_peeks(instance: Server, cookie: str, stage_id: str, avatar: bytes) -> None:
    """``verify-password`` and ``avatar`` on the opened copy of ``stage_id``."""
    verify = f"{RESTORE_STAGE}/{stage_id}/verify-password"
    answers = {}
    for label, password in (("backup's", ADMIN_PASSWORD), ("today's", CHANGED_PASSWORD), ("wrong", WRONG_ACCOUNT_PASSWORD)):
        response = instance.call("POST", verify, cookie=cookie, json={"username": ADMIN, "password": password})
        assert response.status_code == 200, f"verify-password with the {label} password: {owner.shown(response)}"
        answers[label] = response.json()["matches"]
    assert answers == {"backup's": True, "today's": False, "wrong": False}, f"only the password of the backup matches: {answers}"
    for username in (f"c9b_nobody_{unique_id()}", PLAIN_USER):
        refused = instance.call("POST", verify, cookie=cookie, json={"username": username, "password": ADMIN_PASSWORD})
        assert (refused.status_code, owner.code_of(refused)) == (404, "restore_admin_not_found"), f"{username} is not an administrator of the backup: {owner.shown(refused)}"

    picture = instance.call("GET", f"{RESTORE_STAGE}/{stage_id}/avatar/{ADMIN}", cookie=cookie)
    assert picture.status_code == 200, f"the administrator's avatar from the copy: {owner.shown(picture)}"
    assert picture.content == avatar and picture.headers.get("content-type", "").startswith("image/"), f"the avatar is the picture the backup holds: {picture.headers.get('content-type')}, {len(picture.content)} bytes"
    missing = instance.call("GET", f"{RESTORE_STAGE}/{stage_id}/avatar/c9b_nobody_{unique_id()}", cookie=cookie)
    assert (missing.status_code, owner.code_of(missing)) == (404, "restore_avatar_not_found"), f"no avatar for an unknown account: {owner.shown(missing)}"


def test_the_clear_kept_backup_is_checked_from_the_server_and_stays(kept, instance):
    """§2 and §4: the clear backup linked, checked, peeked into and dropped, its archive kept as it was; the sealed backup
    and an unknown id refused, no upload left."""
    print_section("C9-B The clear kept backup, checked from the server")
    server, root = instance
    cookie = sign_in(server, CHANGED_PASSWORD)

    # §4 Refusals first: nothing linked.
    sealed_archive = archive_of(root, kept.sealed)
    refused = server.call("POST", FROM_BACKUP, cookie=cookie, json={"job_id": kept.sealed["job_id"]})
    assert (refused.status_code, owner.code_of(refused)) == (409, "backup_sealed_unsupported"), f"a sealed backup is not restored here: {owner.shown(refused)}"
    refused = server.call("POST", FROM_BACKUP, cookie=cookie, json={"job_id": UNKNOWN_JOB_ID})
    assert (refused.status_code, owner.code_of(refused)) == (404, "backup_job_not_found"), f"no backup has this id: {owner.shown(refused)}"
    assert sealed_archive.stat().st_nlink == 1 and sha256_of(sealed_archive) == kept.sealed["file_sha256"], "the sealed archive stays as it was, never linked"

    # §2 The clear backup: a hard link, then the check.
    archive = archive_of(root, kept.clear)
    assert archive.stat().st_nlink == 1, "precondition: the kept archive has one name"
    upload = taken(server, cookie, kept.clear, "zip")
    assert archive.stat().st_nlink == 2, "the upload is a hard link to the kept archive: no byte copied"
    check = checked(server, cookie, upload["upload_id"])
    report = check["report"]
    assert_report(report)
    assert (report["encrypted"], report["instance_key_included"]) == (False, False), f"a clear backup: {report['encrypted']}, {report['instance_key_included']}"
    assert archive.is_file() and archive.stat().st_nlink == 1, "the check removed its link, never the kept archive"
    assert sha256_of(archive) == kept.clear["file_sha256"], "the kept archive is unchanged"

    assert_peeks(server, cookie, check["stage_id"], kept.avatar)

    dropped = server.call("DELETE", f"{RESTORE_STAGE}/{check['stage_id']}", cookie=cookie)
    assert dropped.status_code == 204, f"the check is dropped: {owner.shown(dropped)}"
    gone = server.call("POST", f"{RESTORE_STAGE}/{check['stage_id']}/verify-password", cookie=cookie, json={"username": ADMIN, "password": ADMIN_PASSWORD})
    assert gone.status_code in (404, 409), f"a dropped check has no copy to read: {owner.shown(gone)}"
    assert archive.is_file() and sha256_of(archive) == kept.clear["file_sha256"], "dropping the check keeps the archive"
    listed = server.call("GET", BACKUP_JOBS, cookie=cookie)
    assert listed.status_code == 200 and {kept.clear["job_id"], kept.secure["job_id"], kept.sealed["job_id"]} <= {item["job_id"] for item in listed.json()["items"]}, f"every backup still kept: {owner.shown(listed)}"
    server.stop()
    print_success(f"zip of {upload['size']} bytes linked, checked, {len(report['administrators'])} administrators, password verified, archive kept")


# =============================================================================
# The restore of the secure kept backup
# =============================================================================


def test_the_secure_kept_backup_is_restored_and_the_verified_password_signs_in(kept, instance):
    """§3: the secure backup's password asked and checked, the check, the password verified on the copy, the confirmation,
    the restart, a new process commits it; the verified password signs in, today's does not, the later broker is gone."""
    print_section("C9-B The secure kept backup, restored to the end")
    server, root = instance
    cookie = sign_in(server, CHANGED_PASSWORD)

    archive = archive_of(root, kept.secure)
    upload = taken(server, cookie, kept.secure, "envelope")
    refused = server.call("POST", RESTORE_STAGE, cookie=cookie, json={"upload_id": upload["upload_id"]})
    assert (refused.status_code, owner.code_of(refused)) == (400, "password_required"), f"a secure backup asks its password: {owner.shown(refused)}"
    refused = server.call("POST", RESTORE_STAGE, cookie=cookie, json={"upload_id": upload["upload_id"], "password": WRONG_BACKUP_PASSWORD})
    assert (refused.status_code, owner.code_of(refused)) == (400, "wrong_password"), f"a wrong password is refused, the upload kept: {owner.shown(refused)}"
    check = checked(server, cookie, upload["upload_id"], BACKUP_PASSWORD)
    stage_id = check["stage_id"]
    report = check["report"]
    assert_report(report)
    assert report["encrypted"] is True, f"a secure backup: {report['encrypted']}"
    assert archive.is_file() and sha256_of(archive) == kept.secure["file_sha256"], "the check keeps the kept archive as it was"

    assert_peeks(server, cookie, stage_id, kept.avatar)

    confirmed = server.call("POST", f"{RESTORE_STAGE}/{stage_id}/confirm", cookie=cookie)
    assert confirmed.status_code == 202 and confirmed.json()["state"] == "pending", f"the administrator confirms: {owner.shown(confirmed)}"
    restarted = server.call("POST", RESTORE_RESTART, cookie=cookie)
    assert restarted.status_code == 202, f"the restart is asked: {owner.shown(restarted)}"
    server.exits("the restart the administrator asked")

    # A new process, the same environment: the restore applied and committed.
    server.start({})
    old_session = server.call("GET", ME, cookie=cookie)
    assert old_session.status_code == 401, f"no session of before the restore: {owner.shown(old_session)}"
    refused = server.call("POST", LOGIN, json={"username": ADMIN, "password": CHANGED_PASSWORD})
    assert refused.status_code == 401, f"the password of before the restore no longer signs in: {owner.shown(refused)}"
    cookie = sign_in(server, ADMIN_PASSWORD)
    state = server.call("GET", RESTORE_STATUS, cookie=cookie)
    assert state.status_code == 200 and (state.json()["state"], state.json()["stage_id"]) == ("committed", stage_id), f"committed by the new process: {owner.shown(state)}"
    server.stop()
    assert rows(root / DATABASE_ENTRY, "SELECT count(*) FROM brokers WHERE name = ?", kept.later_broker) == [(0,)], "the broker created after the backup is gone"
    print_success(f"envelope of {upload['size']} bytes: password asked, checked, verified, confirmed, restarted, committed; {ADMIN} signs in with the verified password")

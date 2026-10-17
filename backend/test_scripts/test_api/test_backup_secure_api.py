"""
The «secure» backup through the API (workstream B, lot B4; decisions 38 and 39, P12): a backup protected by a password
(an ``.lfbk`` envelope), the options that publish the rules of that password, and the restore of such an archive.

Under test, as the frozen contract of B4 says them (§3-§5): ``backend/app/api/v1/backup/instance.py`` (``POST
/backup/instance`` and its optional body ``InstanceBackupRequest``, ``GET /backup/instance/options``), ``panel.py``
(which never encrypts), ``restore.py`` (``RestoreUpload.kind``; ``POST /backup/restore/stage`` and its ``password``; the
new fields of the report), the schemas of ``backend/app/schemas/backup.py``, and the 422 without ``input``
(``api/no_echo.py``) on both routers. The services underneath (``envelope.py``, ``secure.py``, ``jobs.py``,
``restore_jobs.py``, ``staging.py``) have suites of their own.

On the lane's server, with this module's administrator and ordinary user (as ``test_backup_api.py``):

- SECURE-001 ``GET /backup/instance/options``: 200 to an administrator with the archive's password rules, A's five in
  their order, ``min_length`` raised to 12 and the others without a value; 403 to an ordinary user; 401 without a
  session.
- SECURE-002 ``POST /backup/instance`` with a password the archive's rules refuse (one A's own rules accept but shorter
  than 12 included): 400 ``password_too_weak`` with the codes it fails in the rules' order, never the password, and
  nothing started: a clear start right after it answers 202, not 409 ``backup_busy``, and is the one job the lane
  gained.
- SECURE-003 with a password the rules accept: 202, the job ends done, ``encrypted``, named
  ``librefolio-backup-YYYYMMDD-HHMMSS.lfbk``. The download, served as ``application/octet-stream``, is the envelope of §1
  as B4 writes it (``LFBK``, format 1, scrypt with ``log2(n) = 15``, ``r = 8``, ``p = 1``, chunks of 1 MiB); opened here
  with the password it is a backup zip whose manifest says whether it carries the instance key, and carries it exactly
  then, with its SHA-256 and outside ``files``. The job's folder holds its state and the envelope only (no clear zip); no
  answer, no download header and no ``state.json`` holds the password.
- SECURE-004 no body, ``{}`` and ``{"password": null}``: a clear backup as before, ``encrypted`` false, a ``.zip`` still
  served as ``application/zip``, never in phase ``encrypting``.
- SECURE-005 a password that is not a string, one of 1025 characters, another field beside it: 422, each error without
  ``input``, the value nowhere in the answer, no job.

In an app of the test (as ``test_backup_panel.py`` and ``test_backup_restore.py``):

- SECURE-006 the hosting panel's start, with its token and a password in the body: a real backup of a data directory
  under ``tmp_path``, ``encrypted`` false, a zip without the instance key, and no key file made.
- SECURE-007 an upload that starts with ``LFBK`` is ``kind`` ``envelope``; a zip is ``zip``.
- SECURE-008 the check of an envelope: without a password 400 ``password_required``, with a wrong one 400
  ``wrong_password``, each time the upload kept, no check written and the lock let go; then the right one with the same
  upload id: 202, done, the report ``encrypted``, ``instance_key_included`` false, nothing unreadable nor re-encrypted
  (that backup holds no secret), and the decrypted zip not left beside the copy.
- SECURE-009 an envelope that cannot be opened: ``LFBK`` and 16 bytes, 400 ``envelope_damaged``; a valid header but
  ``log2(n) = 30``, 409 ``envelope_unsupported``; the same answer to a second try with the same upload id, never 404
  ``backup_upload_not_found``.
- SECURE-010 a zip checked with a password: the password ignored, the check done, ``encrypted`` false.
- SECURE-011 a check asked with a password that is not a string, of 1025 characters, or another field: 422 without
  ``input``, the value nowhere in the answer, nothing started.
- SECURE-012 a clear zip whose database holds a system secret and a user secret of the instance that made it: the report
  says both unreadable, none re-encrypted, ``encrypted`` false; the copy keeps them as they were.
- SECURE-013 the same backup as an envelope carrying that instance's key (B4b, announced by the manifest with its
  SHA-256): both secrets re-encrypted, none unreadable, ``instance_key_included``; on the copy they open with this
  instance's subkey under its key id, and no ``secrets/`` was unpacked.
- SECURE-014 OpenAPI: both request models, the options, ``encrypted``, the phases ``encrypting`` and ``decrypting``, the
  warning ``instance_key_unusable``, ``kind``, ``RestoreSecretCounts``; a job's download as ``application/zip`` and as
  ``application/octet-stream``; the two codes a check gains, ``password_required`` and ``envelope_damaged``, and not
  ``wrong_password`` nor ``envelope_unsupported``, which no check ends with: ``POST /backup/restore/stage`` answers them
  itself, and documents them in its 400 and its 409.

Red today, each for the contract's reason alone: ``/backup/instance/options`` does not exist (404); ``POST
/backup/instance`` reads no body (202, a clear backup); no job, upload or report carries the new fields; every download
is ``application/zip``; ``RestoreStageRequest`` forbids ``password``, and its 422 echoes the input. No module of B4 is
imported: the envelopes are built and opened here, by the layout of §1, with the scrypt and the AES-GCM of
``cryptography``. So the tests fail on the routes alone, and they hold the server to the contract rather than to its own
encoder.

Ownership. The lane part registers an administrator (promoted in this process with ``user_service.set_user_admin``) and
an ordinary user, deleted at the module's end; every job a test starts, a start that should have been refused and
answered 202 included, is waited for and deleted through the API at its teardown, after a red too. The in-process part
writes under ``tmp_path`` only: the process's own data directory is configured to a folder of the test that must stay
absent (``test_backup_staging.configure``), this instance's key is set in the environment (no key file is generated),
the checks run at once in fake threads, and every check is dropped (through the API, or at the teardown after a red).
The real databases and archives are ``test_backup_staging.py``'s module fixtures, as ``test_backup_restore.py`` takes
them.

Isolation. The lane part shares one global surface, the lane's backup run lock (``backups/.jobs/.lock``), which every
backup of the lane takes. Like ``api backup``, whose module states the same premise, this unit assumes that no other
unit starts a backup on the lane while it runs: SECURE-002 and SECURE-005 read the lane's new jobs, and SECURE-002
asserts that a start right after a refusal is not busy. The catalogue must keep the two from running together. Every
start first waits, with a deadline, for the lock to be free; no sleep stands in for a state.
"""

from __future__ import annotations

import asyncio
import email.message
import hmac
import io
import json
import os
import re
import secrets
import sqlite3
import threading
import time
import unicodedata
import uuid
import zipfile
from collections.abc import Callable, Coroutine, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.auth import SESSION_COOKIE_NAME, get_current_user
from backend.app.api.v1.backup import backup_router, restore
from backend.app.config import get_data_dir, get_settings
from backend.app.db.session import get_async_engine
from backend.app.services.accounts import user_service
from backend.app.services.platform.instance_backup import paths, restore_jobs
from backend.app.services.platform.instance_backup.jobs import _RunLock
from backend.app.services.platform.instance_backup.paths import DATABASE_ENTRY, MANIFEST_ENTRY, RESTORE_FOLDER, STAGE_DATA_FOLDER, STAGE_REPORT_FILE, STATE_FILE, checks_dir, stage_data_dir, stage_dir, uploads_dir
from backend.app.services.platform.instance_key import derive_key_from
from backend.app.services.plugin_settings.crypto import SUBKEY_LENGTH, SUBKEY_PURPOSE, UnreadableSecretError, decrypt_secret, encrypt_secret, key_id_of, secret_aad
from backend.app.utils.runtime.version import get_git_version
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_services import test_backup_staging as cases
from backend.test_scripts.test_utils import print_section, print_success

# The module fixtures of test_backup_staging.py (lot B2a), as test_backup_restore.py takes them: two real databases made
# once by alembic in a process of their own, and the archive of a data directory at the head.
databases = cases.databases
head_archive = cases.head_archive

# =============================================================================
# Constants
# =============================================================================

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
INSTANCE_URL = f"{API_BASE}/backup/instance"
OPTIONS_URL = f"{INSTANCE_URL}/options"
TIMEOUT = 30.0
#: Seconds a backup may take on a loaded machine: a hang still ends.
JOB_DEADLINE_S = 120.0
#: Seconds between two reads of the state a wait polls.
POLL_INTERVAL_S = 0.1
#: The password of this module's accounts on the lane.
ACCOUNT_PASSWORD = "TestPass123!"

#: The archive passwords of this module, test values only. Both meet the archive's rules.
PASSWORD = "Correct-Horse-Battery-9"
WRONG_PASSWORD = "Wrong-Password-123!"
#: What the check of a zip is sent as a password, to be ignored (SECURE-010).
IGNORED_PASSWORD = "anything"

#: The archive's password rules (§4, P12): A's five rules in their order, the minimum length raised from A's 8 to 12.
ARCHIVE_RULES = [
    {"code": "min_length", "value": 12},
    {"code": "uppercase", "value": None},
    {"code": "lowercase", "value": None},
    {"code": "digit", "value": None},
    {"code": "special", "value": None},
]
#: Passwords the archive's rules refuse, with the codes each fails, in the rules' order. Neither is a word an English
#: message could hold ("short" could be, in "too short"), so "the answer never carries the password" cannot hold by
#: chance: seven characters without an uppercase letter or a symbol; eleven with every class, which A's own rules accept.
WEAK_PASSWORDS = [
    pytest.param("xq7vbnm", ["min_length", "uppercase", "special"], id="seven-characters-no-uppercase-no-symbol"),
    pytest.param("Tiny-Pass-1", ["min_length"], id="eleven-characters-every-class"),
]
#: The starts that ask for a clear backup: no body, an empty object, a null password (§4).
CLEAR_STARTS = [
    pytest.param({}, id="no-body"),
    pytest.param({"json": {}}, id="empty-object"),
    pytest.param({"json": {"password": None}}, id="null-password"),
]
#: Malformed bodies of a start or a check, as (the fields beside upload_id, the field the 422 is at, the value it must
#: not echo).
MALFORMED = [
    pytest.param({"password": 123}, "password", 123, id="password-not-a-string"),
    pytest.param({"password": "x" * 1025}, "password", "x" * 1025, id="password-over-1024-characters"),
    pytest.param({"password": PASSWORD, "extra": 1}, "extra", PASSWORD, id="another-field"),
]
#: The same, for a check, with the value the brief names for a password that is not a string.
MALFORMED_CHECKS = [
    pytest.param({"password": 5}, "password", 5, id="password-not-a-string"),
    pytest.param({"password": "x" * 1025}, "password", "x" * 1025, id="password-over-1024-characters"),
    pytest.param({"password": PASSWORD, "extra": 1}, "extra", PASSWORD, id="another-field"),
]

CLEAR_ARCHIVE = re.compile(r"librefolio-backup-\d{8}-\d{6}\.zip")
SECURE_ARCHIVE = re.compile(r"librefolio-backup-\d{8}-\d{6}\.lfbk")
#: The phases of a job: a clear backup's, and a secure one's, which may also be seen encrypting.
CLEAR_PHASES = {"preparing", "database", "files", "finalizing"}
SECURE_PHASES = CLEAR_PHASES | {"encrypting"}
ZIP_MAGIC = b"PK\x03\x04"
#: The media type a job's download is served as (``job_views.job_file``): a clear backup's zip, and a secure backup's
#: envelope, which is not a zip.
ZIP_MEDIA_TYPE = "application/zip"
ENVELOPE_MEDIA_TYPE = "application/octet-stream"
#: The entry of the instance key in a secure archive (§4, B4b): never listed in the manifest's files.
KEY_ENTRY = "secrets/instance.key"
#: What a field the answer lacks reads as, in a message.
ABSENT = "<absent>"
#: The report's fields of B4.
SECURE_FIELDS = ("encrypted", "instance_key_included", "secrets_unreadable", "secrets_rekeyed")
#: The codes a check can now end with (``RestoreStage.error_code``, B4): an envelope staged without a key, a chunk that
#: fails. Only these two: that enum is what checks produce, and ``test_backup_restore.py`` holds it to exactly that.
CHECK_END_CODES = {"password_required", "envelope_damaged"}
#: The codes only ``POST /backup/restore/stage`` answers, before any check exists, by the status it answers them with:
#: never a check's end, so never in that enum, and documented in that status's answer of the route instead.
STAGE_ANSWER_CODES = {"400": "wrong_password", "409": "envelope_unsupported"}

#: The envelope of §1: its magic, its header (52 bytes, big-endian), the tag after each chunk.
ENVELOPE_MAGIC = b"LFBK"
HEADER_SIZE = 52
TAG_SIZE = 16
#: What B4 writes (P12): format 1, scrypt, log2(n) = 15, r = 8, p = 1, chunks of 1 MiB.
WRITTEN = {"version": 1, "kdf": 1, "log2_n": 15, "r": 8, "p": 1, "chunk_size": 1 << 20}
#: What the envelopes of this module use: the cheapest scrypt a reader takes, and chunks of 64 KiB, the smallest it
#: takes, so that an archive is several chunks.
TEST_LOG2_N = 14
TEST_CHUNK_SIZE = 1 << 16

#: The apps of the test, in this process.
IN_PROCESS = "http://in-process"
PANEL = "/api/v1/backup/panel/jobs"
RESTORE = "/api/v1/backup/restore"
UPLOAD = f"{RESTORE}/upload"
STAGE = f"{RESTORE}/stage"
ADMIN = SimpleNamespace(id=1, username="b4-admin", is_superuser=True)
#: The variables of this lot, as .env.example and the deployments write them: spelled out here, so a rename shows.
TOKEN_VARIABLE = "LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN"
TOKEN_FILE_VARIABLE = "LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN_FILE"
INSTANCE_KEY_VARIABLE = "LIBREFOLIO_INSTANCE_KEY"
INSTANCE_KEY_FILE_VARIABLE = "LIBREFOLIO_INSTANCE_KEY_FILE"
PROFILE_VARIABLE = "LIBREFOLIO_PROFILE"
LIMIT_VARIABLE = "LIBREFOLIO_BACKUP_MAX_UPLOAD_MB"
#: This instance's key in the in-process tests, and the key of the instance a backup comes from: test values of at least
#: 32 characters (``INSTANCE_KEY_MIN_LENGTH``), never real keys.
THIS_INSTANCE_KEY = "test-only-key-of-the-instance-that-restores-b4-0001"
OTHER_INSTANCE_KEY = "test-only-key-of-the-instance-that-made-the-backup-b4-0002"
#: The secrets the instance that made the backup stored: (scope, family, plugin, field, owner's username, plaintext).
SECRET_ROWS = (
    ("system", "asset", "mockprov", "api_key", None, "not-a-real-api-key-b4"),
    ("user", "asset", "mockprov", "personal_token", cases.ACCOUNTS[0][0], "not-a-real-token-b4"),
)
#: Each secret as a key that reads it sees it: (scope, field, under that key's id, plaintext).
SECRETS_READABLE = sorted((scope, field_key, True, plaintext) for scope, _family, _plugin, field_key, _owner, plaintext in SECRET_ROWS)

# =============================================================================
# The envelope of §1, built and opened by the test
# =============================================================================


@dataclass(frozen=True)
class EnvelopeHeader:
    """The 52 bytes before the chunks, as §1 lays them out: magic, version, kdf, log2(n), r, p, salt (16), check (16),
    chunk size (u32), nonce prefix (7)."""

    raw: bytes
    version: int
    kdf: int
    log2_n: int
    r: int
    p: int
    salt: bytes
    check: bytes
    chunk_size: int
    nonce_prefix: bytes

    @classmethod
    def parse(cls, raw: bytes) -> EnvelopeHeader:
        assert len(raw) == HEADER_SIZE and raw[:4] == ENVELOPE_MAGIC, f"an envelope starts with a header of {HEADER_SIZE} bytes, LFBK first: {raw[:12]!r}"
        return cls(raw, raw[4], raw[5], raw[6], raw[7], raw[8], raw[9:25], raw[25:41], int.from_bytes(raw[41:45], "big"), raw[45:52])

    @property
    def parameters(self) -> dict[str, int]:
        return {"version": self.version, "kdf": self.kdf, "log2_n": self.log2_n, "r": self.r, "p": self.p, "chunk_size": self.chunk_size}


def derived_key(password: str, salt: bytes, log2_n: int, r: int, p: int) -> tuple[bytes, bytes]:
    """The AES-256 key and the check value of §1: bytes 0-31 and 32-47 of scrypt (48 bytes) of the NFC password in UTF-8."""
    derived = Scrypt(salt=salt, length=48, n=2**log2_n, r=r, p=p).derive(unicodedata.normalize("NFC", password).encode("utf-8"))
    return derived[:32], derived[32:]


def chunk_nonce(prefix: bytes, counter: int, last: bool) -> bytes:
    """The nonce of a chunk: the prefix (7 bytes), the chunk's counter (u32, big-endian, from 0), then 1 on the last one."""
    return prefix + counter.to_bytes(4, "big") + (b"\x01" if last else b"\x00")


def seal(plain: bytes, password: str, *, log2_n: int = TEST_LOG2_N, chunk_size: int = TEST_CHUNK_SIZE) -> bytes:
    """``plain`` as an envelope of §1: a fresh salt and nonce prefix, r = 8, p = 1, the header as every chunk's associated
    data, at least one chunk."""
    salt, prefix = os.urandom(16), os.urandom(7)
    key, check = derived_key(password, salt, log2_n, 8, 1)
    header = ENVELOPE_MAGIC + bytes([1, 1, log2_n, 8, 1]) + salt + check + chunk_size.to_bytes(4, "big") + prefix
    assert len(header) == HEADER_SIZE, f"precondition: a header of {HEADER_SIZE} bytes, not {len(header)}"
    pieces = [plain[offset : offset + chunk_size] for offset in range(0, len(plain), chunk_size)] or [b""]
    aes = AESGCM(key)
    return header + b"".join(aes.encrypt(chunk_nonce(prefix, index, index == len(pieces) - 1), piece, header) for index, piece in enumerate(pieces))


def unseal(source: Path, target: Path, password: str) -> EnvelopeHeader:
    """Open the envelope ``source`` with ``password`` into ``target`` (a new file), chunk by chunk, as §1 makes one: its
    header. A password that does not give the header's check value, or a chunk that does not decrypt, fails the test."""
    with source.open("rb") as envelope, target.open("xb") as plain:
        header = EnvelopeHeader.parse(envelope.read(HEADER_SIZE))
        key, check = derived_key(password, header.salt, header.log2_n, header.r, header.p)
        assert hmac.compare_digest(check, header.check), "the password must give the check value of the header (bytes 32-47 of scrypt, §1)"
        aes = AESGCM(key)
        sealed_size = header.chunk_size + TAG_SIZE
        counter, current = 0, envelope.read(sealed_size)
        while True:
            following = envelope.read(sealed_size)
            try:
                plain.write(aes.decrypt(chunk_nonce(header.nonce_prefix, counter, not following), current, header.raw))
            except InvalidTag:
                raise AssertionError(f"chunk {counter} does not decrypt as §1 makes a chunk: the nonce prefix, the counter, the flag of the last chunk, the header as associated data") from None
            if not following:
                return header
            counter, current = counter + 1, following


def with_byte(data: bytes, index: int, value: int) -> bytes:
    """``data`` with its byte ``index`` set to ``value``."""
    changed = bytearray(data)
    changed[index] = value
    return bytes(changed)


# =============================================================================
# Answers
# =============================================================================


def shown(response: httpx.Response) -> str:
    """An answer read in full, for an assertion's message."""
    return f"{response.request.method} {response.request.url} answered {response.status_code}: {response.text[:800]}"


def code(response: httpx.Response) -> tuple[int, str | None]:
    """Status and ``detail.code``; None for an answer without one."""
    if not response.headers.get("content-type", "").startswith("application/json"):
        return response.status_code, None
    body = response.json()
    detail = body.get("detail") if isinstance(body, dict) else None
    return response.status_code, detail.get("code") if isinstance(detail, dict) else None


def carries(response: httpx.Response, value: object) -> bool:
    """Whether the answer holds ``value``: a text anywhere in its body; anything else as a value of its JSON."""
    if isinstance(value, str):
        return value in response.text
    try:
        pending = [response.json()]
    except ValueError:
        return False
    while pending:
        current = pending.pop()
        if isinstance(current, dict):
            pending.extend(current.values())
        elif isinstance(current, list):
            pending.extend(current)
        elif type(current) is type(value) and current == value:
            return True
    return False


def no_echo_problems(response: httpx.Response, value: object, field: str) -> list[str]:
    """What keeps ``response`` from being the 422 of a malformed body (§3): a list of errors, each with ``type``, ``loc``
    and ``msg`` and never ``input``, one of them at ``field``, and ``value`` nowhere in the answer."""
    detail = response.json().get("detail") if response.headers.get("content-type", "").startswith("application/json") and isinstance(response.json(), dict) else None
    if response.status_code != 422 or not isinstance(detail, list) or not detail:
        return [f"expected FastAPI's 422 with its list of errors: {shown(response)}"]
    problems = [f"an error must keep type, loc and msg and drop input: {error}" for error in detail if not isinstance(error, dict) or "input" in error or not {"type", "loc", "msg"} <= set(error)]
    if not any(isinstance(error, dict) and field in error.get("loc", []) for error in detail):
        problems.append(f"no error is at the field {field!r}: {detail}")
    if carries(response, value):
        problems.append(f"the answer carries the value sent (a {type(value).__name__}): {shown(response)}")
    return problems


def secure_fields(report: dict) -> dict[str, Any]:
    """The report's fields of B4, ``ABSENT`` for those it lacks."""
    return {name: report.get(name, ABSENT) for name in SECURE_FIELDS}


def lock_held(path: Path) -> bool:
    """Whether a run holds the lock at ``path`` now: a probe, taken and released at once when free; none is created."""
    if not path.exists():
        return False
    probe = _RunLock(path)
    if probe.try_acquire():
        probe.release()
        return False
    return True


def files_in(folder: Path) -> list[str]:
    """The names in ``folder``; none when it does not exist."""
    return sorted(path.name for path in folder.iterdir()) if folder.is_dir() else []


def content_disposition(header: str) -> tuple[str | None, str | None]:
    """The disposition type and the file name of a ``Content-Disposition`` header, its quoting undone."""
    message = email.message.Message()
    message["Content-Disposition"] = header
    return message.get_content_disposition(), message.get_filename()


# =============================================================================
# The lane's server: this module's accounts, and the jobs its tests start
# =============================================================================


@dataclass(frozen=True)
class Account:
    """A user of this module, logged in on the lane's server: ``client()`` opens a client that carries its session."""

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


def is_superuser(database: Path, username: str) -> bool | None:
    """Whether ``username`` is an administrator in ``database``; None when it has no such user."""
    with closing(cases.read_only(database)) as conn:
        row = conn.execute("SELECT is_superuser FROM users WHERE username = ?", (username,)).fetchone()
    return None if row is None else bool(row[0])


def lane_lock() -> Path:
    """The lane's backup run lock: one per data directory, taken by every backup of the lane."""
    return paths.lock_path(get_data_dir())


def lane_jobs() -> set[str]:
    """The ids of the jobs the lane's data directory holds now."""
    folder = paths.jobs_dir(get_data_dir())
    return {path.name for path in folder.iterdir() if paths.is_job_id(path.name)} if folder.is_dir() else set()


async def wait_until_the_lane_is_free() -> None:
    """Wait, with a deadline, until no backup holds the lane's run lock. Every job of this module is waited for until its
    run has let the lock go: only a run this module did not start could hold it."""
    deadline = time.monotonic() + JOB_DEADLINE_S
    while lock_held(lane_lock()):
        if time.monotonic() >= deadline:
            raise AssertionError(f"the lane's backup run lock stayed held for {JOB_DEADLINE_S:.0f}s by a run this module did not start")
        await asyncio.sleep(POLL_INTERVAL_S)


async def post_start(client: httpx.AsyncClient, created: list[str], **request: Any) -> httpx.Response:
    """``POST /backup/instance`` with ``request`` (``json=...``, or nothing). A job it starts (202) joins ``created``, to
    be deleted at the teardown, a start that should have been refused included."""
    response = await client.post(INSTANCE_URL, **request)
    if response.status_code == 202:
        created.append(response.json()["job_id"])
    return response


async def poll_until_finished(client: httpx.AsyncClient, job_id: str, answers: list[httpx.Response] | None = None) -> httpx.Response:
    """Read the job until it has ended and its run has let the lane's lock go, or until it is gone: the last answer. Every
    answer read joins ``answers``. The run writes its end just before it lets the lock go: the lock is part of the end."""
    deadline = time.monotonic() + JOB_DEADLINE_S
    while True:
        response = await client.get(job_url(job_id))
        if answers is not None:
            answers.append(response)
        if response.status_code != 200 or (response.json()["status"] != "running" and not lock_held(lane_lock())):
            return response
        if time.monotonic() >= deadline:
            raise AssertionError(f"backup job {job_id} has not ended within {JOB_DEADLINE_S:.0f}s: {shown(response)}, lock held: {lock_held(lane_lock())}")
        await asyncio.sleep(POLL_INTERVAL_S)


async def finished(client: httpx.AsyncClient, job_id: str, answers: list[httpx.Response]) -> dict:
    """The final state of a job, read once it has ended and its run has let the lock go."""
    response = await poll_until_finished(client, job_id, answers)
    assert response.status_code == 200, f"a job stays readable until it is deleted: {shown(response)}"
    return response.json()


def running_phases(answers: list[httpx.Response]) -> set[str]:
    """The phases the answers show a job running in."""
    states = [answer.json() for answer in answers if answer.status_code in (200, 202) and answer.headers.get("content-type", "").startswith("application/json")]
    return {state.get("phase") for state in states if isinstance(state, dict) and state.get("status") == "running"}


async def remove_jobs(admin: Account, job_ids: list[str]) -> list[str]:
    """Wait for each job to end, then delete it through the API as the administrator: what could not be removed."""
    problems: list[str] = []
    async with admin.client() as client:
        for job_id in job_ids:
            try:
                last = await poll_until_finished(client, job_id)
                if last.status_code == 404:
                    continue
                response = await client.delete(job_url(job_id))
                if response.status_code not in (204, 404):
                    problems.append(f"job {job_id}: {shown(response)}")
            except Exception as exc:  # every job gets its attempt; the failures are reported together
                problems.append(f"job {job_id}: {exc!r}")
    return problems


async def download(client: httpx.AsyncClient, job_id: str, target: Path) -> httpx.Headers:
    """Stream the archive of a job into ``target``: the headers it came with."""
    async with client.stream("GET", file_url(job_id)) as response:
        if response.status_code != 200:
            await response.aread()
            raise AssertionError(f"the archive of a done job must download: {shown(response)}")
        with target.open("wb") as handle:
            async for chunk in response.aiter_bytes():
                handle.write(chunk)
        return response.headers


async def first_bytes(client: httpx.AsyncClient, job_id: str, size: int) -> tuple[bytes, str]:
    """The first ``size`` bytes of a job's archive, and the ``Content-Type`` it came with; the rest is never read."""
    head = b""
    async with client.stream("GET", file_url(job_id)) as response:
        if response.status_code != 200:
            await response.aread()
            raise AssertionError(f"the archive of a done job must download: {shown(response)}")
        content_type = response.headers.get("content-type", "")
        async for chunk in response.aiter_bytes():
            head += chunk
            if len(head) >= size:
                break
    return head[:size], content_type


def run_async(coroutine: Coroutine[Any, Any, Any]) -> Any:
    """Run ``coroutine`` to its end on a loop of its own, in a thread of its own: the module's fixtures are synchronous,
    and never touch the loop pytest-asyncio gives a test."""
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="backup-secure-fixture") as pool:
        return pool.submit(asyncio.run, coroutine).result()


async def _open_account(registered: list[int], *, admin: bool) -> Account:
    """Register a user (its id joins ``registered``), promote it when ``admin``, log it in, and check its role."""
    username = f"backup_secure_{'admin' if admin else 'user'}_{uuid.uuid4().hex[:12]}"
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.post(f"{API_BASE}/auth/register", json={"username": username, "email": f"{username}@example.com", "password": ACCOUNT_PASSWORD})
        assert response.status_code == 201, f"registering {username}: {shown(response)}"
        user_id = response.json()["user"]["id"]
        registered.append(user_id)
        if admin:
            async with AsyncSession(get_async_engine()) as session:
                promoted, error = await user_service.set_user_admin(session, username, is_admin=True)
            # The first account of an empty database is an administrator already.
            assert promoted or "already an admin" in (error or ""), f"promoting {username} to administrator: {error}"
        response = await client.post(f"{API_BASE}/auth/login", json={"username": username, "password": ACCOUNT_PASSWORD})
        assert response.status_code == 200, f"logging in {username}: {shown(response)}"
        session_cookie = response.cookies.get(SESSION_COOKIE_NAME)
        assert session_cookie, f"logging in {username} set no {SESSION_COOKIE_NAME} cookie"
    account = Account(username=username, user_id=user_id, session=session_cookie)
    async with account.client() as client:
        me = await client.get(f"{API_BASE}/auth/me")
    assert me.status_code == 200 and me.json()["user"]["is_superuser"] is admin, f"premise: {username} must {'be' if admin else 'not be'} an administrator: {shown(me)}"
    return account


async def _open_accounts(registered: list[int]) -> Accounts:
    return Accounts(admin=await _open_account(registered, admin=True), user=await _open_account(registered, admin=False))


async def _delete_users(user_ids: list[int]) -> list[str]:
    """Delete these users of the lane, each in a session of its own: what failed."""
    problems: list[str] = []
    for user_id in user_ids:
        async with AsyncSession(get_async_engine()) as session:
            try:
                await user_service.delete_user(session, user_id)
            except Exception as exc:  # every account gets its attempt; the failures are reported together
                problems.append(f"user {user_id}: {exc!r}")
    return problems


@pytest.fixture(scope="module")
def test_server():
    """The lane's server, for the tests of this module that need it (attached to when the runner shares one)."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


@pytest.fixture(scope="module")
def accounts(test_server) -> Iterator[Accounts]:
    """This module's administrator and ordinary user, deleted at its end, after a red too. Also the premise of every look
    at the lane's data directory: the database this process reads is the server's, since it holds the administrator the
    server has just registered."""
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


@pytest.fixture
def created_jobs(accounts) -> Iterator[list[str]]:
    """The jobs this test starts: each is waited for and deleted through the API at its teardown, after a red too."""
    created: list[str] = []
    yield created
    problems = run_async(remove_jobs(accounts.admin, created))
    assert not problems, "could not delete the backup jobs of this test:\n" + "\n".join(problems)


# =============================================================================
# The apps of the test: the panel's routes and the restore's, in this process
# =============================================================================


def backup_app(user: SimpleNamespace | None = ADMIN) -> FastAPI:
    """``backup_router`` under ``/api/v1``, as ``router.py`` mounts it, in an app of the test and nothing else.
    ``get_current_user`` answers ``user``, so the real ``require_admin`` decides without a session or a database; None
    leaves it alone, for the panel's routes, which take a token instead."""
    app = FastAPI()
    app.include_router(backup_router, prefix="/api/v1")
    if user is not None:
        app.dependency_overrides[get_current_user] = lambda: user
    return app


async def call(method: str, path: str, *, app: FastAPI | None = None, **request: Any) -> httpx.Response:
    """One request to an app of the test, an administrator's by default. An exception a route does not turn into an
    answer comes back as a client's plain 500 (``raise_app_exceptions=False``) and fails an assertion instead of erroring."""
    transport = httpx.ASGITransport(app=app or backup_app(), raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url=IN_PROCESS) as client:
        return await client.request(method, path, **request)


@dataclass
class FakeThread:
    """A thread ``restore_jobs`` started, run at once in the request that starts it. What its target raises is kept, as a
    real thread's would be lost to the request; the end of every test asserts there was none."""

    target: Callable[..., object]
    args: tuple
    kwargs: dict
    name: str | None
    raised: BaseException | None = None

    def start(self) -> None:
        try:
            self.target(*self.args, **self.kwargs)
        except Exception as exc:
            self.raised = exc


class Threads:
    """``threading`` as ``restore_jobs`` sees it: the thread of a check runs at once, so a check has ended when ``POST
    /stage`` answers. Anything else is the real module's."""

    def __init__(self) -> None:
        self.started: list[FakeThread] = []

    def Thread(self, *, target, args=(), kwargs=None, name=None, daemon=None) -> FakeThread:  # the name restore_jobs calls
        thread = FakeThread(target, tuple(args), dict(kwargs or {}), name)
        self.started.append(thread)
        return thread

    def __getattr__(self, name: str) -> Any:
        return getattr(threading, name)


@dataclass(frozen=True)
class RestoreInstance:
    """The data directory the restore's routes use in a test, and the threads its checks ran in."""

    root: Path
    threads: Threads


def drop_every_check(root: Path) -> list[str]:
    """Remove every check left under ``root``, with its copy, as ``DELETE /stage`` does: what could not be removed."""
    problems: list[str] = []
    states = sorted(checks_dir(root).glob("*.json")) if checks_dir(root).is_dir() else []
    for state in states:
        try:
            restore_jobs.remove_check(state.stem, data_dir=root)
        except restore_jobs.CheckNotFoundError:
            continue
        except Exception as exc:  # every check gets its attempt; the failures are reported together
            problems.append(f"check {state.stem}: {exc!r}")
    return problems


@pytest.fixture
def restore_instance(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[RestoreInstance]:
    """The restore's routes on a data directory of the test. The process is configured with another one that must stay
    absent, this instance's key is ``THIS_INSTANCE_KEY`` (so no key file is ever generated), a self-hosted profile without
    an upload limit, the checks run in fake threads.

    At its end: the checks left are dropped, the configured data directory was never created, nothing was written
    outside ``.restore``, and no check's thread raised."""
    configured = cases.configure(monkeypatch, tmp_path / "configured-data-dir")
    monkeypatch.setenv(INSTANCE_KEY_VARIABLE, THIS_INSTANCE_KEY)
    monkeypatch.delenv(INSTANCE_KEY_FILE_VARIABLE, raising=False)
    monkeypatch.setenv(PROFILE_VARIABLE, "selfhosted")
    monkeypatch.delenv(LIMIT_VARIABLE, raising=False)
    root = tmp_path / "instance"
    root.mkdir()
    monkeypatch.setattr(restore, "get_data_dir", lambda: root)
    monkeypatch.setattr(restore_jobs, "get_data_dir", lambda: root)
    threads = Threads()
    monkeypatch.setattr(restore_jobs, "threading", threads)
    yield RestoreInstance(root, threads)
    problems = drop_every_check(root)
    get_git_version.cache_clear()
    assert not configured.exists(), f"something was written in the configured data directory instead of the one given: {cases.listing(configured)}"
    outside = [name for name in cases.listing(root) if Path(name).parts[0] != RESTORE_FOLDER]
    assert outside == [], f"the restore's routes write nothing outside .restore: {outside}"
    raised = [(thread.name, repr(thread.raised)) for thread in threads.started if thread.raised is not None]
    assert raised == [], f"a check's thread raised: {raised}"
    assert problems == [], "could not drop the checks of this test:\n" + "\n".join(problems)


async def upload(content: bytes) -> httpx.Response:
    """``PUT /upload``, ``content`` the raw body."""
    return await call("PUT", UPLOAD, content=content, headers={"Content-Type": "application/octet-stream"})


async def uploaded(content: bytes) -> dict:
    """``content`` uploaded: the answer, its id first of all."""
    response = await upload(content)
    assert response.status_code == 201, f"precondition: the archive is received: {shown(response)}"
    return response.json()


async def stage(body: dict) -> httpx.Response:
    """``POST /stage`` with ``body``."""
    return await call("POST", STAGE, json=body)


async def poll(stage_id: str) -> httpx.Response:
    return await call("GET", f"{STAGE}/{stage_id}")


async def drop(stage_id: str) -> httpx.Response:
    return await call("DELETE", f"{STAGE}/{stage_id}")


async def checked(body: dict, answers: list[httpx.Response]) -> dict:
    """The check ``body`` asks for: started (202), and ended since it runs at once; its final state. Both answers join
    ``answers``."""
    started = await stage(body)
    answers.append(started)
    assert started.status_code == 202, f"the check starts: {shown(started)}"
    ended = await poll(started.json()["stage_id"])
    answers.append(ended)
    assert ended.status_code == 200 and ended.json()["status"] != "running", f"the check has ended: {shown(ended)}"
    return ended.json()


@dataclass(frozen=True)
class PanelInstance:
    """A data directory of the test, the process's own for the test, and the hosting panel's token."""

    data: Path
    token: str

    @property
    def bearer(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}


@pytest.fixture
def panel_instance(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, databases) -> Iterator[PanelInstance]:
    """A real data directory under ``tmp_path`` (a database at the head, accounts, files), configured as this process's,
    without an instance key, and the panel's routes on with a token of the test. Its backups run for real, in a thread
    of this process, under its own run lock."""
    data = cases.make_data_dir(tmp_path / "data", databases.head)
    cases.configure(monkeypatch, data)
    monkeypatch.delenv(INSTANCE_KEY_VARIABLE, raising=False)
    monkeypatch.delenv(INSTANCE_KEY_FILE_VARIABLE, raising=False)
    token = secrets.token_hex(32)
    monkeypatch.setenv(TOKEN_VARIABLE, token)
    monkeypatch.delenv(TOKEN_FILE_VARIABLE, raising=False)
    yield PanelInstance(data, token)
    get_git_version.cache_clear()


# -----------------------------------------------------------------------------
# A backup holding the secrets of the instance that made it (SECURE-012, SECURE-013)
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class StoredSecret:
    """A secret of the plugin settings, as a database stores it (X's crypto)."""

    scope: str
    family: str
    plugin_code: str
    field_key: str
    user_id: int | None
    blob: bytes
    key_id: str

    def opened_with(self, subkey: bytes) -> str | None:
        """Its plaintext, as ``subkey`` reads it; None when it cannot."""
        try:
            return decrypt_secret(subkey, secret_aad(self.family, self.plugin_code, self.field_key, self.scope, self.user_id), bytes(self.blob))
        except UnreadableSecretError:
            return None


def subkey_of(instance_key: str) -> bytes:
    """The subkey of the plugin settings on an instance whose key is ``instance_key``."""
    return derive_key_from(instance_key, SUBKEY_PURPOSE, SUBKEY_LENGTH)


def secrets_in(database: Path) -> list[StoredSecret]:
    """Every secret ``database`` stores, system and user."""
    with closing(cases.read_only(database)) as conn:
        system = conn.execute("SELECT family, plugin_code, field_key, secret_ciphertext, key_id FROM plugin_system_settings WHERE secret_ciphertext IS NOT NULL").fetchall()
        user = conn.execute("SELECT user_id, family, plugin_code, field_key, secret_ciphertext, key_id FROM plugin_user_settings WHERE secret_ciphertext IS NOT NULL").fetchall()
    found = [StoredSecret("system", family, plugin, field_key, None, blob, key_id) for family, plugin, field_key, blob, key_id in system]
    return found + [StoredSecret("user", family, plugin, field_key, user_id, blob, key_id) for user_id, family, plugin, field_key, blob, key_id in user]


def seen_with(stored: list[StoredSecret], subkey: bytes) -> list[tuple[str, str, bool, str | None]]:
    """Each secret as ``subkey`` sees it: its scope, its field, whether its key id is ``subkey``'s, its plaintext."""
    return sorted((secret.scope, secret.field_key, secret.key_id == key_id_of(subkey), secret.opened_with(subkey)) for secret in stored)


def add_secrets_of_another_instance(database: Path) -> None:
    """Store ``SECRET_ROWS`` in ``database`` as the instance whose key is ``OTHER_INSTANCE_KEY`` stores its secrets."""
    subkey = subkey_of(OTHER_INSTANCE_KEY)
    with closing(sqlite3.connect(database)) as conn, conn:
        for scope, family, plugin_code, field_key, owner, plaintext in SECRET_ROWS:
            user_id = None
            if owner is not None:
                found = conn.execute("SELECT id FROM users WHERE username = ?", (owner,)).fetchone()
                assert found is not None, f"precondition: the data directory has the account {owner}"
                user_id = found[0]
            blob = encrypt_secret(subkey, secret_aad(family, plugin_code, field_key, scope, user_id), plaintext)
            if scope == "system":
                conn.execute("INSERT INTO plugin_system_settings (family, plugin_code, field_key, secret_ciphertext, key_id, updated_at) VALUES (?, ?, ?, ?, ?, ?)", (family, plugin_code, field_key, blob, key_id_of(subkey), cases.CREATED))
            else:
                conn.execute("INSERT INTO plugin_user_settings (user_id, family, plugin_code, field_key, secret_ciphertext, key_id, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)", (user_id, family, plugin_code, field_key, blob, key_id_of(subkey), cases.CREATED))


@dataclass(frozen=True)
class SecretArchives:
    """A backup whose database holds ``SECRET_ROWS`` under the key of the instance that made it: as a clear zip, and as
    the zip a secure backup of that instance holds, its key in ``secrets/instance.key`` announced by the manifest."""

    clear: Path
    keyed: Path


@pytest.fixture(scope="module")
def secret_archives(databases, tmp_path_factory) -> SecretArchives:
    """Built once for the module, under its own configuration, as ``test_backup_staging.archive_of`` builds an archive.
    The keyed zip is the clear one, its key entry added before the manifest, which says ``instance_key: {included: true,
    sha256}`` (§4, B4b) and does not list the entry in its files."""
    root = tmp_path_factory.mktemp("secret-archives")
    with pytest.MonkeyPatch.context() as patch:
        cases.configure(patch, root / "configured-data-dir")
        data = cases.make_data_dir(root / "data", databases.head)
        add_secrets_of_another_instance(data / DATABASE_ENTRY)
        assert seen_with(secrets_in(data / DATABASE_ENTRY), subkey_of(OTHER_INSTANCE_KEY)) == SECRETS_READABLE, "precondition: the backup's secrets open with its own instance's key"
        built = cases.build_into(data, root / "work", "librefolio-backup-secrets.zip")
        get_git_version.cache_clear()
    assert built.warnings == (), f"precondition: a clean archive: {built.warnings}"
    key = cases.Entry(KEY_ENTRY, OTHER_INSTANCE_KEY.encode("utf-8"))
    manifest = cases.manifest_document(built, instance_key={"included": True, "sha256": cases.sha256(key.data)})
    keyed = cases.pack(root / "librefolio-backup-secrets-keyed.zip", [*cases.entries_of(built), key], manifest)
    return SecretArchives(clear=built.path, keyed=keyed)


# =============================================================================
# SECURE-001: the options of a secure backup — on the lane's server
# =============================================================================


@pytest.mark.asyncio
class TestTheOptions:
    @pytest.mark.parametrize(("caller", "status"), [pytest.param("admin", 200, id="administrator"), pytest.param("user", 403, id="ordinary-user"), pytest.param("anonymous", 401, id="without-a-session")])
    async def test_the_options_give_the_archive_password_rules_to_administrators_only(self, accounts, caller, status):
        """SECURE-001: ``GET /backup/instance/options`` answers an administrator the archive's rules, A's five in their
        order, ``min_length`` 12 and the others without a value; an ordinary user 403; a caller without a session 401.
        Red today: no such route (404)."""
        print_section(f"SECURE-001: GET /backup/instance/options as {caller} → {status}")
        clients = {"admin": accounts.admin.client, "user": accounts.user.client, "anonymous": lambda: httpx.AsyncClient(timeout=TIMEOUT)}

        async with clients[caller]() as client:
            response = await client.get(OPTIONS_URL)

        assert response.status_code == status, f"the options of a secure backup are for administrators: {caller} → {status}: {shown(response)}"
        if status == 200:
            rules = response.json().get("password_rules", ABSENT)
            assert rules == ARCHIVE_RULES, f"the archive's rules: A's five in order, min_length 12 (P12), the others without a value:\n  expected {ARCHIVE_RULES}\n  got      {rules}"
        print_success(f"{caller}: {status}")


# =============================================================================
# SECURE-002..005: starting a backup, clear or secure — on the lane's server
# =============================================================================


@pytest.mark.asyncio
class TestTheStart:
    @pytest.mark.parametrize(("password", "failed"), WEAK_PASSWORDS)
    async def test_a_password_the_rules_refuse_is_400_and_starts_nothing(self, accounts, created_jobs, password, failed):
        """SECURE-002: 400 ``password_too_weak``, with the codes of the rules the password fails in the rules' order and a
        message, never the password; nothing started: a clear start right after it answers 202, not 409 ``backup_busy``,
        and the lane gained that one job only. Red today: the route reads no body and starts a clear backup (202)."""
        print_section(f"SECURE-002: a password failing {failed} → 400 password_too_weak, nothing started")
        await wait_until_the_lane_is_free()
        before = lane_jobs()

        async with accounts.admin.client() as admin:
            refused = await post_start(admin, created_jobs, json={"password": password})
            clear = await post_start(admin, created_jobs)

        assert code(refused) == (400, "password_too_weak"), f"a password the archive's rules refuse is 400 password_too_weak: {shown(refused)}"
        detail = refused.json()["detail"]
        assert detail.get("rules") == failed, f"the rules it fails, in the rules' order: expected {failed}, got {detail.get('rules', ABSENT)}"
        assert isinstance(detail.get("message"), str) and detail["message"], f"with a message: {detail}"
        assert not carries(refused, password), f"the refusal never carries the password: {shown(refused)}"
        assert clear.status_code == 202, f"the refusal started nothing: a clear start right after it must not find a backup running: {shown(clear)}"
        gained = lane_jobs() - before
        assert gained == {clear.json()["job_id"]}, f"the lane gained the clear start's job and no other: {sorted(gained)}"
        print_success(f"400 password_too_weak {failed}; then a clear start 202, the one new job")

    async def test_a_secure_backup_is_an_envelope_its_password_opens(self, accounts, created_jobs, tmp_path):
        """SECURE-003: 202, then done, ``encrypted``, ``.lfbk``, every phase a secure job has (``encrypting`` may be seen,
        never required). The download is the envelope of §1 as B4 writes it, served as ``application/octet-stream`` (it is
        not a zip), and the password opens it into a backup zip (database first, manifest last, the key entry exactly when
        the manifest says so, with its SHA-256). The job's folder holds its state and its envelope only; no answer,
        download header or state holds the password. Red today: the route reads no body; its job is a clear zip without
        ``encrypted``."""
        print_section("SECURE-003: a backup with a password → an .lfbk only its password opens")
        await wait_until_the_lane_is_free()
        answers: list[httpx.Response] = []

        async with accounts.admin.client() as admin:
            started = await post_start(admin, created_jobs, json={"password": PASSWORD})
            answers.append(started)
            assert started.status_code == 202, f"a secure backup starts as a clear one does: 202 and the job to poll: {shown(started)}"
            job = await finished(admin, started.json()["job_id"], answers)
            secure = (job["status"], job.get("encrypted", ABSENT), bool(SECURE_ARCHIVE.fullmatch(job.get("file_name") or "")))
            assert secure == ("done", True, True), f"a backup with a password ends done, encrypted, named librefolio-backup-YYYYMMDD-HHMMSS.lfbk: {job}"
            envelope = tmp_path / job["file_name"]
            headers = await download(admin, job["job_id"], envelope)

        phases = running_phases(answers)
        assert phases <= SECURE_PHASES, f"a secure job runs through the phases of a backup, and encrypting: {sorted(phases)}"
        assert headers.get("content-type", "").startswith(ENVELOPE_MEDIA_TYPE), f"an envelope is not a zip: it is served as {ENVELOPE_MEDIA_TYPE}, not {headers.get('content-type')!r}"
        disposition, filename = content_disposition(headers.get("content-disposition", ""))
        assert (disposition, filename) == ("attachment", job["file_name"]), f"the envelope comes as an attachment under the job's name: {headers.get('content-disposition')!r}"
        assert headers.get("cache-control") == "no-store", f"no cache keeps an archive: {headers.get('cache-control')!r}"
        assert envelope.stat().st_size == job["file_size"], f"file_size is the envelope's: {job['file_size']} != {envelope.stat().st_size}"
        with envelope.open("rb") as handle:
            assert handle.read(len(ENVELOPE_MAGIC)) == ENVELOPE_MAGIC, "the download is an envelope: it starts with LFBK"

        opened = tmp_path / "opened.zip"
        try:
            header = unseal(envelope, opened, PASSWORD)
            with zipfile.ZipFile(opened) as zf:
                names = zf.namelist()
                damaged = zf.testzip()
                manifest = json.loads(zf.read(MANIFEST_ENTRY))
                key_sha256 = cases.sha256(zf.read(KEY_ENTRY)) if KEY_ENTRY in names else None
        finally:
            opened.unlink(missing_ok=True)
        assert header.parameters == WRITTEN, f"what B4 writes (P12):\n  expected {WRITTEN}\n  got      {header.parameters}"
        assert damaged is None, f"entry {damaged} of the archive the envelope holds fails its CRC"
        archived = [name for name in names[:-1] if name != KEY_ENTRY]
        assert names[-1:] == [MANIFEST_ENTRY] and archived[:1] == [DATABASE_ENTRY], f"the envelope holds a backup zip, the database first and the manifest last: {names[:3]} … {names[-3:]}"
        assert (manifest.get("format"), manifest.get("origin")) == ("librefolio-backup", "ui"), f"the manifest of a backup started from the API: {manifest.get('format')!r}, {manifest.get('origin')!r}"
        assert [entry["path"] for entry in manifest["files"]] == archived, "the manifest lists every entry but itself and the instance key, in their order"
        instance_key = manifest.get("instance_key") or {}
        included = instance_key.get("included")
        assert isinstance(included, bool), f"the manifest says whether the archive carries the instance key: {instance_key}"
        assert (key_sha256 is not None) == included, f"the key entry is there exactly when the manifest says so: included {included}, entry {'present' if key_sha256 else 'absent'}"
        assert not included or key_sha256 == instance_key.get("sha256"), f"the manifest gives the key entry's SHA-256: {instance_key.get('sha256')!r} != {key_sha256!r}"

        folder = paths.job_dir(get_data_dir(), job["job_id"])
        assert files_in(folder) == sorted([STATE_FILE, job["file_name"]]), f"the job keeps its state and its envelope, the clear zip removed: {files_in(folder)}"
        assert PASSWORD not in (folder / STATE_FILE).read_text(encoding="utf-8"), "the job's state never holds the password"
        header_lines = "\n".join(f"{name}: {value}" for name, value in headers.multi_items())
        leaked = [shown(answer) for answer in answers if PASSWORD in answer.text] + (["the download's headers"] if PASSWORD in header_lines else [])
        assert leaked == [], f"no answer holds the password: {leaked}"
        print_success(f"{job['file_name']}: {job['file_size']} bytes, {header.parameters}, {len(names)} entries inside, instance key included: {included}")

    @pytest.mark.parametrize("sent", CLEAR_STARTS)
    async def test_without_a_password_the_backup_stays_a_clear_zip(self, accounts, created_jobs, sent):
        """SECURE-004: no body, ``{}`` or ``{"password": null}``: done, ``encrypted`` false, a ``.zip`` that starts as a
        zip and is still served as ``application/zip``, never in phase ``encrypting``. Red today: the job has no
        ``encrypted``."""
        print_section(f"SECURE-004: a start with {sent or 'no body'} → a clear zip")
        await wait_until_the_lane_is_free()
        answers: list[httpx.Response] = []

        async with accounts.admin.client() as admin:
            started = await post_start(admin, created_jobs, **sent)
            answers.append(started)
            assert started.status_code == 202, f"a clear backup starts: {shown(started)}"
            job = await finished(admin, started.json()["job_id"], answers)
            head, content_type = await first_bytes(admin, job["job_id"], len(ZIP_MAGIC)) if job["status"] == "done" else (b"", ABSENT)

        clear = (job["status"], job.get("encrypted", ABSENT), bool(CLEAR_ARCHIVE.fullmatch(job.get("file_name") or "")), head)
        assert clear == ("done", False, True, ZIP_MAGIC), f"without a password, a clear backup as before: done, not encrypted, a .zip: {job}, first bytes {head!r}"
        assert content_type.startswith(ZIP_MEDIA_TYPE), f"a clear backup is still served as {ZIP_MEDIA_TYPE}, not {content_type!r}"
        phases = running_phases(answers)
        assert phases <= CLEAR_PHASES, f"a clear backup never encrypts: {sorted(phases)}"
        print_success(f"{job['file_name']}, encrypted false")

    @pytest.mark.parametrize(("body", "field", "value"), MALFORMED)
    async def test_a_malformed_body_is_422_without_its_input_and_starts_nothing(self, accounts, created_jobs, body, field, value):
        """SECURE-005: 422 at the field, each error with type, loc and msg and never ``input``, the value nowhere in the
        answer, and no job. Red today: the route reads no body and starts a clear backup (202)."""
        print_section(f"SECURE-005: POST /backup/instance with a malformed {field} → 422 without its input")
        await wait_until_the_lane_is_free()
        before = lane_jobs()

        async with accounts.admin.client() as admin:
            response = await post_start(admin, created_jobs, json=body)

        problems = no_echo_problems(response, value, field)
        assert problems == [], "a malformed body is FastAPI's 422, without the input:\n- " + "\n- ".join(problems)
        assert lane_jobs() - before == set(), f"a malformed body starts nothing: {sorted(lane_jobs() - before)}"
        print_success(f"422 at {field}, no input, no job")


# =============================================================================
# SECURE-006: the hosting panel never encrypts — in an app of the test
# =============================================================================


async def panel_job_ended(panel: PanelInstance, app: FastAPI, job_id: str) -> httpx.Response:
    """Read the panel's job until it has ended and its run has let the lock of the test's data directory go: the last
    answer. The run is a real one, in a thread of this process; this is the only wait, and it has a deadline."""
    deadline = time.monotonic() + JOB_DEADLINE_S
    while True:
        response = await call("GET", f"{PANEL}/{job_id}", app=app, headers=panel.bearer)
        if response.status_code != 200 or (response.json()["status"] != "running" and not lock_held(paths.lock_path(panel.data))):
            return response
        if time.monotonic() >= deadline:
            raise AssertionError(f"the panel's backup job {job_id} has not ended within {JOB_DEADLINE_S:.0f}s: {shown(response)}")
        await asyncio.sleep(POLL_INTERVAL_S)


@pytest.mark.asyncio
async def test_the_panel_never_encrypts_whatever_body_it_receives(panel_instance):
    """SECURE-006: the panel's start with its token and ``{"password": …}``: 202, a real backup, done, ``encrypted``
    false, a ``.zip`` that is a zip without ``secrets/instance.key``; no key file made; deleted (204). Red today: the
    job has no ``encrypted``."""
    print_section("SECURE-006: the hosting panel's backup with a password in the body → still a clear zip")
    panel = panel_instance
    app = backup_app(user=None)

    started = await call("POST", PANEL, app=app, headers=panel.bearer, json={"password": PASSWORD})
    assert started.status_code == 202, f"the panel's start answers 202 and its job: {shown(started)}"
    job_id = started.json()["job_id"]
    ended = await panel_job_ended(panel, app, job_id)
    archive = await call("GET", f"{PANEL}/{job_id}/file", app=app, headers=panel.bearer)
    deleted = await call("DELETE", f"{PANEL}/{job_id}", app=app, headers=panel.bearer)

    assert ended.status_code == 200, f"the panel reads its job: {shown(ended)}"
    job = ended.json()
    clear = (job["status"], job.get("encrypted", ABSENT), bool(CLEAR_ARCHIVE.fullmatch(job.get("file_name") or "")))
    assert clear == ("done", False, True), f"the panel's backups are never encrypted, whatever the body says: done, not encrypted, a .zip: {job}"
    assert archive.status_code == 200 and archive.content[: len(ZIP_MAGIC)] == ZIP_MAGIC, f"the panel downloads a zip: {archive.status_code} {archive.content[:16]!r}"
    with zipfile.ZipFile(io.BytesIO(archive.content)) as zf:
        names = zf.namelist()
    assert KEY_ENTRY not in names and names[:1] == [DATABASE_ENTRY] and names[-1:] == [MANIFEST_ENTRY], f"a backup zip, never with the instance key: {names}"
    assert not (panel.data / "secrets").exists(), f"a panel's backup never makes an instance key: {cases.listing(panel.data / 'secrets')}"
    assert deleted.status_code == 204, f"the panel deletes its job: {shown(deleted)}"
    print_success(f"{job['file_name']}: a zip of {len(names)} entries, no key")


# =============================================================================
# SECURE-007..013: the restore of a secure backup — in an app of the test
# =============================================================================


@pytest.mark.asyncio
async def test_an_upload_says_whether_it_is_an_envelope_or_a_zip(restore_instance, head_archive):
    """SECURE-007: a file that starts with ``LFBK`` is ``kind`` ``envelope``, a zip is ``zip``, beside the id and the
    size. Red today: an upload has no ``kind``."""
    print_section("SECURE-007: PUT /backup/restore/upload → kind")
    plain = head_archive.path.read_bytes()

    as_zip = await uploaded(plain)
    as_envelope = await uploaded(seal(plain, PASSWORD))

    kinds = (as_zip.get("kind", ABSENT), as_envelope.get("kind", ABSENT))
    assert kinds == ("zip", "envelope"), f"the kind of an upload, read from its first bytes: (zip, envelope) expected, got {kinds}"
    assert set(as_zip) == set(as_envelope) == {"upload_id", "size", "kind"}, f"an upload answers its id, its size and its kind: {sorted(as_zip)}, {sorted(as_envelope)}"
    print_success(f"zip, envelope ({as_envelope['size']} bytes)")


@pytest.mark.asyncio
async def test_an_envelope_asks_for_its_password_keeps_its_upload_and_opens_with_the_right_one(restore_instance, head_archive):
    """SECURE-008: no password → 400 ``password_required``; a wrong one → 400 ``wrong_password``; each time the upload
    kept, no check written, the lock let go. The right one with the same upload id → 202, done; the report says
    ``encrypted`` and what the backup is (no instance key, no secret to read or re-encrypt); the decrypted zip is not left
    beside the copy, the upload is consumed, no answer holds a password. Red today: the request takes no password, and the
    envelope is checked as a zip (202, then not_a_backup)."""
    print_section("SECURE-008: POST /backup/restore/stage on an envelope: password_required, wrong_password, then done")
    root = restore_instance.root
    upload_id = (await uploaded(seal(head_archive.path.read_bytes(), PASSWORD)))["upload_id"]
    answers: list[httpx.Response] = []

    for body, expected in (({"upload_id": upload_id}, (400, "password_required")), ({"upload_id": upload_id, "password": WRONG_PASSWORD}, (400, "wrong_password"))):
        response = await stage(body)
        answers.append(response)
        assert code(response) == expected, f"{sorted(body)}: {expected}: {shown(response)}"
        assert files_in(uploads_dir(root)) == [upload_id], f"{expected[1]}: the upload is kept for the next try: {files_in(uploads_dir(root))}"
        assert files_in(checks_dir(root)) == [], f"{expected[1]}: no check is written: {files_in(checks_dir(root))}"
        assert cases.lock_is_free(root), f"{expected[1]}: the lock of the checks is let go"

    state = await checked({"upload_id": upload_id, "password": PASSWORD}, answers)
    report = state["report"]
    assert (state["status"], state["error_code"]) == ("done", None) and report is not None, f"the right password, the same upload: the check is done, with its report: {state}"
    expected_fields = {"encrypted": True, "instance_key_included": False, "secrets_unreadable": {"system": 0, "user": 0}, "secrets_rekeyed": 0}
    assert secure_fields(report) == expected_fields, f"the report of an envelope without a key or a secret:\n  expected {expected_fields}\n  got      {secure_fields(report)}"
    assert datetime.fromisoformat(report["backup_created_at"]) == head_archive.manifest.created_at, f"the backup checked is the one the envelope holds: {report['backup_created_at']}"
    assert (report["action"], report["restorable"]) == ("same", True), f"a backup at the head, restorable: {report['action']}, {report['restorable']}"
    stage_id = state["stage_id"]
    assert files_in(stage_dir(root, stage_id)) == [STAGE_DATA_FOLDER, STAGE_REPORT_FILE], f"the decrypted zip is removed once unpacked: the copy and its report only: {files_in(stage_dir(root, stage_id))}"
    assert files_in(uploads_dir(root)) == [], f"the upload is consumed by its check: {files_in(uploads_dir(root))}"
    leaked = [shown(answer) for answer in answers if PASSWORD in answer.text or WRONG_PASSWORD in answer.text]
    assert leaked == [], f"no answer holds a password: {leaked}"
    dropped = await drop(stage_id)
    assert dropped.status_code == 204, f"the check is dropped: {shown(dropped)}"
    print_success("password_required, wrong_password, then done: encrypted, the upload kept until then")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("make", "expected"),
    [
        pytest.param(lambda: ENVELOPE_MAGIC + bytes(16), (400, "envelope_damaged"), id="lfbk-and-16-bytes"),
        pytest.param(lambda: with_byte(seal(b"an archive behind a cost no server pays", PASSWORD), 6, 30), (409, "envelope_unsupported"), id="log2-n-30"),
    ],
)
async def test_an_envelope_that_cannot_be_opened_is_refused_and_its_upload_kept(restore_instance, make, expected):
    """SECURE-009: 20 bytes that start with ``LFBK``: 400 ``envelope_damaged``; a valid header whose ``log2(n)`` is 30:
    409 ``envelope_unsupported``, refused before any derivation. A second try with the same upload id answers the same,
    never 404 ``backup_upload_not_found``: the upload is kept, no check written. Red today: an upload has no ``kind``,
    and a check takes no password."""
    print_section(f"SECURE-009: an envelope that cannot be opened → {expected}")
    root = restore_instance.root
    answer = await uploaded(make())
    assert answer.get("kind", ABSENT) == "envelope", f"a file that starts with LFBK is an envelope: {answer}"
    upload_id = answer["upload_id"]

    first = await stage({"upload_id": upload_id, "password": PASSWORD})
    again = await stage({"upload_id": upload_id, "password": PASSWORD})

    assert (code(first), code(again)) == (expected, expected), f"{expected} both times, the upload kept:\n  {shown(first)}\n  {shown(again)}"
    assert files_in(uploads_dir(root)) == [upload_id] and files_in(checks_dir(root)) == [], f"the upload kept, no check written: {files_in(uploads_dir(root))}, {files_in(checks_dir(root))}"
    assert cases.lock_is_free(root), "the lock of the checks is let go"
    assert not (carries(first, PASSWORD) or carries(again, PASSWORD)), "no answer holds the password"
    print_success(f"{expected} twice, the upload kept")


@pytest.mark.asyncio
async def test_a_zip_checked_with_a_password_ignores_it(restore_instance, head_archive):
    """SECURE-010: a zip's check sent with a password: 202, done, ``encrypted`` false; the password is ignored and no
    answer holds it. Red today: ``RestoreStageRequest`` forbids ``password`` (422)."""
    print_section("SECURE-010: a zip checked with a password → the password ignored")
    upload_id = (await uploaded(head_archive.path.read_bytes()))["upload_id"]
    answers: list[httpx.Response] = []

    state = await checked({"upload_id": upload_id, "password": IGNORED_PASSWORD}, answers)

    report = state["report"]
    assert (state["status"], state["error_code"]) == ("done", None) and report is not None, f"a zip is checked as before, its password ignored: {state}"
    assert report.get("encrypted", ABSENT) is False, f"a zip is not encrypted: {secure_fields(report)}"
    assert not any(carries(answer, IGNORED_PASSWORD) for answer in answers), "no answer holds the password"
    dropped = await drop(state["stage_id"])
    assert dropped.status_code == 204, f"the check is dropped: {shown(dropped)}"
    print_success("done, encrypted false")


@pytest.mark.asyncio
@pytest.mark.parametrize(("fields", "field", "value"), MALFORMED_CHECKS)
async def test_a_malformed_check_is_422_without_its_input_and_starts_nothing(restore_instance, fields, field, value):
    """SECURE-011: 422 at the field, each error with type, loc and msg and never ``input``, the value nowhere in the
    answer; the upload kept, no check written. Red today: ``password`` is a field the request forbids, and its 422 echoes
    the input."""
    print_section(f"SECURE-011: POST /backup/restore/stage with a malformed {field} → 422 without its input")
    root = restore_instance.root
    upload_id = (await uploaded(b"an archive no check reads"))["upload_id"]

    response = await stage({"upload_id": upload_id, **fields})

    problems = no_echo_problems(response, value, field)
    assert problems == [], "a malformed check is FastAPI's 422, without the input:\n- " + "\n- ".join(problems)
    assert files_in(uploads_dir(root)) == [upload_id] and files_in(checks_dir(root)) == [], f"nothing started: {files_in(uploads_dir(root))}, {files_in(checks_dir(root))}"
    print_success(f"422 at {field}, no input")


@pytest.mark.asyncio
async def test_a_clear_zip_reports_the_secrets_this_instance_cannot_read(restore_instance, secret_archives):
    """SECURE-012: a clear zip whose database holds a system and a user secret of the instance that made it: done, the
    report ``encrypted`` false, no instance key, both secrets unreadable by scope, none re-encrypted; on the copy they are
    as they were, under that instance's key. Red today: the report has none of these fields."""
    print_section("SECURE-012: a clear zip with secrets of another instance → counted unreadable")
    root = restore_instance.root
    upload_id = (await uploaded(secret_archives.clear.read_bytes()))["upload_id"]

    state = await checked({"upload_id": upload_id}, [])

    report = state["report"]
    assert (state["status"], state["error_code"]) == ("done", None) and report is not None, f"the check is done, with its report: {state}"
    expected_fields = {"encrypted": False, "instance_key_included": False, "secrets_unreadable": {"system": 1, "user": 1}, "secrets_rekeyed": 0}
    assert secure_fields(report) == expected_fields, f"without the key of the instance that made it, its secrets are unreadable here:\n  expected {expected_fields}\n  got      {secure_fields(report)}"
    copy = stage_data_dir(root, state["stage_id"]) / DATABASE_ENTRY
    assert seen_with(secrets_in(copy), subkey_of(OTHER_INSTANCE_KEY)) == SECRETS_READABLE, f"the copy keeps the secrets as they were: {seen_with(secrets_in(copy), subkey_of(OTHER_INSTANCE_KEY))}"
    dropped = await drop(state["stage_id"])
    assert dropped.status_code == 204, f"the check is dropped: {shown(dropped)}"
    print_success("encrypted false, unreadable {system: 1, user: 1}, rekeyed 0")


@pytest.mark.asyncio
async def test_an_envelope_with_its_instance_key_has_its_secrets_rekeyed_to_this_instance(restore_instance, secret_archives):
    """SECURE-013: the same backup in an envelope that carries the key of the instance that made it, announced with its
    SHA-256 (B4b): done, the report ``encrypted``, ``instance_key_included``, both secrets re-encrypted, none unreadable.
    On the copy each secret opens with this instance's subkey and records its key id; the key was read, never unpacked
    (no ``secrets/`` in the copy), and no answer holds it. Red today: a check takes no password."""
    print_section("SECURE-013: an envelope carrying its instance key → its secrets re-encrypted to this instance's")
    root = restore_instance.root
    upload_id = (await uploaded(seal(secret_archives.keyed.read_bytes(), PASSWORD)))["upload_id"]
    answers: list[httpx.Response] = []

    state = await checked({"upload_id": upload_id, "password": PASSWORD}, answers)

    report = state["report"]
    assert (state["status"], state["error_code"]) == ("done", None) and report is not None, f"the check is done, with its report: {state}"
    expected_fields = {"encrypted": True, "instance_key_included": True, "secrets_unreadable": {"system": 0, "user": 0}, "secrets_rekeyed": 2}
    assert secure_fields(report) == expected_fields, f"with the key of the instance that made it, every secret is re-encrypted to this one's:\n  expected {expected_fields}\n  got      {secure_fields(report)}"
    copy_dir = stage_data_dir(root, state["stage_id"])
    this_instance = subkey_of(THIS_INSTANCE_KEY)
    assert seen_with(secrets_in(copy_dir / DATABASE_ENTRY), this_instance) == SECRETS_READABLE, f"on the copy, each secret opens with this instance's subkey, under its key id: {seen_with(secrets_in(copy_dir / DATABASE_ENTRY), this_instance)}"
    assert not (copy_dir / "secrets").exists(), f"the archive's key is read, never unpacked: {cases.listing(copy_dir / 'secrets')}"
    leaked = [shown(answer) for answer in answers if OTHER_INSTANCE_KEY in answer.text or PASSWORD in answer.text]
    assert leaked == [], f"no answer holds the key or the password: {leaked}"
    dropped = await drop(state["stage_id"])
    assert dropped.status_code == 204, f"the check is dropped: {shown(dropped)}"
    print_success("encrypted, instance key included, rekeyed 2, unreadable 0")


# =============================================================================
# SECURE-014: OpenAPI — pure
# =============================================================================


def values_allowed(schema: Any, schemas: dict) -> set:
    """Every value an OpenAPI schema enumerates (``enum``, ``const``), through ``$ref``, ``anyOf``, ``oneOf``, ``allOf``
    and ``items``."""
    found: set = set()
    seen: set[str] = set()
    pending = [schema]
    while pending:
        current = pending.pop()
        if not isinstance(current, dict):
            continue
        reference = current.get("$ref")
        if isinstance(reference, str) and reference not in seen:
            seen.add(reference)
            pending.append(schemas.get(reference.rsplit("/", 1)[-1]))
        found.update(current.get("enum", []))
        if "const" in current:
            found.add(current["const"])
        for key in ("anyOf", "oneOf", "allOf"):
            pending.extend(current.get(key, []))
        pending.append(current.get("items"))
    return found


def schema_properties(schemas: dict, name: str) -> dict:
    """The properties of the component schema ``name``; none when it does not exist."""
    return (schemas.get(name) or {}).get("properties", {})


def test_openapi_documents_the_secure_backup():
    """SECURE-014: the generated client gets B4's surface: ``GET /backup/instance/options`` answering
    ``InstanceBackupOptions``; ``POST /backup/instance`` with an optional ``InstanceBackupRequest`` (``password`` only,
    other fields refused); ``encrypted``, the phase ``encrypting`` and the warning ``instance_key_unusable`` of a job;
    the 200 of ``GET /backup/instance/jobs/{job_id}/file`` as ``application/zip`` and as ``application/octet-stream``;
    ``kind`` of an upload (``zip``, ``envelope``); ``password`` of a check; ``encrypted``, ``secrets_unreadable``
    (``RestoreSecretCounts``: system, user) and ``secrets_rekeyed`` of a report; the phase ``decrypting`` of a check, and
    the two codes it can now end with, ``password_required`` and ``envelope_damaged``, but neither ``wrong_password`` nor
    ``envelope_unsupported``: ``POST /backup/restore/stage`` answers those two itself, before any check exists, and
    documents them in the description of its 400 and of its 409. Red today: none of the new surface is there."""
    print_section("SECURE-014: OpenAPI of the secure backup")
    document = backup_app().openapi()
    schemas, operations = document["components"]["schemas"], document["paths"]
    options = (operations.get("/api/v1/backup/instance/options") or {}).get("get") or {}
    body = operations["/api/v1/backup/instance"]["post"].get("requestBody") or {}
    request = schemas.get("InstanceBackupRequest") or {}
    job = schema_properties(schemas, "InstanceBackupJob")
    report = schema_properties(schemas, "RestoreStageReport")
    check = schema_properties(schemas, "RestoreStage")
    end_codes = values_allowed(check.get("error_code"), schemas)
    stage_answers = operations["/api/v1/backup/restore/stage"]["post"].get("responses", {})
    downloaded = ((operations.get("/api/v1/backup/instance/jobs/{job_id}/file") or {}).get("get") or {}).get("responses", {}).get("200", {})

    documented = {
        "GET /backup/instance/options answers InstanceBackupOptions": "#/components/schemas/InstanceBackupOptions" in json.dumps(options.get("responses", {}).get("200", {})),
        "POST /backup/instance takes an optional InstanceBackupRequest": "#/components/schemas/InstanceBackupRequest" in json.dumps(body) and body.get("required") is not True,
        "InstanceBackupRequest has password only, other fields refused": set(request.get("properties", {})) == {"password"} and request.get("additionalProperties") is False,
        "InstanceBackupOptions has password_rules": "password_rules" in schema_properties(schemas, "InstanceBackupOptions"),
        "InstanceBackupJob has encrypted": "encrypted" in job,
        "InstanceBackupJob.phase allows encrypting": "encrypting" in values_allowed(job.get("phase"), schemas),
        "InstanceBackupJob.warnings allows instance_key_unusable": "instance_key_unusable" in values_allowed(job.get("warnings"), schemas),
        "GET /backup/instance/jobs/{job_id}/file answers its 200 as application/zip and as application/octet-stream": {ZIP_MEDIA_TYPE, ENVELOPE_MEDIA_TYPE} <= set(downloaded.get("content", {})),
        "RestoreUpload.kind is zip or envelope": values_allowed(schema_properties(schemas, "RestoreUpload").get("kind"), schemas) == {"zip", "envelope"},
        "RestoreStageRequest has password": "password" in schema_properties(schemas, "RestoreStageRequest"),
        "RestoreStageReport has encrypted, secrets_unreadable and secrets_rekeyed": {"encrypted", "secrets_unreadable", "secrets_rekeyed"} <= set(report),
        "RestoreStageReport.secrets_unreadable is a RestoreSecretCounts": "#/components/schemas/RestoreSecretCounts" in json.dumps(report.get("secrets_unreadable", {})),
        "RestoreSecretCounts has system and user": set(schema_properties(schemas, "RestoreSecretCounts")) == {"system", "user"},
        "RestoreStage.phase allows decrypting": "decrypting" in values_allowed(check.get("phase"), schemas),
        "RestoreStage.error_code allows password_required and envelope_damaged": CHECK_END_CODES <= end_codes,
        "RestoreStage.error_code allows neither wrong_password nor envelope_unsupported": not set(STAGE_ANSWER_CODES.values()) & end_codes,
        **{f"POST /backup/restore/stage documents {answer_code} in the description of its {status}": answer_code in str(stage_answers.get(status, {}).get("description", "")) for status, answer_code in STAGE_ANSWER_CODES.items()},
    }

    missing = [claim for claim, holds in documented.items() if not holds]
    assert missing == [], "the OpenAPI document lacks B4's surface:\n- " + "\n- ".join(missing)
    print_success(f"{len(documented)} claims documented: options, request, job, download, upload, check and report")

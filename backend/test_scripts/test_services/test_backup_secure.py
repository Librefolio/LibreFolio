"""
Instance backup, the «secure» backup (workstream B, lot B4; decisions 38, 39 and P12): a backup protected by a password
is one envelope, ``.lfbk`` (scrypt, then AES-256-GCM in chunks); it may carry the instance key; a restore decrypts it,
accepts the key entry only where it belongs and re-encrypts the plugin secrets of its copy to this instance's key.
Selector: ``services backup-secure``.

Under test, in ``backend/app/services/platform/instance_backup/``: ``jobs.py`` (``run_backup`` and ``start_backup`` with
``password=``), ``secure.py`` (new, contract §2), ``staging.py`` (``stage_archive(..., key=)``, the report's
``encrypted``, ``secrets_rekeyed`` and ``secrets_unreadable``), ``restore_jobs.py`` (``start_check(..., password=)``).
``envelope.py`` (new, contract §1) is the tool of these tests, never their subject: ``unlock``, ``decrypt_file``,
``encrypt_file``, ``is_envelope``, ``read_header`` and the constants, as §1 gives them.

(a) §4 Creation. With a password the zip is built as today, then encrypted into ``<archive name stem>.lfbk``
    (``librefolio-backup-YYYYMMDD-HHMMSS.lfbk``) and removed: the job ``done`` and ``encrypted``, its size and SHA-256
    the envelope's, its folder holding its state and the envelope (0600), nothing else; ``encrypting`` after the
    archive's phases, counting the zip's bytes; the envelope opens with the password into an archive that checks ok.
    The password is in no file of the data directory, not in ``state.json``, not in the log. ``start_backup`` the same,
    in the background. Without a password (none given, or ``None``): today's clear zip, ``encrypted`` false. An
    encryption that fails (``ENOSPC``: ``backup_no_space``; anything else: ``backup_failed``), or no room for the
    envelope once the zip is built (``backup_no_space``): the job failed, its folder holding its state only, the lock
    free.
(b) §4, decision 39, the instance key. With a password and the key LibreFolio generated: the entry
    ``secrets/instance.key``, the key's text as ``read_secret_file`` reads it, never listed in ``manifest.files``,
    announced as ``instance_key: {included: true, sha256: <its SHA-256>}``; the key in the clear in no file of the job's
    folder. A configured key (``LIBREFOLIO_INSTANCE_KEY``, ``LIBREFOLIO_INSTANCE_KEY_FILE``: a key file beside it is not
    the key), no key yet (none created), an unusable key file of 10 characters (the warning ``instance_key_unusable``,
    the backup done, the file untouched): no entry, ``included`` false. Without a password, never the key.
(c) §2 ``secure.py``: ``ARCHIVE_PASSWORD_MIN_LENGTH`` 12, ``ARCHIVE_PASSWORD_MAX_LENGTH`` 1024;
    ``archive_password_rules()`` is A's rules read at the call, in A's order, ``min_length`` raised to 12 and never
    lowered (A's 16 stays 16), gained first by a list without one; ``archive_password_problems`` the codes of those rules
    a password fails (eleven characters: enough for an account, not for an archive); ``exportable_instance_key()`` the
    generated key's text (a BOM and the trailing line break dropped), ``None`` for a configured key, for no key and for
    an unusable one; nothing ever created or changed.
(d) §5 The check of an envelope, ``stage_archive(..., key=unlock(envelope, password))``: ``decrypting`` first, over the
    envelope's bytes, into ``.restore/stage/<id>/archive.zip`` (0600), then B2's check of that zip, which is gone at the
    end: the report is the clear zip's, but ``encrypted``. Without a key: ``password_required``; a byte changed in its
    second chunk: ``envelope_damaged``, while decrypting. Nothing of the stage left, the lock free, no path said.
(e) §5, revised 23:25, the key entry, read into memory, never unpacked: accepted wherever the manifest announces it with
    its SHA-256, in a decrypted envelope as in the plain zip ``dev.py backup decrypt`` writes out of one (refusing it
    there would make LibreFolio refuse its own output: only writing is restricted, (a) and (b)). The zip
    ``decrypt_file`` writes, as it is, is checked with its key: restorable, ``instance_key_included``, not
    ``encrypted``, the secrets rekeyed with it as from the envelope ((f)). The control: an archive repacked with nothing
    changed is checked, as a zip and as an envelope. Present but not announced: ``unexpected_entry``; announced and
    missing: ``missing_entry``; another SHA-256, or other bytes: ``checksum_mismatch``; each in a zip as in an envelope.
(f) §5 The plugin secrets of the copy: two of the instance and three of two users, encrypted by the source under its
    generated key K1. From an envelope carrying K1, checked on the instance whose generated key is K2, or from the zip
    decrypted out of it: every row re-encrypted (``secrets_rekeyed`` 5, nothing unreadable), each decrypting with K2's
    subkey to its value under K2's key id; no ``secrets/`` in the copy, K1 in no file of the stage. From a clear backup
    (no key): nothing rekeyed, every row counted unreadable by scope and left as the backup holds it; on an instance
    whose key is K1 too, nothing unreadable. This instance's key unusable (configured too short, or ``settings_subkey``
    raising ``InstanceKeyError``), or an archive key ``derive_key_from`` refuses: the check done all the same, nothing
    rekeyed, every row unreadable and as it was.
(g) §5 ``restore_jobs.start_check(..., password=)``, an envelope uploaded. The lock first: while another check holds it,
    ``StagingBusyError`` before any question of password. No password (none given, or ``None``):
    ``PasswordRequiredError``; a wrong one: ``EnvelopeError`` ``wrong_password``; a header too short:
    ``envelope_damaged``; another version, or a scrypt cost out of bounds: ``envelope_unsupported``. Each time the
    upload kept as sent, no check state, no stage, no thread, the lock free, no password in the error. The right password
    then starts the check of that same upload (its thread is given the key, never the password), which ends done and
    removes the upload, as today; no file of ``.restore`` holds the password. A chunk damaged: the check ends ``failed``,
    ``envelope_damaged``, nothing of the stage left. A clear zip given a password: the password ignored.
(h) Lot B4b (review R13-SEC4, B-26): a key the archive could not give back is not exported. A restore reads the key
    entry up to ``INSTANCE_KEY_MAX_BYTES`` (4096) bytes of UTF-8 and refuses a larger one, so a generated key over the
    bound — 4097 ASCII characters, or 2049 characters of which 2048 take two bytes — that the instance key module reads
    and uses stays out of a secure backup: no key entry, ``included`` false, the warning ``instance_key_unusable``, the
    backup done and its check restorable; ``exportable_instance_key()`` is ``None`` and ``generated_key_unusable()``
    true for it. Exactly 4096 bytes, in either form, travels, and a check reads it back: the copy's secrets are
    re-encrypted with it.
(i) Lot B-18 §1, the old instance key given to a check (``stage_archive(..., instance_key=)``, which ``dev.py backup
    restore --instance-key-file`` passes; placed after (f)): a clear archive whose secrets K1 encrypted, checked on this
    instance (K2). Given K1: every secret re-encrypted (5, none unreadable), K1 in no file of the stage nor in the log,
    restorable. Given another key of 32 characters: nothing rekeyed, every secret unreadable and as the backup holds it,
    no error. A key shorter than 32 characters (31, or empty): ``instance_key_invalid`` in the contract's words, checked
    before the lock and any folder (no ``.restore`` where there was none, the one an earlier check left byte for byte, no
    progress), neither the key nor what ``derive_key_from`` says of its length in the message or the log. A secure
    archive carrying K1, given another key: its own key wins. Guards: ``instance_key=None`` is today's check; a wrong key
    on an archive of this very instance (its secrets under K2 already) changes nothing.

How. The database of every source is ``test_backup_staging.py``'s, made once by ``alembic upgrade`` at the head (its
module fixture, imported), copied into a data directory of the test with that module's accounts and files. The live
instance a check runs in is that module's too (``instance``, imported: its database open in WAL mode, its own files and
its generated key, K2; every path of it but ``.restore`` unchanged at the end of each test). Each step runs with the
data directory it works on configured as this process's (``configure``), as on a server: a backup reads the source's
key, a check the instance's. ``LIBREFOLIO_INSTANCE_KEY`` and ``_FILE`` are removed before every test; the tests that
need a configured key set it. Archives are the product's (``jobs.run_backup``, ``envelope.decrypt_file``); the crafted
ones are a secure archive decrypted, changed and zipped again with ``zipfile`` (``pack`` of the staging tests), then, for
an envelope, encrypted again at the lowest cost the format reads (``MIN_LOG2_N``). Secrets are rows written with plain
SQL (``_insert_secret`` of the plugin settings crypto tests), encrypted with ``crypto.encrypt_secret``. An encryption
that fails is ``encrypt_file`` replaced, in ``envelope`` and in every module of the package that bound it, by a stand-in
that leaves a partial behind and raises; it must be reached (a barrier). A disk without room is ``shutil.disk_usage``
answering no free byte once a zip is built (the barrier: it was asked then). A check runs in the fake threads of the
API's restore tests (``Threads``, imported): at once, in the call that starts it, so nothing is waited for. Logs are
read with ``structlog.testing.capture_logs`` behind a barrier (an event of the job's id). No password and no key of this
module is a real secret.

Pure: every data directory, database and archive under ``tmp_path``. The production data directory of this process is a
folder of the test that must stay absent, but where a step configures its own (``configured_data_dir`` of the staging
tests, imported, autouse); ``LF_APP_VERSION`` is set, so no git process runs. No lane database, no server, no network,
no sleep. Modes and locks are POSIX-only.

Written RED, before B4: ``envelope.py`` and ``secure.py`` do not exist, and are looked up by the test that needs them
(``envelope_module``, ``secure_module``), never imported at the top: the file collects without them, and each test fails
on its own with a "[new] …" message, as the new parameters, fields and errors do, each asserted before it is used. (h)
was written red after B4, before B4b: its cases over the bound fail on the key B4 still exports; those at the bound
pin what B4b must keep. (i) was written red before B-18: each of its cases asks ``stage_archive`` for ``instance_key``
first (``new_parameter``), then for the behaviour; its two guards pass the key only once the parameter exists, green
before B-18 as after it.
"""

from __future__ import annotations

import errno
import importlib
import inspect
import json
import os
import random
import re
import shutil
import sqlite3
import sys
import uuid
import zipfile
from collections.abc import Callable
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest
from structlog.testing import capture_logs

from backend.app.config import read_secret_file
from backend.app.services.accounts import password_policy
from backend.app.services.accounts.password_policy import PasswordRule
from backend.app.services.platform.instance_backup import jobs, restore_jobs, staging
from backend.app.services.platform.instance_backup.archive import INSTANCE_KEY_MAX_BYTES, check_archive
from backend.app.services.platform.instance_backup.jobs import BackupJob, archive_name, get_job, job_archive, run_backup, start_backup
from backend.app.services.platform.instance_backup.paths import (
    DATABASE_ENTRY,
    MANIFEST_ENTRY,
    STAGE_DATA_FOLDER,
    STAGE_LOCK_FILE,
    STAGE_REPORT_FILE,
    STATE_FILE,
    checks_dir,
    ensure_private_dir,
    job_dir,
    jobs_dir,
    restore_dir,
    stage_dir,
    stages_dir,
    upload_path,
    uploads_dir,
)
from backend.app.services.platform.instance_backup.snapshot import file_digest
from backend.app.services.platform.instance_backup.staging import StagingBusyError, StagingReport, new_stage_id, read_report, stage_archive
from backend.app.services.platform.instance_key import INSTANCE_KEY_FILE, InstanceKeyError, derive_key_from, instance_key_status
from backend.app.services.plugin_settings import crypto
from backend.app.services.plugin_settings.crypto import SUBKEY_LENGTH, SUBKEY_PURPOSE, decrypt_secret, encrypt_secret, key_id_of, secret_aad, settings_subkey
from backend.test_scripts.test_api import test_backup_restore as api
from backend.test_scripts.test_services import test_backup_jobs as jobs_cases
from backend.test_scripts.test_services import test_backup_staging as cases
from backend.test_scripts.test_services import test_plugin_settings_crypto as crypto_cases
from backend.test_scripts.test_utils import print_section, print_success

# The module fixture of test_backup_staging.py (lot B2a), re-exported: a database made once by alembic at the head.
databases = cases.databases
# The live instance a check runs in (test_backup_staging.py): its database open in WAL mode, its own files and its
# generated key, K2; every path of it but .restore unchanged at the end of the test.
instance = cases.instance
# Autouse, both. The production data directory of this process is a folder of the test that must stay absent unless a
# step configures its own, and LF_APP_VERSION is set (test_backup_staging.py); a backup thread a test starts ends within
# it (test_backup_jobs.py).
configured_data_dir = cases.configured_data_dir
no_backup_thread_outlives_its_test = jobs_cases.no_backup_thread_outlives_its_test

pytestmark = pytest.mark.skipif(os.name == "nt", reason="modes and the locks of the backups and of the checks are POSIX only")


@pytest.fixture(autouse=True)
def no_inherited_instance_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """The instance key a developer's shell may carry (``LIBREFOLIO_INSTANCE_KEY``, ``LIBREFOLIO_INSTANCE_KEY_FILE``) is
    removed for every test: each step reads the key of the data directory it works on, and a key is configured only by
    the tests that say so."""
    for name in ("LIBREFOLIO_INSTANCE_KEY", "LIBREFOLIO_INSTANCE_KEY_FILE"):
        monkeypatch.delenv(name, raising=False)


PACKAGE = "backend.app.services.platform.instance_backup"
ENVELOPE = f"{PACKAGE}.envelope"
SECURE = f"{PACKAGE}.secure"

#: The password of this module's secure backups: one the archive rules accept (12 characters at least, every class).
PASSWORD = "Correct-Horse-Battery-9"
#: Another password as good, never the one an archive was made with.
WRONG_PASSWORD = "Wrong-Horse-Battery-0"
#: The key the source instance generated (K1); a key configured in the environment; a key file too short to be used (10
#: characters). Test keys, never a real one.
SOURCE_KEY = "LibreFolio-b4-source-instance-key-0123456789"
CONFIGURED_KEY = "LibreFolio-b4-configured-instance-key-9876543210"
UNUSABLE_KEY = "0123456789"
#: The entry of a secure archive that carries the instance key (contract §4).
KEY_ENTRY = "secrets/instance.key"
ENVELOPE_NAME = re.compile(r"librefolio-backup-\d{8}-\d{6}\.lfbk")
#: What lot B4 adds to the report of a check (contract §5).
B4_REPORT_FIELDS = ("encrypted", "secrets_rekeyed", "secrets_unreadable")
#: What belongs to one check, not to the archive it checked: never compared between two checks.
PER_CHECK_FIELDS = {"stage_id", "staged_at", "expires_at", "encrypted"}
#: The plugin secrets of a source: (scope, user name or None, family, plugin, field). Two of the instance, three of two
#: of the staging tests' accounts.
SECRET_ROWS = (
    ("system", None, "asset", "b4_secure_test", "api_key"),
    ("system", None, "fx", "b4_secure_test", "token"),
    ("user", "zoe_admin", "asset", "b4_secure_test", "api_key"),
    ("user", "bob_user", "asset", "b4_secure_test", "api_key"),
    ("user", "bob_user", "fx", "b4_secure_test", "token"),
)
SECRETS_BY_SCOPE = {"system": 2, "user": 3}
NO_UNREADABLE = {"system": 0, "user": 0}
#: The secret rows of a database, by scope: (family, plugin, field, user id, blob, key id).
SECRET_SQL = (
    ("system", "SELECT family, plugin_code, field_key, NULL, secret_ciphertext, key_id FROM plugin_system_settings WHERE secret_ciphertext IS NOT NULL"),
    ("user", "SELECT family, plugin_code, field_key, user_id, secret_ciphertext, key_id FROM plugin_user_settings WHERE secret_ciphertext IS NOT NULL"),
)
#: A file of random bytes, which no compression shrinks: with it, an archive spans two chunks of an envelope.
NOISE = "custom-uploads/noise.bin"
#: A's password rules today (decision 37), and those of an archive (P12).
A_RULES = (PasswordRule("min_length", 8), PasswordRule("uppercase"), PasswordRule("lowercase"), PasswordRule("digit"), PasswordRule("special"))
ARCHIVE_RULES = (PasswordRule("min_length", 12), *A_RULES[1:])
#: Lot B4b, B-26: the largest instance key entry a restore reads back (``archive.INSTANCE_KEY_MAX_BYTES``), spelled out
#: so that a change of the bound shows. Generated keys at the bound and one byte over it, in UTF-8: ASCII, and two-byte
#: characters (``é``), over the bound with fewer characters than bytes — the bound counts bytes. Test keys, not secrets.
KEY_MAX_BYTES = 4096
TWO_BYTES = "\N{LATIN SMALL LETTER E WITH ACUTE}"
KEY_AT_THE_BOUND = {"ascii": "k" * KEY_MAX_BYTES, "two-byte-characters": TWO_BYTES * (KEY_MAX_BYTES // 2)}
KEY_OVER_THE_BOUND = {"ascii": "k" * (KEY_MAX_BYTES + 1), "two-byte-characters": TWO_BYTES * (KEY_MAX_BYTES // 2) + "k"}


# =============================================================================
# The product, looked up when a test needs it
# =============================================================================


def _new_module(name: str) -> ModuleType:
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as exc:
        if exc.name != name:
            raise
        pytest.fail(f"[new] {name} does not exist yet: lot B4 brings it (contract §1, §2)")


def envelope_module() -> ModuleType:
    """``instance_backup.envelope`` (contract §1), imported by the test that needs it: its absence is that test's red,
    not a collection error of the whole file."""
    return _new_module(ENVELOPE)


def secure_module() -> ModuleType:
    """``instance_backup.secure`` (contract §2), imported the same way."""
    return _new_module(SECURE)


def new_parameter(function: Callable[..., Any], name: str, *, by: str = "lot B4 adds it (contract §4, §5)") -> None:
    """``function`` takes the keyword ``name``, which a lot adds (``by``: lot B4, unless another is named)."""
    assert name in inspect.signature(function).parameters, f"[new] {function.__qualname__}() has no parameter {name!r} yet: {by}"


def new_field(value: object, name: str) -> Any:
    """``value.<name>``, a field lot B4 adds."""
    assert hasattr(value, name), f"[new] {type(value).__name__} has no field {name!r} yet: lot B4 adds it (contract §4)"
    return getattr(value, name)


def b4_report(report: StagingReport) -> dict[str, Any]:
    """What lot B4 adds to the report of a check, as JSON: ``encrypted``, ``secrets_rekeyed``, ``secrets_unreadable``."""
    dumped = report.model_dump(mode="json")
    missing = [name for name in B4_REPORT_FIELDS if name not in dumped]
    assert not missing, f"[new] the report of a check has no {', '.join(missing)} yet: lot B4 adds them (contract §5)"
    return {name: dumped[name] for name in B4_REPORT_FIELDS}


def comparable(report: StagingReport) -> dict[str, Any]:
    """A report as JSON without what belongs to its check alone (its id and dates) nor ``encrypted``: what two checks of
    one archive's content share."""
    return report.model_dump(mode="json", exclude=PER_CHECK_FIELDS)


def password_required_error() -> type[Exception]:
    """``PasswordRequiredError`` (contract §5), wherever ``restore_jobs`` may raise it from: its own, or the one of
    ``staging``, ``envelope`` or ``secure``."""
    for module in (restore_jobs, staging, sys.modules.get(ENVELOPE), sys.modules.get(SECURE)):
        error = getattr(module, "PasswordRequiredError", None)
        if isinstance(error, type) and issubclass(error, Exception):
            return error
    pytest.fail("[new] PasswordRequiredError does not exist yet: lot B4 adds it (contract §5)")


# =============================================================================
# Data directories, keys, secrets
# =============================================================================


def write_key_file(data_dir: Path, text: str = "", *, raw: bytes | None = None) -> Path:
    """The key file LibreFolio generates, ``secrets/instance.key`` (0600, in a 0700 folder): ``text`` and a line break, as
    a generated key is written, or ``raw``."""
    path = data_dir / INSTANCE_KEY_FILE
    path.parent.mkdir(mode=0o700, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(raw if raw is not None else (text + "\n").encode("utf-8"))
    return path


def source_dir(root: Path, databases: cases.Databases, monkeypatch: pytest.MonkeyPatch, *, key: str | None = None, files: dict[str, bytes] | None = None) -> Path:
    """A source instance at ``root``: a database at the head with the staging tests' accounts, their files and ``files``,
    the key file ``key`` when given, as LibreFolio generated it; configured as this process's data directory, as on the
    server it is backed up from."""
    data = cases.make_data_dir(root, databases.head)
    cases.write_files(data, files or {})
    if key is not None:
        write_key_file(data, key)
    return cases.configure(monkeypatch, data)


def checked_on(monkeypatch: pytest.MonkeyPatch, live: cases.Instance) -> Path:
    """The live instance configured as this process's data directory, as on the server that checks an archive: a check
    reads its key (K2). Its root."""
    return cases.configure(monkeypatch, live.root)


def noise(env: ModuleType) -> dict[str, bytes]:
    """A file of one chunk and a half of random bytes (``NOISE``): with it, an archive spans two chunks of an envelope."""
    return {NOISE: random.Random(20261016).randbytes(env.CHUNK_SIZE + env.CHUNK_SIZE // 2)}


def subkey_of(key: str) -> bytes:
    """The subkey of the plugin secrets on an instance whose key is ``key``."""
    return derive_key_from(key, SUBKEY_PURPOSE, SUBKEY_LENGTH)


def shown_key(value: object) -> str:
    """A key as a message shows it: a long one by its size (characters, UTF-8 bytes), never 4 KiB of text; else as is."""
    if isinstance(value, str) and len(value) > 64:
        return f"<a key of {len(value)} characters, {len(value.encode('utf-8'))} bytes>"
    return repr(value)


@dataclass(frozen=True)
class SecretSource:
    """A source instance whose plugin secrets its generated key (K1, unless another ``key`` is given) encrypted: its data
    directory, the value of each secret by row (scope, family, plugin, field, user id), and that key."""

    data: Path
    values: dict[tuple, str]
    key: str = SOURCE_KEY


def secret_source(root: Path, databases: cases.Databases, monkeypatch: pytest.MonkeyPatch, *, key: str = SOURCE_KEY) -> SecretSource:
    """A source whose key LibreFolio generated (``key``, K1 by default), holding ``SECRET_ROWS`` encrypted under that
    key's subkey, each its own value, written with plain SQL as the app stores them."""
    data = source_dir(root, databases, monkeypatch, key=key)
    subkey = subkey_of(key)
    assert settings_subkey() == subkey, "precondition: the source's own subkey is its key's: its generated key file is its key"
    values: dict[tuple, str] = {}
    with closing(sqlite3.connect(data / DATABASE_ENTRY)) as conn, conn:
        users = dict(conn.execute("SELECT username, id FROM users").fetchall())
        for scope, username, family, plugin, field in SECRET_ROWS:
            user_id = users[username] if username else None
            value = f"b4-secret-{uuid.uuid4().hex}"
            values[(scope, family, plugin, field, user_id)] = value
            blob = encrypt_secret(subkey, secret_aad(family, plugin, field, scope, user_id), value)
            crypto_cases._insert_secret(conn, scope, family, plugin, field, user_id, blob, key_id_of(subkey))
    return SecretSource(data=data, values=values, key=key)


def stored_secrets(database: Path) -> dict[tuple, tuple[bytes, str]]:
    """The secrets a database holds, by row (scope, family, plugin, field, user id): each one's blob and key id."""
    return {(scope, family, plugin, field, user_id): (bytes(blob), key_id) for scope, sql in SECRET_SQL for family, plugin, field, user_id, blob, key_id in cases.rows_of(database, sql)}


def readable_with(rows: dict[tuple, tuple[bytes, str]], subkey: bytes) -> dict[tuple, str]:
    """The value of each secret, decrypted with ``subkey`` in its own row's context; ``UnreadableSecretError`` if one
    cannot be."""
    return {row: decrypt_secret(subkey, secret_aad(row[1], row[2], row[3], row[0], row[4]), blob) for row, (blob, _key_id) in rows.items()}


def copy_database(root: Path, report: StagingReport) -> Path:
    """The database of a check's copy."""
    return stage_dir(root, report.stage_id) / STAGE_DATA_FOLDER / DATABASE_ENTRY


def files_holding(root: Path, needle: bytes) -> list[str]:
    """The files below ``root`` whose bytes hold ``needle``; links never followed."""
    return sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file() and not path.is_symlink() and needle in path.read_bytes())


def own_subkey(root: Path, *, source_key: str = SOURCE_KEY) -> bytes:
    """The subkey of the live instance at ``root`` (configured): its generated key K2, read as the instance reads it;
    checked to be the one ``settings_subkey`` gives, and not the source's (K1 by default)."""
    own = subkey_of(read_secret_file(root / INSTANCE_KEY_FILE, "instance key file"))
    assert settings_subkey() == own != subkey_of(source_key), "precondition: this instance's own key is its generated K2, not the source's"
    return own


def assert_rekeyed_to(own: bytes, root: Path, report: StagingReport, source: SecretSource) -> None:
    """The copy of a check given the archive's key (the source's): every secret of ``source`` kept, re-encrypted under
    ``own``, with its key id and its value; the archive's key never unpacked, in no file of the stage."""
    rows = stored_secrets(copy_database(root, report))
    key_ids = sorted({key_id for _blob, key_id in rows.values()})
    assert (set(rows), key_ids) == (set(source.values), [key_id_of(own)]), f"every secret kept, under this instance's key id: {key_ids}"
    assert readable_with(rows, own) == source.values, "every secret decrypts with this instance's subkey to its value"
    stage = stage_dir(root, report.stage_id)
    assert sorted(os.listdir(stage)) == [STAGE_DATA_FOLDER, STAGE_REPORT_FILE], f"the copy and its report, nothing else: {sorted(os.listdir(stage))}"
    assert not (stage / STAGE_DATA_FOLDER / "secrets").exists(), "the archive's key is never unpacked"
    assert files_holding(stage, source.key.encode("utf-8")) == [], "the archive's key is in no file of the stage"


# -----------------------------------------------------------------------------
# The instance key of a source, as each case arranges it: the key file in its data directory, when there is one.
# -----------------------------------------------------------------------------


def generated_key(data: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path | None:
    """The key LibreFolio generated, K1."""
    return write_key_file(data, SOURCE_KEY)


def generated_key_with_bom_and_crlf(data: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path | None:
    """K1 behind a UTF-8 byte order mark and before a CRLF, as an editor may save the file."""
    return write_key_file(data, raw=b"\xef\xbb\xbf" + SOURCE_KEY.encode("ascii") + b"\r\n")


def configured_key(data: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path | None:
    """``LIBREFOLIO_INSTANCE_KEY``; a generated key file beside it, which is not the key."""
    monkeypatch.setenv("LIBREFOLIO_INSTANCE_KEY", CONFIGURED_KEY)
    return write_key_file(data, SOURCE_KEY)


def configured_key_file(data: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path | None:
    """``LIBREFOLIO_INSTANCE_KEY_FILE``, as Docker mounts a secret; a generated key file beside it, which is not the key."""
    secret = tmp_path / "run-secrets" / "librefolio_instance_key"
    secret.parent.mkdir()
    secret.write_text(CONFIGURED_KEY + "\n", encoding="utf-8")
    monkeypatch.setenv("LIBREFOLIO_INSTANCE_KEY_FILE", str(secret))
    return write_key_file(data, SOURCE_KEY)


def no_key_yet(data: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path | None:
    """No key at all: the first use would generate it."""
    return None


def unusable_key(data: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path | None:
    """A key file of 10 characters: never used, never replaced."""
    return write_key_file(data, UNUSABLE_KEY)


def generated_key_of(text: str) -> Callable[[Path, pytest.MonkeyPatch, Path], Path | None]:
    """The key LibreFolio generated, holding ``text`` (lot B4b: a key at, or over, the bound a restore reads)."""

    def arrange(data: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path | None:
        return write_key_file(data, text)

    return arrange


def bound_cases(keys: dict[str, str], expected: Callable[[str], object]) -> list[Any]:
    """One case per key of ``keys``: its arrangement, what is expected of it, an id saying its size in bytes and its form."""
    return [pytest.param(generated_key_of(key), expected(key), id=f"generated-{len(key.encode('utf-8'))}-bytes-{form}") for form, key in keys.items()]


# =============================================================================
# Backups, envelopes, crafted archives
# =============================================================================


def secure_backup(data: Path) -> tuple[BackupJob, Path]:
    """A backup of ``data`` with ``PASSWORD``, in the calling thread, done: its end state and its envelope."""
    new_parameter(run_backup, "password")
    job, folder = run_backup(origin="cli", data_dir=data, password=PASSWORD)
    assert (job.status, job.error_code) == ("done", None), f"precondition: the secure backup is done: {job}"
    return job, folder / job.file_name


def clear_backup(data: Path) -> Path:
    """A backup of ``data`` without a password, as today, done: its zip."""
    job, folder = run_backup(origin="cli", data_dir=data)
    assert (job.status, job.error_code) == ("done", None), f"precondition: the clear backup is done: {job}"
    return folder / job.file_name


def zip_contents(path: Path) -> tuple[dict[str, bytes], dict[str, Any]]:
    """Every entry of a zip but its manifest, by name and in their order; and the manifest, as JSON."""
    with zipfile.ZipFile(path) as zf:
        entries = {info.filename: zf.read(info) for info in zf.infolist() if info.filename != MANIFEST_ENTRY}
        manifest = json.loads(zf.read(MANIFEST_ENTRY))
    return entries, manifest


def listed(manifest: dict[str, Any]) -> list[str]:
    """The paths ``manifest.files`` lists."""
    return [entry["path"] for entry in manifest["files"]]


@dataclass(frozen=True)
class Opened:
    """A secure archive opened with its password: the zip it holds (a new file), every entry of it but the manifest by
    name and in their order, and the manifest as JSON."""

    zip: Path
    entries: dict[str, bytes]
    manifest: dict[str, Any]


def open_envelope(env: ModuleType, envelope: Path, work: Path) -> Opened:
    """``envelope`` unlocked with ``PASSWORD`` and decrypted into a new zip in ``work``."""
    work.mkdir(parents=True, exist_ok=True)
    target = work / f"{envelope.stem}-{uuid.uuid4().hex[:8]}.zip"
    size = env.decrypt_file(envelope, target, env.unlock(envelope, PASSWORD))
    assert size == target.stat().st_size, f"decrypt_file answers the size of what it wrote: {size}, {target.stat().st_size} bytes written"
    entries, manifest = zip_contents(target)
    return Opened(zip=target, entries=entries, manifest=manifest)


def carrying_the_key(opened: Opened) -> Opened:
    """``opened``, once seen to carry K1, announced: what the crafted archives start from."""
    announced = opened.manifest.get("instance_key") or {}
    assert opened.entries.get(KEY_ENTRY) == SOURCE_KEY.encode("utf-8") and announced.get("included") is True, f"precondition: the secure archive carries the source's key, announced: {sorted(opened.entries)[:4]}, {announced}"
    return opened


def secure_archive_with_its_key(env: ModuleType, tmp_path: Path, databases: cases.Databases, monkeypatch: pytest.MonkeyPatch) -> Opened:
    """A source whose key LibreFolio generated (K1), backed up with ``PASSWORD``, opened: the archive carries K1."""
    data = source_dir(tmp_path / "source", databases, monkeypatch, key=SOURCE_KEY)
    _job, path = secure_backup(data)
    return carrying_the_key(open_envelope(env, path, tmp_path / "opened"))


def packed(env: ModuleType, entries: dict[str, bytes], manifest: dict[str, Any], target: Path, *, encrypted: bool) -> Path:
    """``entries`` and ``manifest`` as an archive at ``target`` (a name without suffix): a plain zip, zipped as the staging
    tests craft archives (the manifest last); for an envelope, that zip encrypted with ``PASSWORD`` at the lowest cost
    the format reads."""
    target.parent.mkdir(parents=True, exist_ok=True)
    plain = cases.pack(target.with_suffix(".zip"), [cases.Entry(name, data) for name, data in entries.items()], json.dumps(manifest).encode("utf-8"))
    if not encrypted:
        return plain
    envelope = target.with_suffix(".lfbk")
    env.encrypt_file(plain, envelope, PASSWORD, log2_n=env.MIN_LOG2_N)
    return envelope


def key_for(env: ModuleType, archive: Path, encrypted: bool) -> dict[str, Any]:
    """What ``stage_archive`` is given besides the archive: the key of an envelope, unlocked with ``PASSWORD``; nothing for
    a zip."""
    return {"key": env.unlock(archive, PASSWORD)} if encrypted else {}


def small_envelope(env: ModuleType, work: Path) -> Path:
    """An envelope of a few bytes, sealed with ``PASSWORD`` at the lowest cost: for the cases refused before a byte of it
    is decrypted."""
    plain = work / "small.bin"
    plain.write_bytes(b"a few bytes, never decrypted by these cases\n")
    target = work / "small.lfbk"
    env.encrypt_file(plain, target, PASSWORD, log2_n=env.MIN_LOG2_N)
    return target


def damaged_copy(env: ModuleType, envelope: Path, target: Path) -> Path:
    """A copy of ``envelope`` with one byte inverted in the middle of its second chunk: its header and its first chunk
    intact, so the password still opens it."""
    raw = bytearray(envelope.read_bytes())
    chunk = env.read_header(envelope).chunk_size + env.TAG_SIZE
    second = env.HEADER_SIZE + chunk
    assert len(raw) > second + env.TAG_SIZE, f"precondition: the envelope has a second chunk: {len(raw)} bytes, its second chunk at {second}"
    raw[second + min(chunk, len(raw) - second) // 2] ^= 0xFF
    target.write_bytes(bytes(raw))
    return target


class StoppedEncryption:
    """``encrypt_file`` stopped half way: it records what it was asked (source, target, whether with the password), leaves
    a partial envelope beside its target as an interrupted write does, and raises ``error``."""

    def __init__(self, error: BaseException) -> None:
        self.error = error
        self.calls: list[tuple[Path, Path, bool]] = []

    def __call__(self, src: Path, dst: Path, password: str, **kwargs: Any) -> Any:
        source, target = Path(src), Path(dst)
        self.calls.append((source, target, password == PASSWORD))
        target.with_name(target.name + ".part").write_bytes(b"LFBK half an envelope")
        raise self.error


def replace_encryption(monkeypatch: pytest.MonkeyPatch, env: ModuleType, replacement: Callable[..., Any]) -> None:
    """``envelope.encrypt_file`` replaced wherever a backup can reach it: the module's own name, and the name in every
    module of the package that bound it."""
    original = env.encrypt_file
    for name, module in list(sys.modules.items()):
        if name.startswith(PACKAGE + ".") and getattr(module, "encrypt_file", None) is original:
            monkeypatch.setattr(module, "encrypt_file", replacement)


def no_room_once_a_zip_is_built(monkeypatch: pytest.MonkeyPatch, data: Path) -> list[Path]:
    """``shutil.disk_usage`` answering no free byte once a backup's zip is built in ``data`` (the build's own check, before
    it, sees the real disk); the paths it was asked about then."""
    real = shutil.disk_usage
    asked: list[Path] = []

    def disk_usage(path: str | os.PathLike[str]) -> Any:
        if not any(jobs_dir(data).rglob("*.zip")):
            return real(path)
        asked.append(Path(path))
        return SimpleNamespace(total=1 << 40, used=1 << 40, free=0)

    monkeypatch.setattr(shutil, "disk_usage", disk_usage)
    return asked


# -----------------------------------------------------------------------------
# The restore's checks
# -----------------------------------------------------------------------------


class StageWatch(cases.Progress):
    """A check's ``progress`` that also notes the files of its stage, with their modes, when the check of the zip begins."""

    def __init__(self, root: Path, stage_id: str) -> None:
        super().__init__()
        self.stage = stage_dir(root, stage_id)
        self.at_checking: dict[str, int] | None = None

    def __call__(self, phase: str, done: int, total: int) -> None:
        super().__call__(phase, done, total)
        if phase == "checking" and self.at_checking is None:
            self.at_checking = {path.name: cases.mode(path) for path in self.stage.iterdir() if path.is_file()}


def fake_threads(monkeypatch: pytest.MonkeyPatch) -> api.Threads:
    """``threading`` as ``restore_jobs`` sees it: a check runs at once, in the call that starts it (the API tests' fake)."""
    threads = api.Threads()
    monkeypatch.setattr(restore_jobs, "threading", threads)
    return threads


def uploaded(root: Path, archive: Path) -> str:
    """``archive`` where an upload is received, ``.restore/upload/<id>`` (0600): its id."""
    upload_id = new_stage_id()
    ensure_private_dir(uploads_dir(root), root)
    target = upload_path(root, upload_id)
    shutil.copyfile(archive, target)
    target.chmod(0o600)
    return upload_id


def assert_nothing_started(root: Path, upload_id: str, sent: str, threads: api.Threads, why: str, *, lock_free: bool = True) -> None:
    """A start refused: the upload kept as sent, no check state, no stage, no thread; the lock free (or still its
    holder's)."""
    upload = upload_path(root, upload_id)
    assert upload.is_file() and cases.sha256(upload.read_bytes()) == sent, f"{why}: the upload is kept as it was sent"
    left = (api.files_in(checks_dir(root)), cases.leftover_stages(root), threads.started)
    assert left == ([], [], []), f"{why}: no check state, no stage, no thread: {left}"
    assert cases.lock_is_free(root) is lock_free, f"{why}: the lock of the checks {'is let go' if lock_free else 'stays with its holder'}"


# =============================================================================
# (a) Creation: the backup of an instance with a password
# =============================================================================


def test_a_backup_with_a_password_is_one_envelope_and_nothing_clear_is_left(tmp_path, databases, monkeypatch):
    """(a) §4 ``run_backup(password=)``: the zip encrypted into ``<archive name stem>.lfbk``, then removed. Done,
    ``encrypted``, the envelope's size and SHA-256, 0600, alone beside the state; ``encrypting`` after the archive's
    phases, over the zip's bytes; the envelope opens into an archive that checks ok. The password in no file of the data
    directory, nor in ``state.json``, nor in the log."""
    print_section("A backup with a password")
    env = envelope_module()
    new_parameter(run_backup, "password")
    data = source_dir(tmp_path / "source", databases, monkeypatch)
    progress = cases.Progress()
    with capture_logs() as events:
        job, folder = run_backup(origin="cli", data_dir=data, progress=progress, password=PASSWORD)
    assert (job.status, job.error_code, job.origin) == ("done", None, "cli"), f"the backup is done: {job}"
    assert new_field(job, "encrypted") is True, f"the job says its archive is encrypted: {job}"
    expected_name = Path(archive_name(job.created_at)).stem + ".lfbk"
    assert ENVELOPE_NAME.fullmatch(job.file_name or "") and job.file_name == expected_name, f"the envelope takes the archive's name, .lfbk: {job.file_name}, expected {expected_name}"
    path = folder / job.file_name
    assert sorted(os.listdir(folder)) == sorted([STATE_FILE, job.file_name]), f"the job's folder holds its state and its envelope, no zip, no partial: {sorted(os.listdir(folder))}"
    assert env.is_envelope(path) and cases.mode(path) == 0o600, f"an envelope, readable by its owner only: {oct(cases.mode(path))}"
    assert (job.file_size, job.file_sha256) == file_digest(path), "the state gives the envelope's size and SHA-256"
    assert get_job(job.job_id, data_dir=data) == job, "the state on disk is the one returned"
    assert job_archive(job.job_id, data_dir=data) == (path, job.file_name), "the envelope is the job's archive"
    opened = open_envelope(env, path, tmp_path / "opened")
    check = check_archive(opened.zip)
    assert check.ok and check.manifest.origin == "cli", f"the envelope holds an archive that checks ok: {check}"
    zip_size = opened.zip.stat().st_size
    phases = progress.phases
    assert phases[0] == "preparing" and {"database", "files"} <= set(phases) and phases[-2:] == ["finalizing", "encrypting"], f"encrypting comes after the archive's phases, last: {phases}"
    encrypting = [(done, total) for phase, done, total in progress.events if phase == "encrypting"]
    assert encrypting[-1] == (zip_size, zip_size) and all(done <= total for done, total in encrypting), f"encrypting counts the zip's {zip_size} bytes: {encrypting[:2]} … {encrypting[-1:]}"
    assert PASSWORD not in (folder / STATE_FILE).read_text(encoding="utf-8"), "the password is not in state.json"
    assert any(event.get("job_id") == job.job_id for event in events), f"barrier: the backup's log reaches the capture: {[event.get('event') for event in events]}"
    assert PASSWORD not in repr(events), "the password is not in the log"
    assert files_holding(data, PASSWORD.encode("utf-8")) == [], "the password is in no file of the data directory"
    print_success(f"{job.file_name}: {job.file_size} bytes, the zip's {zip_size} encrypted")


def test_a_backup_started_in_the_background_with_a_password_ends_as_an_envelope(tmp_path, databases, monkeypatch):
    """(a) §4 ``start_backup(password=)``: the first state at once, then the run in its thread to an envelope, as in the
    foreground; the password not in its state."""
    env = envelope_module()
    new_parameter(start_backup, "password")
    data = source_dir(tmp_path / "source", databases, monkeypatch)
    first = start_backup(origin="ui", data_dir=data, password=PASSWORD)
    assert (first.status, first.file_name) == ("running", None), f"the first state of a run: {first}"
    job = jobs_cases.wait_until_finished(first.job_id, data)
    folder = job_dir(data, job.job_id)
    assert (job.status, job.error_code, new_field(job, "encrypted")) == ("done", None, True), f"the run ends done, encrypted: {job}"
    assert ENVELOPE_NAME.fullmatch(job.file_name or ""), f"its archive has an envelope's name: {job.file_name}"
    assert sorted(os.listdir(folder)) == sorted([STATE_FILE, job.file_name]) and env.is_envelope(folder / job.file_name), f"the state and the envelope, nothing else: {sorted(os.listdir(folder))}"
    assert PASSWORD not in (folder / STATE_FILE).read_text(encoding="utf-8"), "the password is not in state.json"
    check = check_archive(open_envelope(env, folder / job.file_name, tmp_path / "opened").zip)
    assert check.ok and check.manifest.origin == "ui", f"the envelope holds an archive that checks ok, made from the UI: {check}"
    print_success(f"{job.file_name}, in the background")


WITHOUT_PASSWORD = [
    pytest.param({}, id="no-password-given"),
    pytest.param({"password": None}, id="password-none"),
]


@pytest.mark.parametrize("given", WITHOUT_PASSWORD)
def test_without_a_password_the_backup_is_today_s_clear_zip_and_never_carries_the_key(tmp_path, databases, monkeypatch, given):
    """(a)(b) §4 Today's backup: a zip under today's name, ``encrypted`` false, alone beside the state, an archive that
    checks ok; and never the instance key, though LibreFolio generated it."""
    if given:
        new_parameter(run_backup, "password")
    data = source_dir(tmp_path / "source", databases, monkeypatch, key=SOURCE_KEY)
    job, folder = run_backup(origin="cli", data_dir=data, **given)
    assert (job.status, job.error_code) == ("done", None), f"the backup is done: {job}"
    assert new_field(job, "encrypted") is False, f"a backup without a password is not encrypted: {job}"
    assert job.file_name == archive_name(job.created_at), f"today's name, .zip: {job.file_name}"
    path = folder / job.file_name
    assert sorted(os.listdir(folder)) == sorted([STATE_FILE, job.file_name]), f"the state and the zip, nothing else: {sorted(os.listdir(folder))}"
    assert path.read_bytes()[:4] == b"PK\x03\x04" and check_archive(path).ok, "a zip that checks ok, not an envelope"
    entries, manifest = zip_contents(path)
    keys = [name for name in entries if name.startswith("secrets/")]
    assert keys == [] and manifest["instance_key"]["included"] is False, f"never the key without a password: {keys}, {manifest['instance_key']}"
    print_success(f"{job.file_name}: clear, no key")


ENCRYPTION_FAILURES = [
    pytest.param(errno.ENOSPC, "backup_no_space", id="disk-full"),
    pytest.param(None, "backup_failed", id="any-other-failure"),
]


@pytest.mark.parametrize(("error_number", "error_code"), ENCRYPTION_FAILURES)
def test_an_encryption_that_fails_ends_the_job_failed_with_only_its_state_left(tmp_path, databases, monkeypatch, error_number, error_code):
    """(a) §4 The zip built, its encryption stops (a full disk, or anything else) and leaves a partial behind: the job
    failed with its code, its folder holding its state only (no zip, no envelope, no partial), the lock free; the
    password neither in its state nor in the log."""
    env = envelope_module()
    new_parameter(run_backup, "password")
    data = source_dir(tmp_path / "source", databases, monkeypatch)
    stopped = StoppedEncryption(jobs_cases.os_error(error_number) if error_number else RuntimeError("the cipher stopped"))
    replace_encryption(monkeypatch, env, stopped)
    with capture_logs() as events:
        job, folder = run_backup(origin="cli", data_dir=data, password=PASSWORD)
    assert len(stopped.calls) == 1, f"barrier: the backup reached encrypt_file through a name this test replaced: {stopped.calls}, the job {job}"
    source, target, with_the_password = stopped.calls[0]
    expected_target = folder / (Path(archive_name(job.created_at)).stem + ".lfbk")
    assert (source.parent, source.suffix, target, with_the_password) == (folder, ".zip", expected_target, True), f"the job's zip is encrypted with the password into its .lfbk: {source} → {target}"
    assert (job.status, job.error_code, job.phase, job.file_name) == ("failed", error_code, None, None), f"the job failed, {error_code}: {job}"
    assert os.listdir(folder) == [STATE_FILE], f"the job's folder keeps its state only: {sorted(os.listdir(folder))}"
    assert not jobs._run_lock_held(data), "the lock is free once the run returned"
    assert PASSWORD not in (folder / STATE_FILE).read_text(encoding="utf-8"), "the password is not in state.json"
    assert any(event.get("job_id") == job.job_id for event in events), f"barrier: the backup's log reaches the capture: {[event.get('event') for event in events]}"
    assert PASSWORD not in repr(events), "the password is not in the log"
    print_success(f"{error_code}: the state alone")


def test_without_room_for_the_envelope_the_job_fails_backup_no_space_with_only_its_state_left(tmp_path, databases, monkeypatch):
    """(a) §4 The free space is checked before encrypting: the zip built, the disk has no room for its envelope. The job
    failed ``backup_no_space``, its folder holding its state only, the lock free."""
    new_parameter(run_backup, "password")
    data = source_dir(tmp_path / "source", databases, monkeypatch)
    asked = no_room_once_a_zip_is_built(monkeypatch, data)
    job, folder = run_backup(origin="cli", data_dir=data, password=PASSWORD)
    assert asked, f"barrier: the free space was asked (shutil.disk_usage) once the zip was built: the job {job}"
    assert (job.status, job.error_code, job.file_name) == ("failed", "backup_no_space", None), f"no room for the envelope: {job}"
    assert os.listdir(folder) == [STATE_FILE], f"the job's folder keeps its state only: {sorted(os.listdir(folder))}"
    assert not jobs._run_lock_held(data), "the lock is free once the run returned"
    print_success(f"backup_no_space, asked about {sorted({path.name for path in asked})}")


# =============================================================================
# (b) The instance key in a secure archive (decision 39)
# =============================================================================


def test_a_generated_instance_key_travels_in_a_secure_archive_announced_and_never_listed(tmp_path, databases, monkeypatch):
    """(b) §4, decision 39: the key LibreFolio generated, in the entry ``secrets/instance.key`` (its text, UTF-8, as
    ``read_secret_file`` reads it: without the file's line break), never one of ``manifest.files``, announced with its
    SHA-256. No warning; the key file untouched; the key in the clear in no file of the job's folder."""
    print_section("The instance key in a secure archive")
    env = envelope_module()
    data = source_dir(tmp_path / "source", databases, monkeypatch, key=SOURCE_KEY)
    key_file = data / INSTANCE_KEY_FILE
    before = key_file.read_bytes()
    status = instance_key_status()
    assert (status.source, status.problem) == ("generated", None), f"precondition: the source's key is the one LibreFolio generated, usable: {status}"
    text = read_secret_file(key_file, "instance key file")
    job, path = secure_backup(data)
    assert tuple(job.warnings) == (), f"a usable key: no warning: {job.warnings}"
    opened = open_envelope(env, path, tmp_path / "opened")
    assert opened.entries.get(KEY_ENTRY) == text.encode("utf-8"), f"the entry is the key's text: {opened.entries.get(KEY_ENTRY)!r}"
    announced = opened.manifest.get("instance_key") or {}
    assert (announced.get("included"), announced.get("sha256")) == (True, cases.sha256(text.encode("utf-8"))), f"the manifest announces the key with the entry's SHA-256: {announced}"
    assert KEY_ENTRY not in listed(opened.manifest), f"the key is never one of manifest.files: {listed(opened.manifest)}"
    assert key_file.read_bytes() == before, "the key file is read, never changed"
    assert files_holding(path.parent, text.encode("utf-8")) == [], "the key is in the clear in no file of the job's folder"
    print_success(f"{KEY_ENTRY}: announced, sha256 {str(announced.get('sha256'))[:12]}…")


NOT_EXPORTABLE = [
    pytest.param(configured_key, "configured", False, (), id="configured-key-a-key-file-beside-it"),
    pytest.param(configured_key_file, "configured", False, (), id="configured-key-file-a-key-file-beside-it"),
    pytest.param(no_key_yet, "not_created", False, (), id="no-key-yet"),
    pytest.param(unusable_key, "generated", True, ("instance_key_unusable",), id="unusable-generated-key-of-10-characters"),
]


@pytest.mark.parametrize(("arrange", "source", "problem", "warnings"), NOT_EXPORTABLE)
def test_a_key_that_is_not_exportable_stays_out_of_the_secure_archive(tmp_path, databases, monkeypatch, arrange, source, problem, warnings):
    """(b) §4, decision 39: only the key LibreFolio generated travels. A configured key (a key file beside it is not the
    key), no key yet, an unusable key file: no entry, ``included`` false; the backup done, warned ``instance_key_unusable``
    for the unusable key only. No key file created, none changed."""
    env = envelope_module()
    data = source_dir(tmp_path / "source", databases, monkeypatch)
    key_file = arrange(data, monkeypatch, tmp_path)
    before = key_file.read_bytes() if key_file else None
    status = instance_key_status()
    assert (status.source, status.problem is not None) == (source, problem), f"precondition: the instance key is {source}, {'unusable' if problem else 'usable or none'}: {status}"
    job, path = secure_backup(data)
    assert (new_field(job, "encrypted"), tuple(job.warnings)) == (True, warnings), f"a secure backup, done, warned of an unusable key only: {job}"
    opened = open_envelope(env, path, tmp_path / "opened")
    keys = [name for name in opened.entries if name.startswith("secrets/")]
    assert keys == [] and opened.manifest["instance_key"]["included"] is False, f"no key entry, none announced: {keys}, {opened.manifest['instance_key']}"
    if key_file is None:
        assert not (data / "secrets").exists(), "the backup creates no key file"
    else:
        assert key_file.read_bytes() == before, "the key file is never changed"
    print_success(f"{source}: no key entry, warnings {list(job.warnings)}")


# =============================================================================
# (c) secure.py: the archive's password rules, the key a secure archive may carry
# =============================================================================


def test_the_archive_password_rules_are_a_s_rules_with_at_least_12_characters(monkeypatch):
    """(c) §2, P12: ``ARCHIVE_PASSWORD_MIN_LENGTH`` 12, ``ARCHIVE_PASSWORD_MAX_LENGTH`` 1024. A's rules, read at the call
    and in A's order, ``min_length`` raised to 12 and never lowered; a list without one gains it first. Eleven
    characters are enough for an account, not for an archive."""
    print_section("The archive's password rules")
    secure = secure_module()
    assert (secure.ARCHIVE_PASSWORD_MIN_LENGTH, secure.ARCHIVE_PASSWORD_MAX_LENGTH) == (12, 1024), f"P12: {secure.ARCHIVE_PASSWORD_MIN_LENGTH}, {secure.ARCHIVE_PASSWORD_MAX_LENGTH}"
    assert password_policy.PASSWORD_RULES == A_RULES, f"precondition: A's rules, a minimum of 8: {password_policy.PASSWORD_RULES}"
    assert tuple(secure.archive_password_rules()) == ARCHIVE_RULES, f"A's rules, 12 characters at least: {secure.archive_password_rules()}"
    assert (password_policy.failed_rules("Short-Pas-1"), secure.archive_password_problems("Short-Pas-1")) == ([], ["min_length"]), "eleven characters: an account's password, not an archive's"
    longer = (PasswordRule("digit"), PasswordRule("min_length", 16), PasswordRule("lowercase"))
    monkeypatch.setattr(password_policy, "PASSWORD_RULES", longer)
    assert tuple(secure.archive_password_rules()) == longer, f"A's rules read at the call, in A's order, A's 16 never lowered: {secure.archive_password_rules()}"
    monkeypatch.setattr(password_policy, "PASSWORD_RULES", (PasswordRule("uppercase"), PasswordRule("digit")))
    expected = (PasswordRule("min_length", 12), PasswordRule("uppercase"), PasswordRule("digit"))
    assert tuple(secure.archive_password_rules()) == expected, f"a list without min_length gains it first: {secure.archive_password_rules()}"
    print_success("A's rules, at least 12 characters, read at each call")


ARCHIVE_PROBLEMS = [
    pytest.param(PASSWORD, [], id="every-rule-met"),
    pytest.param("Short-Pass-1", [], id="twelve-characters"),
    pytest.param("Short-Pas-1", ["min_length"], id="eleven-characters"),
    pytest.param("correct horse battery staple", ["uppercase", "digit", "special"], id="a-long-passphrase-of-lowercase-and-spaces"),
    pytest.param("", ["min_length", "uppercase", "lowercase", "digit", "special"], id="empty"),
]


@pytest.mark.parametrize(("password", "problems"), ARCHIVE_PROBLEMS)
def test_archive_password_problems_are_the_archive_rules_a_password_fails(password, problems):
    """(c) §2 ``archive_password_problems``: the codes of the archive's rules the password fails, in their order."""
    secure = secure_module()
    assert secure.archive_password_problems(password) == problems, f"{password!r}: {secure.archive_password_problems(password)}"
    print_success(f"{password!r}: {problems}")


EXPORTED = [
    pytest.param(generated_key, SOURCE_KEY, id="generated"),
    pytest.param(generated_key_with_bom_and_crlf, SOURCE_KEY, id="generated-behind-a-bom-before-a-crlf"),
    pytest.param(configured_key, None, id="configured-key-a-key-file-beside-it"),
    pytest.param(configured_key_file, None, id="configured-key-file-a-key-file-beside-it"),
    pytest.param(no_key_yet, None, id="no-key-yet"),
    pytest.param(unusable_key, None, id="unusable-generated-key"),
    # Lot B4b, B-26: at the bound a restore reads, the key travels; one byte over it, it does not.
    *bound_cases(KEY_AT_THE_BOUND, lambda key: key),
    *bound_cases(KEY_OVER_THE_BOUND, lambda key: None),
]


@pytest.mark.parametrize(("arrange", "exported"), EXPORTED)
def test_exportable_instance_key_is_the_generated_key_alone_and_creates_nothing(tmp_path, monkeypatch, arrange, exported):
    """(c) §2 ``exportable_instance_key``: the text of the key LibreFolio generated, read as ``read_secret_file`` reads it
    (a BOM and the trailing line break dropped); ``None`` for a configured key (a key file beside it or not), for no key
    and for an unusable one — and (h), lot B4b, for one over ``INSTANCE_KEY_MAX_BYTES`` bytes of UTF-8, which no restore
    could read back. Nothing created, nothing changed in the data directory."""
    secure = secure_module()
    data = tmp_path / "data"
    data.mkdir()
    cases.configure(monkeypatch, data)
    arrange(data, monkeypatch, tmp_path)
    before = cases.fingerprint(data)
    found = secure.exportable_instance_key()
    assert found == exported, f"{shown_key(found)}, not {shown_key(exported)}"
    assert cases.fingerprint(data) == before, f"nothing created or changed: {cases.changed(before, cases.fingerprint(data))}"
    print_success(shown_key(exported))


# =============================================================================
# (d) The check of a secure archive
# =============================================================================


def test_a_secure_archive_is_checked_as_its_clear_zip_after_decrypting_it(instance, tmp_path, databases, monkeypatch):
    """(d) §5 ``stage_archive(..., key=)``: ``decrypting`` first, over the envelope's bytes, into the stage's
    ``archive.zip`` (0600); then the clear zip's check, phase for phase. The report is the clear zip's (tables, rows,
    action, migrations, totals, administrators: everything but the check's own id and dates), ``encrypted`` true. The
    stage holds the copy and its report only, read back equal; no ``secrets/`` in the copy."""
    print_section("The check of a secure archive")
    env = envelope_module()
    new_parameter(stage_archive, "key")
    data = source_dir(tmp_path / "source", databases, monkeypatch)
    _job, path = secure_backup(data)
    opened = open_envelope(env, path, tmp_path / "opened")
    root = checked_on(monkeypatch, instance)
    zip_progress = cases.Progress()
    from_zip = stage_archive(opened.zip, root, progress=zip_progress)
    stage_id = new_stage_id()
    progress = StageWatch(root, stage_id)
    from_envelope = stage_archive(path, root, stage_id=stage_id, progress=progress, key=env.unlock(path, PASSWORD))
    assert (b4_report(from_envelope)["encrypted"], b4_report(from_zip)["encrypted"]) == (True, False), "the report says whether the archive was encrypted"
    differ = sorted(name for name, value in comparable(from_zip).items() if comparable(from_envelope).get(name) != value)
    assert comparable(from_envelope) == comparable(from_zip), f"the check of the envelope is the check of its zip; they differ in {differ}"
    assert progress.phases == ["decrypting", *zip_progress.phases], f"decrypting, then the zip's phases: {progress.phases}, the zip's {zip_progress.phases}"
    size = path.stat().st_size
    decrypting = [(done, total) for phase, done, total in progress.events if phase == "decrypting"]
    assert decrypting[-1] == (size, size) and all(done <= total for done, total in decrypting), f"decrypting counts the envelope's {size} bytes: {decrypting[:2]} … {decrypting[-1:]}"
    assert (progress.at_checking or {}).get("archive.zip") == 0o600, f"the envelope is decrypted into the stage's archive.zip, 0600: {progress.at_checking}"
    stage = stage_dir(root, stage_id)
    assert sorted(os.listdir(stage)) == [STAGE_DATA_FOLDER, STAGE_REPORT_FILE], f"the decrypted zip is gone once unpacked: {sorted(os.listdir(stage))}"
    assert not (stage / STAGE_DATA_FOLDER / "secrets").exists(), "no secrets/ in the copy"
    assert read_report(root, stage_id) == from_envelope, "report.json reads back as returned"
    print_success(f"{progress.phases}: the zip's report, encrypted")


@pytest.mark.parametrize("given", [pytest.param({}, id="no-key-given"), pytest.param({"key": None}, id="key-none")])
def test_a_secure_archive_checked_without_its_key_is_refused_password_required(instance, tmp_path, databases, monkeypatch, given):
    """(d) §5 An envelope without a key: ``password_required``. Nothing of the stage left, the lock free, no path said;
    the envelope only read."""
    env = envelope_module()
    if given:
        new_parameter(stage_archive, "key")
    data = source_dir(tmp_path / "source", databases, monkeypatch)
    _job, path = secure_backup(data)
    sent = cases.sha256(path.read_bytes())
    checked_on(monkeypatch, instance)
    error, _progress = cases.refused(path, instance, **given)
    assert error.code == "password_required", f"password_required, not {error.code}: {error}"
    assert cases.sha256(path.read_bytes()) == sent and env.is_envelope(path), "the envelope is only read"
    print_success(f"password_required: {error}")


def test_a_secure_archive_damaged_in_its_second_chunk_is_refused_envelope_damaged_while_decrypting(instance, tmp_path, databases, monkeypatch):
    """(d) §5 One byte changed in the second chunk: the password still opens the envelope (its header is intact), its
    first chunk decrypts, the second fails: ``envelope_damaged``, before the zip is checked. Nothing of the stage left
    (the part already decrypted included), the lock free, no path said."""
    env = envelope_module()
    new_parameter(stage_archive, "key")
    data = source_dir(tmp_path / "source", databases, monkeypatch, files=noise(env))
    _job, path = secure_backup(data)
    damaged = damaged_copy(env, path, tmp_path / "damaged.lfbk")
    key = env.unlock(damaged, PASSWORD)
    checked_on(monkeypatch, instance)
    error, progress = cases.refused(damaged, instance, key=key)
    assert error.code == "envelope_damaged", f"envelope_damaged, not {error.code}: {error}"
    assert progress.phases == ["decrypting"], f"refused while decrypting, before the zip is checked: {progress.phases}"
    print_success(f"envelope_damaged: {error}")


# =============================================================================
# (e) The key entry of an archive
# =============================================================================


def test_the_zip_decrypt_writes_out_of_a_secure_archive_is_checked_with_its_key_and_rekeys_the_secrets(instance, tmp_path, databases, monkeypatch):
    """(e)(f) §5, revised 23:25: the plain zip ``dev.py backup decrypt`` writes out of an envelope (``decrypt_file``'s
    output as it is, the key entry announced in its manifest) is checked, never refused for its key: restorable,
    ``instance_key_included``, not ``encrypted``. Its key is used as the envelope's: every secret re-encrypted to this
    instance's key (``secrets_rekeyed`` 5, none unreadable, each decrypting with K2's subkey to its value); and never
    unpacked: no ``secrets/`` in the copy, K1 in no file of the stage."""
    print_section("The zip decrypted out of a secure archive")
    env = envelope_module()
    source = secret_source(tmp_path / "source", databases, monkeypatch)
    _job, path = secure_backup(source.data)
    opened = carrying_the_key(open_envelope(env, path, tmp_path / "opened"))
    root = checked_on(monkeypatch, instance)
    own = own_subkey(root)
    report = stage_archive(opened.zip, root)
    assert b4_report(report) == {"encrypted": False, "secrets_rekeyed": len(SECRET_ROWS), "secrets_unreadable": NO_UNREADABLE}, f"the zip's key is used as the envelope's: {b4_report(report)}"
    assert (report.instance_key_included, report.restorable) == (True, True), f"the key included, the archive restorable: {report.instance_key_included}, {report.blockers}"
    assert_rekeyed_to(own, root, report, source)
    print_success(f"the decrypted zip: {len(SECRET_ROWS)} secrets re-encrypted, its key never unpacked")


#: The two forms an archive carrying the key is checked in: the plain zip ``dev.py backup decrypt`` writes, an envelope.
FORMS = [pytest.param(False, id="plain-zip"), pytest.param(True, id="envelope")]


@pytest.mark.parametrize("encrypted", FORMS)
def test_a_secure_archive_repacked_unchanged_is_checked_as_a_zip_and_as_an_envelope(instance, tmp_path, databases, monkeypatch, encrypted):
    """(e) The control of the crafted archives below: a secure archive carrying the key, decrypted and zipped again as the
    staging tests craft archives (then encrypted again, for an envelope) with nothing changed, is checked: restorable,
    the key included, never unpacked. What each case below changes is the only reason it is refused."""
    env = envelope_module()
    if encrypted:
        new_parameter(stage_archive, "key")
    opened = secure_archive_with_its_key(env, tmp_path, databases, monkeypatch)
    archive = packed(env, opened.entries, opened.manifest, tmp_path / "crafted" / "unchanged", encrypted=encrypted)
    root = checked_on(monkeypatch, instance)
    report = stage_archive(archive, root, **key_for(env, archive, encrypted))
    assert (report.restorable, report.instance_key_included, b4_report(report)["encrypted"]) == (True, True, encrypted), f"checked, the key included: {report.blockers}, {report.instance_key_included}"
    assert not (stage_dir(root, report.stage_id) / STAGE_DATA_FOLDER / "secrets").exists(), "the key entry is never unpacked"
    print_success(f"{'an envelope' if encrypted else 'a plain zip'} repacked unchanged: checked")


def key_not_announced(opened: Opened) -> tuple[dict[str, bytes], dict[str, Any]]:
    """The key held, the manifest saying none is."""
    return opened.entries, {**opened.manifest, "instance_key": {"included": False, "sha256": None}}


def key_announced_missing(opened: Opened) -> tuple[dict[str, bytes], dict[str, Any]]:
    """The key announced, not held."""
    return {name: data for name, data in opened.entries.items() if name != KEY_ENTRY}, opened.manifest


def key_announced_with_another_sha256(opened: Opened) -> tuple[dict[str, bytes], dict[str, Any]]:
    """The key held, announced with another SHA-256."""
    return opened.entries, {**opened.manifest, "instance_key": {**opened.manifest["instance_key"], "sha256": cases.sha256(b"another key")}}


def key_of_other_bytes(opened: Opened) -> tuple[dict[str, bytes], dict[str, Any]]:
    """Another text of the same length in the key's entry, its announcement unchanged."""
    return {**opened.entries, KEY_ENTRY: SOURCE_KEY[::-1].encode("utf-8")}, opened.manifest


KEY_ENTRY_REFUSALS = [
    pytest.param(key_not_announced, "unexpected_entry", id="key-not-announced"),
    pytest.param(key_announced_missing, "missing_entry", id="key-announced-missing"),
    pytest.param(key_announced_with_another_sha256, "checksum_mismatch", id="key-announced-with-another-sha256"),
    pytest.param(key_of_other_bytes, "checksum_mismatch", id="key-of-other-bytes"),
]


@pytest.mark.parametrize("encrypted", FORMS)
@pytest.mark.parametrize(("craft", "code"), KEY_ENTRY_REFUSALS)
def test_a_key_entry_not_announced_or_not_intact_is_refused_in_a_zip_as_in_an_envelope(instance, tmp_path, databases, monkeypatch, craft, code, encrypted):
    """(e) §5 The key entry is accepted only announced with its SHA-256, in a zip as in an envelope. Present but not
    announced: ``unexpected_entry``; announced and missing: ``missing_entry``; another SHA-256, or other bytes:
    ``checksum_mismatch``. An envelope is decrypted first, a zip is not; nothing of the stage left, the lock free, no
    path said."""
    env = envelope_module()
    if encrypted:
        new_parameter(stage_archive, "key")
    entries, manifest = craft(secure_archive_with_its_key(env, tmp_path, databases, monkeypatch))
    archive = packed(env, entries, manifest, tmp_path / "crafted" / "archive", encrypted=encrypted)
    checked_on(monkeypatch, instance)
    error, progress = cases.refused(archive, instance, **key_for(env, archive, encrypted))
    assert error.code == code, f"{code}, not {error.code}: {error}"
    assert (progress.phases[:1] == ["decrypting"]) is encrypted, f"an envelope is decrypted first, a zip is not: {progress.phases}"
    print_success(f"{'an envelope' if encrypted else 'a plain zip'}, {code}: {error}")


# =============================================================================
# (f) The plugin secrets of the copy
# =============================================================================


def test_a_secure_archive_s_plugin_secrets_are_re_encrypted_to_this_instance_s_key_on_the_copy(instance, tmp_path, databases, monkeypatch):
    """(f) §5, decision 39: the archive carries K1, this instance's key is K2. Every secret of the copy re-encrypted:
    ``secrets_rekeyed`` 5, none unreadable; each decrypts with K2's subkey to its value and carries K2's key id. The
    archive's key never unpacked: no ``secrets/`` in the copy, K1 in no file of the stage. The report reads back equal."""
    print_section("The plugin secrets of a secure archive")
    env = envelope_module()
    new_parameter(stage_archive, "key")
    source = secret_source(tmp_path / "source", databases, monkeypatch)
    _job, path = secure_backup(source.data)
    root = checked_on(monkeypatch, instance)
    own = own_subkey(root)
    report = stage_archive(path, root, key=env.unlock(path, PASSWORD))
    assert b4_report(report) == {"encrypted": True, "secrets_rekeyed": len(SECRET_ROWS), "secrets_unreadable": NO_UNREADABLE}, f"every secret re-encrypted: {b4_report(report)}"
    assert (report.instance_key_included, report.restorable) == (True, True), f"the key included, the archive restorable: {report.instance_key_included}, {report.blockers}"
    assert_rekeyed_to(own, root, report, source)
    assert read_report(root, report.stage_id) == report, "report.json reads back as returned"
    print_success(f"{len(SECRET_ROWS)} secrets re-encrypted under {key_id_of(own)[:8]}…")


def test_a_clear_archive_s_plugin_secrets_stay_as_the_backup_holds_them_and_are_counted_unreadable(instance, tmp_path, databases, monkeypatch):
    """(f) §5 A clear zip carries no key: on this instance (K2) nothing is rekeyed, every secret under K1 is counted
    unreadable by scope and left exactly as the backup holds it, never deleted, never given a wrong value."""
    source = secret_source(tmp_path / "source", databases, monkeypatch)
    archive = clear_backup(source.data)
    held = stored_secrets(source.data / DATABASE_ENTRY)
    root = checked_on(monkeypatch, instance)
    assert settings_subkey() != subkey_of(SOURCE_KEY), "precondition: this instance's own key is not K1"
    report = stage_archive(archive, root)
    assert b4_report(report) == {"encrypted": False, "secrets_rekeyed": 0, "secrets_unreadable": SECRETS_BY_SCOPE}, f"nothing rekeyed, every secret unreadable: {b4_report(report)}"
    assert stored_secrets(copy_database(root, report)) == held, "the secrets of the copy are the backup's, untouched"
    print_success(f"unreadable {SECRETS_BY_SCOPE}")


def test_a_clear_archive_checked_by_an_instance_with_the_same_key_has_no_unreadable_secret(instance, tmp_path, databases, monkeypatch):
    """(f) §5 This instance's key is K1 too (configured): a clear zip's secrets are all readable, nothing to rekey, the
    rows as the backup holds them."""
    source = secret_source(tmp_path / "source", databases, monkeypatch)
    archive = clear_backup(source.data)
    held = stored_secrets(source.data / DATABASE_ENTRY)
    root = checked_on(monkeypatch, instance)
    monkeypatch.setenv("LIBREFOLIO_INSTANCE_KEY", SOURCE_KEY)
    assert settings_subkey() == subkey_of(SOURCE_KEY), "precondition: this instance's key is K1, configured"
    report = stage_archive(archive, root)
    assert b4_report(report) == {"encrypted": False, "secrets_rekeyed": 0, "secrets_unreadable": NO_UNREADABLE}, f"every secret readable: {b4_report(report)}"
    assert stored_secrets(copy_database(root, report)) == held, "the secrets of the copy are the backup's, untouched"
    print_success("same key: nothing unreadable")


def own_key_too_short(monkeypatch: pytest.MonkeyPatch) -> None:
    """This instance's key is configured, too short to be used."""
    monkeypatch.setenv("LIBREFOLIO_INSTANCE_KEY", "too-short-a-key")


def own_derivation_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """``settings_subkey`` raises ``InstanceKeyError``, wherever it is called from: the derivation it calls refuses."""

    def refuse(purpose: str, length: int = 32) -> bytes:
        raise InstanceKeyError("this instance's key cannot be used (a test's refusal)")

    monkeypatch.setattr(crypto, "derive_key", refuse)


OWN_KEY_UNUSABLE = [
    pytest.param(own_key_too_short, id="configured-key-too-short"),
    pytest.param(own_derivation_refused, id="settings-subkey-raises"),
]


@pytest.mark.parametrize("unusable", OWN_KEY_UNUSABLE)
def test_without_a_usable_key_of_its_own_the_check_rekeys_nothing_and_counts_every_secret_unreadable(instance, tmp_path, databases, monkeypatch, unusable):
    """(f) §5 ``settings_subkey`` raises ``InstanceKeyError`` (this instance's key configured too short, or the
    derivation refused): the check goes on to its end, restorable, nothing rekeyed though the archive carries K1, every
    secret counted unreadable and left as the backup holds it."""
    env = envelope_module()
    new_parameter(stage_archive, "key")
    source = secret_source(tmp_path / "source", databases, monkeypatch)
    _job, path = secure_backup(source.data)
    held = stored_secrets(source.data / DATABASE_ENTRY)
    key = env.unlock(path, PASSWORD)
    root = checked_on(monkeypatch, instance)
    unusable(monkeypatch)
    with pytest.raises(InstanceKeyError):
        settings_subkey()
    report = stage_archive(path, root, key=key)
    assert b4_report(report) == {"encrypted": True, "secrets_rekeyed": 0, "secrets_unreadable": SECRETS_BY_SCOPE}, f"nothing rekeyed, every secret unreadable: {b4_report(report)}"
    assert (report.instance_key_included, report.restorable) == (True, True), f"the check went on to its end: {report.instance_key_included}, {report.blockers}"
    assert stored_secrets(copy_database(root, report)) == held, "the secrets of the copy are the backup's, untouched"
    print_success(f"no key of its own: unreadable {SECRETS_BY_SCOPE}")


def test_an_archive_key_that_cannot_be_derived_from_is_as_no_key(instance, tmp_path, databases, monkeypatch):
    """(f) §5 The archive's key entry, announced and intact, is too short for ``derive_key_from``: as without a key —
    the check done, nothing rekeyed, every secret counted unreadable and left as the backup holds it."""
    env = envelope_module()
    new_parameter(stage_archive, "key")
    source = secret_source(tmp_path / "source", databases, monkeypatch)
    _job, path = secure_backup(source.data)
    held = stored_secrets(source.data / DATABASE_ENTRY)
    opened = carrying_the_key(open_envelope(env, path, tmp_path / "opened"))
    short = "a-key-too-short"
    with pytest.raises(InstanceKeyError):
        derive_key_from(short, SUBKEY_PURPOSE, SUBKEY_LENGTH)
    manifest = {**opened.manifest, "instance_key": {**opened.manifest["instance_key"], "sha256": cases.sha256(short.encode("utf-8"))}}
    crafted = packed(env, {**opened.entries, KEY_ENTRY: short.encode("utf-8")}, manifest, tmp_path / "crafted" / "short-key", encrypted=True)
    root = checked_on(monkeypatch, instance)
    report = stage_archive(crafted, root, key=env.unlock(crafted, PASSWORD))
    assert b4_report(report) == {"encrypted": True, "secrets_rekeyed": 0, "secrets_unreadable": SECRETS_BY_SCOPE}, f"as without a key: {b4_report(report)}"
    assert stored_secrets(copy_database(root, report)) == held, "the secrets of the copy are the backup's, untouched"
    print_success("an archive key too short: as no key")


# =============================================================================
# (i) Lot B-18: the old instance key, given to the check of a clear archive
# =============================================================================

#: (B-18) Keys a check may be given besides the archive (``stage_archive(..., instance_key=)``): one of 32 characters,
#: the fewest a key has, that is neither K1 nor this instance's; one of 31, which no key is. Test keys, not secrets.
OTHER_INSTANCE_KEY = "LibreFolio-b18-another-key-".ljust(32, "0")
SHORT_INSTANCE_KEY = "LibreFolio-b18-short-key-".ljust(31, "0")
#: What the check says of a key too short (contract §1): never the key, nor its length.
INSTANCE_KEY_TOO_SHORT = "The instance key given is too short: an instance key has at least 32 characters"
#: This instance's own key, K2: the text of the staging tests' live instance's key file.
OWN_KEY = cases.SECRET.decode("utf-8")
#: Keys too short, and whether an earlier check left a ``.restore`` behind.
SHORT_KEYS = [pytest.param(SHORT_INSTANCE_KEY, id="31-characters"), pytest.param("", id="empty")]
EARLIER_CHECK = [pytest.param(False, id="no-restore-folder"), pytest.param(True, id="an-earlier-check-left-one")]


def b18_parameter() -> None:
    """``stage_archive`` takes ``instance_key``, which lot B-18 adds: each red case of (i) asks it first."""
    new_parameter(stage_archive, "instance_key", by="lot B-18 adds it (contract §1)")


def instance_key_given(value: str | None) -> dict[str, Any]:
    """``instance_key=value`` for ``stage_archive`` once lot B-18 adds the parameter, nothing before. The guards of (i)
    pass it so: today they pin today's check, and after B-18 the same check with the key given."""
    return {"instance_key": value} if "instance_key" in inspect.signature(stage_archive).parameters else {}


def logged_text(events: list[dict[str, Any]]) -> list[str]:
    """Each event logged in the block but the barrier's, as text: where a key, or what is said of its length, must never
    be."""
    return [repr(event) for event in events if event.get("event") != cases.LOG_CANARY]


def restore_tree(root: Path) -> dict[str, tuple] | None:
    """What ``.restore`` holds, every path with its mode and, for a file, its size and SHA-256; ``None`` where there is
    none."""
    folder = restore_dir(root)
    return cases.fingerprint(folder) if os.path.lexists(folder) else None


def an_earlier_check(root: Path) -> None:
    """What an earlier check leaves in ``.restore``: the checks' folder with its lock file, and a stage with its report."""
    ensure_private_dir(stages_dir(root), root)
    (stages_dir(root) / STAGE_LOCK_FILE).touch(mode=0o600)
    stage = stage_dir(root, new_stage_id())
    stage.mkdir(mode=0o700)
    (stage / STAGE_REPORT_FILE).write_text("{}\n", encoding="utf-8")


def test_a_clear_archive_checked_with_the_old_instance_key_has_every_secret_re_encrypted(instance, tmp_path, databases, monkeypatch):
    """(i) B-18 §1 (k1) A clear archive carries no key; its check is given the source's, K1 (``instance_key``), on this
    instance (K2): every secret re-encrypted from it — ``secrets_rekeyed`` 5, none unreadable — each decrypting with
    K2's subkey to its value under K2's key id; K1 in no file of the stage and in no line of the log; restorable."""
    print_section("B-18: the old instance key, given to the check of a clear archive")
    b18_parameter()
    source = secret_source(tmp_path / "source", databases, monkeypatch)
    archive = clear_backup(source.data)
    root = checked_on(monkeypatch, instance)
    own = own_subkey(root)
    with cases.staging_logs() as events:
        report = stage_archive(archive, root, instance_key=SOURCE_KEY)
    assert b4_report(report) == {"encrypted": False, "secrets_rekeyed": len(SECRET_ROWS), "secrets_unreadable": NO_UNREADABLE}, f"every secret re-encrypted from the key given: {b4_report(report)}"
    assert (report.instance_key_included, report.restorable) == (False, True), f"a clear archive, restorable: {report.instance_key_included}, {report.blockers}"
    assert_rekeyed_to(own, root, report, source)
    assert [line for line in logged_text(events) if SOURCE_KEY in line] == [], "the key given is in no line of the log"
    print_success(f"{len(SECRET_ROWS)} secrets re-encrypted from the key given")


def test_a_wrong_instance_key_reads_no_secret_and_the_check_ends_without_an_error(instance, tmp_path, databases, monkeypatch):
    """(i) B-18 §1 (k2) The key given is a key (32 characters) but not the source's: it reads none of the secrets.
    Nothing rekeyed, every secret counted unreadable by scope and left as the backup holds it, and the check ends without
    an error, restorable — as with a wrong archive key; the key in no line of the log."""
    b18_parameter()
    source = secret_source(tmp_path / "source", databases, monkeypatch)
    archive = clear_backup(source.data)
    held = stored_secrets(source.data / DATABASE_ENTRY)
    root = checked_on(monkeypatch, instance)
    own = own_subkey(root)
    assert len(OTHER_INSTANCE_KEY) == 32 and subkey_of(OTHER_INSTANCE_KEY) not in (subkey_of(SOURCE_KEY), own), "precondition: a key of 32 characters, neither K1 nor this instance's"
    with cases.staging_logs() as events:
        report = stage_archive(archive, root, instance_key=OTHER_INSTANCE_KEY)
    assert b4_report(report) == {"encrypted": False, "secrets_rekeyed": 0, "secrets_unreadable": SECRETS_BY_SCOPE}, f"nothing rekeyed, every secret unreadable: {b4_report(report)}"
    assert report.restorable, f"the check ends, restorable: {report.blockers}"
    assert stored_secrets(copy_database(root, report)) == held, "the secrets of the copy are the backup's, untouched"
    assert [line for line in logged_text(events) if OTHER_INSTANCE_KEY in line] == [], "the key given is in no line of the log"
    print_success(f"a wrong key: unreadable {SECRETS_BY_SCOPE}, no error")


@pytest.mark.parametrize("earlier", EARLIER_CHECK)
@pytest.mark.parametrize("key", SHORT_KEYS)
def test_an_instance_key_too_short_is_refused_before_anything_is_created(instance, tmp_path, databases, monkeypatch, key, earlier):
    """(i) B-18 §1 (k3) A key shorter than 32 characters is no key: ``StagingError`` ``instance_key_invalid``, in the
    contract's words, checked first — before the lock and before any folder: no ``.restore`` where there was none (no
    stage, no lock file), the one an earlier check left byte for byte, no progress reported. Neither the key nor what
    ``derive_key_from`` says of its length is in the message or in any line of the log."""
    b18_parameter()
    source = secret_source(tmp_path / "source", databases, monkeypatch)
    archive = clear_backup(source.data)
    root = checked_on(monkeypatch, instance)
    if earlier:
        an_earlier_check(root)
    before = restore_tree(root)
    assert (before is None) is not earlier, f"precondition: .restore {'left by an earlier check' if earlier else 'absent'}"
    with pytest.raises(InstanceKeyError) as derivation:
        derive_key_from(key, SUBKEY_PURPOSE, SUBKEY_LENGTH)
    length_said = str(derivation.value)
    progress = cases.Progress()
    with cases.staging_logs() as events, pytest.raises(staging.StagingError) as raised:
        stage_archive(archive, root, progress=progress, instance_key=key)
    error = raised.value
    assert (error.code, str(error)) == ("instance_key_invalid", INSTANCE_KEY_TOO_SHORT), f"instance_key_invalid, in the contract's words: {error.code}: {error}"
    assert (restore_tree(root), progress.events) == (before, []), f"checked first: nothing created or changed in .restore, no progress: {progress.events}"
    leaked = [line for line in logged_text(events) if (key and key in line) or length_said in line]
    assert not leaked, f"neither the key nor its length in any line of the log: {leaked}"
    print_success(f"{len(key)} characters: instance_key_invalid, nothing created")


def test_a_secure_archive_s_own_key_wins_over_the_instance_key_given(instance, tmp_path, databases, monkeypatch):
    """(i) B-18 §1 (k4) The archive carries K1 (an envelope, its ``key`` given) and the check is given another valid key:
    the archive's own key wins — every secret re-encrypted from K1, ``secrets_rekeyed`` 5, none unreadable."""
    b18_parameter()
    env = envelope_module()
    source = secret_source(tmp_path / "source", databases, monkeypatch)
    _job, path = secure_backup(source.data)
    root = checked_on(monkeypatch, instance)
    own = own_subkey(root)
    report = stage_archive(path, root, key=env.unlock(path, PASSWORD), instance_key=OTHER_INSTANCE_KEY)
    assert b4_report(report) == {"encrypted": True, "secrets_rekeyed": len(SECRET_ROWS), "secrets_unreadable": NO_UNREADABLE}, f"re-encrypted from the archive's own key: {b4_report(report)}"
    assert (report.instance_key_included, report.restorable) == (True, True), f"the key included, restorable: {report.instance_key_included}, {report.blockers}"
    assert_rekeyed_to(own, root, report, source)
    print_success("the archive's own key wins")


def test_no_instance_key_given_is_today_s_check_of_a_clear_archive(instance, tmp_path, databases, monkeypatch):
    """(i) B-18 §1 (k5) A guard, green before B-18 too: ``instance_key=None`` (passed once the parameter exists) is
    today's check of a clear archive — nothing rekeyed, every secret unreadable by scope, the rows as the backup holds
    them."""
    source = secret_source(tmp_path / "source", databases, monkeypatch)
    archive = clear_backup(source.data)
    held = stored_secrets(source.data / DATABASE_ENTRY)
    root = checked_on(monkeypatch, instance)
    own_subkey(root)
    report = stage_archive(archive, root, **instance_key_given(None))
    assert b4_report(report) == {"encrypted": False, "secrets_rekeyed": 0, "secrets_unreadable": SECRETS_BY_SCOPE}, f"nothing rekeyed, every secret unreadable: {b4_report(report)}"
    assert stored_secrets(copy_database(root, report)) == held, "the secrets of the copy are the backup's, untouched"
    print_success(f"no key given: unreadable {SECRETS_BY_SCOPE}")


def test_a_wrong_instance_key_on_an_archive_of_this_very_instance_changes_nothing(instance, tmp_path, databases, monkeypatch):
    """(i) B-18 §1 (k6) A guard, green before B-18 too: the archive's secrets are under this instance's own key (K2)
    already; a wrong key given (passed once the parameter exists) rekeys nothing and finds nothing unreadable, the rows
    as the backup holds them."""
    source = secret_source(tmp_path / "source", databases, monkeypatch, key=OWN_KEY)
    archive = clear_backup(source.data)
    held = stored_secrets(source.data / DATABASE_ENTRY)
    root = checked_on(monkeypatch, instance)
    assert settings_subkey() == subkey_of(OWN_KEY) != subkey_of(OTHER_INSTANCE_KEY), "precondition: an archive of this very instance, its secrets under this instance's key; the key given another"
    report = stage_archive(archive, root, **instance_key_given(OTHER_INSTANCE_KEY))
    assert b4_report(report) == {"encrypted": False, "secrets_rekeyed": 0, "secrets_unreadable": NO_UNREADABLE}, f"nothing to rekey, nothing unreadable: {b4_report(report)}"
    assert stored_secrets(copy_database(root, report)) == held, "the secrets of the copy are the backup's, untouched"
    print_success("this very instance's archive: nothing rekeyed, nothing unreadable")


# =============================================================================
# (g) The checks of the restore, an envelope uploaded
# =============================================================================


def test_an_envelope_upload_asks_its_password_before_any_check_and_is_kept_for_the_next_start(instance, tmp_path, databases, monkeypatch):
    """(g) §5 No password (none given, or ``None``): ``PasswordRequiredError``; a wrong one: ``EnvelopeError``
    ``wrong_password``. Each time the upload kept as sent, no check state, no stage, no thread, the lock free, no
    password in the error. The right password then starts the check of that same upload: its thread is given the key,
    never the password; the check ends done, its report ``encrypted``, the upload removed as today, and no file of
    ``.restore`` holds the password."""
    print_section("An envelope uploaded for a restore")
    env = envelope_module()
    new_parameter(restore_jobs.start_check, "password")
    data = source_dir(tmp_path / "source", databases, monkeypatch)
    _job, path = secure_backup(data)
    root = checked_on(monkeypatch, instance)
    threads = fake_threads(monkeypatch)
    upload_id = uploaded(root, path)
    sent = cases.sha256(path.read_bytes())
    for given in ({}, {"password": None}):
        with pytest.raises(password_required_error()):
            restore_jobs.start_check(upload_id, data_dir=root, **given)
        assert_nothing_started(root, upload_id, sent, threads, f"password_required, {given or 'no password given'}")
    with pytest.raises(env.EnvelopeError) as raised:
        restore_jobs.start_check(upload_id, data_dir=root, password=WRONG_PASSWORD)
    assert raised.value.code == "wrong_password", f"wrong_password, not {raised.value.code}: {raised.value}"
    assert WRONG_PASSWORD not in f"{raised.value} {raised.value!r}", "the password tried is not in the error"
    assert_nothing_started(root, upload_id, sent, threads, "wrong_password")
    check = restore_jobs.start_check(upload_id, data_dir=root, password=PASSWORD)
    assert (check.upload_id, check.status, len(threads.started)) == (upload_id, "running", 1), f"the check of the same upload starts, in a thread: {check}, {threads.started}"
    assert PASSWORD not in repr((threads.started[0].args, threads.started[0].kwargs)), "the check's thread is given the key, never the password"
    ended = restore_jobs.read_check(check.stage_id, data_dir=root)
    assert (ended.status, ended.error_code) == ("done", None), f"the check ends done: {ended}"
    assert not upload_path(root, upload_id).exists(), "the upload is removed once its check ended, as today"
    assert b4_report(read_report(root, check.stage_id))["encrypted"] is True, "the report says the archive was encrypted"
    assert files_holding(restore_dir(root), PASSWORD.encode("utf-8")) == [], "no file of .restore holds the password"
    print_success("password_required, wrong_password, then done from the same upload")


def header_too_short(env: ModuleType, envelope: Path, target: Path) -> None:
    """The envelope's first 51 bytes: the magic, and less than a header."""
    target.write_bytes(envelope.read_bytes()[: env.HEADER_SIZE - 1])


def another_format_version(env: ModuleType, envelope: Path, target: Path) -> None:
    """The envelope, its header saying another version of the format."""
    raw = bytearray(envelope.read_bytes())
    raw[4] = env.FORMAT_VERSION + 1
    target.write_bytes(bytes(raw))


def scrypt_cost_out_of_bounds(env: ModuleType, envelope: Path, target: Path) -> None:
    """The envelope, its header asking scrypt for n = 2^30: refused before any derivation."""
    raw = bytearray(envelope.read_bytes())
    raw[6] = 30
    target.write_bytes(bytes(raw))


UNUSABLE_HEADERS = [
    pytest.param(header_too_short, "envelope_damaged", id="header-too-short"),
    pytest.param(another_format_version, "envelope_unsupported", id="another-format-version"),
    pytest.param(scrypt_cost_out_of_bounds, "envelope_unsupported", id="scrypt-cost-2-to-the-30"),
]


@pytest.mark.parametrize(("spoil", "code"), UNUSABLE_HEADERS)
def test_an_envelope_whose_header_cannot_be_used_is_refused_at_the_start_and_kept(instance, tmp_path, monkeypatch, spoil, code):
    """(g) §5 ``unlock`` refuses the header, before any derivation: a header too short is ``envelope_damaged``, another
    version or a scrypt cost out of bounds ``envelope_unsupported``, re-raised by the start. The upload kept as sent, no
    check state, no stage, no thread, the lock free."""
    env = envelope_module()
    new_parameter(restore_jobs.start_check, "password")
    spoiled = tmp_path / "spoiled.lfbk"
    spoil(env, small_envelope(env, tmp_path), spoiled)
    assert env.is_envelope(spoiled), "precondition: it still starts as an envelope"
    root = checked_on(monkeypatch, instance)
    threads = fake_threads(monkeypatch)
    upload_id = uploaded(root, spoiled)
    with pytest.raises(env.EnvelopeError) as raised:
        restore_jobs.start_check(upload_id, data_dir=root, password=PASSWORD)
    assert raised.value.code == code, f"{code}, not {raised.value.code}: {raised.value}"
    assert_nothing_started(root, upload_id, cases.sha256(spoiled.read_bytes()), threads, code)
    print_success(f"{code}: refused at the start, the upload kept")


def test_while_another_check_runs_an_envelope_start_is_busy_before_any_question_of_password(instance, tmp_path, monkeypatch):
    """(g) §5 The lock first: while another check holds it, a start is ``StagingBusyError``, without a password as with a
    wrong one; the upload kept, nothing written, the lock still its holder's."""
    env = envelope_module()
    new_parameter(restore_jobs.start_check, "password")
    envelope = small_envelope(env, tmp_path)
    root = checked_on(monkeypatch, instance)
    threads = fake_threads(monkeypatch)
    upload_id = uploaded(root, envelope)
    sent = cases.sha256(envelope.read_bytes())
    holder = jobs._RunLock(ensure_private_dir(stages_dir(root), root) / STAGE_LOCK_FILE)
    assert holder.try_acquire(), "precondition: nobody holds the lock of the checks"
    try:
        for given in ({}, {"password": WRONG_PASSWORD}):
            with pytest.raises(StagingBusyError):
                restore_jobs.start_check(upload_id, data_dir=root, **given)
            assert_nothing_started(root, upload_id, sent, threads, f"busy, {given or 'no password given'}", lock_free=False)
    finally:
        holder.release()
    print_success("busy before any question of password")


def test_an_envelope_damaged_in_a_chunk_ends_its_check_failed_envelope_damaged_and_leaves_nothing(instance, tmp_path, databases, monkeypatch):
    """(g) §5 The password opens the envelope, its check starts; a chunk fails while it is decrypted: the check ends
    ``failed``, ``envelope_damaged``; nothing of the stage left, the upload removed as at the end of any check, the lock
    free."""
    env = envelope_module()
    new_parameter(restore_jobs.start_check, "password")
    data = source_dir(tmp_path / "source", databases, monkeypatch, files=noise(env))
    _job, path = secure_backup(data)
    damaged = damaged_copy(env, path, tmp_path / "damaged.lfbk")
    root = checked_on(monkeypatch, instance)
    fake_threads(monkeypatch)
    upload_id = uploaded(root, damaged)
    check = restore_jobs.start_check(upload_id, data_dir=root, password=PASSWORD)
    ended = restore_jobs.read_check(check.stage_id, data_dir=root)
    assert (ended.status, ended.error_code) == ("failed", "envelope_damaged"), f"the check ends failed, envelope_damaged: {ended}"
    left = (cases.leftover_stages(root), upload_path(root, upload_id).exists(), cases.lock_is_free(root))
    assert left == ([], False, True), f"no stage, the upload removed, the lock free: {left}"
    print_success("envelope_damaged: the check failed, nothing left")


def test_a_password_given_with_a_clear_zip_is_ignored(instance, tmp_path, databases, monkeypatch):
    """(g) §5 A zip with a password: the password is ignored, never handed to the check's thread; the check ends done,
    its report not ``encrypted``."""
    new_parameter(restore_jobs.start_check, "password")
    data = source_dir(tmp_path / "source", databases, monkeypatch)
    archive = clear_backup(data)
    root = checked_on(monkeypatch, instance)
    threads = fake_threads(monkeypatch)
    upload_id = uploaded(root, archive)
    check = restore_jobs.start_check(upload_id, data_dir=root, password=PASSWORD)
    ended = restore_jobs.read_check(check.stage_id, data_dir=root)
    assert (ended.status, ended.error_code, len(threads.started)) == ("done", None, 1), f"the check ends done: {ended}"
    assert PASSWORD not in repr((threads.started[0].args, threads.started[0].kwargs)), "the password is never handed to the check's thread"
    assert b4_report(read_report(root, check.stage_id))["encrypted"] is False, "the report says the archive was not encrypted"
    print_success("a zip: the password ignored")


# =============================================================================
# (h) Lot B4b, B-26: a key the archive could not give back is not exported
# =============================================================================


UNUSABLE_GENERATED_KEYS = [
    pytest.param(generated_key, False, id="generated"),
    pytest.param(configured_key, False, id="configured-key-a-key-file-beside-it"),
    pytest.param(no_key_yet, False, id="no-key-yet"),
    pytest.param(unusable_key, True, id="generated-10-characters"),
    *bound_cases(KEY_AT_THE_BOUND, lambda key: False),
    *bound_cases(KEY_OVER_THE_BOUND, lambda key: True),
]


@pytest.mark.parametrize(("arrange", "unusable"), UNUSABLE_GENERATED_KEYS)
def test_generated_key_unusable_is_true_for_a_generated_key_a_secure_backup_leaves_out(tmp_path, monkeypatch, arrange, unusable):
    """(h) ``generated_key_unusable()``, the warning's question: true for a generated key the instance key module cannot
    use (10 characters, as before) and — lot B4b — for one it reads fine but that is over ``INSTANCE_KEY_MAX_BYTES``
    bytes of UTF-8, which no restore could read back; false for a usable generated key up to the bound, a configured key
    and no key yet. Never raises; nothing created or changed."""
    secure = secure_module()
    data = tmp_path / "data"
    data.mkdir()
    cases.configure(monkeypatch, data)
    arrange(data, monkeypatch, tmp_path)
    before = cases.fingerprint(data)
    found = secure.generated_key_unusable()
    assert found is unusable, f"generated_key_unusable(): {found!r}, not {unusable!r} (instance key status: {instance_key_status()})"
    assert cases.fingerprint(data) == before, f"nothing created or changed: {cases.changed(before, cases.fingerprint(data))}"
    print_success(f"unusable: {unusable}")


@pytest.mark.parametrize("form", list(KEY_OVER_THE_BOUND))
def test_a_generated_key_over_4096_bytes_stays_out_of_a_secure_backup_with_a_warning(instance, tmp_path, databases, monkeypatch, form):
    """(h) Lot B4b, B-26: a restore reads the key entry up to ``INSTANCE_KEY_MAX_BYTES`` (4096) bytes and refuses a larger
    one, so a generated key of 4097 bytes of UTF-8 — 4097 ASCII characters, or 2049 characters of which 2048 take two
    bytes — which the instance key module reads and uses, is not exported: the secure backup is done without a key
    entry, ``instance_key.included`` false, warned ``instance_key_unusable``; the key file untouched; and a check of that
    archive is not refused for it: restorable, no key included."""
    print_section(f"(h) A generated key over the bound, {form}")
    env = envelope_module()
    key = KEY_OVER_THE_BOUND[form]
    assert (INSTANCE_KEY_MAX_BYTES, len(key.encode("utf-8"))) == (KEY_MAX_BYTES, KEY_MAX_BYTES + 1), f"precondition: the bound is 4096 bytes and this key one byte over it: {INSTANCE_KEY_MAX_BYTES}, {shown_key(key)}"
    data = source_dir(tmp_path / "source", databases, monkeypatch, key=key)
    key_file = data / INSTANCE_KEY_FILE
    before = key_file.read_bytes()
    status = instance_key_status()
    assert (status.source, status.problem) == ("generated", None), f"precondition: the instance key module finds a generated key without a problem of its own: {status}"
    assert settings_subkey() == subkey_of(key), "precondition: it is the key this instance derives its keys from"
    job, path = secure_backup(data)
    opened = open_envelope(env, path, tmp_path / "opened")
    keys = {name: len(entry) for name, entry in opened.entries.items() if name.startswith("secrets/")}
    assert (keys, opened.manifest["instance_key"]["included"]) == ({}, False), f"a key no restore could read back stays out of the archive: entries {keys} (bytes), {opened.manifest['instance_key']}"
    assert (new_field(job, "encrypted"), tuple(job.warnings)) == (True, ("instance_key_unusable",)), f"the secure backup is done, warned that the key stayed out: {job}"
    assert key_file.read_bytes() == before, "the key file is never changed"
    root = checked_on(monkeypatch, instance)
    report = stage_archive(path, root, key=env.unlock(path, PASSWORD))
    assert (report.restorable, report.instance_key_included, b4_report(report)["encrypted"]) == (True, False, True), f"a check of the archive is not refused for its key: restorable, no key included: {report.blockers}, {report.instance_key_included}"
    print_success(f"{shown_key(key)}: no key entry, instance_key_unusable, the archive restorable")


@pytest.mark.parametrize("form", list(KEY_AT_THE_BOUND))
def test_a_generated_key_of_4096_bytes_travels_in_a_secure_backup_and_a_check_reads_it_back(instance, tmp_path, databases, monkeypatch, form):
    """(h) Lot B4b, B-26, the boundary: a generated key of exactly 4096 bytes of UTF-8 — 4096 ASCII characters, or 2048
    two-byte ones — is exported: the entry is its text, announced with its SHA-256, no warning. A check of that archive
    reads it back: the copy's secrets, encrypted by the source under that key, are re-encrypted to this instance's key
    (``secrets_rekeyed`` 5, none unreadable), and the key is never unpacked."""
    env = envelope_module()
    key = KEY_AT_THE_BOUND[form]
    assert (INSTANCE_KEY_MAX_BYTES, len(key.encode("utf-8"))) == (KEY_MAX_BYTES, KEY_MAX_BYTES), f"precondition: the bound is 4096 bytes and this key exactly that: {INSTANCE_KEY_MAX_BYTES}, {shown_key(key)}"
    source = secret_source(tmp_path / "source", databases, monkeypatch, key=key)
    job, path = secure_backup(source.data)
    assert tuple(job.warnings) == (), f"a usable key at the bound: no warning: {job.warnings}"
    opened = open_envelope(env, path, tmp_path / "opened")
    entry = opened.entries.get(KEY_ENTRY) or b""
    announced = opened.manifest.get("instance_key") or {}
    assert (entry == key.encode("utf-8"), announced.get("included"), announced.get("sha256")) == (True, True, cases.sha256(key.encode("utf-8"))), f"the key travels, its text, announced with its SHA-256: an entry of {len(entry)} bytes, {announced}"
    root = checked_on(monkeypatch, instance)
    own = own_subkey(root, source_key=key)
    report = stage_archive(path, root, key=env.unlock(path, PASSWORD))
    assert b4_report(report) == {"encrypted": True, "secrets_rekeyed": len(SECRET_ROWS), "secrets_unreadable": NO_UNREADABLE}, f"the check reads the key back and re-encrypts every secret with it: {b4_report(report)}"
    assert (report.instance_key_included, report.restorable) == (True, True), f"the key included, the archive restorable: {report.instance_key_included}, {report.blockers}"
    assert_rekeyed_to(own, root, report, source)
    print_success(f"{shown_key(key)}: exported, read back, {len(SECRET_ROWS)} secrets re-encrypted")

"""Checking a backup archive for a restore (lot B2): unpacked into a folder of its own, its database brought to the
app's schema on the copy, and described in a report. The live data directory is never touched.

The steps, each refusing with a stable ``code`` (``StagingError``):

0. **A secure backup** (an ``.lfbk`` envelope, lot B4) is first decrypted beside the copy with the key its password
   gave (``envelope.unlock``): without one, ``password_required``; a chunk that fails, ``envelope_damaged``. The
   decrypted archive is removed once unpacked. A secure backup's archive carries the instance key when LibreFolio
   generated it, announced by its manifest: it is read, never unpacked, and ``secrets/`` is never part of the copy.
1. **A LibreFolio backup.** The archive is a zip whose manifest LibreFolio wrote: a copy of a data directory made by
   hand is not restored from here (decision 42: it is put back by pointing the server at it). Every entry is checked
   before a byte is written: the manifest lists it, it is a plain file (no folder, link or encrypted entry), its name
   is unique even ignoring case, its size is the manifest's, and the whole fits in the free space.
2. **Unpacked.** Each entry is written below ``.restore/stage/<id>/data/`` into a new file — never through a link,
   never over another — and its SHA-256 compared with the manifest's as it is written.
3. **The revision decides**, the manifest's, which the copy's ``alembic_version`` must confirm. Unknown to this
   LibreFolio's migrations, so newer, most likely: refused, update LibreFolio first — never a downgrade. The app's
   head: restored as it is. Older: ``alembic upgrade head`` on the copy, in a process of its own. The post-migration
   fixes then run on the copy in either case, as at every start.
4. **Checked before and after.** Before the upgrade, the copy passes its integrity check and holds exactly the rows its
   manifest counted, and every text it holds is UTF-8 (B-49: the server's reads would fail on one that is not). After,
   it passes its integrity check again, at the head; its rows and foreign keys are compared with those before: a
   migration may change data, so a difference is a warning, not a refusal.
5. **Administrators** (decision 40): after a restore, one signs in with an account of the backup, with its password
   of then; the report names the copy's active administrators. With none, the restore is blocked.
6. **Plugin secrets** (decision 39): the instance keeps its own key. The copy's secrets are re-encrypted with it from
   the archive's key, when the archive carries one; the others stay as they are, counted: «set but unreadable, enter it
   again». This instance's key is derived only when the copy holds secrets.
7. **Currency codes** (E-19b1): stored currency values that are not ISO 4217 codes — a number or a name an earlier
   version saved, such as ``978`` or ``EURO`` — are a warning: an edit of their rows is refused until they are
   corrected. Read on the upgraded copy by E-19a's audit; a read that fails only leaves the warning out.

The report is written beside the copy (``report.json``). A confirmed restore (lot B3) moves the copy into place; the
copy of an archive nobody confirms is removed after ``STAGE_LIFETIME``.
"""

from __future__ import annotations

import hashlib
import os
import re
import secrets
import shutil
import sqlite3
import stat
import subprocess
import sys
import unicodedata
import zipfile
import zlib
from collections import Counter
from collections.abc import Callable, Iterable
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from backend.app.config import PROJECT_ROOT, get_version
from backend.app.db.post_migration import run_post_migration_fixes
from backend.app.logging_config import get_logger
from backend.app.services.platform.instance_backup.archive import INSTANCE_KEY_MAX_BYTES, read_instance_key, read_manifest
from backend.app.services.platform.instance_backup.envelope import EnvelopeError, EnvelopeKey, decrypt_file, is_envelope
from backend.app.services.platform.instance_backup.jobs import _RunLock, out_of_space
from backend.app.services.platform.instance_backup.manifest import BackupManifest, BackupOrigin, ManifestError, ManifestFile
from backend.app.services.platform.instance_backup.paths import (
    DATABASE_ENTRY,
    INSTANCE_KEY_ENTRY,
    MANIFEST_ENTRY,
    STAGE_DATA_FOLDER,
    STAGE_DECRYPTED_ARCHIVE,
    STAGE_LOCK_FILE,
    STAGE_REPORT_FILE,
    BackupPathError,
    NotRegularFileError,
    ensure_private_dir,
    is_plain_dir,
    read_regular_file,
    restore_dir,
    stage_dir,
    stages_dir,
)
from backend.app.services.platform.instance_backup.snapshot import DatabaseDescription, _identifier, describe_database
from backend.app.services.platform.instance_backup.totals import TotalsComparison, TotalsDifference, TotalsStatus, compare_totals, ledger_totals_of
from backend.app.services.platform.instance_key import INSTANCE_KEY_MIN_LENGTH, InstanceKeyError, derive_key_from
from backend.app.services.platform.stored_currencies import find_stored_currency_findings
from backend.app.services.plugin_settings.crypto import SUBKEY_LENGTH, SUBKEY_PURPOSE, count_unreadable_secrets, rekey_plugin_secrets, settings_subkey

logger = get_logger(__name__)

ALEMBIC_INI = PROJECT_ROOT / "backend" / "alembic.ini"
#: How long a checked archive waits for its confirmation before its copy is removed.
STAGE_LIFETIME = timedelta(hours=24)
#: An archive LibreFolio writes holds far fewer entries: a hundred thousand files make a 15 MB manifest.
MAX_ENTRIES = 500_000
#: An upgrade of the copy that has not ended after an hour is stopped, and the check fails.
UPGRADE_TIMEOUT_SECONDS = 3600
#: Room kept free beyond the copy and its upgrade.
_SPACE_MARGIN = 64 * 1024 * 1024
_CHUNK = 1024 * 1024
_ZIP_MAGIC = b"PK\x03\x04"
#: Where a POSIX tar names its format: the sealed nightly backup of a hosting panel is one (L3).
_USTAR_MAGIC_AT = 257
_USTAR_MAGIC = b"ustar"
_ZIP_READ_ERRORS = (zipfile.BadZipFile, zlib.error, EOFError)

StagePhase = Literal["decrypting", "checking", "unpacking", "upgrading", "verifying"]
StageProgress = Callable[[StagePhase, int, int], None]
#: What a restore does to the backup's database: nothing (it is at this LibreFolio's head), or an upgrade.
RevisionAction = Literal["same", "upgrade"]


class StagingError(RuntimeError):
    """The archive cannot be restored, or not checked: ``code`` says why, in a stable word. The message holds no path."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class StagingBusyError(RuntimeError):
    """Another archive is being checked in this data directory."""


class TableRows(BaseModel):
    """The rows of one table in the copy, before and after its upgrade; ``None`` where the table does not exist."""

    model_config = ConfigDict(frozen=True)

    before: int | None
    after: int | None


class AppliedMigration(BaseModel):
    """A migration the upgrade of the copy applied: its revision, and the first line of its description."""

    model_config = ConfigDict(frozen=True)

    revision: str
    message: str


class SecretCounts(BaseModel):
    """Saved plugin secrets, by scope: the instance's settings and the users' own."""

    model_config = ConfigDict(frozen=True)

    system: int = Field(default=0, ge=0)
    user: int = Field(default=0, ge=0)


class StagedBackup(BaseModel):
    """What the manifest says of the backup."""

    model_config = ConfigDict(frozen=True)

    created_at: datetime
    app_version: str
    origin: BackupOrigin
    alembic_revision: str


class OwnerCandidate(BaseModel):
    """An account of the copy the owner may choose as theirs after the restore (B5-1): an active administrator, or the
    account whose address is the owner's. Read from the copy, never trusted further: ``apply.confirm_restore`` checks the
    choice against this list."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    user_id: int
    username: str
    email: str | None
    is_superuser: bool
    is_active: bool


class StagingReport(BaseModel):
    """What a restore of the checked archive would do: the report a confirmation shows, kept beside the copy.

    ``warnings`` and ``blockers`` are stable codes. A warning is shown and lets the restore go on: ``rows_changed`` (the
    upgrade changed the rows of a table), ``foreign_key_violations`` (the backup's database has broken references, kept
    as they are), ``foreign_key_violations_added`` (the upgrade added some), ``control_totals_changed`` (the ledger's
    control totals of the copy differ from those the backup recorded: ``control_totals_differences``),
    ``control_totals_unreadable`` (the copy's could not be read), ``non_iso_currencies`` (the copy holds stored currency
    values that are not ISO 4217 codes, which an edit of their rows refuses until they are corrected: ``./dev.py db
    currencies`` lists them; E-19b1), and ``credentials_from_backup``, always, last (after a restore one signs in with
    the backup's credentials, and every session open now ends; L3). A blocker forbids it: ``no_administrator``.
    ``control_totals``: ``same``, ``changed``, ``absent`` (not in the archive), ``other_version`` (another version of
    J's method: not compared) or ``unreadable``. ``encrypted``: a secure backup (lot B4). ``secrets_rekeyed``: the
    plugin secrets re-encrypted with this instance's key; ``secrets_unreadable``: those that stay unreadable.
    """

    model_config = ConfigDict(extra="ignore", frozen=True)

    stage_id: str
    staged_at: datetime
    expires_at: datetime
    backup: StagedBackup
    app_version: str
    head_revision: str
    action: RevisionAction
    migrations: list[AppliedMigration]
    post_migration_fixes: list[str]
    tables: dict[str, TableRows]
    foreign_key_violations_before: int = Field(ge=0)
    foreign_key_violations_after: int = Field(ge=0)
    files: int = Field(ge=0)
    files_size: int = Field(ge=0)
    database_size: int = Field(ge=0)
    instance_key_included: bool
    #: Lot B4; defaults, so that a report written before still reads.
    encrypted: bool = False
    secrets_rekeyed: int = Field(default=0, ge=0)
    secrets_unreadable: SecretCounts = SecretCounts()
    administrators: list[str]
    #: B5-1: the accounts the owner may choose; a report written before reads none. The owner's address the check used
    #: (the confirmation refuses a report whose address is not the current one), and what in the copy would let a
    #: crafted backup defeat the owner's assignment: ``duplicate_email``, ``duplicate_username``,
    #: ``address_is_a_username``.
    owner_candidates: list[OwnerCandidate] = []
    owner_email_checked: str | None = None
    owner_conflicts: list[str] = []
    #: Defaults, so that a report written before lot B-13 still reads.
    control_totals: TotalsStatus = "absent"
    control_totals_differences: list[TotalsDifference] = []
    control_totals_differences_count: int = Field(default=0, ge=0)
    warnings: list[str]
    blockers: list[str]

    @property
    def restorable(self) -> bool:
        return not self.blockers


def new_stage_id() -> str:
    """A new stage id: 32 lowercase hexadecimal digits, as the backup jobs make theirs."""
    return uuid4().hex


def stage_archive(archive_path: Path, data_dir: Path, *, stage_id: str | None = None, progress: StageProgress | None = None, lock: _RunLock | None = None, key: EnvelopeKey | None = None, instance_key: str | None = None, max_unpacked: int | None = None) -> StagingReport:
    """Check the archive at ``archive_path`` for a restore into ``data_dir``, on a copy, and return the report.

    ``key``: the key of a secure backup (``envelope.unlock``); without it, such an archive is refused
    (``password_required``). ``instance_key``: the instance key of the installation the archive came from, for an
    archive that does not carry its own (``dev.py backup restore --instance-key-file``, B-18): its saved plugin secrets
    are re-encrypted from it with this instance's key; the archive's own key wins. Not a key: ``StagingError``
    ``instance_key_invalid``, before anything is created, its text in no message. ``max_unpacked``: the most bytes the
    archive may unpack to (``LIBREFOLIO_BACKUP_MAX_RESTORE_MB``, B-35; ``None``: no limit); above it, ``StagingError``
    ``unpacked_too_large`` before anything is unpacked.

    The copy and its report stay in ``.restore/stage/<stage id>/``; on any refusal nothing of them is left. One archive
    is checked at a time: ``StagingBusyError`` while another is. ``StagingError`` says why an archive is refused; an
    ``sqlite3`` error while the copy's database is read or checked is ``database_damaged`` (B-43), never raised as such.
    The one read that refuses nothing, of the copy's stored currency codes (E-19b1), only warns: when it fails, the
    warning is left out and the check goes on.
    ``lock``: the lock of the checks, already held by the caller (``restore_jobs``, which takes it in the request and
    checks in a thread). The caller keeps it and releases it itself, once the check's end is recorded: until then, a
    reader must find it held. Without one, the lock is taken and released here.
    """
    _refuse_unusable_instance_key(instance_key)
    stage_id = stage_id or new_stage_id()
    owned = lock is None
    if owned:
        ensure_private_dir(stages_dir(data_dir), data_dir)
        lock = _RunLock(stages_dir(data_dir) / STAGE_LOCK_FILE)
        if not lock.try_acquire():
            raise StagingBusyError("Another archive is being checked")
    try:
        root = stage_dir(data_dir, stage_id)
        root.mkdir(mode=0o700)
        try:
            report = _stage(archive_path, root, stage_id, progress if progress is not None else _no_progress, key, instance_key, max_unpacked)
        except BaseException:
            shutil.rmtree(root, ignore_errors=True)
            raise
    finally:
        if owned:
            lock.release()
    logger.info("Backup archive checked for a restore", stage_id=stage_id, action=report.action, migrations=len(report.migrations), restorable=report.restorable, warnings=report.warnings)
    return report


def read_report(data_dir: Path, stage_id: str) -> StagingReport:
    """The report of a checked archive. ``FileNotFoundError`` when there is none to read: never checked, refused or
    removed, a content that is no report, or a folder, a link, a special file or a file it may not read in its place
    (B-53); any other ``OSError``, a transient one, as it came."""
    path = stage_dir(data_dir, stage_id) / STAGE_REPORT_FILE
    try:
        raw = read_regular_file(path)
    except (NotADirectoryError, IsADirectoryError, PermissionError, NotRegularFileError):
        raise FileNotFoundError(f"No readable report for stage {stage_id}") from None
    try:
        return StagingReport.model_validate_json(raw)
    except ValidationError:
        raise FileNotFoundError(f"No readable report for stage {stage_id}") from None


def remove_stage(data_dir: Path, stage_id: str) -> None:
    """Remove the copy of a checked archive and its report; nothing when there is none. A link is removed, never followed,
    and nothing is removed while ``.restore`` or its ``stage`` folder is not a plain folder."""
    root = stage_dir(data_dir, stage_id)
    if not (is_plain_dir(restore_dir(data_dir)) and is_plain_dir(stages_dir(data_dir))):
        return
    try:
        mode = root.lstat().st_mode
    except FileNotFoundError:
        return
    if stat.S_ISDIR(mode):
        shutil.rmtree(root, ignore_errors=True)
    else:
        root.unlink(missing_ok=True)


# =============================================================================
# The steps
# =============================================================================


def _no_progress(phase: StagePhase, done: int, total: int) -> None:
    return None


def _refuse_unusable_instance_key(instance_key: str | None) -> None:
    """An instance key given for the restore (B-18) that is not one is refused before anything is created; never its
    text in a message."""
    if instance_key is None:
        return
    try:
        derive_key_from(instance_key, SUBKEY_PURPOSE, SUBKEY_LENGTH)
    except InstanceKeyError:
        raise StagingError("instance_key_invalid", f"The instance key given is too short: an instance key has at least {INSTANCE_KEY_MIN_LENGTH} characters") from None


def _stage(archive_path: Path, root: Path, stage_id: str, progress: StageProgress, key: EnvelopeKey | None = None, instance_key: str | None = None, max_unpacked: int | None = None) -> StagingReport:
    data_root = root / STAGE_DATA_FOLDER
    encrypted = is_envelope(archive_path)
    if encrypted:
        archive_path = _decrypt(archive_path, root, key, progress)
    progress("checking", 0, 0)
    with _open_archive(archive_path) as archive:
        manifest = _read_manifest(archive)
        entries = _checked_entries(archive, manifest)
        _check_unpacked_limit(manifest, max_unpacked)
        _check_space(root, manifest)
        # The archive's own key wins over one given for the restore (B-18, decision D1).
        archive_key = _archive_instance_key(archive, manifest) if INSTANCE_KEY_ENTRY in entries else instance_key
        _unpack(archive, manifest, entries, root, data_root, progress)
    if encrypted:
        archive_path.unlink(missing_ok=True)

    database = data_root / DATABASE_ENTRY
    try:
        _refuse_foreign_objects(database)
        before = describe_database(database)
        _check_against_manifest(before, manifest)
        _refuse_undecodable_text(database)
        action, migrations, head = _revision_plan(manifest.alembic_revision)
        if action == "upgrade":
            progress("upgrading", 0, len(migrations))
            _upgrade(database)
            progress("upgrading", len(migrations), len(migrations))
        fixes = _post_migration_fixes(database, data_root)
        rekeyed, unreadable = _plugin_secrets(database, archive_key)

        progress("verifying", 0, 0)
        after = describe_database(database)
        if after.integrity_check != "ok":
            raise StagingError("database_damaged", "The copy of the backup's database fails its integrity check after its upgrade")
        if after.alembic_revision != head:
            raise StagingError("upgrade_failed", "The copy of the backup's database did not reach this LibreFolio's revision")
        totals = compare_totals(manifest.database.control_totals, ledger_totals_of(database))
        administrators = _administrators(database)
        owner_email_checked, owner_candidates, owner_conflicts = _owner_check(database)
    except sqlite3.ProgrammingError:
        raise
    except sqlite3.DatabaseError as exc:
        # What reads or checks the copy's database failed (B-43): its schema may call a function this reader lacks, in
        # an index or a generated column (``integrity_check`` fails even read-only) or in a CHECK (the first
        # read-write check: the post-migration fixes), or the file is no database. The message may name the
        # archive's function, archive text: the class and SQLite's error name only (B-28).
        logger.warning("A backup's database could not be read or checked on its copy", error=type(exc).__name__, sqlite_error=getattr(exc, "sqlite_errorname", None))
        raise StagingError("database_damaged", "The backup's database cannot be read or checked: it cannot be restored") from None
    # Outside the wrap above: this read refuses nothing, so its failure must never become database_damaged (E-19b1)
    non_iso_currencies = _holds_non_iso_currencies(database, stage_id)
    report = _report(stage_id, manifest, before, after, action, migrations, head, fixes, administrators, totals, encrypted=encrypted, secrets_rekeyed=rekeyed, secrets_unreadable=unreadable, non_iso_currencies=non_iso_currencies)
    report = report.model_copy(update={"owner_candidates": owner_candidates, "owner_email_checked": owner_email_checked, "owner_conflicts": owner_conflicts})
    _write_report(root, report)
    return report


def _decrypt(envelope: Path, root: Path, key: EnvelopeKey | None, progress: StageProgress) -> Path:
    """Decrypt a secure backup beside its copy, once the space for it is checked; the archive it holds."""
    if key is None:
        raise StagingError("password_required", "The backup is protected by a password")
    size = envelope.stat().st_size
    if shutil.disk_usage(root).free < size + _SPACE_MARGIN:
        raise StagingError("no_space", f"Not enough free space to check the archive: {size + _SPACE_MARGIN} bytes are needed")
    target = root / STAGE_DECRYPTED_ARCHIVE
    progress("decrypting", 0, size)
    try:
        decrypt_file(envelope, target, key, progress=lambda done, total: progress("decrypting", done, total))
    except EnvelopeError:
        # With its key given, an envelope can only fail here as damaged: a tag, a cut, a header changed since.
        raise StagingError("envelope_damaged", "The secure backup is damaged or was changed") from None
    except OSError as exc:
        if out_of_space(exc):
            raise StagingError("no_space", "Not enough free space to check the archive") from None
        logger.error("A secure backup could not be decrypted for a check", error=f"{type(exc).__name__}: {exc.strerror or exc}")
        raise StagingError("stage_failed", "The archive could not be decrypted: the log of the server has the details") from None
    return target


def _open_archive(path: Path) -> zipfile.ZipFile:
    """The archive, opened: a zip, by its first bytes as by its directory. A POSIX tar is the sealed nightly backup of
    a hosting panel (L3), whose password only the provider's key opens: ``sealed_backup_needs_key``, said apart."""
    try:
        with path.open("rb") as handle:
            head = handle.read(_USTAR_MAGIC_AT + len(_USTAR_MAGIC))
    except OSError:
        raise StagingError("archive_unreadable", "The archive cannot be read") from None
    if head[_USTAR_MAGIC_AT:] == _USTAR_MAGIC:
        raise StagingError("sealed_backup_needs_key", "The file is a sealed backup of a hosting panel: its password is encrypted for the provider's key")
    if head[: len(_ZIP_MAGIC)] != _ZIP_MAGIC:
        raise StagingError("not_a_backup", "The file is not a LibreFolio backup")
    try:
        return zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError):
        raise StagingError("archive_damaged", "The archive is damaged") from None


def _read_manifest(archive: zipfile.ZipFile) -> BackupManifest:
    """The manifest. Without one, or with one LibreFolio did not write, the archive is not a LibreFolio backup."""
    try:
        return read_manifest(archive)
    except ManifestError as exc:
        code = "not_a_backup" if exc.code in ("manifest_missing", "manifest_unknown_format") else exc.code
        raise StagingError(code, str(exc)) from None


def _checked_entries(archive: zipfile.ZipFile, manifest: BackupManifest) -> dict[str, zipfile.ZipInfo]:
    """Every entry of the archive, checked against the manifest before anything is written; by path.

    The instance key is expected when the manifest announces it (lot B4): checked here, read later, never unpacked.
    """
    infos = archive.infolist()
    if len(infos) > MAX_ENTRIES + 1:
        raise StagingError("too_many_entries", f"The archive holds more than {MAX_ENTRIES} entries")
    if _repeated(info.filename for info in infos) or _repeated(entry.path for entry in manifest.files) or _nested(entry.path for entry in manifest.files):
        raise StagingError("duplicate_entry", "An entry appears twice in the archive, with only its case changed, or as the folder of another")
    expected = {entry.path: entry for entry in manifest.files}
    key_expected = manifest.instance_key.included
    entries: dict[str, zipfile.ZipInfo] = {}
    for info in infos:
        if info.filename == MANIFEST_ENTRY:
            continue
        if key_expected and info.filename == INSTANCE_KEY_ENTRY:
            _check_key_entry(info)
            entries[info.filename] = info
            continue
        entry = expected.get(info.filename)
        if entry is None:
            raise StagingError("unexpected_entry", "The archive holds an entry its manifest does not list")
        _check_entry(info, entry)
        entries[info.filename] = info
    missing = len(expected) + key_expected - len(entries)
    if missing:
        raise StagingError("missing_entry", f"{missing} entr{'y' if missing == 1 else 'ies'} of the manifest missing from the archive")
    return entries


def _name_key(name: str) -> str:
    """A name as a file system that ignores case, or the Unicode form of a letter, may see it."""
    return unicodedata.normalize("NFC", name).casefold()


def _repeated(names: Iterable[str]) -> bool:
    """Whether a name comes twice, its case and Unicode form ignored: where they are, the second would overwrite the first."""
    return max(Counter(_name_key(name) for name in names).values(), default=0) > 1


def _nested(paths: Iterable[str]) -> bool:
    """Whether a path is also the folder of another (``a/x`` and ``a/x/y``): unpacked, one would stand where the other's
    folder must."""
    keys = {_name_key(path) for path in paths}
    return any("/".join(parts[:depth]) in keys for parts in (key.split("/") for key in keys) for depth in range(1, len(parts)))


def _check_entry(info: zipfile.ZipInfo, entry: ManifestFile) -> None:
    """One entry is a plain file, stored or deflated, unencrypted, of the size its manifest gives."""
    mode = info.external_attr >> 16
    if info.is_dir() or (mode and not stat.S_ISREG(mode)):
        raise StagingError("not_a_file", "An entry of the archive is not a plain file: a folder or a link")
    if info.flag_bits & 0x1:
        raise StagingError("encrypted_entry", "An entry of the archive is encrypted")
    if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
        raise StagingError("unsupported_entry", "An entry of the archive uses a compression LibreFolio does not write")
    if info.file_size != entry.size:
        raise StagingError("checksum_mismatch", "An entry of the archive differs from its manifest: the archive is damaged or was changed")


def _check_key_entry(info: zipfile.ZipInfo) -> None:
    """The instance key entry is a small plain file, stored or deflated, unencrypted."""
    mode = info.external_attr >> 16
    if info.is_dir() or (mode and not stat.S_ISREG(mode)):
        raise StagingError("not_a_file", "An entry of the archive is not a plain file: a folder or a link")
    if info.flag_bits & 0x1:
        raise StagingError("encrypted_entry", "An entry of the archive is encrypted")
    if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
        raise StagingError("unsupported_entry", "An entry of the archive uses a compression LibreFolio does not write")
    if info.file_size > INSTANCE_KEY_MAX_BYTES:
        raise StagingError("checksum_mismatch", "The instance key of the archive differs from its manifest: the archive is damaged or was changed")


def _archive_instance_key(archive: zipfile.ZipFile, manifest: BackupManifest) -> str:
    """The text of the instance key the archive carries, once it matches its manifest."""
    key = read_instance_key(archive, manifest.instance_key.sha256)
    if key is None:
        raise StagingError("checksum_mismatch", "The instance key of the archive differs from its manifest: the archive is damaged or was changed")
    return key


def space_needed(manifest: BackupManifest) -> int:
    """What a check needs free: every entry unpacked, room for the upgrade to rewrite the database, a margin."""
    return sum(entry.size for entry in manifest.files) + 2 * manifest.files[0].size + _SPACE_MARGIN


def _check_unpacked_limit(manifest: BackupManifest, max_unpacked: int | None) -> None:
    """Refuse an archive that unpacks to more than a restore accepts (B-35): the total its manifest declares, which
    ``_checked_entries`` matched entry by entry with the zip's own sizes, and past which the unpacking never reads."""
    if max_unpacked is not None and sum(entry.size for entry in manifest.files) > max_unpacked:
        raise StagingError("unpacked_too_large", "Unpacked, the archive is larger than this LibreFolio accepts for a restore")


def _check_space(root: Path, manifest: BackupManifest) -> None:
    needed = space_needed(manifest)
    if shutil.disk_usage(root).free < needed:
        raise StagingError("no_space", f"Not enough free space to check the archive: {needed} bytes are needed")


def _unpack(archive: zipfile.ZipFile, manifest: BackupManifest, entries: dict[str, zipfile.ZipInfo], root: Path, data_root: Path, progress: StageProgress) -> None:
    """Write every entry below ``data_root``, as it is in a data directory, checking each against the manifest."""
    total = sum(entry.size for entry in manifest.files)
    done = 0
    progress("unpacking", done, total)
    for entry in manifest.files:
        target = data_root.joinpath(*entry.path.split("/"))
        try:
            ensure_private_dir(target.parent, root)
        except BackupPathError:
            # Only the archive put anything below the copy: a file stands where another entry's folder must be.
            raise StagingError("duplicate_entry", "An entry of the archive stands where the folder of another must be") from None
        _write_entry(archive, entries[entry.path], entry, target)
        done += entry.size
        progress("unpacking", done, total)


def _write_entry(archive: zipfile.ZipFile, info: zipfile.ZipInfo, entry: ManifestFile, target: Path) -> None:
    """Write one entry into the new file ``target``, never reading it beyond its manifest size; compare its SHA-256."""
    digest = hashlib.sha256()
    size = 0
    try:
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(fd, "wb") as out, archive.open(info) as source:
            while size <= entry.size and (chunk := source.read(min(_CHUNK, entry.size + 1 - size))):
                out.write(chunk)
                digest.update(chunk)
                size += len(chunk)
    except FileExistsError:
        raise StagingError("duplicate_entry", "An entry appears twice in the archive") from None
    except _ZIP_READ_ERRORS:
        raise StagingError("archive_damaged", "An entry of the archive cannot be read: the archive is damaged") from None
    except OSError as exc:
        if out_of_space(exc):
            raise StagingError("no_space", "Not enough free space to check the archive") from None
        logger.error("A restore copy could not be written", error=f"{type(exc).__name__}: {exc.strerror or exc}")
        raise StagingError("stage_failed", "The copy of the archive could not be written: the log of the server has the details") from None
    if size != entry.size or digest.hexdigest() != entry.sha256:
        raise StagingError("checksum_mismatch", "An entry of the archive differs from its manifest: the archive is damaged or was changed")


def _check_against_manifest(before: DatabaseDescription, manifest: BackupManifest) -> None:
    """The copy's database, before any upgrade, is the one the manifest describes, and an intact one."""
    if before.integrity_check != "ok":
        raise StagingError("database_damaged", "The backup's database fails its integrity check: it cannot be restored")
    if before.alembic_revision != manifest.alembic_revision or before.tables != manifest.database.tables:
        raise StagingError("manifest_mismatch", "The backup's database is not the one its manifest describes")


def _revision_plan(revision: str | None) -> tuple[RevisionAction, list[AppliedMigration], str]:
    """What the backup's revision asks for: nothing, or the migrations from it to the head, oldest first; and the head."""
    from alembic.config import Config  # noqa: PLC0415 — keep alembic out of the app's import scope
    from alembic.script import ScriptDirectory  # noqa: PLC0415

    try:
        script = ScriptDirectory.from_config(Config(str(ALEMBIC_INI)))
        head = script.get_current_head()
        history = list(script.walk_revisions("base", head)) if head else []
    except Exception as exc:
        logger.error("The migration scripts cannot be read for a restore", error=str(exc))
        raise StagingError("head_unknown", "This LibreFolio's migration scripts cannot be read") from None
    if head is None:
        raise StagingError("head_unknown", "This LibreFolio's migration scripts cannot be read")
    if revision is None:
        raise StagingError("revision_missing", "The backup's database records no revision")
    if revision == head:
        return "same", [], head
    newer: list[AppliedMigration] = []
    for script_revision in history:
        if script_revision.revision == revision:
            return "upgrade", list(reversed(newer)), head
        newer.append(AppliedMigration(revision=script_revision.revision, message=_first_line(script_revision.doc) or script_revision.revision))
    raise StagingError("revision_unknown", "The backup comes from a newer LibreFolio, or not from this one: update LibreFolio first, then restore it")


def _first_line(text: str | None) -> str:
    return next((line.strip() for line in (text or "").splitlines() if line.strip()), "")


def _upgrade(database: Path) -> None:
    """``alembic upgrade head`` on the copy, in a process of its own: the app's own engine never sees the copy."""
    command = [sys.executable, "-m", "alembic", "-c", str(ALEMBIC_INI), "-x", f"sqlalchemy.url=sqlite:///{database.resolve()}", "upgrade", "head"]
    try:
        result = subprocess.run(command, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=UPGRADE_TIMEOUT_SECONDS, check=False)
    except subprocess.TimeoutExpired:
        logger.error("The upgrade of a restore copy did not end in time", seconds=UPGRADE_TIMEOUT_SECONDS)
        raise StagingError("upgrade_failed", "The upgrade of the copy did not end in time") from None
    except OSError as exc:
        logger.error("The upgrade of a restore copy could not start", error=str(exc))
        raise StagingError("upgrade_failed", "The upgrade of the copy could not start") from None
    if result.returncode != 0:
        logger.error("The upgrade of a restore copy failed", returncode=result.returncode, stderr=result.stderr[-4000:])
        raise StagingError("upgrade_failed", "The upgrade of the copy failed: the log of the server has the details")


def _post_migration_fixes(database: Path, data_root: Path) -> list[str]:
    """The post-migration fixes, on the copy, as at every start; the ids of those that changed something."""
    report = run_post_migration_fixes(database, data_root)
    if report.failed:
        logger.error("A post-migration fix failed on a restore copy", errors=report.errors)
        raise StagingError("post_migration_failed", "A post-migration fix failed on the copy: the log of the server has the details")
    return sorted(fix_id for fix_id, outcome in report.outcomes.items() if outcome == "applied")


#: A word of an SQL statement, or what comes between two: spaces and comments are skipped, anything else ends the words.
_SQL_TOKEN = re.compile(r"(?P<skip>\s+|--[^\n]*|/\*.*?(?:\*/|\Z))|(?P<word>[A-Za-z_]+)|(?P<other>.)", re.S)
#: The kinds of a schema object LibreFolio's migrations create: tables and their indexes, never anything else (B-28).
_OWN_KINDS = ("table", "index")


def _leading_words(sql: str, count: int) -> list[str]:
    """The first ``count`` words of an SQL statement, upper-cased, past spaces and comments; fewer when something else
    comes first."""
    words: list[str] = []
    for match in _SQL_TOKEN.finditer(sql):
        if match.lastgroup == "skip":
            continue
        if match.lastgroup != "word":
            break
        words.append(match.group("word").upper())
        if len(words) == count:
            break
    return words


def _schema_object_kind(sql: object) -> str:
    """What an object of ``sqlite_master`` is, read from its SQL as SQLite builds it, whatever its row's ``type`` says:
    ``table``, ``index`` (SQL NULL: one of SQLite's own automatic indexes), or ``trigger``, ``view``, ``virtual``,
    ``other``."""
    if sql is None:
        return "index"
    words = _leading_words(sql, 3) if isinstance(sql, str) else []
    if words[:2] == ["CREATE", "TABLE"]:
        return "table"
    if words[:2] == ["CREATE", "INDEX"] or words == ["CREATE", "UNIQUE", "INDEX"]:
        return "index"
    second = words[1] if len(words) > 1 and words[0] == "CREATE" else ""
    return {"TRIGGER": "trigger", "VIEW": "view", "VIRTUAL": "virtual"}.get(second, "other")


def _refuse_foreign_objects(database: Path) -> None:
    """Refuse a database holding a trigger, a view or a virtual table (lot B-28): LibreFolio never creates one, and its SQL
    would run as soon as the check writes or reads the copy, and in the server after a restore, a recursive one for
    ever. Read from ``sqlite_master`` alone, read only, by each object's SQL; nothing of the archive runs.

    The schema is read as the server's connections read it: ``trusted_schema`` off, with the functions SQLAlchemy
    registers there as stand-ins (``_register_server_functions``). A schema that calls one in an index or a generated
    column cannot be read there since H-51, and every connection of the server would fail: it cannot be read here
    either. A schema SQLite refuses to read is ``database_damaged``, as ``_stage`` answers every ``sqlite3`` error of the
    copy's database (B-43)."""
    with closing(sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True)) as conn:
        conn.execute("PRAGMA trusted_schema=OFF")
        _register_server_functions(conn)
        rows = conn.execute("SELECT sql FROM sqlite_master").fetchall()
    foreign = Counter(kind for (sql,) in rows if (kind := _schema_object_kind(sql)) not in _OWN_KINDS)
    if foreign:
        # The kinds only: the names and the SQL are the archive's text.
        logger.warning("A backup's database holds schema objects LibreFolio never creates", objects=sum(foreign.values()), kinds=sorted(foreign))
        raise StagingError("database_foreign_objects", "The backup's database holds triggers, views or other objects LibreFolio never creates: it cannot be restored")


#: The Python functions SQLAlchemy's SQLite dialect registers on every connection of the server, deterministic (SQLAlchemy
#: 2.0.52, ``SQLiteDialect_pysqlite.on_connect()``): name and number of arguments. ``floor`` replaces SQLite's own.
_SERVER_FUNCTIONS = (("regexp", 2), ("floor", 1))


def _register_server_functions(conn: sqlite3.Connection) -> None:
    """Stand-ins for the server's own functions, registered as SQLAlchemy registers them and never run: with
    ``trusted_schema`` off, a schema that calls one in an index or a generated column cannot be read, as on the
    server's connections since H-51 (B-43)."""
    for name, arguments in _SERVER_FUNCTIONS:
        conn.create_function(name, arguments, _stand_in, deterministic=True)


def _stand_in(*_arguments: object) -> None:
    """What a stand-in of the server's functions answers, were it ever called: nothing. Only the schema could call it,
    and with ``trusted_schema`` off SQLite refuses that before any call."""
    return None


#: The rows of a table one query of the text scan reads (B-49): their text values, concatenated by SQLite, come back as
#: one string per column. 200 000 rows of the largest tables of a 488 MB database are about 10 MB of text.
_TEXT_SCAN_ROWS = 200_000
#: The names of a table's rowid. A column may take any of them, and that name is then the column's.
_ROWID_NAMES = ("rowid", "_rowid_", "oid")
_LOWEST_ROWID = -(2**63)
_HIGHEST_ROWID = 2**63 - 1


def _strict_text(value: bytes) -> str:
    """A text value as the server's driver reads it, or ``UnicodeDecodeError`` (B-49)."""
    return value.decode("utf-8")


def _refuse_undecodable_text(database: Path) -> None:
    """Refuse a database holding text that is not UTF-8 (lot B-49). The server's driver raises on such a value and the
    whole read fails, not the row: after a restore every list holding it would fail, and no page could correct what it
    cannot read. LibreFolio writes UTF-8 only.

    Every table but SQLite's own, unknown ones too; every column, generated ones included (``table_xinfo``), its values
    by storage class (``typeof = 'text'``: dates and timestamps are text in DATE and DATETIME columns). Run before the upgrade, so no migration meets such a text
    first. Read only, ``trusted_schema`` off first (B-37), each text through a strict ``text_factory``. The log has the
    number of tables, never a text, a name or a path: they are the archive's."""
    with closing(sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True)) as conn:
        conn.execute("PRAGMA trusted_schema=OFF")
        tables = conn.execute("SELECT name, wr FROM pragma_table_list WHERE schema = 'main' AND type = 'table' AND name NOT LIKE 'sqlite\\_%' ESCAPE '\\'").fetchall()
        conn.text_factory = _strict_text
        undecodable = sum(1 for name, without_rowid in tables if _holds_undecodable_text(conn, name, bool(without_rowid)))
    if undecodable:
        logger.warning("A backup's database holds text that is not UTF-8", tables=undecodable)
        raise StagingError("database_damaged", "The backup's database holds text that is not UTF-8: it cannot be restored")


def _holds_undecodable_text(conn: sqlite3.Connection, table: str, without_rowid: bool) -> bool:
    """Whether a text value of ``table`` is not UTF-8. Read by keyset windows of its rowid, ``_TEXT_SCAN_ROWS`` rows a
    query, each column's text values joined by SQLite with a comma and decoded once: negative or sparse rowids cost
    nothing, and the comma, a byte of its own, never completes a character split over two values. A table without a
    rowid, or whose columns take all its names, is read row by row instead, in constant memory, and so is the rest of a
    table whose window SQLite cannot join (texts past its length limit, ``DataError``)."""
    try:
        names = [name for (name,) in conn.execute("SELECT name FROM pragma_table_xinfo(?)", (table,))]
        texts = ", ".join(f"CASE WHEN typeof({_identifier(name)}) = 'text' THEN {_identifier(name)} END" for name in names)
        if not names:
            return False
        rowid = None if without_rowid else next((candidate for candidate in _ROWID_NAMES if candidate not in {name.lower() for name in names}), None)
        if rowid is None:
            _read_every_row(conn.execute(f"SELECT {texts} FROM {_identifier(table)}"))
            return False
        window = ", ".join(f"CASE WHEN typeof({_identifier(name)}) = 'text' THEN {_identifier(name)} END AS t{index}" for index, name in enumerate(names))
        joined = ", ".join(f"group_concat(t{index}, ',')" for index in range(len(names)))
        query = f"SELECT count(*), max(k), {joined} FROM (SELECT {rowid} AS k, {window} FROM {_identifier(table)} WHERE {rowid} >= ? ORDER BY {rowid} LIMIT ?)"
        low = _LOWEST_ROWID
        while True:
            try:
                rows, top, *_joined = conn.execute(query, (low, _TEXT_SCAN_ROWS)).fetchone()
            except sqlite3.DataError:
                _read_every_row(conn.execute(f"SELECT {texts} FROM {_identifier(table)} WHERE {rowid} >= ? ORDER BY {rowid}", (low,)))
                return False
            if rows < _TEXT_SCAN_ROWS or top >= _HIGHEST_ROWID:
                return False
            low = top + 1
    except UnicodeDecodeError:
        return True


def _read_every_row(cursor: sqlite3.Cursor) -> None:
    """Fetch every row of ``cursor``, a few at a time: its text values pass through the connection's ``text_factory``."""
    while cursor.fetchmany(1000):
        pass


def _plugin_secrets(database: Path, archive_key: str | None) -> tuple[int, SecretCounts]:
    """The copy's plugin secrets after its upgrade: how many were re-encrypted with this instance's key, how many stay
    unreadable. X's functions, on a connection of the copy; this instance's key is derived only when there are secrets."""
    with closing(sqlite3.connect(database)) as conn:
        conn.execute("PRAGMA trusted_schema=OFF")
        # A random key reads no secret: what it counts as unreadable is every secret the copy holds.
        if count_unreadable_secrets(conn, secrets.token_bytes(SUBKEY_LENGTH)).total == 0:
            return 0, SecretCounts()
        try:
            current = settings_subkey()
        except InstanceKeyError:
            current = None
        old = _archive_subkey(archive_key) if current is not None else None
        if current is not None and old is not None:
            report = rekey_plugin_secrets(conn, old, current)
            conn.commit()
            return report.rekeyed, SecretCounts(system=report.unreadable_system, user=report.unreadable_user)
        unreadable = count_unreadable_secrets(conn, current if current is not None else secrets.token_bytes(SUBKEY_LENGTH))
        return 0, SecretCounts(system=unreadable.system, user=unreadable.user)


def _archive_subkey(archive_key: str | None) -> bytes | None:
    """The subkey of the plugin secrets on the instance the archive came from; ``None`` without a key it accepts."""
    if archive_key is None:
        return None
    try:
        return derive_key_from(archive_key, SUBKEY_PURPOSE, SUBKEY_LENGTH)
    except (InstanceKeyError, ValueError, TypeError):
        return None


def _administrators(database: Path) -> list[str]:
    """The user names of the copy's active administrators, in order."""
    with closing(sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True)) as conn:
        conn.execute("PRAGMA trusted_schema=OFF")
        rows = conn.execute("SELECT username FROM users WHERE is_superuser = 1 AND is_active = 1 ORDER BY username").fetchall()
    return [str(row[0]) for row in rows]


def _owner_check(database: Path) -> tuple[str | None, list[OwnerCandidate], list[str]]:
    """What the owner's choice needs from the copy (B5-1): the owner's address this check used
    (``LIBREFOLIO_ADMIN_EMAIL``); the accounts the owner may choose, its active administrators and the account whose
    address is the owner's whatever its role; and what in the copy would defeat the owner's assignment. Addresses compare
    as SQLite's ``lower()`` folds them, as the unique index does. Read-only, every value bound, never written into the
    SQL; no address or name reaches a log. An account whose id is not an integer or whose name is missing: a copy no
    LibreFolio wrote, ``database_damaged``."""
    from backend.app.services.platform.instance_backup.owner import configured_owner_email  # noqa: PLC0415 — owner imports apply, which imports this module

    owner_email = configured_owner_email()
    with closing(sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True)) as conn:
        conn.execute("PRAGMA trusted_schema=OFF")
        if conn.execute("SELECT 1 FROM users WHERE typeof(id) != 'integer' OR username IS NULL LIMIT 1").fetchone():
            raise StagingError("database_damaged", "The backup's accounts are not ones LibreFolio writes: it cannot be restored")
        rows = conn.execute(
            "SELECT id, username, email, is_superuser, is_active FROM users WHERE (is_superuser = 1 AND is_active = 1) OR (? IS NOT NULL AND lower(email) = lower(?)) ORDER BY username",
            (owner_email, owner_email),
        ).fetchall()
        conflicts = []
        # Two accounts on one address or one name: a copy without the unique indexes, where a sign-in may reach another
        # account than the one the owner gets.
        if conn.execute("SELECT 1 FROM users WHERE email IS NOT NULL GROUP BY lower(email) HAVING COUNT(*) > 1 LIMIT 1").fetchone():
            conflicts.append("duplicate_email")
        if conn.execute("SELECT 1 FROM users GROUP BY lower(username) HAVING COUNT(*) > 1 LIMIT 1").fetchone():
            conflicts.append("duplicate_username")
        # The owner's address as another account's name: no account may take it as its email (A-21a), so the owner's
        # assignment would be refused after the swap.
        if owner_email is not None and conn.execute("SELECT 1 FROM users WHERE lower(username) = lower(?) AND (email IS NULL OR lower(email) != lower(?)) LIMIT 1", (owner_email, owner_email)).fetchone():
            conflicts.append("address_is_a_username")
    candidates = []
    for user_id, username, email, is_superuser, is_active in rows:
        if type(user_id) is not int or username is None:
            raise StagingError("database_damaged", "The backup's accounts are not ones LibreFolio writes: it cannot be restored")
        candidates.append(OwnerCandidate(user_id=user_id, username=str(username), email=None if email is None else str(email), is_superuser=bool(is_superuser), is_active=bool(is_active)))
    return owner_email, candidates, sorted(set(conflicts))


def _holds_non_iso_currencies(database: Path, stage_id: str) -> bool:
    """Whether the upgraded copy holds stored currency values that are not ISO 4217 codes (E-19b1): E-19a's audit
    (``find_stored_currency_findings``), read only. Whatever it raises never ends the check, as the control totals' read
    (B-29): the warning is left out, and the log names the error's class, never its text or a path — a message may quote
    what the archive stores (a text that is not UTF-8 no longer gets here: B-49 refuses it first, and since E-20 the
    audit reads one as its bytes)."""
    try:
        with closing(sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True)) as conn:
            conn.execute("PRAGMA trusted_schema=OFF")
            return bool(find_stored_currency_findings(conn))
    except Exception as exc:  # noqa: BLE001 — a warning that cannot be read is left out, never a refusal
        logger.warning("Stored currency codes could not be read on the copy: the check goes on without their warning", stage_id=stage_id, error=type(exc).__name__, sqlite_error=getattr(exc, "sqlite_errorname", None))
        return False


def _report(
    stage_id: str,
    manifest: BackupManifest,
    before: DatabaseDescription,
    after: DatabaseDescription,
    action: RevisionAction,
    migrations: list[AppliedMigration],
    head: str,
    fixes: list[str],
    administrators: list[str],
    totals: TotalsComparison | None = None,
    *,
    encrypted: bool = False,
    secrets_rekeyed: int = 0,
    secrets_unreadable: SecretCounts | None = None,
    non_iso_currencies: bool = False,
) -> StagingReport:
    tables = {name: TableRows(before=before.tables.get(name), after=after.tables.get(name)) for name in sorted(set(before.tables) | set(after.tables))}
    warnings = []
    # A table the upgrade creates empty, or drops empty, changes no row: only counts that differ, an absent table
    # counting as empty, make the warning.
    if any((rows.before or 0) != (rows.after or 0) for rows in tables.values()):
        warnings.append("rows_changed")
    if after.foreign_key_violations > before.foreign_key_violations:
        warnings.append("foreign_key_violations_added")
    elif after.foreign_key_violations:
        warnings.append("foreign_key_violations")
    totals = totals or TotalsComparison("absent")
    if totals.status == "changed":
        warnings.append("control_totals_changed")
    elif totals.status == "unreadable":
        warnings.append("control_totals_unreadable")
    if non_iso_currencies:
        warnings.append("non_iso_currencies")
    # The truth of every restore (``_close_the_way_in``), said in the report too: the reader of an API, a hosting panel
    # included, gets it as a code (L3).
    warnings.append("credentials_from_backup")
    files = manifest.files[1:]
    staged_at = datetime.now(UTC)
    return StagingReport(
        stage_id=stage_id,
        staged_at=staged_at,
        expires_at=staged_at + STAGE_LIFETIME,
        backup=StagedBackup(created_at=manifest.created_at, app_version=manifest.app_version, origin=manifest.origin, alembic_revision=manifest.alembic_revision or ""),
        app_version=get_version(),
        head_revision=head,
        action=action,
        migrations=migrations,
        post_migration_fixes=fixes,
        tables=tables,
        foreign_key_violations_before=before.foreign_key_violations,
        foreign_key_violations_after=after.foreign_key_violations,
        files=len(files),
        files_size=sum(entry.size for entry in files),
        database_size=after.size,
        instance_key_included=manifest.instance_key.included,
        encrypted=encrypted,
        secrets_rekeyed=secrets_rekeyed,
        secrets_unreadable=secrets_unreadable or SecretCounts(),
        administrators=administrators,
        control_totals=totals.status,
        control_totals_differences=list(totals.differences),
        control_totals_differences_count=totals.differences_count,
        warnings=warnings,
        blockers=[] if administrators else ["no_administrator"],
    )


def _write_report(root: Path, report: StagingReport) -> None:
    fd = os.open(root / STAGE_REPORT_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(report.model_dump_json(indent=2))
        handle.write("\n")

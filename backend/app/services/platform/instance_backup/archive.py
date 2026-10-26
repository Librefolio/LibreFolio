"""Build an instance backup archive, and check one.

The archive is a zip with the shape of the data directory (``paths``): the database copied with ``VACUUM INTO``, the
archived folders file by file, and ``manifest.json`` last, listing every entry with its size and SHA-256. It is written
as ``<name>.part`` in a work folder and renamed into place only when complete, so a partial archive never carries the
final name. Files are streamed: nothing is held in memory whole. A secure backup (lot B4) adds the instance key as an
entry of its own, outside the manifest's files, and ``jobs`` then encrypts the whole archive (``envelope``).
"""

from __future__ import annotations

import hashlib
import os
import shutil
import stat
import time
import zipfile
import zlib
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from backend.app.config import get_version
from backend.app.logging_config import get_logger
from backend.app.services.platform.instance_backup.manifest import MANIFEST_MAX_BYTES, BackupManifest, BackupOrigin, ManifestDatabase, ManifestError, ManifestFile, ManifestInstanceKey
from backend.app.services.platform.instance_backup.paths import ARCHIVED_FOLDERS, DATABASE_ENTRY, INSTANCE_KEY_ENTRY, MANIFEST_ENTRY, database_path
from backend.app.services.platform.instance_backup.snapshot import file_digest, snapshot_database
from backend.app.services.platform.instance_backup.totals import ledger_totals_of

logger = get_logger(__name__)

_CHUNK = 1024 * 1024
#: Free space kept beyond the estimate: the file system needs some room for itself.
_SPACE_MARGIN = 64 * 1024 * 1024
#: The oldest and the latest times a zip entry can carry (the format counts seconds in twos).
_ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)
_ZIP_LAST = (2107, 12, 31, 23, 59, 58)
#: What a damaged entry raises while it is read: a bad CRC, a broken deflate stream, a truncated member.
_ENTRY_READ_ERRORS = (zipfile.BadZipFile, zlib.error, EOFError, OSError)
#: An instance key entry larger than this is not one LibreFolio wrote.
INSTANCE_KEY_MAX_BYTES = 4096

Phase = Literal["preparing", "database", "files", "finalizing"]
Progress = Callable[[Phase, int, int], None]

#: The warnings of a build, as stable codes: the database failed its integrity check, has foreign-key violations, or
#: some files were left out (links, special files, files or folders that could not be read, files removed meanwhile).
BuildWarning = Literal["database_integrity", "foreign_key_violations", "files_skipped"]


class BackupNoSpaceError(RuntimeError):
    """The free space where the archive is written is less than the backup needs."""

    def __init__(self, needed: int, free: int):
        super().__init__(f"A backup needs about {needed} bytes free, {free} are")
        self.needed = needed
        self.free = free


class PartialEntryError(RuntimeError):
    """A file failed while its entry was being written: the archive already holds part of it, so the build stops.

    A zip entry cannot be taken back once started, and a part of a file under its name would not match the manifest.
    A file that fails before its entry starts (removed, unreadable, no longer a regular file) is left out instead. The
    cause (a read error, or a write error such as a full disk) is the exception's ``__cause__``.
    """

    def __init__(self, entry: str):
        super().__init__(f"{entry} failed while it was being archived")
        self.entry = entry


class ArchiveError(RuntimeError):
    """The file is not an archive this LibreFolio can read. ``code`` says why, in a stable word."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class SourceFile:
    """A file of an archived folder: its entry in the archive, its path and its size when collected."""

    entry: str
    path: Path
    size: int


@dataclass(frozen=True)
class BuiltArchive:
    """The archive a build wrote, with its manifest and what the build left out."""

    path: Path
    size: int
    sha256: str
    manifest: BackupManifest
    warnings: tuple[BuildWarning, ...] = ()
    skipped: tuple[str, ...] = ()


def collect_files(data_dir: Path) -> tuple[list[SourceFile], list[str]]:
    """The regular files of the archived folders, by entry; and the entries left out (links, special files, bad names).

    Links are never followed: a link in an archived folder could point anywhere, the instance key included.
    """
    files: list[SourceFile] = []
    skipped: list[str] = []
    for folder in ARCHIVED_FOLDERS:
        root = data_dir / folder
        try:
            if not stat.S_ISDIR(root.lstat().st_mode):
                skipped.append(folder)
                continue
        except FileNotFoundError:
            continue

        # A folder that cannot be listed is reported, never dropped in silence.
        def unreadable(error: OSError, folder: str = folder) -> None:
            skipped.append(Path(error.filename).relative_to(data_dir).as_posix() if error.filename else folder)

        for current, dirs, names in os.walk(root, followlinks=False, onerror=unreadable):
            dirs.sort()
            for name in sorted(names):
                path = Path(current) / name
                entry = path.relative_to(data_dir).as_posix()
                try:
                    entry.encode("utf-8")
                    info = path.lstat()
                except (UnicodeEncodeError, OSError):
                    skipped.append(entry.encode("utf-8", "replace").decode("utf-8"))
                    continue
                if stat.S_ISREG(info.st_mode):
                    files.append(SourceFile(entry=entry, path=path, size=info.st_size))
                else:
                    skipped.append(entry)
            for name in [d for d in dirs if (Path(current) / d).is_symlink()]:
                skipped.append((Path(current) / name).relative_to(data_dir).as_posix())
    return files, skipped


def required_space(data_dir: Path, files: list[SourceFile]) -> int:
    """What a build needs free where it writes: the database twice (its copy, then inside the archive), the files, a margin."""
    database = database_path(data_dir)
    database_bytes = sum(_size_or_none(path) for path in (database, database.with_name(database.name + "-wal")))
    return 2 * database_bytes + sum(file.size for file in files) + _SPACE_MARGIN


def _size_or_none(path: Path) -> int:
    """The size of ``path``, 0 when it is not there. Measured at once, never after a separate lookup: SQLite removes the
    ``-wal`` when its last connection closes, at any moment (L3-2: a backup failed between the two)."""
    try:
        return path.stat().st_size
    except FileNotFoundError:
        return 0


def build_archive(data_dir: Path, work_dir: Path, target: Path, *, origin: BackupOrigin, progress: Progress | None = None, instance_key: str | None = None) -> BuiltArchive:
    """Build the archive of ``data_dir`` at ``target``, working in ``work_dir`` (same file system as ``target``).

    ``instance_key``: the key a secure backup carries (decision 39), as the entry ``secrets/instance.key``; the caller
    encrypts the archive. Raises ``BackupNoSpaceError`` before writing anything when the space is short. The work files
    left in ``work_dir`` on an error are the caller's to remove.
    """
    report = progress or (lambda phase, done, total: None)
    report("preparing", 0, 0)
    files, skipped = collect_files(data_dir)
    needed = required_space(data_dir, files)
    free = shutil.disk_usage(work_dir).free
    if free < needed:
        raise BackupNoSpaceError(needed, free)

    report("database", 0, 0)
    snapshot_path = work_dir / "app.db"
    database = snapshot_database(database_path(data_dir), snapshot_path)
    # J's totals of the ledger, read on the snapshot before it is zipped and removed; None leaves them out.
    control_totals = ledger_totals_of(snapshot_path)
    total = database.size + sum(file.size for file in files)
    done = 0
    warnings: list[BuildWarning] = []
    if database.integrity_check != "ok":
        warnings.append("database_integrity")
    if database.foreign_key_violations:
        warnings.append("foreign_key_violations")

    partial = work_dir / (target.name + ".part")
    entries: list[ManifestFile] = []
    created_at = datetime.now(UTC)
    # Created readable by its owner only: the archive holds every user's data.
    with os.fdopen(os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600), "wb") as handle, zipfile.ZipFile(handle, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as archive:

        def on_bytes(count: int) -> None:
            nonlocal done
            done += count
            report("files" if entries else "database", done, total)

        entries.append(_add_file(archive, snapshot_path, DATABASE_ENTRY, on_bytes))
        snapshot_path.unlink()
        for file in files:
            try:
                entries.append(_add_file(archive, file.path, file.entry, on_bytes))
            except OSError as exc:
                logger.warning("Backup left out a file it could not read", entry=file.entry, error=type(exc).__name__)
                skipped.append(file.entry)
        report("finalizing", done, total)
        key_entry = _add_instance_key(archive, instance_key)
        manifest = BackupManifest(
            created_at=created_at,
            origin=origin,
            app_version=get_version(),
            alembic_revision=database.alembic_revision,
            database=ManifestDatabase(
                integrity_check=database.integrity_check,
                foreign_key_violations=database.foreign_key_violations,
                tables=database.tables,
                control_totals=control_totals,
            ),
            files=entries,
            instance_key=key_entry,
        )
        archive.writestr(_entry_info(MANIFEST_ENTRY, time.time()), manifest.to_bytes())
        archive.close()
        handle.flush()
        os.fsync(handle.fileno())
    if skipped:
        warnings.append("files_skipped")
    size, sha256 = file_digest(partial)
    os.replace(partial, target)
    _fsync(target.parent)
    return BuiltArchive(path=target, size=size, sha256=sha256, manifest=manifest, warnings=tuple(warnings), skipped=tuple(skipped))


def _add_file(archive: zipfile.ZipFile, path: Path, entry: str, on_bytes: Callable[[int], None]) -> ManifestFile:
    """Stream one regular file into the archive, hashing what is written; the source is never followed if a link.

    An error before the entry starts (the file is gone, unreadable, no longer a regular file) is an ``OSError``, and the
    caller leaves the file out. Once the entry has started, an error reading the file or writing the archive stops the
    build with ``PartialEntryError``.
    """
    digest = hashlib.sha256()
    size = 0
    # O_NONBLOCK: a file replaced by a FIFO since it was collected must not block the run (it is refused below).
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    fd = os.open(path, flags)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise OSError(f"{entry} is not a regular file")
        source = os.fdopen(fd, "rb")
    except BaseException:
        os.close(fd)  # until the file object owns it, the descriptor is closed here
        raise
    with source:
        try:
            with archive.open(_entry_info(entry, info.st_mtime), "w", force_zip64=True) as target:
                while chunk := source.read(_CHUNK):
                    digest.update(chunk)
                    target.write(chunk)
                    size += len(chunk)
                    on_bytes(len(chunk))
        except OSError as exc:
            logger.error("Backup stopped: a file failed while it was being archived", entry=entry, error=f"{type(exc).__name__}: {exc.strerror or exc}")
            raise PartialEntryError(entry) from exc
    return ManifestFile(path=entry, size=size, sha256=digest.hexdigest())


def _add_instance_key(archive: zipfile.ZipFile, key: str | None) -> ManifestInstanceKey:
    """The instance key as an entry of its own, outside the manifest's files; what the manifest says of it."""
    if key is None:
        return ManifestInstanceKey()
    data = key.encode("utf-8")
    archive.writestr(_entry_info(INSTANCE_KEY_ENTRY, time.time()), data)
    return ManifestInstanceKey(included=True, sha256=hashlib.sha256(data).hexdigest())


def read_instance_key(archive: zipfile.ZipFile, sha256: str | None) -> str | None:
    """The text of the archive's instance key entry when it has the manifest's SHA-256; ``None`` when it is missing,
    differs, is larger than ``INSTANCE_KEY_MAX_BYTES``, is not UTF-8 or cannot be read."""
    try:
        with archive.open(INSTANCE_KEY_ENTRY) as handle:
            raw = handle.read(INSTANCE_KEY_MAX_BYTES + 1)
    except (KeyError, *_ENTRY_READ_ERRORS):
        return None
    if len(raw) > INSTANCE_KEY_MAX_BYTES or hashlib.sha256(raw).hexdigest() != sha256:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _entry_info(entry: str, mtime: float) -> zipfile.ZipInfo:
    """A deflated entry readable only by its owner once unpacked, dated at ``mtime`` (within the years a zip can carry)."""
    info = zipfile.ZipInfo(entry, date_time=min(max(time.localtime(mtime)[:6], _ZIP_EPOCH), _ZIP_LAST))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = (stat.S_IFREG | 0o600) << 16
    return info


def _fsync(path: Path) -> None:
    """Flush a file, or a folder's entries, to disk; a platform that cannot open a folder skips it."""
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


# =============================================================================
# Checking an archive
# =============================================================================


@dataclass
class ArchiveCheck:
    """What ``check_archive`` found: the manifest, and the entries that are missing, differ, or should not be there."""

    manifest: BackupManifest
    verified: bool
    missing: list[str] = field(default_factory=list)
    mismatched: list[str] = field(default_factory=list)
    unexpected: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not (self.missing or self.mismatched or self.unexpected)


def read_manifest(archive: zipfile.ZipFile) -> BackupManifest:
    """The manifest of an open archive. ``ManifestError`` when there is none or it cannot be read.

    Never inflated beyond ``MANIFEST_MAX_BYTES`` + 1, whatever size the archive declares for it.
    """
    try:
        info = archive.getinfo(MANIFEST_ENTRY)
    except KeyError:
        raise ManifestError("manifest_missing", "The archive has no manifest.json") from None
    if info.file_size > MANIFEST_MAX_BYTES:
        raise ManifestError("manifest_too_large", f"The manifest is larger than {MANIFEST_MAX_BYTES} bytes")
    try:
        with archive.open(info) as handle:
            raw = handle.read(MANIFEST_MAX_BYTES + 1)
    except _ENTRY_READ_ERRORS:
        raise ManifestError("manifest_unreadable", "The manifest entry is damaged") from None
    return BackupManifest.from_bytes(raw)


def check_archive(path: Path, *, verify: bool = True) -> ArchiveCheck:
    """Check the archive at ``path`` against its manifest; with ``verify``, read every entry and compare size and SHA-256.

    An entry is never read beyond the size its manifest gives it, so a crafted entry cannot inflate without bound. The
    instance key entry is expected when the manifest announces it (a secure backup's archive, lot B4), unexpected
    otherwise. Raises ``ArchiveError`` when the file is not a zip, ``ManifestError`` when its manifest cannot be read.
    """
    try:
        archive = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError) as exc:
        raise ArchiveError("archive_unreadable", f"Not a zip archive: {type(exc).__name__}") from None
    with archive:
        manifest = read_manifest(archive)
        names = archive.namelist()
        expected = {entry.path: entry for entry in manifest.files}
        key_expected = manifest.instance_key.included
        allowed = {MANIFEST_ENTRY, INSTANCE_KEY_ENTRY} if key_expected else {MANIFEST_ENTRY}
        check = ArchiveCheck(manifest=manifest, verified=verify)
        repeated = {name for name, count in Counter(names).items() if count > 1}
        check.unexpected = sorted({name for name in names if name not in expected and name not in allowed} | repeated)
        check.missing = sorted((set(expected) | (allowed - {MANIFEST_ENTRY})) - set(names))
        if verify:
            for entry in manifest.files:
                if entry.path in check.missing:
                    continue
                if not _entry_matches(archive, entry):
                    check.mismatched.append(entry.path)
            if key_expected and INSTANCE_KEY_ENTRY in names and read_instance_key(archive, manifest.instance_key.sha256) is None:
                check.mismatched.append(INSTANCE_KEY_ENTRY)
        return check


def _entry_matches(archive: zipfile.ZipFile, entry: ManifestFile) -> bool:
    """Whether the archive's entry has the size and SHA-256 its manifest gives; a damaged entry does not."""
    digest = hashlib.sha256()
    size = 0
    try:
        with archive.open(entry.path) as handle:
            while size <= entry.size and (chunk := handle.read(min(_CHUNK, entry.size + 1 - size))):
                digest.update(chunk)
                size += len(chunk)
    except _ENTRY_READ_ERRORS:
        return False
    return size == entry.size and digest.hexdigest() == entry.sha256

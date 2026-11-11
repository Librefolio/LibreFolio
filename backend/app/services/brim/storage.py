"""BRIM file storage: where an uploaded broker report lives, its metadata sidecar and the per-broker lock.

UUID-named data files under ``broker_reports/{uploaded,parsed,failed}/`` with a ``{uuid}.json`` sidecar; every write of one
broker is serialised by a lock, in-process and across processes. Nothing here parses a report."""

from __future__ import annotations

import json
import os
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

import structlog

from backend.app.schemas.brim import (
    BRIMDerivedRef,
    BRIMFileInfo,
    BRIMFileStatus,
)
from backend.app.services.brim.registry import BRIMProviderRegistry
from backend.app.utils.datetime_utils import utcnow

try:
    import fcntl
except ImportError:  # pragma: no cover - not POSIX: the in-process lock still serialises one server
    fcntl = None  # type: ignore[assignment]

from backend.app.config import get_data_dir, get_version
from backend.app.utils.runtime.upload_names import stored_suffix

logger = structlog.get_logger(__name__)


def get_broker_reports_dir() -> Path:
    """Get the broker reports directory based on current environment (prod/test)."""
    return get_data_dir() / "broker_reports"


def detection_signature() -> str:
    """The signature of the plugin catalogue a file's ``compatible_plugins`` were detected with.

    It is the app version: a release (or a nightly commit) may change a plugin's ``can_parse``,
    the base reader or the list of plugins, and the list detected at upload must then be detected
    again. ``plugin_version`` cannot serve: its contract covers the parse output, not detection.
    """
    return get_version()


# Metadata writes of one broker are serialised by a per-broker lock: in-process by a re-entrant
# lock (callers run on worker threads), across processes by an advisory ``flock`` on
# ``broker_reports/.locks/broker_<id>.lock`` (a test server may run several workers). Reads take no
# lock: every write is an atomic rename, so a reader sees the old sidecar or the new one.
_BROKER_LOCKS: Dict[str, threading.RLock] = {}


_BROKER_LOCKS_GUARD = threading.Lock()


_BROKER_LOCK_STATE = threading.local()


def _broker_lock_key(broker_id: Optional[int]) -> str:
    return f"broker_{broker_id}" if broker_id is not None else "broker_none"


@contextmanager
def _broker_metadata_lock(broker_id: Optional[int]) -> Iterator[None]:
    """Hold the metadata lock of one broker; re-entrant within a thread, exclusive across processes.

    The file lock is taken once, by the outermost block of the thread, and released when that block
    ends — also on an exception.
    """
    key = _broker_lock_key(broker_id)
    with _BROKER_LOCKS_GUARD:
        thread_lock = _BROKER_LOCKS.setdefault(key, threading.RLock())
    with thread_lock:
        held: Dict[str, Tuple[int, Any]] = getattr(_BROKER_LOCK_STATE, "held", None) or {}
        _BROKER_LOCK_STATE.held = held
        depth, handle = held.get(key, (0, None))
        if depth == 0:
            handle = _acquire_file_lock(key)
        held[key] = (depth + 1, handle)
        try:
            yield
        finally:
            depth, handle = held[key]
            if depth == 1:
                del held[key]
                _release_file_lock(handle)
            else:
                held[key] = (depth - 1, handle)


# The name other services use (report sets hold it from the reuse check to the save of a combined file).
broker_metadata_lock = _broker_metadata_lock


def _acquire_file_lock(key: str) -> Optional[int]:
    """Open ``.locks/<key>.lock`` and wait for its exclusive ``flock``: the descriptor, closed by ``_release_file_lock``.

    ``O_NOFOLLOW`` and ``0o600`` (Z-28): a symbolic link in the file's place raises ``OSError``, and nothing behind it
    is created or locked. None without ``fcntl``.
    """
    if fcntl is None:  # pragma: no cover - not POSIX
        return None
    lock_dir = get_broker_reports_dir() / ".locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    fd = os.open(lock_dir / f"{key}.lock", os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
    except BaseException:
        os.close(fd)
        raise
    return fd


def _release_file_lock(fd: Optional[int]) -> None:
    if fd is None:
        return
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def _broker_id_of(meta_path: Path) -> Optional[int]:
    """The broker a sidecar belongs to, from its folder (``<status>/broker_<id>/``; ``None`` at the root).

    A file keeps its broker folder for its whole life (moves only change the status folder), so every
    writer of one file derives the same lock key.
    """
    name = meta_path.parent.name
    if name.startswith("broker_"):
        try:
            return int(name[len("broker_") :])
        except ValueError:
            return None
    return None


def _write_metadata_atomic(meta_path: Path, metadata: Dict[str, Any]) -> None:
    """
    Write a BRIM metadata file atomically.

    ``Path.write_text`` truncates first and writes after, so a concurrent reader
    can observe an empty or half-written file, and a crash in between leaves the
    metadata permanently corrupt. Writing to a sibling temp file and renaming it
    makes the swap atomic on POSIX: a reader sees either the old content or the
    new one, never a mixture.

    This does not make read-modify-write sequences safe against each other — two
    writers still race for last-writer-wins — but it removes the failure mode
    where the loser leaves unparseable JSON behind.
    """
    tmp_path = meta_path.with_suffix(meta_path.suffix + f".tmp.{uuid.uuid4().hex}")
    try:
        tmp_path.write_text(json.dumps(metadata, indent=2))
        tmp_path.replace(meta_path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def _ensure_dirs(broker_id: Optional[int] = None) -> None:
    """
    Create storage directories if they don't exist.

    Args:
        broker_id: If provided, also create broker-specific subdirectories
    """
    broker_reports_dir = get_broker_reports_dir()
    for status in BRIMFileStatus:
        base_dir = broker_reports_dir / status.value
        base_dir.mkdir(parents=True, exist_ok=True)
        if broker_id is not None:
            (base_dir / f"broker_{broker_id}").mkdir(parents=True, exist_ok=True)


def _get_folder_for_status(status: BRIMFileStatus, broker_id: Optional[int] = None) -> Path:
    """
    Get the folder path for a given status.

    Args:
        status: File status (uploaded, parsed, failed)
        broker_id: If provided, return broker-specific subdirectory

    Returns:
        Path to the appropriate folder
    """
    base = get_broker_reports_dir() / status.value
    if broker_id is not None:
        return base / f"broker_{broker_id}"
    return base


def save_uploaded_file(
    content: bytes,
    original_filename: str,
    user_id: Optional[int] = None,
    broker_id: Optional[int] = None,
    batch_id: Optional[str] = None,
) -> BRIMFileInfo:
    """
    Save an uploaded file to the 'uploaded' folder.

    Process:
    1. Generate a UUID for the file (security: never expose original filename in path)
    2. Determine file extension from original filename
    3. Write file content to: uploaded/broker_{id}/{uuid}.{ext} (or uploaded/{uuid}.{ext} if no broker)
    4. Query BRIMProviderRegistry.get_compatible_plugins() to detect which plugins can parse
    5. Create metadata JSON sidecar: uploaded/broker_{id}/{uuid}.json
    6. Return BRIMFileInfo with all metadata

    Args:
        content: Raw file bytes from upload
        original_filename: Original filename (e.g., "report_2025.csv")
        user_id: ID of user uploading the file (optional, for tracking)
        broker_id: ID of target broker (optional, creates broker-specific folder)
        batch_id: Upload batch (files uploaded together form a report set)

    Returns:
        BRIMFileInfo with file_id, compatible plugins, etc.
    """
    _ensure_dirs(broker_id)

    # Generate UUID and determine extension
    file_id = str(uuid.uuid4())
    ext = stored_suffix(original_filename, ".dat")

    # Write file to uploaded folder (broker-specific if broker_id provided)
    uploaded_dir = _get_folder_for_status(BRIMFileStatus.UPLOADED, broker_id)
    file_path = uploaded_dir / f"{file_id}{ext}"
    file_path.write_bytes(content)

    # Detect compatible plugins
    signature = detection_signature()
    compatible_plugins = BRIMProviderRegistry.get_compatible_plugins(file_path)

    # Create metadata
    now = utcnow()
    metadata = {
        "file_id": file_id,
        "filename": original_filename,
        "extension": ext,
        "size_bytes": len(content),
        "status": BRIMFileStatus.UPLOADED.value,
        "uploaded_at": now.isoformat(),
        "processed_at": None,
        "compatible_plugins": compatible_plugins,
        "plugins_signature": signature,
        "error_message": None,
        # Multi-user fields
        "uploaded_by_user_id": user_id,
        "target_broker_id": broker_id,
        "last_parse_result": None,
        "batch_id": batch_id,
    }

    # Write metadata JSON
    meta_path = uploaded_dir / f"{file_id}.json"
    with _broker_metadata_lock(_broker_id_of(meta_path)):
        _write_metadata_atomic(meta_path, metadata)

    logger.info(
        "Saved uploaded file",
        file_id=file_id,
        original_filename=original_filename,
        size_bytes=len(content),
        compatible_plugins=compatible_plugins,
        user_id=user_id,
        broker_id=broker_id,
    )

    return BRIMFileInfo(
        file_id=file_id,
        filename=original_filename,
        size_bytes=len(content),
        status=BRIMFileStatus.UPLOADED,
        uploaded_at=now,
        compatible_plugins=compatible_plugins,
        uploaded_by_user_id=user_id,
        target_broker_id=broker_id,
        batch_id=batch_id,
    )


def _build_file_info_from_metadata(meta_path: Path) -> Optional[BRIMFileInfo]:
    """
    Parse a metadata JSON sidecar into a :class:`BRIMFileInfo`.

    Returns ``None`` if the file does not exist or the JSON is malformed.
    Computes ``parse_is_stale`` lazily by comparing the persisted
    ``parsed_plugin_version`` with the current plugin version in the registry.

    This is the single source of truth for metadata deserialization;
    it replaces the previously duplicated inner helpers in ``list_files``
    and ``get_file_info``.
    """
    if not meta_path.exists():
        return None
    try:
        metadata = json.loads(meta_path.read_text())
        status = BRIMFileStatus(metadata["status"])
        parsed_plugin_code = metadata.get("parsed_plugin_code")
        parsed_plugin_version = metadata.get("parsed_plugin_version")

        parse_is_stale = False
        if status == BRIMFileStatus.PARSED and parsed_plugin_code and parsed_plugin_version:
            plugin = BRIMProviderRegistry.get_provider_instance(parsed_plugin_code)
            if plugin is not None and plugin.plugin_version != parsed_plugin_version:
                parse_is_stale = True

        kind = metadata.get("kind", "original")
        combine_is_stale = False
        combine_plugin_code = metadata.get("combine_plugin_code")
        if kind == "combined" and combine_plugin_code:
            combine_plugin = BRIMProviderRegistry.get_provider_instance(combine_plugin_code)
            if combine_plugin is not None and combine_plugin.plugin_version != metadata.get("combine_plugin_version"):
                combine_is_stale = True

        return BRIMFileInfo(
            file_id=metadata["file_id"],
            filename=metadata["filename"],
            size_bytes=metadata["size_bytes"],
            status=status,
            uploaded_at=datetime.fromisoformat(metadata["uploaded_at"]),
            processed_at=(datetime.fromisoformat(metadata["processed_at"]) if metadata.get("processed_at") else None),
            compatible_plugins=metadata.get("compatible_plugins", []) if kind == "combined" else _current_compatible_plugins(meta_path, metadata),
            error_message=metadata.get("error_message"),
            uploaded_by_user_id=metadata.get("uploaded_by_user_id"),
            target_broker_id=metadata.get("target_broker_id"),
            last_parse_result=metadata.get("last_parse_result"),
            parsed_plugin_code=parsed_plugin_code,
            parsed_plugin_version=parsed_plugin_version,
            parsed_settings_fingerprint=metadata.get("parsed_settings_fingerprint"),
            parse_is_stale=parse_is_stale,
            batch_id=metadata.get("batch_id"),
            kind=kind,
            derived_from=[BRIMDerivedRef(**ref) for ref in metadata.get("derived_from", [])],
            combined_into=list(metadata.get("combined_into", [])),
            combine_is_stale=combine_is_stale,
        )
    except Exception as e:
        logger.warning("Error reading file metadata", meta_path=str(meta_path), error=str(e))
        return None


def _current_compatible_plugins(meta_path: Path, metadata: Dict[str, Any]) -> List[str]:
    """An original's ``compatible_plugins`` for today's plugin catalogue (item 8).

    The list is detected at upload and stored with the catalogue's signature. When the signature
    is missing (a file uploaded before 1.2) or older than today's, the file is detected again: a
    plugin added or changed since then — Danske Bank after 1.1.0, the stricter Generic CSV — is
    then offered for it. The detection runs outside the lock (it reads the file); its result is
    saved under the broker lock, once per version. If the data file is gone, the stored list stays.
    """
    stored = list(metadata.get("compatible_plugins", []))
    signature = detection_signature()
    if metadata.get("plugins_signature") == signature:
        return stored
    ext = stored_suffix(metadata.get("filename", ""), ".dat")
    data_path = meta_path.with_name(f"{metadata['file_id']}{ext}")
    if not data_path.exists():
        return stored
    try:
        detected = BRIMProviderRegistry.get_compatible_plugins(data_path)
    except Exception as e:  # never let a read fail on detection: the stored list still describes the file
        logger.warning("Plugin re-detection failed", file_id=metadata.get("file_id"), error=str(e))
        return stored
    _save_detection(meta_path, detected, signature)
    return detected


def _save_detection(meta_path: Path, detected: List[str], signature: str) -> None:
    """Store a re-detection, unless the sidecar moved or was detected again meanwhile.

    Under the broker lock the sidecar is read again: a move or a deletion holds the same lock, so a
    sidecar still at its path is the current one, and only the two detection fields change — a
    field another writer set meanwhile is kept, and a stale copy is never written back.
    """
    with _broker_metadata_lock(_broker_id_of(meta_path)):
        if not meta_path.exists():
            return
        try:
            current = json.loads(meta_path.read_text())
        except Exception:
            return
        if current.get("plugins_signature") == signature:
            return
        current["compatible_plugins"] = detected
        current["plugins_signature"] = signature
        _write_metadata_atomic(meta_path, current)


def _find_metadata_path(file_id: str) -> Optional[Path]:
    """
    Find the sidecar JSON metadata path for a given ``file_id`` by scanning
    every status folder and its ``broker_*`` subdirectories.

    Returns the first match, or ``None`` if the file is not present anywhere.
    Used by :func:`get_file_info` and :func:`save_parse_result` to avoid
    triplicating the scan logic. ``list_files`` performs an exhaustive
    scan and intentionally keeps its own loop.
    """
    broker_reports_dir = get_broker_reports_dir()
    for status in BRIMFileStatus:
        status_folder = broker_reports_dir / status.value

        # Root folder (backward compatibility)
        candidate = status_folder / f"{file_id}.json"
        if candidate.exists():
            return candidate

        # Broker subdirectories
        for broker_dir in status_folder.glob("broker_*"):
            if broker_dir.is_dir():
                candidate = broker_dir / f"{file_id}.json"
                if candidate.exists():
                    return candidate
    return None


def list_files(  # noqa: C901 — flat directory scan over status/broker folders, no decision logic
    status: Optional[BRIMFileStatus] = None,
    broker_ids: Optional[List[int]] = None,
) -> List[BRIMFileInfo]:
    """
    List all files, optionally filtered by status and/or broker_ids.

    Process:
    1. Determine which folders to scan (one folder per status, or all if status=None)
    2. For each folder, also scan broker-specific subdirectories
    3. For each *.json metadata file found, parse into BRIMFileInfo
    4. Filter by broker_ids if specified
    5. Return sorted list (most recent first by uploaded_at)

    Args:
        status: Optional filter (UPLOADED, IMPORTED, FAILED)
        broker_ids: Optional list of broker IDs to filter by

    Returns:
        List of BRIMFileInfo objects, sorted by uploaded_at (newest first)
    """
    _ensure_dirs()

    # Determine status folders to scan
    broker_reports_dir = get_broker_reports_dir()
    if status:
        status_folders = [broker_reports_dir / status.value]
    else:
        status_folders = [broker_reports_dir / s.value for s in BRIMFileStatus]

    files: List[BRIMFileInfo] = []

    for folder in status_folders:
        if not folder.exists():
            continue

        # Scan root folder (files without broker_id, backward compatibility)
        for meta_path in folder.glob("*.json"):
            file_info = _build_file_info_from_metadata(meta_path)
            if file_info:
                files.append(file_info)

        # Scan broker subdirectories
        for broker_dir in folder.glob("broker_*"):
            if broker_dir.is_dir():
                for meta_path in broker_dir.glob("*.json"):
                    file_info = _build_file_info_from_metadata(meta_path)
                    if file_info:
                        files.append(file_info)

    # Filter by broker_ids if specified
    if broker_ids is not None:
        # Include files with matching broker_id OR files without broker_id (legacy)
        files = [f for f in files if f.target_broker_id in broker_ids or f.target_broker_id is None]

    # Sort by uploaded_at, newest first
    files.sort(key=lambda f: f.uploaded_at, reverse=True)
    return files


def get_file_info(file_id: str) -> Optional[BRIMFileInfo]:
    """
    Get metadata for a specific file by its UUID.

    Process:
    1. Search for {file_id}.json in all status folders and their broker subdirectories
    2. Return first match, or None if not found

    Args:
        file_id: UUID of the file

    Returns:
        BRIMFileInfo or None if not found
    """
    _ensure_dirs()
    meta_path = _find_metadata_path(file_id)
    if meta_path is None:
        return None
    return _build_file_info_from_metadata(meta_path)


def get_file_path(file_id: str) -> Optional[Path]:
    """
    Get the actual filesystem path to a file for parsing.

    Process:
    1. Call get_file_info() to find the file and its current status
    2. Extract original extension from the stored metadata
    3. Construct path: {status_folder}/[broker_{id}/]{file_id}.{ext}
    4. Verify file exists, return Path or None

    Args:
        file_id: UUID of the file

    Returns:
        Path object or None if file not found
    """
    file_info = get_file_info(file_id)
    if not file_info:
        return None

    # Get extension from filename
    ext = stored_suffix(file_info.filename, ".dat")

    # Construct path (broker-specific if target_broker_id is set)
    folder = _get_folder_for_status(file_info.status, file_info.target_broker_id)
    file_path = folder / f"{file_id}{ext}"

    if file_path.exists():
        return file_path

    # Fallback: try root folder (backward compatibility)
    if file_info.target_broker_id is not None:
        root_folder = _get_folder_for_status(file_info.status, None)
        fallback_path = root_folder / f"{file_id}{ext}"
        if fallback_path.exists():
            return fallback_path

    # Last resort: scan every status folder, the way _find_metadata_path already
    # does for the sidecar. The two are not always in agreement: _move_file
    # renames the data file first and rewrites the metadata after, so a reader
    # arriving in between computes the *old* folder for a file that already
    # lives in the new one. Deriving the address from the status is only a
    # shortcut; the file itself is the fact.
    return _find_data_path(file_id, ext)


def _find_data_path(file_id: str, ext: str) -> Optional[Path]:
    """Locate a file's data by scanning every status folder and ``broker_*`` subdir."""
    broker_reports_dir = get_broker_reports_dir()
    for status in BRIMFileStatus:
        status_folder = broker_reports_dir / status.value

        candidate = status_folder / f"{file_id}{ext}"
        if candidate.exists():
            return candidate

        for broker_dir in status_folder.glob("broker_*"):
            if broker_dir.is_dir():
                candidate = broker_dir / f"{file_id}{ext}"
                if candidate.exists():
                    return candidate
    return None


def delete_file(file_id: str) -> bool:
    """
    Delete a file and its metadata.

    Process:
    1. Find file location via get_file_info()
    2. Delete both the data file and .json metadata
    3. Return True if deleted, False if not found

    Args:
        file_id: UUID of the file

    Returns:
        True if deleted, False if not found
    """
    meta_path = _find_metadata_path(file_id)
    if meta_path is None:
        return False
    with _broker_metadata_lock(_broker_id_of(meta_path)):
        return _delete_file_locked(file_id)


def delete_files_for_brokers(broker_ids: List[int]) -> int:
    """Delete every BRIM import file that belongs to the given, already deleted, brokers.

    BRIM files live on the filesystem, not in the database, so the ORM cascade that removes a
    broker and its transactions never touches them: the callers run this after the commit that
    deleted the brokers — ``DELETE /brokers``, the last owner leaving a broker, an account
    deletion. Best-effort: only files whose ``target_broker_id`` matches exactly are removed;
    legacy files with no broker (``None``) are left untouched. Once a broker's files are gone,
    its storage goes too (``_remove_broker_storage``).

    Returns the number of files removed. Synchronous filesystem I/O: async callers run it
    through ``asyncio.to_thread``.
    """
    removed = 0
    for broker_id in broker_ids:
        try:
            for file_info in list_files(broker_ids=[broker_id]):
                if file_info.target_broker_id == broker_id and delete_file(file_info.file_id):
                    removed += 1
            _remove_broker_storage(broker_id)
        except Exception as exc:  # best-effort: the broker is already deleted
            logger.warning("Failed to clean BRIM files for deleted broker", broker_id=broker_id, error=str(exc))
    return removed


def _remove_broker_storage(broker_id: int) -> None:
    """Remove a deleted broker's status folders, when empty, and its lock file.

    Runs under the broker's lock, so no writer of this process or another sits between a read and a
    write of its sidecars. ``rmdir`` removes only an empty folder: one still holding a file the store
    did not write stays, with a warning. The lock file is unlinked while held. The re-entrant lock in
    ``_BROKER_LOCKS`` stays: dropping it could hand a second lock for the same key to a thread already
    waiting on the first.
    """
    with _broker_metadata_lock(broker_id):
        for status in BRIMFileStatus:
            folder = _get_folder_for_status(status, broker_id)
            try:
                folder.rmdir()
            except FileNotFoundError:
                continue
            except OSError as exc:
                logger.warning("Kept a non-empty folder of a deleted broker", broker_id=broker_id, folder=str(folder), error=str(exc))
        (get_broker_reports_dir() / ".locks" / f"{_broker_lock_key(broker_id)}.lock").unlink(missing_ok=True)


def _delete_file_locked(file_id: str) -> bool:
    file_info = get_file_info(file_id)
    if not file_info:
        return False

    _unlink_report_set_references(file_info)

    # Get extension and folder (broker-specific if set)
    ext = stored_suffix(file_info.filename, ".dat")
    folder = _get_folder_for_status(file_info.status, file_info.target_broker_id)

    # Delete data file
    file_path = folder / f"{file_id}{ext}"
    if file_path.exists():
        file_path.unlink()

    # Delete metadata
    meta_path = folder / f"{file_id}.json"
    if meta_path.exists():
        meta_path.unlink()

    logger.info("Deleted file", file_id=file_id)
    return True


def _update_metadata(file_id: str, mutate: Callable[[Dict[str, Any]], None]) -> bool:
    """Load a sidecar, apply ``mutate(metadata)`` and write it back atomically, under the broker lock."""
    meta_path = _find_metadata_path(file_id)
    if meta_path is None:
        return False
    with _broker_metadata_lock(_broker_id_of(meta_path)):
        meta_path = _find_metadata_path(file_id)
        if meta_path is None:
            return False
        metadata = json.loads(meta_path.read_text())
        mutate(metadata)
        _write_metadata_atomic(meta_path, metadata)
    return True


def _iter_metadata_paths(broker_id: int) -> Iterator[Path]:
    """Every sidecar of one broker, across status folders."""
    broker_reports_dir = get_broker_reports_dir()
    for status in BRIMFileStatus:
        broker_dir = broker_reports_dir / status.value / f"broker_{broker_id}"
        if broker_dir.is_dir():
            yield from broker_dir.glob("*.json")


def _unlink_report_set_references(file_info: BRIMFileInfo) -> None:
    """Keep report-set links consistent before a file is deleted.

    Deleting an original marks it as deleted in its combined files, which stay
    usable because they carry the verbatim values. Deleting a combined file
    removes it from its originals' ``combined_into``.
    """
    deleted_id = file_info.file_id

    def _mark_deleted(metadata: Dict[str, Any]) -> None:
        refs = metadata.get("derived_from", [])
        for ref in refs:
            if ref.get("file_id") == deleted_id:
                ref["deleted"] = True
        metadata["derived_from"] = refs

    def _drop_combined(metadata: Dict[str, Any]) -> None:
        metadata["combined_into"] = [item for item in metadata.get("combined_into", []) if item != deleted_id]

    for combined_id in file_info.combined_into:
        _update_metadata(combined_id, _mark_deleted)
    if file_info.kind == "combined":
        for ref in file_info.derived_from:
            _update_metadata(ref.file_id, _drop_combined)


def move_to_parsed(file_id: str) -> bool:
    """
    Move a successfully parsed file from 'uploaded' to 'parsed'.

    Process:
    1. Get current file info and verify status is UPLOADED
    2. Move data file: uploaded/{id}.ext → parsed/{id}.ext
    3. Update metadata: status=PARSED, processed_at=now()
    4. Write updated metadata to parsed/{id}.json
    5. Delete old metadata from uploaded/

    Args:
        file_id: UUID of the file

    Returns:
        True if moved, False if not found or wrong status
    """
    return _move_file(file_id, BRIMFileStatus.PARSED)


def move_to_failed(file_id: str, error_message: str) -> bool:
    """
    Move a failed file from 'uploaded' to 'failed' with error details.

    Process:
    1. Get current file info and verify status is UPLOADED
    2. Move data file: uploaded/{id}.ext → failed/{id}.ext
    3. Update metadata: status=FAILED, processed_at=now(), error_message=error
    4. Write updated metadata to failed/{id}.json
    5. Delete old metadata from uploaded/

    Args:
        file_id: UUID of the file
        error_message: Error description to store

    Returns:
        True if moved, False if not found or wrong status
    """
    return _move_file(file_id, BRIMFileStatus.FAILED, error_message)


def save_parse_result(
    file_id: str,
    parse_result: dict,
    plugin_code: Optional[str] = None,
    settings_fingerprint: Optional[str] = None,
) -> bool:
    """
    Save the parse result to the file's metadata for caching.

    This allows the frontend to reload a previous parse result without
    re-parsing the file. If ``plugin_code`` is provided, the current
    plugin version is resolved via :class:`BRIMProviderRegistry` and
    persisted as ``parsed_plugin_version`` so that :class:`BRIMFileInfo`
    can compute ``parse_is_stale`` later when the plugin is bumped.

    The registry is the single source of truth for ``plugin_version``:
    callers pass only the plugin code; this function derives the version.

    Args:
        file_id: UUID of the file
        parse_result: Dictionary containing transactions, warnings, etc.
        plugin_code: Plugin code used to produce ``parse_result``
        settings_fingerprint: ``BoundSettings.fingerprint`` of the values the parse received (CP12), saved as
            ``parsed_settings_fingerprint`` so that a changed setting makes the file stale; ``None`` (a plugin without
            fields) removes the one a previous parse left

    Returns:
        True if saved successfully, False otherwise
    """
    _ensure_dirs()

    meta_path = _find_metadata_path(file_id)
    if meta_path is None:
        logger.warning("Metadata file not found for caching parse result", file_id=file_id)
        return False

    with _broker_metadata_lock(_broker_id_of(meta_path)):
        meta_path = _find_metadata_path(file_id)
        if meta_path is None:
            logger.warning("Metadata file not found for caching parse result", file_id=file_id)
            return False

        # Load, update, and save metadata
        metadata = json.loads(meta_path.read_text())
        metadata["last_parse_result"] = parse_result
        plugin_version: Optional[str] = None
        if plugin_code is not None:
            metadata["parsed_plugin_code"] = plugin_code
            plugin = BRIMProviderRegistry.get_provider_instance(plugin_code)
            if plugin is not None:
                plugin_version = plugin.plugin_version
                metadata["parsed_plugin_version"] = plugin_version
        if settings_fingerprint is not None:
            metadata["parsed_settings_fingerprint"] = settings_fingerprint
        else:
            metadata.pop("parsed_settings_fingerprint", None)
        _write_metadata_atomic(meta_path, metadata)

    logger.info(
        "Saved parse result to metadata",
        file_id=file_id,
        plugin_code=plugin_code,
        plugin_version=plugin_version,
    )
    return True


def _move_file(file_id: str, target_status: BRIMFileStatus, error_message: Optional[str] = None) -> bool:
    """
    Internal helper to move a file to a different status folder.

    Args:
        file_id: UUID of the file
        target_status: Target status (IMPORTED or FAILED)
        error_message: Error message (only for FAILED status)

    Returns:
        True if moved, False if not found or wrong status
    """
    _ensure_dirs()

    meta_path = _find_metadata_path(file_id)
    if meta_path is None:
        return False
    # The whole move holds the broker lock: a writer that read the sidecar before the move then finds
    # it gone, and never writes it back at the old address (which would make the file appear twice).
    with _broker_metadata_lock(_broker_id_of(meta_path)):
        return _move_file_locked(file_id, target_status, error_message)


def _move_file_locked(file_id: str, target_status: BRIMFileStatus, error_message: Optional[str]) -> bool:
    # Get current file info
    file_info = get_file_info(file_id)
    if not file_info:
        return False

    # Only move from UPLOADED status
    if file_info.status != BRIMFileStatus.UPLOADED:
        logger.warning(
            "Cannot move file: not in UPLOADED status",
            file_id=file_id,
            current_status=file_info.status.value,
        )
        return False

    # Get extension and broker_id
    ext = stored_suffix(file_info.filename, ".dat")
    broker_id = file_info.target_broker_id

    # Source paths - check broker subfolder first, then root
    broker_reports_dir = get_broker_reports_dir()
    src_status_folder = broker_reports_dir / BRIMFileStatus.UPLOADED.value
    if broker_id:
        broker_subfolder = src_status_folder / f"broker_{broker_id}"
        src_file = broker_subfolder / f"{file_id}{ext}"
        src_meta = broker_subfolder / f"{file_id}.json"
        # Fallback to root if not in broker subfolder
        if not src_meta.exists():
            src_file = src_status_folder / f"{file_id}{ext}"
            src_meta = src_status_folder / f"{file_id}.json"
    else:
        src_file = src_status_folder / f"{file_id}{ext}"
        src_meta = src_status_folder / f"{file_id}.json"

    # Target paths - keep in broker subfolder if source was there
    dst_status_folder = broker_reports_dir / target_status.value
    if broker_id:
        dst_broker_folder = dst_status_folder / f"broker_{broker_id}"
        dst_broker_folder.mkdir(parents=True, exist_ok=True)
        dst_file = dst_broker_folder / f"{file_id}{ext}"
        dst_meta = dst_broker_folder / f"{file_id}.json"
    else:
        dst_file = dst_status_folder / f"{file_id}{ext}"
        dst_meta = dst_status_folder / f"{file_id}.json"

    # Move data file
    if src_file.exists():
        src_file.rename(dst_file)

    # Update and move metadata
    if src_meta.exists():
        metadata = json.loads(src_meta.read_text())
        metadata["status"] = target_status.value
        metadata["processed_at"] = utcnow().isoformat()
        if error_message:
            metadata["error_message"] = error_message
        _write_metadata_atomic(dst_meta, metadata)
        src_meta.unlink()

    logger.info(
        "Moved file",
        file_id=file_id,
        from_status=BRIMFileStatus.UPLOADED.value,
        to_status=target_status.value,
    )
    return True

"""BRIM combined files: the single CSV a report set is merged into, saved beside its members and reused while the members stand."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

from backend.app.schemas.brim import (
    BRIMCombinedTable,
    BRIMDerivedRef,
    BRIMFileInfo,
    BRIMFileStatus,
)
from backend.app.services.brim import storage
from backend.app.utils.datetime_utils import utcnow

logger = structlog.get_logger(__name__)


def _members_key(member_ids: List[str]) -> str:
    """Order-insensitive identity of a set of member files."""
    return hashlib.sha256(",".join(sorted(member_ids)).encode("utf-8")).hexdigest()


def _combined_csv_text(table: BRIMCombinedTable) -> str:
    """A combined table as CSV text: ``;``-separated, one row per line."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";", quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
    writer.writerow(table.headers)
    writer.writerows(table.rows)
    return buffer.getvalue()


def combined_csv_size(table: BRIMCombinedTable) -> int:
    """The bytes ``write_combined_csv`` writes for ``table``: the space limit asks it before the file is written (C8)."""
    return len(_combined_csv_text(table).encode("utf-8-sig"))


def write_combined_csv(path: Path, table: BRIMCombinedTable) -> None:
    """Write a combined table as UTF-8 with BOM, ``;``-separated, one row per line."""
    path.write_text(_combined_csv_text(table), encoding="utf-8-sig", newline="")


def save_combined_file(
    *,
    broker_id: int,
    plugin_code: str,
    plugin_version: str,
    members: List[BRIMDerivedRef],
    table: BRIMCombinedTable,
    filename: str,
    user_id: Optional[int] = None,
) -> BRIMFileInfo:
    """
    Save the combined file of a report set next to its originals.

    The combined file is an ordinary BRIM file (``kind = "combined"``) that only
    its plugin can parse. Its sidecar records the originals it was built from,
    the plugin code and version that built it and the combine summary; every
    original gains the new file in ``combined_into``. The whole write holds the broker lock.
    """
    with storage._broker_metadata_lock(broker_id):
        return _save_combined_file_locked(
            broker_id=broker_id,
            plugin_code=plugin_code,
            plugin_version=plugin_version,
            members=members,
            table=table,
            filename=filename,
            user_id=user_id,
        )


def _save_combined_file_locked(
    *,
    broker_id: int,
    plugin_code: str,
    plugin_version: str,
    members: List[BRIMDerivedRef],
    table: BRIMCombinedTable,
    filename: str,
    user_id: Optional[int],
) -> BRIMFileInfo:
    storage._ensure_dirs(broker_id)
    if not filename.lower().endswith(".csv"):
        filename = f"{filename}.csv"

    file_id = str(uuid.uuid4())
    uploaded_dir = storage._get_folder_for_status(BRIMFileStatus.UPLOADED, broker_id)
    file_path = uploaded_dir / f"{file_id}.csv"
    write_combined_csv(file_path, table)

    member_ids = [member.file_id for member in members]
    batch_ids = set()
    for member_id in member_ids:
        member_info = storage.get_file_info(member_id)
        batch_ids.add(member_info.batch_id if member_info else None)
    batch_id = batch_ids.pop() if len(batch_ids) == 1 else None

    now = utcnow()
    metadata = {
        "file_id": file_id,
        "filename": filename,
        "extension": ".csv",
        "size_bytes": file_path.stat().st_size,
        "status": BRIMFileStatus.UPLOADED.value,
        "uploaded_at": now.isoformat(),
        "processed_at": None,
        "compatible_plugins": [plugin_code],
        "error_message": None,
        "uploaded_by_user_id": user_id,
        "target_broker_id": broker_id,
        "last_parse_result": None,
        "batch_id": batch_id,
        "kind": "combined",
        "derived_from": [member.model_dump() for member in members],
        "combine_plugin_code": plugin_code,
        "combine_plugin_version": plugin_version,
        "combine_summary": table.summary,
        "members_key": _members_key(member_ids),
    }
    storage._write_metadata_atomic(uploaded_dir / f"{file_id}.json", metadata)

    def _link(member_metadata: Dict[str, Any]) -> None:
        combined_into = list(member_metadata.get("combined_into", []))
        if file_id not in combined_into:
            combined_into.append(file_id)
        member_metadata["combined_into"] = combined_into

    for member_id in member_ids:
        storage._update_metadata(member_id, _link)

    logger.info("Saved combined report-set file", file_id=file_id, plugin_code=plugin_code, members=len(member_ids), broker_id=broker_id)
    info = storage.get_file_info(file_id)
    if info is None:  # pragma: no cover - the sidecar was just written
        raise RuntimeError(f"combined file {file_id} vanished after being written")
    return info


def find_reusable_combined(
    *,
    broker_id: int,
    plugin_code: str,
    plugin_version: str,
    member_ids: List[str],
) -> Optional[BRIMFileInfo]:
    """The combined file already built for exactly these members by this plugin version, if any."""
    wanted = _members_key(member_ids)
    for meta_path in storage._iter_metadata_paths(broker_id):
        try:
            metadata = json.loads(meta_path.read_text())
        except Exception:
            continue
        if metadata.get("kind") == "combined" and metadata.get("target_broker_id") == broker_id and metadata.get("combine_plugin_code") == plugin_code and metadata.get("combine_plugin_version") == plugin_version and metadata.get("members_key") == wanted:
            return storage._build_file_info_from_metadata(meta_path)
    return None


def read_combine_summary(file_id: str) -> Dict[str, Any]:
    """The combine summary stored with a combined file; ``{}`` for originals or unknown files."""
    meta_path = storage._find_metadata_path(file_id)
    if meta_path is None:
        return {}
    try:
        metadata = json.loads(meta_path.read_text())
    except Exception:
        return {}
    summary = metadata.get("combine_summary") if metadata.get("kind") == "combined" else None
    return dict(summary) if isinstance(summary, dict) else {}

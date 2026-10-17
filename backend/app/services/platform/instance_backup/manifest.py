"""The manifest of an instance backup: ``manifest.json``, the last entry of the archive.

It says what made the archive (app version, origin, date), the Alembic revision of its database (what a restore
compares with the app's head), what the database held (integrity, foreign keys, rows per table) and every other entry
with its size and SHA-256. ``format_version`` changes only with an incompatible change; a field added later is ignored
by a reader that does not know it.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from backend.app.services.platform.instance_backup.paths import ARCHIVED_FOLDERS, DATABASE_ENTRY

FORMAT = "librefolio-backup"
FORMAT_VERSION = 1
#: A manifest larger than this is not one LibreFolio wrote (a hundred thousand files take about 15 MB).
MANIFEST_MAX_BYTES = 64 * 1024 * 1024

#: What made an archive: the Settings tab, the CLI, the automatic backup before a restore (B3), the hosting panel (B8).
BackupOrigin = Literal["ui", "cli", "pre-restore", "panel"]


class ManifestError(ValueError):
    """The manifest cannot be read or is not one this LibreFolio understands. ``code`` says why, in a stable word."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def check_entry_path(value: str) -> str:
    """An archive entry is the database, or a file below one of the archived folders, as a plain relative POSIX path."""
    parts = value.split("/")
    if value == DATABASE_ENTRY:
        return value
    if "\\" in value or "\x00" in value or len(parts) < 2 or parts[0] not in ARCHIVED_FOLDERS or any(part in ("", ".", "..") for part in parts):
        raise ValueError(f"not an entry a backup carries: {value!r}")
    return value


class ManifestFile(BaseModel):
    """One entry of the archive: where it goes in the data directory, its size and its SHA-256."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    path: str
    size: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("path")
    @classmethod
    def _entry_path(cls, value: str) -> str:
        return check_entry_path(value)


class ManifestDatabase(BaseModel):
    """What the database of the archive held when it was copied."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    path: Literal["sqlite/app.db"] = DATABASE_ENTRY
    integrity_check: str
    foreign_key_violations: int = Field(ge=0)
    tables: dict[str, int]
    #: J's control totals of the ledger (``ControlTotals.to_json()``), read on the snapshot (lot B-13); ``None`` in an
    #: archive made before, or when they could not be read. Any JSON: a malformed value is not compared, never refused.
    control_totals: Any = None


class ManifestInstanceKey(BaseModel):
    """Whether the archive carries the instance key (``secrets/instance.key``), and its SHA-256.

    Only a password-protected archive may, and only a key LibreFolio generated (decision 39, lot B4). The entry is not
    among ``files``: a restore never unpacks it, it only reads it to re-encrypt the restored secrets.
    """

    model_config = ConfigDict(extra="ignore", frozen=True)

    included: bool = False
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _sha256_with_the_key(self) -> ManifestInstanceKey:
        if self.included != (self.sha256 is not None):
            raise ValueError("instance_key.sha256 is given exactly when the key is included")
        return self


class BackupManifest(BaseModel):
    """``manifest.json``."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    format: Literal["librefolio-backup"] = FORMAT
    format_version: int = FORMAT_VERSION
    created_at: datetime
    origin: BackupOrigin
    app_version: str
    alembic_revision: str | None
    database: ManifestDatabase
    #: Every entry but the manifest, the database first.
    files: list[ManifestFile]
    instance_key: ManifestInstanceKey = ManifestInstanceKey()

    @field_validator("created_at")
    @classmethod
    def _utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("created_at must carry its time zone")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def _entries(self) -> BackupManifest:
        paths = [entry.path for entry in self.files]
        if not paths or paths[0] != DATABASE_ENTRY:
            raise ValueError(f"the first entry must be the database, {DATABASE_ENTRY}")
        if len(set(paths)) != len(paths):
            raise ValueError("an entry is listed twice")
        return self

    def to_bytes(self) -> bytes:
        """The manifest as UTF-8 JSON, indented, ending with a line break."""
        return (json.dumps(self.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n").encode("utf-8")

    @classmethod
    def from_bytes(cls, raw: bytes) -> BackupManifest:
        """Read a manifest, checking the format and its version before the fields. ``ManifestError`` when it cannot."""
        if len(raw) > MANIFEST_MAX_BYTES:
            raise ManifestError("manifest_too_large", f"The manifest is larger than {MANIFEST_MAX_BYTES} bytes")
        try:
            document = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ManifestError("manifest_unreadable", "The manifest is not UTF-8 JSON") from None
        if not isinstance(document, dict) or document.get("format") != FORMAT:
            raise ManifestError("manifest_unknown_format", "The archive is not a LibreFolio backup")
        version = document.get("format_version")
        if not isinstance(version, int) or isinstance(version, bool) or version < 1:
            raise ManifestError("manifest_invalid", "The manifest has no valid format_version")
        if version > FORMAT_VERSION:
            raise ManifestError("manifest_newer_format", f"The backup uses format {version}, newer than this LibreFolio reads ({FORMAT_VERSION})")
        try:
            return cls.model_validate(document)
        except ValidationError as exc:
            raise ManifestError("manifest_invalid", f"The manifest is not valid: {exc.error_count()} problem(s)") from None

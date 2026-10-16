"""Schemas of the instance backup: the state of a backup job (``/backup/instance``), and the check of an archive before a
restore (``/backup/restore``): its upload, its check on a copy, and the report of what the restore would do."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class InstanceBackupJob(BaseModel):
    """A backup of the whole instance, built in the background: poll it until ``status`` is ``done`` or ``failed``.

    ``done_bytes`` of ``total_bytes`` measure the bytes read so far; ``total_bytes`` is 0 until the database is copied.
    ``warnings`` are stable codes: ``database_integrity`` (the database failed its integrity check),
    ``foreign_key_violations``, ``files_skipped`` (files that changed or vanished during the backup, left out).
    ``error_code``: ``backup_no_space``, ``backup_failed`` (the server log has the cause) or ``backup_interrupted`` (the
    server stopped during the backup).
    """

    model_config = ConfigDict(extra="forbid")

    job_id: str
    status: Literal["running", "done", "failed"]
    phase: Literal["preparing", "database", "files", "finalizing"] | None = None
    done_bytes: int = Field(ge=0)
    total_bytes: int = Field(ge=0)
    created_at: datetime
    finished_at: datetime | None = None
    file_name: str | None = None
    file_size: int | None = Field(default=None, ge=0)
    warnings: list[Literal["database_integrity", "foreign_key_violations", "files_skipped"]] = []
    error_code: Literal["backup_no_space", "backup_failed", "backup_interrupted"] | None = None


class RestoreUpload(BaseModel):
    """An archive received for a restore. The server keeps it for its check (``POST /backup/restore/stage``), then removes
    it; a newer upload replaces it."""

    model_config = ConfigDict(extra="forbid")

    upload_id: str
    size: int = Field(ge=0)


class RestoreStageRequest(BaseModel):
    """Which uploaded archive to check."""

    model_config = ConfigDict(extra="forbid")

    upload_id: str = Field(pattern=r"^[0-9a-f]{32}$")


class RestoreTableRows(BaseModel):
    """The rows of one table of the backup's database, before and after its upgrade; ``None`` where the table is absent."""

    model_config = ConfigDict(extra="forbid")

    before: int | None
    after: int | None


class RestoreMigration(BaseModel):
    """A migration the upgrade of the copy applied: its revision, and the first line of its description."""

    model_config = ConfigDict(extra="forbid")

    revision: str
    message: str


#: Why a check refused an archive, as stable codes (``services/platform/instance_backup/staging.py``), plus
#: ``restore_interrupted`` (the server stopped during the check) and ``restore_folder_unusable`` (``.restore`` is not a
#: plain folder).
RestoreErrorCode = Literal[
    "not_a_backup",
    "archive_unreadable",
    "archive_damaged",
    "manifest_newer_format",
    "manifest_invalid",
    "manifest_unreadable",
    "manifest_too_large",
    "too_many_entries",
    "duplicate_entry",
    "unexpected_entry",
    "not_a_file",
    "encrypted_entry",
    "unsupported_entry",
    "checksum_mismatch",
    "missing_entry",
    "no_space",
    "stage_failed",
    "database_damaged",
    "manifest_mismatch",
    "head_unknown",
    "revision_missing",
    "revision_unknown",
    "upgrade_failed",
    "post_migration_failed",
    "restore_interrupted",
    "restore_folder_unusable",
]


class RestoreStageReport(BaseModel):
    """What a restore of the checked archive would do: what the confirmation shows.

    ``action`` is ``same`` (the backup is at this LibreFolio's revision) or ``upgrade`` (its database was brought to it,
    on the copy, by ``migrations``). ``administrators``: after the restore one signs in with one of them, with the
    password of then. ``warnings`` let the restore go on: ``rows_changed``, ``foreign_key_violations``,
    ``foreign_key_violations_added``. ``blockers`` forbid it: ``no_administrator``. The copy is kept until ``expires_at``.
    """

    model_config = ConfigDict(extra="forbid")

    backup_created_at: datetime
    backup_app_version: str
    backup_origin: Literal["ui", "cli", "pre-restore", "panel"]
    backup_revision: str
    app_version: str
    head_revision: str
    action: Literal["same", "upgrade"]
    migrations: list[RestoreMigration]
    post_migration_fixes: list[str]
    tables: dict[str, RestoreTableRows]
    foreign_key_violations_before: int = Field(ge=0)
    foreign_key_violations_after: int = Field(ge=0)
    files: int = Field(ge=0)
    files_size: int = Field(ge=0)
    database_size: int = Field(ge=0)
    instance_key_included: bool
    administrators: list[str]
    warnings: list[Literal["rows_changed", "foreign_key_violations", "foreign_key_violations_added"]]
    blockers: list[Literal["no_administrator"]]
    restorable: bool
    expires_at: datetime


class RestoreStage(BaseModel):
    """The check of an uploaded archive on a copy, run in the background: poll it until ``status`` is ``done`` (with its
    ``report``) or ``failed`` (with its ``error_code``). ``done_bytes`` of ``total_bytes`` measure the unpacking."""

    model_config = ConfigDict(extra="forbid")

    stage_id: str
    status: Literal["running", "done", "failed"]
    phase: Literal["checking", "unpacking", "upgrading", "verifying"] | None = None
    done_bytes: int = Field(ge=0)
    total_bytes: int = Field(ge=0)
    created_at: datetime
    finished_at: datetime | None = None
    error_code: RestoreErrorCode | None = None
    report: RestoreStageReport | None = None

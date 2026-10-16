"""Schemas of the instance backup: the state of a backup job (``/backup/instance``), and the restore (``/backup/restore``):
the upload of an archive, its check on a copy, the report of what the restore would do, and the restore confirmed for
the next start of the server."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# One-line docstrings without backticks on purpose: the API client generator pastes a model's docstring unescaped into
# the TypeScript client wherever the model types a field, and a text over several lines with backticks breaks it at
# import (E2b; guard `schemas openapi-client-text`, E-5). The detail lives in the comment above each model.


# The job's fields: done_bytes of total_bytes measure the bytes read so far; total_bytes is 0 until the database is
# copied. warnings are stable codes: database_integrity (the database failed its integrity check),
# foreign_key_violations, files_skipped (files that changed or vanished during the backup, left out). error_code:
# backup_no_space, backup_failed (the server log has the cause) or backup_interrupted (the server stopped during the
# backup).
class InstanceBackupJob(BaseModel):
    """A backup of the whole instance, built in the background: poll it until its status is done or failed."""

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
    """An archive received for a restore: kept for its check (POST /backup/restore/stage), then removed; a newer upload replaces it."""

    model_config = ConfigDict(extra="forbid")

    upload_id: str
    size: int = Field(ge=0)


class RestoreStageRequest(BaseModel):
    """Which uploaded archive to check."""

    model_config = ConfigDict(extra="forbid")

    upload_id: str = Field(pattern=r"^[0-9a-f]{32}$")


class RestoreTableRows(BaseModel):
    """The rows of one table of the backup's database, before and after its upgrade; null where the table is absent."""

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


# action is same (the backup is at this LibreFolio's revision) or upgrade (its database was brought to it, on the copy,
# by migrations). administrators: after the restore one signs in with one of them, with the password of then. warnings
# let the restore go on: rows_changed, foreign_key_violations, foreign_key_violations_added. blockers forbid it:
# no_administrator. The copy is kept until expires_at.
class RestoreStageReport(BaseModel):
    """What a restore of the checked archive would do: what the confirmation shows."""

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


# done_bytes of total_bytes measure the unpacking; report comes with done, error_code with failed.
class RestoreStage(BaseModel):
    """The check of an uploaded archive on a copy, run in the background: poll it until its status is done or failed."""

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


# state: pending (confirmed, waiting for the next start of the server), in_progress (being applied by a start), or the
# last one that ended: committed (the restored data is the instance's, every session ended) or rolled_back (the data
# is as it was before; reason: first_start_failed, the first start after it did not complete; swap_interrupted, the
# start that applied it was interrupted; swap_failed, its folders could not be moved into place; stage_missing, its
# checked copy was gone). none: there was none.
# waiting, on a pending restore that a start did not apply: backup_running (a backup was running: the next start
# applies it), other_data_directory (it was confirmed for another data directory, of which this one is a copy) or
# server_running (a server process was serving the data directory: a worker started again under its running siblings,
# or a second server; a start of the whole server applies it). confirmed_by: the administrator's username, or cli.
# upload_limit_mb: the largest archive PUT /backup/restore/upload accepts now, in megabytes (0: no limit), so that a
# file too large is refused before it is sent; null when the limit cannot be read (the upload then answers 503).
class RestoreStatus(BaseModel):
    """The restore of the instance: waiting for the next start of the server, being applied, or the last one that ended."""

    model_config = ConfigDict(extra="forbid")

    state: Literal["none", "pending", "in_progress", "committed", "rolled_back"]
    stage_id: str | None = None
    confirmed_at: datetime | None = None
    confirmed_by: str | None = None
    backup_created_at: datetime | None = None
    backup_app_version: str | None = None
    action: Literal["same", "upgrade"] | None = None
    finished_at: datetime | None = None
    reason: Literal["first_start_failed", "swap_interrupted", "swap_failed", "stage_missing"] | None = None
    waiting: Literal["backup_running", "other_data_directory", "server_running"] | None = None
    upload_limit_mb: int | None = Field(default=None, ge=0)

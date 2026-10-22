"""Schemas of the instance backup: the state of a backup job (``/backup/instance``), and the restore (``/backup/restore``):
the upload of an archive, its check on a copy, the report of what the restore would do, and the restore confirmed for
the next start of the server."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from backend.app.schemas.auth import PasswordRuleRead

# One-line docstrings without backticks on purpose: the API client generator pastes a model's docstring unescaped into
# the TypeScript client wherever the model types a field, and a text over several lines with backticks breaks it at
# import (E2b; guard `schemas openapi-client-text`, E-5). The detail lives in the comment above each model.


# The password of a secure backup (decisions 38, 39, P12): the rules of GET /backup/instance/options; the archive is
# then an .lfbk envelope that only this password opens, and it carries the instance key when LibreFolio generated it.
# Never stored, logged or sent back. No body, or a null password: a plain .zip, as before.
class InstanceBackupRequest(BaseModel):
    """What to back up: with a password, a secure backup."""

    model_config = ConfigDict(extra="forbid")

    password: SecretStr | None = Field(default=None, max_length=1024)


# The rules a secure backup's password must meet: those of the accounts (GET /system/instance), with a longer minimum.
class InstanceBackupOptions(BaseModel):
    """What the Backup tab needs to offer a secure backup."""

    model_config = ConfigDict(extra="forbid")

    password_rules: list[PasswordRuleRead]


# The job's fields: done_bytes of total_bytes measure the bytes read so far (while encrypting, of the archive);
# total_bytes is 0 until the database is copied. warnings are stable codes: database_integrity (the database failed
# its integrity check), foreign_key_violations, files_skipped (files that changed or vanished during the backup, left
# out), instance_key_unusable (a secure backup left out the instance key, which cannot be used). encrypted: a secure
# backup, an .lfbk envelope. file_sha256: the SHA-256 of the archive the download serves, 64 lowercase hex digits, once
# done (L3: a hosting panel compares it with what it downloaded). instance_key_included: the archive carries the instance
# key (a secure backup, when LibreFolio generated the key; never a hosting panel's). error_code: backup_no_space,
# backup_failed (the server log has the cause) or backup_interrupted (the server stopped during the backup).
class InstanceBackupJob(BaseModel):
    """A backup of the whole instance, built in the background: poll it until its status is done or failed."""

    model_config = ConfigDict(extra="forbid")

    job_id: str
    status: Literal["running", "done", "failed"]
    phase: Literal["preparing", "database", "files", "finalizing", "encrypting"] | None = None
    done_bytes: int = Field(ge=0)
    total_bytes: int = Field(ge=0)
    created_at: datetime
    finished_at: datetime | None = None
    file_name: str | None = None
    file_size: int | None = Field(default=None, ge=0)
    file_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    warnings: list[Literal["database_integrity", "foreign_key_violations", "files_skipped", "instance_key_unusable"]] = []
    error_code: Literal["backup_no_space", "backup_failed", "backup_interrupted"] | None = None
    encrypted: bool
    instance_key_included: bool = False


# kind: envelope for a secure backup (.lfbk), whose check needs its password; zip otherwise.
class RestoreUpload(BaseModel):
    """An archive received for a restore: kept for its check (POST /backup/restore/stage), then removed; a newer upload replaces it."""

    model_config = ConfigDict(extra="forbid")

    upload_id: str
    size: int = Field(ge=0)
    kind: Literal["zip", "envelope"]


# password: the password of a secure backup (an envelope), ignored for a zip. Checked at once: a wrong one keeps the
# upload, for another try. Never stored, logged or sent back.
class RestoreStageRequest(BaseModel):
    """Which uploaded archive to check, and the password of a secure one."""

    model_config = ConfigDict(extra="forbid")

    upload_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    password: SecretStr | None = Field(default=None, max_length=1024)


# kind cash: the balance of a broker in a currency; kind quantity: the quantity of an asset at a broker. before is
# the backup's, after the copy's, in J's canonical decimal text; null where the line is absent, that is zero.
class RestoreTotalsDifference(BaseModel):
    """One line of the ledger's control totals that differs between the backup and its upgraded copy."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["cash", "quantity"]
    broker_id: int
    currency: str | None
    asset_id: int | None
    before: str | None
    after: str | None


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
#: plain folder). ``instance_key_invalid`` comes only from ``dev.py backup restore --instance-key-file`` (B-18): the API
#: gives a check no key, but the list stays the whole set ``stage_archive`` can raise.
RestoreErrorCode = Literal[
    "not_a_backup",
    "archive_unreadable",
    "archive_damaged",
    "manifest_newer_format",
    "manifest_invalid",
    "manifest_unreadable",
    "manifest_too_large",
    "too_many_entries",
    "unpacked_too_large",
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
    "database_foreign_objects",
    "manifest_mismatch",
    "head_unknown",
    "revision_missing",
    "revision_unknown",
    "upgrade_failed",
    "post_migration_failed",
    "restore_interrupted",
    "restore_folder_unusable",
    "password_required",
    "envelope_damaged",
    "instance_key_invalid",
    "sealed_backup_needs_key",
]


class RestoreSecretCounts(BaseModel):
    """Saved plugin secrets, by scope: the instance's settings and the users' own."""

    model_config = ConfigDict(extra="forbid")

    system: int = Field(ge=0)
    user: int = Field(ge=0)


# action is same (the backup is at this LibreFolio's revision) or upgrade (its database was brought to it, on the copy,
# by migrations). administrators: after the restore one signs in with one of them, with the password of then. warnings
# let the restore go on: rows_changed, foreign_key_violations, foreign_key_violations_added, and non_iso_currencies
# (E-19b1: the copy holds currency values an earlier version saved that are not ISO 4217 codes, such as 978 or EURO; an
# edit that saves their rows is refused until they are corrected); credentials_from_backup, always, last of the check's
# own (after the restore one signs in with the backup's credentials, and every session open now ends); and
# confirming_account_not_in_backup, added for the administrator who reads the report when their username is not among
# administrators (after the restart they cannot sign in with it; L3). blockers forbid it:
# no_administrator. The copy is kept until expires_at. encrypted: a secure backup. secrets_rekeyed: the plugin secrets
# re-encrypted with this instance's key (a secure backup carries its own); secrets_unreadable: those that stay
# unreadable, to enter again after the restore (another instance's, without its key).
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
    encrypted: bool
    secrets_rekeyed: int = Field(ge=0)
    secrets_unreadable: RestoreSecretCounts
    administrators: list[str]
    warnings: list[
        Literal[
            "rows_changed",
            "foreign_key_violations",
            "foreign_key_violations_added",
            "control_totals_changed",
            "control_totals_unreadable",
            "non_iso_currencies",
            "credentials_from_backup",
            "confirming_account_not_in_backup",
        ]
    ]
    blockers: list[Literal["no_administrator"]]
    control_totals: Literal["same", "changed", "absent", "other_version", "unreadable"]
    control_totals_differences: list[RestoreTotalsDifference]
    control_totals_differences_count: int = Field(ge=0)
    restorable: bool
    expires_at: datetime


# done_bytes of total_bytes measure the unpacking; report comes with done, error_code with failed.
class RestoreStage(BaseModel):
    """The check of an uploaded archive on a copy, run in the background: poll it until its status is done or failed."""

    model_config = ConfigDict(extra="forbid")

    stage_id: str
    status: Literal["running", "done", "failed"]
    phase: Literal["decrypting", "checking", "unpacking", "upgrading", "verifying"] | None = None
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
# applies it), other_data_directory (it was confirmed for another data directory, of which this one is a copy),
# server_running (a server process was serving the data directory: a worker started again under its running siblings,
# or a second server; a start of the whole server applies it) or instance_blocked (the hosting provider blocked the
# instance: the first start after the unblock applies it). confirmed_by: the administrator's username, or cli.
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
    waiting: Literal["backup_running", "other_data_directory", "server_running", "instance_blocked"] | None = None
    upload_limit_mb: int | None = Field(default=None, ge=0)


# The restart accepted (POST /backup/restore/restart, lot B5c): the status, and the one-time ticket with which the page
# reads the outcome once the server is back (GET /backup/restore/outcome), without a session: a restore ends every
# session, and without JWT_SECRET every start does. Valid one hour, one per restart (decision N53), in this answer only.
class RestoreRestartAccepted(RestoreStatus):
    """The restore waiting, and the one-time ticket of its outcome."""

    outcome_ticket: str


# What became of a restore, for the holder of its one-time ticket: only what the restart's page shows, nothing about
# the backup or who confirmed it. state: pending (a start left it waiting: waiting says why; or the server is not
# back yet), in_progress, committed, rolled_back (reason says why).
class RestoreOutcome(BaseModel):
    """The outcome of a restore, read with the ticket its restart gave."""

    model_config = ConfigDict(extra="forbid")

    state: Literal["pending", "in_progress", "committed", "rolled_back"]
    reason: Literal["first_start_failed", "swap_interrupted", "swap_failed", "stage_missing"] | None = None
    waiting: Literal["backup_running", "other_data_directory", "server_running", "instance_blocked"] | None = None

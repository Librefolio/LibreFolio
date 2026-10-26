"""Schemas of the hosting panel's own routes (lots H-61 and H-62): what an instance tells the panel that runs it.

The panel never reads a customer's portfolio nor personal data (contract L3, R1): its views of a restore are closed
lists of fields (``extra="forbid"``), with codes, verdicts and counts only — no username, no amount, no table sizes.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.backup import RestoreMigration, RestoreSecretCounts, RestoreStage, RestoreStageReport, RestoreStatus
from backend.app.schemas.system import InstanceMode

# The field types of the administrator's views (workstream B), reused as they are: a code B adds to a report, a phase or
# a state reaches the panel's views with it, instead of a validation error. Only the choice of fields is the panel's.
_REPORT = RestoreStageReport.model_fields
_STAGE = RestoreStage.model_fields
_STATUS = RestoreStatus.model_fields
_ReportAction = _REPORT["action"].annotation
_ReportBackupOrigin = _REPORT["backup_origin"].annotation
_ReportBlockers = _REPORT["blockers"].annotation
_ReportControlTotals = _REPORT["control_totals"].annotation
_ReportWarnings = _REPORT["warnings"].annotation
_StageErrorCode = _STAGE["error_code"].annotation
_StagePhase = _STAGE["phase"].annotation
_StageStatus = _STAGE["status"].annotation
_StatusAction = _STATUS["action"].annotation
_StatusConfirmedVia = _STATUS["confirmed_via"].annotation
_StatusReason = _STATUS["reason"].annotation
_StatusState = _STATUS["state"].annotation
_StatusWaiting = _STATUS["waiting"].annotation


class PanelRestoreSummary(BaseModel):
    """The restore of the instance, in ``GET /panel/status``: its state and why it waits, without who confirmed it.
    ``unreadable`` (D7): the state of the restore cannot be read, ``reason`` then says why (``io``, ``not_a_file``,
    ``invalid``), and the instance serves no data until its administrator recovers it."""

    model_config = ConfigDict(extra="forbid")

    state: _StatusState | Literal["unreadable"]
    reason: _StatusReason | Literal["io", "not_a_file", "invalid"] = None
    waiting: _StatusWaiting = None
    backup_created_at: datetime | None = None
    stage_id: str | None = None


class PanelStatusResponse(BaseModel):
    """``GET /api/v1/panel/status``: the state of the initial administrator's setup, the instance's mode and restore, how
    many places its users take, and where a change of the owner's address stands.

    No email, no username: the panel learns whether the customer has activated the instance, until when the setup link
    works, two counts (``users_used``, ``users_limit``) and whether the owner's new address waits for its confirmation
    (``owner_email_change``), and whether the instance key is the one its data was written with (``instance_key``), never who the users
    are, an address nor the key's check value.
    """

    model_config = ConfigDict(extra="forbid")

    admin_setup: Literal["none", "pending", "done", "expired"] = Field(
        ...,
        description="none: no setup link was ever issued, or its account no longer exists; pending: a link works; done: the setup was completed, or the account was activated another way; expired: the link expired after 72 hours, or was withdrawn",
    )
    setup_expires_at: datetime | None = Field(None, description="When the pending link stops working, in UTC; null in every other state")
    mode: InstanceMode = Field("normal", description="normal, or awaiting_restore while the instance waits for the panel to restore its data (H-62)")
    restore: PanelRestoreSummary | None = Field(None, description="The restore of the instance: waiting, being applied, or the last one that ended; null when none was ever recorded")
    users_used: int = Field(..., ge=0, description="The places the users take: active accounts, live invitations and the inactive accounts that wait for their email verification or their setup, each counted once. A count, never who")
    users_limit: int | None = Field(None, ge=1, description="How many places the instance may hold (`LIBREFOLIO_MAX_USERS`); null when there is no limit")
    owner_email_change: Literal["pending", "blocked"] | None = Field(
        None,
        description="The change of the paying administrator's email address that the hosting provider started by changing LIBREFOLIO_ADMIN_EMAIL: pending, the new address was sent a confirmation link and the account keeps the old one until it is clicked; blocked, another account already holds the new address, so nothing changes (change the variable again to a free address); null, no change is waiting, or the instance is not managed, or its initial administrator has not set up yet. Never the address",
    )
    instance_key: Literal["ok", "mismatch"] = Field(
        ...,
        description="ok: the instance key is the one this instance's data was written with, or nothing can tell (no key yet, a check file that cannot be read); mismatch: it is another key, so the panel's backup jobs (409 backup_instance_key_mismatch) and wake-sync are stopped while the instance keeps serving. Recomputed at every request: the right key put back is ok at the next one. Never the key nor its check value (H5-7)",
    )


class PanelRestoreStageReport(BaseModel):
    """What a restore of the checked archive would do, as the panel sees it (contract L3 §5, R1): the admin's report
    without its personal or portfolio data — the administrators become their count, the totals their verdict and the
    number of differences, and the tables, files and sizes are left out."""

    model_config = ConfigDict(extra="forbid")

    backup_created_at: datetime
    backup_app_version: str
    backup_origin: _ReportBackupOrigin
    backup_revision: str
    app_version: str
    head_revision: str
    action: _ReportAction
    migrations: list[RestoreMigration]
    post_migration_fixes: list[str]
    instance_key_included: bool
    encrypted: bool
    secrets_rekeyed: int = Field(ge=0)
    secrets_unreadable: RestoreSecretCounts
    warnings: _ReportWarnings
    blockers: _ReportBlockers
    control_totals: _ReportControlTotals
    control_totals_differences_count: int = Field(ge=0)
    restorable: bool
    expires_at: datetime
    administrators_count: int = Field(ge=0, description="How many administrators the backup holds: never their names")

    @classmethod
    def of(cls, report: RestoreStageReport) -> "PanelRestoreStageReport":
        """The panel's view of an administrator's report: the closed list of fields, the names counted."""
        kept = report.model_dump(include=set(cls.model_fields) - {"administrators_count"})
        return cls(**kept, administrators_count=len(report.administrators))


class PanelRestoreStage(BaseModel):
    """The check of the panel's upload on a copy, run in the background: poll it until its status is done or failed."""

    model_config = ConfigDict(extra="forbid")

    stage_id: str
    status: _StageStatus
    phase: _StagePhase = None
    done_bytes: int = Field(ge=0)
    total_bytes: int = Field(ge=0)
    created_at: datetime
    finished_at: datetime | None = None
    error_code: _StageErrorCode = None
    report: PanelRestoreStageReport | None = None


class PanelRestoreStatus(BaseModel):
    """The restore of the instance, as the panel sees it: the administrator's status with ``confirmed_via`` instead of
    the username of who confirmed it."""

    model_config = ConfigDict(extra="forbid")

    state: _StatusState
    stage_id: str | None = None
    confirmed_at: datetime | None = None
    confirmed_via: _StatusConfirmedVia = None
    backup_created_at: datetime | None = None
    backup_app_version: str | None = None
    action: _StatusAction = None
    finished_at: datetime | None = None
    reason: _StatusReason = None
    waiting: _StatusWaiting = None
    upload_limit_mb: int | None = Field(default=None, ge=0)

    @classmethod
    def of(cls, status: RestoreStatus) -> "PanelRestoreStatus":
        """The panel's view of an administrator's status: everything but the username."""
        return cls(**status.model_dump(exclude={"confirmed_by"}))

"""Schemas of the hosting panel's own routes (lots H-61 and H-62): what an instance tells the panel that runs it.

The panel never reads a customer's portfolio nor personal data (contract L3, R1): its views of a restore are closed
lists of fields (``extra="forbid"``), with codes, verdicts and counts only — no username, no amount, no table sizes.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.backup import RestoreErrorCode, RestoreMigration, RestoreSecretCounts, RestoreStageReport, RestoreStatus
from backend.app.schemas.system import InstanceMode

#: Who confirmed a restore, without a name.
ConfirmedVia = Literal["admin", "cli", "panel"]


class PanelRestoreSummary(BaseModel):
    """The restore of the instance, in ``GET /panel/status``: its state and why it waits, without who confirmed it."""

    model_config = ConfigDict(extra="forbid")

    state: Literal["none", "pending", "in_progress", "committed", "rolled_back"]
    reason: Literal["first_start_failed", "swap_interrupted", "swap_failed", "stage_missing"] | None = None
    waiting: Literal["backup_running", "other_data_directory", "server_running", "instance_blocked"] | None = None
    backup_created_at: datetime | None = None
    stage_id: str | None = None


class PanelStatusResponse(BaseModel):
    """``GET /api/v1/panel/status``: the state of the initial administrator's setup, and nothing else.

    No email, no username, no count: the panel learns whether the customer has activated the instance, and until when
    the setup link works.
    """

    model_config = ConfigDict(extra="forbid")

    admin_setup: Literal["none", "pending", "done", "expired"] = Field(
        ...,
        description="none: no setup link was ever issued, or its account no longer exists; pending: a link works; done: the setup was completed, or the account was activated another way; expired: the link expired after 72 hours, or was withdrawn",
    )
    setup_expires_at: datetime | None = Field(None, description="When the pending link stops working, in UTC; null in every other state")
    mode: InstanceMode = Field("normal", description="normal, or awaiting_restore while the instance waits for the panel to restore its data (H-62)")
    restore: PanelRestoreSummary | None = Field(None, description="The restore of the instance: waiting, being applied, or the last one that ended; null when none was ever recorded")


class PanelRestoreStageReport(BaseModel):
    """What a restore of the checked archive would do, as the panel sees it (contract L3 §5, R1): the admin's report
    without its personal or portfolio data — the administrators become their count, the totals their verdict and the
    number of differences, and the tables, files and sizes are left out."""

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
    instance_key_included: bool
    encrypted: bool
    secrets_rekeyed: int = Field(ge=0)
    secrets_unreadable: RestoreSecretCounts
    warnings: list[Literal["rows_changed", "foreign_key_violations", "foreign_key_violations_added", "control_totals_changed", "control_totals_unreadable", "non_iso_currencies"]]
    blockers: list[Literal["no_administrator"]]
    control_totals: Literal["same", "changed", "absent", "other_version", "unreadable"]
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
    status: Literal["running", "done", "failed"]
    phase: Literal["decrypting", "checking", "unpacking", "upgrading", "verifying"] | None = None
    done_bytes: int = Field(ge=0)
    total_bytes: int = Field(ge=0)
    created_at: datetime
    finished_at: datetime | None = None
    error_code: RestoreErrorCode | None = None
    report: PanelRestoreStageReport | None = None


class PanelRestoreStatus(BaseModel):
    """The restore of the instance, as the panel sees it: the administrator's status with ``confirmed_via`` instead of
    the username of who confirmed it."""

    model_config = ConfigDict(extra="forbid")

    state: Literal["none", "pending", "in_progress", "committed", "rolled_back"]
    stage_id: str | None = None
    confirmed_at: datetime | None = None
    confirmed_via: ConfirmedVia | None = None
    backup_created_at: datetime | None = None
    backup_app_version: str | None = None
    action: Literal["same", "upgrade"] | None = None
    finished_at: datetime | None = None
    reason: Literal["first_start_failed", "swap_interrupted", "swap_failed", "stage_missing"] | None = None
    waiting: Literal["backup_running", "other_data_directory", "server_running", "instance_blocked"] | None = None
    upload_limit_mb: int | None = Field(default=None, ge=0)

    @classmethod
    def of(cls, status: RestoreStatus, confirmed_via: ConfirmedVia | None) -> "PanelRestoreStatus":
        """The panel's view of an administrator's status: everything but the username."""
        return cls(**status.model_dump(exclude={"confirmed_by"}), confirmed_via=confirmed_via)

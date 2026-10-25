"""System information and diagnostics schemas."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import Field, RootModel, model_validator

from backend.app.schemas.auth import AccountsInstanceConfig
from backend.app.schemas.common import StrictModel
from backend.app.schemas.email import EmailInstanceConfig
from backend.app.utils.runtime.network import ClientClass

#: ``normal``, or ``awaiting_restore`` while ``LIBREFOLIO_AWAIT_RESTORE`` is on (lot H-62, contract L3 §6).
InstanceMode = Literal["normal", "awaiting_restore"]


class DependencyInfo(StrictModel):
    """Information about a dependency."""

    name: str
    version: str


class SystemInfoResponse(StrictModel):
    """``GET /system/info`` with a valid session: versions of the app, Python, the OS and the dependencies."""

    app_version: str
    python_version: str
    os_name: str
    os_version: str
    platform: str
    deployment_mode: str
    backend_dependencies: list[DependencyInfo]
    frontend_dependencies: list[DependencyInfo]


class SystemInfoPublicResponse(StrictModel):
    """``GET /system/info`` without a valid session: the app version, nothing else."""

    app_version: str


class PluginDiscoveryFailureInfo(StrictModel):
    """One failed plugin module import discovered at startup/runtime."""

    system: str = Field(..., description="Plugin system that attempted discovery")
    filename: str = Field(..., description="Python module filename that failed to load")
    error: str = Field(..., description="Import error type and message")


class PluginDiagnosticsResponse(RootModel[list[PluginDiscoveryFailureInfo]]):
    """Plugin discovery diagnostics as a flat failure list."""


class HealthCheckResponse(StrictModel):
    """Health check response."""

    status: str = Field(..., description="Service status ('ok' when the service is healthy)")


ReadinessDatabaseState = Literal["ok", "unreachable"]
ReadinessMigrationsState = Literal["ok", "behind", "ahead", "unknown"]


class ReadinessChecks(StrictModel):
    """One code per readiness check: never an error message, a path or a revision id."""

    database: ReadinessDatabaseState = Field(description="ok: the database answers a query; unreachable: it does not")
    migrations: ReadinessMigrationsState = Field(
        description=(
            "ok: the database schema is at the head revision of the migrations; "
            "behind: it is at an older revision this version knows, a migration was not applied or failed; "
            "ahead: it is at a revision this version does not know, the database is newer than the image; "
            "unknown: the revision of the database or of the migrations cannot be read"
        )
    )


class ReadinessResponse(StrictModel):
    """``GET /system/ready``: whether this instance can serve requests, with status 200 when ready and 503 otherwise.

    Public by design, for health checks and orchestrators: the body carries one code per check, the mode and the
    database's migration revision, and nothing else: never an error message or a path.
    """

    status: Literal["ready", "not_ready"] = Field(description="ready when every check is ok")
    checks: ReadinessChecks
    database_revision: str | None = Field(default=None, description="The revision the database's migrations stand at (the one row of alembic_version), to tell a database behind or ahead of this version; null when it cannot be read")
    mode: InstanceMode = Field(default="normal", description="normal, or awaiting_restore while the hosting panel restores the instance (H-62): ready then means ready to receive the backup")


class ContainerImageStatusResponse(StrictModel):
    """Availability of one normalized LibreFolio container image tag."""

    status: Literal["published", "pending", "error"]
    reason: Literal["image-auth-request-failed", "image-request-failed"] | None = None

    @model_validator(mode="after")
    def validate_reason(self) -> ContainerImageStatusResponse:
        if (self.status == "error") != (self.reason is not None):
            raise ValueError("reason must be set exactly when status is error")
        return self


class ConnectionSecurityResponse(StrictModel):
    """How the server sees the current request, for the connection-security indicator."""

    client_class: ClientClass = Field(
        ...,
        description="Class of the client address: the last X-Forwarded-For value when present, else the TCP peer. Advisory only; the address itself is never returned",
    )
    cookie_secure: bool = Field(..., description="Whether the session cookie set or cleared on this request carries the Secure attribute (SESSION_COOKIE_SECURE)")


InstanceProfile = Literal["selfhosted", "managed"]


class LegalInstanceConfig(StrictModel):
    """The legal part of ``GET /system/instance`` (F09, workstream A): the instance's own legal pages, public."""

    # One-line docstring on purpose (see EmailInstanceConfig). Both null: the instance links no page of its own, and the
    # legal notice shows alone.
    terms_url: str | None = Field(default=None, description="The terms of service of the instance (LIBREFOLIO_TOS_URL): an http(s) page; null when it is not set or not valid")
    privacy_url: str | None = Field(default=None, description="The privacy policy of the instance (LIBREFOLIO_PRIVACY_URL): an http(s) page; null when it is not set or not valid")


class InstanceConfigResponse(StrictModel):
    """``GET /system/instance``: what the app needs to know about this instance before anyone signs in.

    Public by design: every field is the same for whoever asks, and nothing private goes here. A workstream that owns
    part of the public configuration adds one field, typed with a model of its own schemas, and fills it in
    ``api/v1/system/instance.py`` with one call to its service.
    """

    profile: InstanceProfile = Field(description="selfhosted: an install run by its owner; managed: an instance a hosting provider runs for its customers")
    mode: InstanceMode = Field(default="normal", description="normal, or awaiting_restore while the hosting panel restores the instance (H-62): every API route but a few answers 423 `instance_awaiting_restore`, and the app shows a waiting page")
    restore_interrupted: bool = Field(default=False, description="True while the state of the instance's restore cannot be read (B-33): it serves no data, every API route but a few answers 423 `instance_restore_interrupted`, and the app shows a page that asks for the administrator")
    restore_interrupted_reason: Literal["restore_state", "owner_assignment"] | None = Field(
        default=None,
        description="Why `restore_interrupted` is true (H5-3): `restore_state` (the state of the restore cannot be read: the administrator recovers it with `backup pending --recover previous`) or `owner_assignment` (the owner of the restored data has no account yet: `backup pending --recover owner`); null otherwise",
    )
    accounts: AccountsInstanceConfig = Field(description="Who may create an account (workstream A)")
    email: EmailInstanceConfig = Field(default_factory=EmailInstanceConfig, description="Whether the instance can send emails (workstream E)")
    support_url: str | None = Field(
        default=None,
        description="Where users ask for help, such as an asset the search does not find (LIBREFOLIO_SUPPORT_URL, workstream H): an http(s) page or mailto: and one email address; null when it is not set or not valid, and the asset search then offers a new issue on the project's GitHub on a self-hosted instance, and no report link on a managed one",
    )
    legal: LegalInstanceConfig = Field(default_factory=LegalInstanceConfig, description="The legal pages of the instance, linked by the legal notice (workstream A)")
    client_log_level: Literal["error", "debug"] = Field(
        default="error",
        description="How much the web app writes to the browser console about failed API calls (workstream H): error, server errors, network failures and answers that break their schema; debug, every 4xx too. debug when the instance's LOG_LEVEL is DEBUG or TRACE",
    )


class InstanceBlockResponse(StrictModel):
    """``GET /system/block``: the block of this instance by its hosting provider, for the block page. Signed-in users only.

    A workstream that owns part of the block page adds one field here, filled in ``api/v1/system/block.py``.
    """

    blocked: bool = Field(description="Whether the hosting provider blocked this instance: then every API call but a few answers 423")
    deletion_date: date | None = Field(default=None, description="The day the hosting provider will delete this instance and its data, when it gave one")
    billing_url: str | None = Field(
        default=None,
        description="Where the hosting provider's customer manages the subscription (LIBREFOLIO_BILLING_URL), for administrators only: null for other users, and when it is not set or not a valid http(s) address",
    )
    backup_available: bool = Field(description="Whether the signed-in user may still download a full backup of the instance, blocked or not: administrators only (decision 12)")

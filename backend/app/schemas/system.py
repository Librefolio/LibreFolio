"""System information and diagnostics schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, RootModel, model_validator

from backend.app.schemas.common import StrictModel


class DependencyInfo(StrictModel):
    """Information about a dependency."""

    name: str
    version: str


class SystemInfoResponse(StrictModel):
    """System information response."""

    app_version: str
    python_version: str
    os_name: str
    os_version: str
    platform: str
    deployment_mode: str
    backend_dependencies: list[DependencyInfo]
    frontend_dependencies: list[DependencyInfo]


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


class ContainerImageStatusResponse(StrictModel):
    """Availability of one normalized LibreFolio container image tag."""

    status: Literal["published", "pending", "error"]
    reason: Literal["image-auth-request-failed", "image-request-failed"] | None = None

    @model_validator(mode="after")
    def validate_reason(self) -> ContainerImageStatusResponse:
        if (self.status == "error") != (self.reason is not None):
            raise ValueError("reason must be set exactly when status is error")
        return self

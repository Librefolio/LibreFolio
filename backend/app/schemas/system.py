"""System information and diagnostics schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, RootModel


class DependencyInfo(BaseModel):
    """Information about a dependency."""

    model_config = ConfigDict(extra="forbid")

    name: str
    version: str


class SystemInfoResponse(BaseModel):
    """System information response."""

    model_config = ConfigDict(extra="forbid")

    app_version: str
    python_version: str
    os_name: str
    os_version: str
    platform: str
    deployment_mode: str
    backend_dependencies: list[DependencyInfo]
    frontend_dependencies: list[DependencyInfo]


class PluginDiscoveryFailureInfo(BaseModel):
    """One failed plugin module import discovered at startup/runtime."""

    model_config = ConfigDict(extra="forbid")

    system: str = Field(..., description="Plugin system that attempted discovery")
    filename: str = Field(..., description="Python module filename that failed to load")
    error: str = Field(..., description="Import error type and message")


class PluginDiagnosticsResponse(RootModel[list[PluginDiscoveryFailureInfo]]):
    """Plugin discovery diagnostics as a flat failure list."""

"""Plugin diagnostics (``GET /system/plugin-diagnostics``): the plugins that fail to load, in every plugin registry."""

from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app.api.v1.auth import get_current_user
from backend.app.db.models import User
from backend.app.schemas.system import PluginDiagnosticsResponse, PluginDiscoveryFailureInfo
from backend.app.services.assets.registry import AssetProviderRegistry
from backend.app.services.brim.registry import BRIMProviderRegistry
from backend.app.services.fx.registry import FXProviderRegistry
from backend.app.services.risk.registry import RiskAnalyticRegistry
from backend.app.services.signals.registry import SignalPluginRegistry
from backend.app.services.tools.registry import ToolPluginRegistry

diagnostics_router = APIRouter()


def _plugin_discovery_failures(system: str, registry) -> list[PluginDiscoveryFailureInfo]:
    return [
        PluginDiscoveryFailureInfo(
            system=system,
            filename=f"{failure.module_name.rsplit('.', 1)[-1]}.py",
            error=f"{failure.error_type}: {failure.message}",
        )
        for failure in registry.get_discovery_errors()
    ]


def _tool_discovery_failures() -> list[PluginDiscoveryFailureInfo]:
    """The Tool registry quarantines services for more reasons than a failed import; its snapshot lists them all.

    The snapshot carries a closed reason and no exception text, so nothing internal reaches the client.
    """
    return [
        PluginDiscoveryFailureInfo(
            system="tools",
            filename=failure.filename,
            error=f"{failure.reason}: {failure.tool_code}" if failure.tool_code else failure.reason,
        )
        for failure in ToolPluginRegistry.get_snapshot().failures
    ]


@diagnostics_router.get("/plugin-diagnostics", response_model=PluginDiagnosticsResponse)
def get_plugin_diagnostics(
    _current_user: Annotated[User, Depends(get_current_user)],
) -> PluginDiagnosticsResponse:
    """Return plugin discovery import failures for all plugin registries.

    Requires a session: the failures carry exception text that can name internal paths.
    """
    return PluginDiagnosticsResponse(
        [
            *_plugin_discovery_failures("asset", AssetProviderRegistry),
            *_plugin_discovery_failures("fx", FXProviderRegistry),
            *_plugin_discovery_failures("brim", BRIMProviderRegistry),
            *_plugin_discovery_failures("signals", SignalPluginRegistry),
            *_plugin_discovery_failures("risk", RiskAnalyticRegistry),
            *_tool_discovery_failures(),
        ]
    )

"""
System API endpoints.

Provides system information, version data, and runtime details.
"""

import json
import platform
import re
import sys
from importlib.metadata import version as pkg_version
from pathlib import Path

from fastapi import APIRouter

from backend.app.config import PROJECT_ROOT
from backend.app.logging_config import get_logger
from backend.app.schemas.system import DependencyInfo, PluginDiagnosticsResponse, PluginDiscoveryFailureInfo, SystemInfoResponse
from backend.app.services.provider_registry import AssetProviderRegistry, BRIMProviderRegistry, FXProviderRegistry, SignalPluginRegistry
from backend.app.utils.version import get_git_version

router = APIRouter(prefix="/system", tags=["System"])
logger = get_logger(__name__)


# Display name mappings for packages
BACKEND_NAME_MAP = {
    "fastapi": "FastAPI",
    "sqlmodel": "SQLModel",
    "sqlalchemy": "SQLAlchemy",
    "beautifulsoup4": "BeautifulSoup4",
    "httpx": "HTTPX",
    "aiosqlite": "aiosqlite",
    "pydantic-settings": "Pydantic Settings",
    "python-dotenv": "python-dotenv",
    "python-dateutil": "python-dateutil",
    "python-multipart": "python-multipart",
    "justetf-scraping": "JustETF Scraping",
    "email-validator": "email-validator",
}

FRONTEND_NAME_MAP = {
    "@sveltejs/kit": "SvelteKit",
    "@sveltejs/adapter-static": "SvelteKit Adapter",
    "@sveltejs/vite-plugin-svelte": "Svelte Vite Plugin",
    "@tailwindcss/postcss": "Tailwind PostCSS",
    "svelte": "Svelte",
    "tailwindcss": "Tailwind CSS",
    "lucide-svelte": "Lucide Icons",
    "svelte-i18n": "svelte-i18n",
    "date-fns": "date-fns",
    "@zodios/core": "Zodios",
}


def get_display_name(pkg_name: str, name_map: dict) -> str:
    """Get display name for a package, falling back to title case."""
    return name_map.get(pkg_name, pkg_name.replace("-", " ").replace("_", " ").title())


def parse_pipfile() -> list[str]:
    """Parse Pipfile to get list of production packages only (from [packages] section)."""
    packages = []
    try:
        pipfile_path = PROJECT_ROOT / "Pipfile"

        if pipfile_path.exists():
            content = pipfile_path.read_text()

            # Find [packages] section only (not [dev-packages])
            in_packages = False
            for line in content.split("\n"):
                line = line.strip()
                if line == "[packages]":
                    in_packages = True
                    continue
                elif line.startswith("[") and in_packages:
                    # Any other section ends [packages]
                    break
                elif in_packages and line and not line.startswith("#"):
                    # Parse package name (before =). Handles both plain
                    # (fastapi = "*") and quoted names, including a stray
                    # trailing space inside the quotes (e.g.
                    # "borsa-italiana-scraping " = {git = ...}).
                    match = re.match(r'^"?([a-zA-Z0-9_-]+)\s*"?\s*=', line)
                    if match:
                        pkg_name = match.group(1).lower()
                        packages.append(pkg_name)
    except Exception as exc:
        # Non-critical diagnostics endpoint: return an empty dependency list on parse/read failures.
        logger.debug("Failed to parse Pipfile dependencies", error=str(exc))
    return packages


def get_backend_deps() -> list[DependencyInfo]:
    """Get backend dependency versions by parsing Pipfile."""
    deps = []
    packages = parse_pipfile()

    for pkg_name in packages:
        try:
            ver = pkg_version(pkg_name)
            display_name = get_display_name(pkg_name, BACKEND_NAME_MAP)
            deps.append(DependencyInfo(name=display_name, version=ver))
        except Exception as exc:
            # Package might be installed under a different distribution name.
            logger.debug("Failed to resolve backend dependency version", package=pkg_name, error=str(exc))
    return deps


def get_frontend_deps() -> list[DependencyInfo]:
    """Get frontend dependency versions from package.json (production deps only)."""
    deps = []

    try:
        package_json_path = PROJECT_ROOT / "frontend" / "package.json"

        if package_json_path.exists():
            with open(package_json_path) as f:
                pkg_data = json.load(f)

            # Collect all deps
            all_deps = {}

            # Production dependencies only
            for dep, version in pkg_data.get("dependencies", {}).items():
                all_deps[dep] = version.lstrip("^~")

            # Key dev dependencies (main frameworks that are relevant)
            key_dev = ["svelte", "@sveltejs/kit", "tailwindcss"]
            for dep in key_dev:
                if dep in pkg_data.get("devDependencies", {}):
                    all_deps[dep] = pkg_data["devDependencies"][dep].lstrip("^~")

            # Convert to list with display names
            for dep, version in all_deps.items():
                display_name = get_display_name(dep, FRONTEND_NAME_MAP)
                deps.append(DependencyInfo(name=display_name, version=version))
    except Exception as exc:
        # Non-critical diagnostics endpoint: return an empty dependency list on parse/read failures.
        logger.debug("Failed to parse frontend package dependencies", error=str(exc))

    return deps


def get_deployment_mode() -> str:
    """Detect whether the app is running inside the Docker image.

    /.dockerenv is created by the Docker runtime itself in every container,
    regardless of base image — the standard, dependency-free way to detect it.
    """
    return "docker" if Path("/.dockerenv").exists() else "local"


@router.get("/info", response_model=SystemInfoResponse)
async def get_system_info() -> SystemInfoResponse:
    """
    Get system information including versions and dependencies.

    Returns app version, Python version, OS details, and dependency versions.
    """
    return SystemInfoResponse(
        app_version=get_git_version(),
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        os_name=platform.system(),
        os_version=platform.release(),
        platform=platform.platform(),
        deployment_mode=get_deployment_mode(),
        backend_dependencies=get_backend_deps(),
        frontend_dependencies=get_frontend_deps(),
    )


def _plugin_discovery_failures(system: str, registry) -> list[PluginDiscoveryFailureInfo]:
    return [
        PluginDiscoveryFailureInfo(
            system=system,
            filename=f"{failure.module_name.rsplit('.', 1)[-1]}.py",
            error=f"{failure.error_type}: {failure.message}",
        )
        for failure in registry.get_discovery_errors()
    ]


@router.get("/plugin-diagnostics", response_model=PluginDiagnosticsResponse)
def get_plugin_diagnostics() -> PluginDiagnosticsResponse:
    """Return plugin discovery import failures for all plugin registries."""
    return PluginDiagnosticsResponse(
        [
            *_plugin_discovery_failures("asset", AssetProviderRegistry),
            *_plugin_discovery_failures("fx", FXProviderRegistry),
            *_plugin_discovery_failures("brim", BRIMProviderRegistry),
            *_plugin_discovery_failures("signals", SignalPluginRegistry),
        ]
    )


@router.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.

    Returns:
        dict: Status message with "ok" status
    """
    return {"status": "ok"}

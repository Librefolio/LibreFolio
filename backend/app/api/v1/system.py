"""
System API endpoints.

Provides system information, version data, and runtime details.
"""

import json
import platform
import re
import sys
from importlib.metadata import version as pkg_version

from fastapi import APIRouter
from pydantic import BaseModel

from backend.app.config import PROJECT_ROOT

router = APIRouter(prefix="/system", tags=["System"])


class DependencyInfo(BaseModel):
    """Information about a dependency."""

    name: str
    version: str


class SystemInfoResponse(BaseModel):
    """System information response."""

    app_version: str
    python_version: str
    os_name: str
    os_version: str
    platform: str
    backend_dependencies: list[DependencyInfo]
    frontend_dependencies: list[DependencyInfo]


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
                    # Parse package name (before =)
                    match = re.match(r"^([a-zA-Z0-9_-]+)\s*=", line)
                    if match:
                        pkg_name = match.group(1).lower()
                        packages.append(pkg_name)
    except Exception:
        pass
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
        except Exception:
            # Package might be installed under different name
            pass
    return deps


def get_frontend_deps() -> list[DependencyInfo]:
    """Get frontend dependency versions from package.json (production deps only)."""
    deps = []

    try:
        package_json_path = PROJECT_ROOT / "frontend" / "package.json"

        if package_json_path.exists():
            with open(package_json_path, "r") as f:
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
    except Exception:
        pass

    return deps


@router.get("/info", response_model=SystemInfoResponse)
async def get_system_info() -> SystemInfoResponse:
    """
    Get system information including versions and dependencies.

    Returns app version, Python version, OS details, and dependency versions.
    """
    return SystemInfoResponse(
        app_version="0.1.0",
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        os_name=platform.system(),
        os_version=platform.release(),
        platform=platform.platform(),
        backend_dependencies=get_backend_deps(),
        frontend_dependencies=get_frontend_deps(),
    )


@router.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.

    Returns:
        dict: Status message with "ok" status
    """
    return {"status": "ok"}

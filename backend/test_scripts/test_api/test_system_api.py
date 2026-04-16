"""
Tests for system API endpoints.

Covers:
- get_display_name: display name mapping and fallback
- parse_pipfile: parsing [packages] section from Pipfile
- get_backend_deps: backend dependency list
- get_frontend_deps: frontend dependency list from package.json
- GET /api/v1/system/info: system info endpoint
"""

import pytest

from backend.app.api.v1.system import (
    get_display_name,
    get_system_info,
    parse_pipfile,
    get_backend_deps,
    get_frontend_deps,
    BACKEND_NAME_MAP,
    FRONTEND_NAME_MAP,
)


class TestGetDisplayName:
    def test_mapped_name(self):
        assert get_display_name("fastapi", BACKEND_NAME_MAP) == "FastAPI"

    def test_mapped_name_frontend(self):
        assert get_display_name("svelte", FRONTEND_NAME_MAP) == "Svelte"

    def test_unmapped_falls_back_to_title(self):
        result = get_display_name("some-unknown-pkg", {})
        assert result == "Some Unknown Pkg"

    def test_unmapped_underscores(self):
        result = get_display_name("my_cool_lib", {})
        assert result == "My Cool Lib"


class TestParsePipfile:
    def test_returns_list(self):
        packages = parse_pipfile()
        assert isinstance(packages, list)

    def test_contains_fastapi(self):
        packages = parse_pipfile()
        assert "fastapi" in packages

    def test_no_dev_packages(self):
        """Should not contain dev-only packages like pytest."""
        packages = parse_pipfile()
        assert "pytest" not in packages

    def test_all_lowercase(self):
        packages = parse_pipfile()
        for pkg in packages:
            assert pkg == pkg.lower(), f"Package name should be lowercase: {pkg}"


class TestGetBackendDeps:
    def test_returns_list(self):
        deps = get_backend_deps()
        assert isinstance(deps, list)
        assert len(deps) > 0

    def test_contains_fastapi(self):
        deps = get_backend_deps()
        names = [d.name for d in deps]
        assert "FastAPI" in names

    def test_deps_have_version(self):
        deps = get_backend_deps()
        for dep in deps:
            assert dep.version, f"Dependency {dep.name} has no version"


class TestGetFrontendDeps:
    def test_returns_list(self):
        deps = get_frontend_deps()
        assert isinstance(deps, list)
        assert len(deps) > 0

    def test_contains_svelte(self):
        deps = get_frontend_deps()
        names = [d.name for d in deps]
        assert "Svelte" in names

    def test_deps_have_version(self):
        deps = get_frontend_deps()
        for dep in deps:
            assert dep.version, f"Dependency {dep.name} has no version"


class TestGetSystemInfoEndpoint:
    """Test the get_system_info async endpoint function directly."""

    @pytest.mark.asyncio
    async def test_returns_system_info(self):
        result = await get_system_info()
        assert result.app_version
        assert result.python_version
        assert result.os_name
        assert len(result.backend_dependencies) > 0
        assert len(result.frontend_dependencies) > 0


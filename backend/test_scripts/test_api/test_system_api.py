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

import backend.app.api.v1.system as system_module
from backend.app.api.v1.system import (
    BACKEND_NAME_MAP,
    FRONTEND_NAME_MAP,
    get_backend_deps,
    get_deployment_mode,
    get_display_name,
    get_frontend_deps,
    get_system_info,
    parse_pipfile,
)


class _FakePath:
    """Minimal stand-in for pathlib.Path(...).exists() used by get_deployment_mode."""

    def __init__(self, exists_value: bool):
        self._exists_value = exists_value

    def __call__(self, *_args, **_kwargs):
        return self

    def exists(self) -> bool:
        return self._exists_value


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

    def test_real_pipfile_contains_quoted_package(self):
        """Regression: Pipfile has '"borsa-italiana-scraping " = {git = ...}' (quoted
        name with a trailing space inside the quotes) which the old plain
        `^([a-zA-Z0-9_-]+)\\s*=` regex could never match."""
        packages = parse_pipfile()
        assert "borsa-italiana-scraping" in packages

    def test_quoted_name_with_trailing_space(self, tmp_path, monkeypatch):
        pipfile = tmp_path / "Pipfile"
        pipfile.write_text(
            "[packages]\n"
            'fastapi = "*"\n'
            '"borsa-italiana-scraping " = {git = "https://example.com/repo.git"}\n'
            "[dev-packages]\n"
            'pytest = "*"\n'
        )
        monkeypatch.setattr(system_module, "PROJECT_ROOT", tmp_path)

        packages = parse_pipfile()

        assert packages == ["fastapi", "borsa-italiana-scraping"]


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

    def test_fallback_display_name_for_unmapped_package(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(system_module, "parse_pipfile", lambda: ["custom-lib"])
        monkeypatch.setattr(system_module, "pkg_version", lambda name: "1.2.3")

        deps = get_backend_deps()

        assert len(deps) == 1
        assert deps[0].name == "Custom Lib"
        assert deps[0].version == "1.2.3"


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


class TestGetDeploymentMode:
    def test_local_when_dockerenv_absent(self, monkeypatch):
        monkeypatch.setattr(system_module, "Path", _FakePath(False))
        assert get_deployment_mode() == "local"

    def test_docker_when_dockerenv_present(self, monkeypatch):
        monkeypatch.setattr(system_module, "Path", _FakePath(True))
        assert get_deployment_mode() == "docker"


class TestGetSystemInfoEndpoint:
    """Test the get_system_info async endpoint function directly."""

    @pytest.mark.asyncio
    async def test_returns_system_info(self):
        result = await get_system_info()
        assert result.app_version
        assert result.python_version
        assert result.os_name
        assert result.deployment_mode in ("local", "docker")
        assert len(result.backend_dependencies) > 0
        assert len(result.frontend_dependencies) > 0

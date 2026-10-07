"""
Tests for system API endpoints.

Covers:
- get_display_name: display name mapping and fallback
- parse_pipfile: parsing [packages] section from Pipfile
- get_backend_deps: backend dependency list
- get_frontend_deps: frontend dependency list from package.json
- GET /api/v1/system/info: system info endpoint
- GET /api/v1/system/plugin-diagnostics: session required (live HTTP), failure-list shape for a logged-in user
"""

from uuid import uuid4

import httpx
import pytest
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

import backend.app.api.v1.system as system_module
from backend.app.api.v1.auth import SESSION_COOKIE_NAME, get_current_user
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
from backend.app.config import TEST_LANE_HEADER, get_settings
from backend.app.schemas.system import PluginDiagnosticsResponse
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import unique_id


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
        pipfile.write_text("[packages]\n" 'fastapi = "*"\n' '"borsa-italiana-scraping " = {git = "https://example.com/repo.git"}\n' "[dev-packages]\n" 'pytest = "*"\n')
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


class TestTestLaneHealth:
    @staticmethod
    def assert_generic_not_found(error: HTTPException, *hidden_values: str):
        assert error.status_code == 404
        assert error.detail == "Not Found"
        rendered_error = f"{error.detail} {error.headers}"
        assert "test-lane-health" not in rendered_error
        for hidden_value in hidden_values:
            assert hidden_value not in rendered_error

    def test_exact_token_is_accepted_in_test_mode(self, monkeypatch):
        lane_id = "0123456789abcdef0123456789abcdef"
        monkeypatch.setenv("LIBREFOLIO_TEST_LANE_ID", lane_id)
        monkeypatch.setattr(system_module, "is_test_mode", lambda: True)

        response = system_module.test_lane_health(lane_id)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 200
        assert response.body == b'{"status":"ok"}'
        assert response.headers[TEST_LANE_HEADER] == lane_id

    def test_wrong_token_is_generic_not_found(self, monkeypatch):
        lane_id = "0123456789abcdef0123456789abcdef"
        wrong_token = "fedcba9876543210fedcba9876543210"
        monkeypatch.setenv("LIBREFOLIO_TEST_LANE_ID", lane_id)
        monkeypatch.setattr(system_module, "is_test_mode", lambda: True)

        with pytest.raises(HTTPException) as exc_info:
            system_module.test_lane_health(wrong_token)

        self.assert_generic_not_found(
            exc_info.value,
            lane_id,
            wrong_token,
        )

    def test_missing_lane_context_is_generic_not_found(self, monkeypatch):
        supplied_token = "0123456789abcdef0123456789abcdef"
        monkeypatch.delenv("LIBREFOLIO_TEST_LANE_ID", raising=False)
        monkeypatch.setattr(system_module, "is_test_mode", lambda: True)

        with pytest.raises(HTTPException) as exc_info:
            system_module.test_lane_health(supplied_token)

        self.assert_generic_not_found(exc_info.value, supplied_token)

    def test_production_mode_is_generic_not_found_for_exact_token(
        self,
        monkeypatch,
    ):
        lane_id = "0123456789abcdef0123456789abcdef"
        monkeypatch.setenv("LIBREFOLIO_TEST_LANE_ID", lane_id)
        monkeypatch.setattr(system_module, "is_test_mode", lambda: False)

        with pytest.raises(HTTPException) as exc_info:
            system_module.test_lane_health(lane_id)

        self.assert_generic_not_found(exc_info.value, lane_id)


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


# ============================================================================
# GET /api/v1/system/plugin-diagnostics — real HTTP on the lane's shared backend
# ============================================================================
#
# The diagnostics carry the text of plugin import exceptions, which can name
# internal paths. The route is not among the public endpoints listed in
# mkdocs_src/docs/developer/architecture/security.md, so it belongs behind the
# session gate, like its sibling container-image-status. Only FastAPI resolves
# that dependency: these tests talk HTTP instead of calling the handler.

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
PLUGIN_DIAGNOSTICS_URL = f"{API_BASE}/system/plugin-diagnostics"
TIMEOUT = 30
PASSWORD = "PluginDiagPass123!"
#: The ``system`` label get_plugin_diagnostics gives each registry it reads.
PLUGIN_SYSTEMS = {"asset", "fx", "brim", "signals"}


@pytest.fixture(scope="module")
def test_server():
    """Attach to the runner-owned backend, or start its in-process test server."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


async def _login_own_regular_user(client: httpx.AsyncClient) -> None:
    """Register an account of this test's own and put its session on ``client``.

    The first account of an empty database becomes admin (``auth.register``);
    registering again then yields the ordinary user the Settings → About tab is
    served to. That bootstrap admin, if created, cannot delete itself as sole
    admin; a populated lane never takes the branch.
    """

    async def register() -> tuple[str, bool]:
        username = f"{unique_id('plugdiag')}_{uuid4().hex[:8]}"
        response = await client.post(
            f"{API_BASE}/auth/register",
            json={"username": username, "email": f"{username}@example.com", "password": PASSWORD},
            timeout=TIMEOUT,
        )
        assert response.status_code == 201, response.text
        return username, response.json()["user"]["is_superuser"]

    username, is_admin = await register()
    if is_admin:
        username, is_admin = await register()
    assert is_admin is False

    login = await client.post(f"{API_BASE}/auth/login", json={"username": username, "password": PASSWORD}, timeout=TIMEOUT)
    assert login.status_code == 200, login.text
    token = login.cookies.get(SESSION_COOKIE_NAME)
    assert token, f"login set no {SESSION_COOKIE_NAME!r} cookie"
    client.cookies.set(SESSION_COOKIE_NAME, token)
    # Post-condition: the gate accepts this client as that user. Without it, today's
    # open route would answer 200 even to a client whose session never worked.
    me = await client.get(f"{API_BASE}/auth/me", timeout=TIMEOUT)
    assert me.status_code == 200 and me.json()["user"]["username"] == username, me.text


def _route_dependency_calls(path: str) -> set:
    """Every callable FastAPI resolves before the handler of GET ``path`` on the system router."""
    route = next((r for r in system_module.router.routes if isinstance(r, APIRoute) and r.path == path and "GET" in r.methods), None)
    assert route is not None, f"GET {path} is not declared on the system router"
    calls, pending = set(), list(route.dependant.dependencies)
    while pending:
        dependant = pending.pop()
        calls.add(dependant.call)
        pending.extend(dependant.dependencies)
    return calls


class TestPluginDiagnosticsRequiresSession:
    """No valid session, no diagnostics; a logged-in user still gets the same list."""

    @staticmethod
    def assert_rejected_by_session_gate(response: httpx.Response, detail: str):
        assert response.status_code == 401, f"plugin-diagnostics answered without a valid session: expected 401, got {response.status_code}: {response.text}"
        # The gate's own error and nothing of the payload: no list, no filename/error fields.
        assert response.json() == {"detail": detail}

    def test_route_depends_on_get_current_user(self):
        """Structural barrier: FastAPI resolves get_current_user before the handler runs."""
        # Control first: the walk finds the gate where it is already declared, so a
        # red on the second assertion is about plugin-diagnostics, not about the walk.
        assert get_current_user in _route_dependency_calls("/system/container-image-status")
        assert get_current_user in _route_dependency_calls("/system/plugin-diagnostics"), "GET /system/plugin-diagnostics resolves no get_current_user: it answers without a session"

    @pytest.mark.asyncio
    async def test_request_without_session_cookie_is_rejected(self, test_server):
        async with httpx.AsyncClient() as client:
            response = await client.get(PLUGIN_DIAGNOSTICS_URL, timeout=TIMEOUT)

        self.assert_rejected_by_session_gate(response, "Not authenticated")

    @pytest.mark.asyncio
    async def test_invalid_session_cookie_is_rejected(self, test_server):
        async with httpx.AsyncClient() as client:
            client.cookies.set(SESSION_COOKIE_NAME, f"forged-{uuid4().hex}")
            response = await client.get(PLUGIN_DIAGNOSTICS_URL, timeout=TIMEOUT)

        # This detail proves the cookie reached the token check: under a wrong
        # cookie name the gate would answer "Not authenticated" instead.
        self.assert_rejected_by_session_gate(response, "Session expired or invalid")

    @pytest.mark.asyncio
    async def test_logged_in_user_gets_the_failure_list(self, test_server):
        async with httpx.AsyncClient() as client:
            await _login_own_regular_user(client)
            try:
                response = await client.get(PLUGIN_DIAGNOSTICS_URL, timeout=TIMEOUT)
            finally:
                # The account is this test's only write; a regular user may delete itself.
                deleted = await client.delete(f"{API_BASE}/auth/users/me", timeout=TIMEOUT)

        assert response.status_code == 200, f"a logged-in user must still get the diagnostics: {response.status_code} {response.text}"
        body = response.json()
        # Shape unchanged by the gate. The lane may legitimately have discovery
        # failures, so neither emptiness nor a length is asserted.
        assert isinstance(body, list), body
        PluginDiagnosticsResponse.model_validate(body)
        for failure in body:
            assert set(failure) == {"system", "filename", "error"}, failure
            assert failure["system"] in PLUGIN_SYSTEMS, failure
        assert deleted.status_code == 200, f"could not delete this test's own account: {deleted.status_code} {deleted.text}"

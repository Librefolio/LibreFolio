"""
Tests for system API endpoints.

Covers:
- get_display_name: display name mapping and fallback
- parse_pipfile: parsing [packages] section from Pipfile
- get_backend_deps: backend dependency list
- get_frontend_deps: frontend dependency list from package.json
- GET /api/v1/system/info: the app version for anyone, everything with a valid session; signed_in_user reads a 401 of
  get_current_user as anonymous and lets any other refusal through; live, direct, and its OpenAPI 200 (full answer first)
- the /system router split one module per resource (C2): the routes of system.py, in their order; /system/ready after them,
  /system/block last, after /system/ready (CP6)
- GET /api/v1/system/plugin-diagnostics: session required (live HTTP), failure-list shape for a logged-in user
- classify_ip / client_address (utils/runtime/network.py): the class of a client address, and which address (plan 36, §2.1)
- GET /api/v1/system/connection: session required, {client_class, cookie_secure} live and in-process (plan 36, §2.1)
- GET /api/v1/system/instance: public, no session; {profile, accounts, email, support_url, legal, client_log_level} live (the lane's default profile,
  no support address) and in-process (a profile set, a support address set); accounts.first_account_open a boolean,
  optional and false unless set (A6d); accounts.password_rules the backend's password rules, the same on every instance
  (A6c, decision 37); support_url what support_link() publishes, null unless LIBREFOLIO_SUPPORT_URL is an http(s) page
  or mailto: and one address (CP13); client_log_level (D4, H-60) live "debug", as every test lane runs at DEBUG
  (dev.py server --test sets LIBREFOLIO_LOG_LEVEL=DEBUG), its mapping pinned in process in
  test_services/test_server_errors.py
- GET /api/v1/system/ready: public, no session; ready live (the lane's migrated database), 503 with the same body
  in-process, 200 and 503 in OpenAPI
"""

import os
from collections.abc import AsyncIterator
from typing import Optional
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.routing import iter_route_contexts

import backend.app.api.v1.auth as auth_module
import backend.app.api.v1.system as system_module
import backend.app.api.v1.system.health as health_module
import backend.app.api.v1.system.info as info_module
import backend.app.api.v1.system.ready as ready_module
from backend.app.api.v1.auth import SESSION_COOKIE_NAME, get_current_user
from backend.app.api.v1.system.connection import get_connection_security
from backend.app.api.v1.system.info import (
    BACKEND_NAME_MAP,
    FRONTEND_NAME_MAP,
    get_backend_deps,
    get_deployment_mode,
    get_display_name,
    get_frontend_deps,
    get_system_info,
    parse_pipfile,
    signed_in_user,
)
from backend.app.config import TEST_LANE_HEADER, get_settings
from backend.app.db.models import User
from backend.app.db.session import get_session_generator
from backend.app.schemas.auth import AccountsInstanceConfig
from backend.app.schemas.system import PluginDiagnosticsResponse, ReadinessChecks, ReadinessResponse, SystemInfoPublicResponse, SystemInfoResponse
from backend.app.services.platform import instance_links
from backend.app.utils.runtime.network import classify_ip, client_address
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success, unique_id


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
        monkeypatch.setattr(info_module, "PROJECT_ROOT", tmp_path)

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
        monkeypatch.setattr(info_module, "parse_pipfile", lambda: ["custom-lib"])
        monkeypatch.setattr(info_module, "pkg_version", lambda name: "1.2.3")

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
        monkeypatch.setattr(info_module, "Path", _FakePath(False))
        assert get_deployment_mode() == "local"

    def test_docker_when_dockerenv_present(self, monkeypatch):
        monkeypatch.setattr(info_module, "Path", _FakePath(True))
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
        monkeypatch.setattr(health_module, "is_test_mode", lambda: True)

        response = health_module.test_lane_health(lane_id)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 200
        assert response.body == b'{"status":"ok"}'
        assert response.headers[TEST_LANE_HEADER] == lane_id

    def test_wrong_token_is_generic_not_found(self, monkeypatch):
        lane_id = "0123456789abcdef0123456789abcdef"
        wrong_token = "fedcba9876543210fedcba9876543210"
        monkeypatch.setenv("LIBREFOLIO_TEST_LANE_ID", lane_id)
        monkeypatch.setattr(health_module, "is_test_mode", lambda: True)

        with pytest.raises(HTTPException) as exc_info:
            health_module.test_lane_health(wrong_token)

        self.assert_generic_not_found(
            exc_info.value,
            lane_id,
            wrong_token,
        )

    def test_missing_lane_context_is_generic_not_found(self, monkeypatch):
        supplied_token = "0123456789abcdef0123456789abcdef"
        monkeypatch.delenv("LIBREFOLIO_TEST_LANE_ID", raising=False)
        monkeypatch.setattr(health_module, "is_test_mode", lambda: True)

        with pytest.raises(HTTPException) as exc_info:
            health_module.test_lane_health(supplied_token)

        self.assert_generic_not_found(exc_info.value, supplied_token)

    def test_production_mode_is_generic_not_found_for_exact_token(
        self,
        monkeypatch,
    ):
        lane_id = "0123456789abcdef0123456789abcdef"
        monkeypatch.setenv("LIBREFOLIO_TEST_LANE_ID", lane_id)
        monkeypatch.setattr(health_module, "is_test_mode", lambda: False)

        with pytest.raises(HTTPException) as exc_info:
            health_module.test_lane_health(lane_id)

        self.assert_generic_not_found(exc_info.value, lane_id)


class TestGetSystemInfoEndpoint:
    """get_system_info called directly: everything for a signed-in user, the app version only for anyone else."""

    def test_a_signed_in_user_gets_everything(self):
        result = get_system_info(_any_user())

        assert isinstance(result, SystemInfoResponse), f"a signed-in user gets the full answer: {result!r}"
        assert result.app_version
        assert result.python_version
        assert result.os_name
        assert result.deployment_mode in ("local", "docker")
        assert len(result.backend_dependencies) > 0
        assert len(result.frontend_dependencies) > 0

    def test_anyone_else_gets_the_app_version_only(self, monkeypatch):
        """No user: the app version, and nothing else is even read."""
        read = []
        monkeypatch.setattr(info_module, "get_git_version", lambda: "v1.2.3-probe")
        for reader in ("get_backend_deps", "get_frontend_deps", "get_deployment_mode"):
            monkeypatch.setattr(info_module, reader, lambda reader=reader: read.append(reader))

        result = get_system_info(None)

        assert isinstance(result, SystemInfoPublicResponse), f"without a user the answer is the public one: {result!r}"
        assert result.model_dump() == {"app_version": "v1.2.3-probe"}, f"the app version and nothing else: {result.model_dump()}"
        assert read == [], f"without a user only the version is read, not {read}"


# ============================================================================
# THE /system ROUTER, ONE MODULE PER RESOURCE (rule C2)
# ============================================================================
#
# system.py became the package api/v1/system/, whose __init__.py composes one router per
# resource. The composition must register the routes as the single module did: the
# registration order is the order of the OpenAPI document and the order routes are tried
# in. A route added after the split comes after these six, so the pin is on the first six.

#: The routes of the single system.py, in registration order, each with the endpoint that serves it now,
#: as <module>.<function> under backend.app.api.v1.system.
SYSTEM_ROUTES_OF_THE_SPLIT = [
    ("/system/info", "info.get_system_info"),
    ("/system/plugin-diagnostics", "diagnostics.get_plugin_diagnostics"),
    ("/system/container-image-status", "container_image.get_container_image_status"),
    ("/system/connection", "connection.get_connection_security"),
    ("/system/health", "health.health_check"),
    ("/system/test-lane-health", "health.test_lane_health"),
]


def test_the_split_keeps_the_routes_of_system_py_in_their_order():
    """C2: the composed router registers the six routes of system.py first, in their order, each a GET of the System tag served by its resource's module."""
    contexts = list(iter_route_contexts(system_module.router.routes))[: len(SYSTEM_ROUTES_OF_THE_SPLIT)]
    served = [(ctx.path, f"{getattr(ctx.endpoint, '__module__', '?').removeprefix(system_module.__name__ + '.')}.{getattr(ctx.endpoint, '__name__', '?')}") for ctx in contexts]
    assert served == SYSTEM_ROUTES_OF_THE_SPLIT, f"the first routes of the /system router changed: the split must keep the routes of system.py, in their order:\n  expected {SYSTEM_ROUTES_OF_THE_SPLIT}\n  got      {served}"
    shapes = [(ctx.path, sorted(ctx.methods or ()), list(getattr(ctx, "tags", []))) for ctx in contexts]
    assert all(methods == ["GET"] and tags == ["System"] for _, methods, tags in shapes), f"each route of the split must stay a GET under the System tag: {shapes}"
    print_success(f"{len(served)} routes of system.py, in their order: {[path for path, _ in served]}")


def test_the_readiness_probe_comes_after_the_instance_configuration():
    """Routes added after the split come after its six: /system/instance, then /system/ready, a GET of the System tag served by ready.py."""
    contexts = list(iter_route_contexts(system_module.router.routes))
    paths = [ctx.path for ctx in contexts]
    assert paths.count("/system/instance") == 1 and paths.count("/system/ready") == 1, f"each route is registered once: {paths}"
    instance_at, ready_at = paths.index("/system/instance"), paths.index("/system/ready")
    assert len(SYSTEM_ROUTES_OF_THE_SPLIT) <= instance_at < ready_at, f"/system/ready must come after /system/instance, both after the six routes of the split: {paths}"
    ready = contexts[ready_at]
    served = f"{getattr(ready.endpoint, '__module__', '?').removeprefix(system_module.__name__ + '.')}.{getattr(ready.endpoint, '__name__', '?')}"
    assert (served, sorted(ready.methods or ()), list(getattr(ready, "tags", []))) == ("ready.get_readiness", ["GET"], ["System"]), f"/system/ready: {served} {ready.methods} {getattr(ready, 'tags', None)}"


def test_the_block_page_comes_last_after_the_readiness_probe():
    """CP6: /system/block, registered once after /system/ready and last of the router, a GET of the System tag served by block.py."""
    contexts = list(iter_route_contexts(system_module.router.routes))
    paths = [ctx.path for ctx in contexts]
    assert paths.count("/system/block") == 1, f"/system/block is registered once: {paths}"
    ready_at, block_at = paths.index("/system/ready"), paths.index("/system/block")
    assert ready_at < block_at == len(paths) - 1, f"/system/block must come after /system/ready, last of the /system router: {paths}"
    block = contexts[block_at]
    served = f"{getattr(block.endpoint, '__module__', '?').removeprefix(system_module.__name__ + '.')}.{getattr(block.endpoint, '__name__', '?')}"
    assert (served, sorted(block.methods or ()), list(getattr(block, "tags", []))) == ("block.get_instance_block", ["GET"], ["System"]), f"/system/block: {served} {block.methods} {getattr(block, 'tags', None)}"


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


def _route_dependency_calls(path: str, routes: list | None = None) -> set:
    """Every callable FastAPI resolves before the handler of GET ``path``, on the system router unless ``routes`` is given.

    The router holds one included router per resource (C2), so the routes are walked as FastAPI serves them: their
    effective route contexts, and the effective dependant of each, which adds to the handler's own dependencies those
    declared where its router is included. The original route's dependant (``context.route.dependant``) misses those.
    """
    contexts = iter_route_contexts(system_module.router.routes if routes is None else routes)
    context = next((ctx for ctx in contexts if ctx.path == path and "GET" in (ctx.methods or ())), None)
    assert context is not None, f"GET {path} is not declared on the router"
    dependant = getattr(context, "dependant", None)
    assert dependant is not None, f"GET {path} has no dependant to walk: it is not an API route"
    calls, pending = set(), list(dependant.dependencies)
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


# ============================================================================
# THE CONNECTION-SECURITY INDICATOR (plan 36, §2.1)
# ============================================================================
#
# The server's half of the indicator: the class of the client address and the decision the session
# cookie gets on the request, never the address itself. classify_ip and client_address are pure
# (CONN-001 to CONN-004). GET /system/connection runs live on the lane's backend (CONN-010 to
# CONN-013), and in-process (CONN-020 to CONN-023), where the TCP peer can be an address uvicorn does
# not trust and a header can be unreadable.

#: Every address of the plan's table with its class. Documentation ranges count as public.
CLASSIFIED_ADDRESSES = [
    pytest.param("127.0.0.1", "loopback", id="loopback-127.0.0.1"),
    pytest.param("127.255.0.9", "loopback", id="loopback-127.255.0.9"),
    pytest.param("::1", "loopback", id="loopback-ipv6"),
    pytest.param("[::1]", "loopback", id="loopback-ipv6-bracketed"),
    pytest.param("::ffff:127.0.0.1", "loopback", id="loopback-ipv4-mapped"),
    pytest.param("100.64.0.1", "vpn", id="vpn-100.64.0.1"),
    pytest.param("100.127.255.254", "vpn", id="vpn-100.127.255.254"),
    pytest.param("fd7a:115c:a1e0::1", "vpn", id="vpn-tailscale-ipv6"),
    pytest.param("fd7a:115c:a1e0:ab12::5", "vpn", id="vpn-tailscale-ipv6-subnet"),
    pytest.param("10.0.0.1", "lan", id="lan-10.0.0.1"),
    pytest.param("172.16.0.1", "lan", id="lan-172.16.0.1"),
    pytest.param("172.31.255.255", "lan", id="lan-172.31.255.255"),
    pytest.param("192.168.1.20", "lan", id="lan-192.168.1.20"),
    pytest.param("169.254.10.10", "lan", id="lan-link-local-169.254.10.10"),
    pytest.param("fe80::1", "lan", id="lan-ipv6-link-local"),
    pytest.param("fe80::1%eth0", "lan", id="lan-ipv6-link-local-zone-id"),
    pytest.param("fd00::1", "lan", id="lan-ipv6-ula-fd00"),
    pytest.param("fc00::1", "lan", id="lan-ipv6-ula-fc00"),
    pytest.param("::ffff:192.168.1.20", "lan", id="lan-ipv4-mapped"),
    pytest.param("8.8.8.8", "public", id="public-8.8.8.8"),
    pytest.param("203.0.113.9", "public", id="public-documentation-203.0.113.9"),
    pytest.param("198.51.100.7", "public", id="public-documentation-198.51.100.7"),
    pytest.param("192.0.2.1", "public", id="public-documentation-192.0.2.1"),
    pytest.param("172.32.0.1", "public", id="public-172.32.0.1-past-172.16-12"),
    pytest.param("100.128.0.1", "public", id="public-100.128.0.1-past-cgnat"),
    pytest.param("100.63.255.255", "public", id="public-100.63.255.255-before-cgnat"),
    pytest.param("2001:4860:4860::8888", "public", id="public-ipv6"),
    pytest.param("2001:db8::1", "public", id="public-ipv6-documentation"),
]

#: Nothing to classify: no address, an unreadable one, the unspecified addresses, multicast.
UNCLASSIFIABLE_ADDRESSES = [
    pytest.param(None, id="none"),
    pytest.param("", id="empty"),
    pytest.param("garbage", id="garbage"),
    pytest.param("999.1.1.1", id="octet-out-of-range"),
    pytest.param("0.0.0.0", id="ipv4-unspecified"),
    pytest.param("::", id="ipv6-unspecified"),
    pytest.param("224.0.0.1", id="ipv4-multicast"),
    pytest.param("ff02::1", id="ipv6-multicast"),
]

#: (X-Forwarded-For, TCP peer, the address to classify). The peer differs from every header value,
#: so a fallback taken by mistake shows.
PICKED_ADDRESSES = [
    pytest.param(None, "127.0.0.1", "127.0.0.1", id="no-header-the-peer"),
    pytest.param("203.0.113.9", "127.0.0.1", "203.0.113.9", id="one-value"),
    pytest.param("10.0.0.5, 203.0.113.9", "127.0.0.1", "203.0.113.9", id="the-last-value"),
    pytest.param(" 10.0.0.5 ,  192.168.1.20 ", "127.0.0.1", "192.168.1.20", id="spaces-stripped"),
    pytest.param("10.0.0.5, ", "127.0.0.1", "10.0.0.5", id="the-last-non-empty-value"),
    pytest.param("10.0.0.5, garbage", "127.0.0.1", "127.0.0.1", id="an-unreadable-last-value-falls-back-to-the-peer-not-to-an-earlier-value"),
    pytest.param("203.0.113.9:4711", "127.0.0.1", "203.0.113.9", id="ipv4-port-stripped"),
    pytest.param("[2001:db8::7]:443", "127.0.0.1", "2001:db8::7", id="ipv6-brackets-and-port-stripped"),
    pytest.param("[fd7a:115c:a1e0::1]", "127.0.0.1", "fd7a:115c:a1e0::1", id="ipv6-brackets-stripped"),
    # Beyond the plan's table, by its own rule: a bare IPv6 has no port to strip. It is what nginx's
    # $proxy_add_x_forwarded_for appends for an IPv6 client ($remote_addr carries no brackets).
    pytest.param("2001:db8::7", "127.0.0.1", "2001:db8::7", id="ipv6-bare-kept-whole"),
    pytest.param("", "127.0.0.1", "127.0.0.1", id="empty-header-the-peer"),
]


class TestClassifyIp:
    """classify_ip(address): loopback, vpn, lan, public or unknown, once brackets, a zone id and an IPv4-mapped form are normalised."""

    @pytest.mark.parametrize(("address", "expected"), CLASSIFIED_ADDRESSES)
    def test_every_address_gets_its_class(self, address, expected):
        """CONN-001 — NEW, red today: the class of every address of the plan's table.

        loopback is 127/8 and ::1; vpn the CGNAT 100.64/10 and Tailscale's fd7a:115c:a1e0::/48; lan
        the private, link-local and other unique-local ranges; public everything else, the
        documentation ranges included (Python's ipaddress calls those private: they must not read
        as lan). Today the stub answers unknown to every address.
        """
        result = classify_ip(address)

        assert result == expected, f"[new] classify_ip({address!r}) must be {expected!r}, got {result!r}"

    @pytest.mark.parametrize("address", UNCLASSIFIABLE_ADDRESSES)
    def test_no_readable_address_is_unknown(self, address):
        """CONN-002 — GUARD, green today and after: no address, an unreadable one, 0.0.0.0, :: and multicast are unknown."""
        result = classify_ip(address)

        assert result == "unknown", f"classify_ip({address!r}) has no client to classify: it must be 'unknown', got {result!r}"


class TestClientAddress:
    """client_address(forwarded_for, peer): the address to classify, the last X-Forwarded-For value when it is an IP, else the TCP peer."""

    @pytest.mark.parametrize(("forwarded_for", "peer", "expected"), PICKED_ADDRESSES)
    def test_the_last_forwarded_value_else_the_peer(self, forwarded_for, peer, expected):
        """CONN-003 — NEW, red today: the last non-empty X-Forwarded-For value when it is an IP, else the peer.

        The value is stripped of spaces, brackets and a port, and returned as bare address text.
        The last value is the one the nearest proxy appended: when it cannot be read the answer is
        the peer, never an earlier value of the header. Today the stub answers None to everything.
        """
        result = client_address(forwarded_for, peer)

        assert result == expected, f"[new] client_address({forwarded_for!r}, {peer!r}) must be {expected!r}, got {result!r}"

    def test_no_header_and_no_peer_is_none(self):
        """CONN-004 — GUARD, green today and after: without a header and without a peer there is no address."""
        result = client_address(None, None)

        assert result is None, f"client_address(None, None) must be None, got {result!r}"


#: The lane's server by its IPv4 address, as the COOKIE tests of test_auth_api.py reach it: the TCP
#: peer is 127.0.0.1, never ::1.
IPV4_API_BASE = f"http://127.0.0.1:{settings.TEST_PORT}/api/v1"
CONNECTION_URL = f"{IPV4_API_BASE}/system/connection"
CONNECTION_PASSWORD = "ConnSecPass123!"
#: Everything GET /system/connection answers: a class and the cookie decision, never an address.
CONNECTION_KEYS = {"client_class", "cookie_secure"}


@pytest_asyncio.fixture
async def session_cookie(test_server) -> AsyncIterator[dict[str, str]]:
    """A Cookie header with the session of a regular user of this test only; the account is deleted at teardown.

    Registered and logged in over 127.0.0.1. The session travels explicitly on every request,
    never through a client's cookie jar, and teardown deletes the account with it.
    """
    username = f"connsec_{uuid4().hex[:12]}"
    credentials = {"username": username, "password": CONNECTION_PASSWORD}
    async with httpx.AsyncClient() as client:
        registered = await client.post(f"{IPV4_API_BASE}/auth/register", json={**credentials, "email": f"{username}@example.com"}, timeout=TIMEOUT)
        assert registered.status_code == 201, f"Setup: registering {username} failed: {registered.status_code} {registered.text}"
        assert registered.json()["user"]["is_superuser"] is False, "Precondition: a regular user (the lane has its administrators), so deleting the account is never refused"
        login = await client.post(f"{IPV4_API_BASE}/auth/login", json=credentials, timeout=TIMEOUT)
        token = login.cookies.get(SESSION_COOKIE_NAME)
        assert login.status_code == 200 and token, f"Setup: login as {username} failed: {login.status_code} {login.text}"
        cookie = {"Cookie": f"{SESSION_COOKIE_NAME}={token}"}

        yield cookie

        deleted = await client.delete(f"{IPV4_API_BASE}/auth/users/me", headers=cookie, timeout=TIMEOUT)
    assert deleted.status_code == 200, f"Cleanup: deleting {username} failed: {deleted.status_code} {deleted.text}"


async def _get_connection(headers: dict[str, str]) -> httpx.Response:
    """GET /system/connection from 127.0.0.1 with exactly these headers, on a client with an empty cookie jar."""
    async with httpx.AsyncClient() as client:
        return await client.get(CONNECTION_URL, headers=headers, timeout=TIMEOUT)


def _assert_connection_body(response: httpx.Response) -> dict:
    """The answer of a logged-in request: 200, and the class and the cookie decision only."""
    assert response.status_code == 200, f"A logged-in user must get the connection security: {response.status_code} {response.text}"
    body = response.json()
    assert set(body) == CONNECTION_KEYS, f"The answer must carry the class and the cookie decision only, never an address: {body}"
    return body


class TestConnectionSecurityRequiresSession:
    """No valid session, no answer: the class of an address is still information about the network."""

    @pytest.mark.asyncio
    async def test_request_without_session_is_rejected(self, test_server):
        """CONN-010 — GUARD, green today and after: without a session the gate answers 401, and nothing of the payload."""
        print_section("CONN-010: GET /system/connection without a session is rejected")
        response = await _get_connection({})

        assert response.status_code == 401, f"GET /system/connection answered without a session: expected 401, got {response.status_code}: {response.text}"
        assert response.json() == {"detail": "Not authenticated"}, f"The gate's own error and nothing of the payload: {response.text}"

        print_success("✓ No session: 401 Not authenticated")


class TestConnectionSecurityLive:
    """GET /system/connection on the lane's backend, from 127.0.0.1 over plain HTTP (plan 36, §2.1).

    127.0.0.1 is a client uvicorn trusts by default (FORWARDED_ALLOW_IPS=127.0.0.1), so its
    proxy-headers handling also rewrites the TCP peer from X-Forwarded-For and the scheme from
    X-Forwarded-Proto. For a valid IP the peer and the header then agree: these tests send valid
    IPs only, and an untrusted peer or an unreadable value is tested in-process
    (TestConnectionSecurityInProcess). cookie_secure is read under SESSION_COOKIE_SECURE=auto,
    checked by lane_runs_auto.

    Write-scoped: each test logs in as a regular user of its own, deleted at teardown.
    """

    @pytest.fixture(autouse=True)
    def lane_runs_auto(self):
        """Precondition: the default mode, as the COOKIE tests of test_auth_api.py. The server reads the same .env and environment as this process."""
        mode = auth_module.SESSION_COOKIE_SECURE_MODE
        assert mode == "auto", f"Precondition: these tests need SESSION_COOKIE_SECURE=auto, the default; this lane runs {mode!r} (set in .env or in the environment)"

    @pytest.mark.asyncio
    async def test_plain_request_from_loopback(self, session_cookie):
        """CONN-011 — NEW, red today: a session and no proxy header get exactly {"client_class": "loopback", "cookie_secure": false}.

        The TCP peer is 127.0.0.1 and the request plain HTTP, so under auto the session cookie is
        not Secure. Nothing but the class and the cookie decision: no address may leave the server.
        Today the stub classifies nothing, and the red shows client_class 'unknown'.
        """
        print_section("CONN-011: a plain request from 127.0.0.1 is loopback, its cookie not Secure")
        body = _assert_connection_body(await _get_connection(session_cookie))

        assert body == {"client_class": "loopback", "cookie_secure": False}, f"[new] From 127.0.0.1 over plain HTTP, without proxy headers, the server must see a loopback client and a session cookie that is not Secure (auto): got {body}"

        print_success("✓ 127.0.0.1 over plain HTTP: loopback, cookie_secure false, and no other key")

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("forwarded_for", "client_class"),
        [
            pytest.param("192.168.1.20", "lan", id="lan"),
            pytest.param("10.0.0.5, 203.0.113.9", "public", id="public-the-last-of-two"),
            pytest.param("100.100.1.2", "vpn", id="vpn-cgnat"),
        ],
    )
    async def test_the_last_forwarded_for_value_decides_the_class(self, session_cookie, forwarded_for, client_class):
        """CONN-012 — NEW, red today: behind a proxy the class is the last X-Forwarded-For value's.

        The last value is the one the nearest proxy appended: "10.0.0.5, 203.0.113.9" is a public
        client, where the first value alone would say lan. Without X-Forwarded-Proto the cookie
        stays not Secure. Today the stub answers 'unknown'.
        """
        print_section(f"CONN-012: X-Forwarded-For: {forwarded_for} is {client_class}")
        body = _assert_connection_body(await _get_connection({**session_cookie, "X-Forwarded-For": forwarded_for}))

        assert body == {"client_class": client_class, "cookie_secure": False}, f"[new] With X-Forwarded-For: {forwarded_for} over plain HTTP the server must classify the client by the last value, {client_class!r}, and keep the cookie not Secure: got {body}"

        print_success(f"✓ X-Forwarded-For: {forwarded_for} → {client_class}")

    @pytest.mark.asyncio
    async def test_a_proxy_reporting_https_makes_the_cookie_secure(self, session_cookie):
        """CONN-013 — GUARD, green today and after: X-Forwarded-Proto: https gets cookie_secure true.

        It is the decision the session cookie gets on this very request (session_cookie_secure, as
        COOKIE-002 in test_auth_api.py). The class is not this test's subject.
        """
        print_section("CONN-013: X-Forwarded-Proto: https gets cookie_secure true")
        body = _assert_connection_body(await _get_connection({**session_cookie, "X-Forwarded-Proto": "https"}))

        assert body["cookie_secure"] is True, f"Behind a proxy reporting HTTPS the session cookie is Secure under auto, and the answer must say so: {body}"

        print_success("✓ X-Forwarded-Proto: https → cookie_secure true")


def _any_user() -> User:
    """The handler's ``_current_user``: the gate already ran and the handler never reads it, so any account will do. Never stored."""
    return User(username="connsec_probe", email="connsec_probe@example.com", hashed_password="unused")


def _connection_request(client: Optional[tuple[str, int]], *forwarded_for: str) -> Request:
    """GET /system/connection as uvicorn hands it to the app, from ``client``, with one X-Forwarded-For line per value.

    No proxy-headers middleware runs here: the scope's client is the TCP peer whatever the header
    says, as uvicorn leaves it for a client it does not trust. Host and server make request.url
    absolute, as uvicorn's always is.
    """
    headers = [(b"host", b"librefolio.example"), *((b"x-forwarded-for", value.encode("latin-1")) for value in forwarded_for)]
    scope = {
        "type": "http",
        "scheme": "http",
        "method": "GET",
        "path": "/api/v1/system/connection",
        "root_path": "",
        "query_string": b"",
        "headers": headers,
        "client": client,
        "server": ("librefolio.example", 80),
    }
    return Request(scope)


class TestConnectionSecurityInProcess:
    """get_connection_security called directly: the app reads X-Forwarded-For itself, whoever the TCP peer (plan 36, §2.1).

    The peer here can be an address uvicorn does not trust and the header can be unreadable:
    neither can be produced live from 127.0.0.1 (see TestConnectionSecurityLive).
    """

    @pytest.mark.asyncio
    async def test_the_app_reads_the_header_from_a_peer_uvicorn_does_not_trust(self):
        """CONN-020 — NEW, red today: the peer 203.0.113.7 with X-Forwarded-For: 192.168.1.20 is lan.

        uvicorn rewrites the peer from the header only for a client it trusts (127.0.0.1 by
        default): from 203.0.113.7 the scope keeps the real peer, which is public. lan can only
        come from the app reading the header itself. That is advisory, since a forged header
        misleads only the sender's own indicator. Today the stub answers 'unknown'.
        """
        print_section("CONN-020: an untrusted peer with X-Forwarded-For: 192.168.1.20 is lan")
        request = _connection_request(("203.0.113.7", 1234), "192.168.1.20")
        assert request.client is not None and request.client.host == "203.0.113.7", f"Precondition: the TCP peer must stay 203.0.113.7: {request.client}"

        result = await get_connection_security(request=request, _current_user=_any_user())

        assert result.client_class == "lan", f"[new] From the untrusted peer 203.0.113.7 with X-Forwarded-For: 192.168.1.20 the class must come from the header, lan (the peer alone is public): got {result!r}"

        print_success("✓ The app reads X-Forwarded-For itself: lan")

    @pytest.mark.asyncio
    async def test_no_peer_and_no_header_is_unknown(self):
        """CONN-021 — GUARD, green today and after: a scope without a client and without the header is unknown."""
        print_section("CONN-021: no peer and no X-Forwarded-For is unknown")
        request = _connection_request(None)
        assert request.client is None and "x-forwarded-for" not in request.headers, f"Precondition: no peer and no header: {request.client} {request.headers}"

        result = await get_connection_security(request=request, _current_user=_any_user())

        assert result.client_class == "unknown", f"Without a peer and without X-Forwarded-For there is no client to classify: it must be 'unknown', got {result!r}"

        print_success("✓ No address at all: unknown")

    @pytest.mark.asyncio
    async def test_the_last_value_of_the_last_header_line_decides(self):
        """CONN-022 — NEW, red today: two X-Forwarded-For lines, 10.0.0.5 then 203.0.113.9, are public.

        Each proxy may add its own header line, and the endpoint joins them in order: the last value
        of the last line wins. The first line alone would say lan, the peer 127.0.0.1 loopback.
        Today the stub answers 'unknown'.
        """
        print_section("CONN-022: two X-Forwarded-For lines, the last value of the last one decides")
        request = _connection_request(("127.0.0.1", 50000), "10.0.0.5", "203.0.113.9")
        assert request.headers.getlist("x-forwarded-for") == ["10.0.0.5", "203.0.113.9"], f"Precondition: two X-Forwarded-For lines, in this order: {request.headers}"

        result = await get_connection_security(request=request, _current_user=_any_user())

        assert result.client_class == "public", f"[new] With the X-Forwarded-For lines 10.0.0.5 then 203.0.113.9 the last value of the last line decides, public (the first line would say lan, the peer 127.0.0.1 loopback): got {result!r}"

        print_success("✓ The last value of the last line: public")

    @pytest.mark.asyncio
    async def test_an_unreadable_header_falls_back_to_the_peer(self):
        """CONN-023 — NEW, red today: an unreadable X-Forwarded-For falls back to the TCP peer.

        The peer 192.168.1.20 is lan and the header says "garbage", which holds no address. Live,
        from 127.0.0.1, uvicorn would make "garbage" the peer as well, so the app's fallback shows
        only here. Today the stub answers 'unknown'.
        """
        print_section("CONN-023: an unreadable X-Forwarded-For falls back to the peer")
        request = _connection_request(("192.168.1.20", 50000), "garbage")

        result = await get_connection_security(request=request, _current_user=_any_user())

        assert result.client_class == "lan", f"[new] X-Forwarded-For: garbage holds no address, so the class must be the TCP peer's, 192.168.1.20 → lan: got {result!r}"

        print_success("✓ An unreadable header: the peer decides, lan")


# ============================================================================
# GET /api/v1/system/instance — THE PUBLIC CONFIGURATION OF THE INSTANCE
# ============================================================================
#
# What the app reads at startup, before anyone signs in: public by design, the same for
# whoever asks, so behind no session. Six fields today: the profile from LIBREFOLIO_PROFILE
# (selfhosted unless set); accounts — the registration mode, whether a variable locks it, whether the instance has
# no account yet (first_account_open, A6d: what the login page reads instead of the global settings, which now want a
# session) and the password rules (password_rules, A6c: what the registration, invitation and reset pages show before
# anyone signs in) —; email, whether the instance can send emails (workstream E); support_url, where users ask for
# help (LIBREFOLIO_SUPPORT_URL, workstream H, CP13), null unless set to an http(s) page or mailto: and one address;
# legal, the instance's own legal pages (workstream A, F09: its content is pinned in test_instance_config_legal_api.py,
# here only its presence); and client_log_level (D4, H-60), how much the browser's console says of a failed API call:
# "debug" when the backend's LOG_LEVEL is DEBUG or TRACE, "error" otherwise — two states, never the level itself.
# Live on the lane's backend for the lane's default — the runner drops every LIBREFOLIO_* setting from a lane, so no
# support address —, in-process for a profile or a support address set through the environment, which the lane's
# server cannot be given from here. The lane's database is
# shared: the registration mode and first_account_open are typed there, never pinned. The password rules are not lane
# state — the backend's, the same on every instance —: pinned exactly.
# The Settings field itself (default, normalisation, refusal) is in test_config_misc.py; env_url, support_url() and
# support_link() are in test_config_package.py.

INSTANCE_URL = f"{API_BASE}/system/instance"
#: The public configuration, exactly these fields.
# H-62 (contract L3 §6): ``mode``, normal or awaiting_restore. B-33 (22/10): ``restore_interrupted``; H5-3 (24/10): ``restore_interrupted_reason``
INSTANCE_KEYS = {"profile", "accounts", "email", "support_url", "legal", "client_log_level", "mode", "restore_interrupted", "restore_interrupted_reason"}
#: accounts, exactly these fields.
ACCOUNTS_KEYS = {"registration_mode", "registration_locked", "first_account_open", "password_rules"}
#: Decision 37 (lot A6c): accounts.password_rules as (code, value) — a value left out and a null one read alike.
PASSWORD_RULES = [("min_length", 8), ("uppercase", None), ("lowercase", None), ("digit", None), ("special", None)]
#: Where users ask for help (CP13): never set on a lane, set in this process only.
SUPPORT_URL_VARIABLE = "LIBREFOLIO_SUPPORT_URL"


def _password_rule_pairs(rules: object) -> object:
    """``(code, value)`` of every published rule; the rules as they are when they are not a list of mappings of code and value alone, so that the comparison fails and shows them."""
    if not isinstance(rules, list) or not all(isinstance(rule, dict) and set(rule) <= {"code", "value"} for rule in rules):
        return rules
    return [(rule.get("code"), rule.get("value")) for rule in rules]


class TestInstanceConfigIsPublic:
    """GET /system/instance resolves no session gate, wherever one could be declared."""

    def test_the_walk_sees_a_gate_declared_where_a_router_is_included(self):
        """Presence barrier of the next test: a gate added by include_router, not on the handler, is still found."""
        resource = APIRouter()

        @resource.get("/probe")
        def probe() -> dict:
            return {}

        gated, open_router = APIRouter(prefix="/gated"), APIRouter(prefix="/open")
        gated.include_router(resource, dependencies=[Depends(get_current_user)])
        open_router.include_router(resource)

        assert get_current_user in _route_dependency_calls("/gated/probe", gated.routes), "the walk missed a session gate declared on include_router: it would call public a route that is not"
        assert get_current_user not in _route_dependency_calls("/open/probe", open_router.routes), "the walk found a session gate on a route that has none"

    def test_route_depends_on_no_session(self):
        """Structural: no get_current_user among the dependencies FastAPI resolves for GET /system/instance."""
        # Control first: the walk finds the gate where it is declared, so a pass below means the gate is absent.
        assert get_current_user in _route_dependency_calls("/system/container-image-status")
        assert get_current_user not in _route_dependency_calls("/system/instance"), "GET /system/instance resolves get_current_user: the app reads it before anyone signs in, so it must need no session"


class TestInstanceConfigLive:
    """GET /system/instance on the lane's backend: anyone gets the declared fields, and nothing else."""

    @pytest.fixture(autouse=True)
    def lane_sets_no_profile(self):
        """Precondition: the default profile. The server reads the same .env and environment as this process."""
        profile = get_settings().LIBREFOLIO_PROFILE
        assert profile == "selfhosted", f"Precondition: these tests read the default profile; this lane runs {profile!r} (LIBREFOLIO_PROFILE set in .env or in the environment)"

    @pytest.fixture(autouse=True)
    def lane_sets_no_support_address(self):
        """Precondition: no support address. The runner drops every LIBREFOLIO_* setting from a lane, and the server reads the same environment as this process."""
        configured = os.environ.get(SUPPORT_URL_VARIABLE)
        assert not (configured or "").strip(), f"Precondition: these tests read a lane without a support address; this lane runs {SUPPORT_URL_VARIABLE}={configured!r} (the runner drops every LIBREFOLIO_* setting from a lane: was this run started outside ./dev.py test?)"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("forged_cookie", [False, True], ids=["no-cookie", "forged-session-cookie"])
    async def test_anyone_gets_the_public_configuration(self, test_server, forged_cookie):
        """No session, or a session cookie the server never issued: 200 and exactly the declared fields, the default profile beside accounts, email and legal, support_url null: the lane sets no support address, and client_log_level "debug" (D4, H-60).

        "debug" because a test lane always runs at DEBUG: the runner's shared backend is ``dev.py server --test``, which runs in debug mode and sets LIBREFOLIO_LOG_LEVEL=DEBUG whatever the developer's LOG_LEVEL, so the lane's server and this process may read different levels.
        The mapping itself — DEBUG and TRACE "debug", every other level "error" — is pinned in process in test_services/test_server_errors.py.
        """
        async with httpx.AsyncClient() as client:
            if forged_cookie:
                client.cookies.set(SESSION_COOKIE_NAME, f"forged-{uuid4().hex}")
            response = await client.get(INSTANCE_URL, timeout=TIMEOUT)

        assert response.status_code == 200, f"GET /system/instance is public: expected 200 without a valid session, got {response.status_code}: {response.text}"
        body = response.json()
        assert set(body) == INSTANCE_KEYS and body["profile"] == "selfhosted", f"the public configuration must be exactly the declared fields, the profile the lane's default: {response.text}"
        accounts = body["accounts"]
        assert (
            set(accounts) == ACCOUNTS_KEYS and accounts["registration_mode"] in {"open", "invite", "disabled"} and isinstance(accounts["registration_locked"], bool) and isinstance(accounts["first_account_open"], bool)
        ), f"accounts must be exactly the registration mode, whether it is locked, whether the instance has no account yet — the last two booleans (the lane's database is shared: the mode and first_account_open are not pinned here) — and the password rules: {response.text}"
        assert _password_rule_pairs(accounts["password_rules"]) == PASSWORD_RULES, f"accounts.password_rules must be the backend's rules, the same on every instance (decision 37): expected {PASSWORD_RULES} as (code, value), got {accounts['password_rules']}"
        assert set(body["email"]) == {"available", "links"} and all(isinstance(body["email"][key], bool) for key in ("available", "links")), f"email must be exactly whether the instance can send emails, and emails with a link (the lane's configuration, not pinned here): {response.text}"
        assert body["support_url"] is None, f"support_url must be null on a lane that sets no {SUPPORT_URL_VARIABLE}, and the asset search then offers a new GitHub issue on a self-hosted instance, no report link on a managed one: {response.text}"
        assert body["client_log_level"] == "debug", f"client_log_level (D4, H-60) must be 'debug' on a test lane: dev.py server --test runs it with LIBREFOLIO_LOG_LEVEL=DEBUG (a server started in this process, outside ./dev.py test, reads this process's level instead): {response.text}"


def _instance_app() -> FastAPI:
    """The system router in an app of this test, as test_container_registry.py builds one; no override: accounts reads the global settings through the app's own database session, the lane's database here."""
    app = FastAPI()
    app.include_router(system_module.router, prefix="/api/v1")
    return app


@pytest.fixture
def fresh_link_reports():
    """The once-per-process log of an invalid instance link empty before and after the test: an invalid address set here leaves no report behind."""
    instance_links._report_invalid.cache_clear()
    yield
    instance_links._report_invalid.cache_clear()


class TestInstanceConfigInProcess:
    """GET /system/instance answers the profile LIBREFOLIO_PROFILE sets, as get_settings() reads it at each request, and the support address LIBREFOLIO_SUPPORT_URL sets, as support_link() publishes it."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("configured", "profile"),
        [
            pytest.param("managed", "managed", id="managed"),
            pytest.param(" MANAGED ", "managed", id="stripped-and-lowercased"),
            pytest.param("selfhosted", "selfhosted", id="selfhosted"),
        ],
    )
    async def test_the_configured_profile_is_answered(self, monkeypatch, configured, profile):
        monkeypatch.setenv("LIBREFOLIO_PROFILE", configured)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=_instance_app()), base_url="http://test") as client:
            response = await client.get("/api/v1/system/instance")

        assert response.status_code == 200, f"GET /system/instance with LIBREFOLIO_PROFILE={configured!r}: expected 200, got {response.status_code}: {response.text}"
        body = response.json()
        assert set(body) == INSTANCE_KEYS and body["profile"] == profile, f"LIBREFOLIO_PROFILE={configured!r} must be answered as profile {profile!r}, beside accounts, email, support_url, legal and client_log_level and nothing else: {response.text}"
        accounts = body["accounts"]
        assert (
            set(accounts) == ACCOUNTS_KEYS and accounts["registration_mode"] in {"open", "invite", "disabled"} and isinstance(accounts["registration_locked"], bool) and isinstance(accounts["first_account_open"], bool)
        ), f"accounts must be exactly the registration mode, whether it is locked, whether the instance has no account yet — the last two booleans (read from the lane's shared database: not pinned here) — and the password rules: {response.text}"
        assert _password_rule_pairs(accounts["password_rules"]) == PASSWORD_RULES, f"accounts.password_rules must be the backend's rules, the same on every instance (decision 37): expected {PASSWORD_RULES} as (code, value), got {accounts['password_rules']}"
        assert set(body["email"]) == {"available", "links"} and all(isinstance(body["email"][key], bool) for key in ("available", "links")), f"email must be exactly whether the instance can send emails, and emails with a link: {response.text}"

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("fresh_link_reports")
    @pytest.mark.parametrize(
        ("configured", "published"),
        [
            pytest.param("https://help.example/", "https://help.example", id="set-without-its-trailing-slash"),
            pytest.param("ftp://help.example", None, id="invalid-is-null"),
            pytest.param("mailto:Help@Example.ORG", "mailto:Help@example.org", id="mailto-domain-lowercased-local-part-kept"),
            pytest.param("mailto:help?cc=x@example.org", None, id="mailto-with-a-header-is-null"),
        ],
    )
    async def test_the_configured_support_address_is_answered(self, monkeypatch, configured, published):
        """CP13: support_url is what support_link() publishes for this process's LIBREFOLIO_SUPPORT_URL, the answer still 200 — an invalid address never breaks what the app reads at startup.

        An http(s) page without its trailing slash; mailto: and one address as support_url() normalizes it, the local
        part kept and the domain lowercased (CP13/P20); null for any other value, a mailto: the rule refuses included —
        here a header smuggled in with ?, which EmailStr alone would take.
        """
        monkeypatch.setenv(SUPPORT_URL_VARIABLE, configured)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=_instance_app()), base_url="http://test") as client:
            response = await client.get("/api/v1/system/instance")

        assert response.status_code == 200, f"GET /system/instance with {SUPPORT_URL_VARIABLE}={configured!r}: expected 200, got {response.status_code}: {response.text}"
        body = response.json()
        assert set(body) == INSTANCE_KEYS and body["support_url"] == published, f"{SUPPORT_URL_VARIABLE}={configured!r} must be answered as support_url {published!r}, beside the other declared fields and nothing else: {response.text}"


def _schema_component(document: dict, schema: dict) -> dict:
    """The component of ``document`` a schema refers to: its own ``$ref``, or the one of its ``allOf`` (a field with a description)."""
    references = [schema.get("$ref"), *(option.get("$ref") for option in schema.get("allOf", []))]
    reference = next((ref for ref in references if ref), None)
    assert reference, f"the schema refers to no component: {schema}"
    return document["components"]["schemas"][reference.rsplit("/", 1)[-1]]


def test_first_account_open_is_optional_and_false_unless_set():
    """accounts.first_account_open (A6d, C3): optional, false unless set. An AccountsInstanceConfig built without it
    serializes it false, so an answer that forgets the flag never offers the first account to whoever asks; in the
    OpenAPI of GET /system/instance, accounts declares it as a boolean without requiring it, as email.available is
    (EMA-022 in test_email_api.py). Its value on the lane is not pinned: the lane's database is shared."""
    answer = AccountsInstanceConfig(registration_mode="open", registration_locked=False).model_dump(mode="json")
    document = _instance_app().openapi()
    response_schema = document["paths"]["/api/v1/system/instance"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
    accounts = _schema_component(document, _schema_component(document, response_schema)["properties"]["accounts"])

    assert answer.get("first_account_open") is False, f"first_account_open must default to false when it is not given: {answer}"
    assert accounts["properties"].get("first_account_open", {}).get("type") == "boolean", f"the OpenAPI must declare accounts.first_account_open, a boolean: {accounts}"
    assert "first_account_open" not in accounts.get("required", []), f"accounts.first_account_open must stay optional in the OpenAPI: required {accounts.get('required')}"


# ============================================================================
# GET /api/v1/system/info — THE APP VERSION FOR ANYONE, EVERYTHING WITH A SESSION
# ============================================================================
#
# Without a valid session the answer is the app version only; with one, the versions of Python, the OS and the
# dependencies too. signed_in_user runs the checks of get_current_user and reads its 401 as "anonymous": any other
# refusal goes through. Live on the lane's backend for the three kinds of caller, directly for signed_in_user, and the
# OpenAPI document for the union of the two answers.

INFO_URL = f"{IPV4_API_BASE}/system/info"
#: Everything GET /system/info answers with a valid session.
FULL_INFO_KEYS = {"app_version", "python_version", "os_name", "os_version", "platform", "deployment_mode", "backend_dependencies", "frontend_dependencies"}


class TestSystemInfoLive:
    """GET /system/info on the lane's backend: the app version for anyone, everything with a valid session."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("forged_cookie", [False, True], ids=["no-cookie", "forged-session-cookie"])
    async def test_without_a_valid_session_only_the_app_version(self, test_server, forged_cookie):
        headers = {"Cookie": f"{SESSION_COOKIE_NAME}=forged-{uuid4().hex}"} if forged_cookie else {}
        async with httpx.AsyncClient() as client:
            response = await client.get(INFO_URL, headers=headers, timeout=TIMEOUT)

        assert response.status_code == 200, f"GET /system/info answers without a valid session: expected 200, got {response.status_code}: {response.text}"
        body = response.json()
        assert set(body) == {"app_version"}, f"without a valid session the answer is the app version only: {body}"
        assert isinstance(body["app_version"], str) and body["app_version"], f"the app version is a non-empty string: {body}"

    @pytest.mark.asyncio
    async def test_a_signed_in_user_gets_everything(self, session_cookie):
        async with httpx.AsyncClient() as client:
            full = await client.get(INFO_URL, headers=session_cookie, timeout=TIMEOUT)
        # A client of its own: a cookie the first answer might set must not reach the anonymous request.
        async with httpx.AsyncClient() as client:
            public = await client.get(INFO_URL, timeout=TIMEOUT)

        assert full.status_code == 200, f"GET /system/info with a valid session: expected 200, got {full.status_code}: {full.text}"
        body = full.json()
        assert set(body) == FULL_INFO_KEYS, f"with a valid session the answer has every field: missing {FULL_INFO_KEYS - set(body)}, extra {set(body) - FULL_INFO_KEYS}"
        SystemInfoResponse.model_validate(body)
        assert public.status_code == 200 and public.json() == {"app_version": body["app_version"]}, f"the same app version with and without a session: {public.status_code} {public.text}"


def _info_request() -> Request:
    """GET /system/info as uvicorn hands it to the app; signed_in_user passes it on unread."""
    scope = {
        "type": "http",
        "scheme": "http",
        "method": "GET",
        "path": "/api/v1/system/info",
        "root_path": "",
        "query_string": b"",
        "headers": [(b"host", b"librefolio.example")],
        "client": ("127.0.0.1", 50000),
        "server": ("librefolio.example", 80),
    }
    return Request(scope)


def _replace_get_current_user(monkeypatch: pytest.MonkeyPatch, outcome: object) -> list[tuple[object, object]]:
    """get_current_user as signed_in_user calls it, replaced: records ``(request, session)``, then returns ``outcome`` or raises it."""
    calls: list[tuple[object, object]] = []

    async def fake_get_current_user(request, session):
        calls.append((request, session))
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    monkeypatch.setattr(info_module, "get_current_user", fake_get_current_user)
    return calls


class TestSignedInUser:
    """signed_in_user: the user of a valid session; None for a 401 of get_current_user; any other refusal raised."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("detail", ["Not authenticated", "Session expired or invalid", "User not found", "User account is disabled"])
    async def test_a_401_means_anonymous(self, monkeypatch, detail):
        calls = _replace_get_current_user(monkeypatch, HTTPException(status_code=401, detail=detail))
        request, session = _info_request(), object()

        user = await signed_in_user(request, session)

        assert calls == [(request, session)], f"Barrier: get_current_user must run once, on the request and the session: {calls}"
        assert user is None, f"a 401 ({detail}) means an anonymous caller: got {user!r}"

    @pytest.mark.asyncio
    async def test_a_valid_session_gives_its_user(self, monkeypatch):
        account = _any_user()
        _replace_get_current_user(monkeypatch, account)

        user = await signed_in_user(_info_request(), object())

        assert user is account, f"the user of the session must be passed on: got {user!r}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "make_error",
        [
            pytest.param(lambda: HTTPException(status_code=403, detail="Forbidden"), id="http-403"),
            pytest.param(lambda: HTTPException(status_code=503, detail="Service unavailable"), id="http-503"),
            pytest.param(lambda: RuntimeError("the database does not answer"), id="not-an-http-error"),
        ],
    )
    async def test_any_other_refusal_propagates(self, monkeypatch, make_error):
        error = make_error()
        _replace_get_current_user(monkeypatch, error)

        with pytest.raises(type(error)) as raised:
            await signed_in_user(_info_request(), object())

        assert raised.value is error, f"only a 401 means anonymous: {error!r} must reach the caller unchanged, got {raised.value!r}"


def test_openapi_documents_the_full_answer_first():
    """The 200 of GET /system/info is anyOf [SystemInfoResponse, SystemInfoPublicResponse], in that order.

    The order matters: the generated client (``z.union``) keeps the first schema that parses, and its objects drop
    unknown keys, so with the public schema first a full answer would reach the About page as its version only.
    """
    responses = _instance_app().openapi()["paths"]["/api/v1/system/info"]["get"]["responses"]
    schema = responses["200"]["content"]["application/json"]["schema"]

    options = [option.get("$ref") for option in schema.get("anyOf", [])]

    assert options == ["#/components/schemas/SystemInfoResponse", "#/components/schemas/SystemInfoPublicResponse"], f"the 200 of GET /system/info must be anyOf the full answer, then the public one: {schema}"


# ============================================================================
# GET /api/v1/system/ready — THE READINESS PROBE
# ============================================================================
#
# Public, for health checks and orchestrators: no session, one code per check. 200 when the database answers and its
# schema is at the head revision, 503 with the same body shape otherwise. The checks themselves are tested in
# test_services/test_platform_readiness.py; here the route: public, live on the lane's backend (whose database the
# runner migrates, so ready), and in-process with the checks replaced, for the answers the lane cannot be put in.

READY_URL = f"{API_BASE}/system/ready"


class TestReadinessIsPublic:
    """GET /system/ready resolves a database session, and no session gate."""

    def test_route_depends_on_no_session(self):
        # Control first: the walk finds the gate where it is declared, so a pass below means the gate is absent.
        assert get_current_user in _route_dependency_calls("/system/container-image-status")
        calls = _route_dependency_calls("/system/ready")

        assert get_session_generator in calls, f"Barrier: the walk must see the database session the probe resolves: {calls}"
        assert get_current_user not in calls and signed_in_user not in calls, "GET /system/ready resolves a session check: a health check calls it without signing in, so it must need no session"


class TestReadinessLive:
    """GET /system/ready on the lane's backend: ready, for anyone, with the codes and nothing else."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("forged_cookie", [False, True], ids=["no-cookie", "forged-session-cookie"])
    async def test_the_lane_is_ready_for_anyone(self, test_server, forged_cookie):
        headers = {"Cookie": f"{SESSION_COOKIE_NAME}=forged-{uuid4().hex}"} if forged_cookie else {}
        async with httpx.AsyncClient() as client:
            response = await client.get(READY_URL, headers=headers, timeout=TIMEOUT)

        assert response.status_code == 200, f"the lane's database is migrated to the head: expected 200, got {response.status_code}: {response.text}"
        # H-62 (contract L3 §6): readiness says the mode, normal on the lane; red until H-62
        assert response.json() == {"status": "ready", "checks": {"database": "ok", "migrations": "ok"}, "mode": "normal"}, f"exactly the status, the two codes and the mode: {response.text}"


def _readiness_app(session: object) -> FastAPI:
    """The system router in an app of this test, its database session replaced by ``session``."""
    app = _instance_app()
    app.dependency_overrides[get_session_generator] = lambda: session
    return app


class TestReadinessInProcess:
    """GET /system/ready with check_readiness replaced: 200 when ready, 503 otherwise, and the same body either way."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("database", "migrations", "status_code"),
        [
            pytest.param("ok", "ok", 200, id="ready-200"),
            pytest.param("ok", "mismatch", 503, id="mismatch-503"),
            pytest.param("ok", "unknown", 503, id="migrations-unknown-503"),
            pytest.param("unreachable", "unknown", 503, id="unreachable-503"),
        ],
    )
    async def test_the_status_code_follows_the_checks(self, monkeypatch, database, migrations, status_code):
        status = "ready" if status_code == 200 else "not_ready"
        answer = ReadinessResponse(status=status, checks=ReadinessChecks(database=database, migrations=migrations))
        sessions: list[object] = []

        async def fake_check_readiness(session):
            sessions.append(session)
            return answer

        monkeypatch.setattr(ready_module, "check_readiness", fake_check_readiness)
        session = object()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=_readiness_app(session)), base_url="http://test") as client:
            response = await client.get("/api/v1/system/ready")

        assert sessions == [session], f"Barrier: the route must check once, on the session it resolved: {sessions}"
        assert response.status_code == status_code, f"{status} ({database}, {migrations}): expected {status_code}, got {response.status_code}: {response.text}"
        # H-62 (contract L3 §6): the mode beside it, normal outside the mode; red until H-62
        assert response.json() == {"status": status, "checks": {"database": database, "migrations": migrations}, "mode": "normal"}, f"the body is the readiness answer and the mode, whatever the status code: {response.text}"

    def test_openapi_documents_200_and_503_with_the_readiness_body(self):
        responses = _instance_app().openapi()["paths"]["/api/v1/system/ready"]["get"]["responses"]
        schemas = {code: responses.get(code, {}).get("content", {}).get("application/json", {}).get("schema") for code in ("200", "503")}

        expected = {"$ref": "#/components/schemas/ReadinessResponse"}
        assert schemas == {"200": expected, "503": expected}, f"GET /system/ready must document 200 and 503, both with ReadinessResponse: {responses}"

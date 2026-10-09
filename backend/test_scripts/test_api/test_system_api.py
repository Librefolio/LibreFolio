"""
Tests for system API endpoints.

Covers:
- get_display_name: display name mapping and fallback
- parse_pipfile: parsing [packages] section from Pipfile
- get_backend_deps: backend dependency list
- get_frontend_deps: frontend dependency list from package.json
- GET /api/v1/system/info: system info endpoint
- GET /api/v1/system/plugin-diagnostics: session required (live HTTP), failure-list shape for a logged-in user
- classify_ip / client_address (utils/network_utils.py): the class of a client address, and which address (plan 36, §2.1)
- GET /api/v1/system/connection: session required, {client_class, cookie_secure} live and in-process (plan 36, §2.1)
"""

from collections.abc import AsyncIterator
from typing import Optional
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

import backend.app.api.v1.auth as auth_module
import backend.app.api.v1.system as system_module
from backend.app.api.v1.auth import SESSION_COOKIE_NAME, get_current_user
from backend.app.api.v1.system import (
    BACKEND_NAME_MAP,
    FRONTEND_NAME_MAP,
    get_backend_deps,
    get_connection_security,
    get_deployment_mode,
    get_display_name,
    get_frontend_deps,
    get_system_info,
    parse_pipfile,
)
from backend.app.config import TEST_LANE_HEADER, get_settings
from backend.app.db.models import User
from backend.app.schemas.system import PluginDiagnosticsResponse
from backend.app.utils.network_utils import classify_ip, client_address
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

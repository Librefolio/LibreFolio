"""
``GET /api/v1/security/checks`` on the lane's server — release 1.3, workstream A, lot A8a (plan phase01Accounts, A8a C3
and C4): the administrator's list of the «Security» checks, read from the server the runner starts.

The runner starts the lane's backend with ``dev.py server --test``, which sets ``LIBREFOLIO_LOGIN_LIMIT=off`` on every
lane (``configure_test_runtime()`` has dropped any ``LIBREFOLIO_*`` of ``.env`` and of the shell): the lanes sign in over
and over against shared accounts, and the cases of the limit turn it on in-process (``test_login_throttle_api.py``).
Pinned here, through the whole app of ``main.py``:

1. ``e2e_test_admin`` → 200 with ``{"items": [...]}``, each check once; ``accounts.login_limit`` listed, well formed,
   with the severity the lane's server must have — ``warning``, the limit off, under the runner: this pins the
   runner's line —; ``platform.jwt_secret`` and ``platform.plugin_secrets`` listed too.
2. ``e2e_test_user``, a member → 403; no session → 401.

Which severity: ``_expected_login_limit()`` reads ``LIBREFOLIO_LOGIN_LIMIT`` in this process when the case runs, and
``backend/test_scripts/conftest.py`` always provides it: ``off`` in every pytest process that started without a value,
put back before each test (lot E-15). So the case pins ``warning`` under the runner, where the lane's server is
``dev.py server --test``'s, and when the module runs alone too: ``_TestingServerManager`` then runs the server in this
very process, which reads the same ``off``. A value set by hand before a run alone wins in both places: ``on`` pins
``ok``. The function's branches for an unset variable remain for a process without that conftest.

Read-only and parallel-safe: GET requests, and the sign-ins of the two fixture users of ``populate_mock_data.py`` (the
api setup runs ``db populate``), whose roles are checked, never changed; the only write is a login's own counters
(``record_login_and_maybe_show_popup``), which no unit asserts on. Nothing to clean up.
"""

import os
from dataclasses import dataclass
from typing import Any, Optional

import httpx
import pytest

from backend.app.api.v1 import auth as auth_api
from backend.app.config import API_V1_PREFIX, get_settings
from backend.test_scripts.test_server_helper import _TestingServerManager, shared_server_mode
from backend.test_scripts.test_utils import print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}{API_V1_PREFIX}"
TIMEOUT = 30.0
COOKIE = auth_api.SESSION_COOKIE_NAME
CHECKS_PATH = "/security/checks"

#: The fixture users of populate_mock_data.py: signed in, never changed.
E2E_ADMIN = ("e2e_test_admin", "E2eAdminPass123!")
E2E_USER = ("e2e_test_user", "E2eTestPass123!")

LIMIT_VARIABLE = "LIBREFOLIO_LOGIN_LIMIT"
LOGIN_LIMIT_CHECK = "accounts.login_limit"
#: H5-4: A's check of the host-started change of the owner's email.
OWNER_EMAIL_CHANGE_CHECK = "accounts.owner_email_change"
#: Checks of workstream H the lane's server lists beside A's.
PLATFORM_CHECKS = ("platform.jwt_secret", "platform.plugin_secrets")
SEVERITIES = frozenset({"ok", "info", "warning", "error"})


@pytest.fixture(scope="module")
def test_server():
    """The lane's server: the runner's shared backend, or one started in this process (_TestingServerManager)."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


@dataclass(frozen=True)
class _LaneSessions:
    """The Cookie headers of the fixture administrator and of the fixture member, on the lane's server."""

    admin: dict[str, str]
    member: dict[str, str]


def _session_cookie(response: httpx.Response) -> Optional[str]:
    """The value the answer's Set-Cookie gives the session cookie, found by name; None when it sets none."""
    for header in response.headers.get_list("set-cookie"):
        name, _, value = header.split(";", 1)[0].partition("=")
        if name.strip() == COOKIE and value:
            return value
    return None


def _sign_in(credentials: tuple[str, str], *, superuser: bool) -> dict[str, str]:
    """A fixture user signed in on the lane's server, its role checked first: the Cookie header of its session."""
    username, password = credentials
    login = httpx.post(f"{API_BASE}/auth/login", json={"username": username, "password": password}, timeout=TIMEOUT)
    assert login.status_code == 200, f"setup: signing in as {username} on the lane's server: {login.status_code} {login.text} — the api setup (db populate) creates the fixture users"
    user = login.json().get("user") or {}
    assert user.get("is_superuser") is superuser, f"precondition: {username} must {'' if superuser else 'not '}be an administrator, as db populate makes it; this unit changes no role: {user}"
    value = _session_cookie(login)
    assert value, f"setup: the login of {username} set no {COOKIE} cookie: {login.headers.get_list('set-cookie')}"
    return {"Cookie": f"{COOKIE}={value}"}


@pytest.fixture(scope="module")
def lane_sessions(test_server) -> _LaneSessions:
    """``e2e_test_admin`` and ``e2e_test_user`` signed in on the lane's server, once for the module."""
    return _LaneSessions(admin=_sign_in(E2E_ADMIN, superuser=True), member=_sign_in(E2E_USER, superuser=False))


async def _get_checks(headers: Optional[dict[str, str]] = None) -> httpx.Response:
    """``GET /api/v1/security/checks`` on the lane's server, from an empty client: only ``headers`` decide what is sent."""
    async with httpx.AsyncClient() as client:
        return await client.get(f"{API_BASE}{CHECKS_PATH}", headers=headers or {}, timeout=TIMEOUT)


def _expected_login_limit() -> tuple[str, str]:
    """The severity ``accounts.login_limit`` must have on the lane's server, and why (the module's docstring)."""
    explicit = os.environ.get(LIMIT_VARIABLE, "").strip().lower()
    if explicit:
        return ("warning" if explicit == "off" else "ok"), f"{LIMIT_VARIABLE}={explicit} in the environment the lane's server inherits: an explicit value wins over the runner's default"
    if shared_server_mode():
        return "warning", f"the runner's backend is `dev.py server --test`, which sets {LIMIT_VARIABLE}=off unless the variable is set"
    return "ok", f"no shared backend: the server runs in this process, {LIMIT_VARIABLE} unset, the limit on by default"


def _items(response: httpx.Response, request: str) -> dict[str, dict[str, Any]]:
    """The items of the 200 by ``check_id``, each check once."""
    assert response.status_code == 200, f"{request}: expected 200, got {response.status_code} {response.text}"
    body = response.json()
    items = body.get("items") if isinstance(body, dict) else None
    assert isinstance(items, list) and all(isinstance(item, dict) and isinstance(item.get("check_id"), str) for item in items), f"{request}: the answer is an object whose items are a list, each with a check_id: {body}"
    by_id = {item["check_id"]: item for item in items}
    assert len(by_id) == len(items), f"{request}: each check once: {[item['check_id'] for item in items]}"
    return by_id


class TestSecurityChecksOnTheLane:
    """The lane's real server, the whole app of main.py: GET requests only."""

    # red until A8a
    @pytest.mark.asyncio
    async def test_the_lanes_server_lists_its_login_limit(self, lane_sessions: _LaneSessions) -> None:
        """SC-LANE-01: ``e2e_test_admin`` → 200, each check once; ``accounts.login_limit`` listed — a ``severity``, an ``i18n_key``, a ``detail`` object —, ``warning`` under the runner, whose backend runs with the limit off (``_expected_login_limit``); ``platform.jwt_secret`` and ``platform.plugin_secrets`` listed too."""
        print_section("SC-LANE-01: the lane's server lists its login limit")
        severity, why = _expected_login_limit()

        response = await _get_checks(lane_sessions.admin)

        by_id = _items(response, "the lane's GET /api/v1/security/checks as e2e_test_admin")
        missing = [check_id for check_id in (LOGIN_LIMIT_CHECK, *PLATFORM_CHECKS) if check_id not in by_id]
        assert not missing, f"the lane's server must list {missing}: {sorted(by_id)}"
        item = by_id[LOGIN_LIMIT_CHECK]
        assert item.get("severity") in SEVERITIES and isinstance(item.get("i18n_key"), str) and item["i18n_key"] and isinstance(item.get("detail"), dict), f"{LOGIN_LIMIT_CHECK} has a severity of {sorted(SEVERITIES)}, an i18n key and a detail object: {item}"
        assert item["severity"] == severity, f"{LOGIN_LIMIT_CHECK} on the lane's server must be {severity} ({why}): {item}"
        print_success(f"{LOGIN_LIMIT_CHECK}: {severity}")

    # red until H5-4
    @pytest.mark.asyncio
    async def test_the_lanes_server_lists_the_owner_email_change_check_once_and_ok(self, lane_sessions: _LaneSessions) -> None:
        """SC-LANE-04 (H5-4): ``e2e_test_admin`` → 200; ``accounts.owner_email_change`` is listed exactly once (``_items`` fails on a repeated id), well formed — a severity, an i18n key, a detail object —, ``ok`` with ``auth.checks.ownerEmailChange.ok``: no host change waits on the lane's instance (not managed, no ``LIBREFOLIO_ADMIN_EMAIL``). The other states are pinned in-process (``test_login_throttle_api.py``, SC-API-OE) and in ``run_config_checks()`` (``test_accounts_checks.py``)."""
        print_section("SC-LANE-04: the lane's server lists the owner email change check")

        response = await _get_checks(lane_sessions.admin)

        by_id = _items(response, "the lane's GET /api/v1/security/checks as e2e_test_admin")
        item = by_id.get(OWNER_EMAIL_CHANGE_CHECK)
        assert item is not None, f"red until H5-4: the lane's server must list {OWNER_EMAIL_CHANGE_CHECK}: {sorted(by_id)}"
        assert item.get("severity") in SEVERITIES and isinstance(item.get("i18n_key"), str) and isinstance(item.get("detail"), dict), f"{OWNER_EMAIL_CHANGE_CHECK} is well formed: {item}"
        assert (item["severity"], item["i18n_key"]) == ("ok", "auth.checks.ownerEmailChange.ok"), f"nothing waits on the lane's instance: {item}"
        print_success(f"{OWNER_EMAIL_CHANGE_CHECK}: ok")

    # red until A8a
    @pytest.mark.asyncio
    async def test_a_member_is_refused_with_403(self, lane_sessions: _LaneSessions) -> None:
        """SC-LANE-02: ``e2e_test_user``, a member → 403."""
        response = await _get_checks(lane_sessions.member)

        assert response.status_code == 403, f"the lane's GET /api/v1/security/checks as e2e_test_user, a member: expected 403, got {response.status_code} {response.text}"

    # red until A8a
    @pytest.mark.asyncio
    async def test_without_a_session_it_is_401(self, test_server) -> None:
        """SC-LANE-03: no session cookie → 401."""
        response = await _get_checks()

        assert response.status_code == 401, f"the lane's GET /api/v1/security/checks without a session: expected 401, got {response.status_code} {response.text}"

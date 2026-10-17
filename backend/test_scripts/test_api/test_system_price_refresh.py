"""
«Aggiornamento prezzi…» (workstream Z, lot Z5): ``GET /api/v1/system/price-refresh``, the status the web app asks for
while the scheduler catches up the missing prices, after an ``X-LibreFolio-Price-Refresh`` header told it a catch-up
runs (plan phase01SleepWake §Z5, N-Z5-1…N-Z5-5).

Under test: ``backend/app/api/v1/system/price_refresh.py``, composed into the system router by
``api/v1/system/__init__.py``, and ``PriceRefreshResponse`` in ``backend/app/schemas/sleep_wake.py``; the tracker itself
(``PRICE_REFRESH`` in ``services/platform/scheduler/scheduler.py``) is pinned by ``services scheduler-price-refresh``.

- PRAPI-001, on the lane's server: without a session, 401.
- PRAPI-002, on the lane's server, signed in as ``e2e_test_user`` (any signed-in user, not only an administrator): 200,
  exactly the six keys ``state``, ``reason``, ``job``, ``since``, ``last_finished_at``, ``last_refreshed``, each of its
  type, ``state`` one of "idle", "starting", "running". Whatever the lane's scheduler is doing, so nothing more.
- PRAPI-003..006, in-process, the process's ``PRICE_REFRESH`` driven by the test: the body is exactly
  ``price_refresh_progress()`` — idle (all null, not refreshed); "starting" for a "wake" with its ``since``; "running"
  for a "return" with its job; idle after a refreshed catch-up with its ``last_finished_at``. Datetimes are ISO 8601 with
  the UTC offset.
- PRAPI-007, ``PriceRefreshResponse``: exactly the six fields; ``state`` and ``reason`` refuse anything outside their
  literals ("tick" is no reason).
- PRAPI-008, OpenAPI and the composition: ``GET /api/v1/system/price-refresh``, tag System, its 200 the
  ``PriceRefreshResponse`` schema with the six properties.

Where the cases run. PRAPI-001..002 ask the lane's backend and only read: the fixture user signs in (its login counters,
which no unit asserts, are the one write), nothing else is written. PRAPI-003..008 run in-process: the system router
under ``/api/v1`` in an app of the test, ``get_current_user`` overridden with a regular user, and the process's
``PRICE_REFRESH`` — this pytest process's, never the lane server's — reset before and after each case. No database is
reached in-process.

Red until the code of Z5 exists: ``PriceRefreshResponse`` does not import, a collection error for the whole module.

Test IDs: PRAPI-001..PRAPI-008
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any, Optional

import httpx
import pytest
from fastapi import FastAPI
from pydantic import ValidationError

from backend.app.api.v1 import auth as auth_api
from backend.app.api.v1 import system as system_api
from backend.app.config import API_V1_PREFIX, get_settings
from backend.app.schemas.sleep_wake import PriceRefreshResponse
from backend.app.services.platform.scheduler import scheduler
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0
ROUTE = "/system/price-refresh"
COOKIE = auth_api.SESSION_COOKIE_NAME
E2E_USER = ("e2e_test_user", "E2eTestPass123!")

#: The literals of the contract, never read from the module under test.
KEYS = {"state", "reason", "job", "since", "last_finished_at", "last_refreshed"}
STATES = {"idle", "starting", "running"}
REASONS = {"startup", "return", "wake"}
IDLE_NEVER = {"state": "idle", "reason": None, "job": None, "since": None, "last_finished_at": None, "last_refreshed": False}


@pytest.fixture(scope="module")
def test_server():
    """The lane's server: the runner's shared backend, or one started in this process (_TestingServerManager)."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


@pytest.fixture
def fresh_price_refresh() -> Iterator[None]:
    """This process's ``PRICE_REFRESH`` reset before and after the case."""
    scheduler.PRICE_REFRESH.reset()
    yield
    scheduler.PRICE_REFRESH.reset()


def _session_cookie(response: httpx.Response) -> Optional[str]:
    """The value the response's Set-Cookie gives the session cookie, found by name; None when it sets none."""
    for header in response.headers.get_list("set-cookie"):
        name, _, value = header.split(";", 1)[0].partition("=")
        if name.strip() == COOKIE and value:
            return value
    return None


def _in_process_app() -> FastAPI:
    """The system router under ``/api/v1``, as ``router.py`` mounts it, ``get_current_user`` overridden with a regular user."""
    app = FastAPI()
    app.include_router(system_api.router, prefix=API_V1_PREFIX)
    app.dependency_overrides[auth_api.get_current_user] = lambda: SimpleNamespace(id=1, username="prapi_user", is_superuser=False)
    return app


async def _get_in_process() -> dict[str, Any]:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=_in_process_app()), base_url="http://price-refresh.test") as client:
        response = await client.get(f"{API_V1_PREFIX}{ROUTE}", timeout=TIMEOUT)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    body = response.json()
    assert isinstance(body, dict) and set(body) == KEYS, f"exactly the six keys: {body!r}"
    return body


def _utc_moment(value: object, what: str) -> datetime:
    """An ISO 8601 string with the UTC offset, parsed."""
    assert isinstance(value, str), f"{what}: an ISO 8601 string, got {value!r}"
    moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    assert moment.tzinfo is not None and moment.utcoffset() == timedelta(0), f"{what}: {value!r} has no UTC offset"
    return moment


def _assert_valid_body(body: Any) -> None:
    """The six keys, each of its type; ``state`` and ``reason`` within their literals."""
    assert isinstance(body, dict) and set(body) == KEYS, f"exactly the six keys: {body!r}"
    assert body["state"] in STATES, body
    assert body["reason"] is None or body["reason"] in REASONS, body
    assert body["job"] is None or (isinstance(body["job"], str) and body["job"]), body
    for key in ("since", "last_finished_at"):
        if body[key] is not None:
            _utc_moment(body[key], key)
    assert isinstance(body["last_refreshed"], bool), body


# =============================================================================
# On the lane's server: what holds whatever its scheduler does
# =============================================================================


@pytest.mark.asyncio
class TestPriceRefreshOnTheLane:
    @pytest.fixture(autouse=True)
    def server(self, test_server):
        yield

    async def test_without_a_session_401(self):
        """PRAPI-001: GET /system/price-refresh without a session → 401."""
        print_section("PRAPI-001: GET /system/price-refresh without a session")

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE}{ROUTE}", timeout=TIMEOUT)

        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print_success("401 ✓")

    async def test_a_signed_in_user_gets_the_six_keys_and_a_valid_state(self):
        """PRAPI-002: ``e2e_test_user`` (not an administrator) → 200, exactly the six keys, each of its type, a valid ``state``."""
        print_section("PRAPI-002: GET /system/price-refresh as e2e_test_user")
        username, password = E2E_USER

        async with httpx.AsyncClient() as client:
            login = await client.post(f"{API_BASE}/auth/login", json={"username": username, "password": password}, timeout=TIMEOUT)
            assert login.status_code == 200, f"Setup: signing in as {username} failed: {login.status_code} {login.text} — the api setup (db populate) creates the fixture users"
            assert login.json().get("user", {}).get("is_superuser") is False, f"Precondition: {username} is a regular user: {login.text}"
            cookie = _session_cookie(login)
            assert cookie, f"Setup: the login of {username} set no {COOKIE} cookie"
            client.cookies.clear()
            response = await client.get(f"{API_BASE}{ROUTE}", headers={"Cookie": f"{COOKIE}={cookie}"}, timeout=TIMEOUT)

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        _assert_valid_body(response.json())
        print_success(f"200, state {response.json()['state']} ✓")


# =============================================================================
# In-process: the states the test chooses
# =============================================================================


@pytest.mark.asyncio
async def test_idle_answers_nothing_pending_and_nothing_remembered(fresh_price_refresh: None) -> None:
    """PRAPI-003: a reset tracker → exactly the idle body, all null, ``last_refreshed`` false."""
    print_section("PRAPI-003: idle")

    body = await _get_in_process()

    assert body == IDLE_NEVER
    print_success("idle ✓")


@pytest.mark.asyncio
async def test_starting_answers_the_reason_and_since(fresh_price_refresh: None) -> None:
    """PRAPI-004: "wake" announced → "starting", reason "wake", no job, ``since`` the moment of the announce, in UTC."""
    print_section("PRAPI-004: starting")
    before = datetime.now(UTC)
    scheduler.PRICE_REFRESH.announce("wake")
    after = datetime.now(UTC)

    body = await _get_in_process()

    assert {key: body[key] for key in ("state", "reason", "job", "last_finished_at", "last_refreshed")} == {"state": "starting", "reason": "wake", "job": None, "last_finished_at": None, "last_refreshed": False}
    assert before <= _utc_moment(body["since"], "since") <= after
    print_success("starting ✓")


@pytest.mark.asyncio
async def test_running_answers_the_job(fresh_price_refresh: None) -> None:
    """PRAPI-005: a "return" run with ``history_sync`` running → "running", reason "return", job "history_sync"."""
    print_section("PRAPI-005: running")
    scheduler.PRICE_REFRESH.run_started("return")
    scheduler.PRICE_REFRESH.job_started("history_sync")

    body = await _get_in_process()

    assert (body["state"], body["reason"], body["job"], body["last_finished_at"], body["last_refreshed"]) == ("running", "return", "history_sync", None, False)
    _utc_moment(body["since"], "since")
    print_success("running ✓")


@pytest.mark.asyncio
async def test_idle_after_a_refreshed_catch_up_answers_when_it_ended(fresh_price_refresh: None) -> None:
    """PRAPI-006: a "startup" catch-up whose job updated 4 items, ended → idle, ``last_finished_at`` its end in UTC, ``last_refreshed`` true."""
    print_section("PRAPI-006: idle after a refreshed catch-up")
    scheduler.PRICE_REFRESH.run_started("startup")
    scheduler.PRICE_REFRESH.job_started("current_price")
    scheduler.PRICE_REFRESH.job_finished(4)
    before = datetime.now(UTC)
    scheduler.PRICE_REFRESH.run_finished()
    after = datetime.now(UTC)

    body = await _get_in_process()

    assert {key: body[key] for key in ("state", "reason", "job", "since", "last_refreshed")} == {"state": "idle", "reason": None, "job": None, "since": None, "last_refreshed": True}
    assert before <= _utc_moment(body["last_finished_at"], "last_finished_at") <= after
    assert body == {**IDLE_NEVER, "last_finished_at": body["last_finished_at"], "last_refreshed": True}
    print_success("idle, refreshed ✓")


def test_the_response_model_has_the_six_fields_and_refuses_what_is_not_a_literal() -> None:
    """PRAPI-007: ``PriceRefreshResponse`` declares exactly the six fields; a state or a reason outside their literals, "tick" included, is refused."""
    print_section("PRAPI-007: PriceRefreshResponse")
    assert set(PriceRefreshResponse.model_fields) == KEYS

    valid = {"state": "running", "reason": "return", "job": "current_price", "since": datetime(2026, 10, 16, 6, 0, tzinfo=UTC), "last_finished_at": None, "last_refreshed": False}
    assert PriceRefreshResponse.model_validate(valid).model_dump() == valid
    for key, wrong in (("state", "done"), ("reason", "tick"), ("reason", "unknown")):
        with pytest.raises(ValidationError):
            PriceRefreshResponse.model_validate({**valid, key: wrong})
    print_success("six fields; literals enforced ✓")


def test_the_route_is_composed_and_documented() -> None:
    """PRAPI-008: ``GET /api/v1/system/price-refresh`` in the OpenAPI of an app holding the system router, tag System, its 200 the ``PriceRefreshResponse`` schema with the six properties."""
    print_section("PRAPI-008: OpenAPI")
    schema = _in_process_app().openapi()

    operation = schema["paths"].get(f"{API_V1_PREFIX}{ROUTE}", {}).get("get")
    assert operation is not None, f"GET {API_V1_PREFIX}{ROUTE} is not served: {sorted(schema['paths'])}"
    assert "System" in operation.get("tags", [])
    reference = operation["responses"]["200"]["content"]["application/json"]["schema"].get("$ref", "")
    assert reference.endswith("/PriceRefreshResponse"), operation["responses"]["200"]
    assert set(schema["components"]["schemas"]["PriceRefreshResponse"]["properties"]) == KEYS
    print_success("served, tagged, documented ✓")

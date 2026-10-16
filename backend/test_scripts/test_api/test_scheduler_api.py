"""
Test: Scheduler API endpoints.

Tests GET /settings/scheduler/state and GET /settings/scheduler/log.
Verifies admin-only access, response structure, and ?since= filter.

Lot Z7c-2 (SAPI-009..SAPI-014): what lot Z7b added to the scheduler reaches the admin panel through these two
endpoints. The state answers, for each job, ``last_items_deferred`` (0), ``retry_at`` (None), ``consecutive_failures``
(0) and ``next_attempt_at`` (None) as ``scheduler_state.json`` holds them; the log passes through each item's
``deferred`` (False) and ``retry_after`` (None), the summaries' ``deferred`` or ``assets_deferred`` / ``fx_deferred``
(0) and each entry's ``retry_at`` (None) instead of dropping them. A file or an entry written before Z7b, without these
keys, stays valid and comes back with the defaults.

Where the cases run. SAPI-001..SAPI-009 ask the lane's backend and only read: the lane's two scheduler files are the
ones ``populate_mock_data`` seeded, shared by every reader of the lane, and this module never writes them. The cases
that need a chosen ``scheduler_state.json`` or ``logs/scheduler_jobs.jsonl`` (SAPI-010..SAPI-014) run in-process
instead: the settings router in an app of the test, ``require_admin`` overridden (SAPI-001..SAPI-007 cover the access),
and ``get_data_dir`` replaced where the scheduler's ``state`` and ``joblog`` modules read it, so both files live in the
test's own ``tmp_path`` — as ``test_scheduler_state.py`` does. The state route still reads the scheduler timezone from
the lane's database: a read. Nothing is written outside ``tmp_path``, so the unit stays write-scoped.

Test IDs: SAPI-001..SAPI-014
"""

import json
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Optional

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

import backend.app.services.platform.scheduler.joblog as joblog_mod
import backend.app.services.platform.scheduler.state as state_mod
from backend.app.api.v1 import settings as settings_api
from backend.app.config import API_V1_PREFIX, get_settings, is_test_mode
from backend.app.db.session import get_async_engine
from backend.app.services.accounts import user_service
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_info, print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0


@pytest.fixture(scope="module")
def test_server():
    """Start test server for all tests in this module."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


# ============================================================================
# Helpers (same pattern as test_settings_api.py)
# ============================================================================

_user_counter = 0
_admin_credentials: Optional[tuple[str, str, str]] = None


def _next_username() -> str:
    global _user_counter
    _user_counter += 1
    return f"sched_api_test_{_user_counter}"


async def _register_and_login(client: httpx.AsyncClient, username: str) -> Optional[str]:
    email = f"{username}@test.com"
    pwd = "TestPass123!"
    await client.post(f"{API_BASE}/auth/register", json={"username": username, "email": email, "password": pwd}, timeout=TIMEOUT)
    resp = await client.post(f"{API_BASE}/auth/login", json={"username": username, "password": pwd}, timeout=TIMEOUT)
    session = resp.cookies.get("session") if resp.status_code == 200 else None
    if session:
        client.cookies.set("session", session)
    return session


async def _promote_to_admin(username: str) -> bool:
    try:
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            success, error = await user_service.set_user_admin(session, username, is_admin=True)
            return success or (error and "already an admin" in error)
    except Exception:
        return False


async def _get_admin_session(client: httpx.AsyncClient) -> str:
    """Get an admin session token, creating and promoting a user if needed."""
    global _admin_credentials

    if _admin_credentials:
        username, _, _ = _admin_credentials
        resp = await client.post(f"{API_BASE}/auth/login", json={"username": username, "password": "TestPass123!"}, timeout=TIMEOUT)
        session = resp.cookies.get("session") if resp.status_code == 200 else None
        if session:
            client.cookies.set("session", session)
            return session

    username = _next_username()
    session = await _register_and_login(client, username)
    assert session, "Could not create user"

    # Check if already admin (first user in empty DB)
    me_resp = await client.get(f"{API_BASE}/auth/me", timeout=TIMEOUT)
    if me_resp.status_code == 200 and me_resp.json().get("user", {}).get("is_superuser"):
        _admin_credentials = (username, "", session)
        return session

    # Promote
    promoted = await _promote_to_admin(username)
    if promoted:
        resp = await client.post(f"{API_BASE}/auth/login", json={"username": username, "password": "TestPass123!"}, timeout=TIMEOUT)
        session = resp.cookies.get("session") if resp.status_code == 200 else None
        if session:
            client.cookies.set("session", session)
            _admin_credentials = (username, "", session)
            return session

    pytest.skip("Cannot obtain admin session")


async def _get_normal_session(client: httpx.AsyncClient) -> str:
    """Create a fresh non-admin user and return session."""
    username = _next_username()
    session = await _register_and_login(client, username)
    assert session, f"Could not create user {username}"
    return session


# ============================================================================
# SAPI-001: Admin → GET /settings/scheduler/state → 200
# ============================================================================


@pytest.mark.asyncio
class TestSchedulerStateAdminOk:
    @pytest.fixture(autouse=True)
    def server(self, test_server):
        yield

    async def test_scheduler_state_admin_ok(self):
        """SAPI-001: Admin → GET /settings/scheduler/state → 200."""
        print_section("SAPI-001: GET /settings/scheduler/state — admin")

        async with httpx.AsyncClient() as client:
            await _get_admin_session(client)
            resp = await client.get(f"{API_BASE}/settings/scheduler/state", timeout=TIMEOUT)

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        print_success("Admin got 200 OK")


# ============================================================================
# SAPI-002: Non-admin → 403
# ============================================================================


@pytest.mark.asyncio
class TestSchedulerStateNonAdmin:
    @pytest.fixture(autouse=True)
    def server(self, test_server):
        yield

    async def test_scheduler_state_non_admin_403(self):
        """SAPI-002: Non-admin user → GET /settings/scheduler/state → 403."""
        print_section("SAPI-002: GET /settings/scheduler/state — non-admin → 403")

        async with httpx.AsyncClient() as client:
            await _get_normal_session(client)
            resp = await client.get(f"{API_BASE}/settings/scheduler/state", timeout=TIMEOUT)

        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
        print_success("Non-admin correctly rejected with 403")


# ============================================================================
# SAPI-003: Unauthenticated → 401
# ============================================================================


@pytest.mark.asyncio
class TestSchedulerStateUnauthenticated:
    @pytest.fixture(autouse=True)
    def server(self, test_server):
        yield

    async def test_scheduler_state_unauthenticated_401(self):
        """SAPI-003: No session cookie → GET /settings/scheduler/state → 401."""
        print_section("SAPI-003: GET /settings/scheduler/state — unauthenticated → 401")

        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{API_BASE}/settings/scheduler/state", timeout=TIMEOUT)

        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
        print_success("Unauthenticated correctly rejected with 401")


# ============================================================================
# SAPI-004: Admin → GET /settings/scheduler/log → 200 + entries list
# ============================================================================


@pytest.mark.asyncio
class TestSchedulerLogAdminOk:
    @pytest.fixture(autouse=True)
    def server(self, test_server):
        yield

    async def test_scheduler_log_admin_ok(self):
        """SAPI-004: Admin → GET /settings/scheduler/log → 200, entries is a list."""
        print_section("SAPI-004: GET /settings/scheduler/log — admin")

        async with httpx.AsyncClient() as client:
            await _get_admin_session(client)
            resp = await client.get(f"{API_BASE}/settings/scheduler/log", timeout=TIMEOUT)

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "entries" in data, "Response must have 'entries' key"
        assert isinstance(data["entries"], list), "'entries' must be a list"
        print_success(f"Admin got 200 OK, entries: {len(data['entries'])} items")


# ============================================================================
# SAPI-005: ?since= future date → entries: []
# ============================================================================


@pytest.mark.asyncio
class TestSchedulerLogSinceFilter:
    @pytest.fixture(autouse=True)
    def server(self, test_server):
        yield

    async def test_scheduler_log_since_future(self):
        """SAPI-005: ?since=2099-01-01T00:00:00Z → entries: [] (no future log entries)."""
        print_section("SAPI-005: GET /settings/scheduler/log?since=2099... → empty")

        async with httpx.AsyncClient() as client:
            await _get_admin_session(client)
            resp = await client.get(
                f"{API_BASE}/settings/scheduler/log",
                params={"since": "2099-01-01T00:00:00Z"},
                timeout=TIMEOUT,
            )

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data["entries"] == [], f"Expected empty entries for far-future since, got: {data['entries']}"
        print_success("?since=2099 → empty entries list ✓")


# ============================================================================
# SAPI-006: Non-admin log → 403
# ============================================================================


@pytest.mark.asyncio
class TestSchedulerLogNonAdmin:
    @pytest.fixture(autouse=True)
    def server(self, test_server):
        yield

    async def test_scheduler_log_non_admin_403(self):
        """SAPI-006: Non-admin user → GET /settings/scheduler/log → 403."""
        print_section("SAPI-006: GET /settings/scheduler/log — non-admin → 403")

        async with httpx.AsyncClient() as client:
            await _get_normal_session(client)
            resp = await client.get(f"{API_BASE}/settings/scheduler/log", timeout=TIMEOUT)

        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
        print_success("Non-admin rejected with 403 ✓")


# ============================================================================
# SAPI-007: Unauthenticated log → 401
# ============================================================================


@pytest.mark.asyncio
class TestSchedulerLogUnauthenticated:
    @pytest.fixture(autouse=True)
    def server(self, test_server):
        yield

    async def test_scheduler_log_unauthenticated_401(self):
        """SAPI-007: No session → GET /settings/scheduler/log → 401."""
        print_section("SAPI-007: GET /settings/scheduler/log — unauthenticated → 401")

        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{API_BASE}/settings/scheduler/log", timeout=TIMEOUT)

        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
        print_success("Unauthenticated log request rejected with 401 ✓")


# ============================================================================
# SAPI-008: State response structure verification
# ============================================================================


@pytest.mark.asyncio
class TestSchedulerStateStructure:
    @pytest.fixture(autouse=True)
    def server(self, test_server):
        yield

    async def test_scheduler_state_structure(self):
        """SAPI-008: State response has required nested fields for both jobs."""
        print_section("SAPI-008: GET /settings/scheduler/state — structure validation")

        async with httpx.AsyncClient() as client:
            await _get_admin_session(client)
            resp = await client.get(f"{API_BASE}/settings/scheduler/state", timeout=TIMEOUT)

        assert resp.status_code == 200
        data = resp.json()

        # Top-level keys
        assert "current_price" in data, "Missing 'current_price'"
        assert "history_sync" in data, "Missing 'history_sync'"
        assert "server_tz" in data, "Missing 'server_tz'"

        # current_price fields
        cp = data["current_price"]
        for field in ("last_run_at", "last_duration_s", "last_status", "last_items_ok", "last_items_err"):
            assert field in cp, f"current_price missing field: {field}"

        # history_sync fields
        hs = data["history_sync"]
        for field in ("last_run_at", "last_duration_s", "last_status", "last_items_ok", "last_items_err"):
            assert field in hs, f"history_sync missing field: {field}"

        # server_tz is a non-empty string
        assert isinstance(data["server_tz"], str), "server_tz must be string"
        assert len(data["server_tz"]) > 0, "server_tz must not be empty"

        print_info(f"server_tz: {data['server_tz']}")
        print_info(f"current_price.last_status: {cp['last_status']}")
        print_success("All required state fields present ✓")


# ============================================================================
# Lot Z7c-2 — the fields and keys lot Z7b added to the scheduler
# ============================================================================

#: The five fields the state route answered before lot Z7b, per job.
_STATE_FIELDS_BEFORE_Z7B = ("last_run_at", "last_duration_s", "last_status", "last_items_ok", "last_items_err")

#: The four fields lot Z7b added to each job's state, with their defaults.
_Z7B_STATE_DEFAULTS = {"last_items_deferred": 0, "retry_at": None, "consecutive_failures": 0, "next_attempt_at": None}


# ============================================================================
# SAPI-009: the lane's state carries the four fields of lot Z7b, in both jobs
# ============================================================================


@pytest.mark.asyncio
class TestSchedulerStateZ7bFieldsOnTheLane:
    @pytest.fixture(autouse=True)
    def server(self, test_server):
        yield

    async def test_scheduler_state_carries_the_z7b_fields(self):
        """SAPI-009: Admin → GET /settings/scheduler/state on the lane's backend → both jobs carry ``last_items_deferred`` and ``consecutive_failures`` (non-negative ints), ``retry_at`` and ``next_attempt_at`` (an ISO-8601 string or null).

        Read only, like SAPI-008: the values are whatever the lane's file holds, so only their presence and types are asserted.
        """
        print_section("SAPI-009: GET /settings/scheduler/state — the fields of lot Z7b on the lane")

        async with httpx.AsyncClient() as client:
            await _get_admin_session(client)
            resp = await client.get(f"{API_BASE}/settings/scheduler/state", timeout=TIMEOUT)

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        for job in ("current_price", "history_sync"):
            missing = [field for field in _Z7B_STATE_DEFAULTS if field not in data[job]]
            assert not missing, f"{job} does not carry {missing}: {data[job]}"
            for field in ("last_items_deferred", "consecutive_failures"):
                value = data[job][field]
                assert isinstance(value, int) and not isinstance(value, bool) and value >= 0, f"{job}.{field} must be a non-negative int, got {value!r}"
            for field in ("retry_at", "next_attempt_at"):
                value = data[job][field]
                assert value is None or (isinstance(value, str) and datetime.fromisoformat(value)), f"{job}.{field} must be an ISO-8601 string or null, got {value!r}"
        print_success("both jobs carry the four fields of lot Z7b ✓")


# ============================================================================
# SAPI-010..SAPI-014, in-process: the scheduler's two files chosen by the test
# ============================================================================


@pytest.fixture
def scheduler_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The test's own data directory for ``scheduler_state.json`` and ``logs/scheduler_jobs.jsonl``.

    ``get_data_dir`` is replaced where the scheduler's ``state`` and ``joblog`` modules read it: the lane's files are
    neither read nor written. ``LIBREFOLIO_NO_SCHEDULER`` is set besides: should this process also host the server
    thread (the module run alone, outside the runner), a scheduler run there would stop at "disabled" before loading or
    saving a state while the replacement is in place.
    """
    if not is_test_mode():
        pytest.fail("LIBREFOLIO_TEST_MODE is not set: the state route reads the scheduler timezone from the configured database, which must be the lane's")
    monkeypatch.setattr(state_mod, "get_data_dir", lambda: tmp_path)
    monkeypatch.setattr(joblog_mod, "get_data_dir", lambda: tmp_path)
    monkeypatch.setenv("LIBREFOLIO_NO_SCHEDULER", "1")
    return tmp_path


def _write_state(data_dir: Path, state: dict[str, Any]) -> None:
    """``scheduler_state.json`` as the scheduler writes it: one object, one object per job."""
    (data_dir / "scheduler_state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")


def _write_log(data_dir: Path, entries: list[dict[str, Any]]) -> None:
    """``logs/scheduler_jobs.jsonl`` as the scheduler appends it: one JSON object per line, oldest first."""
    path = data_dir / "logs" / "scheduler_jobs.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(entry, ensure_ascii=False) + "\n" for entry in entries), encoding="utf-8")


def _scheduler_app() -> FastAPI:
    """The settings router under ``/api/v1``, as ``router.py`` mounts it, in an app of the test, ``require_admin`` overridden."""
    app = FastAPI()
    app.include_router(settings_api.router, prefix=API_V1_PREFIX)
    app.dependency_overrides[settings_api.require_admin] = lambda: SimpleNamespace(username="sapi_z7c2_admin", is_superuser=True)
    return app


async def _get_in_process(route: str) -> dict[str, Any]:
    """GET ``/api/v1/settings{route}`` from the app of the test: 200 asserted, the body returned."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=_scheduler_app()), base_url="http://scheduler.test") as client:
        resp = await client.get(f"{API_V1_PREFIX}/settings{route}", timeout=TIMEOUT)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    return resp.json()


def _not_carried(written: Any, returned: Any, path: str) -> list[str]:
    """Where ``returned`` does not carry ``written`` intact: every key written, at any depth, with its value.

    ``120`` and ``120.0`` are the same number (``retry_after`` is a float); a bool must come back a bool.
    """
    if isinstance(written, dict):
        if not isinstance(returned, dict):
            return [f"{path}: an object was written, got {returned!r}"]
        return [gap for key, value in written.items() for gap in ([f"{path}.{key}: dropped"] if key not in returned else _not_carried(value, returned[key], f"{path}.{key}"))]
    if isinstance(written, list):
        if not isinstance(returned, list) or len(returned) != len(written):
            return [f"{path}: {len(written)} items were written, got {returned!r}"]
        return [gap for index, (item, back) in enumerate(zip(written, returned, strict=True)) for gap in _not_carried(item, back, f"{path}[{index}]")]
    if isinstance(written, bool) or isinstance(returned, bool):
        return [] if written is returned else [f"{path}: wrote {written!r}, got {returned!r}"]
    return [] if written == returned else [f"{path}: wrote {written!r}, got {returned!r}"]


#: A state written before lot Z7b: the six fields each job had, as ``populate_mock_data`` still writes them.
_STATE_BEFORE_Z7B: dict[str, dict[str, Any]] = {
    "current_price": {"last_run_at": "2026-06-07T18:00:00+00:00", "last_duration_s": 4.25, "last_status": "partial", "last_items_ok": 7, "last_items_err": 1, "last_error": None},
    "history_sync": {"last_run_at": "2026-06-07T23:00:00+00:00", "last_duration_s": 17.5, "last_status": "ok", "last_items_ok": 9, "last_items_err": 0, "last_error": None},
}

#: A state written by lot Z7b, as ``save_state`` writes it: the four new fields set, a value of its own for each field of each job, so that a swapped field or job shows.
_STATE_Z7B: dict[str, dict[str, Any]] = {
    "current_price": {**_STATE_BEFORE_Z7B["current_price"], "last_items_deferred": 2, "retry_at": "2026-06-08T10:05:00+00:00", "consecutive_failures": 1, "next_attempt_at": "2026-06-08T10:02:00+00:00"},
    "history_sync": {**_STATE_BEFORE_Z7B["history_sync"], "last_items_deferred": 3, "retry_at": "2026-06-08T06:30:00+00:00", "consecutive_failures": 4, "next_attempt_at": "2026-06-08T07:00:00+00:00"},
}

#: Log entries written before lot Z7b, shaped as ``populate_mock_data`` writes them: no ``deferred``, no ``retry_after``, no ``retry_at``.
_PRICE_ENTRY_BEFORE_Z7B: dict[str, Any] = {
    "ts": "2026-06-07T12:10:00+00:00",
    "job": "current_price",
    "duration_s": 5.87,
    "status": "partial",
    "summary": {"ok": 1, "err": 1},
    "items": [
        {"asset_id": 1, "name": "Apple Inc.", "ok": True},
        {"asset_id": 3, "name": "Tesla Inc.", "ok": False, "error": "Provider timeout after 30s"},
    ],
}
_HISTORY_ENTRY_BEFORE_Z7B: dict[str, Any] = {
    "ts": "2026-06-07T23:00:00+00:00",
    "job": "history_sync",
    "duration_s": 18.73,
    "status": "partial",
    "summary": {"assets_ok": 1, "assets_err": 1, "fx_ok": 1, "fx_err": 1},
    "assets": [
        {"asset_id": 1, "name": "Apple Inc.", "status": "ok", "provider": "yfinance", "prices_changed": 3, "events_changed": 0},
        {"asset_id": 3, "name": "Tesla Inc.", "status": "error", "provider": "yfinance", "prices_changed": 0, "events_changed": 0, "errors": ["HTTPError 429: Too Many Requests"]},
    ],
    "fx": [
        {"pair": "EUR-USD", "base": "EUR", "quote": "USD", "status": "ok", "provider": "ecb", "points_changed": 3},
        {"pair": "EUR-JPY", "base": "EUR", "quote": "JPY", "status": "error", "provider": "boe", "points_changed": 0, "errors": ["Provider returned empty dataset for date range"]},
    ],
}

#: Log entries written by lot Z7b, shaped as ``build_current_price_entry`` / ``build_history_sync_entry`` write them: a deferred item has
#: ``"deferred": true`` and ``retry_after`` when known, an item not deferred has neither key, every summary counts the deferred apart.
_PRICE_ENTRY_Z7B: dict[str, Any] = {
    "ts": "2026-06-08T10:00:00+00:00",
    "job": "current_price",
    "duration_s": 2.5,
    "status": "partial",
    "summary": {"ok": 1, "err": 1, "deferred": 1},
    "retry_at": "2026-06-08T10:02:00+00:00",
    "items": [
        {"asset_id": 81, "name": "Fetched", "ok": True},
        {"asset_id": 82, "name": "Paused", "ok": False, "deferred": True, "retry_after": 120, "error": "too many requests"},
        {"asset_id": 83, "name": "Broken", "ok": False, "error": "quote unavailable"},
    ],
}
_HISTORY_ENTRY_Z7B: dict[str, Any] = {
    "ts": "2026-06-08T06:00:00+00:00",
    "job": "history_sync",
    "duration_s": 9.5,
    "status": "partial",
    "summary": {"assets_ok": 1, "assets_err": 0, "assets_deferred": 2, "fx_ok": 1, "fx_err": 0, "fx_deferred": 1},
    "retry_at": "2026-06-08T06:05:00+00:00",
    "assets": [
        {"asset_id": 91, "name": "Synced", "status": "ok", "provider": "mockprov", "prices_changed": 3, "events_changed": 0},
        {"asset_id": 92, "name": "Refused", "status": "failed", "deferred": True, "retry_after": 300, "errors": ["too many requests"], "prices_changed": 0, "events_changed": 0},
        {"asset_id": 93, "name": "Partly Saved, Refused", "status": "ok", "deferred": True, "errors": ["too many requests"], "provider": "mockprov", "prices_changed": 2, "events_changed": 0},
    ],
    "fx": [
        {"pair": "EUR-USD", "status": "ok", "base": "EUR", "quote": "USD", "provider": "MOCKFX", "points_changed": 4},
        {"pair": "GBP-USD", "status": "failed", "deferred": True, "retry_after": 45, "base": "GBP", "quote": "USD", "errors": ["too many requests"], "points_changed": 0},
    ],
}

#: One log as an upgraded instance holds it, oldest first: the entries of before lot Z7b, then those of Z7b.
_LOG_ACROSS_Z7B = [_HISTORY_ENTRY_BEFORE_Z7B, _PRICE_ENTRY_BEFORE_Z7B, _HISTORY_ENTRY_Z7B, _PRICE_ENTRY_Z7B]

_ITEM_DEFAULTS = {"deferred": False, "retry_after": None}


def _answered(written: dict[str, Any]) -> dict[str, Any]:
    """What the log route must answer for ``written``: the entry intact, and every key of lot Z7b it lacks at its default."""
    if written["job"] == "current_price":
        return {"retry_at": None, **written, "summary": {"deferred": 0, **written["summary"]}, "items": [{**_ITEM_DEFAULTS, **item} for item in written["items"]]}
    return {
        "retry_at": None,
        **written,
        "summary": {"assets_deferred": 0, "fx_deferred": 0, **written["summary"]},
        "assets": [{**_ITEM_DEFAULTS, **item} for item in written["assets"]],
        "fx": [{**_ITEM_DEFAULTS, **item} for item in written["fx"]],
    }


async def _read_log_across_z7b(data_dir: Path) -> dict[str, Any]:
    """The log route's answer over ``_LOG_ACROSS_Z7B``: all four entries are there, and nothing else (the log is the test's own)."""
    _write_log(data_dir, _LOG_ACROSS_Z7B)
    body = await _get_in_process("/scheduler/log")
    assert sorted((entry.get("ts"), entry.get("job")) for entry in body["entries"]) == sorted((entry["ts"], entry["job"]) for entry in _LOG_ACROSS_Z7B), f"the log route must answer the four entries of the test's log: {body['entries']}"
    return body


def _entry(body: dict[str, Any], written: dict[str, Any]) -> dict[str, Any]:
    """The answered entry for ``written``: the one of its job at its timestamp (each entry of the test's log has its own)."""
    found = [entry for entry in body["entries"] if entry.get("ts") == written["ts"] and entry.get("job") == written["job"]]
    assert len(found) == 1, f"expected one {written['job']} entry at {written['ts']}, got {len(found)}"
    return found[0]


@pytest.mark.asyncio
class TestSchedulerStateZ7bFields:
    async def test_scheduler_state_answers_the_z7b_fields_it_holds(self, scheduler_data_dir: Path):
        """SAPI-010: ``scheduler_state.json`` holding the four fields of lot Z7b, set → GET /settings/scheduler/state answers them for each job, beside the five fields of before, unchanged."""
        print_section("SAPI-010: GET /settings/scheduler/state — the fields of lot Z7b, set")
        _write_state(scheduler_data_dir, _STATE_Z7B)

        data = await _get_in_process("/scheduler/state")

        for job in ("current_price", "history_sync"):
            expected = {field: _STATE_Z7B[job][field] for field in (*_STATE_FIELDS_BEFORE_Z7B, *_Z7B_STATE_DEFAULTS)}
            answered = {field: data[job].get(field, "<missing>") for field in expected}
            assert answered == expected, f"{job}: the state route must answer what scheduler_state.json holds"
            print_info(f"{job}: deferred={answered['last_items_deferred']} retry_at={answered['retry_at']} failures={answered['consecutive_failures']} next_attempt_at={answered['next_attempt_at']}")
        print_success("each job's four fields answered as the file holds them ✓")

    @pytest.mark.parametrize("state_file", ["written before Z7b", "absent"])
    async def test_scheduler_state_without_the_z7b_fields_answers_their_defaults(self, scheduler_data_dir: Path, state_file: str):
        """SAPI-011: ``scheduler_state.json`` written before lot Z7b (the six fields of before only), or no file at all → each job's four new fields are answered at their defaults: 0, null, 0, null; the fields of before keep their values."""
        print_section(f"SAPI-011: GET /settings/scheduler/state — a state file {state_file}")
        if state_file == "absent":
            assert not (scheduler_data_dir / "scheduler_state.json").exists(), "premise: the test's data directory holds no state file"
            before = {job: {"last_run_at": None, "last_duration_s": None, "last_status": None, "last_items_ok": 0, "last_items_err": 0} for job in ("current_price", "history_sync")}
        else:
            _write_state(scheduler_data_dir, _STATE_BEFORE_Z7B)
            before = {job: {field: _STATE_BEFORE_Z7B[job][field] for field in _STATE_FIELDS_BEFORE_Z7B} for job in ("current_price", "history_sync")}

        data = await _get_in_process("/scheduler/state")

        for job in ("current_price", "history_sync"):
            assert {field: data[job].get(field, "<missing>") for field in _Z7B_STATE_DEFAULTS} == _Z7B_STATE_DEFAULTS, f"{job}: the four fields of lot Z7b must come back at their defaults"
            assert {field: data[job].get(field, "<missing>") for field in _STATE_FIELDS_BEFORE_Z7B} == before[job], f"{job}: the fields of before must keep their values"
        print_success("the four fields at their defaults, the others as they were ✓")


@pytest.mark.asyncio
class TestSchedulerLogZ7bKeys:
    async def test_scheduler_log_passes_a_deferred_price_item_through(self, scheduler_data_dir: Path):
        """SAPI-012: a current-price entry of lot Z7b — one item ``deferred: true`` with ``retry_after: 120``, ``summary.deferred`` 1, a ``retry_at`` — comes back intact; its items not deferred come back ``deferred: false``, ``retry_after: null``."""
        print_section("SAPI-012: GET /settings/scheduler/log — a deferred current-price item")

        body = await _read_log_across_z7b(scheduler_data_dir)

        gaps = _not_carried(_answered(_PRICE_ENTRY_Z7B), _entry(body, _PRICE_ENTRY_Z7B), "current_price entry")
        assert not gaps, "the log route must pass the keys of lot Z7b through:\n" + "\n".join(gaps)
        print_success("deferred item, retry_after, summary.deferred and retry_at intact ✓")

    async def test_scheduler_log_passes_deferred_history_items_through(self, scheduler_data_dir: Path):
        """SAPI-013: a history-sync entry of lot Z7b — ``assets_deferred`` 2 and ``fx_deferred`` 1, two assets and one pair ``deferred: true`` (one of the assets with status ``ok``, deferred whatever its status, and without ``retry_after``), a ``retry_at`` — comes back intact; the asset and the pair not deferred come back ``deferred: false``, ``retry_after: null``."""
        print_section("SAPI-013: GET /settings/scheduler/log — deferred history assets and FX pairs")

        body = await _read_log_across_z7b(scheduler_data_dir)

        gaps = _not_carried(_answered(_HISTORY_ENTRY_Z7B), _entry(body, _HISTORY_ENTRY_Z7B), "history_sync entry")
        assert not gaps, "the log route must pass the keys of lot Z7b through:\n" + "\n".join(gaps)
        print_success("assets_deferred, fx_deferred, deferred items and retry_at intact ✓")

    @pytest.mark.parametrize("written", [_PRICE_ENTRY_BEFORE_Z7B, _HISTORY_ENTRY_BEFORE_Z7B], ids=["current_price", "history_sync"])
    async def test_scheduler_log_answers_an_entry_written_before_z7b_with_the_defaults(self, scheduler_data_dir: Path, written: dict[str, Any]):
        """SAPI-014: an entry written before lot Z7b, without any of its keys, stays valid in the same log as the entries of Z7b: it comes back intact, with ``retry_at`` null, the summary's deferred counters 0 and every item ``deferred: false``, ``retry_after: null``."""
        print_section(f"SAPI-014: GET /settings/scheduler/log — a {written['job']} entry written before Z7b")

        body = await _read_log_across_z7b(scheduler_data_dir)

        gaps = _not_carried(_answered(written), _entry(body, written), f"{written['job']} entry")
        assert not gaps, "an entry written before lot Z7b must come back with the defaults:\n" + "\n".join(gaps)
        print_success("old entry intact, with the defaults of lot Z7b ✓")

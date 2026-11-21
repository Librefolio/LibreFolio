"""Live API contracts for the authenticated Tool transport boundary."""

from __future__ import annotations

import asyncio
import gzip
import json
import re
from collections.abc import Awaitable, Callable, Iterator
from dataclasses import replace
from types import SimpleNamespace
from typing import NoReturn
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI

from backend.app.api.v1 import tools as tools_api
from backend.app.api.v1.auth import get_current_user
from backend.app.config import get_settings
from backend.app.schemas.tools import (
    ToolBatchMetrics,
    ToolCatalogResponse,
    ToolComputeBatchRequest,
    ToolComputeBatchResponse,
    ToolComputeFailure,
    ToolComputeProgress,
    ToolDescriptor,
    ToolDiagnosticsResponse,
    ToolDiscoveryFailure,
    ToolError,
    ToolItemMetrics,
    ToolMemoryCapability,
    ToolPlatformPolicy,
    ToolPoolResourceReservation,
    ToolPoolSnapshot,
    ToolResourceCapabilities,
)
from backend.app.services.platform.middleware import MIDDLEWARE_STACK, install_middleware
from backend.app.services.tools.base import ToolExecutionError
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_services import _reb_small_requests as reb

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0

PASSWORD = "ToolApiTestPass123!"

SEMVER_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)" r"(-((0|[1-9][0-9]*|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*)" r"(\.(0|[1-9][0-9]*|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*))*))?" r"(\+[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?$")
FINGERPRINT_RE = re.compile(r"^[a-f0-9]{64}$")
TOKEN_RE = re.compile(r"^[!-~]{1,64}$")
TOOL_CODE_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")

CATALOG_KEYS = {"catalog_version", "policy", "items", "unavailable"}
DESCRIPTOR_KEYS = {
    "tool_code",
    "contract_version",
    "implementation_version",
    "schema_fingerprint",
    "name",
    "description",
    "name_i18n_key",
    "description_i18n_key",
    "category",
    "icon_key",
    "ui",
    "documentation",
    "input_schema",
    "output_schema",
    "operations",
}
UI_KEYS = {"kind", "component_key", "version"}
POLICY_KEYS = {
    "workers",
    "max_batch_items",
    "max_pending_items",
    "max_pending_per_principal",
    "max_batches_per_principal",
    "max_request_bytes",
    "max_parameter_bytes",
    "max_result_bytes",
    "max_response_bytes",
    "envelope_reserve_bytes",
    "max_json_depth",
    "queue_timeout_ms",
    "engine_timeout_ms",
    "job_timeout_ms",
    "soft_timeout_ms",
    "output_reserve_ms",
    "cleanup_timeout_ms",
    "ingress_timeout_ms",
    "response_reserve_ms",
    "request_timeout_ms",
    "client_timeout_ms",
    "memory_limit_bytes",
}
COMPUTE_KEYS = {
    "request_id",
    "results",
    "metrics",
    "success_count",
    "failed_count",
}
FAILURE_KEYS = {
    "correlation_id",
    "tool_code",
    "contract_version",
    "implementation_version",
    "schema_fingerprint",
    "execution_id",
    "metrics",
    "status",
    "error",
}
ERROR_KEYS = {"code", "retryable", "issues", "issue_count"}
ITEM_METRICS_KEYS = {
    "queue_wait_ms",
    "startup_ms",
    "input_validation_ms",
    "compute_ms",
    "output_validation_ms",
    "serialization_ms",
    "execution_ms",
    "cleanup_ms",
    "total_ms",
    "resources",
    "worker_exit_code",
}
DIAGNOSTICS_KEYS = {
    "scope",
    "runtime_id",
    "policy",
    "loaded",
    "failures",
    "capabilities",
    "pool",
}
POOL_KEYS = {
    "available",
    "active",
    "queued",
    "pending",
    "degraded_lanes",
    "completed",
    "failed",
    "resources",
}
RESOURCE_RESERVATION_KEYS = {
    "memory_capacity_bytes",
    "memory_reserved_bytes",
}


@pytest.fixture(scope="module")
def test_server():
    """Attach to the runner-owned backend, or start its in-process test server."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


async def _login_normal_user(client: httpx.AsyncClient) -> str:
    async def register_unique_user() -> tuple[str, bool]:
        username = f"tool_api_{uuid4().hex[:16]}"
        response = await client.post(
            f"{API_BASE}/auth/register",
            json={
                "username": username,
                "email": f"{username}@example.com",
                "password": PASSWORD,
            },
            timeout=TIMEOUT,
        )
        assert response.status_code == 201, response.text
        assert response.json()["user"]["is_active"] is True
        return username, bool(response.json()["user"]["is_superuser"])

    username, is_admin = await register_unique_user()
    if is_admin:
        username, is_admin = await register_unique_user()
    assert is_admin is False
    response = await client.post(
        f"{API_BASE}/auth/login",
        json={"username": username, "password": PASSWORD},
        timeout=TIMEOUT,
    )
    assert response.status_code == 200, response.text
    assert response.json()["user"]["is_active"] is True
    assert response.json()["user"]["is_superuser"] is False
    session = response.cookies.get("session")
    assert session is not None
    client.cookies.set("session", session)
    return username


def _unknown_envelope(
    *,
    duplicate_correlation: bool = False,
    scenario_marker: str | None = None,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    request_id = f"request-{uuid4().hex}"
    duplicate_correlation_id = f"correlation-{uuid4().hex}" if duplicate_correlation else None

    def item() -> dict[str, object]:
        marker = uuid4().hex
        parameters: dict[str, object] = {
            "operation": f"probe_{marker}",
        }
        if scenario_marker is not None:
            parameters["scenario"] = scenario_marker
        return {
            "correlation_id": duplicate_correlation_id or f"correlation-{uuid4().hex}",
            "tool_code": f"unknown_{uuid4().hex}",
            "contract_version": f"1.0.0+{uuid4().hex}",
            "implementation_version": f"1.0.0+{uuid4().hex}",
            "schema_fingerprint": f"{uuid4().hex}{uuid4().hex}",
            "parameters": parameters,
        }

    items = [item() for _ in range(2)]
    return {"request_id": request_id, "items": items}, items


def _assert_identity_contract(
    actual: dict[str, object],
    expected: dict[str, object],
) -> None:
    for key in (
        "correlation_id",
        "tool_code",
        "contract_version",
        "implementation_version",
        "schema_fingerprint",
    ):
        assert actual[key] == expected[key]
    assert TOKEN_RE.fullmatch(str(actual["correlation_id"]))
    assert TOOL_CODE_RE.fullmatch(str(actual["tool_code"]))
    assert SEMVER_RE.fullmatch(str(actual["contract_version"]))
    assert SEMVER_RE.fullmatch(str(actual["implementation_version"]))
    assert FINGERPRINT_RE.fullmatch(str(actual["schema_fingerprint"]))


def _recursive_strings(value: object) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _recursive_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _recursive_strings(child)


def _assert_pool_is_structural(
    pool: dict[str, object],
    policy: dict[str, object],
) -> None:
    ToolPoolSnapshot.model_validate(pool)
    assert set(pool) == POOL_KEYS
    assert isinstance(pool["available"], bool)
    for key in (
        "active",
        "queued",
        "pending",
        "degraded_lanes",
        "completed",
        "failed",
    ):
        assert isinstance(pool[key], int)
        assert pool[key] >= 0
    assert pool["active"] <= policy["workers"]
    assert pool["degraded_lanes"] <= pool["active"]
    assert pool["active"] + pool["queued"] <= pool["pending"]
    assert pool["pending"] <= policy["max_pending_items"]
    assert pool["failed"] <= pool["completed"]
    resources = pool["resources"]
    assert set(resources) == RESOURCE_RESERVATION_KEYS
    assert resources["memory_capacity_bytes"] == policy["workers"] * policy["memory_limit_bytes"]
    assert 0 <= resources["memory_reserved_bytes"] <= resources["memory_capacity_bytes"]
    assert resources["memory_reserved_bytes"] <= pool["active"] * policy["memory_limit_bytes"]


def _assert_capabilities_are_structural(capabilities: dict[str, object]) -> None:
    assert set(capabilities) == {"memory"}
    memory = capabilities["memory"]
    assert set(memory) == {"mode", "observation_interval_ms"}
    assert memory["mode"] in {
        "cgroup_v2_hard",
        "process_tree_observed",
        "unavailable",
    }
    if memory["mode"] == "process_tree_observed":
        assert type(memory["observation_interval_ms"]) is int
        assert memory["observation_interval_ms"] > 0
    else:
        assert memory["observation_interval_ms"] is None


@pytest.mark.asyncio
async def test_compute_route_uses_the_batch_effective_request_budget(
    monkeypatch,
):
    envelope, _items = _unknown_envelope()
    batch = ToolComputeBatchRequest.model_validate(envelope)
    captured = {}
    response_sentinel = object()

    class _Executor:
        @staticmethod
        def batch_request_timeout_ms(actual_batch):
            assert actual_batch is batch
            return 59_000

    def execution_request(request, *, timeout_ms):
        captured["request"] = request
        captured["timeout_ms"] = timeout_ms
        return request

    async def compute_until_disconnect(actual_batch, request, principal_key, settings=None):
        captured["batch"] = actual_batch
        captured["bounded_request"] = request
        captured["principal_key"] = principal_key
        return response_sentinel

    request = object()
    monkeypatch.setattr(tools_api, "get_tool_executor", lambda: _Executor())
    monkeypatch.setattr(tools_api, "_execution_request", execution_request)
    monkeypatch.setattr(
        tools_api,
        "_compute_until_disconnect",
        compute_until_disconnect,
    )

    response = await tools_api.compute_tools(
        batch,
        request,
        type("_ActiveUser", (), {"id": 17})(),
    )

    assert response is response_sentinel
    assert captured == {
        "request": request,
        "timeout_ms": 59_000,
        "batch": batch,
        "bounded_request": request,
        "principal_key": "17",
    }


@pytest.mark.asyncio
async def test_disconnect_cancels_compute_before_any_engine_start(
    monkeypatch,
):
    envelope, _items = _unknown_envelope()
    batch = ToolComputeBatchRequest.model_validate(envelope)
    entered = asyncio.Event()
    cancelled = asyncio.Event()
    blocker = asyncio.Event()
    engine_starts = []

    class _Executor:
        async def compute(self, actual_batch, *, principal_key, request_started, settings=None):
            assert actual_batch is batch
            assert principal_key == "owned-principal"
            assert request_started == 123.0
            entered.set()
            try:
                await blocker.wait()
                engine_starts.append(True)
            except asyncio.CancelledError:
                cancelled.set()
                raise

    class _DisconnectRequest:
        started = 123.0

        @staticmethod
        async def receive():
            await entered.wait()
            return {"type": "http.disconnect"}

    monkeypatch.setattr(tools_api, "get_tool_executor", lambda: _Executor())

    response = await tools_api._compute_until_disconnect(
        batch,
        _DisconnectRequest(),
        "owned-principal",
    )

    assert response.status_code == 499
    assert entered.is_set()
    assert cancelled.is_set()
    assert engine_starts == []


# ---------------------------------------------------------------------------
# Request deadlines, in process. Each test builds its own app around the Tool
# router and replaces the collaborators where the route reads them, so the only
# clock that decides the outcome is the route's own deadline. No server, no DB.
# ---------------------------------------------------------------------------

IN_PROCESS_BASE_URL = "http://tools.test"
CATALOG_PATH = "/api/v1/tools/catalog"
DIAGNOSTICS_PATH = "/api/v1/tools/diagnostics"
COMPUTE_PATH = "/api/v1/tools/compute"
DEADLINE_EXCEEDED = {"detail": "Tool request deadline exceeded"}
# The documented budget of the catalogue and diagnostics routes, capped by the
# policy's request_timeout_ms (the default of ``_execution_request``).
READ_BUDGET_MS = 20_000
# A deadline in the wrong place is slow, not absent: a 503 that arrives only when
# a 20 s budget runs out still looks bounded. The ceiling is far above the
# 10-100 ms deadlines these tests configure and far below that budget, so it
# tells the configured deadline apart from a fallback one.
DEADLINE_CEILING_S = 5.0


class _TransportExecutor:
    """The executor surface the Tool routes read; reaching the compute path is recorded and refused."""

    def __init__(self, policy: ToolPlatformPolicy) -> None:
        self.policy = policy
        # The routes read the CPUs the executor was built with (TURNI of project 67); none here: no CPU table applies.
        self.usable_cpus = None
        self.runtime_id = f"runtime-{uuid4().hex}"
        self.compute_path_calls: list[str] = []

    def snapshot(self) -> ToolPoolSnapshot:
        return ToolPoolSnapshot(
            available=True,
            active=0,
            queued=0,
            pending=0,
            degraded_lanes=0,
            completed=0,
            failed=0,
            resources=ToolPoolResourceReservation(
                memory_capacity_bytes=self.policy.workers * self.policy.memory_limit_bytes,
                memory_reserved_bytes=0,
            ),
        )

    def resource_capabilities(self) -> ToolResourceCapabilities:
        return ToolResourceCapabilities(memory=ToolMemoryCapability(mode="unavailable"))

    def batch_request_timeout_ms(self, batch: ToolComputeBatchRequest) -> int:
        self.compute_path_calls.append("batch_request_timeout_ms")
        raise AssertionError("the compute path was entered although authentication never resolved")

    async def compute(self, batch: ToolComputeBatchRequest, *, principal_key: str, request_started: float | None = None) -> ToolComputeBatchResponse:
        self.compute_path_calls.append("compute")
        raise AssertionError("the compute path was entered although authentication never resolved")


def _install_transport_fakes(
    monkeypatch: pytest.MonkeyPatch,
    policy: ToolPlatformPolicy,
) -> tuple[_TransportExecutor, dict[str, list[ToolPlatformPolicy]]]:
    """Serve ``policy`` from a fake executor and record every catalogue build, per builder."""
    executor = _TransportExecutor(policy)
    builds: dict[str, list[ToolPlatformPolicy]] = {
        "build_tool_catalog": [],
        "effective_catalog_entries": [],
    }

    def build_tool_catalog(actual_policy: ToolPlatformPolicy, *, usable_cpus: int | None = None) -> ToolCatalogResponse:
        builds["build_tool_catalog"].append(actual_policy)
        return ToolCatalogResponse(catalog_version="2", policy=actual_policy, items=[], unavailable=[])

    def effective_catalog_entries(actual_policy: ToolPlatformPolicy, *, usable_cpus: int | None = None) -> tuple[list[ToolDescriptor], tuple[ToolDiscoveryFailure, ...]]:
        builds["effective_catalog_entries"].append(actual_policy)
        return [], ()

    monkeypatch.setattr(tools_api, "get_tool_executor", lambda: executor)
    monkeypatch.setattr(tools_api, "build_tool_catalog", build_tool_catalog)
    monkeypatch.setattr(tools_api, "effective_catalog_entries", effective_catalog_entries)
    return executor, builds


def _stalled_authentication(entries: list[str]) -> Callable[[], Awaitable[NoReturn]]:
    """An authentication that never answers, so only the route's own deadline can end the request."""

    async def authenticate() -> NoReturn:
        entries.append("authenticate")
        await asyncio.Event().wait()  # nobody sets it
        raise AssertionError("unreachable: nobody sets this event")

    return authenticate


async def _request_tool_route(
    authenticate: Callable[[], Awaitable[object]],
    method: str,
    path: str,
    **request_kwargs: object,
) -> httpx.Response:
    """Send one request through a fresh app whose ``get_current_user`` is ``authenticate``."""
    app = FastAPI()
    app.include_router(tools_api.router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = authenticate
    ceiling = asyncio.timeout(DEADLINE_CEILING_S)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=IN_PROCESS_BASE_URL) as client:
        try:
            async with ceiling:
                return await client.request(method, path, **request_kwargs)
        except TimeoutError:
            if not ceiling.expired():
                raise
            pytest.fail(f"{method} {path} was still unanswered after {DEADLINE_CEILING_S} s: the configured route deadline did not end it")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "response_model", "builder"),
    [
        pytest.param(CATALOG_PATH, ToolCatalogResponse, "build_tool_catalog", id="catalog"),
        pytest.param(DIAGNOSTICS_PATH, ToolDiagnosticsResponse, "effective_catalog_entries", id="diagnostics"),
    ],
)
async def test_read_routes_authenticate_within_their_own_budget_not_the_ingress_window(
    monkeypatch,
    path,
    response_model,
    builder,
):
    """A route without a request body has nothing to ingest: authentication spends its read budget.

    FastAPI resolves ``get_current_user`` before the endpoint body moves the deadline to the
    read budget. If the ingress window still covers that step, a slow authentication (cookie,
    JWT, one database read under load) answers 503 "Tool request deadline exceeded" and the
    catalogue is never built: the About plugin diagnostics panel breaks.
    """
    policy = ToolPlatformPolicy(ingress_timeout_ms=50)
    read_budget_ms = min(READ_BUDGET_MS, policy.request_timeout_ms)
    # The simulated cost of a slow collaborator, not a wait for a condition:
    # five ingress windows, yet under 2 % of the read budget.
    authentication_ms = 5 * policy.ingress_timeout_ms
    assert authentication_ms * 50 <= read_budget_ms
    _executor, builds = _install_transport_fakes(monkeypatch, policy)

    async def slow_authentication() -> SimpleNamespace:
        await asyncio.sleep(authentication_ms / 1000)
        return SimpleNamespace(id=1)

    response = await _request_tool_route(slow_authentication, "GET", path)

    assert response.status_code == 200, f"GET {path} -> HTTP {response.status_code} {response.text}; {builder} calls: {len(builds[builder])}"
    assert response_model.model_validate(response.json()).policy == policy
    assert builds[builder] == [policy]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        pytest.param(CATALOG_PATH, id="catalog"),
        pytest.param(DIAGNOSTICS_PATH, id="diagnostics"),
    ],
)
async def test_read_route_is_still_bounded_by_its_request_budget(monkeypatch, path):
    """Authentication outside the ingress window is still bounded: by ``request_timeout_ms``."""
    policy = ToolPlatformPolicy(
        ingress_timeout_ms=10,
        queue_timeout_ms=10,
        engine_timeout_ms=10,
        soft_timeout_ms=20,
        output_reserve_ms=10,
        job_timeout_ms=30,
        cleanup_timeout_ms=10,
        response_reserve_ms=10,
        request_timeout_ms=100,
        client_timeout_ms=200,
    )
    _executor, builds = _install_transport_fakes(monkeypatch, policy)
    authentications: list[str] = []

    response = await _request_tool_route(_stalled_authentication(authentications), "GET", path)

    assert response.status_code == 503, response.text
    assert response.json() == DEADLINE_EXCEEDED
    assert authentications == ["authenticate"]
    assert builds == {"build_tool_catalog": [], "effective_catalog_entries": []}


@pytest.mark.asyncio
async def test_compute_keeps_its_ingress_window(monkeypatch):
    """Compute carries a request body: its admission, authentication included, stays in the ingress window.

    The default policy gives compute no budget shorter than 20 s once the endpoint runs, so
    only the 50 ms ingress window can answer within the ceiling.
    """
    policy = ToolPlatformPolicy(ingress_timeout_ms=50)
    executor, _builds = _install_transport_fakes(monkeypatch, policy)
    envelope, _items = _unknown_envelope()
    authentications: list[str] = []

    response = await _request_tool_route(
        _stalled_authentication(authentications),
        "POST",
        COMPUTE_PATH,
        json=envelope,
    )

    assert response.status_code == 503, response.text
    assert response.json() == DEADLINE_EXCEEDED
    assert authentications == ["authenticate"]
    assert executor.compute_path_calls == []


@pytest.mark.asyncio
async def test_tools_endpoints_require_authentication(test_server):
    envelope, _items = _unknown_envelope()
    requests = (
        ("GET", f"{API_BASE}/tools/catalog", {}),
        ("POST", f"{API_BASE}/tools/compute", {"json": envelope}),
        ("GET", f"{API_BASE}/tools/diagnostics", {}),
    )

    async with httpx.AsyncClient() as client:
        for method, url, request_kwargs in requests:
            response = await client.request(
                method,
                url,
                timeout=TIMEOUT,
                **request_kwargs,
            )
            assert response.status_code == 401


@pytest.mark.asyncio
async def test_tools_catalog_is_strict_and_read_only(test_server):
    async with httpx.AsyncClient() as client:
        await _login_normal_user(client)
        before = await client.get(
            f"{API_BASE}/tools/diagnostics",
            timeout=TIMEOUT,
        )
        response = await client.get(
            f"{API_BASE}/tools/catalog",
            timeout=TIMEOUT,
        )
        after = await client.get(
            f"{API_BASE}/tools/diagnostics",
            timeout=TIMEOUT,
        )

    assert before.status_code == 200
    assert response.status_code == 200
    assert after.status_code == 200

    payload = response.json()
    catalog = ToolCatalogResponse.model_validate(payload)
    assert set(payload) == CATALOG_KEYS
    assert catalog.catalog_version == "2"
    assert set(payload["policy"]) == POLICY_KEYS
    descriptors = [ToolDescriptor.model_validate(item) for item in payload["items"]]
    for raw_descriptor, descriptor in zip(payload["items"], descriptors, strict=True):
        assert set(raw_descriptor) == DESCRIPTOR_KEYS
        assert set(raw_descriptor["ui"]) == UI_KEYS
        assert descriptor.ui.kind == "custom"
        assert SEMVER_RE.fullmatch(descriptor.ui.version)
        assert "ui_contract_version" not in raw_descriptor["ui"]
    descriptor_codes = {descriptor.tool_code for descriptor in descriptors}
    assert len(descriptor_codes) == len(descriptors)
    assert descriptor_codes.isdisjoint(item["tool_code"] for item in payload["unavailable"] if item["tool_code"] is not None)

    before_payload = before.json()
    after_payload = after.json()
    for diagnostics_payload in (before_payload, after_payload):
        diagnostics = ToolDiagnosticsResponse.model_validate(diagnostics_payload)
        assert set(diagnostics_payload) == DIAGNOSTICS_KEYS
        assert {item.tool_code for item in diagnostics.loaded} == descriptor_codes
        assert all(set(failure) == {"tool_code", "filename", "reason"} for failure in diagnostics_payload["failures"])
        _assert_capabilities_are_structural(diagnostics_payload["capabilities"])

    assert before_payload["runtime_id"] == after_payload["runtime_id"]
    assert before_payload["policy"] == payload["policy"] == after_payload["policy"]
    _assert_pool_is_structural(before_payload["pool"], before_payload["policy"])
    _assert_pool_is_structural(after_payload["pool"], after_payload["policy"])
    # Other authenticated callers may advance process-local counters between reads.
    completed_delta = after_payload["pool"]["completed"] - before_payload["pool"]["completed"]
    failed_delta = after_payload["pool"]["failed"] - before_payload["pool"]["failed"]
    assert completed_delta >= 0
    assert 0 <= failed_delta <= completed_delta


@pytest.mark.asyncio
async def test_tools_compute_unknown_tool_preserves_item_identity(test_server):
    envelope, items = _unknown_envelope()

    async with httpx.AsyncClient() as client:
        await _login_normal_user(client)
        response = await client.post(
            f"{API_BASE}/tools/compute",
            json=envelope,
            timeout=TIMEOUT,
        )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert set(payload) == COMPUTE_KEYS
    validated = ToolComputeBatchResponse.model_validate({key: value for key, value in payload.items() if key not in {"success_count", "failed_count"}})
    assert payload["request_id"] == envelope["request_id"]
    assert validated.request_id == envelope["request_id"]
    assert TOKEN_RE.fullmatch(str(payload["request_id"]))
    assert len(payload["results"]) == len(items)
    expected_correlations = [item["correlation_id"] for item in items]
    assert len(set(expected_correlations)) == len(expected_correlations)
    assert len({item["tool_code"] for item in items}) == len(items)
    assert [result["correlation_id"] for result in payload["results"]] == expected_correlations
    assert payload["success_count"] == 0
    assert payload["failed_count"] == len(items)
    assert set(payload["metrics"]) == {"server_processing_ms"}
    assert isinstance(payload["metrics"]["server_processing_ms"], int)
    assert payload["metrics"]["server_processing_ms"] >= 0

    for result, item in zip(payload["results"], items, strict=True):
        ToolComputeFailure.model_validate(result)
        assert set(result) == FAILURE_KEYS
        _assert_identity_contract(result, item)
        assert result["status"] == "error"
        assert result["execution_id"] is None
        assert result["error"] == {
            "code": "unknown_tool",
            "retryable": False,
            "issues": [],
            "issue_count": 0,
        }
        assert set(result["error"]) == ERROR_KEYS
        assert set(result["metrics"]) == ITEM_METRICS_KEYS
        assert result["metrics"]["total_ms"] >= 0
        assert all(value is None for key, value in result["metrics"].items() if key != "total_ms")


@pytest.mark.asyncio
async def test_tools_compute_duplicate_correlations_is_sanitized(test_server):
    scenario_marker = f"raw-scenario-{uuid4().hex}"
    envelope, items = _unknown_envelope(
        duplicate_correlation=True,
        scenario_marker=scenario_marker,
    )
    correlation_ids = {str(item["correlation_id"]) for item in items}
    assert len(items) == 2
    assert len(correlation_ids) == 1
    assert len({item["tool_code"] for item in items}) == len(items)
    assert all(isinstance(item["parameters"], dict) and item["parameters"].get("scenario") == scenario_marker for item in items)

    async with httpx.AsyncClient() as client:
        await _login_normal_user(client)
        response = await client.post(
            f"{API_BASE}/tools/compute",
            json=envelope,
            timeout=TIMEOUT,
        )

    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid Tool request envelope"}
    private_values = [
        scenario_marker,
        str(envelope["request_id"]),
        *correlation_ids,
    ]
    assert all(value not in response.text for value in private_values)


@pytest.mark.asyncio
async def test_tools_diagnostics_is_strict_safe_for_normal_user(test_server):
    async with httpx.AsyncClient() as client:
        username = await _login_normal_user(client)
        catalog_response = await client.get(
            f"{API_BASE}/tools/catalog",
            timeout=TIMEOUT,
        )
        response = await client.get(
            f"{API_BASE}/tools/diagnostics",
            timeout=TIMEOUT,
        )

    assert catalog_response.status_code == 200, catalog_response.text
    assert response.status_code == 200, response.text
    catalog = ToolCatalogResponse.model_validate(catalog_response.json())
    payload = response.json()
    diagnostics = ToolDiagnosticsResponse.model_validate(payload)
    assert set(payload) == DIAGNOSTICS_KEYS
    assert diagnostics.scope == "api_process"
    assert TOKEN_RE.fullmatch(payload["runtime_id"])
    assert set(payload["policy"]) == POLICY_KEYS
    assert {item.tool_code for item in diagnostics.loaded} == {item.tool_code for item in catalog.items}
    assert all(set(failure) == {"tool_code", "filename", "reason"} for failure in payload["failures"])
    _assert_capabilities_are_structural(payload["capabilities"])
    _assert_pool_is_structural(payload["pool"], payload["policy"])

    serialized_strings = "\n".join(_recursive_strings(payload)).lower()
    for forbidden in (
        username.lower(),
        PASSWORD.lower(),
    ):
        assert forbidden not in serialized_strings


# ---------------------------------------------------------------------------
# The streaming route (lot V1 of project 67): one JSON line per progress message, then the result of /compute
# ---------------------------------------------------------------------------

COMPUTE_STREAM_PATH = "/api/v1/tools/compute/stream"
NDJSON = "application/x-ndjson"


def _ndjson(body: bytes) -> list[dict[str, object]]:
    assert body.endswith(b"\n"), "every line, the last one too, ends with a newline"
    return [json.loads(line) for line in body.decode("utf-8").split("\n") if line]


async def _stream(client: httpx.AsyncClient, envelope: dict[str, object]) -> tuple[httpx.Response, list[dict[str, object]]]:
    async with client.stream("POST", f"{API_BASE}/tools/compute/stream", json=envelope, headers={"Accept-Encoding": "gzip"}, timeout=TIMEOUT) as response:
        body = b"".join([chunk async for chunk in response.aiter_bytes()])
    assert response.status_code == 200, body
    assert response.headers["content-type"].startswith(NDJSON)
    assert "content-encoding" not in response.headers, "the stream is never compressed: gzip would hold the lines back"
    return response, _ndjson(body)


def _without_run_details(result: dict[str, object]) -> dict[str, object]:
    """A result without what changes from one run to the next: the execution id and the metrics."""
    return {key: value for key, value in result.items() if key not in {"execution_id", "metrics"}}


@pytest.mark.asyncio
async def test_stream_route_ends_with_the_same_result_as_compute(test_server):
    """Same request, same user: the stream's last line is ``{kind: "result", response}`` where ``response`` has the shape of
    the ``POST /tools/compute`` answer and the same ``result``; every line before it is a progress line."""
    async with httpx.AsyncClient() as client:
        await _login_normal_user(client)
        catalog = (await client.get(f"{API_BASE}/tools/catalog", timeout=TIMEOUT)).json()
        descriptor = next(item for item in catalog["items"] if item["tool_code"] == "portfolio_rebalancer")
        identity = {key: descriptor[key] for key in ("tool_code", "contract_version", "implementation_version", "schema_fingerprint")}
        parameters = {**reb.t4(), "operation": "preview"}

        def envelope() -> dict[str, object]:
            return {"request_id": f"request-{uuid4().hex}", "items": [{"correlation_id": "stream-same", **identity, "parameters": parameters}]}

        computed = await client.post(f"{API_BASE}/tools/compute", json=envelope(), timeout=TIMEOUT)
        streamed_envelope = envelope()
        _response, lines = await _stream(client, streamed_envelope)

    assert computed.status_code == 200, computed.text
    *progress, last = lines
    assert all(line["kind"] == "progress" for line in progress)
    assert set(last) == {"kind", "response"} and last["kind"] == "result"
    streamed = last["response"]
    assert set(streamed) == set(computed.json()) == COMPUTE_KEYS
    assert streamed["request_id"] == streamed_envelope["request_id"]
    ToolComputeBatchResponse.model_validate({key: value for key, value in streamed.items() if key not in {"success_count", "failed_count"}})
    (streamed_item,) = streamed["results"]
    (computed_item,) = computed.json()["results"]
    assert streamed_item["status"] == computed_item["status"] == "success", streamed_item
    assert _without_run_details(streamed_item) == _without_run_details(computed_item)


@pytest.mark.asyncio
async def test_tool_without_phases_streams_only_the_result(test_server):
    """No declared phase, no progress line: the stream is the result line alone, with today's failures intact."""
    envelope, items = _unknown_envelope()
    async with httpx.AsyncClient() as client:
        await _login_normal_user(client)
        _response, lines = await _stream(client, envelope)

    (line,) = lines
    assert line["kind"] == "result"
    assert [result["error"]["code"] for result in line["response"]["results"]] == ["unknown_tool"] * len(items)
    assert [result["correlation_id"] for result in line["response"]["results"]] == [item["correlation_id"] for item in items]


# In process: the real router behind the app's whole middleware stack (``MIDDLEWARE_STACK``, GZip on any size), driven
# at the ASGI level, so that what is sent and when is observed message by message (httpx's ASGI transport would hand
# over the whole body at the end).


def _failure_response(batch: ToolComputeBatchRequest) -> ToolComputeBatchResponse:
    results = [
        ToolComputeFailure(
            status="error",
            error=ToolError(code="unknown_tool", retryable=False),
            correlation_id=item.correlation_id,
            tool_code=item.tool_code,
            contract_version=item.contract_version,
            implementation_version=item.implementation_version,
            schema_fingerprint=item.schema_fingerprint,
            execution_id=None,
            metrics=ToolItemMetrics(total_ms=0),
        )
        for item in batch.items
    ]
    return ToolComputeBatchResponse(request_id=batch.request_id, results=results, metrics=ToolBatchMetrics(server_processing_ms=0))


def _progress(batch: ToolComputeBatchRequest, phase: str, step: int | None = None, total: int | None = None) -> ToolComputeProgress:
    return ToolComputeProgress(kind="progress", correlation_id=batch.items[0].correlation_id, phase=phase, step=step, total=total, elapsed_ms=1)


class _StreamExecutor(_TransportExecutor):
    """An executor whose compute is scripted by the test: it may report progress, wait, fail or be cancelled."""

    def __init__(self, policy: ToolPlatformPolicy, script: Callable[..., Awaitable[ToolComputeBatchResponse]]) -> None:
        super().__init__(policy)
        self.script = script

    def batch_request_timeout_ms(self, batch: ToolComputeBatchRequest) -> int:
        return self.policy.request_timeout_ms

    async def compute(self, batch, *, principal_key, request_started=None, settings=None, on_progress=None):
        return await self.script(batch, on_progress)


async def _drive_stream(
    monkeypatch,
    script,
    envelope: dict[str, object],
    *,
    disconnect: asyncio.Event,
    on_body: Callable[[bytes], None] = lambda body: None,
    policy: ToolPlatformPolicy | None = None,
) -> list[dict]:
    """POST the stream route of a fresh app — the Tool router behind the app's whole ``MIDDLEWARE_STACK``, its GZip on
    any size — and return every ASGI message it sends."""
    policy = policy or ToolPlatformPolicy()
    executor = _StreamExecutor(policy, script)
    monkeypatch.setattr(tools_api, "get_tool_executor", lambda: executor)
    app = FastAPI()
    app.include_router(tools_api.router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1)
    stack = tuple(replace(entry, options={**entry.options, "minimum_size": 1}) if entry.name == "gzip" else entry for entry in MIDDLEWARE_STACK)
    install_middleware(app, stack)
    body = json.dumps(envelope).encode()
    received = False
    messages: list[dict] = []

    async def receive() -> dict:
        nonlocal received
        if not received:
            received = True
            return {"type": "http.request", "body": body, "more_body": False}
        await disconnect.wait()
        return {"type": "http.disconnect"}

    async def send(message: dict) -> None:
        messages.append(message)
        if message["type"] == "http.response.body" and message.get("body"):
            on_body(message["body"])

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},  # what uvicorn reports here: Starlette listens for the disconnect
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": COMPUTE_STREAM_PATH,
        "raw_path": COMPUTE_STREAM_PATH.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [(b"host", b"tools.test"), (b"content-type", b"application/json"), (b"accept-encoding", b"gzip"), (b"content-length", str(len(body)).encode())],
        "client": ("127.0.0.1", 50000),
        "server": ("tools.test", 80),
    }
    async with asyncio.timeout(DEADLINE_CEILING_S):
        await app(scope, receive, send)
    return messages


def _start(messages: list[dict]) -> tuple[int, dict[bytes, bytes]]:
    start = next(message for message in messages if message["type"] == "http.response.start")
    return start["status"], dict(start["headers"])


@pytest.mark.asyncio
async def test_stream_route_sends_progress_before_the_result_through_gzip(monkeypatch):
    """The first progress line leaves the server before the calculation ends, uncompressed, behind the real GZip middleware:
    the script only finishes once the transport has sent that line."""
    envelope, _items = _unknown_envelope()
    line_sent = asyncio.Event()

    async def script(batch, on_progress):
        on_progress(_progress(batch, "validate"))
        await line_sent.wait()  # never set if the stream is held back: the ceiling then fails the test
        on_progress(_progress(batch, "search", 1, 2))
        return _failure_response(batch)

    messages = await _drive_stream(monkeypatch, script, envelope, disconnect=asyncio.Event(), on_body=lambda body: line_sent.set() if b'"progress"' in body else None)

    status, headers = _start(messages)
    assert status == 200
    assert headers[b"content-type"].startswith(NDJSON.encode())
    assert b"content-encoding" not in headers
    lines = _ndjson(b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body"))
    assert [(line["kind"], line.get("phase"), line.get("step"), line.get("total")) for line in lines] == [("progress", "validate", None, None), ("progress", "search", 1, 2), ("result", None, None, None)]
    assert lines[0]["correlation_id"] == envelope["items"][0]["correlation_id"]
    assert lines[-1]["response"]["request_id"] == envelope["request_id"]


@pytest.mark.asyncio
async def test_stream_route_disconnect_cancels_the_compute(monkeypatch):
    """Closing the browser after the first line cancels the calculation, as on ``/compute``; no result line follows."""
    envelope, _items = _unknown_envelope()
    disconnect = asyncio.Event()
    cancelled = asyncio.Event()

    async def script(batch, on_progress):
        on_progress(_progress(batch, "validate"))
        try:
            await asyncio.Event().wait()  # nobody sets it: only a cancellation ends this calculation
        except asyncio.CancelledError:
            cancelled.set()
            raise
        raise AssertionError("unreachable")

    messages = await _drive_stream(monkeypatch, script, envelope, disconnect=disconnect, on_body=lambda body: disconnect.set())
    async with asyncio.timeout(DEADLINE_CEILING_S):
        await cancelled.wait()

    body = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")
    assert [line["kind"] for line in _ndjson(body)] == ["progress"]


@pytest.mark.asyncio
@pytest.mark.parametrize(("code", "status_code"), [("queue_full", 429), ("service_unavailable", 503)])
async def test_stream_route_admission_errors_stay_http_statuses(monkeypatch, code, status_code):
    """A refusal before any job starts is the HTTP status of ``/compute``, never a 200 stream."""
    envelope, _items = _unknown_envelope()

    async def script(batch, on_progress):
        raise ToolExecutionError(code, retryable=True)

    messages = await _drive_stream(monkeypatch, script, envelope, disconnect=asyncio.Event())

    status, headers = _start(messages)
    assert status == status_code
    body = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")
    if headers.get(b"content-encoding") == b"gzip":  # an ordinary JSON answer, compressed like any other
        body = gzip.decompress(body)
    assert json.loads(body) == {"detail": {"code": code, "retryable": True}}


@pytest.mark.asyncio
async def test_stream_route_deadline_ends_the_stream_without_a_result_and_cancels(monkeypatch):
    """A calculation still running at the request's deadline: the stream ends without its result line (the client reads
    a broken answer) and the calculation is cancelled, as ``/compute`` would end it."""
    policy = ToolPlatformPolicy(
        ingress_timeout_ms=10,
        queue_timeout_ms=10,
        engine_timeout_ms=10,
        soft_timeout_ms=20,
        output_reserve_ms=10,
        job_timeout_ms=30,
        cleanup_timeout_ms=10,
        response_reserve_ms=10,
        request_timeout_ms=300,
        client_timeout_ms=400,
    )
    envelope, _items = _unknown_envelope()
    cancelled = asyncio.Event()

    async def script(batch, on_progress):
        on_progress(_progress(batch, "validate"))
        try:
            await asyncio.Event().wait()  # nobody sets it: only the deadline's cancellation ends this calculation
        except asyncio.CancelledError:
            cancelled.set()
            raise
        raise AssertionError("unreachable")

    messages = await _drive_stream(monkeypatch, script, envelope, disconnect=asyncio.Event(), policy=policy)
    async with asyncio.timeout(DEADLINE_CEILING_S):
        await cancelled.wait()

    status, _headers = _start(messages)
    assert status == 200
    body = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")
    assert [line["kind"] for line in _ndjson(body)] == ["progress"]


@pytest.mark.asyncio
async def test_stream_route_unexpected_failure_before_any_line_is_not_a_stream(monkeypatch):
    """A calculation that fails before any line is an HTTP error, as on ``/compute``: never a 200 with an empty stream."""
    envelope, _items = _unknown_envelope()

    async def script(batch, on_progress):
        raise RuntimeError("private failure")

    with pytest.raises(RuntimeError, match="private failure"):
        await _drive_stream(monkeypatch, script, envelope, disconnect=asyncio.Event())

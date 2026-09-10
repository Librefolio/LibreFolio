"""Live API contracts for the authenticated Tool transport boundary."""

from __future__ import annotations

import re
from collections.abc import Iterator
from uuid import uuid4

import httpx
import pytest

from backend.app.config import get_settings
from backend.app.schemas.tools import (
    ToolCatalogResponse,
    ToolComputeBatchResponse,
    ToolComputeFailure,
    ToolDescriptor,
    ToolDiagnosticsResponse,
    ToolPoolSnapshot,
)
from backend.test_scripts.test_server_helper import _TestingServerManager

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0

PASSWORD = "ToolApiTestPass123!"

SEMVER_RE = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(-((0|[1-9][0-9]*|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*)"
    r"(\.(0|[1-9][0-9]*|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*))*))?"
    r"(\+[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?$"
)
FINGERPRINT_RE = re.compile(r"^[a-f0-9]{64}$")
TOKEN_RE = re.compile(r"^[!-~]{1,64}$")
TOOL_CODE_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")

CATALOG_KEYS = {"catalog_version", "policy", "items", "unavailable"}
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
    "job_timeout_ms",
    "soft_timeout_ms",
    "output_reserve_ms",
    "cleanup_timeout_ms",
    "ingress_timeout_ms",
    "response_reserve_ms",
    "request_timeout_ms",
    "client_timeout_ms",
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
}
DIAGNOSTICS_KEYS = {
    "scope",
    "runtime_id",
    "policy",
    "loaded",
    "failures",
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
    assert catalog.catalog_version == "1"
    assert set(payload["policy"]) == POLICY_KEYS
    descriptors = [ToolDescriptor.model_validate(item) for item in payload["items"]]
    descriptor_codes = {descriptor.tool_code for descriptor in descriptors}
    assert len(descriptor_codes) == len(descriptors)
    assert descriptor_codes.isdisjoint(
        item["tool_code"]
        for item in payload["unavailable"]
        if item["tool_code"] is not None
    )

    before_payload = before.json()
    after_payload = after.json()
    for diagnostics_payload in (before_payload, after_payload):
        diagnostics = ToolDiagnosticsResponse.model_validate(diagnostics_payload)
        assert set(diagnostics_payload) == DIAGNOSTICS_KEYS
        assert {item.tool_code for item in diagnostics.loaded} == descriptor_codes
        assert all(
            set(failure) == {"tool_code", "filename", "reason"}
            for failure in diagnostics_payload["failures"]
        )

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
    validated = ToolComputeBatchResponse.model_validate(
        {
            key: value
            for key, value in payload.items()
            if key not in {"success_count", "failed_count"}
        }
    )
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
        assert all(
            value is None
            for key, value in result["metrics"].items()
            if key != "total_ms"
        )


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
    assert all(
        isinstance(item["parameters"], dict)
        and item["parameters"].get("scenario") == scenario_marker
        for item in items
    )

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
    assert {item.tool_code for item in diagnostics.loaded} == {
        item.tool_code for item in catalog.items
    }
    assert all(
        set(failure) == {"tool_code", "filename", "reason"}
        for failure in payload["failures"]
    )
    _assert_pool_is_structural(payload["pool"], payload["policy"])

    serialized_strings = "\n".join(_recursive_strings(payload)).lower()
    for forbidden in (
        username.lower(),
        PASSWORD.lower(),
    ):
        assert forbidden not in serialized_strings

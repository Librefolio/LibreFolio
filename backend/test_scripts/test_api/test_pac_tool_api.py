"""Live authenticated API contract for the PAC/Rebalancer Tool bundle."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.db.session import get_async_engine
from backend.app.schemas.pac_allocator import (
    PAC_ANALYZE_OUTPUT_ADAPTER,
    REBALANCE_ANALYZE_OUTPUT_ADAPTER,
    PacAnalyzeInvalid,
    PacAnalyzeReady,
    RebalanceAnalyzeReady,
)
from backend.app.schemas.tools import (
    ToolCatalogResponse,
    ToolComputeBatchResponse,
    ToolComputeFailure,
    ToolComputeSuccess,
    ToolDescriptor,
    ToolItemMetrics,
)
from backend.app.services import user_service
from backend.app.services.tools.schema import schema_fingerprint
from backend.test_scripts.test_db_config import verify_test_database
from backend.test_scripts.test_server_helper import _TestingServerManager

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0
PASSWORD = "PacToolApiTestPass123!"
SOLE_ADMIN_DELETE_DETAIL = "Cannot delete account: you are the only administrator"

EXPECTED_TOOL_CODES = frozenset(
    {
        "pac_allocator",
        "portfolio_rebalancer",
    }
)
EXPECTED_METADATA = {
    "pac_allocator": {
        "icon_key": "calculator",
        "component_key": "pac-allocator",
        "documentation": "user/tools/pac-allocator/",
        "name_i18n_key": "tools.pacAllocator.name",
        "description_i18n_key": "tools.pacAllocator.description",
    },
    "portfolio_rebalancer": {
        "icon_key": "scale",
        "component_key": "portfolio-rebalancer",
        "documentation": "user/tools/portfolio-rebalancer/",
        "name_i18n_key": "tools.portfolioRebalancer.name",
        "description_i18n_key": "tools.portfolioRebalancer.description",
    },
}
ITEM_METRIC_FIELDS = {
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
}


@pytest.fixture(scope="module")
def test_server():
    """Attach to the one backend owned by the test runner."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to attach to the test server")
        yield server_manager


async def _register_and_login(
    client: httpx.AsyncClient,
) -> dict[str, object]:
    username = f"pac_tool_{uuid4().hex}"
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
    registered = response.json()["user"]

    response = await client.post(
        f"{API_BASE}/auth/login",
        json={"username": username, "password": PASSWORD},
        timeout=TIMEOUT,
    )
    assert response.status_code == 200, response.text
    assert response.json()["user"]["id"] == registered["id"]
    assert response.cookies.get("session") is not None
    return registered


@asynccontextmanager
async def _authenticated_client() -> AsyncIterator[tuple[httpx.AsyncClient, dict[str, object]]]:
    async with httpx.AsyncClient() as client:
        user = await _register_and_login(client)
        try:
            yield client, user
        finally:
            response = await client.delete(
                f"{API_BASE}/auth/users/me",
                timeout=TIMEOUT,
            )
            if response.status_code == 400 and response.json().get("detail") == SOLE_ADMIN_DELETE_DETAIL:
                is_test_db, _reason = verify_test_database()
                assert is_test_db, "Refusing sole-admin cleanup outside test data"
                async with AsyncSession(get_async_engine()) as session:
                    assert await user_service.delete_user(
                        session,
                        int(user["id"]),
                    )
            else:
                assert response.status_code == 200, response.text


async def _catalog(
    client: httpx.AsyncClient,
) -> tuple[ToolCatalogResponse, dict[str, ToolDescriptor]]:
    response = await client.get(f"{API_BASE}/tools/catalog", timeout=TIMEOUT)
    assert response.status_code == 200, response.text
    catalog = ToolCatalogResponse.model_validate(response.json(), strict=True)
    descriptors = {descriptor.tool_code: descriptor for descriptor in catalog.items if descriptor.tool_code in EXPECTED_TOOL_CODES}
    assert set(descriptors) == EXPECTED_TOOL_CODES
    return catalog, descriptors


def _compute_item(
    descriptor: ToolDescriptor,
    correlation_id: str,
    parameters: dict[str, object],
) -> dict[str, object]:
    return {
        "correlation_id": correlation_id,
        "tool_code": descriptor.tool_code,
        "contract_version": descriptor.contract_version,
        "implementation_version": descriptor.implementation_version,
        "schema_fingerprint": descriptor.schema_fingerprint,
        "parameters": parameters,
    }


def _transport(payload: dict[str, object]) -> ToolComputeBatchResponse:
    return ToolComputeBatchResponse.model_validate(
        {key: value for key, value in payload.items() if key not in {"success_count", "failed_count"}},
        strict=True,
    )


def _assert_complete_success_metrics(metrics: ToolItemMetrics) -> None:
    values = metrics.model_dump(mode="json")
    assert set(values) == ITEM_METRIC_FIELDS
    resources = values.pop("resources")
    assert resources is not None
    assert set(resources) == {"memory"}
    assert set(resources["memory"]) == {
        "mode",
        "limit_bytes",
        "peak_observed_bytes",
    }
    assert resources["memory"]["mode"] in {
        "cgroup_v2_hard",
        "process_tree_observed",
    }
    assert type(resources["memory"]["limit_bytes"]) is int
    assert resources["memory"]["limit_bytes"] > 0
    peak = resources["memory"]["peak_observed_bytes"]
    assert peak is None or (type(peak) is int and peak >= 0)
    for value in values.values():
        assert type(value) is int
        assert value >= 0
    assert values["total_ms"] >= values["execution_ms"]
    assert values["execution_ms"] >= values["compute_ms"]


def _assert_success_identity(
    result: ToolComputeSuccess,
    descriptor: ToolDescriptor,
    correlation_id: str,
) -> None:
    assert result.correlation_id == correlation_id
    assert result.tool_code == descriptor.tool_code
    assert result.contract_version == descriptor.contract_version
    assert result.implementation_version == descriptor.implementation_version
    assert result.schema_fingerprint == descriptor.schema_fingerprint
    assert result.execution_id
    _assert_complete_success_metrics(result.metrics)


def _available_value(fact: dict[str, Any]) -> Any:
    assert fact["availability"] == "available"
    assert fact["reason_codes"] == []
    return fact["value"]


def _repeated_eur_contributions() -> list[dict[str, str]]:
    return [
        {
            "currency": "EUR",
            "amount": "0.100000000001",
            "monetary_step": "0.000000000001",
        },
        {
            "currency": "EUR",
            "amount": "0.200000000002",
            "monetary_step": "0.000000000001",
        },
    ]


def _pac_parameters() -> dict[str, object]:
    return {
        "operation": "analyze",
        "report_currency": "EUR",
        "as_of_date": "2026-09-14",
        "assets": [
            {
                "instrument_key": "api-pac-alpha",
                "name": "PAC Alpha",
            },
            {
                "instrument_key": "api-pac-beta",
                "name": "PAC Beta",
            },
        ],
        "targets": [
            {
                "instrument_key": "api-pac-alpha",
                "target_percent": "25",
            },
            {
                "instrument_key": "api-pac-beta",
                "target_percent": "75",
            },
        ],
        "cash_balances": [{"currency": "EUR", "amount": "99.699999999997"}],
        "contributions": _repeated_eur_contributions(),
        "valuation_rates": [],
    }


def _rebalancer_parameters() -> dict[str, object]:
    return {
        "operation": "analyze",
        "report_currency": "EUR",
        "as_of_date": "2026-09-14",
        "holdings": [
            {
                "row_key": "api-broker-a::alpha",
                "instrument_key": "api-rebalance-alpha",
                "name": "Rebalance Alpha",
                "quantity": "1",
                "quote": {
                    "raw_price": "60",
                    "currency": "EUR",
                    "quote_base_quantity": 1,
                    "reference_date": "2026-09-14",
                },
            },
            {
                "row_key": "api-broker-b::beta",
                "instrument_key": "api-rebalance-beta",
                "name": "Rebalance Beta",
                "quantity": "1",
                "quote": {
                    "raw_price": "40",
                    "currency": "EUR",
                    "quote_base_quantity": 1,
                    "reference_date": "2026-09-14",
                },
            },
        ],
        "targets": [
            {
                "instrument_key": "api-rebalance-alpha",
                "target_percent": "50",
            },
            {
                "instrument_key": "api-rebalance-beta",
                "target_percent": "50",
            },
        ],
        "cash_balances": [{"currency": "EUR", "amount": "0.699999999997"}],
        "contributions": _repeated_eur_contributions(),
        "valuation_rates": [],
    }


@pytest.mark.asyncio
async def test_catalog_publishes_both_services_with_shared_backend_versions(
    test_server,
):
    async with _authenticated_client() as (client, _user):
        catalog, descriptors = await _catalog(client)

    assert catalog.catalog_version == "2"
    assert all(unavailable.tool_code not in EXPECTED_TOOL_CODES for unavailable in catalog.unavailable)
    assert {descriptor.contract_version for descriptor in descriptors.values()} == {"1.0.0"}
    assert {descriptor.implementation_version for descriptor in descriptors.values()} == {"1.0.0"}
    assert {descriptor.ui.component_key for descriptor in descriptors.values()} == {"pac-allocator", "portfolio-rebalancer"}

    for code, descriptor in descriptors.items():
        metadata = EXPECTED_METADATA[code]
        assert descriptor.category == "allocation"
        assert descriptor.icon_key == metadata["icon_key"]
        assert descriptor.name_i18n_key == metadata["name_i18n_key"]
        assert descriptor.description_i18n_key == metadata["description_i18n_key"]
        assert descriptor.ui.model_dump(mode="json") == {
            "kind": "custom",
            "component_key": metadata["component_key"],
            "version": "1.0.0",
        }
        assert descriptor.documentation.model_dump(mode="json") == {
            "path": metadata["documentation"],
            "version": "1.0.0",
        }
        (operation,) = descriptor.operations
        assert operation.model_dump(mode="json") == {
            "operation": "analyze",
            "pure": True,
            "deterministic": True,
            "deduplication": "none",
            "max_parameter_bytes": 131_072,
            "max_result_bytes": 262_144,
            "queue_timeout_ms": 5_000,
            "engine_timeout_ms": 4_000,
            "job_timeout_ms": 5_000,
            "soft_timeout_ms": 4_000,
            "cleanup_timeout_ms": 2_000,
            "request_timeout_ms": 20_000,
            "client_timeout_ms": 25_000,
            "memory_limit_bytes": 1_073_741_824,
        }
        assert descriptor.schema_fingerprint == schema_fingerprint(
            descriptor.input_schema,
            descriptor.output_schema,
            frozenset(policy.operation for policy in descriptor.operations),
        )
        assert (
            len(
                json.dumps(
                    descriptor.input_schema,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode()
            )
            < operation.max_parameter_bytes
        )
        assert (
            len(
                json.dumps(
                    descriptor.output_schema,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode()
            )
            < operation.max_result_bytes
        )
        assert descriptor.input_schema["additionalProperties"] is False
        assert "operation" in descriptor.input_schema["required"]
        assert "default" not in descriptor.input_schema["properties"]["operation"]


@pytest.mark.asyncio
async def test_mixed_compute_batch_preserves_request_order_and_typed_results(
    test_server,
):
    async with _authenticated_client() as (client, _user):
        _catalog_response, descriptors = await _catalog(client)
        request_id = f"mixed-request-{uuid4().hex}"
        rebalance_correlation = f"rebalance-{uuid4().hex}"
        pac_correlation = f"pac-{uuid4().hex}"
        response = await client.post(
            f"{API_BASE}/tools/compute",
            json={
                "request_id": request_id,
                "items": [
                    _compute_item(
                        descriptors["portfolio_rebalancer"],
                        rebalance_correlation,
                        _rebalancer_parameters(),
                    ),
                    _compute_item(
                        descriptors["pac_allocator"],
                        pac_correlation,
                        _pac_parameters(),
                    ),
                ],
            },
            timeout=TIMEOUT,
        )

    assert response.status_code == 200, response.text
    payload = response.json()
    transport = _transport(payload)
    assert transport.request_id == request_id
    assert payload["success_count"] == 2
    assert payload["failed_count"] == 0
    assert type(transport.metrics.server_processing_ms) is int
    assert transport.metrics.server_processing_ms >= 0
    assert [result.correlation_id for result in transport.results] == [rebalance_correlation, pac_correlation]
    assert [result.tool_code for result in transport.results] == [
        "portfolio_rebalancer",
        "pac_allocator",
    ]

    rebalance_result, pac_result = transport.results
    assert isinstance(rebalance_result, ToolComputeSuccess)
    assert isinstance(pac_result, ToolComputeSuccess)
    _assert_success_identity(
        rebalance_result,
        descriptors["portfolio_rebalancer"],
        rebalance_correlation,
    )
    _assert_success_identity(
        pac_result,
        descriptors["pac_allocator"],
        pac_correlation,
    )
    assert rebalance_result.execution_id != pac_result.execution_id

    rebalance_model = REBALANCE_ANALYZE_OUTPUT_ADAPTER.validate_python(
        rebalance_result.result,
        strict=True,
    )
    pac_model = PAC_ANALYZE_OUTPUT_ADAPTER.validate_python(
        pac_result.result,
        strict=True,
    )
    assert isinstance(rebalance_model, RebalanceAnalyzeReady)
    assert isinstance(pac_model, PacAnalyzeReady)

    rebalance = rebalance_model.model_dump(mode="json")
    assert rebalance["result_kind"] == "portfolio_rebalancing_analysis"
    assert _available_value(rebalance["totals"]["current_invested_reporting"]) == {"currency": "EUR", "amount": "100"}
    assert _available_value(rebalance["totals"]["contributions_reporting"]) == {
        "currency": "EUR",
        "amount": "0.300000000003",
    }
    assert _available_value(rebalance["totals"]["cash_plus_contributions_reporting"]) == {
        "currency": "EUR",
        "amount": "1",
    }
    instruments = {item["instrument_key"]: item for item in rebalance["instruments"]}
    assert _available_value(instruments["api-rebalance-alpha"]["value_gap_to_target_reporting"]) == {"currency": "EUR", "amount": "-10"}
    assert _available_value(instruments["api-rebalance-beta"]["value_gap_to_target_reporting"]) == {"currency": "EUR", "amount": "10"}
    assert all(issue["code"] != "duplicate_currency" for issue in rebalance["issues"])

    pac = pac_model.model_dump(mode="json")
    assert pac["result_kind"] == "pac_budget_analysis"
    assert _available_value(pac["totals"]["contributions_reporting"]) == {
        "currency": "EUR",
        "amount": "0.300000000003",
    }
    assert _available_value(pac["totals"]["investable_budget_reporting"]) == {"currency": "EUR", "amount": "100"}
    allocations = {item["instrument_key"]: item for item in pac["allocations"]}
    assert _available_value(allocations["api-pac-alpha"]["ideal_allocation_reporting"]) == {"currency": "EUR", "amount": "25"}
    assert _available_value(allocations["api-pac-beta"]["ideal_allocation_reporting"]) == {"currency": "EUR", "amount": "75"}
    assert all(issue["code"] != "duplicate_currency" for issue in pac["issues"])


@pytest.mark.asyncio
async def test_duplicate_existing_cash_is_a_typed_domain_invalid_result(
    test_server,
):
    async with _authenticated_client() as (client, _user):
        _catalog_response, descriptors = await _catalog(client)
        descriptor = descriptors["pac_allocator"]
        correlation_id = f"duplicate-cash-{uuid4().hex}"
        parameters = _pac_parameters()
        parameters["cash_balances"] = [
            {"currency": "EUR", "amount": "1"},
            {"currency": "EUR", "amount": "2"},
        ]
        parameters["contributions"] = []
        response = await client.post(
            f"{API_BASE}/tools/compute",
            json={
                "request_id": f"duplicate-cash-request-{uuid4().hex}",
                "items": [
                    _compute_item(
                        descriptor,
                        correlation_id,
                        parameters,
                    )
                ],
            },
            timeout=TIMEOUT,
        )

    assert response.status_code == 200, response.text
    payload = response.json()
    transport = _transport(payload)
    assert payload["success_count"] == 1
    assert payload["failed_count"] == 0
    (result,) = transport.results
    assert isinstance(result, ToolComputeSuccess)
    _assert_success_identity(result, descriptor, correlation_id)

    model = PAC_ANALYZE_OUTPUT_ADAPTER.validate_python(
        result.result,
        strict=True,
    )
    assert isinstance(model, PacAnalyzeInvalid)
    invalid = model.model_dump(mode="json")
    assert invalid["availability"] == "invalid"
    assert invalid["normalized"] is None
    duplicates = [issue for issue in invalid["issues"] if issue["code"] == "duplicate_currency"]
    assert len(duplicates) == 1
    (issue,) = duplicates
    assert issue["kind"] == "invalid"
    assert issue["path"] == ["cash_balances", 0, "currency"]
    assert issue["related_indices"] == [0, 1]
    assert issue["params"]["currency"] == "EUR"
    assert issue["params"]["vector"] == "cash_balances"
    assert invalid["cash_pools"] == {
        "availability": "unavailable",
        "value": None,
        "reason_codes": ["input_invalid"],
    }


@pytest.mark.asyncio
async def test_tools_require_auth_and_publish_no_separate_schema_endpoint(
    test_server,
):
    valid_unauthorized_batch = {
        "request_id": f"unauthorized-{uuid4().hex}",
        "items": [
            {
                "correlation_id": f"unauthorized-item-{uuid4().hex}",
                "tool_code": "pac_allocator",
                "contract_version": "1.0.0",
                "implementation_version": "1.0.0",
                "schema_fingerprint": "0" * 64,
                "parameters": _pac_parameters(),
            }
        ],
    }
    async with httpx.AsyncClient() as anonymous:
        for path in ("/tools/catalog", "/tools/diagnostics"):
            response = await anonymous.get(
                f"{API_BASE}{path}",
                timeout=TIMEOUT,
            )
            assert response.status_code == 401, response.text
        response = await anonymous.post(
            f"{API_BASE}/tools/compute",
            json=valid_unauthorized_batch,
            timeout=TIMEOUT,
        )
        assert response.status_code == 401, response.text

    async with _authenticated_client() as (client, _user):
        for path in (
            "/tools/schema",
            "/tools/pac_allocator/schema",
            "/tools/portfolio_rebalancer/schema",
        ):
            response = await client.get(f"{API_BASE}{path}", timeout=TIMEOUT)
            assert response.status_code == 404, response.text


@pytest.mark.asyncio
async def test_foreign_user_references_and_execution_lookup_are_impossible(
    test_server,
):
    async with (
        _authenticated_client() as (
            owner_client,
            owner,
        ),
        _authenticated_client() as (foreign_client, foreign),
    ):
        _catalog_response, descriptors = await _catalog(owner_client)
        owner_correlation = f"owner-{uuid4().hex}"
        owner_response = await owner_client.post(
            f"{API_BASE}/tools/compute",
            json={
                "request_id": f"owner-request-{uuid4().hex}",
                "items": [
                    _compute_item(
                        descriptors["pac_allocator"],
                        owner_correlation,
                        _pac_parameters(),
                    )
                ],
            },
            timeout=TIMEOUT,
        )
        assert owner_response.status_code == 200, owner_response.text
        owner_transport = _transport(owner_response.json())
        (owner_result,) = owner_transport.results
        assert isinstance(owner_result, ToolComputeSuccess)

        for path in (
            f"/tools/results/{owner_result.execution_id}",
            f"/tools/executions/{owner_result.execution_id}",
        ):
            lookup = await foreign_client.get(
                f"{API_BASE}{path}",
                timeout=TIMEOUT,
            )
            assert lookup.status_code == 404, lookup.text

        foreign_parameters = _pac_parameters()
        foreign_parameters["user_id"] = owner["id"]
        foreign_correlation = f"foreign-{uuid4().hex}"
        foreign_response = await foreign_client.post(
            f"{API_BASE}/tools/compute",
            json={
                "request_id": f"foreign-request-{uuid4().hex}",
                "items": [
                    _compute_item(
                        descriptors["pac_allocator"],
                        foreign_correlation,
                        foreign_parameters,
                    )
                ],
            },
            timeout=TIMEOUT,
        )

    assert foreign_response.status_code == 200, foreign_response.text
    payload = foreign_response.json()
    transport = _transport(payload)
    assert payload["success_count"] == 0
    assert payload["failed_count"] == 1
    (result,) = transport.results
    assert isinstance(result, ToolComputeFailure)
    assert result.correlation_id == foreign_correlation
    assert result.tool_code == "pac_allocator"
    assert result.error.code == "invalid_parameters"
    assert result.error.retryable is False
    assert result.error.issue_count == 1
    assert [issue.path for issue in result.error.issues] == [["user_id"]]
    assert str(owner["username"]) not in foreign_response.text
    assert str(foreign["username"]) not in foreign_response.text

"""Live HTTP contract test for the PAC allocator Tool pilot."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

import httpx
import pytest

from backend.app.config import get_settings
from backend.app.schemas.pac_allocator import (
    PAC_ANALYZE_OUTPUT_ADAPTER,
    PacAnalyzeInvalid,
    PacAnalyzeReady,
)
from backend.app.schemas.tools import (
    ToolCatalogResponse,
    ToolComputeBatchResponse,
    ToolComputeSuccess,
    ToolDescriptor,
    ToolItemMetrics,
)
from backend.app.services.tools.schema import schema_fingerprint
from backend.test_scripts.test_server_helper import _TestingServerManager

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0
PASSWORD = "PacToolApiTestPass123!"

PAC_SCHEMA_FINGERPRINT = "9741509a39b3fecf736091d1687b0663d325687d23b39a1f0a36a77593c291b4"
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
}


@pytest.fixture(scope="module")
def test_server():
    """Attach to the backend owned by the test runner."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


async def _login_normal_user(client: httpx.AsyncClient) -> None:
    async def register_unique_user() -> tuple[str, bool]:
        username = f"pac_tool_{uuid4().hex[:16]}"
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


@asynccontextmanager
async def _normal_user_client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient() as client:
        await _login_normal_user(client)
        try:
            yield client
        finally:
            response = await client.delete(
                f"{API_BASE}/auth/users/me",
                timeout=TIMEOUT,
            )
            assert response.status_code == 200, response.text


def _parameters(*, first_price: str = "25") -> dict[str, object]:
    return {
        "operation": "analyze",
        "report_currency": "EUR",
        "as_of_date": "2026-09-08",
        "rows": [
            {
                "row_key": "pilot-equity",
                "instrument_key": "pilot-equity",
                "name": "Pilot equity",
                "initial_quantity": "2",
                "quote": {
                    "raw_price": first_price,
                    "currency": "EUR",
                    "quote_base_quantity": 1,
                    "reference_date": "2026-09-08",
                },
                "target_percent": "25",
                "buy_grid": {"mode": "whole", "quantity_step": "1"},
            },
            {
                "row_key": "pilot-bond",
                "instrument_key": "pilot-bond",
                "name": "Pilot bond",
                "initial_quantity": "1",
                "quote": {
                    "raw_price": "150",
                    "currency": "EUR",
                    "quote_base_quantity": 1,
                    "reference_date": "2026-09-08",
                },
                "target_percent": "75",
                "buy_grid": {"mode": "whole", "quantity_step": "1"},
            },
        ],
        "cash_balances": [{"currency": "EUR", "amount": "10"}],
        "contributions": [{"currency": "EUR", "amount": "5"}],
        "valuation_rates": [],
    }


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


def _assert_complete_success_metrics(metrics: ToolItemMetrics) -> None:
    values = metrics.model_dump(mode="json")
    assert set(values) == ITEM_METRIC_FIELDS
    for value in values.values():
        assert type(value) is int
        assert value >= 0
    assert values["total_ms"] >= values["execution_ms"]
    assert values["execution_ms"] >= values["compute_ms"]


def _available_value(fact: dict[str, object]) -> object:
    assert fact["availability"] == "available"
    assert fact["reason_codes"] == []
    return fact["value"]


def _assert_ratio(
    fact: dict[str, object],
    *,
    numerator: str,
    denominator: str,
    approximation: str,
    unit: str,
) -> None:
    assert _available_value(fact) == {
        "numerator": numerator,
        "denominator": denominator,
        "unit": unit,
        "approximation": approximation,
        "approximation_decimal_places": 28,
        "approximation_exact": True,
    }


@pytest.mark.asyncio
async def test_pac_tool_catalog_and_cross_process_compute(test_server):
    """The live Tool boundary executes both ready and domain-invalid P1 inputs."""
    async with _normal_user_client() as client:
        catalog_response = await client.get(
            f"{API_BASE}/tools/catalog",
            timeout=TIMEOUT,
        )
        assert catalog_response.status_code == 200, catalog_response.text
        catalog = ToolCatalogResponse.model_validate(catalog_response.json())
        matching = [item for item in catalog.items if item.tool_code == "pac_allocator" and item.contract_version == "1.0.0"]
        assert len(matching) == 1
        (descriptor,) = matching
        assert all(item.tool_code != "pac_allocator" for item in catalog.unavailable)

        assert descriptor.implementation_version == "1.0.0"
        assert descriptor.schema_fingerprint == PAC_SCHEMA_FINGERPRINT
        assert descriptor.category == "allocation"
        assert descriptor.icon_key == "calculator"
        assert descriptor.ui.model_dump(mode="json") == {
            "kind": "custom",
            "component_key": "pac-allocator",
            "ui_contract_version": 1,
        }
        assert descriptor.documentation.model_dump(mode="json") == {
            "path": "user/tools/pac-allocator/",
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
            "job_timeout_ms": 5_000,
            "soft_timeout_ms": 4_000,
        }
        assert descriptor.schema_fingerprint == schema_fingerprint(
            descriptor.input_schema,
            descriptor.output_schema,
            frozenset(policy.operation for policy in descriptor.operations),
        )

        request_id = f"pac-request-{uuid4().hex}"
        ready_correlation = f"pac-ready-{uuid4().hex}"
        invalid_correlation = f"pac-invalid-{uuid4().hex}"
        response = await client.post(
            f"{API_BASE}/tools/compute",
            json={
                "request_id": request_id,
                "items": [
                    _compute_item(descriptor, ready_correlation, _parameters()),
                    _compute_item(
                        descriptor,
                        invalid_correlation,
                        _parameters(first_price="not-a-decimal"),
                    ),
                ],
            },
            timeout=TIMEOUT,
        )

    assert response.status_code == 200, response.text
    payload = response.json()
    transport = ToolComputeBatchResponse.model_validate({key: value for key, value in payload.items() if key not in {"success_count", "failed_count"}})
    assert transport.request_id == request_id
    assert payload["success_count"] == 2
    assert payload["failed_count"] == 0
    assert type(transport.metrics.server_processing_ms) is int
    assert transport.metrics.server_processing_ms >= 0

    results = {result.correlation_id: result for result in transport.results}
    assert set(results) == {ready_correlation, invalid_correlation}
    ready_result = results[ready_correlation]
    invalid_result = results[invalid_correlation]
    assert isinstance(ready_result, ToolComputeSuccess)
    assert isinstance(invalid_result, ToolComputeSuccess)
    assert ready_result.status == invalid_result.status == "success"
    assert ready_result.execution_id != invalid_result.execution_id
    _assert_success_identity(ready_result, descriptor, ready_correlation)
    _assert_success_identity(invalid_result, descriptor, invalid_correlation)

    ready_model = PAC_ANALYZE_OUTPUT_ADAPTER.validate_python(ready_result.result)
    assert isinstance(ready_model, PacAnalyzeReady)
    ready = ready_model.model_dump(mode="json")
    assert ready["operation"] == "analyze"
    assert ready["result_kind"] == "initial_state_analysis"
    assert ready["numeric_policy_id"] == "pac-initial-state-v1"
    assert ready["availability"] == "ready"
    assert ready["trade_feasibility"] == "not_evaluated"
    assert ready["optimization"] == "not_run"
    assert ready["issues"] == []

    rows = {row["row_key"]: row for row in ready["rows"]}
    assert set(rows) == {"pilot-equity", "pilot-bond"}
    assert _available_value(rows["pilot-equity"]["quantity"]) == "2"
    assert _available_value(rows["pilot-equity"]["initial_value_native"]) == {
        "currency": "EUR",
        "amount": "50",
    }
    assert _available_value(rows["pilot-equity"]["initial_value_reporting"]) == {
        "currency": "EUR",
        "amount": "50",
    }
    _assert_ratio(
        rows["pilot-equity"]["current_weight_percent"],
        numerator="5000",
        denominator="200",
        approximation="25",
        unit="percent",
    )
    assert _available_value(rows["pilot-bond"]["initial_value_reporting"]) == {
        "currency": "EUR",
        "amount": "150",
    }
    _assert_ratio(
        rows["pilot-bond"]["current_weight_percent"],
        numerator="15000",
        denominator="200",
        approximation="75",
        unit="percent",
    )

    assert _available_value(ready["totals"]["initial_invested_reporting"]) == {
        "currency": "EUR",
        "amount": "200",
    }
    assert _available_value(ready["totals"]["existing_cash_reporting"]) == {
        "currency": "EUR",
        "amount": "10",
    }
    assert _available_value(ready["totals"]["contributions_reporting"]) == {
        "currency": "EUR",
        "amount": "5",
    }
    assert _available_value(ready["totals"]["cash_plus_contributions_reporting"]) == {
        "currency": "EUR",
        "amount": "15",
    }
    assert _available_value(ready["totals"]["target_total_percent"]) == "100"
    _assert_ratio(
        ready["totals"]["max_abs_gap_pp"],
        numerator="0",
        denominator="200",
        approximation="0",
        unit="percentage_points",
    )
    _assert_ratio(
        ready["totals"]["squared_gap_pp2"],
        numerator="0",
        denominator="40000",
        approximation="0",
        unit="percentage_points_squared",
    )

    cash_pools = {pool["currency"]: pool for pool in _available_value(ready["cash_pools"])}
    assert set(cash_pools) == {"EUR"}
    assert cash_pools["EUR"]["existing_amount"] == "10"
    assert cash_pools["EUR"]["contribution_amount"] == "5"
    assert cash_pools["EUR"]["combined_amount"] == "15"

    normalized = ready["normalized"]
    normalized_rows = {row["row_key"]: row for row in normalized["rows"]}
    assert normalized_rows["pilot-equity"]["initial_quantity"] == "2"
    assert normalized_rows["pilot-equity"]["quote"]["raw_price"] == "25"
    assert normalized["cash_balances"] == [{"currency": "EUR", "amount": "10"}]
    assert normalized["contributions"] == [{"currency": "EUR", "amount": "5"}]

    invalid_model = PAC_ANALYZE_OUTPUT_ADAPTER.validate_python(invalid_result.result)
    assert isinstance(invalid_model, PacAnalyzeInvalid)
    invalid = invalid_model.model_dump(mode="json")
    assert invalid["availability"] == "invalid"
    assert invalid["trade_feasibility"] == "not_evaluated"
    assert invalid["optimization"] == "not_run"
    assert invalid["normalized"] is None
    matching_issues = [issue for issue in invalid["issues"] if issue["kind"] == "invalid" and issue["code"] == "invalid_decimal_syntax" and issue["path"] == ["rows", 0, "quote", "raw_price"]]
    assert len(matching_issues) == 1
    (decimal_issue,) = matching_issues
    assert decimal_issue["related_row_indices"] == [0]

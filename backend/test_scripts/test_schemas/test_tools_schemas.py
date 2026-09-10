"""Private DTO contract tests; no application, registry, worker or database setup.

The primitive models below only supply genuine Pydantic schemas for transport
fixtures. They are not registered plugins or substitutes for a financial model.
Normal package imports are intentional: these tests do not bypass package
initializers or the runner's global conftest.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Literal

import pytest
from pydantic import BaseModel, ConfigDict, TypeAdapter, ValidationError

from backend.app.schemas.tools import (
    ToolCatalogResponse,
    ToolComputeBatchRequest,
    ToolComputeBatchResponse,
    ToolComputeFailure,
    ToolComputeItem,
    ToolComputeResult,
    ToolComputeSuccess,
    ToolDescriptor,
    ToolDiagnosticsResponse,
    ToolDocumentation,
    ToolItemMetrics,
    ToolOperationPolicy,
    ToolPlatformPolicy,
    ToolUIDescriptor,
    ToolVersion,
)


class _PrivateInput(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    operation: Literal["inspect"]
    text: str | None = None


class _PrivateOutput(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    operation: Literal["inspect"]
    availability: Literal["ready", "invalid"]
    text: str | None


def _ui() -> dict:
    return {"kind": "custom", "component_key": "private-dto-probe", "ui_contract_version": 1}


def _documentation() -> dict:
    return {"path": "user/tools/private-dto-probe/", "version": "1.0.0"}


def _operation() -> dict:
    return {"operation": "inspect"}


def _descriptor() -> dict:
    return {
        "tool_code": "private_dto_probe",
        "contract_version": "1.0.0",
        "implementation_version": "1.0.0",
        "schema_fingerprint": "a" * 64,
        "name": "Private DTO probe",
        "description": "A test-owned primitive transport fixture.",
        "category": "testing",
        "icon_key": "code",
        "ui": _ui(),
        "documentation": _documentation(),
        "input_schema": _PrivateInput.model_json_schema(mode="validation"),
        "output_schema": _PrivateOutput.model_json_schema(mode="serialization"),
        "operations": [_operation()],
    }


def _identity(correlation_id: str) -> dict:
    return {
        "correlation_id": correlation_id,
        "tool_code": "private_dto_probe",
        "contract_version": "1.0.0",
        "implementation_version": "1.0.0",
        "schema_fingerprint": "a" * 64,
    }


def _item(correlation_id: str = "item-a") -> dict:
    return {**_identity(correlation_id), "parameters": {"operation": "inspect", "text": "private"}}


def _success(correlation_id: str = "item-a") -> dict:
    return {
        **_identity(correlation_id),
        "execution_id": f"execution-{correlation_id}",
        "metrics": {},
        "status": "success",
        "result": _PrivateOutput(operation="inspect", availability="ready", text=None).model_dump(),
    }


def _failure(correlation_id: str = "item-b") -> dict:
    return {
        **_identity(correlation_id),
        "execution_id": None,
        "metrics": {},
        "status": "error",
        "error": {
            "code": "invalid_parameters",
            "retryable": False,
            "issues": [{"code": "string_type", "path": ["text"]}],
            "issue_count": 1,
        },
    }


def _request() -> dict:
    return {"request_id": "private-request", "items": [_item()]}


def _response() -> dict:
    return {
        "request_id": "private-request",
        "results": [_success(), _failure()],
        "metrics": {"server_processing_ms": 7},
    }


def _catalog() -> dict:
    return {
        "catalog_version": "1",
        "policy": {},
        "items": [_descriptor()],
        "unavailable": [{"tool_code": "private_unavailable", "reason": "unavailable"}],
    }


def _diagnostics() -> dict:
    return {
        "scope": "api_process",
        "runtime_id": "private-runtime",
        "policy": {},
        "loaded": [_descriptor()],
        "failures": [{"tool_code": None, "filename": "private_broken.py", "reason": "import_failed"}],
        "pool": {
            "available": True,
            "active": 0,
            "queued": 0,
            "pending": 0,
            "degraded_lanes": 0,
            "completed": 0,
            "failed": 0,
        },
    }


def _boundary_policy() -> dict:
    """Small owned limits exactly covering both envelopes and every timed phase."""
    return {
        "workers": 2,
        "max_batch_items": 4,
        "max_pending_items": 8,
        "max_pending_per_principal": 4,
        "max_batches_per_principal": 1,
        "max_request_bytes": 48,
        "max_parameter_bytes": 8,
        "max_result_bytes": 16,
        "max_response_bytes": 80,
        "envelope_reserve_bytes": 16,
        "max_json_depth": 4,
        "queue_timeout_ms": 5,
        "job_timeout_ms": 5,
        "soft_timeout_ms": 4,
        "output_reserve_ms": 1,
        "cleanup_timeout_ms": 2,
        "ingress_timeout_ms": 2,
        "response_reserve_ms": 2,
        "request_timeout_ms": 16,
        "client_timeout_ms": 17,
    }


def _at(payload: dict, path: tuple[str | int, ...]) -> dict:
    """Address only a known location in a fresh, test-owned payload."""
    node = payload
    for part in path:
        node = node[part]
    return node


@pytest.mark.parametrize(
    ("model", "factory", "path"),
    [
        pytest.param(ToolComputeBatchRequest, _request, (), id="request"),
        pytest.param(ToolComputeBatchRequest, _request, ("items", 0), id="request-item"),
        pytest.param(ToolCatalogResponse, _catalog, (), id="catalog"),
        pytest.param(ToolCatalogResponse, _catalog, ("policy",), id="platform-policy"),
        pytest.param(ToolCatalogResponse, _catalog, ("items", 0), id="descriptor"),
        pytest.param(ToolCatalogResponse, _catalog, ("items", 0, "ui"), id="ui"),
        pytest.param(ToolCatalogResponse, _catalog, ("items", 0, "documentation"), id="documentation"),
        pytest.param(ToolCatalogResponse, _catalog, ("items", 0, "operations", 0), id="operation-policy"),
        pytest.param(ToolCatalogResponse, _catalog, ("unavailable", 0), id="unavailable"),
        pytest.param(ToolComputeBatchResponse, _response, (), id="response"),
        pytest.param(ToolComputeBatchResponse, _response, ("metrics",), id="batch-metrics"),
        pytest.param(ToolComputeBatchResponse, _response, ("results", 0), id="success"),
        pytest.param(ToolComputeBatchResponse, _response, ("results", 1), id="failure"),
        pytest.param(ToolComputeBatchResponse, _response, ("results", 0, "metrics"), id="item-metrics"),
        pytest.param(ToolComputeBatchResponse, _response, ("results", 1, "error"), id="error"),
        pytest.param(ToolComputeBatchResponse, _response, ("results", 1, "error", "issues", 0), id="validation-issue"),
        pytest.param(ToolDiagnosticsResponse, _diagnostics, (), id="diagnostics"),
        pytest.param(ToolDiagnosticsResponse, _diagnostics, ("pool",), id="pool"),
        pytest.param(ToolDiagnosticsResponse, _diagnostics, ("failures", 0), id="discovery-failure"),
    ],
)
def test_transport_forbids_extras_at_each_envelope_level(model, factory, path):
    payload = factory()
    model.model_validate(payload)
    _at(payload, path)["unexpected_test_field"] = "private"

    with pytest.raises(ValidationError) as caught:
        model.model_validate(payload)

    assert any(
        issue["type"] == "extra_forbidden" and issue["loc"][-1] == "unexpected_test_field"
        for issue in caught.value.errors(include_input=False)
    )


@pytest.mark.parametrize(
    ("model", "factory", "path", "field", "value"),
    [
        (ToolComputeBatchRequest, _request, (), "request_id", 1),
        (ToolComputeBatchRequest, _request, ("items", 0), "correlation_id", b"item-a"),
        (ToolComputeBatchRequest, _request, ("items", 0), "tool_code", b"private_dto_probe"),
        (ToolComputeBatchRequest, _request, ("items", 0), "contract_version", 1),
        (ToolComputeBatchRequest, _request, ("items", 0), "schema_fingerprint", b"a" * 64),
        (ToolCatalogResponse, _catalog, ("policy",), "workers", True),
        (ToolCatalogResponse, _catalog, ("policy",), "max_parameter_bytes", "131072"),
        (ToolCatalogResponse, _catalog, ("items", 0, "ui"), "ui_contract_version", "1"),
        (ToolCatalogResponse, _catalog, ("items", 0, "ui"), "ui_contract_version", True),
        (ToolCatalogResponse, _catalog, ("items", 0, "ui"), "ui_contract_version", 1.0),
        (ToolCatalogResponse, _catalog, ("items", 0, "operations", 0), "deterministic", "true"),
        (ToolCatalogResponse, _catalog, ("items", 0, "operations", 0), "deterministic", 1),
        (ToolCatalogResponse, _catalog, ("items", 0, "operations", 0), "pure", 1),
        (ToolCatalogResponse, _catalog, ("items", 0, "documentation"), "version", 1),
        (ToolComputeBatchResponse, _response, ("metrics",), "server_processing_ms", 7.0),
        (ToolComputeBatchResponse, _response, ("results", 1, "error"), "retryable", 0),
        (ToolComputeBatchResponse, _response, ("results", 1, "error"), "issue_count", "1"),
        (ToolDiagnosticsResponse, _diagnostics, ("pool",), "available", 1),
        (ToolDiagnosticsResponse, _diagnostics, ("pool",), "active", False),
    ],
)
def test_transport_does_not_coerce_nested_metadata_types(model, factory, path, field, value):
    payload = factory()
    model.model_validate(payload)
    _at(payload, path)[field] = value

    with pytest.raises(ValidationError) as caught:
        model.model_validate(payload)

    assert any(field in issue["loc"] for issue in caught.value.errors(include_input=False))


@pytest.mark.parametrize(
    ("model", "factory", "fields"),
    [
        (ToolUIDescriptor, _ui, ("kind", "component_key", "ui_contract_version")),
        (ToolCatalogResponse, _catalog, ("catalog_version",)),
        (ToolDiagnosticsResponse, _diagnostics, ("scope",)),
        (ToolOperationPolicy, _operation, ("operation",)),
        (ToolDocumentation, _documentation, ("path", "version")),
        (
            ToolDescriptor,
            _descriptor,
            ("contract_version", "implementation_version", "schema_fingerprint", "ui", "documentation", "operations"),
        ),
        (
            ToolComputeItem,
            _item,
            ("correlation_id", "tool_code", "contract_version", "implementation_version", "schema_fingerprint", "parameters"),
        ),
        (ToolComputeSuccess, _success, ("status", "execution_id", "metrics", "result")),
        (ToolComputeFailure, _failure, ("status", "execution_id", "metrics", "error")),
    ],
)
def test_required_contract_fields_are_not_supplied_by_defaults(model, factory, fields):
    model.model_validate(factory())
    for field in fields:
        payload = factory()
        del payload[field]
        with pytest.raises(ValidationError) as caught:
            model.model_validate(payload)
        assert any(
            issue["type"] == "missing" and issue["loc"] == (field,)
            for issue in caught.value.errors(include_input=False)
        ), field


@pytest.mark.parametrize(
    ("model", "factory", "field", "value"),
    [
        (ToolUIDescriptor, _ui, "kind", "generated"),
        (ToolCatalogResponse, _catalog, "catalog_version", "2"),
        (ToolCatalogResponse, _catalog, "catalog_version", 1),
        (ToolDiagnosticsResponse, _diagnostics, "scope", "global"),
        (ToolComputeSuccess, _success, "status", "ready"),
        (ToolComputeFailure, _failure, "status", "failed"),
        (ToolOperationPolicy, _operation, "pure", False),
        (ToolOperationPolicy, _operation, "deduplication", "exact"),
    ],
)
def test_literal_metadata_rejects_other_variants(model, factory, field, value):
    payload = factory()
    payload[field] = value
    with pytest.raises(ValidationError) as caught:
        model.model_validate(payload)
    assert any(
        issue["type"] == "literal_error" and issue["loc"] == (field,)
        for issue in caught.value.errors(include_input=False)
    )


@pytest.mark.parametrize("mode", ["validation", "serialization"])
@pytest.mark.parametrize(
    ("model", "field", "literal"),
    [
        (ToolUIDescriptor, "kind", "custom"),
        (ToolCatalogResponse, "catalog_version", "1"),
        (ToolDiagnosticsResponse, "scope", "api_process"),
        (ToolComputeSuccess, "status", "success"),
        (ToolComputeFailure, "status", "error"),
    ],
)
def test_exported_literal_metadata_is_explicit_and_required(model, field, literal, mode):
    schema = model.model_json_schema(mode=mode)
    assert field in schema["required"]
    assert schema["properties"][field]["enum"] == [literal]


def test_descriptor_uses_optional_i18n_key_metadata():
    payload = _descriptor()
    descriptor = ToolDescriptor.model_validate(payload)
    assert descriptor.name_i18n_key is None
    assert descriptor.description_i18n_key is None

    payload.update(name_i18n_key="tools.private.name", description_i18n_key="tools.private.description")
    descriptor = ToolDescriptor.model_validate(payload)
    assert descriptor.name_i18n_key == payload["name_i18n_key"]
    assert descriptor.description_i18n_key == payload["description_i18n_key"]


def test_descriptor_rejects_duplicate_operation_names():
    payload = _descriptor()
    payload["operations"] = [_operation(), _operation()]
    with pytest.raises(ValidationError) as caught:
        ToolDescriptor.model_validate(payload)
    assert any(issue["type"] == "value_error" for issue in caught.value.errors(include_input=False))


@pytest.mark.parametrize("factory", [_success, _failure], ids=["success", "error"])
def test_result_union_requires_the_status_discriminator(factory):
    payload = factory()
    del payload["status"]
    with pytest.raises(ValidationError) as caught:
        TypeAdapter(ToolComputeResult).validate_python(payload)
    assert any(issue["type"] == "union_tag_not_found" for issue in caught.value.errors(include_input=False))


@pytest.mark.parametrize("status", ["ready", "invalid", "failed", None, 1])
def test_result_union_does_not_treat_domain_availability_as_platform_status(status):
    payload = _success()
    payload["status"] = status
    with pytest.raises(ValidationError) as caught:
        TypeAdapter(ToolComputeResult).validate_python(payload)
    assert any(issue["type"] == "union_tag_invalid" for issue in caught.value.errors(include_input=False))


@pytest.mark.parametrize(
    ("factory", "status", "missing_field", "extra_field"),
    [(_success, "error", "error", "result"), (_failure, "success", "result", "error")],
)
def test_result_discriminator_selects_only_its_own_payload(factory, status, missing_field, extra_field):
    payload = factory()
    payload.update(status=status, execution_id="private-execution")
    with pytest.raises(ValidationError) as caught:
        TypeAdapter(ToolComputeResult).validate_python(payload)
    errors = caught.value.errors(include_input=False)
    assert any(issue["type"] == "missing" and issue["loc"][-1] == missing_field for issue in errors)
    assert any(issue["type"] == "extra_forbidden" and issue["loc"][-1] == extra_field for issue in errors)


def test_success_requires_a_nonnull_execution_id():
    payload = _success()
    payload["execution_id"] = None
    with pytest.raises(ValidationError) as caught:
        ToolComputeSuccess.model_validate(payload)
    assert any(issue["loc"] == ("execution_id",) for issue in caught.value.errors(include_input=False))


@pytest.mark.parametrize("execution_id", [None, "private-execution"])
def test_failure_can_describe_rejection_before_or_after_execution(execution_id):
    payload = _failure()
    payload["execution_id"] = execution_id
    assert ToolComputeFailure.model_validate(payload).execution_id == execution_id


@pytest.mark.parametrize(
    "parameters",
    [None, True, 1, 1.0, "1", "  unparsed text  ", [], {}, ["text", None, False], {"operation": "not_a_plugin_operation"}],
)
def test_parameters_are_arbitrary_json_until_per_item_validation(parameters):
    payload = _item()
    payload["parameters"] = deepcopy(parameters)
    item = ToolComputeItem.model_validate(payload)
    assert type(item.parameters) is type(parameters)
    assert item.parameters == parameters


def test_parameters_preserve_omission_null_text_and_scalar_types():
    raw = {
        "explicit_null": None,
        "string": "1",
        "integer": 1,
        "float": 1.0,
        "boolean": True,
        "text": "  e\u0301 🚀\r\n ",
    }
    payload = _item()
    payload["parameters"] = deepcopy(raw)
    actual = ToolComputeItem.model_validate(payload).model_dump()["parameters"]

    assert actual == raw
    assert "operation" not in actual
    assert actual["explicit_null"] is None
    for key in ("string", "integer", "float", "boolean"):
        assert type(actual[key]) is type(raw[key]), key


def test_parameters_do_not_expand_optional_defaults_or_conflate_missing_with_null():
    omitted = _item("omitted-text")
    omitted["parameters"] = {"operation": "inspect"}
    explicit_null = _item("null-text")
    explicit_null["parameters"] = {"operation": "inspect", "text": None}
    payload = _request()
    payload["items"] = [omitted, explicit_null]

    request = ToolComputeBatchRequest.model_validate(payload)
    by_correlation = {item.correlation_id: item.parameters for item in request.items}
    assert by_correlation["omitted-text"] == {"operation": "inspect"}
    assert "text" not in by_correlation["omitted-text"]
    assert by_correlation["null-text"] == {"operation": "inspect", "text": None}
    assert by_correlation["null-text"]["text"] is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("correlation_id", ""),
        ("correlation_id", "two words"),
        ("correlation_id", "x" * 65),
        ("tool_code", "Private_dto_probe"),
        ("tool_code", " private_dto_probe"),
        ("tool_code", "private-dto-probe"),
        ("schema_fingerprint", "a" * 63),
        ("schema_fingerprint", "A" * 64),
    ],
)
def test_invalid_envelope_identity_is_rejected_before_domain_validation(field, value):
    payload = _item()
    payload.update(parameters=None)
    payload[field] = value
    with pytest.raises(ValidationError) as caught:
        ToolComputeItem.model_validate(payload)
    assert any(issue["loc"] == (field,) for issue in caught.value.errors(include_input=False))


def test_repeated_tool_and_identical_parameters_are_distinct_request_items():
    payload = _request()
    payload["items"] = [_item("item-a"), _item("item-b")]
    request = ToolComputeBatchRequest.model_validate(payload)
    assert [item.correlation_id for item in request.items] == ["item-a", "item-b"]
    assert {item.tool_code for item in request.items} == {"private_dto_probe"}
    assert all(item.parameters == {"operation": "inspect", "text": "private"} for item in request.items)


@pytest.mark.parametrize(
    ("model", "factory", "field", "duplicate_items"),
    [
        (ToolComputeBatchRequest, _request, "items", lambda: [_item("same-id"), _item("same-id")]),
        (ToolComputeBatchResponse, _response, "results", lambda: [_success("same-id"), _failure("same-id")]),
    ],
)
def test_correlation_ids_must_be_unique_within_each_envelope(model, factory, field, duplicate_items):
    payload = factory()
    payload[field] = duplicate_items()
    with pytest.raises(ValidationError) as caught:
        model.model_validate(payload)
    assert any(issue["type"] == "value_error" for issue in caught.value.errors(include_input=False))


@pytest.mark.parametrize("size", [0, 5])
@pytest.mark.parametrize(
    ("model", "factory", "field", "item_factory"),
    [(ToolComputeBatchRequest, _request, "items", _item), (ToolComputeBatchResponse, _response, "results", _success)],
)
def test_batch_cardinality_is_bounded(model, factory, field, item_factory, size):
    payload = factory()
    payload[field] = [item_factory(f"item-{index}") for index in range(size)]
    with pytest.raises(ValidationError) as caught:
        model.model_validate(payload)
    assert any(issue["loc"] == (field,) for issue in caught.value.errors(include_input=False))


@pytest.mark.parametrize("size", [1, 4])
def test_request_accepts_both_batch_size_boundaries(size):
    payload = _request()
    correlations = [f"item-{index}" for index in range(size)]
    payload["items"] = [_item(correlation) for correlation in correlations]
    request = ToolComputeBatchRequest.model_validate(payload)
    assert [item.correlation_id for item in request.items] == correlations


def test_response_counts_platform_success_even_when_domain_result_is_invalid():
    invalid = _success("domain-invalid")
    invalid["result"] = _PrivateOutput(operation="inspect", availability="invalid", text=None).model_dump()
    payload = _response()
    payload["results"] = [_success("domain-ready"), invalid, _failure("platform-error")]
    response = ToolComputeBatchResponse.model_validate(payload)

    assert response.success_count == 2
    assert response.failed_count == 1
    by_correlation = {item.correlation_id: item for item in response.results}
    assert by_correlation["domain-invalid"].status == "success"
    assert by_correlation["domain-invalid"].result == invalid["result"]
    serialized = response.model_dump(mode="json")
    assert serialized["success_count"] == 2
    assert serialized["failed_count"] == 1


@pytest.mark.parametrize("count_field", ["success_count", "failed_count"])
def test_response_counts_cannot_be_supplied_or_overridden(count_field):
    payload = _response()
    payload[count_field] = 99
    with pytest.raises(ValidationError) as caught:
        ToolComputeBatchResponse.model_validate(payload)
    assert any(
        issue["type"] == "extra_forbidden" and issue["loc"] == (count_field,)
        for issue in caught.value.errors(include_input=False)
    )


_METRIC_PHASES = (
    "queue_wait_ms",
    "startup_ms",
    "input_validation_ms",
    "compute_ms",
    "output_validation_ms",
    "serialization_ms",
    "execution_ms",
    "cleanup_ms",
    "total_ms",
)


def test_unobserved_metric_phases_serialize_as_null_not_zero():
    expected = {phase: None for phase in _METRIC_PHASES}
    assert ToolItemMetrics().model_dump(mode="json") == expected
    assert ToolItemMetrics.model_validate(expected).model_dump(mode="json") == expected

    observed = ToolItemMetrics(queue_wait_ms=0, cleanup_ms=2)
    expected.update(queue_wait_ms=0, cleanup_ms=2)
    assert observed.model_dump(mode="json") == expected


@pytest.mark.parametrize("phase", _METRIC_PHASES)
@pytest.mark.parametrize("value", [-1, True, "0", 0.0])
def test_observed_item_durations_are_strict_nonnegative_integers(phase, value):
    with pytest.raises(ValidationError) as caught:
        ToolItemMetrics.model_validate({phase: value})
    assert any(issue["loc"] == (phase,) for issue in caught.value.errors(include_input=False))


def test_platform_policy_accepts_exact_envelope_and_deadline_boundaries():
    payload = _boundary_policy()
    policy = ToolPlatformPolicy.model_validate(payload)
    assert policy.model_dump() == payload
    assert policy.max_batch_items * policy.max_parameter_bytes + policy.envelope_reserve_bytes == policy.max_request_bytes
    assert policy.max_batch_items * policy.max_result_bytes + policy.envelope_reserve_bytes == policy.max_response_bytes
    assert policy.soft_timeout_ms + policy.output_reserve_ms == policy.job_timeout_ms
    assert (
        policy.ingress_timeout_ms
        + policy.queue_timeout_ms
        + policy.job_timeout_ms
        + policy.cleanup_timeout_ms
        + policy.response_reserve_ms
    ) == policy.request_timeout_ms
    assert policy.client_timeout_ms > policy.request_timeout_ms


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("workers", 9),
        ("max_pending_per_principal", 9),
        ("soft_timeout_ms", 5),
        ("output_reserve_ms", 2),
        ("queue_timeout_ms", 6),
        ("job_timeout_ms", 6),
        ("cleanup_timeout_ms", 3),
        ("ingress_timeout_ms", 3),
        ("response_reserve_ms", 3),
        ("request_timeout_ms", 15),
        ("client_timeout_ms", 16),
        ("client_timeout_ms", 15),
        ("max_request_bytes", 47),
        ("max_response_bytes", 79),
        ("max_parameter_bytes", 9),
        ("max_result_bytes", 17),
        ("envelope_reserve_bytes", 17),
    ],
)
def test_platform_policy_rejects_incoherent_capacity_and_deadlines(field, value):
    payload = _boundary_policy()
    payload[field] = value
    with pytest.raises(ValidationError) as caught:
        ToolPlatformPolicy.model_validate(payload)
    assert any(issue["type"] == "value_error" for issue in caught.value.errors(include_input=False))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("workers", 0),
        ("max_batch_items", 0),
        ("max_batch_items", 5),
        ("max_batches_per_principal", 2),
        ("max_json_depth", 0),
        ("max_json_depth", 65),
    ],
)
def test_platform_policy_rejects_out_of_range_resource_limits(field, value):
    payload = _boundary_policy()
    payload[field] = value
    with pytest.raises(ValidationError) as caught:
        ToolPlatformPolicy.model_validate(payload)
    assert any(issue["loc"] == (field,) for issue in caught.value.errors(include_input=False))


def test_operation_policy_is_pure_without_deduplication():
    policy = ToolOperationPolicy.model_validate(_operation())
    assert policy.operation == "inspect"
    assert policy.pure is True
    assert policy.deduplication == "none"


@pytest.mark.parametrize("soft_timeout", [5, 6])
def test_operation_soft_deadline_must_precede_hard_deadline(soft_timeout):
    with pytest.raises(ValidationError) as caught:
        ToolOperationPolicy(operation="inspect", soft_timeout_ms=soft_timeout, job_timeout_ms=5)
    assert any(issue["type"] == "value_error" for issue in caught.value.errors(include_input=False))


@pytest.mark.parametrize("path", ["user/tools/private-dto-probe", "user/tools/private-dto-probe/", "developer/tools_1"])
def test_documentation_accepts_safe_relative_paths_without_rewriting(path):
    assert ToolDocumentation(path=path, version="1.0.0").path == path


@pytest.mark.parametrize(
    "path",
    [
        "",
        "/user/tools",
        "mkdocs/user/tools",
        "../tools",
        "user/../tools",
        "user/./tools",
        "user//tools",
        "https://example.invalid/tools",
        "user/tools?lang=en",
        "user/tools#section",
        "user/%2e%2e/tools",
        "user\\tools",
        "user/é",
    ],
)
def test_documentation_rejects_absolute_escaped_or_ambiguous_paths(path):
    with pytest.raises(ValidationError) as caught:
        ToolDocumentation(path=path, version="1.0.0")
    assert any(issue["loc"] == ("path",) for issue in caught.value.errors(include_input=False))


@pytest.mark.parametrize(
    "version",
    ["0.0.0", "1.2.3", "1.2.3-0", "1.2.3-rc.1", "1.2.3-0A", "1.2.3-alpha-1+build.001", "1.2.3+001"],
)
def test_semver_accepts_valid_prerelease_and_build_identifiers_without_normalizing(version):
    assert TypeAdapter(ToolVersion).validate_python(version) == version


@pytest.mark.parametrize(
    "version",
    [
        "1",
        "1.2",
        "v1.2.3",
        "01.2.3",
        "1.02.3",
        "1.2.03",
        "1.2.3-01",
        "1.2.3-alpha.01",
        "1.2.3-",
        "1.2.3-alpha..1",
        "1.2.3+",
        "1.2.3+build..1",
        "1.2.3-β",
        " 1.2.3",
        "1.2.3 ",
        "1.2.3+" + "a" * 59,
    ],
)
def test_semver_rejects_invalid_grammar_and_oversized_versions(version):
    with pytest.raises(ValidationError):
        TypeAdapter(ToolVersion).validate_python(version)

"""Versioned transport contracts for atomic, authenticated Tools."""

from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import ConfigDict, Field, JsonValue, computed_field, field_validator, model_validator

from backend.app.schemas.common import StrictModel

ToolCode = Annotated[str, Field(strict=True, min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_]*$")]
ToolVersion = Annotated[
    str,
    Field(
        strict=True,
        max_length=64,
        pattern=r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-((0|[1-9][0-9]*|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*)(\.(0|[1-9][0-9]*|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*))*))?(\+[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?$",
    ),
]
ToolToken = Annotated[str, Field(strict=True, min_length=1, max_length=64, pattern=r"^[!-~]+$")]
ToolFingerprint = Annotated[str, Field(strict=True, pattern=r"^[a-f0-9]{64}$")]
ToolMilliseconds = Annotated[int, Field(strict=True, ge=0)]
ToolPositiveInt = Annotated[int, Field(strict=True, gt=0)]
ToolFieldPath = Annotated[list[Annotated[str, Field(strict=True, max_length=64)] | Annotated[int, Field(strict=True, ge=0)]], Field(max_length=16)]

ToolErrorCode = Literal[
    "unknown_tool",
    "tool_unavailable",
    "version_mismatch",
    "invalid_parameters",
    "input_limit_exceeded",
    "queue_full",
    "queue_timeout",
    "execution_limit",
    "execution_timeout",
    "worker_crashed",
    "execution_failed",
    "invalid_output",
    "output_limit_exceeded",
    "cleanup_failed",
    "service_unavailable",
]
ToolDiscoveryReason = Literal[
    "import_failed",
    "invalid_plugin",
    "invalid_code",
    "duplicate_code",
    "invalid_descriptor",
    "invalid_input_model",
    "invalid_output_model",
    "invalid_schema",
    "invalid_operation_policy",
]


class ToolTransportModel(StrictModel):
    model_config = ConfigDict(strict=True, frozen=True, allow_inf_nan=False, json_schema_serialization_defaults_required=True)


class ToolPlatformPolicy(ToolTransportModel):
    """Effective per-API-process limits, not a throughput guarantee."""

    workers: ToolPositiveInt = 2
    max_batch_items: Annotated[int, Field(strict=True, ge=1, le=4)] = 4
    max_pending_items: ToolPositiveInt = 8
    max_pending_per_principal: ToolPositiveInt = 4
    max_batches_per_principal: Annotated[int, Field(strict=True, ge=1, le=1)] = 1
    max_request_bytes: ToolPositiveInt = 1_048_576
    max_parameter_bytes: ToolPositiveInt = 131_072
    max_result_bytes: ToolPositiveInt = 262_144
    max_response_bytes: ToolPositiveInt = 1_114_112
    envelope_reserve_bytes: ToolPositiveInt = 65_536
    max_json_depth: Annotated[int, Field(strict=True, ge=1, le=64)] = 32
    queue_timeout_ms: ToolPositiveInt = 5_000
    job_timeout_ms: ToolPositiveInt = 5_000
    soft_timeout_ms: ToolPositiveInt = 4_000
    output_reserve_ms: ToolPositiveInt = 1_000
    cleanup_timeout_ms: ToolPositiveInt = 2_000
    ingress_timeout_ms: ToolPositiveInt = 2_000
    response_reserve_ms: ToolPositiveInt = 2_000
    request_timeout_ms: ToolPositiveInt = 20_000
    client_timeout_ms: ToolPositiveInt = 25_000

    @model_validator(mode="after")
    def coherent_limits(self) -> Self:
        if self.workers > self.max_pending_items:
            raise ValueError("Worker count cannot exceed pending-item capacity")
        if self.max_pending_per_principal > self.max_pending_items:
            raise ValueError("Principal capacity cannot exceed process capacity")
        if self.soft_timeout_ms + self.output_reserve_ms > self.job_timeout_ms:
            raise ValueError("The job deadline must reserve time for validated output")
        server_bound = self.ingress_timeout_ms + self.queue_timeout_ms + self.job_timeout_ms + self.cleanup_timeout_ms + self.response_reserve_ms
        if server_bound > self.request_timeout_ms:
            raise ValueError("Request deadline must include admission, queue, job, cleanup and response")
        if self.client_timeout_ms <= self.request_timeout_ms:
            raise ValueError("Client timeout must leave transport time after the server deadline")
        if self.max_batch_items * self.max_result_bytes + self.envelope_reserve_bytes > self.max_response_bytes:
            raise ValueError("Response capacity must cover every item and its envelope")
        if self.max_batch_items * self.max_parameter_bytes + self.envelope_reserve_bytes > self.max_request_bytes:
            raise ValueError("Request capacity must cover every item and its envelope")
        return self


class ToolOperationPolicy(ToolTransportModel):
    operation: ToolCode
    pure: Literal[True] = True
    deterministic: bool = True
    deduplication: Literal["none"] = "none"
    max_parameter_bytes: ToolPositiveInt = 131_072
    max_result_bytes: ToolPositiveInt = 262_144
    queue_timeout_ms: ToolPositiveInt = 5_000
    job_timeout_ms: ToolPositiveInt = 5_000
    soft_timeout_ms: ToolPositiveInt = 4_000

    @field_validator("pure", mode="before")
    @classmethod
    def require_pure_boolean(cls, value: object) -> object:
        if type(value) is not bool:
            raise ValueError("Tool purity must be a boolean literal")
        return value

    @model_validator(mode="after")
    def ordered_deadlines(self) -> Self:
        if self.soft_timeout_ms >= self.job_timeout_ms:
            raise ValueError("Soft deadline must precede the hard job deadline")
        return self


class ToolUIDescriptor(ToolTransportModel):
    kind: Literal["custom"] = Field(..., json_schema_extra={"enum": ["custom"]})
    component_key: Annotated[str, Field(strict=True, min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9-]*$")]
    ui_contract_version: Annotated[int, Field(strict=True, ge=1)]


class ToolDocumentation(ToolTransportModel):
    path: Annotated[str, Field(strict=True, min_length=1, max_length=256)]
    version: ToolVersion

    @field_validator("path")
    @classmethod
    def relative_documentation_path(cls, value: str) -> str:
        parts = value.removesuffix("/").split("/")
        if value.startswith("/") or value.startswith("mkdocs/") or any(part in ("", ".", "..") for part in parts):
            raise ValueError("Documentation path must be relative to the documentation root")
        if any(not (character.isascii() and (character.isalnum() or character in "-_/")) for character in value):
            raise ValueError("Documentation path cannot contain a URL, query, fragment or escape")
        return value


class ToolDescriptor(ToolTransportModel):
    tool_code: ToolCode
    contract_version: ToolVersion
    implementation_version: ToolVersion
    schema_fingerprint: ToolFingerprint
    name: Annotated[str, Field(strict=True, min_length=1, max_length=128)]
    description: Annotated[str, Field(strict=True, min_length=1, max_length=512)]
    name_i18n_key: Annotated[str, Field(strict=True, max_length=128)] | None = None
    description_i18n_key: Annotated[str, Field(strict=True, max_length=128)] | None = None
    category: ToolCode
    icon_key: ToolCode
    ui: ToolUIDescriptor
    documentation: ToolDocumentation
    input_schema: dict[str, JsonValue]
    output_schema: dict[str, JsonValue]
    operations: Annotated[list[ToolOperationPolicy], Field(min_length=1, max_length=16)]

    @model_validator(mode="after")
    def unique_operations(self) -> Self:
        if len({policy.operation for policy in self.operations}) != len(self.operations):
            raise ValueError("Tool operation names must be unique")
        return self


class ToolUnavailableSummary(ToolTransportModel):
    tool_code: ToolCode | None
    reason: Literal["unavailable"] = "unavailable"


class ToolCatalogResponse(ToolTransportModel):
    catalog_version: Literal["1"] = Field(..., json_schema_extra={"enum": ["1"]})
    policy: ToolPlatformPolicy
    items: list[ToolDescriptor]
    unavailable: list[ToolUnavailableSummary]


class ToolComputeItem(ToolTransportModel):
    correlation_id: ToolToken
    tool_code: ToolCode
    contract_version: ToolVersion
    implementation_version: ToolVersion
    schema_fingerprint: ToolFingerprint
    parameters: JsonValue


class ToolComputeBatchRequest(ToolTransportModel):
    request_id: ToolToken
    items: Annotated[list[ToolComputeItem], Field(min_length=1, max_length=4)]

    @model_validator(mode="after")
    def unique_correlations(self) -> Self:
        if len({item.correlation_id for item in self.items}) != len(self.items):
            raise ValueError("Each compute item must have a distinct correlation ID")
        return self


class ToolValidationIssue(ToolTransportModel):
    code: Annotated[str, Field(strict=True, min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")]
    path: ToolFieldPath


class ToolError(ToolTransportModel):
    code: ToolErrorCode
    retryable: bool
    issues: Annotated[list[ToolValidationIssue], Field(max_length=32)] = Field(default_factory=list)
    issue_count: Annotated[int, Field(strict=True, ge=0)] = 0


class ToolItemMetrics(ToolTransportModel):
    """Monotonic durations; unobserved phases are null, never invented zeroes."""

    queue_wait_ms: ToolMilliseconds | None = None
    startup_ms: ToolMilliseconds | None = None
    input_validation_ms: ToolMilliseconds | None = None
    compute_ms: ToolMilliseconds | None = None
    output_validation_ms: ToolMilliseconds | None = None
    serialization_ms: ToolMilliseconds | None = None
    execution_ms: ToolMilliseconds | None = None
    cleanup_ms: ToolMilliseconds | None = None
    total_ms: ToolMilliseconds | None = None


class ToolBatchMetrics(ToolTransportModel):
    server_processing_ms: ToolMilliseconds


class ToolResultIdentity(ToolTransportModel):
    correlation_id: ToolToken
    tool_code: ToolCode
    contract_version: ToolVersion
    implementation_version: ToolVersion
    schema_fingerprint: ToolFingerprint
    execution_id: ToolToken | None
    metrics: ToolItemMetrics


class ToolComputeSuccess(ToolResultIdentity):
    status: Literal["success"] = Field(..., json_schema_extra={"enum": ["success"]})
    execution_id: ToolToken
    result: JsonValue


class ToolComputeFailure(ToolResultIdentity):
    status: Literal["error"] = Field(..., json_schema_extra={"enum": ["error"]})
    error: ToolError


ToolComputeResult = Annotated[ToolComputeSuccess | ToolComputeFailure, Field(discriminator="status")]


class ToolComputeBatchResponse(ToolTransportModel):
    """Counts describe platform outcomes, not financially ready scenarios."""

    request_id: ToolToken
    results: Annotated[list[ToolComputeResult], Field(min_length=1, max_length=4)]
    metrics: ToolBatchMetrics

    @model_validator(mode="after")
    def unique_correlations(self) -> Self:
        if len({result.correlation_id for result in self.results}) != len(self.results):
            raise ValueError("Compute results must retain distinct correlation IDs")
        return self

    @computed_field
    @property
    def success_count(self) -> int:
        return sum(result.status == "success" for result in self.results)

    @computed_field
    @property
    def failed_count(self) -> int:
        return len(self.results) - self.success_count


class ToolDiscoveryFailure(ToolTransportModel):
    tool_code: ToolCode | None
    filename: Annotated[str, Field(strict=True, max_length=132, pattern=r"^[A-Za-z0-9_.-]+$")]
    reason: ToolDiscoveryReason


class ToolPoolSnapshot(ToolTransportModel):
    available: bool
    active: Annotated[int, Field(strict=True, ge=0)]
    queued: Annotated[int, Field(strict=True, ge=0)]
    pending: Annotated[int, Field(strict=True, ge=0)]
    degraded_lanes: Annotated[int, Field(strict=True, ge=0)]
    completed: Annotated[int, Field(strict=True, ge=0)]
    failed: Annotated[int, Field(strict=True, ge=0)]


class ToolDiagnosticsResponse(ToolTransportModel):
    scope: Literal["api_process"] = Field(..., json_schema_extra={"enum": ["api_process"]})
    runtime_id: ToolToken
    policy: ToolPlatformPolicy
    loaded: list[ToolDescriptor]
    failures: list[ToolDiscoveryFailure]
    pool: ToolPoolSnapshot

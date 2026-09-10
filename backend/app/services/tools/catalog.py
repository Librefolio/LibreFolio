"""Read-only catalogue projection and effective operation policies."""

from __future__ import annotations

from backend.app.schemas.tools import ToolCatalogResponse, ToolDescriptor, ToolDiscoveryFailure, ToolOperationPolicy, ToolPlatformPolicy, ToolUnavailableSummary
from backend.app.services.tools.base import ToolDefinitionError
from backend.app.services.tools.registry import ToolDefinition, ToolPluginRegistry


def effective_operation(policy: ToolOperationPolicy, platform: ToolPlatformPolicy) -> ToolOperationPolicy:
    hard = min(policy.job_timeout_ms, platform.job_timeout_ms)
    soft = min(policy.soft_timeout_ms, platform.soft_timeout_ms, hard - platform.output_reserve_ms)
    if soft <= 0:
        raise ToolDefinitionError("invalid_operation_policy")
    return ToolOperationPolicy(
        operation=policy.operation,
        pure=policy.pure,
        deterministic=policy.deterministic,
        deduplication="none",
        max_parameter_bytes=min(policy.max_parameter_bytes, platform.max_parameter_bytes),
        max_result_bytes=min(policy.max_result_bytes, platform.max_result_bytes),
        queue_timeout_ms=min(policy.queue_timeout_ms, platform.queue_timeout_ms),
        job_timeout_ms=hard,
        soft_timeout_ms=soft,
    )


def effective_descriptor(definition: ToolDefinition, policy: ToolPlatformPolicy) -> ToolDescriptor:
    return ToolDescriptor.model_validate(
        {
            **definition.descriptor.model_dump(),
            "operations": [effective_operation(operation, policy) for operation in definition.descriptor.operations],
        }
    )


def effective_catalog_entries(policy: ToolPlatformPolicy, registry_class: type[ToolPluginRegistry] = ToolPluginRegistry) -> tuple[list[ToolDescriptor], tuple[ToolDiscoveryFailure, ...]]:
    snapshot = registry_class.get_snapshot()
    descriptors: list[ToolDescriptor] = []
    failures = list(snapshot.failures)
    for code, definition in snapshot.definitions.items():
        try:
            descriptors.append(effective_descriptor(definition, policy))
        except ToolDefinitionError as exc:
            failures.append(ToolDiscoveryFailure(tool_code=code, filename="operation_policy", reason=exc.reason))
    return descriptors, tuple(failures)


def get_tool_catalog(policy: ToolPlatformPolicy, registry_class: type[ToolPluginRegistry] = ToolPluginRegistry) -> ToolCatalogResponse:
    descriptors, failures = effective_catalog_entries(policy, registry_class)
    unavailable_codes = dict.fromkeys(failure.tool_code for failure in failures)
    return ToolCatalogResponse(
        catalog_version="1",
        policy=policy,
        items=descriptors,
        unavailable=[ToolUnavailableSummary(tool_code=code) for code in unavailable_codes],
    )

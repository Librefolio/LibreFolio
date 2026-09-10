"""Tool adapter for the pure PAC initial-state analyzer."""

from backend.app.schemas.pac_allocator import PacAnalyzeInput, PacAnalyzeOutput
from backend.app.schemas.tools import (
    ToolDocumentation,
    ToolOperationPolicy,
    ToolUIDescriptor,
)
from backend.app.services.pac_allocator import analyze_initial_state
from backend.app.services.provider_registry import register_plugin
from backend.app.services.tools.base import ToolExecutionContext, ToolPlugin
from backend.app.services.tools.registry import ToolPluginRegistry


@register_plugin(ToolPluginRegistry)
class PacAllocatorTool(ToolPlugin[PacAnalyzeInput, PacAnalyzeOutput]):
    tool_code = "pac_allocator"
    contract_version = "1.0.0"
    implementation_version = "1.0.0"

    name = "PAC allocator"
    description = "Analyze the exact initial allocation state."
    name_i18n_key = "tools.pacAllocator.name"
    description_i18n_key = "tools.pacAllocator.description"
    category = "allocation"
    icon_key = "calculator"

    ui = ToolUIDescriptor(
        kind="custom",
        component_key="pac-allocator",
        ui_contract_version=1,
    )
    documentation = ToolDocumentation(
        path="user/tools/pac-allocator/",
        version="1.0.0",
    )
    operations = (
        ToolOperationPolicy(
            operation="analyze",
            pure=True,
            deterministic=True,
            deduplication="none",
            max_parameter_bytes=131_072,
            max_result_bytes=262_144,
            queue_timeout_ms=5_000,
            job_timeout_ms=5_000,
            soft_timeout_ms=4_000,
        ),
    )

    input_type = PacAnalyzeInput
    output_type = PacAnalyzeOutput

    def compute(
        self,
        parameters: PacAnalyzeInput,
        context: ToolExecutionContext,
    ) -> PacAnalyzeOutput:
        return analyze_initial_state(
            parameters,
            checkpoint=context.checkpoint,
        )

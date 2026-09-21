"""Tool adapter for pure PAC and portfolio-rebalancing P1 analyses."""

from pydantic import BaseModel

from backend.app.schemas.pac_allocator import (
    P1_RESULT_BYTES,
    PacAnalyzeInput,
    PacAnalyzeOutput,
    RebalanceAnalyzeInput,
    RebalanceAnalyzeOutput,
)
from backend.app.schemas.tools import (
    ToolDocumentation,
    ToolOperationPolicy,
    ToolUIDescriptor,
)
from backend.app.services.pac_allocator import analyze_pac_budget, analyze_rebalancing
from backend.app.services.provider_registry import register_plugin
from backend.app.services.tools.base import (
    ToolExecutionContext,
    ToolExecutionError,
    ToolPlugin,
    ToolService,
)
from backend.app.services.tools.registry import ToolPluginRegistry

_ANALYZE_POLICY = (
    ToolOperationPolicy(
        operation="analyze",
        pure=True,
        deterministic=True,
        deduplication="none",
        max_parameter_bytes=131_072,
        max_result_bytes=P1_RESULT_BYTES,
        queue_timeout_ms=5_000,
        job_timeout_ms=5_000,
        soft_timeout_ms=4_000,
    ),
)


@register_plugin(ToolPluginRegistry)
class PacAllocatorTool(ToolPlugin):
    contract_version = "1.0.0"
    implementation_version = "1.0.0"

    services = (
        ToolService(
            tool_code="pac_allocator",
            name="PAC allocator",
            description="Distribute investable liquidity across selected Assets by target percentage.",
            name_i18n_key="tools.pacAllocator.name",
            description_i18n_key="tools.pacAllocator.description",
            category="allocation",
            icon_key="calculator",
            ui=ToolUIDescriptor(
                kind="custom",
                component_key="pac-allocator",
                version="1.0.0",
            ),
            documentation=ToolDocumentation(
                path="user/tools/pac-allocator/",
                version="1.0.0",
            ),
            operations=_ANALYZE_POLICY,
            input_type=PacAnalyzeInput,
            output_type=PacAnalyzeOutput,
        ),
        ToolService(
            tool_code="portfolio_rebalancer",
            name="Portfolio rebalancer",
            description="Compare current invested allocation with a final target.",
            name_i18n_key="tools.portfolioRebalancer.name",
            description_i18n_key="tools.portfolioRebalancer.description",
            category="allocation",
            icon_key="scale",
            ui=ToolUIDescriptor(
                kind="custom",
                component_key="portfolio-rebalancer",
                version="1.0.0",
            ),
            documentation=ToolDocumentation(
                path="user/tools/portfolio-rebalancer/",
                version="1.0.0",
            ),
            operations=_ANALYZE_POLICY,
            input_type=RebalanceAnalyzeInput,
            output_type=RebalanceAnalyzeOutput,
        ),
    )

    def compute(
        self,
        tool_code: str,
        parameters: BaseModel,
        context: ToolExecutionContext,
    ) -> PacAnalyzeOutput | RebalanceAnalyzeOutput:
        if tool_code == "pac_allocator" and isinstance(parameters, PacAnalyzeInput):
            return analyze_pac_budget(
                parameters,
                checkpoint=context.checkpoint,
            )
        if tool_code == "portfolio_rebalancer" and isinstance(
            parameters,
            RebalanceAnalyzeInput,
        ):
            return analyze_rebalancing(
                parameters,
                checkpoint=context.checkpoint,
            )
        raise ToolExecutionError("invalid_parameters")

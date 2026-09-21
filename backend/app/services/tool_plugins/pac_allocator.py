"""Tool adapter for the PAC planner v2.

The P1 ``analyze`` services (``pac_allocator`` and ``portfolio_rebalancer``)
were removed on 2026-09-21 by developer decision: they were never released,
never fully tested, and the master plan §1.2 declares compatibility with the P1
prototype a non-goal. What replaces them is ``operation="plan"``, backed by
``plan_pac_allocation`` — the exact-arithmetic planner with an exhaustive
oracle and a proof layer.

**The Rebalancer has no service here yet.** Its v2 policies (``invest_only``,
``invest_and_sell``) and the SELL verifier do not exist, so registering a
Rebalancer service would mean shipping a tool with nothing behind it. It comes
back when those exist — which is the next piece of work, because PAC is the
special case of the Rebalancer with an all-zero starting allocation.

Timeout envelope: only one number is a product decision — ``engine_timeout_ms``,
the solver's own budget, set to 30 s by the developer. Every other value is
*derived* from identities the platform validators impose, not chosen:

    soft    >= engine + post-engine reserve   44 000 = 30 000 + 14 000
    job      = soft + output_reserve          45 000 = 44 000 +  1 000
    request >= ingress + queue + job + cleanup + response
                                              59 000 = 2 000 + 5 000 + 45 000
                                                       + 5 000 + 2 000
    client   > request                        65 000

``server_bound`` therefore equals exactly 59 000 against a ``request`` of
59 000: **the margin is zero**. Raising ``queue``, ``cleanup`` or ``job`` by a
single millisecond fails validation — and an invalid operation policy removes
the whole tool from the catalog, not just the operation. If more cleanup time
is ever needed it has to be taken from the job budget.

> The 30 s is **provisional and unmeasured at representative scale**. It comes
> from a product decision plus the platform's own arithmetic, not from a
> capacity campaign: the only timings taken so far are on single-digit
> asset/broker fixtures (3-8 ms), which have no predictive value. Revisit it
> once the planner is stress-tested with progressively more assets, brokers and
> constraints. Do not treat this number as validated.
"""

from pydantic import BaseModel

from backend.app.schemas.pac_allocator import PacPlannerRequest, PacPlannerResult
from backend.app.schemas.tools import (
    ToolDocumentation,
    ToolOperationPolicy,
    ToolUIDescriptor,
)
from backend.app.services.pac_allocator.planner import plan_pac_allocation
from backend.app.services.provider_registry import register_plugin
from backend.app.services.tools.base import (
    ToolExecutionContext,
    ToolExecutionError,
    ToolPlugin,
    ToolService,
)
from backend.app.services.tools.registry import ToolPluginRegistry

_PLAN_RESULT_BYTES = 512 * 1024

_PLAN_POLICY = (
    ToolOperationPolicy(
        operation="plan",
        pure=True,
        deterministic=True,
        deduplication="none",
        max_parameter_bytes=262_144,
        max_result_bytes=_PLAN_RESULT_BYTES,
        queue_timeout_ms=5_000,
        engine_timeout_ms=30_000,
        job_timeout_ms=45_000,
        soft_timeout_ms=44_000,
        cleanup_timeout_ms=5_000,
        request_timeout_ms=59_000,
        client_timeout_ms=65_000,
    ),
)


@register_plugin(ToolPluginRegistry)
class PacAllocatorTool(ToolPlugin):
    contract_version = "2.0.0"
    implementation_version = "2.0.0"

    services = (
        ToolService(
            tool_code="pac_allocator",
            name="PAC allocator",
            description="Plan whole-unit purchases that bring an allocation as close as possible to its target.",
            name_i18n_key="tools.pacAllocator.name",
            description_i18n_key="tools.pacAllocator.description",
            category="allocation",
            icon_key="calculator",
            ui=ToolUIDescriptor(
                kind="custom",
                component_key="pac-allocator",
                version="2.0.0",
            ),
            documentation=ToolDocumentation(
                path="user/tools/pac-allocator/",
                version="2.0.0",
            ),
            operations=_PLAN_POLICY,
            input_type=PacPlannerRequest,
            output_type=PacPlannerResult,
        ),
    )

    def compute(
        self,
        tool_code: str,
        parameters: BaseModel,
        context: ToolExecutionContext,
    ) -> PacPlannerResult:
        # Dispatch on tool_code *and* the declared operation, never on the
        # shape of the parameters.
        if tool_code == "pac_allocator" and isinstance(parameters, PacPlannerRequest) and parameters.operation == "plan":
            return plan_pac_allocation(
                parameters,
                checkpoint=context.checkpoint,
            )
        raise ToolExecutionError("invalid_parameters")

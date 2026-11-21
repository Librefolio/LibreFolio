"""Tool adapter for the planner v2: the PAC and the Rebalancer.

The P1 ``analyze`` services (``pac_allocator`` and ``portfolio_rebalancer``)
were removed on 2026-09-21 by developer decision: they were never released,
never fully tested, and the master plan §1.2 declares compatibility with the P1
prototype a non-goal. What replaces them is ``operation="plan"``, backed by
``plan_pac_allocation`` — SCIP, whose own status is the proof (D-X1), with
every published number replayed in exact arithmetic.

**The Rebalancer is the second service** (B3 of project 67):
``portfolio_rebalancer``, ``operation="plan"``, backed by ``plan_rebalancing``
— the same engine, the same proof, the same replay, the same operation policy.
Until C1 it plans «Invest only»: its request refuses «Invest and sell» and any
sale route at the schema, which the platform answers ``invalid_parameters``.

**Both services also answer ``operation="preview"``** (B4 of project 67): the
numbers the screen shows before the calculation, read with the normalizer and
one exact replay (``pac_allocator/preview.py``). No optimizer, no engine window,
no phases; the platform's short default deadlines.

**``plan`` reports its phases** (V2 of project 67): ``validate``, ``model``,
``search`` («n of m» over the named stages), ``verify``, ``report``, declared on
the operation and handed to the engine as ``context.report_progress``.

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

from backend.app.logging_config import get_logger
from backend.app.schemas.pac_allocator.preview import PacToolOutput, RebalancerToolOutput
from backend.app.schemas.pac_allocator.request import PacPlannerRequest, RebalancerPlannerRequest
from backend.app.schemas.tools import (
    ToolDocumentation,
    ToolOperationPolicy,
    ToolUIDescriptor,
)
from backend.app.services.pac_allocator.evaluation.errors import ExactReplayRejectedError
from backend.app.services.pac_allocator.planner import SeededRunsFailedError, plan_pac_allocation, plan_rebalancing
from backend.app.services.pac_allocator.preview import preview_pac_allocation, preview_rebalancing
from backend.app.services.pac_allocator.progress import PLANNER_PHASES
from backend.app.services.pac_allocator.solver import SolverStageError
from backend.app.services.platform.provider_registry import register_plugin
from backend.app.services.tools.base import (
    ToolExecutionContext,
    ToolExecutionError,
    ToolPlugin,
    ToolService,
)
from backend.app.services.tools.registry import ToolPluginRegistry
from backend.app.utils.runtime.errors import code_site

logger = get_logger(__name__)

_PLAN_RESULT_BYTES = 512 * 1024

#: The engine failures whose message the log carries, as ``reason`` (R1-B of project 67, the developer's rule of 20/11/2026).
#: A closed list, matched by exact type: a class enters only once every place that raises it has been read, and its
#: messages are fixed words, identifiers and closed codes, never an amount or a name. ``test_pac_planner_tool_api.py``
#: keeps that reading true: it scans every raise of each listed class. Every other failure keeps the rule below.
MESSAGE_SAFE_ERRORS: frozenset[type[Exception]] = frozenset({ExactReplayRejectedError, SolverStageError, SeededRunsFailedError})

# Time reserved *after* the solver returns, for the exact replay and the report.
# Re-measured on 2026-10-06 (step S5 of
# `13_pacAllocator/implementation/plan-phase00PacSolverRobustness.prompt.md`,
# which closes checklist item 13 of the Step3 solver-policies plan): that work
# took 6.4-12.9 ms. The value stays as a deliberate over-reserve; the comment in
# `compute()` says why it costs nothing. The measurements live in the plan
# rather than only here, because an accurate comment ages without announcing it.
_POST_ENGINE_RESERVE_MS = 2_000

_OPERATION_POLICIES = (
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
        # The engine's phases, in order (V2 of project 67): the stream route forwards them, the waiting panel shows them.
        progress_phases=PLANNER_PHASES,
    ),
    # The scenario preview (B4 of project 67): the normalizer and one exact replay, no optimizer, so no engine window is
    # claimed and the platform's short defaults hold. Its answer has one row per target entry, smaller than the entry in the
    # request, so the plan's result cap holds it for any request the parameter cap admits.
    ToolOperationPolicy(
        operation="preview",
        pure=True,
        deterministic=True,
        deduplication="none",
        max_parameter_bytes=262_144,
        max_result_bytes=_PLAN_RESULT_BYTES,
    ),
)


def _log_engine_failure(exc: Exception, execution_id: str) -> None:
    """Tell the administrator where the engine failed, and nothing else.

    The platform turns the exception into ``execution_failed`` and, by design,
    discloses nothing more; without this line the failure left no trace at all.
    Only the exception class and the code location are logged — never the
    message, the arguments or the local variables, which can carry the user's
    amounts. ``where`` is the innermost frame of LibreFolio code, ``callers``
    the at most two LibreFolio frames that called it, nearest first, and
    ``raised_in`` the library frame below it, if any.

    The one exception is ``reason``: the message of a class in
    ``MESSAGE_SAFE_ERRORS``, matched by exact type, whose every message was
    read and names no amount (R1-B of project 67).

    The worker sends its lines to the server, which writes them in
    ``librefolio.log`` with the request's id (lot LOGS of project 67).
    """
    reason = {"reason": str(exc)} if type(exc) in MESSAGE_SAFE_ERRORS else {}
    logger.error("PAC planner engine failure", error_type=type(exc).__qualname__, execution_id=execution_id, **reason, **code_site(exc))


@register_plugin(ToolPluginRegistry)
class PacAllocatorTool(ToolPlugin):
    contract_version = "2.0.0"
    implementation_version = "2.0.0"

    services = (
        ToolService(
            tool_code="pac_allocator",
            name="PAC allocator",
            description="Plan the purchases that bring a new investment as close as possible to its target allocation, in whole units or amounts, without placing orders.",
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
                version="1.0.0",
            ),
            operations=_OPERATION_POLICIES,
            input_type=PacPlannerRequest,
            output_type=PacToolOutput,
        ),
        ToolService(
            tool_code="portfolio_rebalancer",
            name="Portfolio rebalancer",
            description="Bring an already invested portfolio towards its targets: it buys and, if you allow it, sells, estimating fees and taxes. It places no orders.",
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
            # The same policy as the PAC: the same engine window, the same reserve, the same zero margin (module docstring).
            operations=_OPERATION_POLICIES,
            input_type=RebalancerPlannerRequest,
            output_type=RebalancerToolOutput,
        ),
    )

    def compute(
        self,
        tool_code: str,
        parameters: BaseModel,
        context: ToolExecutionContext,
    ) -> BaseModel:
        # Dispatch on tool_code *and* the declared operation, never on the
        # shape of the parameters.
        services = {
            "pac_allocator": (PacPlannerRequest, plan_pac_allocation, preview_pac_allocation),
            "portfolio_rebalancer": (RebalancerPlannerRequest, plan_rebalancing, preview_rebalancing),
        }
        request_type, plan, preview = services.get(tool_code, (None, None, None))
        if request_type is None or not isinstance(parameters, request_type):
            raise ToolExecutionError("invalid_parameters")
        if parameters.operation == "preview":
            # No optimizer, so no engine window and no phases: the normalizer and one exact replay (B4 of project 67). A
            # failure is logged like the plan's: the class and the code location, never the amounts.
            try:
                return preview(parameters, checkpoint=context.checkpoint)
            except ToolExecutionError:
                raise
            except Exception as exc:
                _log_engine_failure(exc, context.execution_id)
                raise
        if parameters.operation == "plan":
            # The engine window is the product decision this module's header
            # calls the only one: claiming it is what makes `engine_timeout_ms`
            # reach SCIP instead of leaving the solver on its own 3.5 s default.
            #
            # The reserve covers what runs *after* the solver returns: the exact
            # replay of the candidate, the rounding top-ups, the conclusion and
            # the report. Measured on 2026-10-06 at 6.4-12.9 ms on synthetic
            # 5x2, 10x2 and 10x3 requests (assets x brokers), with a machine
            # load between 6 and 28; SCIP itself overran its 30 s budget by at
            # most 8 ms. It stays small because the replay evaluates one
            # candidate, whose size is the number of decisions, not the number
            # of possible candidates (the 0.7-1.0 ms measured on 2026-09-22
            # covered the replay alone, flat across 16 to 4 008 004 candidates).
            #
            # 2 000 ms is therefore a deliberate over-reserve, not a projection,
            # and it costs nothing: the claim only checks that the soft window
            # (44 000 ms from the moment the job got its slot, child start-up
            # included) still holds 30 000 + 2 000 ms. The JSON encoding and the
            # strict output check run after this method returns, outside the
            # reserve: at most 2.8 ms for a 28.5 KB result.
            window = context.claim_engine_window(post_engine_reserve_ms=_POST_ENGINE_RESERVE_MS)
            try:
                return plan(
                    parameters,
                    checkpoint=context.checkpoint,
                    solver_time_budget_seconds=window.timeout_ms / 1000,
                    # A pipe write per phase and per named stage of the search, never a datum of the scenario: no cost
                    # inside the engine window worth a reserve.
                    progress=context.report_progress,
                )
            except ToolExecutionError:
                # A platform code (time or cancellation limit): not a failure of the engine.
                raise
            except SeededRunsFailedError as exc:
                # Lot SEEDS-b of project 67: none of the Rebalancer's three runs answered (they crashed or overran, or a
                # lone «impossible» the contract cannot publish as «no plan»). The same request may answer on a retry.
                _log_engine_failure(exc, context.execution_id)
                raise ToolExecutionError("execution_failed", retryable=True) from exc
            except Exception as exc:
                _log_engine_failure(exc, context.execution_id)
                raise
        raise ToolExecutionError("invalid_parameters")

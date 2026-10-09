"""Tool adapter for the PAC planner v2.

The P1 ``analyze`` services (``pac_allocator`` and ``portfolio_rebalancer``)
were removed on 2026-09-21 by developer decision: they were never released,
never fully tested, and the master plan §1.2 declares compatibility with the P1
prototype a non-goal. What replaces them is ``operation="plan"``, backed by
``plan_pac_allocation`` — SCIP, whose own status is the proof (D-X1), with
every published number replayed in exact arithmetic.

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

import traceback
from pathlib import Path

from pydantic import BaseModel

from backend.app.logging_config import get_logger
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

logger = get_logger(__name__)

_PLAN_RESULT_BYTES = 512 * 1024

# LibreFolio's own code, told apart from libraries in a failure site; paths are
# shown from the repository root, library files by name only.
_BACKEND_ROOT = Path(__file__).resolve().parents[3]
_REPO_ROOT = _BACKEND_ROOT.parent

# Time reserved *after* the solver returns, for the exact replay and the report.
# Re-measured on 2026-10-06 (step S5 of
# `13_pacAllocator/implementation/plan-phase00PacSolverRobustness.prompt.md`,
# which closes checklist item 13 of the Step3 solver-policies plan): that work
# took 6.4-12.9 ms. The value stays as a deliberate over-reserve; the comment in
# `compute()` says why it costs nothing. The measurements live in the plan
# rather than only here, because an accurate comment ages without announcing it.
_POST_ENGINE_RESERVE_MS = 2_000

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


def _frame_text(frame: traceback.FrameSummary) -> str:
    path = Path(frame.filename).resolve()
    shown = path.relative_to(_REPO_ROOT).as_posix() if path.is_relative_to(_BACKEND_ROOT) else path.name
    return f"{shown}:{frame.lineno}:{frame.name}"


def _log_engine_failure(exc: Exception, execution_id: str) -> None:
    """Tell the administrator where the engine failed, and nothing else.

    The platform turns the exception into ``execution_failed`` and, by design,
    discloses nothing more; without this line the failure left no trace at all.
    Only the exception class and the code location are logged — never the
    message, the arguments or the local variables, which can carry the user's
    amounts. ``where`` is the innermost frame of LibreFolio code, ``callers``
    the at most two LibreFolio frames that called it, nearest first, and
    ``raised_in`` the library frame below it, if any.

    The worker is a spawn child that never calls ``configure_logging``: the
    line reaches the server's stderr (console, ``docker logs``), not
    ``librefolio.log``.
    """
    frames = traceback.extract_tb(exc.__traceback__)
    own = [frame for frame in frames if Path(frame.filename).resolve().is_relative_to(_BACKEND_ROOT)]
    site: dict[str, str | list[str]] = {}
    if own:
        site["where"] = _frame_text(own[-1])
        callers = [_frame_text(frame) for frame in reversed(own[-3:-1])]
        if callers:
            site["callers"] = callers
    if frames and (not own or own[-1] is not frames[-1]):
        site["raised_in"] = _frame_text(frames[-1])
    logger.error("PAC planner engine failure", error_type=type(exc).__qualname__, execution_id=execution_id, **site)


@register_plugin(ToolPluginRegistry)
class PacAllocatorTool(ToolPlugin):
    contract_version = "1.0.0"
    implementation_version = "1.0.0"

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
                version="1.0.0",
            ),
            documentation=ToolDocumentation(
                path="user/tools/pac-allocator/",
                version="1.0.0",
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
                return plan_pac_allocation(
                    parameters,
                    checkpoint=context.checkpoint,
                    solver_time_budget_seconds=window.timeout_ms / 1000,
                )
            except ToolExecutionError:
                # A platform code (time or cancellation limit): not a failure of the engine.
                raise
            except Exception as exc:
                _log_engine_failure(exc, context.execution_id)
                raise
        raise ToolExecutionError("invalid_parameters")
